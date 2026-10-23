"""Final video deduplication stays inside the configured storyboard contract."""
from __future__ import annotations

import json
import re
import unittest
from collections import OrderedDict
from unittest import mock

from test_stage_prompt_modules import load_stage_prompt_generator_for_integration_test, video_prompt_skill


class TestVideoDedupeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_stage_prompt_generator_for_integration_test()

    def build(self, language="纯中文", mode="FL2V", count="标准剧情", non_person=False):
        english = language == "纯英文"
        groups = OrderedDict({
            "主体": ["a mechanical clock" if english else "机械钟表"] if non_person else ["an adult detective" if english else "成年女性侦探"],
            "场景背景": ["an old station" if english else "旧车站"],
            "服装造型": ["a brass casing" if english else "黄铜外壳"] if non_person else ["a dark coat" if english else "深色风衣"],
            "动作姿态": ["its mechanism slowly turns" if english else "既有机构缓慢转动"] if non_person else ["turning to inspect" if english else "转身查看"],
        })
        settings = {
            "提示词语言": language, "主体类型": "非人物主体" if non_person else "人物角色",
            "视频提示词输入模式": mode, "视频提示词镜头段数": count, "seed": 41,
        }
        original = video_prompt_skill.build_video_prompt(groups, [], settings)
        settings["视频提示词Profile"] = video_prompt_skill.resolve_video_prompt_profile(settings)
        return original, settings

    def sections(self, text, language):
        if language == "英文提示词+中文说明":
            english, _, chinese = text.partition("中文说明：")
            return [(english.strip(), True), (chinese.strip(), False)]
        return [(text, language == "纯英文")]

    def test_variations_keep_sizes_reference_boundaries_and_natural_prose(self):
        module = self.module
        for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
            for mode in ("T2V", "I2V", "FL2V", "L2V", "Ref2V"):
                for count, expected in (("单镜头", 1), ("短动作", 3), ("标准剧情", 5), ("长剧情", 7)):
                    with self.subTest(language=language, mode=mode, count=count):
                        original, settings = self.build(language, mode, count)
                        first = module._strict_dedupe_prompt_list("", [original], settings, channel="video")[0]
                        varied = module._strict_dedupe_prompt_list("", [original], settings, channel="video")[0]
                        self.assertEqual(first, original)
                        self.assertNotEqual(varied, original)
                        self.assertTrue(video_prompt_skill.is_natural_video_prompt(varied, language=language))
                        self.assertEqual(video_prompt_skill.video_prompt_contract_violation(
                            varied, original, settings, language=language,
                        ), "")
                        originals = self.sections(original, language)
                        for (section, english), (before, _) in zip(self.sections(varied, language), originals):
                            shots = section.split("\n\n")
                            self.assertEqual(len(shots), expected)
                            if expected > 1:
                                self.assertEqual(shots[0], before.split("\n\n")[0])
                                self.assertEqual(shots[-1], before.split("\n\n")[-1])
                            else:
                                self.assertEqual(len(re.findall(r"(?im)^(?:shot|scene|分镜|镜头)\s*[0-9一二两三四五六七]+", section)), 1)
                                for marker in ("previous shot", "next shot", "上一分镜", "下一分镜"):
                                    self.assertNotIn(marker, section)
                            _, closing = video_prompt_skill._video_reference_prose(settings, english=english)
                            if closing:
                                self.assertTrue(shots[-1].endswith(closing))
                        metadata = video_prompt_skill.build_video_storyboard_metadata(varied, settings)
                        self.assertEqual([shot["number"] for shot in metadata], list(range(1, expected + 1)))

    def test_variation_pool_does_not_add_human_anatomy_or_unselected_props(self):
        for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
            original, settings = self.build(language, non_person=True)
            for cursor in (0, 4, 32, 64, 575):
                with self.subTest(language=language, cursor=cursor):
                    varied = self.module._append_video_variation_clause(original, cursor, settings)
                    for marker in ("手部", "呼吸", "脚步", "衣料", "发丝", "hands", "breathing", "footsteps", "fabric inertia"):
                        self.assertNotIn(marker, varied)
                    self.assertTrue(video_prompt_skill.is_natural_video_prompt(varied, language=language))
                    self.assertEqual(video_prompt_skill.video_prompt_contract_violation(
                        varied, original, settings, language=language,
                    ), "")

    def test_repeated_variation_replaces_inline_detail_without_adding_shots(self):
        for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
            original, settings = self.build(language, count="单镜头")
            first = self.module._append_video_variation_clause(original, 0, settings)
            second = self.module._append_video_variation_clause(first, 4, settings)
            for section, english in self.sections(second, language):
                marker = "Within this shot's existing action" if english else "在本镜已有动作内部"
                self.assertEqual(section.count(marker), 1)
                self.assertEqual(len(section.split("\n\n")), 1)
            self.assertEqual(video_prompt_skill.video_prompt_contract_violation(
                second, original, settings, language=language,
            ), "")

    def stage_kwargs(self, settings, cache=None):
        english = settings.get("提示词语言") == "纯英文"
        return {
            **{key: value for key, value in settings.items() if key != "视频提示词Profile"},
            "模型来源": "仅Skill", "主体标签1": "an adult detective" if english else "成年女性侦探",
            "服装造型标签1": "a dark coat" if english else "深色风衣",
            "场景背景标签1": "an old station" if english else "旧车站",
            "动作姿态标签1": "turning to inspect" if english else "转身查看", "生成数量": 1,
            "运行时随机标签": False, "连续生成避重缓存": json.dumps(cache or {}),
        }

    def test_final_stage_json_matches_requested_size_after_real_deduplication(self):
        for language, count, expected in (
            ("纯中文", "单镜头", 1), ("纯英文", "标准剧情", 5),
            ("英文提示词+中文说明", "单镜头", 1), ("英文提示词+中文说明", "标准剧情", 5),
            ("英文提示词+中文说明", "长剧情", 7),
        ):
            with self.subTest(language=language, count=count):
                original, settings = self.build(language, count=count)
                prompt_hash = self.module._canonical_prompt_hash(original)
                cache = {"version": 3, "channels": {"video": {
                    "cursor": 4, "hashes": [prompt_hash], "base_hashes": [prompt_hash],
                }}}
                with mock.patch.object(self.module, "_build_video_prompt_impl", return_value=original):
                    outputs = self.module._run_stage(None, **self.stage_kwargs(settings, cache))
                payload = json.loads(outputs[3])
                self.assertNotEqual(outputs[7], original)
                self.assertEqual(payload["video_prompt_profile"]["shot_count"], expected)
                self.assertEqual([shot["number"] for shot in payload["video_storyboard"]], list(range(1, expected + 1)))
                self.assertEqual(payload["video_prompt"], outputs[7])
                self.assertEqual(payload["video_prompt_skill_status"], "已生成")
                self.assertEqual(payload["model_call_attempt_count"], 0)

    def test_final_stage_rejects_natural_dedupe_that_drops_count_or_last_frame(self):
        original, settings = self.build()
        _, closing = video_prompt_skill._video_reference_prose(settings, english=False)
        extra_shot = original.split("\n\n")[-1].replace("分镜五", "分镜六").replace("（收束）", "（连续避重）")
        for bad in (original.replace(closing, ""), original + "\n\n" + extra_shot):
            with self.subTest(extra_shot=bad.endswith(extra_shot)):
                self.assertTrue(video_prompt_skill.is_natural_video_prompt(bad, language="纯中文"))
                dedupe = self.module._strict_dedupe_prompt_list

                def fake_dedupe(key, prompts, active_settings, *, channel="prompt"):
                    return [bad] if channel == "video" else dedupe(key, prompts, active_settings, channel=channel)

                with mock.patch.object(self.module, "_build_video_prompt_impl", return_value=original), mock.patch.object(
                    self.module, "_strict_dedupe_prompt_list", side_effect=fake_dedupe,
                ):
                    outputs = self.module._run_stage(None, **self.stage_kwargs(settings))
                payload = json.loads(outputs[3])
                self.assertEqual(outputs[7], original)
                self.assertEqual(len(payload["video_storyboard"]), 5)
                self.assertEqual(payload["video_prompt_skill_status"], "已生成")
                self.assertTrue(any("镜头数或参考素材合同" in note for note in payload["normalization_notes"]))


if __name__ == "__main__":
    unittest.main()
