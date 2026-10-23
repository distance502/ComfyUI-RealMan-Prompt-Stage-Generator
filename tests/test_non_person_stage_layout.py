"""Stage-level three-view supplementation keeps object and human defaults separate."""
from __future__ import annotations

import json
import unittest

from test_stage_prompt_modules import load_stage_prompt_generator_for_integration_test


HUMAN_SHEET_DEFAULTS = (
    "正面全身", "标准侧面全身", "背面全身", "相同人物高度", "同一头顶线",
    "同一地面基线", "中性自然站姿", "全身完整入镜", "人物完整入镜",
)


class TestNonPersonStageLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_stage_prompt_generator_for_integration_test()

    def run_stage(self, **overrides):
        settings = {
            "模型来源": "仅Skill", "主体类型": "非人物主体", "主体标签1": "机械钟表",
            "服装造型标签1": "黄铜外壳", "构图视角标签1": "角色三视图",
            "图像提示词目标模型": "MOSS Image", "生成数量": 1,
            "运行时随机标签": False, "提示词语言": "纯中文", "seed": 41,
        }
        settings.update(overrides)
        outputs = self.module._run_stage(None, **settings)
        payload = json.loads(outputs[3])
        self.assertEqual(payload["model_call_attempt_count"], 0)
        self.assertEqual(payload["model_source_effective"], "仅Skill")
        return outputs, payload

    def test_non_person_three_view_defaults_are_structural_end_to_end(self):
        for composition in ("三视图", "角色三视图"):
            for smart in (False, True):
                with self.subTest(composition=composition, smart=smart):
                    outputs, payload = self.run_stage(**{
                        "构图视角标签1": composition,
                        "智能文本匹配": smart,
                        "智能文本输入": "一只机械钟表，黄铜外壳，圆形表盘，齿轮与底座结构清晰。" if smart else "",
                    })
                    self.assertEqual(payload["subject_type"], "非人物主体")
                    self.assertEqual(payload["image_prompt_contract"]["layout_mode"], "multi_view")
                    self.assertEqual(payload["image_prompt_contract"]["layout_priority"], "hard_first")
                    self.assertIn("黄铜外壳", outputs[1])
                    self.assertIn("机械钟表", outputs[1])
                    for tag in HUMAN_SHEET_DEFAULTS:
                        self.assertNotIn(tag, payload["selected_tags_flat"])
                        self.assertNotIn(tag, outputs[1])
                    if composition == "角色三视图":
                        for tag in ("相同主体高度", "同一顶端基准线", "同一底部基准线", "一致结构状态", "主体整体完整入镜"):
                            self.assertIn(tag, payload["selected_tags_flat"])
                    for marker in ("三视图", "三栏", "1:1:1", "正交投影"):
                        self.assertNotIn(marker, outputs[7])

    def test_non_person_supplementation_retains_explicit_human_wording(self):
        explicit = ("中性自然站姿", "同一头顶线", "人物完整入镜")
        _, payload = self.run_stage(**{
            "动作姿态标签1": explicit[0],
            "构图视角标签2": explicit[2],
            "自定义补充标签": explicit[1],
        })
        for tag in explicit:
            self.assertIn(tag, payload["selected_tags_flat"])

    def test_human_three_view_defaults_are_unchanged(self):
        outputs, payload = self.run_stage(**{
            "主体类型": "人物角色", "主体标签1": "成年女性侦探", "服装造型标签1": "深色风衣",
        })
        self.assertEqual(payload["subject_type"], "人物角色")
        self.assertEqual(payload["image_prompt_contract"]["layout_mode"], "multi_view")
        for tag in HUMAN_SHEET_DEFAULTS[:-1]:
            self.assertIn(tag, payload["selected_tags_flat"])
        self.assertIn("正脸", outputs[1])
