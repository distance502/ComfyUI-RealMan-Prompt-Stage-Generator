# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import threading
import types
import unittest
from unittest import mock

from test_stage_prompt_modules import load_stage_prompt_generator_for_integration_test


class _Interrupted(RuntimeError):
    pass


class TestImageReverseRuntimeReliability(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_stage_prompt_generator_for_integration_test()
        self.model = types.SimpleNamespace(
            llm=types.SimpleNamespace(model_path="offline-reference-vision.gguf")
        )
        self.mm = types.SimpleNamespace(
            processing_interrupted=lambda: False,
            InterruptProcessingException=_Interrupted,
        )
        for patcher in (
            mock.patch.object(self.module, "_comfy_mm", self.mm),
            mock.patch.object(
                self.module,
                "_批量帧索引转data_url",
                return_value={0: "data:image/png;base64,offline-reference"},
            ),
            mock.patch.object(
                self.module,
                "_清洗think块文本",
                side_effect=lambda text: re.sub(
                    r"<think\b[^>]*>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE
                ),
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def settings() -> dict:
        return {"图片反推生成": True, "seed": 123}

    def assert_no_cached_flight(self) -> None:
        self.assertEqual(self.module._IMAGE_REVERSE_CACHE, {})
        self.assertEqual(self.module._IMAGE_REVERSE_INFLIGHT, {})

    def run_shared_call(self, *, content: str = "", error: BaseException | None = None):
        """Join a real follower before releasing an entirely offline leader."""
        module = self.module
        follower_joined = threading.Event()
        original_begin = module._begin_image_reverse_singleflight
        settings = [self.settings(), self.settings()]
        results = [None, None]
        errors = [None, None]

        def observed_begin(*args, **kwargs):
            result = original_begin(*args, **kwargs)
            if result[0] == "wait":
                follower_joined.set()
            return result

        def fake_chat(_llm, *, messages, params):
            if not follower_joined.wait(2.0):
                raise AssertionError("offline follower did not join the leader")
            if error is not None:
                raise error
            return {"choices": [{"message": {"content": content}}]}

        def worker(index):
            try:
                results[index] = module._apply_image_reverse_to_settings(
                    self.model, object(), settings[index]
                )
            except BaseException as exc:
                errors[index] = exc

        with (
            mock.patch.object(module, "_begin_image_reverse_singleflight", side_effect=observed_begin),
            mock.patch.object(module, "_调用chat_completion", side_effect=fake_chat) as chat,
        ):
            threads = [threading.Thread(target=worker, args=(index,)) for index in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(3.0)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertTrue(follower_joined.is_set())
            self.assertEqual(chat.call_count, 1)
        return settings, results, errors

    def test_explicit_interruption_escapes_after_global_flag_was_reset(self) -> None:
        module = self.module
        settings = self.settings()
        cancellation = _Interrupted("explicit cancellation after reset")
        with (
            mock.patch.object(module, "_reverse_reference_image", side_effect=cancellation),
            mock.patch.object(module, "_record_model_call_result_impl") as record,
        ):
            with self.assertRaises(_Interrupted) as raised:
                module._apply_image_reverse_to_settings(self.model, object(), settings)
        self.assertIs(raised.exception, cancellation)
        record.assert_not_called()
        self.assertEqual(settings["图片反推错误"], "")

    def test_interruption_while_waiting_for_a_flight_escapes_entry(self) -> None:
        module = self.module
        flight = module._ImageReverseInFlight()
        settings = self.settings()
        self.mm.processing_interrupted = mock.Mock(side_effect=(False, True))
        with (
            mock.patch.object(module, "_begin_image_reverse_singleflight", return_value=("wait", None, flight)),
            mock.patch.object(module, "_COOPERATIVE_WAIT_POLL_SECONDS", 0.001),
            mock.patch.object(module, "_调用chat_completion") as chat,
            mock.patch.object(module, "_record_model_call_result_impl") as record,
        ):
            with self.assertRaises(_Interrupted):
                module._apply_image_reverse_to_settings(self.model, object(), settings)
        chat.assert_not_called()
        record.assert_not_called()
        self.assertFalse(flight.event.is_set())

    def test_cancelled_leader_propagates_to_follower_without_failure_or_cache(self) -> None:
        cancellation = _Interrupted("backend consumed the global interrupt flag")
        settings, results, errors = self.run_shared_call(error=cancellation)
        self.assertEqual(results, [None, None])
        self.assertTrue(all(error is cancellation for error in errors))
        for state in settings:
            self.assertEqual(state.get("模型调用失败次数", 0), 0)
            self.assertEqual(state["图片反推错误"], "")
            self.assertFalse(state["图片反推缓存命中"])
        self.assert_no_cached_flight()

    def test_live_interruption_after_backend_return_discards_successful_text(self) -> None:
        module = self.module
        cancelled = {"value": False}
        self.mm.processing_interrupted = lambda: cancelled["value"]
        settings = self.settings()

        def fake_chat(_llm, *, messages, params):
            cancelled["value"] = True
            return {"choices": [{"message": {"content": "黄铜外壳与可见齿轮。"}}]}

        with mock.patch.object(module, "_调用chat_completion", side_effect=fake_chat):
            with self.assertRaises(_Interrupted):
                module._apply_image_reverse_to_settings(self.model, object(), settings)
        self.assertEqual(settings.get("模型调用失败次数", 0), 0)
        self.assert_no_cached_flight()

    def test_empty_cleaned_body_fails_for_leader_and_follower_and_next_call_retries(self) -> None:
        module = self.module
        settings, results, errors = self.run_shared_call(content="<think>analysis only</think>")
        self.assertEqual(results, ["", ""])
        self.assertEqual(errors, [None, None])
        for state in settings:
            self.assertEqual(state["图片反推状态"], "调用失败，已回退")
            self.assertEqual(state["模型调用失败次数"], 1)
            self.assertFalse(state["图片反推缓存命中"])
            self.assertIn("清洗后没有有效描述", state["图片反推错误"])
        self.assertEqual(settings[0]["图片反推错误"], settings[1]["图片反推错误"])
        self.assert_no_cached_flight()

        valid_text = "机械钟表的黄铜外壳包围可见齿轮。"
        retry_settings = self.settings()
        cached_settings = self.settings()
        with mock.patch.object(
            module,
            "_调用chat_completion",
            return_value={"choices": [{"message": {"content": valid_text}}]},
        ) as chat:
            self.assertEqual(
                module._apply_image_reverse_to_settings(self.model, object(), retry_settings),
                valid_text,
            )
            self.assertEqual(
                module._apply_image_reverse_to_settings(self.model, object(), cached_settings),
                valid_text,
            )
        self.assertEqual(chat.call_count, 1)
        self.assertEqual(retry_settings["图片反推状态"], "调用成功")
        self.assertEqual(cached_settings["图片反推状态"], "缓存命中")
        self.assertTrue(cached_settings["图片反推缓存命中"])

    def test_empty_cache_hit_is_validated_before_success_status(self) -> None:
        module = self.module
        settings = self.settings()

        def invalid_cached_result(_model, _image, state):
            state["图片反推缓存命中"] = True
            return " \n "

        with mock.patch.object(module, "_reverse_reference_image", side_effect=invalid_cached_result):
            self.assertEqual(module._apply_image_reverse_to_settings(self.model, object(), settings), "")
        self.assertEqual(settings["图片反推状态"], "调用失败，已回退")
        self.assertFalse(settings["图片反推缓存命中"])
        self.assertEqual(settings["模型调用失败次数"], 1)

    def test_ordinary_backend_failure_still_falls_back(self) -> None:
        settings = self.settings()
        with mock.patch.object(
            self.module, "_调用chat_completion", side_effect=RuntimeError("offline backend failure")
        ):
            result = self.module._apply_image_reverse_to_settings(self.model, object(), settings)
        self.assertEqual(result, "")
        self.assertEqual(settings["图片反推状态"], "调用失败，已回退")
        self.assertEqual(settings["模型调用失败次数"], 1)
        self.assertIn("offline backend failure", settings["图片反推错误"])
        self.assert_no_cached_flight()
