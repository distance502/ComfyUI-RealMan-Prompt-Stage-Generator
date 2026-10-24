"""The Chinese explanation must describe the English storyboard's actual story."""
from __future__ import annotations

import unittest
from collections import OrderedDict
from unittest import mock

from test_stage_prompt_modules import video_prompt_skill


SELECTED = OrderedDict({
    "主体": ["成年女性侦探"],
    "场景背景": ["旧车站"],
    "动作姿态": ["转身查看"],
    "服装造型": ["深色风衣"],
    "道具世界观": ["旧信封"],
    "构图视角": ["中景"],
    "光影氛围": ["青蓝侧光"],
})
SOURCE = "An adult detective in a dark coat holds an old envelope at an old station."


class TestVideoBilingualStoryPlan(unittest.TestCase):
    def build(self, settings):
        plans = []
        original = video_prompt_skill.build_narrative_plan

        def record_plan(*args, **kwargs):
            plan = original(*args, **kwargs)
            plans.append(plan)
            return plan

        with mock.patch.object(video_prompt_skill, "build_narrative_plan", side_effect=record_plan):
            text = video_prompt_skill.build_video_prompt(SELECTED, [], settings, primary_prompt=SOURCE)
        return text, plans

    def test_bilingual_story_beats_share_the_same_plan(self):
        for seed in (0, 1, 7, 41):
            for count in ("短动作", "标准剧情", "长剧情"):
                with self.subTest(seed=seed, count=count):
                    text, plans = self.build({
                        "提示词语言": "英文提示词+中文说明", "主体类型": "人物角色",
                        "视频提示词镜头段数": count, "seed": seed,
                    })
                    self.assertEqual(len(plans), 1)
                    english, marker, chinese = text.partition("中文说明：")
                    self.assertTrue(marker)
                    beats = ["opening", "motive", "ending"]
                    if count != "短动作":
                        beats.extend(["trigger", "turn"])
                    for beat in beats:
                        with self.subTest(beat=beat):
                            self.assertIn(plans[0][beat + "_en"].casefold(), english.casefold())
                            expected = plans[0][beat + "_zh"].replace("主体", "她").replace("当前空间", "旧车站")
                            self.assertIn(expected, chinese)
                    self.assertTrue(video_prompt_skill.is_natural_video_prompt(
                        text, language="英文提示词+中文说明",
                    ))

    def test_shared_plan_keeps_shot_count_and_reference_contracts(self):
        for mode in video_prompt_skill.VIDEO_PROMPT_INPUT_MODE_OPTIONS:
            for count, expected in (("单镜头", 1), ("短动作", 3), ("标准剧情", 5), ("长剧情", 7)):
                with self.subTest(mode=mode, count=count):
                    settings = {
                        "提示词语言": "英文提示词+中文说明", "主体类型": "人物角色",
                        "视频提示词输入模式": mode, "视频提示词镜头段数": count, "seed": 41,
                    }
                    text, plans = self.build(settings)
                    self.assertEqual(len(plans), 1)
                    self.assertEqual(video_prompt_skill.video_prompt_contract_violation(
                        text, text, settings, language="英文提示词+中文说明",
                    ), "")
                    english, _, chinese = text.partition("中文说明：")
                    self.assertEqual(len(english.strip().split("\n\n")), expected)
                    self.assertEqual(len(chinese.strip().split("\n\n")), expected)
                    metadata = video_prompt_skill.build_video_storyboard_metadata(text, settings, selected=SELECTED)
                    self.assertEqual([shot["number"] for shot in metadata], list(range(1, expected + 1)))
                    self.assertEqual([shot["description"] for shot in metadata], chinese.strip().split("\n\n"))

    def test_single_language_rendering_keeps_its_existing_plan_inputs(self):
        for language in ("纯中文", "纯英文"):
            with self.subTest(language=language):
                settings = {"提示词语言": language, "主体类型": "人物角色", "seed": 41}
                text, plans = self.build(settings)
                groups = video_prompt_skill._normalized_groups(SELECTED, [], settings, include_preferences=True)
                source = video_prompt_skill._video_story_source(groups, settings, SOURCE)
                if language == "纯中文":
                    expected = video_prompt_skill._build_chinese_video_prompt(groups, settings, primary_prompt=source)
                else:
                    expected = video_prompt_skill._build_english_video_prompt(settings, primary_prompt=source, groups=groups)
                self.assertEqual(text, expected)
                self.assertEqual(len(plans), 1)


if __name__ == "__main__":
    unittest.main()
