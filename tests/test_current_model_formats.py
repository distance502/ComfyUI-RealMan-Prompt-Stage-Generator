"""Offline contracts for the 2026-10-23 model/format refresh (no paid API calls)."""
from __future__ import annotations

import json
import re
import unittest
from collections import OrderedDict
from pathlib import Path
from unittest import mock

from test_stage_prompt_modules import (
    load_stage_prompt_generator_for_integration_test,
    narrative,
    prompt_builder,
    model_refiner,
    uniq,
    video_prompt_skill,
)


ROOT = Path(__file__).resolve().parents[1]
IMAGE_TARGETS = ("FLUX.2", "FLUX.3", "FLUX.3 Klein", "MOSS Image", "Qwen Image 2.1", "Qwen Image 2.1 Turbo", "Qwen Image 2512", "Qwen Image Edit 2511", "Qwen Image 3.0", "Wan 2.7 Image", "Gemini Image")
VIDEO_TARGETS = ("FLUX.3 Video", "Wan 3.0", "Wan 2.7", "LTX 2.5", "HappyHorse 1.1", "Veo 3.1")
SELECTED = OrderedDict({
    "主体": ["成年女性侦探"],
    "场景背景": ["雨夜旧车站"],
    "动作姿态": ["停步回望"],
    "服装造型": ["深色长风衣"],
    "道具世界观": ["旧信封"],
    "光影氛围": ["青蓝侧光"],
    "构图视角": ["中景"],
    "画面风格": ["电影写实"],
})


def build_image(target, *, multi_view=False, language="纯中文"):
    settings = {
        "图像提示词目标模型": target,
        "模板风格": "真实感", "主体类型": "人物角色",
        "案例输出结构": "案例长段版", "生成数量": 1,
        "标签反推模式": "自动平衡", "额外要求": "",
        "提示词语言": language, "运行时随机标签": False,
    }
    selected = OrderedDict((name, list(tags)) for name, tags in SELECTED.items())
    if multi_view:
        selected["构图视角"] = ["角色三视图", "正面视图", "侧面视图", "背面视图"]
        selected["主体"].append("角色设定图")
    text = prompt_builder.build_prompt_list(
        selected, [], settings, scene_group="", identity="", style_track="",
        recent_tracks=[], uniq=uniq,
        infer_template_style=lambda _tags, explicit: explicit,
        infer_subject_type=lambda _tags, explicit: explicit,
        infer_output_structure=lambda _subject, explicit: explicit,
    )[0]
    return text, settings


