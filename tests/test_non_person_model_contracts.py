"""Local and API polishers share the same subject-aware three-view contract."""
from __future__ import annotations

import unittest

from test_stage_prompt_modules import model_refiner, narrative


class TestNonPersonModelContracts(unittest.TestCase):
    def settings(self, language="纯中文", local=False):
        return {
            "主体类型": "非人物主体", "画面结构模式解析结果": "multi_view",
            "提示词语言": language, "模型来源": "本地模型" if local else "API接口",
            "内置模型系列": "Qwen3.8-VL" if local else "",
        }

    def prompt(self, english=False):
        return narrative.render_narrative_prompt({
            "subject": "a mechanical clock" if english else "机械钟表",
            "outfit": "a brass casing" if english else "黄铜外壳",
            "props": "one winding key" if english else "一把发条钥匙",
            "layout_mode": "multi_view", "image_target": "MOSS Image",
        }, {}, language="纯英文" if english else "纯中文", non_person=True)

    def test_api_and_local_system_prompts_do_not_require_character_features(self):
        for language in ("纯中文", "纯英文", "英文提示词+中文说明"):
            for local in (False, True):
                with self.subTest(language=language, local=local):
                    text = model_refiner._resolve_system_prompt(self.settings(language, local))
                    self.assertIn("非人物三视图", text)
                    self.assertIn("1:1:1", text)
                    for human_rule in ("三栏人物等高", "正脸", "鼻颌轮廓", "中性站姿", "matching face", "frontal face"):
                        self.assertNotIn(human_rule, text)

    def test_person_system_contract_is_unchanged(self):
        settings = {**self.settings(), "主体类型": "人物角色"}
        text = model_refiner._resolve_system_prompt(settings)
        self.assertIn(narrative.MULTI_VIEW_MODEL_CONTRACT, text)
        self.assertIn("正脸", text)

    def test_natural_object_views_are_adoptable_without_inventing_faces(self):
        for english in (False, True):
            with self.subTest(english=english):
                settings = self.settings("纯英文" if english else "纯中文")
                text = self.prompt(english)
                self.assertTrue(model_refiner.is_natural_language_prompt(text, settings))
                result, mode, reason = model_refiner._resolve_model_prompt_candidate(text, text, settings)
                self.assertNotEqual(mode, "rejected", reason)
                self.assertTrue(narrative.prompt_preserves_visual_layout(result, "multi_view", non_person=True))

    def test_non_person_validation_still_requires_three_distinct_views(self):
        incomplete = "机械钟表的正面视图展示黄铜外壳，材质纹理清晰，背景简洁，光线统一。"
        self.assertFalse(model_refiner.is_natural_language_prompt(incomplete, self.settings()))


if __name__ == "__main__":
    unittest.main()
