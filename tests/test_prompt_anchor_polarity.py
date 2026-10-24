"""Ordinary prompt anchors keep their meaning across refinement paths."""
from __future__ import annotations

import unittest
from unittest import mock

from test_stage_prompt_modules import intelligence, model_refiner


class TestPromptAnchorPolarity(unittest.TestCase):
    original = "一名成年探险者穿着皮革护甲，手持火炬，站在地下城遗迹入口。"
    denied = (
        "起初，一名成年探险者站在地下城遗迹入口。"
        "因为远处传来落石声，他保持警觉并缓缓转身。"
        "身上没有皮革护甲，手中也没有火炬。"
        "环境中的微弱光线照亮石墙。镜头最终停在他凝视入口的瞬间。"
    )

    def settings(self):
        selected = {
            "服装造型": ["皮革护甲"], "道具世界观": ["火炬"], "场景背景": ["地下城遗迹"],
        }
        settings = {
            "提示词语言": "纯中文", "模型来源": "API接口", "全局叙事合同启用": True,
            "模型瞬时重试次数": 0, "模型输出修复重试次数": 0,
        }
        settings["全局创作主线合同"] = model_refiner.build_global_creative_spine_contract(
            selected, [], settings, template_style="自动", subject_type="人物角色",
            layout_mode="", primary_style_family="",
        )
        settings["智能场景关系图"] = intelligence.build_scene_relationship_graph(
            selected, subject_type="人物角色",
        )
        return settings

    def test_required_anchor_needs_positive_presence_without_explicit_absence(self):
        cases = (
            ("他手持火炬站在入口。", "火炬", True),
            ("他手中没有火炬。", "火炬", False),
            ("他手持火炬。镜头中却没有火炬。", "火炬", False),
            ("他手持火炬。最后画面中并非手持火炬。", "火炬", False),
            ("他手持火炬，避免火炬遮挡面部。", "火炬", True),
            ("他手持火炬。没有火炬遮挡面部。", "火炬", True),
            ("The torch casts no shadow.", "torch", True),
            ("He holds a TORCH beside the gate.", "torch", True),
            ("He does not carry a torch.", "torch", False),
            ("He holds a torch. No torch is visible in the scene.", "torch", False),
            ("He holds a torch without a torch obscuring his face.", "torch", True),
            ("Not only a torch but also a sword is visible.", "torch", True),
            ("A knight without a torch or sword waits at the gate.", "sword", False),
            ("A knight without a helmet waits beside a torch.", "torch", True),
            ("保持无水印输出。", "无水印", True),
        )
        for text, anchor, expected in cases:
            with self.subTest(text=text, anchor=anchor):
                self.assertEqual(intelligence.prompt_preserves_anchor(text, anchor), expected)

    def test_negative_anchor_qualifiers_do_not_remove_the_present_object(self):
        cases = (
            ("He holds a torch, not a torch with a cracked handle.", True),
            ("他手持火炬，并非火炬在引导方向，而是旧地图指明道路。", True),
            ("He holds a torch. No torch is visible.", False),
            ("他手持火炬。画面中没有火炬。", False),
            ("Not a torch with a cracked handle is visible.", False),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                anchor = "火炬" if "火炬" in text else "torch"
                self.assertEqual(intelligence.prompt_preserves_anchor(text, anchor), expected)

    def test_image_refinement_does_not_adopt_denied_required_anchors(self):
        resolved, mode, _ = model_refiner._resolve_model_prompt_candidate(
            self.original, self.denied, self.settings(),
        )
        self.assertEqual((resolved, mode), (self.original, "rejected"))

    def test_image_repair_replaces_a_denied_anchor_candidate(self):
        settings = self.settings()
        settings["模型输出修复重试次数"] = 1
        repaired = self.denied.replace("没有皮革护甲", "穿着皮革护甲").replace("也没有火炬", "仍握着火炬")
        with mock.patch.object(model_refiner, "_call_model_text_with_retry", side_effect=[self.denied, repaired]) as call:
            result = model_refiner.maybe_model_refine(
                lambda _: None, self.original, settings,
                chat_completion=lambda *args, **kwargs: None, clean_think_text=lambda text: text,
            )
        self.assertEqual(result, repaired)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(settings.get("模型活动回退数量", 0), 0)

    def test_batch_refinement_preserves_corresponding_skill_for_denied_anchors(self):
        settings = self.settings()
        settings["全局叙事合同启用"] = False
        other = self.original.replace("入口", "石阶")
        raw = model_refiner._BATCH_SEPARATOR.join((self.denied, other))
        with mock.patch.object(model_refiner, "_call_model_text_with_retry", return_value=raw):
            result = model_refiner.maybe_model_refine_batch(
                lambda _: None, [self.original, other], settings,
                chat_completion=lambda *args, **kwargs: None, clean_think_text=lambda text: text,
            )
        self.assertEqual(result, [self.original, other])
        self.assertEqual(settings["模型活动回退数量"], 1)

    def test_video_direct_repaired_and_blended_candidates_check_anchor_polarity(self):
        original = "镜头记录探险者手持火炬站在入口，火光沿石墙移动。"
        denied = "镜头记录探险者站在入口，他手中没有火炬，微弱光线沿石墙移动。"
        for path in ("direct", "repaired", "blended"):
            with self.subTest(path=path):
                settings = {
                    "提示词语言": "纯中文", "模型来源": "API接口",
                    "视频提示词必保留锚点": ["火炬"], "模型输出修复重试次数": 0,
                }
                raw = denied if path == "direct" else "镜头记录石墙上的微弱光线移动。"
                repaired = denied if path == "repaired" else ""
                blended = original + denied if path == "blended" else original
                with (
                    mock.patch.object(model_refiner, "_call_model_text_with_retry", return_value=raw),
                    mock.patch.object(model_refiner, "_retry_invalid_model_output", return_value=repaired),
                    mock.patch.object(model_refiner, "_blend_video_draft_with_storyboard", return_value=blended),
                    mock.patch.object(model_refiner, "_video_model_contract_violation", return_value=""),
                ):
                    result = model_refiner.maybe_model_refine_video(
                        lambda _: None, original, settings, validator=lambda *args, **kwargs: True,
                        chat_completion=lambda *args, **kwargs: None, clean_think_text=lambda text: text,
                    )
                self.assertEqual(result, original)
                self.assertEqual(settings["模型活动回退数量"], 1)

    def test_local_without_does_not_negate_a_later_affirmative_location(self):
        graph = intelligence.build_scene_relationship_graph({"场景背景": ["地下城遗迹"]})
        for text in (
            "A knight without a helmet waits inside a spaceship.",
            "A knight without a helmet and shield stands in a hangar.",
            "A knight without a helmet walks into a spaceship.",
        ):
            with self.subTest(text=text):
                self.assertIn("industrial_scifi", intelligence.detect_world_families(text))
                self.assertIn(
                    "世界族", intelligence.candidate_world_violation("A knight stands in a dungeon.", text, graph),
                )

    def test_local_without_retains_conjoined_negation_and_not_only(self):
        for text in (
            "A knight without a spaceship or control console waits at the gate.",
            "The knight moves without entering a spaceship.",
            "The dungeon must not contain a spaceship or control console.",
        ):
            with self.subTest(text=text):
                self.assertNotIn("industrial_scifi", intelligence.detect_world_families(text))
        text = "Not only a dungeon but also a spaceship appears in the scene."
        self.assertEqual(set(intelligence.detect_world_families(text)), {"underground_ruin", "industrial_scifi"})

    def test_pending_image_translation_requires_full_draft_and_complete_source_requirements(self):
        requirement = "旅人的蓝色外套左袖缝着三枚铜扣，右手握着断开的怀表链。" * 5
        for language in ("纯英文", "英文提示词+中文说明"):
            for layout in ("single_frame", "multi_view"):
                with self.subTest(language=language, layout=layout):
                    settings = {
                        "提示词语言": language, "图像提示词待翻译锚点": [requirement],
                        "智能模型策略": {"mode": "incremental_blend"},
                        "画面结构模式解析结果": layout,
                    }
                    self.assertFalse(model_refiner._uses_incremental_refinement(settings))
                    for request in (
                        model_refiner._compose_model_user_prompt(self.original, settings),
                        model_refiner._compose_batch_prompt([self.original, self.original], settings),
                    ):
                        self.assertIn(requirement, request)
                        self.assertIn("完整翻译", request)
                        self.assertIn("不得只追加", request)
                    with mock.patch.object(model_refiner, "_blend_model_draft_with_skill_prompt") as blend:
                        self.assertEqual(
                            model_refiner._validated_model_blend(self.original, "A readable addition.", settings, layout_mode=""),
                            self.original,
                        )
                        blend.assert_not_called()

    def test_translated_image_candidates_do_not_restore_chinese_literals(self):
        original = "古风CG感的旅人以全景全身构图站在城门旁，手持黄铜罗盘。"
        body = (
            "A single adult traveler is shown from head to toe in a classical fantasy CGI scene, "
            "holding a brass compass by the gate. The entire frame contains only this one person."
        )
        for language in ("纯英文", "英文提示词+中文说明"):
            with self.subTest(language=language):
                candidate = body + ("\n中文说明：旅人站在城门旁手持黄铜罗盘。" if language != "纯英文" else "")
                settings = {
                    "提示词语言": language, "图像提示词待翻译锚点": ["手持黄铜罗盘"],
                    "画面结构模式解析结果": "single_person", "主体类型": "人物角色",
                }
                resolved, mode, reason = model_refiner._resolve_model_prompt_candidate(original, candidate, settings)
                self.assertEqual((mode, reason), ("direct", ""))
                self.assertEqual("".join(resolved.split()), "".join(model_refiner._postprocess_prompt_text(candidate).split()))
                self.assertFalse(model_refiner._CJK_PATTERN.search(resolved.split("中文说明：", 1)[0]))


if __name__ == "__main__":
    unittest.main()
