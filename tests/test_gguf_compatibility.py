"""Small synthetic GGUF fixtures: no weight downloads or actual inference."""
from __future__ import annotations

import struct
import enum
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from test_raw_model_support import load_nodes


def gguf_string(value):
    data = value.encode("utf-8")
    return struct.pack("<Q", len(data)) + data


def gguf_header(**metadata):
    data = b"GGUF" + struct.pack("<IQQ", 3, 0, len(metadata))
    for key, value in metadata.items():
        data += gguf_string(key)
        data += struct.pack("<I", 8 if isinstance(value, str) else 4)
        data += gguf_string(value) if isinstance(value, str) else struct.pack("<I", value)
    return data


class TestGGUFCompatibility(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "LLM"
        self.root.mkdir()
        self.nodes = load_nodes(Path(self.temp.name))

    def model(self, name, data=b"placeholder"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_metadata_detects_renamed_qwen_without_loading_weights(self):
        path = self.model("renamed-IQ4_XS.gguf", gguf_header(**{
            "general.architecture": "qwen38", "general.name": "Qwen3.8-27B", "general.file_type": 30,
        }))
        metadata = self.nodes._读取GGUF基本元数据(str(path))
        self.assertEqual(metadata["general.architecture"], "qwen38")
        config = self.nodes._规范化本地模型配置({"model": path.name, "family": "通用GGUF"})
        self.assertEqual(config["family"], "Qwen3.8-VL")

    def test_renamed_qwen_still_checks_exact_mmproj_version(self):
        self.model("renamed.gguf", gguf_header(**{"general.name": "Qwen3.6-27B"}))
        with self.assertRaisesRegex(RuntimeError, "不同 Qwen3 版本"):
            self.nodes._规范化本地模型配置({"model": "renamed.gguf", "mmproj": "mmproj-Qwen3.5-27B.gguf"})

    def test_unknown_architecture_or_quantization_is_delegated_to_runtime(self):
        for quant in ("Q4_K_M", "IQ2_XXS", "IQ4_XS", "TQ1_0", "MXFP4", "NVFP4"):
            with self.subTest(quant=quant):
                path = self.model(f"future-{quant}.gguf", gguf_header(**{"general.architecture": "future-text", "general.file_type": 999}))
                self.assertEqual(self.nodes._解析本地模型路径(path.name), (str(path), "gguf"))
                self.assertIn(path.name, self.nodes._列出llm文件())

    def test_media_and_projector_metadata_are_not_text_main_models(self):
        for architecture in ("flux3", "qwen_image", "moss_image", "clip"):
            with self.subTest(architecture=architecture):
                path = self.model(f"{architecture}.gguf", gguf_header(**{"general.architecture": architecture}))
                with self.assertRaisesRegex(RuntimeError, "下游.*GGUF 加载器"):
                    self.nodes._解析本地模型路径(path.name)

    def test_only_split_first_shard_is_listed_and_legacy_selection_resolves(self):
        first = self.model("nested/Qwen3.8-Q4_K_M-00001-of-00002.gguf")
        second = self.model("nested/Qwen3.8-Q4_K_M-00002-of-00002.gguf")
        self.assertIn("nested/" + first.name, self.nodes._列出llm文件())
        self.assertNotIn("nested/" + second.name, self.nodes._列出llm文件())
        self.assertEqual(self.nodes._解析本地模型路径("nested/" + second.name), (str(first), "gguf"))
        config = self.nodes._规范化本地模型配置({"model": "nested/" + second.name})
        self.assertEqual(config["model"], "nested/" + first.name)

    def test_missing_shards_fail_before_unloading_existing_model(self):
        path = self.model("Qwen3.8-00001-of-00003.gguf")
        for storage in (self.nodes._QwenStorage, self.nodes._Gemma4Storage):
            with self.subTest(storage=storage.__name__):
                old = types.SimpleNamespace(settings={"model": "current.gguf"})
                storage.model = old
                with mock.patch.object(storage, "unload") as unload:
                    with self.assertRaisesRegex(RuntimeError, "分片不完整"):
                        storage.load({"model": path.name, "family": "Qwen3.8-VL"})
                    unload.assert_not_called()
                    self.assertIs(storage.model, old)

    def test_normalized_family_diagnostic_does_not_reload_the_same_weights(self):
        self.model("renamed.gguf", gguf_header(**{"general.name": "Qwen3.8-27B"}))
        storage = self.nodes._QwenStorage
        model = storage.load({"model": "renamed.gguf", "family": "通用GGUF", "think": False})
        self.assertIn("family_auto_note", model.settings)
        with mock.patch.object(storage, "unload") as unload:
            self.assertIs(storage.load(dict(model.settings)), model)
            self.assertIs(storage.load({**model.settings, "family_auto_note": "diagnostic only"}), model)
            unload.assert_not_called()
        # Real loading parameters, unlike the note, must still invalidate the cache.
        self.assertIsNot(storage.load({**model.settings, "n_ctx": 4096}), model)
        latest = storage.model
        self.assertIsNot(storage.load(dict(latest.settings), force_reload=True), latest)

    def test_old_managed_handle_uses_current_weights_when_only_diagnostics_changed(self):
        old_llm, current_llm = object(), object()
        settings = {"model": "renamed.gguf", "family": "Qwen3.8-VL"}
        current = types.SimpleNamespace(llm=current_llm, settings={**settings, "family_auto_note": "auto detected"})
        storage = types.SimpleNamespace(model=current)
        with mock.patch.object(self.nodes, "_按设置重载托管模型") as reload_model:
            self.assertIs(self.nodes._同步托管llm实例(old_llm, settings, storage), current_llm)
            reload_model.assert_not_called()

    def test_invalid_projection_fails_before_unloading_existing_model(self):
        self.model("generic.gguf")
        (self.root / "directory-mmproj.gguf").mkdir()
        for storage in (self.nodes._QwenStorage, self.nodes._Gemma4Storage):
            for projection in ("missing-mmproj.gguf", "directory-mmproj.gguf", "../outside-mmproj.gguf"):
                with self.subTest(storage=storage.__name__, projection=projection):
                    old = types.SimpleNamespace(settings={"model": "current.gguf"})
                    storage.model = old
                    with mock.patch.object(storage, "unload") as unload:
                        with self.assertRaises((FileNotFoundError, ValueError)):
                            storage.load({"model": "generic.gguf", "family": "通用GGUF", "mmproj": projection, "think": False})
                        unload.assert_not_called()
                        self.assertIs(storage.model, old)

    def test_raw_model_projection_misconfiguration_preserves_existing_model(self):
        self.model("raw/config.json", b"{}")
        self.model("raw/model.safetensors")
        for storage in (self.nodes._QwenStorage, self.nodes._Gemma4Storage):
            with self.subTest(storage=storage.__name__):
                old = types.SimpleNamespace(settings={"model": "current.gguf"})
                storage.model = old
                with mock.patch.object(storage, "unload") as unload:
                    with self.assertRaisesRegex(RuntimeError, "原始 Transformers 模型不使用"):
                        storage.load({"model": "raw", "family": "通用GGUF", "mmproj": "mmproj.gguf"})
                    unload.assert_not_called()
                    self.assertIs(storage.model, old)

    def test_missing_llama_dependency_preserves_existing_model(self):
        self.model("generic.gguf")
        for storage in (self.nodes._QwenStorage, self.nodes._Gemma4Storage):
            with self.subTest(storage=storage.__name__):
                old = types.SimpleNamespace(settings={"model": "current.gguf"})
                storage.model = old
                with mock.patch.object(self.nodes, "Llama", None), mock.patch.object(storage, "unload") as unload:
                    with self.assertRaisesRegex(RuntimeError, "llama-cpp-python"):
                        storage.load({"model": "generic.gguf", "family": "通用GGUF", "think": False})
                    unload.assert_not_called()
                    self.assertIs(storage.model, old)

    def test_unavailable_visual_handlers_fail_before_unloading_existing_model(self):
        self.model("generic.gguf")
        self.model("mmproj.gguf")
        cases = (
            (self.nodes._QwenStorage, "Qwen3-VL", "Qwen3VLChatHandler"),
            (self.nodes._QwenStorage, "Qwen3.5-VL", "Qwen35ChatHandler"),
            (self.nodes._QwenStorage, "Gemma4", "Gemma4ChatHandler"),
            (self.nodes._Gemma4Storage, "Gemma4", "Gemma4ChatHandler"),
        )
        for storage, family, handler in cases:
            with self.subTest(storage=storage.__name__, family=family):
                old = types.SimpleNamespace(settings={"model": "current.gguf"})
                storage.model = old
                with mock.patch.object(self.nodes, handler, None), mock.patch.object(storage, "unload") as unload:
                    with self.assertRaisesRegex(RuntimeError, handler):
                        storage.load({"model": "generic.gguf", "family": family, "mmproj": "mmproj.gguf", "think": False})
                    unload.assert_not_called()
                    self.assertIs(storage.model, old)

    def test_unknown_visual_family_fails_before_unloading_existing_model(self):
        self.model("generic.gguf")
        self.model("mmproj.gguf")
        storage = self.nodes._QwenStorage
        old = types.SimpleNamespace(settings={"model": "current.gguf"})
        storage.model = old
        with mock.patch.object(storage, "unload") as unload:
            with self.assertRaisesRegex(RuntimeError, "暂未配置专用视觉"):
                storage.load({"model": "generic.gguf", "family": "通用GGUF", "mmproj": "mmproj.gguf", "think": False})
            unload.assert_not_called()
            self.assertIs(storage.model, old)

    def test_invalid_kv_or_constructor_options_do_not_release_model_or_construct_handler(self):
        self.model("generic.gguf")
        self.model("mmproj.gguf")
        options = (
            ({"cache_type_k": "q4_0"}, RuntimeError, "未导出 q4_0"),
            ({"cache_type_v": "q8_0"}, RuntimeError, "不支持 type_k/type_v"),
            ({"cache_type_k": "unsupported"}, ValueError, "未知 KV"),
            ({"custom_llama_params": "{invalid"}, ValueError, "合法 JSON"),
            ({"n_ctx": "invalid"}, ValueError, "invalid"),
        )
        for storage in (self.nodes._QwenStorage, self.nodes._Gemma4Storage):
            for extra, error_type, message in options:
                with self.subTest(storage=storage.__name__, options=extra):
                    old = types.SimpleNamespace(settings={"model": "current.gguf"})
                    storage.model = old
                    with mock.patch.object(self.nodes, "Gemma4ChatHandler") as handler, mock.patch.object(storage, "unload") as unload:
                        with self.assertRaisesRegex(error_type, message):
                            storage.load({"model": "generic.gguf", "family": "Gemma4", "mmproj": "mmproj.gguf", "think": False, **extra})
                        handler.assert_not_called()
                        unload.assert_not_called()
                        self.assertIs(storage.model, old)

    def test_valid_handler_is_constructed_only_after_existing_model_is_released(self):
        self.model("generic.gguf")
        self.model("mmproj.gguf")
        for storage in (self.nodes._QwenStorage, self.nodes._Gemma4Storage):
            with self.subTest(storage=storage.__name__):
                storage.model = types.SimpleNamespace(settings={"model": "current.gguf"})
                events = []
                handler = object()
                with (
                    mock.patch.object(storage, "unload", side_effect=lambda: events.append("unload")),
                    mock.patch.object(self.nodes, "Gemma4ChatHandler", side_effect=lambda **kwargs: events.append("handler") or handler),
                ):
                    model = storage.load({"model": "generic.gguf", "family": "Gemma4", "mmproj": "mmproj.gguf", "think": False})
                self.assertEqual(events, ["unload", "handler"])
                self.assertIs(model.chat_handler, handler)

    def test_qwen38_missing_visual_handler_keeps_existing_text_fallback(self):
        self.model("generic.gguf")
        self.model("mmproj.gguf")
        storage = self.nodes._QwenStorage
        old_llm = mock.Mock()
        storage.model = types.SimpleNamespace(llm=old_llm, settings={"model": "current.gguf"})
        with mock.patch.object(self.nodes, "Qwen38ChatHandler", None), mock.patch.object(self.nodes, "Qwen38VLChatHandler", None):
            model = storage.load({"model": "generic.gguf", "family": "Qwen3.8-VL", "mmproj": "mmproj.gguf", "think": False})
        old_llm.close.assert_called_once()
        self.assertIsNone(model.chat_handler)
        self.assertIs(storage.model, model)

    def test_comfy_validation_accepts_legacy_split_selection_without_opening_other_paths(self):
        self.model("nested/model-00001-of-00002.gguf")
        self.model("nested/model-00002-of-00002.gguf")
        for loader in (self.nodes.QwenTE模型加载器, self.nodes.Gemma4TE模型加载器):
            with self.subTest(loader=loader.__name__):
                self.assertIs(loader.VALIDATE_INPUTS("nested/model-00002-of-00002.gguf"), True)
                self.assertIsNot(loader.VALIDATE_INPUTS("missing.gguf"), True)
                self.assertIsNot(loader.VALIDATE_INPUTS("../outside.gguf"), True)

    def test_split_count_is_bounded_and_zero_index_is_rejected(self):
        for name in ("model-00000-of-00002.gguf", "model-00001-of-99999.gguf"):
            with self.subTest(name=name):
                self.model(name)
                with self.assertRaisesRegex(RuntimeError, "分片编号无效"):
                    self.nodes._解析本地模型路径(name)

    def test_truncated_unknown_and_oversized_metadata_are_nonfatal(self):
        valid = gguf_header(**{"general.architecture": "future-text"})
        for data in (b"", b"GGUF", valid[:-3], b"GGUF" + struct.pack("<IQQ", 99, 0, 0), b"GGUF" + struct.pack("<IQQ", 3, 0, 999_999_999)):
            with self.subTest(size=len(data)):
                path = self.model("test.gguf", data)
                self.assertIsInstance(self.nodes._读取GGUF基本元数据(str(path)), dict)

    def test_metadata_arrays_are_skipped_without_allocating_their_contents(self):
        data = b"GGUF" + struct.pack("<IQQ", 3, 0, 3)
        data += gguf_string("general.name") + struct.pack("<I", 8) + gguf_string("Qwen3.8-27B")
        data += gguf_string("unrelated.array") + struct.pack("<IIQ", 9, 4, 2) + struct.pack("<II", 7, 8)
        data += gguf_string("general.architecture") + struct.pack("<I", 8) + gguf_string("qwen38")
        path = self.model("array.gguf", data)
        self.assertEqual(self.nodes._读取GGUF基本元数据(str(path))["general.architecture"], "qwen38")
        # A hostile declared length is bounded by the header budget, not looped.
        hostile = b"GGUF" + struct.pack("<IQQ", 3, 0, 1)
        hostile += gguf_string("unrelated.array") + struct.pack("<IIQ", 9, 8, 2**63)
        self.assertEqual(self.nodes._读取GGUF基本元数据(str(self.model("hostile.gguf", hostile))), {})

    def test_new_kv_types_only_use_constants_exported_by_installed_runtime(self):
        runtime = types.SimpleNamespace(GGML_TYPE_Q4_0=2, GGML_TYPE_Q4_1=3, GGML_TYPE_Q5_0=6, GGML_TYPE_Q5_1=7, GGML_TYPE_BF16=30)
        with mock.patch.object(self.nodes, "_LLAMA_LOW_LEVEL", runtime):
            for name, expected in (("q4_0", 2), ("q4_1", 3), ("q5_0", 6), ("q5_1", 7), ("bf16", 30)):
                with self.subTest(name=name):
                    self.assertEqual(self.nodes._解析kv缓存类型(name), expected)
        with self.assertRaisesRegex(RuntimeError, "改回默认"):
            self.nodes._解析kv缓存类型("q4_0")
        self.assertIsNone(self.nodes._解析kv缓存类型("默认(F16)"))
        self.assertEqual(self.nodes._解析kv缓存类型("q8_0"), 8)

    def test_new_runtime_ggml_enum_location_is_compatible_with_old_flat_constants(self):
        class GGMLType(enum.IntEnum):
            GGML_TYPE_Q4_0 = 2
            GGML_TYPE_Q4_1 = 3
            GGML_TYPE_Q5_0 = 6
            GGML_TYPE_Q5_1 = 7
            GGML_TYPE_BF16 = 30

        with mock.patch.object(self.nodes, "_LLAMA_GGML", types.SimpleNamespace(GGMLType=GGMLType)):
            for value in ("q4_0", "q4_1", "q5_0", "q5_1", "bf16"):
                with self.subTest(value=value):
                    expected = int(getattr(GGMLType, "GGML_TYPE_" + value.upper()))
                    self.assertEqual(self.nodes._解析kv缓存类型(value), expected)
                    self.assertIs(type(self.nodes._解析kv缓存类型(value)), int)


if __name__ == "__main__":
    unittest.main()
