"""Synthetic local-backend regressions; no model weights or CUDA allocation."""
from __future__ import annotations

import base64
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import torch

from test_raw_model_support import load_nodes


class TestLocalModelRuntimeReliability(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.nodes = load_nodes(Path(self.temp.name))

    def tokenizer(self, token_ids=(1, 2)):
        class Tokenizer:
            pad_token_id = 0
            eos_token_id = 2

            def apply_chat_template(self, *args, **kwargs):
                return "a synthetic prompt"

            def __call__(self, *args, **kwargs):
                # Simulate a legacy encoder that ignores max_length.
                return {
                    "input_ids": torch.tensor([list(token_ids)], dtype=torch.long),
                    "attention_mask": torch.ones((1, len(token_ids)), dtype=torch.long),
                }

            def batch_decode(self, *args, **kwargs):
                return ["synthetic output"]

        return Tokenizer()

    def model(self):
        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.anchor = torch.nn.Parameter(torch.zeros(1))
                self.calls = []

            def generate(self, input_ids, **kwargs):
                self.calls.append({"input_ids": input_ids, **kwargs})
                token = torch.tensor([[7]], dtype=input_ids.dtype)
                return torch.cat((input_ids, token), dim=-1)

        return Model()

    @staticmethod
    def encoded_vision():
        return {
            "input_ids": torch.tensor([[99, 99, 99, 99, 99, 99, 1]], dtype=torch.long),
            "attention_mask": torch.ones((1, 7), dtype=torch.long),
            "pixel_values": torch.ones((6, 3)),
            "image_grid_thw": torch.tensor([[1, 2, 3]], dtype=torch.long),
        }

    def image_messages(self):
        buffer = io.BytesIO()
        self.nodes.Image.new("RGB", (1, 1), "white").save(buffer, format="PNG")
        url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
        return [{"role": "user", "content": [
            {"type": "text", "text": "describe this synthetic object"},
            {"type": "image_url", "image_url": {"url": url}},
        ]}]

    def test_raw_model_cpu_selection_preserves_numeric_zero_with_cuda_available(self):
        with mock.patch.object(self.nodes.torch.cuda, "is_available", return_value=True):
            for value, expected in ((0, None), ("0", None), (-1, "auto"), (None, "auto")):
                with self.subTest(n_gpu_layers=value):
                    options = self.nodes._原始模型加载参数({"n_gpu_layers": value})
                    self.assertEqual(options["device_map"], expected)

    def test_raw_model_unavailable_cuda_and_explicit_device_map_keep_existing_behavior(self):
        with mock.patch.object(self.nodes.torch.cuda, "is_available", return_value=False):
            for value in (0, "0", -1, None):
                with self.subTest(n_gpu_layers=value):
                    self.assertIsNone(self.nodes._原始模型加载参数({"n_gpu_layers": value})["device_map"])
        with mock.patch.object(self.nodes.torch.cuda, "is_available", return_value=True):
            options = self.nodes._原始模型加载参数({
                "n_gpu_layers": 0,
                "custom_llama_params": {"device_map": "auto"},
            })
            self.assertEqual(options["device_map"], "auto")

    def test_oversized_visual_prompt_is_rejected_before_generate_without_slicing_media(self):
        encoded = self.encoded_vision()
        snapshots = {key: value.clone() for key, value in encoded.items()}

        class Processor:
            image_processor = object()

            def __init__(self):
                self.calls = []

            def __call__(self, *args, **kwargs):
                self.calls.append(kwargs)
                return encoded

        processor = Processor()
        model = self.model()
        adapter = self.nodes._TransformersChatAdapter(model, self.tokenizer(), processor, "mock-vision", {"n_ctx": 5})
        with self.assertRaises(ValueError) as error:
            adapter.create_chat_completion(self.image_messages(), max_tokens=20, temperature=0)
        self.assertIn("完整输入需要 7 token", str(error.exception))
        self.assertIn("输入预算为 4 token", str(error.exception))
        self.assertIn("至少 8 token 上下文", str(error.exception))
        self.assertEqual(model.calls, [])
        self.assertEqual(len(processor.calls), 1)
        self.assertIs(processor.calls[0]["truncation"], False)
        self.assertNotIn("max_length", processor.calls[0])
        for key in snapshots:
            self.assertTrue(torch.equal(encoded[key], snapshots[key]), key)

    def test_visual_prompt_exact_budget_preserves_media_and_one_output_token(self):
        encoded = self.encoded_vision()
        processor = mock.Mock(image_processor=object(), model_input_names=[], return_value=encoded)
        model = self.model()
        adapter = self.nodes._TransformersChatAdapter(model, self.tokenizer(), processor, "mock-vision", {"n_ctx": 8})
        # Use a real tokenizer template, not a Mock-generated placeholder.
        processor.apply_chat_template = None
        response = adapter.create_chat_completion(self.image_messages(), max_tokens=20, temperature=0)
        self.assertEqual(response["choices"][0]["message"]["content"], "synthetic output")
        self.assertEqual(model.calls[0]["max_new_tokens"], 1)
        self.assertEqual(int((model.calls[0]["input_ids"] == 99).sum()), 6)
        self.assertEqual(model.calls[0]["pixel_values"].shape[0], 6)
        for key, value in encoded.items():
            self.assertTrue(torch.equal(model.calls[0][key], value), key)

    def test_preencoded_multimodal_template_checks_budget_without_processor_or_mutation(self):
        encoded = self.encoded_vision()
        snapshots = {key: value.clone() for key, value in encoded.items()}
        processor = mock.Mock(image_processor=object(), model_input_names=[])
        adapter = self.nodes._TransformersChatAdapter(self.model(), self.tokenizer(), processor, "mock-vision", {"n_ctx": 8})
        with self.assertRaisesRegex(ValueError, "完整输入需要 7 token"):
            adapter._encode_multimodal(processor, encoded, [], max_length=6)
        result = adapter._encode_multimodal(processor, encoded, [], max_length=7)
        processor.assert_not_called()
        for key in snapshots:
            self.assertTrue(torch.equal(encoded[key], snapshots[key]), key)
            self.assertTrue(torch.equal(result[key], snapshots[key]), key)

    def test_legacy_visual_processor_without_truncation_keyword_still_works(self):
        encoded = self.encoded_vision()

        class LegacyProcessor:
            image_processor = object()

            def __call__(self, text, images, return_tensors):
                return encoded

        processor = LegacyProcessor()
        adapter = self.nodes._TransformersChatAdapter(self.model(), self.tokenizer(), processor, "mock-vision", {"n_ctx": 8})
        result = adapter._encode_multimodal(processor, "prompt", [], max_length=7)
        self.assertTrue(torch.equal(result["input_ids"], encoded["input_ids"]))
        self.assertTrue(torch.equal(result["pixel_values"], encoded["pixel_values"]))

    def test_plain_text_truncation_and_requested_output_budget_are_unchanged(self):
        cases = (
            (5, (1, 2, 3, 4, 5, 6), 20, [3, 4, 5, 6], 1),
            (8, (1, 2), 3, [1, 2], 3),
        )
        for context, token_ids, requested, expected_ids, expected_output in cases:
            with self.subTest(context=context, prompt_tokens=len(token_ids)):
                model = self.model()
                adapter = self.nodes._TransformersChatAdapter(model, self.tokenizer(token_ids), None, "mock-text", {"n_ctx": context})
                adapter.create_chat_completion([{"role": "user", "content": "a text prompt"}], max_tokens=requested, temperature=0)
                self.assertEqual(model.calls[0]["input_ids"].tolist(), [expected_ids])
                self.assertEqual(model.calls[0]["attention_mask"].shape[-1], len(expected_ids))
                self.assertEqual(model.calls[0]["max_new_tokens"], expected_output)


if __name__ == "__main__":
    unittest.main()
