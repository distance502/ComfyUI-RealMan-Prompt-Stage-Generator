"""ComfyUI validation contracts; no model weights or inference required."""
from __future__ import annotations

import inspect
import types
import unittest
from unittest import mock

from test_stage_prompt_modules import load_stage_prompt_generator_for_integration_test


def validate_prompt_widgets(node_class, inputs):
    """Match host argument filtering and unresolved-link values at validation."""
    signature = inspect.signature(node_class.VALIDATE_INPUTS)
    supplied = {
        name: None if isinstance(value, list) else value
        for name, value in inputs.items()
        if name in signature.parameters
    }
    return node_class.VALIDATE_INPUTS(**supplied)


class TestStageModelInputValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = load_stage_prompt_generator_for_integration_test()

    def setUp(self):
        self.main = self.stage.QwenTE阶段式提示词生成器
        self.options = mock.patch.object(
            self.stage,
            "_内置模型文件选项",
            return_value=(["nested/model-00001-of-00002.gguf", "current.gguf"], ["无", "nested/mmproj.gguf"]),
        )
        self.list_options = self.options.start()
        self.addCleanup(self.options.stop)

    def test_idle_deleted_models_do_not_block_api_or_skill(self):
        for source in ("API接口", "仅Skill"):
            with self.subTest(source=source):
                result = validate_prompt_widgets(self.main, {
                    "模型来源": source,
                    "内置主模型": "deleted.gguf",
                    "内置视觉投影mmproj": "deleted-mmproj.gguf",
                })
                self.assertIs(result, True)
        self.list_options.assert_not_called()

    def test_connected_model_does_not_validate_idle_builtin_selections(self):
        self.assertIs(validate_prompt_widgets(self.main, {
            "模型来源": "本地模型",
            "内置主模型": "deleted.gguf",
            "内置视觉投影mmproj": "deleted-mmproj.gguf",
            "qwen模型": ["loader-node", 0],
        }), True)
        self.list_options.assert_not_called()

    def test_absent_external_input_keeps_builtin_model_validation(self):
        for source in ("本地模型", "本地GGUF"):
            with self.subTest(source=source):
                result = validate_prompt_widgets(self.main, {
                    "模型来源": source,
                    "内置主模型": "deleted.gguf",
                })
                self.assertIsInstance(result, str)
                self.assertIn("内置主模型", result)

    def test_builtin_projection_is_checked_only_when_needed(self):
        result = validate_prompt_widgets(self.main, {
            "模型来源": "本地模型", "内置主模型": "current.gguf",
            "内置视觉投影mmproj": "missing-mmproj.gguf",
        })
        self.assertIsInstance(result, str)
        self.assertIn("mmproj", result)
        self.assertIs(validate_prompt_widgets(self.main, {
            "模型来源": "本地模型", "内置主模型": "current.gguf",
            "内置视觉投影mmproj": "nested\\mmproj.gguf",
        }), True)

    def test_legacy_continuation_shard_normalizes_only_to_listed_first_shard(self):
        self.assertIs(validate_prompt_widgets(self.main, {
            "模型来源": "本地模型",
            "内置主模型": "nested\\model-00002-of-00002.gguf",
        }), True)
        for selected in (
            "nested/missing-00002-of-00002.gguf",
            "nested/model-00000-of-00002.gguf",
            "nested/model-00001-of-99999.gguf",
            "../outside.gguf",
        ):
            with self.subTest(selected=selected):
                self.assertIsInstance(validate_prompt_widgets(self.main, {
                    "模型来源": "本地模型", "内置主模型": selected,
                }), str)

    def test_dynamic_widget_values_are_deferred_until_execution(self):
        self.assertIs(validate_prompt_widgets(self.main, {
            "模型来源": ["source-node", 0], "内置主模型": "stale.gguf",
        }), True)
        self.assertIs(validate_prompt_widgets(self.main, {
            "模型来源": "本地模型", "内置主模型": ["filename-node", 0],
        }), True)

    def test_source_default_matches_runtime_and_does_not_hide_required_inputs(self):
        self.assertIn("模型来源", self.main.INPUT_TYPES()["required"])
        self.list_options.reset_mock()
        self.assertEqual(inspect.signature(self.main.VALIDATE_INPUTS).parameters["模型来源"].default, "仅Skill")
        self.assertEqual(self.stage.SETTING_DEFAULTS["模型来源"], "仅Skill")
        for source_inputs in ({}, {"模型来源": None}):
            with self.subTest(source_inputs=source_inputs):
                self.assertIs(validate_prompt_widgets(self.main, {
                    "内置主模型": "deleted.gguf", **source_inputs,
                }), True)
        self.list_options.assert_not_called()

    def test_none_source_uses_skill_at_execution(self):
        with mock.patch.object(self.stage, "_加载内置阶段模型") as local_loader, \
             mock.patch.object(self.stage, "_run_stage", return_value=("",) * 8) as run_stage, \
             mock.patch.object(self.stage, "获取阶段节点输出缓存", return_value={}):
            self.main().run(模型来源=None, 内置主模型="deleted.gguf")
        local_loader.assert_not_called()
        self.assertEqual(run_stage.call_args.kwargs["模型来源"], "仅Skill")

    def test_invalid_source_is_not_accidentally_exempted_from_combo_validation(self):
        self.assertIsInstance(validate_prompt_widgets(self.main, {
            "模型来源": "invalid-source", "内置主模型": "current.gguf",
            "qwen模型": ["loader-node", 0],
        }), str)

    def test_host_keeps_other_input_types_ranges_and_combos(self):
        signature = inspect.signature(self.main.VALIDATE_INPUTS)
        self.assertNotIn("input_types", signature.parameters)
        self.assertFalse(any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        ))
        for host_checked in ("生成数量", "温度", "模板风格", "参考图片", "内置上下文长度"):
            self.assertNotIn(host_checked, signature.parameters)

    def test_generic_model_node_does_not_inherit_removed_widget_arguments(self):
        generic = self.stage.QwenTE通用模型阶段式提示词生成器
        self.assertNotIn("内置主模型", generic.INPUT_TYPES()["required"])
        self.assertEqual(list(inspect.signature(generic.VALIDATE_INPUTS).parameters), [])
        self.assertIs(validate_prompt_widgets(generic, {"通用模型": ["loader-node", 0]}), True)

    def test_connected_none_still_uses_strict_runtime_loader(self):
        storage = types.SimpleNamespace(load=mock.Mock(side_effect=RuntimeError("missing model")))
        with mock.patch.object(self.stage, "_内置QwenStorage", storage), \
             mock.patch.object(self.stage, "_run_stage", return_value=("",) * 8) as run_stage, \
             mock.patch.object(self.stage, "获取阶段节点输出缓存", return_value={}):
            self.main().run(qwen模型=None, 模型来源="本地模型", 内置主模型="deleted.gguf")
        storage.load.assert_called_once()
        self.assertEqual(storage.load.call_args.args[0]["model"], "deleted.gguf")
        self.assertIsNone(run_stage.call_args.args[0])
        self.assertEqual(run_stage.call_args.kwargs["模型来源实际"], "仅Skill回退")
        self.assertIn("missing model", run_stage.call_args.kwargs["模型回退说明"])


if __name__ == "__main__":
    unittest.main()
