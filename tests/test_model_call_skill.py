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


if __name__ == "__main__":
    unittest.main()
