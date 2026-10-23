"""Offline regression coverage for model cancellation and final fallback status."""
from __future__ import annotations

import types
import unittest
from unittest import mock

from test_stage_prompt_modules import model_refiner


class Cancelled(Exception):
    pass


class SequenceModel:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class TestModelRefinerRuntimeReliability(unittest.TestCase):
    prompts = [
        "A mechanical clock turns slowly in an old station.",
        "A brass carriage rolls along the existing station rail.",
    ]
    bad_body = "分析：尚未形成最终正文。"

    def settings(self):
        return {
            "模型来源": "API接口", "提示词语言": "纯英文",
            "模型瞬时重试次数": 0, "模型输出修复重试次数": 0,
        }

    def run_entry(self, entry, model, settings):
        kwargs = {
            "chat_completion": lambda *args, **kwargs: None,
            "clean_think_text": lambda text: text,
        }
        if entry == "batch":
            return model_refiner.maybe_model_refine_batch(model, list(self.prompts), settings, **kwargs)
        if entry == "video":
            return model_refiner.maybe_model_refine_video(
                model, self.prompts[0], settings, validator=lambda *args, **kwargs: False, **kwargs,
            )
        return model_refiner.maybe_model_refine(model, self.prompts[0], settings, **kwargs)

    def test_successful_transports_with_rejected_bodies_remain_counted_as_fallbacks(self):
        settings = self.settings()
        model = SequenceModel("combined response without separator", self.bad_body, self.bad_body)
        result = self.run_entry("batch", model, settings)
        self.assertEqual(result, self.prompts)
        self.assertEqual(settings["模型调用成功次数"], 2)
        self.assertEqual(settings["模型调用失败次数"], 1)
        self.assertEqual(settings["模型活动回退数量"], 2)
        self.assertEqual(settings["模型调用采纳次数"], 0)
        self.assertEqual(settings["模型来源实际"], "仅Skill回退")
        self.assertIn("最终仍有 2 条回退 Skill", settings["模型调用状态"])
        self.assertIn("仍有 2/2 条", settings["模型回退说明"])
        self.assertFalse(any("最终无输出回退" in note for note in settings["推理纠偏说明"]))

    def test_mixed_retry_retains_existing_fallbacks_and_only_counts_rejected_item(self):
        settings = self.settings()
        settings.update({"模型活动回退数量": 4, "模型回退说明": "existing channel fallback"})
        candidate = "A mechanical clock turns slowly inside the same old station while side light crosses its brass casing."
        model = SequenceModel("combined response without separator", candidate, self.bad_body)
        result = self.run_entry("batch", model, settings)
        self.assertNotEqual(result[0], self.prompts[0])
        self.assertEqual(result[1], self.prompts[1])
        self.assertEqual(settings["模型活动回退数量"], 5)
        self.assertEqual(settings["模型调用采纳次数"], 1)
        self.assertIn("existing channel fallback", settings["模型回退说明"])
        self.assertIn("仍有 1/2 条", settings["模型回退说明"])
        self.assertEqual(settings["模型来源实际"], "API接口（部分回退）")

    def test_valid_unchanged_outputs_are_not_misclassified_as_rejected_bodies(self):
        settings = self.settings()
        result = self.run_entry(
            "batch", SequenceModel("combined response without separator", *self.prompts), settings,
        )
        self.assertEqual(result, self.prompts)
        self.assertEqual(settings["模型活动回退数量"], 0)
        self.assertEqual(settings["模型回退说明"], "")
        self.assertIn("最终无输出回退", settings["模型调用状态"])

    def test_preexisting_comfy_interruption_escapes_all_entrypoints(self):
        comfy = types.SimpleNamespace(processing_interrupted=lambda: True, InterruptProcessingException=Cancelled)
        for entry in ("single", "batch", "video"):
            with self.subTest(entry=entry):
                settings = self.settings()
                model = SequenceModel("must not execute")
                with mock.patch.object(model_refiner, "_comfy_mm", comfy), self.assertRaises(Cancelled):
                    self.run_entry(entry, model, settings)
                self.assertEqual(model.calls, 0)
                self.assertEqual(settings.get("模型调用失败次数", 0), 0)
                self.assertEqual(settings.get("模型活动回退数量", 0), 0)

    def test_backend_cancellation_escapes_even_if_global_flag_has_reset(self):
        comfy = types.SimpleNamespace(processing_interrupted=lambda: False, InterruptProcessingException=Cancelled)
        for entry in ("single", "batch", "video"):
            with self.subTest(entry=entry):
                settings = self.settings()
                cancellation = Cancelled("backend cancelled")
                with mock.patch.object(model_refiner, "_comfy_mm", comfy), self.assertRaises(Cancelled) as raised:
                    self.run_entry(entry, SequenceModel(cancellation), settings)
                self.assertIs(raised.exception, cancellation)
                self.assertEqual(settings.get("模型调用失败次数", 0), 0)
                self.assertEqual(settings.get("模型活动回退数量", 0), 0)

    def test_cancellation_during_repair_is_not_converted_to_skill_fallback(self):
        comfy = types.SimpleNamespace(processing_interrupted=lambda: False, InterruptProcessingException=Cancelled)
        for entry in ("single", "batch", "video"):
            with self.subTest(entry=entry):
                settings = self.settings()
                settings["模型输出修复重试次数"] = 1
                first = self.bad_body
                if entry == "batch":
                    first = model_refiner._BATCH_SEPARATOR.join([self.bad_body, self.bad_body])
                model = SequenceModel(first, Cancelled("repair cancelled"))
                with mock.patch.object(model_refiner, "_comfy_mm", comfy), self.assertRaisesRegex(Cancelled, "repair cancelled"):
                    self.run_entry(entry, model, settings)
                self.assertEqual(model.calls, 2)
                self.assertEqual(settings.get("模型调用失败次数", 0), 0)
                self.assertEqual(settings.get("模型活动回退数量", 0), 0)
                self.assertEqual(settings.get("模型输出修复重试次数实际", 0), 0)

    def test_cancellation_signalled_during_backend_call_blocks_adoption(self):
        state = {"cancelled": False}
        comfy = types.SimpleNamespace(
            processing_interrupted=lambda: state["cancelled"], InterruptProcessingException=Cancelled,
        )

        class InterruptingModel:
            def invoke(self, prompt):
                state["cancelled"] = True
                return "A mechanical clock turns in the same old station while light moves across its casing."

        for entry in ("single", "batch", "video"):
            with self.subTest(entry=entry):
                state["cancelled"] = False
                settings = self.settings()
                with mock.patch.object(model_refiner, "_comfy_mm", comfy), self.assertRaises(Cancelled):
                    self.run_entry(entry, InterruptingModel(), settings)
                self.assertEqual(settings.get("模型调用采纳次数", 0), 0)
                self.assertEqual(settings.get("模型活动回退数量", 0), 0)

    def test_normal_backend_errors_still_fall_back_for_all_entrypoints(self):
        comfy = types.SimpleNamespace(processing_interrupted=lambda: False, InterruptProcessingException=Cancelled)
        for entry in ("single", "batch", "video"):
            with self.subTest(entry=entry):
                settings = self.settings()
                with mock.patch.object(model_refiner, "_comfy_mm", comfy):
                    result = self.run_entry(entry, SequenceModel(RuntimeError("ordinary backend failure")), settings)
                self.assertEqual(result, self.prompts if entry == "batch" else self.prompts[0])
                self.assertEqual(settings["模型调用失败次数"], 1)
                self.assertEqual(settings["模型活动回退数量"], 2 if entry == "batch" else 1)
                self.assertIn("ordinary backend failure", settings["模型回退说明"])


if __name__ == "__main__":
    unittest.main()
