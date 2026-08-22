from __future__ import annotations

import importlib.util
import base64
import io
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

import torch


ROOT = Path(__file__).resolve().parents[1]


def load_nodes(models_dir: Path):
    package_name = "qwen_te_raw_model_nodes_test"
    dependency_names = [
        package_name,
        "folder_paths",
        "comfy",
        "comfy.model_management",
        "llama_cpp",
        "llama_cpp.llama_tokenizer",
        "llama_cpp.llama_chat_format",
        "transformers",
    ]
    saved = {name: sys.modules.get(name) for name in dependency_names}

    folder_paths = types.ModuleType("folder_paths")
    folder_paths.models_dir = str(models_dir)
    folder_paths.supported_pt_extensions = {".safetensors", ".bin", ".pt", ".pth"}
    folder_paths.folder_names_and_paths = {}
    folder_paths.get_filename_list = lambda _name: []

    model_management = types.ModuleType("comfy.model_management")
    model_management.soft_empty_cache = lambda: None
    model_management.unload_all_models = lambda *args, **kwargs: None
    model_management.processing_interrupted = lambda: False
    model_management.InterruptProcessingException = RuntimeError
    comfy = types.ModuleType("comfy")
    comfy.__path__ = []
    comfy.model_management = model_management

    class FakeLlama:
        def __init__(self, model_path=None, **kwargs):
            self.model_path = model_path
            self.init_kwargs = kwargs

        def create_chat_completion(self, **_kwargs):
            return {"choices": [{"message": {"content": "gguf output"}}]}

        def close(self):
            return None

    llama_cpp = types.ModuleType("llama_cpp")
    llama_cpp.__path__ = []
    llama_cpp.Llama = FakeLlama
    llama_cpp.GGML_TYPE_Q8_0 = 8
    tokenizer_module = types.ModuleType("llama_cpp.llama_tokenizer")
    tokenizer_module.LlamaTokenizer = None
    chat_format = types.ModuleType("llama_cpp.llama_chat_format")
    for name in ("Qwen3VLChatHandler", "Qwen35ChatHandler", "Qwen38ChatHandler", "Qwen38VLChatHandler", "Gemma4ChatHandler"):
        setattr(chat_format, name, None)

    class FakeTokenizer:
        pad_token_id = 0
        eos_token_id = 2

        @classmethod
        def from_pretrained(cls, *_args, **_kwargs):
            return cls()

        def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
            assert tokenize is False
            assert add_generation_prompt is True
            return "\n".join(f"{item['role']}: {item['content']}" for item in messages) + "\nassistant:"

        def __call__(self, *_args, **_kwargs):
            return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

        def batch_decode(self, _tokens, skip_special_tokens=True):
            assert skip_special_tokens is True
            return ["原始模型输出"]

    class FakeCausalModel(torch.nn.Module):
        @classmethod
        def from_pretrained(cls, *_args, **_kwargs):
            return cls()

        def __init__(self):
            super().__init__()
            self.anchor = torch.nn.Parameter(torch.zeros(1))

        def generate(self, input_ids, **_kwargs):
            return torch.tensor([[1, 2, 3, 4]], dtype=input_ids.dtype, device=input_ids.device)

    transformers = types.ModuleType("transformers")
    transformers.AutoTokenizer = FakeTokenizer
    transformers.AutoProcessor = None
    transformers.AutoModelForCausalLM = FakeCausalModel

    injected = {
        "folder_paths": folder_paths,
        "comfy": comfy,
        "comfy.model_management": model_management,
        "llama_cpp": llama_cpp,
        "llama_cpp.llama_tokenizer": tokenizer_module,
        "llama_cpp.llama_chat_format": chat_format,
        "transformers": transformers,
    }
    sys.modules.update(injected)
    try:
        spec = importlib.util.spec_from_file_location(package_name, ROOT / "nodes.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


class RawModelSupportTests(unittest.TestCase):
    def test_raw_directory_is_listed_and_weight_file_resolves_to_parent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "LLM"
            model_dir = root / "raw-qwen"
            model_dir.mkdir(parents=True)
            (model_dir / "config.json").write_text("{}", encoding="utf-8")
            (model_dir / "model.safetensors").write_bytes(b"placeholder")
            module = load_nodes(Path(temp))

            self.assertIn("raw-qwen", module._列出llm文件())
            self.assertTrue(module._是本地模型选项("raw-qwen"))
            self.assertEqual(
                module._解析本地模型路径("raw-qwen/model.safetensors"),
                (str(model_dir), "transformers"),
            )

    def test_transformers_model_uses_same_chat_completion_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            model_dir = Path(temp) / "LLM" / "raw-qwen"
            model_dir.mkdir(parents=True)
            (model_dir / "config.json").write_text("{}", encoding="utf-8")
            (model_dir / "model.safetensors").write_bytes(b"placeholder")
            module = load_nodes(Path(temp))
            config = {
                "model": "raw-qwen",
                "family": "Qwen3.5-VL",
                "mmproj": "无",
                "think": False,
                "n_ctx": 4096,
                "n_gpu_layers": 0,
            }
            loaded = module._QwenStorage.load(config)
            self.assertTrue(getattr(loaded.llm, "_qwen_te_transformers", False))
            output = module._调用chat_completion(
                loaded.llm,
                messages=[{"role": "user", "content": "你好"}],
                params={"max_tokens": 16, "temperature": 0},
            )
            self.assertEqual(output["choices"][0]["message"]["content"], "原始模型输出")
            module._QwenStorage.unload()

    def test_missing_transformers_dependency_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as temp:
            model_dir = Path(temp) / "LLM" / "raw"
            model_dir.mkdir(parents=True)
            (model_dir / "config.json").write_text("{}", encoding="utf-8")
            (model_dir / "model.safetensors").write_bytes(b"placeholder")
            module = load_nodes(Path(temp))
            module._TRANSFORMERS = None
            with self.assertRaisesRegex(RuntimeError, "transformers"):
                module._QwenStorage.load(
                    {
                        "model": "raw",
                        "family": "Llama",
                        "mmproj": "无",
                        "think": False,
                    }
                )

    def test_transformers_adapter_clamps_generation_to_context_and_supports_old_templates(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {}

            class TinyTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, messages, tokenize=False):
                    captured["template_messages"] = messages
                    return "prompt"

                def __call__(self, *_args, **_kwargs):
                    return {"input_ids": torch.tensor([[1, 2, 3, 4]], dtype=torch.long)}

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["bounded output"]

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **kwargs):
                    captured["generation"] = kwargs
                    return torch.tensor([[1, 2, 3, 4, 5]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                TinyTokenizer(),
                None,
                "raw",
                {"n_ctx": 256},
            )
            response = adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=512,
                temperature=0,
            )
            self.assertEqual(captured["generation"]["max_new_tokens"], 252)
            self.assertEqual(response["choices"][0]["message"]["content"], "bounded output")

    def test_transformers_adapter_respects_model_context_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {}

            class LimitedConfig:
                max_position_embeddings = 32

            class LimitedTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
                    return "prompt"

                def __call__(self, *_args, **_kwargs):
                    return {"input_ids": torch.tensor([[1, 2, 3, 4]], dtype=torch.long)}

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["metadata bounded output"]

            class LimitedModel(torch.nn.Module):
                config = LimitedConfig()

                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **kwargs):
                    captured["generation"] = kwargs
                    return torch.tensor([[1, 2, 3, 4, 5]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                LimitedModel(),
                LimitedTokenizer(),
                None,
                "raw-limited",
                {"n_ctx": 256},
            )
            adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=128,
                temperature=0,
            )
            self.assertEqual(captured["generation"]["max_new_tokens"], 28)

    def test_transformers_adapter_keeps_images_out_of_template_and_passes_them_to_processor(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            image_buffer = io.BytesIO()
            module.Image.new("RGB", (1, 1), (255, 0, 0)).save(image_buffer, format="PNG")
            image_url = "data:image/png;base64," + base64.b64encode(image_buffer.getvalue()).decode("ascii")
            captured = {}

            class VisionTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
                    captured["template_messages"] = messages
                    return "vision prompt"

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["vision output"]

            class VisionProcessor(VisionTokenizer):
                image_processor = object()

                def __call__(self, **kwargs):
                    captured["images"] = kwargs["images"]
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **kwargs):
                    return torch.tensor([[1, 2, 3]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                VisionTokenizer(),
                VisionProcessor(),
                "raw-vision",
                {"n_ctx": 16},
            )
            adapter.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "describe"},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                max_tokens=4,
            )
            template_content = captured["template_messages"][0]["content"]
            self.assertEqual(template_content[1], {"type": "image"})
            self.assertEqual(len(captured["images"]), 1)

    def test_transformers_adapter_retries_legacy_processor_signature(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            image_buffer = io.BytesIO()
            module.Image.new("RGB", (1, 1), (0, 255, 0)).save(image_buffer, format="PNG")
            image_url = "data:image/png;base64," + base64.b64encode(image_buffer.getvalue()).decode("ascii")
            captured = {}

            class LegacyTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
                    return "legacy vision prompt"

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["legacy vision output"]

            class LegacyProcessor(LegacyTokenizer):
                image_processor = object()

                def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
                    image_part = messages[0]["content"][1]
                    if "image" not in image_part:
                        raise KeyError("legacy processor requires an embedded image")
                    captured["template_image"] = image_part["image"]
                    return "legacy vision prompt"

                def __call__(self, text, images, return_tensors):
                    captured["text"] = text
                    captured["images"] = images
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **_kwargs):
                    return torch.tensor([[1, 2, 3]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                LegacyTokenizer(),
                LegacyProcessor(),
                "raw-legacy-vision",
                {"n_ctx": 16},
            )
            adapter.create_chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "describe"},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                max_tokens=4,
            )
            self.assertEqual(captured["text"], ["legacy vision prompt"])
            self.assertEqual(len(captured["images"]), 1)
            self.assertIsInstance(captured["template_image"], module.Image.Image)

    def test_transformers_adapter_accepts_tokenized_chat_template(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))

            class TokenizedTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return [11, 12, 13]

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["tokenized output"]

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **kwargs):
                    return torch.tensor([[11, 12, 13, 14]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                TokenizedTokenizer(),
                None,
                "raw-tokenized",
                {"n_ctx": 16},
            )
            response = adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
                temperature=0,
            )
            self.assertEqual(response["choices"][0]["message"]["content"], "tokenized output")


if __name__ == "__main__":
    unittest.main()
