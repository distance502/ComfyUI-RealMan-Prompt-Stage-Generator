# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(relative_path: str, module_name: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cg_focus_suite = load_module("run_cg_style_focus_suite.py", "cg_style_focus_suite_test")


class TestCgStyleFocusSuite(unittest.TestCase):
    def test_build_negative_text_suppresses_text_artifacts(self) -> None:
        negative = cg_focus_suite.build_negative_text(cg_focus_suite.CG_CASE_PRESETS[0])
        for term in ["text", "watermark", "logo", "signature"]:
            self.assertIn(term, negative)

    def test_build_negative_text_agent_suppresses_poster_typography(self) -> None:
        negative = cg_focus_suite.build_negative_text(cg_focus_suite.CG_CASE_PRESETS[0])
        for term in ["poster", "typography", "billboard", "lettering", "subtitle"]:
            self.assertIn(term, negative)


if __name__ == "__main__":
    unittest.main()
