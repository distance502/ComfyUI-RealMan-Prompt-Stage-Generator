# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import pathlib
import tempfile
import threading
import types
import unittest
from unittest import mock

from test_stage_prompt_modules import load_plugin_init_for_integration_test


class TestCompanionBrowserUrl(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_plugin_init_for_integration_test()

    def test_public_http_urls_are_normalized(self) -> None:
        for raw, expected in (
            ("https://example.com", "https://example.com/"),
            ("http://example.com/path?q=1#part", "http://example.com/path?q=1#part"),
            ("https://8.8.8.8/dns", "https://8.8.8.8/dns"),
            ("https://[2606:4700:4700::1111]/dns", "https://[2606:4700:4700::1111]/dns"),
        ):
            normalized, error = self.module._normalize_companion_browser_url(raw)
            self.assertEqual(error, "", raw)
            self.assertEqual(normalized, expected, raw)

    def test_dangerous_and_non_public_urls_are_rejected(self) -> None:
        invalid_urls = (
            "",
            "example.com",
            "javascript:alert(1)",
            "file:///etc/passwd",
            "//example.com",
            "https://user:secret@example.com",
            "https://example.com:0",
            "https://example.com:65536",
            "https://example.com\\@127.0.0.1/",
            "https://localhost/",
            "https://router/",
            "https://router.local/",
            "https://127.0.0.1/",
            "https://127.1/",
            "https://2130706433/",
            "https://0177.0.0.1/",
            "https://0x7f000001/",
            "https://0x7f.0.0.1/",
            "https://0x7f.1/",
            "https://127.0x0.0.1/",
            "https://0x7f.0x0.0x0.0x1/",
            "https://0177.0x0.1/",
            "https://10.0.0.1/",
            "https://169.254.169.254/",
            "https://192.168.1.1/",
            "https://[::1]/",
            "https://[::ffff:127.0.0.1]/",
            "https://192.0.2.1/",
            "https://example.com/\nnext",
        )
        for raw in invalid_urls:
            normalized, error = self.module._normalize_companion_browser_url(raw)
            self.assertEqual(normalized, "", raw)
            self.assertTrue(error, raw)

    def test_url_length_is_bounded(self) -> None:
        normalized, error = self.module._normalize_companion_browser_url(
            "https://example.com/" + "x" * self.module._COMPANION_BROWSER_URL_MAX_CHARS
        )
        self.assertEqual(normalized, "")
        self.assertIn(str(self.module._COMPANION_BROWSER_URL_MAX_CHARS), error)


class TestCompanionBrowserLaunch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_plugin_init_for_integration_test()

    def test_explicit_browser_override_is_validated_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            edge = pathlib.Path(temp_dir) / "msedge.exe"
            edge.write_bytes(b"")
            with mock.patch.dict(self.module.os.environ, {"QWEN_TE_BROWSER_EXE": str(edge)}, clear=False):
                executable, family, error = self.module._find_companion_browser_executable()
            self.assertEqual(executable, edge.resolve())
            self.assertEqual(family, "Microsoft Edge")
            self.assertEqual(error, "")

            invalid = pathlib.Path(temp_dir) / "not-a-browser.exe"
            invalid.write_bytes(b"")
            with mock.patch.dict(self.module.os.environ, {"QWEN_TE_BROWSER_EXE": str(invalid)}, clear=False):
                executable, family, error = self.module._find_companion_browser_executable()
            self.assertIsNone(executable)
            self.assertEqual(family, "")
            self.assertIn("QWEN_TE_BROWSER_EXE", error)

    def test_process_launch_uses_fixed_argv_without_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            edge = root / "msedge.exe"
            edge.write_bytes(b"")
            profile = root / "profile"
            popen_result = types.SimpleNamespace(pid=4321)
            url = "https://example.com/?a=1&b=%22x%22"
            with (
                mock.patch.object(
                    self.module,
                    "_find_companion_browser_executable",
                    return_value=(edge, "Microsoft Edge", ""),
                ),
                mock.patch.object(
                    self.module,
                    "_companion_browser_profile_directory",
                    return_value=profile,
                ),
                mock.patch.object(
                    self.module.subprocess,
                    "Popen",
                    return_value=popen_result,
                ) as popen,
            ):
                detail = self.module._launch_companion_browser(url)

        self.assertEqual(detail, {"browser": "Microsoft Edge", "pid": 4321})
        args, kwargs = popen.call_args
        argv = args[0]
        self.assertIsInstance(argv, list)
        self.assertEqual(argv[0], str(edge))
        self.assertEqual(argv[-2:], ["--new-window", url])
        self.assertIn(f"--user-data-dir={profile}", argv)
        self.assertIn("--start-maximized", argv)
        self.assertNotIn("--no-sandbox", argv)
        self.assertNotIn("--disable-web-security", argv)
        self.assertNotIn("--remote-debugging-port", " ".join(argv))
        self.assertFalse(kwargs["shell"])
        self.assertIs(kwargs["stdin"], self.module.subprocess.DEVNULL)
        self.assertIs(kwargs["stdout"], self.module.subprocess.DEVNULL)
        self.assertIs(kwargs["stderr"], self.module.subprocess.DEVNULL)

    def test_launch_rate_limit_blocks_bursts_and_minute_floods(self) -> None:
        self.module._reset_companion_browser_launch_rate_limit_for_tests()
        self.assertEqual(self.module._reserve_companion_browser_launch(now=0.0), (True, 0.0))
        allowed, retry_after = self.module._reserve_companion_browser_launch(now=1.0)
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)
        self.assertEqual(self.module._reserve_companion_browser_launch(now=2.1), (True, 0.0))

        self.module._reset_companion_browser_launch_rate_limit_for_tests()
        for timestamp in (0.0, 2.1, 4.2, 6.3, 8.4):
            self.assertEqual(self.module._reserve_companion_browser_launch(now=timestamp), (True, 0.0))
        allowed, retry_after = self.module._reserve_companion_browser_launch(now=10.5)
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 40.0)


class TestCompanionBrowserRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_plugin_init_for_integration_test()

    def _request(self, url="https://example.com/", **overrides):
        headers = {
            "Content-Type": "application/json",
            "Origin": "http://127.0.0.1:8188",
            "Sec-Fetch-Site": "same-origin",
            "X-Qwen-TE-Companion-Browser": "1",
        }
        headers.update(overrides.pop("headers", {}))

        class Request:
            content_type = overrides.pop("content_type", "application/json")
            content_length = overrides.pop("content_length", 128)
            remote = overrides.pop("remote", "127.0.0.1")
            host = overrides.pop("host", "127.0.0.1:8188")
            scheme = overrides.pop("scheme", "http")

            async def json(self):
                return {"url": url}

        request = Request()
        request.headers = headers
        for name, value in overrides.items():
            setattr(request, name, value)
        return request

    def _register_handler(self):
        handlers = {}

        class Routes:
            def get(self, path):
                return lambda handler: handlers.setdefault(("GET", path), handler)

            def post(self, path):
                return lambda handler: handlers.setdefault(("POST", path), handler)

        prompt_server = types.SimpleNamespace(routes=Routes())
        self.module._get_prompt_server_class = lambda: types.SimpleNamespace(instance=prompt_server)
        self.assertTrue(self.module._register_tag_routes())
        return handlers[("POST", "/qwen_te/companion_browser/open")]

    def setUp(self) -> None:
        self.module._reset_companion_browser_launch_rate_limit_for_tests()

    def test_request_guard_requires_loopback_same_origin_json(self) -> None:
        self.assertIsNone(self.module._companion_browser_request_guard(self._request()))
        cases = (
            self._request(remote="192.168.1.4"),
            self._request(host="192.168.1.4:8188"),
            self._request(headers={"Origin": "https://evil.example"}),
            self._request(headers={"Sec-Fetch-Site": "cross-site"}),
            self._request(headers={"X-Qwen-TE-Companion-Browser": ""}),
            self._request(content_type="text/plain", headers={"Content-Type": "text/plain"}),
            self._request(content_length=self.module._COMPANION_BROWSER_REQUEST_MAX_BYTES + 1),
        )
        for request in cases:
            denial = self.module._companion_browser_request_guard(request)
            self.assertIsNotNone(denial)
            self.assertGreaterEqual(denial[0], 400)

    def test_route_launches_in_worker_thread_and_returns_browser_family(self) -> None:
        handler = self._register_handler()
        launch_threads = []

        def launch(url):
            launch_threads.append(threading.current_thread())
            self.assertEqual(url, "https://example.com/")
            return {"browser": "Microsoft Edge", "pid": 123}

        with (
            mock.patch.object(self.module, "_reserve_companion_browser_launch", return_value=(True, 0.0)),
            mock.patch.object(self.module, "_launch_companion_browser", side_effect=launch),
        ):
            response = self.module.asyncio.run(handler(self._request()))

        payload = json.loads(response.text)
        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["browser"], "Microsoft Edge")
        self.assertEqual(len(launch_threads), 1)
        self.assertIsNot(launch_threads[0], threading.current_thread())

    def test_route_reports_invalid_unavailable_and_throttled_requests(self) -> None:
        handler = self._register_handler()
        invalid = self.module.asyncio.run(handler(self._request("https://127.0.0.1/")))
        self.assertEqual(invalid.status, 400)

        with (
            mock.patch.object(self.module, "_reserve_companion_browser_launch", return_value=(True, 0.0)),
            mock.patch.object(
                self.module,
                "_launch_companion_browser",
                side_effect=self.module._CompanionBrowserUnavailable("没有找到可用浏览器。"),
            ),
        ):
            unavailable = self.module.asyncio.run(handler(self._request()))
        self.assertEqual(unavailable.status, 503)

        with mock.patch.object(self.module, "_reserve_companion_browser_launch", return_value=(False, 1.25)):
            throttled = self.module.asyncio.run(handler(self._request()))
        self.assertEqual(throttled.status, 429)
        self.assertEqual(throttled.headers["Retry-After"], "2")

    def test_route_stops_chunked_bodies_at_the_companion_limit(self) -> None:
        handler = self._register_handler()

        class Content:
            async def iter_chunked(self, _size):
                yield b'{"url":"https://example.com/'
                yield b"x" * self.module._COMPANION_BROWSER_REQUEST_MAX_BYTES

        request = self._request(content_length=None)
        request._read_bytes = None
        request.content = Content()
        request.content.module = self.module
        request.charset = "utf-8"
        with mock.patch.object(
            self.module,
            "_launch_companion_browser",
            side_effect=AssertionError("oversized request must not launch"),
        ):
            response = self.module.asyncio.run(handler(request))

        self.assertEqual(response.status, 413)
        self.assertFalse(json.loads(response.text)["ok"])


if __name__ == "__main__":
    unittest.main()
