"""Local negation must not erase the visible facts in an image requirement."""
from __future__ import annotations

from collections import OrderedDict
import unittest

from test_stage_prompt_modules import prompt_builder, uniq


class TestImageRequirementPolarity(unittest.TestCase):
    def build(self, requirement, *, language="纯英文", custom=False):
        settings = {
            "模板风格": "真实感", "主体类型": "人物角色",
            "案例输出结构": "案例长段版", "标签反推模式": "自动平衡",
            "生成数量": 1, "运行时随机标签": False,
            "提示词语言": language, "额外要求": "" if custom else requirement,
        }
        prompts = prompt_builder.build_prompt_list(
            OrderedDict({"主体": ["an adult traveler"], "场景背景": ["an old station"]}),
            [requirement] if custom else [], settings, uniq=uniq,
            infer_template_style=lambda _tags, explicit: explicit,
            infer_subject_type=lambda _tags, explicit: explicit,
            infer_output_structure=lambda _subject, explicit: explicit,
        )
        return prompts[0], settings

    def test_embedded_negation_preserves_the_complete_visual_requirement(self):
        for requirement in (
            "A traveler without a hat carries a blue backpack.",
            "A traveler carries a blue backpack with no logo.",
            "A traveler has no hat and carries a blue backpack.",
        ):
            for custom in (False, True):
                with self.subTest(requirement=requirement, custom=custom):
                    prompt, settings = self.build(requirement, custom=custom)
                    self.assertIn(requirement, prompt)
                    self.assertEqual(settings["图像提示词待翻译锚点"], [])

    def test_fronted_without_descriptor_stays_attached_to_its_visual_sentence(self):
        for requirement in (
            "Without a hat, a traveler carries a blue backpack.",
            "Without a hat the traveler carries a blue backpack.",
            "Without a hat, she carries a blue backpack.",
        ):
            with self.subTest(requirement=requirement):
                cleaned = prompt_builder._strip_negative_constraint_clauses(requirement)
                self.assertIn("Without a hat", cleaned)
                self.assertIn("carries a blue backpack", cleaned)
                prompt, _ = self.build(requirement)
                self.assertIn("Without a hat", prompt)
                self.assertIn("carries a blue backpack", prompt)

    def test_chinese_local_negation_keeps_positive_and_absent_facts(self):
        requirement = "旅人不戴帽子，左手提着蓝色背包"
        prompt, settings = self.build(requirement)
        self.assertIn("旅人不戴帽子", prompt)
        self.assertIn("左手提着蓝色背包", prompt)
        self.assertTrue(settings["图像提示词待翻译锚点"])

    def test_standalone_negative_constraints_do_not_become_positive_props(self):
        for requirement in (
            "no torch", "without a torch", "no watermark", "without watermark",
            "不要二次元", "避免上下分屏和重复脸", "画面中不要多人",
        ):
            with self.subTest(requirement=requirement):
                self.assertEqual(prompt_builder._strip_negative_constraint_clauses(requirement), "")
        prompt, _ = self.build("A traveler without a torch carries a blue backpack.")
        self.assertIn("without a torch", prompt)
        self.assertIn("blue backpack", prompt)
        self.assertNotIn("with a torch", prompt)
        self.assertNotIn("holding a torch", prompt)

    def test_technical_negatives_are_removed_without_dropping_neighboring_facts(self):
        self.assertEqual(
            prompt_builder._strip_negative_constraint_clauses("piano performance, no watermark"),
            "piano performance",
        )
        self.assertEqual(
            prompt_builder._strip_negative_constraint_clauses("不要二次元，不要水彩线稿，保持真实摄影。"),
            "保持真实摄影",
        )
        cleaned = prompt_builder._strip_negative_constraint_clauses(
            "A traveler without a hat carries a blue backpack, no watermark",
        )
        self.assertIn("without a hat", cleaned)
        self.assertIn("blue backpack", cleaned)
        self.assertNotIn("watermark", cleaned)


if __name__ == "__main__":
    unittest.main()
