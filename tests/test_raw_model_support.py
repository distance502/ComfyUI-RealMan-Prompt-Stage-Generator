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

import numpy as np
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

    def test_transformers_loader_uses_processor_tokenizer_when_autotokenizer_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            model_dir = Path(temp) / "LLM" / "processor-only-vision"
            model_dir.mkdir(parents=True)
            (model_dir / "config.json").write_text("{}", encoding="utf-8")
            (model_dir / "model.safetensors").write_bytes(b"placeholder")
            module = load_nodes(Path(temp))

            class FailingTokenizer:
                @classmethod
                def from_pretrained(cls, *_args, **_kwargs):
                    raise ValueError("standalone tokenizer is unavailable")

            class ProcessorOnly:
                model_input_names = ["input_ids", "pixel_values", "image_grid_thw"]

                @classmethod
                def from_pretrained(cls, *_args, **_kwargs):
                    instance = cls()
                    instance.tokenizer = instance
                    return instance

                def apply_chat_template(self, _messages, tokenize=False, add_generation_prompt=True, **_kwargs):
                    return "processor prompt"

                def __call__(self, *_args, **_kwargs):
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["processor-only output"]

            class VisionModel(torch.nn.Module):
                @classmethod
                def from_pretrained(cls, *_args, **_kwargs):
                    return cls()

                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, input_ids, **_kwargs):
                    return torch.tensor([[1, 2, 3]], dtype=input_ids.dtype)

            module._TRANSFORMERS.AutoTokenizer = FailingTokenizer
            module._TRANSFORMERS.AutoProcessor = ProcessorOnly
            module._TRANSFORMERS.AutoModelForImageTextToText = VisionModel
            loaded = module._QwenStorage.load(
                {
                    "model": "processor-only-vision",
                    "family": "Qwen3.8-VL",
                    "mmproj": "无",
                    "think": False,
                    "n_ctx": 256,
                    "n_gpu_layers": 0,
                },
                force_reload=True,
            )
            self.assertIs(loaded.llm.tokenizer, loaded.llm.processor)
            self.assertTrue(loaded.llm.supports_images)
            module._QwenStorage.unload()

    def test_transformers_adapter_passes_thinking_flag_to_supported_template(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {}

            class ThinkingTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(
                    self,
                    _messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    enable_thinking=None,
                ):
                    captured["enable_thinking"] = enable_thinking
                    return "thinking prompt"

                def __call__(self, *_args, **_kwargs):
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["thinking output"]

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **_kwargs):
                    return torch.tensor([[1, 2, 3]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                ThinkingTokenizer(),
                None,
                "raw-thinking",
                {"n_ctx": 16, "think": True},
            )
            adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
            )
            self.assertIs(captured["enable_thinking"], True)

    def test_transformers_adapter_uses_cpu_device_map_before_meta_parameter(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))

            class MetaModel(torch.nn.Module):
                hf_device_map = {
                    "model.embed_tokens": "cpu",
                    "model.layers.0": "cuda:0",
                    "model.layers.1": "disk",
                }

                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.empty(1, device="meta"))

            adapter = module._TransformersChatAdapter(
                MetaModel(),
                object(),
                None,
                "raw-offloaded",
                {"n_ctx": 16},
            )
            self.assertEqual(adapter.device, torch.device("cpu"))

    def test_transformers_adapter_keeps_full_encoder_decoder_output(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {}

            class EncoderDecoderConfig:
                is_encoder_decoder = True
                pad_token_id = 7
                eos_token_id = 8

            class EncoderDecoderTokenizer:
                pad_token_id = None
                eos_token_id = None

                def apply_chat_template(self, _messages, tokenize=False, add_generation_prompt=True):
                    return "encoder prompt"

                def __call__(self, *_args, **_kwargs):
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

                def batch_decode(self, tokens, skip_special_tokens=True):
                    captured["decoded_tokens"] = tokens.clone()
                    return ["encoder-decoder output END trailing"]

            class EncoderDecoderModel(torch.nn.Module):
                config = EncoderDecoderConfig()

                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **kwargs):
                    captured["generation"] = kwargs
                    return torch.tensor([[21, 22, 23, 24]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                EncoderDecoderModel(),
                EncoderDecoderTokenizer(),
                None,
                "raw-encoder-decoder",
                {"n_ctx": 16},
            )
            response = adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
                stop="END",
            )
            self.assertEqual(captured["decoded_tokens"].tolist(), [[21, 22, 23, 24]])
            self.assertEqual(captured["generation"]["pad_token_id"], 7)
            self.assertEqual(captured["generation"]["eos_token_id"], 8)
            self.assertEqual(response["choices"][0]["message"]["content"], "encoder-decoder output")

    def test_transformers_loader_falls_back_to_remote_auto_model_with_generate(self):
        with tempfile.TemporaryDirectory() as temp:
            model_dir = Path(temp) / "LLM" / "remote-auto-model"
            model_dir.mkdir(parents=True)
            (model_dir / "config.json").write_text("{}", encoding="utf-8")
            (model_dir / "model.safetensors").write_bytes(b"placeholder")
            module = load_nodes(Path(temp))

            class UnsupportedSpecializedModel:
                @classmethod
                def from_pretrained(cls, *_args, **_kwargs):
                    raise ValueError("architecture is not registered here")

            class RemoteAutoModel(torch.nn.Module):
                @classmethod
                def from_pretrained(cls, *_args, **kwargs):
                    instance = cls()
                    instance.load_kwargs = kwargs
                    return instance

                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, input_ids, **_kwargs):
                    return torch.tensor([[1, 2, 3]], dtype=input_ids.dtype)

            for class_name in (
                "AutoModelForImageTextToText",
                "AutoModelForVision2Seq",
                "AutoModelForSeq2SeqLM",
                "AutoModelForCausalLM",
            ):
                setattr(module._TRANSFORMERS, class_name, UnsupportedSpecializedModel)
            module._TRANSFORMERS.AutoModel = RemoteAutoModel
            loaded = module._QwenStorage.load(
                {
                    "model": "remote-auto-model",
                    "family": "通用模型",
                    "mmproj": "无",
                    "think": False,
                    "n_ctx": 256,
                    "n_gpu_layers": 0,
                },
                force_reload=True,
            )
            self.assertIsInstance(loaded.llm.model, RemoteAutoModel)
            self.assertIs(loaded.llm.model.load_kwargs["trust_remote_code"], True)
            module._QwenStorage.unload()

    def test_multimodal_tokenized_template_is_decoded_before_processor_call(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            image_buffer = io.BytesIO()
            module.Image.new("RGB", (1, 1), (0, 0, 255)).save(image_buffer, format="PNG")
            image_url = "data:image/png;base64," + base64.b64encode(image_buffer.getvalue()).decode("ascii")
            captured = {}

            class MappingTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["decoded vision prompt"] if not skip_special_tokens else ["mapping vision output"]

            class MappingProcessor:
                model_input_names = ["input_ids", "pixel_values"]

                def apply_chat_template(self, _messages, **_kwargs):
                    return {"input_ids": torch.tensor([[31, 32]], dtype=torch.long)}

                def __call__(self, **kwargs):
                    captured["text"] = kwargs["text"]
                    captured["images"] = kwargs["images"]
                    return {
                        "input_ids": torch.tensor([[1, 2]], dtype=torch.long),
                        "pixel_values": torch.zeros((1, 3, 1, 1)),
                    }

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **_kwargs):
                    return torch.tensor([[1, 2, 3]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                MappingTokenizer(),
                MappingProcessor(),
                "raw-mapping-vision",
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
            self.assertEqual(captured["text"], ["decoded vision prompt"])
            self.assertEqual(len(captured["images"]), 1)

    def test_transformers_adapter_reads_nested_and_tokenizer_context_limits(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))

            class TextConfig:
                max_position_embeddings = 48

            class VisionConfig:
                max_position_embeddings = 8
                text_config = TextConfig()

            class LimitedTokenizer:
                model_max_length = 40

            class TinyModel(torch.nn.Module):
                config = VisionConfig()

                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                LimitedTokenizer(),
                None,
                "nested-context",
                {"n_ctx": 64},
            )
            self.assertEqual(adapter._context_length(), 40)

    def test_transformers_adapter_falls_back_to_root_context_when_nested_metadata_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))

            class TextConfig:
                pass

            class MultimodalConfig:
                max_position_embeddings = 96
                text_config = TextConfig()

            class LimitedTokenizer:
                model_max_length = 0

            class TinyModel(torch.nn.Module):
                config = MultimodalConfig()

                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                LimitedTokenizer(),
                None,
                "root-context-fallback",
                {"n_ctx": 128},
            )
            self.assertEqual(adapter._context_length(), 96)

    def test_transformers_adapter_merges_system_role_for_strict_template(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {}

            class StrictTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True, **_kwargs):
                    if any(item.get("role") == "system" for item in messages):
                        raise ValueError("system role is unsupported")
                    captured["messages"] = messages
                    return "strict prompt"

                def __call__(self, *_args, **_kwargs):
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["strict output"]

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **_kwargs):
                    return torch.tensor([[1, 2, 3]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                StrictTokenizer(),
                None,
                "strict-template",
                {"n_ctx": 32, "think": False},
            )
            adapter.create_chat_completion(
                messages=[
                    {"role": "system", "content": "只输出自然语言。"},
                    {"role": "user", "content": "生成提示词。"},
                ],
                max_tokens=4,
            )
            self.assertEqual(len(captured["messages"]), 1)
            merged = captured["messages"][0]["content"]
            self.assertIn("系统指令", merged)
            self.assertIn("只输出自然语言", merged)
            self.assertIn("生成提示词", merged)

    def test_transformers_adapter_uses_readable_prompt_when_chat_template_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {}

            class BaseTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, *_args, **_kwargs):
                    raise ValueError("Cannot use chat template because tokenizer.chat_template is not set")

                def __call__(self, prompt, **_kwargs):
                    captured["prompt"] = prompt
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["base model output"]

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **_kwargs):
                    return torch.tensor([[1, 2, 3]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                BaseTokenizer(),
                None,
                "base-model",
                {"n_ctx": 32},
            )
            response = adapter.create_chat_completion(
                messages=[
                    {"role": "system", "content": "保持简洁。"},
                    {"role": "user", "content": "写一个场景。"},
                ],
                max_tokens=4,
            )
            self.assertIn("系统指令", captured["prompt"])
            self.assertIn("保持简洁", captured["prompt"])
            self.assertTrue(captured["prompt"].endswith("assistant:"))
            self.assertEqual(response["choices"][0]["message"]["content"], "base model output")

    def test_transformers_adapter_returns_empty_text_when_causal_model_generates_no_new_tokens(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))

            class TinyTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return "prompt"

                def __call__(self, *_args, **_kwargs):
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

                def batch_decode(self, tokens, skip_special_tokens=True):
                    return ["" if tokens.shape[-1] == 0 else "unexpected prompt"]

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **_kwargs):
                    return torch.tensor([[1, 2]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                TinyTokenizer(),
                None,
                "no-new-tokens",
                {"n_ctx": 16},
            )
            response = adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
            )
            self.assertEqual(response["choices"][0]["message"]["content"], "")

    def test_transformers_adapter_retries_unknown_generate_keyword(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {"attempts": 0}

            class StrictTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return "strict generation prompt"

                def __call__(self, *_args, **_kwargs):
                    return {
                        "input_ids": torch.tensor([[1, 2]], dtype=torch.long),
                        "token_type_ids": torch.tensor([[0, 0]], dtype=torch.long),
                    }

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["strict generation output"]

            class StrictModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, input_ids, **kwargs):
                    captured["attempts"] += 1
                    if "token_type_ids" in kwargs:
                        raise ValueError("The following model_kwargs are not used by the model: token_type_ids")
                    if "repetition_penalty" in kwargs:
                        raise TypeError("generate() got an unexpected keyword argument 'repetition_penalty'")
                    return torch.tensor([[1, 2, 3]], dtype=input_ids.dtype)

            adapter = module._TransformersChatAdapter(
                StrictModel(),
                StrictTokenizer(),
                None,
                "strict-generation",
                {"n_ctx": 16},
            )
            response = adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
                temperature=0,
            )
            self.assertEqual(captured["attempts"], 3)
            self.assertEqual(response["choices"][0]["message"]["content"], "strict generation output")

    def test_transformers_adapter_does_not_drop_required_visual_inputs_on_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            image_buffer = io.BytesIO()
            module.Image.new("RGB", (1, 1), (255, 0, 0)).save(image_buffer, format="PNG")
            image_url = "data:image/png;base64," + base64.b64encode(image_buffer.getvalue()).decode("ascii")

            class VisionTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return "vision prompt"

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["vision output"]

            class VisionProcessor:
                image_processor = object()

                def __call__(self, *_args, **_kwargs):
                    return {
                        "input_ids": torch.tensor([[1, 2]], dtype=torch.long),
                        "pixel_values": torch.ones((1, 3, 2, 2)),
                    }

            class StrictVisionModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, input_ids, pixel_values, **kwargs):
                    raise TypeError("generate() got an unexpected keyword argument 'pixel_values'")

            adapter = module._TransformersChatAdapter(
                StrictVisionModel(),
                VisionTokenizer(),
                VisionProcessor(),
                "strict-vision-generation",
                {"n_ctx": 16},
            )
            with self.assertRaisesRegex(TypeError, "pixel_values"):
                adapter.create_chat_completion(
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "hello"},
                                {"type": "image_url", "image_url": {"url": image_url}},
                            ],
                        }
                    ],
                    max_tokens=4,
                )

    def test_transformers_adapter_accepts_batched_tokenized_chat_template(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))

            class BatchedTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return [[11, 12, 13], [21, 22, 23]]

                def batch_decode(self, tokens, skip_special_tokens=True):
                    self.shape = tuple(tokens.shape)
                    return ["batched output"]

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, input_ids, **_kwargs):
                    return torch.tensor([[11, 12, 13, 14]], dtype=input_ids.dtype)

            tokenizer = BatchedTokenizer()
            adapter = module._TransformersChatAdapter(
                TinyModel(),
                tokenizer,
                None,
                "batched-tokenized",
                {"n_ctx": 16},
            )
            response = adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
                temperature=0,
            )
            self.assertEqual(tokenizer.shape, (1, 1))
            self.assertEqual(response["choices"][0]["message"]["content"], "batched output")

    def test_transformers_adapter_accepts_numpy_tokenized_chat_template(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))

            class NumpyTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return np.asarray([31, 32, 33], dtype=np.int32)

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["numpy output"]

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, input_ids, **_kwargs):
                    return torch.tensor([[31, 32, 33, 34]], dtype=input_ids.dtype)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                NumpyTokenizer(),
                None,
                "numpy-tokenized",
                {"n_ctx": 16},
            )
            response = adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
                temperature=0,
            )
            self.assertEqual(response["choices"][0]["message"]["content"], "numpy output")

    def test_transformers_adapter_skips_unavailable_cuda_device_map(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))

            class CpuFallbackModel(torch.nn.Module):
                hf_device_map = {"model.embed_tokens": "cuda:0", "model.layers.0": "cpu"}

                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

            adapter = module._TransformersChatAdapter(
                CpuFallbackModel(),
                object(),
                None,
                "cpu-fallback",
                {"n_ctx": 16},
            )
            expected = torch.device("cuda:0") if torch.cuda.is_available() else torch.device("cpu")
            self.assertEqual(adapter.device, expected)

    def test_transformers_adapter_converts_list_generation_to_tensor(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))

            class ListTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return "list prompt"

                def __call__(self, *_args, **_kwargs):
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    self.decoded_shape = tuple(_tokens.shape)
                    return ["list output"]

            class ListModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **_kwargs):
                    return [1, 2, 3]

            adapter = module._TransformersChatAdapter(
                ListModel(),
                ListTokenizer(),
                None,
                "list-generation",
                {"n_ctx": 16},
            )
            response = adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
            )
            self.assertEqual(adapter.tokenizer.decoded_shape, (1, 1))
            self.assertEqual(response["choices"][0]["message"]["content"], "list output")

    def test_transformers_adapter_normalizes_numpy_processor_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {}

            class ArrayTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return "array prompt"

                def __call__(self, *_args, **_kwargs):
                    return {
                        "input_ids": np.asarray([[1, 2]], dtype=np.int32),
                        "attention_mask": [[1, 1]],
                    }

                def batch_decode(self, tokens, skip_special_tokens=True):
                    captured["input_type"] = type(tokens).__name__
                    return ["array output"]

            class ArrayModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, input_ids, attention_mask, **_kwargs):
                    captured["input_ids_type"] = type(input_ids).__name__
                    captured["attention_mask_type"] = type(attention_mask).__name__
                    captured["input_ids_dtype"] = input_ids.dtype
                    captured["attention_mask_dtype"] = attention_mask.dtype
                    return torch.tensor([[1, 2, 3]], dtype=input_ids.dtype)

            adapter = module._TransformersChatAdapter(
                ArrayModel(),
                ArrayTokenizer(),
                None,
                "array-processor-inputs",
                {"n_ctx": 16},
            )
            response = adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
            )
            self.assertEqual(captured["input_ids_type"], "Tensor")
            self.assertEqual(captured["attention_mask_type"], "Tensor")
            self.assertEqual(captured["input_ids_dtype"], torch.long)
            self.assertEqual(captured["attention_mask_dtype"], torch.long)
            self.assertEqual(response["choices"][0]["message"]["content"], "array output")

    def test_transformers_adapter_batches_flat_mapping_token_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {}

            class FlatTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return "flat prompt"

                def __call__(self, *_args, **_kwargs):
                    return {"input_ids": [1, 2, 3], "attention_mask": np.asarray([1, 1, 1], dtype=np.int32)}

                def batch_decode(self, tokens, skip_special_tokens=True):
                    captured["shape"] = tuple(tokens.shape)
                    return ["flat output"]

            class FlatModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, input_ids, attention_mask, **_kwargs):
                    captured["input_shape"] = tuple(input_ids.shape)
                    captured["mask_shape"] = tuple(attention_mask.shape)
                    return torch.tensor([[1, 2, 3, 4]], dtype=input_ids.dtype)

            adapter = module._TransformersChatAdapter(
                FlatModel(),
                FlatTokenizer(),
                None,
                "flat-mapping-inputs",
                {"n_ctx": 16},
            )
            response = adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
            )
            self.assertEqual(captured["input_shape"], (1, 3))
            self.assertEqual(captured["mask_shape"], (1, 3))
            self.assertEqual(captured["shape"], (1, 1))
            self.assertEqual(response["choices"][0]["message"]["content"], "flat output")

    def test_transformers_adapter_supports_keyword_only_tokenizer(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {}

            class KeywordTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return "keyword prompt"

                def __call__(self, *, text, return_tensors, **_kwargs):
                    captured["text"] = text
                    captured["return_tensors"] = return_tensors
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["keyword output"]

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **_kwargs):
                    return torch.tensor([[1, 2, 3]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                KeywordTokenizer(),
                None,
                "keyword-tokenizer",
                {"n_ctx": 16},
            )
            adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
            )
            self.assertEqual(captured["text"], "keyword prompt")
            self.assertEqual(captured["return_tensors"], "pt")

    def test_transformers_adapter_uses_natural_prompt_when_template_returns_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            captured = {}

            class EmptyTemplateTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return "   "

                def __call__(self, prompt, **_kwargs):
                    captured["prompt"] = prompt
                    return {"input_ids": torch.tensor([[1, 2]], dtype=torch.long)}

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["empty template output"]

            class TinyModel(torch.nn.Module):
                def __init__(self):
                    super().__init__()
                    self.anchor = torch.nn.Parameter(torch.zeros(1))

                def generate(self, **_kwargs):
                    return torch.tensor([[1, 2, 3]], dtype=torch.long)

            adapter = module._TransformersChatAdapter(
                TinyModel(),
                EmptyTemplateTokenizer(),
                None,
                "empty-template",
                {"n_ctx": 16},
            )
            adapter.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=4,
            )
            self.assertTrue(captured["prompt"].endswith("assistant:"))

    def test_transformers_adapter_supports_positional_vision_processor(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_nodes(Path(temp))
            image_buffer = io.BytesIO()
            module.Image.new("RGB", (1, 1), (255, 255, 0)).save(image_buffer, format="PNG")
            image_url = "data:image/png;base64," + base64.b64encode(image_buffer.getvalue()).decode("ascii")
            captured = {}

            class VisionTokenizer:
                pad_token_id = 0
                eos_token_id = 2

                def apply_chat_template(self, _messages, **_kwargs):
                    return "positional vision prompt"

                def batch_decode(self, _tokens, skip_special_tokens=True):
                    return ["positional vision output"]

            class PositionalProcessor(VisionTokenizer):
                image_processor = object()

                def __call__(self, *args, **kwargs):
                    if kwargs:
                        raise TypeError("legacy processor only accepts positional inputs")
                    text, images, return_tensors = args
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
                VisionTokenizer(),
                PositionalProcessor(),
                "positional-vision",
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
            self.assertEqual(captured["text"], "positional vision prompt")
            self.assertEqual(len(captured["images"]), 1)


if __name__ == "__main__":
    unittest.main()
