# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures"
PROMPT_LIBRARY_SNAPSHOT_PATH = ROOT / "prompt_library_snapshot.json"


class TestFixtureContracts(unittest.TestCase):
    def _load_prompt_library_tag_sets(self) -> dict[str, set[str]]:
        payload = json.loads(PROMPT_LIBRARY_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        tag_sets: dict[str, set[str]] = {}
        for section_name, section_groups in payload.get("tag_library", {}).items():
            values: set[str] = set()
            for group_values in section_groups.values():
                values.update(group_values)
            custom_groups = payload.get("custom_tag_library", {}).get(section_name, {})
            for group_values in custom_groups.values():
                values.update(group_values)
            tag_sets[section_name] = values
        return tag_sets

    def _resolve_style_mode_section(self, tag_key: str) -> str | None:
        if tag_key.startswith("主体标签"):
            return "主体"
        if tag_key.startswith("画面风格标签"):
            return "画面风格"
        if tag_key.startswith("光影氛围标签"):
            return "光影氛围"
        if tag_key.startswith("构图视角标签"):
            return "构图视角"
        if tag_key.startswith("动作姿态标签"):
            return "动作姿态"
        if tag_key.startswith("服装造型标签"):
            return "服装造型"
        if tag_key.startswith("场景背景标签"):
            return "场景背景"
        if tag_key.startswith("道具世界观标签"):
            return "道具世界观"
        if tag_key.startswith("技术画质标签"):
            return "技术画质"
        return None

    def test_brief_cases_fixture_shape(self) -> None:
        payload = json.loads((FIXTURES_DIR / "brief_cases.json").read_text(encoding="utf-8"))
        self.assertIsInstance(payload, dict)
        self.assertTrue(payload)
        for case_name, case in payload.items():
            self.assertTrue(case_name)
            self.assertIsInstance(case, dict)
            self.assertIsInstance(case.get("selected"), dict)
            self.assertIsInstance(case.get("custom_tags"), list)
            self.assertIsInstance(case.get("expected"), dict)

    def test_model_loader_supports_broader_family_contract(self) -> None:
        source = (ROOT / "nodes.py").read_text(encoding="utf-8")
        self.assertIn("TE通用模型系列选项", source)
        for family in ("Qwen3-VL", "Qwen3.5-VL", "Gemma4", "Llama", "Mistral", "DeepSeek", "通用GGUF"):
            self.assertIn(f'"{family}"', source)
        self.assertIn('"模型系列": (TE通用模型系列选项', source)
        self.assertIn('elif family == "Gemma4"', source)
        self.assertIn('return "llama-3"', source)
        self.assertIn('return "mistral-instruct"', source)

    def test_regression_cases_fixture_shape(self) -> None:
        payload = json.loads((FIXTURES_DIR / "regression_cases.json").read_text(encoding="utf-8"))
        self.assertIsInstance(payload, dict)
        case_groups = payload.get("case_groups")
        self.assertIsInstance(case_groups, dict)
        cases = payload.get("cases")
        self.assertIsInstance(cases, list)
        self.assertGreaterEqual(len(cases), 2)
        seen_names: set[str] = set()
        for case in cases:
            self.assertIsInstance(case, dict)
            name = str(case.get("name", "")).strip()
            self.assertTrue(name)
            self.assertNotIn(name, seen_names)
            seen_names.add(name)
            self.assertIn(name, case_groups)
            self.assertIsInstance(case_groups[name], str)
            self.assertTrue(case_groups[name].strip())
            self.assertIsInstance(case.get("stage"), dict)
            self.assertIsInstance(case.get("expect"), dict)
            self.assertIsInstance(case.get("image", False), bool)
            expect = case["expect"]
            if "must_contain" in expect:
                self.assertIsInstance(expect["must_contain"], list)
            if "must_not_contain" in expect:
                self.assertIsInstance(expect["must_not_contain"], list)

    def test_style_mode_cases_fixture_shape(self) -> None:
        payload = json.loads((FIXTURES_DIR / "style_mode_cases.json").read_text(encoding="utf-8"))
        prompt_library_tag_sets = self._load_prompt_library_tag_sets()
        self.assertIsInstance(payload, dict)
        cases = payload.get("cases")
        self.assertIsInstance(cases, list)
        self.assertGreaterEqual(len(cases), 5)
        seen_names: set[str] = set()
        seen_styles: set[str] = set()
        for case in cases:
            self.assertIsInstance(case, dict)
            name = str(case.get("name", "")).strip()
            self.assertTrue(name)
            self.assertNotIn(name, seen_names)
            seen_names.add(name)
            self.assertEqual(case.get("group"), "style_mode")
            self.assertIs(case.get("image"), False)
            self.assertIsInstance(case.get("stage"), dict)
            self.assertIsInstance(case.get("expect"), dict)
            style = str(case["stage"].get("模板风格", "")).strip()
            self.assertTrue(style)
            seen_styles.add(style)
            for tag_key, tag_value in case["stage"].items():
                section_name = self._resolve_style_mode_section(tag_key)
                if section_name is None:
                    continue
                if not tag_key.endswith(tuple(str(index) for index in range(1, 5))):
                    continue
                self.assertIn(
                    tag_value,
                    prompt_library_tag_sets.get(section_name, set()),
                    msg=f"{case['name']} -> {tag_key}={tag_value!r} is not valid for {section_name}",
                )
        self.assertEqual(seen_styles, {"真实感", "插画感", "CG感", "古风", "神话感"})
        expected_keys = {
            "style_mode_realistic",
            "style_mode_illustration",
            "style_mode_cg",
            "style_mode_ancient",
            "style_mode_myth",
        }
        self.assertEqual(seen_names, expected_keys)
        for case in cases:
            expect = case["expect"]
            self.assertGreaterEqual(len(expect.get("must_contain", [])), 5)
            self.assertGreaterEqual(len(expect.get("must_not_contain", [])), 5)


if __name__ == "__main__":
    unittest.main()
