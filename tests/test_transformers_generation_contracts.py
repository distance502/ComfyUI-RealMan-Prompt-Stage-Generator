"""Offline EOS and independent encoder/decoder generation regressions."""
from __future__ import annotations

import tempfile
import types
import unittest
from pathlib import Path

import torch

from test_raw_model_support import load_nodes


class TestTransformersGenerationContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.nodes = load_nodes(Path(self.temp.name))

    def adapter(self, *, count=2, config=None, generation_config=None,
                tokenizer_limit=None, decoder_prefix=None, context=16):
        class Tokenizer:
            pad_token_id = 0
            eos_token_id = 2
            model_max_length = tokenizer_limit

            def apply_chat_template(self, *_args, **_kwargs):
                if decoder_prefix is not None:
                    return {
                        "input_ids": torch.arange(10, 10 + count).unsqueeze(0),
                        "decoder_input_ids": torch.tensor([decoder_prefix]),
                    }
                return "synthetic encoder input"

            def __call__(self, *_args, **_kwargs):
                # A legacy tokenizer intentionally ignores truncation options.
                return {"input_ids": torch.arange(10, 10 + count).unsqueeze(0)}

            def batch_decode(self, tokens, **_kwargs):
                self.decoded = tokens.clone()
                return ["synthetic answer"]

        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.anchor = torch.nn.Parameter(torch.zeros(1))
                self.config = config or types.SimpleNamespace(is_encoder_decoder=False)
                self.generation_config = generation_config
                self.calls = []

            def generate(self, input_ids, **kwargs):
                self.calls.append({"input_ids": input_ids, **kwargs})
                answer = torch.tensor([[7, 8]])
                if getattr(self.config, "is_encoder_decoder", False):
                    return answer
                return torch.cat((input_ids, answer), dim=-1)

        model = Model()
        return self.nodes._TransformersChatAdapter(
            model, Tokenizer(), None, "synthetic-generation", {"n_ctx": context}
        )

    @staticmethod
    def generate(adapter, max_tokens=8, **kwargs):
        return adapter.create_chat_completion(
            [{"role": "user", "content": "describe one object"}],
            max_tokens=max_tokens, temperature=0, **kwargs,
        )

    def test_native_multiple_eos_are_preserved_over_tokenizer_single_eos(self):
        native_eos = [2, 3]
        config = types.SimpleNamespace(eos_token_id=4)
        generation_config = types.SimpleNamespace(eos_token_id=native_eos)
        adapter = self.adapter(config=config, generation_config=generation_config)
        self.generate(adapter)
        self.assertEqual(adapter.model.calls[0]["eos_token_id"], [2, 3])
        self.assertEqual(generation_config.eos_token_id, [2, 3])
        self.assertEqual(adapter.tokenizer.eos_token_id, 2)

    def test_model_config_eos_then_tokenizer_remain_fallbacks(self):
        cases = (
            (types.SimpleNamespace(eos_token_id=[3, 4]), [3, 4]),
            (types.SimpleNamespace(eos_token_id=0), 0),
            (types.SimpleNamespace(eos_token_id=None), 2),
        )
        for config, expected in cases:
            with self.subTest(expected=expected):
                adapter = self.adapter(
                    config=config, generation_config=types.SimpleNamespace(eos_token_id=None),
                )
                self.generate(adapter)
                self.assertEqual(adapter.model.calls[0]["eos_token_id"], expected)

    def test_explicit_call_eos_override_wins_including_none_and_zero(self):
        for override in (None, 0, [9, 10]):
            with self.subTest(override=override):
                generation_config = types.SimpleNamespace(eos_token_id=[2, 3])
                adapter = self.adapter(generation_config=generation_config)
                self.generate(adapter, eos_token_id=override)
                self.assertIn("eos_token_id", adapter.model.calls[0])
                self.assertEqual(adapter.model.calls[0]["eos_token_id"], override)
                self.assertEqual(generation_config.eos_token_id, [2, 3])

    def test_seq2seq_long_encoder_does_not_consume_decoder_output_budget(self):
        for count, expected_count in ((15, 15), (16, 16), (18, 16)):
            with self.subTest(encoder_tokens=count):
                adapter = self.adapter(
                    count=count,
                    config=types.SimpleNamespace(is_encoder_decoder=True, max_position_embeddings=16),
                )
                self.generate(adapter, max_tokens=8)
                self.assertEqual(adapter.model.calls[0]["input_ids"].shape[-1], expected_count)
                self.assertEqual(adapter.model.calls[0]["max_new_tokens"], 8)
                self.assertEqual(adapter.tokenizer.decoded.tolist(), [[7, 8]])

    def test_seq2seq_reserves_decoder_start_token(self):
        adapter = self.adapter(
            count=15,
            config=types.SimpleNamespace(is_encoder_decoder=True, max_position_embeddings=16),
        )
        self.generate(adapter, max_tokens=30)
        self.assertEqual(adapter.model.calls[0]["max_new_tokens"], 15)

    def test_seq2seq_nested_encoder_and_decoder_limits_are_independent(self):
        config = types.SimpleNamespace(
            is_encoder_decoder=True,
            encoder=types.SimpleNamespace(max_position_embeddings=24),
            decoder=types.SimpleNamespace(max_position_embeddings=12),
        )
        adapter = self.adapter(count=20, config=config, context=64)
        self.generate(adapter, max_tokens=20)
        self.assertEqual(adapter.model.calls[0]["input_ids"].shape[-1], 20)
        self.assertEqual(adapter.model.calls[0]["max_new_tokens"], 11)

    def test_tokenizer_source_limit_does_not_constrain_decoder(self):
        adapter = self.adapter(
            count=12, tokenizer_limit=6,
            config=types.SimpleNamespace(is_encoder_decoder=True, max_position_embeddings=32),
        )
        self.generate(adapter, max_tokens=10)
        self.assertEqual(adapter.model.calls[0]["input_ids"].shape[-1], 6)
        self.assertEqual(adapter.model.calls[0]["max_new_tokens"], 10)

    def test_source_and_target_specific_metadata_are_honored(self):
        adapter = self.adapter(
            count=15, context=64,
            config=types.SimpleNamespace(
                is_encoder_decoder=True, max_source_positions=12, max_target_positions=5,
            ),
        )
        self.generate(adapter, max_tokens=20)
        self.assertEqual(adapter.model.calls[0]["input_ids"].shape[-1], 12)
        self.assertEqual(adapter.model.calls[0]["max_new_tokens"], 4)

    def test_decoder_prefix_budget_includes_start_token_if_missing(self):
        for prefix in ([1, 6, 7], [6, 7]):
            with self.subTest(prefix=prefix):
                adapter = self.adapter(
                    count=15, decoder_prefix=prefix,
                    config=types.SimpleNamespace(is_encoder_decoder=True, max_position_embeddings=12),
                    generation_config=types.SimpleNamespace(decoder_start_token_id=1),
                )
                self.generate(adapter, max_tokens=20)
                self.assertEqual(adapter.model.calls[0]["max_new_tokens"], 9)

    def test_decoder_prefix_that_fills_window_is_rejected_before_generate(self):
        adapter = self.adapter(
            decoder_prefix=[1, 6, 7, 8],
            config=types.SimpleNamespace(is_encoder_decoder=True, max_position_embeddings=4),
            generation_config=types.SimpleNamespace(decoder_start_token_id=1),
        )
        with self.assertRaisesRegex(ValueError, "已占满解码器上下文 4 token"):
            self.generate(adapter)
        self.assertEqual(adapter.model.calls, [])

    def test_causal_input_output_budget_remains_shared(self):
        adapter = self.adapter(
            count=15,
            config=types.SimpleNamespace(is_encoder_decoder=False, max_position_embeddings=16),
        )
        self.generate(adapter)
        self.assertEqual(adapter.model.calls[0]["max_new_tokens"], 1)
        self.assertEqual(adapter.tokenizer.decoded.tolist(), [[7, 8]])


if __name__ == "__main__":
    unittest.main()
