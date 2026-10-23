"""Object and architectural three-view references must not acquire human anatomy."""
from __future__ import annotations

import json
import unittest
from collections import OrderedDict

from test_stage_prompt_modules import load_stage_prompt_generator_for_integration_test, narrative, prompt_builder, uniq


HUMAN_ONLY_ZH = ("人物等高", "服装", "发型", "五官", "正脸", "握持", "手势", "站姿", "头脚", "肢体", "鼻颌", "身体侧", "角色设计")
HUMAN_ONLY_EN = ("frontal face", "wardrobe", "hairstyle", "anatomy", "body build", "hand position", "limb", "neutral stance", "full-body", "head-to-foot", "character design", "nose-jaw", "garment", "grip position")
TARGETS = ("通用", "Flux", "SDXL", "Qwen Image", "Krea 2", "Midjourney", "自定义", "FLUX.3", "FLUX.3 Klein", "FLUX.2", "MOSS Image", "Qwen Image 2.1", "Qwen Image 2.1 Turbo", "Qwen Image 2512", "Qwen Image Edit 2511", "Qwen Image 3.0", "Wan 2.7 Image", "Gemini Image")
SUBJECTS = (
    ("机械钟表", "a mechanical clock", "黄铜外壳", "a brass casing"),
    ("石砌钟楼", "a stone clock tower", "石砌承重结构", "load-bearing stonework"),
)


