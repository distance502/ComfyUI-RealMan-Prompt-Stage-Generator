"""Unified model-call skill shared by local and API-backed refiners.

The stage generator deliberately keeps transport-specific details in the
model object.  This module owns the common contract around that object so
local GGUF, DashScope, Ollama and OpenAI-compatible clients are treated the
same way by image, video, smart-text and image-reverse paths.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable


MODEL_CALL_SKILL_NAME = "model-call"
MODEL_CALL_SKILL_VERSION = "1"


class ModelCallSkill:
    """Call a text-capable backend through one normalized conversation contract."""

    def __init__(
        self,
        *,
        resolve_backend: Callable[[Any], Any],
        resolve_system_prompt: Callable[[dict[str, Any]], str],
        compose_user_prompt: Callable[[str, dict[str, Any]], str],
        extract_text: Callable[[Any], str],
        clean_think_text: Callable[[str], str],
        sampling_params: Callable[[dict[str, Any], int], dict[str, Any]],
        chat_completion: Callable[..., Any],
    ) -> None:
        self._resolve_backend = resolve_backend
        self._resolve_system_prompt = resolve_system_prompt
        self._compose_user_prompt = compose_user_prompt
        self._extract_text = extract_text
        self._clean_think_text = clean_think_text
        self._sampling_params = sampling_params
        self._chat_completion = chat_completion

    @staticmethod
    def _call_flexible_method(method: Callable[..., Any], *, prompt: str, messages: list[dict[str, str]]) -> Any:
        try:
            signature = inspect.signature(method)
        except (TypeError, ValueError):
            signature = None
        parameters = signature.parameters if signature is not None else {}
        if "messages" in parameters:
            return method(messages=messages)
        return method(prompt)

    def _finish(self, response: Any, *, empty_message: str, settings: dict[str, Any], channel: str) -> str:
        text = str(self._extract_text(response) or "").strip()
        if not text:
            settings["模型调用Skill名称"] = MODEL_CALL_SKILL_NAME
            settings["模型调用Skill版本"] = MODEL_CALL_SKILL_VERSION
            settings["模型调用Skill状态"] = "失败"
            settings["模型调用Skill通道"] = channel
            settings["模型调用Skill错误"] = empty_message
            raise RuntimeError(empty_message)
        settings["模型调用Skill名称"] = MODEL_CALL_SKILL_NAME
        settings["模型调用Skill版本"] = MODEL_CALL_SKILL_VERSION
        settings["模型调用Skill通道"] = channel
        settings["模型调用Skill状态"] = "成功"
        settings["模型调用Skill错误"] = ""
        return self._clean_think_text(text)

    @staticmethod
    def _begin(settings: dict[str, Any]) -> None:
        settings["模型调用Skill名称"] = MODEL_CALL_SKILL_NAME
        settings["模型调用Skill版本"] = MODEL_CALL_SKILL_VERSION
        settings["模型调用Skill状态"] = "调用中"
        settings["模型调用Skill错误"] = ""

    def invoke(self, llm: Any, prompt: str, settings: dict[str, Any], *, prompt_count: int = 1) -> str:
        self._begin(settings)
        backend = self._resolve_backend(llm)
        system_prompt = self._resolve_system_prompt(settings)
        user_prompt = self._compose_user_prompt(prompt, settings)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        combined_prompt = f"{system_prompt}\n\n{user_prompt}".strip()

        if callable(getattr(backend, "create_chat_completion", None)):
            response = self._chat_completion(
                backend,
                messages=messages,
                params=self._sampling_params(settings, prompt_count),
            )
            return self._finish(response, empty_message="模型 API 返回空文本。", settings=settings, channel="chat_completion")

        if callable(getattr(backend, "invoke", None)):
            return self._finish(
                backend.invoke(combined_prompt),
                empty_message="模型返回空文本。",
                settings=settings,
                channel="invoke",
            )

        if callable(getattr(backend, "generate_content", None)):
            return self._finish(
                backend.generate_content(combined_prompt),
                empty_message="模型返回空文本。",
                settings=settings,
                channel="generate_content",
            )

        for method_name in ("complete", "predict", "chat"):
            method = getattr(backend, method_name, None)
            if not callable(method):
                continue
            response = self._call_flexible_method(method, prompt=combined_prompt, messages=messages)
            return self._finish(
                response,
                empty_message=f"模型 {method_name} 返回空文本。",
                settings=settings,
                channel=method_name,
            )

        if callable(backend):
            return self._finish(
                backend(combined_prompt),
                empty_message="可调用模型返回空文本。",
                settings=settings,
                channel="callable",
            )

        raise RuntimeError(
            "当前模型对象不支持 create_chat_completion、invoke、generate_content、complete、predict、chat 或可调用文本接口。"
        )

    def invoke_messages(
        self,
        llm: Any,
        messages: list[dict[str, Any]],
        settings: dict[str, Any],
        *,
        params: dict[str, Any] | None = None,
        force_chat_completion: bool = False,
    ) -> str:
        """Run a caller-owned message list, including multimodal content."""

        self._begin(settings)
        backend = self._resolve_backend(llm)
        if force_chat_completion or callable(getattr(backend, "create_chat_completion", None)):
            response = self._chat_completion(
                backend,
                messages=messages,
                params=dict(params or {}),
            )
            return self._finish(response, empty_message="模型 API 返回空文本。", settings=settings, channel="chat_completion")

        text_parts: list[str] = []
        for message in messages:
            content = message.get("content") if isinstance(message, dict) else message
            if isinstance(content, str) and content.strip():
                text_parts.append(content.strip())
            elif isinstance(content, list):
                text_parts.extend(
                    str(part.get("text") or "").strip()
                    for part in content
                    if isinstance(part, dict) and str(part.get("text") or "").strip()
                )
        combined_prompt = "\n\n".join(text_parts).strip()
        if callable(getattr(backend, "invoke", None)):
            return self._finish(backend.invoke(combined_prompt), empty_message="模型返回空文本。", settings=settings, channel="invoke")
        if callable(getattr(backend, "generate_content", None)):
            return self._finish(backend.generate_content(combined_prompt), empty_message="模型返回空文本。", settings=settings, channel="generate_content")
        raise RuntimeError("当前模型对象不支持带消息列表的模型调用。")
