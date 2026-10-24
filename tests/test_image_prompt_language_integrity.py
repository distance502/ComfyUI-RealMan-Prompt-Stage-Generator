"""Image Skill fallbacks preserve explicit facts without claiming a translation."""
from __future__ import annotations

from collections import OrderedDict
import unittest
from unittest import mock

from test_stage_prompt_modules import model_refiner, prompt_builder, uniq


class TestImagePromptLanguageIntegrity(unittest.TestCase):
    def build(self, *, extra="", custom=None, language="纯英文", selected=None, **overrides):
        settings = {
            "模板风格": "真实感", "主体类型": "人物角色",
            "案例输出结构": "案例长段版", "标签反推模式": "自动平衡",
            "生成数量": 1, "运行时随机标签": False,
            "提示词语言": language, "额外要求": extra, **overrides,
        }
        prompts = prompt_builder.build_prompt_list(
            selected or OrderedDict({"主体": ["成年男性"], "构图视角": ["全景全身"]}),
            custom or [], settings, uniq=uniq,
            infer_template_style=lambda _tags, explicit: explicit,
            infer_subject_type=lambda _tags, explicit: explicit,
            infer_output_structure=lambda _subject, explicit: explicit,
        )
        return prompts, settings

    def test_english_words_containing_brief_remain_drawable_facts(self):
        for requirement in (
            "brown leather briefcase",
            "a firefighter debriefing a team",
            "a brief pause beside the doorway",
            "a silver BRIEFCASE",
        ):
            with self.subTest(requirement=requirement):
                self.assertEqual(prompt_builder._clean_fragment(requirement), requirement)
                prompts, _ = self.build(extra=requirement)
                self.assertIn(requirement, prompts[0])

    def test_only_standalone_legacy_brief_marker_is_removed(self):
        for marker in ("brief", "Brief", "BRIEF"):
            with self.subTest(marker=marker):
                self.assertEqual(prompt_builder._clean_fragment(marker), "")

    def test_unknown_explicit_chinese_gets_a_usable_faithful_skill_fallback(self):
        requirement = "左手握着折叠测绘尺，右肩悬挂黄色工具包"
        for language in ("纯英文", "英文提示词+中文说明"):
            with self.subTest(language=language):
                prompts, settings = self.build(extra=requirement, language=language)
                self.assertIn(requirement, prompts[0])
                self.assertIn("画面", prompts[0])
                self.assertEqual(settings["提示词语言"], language)
                self.assertEqual(settings["图像提示词待翻译锚点"], [requirement])
                self.assertEqual(settings["图像提示词Skill回退语言"], "纯中文")
                self.assertEqual(settings["图像提示词中文回退"], prompts)
                self.assertTrue(any("翻译" in note and "中文" in note for note in settings["推理纠偏说明"]))
                self.assertTrue(model_refiner.is_natural_language_prompt(
                    prompts[0], {**settings, "提示词语言": "纯中文"},
                ))

    def test_untranslated_explicit_tags_are_kept_but_automatic_tags_do_not_force_fallback(self):
        unknown = "左腕佩戴靛蓝色机械罗盘"
        selected = OrderedDict({"主体": ["成年男性"], "道具世界观": [unknown]})
        prompts, settings = self.build(selected=selected)
        self.assertEqual(settings["图像提示词待翻译锚点"], [unknown])
        self.assertIn(unknown, prompts[0])

        prompts, settings = self.build(
            selected=selected,
            用户标签Skill={"protected_tags": ["成年男性"]},
        )
        self.assertEqual(settings["图像提示词待翻译锚点"], [])
        self.assertEqual(settings["图像提示词Skill回退语言"], "")
        self.assertFalse(prompt_builder._has_cjk(prompts[0]))

    def test_custom_requirements_are_preserved_once_across_a_batch(self):
        unknown = "衣领别着铜色方形徽章"
        prompts, settings = self.build(custom=[unknown, unknown], extra=unknown, 生成数量=2)
        self.assertEqual(settings["图像提示词待翻译锚点"], [unknown])
        self.assertEqual(settings["图像提示词中文回退"], prompts)
        self.assertEqual(len(prompts), 2)
        for prompt in prompts:
            self.assertIn(unknown, prompt)

    def test_known_chinese_and_negative_only_requirements_keep_english_output(self):
        for requirement in (
            "高细节", "中画幅质感", "港式武侠胶片", "霓虹侧逆光", "雨夜街头",
            "CG感", "浮空水晶", "无水印", "",
        ):
            with self.subTest(requirement=requirement):
                prompts, settings = self.build(extra=requirement)
                self.assertEqual(settings["图像提示词待翻译锚点"], [])
                self.assertEqual(settings["图像提示词中文回退"], [])
                self.assertEqual(settings["图像提示词Skill回退语言"], "")
                self.assertFalse(prompt_builder._has_cjk(prompts[0]))

    def test_chinese_request_clears_stale_translation_state(self):
        prompts, settings = self.build(
            language="纯中文", extra="衣领别着铜色方形徽章",
            图像提示词待翻译锚点=["old"], 图像提示词Skill回退语言="纯中文",
            图像提示词中文回退=["old"],
        )
        self.assertIn("铜色方形徽章", prompts[0])
        self.assertEqual(settings["图像提示词待翻译锚点"], [])
        self.assertEqual(settings["图像提示词Skill回退语言"], "")
        self.assertEqual(settings["图像提示词中文回退"], [])

    def test_known_selected_source_anchors_do_not_force_chinese_fallback(self):
        for group, tag in (
            ("主体", "成年女性冒险者"), ("动作姿态", "站姿放松"),
            ("光影氛围", "霓虹逆光"), ("光影氛围", "霓虹侧逆光"),
            ("场景背景", "雨夜街头"), ("画面风格", "CG感"),
            ("道具世界观", "浮空水晶"),
        ):
            with self.subTest(group=group, tag=tag):
                selected = OrderedDict({"主体": ["成年男性"], "构图视角": ["全景全身"]})
                selected[group] = [tag]
                prompts, settings = self.build(selected=selected)
                self.assertEqual(settings["图像提示词待翻译锚点"], [])
                self.assertEqual(settings["图像提示词Skill回退语言"], "")
                self.assertFalse(prompt_builder._has_cjk(prompts[0]))
                self.assertIn(prompt_builder._translate_prompt_fragment(tag), prompts[0])
        self.assertEqual(prompt_builder._translate_prompt_fragment("浮空水晶"), "floating crystals")

    def test_fallback_keeps_resolved_target_and_non_person_subject_contract(self):
        selected = OrderedDict({"主体": ["a mechanical clock"], "构图视角": ["三视图"]})
        with mock.patch.object(
            prompt_builder, "render_narrative_prompt", wraps=prompt_builder.render_narrative_prompt,
        ) as render:
            prompts, settings = self.build(
                selected=selected, extra="表壳侧面带靛蓝色珐琅刻线",
                主体类型="非人物主体", 图像提示词目标模型="MOSS Image",
            )
        self.assertEqual(render.call_args.args[0]["image_target"], "MOSS Image")
        self.assertTrue(render.call_args.kwargs["non_person"])
        self.assertEqual(render.call_args.kwargs["layout_mode"], "multi_view")
        self.assertEqual(settings["画面结构模式解析结果"], "multi_view")
        self.assertIn("珐琅刻线", prompts[0])
        self.assertIn("部件数量", prompts[0])
        self.assertNotIn("服装", prompts[0])
        self.assertTrue(model_refiner.is_natural_language_prompt(
            prompts[0], {**settings, "提示词语言": "纯中文"},
        ))

    def test_known_detective_scene_keeps_english_target_opening(self):
        selected = OrderedDict({
            "主体": ["成年女性侦探"], "场景背景": ["雨夜旧车站"],
            "动作姿态": ["停步回望"], "服装造型": ["深色长风衣"],
            "道具世界观": ["旧信封"], "光影氛围": ["青蓝侧光"],
            "构图视角": ["中景"], "画面风格": ["电影写实"],
        })
        prompts, settings = self.build(selected=selected, 图像提示词目标模型="MOSS Image")
        self.assertEqual(settings["图像提示词待翻译锚点"], [])
        self.assertTrue(prompts[0].startswith("The image uses"))
        self.assertFalse(prompt_builder._has_cjk(prompts[0]))
        for anchor in ("adult female detective", "old railway station", "old envelope", "blue-cyan side lighting"):
            self.assertIn(anchor, prompts[0])

    def test_untranslated_explicit_text_blocks_keep_source_order(self):
        blocks = ["左袖别着铜色菱形徽章", "右侧腰带悬着靛蓝色机械罗盘"]
        prompts, settings = self.build(标签块显式文本=blocks)
        self.assertEqual(settings["图像提示词待翻译锚点"], blocks)
        self.assertIn(blocks[0], prompts[0])
        self.assertIn(blocks[1], prompts[0])
        self.assertLess(prompts[0].index(blocks[0]), prompts[0].index(blocks[1]))
        self.assertEqual(settings["图像提示词Skill回退语言"], "纯中文")

    def test_translation_uses_real_model_call_skill_and_adopts_complete_english(self):
        requirement = "左手握着折叠测绘尺，右肩悬挂黄色工具包"
        source, settings = self.build(
            extra=requirement, 模型来源="API接口",
            智能模型策略={"mode": "incremental_blend"},
            模型瞬时重试次数=0, 模型输出修复重试次数=0,
        )
        translated, _ = self.build(extra=(
            "The traveler holds a folding survey ruler in the left hand, "
            "with a yellow tool bag hanging from the right shoulder."
        ))
        requests = []

        def backend(prompt, **_kwargs):
            requests.append(prompt)
            return translated[0]

        resolved = model_refiner.maybe_model_refine(
            backend, source[0], settings,
            chat_completion=lambda *_args, **_kwargs: None,
            clean_think_text=lambda text: text,
        )
        self.assertEqual(resolved, translated[0])
        self.assertEqual(len(requests), 1)
        self.assertIn(requirement, requests[0])
        self.assertIn("完整翻译", requests[0])
        self.assertEqual(settings["模型调用Skill状态"], "成功")
        self.assertEqual(settings["模型调用采纳次数"], 1)
        self.assertFalse(prompt_builder._has_cjk(resolved))


if __name__ == "__main__":
    unittest.main()
