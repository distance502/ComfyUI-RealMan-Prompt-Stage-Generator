"""Non-person smart-text turnarounds must describe geometry, not character anatomy."""
from __future__ import annotations

import re
import unittest
from unittest import mock

from test_stage_prompt_modules import narrative, smart_text


class TestNonPersonSmartMultiView(unittest.TestCase):
    def assert_non_person_design(self, text):
        for marker in ("正脸", "脸部", "体型", "发型", "服装", "站姿", "手势", "重心", "角色身份"):
            self.assertNotIn(marker, text)
        self.assertIsNone(re.search(r"\b(?:face|anatomy|hairstyle|wardrobe|stance)\b", text, re.IGNORECASE), text)

    def test_seed_uses_non_person_contract_and_design_dimensions_in_all_languages(self):
        for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
            for subject in ("铜制台灯", "履带式巡检机械", "砖砌钟楼"):
                with self.subTest(language=language, subject=subject):
                    settings = {
                        "提示词语言": language,
                        "主体类型": "非人物主体",
                        "画面结构模式解析结果": "multi_view",
                        "全局创作主线摘要": subject,
                    }
                    seed = smart_text.build_smart_text_seed(
                        user_text="补充黄铜连接件",
                        primary_prompt=subject,
                        selected_tags_text=subject,
                        settings=settings,
                    )
                    self.assert_non_person_design(seed)
                    self.assertIn("1:1:1", seed)
                    self.assertIn("部件数量", seed)
                    self.assertIn("全局实体设计主线", seed)
                    self.assertEqual(settings["画面结构模式解析结果"], "multi_view")

    def test_non_person_system_template_matches_resolved_subject_type(self):
        settings = smart_text.build_smart_text_settings({
            "主体类型": "自动",
            "主体类型解析结果": "非人物主体",
            "画面结构模式解析结果": "multi_view",
        })
        system = settings["系统提示词覆盖"]
        self.assertEqual(system, smart_text.SMART_TEXT_NON_PERSON_MULTI_VIEW_SYSTEM_TEMPLATE)
        self.assert_non_person_design(system)
        self.assertIn("普通器物、机械或建筑", system)
        self.assertIn("1:1:1", system)

    def test_incomplete_seed_fallback_builds_non_person_views_in_both_languages(self):
        cases = (
            ("纯中文", "砖砌钟楼", "黄铜检修盖板", "几何轮廓"),
            ("纯英文", "a tracked inspection machine", "brass access hatch", "component count"),
        )
        for language, primary, detail, marker in cases:
            with self.subTest(language=language):
                result = smart_text.fallback_smart_text(
                    user_text=detail,
                    primary_prompt=primary,
                    subject_type="非人物主体",
                    language=language,
                    layout_mode="multi_view",
                )
                self.assert_non_person_design(result)
                self.assertIn(detail, result)
                self.assertIn(marker, result)
                self.assertTrue(narrative.prompt_preserves_visual_layout(result, "multi_view", non_person=True), result)

    def test_complete_non_person_views_merge_detail_without_wardrobe(self):
        for english in (False, True):
            with self.subTest(english=english):
                primary = narrative.visual_layout_contract("multi_view", english=english, non_person=True)
                primary += " A tracked inspection machine with a steel shell." if english else "三栏共同展示钢制履带巡检机械。"
                detail = "brass access hatch" if english else "黄铜检修盖板"
                result = smart_text.fallback_smart_text(
                    user_text=detail,
                    primary_prompt=primary,
                    subject_type="非人物主体",
                    language="纯英文" if english else "纯中文",
                    layout_mode="multi_view",
                )
                self.assertTrue(result.startswith(primary), result)
                self.assertIn(detail, result)
                self.assert_non_person_design(result)
                self.assertIn("same structural location" if english else "同一结构位置", result)

    def test_bilingual_fallback_keeps_non_person_structure_in_both_parts(self):
        result = smart_text.fallback_smart_text(
            user_text="brass access hatch",
            primary_prompt="tracked inspection machine",
            subject_type="非人物主体",
            language="英文提示词+中文说明",
            layout_mode="multi_view",
        )
        self.assertIn("中文说明：", result)
        self.assertIn("component count", result)
        self.assertIn("部件数量", result)
        self.assert_non_person_design(result)

    def test_sanitizer_rebuilds_unusable_model_output_with_non_person_fallback(self):
        for language in ("纯中文", "纯英文"):
            with self.subTest(language=language):
                result = smart_text.sanitize_smart_text_prompt(
                    text="CG感",
                    user_text="brass access hatch" if language == "纯英文" else "黄铜检修盖板",
                    primary_prompt="tracked inspection machine" if language == "纯英文" else "钢制履带巡检机械",
                    subject_type="非人物主体",
                    language=language,
                    layout_mode="multi_view",
                )
                self.assert_non_person_design(result)
                self.assertTrue(narrative.prompt_preserves_visual_layout(result, "multi_view", non_person=True), result)

    def test_sanitizer_passes_non_person_context_to_layout_validation(self):
        primary = narrative.visual_layout_contract("multi_view", non_person=True) + "三栏共同展示同一钢制履带巡检机械。"
        with mock.patch.object(smart_text, "prompt_preserves_visual_layout", wraps=smart_text.prompt_preserves_visual_layout) as validate:
            result = smart_text.sanitize_smart_text_prompt(
                text=primary,
                primary_prompt=primary,
                subject_type="非人物主体",
                layout_mode="multi_view",
            )
        self.assertEqual(result, smart_text._strip_smart_text_meta(primary))
        self.assertTrue(validate.call_args.kwargs["non_person"])

    def test_person_seed_system_and_fallback_keep_original_design_wording(self):
        settings = {"主体类型": "人物角色", "画面结构模式解析结果": "multi_view"}
        seed = smart_text.build_smart_text_seed(
            user_text="补充银色扣件",
            primary_prompt="成年女性侦探",
            selected_tags_text="深色长风衣",
            settings=settings,
        )
        self.assertIn("正脸、体型、发型、服装", seed)
        self.assertIn("中性站姿", seed)
        self.assertEqual(smart_text.build_smart_text_settings(settings)["系统提示词覆盖"], smart_text.SMART_TEXT_MULTI_VIEW_SYSTEM_TEMPLATE)
        fallback = smart_text.fallback_smart_text(
            user_text="silver fasteners",
            primary_prompt="adult woman detective",
            subject_type="人物角色",
            language="纯英文",
            layout_mode="multi_view",
        )
        self.assertIn("matching face, body build, hairstyle", fallback)
        self.assertIn("wardrobe construction", fallback)


if __name__ == "__main__":
    unittest.main()
