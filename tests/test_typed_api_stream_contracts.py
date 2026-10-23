"""Typed native API stream regressions without external requests."""
from __future__ import annotations

import json
import unittest
from unittest import mock

from test_stage_prompt_modules import load_stage_prompt_generator_for_integration_test


class TestTypedAPIStreamContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage_prompt_generator_for_integration_test()

    def invoke(self, kind, events):
        raw = "\n\n".join(
            f"event: {event.get('type', 'message')}\ndata: {json.dumps(event)}"
            for event in events
        ).encode("utf-8")
        model = self.stage._TEAPIChatModel({
            "provider": "Claude" if kind == "anthropic" else "OpenAI兼容",
            "kind": kind,
            "url": "https://offline.invalid/v1/" + ("messages" if kind == "anthropic" else "responses"),
            "model": "offline-model", "api_key": "offline-key", "timeout": 5,
        })
        with mock.patch.object(self.stage, "_api_uses_loopback_proxy", return_value=False):
            with mock.patch.object(self.stage, "_perform_api_http_request", return_value=(raw, "utf-8")) as request:
                result = model.create_chat_completion(messages=[{"role": "user", "content": "Describe the hall."}])
        request.assert_called_once()
        return result

    def visible(self, response):
        return self.stage._extract_model_response_text_impl(response)

    def test_anthropic_native_events_reach_adapter_and_extractor(self):
        result = self.invoke("anthropic", [
            {"type": "message_start", "message": {
                "id": "msg_offline", "type": "message", "role": "assistant", "content": [],
                "usage": {"input_tokens": 8, "output_tokens": 0},
            }},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            *[{"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}}
              for text in ["The torch ", "glows", "glows", " in the hall."]],
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
             "usage": {"output_tokens": 12}},
            {"type": "message_stop"},
        ])
        self.assertEqual(self.visible(result), "The torch glowsglows in the hall.")
        self.assertEqual(result["raw"]["stop_reason"], "end_turn")
        self.assertEqual(result["raw"]["usage"], {"input_tokens": 8, "output_tokens": 12})

    def test_anthropic_keeps_text_blocks_in_index_order_without_thoughts_or_tools(self):
        result = self.invoke("anthropic", [
            {"type": "message_start", "message": {"role": "assistant", "content": []}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "private"}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "private"}},
            {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "name": "search", "input": {}}},
            {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": '{"text":"tool"}'}},
            {"type": "content_block_start", "index": 3, "content_block": {"type": "text", "text": " second"}},
            {"type": "content_block_delta", "index": 3, "delta": {"type": "text_delta", "text": " view."}},
            {"type": "content_block_start", "index": 2, "content_block": {"type": "text", "text": "First view,"}},
            {"type": "ping"},
            {"type": "message_stop"},
        ])
        self.assertEqual(self.visible(result), "First view, second view.")

    def test_anthropic_single_text_delta_event_is_not_lost(self):
        result = self.invoke("anthropic", [
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "A stone hall."}},
        ])
        self.assertEqual(self.visible(result), "A stone hall.")

    def test_anthropic_empty_stream_preserves_stop_reason_in_error(self):
        with self.assertRaisesRegex(RuntimeError, "stop_reason=max_tokens"):
            self.invoke("anthropic", [
                {"type": "message_delta", "delta": {"stop_reason": "max_tokens"}},
                {"type": "message_stop"},
            ])

    def test_anthropic_server_error_after_partial_text_is_not_success(self):
        with self.assertRaisesRegex(RuntimeError, "overloaded"):
            self.invoke("anthropic", [
                {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Partial answer."}},
                {"type": "error", "error": {"type": "overloaded_error", "message": "Server overloaded"}},
            ])

    def test_responses_visible_deltas_exclude_reasoning_and_tool_arguments(self):
        result = self.invoke("openai_responses", [
            {"type": "response.created", "response": {"id": "resp_offline", "status": "in_progress", "output": []}},
            {"type": "response.reasoning_summary_text.delta", "delta": "private summary"},
            {"type": "response.reasoning_text.delta", "delta": "private thought"},
            {"type": "response.function_call_arguments.delta", "delta": '{"text":"tool"}'},
            *[{"type": "response.output_text.delta", "output_index": 1, "content_index": 0, "delta": text}
              for text in ["go", "go", " through the hall."]],
        ])
        self.assertEqual(self.visible(result), "gogo through the hall.")
        self.assertEqual(result["delta"], "gogo through the hall.")

    def test_responses_done_snapshot_is_authoritative_not_an_extra_delta(self):
        result = self.invoke("openai_responses", [
            {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "draft"},
            {"type": "response.output_text.done", "output_index": 0, "content_index": 0, "text": "A finished scene."},
            {"type": "response.completed", "response": {"status": "completed", "output": [
                {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "A finished scene."}]},
            ]}},
        ])
        self.assertEqual(self.visible(result), "A finished scene.")
        self.assertEqual(result["status"], "completed")

    def test_responses_completed_snapshot_alone_extracts_only_assistant_text(self):
        result = self.invoke("openai_responses", [
            {"type": "response.completed", "response": {"status": "completed", "output": [
                {"type": "reasoning", "summary": [{"type": "summary_text", "text": "private summary"}]},
                {"type": "function_call", "arguments": '{"text":"tool"}'},
                {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "A finished scene."}]},
            ]}},
        ])
        self.assertEqual(self.visible(result), "A finished scene.")

    def test_responses_interleaved_parts_keep_native_output_and_content_order(self):
        result = self.invoke("openai_responses", [
            {"type": "response.output_text.delta", "output_index": 2, "content_index": 1, "delta": " third"},
            {"type": "response.output_text.delta", "output_index": 1, "content_index": 0, "delta": "First"},
            {"type": "response.output_text.delta", "output_index": 2, "content_index": 0, "delta": " second"},
        ])
        self.assertEqual(self.visible(result), "First second third")

    def test_responses_content_part_and_item_snapshots_do_not_duplicate_text(self):
        result = self.invoke("openai_responses", [
            {"type": "response.content_part.added", "output_index": 0, "content_index": 0,
             "part": {"type": "output_text", "text": ""}},
            {"type": "response.output_text.delta", "output_index": 0, "content_index": 0, "delta": "A scene."},
            {"type": "response.content_part.done", "output_index": 0, "content_index": 0,
             "part": {"type": "output_text", "text": "A scene."}},
            {"type": "response.output_item.done", "output_index": 0, "item": {
                "type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "A scene."}],
            }},
        ])
        self.assertEqual(self.visible(result), "A scene.")

    def test_responses_failed_event_raises_even_after_visible_partial_output(self):
        for prefix in ([], [{"type": "response.output_text.delta", "delta": "Partial scene."}]):
            with self.subTest(partial=bool(prefix)), self.assertRaisesRegex(RuntimeError, "Generation aborted"):
                self.invoke("openai_responses", [*prefix, {
                    "type": "response.failed", "response": {
                        "status": "failed", "error": {"code": "server_error", "message": "Generation aborted"},
                    },
                }])

    def test_responses_generic_error_event_does_not_return_partial_success(self):
        with self.assertRaisesRegex(RuntimeError, "Generation aborted"):
            self.invoke("openai_responses", [
                {"type": "response.output_text.delta", "delta": "Partial scene."},
                {"type": "error", "code": "server_error", "message": "Generation aborted"},
            ])

    def test_responses_incomplete_visible_text_retains_original_status_and_reason(self):
        result = self.invoke("openai_responses", [
            {"type": "response.output_text.delta", "delta": "A visible scene."},
            {"type": "response.incomplete", "response": {
                "status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output": [],
            }},
        ])
        self.assertEqual(self.visible(result), "A visible scene.")
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["incomplete_details"], {"reason": "max_output_tokens"})

    def test_responses_reasoning_and_tool_only_stream_has_no_visible_text(self):
        result = self.invoke("openai_responses", [
            {"type": "response.reasoning_summary_text.delta", "delta": "private summary"},
            {"type": "response.function_call_arguments.delta", "delta": '{"text":"tool"}'},
        ])
        self.assertEqual(self.visible(result), "")

    def test_non_stream_response_envelopes_keep_existing_shape(self):
        payload = {"status": "incomplete", "output": [{
            "type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "A scene."}],
        }]}
        self.assertEqual(self.stage._decode_api_json(json.dumps(payload).encode(), charset="utf-8", label="offline"), payload)


if __name__ == "__main__":
    unittest.main()
