"""Complete same-language video requirements retain their temporal scope."""
from __future__ import annotations

import unittest
from collections import OrderedDict

from test_stage_prompt_modules import video_prompt_skill


SELECTED = OrderedDict({
    "主体": ["成年女性侦探"],
    "场景背景": ["旧车站"],
    "动作姿态": ["转身查看"],
    "服装造型": ["深色风衣"],
    "道具世界观": ["旧信封"],
    "构图视角": ["中景"],
})
ENGLISH_SELECTED = OrderedDict({
    "主体": ["an adult female detective"],
    "场景背景": ["an old station"],
    "动作姿态": ["turning to inspect"],
    "服装造型": ["a dark trench coat"],
    "道具世界观": ["an old envelope"],
    "构图视角": ["a medium shot"],
})
SHOT_MODES = (("单镜头", 1), ("短动作", 3), ("标准剧情", 5), ("长剧情", 7))
REQUIREMENTS = {
    "纯中文": {
        "source": "成年女性侦探身穿深色风衣，在旧车站转身查看旧信封。",
        "objective": "在旧车站调查线索",
        "persistent": "左手始终握着一把蓝色雨伞",
        "ending": "把雨伞靠在长椅上",
        "extra": "在旧车站调查线索。左手始终握着一把蓝色雨伞，结尾把雨伞靠在长椅上。",
    },
    "纯英文": {
        "source": "An adult female detective in a dark trench coat inspects an old envelope at an old station.",
        "objective": "She investigates clues at the old station",
        "persistent": "She keeps holding a blue umbrella in her left hand",
        "ending": "she leans the umbrella against a bench",
        "extra": (
            "She investigates clues at the old station. "
            "She keeps holding a blue umbrella in her left hand. "
            "Finally, she leans the umbrella against a bench."
        ),
    },
}


