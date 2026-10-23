"""Opaque backend compatibility retries must not repeat backend business errors."""
from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stage_prompt.model_call_skill import ModelCallSkill


def make_skill():
    return ModelCallSkill(
        resolve_backend=lambda value: value,
        resolve_system_prompt=lambda _settings: "system contract",
        compose_user_prompt=lambda prompt, _settings: prompt,
        extract_text=lambda response: response["content"],
        clean_think_text=lambda text: text,
        sampling_params=lambda _settings, _count: {"max_tokens": 32},
        chat_completion=lambda *_args, **_kwargs: None,
    )


class TestOpaqueBindingErrors(unittest.TestCase):
    def test_internal_decoder_binding_error_is_not_a_backend_call_shape_error(self):
        class Backend:
            __signature__ = "opaque"
            calls = 0

            def __call__(self, *args, **kwargs):
                self.calls += 1

                def decode(value):
                    return value

                return decode("response", "unexpected")

        backend = Backend()
        with self.assertRaisesRegex(TypeError, "positional argument"):
            make_skill().invoke(backend, "mechanical clock", {})
        self.assertEqual(backend.calls, 1)

    def test_internal_error_mentioning_unsupported_keyword_is_not_retried(self):
        class Backend:
            __signature__ = "opaque"
            calls = 0

            def __call__(self, *args, **kwargs):
                self.calls += 1
                raise TypeError("decoder got an unexpected keyword argument 'pixel_values'")

        backend = Backend()
        with self.assertRaisesRegex(TypeError, "pixel_values"):
            make_skill().invoke(backend, "mechanical clock", {})
        self.assertEqual(backend.calls, 1)

    def test_true_binding_errors_still_allow_legacy_prompt_only_backend(self):
        class Backend:
            __signature__ = "opaque"

            def __init__(self):
                self.calls = []

            def __call__(self, prompt):
                self.calls.append(prompt)
                return {"content": "usable reply"}

        backend = Backend()
        self.assertEqual(make_skill().invoke(backend, "mechanical clock", {}), "usable reply")
        self.assertEqual(backend.calls, ["system contract\n\nmechanical clock"])

    def test_prompt_fallback_keeps_sampling_when_backend_accepts_it(self):
        class Backend:
            __signature__ = "opaque"

            def __init__(self):
                self.calls = []

            def __call__(self, prompt, **kwargs):
                self.calls.append((prompt, kwargs))
                return {"content": "usable reply"}

        backend = Backend()
        self.assertEqual(make_skill().invoke(backend, "mechanical clock", {}), "usable reply")
        self.assertEqual(backend.calls, [("system contract\n\nmechanical clock", {"max_tokens": 32})])


if __name__ == "__main__":
    unittest.main()
