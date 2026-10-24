"""Untranslated explicit requirements survive final image-output processing."""
from __future__ import annotations

import json
import unittest
from unittest import mock

from test_stage_prompt_modules import load_stage_prompt_generator_for_integration_test


class TestPromptLanguageFallbacks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_stage_prompt_generator_for_integration_test()

    def kwargs(self, language="纯英文", extra=""):
        return {
            "模型来源": "仅Skill", "模板风格": "真实感", "主体类型": "人物角色",
            "提示词语言": language, "运行时随机标签": False, "生成数量": 2, "seed": 41,
            "unique_id": self.id() + language + str(len(extra)),
            "主体标签1": "an adult traveler", "服装造型标签1": "a dark coat",
            "场景背景标签1": "an old station", "道具世界观标签1": "a folded map",
            "额外要求": extra,
        }

    def test_skill_only_keeps_untranslated_requirements_and_reports_actual_language(self):
        extra = "左手握着折叠测绘尺，右肩悬挂黄色工具包"
        for language in ("纯英文", "英文提示词+中文说明"):
            with self.subTest(language=language):
                outputs = self.module._run_stage(None, **self.kwargs(language, extra))
                payload = json.loads(outputs[3])
                self.assertIn("折叠测绘尺", outputs[1])
                self.assertIn("黄色工具包", outputs[1])
                self.assertEqual(payload["image_prompt_languages"], ["纯中文", "纯中文"])
                self.assertIn(extra, payload["image_prompt_translation_pending"])
                self.assertTrue(any("语言回退" in note for note in payload["normalization_notes"]))

    def test_model_receives_complete_source_before_english_output_is_accepted(self):
        module = self.module
        extra = "左手握着折叠测绘尺，右肩悬挂黄色工具包"
        baseline = json.loads(module._run_stage(None, **self.kwargs())[3])["prompt_list"]
        translated = [
            prompt + " The traveler holds a folding survey ruler in the left hand, with a yellow tool bag hanging from the right shoulder."
            for prompt in baseline
        ]

        def translate(_model, prompts, settings, **_kwargs):
            self.assertEqual(settings["提示词语言"], "纯英文")
            self.assertIn(extra, settings["图像提示词待翻译锚点"])
            self.assertTrue(all("折叠测绘尺" in prompt and "黄色工具包" in prompt for prompt in prompts))
            return translated

        with mock.patch.object(module, "_maybe_model_refine_batch_impl", side_effect=translate):
            outputs = module._run_stage(None, **self.kwargs(extra=extra))
        payload = json.loads(outputs[3])
        self.assertEqual(payload["image_prompt_languages"], ["纯英文", "纯英文"])
        self.assertEqual(payload["image_prompt_translation_pending"], [])
        self.assertIn("folding survey ruler", outputs[1])
        self.assertNotIn("折叠测绘尺", outputs[1])
        self.assertFalse(any("主提示词语言回退" in note for note in payload["normalization_notes"]))

    def test_unrelated_chinese_model_candidate_cannot_use_the_saved_language_fallback(self):
        extra = "左手握着折叠测绘尺，右肩悬挂黄色工具包"
        unrelated = "一名成年旅人在城市街道停下，随后望向远处的塔楼。因为钟声响起，他警觉地转身，镜头最终停在路口。"
        with mock.patch.object(self.module, "_maybe_model_refine_batch_impl", return_value=[unrelated, unrelated]):
            outputs = self.module._run_stage(None, **self.kwargs(extra=extra))
        payload = json.loads(outputs[3])
        self.assertNotIn("城市街道", outputs[1])
        self.assertIn("折叠测绘尺", outputs[1])
        self.assertIn("黄色工具包", outputs[1])
        self.assertEqual(payload["image_prompt_languages"], ["纯中文", "纯中文"])

    def test_known_english_input_does_not_trigger_language_fallback(self):
        outputs = self.module._run_stage(None, **self.kwargs())
        payload = json.loads(outputs[3])
        self.assertEqual(payload["image_prompt_languages"], ["纯英文", "纯英文"])
        self.assertEqual(payload["image_prompt_translation_pending"], [])

    def test_tag_block_fallback_keeps_free_text_and_block_order(self):
        free_text = "A blue ticket protrudes from the left coat pocket."
        kwargs = self.kwargs()
        kwargs.update({
            "服装造型标签1": "雾银菱纹披肩", "标签块编排启用": True,
            "标签块编排JSON": json.dumps({"enabled": True, "blocks": [
                {"type": "text", "text": free_text, "locked": True},
                {"type": "tags", "group": "服装造型", "tags": ["雾银菱纹披肩"]},
            ]}),
        })
        outputs = self.module._run_stage(None, **kwargs)
        payload = json.loads(outputs[3])
        self.assertIn(free_text, outputs[1])
        self.assertIn("雾银菱纹披肩", outputs[1])
        self.assertLess(outputs[1].find(free_text), outputs[1].find("服装造型围绕"))
        self.assertEqual(payload["image_prompt_languages"], ["纯中文", "纯中文"])

    def test_unknown_chinese_only_in_a_free_text_block_is_not_discarded(self):
        requirement = "左手握着折叠测绘尺，右肩悬挂黄色工具包"
        kwargs = self.kwargs()
        kwargs.update({
            "标签块编排启用": True,
            "标签块编排JSON": json.dumps({"enabled": True, "blocks": [
                {"type": "text", "text": requirement, "locked": True},
            ]}),
        })
        outputs = self.module._run_stage(None, **kwargs)
        payload = json.loads(outputs[3])
        self.assertIn("折叠测绘尺", outputs[1])
        self.assertIn("黄色工具包", outputs[1])
        self.assertIn(requirement, payload["image_prompt_translation_pending"])
        self.assertEqual(payload["image_prompt_languages"], ["纯中文", "纯中文"])


if __name__ == "__main__":
    unittest.main()