class TestCurrentModelFormats(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage_prompt_generator_for_integration_test()

    def test_provider_defaults_match_frontend_and_keep_custom_ids(self):
        source = (ROOT / "web" / "stage_prompt_generator_ui_v2.js").read_text(encoding="utf-8")
        front = dict(re.findall(r'\{ value: "([^"]+)", label: "[^"]+", baseUrl: "[^"]*", model: "([^"]*)"', source))
        for provider, preset in self.stage.API服务商预设.items():
            with self.subTest(provider=provider):
                self.assertEqual(front[provider], preset["model"])
        for model in ("qwen3.7-max", "my-custom-future-model"):
            config = self.stage._解析API模型配置({
                "API服务商": "通义千问DashScope", "API模型": model, "API密钥": "test-key",
            })
            self.assertEqual(config["model"], model)
        self.assertEqual(self.stage.API服务商预设["DeepSeek"]["model"], "deepseek-flash")
        self.assertEqual(self.stage.API服务商预设["通义千问DashScope"]["model"], "qwen3.8-max")

    def test_deepseek_current_and_legacy_aliases_use_protocol_specific_controls(self):
        for model in ("deepseek-flash", "deepseek-v4-pro", "deepseek-v4-flash", "deepseek-v4.1-flash", "deepseek-v4-pro-0813"):
            for kind in ("openai", "openai_responses"):
                with self.subTest(model=model, kind=kind):
                    backend = self.stage._TEAPIChatModel({
                        "provider": "DeepSeek", "kind": kind, "model": model,
                        "url": "https://api.deepseek.com/" + ("responses" if kind.endswith("responses") else "chat/completions"),
                    })
                    with mock.patch.object(self.stage, "_http_post_json", return_value={"choices": [{"message": {"content": "ok"}}]}) as post:
                        backend.create_chat_completion(messages=[{"role": "system", "content": "rules"}, {"role": "user", "content": "hello"}])
                    payload = post.call_args.args[1]
                    if kind == "openai":
                        self.assertEqual(payload["thinking"], {"type": "disabled"})
                        self.assertNotIn("reasoning", payload)
                        self.assertEqual(payload["messages"][0]["role"], "system")
                    else:
                        self.assertEqual(payload["reasoning"], {"effort": "none"})
                        self.assertNotIn("thinking", payload)

    def test_deepseek_name_does_not_pollute_unrelated_provider(self):
        for provider, url, expected in (
            ("OpenAI兼容", "https://api.deepseek.com/chat/completions", True),
            ("OpenAI兼容", "https://unrelated.example/chat/completions", False),
            ("自定义", "https://api.deepseek.com.evil.example/chat/completions", False),
        ):
            with self.subTest(url=url):
                backend = self.stage._TEAPIChatModel({"provider": provider, "kind": "openai", "model": "deepseek-flash", "url": url})
                with mock.patch.object(self.stage, "_http_post_json", return_value={}) as post:
                    backend.create_chat_completion(messages=[{"role": "user", "content": "hello"}])
                self.assertEqual("thinking" in post.call_args.args[1], expected)
        self.assertFalse(self.stage._is_deepseek_v4_model("deepseek-chat"))
        self.assertFalse(self.stage._is_deepseek_v4_model("my-deepseek-flash-custom"))

    def test_qwen38_has_bounded_stateless_thinking_and_preserves_visual_input(self):
        for model in ("qwen3.8-max", "qwen3.8-flash", "qwen3.8-max-0902", "qwen3.7-max"):
            with self.subTest(model=model):
                config = self.stage._解析API模型配置({"API服务商": "通义千问DashScope", "API模型": model, "API密钥": "test-key"})
                with mock.patch.object(self.stage, "_http_post_json", return_value={"output": {"text": "可见正文"}}) as post:
                    self.stage._TEAPIChatModel(config).create_chat_completion(
                        messages=[{"role": "user", "content": [
                            {"type": "text", "text": "描述图片"},
                            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
                        ]}], max_tokens=512,
                    )
                url, payload = post.call_args.args[:2]
                self.assertIn("multimodal-generation", url)
                self.assertEqual(payload["input"]["messages"][0]["content"][1], {"image": "data:image/png;base64,AAAA"})
                params = payload["parameters"]
                if model.startswith("qwen3.8"):
                    self.assertEqual(params["thinking_budget"], 256)
                    self.assertIs(params["preserve_thinking"], False)
                    self.assertNotIn("reasoning_effort", params)
                else:
                    self.assertNotIn("thinking_budget", params)

    def test_claude5_omits_legacy_sampling_without_changing_claude4(self):
        for model in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-mythos-5-1", "claude-haiku-4-5"):
            with self.subTest(model=model):
                backend = self.stage._TEAPIChatModel({"provider": "Claude Anthropic", "kind": "anthropic", "model": model, "url": "https://api.anthropic.com/v1/messages"})
                with mock.patch.object(self.stage, "_http_post_json", return_value={"content": [{"type": "thinking", "thinking": "hidden"}, {"type": "text", "text": "正文"}]}) as post:
                    response = backend.create_chat_completion(messages=[{"role": "user", "content": "hello"}], top_k=40)
                payload = post.call_args.args[1]
                for field in ("temperature", "top_p", "top_k"):
                    self.assertEqual(field in payload, model == "claude-haiku-4-5")
                self.assertEqual(response["choices"][0]["message"]["content"], "正文")

    def test_current_image_profiles_are_exposed_and_really_use_family_order(self):
        self.assertEqual(list(prompt_builder.IMAGE_PROMPT_TARGET_MODEL_OPTIONS), self.stage.图像提示词目标模型选项)
        self.assertEqual(self.stage.图像提示词目标模型选项[-1], "自定义")
        for target in IMAGE_TARGETS:
            with self.subTest(target=target):
                profile = prompt_builder.resolve_image_prompt_target_profile({"图像提示词目标模型": target})
                text, _ = build_image(target)
                family_text, _ = build_image(profile["family"])
                self.assertEqual(text, family_text)
                self.assertTrue(profile["model_ids"])
                self.assertNotIn(target, text)
                self.assertNotIn("--ar", text)

    def test_current_image_profiles_keep_three_view_layout_in_both_languages(self):
        for target in IMAGE_TARGETS:
            for language in ("纯中文", "纯英文"):
                with self.subTest(target=target, language=language):
                    text, settings = build_image(target, multi_view=True, language=language)
                    profile = settings["图像提示词目标模型Profile"]
                    self.assertEqual(profile["prompt_order"][0], "layout_contract")
                    self.assertEqual(profile["layout_priority"], "hard_first")
                    self.assertTrue(narrative.prompt_preserves_visual_layout(text, narrative.VISUAL_LAYOUT_MULTI_VIEW), text)
                    self.assertEqual(settings["全局剧情规划"], [])

    def test_profile_results_do_not_share_mutable_catalog_lists(self):
        image = prompt_builder.resolve_image_prompt_target_profile({"图像提示词目标模型": "FLUX.2"})
        image["model_ids"].clear()
        self.assertTrue(prompt_builder.resolve_image_prompt_target_profile({"图像提示词目标模型": "FLUX.2"})["model_ids"])
        video = video_prompt_skill.resolve_video_prompt_profile({"视频提示词目标模型": "Wan 3.0"})
        video["supported_input_modes"].clear()
        self.assertTrue(video_prompt_skill.resolve_video_prompt_profile({"视频提示词目标模型": "Wan 3.0"})["supported_input_modes"])

    def test_new_image_capabilities_do_not_leak_across_models_or_quantization(self):
        profiles = {name: prompt_builder.resolve_image_prompt_target_profile({"图像提示词目标模型": name}) for name in IMAGE_TARGETS}
        self.assertEqual(profiles["MOSS Image"]["task_modes"], ["T2I", "Layout"])
        self.assertEqual(profiles["MOSS Image"]["prompt_token_limit"], 4096)
        self.assertNotIn("max_reference_images", profiles["MOSS Image"])
        self.assertIn("no_native_negative_field", profiles["FLUX.3"]["negative_contract"])
        self.assertIn("upsampler_required_downstream", profiles["FLUX.3 Klein"]["prompt_expansion_policy"])
        for target in ("Qwen Image 2.1", "Qwen Image 2.1 Turbo"):
            self.assertEqual(profiles[target]["max_reference_images"], 10)
            self.assertIn("only when requested", profiles[target]["transparency_contract"])
        for profile in profiles.values():
            self.assertIn("same_prompt_for_native_and_GGUF", profile["weight_format_policy"])

    def test_render_family_honors_resolved_target(self):
        self.assertEqual(prompt_builder._image_prompt_render_family({"图像提示词目标模型": "Flux", "图像提示词目标模型有效": "MOSS Image"}), "MOSS Image")
        self.assertEqual(prompt_builder._image_prompt_render_family({"图像提示词目标模型": "unknown"}), "通用")

    def test_stage_validator_preserves_legacy_split_selection_only_with_listed_first_shard(self):
        with mock.patch.object(self.stage, "_内置模型文件选项", return_value=(["nested/model-00001-of-00002.gguf"], ["无"])):
            validator = self.stage.QwenTE阶段式提示词生成器.VALIDATE_INPUTS
            self.assertIs(validator("nested/model-00002-of-00002.gguf", 模型来源="本地模型"), True)
            self.assertIsNot(validator("nested/model-00000-of-00002.gguf", 模型来源="本地模型"), True)
            self.assertIsNot(validator("missing.gguf", 模型来源="本地模型"), True)

    def test_new_image_families_really_change_opening_in_both_languages(self):
        for language in ("纯中文", "纯英文"):
            with self.subTest(language=language):
                texts = {target: build_image(target, language=language)[0] for target in ("通用", "Flux", "FLUX.3", "MOSS Image")}
                self.assertEqual(len(set(texts.values())), 4)
                self.assertTrue(texts["MOSS Image"].startswith("画面以" if language == "纯中文" else "The image uses"))

    def test_new_image_families_do_not_dress_non_person_subjects(self):
        for target in IMAGE_TARGETS:
            for language in ("纯中文", "纯英文"):
                with self.subTest(target=target, language=language):
                    profile = prompt_builder.resolve_image_prompt_target_profile({"图像提示词目标模型": target})
                    anchors = {
                        "image_target": profile["family"],
                        "subject": "机械钟表" if language == "纯中文" else "a mechanical clock",
                        "outfit": "黄铜外壳" if language == "纯中文" else "a brass casing",
                    }
                    plan = narrative.build_narrative_plan(anchors, seed=27, output_count=1)
                    text = narrative.render_narrative_prompt(anchors, plan, language=language, non_person=True)
                    self.assertNotIn("穿着", text)
                    self.assertNotIn(" wears ", text)
                    self.assertIn(anchors["outfit"], text)

    def test_stage_json_exports_requested_image_and_video_formats_together(self):
        result = self.stage._run_stage(None, **{
            "模型来源": "仅Skill", "生成数量": 1, "图像提示词目标模型": "Qwen Image 2.1",
            "视频提示词目标模型": "FLUX.3 Video", "视频提示词输入模式": "FL2V",
            "主体标签1": "成年女性侦探", "场景背景标签1": "雨夜旧车站", "seed": 2817,
        })
        payload = json.loads(result[3])
        self.assertEqual(payload["image_prompt_contract"]["max_reference_images"], 10)
        self.assertIn("RGBA only when requested", payload["image_prompt_contract"]["transparency_contract"])
        self.assertEqual(payload["video_prompt_profile"]["target_model"], "FLUX.3 Video")
        self.assertIs(payload["video_prompt_profile"]["input_mode_supported"], True)
        self.assertIn("last frames", payload["video_storyboard"][0]["input_contract"])

    def test_current_video_profiles_export_natural_storyboards_and_input_contracts(self):
        for target in VIDEO_TARGETS:
            with self.subTest(target=target):
                settings = {"视频提示词目标模型": target, "视频提示词输入模式": "I2V", "提示词语言": "纯中文", "主体类型": "人物角色"}
                profile = video_prompt_skill.resolve_video_prompt_profile(settings)
                text = video_prompt_skill.build_video_prompt(SELECTED, [], settings, primary_prompt="成年女性侦探在雨夜旧车站停步回望。")
                self.assertTrue(video_prompt_skill.is_natural_video_prompt(text, language="纯中文"))
                self.assertNotIn(target, text)
                self.assertIs(profile["input_mode_supported"], True)
                self.assertIn("first frame", profile["input_contract"])
                shots = video_prompt_skill.build_video_storyboard_metadata(text, settings, selected=SELECTED)
                self.assertEqual(len(shots), 5)
                self.assertEqual(shots[0]["input_contract"], profile["input_contract"])
                self.assertEqual(shots[0]["submission_unit"], profile["submission_unit"])
                self.assertFalse(profile["timeline_enabled"])

    def test_video_input_modes_change_skill_prose_without_cross_mode_contamination(self):
        for language in ("纯中文", "纯英文"):
            generated = {}
            for mode in video_prompt_skill.VIDEO_PROMPT_INPUT_MODE_OPTIONS:
                with self.subTest(language=language, mode=mode):
                    settings = {"视频提示词目标模型": "FLUX.3 Video", "视频提示词输入模式": mode, "提示词语言": language, "主体类型": "人物角色"}
                    text = video_prompt_skill.build_video_prompt(SELECTED, [], settings, primary_prompt="A detective stops at a quiet station.")
                    self.assertTrue(video_prompt_skill.is_natural_video_prompt(text, language=language))
                    generated[mode] = text
                    if mode in {"FL2V", "L2V"}:
                        self.assertIn("输入尾帧" if language == "纯中文" else "supplied last frame", text)
                    elif mode == "I2V":
                        self.assertIn("输入首帧" if language == "纯中文" else "supplied first frame", text)
                        self.assertNotIn("输入尾帧" if language == "纯中文" else "supplied last frame", text)
            self.assertEqual(len(set(generated.values())), 5)
            self.assertNotIn("输入首帧" if language == "纯中文" else "supplied first frame", generated["T2V"])

    def test_compact_local_video_model_keeps_reference_input_contract(self):
        profile = video_prompt_skill.resolve_video_prompt_profile({"视频提示词目标模型": "FLUX.3 Video", "视频提示词输入模式": "FL2V"})
        settings = {"模型任务": "视频提示词", "视频提示词Profile": profile}
        with mock.patch.object(model_refiner, "_uses_qwen35_local_incremental_refinement", return_value=True):
            system = model_refiner._resolve_system_prompt(settings)
        self.assertIn(profile["input_contract"], system)
        self.assertIn("never invent missing reference assets", system)

    def test_unconfirmed_video_mode_warns_without_overwriting_workflow(self):
        result = self.stage._run_stage(None, **{
            "模型来源": "仅Skill", "生成数量": 1, "视频提示词目标模型": "LTX 2.5",
            "视频提示词输入模式": "L2V", "主体标签1": "成年女性侦探",
            "场景背景标签1": "雨夜旧车站", "seed": 817,
        })
        payload = json.loads(result[3])
        profile = payload["video_prompt_profile"]
        self.assertEqual(profile["input_mode"], "L2V")
        self.assertIs(profile["input_mode_supported"], False)
        self.assertEqual(profile["submission_unit"], "per_shot")
        self.assertIn("未确认 L2V", result[2])


if __name__ == "__main__":
    unittest.main()
