# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import gc
import json
import pathlib
import random
import re
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock
from collections import OrderedDict
from copy import deepcopy


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = json.loads((ROOT / "tests" / "fixtures" / "brief_cases.json").read_text(encoding="utf-8"))


def load_module(relative_path: str, module_name: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_nodes_for_storage_test(models_dir: pathlib.Path, runtime: dict[str, object] | None = None):
    module_name = "qwen_te_nodes_storage_test"
    dependency_names = [
        module_name,
        "folder_paths",
        "comfy",
        "comfy.model_management",
        "llama_cpp",
        "llama_cpp.llama_tokenizer",
        "llama_cpp.llama_chat_format",
    ]
    saved_modules = {name: sys.modules.get(name) for name in dependency_names}

    if runtime is None:
        folder_paths_module = types.ModuleType("folder_paths")
        folder_paths_module.models_dir = str(models_dir)
        folder_paths_module.supported_pt_extensions = set()
        folder_paths_module.folder_names_and_paths = {}
        folder_paths_module.get_filename_list = lambda _name: []

        model_management_module = types.ModuleType("comfy.model_management")
        model_management_module.soft_empty_cache = lambda: None
        model_management_module.unload_all_models = lambda *args, **kwargs: None
        model_management_module.processing_interrupted = lambda: False
        model_management_module.InterruptProcessingException = RuntimeError
        comfy_module = types.ModuleType("comfy")
        comfy_module.__path__ = []
        comfy_module.model_management = model_management_module

        class FakeLlama:
            created: list[object] = []
            created_lock = threading.Lock()
            block_completions = False
            completion_started = threading.Event()
            completion_release = threading.Event()

            def __init__(self, model_path=None, **_kwargs):
                self.model_path = model_path
                self.closed = False
                self.fail_once = False
                self.reset_count = 0
                with type(self).created_lock:
                    type(self).created.append(self)
                time.sleep(0.03)

            def create_chat_completion(self, **_kwargs):
                if self.fail_once:
                    self.fail_once = False
                    raise RuntimeError("access violation while tokenizing")
                if type(self).block_completions:
                    type(self).completion_started.set()
                    if not type(self).completion_release.wait(2.0):
                        raise RuntimeError("test completion release timeout")
                return {"choices": [{"message": {"content": "ok"}}]}

            def reset(self):
                self.reset_count += 1

            def close(self):
                self.closed = True

        llama_cpp_module = types.ModuleType("llama_cpp")
        llama_cpp_module.__path__ = []
        llama_cpp_module.Llama = FakeLlama
        llama_cpp_module.GGML_TYPE_Q8_0 = 8
        tokenizer_module = types.ModuleType("llama_cpp.llama_tokenizer")
        tokenizer_module.LlamaTokenizer = None
        chat_format_module = types.ModuleType("llama_cpp.llama_chat_format")
        chat_format_module.Qwen3VLChatHandler = None
        chat_format_module.Qwen35ChatHandler = None
        chat_format_module.Gemma4ChatHandler = None
        runtime = {
            "folder_paths": folder_paths_module,
            "comfy": comfy_module,
            "model_management": model_management_module,
            "llama_cpp": llama_cpp_module,
            "tokenizer": tokenizer_module,
            "chat_format": chat_format_module,
            "fake_llama": FakeLlama,
        }
    else:
        folder_paths_module = runtime["folder_paths"]
        comfy_module = runtime["comfy"]
        model_management_module = runtime["model_management"]
        llama_cpp_module = runtime["llama_cpp"]
        tokenizer_module = runtime["tokenizer"]
        chat_format_module = runtime["chat_format"]
        FakeLlama = runtime["fake_llama"]

    sys.modules["folder_paths"] = folder_paths_module
    sys.modules["comfy"] = comfy_module
    sys.modules["comfy.model_management"] = model_management_module
    sys.modules["llama_cpp"] = llama_cpp_module
    sys.modules["llama_cpp.llama_tokenizer"] = tokenizer_module
    sys.modules["llama_cpp.llama_chat_format"] = chat_format_module
    try:
        module = load_module("nodes.py", module_name)
    finally:
        for name, original in saved_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
    return module, FakeLlama, runtime


skills = load_module("stage_prompt/skills.py", "stage_prompt_skills_test")
normalizer = load_module("stage_prompt/normalizer.py", "stage_prompt_normalizer_test")
negative_builder = load_module("stage_prompt/negative_builder.py", "stage_prompt_negative_builder_test")
prompt_builder = load_module("stage_prompt/prompt_builder.py", "stage_prompt_prompt_builder_test")
randomizer = load_module("stage_prompt/randomizer.py", "stage_prompt_randomizer_test")
formatter = load_module("stage_prompt/formatter.py", "stage_prompt_formatter_test")
model_refiner = load_module("stage_prompt/model_refiner.py", "stage_prompt_model_refiner_test")
smart_text = load_module("stage_prompt/smart_text.py", "stage_prompt_smart_text_test")
tag_block_composer = load_module("stage_prompt/tag_block_composer.py", "stage_prompt_tag_block_composer_test")
tag_library = load_module("prompt_tag_library.py", "prompt_tag_library_test")
state_builder = load_module("stage_prompt/state_builder.py", "stage_prompt_state_builder_test")
nsfw_presets = load_module("stage_prompt/nsfw_presets.py", "stage_prompt_nsfw_presets_test")
nsfw_workspace = load_module("stage_prompt/nsfw_workspace.py", "stage_prompt_nsfw_workspace_test")
nsfw_mapper = load_module("stage_prompt/nsfw_mapper.py", "stage_prompt_nsfw_mapper_test")
dependency_installer = load_module("install_dependencies.py", "qwen_te_dependency_installer_test")


def uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def collect_all_tags(selected: OrderedDict[str, list[str]], custom: list[str]) -> list[str]:
    return uniq([tag for values in selected.values() for tag in values] + list(custom))


def load_stage_prompt_generator_for_integration_test(*, nodes_available: bool = True):
    package_name = "comfyui_qwen3_5_llama_te_stage_prompt_testpkg"
    package_prefix = f"{package_name}"
    stage_prefix = f"{package_prefix}.stage_prompt"
    saved_modules = {
        name: sys.modules.get(name)
        for name in [
            package_prefix,
            stage_prefix,
            f"{package_prefix}.nodes",
            f"{package_prefix}.prompt_tag_library",
            f"{package_prefix}.prompt_semantic_config",
            f"{package_prefix}.prompt_rule_config",
            f"{package_prefix}.stage_prompt.negative_builder",
            f"{package_prefix}.stage_prompt.nsfw_mapper",
            f"{package_prefix}.stage_prompt.nsfw_presets",
            f"{package_prefix}.stage_prompt.nsfw_workspace",
            f"{package_prefix}.stage_prompt.formatter",
            f"{package_prefix}.stage_prompt.model_refiner",
            f"{package_prefix}.stage_prompt.normalizer",
            f"{package_prefix}.stage_prompt.prompt_builder",
            f"{package_prefix}.stage_prompt.randomizer",
            f"{package_prefix}.stage_prompt.skills",
            f"{package_prefix}.stage_prompt.smart_text",
            f"{package_prefix}.stage_prompt.state_builder",
            f"{package_prefix}.stage_prompt.tag_block_composer",
        ]
    }

    package_module = types.ModuleType(package_prefix)
    package_module.__path__ = [str(ROOT)]
    stage_package_module = types.ModuleType(stage_prefix)
    stage_package_module.__path__ = [str(ROOT / "stage_prompt")]
    nodes_module = types.ModuleType(f"{package_prefix}.nodes")
    nodes_module._调用chat_completion = lambda *args, **kwargs: None
    nodes_module._清洗think块文本 = lambda text: text
    nodes_module._规范化随机种子 = lambda seed: int(seed)
    nodes_module.any_type = object()

    semantic_config = load_module("prompt_semantic_config.py", f"{package_prefix}.prompt_semantic_config")
    rule_config = load_module("prompt_rule_config.py", f"{package_prefix}.prompt_rule_config")
    sys.modules[package_prefix] = package_module
    sys.modules[stage_prefix] = stage_package_module
    if nodes_available:
        sys.modules[f"{package_prefix}.nodes"] = nodes_module
    sys.modules[f"{package_prefix}.prompt_tag_library"] = tag_library
    sys.modules[f"{package_prefix}.prompt_semantic_config"] = semantic_config
    sys.modules[f"{package_prefix}.prompt_rule_config"] = rule_config
    sys.modules[f"{package_prefix}.stage_prompt.negative_builder"] = negative_builder
    sys.modules[f"{package_prefix}.stage_prompt.nsfw_mapper"] = nsfw_mapper
    sys.modules[f"{package_prefix}.stage_prompt.nsfw_presets"] = nsfw_presets
    sys.modules[f"{package_prefix}.stage_prompt.nsfw_workspace"] = nsfw_workspace
    sys.modules[f"{package_prefix}.stage_prompt.formatter"] = formatter
    sys.modules[f"{package_prefix}.stage_prompt.model_refiner"] = model_refiner
    sys.modules[f"{package_prefix}.stage_prompt.normalizer"] = normalizer
    sys.modules[f"{package_prefix}.stage_prompt.prompt_builder"] = prompt_builder
    sys.modules[f"{package_prefix}.stage_prompt.randomizer"] = randomizer
    sys.modules[f"{package_prefix}.stage_prompt.skills"] = skills
    sys.modules[f"{package_prefix}.stage_prompt.smart_text"] = smart_text
    sys.modules[f"{package_prefix}.stage_prompt.state_builder"] = state_builder
    sys.modules[f"{package_prefix}.stage_prompt.tag_block_composer"] = tag_block_composer

    original_import = __import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if not nodes_available and (
            name == f"{package_prefix}.nodes"
            or name.endswith(".nodes")
            or (level > 0 and name == "nodes")
        ):
            raise ModuleNotFoundError(name)
        return original_import(name, globals, locals, fromlist, level)

    try:
        with mock.patch("builtins.__import__", side_effect=guarded_import):
            module = load_module("stage_prompt_generator.py", f"{package_prefix}.stage_prompt_generator")
    finally:
        for name, original in saved_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
    return module


def load_plugin_init_for_integration_test(*, failing_imports: set[str] | None = None):
    package_name = "comfyui_qwen3_5_llama_te_init_testpkg"
    package_prefix = f"{package_name}"
    saved_modules = {
        name: sys.modules.get(name)
        for name in [
            package_prefix,
            f"{package_prefix}.nodes",
            f"{package_prefix}.prompt_tag_library",
            f"{package_prefix}.stage_prompt_generator",
            f"{package_prefix}.quality_audit_ocr_skin",
            f"{package_prefix}.embedded_browser",
        ]
    }

    package_module = types.ModuleType(package_prefix)
    package_module.__path__ = [str(ROOT)]
    nodes_module = types.ModuleType(f"{package_prefix}.nodes")
    for name in ("Gemma4TE卸载模型", "Gemma4TE图像推理", "Gemma4TE模型加载器", "QwenTE卸载模型", "QwenTE图像推理", "QwenTE模型加载器"):
        setattr(nodes_module, name, type(name, (), {}))

    tag_module = types.ModuleType(f"{package_prefix}.prompt_tag_library")
    tag_module.前端标签库数据 = lambda: {}
    tag_module.删除自定义标签 = lambda *args, **kwargs: (True, "")
    tag_module.添加自定义标签 = lambda *args, **kwargs: (True, "")
    tag_module.批量添加自定义标签 = lambda *args, **kwargs: (True, "", {})
    tag_module.推荐自定义标签归类 = lambda *args, **kwargs: {}

    stage_module = types.ModuleType(f"{package_prefix}.stage_prompt_generator")
    stage_module.QwenTE提示词合集拆分器 = type("QwenTE提示词合集拆分器", (), {})
    stage_module.QwenTE阶段式提示词生成器 = type("QwenTE阶段式提示词生成器", (), {})
    stage_module.QwenTE通用模型阶段式提示词生成器 = type("QwenTE通用模型阶段式提示词生成器", (), {})
    stage_module.构建NSFW工作台目录 = lambda: {"defaults": {"enabled": False}, "options": {"scene": ["——"]}}
    stage_module.构建状态可视化预览 = lambda *args, **kwargs: {}
    stage_module.构建运行时随机预览状态 = lambda *args, **kwargs: {}
    stage_module.获取阶段节点输出缓存 = lambda *args, **kwargs: {}

    sys.modules[package_prefix] = package_module
    sys.modules[f"{package_prefix}.nodes"] = nodes_module
    sys.modules[f"{package_prefix}.prompt_tag_library"] = tag_module
    sys.modules[f"{package_prefix}.stage_prompt_generator"] = stage_module

    original_import = __import__
    failing_imports = set(failing_imports or set())

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name in failing_imports:
            raise ModuleNotFoundError(name)
        return original_import(name, globals, locals, fromlist, level)

    try:
        with mock.patch("builtins.__import__", side_effect=guarded_import):
            module = load_module("__init__.py", f"{package_prefix}.__init__")
    finally:
        for name, original in saved_modules.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
        sys.modules.pop(f"{package_prefix}.__init__", None)
    return module


def remove_tag_from_state(selected: OrderedDict[str, list[str]], custom_tags: list[str], tag: str) -> None:
    for key in list(selected.keys()):
        selected[key] = [item for item in selected[key] if item != tag]
    custom_tags[:] = [item for item in custom_tags if item != tag]


def append_tag_to_state(selected: OrderedDict[str, list[str]], custom_tags: list[str], tag: str) -> None:
    if tag in collect_all_tags(selected, custom_tags):
        return
    if "构图视角" in selected:
        selected["构图视角"].append(tag)
    else:
        custom_tags.append(tag)


class TestStagePromptModules(unittest.TestCase):
    def test_module_root_matches_current_worktree(self) -> None:
        self.assertEqual(ROOT, pathlib.Path(__file__).resolve().parents[1])

    def test_model_storage_serializes_load_completion_and_unload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = pathlib.Path(temp_dir)
            llm_dir = models_dir / "LLM"
            llm_dir.mkdir()
            (llm_dir / "fake-qwen.gguf").touch()
            module, fake_llama, _runtime = load_nodes_for_storage_test(models_dir)
            config = {
                "model": "fake-qwen.gguf",
                "family": "Qwen3-VL",
                "think": False,
            }

            worker_count = 8
            barrier = threading.Barrier(worker_count)
            loaded_models: list[object] = []
            load_errors: list[BaseException] = []

            def load_model():
                try:
                    barrier.wait(timeout=2.0)
                    loaded_models.append(module._QwenStorage.load(config))
                except BaseException as error:
                    load_errors.append(error)

            workers = [threading.Thread(target=load_model) for _ in range(worker_count)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=3.0)

            self.assertFalse(load_errors)
            self.assertTrue(all(not worker.is_alive() for worker in workers))
            self.assertEqual(len(fake_llama.created), 1)
            self.assertEqual(len({id(model) for model in loaded_models}), 1)

            active_model = loaded_models[0]
            fake_llama.block_completions = True
            completion_results: list[dict] = []
            completion_errors: list[BaseException] = []

            def run_completion():
                try:
                    completion_results.append(
                        module._调用chat_completion(active_model.llm, messages=[{"role": "user", "content": "test"}], params={})
                    )
                except BaseException as error:
                    completion_errors.append(error)

            completion_thread = threading.Thread(target=run_completion)
            completion_thread.start()
            self.assertTrue(fake_llama.completion_started.wait(1.0))

            unload_done = threading.Event()

            def unload_model():
                module._QwenStorage.unload()
                unload_done.set()

            unload_thread = threading.Thread(target=unload_model)
            unload_thread.start()
            self.assertFalse(unload_done.wait(0.08))
            fake_llama.completion_release.set()
            completion_thread.join(timeout=2.0)
            unload_thread.join(timeout=2.0)

            self.assertFalse(completion_errors)
            self.assertEqual(completion_results[0]["choices"][0]["message"]["content"], "ok")
            self.assertTrue(unload_done.is_set())
            self.assertTrue(active_model.llm.closed)
            self.assertIsNone(module._QwenStorage.model)

    def test_model_recovery_uses_recorded_owner_storage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = pathlib.Path(temp_dir)
            llm_dir = models_dir / "LLM"
            llm_dir.mkdir()
            (llm_dir / "fake-gemma.gguf").touch()
            module, fake_llama, _runtime = load_nodes_for_storage_test(models_dir)
            config = {
                "model": "fake-gemma.gguf",
                "family": "Gemma4",
                "think": False,
            }

            original_model = module._QwenStorage.load(config)
            original_model.llm.fail_once = True
            result = module._调用chat_completion(
                original_model.llm,
                messages=[{"role": "user", "content": "recover"}],
                params={},
            )

            self.assertEqual(result["choices"][0]["message"]["content"], "ok")
            self.assertEqual(len(fake_llama.created), 2)
            self.assertTrue(original_model.llm.closed)
            self.assertIs(module._QwenStorage.model.llm, fake_llama.created[-1])
            self.assertIsNone(module._Gemma4Storage.model)

    def test_model_storage_survives_module_hot_reload_without_duplicate_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = pathlib.Path(temp_dir)
            llm_dir = models_dir / "LLM"
            llm_dir.mkdir()
            (llm_dir / "hot-reload.gguf").touch()
            first_module, fake_llama, runtime = load_nodes_for_storage_test(models_dir)
            config = {
                "model": "hot-reload.gguf",
                "family": "Gemma4",
                "think": False,
            }
            original_model = first_module._QwenStorage.load(config)
            original_lock = first_module._MODEL_STORAGE_LOCK
            original_storage = first_module._QwenStorage

            second_module, _, _ = load_nodes_for_storage_test(models_dir, runtime=runtime)

            self.assertIs(second_module._MODEL_STORAGE_LOCK, original_lock)
            self.assertIs(second_module._QwenStorage.model, original_model)
            self.assertIsNone(original_storage.model)
            self.assertIs(original_model.llm._qwen_te_storage_owner, second_module._QwenStorage)
            self.assertEqual(original_model.llm._qwen_te_storage_key, "qwen")
            self.assertEqual(len(fake_llama.created), 1)

            result = second_module._调用chat_completion(
                original_model.llm,
                messages=[{"role": "user", "content": "after reload"}],
                params={},
            )
            self.assertEqual(result["choices"][0]["message"]["content"], "ok")
            self.assertEqual(len(fake_llama.created), 1)
            runtime["model_management"].unload_all_models()
            self.assertTrue(original_model.llm.closed)
            self.assertIsNone(second_module._QwenStorage.model)
            self.assertNotIn("qwen", second_module._MODEL_STORAGE_MODELS)

    def test_managed_model_cooperative_deadline_aborts_decode_and_cleans_callback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = pathlib.Path(temp_dir)
            llm_dir = models_dir / "LLM"
            llm_dir.mkdir()
            (llm_dir / "cooperative-timeout.gguf").touch()
            module, _fake_llama, _runtime = load_nodes_for_storage_test(models_dir)
            model = module._QwenStorage.load(
                {"model": "cooperative-timeout.gguf", "family": "Qwen3-VL", "think": False}
            )
            model.llm._ctx = types.SimpleNamespace(ctx=object())

            class FakeLowLevel:
                current_callback = None
                installed_callbacks: list[object] = []

                @staticmethod
                def ggml_abort_callback(callback=None):
                    return callback

                @classmethod
                def llama_set_abort_callback(cls, _context, callback, _data):
                    cls.current_callback = callback
                    cls.installed_callbacks.append(callback)

            received_kwargs: list[dict] = []

            def blocking_completion(**kwargs):
                received_kwargs.append(dict(kwargs))
                while True:
                    callback = FakeLowLevel.current_callback
                    if callable(callback) and callback(None):
                        raise RuntimeError("llama_decode failed (code 2): Decoding aborted by user callback")
                    time.sleep(0.002)

            model.llm.create_chat_completion = blocking_completion
            module._LLAMA_LOW_LEVEL = FakeLowLevel
            deadline = time.monotonic() + 0.04
            with self.assertRaisesRegex(TimeoutError, "合作中止"):
                module._调用chat_completion(
                    model.llm,
                    messages=[{"role": "user", "content": "timeout"}],
                    params={module._MODEL_CALL_DEADLINE_PARAM: deadline},
                )

            self.assertEqual(len(received_kwargs), 1)
            self.assertNotIn(module._MODEL_CALL_DEADLINE_PARAM, received_kwargs[0])
            self.assertIsNone(FakeLowLevel.current_callback)
            self.assertTrue(callable(FakeLowLevel.installed_callbacks[0]))
            self.assertIsNone(FakeLowLevel.installed_callbacks[-1])

    def test_deadline_exception_does_not_trigger_model_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = pathlib.Path(temp_dir)
            llm_dir = models_dir / "LLM"
            llm_dir.mkdir()
            (llm_dir / "deadline-no-recovery.gguf").touch()
            module, fake_llama, _runtime = load_nodes_for_storage_test(models_dir)
            model = module._QwenStorage.load(
                {"model": "deadline-no-recovery.gguf", "family": "Qwen3-VL", "think": False}
            )

            def late_tokenizer_failure(**_kwargs):
                time.sleep(0.04)
                raise RuntimeError("tokenizer access violation after deadline")

            model.llm.create_chat_completion = late_tokenizer_failure
            with self.assertRaisesRegex(TimeoutError, "合作中止"):
                module._调用chat_completion(
                    model.llm,
                    messages=[{"role": "user", "content": "timeout"}],
                    params={module._MODEL_CALL_DEADLINE_PARAM: time.monotonic() + 0.02},
                )

            self.assertEqual(len(fake_llama.created), 1)
            self.assertFalse(model.llm.closed)
            self.assertIs(module._QwenStorage.model, model)

    def test_result_returned_after_deadline_is_discarded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = pathlib.Path(temp_dir)
            llm_dir = models_dir / "LLM"
            llm_dir.mkdir()
            (llm_dir / "late-result.gguf").touch()
            module, fake_llama, _runtime = load_nodes_for_storage_test(models_dir)
            model = module._QwenStorage.load(
                {"model": "late-result.gguf", "family": "Qwen3-VL", "think": False}
            )

            def late_success(**_kwargs):
                time.sleep(0.04)
                return {"choices": [{"message": {"content": "late result"}}]}

            model.llm.create_chat_completion = late_success
            with self.assertRaisesRegex(TimeoutError, "合作中止"):
                module._调用chat_completion(
                    model.llm,
                    messages=[{"role": "user", "content": "late"}],
                    params={module._MODEL_CALL_DEADLINE_PARAM: time.monotonic() + 0.02},
                )
            self.assertEqual(len(fake_llama.created), 1)
            self.assertIs(module._QwenStorage.model, model)

    def test_abort_callback_cleanup_failure_keeps_strong_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = pathlib.Path(temp_dir)
            llm_dir = models_dir / "LLM"
            llm_dir.mkdir()
            (llm_dir / "callback-guard.gguf").touch()
            module, _fake_llama, _runtime = load_nodes_for_storage_test(models_dir)
            model = module._QwenStorage.load(
                {"model": "callback-guard.gguf", "family": "Qwen3-VL", "think": False}
            )
            model.llm._ctx = types.SimpleNamespace(ctx=object())

            class CleanupFailLowLevel:
                current_callback = None

                @staticmethod
                def ggml_abort_callback(callback=None):
                    return callback

                @classmethod
                def llama_set_abort_callback(cls, _context, callback, _data):
                    if callback is None:
                        raise RuntimeError("cannot clear callback")
                    cls.current_callback = callback

            module._LLAMA_LOW_LEVEL = CleanupFailLowLevel
            result = module._调用chat_completion(
                model.llm,
                messages=[{"role": "user", "content": "guard"}],
                params={},
            )
            self.assertEqual(result["choices"][0]["message"]["content"], "ok")
            guard = getattr(model.llm, "_qwen_te_abort_callback_guard", None)
            self.assertIsNotNone(guard)
            self.assertIs(guard[0], CleanupFailLowLevel.current_callback)
            self.assertTrue(callable(guard[0]))
            self.assertFalse(guard[0](None))
            self.assertTrue(guard[1]["disabled"])

    def test_managed_model_deadline_bounds_wait_for_storage_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = pathlib.Path(temp_dir)
            llm_dir = models_dir / "LLM"
            llm_dir.mkdir()
            (llm_dir / "lock-timeout.gguf").touch()
            module, _fake_llama, _runtime = load_nodes_for_storage_test(models_dir)
            model = module._QwenStorage.load(
                {"model": "lock-timeout.gguf", "family": "Qwen3-VL", "think": False}
            )
            lock_held = threading.Event()
            release_lock = threading.Event()

            def hold_model_lock():
                with module._MODEL_STORAGE_LOCK:
                    lock_held.set()
                    release_lock.wait(2.0)

            holder = threading.Thread(target=hold_model_lock)
            holder.start()
            self.assertTrue(lock_held.wait(1.0))
            started_at = time.monotonic()
            try:
                with self.assertRaisesRegex(TimeoutError, "等待可用推理槽位"):
                    module._调用chat_completion(
                        model.llm,
                        messages=[{"role": "user", "content": "wait"}],
                        params={module._MODEL_CALL_DEADLINE_PARAM: time.monotonic() + 0.04},
                    )
            finally:
                release_lock.set()
                holder.join(timeout=2.0)

            self.assertLess(time.monotonic() - started_at, 0.5)
            self.assertFalse(holder.is_alive())

    def test_hot_reload_replaces_legacy_non_reentrant_model_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = pathlib.Path(temp_dir)
            llm_dir = models_dir / "LLM"
            llm_dir.mkdir()
            (llm_dir / "legacy-lock.gguf").touch()
            _first_module, _fake_llama, runtime = load_nodes_for_storage_test(models_dir)
            legacy_lock = threading.Lock()
            runtime["model_management"]._qwen_te_model_storage_lock = legacy_lock
            lock_held = threading.Event()
            release_lock = threading.Event()

            def hold_legacy_lock():
                with legacy_lock:
                    lock_held.set()
                    release_lock.wait(10.0)

            holder = threading.Thread(target=hold_legacy_lock)
            holder.start()
            self.assertTrue(lock_held.wait(1.0))

            def release_legacy_lock():
                time.sleep(0.08)
                release_lock.set()

            releaser = threading.Thread(target=release_legacy_lock)
            releaser.start()

            started_at = time.monotonic()
            module, _, _ = load_nodes_for_storage_test(models_dir, runtime=runtime)
            elapsed = time.monotonic() - started_at
            self.assertIsNot(module._MODEL_STORAGE_LOCK, legacy_lock)
            self.assertTrue(module._MODEL_STORAGE_LOCK._qwen_te_reentrant_lock_adapter)
            self.assertIs(module._MODEL_STORAGE_LOCK._lock, legacy_lock)
            self.assertEqual(runtime["model_management"]._qwen_te_model_storage_lock_version, 2)
            holder.join(timeout=2.0)
            releaser.join(timeout=2.0)
            self.assertFalse(holder.is_alive())
            self.assertFalse(releaser.is_alive())
            self.assertGreaterEqual(elapsed, 0.05)
            model = module._QwenStorage.load(
                {"model": "legacy-lock.gguf", "family": "Qwen3-VL", "think": False}
            )
            self.assertIsNotNone(model.llm)

    def test_managed_model_rejects_streaming_before_inference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = pathlib.Path(temp_dir)
            llm_dir = models_dir / "LLM"
            llm_dir.mkdir()
            (llm_dir / "no-stream.gguf").touch()
            module, _fake_llama, _runtime = load_nodes_for_storage_test(models_dir)
            model = module._QwenStorage.load(
                {"model": "no-stream.gguf", "family": "Qwen3-VL", "think": False}
            )
            with self.assertRaisesRegex(ValueError, "不支持 stream=True"):
                module._调用chat_completion(
                    model.llm,
                    messages=[{"role": "user", "content": "stream"}],
                    params={"stream": True},
                )
            self.assertEqual(model.llm.reset_count, 0)

    def test_plugin_init_survives_missing_quality_audit_dependencies(self) -> None:
        module = load_plugin_init_for_integration_test(failing_imports={"cv2", "rapidocr_onnxruntime"})
        self.assertIn("QwenTE_StagePromptGenerator", module.NODE_CLASS_MAPPINGS)

    def test_frontend_prompt_library_payload_includes_backend_nsfw_catalog(self) -> None:
        module = load_plugin_init_for_integration_test(failing_imports={"cv2", "rapidocr_onnxruntime"})
        payload = module._build_frontend_prompt_library_payload()
        self.assertIn("nsfw_workspace_catalog", payload)
        self.assertFalse(payload["nsfw_workspace_catalog"]["defaults"]["enabled"])

    def test_stage_output_route_forwards_cache_namespace(self) -> None:
        module = load_plugin_init_for_integration_test(failing_imports={"cv2", "rapidocr_onnxruntime"})
        handlers: dict[tuple[str, str], object] = {}

        class FakeRoutes:
            def get(self, path):
                return lambda handler: handlers.setdefault(("GET", path), handler)

            def post(self, path):
                return lambda handler: handlers.setdefault(("POST", path), handler)

        prompt_server = types.SimpleNamespace(routes=FakeRoutes())
        module._get_prompt_server_class = lambda: types.SimpleNamespace(instance=prompt_server)
        captured: dict[str, object] = {}
        caller_thread_id = threading.get_ident()

        def load_cache(node_id, cache_namespace=None):
            captured["node_id"] = node_id
            captured["cache_namespace"] = cache_namespace
            captured["thread_id"] = threading.get_ident()
            return {"status": "done"}

        module.获取阶段节点输出缓存 = load_cache
        self.assertTrue(module._register_tag_routes())
        handler = handlers[("GET", "/qwen_te/stage_output/{node_id}")]
        request = types.SimpleNamespace(
            match_info={"node_id": "7"},
            query={"namespace": "node-route-cache-0001"},
        )
        response = module.asyncio.run(handler(request))
        self.assertEqual(response.status, 200)
        self.assertEqual(captured["node_id"], "7")
        self.assertEqual(captured["cache_namespace"], "node-route-cache-0001")
        self.assertNotEqual(captured["thread_id"], caller_thread_id)

    def test_read_and_preview_routes_offload_sync_work(self) -> None:
        source = (ROOT / "__init__.py").read_text(encoding="utf-8")
        for call in (
            "await _run_tag_library_transaction(_build_frontend_prompt_library_payload)",
            "await _run_thread_until_done(构建运行时随机预览状态, data)",
            "await _run_thread_until_done(构建状态可视化预览, data)",
            "await _run_thread_until_done(\n                    collect_recent_output_images,",
        ):
            self.assertIn(call, source)

    def test_tag_suggest_route_offloads_recommendation_to_worker_thread(self) -> None:
        module = load_plugin_init_for_integration_test(failing_imports={"cv2", "rapidocr_onnxruntime"})
        handlers: dict[tuple[str, str], object] = {}

        class FakeRoutes:
            def get(self, path):
                return lambda handler: handlers.setdefault(("GET", path), handler)

            def post(self, path):
                return lambda handler: handlers.setdefault(("POST", path), handler)

        class FakeRequest:
            async def json(self):
                return {"tag": "银发，柔光"}

        prompt_server = types.SimpleNamespace(routes=FakeRoutes())
        module._get_prompt_server_class = lambda: types.SimpleNamespace(instance=prompt_server)
        worker_thread_ids: list[int] = []

        def recommend(tag, *, max_items):
            worker_thread_ids.append(threading.get_ident())
            return {
                "summary": {"total": 2, "matched": 2, "exists": 2, "hit_score": 1998},
                "tags": [{"tag": "银发"}, {"tag": "柔光"}],
            }

        module.推荐自定义标签归类 = recommend
        self.assertTrue(module._register_tag_routes())
        handler = handlers[("POST", "/qwen_te/tag_library/suggest")]
        event_loop_thread_id = threading.get_ident()
        response = module.asyncio.run(handler(FakeRequest()))

        self.assertEqual(response.status, 200)
        self.assertEqual(len(worker_thread_ids), 1)
        self.assertNotEqual(worker_thread_ids[0], event_loop_thread_id)
        self.assertEqual(json.loads(response.text)["detail"]["summary"]["total"], 2)

    def test_tag_write_routes_offload_atomic_mutation_and_snapshot(self) -> None:
        module = load_plugin_init_for_integration_test(failing_imports={"cv2", "rapidocr_onnxruntime"})
        handlers: dict[tuple[str, str], object] = {}

        class FakeRoutes:
            def get(self, path):
                return lambda handler: handlers.setdefault(("GET", path), handler)

            def post(self, path):
                return lambda handler: handlers.setdefault(("POST", path), handler)

        class FakeRequest:
            async def json(self):
                return {"category": "主体", "section": "测试", "tag": "测试标签"}

        prompt_server = types.SimpleNamespace(routes=FakeRoutes())
        module._get_prompt_server_class = lambda: types.SimpleNamespace(instance=prompt_server)
        worker_state = threading.local()
        mutation_threads: dict[str, int] = {}
        snapshot_threads: dict[str, int] = {}

        def record_mutation(operation: str):
            worker_state.operation = operation
            mutation_threads[operation] = threading.get_ident()

        def add_tag(*_args):
            record_mutation("add")
            return True, "added"

        def add_tags_batch(*_args):
            record_mutation("add_batch")
            return True, "added batch", {"added": ["测试标签"], "skipped": [], "errors": []}

        def delete_tag(*_args):
            record_mutation("delete")
            return True, "deleted"

        def build_library():
            operation = worker_state.operation
            snapshot_threads[operation] = threading.get_ident()
            return {"operation": operation}

        module.添加自定义标签 = add_tag
        module.批量添加自定义标签 = add_tags_batch
        module.删除自定义标签 = delete_tag
        module._build_frontend_prompt_library_payload = build_library
        self.assertTrue(module._register_tag_routes())

        async def invoke_routes():
            event_loop_thread = threading.get_ident()
            responses = []
            for path in (
                "/qwen_te/tag_library/add",
                "/qwen_te/tag_library/add_batch",
                "/qwen_te/tag_library/delete",
            ):
                responses.append(await handlers[("POST", path)](FakeRequest()))
            return event_loop_thread, responses

        event_loop_thread_id, responses = module.asyncio.run(invoke_routes())
        self.assertTrue(all(response.status == 200 for response in responses))
        self.assertEqual(set(mutation_threads), {"add", "add_batch", "delete"})
        self.assertEqual(mutation_threads, snapshot_threads)
        self.assertTrue(all(thread_id != event_loop_thread_id for thread_id in mutation_threads.values()))

    def test_tag_library_transaction_holds_lock_through_cancelled_worker_and_get(self) -> None:
        module = load_plugin_init_for_integration_test(failing_imports={"cv2", "rapidocr_onnxruntime"})
        handlers: dict[tuple[str, str], object] = {}

        class FakeRoutes:
            def get(self, path):
                return lambda handler: handlers.setdefault(("GET", path), handler)

            def post(self, path):
                return lambda handler: handlers.setdefault(("POST", path), handler)

        class FakeRequest:
            async def json(self):
                return {"category": "主体", "section": "测试", "tag": "测试标签"}

        prompt_server = types.SimpleNamespace(routes=FakeRoutes())
        module._get_prompt_server_class = lambda: types.SimpleNamespace(instance=prompt_server)
        add_started = threading.Event()
        delete_started = threading.Event()
        release_add = threading.Event()
        state_lock = threading.Lock()
        state = {"version": 0}
        snapshot_versions: list[int] = []

        def add_tag(*_args):
            add_started.set()
            if not release_add.wait(2.0):
                raise RuntimeError("test add release timeout")
            with state_lock:
                state["version"] = 1
            return True, "added"

        def delete_tag(*_args):
            delete_started.set()
            with state_lock:
                state["version"] = 2
            return True, "deleted"

        def build_library():
            with state_lock:
                version = state["version"]
                snapshot_versions.append(version)
            return {"version": version}

        module.添加自定义标签 = add_tag
        module.删除自定义标签 = delete_tag
        module._build_frontend_prompt_library_payload = build_library
        self.assertTrue(module._register_tag_routes())

        async def wait_for_thread_event(event: threading.Event) -> None:
            for _ in range(200):
                if event.is_set():
                    return
                await module.asyncio.sleep(0.005)
            raise AssertionError("worker event did not start")

        async def exercise_cancel_and_queue():
            add_task = module.asyncio.create_task(
                handlers[("POST", "/qwen_te/tag_library/add")](FakeRequest())
            )
            await wait_for_thread_event(add_started)
            add_task.cancel()
            delete_task = module.asyncio.create_task(
                handlers[("POST", "/qwen_te/tag_library/delete")](FakeRequest())
            )
            get_task = module.asyncio.create_task(
                handlers[("GET", "/qwen_te/prompt_library")](types.SimpleNamespace())
            )
            await module.asyncio.sleep(0.05)
            self.assertFalse(delete_started.is_set())
            self.assertEqual(snapshot_versions, [])

            release_add.set()
            with self.assertRaises(module.asyncio.CancelledError):
                await add_task
            return await delete_task, await get_task

        delete_response, get_response = module.asyncio.run(exercise_cancel_and_queue())
        self.assertTrue(delete_started.is_set())
        self.assertEqual(snapshot_versions, [1, 2, 2])
        self.assertEqual(json.loads(delete_response.text)["library"]["version"], 2)
        self.assertEqual(json.loads(get_response.text)["version"], 2)

    def test_quality_audit_fallback_functions_do_not_capture_cleared_exception(self) -> None:
        module = load_plugin_init_for_integration_test(failing_imports={"cv2", "rapidocr_onnxruntime"})
        result = module.audit_images([])
        markdown = module.build_quality_markdown(result)
        self.assertTrue(result["dependency_missing"])
        self.assertIn("质检功能依赖缺失", markdown)

    def test_quality_audit_request_rejects_all_client_image_paths(self) -> None:
        module = load_plugin_init_for_integration_test(failing_imports={"cv2", "rapidocr_onnxruntime"})
        forbidden_payloads = [
            {"image_paths": [r"C:\Users\Public\secret.png"]},
            {"image_paths": [r"\\server\share\secret.png"]},
            {"image_paths": ["../../secret.png"]},
            {"image_paths": []},
            {"image_paths": None, "history_prompt_id": "safe-history-id"},
        ]
        for payload in forbidden_payloads:
            with self.subTest(payload=payload):
                prompt_ids, error = module._parse_quality_audit_source_request(payload)
                self.assertEqual(prompt_ids, [])
                self.assertIn("不接受客户端 image_paths", error)

    def test_quality_audit_request_allows_only_history_ids_or_recent_fallback(self) -> None:
        module = load_plugin_init_for_integration_test(failing_imports={"cv2", "rapidocr_onnxruntime"})
        prompt_ids, error = module._parse_quality_audit_source_request(
            {
                "history_prompt_ids": [" first ", "first", "second", ""],
                "history_prompt_id": "latest",
            }
        )
        self.assertIsNone(error)
        self.assertEqual(prompt_ids, ["latest", "first", "second"])
        self.assertEqual(module._parse_quality_audit_source_request({}), ([], None))

    def test_plugin_init_registers_only_embedded_stage_prompt_node(self) -> None:
        module = load_plugin_init_for_integration_test(
            failing_imports={"cv2", "rapidocr_onnxruntime", "llama_cpp", "numpy", "PIL", "comfy.model_management"}
        )
        self.assertEqual(set(module.NODE_CLASS_MAPPINGS.keys()), {"QwenTE_StagePromptGenerator"})
        self.assertEqual(set(module.NODE_DISPLAY_NAME_MAPPINGS.keys()), {"QwenTE_StagePromptGenerator"})
        self.assertEqual(module.NODE_DISPLAY_NAME_MAPPINGS["QwenTE_StagePromptGenerator"], "真男人提示词阶段生成器")

    def test_stage_generator_loads_without_model_node_dependencies(self) -> None:
        module = load_stage_prompt_generator_for_integration_test(nodes_available=False)
        node_class = getattr(module, "QwenTE阶段式提示词生成器")
        input_types = node_class.INPUT_TYPES()
        self.assertIn("required", input_types)
        self.assertIn("模板风格", input_types["required"])
        self.assertIsNone(module._规范化随机种子("-1"))
        self.assertEqual(module._清洗think块文本("<think>skip</think>正向提示词"), "正向提示词")

    def test_dependency_installer_builds_default_install_commands(self) -> None:
        commands = dependency_installer.build_install_commands(include_llama=True, upgrade_pip=False)
        rendered = [" ".join(command) for _label, command, _required in commands]
        self.assertTrue(any("opencv-python" in command and "rapidocr-onnxruntime" in command for command in rendered))
        self.assertTrue(any("llama-cpp-python" in command for command in rendered))

    def test_dependency_installer_can_skip_llama_group(self) -> None:
        commands = dependency_installer.build_install_commands(include_llama=False, upgrade_pip=False)
        rendered = [" ".join(command) for _label, command, _required in commands]
        self.assertFalse(any("llama-cpp-python" in command for command in rendered))

    def test_stage_prompt_skill_engine_exposes_core_skills(self) -> None:
        skill_names = {item["name"] for item in skills.list_stage_prompt_skills()}
        self.assertIn("prompt_noise_filter", skill_names)
        self.assertIn("custom_tag_router", skill_names)
        self.assertIn("default_person_full_body_guard", skill_names)
        self.assertIn("global_detail_anchor_guard", skill_names)
        self.assertIn("semantic_repetition_compactor", skill_names)
        self.assertIn("global_nonlocking_diversity_director", skill_names)
        self.assertIn("prompt_craft_source_guard", skill_names)
        self.assertIn("runtime_random_style_isolation", skill_names)
        self.assertIn("adult_mature_scene_consistency", skill_names)
        self.assertIn("nsfw_workspace_strategy", skill_names)
        self.assertIn("adult_mature_group_compactor", skill_names)

    def test_global_nonlocking_diversity_skill_publishes_strategy_without_changing_tags(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["真实感"],
                "服装造型": ["长款大衣"],
                "场景背景": [],
                "动作姿态": [],
                "光影氛围": ["柔光"],
                "构图视角": ["全景全身"],
            }
        )
        custom_tags = ["雨夜站台"]
        settings = {"运行时随机标签": True, "运行时随机模式": "重写主体与场景", "智能文本匹配": True}
        notes: list[str] = []
        before = collect_all_tags(selected, custom_tags)
        skills._apply_global_nonlocking_diversity_director(
            selected=selected,
            custom_tags=custom_tags,
            settings=settings,
            notes=notes,
            collect_all_tags=collect_all_tags,
        )
        after = collect_all_tags(selected, custom_tags)
        self.assertEqual(before, after)
        self.assertIn("Skill动态变化策略", settings)
        self.assertIn("标签作为素材锚点而非固定模板", settings["Skill动态变化策略"])
        self.assertIn("优先变化未明确锁定维度", settings["Skill动态变化策略"])
        self.assertTrue(any("Skill动态变化" in note for note in notes))

    def test_nsfw_workspace_skill_adds_stable_generation_anchors(self) -> None:
        selected = OrderedDict({"主体": [], "成人向表达": ["内衣风"], "构图视角": [], "技术画质": []})
        custom_tags = ["阴道", "成人动作", "用户保留词"]
        settings = {"模板风格": "真实感", "标签反推模式": "成人向成熟", "NSFW工作台启用": True}
        notes: list[str] = []

        def append_for_test(next_selected: OrderedDict[str, list[str]], next_custom: list[str], tag: str) -> None:
            group_map = {"成年女性": "主体", "全景全身": "构图视角", "人物完整入镜": "构图视角", "高细节": "技术画质"}
            group = group_map.get(tag)
            if group and group in next_selected and tag not in next_selected[group]:
                next_selected[group].append(tag)
                return
            append_tag_to_state(next_selected, next_custom, tag)

        skills.apply_stage_prompt_skills(
            selected,
            custom_tags,
            settings,
            notes,
            phase="final_normalize",
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_for_test,
            uniq=uniq,
            context={
                "adult_mature_subject_anchors": {"成年女性", "成年男性"},
                "adult_mature_default_subject_anchor": "成年女性",
                "adult_mature_stable_shot_tag": "全景全身",
                "default_quality_anchor_tag": "高细节",
                "quality_anchor_tags": {"高细节"},
                "person_shot_tags": {"全景全身", "全身", "中景", "近景"},
            },
        )

        all_tags = collect_all_tags(selected, custom_tags)
        self.assertIn("成年女性", selected["主体"])
        self.assertIn("全景全身", selected["构图视角"])
        self.assertIn("人物完整入镜", selected["构图视角"])
        self.assertIn("高细节", selected["技术画质"])
        self.assertIn("阴道", all_tags)
        self.assertIn("成人动作", all_tags)
        self.assertIn("用户保留词", all_tags)
        self.assertIn("工作台启用", settings["NSFW策略解析结果"])
        self.assertTrue(any("NSFW Skill策略" in note for note in notes))

    def test_advanced_adult_reverse_mode_enables_global_nsfw_strategy(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()

        class DummyModel:
            pass

        original_build_json = module._build_json_payload_impl
        original_update_history = module._update_history
        captured: dict[str, object] = {}

        def fake_json_payload(**kwargs):
            captured.update(kwargs)
            return original_build_json(**kwargs)

        module._build_json_payload_impl = fake_json_payload
        module._maybe_model_refine_batch_impl = lambda model, prompt_list, settings, **kwargs: list(prompt_list)
        module._update_history = lambda *args, **kwargs: []
        try:
            result = module._run_stage(
                DummyModel(),
                **{
                    "模板风格": "自动",
                    "主体类型": "自动",
                    "标签反推模式": "成人向成熟",
                    "主体标签1": "",
                    "成人向表达标签1": "内衣风",
                    "生成数量": 1,
                    "提示词语言": "纯中文",
                    "详细度": "标准",
                    "输出模式": "完整结果",
                    "运行时随机标签": False,
                    "模型来源": "仅Skill",
                },
            )
        finally:
            module._build_json_payload_impl = original_build_json
            module._update_history = original_update_history

        payload = json.loads(result[3])
        settings = captured["settings"]
        self.assertTrue(settings["NSFW策略启用"])
        self.assertEqual(settings["NSFW策略来源"], "高级标签反推")
        self.assertFalse(settings.get("NSFW工作台启用", False))
        self.assertEqual(settings["主体类型"], "人物角色")
        self.assertTrue(settings["优先柔和肤质"])
        self.assertTrue(settings["抑制文字伪影"])
        self.assertIn("高级标签反推", payload["selected_tags_text"])
        self.assertNotIn("nsfw_workspace", payload)

    def test_nsfw_strategy_skips_non_person_subjects_even_when_adult_mode_selected(self) -> None:
        selected = OrderedDict({"主体": [], "构图视角": [], "技术画质": []})
        custom_tags: list[str] = []
        settings = {"模板风格": "CG感", "主体类型": "非人物主体", "标签反推模式": "成人向成熟", "NSFW策略启用": True}
        notes: list[str] = []

        skills.apply_stage_prompt_skills(
            selected,
            custom_tags,
            settings,
            notes,
            phase="final_normalize",
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "adult_mature_subject_anchors": {"成年女性", "成年男性"},
                "adult_mature_default_subject_anchor": "成年女性",
                "adult_mature_stable_shot_tag": "全景全身",
                "default_quality_anchor_tag": "高细节",
            },
        )

        all_tags = collect_all_tags(selected, custom_tags)
        self.assertNotIn("成年女性", all_tags)
        self.assertNotIn("全景全身", all_tags)
        self.assertNotIn("NSFW策略解析结果", settings)

    def test_auto_subject_resolves_non_person_before_adult_skill_anchors(self) -> None:
        selected = OrderedDict({"主体": ["机甲"], "构图视角": [], "技术画质": [], "成人向表达": ["性感"]})
        custom_tags: list[str] = []
        settings = {"模板风格": "CG感", "主体类型": "自动", "标签反推模式": "成人向成熟", "NSFW策略启用": True}
        notes: list[str] = []
        context = {
            "non_person_subject_tags": {"机甲", "机器人", "飞船"},
            "human_identity_tags": {"成年女性", "成年男性"},
            "adult_mature_subject_anchors": {"成年女性", "成年男性", "成熟", "性感"},
            "adult_mature_default_subject_anchor": "成年女性",
            "adult_mature_stable_shot_tag": "全景全身",
            "default_quality_anchor_tag": "高细节",
        }

        for phase in ("early_normalize", "final_normalize"):
            skills.apply_stage_prompt_skills(
                selected,
                custom_tags,
                settings,
                notes,
                phase=phase,
                collect_all_tags=collect_all_tags,
                remove_tag_from_state=remove_tag_from_state,
                append_tag_to_state=append_tag_to_state,
                uniq=uniq,
                context=context,
            )

        all_tags = collect_all_tags(selected, custom_tags)
        self.assertEqual(settings["主体类型"], "非人物主体")
        self.assertIn("机甲", all_tags)
        self.assertNotIn("成年女性", all_tags)
        self.assertNotIn("全景全身", all_tags)
        self.assertTrue(any("自动模式检测到明确非人物主体" in note for note in notes))

    def test_auto_non_person_adult_mode_stays_non_person_through_full_pipeline(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module._run_stage(
            None,
            **{
                "unique_id": "auto-non-person-adult",
                "主体标签1": "机甲",
                "主体类型": "自动",
                "标签反推模式": "成人向成熟",
                "模板风格": "CG感",
                "生成数量": 1,
                "提示词语言": "纯中文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 1,
            },
        )
        payload = json.loads(result[3])
        self.assertIn("机甲", payload["selected_tags_flat"])
        self.assertNotIn("成年女性", payload["selected_tags_flat"])
        self.assertEqual(payload["subject_type"], "非人物主体")

    def test_tag_library_enriches_practical_hair_tags(self) -> None:
        library = tag_library.当前标签库()
        subject = library["主体"]
        self.assertIn("发型长度", subject)
        self.assertIn("发型轮廓", subject)
        self.assertIn("刘海与分线", subject)
        self.assertIn("发色", subject)
        self.assertIn("短发", subject["发型长度"])
        self.assertIn("长发", subject["发型长度"])
        self.assertIn("锁骨发", subject["发型长度"])
        self.assertIn("双马尾", subject["发型轮廓"])
        self.assertIn("法式刘海", subject["刘海与分线"])
        self.assertIn("红发", subject["发色"])
        self.assertIn("波波头", subject["发型轮廓"])
        self.assertIn("空气刘海", subject["刘海与分线"])
        self.assertIn("黑发", subject["发色"])

    def test_tag_library_flattened_snapshot_is_reused_and_invalidated_after_save(self) -> None:
        original_path = tag_library._自定义标签库文件路径
        try:
            with tempfile.TemporaryDirectory() as temporary_dir:
                tag_library._自定义标签库文件路径 = pathlib.Path(temporary_dir) / "custom.json"
                tag_library._自定义标签库文件路径.write_text("{}", encoding="utf-8")
                tag_library._清空标签库缓存()
                original_reader = tag_library._读取自定义标签库文件
                with mock.patch.object(tag_library, "_读取自定义标签库文件", wraps=original_reader) as reader:
                    for _ in range(50):
                        self.assertIn("成年女性", tag_library.展平标签分类("主体"))
                    self.assertEqual(reader.call_count, 1)

                    ok, _message = tag_library.添加自定义标签("主体", "缓存测试", "缓存新增标签")
                    self.assertTrue(ok)
                    self.assertIn("缓存新增标签", tag_library.展平标签分类("主体"))
                    self.assertEqual(reader.call_count, 1)
        finally:
            tag_library._自定义标签库文件路径 = original_path
            tag_library._清空标签库缓存()

    def test_tag_library_recommendation_index_matches_legacy_results_and_order(self) -> None:
        def legacy_recommend(tag: str, *, max_items: int = 12) -> dict[str, object]:
            tags = tag_library.解析标签文本列表(tag, max_items=max_items)
            current_library = tag_library.当前标签库()
            results: list[dict[str, object]] = []
            total_hits = 0
            for item in tags:
                best_group = "画面风格"
                best_section = tag_library._默认自定义小类(best_group)
                best_score = -1
                exists = False
                for group_name, sections in current_library.items():
                    for section_name, values in sections.items():
                        value_keys = {tag_library._标签规范键(value) for value in values}
                        item_key = tag_library._标签规范键(item)
                        if item_key in value_keys:
                            best_group = group_name
                            best_section = section_name
                            best_score = 999
                            exists = True
                            break
                        score = sum(1 for value in values if tag_library._命中关键词(item, value))
                        if score > best_score:
                            best_group = group_name
                            best_section = section_name
                            best_score = score
                    if exists:
                        break
                if best_score > 0:
                    total_hits += best_score
                results.append(
                    {
                        "tag": item,
                        "recommended_group": best_group,
                        "recommended_section": best_section,
                        "exists": exists,
                        "score": best_score,
                    }
                )
            return {
                "summary": {
                    "total": len(results),
                    "matched": sum(1 for item in results if int(item["score"]) > 0),
                    "exists": sum(1 for item in results if bool(item["exists"])),
                    "hit_score": total_hits,
                },
                "tags": results,
            }

        source = "银发，柔和逆光，ＣＧ感，完全不存在的测试标签，银发"
        expected = legacy_recommend(source, max_items=12)
        actual = tag_library.推荐自定义标签归类(source, max_items=12)
        self.assertEqual(actual, expected)
        self.assertEqual(
            [item["tag"] for item in actual["tags"]],
            ["银发", "柔和逆光", "CG感", "完全不存在的测试标签"],
        )

    def test_tag_library_recommendation_normalizes_each_input_constant_times(self) -> None:
        tag_library._当前标签推荐索引()
        original_normalizer = tag_library._标签规范键
        with mock.patch.object(tag_library, "_标签规范键", wraps=original_normalizer) as normalized_key:
            detail = tag_library.推荐自定义标签归类(
                "银发，柔光，废弃教堂，未知测试标签",
                max_items=12,
            )
        self.assertEqual(len(detail["tags"]), 4)
        self.assertLessEqual(normalized_key.call_count, len(detail["tags"]) * 2)

    def test_tag_library_concurrent_updates_remain_valid_and_atomic(self) -> None:
        original_path = tag_library._自定义标签库文件路径
        try:
            with tempfile.TemporaryDirectory() as temporary_dir:
                target = pathlib.Path(temporary_dir) / "custom.json"
                target.write_text("{}", encoding="utf-8")
                tag_library._自定义标签库文件路径 = target
                tag_library._清空标签库缓存()
                errors: list[str] = []
                results: list[tuple[bool, str]] = []

                def add_tag(index: int) -> None:
                    try:
                        results.append(tag_library.添加自定义标签("主体", "并发测试", f"tag-{index}"))
                    except Exception as exc:
                        errors.append(f"{type(exc).__name__}: {exc}")

                threads = [threading.Thread(target=add_tag, args=(index,)) for index in range(16)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=10)

                self.assertFalse(errors)
                self.assertEqual(sum(1 for ok, _message in results if ok), 16)
                payload = json.loads(target.read_text(encoding="utf-8"))
                self.assertEqual(set(payload["主体"]["并发测试"]), {f"tag-{index}" for index in range(16)})
                self.assertFalse(list(target.parent.glob(f"{target.name}.*.tmp")))
        finally:
            tag_library._自定义标签库文件路径 = original_path
            tag_library._清空标签库缓存()

    def test_tag_library_enriches_practical_portrait_controls(self) -> None:
        library = tag_library.当前标签库()
        self.assertIn("清晰下颌线", library["主体"]["脸型轮廓"])
        self.assertIn("高鼻梁", library["主体"]["五官细节"])
        self.assertIn("浅笑", library["主体"]["表情眼神"])
        self.assertIn("裸妆", library["主体"]["妆容特征"])
        self.assertIn("头身比例自然", library["主体"]["体态比例"])
        self.assertIn("长腿", library["主体"]["体态比例"])
        self.assertIn("锁骨明显", library["主体"]["体态比例"])
        self.assertIn("脚部完整入镜", library["构图视角"]["人像构图控制"])
        self.assertIn("自然透视", library["构图视角"]["稳定镜头"])
        self.assertIn("85mm人像镜头", library["构图视角"]["稳定镜头"])
        self.assertIn("浅景深", library["构图视角"]["稳定镜头"])
        self.assertIn("托腮", library["动作姿态"]["手部动作"])
        self.assertIn("轻抚衣角", library["动作姿态"]["手部动作"])
        self.assertIn("看向镜头", library["动作姿态"]["视线互动"])
        self.assertIn("短靴", library["服装造型"]["鞋履"])
        self.assertIn("缎面", library["服装造型"]["面料材质"])
        self.assertIn("收腰剪裁", library["服装造型"]["穿搭结构"])
        self.assertIn("真丝", library["服装造型"]["面料材质"])
        self.assertIn("露肩设计", library["服装造型"]["穿搭结构"])
        self.assertIn("耳环", library["服装造型"]["配饰"])
        self.assertIn("托特包", library["服装造型"]["配饰"])
        self.assertIn("墨镜", library["服装造型"]["配饰"])
        self.assertIn("落地窗", library["场景背景"]["室内锚点"])
        self.assertIn("玻璃橱窗", library["场景背景"]["城市锚点"])
        self.assertIn("相机", library["道具世界观"]["持物道具"])
        self.assertIn("雨伞", library["道具世界观"]["持物道具"])
        self.assertIn("摄影包", library["道具世界观"]["持物道具"])
        self.assertIn("双眼清晰", library["技术画质"]["人像稳定"])
        self.assertIn("景深控制稳定", library["技术画质"]["人像稳定"])
        self.assertIn("35mm胶片摄影", library["画面风格"]["写实风格"])
        self.assertIn("大画幅棚拍", library["画面风格"]["写实风格"])
        self.assertIn("水粉插画", library["画面风格"]["艺术风格"])
        self.assertIn("黄金时刻侧光", library["光影氛围"]["光线类型"])
        self.assertIn("俯视平铺", library["构图视角"]["构图方式"])
        self.assertIn("哑光陶瓷", library["技术画质"]["材质"])

    def test_tag_library_enriches_example_case_scene_and_colossus_tags(self) -> None:
        library = tag_library.当前标签库()
        self.assertIn("城市屋顶纪实", library["画面风格"]["现代摄影"])
        self.assertIn("日落逆光", library["光影氛围"]["光线类型"])
        self.assertIn("晚风感", library["光影氛围"]["自然情绪"])
        self.assertIn("城市天台", library["场景背景"]["城市锚点"])
        self.assertIn("屋顶晾衣架", library["场景背景"]["城市锚点"])
        self.assertIn("有线耳机", library["道具世界观"]["持物道具"])
        self.assertIn("侧脸构图", library["构图视角"]["人像构图控制"])
        self.assertIn("发丝迎风清晰", library["技术画质"]["人像稳定"])
        self.assertIn("山谷圣城", library["场景背景"]["特殊场景"])
        self.assertIn("巨构神殿", library["场景背景"]["特殊场景"])
        self.assertIn("瀑布峡谷", library["场景背景"]["室外场景"])
        self.assertIn("远山雪峰", library["场景背景"]["室外场景"])
        self.assertIn("史诗城市中轴", library["道具世界观"]["世界观元素"])
        self.assertIn("树灵巨像", library["主体"]["非人主体"])
        self.assertIn("工业舱室", library["场景背景"]["现代场景"])
        self.assertIn("巨物压迫近景", library["构图视角"]["景别"])
        self.assertIn("朽木树皮纹理", library["技术画质"]["材质细节"])
        self.assertIn("苔藓附生质感", library["技术画质"]["材质细节"])

    def test_normalizer_skill_filters_control_noise_tags(self) -> None:
        selected = OrderedDict({"主体": ["成年女性", "True"], "画面风格": ["自然写实图像", "低保真"], "技术画质": ["高细节", "标准"]})
        custom_tags = ["书店", "自动", "保留自由补充"]
        settings = {"模板风格": "真实感", "标签反推模式": "自动平衡"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ambiguous_adult_tags": set(),
                "half_body_shot_tags": set(),
                "full_body_motion_conflicts": set(),
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": set(),
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": set(),
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
                "prompt_noise_tags": {"True", "自动", "标准", "低保真"},
            },
        )
        all_tags = collect_all_tags(next_selected, next_custom)
        self.assertIn("成年女性", all_tags)
        self.assertIn("自然写实图像", all_tags)
        self.assertIn("书店", all_tags)
        self.assertNotIn("True", all_tags)
        self.assertNotIn("自动", all_tags)
        self.assertNotIn("标准", all_tags)
        self.assertIn("低保真", all_tags)
        self.assertTrue(any("Skill噪声清理" in note for note in notes))

    def test_normalizer_skill_filters_external_mj_parameter_noise(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["古风电影"],
                "技术画质": ["高细节", "--hd"],
            }
        )
        custom_tags = ["--ar 16:9", "--profile 2q4zxma", "8dc2e476-6225-4bec-bbe2-6a0c93e77871", "雨雾竹林"]
        settings = {"模板风格": "古风", "标签反推模式": "自动平衡"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ambiguous_adult_tags": set(),
                "half_body_shot_tags": set(),
                "full_body_motion_conflicts": set(),
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": set(),
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": set(),
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
            },
        )
        all_tags = collect_all_tags(next_selected, next_custom)
        self.assertIn("成年女性", all_tags)
        self.assertIn("古风电影", all_tags)
        self.assertIn("雨雾竹林", all_tags)
        self.assertNotIn("--hd", all_tags)
        self.assertNotIn("--ar 16:9", all_tags)
        self.assertNotIn("--profile 2q4zxma", all_tags)
        self.assertNotIn("8dc2e476-6225-4bec-bbe2-6a0c93e77871", all_tags)
        self.assertTrue(any("Skill噪声清理" in note for note in notes))
        self.assertTrue(any("Skill构图语义" in note for note in notes))

    def test_normalizer_skill_adds_default_full_body_when_shot_is_missing(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["真实感"], "构图视角": []})
        custom_tags = ["书店"]
        settings = {"模板风格": "真实感", "主体类型": "人物角色", "标签反推模式": "自动平衡"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ambiguous_adult_tags": set(),
                "half_body_shot_tags": set(),
                "full_body_motion_conflicts": set(),
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": set(),
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": set(),
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
                "default_person_shot_tag": "全景全身",
                "person_shot_tags": {"全景全身", "全身", "中景", "近景", "半身"},
            },
        )
        self.assertIn("全景全身", next_selected["构图视角"])
        self.assertIn("书店", next_custom)
        self.assertTrue(any("Skill景别护栏" in note for note in notes))

    def test_normalizer_skill_respects_existing_user_shot(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["真实感"], "构图视角": ["近景"]})
        settings = {"模板风格": "真实感", "主体类型": "人物角色", "标签反推模式": "自动平衡"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            [],
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ambiguous_adult_tags": set(),
                "half_body_shot_tags": set(),
                "full_body_motion_conflicts": set(),
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": set(),
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": set(),
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
                "default_person_shot_tag": "全景全身",
                "person_shot_tags": {"全景全身", "全身", "中景", "近景", "半身"},
            },
        )
        self.assertEqual(next_selected["构图视角"], ["近景"])
        self.assertEqual(next_custom, [])
        self.assertFalse(any("Skill景别护栏" in note for note in notes))

    def test_normalizer_skill_compacts_semantic_repetition(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["自然写实图像", "真实感", "照片级", "杂志编辑摄影"],
                "构图视角": ["全景全身", "人物完整入镜", "全身"],
                "技术画质": ["16K", "8K", "高质量", "高细节", "材质细节丰富"],
            }
        )
        settings = {"模板风格": "真实感", "主体类型": "人物角色", "标签反推模式": "自动平衡"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            [],
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ambiguous_adult_tags": set(),
                "half_body_shot_tags": set(),
                "full_body_motion_conflicts": set(),
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": set(),
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": set(),
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
                "default_person_shot_tag": "全景全身",
                "person_shot_tags": {"全景全身", "人物完整入镜", "全身"},
            },
        )
        self.assertEqual(next_selected["画面风格"], ["真实感", "照片级", "杂志编辑摄影"])
        self.assertEqual(next_selected["构图视角"], ["全景全身", "人物完整入镜"])
        self.assertEqual(next_selected["技术画质"], ["16K", "高质量", "高细节", "材质细节丰富"])
        self.assertEqual(next_custom, [])
        self.assertTrue(any("Skill重复收敛" in note for note in notes))

    def test_normalizer_runtime_random_style_isolation_removes_cross_style_noise(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["真实感", "港风", "照片级", "古风电影剧照", "CG感", "虚幻引擎"],
                "场景背景": ["校园", "古风建筑"],
                "光影氛围": ["柔光"],
            }
        )
        custom_tags = ["神殿", "保留自由补充"]
        settings = {"模板风格": "真实感", "主体类型": "人物角色", "标签反推模式": "自动平衡", "运行时随机标签": True}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ambiguous_adult_tags": set(),
                "half_body_shot_tags": set(),
                "full_body_motion_conflicts": set(),
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": set(),
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": set(),
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
                "style_positive_exclusion_terms": {
                    "真实感": ("神殿", "古风建筑", "虚幻引擎"),
                },
                "runtime_style_isolation_families": {
                    "真实感": {"真实感", "港风", "照片级"},
                    "古风": {"古风电影剧照"},
                    "CG感": {"CG感", "虚幻引擎"},
                },
            },
        )
        all_tags = set(collect_all_tags(next_selected, next_custom))
        self.assertIn("真实感", all_tags)
        self.assertIn("港风", all_tags)
        self.assertIn("照片级", all_tags)
        self.assertIn("校园", all_tags)
        self.assertIn("保留自由补充", all_tags)
        self.assertNotIn("古风电影剧照", all_tags)
        self.assertNotIn("CG感", all_tags)
        self.assertNotIn("虚幻引擎", all_tags)
        self.assertNotIn("古风建筑", all_tags)
        self.assertNotIn("神殿", all_tags)
        self.assertTrue(any("运行随机风格隔离" in note for note in notes))

    def test_normalizer_skill_router_groups_custom_tags_in_general_mode(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "光影氛围": [], "场景背景": [], "技术画质": []})
        custom_tags = ["彩色霓虹光", "蒸汽浴室", "镜面倒影", "保留自由补充"]
        settings = {"模板风格": "真实感", "标签反推模式": "自动平衡"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ambiguous_adult_tags": set(),
                "half_body_shot_tags": set(),
                "full_body_motion_conflicts": set(),
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": set(),
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": set(),
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
                "skill_custom_group_map": {
                    "彩色霓虹光": "光影氛围",
                    "蒸汽浴室": "场景背景",
                    "镜面倒影": "技术画质",
                },
            },
        )
        self.assertEqual(next_selected["光影氛围"], ["彩色霓虹光"])
        self.assertEqual(next_selected["场景背景"], ["蒸汽浴室"])
        self.assertEqual(next_selected["技术画质"], ["镜面倒影"])
        self.assertEqual(next_custom, ["保留自由补充"])
        self.assertTrue(any("Skill标签归位" in note for note in notes))

    def test_normalizer_rewrites_youth_school_tags_in_adult_mode(self) -> None:
        selected = OrderedDict({"主体": ["少女"], "画面风格": [], "场景背景": ["校园"], "服装造型": ["校服"], "构图视角": []})
        custom_tags: list[str] = []
        settings = {"模板风格": "真实感", "标签反推模式": "成人向成熟"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ambiguous_adult_tags": set(),
                "half_body_shot_tags": set(),
                "full_body_motion_conflicts": set(),
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": set(),
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": set(),
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
                "adult_mature_subject_anchors": {"成年女性"},
                "adult_mature_default_subject_anchor": "成年女性",
                "adult_mature_youth_risk_tags": {"少女", "校园", "校服"},
                "adult_mature_youth_safe_map": {
                    "少女": ["成年女性", "青春感"],
                    "校园": ["大学校园"],
                    "校服": ["学院风穿搭"],
                },
            },
        )
        all_tags = collect_all_tags(next_selected, next_custom)
        self.assertIn("成年女性", all_tags)
        self.assertIn("青春感", all_tags)
        self.assertIn("大学校园", all_tags)
        self.assertIn("学院风穿搭", all_tags)
        self.assertNotIn("少女", all_tags)
        self.assertNotIn("校园", all_tags)
        self.assertNotIn("校服", all_tags)
        self.assertTrue(any("安全转译" in note for note in notes))

    def test_normalizer_collapses_conflicting_scenes(self) -> None:
        case = FIXTURES["conflicting_brief_case"]
        selected = OrderedDict((key, list(value)) for key, value in case["selected"].items())
        custom_tags = list(case["custom_tags"])
        settings = {"模板风格": "自动"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": {"双排扣西装", "酒店套房", "雨巷"},
                "humanoid_fantasy_map": {"小精灵": "银发精灵"},
                "human_identity_tags": {"偶像", "成年女性"},
                "sacred_scene_tags": {"废弃教堂"},
                "private_scene_tags": {"酒店套房"},
                "urban_rain_scene_tags": {"雨巷"},
                "ambiguous_adult_tags": {"暧昧"},
                "half_body_shot_tags": {"中景半身"},
                "full_body_motion_conflicts": {"披风扬起", "踮脚回望", "俯身前倾"},
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": {"双排扣西装"},
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": {"双排扣西装"},
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
            },
        )
        all_tags = set(collect_all_tags(next_selected, next_custom))
        expected = case["expected"]
        self.assertEqual(settings["模板风格"], expected["template_style"])
        for tag in [item for item in expected["must_keep"] if item != "中景"]:
            self.assertIn(tag, all_tags)
        self.assertIn("中景半身", all_tags)
        for tag in expected["must_drop"]:
            if tag == "中景半身":
                continue
            self.assertNotIn(tag, all_tags)
        self.assertTrue(any("世界观纠偏" in note for note in notes))
        self.assertTrue(any("场景收敛" in note for note in notes))
        self.assertTrue(any("景别优先" in note for note in notes))

    def test_normalizer_auto_pool_prefers_keeping_half_body_and_drops_conflicting_actions(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "偶像"],
                "场景背景": ["校园"],
                "构图视角": ["中景半身"],
                "动作姿态": ["踮脚回望", "身体前探"],
                "技术画质": ["高细节"],
            }
        )
        custom_tags: list[str] = []
        settings = {"模板风格": "插画感", "随机主题池": "自动"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"偶像", "成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ambiguous_adult_tags": set(),
                "half_body_shot_tags": {"中景半身"},
                "full_body_motion_conflicts": {"披风扬起", "踮脚回望", "俯身前倾", "身体前探"},
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": set(),
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": set(),
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
            },
        )
        all_tags = set(collect_all_tags(next_selected, next_custom))
        self.assertIn("中景半身", all_tags)
        self.assertNotIn("中景", all_tags)
        self.assertFalse({"踮脚回望", "身体前探"} <= all_tags)
        self.assertTrue(any("保留半身镜头" in note or "移除冲突动作" in note for note in notes))

    def test_normalizer_keeps_ancient_mode_from_drifting_to_modern_palace(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "公主"],
                "画面风格": ["古风"],
                "服装造型": ["百褶短裙", "露背礼服"],
                "场景背景": ["宫殿", "回廊", "玻璃幕墙室内"],
            }
        )
        custom_tags = ["办公室"]
        settings = {"模板风格": "古风"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": {"双排扣西装", "酒店套房", "雨巷"},
                "humanoid_fantasy_map": {"小精灵": "银发精灵"},
                "human_identity_tags": {"偶像", "成年女性"},
                "sacred_scene_tags": {"废弃教堂"},
                "private_scene_tags": {"酒店套房"},
                "urban_rain_scene_tags": {"雨巷"},
                "ancient_scene_anchor_tags": {"古风建筑", "月下庭院", "竹林", "古建道场", "中式书房", "月洞门", "水榭", "江南湖畔", "回廊", "宫殿"},
                "ancient_scene_conflict_tags": {"办公室", "玻璃幕墙室内"},
                "ancient_style_clothing_conflicts": {"百褶短裙", "露背礼服"},
                "ambiguous_adult_tags": {"暧昧"},
                "half_body_shot_tags": {"中景半身"},
                "full_body_motion_conflicts": {"披风扬起", "踮脚回望", "俯身前倾"},
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": {"汉服", "百褶短裙", "露背礼服"},
                "ancient_clothing_tags": {"汉服", "宋制", "明制", "魏晋"},
                "modern_formal_clothing_tags": {"双排扣西装"},
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
            },
        )
        all_tags = set(collect_all_tags(next_selected, next_custom))
        self.assertIn("汉服", all_tags)
        self.assertIn("古风建筑", all_tags)
        self.assertNotIn("百褶短裙", all_tags)
        self.assertNotIn("露背礼服", all_tags)
        self.assertNotIn("办公室", all_tags)
        self.assertNotIn("玻璃幕墙室内", all_tags)
        self.assertTrue(any("古风服装补锚" in note for note in notes))
        self.assertTrue(any("古风场景补锚" in note for note in notes))

    def test_normalizer_adult_mature_converges_noisy_reverse_template(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["银白长发", "温柔", "娇小", "中分短发"],
                "成人向表达": ["内衣风", "吊带睡裙", "逆光剪影全裸"],
                "服装造型": ["运动", "百褶短裙", "影棚礼服"],
                "场景背景": ["幻境", "厨房", "雪地"],
                "构图视角": ["前景遮挡", "肩部以上特写", "特写"],
                "动作姿态": ["双人互动", "抬臂撑墙", "倚靠栏杆"],
                "光影氛围": ["玫瑰粉调", "高饱和", "慵懒"],
                "画面风格": ["手办风", "港风", "照片级", "复古未来主义"],
                "道具世界观": ["面具", "武器", "全息界面"],
            }
        )
        custom_tags = [
            "蒸汽浴室",
            "湿滑瓷砖",
            "彩色霓虹光",
            "湿身淋浴",
            "泡沫滑落",
            "露骨器官特写",
            "半裸湿透衬衫",
            "局部身体贴脸前景",
            "紧贴阴道与乳房",
            "赤裸渴望",
            "湿润唇部",
            "masterpiece",
            "best quality",
            "ultra-detailed",
            "high resolution",
            "女人抱着一个男的身体",
        ]
        settings = {"模板风格": "真实感", "标签反推模式": "成人向成熟"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ancient_scene_anchor_tags": set(),
                "ancient_scene_conflict_tags": set(),
                "ancient_style_clothing_conflicts": set(),
                "ambiguous_adult_tags": {"内衣风", "吊带睡裙"},
                "half_body_shot_tags": {"肩部以上特写", "特写"},
                "full_body_motion_conflicts": set(),
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": {"运动", "百褶短裙", "影棚礼服", "吊带睡裙", "半裸湿透衬衫"},
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": {"影棚礼服"},
                "intimate_clothing_tags": {"内衣风", "吊带睡裙", "半裸湿透衬衫"},
                "emotion_cleanup_rules": [],
                "adult_mature_closeup_markers": {"器官特写", "局部身体贴脸", "贴脸前景", "紧贴阴道", "赤裸渴望", "湿润唇部"},
                "adult_mature_direct_noise_markers": {"masterpiece", "best quality", "ultra-detailed", "high resolution", "女人抱着一个男的身体"},
                "adult_mature_subject_anchors": {"成年女性", "成年男性", "成熟"},
                "adult_mature_default_subject_anchor": "成年女性",
                "adult_mature_youth_risk_tags": {"娇小", "学生", "百褶短裙"},
                "adult_mature_scene_families": OrderedDict(
                    {
                        "wet_private": {"蒸汽浴室", "湿滑瓷砖", "彩色霓虹光", "湿身淋浴", "泡沫滑落", "浴室", "浴缸"},
                        "domestic": {"厨房"},
                        "outdoor": {"雪地"},
                        "fantasy": {"幻境"},
                    }
                ),
                "adult_mature_scene_priority": ["wet_private", "private", "studio", "domestic", "outdoor", "fantasy"],
                "adult_mature_intimate_clothing": {"内衣风", "吊带睡裙", "半裸湿透衬衫"},
                "adult_mature_close_shot_risk_tags": {"肩部以上特写", "特写"},
                "adult_mature_stable_shot_tag": "全景全身",
                "adult_mature_action_tags": {"双人互动", "抬臂撑墙", "倚靠栏杆"},
                "adult_mature_action_priority": ["倚靠栏杆", "抬臂撑墙", "双人互动"],
                "hair_conflict_tags": {"银白长发", "中分短发", "短碎发", "长直发"},
                "adult_mature_realistic_style_conflicts": {"手办风", "复古未来主义"},
                "adult_mature_prop_conflicts": {"武器", "全息界面"},
                "adult_mature_custom_group_map": {
                    "蒸汽浴室": "场景背景",
                    "湿滑瓷砖": "场景背景",
                    "湿身淋浴": "场景背景",
                    "泡沫滑落": "场景背景",
                    "彩色霓虹光": "光影氛围",
                },
                "adult_mature_group_limits": {
                    "主体": 4,
                    "画面风格": 3,
                    "成人向表达": 3,
                    "光影氛围": 3,
                    "构图视角": 3,
                    "动作姿态": 1,
                    "场景背景": 3,
                    "道具世界观": 1,
                    "技术画质": 3,
                },
                "adult_mature_group_priorities": {
                    "主体": ["成年女性", "银白长发", "温柔", "丰满"],
                    "画面风格": ["照片级", "港风"],
                    "成人向表达": ["吊带睡裙", "内衣风"],
                    "光影氛围": ["玫瑰粉调", "彩色霓虹光", "高饱和"],
                    "构图视角": ["全景全身"],
                    "动作姿态": ["倚靠栏杆"],
                    "场景背景": ["蒸汽浴室", "湿滑瓷砖", "湿身淋浴"],
                    "道具世界观": ["面具"],
                    "技术画质": [],
                },
            },
        )
        all_tags = set(collect_all_tags(next_selected, next_custom))

        self.assertIn("成年女性", all_tags)
        self.assertIn("银白长发", all_tags)
        self.assertIn("吊带睡裙", all_tags)
        self.assertIn("蒸汽浴室", all_tags)
        self.assertIn("湿滑瓷砖", all_tags)
        self.assertIn("湿身淋浴", all_tags)
        self.assertIn("彩色霓虹光", all_tags)
        self.assertIn("全景全身", all_tags)
        self.assertIn("倚靠栏杆", all_tags)
        self.assertIn("面具", all_tags)
        self.assertIn("照片级", all_tags)
        self.assertEqual(next_selected["场景背景"], ["蒸汽浴室", "湿滑瓷砖", "湿身淋浴"])
        self.assertEqual(next_selected["光影氛围"], ["玫瑰粉调", "彩色霓虹光", "高饱和"])
        self.assertEqual(next_selected["动作姿态"], ["倚靠栏杆"])
        self.assertEqual(next_selected["道具世界观"], ["面具"])
        self.assertNotIn("蒸汽浴室", next_custom)
        self.assertNotIn("湿滑瓷砖", next_custom)
        self.assertNotIn("彩色霓虹光", next_custom)
        self.assertNotIn("娇小", all_tags)
        self.assertNotIn("中分短发", all_tags)
        self.assertNotIn("幻境", all_tags)
        self.assertNotIn("厨房", all_tags)
        self.assertNotIn("雪地", all_tags)
        self.assertNotIn("运动", all_tags)
        self.assertNotIn("百褶短裙", all_tags)
        self.assertNotIn("影棚礼服", all_tags)
        self.assertNotIn("肩部以上特写", all_tags)
        self.assertNotIn("特写", all_tags)
        self.assertNotIn("双人互动", all_tags)
        self.assertNotIn("抬臂撑墙", all_tags)
        self.assertNotIn("露骨器官特写", all_tags)
        self.assertNotIn("局部身体贴脸前景", all_tags)
        self.assertNotIn("紧贴阴道与乳房", all_tags)
        self.assertNotIn("赤裸渴望", all_tags)
        self.assertNotIn("湿润唇部", all_tags)
        self.assertNotIn("masterpiece", all_tags)
        self.assertNotIn("best quality", all_tags)
        self.assertNotIn("ultra-detailed", all_tags)
        self.assertNotIn("high resolution", all_tags)
        self.assertNotIn("女人抱着一个男的身体", all_tags)
        self.assertNotIn("手办风", all_tags)
        self.assertNotIn("复古未来主义", all_tags)
        self.assertNotIn("武器", all_tags)
        self.assertNotIn("全息界面", all_tags)
        self.assertTrue(any("成人向主体补锚" in note for note in notes))
        self.assertTrue(any("成人向分组归位" in note for note in notes))
        self.assertTrue(any("成人向分组精简" in note for note in notes))
        self.assertTrue(any("成人向年龄收敛" in note for note in notes))
        self.assertTrue(any("成人向场景收敛" in note for note in notes))
        self.assertTrue(any("成人向服装收敛" in note for note in notes))
        self.assertTrue(any("成人向局部收敛" in note for note in notes))
        self.assertTrue(any("成人向自定义收敛" in note for note in notes))
        self.assertTrue(any("成人向景别收敛" in note for note in notes))
        self.assertTrue(any("成人向动作收敛" in note for note in notes))
        self.assertTrue(any("成人向风格收敛" in note for note in notes))
        self.assertTrue(any("成人向道具收敛" in note for note in notes))
        self.assertTrue(any("发型收敛" in note for note in notes))

    def test_negative_builder_emits_adult_and_soft_skin_terms(self) -> None:
        selected = OrderedDict({"成人向表达": ["暧昧"], "主体": ["成年女性"]})
        custom_tags = ["无遮挡感"]
        settings = {"模板风格": "真实感", "提示词语言": "纯中文", "优先柔和肤质": True, "抑制文字伪影": True}
        negative = negative_builder.build_negative_prompt_from_state(
            selected,
            custom_tags,
            settings,
            uniq=uniq,
            adult_tag_keywords={"暧昧"},
            adult_low_cover_tags={"无遮挡感"},
            template_negative_zh={"真实感": ["坏手"]},
            template_negative_en={},
            adult_negative_zh=["解剖错误"],
            adult_negative_en=[],
            low_cover_negative_zh=["局部身体透视异常"],
            low_cover_negative_en=[],
            composition_negative_zh=["多人复制"],
            composition_negative_en=[],
            soft_skin_terms=["法令纹过深"],
            text_artifact_terms=["文字", "水印"],
            separator="、",
        )
        self.assertIn("坏手", negative)
        self.assertIn("解剖错误", negative)
        self.assertIn("法令纹过深", negative)
        self.assertIn("文字", negative)

    def test_negative_builder_uses_english_for_mixed_language_mode(self) -> None:
        selected = OrderedDict({"成人向表达": ["暧昧"], "主体": ["成年女性"]})
        settings = {"模板风格": "真实感", "提示词语言": "英文提示词+中文说明", "优先柔和肤质": True, "抑制文字伪影": True}
        negative = negative_builder.build_negative_prompt_from_state(
            selected,
            [],
            settings,
            uniq=uniq,
            adult_tag_keywords={"暧昧"},
            adult_low_cover_tags=set(),
            template_negative_zh={"真实感": ["坏手"]},
            template_negative_en={"真实感": ["bad hands"]},
            adult_negative_zh=["解剖错误"],
            adult_negative_en=["bad anatomy"],
            low_cover_negative_zh=[],
            low_cover_negative_en=[],
            composition_negative_zh=[],
            composition_negative_en=[],
            soft_skin_terms=["法令纹过深"],
            text_artifact_terms=["文字", "水印"],
            separator=", ",
        )
        self.assertIn("bad hands", negative)
        self.assertIn("bad anatomy", negative)
        self.assertIn("overly deep nasolabial folds", negative)
        self.assertIn("text", negative)
        self.assertIn("watermark", negative)
        self.assertNotIn("坏手", negative)
        self.assertNotIn("解剖错误", negative)
        self.assertIsNone(re.search(r"[\u4e00-\u9fff]", negative))

    def test_prompt_builder_appends_extra_requirement(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["真实感"], "构图视角": ["中景"]})
        custom_tags = ["压抑"]
        settings = {
            "模板风格": "真实感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "生成数量": 1,
            "额外要求": "固定单一主场景",
        }
        prompts = prompt_builder.build_prompt_list(
            selected,
            custom_tags,
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        self.assertEqual(len(prompts), 1)
        self.assertIn("固定单一主场景", prompts[0])
        self.assertTrue(prompts[0].startswith("写实摄影"))
        self.assertNotIn("brief", prompts[0].lower())

    def test_prompt_builder_multi_output_adds_distinct_focus(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["真实感"], "构图视角": ["中景"]})
        custom_tags = ["压抑"]
        settings = {
            "模板风格": "真实感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "生成数量": 3,
            "额外要求": "",
        }
        prompts = prompt_builder.build_prompt_list(
            selected,
            custom_tags,
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        self.assertEqual(len(prompts), 3)
        self.assertEqual(len(set(prompts)), 3)
        self.assertIn("全景全身", prompts[0])
        self.assertIn("人物完整入镜", prompts[0])
        self.assertIn("头身比例与姿态优先", prompts[0])
        self.assertIn("全景全身", prompts[1])
        self.assertIn("服装整体轮廓与材质层次优先", prompts[1])
        self.assertIn("全景全身", prompts[2])
        self.assertIn("环境人像", prompts[2])
        self.assertIn("人物与场景比例自然", prompts[2])
        self.assertTrue(any("面部与主体关系清晰" in prompt for prompt in prompts))
        self.assertTrue(any("服装结构与材质层次清晰" in prompt for prompt in prompts))

    def test_prompt_builder_style_mode_isolation_keeps_scene_fixed(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "清冷"],
                "场景背景": ["校园"],
                "构图视角": ["中景半身"],
                "技术画质": ["高细节"],
            }
        )
        custom_tags: list[str] = []
        style_cases = [
            ("真实感", "写实摄影"),
            ("插画感", "高完成度插画"),
            ("CG感", "电影级CG"),
            ("古风", "古风人像"),
            ("神话感", "神话史诗感"),
        ]
        prompts: list[str] = []
        non_leading_fragments: list[list[str]] = []
        for style, cue in style_cases:
            settings = {
                "模板风格": style,
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": False,
                "生成数量": 1,
                "额外要求": "",
            }
            prompt = prompt_builder.build_prompt_list(
                selected,
                custom_tags,
                settings,
                scene_group="",
                identity="",
                style_track="",
                recent_tracks=[],
                uniq=uniq,
                infer_template_style=lambda tags, explicit: explicit,
                infer_subject_type=lambda tags, explicit: explicit,
                infer_output_structure=lambda subject, explicit: explicit,
            )[0]
            prompts.append(prompt)
            fragments = [fragment.strip() for fragment in prompt.split("，")]
            non_leading_fragments.append(fragments[1:])
            self.assertIn("校园", prompt)
            self.assertIn(cue, prompt)
            self.assertIn("成年女性", prompt)
            self.assertIn("东亚", prompt)
            self.assertIn("清冷", prompt)
            self.assertIn("中景半身", prompt)
            self.assertIn("高细节", prompt)
            other_cues = {expected_cue for expected_style, expected_cue in style_cases if expected_style != style}
            for other_cue in other_cues:
                self.assertNotIn(other_cue, prompt)
        self.assertEqual(len(prompts), 5)
        self.assertEqual(len(set(prompts)), 5)
        self.assertEqual(len({tuple(parts) for parts in non_leading_fragments}), 1)

    def test_prompt_builder_auto_template_stays_more_neutral_than_realistic(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "清冷"],
                "场景背景": ["街道"],
                "构图视角": ["中景半身"],
                "技术画质": ["高细节"],
            }
        )
        auto_settings = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 1,
            "额外要求": "",
        }
        realistic_settings = {
            **auto_settings,
            "模板风格": "真实感",
        }
        infer_auto_realistic = lambda tags, explicit: "真实感" if explicit == "自动" else explicit

        auto_prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            auto_settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=infer_auto_realistic,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        realistic_prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            realistic_settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=infer_auto_realistic,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]

        self.assertTrue(auto_prompt.startswith("完整画面"))
        self.assertTrue(realistic_prompt.startswith("杂志编辑摄影"))
        self.assertNotIn("杂志编辑摄影", auto_prompt)
        self.assertNotIn("杂志感", auto_prompt)
        self.assertIn("杂志感", realistic_prompt)

    def test_prompt_builder_runtime_random_english_uses_global_natural_expansion_without_subject_lock(self) -> None:
        selected = OrderedDict(
            {
                "主体": [],
                "画面风格": ["自然写实图像"],
                "构图视角": ["全景全身", "人物完整入镜"],
                "技术画质": ["高细节"],
            }
        )
        settings = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "提示词语言": "纯英文",
            "详细度": "详细",
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: "真实感" if explicit == "自动" else explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]

        self.assertTrue(prompt.startswith("realistic photography"))
        self.assertIn("coherent positive scene description", prompt)
        self.assertIn("full-body", prompt)
        self.assertIn("selected subject", prompt)
        self.assertNotIn("adult woman", prompt)
        self.assertNotIn("Create ", prompt)
        self.assertNotIn("--profile", prompt)

    def test_prompt_builder_runtime_random_chinese_uses_global_natural_expansion(self) -> None:
        selected = OrderedDict(
            {
                "主体": [],
                "画面风格": ["自然写实图像"],
                "场景背景": ["湖畔夕照"],
                "光影氛围": ["柔光"],
                "构图视角": ["全景全身"],
                "技术画质": ["高细节"],
            }
        )
        settings = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "提示词语言": "纯中文",
            "详细度": "详细",
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: "真实感" if explicit == "自动" else explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]

        self.assertTrue(prompt.startswith("写实摄影"))
        self.assertIn("正向画面说明", prompt)
        self.assertIn("湖畔夕照", prompt)
        self.assertIn("全景全身", prompt)
        self.assertIn("主体身份", prompt)
        self.assertNotIn("成年女性", prompt)
        self.assertNotIn("--ar", prompt)

    def test_prompt_builder_auto_rewrite_uses_inferred_cg_lead_before_api_refine(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["冰霜骑士", "沙漏身材"],
                "画面风格": ["虚幻引擎"],
                "场景背景": ["海边", "河岸"],
                "光影氛围": ["晒褪色调", "柔光"],
                "构图视角": ["全景全身", "人物完整入镜"],
                "动作姿态": ["低头凝视", "俯身前倾"],
                "技术画质": ["高细节", "发光裂隙", "磨砂亚克力"],
            }
        )
        settings = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "重写主体与场景",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "提示词语言": "纯中文",
            "详细度": "详细",
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: "CG感" if explicit == "自动" else explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]

        self.assertTrue(prompt.startswith("电影级CG"))
        self.assertNotIn("完整画面", prompt.split("，", 1)[0])
        self.assertIn("虚幻引擎", prompt)
        self.assertIn("冰霜骑士", prompt)
        self.assertIn("海边", prompt)

    def test_prompt_builder_auto_style_does_not_default_to_realistic_when_unselected(self) -> None:
        settings_base = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "详细度": "详细",
            "生成数量": 1,
            "额外要求": "",
        }
        selected = OrderedDict(
            {
                "主体": [],
                "构图视角": ["全景全身"],
                "技术画质": ["高细节"],
            }
        )
        build = lambda language: prompt_builder.build_prompt_list(
            selected,
            [],
            {**settings_base, "提示词语言": language},
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: "自动",
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        zh_prompt = build("纯中文")
        en_prompt = build("纯英文")
        self.assertTrue(zh_prompt.startswith("完整画面"))
        self.assertNotIn("自然写实图像", zh_prompt)
        self.assertTrue(en_prompt.startswith("coherent finished image"))
        self.assertNotIn("natural realistic image", en_prompt)

    def test_prompt_builder_realistic_template_keeps_photography_bias(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "甜美"],
                "场景背景": ["樱花树下"],
                "构图视角": ["近景半身"],
                "技术画质": ["高细节"],
            }
        )
        settings = {
            "模板风格": "真实感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertTrue(prompt.startswith("杂志编辑摄影"))
        self.assertTrue(any(term in prompt for term in ["杂志感", "杂志编辑摄影"]))
        self.assertTrue(any(term in prompt for term in ["时尚成片感更强", "封面肖像"]))
        self.assertNotIn("自然写实图像", prompt)

    def test_prompt_builder_expanded_prompt_collapses_conflicting_visual_tracks(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "公主", "盘发", "清贵"],
                "画面风格": ["古风电影剧照", "欧美风", "照片级"],
                "成人向表达": ["内衣风", "吊带睡裙", "逆光剪影全裸"],
                "服装造型": ["细跟高跟鞋", "宋制"],
                "场景背景": ["化妆台", "宫殿", "回廊", "赛博街区"],
                "道具世界观": ["手机"],
                "光影氛围": ["玫瑰粉调", "高饱和", "慵懒"],
                "构图视角": ["四联画构图", "眼平视角", "轻微俯拍"],
                "动作姿态": ["持刀回身", "托腮", "闭眼感受光线"],
                "技术画质": ["锐利", "空气感奶油肌", "义体金属细节"],
            }
        )
        settings = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": False,
            "提示词语言": "纯中文",
            "详细度": "详细",
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            ["全景全身", "人物完整入镜"],
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: "古风" if "古风电影剧照" in tags else explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("古风电影剧照", prompt)
        self.assertIn("宫殿", prompt)
        self.assertIn("回廊", prompt)
        self.assertNotIn("赛博街区", prompt)
        self.assertNotIn("化妆台、宫殿、回廊、赛博街区", prompt)
        self.assertNotIn("持刀回身、托腮、闭眼感受光线", prompt)
        self.assertLessEqual(prompt.count("欧美风"), 0)
        self.assertNotIn("标签清单；", prompt)

    def test_prompt_builder_english_expanded_prompt_collapses_conflicting_visual_tracks(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "公主", "盘发", "清贵"],
                "画面风格": ["古风电影剧照", "欧美风", "照片级"],
                "成人向表达": ["内衣风", "吊带睡裙", "逆光剪影全裸"],
                "服装造型": ["细跟高跟鞋", "宋制"],
                "场景背景": ["化妆台", "宫殿", "回廊", "赛博街区"],
                "道具世界观": ["手机"],
                "光影氛围": ["玫瑰粉调", "高饱和", "慵懒"],
                "构图视角": ["四联画构图", "眼平视角", "轻微俯拍"],
                "动作姿态": ["持刀回身", "托腮", "闭眼感受光线"],
                "技术画质": ["锐利", "空气感奶油肌", "义体金属细节"],
            }
        )
        settings = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": False,
            "提示词语言": "纯英文",
            "详细度": "详细",
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            ["全景全身", "人物完整入镜"],
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: "古风" if "古风电影剧照" in tags else explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("oriental historical cinematic still", prompt)
        self.assertIn("palace", prompt)
        self.assertIn("covered corridor", prompt)
        self.assertNotIn("cyberpunk street district", prompt)
        self.assertNotIn("vanity table, palace, covered corridor, cyberpunk street district", prompt)
        self.assertNotIn("turning back while holding a blade, chin resting on hand, eyes closed", prompt)
        self.assertNotIn("western editorial style", prompt)
        self.assertNotIn("The prompt should read", prompt)
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in prompt))

    def test_prompt_builder_english_fallback_identity_and_scene_are_translated(self) -> None:
        selected = OrderedDict(
            {
                "主体": [],
                "画面风格": ["古风电影剧照"],
                "场景背景": [],
                "构图视角": ["全景全身"],
                "技术画质": ["高细节"],
            }
        )
        settings = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": False,
            "提示词语言": "纯英文",
            "详细度": "详细",
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="回廊",
            identity="公主",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("princess", prompt)
        self.assertIn("covered corridor", prompt)
        self.assertNotIn("公主", prompt)
        self.assertNotIn("回廊", prompt)
        self.assertNotIn("The prompt should read", prompt)
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in prompt))

    def test_prompt_builder_standard_prompt_does_not_leak_character_sheet_language(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["少女", "侦查机甲", "倒三角身形", "浅笑"],
                "画面风格": ["古风电影剧照", "港风", "照片级"],
                "成人向表达": ["湿身薄纱", "内衣风"],
                "服装造型": ["汉服", "绑带凉鞋", "明制"],
                "场景背景": ["纯色背景", "镜前"],
                "构图视角": ["全景全身", "人物完整入镜", "自然透视"],
                "动作姿态": ["持刀回身", "托腮"],
                "光影氛围": ["诡异", "玫瑰粉调", "高饱和"],
                "道具世界观": ["酒杯", "神谕圣所"],
                "技术画质": ["高细节", "人物完成度高", "清晰"],
            }
        )
        settings = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": False,
            "提示词语言": "纯中文",
            "详细度": "详细",
            "生成数量": 1,
            "额外要求": "",
            "图片反推生成": False,
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: "古风" if "古风电影剧照" in tags else explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        for banned in ("角色设定图", "设定图", "三视图", "正面全身", "侧面全身", "背面全身", "角色卡"):
            self.assertNotIn(banned, prompt)

    def test_prompt_builder_hybrid_ancient_realistic_style_keeps_selected_media_cues(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["少女", "倒三角身形", "浅笑"],
                "画面风格": ["古风电影剧照", "港风", "照片级"],
                "服装造型": ["汉服", "明制"],
                "场景背景": ["纯色背景", "镜前"],
                "构图视角": ["全景全身", "人物完整入镜", "自然透视"],
                "动作姿态": ["持刀回身", "托腮"],
                "光影氛围": ["诡异", "玫瑰粉调", "高饱和"],
                "道具世界观": ["酒杯", "神谕圣所"],
                "技术画质": ["高细节", "人物完成度高", "清晰"],
            }
        )
        settings = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "提示词语言": "纯中文",
            "详细度": "详细",
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="minimal",
            identity="少女",
            style_track="古风人像",
            recent_tracks=["古风人像"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: "古风" if "古风电影剧照" in tags else explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("古风电影剧照", prompt)
        self.assertIn("港风", prompt)
        self.assertIn("照片级", prompt)

    def test_prompt_builder_ancient_prompt_does_not_invent_pink_when_unselected(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "公主", "盘发", "清贵"],
                "画面风格": ["古风电影剧照", "照片级"],
                "服装造型": ["汉服", "明制"],
                "场景背景": ["宫殿", "回廊"],
                "构图视角": ["全景全身", "自然透视"],
                "动作姿态": ["持刀回身"],
                "光影氛围": ["神秘", "高饱和"],
                "技术画质": ["高细节", "清晰"],
            }
        )
        settings = {
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": False,
            "提示词语言": "纯中文",
            "详细度": "详细",
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: "古风" if "古风电影剧照" in tags else explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertNotIn("玫瑰粉调", prompt)
        self.assertNotIn("粉嫩色调", prompt)

    def test_prompt_builder_ancient_and_myth_profiles_preserve_distinct_world_language(self) -> None:
        style_profiles = prompt_builder._RUNTIME_STYLE_VARIANT_PROFILES
        ancient_fragments = " ".join(
            fragment
            for profile in style_profiles["古风"]
            for fragment in profile["extra_fragments"]
        )
        myth_fragments = " ".join(
            fragment
            for profile in style_profiles["神话感"]
            for fragment in profile["extra_fragments"]
        )
        self.assertTrue(any(term in ancient_fragments for term in ["庭院", "回廊", "江湖", "书卷"]))
        self.assertFalse(any(term in ancient_fragments for term in ["祭典", "圣坛", "神性主视觉"]))
        self.assertTrue(any(term in myth_fragments for term in ["祭典", "神性", "圣坛", "云海"]))
        self.assertFalse(any(term in myth_fragments for term in ["江湖", "书卷", "回廊"]))

    def test_prompt_builder_cg_profiles_preserve_industrial_tactical_language(self) -> None:
        style_profiles = prompt_builder._RUNTIME_STYLE_VARIANT_PROFILES
        cg_fragments = " ".join(
            fragment
            for profile in style_profiles["CG感"]
            for fragment in profile["extra_fragments"]
        )
        cg_tags = " ".join(
            tag
            for profile in style_profiles["CG感"]
            for tag in profile["style_tags"]
        )
        cyber_profiles = prompt_builder._resolve_runtime_style_profiles(
            "CG感",
            "赛博雨夜",
            prompt_builder._identity_variant_group("特工"),
        )
        warrior_profiles = prompt_builder._resolve_runtime_style_profiles(
            "CG感",
            "",
            prompt_builder._identity_variant_group("女武士"),
        )
        cyber_fragments = " ".join(
            fragment
            for profile in cyber_profiles
            for fragment in profile["extra_fragments"]
        )
        warrior_fragments = " ".join(
            fragment
            for profile in warrior_profiles
            for fragment in profile["extra_fragments"]
        )
        warrior_tags = " ".join(
            tag
            for profile in warrior_profiles
            for tag in profile["style_tags"]
        )
        self.assertTrue(any(term in cg_fragments for term in ["材质", "空间", "工业"]))
        self.assertTrue(any(term in cg_tags for term in ["PBR", "引擎", "渲染", "概念设计"]))
        self.assertTrue(any(term in cyber_fragments for term in ["任务", "装备", "潜入", "战术"]))
        self.assertTrue(any(term in warrior_fragments for term in ["装甲", "甲胄", "机动", "战斗"]))
        self.assertTrue(any(term in warrior_tags for term in ["战术", "装甲", "女武士设定", "机甲"]))
        self.assertFalse(any(term in cg_fragments for term in ["祭典", "圣坛", "神性", "江湖", "书卷"]))
        self.assertFalse(any(term in cyber_fragments for term in ["宣传图主角", "主视觉成片", "商业CG效果"]))
        self.assertFalse(any(term in warrior_fragments for term in ["宣传海报主角", "高预算女武士角色海报", "高预算CG海报"]))

    def test_prompt_builder_agent_and_warrior_profiles_keep_task_and_frontline_language(self) -> None:
        agent_profiles = prompt_builder._resolve_runtime_style_profiles(
            "CG感",
            "赛博雨夜",
            prompt_builder._identity_variant_group("特工"),
        )
        warrior_profiles = prompt_builder._resolve_runtime_style_profiles(
            "CG感",
            "",
            prompt_builder._identity_variant_group("战士"),
        )
        agent_fragments = " ".join(
            fragment
            for profile in agent_profiles
            for fragment in profile["extra_fragments"]
        )
        warrior_fragments = " ".join(
            fragment
            for profile in warrior_profiles
            for fragment in profile["extra_fragments"]
        )
        self.assertIn("人物更像潜入任务主视觉主角", agent_fragments)
        self.assertIn("任务紧张感更强", agent_fragments)
        self.assertIn("战斗定位更明确", warrior_fragments)
        self.assertIn("角色更像战术出击镜头中的前线主角", warrior_fragments)
        self.assertFalse(any(term in agent_fragments for term in ["花房", "向日葵", "甜美", "神女"]))
        self.assertFalse(any(term in warrior_fragments for term in ["园林", "宫殿", "书卷", "糖水片"]))

    def test_prompt_builder_agent_prompt_merges_track_context_into_identity_override(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "特工", "冷艳"],
                "画面风格": ["CG感"],
                "场景背景": ["未来都市"],
                "构图视角": ["中景半身"],
                "技术画质": ["高细节", "8K"],
            }
        )
        settings = {
            "模板风格": "CG感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            ["雨夜", "装备材质", "湿地面反射"],
            settings,
            scene_group="city",
            identity="特工",
            style_track="赛博雨夜",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("通讯器与潜入工具更具体", prompt)
        self.assertTrue(any(term in prompt for term in ["霓虹雨巷", "湿地面反射与装备高光反馈", "狭窄通道压迫感"]))

    def test_prompt_builder_warrior_single_output_keeps_frontline_pressure(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "战士", "冷峻"],
                "画面风格": ["CG感"],
                "场景背景": ["战场"],
                "构图视角": ["全身"],
                "技术画质": ["高细节", "8K"],
            }
        )
        settings = {
            "模板风格": "CG感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 1,
            "额外要求": "",
        }
        prompt = prompt_builder.build_prompt_list(
            selected,
            ["装甲", "战术机动", "工业结构"],
            settings,
            scene_group="industrial",
            identity="战士",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("战斗定位更明确", prompt)
        self.assertTrue(any(term in prompt for term in ["前线压迫感", "冲锋", "前线主角"]))

    def test_prompt_builder_style_variant_profiles_reduce_cross_family_overlap(self) -> None:
        style_profiles = prompt_builder._RUNTIME_STYLE_VARIANT_PROFILES
        style_tag_sets = {
            style: {
                tag
                for profile in profiles
                for tag in profile["style_tags"]
                if tag != style
            }
            for style, profiles in style_profiles.items()
        }
        shared_tokens: dict[tuple[str, str], set[str]] = {}
        for index, style in enumerate(style_tag_sets):
            for other_style in list(style_tag_sets)[index + 1 :]:
                overlap = style_tag_sets[style] & style_tag_sets[other_style]
                if overlap:
                    shared_tokens[(style, other_style)] = overlap

        self.assertEqual(shared_tokens, {})
        self.assertTrue(
            any(
                any(fragment in " ".join(profile["extra_fragments"]) for fragment in ["时尚", "编辑", "封面", "摄影"])
                for profile in style_profiles["真实感"]
            )
        )
        self.assertTrue(
            any(
                any(fragment in " ".join(profile["extra_fragments"]) for fragment in ["笔触", "色块", "留白", "线稿"])
                for profile in style_profiles["插画感"]
            )
        )
        self.assertTrue(
            any(
                any(fragment in " ".join(profile["extra_fragments"]) for fragment in ["材质", "光影", "体积", "空间"])
                for profile in style_profiles["CG感"]
            )
        )
        self.assertTrue(
            any(
                any(fragment in " ".join(profile["extra_fragments"]) for fragment in ["古典", "留白", "气韵", "国风"])
                for profile in style_profiles["古风"]
            )
        )
        self.assertTrue(
            any(
                any(fragment in " ".join(profile["extra_fragments"]) for fragment in ["神性", "仪式", "庄严", "幻境"])
                for profile in style_profiles["神话感"]
            )
        )

    def test_prompt_builder_resolved_runtime_style_profiles_reduce_reachable_overlap(self) -> None:
        resolved_cases = [
            ("真实感", "商业摄影", "摄影师", "photographer"),
            ("插画感", "复古OVA", "偶像", "idol"),
            ("CG感", "赛博雨夜", "特工", "agent"),
            ("古风", "古风园林", "神女", "goddess"),
            ("神话感", "神殿史诗", "女王", "queen"),
        ]
        resolved_tag_sets: dict[str, set[str]] = {}
        for style, style_track, identity, expected_group in resolved_cases:
            resolved_group = prompt_builder._identity_variant_group(identity)
            self.assertEqual(resolved_group, expected_group)
            profiles = prompt_builder._resolve_runtime_style_profiles(
                style,
                style_track,
                resolved_group,
            )
            self.assertTrue(profiles)
            tags = {
                tag
                for profile in profiles
                for tag in profile["style_tags"]
                if tag != style
            }
            resolved_tag_sets[style] = tags

        shared_tokens: dict[tuple[str, str], set[str]] = {}
        style_names = list(resolved_tag_sets)
        for index, style in enumerate(style_names):
            for other_style in style_names[index + 1 :]:
                overlap = resolved_tag_sets[style] & resolved_tag_sets[other_style]
                if overlap:
                    shared_tokens[(style, other_style)] = overlap

        self.assertEqual(shared_tokens, {})
        self.assertTrue(
            any(
                "封面" in " ".join(profile["extra_fragments"])
                or "封面" in " ".join(profile["style_tags"])
                for profile in prompt_builder._resolve_runtime_style_profiles(
                    "真实感",
                    "商业摄影",
                    prompt_builder._identity_variant_group("摄影师"),
                )
            )
        )
        self.assertTrue(
            any(
                "动画" in " ".join(profile["extra_fragments"]) or "番剧" in " ".join(profile["extra_fragments"])
                for profile in prompt_builder._resolve_runtime_style_profiles(
                    "插画感",
                    "复古OVA",
                    prompt_builder._identity_variant_group("偶像"),
                )
            )
        )
        self.assertTrue(
            any(
                "任务" in " ".join(profile["extra_fragments"])
                or "潜入" in " ".join(profile["style_tags"])
                for profile in prompt_builder._resolve_runtime_style_profiles(
                    "CG感",
                    "赛博雨夜",
                    prompt_builder._identity_variant_group("特工"),
                )
            )
        )
        self.assertTrue(
            any(
                "古典" in " ".join(profile["extra_fragments"]) or "留白" in " ".join(profile["extra_fragments"])
                for profile in prompt_builder._resolve_runtime_style_profiles(
                    "古风",
                    "古风园林",
                    prompt_builder._identity_variant_group("神女"),
                )
            )
        )
        self.assertTrue(
            any(
                "王权" in " ".join(profile["extra_fragments"]) or "统御" in " ".join(profile["extra_fragments"])
                for profile in prompt_builder._resolve_runtime_style_profiles(
                    "神话感",
                    "神殿史诗",
                    prompt_builder._identity_variant_group("女王"),
                )
            )
        )
        concrete_cases = [
            ("古风", "祭司", "priest"),
            ("神话感", "祭司", "priest"),
            ("古风", "神女", "goddess"),
            ("神话感", "神女", "goddess"),
            ("CG感", "战士", "warrior"),
            ("古风", "战士", "warrior"),
            ("神话感", "战斗修女", "sacred"),
            ("CG感", "女武士", "female_warrior"),
            ("古风", "女武士", "female_warrior"),
        ]
        branch_tags: dict[tuple[str, str], set[str]] = {}
        branch_fragments: dict[tuple[str, str], list[str]] = {}
        for style, concrete_identity, expected_group in concrete_cases:
            with self.subTest(style=style, identity=concrete_identity):
                resolved_group = prompt_builder._identity_variant_group(concrete_identity)
                self.assertEqual(resolved_group, expected_group)
                profiles = prompt_builder._resolve_runtime_style_profiles(style, "", resolved_group)
                self.assertTrue(profiles)
                branch_tags[(style, concrete_identity)] = {
                    tag
                    for profile in profiles
                    for tag in profile["style_tags"]
                    if tag != style
                }
                branch_fragments[(style, concrete_identity)] = [
                    fragment
                    for profile in profiles
                    for fragment in profile["extra_fragments"]
                ]
        shared_tokens: dict[tuple[tuple[str, str], tuple[str, str]], set[str]] = {}
        keys = list(branch_tags)
        for index, left_key in enumerate(keys):
            for right_key in keys[index + 1 :]:
                overlap = branch_tags[left_key] & branch_tags[right_key]
                if overlap:
                    shared_tokens[(left_key, right_key)] = overlap
        self.assertEqual(shared_tokens, {})
        self.assertIn("人物更像祭司题材古装定格主角", " ".join(branch_fragments[("古风", "祭司")]))
        self.assertIn("人物更像神谕叙事中的祭司主角", " ".join(branch_fragments[("神话感", "祭司")]))
        self.assertIn("人物更像神女仪典主角", " ".join(branch_fragments[("古风", "神女")]))
        self.assertIn("人物更像神话分支中的暗系神女", " ".join(branch_fragments[("神话感", "神女")]))
        self.assertIn("人物更像女武士战备镜头主角", " ".join(branch_fragments[("CG感", "女武士")]))
        self.assertIn("人物更像传奇女武士主角", " ".join(branch_fragments[("古风", "女武士")]))
        self.assertIn("战斗定位更明确", " ".join(branch_fragments[("CG感", "战士")]))
        self.assertIn("武侠定妆宣传照", " ".join(branch_fragments[("古风", "战士")]))
        self.assertIn("出场感更强", " ".join(branch_fragments[("古风", "战士")]))
        self.assertIn("神性主视觉", " ".join(branch_fragments[("神话感", "战斗修女")]))
        self.assertIn("神话故事主角", " ".join(branch_fragments[("神话感", "战斗修女")]))

    def test_prompt_builder_runtime_random_multi_output_adds_distinct_style_variants(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["真实感"], "构图视角": ["中景"]})
        custom_tags = ["压抑"]
        settings = {
            "模板风格": "真实感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 3,
            "额外要求": "",
        }
        prompts = prompt_builder.build_prompt_list(
            selected,
            custom_tags,
            settings,
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        self.assertEqual(len(prompts), 3)
        self.assertTrue(prompts[0].startswith("杂志编辑摄影"))
        self.assertTrue(prompts[1].startswith("生活电影剧照"))
        self.assertTrue(prompts[2].startswith("纪实抓拍"))
        self.assertIn("杂志感", prompts[0])
        self.assertIn("杂志编辑摄影", prompts[0])
        self.assertIn("时尚成片感更强", prompts[0])
        self.assertIn("电影剧照", prompts[1])
        self.assertIn("生活电影剧照", prompts[1])
        self.assertIn("叙事情绪更强", prompts[1])
        self.assertIn("纪实抓拍", prompts[2])
        self.assertIn("街拍", prompts[2])
        self.assertIn("抓拍感更强", prompts[2])
        self.assertIn("全景全身", prompts[0])
        self.assertIn("全景全身", prompts[1])
        self.assertIn("全景全身", prompts[2])

    def test_prompt_builder_runtime_random_full_random_multi_output_varies_subject_and_scene(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["真实感"], "构图视角": ["中景"]})
        custom_tags = ["压抑"]
        settings = {
            "模板风格": "真实感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "生成数量": 4,
            "额外要求": "",
        }
        prompts = prompt_builder.build_prompt_list(
            selected,
            custom_tags,
            settings,
            scene_group="",
            identity="",
            style_track="写实人像",
            recent_tracks=["写实人像"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        self.assertEqual(len(prompts), 4)
        self.assertIn("偶像", prompts[0])
        self.assertTrue("摄影棚" in prompts[0] or "影棚纯色背景" in prompts[0])
        self.assertIn("摄影师", prompts[1])
        self.assertTrue("街道" in prompts[1] or "咖啡厅" in prompts[1])
        self.assertIn("调酒师", prompts[2])
        self.assertTrue("酒吧" in prompts[2] or "夜店" in prompts[2])
        self.assertIn("学生", prompts[3])
        self.assertTrue("教室" in prompts[3] or "校园" in prompts[3])
        self.assertEqual(len(set(prompts)), 4)

    def test_prompt_builder_runtime_random_scene_anchor_keeps_campus_fixed(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["真实感"],
                "场景背景": ["校园", "图书馆"],
                "构图视角": ["中景"],
            }
        )
        settings = {
            "模板风格": "真实感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "生成数量": 3,
            "额外要求": "",
        }
        prompts = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="写实人像",
            recent_tracks=["写实人像"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        expected_scene_additions = [
            {"摄影棚", "影棚纯色背景"},
            {"街道", "咖啡厅"},
            {"酒吧", "夜店"},
        ]
        all_scene_additions = set().union(*expected_scene_additions)
        self.assertEqual(len(prompts), 3)
        self.assertEqual(len(set(prompts)), 3)
        for prompt, expected_scene_options in zip(prompts, expected_scene_additions):
            self.assertIn("校园", prompt)
            self.assertNotIn("图书馆", prompt)
            self.assertEqual({scene for scene in all_scene_additions if scene in prompt}, expected_scene_options)
        self.assertEqual(len({prompt.split("，", 1)[0] for prompt in prompts}), 3)

    def test_prompt_builder_runtime_random_full_random_strong_intensity_spreads_scene_buckets(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["真实感"], "构图视角": ["中景"]})
        custom_tags = ["压抑"]
        settings = {
            "模板风格": "真实感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "强",
            "生成数量": 3,
            "额外要求": "",
        }
        prompts = prompt_builder.build_prompt_list(
            selected,
            custom_tags,
            settings,
            scene_group="",
            identity="",
            style_track="写实人像",
            recent_tracks=["写实人像"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        self.assertEqual(len(prompts), 3)
        self.assertIn("偶像", prompts[0])
        self.assertTrue("摄影棚" in prompts[0] or "影棚纯色背景" in prompts[0])
        self.assertIn("摄影师", prompts[1])
        self.assertTrue("街道" in prompts[1] or "咖啡厅" in prompts[1])
        self.assertIn("调酒师", prompts[2])
        self.assertTrue("酒吧" in prompts[2] or "夜店" in prompts[2])
        self.assertIn("背景控制更克制", prompts[0])
        self.assertIn("都市环境参与感更强", prompts[1])
        self.assertTrue("人物更像酒吧题材影片定格主角" in prompts[2] or "人物更偏夜生活专题封面" in prompts[2])
        self.assertEqual(len(set(prompts)), 3)

    def test_prompt_builder_runtime_random_full_random_strong_extreme_spreads_buckets_and_avoids_first_pass_lead_repeats(self) -> None:
        cases = [
            {
                "style": "真实感",
                "style_track": "写实人像",
                "bucket_checks": [
                    {"scene_options": ("摄影棚", "影棚纯色背景"), "identity_options": ("偶像", "学生")},
                    {"scene_options": ("街道", "咖啡厅"), "identity_options": ("摄影师",)},
                    {"scene_options": ("酒吧", "夜店"), "identity_options": ("调酒师",)},
                ],
            },
            {
                "style": "插画感",
                "style_track": "复古OVA",
                "bucket_checks": [
                    {"scene_options": ("街道", "独立书店"), "identity_options": ("摄影师",)},
                    {"scene_options": ("梦境", "花海"), "identity_options": ("偶像", "学生")},
                    {"scene_options": ("霓虹小巷", "夜店"), "identity_options": ("乐队主唱",)},
                ],
            },
            {
                "style": "CG感",
                "style_track": "工业科幻",
                "bucket_checks": [
                    {"scene_options": ("办公室", "玻璃幕墙室内"), "identity_options": ("研究员",)},
                    {"scene_options": ("未来都市", "霓虹街区"), "identity_options": ("特工",)},
                    {"scene_options": ("机库", "维修车间", "工业废墟", "训练场"), "identity_options": ("机械师", "女武士")},
                ],
            },
            {
                "style": "古风",
                "style_track": "古风园林",
                "bucket_checks": [
                    {"scene_options": ("宫殿", "古风建筑", "回廊"), "identity_options": ("公主",)},
                    {"scene_options": ("竹林", "古建道场"), "identity_options": ("女武士",)},
                    {"scene_options": ("月下庭院", "古风建筑", "神圣祭坛", "云海"), "identity_options": ("神女", "祭司")},
                ],
            },
            {
                "style": "神话感",
                "style_track": "神殿史诗",
                "bucket_checks": [
                    {"scene_options": ("神圣祭坛", "宗教圣所"), "identity_options": ("祭司",)},
                    {"scene_options": ("神殿", "云海"), "identity_options": ("神女",)},
                    {"scene_options": ("黑铁王座", "神谕圣所", "法阵", "幻境"), "identity_options": ("女王", "魔女")},
                ],
            },
        ]
        for case in cases:
            with self.subTest(style=case["style"]):
                selected = OrderedDict({"主体": ["成年女性"], "画面风格": [case["style"]], "构图视角": ["中景"]})
                settings = {
                    "模板风格": case["style"],
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "强 / 极限拉开",
                    "生成数量": 3,
                    "额外要求": "",
                }
                prompts = prompt_builder.build_prompt_list(
                    selected,
                    [],
                    settings,
                    scene_group="",
                    identity="",
                    style_track=case["style_track"],
                    recent_tracks=[case["style_track"]],
                    uniq=uniq,
                    infer_template_style=lambda tags, explicit: explicit,
                    infer_subject_type=lambda tags, explicit: explicit,
                    infer_output_structure=lambda subject, explicit: explicit,
                )
                self.assertEqual(len(prompts), 3)
                self.assertEqual(len(set(prompts)), 3)
                style_leads = [prompt.split("，", 1)[0] for prompt in prompts]
                self.assertEqual(len(set(style_leads)), 3)
                found_identities: list[str] = []
                for index, bucket_check in enumerate(case["bucket_checks"]):
                    self.assertTrue(any(scene in prompts[index] for scene in bucket_check["scene_options"]))
                    matched_identity = next(
                        (identity for identity in bucket_check["identity_options"] if identity in prompts[index]),
                        "",
                    )
                    self.assertTrue(matched_identity)
                    found_identities.append(matched_identity)
                self.assertEqual(len(set(found_identities)), 3)

    def test_prompt_builder_runtime_random_uses_identity_aware_style_variants(self) -> None:
        selected = OrderedDict({"主体": ["成年女性", "偶像"], "画面风格": ["真实感"], "构图视角": ["中景"]})
        custom_tags = ["霓虹夜色"]
        settings = {
            "模板风格": "真实感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 3,
            "额外要求": "",
        }
        prompts = prompt_builder.build_prompt_list(
            selected,
            custom_tags,
            settings,
            scene_group="city",
            identity="偶像",
            style_track="写实人像",
            recent_tracks=["写实人像"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        self.assertEqual(len(prompts), 3)
        self.assertTrue(prompts[0].startswith("时装广告大片"))
        self.assertTrue(prompts[1].startswith("夜间闪光摄影"))
        self.assertIn("商业广告大片", prompts[0])
        self.assertIn("人物更像企划封面主角", prompts[0])
        self.assertIn("都市环境参与感更强", prompts[0])
        self.assertIn("夜间闪光摄影", prompts[1])
        self.assertIn("人物更像明星街头出片瞬间", prompts[1])
        self.assertIn("镜头表现欲更强", prompts[1])

    def test_prompt_builder_runtime_random_uses_style_track_aware_variants(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["古风"], "构图视角": ["中景"], "场景背景": ["花园"]})
        custom_tags = ["月下庭院"]
        settings = {
            "模板风格": "古风",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 3,
            "额外要求": "",
        }
        prompts = prompt_builder.build_prompt_list(
            selected,
            custom_tags,
            settings,
            scene_group="ancient",
            identity="成年女性",
            style_track="古风园林",
            recent_tracks=["古风园林"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        self.assertEqual(len(prompts), 3)
        self.assertTrue(prompts[0].startswith("工笔重彩"))
        self.assertTrue(prompts[1].startswith("古风电影剧照"))
        self.assertTrue(prompts[2].startswith("水墨写意"))
        self.assertIn("园林细节与服饰纹样更突出", prompts[0])
        self.assertIn("古典空间语义更完整", prompts[0])
        self.assertIn("人物与园林空间更协调", prompts[1])
        self.assertIn("留白更有呼吸感", prompts[2])

    def test_prompt_builder_runtime_random_uses_expanded_identity_variants(self) -> None:
        cases = [
            {
                "selected": OrderedDict({"主体": ["成年女性", "学生"], "画面风格": ["真实感"], "构图视角": ["中景"]}),
                "custom_tags": ["校园"],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "indoor",
                "identity": "学生",
                "style_track": "写实人像",
                "starts_with": "青春写真",
                "must_have": ["人物更像校园企划主角", "青春感更自然"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "女武士"], "画面风格": ["古风"], "构图视角": ["中景"]}),
                "custom_tags": ["竹林"],
                "settings": {
                    "模板风格": "古风",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "ancient",
                "identity": "女武士",
                "style_track": "武侠剧照",
                "starts_with": "古风电影剧照",
                "must_have": ["人物更像女武士定妆宣传照", "英气更明确"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "神女"], "画面风格": ["神话感"], "构图视角": ["中景"]}),
                "custom_tags": ["神殿"],
                "settings": {
                    "模板风格": "神话感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "sacred",
                "identity": "神女",
                "style_track": "神话人像",
                "starts_with": "神圣史诗",
                "must_have": ["人物更像神女主祭形象", "神性表达更明确"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "摄影师"], "画面风格": ["真实感"], "构图视角": ["中景"]}),
                "custom_tags": ["街道"],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "city",
                "identity": "摄影师",
                "style_track": "写实人像",
                "starts_with": "杂志编辑摄影",
                "must_have": ["人物更像创作者主题企划主角", "观察者气质更强"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "机械师"], "画面风格": ["CG感"], "构图视角": ["中景"]}),
                "custom_tags": ["机库"],
                "settings": {
                    "模板风格": "CG感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "industrial",
                "identity": "机械师",
                "style_track": "工业科幻",
                "starts_with": "概念设计稿",
                "must_have": ["人物更像机械维护主角", "技术职业感更明确"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "医生"], "画面风格": ["真实感"], "构图视角": ["中景"]}),
                "custom_tags": ["医院走廊"],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "indoor",
                "identity": "医生",
                "style_track": "写实人像",
                "starts_with": "纪实抓拍",
                "must_have": ["人物更像医疗现场主角", "专业可信度更强"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "律师"], "画面风格": ["真实感"], "构图视角": ["中景"]}),
                "custom_tags": ["办公室"],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "indoor",
                "identity": "律师",
                "style_track": "写实人像",
                "starts_with": "杂志编辑摄影",
                "must_have": ["人物更像律政专题封面主角", "理性气场更明确"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "祭司"], "画面风格": ["神话感"], "构图视角": ["中景"]}),
                "custom_tags": ["神圣祭坛"],
                "settings": {
                    "模板风格": "神话感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "sacred",
                "identity": "祭司",
                "style_track": "神话人像",
                "starts_with": "神圣史诗",
                "must_have": ["人物更像祭仪中心角色", "仪式指向更清晰"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "特工"], "画面风格": ["CG感"], "构图视角": ["中景"]}),
                "custom_tags": ["未来都市"],
                "settings": {
                    "模板风格": "CG感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "city",
                "identity": "特工",
                "style_track": "CG大片",
                "starts_with": "概念设计稿",
                "must_have": ["人物更像潜入任务主视觉主角", "任务紧张感更强"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "乐队主唱"], "画面风格": ["真实感"], "构图视角": ["中景"]}),
                "custom_tags": ["夜店"],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "city",
                "identity": "乐队主唱",
                "style_track": "写实人像",
                "starts_with": "夜间闪光摄影",
                "must_have": ["人物更像舞台外演出主角", "舞台感染力更强"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "OL"], "画面风格": ["真实感"], "构图视角": ["中景"]}),
                "custom_tags": ["办公室"],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "indoor",
                "identity": "OL",
                "style_track": "写实人像",
                "starts_with": "杂志编辑摄影",
                "must_have": ["人物更像都市职场封面主角", "职业干练感更明确"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "调酒师"], "画面风格": ["真实感"], "构图视角": ["中景"]}),
                "custom_tags": ["酒吧"],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "city",
                "identity": "调酒师",
                "style_track": "写实人像",
                "starts_with": "夜间闪光摄影",
                "must_have": ["人物更像夜场人物企划主角", "场域掌控感更强"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "研究员"], "画面风格": ["真实感"], "构图视角": ["中景"]}),
                "custom_tags": ["实验室"],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "industrial",
                "identity": "研究员",
                "style_track": "写实人像",
                "starts_with": "杂志编辑摄影",
                "must_have": ["人物更像实验专题主角", "理性探索感更明确"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "女王"], "画面风格": ["神话感"], "构图视角": ["中景"]}),
                "custom_tags": ["王座"],
                "settings": {
                    "模板风格": "神话感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "sacred",
                "identity": "女王",
                "style_track": "神话人像",
                "starts_with": "神圣史诗",
                "must_have": ["人物更像神权王座主角", "统御感更明确"],
            },
            {
                "selected": OrderedDict({"主体": ["成年女性", "魔女"], "画面风格": ["神话感"], "构图视角": ["中景"]}),
                "custom_tags": ["法阵"],
                "settings": {
                    "模板风格": "神话感",
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "生成数量": 3,
                    "额外要求": "",
                },
                "scene_group": "sacred",
                "identity": "魔女",
                "style_track": "神话人像",
                "starts_with": "暗黑奇幻",
                "must_have": ["人物更像咒术叙事主角", "神秘压迫感更强"],
            },
        ]
        for case in cases:
            with self.subTest(identity=case["identity"]):
                prompts = prompt_builder.build_prompt_list(
                    case["selected"],
                    case["custom_tags"],
                    case["settings"],
                    scene_group=case["scene_group"],
                    identity=case["identity"],
                    style_track=case["style_track"],
                    recent_tracks=[case["style_track"]],
                    uniq=uniq,
                    infer_template_style=lambda tags, explicit: explicit,
                    infer_subject_type=lambda tags, explicit: explicit,
                    infer_output_structure=lambda subject, explicit: explicit,
                )
                self.assertEqual(len(prompts), 3)
                self.assertTrue(prompts[0].startswith(str(case["starts_with"])))
                for fragment in list(case["must_have"]):
                    self.assertIn(fragment, prompts[0])

    def test_randomizer_fills_empty_slots(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "构图视角": []})
        custom_tags: list[str] = []
        settings = {
            "运行时随机模式": "保留已选核心标签",
            "运行时随机强度": "中",
            "核心标签锁定数量": 10,
            "seed": 1,
            "unique_id": "demo",
            "锁定标签白名单": "",
            "随机排除标签": "",
            "随机补充避重缓存": "",
        }
        next_selected, _, generated = randomizer.build_runtime_tags(
            selected,
            custom_tags,
            settings,
            all_tag_groups=lambda: [("主体", 2, ["无", "成年女性", "偶像"]), ("构图视角", 1, ["无", "中景", "近景"])],
            tag_group_index=lambda: {"成年女性": "主体", "偶像": "主体", "中景": "构图视角", "近景": "构图视角"},
            parse_tags=lambda text: [],
            uniq=uniq,
            seed_normalizer=lambda seed: int(seed),
            history_loader=lambda _node_id: [],
            random_module=__import__("random"),
            empty_tag="无",
        )
        self.assertGreaterEqual(len(next_selected["主体"]), 1)
        self.assertEqual(len(next_selected["构图视角"]), 1)
        self.assertTrue(generated)

    def test_randomizer_preserves_limited_core_tags(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚"],
                "构图视角": ["中景"],
                "场景背景": ["校园"],
            }
        )
        custom_tags = ["柔光"]
        settings = {
            "运行时随机模式": "保留已选核心标签",
            "运行时随机强度": "弱",
            "核心标签锁定数量": 2,
            "seed": 1,
            "unique_id": "demo",
            "锁定标签白名单": "校园",
            "随机排除标签": "",
            "随机补充避重缓存": "",
        }
        next_selected, next_custom, generated = randomizer.build_runtime_tags(
            selected,
            custom_tags,
            settings,
            all_tag_groups=lambda: [
                ("主体", 2, ["无", "成年女性", "东亚", "偶像"]),
                ("构图视角", 1, ["无", "中景"]),
                ("场景背景", 2, ["无", "校园", "教室"]),
            ],
            tag_group_index=lambda: {"成年女性": "主体", "东亚": "主体", "偶像": "主体", "中景": "构图视角", "校园": "场景背景", "教室": "场景背景"},
            parse_tags=lambda text: [item.strip() for item in str(text).split(",") if item.strip()],
            uniq=uniq,
            seed_normalizer=lambda seed: int(seed),
            history_loader=lambda _node_id: [],
            random_module=__import__("random"),
            empty_tag="无",
        )
        self.assertEqual(next_selected["主体"], ["成年女性", "东亚"])
        self.assertEqual(next_selected["构图视角"], ["中景"])
        self.assertEqual(next_selected["场景背景"], ["校园", "教室"])
        self.assertEqual(next_custom, [])
        self.assertEqual(generated, ["中景", "教室"])

    def test_randomizer_preserve_core_still_fills_auto_theme_slots(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "场景背景": []})
        settings = {
            "运行时随机模式": "保留已选核心标签",
            "运行时随机强度": "弱",
            "核心标签锁定数量": 1,
            "seed": 1,
            "unique_id": "demo",
            "锁定标签白名单": "",
            "随机排除标签": "",
            "随机补充避重缓存": "",
            "随机主题池": "自动",
        }
        next_selected, _, generated = randomizer.build_runtime_tags(
            selected,
            [],
            settings,
            all_tag_groups=lambda: [
                ("主体", 2, ["无", "成年女性", "偶像"]),
                ("场景背景", 1, ["无", "书店", "街头"]),
            ],
            tag_group_index=lambda: {"成年女性": "主体", "偶像": "主体", "书店": "场景背景", "街头": "场景背景"},
            parse_tags=lambda text: [item.strip() for item in str(text).split(",") if item.strip()],
            uniq=uniq,
            seed_normalizer=lambda seed: int(seed),
            history_loader=lambda _node_id: [],
            random_module=__import__("random"),
            empty_tag="无",
        )
        self.assertEqual(next_selected["主体"][0], "成年女性")
        self.assertEqual(len(next_selected["场景背景"]), 1)
        self.assertTrue(generated)

    def test_randomizer_explicit_full_random_does_not_preserve_selected_anchors(self) -> None:
        selected = OrderedDict({"主体": ["旧主体"], "场景背景": ["旧场景"], "构图视角": ["旧构图"]})
        settings = {
            "运行时随机模式": "全随机",
            "运行时随机强度": "弱",
            "核心标签锁定数量": 10,
            "seed": 1,
            "unique_id": "demo",
            "锁定标签白名单": "",
            "随机排除标签": "",
            "随机补充避重缓存": "",
            "随机主题池": "自动",
        }
        next_selected, _, generated = randomizer.build_runtime_tags(
            selected,
            [],
            settings,
            all_tag_groups=lambda: [
                ("主体", 1, ["无", "成年女性"]),
                ("场景背景", 1, ["无", "书店"]),
                ("构图视角", 1, ["无", "全景全身"]),
            ],
            tag_group_index=lambda: {"成年女性": "主体", "书店": "场景背景", "全景全身": "构图视角"},
            parse_tags=lambda text: [item.strip() for item in str(text).split(",") if item.strip()],
            uniq=uniq,
            seed_normalizer=lambda seed: int(seed),
            history_loader=lambda _node_id: [],
            random_module=__import__("random"),
            empty_tag="无",
        )
        self.assertNotIn("旧主体", next_selected["主体"])
        self.assertNotIn("旧场景", next_selected["场景背景"])
        self.assertNotIn("旧构图", next_selected["构图视角"])
        self.assertEqual(generated, ["成年女性", "书店", "全景全身"])

    def test_randomizer_avoids_recent_supplement_tags(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "构图视角": []})
        custom_tags: list[str] = []
        settings = {
            "运行时随机模式": "保留已选核心标签",
            "运行时随机强度": "弱",
            "核心标签锁定数量": 1,
            "seed": 1,
            "unique_id": "demo",
            "锁定标签白名单": "",
            "随机排除标签": "",
            "随机补充避重缓存": "中景",
        }
        next_selected, _, generated = randomizer.build_runtime_tags(
            selected,
            custom_tags,
            settings,
            all_tag_groups=lambda: [("主体", 1, ["无", "成年女性"]), ("构图视角", 1, ["无", "中景", "近景"])],
            tag_group_index=lambda: {"成年女性": "主体", "中景": "构图视角", "近景": "构图视角"},
            parse_tags=lambda text: [item.strip() for item in str(text).split(",") if item.strip()],
            uniq=uniq,
            seed_normalizer=lambda seed: int(seed),
            history_loader=lambda _node_id: [],
            random_module=__import__("random"),
            empty_tag="无",
        )
        self.assertEqual(next_selected["构图视角"], ["近景"])
        self.assertEqual(generated, ["近景"])

    def test_randomizer_avoids_runtime_history_identity_markers(self) -> None:
        selected = OrderedDict({"主体": []})
        settings = {
            "运行时随机模式": "全随机",
            "运行时随机强度": "强",
            "核心标签锁定数量": 0,
            "seed": 1,
            "unique_id": "demo",
            "锁定标签白名单": "",
            "随机排除标签": "",
            "随机补充避重缓存": "",
            "随机主题池": "自动",
        }
        next_selected, _, generated = randomizer.build_runtime_tags(
            selected,
            [],
            settings,
            all_tag_groups=lambda: [("主体", 1, ["无", "炎魔天使", "冰霜骑士"])],
            tag_group_index=lambda: {"炎魔天使": "主体", "冰霜骑士": "主体"},
            parse_tags=lambda text: [item.strip() for item in re.split(r"[,，]", str(text)) if item.strip()],
            uniq=uniq,
            seed_normalizer=lambda seed: int(seed),
            history_loader=lambda _node_id: ["identity:炎魔天使"],
            random_module=random,
            empty_tag="无",
        )
        self.assertEqual(next_selected["主体"], ["冰霜骑士"])
        self.assertEqual(generated, ["冰霜骑士"])

    def test_randomizer_rewrites_subject_and_scene_mode_replaces_mainline(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "偶像"],
                "场景背景": ["校园"],
                "画面风格": ["真实感", "港风"],
                "构图视角": ["中景"],
                "光影氛围": ["柔光"],
            }
        )
        custom_tags = ["保留要求", "旧主体", "旧场景"]
        settings = {
            "运行时随机模式": "重写主体与场景",
            "运行时随机强度": "中",
            "核心标签锁定数量": 10,
            "seed": 1,
            "unique_id": "demo",
            "锁定标签白名单": "",
            "随机排除标签": "",
            "随机补充避重缓存": "",
            "随机主题池": "自动",
        }
        next_selected, next_custom, generated = randomizer.build_runtime_tags(
            selected,
            custom_tags,
            settings,
            all_tag_groups=lambda: [
                ("主体", 2, ["无", "成年女性", "偶像", "摄影师", "调酒师"]),
                ("场景背景", 2, ["无", "校园", "街道", "咖啡厅"]),
                ("画面风格", 3, ["无", "真实感", "港风", "照片级"]),
                ("构图视角", 1, ["无", "中景"]),
                ("光影氛围", 1, ["无", "柔光"]),
            ],
            tag_group_index=lambda: {
                "成年女性": "主体",
                "偶像": "主体",
                "摄影师": "主体",
                "调酒师": "主体",
                "旧主体": "主体",
                "校园": "场景背景",
                "街道": "场景背景",
                "咖啡厅": "场景背景",
                "旧场景": "场景背景",
                "真实感": "画面风格",
                "港风": "画面风格",
                "照片级": "画面风格",
                "中景": "构图视角",
                "柔光": "光影氛围",
            },
            parse_tags=lambda text: [item.strip() for item in str(text).split(",") if item.strip()],
            uniq=uniq,
            seed_normalizer=lambda seed: int(seed),
            history_loader=lambda _node_id: [],
            random_module=__import__("random"),
            empty_tag="无",
        )
        self.assertTrue(next_selected["主体"])
        self.assertTrue(next_selected["场景背景"])
        self.assertNotIn("成年女性", next_selected["主体"])
        self.assertNotIn("偶像", next_selected["主体"])
        self.assertNotIn("校园", next_selected["场景背景"])
        self.assertIn("真实感", next_selected["画面风格"])
        self.assertIn("港风", next_selected["画面风格"])
        self.assertIn("中景", next_selected["构图视角"])
        self.assertIn("柔光", next_selected["光影氛围"])
        self.assertEqual(next_custom, ["保留要求"])
        self.assertTrue(generated)

    def test_randomizer_auto_mode_prefers_rewrite_when_subject_and_scene_are_dense(self) -> None:
        mode = randomizer.resolve_runtime_random_mode(
            "自动判断",
            OrderedDict(
                {
                    "主体": ["成年女性", "偶像"],
                    "场景背景": ["校园", "图书馆"],
                    "构图视角": ["中景"],
                    "画面风格": ["真实感"],
                }
            ),
            {"核心标签锁定数量": 10},
        )
        self.assertEqual(mode, "重写主体与场景")

    def test_randomizer_auto_mode_prefers_preserve_core_when_mainline_is_light(self) -> None:
        mode = randomizer.resolve_runtime_random_mode(
            "自动判断",
            OrderedDict(
                {
                    "主体": ["成年女性"],
                    "场景背景": [],
                    "构图视角": ["中景"],
                    "画面风格": ["真实感"],
                }
            ),
            {"核心标签锁定数量": 10},
        )
        self.assertEqual(mode, "保留已选核心标签")

    def test_randomizer_auto_mode_avoids_over_preserving_many_anchors(self) -> None:
        mode = randomizer.resolve_runtime_random_mode(
            "自动判断",
            OrderedDict(
                {
                    "主体": ["成年女性", "东亚"],
                    "场景背景": [],
                    "构图视角": ["中景", "全身"],
                    "画面风格": ["真实感"],
                }
            ),
            {"核心标签锁定数量": 10, "锁定标签白名单": ""},
        )
        self.assertEqual(mode, "全随机")

    def test_randomizer_auto_mode_preserves_when_whitelist_exists(self) -> None:
        mode = randomizer.resolve_runtime_random_mode(
            "自动判断",
            OrderedDict(
                {
                    "主体": ["成年女性", "东亚"],
                    "场景背景": [],
                    "构图视角": ["中景", "全身"],
                    "画面风格": ["真实感"],
                }
            ),
            {"核心标签锁定数量": 0, "锁定标签白名单": "成年女性"},
        )
        self.assertEqual(mode, "保留已选核心标签")

    def test_prompt_builder_recent_diversity_guard_pushes_recent_profile_back(self) -> None:
        profiles = list(prompt_builder._RUNTIME_DIVERSITY_VARIANT_PROFILES["真实感"])
        recent_signature = prompt_builder._diversity_signature_for_profile(profiles[0])
        ordered = prompt_builder._order_runtime_diversity_profiles(
            profiles,
            style="真实感",
            style_track="写实人像",
            recent_tracks=["写实人像", f"diversity:{recent_signature}"],
            runtime_random_intensity="中",
        )
        self.assertNotEqual(
            prompt_builder._diversity_signature_for_profile(ordered[0]),
            recent_signature,
        )

    def test_prompt_builder_recent_diversity_guard_avoids_same_macro_direction(self) -> None:
        profiles = list(prompt_builder._RUNTIME_DIVERSITY_VARIANT_PROFILES["真实感"])
        recent_signature = prompt_builder._diversity_signature_for_profile(profiles[0])
        ordered = prompt_builder._order_runtime_diversity_profiles(
            profiles,
            style="真实感",
            style_track="写实人像",
            recent_tracks=["写实人像", f"diversity:{recent_signature}"],
            runtime_random_intensity="中",
        )
        self.assertNotEqual(
            str(ordered[0].get("macro_direction", "")).strip(),
            str(profiles[0].get("macro_direction", "")).strip(),
        )

    def test_prompt_builder_recent_identity_guard_avoids_same_profile_identity(self) -> None:
        profiles = list(prompt_builder._RUNTIME_DIVERSITY_TRACK_OVERRIDES[("神话感", "西方奇幻神话史诗")])
        infernal = next(profile for profile in profiles if profile.get("subject_identity") == "炎魔天使")
        ordered = prompt_builder._order_runtime_diversity_profiles(
            [infernal, *[profile for profile in profiles if profile is not infernal]],
            style="神话感",
            style_track="西方奇幻神话史诗",
            recent_tracks=["西方奇幻神话史诗", "identity:炎魔天使"],
            runtime_random_intensity="中",
        )
        self.assertNotEqual(str(ordered[0].get("subject_identity", "")).strip(), "炎魔天使")

    def test_prompt_builder_exposes_runtime_diversity_markers_for_next_run(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["神话感"], "构图视角": ["全景全身"]})
        settings = {
            "模板风格": "神话感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "强",
            "生成数量": 1,
            "额外要求": "",
        }
        prompts = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="西方奇幻神话史诗",
            recent_tracks=["西方奇幻神话史诗"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        markers = settings.get("运行时随机档案标记", [])
        self.assertTrue(prompts)
        self.assertTrue(any(str(marker).startswith("diversity:") for marker in markers))
        self.assertTrue(any(str(marker).startswith("identity:") for marker in markers))
        self.assertTrue(any(str(marker).startswith("macro:") for marker in markers))

    def test_prompt_builder_rewrite_subject_scene_uses_runtime_diversity_profiles(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["真实感"], "构图视角": ["全景全身"]})
        settings = {
            "模板风格": "真实感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "重写主体与场景",
            "运行时随机强度": "强",
            "生成数量": 2,
            "额外要求": "",
        }
        prompts = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="商业摄影",
            recent_tracks=["商业摄影"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        markers = settings.get("运行时随机档案标记", [])
        self.assertEqual(len(prompts), 2)
        self.assertNotEqual(prompts[0], prompts[1])
        self.assertTrue(any(str(marker).startswith("diversity:") for marker in markers))
        self.assertTrue(any(str(marker).startswith("identity:") for marker in markers))

    def test_prompt_builder_recent_diversity_guard_avoids_same_first_prompt_across_runs(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": ["真实感"], "构图视角": ["中景"]})
        settings = {
            "模板风格": "真实感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "生成数量": 1,
            "额外要求": "",
        }
        first_run = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="写实人像",
            recent_tracks=["写实人像"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        recent_signature = prompt_builder._diversity_signature_for_profile(
            prompt_builder._RUNTIME_DIVERSITY_VARIANT_PROFILES["真实感"][0]
        )
        second_run = prompt_builder.build_prompt_list(
            selected,
            [],
            settings,
            scene_group="",
            identity="",
            style_track="写实人像",
            recent_tracks=["写实人像", f"diversity:{recent_signature}"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        self.assertTrue(first_run)
        self.assertTrue(second_run)
        self.assertNotEqual(first_run[0], second_run[0])

    def test_prompt_builder_variant_group_fragments_apply_extended_diversity_replacements(self) -> None:
        diversity_profile = {
            "replace_subject_tags": ["成年女性", "东亚", "摄影师"],
            "replace_scene_tags": ["街道", "雨夜站台"],
            "replace_outfit_tags": ["长款大衣", "白衬衫"],
            "replace_light_tags": ["阴天柔散光", "青蓝冷雾"],
            "replace_action_tags": ["回眸", "手持相机"],
            "replace_prop_tags": ["相机", "摄影包"],
            "subject_identity": "摄影师",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "urban_observer",
            "diversity_signature": "outdoor::city::摄影师::urban_observer::街道|雨夜站台",
        }
        self.assertEqual(
            prompt_builder._variant_group_fragments("服装造型", ["针织"], None, None, diversity_profile),
            ["长款大衣", "白衬衫"],
        )
        self.assertEqual(
            prompt_builder._variant_group_fragments("光影氛围", ["柔光"], None, None, diversity_profile),
            ["阴天柔散光", "青蓝冷雾"],
        )
        self.assertEqual(
            prompt_builder._variant_group_fragments("动作姿态", ["站姿放松"], None, None, diversity_profile),
            ["回眸", "手持相机"],
        )
        self.assertEqual(
            prompt_builder._variant_group_fragments("道具世界观", ["书本"], None, None, diversity_profile),
            ["相机", "摄影包"],
        )

    def test_prompt_builder_runtime_diversity_track_overrides_expose_non_core_groups(self) -> None:
        cases = {
            ("真实感", "写实人像"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("真实感", "生活纪实"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("真实感", "商业摄影"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("真实感", "私房写实"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("真实感", "时尚编辑商业广告"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("真实感", "日韩影像"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("CG感", "赛博雨夜"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("CG感", "工业科幻"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("插画感", "插画叙事"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("插画感", "复古OVA"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("古风", "古风园林"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("古风", "武侠剧照"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("神话感", "神话人像"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("神话感", "神殿史诗"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("神话感", "山谷圣城史诗"): ("replace_light_tags", "replace_prop_tags", "replace_composition_tags"),
            ("神话感", "西方奇幻神话史诗"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("古风", "东方古风武侠"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("古风", "国风暗黑志怪"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("CG感", "东方赛博武侠朋克"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags"),
            ("CG感", "工业树灵巨像"): ("replace_light_tags", "replace_prop_tags", "replace_composition_tags"),
            ("真实感", "城市天台纪实"): ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags", "replace_composition_tags"),
        }
        for (style, track), required_keys in cases.items():
            with self.subTest(style=style, track=track):
                profiles = prompt_builder._resolve_runtime_diversity_profiles(style, track)
                self.assertTrue(profiles)
                self.assertTrue(any(all(profile.get(key) for key in required_keys) for profile in profiles))

    def test_prompt_builder_runtime_diversity_track_profiles_vary_non_core_groups(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["真实感"],
                "服装造型": ["针织"],
                "场景背景": ["街道"],
                "光影氛围": ["柔光"],
                "构图视角": ["中景半身"],
                "动作姿态": ["站姿放松"],
                "道具世界观": ["书本"],
                "技术画质": ["高细节"],
            }
        )
        prompt_list = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 4,
                "额外要求": "",
            },
            scene_group="city",
            identity="",
            style_track="都市电影人文",
            recent_tracks=["都市电影人文"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        joined = "\n".join(prompt_list)
        self.assertTrue(any(tag in joined for tag in ("长款大衣", "风衣", "西装", "皮夹克")))
        self.assertTrue(any(tag in joined for tag in ("阴天柔散光", "青蓝冷雾", "暖褪色胶片")))
        self.assertTrue(any(tag in joined for tag in ("回眸", "双手负后", "倚靠栏杆", "手持咖啡杯")))
        self.assertTrue(any(tag in joined for tag in ("相机", "摄影包", "咖啡杯", "雨伞")))

    def test_prompt_builder_runtime_diversity_track_profiles_vary_non_core_groups_for_realistic_base(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["真实感"],
                "服装造型": ["白衬衫"],
                "场景背景": ["街道"],
                "光影氛围": ["自然光"],
                "构图视角": ["全景全身"],
                "动作姿态": ["站姿放松"],
                "道具世界观": ["书本"],
                "技术画质": ["高细节"],
            }
        )
        prompt_list = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 4,
                "额外要求": "",
            },
            scene_group="city",
            identity="",
            style_track="写实人像",
            recent_tracks=["写实人像"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        joined = "\n".join(prompt_list)
        self.assertTrue(any(tag in joined for tag in ("长款大衣", "白衬衫", "针织开衫", "西装")))
        self.assertTrue(any(tag in joined for tag in ("自然光", "阴天柔散光", "电影胶片look", "暖褪色胶片")))
        self.assertTrue(any(tag in joined for tag in ("回眸", "若有所思", "手部姿态自然", "双手插袋")))
        self.assertTrue(any(tag in joined for tag in ("书本", "相机", "托特包", "咖啡杯")))

    def test_prompt_builder_runtime_diversity_track_profiles_vary_non_core_groups_for_rooftop_documentary(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["真实感"],
                "服装造型": ["白衬衫"],
                "场景背景": ["城市天台"],
                "光影氛围": ["自然光"],
                "构图视角": ["中景半身"],
                "动作姿态": ["站姿放松"],
                "道具世界观": ["手机"],
                "技术画质": ["高细节"],
            }
        )
        prompt_list = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 4,
                "额外要求": "",
            },
            scene_group="city",
            identity="",
            style_track="城市天台纪实",
            recent_tracks=["城市天台纪实"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        joined = "\n".join(prompt_list)
        self.assertTrue(any(tag in joined for tag in ("长款大衣", "宽松外套", "针织开衫", "短外套")))
        self.assertTrue(any(tag in joined for tag in ("日落逆光", "金色侧逆光", "自然光")))
        self.assertTrue(any(tag in joined for tag in ("侧目看向远处", "回头看向镜头", "若有所思", "视线越过镜头")))
        self.assertTrue(any(tag in joined for tag in ("有线耳机", "耳机", "手机", "书本")))
        self.assertTrue(any(tag in joined for tag in ("侧脸构图", "负空间留白", "镜头近距离")))

    def test_prompt_builder_runtime_diversity_track_profiles_vary_non_core_groups_for_cg_base(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["CG感"],
                "服装造型": ["机能外套"],
                "场景背景": ["未来都市"],
                "光影氛围": ["体积光"],
                "构图视角": ["全景全身"],
                "动作姿态": ["站姿挺拔"],
                "道具世界观": ["全息界面"],
                "技术画质": ["高细节"],
            }
        )
        prompt_list = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "CG感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 4,
                "额外要求": "",
            },
            scene_group="industrial",
            identity="",
            style_track="工业科幻",
            recent_tracks=["工业科幻"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        joined = "\n".join(prompt_list)
        self.assertTrue(any(tag in joined for tag in ("机能外套", "战术服", "皮革", "短外套")))
        self.assertTrue(any(tag in joined for tag in ("全息投影光", "广告屏反射光", "蓝洋红对撞", "青蓝冷雾")))
        self.assertTrue(any(tag in joined for tag in ("持物待发", "回头看向镜头", "站姿挺拔", "双手负后")))
        self.assertTrue(any(tag in joined for tag in ("能量刀", "全息界面", "手机", "耳机")))

    def test_prompt_builder_runtime_diversity_track_profiles_apply_for_non_human_colossus(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["树灵巨像"],
                "画面风格": ["CG感"],
                "场景背景": ["工业舱室"],
                "构图视角": ["中景"],
                "道具世界观": ["苔藓附生质感"],
                "技术画质": ["高细节"],
            }
        )
        prompt_list = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "CG感",
                "主体类型": "非人物主体",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 4,
                "额外要求": "",
            },
            scene_group="industrial",
            identity="",
            style_track="工业树灵巨像",
            recent_tracks=["工业树灵巨像"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        joined = "\n".join(prompt_list)
        self.assertTrue(any(tag in joined for tag in ("树灵巨像", "古木守卫", "藤蔓木妖")))
        self.assertTrue(any(tag in joined for tag in ("工业舱室", "维修车间", "机库")))
        self.assertTrue(any(tag in joined for tag in ("朽木树皮纹理", "苔藓附生质感", "发光裂隙")))
        self.assertTrue(any(tag in joined for tag in ("巨物压迫近景", "低角度", "超广角全景")))

    def test_prompt_builder_non_person_expansion_uses_structure_not_portrait_language(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["侦查机甲"],
                "画面风格": ["CG感"],
                "场景背景": ["机库"],
                "光影氛围": ["冷色调", "轮廓光"],
                "构图视角": ["全景"],
                "动作姿态": ["悬浮待机"],
                "道具世界观": ["全息界面"],
                "技术画质": ["高细节", "真实材质"],
            }
        )
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "CG感",
                "主体类型": "非人物主体",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": False,
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "提示词语言": "纯中文",
                "详细度": "详细",
                "生成数量": 1,
                "额外要求": "",
            },
            scene_group="industrial",
            identity="",
            style_track="工业科幻",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]

        self.assertIn("非人物主题", prompt)
        self.assertIn("主体结构", prompt)
        self.assertIn("功能部件", prompt)
        self.assertNotIn("成年女性", prompt)
        self.assertNotIn("脸部可读性", prompt)
        self.assertNotIn("手指数量稳定", prompt)
        self.assertNotIn("解剖结构自然", prompt)
        self.assertNotIn("服装造型", prompt)

    def test_prompt_builder_runtime_diversity_track_profiles_vary_non_core_groups_for_private_realistic(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["真实感"],
                "服装造型": ["丝质睡袍"],
                "场景背景": ["卧室"],
                "光影氛围": ["柔光"],
                "构图视角": ["全景全身"],
                "动作姿态": ["站姿放松"],
                "道具世界观": ["书本"],
                "技术画质": ["高细节"],
            }
        )
        prompt_list = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "成人向成熟",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 4,
                "额外要求": "",
            },
            scene_group="indoor",
            identity="",
            style_track="私房写实",
            recent_tracks=["私房写实"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        joined = "\n".join(prompt_list)
        self.assertTrue(any(tag in joined for tag in ("丝质睡袍", "吊带睡裙", "露背礼服", "针织开衫")))
        self.assertTrue(any(tag in joined for tag in ("柔和光晕", "电影胶片look", "暖褪色胶片", "暖色轮廓逆光")))
        self.assertTrue(any(tag in joined for tag in ("倚靠栏杆", "低头浅笑", "手部姿态自然", "侧身")))
        self.assertTrue(any(tag in joined for tag in ("手持咖啡杯", "酒杯", "雨伞", "镜前")))

    def test_prompt_builder_runtime_diversity_track_profiles_vary_non_core_groups_for_illustration(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["插画感"],
                "服装造型": ["汉服"],
                "场景背景": ["梦境"],
                "光影氛围": ["柔光"],
                "构图视角": ["全景全身"],
                "动作姿态": ["站姿放松"],
                "道具世界观": ["书本"],
                "技术画质": ["高细节"],
            }
        )
        prompt_list = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "插画感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 4,
                "额外要求": "",
            },
            scene_group="nature",
            identity="",
            style_track="插画叙事",
            recent_tracks=["插画叙事"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        joined = "\n".join(prompt_list)
        self.assertTrue(any(tag in joined for tag in ("和服", "Lolita", "披风", "奶油针织")))
        self.assertTrue(any(tag in joined for tag in ("浮光", "叶隙斑驳光", "高调粉彩", "暖褪色胶片")))
        self.assertTrue(any(tag in joined for tag in ("轻拈发梢", "回眸", "拈花而立", "侧坐回眸")))
        self.assertTrue(any(tag in joined for tag in ("花束", "卷轴", "伞", "古琴")))

    def test_prompt_builder_runtime_diversity_track_profiles_vary_non_core_groups_for_mythic(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["神话感"],
                "服装造型": ["长袍"],
                "场景背景": ["神殿"],
                "光影氛围": ["体积光"],
                "构图视角": ["全景全身"],
                "动作姿态": ["站姿挺拔"],
                "道具世界观": ["法器"],
                "技术画质": ["高细节"],
            }
        )
        prompt_list = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "神话感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 4,
                "额外要求": "",
            },
            scene_group="sacred",
            identity="",
            style_track="神殿史诗",
            recent_tracks=["神殿史诗"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        joined = "\n".join(prompt_list)
        self.assertTrue(any(tag in joined for tag in ("神官长袍", "鎏金头冠", "白色斗篷", "黑金重甲")))
        self.assertTrue(any(tag in joined for tag in ("圣辉逆光", "体积神光", "金雾神光", "蓝灰月光")))
        self.assertTrue(any(tag in joined for tag in ("抬头仰望", "伸手触碰", "拈花而立", "站姿挺拔")))
        self.assertTrue(any(tag in joined for tag in ("日轮", "月轮", "权杖", "圣火")))

    def test_prompt_builder_runtime_diversity_track_profiles_apply_for_non_human_epic_scene(self) -> None:
        selected = OrderedDict(
            {
                "画面风格": ["神话感"],
                "场景背景": ["山谷圣城"],
                "构图视角": ["大全景"],
                "道具世界观": ["史诗城市中轴"],
                "技术画质": ["高细节"],
            }
        )
        prompt_list = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "神话感",
                "主体类型": "非人物主体",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 4,
                "额外要求": "",
            },
            scene_group="sacred",
            identity="",
            style_track="山谷圣城史诗",
            recent_tracks=["山谷圣城史诗"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        joined = "\n".join(prompt_list)
        self.assertTrue(any(tag in joined for tag in ("巨构神殿", "瀑布峡谷", "远山雪峰")))
        self.assertTrue(any(tag in joined for tag in ("史诗城市中轴", "山体建筑一体化")))
        self.assertTrue(any(tag in joined for tag in ("中轴对称巨构", "超广角全景", "祭坛对称构图")))
        self.assertTrue(any(tag in joined for tag in ("云隙光", "圣辉逆光", "体积光", "金雾神光")))

    def test_prompt_builder_runtime_diversity_track_profiles_vary_non_core_groups_for_wuxia(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["古风"],
                "服装造型": ["汉服"],
                "场景背景": ["竹林"],
                "光影氛围": ["柔光"],
                "构图视角": ["全景全身"],
                "动作姿态": ["站姿放松"],
                "道具世界观": ["书本"],
                "技术画质": ["高细节"],
            }
        )
        prompt_list = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "古风",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 4,
                "额外要求": "",
            },
            scene_group="ancient",
            identity="",
            style_track="东方古风武侠",
            recent_tracks=["东方古风武侠"],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )
        joined = "\n".join(prompt_list)
        self.assertTrue(any(tag in joined for tag in ("劲装", "宽袖法袍", "披风", "飞鱼服")))
        self.assertTrue(any(tag in joined for tag in ("烛火暖光", "暖色轮廓逆光", "红雾表现主义打光", "青蓝冷雾")))
        self.assertTrue(any(tag in joined for tag in ("扶剑而立", "持刀回身", "回头看向镜头", "双手负后")))
        self.assertTrue(any(tag in joined for tag in ("剑", "刀", "伞", "灯笼")))

    def test_formatter_builds_selected_text_and_payload(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "构图视角": ["中景"]})
        custom_tags = ["压抑"]
        selected_text = formatter.build_selected_tags_text(
            template_style="真实感",
            subject_type="人物角色",
            output_structure="案例长段版",
            runtime_random_enabled=False,
            settings={
                "运行时随机模式": "全随机",
                "核心标签锁定数量": 10,
                "运行时随机强度": "中",
                "随机主题池": "神话史诗",
                "标签反推模式": "自动平衡",
                "模型来源": "API接口",
                "API服务商": "OpenAI兼容",
                "API模型": "demo-model",
                "推理纠偏说明": ["世界观纠偏"],
            },
            adult_subpool="none",
            scene_group="sacred",
            identity="偶像",
            style_track="写实人像",
            selected=selected,
            custom_tags=custom_tags,
            recent_tracks=["写实人像"],
            negative_prompt="文字、多人复制",
            format_grouped_summary=prompt_builder.format_grouped_summary,
        )
        self.assertIn("模板风格：真实感", selected_text)
        self.assertIn("随机主题池：神话史诗", selected_text)
        self.assertIn("模型与Skill链路：Skill前置 + API模型后置润色", selected_text)
        self.assertIn("推理纠偏：世界观纠偏", selected_text)
        payload = formatter.build_json_payload(
            full_text="FULL",
            prompt_only="PROMPT",
            prompt_list=["PROMPT"],
            selected_tags_text=selected_text,
            selected=selected,
            tags=["成年女性", "中景", "压抑"],
            template_style="真实感",
            subject_type="人物角色",
            output_structure="案例长段版",
            runtime_random_enabled=False,
            settings={
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "神话史诗",
                "模型来源": "API接口",
                "API服务商": "OpenAI兼容",
                "API模型": "demo-model",
                "模型来源实际": "API接口",
                "模型调用状态": "调用成功：1 次，采纳 1 次",
                "模型调用尝试次数": 1,
                "模型调用成功次数": 1,
                "模型调用失败次数": 0,
                "模型调用采纳次数": 1,
                "核心标签锁定数量": 10,
                "优先柔和肤质": True,
                "抑制文字伪影": False,
                "生成数量": 1,
                "提示词语言": "纯中文",
                "详细度": "详细",
                "输出模式": "完整结果",
                "额外要求": "固定单一主场景",
                "推理纠偏说明": ["世界观纠偏"],
                "Skill动态变化策略": "随机运行时；标签作为素材锚点而非固定模板；优先变化未明确锁定维度。",
                "最近提示词指纹": ["visual:scene:神谕圣所|light:柔光", "成年女性|中景|压抑"],
            },
            generated=["中景"],
            lock_tag_whitelist=["中景"],
            random_exclude_tags=["多人"],
            scene_group="sacred",
            identity="偶像",
            adult_subpool="none",
            style_track="写实人像",
            recent_tracks=["写实人像"],
            negative_prompt="文字、多人复制",
        )
        self.assertEqual(payload["prompt_text"], "PROMPT")
        self.assertEqual(payload["runtime_random_theme_pool"], "神话史诗")
        self.assertEqual(payload["lock_tag_whitelist"], ["中景"])
        self.assertEqual(payload["extra_requirement"], "固定单一主场景")
        self.assertEqual(payload["runtime_random_mode_resolved"], "")
        self.assertEqual(payload["model_source"], "API接口")
        self.assertEqual(payload["model_call_status"], "调用成功：1 次，采纳 1 次")
        self.assertEqual(payload["model_call_attempt_count"], 1)
        self.assertEqual(payload["model_call_success_count"], 1)
        self.assertEqual(payload["model_call_failure_count"], 0)
        self.assertEqual(payload["model_call_adopted_count"], 1)
        self.assertIn("Skill前置 + API模型后置润色", payload["model_skill_pipeline"])
        self.assertIn("标签作为素材锚点而非固定模板", payload["skill_dynamic_strategy"])
        self.assertEqual(payload["recent_prompt_fingerprint_count"], 2)
        self.assertEqual(payload["smart_text_style_priority"], "自动判断")
        self.assertEqual(payload["smart_text_style_priority_resolved"], "")
        self.assertEqual(payload["smart_text_style_resolved"], "")
        cache_payload = formatter.build_cache_payload(
            full_text="FULL",
            primary_prompt="FIRST PROMPT",
            prompt_only="FIRST PROMPT\n\nSECOND PROMPT",
            prompt_collection="FIRST PROMPT\n\nSECOND PROMPT",
            selected_tags_text=selected_text,
            json_result=json.dumps(payload, ensure_ascii=False),
            negative_prompt="文字、多人复制",
            style_track="写实人像",
            smart_text_prompt="SMART PROMPT",
        )
        self.assertEqual(cache_payload["status"], "done")
        self.assertIsInstance(cache_payload["updated_at"], int)
        self.assertEqual(cache_payload["prompt_text"], "FIRST PROMPT")
        self.assertEqual(cache_payload["prompt_collection"], "FIRST PROMPT\n\nSECOND PROMPT")
        self.assertEqual(cache_payload["model_call_status"], "调用成功：1 次，采纳 1 次")
        self.assertEqual(cache_payload["model_call_attempt_count"], 1)
        self.assertEqual(cache_payload["model_call_success_count"], 1)
        self.assertEqual(cache_payload["model_call_failure_count"], 0)
        self.assertEqual(cache_payload["model_call_adopted_count"], 1)
        self.assertIn("Skill前置 + API模型后置润色", cache_payload["model_skill_pipeline"])
        self.assertIn("标签作为素材锚点而非固定模板", cache_payload["skill_dynamic_strategy"])
        self.assertEqual(cache_payload["recent_prompt_fingerprint_count"], 2)
        self.assertEqual(cache_payload["normalization_notes"], ["世界观纠偏"])
        self.assertEqual(cache_payload["outputs"][1], "FIRST PROMPT")
        self.assertEqual(cache_payload["outputs"][5], "FIRST PROMPT\n\nSECOND PROMPT")
        self.assertEqual(cache_payload["outputs"][6], "SMART PROMPT")

    def test_formatter_hides_verbose_adult_safety_terms_in_display_only(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "构图视角": ["中景"]})
        negative_prompt = "OVA风、未成年、幼态、萝莉感、课堂情境、校规情境、违法暗示、强迫暗示、暴力羞辱、露骨器官特写、文字"
        selected_text = formatter.build_selected_tags_text(
            template_style="真实感",
            subject_type="人物角色",
            output_structure="案例长段版",
            runtime_random_enabled=False,
            settings={
                "运行时随机模式": "全随机",
                "核心标签锁定数量": 10,
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "标签反推模式": "成人向成熟",
                "推理纠偏说明": [],
            },
            adult_subpool="none",
            scene_group="private",
            identity="成年女性",
            style_track="写实人像",
            selected=selected,
            custom_tags=[],
            recent_tracks=[],
            negative_prompt=negative_prompt,
            format_grouped_summary=prompt_builder.format_grouped_summary,
        )
        self.assertIn("OVA风", selected_text)
        self.assertIn("文字", selected_text)
        self.assertIn("成人安全护栏已启用", selected_text)
        for hidden in ("未成年", "幼态", "萝莉感", "课堂情境", "校规情境", "违法暗示", "强迫暗示", "暴力羞辱", "露骨器官"):
            self.assertNotIn(hidden, selected_text)

        payload = formatter.build_json_payload(
            full_text="FULL",
            prompt_only="PROMPT",
            prompt_list=["PROMPT"],
            selected_tags_text=selected_text,
            selected=selected,
            tags=["成年女性", "中景"],
            template_style="真实感",
            subject_type="人物角色",
            output_structure="案例长段版",
            runtime_random_enabled=False,
            settings={
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "核心标签锁定数量": 10,
                "优先柔和肤质": True,
                "抑制文字伪影": True,
                "生成数量": 1,
                "提示词语言": "纯中文",
                "详细度": "详细",
                "输出模式": "完整结果",
                "额外要求": "",
            },
            generated=[],
            lock_tag_whitelist=[],
            random_exclude_tags=[],
            scene_group="private",
            identity="成年女性",
            adult_subpool="none",
            style_track="写实人像",
            recent_tracks=[],
            negative_prompt=negative_prompt,
        )
        self.assertIn("未成年", payload["negative_prompt_recommendation"])
        self.assertNotIn("未成年", payload["negative_prompt_display"])
        self.assertIn("成人安全护栏已启用", payload["negative_prompt_display"])
        self.assertEqual(payload["runtime_random_mode_resolved"], "")
        self.assertEqual(payload["smart_text_style_priority"], "自动判断")
        self.assertEqual(payload["smart_text_style_priority_resolved"], "")
        self.assertEqual(payload["smart_text_style_resolved"], "")

    def test_adult_subpool_ignores_loose_male_word_in_custom_sentence(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        self.assertEqual(module._adult_subpool(["成年女性", "内衣风", "女人抱着一个男的身体"]), "")
        self.assertEqual(module._adult_subpool(["成年男性", "内衣风"]), "male_private")

    def test_state_builder_keeps_random_theme_pool(self) -> None:
        selected, custom_tags, settings, all_tags_text = state_builder.build_state_from_kwargs(
            {
                "模板风格": "自动",
                "主体类型": "自动",
                "案例输出结构": "自动",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "糖水写真",
                "生成数量": 1,
                "提示词语言": "纯中文",
                "详细度": "详细",
                "输出模式": "完整结果",
                "标签反推模式": "自动平衡",
                "主体标签1": "成年女性",
                "自定义补充标签": "柔光",
            },
            collect_selected=lambda kwargs: (OrderedDict({"主体": ["成年女性"]}), ["柔光"]),
            tag_group_index=lambda: {"柔光": "光影氛围"},
            group_slot_limits={"主体": 4, "光影氛围": 3},
            setting_defaults={
                "模板风格": "自动",
                "主体类型": "自动",
                "案例输出结构": "自动",
                "运行时随机标签": False,
                "运行时随机模式": "全随机",
                "核心标签锁定数量": 10,
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "标签反推模式": "自动平衡",
                "生成数量": 3,
                "提示词语言": "纯中文",
                "详细度": "标准",
                "输出模式": "完整结果",
                "优先柔和肤质": False,
                "抑制文字伪影": False,
                "额外要求": "",
                "锁定标签白名单": "",
                "随机排除标签": "",
                "随机补充避重缓存": "",
                "系统提示词覆盖": "",
                "最大生成token": 960,
                "温度": 0.62,
                "top_p": 0.9,
                "top_k": 40,
                "重复惩罚": 1.08,
                "频率惩罚": 0.0,
                "存在惩罚": 0.0,
                "seed": 0,
                "输出think块": False,
            },
            safe_int=lambda value, default, low, high: max(low, min(high, int(value))),
            safe_float=lambda value, default, low, high: max(low, min(high, float(value))),
            normalize_inference_state=lambda selected, custom_tags, settings: (selected, custom_tags, []),
            collect_all_tags=lambda selected, custom_tags: [*selected["主体"], *custom_tags],
        )
        self.assertEqual(settings["随机主题池"], "糖水写真")
        self.assertEqual(all_tags_text, "成年女性、柔光")

    def test_state_builder_collapses_legacy_reverse_modes_to_auto_balance(self) -> None:
        _selected, _custom_tags, settings, _all_tags_text = state_builder.build_state_from_kwargs(
            {
                "标签反推模式": "商业摄影",
            },
            collect_selected=lambda kwargs: (OrderedDict({"主体": ["成年女性"]}), []),
            tag_group_index=lambda: {},
            group_slot_limits={"主体": 4},
            setting_defaults={
                "模板风格": "自动",
                "主体类型": "自动",
                "案例输出结构": "自动",
                "运行时随机标签": False,
                "运行时随机模式": "全随机",
                "核心标签锁定数量": 10,
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "标签反推模式": "自动平衡",
                "生成数量": 3,
                "提示词语言": "纯中文",
                "详细度": "标准",
                "输出模式": "完整结果",
                "优先柔和肤质": False,
                "抑制文字伪影": False,
                "额外要求": "",
                "锁定标签白名单": "",
                "随机排除标签": "",
                "随机补充避重缓存": "",
                "系统提示词覆盖": "",
                "最大生成token": 960,
                "温度": 0.62,
                "top_p": 0.9,
                "top_k": 40,
                "重复惩罚": 1.08,
                "频率惩罚": 0.0,
                "存在惩罚": 0.0,
                "seed": 0,
                "输出think块": False,
            },
            safe_int=lambda value, default, low, high: max(low, min(high, int(value))),
            safe_float=lambda value, default, low, high: max(low, min(high, float(value))),
            normalize_inference_state=lambda selected, custom_tags, settings: (selected, custom_tags, []),
            collect_all_tags=lambda selected, custom_tags: [*selected["主体"], *custom_tags],
        )
        self.assertEqual(settings["标签反推模式"], "自动平衡")

    def test_state_builder_empty_system_template_falls_back_to_default(self) -> None:
        default_template = "节点默认系统模板"
        selected, _custom_tags, settings, _all_tags_text = state_builder.build_state_from_kwargs(
            {"系统提示词覆盖": ""},
            collect_selected=lambda kwargs: (OrderedDict({"主体": ["成年女性"]}), []),
            tag_group_index=lambda: {},
            group_slot_limits={"主体": 4},
            setting_defaults={
                "模板风格": "自动",
                "主体类型": "自动",
                "案例输出结构": "自动",
                "运行时随机标签": False,
                "运行时随机模式": "全随机",
                "核心标签锁定数量": 10,
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "标签反推模式": "自动平衡",
                "生成数量": 3,
                "提示词语言": "纯中文",
                "详细度": "标准",
                "输出模式": "完整结果",
                "优先柔和肤质": False,
                "抑制文字伪影": False,
                "额外要求": "",
                "锁定标签白名单": "",
                "随机排除标签": "",
                "随机补充避重缓存": "",
                "系统提示词覆盖": default_template,
                "最大生成token": 960,
                "温度": 0.62,
                "top_p": 0.9,
                "top_k": 40,
                "重复惩罚": 1.08,
                "频率惩罚": 0.0,
                "存在惩罚": 0.0,
                "seed": 0,
                "输出think块": False,
            },
            safe_int=lambda value, default, low, high: max(low, min(high, int(value))),
            safe_float=lambda value, default, low, high: max(low, min(high, float(value))),
            normalize_inference_state=lambda selected, custom_tags, settings: (selected, custom_tags, []),
            collect_all_tags=lambda selected, custom_tags: [*selected["主体"], *custom_tags],
        )
        self.assertEqual(selected["主体"], ["成年女性"])
        self.assertEqual(settings["系统提示词覆盖"], default_template)

    def test_state_builder_routes_custom_half_body_tag_into_composition_group(self) -> None:
        def normalize_stub(
            selected: OrderedDict[str, list[str]],
            custom_tags: list[str],
            settings: dict[str, object],
        ) -> tuple[OrderedDict[str, list[str]], list[str], list[str]]:
            next_selected = OrderedDict((key, list(value)) for key, value in selected.items())
            next_custom = [tag for tag in custom_tags if tag != "中景半身"]
            next_selected.setdefault("构图视角", [])
            if "中景半身" not in next_selected["构图视角"]:
                next_selected["构图视角"].append("中景半身")
            return next_selected, next_custom, []

        selected, custom_tags, _settings, all_tags_text = state_builder.build_state_from_kwargs(
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "生成数量": 1,
                "提示词语言": "纯中文",
                "详细度": "详细",
                "输出模式": "完整结果",
                "标签反推模式": "自动平衡",
                "主体标签1": "成年女性",
                "自定义补充标签": "校园, 中景半身, 高细节",
            },
            collect_selected=lambda kwargs: (
                OrderedDict(
                    {
                        "主体": ["成年女性"],
                        "画面风格": [],
                        "成人向表达": [],
                        "光影氛围": [],
                        "构图视角": [],
                        "动作姿态": [],
                        "服装造型": [],
                        "场景背景": [],
                        "道具世界观": [],
                        "技术画质": [],
                    }
                ),
                ["校园", "中景半身", "高细节"],
            ),
            tag_group_index=lambda: {"校园": "场景背景", "中景半身": "构图视角", "高细节": "技术画质"},
            group_slot_limits={
                "主体": 4,
                "画面风格": 4,
                "成人向表达": 3,
                "光影氛围": 3,
                "构图视角": 3,
                "动作姿态": 3,
                "服装造型": 3,
                "场景背景": 3,
                "道具世界观": 3,
                "技术画质": 3,
            },
            setting_defaults={
                "模板风格": "自动",
                "主体类型": "自动",
                "案例输出结构": "自动",
                "运行时随机标签": False,
                "运行时随机模式": "全随机",
                "核心标签锁定数量": 10,
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "标签反推模式": "自动平衡",
                "生成数量": 3,
                "提示词语言": "纯中文",
                "详细度": "标准",
                "输出模式": "完整结果",
                "优先柔和肤质": False,
                "抑制文字伪影": False,
                "额外要求": "",
                "锁定标签白名单": "",
                "随机排除标签": "",
                "随机补充避重缓存": "",
                "系统提示词覆盖": "",
                "最大生成token": 960,
                "温度": 0.62,
                "top_p": 0.9,
                "top_k": 40,
                "重复惩罚": 1.08,
                "频率惩罚": 0.0,
                "存在惩罚": 0.0,
                "seed": 0,
                "输出think块": False,
            },
            safe_int=lambda value, default, low, high: max(low, min(high, int(value))),
            safe_float=lambda value, default, low, high: max(low, min(high, float(value))),
            normalize_inference_state=normalize_stub,
            collect_all_tags=lambda next_selected, next_custom: [tag for values in next_selected.values() for tag in values] + list(next_custom),
        )
        self.assertIn("中景半身", selected["构图视角"])
        self.assertNotIn("中景半身", custom_tags)
        self.assertIn("中景半身", all_tags_text)

    def test_state_builder_absorbs_groupable_custom_tags_before_normalization(self) -> None:
        captured_selected: list[OrderedDict[str, list[str]]] = []
        captured_custom_tags: list[list[str]] = []

        def normalize_probe(
            selected: OrderedDict[str, list[str]],
            custom_tags: list[str],
            settings: dict[str, object],
        ) -> tuple[OrderedDict[str, list[str]], list[str], list[str]]:
            captured_selected.append(OrderedDict((key, list(value)) for key, value in selected.items()))
            captured_custom_tags.append(list(custom_tags))
            return selected, custom_tags, []

        selected, custom_tags, _settings, all_tags_text = state_builder.build_state_from_kwargs(
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "生成数量": 1,
                "提示词语言": "纯中文",
                "详细度": "详细",
                "输出模式": "完整结果",
                "标签反推模式": "自动平衡",
                "主体标签1": "成年女性",
                "自定义补充标签": "校园, 中景半身, 高细节",
            },
            collect_selected=lambda kwargs: (
                OrderedDict(
                    {
                        "主体": ["成年女性"],
                        "画面风格": [],
                        "成人向表达": [],
                        "光影氛围": [],
                        "构图视角": [],
                        "动作姿态": [],
                        "服装造型": [],
                        "场景背景": [],
                        "道具世界观": [],
                        "技术画质": [],
                    }
                ),
                ["校园", "中景半身", "高细节"],
            ),
            tag_group_index=lambda: {"校园": "场景背景", "中景半身": "构图视角", "高细节": "技术画质"},
            group_slot_limits={
                "主体": 4,
                "画面风格": 4,
                "成人向表达": 3,
                "光影氛围": 3,
                "构图视角": 3,
                "动作姿态": 3,
                "服装造型": 3,
                "场景背景": 3,
                "道具世界观": 3,
                "技术画质": 3,
            },
            setting_defaults={
                "模板风格": "自动",
                "主体类型": "自动",
                "案例输出结构": "自动",
                "运行时随机标签": False,
                "运行时随机模式": "全随机",
                "核心标签锁定数量": 10,
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "标签反推模式": "自动平衡",
                "生成数量": 3,
                "提示词语言": "纯中文",
                "详细度": "标准",
                "输出模式": "完整结果",
                "优先柔和肤质": False,
                "抑制文字伪影": False,
                "额外要求": "",
                "锁定标签白名单": "",
                "随机排除标签": "",
                "随机补充避重缓存": "",
                "系统提示词覆盖": "",
                "最大生成token": 960,
                "温度": 0.62,
                "top_p": 0.9,
                "top_k": 40,
                "重复惩罚": 1.08,
                "频率惩罚": 0.0,
                "存在惩罚": 0.0,
                "seed": 0,
                "输出think块": False,
            },
            safe_int=lambda value, default, low, high: max(low, min(high, int(value))),
            safe_float=lambda value, default, low, high: max(low, min(high, float(value))),
            normalize_inference_state=normalize_probe,
            collect_all_tags=lambda next_selected, next_custom: [tag for values in next_selected.values() for tag in values] + list(next_custom),
        )
        self.assertEqual(len(captured_selected), 1)
        self.assertIn("中景半身", captured_selected[0]["构图视角"])
        self.assertNotIn("中景半身", captured_custom_tags[0])
        self.assertIn("中景半身", selected["构图视角"])
        self.assertNotIn("中景半身", custom_tags)
        self.assertIn("中景半身", all_tags_text)

    def test_normalizer_keeps_custom_half_body_composition_tag(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚"],
                "画面风格": [],
                "成人向表达": [],
                "光影氛围": [],
                "构图视角": [],
                "动作姿态": [],
                "服装造型": [],
                "场景背景": ["校园"],
                "道具世界观": [],
                "技术画质": ["高细节"],
            }
        )
        custom_tags = ["中景半身"]
        settings = {"模板风格": "真实感"}
        next_selected, next_custom, notes = normalizer.normalize_inference_state(
            selected,
            custom_tags,
            settings,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
            context={
                "ancient_modern_conflicts": set(),
                "humanoid_fantasy_map": {},
                "human_identity_tags": {"成年女性"},
                "sacred_scene_tags": set(),
                "private_scene_tags": set(),
                "urban_rain_scene_tags": set(),
                "ancient_scene_anchor_tags": set(),
                "ancient_scene_conflict_tags": set(),
                "ancient_style_clothing_conflicts": set(),
                "ambiguous_adult_tags": set(),
                "half_body_shot_tags": {"中景半身"},
                "full_body_motion_conflicts": {"披风扬起", "踮脚回望", "俯身前倾"},
                "strong_identity_tags": set(),
                "casual_conflict_clothing": set(),
                "clothing_core_tags": set(),
                "ancient_clothing_tags": set(),
                "modern_formal_clothing_tags": set(),
                "intimate_clothing_tags": set(),
                "emotion_cleanup_rules": [],
            },
        )
        self.assertIn("中景半身", collect_all_tags(next_selected, next_custom))
        self.assertIn("中景半身", next_custom + next_selected["构图视角"])
        self.assertEqual(notes, [])

    def test_random_theme_pool_bias_prefers_mythic_direction(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": [], "场景背景": []})
        next_style, next_selected, next_custom = module._apply_random_theme_pool_bias(
            "真实感",
            selected,
            [],
            {"随机主题池": "神话史诗"},
        )
        all_tags = [tag for values in next_selected.values() for tag in values] + list(next_custom)
        self.assertEqual(next_style, "神话感")
        self.assertIn("云海", all_tags)
        self.assertIn("神殿", all_tags)

    def test_append_tag_to_state_never_writes_unknown_value_into_dropdown_group(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        selected = OrderedDict((group_name, []) for group_name, _, _ in module._all_tag_groups())
        custom_tags = []

        module._append_tag_to_state(selected, custom_tags, "未收录的测试标签", preferred_group="光影氛围")

        self.assertNotIn("未收录的测试标签", selected["光影氛围"])
        self.assertIn("未收录的测试标签", custom_tags)

    def test_painterly_template_profile_uses_registered_light_tag(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        selected = OrderedDict((group_name, []) for group_name, _, _ in module._all_tag_groups())
        settings = {"模板风格": "插画感", "seed": 0, "unique_id": "painterly-valid-tags"}

        next_selected, next_custom = module._apply_template_style_profile_bias(
            "插画感",
            selected,
            [],
            settings,
        )

        self.assertIn("饱满色彩", module._group_tags("光影氛围"))
        self.assertIn("饱满色彩", next_selected["光影氛围"])
        self.assertNotIn("饱满色彩", next_custom)

    def test_random_theme_pool_bias_does_not_override_explicit_template_style(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        selected = OrderedDict({"主体": ["成年女性"], "画面风格": [], "场景背景": []})
        next_style, next_selected, next_custom = module._apply_random_theme_pool_bias(
            "插画感",
            selected,
            [],
            {"模板风格": "插画感", "随机主题池": "神话史诗"},
        )
        all_tags = [tag for values in next_selected.values() for tag in values] + list(next_custom)
        self.assertEqual(next_style, "插画感")
        self.assertIn("神话感", all_tags)
        self.assertIn("神殿", all_tags)

    def test_random_theme_pool_bias_rotates_with_runtime_history(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        node_id = "theme-pool-rotate"
        selected = OrderedDict((group_name, []) for group_name, _, _ in module._all_tag_groups())
        selected["主体"] = ["成年女性"]
        settings = {"模板风格": "自动", "随机主题池": "古风园林", "seed": 0, "unique_id": node_id}
        _style, first_selected, first_custom = module._apply_random_theme_pool_bias(
            "真实感",
            selected,
            [],
            settings,
        )
        first_tags = collect_all_tags(first_selected, first_custom)
        module._update_runtime_random_history(
            node_id,
            selected=first_selected,
            custom_tags=first_custom,
            generated=[],
            prompt_list=[],
            extra_markers=list(settings.get("随机主题池档案标记", [])),
        )
        second_settings = {"模板风格": "自动", "随机主题池": "古风园林", "seed": 0, "unique_id": node_id}
        _style, second_selected, second_custom = module._apply_random_theme_pool_bias(
            "真实感",
            selected,
            [],
            second_settings,
        )
        second_tags = collect_all_tags(second_selected, second_custom)
        self.assertNotEqual(set(first_tags) & {"月洞门", "水榭", "竹林", "月下庭院", "回廊"}, set(second_tags) & {"月洞门", "水榭", "竹林", "月下庭院", "回廊"})
        self.assertTrue(second_settings.get("随机主题池档案标记"))
        self.assertTrue(any(str(marker).startswith("variant:古风园林:") for marker in second_settings.get("随机主题池档案标记", [])))

    def test_random_theme_pool_bias_supports_new_mecha_track(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        selected = OrderedDict((group_name, []) for group_name, _, _ in module._all_tag_groups())
        settings = {"模板风格": "自动", "随机主题池": "机甲科幻", "seed": 0, "unique_id": "theme-pool-mecha"}
        next_style, next_selected, next_custom = module._apply_random_theme_pool_bias(
            "真实感",
            selected,
            [],
            settings,
        )
        all_tags = collect_all_tags(next_selected, next_custom)
        self.assertEqual(next_style, "CG感")
        self.assertTrue(any(tag in all_tags for tag in ("工程机甲", "侦查机甲", "机械外骨骼", "透明头盔", "装甲靴")))
        self.assertTrue(any(tag in all_tags for tag in ("机库", "实验室", "战术整备间", "飞船走廊", "地下基地")))
        self.assertTrue(any(str(marker).startswith("variant:机甲科幻:") for marker in settings.get("随机主题池档案标记", [])))

    def test_template_style_profile_bias_rotates_with_runtime_history(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        node_id = "template-style-profile-rotate"
        selected = OrderedDict((group_name, []) for group_name, _, _ in module._all_tag_groups())
        settings = {"模板风格": "商业摄影", "seed": 0, "unique_id": node_id}
        first_selected, first_custom = module._apply_template_style_profile_bias(
            "商业摄影",
            selected,
            [],
            settings,
        )
        first_markers = list(settings.get("模板风格档案标记", []))
        module._update_runtime_random_history(
            node_id,
            selected=first_selected,
            custom_tags=first_custom,
            generated=[],
            prompt_list=[],
            extra_markers=first_markers,
        )
        second_settings = {"模板风格": "商业摄影", "seed": 0, "unique_id": node_id}
        second_selected, second_custom = module._apply_template_style_profile_bias(
            "商业摄影",
            selected,
            [],
            second_settings,
        )
        first_signature = next(marker for marker in first_markers if str(marker).startswith("stylevariant:"))
        second_signature = next(marker for marker in second_settings.get("模板风格档案标记", []) if str(marker).startswith("stylevariant:"))
        self.assertNotEqual(first_signature, second_signature)
        self.assertTrue(set(collect_all_tags(first_selected, first_custom)) & {"商业广告大片", "品牌大片", "Lookbook", "产品广告", "中画幅"})
        self.assertTrue(set(collect_all_tags(second_selected, second_custom)) & {"商业广告大片", "品牌大片", "Lookbook", "产品广告", "中画幅"})

    def test_preview_state_applies_template_style_profile_bias(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module.构建运行时随机预览状态(
            {
                "selected": {},
                "customTags": [],
                "settings": {
                    "模板风格": "东方赛博",
                    "主体类型": "人物角色",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": False,
                    "随机主题池": "自动",
                    "seed": 0,
                    "unique_id": "preview-template-style-profile",
                },
            }
        )
        all_tags = collect_all_tags(OrderedDict(result["selected"]), result["customTags"])
        self.assertTrue(any(tag in all_tags for tag in ("东方赛博武侠朋克", "东方赛博机甲", "机能赛博", "赛博雨夜")))
        self.assertTrue(any(str(marker).startswith("stylevariant:东方赛博:") for marker in result["settings"].get("模板风格档案标记", [])))

    def test_style_track_preserves_new_template_style_as_track(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        self.assertEqual(module._style_track("电影写实", []), "电影写实")
        self.assertEqual(module._style_track("国风电影", []), "国风电影")

    def test_preview_state_runs_skill_for_manual_positive_tags(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module.构建运行时随机预览状态(
            {
                "selected": {
                    "画面风格": ["自然写实图像", "真实感", "照片级", "杂志编辑摄影"],
                    "构图视角": ["全景全身", "人物完整入镜", "全身"],
                    "技术画质": ["16K", "8K", "高质量", "高细节", "材质细节丰富"],
                },
                "customTags": "True, 保留自定义",
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": False,
                },
            }
        )
        selected = result["selected"]
        all_tags = [tag for values in selected.values() for tag in values] + result["customTags"]
        self.assertEqual(selected["画面风格"], ["真实感", "照片级", "杂志编辑摄影"])
        self.assertEqual(selected["构图视角"], ["全景全身", "人物完整入镜"])
        self.assertEqual(selected["技术画质"], ["16K", "高质量", "高细节", "材质细节丰富"])
        self.assertNotIn("True", all_tags)
        self.assertIn("保留自定义", result["customTags"])
        self.assertTrue(any("Skill重复收敛" in note for note in result["meta"]["normalization_notes"]))

    def test_preview_state_applies_random_theme_pool_bias(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module.构建运行时随机预览状态(
            {
                "selected": {},
                "customTags": [],
                "settings": {
                    "模板风格": "自动",
                    "主体类型": "人物角色",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": False,
                    "随机主题池": "海岸假日",
                    "seed": 0,
                    "unique_id": "preview-theme-pool",
                },
            }
        )
        all_tags = collect_all_tags(OrderedDict(result["selected"]), result["customTags"])
        self.assertTrue(any(tag in all_tags for tag in ("沙滩", "海边栈道", "礁石海岸", "海边公路", "白色阳台")))
        self.assertTrue(any(tag in all_tags for tag in ("日落逆光", "蓝调时刻", "冷色调", "高饱和", "清晨柔光")))
        self.assertTrue(set(result["_randomSupplementTags"]) & set(all_tags))

    def test_preview_state_runs_skill_after_runtime_random_tags(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()

        def random_stub(selected, custom_tags, settings):
            next_selected = OrderedDict((name, list(tags)) for name, tags in selected.items())
            next_selected["画面风格"] = ["自然写实图像", "真实感", "照片级", "杂志编辑摄影"]
            next_selected["构图视角"] = ["全景全身", "人物完整入镜", "全身"]
            next_custom = list(custom_tags) + ["True"]
            return next_selected, next_custom, ["自然写实图像", "真实感", "照片级", "杂志编辑摄影", "全身", "True"]

        module._build_runtime_tags = random_stub
        result = module.构建运行时随机预览状态(
            {
                "selected": {},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "标签反推模式": "自动平衡",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "中",
                },
            }
        )
        selected = result["selected"]
        generated = result["meta"]["runtime_random_generated_tags"]
        self.assertEqual(selected["画面风格"], ["真实感", "照片级", "杂志编辑摄影"])
        self.assertEqual(selected["构图视角"], ["全景全身", "人物完整入镜"])
        self.assertNotIn("自然写实图像", generated)
        self.assertNotIn("全身", generated)
        self.assertNotIn("True", generated)
        self.assertTrue(any("Skill重复收敛" in note for note in result["meta"]["normalization_notes"]))

    def test_stage_output_cache_hides_runtime_random_history_markers(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        node_id = "runtime-history-cache"
        module._update_runtime_random_history(
            node_id,
            selected=OrderedDict({"主体": ["炎魔天使"]}),
            custom_tags=[],
            generated=["炎魔天使"],
            prompt_list=["炎魔天使 standing in frame"],
        )
        module._cache_output(node_id, {"prompt_text": "demo prompt"})
        cache = module.获取阶段节点输出缓存(node_id)
        self.assertIsNotNone(cache)
        self.assertEqual(cache, {"prompt_text": "demo prompt"})
        self.assertNotIn("recent_runtime_markers", cache)
        self.assertIn("tag:炎魔天使", module._random_history(node_id))

    def test_stage_output_cache_whitelists_and_deep_copies_large_internal_bucket(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        node_id = "public-stage-output-cache"
        public_payload = module._build_cache_payload_impl(
            full_text="full",
            primary_prompt="public prompt",
            prompt_only="public prompt",
            prompt_collection="collection",
            selected_tags_text="tags",
            json_result=json.dumps({"normalization_notes": ["public note"]}, ensure_ascii=False),
            negative_prompt="negative",
            style_track="style",
            smart_text_prompt="smart",
        )
        self.assertEqual(set(public_payload), set(module._STAGE_OUTPUT_CACHE_PUBLIC_KEYS))
        module._cache_output(node_id, {**public_payload, "private_probe": "must not escape"})
        with module._CACHE_LOCK:
            bucket = module._cache_bucket_unlocked(node_id)
            self.assertIsNotNone(bucket)
            bucket["strict_prompt_dedupe"] = {
                "channels": {
                    "prompt": {"hashes": [f"{index:064x}" for index in range(2048)]},
                }
            }
            bucket["recent_runtime_markers"] = [f"marker-{index}" for index in range(2048)]
            bucket["recent_prompt_signatures"] = [f"signature-{index}" for index in range(2048)]

        first = module.获取阶段节点输出缓存(node_id)
        self.assertEqual(first, public_payload)
        self.assertNotIn("strict_prompt_dedupe", first)
        self.assertNotIn("recent_runtime_markers", first)
        self.assertNotIn("recent_prompt_signatures", first)
        self.assertNotIn("private_probe", first)

        first["normalization_notes"].append("caller mutation")
        first["outputs"][0] = "caller mutation"
        second = module.获取阶段节点输出缓存(node_id)
        self.assertEqual(second, public_payload)

    def test_runtime_random_history_extracts_prompt_scene_outfit_action_and_light(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        markers = module._runtime_random_markers_from_prompt([
            "商业广告大片，成年女性，银白长发，修身礼服，摄影棚，回眸，风暴天光，书本，高细节"
        ])
        self.assertIn("tag:银白长发", markers)
        self.assertIn("identity:银白长发", markers)
        self.assertIn("tag:修身礼服", markers)
        self.assertIn("outfit:修身礼服", markers)
        self.assertIn("tag:摄影棚", markers)
        self.assertIn("scene:摄影棚", markers)
        self.assertIn("tag:回眸", markers)
        self.assertIn("action:回眸", markers)
        self.assertIn("tag:风暴天光", markers)
        self.assertIn("light:风暴天光", markers)

    def test_prompt_history_fingerprints_are_saved_for_future_runs(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        node_id = "prompt-history-fingerprint"
        saved = module._update_prompt_history(
            node_id,
            ["商业广告大片，银白长发，修身礼服，摄影棚，回眸，风暴天光，高细节"],
        )
        self.assertTrue(saved)
        self.assertEqual(module._prompt_history_fingerprints(node_id), saved)
        self.assertTrue(any(item in module._random_history(node_id) for item in saved))

    def test_prompt_history_records_visual_and_tag_markers_for_anti_repeat(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        node_id = "prompt-history-visual-markers"
        saved = module._update_prompt_history(
            node_id,
            ["商业广告大片，银白长发，修身礼服，摄影棚，回眸，风暴天光，书本，高细节"],
        )
        self.assertTrue(any(str(item).startswith("visual:") for item in saved))
        self.assertIn("tag:摄影棚", saved)
        self.assertIn("scene:摄影棚", saved)
        self.assertIn("outfit:修身礼服", saved)
        self.assertIn("action:回眸", saved)

    def test_runtime_random_preserve_core_keeps_subject_and_scene_anchor(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "清冷"],
                "场景背景": ["校园"],
                "构图视角": ["中景半身"],
                "画面风格": ["真实感"],
            }
        )
        settings = {
            "运行时随机模式": "保留已选核心标签",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "核心标签锁定数量": 6,
            "锁定标签白名单": "",
            "随机排除标签": "",
            "随机补充避重缓存": "",
            "seed": 42,
            "unique_id": "auto-pool-anchor",
        }
        groups = [
            ("主体", 4, ["无", "成年女性", "东亚", "清冷", "偶像", "调酒师"]),
            ("场景背景", 3, ["无", "校园", "街道", "神殿", "机库"]),
            ("构图视角", 3, ["无", "中景半身", "近景", "全身"]),
            ("画面风格", 3, ["无", "真实感", "杂志感", "电影剧照"]),
        ]
        result_selected, result_custom, generated = randomizer.build_runtime_tags(
            selected,
            [],
            settings,
            all_tag_groups=lambda: groups,
            tag_group_index=lambda: {
                "成年女性": "主体",
                "东亚": "主体",
                "清冷": "主体",
                "偶像": "主体",
                "调酒师": "主体",
                "校园": "场景背景",
                "街道": "场景背景",
                "神殿": "场景背景",
                "机库": "场景背景",
                "中景半身": "构图视角",
                "近景": "构图视角",
                "全身": "构图视角",
                "真实感": "画面风格",
                "杂志感": "画面风格",
                "电影剧照": "画面风格",
            },
            parse_tags=lambda value: [],
            uniq=uniq,
            seed_normalizer=lambda value: int(value),
            history_loader=lambda _node_id: [],
            random_module=random,
            empty_tag="无",
        )
        self.assertIn("成年女性", result_selected["主体"])
        self.assertIn("东亚", result_selected["主体"])
        self.assertIn("清冷", result_selected["主体"])
        self.assertIn("校园", result_selected["场景背景"])
        self.assertIn("中景半身", result_selected["构图视角"])
        self.assertIn("真实感", result_selected["画面风格"])
        self.assertLessEqual(len(result_selected["主体"]), 10)
        self.assertLessEqual(len(result_selected["场景背景"]), 10)
        self.assertLessEqual(len(result_selected["构图视角"]), 10)
        self.assertLessEqual(len(result_selected["画面风格"]), 10)
        self.assertTrue(generated)
        self.assertTrue(any(tag not in {"成年女性", "东亚", "清冷", "校园", "中景半身", "真实感"} for tag in generated))
        self.assertEqual(result_custom, [])

    def test_prompt_builder_auto_pool_variants_keep_scene_fixed_while_style_fragments_shift(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "清冷"],
                "场景背景": ["校园"],
                "构图视角": ["中景半身"],
                "技术画质": ["高细节"],
            }
        )
        realistic_prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "生成数量": 1,
                "额外要求": "",
            },
            scene_group="city",
            identity="成年女性",
            style_track="写实人像",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        cg_prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "CG感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "生成数量": 1,
                "额外要求": "",
            },
            scene_group="city",
            identity="成年女性",
            style_track="工业科幻",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        for prompt in (realistic_prompt, cg_prompt):
            self.assertIn("校园", prompt)
            self.assertIn("成年女性", prompt)
            self.assertIn("中景半身", prompt)
        self.assertTrue(any(term in realistic_prompt for term in ["写实摄影", "时装广告大片", "杂志编辑摄影"]))
        self.assertTrue(any(term in cg_prompt for term in ["电影级CG", "概念设计稿", "虚幻引擎渲染", "Octane渲染"]))
        self.assertNotEqual(realistic_prompt, cg_prompt)

    def test_prompt_builder_auto_pool_five_mode_keeps_same_bone_and_mode_cores(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "清冷"],
                "场景背景": ["校园"],
                "构图视角": ["中景半身"],
                "技术画质": ["高细节"],
            }
        )
        settings_base = {
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "生成数量": 1,
            "额外要求": "",
        }
        expectations = {
            "真实感": {
                "must_have_any": ["写实摄影", "时装广告大片", "杂志编辑摄影", "纪实抓拍"],
                "must_not_have": ["OVA风", "赛璐璐", "虚幻引擎", "神殿", "古风建筑"],
            },
            "插画感": {
                "must_have_any": ["高完成度插画", "厚涂插画", "水彩线稿", "复古未来动漫", "OVA风"],
                "must_not_have": ["raw photo", "纪实抓拍", "虚幻引擎", "神殿", "古风建筑"],
            },
            "CG感": {
                "must_have_any": ["电影级CG", "概念设计稿", "虚幻引擎渲染", "Octane渲染", "PBR渲染"],
                "must_not_have": ["水彩", "赛璐璐", "神殿", "古风建筑"],
            },
            "古风": {
                "must_have_any": ["古风人像", "古风电影剧照", "工笔重彩", "玄幻古风", "水墨写意"],
                "must_not_have": ["虚幻引擎", "未来都市", "机库", "神殿"],
            },
            "神话感": {
                "must_have_any": ["神话史诗感", "神圣史诗", "魔幻现实主义", "暗黑奇幻", "冰雪奇幻"],
                "must_not_have": ["虚幻引擎", "未来都市", "机库", "古风建筑"],
            },
        }
        prompts: dict[str, str] = {}
        for style, rules in expectations.items():
            prompt = prompt_builder.build_prompt_list(
                selected,
                [],
                {**settings_base, "模板风格": style},
                scene_group="",
                identity="",
                style_track=style,
                recent_tracks=[],
                uniq=uniq,
                infer_template_style=lambda tags, explicit: explicit,
                infer_subject_type=lambda tags, explicit: explicit,
                infer_output_structure=lambda subject, explicit: explicit,
            )[0]
            prompts[style] = prompt
            self.assertIn("成年女性", prompt)
            self.assertIn("校园", prompt)
            self.assertIn("中景半身", prompt)
            self.assertTrue(any(term in prompt for term in rules["must_have_any"]))
            for banned in rules["must_not_have"]:
                self.assertNotIn(banned, prompt)
        self.assertEqual(len(set(prompts.values())), 5)

    def test_prompt_builder_auto_pool_filters_mode_noise_and_scene_drift(self) -> None:
        settings_base = {
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "生成数量": 1,
            "额外要求": "保持校园单一主场景，不要切到室内棚拍或夜场，不要任何文字元素。",
        }
        cases = {
            "真实感": {
                "selected_style": ["二次元", "水彩线稿"],
                "selected_light": ["阴天"],
                "identity": "成年女性",
                "scene_group": "city",
                "style_track": "写实人像",
                "must_have_any": ["写实摄影", "时装广告大片", "杂志编辑摄影", "纪实抓拍"],
                "must_not_have": ["二次元", "水彩线稿", "摄影棚", "影棚纯色背景", "夜店", "街景"],
            },
            "CG感": {
                "selected_style": ["版画", "Q版"],
                "selected_light": ["冷白皮"],
                "identity": "机械师",
                "scene_group": "industrial",
                "style_track": "工业科幻",
                "must_have_any": ["电影级CG", "概念设计稿", "虚幻引擎渲染", "Octane渲染", "PBR渲染"],
                "must_not_have": ["版画", "Q版", "机库", "维修车间", "机械结构与空间透视"],
            },
            "古风": {
                "selected_style": ["杂志感", "轻熟感"],
                "selected_light": ["钨丝灯实景光", "窗边光"],
                "identity": "神女",
                "scene_group": "ancient",
                "style_track": "古风园林",
                "must_have_any": ["古风人像", "古风电影剧照", "工笔重彩", "玄幻古风", "水墨写意"],
                "must_not_have": ["杂志感", "轻熟感", "钨丝灯实景光", "窗边光", "古典空间语义"],
            },
            "神话感": {
                "selected_style": ["赛璐璐画风", "水墨水彩融合"],
                "selected_light": ["广告屏反射光"],
                "identity": "神女",
                "scene_group": "sacred",
                "style_track": "神殿史诗",
                "must_have_any": ["神话史诗感", "神圣史诗", "魔幻现实主义", "暗黑奇幻", "冰雪奇幻"],
                "must_not_have": ["赛璐璐画风", "水墨水彩融合", "广告屏反射光", "神殿", "云海", "仪式空间感"],
            },
        }
        for style, case in cases.items():
            with self.subTest(style=style):
                selected = OrderedDict(
                    {
                        "主体": ["成年女性", "东亚", "清冷"],
                        "画面风格": list(case["selected_style"]),
                        "场景背景": ["校园"],
                        "光影氛围": list(case["selected_light"]),
                        "构图视角": ["中景半身"],
                        "技术画质": ["高细节"],
                    }
                )
                prompt = prompt_builder.build_prompt_list(
                    selected,
                    [],
                    {**settings_base, "模板风格": style},
                    scene_group=str(case["scene_group"]),
                    identity=str(case["identity"]),
                    style_track=str(case["style_track"]),
                    recent_tracks=[],
                    uniq=uniq,
                    infer_template_style=lambda tags, explicit: explicit,
                    infer_subject_type=lambda tags, explicit: explicit,
                    infer_output_structure=lambda subject, explicit: explicit,
                )[0]
                self.assertIn("成年女性", prompt)
                self.assertIn("东亚", prompt)
                self.assertIn("清冷", prompt)
                self.assertIn("校园", prompt)
                self.assertIn("中景半身", prompt)
                self.assertTrue(any(term in prompt for term in case["must_have_any"]))
                for banned in case["must_not_have"]:
                    self.assertNotIn(banned, prompt)

    def test_prompt_builder_style_noise_filter_keeps_negative_constraints(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "画面风格": ["二次元", "水彩线稿"],
                "场景背景": ["校园"],
                "构图视角": ["中景半身"],
            }
        )
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": False,
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "生成数量": 1,
                "额外要求": "不要二次元，不要水彩线稿，保持真实摄影。",
            },
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        fragments = [fragment.strip() for fragment in prompt.split("，") if fragment.strip()]
        self.assertNotIn("二次元", fragments)
        self.assertNotIn("水彩线稿", fragments)
        self.assertIn("不要二次元", prompt)
        self.assertIn("不要水彩线稿", prompt)

    def test_prompt_builder_uses_world_and_adult_tag_groups(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性"],
                "成人向表达": ["暧昧"],
                "服装造型": ["丝质睡袍"],
                "场景背景": ["酒店套房"],
                "道具世界观": ["红酒杯"],
                "构图视角": ["中景半身"],
                "技术画质": ["高细节"],
            }
        )
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "成人向成熟",
                "运行时随机标签": False,
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "生成数量": 1,
                "额外要求": "",
            },
            scene_group="private",
            identity="成年女性",
            style_track="私房写实",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("暧昧", prompt)
        self.assertIn("红酒杯", prompt)
        self.assertIn("丝质睡袍", prompt)
        self.assertIn("酒店套房", prompt)

    def test_prompt_builder_keeps_core_tags_when_fragment_budget_is_crowded(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "清冷", "摄影师"],
                "画面风格": ["真实感", "杂志感", "电影剧照", "生活方式广告"],
                "成人向表达": ["暧昧", "微醺感", "成熟"],
                "服装造型": ["白衬衫", "长款风衣", "皮革腰带"],
                "场景背景": ["校园", "图书馆", "雨巷"],
                "道具世界观": ["相机", "胶片卷", "旧书"],
                "光影氛围": ["自然光", "侧逆光", "阴天"],
                "构图视角": ["中景半身", "低角度", "浅景深"],
                "动作姿态": ["回眸", "手持相机", "站姿"],
                "技术画质": ["高细节", "8K", "胶片颗粒"],
            }
        )
        custom_tags = [f"自定义补充{i}" for i in range(1, 18)]
        prompt = prompt_builder.build_prompt_list(
            selected,
            custom_tags,
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "高密度站点",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "随机主题池": "自动",
                "生成数量": 1,
                "额外要求": "固定校园图书馆主场景，不要文字水印。",
            },
            scene_group="indoor",
            identity="摄影师",
            style_track="写实人像",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        fragments = [fragment.strip() for fragment in prompt.split("，") if fragment.strip()]
        self.assertLessEqual(len(fragments), 34)
        for required in ("成年女性", "校园", "中景半身", "暧昧", "相机", "固定校园图书馆主场景"):
            self.assertIn(required, prompt)
        self.assertIn("自定义补充1", prompt)
        self.assertNotIn("自定义补充17", prompt)

    def test_prompt_builder_cg_mode_avoids_ancient_and_illustration_core_pollution(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "清冷"],
                "场景背景": ["校园"],
                "构图视角": ["中景半身"],
                "技术画质": ["高细节"],
            }
        )
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "CG感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "生成数量": 1,
                "额外要求": "",
            },
            scene_group="industrial",
            identity="机械师",
            style_track="工业科幻",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("成年女性", prompt)
        self.assertIn("校园", prompt)
        self.assertIn("中景半身", prompt)
        self.assertTrue(any(term in prompt for term in ["电影级CG", "概念设计稿", "虚幻引擎渲染", "Octane渲染", "PBR渲染", "CG感"]))
        for banned in ("宋韵", "汉服", "神殿", "云海", "OVA风", "水彩线稿", "赛璐璐"):
            self.assertNotIn(banned, prompt)

    def test_prompt_builder_myth_mode_keeps_literal_adult_female_anchor(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "清冷"],
                "场景背景": ["校园"],
                "构图视角": ["中景半身"],
                "技术画质": ["高细节"],
            }
        )
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "神话感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "运行时随机标签": True,
                "运行时随机模式": "全随机",
                "运行时随机强度": "中",
                "随机主题池": "自动",
                "生成数量": 1,
                "额外要求": "",
            },
            scene_group="sacred",
            identity="神女",
            style_track="神殿史诗",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("成年女性", prompt)
        self.assertIn("校园", prompt)
        self.assertIn("中景半身", prompt)
        self.assertTrue(any(term in prompt for term in ["神话史诗感", "神圣史诗", "魔幻现实主义", "暗黑奇幻", "冰雪奇幻", "神话感"]))

    def test_prompt_builder_format_sections_keeps_collection_separate_from_primary_prompt(self) -> None:
        prompt_list = [
            "时装广告大片，成年女性，摄影棚，近景",
            "黑白摄影，成年女性，街道，中景半身",
            "杂志编辑摄影，成年女性，酒吧，全身",
        ]
        full_text, prompt_collection = prompt_builder.format_sections(prompt_list, "使用标签：成年女性")
        self.assertEqual(prompt_collection, "\n\n".join(prompt_list))
        self.assertEqual(prompt_collection.split("\n\n")[0], prompt_list[0])
        self.assertNotEqual(prompt_collection, prompt_list[0])
        self.assertIn(prompt_list[0], full_text)
        self.assertIn(prompt_list[1], full_text)

    def test_prompt_builder_pure_english_localizes_positive_prompt(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "清晰下颌线", "黑发"],
                "服装造型": ["短靴", "缎面"],
                "场景背景": ["卧室", "落地窗"],
                "构图视角": ["中景半身", "脚部完整入镜", "自然透视"],
                "动作姿态": ["看向镜头", "手部姿态自然"],
                "光影氛围": ["柔光"],
                "技术画质": ["高细节", "双眼清晰"],
            }
        )
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "生成数量": 1,
                "额外要求": "",
                "提示词语言": "纯英文",
            },
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("realistic photography", prompt)
        self.assertIn("adult woman", prompt)
        self.assertIn("East Asian", prompt)
        self.assertIn("defined jawline", prompt)
        self.assertIn("black hair", prompt)
        self.assertIn("ankle boots", prompt)
        self.assertIn("satin fabric", prompt)
        self.assertIn("bedroom", prompt)
        self.assertIn("floor-to-ceiling window", prompt)
        self.assertIn("medium half-body shot", prompt)
        self.assertIn("feet fully in frame", prompt)
        self.assertIn("natural perspective", prompt)
        self.assertIn("looking at the camera", prompt)
        self.assertIn("natural hand pose", prompt)
        self.assertIn("soft light", prompt)
        self.assertIn("high detail", prompt)
        self.assertIn("sharp eyes", prompt)
        self.assertIsNone(re.search(r"[\u4e00-\u9fff]", prompt))

    def test_prompt_builder_pure_english_localizes_reference_vocabulary(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚"],
                "画面风格": ["35mm胶片摄影", "大画幅棚拍"],
                "光影氛围": ["黄金时刻侧光", "蓝灰月光"],
                "构图视角": ["俯视平铺", "200mm长焦压缩"],
                "技术画质": ["中画幅质感", "哑光陶瓷"],
            }
        )
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "生成数量": 1,
                "额外要求": "",
                "提示词语言": "纯英文",
            },
            scene_group="",
            identity="",
            style_track="商业摄影",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("35mm film photograph", prompt)
        self.assertIn("large-format studio photo", prompt)
        self.assertIn("golden-hour side-light", prompt)
        self.assertIn("blue-grey moonlight", prompt)
        self.assertIn("top-down flat-lay composition", prompt)
        self.assertIn("200mm long-lens compression", prompt)

    def test_prompt_builder_pure_english_localizes_reference_patina_vocabulary(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚"],
                "画面风格": ["港式武侠胶片"],
                "光影氛围": ["红雾表现主义打光", "青蓝冷雾"],
                "构图视角": ["变形宽银幕"],
                "技术画质": ["复古非镀膜镜头", "RGB轻微分离", "轻微色差", "柔和光晕", "老胶片褪色感", "港片胶片质感"],
            }
        )
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "生成数量": 1,
                "额外要求": "",
                "提示词语言": "纯英文",
            },
            scene_group="ancient",
            identity="",
            style_track="东方古风武侠",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("Hong Kong wuxia film stock look", prompt)
        self.assertIn("red-mist expressionist lighting", prompt)
        self.assertIn("blue-cyan cold mist", prompt)
        self.assertIn("anamorphic widescreen framing", prompt)
        self.assertIn("vintage uncoated glass lens", prompt)
        self.assertIn("subtle RGB split", prompt)
        self.assertIn("slight chromatic aberration", prompt)
        self.assertIn("soft halation", prompt)
        self.assertIn("faded old-film patina", prompt)

    def test_prompt_builder_pure_english_localizes_extended_runtime_diversity_terms(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚", "国潮模特"],
                "服装造型": ["修身礼服", "机能外套"],
                "场景背景": ["极简白棚", "便利店门口", "冷雾古巷", "赛博地铁"],
                "光影氛围": ["高窗冷天光", "冷白极简棚拍", "暖褪色胶片", "冷雾惊悚侧光"],
                "动作姿态": ["扶剑而立"],
                "道具世界观": ["神谕石碑"],
            }
        )
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "生成数量": 1,
                "额外要求": "",
                "提示词语言": "纯英文",
            },
            scene_group="city",
            identity="",
            style_track="时尚编辑商业广告",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("fashion model from Chinese chic styling", prompt)
        self.assertIn("tailored evening dress", prompt)
        self.assertIn("functional techwear jacket", prompt)
        self.assertIn("minimal white studio set", prompt)
        self.assertIn("cyber subway", prompt)
        self.assertIn("cool skylight from a high window", prompt)
        self.assertIn("cold-white minimalist studio lighting", prompt)
        self.assertIn("warm faded film palette", prompt)
        self.assertIn("standing with a sword in hand", prompt)
        self.assertIn("oracle stone stele", prompt)

    def test_prompt_builder_translates_extended_runtime_diversity_terms_directly(self) -> None:
        expectations = {
            "国潮模特": "fashion model from Chinese chic styling",
            "修身礼服": "tailored evening dress",
            "机能外套": "functional techwear jacket",
            "便利店门口": "convenience store entrance",
            "冷雾古巷": "cold-fog alley",
            "赛博地铁": "cyber subway",
            "高窗冷天光": "cool skylight from a high window",
            "冷白极简棚拍": "cold-white minimalist studio lighting",
            "暖褪色胶片": "warm faded film palette",
            "冷雾惊悚侧光": "cold-fog thriller sidelight",
            "扶剑而立": "standing with a sword in hand",
            "神谕石碑": "oracle stone stele",
            "偶像": "idol",
            "摄影师": "photographer",
            "调酒师": "bartender",
            "书店女孩": "bookstore girl",
            "独立书店": "independent bookstore",
            "影棚纯色背景": "clean studio backdrop",
            "雨后街头": "street after rain",
            "霓虹街区": "neon district",
            "工业废墟": "industrial ruins",
            "白色斗篷": "white cloak",
            "黑金重甲": "black-and-gold heavy armor",
            "银白雕花重甲": "silver-white engraved heavy armor",
            "神圣骑士": "holy knight",
            "冰霜骑士": "frost knight",
            "炎魔天使": "infernal angel",
            "神女": "goddess",
            "祭司": "priestess",
            "魔女": "sorceress",
            "女冒险者": "female adventurer",
            "古建道场": "ancient training hall",
            "月下庭院": "moonlit courtyard",
            "神圣祭坛": "sacred altar",
            "星海神殿": "star-sea temple",
            "露背礼服": "backless gown",
            "银白长发": "long silver-white hair",
            "中分短发": "center-parted short hair",
            "古风建筑": "classical Chinese architecture",
            "宗教圣所": "religious sanctuary",
            "咖啡厅": "cafe",
            "画室": "art studio",
            "飞鱼服": "flying fish robe",
            "宽袖法袍": "wide-sleeved ceremonial robe",
            "劲装": "martial outfit",
            "手持相机": "holding a camera",
            "城市屋顶纪实": "urban rooftop documentary mood",
            "城市天台": "city rooftop",
            "屋顶晾衣架": "rooftop clothesline frame",
            "日落逆光": "sunset backlight",
            "金色侧逆光": "golden rim sidelight",
            "有线耳机": "wired earphones",
            "侧脸构图": "profile composition",
            "负空间留白": "negative space breathing room",
            "山谷圣城": "holy city in a mountain valley",
            "巨构神殿": "megastructure temple",
            "瀑布峡谷": "waterfall canyon",
            "远山雪峰": "snow peaks in the far distance",
            "史诗城市中轴": "epic city central axis",
            "山体建筑一体化": "mountain-integrated architecture",
            "中轴对称巨构": "axial symmetric megastructure framing",
            "超广角全景": "ultra-wide panoramic framing",
            "树灵巨像": "colossal tree spirit",
            "古木守卫": "ancient wood guardian",
            "藤蔓木妖": "vinebound wood fiend",
            "工业舱室": "industrial chamber",
            "巨物压迫近景": "intimidating colossal close shot",
            "朽木树皮纹理": "rotted bark texture",
            "苔藓附生质感": "moss-covered overgrowth texture",
            "发光裂隙": "glowing fissures",
        }
        for source, target in expectations.items():
            with self.subTest(source=source):
                self.assertEqual(prompt_builder._translate_prompt_fragment(source), target)

    def test_prompt_builder_reference_track_overrides_keep_style_tracks_separate(self) -> None:
        settings_base = {
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "生成数量": 1,
            "额外要求": "",
        }
        cases = {
            "都市电影人文": {
                "template_style": "真实感",
                "scene_group": "city",
                "identity": "",
                "selected": OrderedDict(
                    {
                        "主体": ["成年女性", "东亚", "清冷"],
                        "场景背景": ["街道"],
                        "构图视角": ["中景半身"],
                        "技术画质": ["高细节"],
                    }
                ),
                "must_have_any": ["都市电影人文", "纪实电影摄影", "35mm胶片摄影"],
                "must_not_have": ["时装广告大片", "高端时尚编辑肖像", "港式武侠"],
            },
            "时尚编辑商业广告": {
                "template_style": "真实感",
                "scene_group": "minimal",
                "identity": "",
                "selected": OrderedDict(
                    {
                        "主体": ["成年女性", "东亚", "优雅"],
                        "场景背景": ["影棚纯色背景"],
                        "构图视角": ["中景半身"],
                        "技术画质": ["高细节"],
                    }
                ),
                "must_have_any": ["高端时尚编辑肖像", "杂志编辑摄影", "大画幅棚拍"],
                "must_not_have": ["纪实抓拍", "港式武侠", "志怪古风"],
            },
            "东方古风武侠": {
                "template_style": "古风",
                "scene_group": "ancient",
                "identity": "",
                "selected": OrderedDict(
                    {
                        "主体": ["成年女性", "东亚", "英气"],
                        "场景背景": ["竹林"],
                        "构图视角": ["全景全身"],
                        "技术画质": ["高细节"],
                    }
                ),
                "must_have_any": ["港式武侠", "港式武侠胶片", "35mm胶片摄影"],
                "must_not_have": ["园林仕女", "高端时尚编辑肖像", "都市电影人文"],
            },
            "国风暗黑志怪": {
                "template_style": "古风",
                "scene_group": "ancient",
                "identity": "",
                "selected": OrderedDict(
                    {
                        "主体": ["成年女性", "东亚", "神秘"],
                        "场景背景": ["废弃教堂"],
                        "构图视角": ["过肩镜头"],
                        "技术画质": ["高细节"],
                    }
                ),
                "must_have_any": ["志怪古风", "雾景实拍感", "黑色电影硬光"],
                "must_not_have": ["园林仕女", "大画幅棚拍", "高端时尚编辑肖像"],
            },
            "东方赛博武侠朋克": {
                "template_style": "CG感",
                "scene_group": "city",
                "identity": "",
                "selected": OrderedDict(
                    {
                        "主体": ["成年女性", "东亚", "冷艳"],
                        "场景背景": ["赛博街区"],
                        "构图视角": ["全景全身"],
                        "技术画质": ["高细节"],
                    }
                ),
                "must_have_any": ["东方赛博机甲", "机能赛博", "能量刀", "全息界面"],
                "must_not_have": ["园林仕女", "私房写真", "都市电影人文"],
            },
        }
        for style_track, case in cases.items():
            with self.subTest(style_track=style_track):
                prompt = prompt_builder.build_prompt_list(
                    case["selected"],
                    [],
                    {**settings_base, "模板风格": case["template_style"]},
                    scene_group=str(case["scene_group"]),
                    identity=str(case["identity"]),
                    style_track=style_track,
                    recent_tracks=[],
                    uniq=uniq,
                    infer_template_style=lambda tags, explicit: explicit,
                    infer_subject_type=lambda tags, explicit: explicit,
                    infer_output_structure=lambda subject, explicit: explicit,
                )[0]
                self.assertTrue(any(term in prompt for term in case["must_have_any"]))
                for banned in case["must_not_have"]:
                    self.assertNotIn(banned, prompt)

    def test_prompt_builder_mixed_language_keeps_prompt_body_english(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年女性", "东亚"],
                "服装造型": ["浴巾裹身"],
                "场景背景": ["浴室", "温泉雾气"],
                "构图视角": ["近景半身"],
                "光影氛围": ["暖色调"],
            }
        )
        prompt = prompt_builder.build_prompt_list(
            selected,
            [],
            {
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "案例输出结构": "案例长段版",
                "标签反推模式": "自动平衡",
                "生成数量": 1,
                "额外要求": "",
                "提示词语言": "英文提示词+中文说明",
            },
            scene_group="",
            identity="",
            style_track="",
            recent_tracks=[],
            uniq=uniq,
            infer_template_style=lambda tags, explicit: explicit,
            infer_subject_type=lambda tags, explicit: explicit,
            infer_output_structure=lambda subject, explicit: explicit,
        )[0]
        self.assertIn("realistic photography", prompt)
        self.assertIn("wrapped bath towel", prompt)
        self.assertIn("bathroom", prompt)
        self.assertIn("hot spring steam", prompt)
        english_body, chinese_note = prompt.split("中文说明：", 1)
        self.assertIsNone(re.search(r"[\u4e00-\u9fff]", english_body))
        self.assertIsNotNone(re.search(r"[\u4e00-\u9fff]", chinese_note))

    def test_prompt_builder_format_sections_uses_english_labels_for_pure_english(self) -> None:
        prompt_list = ["realistic photography, adult woman, bedroom, soft light"]
        full_text, prompt_collection = prompt_builder.format_sections(
            prompt_list,
            "主体：成年女性",
            settings={"提示词语言": "纯英文"},
        )
        self.assertEqual(prompt_collection, prompt_list[0])
        self.assertIn("### Prompt 1", full_text)
        self.assertIn("#### Tag Analysis", full_text)
        self.assertNotIn("### 提示词", full_text)
        self.assertIsNone(re.search(r"[\u4e00-\u9fff]", full_text))

    def test_prompt_tag_library_adds_reference_tags_and_quick_presets(self) -> None:
        flattened_tags = set()
        for sections in tag_library.内置标签库.values():
            for values in sections.values():
                flattened_tags.update(str(item).strip() for item in values if str(item).strip())
        for required_tag in (
            "日韩影像",
            "日系电影感",
            "韩系极简影像",
            "生活流写实",
            "东方古风武侠",
            "东方赛博武侠朋克",
            "时尚编辑商业广告",
            "西方奇幻史诗",
            "影棚时尚女性",
            "书店女孩",
            "居家游戏女孩",
            "湖畔金发女性",
            "独立书店",
            "雨后街头",
            "白色斗篷",
            "黑金重甲",
            "银白雕花重甲",
            "神圣骑士",
            "冰霜骑士",
            "炎魔天使",
        ):
            self.assertIn(required_tag, flattened_tags)

        for preset_name in (
            "日韩系生活影像",
            "东方古风武侠",
            "东方赛博武侠朋克",
            "现代生活流写实",
            "城市天台晚风纪实",
            "山谷圣城巨构",
            "工业树灵巨像",
        ):
            self.assertIn(preset_name, tag_library.快速推荐组合)

        self.assertEqual(tag_library.快速推荐元数据["城市天台晚风纪实"]["group"], "人像写真")
        self.assertIn("人像", tag_library.快速推荐元数据["城市天台晚风纪实"]["use_cases"])
        self.assertIn("场景", tag_library.快速推荐元数据["山谷圣城巨构"]["use_cases"])
        self.assertIn("巨物", tag_library.快速推荐元数据["工业树灵巨像"]["use_cases"])
        self.assertEqual(tag_library.快速推荐元数据["山谷圣城巨构"]["catalog_group"], "场景")
        self.assertEqual(tag_library.快速推荐元数据["工业树灵巨像"]["catalog_group"], "巨物")
        self.assertIn("空间尺度", tag_library.快速推荐元数据["山谷圣城巨构"]["selection_tip"])
        self.assertIn("巨物体量", tag_library.快速推荐元数据["工业树灵巨像"]["selection_tip"])
        self.assertIn("场景", tag_library.快速推荐用途顺序[:3])
        self.assertIn("巨物", tag_library.快速推荐用途顺序[:3])

    def test_prompt_tag_library_contains_runtime_archive_support_terms(self) -> None:
        flattened_tags = set()
        for sections in tag_library.内置标签库.values():
            for values in sections.values():
                flattened_tags.update(str(item).strip() for item in values if str(item).strip())
        for required_tag in ("手持相机", "古建道场"):
            self.assertIn(required_tag, flattened_tags)

    def test_prompt_collection_splitter_logic_splits_double_newline_collection(self) -> None:
        text = "提示词A，近景\n\n提示词B，中景\n\n提示词C，全身"
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        parts = [item.strip() for item in normalized.split("\n\n") if item.strip()]
        outputs = tuple(str(parts[index]).strip() if index < len(parts) else "" for index in range(4))
        self.assertEqual(outputs[0], "提示词A，近景")
        self.assertEqual(outputs[1], "提示词B，中景")
        self.assertEqual(outputs[2], "提示词C，全身")
        self.assertEqual(outputs[3], "")

    def test_default_stage_prompt_template_keeps_node_output_contract(self) -> None:
        template = model_refiner.DEFAULT_STAGE_PROMPT_SYSTEM_TEMPLATE
        self.assertIn("Qwen TE 阶段式提示词生成器", template)
        self.assertIn("只输出最终提示词正文", template)
        self.assertIn("真实但美", template)
        self.assertIn("不要强行改成写实摄影", template)
        self.assertIn("650-900", template)
        self.assertIn("320-520", template)
        self.assertIn("目标接近 800 字", template)
        self.assertIn("主体 → 环境 → 光线 → 风格/媒介 → 镜头", template)
        self.assertIn("具体描述优先", template)
        self.assertIn("--profile", template)
        self.assertIn("不得锁死", template)

    def test_stage_generator_loads_default_system_template(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        node_class = getattr(module, "QwenTE阶段式提示词生成器")
        input_types = node_class.INPUT_TYPES()
        default_template = module.SETTING_DEFAULTS["系统提示词覆盖"]
        widget_default = input_types["required"]["系统提示词覆盖"][1]["default"]
        self.assertEqual(default_template, model_refiner.DEFAULT_STAGE_PROMPT_SYSTEM_TEMPLATE)
        self.assertEqual(widget_default, default_template)
        self.assertEqual(module.SETTING_DEFAULTS["最大生成token"], 1800)
        self.assertEqual(input_types["required"]["最大生成token"][1]["default"], 1800)

    def test_stage_generator_style_track_routes_reference_driven_branches(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        self.assertEqual(
            module._style_track("真实感", ["都市电影人文", "纪实电影摄影", "街道"]),
            "都市电影人文",
        )
        self.assertEqual(
            module._style_track("真实感", ["高端时尚编辑肖像", "大画幅棚拍", "广告成片质感"]),
            "时尚编辑商业广告",
        )
        self.assertEqual(
            module._style_track("真实感", ["日韩影像", "日系电影感", "生活流写实"]),
            "日韩影像",
        )
        self.assertEqual(
            module._style_track("古风", ["港式武侠", "港式武侠胶片", "竹林"]),
            "东方古风武侠",
        )
        self.assertEqual(
            module._style_track("古风", ["志怪古风", "神谕石碑", "雾景实拍感"]),
            "国风暗黑志怪",
        )
        self.assertEqual(
            module._style_track("CG感", ["东方赛博武侠朋克", "东方赛博机甲", "能量刀", "全息界面"]),
            "东方赛博武侠朋克",
        )
        self.assertEqual(
            module._style_track("真实感", ["城市屋顶纪实", "城市天台", "日落逆光"]),
            "城市天台纪实",
        )
        self.assertEqual(
            module._style_track("神话感", ["山谷圣城", "巨构神殿", "瀑布峡谷"]),
            "山谷圣城史诗",
        )
        self.assertEqual(
            module._style_track("CG感", ["树灵巨像", "工业舱室", "朽木树皮纹理"]),
            "工业树灵巨像",
        )

    def test_stage_generator_recovers_shifted_system_prompt_and_text_noise(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        _, _, settings, _ = module._build_state_from_kwargs(
            {
                "系统提示词覆盖": "960",
                "额外要求": "true\n角色设定图模式：保留当前角色材质。\n角色设定图模式：保留当前角色材质。",
                "智能文本输入": "false\n浴室柔光\n浴室柔光",
            }
        )
        self.assertEqual(settings["系统提示词覆盖"], module.SETTING_DEFAULTS["系统提示词覆盖"])
        self.assertEqual(settings["额外要求"], "角色设定图模式：保留当前角色材质。")
        self.assertEqual(settings["智能文本输入"], "浴室柔光")

    def test_state_builder_parses_string_booleans_without_enabling_false_values(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        _, _, false_settings, _ = module._build_state_from_kwargs(
            {
                "运行时随机标签": "false",
                "优先柔和肤质": "0",
                "抑制文字伪影": "off",
                "智能文本匹配": "关闭",
                "标签块编排启用": "no",
                "图片反推生成": "null",
                "输出think块": "undefined",
            }
        )
        self.assertFalse(false_settings["运行时随机标签"])
        self.assertFalse(false_settings["优先柔和肤质"])
        self.assertFalse(false_settings["抑制文字伪影"])
        self.assertFalse(false_settings["智能文本匹配"])
        self.assertFalse(false_settings["标签块编排启用"])
        self.assertFalse(false_settings["图片反推生成"])
        self.assertFalse(false_settings["输出think块"])

        _, _, true_settings, _ = module._build_state_from_kwargs(
            {
                "运行时随机标签": "true",
                "优先柔和肤质": "1",
                "抑制文字伪影": "on",
                "智能文本匹配": "开启",
                "标签块编排启用": "yes",
                "图片反推生成": "是",
                "输出think块": True,
            }
        )
        self.assertTrue(true_settings["运行时随机标签"])
        self.assertTrue(true_settings["优先柔和肤质"])
        self.assertTrue(true_settings["抑制文字伪影"])
        self.assertTrue(true_settings["智能文本匹配"])
        self.assertTrue(true_settings["标签块编排启用"])
        self.assertTrue(true_settings["图片反推生成"])
        self.assertTrue(true_settings["输出think块"])

    def test_stage_generator_preserves_pretty_tag_block_json_structure(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        payload = {
            "version": 1,
            "enabled": True,
            "blocks": [
                {"id": "a", "type": "tag_group", "group": "主体", "tags": ["成年女性"], "locked": False},
                {"id": "b", "type": "tag_group", "group": "场景背景", "tags": ["宫殿"], "locked": False},
            ],
        }
        pretty = json.dumps(payload, ensure_ascii=False, indent=2)
        _, _, settings, _ = module._build_state_from_kwargs({"标签块编排JSON": pretty})
        self.assertEqual(json.loads(settings["标签块编排JSON"]), payload)
        self.assertEqual(settings["标签块编排JSON"].count('"locked": false'), 2)

    def test_state_builder_tag_block_json_limit_never_returns_truncated_json(self) -> None:
        payload = {
            "version": 1,
            "enabled": True,
            "blocks": [{"id": "a", "type": "tag_group", "group": "主体", "tags": ["成年女性"]}],
        }
        pretty = json.dumps(payload, ensure_ascii=False, indent=2)
        padded_valid = "{" + (" " * state_builder._TAG_BLOCK_JSON_MAX_CHARS) + pretty[1:]
        compacted = state_builder._clean_tag_block_json_field(padded_valid)
        self.assertTrue(compacted)
        self.assertLessEqual(len(compacted), state_builder._TAG_BLOCK_JSON_MAX_CHARS)
        self.assertEqual(json.loads(compacted), payload)

        oversized_invalid = '{"blocks":[' + (" " * state_builder._TAG_BLOCK_JSON_MAX_CHARS)
        self.assertEqual(state_builder._clean_tag_block_json_field(oversized_invalid), "")

        oversized_content = {
            "version": 1,
            "enabled": True,
            "blocks": [{"type": "text", "text": "x" * state_builder._TAG_BLOCK_JSON_MAX_CHARS}],
        }
        self.assertEqual(state_builder._clean_tag_block_json_field(oversized_content), "")

    def test_stage_generator_can_use_embedded_model_without_required_link(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        node_class = getattr(module, "QwenTE阶段式提示词生成器")
        input_types = node_class.INPUT_TYPES()
        self.assertEqual(module.SETTING_DEFAULTS["模型来源"], "仅Skill")
        self.assertEqual(input_types["required"]["模型来源"][1]["default"], "仅Skill")
        self.assertEqual(input_types["required"]["内置主模型"][1]["default"], input_types["required"]["内置主模型"][0][0])
        self.assertNotIn("qwen模型", input_types["required"])
        self.assertIn("qwen模型", input_types["optional"])
        for name in (
            "模型来源",
            "内置模型系列",
            "内置主模型",
            "内置视觉投影mmproj",
            "内置启用思考",
            "内置上下文长度",
            "内置GPU层数",
            "内置KV缓存K类型",
            "内置KV缓存V类型",
            "API服务商",
            "API地址",
            "API密钥",
            "API模型",
            "API超时秒",
            "API额外请求头",
        ):
            self.assertIn(name, input_types["required"])

    def test_stage_api_model_uses_openai_compatible_chat_completion(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()

        captured: dict[str, object] = {}

        class DummyHeaders:
            def get_content_charset(self):
                return "utf-8"

        class DummyResponse:
            headers = DummyHeaders()

            def __init__(self):
                self.payload = json.dumps({"choices": [{"message": {"content": "api refined prompt"}}]}).encode("utf-8")
                self.offset = 0

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, size=-1):
                if size is None or size < 0:
                    size = len(self.payload) - self.offset
                chunk = self.payload[self.offset : self.offset + size]
                self.offset += len(chunk)
                return chunk

        def fake_open(request, timeout=0):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["auth"] = request.headers.get("Authorization")
            return DummyResponse()

        with mock.patch.object(module._API_HTTP_OPENER, "open", side_effect=fake_open):
            model = module._创建API阶段模型(
                {
                    "API服务商": "OpenAI兼容",
                    "API地址": "https://api.example.com/v1",
                    "API密钥": "test-key",
                    "API模型": "demo-model",
                    "API超时秒": 33,
                    "API额外请求头": "X-Test: yes",
                }
            )
            response = model.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=64,
                temperature=0.3,
                top_p=0.8,
                frequency_penalty=0.25,
                presence_penalty=0.15,
                seed=1234,
            )

        self.assertEqual(response["choices"][0]["message"]["content"], "api refined prompt")
        self.assertEqual(captured["url"], "https://api.example.com/v1/chat/completions")
        self.assertEqual(captured["timeout"], 33)
        self.assertEqual(captured["auth"], "Bearer test-key")
        self.assertEqual(captured["body"]["model"], "demo-model")
        self.assertEqual(captured["body"]["messages"][0]["content"], "hello")
        self.assertEqual(captured["body"]["frequency_penalty"], 0.25)
        self.assertEqual(captured["body"]["presence_penalty"], 0.15)
        self.assertEqual(captured["body"]["seed"], 1234)

    def test_model_response_extractor_is_strict_and_supports_content_blocks(self) -> None:
        self.assertEqual(
            model_refiner.extract_text(
                {"choices": [{"message": {"content": [{"type": "text", "text": "first"}, {"text": "second"}]}}]}
            ),
            "first\nsecond",
        )

        class AiMessage:
            content = [{"text": "object content"}]

        self.assertEqual(model_refiner.extract_text(AiMessage()), "object content")
        self.assertEqual(model_refiner.extract_text({"unexpected": {"value": "not prompt text"}}), "")
        with self.assertRaisesRegex(RuntimeError, "token rejected"):
            model_refiner.extract_text({"error": {"message": "token rejected"}})

    def test_invoke_model_error_object_uses_skill_fallback(self) -> None:
        class InvokeModel:
            def invoke(self, _prompt):
                return {"error": {"message": "invoke denied"}}

        settings = {
            "模型来源": "API接口",
            "模型来源实际": "API接口",
            "模型调用基础来源": "API接口",
            "最大生成token": 256,
            "温度": 0.5,
            "top_p": 0.9,
        }
        original = "cinematic portrait, adult woman, studio light"
        refined = model_refiner.maybe_model_refine(
            InvokeModel(),
            original,
            settings,
            chat_completion=lambda *_args, **_kwargs: None,
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, original)
        self.assertEqual(settings["模型调用失败次数"], 1)
        self.assertEqual(settings["模型活动回退数量"], 1)
        self.assertIn("invoke denied", settings["模型回退说明"])

    def test_repeated_fallback_note_keeps_earlier_reasons(self) -> None:
        settings: dict[str, object] = {"模型回退说明": "", "推理纠偏说明": []}
        model_refiner._merge_fallback_note(settings, "原因A")
        model_refiner._merge_fallback_note(settings, "原因B")
        model_refiner._merge_fallback_note(settings, "原因B")
        self.assertIn("原因A", settings["模型回退说明"])
        self.assertIn("原因B", settings["模型回退说明"])
        self.assertEqual(str(settings["模型回退说明"]).count("原因B"), 1)

    def test_stage_api_extra_headers_fail_closed(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        self.assertEqual(
            module._parse_api_extra_headers('{"HTTP-Referer":"https://example.test","X-Title":"Prompt Node"}'),
            {"HTTP-Referer": "https://example.test", "X-Title": "Prompt Node"},
        )
        invalid_cases = (
            ('["not-an-object"]', "JSON 必须是对象"),
            ("BrokenHeader", "缺少"),
            ("Authorization: Bearer secret", "受保护"),
            ("content-type: text/plain", "受保护"),
            ("X-Test: one\nx-test: two", "重复"),
            (json.dumps({"X-Test": "ok\u0000bad"}), "控制字符"),
        )
        for raw_headers, expected in invalid_cases:
            with self.subTest(raw_headers=raw_headers):
                with self.assertRaisesRegex(RuntimeError, expected):
                    module._parse_api_extra_headers(raw_headers)

    def test_stage_api_explicit_env_name_does_not_borrow_provider_key(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        common = {
            "API服务商": "OpenAI",
            "API地址": "https://api.openai.com/v1",
            "API模型": "gpt-4o-mini",
        }
        with mock.patch.dict(module.os.environ, {"OPENAI_API_KEY": "provider-key"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "未找到 API Key"):
                module._解析API模型配置({**common, "API密钥": "env:DOES_NOT_EXIST"})
            legacy = module._解析API模型配置({**common, "API密钥": "env:QWEN_TE_API_KEY"})
        self.assertEqual(legacy["api_key"], "provider-key")

    def test_stage_api_provider_payload_mappings(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        calls: list[dict[str, object]] = []

        def fake_http(url, payload, headers, timeout):
            calls.append({"url": url, "payload": payload, "headers": headers, "timeout": timeout})
            if "anthropic" in url:
                return {"content": [{"type": "text", "text": "anthropic prompt"}]}
            if "generativelanguage" in url:
                return {"candidates": [{"content": {"parts": [{"text": "gemini prompt"}]}}]}
            return {"choices": [{"message": {"content": "compatible prompt"}}]}

        messages = [{"role": "system", "content": "system rule"}, {"role": "user", "content": "hello"}]
        with mock.patch.object(module, "_http_post_json", side_effect=fake_http):
            anthropic = module._TEAPIChatModel(
                {
                    "provider": "Claude Anthropic",
                    "kind": "anthropic",
                    "url": "https://api.anthropic.com/v1/messages",
                    "api_key": "anthropic-key",
                    "model": "claude-haiku-4-5",
                    "timeout": 30,
                }
            )
            anthropic.create_chat_completion(
                messages=messages,
                max_tokens=64,
                temperature=1.8,
                top_p=0.8,
                top_k=37,
                stop=["END"],
            )

            gemini = module._TEAPIChatModel(
                {
                    "provider": "Gemini 原生",
                    "kind": "gemini",
                    "url": "https://generativelanguage.googleapis.com/v1beta",
                    "api_key": "gemini-key",
                    "model": "gemini-2.5-flash",
                    "timeout": 31,
                }
            )
            gemini.create_chat_completion(
                messages=messages,
                max_tokens=65,
                temperature=0.7,
                top_p=0.82,
                top_k=29,
                seed=17,
                stop=["STOP"],
            )

            openai = module._TEAPIChatModel(
                {
                    "provider": "OpenAI",
                    "kind": "openai",
                    "url": "https://api.openai.com/v1/chat/completions",
                    "api_key": "openai-key",
                    "model": "gpt-5-mini",
                    "timeout": 32,
                }
            )
            openai.create_chat_completion(
                messages=messages,
                max_tokens=66,
                temperature=1.2,
                top_p=0.83,
                seed=18,
                stop=["HALT"],
            )

            deepseek = module._TEAPIChatModel(
                {
                    "provider": "DeepSeek",
                    "kind": "openai",
                    "url": "https://api.deepseek.com/chat/completions",
                    "api_key": "deepseek-key",
                    "model": "deepseek-v4-flash",
                    "timeout": 33,
                }
            )
            deepseek.create_chat_completion(messages=messages, max_tokens=67, temperature=0.6, top_p=0.84)

        anthropic_call, gemini_call, openai_call, deepseek_call = calls
        self.assertEqual(anthropic_call["payload"]["temperature"], 1.0)
        self.assertEqual(anthropic_call["payload"]["top_k"], 37)
        self.assertEqual(anthropic_call["payload"]["stop_sequences"], ["END"])
        self.assertEqual(anthropic_call["headers"]["x-api-key"], "anthropic-key")

        self.assertTrue(str(gemini_call["url"]).endswith("/models/gemini-2.5-flash:generateContent"))
        self.assertEqual(gemini_call["headers"]["x-goog-api-key"], "gemini-key")
        self.assertEqual(gemini_call["payload"]["generationConfig"]["topK"], 29)
        self.assertEqual(gemini_call["payload"]["generationConfig"]["seed"], 17)
        self.assertEqual(gemini_call["payload"]["generationConfig"]["stopSequences"], ["STOP"])

        self.assertEqual(openai_call["payload"]["max_completion_tokens"], 66)
        self.assertEqual(openai_call["payload"]["messages"][0]["role"], "developer")
        for unsupported in ("max_tokens", "temperature", "top_p", "seed", "stop"):
            self.assertNotIn(unsupported, openai_call["payload"])

        self.assertEqual(deepseek_call["payload"]["max_tokens"], 67)
        self.assertEqual(deepseek_call["payload"]["thinking"], {"type": "disabled"})

    def test_native_provider_blocked_responses_surface_reason(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        messages = [{"role": "user", "content": "hello"}]

        anthropic = module._TEAPIChatModel(
            {
                "provider": "Claude Anthropic",
                "kind": "anthropic",
                "url": "https://api.anthropic.com/v1/messages",
                "api_key": "anthropic-key",
                "model": "claude-haiku-4-5",
                "timeout": 30,
            }
        )
        with mock.patch.object(
            module,
            "_http_post_json",
            return_value={"content": [], "stop_reason": "refusal"},
        ):
            with self.assertRaisesRegex(RuntimeError, "stop_reason=refusal"):
                anthropic.create_chat_completion(messages=messages)

        gemini = module._TEAPIChatModel(
            {
                "provider": "Gemini 原生",
                "kind": "gemini",
                "url": "https://generativelanguage.googleapis.com/v1beta",
                "api_key": "gemini-key",
                "model": "gemini-2.5-flash",
                "timeout": 30,
            }
        )
        with mock.patch.object(
            module,
            "_http_post_json",
            return_value={"promptFeedback": {"blockReason": "SAFETY"}, "candidates": []},
        ):
            with self.assertRaisesRegex(RuntimeError, "blockReason=SAFETY"):
                gemini.create_chat_completion(messages=messages)

    def test_stage_api_config_failure_counts_all_requested_outputs(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        node = module.QwenTE阶段式提示词生成器()
        result = node.run(
            模型来源="API接口",
            API服务商="自定义",
            API地址="https://api.example.com/v1",
            API密钥="",
            API模型="",
            主体标签1="成年女性",
            场景背景标签1="简洁室内",
            智能文本匹配=True,
            智能文本输入="成年女性室内商业摄影",
            运行时随机标签=False,
            生成数量=3,
            提示词语言="纯中文",
            详细度="标准",
            输出模式="完整结果",
            最大生成token=256,
        )
        payload = json.loads(result[3])
        self.assertEqual(len(payload["prompt_list"]), 3)
        self.assertEqual(payload["model_call_attempt_count"], 1)
        self.assertEqual(payload["model_call_failure_count"], 1)
        self.assertEqual(payload["model_active_fallback_count"], 4)
        self.assertEqual(payload["model_source_effective"], "仅Skill回退")

    def test_smart_text_unchanged_model_output_keeps_main_adoption_count(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()

        class DummyModel:
            pass

        original_build_prompt = module._build_prompt_list_impl
        original_refine_batch = module._maybe_model_refine_batch_impl
        original_refine_one = module._maybe_model_refine_impl
        original_update_history = module._update_history

        module._build_prompt_list_impl = lambda *args, **kwargs: [
            "商业摄影，成年女性，雨夜站台，红色风衣，全景全身，高细节"
        ]

        def fake_batch(_model, prompt_list, settings, **_kwargs):
            module._record_model_call_result_impl(
                settings,
                outcome="success",
                changed=True,
                adopted_outputs=1,
            )
            return ["电影感商业摄影，成年女性，雨夜站台，红色风衣，全景全身，轮廓光，高细节"]

        def fake_one(_model, prompt, settings, **_kwargs):
            module._record_model_call_result_impl(
                settings,
                outcome="success",
                changed=False,
                adopted_outputs=0,
            )
            return prompt

        module._maybe_model_refine_batch_impl = fake_batch
        module._maybe_model_refine_impl = fake_one
        module._update_history = lambda *args, **kwargs: []
        try:
            result = module._run_stage(
                DummyModel(),
                **{
                    "unique_id": "smart-unchanged-status",
                    "主体标签1": "成年女性",
                    "场景背景标签1": "雨夜站台",
                    "智能文本匹配": True,
                    "智能文本输入": "成年女性，雨夜站台，全身商业摄影",
                    "模型来源": "API接口",
                    "模型来源实际": "API接口",
                    "模型调用基础来源": "API接口",
                    "运行时随机标签": False,
                    "生成数量": 1,
                    "提示词语言": "纯中文",
                    "详细度": "标准",
                    "输出模式": "完整结果",
                    "最大生成token": 512,
                },
            )
        finally:
            module._build_prompt_list_impl = original_build_prompt
            module._maybe_model_refine_batch_impl = original_refine_batch
            module._maybe_model_refine_impl = original_refine_one
            module._update_history = original_update_history

        payload = json.loads(result[3])
        self.assertEqual(payload["model_call_success_count"], 2)
        self.assertEqual(payload["model_call_adopted_count"], 1)
        self.assertEqual(payload["model_active_fallback_count"], 1)
        self.assertEqual(payload["model_source_effective"], "API接口（部分回退）")
        self.assertIn("最终仍有 1 条回退 Skill", payload["model_call_status"])

    def test_model_api_config_signature_matches_frontend_vector(self) -> None:
        provider, base_url, model, signature = formatter._model_api_config_meta(
            {
                "模型来源": "API接口",
                "API服务商有效": "OpenAI",
                "API地址有效": "https://api.openai.com/v1",
                "API模型有效": "gpt-4o-mini",
                "API密钥": "env:OPENAI_API_KEY",
                "API额外请求头": "X-Title: Demo",
            }
        )
        self.assertEqual((provider, base_url, model), ("OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"))
        self.assertEqual(signature, "model-api-v1:53518f0821f655b6")
        self.assertNotIn("OPENAI_API_KEY", signature)

    def test_stage_api_preset_requires_a_resolved_key_before_first_request(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        with mock.patch.dict(module.os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "未找到 API Key"):
                module._解析API模型配置(
                    {
                        "API服务商": "OpenAI",
                        "API地址": "https://api.openai.com/v1",
                        "API密钥": "env:OPENAI_API_KEY",
                        "API模型": "gpt-4o-mini",
                    }
                )

    def test_stage_api_runtime_failure_is_visible_in_final_output(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()

        class FailingApiModel:
            llm = None

            def __init__(self) -> None:
                self.llm = self

            def create_chat_completion(self, **_kwargs):
                raise RuntimeError("HTTP 401 Unauthorized")

        with mock.patch.object(
            module,
            "_调用chat_completion",
            side_effect=lambda llm, *, messages, params: llm.create_chat_completion(messages=messages, **params),
        ):
            result = module._run_stage(
                FailingApiModel(),
                **{
                    "模型来源": "API接口",
                    "模型来源实际": "API接口",
                    "模型调用基础来源": "API接口",
                    "API服务商": "OpenAI",
                    "API模型": "gpt-4o-mini",
                    "主体标签1": "成年女性",
                    "场景背景标签1": "简洁室内",
                    "运行时随机标签": False,
                    "生成数量": 1,
                    "提示词语言": "纯中文",
                    "详细度": "标准",
                    "输出模式": "完整结果",
                    "最大生成token": 256,
                },
            )
        payload = json.loads(result[3])
        self.assertTrue(result[1].strip())
        self.assertEqual(payload["model_source"], "API接口")
        self.assertEqual(payload["model_source_effective"], "仅Skill回退")
        self.assertEqual(payload["model_call_attempt_count"], 1)
        self.assertEqual(payload["model_call_success_count"], 0)
        self.assertEqual(payload["model_call_failure_count"], 1)
        self.assertIn("调用失败", payload["model_call_status"])
        self.assertIn("401 Unauthorized", payload["model_fallback_note"])
        self.assertIn("401 Unauthorized", result[2])

    def test_model_refiner_retries_small_batches_when_separator_is_missing(self) -> None:
        class DummyApiModel:
            def create_chat_completion(self, **_kwargs):
                return None

        responses = iter(
            [
                "cinematic portrait and rainy urban night combined into one response",
                "cinematic editorial portrait, adult woman in a crimson silk dress, soft studio rim light, detailed fabric texture",
                "cinematic rainy urban night, adult man in a cobalt coat, neon reflections, dynamic street composition",
            ]
        )
        calls = []

        def fake_chat_completion(*_args, **kwargs):
            calls.append(kwargs)
            return {"text": next(responses)}

        settings = {
            "模型来源": "API接口",
            "模型来源实际": "API接口",
            "模型调用基础来源": "API接口",
            "提示词语言": "纯英文",
            "详细度": "标准",
            "输出模式": "完整结果",
            "系统提示词覆盖": "",
            "最大生成token": 512,
            "温度": 0.6,
            "top_p": 0.9,
        }
        prompts = [
            "cinematic portrait, adult woman, red dress, studio light",
            "rainy urban night, adult man, blue coat, neon reflections",
        ]
        refined = model_refiner.maybe_model_refine_batch(
            DummyApiModel(),
            prompts,
            settings,
            chat_completion=fake_chat_completion,
            clean_think_text=lambda text: text,
        )

        self.assertEqual(len(calls), 3)
        self.assertEqual(len(refined), 2)
        self.assertNotEqual(refined, prompts)
        self.assertEqual(settings["模型调用尝试次数"], 3)
        self.assertEqual(settings["模型调用成功次数"], 2)
        self.assertEqual(settings["模型调用失败次数"], 1)
        self.assertEqual(
            settings["模型调用成功次数"] + settings["模型调用失败次数"],
            settings["模型调用尝试次数"],
        )
        self.assertEqual(settings["模型调用采纳次数"], 2)
        self.assertIn("无输出回退", settings["模型调用状态"])
        self.assertNotIn("部分回退", settings["模型调用状态"])
        self.assertEqual(settings["模型来源实际"], "API接口")
        self.assertEqual(settings["模型回退说明"], "")

    def test_model_refiner_small_batch_retry_reports_final_fallback_count(self) -> None:
        class DummyApiModel:
            def create_chat_completion(self, **_kwargs):
                return None

        responses = iter(
            [
                "combined response without the required separator",
                "cinematic editorial portrait, adult woman in a crimson silk dress, detailed studio rim light",
                RuntimeError("HTTP 503 temporary upstream failure"),
            ]
        )

        def fake_chat_completion(*_args, **_kwargs):
            response = next(responses)
            if isinstance(response, Exception):
                raise response
            return {"text": response}

        settings = {
            "模型来源": "API接口",
            "模型来源实际": "API接口",
            "模型调用基础来源": "API接口",
            "提示词语言": "纯英文",
            "详细度": "标准",
            "输出模式": "完整结果",
            "系统提示词覆盖": "",
            "最大生成token": 512,
            "温度": 0.6,
            "top_p": 0.9,
        }
        prompts = [
            "cinematic portrait, adult woman, red dress, studio light",
            "rainy urban night, adult man, blue coat, neon reflections",
        ]
        refined = model_refiner.maybe_model_refine_batch(
            DummyApiModel(),
            prompts,
            settings,
            chat_completion=fake_chat_completion,
            clean_think_text=lambda text: text,
        )

        self.assertNotEqual(refined[0], prompts[0])
        self.assertEqual(refined[1], prompts[1])
        self.assertEqual(settings["模型调用尝试次数"], 3)
        self.assertEqual(settings["模型调用成功次数"], 1)
        self.assertEqual(settings["模型调用失败次数"], 2)
        self.assertEqual(
            settings["模型调用成功次数"] + settings["模型调用失败次数"],
            settings["模型调用尝试次数"],
        )
        self.assertEqual(settings["模型调用采纳次数"], 1)
        self.assertIn("最终仍有 1 条回退 Skill", settings["模型调用状态"])
        self.assertIn("仍有 1/2 条", settings["模型回退说明"])
        self.assertEqual(settings["模型来源实际"], "API接口（部分回退）")

    def test_model_refiner_partial_batch_is_one_successful_attempt(self) -> None:
        class DummyApiModel:
            def create_chat_completion(self, **_kwargs):
                return None

        settings = {
            "模型来源": "API接口",
            "模型来源实际": "API接口",
            "模型调用基础来源": "API接口",
            "提示词语言": "纯英文",
            "系统提示词覆盖": "",
            "最大生成token": 512,
            "温度": 0.6,
            "top_p": 0.9,
        }
        prompts = [
            "cinematic portrait, adult woman, red dress, studio light",
            "rainy urban night, adult man, blue coat, neon reflections",
        ]
        refined = model_refiner.maybe_model_refine_batch(
            DummyApiModel(),
            prompts,
            settings,
            chat_completion=lambda *_args, **_kwargs: {
                "text": (
                    "cinematic editorial portrait, adult woman in a crimson silk dress, soft rim light"
                    "<<<QWEN_TE_SPLIT>>>"
                    "分析用户请求，解释雨夜城市画面的构图步骤"
                )
            },
            clean_think_text=lambda text: text,
        )

        self.assertNotEqual(refined[0], prompts[0])
        self.assertEqual(refined[1], prompts[1])
        self.assertEqual(settings["模型调用尝试次数"], 1)
        self.assertEqual(settings["模型调用成功次数"], 1)
        self.assertEqual(settings["模型调用失败次数"], 0)
        self.assertEqual(
            settings["模型调用成功次数"] + settings["模型调用失败次数"],
            settings["模型调用尝试次数"],
        )
        self.assertEqual(settings["模型调用采纳次数"], 1)
        self.assertIn("最终仍有 1 条回退 Skill", settings["模型调用状态"])

    def test_model_refiner_redacts_configured_and_common_tokens_from_errors(self) -> None:
        class DummyApiModel:
            def create_chat_completion(self, **_kwargs):
                return None

        resolved_key = "resolved-secret-123456789"
        header_secret = "header-secret-987654321"
        common_key = "sk-proj-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        github_token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        settings = {
            "模型来源": "API接口",
            "模型来源实际": "API接口",
            "模型调用基础来源": "API接口",
            "API密钥解析值": resolved_key,
            "API额外请求头": json.dumps(
                {
                    "Authorization": f"Bearer {header_secret}",
                    "X-Custom-Secret": "custom-header-value-24680",
                }
            ),
            "系统提示词覆盖": "",
            "最大生成token": 256,
            "温度": 0.6,
            "top_p": 0.9,
        }
        raw_error = (
            f"HTTP 401 api_key={resolved_key}; Authorization: Bearer {header_secret}; "
            f"provider={common_key}; github={github_token}; custom=custom-header-value-24680"
        )

        refined = model_refiner.maybe_model_refine(
            DummyApiModel(),
            "cinematic portrait, adult woman, studio light",
            settings,
            chat_completion=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError(raw_error)),
            clean_think_text=lambda text: text,
        )

        self.assertEqual(refined, "cinematic portrait, adult woman, studio light")
        serialized_errors = json.dumps(
            {
                "errors": settings["模型调用错误"],
                "fallback": settings["模型回退说明"],
                "notes": settings["推理纠偏说明"],
            },
            ensure_ascii=False,
        )
        for secret in (resolved_key, header_secret, common_key, github_token, "custom-header-value-24680"):
            self.assertNotIn(secret, serialized_errors)
        self.assertIn("[REDACTED]", serialized_errors)
        self.assertEqual(
            model_refiner.sanitize_model_error(raw_error, settings),
            settings["模型调用错误"][0],
        )

    def test_stage_api_env_key_is_limited_to_provider_preset_origin(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        with mock.patch.dict(module.os.environ, {"OPENAI_API_KEY": "provider-env-key"}, clear=True):
            config = module._解析API模型配置(
                {
                    "API服务商": "OpenAI",
                    "API地址": "https://api.openai.com/proxy/v1",
                    "API密钥": "env:OPENAI_API_KEY",
                }
            )
            self.assertEqual(config["api_key"], "provider-env-key")
            self.assertEqual(config["url"], "https://api.openai.com/proxy/v1/chat/completions")
            with self.assertRaisesRegex(RuntimeError, "环境变量密钥只能发送到.*预设来源"):
                module._解析API模型配置(
                    {
                        "API服务商": "OpenAI",
                        "API地址": "https://proxy.example.com/v1",
                        "API密钥": "env:OPENAI_API_KEY",
                    }
                )

    def test_stage_api_custom_env_key_requires_exact_origin_allowlist(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        common = {
            "API服务商": "OpenAI兼容",
            "API地址": "https://api.example.com/v1",
            "API密钥": "env:CUSTOM_API_KEY",
        }
        with mock.patch.dict(module.os.environ, {"CUSTOM_API_KEY": "custom-env-key"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "QWEN_TE_CUSTOM_API_SECRET_ORIGINS"):
                module._解析API模型配置(common)
        with mock.patch.dict(
            module.os.environ,
            {
                "CUSTOM_API_KEY": "custom-env-key",
                "QWEN_TE_CUSTOM_API_SECRET_ORIGINS": "https://other.example; https://api.example.com\nhttp://localhost:8000",
            },
            clear=True,
        ):
            config = module._解析API模型配置(common)
        self.assertEqual(config["api_key"], "custom-env-key")
        with mock.patch.dict(module.os.environ, {"QWEN_TE_API_KEY": "must-not-be-used"}, clear=True):
            no_auth_config = module._解析API模型配置({**common, "API密钥": ""})
        self.assertEqual(no_auth_config["api_key"], "")

    def test_stage_api_literal_key_remains_compatible_with_overridden_address(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        with mock.patch.dict(module.os.environ, {}, clear=True):
            config = module._解析API模型配置(
                {
                    "API服务商": "OpenAI",
                    "API地址": "https://trusted-proxy.example/v1",
                    "API密钥": "proxy-specific-key",
                }
            )
        self.assertEqual(config["api_key"], "proxy-specific-key")
        self.assertEqual(config["url"], "https://trusted-proxy.example/v1/chat/completions")

    def test_stage_api_custom_address_without_resolved_env_secret_remains_usable(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        with mock.patch.dict(module.os.environ, {}, clear=True):
            config = module._解析API模型配置(
                {
                    "API服务商": "OpenAI",
                    "API地址": "http://127.0.0.1:9000/v1",
                    "API密钥": "env:OPENAI_API_KEY",
                }
            )
        self.assertEqual(config["api_key"], "")
        self.assertEqual(config["url"], "http://127.0.0.1:9000/v1/chat/completions")

    def test_stage_api_rejects_unsafe_or_invalid_urls(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        cases = (
            ("file:///tmp/api", "仅允许 http:// 或 https://"),
            ("https:///v1", "必须包含有效主机名"),
            ("https://user:password@api.example.com/v1", "不得包含用户名或密码"),
            ("https://api.example.com/v1?token=secret", "不得包含查询参数或片段"),
            ("https://api.example.com/v1#fragment", "不得包含查询参数或片段"),
        )
        for url, expected in cases:
            with self.subTest(url=url):
                with self.assertRaisesRegex(RuntimeError, expected):
                    module._解析API模型配置(
                        {
                            "API服务商": "自定义",
                            "API地址": url,
                            "API密钥": "literal-key",
                        }
                    )

    def test_stage_api_secret_origin_rejection_uses_safe_skill_fallback(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        settings = {
            "模型来源": "API接口",
            "API服务商": "OpenAI",
            "API地址": "https://untrusted.example/v1",
            "API密钥": "env:OPENAI_API_KEY",
            "API模型": "demo-model",
        }
        with mock.patch.dict(module.os.environ, {"OPENAI_API_KEY": "must-not-leave-origin"}, clear=True):
            model = module._安全加载阶段模型(settings)
        self.assertIsNone(model)
        self.assertEqual(settings["模型来源实际"], "仅Skill回退")
        self.assertIn("环境变量密钥只能发送到", settings["模型回退说明"])
        self.assertNotIn("must-not-leave-origin", settings["模型回退说明"])

    def test_stage_run_can_disable_model_and_use_skill_only(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        self.assertIsNone(module._加载阶段模型({}))
        self.assertIsNone(module._加载阶段模型({"模型来源": "仅Skill"}))

    def test_stage_node_falls_back_to_skill_when_api_model_config_is_incomplete(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        node = module.QwenTE阶段式提示词生成器()
        result = node.run(
            模型来源="API接口",
            API服务商="自定义",
            API地址="https://api.example.com/v1",
            API模型="",
            主体标签1="成年女性",
            场景背景标签1="简洁室内",
            运行时随机标签=False,
            生成数量=1,
            提示词语言="纯中文",
            详细度="标准",
            输出模式="完整结果",
            最大生成token=256,
        )
        payload = json.loads(result[3])
        self.assertTrue(result[1].strip())
        self.assertEqual(payload["model_source"], "API接口")
        self.assertEqual(payload["model_source_effective"], "仅Skill回退")
        self.assertIn("模型加载回退", payload["model_fallback_note"])
        self.assertIn("模型加载回退", result[2])

    def test_stage_run_skips_image_reverse_when_visual_model_is_unavailable(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module._run_stage(
            None,
            **{
                "模型来源": "仅Skill",
                "参考图片": object(),
                "图片反推生成": True,
                "图片反推模式": "角色设定图",
                "主体标签1": "成年女性",
                "场景背景标签1": "简洁室内",
                "运行时随机标签": False,
                "生成数量": 1,
                "提示词语言": "纯中文",
                "详细度": "标准",
                "输出模式": "完整结果",
                "最大生成token": 256,
            },
        )
        payload = json.loads(result[3])
        self.assertTrue(result[1].strip())
        self.assertIn("图片反推回退", result[2])
        self.assertIn("图片反推回退", " | ".join(payload["normalization_notes"]))

    def test_model_refiner_sends_skill_context_to_chat_model(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        captured: dict[str, Any] = {}

        def fake_chat_completion(*args: Any, **kwargs: Any) -> dict[str, str]:
            captured["messages"] = kwargs.get("messages", [])
            return {"text": "写实摄影，成年女性，全景全身，柔光，高细节"}

        model_refiner.maybe_model_refine(
            DummyChatLlm(),
            "写实摄影，成年女性，全景全身，柔光",
            {
                "系统提示词覆盖": "",
                "最大生成token": 256,
                "温度": 0.7,
                "top_p": 0.9,
                "模型来源": "API接口",
                "提示词语言": "纯中文",
                "运行时随机模式解析结果": "重写主体与场景",
                "智能文本风格优先解析结果": "文本优先",
                "智能文本风格解析结果": "古风",
                "风格隔离策略": "严格风格隔离",
                "NSFW工作台标签摘要": "已启用；映射标签：蒸汽浴室、湿身淋浴、柔光",
                "模型后置素材摘要": "当前已选/运行标签：成年女性、蒸汽浴室、湿身淋浴、柔光",
                "Skill动态变化策略": "运行时随机:重写主体与场景；标签作为素材锚点而非固定模板；优先变化未明确锁定维度：场景空间、动作姿态、持物道具。",
                "最近提示词指纹": ["tag:蒸汽浴室", "visual:scene:蒸汽浴室|light:柔光", "成年女性|蒸汽浴室|湿身淋浴|柔光"],
                "推理纠偏说明": ["Skill重复收敛：保留主线", "成人向主体补锚：成年女性"],
            },
            chat_completion=fake_chat_completion,
            clean_think_text=lambda text: text,
        )
        user_message = str(captured["messages"][1]["content"])
        self.assertIn("Skill前置上下文", user_message)
        self.assertIn("模型来源：API接口", user_message)
        self.assertIn("运行时随机解析：重写主体与场景", user_message)
        self.assertIn("Skill重复收敛：保留主线", user_message)
        self.assertIn("NSFW 工作台素材", user_message)
        self.assertIn("蒸汽浴室", user_message)
        self.assertIn("当前激活素材摘要", user_message)
        self.assertIn("最近输出避重档案", user_message)
        self.assertIn("Skill动态变化策略", user_message)
        self.assertIn("标签作为素材锚点而非固定模板", user_message)
        self.assertIn("全局非锁死策略", user_message)
        self.assertIn("最近输出只用于避让", user_message)
        self.assertIn("至少更换三个视觉维度", user_message)
        self.assertIn("近期标签：蒸汽浴室", user_message)
        self.assertIn("视觉档案：场景=蒸汽浴室", user_message)
        self.assertIn("成年女性|蒸汽浴室|湿身淋浴|柔光", user_message)
        self.assertIn("待整理提示词正文", user_message)

    def test_model_refiner_recent_history_raises_sampling_diversity(self) -> None:
        params = model_refiner._refiner_sampling_params(
            {
                "温度": 0.42,
                "top_p": 0.72,
                "重复惩罚": 1.0,
                "频率惩罚": 0.0,
                "存在惩罚": 0.0,
                "最近提示词指纹": ["visual:scene:摄影棚|outfit:修身礼服|action:回眸|light:柔光"],
            },
            prompt_count=1,
        )
        self.assertGreaterEqual(params["temperature"], 0.72)
        self.assertGreaterEqual(params["top_p"], 0.9)
        self.assertGreaterEqual(params["frequency_penalty"], 0.18)

    def test_model_refiner_uses_invoke_fallback(self) -> None:
        captured: dict[str, str] = {}

        class DummyLlm:
            def invoke(self, prompt: str) -> str:
                captured["prompt"] = prompt
                return "base prompt refined"

        refined = model_refiner.maybe_model_refine(
            DummyLlm(),
            "base prompt",
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.7, "top_p": 0.9, "模型来源": "本地GGUF"},
            chat_completion=lambda *args, **kwargs: None,
            clean_think_text=lambda text: text.replace(" refined", "++"),
        )
        self.assertEqual(refined, "base prompt++")
        self.assertIn("Skill前置上下文", captured["prompt"])
        self.assertIn("模型来源：本地GGUF", captured["prompt"])
        self.assertIn("待整理提示词正文", captured["prompt"])

    def test_model_refiner_removes_placeholder_fragments_from_api_output(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            "完整画面，环境人像，全景全身，高细节",
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.7, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {
                "text": "完整画面，环境人像，[]，全景全身，True，高细节，False，清晰"
            },
            clean_think_text=lambda text: text,
        )
        self.assertIn("完整画面", refined)
        self.assertIn("全景全身", refined)
        self.assertIn("高细节", refined)
        self.assertNotIn("[]", refined)
        self.assertNotIn("True", refined)
        self.assertNotIn("False", refined)

    def test_model_refiner_rejects_placeholder_only_output(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        original = "完整画面，环境人像，全景全身，高细节"
        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            original,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.7, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {"text": "[]"},
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, original)

    def test_model_refiner_strips_prompt_wrappers(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            "成年女性，中景，废弃教堂",
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.7, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {"text": "成品提示词：\n一张描绘成年女性的画面，废弃教堂，中景，压抑氛围"},
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, "成年女性，废弃教堂，中景，压抑氛围")

    def test_model_refiner_strips_narrative_fillers(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            "成年女性，白衬衫，废弃教堂",
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.7, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {
                "text": "提示词：\n画面中，这个角色身穿白衬衫，站在废弃教堂里，整体呈现压抑氛围，仿佛时间凝固"
            },
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, "身穿白衬衫，站在废弃教堂里，压抑氛围，时间凝固")

    def test_model_refiner_rejects_non_person_prompt_rewritten_as_portrait(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        original = "电影级CG，侦查机甲，机库，全景，高细节；非人物主题，主体结构和功能部件清晰"
        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            original,
            {
                "系统提示词覆盖": "",
                "最大生成token": 256,
                "温度": 0.7,
                "top_p": 0.9,
                "主体类型": "非人物主体",
                "主体类型解析结果": "非人物主体",
                "提示词语言": "纯中文",
            },
            chat_completion=lambda *args, **kwargs: {
                "text": "一位气质高智的东亚成年女性国潮模特，身着修身礼服，细跟高跟鞋，脸部清晰，手指优雅"
            },
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, original)

    def test_model_refiner_rejects_english_human_intrusion_for_non_person(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        original = "cinematic CG, reconnaissance mecha, aircraft hangar, wide shot, detailed armor and functional joints"
        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            original,
            {
                "系统提示词覆盖": "",
                "最大生成token": 256,
                "温度": 0.7,
                "top_p": 0.9,
                "主体类型": "非人物主体",
                "主体类型解析结果": "非人物主体",
                "提示词语言": "纯英文",
            },
            chat_completion=lambda *args, **kwargs: {
                "text": (
                    "An adult woman fashion portrait in a studio, elegant dress, visible face and skin, "
                    "soft beauty lighting, detailed hair, polished editorial background"
                )
            },
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, original)

    def test_model_refiner_rejects_chinese_when_english_language_selected(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        captured: dict[str, Any] = {}

        def fake_chat_completion(*args: Any, **kwargs: Any) -> dict[str, str]:
            captured["messages"] = kwargs.get("messages", [])
            return {"text": "写实摄影，成年女性，卧室，柔光"}

        original = "realistic photography, adult woman, bedroom, soft light"
        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            original,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.7, "top_p": 0.9, "提示词语言": "纯英文"},
            chat_completion=fake_chat_completion,
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, original)
        system_message = str(captured["messages"][0]["content"])
        self.assertIn("English only", system_message)

    def test_model_refiner_enforces_chinese_and_bilingual_language_contracts(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        chinese_original = "写实摄影，成年女性，全景全身，窗边柔光，服装材质清晰"
        chinese_refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            chinese_original,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.7, "top_p": 0.9, "提示词语言": "纯中文"},
            chat_completion=lambda *args, **kwargs: {
                "text": (
                    "全景全身, A cinematic adult portrait beside a rain soaked window, soft directional light, "
                    "detailed fabric, natural anatomy, balanced framing, clear background depth, polished editorial finish"
                )
            },
            clean_think_text=lambda text: text,
        )
        self.assertEqual(chinese_refined, chinese_original)

        bilingual_original = "editorial portrait, adult woman, full body, soft window light"
        bilingual_refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            bilingual_original,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.7, "top_p": 0.9, "提示词语言": "英文提示词+中文说明"},
            chat_completion=lambda *args, **kwargs: {
                "text": "editorial portrait, adult woman, full body, soft window light, detailed fabric"
            },
            clean_think_text=lambda text: text,
        )
        self.assertEqual(bilingual_refined, bilingual_original)

    def test_model_refiner_allows_bilingual_note_when_selected(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        captured: dict[str, Any] = {}

        def fake_chat_completion(*args: Any, **kwargs: Any) -> dict[str, str]:
            captured["messages"] = kwargs.get("messages", [])
            return {"text": "editorial portrait, adult woman, full body, soft window light. 中文说明：全身构图与柔光人像。"}

        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            "editorial portrait, adult woman, full body, soft window light",
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.7, "top_p": 0.9, "提示词语言": "英文提示词+中文说明"},
            chat_completion=fake_chat_completion,
            clean_think_text=lambda text: text,
        )
        self.assertIn("中文说明", refined)
        system_message = str(captured["messages"][0]["content"])
        self.assertIn("中文说明", system_message)

    def test_model_refiner_uses_long_token_budget_for_single_prompt(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        captured: dict[str, Any] = {}

        def fake_chat_completion(*args: Any, **kwargs: Any) -> dict[str, str]:
            captured["params"] = kwargs.get("params", {})
            return {"text": "写实摄影，成年女性，全景全身，柔光，高细节"}

        model_refiner.maybe_model_refine(
            DummyChatLlm(),
            "写实摄影，成年女性，全景全身，柔光",
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.7, "top_p": 0.9},
            chat_completion=fake_chat_completion,
            clean_think_text=lambda text: text,
        )
        self.assertGreaterEqual(captured["params"]["max_tokens"], 1280)

    def test_model_refiner_uses_scaled_token_budget_for_batch(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        captured: dict[str, Any] = {}

        def fake_chat_completion(*args: Any, **kwargs: Any) -> dict[str, str]:
            captured["params"] = kwargs.get("params", {})
            return {"text": "成年女性，全景全身，高细节<<<QWEN_TE_SPLIT>>>成年女性，近景，柔光<<<QWEN_TE_SPLIT>>>成年女性，都市夜景，电影感"}

        model_refiner.maybe_model_refine_batch(
            DummyChatLlm(),
            ["成年女性，全景全身", "成年女性，近景", "成年女性，都市夜景"],
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.62, "top_p": 0.9},
            chat_completion=fake_chat_completion,
            clean_think_text=lambda text: text,
        )
        self.assertGreaterEqual(captured["params"]["max_tokens"], 3840)
        self.assertGreaterEqual(captured["params"]["temperature"], 0.72)
        self.assertGreaterEqual(captured["params"]["repeat_penalty"], 1.1)
        self.assertGreaterEqual(captured["params"]["frequency_penalty"], 0.18)
        self.assertGreaterEqual(captured["params"]["presence_penalty"], 0.1)
        self.assertIn("top_k", captured["params"])

    def test_model_refiner_batch_prompt_includes_per_item_diversity_contract(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        captured: dict[str, Any] = {}

        def fake_chat_completion(*args: Any, **kwargs: Any) -> dict[str, str]:
            captured["messages"] = kwargs.get("messages", [])
            return {
                "text": "成年女性，废弃教堂，中景，冷调柔光<<<QWEN_TE_SPLIT>>>成年女性，校园，近景，暖调窗光"
            }

        model_refiner.maybe_model_refine_batch(
            DummyChatLlm(),
            ["成年女性，中景，废弃教堂，冷调柔光", "成年女性，近景，校园，暖调窗光"],
            {
                "系统提示词覆盖": "",
                "最大生成token": 256,
                "温度": 0.62,
                "top_p": 0.9,
                "模型来源": "API接口",
                "运行时随机模式解析结果": "全随机",
                "NSFW工作台标签摘要": "已启用；映射标签：柔光",
                "标签块编排摘要": "场景: 废弃教堂 -> 场景: 校园",
            },
            chat_completion=fake_chat_completion,
            clean_think_text=lambda text: text,
        )
        user_message = str(captured["messages"][1]["content"])
        self.assertIn("差异化合同", user_message)
        self.assertIn("第1条差异锚点", user_message)
        self.assertIn("废弃教堂", user_message)
        self.assertIn("第2条差异锚点", user_message)
        self.assertIn("校园", user_message)
        self.assertIn("NSFW 工作台素材", user_message)
        self.assertIn("标签块编排顺序", user_message)

    def test_model_refiner_batch_preserves_order(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        refined = model_refiner.maybe_model_refine_batch(
            DummyChatLlm(),
            ["成年女性，中景，废弃教堂", "成年女性，近景，校园"],
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.62, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {"text": "成年女性，废弃教堂，中景<<<QWEN_TE_SPLIT>>>成年女性，校园，近景"},
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, ["成年女性，废弃教堂，中景", "成年女性，校园，近景"])

    def test_model_refiner_rejects_analysis_scaffold(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        original = "写实摄影，成年女性，白衬衫，校园，柔光，85mm人像镜头"
        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            original,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.62, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {"text": "1. 分析用户请求：核心主题：写实摄影。2. 理解输入：需要自然、诗意、自述风格。"},
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, original)

    def test_model_refiner_rejects_repetition_spam(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        original = "写实摄影，成年女性，海边，黄昏，黑长直，丝绒礼服，85mm人像镜头"
        spam = "写实摄影，成年女性，海边，黄昏，巨大，巨大，巨大，巨大，巨大，巨大，巨大，巨大"
        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            original,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.62, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {"text": spam},
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, original)

    def test_model_refiner_dedupes_repeated_api_fragments(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        original = "写实摄影，成年女性，海边，黄昏，柔光，高细节"
        repeated = "写实摄影，成年女性，海边，黄昏，柔光，高细节，成年女性，海边，柔光，高细节，成年女性，海边，柔光"
        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            original,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.62, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {"text": repeated},
            clean_think_text=lambda text: text,
        )
        self.assertLessEqual(refined.count("海边"), 1)
        self.assertLessEqual(refined.count("成年女性"), 1)
        self.assertLessEqual(refined.count("柔光"), 1)

    def test_model_refiner_rejects_style_only_positive_prompt(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        original = "电影级CG，成年女性，粉色汉服，角色设定图，头像特写，全身，正面视图，侧面视图，背面视图，白底棚拍，高细节"
        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            original,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.62, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {"text": "CG感"},
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, original)

    def test_model_refiner_batch_falls_back_for_invalid_items(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        prompts = ["成年女性，废弃教堂，中景", "成年女性，校园，近景"]
        refined = model_refiner.maybe_model_refine_batch(
            DummyChatLlm(),
            prompts,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.62, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {
                "text": "成年女性，废弃教堂，中景<<<QWEN_TE_SPLIT>>>1. 分析用户请求：核心主题：校园肖像"
            },
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, ["成年女性，废弃教堂，中景", "成年女性，校园，近景"])

    def test_model_refiner_batch_rejects_duplicate_outputs(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        prompts = ["成年女性，废弃教堂，中景", "成年女性，校园，近景"]
        refined = model_refiner.maybe_model_refine_batch(
            DummyChatLlm(),
            prompts,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.62, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {
                "text": "成年女性，废弃教堂，中景<<<QWEN_TE_SPLIT>>>成年女性，废弃教堂，中景"
            },
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, ["成年女性，废弃教堂，中景", "成年女性，校园，近景"])

    def test_model_refiner_preserves_half_body_composition_anchor(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        original = "写实摄影，成年女性，校园，中景半身，85mm人像镜头"
        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            original,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.62, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {"text": "写实摄影，成年女性，校园，中景构图，85mm人像镜头"},
            clean_think_text=lambda text: text,
        )
        self.assertIn("中景半身", refined)

    def test_model_refiner_restores_missing_half_body_composition_anchor(self) -> None:
        class DummyChatLlm:
            def create_chat_completion(self, *args, **kwargs):
                return None

        original = "写实摄影，成年女性，校园，中景半身，85mm人像镜头"
        refined = model_refiner.maybe_model_refine(
            DummyChatLlm(),
            original,
            {"系统提示词覆盖": "", "最大生成token": 256, "温度": 0.62, "top_p": 0.9},
            chat_completion=lambda *args, **kwargs: {"text": "写实摄影，成年女性，校园，85mm人像镜头，视觉中心集中"},
            clean_think_text=lambda text: text,
        )
        self.assertIn("中景半身", refined)

    def test_disabled_quick_presets_are_removed(self) -> None:
        disabled = {
            "运行时弱随机",
            "运行时强随机",
            "成人私房",
            "白底低遮挡私房",
            "男性低遮挡轮廓",
        }
        self.assertTrue(disabled.isdisjoint(set(tag_library.快速推荐组合.keys())))

    def test_nsfw_workspace_defaults_include_expected_preset_fields(self) -> None:
        defaults = nsfw_presets.build_nsfw_workspace_defaults()
        self.assertFalse(defaults["enabled"])
        self.assertEqual(defaults["negative_preset"], "标准负面提示词")
        self.assertEqual(defaults["random_mode"], "关闭")
        self.assertEqual(defaults["quality_tier"], "高质量")
        self.assertEqual(defaults["anatomy_terms"], "——")
        self.assertEqual(defaults["explicit_terms"], "——")
        self.assertEqual(defaults["adult_action_style"], "——")
        self.assertIn("custom_negative", defaults)

    def test_nsfw_workspace_catalog_exposes_negative_presets(self) -> None:
        catalog = nsfw_workspace.build_nsfw_workspace_catalog()
        self.assertEqual(catalog["defaults"]["preset"], "——")
        self.assertIn("标准负面提示词", catalog["negative_presets"])
        self.assertIn("自定义负面提示词", catalog["negative_presets"])
        self.assertIn("options", catalog)
        self.assertIn("presets", catalog)
        self.assertIn("quality_tags", catalog)
        self.assertIn("豪华卧室，红色丝绒床单，镜面天花板", catalog["options"]["scene"])
        self.assertIn("经典情色", catalog["presets"])
        self.assertIn("masterpiece", catalog["quality_tags"]["高质量"])
        self.assertIn("高强度成人氛围", catalog["presets"])
        self.assertIn("成人氛围增强", catalog["quality_tags"])
        self.assertIn("anatomy_terms", catalog["options"])
        for required in ("乳房", "乳头", "外阴", "阴道", "阴蒂", "阴茎"):
            self.assertIn(required, catalog["options"]["anatomy_terms"])
        self.assertIn("explicit_terms", catalog["options"])
        for required in ("性交", "插入", "自慰", "潮吹"):
            self.assertIn(required, catalog["options"]["explicit_terms"])
        self.assertIn("adult_action_style", catalog["options"])
        for required in ("单人私密姿态", "脱衣动作", "弯腰姿态", "跨坐互动", "口部亲密互动", "车内亲密氛围", "主从感跪姿互动", "多人亲密氛围"):
            self.assertTrue(any(required in option for option in catalog["options"]["adult_action_style"]))
        for required_field in ("selector_character", "selector_outfit", "selector_action", "selector_scene", "selector_expression", "selector_prop"):
            self.assertIn(required_field, catalog["defaults"])
            self.assertIn(required_field, catalog["options"])
        self.assertIn("女仆", catalog["options"]["selector_character"])
        self.assertIn("内衣", catalog["options"]["selector_outfit"])
        self.assertIn("接吻", catalog["options"]["selector_action"])
        self.assertIn("温泉", catalog["options"]["selector_scene"])
        self.assertIn("诱惑视线", catalog["options"]["selector_expression"])
        self.assertIn("成人道具", catalog["options"]["selector_prop"])
        self.assertIn("内衣", nsfw_presets.NSFW_WORKSPACE_SIGNAL_TERMS)
        for required in ("镂空蕾丝内衣", "紧身乳胶装", "情趣吊带袜", "皮质束缚装"):
            self.assertTrue(any(required in option for option in catalog["options"]["outfit"]))
        for required in ("欲念张力", "禁忌诱惑", "支配感", "强烈感官氛围"):
            self.assertTrue(any(required in option for option in catalog["options"]["mood"]))
        for required in ("360度环绕", "低角度慢扫", "快速变焦"):
            self.assertTrue(any(required in option for option in catalog["options"]["camera_movement"]))
        for required in ("粉紫霓虹光", "彩色渐变光"):
            self.assertTrue(any(required in option for option in catalog["options"]["light_source"]))
        for required in ("炽热红色调", "冷艳紫色调", "金色调"):
            self.assertTrue(any(required in option for option in catalog["options"]["color_tone"]))
        for required in ("复古禁忌风", "超现实私密", "艺术情欲风"):
            self.assertTrue(any(required in option for option in catalog["options"]["visual_style"]))
        self.assertIn("阴道", catalog["presets"]["高强度成人氛围"]["anatomy_terms"])
        self.assertIn("性交", catalog["presets"]["高强度成人氛围"]["explicit_terms"])
        self.assertIn("双人亲密互动", catalog["presets"]["高强度成人氛围"]["adult_action_style"])
        self.assertNotIn("anatomy_terms", nsfw_mapper._RANDOM_ALL_FIELDS)
        self.assertNotIn("explicit_terms", nsfw_mapper._RANDOM_ALL_FIELDS)
        self.assertNotIn("adult_action_style", nsfw_mapper._RANDOM_ALL_FIELDS)

    def test_nsfw_workspace_catalog_exposes_global_style_tracks(self) -> None:
        catalog = nsfw_workspace.build_nsfw_workspace_catalog()
        visual_styles = set(catalog["options"].get("visual_style", []))
        for required in ("高端时尚编辑肖像", "都市电影人文", "港式武侠胶片", "日韩影像", "东方赛博武侠朋克"):
            self.assertIn(required, visual_styles)

    def test_stage_generator_output_contract_matches_ui_slots(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        node_class = getattr(module, "QwenTE阶段式提示词生成器")
        self.assertEqual(node_class.RETURN_TYPES, ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING"))
        self.assertEqual(
            node_class.RETURN_NAMES,
            ("结果全文", "首条正向提示词", "已选标签", "JSON结果", "推荐负面词", "正向提示词合集", "智能文本"),
        )
        self.assertTrue(node_class.OUTPUT_NODE)
        input_types = node_class.INPUT_TYPES()
        self.assertEqual(input_types["optional"]["参考图片"], ("IMAGE",))
        self.assertIn("图片反推生成", input_types["required"])
        self.assertIn("图片反推模式", input_types["required"])
        for group_name in ("主体", "画面风格", "成人向表达", "光影氛围", "构图视角", "动作姿态", "服装造型", "场景背景", "道具世界观", "技术画质"):
            self.assertIn(f"{group_name}标签10", input_types["required"])
            self.assertNotIn(f"{group_name}标签11", input_types["required"])

    def test_character_sheet_reverse_prompt_does_not_lock_visual_theme(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        prompt = module._build_image_reverse_prompt({"图片反推模式": "角色设定图"})
        self.assertIn("正面全身", prompt)
        self.assertIn("跟随参考图与用户输入", prompt)
        self.assertIn("不要锁定白底、古风、汉服或固定颜色", prompt)
        self.assertNotIn("白底棚拍", prompt)
        self.assertNotIn("粉色汉服", prompt)

    def test_character_sheet_strategy_uses_global_prompt_without_reference_image(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        selected = OrderedDict({"主体": ["机械少女"], "服装造型": ["黑色礼服"], "场景背景": ["雾夜街道"]})
        custom_tags = ["银发", "冷色调"]
        settings = {
            "图片反推生成": True,
            "图片反推模式": "角色设定图",
            "智能文本匹配": False,
            "智能文本输入": "",
            "额外要求": "保留哥特气质，不要白底棚拍",
            "推理纠偏说明": [],
        }
        applied = module._apply_character_sheet_to_settings(
            settings,
            selected,
            custom_tags,
            image_reverse_text="",
            has_reference_image=False,
        )
        self.assertTrue(applied)
        self.assertTrue(settings["智能文本匹配"])
        self.assertEqual(settings["图片反推模式"], "角色设定图")
        self.assertIn("纯提示词模式", settings["智能文本输入"])
        self.assertIn("机械少女", settings["智能文本输入"])
        self.assertIn("雾夜街道", settings["智能文本输入"])
        self.assertIn("多视角角色展示", settings["智能文本输入"])
        self.assertIn("正面全身", settings["额外要求"])
        self.assertNotIn("不要自行锁定", settings["额外要求"])
        self.assertNotIn("生成目标", settings["智能文本输入"])
        self.assertIn("角色设定图策略", "\n".join(settings["推理纠偏说明"]))

    def test_character_sheet_pure_english_keeps_multiview_semantics(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module._run_stage(
            None,
            **{
                "unique_id": "character-sheet-pure-english",
                "主体标签1": "成年女性",
                "画面风格标签1": "CG感",
                "图片反推生成": True,
                "图片反推模式": "角色设定图",
                "提示词语言": "纯英文",
                "模板风格": "CG感",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "seed": 23,
            },
        )
        prompt = result[1]
        self.assertNotRegex(prompt, r"[\u4e00-\u9fff]")
        for required in (
            "character sheet",
            "multi-view character turnaround",
            "front full-body view",
            "side full-body view",
            "back full-body view",
        ):
            self.assertIn(required, prompt)

    def test_character_sheet_strategy_merges_reference_reverse_without_theme_lock(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        selected = OrderedDict({"主体": ["角色设定图"], "画面风格": ["真实感"]})
        settings = {
            "图片反推生成": True,
            "图片反推模式": "角色设定图",
            "智能文本匹配": False,
            "智能文本输入": "保留参考图发型",
            "额外要求": "",
            "推理纠偏说明": [],
        }
        module._apply_character_sheet_to_settings(
            settings,
            selected,
            [],
            image_reverse_text="粉色长袍，侧面站姿，柔光背景",
            has_reference_image=True,
        )
        self.assertIn("参考单人图模式", settings["智能文本输入"])
        self.assertIn("粉色长袍", settings["智能文本输入"])
        self.assertIn("保留参考图发型", settings["智能文本输入"])
        self.assertIn("粉色长袍", settings["额外要求"])
        self.assertNotIn("白底棚拍", settings["智能文本输入"])
        self.assertNotIn("固定颜色", settings["额外要求"])

    def test_character_sheet_strategy_strips_reference_reasoning_and_rule_text(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        selected = OrderedDict(
            {
                "主体": ["成年女性", "银白长发"],
                "画面风格": ["时装广告大片"],
                "服装造型": ["修身礼服"],
                "场景背景": ["摄影棚"],
            }
        )
        settings = {
            "图片反推生成": True,
            "图片反推模式": "角色设定图",
            "智能文本匹配": False,
            "智能文本输入": "当前全局提示词上下文：防御机甲，高马尾，古风建筑",
            "额外要求": "生成目标：把上述内容组织为三视图；输出要求：不要输出规则解释",
            "推理纠偏说明": [],
        }
        reference_text = (
            "Thinking Process: 1. **Analyze the Request:** **Role:** AI Painting Reference Image Inversion Assistant. "
            "**Output Requirements:** no JSON. 2. **Analyze the Reference Image:** "
            "* **Subject:** Young woman, confident temperament. "
            "* **Hair:** silver white long braided hair, loose strands framing face. "
            "* **Clothing:** black leather jacket, cream silk blouse, silver hardware."
        )
        module._apply_character_sheet_to_settings(
            settings,
            selected,
            [],
            image_reverse_text=reference_text,
            has_reference_image=True,
        )
        combined = f"{settings['智能文本输入']}\n{settings['额外要求']}"
        for banned in (
            "Thinking Process",
            "Analyze the Request",
            "Output Requirements",
            "当前全局提示词上下文",
            "参考图反推上下文",
            "生成目标",
            "输出要求",
            "Role:",
        ):
            self.assertNotIn(banned, combined)
        self.assertIn("Young woman", combined)
        self.assertIn("silver white long braided hair", combined)
        self.assertIn("black leather jacket", combined)
        self.assertIn("多视角角色展示", combined)
        self.assertIn("角色设定图内部策略", settings["角色设定图内部策略"])

    def test_smart_text_matches_free_text_to_stage_tags(self) -> None:
        selected = OrderedDict({"主体": [], "画面风格": [], "成人向表达": [], "场景背景": [], "构图视角": [], "技术画质": []})
        custom_tags: list[str] = []
        settings = {"模板风格": "自动", "主体类型": "自动", "标签反推模式": "自动平衡"}
        available = {"成年女性", "私房写真", "内衣风", "中景半身", "全景全身", "浴室", "温泉雾气", "湿发", "杂志编辑摄影", "面部聚焦", "85mm人像镜头"}
        tag_group_index = {
            "成年女性": "主体",
            "私房写真": "画面风格",
            "内衣风": "成人向表达",
            "中景半身": "构图视角",
            "全景全身": "构图视角",
            "浴室": "场景背景",
            "温泉雾气": "场景背景",
            "湿发": "主体",
            "杂志编辑摄影": "画面风格",
            "面部聚焦": "构图视角",
            "85mm人像镜头": "构图视角",
        }

        def append_tag(next_selected, next_custom, tag):
            group = tag_group_index.get(tag)
            if group and group in next_selected:
                next_selected[group].append(tag)
            else:
                next_custom.append(tag)

        selected, custom_tags, notes = smart_text.apply_smart_text_to_state(
            selected,
            custom_tags,
            settings,
            text="杂志封面感，成年女性浴室蒸汽私房，湿发内衣",
            available_tags=available,
            tag_group_index=tag_group_index,
            append_tag_to_state=append_tag,
        )
        all_tags = collect_all_tags(selected, custom_tags)
        self.assertIn("杂志编辑摄影", all_tags)
        self.assertIn("成年女性", all_tags)
        self.assertIn("私房写真", all_tags)
        self.assertIn("全景全身", all_tags)
        self.assertEqual(settings["标签反推模式"], "成人向成熟")
        self.assertTrue(any("智能文本匹配" in note for note in notes))

    def test_smart_text_infers_practical_hair_tags(self) -> None:
        available = {"短发", "齐耳短发", "长发", "及腰长发", "空气刘海", "黑发"}
        inferred = smart_text.infer_smart_text_tags("黑发短发，空气刘海，也可以换成长发", available)
        self.assertIn("短发", inferred)
        self.assertIn("齐耳短发", inferred)
        self.assertIn("长发", inferred)
        self.assertIn("空气刘海", inferred)
        self.assertIn("黑发", inferred)

    def test_smart_text_short_ascii_tags_require_token_boundaries(self) -> None:
        inferred = smart_text.infer_smart_text_tags(
            "bold color grading with soft volumetric light",
            {"OL", "HDR"},
        )
        self.assertNotIn("OL", inferred)
        self.assertIn("OL", smart_text.infer_smart_text_tags("OL office portrait", {"OL"}))
        self.assertFalse(smart_text._contains_marker("woman portrait", "man"))

    def test_smart_text_infers_practical_portrait_control_tags(self) -> None:
        available = {
            "清晰下颌线",
            "看向镜头",
            "脚部完整入镜",
            "人物完整入镜",
            "自然透视",
            "落地窗",
            "短靴",
            "缎面",
            "真丝",
            "露肩设计",
            "景深控制稳定",
            "焦点落在面部",
            "背景不过分抢镜",
            "双眼清晰",
            "手部结构自然",
            "浅笑",
            "裸妆",
            "托腮",
            "轻抚衣角",
        }
        inferred = smart_text.infer_smart_text_tags(
            "下颌线清晰，看镜头，落地窗边，缎面裙和短靴，全身脚部完整，自然透视，双眼清晰，手部结构自然，浅笑，裸妆，托腮，轻抚衣角",
            available,
        )
        self.assertIn("清晰下颌线", inferred)
        self.assertIn("看向镜头", inferred)
        self.assertIn("脚部完整入镜", inferred)
        self.assertIn("人物完整入镜", inferred)
        self.assertIn("自然透视", inferred)
        self.assertIn("落地窗", inferred)
        self.assertIn("短靴", inferred)
        self.assertIn("缎面", inferred)
        self.assertIn("双眼清晰", inferred)
        self.assertIn("手部结构自然", inferred)
        self.assertIn("浅笑", inferred)
        self.assertIn("裸妆", inferred)
        self.assertIn("托腮", inferred)
        self.assertIn("轻抚衣角", inferred)

    def test_smart_text_infers_practical_clothing_and_quality_tags(self) -> None:
        available = {
            "真丝",
            "蕾丝",
            "针织纹理",
            "露肩设计",
            "高领结构",
            "短外套",
            "长外套",
            "开衩设计",
            "景深控制稳定",
            "焦点落在面部",
            "边缘干净",
            "背景不过分抢镜",
        }
        inferred = smart_text.infer_smart_text_tags(
            "真丝蕾丝，露肩设计，短外套，开衩，景深稳定，焦点在脸上，边缘干净，背景不要抢镜",
            available,
        )
        self.assertIn("真丝", inferred)
        self.assertIn("蕾丝", inferred)
        self.assertIn("露肩设计", inferred)
        self.assertIn("短外套", inferred)
        self.assertIn("开衩设计", inferred)
        self.assertIn("景深控制稳定", inferred)
        self.assertIn("焦点落在面部", inferred)
        self.assertIn("边缘干净", inferred)
        self.assertIn("背景不过分抢镜", inferred)

    def test_smart_text_infers_reference_quality_and_camera_vocabulary(self) -> None:
        available = {
            "35mm胶片摄影",
            "大画幅棚拍",
            "黄金时刻侧光",
            "黑色电影硬光",
            "俯视平铺",
            "过肩镜头",
            "200mm长焦压缩",
            "中画幅质感",
            "广告成片质感",
        }
        inferred = smart_text.infer_smart_text_tags(
            "35mm film photograph, large-format studio, golden-hour side-light, hard noir key-light, top-down flat-lay, over-the-shoulder, 200mm long-lens compression, large-format finish",
            available,
        )
        self.assertIn("35mm胶片摄影", inferred)
        self.assertIn("大画幅棚拍", inferred)
        self.assertIn("黄金时刻侧光", inferred)
        self.assertIn("黑色电影硬光", inferred)
        self.assertIn("俯视平铺", inferred)
        self.assertIn("中画幅质感", inferred)

    def test_smart_text_infers_reference_lens_and_film_patina_vocabulary(self) -> None:
        available = {
            "红雾表现主义打光",
            "复古非镀膜镜头",
            "RGB轻微分离",
            "轻微色差",
            "柔和光晕",
            "老胶片褪色感",
            "港片胶片质感",
            "青蓝冷雾",
        }
        inferred = smart_text.infer_smart_text_tags(
            "red mist expressionist lighting, old uncoated glass lens, subtle RGB split, slight chromatic aberration, soft halation, faded old-film look, Hong Kong film stock texture, blue-cyan cold mist",
            available,
        )
        self.assertIn("红雾表现主义打光", inferred)
        self.assertIn("复古非镀膜镜头", inferred)
        self.assertIn("RGB轻微分离", inferred)
        self.assertIn("轻微色差", inferred)
        self.assertIn("柔和光晕", inferred)
        self.assertIn("老胶片褪色感", inferred)
        self.assertIn("港片胶片质感", inferred)
        self.assertIn("青蓝冷雾", inferred)

    def test_smart_text_infers_body_shape_and_camera_tags(self) -> None:
        available = {
            "长腿",
            "腿部修长",
            "腰臀曲线自然",
            "骨架轻盈",
            "肩宽适中",
            "锁骨明显",
            "人物居中",
            "负空间留白",
            "纵向构图",
            "海报主视觉",
            "浅景深",
            "镜头近距离",
            "35mm镜头",
            "50mm标准镜头",
            "85mm人像镜头",
        }
        inferred = smart_text.infer_smart_text_tags(
            "长腿，腿部修长，腰臀曲线自然，骨架轻盈，肩宽适中，锁骨明显，人物居中，负空间留白，纵向构图，海报主视觉，浅景深，镜头近距离，85mm人像镜头",
            available,
        )
        self.assertIn("长腿", inferred)
        self.assertIn("腿部修长", inferred)
        self.assertIn("腰臀曲线自然", inferred)
        self.assertIn("骨架轻盈", inferred)
        self.assertIn("肩宽适中", inferred)
        self.assertIn("锁骨明显", inferred)
        self.assertIn("人物居中", inferred)
        self.assertIn("负空间留白", inferred)
        self.assertIn("纵向构图", inferred)
        self.assertIn("海报主视觉", inferred)
        self.assertIn("浅景深", inferred)
        self.assertIn("镜头近距离", inferred)
        self.assertIn("85mm人像镜头", inferred)

    def test_smart_text_infers_accessories_and_props(self) -> None:
        available = {
            "耳环",
            "项链",
            "眼镜",
            "手提包",
            "托特包",
            "斜挎包",
            "相机",
            "手机",
            "手持咖啡杯",
            "书本",
            "雨伞",
            "耳机",
        }
        inferred = smart_text.infer_smart_text_tags(
            "戴着耳环和项链，扶眼镜，背着托特包，手里拿着相机、手机、咖啡杯和书本，雨伞与耳机也在旁边",
            available,
        )
        self.assertIn("耳环", inferred)
        self.assertIn("项链", inferred)
        self.assertIn("扶眼镜", inferred)
        self.assertIn("托特包", inferred)
        self.assertIn("相机", inferred)
        self.assertIn("手机", inferred)
        self.assertIn("手持咖啡杯", inferred)
        self.assertIn("书本", inferred)
        self.assertIn("雨伞", inferred)
        self.assertIn("耳机", inferred)

    def test_smart_text_infers_hair_and_accessory_variants(self) -> None:
        available = {
            "高马尾",
            "双马尾",
            "法式刘海",
            "龙须刘海",
            "红发",
            "紫发",
            "墨镜",
            "珍珠耳环",
            "耳钉",
            "胸针",
            "摄影包",
            "单反相机",
            "背包",
        }
        inferred = smart_text.infer_smart_text_tags(
            "高马尾、双马尾、法式刘海、龙须刘海、红发、紫发，戴墨镜和珍珠耳环，别着胸针，背着摄影包，拿着单反相机和背包",
            available,
        )
        self.assertIn("高马尾", inferred)
        self.assertIn("双马尾", inferred)
        self.assertIn("法式刘海", inferred)
        self.assertIn("龙须刘海", inferred)
        self.assertIn("红发", inferred)
        self.assertIn("紫发", inferred)
        self.assertIn("墨镜", inferred)
        self.assertIn("珍珠耳环", inferred)
        self.assertIn("胸针", inferred)
        self.assertIn("摄影包", inferred)
        self.assertIn("单反相机", inferred)

    def test_smart_text_infers_random_archive_editorial_and_fantasy_terms(self) -> None:
        available = {
            "书店女孩",
            "影棚时尚女性",
            "独立书店",
            "影棚纯色背景",
            "白色斗篷",
            "黑金重甲",
            "银白雕花重甲",
            "神圣骑士",
            "冰霜骑士",
            "炎魔天使",
            "神官长袍",
            "鎏金头冠",
            "日轮",
            "月轮",
            "圣火",
            "权杖",
        }
        inferred = smart_text.infer_smart_text_tags(
            "影棚时尚女性，独立书店，影棚纯色背景，white cloak, black-gold heavy armor, silver-white engraved heavy armor, holy knight, frost knight, infernal angel, high priest ceremonial robe, gilded ceremonial crown, sun disc, moon disc, sacred flame, scepter",
            available,
        )
        self.assertIn("影棚时尚女性", inferred)
        self.assertIn("独立书店", inferred)
        self.assertIn("影棚纯色背景", inferred)
        self.assertIn("白色斗篷", inferred)
        self.assertIn("黑金重甲", inferred)
        self.assertIn("银白雕花重甲", inferred)
        self.assertIn("神圣骑士", inferred)
        self.assertIn("冰霜骑士", inferred)
        self.assertIn("炎魔天使", inferred)
        self.assertIn("神官长袍", inferred)
        self.assertIn("鎏金头冠", inferred)
        self.assertIn("日轮", inferred)
        self.assertIn("月轮", inferred)
        self.assertIn("圣火", inferred)
        self.assertIn("权杖", inferred)

    def test_smart_text_infers_runtime_archive_extended_scene_and_identity_terms(self) -> None:
        available = {
            "居家游戏女孩",
            "湖畔金发女性",
            "女武士",
            "图书馆",
            "雨后街头",
            "霓虹街区",
            "工业废墟",
            "北欧海岸",
            "冰冻森林",
            "黑铁王座",
            "火山洞穴",
            "云端阶梯",
        }
        inferred = smart_text.infer_smart_text_tags(
            "homebody gamer girl, blonde woman by the lakeside, female warrior, library, street after rain, neon district, industrial ruins, Nordic coast, frozen forest, black iron throne, volcanic cave, stairway above the clouds",
            available,
        )
        self.assertIn("居家游戏女孩", inferred)
        self.assertIn("湖畔金发女性", inferred)
        self.assertIn("女武士", inferred)
        self.assertIn("图书馆", inferred)
        self.assertIn("雨后街头", inferred)
        self.assertIn("霓虹街区", inferred)
        self.assertIn("工业废墟", inferred)
        self.assertIn("北欧海岸", inferred)
        self.assertIn("冰冻森林", inferred)
        self.assertIn("黑铁王座", inferred)
        self.assertIn("火山洞穴", inferred)
        self.assertIn("云端阶梯", inferred)

    def test_smart_text_infers_mythic_archive_roles_and_scenes(self) -> None:
        available = {
            "神女",
            "祭司",
            "魔女",
            "女冒险者",
            "古建道场",
            "月下庭院",
            "神圣祭坛",
            "星海神殿",
            "悬空神庙",
            "露背礼服",
        }
        inferred = smart_text.infer_smart_text_tags(
            "goddess, priestess, sorceress, female adventurer, ancient training hall, moonlit courtyard, sacred altar, star-sea temple, suspended sky temple, backless gown",
            available,
        )
        self.assertIn("神女", inferred)
        self.assertIn("祭司", inferred)
        self.assertIn("魔女", inferred)
        self.assertIn("女冒险者", inferred)
        self.assertIn("古建道场", inferred)
        self.assertIn("月下庭院", inferred)
        self.assertIn("神圣祭坛", inferred)
        self.assertIn("星海神殿", inferred)
        self.assertIn("悬空神庙", inferred)
        self.assertIn("露背礼服", inferred)

    def test_smart_text_infers_runtime_archive_extended_visual_terms_from_english(self) -> None:
        available = {
            "银白长发",
            "中分短发",
            "古风建筑",
            "宗教圣所",
            "咖啡厅",
            "画室",
            "飞鱼服",
            "宽袖法袍",
            "劲装",
            "手持相机",
        }
        inferred = smart_text.infer_smart_text_tags(
            "long silver-white hair, center-parted short hair, classical Chinese architecture, religious sanctuary, cafe, art studio, flying fish robe, wide-sleeved ceremonial robe, martial outfit, holding a camera",
            available,
        )
        self.assertIn("银白长发", inferred)
        self.assertIn("中分短发", inferred)
        self.assertIn("古风建筑", inferred)
        self.assertIn("宗教圣所", inferred)
        self.assertIn("咖啡厅", inferred)
        self.assertIn("画室", inferred)
        self.assertIn("飞鱼服", inferred)
        self.assertIn("宽袖法袍", inferred)
        self.assertIn("劲装", inferred)
        self.assertIn("手持相机", inferred)

    def test_smart_text_infers_case_example_role_scene_and_colossus_terms(self) -> None:
        available = {
            "城市屋顶纪实",
            "城市天台",
            "屋顶晾衣架",
            "日落逆光",
            "有线耳机",
            "侧脸构图",
            "山谷圣城",
            "巨构神殿",
            "瀑布峡谷",
            "远山雪峰",
            "史诗城市中轴",
            "山体建筑一体化",
            "树灵巨像",
            "古木守卫",
            "工业舱室",
            "巨物压迫近景",
            "朽木树皮纹理",
            "苔藓附生质感",
            "发光裂隙",
        }
        inferred = smart_text.infer_smart_text_tags(
            "urban rooftop documentary mood, city rooftop, rooftop clothesline frame, sunset backlight, wired earphones, profile composition, holy city in a mountain valley, megastructure temple, waterfall canyon, snow peaks in the far distance, epic city central axis, mountain-integrated architecture, colossal tree spirit, ancient wood guardian, industrial chamber, intimidating colossal close shot, rotted bark texture, moss-covered overgrowth texture, glowing fissures",
            available,
        )
        self.assertIn("城市屋顶纪实", inferred)
        self.assertIn("城市天台", inferred)
        self.assertIn("屋顶晾衣架", inferred)
        self.assertIn("日落逆光", inferred)
        self.assertIn("有线耳机", inferred)
        self.assertIn("侧脸构图", inferred)
        self.assertIn("山谷圣城", inferred)
        self.assertIn("巨构神殿", inferred)
        self.assertIn("瀑布峡谷", inferred)
        self.assertIn("远山雪峰", inferred)
        self.assertIn("史诗城市中轴", inferred)
        self.assertIn("山体建筑一体化", inferred)
        self.assertIn("树灵巨像", inferred)
        self.assertIn("古木守卫", inferred)
        self.assertIn("工业舱室", inferred)
        self.assertIn("巨物压迫近景", inferred)
        self.assertIn("朽木树皮纹理", inferred)
        self.assertIn("苔藓附生质感", inferred)
        self.assertIn("发光裂隙", inferred)

    def test_fallback_smart_text_weaves_runtime_archive_terms(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="影棚时尚女性，独立书店，白色斗篷，神官长袍，柔和光晕，日轮，权杖",
            primary_prompt="高端时尚编辑肖像，成年女性，中景半身，电影胶片look",
        )
        self.assertIn("影棚时尚女性", text)
        self.assertIn("独立书店", text)
        self.assertIn("白色斗篷", text)
        self.assertIn("神官长袍", text)
        self.assertIn("柔和光晕", text)
        self.assertIn("日轮", text)
        self.assertIn("权杖", text)

    def test_fallback_smart_text_prioritizes_outfit_terms_under_term_pressure(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="神话感，成年女性，云海，体积神光，全景全身，伸手触碰，权杖，细节A，细节B，细节C，细节D，细节E，细节F，细节G，细节H，细节I，白色斗篷，神官长袍，鎏金头冠",
            primary_prompt="神话史诗感，成年女性",
        )
        self.assertIn("白色斗篷", text)
        self.assertIn("神官长袍", text)
        self.assertIn("鎏金头冠", text)

    def test_fallback_smart_text_prioritizes_track_specific_commercial_terms(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="高端时尚编辑肖像，国潮模特，极简白棚，高窗冷天光，修身礼服，手提包，细节A，细节B，细节C，细节D，细节E，细节F",
            primary_prompt="时尚编辑商业广告，成年女性，中景半身，广告成片质感",
        )
        self.assertIn("极简白棚", text)
        self.assertIn("高窗冷天光", text)
        self.assertIn("修身礼服", text)
        self.assertIn("手提包", text)

    def test_fallback_smart_text_prioritizes_track_specific_cyber_terms(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="东方赛博武侠朋克，特工，赛博地铁，全息投影光，机能外套，能量刀，耳机，细节A，细节B，细节C，细节D，细节E",
            primary_prompt="东方赛博武侠朋克，成年女性，全景全身，电影级CG",
        )
        self.assertIn("赛博地铁", text)
        self.assertIn("全息投影光", text)
        self.assertIn("机能外套", text)
        self.assertIn("能量刀", text)

    def test_fallback_smart_text_uses_track_defaults_for_sparse_cyber_context(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="成年女性，全景全身，高细节",
            primary_prompt="电影级CG，完整人物入镜",
            style_track="东方赛博武侠朋克",
        )
        self.assertIn("赛博街区", text)
        self.assertIn("机能外套", text)
        self.assertIn("全息投影光", text)
        self.assertIn("能量刀", text)

    def test_fallback_smart_text_uses_track_defaults_for_sparse_mythic_context(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="成年女性，全景全身，高细节",
            primary_prompt="神话史诗感，完整人物入镜",
            style_track="神殿史诗",
        )
        self.assertIn("神殿", text)
        self.assertIn("神官长袍", text)
        self.assertIn("圣辉逆光", text)
        self.assertIn("权杖", text)

    def test_fallback_smart_text_uses_track_defaults_for_sparse_rooftop_documentary_context(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="成年女性，中景半身，高细节",
            primary_prompt="真实感，完整人物入镜",
            style_track="城市天台纪实",
        )
        self.assertIn("城市天台", text)
        self.assertIn("有线耳机", text)
        self.assertTrue(any(term in text for term in ("日落逆光", "金色侧逆光")))
        self.assertTrue(any(term in text for term in ("长款大衣", "宽松外套", "针织开衫", "短外套")))

    def test_fallback_smart_text_uses_track_defaults_for_sparse_epic_city_context(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="大全景，高细节",
            primary_prompt="神话史诗感，非人物主体",
            style_track="山谷圣城史诗",
        )
        self.assertIn("山谷圣城", text)
        self.assertIn("史诗城市中轴", text)
        self.assertTrue(any(term in text for term in ("云隙光", "圣辉逆光", "金雾神光")))

    def test_fallback_smart_text_uses_track_defaults_for_sparse_colossus_context(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="非人物主体，高细节",
            primary_prompt="电影级CG，巨物主题",
            style_track="工业树灵巨像",
        )
        self.assertIn("工业舱室", text)
        self.assertIn("朽木树皮纹理", text)
        self.assertTrue(any(term in text for term in ("巨物压迫近景", "低角度", "超广角全景")))

    def test_fallback_smart_text_does_not_append_track_defaults_when_user_already_specified_scene_and_outfit(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="成年女性，蒸汽浴室，丝质睡袍，柔和光晕，手持咖啡杯，全景全身",
            primary_prompt="东方赛博武侠朋克，完整人物入镜",
            style_track="东方赛博武侠朋克",
        )
        self.assertIn("蒸汽浴室", text)
        self.assertIn("丝质睡袍", text)
        self.assertIn("柔和光晕", text)
        self.assertIn("手持咖啡杯", text)
        self.assertNotIn("赛博街区", text)
        self.assertNotIn("机能外套", text)
        self.assertNotIn("全息投影光", text)
        self.assertNotIn("能量刀", text)

    def test_smart_text_uses_adult_mode_when_nsfw_profile_already_enabled(self) -> None:
        selected = OrderedDict({"主体": [], "构图视角": []})
        custom_tags: list[str] = []
        settings = {"模板风格": "真实感", "主体类型": "人物角色", "标签反推模式": "成人向成熟"}
        available = {"成年女性", "中景半身", "全景全身"}
        tag_group_index = {"成年女性": "主体", "中景半身": "构图视角", "全景全身": "构图视角"}

        def append_tag(next_selected, next_custom, tag):
            group = tag_group_index.get(tag)
            if group and group in next_selected and tag not in next_selected[group]:
                next_selected[group].append(tag)
            elif tag not in next_custom:
                next_custom.append(tag)

        selected, custom_tags, notes = smart_text.apply_smart_text_to_state(
            selected,
            custom_tags,
            settings,
            text="杂志封面，浴室柔光",
            available_tags=available,
            tag_group_index=tag_group_index,
            append_tag_to_state=append_tag,
        )
        self.assertEqual(settings["标签反推模式"], "成人向成熟")
        self.assertIn("成年女性", selected["主体"])
        self.assertIn("全景全身", selected["构图视角"])
        self.assertNotIn("中景半身", selected["构图视角"])
        self.assertTrue(any("成人向成熟" in note for note in notes))

    def test_smart_text_general_female_neon_portrait_does_not_enable_adult_mode(self) -> None:
        self.assertFalse(smart_text.looks_like_adult_request("女性在霓虹办公室拍摄商业人像", []))
        self.assertFalse(smart_text.looks_like_adult_request("成熟职业女性在办公室完成杂志封面拍摄", []))
        self.assertTrue(smart_text.looks_like_adult_request("成年女性在酒店拍摄内衣私房写真", []))

    def test_smart_text_specialized_style_uses_base_style_exclusions(self) -> None:
        filtered, removed = smart_text._filter_smart_text_style_pollution(
            ["水彩线稿", "CG感", "电影级CG"],
            "东方赛博",
        )
        self.assertEqual(filtered, ["CG感", "电影级CG"])
        self.assertEqual(removed, ["水彩线稿"])

    def test_smart_text_fallback_respects_english_language_modes(self) -> None:
        english = smart_text.fallback_smart_text(
            user_text="成年女性，东方赛博，霓虹街区",
            primary_prompt="全景全身，高细节",
            style_track="东方赛博",
            language="纯英文",
        )
        bilingual = smart_text.fallback_smart_text(
            user_text="成年女性，东方赛博，霓虹街区",
            primary_prompt="全景全身，高细节",
            style_track="东方赛博",
            language="英文提示词+中文说明",
        )
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in english))
        self.assertIn("中文说明：", bilingual)
        self.assertTrue(any("\u4e00" <= char <= "\u9fff" for char in bilingual))

    def test_smart_text_filters_cross_style_pollution_from_inferred_tags(self) -> None:
        selected = OrderedDict({"主体": [], "画面风格": [], "场景背景": [], "构图视角": []})
        custom_tags: list[str] = []
        settings = {"模板风格": "真实感", "主体类型": "人物角色", "标签反推模式": "自动平衡"}
        available = {"真实感", "照片级", "港风", "古风电影剧照", "CG感", "虚幻引擎", "成年女性", "全景全身"}
        tag_group_index = {
            "真实感": "画面风格",
            "照片级": "画面风格",
            "港风": "画面风格",
            "古风电影剧照": "画面风格",
            "CG感": "画面风格",
            "虚幻引擎": "画面风格",
            "成年女性": "主体",
            "全景全身": "构图视角",
        }

        def append_tag(next_selected, next_custom, tag):
            group = tag_group_index.get(tag)
            if group and group in next_selected and tag not in next_selected[group]:
                next_selected[group].append(tag)
            elif tag not in next_custom:
                next_custom.append(tag)

        selected, custom_tags, notes = smart_text.apply_smart_text_to_state(
            selected,
            custom_tags,
            settings,
            text="港风写实少女，带一点古风电影和机甲科幻感",
            available_tags=available,
            tag_group_index=tag_group_index,
            append_tag_to_state=append_tag,
        )
        all_tags = collect_all_tags(selected, custom_tags)
        self.assertIn("真实感", all_tags)
        self.assertIn("照片级", all_tags)
        self.assertIn("港风", all_tags)
        self.assertNotIn("古风电影剧照", all_tags)
        self.assertNotIn("CG感", all_tags)
        self.assertNotIn("虚幻引擎", all_tags)
        self.assertTrue(any("智能文本风格隔离" in note for note in notes))

    def test_smart_text_removes_existing_conflicting_style_tags_from_state(self) -> None:
        selected = OrderedDict({"主体": [], "画面风格": ["古风电影剧照", "CG感"], "场景背景": [], "构图视角": []})
        custom_tags: list[str] = []
        settings = {"模板风格": "真实感", "主体类型": "人物角色", "标签反推模式": "自动平衡"}
        available = {"真实感", "照片级", "港风", "古风电影剧照", "CG感", "成年女性", "全景全身"}
        tag_group_index = {
            "真实感": "画面风格",
            "照片级": "画面风格",
            "港风": "画面风格",
            "古风电影剧照": "画面风格",
            "CG感": "画面风格",
            "成年女性": "主体",
            "全景全身": "构图视角",
        }

        def append_tag(next_selected, next_custom, tag):
            group = tag_group_index.get(tag)
            if group and group in next_selected and tag not in next_selected[group]:
                next_selected[group].append(tag)
            elif tag not in next_custom:
                next_custom.append(tag)

        selected, custom_tags, notes = smart_text.apply_smart_text_to_state(
            selected,
            custom_tags,
            settings,
            text="港风杂志封面感的真实写实人像",
            available_tags=available,
            tag_group_index=tag_group_index,
            append_tag_to_state=append_tag,
        )
        all_tags = collect_all_tags(selected, custom_tags)
        self.assertIn("真实感", all_tags)
        self.assertIn("港风", all_tags)
        self.assertNotIn("古风电影剧照", all_tags)
        self.assertNotIn("CG感", all_tags)
        self.assertTrue(any("智能文本风格收敛" in note for note in notes))

    def test_smart_text_style_priority_prefers_node_style_when_configured(self) -> None:
        selected = OrderedDict({"主体": [], "画面风格": ["古风电影剧照"], "场景背景": [], "构图视角": []})
        custom_tags: list[str] = []
        settings = {"模板风格": "古风", "主体类型": "人物角色", "标签反推模式": "自动平衡", "智能文本风格优先": "节点优先"}
        available = {"真实感", "照片级", "港风", "古风电影剧照", "古风", "CG感", "成年女性", "全景全身"}
        tag_group_index = {tag: "画面风格" for tag in ["真实感", "照片级", "港风", "古风电影剧照", "古风", "CG感"]}
        tag_group_index.update({"成年女性": "主体", "全景全身": "构图视角"})

        def append_tag(next_selected, next_custom, tag):
            group = tag_group_index.get(tag)
            if group and group in next_selected and tag not in next_selected[group]:
                next_selected[group].append(tag)
            elif tag not in next_custom:
                next_custom.append(tag)

        selected, custom_tags, _notes = smart_text.apply_smart_text_to_state(
            selected,
            custom_tags,
            settings,
            text="港风杂志封面感的真实写实人像",
            available_tags=available,
            tag_group_index=tag_group_index,
            append_tag_to_state=append_tag,
        )
        all_tags = set(collect_all_tags(selected, custom_tags))
        self.assertIn("古风电影剧照", all_tags)
        self.assertNotIn("真实感", all_tags)
        self.assertNotIn("港风", all_tags)

    def test_smart_text_style_priority_prefers_text_style_when_configured(self) -> None:
        selected = OrderedDict({"主体": [], "画面风格": ["古风电影剧照"], "场景背景": [], "构图视角": []})
        custom_tags: list[str] = []
        settings = {"模板风格": "古风", "主体类型": "人物角色", "标签反推模式": "自动平衡", "智能文本风格优先": "文本优先"}
        available = {"真实感", "照片级", "港风", "古风电影剧照", "古风", "成年女性", "全景全身"}
        tag_group_index = {tag: "画面风格" for tag in ["真实感", "照片级", "港风", "古风电影剧照", "古风"]}
        tag_group_index.update({"成年女性": "主体", "全景全身": "构图视角"})

        def append_tag(next_selected, next_custom, tag):
            group = tag_group_index.get(tag)
            if group and group in next_selected and tag not in next_selected[group]:
                next_selected[group].append(tag)
            elif tag not in next_custom:
                next_custom.append(tag)

        selected, custom_tags, _notes = smart_text.apply_smart_text_to_state(
            selected,
            custom_tags,
            settings,
            text="港风杂志封面感的真实写实人像",
            available_tags=available,
            tag_group_index=tag_group_index,
            append_tag_to_state=append_tag,
        )
        all_tags = set(collect_all_tags(selected, custom_tags))
        self.assertIn("真实感", all_tags)
        self.assertIn("港风", all_tags)
        self.assertNotIn("古风电影剧照", all_tags)

    def test_smart_text_adult_mode_respects_full_body_intent(self) -> None:
        selected = OrderedDict({"主体": [], "构图视角": ["中景半身"]})
        custom_tags: list[str] = []
        settings = {"模板风格": "真实感", "主体类型": "人物角色", "标签反推模式": "成人向成熟"}
        available = {"成年女性", "中景半身", "全景全身", "全身"}
        tag_group_index = {"成年女性": "主体", "中景半身": "构图视角", "全景全身": "构图视角", "全身": "构图视角"}

        def append_tag(next_selected, next_custom, tag):
            group = tag_group_index.get(tag)
            if group and group in next_selected and tag not in next_selected[group]:
                next_selected[group].append(tag)
            elif tag not in next_custom:
                next_custom.append(tag)

        selected, custom_tags, notes = smart_text.apply_smart_text_to_state(
            selected,
            custom_tags,
            settings,
            text="全身浴室柔光",
            available_tags=available,
            tag_group_index=tag_group_index,
            append_tag_to_state=append_tag,
        )
        self.assertIn("成年女性", selected["主体"])
        self.assertIn("全景全身", selected["构图视角"])
        self.assertNotIn("中景半身", selected["构图视角"])
        self.assertTrue(any("全身构图意图" in note for note in notes))

    def test_smart_text_adult_mode_preserves_existing_adult_male_subject(self) -> None:
        selected = OrderedDict({"主体": ["成年男性"], "构图视角": []})
        custom_tags: list[str] = []
        settings = {"模板风格": "真实感", "主体类型": "人物角色", "标签反推模式": "自动平衡"}
        available = {"成年女性", "成年男性", "全景全身"}
        tag_group_index = {"成年女性": "主体", "成年男性": "主体", "全景全身": "构图视角"}

        def append_tag(next_selected, next_custom, tag):
            group = tag_group_index.get(tag)
            if group and group in next_selected and tag not in next_selected[group]:
                next_selected[group].append(tag)
            elif tag not in next_custom:
                next_custom.append(tag)

        selected, custom_tags, _notes = smart_text.apply_smart_text_to_state(
            selected,
            custom_tags,
            settings,
            text="adult man nsfw",
            available_tags=available,
            tag_group_index=tag_group_index,
            append_tag_to_state=append_tag,
        )
        self.assertIn("成年男性", selected["主体"])
        self.assertNotIn("成年女性", selected["主体"])
        self.assertEqual(settings["标签反推模式"], "成人向成熟")

    def test_smart_text_preserves_close_shot_without_adding_full_body(self) -> None:
        selected = OrderedDict({"主体": ["成年女性"], "构图视角": ["近景"]})
        custom_tags: list[str] = []
        settings = {"模板风格": "真实感", "主体类型": "人物角色", "标签反推模式": "自动平衡"}
        available = {"成年女性", "近景", "全景全身"}
        tag_group_index = {"成年女性": "主体", "近景": "构图视角", "全景全身": "构图视角"}

        def append_tag(next_selected, next_custom, tag):
            group = tag_group_index.get(tag)
            if group and group in next_selected and tag not in next_selected[group]:
                next_selected[group].append(tag)
            elif tag not in next_custom:
                next_custom.append(tag)

        selected, custom_tags, _notes = smart_text.apply_smart_text_to_state(
            selected,
            custom_tags,
            settings,
            text="保留红色丝带",
            available_tags=available,
            tag_group_index=tag_group_index,
            append_tag_to_state=append_tag,
        )
        self.assertIn("近景", selected["构图视角"])
        self.assertNotIn("全景全身", selected["构图视角"])

    def test_smart_text_seed_mentions_adult_mode_when_enabled(self) -> None:
        seed = smart_text.build_smart_text_seed(
            user_text="浴室柔光",
            primary_prompt="杂志编辑摄影，成年女性，私房写真",
            selected_tags_text="标签反推模式：成人向成熟\n成人向表达：私房写真",
            settings={
                "提示词语言": "纯中文",
                "标签反推模式": "成人向成熟",
                "NSFW工作台标签摘要": "已启用；映射标签：蒸汽浴室、湿身淋浴、柔光",
                "Skill动态变化策略": "智能文本；标签作为素材锚点而非固定模板；优先变化未明确锁定维度：动作姿态、持物道具。",
                "最近提示词指纹": ["visual:scene:蒸汽浴室|light:柔光"],
            },
        )
        self.assertIn("成人成熟模式：已启用", seed)
        self.assertIn("NSFW 成熟写真工作台标签", seed)
        self.assertIn("NSFW工作台摘要", seed)
        self.assertIn("Skill动态变化策略", seed)
        self.assertIn("标签作为素材锚点而非固定模板", seed)
        self.assertIn("最近输出避重", seed)
        self.assertIn("蒸汽浴室", seed)
        self.assertIn("湿身淋浴", seed)
        self.assertIn("目标 650-900 字", seed)

    def test_smart_text_seed_requests_prompt_first_and_not_tag_list(self) -> None:
        seed = smart_text.build_smart_text_seed(
            user_text="浴室柔光，湿发，成年人像",
            primary_prompt="杂志编辑摄影，成年女性，全景全身，蒸汽浴室，柔光，电影感",
            selected_tags_text="主体：成年女性\n场景背景：蒸汽浴室\n成人向表达：私房写真",
            settings={"提示词语言": "英文提示词+中文说明", "标签反推模式": "成人向成熟"},
        )
        self.assertIn("优先吸收 NSFW 成熟写真工作台标签", seed)
        self.assertIn("基础提示词", seed)
        self.assertIn("不要原样抄写", seed)
        self.assertIn("不要锁死风格和景别", seed)
        self.assertIn("中文说明", seed)

    def test_smart_text_seed_includes_runtime_track_context(self) -> None:
        seed = smart_text.build_smart_text_seed(
            user_text="雨夜站台的都市女性",
            primary_prompt="都市电影人文，成年女性，长款大衣，雨夜站台，青蓝冷雾",
            selected_tags_text="主体：成年女性\n场景背景：雨夜站台\n画面风格：都市电影人文",
            settings={
                "提示词语言": "纯中文",
                "标签反推模式": "自动平衡",
                "运行时随机模式解析结果": "全随机",
                "运行时随机强度": "强 / 极限拉开",
                "风格隔离策略": "严格风格隔离",
            },
            style_track="都市电影人文",
        )
        self.assertIn("当前轨道：都市电影人文", seed)
        self.assertIn("运行时随机：全随机 / 强 / 极限拉开", seed)
        self.assertIn("风格隔离：严格风格隔离", seed)

    def test_smart_text_non_person_seed_and_fallback_avoid_portrait_defaults(self) -> None:
        seed = smart_text.build_smart_text_seed(
            user_text="侦查机甲，机库冷光",
            primary_prompt="电影级CG，侦查机甲，机库，全景，高细节",
            selected_tags_text="主体类型：非人物主体\n主体：侦查机甲",
            settings={"提示词语言": "纯中文", "标签反推模式": "自动平衡", "主体类型": "非人物主体"},
        )
        fallback = smart_text.fallback_smart_text(
            user_text="侦查机甲，机库冷光",
            primary_prompt="电影级CG，侦查机甲，机库，全景，高细节",
            subject_type="非人物主体",
        )

        self.assertIn("当前是非人物主体", seed)
        self.assertIn("物体、机械、建筑、场景或概念设计", seed)
        self.assertIn("主体结构", fallback)
        self.assertNotIn("人物轮廓", fallback)
        self.assertNotIn("脸部方向", fallback)
        self.assertNotIn("服装、发丝、皮肤", fallback)

    def test_smart_text_seed_respects_language_modes(self) -> None:
        chinese_seed = smart_text.build_smart_text_seed(
            user_text="一个女孩",
            primary_prompt="成年女性，全景全身",
            selected_tags_text="",
            settings={"提示词语言": "纯中文"},
        )
        english_seed = smart_text.build_smart_text_seed(
            user_text="a woman",
            primary_prompt="adult woman, full body",
            selected_tags_text="",
            settings={"提示词语言": "纯英文"},
        )
        bilingual_seed = smart_text.build_smart_text_seed(
            user_text="a woman",
            primary_prompt="adult woman, full body",
            selected_tags_text="",
            settings={"提示词语言": "英文提示词+中文说明"},
        )
        self.assertIn("目标 650-900 字", chinese_seed)
        self.assertIn("320-520 words", english_seed)
        self.assertIn("中文说明", bilingual_seed)

    def test_smart_text_settings_use_compact_fast_sampling(self) -> None:
        settings = smart_text.build_smart_text_settings(
            {"最大生成token": 1600, "温度": 0.9, "top_p": 0.96, "top_k": 99, "重复惩罚": 1.0}
        )
        self.assertLessEqual(settings["最大生成token"], 2200)
        self.assertGreaterEqual(settings["最大生成token"], 1280)
        self.assertLessEqual(settings["温度"], 0.62)
        self.assertLessEqual(settings["top_p"], 0.9)
        self.assertLessEqual(settings["top_k"], 40)
        self.assertGreaterEqual(settings["重复惩罚"], 1.1)
        self.assertGreaterEqual(settings["频率惩罚"], 0.12)
        self.assertGreaterEqual(settings["存在惩罚"], 0.06)
        self.assertIn("650-900", settings["系统提示词覆盖"])
        self.assertIn("320-520", settings["系统提示词覆盖"])
        self.assertIn("不要标签清单", settings["系统提示词覆盖"])
        self.assertIn("不要用近义词反复堆叠", settings["系统提示词覆盖"])
        self.assertIn("主体 → 环境 → 光线 → 风格/媒介 → 镜头", settings["系统提示词覆盖"])
        self.assertIn("中文模式必须输出自然中文正向提示词", settings["系统提示词覆盖"])
        self.assertIn("--profile", settings["系统提示词覆盖"])
        self.assertIn("不要锁死素材库风格", settings["系统提示词覆盖"])

    def test_smart_text_fallback_writes_natural_prompt_not_tag_chain(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="自然写实图像，傲娇，书店女孩，动漫，国风美学，水彩线稿，环境遮挡，透明高跟凉鞋，地下通道，能量刀，欲感，月夜森林，霓虹夜色，近景，面部聚焦，镜头近距离，持物待发，站姿挺拔，双手负后，高细节，低保真，光束尘埃，标准，True，脸部表情与妆发细节优先，面部作为第一视觉中心，面部与主体关系清晰",
            primary_prompt="自然写实图像，书店女孩，近景，面部聚焦，高细节",
        )
        self.assertIn("画面以", text)
        self.assertIn("场景", text)
        self.assertIn("镜头采用", text)
        self.assertIn("整体保持", text)
        self.assertNotIn("True", text)
        self.assertNotIn("低保真", text)
        self.assertGreater(len(text), 180)
        self.assertLess(text.count("，"), 32)

    def test_smart_text_fallback_defaults_to_full_body_when_no_shot_requested(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="杂志封面感，成年女性，书店霓虹柔光",
            primary_prompt="杂志编辑摄影，成年女性，高细节",
        )
        self.assertIn("全景全身", text)
        self.assertIn("人物完整入镜", text)
        self.assertNotIn("镜头采用近景", text)
        self.assertNotIn("镜头采用近景、面部聚焦", text)

    def test_smart_text_fallback_keeps_adult_woman_subject_wording(self) -> None:
        text = smart_text.fallback_smart_text(
            user_text="湖边柔光，一个成年女性，参考素材但不要锁死古风",
            primary_prompt="古风电影，雨雾竹林，丝绸边缘高光，全景全身",
        )
        self.assertIn("成年女性", text)
        self.assertNotIn("画面以女孩", text)

    def test_smart_text_sanitizer_removes_model_chatter_and_uncertain_adult_subject(self) -> None:
        text = smart_text.sanitize_smart_text_prompt(
            text="一个女孩在自慰，以下是为您优化的最终正向提示词（已严格使用中文，适配主流AI绘画平台）：，杂志编辑摄影，成年女性踮起脚尖回眸回望，姿态优雅",
            user_text="一个女孩在自慰",
            primary_prompt="杂志编辑摄影，成年女性，私房写真，中景半身，柔光",
        )
        self.assertNotIn("以下是", text)
        self.assertNotIn("为您优化", text)
        self.assertNotIn("女孩", text)
        self.assertIn("自慰", text)
        self.assertIn("成年女性", text)
        self.assertIn("杂志编辑摄影", text)
        self.assertIn("姿态优雅", text)

    def test_smart_text_sanitizer_rewrites_youth_school_terms_in_adult_mode(self) -> None:
        text = smart_text.sanitize_smart_text_prompt(
            text="校园少女感，校服，书店女孩，午后柔光，青春氛围",
            user_text="校园少女感",
            primary_prompt="成年女性，私房写真",
            adult_mode=True,
        )
        self.assertIn("成年女性", text)
        self.assertIn("青春感成年女性", text)
        self.assertIn("学院风穿搭", text)
        self.assertIn("大学校园", text)
        self.assertIn("书店里的年轻成年女性", text)
        self.assertNotIn("校园少女", text)
        self.assertNotIn("校服", text)

    def test_smart_text_sanitizer_rewrites_subject_only_output_to_full_prompt(self) -> None:
        text = smart_text.sanitize_smart_text_prompt(
            text="成年女性",
            user_text="一个女孩",
            primary_prompt="一位成年女性，杂志编辑风格的摄影作品，中景半身构图，身体微微前倾俯身，青橙色调（Teal and Orange），背景为湖畔夕照，皮肤着色干净，冷白皮，True，时尚成片感更强，人物视觉重心更偏封面肖像",
            adult_mode=True,
        )
        self.assertNotEqual(text, "成年女性")
        self.assertIn("成年女性", text)
        self.assertIn("杂志编辑风格", text)
        self.assertIn("湖畔夕照", text)

    def test_smart_text_sanitizer_rewrites_style_only_output_to_full_prompt(self) -> None:
        text = smart_text.sanitize_smart_text_prompt(
            text="CG感",
            user_text="粉色汉服角色设定图，长发，白底展示",
            primary_prompt="CG感，角色设定图，成年女性，长发，粉色汉服，头像特写，全身，正面视图，侧面视图，背面视图，白底棚拍，高细节",
        )
        self.assertNotEqual(text, "CG感")
        self.assertIn("电影级CG", text)
        self.assertIn("画面以", text)
        self.assertIn("镜头采用", text)
        self.assertIn("高细节", text)
        self.assertIn("镜头采用", text)
        self.assertNotIn("True", text)
        self.assertGreater(len(text), 40)

    def test_model_refiner_stabilizes_repetitive_prompt_output(self) -> None:
        text = model_refiner.stabilize_prompt_output(
            "Create a coherent image centered on the main subject, "
            "wide full-body shot, entire subject fully in frame, full body, full body, "
            "high detail, high detail, best quality, masterpiece, sharp focus, high resolution, "
            "clear focus hierarchy, natural anatomy, stable hands, correct fingers, stable hands, no text, no watermark, no logo"
        )
        self.assertNotIn("Create a coherent image", text)
        self.assertIn("wide full-body shot", text)
        self.assertLessEqual(text.count("full body"), 2)
        self.assertEqual(text.count("high detail"), 1)
        self.assertEqual(text.count("stable hands"), 1)

    def test_maybe_model_refine_cleans_api_repetition_without_losing_anchors(self) -> None:
        class DummyLLM:
            def create_chat_completion(self, *args, **kwargs):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "最终提示词：Create a coherent image centered on the main subject, 全景全身，全景全身，人物完整入镜，高细节，高细节，清晰对焦，清晰对焦，成年女性，雨夜站台"
                            }
                        }
                    ]
                }

        text = model_refiner.maybe_model_refine(
            DummyLLM(),
            "成年女性，全景全身，人物完整入镜，雨夜站台，高细节",
            {"提示词语言": "纯中文", "主体类型": "人物角色", "主体类型解析结果": "人物角色"},
            chat_completion=lambda llm, messages, params: llm.create_chat_completion(messages=messages, **params),
            clean_think_text=lambda value: value,
        )
        self.assertNotIn("Create a coherent image", text)
        self.assertIn("成年女性", text)
        self.assertIn("雨夜站台", text)
        self.assertEqual(text.count("全景全身"), 1)
        self.assertEqual(text.count("高细节"), 1)

    def test_stage_generator_stabilizer_falls_back_when_api_matches_recent_prompt(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        recent_prompt = "商业广告大片，银白长发，修身礼服，摄影棚，回眸，风暴天光，高细节"
        original_prompt = "武侠电影剧照，黑发剑客，竹林雨夜，持伞侧身，冷青月光，高细节"
        settings = {"最近提示词指纹": [module._prompt_core_signature(recent_prompt)]}
        result = module._stabilize_prompt_list_outputs(
            [recent_prompt],
            [original_prompt],
            settings,
        )
        self.assertEqual(result, [original_prompt])
        self.assertTrue(any("最近提示词避重" in note for note in settings.get("推理纠偏说明", [])))

    def test_stage_generator_stabilizer_falls_back_when_visual_profile_matches_recent_prompt(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        recent_prompt = "商业广告大片，银白长发，修身礼服，摄影棚，回眸，风暴天光，书本，高细节"
        near_duplicate = (
            "高级时装画面，银白长发人物穿修身礼服站在摄影棚，手边放着书本，"
            "以回眸姿态面对镜头，风暴天光压出戏剧化边缘，高细节"
        )
        original_prompt = "武侠电影剧照，黑发剑客，竹林雨夜，持伞侧身，冷青月光，高细节"
        settings = {"最近提示词指纹": module._update_prompt_history("visual-near-duplicate", [recent_prompt])}
        result = module._stabilize_prompt_list_outputs(
            [near_duplicate],
            [original_prompt],
            settings,
        )
        self.assertEqual(result, [original_prompt])
        self.assertTrue(any("最近提示词避重" in note for note in settings.get("推理纠偏说明", [])))

    def test_stage_generator_stabilizer_flags_repeated_visual_dimensions(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        recent_prompt = "时装广告大片，银白长发，修身礼服，摄影棚，回眸，风暴天光，书本，高细节"
        near_duplicate = (
            "商业封面成片，银白长发主体穿修身礼服站在摄影棚内，手持书本轻微回眸，"
            "风暴天光形成轮廓，高细节"
        )
        original_prompt = "港风夜雨人像，黑发短发，皮革夹克，霓虹巷口，撑伞前行，冷青侧光，高细节"
        settings = {"最近提示词指纹": module._update_prompt_history("visual-dimension-repeat", [recent_prompt])}
        self.assertTrue(module._prompt_too_close_to_recent(near_duplicate, set(settings["最近提示词指纹"])))
        result = module._stabilize_prompt_list_outputs(
            [near_duplicate],
            [original_prompt],
            settings,
        )
        self.assertEqual(result, [original_prompt])
        self.assertTrue(any("最近提示词避重" in note for note in settings.get("推理纠偏说明", [])))

    def test_stage_generator_stabilizer_adds_variation_cue_when_fallback_is_still_close(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        recent_prompt = "商业广告大片，银白长发，修身礼服，摄影棚，回眸，风暴天光，书本，高细节"
        near_duplicate = (
            "高级广告画面，银白长发人物穿修身礼服站在摄影棚，手边放着书本，"
            "以回眸姿态面对镜头，风暴天光压出轮廓，高细节"
        )
        close_original = (
            "商业封面摄影，银白长发模特穿修身礼服立于摄影棚，手持书本回眸，"
            "风暴天光形成边缘光，高细节"
        )
        settings = {
            "最近提示词指纹": module._update_prompt_history("visual-cue-repeat", [recent_prompt]),
            "提示词语言": "纯中文",
            "seed": 0,
        }
        result = module._stabilize_prompt_list_outputs(
            [near_duplicate],
            [close_original],
            settings,
        )
        self.assertEqual(len(result), 1)
        self.assertIn("成片方案", result[0])
        self.assertTrue(any("最近提示词差异补强" in note for note in settings.get("推理纠偏说明", [])))

    def test_tag_block_composer_preserves_user_block_order(self) -> None:
        payload = tag_block_composer.parse_tag_block_payload(json.dumps({
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "场景背景", "label": "场景", "tags": ["湖畔", "晨雾"]},
                {"type": "text", "label": "补充", "text": "人物站在画面右侧"},
                {"type": "tag_group", "group": "主体", "label": "主体", "tags": ["成年女性", "银白长发"]},
            ],
        }, ensure_ascii=False))
        summary = tag_block_composer.summarize_tag_block_payload(payload)
        self.assertLess(summary.index("场景"), summary.index("主体"))
        prompt = tag_block_composer.build_tag_block_prompt_list(
            payload,
            OrderedDict({"主体": ["成年女性"], "场景背景": ["湖畔"]}),
            [],
            {"提示词语言": "纯中文", "详细度": "详细", "模板风格": "真实感"},
            style_track="写实人像",
            subject_type="人物角色",
        )[0]
        self.assertLess(prompt.index("湖畔"), prompt.index("成年女性"))
        self.assertIn("人物站在画面右侧", prompt)
        self.assertIn("正向画面说明", prompt)
        self.assertNotIn("根据用户拖拽后的标签块顺序", prompt)
        self.assertNotIn("块顺序摘要", prompt)

    def test_tag_block_composer_outputs_natural_prompt_not_model_instruction(self) -> None:
        payload = tag_block_composer.parse_tag_block_payload(json.dumps({
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "画面风格", "label": "画面风格", "tags": ["游戏风", "电影感单幅画面"]},
                {"type": "tag_group", "group": "光影氛围", "label": "光影氛围", "tags": ["诡异", "冷静"]},
                {"type": "tag_group", "group": "构图视角", "label": "构图视角", "tags": ["全景全身", "人物完整入镜"]},
                {"type": "text", "label": "文字块", "text": "一个女人"},
                {"type": "tag_group", "group": "动作姿态", "label": "动作姿态", "tags": ["手拿包", "手持咖啡杯"]},
                {"type": "tag_group", "group": "技术画质", "label": "技术画质", "tags": ["电影感"]},
                {"type": "tag_group", "group": "自定义补充", "label": "自定义", "tags": ["中"]},
            ],
        }, ensure_ascii=False))
        prompt = tag_block_composer.build_tag_block_prompt_list(
            payload,
            OrderedDict(),
            [],
            {"提示词语言": "纯中文", "详细度": "标准", "模板风格": "商业摄影"},
            style_track="商业摄影",
            subject_type="人物角色",
        )[0]
        self.assertIn("游戏风", prompt)
        self.assertIn("一个女人", prompt)
        self.assertIn("全景全身", prompt)
        self.assertIn("手拿包", prompt)
        self.assertIn("手持咖啡杯", prompt)
        self.assertNotIn("根据用户拖拽后的标签块顺序", prompt)
        self.assertNotIn("画面阅读顺序依次为", prompt)
        self.assertNotIn("块顺序摘要", prompt)
        self.assertNotIn("自定义", prompt)
        self.assertNotIn("使用 中", prompt)

    def test_tag_block_composer_uses_normalized_state_as_content_boundary(self) -> None:
        payload = tag_block_composer.parse_tag_block_payload(json.dumps({
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "画面风格", "label": "风格", "tags": ["商业摄影"]},
                {"type": "tag_group", "group": "场景背景", "label": "场景", "tags": ["办公室"]},
                {"type": "text", "label": "旧场景补充", "text": "人物站在办公室窗边"},
            ],
        }, ensure_ascii=False))
        prompt = tag_block_composer.build_tag_block_prompt_list(
            payload,
            OrderedDict({
                "主体": ["成年女性"],
                "画面风格": ["古风"],
                "场景背景": ["宫殿"],
            }),
            [],
            {"提示词语言": "纯中文", "详细度": "标准", "模板风格": "古风"},
            style_track="古风",
            subject_type="人物角色",
        )[0]
        self.assertIn("古风", prompt)
        self.assertIn("宫殿", prompt)
        self.assertIn("成年女性", prompt)
        self.assertNotIn("商业摄影", prompt)
        self.assertNotIn("办公室", prompt)

    def test_tag_block_composer_honors_generation_count_and_locked_state(self) -> None:
        payload = tag_block_composer.parse_tag_block_payload(json.dumps({
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "主体", "label": "主体", "tags": ["成年女性"]},
                {"type": "tag_group", "group": "场景背景", "label": "场景", "tags": ["宫殿"], "locked": True},
                {"type": "tag_group", "group": "光影氛围", "label": "光影", "tags": ["柔光"]},
            ],
        }, ensure_ascii=False))
        prompts = tag_block_composer.build_tag_block_prompt_list(
            payload,
            OrderedDict({
                "主体": ["成年女性"],
                "场景背景": ["宫殿", "竹林"],
                "光影氛围": ["柔光"],
            }),
            [],
            {"提示词语言": "纯中文", "详细度": "简洁", "模板风格": "古风"},
            style_track="古风",
            subject_type="人物角色",
            generation_count=6,
        )
        self.assertEqual(len(prompts), 6)
        self.assertEqual(len(set(prompts)), 6)
        self.assertTrue(all("成年女性" in prompt for prompt in prompts))
        self.assertTrue(all("宫殿" in prompt and "竹林" in prompt for prompt in prompts))
        self.assertTrue(all("柔光" in prompt for prompt in prompts))

    def test_tag_block_composer_keeps_extra_requirement_once_and_accepts_invalid_version(self) -> None:
        payload = tag_block_composer.parse_tag_block_payload(
            {
                "version": "invalid",
                "enabled": True,
                "blocks": [
                    {"type": "tag_group", "group": "主体", "tags": ["成年女性"]},
                ],
            }
        )
        self.assertEqual(payload["version"], 1)
        prompt = tag_block_composer.build_tag_block_prompt_list(
            payload,
            OrderedDict({"主体": ["成年女性"]}),
            [],
            {
                "提示词语言": "纯中文",
                "详细度": "标准",
                "模板风格": "真实感",
                "额外要求": "保留红色丝带\n角色设定图内部策略：不要泄露",
            },
        )[0]
        self.assertEqual(prompt.count("保留红色丝带"), 1)
        self.assertNotIn("角色设定图内部策略", prompt)

    def test_tag_block_composer_english_preserves_order_text_adult_and_detail(self) -> None:
        payload = tag_block_composer.parse_tag_block_payload(json.dumps({
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "场景背景", "label": "scene", "tags": ["moonlit hall"]},
                {"type": "text", "label": "detail", "text": "keep a red ribbon visible near the left hand"},
                {"type": "tag_group", "group": "成人向表达", "label": "mature mood", "tags": ["mature elegance"]},
                {"type": "tag_group", "group": "主体", "label": "subject", "tags": ["adult woman"]},
                {"type": "tag_group", "group": "技术画质", "label": "quality", "tags": ["high detail"]},
            ],
        }, ensure_ascii=False))
        prompt = tag_block_composer.build_tag_block_prompt_list(
            payload,
            OrderedDict(),
            [],
            {"提示词语言": "纯英文", "详细度": "详细", "模板风格": "editorial photography"},
            style_track="editorial photography",
            subject_type="人物角色",
        )[0]
        self.assertLess(prompt.index("moonlit hall"), prompt.index("red ribbon"))
        self.assertLess(prompt.index("red ribbon"), prompt.index("mature elegance"))
        self.assertLess(prompt.index("mature elegance"), prompt.index("adult woman"))
        self.assertIn("Develop visible material response", prompt)
        self.assertIn("The mature styling direction", prompt)
        self.assertIn("The user-provided detail", prompt)

    def test_tag_block_composer_pure_english_localizes_real_ui_chinese_tags(self) -> None:
        payload = tag_block_composer.parse_tag_block_payload(json.dumps({
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "主体", "label": "主体", "tags": ["成年女性"]},
                {"type": "tag_group", "group": "场景背景", "label": "场景", "tags": ["宫殿"]},
                {"type": "tag_group", "group": "构图视角", "label": "构图", "tags": ["全景全身", "人物完整入镜"]},
                {"type": "tag_group", "group": "自定义补充", "label": "自定义", "tags": ["自定义未知纹理词"]},
                {"type": "text", "label": "补充", "text": "保留红色丝带"},
            ],
        }, ensure_ascii=False))
        prompt = tag_block_composer.build_tag_block_prompt_list(
            payload,
            OrderedDict({
                "主体": ["成年女性"],
                "场景背景": ["宫殿"],
                "构图视角": ["全景全身", "人物完整入镜"],
            }),
            ["自定义未知纹理词"],
            {"提示词语言": "纯英文", "详细度": "标准", "模板风格": "真实感"},
            style_track="真实感",
            subject_type="人物角色",
        )[0]
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in prompt), prompt)
        self.assertIn("adult woman", prompt)
        self.assertIn("palace", prompt)
        self.assertIn("wide full-body shot", prompt)
        self.assertIn("user-provided visual detail", prompt)

    def test_stage_generator_tag_block_pure_english_has_no_chinese_content(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        payload = {
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "主体", "tags": ["成年女性"]},
                {"type": "tag_group", "group": "场景背景", "tags": ["宫殿"]},
            ],
        }
        result = module._run_stage(
            None,
            **{
                "unique_id": "tag-block-pure-english",
                "主体标签1": "成年女性",
                "场景背景标签1": "宫殿",
                "标签块编排启用": True,
                "标签块编排JSON": json.dumps(payload, ensure_ascii=False),
                "模板风格": "真实感",
                "生成数量": 1,
                "提示词语言": "纯英文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 1,
            },
        )
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in result[1]), result[1])
        self.assertIn("adult woman", result[1])
        self.assertIn("palace", result[1])

    def test_stage_generator_tag_block_composer_routes_prompt_and_json(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()

        class DummyModel:
            pass

        original_refine_batch = module._maybe_model_refine_batch_impl
        original_update_history = module._update_history
        module._maybe_model_refine_batch_impl = lambda model, prompt_list, settings, **kwargs: list(prompt_list)
        module._update_history = lambda *args, **kwargs: []
        payload = {
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "场景背景", "label": "场景背景", "tags": ["湖畔夕照"]},
                {"type": "tag_group", "group": "主体", "label": "主体", "tags": ["成年女性"]},
            ],
        }
        try:
            result = module._run_stage(
                DummyModel(),
                **{
                    "主体标签1": "成年女性",
                    "场景背景标签1": "湖畔夕照",
                    "标签块编排启用": True,
                    "标签块编排JSON": json.dumps(payload, ensure_ascii=False),
                    "生成数量": 1,
                    "提示词语言": "纯中文",
                    "详细度": "标准",
                    "输出模式": "完整结果",
                    "运行时随机标签": False,
                    "模型来源": "仅Skill",
                },
            )
        finally:
            module._maybe_model_refine_batch_impl = original_refine_batch
            module._update_history = original_update_history
        self.assertIn("湖畔夕照", result[1])
        self.assertIn("成年女性", result[1])
        self.assertLess(result[1].index("湖畔夕照"), result[1].index("成年女性"))
        self.assertNotIn("根据用户拖拽后的标签块顺序", result[1])
        json_payload = json.loads(result[3])
        self.assertTrue(json_payload["tag_block_composer_enabled"])
        self.assertIn("湖畔夕照", json_payload["tag_block_composer_summary"])

    def test_stage_generator_tag_block_composer_honors_count_and_normalized_state(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        payload = {
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "场景背景", "label": "场景", "tags": ["办公室"]},
                {"type": "tag_group", "group": "画面风格", "label": "风格", "tags": ["商业摄影"]},
            ],
        }
        result = module._run_stage(
            None,
            **{
                "unique_id": "tag-block-normalized-count",
                "主体标签1": "成年女性",
                "场景背景标签1": "宫殿",
                "模板风格": "古风",
                "标签块编排启用": True,
                "标签块编排JSON": json.dumps(payload, ensure_ascii=False),
                "生成数量": 4,
                "提示词语言": "纯中文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 123,
            },
        )
        result_payload = json.loads(result[3])
        prompts = result_payload["prompt_list"]
        self.assertEqual(len(prompts), 4)
        self.assertEqual(len(set(prompts)), 4)
        self.assertTrue(all("宫殿" in prompt for prompt in prompts))
        self.assertTrue(all("成年女性" in prompt for prompt in prompts))
        self.assertTrue(all("办公室" not in prompt and "商业摄影" not in prompt for prompt in prompts))

    def test_stage_generator_exposes_nsfw_workspace_catalog(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        catalog = module.构建NSFW工作台目录()
        self.assertIn("defaults", catalog)
        self.assertIn("negative_presets", catalog)

    def test_stage_generator_merges_nsfw_workspace_into_selected_state(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        apply_workspace = module.应用NSFW工作台到阶段状态
        workspace = {
            "enabled": True,
            "trigger_words": ["女仆"],
            "scene": "豪华卧室，红色丝绒床单，镜面天花板",
            "negative_preset": "标准负面提示词",
        }
        result = apply_workspace(
            workspace,
            selected=OrderedDict({"主体": [], "场景背景": [], "服装造型": []}),
            custom_tags=[],
        )
        self.assertTrue(result["negative_prompt"])
        self.assertIn("女仆", result["selected"]["主体"] + result["custom_tags"])

    def test_nsfw_workspace_does_not_revive_normalized_scene_conflict(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        workspace = {
            "enabled": True,
            "preset": "——",
            "quality_tier": "标准",
            "negative_preset": "标准负面提示词",
            "random_mode": "关闭",
            "trigger_words": ["废弃教堂"],
            "scene": "酒店套房",
        }
        result = module._run_stage(
            None,
            **{
                "unique_id": "nsfw-normalized-scene-main",
                "nsfw_workspace": workspace,
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "提示词语言": "纯中文",
                "seed": 31,
            },
        )
        payload = json.loads(result[3])
        self.assertIn("废弃教堂", payload["selected_tags_flat"])
        self.assertNotIn("酒店套房", payload["selected_tags_flat"])
        self.assertTrue(any("仅保留最终归一化后仍有效" in note for note in payload["normalization_notes"]))

        preview = module.构建运行时随机预览状态(
            {
                "unique_id": "nsfw-normalized-scene-preview",
                "selected": {},
                "customTags": [],
                "nsfwWorkspace": workspace,
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": False,
                    "随机主题池": "自动",
                    "seed": 31,
                },
            }
        )
        preview_tags = set(collect_all_tags(OrderedDict(preview["selected"]), preview["customTags"]))
        self.assertIn("废弃教堂", preview_tags)
        self.assertNotIn("酒店套房", preview_tags)

    def test_nsfw_workspace_does_not_revive_normalized_outfit_conflict(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        workspace = {
            "enabled": True,
            "preset": "——",
            "quality_tier": "标准",
            "negative_preset": "标准负面提示词",
            "random_mode": "关闭",
            "trigger_words": ["浴袍"],
            "outfit": "丝质睡袍，腰带松弛，袖口自然垂落",
        }
        result = module._run_stage(
            None,
            **{
                "unique_id": "nsfw-normalized-outfit-main",
                "nsfw_workspace": workspace,
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "提示词语言": "纯中文",
                "seed": 31,
            },
        )
        payload = json.loads(result[3])
        self.assertIn("丝质睡袍", payload["selected_tags_flat"])
        self.assertNotIn("浴袍", payload["selected_tags_flat"])
        self.assertTrue(any("成人向服装收敛" in note for note in payload["normalization_notes"]))

        preview = module.构建运行时随机预览状态(
            {
                "unique_id": "nsfw-normalized-outfit-preview",
                "selected": {},
                "customTags": [],
                "nsfwWorkspace": workspace,
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": False,
                    "随机主题池": "自动",
                    "seed": 31,
                },
            }
        )
        preview_tags = set(collect_all_tags(OrderedDict(preview["selected"]), preview["customTags"]))
        self.assertIn("丝质睡袍", preview_tags)
        self.assertNotIn("浴袍", preview_tags)

    def test_stage_generator_run_stage_exposes_nsfw_json_payload(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()

        class DummyModel:
            pass

        module._build_prompt_list_impl = lambda *args, **kwargs: ["写实摄影，成年女性，豪华卧室，女仆"]
        module._maybe_model_refine_batch_impl = lambda model, prompt_list, settings, **kwargs: list(prompt_list)
        module._update_history = lambda *args, **kwargs: []
        module._build_negative_prompt_from_state_impl = lambda *args, **kwargs: "推荐负面词"
        original_build_json = module._build_json_payload_impl
        original_build_cache = module._build_cache_payload_impl
        captured: dict[str, object] = {}

        def fake_json_payload(**kwargs):
            captured.update(kwargs)
            return original_build_json(**kwargs)

        module._build_json_payload_impl = fake_json_payload
        module._build_cache_payload_impl = lambda **kwargs: dict(kwargs)
        try:
            result = module._run_stage(
                DummyModel(),
                **{
                    "nsfw_workspace": {
                        "enabled": True,
                        "trigger_words": ["女仆"],
                        "scene": "豪华卧室，红色丝绒床单，镜面天花板",
                        "negative_preset": "标准负面提示词",
                        "custom_negative": "low quality, blurry, bad anatomy",
                    },
                    "主体标签1": "成年女性",
                    "场景背景标签1": "豪华卧室",
                    "自定义补充标签": "",
                    "qwen模型": DummyModel(),
                    "运行时随机标签": False,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "中",
                    "随机主题池": "自动",
                    "核心标签锁定数量": 10,
                    "生成数量": 1,
                    "提示词语言": "纯中文",
                    "详细度": "标准",
                    "输出模式": "完整结果",
                    "标签反推模式": "自动平衡",
                    "优先柔和肤质": False,
                    "抑制文字伪影": False,
                    "最大生成token": 256,
                    "温度": 0.62,
                    "top_p": 0.9,
                    "top_k": 40,
                    "重复惩罚": 1.08,
                    "频率惩罚": 0.0,
                    "存在惩罚": 0.0,
                    "seed": 0,
                    "输出think块": False,
                    "随机补充避重缓存": "",
                },
            )
        finally:
            module._build_json_payload_impl = original_build_json
            module._build_cache_payload_impl = original_build_cache
        payload = json.loads(result[3])
        self.assertIn("nsfw_workspace", payload)
        self.assertIn("nsfw_workspace_state", payload)
        self.assertIn("nsfw_negative_prompt", payload)
        self.assertIn("nsfw_negative", payload)
        self.assertEqual(payload["nsfw_workspace"]["trigger_words"], ["女仆"])
        self.assertTrue(payload["nsfw_negative_prompt"])
        self.assertTrue(payload["nsfw_negative"]["prompt"])
        self.assertIn("low quality", result[4])
        self.assertEqual(payload["template_style"], "真实感")
        self.assertEqual(payload["subject_type"], "人物角色")
        self.assertEqual(captured["settings"]["标签反推模式"], "成人向成熟")
        self.assertTrue(captured["settings"]["优先柔和肤质"])
        self.assertTrue(captured["settings"]["抑制文字伪影"])
        self.assertIn("NSFW工作台标签摘要", captured["settings"])
        self.assertIn("女仆", captured["settings"]["NSFW工作台标签摘要"])
        self.assertLessEqual(captured["settings"]["NSFW工作台标签摘要"].count("豪华卧室"), 1)
        self.assertIn("模型后置素材摘要", captured["settings"])
        self.assertIn("NSFW摘要", captured["settings"]["模型后置素材摘要"])
        self.assertIn("标签反推模式：成人向成熟", payload["selected_tags_text"])

    def test_stage_generator_stabilizes_smart_text_model_output(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()

        class DummyModel:
            pass

        original_build_prompt = module._build_prompt_list_impl
        original_refine_batch = module._maybe_model_refine_batch_impl
        original_refine_one = module._maybe_model_refine_impl
        original_update_history = module._update_history
        module._build_prompt_list_impl = lambda *args, **kwargs: ["成年女性，全景全身，人物完整入镜，雨夜站台，高细节"]
        module._maybe_model_refine_batch_impl = lambda model, prompt_list, settings, **kwargs: list(prompt_list)
        module._maybe_model_refine_impl = lambda model, prompt, settings, **kwargs: (
            "Create a coherent image centered on the main subject, 全景全身，全景全身，人物完整入镜，高细节，高细节，清晰对焦，清晰对焦，成年女性，雨夜站台"
        )
        module._update_history = lambda *args, **kwargs: []
        try:
            result = module._run_stage(
                DummyModel(),
                **{
                    "主体标签1": "成年女性",
                    "场景背景标签1": "雨夜站台",
                    "智能文本匹配": True,
                    "智能文本输入": "成年女性，雨夜站台，全身商业摄影",
                    "qwen模型": DummyModel(),
                    "模型来源": "API接口",
                    "运行时随机标签": False,
                    "生成数量": 1,
                    "提示词语言": "纯中文",
                    "详细度": "标准",
                    "输出模式": "完整结果",
                    "最大生成token": 512,
                },
            )
        finally:
            module._build_prompt_list_impl = original_build_prompt
            module._maybe_model_refine_batch_impl = original_refine_batch
            module._maybe_model_refine_impl = original_refine_one
            module._update_history = original_update_history
        smart_prompt = result[6]
        self.assertNotIn("Create a coherent image", smart_prompt)
        self.assertIn("成年女性", smart_prompt)
        self.assertIn("雨夜站台", smart_prompt)
        self.assertEqual(smart_prompt.count("全景全身"), 1)
        self.assertEqual(smart_prompt.count("高细节"), 1)

    def test_stage_generator_falls_back_when_model_batch_returns_same_prompt(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()

        class DummyModel:
            pass

        original_build_prompt = module._build_prompt_list_impl
        original_refine_batch = module._maybe_model_refine_batch_impl
        original_update_history = module._update_history
        module._build_prompt_list_impl = lambda *args, **kwargs: [
            "商业摄影，成年女性，雨夜站台，红色风衣，全景全身，高细节",
            "商业摄影，成年女性，海边黄昏，白色长裙，全景全身，高细节",
        ]
        module._maybe_model_refine_batch_impl = lambda model, prompt_list, settings, **kwargs: [
            "商业摄影，成年女性，影棚，全景全身，高细节，清晰对焦",
            "商业摄影，成年女性，影棚，全景全身，高细节，清晰对焦",
        ]
        module._update_history = lambda *args, **kwargs: []
        try:
            result = module._run_stage(
                DummyModel(),
                **{
                    "主体标签1": "成年女性",
                    "场景背景标签1": "雨夜站台",
                    "qwen模型": DummyModel(),
                    "模型来源": "API接口",
                    "运行时随机标签": False,
                    "生成数量": 2,
                    "提示词语言": "纯中文",
                    "详细度": "标准",
                    "输出模式": "完整结果",
                    "最大生成token": 512,
                },
            )
        finally:
            module._build_prompt_list_impl = original_build_prompt
            module._maybe_model_refine_batch_impl = original_refine_batch
            module._update_history = original_update_history
        prompt_collection = result[5]
        prompts = prompt_collection.split("\n\n")
        self.assertEqual(len(prompts), 2)
        self.assertNotEqual(prompts[0], prompts[1])
        self.assertIn("影棚", prompts[0])
        self.assertIn("海边黄昏", prompts[1])
        self.assertIn("白色长裙", prompts[1])
        self.assertEqual(prompt_collection.count("影棚"), 1)

    def test_stage_generator_skill_mode_filters_empty_placeholder_and_adds_sparse_scaffold(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()

        kwargs = {
            "模型来源": "仅Skill",
            "模板风格": "自动",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "运行时随机标签": False,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "核心标签锁定数量": 10,
            "生成数量": 1,
            "提示词语言": "纯中文",
            "详细度": "标准",
            "输出模式": "完整结果",
            "标签反推模式": "自动平衡",
            "风格隔离策略": "平衡收敛",
            "优先柔和肤质": False,
            "抑制文字伪影": False,
            "自定义补充标签": "[]",
            "额外要求": "",
            "智能文本匹配": False,
            "智能文本输入": "",
            "智能文本风格优先": "自动判断",
            "图片反推生成": False,
            "图片反推模式": "角色设定图",
            "图片反推最大边长": 960,
            "最大生成token": 1800,
            "温度": 0.62,
            "top_p": 0.9,
            "top_k": 40,
            "重复惩罚": 1.08,
            "频率惩罚": 0.0,
            "存在惩罚": 0.0,
            "seed": 0,
            "输出think块": False,
            "随机补充避重缓存": "",
        }
        result = module._run_stage(None, **kwargs)
        positive = result[1]
        selected_text = result[2]

        self.assertNotIn("[]", positive)
        self.assertNotIn("自定义补充自然融入同一个场景：[]", positive)
        self.assertTrue(positive.startswith("写实摄影"))
        self.assertIn("成年人物主体", positive)
        self.assertIn("真实感", positive)
        self.assertIn("简洁室内", positive)
        self.assertIn("自然光", positive)
        self.assertIn("站姿挺拔", positive)
        self.assertIn("全景全身", positive)
        self.assertIn("人物完整入镜", positive)
        self.assertIn("Skill空输入脚手架", selected_text)

    def test_nsfw_mapper_routes_known_terms_into_stage_groups(self) -> None:
        workspace = {
            "trigger_words": ["女仆，护士"],
            "selector_character": "猫女 catgirl",
            "selector_outfit": "内衣 lingerie",
            "selector_action": "接吻 kissing",
            "selector_scene": "温泉 onsen hot spring",
            "selector_expression": "诱惑视线 seductive gaze",
            "selector_prop": "项圈 collar",
            "scene": "豪华卧室，红色丝绒床单，镜面天花板",
            "action": "男女深吻，舌尖交缠，男抚摸女阴道",
            "outfit": "透明睡袍，阴道隐约可见",
            "mood": "禁忌诱惑，嘴角微翘",
            "camera_angle": "床边视角，捕捉明暗插入动作",
            "color_tone": "赤裸渴望，湿润唇部",
            "custom_prefix": "Ultra realistic",
            "custom_suffix": "cinematic framing",
            "negative_preset": "标准负面提示词",
            "custom_negative": "",
        }
        result = nsfw_mapper.map_nsfw_workspace_to_stage_state(
            workspace,
            tag_group_index={"女仆": "主体", "护士": "主体", "猫女": "主体", "接吻": "动作姿态", "透明睡袍": "服装造型", "豪华卧室": "场景背景", "床边视角": "构图视角"},
            group_slot_limits={"主体": 4, "动作姿态": 3, "服装造型": 3, "场景背景": 3, "构图视角": 2},
        )
        self.assertIn("女仆", result["selected"]["主体"])
        self.assertIn("护士", result["selected"]["主体"])
        self.assertIn("猫女", result["selected"]["主体"])
        self.assertIn("接吻", result["selected"]["动作姿态"])
        self.assertIn("透明睡袍", result["selected"]["服装造型"])
        self.assertIn("床边视角", result["selected"]["构图视角"])
        self.assertIn("赤裸渴望", result["custom_tags"])
        self.assertIn("内衣", result["custom_tags"])
        self.assertIn("温泉", result["custom_tags"])
        self.assertIn("诱惑视线", result["custom_tags"])
        self.assertIn("项圈", result["custom_tags"])
        self.assertNotIn("猫女 catgirl", result["custom_tags"])
        self.assertNotIn("内衣 lingerie", result["custom_tags"])
        self.assertNotIn("接吻 kissing", result["custom_tags"])
        self.assertNotIn("温泉 onsen hot spring", result["custom_tags"])
        self.assertNotIn("诱惑视线 seductive gaze", result["custom_tags"])
        self.assertNotIn("项圈 collar", result["custom_tags"])
        self.assertNotIn("女仆，护士", result["custom_tags"])
        self.assertTrue(any("Ultra realistic" in tag for tag in result["custom_tags"]))
        self.assertTrue(result["negative_prompt"])

    def test_nsfw_selector_preserves_pure_english_phrases(self) -> None:
        self.assertEqual(list(nsfw_mapper._iter_selector_terms("adult woman")), ["adult woman"])
        self.assertEqual(list(nsfw_mapper._iter_selector_terms("mature adult man")), ["mature adult man"])
        self.assertEqual(list(nsfw_mapper._iter_selector_terms("猫女 catgirl")), ["猫女"])

    def test_nsfw_negative_preset_prefers_custom_when_selected(self) -> None:
        workspace = {
            "negative_preset": "自定义负面提示词",
            "custom_negative": "low quality, blurry, bad anatomy",
        }
        self.assertEqual(nsfw_mapper.resolve_nsfw_negative_prompt(workspace), "low quality, blurry, bad anatomy")

    def test_nsfw_mapper_applies_preset_and_quality_terms(self) -> None:
        workspace = {
            "preset": "经典情色",
            "quality_tier": "大师级",
            "negative_preset": "标准负面提示词",
        }
        result = nsfw_mapper.map_nsfw_workspace_to_stage_state(
            workspace,
            tag_group_index={"豪华卧室": "场景背景"},
            group_slot_limits={"场景背景": 3},
        )
        self.assertIn("豪华卧室", result["selected"]["场景背景"])
        self.assertIn("masterpiece", result["custom_tags"])
        self.assertIn("professional photography", result["custom_tags"])
        self.assertTrue(any("男女深吻" in tag for tag in result["custom_tags"]))
        action_index = next(index for index, tag in enumerate(result["custom_tags"]) if "男女深吻" in tag)
        self.assertLess(action_index, result["custom_tags"].index("masterpiece"))

    def test_nsfw_mapper_keeps_custom_prefix_and_suffix_out_of_group_slots(self) -> None:
        workspace = {
            "trigger_words": [],
            "scene": "——",
            "action": "——",
            "outfit": "——",
            "mood": "——",
            "custom_prefix": "真实感",
            "custom_suffix": "电影感",
            "negative_preset": "标准负面提示词",
            "negative_apply_mode": "preview",
        }
        result = nsfw_mapper.map_nsfw_workspace_to_stage_state(
            workspace,
            tag_group_index={"真实感": "画面风格", "电影感": "技术画质"},
            group_slot_limits={"画面风格": 4, "技术画质": 3},
        )
        self.assertEqual(result["selected"]["画面风格"], [])
        self.assertEqual(result["selected"]["技术画质"], [])
        self.assertIn("真实感", result["custom_tags"])
        self.assertIn("电影感", result["custom_tags"])

    def test_nsfw_mapper_exposes_negative_prompt_mode_metadata(self) -> None:
        defaults = nsfw_presets.build_nsfw_workspace_defaults()
        self.assertIn("negative_apply_mode", defaults)
        self.assertEqual(defaults["negative_apply_mode"], "preview")

        workspace = {
            "negative_preset": "标准负面提示词",
            "negative_apply_mode": "override",
            "custom_negative": "",
        }
        result = nsfw_mapper.map_nsfw_workspace_to_stage_state(
            workspace,
            tag_group_index={},
            group_slot_limits={},
        )
        self.assertIn("negative", result)
        self.assertEqual(result["negative"]["mode"], "override")
        self.assertTrue(result["negative"]["prompt"])

    def test_template_style_base_map_covers_every_non_auto_option(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        self.assertEqual(set(skills.TEMPLATE_STYLE_BASE_MAP), set(module.模板选项) - {"自动"})
        self.assertEqual(
            set(skills.TEMPLATE_STYLE_BASE_MAP.values()),
            {"真实感", "插画感", "CG感", "古风", "神话感"},
        )

    def test_sparse_scaffold_uses_explicit_template_base_style(self) -> None:
        cases = {
            "商业摄影": "真实感",
            "复古动画": "插画感",
            "东方赛博": "CG感",
            "国风电影": "古风",
            "暗黑奇幻": "神话感",
        }
        for configured_style, expected_base_style in cases.items():
            with self.subTest(configured_style=configured_style):
                selected = OrderedDict(
                    (name, [])
                    for name in ("主体", "画面风格", "成人向表达", "光影氛围", "动作姿态", "服装造型", "场景背景", "道具世界观")
                )
                settings = {
                    "模型来源": "仅Skill",
                    "模板风格": configured_style,
                    "随机主题池": "自动",
                    "运行时随机标签": False,
                    "主体类型": "人物角色",
                }
                notes: list[str] = []
                skills._apply_sparse_skill_scaffold(
                    selected=selected,
                    custom_tags=[],
                    settings=settings,
                    notes=notes,
                    collect_all_tags=collect_all_tags,
                )
                self.assertEqual(selected["画面风格"], [expected_base_style])
                self.assertEqual(settings["模板风格"], configured_style)

    def test_specialized_template_uses_base_positive_exclusions(self) -> None:
        cases = {
            "商业摄影": ("OVA风", "商业广告大片"),
            "复古动画": ("虚幻引擎", "OVA风"),
            "东方赛博": ("水彩", "CG感"),
            "国风电影": ("未来都市", "古风"),
            "暗黑奇幻": ("未来都市", "神话感"),
        }
        for style, (blocked, allowed) in cases.items():
            with self.subTest(style=style):
                filtered = prompt_builder._filter_style_positive_fragments([blocked, allowed], style)
                self.assertNotIn(blocked, filtered)
                self.assertIn(allowed, filtered)

    def test_runtime_style_isolation_keeps_specialized_target_family(self) -> None:
        selected = OrderedDict({"画面风格": ["插画感", "OVA风", "CG感", "虚幻引擎"]})
        custom_tags: list[str] = []
        notes: list[str] = []
        skills._apply_runtime_random_style_isolation(
            selected=selected,
            custom_tags=custom_tags,
            settings={"模板风格": "复古动画", "运行时随机标签": True, "风格隔离策略": "平衡收敛"},
            notes=notes,
            context={
                "runtime_style_isolation_families": {
                    "真实感": {"真实感"},
                    "插画感": {"插画感", "OVA风"},
                    "CG感": {"CG感", "虚幻引擎"},
                    "古风": {"古风"},
                    "神话感": {"神话感"},
                },
                "style_positive_exclusion_terms": {"插画感": ("CG感", "虚幻引擎")},
            },
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
        )
        self.assertIn("插画感", selected["画面风格"])
        self.assertIn("OVA风", selected["画面风格"])
        self.assertNotIn("CG感", selected["画面风格"])
        self.assertNotIn("虚幻引擎", selected["画面风格"])

    def test_theme_profile_rotation_continues_after_full_cycle(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        node_id = "theme-full-cycle"
        cursors: list[int] = []
        for _ in range(12):
            selected = OrderedDict((name, []) for name, _, _ in module._all_tag_groups())
            settings = {"模板风格": "自动", "随机主题池": "商业摄影", "seed": 0, "unique_id": node_id}
            _style, next_selected, next_custom = module._apply_random_theme_pool_bias("真实感", selected, [], settings)
            markers = list(settings.get("随机主题池档案标记", []))
            cursor_marker = next(marker for marker in markers if str(marker).startswith("variantcursor:商业摄影:"))
            cursors.append(int(str(cursor_marker).rsplit(":", 1)[1]))
            module._update_runtime_random_history(
                node_id,
                selected=next_selected,
                custom_tags=next_custom,
                generated=[],
                prompt_list=[],
                extra_markers=markers,
            )
        self.assertEqual(cursors, [0, 1, 2, 3, 4, 0, 1, 2, 3, 4, 0, 1])

    def test_template_profile_rotation_continues_after_full_cycle(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        node_id = "style-full-cycle"
        cursors: list[int] = []
        for _ in range(10):
            selected = OrderedDict((name, []) for name, _, _ in module._all_tag_groups())
            settings = {"模板风格": "真实感", "seed": 0, "unique_id": node_id}
            next_selected, next_custom = module._apply_template_style_profile_bias("真实感", selected, [], settings)
            markers = list(settings.get("模板风格档案标记", []))
            cursor_marker = next(marker for marker in markers if str(marker).startswith("stylevariantcursor:真实感:"))
            cursors.append(int(str(cursor_marker).rsplit(":", 1)[1]))
            module._update_runtime_random_history(
                node_id,
                selected=next_selected,
                custom_tags=next_custom,
                generated=[],
                prompt_list=[],
                extra_markers=markers,
            )
        self.assertEqual(cursors, [0, 1, 2, 3, 4, 0, 1, 2, 3, 4])

    def test_profile_rotation_resumes_from_serialized_cursors(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        selected = OrderedDict((name, []) for name, _, _ in module._all_tag_groups())

        theme_settings = {
            "模板风格": "自动",
            "随机主题池": "商业摄影",
            "随机补充避重缓存": "variantcursor:商业摄影:2",
            "seed": 0,
            "unique_id": "theme-cursor-restored",
        }
        module._apply_random_theme_pool_bias("真实感", selected, [], theme_settings)
        self.assertIn("variantcursor:商业摄影:3", theme_settings["随机主题池档案标记"])

        style_settings = {
            "模板风格": "真实感",
            "随机补充避重缓存": "stylevariantcursor:真实感:2",
            "seed": 0,
            "unique_id": "style-cursor-restored",
        }
        module._apply_template_style_profile_bias("真实感", selected, [], style_settings)
        self.assertIn("stylevariantcursor:真实感:3", style_settings["模板风格档案标记"])

    def test_preview_profile_pipeline_order_matches_generation_order(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        calls: list[str] = []
        original_normalize = module._normalize_inference_state
        original_random = module._build_runtime_tags
        original_theme = module._apply_random_theme_pool_bias
        original_style = module._apply_template_style_profile_bias

        def normalize_stub(selected, custom_tags, settings):
            calls.append("normalize")
            return selected, custom_tags, []

        def random_stub(selected, custom_tags, settings):
            calls.append("random")
            return selected, custom_tags, []

        def theme_stub(template_style, selected, custom_tags, settings):
            calls.append("theme")
            return template_style, selected, custom_tags

        def style_stub(template_style, selected, custom_tags, settings):
            calls.append("style")
            return selected, custom_tags

        module._normalize_inference_state = normalize_stub
        module._build_runtime_tags = random_stub
        module._apply_random_theme_pool_bias = theme_stub
        module._apply_template_style_profile_bias = style_stub
        try:
            module.构建运行时随机预览状态(
                {
                    "selected": {},
                    "customTags": [],
                    "settings": {
                        "模板风格": "真实感",
                        "运行时随机标签": True,
                        "随机主题池": "商业摄影",
                    },
                }
            )
        finally:
            module._normalize_inference_state = original_normalize
            module._build_runtime_tags = original_random
            module._apply_random_theme_pool_bias = original_theme
            module._apply_template_style_profile_bias = original_style
        self.assertEqual(calls, ["normalize", "random", "theme", "style", "normalize"])

    def test_preview_parses_custom_tag_arrays_without_stringifying_them(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module.构建运行时随机预览状态(
            {
                "selected": {"主体": ["成年女性"]},
                "customTags": ["保留自定义", "第二标签", "保留自定义"],
                "settings": {
                    "模板风格": "真实感",
                    "运行时随机标签": False,
                    "随机主题池": "自动",
                },
            }
        )
        self.assertIn("保留自定义", result["customTags"])
        self.assertIn("第二标签", result["customTags"])
        self.assertEqual(result["customTags"].count("保留自定义"), 1)
        self.assertFalse(any(str(tag).startswith("[") for tag in result["customTags"]))

    def test_runtime_random_preview_uses_explicit_cache_namespace(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module.构建运行时随机预览状态(
            {
                "unique_id": "17",
                "cache_namespace": "node-preview-cache-0001",
                "selected": {"主体": ["成年女性"]},
                "settings": {
                    "模板风格": "真实感",
                    "运行时随机标签": True,
                    "运行时随机模式": "保留已选核心标签",
                    "随机主题池": "自动",
                    "seed": 123,
                },
            }
        )
        self.assertEqual(result["settings"]["cache_namespace"], "node-preview-cache-0001")
        self.assertEqual(result["settings"]["cache_key"], "stage:node-preview-cache-0001")

    def test_specialized_template_style_survives_full_generation_pipeline(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        cases = {
            "商业摄影": "真实感",
            "复古动画": "插画感",
            "东方赛博": "CG感",
            "国风电影": "古风",
            "暗黑奇幻": "神话感",
        }
        for style, base_style in cases.items():
            with self.subTest(style=style):
                module._CACHE.clear()
                result = module._run_stage(
                    None,
                    **{
                        "unique_id": f"specialized-style-{style}",
                        "模板风格": style,
                        "随机主题池": "自动",
                        "生成数量": 1,
                        "提示词语言": "纯中文",
                        "运行时随机标签": False,
                        "模型来源": "仅Skill",
                        "seed": 0,
                    },
                )
                payload = json.loads(result[3])
                self.assertEqual(payload["template_style"], style)
                self.assertEqual(module._base_template_style(payload["template_style"]), base_style)
                if base_style != "真实感":
                    self.assertNotIn("真实感", payload["selected_tags_flat"])
                self.assertTrue(payload["profile_rotation_markers"])

    def test_every_theme_and_template_option_runs_through_full_generation_pipeline(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()

        for pool in module.随机主题池选项[1:]:
            with self.subTest(kind="theme", option=pool):
                result = module._run_stage(
                    None,
                    **{
                        "unique_id": f"full-theme-{pool}",
                        "模板风格": "自动",
                        "随机主题池": pool,
                        "生成数量": 1,
                        "提示词语言": "纯中文",
                        "运行时随机标签": False,
                        "模型来源": "仅Skill",
                        "seed": 0,
                    },
                )
                payload = json.loads(result[3])
                self.assertTrue(result[1].strip())
                self.assertTrue(payload["selected_tags_flat"])
                self.assertEqual(payload["runtime_random_theme_pool"], pool)
                self.assertTrue(any(str(marker).startswith(f"variantcursor:{pool}:") for marker in payload["profile_rotation_markers"]))

        for style in module.模板选项[1:]:
            with self.subTest(kind="style", option=style):
                result = module._run_stage(
                    None,
                    **{
                        "unique_id": f"full-style-{style}",
                        "模板风格": style,
                        "随机主题池": "自动",
                        "生成数量": 1,
                        "提示词语言": "纯中文",
                        "运行时随机标签": False,
                        "模型来源": "仅Skill",
                        "seed": 0,
                    },
                )
                payload = json.loads(result[3])
                self.assertTrue(result[1].strip())
                self.assertTrue(payload["selected_tags_flat"])
                self.assertEqual(payload["template_style"], style)
                self.assertTrue(any(str(marker).startswith(f"stylevariantcursor:{style}:") for marker in payload["profile_rotation_markers"]))

    def test_strict_prompt_dedupe_keeps_fixed_candidate_unique(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        base = "商业广告大片，银白长发，修身礼服，摄影棚，回眸，风暴天光，书本，高细节"
        outputs = [
            module._strict_dedupe_prompt_list(
                "strict-fixed-candidate",
                [base],
                {"提示词语言": "纯中文", "连续生成避重缓存": ""},
            )[0]
            for _ in range(12)
        ]
        self.assertEqual(len(set(outputs)), len(outputs))
        self.assertTrue(all(previous != current for previous, current in zip(outputs, outputs[1:])))

    def test_strict_prompt_dedupe_normalizes_case_width_and_common_separators(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        first = "ABC prompt, adult woman, studio light"
        equivalent = "ＡＢＣ PROMPT、adult woman，studio light"
        self.assertEqual(module._canonical_prompt_hash(first), module._canonical_prompt_hash(equivalent))
        outputs = module._strict_dedupe_prompt_list(
            "strict-compatible-text",
            [first, equivalent],
            {"提示词语言": "纯英文", "连续生成避重缓存": ""},
        )
        self.assertEqual(outputs[0], first)
        self.assertNotEqual(outputs[1], equivalent)
        self.assertIn("visual variation", outputs[1])

    def test_strict_prompt_dedupe_slow_node_does_not_block_other_node_cache_getter(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        slow_key = "slow-strict-node"
        other_key = "unrelated-stage-output"
        base = "fixed prompt, adult woman, studio, soft light, high detail"
        settings = {"提示词语言": "纯英文", "连续生成避重缓存": ""}
        module._strict_dedupe_prompt_list(slow_key, [base], settings)
        module._cache_output(other_key, {"status": "done", "prompt_text": "other prompt"})

        entered_stabilizer = threading.Event()
        release_stabilizer = threading.Event()
        getter_finished = threading.Event()
        strict_errors: list[Exception] = []
        getter_result: list[dict[str, object] | None] = []
        original_stabilizer = module._stabilize_prompt_output_impl

        def slow_stabilizer(text, state):
            entered_stabilizer.set()
            release_stabilizer.wait(timeout=5)
            return original_stabilizer(text, state)

        def run_strict() -> None:
            try:
                module._strict_dedupe_prompt_list(slow_key, [base], {"提示词语言": "纯英文"})
            except Exception as exc:  # pragma: no cover - asserted below
                strict_errors.append(exc)

        def read_other_cache() -> None:
            getter_result.append(module.获取阶段节点输出缓存(other_key))
            getter_finished.set()

        module._stabilize_prompt_output_impl = slow_stabilizer
        strict_thread = threading.Thread(target=run_strict)
        getter_thread = threading.Thread(target=read_other_cache)
        try:
            strict_thread.start()
            self.assertTrue(entered_stabilizer.wait(timeout=5))
            getter_thread.start()
            completed_while_slow = getter_finished.wait(timeout=0.5)
        finally:
            release_stabilizer.set()
            strict_thread.join(timeout=5)
            getter_thread.join(timeout=5)
            module._stabilize_prompt_output_impl = original_stabilizer

        self.assertTrue(completed_while_slow)
        self.assertFalse(strict_thread.is_alive())
        self.assertFalse(getter_thread.is_alive())
        self.assertEqual(strict_errors, [])
        self.assertEqual(getter_result, [{"status": "done", "prompt_text": "other prompt"}])

    def test_strict_prompt_dedupe_serializes_concurrent_runs_for_same_node(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        worker_count = 12
        barrier = threading.Barrier(worker_count)
        result_lock = threading.Lock()
        outputs: list[str] = []
        errors: list[Exception] = []
        base = "same node concurrent prompt, adult woman, studio, soft light, high detail"

        def worker() -> None:
            try:
                barrier.wait(timeout=5)
                output = module._strict_dedupe_prompt_list(
                    "same-node-concurrent-strict",
                    [base],
                    {"提示词语言": "纯英文", "连续生成避重缓存": ""},
                )[0]
                with result_lock:
                    outputs.append(output)
            except Exception as exc:  # pragma: no cover - asserted below
                with result_lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(worker_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(len(outputs), worker_count)
        self.assertEqual(len(set(outputs)), worker_count)

    def test_strict_prompt_dedupe_migrates_v2_legacy_hashes(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        base = "ABC Prompt, adult woman; studio light"
        legacy_hash = module._legacy_canonical_prompt_hash(base)
        settings = {
            "提示词语言": "纯英文",
            "连续生成避重缓存": json.dumps(
                {
                    "version": 2,
                    "channels": {
                        "prompt": {
                            "cursor": 0,
                            "hashes": [legacy_hash],
                            "base_hashes": [legacy_hash],
                        }
                    },
                }
            ),
        }
        output = module._strict_dedupe_prompt_list("strict-v2-migration", [base], settings)[0]
        self.assertNotEqual(output, base)
        migrated = json.loads(settings["连续生成避重缓存输出"])
        self.assertEqual(migrated["version"], 3)
        self.assertEqual(migrated["hash_algorithm"], "nfkc-casefold-common-separators-v1")
        self.assertNotIn(legacy_hash, migrated["channels"]["prompt"]["legacy_hashes"])
        self.assertTrue(migrated["channels"]["prompt"]["hashes"])

    def test_strict_prompt_dedupe_hashes_nonempty_punctuation_only_text(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        settings = {"提示词语言": "纯中文", "连续生成避重缓存": ""}
        first = module._strict_dedupe_prompt_list("strict-punctuation", ["。"], settings)[0]
        second = module._strict_dedupe_prompt_list("strict-punctuation", ["。"], settings)[0]
        self.assertEqual(first, "。")
        self.assertNotEqual(second, first)
        self.assertTrue(module._canonical_prompt_hash("。"))

    def test_strict_prompt_dedupe_restores_hashes_from_serialized_cache(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        base = "固定提示词，成年女性，摄影棚，柔光，高细节"
        first_settings = {"提示词语言": "纯中文", "连续生成避重缓存": ""}
        first = module._strict_dedupe_prompt_list("strict-cache-source", [base], first_settings)[0]
        serialized = first_settings["连续生成避重缓存输出"]
        self.assertNotIn(base, serialized)

        module._CACHE.clear()
        second_settings = {"提示词语言": "纯中文", "连续生成避重缓存": serialized}
        second = module._strict_dedupe_prompt_list("strict-cache-restored", [base], second_settings)[0]
        self.assertNotEqual(first, second)

    def test_strict_prompt_dedupe_parser_keeps_only_the_recent_bounded_window(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        hashes = [f"{index:064x}" for index in range(module._STRICT_PROMPT_HASH_HISTORY_LIMIT + 12)]
        base_hashes = [f"{index + 10000:064x}" for index in range(module._STRICT_PROMPT_BASE_HASH_HISTORY_LIMIT + 12)]
        state = module._parse_prompt_dedupe_cache(
            {
                "channels": {
                    "prompt": {
                        "cursor": 99,
                        "hashes": hashes,
                        "base_hashes": base_hashes,
                    }
                }
            }
        )
        channel = state["channels"]["prompt"]
        self.assertEqual(channel["hashes"], hashes[: module._STRICT_PROMPT_HASH_HISTORY_LIMIT])
        self.assertEqual(channel["base_hashes"], base_hashes[: module._STRICT_PROMPT_BASE_HASH_HISTORY_LIMIT])

    def test_strict_prompt_dedupe_does_not_wrap_after_full_variation_space(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        base = "固定长程提示词，成年女性，摄影棚，柔光，全景全身，高细节"
        settings = {"提示词语言": "纯中文", "连续生成避重缓存": ""}
        outputs = [
            module._strict_dedupe_prompt_list(
                "strict-long-session",
                [base],
                settings,
            )[0]
            for _ in range(600)
        ]
        self.assertEqual(len(set(outputs)), 600)
        serialized_channel = module._parse_prompt_dedupe_cache(settings["连续生成避重缓存输出"])["channels"]["prompt"]
        memory_channel = module._CACHE["strict-long-session"]["strict_prompt_dedupe"]["channels"]["prompt"]
        for channel in (serialized_channel, memory_channel):
            self.assertLessEqual(len(channel["hashes"]), module._STRICT_PROMPT_HASH_HISTORY_LIMIT)
            self.assertLessEqual(len(channel["base_hashes"]), module._STRICT_PROMPT_BASE_HASH_HISTORY_LIMIT)
            self.assertGreaterEqual(channel["cursor"], 599)

    def test_stage_cache_namespace_isolates_same_node_id_across_workflows(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()

        def workflow_meta(namespace: str) -> dict:
            return {
                "workflow": {
                    "nodes": [
                        {
                            "id": 7,
                            "properties": {module._CACHE_NAMESPACE_PROPERTY: namespace},
                        }
                    ]
                }
            }

        namespace_a = "node-workflow-a-0001"
        namespace_b = "node-workflow-b-0001"
        common = {
            "unique_id": "7",
            "主体标签1": "成年女性",
            "模板风格": "真实感",
            "随机主题池": "自动",
            "生成数量": 1,
            "提示词语言": "纯中文",
            "运行时随机标签": False,
            "模型来源": "仅Skill",
            "seed": 123,
        }
        first_a = module._run_stage(None, **common, extra_pnginfo=workflow_meta(namespace_a))[1]
        first_b = module._run_stage(None, **common, extra_pnginfo=workflow_meta(namespace_b))[1]
        second_a = module._run_stage(None, **common, extra_pnginfo=workflow_meta(namespace_a))[1]

        self.assertEqual(first_a, first_b)
        self.assertNotEqual(second_a, first_a)
        self.assertEqual(
            module._resolve_stage_cache_key("7", extra_pnginfo=workflow_meta(namespace_a)),
            f"stage:{namespace_a}",
        )
        self.assertIsNotNone(module.获取阶段节点输出缓存("7", cache_namespace=namespace_a))
        self.assertIsNotNone(module.获取阶段节点输出缓存("7", cache_namespace=namespace_b))

    def test_stage_cache_rejects_explicit_invalid_namespace_without_legacy_fallback(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._cache_output("7", {"status": "done", "prompt_text": "legacy output"})

        self.assertIsNotNone(module.获取阶段节点输出缓存("7"))
        self.assertEqual(module._resolve_stage_cache_key("7", cache_namespace="bad"), "")
        self.assertIsNone(module.获取阶段节点输出缓存("7", cache_namespace="bad"))
        invalid_workflow = {
            "workflow": {
                "nodes": [
                    {
                        "id": 7,
                        "properties": {module._CACHE_NAMESPACE_PROPERTY: "bad"},
                    }
                ]
            }
        }
        self.assertEqual(module._resolve_stage_cache_key("7", extra_pnginfo=invalid_workflow), "")

        result = module._run_stage(
            None,
            **{
                "unique_id": "7",
                "cache_namespace": "bad",
                "主体标签1": "成年女性",
                "模板风格": "真实感",
                "随机主题池": "自动",
                "生成数量": 1,
                "提示词语言": "纯中文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 123,
            },
        )
        self.assertTrue(result[1].strip())
        self.assertEqual(module._CACHE["7"]["prompt_text"], "legacy output")

        preview = module.构建运行时随机预览状态(
            {
                "unique_id": "7",
                "cache_namespace": "bad",
                "selected": {},
                "customTags": [],
                "settings": {"运行时随机标签": False},
            }
        )
        self.assertEqual(preview["settings"]["cache_namespace"], "")
        self.assertEqual(preview["settings"]["cache_key"], "")

    def test_stage_cache_lru_is_bounded(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        for index in range(module._CACHE_NODE_LIMIT + 10):
            module._cache_output(f"bounded-cache-{index}", {"index": index})
        self.assertEqual(len(module._CACHE), module._CACHE_NODE_LIMIT)
        self.assertNotIn("bounded-cache-0", module._CACHE)
        self.assertIn(f"bounded-cache-{module._CACHE_NODE_LIMIT + 9}", module._CACHE)

    def test_strict_prompt_dedupe_replaces_existing_variation_without_stacking(self) -> None:
        cases = {
            "纯中文": "固定中文提示词，成年女性，摄影棚，柔光，高细节",
            "纯英文": "fixed English prompt, adult woman, studio, soft light, high detail",
        }
        for language, base in cases.items():
            with self.subTest(language=language):
                module = load_stage_prompt_generator_for_integration_test()
                module._CACHE.clear()
                current = base
                outputs: list[str] = []
                for _ in range(40):
                    current = module._strict_dedupe_prompt_list(
                        f"strict-chain-{language}",
                        [current],
                        {"提示词语言": language, "连续生成避重缓存": ""},
                    )[0]
                    outputs.append(current)
                self.assertEqual(len(set(outputs)), len(outputs))
                self.assertLess(max(len(text) for text in outputs), len(base) + 500)
                marker = "visual variation" if language == "纯英文" else "画面变化方向"
                self.assertTrue(all(text.lower().count(marker.lower()) <= 1 for text in outputs))

    def test_strict_prompt_dedupe_preserves_both_channels_without_node_id(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        settings = {"提示词语言": "纯中文", "连续生成避重缓存": ""}
        module._strict_dedupe_prompt_list("", ["固定主提示词"], settings, channel="prompt")
        module._strict_dedupe_prompt_list("", ["固定智能提示词"], settings, channel="smart")
        state = module._parse_prompt_dedupe_cache(settings["连续生成避重缓存输出"])
        self.assertEqual(len(state["channels"]["prompt"]["hashes"]), 1)
        self.assertEqual(len(state["channels"]["smart"]["hashes"]), 1)

    def test_stage_generator_tag_block_output_is_strictly_unique_across_runs(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        original_build = module._build_tag_block_prompt_list_impl
        original_refine = module._maybe_model_refine_batch_impl
        fixed = "固定标签块提示词，成年女性，摄影棚，柔光，高细节"
        module._build_tag_block_prompt_list_impl = lambda *args, **kwargs: [fixed]
        module._maybe_model_refine_batch_impl = lambda model, prompt_list, settings, **kwargs: list(prompt_list)
        payload = {"enabled": True, "blocks": [{"type": "text", "label": "固定", "text": fixed}]}
        try:
            outputs = [
                module._run_stage(
                    None,
                    **{
                        "unique_id": "strict-tag-block",
                        "主体标签1": "成年女性",
                        "标签块编排启用": True,
                        "标签块编排JSON": json.dumps(payload, ensure_ascii=False),
                        "生成数量": 1,
                        "提示词语言": "纯中文",
                        "运行时随机标签": False,
                        "模型来源": "仅Skill",
                        "seed": 123,
                    },
                )[1]
                for _ in range(5)
            ]
        finally:
            module._build_tag_block_prompt_list_impl = original_build
            module._maybe_model_refine_batch_impl = original_refine
        self.assertEqual(len(set(outputs)), len(outputs))

    def test_stage_generator_always_executes_for_strict_dedupe(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        changed = module.QwenTE阶段式提示词生成器.IS_CHANGED(运行时随机标签=False, seed=123)
        self.assertNotEqual(changed, changed)

    def test_runtime_random_full_mode_preserves_protected_nsfw_anchors(self) -> None:
        selected = OrderedDict({"主体": ["女仆"], "场景背景": ["豪华卧室"], "动作姿态": ["接吻"], "服装造型": ["透明睡袍"]})
        settings = {
            "运行时随机模式": "全随机",
            "运行时随机强度": "强",
            "核心标签锁定数量": 0,
            "seed": 7,
            "unique_id": "protected-nsfw-anchors",
            "锁定标签白名单": "",
            "运行时随机保护标签": "女仆, 豪华卧室, 接吻, 透明睡袍",
            "随机排除标签": "",
            "随机补充避重缓存": "",
            "随机主题池": "自动",
        }
        next_selected, next_custom, _generated = randomizer.build_runtime_tags(
            selected,
            [],
            settings,
            all_tag_groups=lambda: [
                ("主体", 1, ["无", "女仆", "护士"]),
                ("场景背景", 1, ["无", "豪华卧室", "办公室"]),
                ("动作姿态", 1, ["无", "接吻", "回眸"]),
                ("服装造型", 1, ["无", "透明睡袍", "礼服"]),
            ],
            tag_group_index=lambda: {
                "女仆": "主体",
                "护士": "主体",
                "豪华卧室": "场景背景",
                "办公室": "场景背景",
                "接吻": "动作姿态",
                "回眸": "动作姿态",
                "透明睡袍": "服装造型",
                "礼服": "服装造型",
            },
            parse_tags=lambda value: [item.strip() for item in str(value).split(",") if item.strip()],
            uniq=uniq,
            seed_normalizer=lambda value: int(value),
            history_loader=lambda _node_id: [],
            random_module=random,
            empty_tag="无",
        )
        active = set(collect_all_tags(next_selected, next_custom))
        self.assertTrue({"女仆", "豪华卧室", "接吻", "透明睡袍"}.issubset(active), active)

    def test_runtime_random_seed_zero_records_reusable_effective_seed(self) -> None:
        class FixedSeedRandom:
            Random = random.Random

            @staticmethod
            def randint(_start: int, _end: int) -> int:
                return 24681357

        groups = [("主体", 1, ["无", "女仆", "护士"]), ("场景背景", 1, ["无", "卧室", "办公室"])]
        base_settings = {
            "运行时随机模式": "全随机",
            "运行时随机强度": "强",
            "核心标签锁定数量": 0,
            "seed": 0,
            "unique_id": "seed-zero-preview",
            "锁定标签白名单": "",
            "运行时随机保护标签": "",
            "随机排除标签": "",
            "随机补充避重缓存": "",
            "随机主题池": "自动",
        }
        first_settings = dict(base_settings)
        first_selected, first_custom, first_generated = randomizer.build_runtime_tags(
            OrderedDict((name, []) for name, _, _ in groups),
            [],
            first_settings,
            all_tag_groups=lambda: groups,
            tag_group_index=lambda: {"女仆": "主体", "护士": "主体", "卧室": "场景背景", "办公室": "场景背景"},
            parse_tags=lambda value: [item.strip() for item in str(value).split(",") if item.strip()],
            uniq=uniq,
            seed_normalizer=lambda value: int(value),
            history_loader=lambda _node_id: [],
            random_module=FixedSeedRandom,
            empty_tag="无",
        )
        self.assertEqual(first_settings["运行时随机有效种子"], 24681357)

        replay_settings = {**base_settings, "seed": first_settings["运行时随机有效种子"]}
        replay_selected, replay_custom, replay_generated = randomizer.build_runtime_tags(
            OrderedDict((name, []) for name, _, _ in groups),
            [],
            replay_settings,
            all_tag_groups=lambda: groups,
            tag_group_index=lambda: {"女仆": "主体", "护士": "主体", "卧室": "场景背景", "办公室": "场景背景"},
            parse_tags=lambda value: [item.strip() for item in str(value).split(",") if item.strip()],
            uniq=uniq,
            seed_normalizer=lambda value: int(value),
            history_loader=lambda _node_id: [],
            random_module=FixedSeedRandom,
            empty_tag="无",
        )
        self.assertEqual(first_selected, replay_selected)
        self.assertEqual(first_custom, replay_custom)
        self.assertEqual(first_generated, replay_generated)

    def test_large_runtime_random_seeds_match_preview_and_generation_paths(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        large_seeds = (2147483648, 4294967295)

        for seed in large_seeds:
            with self.subTest(seed=seed):
                _, _, built_settings, _ = module._build_state_from_kwargs({"seed": seed})
                self.assertEqual(built_settings["seed"], seed)

                node_id = f"large-runtime-seed-{seed}"
                preview = module.构建运行时随机预览状态(
                    {
                        "unique_id": node_id,
                        "selected": {"主体": ["成年女性"]},
                        "customTags": [],
                        "settings": {
                            "模板风格": "真实感",
                            "主体类型": "人物角色",
                            "运行时随机标签": True,
                            "运行时随机模式": "全随机",
                            "运行时随机强度": "弱",
                            "随机主题池": "自动",
                            "seed": seed,
                        },
                    }
                )
                self.assertEqual(preview["settings"]["seed"], seed)
                self.assertEqual(preview["meta"]["runtime_random_effective_seed"], seed)
                marker = module._parse_runtime_random_preview_marker(
                    preview["settings"]["运行时随机预览令牌"]
                )
                self.assertIsNotNone(marker)
                self.assertEqual(marker["seed"], seed)

                result = module._run_stage(
                    None,
                    **{
                        "unique_id": f"{node_id}-generation",
                        "主体标签1": "成年女性",
                        "模板风格": "真实感",
                        "随机主题池": "自动",
                        "生成数量": 1,
                        "提示词语言": "纯中文",
                        "运行时随机标签": True,
                        "运行时随机模式": "全随机",
                        "运行时随机强度": "弱",
                        "模型来源": "仅Skill",
                        "seed": seed,
                    },
                )
                self.assertEqual(json.loads(result[3])["runtime_random_effective_seed"], seed)

        self.assertNotEqual(large_seeds[0], large_seeds[1])

    def test_runtime_random_preview_marker_skips_exactly_one_backend_random_pass(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        node_id = "runtime-preview-one-shot"
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": node_id,
                "selected": {"主体": ["成年女性"]},
                "customTags": [],
                "settings": {
                    "模板风格": "自动",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "弱",
                    "随机主题池": "自动",
                    "seed": 0,
                },
            }
        )
        self.assertGreater(int(preview["settings"]["seed"]), 0)
        parsed_marker = module._parse_runtime_random_preview_marker(preview["settings"]["运行时随机预览令牌"])
        self.assertIsNotNone(parsed_marker)
        self.assertEqual(parsed_marker["source"], "backend")

        run_kwargs = dict(preview["settings"])
        run_kwargs.update(
            {
                "unique_id": node_id,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "自定义补充标签": ", ".join(preview["customTags"]),
                "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
            }
        )
        for group_name, slot_count, _options in module._all_tag_groups():
            for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                run_kwargs[f"{group_name}标签{index}"] = tag

        calls: list[str] = []
        original_random = module._build_runtime_tags

        def random_stub(selected, custom_tags, settings):
            calls.append(str(settings.get("unique_id")))
            return selected, custom_tags, []

        module._build_runtime_tags = random_stub
        try:
            first = module._run_stage(None, **run_kwargs)
            self.assertEqual(calls, [])
            self.assertTrue(json.loads(first[3])["runtime_random_preview_consumed"])

            second = module._run_stage(None, **run_kwargs)
            self.assertEqual(calls, [node_id])
            self.assertFalse(json.loads(second[3])["runtime_random_preview_consumed"])
        finally:
            module._build_runtime_tags = original_random

    def test_runtime_random_preview_reservation_is_released_after_generation_failure(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        node_id = "runtime-preview-retry-after-failure"
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": node_id,
                "selected": {"主体": ["成年女性"]},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "弱",
                    "随机主题池": "自动",
                    "seed": 123,
                },
            }
        )
        run_kwargs = dict(preview["settings"])
        run_kwargs.update(
            {
                "unique_id": node_id,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "自定义补充标签": ", ".join(preview["customTags"]),
                "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
            }
        )
        for group_name, slot_count, _options in module._all_tag_groups():
            for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                run_kwargs[f"{group_name}标签{index}"] = tag

        original_infer_style = module._infer_template_style
        module._infer_template_style = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("downstream failed"))
        try:
            with self.assertRaisesRegex(RuntimeError, "downstream failed"):
                module._run_stage(None, **run_kwargs)
        finally:
            module._infer_template_style = original_infer_style

        self.assertEqual(module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS, {})
        result = module._run_stage(None, **run_kwargs)
        self.assertTrue(json.loads(result[3])["runtime_random_preview_consumed"])
        self.assertEqual(module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS, {})

    def test_stage_cache_transaction_rolls_back_late_generation_failure(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        node_id = "runtime-preview-late-rollback"
        module._cache_output(
            node_id,
            {
                "status": "done",
                "prompt_text": "previous successful prompt",
                "recent_style_tracks": ["previous-style"],
                "recent_prompt_signatures": ["previous-signature"],
                "recent_runtime_markers": ["previous-marker"],
                "strict_prompt_dedupe": {"version": 3, "channels": {}},
            },
        )
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": node_id,
                "selected": {"主体": ["成年女性"]},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "弱",
                    "随机主题池": "商业摄影",
                    "seed": 123,
                },
            }
        )
        run_kwargs = dict(preview["settings"])
        run_kwargs.update(
            {
                "unique_id": node_id,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "自定义补充标签": ", ".join(preview["customTags"]),
                "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
            }
        )
        for group_name, slot_count, _options in module._all_tag_groups():
            for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                run_kwargs[f"{group_name}标签{index}"] = tag

        before_cache = deepcopy(module._CACHE)
        original_negative = module._build_negative_prompt
        module._build_negative_prompt = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("late generation failure")
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "late generation failure"):
                module._run_stage(None, **run_kwargs)
        finally:
            module._build_negative_prompt = original_negative

        self.assertEqual(module._CACHE, before_cache)
        self.assertEqual(module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS, {})
        retry = module._run_stage(None, **run_kwargs)
        self.assertTrue(json.loads(retry[3])["runtime_random_preview_consumed"])

    def test_failed_stage_transaction_does_not_evict_full_cache(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        for index in range(module._CACHE_NODE_LIMIT):
            module._cache_output(f"stable-cache-{index}", {"status": "done", "prompt_text": f"prompt-{index}"})
        before_cache = deepcopy(module._CACHE)
        node_id = "runtime-preview-full-cache-failure"
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": node_id,
                "selected": {"主体": ["成年女性"]},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "弱",
                    "随机主题池": "自动",
                    "seed": 123,
                },
            }
        )
        run_kwargs = dict(preview["settings"])
        run_kwargs.update(
            {
                "unique_id": node_id,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "自定义补充标签": ", ".join(preview["customTags"]),
                "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
            }
        )
        for group_name, slot_count, _options in module._all_tag_groups():
            for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                run_kwargs[f"{group_name}标签{index}"] = tag

        original_negative = module._build_negative_prompt
        module._build_negative_prompt = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("full cache failure")
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "full cache failure"):
                module._run_stage(None, **run_kwargs)
        finally:
            module._build_negative_prompt = original_negative

        self.assertEqual(module._CACHE, before_cache)
        self.assertNotIn(node_id, module._CACHE)
        self.assertEqual(module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS, {})

    def test_invalid_cache_namespace_cannot_reserve_preview_marker_or_write_legacy_bucket(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        node_id = "runtime-preview-invalid-cache"
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": node_id,
                "cache_namespace": "bad",
                "selected": {"主体": ["成年女性"]},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "弱",
                    "随机主题池": "自动",
                    "seed": 123,
                },
            }
        )
        self.assertEqual(preview["settings"]["cache_key"], "")
        selected = OrderedDict(
            (name, list(preview["selected"].get(name, [])))
            for name, _slots, _options in module._all_tag_groups()
        )
        self.assertIsNone(
            module._reserve_runtime_random_preview_marker(
                dict(preview["settings"]),
                selected,
                list(preview["customTags"]),
            )
        )

        run_kwargs = dict(preview["settings"])
        run_kwargs.update(
            {
                "unique_id": node_id,
                "cache_namespace": "bad",
                "模型来源": "仅Skill",
                "生成数量": 1,
                "自定义补充标签": ", ".join(preview["customTags"]),
                "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
            }
        )
        for group_name, slot_count, _options in module._all_tag_groups():
            for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                run_kwargs[f"{group_name}标签{index}"] = tag
        result = module._run_stage(None, **run_kwargs)
        self.assertFalse(json.loads(result[3])["runtime_random_preview_consumed"])
        self.assertEqual(module._CACHE, OrderedDict())
        self.assertEqual(module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS, {})

    def test_invalid_cache_namespace_does_not_read_legacy_node_history(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        node_id = "runtime-preview-invalid-history"
        module._cache_output(
            node_id,
            {
                "status": "done",
                "recent_style_tracks": ["legacy-style"],
                "recent_runtime_markers": ["variantcursor:商业摄影:4"],
            },
        )
        module._cache_output("history-order-sentinel", {"status": "done"})
        before_cache = deepcopy(module._CACHE)
        history_keys: list[str] = []
        original_history = module._random_history

        def observed_history(cache_key):
            history_keys.append(str(cache_key or ""))
            return original_history(cache_key)

        module._random_history = observed_history
        try:
            preview = module.构建运行时随机预览状态(
                {
                    "unique_id": node_id,
                    "cache_namespace": "bad",
                    "selected": {"主体": ["成年女性"]},
                    "customTags": [],
                    "settings": {
                        "模板风格": "真实感",
                        "主体类型": "人物角色",
                        "运行时随机标签": True,
                        "运行时随机模式": "全随机",
                        "运行时随机强度": "弱",
                        "随机主题池": "商业摄影",
                        "seed": 123,
                    },
                }
            )
            run_kwargs = dict(preview["settings"])
            run_kwargs.update(
                {
                    "unique_id": node_id,
                    "cache_namespace": "bad",
                    "模型来源": "仅Skill",
                    "生成数量": 1,
                    "自定义补充标签": ", ".join(preview["customTags"]),
                    "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
                }
            )
            for group_name, slot_count, _options in module._all_tag_groups():
                for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                    run_kwargs[f"{group_name}标签{index}"] = tag
            module._run_stage(None, **run_kwargs)
        finally:
            module._random_history = original_history

        self.assertNotIn(node_id, history_keys)
        self.assertEqual(module._CACHE, before_cache)

    def test_stage_cache_commit_fault_restores_bucket_token_and_lru(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        node_id = "runtime-preview-commit-fault"
        module._cache_output(node_id, {"status": "done", "prompt_text": "previous output"})
        module._cache_output("commit-fault-sentinel", {"status": "done"})
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": node_id,
                "selected": {"主体": ["成年女性"]},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "弱",
                    "随机主题池": "商业摄影",
                    "seed": 123,
                },
            }
        )
        run_kwargs = dict(preview["settings"])
        run_kwargs.update(
            {
                "unique_id": node_id,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "自定义补充标签": ", ".join(preview["customTags"]),
                "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
            }
        )
        for group_name, slot_count, _options in module._all_tag_groups():
            for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                run_kwargs[f"{group_name}标签{index}"] = tag

        before_cache = deepcopy(module._CACHE)
        original_prune = module._prune_stage_cache_unlocked
        module._prune_stage_cache_unlocked = lambda: (_ for _ in ()).throw(RuntimeError("commit prune failed"))
        try:
            with self.assertRaisesRegex(RuntimeError, "commit prune failed"):
                module._run_stage(None, **run_kwargs)
        finally:
            module._prune_stage_cache_unlocked = original_prune

        self.assertEqual(module._CACHE, before_cache)
        self.assertEqual(module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS, {})
        self.assertEqual(module._STAGE_CACHE_PINNED_KEYS, set())
        retry = module._run_stage(None, **run_kwargs)
        self.assertTrue(json.loads(retry[3])["runtime_random_preview_consumed"])

    def test_stage_cache_rollback_retries_cleanup_before_reraising_cancel(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        module._STAGE_CACHE_PINNED_KEYS.clear()
        key = "rollback-interrupted-cleanup"
        preview_transaction = module._RuntimeRandomPreviewTransaction()
        reservation = module._RuntimeRandomPreviewReservation(key, "token", {"token": "token"})
        preview_transaction.reservation = reservation
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS[(key, "token")] = reservation
        module._STAGE_CACHE_PINNED_KEYS.add(key)
        transaction = module._StageCacheTransaction()
        transaction.key = key
        transaction.bound = True
        transaction.lock = module._cache_key_lock(key)
        transaction.lock.acquire()
        transaction.owns_key_lock = True
        transaction.owns_pin = True
        original_cache_lock = module._CACHE_LOCK

        class InterruptOnceLock:
            def __init__(self, lock):
                self.lock = lock
                self.interrupted = False

            def acquire(self):
                if not self.interrupted:
                    self.interrupted = True
                    raise KeyboardInterrupt("cancel during rollback")
                return self.lock.acquire()

            def release(self):
                return self.lock.release()

        module._CACHE_LOCK = InterruptOnceLock(original_cache_lock)
        try:
            with self.assertRaisesRegex(KeyboardInterrupt, "cancel during rollback"):
                transaction.rollback(preview_transaction)
        finally:
            module._CACHE_LOCK = original_cache_lock

        self.assertTrue(transaction.closed)
        self.assertTrue(preview_transaction.closed)
        self.assertIsNone(preview_transaction.reservation)
        self.assertNotIn((key, "token"), module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS)
        self.assertNotIn(key, module._STAGE_CACHE_PINNED_KEYS)
        lock = module._cache_key_lock(key)
        self.assertTrue(lock.acquire(timeout=0.1))
        lock.release()

    def test_cancelled_waiting_stage_transaction_does_not_remove_owner_pin(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        key = "waiting-transaction-pin-owner"
        module._STAGE_CACHE_PINNED_KEYS.clear()
        module._STAGE_CACHE_PINNED_KEYS.add(key)
        original_key_lock = module._cache_key_lock

        class CancelledWaitLock:
            def acquire(self):
                raise KeyboardInterrupt("cancel while waiting for key lock")

            def release(self):
                raise AssertionError("unacquired lock must not be released")

        module._cache_key_lock = lambda _key: CancelledWaitLock()
        transaction = module._StageCacheTransaction()
        try:
            with self.assertRaisesRegex(KeyboardInterrupt, "cancel while waiting"):
                transaction.bind(key)
        finally:
            module._cache_key_lock = original_key_lock

        self.assertIn(key, module._STAGE_CACHE_PINNED_KEYS)
        self.assertFalse(transaction.owns_pin)
        self.assertFalse(transaction.owns_key_lock)
        module._STAGE_CACHE_PINNED_KEYS.clear()

    def test_same_stage_cache_key_serializes_success_and_failure_transactions(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        node_id = "runtime-preview-concurrent-stage-transactions"

        def build_run_kwargs():
            preview = module.构建运行时随机预览状态(
                {
                    "unique_id": node_id,
                    "selected": {"主体": ["成年女性"]},
                    "customTags": [],
                    "settings": {
                        "模板风格": "真实感",
                        "主体类型": "人物角色",
                        "运行时随机标签": True,
                        "运行时随机模式": "全随机",
                        "运行时随机强度": "弱",
                        "随机主题池": "商业摄影",
                        "seed": 123,
                    },
                }
            )
            kwargs = dict(preview["settings"])
            kwargs.update(
                {
                    "unique_id": node_id,
                    "模型来源": "仅Skill",
                    "生成数量": 1,
                    "自定义补充标签": ", ".join(preview["customTags"]),
                    "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
                }
            )
            for group_name, slot_count, _options in module._all_tag_groups():
                for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                    kwargs[f"{group_name}标签{index}"] = tag
            marker = module._parse_runtime_random_preview_marker(preview["settings"]["运行时随机预览令牌"])
            return kwargs, marker["token"]

        success_kwargs, success_token = build_run_kwargs()
        failure_kwargs, failure_token = build_run_kwargs()
        self.assertNotEqual(success_token, failure_token)
        barrier = threading.Barrier(2)
        results: list[tuple] = []
        errors: list[BaseException] = []
        result_lock = threading.Lock()
        original_negative = module._build_negative_prompt

        def guarded_negative(*args, **kwargs):
            if threading.current_thread().name == "stage-failure":
                raise RuntimeError("concurrent stage failure")
            return original_negative(*args, **kwargs)

        def worker(run_kwargs):
            try:
                barrier.wait(timeout=5)
                value = module._run_stage(None, **run_kwargs)
                with result_lock:
                    results.append(value)
            except BaseException as error:
                with result_lock:
                    errors.append(error)

        module._build_negative_prompt = guarded_negative
        success_thread = threading.Thread(target=worker, args=(success_kwargs,), name="stage-success")
        failure_thread = threading.Thread(target=worker, args=(failure_kwargs,), name="stage-failure")
        try:
            success_thread.start()
            failure_thread.start()
            success_thread.join(timeout=10)
            failure_thread.join(timeout=10)
        finally:
            module._build_negative_prompt = original_negative

        self.assertFalse(success_thread.is_alive())
        self.assertFalse(failure_thread.is_alive())
        self.assertEqual(len(results), 1)
        self.assertEqual({str(error) for error in errors}, {"concurrent stage failure"})
        self.assertEqual(module._CACHE[node_id]["prompt_text"], results[0][1])
        consumed = module._CACHE[node_id]["consumed_runtime_random_preview_tokens"]
        self.assertIn(success_token, consumed)
        self.assertNotIn(failure_token, consumed)
        self.assertEqual(module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS, {})

    def test_active_stage_cache_key_is_pinned_during_lru_pressure(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._cache_output("active-stage-cache", {"status": "done", "prompt_text": "stable"})
        transaction = module._StageCacheTransaction()
        previous_transaction = getattr(module._STAGE_CACHE_TRANSACTION_LOCAL, "current", None)
        module._STAGE_CACHE_TRANSACTION_LOCAL.current = transaction
        preview_transaction = module._RuntimeRandomPreviewTransaction()
        try:
            transaction.bind("active-stage-cache")
            for index in range(module._CACHE_NODE_LIMIT + 1):
                module._cache_output(f"lru-pressure-{index}", {"status": "done", "prompt_text": str(index)})
            with module._CACHE_LOCK:
                self.assertIn("active-stage-cache", module._CACHE)
                self.assertIn("active-stage-cache", module._STAGE_CACHE_PINNED_KEYS)
            transaction.rollback(preview_transaction)
        finally:
            if not transaction.closed:
                transaction.rollback(preview_transaction)
            if previous_transaction is None:
                try:
                    del module._STAGE_CACHE_TRANSACTION_LOCAL.current
                except AttributeError:
                    pass
            else:
                module._STAGE_CACHE_TRANSACTION_LOCAL.current = previous_transaction

        self.assertIn("active-stage-cache", module._CACHE)
        self.assertNotIn("active-stage-cache", module._STAGE_CACHE_PINNED_KEYS)
        self.assertLessEqual(len(module._CACHE), module._CACHE_NODE_LIMIT)

    def test_stage_cache_key_locks_are_reclaimed_after_churn(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE_KEY_LOCKS.clear()
        for index in range(module._CACHE_NODE_LIMIT * 4):
            lock = module._cache_key_lock(f"ephemeral-lock-{index}")
            with lock:
                pass
        del lock
        gc.collect()
        self.assertEqual(len(module._CACHE_KEY_LOCKS), 0)

    def test_runtime_random_preview_reservation_allows_only_one_concurrent_owner(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": "runtime-preview-concurrent-reservation",
                "selected": {"主体": ["成年女性"]},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "弱",
                    "随机主题池": "自动",
                    "seed": 123,
                },
            }
        )
        settings = dict(preview["settings"])
        selected = OrderedDict(
            (name, list(preview["selected"].get(name, [])))
            for name, _slots, _options in module._all_tag_groups()
        )
        custom_tags = list(preview["customTags"])
        worker_count = 12
        barrier = threading.Barrier(worker_count)
        result_lock = threading.Lock()
        reservations = []

        def worker() -> None:
            barrier.wait(timeout=5)
            reservation = module._reserve_runtime_random_preview_marker(settings, selected, custom_tags)
            with result_lock:
                reservations.append(reservation)

        threads = [threading.Thread(target=worker) for _ in range(worker_count)]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
            owners = [reservation for reservation in reservations if reservation is not None]
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(len(reservations), worker_count)
            self.assertEqual(len(owners), 1)
            self.assertIsNone(module._reserve_runtime_random_preview_marker(settings, selected, custom_tags))
            self.assertTrue(module._release_runtime_random_preview_reservation(owners[0]))
            retry = module._reserve_runtime_random_preview_marker(settings, selected, custom_tags)
            self.assertIsNotNone(retry)
            self.assertFalse(module._release_runtime_random_preview_reservation(owners[0]))
            self.assertIsNone(module._reserve_runtime_random_preview_marker(settings, selected, custom_tags))
            self.assertTrue(module._release_runtime_random_preview_reservation(retry))
        finally:
            module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()

        self.assertEqual(module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS, {})

    def test_runtime_random_preview_reservation_survives_cache_bucket_eviction(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        node_id = "runtime-preview-lru-reservation"
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": node_id,
                "selected": {"主体": ["成年女性"]},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "弱",
                    "随机主题池": "自动",
                    "seed": 123,
                },
            }
        )
        settings = dict(preview["settings"])
        selected = OrderedDict(
            (name, list(preview["selected"].get(name, [])))
            for name, _slots, _options in module._all_tag_groups()
        )
        reservation = module._reserve_runtime_random_preview_marker(settings, selected, list(preview["customTags"]))
        self.assertIsNotNone(reservation)
        try:
            with module._CACHE_LOCK:
                for index in range(module._CACHE_NODE_LIMIT + 1):
                    module._cache_bucket_unlocked(f"reservation-eviction-{index}", create=True)
                self.assertNotIn(node_id, module._CACHE)
                self.assertIs(
                    module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.get((node_id, reservation.token)),
                    reservation,
                )
            self.assertTrue(module._commit_runtime_random_preview_reservation(reservation))
            with module._CACHE_LOCK:
                consumed = module._CACHE[node_id]["consumed_runtime_random_preview_tokens"]
                self.assertIn(reservation.token, consumed)
                self.assertNotIn((node_id, reservation.token), module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS)
        finally:
            module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()

    def test_runtime_random_preview_marker_is_bound_to_node_and_workflow(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
        namespace_a = "runtime-preview-workflow-a"
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": "runtime-preview-origin-node",
                "cache_namespace": namespace_a,
                "selected": {"主体": ["成年女性"]},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "弱",
                    "随机主题池": "自动",
                    "seed": 123,
                },
            }
        )
        selected = OrderedDict(
            (name, list(preview["selected"].get(name, [])))
            for name, _slots, _options in module._all_tag_groups()
        )
        custom_tags = list(preview["customTags"])
        original_settings = dict(preview["settings"])
        original_reservation = module._reserve_runtime_random_preview_marker(
            original_settings,
            selected,
            custom_tags,
        )
        self.assertIsNotNone(original_reservation)
        self.assertTrue(module._release_runtime_random_preview_reservation(original_reservation))

        copied_node_settings = dict(original_settings)
        copied_node_settings["unique_id"] = "runtime-preview-copied-node"
        copied_node_settings["cache_key"] = f"stage:{namespace_a}"
        self.assertIsNone(
            module._reserve_runtime_random_preview_marker(copied_node_settings, selected, custom_tags)
        )

        copied_workflow_settings = dict(original_settings)
        copied_workflow_settings["cache_key"] = "stage:runtime-preview-workflow-b"
        self.assertIsNone(
            module._reserve_runtime_random_preview_marker(copied_workflow_settings, selected, custom_tags)
        )
        self.assertEqual(module._RUNTIME_RANDOM_PREVIEW_RESERVATIONS, {})

    def test_runtime_random_preview_marker_rejects_legacy_and_changed_state(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": "runtime-preview-bound-state",
                "selected": {"主体": ["成年女性"], "画面风格": ["真实感"]},
                "customTags": ["保留自定义"],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "中",
                    "随机主题池": "商业摄影",
                    "seed": 123,
                },
            }
        )
        marker_text = preview["settings"]["运行时随机预览令牌"]
        marker = module._parse_runtime_random_preview_marker(marker_text)
        self.assertIsNotNone(marker)
        self.assertEqual(len(marker["state_fingerprint"]), 64)
        self.assertIsNone(
            module._parse_runtime_random_preview_marker(
                json.dumps(
                    {"v": 1, "source": "ui", "token": "legacy-token", "mode": "全随机", "seed": 123},
                    ensure_ascii=False,
                )
            )
        )

        selected = OrderedDict((name, list(preview["selected"].get(name, []))) for name, _, _ in module._all_tag_groups())
        custom_tags = list(preview["customTags"])
        settings = dict(preview["settings"])
        self.assertIsNotNone(module._consume_runtime_random_preview_marker(settings, selected, custom_tags))

        for label, mutate in (
            ("selected", lambda next_selected, _custom, _settings: next_selected["主体"].append("成年男性")),
            ("custom", lambda _selected, next_custom, _settings: next_custom.append("状态已修改")),
            ("theme", lambda _selected, _custom, next_settings: next_settings.__setitem__("随机主题池", "动漫插画")),
            ("template", lambda _selected, _custom, next_settings: next_settings.__setitem__("模板风格", "CG感")),
        ):
            with self.subTest(label=label):
                module._CACHE.clear()
                next_selected = OrderedDict((name, list(tags)) for name, tags in selected.items())
                next_custom = list(custom_tags)
                next_settings = dict(settings)
                mutate(next_selected, next_custom, next_settings)
                self.assertIsNone(
                    module._consume_runtime_random_preview_marker(next_settings, next_selected, next_custom)
                )

    def test_runtime_random_preview_and_generation_keep_the_same_final_selection(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        node_id = "runtime-preview-selection-parity"
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": node_id,
                "selected": {"主体": ["成年女性"], "画面风格": ["真实感"]},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "中",
                    "随机主题池": "商业摄影",
                    "seed": 123,
                },
            }
        )
        run_kwargs = dict(preview["settings"])
        run_kwargs.update(
            {
                "unique_id": node_id,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "自定义补充标签": ", ".join(preview["customTags"]),
                "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
            }
        )
        for group_name, slot_count, _options in module._all_tag_groups():
            for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                run_kwargs[f"{group_name}标签{index}"] = tag
        result_payload = json.loads(module._run_stage(None, **run_kwargs)[3])
        preview_tags = set(collect_all_tags(OrderedDict(preview["selected"]), preview["customTags"]))
        self.assertEqual(set(result_payload["selected_tags_flat"]), preview_tags)

    def test_runtime_random_preview_marker_survives_adult_profile_normalization(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        node_id = "runtime-preview-adult-profile"
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": node_id,
                "selected": {"主体": ["成年女性"]},
                "customTags": [],
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "自动",
                    "标签反推模式": "成人向成熟",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "中",
                    "随机主题池": "自动",
                    "seed": 123,
                },
            }
        )
        self.assertEqual(preview["settings"]["主体类型"], "人物角色")
        run_kwargs = dict(preview["settings"])
        run_kwargs.update(
            {
                "unique_id": node_id,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "自定义补充标签": ", ".join(preview["customTags"]),
                "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
            }
        )
        for group_name, slot_count, _options in module._all_tag_groups():
            for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                run_kwargs[f"{group_name}标签{index}"] = tag
        payload = json.loads(module._run_stage(None, **run_kwargs)[3])
        self.assertTrue(payload["runtime_random_preview_consumed"])

    def test_runtime_random_preview_marker_survives_nsfw_allowed_filtering(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        node_id = "runtime-preview-nsfw-filtered"
        workspace = {
            "enabled": True,
            "preset": "——",
            "quality_tier": "标准",
            "negative_preset": "标准负面提示词",
            "random_mode": "关闭",
            "trigger_words": ["废弃教堂"],
            "scene": "酒店套房",
        }
        preview = module.构建运行时随机预览状态(
            {
                "unique_id": node_id,
                "selected": {},
                "customTags": [],
                "nsfwWorkspace": workspace,
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "自动",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "中",
                    "随机主题池": "自动",
                    "seed": 31,
                },
            }
        )
        preview_tags = set(collect_all_tags(OrderedDict(preview["selected"]), preview["customTags"]))
        self.assertIn("废弃教堂", preview_tags)
        self.assertNotIn("酒店套房", preview_tags)
        run_kwargs = dict(preview["settings"])
        run_kwargs.update(
            {
                "unique_id": node_id,
                "nsfw_workspace": workspace,
                "模型来源": "仅Skill",
                "生成数量": 1,
                "自定义补充标签": ", ".join(preview["customTags"]),
                "随机补充避重缓存": ", ".join(preview["_randomSupplementTags"]),
            }
        )
        for group_name, slot_count, _options in module._all_tag_groups():
            for index, tag in enumerate(preview["selected"].get(group_name, [])[:slot_count], start=1):
                run_kwargs[f"{group_name}标签{index}"] = tag
        payload = json.loads(module._run_stage(None, **run_kwargs)[3])
        self.assertTrue(payload["runtime_random_preview_consumed"])
        self.assertEqual(set(payload["selected_tags_flat"]), preview_tags)

    def test_runtime_random_preview_parser_rejects_non_numeric_version(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        self.assertIsNone(module._parse_runtime_random_preview_marker('{"v":"invalid"}'))
        self.assertIsNone(module._parse_runtime_random_preview_marker('{"v":{}}'))

    def test_stage_generator_smart_text_fallback_stays_pure_english(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module._run_stage(
            None,
            **{
                "unique_id": "smart-fallback-pure-english",
                "主体标签1": "成年女性",
                "画面风格标签1": "东方赛博机甲",
                "场景背景标签1": "霓虹街区",
                "智能文本匹配": True,
                "智能文本输入": "成年女性，东方赛博，霓虹街区，全景全身，高细节",
                "模板风格": "东方赛博",
                "提示词语言": "纯英文",
                "生成数量": 1,
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 123,
            },
        )
        smart_prompt = result[6]
        self.assertTrue(smart_prompt)
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in smart_prompt), smart_prompt)

    def test_runtime_random_legacy_ui_preview_marker_runs_full_backend_pipeline(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        node_id = "runtime-ui-preview-profile"
        marker = json.dumps(
            {"v": 1, "source": "ui", "token": "ui-preview-token", "mode": "全随机", "seed": 123},
            ensure_ascii=False,
        )
        calls: list[str] = []
        original_random = module._build_runtime_tags
        original_theme = module._apply_random_theme_pool_bias
        original_style = module._apply_template_style_profile_bias

        def random_stub(selected, custom_tags, settings):
            calls.append("random")
            return selected, custom_tags, []

        module._build_runtime_tags = random_stub

        def theme_stub(template_style, selected, custom_tags, settings):
            calls.append("theme")
            return template_style, selected, custom_tags

        def style_stub(template_style, selected, custom_tags, settings):
            calls.append("style")
            return selected, custom_tags

        module._apply_random_theme_pool_bias = theme_stub
        module._apply_template_style_profile_bias = style_stub
        try:
            module._run_stage(
                None,
                **{
                    "unique_id": node_id,
                    "主体标签1": "成年女性",
                    "模板风格": "真实感",
                    "随机主题池": "自动",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机预览令牌": marker,
                    "模型来源": "仅Skill",
                    "生成数量": 1,
                    "seed": 123,
                },
            )
        finally:
            module._build_runtime_tags = original_random
            module._apply_random_theme_pool_bias = original_theme
            module._apply_template_style_profile_bias = original_style
        self.assertEqual(calls, ["random", "theme", "style"])

    def test_runtime_random_ignores_stale_protected_tags_without_nsfw_workspace(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        captured: list[str] = []
        original_random = module._build_runtime_tags

        def random_stub(selected, custom_tags, settings):
            captured.append(str(settings.get("运行时随机保护标签", "")))
            return selected, custom_tags, []

        module._build_runtime_tags = random_stub
        try:
            module._run_stage(
                None,
                **{
                    "unique_id": "runtime-stale-protected",
                    "主体标签1": "成年女性",
                    "模板风格": "真实感",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机保护标签": "女仆, 豪华卧室",
                    "模型来源": "仅Skill",
                    "生成数量": 1,
                    "seed": 123,
                },
            )
        finally:
            module._build_runtime_tags = original_random
        self.assertEqual(captured, [""])

    def test_runtime_random_preview_preserves_enabled_nsfw_workspace_after_normalization(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        workspace = {
            "enabled": True,
            "preset": "——",
            "quality_tier": "高质量",
            "random_mode": "关闭",
            "trigger_words": ["女仆"],
            "scene": "豪华卧室",
            "action": "接吻",
            "outfit": "透明睡袍",
            "negative_preset": "标准负面提示词",
        }
        result = module.构建运行时随机预览状态(
            {
                "unique_id": "runtime-preview-nsfw",
                "selected": {},
                "customTags": [],
                "nsfwWorkspace": workspace,
                "settings": {
                    "模板风格": "真实感",
                    "主体类型": "人物角色",
                    "运行时随机标签": True,
                    "运行时随机模式": "全随机",
                    "运行时随机强度": "强",
                    "随机主题池": "自动",
                    "seed": 19,
                },
            }
        )
        active = set(collect_all_tags(OrderedDict(result["selected"]), result["customTags"]))
        self.assertTrue({"女仆", "豪华卧室", "接吻"}.issubset(active), active)
        self.assertNotIn("透明睡袍", active)
        self.assertTrue(result["nsfwWorkspace"]["enabled"])
        protected = set(module._parse_tags(result["settings"]["运行时随机保护标签"]))
        self.assertTrue({"女仆", "豪华卧室", "接吻"}.issubset(protected))
        self.assertNotIn("透明睡袍", protected)
        self.assertTrue(protected.issubset(active))

    def test_disabled_nsfw_workspace_is_bounded_before_preview_and_output_caching(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        workspace = {
            "enabled": False,
            "trigger_words": [f"tag-{index}-" + ("x" * 1_000) for index in range(300)],
            "custom_negative": "negative " * 20_000,
            "unknown_payload": {"nested": "z" * 200_000},
        }

        resolved, source = module._resolve_nsfw_workspace_payload(
            {"nsfw_workspace": workspace},
            {},
        )
        self.assertEqual(source, "直接输入")
        self.assertIsNotNone(resolved)
        self.assertNotIn("unknown_payload", resolved)
        self.assertLessEqual(nsfw_mapper._workspace_json_size(resolved), nsfw_mapper._WORKSPACE_MAX_JSON_BYTES)

        preview = module.构建运行时随机预览状态(
            {
                "unique_id": "runtime-preview-disabled-nsfw-bounds",
                "selected": {},
                "customTags": [],
                "nsfwWorkspace": workspace,
                "settings": {
                    "运行时随机标签": False,
                    "随机主题池": "自动",
                    "seed": 19,
                },
            }
        )
        self.assertFalse(preview["nsfwWorkspace"]["enabled"])
        self.assertNotIn("unknown_payload", preview["nsfwWorkspace"])
        self.assertLessEqual(
            nsfw_mapper._workspace_json_size(preview["nsfwWorkspace"]),
            nsfw_mapper._WORKSPACE_MAX_JSON_BYTES,
        )

    def test_nsfw_preset_fills_empty_fields_without_overwriting_manual_values(self) -> None:
        workspace = {
            "preset": "经典情色",
            "quality_tier": "高质量",
            "negative_preset": "标准负面提示词",
            "random_mode": "关闭",
            "scene": "手工保留场景",
            "action": "——",
            "outfit": "手工保留服装",
            "mood": "——",
        }
        effective = nsfw_mapper._resolve_effective_workspace(workspace)
        self.assertEqual(effective["scene"], "手工保留场景")
        self.assertEqual(effective["outfit"], "手工保留服装")
        self.assertEqual(effective["action"], nsfw_presets.NSFW_WORKSPACE_PRESETS["经典情色"]["action"])
        self.assertEqual(effective["mood"], nsfw_presets.NSFW_WORKSPACE_PRESETS["经典情色"]["mood"])

    def test_nsfw_preset_expands_all_supported_fields_with_manual_priority(self) -> None:
        workspace = {
            "preset": "高强度成人氛围",
            "quality_tier": "高质量",
            "negative_preset": "标准负面提示词",
            "random_mode": "关闭",
            "scene": "手工场景",
            "visual_style": "手工视觉风格",
        }
        effective = nsfw_mapper._resolve_effective_workspace(workspace)
        preset = nsfw_presets.NSFW_WORKSPACE_PRESETS["高强度成人氛围"]
        self.assertEqual(effective["scene"], "手工场景")
        self.assertEqual(effective["visual_style"], "手工视觉风格")
        for field in ("anatomy_terms", "explicit_terms", "adult_action_style", "camera_angle", "light_source", "light_type", "lens_type", "effect", "filter"):
            self.assertEqual(effective[field], preset[field])

    def test_retro_animation_ova_profile_keeps_registered_low_fidelity_tag(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        result = module._run_stage(
            None,
            **{
                "unique_id": "retro-animation-low-fidelity",
                "主体标签1": "成年女性",
                "模板风格": "复古动画",
                "随机主题池": "自动",
                "生成数量": 1,
                "提示词语言": "纯中文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 0,
            },
        )
        payload = json.loads(result[3])
        self.assertIn("低保真", payload["selected_tags_flat"])
        self.assertIn("低保真", result[1])
        self.assertFalse(any("低保真" in note and "移除" in note for note in payload["normalization_notes"]))

    def test_nsfw_random_nonce_is_deterministic_and_rotates_backend_selection(self) -> None:
        original_scene_options = nsfw_mapper.NSFW_WORKSPACE_OPTIONS["scene"]
        nsfw_mapper.NSFW_WORKSPACE_OPTIONS["scene"] = ["——", "甲", "乙", "丙", "丁"]
        workspace = {
            "preset": "——",
            "quality_tier": "高质量",
            "negative_preset": "标准负面提示词",
            "random_mode": "场景随机",
            "trigger_words": ["护士", "女仆", "护士"],
            "random_nonce": "nonce-1",
        }
        try:
            first = nsfw_mapper._resolve_effective_workspace(workspace)["scene"]
            second = nsfw_mapper._resolve_effective_workspace(dict(workspace))["scene"]
            rotated = {
                nsfw_mapper._resolve_effective_workspace({**workspace, "random_nonce": f"nonce-{index}"})["scene"]
                for index in range(12)
            }
        finally:
            nsfw_mapper.NSFW_WORKSPACE_OPTIONS["scene"] = original_scene_options

        self.assertEqual(first, "丁")
        self.assertEqual(second, first)
        self.assertGreater(len(rotated), 1)
        self.assertEqual(nsfw_presets.build_nsfw_workspace_defaults()["random_nonce"], "")

    def test_nsfw_workspace_is_recovered_from_matching_workflow_node_properties(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        workspace = {
            "enabled": True,
            "preset": "——",
            "quality_tier": "高质量",
            "random_mode": "关闭",
            "trigger_words": ["女仆"],
            "negative_preset": "自定义负面提示词",
            "negative_apply_mode": "override",
            "custom_negative": "nsfw custom negative",
        }
        extra_pnginfo = {
            "workflow": {
                "nodes": [
                    {"id": 17, "properties": {"nsfw_workspace": {"enabled": False}}},
                    {"id": 42, "properties": {"nsfw_workspace": workspace}},
                ]
            }
        }
        self.assertEqual(
            module._extract_nsfw_workspace_from_extra_pnginfo(extra_pnginfo, "42"),
            workspace,
        )
        self.assertIsNone(module._extract_nsfw_workspace_from_extra_pnginfo(extra_pnginfo, "99"))

        result = module._run_stage(
            None,
            **{
                "unique_id": "42",
                "extra_pnginfo": extra_pnginfo,
                "模板风格": "真实感",
                "主体类型": "人物角色",
                "生成数量": 1,
                "提示词语言": "纯中文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 123,
            },
        )
        payload = json.loads(result[3])
        self.assertEqual(payload["nsfw_workspace_source"], "工作流元数据")
        self.assertEqual(payload["nsfw_workspace"]["custom_negative"], "nsfw custom negative")
        self.assertIn("女仆", payload["selected_tags_flat"])
        self.assertEqual(result[4], "nsfw custom negative")

    def test_direct_nsfw_workspace_takes_precedence_over_workflow_metadata(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        direct = {"enabled": True, "trigger_words": ["护士"]}
        metadata = {
            "workflow": {
                "nodes": [
                    {"id": 7, "properties": {"nsfwWorkspace": {"enabled": True, "trigger_words": ["女仆"]}}}
                ]
            }
        }
        resolved, source = module._resolve_nsfw_workspace_payload(
            {"nsfw_workspace": direct, "extra_pnginfo": metadata},
            {"unique_id": "7", "extra_pnginfo": metadata},
        )
        self.assertEqual(resolved, direct)
        self.assertEqual(source, "直接输入")

    def test_normalizer_runs_every_skill_phase_once_for_non_person_subjects(self) -> None:
        phases: list[str] = []
        original_apply_skills = normalizer.apply_stage_prompt_skills

        def record_phase(*args, **kwargs) -> None:
            phases.append(str(kwargs.get("phase", "")))

        normalizer.apply_stage_prompt_skills = record_phase
        try:
            normalizer.normalize_inference_state(
                OrderedDict({"主体": ["机械城市"], "画面风格": ["CG感"], "构图视角": []}),
                [],
                {
                    "模板风格": "CG感",
                    "标签反推模式": "自动平衡",
                    "主体类型": "非人物主体",
                    "随机主题池": "自动",
                },
                collect_all_tags=collect_all_tags,
                remove_tag_from_state=remove_tag_from_state,
                append_tag_to_state=append_tag_to_state,
                uniq=uniq,
                context={},
            )
        finally:
            normalizer.apply_stage_prompt_skills = original_apply_skills

        self.assertEqual(phases, ["early_normalize", "mid_normalize", "final_normalize"])

    def test_randomizer_rewrite_subject_scene_keeps_empty_non_target_groups_empty(self) -> None:
        settings = {
            "运行时随机模式": "重写主体与场景",
            "运行时随机强度": "强",
            "核心标签锁定数量": 0,
            "seed": 7,
            "unique_id": "rewrite-budget",
            "锁定标签白名单": "",
            "随机排除标签": "",
            "随机补充避重缓存": "",
            "随机主题池": "自动",
        }
        next_selected, next_custom, generated = randomizer.build_runtime_tags(
            OrderedDict(
                {
                    "主体": ["旧主体"],
                    "场景背景": ["旧场景"],
                    "画面风格": [],
                    "光影氛围": [],
                    "构图视角": [],
                }
            ),
            [],
            settings,
            all_tag_groups=lambda: [
                ("主体", 1, ["无", "旧主体", "新主体"]),
                ("场景背景", 1, ["无", "旧场景", "新场景"]),
                ("画面风格", 1, ["无", "真实感"]),
                ("光影氛围", 1, ["无", "柔光"]),
                ("构图视角", 1, ["无", "全景全身"]),
            ],
            tag_group_index=lambda: {
                "旧主体": "主体",
                "新主体": "主体",
                "旧场景": "场景背景",
                "新场景": "场景背景",
                "真实感": "画面风格",
                "柔光": "光影氛围",
                "全景全身": "构图视角",
            },
            parse_tags=lambda text: [item.strip() for item in str(text).split(",") if item.strip()],
            uniq=uniq,
            seed_normalizer=lambda seed: int(seed),
            history_loader=lambda _node_id: [],
            random_module=random,
            empty_tag="无",
        )

        self.assertEqual(next_selected["主体"], ["新主体"])
        self.assertEqual(next_selected["场景背景"], ["新场景"])
        self.assertEqual(next_selected["画面风格"], [])
        self.assertEqual(next_selected["光影氛围"], [])
        self.assertEqual(next_selected["构图视角"], [])
        self.assertEqual(next_custom, [])
        self.assertEqual(set(generated), {"新主体", "新场景"})

    def test_image_reverse_cache_reuses_identical_requests_and_separates_modes(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        with module._IMAGE_REVERSE_CACHE_LOCK:
            module._IMAGE_REVERSE_CACHE.clear()
            module._IMAGE_REVERSE_INFLIGHT.clear()

        class DummyLlm:
            model_path = "dummy-vision.gguf"

        class DummyModel:
            llm = DummyLlm()

        calls: list[str] = []
        deadlines: list[float] = []
        original_converter = module._批量帧索引转data_url
        original_chat = module._调用chat_completion
        module._批量帧索引转data_url = lambda image, indices, max_edge: {0: "data:image/png;base64,cache-test"}

        def fake_chat(llm, *, messages, params):
            calls.append(messages[1]["content"][0]["text"])
            deadlines.append(float(params[module._MODEL_CALL_DEADLINE_PARAM]))
            return {"choices": [{"message": {"content": "银发角色，黑色礼服，全景全身"}}]}

        module._调用chat_completion = fake_chat
        base_settings = {
            "图片反推模式": "角色设定图",
            "图片反推最大边长": 960,
            "温度": 0.62,
            "top_p": 0.9,
            "top_k": 40,
            "重复惩罚": 1.08,
            "频率惩罚": 0.0,
            "存在惩罚": 0.0,
            "seed": 123,
            "内置主模型": "dummy-vision.gguf",
        }
        try:
            first_settings = dict(base_settings)
            second_settings = dict(base_settings)
            alternate_settings = {**base_settings, "图片反推模式": "仅反推描述"}
            first = module._reverse_reference_image(DummyModel(), object(), first_settings)
            second = module._reverse_reference_image(DummyModel(), object(), second_settings)
            alternate = module._reverse_reference_image(DummyModel(), object(), alternate_settings)
        finally:
            module._批量帧索引转data_url = original_converter
            module._调用chat_completion = original_chat
            with module._IMAGE_REVERSE_CACHE_LOCK:
                module._IMAGE_REVERSE_CACHE.clear()
                module._IMAGE_REVERSE_INFLIGHT.clear()

        self.assertEqual(first, second)
        self.assertEqual(alternate, first)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(deadlines), 2)
        self.assertTrue(all(deadline > 0.0 for deadline in deadlines))
        self.assertFalse(first_settings["图片反推缓存命中"])
        self.assertTrue(second_settings["图片反推缓存命中"])
        self.assertFalse(alternate_settings["图片反推缓存命中"])

    def test_image_reverse_singleflight_calls_model_once_for_eight_identical_threads(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        with module._IMAGE_REVERSE_CACHE_LOCK:
            module._IMAGE_REVERSE_CACHE.clear()
            module._IMAGE_REVERSE_INFLIGHT.clear()

        class DummyLlm:
            model_path = "singleflight-vision.gguf"

        class DummyModel:
            llm = DummyLlm()

        worker_count = 8
        barrier = threading.Barrier(worker_count)
        result_lock = threading.Lock()
        arrival_lock = threading.Lock()
        all_registered = threading.Event()
        model_calls = 0
        registered = 0
        results: list[str] = []
        cache_hits: list[bool] = []
        errors: list[Exception] = []
        original_converter = module._批量帧索引转data_url
        original_chat = module._调用chat_completion
        original_begin = module._begin_image_reverse_singleflight
        module._批量帧索引转data_url = lambda image, indices, max_edge: {0: "data:image/png;base64,singleflight"}

        def observed_begin(cache_key, **kwargs):
            nonlocal registered
            outcome = original_begin(cache_key, **kwargs)
            with arrival_lock:
                registered += 1
                if registered >= worker_count:
                    all_registered.set()
            return outcome

        def fake_chat(llm, *, messages, params):
            nonlocal model_calls
            with result_lock:
                model_calls += 1
            all_registered.wait(timeout=5)
            return {"choices": [{"message": {"content": "singleflight reverse result"}}]}

        def worker() -> None:
            settings = {"图片反推模式": "角色设定图", "图片反推最大边长": 960, "seed": 123}
            try:
                barrier.wait(timeout=5)
                value = module._reverse_reference_image(DummyModel(), object(), settings)
                with result_lock:
                    results.append(value)
                    cache_hits.append(bool(settings.get("图片反推缓存命中", False)))
            except Exception as exc:  # pragma: no cover - asserted below
                with result_lock:
                    errors.append(exc)

        module._begin_image_reverse_singleflight = observed_begin
        module._调用chat_completion = fake_chat
        threads = [threading.Thread(target=worker) for _ in range(worker_count)]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            with module._IMAGE_REVERSE_CACHE_LOCK:
                inflight_count = len(module._IMAGE_REVERSE_INFLIGHT)
        finally:
            module._批量帧索引转data_url = original_converter
            module._调用chat_completion = original_chat
            module._begin_image_reverse_singleflight = original_begin
            with module._IMAGE_REVERSE_CACHE_LOCK:
                module._IMAGE_REVERSE_CACHE.clear()
                module._IMAGE_REVERSE_INFLIGHT.clear()

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(model_calls, 1)
        self.assertEqual(results, ["singleflight reverse result"] * worker_count)
        self.assertEqual(cache_hits.count(False), 1)
        self.assertEqual(cache_hits.count(True), worker_count - 1)
        self.assertEqual(inflight_count, 0)

    def test_image_reverse_singleflight_failure_is_shared_and_next_call_retries(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        with module._IMAGE_REVERSE_CACHE_LOCK:
            module._IMAGE_REVERSE_CACHE.clear()
            module._IMAGE_REVERSE_INFLIGHT.clear()

        class DummyLlm:
            model_path = "singleflight-retry-vision.gguf"

        class DummyModel:
            llm = DummyLlm()

        worker_count = 8
        barrier = threading.Barrier(worker_count)
        state_lock = threading.Lock()
        arrival_lock = threading.Lock()
        all_registered = threading.Event()
        model_calls = 0
        registered = 0
        errors: list[Exception] = []
        original_converter = module._批量帧索引转data_url
        original_chat = module._调用chat_completion
        original_begin = module._begin_image_reverse_singleflight
        module._批量帧索引转data_url = lambda image, indices, max_edge: {0: "data:image/png;base64,singleflight-retry"}

        def observed_begin(cache_key, **kwargs):
            nonlocal registered
            outcome = original_begin(cache_key, **kwargs)
            with arrival_lock:
                registered += 1
                if registered >= worker_count:
                    all_registered.set()
            return outcome

        def fake_chat(llm, *, messages, params):
            nonlocal model_calls
            with state_lock:
                model_calls += 1
                call_number = model_calls
            if call_number == 1:
                all_registered.wait(timeout=5)
                raise RuntimeError("shared singleflight failure")
            return {"choices": [{"message": {"content": "retry succeeded"}}]}

        def worker() -> None:
            try:
                barrier.wait(timeout=5)
                module._reverse_reference_image(
                    DummyModel(),
                    object(),
                    {"图片反推模式": "角色设定图", "图片反推最大边长": 960, "seed": 123},
                )
            except Exception as exc:
                with state_lock:
                    errors.append(exc)

        module._begin_image_reverse_singleflight = observed_begin
        module._调用chat_completion = fake_chat
        threads = [threading.Thread(target=worker) for _ in range(worker_count)]
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
            with module._IMAGE_REVERSE_CACHE_LOCK:
                inflight_after_failure = len(module._IMAGE_REVERSE_INFLIGHT)
            module._begin_image_reverse_singleflight = original_begin
            retry_settings = {"图片反推模式": "角色设定图", "图片反推最大边长": 960, "seed": 123}
            retry_result = module._reverse_reference_image(DummyModel(), object(), retry_settings)
            cached_settings = {"图片反推模式": "角色设定图", "图片反推最大边长": 960, "seed": 123}
            cached_result = module._reverse_reference_image(DummyModel(), object(), cached_settings)
            with module._IMAGE_REVERSE_CACHE_LOCK:
                inflight_after_retry = len(module._IMAGE_REVERSE_INFLIGHT)
        finally:
            module._批量帧索引转data_url = original_converter
            module._调用chat_completion = original_chat
            module._begin_image_reverse_singleflight = original_begin
            with module._IMAGE_REVERSE_CACHE_LOCK:
                module._IMAGE_REVERSE_CACHE.clear()
                module._IMAGE_REVERSE_INFLIGHT.clear()

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(errors), worker_count)
        self.assertEqual({str(exc) for exc in errors}, {"shared singleflight failure"})
        self.assertEqual(len({id(exc) for exc in errors}), 1)
        self.assertEqual(inflight_after_failure, 0)
        self.assertEqual(retry_result, "retry succeeded")
        self.assertFalse(retry_settings["图片反推缓存命中"])
        self.assertEqual(cached_result, retry_result)
        self.assertTrue(cached_settings["图片反推缓存命中"])
        self.assertEqual(model_calls, 2)
        self.assertEqual(inflight_after_retry, 0)

    def test_image_reverse_singleflight_capacity_wait_is_bounded(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        original_limit = module._IMAGE_REVERSE_INFLIGHT_LIMIT
        module._IMAGE_REVERSE_INFLIGHT_LIMIT = 2
        with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
            module._IMAGE_REVERSE_CACHE.clear()
            module._IMAGE_REVERSE_INFLIGHT.clear()
            module._IMAGE_REVERSE_INFLIGHT["occupied-a"] = module._ImageReverseInFlight()
            module._IMAGE_REVERSE_INFLIGHT["occupied-b"] = module._ImageReverseInFlight()

        started_at = module.time.monotonic()
        try:
            with self.assertRaisesRegex(TimeoutError, "等待可用执行槽位超时"):
                module._begin_image_reverse_singleflight(
                    "waiting-for-slot",
                    wait_timeout=0.03,
                    stale_after=10.0,
                )
            elapsed = module.time.monotonic() - started_at
        finally:
            module._IMAGE_REVERSE_INFLIGHT_LIMIT = original_limit
            with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
                module._IMAGE_REVERSE_CACHE.clear()
                module._IMAGE_REVERSE_INFLIGHT.clear()
                module._IMAGE_REVERSE_INFLIGHT_CONDITION.notify_all()

        self.assertLess(elapsed, 0.5)

    def test_image_reverse_capacity_rejects_new_key_when_leader_is_stale(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        stale_flight = module._ImageReverseInFlight()
        stale_flight.started_at = module.time.monotonic() - 10.0
        with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
            module._IMAGE_REVERSE_CACHE.clear()
            module._IMAGE_REVERSE_INFLIGHT.clear()
            module._IMAGE_REVERSE_INFLIGHT["stale-capacity-leader"] = stale_flight

        started_at = module.time.monotonic()
        try:
            with self.assertRaisesRegex(TimeoutError, "已拒绝新的反推任务"):
                module._begin_image_reverse_singleflight(
                    "different-image-key",
                    wait_timeout=2.0,
                    stale_after=0.01,
                )
            elapsed = module.time.monotonic() - started_at
            with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
                self.assertIs(
                    module._IMAGE_REVERSE_INFLIGHT.get("stale-capacity-leader"),
                    stale_flight,
                )
                self.assertEqual(len(module._IMAGE_REVERSE_INFLIGHT), 1)
        finally:
            with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
                module._IMAGE_REVERSE_CACHE.clear()
                module._IMAGE_REVERSE_INFLIGHT.clear()
                module._IMAGE_REVERSE_INFLIGHT_CONDITION.notify_all()

        self.assertLess(elapsed, 0.5)

    def test_image_reverse_singleflight_follower_wait_is_bounded(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        cache_key = "bounded-follower"
        flight = module._ImageReverseInFlight()
        with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
            module._IMAGE_REVERSE_CACHE.clear()
            module._IMAGE_REVERSE_INFLIGHT.clear()
            module._IMAGE_REVERSE_INFLIGHT[cache_key] = flight

        started_at = module.time.monotonic()
        try:
            with self.assertRaisesRegex(TimeoutError, "等待已有任务完成超时"):
                module._wait_image_reverse_singleflight(
                    cache_key,
                    flight,
                    wait_timeout=0.03,
                    stale_after=10.0,
                )
            elapsed = module.time.monotonic() - started_at
            with module._IMAGE_REVERSE_CACHE_LOCK:
                still_active = module._IMAGE_REVERSE_INFLIGHT.get(cache_key) is flight
        finally:
            module._finish_image_reverse_singleflight(cache_key, flight)
            with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
                module._IMAGE_REVERSE_CACHE.clear()
                module._IMAGE_REVERSE_INFLIGHT.clear()
                module._IMAGE_REVERSE_INFLIGHT_CONDITION.notify_all()

        self.assertLess(elapsed, 0.5)
        self.assertTrue(still_active)

    def test_image_reverse_singleflight_old_follower_uses_remaining_stale_budget(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        cache_key = "near-stale-follower"
        flight = module._ImageReverseInFlight()
        stale_after = 0.08
        flight.started_at = module.time.monotonic() - 0.06
        with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
            module._IMAGE_REVERSE_CACHE.clear()
            module._IMAGE_REVERSE_INFLIGHT.clear()
            module._IMAGE_REVERSE_INFLIGHT[cache_key] = flight

        started_at = module.time.monotonic()
        try:
            with self.assertRaisesRegex(TimeoutError, "等待已有任务完成超时"):
                module._wait_image_reverse_singleflight(
                    cache_key,
                    flight,
                    wait_timeout=2.0,
                    stale_after=stale_after,
                )
            elapsed = module.time.monotonic() - started_at
            with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
                still_active = module._IMAGE_REVERSE_INFLIGHT.get(cache_key) is flight
                event_set = flight.event.is_set()
                error = flight.error
        finally:
            with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
                module._IMAGE_REVERSE_CACHE.clear()
                module._IMAGE_REVERSE_INFLIGHT.clear()
                module._IMAGE_REVERSE_INFLIGHT_CONDITION.notify_all()

        self.assertLess(elapsed, 0.5)
        self.assertTrue(still_active)
        self.assertFalse(event_set)
        self.assertIsNone(error)

    def test_image_reverse_singleflight_keeps_stale_leader_until_authoritative_finish(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        cache_key = "stale-image-reverse"
        stale_flight = module._ImageReverseInFlight()
        stale_flight.started_at = module.time.monotonic() - 10.0
        with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
            module._IMAGE_REVERSE_CACHE.clear()
            module._IMAGE_REVERSE_INFLIGHT.clear()
            module._IMAGE_REVERSE_INFLIGHT[cache_key] = stale_flight

        try:
            mode, cached, fresh_flight = module._begin_image_reverse_singleflight(
                cache_key,
                wait_timeout=0.1,
                stale_after=0.01,
            )
            self.assertEqual(mode, "wait")
            self.assertIsNone(cached)
            self.assertIs(fresh_flight, stale_flight)
            self.assertFalse(stale_flight.event.is_set())
            self.assertIsNone(stale_flight.error)

            with self.assertRaisesRegex(TimeoutError, "等待已有任务完成超时"):
                module._wait_image_reverse_singleflight(
                    cache_key,
                    stale_flight,
                    wait_timeout=0.1,
                    stale_after=0.01,
                )
            with module._IMAGE_REVERSE_CACHE_LOCK:
                self.assertIs(module._IMAGE_REVERSE_INFLIGHT.get(cache_key), stale_flight)
                self.assertNotIn(cache_key, module._IMAGE_REVERSE_CACHE)

            module._finish_image_reverse_singleflight(cache_key, stale_flight, result="late stale result")
            with module._IMAGE_REVERSE_CACHE_LOCK:
                self.assertEqual(module._IMAGE_REVERSE_CACHE.get(cache_key), "late stale result")
                self.assertNotIn(cache_key, module._IMAGE_REVERSE_INFLIGHT)

            mode, cached, next_flight = module._begin_image_reverse_singleflight(cache_key)
            self.assertEqual(mode, "cached")
            self.assertEqual(cached, "late stale result")
            self.assertIsNone(next_flight)
        finally:
            with module._IMAGE_REVERSE_INFLIGHT_CONDITION:
                module._IMAGE_REVERSE_CACHE.clear()
                module._IMAGE_REVERSE_INFLIGHT.clear()
                module._IMAGE_REVERSE_INFLIGHT_CONDITION.notify_all()

    def test_image_reverse_cache_is_bounded(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        with module._IMAGE_REVERSE_CACHE_LOCK:
            module._IMAGE_REVERSE_CACHE.clear()
        try:
            for index in range(module._IMAGE_REVERSE_CACHE_LIMIT + 5):
                module._cache_image_reverse(f"cache-key-{index}", f"value-{index}")
            with module._IMAGE_REVERSE_CACHE_LOCK:
                self.assertEqual(len(module._IMAGE_REVERSE_CACHE), module._IMAGE_REVERSE_CACHE_LIMIT)
                self.assertNotIn("cache-key-0", module._IMAGE_REVERSE_CACHE)
                self.assertIn(f"cache-key-{module._IMAGE_REVERSE_CACHE_LIMIT + 4}", module._IMAGE_REVERSE_CACHE)
        finally:
            with module._IMAGE_REVERSE_CACHE_LOCK:
                module._IMAGE_REVERSE_CACHE.clear()


    def test_batch_model_prompt_uses_the_same_active_mode_contract_as_single_prompt(self) -> None:
        settings = {
            "提示词语言": "纯中文",
            "模型来源": "API接口",
            "运行时随机标签": True,
            "智能文本匹配": True,
            "标签块编排启用": True,
            "图片反推生成": True,
            "图片反推状态": "调用成功",
            "角色设定图内部策略": "保持同一角色的多视角一致性",
            "NSFW工作台启用": True,
            "NSFW策略启用": True,
            "NSFW工作台标签摘要": "成年主体、柔光、豪华卧室",
            "标签块编排摘要": "主体 -> 场景 -> 光影",
            "模板风格档案标记": ["stylevariant:古风:film"],
            "随机主题池档案标记": ["theme:雨夜"],
            "运行时随机档案标记": ["visual:scene:雨夜"],
        }
        batch_prompt = model_refiner._compose_batch_prompt(
            ["第一条基础提示词", "第二条基础提示词"],
            settings,
        )
        self.assertIn("Skill前置上下文", batch_prompt)
        self.assertIn("当前激活模式", batch_prompt)
        for label in ("运行时随机", "智能文本", "标签块编排", "角色设定图", "图片反推", "NSFW工作台"):
            self.assertIn(label, batch_prompt)
        self.assertIn("模式合并优先级", batch_prompt)
        self.assertIn("stylevariant:古风:film", batch_prompt)
        self.assertIn("NSFW 工作台素材", batch_prompt)
        self.assertIn("标签块编排顺序", batch_prompt)

    def test_strict_dedupe_uses_non_person_variation_without_human_pollution(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        base = "巨型轨道采矿机，工业废墟，硬表面金属，体积光，高细节"
        settings = {
            "提示词语言": "纯中文",
            "主体类型解析结果": "非人物主体",
            "连续生成避重缓存": "",
        }
        first = module._strict_dedupe_prompt_list("strict-non-person-mode", [base], settings)[0]
        second = module._strict_dedupe_prompt_list("strict-non-person-mode", [base], settings)[0]
        self.assertEqual(first, base)
        self.assertIn("功能部件", second)
        for forbidden in ("腿部", "手部动作", "发丝", "衣摆", "服装褶皱"):
            self.assertNotIn(forbidden, second)

    def test_strict_dedupe_respects_character_sheet_tag_block_and_nsfw_modes(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        character = module._append_strict_variation_clause(
            "角色设定图，成年女性，正面视图，侧面视图，背面视图",
            0,
            {"提示词语言": "纯中文", "角色设定图内部策略": "保持多视角一致"},
        )
        blocks = module._append_strict_variation_clause(
            "主体块，场景块，光影块",
            0,
            {"提示词语言": "纯中文", "标签块编排启用": True},
        )
        nsfw = module._append_strict_variation_clause(
            "成年女性，豪华卧室，柔光，成熟写真",
            0,
            {"提示词语言": "纯中文", "NSFW工作台启用": True},
        )
        self.assertIn("多视角设定图结构", character)
        self.assertIn("锁定块", blocks)
        self.assertIn("成年主体", nsfw)
        self.assertNotIn("整理衣领或发丝", nsfw)

    def test_recent_variation_cue_uses_active_mode_profile(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        non_person = module._recent_prompt_variation_cue(
            {"提示词语言": "纯中文", "主体类型解析结果": "非人物主体"},
            0,
            4,
        )
        character = module._recent_prompt_variation_cue(
            {"提示词语言": "纯英文", "角色设定图内部策略": "multi-view"},
            1,
            4,
        )
        self.assertIn("功能部件", non_person)
        self.assertNotIn("身体", non_person)
        self.assertIn("multi-view", character)

    def test_danbooru_general_visual_tags_are_registered_with_english_aliases(self) -> None:
        frontend = tag_library.前端标签库数据()
        metadata = frontend["danbooru_general_tags"]
        flat_tags = {
            tag
            for sections in frontend["tag_library"].values()
            for tags in sections.values()
            for tag in tags
        }
        self.assertGreaterEqual(metadata["tag_count"], 130)
        for tag in ("鱼眼镜头", "参考设定表", "赛璐璐上色", "VHS噪点", "简单背景"):
            self.assertIn(tag, flat_tags)
            self.assertIn(tag, metadata["aliases"])
        self.assertEqual(prompt_builder._translate_prompt_fragment("鱼眼镜头"), "fisheye lens")
        self.assertEqual(prompt_builder._translate_prompt_fragment("参考设定表"), "reference sheet")

    def test_danbooru_visual_intents_converge_before_every_prompt_mode(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        selected = OrderedDict((name, []) for name, _slots, _options in module._all_tag_groups())
        selected["场景背景"] = ["城市街道", "白色背景", "黑色背景"]
        selected["构图视角"] = ["参考设定表", "多视角展示", "鱼眼镜头", "第一人称视角"]
        selected["光影氛围"] = ["双色调", "互补色", "高键光", "低键光", "月光"]
        normalized, custom_tags, notes = module._normalize_inference_state(
            selected,
            [],
            {
                "模板风格": "插画感",
                "标签反推模式": "自动平衡",
                "主体类型": "自动",
                "随机主题池": "自动",
            },
        )
        active = set(module._collect_all_tags(normalized, custom_tags))
        self.assertIn("参考设定表", active)
        self.assertIn("多视角展示", active)
        self.assertEqual(len(active & {"简单背景", "白色背景", "黑色背景", "渐变背景", "网格背景", "透明背景"}), 1)
        self.assertIn("白色背景", active)
        self.assertNotIn("城市街道", active)
        self.assertNotIn("鱼眼镜头", active)
        self.assertNotIn("第一人称视角", active)
        self.assertEqual(len(active & {"双色调", "互补色", "冷暖对比", "单色插画"}), 1)
        self.assertLessEqual(len(active & {"顶光", "底光", "聚光灯", "伦勃朗光", "高键光", "低键光", "月光", "霓虹光"}), 2)
        self.assertTrue(any("设定表收敛" in note for note in notes))

    def test_advanced_theme_and_template_profiles_can_emit_danbooru_visual_tags(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        theme_seen: set[str] = set()
        style_seen: set[str] = set()
        for seed in range(24):
            empty = OrderedDict((name, []) for name, _slots, _options in module._all_tag_groups())
            _style, themed, themed_custom = module._apply_random_theme_pool_bias(
                "CG感",
                empty,
                [],
                {"随机主题池": "机甲科幻", "模板风格": "自动", "seed": seed},
            )
            theme_seen.update(module._collect_all_tags(themed, themed_custom))
            styled, styled_custom = module._apply_template_style_profile_bias(
                "插画感",
                empty,
                [],
                {"模板风格": "插画感", "运行时随机标签": False, "seed": seed},
            )
            style_seen.update(module._collect_all_tags(styled, styled_custom))
        self.assertTrue({"参考设定表", "多视角展示", "角色设计稿"} <= theme_seen)
        self.assertTrue({"赛璐璐上色", "对角线构图", "双色调"} <= style_seen)

    def test_pipeline_reports_danbooru_tags_for_skill_and_model_context(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module._run_stage(
            None,
            **{
                "unique_id": "danbooru-general-pipeline",
                "主体标签1": "成年女性",
                "画面风格标签1": "赛璐璐上色",
                "构图视角标签1": "鱼眼镜头",
                "场景背景标签1": "城市街道",
                "光影氛围标签1": "霓虹光",
                "模板风格": "插画感",
                "随机主题池": "自动",
                "生成数量": 1,
                "提示词语言": "纯英文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 0,
            },
        )
        payload = json.loads(result[3])
        self.assertIn("鱼眼镜头", payload["danbooru_general_tags"])
        self.assertEqual(payload["danbooru_general_aliases"]["鱼眼镜头"], "fisheye lens")
        self.assertIn("fisheye lens", result[1])
        self.assertNotRegex(result[1], r"[\u4e00-\u9fff]")


    def test_fantasy_template_and_theme_options_are_profile_backed(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        expected_styles = {
            "奇幻风格", "西方奇幻", "高等奇幻", "剑与魔法", "哥特奇幻",
            "黑暗童话", "精灵幻想", "梦幻奇境", "日式奇幻动画",
            "漆原智志画风", "结城信辉画风", "童话绘本", "魔幻油画",
            "奇幻概念设计", "史诗奇幻海报",
        }
        expected_pools = {
            "奇幻风格", "高等奇幻", "剑与魔法", "精灵秘境", "龙骑士史诗",
            "魔法学院", "地下城冒险", "黑暗童话", "哥特奇幻", "天使与恶魔",
            "魔女秘仪", "浮空城邦", "幻想宫廷", "冰雪王国", "沙漠神话",
            "海洋奇幻", "森林精灵", "蒸汽魔法", "异世界冒险", "日式奇幻OVA",
            "漆原智志幻想", "结城信辉幻想", "史诗群像", "远古遗迹", "龙与宝藏",
        }
        self.assertTrue(expected_styles <= set(module.模板选项))
        self.assertTrue(expected_pools <= set(module.随机主题池选项))
        self.assertTrue(expected_styles <= set(module.模板风格基础映射))
        self.assertEqual(expected_styles, set(module.FANTASY_TEMPLATE_STYLE_VARIANTS))
        self.assertEqual(expected_pools, set(module.FANTASY_THEME_VARIANTS))
        self.assertTrue(all(len(variants) >= 2 for variants in module.FANTASY_TEMPLATE_STYLE_VARIANTS.values()))
        self.assertTrue(all(len(variants) >= 2 for variants in module.FANTASY_THEME_VARIANTS.values()))
        for pool in ("奇幻风格", "漆原智志幻想", "结城信辉幻想"):
            selected = OrderedDict((name, []) for name, _slots, _options in module._all_tag_groups())
            settings = {"随机主题池": pool, "模板风格": "自动", "seed": 3}
            resolved_style, themed, themed_custom = module._apply_random_theme_pool_bias(
                "真实感", selected, [], settings
            )
            self.assertNotEqual(resolved_style, "真实感")
            self.assertTrue(module._collect_all_tags(themed, themed_custom))
            self.assertTrue(settings["随机主题池档案标记"])

    def test_fantasy_tag_library_exposes_artist_scene_and_worldbuilding_controls(self) -> None:
        library = tag_library.当前标签库()
        flat = {tag for sections in library.values() for tags in sections.values() for tag in tags}
        for tag in (
            "漆原智志画风", "结城信辉画风", "奇幻概念设计", "精灵游侠",
            "龙骑士", "浮空城", "魔法学院", "地下城遗迹", "水晶法杖",
            "魔法阵", "精细赛璐璐", "优雅奇幻线稿", "英雄海报构图",
        ):
            self.assertIn(tag, flat)

    def test_fantasy_artist_style_reaches_every_model_source_before_refinement(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        captured: list[tuple[str, str]] = []

        def capture_refinement(_model, prompts, settings, **_kwargs):
            captured.append((str(settings.get("模型来源", "")), str(prompts[0])))
            return list(prompts)

        with mock.patch.object(module, "_maybe_model_refine_batch_impl", side_effect=capture_refinement):
            for source in ("仅Skill", "本地GGUF", "API接口"):
                result = module._run_stage(
                    None,
                    **{
                        "unique_id": f"fantasy-all-models-{source}",
                        "主体标签1": "成年女性",
                        "模板风格": "漆原智志画风",
                        "随机主题池": "自动",
                        "生成数量": 1,
                        "提示词语言": "纯中文",
                        "运行时随机标签": False,
                        "模型来源": source,
                        "seed": 1,
                    },
                )
                self.assertIn("漆原智志", result[1])
        self.assertEqual([source for source, _prompt in captured], ["仅Skill", "本地GGUF", "API接口"])
        self.assertTrue(all("漆原智志" in prompt for _source, prompt in captured))

    def test_fantasy_styles_survive_runtime_smart_text_tag_blocks_and_model_guards(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        runtime_profiles = prompt_builder._resolve_runtime_style_profiles(
            "漆原智志画风", "漆原智志画风", ""
        )
        self.assertTrue(runtime_profiles)
        self.assertTrue(all(profile["style_lead"] == "漆原智志式华丽奇幻动画插画" for profile in runtime_profiles))
        self.assertTrue(all("漆原智志画风" in profile["style_tags"] for profile in runtime_profiles))

        smart = module._run_stage(
            None,
            **{
                "unique_id": "fantasy-smart-text-english",
                "主体标签1": "成年女性",
                "智能文本匹配": True,
                "智能文本输入": "银发精灵，远古森林，柔和月光，奇幻冒险",
                "模板风格": "结城信辉画风",
                "随机主题池": "精灵秘境",
                "生成数量": 1,
                "提示词语言": "纯英文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 2,
            },
        )
        self.assertIn("Nobuteru Yuki", smart[1])
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in smart[1]), smart[1])

        block_payload = {
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "主体", "tags": ["成年女性"]},
                {"type": "tag_group", "group": "画面风格", "tags": ["漆原智志画风"]},
                {"type": "tag_group", "group": "场景背景", "tags": ["水晶宫殿"]},
            ],
        }
        blocked = module._run_stage(
            None,
            **{
                "unique_id": "fantasy-tag-block-english",
                "主体标签1": "成年女性",
                "画面风格标签1": "漆原智志画风",
                "场景背景标签1": "水晶宫殿",
                "标签块编排启用": True,
                "标签块编排JSON": json.dumps(block_payload, ensure_ascii=False),
                "模板风格": "漆原智志画风",
                "生成数量": 1,
                "提示词语言": "纯英文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 4,
            },
        )
        self.assertIn("Satoshi Urushihara", blocked[1])
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in blocked[1]), blocked[1])

        character_sheet = module._run_stage(
            None,
            **{
                "unique_id": "fantasy-character-sheet-english",
                "主体标签1": "成年女性",
                "图片反推生成": True,
                "图片反推模式": "角色设定图",
                "模板风格": "漆原智志画风",
                "随机主题池": "自动",
                "生成数量": 1,
                "提示词语言": "纯英文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 5,
            },
        )
        self.assertIn("Satoshi Urushihara", character_sheet[1])
        self.assertIn("character sheet", character_sheet[1])
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in character_sheet[1]), character_sheet[1])

        nsfw_workspace = {
            "enabled": True,
            "preset": "——",
            "quality_tier": "高质量",
            "random_mode": "关闭",
            "trigger_words": ["女仆"],
            "scene": "豪华卧室",
            "negative_preset": "标准负面提示词",
        }
        nsfw = module._run_stage(
            None,
            **{
                "unique_id": "fantasy-nsfw-style-anchor",
                "主体标签1": "成年女性",
                "模板风格": "结城信辉画风",
                "随机主题池": "精灵秘境",
                "nsfw_workspace": nsfw_workspace,
                "生成数量": 1,
                "提示词语言": "纯中文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 6,
            },
        )
        self.assertIn("结城信辉", nsfw[1])
        self.assertIn(
            "漆原智志画风",
            model_refiner._restore_mode_literal_guards(
                "漆原智志画风，成年女性，水晶宫殿",
                "成年女性，水晶宫殿",
            ),
        )


    def test_expanded_template_and_theme_catalogs_are_large_and_profile_backed(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        self.assertGreaterEqual(len(module.EXPANDED_TEMPLATE_OPTIONS), 60)
        self.assertGreaterEqual(len(module.EXPANDED_THEME_POOL_OPTIONS), 67)
        self.assertGreaterEqual(len(module.模板选项), 90)
        self.assertGreaterEqual(len(module.随机主题池选项), 110)
        self.assertEqual(set(module.EXPANDED_TEMPLATE_OPTIONS), set(module.EXPANDED_TEMPLATE_STYLE_VARIANTS))
        self.assertEqual(set(module.EXPANDED_THEME_POOL_OPTIONS), set(module.EXPANDED_THEME_VARIANTS))
        self.assertTrue(all(len(items) >= 2 for items in module.EXPANDED_TEMPLATE_STYLE_VARIANTS.values()))
        self.assertTrue(all(len(items) >= 2 for items in module.EXPANDED_THEME_VARIANTS.values()))
        for style in ("纪实摄影", "水彩插画", "赛博朋克", "宋韵工笔", "宇宙神话"):
            self.assertIn(style, module.模板选项)
            self.assertIn(style, skills.TEMPLATE_STYLE_BASE_MAP)
        for pool in ("雨夜都市", "江南烟雨", "星际远征", "梦核空间", "量子神殿"):
            self.assertIn(pool, module.随机主题池选项)

    def test_expanded_profile_tags_are_registered_in_the_builtin_library(self) -> None:
        library = tag_library.当前标签库()
        flat = {tag for sections in library.values() for tags in sections.values() for tag in tags}
        for tag in ("纪实摄影", "赛博朋克", "宋韵工笔", "宇宙神话", "雨后街头", "环形空间站", "量子神殿"):
            self.assertIn(tag, flat)

    def test_concise_prompt_mode_is_natural_language_for_all_model_sources(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        for source in ("仅Skill", "本地GGUF", "API接口"):
            with self.subTest(source=source):
                result = module._run_stage(
                    None,
                    **{
                        "unique_id": f"natural-concise-{source}",
                        "模板风格": "赛博朋克",
                        "随机主题池": "赛博雨城",
                        "详细度": "简洁",
                        "生成数量": 1,
                        "提示词语言": "纯中文",
                        "运行时随机标签": source == "仅Skill",
                        "模型来源": source,
                        "seed": 17,
                    },
                )
                prompt = result[1]
                self.assertIn("画面以", prompt)
                self.assertIn("最终画面", prompt)
                self.assertIn("。", prompt)
                self.assertFalse(model_refiner._looks_like_tag_chain_prompt(prompt))

    def test_expanded_style_and_theme_keep_natural_english_output(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module._run_stage(
            None,
            **{
                "unique_id": "expanded-natural-english",
                "模板风格": "宇宙神话",
                "随机主题池": "量子神殿",
                "详细度": "简洁",
                "生成数量": 1,
                "提示词语言": "纯英文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 21,
            },
        )
        self.assertIn("centered on", result[1])
        self.assertIn("The final image", result[1])
        self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in result[1]), result[1])

    def test_model_tag_chain_falls_back_to_natural_skill_prompt(self) -> None:
        class FakeModel:
            def create_chat_completion(self, **_kwargs):
                return None

        original = "电影感影像，画面以成年女性为核心，主体处于霓虹街区中；镜头保持稳定，最终画面层次清楚。"
        tag_chain = "成年女性, 赛博朋克, 霓虹街区, 蓝洋红对撞, 能量刀, 机能外套, 全景全身, 高细节, 清晰对焦"
        settings = {"提示词语言": "纯中文", "模型来源": "API接口"}
        refined = model_refiner.maybe_model_refine(
            FakeModel(),
            original,
            settings,
            chat_completion=lambda *_args, **_kwargs: {"choices": [{"message": {"content": tag_chain}}]},
            clean_think_text=lambda text: text,
        )
        self.assertEqual(refined, original)
        self.assertTrue(model_refiner._looks_like_tag_chain_prompt(tag_chain))

    def test_nsfw_catalog_exposes_enriched_adult_controls_and_presets(self) -> None:
        catalog = nsfw_workspace.build_nsfw_workspace_catalog()
        options = catalog["options"]
        self.assertGreaterEqual(sum(len(values) for values in options.values()), 560)
        self.assertGreaterEqual(len(catalog["presets"]), 16)
        self.assertGreaterEqual(len(nsfw_presets.NSFW_WORKSPACE_SIGNAL_TERMS), 475)
        self.assertIn("成年情侣", options["selector_character"])
        self.assertIn("真丝睡袍", options["selector_outfit"])
        self.assertIn("从后拥抱", options["selector_action"])
        self.assertIn("雨夜车厢", options["selector_scene"])
        self.assertIn("自信凝视", options["selector_expression"])
        self.assertIn("红酒杯", options["selector_prop"])
        self.assertIn("星海舱室", catalog["presets"])
        self.assertIn("成人写实负面提示词", catalog["negative_presets"])
        self.assertIn("视频电影感", catalog["quality_tags"])
        self.assertNotIn("anatomy_terms", nsfw_mapper._RANDOM_ALL_FIELDS)
        self.assertNotIn("explicit_terms", nsfw_mapper._RANDOM_ALL_FIELDS)

    def test_concise_nsfw_prompt_keeps_adult_and_runtime_profile_details_as_prose(self) -> None:
        selected = OrderedDict(
            {
                "主体": ["成年情侣"],
                "画面风格": ["电影写实"],
                "成人向表达": ["高级性感"],
                "服装造型": [],
                "场景背景": ["酒店套房"],
                "道具世界观": [],
                "光影氛围": [],
                "构图视角": ["全景全身"],
                "动作姿态": [],
                "技术画质": [],
            }
        )
        fragments = [
            "电影写实影像",
            "成年情侣",
            "电影写实",
            "高级性感",
            "酒店套房",
            "全景全身",
            "从背后轻拥，双手位置清楚，人物关系稳定",
            "酒红色蕾丝连体衣，花纹边缘清晰，身体比例自然",
            "暖色台灯，局部照亮面部",
            "masterpiece",
            "best quality",
        ]
        custom_tags = [
            "masterpiece",
            "best quality",
            "成年主体明确",
            "丝绸床单",
            "红酒杯",
            "亲密关系稳定",
        ]
        prompt = prompt_builder._build_concise_chinese_prompt(
            fragments,
            selected,
            custom_tags,
            {"主体类型": "人物角色", "详细度": "简洁", "提示词语言": "纯中文"},
            {"scene_group": "酒店套房", "identity": "成年情侣", "style_track": "电影写实", "recent_tracks": []},
        )
        self.assertIn("成人氛围通过高级性感", prompt)
        self.assertIn("从背后轻拥", prompt)
        self.assertIn("酒红色蕾丝连体衣", prompt)
        self.assertIn("成年主体明确", prompt)
        self.assertIn("红酒杯", prompt)
        self.assertIn("最终画面", prompt)
        self.assertFalse(model_refiner._looks_like_tag_chain_prompt(prompt))

    def test_nsfw_preset_replaces_empty_scaffold_and_prioritizes_user_choices(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        result = module._run_stage(
            None,
            **{
                "unique_id": "enriched-nsfw-natural-preset",
                "nsfw_workspace": {
                    "enabled": True,
                    "preset": "镜前蕾丝",
                    "quality_tier": "成人氛围增强",
                    "random_mode": "关闭",
                    "selector_character": "成年女性",
                    "selector_prop": "红酒杯",
                    "negative_preset": "成人写实负面提示词",
                },
                "模板风格": "电影写实",
                "随机主题池": "自动",
                "详细度": "简洁",
                "生成数量": 1,
                "提示词语言": "纯中文",
                "运行时随机标签": False,
                "模型来源": "仅Skill",
                "seed": 19,
            },
        )
        prompt = result[1]
        self.assertIn("成年女性", prompt)
        self.assertIn("成熟私密氛围", prompt)
        self.assertIn("红酒杯", prompt)
        self.assertIn("复古化妆间", prompt)
        self.assertIn("酒红色蕾丝连体衣", prompt)
        self.assertNotIn("简洁室内", prompt)
        self.assertNotIn("站姿挺拔", prompt)
        self.assertNotIn("other", prompt)
        self.assertFalse(model_refiner._looks_like_tag_chain_prompt(prompt))

    def test_natural_language_validator_rejects_tag_chains(self) -> None:
        natural = (
            "电影感影像，画面以成年女性为核心，主体位于雨夜街头并自然走动。"
            "镜头采用全景构图，以霓虹逆光塑造空间层次，最终画面保持材质可信和视觉流动。"
        )
        tag_chain = "成年女性, 电影写实, 雨夜街头, 霓虹逆光, 全景全身, 自然行走, 高细节, 清晰对焦"
        self.assertTrue(model_refiner.is_natural_language_prompt(natural, {"提示词语言": "纯中文"}))
        self.assertFalse(model_refiner.is_natural_language_prompt(tag_chain, {"提示词语言": "纯中文"}))

    def test_all_generation_modes_emit_natural_language_prompts(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        module._CACHE.clear()
        tag_block_payload = {
            "enabled": True,
            "blocks": [
                {"type": "tag_group", "group": "主体", "label": "主体", "tags": ["成年女性"]},
                {"type": "tag_group", "group": "画面风格", "label": "风格", "tags": ["电影写实"]},
                {"type": "tag_group", "group": "场景背景", "label": "场景", "tags": ["雨夜街头"]},
                {"type": "tag_group", "group": "光影氛围", "label": "光影", "tags": ["霓虹逆光"]},
            ],
        }
        cases = {
            "standard": {"详细度": "标准"},
            "concise": {"详细度": "简洁"},
            "detailed": {"详细度": "详细"},
            "english": {"提示词语言": "纯英文"},
            "mixed": {"提示词语言": "英文提示词+中文说明"},
            "runtime_random": {"运行时随机标签": True, "运行时随机强度": "强 / 极限拉开"},
            "smart_text": {
                "智能文本匹配": True,
                "智能文本输入": "成年女性在雨夜街头自然行走，霓虹逆光，电影写实，全景全身",
            },
            "tag_block": {
                "标签块编排启用": True,
                "标签块编排JSON": json.dumps(tag_block_payload, ensure_ascii=False),
            },
            "character_sheet": {"图片反推生成": True, "图片反推模式": "角色设定图"},
            "nsfw": {
                "nsfw_workspace": {
                    "enabled": True,
                    "preset": "镜前蕾丝",
                    "quality_tier": "成人氛围增强",
                    "random_mode": "关闭",
                    "selector_character": "成年女性",
                    "negative_preset": "成人写实负面提示词",
                },
            },
            "non_person": {"主体类型": "非人物主体", "主体标签1": "机械巨龙"},
            "prompt_only": {"输出模式": "仅提示词优先"},
        }
        for index, (mode, overrides) in enumerate(cases.items()):
            with self.subTest(mode=mode):
                settings = {
                    "unique_id": f"natural-contract-{mode}",
                    "主体标签1": "成年女性",
                    "画面风格标签1": "电影写实",
                    "场景背景标签1": "雨夜街头",
                    "光影氛围标签1": "霓虹逆光",
                    "模板风格": "电影写实",
                    "随机主题池": "自动",
                    "详细度": "标准",
                    "生成数量": 1,
                    "提示词语言": "纯中文",
                    "运行时随机标签": False,
                    "模型来源": "仅Skill",
                    "seed": 3100 + index,
                }
                settings.update(overrides)
                result = module._run_stage(None, **settings)
                prompt = result[1]
                language_settings = {"提示词语言": settings["提示词语言"]}
                self.assertTrue(
                    model_refiner.is_natural_language_prompt(prompt, language_settings),
                    prompt,
                )
                self.assertFalse(model_refiner._looks_like_tag_chain_prompt(prompt), prompt)
                smart_prompt = result[6]
                if mode == "smart_text":
                    self.assertTrue(smart_prompt)
                if smart_prompt:
                    self.assertTrue(
                        model_refiner.is_natural_language_prompt(smart_prompt, language_settings),
                        smart_prompt,
                    )
                    self.assertFalse(model_refiner._looks_like_tag_chain_prompt(smart_prompt), smart_prompt)

    def test_tag_block_tag_chain_is_replaced_by_natural_fallback(self) -> None:
        module = load_stage_prompt_generator_for_integration_test()
        tag_chain = "成年女性, 电影写实, 雨夜街头, 霓虹逆光, 全景全身, 自然行走, 高细节, 清晰对焦"
        payload = {
            "enabled": True,
            "blocks": [{"type": "text", "label": "画面", "text": "成年女性在雨夜街头自然行走"}],
        }
        with (
            mock.patch.object(module, "_build_tag_block_prompt_list_impl", return_value=[tag_chain]),
            mock.patch.object(
                module,
                "_maybe_model_refine_batch_impl",
                side_effect=lambda _model, prompt_list, _settings, **_kwargs: list(prompt_list),
            ),
        ):
            result = module._run_stage(
                None,
                **{
                    "unique_id": "natural-contract-tag-block-fallback",
                    "主体标签1": "成年女性",
                    "画面风格标签1": "电影写实",
                    "场景背景标签1": "雨夜街头",
                    "标签块编排启用": True,
                    "标签块编排JSON": json.dumps(payload, ensure_ascii=False),
                    "生成数量": 1,
                    "提示词语言": "纯中文",
                    "运行时随机标签": False,
                    "模型来源": "仅Skill",
                    "seed": 3200,
                },
            )
        self.assertNotEqual(result[1], tag_chain)
        self.assertTrue(
            model_refiner.is_natural_language_prompt(result[1], {"提示词语言": "纯中文"}),
            result[1],
        )

if __name__ == "__main__":
    unittest.main()
