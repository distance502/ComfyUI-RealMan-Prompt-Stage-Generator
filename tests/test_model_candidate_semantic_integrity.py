"""Ordinary model candidates keep language boundaries and comparable anchors."""
from __future__ import annotations

import unittest
from unittest import mock

from test_stage_prompt_modules import intelligence, model_refiner


class TestModelCandidateSemanticIntegrity(unittest.TestCase):
    body = (
        "The story begins with an adult traveler entering the dungeon. "
        "A falling stone interrupts the silence because an old latch shifts. "
        "The traveler pauses and turns toward the gate. "
        "Unease crosses his face as the movement settles. "
        "Lighting and shadow reveal the worn material of the walls. "
        "The camera holds on his alert expression in the final frame."
    )
    source = body.replace("entering the dungeon", "carrying a torch into the dungeon")
    note = "探险者停在地牢入口，观察墙上的光线。"

    def settings(self, language="纯英文", *, prop="torch"):
        selected = {"主体": ["adult traveler"], "道具世界观": [prop], "场景背景": ["dungeon"]}
        settings = {
            "提示词语言": language, "全局叙事合同启用": True, "模型来源": "API接口",
            "模型瞬时重试次数": 0, "模型输出修复重试次数": 0,
        }
        settings["全局创作主线合同"] = model_refiner.build_global_creative_spine_contract(
            selected, [], settings, template_style="自动", subject_type="人物角色",
            layout_mode="", primary_style_family="",
        )
        settings["智能场景关系图"] = intelligence.build_scene_relationship_graph(selected)
        return settings

    def test_equivalent_bilingual_markers_pass_all_image_checks(self):
        settings = self.settings("英文提示词+中文说明")
        original = self.source + "\n中文说明：" + self.note
        for marker in ("中文说明：", "中文说明:", "中文说明 ：", "中文说明 \t :"):
            with self.subTest(marker=marker):
                candidate = self.source + "\n" + marker + self.note
                self.assertFalse(model_refiner._violates_language(candidate, settings))
                self.assertTrue(model_refiner._looks_like_natural_prose_prompt(candidate))
                self.assertTrue(model_refiner._looks_like_narrative_prompt(candidate, settings))
                self.assertTrue(model_refiner.is_natural_language_prompt(candidate, settings))
                resolved, mode, reason = model_refiner._resolve_model_prompt_candidate(original, candidate, settings)
                self.assertNotEqual(mode, "rejected", reason)
                self.assertIn("中文说明：", resolved)

    def test_bilingual_marker_tolerance_does_not_supply_missing_or_reversed_parts(self):
        settings = self.settings("英文提示词+中文说明")
        for candidate in (
            self.source,
            self.source + "\n中文说明:",
            "中文说明:" + self.note,
            "中文说明:" + self.note + "\n" + self.source,
            self.source + "\n中文说明:No Chinese note is present.",
            "A traveler 含中文 walks onward.\n中文说明:" + self.note,
        ):
            with self.subTest(candidate=candidate):
                self.assertTrue(model_refiner._violates_language(candidate, settings))

    def test_video_and_fragment_cleaners_canonicalize_the_same_marker(self):
        candidate = self.source + "\n中文说明 :" + self.note
        for clean in (
            model_refiner._postprocess_prompt_text,
            model_refiner._postprocess_video_prompt_text,
            model_refiner._dedupe_prompt_fragments,
        ):
            with self.subTest(clean=clean.__name__):
                self.assertIn("中文说明：", clean(candidate))

    def test_english_and_bilingual_candidates_cannot_remove_english_prop_anchors(self):
        for language in ("纯英文", "英文提示词+中文说明"):
            for body in (self.body, self.body + " The traveler continues without a torch."):
                with self.subTest(language=language, body=body):
                    suffix = "\n中文说明：" + self.note if language != "纯英文" else ""
                    original = self.source + suffix
                    resolved, mode, reason = model_refiner._resolve_model_prompt_candidate(
                        original, body + suffix, self.settings(language),
                    )
                    self.assertIn(mode, {"rejected", "blended"})
                    if mode == "rejected":
                        self.assertEqual(resolved, original)
                        self.assertIn("torch", reason)
                    else:
                        english_body = resolved.split("中文说明：", 1)[0]
                        self.assertTrue(intelligence.prompt_preserves_anchor(english_body, "torch"))

    def test_english_prop_hidden_only_in_chinese_note_does_not_satisfy_anchor(self):
        original = self.source + "\n中文说明：" + self.note
        candidate = self.body + "\n中文说明：探险者仍握着 torch。"
        resolved, mode, reason = model_refiner._resolve_model_prompt_candidate(
            original, candidate, self.settings("英文提示词+中文说明"),
        )
        self.assertIn(mode, {"rejected", "blended"})
        if mode == "rejected":
            self.assertEqual(resolved, original)
            self.assertIn("torch", reason)
        else:
            english_body = resolved.split("中文说明：", 1)[0]
            self.assertTrue(intelligence.prompt_preserves_anchor(english_body, "torch"))

    def test_comparable_english_anchors_remain_case_insensitive(self):
        resolved, mode, reason = model_refiner._resolve_model_prompt_candidate(
            self.source, self.source.replace("torch", "TORCH"), self.settings(),
        )
        self.assertEqual((resolved, mode, reason), (self.source.replace("torch", "TORCH"), "direct", ""))

    def test_comparable_english_anchors_allow_leading_article_changes(self):
        for language in ("纯英文", "英文提示词+中文说明"):
            for anchor, replacement in (
                ("a torch", "the torch"),
                ("an oil lantern", "the oil lantern"),
                ("the dark coat", "a dark coat"),
                ("A TORCH", "the torch"),
            ):
                with self.subTest(language=language, anchor=anchor, replacement=replacement):
                    suffix = "\n中文说明：" + self.note if language != "纯英文" else ""
                    original = self.source.replace("a torch", anchor) + suffix
                    candidate = self.source.replace("a torch", replacement) + suffix
                    resolved, mode, reason = model_refiner._resolve_model_prompt_candidate(
                        original, candidate, self.settings(language, prop=anchor),
                    )
                    self.assertEqual((mode, reason), ("direct", ""))
                    self.assertIn(replacement, resolved)

    def test_english_article_tolerance_keeps_entity_detail_boundary_and_polarity(self):
        for language in ("纯英文", "英文提示词+中文说明"):
            for anchor, replacement in (
                ("a torch", "the torchlight"),
                ("an oil lantern", "the lantern"),
                ("a dark coat", "the coat"),
                ("a torch", "no torch"),
                ("a dark coat", "no dark coat"),
            ):
                with self.subTest(language=language, anchor=anchor, replacement=replacement):
                    suffix = "\n中文说明：" + self.note if language != "纯英文" else ""
                    original = self.source.replace("a torch", anchor) + suffix
                    candidate = self.source.replace("a torch", replacement) + suffix
                    reason = model_refiner._creative_spine_violation(
                        original, candidate, self.settings(language, prop=anchor),
                    )
                    self.assertIn(anchor, reason)

    def test_chinese_anchors_needing_translation_are_not_forced_into_english(self):
        settings = self.settings(prop="火炬")
        settings["图像提示词待翻译锚点"] = ["手持火炬"]
        resolved, mode, reason = model_refiner._resolve_model_prompt_candidate(
            "成年旅人手持火炬穿过地下城遗迹。", self.source, settings,
        )
        self.assertEqual((resolved, mode, reason), (self.source, "direct", ""))

    def test_batch_falls_back_only_for_the_item_missing_its_english_anchor(self):
        settings = self.settings()
        second = self.source.replace("gate", "archway")
        raw = model_refiner._BATCH_SEPARATOR.join((self.body, second))
        with mock.patch.object(model_refiner, "_call_model_text_with_retry", return_value=raw):
            resolved = model_refiner.maybe_model_refine_batch(
                lambda _: None, [self.source, second], settings,
                chat_completion=lambda *args, **kwargs: None, clean_think_text=lambda text: text,
            )
        self.assertEqual(resolved, [self.source, second])
        self.assertEqual(settings["模型活动回退数量"], 1)


if __name__ == "__main__":
    unittest.main()
