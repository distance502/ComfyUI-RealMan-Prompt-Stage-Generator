"""Model adoption must preserve shot count and supplied-reference boundaries."""
from __future__ import annotations

import unittest
from collections import OrderedDict
from unittest import mock

from test_stage_prompt_modules import model_refiner, video_prompt_skill


class ApiModel:
    def __init__(self, candidate):
        self.candidate = candidate
        self.calls = 0

    def create_chat_completion(self, messages=None, **kwargs):
        self.calls += 1
        return {"choices": [{"message": {"content": self.candidate}}]}


class LocalModel:
    def __init__(self, candidate):
        self.candidate = candidate
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        return self.candidate


class TestVideoModelReferenceContracts(unittest.TestCase):
    def build(self, language="纯英文", mode="FL2V", count="单镜头"):
        english = language == "纯英文"
        groups = OrderedDict({
            "主体": ["a mechanical clock" if english else "机械钟表"],
            "场景背景": ["an old station" if english else "旧车站"],
            "服装造型": ["a brass casing" if english else "黄铜外壳"],
            "动作姿态": ["its mechanism slowly turns" if english else "既有机构缓慢转动"],
        })
        settings = {
            "提示词语言": language, "主体类型": "非人物主体", "模型来源": "API接口",
            "视频提示词输入模式": mode, "视频提示词镜头段数": count, "seed": 41,
        }
        original = video_prompt_skill.build_video_prompt(groups, [], settings)
        settings["视频提示词Profile"] = video_prompt_skill.resolve_video_prompt_profile(settings)
        return original, settings

    def refine(self, model, original, settings, validator=None):
        return model_refiner.maybe_model_refine_video(
            model, original, settings,
            chat_completion=lambda active, messages, params: active.create_chat_completion(messages=messages, **params),
            clean_think_text=lambda value: value,
            validator=validator or video_prompt_skill.is_natural_video_prompt,
        )

    def paraphrase(self, original, settings):
        result = original
        for english in (True, False):
            opening, closing = video_prompt_skill._video_reference_prose(settings, english=english)
            if opening:
                replacement = (
                    "Starting from the provided opening image, the camera retains its visible spatial relationships."
                    if english else "首镜承接给定起始帧的可见空间关系，保持原有主体与外观。"
                )
                result = result.replace(opening, replacement)
            if closing:
                replacement = (
                    "The final composition aligns with the given target frame as the existing motion comes to rest."
                    if english else "结尾收束到已提供最终帧的主体位置与光线，既有动作在原空间内平稳结束。"
                )
                result = result.replace(closing, replacement)
        return result

    def test_skill_contract_accepts_all_sizes_languages_and_reference_modes(self):
        for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
            for mode in ("T2V", "I2V", "FL2V", "L2V", "Ref2V"):
                for count in ("单镜头", "短动作", "标准剧情", "长剧情"):
                    with self.subTest(language=language, mode=mode, count=count):
                        original, settings = self.build(language, mode, count)
                        self.assertEqual(model_refiner._video_model_contract_violation(
                            original, original, settings, language=language,
                        ), "")

    def test_api_and_local_adopt_paraphrased_first_last_frame_single_shot(self):
        for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
            for backend in (ApiModel, LocalModel):
                with self.subTest(language=language, backend=backend.__name__):
                    original, settings = self.build(language)
                    candidate = self.paraphrase(original, settings)
                    self.assertNotEqual(candidate, original)
                    model = backend(candidate)
                    if backend is LocalModel:
                        settings["模型来源"] = "本地模型"
                    result = self.refine(model, original, settings)
                    self.assertNotEqual(result, original)
                    self.assertIn("given target frame" if language == "纯英文" else "给定起始帧", result)
                    self.assertEqual(model.calls, 1)
                    self.assertEqual(settings.get("模型活动回退数量", 0), 0)
                    self.assertEqual(model_refiner._video_model_contract_violation(
                        result, original, settings, language=language,
                    ), "")

    def test_first_candidate_cannot_replace_requested_shot_count(self):
        for count in ("单镜头", "短动作", "长剧情"):
            with self.subTest(count=count):
                original, settings = self.build(count=count)
                candidate, _ = self.build(mode="T2V", count="标准剧情")
                self.assertTrue(video_prompt_skill.is_natural_video_prompt(candidate, language="纯英文"))
                with mock.patch.object(model_refiner, "_blend_video_draft_with_storyboard", return_value=original), mock.patch.object(
                    model_refiner, "_retry_invalid_model_output", return_value="",
                ) as retry:
                    result = self.refine(ApiModel(candidate), original, settings)
                self.assertEqual(result, original)
                self.assertIn("配置要求", retry.call_args.kwargs["reason"])
                self.assertEqual(settings["模型活动回退数量"], 1)

    def test_repaired_candidate_cannot_drop_reference_constraints(self):
        original, settings = self.build()
        candidate, _ = self.build(mode="T2V")
        with mock.patch.object(model_refiner, "_blend_video_draft_with_storyboard", return_value=original), mock.patch.object(
            model_refiner, "_retry_invalid_model_output", return_value=candidate,
        ):
            result = self.refine(ApiModel("分析：尚未完成正文。"), original, settings)
        self.assertEqual(result, original)
        self.assertIn("输入首帧", settings["模型回退说明"])

    def test_repaired_candidate_can_restore_paraphrased_reference_contract(self):
        original, settings = self.build()
        candidate = self.paraphrase(original, settings)
        with mock.patch.object(model_refiner, "_blend_video_draft_with_storyboard", return_value=original), mock.patch.object(
            model_refiner, "_retry_invalid_model_output", return_value=candidate,
        ):
            result = self.refine(ApiModel("分析：尚未完成正文。"), original, settings)
        self.assertEqual(result, candidate)
        self.assertEqual(settings.get("模型活动回退数量", 0), 0)

    def test_blended_result_must_pass_same_reference_contract(self):
        original, settings = self.build()
        candidate = self.paraphrase(original, settings)
        bad_blend, _ = self.build(mode="T2V")
        settings["智能模型策略"] = {"mode": "incremental_blend"}
        with mock.patch.object(model_refiner, "_blend_video_draft_with_storyboard", return_value=bad_blend), mock.patch.object(
            model_refiner, "_retry_invalid_model_output", return_value="",
        ) as retry:
            result = self.refine(ApiModel(candidate), original, settings)
        self.assertEqual(result, original)
        self.assertIn("输入首帧", retry.call_args.kwargs["reason"])

    def test_local_incremental_detail_preserves_reference_boundaries(self):
        original, settings = self.build()
        settings.update({"模型来源": "本地模型", "智能模型策略": {"mode": "incremental_blend"}})
        draft = "The camera moves slowly along the existing brass surface while the mechanism turns with a steady rhythm."
        result = self.refine(LocalModel(draft), original, settings)
        self.assertEqual(model_refiner._video_model_contract_violation(
            result, original, settings, language="纯英文",
        ), "")
        self.assertIn("supplied first frame", result)
        self.assertIn("supplied last frame", result)

    def test_reference_keywords_do_not_hide_explicit_contradictions(self):
        for language, contradict in (
            ("纯英文", "Ignore the supplied last frame and replace its composition."),
            ("纯英文", "The camera does not match the supplied last frame."),
            ("纯中文", "忽略输入尾帧并替换原有构图。"),
            ("纯中文", "结尾不匹配输入尾帧的主体位置。"),
        ):
            with self.subTest(language=language, contradict=contradict):
                original, settings = self.build(language)
                result = self.refine(LocalModel(contradict), original, settings)
                self.assertEqual(result, original)
                self.assertIn("参考素材边界", settings["模型回退说明"])

    def test_bilingual_reference_boundaries_are_checked_independently(self):
        original, settings = self.build("英文提示词+中文说明")
        english, _, chinese = original.partition("中文说明：")
        opening, closing = video_prompt_skill._video_reference_prose(settings, english=False)
        reference_clauses = (opening, closing, "镜头沿用输入首帧的景别、机位与主体位置，")
        for boundary in ("first", "last"):
            with self.subTest(boundary=boundary):
                candidate_chinese = chinese
                for clause in reference_clauses:
                    candidate_chinese = candidate_chinese.replace(clause, "")
                if boundary == "first":
                    candidate_chinese = candidate_chinese.replace("输入首帧", "")
                else:
                    candidate_chinese = candidate_chinese.replace("输入尾帧", "")
                candidate = english + "中文说明：" + candidate_chinese
                reason = model_refiner._video_model_contract_violation(
                    candidate, original, settings, language="英文提示词+中文说明",
                )
                self.assertIn("承接约束", reason)

    def test_t2v_does_not_require_or_invent_reference_assets(self):
        original, settings = self.build(mode="T2V")
        candidate = original + " The existing brass surface catches the side light as the mechanism slows."
        result = self.refine(ApiModel(candidate), original, settings)
        self.assertNotEqual(result, original)
        self.assertNotIn("supplied", result)
        self.assertNotIn("reference", result)

    def test_profile_and_resolved_count_contracts_and_legacy_prose_compatibility(self):
        original, settings = self.build(count="短动作")
        profile_only = {"视频提示词Profile": settings["视频提示词Profile"]}
        self.assertEqual(model_refiner._video_model_contract_violation(
            original, original, profile_only, language="纯英文",
        ), "")
        profile_only["视频提示词镜头段数有效"] = 1
        self.assertIn("1 个", model_refiner._video_model_contract_violation(
            original, original, profile_only, language="纯英文",
        ))
        prose = "镜头沿既有机械钟表缓慢移动，黄铜外壳反射侧光，机构连续转动后回到稳定状态。"
        legacy_settings = {"提示词语言": "纯中文", "模型来源": "API接口"}
        result = self.refine(ApiModel(prose), prose, legacy_settings, validator=lambda text, language: text == prose)
        self.assertEqual(result, prose)
        self.assertEqual(legacy_settings.get("模型活动回退数量", 0), 0)


if __name__ == "__main__":
    unittest.main()