class TestVideoSourceRequirements(unittest.TestCase):
    def build(self, language="纯中文", count="标准剧情", **overrides):
        facts = REQUIREMENTS[language]
        settings = {
            "提示词语言": language, "主体类型": "人物角色", "seed": 41,
            "视频提示词镜头段数": count, "额外要求": facts["extra"],
            **overrides,
        }
        selected = ENGLISH_SELECTED if language == "纯英文" else SELECTED
        text = video_prompt_skill.build_video_prompt(
            selected, [], settings, primary_prompt=facts["source"],
        )
        return text, settings

    def assert_temporal_requirements(self, text, language, expected_count):
        facts = REQUIREMENTS[language]
        shots = text.strip().split("\n\n")
        self.assertEqual(len(shots), expected_count)
        self.assertIn(facts["objective"], text)
        if expected_count > 1:
            self.assertIn(facts["objective"], "\n\n".join(shots[:-1]))
        for index, shot in enumerate(shots):
            self.assertEqual(shot.count(facts["persistent"]), 1, f"persistent state in shot {index + 1}")
            if index < expected_count - 1:
                self.assertNotIn(facts["ending"], shot)
        self.assertEqual(text.count(facts["ending"]), 1)
        self.assertIn(facts["ending"], shots[-1])
        self.assertLess(shots[-1].index(facts["persistent"]), shots[-1].index(facts["ending"]))
        if expected_count == 1:
            self.assertLess(shots[0].index(facts["objective"]), shots[0].index(facts["ending"]))
        self.assertTrue(video_prompt_skill.is_natural_video_prompt(text, language=language))

    def test_multisentence_requirements_survive_all_shot_counts(self):
        for language in REQUIREMENTS:
            for count, expected in SHOT_MODES:
                with self.subTest(language=language, count=count):
                    text, _ = self.build(language, count)
                    self.assert_temporal_requirements(text, language, expected)

    def test_both_text_sources_merge_without_duplicate_requirements(self):
        for language, facts in REQUIREMENTS.items():
            for count, expected in SHOT_MODES:
                with self.subTest(language=language, count=count):
                    text, _ = self.build(
                        language, count, 智能文本输入=facts["extra"],
                    )
                    self.assert_temporal_requirements(text, language, expected)
                    self.assertEqual(text.count(facts["objective"]), 1)

    def test_smart_text_does_not_hide_additional_requirements(self):
        for language, facts in REQUIREMENTS.items():
            with self.subTest(language=language):
                text, _ = self.build(
                    language,
                    智能文本输入=facts["objective"] + ("." if language == "纯英文" else "。"),
                )
                self.assert_temporal_requirements(text, language, 5)
                self.assertEqual(text.count(facts["objective"]), 1)

    def test_unmarked_sentences_keep_source_order_before_the_actual_ending(self):
        cases = {
            "纯中文": (
                ["她查看铜制时刻表", "她走到封闭售票窗前", "她核对衣袋里的纸质车票", "她沿地面标记走向站台"],
                "最后她停在黄色安全线内侧", "。",
            ),
            "纯英文": (
                [
                    "She studies the brass timetable", "She walks to the shuttered ticket window",
                    "She checks the paper ticket in her pocket", "She follows the floor markings toward the platform",
                ],
                "Finally, she stops behind the yellow safety line", ". ",
            ),
        }
        for language, (clauses, ending, separator) in cases.items():
            for count, expected in SHOT_MODES:
                with self.subTest(language=language, count=count):
                    extra = separator.join([*clauses, ending]) + separator.strip()
                    text, _ = self.build(language, count, 额外要求=extra)
                    shots = text.strip().split("\n\n")
                    self.assertEqual(len(shots), expected)
                    indices = [text.index(clause) for clause in clauses]
                    self.assertEqual(indices, sorted(indices))
                    for clause in clauses:
                        self.assertEqual(text.count(clause), 1)
                        if expected > 1:
                            self.assertNotIn(clause, shots[-1])
                    terminal = "停在黄色安全线内侧" if language == "纯中文" else "stops behind the yellow safety line"
                    self.assertIn(terminal, shots[-1])
                    self.assertNotIn(terminal, "\n\n".join(shots[:-1]))

    def test_explicit_opening_remains_in_first_shot(self):
        cases = (
            ("纯中文", "开场她观察站台尽头的红色钟面。", "观察站台尽头的红色钟面"),
            ("纯英文", "Initially, she observes a red clock at the far end of the platform. ", "observes a red clock at the far end of the platform"),
            ("纯英文", "At the opening, she observes a red clock at the far end of the platform. ", "observes a red clock at the far end of the platform"),
        )
        for language, opening, visible_action in cases:
            with self.subTest(language=language, opening=opening):
                extra = REQUIREMENTS[language]["extra"] + (" " if language == "纯英文" else "") + opening
                text, _ = self.build(language, "长剧情", 额外要求=extra)
                shots = text.strip().split("\n\n")
                self.assertIn(visible_action, shots[0])
                self.assertNotIn(visible_action, "\n\n".join(shots[1:]))

    def test_long_source_sentences_are_not_truncated(self):
        cases = {
            "纯中文": (
                "她先逐一核对旧车站北侧砖墙上悬挂的十二块旧式铜制时刻表，"
                "并且按照由左向右的顺序观察每块时刻表边缘留下的磨损和维修标记，"
                "同时把票窗玻璃上的反射与身后立柱的位置逐一对应，"
                "随后沿着没有积水的地面区域缓慢移动，始终留意地砖裂缝之间的距离变化，"
                "最后在走廊转角处仔细辨认一块被灰尘覆盖但仍然能够读出文字的铭牌，"
                "其中最重要的发现是右侧铭牌上刻着七位站台编号，"
                "她把这个编号与手中旧信封背面的铅笔字迹进行完整核对",
                ("十二块旧式铜制时刻表", "票窗玻璃上的反射", "七位站台编号", "旧信封背面的铅笔字迹"),
            ),
            "纯英文": (
                "She carefully compares the twelve brass timetables on the north wall of the old station, "
                "checks their worn edges and repair marks from left to right, "
                "aligns the reflections on the ticket window with the pillars behind her, "
                "and records the seven-digit platform number engraved on the dusty plate beside the corridor",
                ("twelve brass timetables", "repair marks from left to right", "reflections on the ticket window", "seven-digit platform number"),
            ),
        }
        for language, (sentence, fragments) in cases.items():
            with self.subTest(language=language):
                self.assertGreater(len(sentence), 160)
                text, _ = self.build(language, "长剧情", 额外要求=sentence + ("." if language == "纯英文" else "。"))
                for fragment in fragments:
                    self.assertIn(fragment, text)
                    self.assertEqual(text.count(fragment), 1)

    def test_short_complete_sentences_are_not_dropped(self):
        text, _ = self.build(额外要求="她等雨。她抬头。")
        self.assertIn("她等雨", text)
        self.assertIn("她抬头", text)
        self.assertLess(text.index("她等雨"), text.index("她抬头"))

    def test_quoted_dialogue_keeps_its_punctuation_and_stays_in_one_shot(self):
        cases = (
            (
                "纯中文", "“等一下。你听见钟声了吗？别动！”",
                "她低声说：“等一下。你听见钟声了吗？别动！”随后她看向入口。结尾她合上信封。",
            ),
            (
                "纯中文", "「等一下。你听见钟声了吗?别动！」",
                "她低声说：「等一下。你听见钟声了吗?别动！」随后她看向入口。结尾她合上信封。",
            ),
            (
                "纯英文", '"Wait here. Did you hear the bell? Stay still!"',
                'She says, "Wait here. Did you hear the bell? Stay still!" Then she looks toward the entrance. Finally, she closes the envelope.',
            ),
        )
        for language, dialogue, source in cases:
            for count, _ in SHOT_MODES:
                with self.subTest(language=language, count=count, dialogue=dialogue):
                    text, _ = self.build(language, count, 额外要求=source)
                    self.assertEqual(text.count(dialogue), 1)
                    shots = text.strip().split("\n\n")
                    self.assertEqual(sum(dialogue in shot for shot in shots), 1)

    def test_abbreviated_names_are_not_split_across_shots(self):
        sentences = (
            "Dr. Chen walks toward the station clock.",
            "Prof. Lin examines the ticket window.",
        )
        source = " ".join([*sentences, "Finally, they stop behind the safety line."])
        for count, _ in SHOT_MODES:
            with self.subTest(count=count):
                text, _ = self.build("纯英文", count, 额外要求=source)
                shots = text.strip().split("\n\n")
                for sentence in sentences:
                    self.assertEqual(text.count(sentence), 1)
                    self.assertEqual(sum(sentence in shot for shot in shots), 1)

    def test_last_item_and_end_of_location_are_not_terminal_markers(self):
        cases = (
            ("纯中文", "最后一个信封放在桌上。结尾她抬头。", "最后一个信封放在桌上"),
            (
                "纯英文",
                "At the end of the platform stands a clock. Finally, she closes the envelope.",
                "At the end of the platform stands a clock",
            ),
        )
        for language, source, fact in cases:
            for count, expected in SHOT_MODES:
                with self.subTest(language=language, count=count):
                    text, _ = self.build(language, count, 额外要求=source)
                    self.assertEqual(text.count(fact), 1)
                    if expected > 1:
                        shots = text.strip().split("\n\n")
                        self.assertIn(fact, "\n\n".join(shots[:-1]))
                        self.assertNotIn(fact, shots[-1])

    def test_identical_opening_and_terminal_actions_keep_both_phases(self):
        cases = (
            ("纯中文", "开场她看向车站。结尾她看向车站。", "她看向车站"),
            (
                "纯英文",
                "Initially, she looks toward the station. Finally, she looks toward the station.",
                "she looks toward the station",
            ),
        )
        for language, source, action in cases:
            for count, expected in SHOT_MODES:
                with self.subTest(language=language, count=count):
                    text, _ = self.build(language, count, 额外要求=source)
                    self.assertEqual(text.count(action), 2)
                    if expected > 1:
                        shots = text.strip().split("\n\n")
                        self.assertEqual(shots[0].count(action), 1)
                        self.assertEqual(shots[-1].count(action), 1)
                        self.assertNotIn(action, "\n\n".join(shots[1:-1]))

    def test_later_source_actions_do_not_restore_an_earlier_persistent_state(self):
        cases = (
            (
                "纯中文", "她一直握着蓝色雨伞", "她把雨伞放到门边", "她走向站台", "。",
            ),
            (
                "纯英文", "She holds a blue umbrella throughout the walk",
                "She puts the umbrella beside the gate", "She walks toward the platform", ". ",
            ),
        )
        for language, holding, placement, departure, separator in cases:
            source = separator.join((holding, placement, departure)) + separator.strip()
            for count, expected in SHOT_MODES:
                with self.subTest(language=language, count=count):
                    text, _ = self.build(language, count, 额外要求=source)
                    shots = text.strip().split("\n\n")
                    self.assertEqual(len(shots), expected)
                    self.assertIn(holding, text)
                    self.assertEqual(text.count(placement), 1)
                    self.assertEqual(text.count(departure), 1)
                    self.assertLess(text.rindex(holding), text.index(placement))
                    self.assertLess(text.index(placement), text.index(departure))
                    placement_shot = next(index for index, shot in enumerate(shots) if placement in shot)
                    for shot in shots[placement_shot + 1:]:
                        self.assertNotIn(holding, shot)

    def test_terminal_requirements_precede_the_supplied_last_frame_contract(self):
        for language in REQUIREMENTS:
            for mode in ("FL2V", "L2V"):
                for count, expected in SHOT_MODES:
                    with self.subTest(language=language, mode=mode, count=count):
                        text, settings = self.build(language, count, 视频提示词输入模式=mode)
                        self.assert_temporal_requirements(text, language, expected)
                        closing = video_prompt_skill._video_reference_prose(settings, english=language == "纯英文")[1]
                        self.assertTrue(text.rstrip().endswith(closing))
                        last = text.strip().split("\n\n")[-1]
                        self.assertLess(last.index(REQUIREMENTS[language]["ending"]), last.index(closing))
                        self.assertEqual(video_prompt_skill.video_prompt_contract_violation(
                            text, text, settings, language=language,
                        ), "")

    def test_no_unsupported_release_action_is_inferred(self):
        for language in REQUIREMENTS:
            with self.subTest(language=language):
                text, _ = self.build(language)
                if language == "纯中文":
                    for inferred in ("松开左手", "松开雨伞", "丢下雨伞"):
                        self.assertNotIn(inferred, text)
                else:
                    for inferred in ("releases the umbrella", "drops the umbrella", "lets go of the umbrella"):
                        self.assertNotIn(inferred, text.casefold())

    def test_bilingual_output_does_not_gain_untranslated_one_sided_requirements(self):
        for language, facts in REQUIREMENTS.items():
            with self.subTest(source_language=language):
                settings = {
                    "提示词语言": "英文提示词+中文说明", "主体类型": "人物角色",
                    "视频提示词镜头段数": "长剧情", "额外要求": facts["extra"], "seed": 41,
                }
                text = video_prompt_skill.build_video_prompt(SELECTED, [], settings, primary_prompt=REQUIREMENTS["纯英文"]["source"])
                self.assertIn("中文说明：", text)
                for marker in ("蓝色雨伞", "长椅", "blue umbrella", "against a bench"):
                    self.assertNotIn(marker, text)

    def test_multi_view_projection_does_not_revive_raw_sheet_requirements(self):
        facts = REQUIREMENTS["纯中文"]
        settings = {
            "提示词语言": "纯中文", "主体类型": "人物角色", "seed": 41,
            "画面结构模式解析结果": "multi_view", "视频提示词镜头段数": "长剧情",
            "额外要求": "三栏等高基线，正面、侧面、背面。" + facts["extra"],
            "智能文本输入": "三视图参考设定表。" + facts["extra"],
        }
        projected = video_prompt_skill.project_video_story_settings(SELECTED, [], settings)
        self.assertEqual(projected["额外要求"], "")
        self.assertEqual(projected["智能文本输入"], "")
        for story_settings in (settings, projected):
            with self.subTest(projected=story_settings is projected):
                text = video_prompt_skill.build_video_prompt(
                    SELECTED, [], story_settings,
                    primary_prompt="三栏等高基线，正面、侧面、背面。" + facts["extra"],
                )
                self.assertFalse(video_prompt_skill.video_prompt_has_layout_contamination(text))
                for marker in ("蓝色雨伞", "长椅", "三栏等高基线"):
                    self.assertNotIn(marker, text)


if __name__ == "__main__":
    unittest.main()
