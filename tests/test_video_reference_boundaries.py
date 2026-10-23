"""Reference-frame continuity must survive every storyboard-size projection."""
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
    "光影氛围": ["青蓝侧光"],
})
ENGLISH_SELECTED = OrderedDict({
    "主体": ["an adult detective"],
    "场景背景": ["an old station"],
    "动作姿态": ["turning to inspect"],
    "服装造型": ["a dark coat"],
    "道具世界观": ["an old envelope"],
    "构图视角": ["a medium shot"],
    "光影氛围": ["cool side lighting"],
})


class TestVideoReferenceBoundaries(unittest.TestCase):
    def build(self, language, mode, count):
        settings = {
            "提示词语言": language, "视频提示词输入模式": mode,
            "视频提示词镜头段数": count, "主体类型": "人物角色", "seed": 41,
        }
        selected = ENGLISH_SELECTED if language == "纯英文" else SELECTED
        return video_prompt_skill.build_video_prompt(selected, [], settings), settings

    def test_reference_constraints_follow_actual_first_and_last_shots(self):
        for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
            for mode in ("I2V", "FL2V", "L2V", "Ref2V"):
                for count in ("单镜头", "短动作", "标准剧情", "长剧情"):
                    with self.subTest(language=language, mode=mode, count=count):
                        text, _ = self.build(language, mode, count)
                        sections = [(text, language == "纯英文")]
                        if language == "英文提示词+中文说明":
                            english, _, chinese = text.partition("中文说明：")
                            sections = [(english, True), (chinese, False)]
                        for section, english in sections:
                            shots = section.strip().split("\n\n")
                            opening, closing = video_prompt_skill._video_reference_prose(
                                {"视频提示词输入模式": mode}, english=english,
                            )
                            self.assertIn(opening, shots[0])
                            if closing:
                                self.assertTrue(shots[-1].rstrip().endswith(closing))
                                if len(shots) > 1:
                                    self.assertNotIn(closing, "\n\n".join(shots[:-1]))
                        self.assertTrue(video_prompt_skill.is_natural_video_prompt(text, language=language))

    def test_single_shot_is_self_contained_instead_of_referring_to_absent_shots(self):
        for language, selected in (("纯中文", SELECTED), ("纯英文", ENGLISH_SELECTED)):
            for mode in video_prompt_skill.VIDEO_PROMPT_INPUT_MODE_OPTIONS:
                with self.subTest(language=language, mode=mode):
                    text, _ = self.build(language, mode, "单镜头")
                    self.assertEqual(len(text.split("\n\n")), 1)
                    for group in ("主体", "场景背景", "服装造型", "道具世界观"):
                        self.assertIn(selected[group][0], text)
                    for marker in ("上一分镜", "下一分镜", "preceding clue", "previous shot", "next shot"):
                        self.assertNotIn(marker, text)

    def test_supplied_frames_do_not_also_force_template_composition(self):
        for mode in ("I2V", "FL2V"):
            for language in ("纯中文", "纯英文"):
                with self.subTest(language=language, mode=mode):
                    text, _ = self.build(language, mode, "标准剧情")
                    first = text.split("\n\n")[0]
                    self.assertNotIn("位于画面中心偏前", first)
                    self.assertNotIn("The camera opens on a medium shot", first)
        for mode in ("FL2V", "L2V"):
            text, _ = self.build("纯英文", mode, "标准剧情")
            self.assertNotIn("The final image preserves a medium shot", text)

    def test_english_reference_modes_keep_source_facts_when_tags_are_chinese(self):
        source = (
            "A medium shot of a mechanical probe turns slowly along a rail in an underground laboratory, "
            "with a red warning lamp."
        )
        selected = OrderedDict({
            "主体": ["机械探测器"], "场景背景": ["地下实验室"],
            "动作姿态": ["沿轨道缓慢转向"], "道具世界观": ["红色警示灯"],
        })
        for mode in ("I2V", "FL2V"):
            for count in ("单镜头", "标准剧情", "长剧情"):
                with self.subTest(mode=mode, count=count):
                    settings = {
                        "提示词语言": "纯英文", "视频提示词输入模式": mode,
                        "视频提示词镜头段数": count, "主体类型": "非人物主体",
                    }
                    text = video_prompt_skill.build_video_prompt(selected, [], settings, primary_prompt=source)
                    first = text.split("\n\n")[0]
                    for fact in ("mechanical probe", "rail", "underground laboratory", "red warning lamp"):
                        self.assertIn(fact, first)
                    self.assertNotIn("medium shot", first.casefold())
                    self.assertNotIn("wore", first)
                    self.assertTrue(video_prompt_skill.is_natural_video_prompt(text, language="纯英文"))

    def test_reference_framing_cleanup_preserves_outfit_and_prop_facts(self):
        source = "A detective in a wide-brim hat holds a camera in a wide shot, beside an old envelope."
        cleaned = video_prompt_skill._english_source_clause(source, reference_framing=True)
        self.assertIn("wide-brim hat", cleaned)
        self.assertIn("holds a camera", cleaned)
        self.assertIn("old envelope", cleaned)
        self.assertNotIn("in a wide shot", cleaned)
        self.assertIn("in a wide shot", video_prompt_skill._english_source_clause(source))

    def test_non_person_video_does_not_acquire_hands_clothing_or_footsteps(self):
        for language in ("纯中文", "纯英文"):
            for seed in range(12):
                with self.subTest(language=language, seed=seed):
                    english = language == "纯英文"
                    selected = OrderedDict({
                        "主体": ["a mechanical clock" if english else "机械钟表"],
                        "场景背景": ["a station in the rain" if english else "雨夜旧车站"],
                        "服装造型": ["a brass casing" if english else "黄铜外壳"],
                        "动作姿态": ["its existing mechanism slowly turns" if english else "既有机构缓慢转动"],
                    })
                    settings = {"提示词语言": language, "主体类型": "非人物主体", "seed": seed}
                    text = video_prompt_skill.build_video_prompt(selected, [], settings)
                    for marker in ("手部", "手势", "呼吸", "衣料", "衣摆", "发丝", "表情", "它的视线", "footsteps", "hands", "breathing", "garment", "The emotion shifts", "emotional aftertone"):
                        self.assertNotIn(marker, text)
                    self.assertTrue(video_prompt_skill.is_natural_video_prompt(text, language=language))
                    metadata = video_prompt_skill.build_video_storyboard_metadata(text, settings, selected=selected)
                    self.assertNotIn("脚步" if not english else "footsteps", metadata[0]["sound_effects"])

    def test_non_person_plan_projection_does_not_rewrite_explicit_subject_facts(self):
        projected = video_prompt_skill._non_person_video_plan({
            "feedback_zh": "衣料、草木、烟雾随动作改变", "turn_en": "The emotion shifts through a change of gaze",
            "opening_zh": "表盘中央的机械手臂保持原位", "signature": "unchanged",
        })
        self.assertNotIn("衣料", projected["feedback_zh"])
        self.assertNotIn("emotion", projected["turn_en"].casefold())
        self.assertEqual(projected["opening_zh"], "表盘中央的机械手臂保持原位")
        self.assertEqual(projected["signature"], "unchanged")

    def test_single_shot_metadata_does_not_refer_to_absent_shots(self):
        for language in ("纯中文", "纯英文"):
            with self.subTest(language=language):
                text, settings = self.build(language, "FL2V", "单镜头")
                metadata = video_prompt_skill.build_video_storyboard_metadata(text, settings)
                self.assertEqual(len(metadata), 1)
                handoff = metadata[0]["continuity_handoff"]
                for marker in ("上一镜头", "下一镜头", "previous shot", "next shot"):
                    self.assertNotIn(marker, handoff)
                self.assertIn("连续镜头" if language == "纯中文" else "one continuous take", handoff)

    def test_non_person_english_material_anchor_is_not_described_as_clothing(self):
        groups = OrderedDict({"主体": ["a mechanical clock"], "服装造型": ["a brass casing"]})
        text = video_prompt_skill.build_video_prompt(groups, [], {
            "主体类型": "非人物主体", "提示词语言": "纯英文",
        })
        self.assertIn("the exterior construction is a brass casing", text)
        self.assertNotIn("the outfit", text)
        self.assertIn("the outfit is a brass casing", video_prompt_skill._english_anchor_sentence(groups))


if __name__ == "__main__":
    unittest.main()
