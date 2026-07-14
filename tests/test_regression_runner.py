# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
from unittest import mock
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


runner = load_module("stage_prompt_regression_runner.py", "stage_prompt_regression_runner_test")
template_suite = load_module("run_template_example_suite.py", "run_template_example_suite_test")
auto_pool_suite = load_module("run_auto_theme_pool_comparison.py", "run_auto_theme_pool_comparison_test")
auto_pool_five_mode_stage_suite = load_module("run_auto_theme_pool_five_mode_stage_check.py", "run_auto_theme_pool_five_mode_stage_check_test")
auto_pool_five_mode_full_suite = load_module("run_auto_theme_pool_five_mode_full_comparison.py", "run_auto_theme_pool_five_mode_full_comparison_test")


class TestRegressionRunner(unittest.TestCase):
    def test_normalize_case_entry_applies_group(self) -> None:
        case = runner.normalize_case_entry({"name": "alpha", "stage": {}, "expect": {}}, group_name="realistic")
        self.assertEqual(case["group"], "realistic")

    def test_sanitize_report_suffix_normalizes_text(self) -> None:
        self.assertEqual(runner.sanitize_report_suffix("  campus run / A "), "campus_run_A")

    def test_list_case_names_deduplicates_and_preserves_order(self) -> None:
        cases = [
            {"name": "alpha", "stage": {}, "expect": {}},
            {"name": "beta", "stage": {}, "expect": {}},
            {"name": "alpha", "stage": {}, "expect": {}},
            {"name": " ", "stage": {}, "expect": {}},
        ]
        self.assertEqual(runner.list_case_names(cases), ["alpha", "beta"])

    def test_list_grouped_case_names_uses_group_order(self) -> None:
        cases = [
            {"name": "zeta", "stage": {}, "expect": {}, "group": "conflict"},
            {"name": "alpha", "stage": {}, "expect": {}, "group": "realistic"},
            {"name": "beta", "stage": {}, "expect": {}, "group": "private"},
        ]
        grouped = runner.list_grouped_case_names(cases)
        self.assertEqual(list(grouped.keys())[:3], ["realistic", "private", "conflict"])
        self.assertEqual(grouped["realistic"], ["alpha"])

    def test_resolve_requested_case_names(self) -> None:
        resolved = runner.resolve_requested_case_names(["case_a, case_b", "case_b", "case_c"])
        self.assertEqual(resolved, ["case_a", "case_b", "case_c"])

    def test_resolve_requested_group_names(self) -> None:
        resolved = runner.resolve_requested_group_names(["realistic, sacred", "SACRED", "conflict"])
        self.assertEqual(resolved, ["realistic", "sacred", "conflict"])

    def test_select_cases_filters_and_preserves_requested_order(self) -> None:
        cases = [
            {"name": "alpha", "stage": {}, "expect": {}},
            {"name": "beta", "stage": {}, "expect": {}},
            {"name": "gamma", "stage": {}, "expect": {}},
        ]
        selected = runner.select_cases(cases, ["gamma", "alpha"])
        self.assertEqual([item["name"] for item in selected], ["gamma", "alpha"])

    def test_select_cases_raises_on_missing_name(self) -> None:
        cases = [
            {"name": "alpha", "stage": {}, "expect": {}},
            {"name": "beta", "stage": {}, "expect": {}},
        ]
        with self.assertRaises(ValueError):
            runner.select_cases(cases, ["missing"])

    def test_resolve_case_name_supports_prefix_and_substring(self) -> None:
        cases = [
            {"name": "adult_campus_realistic", "stage": {}, "expect": {}},
            {"name": "cyberpunk_female", "stage": {}, "expect": {}},
            {"name": "formal_privatewear_conflict", "stage": {}, "expect": {}},
        ]
        self.assertEqual(runner.resolve_case_name(cases, "adult_campus"), "adult_campus_realistic")
        self.assertEqual(runner.resolve_case_name(cases, "privatewear"), "formal_privatewear_conflict")

    def test_resolve_case_name_raises_on_ambiguous_prefix(self) -> None:
        cases = [
            {"name": "myth_goddess", "stage": {}, "expect": {}},
            {"name": "myth_refined", "stage": {}, "expect": {}},
        ]
        with self.assertRaises(ValueError):
            runner.resolve_case_name(cases, "myth")

    def test_list_group_names_preserves_group_order(self) -> None:
        cases = [
            {"name": "alpha", "stage": {}, "expect": {}, "group": "conflict"},
            {"name": "beta", "stage": {}, "expect": {}, "group": "realistic"},
            {"name": "gamma", "stage": {}, "expect": {}, "group": "custom"},
        ]
        self.assertEqual(runner.list_group_names(cases), ["realistic", "conflict", "custom"])

    def test_resolve_group_name_supports_prefix_and_substring(self) -> None:
        cases = [
            {"name": "alpha", "stage": {}, "expect": {}, "group": "realistic"},
            {"name": "beta", "stage": {}, "expect": {}, "group": "private"},
            {"name": "gamma", "stage": {}, "expect": {}, "group": "conflict"},
        ]
        self.assertEqual(runner.resolve_group_name(cases, "real"), "realistic")
        self.assertEqual(runner.resolve_group_name(cases, "flict"), "conflict")

    def test_resolve_group_name_raises_on_missing(self) -> None:
        cases = [{"name": "alpha", "stage": {}, "expect": {}, "group": "realistic"}]
        with self.assertRaises(ValueError):
            runner.resolve_group_name(cases, "missing")

    def test_filter_cases_by_group_filters_selection(self) -> None:
        cases = [
            {"name": "alpha", "stage": {}, "expect": {}, "group": "realistic"},
            {"name": "beta", "stage": {}, "expect": {}, "group": "private"},
            {"name": "gamma", "stage": {}, "expect": {}, "group": "conflict"},
        ]
        filtered = runner.filter_cases_by_group(cases, ["priv"])
        self.assertEqual([item["name"] for item in filtered], ["beta"])

    def test_style_mode_group_is_listed_and_ordered_in_group_listing(self) -> None:
        cases = [
            {"name": "other_case", "stage": {}, "expect": {}, "group": "realistic"},
            {"name": "myth_case", "stage": {}, "expect": {}, "group": "style_mode"},
            {"name": "ancient_case", "stage": {}, "expect": {}, "group": "style_mode"},
            {"name": "illustration_case", "stage": {}, "expect": {}, "group": "style_mode"},
        ]
        grouped = runner.list_grouped_case_names(cases)
        self.assertEqual(list(grouped.keys())[:2], ["realistic", "style_mode"])
        self.assertEqual(grouped["style_mode"], ["myth_case", "ancient_case", "illustration_case"])

    def test_style_mode_group_is_listed_and_filterable(self) -> None:
        cases = [
            {"name": "realistic_case", "stage": {}, "expect": {}, "group": "style_mode"},
            {"name": "illustration_case", "stage": {}, "expect": {}, "group": "style_mode"},
            {"name": "cyber_case", "stage": {}, "expect": {}, "group": "style_mode"},
            {"name": "ancient_case", "stage": {}, "expect": {}, "group": "style_mode"},
            {"name": "myth_case", "stage": {}, "expect": {}, "group": "style_mode"},
            {"name": "other_case", "stage": {}, "expect": {}, "group": "realistic"},
        ]
        self.assertIn("style_mode", runner.list_group_names(cases))
        filtered = runner.filter_cases_by_group(cases, ["style_mode"])
        self.assertEqual([item["name"] for item in filtered], [
            "realistic_case",
            "illustration_case",
            "cyber_case",
            "ancient_case",
            "myth_case",
        ])

    def test_load_style_mode_cases_reads_fixture_family(self) -> None:
        cases = runner.load_style_mode_cases()
        self.assertEqual(len(cases), 5)
        self.assertEqual([case["group"] for case in cases], ["style_mode"] * 5)
        self.assertEqual(
            [case["stage"]["模板风格"] for case in cases],
            ["真实感", "插画感", "CG感", "古风", "神话感"],
        )
        self.assertIn("style_mode", runner.list_group_names(cases))

    def test_parse_args_supports_list_cases(self) -> None:
        args = runner.parse_args(["--list-cases", "--case", "alpha", "--group", "private", "--report-suffix", "campus", "--output", "custom.json"])
        self.assertTrue(args.list_cases)
        self.assertEqual(args.case_names, ["alpha"])
        self.assertEqual(args.group_names, ["private"])
        self.assertEqual(args.report_suffix, "campus")
        self.assertEqual(args.output, "custom.json")

    def test_resolve_report_path_prefers_output(self) -> None:
        path = runner.resolve_report_path(default_path=runner.REPORT_PATH, suffix="campus", output="F:/tmp/report.json")
        self.assertEqual(str(path).replace("\\", "/"), "F:/tmp/report.json")

    def test_resolve_report_path_appends_suffix(self) -> None:
        path = runner.resolve_report_path(default_path=runner.REPORT_PATH, suffix="campus run", output=None)
        self.assertTrue(str(path).endswith("codex_stage_regression_report_campus_run.json"))

    def test_build_stage_workflow_uses_available_model_loader_options(self) -> None:
        def fake_get_json(url: str) -> dict[str, object]:
            if url.endswith("/object_info/QwenTE_StagePromptGenerator"):
                return {
                    "QwenTE_StagePromptGenerator": {
                        "input": {
                            "required": {
                                "qwen模型": ["QWENLLAMA", {}],
                                "模板风格": [["真实感", "CG感"], {"default": "真实感"}],
                                "seed": ["INT", {"default": 1}],
                            }
                        }
                    }
                }
            if url.endswith("/object_info/QwenTE_ModelLoader"):
                return {
                    "QwenTE_ModelLoader": {
                        "input": {
                            "required": {
                                "模型系列": [["Qwen3-VL", "Qwen3.5-VL"], {"default": "Qwen3.5-VL"}],
                                "主模型": [["Qwen3.6-35B-A3B-Q4_K_M.gguf"], {}],
                                "视觉投影mmproj": [["无", "mmproj-Qwen3.6-35B-A3B-f16.gguf"], {"default": "无"}],
                                "启用思考": ["BOOLEAN", {"default": False}],
                                "上下文长度": ["INT", {"default": 8192}],
                                "GPU层数": ["INT", {"default": -1}],
                                "KV缓存K类型": [["默认(F16)", "q8_0"], {"default": "默认(F16)"}],
                                "KV缓存V类型": [["默认(F16)", "q8_0"], {"default": "默认(F16)"}],
                            }
                        }
                    }
                }
            raise AssertionError(f"Unexpected object_info url: {url}")

        with mock.patch.object(runner, "get_json", side_effect=fake_get_json):
            payload, output_node_id, negative_node_id = runner.build_stage_workflow({
                "name": "dynamic_model_loader",
                "stage": {"模板风格": "CG感"},
                "expect": {},
            })

        model_inputs = payload["prompt"]["1"]["inputs"]
        stage_inputs = payload["prompt"]["2"]["inputs"]
        self.assertEqual(payload["prompt"]["1"]["class_type"], "QwenTE_ModelLoader")
        self.assertEqual(model_inputs["主模型"], "Qwen3.6-35B-A3B-Q4_K_M.gguf")
        self.assertEqual(model_inputs["模型系列"], "Qwen3.5-VL")
        self.assertEqual(model_inputs["视觉投影mmproj"], "无")
        self.assertEqual(model_inputs["GPU层数"], -1)
        self.assertEqual(stage_inputs["qwen模型"], ["1", 0])
        self.assertEqual(stage_inputs["模板风格"], "CG感")
        self.assertEqual((output_node_id, negative_node_id), ("3", "4"))

    def test_style_mode_main_keeps_list_report_and_attaches_final_comparison(self) -> None:
        cases = [
            {
                "name": "style_mode_realistic",
                "group": "style_mode",
                "image": False,
                "stage": {"模板风格": "真实感"},
                "expect": {},
            },
            {
                "name": "style_mode_illustration",
                "group": "style_mode",
                "image": False,
                "stage": {"模板风格": "插画感"},
                "expect": {},
            }
        ]

        def fake_run_stage_case(case: dict[str, object]) -> dict[str, object]:
            prompt_text = f'PROMPT TEXT {case["name"]}'
            return {
                "prompt_id": "prompt-1",
                "status": "success",
                "raw_prompt_text": prompt_text,
                "prompt_lines": [prompt_text],
                "negative_prompt": f'NEGATIVE TEXT {case["name"]}',
                "evaluations": [
                    {
                        "ok": True,
                        "noise_hit": False,
                        "missing_terms": [],
                        "unexpected_terms": [],
                    }
                ],
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = pathlib.Path(tmpdir) / "style_mode_report.json"
            with mock.patch.object(runner, "parse_args", return_value=mock.Mock(list_cases=False, case_names=None, group_names=["style_mode"], report_suffix=None, output=str(report_path))), \
                mock.patch.object(runner, "filter_cases_by_group", return_value=cases), \
                mock.patch.object(runner, "select_cases", return_value=cases), \
                mock.patch.object(runner, "resolve_report_path", return_value=report_path), \
                mock.patch.object(runner, "run_stage_case", side_effect=fake_run_stage_case), \
                mock.patch.object(runner, "run_image_case", side_effect=AssertionError("image path should not be used")), \
                mock.patch.object(runner, "print"):
                exit_code = runner.main([])

            self.assertEqual(exit_code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIsInstance(payload, list)
            self.assertEqual([row["name"] for row in payload], ["style_mode_realistic", "style_mode_illustration"])
            self.assertNotIn("style_mode_comparison", payload[0])
            self.assertIn("style_mode_comparison", payload[-1])
            comparison = payload[-1]["style_mode_comparison"]
            self.assertEqual(len(comparison), 2)
            self.assertEqual(comparison[0]["template_style"], "真实感")
            self.assertEqual(comparison[0]["prompt_text"], "PROMPT TEXT style_mode_realistic")
            self.assertEqual(comparison[0]["negative_text"], "NEGATIVE TEXT style_mode_realistic")
            self.assertEqual(comparison[1]["template_style"], "插画感")
            self.assertEqual(comparison[1]["prompt_text"], "PROMPT TEXT style_mode_illustration")
            self.assertEqual(comparison[1]["negative_text"], "NEGATIVE TEXT style_mode_illustration")

    def test_template_suite_attaches_style_matrix_summary_on_final_record(self) -> None:
        cases = [template_suite.CASE_PRESETS[0], template_suite.CASE_PRESETS[1]]
        def fake_run_stage_case(case: dict[str, object]) -> dict[str, object]:
            return {
                "prompt_id": f"stage-{case['name']}",
                "status": "success",
                "raw_prompt_text": f"PROMPT {case['name']}",
                "prompt_lines": [f"PROMPT {case['name']}"],
                "negative_prompt": f"NEG {case['name']}",
                "evaluations": [],
            }

        def fake_build_case_prompt_map(case: dict[str, object], library: dict[str, object]) -> tuple[dict[str, dict[str, object]], str, str | None, str | None]:
            return {"14": {"inputs": {"text": ""}}, "43": {"inputs": {"text": ""}}}, "stage", "14", "43"

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = pathlib.Path(tmpdir) / "template_suite_report.json"
            with mock.patch.object(template_suite, "CASE_PRESETS", cases), \
                mock.patch.object(template_suite, "fetch_prompt_library", return_value={"slot_config": [], "tag_library": {}}), \
                mock.patch.object(template_suite, "load_regression_runner", return_value=mock.Mock(run_stage_case=fake_run_stage_case)), \
                mock.patch.object(template_suite, "build_case_prompt_map", side_effect=fake_build_case_prompt_map), \
                mock.patch.object(template_suite, "post_json", return_value={"prompt_id": "image-1"}), \
                mock.patch.object(template_suite, "poll_history", return_value={"status": {"status_str": "success"}, "outputs": {}}), \
                mock.patch.object(template_suite, "build_contact_sheet"), \
                mock.patch.object(template_suite, "REPORT_JSON", report_path), \
                mock.patch.object(template_suite, "print"):
                exit_code = template_suite.main()

            self.assertEqual(exit_code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIsInstance(payload, list)
            self.assertEqual(len(payload), 2)
            self.assertNotIn("style_matrix_summary", payload[0])
            self.assertIn("style_matrix_summary", payload[-1])
            summary = payload[-1]["style_matrix_summary"]
            self.assertEqual(summary["case_count"], 2)
            self.assertEqual([row["template_style"] for row in summary["styles"]], ["自动", "真实感"])
            self.assertEqual([row["name"] for row in summary["styles"]], [cases[0]["name"], cases[1]["name"]])
            self.assertEqual(summary["styles"][0]["prompt_preview"], f'PROMPT {cases[0]["name"]}')
            self.assertEqual(summary["styles"][1]["negative_preview"], f'NEG {cases[1]["name"]}')

    def test_build_case_prompt_map_falls_back_for_generic_workflow_without_qwente_nodes(self) -> None:
        case = {
            "name": "generic_fallback_case",
            "tags": ["成年女性", "东亚", "真实感"],
            "settings": {
                "模板风格": "自动",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "提示词语言": "纯中文",
                "详细度": "详细",
                "输出模式": "完整结果",
            },
            "extra": "保持成年感，不要文字。",
        }
        library = {"slot_config": [], "tag_library": {}}
        workflow = {
            "nodes": [
                {
                    "id": 14,
                    "type": "CLIPTextEncode",
                    "widgets_values": ["positive placeholder"],
                    "inputs": [
                        {"name": "text", "type": "STRING", "widget": {"name": "text"}}
                    ],
                },
                {
                    "id": 43,
                    "type": "CLIPTextEncode",
                    "widgets_values": ["negative placeholder"],
                    "inputs": [
                        {"name": "text", "type": "STRING", "widget": {"name": "text"}}
                    ],
                },
                {
                    "id": 18,
                    "type": "KSampler",
                    "widgets_values": [],
                    "inputs": [
                        {"name": "seed", "type": "INT"},
                        {"name": "steps", "type": "INT"},
                    ],
                },
                {
                    "id": 31,
                    "type": "SaveImage",
                    "widgets_values": ["template_example"],
                    "inputs": [
                        {"name": "filename_prefix", "type": "STRING", "widget": {"name": "filename_prefix"}}
                    ],
                },
            ],
            "links": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_path = pathlib.Path(tmpdir) / "generic_live_workflow.json"
            workflow_path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
            with mock.patch.object(template_suite, "resolve_workflow_path", return_value=workflow_path):
                prompt_map, stage_id, positive_id, negative_id = template_suite.build_case_prompt_map(case, library)

        self.assertIn("14", prompt_map)
        self.assertIn("43", prompt_map)
        self.assertEqual(prompt_map["31"]["inputs"]["filename_prefix"], "template_example_generic_fallback_case")
        self.assertIsInstance(stage_id, str)
        self.assertEqual(positive_id, "14")
        self.assertEqual(negative_id, "43")

    def test_resolve_image_workflow_path_falls_back_to_live_comfyui_workflow(self) -> None:
        expected = runner.IMAGE_WORKFLOW_FALLBACK_PATHS[0]

        def fake_exists(path: pathlib.Path) -> bool:
            normalized = str(path).replace("\\", "/")
            if normalized.endswith("Unsaved Workflow.json"):
                return False
            return normalized == str(expected).replace("\\", "/")

        with mock.patch.object(pathlib.Path, "exists", autospec=True, side_effect=fake_exists):
            resolved = runner.resolve_image_workflow_path()

        self.assertEqual(resolved, expected)

    def test_build_image_payload_injects_prompt_text_without_hard_coded_node_ids(self) -> None:
        workflow = {
            "nodes": [
                {
                    "id": 89,
                    "type": "ImpactInt",
                    "widgets_values": [1920],
                    "inputs": [
                        {"name": "value", "type": "INT", "widget": {"name": "value"}}
                    ],
                },
                {
                    "id": 91,
                    "type": "ImpactInt",
                    "widgets_values": [1080],
                    "inputs": [
                        {"name": "value", "type": "INT", "widget": {"name": "value"}}
                    ],
                },
                {
                    "id": 14,
                    "type": "CLIPTextEncode",
                    "widgets_values": ["positive placeholder"],
                    "inputs": [
                        {"name": "text", "type": "STRING", "widget": {"name": "text"}}
                    ],
                },
                {
                    "id": 43,
                    "type": "CLIPTextEncode",
                    "widgets_values": ["text, watermark, blurry, low quality"],
                    "inputs": [
                        {"name": "text", "type": "STRING", "widget": {"name": "text"}}
                    ],
                },
                {
                    "id": 18,
                    "type": "KSampler",
                    "widgets_values": [123456789, "fixed", 12],
                    "inputs": [
                        {"name": "positive", "type": "CONDITIONING"},
                        {"name": "negative", "type": "CONDITIONING"},
                        {"name": "latent_image", "type": "LATENT"},
                        {"name": "seed", "type": "INT", "widget": {"name": "seed"}},
                        {"name": "steps", "type": "INT", "widget": {"name": "steps"}},
                    ],
                },
                {
                    "id": 84,
                    "type": "EmptyLatentImage",
                    "widgets_values": [1920, 1080, 1],
                    "inputs": [
                        {"name": "width", "type": "INT", "link": 1},
                        {"name": "height", "type": "INT", "link": 2},
                        {"name": "batch_size", "type": "INT", "widget": {"name": "batch_size"}},
                    ],
                },
                {
                    "id": 31,
                    "type": "SaveImage",
                    "widgets_values": ["ComfyUI"],
                    "inputs": [
                        {"name": "filename_prefix", "type": "STRING", "widget": {"name": "filename_prefix"}}
                    ],
                },
            ],
            "links": [
                [1, 89, 0, 84, 0, "INT"],
                [2, 91, 0, 84, 1, "INT"],
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            workflow_path = pathlib.Path(tmpdir) / "image_workflow.json"
            workflow_path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
            with mock.patch.object(runner, "resolve_image_workflow_path", return_value=workflow_path), \
                mock.patch.object(runner.random, "randint", return_value=246813579):
                payload = runner.build_image_payload("PROMPT TEXT", negative_text="NEGATIVE TEXT", filename_prefix="codex_prefix")

        prompt_map = payload["prompt"]
        self.assertEqual(prompt_map["14"]["inputs"]["text"], "PROMPT TEXT")
        self.assertEqual(prompt_map["43"]["inputs"]["text"], "NEGATIVE TEXT")
        self.assertEqual(prompt_map["18"]["inputs"]["seed"], 246813579)
        self.assertEqual(prompt_map["18"]["inputs"]["steps"], 6)
        self.assertEqual(prompt_map["89"]["inputs"]["value"], 1024)
        self.assertEqual(prompt_map["91"]["inputs"]["value"], 576)
        self.assertEqual(prompt_map["31"]["inputs"]["filename_prefix"], "codex_prefix")

    def test_resolve_prompt_text_node_ids_prefers_negative_prompt_signature(self) -> None:
        prompt_map = {
            "14": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
            "43": {"class_type": "CLIPTextEncode", "inputs": {"text": "text, watermark, blurry, low quality"}},
            "31": {"class_type": "SaveImage", "inputs": {"filename_prefix": "template_example"}},
        }
        positive_id, negative_id = template_suite._resolve_prompt_text_node_ids(prompt_map)
        self.assertEqual(positive_id, "14")
        self.assertEqual(negative_id, "43")

    def test_template_suite_image_paths_use_live_comfyui_output_root(self) -> None:
        cases = [
            {
                "name": "image_path_case",
                "template_style": "自动",
                "settings": {
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "提示词语言": "纯中文",
                    "详细度": "详细",
                    "输出模式": "完整结果",
                },
                "tags": ["成年女性", "东亚", "真实感"],
                "extra": "保持成年感，不要文字。",
            }
        ]

        def fake_run_stage_case(case: dict[str, object]) -> dict[str, object]:
            return {
                "prompt_id": f"stage-{case['name']}",
                "status": "success",
                "raw_prompt_text": "PROMPT TEXT",
                "prompt_lines": ["PROMPT TEXT"],
                "negative_prompt": "NEGATIVE TEXT",
                "evaluations": [],
            }

        def fake_build_case_prompt_map(case: dict[str, object], library: dict[str, object]) -> tuple[dict[str, dict[str, object]], str, str | None, str | None]:
            return {
                "14": {"inputs": {"text": ""}},
                "43": {"inputs": {"text": ""}},
                "31": {"inputs": {"filename_prefix": ""}},
            }, "stage", "14", "43"

        def fake_poll_history(prompt_id: str, timeout_sec: int = 1800) -> dict[str, object]:
            return {
                "status": {"status_str": "success"},
                "outputs": {
                    "31": {
                        "images": [
                            {"type": "output", "subfolder": "", "filename": "live_result.png"},
                        ]
                    }
                },
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = pathlib.Path(tmpdir) / "template_suite_report.json"
            with mock.patch.object(template_suite, "CASE_PRESETS", cases), \
                mock.patch.object(template_suite, "fetch_prompt_library", return_value={"slot_config": [], "tag_library": {}}), \
                mock.patch.object(template_suite, "load_regression_runner", return_value=mock.Mock(run_stage_case=fake_run_stage_case)), \
                mock.patch.object(template_suite, "build_case_prompt_map", side_effect=fake_build_case_prompt_map), \
                mock.patch.object(template_suite, "post_json", return_value={"prompt_id": "image-1"}), \
                mock.patch.object(template_suite, "poll_history", side_effect=fake_poll_history), \
                mock.patch.object(template_suite, "build_contact_sheet"), \
                mock.patch.object(template_suite, "REPORT_JSON", report_path), \
                mock.patch.object(template_suite, "print"):
                exit_code = template_suite.main()

            self.assertEqual(exit_code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 1)
            image_paths = payload[0]["image"]["images"]
            self.assertEqual(
                image_paths,
                [
                    str(
                        template_suite.LIVE_COMFYUI_ROOT
                        / "output"
                        / "live_result.png"
                    )
                ],
            )

    def test_template_suite_main_injects_prompt_text_for_generic_workflow_without_text_node_ids(self) -> None:
        cases = [
            {
                "name": "generic_main_case",
                "template_style": "自动",
                "settings": {
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "提示词语言": "纯中文",
                    "详细度": "详细",
                    "输出模式": "完整结果",
                },
                "tags": ["成年女性", "东亚", "真实感"],
                "extra": "保持成年感，不要文字。",
            }
        ]
        captured_prompts: list[dict[str, object]] = []

        def fake_run_stage_case(case: dict[str, object]) -> dict[str, object]:
            return {
                "prompt_id": f"stage-{case['name']}",
                "status": "success",
                "raw_prompt_text": "PROMPT TEXT",
                "prompt_lines": ["PROMPT TEXT"],
                "negative_prompt": "NEGATIVE TEXT",
                "evaluations": [],
            }

        def fake_build_case_prompt_map(case: dict[str, object], library: dict[str, object]) -> tuple[dict[str, dict[str, object]], str, str | None, str | None]:
            return {
                "14": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
                "43": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
                "31": {"class_type": "SaveImage", "inputs": {"filename_prefix": "template_example"}},
            }, "", None, None

        def fake_post_json(url: str, payload: dict[str, object], timeout: int = 90) -> dict[str, object]:
            captured_prompts.append(payload["prompt"])
            return {"prompt_id": "image-1"}

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = pathlib.Path(tmpdir) / "template_suite_report.json"
            with mock.patch.object(template_suite, "CASE_PRESETS", cases), \
                mock.patch.object(template_suite, "fetch_prompt_library", return_value={"slot_config": [], "tag_library": {}}), \
                mock.patch.object(template_suite, "load_regression_runner", return_value=mock.Mock(run_stage_case=fake_run_stage_case)), \
                mock.patch.object(template_suite, "build_case_prompt_map", side_effect=fake_build_case_prompt_map), \
                mock.patch.object(template_suite, "post_json", side_effect=fake_post_json), \
                mock.patch.object(template_suite, "poll_history", return_value={"status": {"status_str": "success"}, "outputs": {}}), \
                mock.patch.object(template_suite, "build_contact_sheet"), \
                mock.patch.object(template_suite, "REPORT_JSON", report_path), \
                mock.patch.object(template_suite, "print"):
                exit_code = template_suite.main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(captured_prompts), 1)
            prompt_map = captured_prompts[0]
            self.assertEqual(prompt_map["14"]["inputs"]["text"], "PROMPT TEXT")
            self.assertEqual(prompt_map["43"]["inputs"]["text"], "NEGATIVE TEXT")

    def test_resolve_workflow_path_falls_back_to_live_comfyui_workflow(self) -> None:
        expected = pathlib.Path(r"F:/ComfyUI_portable_TE v251130/ComfyUI/user/default/workflows/Z-IMAGE电影光影工作流 by.TE.json")
        def fake_exists(path: pathlib.Path) -> bool:
            normalized = str(path).replace("\\", "/")
            if normalized.endswith("QwenTE_阶段节点精简生图.json"):
                return False
            return normalized == str(expected).replace("\\", "/")

        with mock.patch.object(pathlib.Path, "exists", autospec=True, side_effect=fake_exists):
            resolved = template_suite.resolve_workflow_path()

        self.assertEqual(resolved, expected)

    def test_auto_pool_suite_builds_stage_case_with_expected_settings(self) -> None:
        case = auto_pool_suite.CASES[0]
        stage_case = auto_pool_suite.build_stage_case(case)
        self.assertEqual(stage_case["name"], case["name"])
        self.assertEqual(stage_case["stage"]["模板风格"], case["template_style"])
        self.assertEqual(stage_case["stage"]["随机主题池"], "自动")
        self.assertEqual(stage_case["stage"]["运行时随机模式"], "全随机")
        self.assertEqual(stage_case["stage"]["运行时随机强度"], "中")
        self.assertEqual(stage_case["stage"]["自定义补充标签"], ", ".join(case["tags"]))
        self.assertEqual(stage_case["expect"]["must_contain"], [])

    def test_auto_pool_suite_main_uses_regression_runner_and_writes_image_paths(self) -> None:
        case = {
            "name": "auto_pool_case",
            "template_style": "真实感",
            "tags": ["成年女性", "东亚", "校园", "中景半身"],
            "extra": "保持校园单一主场景。",
        }

        def fake_run_stage_case(stage_case: dict[str, object]) -> dict[str, object]:
            self.assertEqual(stage_case["name"], case["name"])
            self.assertEqual(stage_case["stage"]["随机主题池"], "自动")
            return {
                "prompt_id": "stage-1",
                "status": "success",
                "raw_prompt_text": "写实摄影，成年女性，东亚，校园，中景半身",
                "prompt_lines": ["写实摄影，成年女性，东亚，校园，中景半身"],
                "negative_prompt": "text, watermark",
                "evaluations": [],
            }

        def fake_run_image_case(prompt_text: str, *, negative_text: str, name: str) -> dict[str, object]:
            self.assertEqual(prompt_text, "写实摄影，成年女性，东亚，校园，中景半身")
            self.assertEqual(negative_text, "text, watermark")
            self.assertEqual(name, case["name"])
            return {
                "prompt_id": "image-1",
                "status": "success",
                "images": [r"F:/ComfyUI_portable_TE v251130/ComfyUI/output/auto_pool_case.png"],
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = pathlib.Path(tmpdir) / "auto_pool_report.json"
            with mock.patch.object(auto_pool_suite, "CASES", [case]), \
                mock.patch.object(auto_pool_suite, "load_regression_runner", return_value=mock.Mock(run_stage_case=fake_run_stage_case, run_image_case=fake_run_image_case)), \
                mock.patch.object(auto_pool_suite, "REPORT_PATH", report_path), \
                mock.patch.object(auto_pool_suite, "print"):
                exit_code = auto_pool_suite.main()

            self.assertEqual(exit_code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 1)
            row = payload[0]
            self.assertEqual(row["status"], "success")
            self.assertEqual(row["prompt_id"], "stage-1")
            self.assertEqual(row["lead"], "写实摄影")
            self.assertEqual(row["image"]["status"], "success")
            self.assertEqual(
                row["image"]["images"],
                [r"F:/ComfyUI_portable_TE v251130/ComfyUI/output/auto_pool_case.png"],
            )
            self.assertTrue(row["anchor_checks"]["has_subject"])
            self.assertTrue(row["anchor_checks"]["has_scene"])
            self.assertTrue(row["anchor_checks"]["has_composition"])

    def test_five_mode_stage_suite_reports_mode_core_and_anchor_checks(self) -> None:
        case = {
            "name": "five_mode_case",
            "template_style": "神话感",
            "tags": ["成年女性", "东亚", "校园", "中景半身"],
            "extra": "保持校园单一主场景。",
            "must_have_any": ["神话感", "神圣史诗"],
            "must_not_have": ["虚幻引擎", "未来都市"],
        }

        def fake_run_stage_case(stage_case: dict[str, object]) -> dict[str, object]:
            self.assertEqual(stage_case["name"], case["name"])
            self.assertEqual(stage_case["stage"]["模板风格"], "神话感")
            return {
                "prompt_id": "stage-five",
                "status": "success",
                "raw_prompt_text": "成年女性，神话感，校园神殿场景，中景半身，神圣史诗感",
                "prompt_lines": ["成年女性，神话感，校园神殿场景，中景半身，神圣史诗感"],
                "negative_prompt": "text, watermark",
                "evaluations": [],
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = pathlib.Path(tmpdir) / "five_mode_stage_report.json"
            with mock.patch.object(auto_pool_five_mode_stage_suite, "CASES", [case]), \
                mock.patch.object(auto_pool_five_mode_stage_suite, "load_regression_runner", return_value=mock.Mock(run_stage_case=fake_run_stage_case)), \
                mock.patch.object(auto_pool_five_mode_stage_suite, "REPORT_PATH", report_path), \
                mock.patch.object(auto_pool_five_mode_stage_suite, "print"):
                exit_code = auto_pool_five_mode_stage_suite.main()

            self.assertEqual(exit_code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 1)
            row = payload[0]
            self.assertEqual(row["status"], "success")
            self.assertTrue(row["checks"]["has_subject"])
            self.assertTrue(row["checks"]["has_scene"])
            self.assertTrue(row["checks"]["has_composition"])
            self.assertTrue(row["checks"]["has_mode_core"])
            self.assertEqual(row["checks"]["cross_mode_pollution"], [])

    def test_five_mode_full_suite_writes_stage_and_image_results(self) -> None:
        case = {
            "name": "five_mode_full_case",
            "template_style": "CG感",
            "tags": ["成年女性", "东亚", "校园", "中景半身"],
            "extra": "保持校园单一主场景。",
            "must_have_any": ["CG感", "电影级CG"],
            "must_not_have": ["神殿", "古风建筑"],
        }

        def fake_run_stage_case(stage_case: dict[str, object]) -> dict[str, object]:
            self.assertEqual(stage_case["name"], case["name"])
            return {
                "prompt_id": "stage-full",
                "status": "success",
                "raw_prompt_text": "成年女性，CG感，校园机库维修车间，中景半身，电影级CG",
                "prompt_lines": ["成年女性，CG感，校园机库维修车间，中景半身，电影级CG"],
                "negative_prompt": "text, watermark",
                "evaluations": [],
            }

        def fake_run_image_case(prompt_text: str, *, negative_text: str, name: str) -> dict[str, object]:
            self.assertEqual(prompt_text, "成年女性，CG感，校园机库维修车间，中景半身，电影级CG")
            self.assertEqual(negative_text, "text, watermark")
            self.assertEqual(name, case["name"])
            return {
                "prompt_id": "image-full",
                "status": "success",
                "images": [r"F:/ComfyUI_portable_TE v251130/ComfyUI/output/five_mode_full_case.png"],
            }

        with tempfile.TemporaryDirectory() as tmpdir:
            report_path = pathlib.Path(tmpdir) / "five_mode_full_report.json"
            with mock.patch.object(auto_pool_five_mode_full_suite, "CASES", [case]), \
                mock.patch.object(auto_pool_five_mode_full_suite, "load_regression_runner", return_value=mock.Mock(run_stage_case=fake_run_stage_case, run_image_case=fake_run_image_case)), \
                mock.patch.object(auto_pool_five_mode_full_suite, "REPORT_PATH", report_path), \
                mock.patch.object(auto_pool_five_mode_full_suite, "print"):
                exit_code = auto_pool_five_mode_full_suite.main()

            self.assertEqual(exit_code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 1)
            row = payload[0]
            self.assertEqual(row["status"], "success")
            self.assertTrue(row["checks"]["has_subject"])
            self.assertTrue(row["checks"]["has_scene"])
            self.assertTrue(row["checks"]["has_composition"])
            self.assertTrue(row["checks"]["has_mode_core"])
            self.assertEqual(row["checks"]["cross_mode_pollution"], [])
            self.assertEqual(row["image"]["status"], "success")
            self.assertEqual(row["image"]["images"], [r"F:/ComfyUI_portable_TE v251130/ComfyUI/output/five_mode_full_case.png"])


if __name__ == "__main__":
    unittest.main()
