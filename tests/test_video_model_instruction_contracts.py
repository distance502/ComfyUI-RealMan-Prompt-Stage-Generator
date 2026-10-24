"""Resolved video model instructions must not contradict the active shot contract."""
from __future__ import annotations

import unittest

from test_stage_prompt_modules import model_refiner, video_prompt_skill


class TestVideoModelInstructionContracts(unittest.TestCase):
    def resolve(self, *, count="标准剧情", timeline=False, source="API接口", language="纯中文"):
        settings = {
            "模型任务": "视频提示词", "模型来源": source, "内置模型系列": "Llama",
            "提示词语言": language, "视频提示词镜头段数": count,
            "视频提示词目标模型": "H3", "视频提示词启用时间轴": timeline,
            "视频提示词模型系统提示": video_prompt_skill.VIDEO_PROMPT_MODEL_SYSTEM_TEMPLATE,
        }
        settings["视频提示词Profile"] = video_prompt_skill.resolve_video_prompt_profile(settings)
        return model_refiner._resolve_system_prompt(settings)

    def test_single_shot_has_no_conflicting_minimum_paragraph_count(self):
        for source in ("API接口", "本地模型"):
            with self.subTest(source=source):
                system = self.resolve(count="单镜头", source=source)
                self.assertIn("只输出恰好一段行动镜头", system)
                self.assertNotIn("输出至少三段分镜", system)
                self.assertIn("镜头段数合同", system)

    def test_multi_shot_instructions_keep_the_exact_requested_count(self):
        for count, number in (("短动作", 3), ("标准剧情", 5), ("长剧情", 7)):
            with self.subTest(count=count):
                system = self.resolve(count=count)
                self.assertIn(f"只输出恰好 {number} 段连续分镜", system)
                self.assertNotIn("输出至少三段分镜", system)

    def test_timeline_permission_is_conditional_in_the_resolved_system_prompt(self):
        for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
            for count in ("单镜头", "标准剧情"):
                for enabled in (False, True):
                    with self.subTest(language=language, count=count, timeline=enabled):
                        system = self.resolve(count=count, timeline=enabled, language=language)
                        self.assertNotIn("正文仍不得写具体秒数或时长参数", system)
                        self.assertIn("时间轴未启用时", system)
                        self.assertIn("时间轴已启用时", system)
                        if enabled:
                            self.assertIn("每个分镜标题必须保留连续、互不重叠的时间段", system)
                            self.assertIn("0-2秒", system)
                            self.assertIn("0-2s", system)
                        else:
                            self.assertNotIn("时间轴已启用：", system)


if __name__ == "__main__":
    unittest.main()
