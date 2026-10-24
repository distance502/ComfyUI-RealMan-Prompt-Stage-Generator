"""The bilingual note must describe the same resolved image as its English body."""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import unittest
from unittest import mock

from test_stage_prompt_modules import prompt_builder, uniq


class TestImageBilingualVariantConsistency(unittest.TestCase):
    def build(self, *, language="英文提示词+中文说明", randomize=True, selected=None, count=3, style="CG感", track=""):
        selected = selected if selected is not None else OrderedDict({
            "主体": ["成年男性"], "场景背景": ["a quiet courtyard"],
            "动作姿态": ["a relaxed standing pose"], "构图视角": ["全景全身"],
        })
        original_selected = deepcopy(selected)
        settings = {
            "模板风格": style, "主体类型": "人物角色",
            "案例输出结构": "案例长段版", "标签反推模式": "自动平衡",
            "生成数量": count, "运行时随机标签": randomize,
            "提示词语言": language, "额外要求": "",
            "运行时随机模式": "全随机", "运行时随机强度": "强", "随机主题池": "自动",
        }
        original_settings = deepcopy(settings)
        profiles = []
        original_profile_builder = prompt_builder._build_runtime_diversity_variant_profile

        def record_profile(*args, **kwargs):
            profile = original_profile_builder(*args, **kwargs)
            profiles.append(deepcopy(profile))
            return profile

        with mock.patch.object(
            prompt_builder, "_build_runtime_diversity_variant_profile", side_effect=record_profile,
        ) as profile_builder:
            prompts = prompt_builder.build_prompt_list(
                selected, [], settings, style_track=track, uniq=uniq,
                infer_template_style=lambda _tags, explicit: explicit,
                infer_subject_type=lambda _tags, explicit: explicit,
                infer_output_structure=lambda _subject, explicit: explicit,
            )
        self.assertEqual(selected, original_selected)
        for key, value in original_settings.items():
            self.assertEqual(settings[key], value)
        self.assertEqual(profile_builder.call_count, count)
        self.assertEqual(len(settings["全局剧情规划"]), count)
        self.assertEqual(settings["图像提示词待翻译锚点"], [])
        return prompts, profiles

    def test_full_random_note_uses_each_resolved_subject_instead_of_the_original(self):
        prompts, profiles = self.build()
        self.assertEqual(len(prompts), 3)
        for prompt, profile in zip(prompts, profiles):
            with self.subTest(profile=profile["subject_identity"]):
                body, note = prompt.split("\n中文说明：", 1)
                self.assertNotIn("成年男性", note)
                subject = profile["replace_subject_tags"][0]
                self.assertIn(subject, note)
                self.assertIn(prompt_builder._translate_prompt_fragment(subject), body)

    def test_track_variants_use_the_same_replacement_action_and_light(self):
        prompts, profiles = self.build(track="工业科幻")
        matched_relations = 0
        for prompt, profile in zip(prompts, profiles):
            with self.subTest(profile=profile["subject_identity"]):
                body, note = prompt.split("\n中文说明：", 1)
                self.assertNotIn("a relaxed standing pose", note)
                for key in ("replace_action_tags", "replace_light_tags"):
                    rendered_values = [
                        value for value in profile[key]
                        if prompt_builder._translate_prompt_fragment(value)
                        and prompt_builder._translate_prompt_fragment(value) in body
                    ]
                    if rendered_values:
                        matched_relations += 1
                        self.assertTrue(any(value in note for value in rendered_values))
                    else:
                        self.assertFalse(any(value in note for value in profile[key]))
        self.assertGreater(matched_relations, 0)

    def test_companion_does_not_change_the_existing_english_image_body(self):
        mixed, _ = self.build()
        english, _ = self.build(language="纯英文")
        self.assertEqual([prompt.split("\n中文说明：", 1)[0] for prompt in mixed], english)

    def test_nonrandom_note_keeps_current_anchors(self):
        prompts, _ = self.build(randomize=False, count=1)
        _, note = prompts[0].split("\n中文说明：", 1)
        self.assertIn("成年男性", note)
        self.assertIn("a quiet courtyard", note)
        self.assertIn("a relaxed standing pose", note)

    def test_note_does_not_reintroduce_a_style_discarded_from_the_final_fragments(self):
        selected = OrderedDict({
            "主体": ["成年男性"], "画面风格": ["真实感", "神殿"],
            "场景背景": ["a quiet courtyard"],
        })
        prompts, _ = self.build(randomize=False, selected=selected, count=1, style="真实感")
        body, note = prompts[0].split("\n中文说明：", 1)
        self.assertNotIn("temple", body)
        self.assertNotIn("神殿", note)


if __name__ == "__main__":
    unittest.main()
