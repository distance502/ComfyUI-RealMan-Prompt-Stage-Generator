# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest
from collections import OrderedDict
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(relative_path: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tag_library = load_module("prompt_tag_library.py", "prompt_tag_library_storage_bounds_test")
state_builder = load_module("stage_prompt/state_builder.py", "stage_prompt_state_builder_storage_bounds_test")
nsfw_mapper = load_module("stage_prompt/nsfw_mapper.py", "stage_prompt_nsfw_mapper_storage_bounds_test")
nsfw_presets = load_module("stage_prompt/nsfw_presets.py", "stage_prompt_nsfw_presets_storage_bounds_test")


class TestCustomTagLibraryBounds(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.original_path = tag_library._自定义标签库文件路径
        tag_library._自定义标签库文件路径 = (
            pathlib.Path(self.temporary_directory.name) / "custom.json"
        )
        tag_library._清空标签库缓存()

    def tearDown(self) -> None:
        tag_library._自定义标签库文件路径 = self.original_path
        tag_library._清空标签库缓存()
        self.temporary_directory.cleanup()

    def _library(self, sections: dict[str, list[str]]):
        payload = tag_library._空自定义标签库()
        payload["主体"].update(sections)
        return payload

    def test_add_over_total_limit_keeps_previous_file_and_cache(self) -> None:
        baseline = self._library({"测试": ["标签一"]})
        tag_library.保存自定义标签库(baseline)
        previous_bytes = tag_library._自定义标签库文件路径.read_bytes()

        with mock.patch.object(tag_library, "_自定义标签库最大标签总数", 1):
            ok, message = tag_library.添加自定义标签("主体", "测试", "标签二")

        self.assertFalse(ok)
        self.assertIn("总数", message)
        self.assertEqual(tag_library._自定义标签库文件路径.read_bytes(), previous_bytes)
        self.assertEqual(tag_library.读取自定义标签库()["主体"]["测试"], ["标签一"])

    def test_strict_save_rejects_section_item_and_json_limits(self) -> None:
        with mock.patch.object(tag_library, "_自定义标签库最大小类数", 1):
            with self.assertRaisesRegex(ValueError, "小类总数"):
                tag_library.保存自定义标签库(self._library({"一": [], "二": []}))

        oversized_tag = "x" * (int(tag_library.自定义标签规则["max_tag_length"]) + 1)
        with self.assertRaisesRegex(ValueError, "标签长度"):
            tag_library.保存自定义标签库(self._library({"测试": [oversized_tag]}))

        with mock.patch.object(tag_library, "_自定义标签库最大JSON字节", 64):
            with self.assertRaisesRegex(ValueError, "JSON"):
                tag_library.保存自定义标签库(self._library({"测试": ["标签"]}))

    def test_oversized_file_is_rejected_before_json_loading(self) -> None:
        tag_library._自定义标签库文件路径.write_bytes(b" " * 65)
        with mock.patch.object(tag_library, "_自定义标签库最大JSON字节", 64):
            with self.assertRaisesRegex(ValueError, "文件不能超过"):
                tag_library._读取自定义标签库文件()

    def test_batch_route_rejects_oversized_text_without_writing(self) -> None:
        baseline = self._library({"测试": ["标签一"]})
        tag_library.保存自定义标签库(baseline)
        previous_bytes = tag_library._自定义标签库文件路径.read_bytes()

        ok, message, detail = tag_library.批量添加自定义标签(
            "主体",
            "测试",
            "x" * (tag_library._自定义标签批量输入最大字符 + 1),
        )

        self.assertFalse(ok)
        self.assertIn("不能超过", message)
        self.assertTrue(detail["errors"])
        self.assertEqual(tag_library._自定义标签库文件路径.read_bytes(), previous_bytes)

    def test_empty_batch_does_not_create_or_persist_an_empty_section(self) -> None:
        baseline = self._library({"已有": ["标签一"]})
        tag_library.保存自定义标签库(baseline)
        previous_bytes = tag_library._自定义标签库文件路径.read_bytes()

        ok, _message, detail = tag_library.批量添加自定义标签("主体", "空小类", " , ， ; ")

        self.assertFalse(ok)
        self.assertEqual(detail["added"], [])
        self.assertEqual(tag_library._自定义标签库文件路径.read_bytes(), previous_bytes)
        self.assertNotIn("空小类", tag_library.读取自定义标签库()["主体"])

    def test_invalid_existing_file_is_backed_up_before_recovery_write(self) -> None:
        invalid_bytes = b"{broken-json"
        tag_library._自定义标签库文件路径.write_bytes(invalid_bytes)
        tag_library._清空标签库缓存()

        ok, message = tag_library.添加自定义标签("主体", "恢复测试", "恢复标签")

        backup_path = tag_library._自定义标签库文件路径.with_name(
            f"{tag_library._自定义标签库文件路径.name}.invalid.bak"
        )
        self.assertTrue(ok, message)
        self.assertEqual(backup_path.read_bytes(), invalid_bytes)
        recovered = json.loads(tag_library._自定义标签库文件路径.read_text(encoding="utf-8"))
        self.assertIn("恢复标签", recovered["主体"]["恢复测试"])

    def test_failed_replacement_restores_quarantined_invalid_file(self) -> None:
        invalid_bytes = b"{broken-json"
        tag_library._自定义标签库文件路径.write_bytes(invalid_bytes)
        replacement = self._library({"恢复测试": ["恢复标签"]})
        original_replace = tag_library.os.replace
        replace_count = 0

        def fail_final_replace(source, target):
            nonlocal replace_count
            replace_count += 1
            if replace_count == 2:
                raise OSError("simulated final replace failure")
            return original_replace(source, target)

        with mock.patch.object(tag_library.os, "replace", side_effect=fail_final_replace):
            with self.assertRaisesRegex(OSError, "simulated"):
                tag_library.保存自定义标签库(replacement)

        self.assertEqual(tag_library._自定义标签库文件路径.read_bytes(), invalid_bytes)
        self.assertEqual(replace_count, 3)

    def test_frontend_rules_publish_all_persistence_limits(self) -> None:
        rules = tag_library.前端标签库数据()["custom_tag_rules"]
        for field in (
            "max_groups",
            "max_sections",
            "max_tags_per_section",
            "max_total_tags",
            "max_json_bytes",
            "max_batch_input_chars",
        ):
            self.assertGreater(int(rules[field]), 0)


class TestStateBuilderInputBounds(unittest.TestCase):
    @staticmethod
    def _build(kwargs, custom_tags):
        defaults = {
            "运行时随机标签": False,
            "运行时随机模式": "自动判断",
            "运行时随机强度": "中",
            "标签反推模式": "自动平衡",
            "提示词语言": "纯中文",
            "详细度": "标准",
            "输出模式": "完整结果",
            "系统提示词覆盖": "默认系统提示词",
            "API额外请求头": "",
        }
        return state_builder.build_state_from_kwargs(
            kwargs,
            collect_selected=lambda _kwargs: (
                OrderedDict({"主体": ["s" * 2_000]}),
                custom_tags,
            ),
            tag_group_index=lambda: {},
            group_slot_limits={"主体": 10},
            setting_defaults=defaults,
            safe_int=lambda value, default, minimum, maximum: max(
                minimum, min(maximum, int(value if value is not None else default))
            ),
            safe_float=lambda value, default, minimum, maximum: max(
                minimum, min(maximum, float(value if value is not None else default))
            ),
            normalize_inference_state=lambda selected, custom, settings: (
                selected,
                custom,
                [],
            ),
            collect_all_tags=lambda selected, custom: [
                *[tag for tags in selected.values() for tag in tags],
                *custom,
            ],
        )

    def test_free_text_settings_and_identifiers_are_bounded(self) -> None:
        _selected, _custom, settings, _all_tags = self._build(
            {
                "额外要求": "x" * 200_000,
                "智能文本输入": "\n".join(f"line-{index}-" + ("x" * 300) for index in range(500)),
                "系统提示词覆盖": "s" * 200_000,
                "API额外请求头": "h" * 100_000,
                "unique_id": "i" * 2_000,
            },
            [],
        )
        self.assertLessEqual(len(settings["额外要求"]), state_builder._TEXT_FIELD_MAX_CHARS)
        self.assertLessEqual(len(settings["智能文本输入"]), state_builder._TEXT_FIELD_MAX_CHARS)
        self.assertLessEqual(
            len(settings["智能文本输入"].splitlines()),
            state_builder._TEXT_FIELD_MAX_LINES,
        )
        self.assertLessEqual(len(settings["系统提示词覆盖"]), state_builder._SYSTEM_PROMPT_MAX_CHARS)
        self.assertLessEqual(len(settings["API额外请求头"]), state_builder._SETTING_TEXT_MAX_CHARS)
        self.assertEqual(len(settings["unique_id"]), 256)

    def test_selected_and_custom_tags_are_deduplicated_and_bounded(self) -> None:
        custom_tags = [
            f"tag-{index:04d}-" + ("x" * 1_000)
            for index in range(state_builder._CUSTOM_TAG_MAX_ITEMS + 100)
        ]
        selected, normalized_custom, _settings, all_tags = self._build({}, custom_tags)

        self.assertEqual(len(selected["主体"][0]), state_builder._CUSTOM_TAG_MAX_ITEM_CHARS)
        self.assertLessEqual(len(normalized_custom), state_builder._CUSTOM_TAG_MAX_ITEMS)
        self.assertTrue(
            all(len(tag) <= state_builder._CUSTOM_TAG_MAX_ITEM_CHARS for tag in normalized_custom)
        )
        total_chars = sum(map(len, normalized_custom)) + max(0, len(normalized_custom) - 1)
        self.assertLessEqual(total_chars, state_builder._CUSTOM_TAG_MAX_TOTAL_CHARS)
        self.assertEqual(len(normalized_custom), len(set(normalized_custom)))
        self.assertEqual(all_tags.count("、"), len(selected["主体"]) + len(normalized_custom) - 1)

    def test_custom_tag_scanning_is_bounded_even_when_entries_are_empty(self) -> None:
        custom_tags = [""] * (state_builder._CUSTOM_TAG_MAX_SCANNED_ITEMS + 500) + ["late-tag"]
        _selected, normalized_custom, _settings, _all_tags = self._build({}, custom_tags)
        self.assertEqual(normalized_custom, [])

    def test_structured_tag_block_is_rejected_before_unbounded_serialization(self) -> None:
        oversized = {"blocks": [{"text": "x" * (state_builder._TAG_BLOCK_JSON_MAX_CHARS + 1)}]}
        self.assertEqual(state_builder._clean_tag_block_json_field(oversized), "")

        too_deep: object = "leaf"
        for _ in range(state_builder._TAG_BLOCK_JSON_MAX_DEPTH + 1):
            too_deep = [too_deep]
        self.assertEqual(state_builder._clean_tag_block_json_field(too_deep), "")


class TestNsfwWorkspaceBounds(unittest.TestCase):
    def test_all_default_fields_survive_normalization(self) -> None:
        defaults = nsfw_presets.build_nsfw_workspace_defaults()
        normalized = nsfw_mapper.normalize_nsfw_workspace(defaults)
        self.assertEqual(set(normalized), set(defaults))
        self.assertLessEqual(nsfw_mapper._workspace_json_size(normalized), nsfw_mapper._WORKSPACE_MAX_JSON_BYTES)

    def test_mapper_mutates_only_local_workspace_to_bounded_known_state(self) -> None:
        workspace = {
            "enabled": True,
            "preset": "——",
            "negative_preset": "自定义负面提示词",
            "negative_apply_mode": "override",
            "custom_negative": "negative " * 20_000,
            "trigger_words": [f"trigger-{index}-" + ("x" * 1_000) for index in range(300)],
            "workspace_custom_tags": [f"custom-{index}-" + ("y" * 1_000) for index in range(300)],
            "custom_prefix": "prefix " * 5_000,
            "unknown_payload": {"nested": "z" * 200_000},
        }
        result = nsfw_mapper.map_nsfw_workspace_to_stage_state(
            workspace,
            tag_group_index={},
            group_slot_limits={},
        )

        self.assertNotIn("unknown_payload", workspace)
        self.assertLessEqual(nsfw_mapper._workspace_json_size(workspace), nsfw_mapper._WORKSPACE_MAX_JSON_BYTES)
        self.assertLessEqual(len(workspace["trigger_words"]), nsfw_mapper._WORKSPACE_MAX_LIST_ITEMS)
        self.assertTrue(
            all(len(item) <= nsfw_mapper._WORKSPACE_MAX_TERM_CHARS for item in workspace["trigger_words"])
        )
        self.assertLessEqual(len(result["custom_tags"]), nsfw_mapper._WORKSPACE_MAX_CUSTOM_TAGS)
        custom_chars = sum(map(len, result["custom_tags"])) + max(0, len(result["custom_tags"]) - 1)
        self.assertLessEqual(custom_chars, nsfw_mapper._WORKSPACE_MAX_CUSTOM_TAG_TOTAL_CHARS)
        self.assertLessEqual(len(result["negative_prompt"]), nsfw_mapper._WORKSPACE_MAX_NEGATIVE_CHARS)
        self.assertEqual(result["negative"]["mode"], "override")

    def test_legacy_camel_case_fields_are_migrated_before_bounding(self) -> None:
        normalized = nsfw_mapper.normalize_nsfw_workspace(
            {
                "enabled": True,
                "triggerWords": ["legacy-trigger"],
                "workspaceCustomTags": ["legacy-custom"],
                "selectorCharacter": "女王",
                "cameraMovement": "推进",
                "negativeApplyMode": "append",
                "customNegative": "legacy-negative",
            }
        )
        self.assertEqual(normalized["trigger_words"], ["legacy-trigger"])
        self.assertEqual(normalized["workspace_custom_tags"], ["legacy-custom"])
        self.assertEqual(normalized["selector_character"], "女王")
        self.assertEqual(normalized["camera_movement"], "推进")
        self.assertEqual(normalized["negative_apply_mode"], "append")
        self.assertEqual(normalized["custom_negative"], "legacy-negative")


if __name__ == "__main__":
    unittest.main()
