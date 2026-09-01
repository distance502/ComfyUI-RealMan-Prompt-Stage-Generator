from __future__ import annotations

import unittest
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from stage_prompt.model_call_skill import ModelCallSkill


class _LocalBackend:
    def create_chat_completion(self, **kwargs):
        return {"choices": [{"message": {"content": "<think>hidden</think>local result"}}]}


class _ApiBackend:
    def invoke(self, prompt):
        return {"content": f"api result: {prompt.splitlines()[-1]}"}


class _EmptyBackend:
    def invoke(self, _prompt):
        return {"content": ""}


class _KwargsBackend:
    def __init__(self):
        self.calls = []

    def invoke(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return {"content": "kwargs result"}


class _KwargsOnlyBackend:
    def __init__(self):
        self.calls = []

    def invoke(self, **kwargs):
        self.calls.append(kwargs)
        return {"content": "kwargs-only result"}


class _PositionalOnlyBackend:
    def __init__(self):
        self.calls = []

    def invoke(self, prompt, /, **kwargs):
        self.calls.append((prompt, kwargs))
        return {"content": "positional-only result"}


class _PositionalOnlySamplingBackend:
    def __init__(self):
        self.calls = []

    def invoke(self, prompt, max_new_tokens, repetition_penalty, /):
        self.calls.append((prompt, max_new_tokens, repetition_penalty))
        return {"content": "positional-only sampling result"}


class _PromptBeforeOptionalMessagesBackend:
    def __init__(self):
        self.calls = []

    def invoke(self, prompt, messages=None, **kwargs):
        self.calls.append((prompt, messages, kwargs))
        return {"content": "prompt-first result"}


class _QueryBackend:
    def __init__(self):
        self.calls = []

    def generate_content(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return {"content": "query result"}


class _InputsBackend:
    def __init__(self):
        self.calls = []

    def __call__(self, inputs):
        self.calls.append(inputs)
        return {"content": "inputs result"}


class _MultimodalPromptBackend:
    def __init__(self):
        self.calls = []

    def invoke(self, prompt, images=None):
        self.calls.append((prompt, images))
        return {"content": "multimodal result"}


class _CallableBackend:
    def __init__(self):
        self.calls = []

    def __call__(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return {"content": "callable result"}


class _OpaqueCallableBackend:
    __signature__ = "opaque"

    def __init__(self):
        self.calls = []

    def __call__(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return {"content": "opaque result"}


class _OpaqueFailureBackend:
    __signature__ = "opaque"

    def __init__(self):
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        raise TypeError("internal model failure")


class ModelCallSkillTests(unittest.TestCase):
    def _skill(self, calls):
        def extract(response):
            if isinstance(response, dict) and "choices" in response:
                return response["choices"][0]["message"]["content"]
            return response.get("content", "") if isinstance(response, dict) else str(response)

        return ModelCallSkill(
            resolve_backend=lambda value: value,
            resolve_system_prompt=lambda _settings: "system contract",
            compose_user_prompt=lambda prompt, _settings: prompt,
            extract_text=extract,
            clean_think_text=lambda text: text.replace("<think>hidden</think>", ""),
            sampling_params=lambda _settings, count: {"prompt_count": count},
            chat_completion=lambda backend, **kwargs: (calls.append(kwargs), backend.create_chat_completion(**kwargs))[1],
        )

    def test_local_chat_and_api_invoke_share_one_contract(self):
        calls = []
        skill = self._skill(calls)
        local_settings = {}
        api_settings = {}

        self.assertEqual(skill.invoke(_LocalBackend(), "local prompt", local_settings), "local result")
        self.assertEqual(skill.invoke(_ApiBackend(), "api prompt", api_settings), "api result: api prompt")
        self.assertEqual(local_settings["模型调用Skill通道"], "chat_completion")
        self.assertEqual(api_settings["模型调用Skill通道"], "invoke")
        self.assertEqual(local_settings["模型调用Skill版本"], "1")
        self.assertEqual(local_settings["模型调用Skill状态"], "成功")
        self.assertEqual(calls[0]["params"], {"prompt_count": 1})

    def test_empty_response_keeps_failure_diagnostics(self):
        skill = self._skill([])
        settings = {}
        with self.assertRaisesRegex(RuntimeError, "模型返回空文本"):
            skill.invoke(_EmptyBackend(), "empty prompt", settings)
        self.assertEqual(settings["模型调用Skill状态"], "失败")
        self.assertEqual(settings["模型调用Skill通道"], "invoke")

    def test_multimodal_messages_use_chat_completion_without_rebuilding_content(self):
        calls = []
        skill = self._skill(calls)
        settings = {}
        messages = [{"role": "user", "content": [{"type": "text", "text": "image facts"}, {"type": "image_url", "image_url": {"url": "data:"}}]}]
        result = skill.invoke_messages(_LocalBackend(), messages, settings, params={"max_tokens": 8})
        self.assertEqual(result, "local result")
        self.assertEqual(calls[0]["messages"], messages)
        self.assertEqual(calls[0]["params"], {"max_tokens": 8})

    def test_invoke_forwards_sampling_params_to_var_keyword_backend(self):
        skill = self._skill([])
        backend = _KwargsBackend()
        settings = {}
        result = skill.invoke(backend, "kwargs prompt", settings)
        self.assertEqual(result, "kwargs result")
        self.assertEqual(backend.calls[0][0], "system contract\n\nkwargs prompt")
        self.assertEqual(backend.calls[0][1], {"prompt_count": 1})

    def test_invoke_supports_backend_with_only_var_keyword_signature(self):
        skill = self._skill([])
        backend = _KwargsOnlyBackend()
        settings = {}
        result = skill.invoke(backend, "kwargs-only prompt", settings)
        self.assertEqual(result, "kwargs-only result")
        self.assertEqual(
            backend.calls[0],
            {"prompt": "system contract\n\nkwargs-only prompt", "prompt_count": 1},
        )

    def test_invoke_supports_positional_only_prompt_with_kwargs(self):
        skill = self._skill([])
        backend = _PositionalOnlyBackend()
        result = skill.invoke(backend, "positional prompt", {})
        self.assertEqual(result, "positional-only result")
        self.assertEqual(
            backend.calls[0],
            ("system contract\n\npositional prompt", {"prompt_count": 1}),
        )

    def test_invoke_maps_sampling_aliases_to_positional_only_parameters(self):
        skill = self._skill([])
        skill._sampling_params = lambda _settings, _count: {
            "max_tokens": 7,
            "repeat_penalty": 1.2,
        }
        backend = _PositionalOnlySamplingBackend()
        result = skill.invoke(
            backend,
            "positional sampling prompt",
            {},
        )
        self.assertEqual(result, "positional-only sampling result")
        self.assertEqual(
            backend.calls[0],
            ("system contract\n\npositional sampling prompt", 7, 1.2),
        )

    def test_invoke_prefers_required_prompt_before_optional_messages(self):
        skill = self._skill([])
        backend = _PromptBeforeOptionalMessagesBackend()
        result = skill.invoke(backend, "prompt-first", {})
        self.assertEqual(result, "prompt-first result")
        self.assertEqual(
            backend.calls[0],
            ("system contract\n\nprompt-first", None, {"prompt_count": 1}),
        )

    def test_invoke_supports_common_query_parameter_name(self):
        skill = self._skill([])
        backend = _QueryBackend()
        result = skill.invoke(backend, "query prompt", {})
        self.assertEqual(result, "query result")
        self.assertEqual(
            backend.calls[0],
            ("system contract\n\nquery prompt", {"prompt_count": 1}),
        )

    def test_invoke_supports_inputs_parameter_name(self):
        skill = self._skill([])
        backend = _InputsBackend()
        result = skill.invoke(backend, "inputs prompt", {})
        self.assertEqual(result, "inputs result")
        self.assertEqual(backend.calls, ["system contract\n\ninputs prompt"])

    def test_invoke_messages_forwards_media_to_prompt_backend(self):
        skill = self._skill([])
        backend = _MultimodalPromptBackend()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "describe this"},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
                ],
            }
        ]
        result = skill.invoke_messages(backend, messages, {}, params={"prompt_count": 1})
        self.assertEqual(result, "multimodal result")
        self.assertEqual(backend.calls[0][0], "describe this")
        self.assertEqual(backend.calls[0][1], ["data:image/png;base64,abc"])

    def test_invoke_messages_supports_complete_and_callable_backends(self):
        messages = [{"role": "user", "content": "message prompt"}]
        complete_backend = type(
            "CompleteBackend",
            (),
            {"complete": lambda self, prompt, **kwargs: {"content": f"complete:{prompt}"}},
        )()
        skill = self._skill([])
        self.assertEqual(skill.invoke_messages(complete_backend, messages, {}, params={"prompt_count": 1}), "complete:message prompt")

        callable_backend = _CallableBackend()
        self.assertEqual(skill.invoke_messages(callable_backend, messages, {}, params={"prompt_count": 1}), "callable result")
        self.assertEqual(callable_backend.calls[0][1], {"prompt_count": 1})

    def test_invoke_callable_backend_receives_sampling_params(self):
        backend = _CallableBackend()
        result = self._skill([]).invoke(backend, "callable prompt", {})
        self.assertEqual(result, "callable result")
        self.assertEqual(backend.calls[0][1], {"prompt_count": 1})

    def test_invoke_opaque_callable_retries_with_positional_prompt(self):
        backend = _OpaqueCallableBackend()
        result = self._skill([]).invoke(backend, "opaque prompt", {})
        self.assertEqual(result, "opaque result")
        self.assertEqual(backend.calls[0][0], "system contract\n\nopaque prompt")
        self.assertEqual(backend.calls[0][1], {"prompt_count": 1})

    def test_invoke_opaque_callable_does_not_retry_internal_type_error(self):
        backend = _OpaqueFailureBackend()
        with self.assertRaisesRegex(TypeError, "internal model failure"):
            self._skill([]).invoke(backend, "opaque failure", {})
        self.assertEqual(backend.calls, 1)


if __name__ == "__main__":
    unittest.main()
