"""Local socketpair HTTP regressions; no external requests or reader threads."""
from __future__ import annotations

import http.client
import json
import socket
import ssl
import threading
import time
import types
import unittest
import urllib.error
from contextlib import contextmanager
from unittest import mock

from test_stage_prompt_modules import load_stage_prompt_generator_for_integration_test


class TestAPIBufferedStreamReliability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage_prompt_generator_for_integration_test()

    @contextmanager
    def response(self, headers, parts=(), initial_body=b""):
        reader_socket, writer_socket = socket.socketpair()
        reader_socket.settimeout(1.5)
        writer_socket.sendall(b"HTTP/1.1 200 OK\r\n" + headers + b"\r\n" + initial_body)
        response = http.client.HTTPResponse(reader_socket)
        response.begin()
        stop = threading.Event()

        def write_parts():
            try:
                for delay, data in parts:
                    if stop.wait(delay):
                        return
                    writer_socket.sendall(data)
                writer_socket.shutdown(socket.SHUT_WR)
            except OSError:
                # Cancellation/limits intentionally close the local fixture.
                pass

        writer = threading.Thread(target=write_parts, daemon=True)
        writer.start()
        try:
            yield response, reader_socket
        finally:
            stop.set()
            writer.join(timeout=1.0)
            response.close()
            reader_socket.close()
            writer_socket.close()
            self.assertFalse(writer.is_alive())

    def read(self, response, **kwargs):
        return self.stage._read_http_response_limited(
            response, max_bytes=kwargs.pop("max_bytes", 1024),
            timeout=kwargs.pop("timeout", 2.0), label="local HTTP", **kwargs,
        )

    def test_real_content_length_body_can_arrive_after_old_socket_poll_timeout(self):
        with self.response(b"Content-Length: 4\r\n", [(0.35, b"ok"), (0.04, b"ay")]) as (response, sock):
            self.assertEqual(self.read(response), b"okay")
            self.assertIsNone(response.fp)
            self.assertEqual(sock.gettimeout(), 1.5)

    def test_body_already_buffered_with_headers_is_not_hidden_by_select(self):
        with self.response(b"Content-Length: 8\r\n", initial_body=b"buffered") as (response, sock):
            self.assertEqual(self.read(response), b"buffered")
            self.assertIsNone(response.fp)
            self.assertEqual(sock.gettimeout(), 1.5)

    def test_chunked_response_with_delayed_partial_headers_and_body(self):
        parts = [(0.02, b"2"), (0.08, b"\r\n"), (0.08, b"o"), (0.08, b"k\r\n0\r\n\r\n")]
        with self.response(b"Transfer-Encoding: chunked\r\n", parts) as (response, sock):
            with mock.patch.object(self.stage, "_COOPERATIVE_WAIT_POLL_SECONDS", 0.02):
                self.assertEqual(self.read(response), b"ok")
            self.assertIsNone(response.fp)
            self.assertEqual(sock.gettimeout(), 1.5)

    def test_connection_close_delimits_body_without_losing_delayed_bytes(self):
        with self.response(b"Connection: close\r\n", [(0.04, b"one"), (0.08, b"two")]) as (response, sock):
            with mock.patch.object(self.stage, "_COOPERATIVE_WAIT_POLL_SECONDS", 0.02):
                self.assertEqual(self.read(response), b"onetwo")
            self.assertIsNone(response.fp)
            self.assertEqual(sock.gettimeout(), 1.5)

    def test_deadline_restores_unpoisoned_buffer_and_original_socket_timeout(self):
        with self.response(b"Content-Length: 2\r\n", [(0.15, b"ok")]) as (response, sock):
            original = response.fp
            start = time.monotonic()
            with self.assertRaises(TimeoutError):
                self.read(response, deadline_monotonic=start + 0.05)
            self.assertLess(time.monotonic() - start, 0.3)
            self.assertIs(response.fp, original)
            self.assertEqual(sock.gettimeout(), 1.5)
            # A timed-out request is normally closed by its caller. Reading the
            # fixture once more proves no internal SocketIO timeout was set.
            self.assertEqual(response.read(), b"ok")

    def test_total_timeout_remains_bounded_without_an_external_deadline(self):
        with self.response(b"Content-Length: 2\r\n", [(0.15, b"ok")]) as (response, sock):
            original = response.fp
            started = time.monotonic()
            with self.assertRaisesRegex(TimeoutError, "总时限"):
                self.read(response, timeout=0.1)
            self.assertLess(time.monotonic() - started, 0.3)
            self.assertIs(response.fp, original)
            self.assertEqual(sock.gettimeout(), 1.5)
            self.assertEqual(response.read(), b"ok")

    def test_cancel_during_partial_chunk_header_restores_readable_buffer(self):
        class Cancelled(RuntimeError):
            pass

        with self.response(b"Transfer-Encoding: chunked\r\n", [(0.0, b"2"), (0.15, b"\r\nok\r\n0\r\n\r\n")]) as (response, sock):
            original = response.fp
            started = time.monotonic()

            def check():
                if time.monotonic() - started >= 0.04:
                    raise Cancelled("cancel local read")

            with mock.patch.object(self.stage, "_raise_if_comfy_interrupted", side_effect=check):
                with mock.patch.object(self.stage, "_COOPERATIVE_WAIT_POLL_SECONDS", 0.01):
                    with self.assertRaises(Cancelled):
                        self.read(response)
            self.assertLess(time.monotonic() - started, 0.2)
            self.assertIs(response.fp, original)
            self.assertEqual(sock.gettimeout(), 1.5)
            # HTTPResponse consumed a partial chunk header before cancellation;
            # do not resume protocol parsing, but the underlying socket buffer
            # remains healthy and all remaining bytes are still available.
            self.assertEqual(original.read(), b"\r\nok\r\n0\r\n\r\n")

    def test_http_error_wrapper_uses_same_safe_underlying_http_response(self):
        with self.response(b"Content-Length: 3\r\n", [(0.08, b"bad")]) as (response, sock):
            error = urllib.error.HTTPError("https://local.invalid", 400, "Bad Request", response.headers, response)
            with mock.patch.object(self.stage, "_COOPERATIVE_WAIT_POLL_SECONDS", 0.01):
                self.assertEqual(self.read(error), b"bad")
            self.assertIsNone(response.fp)
            self.assertEqual(sock.gettimeout(), 1.5)

    def test_http_error_body_propagates_consumed_cancellation_and_still_closes(self):
        class Cancelled(RuntimeError):
            pass

        stage = self.stage
        error_body = mock.Mock()
        error = urllib.error.HTTPError(
            "https://local.invalid/chat", 400, "Bad Request", {}, error_body,
        )
        cancellation = Cancelled("cancelled while reading an error body")
        mm = types.SimpleNamespace(
            InterruptProcessingException=Cancelled, processing_interrupted=lambda: False,
        )
        with (
            mock.patch.object(stage, "_comfy_mm", mm),
            mock.patch.object(stage, "_api_uses_loopback_proxy", return_value=False),
            mock.patch.object(stage, "_perform_api_http_request", side_effect=error) as request,
            mock.patch.object(stage, "_read_http_response_limited", side_effect=cancellation),
        ):
            with self.assertRaises(Cancelled) as raised:
                stage._http_post_json("https://local.invalid/chat", {"messages": []}, {}, 1.0)
        self.assertIs(raised.exception, cancellation)
        request.assert_called_once()
        error_body.close.assert_called_once()

    def test_chunked_size_limit_and_closed_fp_are_not_bypassed(self):
        with self.response(b"Transfer-Encoding: chunked\r\n", initial_body=b"4\r\n1234\r\n0\r\n\r\n") as (response, sock):
            original = response.fp
            with self.assertRaisesRegex(RuntimeError, "3 字节上限"):
                self.read(response, max_bytes=3)
            self.assertIs(response.fp, original)
            self.assertEqual(sock.gettimeout(), 1.5)

    def test_proxy_read_respects_length_and_tls_pending_buffer_without_select(self):
        sock = mock.Mock(spec=ssl.SSLSocket)
        sock.gettimeout.return_value = 4.0
        buffer = mock.Mock()
        buffer.peek.side_effect = [ssl.SSLWantReadError(), b"abc", b"bc"]
        buffer.read1.side_effect = [b"a", b"bc"]
        proxy = self.stage._CooperativeHTTPBuffer(buffer, sock, lambda: 1.0)
        with mock.patch.object(self.stage.select, "select", return_value=([sock], [], [])) as wait:
            self.assertEqual(proxy.read(1), b"a")
            self.assertEqual(proxy.read(2), b"bc")
        self.assertEqual(wait.call_count, 1)
        self.assertEqual(buffer.read1.call_args_list, [mock.call(1), mock.call(2)])
        self.assertEqual(sock.settimeout.call_args_list, [mock.call(4.0)] * 3)

    def test_proxy_read_combines_short_buffers_until_requested_length(self):
        sock = mock.Mock(spec=socket.socket)
        sock.gettimeout.return_value = None
        buffer = mock.Mock()
        buffer.peek.side_effect = [b"a", b"bc"]
        buffer.read1.side_effect = [b"a", b"bc"]
        proxy = self.stage._CooperativeHTTPBuffer(buffer, sock, lambda: 1.0)
        with mock.patch.object(self.stage.select, "select") as wait:
            self.assertEqual(proxy.read(3), b"abc")
        wait.assert_not_called()
        self.assertEqual(buffer.read1.call_args_list, [mock.call(1), mock.call(2)])
        self.assertEqual(sock.settimeout.call_args_list, [mock.call(None)] * 2)


class TestAPIStreamDeltaContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage_prompt_generator_for_integration_test()

    def decode(self, payloads):
        stream = "\n\n".join("data: " + json.dumps(payload, ensure_ascii=False) for payload in payloads)
        return self.stage._decode_api_json(stream.encode("utf-8"), charset="utf-8", label="local SSE")

    def test_openai_native_deltas_preserve_repeated_and_prefix_related_content(self):
        pieces = ["a", "a", "ab", "aba", "aba"]
        parsed = self.decode([{"choices": [{"delta": {"content": text}}]} for text in pieces])
        self.assertEqual(parsed["choices"][0]["message"]["content"], "".join(pieces))

    def test_cumulative_message_snapshots_still_replace_their_prefix(self):
        parsed = self.decode([{"choices": [{"message": {"content": text}}]} for text in ["a", "ab", "abc", "abc"]])
        self.assertEqual(parsed["choices"][0]["message"]["content"], "abc")

    def test_dashscope_message_snapshots_still_merge_without_duplication(self):
        parsed = self.decode([{"output": {"choices": [{"message": {"content": text}}]}} for text in ["a", "ab", "abc"]])
        self.assertEqual(parsed["output"]["choices"][0]["message"]["content"], "abc")

    def test_gemini_native_parts_preserve_legitimate_repetition(self):
        parsed = self.decode([{"candidates": [{"content": {"parts": [{"text": text}]}}]} for text in ["很", "很", "好"]])
        self.assertEqual(parsed["candidates"][0]["content"]["parts"][0]["text"], "很很好")

    def test_openai_responses_typed_deltas_append_without_content_deduplication(self):
        parsed = self.decode([{"type": "response.output_text.delta", "delta": text} for text in ["go", "go", "go"]])
        self.assertEqual(parsed["delta"], "gogogo")

    def test_ollama_native_message_and_response_deltas_preserve_repetition(self):
        for field in ("message", "response"):
            with self.subTest(field=field):
                def payload(text, done=False):
                    return {field: {"content": text} if field == "message" else text, "done": done}
                parsed = self.decode([payload("ha"), payload("ha"), payload("", True)])
                text = parsed["message"]["content"] if field == "message" else parsed["response"]
                self.assertEqual(text, "haha")


if __name__ == "__main__":
    unittest.main()
