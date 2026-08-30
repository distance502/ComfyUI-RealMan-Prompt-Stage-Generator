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


def _is_argument_binding_type_error(error: TypeError) -> bool:
    """Identify TypeErrors caused by a call shape, not backend business logic."""

    message = str(error or "").casefold()
    return any(
        marker in message
        for marker in (
            "unexpected keyword argument",
            "got an unexpected keyword",
            "missing required positional argument",
            "required positional argument",
            "positional-only argument",
            "takes ",
            "got multiple values for argument",
        )
    )


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
    def _call_flexible_method(
        method: Callable[..., Any],
        *,
        prompt: str,
        messages: list[dict[str, str]],
        params: dict[str, Any] | None = None,
    ) -> Any:
        try:
            signature = inspect.signature(method)
        except (TypeError, ValueError):
            signature = None
        if signature is None:
            # C-extension callables and some proxy objects do not expose a
            # signature. Try the richest chat form first, then a positional
            # prompt, and finally the legacy prompt-only form for wrappers
            # that reject generation controls. This keeps opaque backends
            # usable without masking a successful first call.
            opaque_params = dict(params or {})
            try:
                return method(messages=messages, **opaque_params)
            except TypeError as first_error:
                if not _is_argument_binding_type_error(first_error):
                    raise
                try:
                    return method(prompt, **opaque_params)
                except TypeError as second_error:
                    if not _is_argument_binding_type_error(second_error):
                        raise
                    return method(prompt)
        parameters = signature.parameters if signature is not None else {}
        accepts_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )
        accepted: dict[str, Any] = {}
        positional_values: dict[str, Any] = {}
        aliases = {
            "max_tokens": "max_new_tokens",
            "repeat_penalty": "repetition_penalty",
        }
        for name, value in dict(params or {}).items():
            candidates = (name, aliases.get(name, ""))
            bound = False
            for candidate in candidates:
                parameter = parameters.get(candidate)
                if parameter is None or parameter.kind == inspect.Parameter.VAR_POSITIONAL:
                    continue
                if parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
                    positional_values[candidate] = value
                else:
                    accepted[candidate] = value
                bound = True
                break
            if not bound:
                # Opaque wrappers commonly expose ``invoke(prompt, **kwargs)``
                # or ``generate_content(**kwargs)``. Preserve the sampling
                # contract for those wrappers instead of silently dropping all
                # optional generation controls.
                if accepts_kwargs:
                    accepted[name] = value

        def call_positional(primary_name: str, primary_value: Any) -> Any:
            """Fill a positional-only prefix without turning optional values into keywords."""

            args: list[Any] = []
            primary_found = False
            for parameter in parameters.values():
                if parameter.kind != inspect.Parameter.POSITIONAL_ONLY:
                    break
                if parameter.name == primary_name:
                    args.append(primary_value)
                    primary_found = True
                elif parameter.name in positional_values:
                    args.append(positional_values[parameter.name])
                elif parameter.default is not inspect.Parameter.empty:
                    args.append(parameter.default)
                else:
                    # An unrelated required positional argument cannot be
                    # inferred from the normalized chat contract. Let Python
                    # report the binding error instead of guessing a value.
                    break
            if not primary_found:
                args.append(primary_value)
            return method(*args, **accepted)

        message_parameter = parameters.get("messages")

        # A few wrappers expose both ``prompt`` and an optional ``messages``
        # argument, for example ``invoke(prompt, messages=None, **kwargs)``.
        # Supplying only ``messages=`` leaves the required prompt unbound and
        # produces a misleading fallback error. Use the message form only
        # when every positional parameter before it can be satisfied by a
        # default value.
        message_index = None
        if message_parameter is not None:
            parameter_names = list(parameters)
            try:
                message_index = parameter_names.index("messages")
            except ValueError:
                message_index = None
            if message_index is not None:
                required_prefix = [
                    parameter
                    for parameter in list(parameters.values())[:message_index]
                    if parameter.kind
                    in {
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    }
                    and parameter.default is inspect.Parameter.empty
                ]
                if required_prefix:
                    message_parameter = None

        if message_parameter is not None:
            if message_parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
                return call_positional("messages", messages)
            return method(messages=messages, **accepted)

        # Some generation wrappers call the text argument ``contents`` or
        # ``text`` instead of ``prompt``.  Prefer their explicit name while
        # retaining the original positional fallback for opaque callables.
        # ``context``/``query``/``instruction`` are common names in local
        # pipelines and hosted SDK adapters. They carry the same normalized
        # text contract as ``prompt`` and should not be mistaken for an
        # unsupported backend merely because the wrapper chose a different
        # parameter name.
        for argument_name in (
            "prompt",
            "contents",
            "text",
            "input",
            "context",
            "query",
            "input_text",
            "instruction",
            "question",
            "user_prompt",
        ):
            parameter = parameters.get(argument_name)
            if parameter is None:
                continue
            if parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
                return call_positional(argument_name, prompt)
            return method(**{argument_name: prompt, **accepted})
        if accepts_kwargs:
            return method(prompt=prompt, **accepted)
        return method(prompt, **accepted)

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
        sampling_params = self._sampling_params(settings, prompt_count)

        if callable(getattr(backend, "create_chat_completion", None)):
            response = self._chat_completion(
                backend,
                messages=messages,
                params=sampling_params,
            )
            return self._finish(response, empty_message="模型 API 返回空文本。", settings=settings, channel="chat_completion")

        if callable(getattr(backend, "invoke", None)):
            return self._finish(
                self._call_flexible_method(
                    backend.invoke,
                    prompt=combined_prompt,
                    messages=messages,
                    params=sampling_params,
                ),
                empty_message="模型返回空文本。",
                settings=settings,
                channel="invoke",
            )

        if callable(getattr(backend, "generate_content", None)):
            return self._finish(
                self._call_flexible_method(
                    backend.generate_content,
                    prompt=combined_prompt,
                    messages=messages,
                    params=sampling_params,
                ),
                empty_message="模型返回空文本。",
                settings=settings,
                channel="generate_content",
            )

        for method_name in ("complete", "predict", "chat"):
            method = getattr(backend, method_name, None)
            if not callable(method):
                continue
            response = self._call_flexible_method(
                method,
                prompt=combined_prompt,
                messages=messages,
                params=sampling_params,
            )
            return self._finish(
                response,
                empty_message=f"模型 {method_name} 返回空文本。",
                settings=settings,
                channel=method_name,
            )

        if callable(backend):
            return self._finish(
                self._call_flexible_method(
                    backend,
                    prompt=combined_prompt,
                    messages=messages,
                    params=sampling_params,
                ),
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
            return self._finish(
                self._call_flexible_method(
                    backend.invoke,
                    prompt=combined_prompt,
                    messages=messages,
                    params=dict(params or {}),
                ),
                empty_message="模型返回空文本。",
                settings=settings,
                channel="invoke",
            )
        if callable(getattr(backend, "generate_content", None)):
            return self._finish(
                self._call_flexible_method(
                    backend.generate_content,
                    prompt=combined_prompt,
                    messages=messages,
                    params=dict(params or {}),
                ),
                empty_message="模型返回空文本。",
                settings=settings,
                channel="generate_content",
            )

        for method_name in ("complete", "predict", "chat"):
            method = getattr(backend, method_name, None)
            if not callable(method):
                continue
            return self._finish(
                self._call_flexible_method(
                    method,
                    prompt=combined_prompt,
                    messages=messages,
                    params=dict(params or {}),
                ),
                empty_message=f"模型 {method_name} 返回空文本。",
                settings=settings,
                channel=method_name,
            )
        if callable(backend):
            return self._finish(
                self._call_flexible_method(
                    backend,
                    prompt=combined_prompt,
                    messages=messages,
                    params=dict(params or {}),
                ),
                empty_message="可调用模型返回空文本。",
                settings=settings,
                channel="callable",
            )
        raise RuntimeError("当前模型对象不支持带消息列表的模型调用。")
