"""The sheet-generation entry point preserves explicitly non-human subjects."""
from __future__ import annotations

from collections import OrderedDict
import json
import unittest
from unittest import mock

from test_stage_prompt_modules import load_stage_prompt_generator_for_integration_test


class TestNonPersonSheetStrategy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_stage_prompt_generator_for_integration_test()

    def assert_structural(self, text):
        for word in ("人物高度", "头顶线", "五官", "正脸", "脸型", "发型", "服装", "站姿", "肤质"):
            self.assertNotIn(word, text)

    def test_strategy_preserves_object_type_and_structural_state(self):
        for english in (False, True):
            with self.subTest(english=english):
                settings = {
                    "主体类型": "非人物主体", "图片反推生成": True,
                    "提示词语言": "纯英文" if english else "纯中文",
                }
                selected = OrderedDict({"主体": ["机械钟表"], "服装造型": ["黄铜外壳"]})
                self.assertTrue(self.module._apply_character_sheet_to_settings(settings, selected, []))
                self.assertEqual(settings["主体类型"], "非人物主体")
                self.assertNotEqual(selected["动作姿态"], ["中性自然站姿"])
                self.assertFalse(settings.get("优先柔和肤质", False))
                for key in ("智能文本输入", "额外要求", "角色设定图内部策略"):
                    self.assert_structural(settings[key])
                brief = settings["额外要求"]
                self.assertIn("1:1:1", brief)
                self.assertIn("component count" if english else "部件数量", brief)
                cues = self.module._strict_special_variation_cues(settings, english=english)
                self.assertTrue(cues)
                for cue in cues:
                    self.assert_structural(cue)
                    self.assertNotIn("wardrobe", cue)
                    self.assertNotIn("stance", cue)

    def test_reference_features_and_user_facts_remain_in_structural_seed(self):
        selected = OrderedDict({"主体": ["机械钟表"]})
        settings = {
            "主体类型": "非人物主体", "图片反推生成": True,
            "智能文本输入": "保留圆形表盘", "额外要求": "黄铜外壳",
        }
        self.module._apply_character_sheet_to_settings(
            settings, selected, [], has_reference_image=True,
            image_reverse_text="主体：机械钟表；材质：黄铜；背景：木桌与红色窗帘",
        )
        for fact in ("机械钟表", "圆形表盘", "黄铜"):
            self.assertIn(fact, settings["智能文本输入"])
        for key in ("智能文本输入", "额外要求"):
            self.assertNotIn("木桌", settings[key])
            self.assertNotIn("红色窗帘", settings[key])
            self.assert_structural(settings[key])

    def test_reverse_request_describes_geometry_in_both_modes(self):
        for mode in ("角色设定图", "仅反推描述"):
            with self.subTest(mode=mode):
                prompt = self.module._build_image_reverse_prompt({
                    "主体类型": "非人物主体", "图片反推模式": mode,
                })
                self.assert_structural(prompt)
                self.assertIn("几何结构", prompt)
                if mode == "角色设定图":
                    self.assertIn("90度", prompt)
                    self.assertIn("1:1:1", prompt)

    def test_description_only_does_not_silently_enable_sheet_mode(self):
        for subject_type in ("人物角色", "非人物主体"):
            with self.subTest(subject_type=subject_type):
                settings = {
                    "主体类型": subject_type, "图片反推生成": True,
                    "图片反推模式": "仅反推描述", "智能文本输入": "保留可见材质",
                }
                selected = OrderedDict({"场景背景": ["室内"], "动作姿态": ["保持当前状态"]})
                before_settings = dict(settings)
                before_tags = OrderedDict((key, list(values)) for key, values in selected.items())
                self.assertFalse(self.module._apply_character_sheet_to_settings(settings, selected, []))
                self.assertEqual(settings, before_settings)
                self.assertEqual(selected, before_tags)

    def test_description_only_still_passes_reference_facts_to_normal_smart_text(self):
        settings = {
            "主体类型": "非人物主体", "图片反推生成": True,
            "图片反推模式": "仅反推描述", "智能文本输入": "保留黄铜表壳",
        }
        selected = OrderedDict({"场景背景": ["木桌"], "动作姿态": ["保持当前状态"]})
        self.assertFalse(self.module._apply_character_sheet_to_settings(
            settings, selected, [], has_reference_image=True,
            image_reverse_text="机械钟表位于木桌上，背景可见红色窗帘。",
        ))
        self.assertTrue(settings["智能文本匹配"])
        for fact in ("黄铜表壳", "机械钟表", "木桌", "红色窗帘"):
            self.assertIn(fact, settings["智能文本输入"])
        self.assertEqual(settings["图片反推模式"], "仅反推描述")
        self.assertNotIn("角色设定图内部策略", settings)
        self.assertEqual(selected["场景背景"], ["木桌"])

    def test_description_only_reference_keeps_single_frame_contract_end_to_end(self):
        with mock.patch.object(self.module, "_reverse_reference_image", return_value="机械钟表位于木桌上，黄铜外壳清晰可见。"):
            outputs = self.module._run_stage(None, **{
                "主体类型": "非人物主体", "主体标签1": "机械钟表",
                "服装造型标签1": "黄铜外壳", "场景背景标签1": "木桌",
                "模型来源": "仅Skill", "图片反推生成": True, "图片反推模式": "仅反推描述",
                "参考图片": object(), "运行时随机标签": False, "生成数量": 1, "seed": 51,
            })
        payload = json.loads(outputs[3])
        self.assertEqual(payload["subject_type"], "非人物主体")
        self.assertEqual(payload["image_prompt_contract"]["layout_mode"], "single_non_person")
        self.assertIn("机械钟表", outputs[1])
        self.assertIn("木桌", outputs[1])
        self.assertNotIn("1:1:1", outputs[1])
        self.assertNotIn("中性自然站姿", outputs[1])

    def test_sheet_entry_point_stays_non_person_end_to_end(self):
        for mode in ("reverse_switch", "text_intent"):
            with self.subTest(mode=mode):
                settings = {
                    "主体类型": "非人物主体", "主体标签1": "机械钟表",
                    "服装造型标签1": "黄铜外壳", "模型来源": "仅Skill",
                    "运行时随机标签": False, "生成数量": 1, "seed": 41,
                    "额外要求": "机械钟表三视图" if mode == "text_intent" else "",
                    "图片反推生成": mode == "reverse_switch",
                    "图片反推模式": "角色设定图",
                }
                outputs = self.module._run_stage(None, **settings)
                payload = json.loads(outputs[3])
                self.assertEqual(payload["subject_type"], "非人物主体")
                self.assertEqual(payload["image_prompt_contract"]["layout_mode"], "multi_view")
                self.assertIn("机械钟表", outputs[1])
                self.assertIn("黄铜外壳", outputs[1])
                self.assertIn("1:1:1", outputs[1])
                self.assert_structural(outputs[1])
                self.assert_structural("、".join(payload["selected_tags_flat"]))
                self.assert_structural(outputs[7])