class TestNonPersonMultiView(unittest.TestCase):
    def assert_non_person_layout(self, text, *, english):
        self.assertTrue(narrative.prompt_preserves_visual_layout(text, "multi_view"), text)
        self.assertTrue(narrative.prompt_preserves_visual_layout(text, "multi_view", non_person=True), text)
        for forbidden in HUMAN_ONLY_EN if english else HUMAN_ONLY_ZH:
            self.assertNotIn(forbidden, text.casefold())
        for required in (("front at 0 degrees", "side profile at 90 degrees", "back at 180 degrees", "1:1:1", "overall height", "orthographic") if english else ("正面视图0度", "90度标准侧面", "背面视图180度", "1:1:1", "整体等高", "正交投影")):
            self.assertIn(required, text)

    def test_contract_is_subject_aware_without_changing_person_default(self):
        for english in (False, True):
            with self.subTest(english=english):
                default = narrative.visual_layout_contract("multi_view", english=english)
                explicit_person = narrative.visual_layout_contract("multi_view", english=english, non_person=False)
                self.assertEqual(default, explicit_person)
                self.assertIn("clear frontal face" if english else "正脸清晰", default)
                self.assert_non_person_layout(narrative.visual_layout_contract("multi_view", english=english, non_person=True), english=english)

    def test_non_person_contract_remains_resolvable_without_saved_settings(self):
        for english in (False, True):
            with self.subTest(english=english):
                contract = narrative.visual_layout_contract("multi_view", english=english, non_person=True)
                self.assertEqual(narrative.resolve_visual_layout_mode([contract], non_person=True), "multi_view")
                for mode in ("single_person", "single_non_person", "multi_subject"):
                    self.assertEqual(
                        narrative.visual_layout_contract(mode, english=english),
                        narrative.visual_layout_contract(mode, english=english, non_person=True),
                    )

    def test_bare_three_view_tag_reaches_stage_output_without_negation_regression(self):
        self.assertEqual(narrative.resolve_visual_layout_mode(["三视图"], non_person=True), "multi_view")
        for negated in ("不要三视图", "不能生成三视图", "避免三视图", "排除三视图"):
            with self.subTest(negated=negated):
                self.assertEqual(narrative.resolve_visual_layout_mode([negated], non_person=True), "single_non_person")
        self.assertEqual(narrative.resolve_visual_layout_mode(["不要水印，输出三视图"], non_person=True), "multi_view")
        stage = load_stage_prompt_generator_for_integration_test()
        result = stage._run_stage(None, **{
            "模型来源": "仅Skill", "主体类型": "非人物主体", "主体标签1": "机械钟表",
            "服装造型标签1": "黄铜外壳", "构图视角标签1": "三视图",
            "图像提示词目标模型": "MOSS Image", "生成数量": 1,
        })
        payload = json.loads(result[3])
        self.assertEqual(payload["image_prompt_target_profile"]["layout_mode"], "multi_view")
        self.assert_non_person_layout(result[1], english=False)
        self.assertIn("机械钟表", result[1])

    def test_renderers_keep_every_family_object_and_architecture_subject_aware(self):
        for target in TARGETS:
            family = prompt_builder.resolve_image_prompt_target_profile({"图像提示词目标模型": target}).get("family", target)
            for subject_zh, subject_en, material_zh, material_en in SUBJECTS:
                for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
                    english = language != "纯中文"
                    anchors = {
                        "subject": subject_en if english else subject_zh,
                        "outfit": material_en if english else material_zh,
                        "image_target": family,
                        "layout_mode": "multi_view",
                        "custom": "one circular opening" if english else "一处圆形开口",
                    }
                    for detail in ("简洁", "标准", "详细"):
                        with self.subTest(target=target, subject=subject_zh, language=language, detail=detail):
                            text = narrative.render_narrative_prompt(anchors, {}, language=language, non_person=True, detail_level=detail)
                            self.assert_non_person_layout(text, english=english)
                            self.assertIn(anchors["subject"], text)
                            self.assertIn(anchors["outfit"], text)
                            self.assertIn(anchors["custom"], text)

    def test_builder_routes_non_person_views_without_creating_a_story_plan(self):
        for target in ("通用", "FLUX.3", "FLUX.3 Klein", "MOSS Image", "Qwen Image 2.1"):
            for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
                with self.subTest(target=target, language=language):
                    english = language != "纯中文"
                    subject = "a mechanical clock" if english else "机械钟表"
                    selected = OrderedDict({
                        "主体": [subject],
                        "服装造型": ["a brass casing" if english else "黄铜外壳"],
                        "构图视角": ["front view", "side view", "back view"] if english else ["正面视图", "侧面视图", "背面视图"],
                    })
                    settings = {
                        "图像提示词目标模型": target, "主体类型": "非人物主体", "模板风格": "真实感",
                        "案例输出结构": "案例长段版", "生成数量": 1, "标签反推模式": "自动平衡",
                        "额外要求": "", "提示词语言": language, "运行时随机标签": False,
                    }
                    text = prompt_builder.build_prompt_list(
                        selected, [], settings, scene_group="", identity="", style_track="", recent_tracks=[], uniq=uniq,
                        infer_template_style=lambda _tags, explicit: explicit,
                        infer_subject_type=lambda _tags, explicit: explicit,
                        infer_output_structure=lambda _subject, explicit: explicit,
                    )[0]
                    main_text = text.split("\n中文说明：", 1)[0]
                    self.assert_non_person_layout(main_text, english=english)
                    self.assertIn(subject, main_text)
                    self.assertEqual(settings["画面结构模式解析结果"], "multi_view")
                    self.assertEqual(settings["图像提示词目标模型Profile"]["prompt_order"][0], "layout_contract")
                    self.assertEqual(settings["全局剧情规划"], [])

    def test_object_validation_keeps_angles_and_ratio_required(self):
        for english in (False, True):
            contract = narrative.visual_layout_contract("multi_view", english=english, non_person=True)
            for old in (("front at 0 degrees", "one true side profile at 90 degrees", "back at 180 degrees") if english else ("正面视图0度", "90度标准侧面", "背面视图180度")):
                with self.subTest(english=english, removed=old):
                    self.assertFalse(narrative.prompt_preserves_visual_layout(contract.replace(old, "omitted"), "multi_view", non_person=True))
            no_ratio = contract.replace("1:1:1", "").replace("three equal-width columns", "columns").replace("三栏等宽", "三栏")
            self.assertFalse(narrative.prompt_preserves_visual_layout(no_ratio, "multi_view", non_person=True))

    def test_person_validation_still_requires_a_frontal_face(self):
        text = "three-view reference: front at 0 degrees, side profile at 90 degrees, back at 180 degrees, three equal-width columns, 1:1:1."
        self.assertFalse(narrative.prompt_preserves_visual_layout(text, "multi_view"))
        self.assertTrue(narrative.prompt_preserves_visual_layout(text, "multi_view", non_person=True))
        self.assertTrue(narrative.prompt_preserves_visual_layout(text + " clear frontal face.", "multi_view"))
        for english in (False, True):
            with self.subTest(english=english):
                mislabeled_person = narrative.visual_layout_contract("multi_view", english=english, non_person=True)
                self.assertFalse(narrative.prompt_preserves_visual_layout(mislabeled_person, "multi_view", non_person=False))


if __name__ == "__main__":
    unittest.main()
