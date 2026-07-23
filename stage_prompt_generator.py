# -*- coding: utf-8 -*-
"""Minimal rebuilt stage prompt generator."""

from __future__ import annotations

import json
import hashlib
import os
import random
import re
import secrets
import threading
import time
import weakref
import unicodedata
import urllib.parse
import urllib.request
from collections import OrderedDict
from contextlib import nullcontext
from copy import deepcopy
from typing import Any

try:
    import comfy.model_management as _comfy_mm
except Exception:  # pragma: no cover - focused tests may not load ComfyUI
    _comfy_mm = None

_NODE_TOOL_IMPORT_ERROR: Exception | None = None
try:
    from .nodes import _调用chat_completion, _清洗think块文本, _规范化随机种子, any_type
except Exception as exc:  # pragma: no cover - exercised through integration import tests
    _NODE_TOOL_IMPORT_ERROR = exc
    _NODE_TOOL_IMPORT_ERROR_TEXT = f"{type(exc).__name__}: {exc}"

    class AnyType(str):
        def __ne__(self, __value: object) -> bool:
            return False

    any_type = AnyType("*")

    def _调用chat_completion(_llm, *, messages, params: dict, _allow_recover: bool = True) -> dict:
        raise RuntimeError(
            "内置模型调用不可用：模型/图像节点依赖未完整加载。"
            f"原始错误：{_NODE_TOOL_IMPORT_ERROR_TEXT}"
        )

    def _清洗think块文本(text: str) -> str:
        if not isinstance(text, str) or not text:
            return "" if text is None else str(text)
        cleaned = re.sub(r"<think\b[^>]*>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        if re.search(r"</think>", cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(r"^.*?</think>\s*", "", cleaned, count=1, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.replace("<think>", "").replace("</think>", "")

    def _规范化随机种子(seed_value):
        try:
            seed_value = int(seed_value)
        except Exception:
            return None
        return None if seed_value < 0 else seed_value


class _StageModelAnyType(str):
    def __ne__(self, other: object) -> bool:
        return False


_STAGE_MODEL_ANY_TYPE = any_type if isinstance(any_type, str) else _StageModelAnyType("*")


try:
    from .nodes import _批量帧索引转data_url
except Exception:  # pragma: no cover - focused tests may stub .nodes
    def _批量帧索引转data_url(image_tensor, frame_indices: list[int], 最大边长: int) -> dict[int, str]:
        return {}

try:
    from .nodes import (
        KV缓存类型选项 as _内置模型KV缓存类型选项,
        TE通用模型系列选项 as _内置模型系列选项,
        _QwenStorage as _内置QwenStorage,
        _列出llm文件 as _列出内置llm文件,
        默认KV缓存类型 as _内置默认KV缓存类型,
    )
except Exception:  # pragma: no cover - focused tests may stub .nodes
    _内置模型系列选项 = ["Qwen3-VL", "Qwen3.5-VL", "Gemma4", "Llama", "Mistral", "DeepSeek", "通用GGUF"]
    _内置模型KV缓存类型选项 = ["默认(F16)", "q8_0"]
    _内置默认KV缓存类型 = "默认(F16)"
    _内置QwenStorage = None

    def _列出内置llm文件() -> list[str]:
        return []
from .prompt_tag_library import (
    DANBOORU_GENERAL_TAG_ALIASES,
    DANBOORU_REFERENCE_SHEET_BALANCE_TAGS,
    DANBOORU_REFERENCE_SHEET_BACKGROUND_TAGS,
    DANBOORU_REFERENCE_SHEET_DYNAMIC_TAGS,
    DANBOORU_REFERENCE_SHEET_TAGS,
    DANBOORU_VISUAL_INTENT_FAMILIES,
    分组配置,
    展平标签分类,
    模板推断关键词,
)
from .prompt_semantic_config import (
    服装主线标签集合,
    室内场景标签集合,
    极简背景标签集合,
    职业持物身份集合,
    城市街景标签集合,
    自然户外标签集合,
    工业科技标签集合,
    古风东方标签集合,
    神圣仪式标签集合,
    女性身份锚点集合,
    男性身份锚点集合,
    强设定身份锚点集合,
    强设定身份生活化服装冲突集合,
)
from .prompt_rule_config import (
    成人向标签关键词,
    成人向低遮挡标签集合,
    低遮挡附加负面词_ZH,
    低遮挡附加负面词_EN,
    成人向构图附加负面词_ZH,
    成人向构图附加负面词_EN,
    成人向附加负面词_ZH,
    成人向附加负面词_EN,
    主体复制附加负面词_ZH,
    主体复制附加负面词_EN,
    全局单帧附加负面词_ZH,
    全局单帧附加负面词_EN,
    单人构图附加负面词_ZH,
    单人构图附加负面词_EN,
    多主体构图附加负面词_ZH,
    多主体构图附加负面词_EN,
    多视图一致性附加负面词_ZH,
    多视图一致性附加负面词_EN,
    模板附加负面词_ZH,
    模板附加负面词_EN,
)
from .stage_prompt.negative_builder import (
    build_negative_prompt_from_state as _build_negative_prompt_from_state_impl,
)
from .stage_prompt.nsfw_mapper import (
    map_nsfw_workspace_to_stage_state as _map_nsfw_workspace_to_stage_state_impl,
    normalize_nsfw_workspace as _normalize_nsfw_workspace_impl,
)
from .stage_prompt.nsfw_presets import (
    NSFW_SELECTOR_FIELDS as _NSFW_SELECTOR_FIELDS,
    NSFW_WORKSPACE_SIGNAL_TERMS as _NSFW_WORKSPACE_SIGNAL_TERMS,
)
from .stage_prompt.nsfw_workspace import (
    build_nsfw_workspace_catalog as _build_nsfw_workspace_catalog_impl,
)
from .stage_prompt.formatter import (
    build_cache_payload as _build_cache_payload_impl,
    build_json_payload as _build_json_payload_impl,
    build_selected_tags_text as _build_selected_tags_text_impl,
)
from .stage_prompt.model_refiner import (
    DEFAULT_STAGE_PROMPT_SYSTEM_TEMPLATE,
    _record_model_call_result as _record_model_call_result_impl,
    build_global_creative_spine_contract as _build_global_creative_spine_contract_impl,
    extract_text as _extract_model_response_text_impl,
    is_natural_language_prompt as _is_natural_language_prompt_impl,
    maybe_model_refine as _maybe_model_refine_impl,
    maybe_model_refine_batch as _maybe_model_refine_batch_impl,
    maybe_model_refine_video as _maybe_model_refine_video_impl,
    reconcile_model_output_fallback as _reconcile_model_output_fallback_impl,
    sanitize_model_error as _sanitize_model_error_impl,
    stabilize_prompt_output as _stabilize_prompt_output_impl,
    summarize_global_creative_spine_contract as _summarize_global_creative_spine_contract_impl,
)
from .stage_prompt.character_sheet_skill import (
    apply_character_sheet_strategy as _apply_character_sheet_strategy_impl,
)
from .stage_prompt.normalizer import normalize_inference_state as _normalize_inference_state_impl
from .stage_prompt.prompt_builder import (
    _STYLE_POSITIVE_EXCLUSION_TERMS,
    build_prompt_list as _build_prompt_list_impl,
    format_grouped_summary as _format_grouped_summary_impl,
    format_sections as _format_sections_impl,
)
from .stage_prompt.randomizer import build_runtime_tags as _build_runtime_tags_impl
from .stage_prompt.randomizer import resolve_runtime_random_mode as _resolve_runtime_random_mode_impl
from .stage_prompt.smart_text import (
    apply_smart_text_to_state as _apply_smart_text_to_state_impl,
    build_smart_text_seed as _build_smart_text_seed_impl,
    build_smart_text_settings as _build_smart_text_settings_impl,
    fallback_smart_text as _fallback_smart_text_impl,
    sanitize_smart_text_prompt as _sanitize_smart_text_prompt_impl,
)
from .stage_prompt.state_builder import build_state_from_kwargs as _build_state_from_kwargs_impl
from .stage_prompt.fantasy_profiles import (
    FANTASY_TEMPLATE_OPTIONS,
    FANTASY_TEMPLATE_STYLE_VARIANTS,
    FANTASY_THEME_POOL_OPTIONS,
    FANTASY_THEME_VARIANTS,
)
from .stage_prompt.expanded_profiles import (
    EXPANDED_TEMPLATE_OPTIONS,
    EXPANDED_TEMPLATE_STYLE_VARIANTS,
    EXPANDED_THEME_POOL_OPTIONS,
    EXPANDED_THEME_VARIANTS,
)
from .stage_prompt.skills import TEMPLATE_STYLE_BASE_MAP, resolve_base_template_style
from .stage_prompt.tag_block_composer import (
    build_tag_block_prompt_list as _build_tag_block_prompt_list_impl,
    parse_tag_block_payload as _parse_tag_block_payload_impl,
    summarize_tag_block_payload as _summarize_tag_block_payload_impl,
)
from .stage_prompt.video_prompt_skill import (
    VIDEO_PROMPT_MODEL_SYSTEM_TEMPLATE as _VIDEO_PROMPT_MODEL_SYSTEM_TEMPLATE,
    VIDEO_PROMPT_SKILL_VERSION as _VIDEO_PROMPT_SKILL_VERSION,
    build_video_prompt as _build_video_prompt_impl,
    is_natural_video_prompt as _is_natural_video_prompt_impl,
    video_prompt_required_anchors as _video_prompt_required_anchors_impl,
)

NODE_CLASS_MAPPINGS: dict[str, Any] = {}
NODE_DISPLAY_NAME_MAPPINGS: dict[str, Any] = {}
_COOPERATIVE_WAIT_POLL_SECONDS = 0.25
_SEED_MAX = 0xFFFFFFFFFFFFFFFF


def _raise_if_comfy_interrupted() -> None:
    model_management = _comfy_mm
    checker = getattr(model_management, "processing_interrupted", None)
    if callable(checker) and bool(checker()):
        error_type = getattr(model_management, "InterruptProcessingException", RuntimeError)
        raise error_type()


class _ImageReverseInFlight:
    __slots__ = ("event", "result", "error", "started_at")

    def __init__(self) -> None:
        self.event = threading.Event()
        self.result = ""
        self.error: BaseException | None = None
        self.started_at = time.monotonic()


class _ImageReverseSingleflightGuard:
    __slots__ = ("cache_key", "flight", "leader")

    def __init__(self, cache_key: str) -> None:
        self.cache_key = cache_key
        self.flight: _ImageReverseInFlight | None = None
        self.leader = False

    def begin(self):
        return _begin_image_reverse_singleflight(self.cache_key, _guard=self)

    def finish(self, *, result: str = "", error: BaseException | None = None) -> None:
        flight = self.flight
        if not self.leader or flight is None:
            return
        self.leader = False
        _finish_image_reverse_singleflight(self.cache_key, flight, result=result, error=error)


class _RuntimeRandomPreviewReservation:
    __slots__ = ("node_key", "token", "marker")

    def __init__(self, node_key: str, token: str, marker: dict[str, Any]) -> None:
        self.node_key = node_key
        self.token = token
        self.marker = marker


class _RuntimeRandomPreviewTransaction:
    __slots__ = ("reservation", "closed")

    def __init__(self) -> None:
        self.reservation: _RuntimeRandomPreviewReservation | None = None
        self.closed = False

    def reserve(
        self,
        settings: dict[str, Any],
        selected: OrderedDict[str, list[str]] | dict[str, list[str]],
        custom_tags: list[str],
    ) -> dict[str, Any] | None:
        if self.closed or self.reservation is not None:
            return None
        reservation = _reserve_runtime_random_preview_marker(
            settings,
            selected,
            custom_tags,
            transaction=self,
        )
        if reservation is None:
            return None
        return reservation.marker

    def commit(self) -> None:
        if self.closed:
            return
        reservation = self.reservation
        if reservation is not None and not _commit_runtime_random_preview_reservation(reservation):
            raise RuntimeError("运行时随机预览令牌提交失败：预留状态已失效。")
        self.reservation = None
        self.closed = True

    def release(self) -> None:
        if self.closed:
            return
        reservation = self.reservation
        self.reservation = None
        self.closed = True
        if reservation is not None:
            _release_runtime_random_preview_reservation(reservation)


class _StageCacheTransaction:
    __slots__ = ("key", "bucket", "lock", "bound", "closed", "owns_key_lock", "owns_pin")

    def __init__(self) -> None:
        self.key = ""
        self.bucket: dict[str, Any] | None = None
        self.lock = None
        self.bound = False
        self.closed = False
        self.owns_key_lock = False
        self.owns_pin = False

    def bind(self, cache_key: str) -> None:
        if self.bound or self.closed:
            raise RuntimeError("阶段缓存事务已绑定或关闭。")
        key = str(cache_key or "").strip()
        self.bound = True
        self.key = key
        if not key:
            return
        lock = _cache_key_lock(key)
        acquired = False
        try:
            while not acquired:
                _raise_if_comfy_interrupted()
                try:
                    acquired = bool(lock.acquire(timeout=_COOPERATIVE_WAIT_POLL_SECONDS))
                except TypeError:
                    # Compatibility for test doubles and unusual lock adapters.
                    acquired = bool(lock.acquire())
            if not acquired:
                raise RuntimeError("阶段缓存事务无法获取节点锁。")
            _raise_if_comfy_interrupted()
            self.lock = lock
            self.owns_key_lock = True
            with _CACHE_LOCK:
                self.owns_pin = True
                _STAGE_CACHE_PINNED_KEYS.add(key)
                current = _CACHE.get(key)
                self.bucket = deepcopy(current) if isinstance(current, dict) else None
        except BaseException:
            if self.owns_pin:
                with _CACHE_LOCK:
                    _STAGE_CACHE_PINNED_KEYS.discard(key)
                self.owns_pin = False
            if acquired and not self.owns_key_lock:
                lock.release()
            else:
                self._finish_lock()
            raise

    def matches(self, cache_key: str) -> bool:
        return bool(self.bound and not self.closed and self.key and self.key == str(cache_key or "").strip())

    def get_bucket(self, *, create: bool = False) -> dict[str, Any] | None:
        if not self.bound or self.closed or not self.key:
            return None
        if self.bucket is None and create:
            self.bucket = {}
        return self.bucket

    def commit(self, preview_transaction: _RuntimeRandomPreviewTransaction) -> None:
        if self.closed:
            return
        if not self.key:
            preview_transaction.commit()
            self.closed = True
            return
        reservation = preview_transaction.reservation
        reservation_key = None
        try:
            with _CACHE_LOCK:
                if reservation is not None:
                    reservation_key = (reservation.node_key, reservation.token)
                    if reservation.node_key != self.key:
                        raise RuntimeError("运行时随机预览令牌与阶段缓存事务不匹配。")
                    if _RUNTIME_RANDOM_PREVIEW_RESERVATIONS.get(reservation_key) is not reservation:
                        raise RuntimeError("运行时随机预览令牌提交失败：预留状态已失效。")
                original_cache = _CACHE.copy()
                original_reservations = dict(_RUNTIME_RANDOM_PREVIEW_RESERVATIONS)
                original_pins = set(_STAGE_CACHE_PINNED_KEYS)
                original_preview_reservation = preview_transaction.reservation
                original_preview_closed = preview_transaction.closed
                original_closed = self.closed
                original_owns_pin = self.owns_pin
                try:
                    if reservation is not None:
                        cache = self.get_bucket(create=True)
                        if cache is None:
                            raise RuntimeError("运行时随机预览令牌提交失败：阶段缓存不可用。")
                        consumed = [
                            str(item)
                            for item in cache.get("consumed_runtime_random_preview_tokens", [])
                            if str(item)
                        ]
                        cache["consumed_runtime_random_preview_tokens"] = [
                            reservation.token,
                            *[token for token in consumed if token != reservation.token],
                        ][:_RUNTIME_RANDOM_PREVIEW_TOKEN_LIMIT]
                    if self.bucket is not None:
                        _CACHE[self.key] = self.bucket
                        _CACHE.move_to_end(self.key)
                    if reservation_key is not None:
                        del _RUNTIME_RANDOM_PREVIEW_RESERVATIONS[reservation_key]
                    if self.owns_pin:
                        _STAGE_CACHE_PINNED_KEYS.discard(self.key)
                        self.owns_pin = False
                    _prune_stage_cache_unlocked()
                    preview_transaction.reservation = None
                    preview_transaction.closed = True
                    self.closed = True
                except BaseException:
                    _CACHE.clear()
                    _CACHE.update(original_cache)
                    _RUNTIME_RANDOM_PREVIEW_RESERVATIONS.clear()
                    _RUNTIME_RANDOM_PREVIEW_RESERVATIONS.update(original_reservations)
                    _STAGE_CACHE_PINNED_KEYS.clear()
                    _STAGE_CACHE_PINNED_KEYS.update(original_pins)
                    preview_transaction.reservation = original_preview_reservation
                    preview_transaction.closed = original_preview_closed
                    self.closed = original_closed
                    self.owns_pin = original_owns_pin
                    raise
        finally:
            self._finish_lock()

    def rollback(self, preview_transaction: _RuntimeRandomPreviewTransaction) -> None:
        if self.closed:
            return
        pending_error: BaseException | None = None
        try:
            while True:
                try:
                    _CACHE_LOCK.acquire()
                    break
                except BaseException as exc:
                    if pending_error is None:
                        pending_error = exc
            try:
                reservation = preview_transaction.reservation
                if reservation is not None:
                    reservation_key = (reservation.node_key, reservation.token)
                    if _RUNTIME_RANDOM_PREVIEW_RESERVATIONS.get(reservation_key) is reservation:
                        del _RUNTIME_RANDOM_PREVIEW_RESERVATIONS[reservation_key]
                preview_transaction.reservation = None
                preview_transaction.closed = True
                if self.key and self.owns_pin:
                    _STAGE_CACHE_PINNED_KEYS.discard(self.key)
                    self.owns_pin = False
                    try:
                        _prune_stage_cache_unlocked()
                    except BaseException:
                        pass
            finally:
                _CACHE_LOCK.release()
        finally:
            self.bucket = None
            self.closed = True
            self._finish_lock()
        if pending_error is not None:
            raise pending_error

    def _finish_lock(self) -> None:
        lock = self.lock
        self.lock = None
        owns_key_lock = self.owns_key_lock
        self.owns_key_lock = False
        if lock is not None and owns_key_lock:
            lock.release()


_CACHE_NAMESPACE_PROPERTY = "qwen_te_cache_namespace_v1"
_CACHE_NAMESPACE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
_CACHE_NODE_LIMIT = 256
_CACHE: OrderedDict[str, dict[str, Any]] = OrderedDict()
_CACHE_LOCK = threading.Lock()
_CACHE_KEY_LOCKS = weakref.WeakValueDictionary()
_CACHE_KEY_LOCKS_GUARD = threading.Lock()
_STAGE_CACHE_PINNED_KEYS: set[str] = set()
_STAGE_CACHE_TRANSACTION_LOCAL = threading.local()
_RUNTIME_RANDOM_PREVIEW_RESERVATIONS: dict[tuple[str, str], _RuntimeRandomPreviewReservation] = {}
_STAGE_OUTPUT_CACHE_PUBLIC_KEYS = (
    "status",
    "updated_at",
    "full_text",
    "prompt_text",
    "prompt_collection",
    "smart_text_prompt",
    "video_prompt",
    "selected_tags_text",
    "json_result",
    "negative_prompt",
    "runtime_random_style_track",
    "runtime_random_mode_resolved",
    "smart_text_style_priority_resolved",
    "smart_text_style_resolved",
    "model_skill_pipeline",
    "model_call_status",
    "model_call_attempt_count",
    "model_call_success_count",
    "model_call_failure_count",
    "model_call_adopted_count",
    "model_active_fallback_count",
    "image_reverse_status",
    "skill_dynamic_strategy",
    "recent_prompt_fingerprint_count",
    "normalization_notes",
    "outputs",
)
_STAGE_OUTPUT_EXECUTION_HISTORY_KEY = "_execution_history"
_STAGE_OUTPUT_EXECUTION_SEQUENCE_KEY = "_execution_sequence"
_STAGE_OUTPUT_EXECUTION_HISTORY_LIMIT = 32
_STAGE_OUTPUT_EXECUTION_HISTORY_FIELDS = tuple(
    field
    for field in _STAGE_OUTPUT_CACHE_PUBLIC_KEYS
    if field not in {"full_text", "json_result", "normalization_notes", "outputs"}
)
_MODEL_RUNTIME_STATE_KEYS = (
    "模型来源实际",
    "模型回退说明",
    "模型调用状态",
    "模型调用尝试次数",
    "模型调用成功次数",
    "模型调用失败次数",
    "模型调用采纳次数",
    "模型调用错误",
    "模型活动回退数量",
    "模型调用基础来源",
    "模型传输重试次数",
    "模型最近瞬时错误",
    "推理纠偏说明",
)
_IMAGE_REVERSE_CACHE: OrderedDict[str, str] = OrderedDict()
_IMAGE_REVERSE_CACHE_LOCK = threading.Lock()
_IMAGE_REVERSE_CACHE_LIMIT = 32
_IMAGE_REVERSE_INFLIGHT: dict[str, _ImageReverseInFlight] = {}
_IMAGE_REVERSE_INFLIGHT_LIMIT = 1
_IMAGE_REVERSE_INFLIGHT_WAIT_TIMEOUT_SECONDS = 630.0
_IMAGE_REVERSE_INFLIGHT_STALE_AFTER_SECONDS = 630.0
_IMAGE_REVERSE_MODEL_CALL_TIMEOUT_SECONDS = 600.0
_MODEL_CALL_DEADLINE_PARAM = "_qwen_te_deadline_monotonic"
_IMAGE_REVERSE_INFLIGHT_CONDITION = threading.Condition(_IMAGE_REVERSE_CACHE_LOCK)


def _normalize_cache_namespace(value: Any) -> str:
    namespace = str(value or "").strip()
    return namespace if _CACHE_NAMESPACE_PATTERN.fullmatch(namespace) else ""


def _prune_stage_cache_unlocked() -> None:
    while len(_CACHE) > _CACHE_NODE_LIMIT:
        removable_key = next((key for key in _CACHE if key not in _STAGE_CACHE_PINNED_KEYS), None)
        if removable_key is None:
            break
        del _CACHE[removable_key]


def _cache_bucket_unlocked(key: str, *, create: bool = False) -> dict[str, Any] | None:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        return None
    transaction = getattr(_STAGE_CACHE_TRANSACTION_LOCAL, "current", None)
    if isinstance(transaction, _StageCacheTransaction) and transaction.matches(normalized_key):
        return transaction.get_bucket(create=create)
    bucket = _CACHE.get(normalized_key)
    if bucket is None and create:
        bucket = {}
        _CACHE[normalized_key] = bucket
    if bucket is not None:
        _CACHE.move_to_end(normalized_key)
    _prune_stage_cache_unlocked()
    return bucket


def _peek_cache_bucket_unlocked(key: str) -> dict[str, Any] | None:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        return None
    transaction = getattr(_STAGE_CACHE_TRANSACTION_LOCAL, "current", None)
    if isinstance(transaction, _StageCacheTransaction) and transaction.matches(normalized_key):
        return transaction.get_bucket(create=False)
    bucket = _CACHE.get(normalized_key)
    return bucket if isinstance(bucket, dict) else None


def _cache_key_lock(key: str):
    normalized_key = str(key or "").strip()
    if not normalized_key:
        return nullcontext()
    with _CACHE_KEY_LOCKS_GUARD:
        lock = _CACHE_KEY_LOCKS.get(normalized_key)
        if lock is None:
            lock = threading.RLock()
            _CACHE_KEY_LOCKS[normalized_key] = lock
        return lock


_IMAGE_REVERSE_MODEL_SETTING_KEYS = (
    "模型来源",
    "模型来源实际",
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
    "API模型",
    "API额外请求头",
)
_IMAGE_REVERSE_ATTACHED_CONFIG_KEYS = (
    "family",
    "model",
    "mmproj",
    "think",
    "n_ctx",
    "n_gpu_layers",
    "cache_type_k",
    "cache_type_v",
    "provider",
    "kind",
    "url",
)
_RUNTIME_RANDOM_HISTORY_LIMIT = 48
_RUNTIME_RANDOM_PREVIEW_TOKEN_LIMIT = 64
_RUNTIME_RANDOM_PREVIEW_MARKER_MAX_CHARS = 8_192
_RUNTIME_RANDOM_PREVIEW_STATE_SETTING_KEYS = (
    "unique_id",
    "cache_key",
    "模板风格",
    "主体类型",
    "标签反推模式",
    "风格隔离策略",
    "运行时随机标签",
    "运行时随机模式",
    "运行时随机强度",
    "随机主题池",
    "核心标签锁定数量",
    "锁定标签白名单",
    "随机排除标签",
    "seed",
    "NSFW工作台状态指纹",
)
_STRICT_PROMPT_VARIATION_ATTEMPTS = 2048
_STRICT_PROMPT_HASH_HISTORY_LIMIT = 512
_STRICT_PROMPT_BASE_HASH_HISTORY_LIMIT = 512
_RUNTIME_RANDOM_HISTORY_GROUP_PREFIX = {
    "主体": "identity",
    "画面风格": "style",
    "场景背景": "scene",
    "服装造型": "outfit",
    "动作姿态": "action",
    "光影氛围": "light",
    "构图视角": "composition",
    "道具世界观": "prop",
    "成人向表达": "adult",
}
_RUNTIME_RANDOM_HISTORY_STABLE_TAGS = {
    "成年女性",
    "成年男性",
    "全景全身",
    "人物完整入镜",
    "全身",
    "完整画面",
    "自然透视",
    "高细节",
    "清晰",
    "无文字",
    "无水印",
    "无logo",
}
_RUNTIME_RANDOM_HISTORY_GENERIC_SUBJECTS = {
    "少女",
    "少年",
    "儿童",
    "老年",
    "中年女性",
    "中年男性",
    "东亚",
    "欧美",
    "混血",
    "南亚",
    "中东",
    "拉美",
    "非裔",
    "北欧",
    "二次元",
    "通用",
}

无标签 = "无"
模板选项 = [
    "自动",
    "真实感",
    "商业摄影",
    "时尚编辑",
    "电影写实",
    "私房写实",
    "插画感",
    "复古动画",
    "CG感",
    "东方赛博",
    "硬表面科幻",
    "古风",
    "国风电影",
    "武侠电影",
    "神话感",
    "暗黑奇幻",
    *FANTASY_TEMPLATE_OPTIONS,
    *EXPANDED_TEMPLATE_OPTIONS,
]
模板风格基础映射 = dict(TEMPLATE_STYLE_BASE_MAP)
随机主题池选项 = [
    "自动",
    "写实生活",
    "商业摄影",
    "时尚大片",
    "糖水写真",
    "旅行街拍",
    "海岸假日",
    "森林自然",
    "都市职场",
    "夜场电影感",
    "私房写实",
    "运动机能",
    "古风园林",
    "武侠江湖",
    "洛可可宫廷",
    "神话史诗",
    "暗黑哥特",
    "赛博工业",
    "东方赛博",
    "机甲科幻",
    "废土荒原",
    "复古插画",
    *FANTASY_THEME_POOL_OPTIONS,
    *EXPANDED_THEME_POOL_OPTIONS,
]
提示词语言选项 = ["纯中文", "英文提示词+中文说明", "纯英文"]
详细度选项 = ["简洁", "标准", "详细"]
输出模式选项 = ["完整结果", "仅提示词优先"]
标签反推模式选项 = ["自动平衡", "成人向成熟"]
风格隔离策略选项 = ["平衡收敛", "严格风格隔离", "允许风格漂移"]
主体类型选项 = ["自动", "人物角色", "非人物主体"]
案例输出结构选项 = ["自动", "案例长段版", "案例分段版"]
运行时随机模式选项 = ["自动判断", "全随机", "保留已选核心标签", "重写主体与场景"]
运行时随机强度选项 = ["弱", "中", "强", "强 / 极限拉开"]
智能文本风格优先选项 = ["自动判断", "节点优先", "文本优先"]
本地模型来源 = "本地模型"
旧本地模型来源 = "本地GGUF"
模型来源选项 = ["仅Skill", 本地模型来源, "API接口", 旧本地模型来源]


def _normalize_stage_model_source(source: Any) -> str:
    value = str(source or "").strip()
    if value == 旧本地模型来源 or value.startswith("本地") or value.startswith("外接本地"):
        return 本地模型来源
    return value if value in {"仅Skill", 本地模型来源, "API接口"} else (value or "仅Skill")
API服务商选项 = [
    "OpenAI兼容",
    "OpenAI",
    "OpenRouter",
    "DeepSeek",
    "通义千问DashScope",
    "Kimi",
    "SiliconFlow",
    "火山方舟",
    "智谱GLM",
    "Groq",
    "Together",
    "Fireworks",
    "Mistral",
    "Perplexity",
    "Gemini OpenAI兼容",
    "Claude Anthropic",
    "Gemini 原生",
    "Ollama本地",
    "LM Studio本地",
    "自定义",
]

API服务商预设 = {
    "OpenAI兼容": {"kind": "openai", "base_url": "", "env": ["QWEN_TE_API_KEY", "OPENAI_API_KEY"], "model": ""},
    "OpenAI": {"kind": "openai", "base_url": "https://api.openai.com/v1", "env": ["OPENAI_API_KEY", "QWEN_TE_API_KEY"], "model": "gpt-4o-mini"},
    "OpenRouter": {"kind": "openai", "base_url": "https://openrouter.ai/api/v1", "env": ["OPENROUTER_API_KEY", "QWEN_TE_API_KEY"], "model": "openai/gpt-4o-mini"},
    "DeepSeek": {"kind": "openai", "base_url": "https://api.deepseek.com", "env": ["DEEPSEEK_API_KEY", "QWEN_TE_API_KEY"], "model": "deepseek-v4-flash"},
    "通义千问DashScope": {"kind": "openai", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "env": ["DASHSCOPE_API_KEY", "QWEN_TE_API_KEY"], "model": "qwen-plus"},
    "Kimi": {"kind": "openai", "base_url": "https://api.moonshot.cn/v1", "env": ["MOONSHOT_API_KEY", "KIMI_API_KEY", "QWEN_TE_API_KEY"], "model": "moonshot-v1-8k"},
    "SiliconFlow": {"kind": "openai", "base_url": "https://api.siliconflow.cn/v1", "env": ["SILICONFLOW_API_KEY", "QWEN_TE_API_KEY"], "model": ""},
    "火山方舟": {"kind": "openai", "base_url": "https://ark.cn-beijing.volces.com/api/v3", "env": ["ARK_API_KEY", "VOLCENGINE_API_KEY", "QWEN_TE_API_KEY"], "model": ""},
    "智谱GLM": {"kind": "openai", "base_url": "https://open.bigmodel.cn/api/paas/v4", "env": ["ZHIPUAI_API_KEY", "GLM_API_KEY", "QWEN_TE_API_KEY"], "model": "glm-4.5"},
    "Groq": {"kind": "openai", "base_url": "https://api.groq.com/openai/v1", "env": ["GROQ_API_KEY", "QWEN_TE_API_KEY"], "model": "openai/gpt-oss-20b"},
    "Together": {"kind": "openai", "base_url": "https://api.together.xyz/v1", "env": ["TOGETHER_API_KEY", "QWEN_TE_API_KEY"], "model": ""},
    "Fireworks": {"kind": "openai", "base_url": "https://api.fireworks.ai/inference/v1", "env": ["FIREWORKS_API_KEY", "QWEN_TE_API_KEY"], "model": ""},
    "Mistral": {"kind": "openai", "base_url": "https://api.mistral.ai/v1", "env": ["MISTRAL_API_KEY", "QWEN_TE_API_KEY"], "model": "mistral-small-latest"},
    "Perplexity": {"kind": "openai", "base_url": "https://api.perplexity.ai", "env": ["PPLX_API_KEY", "PERPLEXITY_API_KEY", "QWEN_TE_API_KEY"], "model": "sonar"},
    "Gemini OpenAI兼容": {"kind": "openai", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "QWEN_TE_API_KEY"], "model": "gemini-2.5-flash"},
    "Claude Anthropic": {"kind": "anthropic", "base_url": "https://api.anthropic.com/v1/messages", "env": ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY", "QWEN_TE_API_KEY"], "model": "claude-haiku-4-5"},
    "Gemini 原生": {"kind": "gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta", "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "QWEN_TE_API_KEY"], "model": "gemini-2.5-flash"},
    "Ollama本地": {"kind": "openai", "base_url": "http://127.0.0.1:11434/v1", "env": [], "model": "qwen2.5"},
    "LM Studio本地": {"kind": "openai", "base_url": "http://127.0.0.1:1234/v1", "env": [], "model": ""},
    "自定义": {"kind": "openai", "base_url": "", "env": ["QWEN_TE_API_KEY"], "model": ""},
}

_自定义API密钥来源环境变量 = "QWEN_TE_CUSTOM_API_SECRET_ORIGINS"

SETTING_DEFAULTS = {
    "模板风格": "自动",
    "主体类型": "自动",
    "案例输出结构": "自动",
    "运行时随机标签": False,
    "运行时随机模式": "自动判断",
    "核心标签锁定数量": 10,
    "运行时随机强度": "中",
    "随机主题池": "自动",
    "锁定标签白名单": "",
    "随机排除标签": "",
    "生成数量": 3,
    "提示词语言": "纯中文",
    "详细度": "标准",
    "输出模式": "完整结果",
    "标签反推模式": "自动平衡",
    "风格隔离策略": "平衡收敛",
    "优先柔和肤质": False,
    "抑制文字伪影": False,
    "额外要求": "",
    "智能文本匹配": False,
    "智能文本输入": "",
    "智能文本风格优先": "自动判断",
    "标签块编排启用": False,
    "标签块编排JSON": "",
    "图片反推生成": False,
    "图片反推模式": "角色设定图",
    "图片反推最大边长": 960,
    "模型来源": "仅Skill",
    "模型来源实际": "仅Skill",
    "模型回退说明": "",
    "模型调用状态": "未启用（仅Skill）",
    "模型调用尝试次数": 0,
    "模型调用成功次数": 0,
    "模型调用失败次数": 0,
    "模型调用采纳次数": 0,
    "模型活动回退数量": 0,
    "模型调用错误": [],
    "模型传输重试次数": 0,
    "模型最近瞬时错误": "",
    "模型调用基础来源": "仅Skill",
    "图片反推状态": "未启用",
    "图片反推错误": "",
    "内置模型系列": "Qwen3.5-VL",
    "内置主模型": "",
    "内置视觉投影mmproj": "无",
    "内置启用思考": False,
    "内置上下文长度": 8192,
    "内置GPU层数": -1,
    "内置KV缓存K类型": _内置默认KV缓存类型,
    "内置KV缓存V类型": _内置默认KV缓存类型,
    "API服务商": "OpenAI兼容",
    "API地址": "",
    "API密钥": "env:QWEN_TE_API_KEY",
    "API模型": "",
    "API超时秒": 120,
    "API额外请求头": "",
    "模型瞬时重试次数": 1,
    "系统提示词覆盖": DEFAULT_STAGE_PROMPT_SYSTEM_TEMPLATE,
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
    "连续生成避重缓存": "",
    "运行时随机保护标签": "",
    "运行时随机预览令牌": "",
}

_RUNTIME_PREVIEW_SETTING_MAX_CHARS = 32_768
_RUNTIME_PREVIEW_TAG_MAX_ITEMS = 256
_RUNTIME_PREVIEW_TAG_MAX_CHARS = 512
_RUNTIME_PREVIEW_TAG_TOTAL_CHARS = 32_768
_RUNTIME_PREVIEW_LARGE_SETTING_LIMITS = {
    "系统提示词覆盖": 131_072,
    "标签块编排JSON": 262_144,
    "连续生成避重缓存": 131_072,
}


def _coerce_runtime_preview_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on", "开启", "开", "是"}:
            return True
        if normalized in {"", "0", "false", "no", "off", "关闭", "关", "否", "none", "null", "undefined"}:
            return False
    return bool(default)


def _bounded_runtime_preview_settings(raw_settings: Any) -> dict[str, Any]:
    source = raw_settings if isinstance(raw_settings, dict) else {}
    settings = dict(SETTING_DEFAULTS)
    for name, default in SETTING_DEFAULTS.items():
        if name not in source:
            continue
        value = source.get(name)
        if isinstance(default, bool):
            settings[name] = _coerce_runtime_preview_bool(value, default)
        elif isinstance(value, str):
            limit = _RUNTIME_PREVIEW_LARGE_SETTING_LIMITS.get(name, _RUNTIME_PREVIEW_SETTING_MAX_CHARS)
            settings[name] = value[:limit]
        elif value is None or isinstance(value, (bool, int, float)):
            settings[name] = value
        else:
            settings[name] = default
    return settings


def _bounded_runtime_preview_tags(
    value: Any,
    *,
    max_items: int = _RUNTIME_PREVIEW_TAG_MAX_ITEMS,
    max_total_chars: int = _RUNTIME_PREVIEW_TAG_TOTAL_CHARS,
) -> list[str]:
    if isinstance(value, dict):
        return []
    raw_items = value if isinstance(value, (list, tuple, set)) else _parse_tags(str(value or "")[:max_total_chars])
    result: list[str] = []
    seen: set[str] = set()
    total_chars = 0
    scan_limit = max(1, max(0, int(max_items)) * 4)
    for raw_index, raw_item in enumerate(raw_items):
        if raw_index >= scan_limit:
            break
        if isinstance(raw_item, (dict, list, tuple, set)):
            continue
        tag = unicodedata.normalize("NFKC", str(raw_item or "")[: 4 * _RUNTIME_PREVIEW_TAG_MAX_CHARS])
        tag = re.sub(r"\s+", " ", tag).strip()[:_RUNTIME_PREVIEW_TAG_MAX_CHARS].rstrip()
        if not tag or tag in seen:
            continue
        separator_chars = 1 if result else 0
        remaining = max_total_chars - total_chars - separator_chars
        if remaining <= 0:
            break
        tag = tag[:remaining].rstrip()
        if not tag:
            break
        result.append(tag)
        seen.add(tag)
        total_chars += len(tag) + separator_chars
        if len(result) >= max(0, int(max_items)):
            break
    return result


def _bounded_runtime_preview_scalar(value: Any, max_chars: int) -> str:
    if isinstance(value, (dict, list, tuple, set)):
        return ""
    return str(value or "")[: max(0, int(max_chars))].strip()

_分组槽位上限 = {str(group["name"]): int(group["slots"]) for group in 分组配置}
def _内置模型文件选项() -> tuple[list[str], list[str]]:
    all_files = _列出内置llm文件()
    model_list = [
        file
        for file in all_files
        if "mmproj" not in file.lower() and str(file).lower().endswith((".gguf", ".safetensors", ".bin", ".pth", ".pt"))
    ]
    mmproj_list = ["无"] + [
        file
        for file in all_files
        if "mmproj" in file.lower() and str(file).lower().endswith((".gguf", ".safetensors", ".bin"))
    ]
    if not model_list:
        model_list = ["（请把模型放到 models/LLM）"]
    return model_list, mmproj_list


def _api_provider_preset(provider: str) -> dict[str, Any]:
    return dict(API服务商预设.get(str(provider or "").strip()) or API服务商预设["OpenAI兼容"])


def _validate_api_http_url(raw_url: Any, *, label: str = "API地址") -> str:
    url = str(raw_url or "").strip()
    if not url:
        raise RuntimeError(f"{label}为空。")
    if any(char.isspace() for char in url):
        raise RuntimeError(f"{label}不得包含空白字符。")
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise RuntimeError(f"{label}格式无效：{exc}") from exc
    scheme = str(parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise RuntimeError(f"{label}仅允许 http:// 或 https:// 地址。")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError(f"{label}不得包含用户名或密码。")
    hostname = str(parsed.hostname or "").strip()
    if not hostname or re.search(r"[\s/%?#@\\]", hostname):
        raise RuntimeError(f"{label}必须包含有效主机名。")
    try:
        hostname.encode("idna")
    except UnicodeError as exc:
        raise RuntimeError(f"{label}包含无效主机名。") from exc
    if port is not None and not (1 <= port <= 65535):
        raise RuntimeError(f"{label}端口必须在 1 到 65535 之间。")
    decoded_path = urllib.parse.unquote(str(parsed.path or ""))
    decoded_segments = [segment for segment in decoded_path.split("/") if segment]
    if (
        "\\" in decoded_path
        or any(segment in {".", ".."} for segment in decoded_segments)
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 or ord(char) > 127 for char in decoded_path)
    ):
        raise RuntimeError(
            f"{label}路径必须使用规范 ASCII 路径，不得包含转义的点段、反斜杠、空白或非 ASCII 字符。"
        )
    return url


def _api_url_origin(raw_url: Any, *, label: str = "API地址") -> str:
    url = _validate_api_http_url(raw_url, label=label)
    parsed = urllib.parse.urlsplit(url)
    scheme = str(parsed.scheme).lower()
    hostname = str(parsed.hostname).encode("idna").decode("ascii").lower()
    port = parsed.port
    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        port = None
    host = f"[{hostname}]" if ":" in hostname else hostname
    return f"{scheme}://{host}{f':{port}' if port is not None else ''}"


def _custom_api_secret_origins() -> set[str]:
    raw_origins = str(os.environ.get(_自定义API密钥来源环境变量, "") or "")
    origins: set[str] = set()
    for raw_origin in re.split(r"[,;\r\n]+", raw_origins):
        origin = raw_origin.strip()
        if not origin:
            continue
        try:
            parsed = urllib.parse.urlsplit(origin)
            normalized = _api_url_origin(origin, label=_自定义API密钥来源环境变量)
        except RuntimeError as exc:
            raise RuntimeError(
                f"{_自定义API密钥来源环境变量} 包含无效来源 {origin!r}；"
                "请精确填写 scheme://host[:port]。"
            ) from exc
        if parsed.path or parsed.query or parsed.fragment:
            raise RuntimeError(
                f"{_自定义API密钥来源环境变量} 包含无效来源 {origin!r}；"
                "来源不得包含路径、查询参数或片段，请精确填写 scheme://host[:port]。"
            )
        origins.add(normalized)
    return origins


def _ensure_environment_api_key_origin(*, provider: str, target_url: str, preset: dict[str, Any]) -> None:
    target_origin = _api_url_origin(target_url)
    preset_base_url = str(preset.get("base_url") or "").strip()
    if preset_base_url:
        preset_origin = _api_url_origin(preset_base_url, label=f"服务商“{provider}”预设 API 地址")
        if target_origin != preset_origin:
            raise RuntimeError(
                f"为防止环境变量密钥外传，服务商“{provider}”的环境变量密钥只能发送到"
                f"预设来源 {preset_origin}；当前 API 来源为 {target_origin}。"
                "请恢复同源地址，或直接填写仅供当前地址使用的 API key。"
            )
        return
    if target_origin not in _custom_api_secret_origins():
        raise RuntimeError(
            f"环境变量密钥默认不允许发送到自定义 API 来源 {target_origin}。"
            f"如确认可信，请将该来源加入 {_自定义API密钥来源环境变量} "
            "（精确填写 scheme://host[:port]）；也可以直接填写该地址专用的 API key，"
            "接口无需密钥时请清空 API密钥。"
        )


def _resolve_api_key(
    raw_key: Any,
    env_names: list[str],
    *,
    provider: str,
    target_url: str,
    preset: dict[str, Any],
) -> str:
    key = str(raw_key or "").strip()
    if key and not key.lower().startswith("env:"):
        return key
    if not key and not str(preset.get("base_url") or "").strip():
        return ""

    candidates: list[str] = []
    if key.lower().startswith("env:"):
        env_name = key[4:].strip()
        if not env_name:
            raise RuntimeError("API密钥使用 env:VAR 时必须填写环境变量名。")
        candidates.append(env_name)
        if env_name == "QWEN_TE_API_KEY":
            candidates.extend(str(item or "").strip() for item in env_names)
    else:
        candidates.extend(str(item or "").strip() for item in env_names)
    candidates = list(dict.fromkeys(env_name for env_name in candidates if env_name))
    if not candidates:
        return ""

    for env_name in candidates:
        value = os.environ.get(env_name, "")
        if value:
            _ensure_environment_api_key_origin(provider=provider, target_url=target_url, preset=preset)
            return value.strip()
    return ""


def _normalize_api_base_url(base_url: Any, *, provider: str, kind: str) -> str:
    preset = _api_provider_preset(provider)
    base = str(base_url or "").strip() or str(preset.get("base_url") or "").strip()
    if not base:
        raise RuntimeError("API地址为空。请选择服务商，或在模型按钮里填写 API 地址。")
    base = _validate_api_http_url(base)
    parsed_base = urllib.parse.urlsplit(base)
    if parsed_base.query or parsed_base.fragment:
        raise RuntimeError("API地址必须填写 Base URL，不得包含查询参数或片段。")
    if kind == "openai":
        trimmed = base.rstrip("/")
        if trimmed.endswith("/chat/completions"):
            normalized = trimmed
        else:
            normalized = f"{trimmed}/chat/completions"
        return _validate_api_http_url(normalized)
    if kind == "anthropic":
        trimmed = base.rstrip("/")
        normalized = trimmed if trimmed.endswith("/messages") else f"{trimmed}/messages"
        return _validate_api_http_url(normalized)
    if kind == "gemini":
        return _validate_api_http_url(base.rstrip("/"))
    return _validate_api_http_url(base)


def _normalize_api_config_base_url(base_url: Any) -> str:
    base = _validate_api_http_url(base_url)
    parsed = urllib.parse.urlsplit(base)
    if parsed.query or parsed.fragment:
        raise RuntimeError("API地址必须填写 Base URL，不得包含查询参数或片段。")
    origin = _api_url_origin(base)
    path = str(parsed.path or "").rstrip("/")
    path_segments = [segment for segment in path.split("/") if segment]
    if "\\" in path or any(segment in {".", ".."} for segment in path_segments) or any(ord(char) > 127 for char in path):
        raise RuntimeError(
            "API地址路径必须使用规范 ASCII 路径，不得包含反斜杠、中文路径或 . / .. 路径段。"
        )
    return f"{origin}{path if path and path != '/' else ''}"


_API_EXTRA_HEADER_NAME_PATTERN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_FORBIDDEN_API_EXTRA_HEADERS = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "x-goog-api-key",
    "content-type",
    "accept-encoding",
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "cookie",
    "set-cookie",
}


def _validate_api_extra_header(name: Any, value: Any) -> tuple[str, str]:
    header_name = str(name or "").strip()
    header_value = str(value or "").strip()
    if not header_name or not _API_EXTRA_HEADER_NAME_PATTERN.fullmatch(header_name):
        raise RuntimeError(f"API额外请求头名称无效：{header_name or '<空>'}。")
    if header_name.casefold() in _FORBIDDEN_API_EXTRA_HEADERS:
        raise RuntimeError(f"API额外请求头不允许覆盖受保护字段：{header_name}。请使用 API密钥 配置认证。")
    if not header_value:
        raise RuntimeError(f"API额外请求头 {header_name} 的值为空。")
    if any(ord(char) < 32 or ord(char) == 127 for char in header_value):
        raise RuntimeError(f"API额外请求头 {header_name} 不得包含控制字符。")
    return header_name, header_value


def _parse_api_extra_headers(raw_headers: Any) -> dict[str, str]:
    text = str(raw_headers or "").strip()
    if not text:
        return {}
    items: list[tuple[Any, Any]] = []
    if text.startswith(("{", "[")):
        try:
            payload = json.loads(text)
        except Exception as exc:
            raise RuntimeError(f"API额外请求头 JSON 格式无效：{exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("API额外请求头 JSON 必须是对象，例如 {\"HTTP-Referer\": \"https://example.com\"}。")
        items = list(payload.items())
    else:
        for line_number, raw_line in enumerate(re.split(r"[\n\r]+", text), start=1):
            line = raw_line.strip()
            if not line:
                continue
            if ":" in line:
                key, value = line.split(":", 1)
            elif "=" in line:
                key, value = line.split("=", 1)
            else:
                raise RuntimeError(f"API额外请求头第 {line_number} 行缺少 : 或 = 分隔符。")
            items.append((key, value))
    headers: dict[str, str] = {}
    seen_names: set[str] = set()
    for raw_name, raw_value in items:
        name, value = _validate_api_extra_header(raw_name, raw_value)
        folded = name.casefold()
        if folded in seen_names:
            raise RuntimeError(f"API额外请求头重复：{name}。")
        seen_names.add(folded)
        headers[name] = value
    return headers
def _split_system_user_messages(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    system_parts: list[str] = []
    user_messages: list[dict[str, Any]] = []
    for message in messages or []:
        role = str(message.get("role") or "user").strip() or "user"
        content = message.get("content", "")
        if role == "system":
            if isinstance(content, str):
                system_parts.append(content)
            elif isinstance(content, list):
                system_parts.extend(str(part.get("text") or "") for part in content if isinstance(part, dict) and part.get("type") == "text")
            continue
        user_messages.append({"role": role, "content": content})
    return "\n\n".join(part.strip() for part in system_parts if part.strip()), user_messages


def _data_url_to_media_source(data_url: str) -> tuple[str, str]:
    text = str(data_url or "").strip()
    match = re.match(r"^data:([^;,]+);base64,(.+)$", text, flags=re.DOTALL)
    if not match:
        return "image/png", text
    return match.group(1), match.group(2)


def _anthropic_content_parts(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    parts: list[dict[str, Any]] = []
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                parts.append({"type": "text", "text": str(item.get("text") or "")})
            elif item.get("type") == "image_url":
                url = str((item.get("image_url") or {}).get("url") or "")
                media_type, data = _data_url_to_media_source(url)
                parts.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}})
    return parts or [{"type": "text", "text": str(content or "")}]


def _gemini_parts(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, str):
        return [{"text": content}]
    parts: list[dict[str, Any]] = []
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                parts.append({"text": str(item.get("text") or "")})
            elif item.get("type") == "image_url":
                url = str((item.get("image_url") or {}).get("url") or "")
                media_type, data = _data_url_to_media_source(url)
                parts.append({"inline_data": {"mime_type": media_type, "data": data}})
    return parts or [{"text": str(content or "")}]


_API_RESPONSE_MAX_BYTES = 16 * 1024 * 1024
_HTTP_READ_CHUNK_BYTES = 64 * 1024


class _NoSecretRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            parsed = urllib.parse.urlsplit(str(newurl or ""))
            hostname = str(parsed.hostname or "").encode("idna").decode("ascii")
            host = f"[{hostname}]" if ":" in hostname else hostname
            port = parsed.port
            origin = f"{str(parsed.scheme or '').lower()}://{host}{f':{port}' if port is not None else ''}"
            safe_target = f"{origin}/<redacted>" if hostname else "<redacted>"
        except (UnicodeError, ValueError):
            safe_target = "<redacted>"
        raise RuntimeError(f"API 返回 HTTP {code} 重定向；为防止密钥跨来源泄露，QwenTE 不会自动跟随：{safe_target}")


_API_HTTP_OPENER = urllib.request.build_opener(_NoSecretRedirectHandler())


def _set_http_response_timeout(response: Any, timeout: float) -> None:
    fp = getattr(response, "fp", None)
    raw = getattr(fp, "raw", None)
    socket_obj = getattr(raw, "_sock", None)
    for candidate in (socket_obj, raw, fp):
        setter = getattr(candidate, "settimeout", None)
        if callable(setter):
            try:
                setter(max(0.1, float(timeout)))
            except Exception:
                pass
            return


def _read_http_response_limited(response: Any, *, max_bytes: int, timeout: float, label: str) -> bytes:
    content_length = None
    try:
        content_length = int(response.headers.get("Content-Length", "") or 0)
    except (TypeError, ValueError, OverflowError, AttributeError):
        content_length = None
    if content_length is not None and content_length > max_bytes:
        raise RuntimeError(f"{label}响应过大：Content-Length={content_length}，上限为 {max_bytes} 字节。")

    deadline = time.monotonic() + max(0.1, float(timeout))
    chunks: list[bytes] = []
    total = 0
    reader = getattr(response, "read1", None)
    if not callable(reader):
        reader = response.read
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"{label}读取超过总时限。")
        _set_http_response_timeout(response, remaining)
        chunk = reader(min(_HTTP_READ_CHUNK_BYTES, max_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(bytes(chunk))
        total += len(chunk)
        if total > max_bytes:
            raise RuntimeError(f"{label}响应超过 {max_bytes} 字节上限。")
    return b"".join(chunks)


def _http_post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with _API_HTTP_OPENER.open(request, timeout=timeout) as response:
        raw = _read_http_response_limited(
            response,
            max_bytes=_API_RESPONSE_MAX_BYTES,
            timeout=timeout,
            label="模型 API",
        )
        charset = response.headers.get_content_charset() or "utf-8"
    parsed = json.loads(raw.decode(charset, errors="replace"))
    return parsed if isinstance(parsed, dict) else {}


class _TEAPIChatModel:
    def __init__(self, config: dict[str, Any]):
        self.config = dict(config)
        self.llm = self
        self.model_path = f"api://{self.config.get('provider')}/{self.config.get('model')}"

    def create_chat_completion(self, **kwargs) -> dict[str, Any]:
        provider = str(self.config.get("provider") or "OpenAI兼容")
        kind = str(self.config.get("kind") or "openai")
        model = str(self.config.get("model") or "").strip()
        if not model:
            raise RuntimeError("API模型为空。请在模型按钮里填写模型名。")
        timeout = _safe_float(self.config.get("timeout"), 120.0, 5.0, 600.0)
        messages = list(kwargs.get("messages") or [])
        max_tokens = _safe_int(kwargs.get("max_tokens", 1800), 1800, 1, 8192)
        temperature = _safe_float(kwargs.get("temperature", 0.62), 0.62, 0.0, 2.0)
        top_p = _safe_float(kwargs.get("top_p", 0.9), 0.9, 0.0, 1.0)
        frequency_penalty = _safe_float(kwargs.get("frequency_penalty", 0.0), 0.0, -2.0, 2.0)
        presence_penalty = _safe_float(kwargs.get("presence_penalty", 0.0), 0.0, -2.0, 2.0)
        seed = _safe_int(kwargs.get("seed", 0), 0, 0, 0xFFFFFFFFFFFFFFFF)
        top_k = _safe_int(kwargs.get("top_k", 0), 0, 0, 200)
        raw_stop = kwargs.get("stop")
        stop_sequences = [str(item) for item in (raw_stop if isinstance(raw_stop, (list, tuple)) else [raw_stop]) if str(item or "")]

        headers = {"Content-Type": "application/json", **dict(self.config.get("extra_headers") or {})}
        api_key = str(self.config.get("api_key") or "").strip()

        if kind == "anthropic":
            if api_key:
                headers["x-api-key"] = api_key
            headers.setdefault("anthropic-version", "2023-06-01")
            system_text, user_messages = _split_system_user_messages(messages)
            payload: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": min(1.0, temperature),
                "top_p": top_p,
                "stream": False,
                "messages": [
                    {"role": "assistant" if item["role"] == "assistant" else "user", "content": _anthropic_content_parts(item.get("content"))}
                    for item in user_messages
                ],
            }
            if top_k > 0:
                payload["top_k"] = top_k
            if stop_sequences:
                payload["stop_sequences"] = stop_sequences
            if system_text:
                payload["system"] = system_text
            response = _http_post_json(str(self.config.get("url")), payload, headers, timeout)
            if response.get("error"):
                _extract_model_response_text_impl(response)
            text = "".join(str(part.get("text") or "") for part in response.get("content", []) if isinstance(part, dict))
            if not text.strip():
                stop_reason = str(response.get("stop_reason") or response.get("stop_sequence") or "empty_content")
                raise RuntimeError(f"Claude API 未返回文本：stop_reason={stop_reason}")
            return {"choices": [{"message": {"content": text}}], "raw": response}

        if kind == "gemini":
            if not api_key:
                raise RuntimeError("Gemini 原生 API 需要 API Key。可填写 key 或 env:GEMINI_API_KEY。")
            base_url = str(self.config.get("url") or "").rstrip("/")
            encoded_model = urllib.parse.quote(model, safe="")
            url = f"{base_url}/models/{encoded_model}:generateContent"
            headers["x-goog-api-key"] = api_key
            system_text, user_messages = _split_system_user_messages(messages)
            contents = [
                {"role": "model" if item["role"] == "assistant" else "user", "parts": _gemini_parts(item.get("content"))}
                for item in user_messages
            ]
            payload = {
                "contents": contents,
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature, "topP": top_p},
            }
            if top_k > 0:
                payload["generationConfig"]["topK"] = top_k
            if seed > 0:
                payload["generationConfig"]["seed"] = seed
            if stop_sequences:
                payload["generationConfig"]["stopSequences"] = stop_sequences
            if abs(frequency_penalty) > 1e-9:
                payload["generationConfig"]["frequencyPenalty"] = frequency_penalty
            if abs(presence_penalty) > 1e-9:
                payload["generationConfig"]["presencePenalty"] = presence_penalty
            if system_text:
                payload["system_instruction"] = {"parts": [{"text": system_text}]}
            response = _http_post_json(url, payload, headers, timeout)
            if response.get("error"):
                _extract_model_response_text_impl(response)
            candidates = response.get("candidates") or []
            if not candidates:
                feedback = response.get("promptFeedback") if isinstance(response.get("promptFeedback"), dict) else {}
                block_reason = str(feedback.get("blockReason") or "no_candidates")
                raise RuntimeError(f"Gemini API 未返回候选：blockReason={block_reason}")
            candidate = candidates[0] if isinstance(candidates[0], dict) else {}
            parts = ((candidate.get("content") or {}).get("parts") or []) if isinstance(candidate.get("content"), dict) else []
            text = "".join(str(part.get("text") or "") for part in parts if isinstance(part, dict))
            if not text.strip():
                finish_reason = str(candidate.get("finishReason") or "empty_content")
                raise RuntimeError(f"Gemini API 候选没有文本：finishReason={finish_reason}")
            return {"choices": [{"message": {"content": text}}], "raw": response}

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        openai_reasoning_model = provider == "OpenAI" and bool(re.match(r"(?i)^(?:o[134](?:-|$)|gpt-5(?:-|$))", model))
        request_messages = [
            {**message, "role": "developer" if openai_reasoning_model and str(message.get("role") or "") == "system" else message.get("role")}
            if isinstance(message, dict)
            else message
            for message in messages
        ]
        payload = {
            "model": model,
            "messages": request_messages,
            "stream": False,
        }
        payload["max_completion_tokens" if provider == "OpenAI" else "max_tokens"] = max_tokens
        if not openai_reasoning_model:
            payload["temperature"] = temperature
            payload["top_p"] = top_p
            if abs(frequency_penalty) > 1e-9:
                payload["frequency_penalty"] = frequency_penalty
            if abs(presence_penalty) > 1e-9:
                payload["presence_penalty"] = presence_penalty
            if seed > 0:
                payload["seed"] = seed
            if stop_sequences:
                payload["stop"] = stop_sequences
        if provider == "DeepSeek" and model.startswith("deepseek-v4"):
            payload["thinking"] = {"type": "disabled"}
        response = _http_post_json(str(self.config.get("url")), payload, headers, timeout)
        return response


def _解析API模型配置(kwargs: dict[str, Any]) -> dict[str, Any]:
    provider = str(kwargs.get("API服务商", SETTING_DEFAULTS["API服务商"]) or SETTING_DEFAULTS["API服务商"]).strip()
    preset = _api_provider_preset(provider)
    kind = str(preset.get("kind") or "openai")
    model = str(kwargs.get("API模型", "") or "").strip() or str(preset.get("model") or "").strip()
    configured_base_url = str(kwargs.get("API地址", "") or "").strip() or str(preset.get("base_url") or "").strip()
    url = _normalize_api_base_url(kwargs.get("API地址", ""), provider=provider, kind=kind)
    kwargs["API服务商有效"] = provider
    kwargs["API地址有效"] = _normalize_api_config_base_url(configured_base_url)
    kwargs["API模型有效"] = model
    api_key = _resolve_api_key(
        kwargs.get("API密钥", ""),
        list(preset.get("env") or []),
        provider=provider,
        target_url=url,
        preset=preset,
    )
    kwargs["_API密钥脱敏值"] = api_key
    preset_base_url = str(preset.get("base_url") or "").strip()
    preset_env_names = [str(name).strip() for name in preset.get("env", []) if str(name).strip()]
    if (
        not api_key
        and preset_base_url
        and preset_env_names
        and _api_url_origin(url) == _api_url_origin(preset_base_url, label=f"服务商“{provider}”预设 API 地址")
    ):
        env_hint = "、".join(preset_env_names[:3])
        raise RuntimeError(
            f"服务商“{provider}”未找到 API Key。请直接填写 API密钥，或在启动 ComfyUI 前设置 {env_hint}。"
        )
    return {
        "provider": provider,
        "kind": kind,
        "url": url,
        "api_key": api_key,
        "model": model,
        "timeout": _safe_int(kwargs.get("API超时秒", SETTING_DEFAULTS["API超时秒"]), SETTING_DEFAULTS["API超时秒"], 5, 600),
        "extra_headers": _parse_api_extra_headers(kwargs.get("API额外请求头", "")),
    }


def _创建API阶段模型(kwargs: dict[str, Any]) -> _TEAPIChatModel:
    config = _解析API模型配置(kwargs)
    if not str(config.get("model") or "").strip():
        raise RuntimeError("API模型为空。请在模型按钮里填写模型名，或选择带默认模型的服务商。")
    return _TEAPIChatModel(config)


def _解析内置模型配置(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": str(kwargs.get("内置模型系列", SETTING_DEFAULTS["内置模型系列"]) or SETTING_DEFAULTS["内置模型系列"]),
        "model": str(kwargs.get("内置主模型", "") or ""),
        "mmproj": str(kwargs.get("内置视觉投影mmproj", "无") or "无"),
        "think": bool(kwargs.get("内置启用思考", SETTING_DEFAULTS["内置启用思考"])),
        "n_ctx": _safe_int(kwargs.get("内置上下文长度", SETTING_DEFAULTS["内置上下文长度"]), SETTING_DEFAULTS["内置上下文长度"], 1024, 327680),
        "n_gpu_layers": _safe_int(kwargs.get("内置GPU层数", SETTING_DEFAULTS["内置GPU层数"]), SETTING_DEFAULTS["内置GPU层数"], -1, 9999),
        "cache_type_k": str(kwargs.get("内置KV缓存K类型", _内置默认KV缓存类型) or _内置默认KV缓存类型),
        "cache_type_v": str(kwargs.get("内置KV缓存V类型", _内置默认KV缓存类型) or _内置默认KV缓存类型),
    }


def _加载内置阶段模型(kwargs: dict[str, Any]) -> Any:
    if _内置QwenStorage is None:
        raise RuntimeError("当前环境无法访问内置模型加载器。请确认 Qwen TE 节点已完整加载。")
    config = _解析内置模型配置(kwargs)
    if not config["model"] or str(config["model"]).startswith("（请把模型放到"):
        raise RuntimeError("未选择内置主模型。请点击节点底部“模型”按钮选择 models/LLM 里的模型。")
    return _内置QwenStorage.load(config)


def _加载阶段模型(kwargs: dict[str, Any]) -> Any:
    source = _normalize_stage_model_source(
        kwargs.get("模型来源", SETTING_DEFAULTS["模型来源"]) or SETTING_DEFAULTS["模型来源"]
    )
    if source == "仅Skill":
        return None
    if source == "API接口":
        return _创建API阶段模型(kwargs)
    return _加载内置阶段模型(kwargs)


def _append_runtime_note(settings: dict[str, Any], note: str) -> None:
    text = str(note or "").strip()
    if not text:
        return
    current = settings.get("推理纠偏说明", [])
    if isinstance(current, (list, tuple, set)):
        notes = [str(item).strip() for item in current if str(item).strip()]
    else:
        notes = [line.strip() for line in str(current or "").replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
    if text not in notes:
        notes.append(text)
    settings["推理纠偏说明"] = notes


def _safe_stage_model_source_label(source: str) -> str:
    normalized = _normalize_stage_model_source(source)
    return normalized if normalized in {"仅Skill", "API接口", 本地模型来源} else (normalized or "未知来源")


def _安全加载阶段模型(settings: dict[str, Any]) -> Any:
    source = _safe_stage_model_source_label(
        str(settings.get("模型来源", SETTING_DEFAULTS["模型来源"]) or SETTING_DEFAULTS["模型来源"]).strip()
    )
    settings["模型调用基础来源"] = source
    settings["模型调用尝试次数"] = 0
    settings["模型调用成功次数"] = 0
    settings["模型调用失败次数"] = 0
    settings["模型活动回退数量"] = 0
    settings["模型调用采纳次数"] = 0
    settings["模型调用错误"] = []
    settings["模型传输重试次数"] = 0
    settings["模型最近瞬时错误"] = ""
    if source == "仅Skill":
        settings["模型来源实际"] = "仅Skill"
        settings["模型回退说明"] = ""
        settings["模型调用状态"] = "未启用（仅Skill）"
        return None
    try:
        model = _加载阶段模型(settings)
    except Exception as exc:
        reason = _sanitize_model_error_impl(exc, settings)
        note = f"模型加载回退：{source} 加载失败，已改用仅Skill；原因：{reason}"
        settings["模型来源实际"] = "仅Skill回退"
        settings["模型回退说明"] = note
        settings["模型调用状态"] = "配置或加载失败，已回退 Skill"
        settings["模型调用尝试次数"] = 1
        settings["模型调用失败次数"] = 1
        requested_fallback_count = _safe_int(
            settings.get("生成数量", SETTING_DEFAULTS["生成数量"]),
            SETTING_DEFAULTS["生成数量"],
            1,
            20,
        )
        settings["模型活动回退数量"] = requested_fallback_count + 1 + int(
            bool(settings.get("智能文本匹配", False))
            and bool(str(settings.get("智能文本输入", "") or "").strip())
        )
        settings["模型调用错误"] = [reason]
        _append_runtime_note(settings, note)
        return None
    settings["模型来源实际"] = source
    settings["模型回退说明"] = ""
    settings["模型调用状态"] = "已加载，等待调用"
    return model


_半身景别标签集合 = {"半身", "中景半身", "近景半身"}
_全身动作冲突标签集合 = {
    "披风扬起",
    "踮脚回望",
    "俯身前倾",
    "背部曲线",
    "身体前探",
    "重心偏移",
    "提裙回身",
    "阔步前行",
    "持刀回身",
    "提裙摆",
    "裙摆飞扬",
}
_古风现代冲突标签集合 = {
    "双排扣西装",
    "西装",
    "耳钉",
    "衬衫领带",
    "领带",
    "领结",
    "袖扣",
    "胸针",
    "酒店套房",
    "酒店氛围",
    "豪华套房氛围",
    "落地窗夜景",
    "玻璃幕墙室内",
    "雨巷",
}
_古风服装标签集合 = {
    "汉服",
    "唐装",
    "宋制",
    "明制",
    "魏晋",
    "仙侠",
    "武侠",
    "宫廷",
    "玄幻古风",
    "袄裙",
    "马面裙",
    "中式盘扣",
    "国潮新中式",
    "披帛",
    "香云纱",
    "苏绣",
    "帷帽",
    "步摇",
    "花钿",
    "簪花",
}
_现代正式服装标签集合 = {
    "双排扣西装",
    "西装",
    "衬衫领带",
    "领带",
    "领结",
    "袖扣",
    "胸针",
    "商务休闲",
    "礼服",
    "长款风衣",
    "宽肩大衣",
}
_私密服装标签集合 = {
    "睡裙",
    "浴袍",
    "比基尼",
    "连体泳衣",
    "内衣风",
    "丝质睡袍",
    "吊带睡裙",
    "浴巾裹身",
    "裹身床单",
    "裸肩上衣",
    "露背礼服",
    "开衩礼服",
}
_圣所场景标签集合 = {"废弃教堂", "教堂", "宗教圣所"}
_私密场景扩展标签集合 = {"酒店套房", "酒店氛围", "豪华套房氛围", "落地窗夜景", "卧室"}
_都市雨景场景标签集合 = {"雨巷", "小巷", "街道", "城市", "霓虹雨夜"}
_古风场景锚点标签集合 = {"古风建筑", "月下庭院", "竹林", "古建道场", "中式书房", "月洞门", "水榭", "江南湖畔", "回廊", "宫殿"}
_运行随机风格隔离标签族 = {
    "真实感": {"真实感", "照片级", "写实摄影", "自然写实图像", "欧美风", "港风", "杂志感", "杂志编辑摄影", "时尚写真", "纪实抓拍", "生活电影剧照", "街拍", "黑白摄影", "高对比黑白", "商业广告大片", "时装广告大片", "棚拍", "写真", "私房写真", "手机抓拍", "无滤镜直出", "夜间闪光摄影"},
    "插画感": {"插画感", "水彩线稿", "水彩", "后印象派", "厚涂", "手绘画风", "90年代复古未来动漫", "OVA风", "怀旧动画", "复古动画", "洛可可", "复古未来主义", "动漫", "二次元", "赛璐璐"},
    "CG感": {"CG感", "电影级CG", "概念设计稿", "虚幻引擎", "3D渲染", "Octane渲染", "PBR渲染", "游戏风", "赛博朋克", "未来科技感", "机能赛博", "义体美学"},
    "古风": {"古风", "古风电影剧照", "玄幻古风", "国风美学", "古装定格", "工笔重彩", "水墨", "水墨写意", "宋韵美学", "武侠定格", "江湖传奇", "侠客定格", "工笔武行"},
    "神话感": {"神话感", "神圣史诗", "魔幻现实主义", "暗黑奇幻", "冰雪奇幻", "神圣", "神性幻境", "神话史诗感", "神话叙事"},
}
_运行随机风格隔离标签族["插画感"].update({"日式奇幻动画", "漆原智志画风", "结城信辉画风", "童话绘本", "魔幻油画", "精细赛璐璐", "柔和赛璐璐", "90年代奇幻OVA质感"})
_运行随机风格隔离标签族["CG感"].update({"奇幻概念设计", "史诗奇幻海报", "史诗概念艺术完成度", "奇幻角色设定"})
_运行随机风格隔离标签族["神话感"].update({"奇幻风格", "西方奇幻", "高等奇幻", "剑与魔法", "哥特奇幻", "黑暗童话", "精灵幻想", "梦幻奇境"})
_古风场景冲突标签集合 = {
    "办公室",
    "教室",
    "咖啡厅",
    "图书馆",
    "甜品店",
    "酒店套房",
    "摄影棚",
    "衣帽间",
    "餐厅包厢",
    "玻璃幕墙室内",
    "教堂",
    "地铁车厢",
    "地下通道",
    "现代公寓",
    "独立书店",
    "红毯入口",
    "影棚纯色背景",
    "未来都市",
    "霓虹街区",
    "太空船机库",
    "工业废墟",
    "酒吧",
    "夜店",
    "落地窗夜景",
}
_古风服装冲突标签集合 = {
    "比基尼",
    "连体泳衣",
    "睡裙",
    "浴袍",
    "衬衫男友风",
    "男友风",
    "工装",
    "商务休闲",
    "西装",
    "礼服",
    "休闲",
    "运动",
    "夹克",
    "风衣",
    "皮衣",
    "T恤",
    "毛衣",
    "卫衣",
    "白衬衫",
    "吊带裙",
    "束腰礼服",
    "机能外套",
    "战术服",
    "oversized",
    "裸肩上衣",
    "吊带",
    "高跟鞋",
    "吊袜带",
    "衬衫领带",
    "双排扣西装",
    "长款风衣",
    "机能工装",
    "皮质夹克",
    "高领毛衣",
    "宽肩大衣",
    "短裙",
    "牛仔裤",
    "西裤",
    "阔腿裤",
    "短裤",
    "修身礼服",
    "鱼尾裙",
    "露肩礼服",
    "露背礼服",
    "小香风",
    "针织长裙",
    "百褶短裙",
    "吊带长裙",
    "旗袍开衩",
    "宫廷裙摆",
    "薄纱罩裙",
    "丝质睡袍",
    "影棚礼服",
    "白色迷你连衣裙",
    "牛仔套装",
    "亮片高领长裙",
    "浅蓝健身套装",
    "滑板街头穿搭",
}
_人形奇幻映射 = {"小精灵": "银发精灵"}
_人类身份线索标签集合 = {
    "偶像",
    "学生",
    "OL",
    "调酒师",
    "律师",
    "特工",
    "摄影师",
    "乐队主唱",
    "成年女性",
    "成年男性",
    "中年女性",
    "中年男性",
}
_暧昧成人线索标签集合 = {"暧昧", "无遮挡感", "背部曲线", "微醺感", "私密氛围", "成人向", "私房", "酒店氛围"}
_成人向成熟主体锚点集合 = {"成年女性", "成年男性", "中年女性", "中年男性", "御姐", "成熟", "妩媚", "性感"}
_成人向成熟默认主体锚点 = "成年女性"
_成人向成熟幼态风险标签集合 = {
    "少女",
    "少年",
    "儿童",
    "学生",
    "幼态",
    "稚嫩",
    "萝莉",
    "萝莉感",
    "娇小",
    "JK",
    "校服",
    "校园",
    "教室",
    "课堂",
    "百褶短裙",
}
_成人向成熟青春校园安全映射 = {
    "少女": ["成年女性", "青春感"],
    "少年": ["成年男性", "青春感"],
    "学生": ["成年女性", "学院风"],
    "校园": ["大学校园"],
    "教室": ["大学教室"],
    "课堂": ["大学课堂"],
    "校服": ["学院风穿搭"],
    "JK": ["学院风穿搭"],
    "百褶短裙": ["学院风穿搭"],
    "娇小": ["成年女性"],
}
_发型互斥标签集合 = {
    "长直发",
    "波浪卷发",
    "高马尾",
    "低马尾",
    "麻花辫",
    "发髻",
    "盘发",
    "披发",
    "散发",
    "公主切",
    "丸子头",
    "齐刘海",
    "短碎发",
    "中分短发",
    "背头",
    "寸头",
    "狼尾短发",
    "黑长直",
    "银白长发",
    "湿发",
}
_成人向成熟场景族 = OrderedDict(
    {
        "wet_private": {"蒸汽浴室", "湿滑瓷砖", "湿身淋浴", "泡沫滑落", "浴室", "浴缸", "浴后水汽", "温泉雾气", "桑拿房"},
        "private": {"卧室", "酒店套房", "酒店氛围", "豪华套房氛围", "落地窗夜景", "晨光卧室", "晨光私房"},
        "studio": {"摄影棚", "影棚纯色背景", "影棚礼服"},
        "domestic": {"厨房", "客厅", "阳台", "现代公寓"},
        "outdoor": {"雪地", "海边", "森林", "公园", "城市", "街道", "花园", "雨中", "屋顶"},
        "fantasy": {"幻境", "梦境", "异世界", "魔法森林", "神殿", "云海", "星空"},
        "nightlife": {"酒吧", "夜店", "霓虹都市", "霓虹雨夜", "霓虹小巷"},
    }
)
_成人向成熟场景优先级 = ["wet_private", "private", "studio", "nightlife", "domestic", "outdoor", "fantasy"]
_成人向成熟私密服装集合 = {
    "内衣风",
    "吊带睡裙",
    "睡裙",
    "浴袍",
    "丝质睡袍",
    "透明睡袍",
    "半裸湿透衬衫",
    "衬衫男友风",
    "浴巾裹身",
    "裹身床单",
    "透肤薄纱",
    "湿身薄纱",
    "比基尼",
    "连体泳衣",
}
_成人向成熟服装优先级 = ["吊带睡裙", "丝质睡袍", "睡裙", "浴袍", "透明睡袍", "内衣风", "衬衫男友风", "半裸湿透衬衫"]
_成人向成熟局部特写标记 = {
    "器官特写",
    "阴道特写",
    "阴茎特写",
    "局部身体贴脸",
    "贴脸前景",
    "下半身贴脸",
    "只剩局部身体",
    "紧贴阴道",
    "紧贴乳房",
    "乳房特写",
    "阴部",
    "私处",
    "赤裸渴望",
    "湿润唇部",
}
_成人向成熟直出噪声标记 = {
    "masterpiece",
    "best quality",
    "ultra-detailed",
    "high resolution",
    "女人抱着一个男的身体",
    "男的身体",
}
_成人向成熟自定义分组归位 = {
    "蒸汽浴室": "场景背景",
    "湿滑瓷砖": "场景背景",
    "湿身淋浴": "场景背景",
    "泡沫滑落": "场景背景",
    "彩色霓虹光": "光影氛围",
    "霓虹反射": "技术画质",
    "汗湿皮肤": "技术画质",
    "镜面倒影": "技术画质",
    "湿润皮肤": "技术画质",
}
_成人向成熟构图噪声标签集合 = {
    "前景遮挡",
    "大面积前景遮挡",
    "过度环境遮挡",
    "浓雾遮挡",
    "烟雾遮挡",
    "厚重披帛遮挡",
    "厚重长袍遮挡",
}
_成人向成熟近景风险标签集合 = {"肩部以上特写", "特写", "极近景", "面部特写", "局部特写"}
_成人向成熟稳定景别标签 = "全景全身"
_成人向成熟动作收敛标签集合 = {
    "双人互动",
    "抬臂撑墙",
    "倚靠栏杆",
    "坐姿",
    "跪姿",
    "回眸",
    "侧身站姿",
    "抬手撩发",
    "手扶栏杆",
    "站姿",
}
_成人向成熟动作优先级 = ["倚靠栏杆", "抬臂撑墙", "回眸", "侧身站姿", "坐姿", "抬手撩发", "手扶栏杆", "站姿", "双人互动"]
_成人向成熟写实风格冲突集合 = {
    "手办风",
    "后印象派",
    "洛可可",
    "油画",
    "水彩",
    "插画",
    "厚涂",
    "赛璐璐",
    "OVA风",
    "二次元",
    "Q版",
    "复古未来主义",
    "赛博朋克",
    "机能赛博",
    "义体美学",
}
_成人向成熟道具冲突集合 = {"武器", "枪", "刀", "剑", "法器", "能量刀", "光刃", "全息界面", "广告屏街谷"}
_成人向成熟分组上限 = {
    "主体": 4,
    "画面风格": 3,
    "成人向表达": 3,
    "光影氛围": 3,
    "构图视角": 3,
    "动作姿态": 1,
    "场景背景": 3,
    "道具世界观": 1,
    "技术画质": 3,
}
_成人向成熟分组优先级 = {
    "主体": ["成年女性", "成年男性", "中年女性", "中年男性", "湿发", "银白长发", "黑长直", "成熟", "御姐", "霸气", "妩媚", "丰满"],
    "画面风格": ["杂志编辑摄影", "照片级", "真实感", "私房写真", "杂志感", "时尚写真", "港风", "胶片感"],
    "成人向表达": ["内衣风", "吊带睡裙", "丝质睡袍", "私房", "轻熟感", "高级性感", "贴身布料感", "微醺感"],
    "光影氛围": ["玫瑰粉调", "彩色霓虹光", "霓虹光", "高饱和", "柔光", "暖色调", "迷离", "慵懒", "私密氛围", "诡异"],
    "构图视角": ["全景全身", "全身", "中景", "中景半身", "近景半身", "85mm人像镜头", "杂志封面构图", "平视", "人物居中"],
    "动作姿态": ["倚靠栏杆", "抬臂撑墙", "回眸", "侧身", "扶发", "坐姿慵懒", "站姿放松"],
    "场景背景": ["蒸汽浴室", "浴室", "湿滑瓷砖", "湿身淋浴", "浴缸", "温泉雾气", "泡沫滑落", "酒店套房", "落地窗夜景"],
    "道具世界观": ["面具", "花束", "酒杯", "扇", "伞"],
    "技术画质": ["汗湿皮肤", "镜面倒影", "16K", "高细节", "皮肤纹理", "发丝细节", "霓虹反射", "霓虹反射克制", "社论修图质感"],
}
_情绪冲突清理规则 = [
    ({"压抑", "禁欲感", "克制"}, {"治愈", "温馨", "活泼", "童趣"}),
    ({"暧昧", "欲感", "私密氛围"}, {"童趣", "神圣"}),
    ({"神圣", "庄严"}, {"活泼", "童趣"}),
]


def _safe_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except Exception:
        return default


def _safe_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        return max(low, min(high, float(value)))
    except Exception:
        return default


_TAG_SEPARATOR_TRANSLATION = str.maketrans({"，": ",", "、": ",", "；": ",", ";": ",", "|": ","})


def _parse_tags(
    value: Any,
    *,
    max_chars: int = 131_072,
    max_items: int = 512,
    max_item_chars: int = 4_096,
) -> list[str]:
    if value is None or int(max_chars) <= 0 or int(max_items) <= 0 or int(max_item_chars) <= 0:
        return []
    if isinstance(value, (dict, list, tuple, set)):
        return []
    text = str(value)[: int(max_chars)].translate(_TAG_SEPARATOR_TRANSLATION)
    seen: set[str] = set()
    out: list[str] = []
    scan_limit = int(max_items) * 4
    for raw_index, raw_tag in enumerate(re.split(r"[,\n\r\t]+", text)):
        if raw_index >= scan_limit:
            break
        tag = raw_tag.strip()[: int(max_item_chars)].rstrip()
        if not tag:
            continue
        compact = re.sub(r"\s+", "", tag)
        if compact.casefold() in {"[]", "{}", "()", "（）", "【】", "null", "none", "undefined"}:
            continue
        if compact and not compact.strip("[]{}()（）【】"):
            continue
        if tag not in seen:
            seen.add(tag)
            out.append(tag)
            if len(out) >= int(max_items):
                break
    return out


def _uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _group_tags(group_name: str) -> list[str]:
    try:
        return ["无", *展平标签分类(group_name)]
    except Exception:
        return ["无"]


def _all_tag_groups() -> list[tuple[str, int, list[str]]]:
    return [(str(group["name"]), int(group["slots"]), _group_tags(str(group["name"]))) for group in 分组配置]


def _tag_group_index_from_groups(tag_groups: list[tuple[str, int, list[str]]]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for name, _, tags in tag_groups:
        for tag in tags:
            if tag != 无标签 and tag not in mapping:
                mapping[tag] = name
    return mapping


def _tag_group_index() -> dict[str, str]:
    return _tag_group_index_from_groups(_all_tag_groups())


def _tag_catalog_snapshot() -> tuple[
    list[tuple[str, int, list[str]]],
    dict[str, str],
    dict[str, frozenset[str]],
]:
    """Build one internally consistent tag catalog for a single execution."""

    groups = _all_tag_groups()
    index = _tag_group_index_from_groups(groups)
    memberships = {
        group_name: frozenset(tag for tag in tags if tag != 无标签)
        for group_name, _slot_count, tags in groups
    }
    return groups, index, memberships


def _pick(rng: random.Random, items: list[str]) -> str | None:
    return rng.choice(items) if items else None


def _collect_selected(
    kwargs: dict[str, Any],
    *,
    tag_groups: list[tuple[str, int, list[str]]] | None = None,
) -> tuple[OrderedDict[str, list[str]], list[str]]:
    selected: OrderedDict[str, list[str]] = OrderedDict()
    for group_name, slot_count, _ in tag_groups if tag_groups is not None else _all_tag_groups():
        items: list[str] = []
        for index in range(1, slot_count + 1):
            raw_value = kwargs.get(f"{group_name}标签{index}", "")
            value = "" if isinstance(raw_value, (dict, list, tuple, set)) else str(raw_value)[:512].strip()
            if value and value != 无标签 and value not in items:
                items.append(value)
        selected[group_name] = items
    custom = _parse_tags(
        kwargs.get("自定义补充标签", ""),
        max_chars=32_768,
        max_items=256,
        max_item_chars=512,
    )
    return selected, custom


def _collect_all_tags(selected: OrderedDict[str, list[str]], custom: list[str]) -> list[str]:
    return _uniq([tag for tags in selected.values() for tag in tags] + custom)


def _remove_tag_from_state(selected: OrderedDict[str, list[str]], custom_tags: list[str], tag: str) -> None:
    text = str(tag).strip()
    if not text:
        return
    for group_name in list(selected.keys()):
        selected[group_name] = [item for item in selected[group_name] if item != text]
    custom_tags[:] = [item for item in custom_tags if item != text]


def _append_tag_to_state(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    tag: str,
    *,
    preferred_group: str | None = None,
    tag_group_index: dict[str, str] | None = None,
    tag_group_memberships: dict[str, frozenset[str]] | None = None,
) -> None:
    text = str(tag).strip()
    if not text:
        return
    current_tags = _collect_all_tags(selected, custom_tags)
    if text in current_tags:
        return
    resolved_index = tag_group_index if tag_group_index is not None else _tag_group_index()
    indexed_group = resolved_index.get(text)
    preferred_tags = (
        tag_group_memberships.get(preferred_group, frozenset())
        if preferred_group and tag_group_memberships is not None
        else frozenset(_group_tags(preferred_group)) if preferred_group else frozenset()
    )
    preferred_is_valid = bool(
        preferred_group
        and preferred_group in selected
        and text in preferred_tags
    )
    group_name = preferred_group if preferred_is_valid else indexed_group
    if group_name and group_name in selected:
        limit = _分组槽位上限.get(group_name, len(selected[group_name]) + 1)
        if len(selected[group_name]) < limit:
            selected[group_name].append(text)
            return
    if text not in custom_tags:
        custom_tags.append(text)


def _normalize_inference_state(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    tag_group_index: dict[str, str] | None = None,
    tag_group_memberships: dict[str, frozenset[str]] | None = None,
) -> tuple[OrderedDict[str, list[str]], list[str], list[str]]:
    return _normalize_inference_state_impl(
        selected,
        custom_tags,
        settings,
        collect_all_tags=_collect_all_tags,
        remove_tag_from_state=_remove_tag_from_state,
        append_tag_to_state=lambda next_selected, next_custom_tags, tag: _append_tag_to_state(
            next_selected,
            next_custom_tags,
            tag,
            tag_group_index=tag_group_index,
            tag_group_memberships=tag_group_memberships,
        ),
        uniq=_uniq,
        context={
            "ancient_modern_conflicts": _古风现代冲突标签集合,
            "humanoid_fantasy_map": _人形奇幻映射,
            "human_identity_tags": _人类身份线索标签集合,
            "sacred_scene_tags": _圣所场景标签集合,
            "private_scene_tags": _私密场景扩展标签集合,
            "urban_rain_scene_tags": _都市雨景场景标签集合,
            "ancient_scene_anchor_tags": _古风场景锚点标签集合,
            "ancient_scene_conflict_tags": _古风场景冲突标签集合,
            "ancient_style_clothing_conflicts": _古风服装冲突标签集合,
            "ambiguous_adult_tags": _暧昧成人线索标签集合,
            "half_body_shot_tags": _半身景别标签集合,
            "full_body_motion_conflicts": _全身动作冲突标签集合,
            "strong_identity_tags": 强设定身份锚点集合,
            "casual_conflict_clothing": 强设定身份生活化服装冲突集合,
            "clothing_core_tags": 服装主线标签集合,
            "ancient_clothing_tags": _古风服装标签集合,
            "modern_formal_clothing_tags": _现代正式服装标签集合,
            "intimate_clothing_tags": _私密服装标签集合,
            "emotion_cleanup_rules": _情绪冲突清理规则,
            "adult_mature_subject_anchors": _成人向成熟主体锚点集合,
            "adult_mature_default_subject_anchor": _成人向成熟默认主体锚点,
            "adult_mature_youth_risk_tags": _成人向成熟幼态风险标签集合,
            "adult_mature_youth_safe_map": _成人向成熟青春校园安全映射,
            "hair_conflict_tags": _发型互斥标签集合,
            "adult_mature_scene_families": _成人向成熟场景族,
            "adult_mature_scene_priority": _成人向成熟场景优先级,
            "adult_mature_intimate_clothing": _成人向成熟私密服装集合,
            "adult_mature_outfit_priority": _成人向成熟服装优先级,
            "adult_mature_closeup_markers": _成人向成熟局部特写标记,
            "adult_mature_direct_noise_markers": _成人向成熟直出噪声标记,
            "adult_mature_composition_noise_tags": _成人向成熟构图噪声标签集合,
            "adult_mature_close_shot_risk_tags": _成人向成熟近景风险标签集合,
            "adult_mature_stable_shot_tag": _成人向成熟稳定景别标签,
            "adult_mature_action_tags": _成人向成熟动作收敛标签集合,
            "adult_mature_action_priority": _成人向成熟动作优先级,
            "adult_mature_realistic_style_conflicts": _成人向成熟写实风格冲突集合,
            "adult_mature_prop_conflicts": _成人向成熟道具冲突集合,
            "adult_mature_custom_group_map": _成人向成熟自定义分组归位,
            "adult_mature_group_limits": _成人向成熟分组上限,
            "adult_mature_group_priorities": _成人向成熟分组优先级,
            "default_person_shot_tag": "全景全身",
            "default_quality_anchor_tag": "高细节",
            "nsfw_workspace_signal_terms": _NSFW_WORKSPACE_SIGNAL_TERMS,
            "quality_anchor_tags": {"16K", "8K", "高质量", "高细节", "材质细节丰富", "清晰对焦", "超清画质", "高分辨率", "真实材质", "自然解剖", "手部自然", "主体结构完整"},
            "person_shot_tags": {
                "大全景",
                "大远景",
                "远景",
                "全景",
                "全景全身",
                "全身",
                "中景",
                "中景半身",
                "近景",
                "近景半身",
                "半身",
                "肩部以上特写",
                "面部特写",
                "特写",
                "局部特写",
            },
            "prompt_noise_tags": {"True", "False", "true", "false", "自动", "标准", "详细", "简洁", "低保真", "none", "null"},
            "style_positive_exclusion_terms": _STYLE_POSITIVE_EXCLUSION_TERMS,
            "runtime_style_isolation_families": _运行随机风格隔离标签族,
            "danbooru_visual_intent_families": DANBOORU_VISUAL_INTENT_FAMILIES,
            "danbooru_reference_sheet_tags": DANBOORU_REFERENCE_SHEET_TAGS,
            "danbooru_reference_sheet_balance_tags": DANBOORU_REFERENCE_SHEET_BALANCE_TAGS,
            "danbooru_reference_sheet_background_tags": DANBOORU_REFERENCE_SHEET_BACKGROUND_TAGS,
            "danbooru_reference_sheet_dynamic_tags": DANBOORU_REFERENCE_SHEET_DYNAMIC_TAGS,
        },
    )


def _merge_inference_notes(settings: dict[str, Any], notes: list[str]) -> None:
    existing = [str(note).strip() for note in settings.get("推理纠偏说明", []) if str(note).strip()]
    for note in notes:
        text = str(note).strip()
        if text and text not in existing:
            existing.append(text)
    settings["推理纠偏说明"] = existing


def _base_template_style(style: str) -> str:
    return resolve_base_template_style(style, default="真实感")


def _infer_template_style(tags: list[str], explicit: str) -> str:
    if explicit != "自动":
        return explicit
    if not tags:
        return "真实感"
    scores = {name: 0 for name in 模板推断关键词}
    tag_set = set(tags)
    for name, keywords in 模板推断关键词.items():
        for keyword in keywords:
            if keyword in tag_set:
                scores[name] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "真实感"


def _ordered_profile_history(settings: dict[str, Any]) -> list[str]:
    history: list[str] = []
    loader = globals().get("_random_history")
    history_key = settings.get("cache_key") if "cache_key" in settings else settings.get("unique_id", "")
    if callable(loader) and str(history_key or "").strip():
        try:
            history.extend(
                str(item).strip()
                for item in loader(str(history_key).strip())
                if str(item).strip()
            )
        except Exception:
            pass
    history.extend(_parse_tags(settings.get("随机补充避重缓存", "")))
    return [item for item in history if item and not item.startswith("diversity:")]


def _choose_ordered_profile_variant(
    variants: list[dict[str, Any]],
    settings: dict[str, Any],
    *,
    namespace: str,
    track: str,
    marker_prefix: str,
    cursor_prefix: str,
    signature_fn,
) -> tuple[dict[str, Any], int]:
    if not variants:
        return {}, -1

    signatures = [str(signature_fn(variant)).strip() for variant in variants]
    seed = _safe_int(settings.get("seed", 0), 0, 0, _SEED_MAX)
    start = 0 if seed == 0 else (seed + sum(ord(char) for char in f"{namespace}|{track}")) % len(variants)
    order = [*range(start, len(variants)), *range(0, start)]
    history = _ordered_profile_history(settings)

    last_index: int | None = None
    for item in history:
        if not cursor_prefix or not item.startswith(cursor_prefix):
            continue
        try:
            parsed_index = int(item[len(cursor_prefix):].strip())
        except Exception:
            continue
        if 0 <= parsed_index < len(variants):
            last_index = parsed_index
            break

    marker_to_index = {
        f"{marker_prefix}{signature}": index
        for index, signature in enumerate(signatures)
        if signature
    }
    if last_index is None:
        last_index = next((marker_to_index[item] for item in history if item in marker_to_index), None)

    if last_index is None and history:
        recent_values: set[str] = set(history)
        for item in history:
            if ":" in item:
                recent_values.add(item.split(":", 1)[1].strip())
        overlaps = [
            len(
                {
                    str(tag).strip()
                    for tag, _group in variant.get("tags", [])
                    if str(tag).strip()
                }
                & recent_values
            )
            for variant in variants
        ]
        if overlaps and max(overlaps) > 0 and overlaps.count(max(overlaps)) == 1:
            last_index = overlaps.index(max(overlaps))

    if last_index is None or len(variants) == 1:
        selected_index = order[0]
    else:
        order_position = order.index(last_index) if last_index in order else -1
        selected_index = order[(order_position + 1) % len(order)]
    return variants[selected_index], selected_index


def _apply_random_theme_pool_bias(
    template_style: str,
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    tag_group_index: dict[str, str] | None = None,
    tag_group_memberships: dict[str, frozenset[str]] | None = None,
) -> tuple[str, OrderedDict[str, list[str]], list[str]]:
    pool = str(settings.get("随机主题池", "自动") or "自动").strip()
    if pool == "自动":
        return template_style, selected, custom_tags

    next_selected = OrderedDict((group_name, list(tags)) for group_name, tags in selected.items())
    next_custom = list(custom_tags)

    def add_tag(tag: str, preferred_group: str | None = None) -> None:
        _append_tag_to_state(
            next_selected,
            next_custom,
            tag,
            preferred_group=preferred_group,
            tag_group_index=tag_group_index,
            tag_group_memberships=tag_group_memberships,
        )

    explicit_template_style = str(settings.get("模板风格", "自动") or "自动").strip()

    def themed_style(style: str) -> str:
        return style if explicit_template_style in {"", "自动"} else template_style

    theme_variants: dict[str, list[dict[str, Any]]] = {
        "写实生活": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("生活电影剧照", "画面风格"), ("街道", "场景背景"), ("自然光", "光影氛围")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("纪实抓拍", "画面风格"), ("雨后街头", "场景背景"), ("阴天", "光影氛围")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("街拍", "画面风格"), ("咖啡厅", "场景背景"), ("窗边光", "光影氛围")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("手机抓拍", "画面风格"), ("城市街边", "场景背景"), ("黄昏", "光影氛围")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("生活方式广告", "画面风格"), ("便利店门口", "场景背景"), ("傍晚自然光", "光影氛围"), ("手持饮料", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("都市纪实", "画面风格"), ("居民楼走廊", "场景背景"), ("顶光", "光影氛围"), ("回头看向镜头", "动作姿态")]},
        ],
        "商业摄影": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("商业广告大片", "画面风格"), ("白棚", "场景背景"), ("硬光", "光影氛围"), ("全景全身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("品牌大片", "画面风格"), ("极简影棚", "场景背景"), ("轮廓光", "光影氛围"), ("手提包", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("中画幅", "画面风格"), ("玻璃橱窗", "场景背景"), ("柔光", "光影氛围"), ("85mm人像镜头", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("产品广告", "画面风格"), ("金属展台", "场景背景"), ("高对比", "光影氛围"), ("材质细节丰富", "技术画质")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("Lookbook", "画面风格"), ("纯色背景", "场景背景"), ("自然阴影", "光影氛围"), ("站姿挺拔", "动作姿态")]},
        ],
        "时尚大片": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("杂志编辑摄影", "画面风格"), ("影棚", "场景背景"), ("聚光灯", "光影氛围"), ("高定礼服", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("时尚成片感", "画面风格"), ("城市天台", "场景背景"), ("日落逆光", "光影氛围"), ("风吹发丝", "动作姿态")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("封面肖像", "画面风格"), ("暗色布景", "场景背景"), ("侧光", "光影氛围"), ("近景半身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("高级定制大片", "画面风格"), ("大理石大厅", "场景背景"), ("冷暖混合光", "光影氛围"), ("细跟高跟鞋", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("胶片时装片", "画面风格"), ("旧酒店大堂", "场景背景"), ("暖色调", "光影氛围"), ("手拿包", "动作姿态")]},
        ],
        "糖水写真": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("糖水片", "画面风格"), ("樱花树下", "场景背景"), ("柔光", "光影氛围"), ("全景全身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("写真", "画面风格"), ("花海", "场景背景"), ("自然光", "光影氛围"), ("全景全身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("日系", "画面风格"), ("玻璃温室", "场景背景"), ("奶油色调", "光影氛围"), ("全景全身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("韩系", "画面风格"), ("湖畔夕照", "光影氛围"), ("湖畔", "场景背景"), ("全景全身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("清新写真", "画面风格"), ("白色窗帘", "场景背景"), ("窗边光", "光影氛围"), ("浅景深", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("奶油胶片", "画面风格"), ("草坪", "场景背景"), ("光斑", "光影氛围"), ("坐姿放松", "动作姿态")]},
        ],
        "旅行街拍": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("旅行街拍", "画面风格"), ("老城街巷", "场景背景"), ("午后自然光", "光影氛围"), ("手持相机", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("胶片旅行照", "画面风格"), ("火车站台", "场景背景"), ("黄昏", "光影氛围"), ("行李箱", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("城市漫游", "画面风格"), ("桥上人行道", "场景背景"), ("阴天柔光", "光影氛围"), ("背包", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("度假纪实", "画面风格"), ("民宿露台", "场景背景"), ("晨光", "光影氛围"), ("倚靠栏杆", "动作姿态")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("旅拍大片", "画面风格"), ("石板路", "场景背景"), ("侧逆光", "光影氛围"), ("回头看向镜头", "动作姿态")]},
        ],
        "海岸假日": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("海边写真", "画面风格"), ("沙滩", "场景背景"), ("日落逆光", "光影氛围"), ("全景全身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("度假广告", "画面风格"), ("海边栈道", "场景背景"), ("蓝调时刻", "光影氛围"), ("草帽", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("海风纪实", "画面风格"), ("礁石海岸", "场景背景"), ("冷色调", "光影氛围"), ("风吹发丝", "动作姿态")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("夏日胶片", "画面风格"), ("海边公路", "场景背景"), ("高饱和", "光影氛围"), ("太阳镜", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("滨海生活方式", "画面风格"), ("白色阳台", "场景背景"), ("清晨柔光", "光影氛围"), ("咖啡杯", "道具世界观")]},
        ],
        "森林自然": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("自然人像", "画面风格"), ("森林小径", "场景背景"), ("叶隙斑驳光", "光影氛围"), ("全景全身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("户外写真", "画面风格"), ("溪流边", "场景背景"), ("清晨薄雾", "光影氛围"), ("长裙", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("自然纪录感", "画面风格"), ("山谷草甸", "场景背景"), ("逆光", "光影氛围"), ("远山", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("森系写真", "画面风格"), ("苔藓石阶", "场景背景"), ("低饱和", "光影氛围"), ("侧脸构图", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("野外生活方式", "画面风格"), ("木屋门前", "场景背景"), ("暖色轮廓逆光", "光影氛围"), ("手持花束", "道具世界观")]},
        ],
        "都市职场": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("杂志感", "画面风格"), ("办公室", "场景背景"), ("窗边光", "光影氛围"), ("全景全身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("商业广告大片", "画面风格"), ("玻璃幕墙室内", "场景背景"), ("高对比", "光影氛围"), ("全景全身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("时尚街拍", "画面风格"), ("城市街边", "场景背景"), ("黄昏", "光影氛围"), ("全景全身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("OOTD", "画面风格"), ("天桥", "场景背景"), ("硬光", "光影氛围"), ("全景全身", "构图视角")]},
        ],
        "夜场电影感": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("电影剧照", "画面风格"), ("夜店", "场景背景"), ("夜晚", "光影氛围")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("王家卫美学", "画面风格"), ("霓虹雨夜", "场景背景"), ("雨夜", "光影氛围")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("夜间闪光摄影", "画面风格"), ("酒吧", "场景背景"), ("直闪抓拍", "光影氛围")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("港风", "画面风格"), ("霓虹小巷", "场景背景"), ("低保真胶片夜景", "光影氛围")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("黑色电影感", "画面风格"), ("地下停车场", "场景背景"), ("冷硬侧光", "光影氛围"), ("低角度", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("音乐现场抓拍", "画面风格"), ("Livehouse", "场景背景"), ("舞台光", "光影氛围"), ("手持麦克风", "道具世界观")]},
        ],
        "私房写实": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("私房写真", "画面风格"), ("卧室", "场景背景"), ("窗纱柔光", "光影氛围"), ("中景半身", "构图视角")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("胶片私房", "画面风格"), ("复古公寓", "场景背景"), ("暖色调", "光影氛围"), ("居家针织", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("轻熟写真", "画面风格"), ("窗边沙发", "场景背景"), ("柔光", "光影氛围"), ("托腮", "动作姿态")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("生活感私房", "画面风格"), ("白色床单", "场景背景"), ("清晨自然光", "光影氛围"), ("慵懒", "光影氛围")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("高级私房", "画面风格"), ("酒店套房", "场景背景"), ("低饱和", "光影氛围"), ("丝质睡裙", "服装造型")]},
        ],
        "运动机能": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("运动摄影", "画面风格"), ("健身房", "场景背景"), ("硬光", "光影氛围"), ("运动套装", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("机能风", "画面风格"), ("城市跑道", "场景背景"), ("清晨逆光", "光影氛围"), ("跑步姿态", "动作姿态")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("户外运动广告", "画面风格"), ("山地公路", "场景背景"), ("高对比", "光影氛围"), ("风衣", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("舞蹈训练纪实", "画面风格"), ("练功房", "场景背景"), ("顶光", "光影氛围"), ("身体拉伸", "动作姿态")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("极限运动大片", "画面风格"), ("天台", "场景背景"), ("夕阳轮廓光", "光影氛围"), ("低角度", "构图视角")]},
        ],
        "古风园林": [
            {"style": "古风", "tags": [("古风", "画面风格"), ("园林仕女", "服装造型"), ("水榭", "场景背景"), ("纸窗天光", "光影氛围")]},
            {"style": "古风", "tags": [("古风", "画面风格"), ("宋韵美学", "画面风格"), ("褙子", "服装造型"), ("月洞门", "场景背景"), ("柔光", "光影氛围")]},
            {"style": "古风", "tags": [("古风", "画面风格"), ("国风美学", "画面风格"), ("竹林", "场景背景"), ("叶隙斑驳光", "光影氛围")]},
            {"style": "古风", "tags": [("古风", "画面风格"), ("玄幻古风", "画面风格"), ("月下庭院", "场景背景"), ("蓝灰月光", "光影氛围")]},
            {"style": "古风", "tags": [("古风", "画面风格"), ("古装剧照感", "画面风格"), ("回廊", "场景背景"), ("烛火暖光", "光影氛围")]},
            {"style": "古风", "tags": [("古风", "画面风格"), ("明制", "服装造型"), ("荷塘", "场景背景"), ("雨后柔光", "光影氛围"), ("油纸伞", "道具世界观")]},
            {"style": "古风", "tags": [("古风", "画面风格"), ("唐风", "服装造型"), ("朱墙宫道", "场景背景"), ("侧逆光", "光影氛围"), ("回眸", "动作姿态")]},
        ],
        "武侠江湖": [
            {"style": "古风", "tags": [("古风", "画面风格"), ("武侠电影感", "画面风格"), ("竹林", "场景背景"), ("青蓝冷雾", "光影氛围"), ("剑", "道具世界观")]},
            {"style": "古风", "tags": [("古风", "画面风格"), ("江湖侠客", "画面风格"), ("客栈门口", "场景背景"), ("烛火暖光", "光影氛围"), ("扶剑而立", "动作姿态")]},
            {"style": "古风", "tags": [("古风", "画面风格"), ("港式武侠", "画面风格"), ("雨夜屋檐", "场景背景"), ("雨夜", "光影氛围"), ("持刀回身", "动作姿态")]},
            {"style": "古风", "tags": [("古风", "画面风格"), ("水墨武侠", "画面风格"), ("山道", "场景背景"), ("远山雾气", "光影氛围"), ("斗笠", "道具世界观")]},
            {"style": "古风", "tags": [("古风", "画面风格"), ("玄幻武侠", "画面风格"), ("悬崖栈道", "场景背景"), ("体积光", "光影氛围"), ("长剑出鞘", "动作姿态")]},
        ],
        "洛可可宫廷": [
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("洛可可", "画面风格"), ("宫殿", "场景背景"), ("暖金柔光", "光影氛围"), ("礼服", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("巴洛克宫廷", "画面风格"), ("金色大厅", "场景背景"), ("烛火", "光影氛围"), ("珠宝项链", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("油画感", "画面风格"), ("复古沙龙", "场景背景"), ("伦勃朗光", "光影氛围"), ("丝绒礼服", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("宫廷时装片", "画面风格"), ("镜厅", "场景背景"), ("水晶吊灯光", "光影氛围"), ("细跟高跟鞋", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("欧式古典", "画面风格"), ("花园露台", "场景背景"), ("清晨柔光", "光影氛围"), ("手持折扇", "道具世界观")]},
        ],
        "神话史诗": [
            {"style": "神话感", "tags": [("神话感", "画面风格"), ("云海", "场景背景"), ("神殿", "场景背景"), ("体积光", "光影氛围")]},
            {"style": "神话感", "tags": [("神话感", "画面风格"), ("神圣史诗", "画面风格"), ("天穹祭坛", "场景背景"), ("圣辉逆光", "光影氛围")]},
            {"style": "神话感", "tags": [("神话感", "画面风格"), ("宗教核", "画面风格"), ("星海神殿", "场景背景"), ("金雾神光", "光影氛围")]},
            {"style": "神话感", "tags": [("神话感", "画面风格"), ("暗黑奇幻", "画面风格"), ("黑铁王座", "场景背景"), ("顶光烟雾", "光影氛围")]},
            {"style": "神话感", "tags": [("神话感", "画面风格"), ("东方神话", "画面风格"), ("山谷圣城", "场景背景"), ("云缝天光", "光影氛围"), ("长袍", "服装造型")]},
            {"style": "神话感", "tags": [("神话感", "画面风格"), ("史诗壁画感", "画面风格"), ("巨构神殿", "场景背景"), ("金色轮廓光", "光影氛围"), ("权杖", "道具世界观")]},
        ],
        "暗黑哥特": [
            {"style": "神话感", "tags": [("神话感", "画面风格"), ("暗黑哥特", "画面风格"), ("哥特教堂", "场景背景"), ("冷月光", "光影氛围"), ("黑色长裙", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("哥特时装片", "画面风格"), ("旧剧院", "场景背景"), ("红雾表现主义打光", "光影氛围"), ("手持玫瑰", "道具世界观")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("暗黑奇幻", "画面风格"), ("黑铁王座", "场景背景"), ("顶光烟雾", "光影氛围"), ("金属冠冕", "道具世界观")]},
            {"style": "插画感", "tags": [("插画感", "画面风格"), ("哥特插画", "画面风格"), ("废弃城堡", "场景背景"), ("蓝灰月光", "光影氛围"), ("乌鸦", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("黑色电影感", "画面风格"), ("雨夜墓园", "场景背景"), ("低调光", "光影氛围"), ("长款大衣", "服装造型")]},
        ],
        "赛博工业": [
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("机库", "场景背景"), ("金属", "服装造型"), ("低角度", "构图视角")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("赛博朋克", "画面风格"), ("霓虹街区", "场景背景"), ("霓虹光", "光影氛围")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("未来感", "画面风格"), ("赛博地铁", "场景背景"), ("全息投影光", "光影氛围")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("PBR渲染", "画面风格"), ("工业废墟", "场景背景"), ("硬光", "光影氛围")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("工业科幻", "画面风格"), ("机械维修舱", "场景背景"), ("警示灯", "光影氛围"), ("机械臂", "道具世界观")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("硬表面科幻", "画面风格"), ("轨道交通站", "场景背景"), ("冷白顶光", "光影氛围"), ("机能外套", "服装造型")]},
            {"id": "fisheye-night", "style": "CG感", "tags": [("机能赛博", "画面风格"), ("城市街道", "场景背景"), ("霓虹光", "光影氛围"), ("鱼眼镜头", "构图视角"), ("广角畸变", "构图视角")]},
        ],
        "东方赛博": [
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("东方赛博", "画面风格"), ("霓虹古街", "场景背景"), ("霓虹雨夜", "光影氛围"), ("全息灯笼", "道具世界观")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("国潮科幻", "画面风格"), ("未来茶馆", "场景背景"), ("青橙色调", "光影氛围"), ("全息界面", "道具世界观")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("新中式赛博", "画面风格"), ("高架桥下", "场景背景"), ("广告屏街谷", "光影氛围"), ("机能汉元素", "服装造型")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("赛博武侠", "画面风格"), ("雨夜屋檐", "场景背景"), ("蓝紫霓虹", "光影氛围"), ("能量刀", "道具世界观")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("东方未来都市", "画面风格"), ("垂直城市", "场景背景"), ("全息投影光", "光影氛围"), ("透明雨伞", "道具世界观")]},
        ],
        "机甲科幻": [
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("机甲设定", "画面风格"), ("机库", "场景背景"), ("硬光", "光影氛围"), ("工程机甲", "主体")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("科幻电影剧照", "画面风格"), ("实验室", "场景背景"), ("冷色调", "光影氛围"), ("侦查机甲", "主体")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("装甲角色", "画面风格"), ("战术整备间", "场景背景"), ("警示灯", "光影氛围"), ("机械外骨骼", "服装造型")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("太空歌剧", "画面风格"), ("飞船走廊", "场景背景"), ("轮廓光", "光影氛围"), ("透明头盔", "道具世界观")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("未来军工", "画面风格"), ("地下基地", "场景背景"), ("低角度", "构图视角"), ("装甲靴", "服装造型")]},
            {"id": "turnaround-sheet", "style": "CG感", "tags": [("角色设计稿", "画面风格"), ("参考设定表", "构图视角"), ("多视角展示", "构图视角"), ("表情组", "构图视角"), ("简单背景", "场景背景"), ("高键光", "光影氛围")]},
        ],
        "废土荒原": [
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("废土电影感", "画面风格"), ("荒漠公路", "场景背景"), ("晒褪色调", "光影氛围"), ("防风披风", "服装造型")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("末日纪实", "画面风格"), ("废弃加油站", "场景背景"), ("硬日光", "光影氛围"), ("背包", "道具世界观")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("沙尘科幻", "画面风格"), ("风蚀城市", "场景背景"), ("沙尘逆光", "光影氛围"), ("护目镜", "道具世界观")]},
            {"style": "真实感", "tags": [("真实感", "画面风格"), ("荒野公路片", "画面风格"), ("废弃车站", "场景背景"), ("黄昏", "光影氛围"), ("长款大衣", "服装造型")]},
            {"style": "CG感", "tags": [("CG感", "画面风格"), ("后启示录", "画面风格"), ("残破高架", "场景背景"), ("低饱和", "光影氛围"), ("金属护具", "服装造型")]},
        ],
        "复古插画": [
            {"style": "插画感", "tags": [("插画感", "画面风格"), ("OVA风", "画面风格"), ("怀旧动画", "画面风格"), ("乡村小道", "场景背景")]},
            {"style": "插画感", "tags": [("插画感", "画面风格"), ("复古动画", "画面风格"), ("复古色调", "光影氛围"), ("城市", "场景背景")]},
            {"style": "插画感", "tags": [("插画感", "画面风格"), ("水彩线稿", "画面风格"), ("花海", "场景背景"), ("低饱和", "光影氛围")]},
            {"style": "插画感", "tags": [("插画感", "画面风格"), ("后印象派", "画面风格"), ("湖畔", "场景背景"), ("暖色调", "光影氛围")]},
            {"style": "插画感", "tags": [("插画感", "画面风格"), ("手绘海报", "画面风格"), ("复古电影院", "场景背景"), ("颗粒质感", "技术画质"), ("暖色灯光", "光影氛围")]},
            {"style": "插画感", "tags": [("插画感", "画面风格"), ("漫画封面感", "画面风格"), ("屋顶", "场景背景"), ("夕阳", "光影氛围"), ("夸张透视", "构图视角")]},
            {"id": "anime-screencap", "style": "复古动画", "tags": [("90年代动画风", "画面风格"), ("动画截图感", "画面风格"), ("城市街道", "场景背景"), ("牛仔景别", "构图视角"), ("VHS噪点", "技术画质")]},
        ],
    }
    theme_variants.update(FANTASY_THEME_VARIANTS)
    theme_variants.update(EXPANDED_THEME_VARIANTS)

    variants = theme_variants.get(pool, [])
    if variants:
        def variant_signature(candidate: dict[str, Any]) -> str:
            tags = [str(tag).strip() for tag, _group in candidate.get("tags", []) if str(tag).strip()]
            explicit_id = str(candidate.get("id", "") or "").strip()
            return f"{pool}:{explicit_id or '|'.join(tags[:6])}"

        variant, variant_index = _choose_ordered_profile_variant(
            variants,
            settings,
            namespace="theme",
            track=pool,
            marker_prefix="variant:",
            cursor_prefix=f"variantcursor:{pool}:",
            signature_fn=variant_signature,
        )
        variant_tags = [str(tag).strip() for tag, _group in variant.get("tags", []) if str(tag).strip()]
        explicit_variant_id = str(variant.get("id", "") or "").strip()
        variant_signature = f"{pool}:{explicit_variant_id or '|'.join(variant_tags[:6])}"
        markers: list[str] = []
        markers.append(f"variantcursor:{pool}:{variant_index}")
        markers.append(f"variant:{variant_signature}")
        for tag, group_name in variant.get("tags", []):
            add_tag(str(tag), str(group_name))
            markers.append(f"tag:{str(tag).strip()}")
        settings["随机主题池档案标记"] = markers
        return themed_style(str(variant.get("style", template_style))), next_selected, next_custom
    return template_style, next_selected, next_custom


_非人物模板档案禁用分组 = {"成人向表达", "服装造型", "动作姿态"}
_非人物模板档案禁用词 = (
    "人像",
    "肖像",
    "人物",
    "牛仔景别",
    "半身",
    "全身",
    "发丝",
    "发髻",
    "皮肤",
    "身材",
    "手部",
    "解剖",
)


def _apply_template_style_profile_bias(
    template_style: str,
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    tag_group_index: dict[str, str] | None = None,
    tag_group_memberships: dict[str, frozenset[str]] | None = None,
) -> tuple[OrderedDict[str, list[str]], list[str]]:
    configured_style = str(settings.get("模板风格", "自动") or "自动").strip()
    runtime_random_enabled = bool(settings.get("运行时随机标签", False))
    if configured_style in {"", "自动"} and not runtime_random_enabled:
        settings["模板风格档案标记"] = []
        return selected, custom_tags

    style = str(template_style or configured_style or "真实感").strip() or "真实感"
    if style == "自动":
        style = "真实感"
    base_style = _base_template_style(style)

    style_variants: dict[str, list[dict[str, Any]]] = {
        "真实感": [
            {"id": "editorial", "tags": [("真实感", "画面风格"), ("杂志编辑摄影", "画面风格"), ("侧光", "光影氛围"), ("材质细节丰富", "技术画质")]},
            {"id": "documentary", "tags": [("真实感", "画面风格"), ("生活电影剧照", "画面风格"), ("自然光", "光影氛围"), ("纪实抓拍", "画面风格")]},
            {"id": "film", "tags": [("真实感", "画面风格"), ("35mm胶片摄影", "画面风格"), ("低饱和", "光影氛围"), ("胶片颗粒", "技术画质")]},
            {"id": "clean", "tags": [("真实感", "画面风格"), ("中画幅", "画面风格"), ("柔光", "光影氛围"), ("主体突出", "技术画质")]},
            {"id": "cinematic-cowboy", "tags": [("真实感", "画面风格"), ("电影剧照感", "画面风格"), ("牛仔景别", "构图视角"), ("明暗对照", "光影氛围"), ("胶片颗粒", "技术画质")]},
        ],
        "商业摄影": [
            {"id": "white-studio", "tags": [("商业广告大片", "画面风格"), ("白棚", "场景背景"), ("硬光", "光影氛围"), ("清晰产品级质感", "技术画质")]},
            {"id": "brand-campaign", "tags": [("品牌大片", "画面风格"), ("极简影棚", "场景背景"), ("轮廓光", "光影氛围"), ("广告成片质感", "技术画质")]},
            {"id": "lookbook", "tags": [("Lookbook", "画面风格"), ("纯色背景", "场景背景"), ("自然阴影", "光影氛围"), ("服装褶皱真实", "技术画质")]},
            {"id": "product", "tags": [("产品广告", "画面风格"), ("金属展台", "场景背景"), ("高对比", "光影氛围"), ("材质细节丰富", "技术画质")]},
            {"id": "window", "tags": [("中画幅", "画面风格"), ("玻璃橱窗", "场景背景"), ("柔光", "光影氛围"), ("景深层次自然", "技术画质")]},
            {"id": "catalog", "tags": [("商业广告大片", "画面风格"), ("简单背景", "场景背景"), ("居中构图", "构图视角"), ("高键光", "光影氛围"), ("干净线条", "技术画质")]},
        ],
        "时尚编辑": [
            {"id": "cover", "tags": [("杂志编辑摄影", "画面风格"), ("封面肖像", "构图视角"), ("聚光灯", "光影氛围"), ("时尚成片感", "画面风格")]},
            {"id": "couture", "tags": [("高级定制大片", "画面风格"), ("大理石大厅", "场景背景"), ("冷暖混合光", "光影氛围"), ("高定礼服", "服装造型")]},
            {"id": "hotel", "tags": [("胶片时装片", "画面风格"), ("旧酒店大堂", "场景背景"), ("暖色调", "光影氛围"), ("手拿包", "动作姿态")]},
            {"id": "rooftop", "tags": [("时尚成片感", "画面风格"), ("城市天台", "场景背景"), ("日落逆光", "光影氛围"), ("风吹发丝", "动作姿态")]},
        ],
        "电影写实": [
            {"id": "street-film", "tags": [("电影剧照", "画面风格"), ("街道", "场景背景"), ("侧逆光", "光影氛围"), ("生活电影剧照", "画面风格")]},
            {"id": "noir", "tags": [("黑色电影感", "画面风格"), ("地下停车场", "场景背景"), ("冷硬侧光", "光影氛围"), ("低角度", "构图视角")]},
            {"id": "rain", "tags": [("港风", "画面风格"), ("霓虹雨夜", "场景背景"), ("雨夜", "光影氛围"), ("湿沥青反光", "技术画质")]},
            {"id": "quiet", "tags": [("纪实电影摄影", "画面风格"), ("居民楼走廊", "场景背景"), ("顶光", "光影氛围"), ("负空间留白", "构图视角")]},
        ],
        "私房写实": [
            {"id": "window", "tags": [("私房写真", "画面风格"), ("卧室", "场景背景"), ("窗纱柔光", "光影氛围"), ("胶片感", "技术画质")]},
            {"id": "apartment", "tags": [("胶片私房", "画面风格"), ("复古公寓", "场景背景"), ("暖色调", "光影氛围"), ("居家针织", "服装造型")]},
            {"id": "hotel", "tags": [("高级私房", "画面风格"), ("酒店套房", "场景背景"), ("低饱和", "光影氛围"), ("丝质睡裙", "服装造型")]},
            {"id": "morning", "tags": [("生活感私房", "画面风格"), ("白色床单", "场景背景"), ("清晨自然光", "光影氛围"), ("慵懒", "光影氛围")]},
        ],
        "插画感": [
            {"id": "painterly", "tags": [("插画感", "画面风格"), ("厚涂", "画面风格"), ("手绘画风", "画面风格"), ("饱满色彩", "光影氛围")]},
            {"id": "watercolor", "tags": [("插画感", "画面风格"), ("水彩线稿", "画面风格"), ("水彩", "画面风格"), ("柔和色彩", "光影氛围")]},
            {"id": "poster", "tags": [("插画感", "画面风格"), ("手绘海报", "画面风格"), ("颗粒质感", "技术画质"), ("暖色灯光", "光影氛围")]},
            {"id": "cover", "tags": [("插画感", "画面风格"), ("漫画封面感", "画面风格"), ("夸张透视", "构图视角"), ("高细节", "技术画质")]},
            {"id": "cel-diagonal", "tags": [("插画感", "画面风格"), ("赛璐璐上色", "画面风格"), ("对角线构图", "构图视角"), ("双色调", "光影氛围"), ("干净线条", "技术画质")]},
        ],
        "复古动画": [
            {"id": "ova", "tags": [("插画感", "画面风格"), ("OVA风", "画面风格"), ("怀旧动画", "画面风格"), ("低保真", "技术画质")]},
            {"id": "cel", "tags": [("插画感", "画面风格"), ("复古动画", "画面风格"), ("赛璐璐", "画面风格"), ("复古色调", "光影氛围")]},
            {"id": "future", "tags": [("插画感", "画面风格"), ("90年代复古未来动漫", "画面风格"), ("复古未来主义", "画面风格"), ("霓虹夜色", "光影氛围")]},
            {"id": "print", "tags": [("插画感", "画面风格"), ("木刻版画", "画面风格"), ("印刷网点", "技术画质"), ("高对比", "光影氛围")]},
            {"id": "screencap", "tags": [("复古动画", "画面风格"), ("动画截图感", "画面风格"), ("牛仔景别", "构图视角"), ("VHS噪点", "技术画质"), ("倾斜地平线", "构图视角")]},
        ],
        "CG感": [
            {"id": "pbr", "tags": [("CG感", "画面风格"), ("PBR渲染", "画面风格"), ("体积光", "光影氛围"), ("材质细节丰富", "技术画质")]},
            {"id": "concept", "tags": [("CG感", "画面风格"), ("概念设计稿", "画面风格"), ("游戏风", "画面风格"), ("轮廓设计清晰", "技术画质")]},
            {"id": "engine", "tags": [("CG感", "画面风格"), ("虚幻引擎", "画面风格"), ("3D渲染", "画面风格"), ("空间透视", "构图视角")]},
            {"id": "render", "tags": [("CG感", "画面风格"), ("Octane渲染", "画面风格"), ("高光材质", "技术画质"), ("电影感", "技术画质")]},
            {"id": "concept-establishing", "tags": [("CG感", "画面风格"), ("概念艺术", "画面风格"), ("全景建立镜头", "构图视角"), ("鸟瞰视角", "构图视角"), ("漂浮尘埃", "技术画质")]},
        ],
        "东方赛博": [
            {"id": "wuxia", "tags": [("CG感", "画面风格"), ("东方赛博武侠朋克", "画面风格"), ("赛博街区", "场景背景"), ("能量刀", "道具世界观")]},
            {"id": "mecha", "tags": [("CG感", "画面风格"), ("东方赛博机甲", "画面风格"), ("机库", "场景背景"), ("机械外骨骼", "服装造型")]},
            {"id": "neon", "tags": [("CG感", "画面风格"), ("机能赛博", "画面风格"), ("全息界面", "道具世界观"), ("全息投影光", "光影氛围")]},
            {"id": "rain", "tags": [("CG感", "画面风格"), ("赛博雨夜", "画面风格"), ("霓虹雨夜", "场景背景"), ("广告屏反射光", "光影氛围")]},
        ],
        "硬表面科幻": [
            {"id": "hangar", "tags": [("CG感", "画面风格"), ("硬表面科幻", "画面风格"), ("机库", "场景背景"), ("金属反光", "技术画质")]},
            {"id": "lab", "tags": [("CG感", "画面风格"), ("工业科幻", "画面风格"), ("实验室", "场景背景"), ("冷色工业顶光", "光影氛围")]},
            {"id": "ship", "tags": [("CG感", "画面风格"), ("太空歌剧", "画面风格"), ("飞船走廊", "场景背景"), ("透明头盔", "道具世界观")]},
            {"id": "military", "tags": [("CG感", "画面风格"), ("未来军工", "画面风格"), ("地下基地", "场景背景"), ("装甲靴", "服装造型")]},
        ],
        "古风": [
            {"id": "garden", "tags": [("古风", "画面风格"), ("宋韵美学", "画面风格"), ("月洞门", "场景背景"), ("纸窗天光", "光影氛围")]},
            {"id": "drama", "tags": [("古风", "画面风格"), ("古装剧照感", "画面风格"), ("回廊", "场景背景"), ("烛火暖光", "光影氛围")]},
            {"id": "ink", "tags": [("古风", "画面风格"), ("水墨", "画面风格"), ("远山雾气", "光影氛围"), ("负空间留白", "构图视角")]},
            {"id": "fantasy", "tags": [("古风", "画面风格"), ("玄幻古风", "画面风格"), ("月下庭院", "场景背景"), ("蓝灰月光", "光影氛围")]},
        ],
        "国风电影": [
            {"id": "palace", "tags": [("古风电影氛围", "画面风格"), ("宫殿", "场景背景"), ("侧逆光", "光影氛围"), ("丝绸褶裥清晰", "技术画质")]},
            {"id": "garden", "tags": [("园林人像", "画面风格"), ("水榭", "场景背景"), ("柔光", "光影氛围"), ("发髻结构完整", "技术画质")]},
            {"id": "period", "tags": [("古装剧照感", "画面风格"), ("朱墙宫道", "场景背景"), ("日落逆光", "光影氛围"), ("唐风", "服装造型")]},
            {"id": "elegant", "tags": [("国风人像", "画面风格"), ("荷塘", "场景背景"), ("雨后柔光", "光影氛围"), ("油纸伞", "道具世界观")]},
        ],
        "武侠电影": [
            {"id": "bamboo", "tags": [("东方古风武侠", "画面风格"), ("竹林", "场景背景"), ("青蓝冷雾", "光影氛围"), ("剑", "道具世界观")]},
            {"id": "inn", "tags": [("武侠电影感", "画面风格"), ("客栈门口", "场景背景"), ("烛火暖光", "光影氛围"), ("扶剑而立", "动作姿态")]},
            {"id": "rain-roof", "tags": [("港式武侠", "画面风格"), ("雨夜屋檐", "场景背景"), ("雨夜", "光影氛围"), ("持刀回身", "动作姿态")]},
            {"id": "mountain", "tags": [("水墨武侠", "画面风格"), ("山道", "场景背景"), ("远山雾气", "光影氛围"), ("斗笠", "道具世界观")]},
        ],
        "神话感": [
            {"id": "temple", "tags": [("神话感", "画面风格"), ("神圣史诗", "画面风格"), ("天穹祭坛", "场景背景"), ("圣辉逆光", "光影氛围")]},
            {"id": "dunhuang", "tags": [("神话感", "画面风格"), ("敦煌神性", "画面风格"), ("日轮", "道具世界观"), ("云隙光", "光影氛围")]},
            {"id": "cosmic", "tags": [("神话感", "画面风格"), ("星海神殿", "场景背景"), ("金雾神光", "光影氛围"), ("宝石能量晕光", "技术画质")]},
            {"id": "mythic-city", "tags": [("神话感", "画面风格"), ("山谷圣城", "场景背景"), ("云缝天光", "光影氛围"), ("史诗感", "画面风格")]},
        ],
        "暗黑奇幻": [
            {"id": "gothic", "tags": [("神话感", "画面风格"), ("暗黑奇幻", "画面风格"), ("黑铁王座", "场景背景"), ("顶光烟雾", "光影氛围")]},
            {"id": "baroque", "tags": [("神话感", "画面风格"), ("巴洛克", "画面风格"), ("烛火", "光影氛围"), ("权杖", "道具世界观")]},
            {"id": "witch", "tags": [("神话感", "画面风格"), ("巫术暗黑", "画面风格"), ("祭仪场景", "场景背景"), ("神谕石碑", "道具世界观")]},
            {"id": "frost", "tags": [("神话感", "画面风格"), ("冰雪奇幻", "画面风格"), ("冷冽神性", "光影氛围"), ("神性皮肤光泽", "技术画质")]},
        ],
    }
    style_variants.update(FANTASY_TEMPLATE_STYLE_VARIANTS)
    style_variants.update(EXPANDED_TEMPLATE_STYLE_VARIANTS)

    variants = style_variants.get(style) or style_variants.get(base_style, [])
    if not variants:
        settings["模板风格档案标记"] = []
        return selected, custom_tags

    def variant_signature(variant: dict[str, Any]) -> str:
        explicit_id = str(variant.get("id", "") or "").strip()
        tags = [str(tag).strip() for tag, _group in variant.get("tags", []) if str(tag).strip()]
        return f"{style}:{explicit_id or '|'.join(tags[:5])}"

    variant, variant_index = _choose_ordered_profile_variant(
        variants,
        settings,
        namespace="style",
        track=style,
        marker_prefix="stylevariant:",
        cursor_prefix=f"stylevariantcursor:{style}:",
        signature_fn=variant_signature,
    )

    next_selected = OrderedDict((group_name, list(tags)) for group_name, tags in selected.items())
    next_custom = list(custom_tags)
    subject_type = _infer_subject_type(
        _collect_all_tags(next_selected, next_custom),
        str(settings.get("主体类型", "自动") or "自动").strip(),
    )
    markers = [f"stylevariantcursor:{style}:{variant_index}", f"stylevariant:{variant_signature(variant)}"]
    for tag, group_name in variant.get("tags", []):
        cleaned_tag = str(tag).strip()
        if not cleaned_tag:
            continue
        cleaned_group = str(group_name).strip()
        if subject_type == "非人物主体" and (
            cleaned_group in _非人物模板档案禁用分组
            or any(marker in cleaned_tag for marker in _非人物模板档案禁用词)
        ):
            continue
        _append_tag_to_state(
            next_selected,
            next_custom,
            cleaned_tag,
            preferred_group=cleaned_group,
            tag_group_index=tag_group_index,
            tag_group_memberships=tag_group_memberships,
        )
        markers.append(f"styletag:{cleaned_tag}")
    settings["模板风格档案标记"] = markers
    return next_selected, next_custom


def _infer_subject_type(tags: list[str], explicit: str) -> str:
    if explicit != "自动":
        return explicit
    if set(tags) & {"机甲", "机械", "载具", "机器人", "战舰", "飞船", "工程机甲", "防御机甲", "侦查机甲", "步兵机甲", "装甲"}:
        return "非人物主体"
    return "人物角色"


def _infer_output_structure(subject_type: str, explicit: str) -> str:
    if explicit != "自动":
        return explicit
    return "案例分段版" if subject_type == "非人物主体" else "案例长段版"


def _main_scene_group(tags: list[str], template_style: str) -> str:
    tag_set = set(tags)
    base_template_style = _base_template_style(template_style)
    if tag_set & 室内场景标签集合:
        return "indoor"
    if tag_set & 城市街景标签集合:
        return "city"
    if tag_set & 自然户外标签集合:
        return "nature"
    if tag_set & 工业科技标签集合:
        return "industrial"
    if tag_set & 古风东方标签集合:
        return "ancient"
    if tag_set & 神圣仪式标签集合:
        return "sacred"
    if tag_set & 极简背景标签集合:
        return "minimal"
    if base_template_style == "古风":
        return "ancient"
    if base_template_style == "神话感":
        return "sacred"
    return "other"


def _main_identity(tags: list[str]) -> str:
    for tag in tags:
        if tag in 女性身份锚点集合 or tag in 男性身份锚点集合 or tag in 职业持物身份集合 or tag in 强设定身份锚点集合:
            return tag
    for tag in tags:
        if tag in {"成年女性", "成年男性", "中年女性", "中年男性"}:
            return tag
    return ""


def _adult_subpool(tags: list[str]) -> str:
    tag_set = set(tags)
    text = " ".join(tags)
    if any(item in text for item in ["比基尼", "泳装", "海边"]):
        return "swimwear"
    if tag_set & {"成年男性", "中年男性", "男模", "男性角色"} or (tag_set & {"双人互动", "情侣互动"} and any(item in text for item in ["男性", "成年男性", "男模"])):
        return "male_private"
    if any(item in text for item in ["裸体", "全裸", "上空", "裸露", "nude", "topless"]):
        return "nude_controlled"
    if any(item in text for item in ["私房", "卧室", "浴缸", "落地窗夜景", "阳台", "酒店"]):
        return "soft_private"
    return ""


def _style_track(template_style: str, tags: list[str]) -> str:
    tag_set = set(tags)
    base_template_style = _base_template_style(template_style)
    if base_template_style == "真实感":
        if tag_set & {"城市屋顶纪实", "城市天台", "屋顶晾衣架", "日落逆光", "晚风纪实"}:
            return "城市天台纪实"
        if tag_set & {"高端时尚编辑肖像", "时尚编辑商业广告", "大画幅棚拍", "广告成片质感"}:
            return "时尚编辑商业广告"
        if tag_set & {"日韩影像", "日系电影感", "韩系极简影像"}:
            return "日韩影像"
        if tag_set & {"都市电影人文", "纪实电影摄影", "街头纪实", "生活流写实"}:
            return "都市电影人文"
        if tag_set & {"品牌大片", "Lookbook", "中画幅", "生活方式广告"}:
            return "商业摄影"
        if tag_set & {"街拍摄影", "都市纪实", "纪实"}:
            return "生活纪实"
        if tag_set & {"私房写真", "微醺感", "落地窗夜景", "卧室"}:
            return "私房写实"
        return template_style if template_style != base_template_style else "写实人像"
    if base_template_style == "古风":
        if tag_set & {"志怪古风", "国风暗黑志怪", "神谕石碑", "港风惊悚志怪", "雾景实拍感"}:
            return "国风暗黑志怪"
        if tag_set & {"港式武侠", "港式武侠胶片", "东方古风武侠", "武侠剧照感"}:
            return "东方古风武侠"
        if tag_set & {"宋韵美学", "园林仕女", "月洞门", "水榭"}:
            return "古风园林"
        if tag_set & {"武侠", "剑客", "竹林"}:
            return "武侠剧照"
        return template_style if template_style != base_template_style else "古风人像"
    if base_template_style == "CG感":
        if tag_set & {"树灵巨像", "古木守卫", "藤蔓木妖", "工业舱室", "朽木树皮纹理", "苔藓附生质感"}:
            return "工业树灵巨像"
        if tag_set & {"东方赛博武侠朋克", "东方赛博机甲", "能量刀", "全息界面"}:
            return "东方赛博武侠朋克"
        if tag_set & {"赛博朋克", "机能赛博", "霓虹雨夜", "广告屏街谷"}:
            return "赛博雨夜"
        if tag_set & {"机库", "工业展台", "实验室"}:
            return "工业科幻"
        return template_style if template_style != base_template_style else "CG大片"
    if base_template_style == "神话感":
        if tag_set & {"山谷圣城", "巨构神殿", "瀑布峡谷", "远山雪峰", "史诗城市中轴", "山体建筑一体化"}:
            return "山谷圣城史诗"
        if tag_set & {"西方奇幻史诗", "天使机甲", "西方奇幻女战士"}:
            return "西方奇幻神话史诗"
        if tag_set & {"云海", "神殿", "天穹祭坛", "星海神殿"}:
            return "神殿史诗"
        return template_style if template_style != base_template_style else "神话人像"
    if base_template_style == "插画感":
        if tag_set & {"OVA风", "怀旧动画", "复古动画"}:
            return "复古OVA"
        return template_style if template_style != base_template_style else "插画叙事"
    return template_style


def _random_history(node_key: str) -> list[str]:
    with _CACHE_LOCK:
        cache = _cache_bucket_unlocked(node_key) or {}
        return (
            list(cache.get("recent_style_tracks", []))
            + list(cache.get("recent_runtime_markers", []))
            + list(cache.get("recent_prompt_signatures", []))
        )


def _runtime_random_history_markers(node_key: str) -> list[str]:
    with _CACHE_LOCK:
        return list((_cache_bucket_unlocked(node_key) or {}).get("recent_runtime_markers", []))


def _runtime_random_markers_from_tags(
    tags: list[str],
    *,
    tag_group_index: dict[str, str] | None = None,
) -> list[str]:
    tag_index = tag_group_index if tag_group_index is not None else _tag_group_index()
    markers: list[str] = []
    for raw_tag in tags:
        tag = str(raw_tag).strip()
        if not tag or tag == 无标签 or tag in _RUNTIME_RANDOM_HISTORY_STABLE_TAGS:
            continue
        group_name = tag_index.get(tag, "")
        prefix = _RUNTIME_RANDOM_HISTORY_GROUP_PREFIX.get(group_name, "tag")
        markers.append(f"tag:{tag}")
        if prefix != "tag":
            markers.append(f"{prefix}:{tag}")
    return _uniq(markers)


def _runtime_random_markers_from_prompt(
    prompt_list: list[str],
    *,
    tag_groups: list[tuple[str, int, list[str]]] | None = None,
) -> list[str]:
    prompt_text = "\n".join(str(prompt or "") for prompt in prompt_list if str(prompt or "").strip())
    if not prompt_text:
        return []
    group_values = {name: tags for name, _slot_count, tags in tag_groups or []}
    markers: list[str] = []
    for group_name, prefix in _RUNTIME_RANDOM_HISTORY_GROUP_PREFIX.items():
        group_tags = group_values[group_name] if group_name in group_values else _group_tags(group_name)
        for tag in group_tags:
            tag = str(tag).strip()
            if (
                not tag
                or tag == 无标签
                or tag in _RUNTIME_RANDOM_HISTORY_STABLE_TAGS
                or (group_name == "主体" and tag in _RUNTIME_RANDOM_HISTORY_GENERIC_SUBJECTS)
            ):
                continue
            if tag in prompt_text:
                markers.append(f"tag:{tag}")
                markers.append(f"{prefix}:{tag}")
    return _uniq(markers)


def _update_runtime_random_history(
    node_key: str,
    *,
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    generated: list[str],
    prompt_list: list[str],
    extra_markers: list[str] | None = None,
    tag_group_index: dict[str, str] | None = None,
    tag_groups: list[tuple[str, int, list[str]]] | None = None,
) -> list[str]:
    if not str(node_key or "").strip():
        return []
    state_tags: list[str] = []
    for group_name in _RUNTIME_RANDOM_HISTORY_GROUP_PREFIX:
        state_tags.extend(str(tag).strip() for tag in selected.get(group_name, []) if str(tag).strip())
    state_markers = _runtime_random_markers_from_tags(state_tags, tag_group_index=tag_group_index)
    generated_markers = _runtime_random_markers_from_tags(generated, tag_group_index=tag_group_index)
    identity_tags = [
        tag
        for tag in _collect_all_tags(selected, custom_tags)
        if tag in 职业持物身份集合 or tag in 强设定身份锚点集合
    ]
    identity_markers = _runtime_random_markers_from_tags(identity_tags, tag_group_index=tag_group_index)
    prompt_markers = _runtime_random_markers_from_prompt(
        prompt_list,
        tag_groups=tag_groups,
    )
    additional_markers = [str(marker).strip() for marker in (extra_markers or []) if str(marker).strip()]
    markers = _uniq([*additional_markers, *state_markers, *generated_markers, *identity_markers, *prompt_markers])
    if not markers:
        return _runtime_random_history_markers(node_key)
    with _CACHE_LOCK:
        cache = _cache_bucket_unlocked(node_key, create=True)
        if cache is None:
            return []
        history = list(cache.get("recent_runtime_markers", []))
        next_history = [*markers, *[item for item in history if item not in markers]]
        cache["recent_runtime_markers"] = next_history[:_RUNTIME_RANDOM_HISTORY_LIMIT]
        return list(cache["recent_runtime_markers"])


def _update_history(node_key: str, track: str, diversity_signature: str = "") -> list[str]:
    with _CACHE_LOCK:
        cache = _cache_bucket_unlocked(node_key, create=True)
        if cache is None:
            cache = {}
        history = list(cache.get("recent_style_tracks", []))
        track = str(track).strip()
        if track:
            history = [track, *[item for item in history if item != track]][:3]
        diversity_signature = str(diversity_signature).strip()
        if diversity_signature:
            signature_item = f"diversity:{diversity_signature}"
            history = [*history, signature_item]
            deduped: list[str] = []
            for item in history:
                if item in deduped:
                    continue
                deduped.append(item)
            history = deduped[-6:]
        cache["recent_style_tracks"] = history
        return history


def _prompt_history_fingerprints(node_key: str) -> list[str]:
    key = str(node_key or "").strip()
    if not key:
        return []
    with _CACHE_LOCK:
        return list((_cache_bucket_unlocked(key) or {}).get("recent_prompt_signatures", []))


def _update_prompt_history(node_key: str, prompt_list: list[str]) -> list[str]:
    key = str(node_key or "").strip()
    if not key:
        return []
    signatures: list[str] = []
    for prompt in prompt_list:
        prompt_text = str(prompt or "").strip()
        if not prompt_text:
            continue
        signatures.extend(_prompt_history_signatures(prompt_text))
    signatures = _uniq([signature for signature in signatures if signature])
    if not signatures:
        return _prompt_history_fingerprints(key)
    with _CACHE_LOCK:
        cache = _cache_bucket_unlocked(key, create=True)
        if cache is None:
            return []
        history = list(cache.get("recent_prompt_signatures", []))
        next_history = [*signatures, *[item for item in history if item not in signatures]]
        cache["recent_prompt_signatures"] = next_history[:36]
        return list(cache["recent_prompt_signatures"])


def 获取阶段节点输出缓存(node_id: str | None, cache_namespace: str | None = None) -> dict[str, Any] | None:
    key = _resolve_stage_cache_key(node_id, cache_namespace=cache_namespace)
    if not key:
        return None
    with _CACHE_LOCK:
        payload = _cache_bucket_unlocked(key)
        if not isinstance(payload, dict):
            return None
        public_payload = {field: payload[field] for field in _STAGE_OUTPUT_CACHE_PUBLIC_KEYS if field in payload}
        execution_history = payload.get(_STAGE_OUTPUT_EXECUTION_HISTORY_KEY)
        if isinstance(execution_history, list) and execution_history:
            public_payload["execution_history"] = execution_history
        return deepcopy(public_payload)


def _cache_output(node_id: str | None, payload: dict[str, Any]) -> None:
    key = str(node_id or "").strip()
    if not key:
        return
    with _cache_key_lock(key):
        with _CACHE_LOCK:
            cache = _cache_bucket_unlocked(key, create=True)
            if cache is not None:
                updated_at = int(payload.get("updated_at", 0) or 0)
                prompt_text = str(payload.get("prompt_text", "") or "").strip()
                if str(payload.get("status", "") or "").strip().lower() == "done" and updated_at > 0 and prompt_text:
                    sequence = int(cache.get(_STAGE_OUTPUT_EXECUTION_SEQUENCE_KEY, 0) or 0) + 1
                    cache[_STAGE_OUTPUT_EXECUTION_SEQUENCE_KEY] = sequence
                    snapshot = {
                        field: deepcopy(payload[field])
                        for field in _STAGE_OUTPUT_EXECUTION_HISTORY_FIELDS
                        if field in payload
                    }
                    snapshot["execution_id"] = f"{updated_at}:{sequence}"
                    history = [
                        item
                        for item in cache.get(_STAGE_OUTPUT_EXECUTION_HISTORY_KEY, [])
                        if isinstance(item, dict) and item.get("execution_id") != snapshot["execution_id"]
                    ]
                    cache[_STAGE_OUTPUT_EXECUTION_HISTORY_KEY] = [
                        snapshot,
                        *history,
                    ][:_STAGE_OUTPUT_EXECUTION_HISTORY_LIMIT]
                cache.update(payload)


def 构建NSFW工作台目录() -> dict[str, Any]:
    return _build_nsfw_workspace_catalog_impl()


def 应用NSFW工作台到阶段状态(
    workspace: dict[str, Any],
    *,
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    allowed_tags: set[str] | None = None,
    tag_group_index: dict[str, str] | None = None,
) -> dict[str, Any]:
    mapped = _map_nsfw_workspace_to_stage_state_impl(
        workspace,
        tag_group_index=tag_group_index if tag_group_index is not None else _tag_group_index(),
        group_slot_limits=_分组槽位上限,
    )
    if allowed_tags is not None:
        allowed = {str(tag).strip() for tag in allowed_tags if str(tag).strip()}
        mapped["selected"] = OrderedDict(
            (
                group_name,
                [tag for tag in tags if tag in allowed],
            )
            for group_name, tags in mapped["selected"].items()
        )
        mapped["custom_tags"] = [tag for tag in mapped["custom_tags"] if tag in allowed]
    next_selected = OrderedDict((group_name, list(tags)) for group_name, tags in selected.items())
    for group_name, tags in mapped["selected"].items():
        bucket = next_selected.setdefault(group_name, [])
        for tag in tags:
            if tag in bucket:
                continue
            limit = _分组槽位上限.get(group_name, len(bucket))
            if len(bucket) < max(0, int(limit)):
                bucket.append(tag)
            elif tag not in mapped["custom_tags"]:
                mapped["custom_tags"].append(tag)
    next_custom = list(custom_tags)
    for tag in mapped["custom_tags"]:
        text = str(tag).strip()
        if text and text not in next_custom:
            next_custom.append(text)
    protected_tags = _uniq(
        [
            *[tag for tags in mapped["selected"].values() for tag in tags],
            *mapped["custom_tags"],
        ]
    )
    return {
        "selected": next_selected,
        "custom_tags": next_custom,
        "protected_tags": protected_tags,
        "negative_prompt": str(mapped.get("negative_prompt") or "").strip(),
        "negative": dict(mapped.get("negative", {})) if isinstance(mapped.get("negative"), dict) else {},
    }


def _build_state_from_kwargs(
    kwargs: dict[str, Any],
    *,
    tag_groups: list[tuple[str, int, list[str]]] | None = None,
    tag_group_index: dict[str, str] | None = None,
    tag_group_memberships: dict[str, frozenset[str]] | None = None,
) -> tuple[OrderedDict[str, list[str]], list[str], dict[str, Any], str]:
    resolved_groups = tag_groups if tag_groups is not None else _all_tag_groups()
    resolved_index = tag_group_index if tag_group_index is not None else _tag_group_index_from_groups(resolved_groups)
    return _build_state_from_kwargs_impl(
        kwargs,
        collect_selected=lambda values: _collect_selected(values, tag_groups=resolved_groups),
        tag_group_index=lambda: resolved_index,
        group_slot_limits=_分组槽位上限,
        setting_defaults=SETTING_DEFAULTS,
        safe_int=_safe_int,
        safe_float=_safe_float,
        normalize_inference_state=lambda next_selected, next_custom_tags, next_settings: _normalize_inference_state(
            next_selected,
            next_custom_tags,
            next_settings,
            tag_group_index=resolved_index,
            tag_group_memberships=tag_group_memberships,
        ),
        collect_all_tags=_collect_all_tags,
    )


def _build_runtime_tags(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    tag_groups: list[tuple[str, int, list[str]]] | None = None,
    tag_group_index: dict[str, str] | None = None,
) -> tuple[OrderedDict[str, list[str]], list[str], list[str]]:
    resolved_groups = tag_groups if tag_groups is not None else _all_tag_groups()
    resolved_index = tag_group_index if tag_group_index is not None else _tag_group_index_from_groups(resolved_groups)
    return _build_runtime_tags_impl(
        selected,
        custom_tags,
        settings,
        all_tag_groups=lambda: resolved_groups,
        tag_group_index=lambda: resolved_index,
        parse_tags=_parse_tags,
        uniq=_uniq,
        seed_normalizer=_规范化随机种子,
        history_loader=_random_history,
        random_module=random,
        empty_tag=无标签,
    )


def _format_grouped_summary(selected: OrderedDict[str, list[str]], custom_tags: list[str]) -> str:
    return _format_grouped_summary_impl(selected, custom_tags)


def _build_prompt_list(selected: OrderedDict[str, list[str]], custom_tags: list[str], settings: dict[str, Any]) -> list[str]:
    return _build_prompt_list_impl(
        selected,
        custom_tags,
        settings,
        scene_group="",
        identity="",
        style_track="",
        recent_tracks=[],
        uniq=_uniq,
        infer_template_style=_infer_template_style,
        infer_subject_type=_infer_subject_type,
        infer_output_structure=_infer_output_structure,
    )


def _build_negative_prompt(selected: OrderedDict[str, list[str]], custom_tags: list[str], settings: dict[str, Any]) -> str:
    prompt_language = str(settings.get("提示词语言", "纯中文") or "纯中文").strip()
    negative_separator = ", " if prompt_language in {"纯英文", "英文提示词+中文说明"} else "、"
    return _build_negative_prompt_from_state_impl(
        selected,
        custom_tags,
        settings,
        uniq=_uniq,
        adult_tag_keywords=成人向标签关键词,
        adult_low_cover_tags=成人向低遮挡标签集合,
        template_negative_zh=模板附加负面词_ZH,
        template_negative_en=模板附加负面词_EN,
        adult_negative_zh=成人向附加负面词_ZH,
        adult_negative_en=成人向附加负面词_EN,
        low_cover_negative_zh=低遮挡附加负面词_ZH,
        low_cover_negative_en=低遮挡附加负面词_EN,
        composition_negative_zh=成人向构图附加负面词_ZH,
        composition_negative_en=成人向构图附加负面词_EN,
        soft_skin_terms=["过度锐化", "硬光打脸", "法令纹过深", "眼周纹理过重"],
        text_artifact_terms=["文字", "水印", "logo", "铭文", "符文", "字样"],
        single_frame_negative_zh=全局单帧附加负面词_ZH,
        single_frame_negative_en=全局单帧附加负面词_EN,
        duplicate_subject_negative_zh=主体复制附加负面词_ZH,
        duplicate_subject_negative_en=主体复制附加负面词_EN,
        single_subject_negative_zh=单人构图附加负面词_ZH,
        single_subject_negative_en=单人构图附加负面词_EN,
        multi_subject_negative_zh=多主体构图附加负面词_ZH,
        multi_subject_negative_en=多主体构图附加负面词_EN,
        multi_view_negative_zh=多视图一致性附加负面词_ZH,
        multi_view_negative_en=多视图一致性附加负面词_EN,
        separator=negative_separator,
    )


def _runtime_random_preview_state_fingerprint(
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
) -> str:
    normalized_selected = {
        str(group_name): _uniq([str(tag).strip() for tag in tags if str(tag).strip()])
        for group_name, tags in selected.items()
        if isinstance(tags, (list, tuple))
    }
    normalized_settings: dict[str, Any] = {}
    for key in _RUNTIME_RANDOM_PREVIEW_STATE_SETTING_KEYS:
        value = settings.get(key)
        if key == "运行时随机标签":
            normalized_settings[key] = bool(value)
        elif key == "核心标签锁定数量":
            normalized_settings[key] = _safe_int(value, 0, 0, 0x7FFFFFFF)
        elif key == "seed":
            normalized_settings[key] = _safe_int(value, 0, 0, _SEED_MAX)
        else:
            normalized_settings[key] = str(value or "").strip()
    payload = {
        "selected": normalized_selected,
        "custom_tags": _uniq([str(tag).strip() for tag in custom_tags if str(tag).strip()]),
        "settings": normalized_settings,
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _nsfw_workspace_state_fingerprint(workspace: Any) -> str:
    if not isinstance(workspace, dict):
        return ""
    try:
        serialized = json.dumps(workspace, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        return ""
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _new_runtime_random_preview_marker(
    settings: dict[str, Any],
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    custom_tags: list[str],
) -> str:
    token_source = f"{settings.get('unique_id', '')}|{time.time_ns()}|{random.getrandbits(128)}"
    token = hashlib.sha256(token_source.encode("utf-8")).hexdigest()[:32]
    return json.dumps(
        {
            "v": 2,
            "source": "backend",
            "token": token,
            "state_fingerprint": _runtime_random_preview_state_fingerprint(selected, custom_tags, settings),
            "mode": str(settings.get("运行时随机模式解析结果", "") or ""),
            "seed": int(settings.get("运行时随机有效种子", settings.get("seed", 0)) or 0),
            "theme_markers": list(settings.get("随机主题池档案标记", []) or []),
            "style_markers": list(settings.get("模板风格档案标记", []) or []),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _parse_runtime_random_preview_marker(raw_marker: Any) -> dict[str, Any] | None:
    if not isinstance(raw_marker, str):
        return None
    text = raw_marker.strip()
    if not text or len(text) > _RUNTIME_RANDOM_PREVIEW_MARKER_MAX_CHARS:
        return None
    try:
        payload = json.loads(text)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    try:
        version = int(payload.get("v", 0) or 0)
    except (TypeError, ValueError):
        return None
    if version != 2:
        return None
    token = str(payload.get("token") or "").strip()
    state_fingerprint = str(payload.get("state_fingerprint") or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{32}", token) or not re.fullmatch(r"[0-9a-f]{64}", state_fingerprint):
        return None
    source = str(payload.get("source") or "").strip()
    if source != "backend":
        return None

    def marker_list(name: str) -> list[str]:
        values = payload.get(name)
        if not isinstance(values, list):
            return []
        return _uniq(
            [str(item).strip()[:256] for item in values[:64] if not isinstance(item, (dict, list)) and str(item).strip()]
        )

    return {
        "token": token,
        "state_fingerprint": state_fingerprint,
        "source": source,
        "mode": str(payload.get("mode") or "").strip()[:128],
        "seed": _safe_int(payload.get("seed", 0), 0, 0, _SEED_MAX),
        "theme_markers": marker_list("theme_markers"),
        "style_markers": marker_list("style_markers"),
    }


def _consume_runtime_random_preview_marker(
    settings: dict[str, Any],
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    custom_tags: list[str],
) -> dict[str, Any] | None:
    reservation = _reserve_runtime_random_preview_marker(settings, selected, custom_tags)
    if reservation is None:
        return None
    if not _commit_runtime_random_preview_reservation(reservation):
        _release_runtime_random_preview_reservation(reservation)
        return None
    return reservation.marker


def _reserve_runtime_random_preview_marker(
    settings: dict[str, Any],
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    custom_tags: list[str],
    *,
    transaction: _RuntimeRandomPreviewTransaction | None = None,
) -> _RuntimeRandomPreviewReservation | None:
    marker = _parse_runtime_random_preview_marker(settings.get("运行时随机预览令牌"))
    if marker is None:
        return None
    current_fingerprint = _runtime_random_preview_state_fingerprint(selected, custom_tags, settings)
    if not secrets.compare_digest(marker["state_fingerprint"], current_fingerprint):
        return None
    node_key = str(settings.get("cache_key") or "").strip()
    if not node_key:
        return None
    token = marker["token"]
    reservation_key = (node_key, token)
    with _cache_key_lock(node_key):
        with _CACHE_LOCK:
            cache = _peek_cache_bucket_unlocked(node_key) or {}
            consumed = [str(item) for item in cache.get("consumed_runtime_random_preview_tokens", []) if str(item)]
            if token in consumed or reservation_key in _RUNTIME_RANDOM_PREVIEW_RESERVATIONS:
                return None
            reservation = _RuntimeRandomPreviewReservation(node_key, token, marker)
            if transaction is not None:
                transaction.reservation = reservation
            try:
                _RUNTIME_RANDOM_PREVIEW_RESERVATIONS[reservation_key] = reservation
            except BaseException:
                if transaction is not None and transaction.reservation is reservation:
                    transaction.reservation = None
                raise
            return reservation


def _commit_runtime_random_preview_reservation(reservation: _RuntimeRandomPreviewReservation) -> bool:
    reservation_key = (reservation.node_key, reservation.token)
    with _cache_key_lock(reservation.node_key):
        with _CACHE_LOCK:
            if _RUNTIME_RANDOM_PREVIEW_RESERVATIONS.get(reservation_key) is not reservation:
                return False
            cache = _cache_bucket_unlocked(reservation.node_key, create=True)
            if cache is None:
                return False
            consumed = [str(item) for item in cache.get("consumed_runtime_random_preview_tokens", []) if str(item)]
            cache["consumed_runtime_random_preview_tokens"] = [
                reservation.token,
                *[token for token in consumed if token != reservation.token],
            ][:_RUNTIME_RANDOM_PREVIEW_TOKEN_LIMIT]
            del _RUNTIME_RANDOM_PREVIEW_RESERVATIONS[reservation_key]
            return True


def _release_runtime_random_preview_reservation(reservation: _RuntimeRandomPreviewReservation) -> bool:
    reservation_key = (reservation.node_key, reservation.token)
    with _cache_key_lock(reservation.node_key):
        with _CACHE_LOCK:
            if _RUNTIME_RANDOM_PREVIEW_RESERVATIONS.get(reservation_key) is not reservation:
                return False
            del _RUNTIME_RANDOM_PREVIEW_RESERVATIONS[reservation_key]
            return True


def _merge_nsfw_negative_prompt(base_prompt: str, nsfw_negative: dict[str, Any] | None, settings: dict[str, Any]) -> str:
    if not isinstance(nsfw_negative, dict):
        return str(base_prompt or "").strip()
    nsfw_prompt = str(nsfw_negative.get("prompt") or "").strip()
    if not nsfw_prompt:
        return str(base_prompt or "").strip()
    mode = str(nsfw_negative.get("mode") or "preview").strip()
    if mode == "override":
        return nsfw_prompt

    prompt_language = str(settings.get("提示词语言", "纯中文") or "纯中文").strip()
    separator = ", " if prompt_language in {"纯英文", "英文提示词+中文说明"} else "、"
    return separator.join(_uniq([*_parse_tags(base_prompt), *_parse_tags(nsfw_prompt)]))


def _compact_tag_summary(tags: list[str], *, limit: int = 48) -> str:
    clean_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
    clean_tags = _uniq(clean_tags)
    if not clean_tags:
        return ""
    shown = clean_tags[:limit]
    suffix = f" +{len(clean_tags) - limit}" if len(clean_tags) > limit else ""
    return "、".join(shown) + suffix


def _summary_dedupe_key(tag: str) -> str:
    return re.sub(r"[\s，,。；;、:：|/()（）【】\[\]{}]+", "", str(tag or "").strip().casefold())


def _compact_fresh_tag_summary(tags: list[str], *, seen_keys: set[str], limit: int = 48) -> str:
    fresh_tags: list[str] = []
    for tag in _uniq([str(item).strip() for item in tags if str(item).strip()]):
        key = _summary_dedupe_key(tag)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        fresh_tags.append(tag)
    if not fresh_tags:
        return ""
    shown = fresh_tags[:limit]
    suffix = f" +{len(fresh_tags) - limit}" if len(fresh_tags) > limit else ""
    return "、".join(shown) + suffix


def _build_nsfw_model_context_summary(
    *,
    nsfw_workspace: Any,
    nsfw_output: dict[str, Any] | None,
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
) -> str:
    if not isinstance(nsfw_workspace, dict) or not bool(nsfw_workspace.get("enabled", False)):
        return ""
    mapped_tags: list[str] = []
    if isinstance(nsfw_output, dict):
        mapped_selected = nsfw_output.get("selected")
        mapped_custom = nsfw_output.get("custom_tags")
        if isinstance(mapped_selected, OrderedDict):
            mapped_tags.extend(_collect_all_tags(mapped_selected, list(mapped_custom or [])))
        elif isinstance(mapped_selected, dict):
            mapped_tags.extend(_uniq([tag for tags in mapped_selected.values() for tag in list(tags or [])] + list(mapped_custom or [])))
    active_tags = _collect_all_tags(selected, custom_tags)
    workspace_fields = [
        "preset",
        "trigger_words",
        *_NSFW_SELECTOR_FIELDS,
        "scene",
        "action",
        "outfit",
        "mood",
        "anatomy_terms",
        "explicit_terms",
        "adult_action_style",
        "camera_movement",
        "camera_angle",
        "light_source",
        "light_type",
        "lens_type",
        "focal_length",
        "color_tone",
        "visual_style",
        "effect",
        "filter",
        "quality_tier",
    ]
    raw_terms: list[str] = []
    for field in workspace_fields:
        value = nsfw_workspace.get(field)
        if isinstance(value, (list, tuple, set)):
            raw_terms.extend(str(item).strip() for item in value if str(item).strip())
        elif str(value or "").strip() and str(value or "").strip() != "——":
            raw_terms.extend(_parse_tags(str(value)))
    seen_keys: set[str] = set()
    raw_summary = _compact_fresh_tag_summary(raw_terms, seen_keys=seen_keys, limit=32)
    mapped_summary = _compact_fresh_tag_summary(mapped_tags, seen_keys=seen_keys, limit=40)
    active_summary = _compact_fresh_tag_summary(active_tags, seen_keys=seen_keys, limit=48)
    parts = ["已启用"]
    if raw_summary:
        parts.append(f"工作台原始选择：{raw_summary}")
    if mapped_summary:
        parts.append(f"映射新增标签：{mapped_summary}")
    if active_summary:
        parts.append(f"节点额外激活标签：{active_summary}")
    return "；".join(parts)


def _build_model_post_context_summary(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    *,
    generated: list[str],
    nsfw_summary: str = "",
) -> str:
    grouped = _format_grouped_summary(selected, custom_tags)
    active_tags = _compact_tag_summary(_collect_all_tags(selected, custom_tags), limit=64)
    random_tags = _compact_tag_summary(list(generated or []), limit=24)
    parts = []
    if active_tags:
        parts.append(f"当前已选/运行标签：{active_tags}")
    if random_tags:
        parts.append(f"本次随机新增：{random_tags}")
    if grouped:
        parts.append(f"分组摘要：{grouped}")
    if nsfw_summary:
        parts.append(f"NSFW摘要：{nsfw_summary}")
    return "；".join(parts)


def _apply_nsfw_generation_profile(settings: dict[str, Any]) -> None:
    if str(settings.get("模板风格", "自动") or "自动").strip() in {"", "自动"}:
        settings["模板风格"] = "真实感"
    if str(settings.get("主体类型", "自动") or "自动").strip() in {"", "自动"}:
        settings["主体类型"] = "人物角色"
    settings["NSFW工作台启用"] = True
    settings["NSFW策略启用"] = True
    settings["NSFW策略来源"] = "NSFW工作台"
    settings["标签反推模式"] = "成人向成熟"
    settings["优先柔和肤质"] = True
    settings["抑制文字伪影"] = True


def _remove_empty_skill_scaffold_for_nsfw(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
) -> None:
    notes = [str(note).strip() for note in settings.get("推理纠偏说明", []) if str(note).strip()]
    scaffold_notes = [note for note in notes if note.startswith("Skill空输入脚手架：")]
    if not scaffold_notes:
        return
    for tag in ("成年人物主体", "真实感", "简洁室内", "自然光", "站姿挺拔"):
        _remove_tag_from_state(selected, custom_tags, tag)
    settings["推理纠偏说明"] = [
        *(note for note in notes if note not in scaffold_notes),
        "NSFW工作台主线：已移除空输入脚手架占位标签，改由工作台的成年主体、场景、服装、动作和光影建立画面。",
    ]


def _apply_adult_reverse_profile(settings: dict[str, Any]) -> None:
    if str(settings.get("标签反推模式", "") or "").strip() != "成人向成熟":
        settings["NSFW策略启用"] = False
        settings["NSFW策略来源"] = ""
        return
    if str(settings.get("主体类型", "自动") or "自动").strip() == "非人物主体":
        settings["NSFW策略启用"] = False
        settings["NSFW策略来源"] = "非人物主体已跳过"
        return
    if str(settings.get("主体类型", "自动") or "自动").strip() in {"", "自动"}:
        settings["主体类型"] = "人物角色"
    settings["NSFW策略启用"] = True
    settings["NSFW策略来源"] = "高级标签反推"
    settings["优先柔和肤质"] = True
    settings["抑制文字伪影"] = True


def _merge_requirement_text(*parts: Any) -> str:
    seen: set[str] = set()
    merged: list[str] = []
    for raw in parts:
        text = str(raw or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        merged.append(text)
    return "\n".join(merged)


def _extract_chat_text(out: Any) -> str:
    return _extract_model_response_text_impl(out)


def _build_image_reverse_prompt(settings: dict[str, Any]) -> str:
    mode = str(settings.get("图片反推模式", "角色设定图") or "角色设定图").strip()
    base = (
        "请反推这张参考图，输出一段中文结构化描述，用于后续生成AI绘画正向提示词。"
        "只描述可见画面，不要编造身份和剧情，不要输出负面词，不要输出JSON。"
        "重点包括：主体年龄段与气质、发型发色、服装版型和材质、主配色、构图景别、视角、"
        "姿态、光影、背景简洁度、画质风格。"
    )
    if mode == "仅反推描述":
        return base + "请保持为一段自然语言描述，便于智能文本匹配。"
    return (
        base
        + "当前目标是生成标准角色三视图：请准确提取同一角色的脸型、发型、体型、服装结构、主配色和材质逻辑，"
        "并为后续从左到右的正面全身、90度标准侧面全身、背面全身三幅等宽视图提供一致设定；三幅人物使用相同高度、"
        "同一头顶线和脚底基线、统一镜头高度、正交投影、中性站姿与完整头脚构图。背景、风格、服装和配色跟随参考图与用户输入，"
        "除非用户明确要求，不要锁定白底、古风、汉服或固定颜色；不要文字标注。头像或材质细节只在用户明确要求时作为独立辅助信息。"
    )


def _image_reverse_model_signature(model: Any, settings: dict[str, Any]) -> dict[str, Any]:
    def scalar(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    signature: dict[str, Any] = {
        "settings": {
            key: scalar(settings.get(key))
            for key in _IMAGE_REVERSE_MODEL_SETTING_KEYS
            if key in settings
        }
    }
    has_attached_identity = False
    for label, target in (("model", model), ("llm", getattr(model, "llm", None))):
        if target is None:
            continue
        target_signature: dict[str, Any] = {
            "class": f"{type(target).__module__}.{type(target).__qualname__}",
        }
        for attribute in ("model_path", "_model_path", "model_name", "chat_format"):
            value = getattr(target, attribute, None)
            if value not in (None, ""):
                target_signature[attribute] = scalar(value)
                has_attached_identity = True
        for attribute in ("settings", "config"):
            attached = getattr(target, attribute, None)
            if not isinstance(attached, dict):
                continue
            selected = {
                key: scalar(attached.get(key))
                for key in _IMAGE_REVERSE_ATTACHED_CONFIG_KEYS
                if key in attached
            }
            if selected:
                target_signature[attribute] = selected
                has_attached_identity = True
        signature[label] = target_signature
    if not has_attached_identity:
        signature["instance"] = id(getattr(model, "llm", model))
    return signature


def _build_image_reverse_cache_key(
    image_url: str,
    reverse_prompt: str,
    model: Any,
    settings: dict[str, Any],
    params: dict[str, Any],
) -> str:
    metadata = json.dumps(
        {
            "model": _image_reverse_model_signature(model, settings),
            "params": params,
            "max_edge": int(settings.get("图片反推最大边长", 960) or 960),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256()
    digest.update(b"qwen-te:image-reverse:v1\0")
    for value in (image_url, reverse_prompt, metadata):
        text = str(value)
        digest.update(str(len(text)).encode("ascii"))
        digest.update(b":")
        for offset in range(0, len(text), 65536):
            digest.update(text[offset : offset + 65536].encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _get_cached_image_reverse(cache_key: str) -> str | None:
    with _IMAGE_REVERSE_CACHE_LOCK:
        cached = _IMAGE_REVERSE_CACHE.get(cache_key)
        if cached is None:
            return None
        _IMAGE_REVERSE_CACHE.move_to_end(cache_key)
        return cached


def _cache_image_reverse(cache_key: str, text: str) -> None:
    value = str(text or "").strip()
    if not value:
        return
    with _IMAGE_REVERSE_CACHE_LOCK:
        _IMAGE_REVERSE_CACHE[cache_key] = value
        _IMAGE_REVERSE_CACHE.move_to_end(cache_key)
        while len(_IMAGE_REVERSE_CACHE) > _IMAGE_REVERSE_CACHE_LIMIT:
            _IMAGE_REVERSE_CACHE.popitem(last=False)


def _image_reverse_singleflight_timeout(value: Any, default: float) -> float:
    try:
        timeout = float(value)
    except (TypeError, ValueError, OverflowError):
        timeout = float(default)
    if not 0.0 < timeout < float("inf"):
        timeout = float(default)
    return max(0.001, timeout)


def _begin_image_reverse_singleflight(
    cache_key: str,
    *,
    wait_timeout: float | None = None,
    stale_after: float | None = None,
    _guard: _ImageReverseSingleflightGuard | None = None,
) -> tuple[str, str | None, _ImageReverseInFlight | None]:
    wait_seconds = _image_reverse_singleflight_timeout(
        wait_timeout,
        _IMAGE_REVERSE_INFLIGHT_WAIT_TIMEOUT_SECONDS,
    )
    stale_seconds = _image_reverse_singleflight_timeout(
        stale_after,
        _IMAGE_REVERSE_INFLIGHT_STALE_AFTER_SECONDS,
    )
    deadline = time.monotonic() + wait_seconds
    with _IMAGE_REVERSE_INFLIGHT_CONDITION:
        while True:
            _raise_if_comfy_interrupted()
            now = time.monotonic()
            cached = _IMAGE_REVERSE_CACHE.get(cache_key)
            if cached is not None:
                _IMAGE_REVERSE_CACHE.move_to_end(cache_key)
                return "cached", cached, None
            flight = _IMAGE_REVERSE_INFLIGHT.get(cache_key)
            if flight is not None:
                return "wait", None, flight
            if len(_IMAGE_REVERSE_INFLIGHT) < _IMAGE_REVERSE_INFLIGHT_LIMIT:
                flight = _ImageReverseInFlight()
                if _guard is not None:
                    _guard.flight = flight
                    _guard.leader = True
                _IMAGE_REVERSE_INFLIGHT[cache_key] = flight
                return "lead", None, flight
            oldest_remaining = min(
                stale_seconds - (now - float(item.started_at))
                for item in _IMAGE_REVERSE_INFLIGHT.values()
            )
            if oldest_remaining <= 0:
                raise TimeoutError("图片反推已有底层任务超过截止时间但尚未退出；为避免并发访问模型，已拒绝新的反推任务。")
            remaining = deadline - now
            if remaining <= 0:
                raise TimeoutError("图片反推 singleflight 等待可用执行槽位超时。")
            _IMAGE_REVERSE_INFLIGHT_CONDITION.wait(
                timeout=min(remaining, oldest_remaining, _COOPERATIVE_WAIT_POLL_SECONDS)
            )


def _wait_image_reverse_singleflight(
    cache_key: str,
    flight: _ImageReverseInFlight,
    *,
    wait_timeout: float | None = None,
    stale_after: float | None = None,
) -> str:
    wait_seconds = _image_reverse_singleflight_timeout(
        wait_timeout,
        _IMAGE_REVERSE_INFLIGHT_WAIT_TIMEOUT_SECONDS,
    )
    stale_seconds = _image_reverse_singleflight_timeout(
        stale_after,
        _IMAGE_REVERSE_INFLIGHT_STALE_AFTER_SECONDS,
    )
    stale_deadline = float(flight.started_at) + stale_seconds
    wait_deadline = time.monotonic() + wait_seconds
    completed = flight.event.is_set()
    while not completed:
        _raise_if_comfy_interrupted()
        remaining = min(wait_deadline, stale_deadline) - time.monotonic()
        if remaining <= 0.0:
            break
        completed = flight.event.wait(timeout=min(remaining, _COOPERATIVE_WAIT_POLL_SECONDS))
    if not completed:
        raise TimeoutError("图片反推 singleflight 等待已有任务完成超时。")
    _raise_if_comfy_interrupted()
    if flight.error is not None:
        raise flight.error
    return flight.result


def _finish_image_reverse_singleflight(
    cache_key: str,
    flight: _ImageReverseInFlight,
    *,
    result: str = "",
    error: BaseException | None = None,
) -> None:
    value = str(result or "").strip()
    with _IMAGE_REVERSE_INFLIGHT_CONDITION:
        authoritative = _IMAGE_REVERSE_INFLIGHT.get(cache_key) is flight
        if authoritative or not flight.event.is_set():
            flight.result = value
            flight.error = error
        if authoritative and error is None and value:
            _IMAGE_REVERSE_CACHE[cache_key] = value
            _IMAGE_REVERSE_CACHE.move_to_end(cache_key)
            while len(_IMAGE_REVERSE_CACHE) > _IMAGE_REVERSE_CACHE_LIMIT:
                _IMAGE_REVERSE_CACHE.popitem(last=False)
        if authoritative:
            del _IMAGE_REVERSE_INFLIGHT[cache_key]
        flight.event.set()
        _IMAGE_REVERSE_INFLIGHT_CONDITION.notify_all()


def _reverse_reference_image(model: Any, image: Any, settings: dict[str, Any]) -> str:
    settings["图片反推缓存命中"] = False
    if image is None:
        return ""
    if model is None or not hasattr(model, "llm"):
        raise RuntimeError("图片反推需要可用的视觉模型。请先在“模型”按钮里选择支持视觉的模型和 mmproj，或连接 qwen模型。")
    data_urls = _批量帧索引转data_url(image, [0], int(settings.get("图片反推最大边长", 960) or 960))
    image_url = data_urls.get(0, "")
    if not image_url:
        return ""
    reverse_prompt = _build_image_reverse_prompt(settings)
    params = {
        "max_tokens": 420,
        "temperature": min(float(settings.get("温度", 0.62) or 0.62), 0.55),
        "top_p": float(settings.get("top_p", 0.9) or 0.9),
        "top_k": int(settings.get("top_k", 40) or 40),
        "repeat_penalty": float(settings.get("重复惩罚", 1.08) or 1.08),
        "frequency_penalty": float(settings.get("频率惩罚", 0.0) or 0.0),
        "presence_penalty": float(settings.get("存在惩罚", 0.0) or 0.0),
        "seed": _规范化随机种子(settings.get("seed", 0)),
        "stream": False,
        "stop": ["</s>"],
    }
    cache_key = _build_image_reverse_cache_key(image_url, reverse_prompt, model, settings, params)
    guard = _ImageReverseSingleflightGuard(cache_key)
    text = ""
    error: BaseException | None = None
    try:
        flight_mode, cached, flight = guard.begin()
        if flight_mode == "cached":
            settings["图片反推缓存命中"] = True
            return str(cached or "")
        if flight is None:
            raise RuntimeError("图片反推 singleflight 状态异常。")
        if flight_mode == "wait":
            result = _wait_image_reverse_singleflight(cache_key, flight)
            settings["图片反推缓存命中"] = True
            return result

        params[_MODEL_CALL_DEADLINE_PARAM] = time.monotonic() + _IMAGE_REVERSE_MODEL_CALL_TIMEOUT_SECONDS
        messages = [
            {
                "role": "system",
                "content": (
                    "你是AI绘画参考图反推助手。输出必须简洁、准确、可用于提示词生成；"
                    "不要寒暄，不要解释规则，不要写“以下是”。"
                ),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": reverse_prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ]
        out = _调用chat_completion(model.llm, messages=messages, params=params)
        text = _清洗think块文本(_extract_chat_text(out)).strip()
        text = re.sub(r"^\s*(?:以下是|这是|为你生成的).*?[：:]\s*", "", text)
        return text
    except BaseException as exc:
        error = exc
        raise
    finally:
        guard.finish(result=text, error=error)


def _apply_image_reverse_to_settings(model: Any, image: Any, settings: dict[str, Any]) -> str:
    settings["图片反推缓存命中"] = False
    settings["图片反推状态"] = "未启用"
    settings["图片反推错误"] = ""
    if not bool(settings.get("图片反推生成", False)) or image is None:
        return ""
    settings["图片反推状态"] = "等待调用"
    try:
        reversed_text = _reverse_reference_image(model, image, settings).strip()
    except Exception as exc:
        reason = _sanitize_model_error_impl(exc, settings)
        settings["图片反推状态"] = "调用失败，已回退"
        settings["图片反推错误"] = reason
        _record_model_call_result_impl(settings, outcome="failure", reason=f"图片反推回退：{reason}")
        return ""
    if bool(settings.get("图片反推缓存命中", False)):
        settings["图片反推状态"] = "缓存命中"
        return reversed_text
    if not reversed_text:
        reason = "图片反推 API 返回空文本或清洗后没有有效描述。"
        settings["图片反推状态"] = "调用失败，已回退"
        settings["图片反推错误"] = reason
        _record_model_call_result_impl(settings, outcome="failure", reason=reason)
        return ""
    settings["图片反推状态"] = "调用成功"
    _record_model_call_result_impl(settings, outcome="success", changed=True, adopted_outputs=1)
    return reversed_text


def _merge_model_runtime_state(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key in _MODEL_RUNTIME_STATE_KEYS:
        if key not in source:
            continue
        value = source[key]
        target[key] = list(value) if isinstance(value, list) else value


def _apply_character_sheet_to_settings(
    settings: dict[str, Any],
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    image_reverse_text: str = "",
    has_reference_image: bool = False,
) -> bool:
    if not bool(settings.get("图片反推生成", False)):
        return False
    tag_context = "，".join(_collect_all_tags(selected, custom_tags)[:80])
    grouped_context = _format_grouped_summary(selected, custom_tags)
    source_text = _merge_requirement_text(
        settings.get("智能文本输入"),
        settings.get("额外要求"),
        tag_context,
        grouped_context,
    )
    return _apply_character_sheet_strategy_impl(
        settings,
        source_text=source_text,
        reference_text=image_reverse_text,
        has_reference_image=has_reference_image,
        merge_requirement_text=_merge_requirement_text,
    )


def _extract_nsfw_workspace_from_extra_pnginfo(extra_pnginfo: Any, node_id: Any) -> dict[str, Any] | None:
    if not isinstance(extra_pnginfo, dict):
        return None
    workflow = extra_pnginfo.get("workflow")
    if not isinstance(workflow, dict) and isinstance(extra_pnginfo.get("nodes"), list):
        workflow = extra_pnginfo
    if not isinstance(workflow, dict):
        return None
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        return None
    target_id = str(node_id or "").strip()
    if not target_id:
        return None
    for node in nodes:
        if not isinstance(node, dict) or str(node.get("id") or "").strip() != target_id:
            continue
        properties = node.get("properties")
        if not isinstance(properties, dict):
            return None
        workspace = properties.get("nsfw_workspace")
        if not isinstance(workspace, dict):
            workspace = properties.get("nsfwWorkspace")
        return dict(workspace) if isinstance(workspace, dict) else None
    return None


def _extract_cache_namespace_record(extra_pnginfo: Any, node_id: Any) -> tuple[bool, str]:
    if not isinstance(extra_pnginfo, dict):
        return False, ""
    workflow = extra_pnginfo.get("workflow")
    if not isinstance(workflow, dict) and isinstance(extra_pnginfo.get("nodes"), list):
        workflow = extra_pnginfo
    if not isinstance(workflow, dict):
        return False, ""
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        return False, ""
    target_id = str(node_id or "").strip()
    if not target_id:
        return False, ""
    for node in nodes:
        if not isinstance(node, dict) or str(node.get("id") or "").strip() != target_id:
            continue
        properties = node.get("properties")
        if not isinstance(properties, dict) or _CACHE_NAMESPACE_PROPERTY not in properties:
            return False, ""
        raw_namespace = str(properties.get(_CACHE_NAMESPACE_PROPERTY) or "").strip()
        return bool(raw_namespace), _normalize_cache_namespace(raw_namespace)
    return False, ""


def _extract_cache_namespace_from_extra_pnginfo(extra_pnginfo: Any, node_id: Any) -> str:
    return _extract_cache_namespace_record(extra_pnginfo, node_id)[1]


def _resolve_stage_cache_key(
    node_id: Any,
    *,
    extra_pnginfo: Any = None,
    cache_namespace: Any = None,
) -> str:
    normalized_id = str(node_id or "").strip()
    raw_namespace = str(cache_namespace or "").strip()
    namespace = _normalize_cache_namespace(raw_namespace)
    if raw_namespace and not namespace:
        return ""
    if not raw_namespace:
        namespace_present, namespace = _extract_cache_namespace_record(extra_pnginfo, normalized_id)
        if namespace_present and not namespace:
            return ""
    return f"stage:{namespace}" if namespace else normalized_id


def _resolve_nsfw_workspace_payload(kwargs: dict[str, Any], settings: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    direct_workspace = kwargs.get("nsfw_workspace")
    if not isinstance(direct_workspace, dict):
        direct_workspace = kwargs.get("nsfwWorkspace")
    if isinstance(direct_workspace, dict):
        return _normalize_nsfw_workspace_impl(direct_workspace), "直接输入"
    recovered = _extract_nsfw_workspace_from_extra_pnginfo(
        kwargs.get("extra_pnginfo") or settings.get("extra_pnginfo"),
        settings.get("unique_id") or kwargs.get("unique_id") or kwargs.get("id"),
    )
    return (
        (_normalize_nsfw_workspace_impl(recovered), "工作流元数据")
        if recovered is not None
        else (None, "")
    )


def _run_stage_impl(
    model: Any,
    preview_transaction: _RuntimeRandomPreviewTransaction,
    cache_transaction: _StageCacheTransaction,
    **kwargs: Any,
) -> tuple[str, str, str, str, str, str, str]:
    tag_groups, tag_group_index, tag_group_memberships = _tag_catalog_snapshot()
    selected, custom_tags, settings, all_tags_text = _build_state_from_kwargs(
        kwargs,
        tag_groups=tag_groups,
        tag_group_index=tag_group_index,
        tag_group_memberships=tag_group_memberships,
    )
    settings["模型来源"] = _normalize_stage_model_source(settings.get("模型来源"))
    _apply_adult_reverse_profile(settings)
    reference_image = kwargs.get("参考图片")
    image_reverse_text = _apply_image_reverse_to_settings(model, reference_image, settings)
    nsfw_workspace, nsfw_workspace_source = _resolve_nsfw_workspace_payload(kwargs, settings)
    settings["NSFW工作台状态来源"] = nsfw_workspace_source
    settings["NSFW工作台状态指纹"] = _nsfw_workspace_state_fingerprint(nsfw_workspace)
    nsfw_output: dict[str, Any] | None = None
    nsfw_enabled = isinstance(nsfw_workspace, dict) and bool(nsfw_workspace.get("enabled", False))
    settings["运行时随机保护标签"] = ""
    if nsfw_enabled:
        _apply_nsfw_generation_profile(settings)
        _remove_empty_skill_scaffold_for_nsfw(selected, custom_tags, settings)
    node_id = settings["unique_id"]
    extra_pnginfo = kwargs.get("extra_pnginfo") or settings.get("extra_pnginfo")
    raw_cache_namespace = kwargs.get("cache_namespace") or kwargs.get("cacheNamespace")
    cache_namespace = _normalize_cache_namespace(raw_cache_namespace)
    if not cache_namespace and not str(raw_cache_namespace or "").strip():
        cache_namespace = _extract_cache_namespace_from_extra_pnginfo(extra_pnginfo, node_id)
    cache_key = _resolve_stage_cache_key(
        node_id,
        extra_pnginfo=extra_pnginfo,
        cache_namespace=raw_cache_namespace if str(raw_cache_namespace or "").strip() else cache_namespace,
    )
    settings["cache_namespace"] = cache_namespace
    settings["cache_key"] = cache_key
    cache_transaction.bind(cache_key)
    runtime_random_enabled = bool(settings["运行时随机标签"])
    preview_marker = (
        preview_transaction.reserve(settings, selected, custom_tags)
        if runtime_random_enabled
        else None
    )
    if nsfw_enabled and preview_marker is None:
        nsfw_output = 应用NSFW工作台到阶段状态(
            nsfw_workspace,
            selected=selected,
            custom_tags=custom_tags,
            tag_group_index=tag_group_index,
        )
        selected = nsfw_output["selected"]
        custom_tags = nsfw_output["custom_tags"]
        settings["运行时随机保护标签"] = ",".join(
            _uniq([*_parse_tags(settings.get("运行时随机保护标签")), *nsfw_output.get("protected_tags", [])])
        )
    resolved_runtime_mode = _resolve_runtime_random_mode_impl(
        str(settings.get("运行时随机模式", "") or ""),
        selected,
        settings,
    ) if runtime_random_enabled else ""
    if runtime_random_enabled and preview_marker is None:
        selected, custom_tags, generated = _build_runtime_tags(
            selected,
            custom_tags,
            settings,
            tag_groups=tag_groups,
            tag_group_index=tag_group_index,
        )
        settings["运行时随机模式解析结果"] = resolved_runtime_mode
        settings["运行时随机预览已消费"] = False
    elif runtime_random_enabled:
        active_tags = set(_collect_all_tags(selected, custom_tags))
        generated = [tag for tag in _parse_tags(settings.get("随机补充避重缓存")) if tag in active_tags]
        settings["运行时随机模式解析结果"] = str(preview_marker.get("mode") or resolved_runtime_mode)
        settings["运行时随机有效种子"] = int(preview_marker.get("seed") or settings.get("seed", 0) or 0)
        settings["随机主题池档案标记"] = list(preview_marker.get("theme_markers", []))
        settings["模板风格档案标记"] = list(preview_marker.get("style_markers", []))
        settings["运行时随机预览已消费"] = True
    else:
        generated = []
        settings["运行时随机模式解析结果"] = ""
        settings["运行时随机预览已消费"] = False
    settings["智能文本风格解析结果"] = ""
    settings["智能文本风格优先解析结果"] = str(settings.get("智能文本风格优先", "自动判断") or "自动判断")
    _apply_character_sheet_to_settings(
        settings,
        selected,
        custom_tags,
        image_reverse_text=image_reverse_text,
        has_reference_image=reference_image is not None,
    )
    biased_template_style = _infer_template_style(_collect_all_tags(selected, custom_tags), str(settings["模板风格"]))
    preview_has_profile_pipeline = bool(preview_marker and preview_marker.get("source") == "backend")
    if not preview_has_profile_pipeline:
        biased_template_style, selected, custom_tags = _apply_random_theme_pool_bias(
            biased_template_style,
            selected,
            custom_tags,
            settings,
            tag_group_index=tag_group_index,
            tag_group_memberships=tag_group_memberships,
        )
        selected, custom_tags = _apply_template_style_profile_bias(
            biased_template_style,
            selected,
            custom_tags,
            settings,
            tag_group_index=tag_group_index,
            tag_group_memberships=tag_group_memberships,
        )
    smart_text_input = str(settings.get("智能文本输入") or settings.get("额外要求") or "").strip()
    smart_text_enabled = bool(settings.get("智能文本匹配", False)) and bool(smart_text_input)
    if smart_text_enabled:
        available_tag_names = set(tag_group_index)
        selected, custom_tags, smart_text_notes = _apply_smart_text_to_state_impl(
            selected,
            custom_tags,
            settings,
            text=smart_text_input,
            available_tags=available_tag_names,
            tag_group_index=tag_group_index,
            append_tag_to_state=lambda next_selected, next_custom_tags, tag: _append_tag_to_state(
                next_selected,
                next_custom_tags,
                tag,
                tag_group_index=tag_group_index,
                tag_group_memberships=tag_group_memberships,
            ),
        )
        if smart_text_notes:
            existing_notes = [str(note).strip() for note in settings.get("推理纠偏说明", []) if str(note).strip()]
            for note in smart_text_notes:
                text = str(note).strip()
                if text and text not in existing_notes:
                    existing_notes.append(text)
            settings["推理纠偏说明"] = existing_notes
    selected, custom_tags, runtime_normalization_notes = _normalize_inference_state(
        selected,
        custom_tags,
        settings,
        tag_group_index=tag_group_index,
        tag_group_memberships=tag_group_memberships,
    )
    if runtime_normalization_notes:
        _merge_inference_notes(settings, runtime_normalization_notes)
    if nsfw_enabled and isinstance(nsfw_workspace, dict):
        normalized_active_tags = set(_collect_all_tags(selected, custom_tags))
        nsfw_output = 应用NSFW工作台到阶段状态(
            nsfw_workspace,
            selected=selected,
            custom_tags=custom_tags,
            allowed_tags=normalized_active_tags,
            tag_group_index=tag_group_index,
        )
        selected = nsfw_output["selected"]
        custom_tags = nsfw_output["custom_tags"]
        settings["运行时随机保护标签"] = ",".join(nsfw_output.get("protected_tags", []))
        _merge_inference_notes(settings, ["NSFW工作台锚点保护：仅保留最终归一化后仍有效的工作台显式选择。"])
    tags = _collect_all_tags(selected, custom_tags)
    if generated:
        active_tags = set(tags)
        generated = [tag for tag in _uniq(generated) if tag in active_tags]
    nsfw_model_summary = _build_nsfw_model_context_summary(
        nsfw_workspace=nsfw_workspace,
        nsfw_output=nsfw_output,
        selected=selected,
        custom_tags=custom_tags,
    )
    settings["NSFW工作台标签摘要"] = nsfw_model_summary
    danbooru_general_tags = [tag for tag in tags if tag in DANBOORU_GENERAL_TAG_ALIASES]
    settings["Danbooru通用视觉标签摘要"] = "、".join(
        f"{tag} ({DANBOORU_GENERAL_TAG_ALIASES[tag]})" for tag in danbooru_general_tags[:16]
    )
    settings["模型后置素材摘要"] = _build_model_post_context_summary(
        selected,
        custom_tags,
        generated=generated,
        nsfw_summary=nsfw_model_summary,
    )
    template_style = biased_template_style if str(settings.get("随机主题池", "自动")).strip() != "自动" else _infer_template_style(tags, str(settings["模板风格"]))
    subject_type = _infer_subject_type(tags, str(settings["主体类型"]))
    output_structure = _infer_output_structure(subject_type, str(settings["案例输出结构"]))
    creative_spine_contract = _build_global_creative_spine_contract_impl(
        selected,
        custom_tags,
        settings,
        template_style=template_style,
        subject_type=subject_type,
        layout_mode=str(settings.get("画面结构模式解析结果", "") or ""),
        primary_style_family=_base_template_style(template_style),
    )
    settings["全局创作主线合同"] = creative_spine_contract
    settings["全局创作主线摘要"] = _summarize_global_creative_spine_contract_impl(creative_spine_contract)
    scene_group = _main_scene_group(tags, template_style)
    identity = _main_identity(tags)
    adult_subpool = _adult_subpool(tags) if bool(set(tags) & 成人向标签关键词) else ""
    style_track = _style_track(template_style, tags)
    recent_tracks = _update_history(cache_key, style_track)
    prompt_recent_tracks = _random_history(cache_key)
    settings["最近提示词指纹"] = _prompt_history_fingerprints(cache_key)
    tag_block_payload = _parse_tag_block_payload_impl(settings.get("标签块编排JSON", ""))
    tag_block_enabled = bool(settings.get("标签块编排启用", False)) and bool(tag_block_payload.get("blocks"))
    if tag_block_enabled:
        grouped_summary_for_blocks = _format_grouped_summary(selected, custom_tags)
        settings["标签块编排摘要"] = _summarize_tag_block_payload_impl(tag_block_payload)
        existing_notes = [str(note).strip() for note in settings.get("推理纠偏说明", []) if str(note).strip()]
        block_note = "标签块编排：已按终端预览中的用户块顺序生成主线。"
        if block_note not in existing_notes:
            existing_notes.append(block_note)
        settings["推理纠偏说明"] = existing_notes
        prompt_list = _build_tag_block_prompt_list_impl(
            tag_block_payload,
            selected,
            custom_tags,
            settings,
            grouped_summary=grouped_summary_for_blocks,
            style_track=style_track,
            subject_type=subject_type,
            template_style=template_style,
            generation_count=int(settings.get("生成数量", 1) or 1),
        )
        tag_block_narrative_plans = list(settings.get("全局剧情规划", []) or [])
        natural_contract_fallback_list = _build_prompt_list_impl(
            selected,
            custom_tags,
            settings,
            scene_group=scene_group,
            identity=identity,
            style_track=style_track,
            recent_tracks=prompt_recent_tracks,
            uniq=_uniq,
            infer_template_style=_infer_template_style,
            infer_subject_type=_infer_subject_type,
            infer_output_structure=_infer_output_structure,
        )
        if tag_block_narrative_plans:
            settings["全局剧情规划"] = tag_block_narrative_plans
    else:
        settings["标签块编排摘要"] = ""
        prompt_list = _build_prompt_list_impl(
            selected,
            custom_tags,
            settings,
            scene_group=scene_group,
            identity=identity,
            style_track=style_track,
            recent_tracks=prompt_recent_tracks,
            uniq=_uniq,
            infer_template_style=_infer_template_style,
            infer_subject_type=_infer_subject_type,
            infer_output_structure=_infer_output_structure,
        )
        natural_contract_fallback_list = list(prompt_list)
    raw_prompt_list = list(prompt_list)
    model_prompt_list = _maybe_model_refine_batch_impl(
        model,
        prompt_list,
        settings,
        chat_completion=_调用chat_completion,
        clean_think_text=_清洗think块文本,
    )
    prompt_list = _stabilize_prompt_list_outputs(model_prompt_list, raw_prompt_list, settings)
    prompt_list = _enforce_natural_prompt_list_outputs(
        prompt_list,
        raw_prompt_list,
        natural_contract_fallback_list,
        settings,
        channel="prompt",
    )
    stabilization_fallback_indices = {
        int(index)
        for index in settings.get("模型稳定化回退索引", [])
        if isinstance(index, int) or str(index).isdigit()
    }
    pre_dedupe_prompt_list = list(prompt_list)
    prompt_list = _strict_dedupe_prompt_list(cache_key, prompt_list, settings, channel="prompt")
    prompt_list = _enforce_natural_prompt_list_outputs(
        prompt_list,
        pre_dedupe_prompt_list,
        natural_contract_fallback_list,
        settings,
        channel="prompt",
    )
    postprocess_fallback_count = sum(
        model_candidate != original and (index in stabilization_fallback_indices or final_prompt == original)
        for index, (model_candidate, final_prompt, original) in enumerate(
            zip(model_prompt_list, prompt_list, raw_prompt_list)
        )
    )
    settings["模型主提示词后处理回退数量"] = postprocess_fallback_count
    if postprocess_fallback_count:
        _reconcile_model_output_fallback_impl(
            settings,
            fallback_outputs=postprocess_fallback_count,
            output_count=len(raw_prompt_list),
            reason="模型候选在最终稳定化、批内差异或连续生成避重校验中被恢复为 Skill 结果。",
        )
    _update_prompt_history(cache_key, prompt_list)
    profile_markers = [
        *list(settings.get("随机主题池档案标记", []) or []),
        *list(settings.get("模板风格档案标记", []) or []),
    ]
    if runtime_random_enabled or profile_markers:
        _update_runtime_random_history(
            cache_key,
            selected=selected,
            custom_tags=custom_tags,
            generated=generated,
            prompt_list=prompt_list,
            extra_markers=[
                *profile_markers,
                *list(settings.get("运行时随机档案标记", []) or []),
            ],
            tag_group_index=tag_group_index,
            tag_groups=tag_groups,
        )
    grouped_summary = _format_grouped_summary(selected, custom_tags)
    full_text, prompt_only = _format_sections_impl(prompt_list, grouped_summary, settings=settings)
    primary_prompt = str(prompt_list[0]).strip() if prompt_list else ""
    negative_prompt = _build_negative_prompt(selected, custom_tags, settings)
    if nsfw_output is not None:
        negative_prompt = _merge_nsfw_negative_prompt(negative_prompt, nsfw_output.get("negative"), settings)
    lock_tag_whitelist = _parse_tags(settings["锁定标签白名单"])
    random_exclude_tags = _parse_tags(settings["随机排除标签"])
    selected_tags_text = _build_selected_tags_text_impl(
        template_style=template_style,
        subject_type=subject_type,
        output_structure=output_structure,
        runtime_random_enabled=runtime_random_enabled,
        settings=settings,
        adult_subpool=adult_subpool,
        scene_group=scene_group,
        identity=identity,
        style_track=style_track,
        selected=selected,
        custom_tags=custom_tags,
        recent_tracks=recent_tracks,
        negative_prompt=negative_prompt,
        format_grouped_summary=_format_grouped_summary_impl,
    )
    smart_text_prompt = ""
    if smart_text_enabled:
        smart_seed = _build_smart_text_seed_impl(
            user_text=smart_text_input,
            primary_prompt=primary_prompt,
            selected_tags_text=selected_tags_text,
            settings=settings,
            style_track=style_track,
        )
        smart_text_settings = _build_smart_text_settings_impl(settings)
        smart_success_count_before = max(0, int(smart_text_settings.get("模型调用成功次数", 0) or 0))
        smart_text_prompt = _maybe_model_refine_impl(
            model,
            smart_seed,
            smart_text_settings,
            chat_completion=_调用chat_completion,
            clean_think_text=_清洗think块文本,
        )
        smart_model_candidate = str(smart_text_prompt or "").strip()
        smart_model_succeeded = (
            max(0, int(smart_text_settings.get("模型调用成功次数", 0) or 0))
            > smart_success_count_before
        )
        smart_model_adopted = smart_model_candidate != str(smart_seed or "").strip()
        smart_model_fallback_used = smart_model_succeeded and not smart_model_adopted
        _merge_model_runtime_state(settings, smart_text_settings)
        smart_text_prompt = (_stabilize_prompt_list_outputs([smart_text_prompt], [smart_seed], settings) or [smart_text_prompt])[0]
        smart_stabilization_fallback = 0 in set(settings.get("模型稳定化回退索引", []))
        if smart_stabilization_fallback and (smart_model_adopted or smart_model_succeeded):
            smart_model_fallback_used = True
        if smart_text_prompt == smart_seed or "节点基础正向提示词" in str(smart_text_prompt):
            smart_model_fallback_used = smart_model_adopted or smart_model_succeeded
            smart_text_prompt = ""
        smart_text_prompt = _sanitize_smart_text_prompt_impl(
            text=str(smart_text_prompt or "").strip(),
            user_text=smart_text_input,
            primary_prompt=primary_prompt,
            adult_mode=nsfw_enabled or str(settings.get("标签反推模式", "") or "").strip() == "成人向成熟",
            style_track=style_track,
            subject_type=subject_type,
            language=str(settings.get("提示词语言", "纯中文") or "纯中文"),
        )
        if not smart_text_prompt and (smart_model_adopted or smart_model_succeeded):
            smart_model_fallback_used = True
        smart_text_prompt = smart_text_prompt or _fallback_smart_text_impl(
            user_text=smart_text_input,
            primary_prompt=primary_prompt,
            style_track=style_track,
            subject_type=subject_type,
            language=str(settings.get("提示词语言", "纯中文") or "纯中文"),
            adult_mode=nsfw_enabled or str(settings.get("标签反推模式", "") or "").strip() == "成人向成熟",
        )
        smart_text_prompt = _sanitize_smart_text_prompt_impl(
            text=smart_text_prompt,
            user_text=smart_text_input,
            primary_prompt=primary_prompt,
            adult_mode=nsfw_enabled or str(settings.get("标签反推模式", "") or "").strip() == "成人向成熟",
            style_track=style_track,
            subject_type=subject_type,
            language=str(settings.get("提示词语言", "纯中文") or "纯中文"),
        ) or primary_prompt
        smart_text_prompt = _stabilize_prompt_output_impl(smart_text_prompt, settings) or primary_prompt
        smart_text_prompt = _enforce_natural_prompt_list_outputs(
            [smart_text_prompt],
            [primary_prompt],
            [primary_prompt],
            settings,
            channel="smart",
        )[0]
        if smart_text_prompt and smart_text_prompt != primary_prompt:
            pre_dedupe_smart_text_prompt = smart_text_prompt
            smart_text_prompt = (
                _strict_dedupe_prompt_list(cache_key, [smart_text_prompt], settings, channel="smart")
                or [smart_text_prompt]
            )[0]
            smart_text_prompt = _enforce_natural_prompt_list_outputs(
                [smart_text_prompt],
                [pre_dedupe_smart_text_prompt],
                [primary_prompt],
                settings,
                channel="smart",
            )[0]
            _update_prompt_history(cache_key, [smart_text_prompt])
        if (smart_model_adopted or smart_model_succeeded) and smart_text_prompt == primary_prompt:
            smart_model_fallback_used = True
        if smart_model_fallback_used:
            _reconcile_model_output_fallback_impl(
                settings,
                fallback_outputs=1,
                output_count=1,
                reason="智能文本模型候选未通过最终稳定化或安全清洗，已使用 Skill 智能文本回退。",
                adopted_outputs_to_revert=1 if smart_model_adopted else 0,
            )
    else:
        smart_text_prompt = primary_prompt
    video_prompt = _build_video_prompt_impl(
        selected,
        custom_tags,
        settings,
        primary_prompt=primary_prompt,
    )
    video_model_success_before = max(0, int(settings.get("模型调用成功次数", 0) or 0))
    video_model_failure_before = max(0, int(settings.get("模型调用失败次数", 0) or 0))
    video_model_fallback_before = max(0, int(settings.get("模型活动回退数量", 0) or 0))
    settings["视频提示词必保留锚点"] = _video_prompt_required_anchors_impl(
        selected,
        custom_tags,
        settings,
    )
    video_model_settings = dict(settings)
    video_model_settings["模型任务"] = "视频提示词"
    video_model_settings["视频提示词模型系统提示"] = _VIDEO_PROMPT_MODEL_SYSTEM_TEMPLATE
    refined_video_prompt = _maybe_model_refine_video_impl(
        model,
        video_prompt,
        video_model_settings,
        chat_completion=_调用chat_completion,
        clean_think_text=_清洗think块文本,
        validator=_is_natural_video_prompt_impl,
    )
    _merge_model_runtime_state(settings, video_model_settings)
    if model is None:
        if video_model_failure_before:
            settings["视频提示词模型状态"] = "模型加载失败，保留 Skill 结果"
        else:
            settings["视频提示词模型状态"] = "未调用（仅Skill）"
    elif refined_video_prompt != video_prompt:
        settings["视频提示词模型状态"] = "已采用模型润色"
    elif max(0, int(settings.get("模型调用成功次数", 0) or 0)) > video_model_success_before:
        settings["视频提示词模型状态"] = "模型调用成功，保留 Skill 结果"
    elif (
        max(0, int(settings.get("模型调用失败次数", 0) or 0)) > video_model_failure_before
        or max(0, int(settings.get("模型活动回退数量", 0) or 0)) > video_model_fallback_before
    ):
        settings["视频提示词模型状态"] = "模型调用失败或候选不合格，保留 Skill 结果"
    else:
        settings["视频提示词模型状态"] = "未产生模型候选，保留 Skill 结果"
    video_prompt = refined_video_prompt
    if _is_natural_video_prompt_impl(video_prompt, language=str(settings.get("提示词语言", "纯中文") or "纯中文")):
        settings["视频提示词Skill状态"] = "已生成"
    else:
        settings["视频提示词Skill状态"] = "生成结果未通过自然语言校验"
    settings["视频提示词Skill版本"] = _VIDEO_PROMPT_SKILL_VERSION
    selected_tags_text = _build_selected_tags_text_impl(
        template_style=template_style,
        subject_type=subject_type,
        output_structure=output_structure,
        runtime_random_enabled=runtime_random_enabled,
        settings=settings,
        adult_subpool=adult_subpool,
        scene_group=scene_group,
        identity=identity,
        style_track=style_track,
        selected=selected,
        custom_tags=custom_tags,
        recent_tracks=recent_tracks,
        negative_prompt=negative_prompt,
        format_grouped_summary=_format_grouped_summary_impl,
    )
    json_payload = _build_json_payload_impl(
        full_text=full_text,
        prompt_only=prompt_only,
        prompt_list=prompt_list,
        selected_tags_text=selected_tags_text,
        selected=selected,
        tags=tags,
        template_style=template_style,
        subject_type=subject_type,
        output_structure=output_structure,
        runtime_random_enabled=runtime_random_enabled,
        settings=settings,
        generated=generated,
        lock_tag_whitelist=lock_tag_whitelist,
        random_exclude_tags=random_exclude_tags,
        scene_group=scene_group,
        identity=identity,
        adult_subpool=adult_subpool,
        style_track=style_track,
        recent_tracks=recent_tracks,
        negative_prompt=negative_prompt,
        smart_text_prompt=smart_text_prompt,
        video_prompt=video_prompt,
    )
    json_payload["runtime_random_effective_seed"] = int(settings.get("运行时随机有效种子", settings.get("seed", 0)) or 0)
    json_payload["runtime_random_preview_consumed"] = bool(settings.get("运行时随机预览已消费", False))
    json_payload["runtime_random_preview_marker_present"] = bool(str(settings.get("运行时随机预览令牌", "") or "").strip())
    if tag_block_enabled:
        json_payload["tag_block_composer_enabled"] = True
        json_payload["tag_block_composer"] = tag_block_payload
        json_payload["tag_block_composer_summary"] = settings.get("标签块编排摘要", "")
    json_payload["smart_text_prompt"] = smart_text_prompt
    json_payload["video_prompt"] = video_prompt
    json_payload["smart_text_enabled"] = bool(smart_text_enabled)
    json_payload["smart_text_input"] = smart_text_input
    json_payload["danbooru_general_tags"] = list(danbooru_general_tags)
    json_payload["danbooru_general_aliases"] = {
        tag: DANBOORU_GENERAL_TAG_ALIASES[tag] for tag in danbooru_general_tags
    }
    json_payload["danbooru_general_scope"] = "general visual tags only"
    json_payload["prompt_dedupe_cache"] = str(settings.get("连续生成避重缓存输出", "") or "")
    json_payload["profile_rotation_markers"] = list(profile_markers)
    json_payload["strict_prompt_dedupe_enabled"] = True
    json_payload["normalization_notes"] = list(settings.get("推理纠偏说明", []))
    if nsfw_output is not None:
        json_payload["nsfw_workspace"] = dict(nsfw_workspace)
        json_payload["nsfw_workspace_source"] = nsfw_workspace_source
        json_payload["nsfw_workspace_state"] = {
            "selected": {key: list(value) for key, value in nsfw_output["selected"].items()},
            "custom_tags": list(nsfw_output["custom_tags"]),
        }
        json_payload["nsfw_negative_prompt"] = str(nsfw_output["negative_prompt"] or "").strip()
        if nsfw_output.get("negative"):
            json_payload["nsfw_negative"] = dict(nsfw_output["negative"])
    json_result = json.dumps(json_payload, ensure_ascii=False, indent=2)
    _cache_output(
        cache_key,
        _build_cache_payload_impl(
            full_text=full_text,
            primary_prompt=primary_prompt,
            prompt_only=prompt_only,
            prompt_collection=prompt_only,
            selected_tags_text=selected_tags_text,
            json_result=json_result,
            negative_prompt=negative_prompt,
            style_track=style_track,
            smart_text_prompt=smart_text_prompt,
            video_prompt=video_prompt,
        ),
    )
    return full_text, primary_prompt, selected_tags_text, json_result, negative_prompt, prompt_only, smart_text_prompt, video_prompt


def _run_stage(model: Any, **kwargs: Any) -> tuple[str, str, str, str, str, str, str, str]:
    preview_transaction = _RuntimeRandomPreviewTransaction()
    cache_transaction = _StageCacheTransaction()
    previous_transaction = getattr(_STAGE_CACHE_TRANSACTION_LOCAL, "current", None)
    if isinstance(previous_transaction, _StageCacheTransaction) and not previous_transaction.closed:
        raise RuntimeError("阶段提示词生成不支持同线程嵌套执行；请等待当前生成事务完成。")
    _STAGE_CACHE_TRANSACTION_LOCAL.current = cache_transaction
    try:
        result = _run_stage_impl(model, preview_transaction, cache_transaction, **kwargs)
        cache_transaction.commit(preview_transaction)
        return result
    except BaseException:
        cache_transaction.rollback(preview_transaction)
        raise
    finally:
        if previous_transaction is None:
            try:
                del _STAGE_CACHE_TRANSACTION_LOCAL.current
            except AttributeError:
                pass
        else:
            _STAGE_CACHE_TRANSACTION_LOCAL.current = previous_transaction


_PROMPT_CORE_SPLIT_RE = re.compile(r"[\n\r，,。；;]+")
_PROMPT_CORE_IGNORE_KEYS = {
    _summary_dedupe_key(term)
    for term in (
        "高细节",
        "高质量",
        "清晰",
        "清晰对焦",
        "焦点层级清晰",
        "解剖结构自然",
        "手指数量稳定",
        "皮肤与材质纹理真实",
        "背景干净",
        "无文字",
        "无水印",
        "水印",
        "logo",
        "低清伪影",
        "多余肢体",
        "masterpiece",
        "best quality",
        "sharp focus",
        "no text",
        "no watermark",
        "no logo",
    )
}
_PROMPT_CORE_IGNORE_SUBSTRINGS = tuple(
    _summary_dedupe_key(term)
    for term in (
        "画面呈现为自然连贯的正向画面说明",
        "主体身份、年龄气质、身体比例、脸部可读性和姿态关系保持稳定",
        "整体风格遵循",
        "不要突然偏向未选择的画风",
        "需要有前景中景和背景层次",
        "空间透视清楚",
        "环境细节服务主体而不是遮挡主体",
        "主体在画面中占比清晰",
        "头身关系自然",
        "必要时保证全身、手部、脚部和服装轮廓完整入镜",
        "重心、肩颈、手臂、腰胯和视线方向要互相协调",
        "看起来像真实摄影或成熟成片中的自然瞬间",
        "明确主光、辅光、轮廓光、阴影软硬、反射与色温",
        "让肤色、服装材质和场景边缘都有层次",
        "只作为叙事补充和视觉锚点出现、不抢走人物主体焦点",
        "最终画质强调",
        "无文字、水印、logo、低清伪影和多余肢体",
        "Create a coherent image centered on the main subject",
        "Keep the face, torso, limbs, clothing silhouette",
        "Organize the frame with a clear visual hierarchy",
        "Use a balanced lighting plan",
        "Finish by respecting the selected quality controls",
    )
)


def _prompt_core_signature(text: str, *, limit: int = 14) -> str:
    keys: list[str] = []
    for raw in _PROMPT_CORE_SPLIT_RE.split(str(text or "")):
        fragment = raw.strip()
        if not fragment:
            continue
        key = _summary_dedupe_key(fragment)
        if len(key) < 2 or key in _PROMPT_CORE_IGNORE_KEYS:
            continue
        if any(marker and marker in key for marker in _PROMPT_CORE_IGNORE_SUBSTRINGS) and len(key) <= 96:
            continue
        if key not in keys:
            keys.append(key[:64])
        if len(keys) >= limit:
            break
    if not keys:
        return _summary_dedupe_key(text)[:160]
    return "|".join(keys)


def _prompt_visual_signature(text: str, *, group_limit: int = 3) -> str:
    prompt_text = str(text or "").strip()
    if not prompt_text:
        return ""
    segments: list[str] = []
    for group_name, prefix in _RUNTIME_RANDOM_HISTORY_GROUP_PREFIX.items():
        group_keys: list[str] = []
        for raw_tag in _group_tags(group_name):
            tag = str(raw_tag).strip()
            if (
                not tag
                or tag == 无标签
                or tag in _RUNTIME_RANDOM_HISTORY_STABLE_TAGS
                or (group_name == "主体" and tag in _RUNTIME_RANDOM_HISTORY_GENERIC_SUBJECTS)
            ):
                continue
            if tag not in prompt_text:
                continue
            key = _summary_dedupe_key(tag)
            if key and key not in group_keys:
                group_keys.append(key[:40])
            if len(group_keys) >= group_limit:
                break
        if group_keys:
            segments.append(f"{prefix}:{','.join(group_keys)}")
    return "|".join(segments)


def _prompt_visual_signature_parts(signature: str) -> set[str]:
    text = str(signature or "").strip()
    if text.startswith("visual:"):
        text = text.removeprefix("visual:").strip()
    parts: set[str] = set()
    for segment in text.split("|"):
        segment = segment.strip()
        if not segment or ":" not in segment:
            continue
        prefix, values = segment.split(":", 1)
        prefix = prefix.strip()
        for raw_value in values.split(","):
            value = raw_value.strip()
            if prefix and value:
                parts.add(f"{prefix}:{value}")
    return parts


def _prompt_visual_signature_dimension_map(signature: str) -> dict[str, set[str]]:
    text = str(signature or "").strip()
    if text.startswith("visual:"):
        text = text.removeprefix("visual:").strip()
    dimensions: dict[str, set[str]] = {}
    for part in _prompt_visual_signature_parts(text):
        if ":" not in part:
            continue
        prefix, value = part.split(":", 1)
        prefix = prefix.strip()
        value = value.strip()
        if prefix and value:
            dimensions.setdefault(prefix, set()).add(value)
    return dimensions


def _prompt_compare_signatures(text: str) -> list[str]:
    signatures: list[str] = []
    core_signature = _prompt_core_signature(text)
    visual_signature = _prompt_visual_signature(text)
    if core_signature:
        signatures.append(core_signature)
    if visual_signature:
        signatures.append(f"visual:{visual_signature}")
    return _uniq(signatures)


def _prompt_history_signatures(text: str) -> list[str]:
    return _uniq([
        *_prompt_compare_signatures(text),
        *_runtime_random_markers_from_prompt([str(text or "")]),
    ])


_STRICT_VARIATION_SPATIAL_ZH = (
    "改用更深的前中后景递进，并让主体落在偏离中心的三分线位置",
    "压低机位并拉开主体与背景的尺度差，让空间形成新的纵深关系",
    "提高机位并增加前景遮挡层次，用俯视动线重新组织画面重心",
    "采用更近的镜头距离与侧向留白，让环境沿对角线向远处展开",
    "扩大环境占比并缩小主体比例，以清晰地标建立新的空间主线",
    "收紧景别并弱化远景信息，让面部、服装轮廓与局部环境形成层次",
    "将主体移到画面另一侧，并用连续结构线引导视线穿过背景",
    "改为稳定的中轴构图，同时通过前景框景与远景留白拉开层次",
)
_STRICT_VARIATION_LIGHT_ZH = (
    "主光从画面左后方切入，冷色辅光只保留在阴影边缘",
    "主光从画面右前方落下，暖色反射在材质转折处逐级衰减",
    "使用顶部窄光塑造轮廓，并让背景保持低照度的局部层次",
    "改用大面积侧窗柔光，让阴影方向与上一方案形成明显区别",
    "以低位逆光勾勒主体边缘，同时让环境光集中在空间深处",
    "采用阴天漫射光，利用细微色温差区分皮肤、服装和背景",
    "让主光穿过前景形成斑驳落点，并重新分配高光与暗部比例",
    "使用硬质侧逆光配合克制补光，突出不同的材质反射路径",
)
_STRICT_VARIATION_ACTION_ZH = (
    "身体重心转移到另一侧腿部，手部动作与视线朝向形成新的呼应",
    "让主体在行进中轻微回身，衣摆与发丝沿相反方向产生动态",
    "改为停步侧身姿态，一只手与场景物件建立明确的叙事联系",
    "让肩线和髋部朝向错开，视线越过镜头指向背景中的次要焦点",
    "采用坐姿或倚靠姿态，重新安排手臂支点与服装褶皱走向",
    "让主体抬手整理衣领或发丝，动作保持完整并改变轮廓节奏",
    "改为正面稳定站姿，但让头部、手部和脚步方向产生层次变化",
    "让主体向环境深处移动，回望镜头并留下清楚的动作轨迹",
)
_STRICT_VARIATION_SPATIAL_EN = (
    "use deeper foreground-to-background staging and place the subject on an off-center third",
    "lower the camera and widen the scale difference between subject and background",
    "raise the camera and introduce a foreground layer that redirects the composition",
    "move the camera closer and open lateral negative space along a diagonal depth line",
    "increase the environment share and use a clear landmark as the new spatial anchor",
    "tighten the framing and build depth through face, clothing silhouette, and nearby setting",
    "move the subject to the opposite side and guide the eye through continuous background lines",
    "use a stable axial composition framed by foreground structure and distant negative space",
)
_STRICT_VARIATION_LIGHT_EN = (
    "bring the key light from rear left with cool fill restricted to the shadow edge",
    "drop the key light from front right with warm bounce fading across material turns",
    "use a narrow overhead key while keeping the background in layered low illumination",
    "switch to broad side-window diffusion with a clearly different shadow direction",
    "use low backlight for the silhouette and concentrate ambient light deep in the setting",
    "use overcast diffusion with subtle color-temperature separation across materials",
    "pass the key through foreground texture to redistribute highlights and dark regions",
    "use hard side-backlight with restrained fill to reveal a new reflection path",
)
_STRICT_VARIATION_ACTION_EN = (
    "shift body weight to the opposite leg and align the hand gesture with a new gaze direction",
    "turn slightly while walking so clothing and hair move in opposing directions",
    "pause in a side-facing stance and connect one hand to a meaningful object in the setting",
    "offset shoulder and hip direction while the gaze targets a secondary background focus",
    "use a seated or leaning pose with new arm support and clothing-fold directions",
    "raise one hand toward the collar or hair while preserving a complete readable silhouette",
    "use a stable frontal stance with layered head, hand, and foot directions",
    "move deeper into the setting and look back toward the camera with a readable motion path",
)

_STRICT_VARIATION_SPECIAL_CUES_ZH: dict[str, tuple[str, ...]] = {
    "character_sheet": (
        "保持多视角设定图结构、正面、90度侧面、背面三幅等宽全身视图与同一角色身份不变，只调整背景明度、材质重点和留白节奏",
        "维持多视角设定图结构、1:1:1三栏、相同人物高度、同一头顶线和脚底基线，只在独立辅助带变化用户已明确要求的细节",
        "保留多视角设定图结构、正交镜头、中性站姿、角色比例和服装结构，在未锁定区域更换统一光线、背景色值与材质呈现",
    ),
    "tag_block": (
        "保持锁定块内容与用户块顺序不变，只在未锁定块中调整前中后景、光线落点和材质层次",
        "不改写编排主线与锁定标签，通过未锁定道具位置、背景结构和色温关系形成新的成片方案",
        "沿既定标签块顺序保留主体关系，仅变化未锁定的镜头距离、环境层次与次要细节",
    ),
    "non_person": (
        "重新安排主体结构朝向、关键功能部件与场景尺度关系，避免引入人物、服装或肢体动作",
        "改变物体或建筑的体块重心、表面材质和环境动线，让关键功能部件与空间层级形成新主线",
        "保留非人物主体类别，只调整结构展示面、运动或工作状态、光照路径和背景参照尺度",
    ),
    "nsfw": (
        "保留成年主体与工作台保护锚点，仅变化镜头距离、环境层次、色温和材质光泽",
        "不新增冲突动作或未选择的成熟表达，改用不同光线落点、背景结构和主体朝向形成差异",
        "维持已选服装、场景与成熟氛围，通过构图留白、轮廓光和道具位置生成新的成片关系",
    ),
}
_STRICT_VARIATION_SPECIAL_CUES_EN: dict[str, tuple[str, ...]] = {
    "character_sheet": (
        "preserve the multi-view character-sheet structure with equal-width front, true 90-degree side, and back full-body views and one identity while varying backdrop value, material emphasis, and negative-space rhythm",
        "keep the multi-view structure, balanced 1:1:1 columns, identical character height, shared head line, and ground baseline; vary only explicitly requested details in a separate support strip",
        "retain the multi-view three-view arrangement, orthographic cameras, neutral stance, character proportions, and wardrobe while changing unlocked lighting, backdrop tone, and material presentation",
    ),
    "tag_block": (
        "preserve locked blocks and the user-defined block order while varying only unlocked depth layers, light placement, and material emphasis",
        "keep the arranged visual spine and locked tags intact; vary unlocked prop placement, background structure, and color-temperature relationships",
        "follow the existing block order and subject relationships while changing only unlocked camera distance, environment depth, and secondary detail",
    ),
    "non_person": (
        "reorganize structural orientation, key functional components, and scene scale without introducing people, clothing, or body gestures",
        "vary the object or architecture massing, surface material, and environmental flow so function and spatial hierarchy form a new visual spine",
        "preserve the non-human subject category while changing the displayed structure side, operating state, light path, and scale references",
    ),
    "nsfw": (
        "preserve the adult subject and protected workspace anchors while varying camera distance, environment depth, color temperature, and material sheen",
        "add no conflicting action or unselected mature detail; create variation through light placement, background structure, and subject orientation",
        "keep the selected clothing, setting, and mature mood while changing negative space, rim light, and prop placement",
    ),
}


def _strict_variation_mode(settings: dict[str, Any]) -> str:
    if str(settings.get("角色设定图内部策略", "") or "").strip():
        return "character_sheet"
    if bool(settings.get("标签块编排启用", False)):
        return "tag_block"
    subject_type = str(settings.get("主体类型解析结果", "") or settings.get("主体类型", "") or "").strip()
    if subject_type == "非人物主体":
        return "non_person"
    if (
        bool(settings.get("NSFW工作台启用", False))
        or bool(settings.get("NSFW策略启用", False))
        or str(settings.get("标签反推模式", "") or "").strip() == "成人向成熟"
    ):
        return "nsfw"
    return ""


def _strict_special_variation_cues(settings: dict[str, Any], *, english: bool) -> tuple[str, ...]:
    mode = _strict_variation_mode(settings)
    catalog = _STRICT_VARIATION_SPECIAL_CUES_EN if english else _STRICT_VARIATION_SPECIAL_CUES_ZH
    return catalog.get(mode, ())



def _canonical_prompt_hash(text: str) -> str:
    raw_text = str(text or "")
    normalized = unicodedata.normalize("NFKC", raw_text).casefold()
    normalized = re.sub(r"[、,;；。｡]+", ",", normalized)
    normalized = re.sub(r"\s*,\s*", ",", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" ,")
    if not normalized and raw_text.strip():
        normalized = "<empty-after-canonical-normalization>"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""


def _legacy_canonical_prompt_hash(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""


def _parse_prompt_dedupe_cache(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        payload = value
    else:
        try:
            payload = json.loads(str(value or ""))
        except Exception:
            payload = {}
    channels = payload.get("channels") if isinstance(payload, dict) else {}
    try:
        source_version = int(payload.get("version", 3)) if isinstance(payload, dict) else 3
    except Exception:
        source_version = 3
    legacy_schema = source_version < 3
    normalized_channels: dict[str, dict[str, Any]] = {}
    for channel_name in ("prompt", "smart"):
        raw_channel = channels.get(channel_name, {}) if isinstance(channels, dict) else {}
        raw_hashes = [
            str(item).strip().lower()
            for item in (raw_channel.get("hashes", []) if isinstance(raw_channel, dict) else [])
            if re.fullmatch(r"[0-9a-fA-F]{64}", str(item).strip())
        ]
        raw_base_hashes = [
            str(item).strip().lower()
            for item in (raw_channel.get("base_hashes", []) if isinstance(raw_channel, dict) else [])
            if re.fullmatch(r"[0-9a-fA-F]{64}", str(item).strip())
        ]
        legacy_hashes = [
            str(item).strip().lower()
            for item in (raw_channel.get("legacy_hashes", []) if isinstance(raw_channel, dict) else [])
            if re.fullmatch(r"[0-9a-fA-F]{64}", str(item).strip())
        ]
        legacy_base_hashes = [
            str(item).strip().lower()
            for item in (raw_channel.get("legacy_base_hashes", []) if isinstance(raw_channel, dict) else [])
            if re.fullmatch(r"[0-9a-fA-F]{64}", str(item).strip())
        ]
        hashes = [] if legacy_schema else raw_hashes
        base_hashes = [] if legacy_schema else raw_base_hashes
        if legacy_schema:
            legacy_hashes = [*raw_hashes, *legacy_hashes]
            legacy_base_hashes = [*raw_base_hashes, *legacy_base_hashes]
        try:
            cursor = max(0, int(raw_channel.get("cursor", 0))) if isinstance(raw_channel, dict) else 0
        except Exception:
            cursor = 0
        normalized_channels[channel_name] = {
            "cursor": cursor,
            "hashes": _uniq(hashes)[:_STRICT_PROMPT_HASH_HISTORY_LIMIT],
            "base_hashes": _uniq(base_hashes)[:_STRICT_PROMPT_BASE_HASH_HISTORY_LIMIT],
            "legacy_hashes": _uniq(legacy_hashes)[:_STRICT_PROMPT_HASH_HISTORY_LIMIT],
            "legacy_base_hashes": _uniq(legacy_base_hashes)[:_STRICT_PROMPT_BASE_HASH_HISTORY_LIMIT],
        }
    return {
        "version": 3,
        "hash_algorithm": "nfkc-casefold-common-separators-v1",
        "channels": normalized_channels,
    }


def _serialize_prompt_dedupe_cache(state: dict[str, Any]) -> str:
    return json.dumps(_parse_prompt_dedupe_cache(state), ensure_ascii=False, separators=(",", ":"))


def _strip_strict_variation_clause(text: str) -> str:
    prompt = str(text or "").strip()
    marker_pattern = re.compile(
        r"(?:[，,；;]\s*)?(?:画面变化方向|visual\s+variation)(?:\s*[（(][^）)]*[）)])?\s*[:：]",
        re.IGNORECASE,
    )
    match = marker_pattern.search(prompt)
    return prompt[:match.start()].strip("，,。；; \t\n") if match else prompt


def _append_strict_variation_clause(text: str, cursor: int, settings: dict[str, Any]) -> str:
    prompt = _strip_strict_variation_clause(text)
    english = str(settings.get("提示词语言", "纯中文") or "纯中文").strip() == "纯英文"
    index = max(0, int(cursor))
    special_cues = _strict_special_variation_cues(settings, english=english)
    if special_cues:
        cue = special_cues[index % len(special_cues)]
        variation_pass = index // len(special_cues)
        if english:
            pass_note = f"; variation pass {variation_pass + 1}" if variation_pass else ""
            return f"{prompt.rstrip(' ,.;')}, visual variation: {cue}{pass_note}"
        pass_note = f"；第{variation_pass + 1}轮变化编排" if variation_pass else ""
        return f"{prompt.rstrip('，。；,.;')}；画面变化方向：{cue}{pass_note}"

    spatial_pool = _STRICT_VARIATION_SPATIAL_EN if english else _STRICT_VARIATION_SPATIAL_ZH
    light_pool = _STRICT_VARIATION_LIGHT_EN if english else _STRICT_VARIATION_LIGHT_ZH
    action_pool = _STRICT_VARIATION_ACTION_EN if english else _STRICT_VARIATION_ACTION_ZH
    spatial = spatial_pool[index % len(spatial_pool)]
    light = light_pool[(index // len(spatial_pool)) % len(light_pool)]
    action = action_pool[(index // (len(spatial_pool) * len(light_pool))) % len(action_pool)]
    combination_count = len(spatial_pool) * len(light_pool) * len(action_pool)
    variation_pass = index // combination_count
    if english:
        pass_note = f"; variation pass {variation_pass + 1}" if variation_pass else ""
        return f"{prompt.rstrip(' ,.;')}, visual variation: {spatial}; {light}; {action}{pass_note}"
    pass_note = f"；第{variation_pass + 1}轮变化编排" if variation_pass else ""
    return f"{prompt.rstrip('，。；,.;')}；画面变化方向：{spatial}；{light}；{action}{pass_note}"


def _append_strict_unique_fallback(text: str, cursor: int, settings: dict[str, Any]) -> str:
    prompt = _strip_strict_variation_clause(text)
    sequence = max(0, int(cursor)) + 1
    if str(settings.get("提示词语言", "纯中文") or "纯中文").strip() == "纯英文":
        return f"{prompt.rstrip(' ,.;')}, visual variation sequence {sequence:x}"
    return f"{prompt.rstrip('，。；,.;')}，画面变化序列 {sequence:x}"


def _strict_dedupe_prompt_list(
    node_key: str,
    prompt_list: list[str],
    settings: dict[str, Any],
    *,
    channel: str = "prompt",
) -> list[str]:
    channel_name = "smart" if channel == "smart" else "prompt"
    input_state = _parse_prompt_dedupe_cache(
        settings.get("连续生成避重缓存输出") or settings.get("连续生成避重缓存", "")
    )
    key = str(node_key or "").strip()
    changed_count = 0
    transaction_lock = _cache_key_lock(key) if key else nullcontext()

    with transaction_lock:
        if key:
            with _CACHE_LOCK:
                cache = _cache_bucket_unlocked(key, create=True)
                cached_state = deepcopy(cache.get("strict_prompt_dedupe", {})) if cache is not None else {}
        else:
            cached_state = {}

        memory_state = _parse_prompt_dedupe_cache(cached_state)
        input_channel = input_state["channels"][channel_name]
        memory_channel = memory_state["channels"][channel_name]
        history = _uniq([*memory_channel["hashes"], *input_channel["hashes"]])
        base_history = _uniq([*memory_channel["base_hashes"], *input_channel["base_hashes"]])
        legacy_history = _uniq([*memory_channel["legacy_hashes"], *input_channel["legacy_hashes"]])
        legacy_base_history = _uniq([*memory_channel["legacy_base_hashes"], *input_channel["legacy_base_hashes"]])
        forbidden = set(history)
        known_base_hashes = set(base_history)
        legacy_forbidden = set(legacy_history)
        legacy_known_base_hashes = set(legacy_base_history)
        consumed_legacy_hashes: set[str] = set()
        consumed_legacy_base_hashes: set[str] = set()
        cursor = max(int(memory_channel["cursor"]), int(input_channel["cursor"]))
        accepted: list[str] = []
        accepted_hashes: list[str] = []
        accepted_base_hashes: list[str] = []

        for raw_prompt in prompt_list:
            candidate = str(raw_prompt or "").strip()
            base_prompt = _strip_strict_variation_clause(candidate)
            base_hash = _canonical_prompt_hash(base_prompt)
            candidate_hash = _canonical_prompt_hash(candidate)
            legacy_base_hash = _legacy_canonical_prompt_hash(base_prompt)
            legacy_candidate_hash = _legacy_canonical_prompt_hash(candidate)
            legacy_candidate_match = bool(legacy_candidate_hash and legacy_candidate_hash in legacy_forbidden)
            legacy_base_match = bool(legacy_base_hash and legacy_base_hash in legacy_known_base_hashes)
            if legacy_candidate_match:
                consumed_legacy_hashes.add(legacy_candidate_hash)
            if legacy_base_match:
                consumed_legacy_base_hashes.add(legacy_base_hash)
            if candidate and (
                candidate_hash in forbidden
                or (base_hash and base_hash in known_base_hashes)
                or legacy_candidate_match
                or legacy_base_match
            ):
                resolved = False
                for _attempt in range(_STRICT_PROMPT_VARIATION_ATTEMPTS):
                    variation_cursor = cursor
                    cursor += 1
                    varied = _append_strict_variation_clause(base_prompt, variation_cursor, settings)
                    varied = _stabilize_prompt_output_impl(varied, settings) or varied
                    varied_hash = _canonical_prompt_hash(varied)
                    varied_legacy_hash = _legacy_canonical_prompt_hash(varied)
                    if (
                        varied_hash
                        and varied_hash not in forbidden
                        and varied_legacy_hash not in legacy_forbidden
                    ):
                        candidate = varied
                        candidate_hash = varied_hash
                        changed_count += 1
                        resolved = True
                        break
                while not resolved:
                    variation_cursor = cursor
                    cursor += 1
                    varied = _append_strict_unique_fallback(base_prompt, variation_cursor, settings)
                    varied_hash = _canonical_prompt_hash(varied)
                    varied_legacy_hash = _legacy_canonical_prompt_hash(varied)
                    if (
                        varied_hash
                        and varied_hash not in forbidden
                        and varied_legacy_hash not in legacy_forbidden
                    ):
                        candidate = varied
                        candidate_hash = varied_hash
                        changed_count += 1
                        resolved = True
            if not candidate:
                continue
            if not candidate_hash:
                candidate_hash = _canonical_prompt_hash(candidate)
            forbidden.add(candidate_hash)
            if base_hash:
                known_base_hashes.add(base_hash)
            accepted.append(candidate)
            accepted_hashes.append(candidate_hash)
            if base_hash:
                accepted_base_hashes.append(base_hash)

        merged_state = _parse_prompt_dedupe_cache(memory_state)
        for other_channel in ("prompt", "smart"):
            input_other = input_state["channels"][other_channel]
            memory_other = merged_state["channels"][other_channel]
            if other_channel == channel_name:
                memory_other["cursor"] = cursor
                memory_other["hashes"] = _uniq([*accepted_hashes, *history])
                memory_other["base_hashes"] = _uniq([*accepted_base_hashes, *base_history])
                memory_other["legacy_hashes"] = [item for item in legacy_history if item not in consumed_legacy_hashes]
                memory_other["legacy_base_hashes"] = [item for item in legacy_base_history if item not in consumed_legacy_base_hashes]
            else:
                memory_other["cursor"] = max(int(memory_other["cursor"]), int(input_other["cursor"]))
                memory_other["hashes"] = _uniq([*memory_other["hashes"], *input_other["hashes"]])
                memory_other["base_hashes"] = _uniq([*memory_other["base_hashes"], *input_other["base_hashes"]])
                memory_other["legacy_hashes"] = _uniq([*memory_other["legacy_hashes"], *input_other["legacy_hashes"]])
                memory_other["legacy_base_hashes"] = _uniq([*memory_other["legacy_base_hashes"], *input_other["legacy_base_hashes"]])
        merged_state = _parse_prompt_dedupe_cache(merged_state)
        if key:
            with _CACHE_LOCK:
                cache = _cache_bucket_unlocked(key, create=True)
                if cache is not None:
                    cache["strict_prompt_dedupe"] = merged_state

        settings["连续生成避重缓存输出"] = _serialize_prompt_dedupe_cache(merged_state)
        if changed_count:
            _merge_inference_notes(settings, [f"最终提示词严格避重：改写 {changed_count} 条与最近输出完全相同的提示词。"])
        return accepted


def _prompt_too_close_to_recent(text: str, recent_signatures: set[str]) -> bool:
    compare_signatures = _prompt_compare_signatures(text)
    if any(signature in recent_signatures for signature in compare_signatures):
        return True
    visual_signature = _prompt_visual_signature(text)
    candidate_parts = _prompt_visual_signature_parts(visual_signature)
    if len(candidate_parts) < 4:
        return False
    candidate_dimensions = _prompt_visual_signature_dimension_map(visual_signature)
    for recent in recent_signatures:
        recent_text = str(recent or "").strip()
        if not recent_text.startswith("visual:"):
            continue
        recent_parts = _prompt_visual_signature_parts(recent_text)
        if len(recent_parts) < 4:
            continue
        overlap = len(candidate_parts & recent_parts)
        if overlap >= 4 and overlap / max(1, min(len(candidate_parts), len(recent_parts))) >= 0.75:
            return True
        recent_dimensions = _prompt_visual_signature_dimension_map(recent_text)
        repeated_dimensions = sum(
            1
            for prefix, values in candidate_dimensions.items()
            if values and values & recent_dimensions.get(prefix, set())
        )
        if repeated_dimensions >= 4 and overlap >= 4:
            return True
        if repeated_dimensions >= 3 and overlap >= 5 and len(candidate_dimensions) <= 6:
            return True
    return False


_RECENT_PROMPT_VARIATION_CUES_ZH: tuple[str, ...] = (
    "加入新的空间纵深、材质触感和动作重心差异，让画面形成不同于上一轮的视觉主线",
    "强化不同的前中后景关系、边缘光方向和道具位置，使主体与环境产生新的阅读节奏",
    "调整服装材质层次、手部姿态和背景结构，让同一标签素材呈现新的成片方案",
    "通过不同色温对比、镜头距离和身体朝向组织画面，避免重复上一轮主体与场景组合",
    "让背景空间、光线落点和人物动作关系重新分配，保持标签锚点但形成新的画面骨架",
)
_RECENT_PROMPT_VARIATION_CUES_EN: tuple[str, ...] = (
    "add a new sense of spatial depth, material tactility, and body-weight shift so this image follows a different visual spine from the previous run",
    "reshape the foreground, middle ground, edge light direction, and prop placement to create a fresh reading rhythm around the subject",
    "vary the clothing material layers, hand gesture, and background structure while keeping the selected tags as flexible anchors",
    "use a different color-temperature contrast, camera distance, and body orientation to avoid repeating the previous subject-scene pairing",
    "redistribute background space, light placement, and pose relationships so the same tag anchors lead to a new composition",
)


def _recent_prompt_variation_cue(settings: dict[str, Any], index: int, recent_count: int) -> str:
    language = str(settings.get("提示词语言", "纯中文") or "纯中文").strip()
    english = language == "纯英文"
    cues = _strict_special_variation_cues(settings, english=english)
    if not cues:
        cues = _RECENT_PROMPT_VARIATION_CUES_EN if english else _RECENT_PROMPT_VARIATION_CUES_ZH
    if not cues:
        return ""
    seed = _safe_int(settings.get("seed", 0), 0, 0, _SEED_MAX)
    return cues[(seed + index + recent_count) % len(cues)]


def _append_recent_prompt_variation_cue(text: str, settings: dict[str, Any], index: int, recent_count: int) -> str:
    cue = _recent_prompt_variation_cue(settings, index, recent_count)
    prompt = str(text or "").strip()
    if not cue or not prompt or cue in prompt:
        return prompt
    language = str(settings.get("提示词语言", "纯中文") or "纯中文").strip()
    if language == "纯英文":
        return f"{prompt.rstrip(' ,.;')} , {cue}"
    return f"{prompt.rstrip('，。；,.;')}；{cue}"


def _stabilize_prompt_list_outputs(
    prompt_list: list[str],
    original_prompt_list: list[str],
    settings: dict[str, Any],
) -> list[str]:
    stabilized: list[str] = []
    seen_signatures: set[str] = set()
    recent_signatures = {
        str(signature).strip()
        for signature in settings.get("最近提示词指纹", [])
        if str(signature).strip()
    }
    fallback_count = 0
    fallback_indices: set[int] = set()
    recent_fallback_count = 0
    variation_cue_count = 0
    originals = [str(prompt or "").strip() for prompt in original_prompt_list]
    for index, prompt in enumerate(prompt_list):
        cleaned = _stabilize_prompt_output_impl(prompt, settings)
        compare_signatures = set(_prompt_compare_signatures(cleaned))
        if compare_signatures and compare_signatures & seen_signatures and index < len(originals):
            fallback = _stabilize_prompt_output_impl(originals[index], settings)
            fallback_signatures = set(_prompt_compare_signatures(fallback))
            if fallback and (not fallback_signatures or not (fallback_signatures & seen_signatures)):
                cleaned = fallback
                compare_signatures = fallback_signatures
                fallback_count += 1
                fallback_indices.add(index)
        if _prompt_too_close_to_recent(cleaned, recent_signatures) and index < len(originals):
            fallback = _stabilize_prompt_output_impl(originals[index], settings)
            fallback_signatures = set(_prompt_compare_signatures(fallback))
            if fallback and fallback_signatures and not _prompt_too_close_to_recent(fallback, recent_signatures) and not (fallback_signatures & seen_signatures):
                cleaned = fallback
                compare_signatures = fallback_signatures
                recent_fallback_count += 1
                fallback_indices.add(index)
        if _prompt_too_close_to_recent(cleaned, recent_signatures):
            varied = _stabilize_prompt_output_impl(
                _append_recent_prompt_variation_cue(cleaned, settings, index, len(recent_signatures)),
                settings,
            )
            if varied and varied != cleaned:
                cleaned = varied
                compare_signatures = set(_prompt_compare_signatures(cleaned))
                variation_cue_count += 1
        if cleaned:
            seen_signatures.update(compare_signatures)
            stabilized.append(cleaned)
    if fallback_count:
        notes = [str(note).strip() for note in settings.get("推理纠偏说明", []) if str(note).strip()]
        note = f"模型批量去同化：发现 {fallback_count} 条输出过近，已回退对应原始随机/标签种子。"
        if note not in notes:
            notes.append(note)
        settings["推理纠偏说明"] = notes
    if recent_fallback_count:
        notes = [str(note).strip() for note in settings.get("推理纠偏说明", []) if str(note).strip()]
        note = f"最近提示词避重：发现 {recent_fallback_count} 条输出接近历史，已回退到本轮 Skill 随机主线。"
        if note not in notes:
            notes.append(note)
        settings["推理纠偏说明"] = notes
    if variation_cue_count:
        notes = [str(note).strip() for note in settings.get("推理纠偏说明", []) if str(note).strip()]
        note = f"最近提示词差异补强：为 {variation_cue_count} 条仍接近历史的输出追加视觉变化方向。"
        if note not in notes:
            notes.append(note)
        settings["推理纠偏说明"] = notes
    settings["模型稳定化回退索引"] = sorted(fallback_indices)
    return stabilized


def _enforce_natural_prompt_list_outputs(
    prompt_list: list[str],
    primary_fallbacks: list[str],
    secondary_fallbacks: list[str],
    settings: dict[str, Any],
    *,
    channel: str,
) -> list[str]:
    """Keep every final positive-output path inside the natural-language contract."""

    prompts = [str(prompt or "").strip() for prompt in prompt_list]
    primary = [str(prompt or "").strip() for prompt in primary_fallbacks]
    secondary = [str(prompt or "").strip() for prompt in secondary_fallbacks]
    result: list[str] = []
    fallback_indices: list[int] = []
    for index, candidate in enumerate(prompts):
        options = (
            candidate,
            primary[index] if index < len(primary) else "",
            secondary[index] if index < len(secondary) else "",
        )
        accepted = next(
            (option for option in options if _is_natural_language_prompt_impl(option, settings)),
            next((option for option in options if option), ""),
        )
        if accepted != candidate:
            fallback_indices.append(index)
        result.append(accepted)

    channel_name = "智能文本" if channel == "smart" else "主提示词"
    settings["自然语言输出合同"] = "所有模式的正向输出必须为完整自然语言画面描述"
    settings[f"{channel_name}自然语言回退索引"] = fallback_indices
    if fallback_indices:
        fallback_count = len(fallback_indices)
        settings["自然语言输出回退数量"] = max(
            0,
            int(settings.get("自然语言输出回退数量", 0) or 0),
        ) + fallback_count
        _merge_inference_notes(
            settings,
            [f"{channel_name}自然语言合同：{fallback_count} 条标签链或非完整句输出已回退为自然语言结果。"],
        )
    return result


def 构建运行时随机预览状态(payload: dict[str, Any]) -> dict[str, Any]:
    state = payload if isinstance(payload, dict) else {}
    tag_groups, tag_group_index, tag_group_memberships = _tag_catalog_snapshot()
    raw_settings = state.get("settings") if isinstance(state.get("settings"), dict) else {}
    settings = _bounded_runtime_preview_settings(raw_settings)
    settings["运行时随机标签"] = bool(settings.get("运行时随机标签", SETTING_DEFAULTS["运行时随机标签"]))
    settings["运行时随机模式"] = str(settings.get("运行时随机模式", SETTING_DEFAULTS["运行时随机模式"]))
    settings["运行时随机强度"] = str(settings.get("运行时随机强度", SETTING_DEFAULTS["运行时随机强度"]))
    settings["随机主题池"] = str(settings.get("随机主题池", SETTING_DEFAULTS["随机主题池"]))
    settings["核心标签锁定数量"] = _safe_int(settings.get("核心标签锁定数量"), 10, 0, 500)
    settings["锁定标签白名单"] = str(settings.get("锁定标签白名单", ""))
    settings["随机排除标签"] = str(settings.get("随机排除标签", ""))
    settings["seed"] = _safe_int(settings.get("seed"), 0, 0, _SEED_MAX)
    settings["unique_id"] = _bounded_runtime_preview_scalar(
        raw_settings.get("unique_id") or state.get("unique_id"),
        256,
    )
    raw_cache_namespace = (
        state.get("cache_namespace")
        or state.get("cacheNamespace")
        or raw_settings.get("cache_namespace")
        or raw_settings.get("cacheNamespace")
    )
    raw_cache_namespace = _bounded_runtime_preview_scalar(raw_cache_namespace, 128)
    cache_namespace = _normalize_cache_namespace(raw_cache_namespace)
    settings["cache_namespace"] = cache_namespace
    settings["cache_key"] = _resolve_stage_cache_key(
        settings["unique_id"],
        extra_pnginfo=state.get("extra_pnginfo") or raw_settings.get("extra_pnginfo"),
        cache_namespace=raw_cache_namespace if str(raw_cache_namespace or "").strip() else cache_namespace,
    )
    _apply_adult_reverse_profile(settings)
    settings["运行时随机保护标签"] = ""
    dedupe_tags = _bounded_runtime_preview_tags(state.get("_randomDedupeCache"))
    settings["随机补充避重缓存"] = str(
        settings.get("随机补充避重缓存")
        or ",".join(dedupe_tags)
        or SETTING_DEFAULTS["随机补充避重缓存"]
    )[:_RUNTIME_PREVIEW_SETTING_MAX_CHARS]

    raw_selected = state.get("selected") if isinstance(state.get("selected"), dict) else {}
    selected = OrderedDict()
    for group_name, slot_count, _ in tag_groups:
        values = raw_selected.get(group_name, [])
        selected[group_name] = _bounded_runtime_preview_tags(
            values if isinstance(values, (list, tuple)) else [],
            max_items=max(32, int(slot_count)),
            max_total_chars=16_384,
        )
    raw_custom_tags = state.get("customTags")
    custom_tags = _bounded_runtime_preview_tags(raw_custom_tags)

    selected, custom_tags, initial_notes = _normalize_inference_state(
        selected,
        custom_tags,
        settings,
        tag_group_index=tag_group_index,
        tag_group_memberships=tag_group_memberships,
    )
    if initial_notes:
        _merge_inference_notes(settings, initial_notes)

    raw_nsfw_workspace = state.get("nsfwWorkspace") if isinstance(state.get("nsfwWorkspace"), dict) else state.get("nsfw_workspace")
    nsfw_workspace = (
        _normalize_nsfw_workspace_impl(raw_nsfw_workspace)
        if isinstance(raw_nsfw_workspace, dict)
        else None
    )
    settings["NSFW工作台状态指纹"] = _nsfw_workspace_state_fingerprint(nsfw_workspace)
    nsfw_enabled = nsfw_workspace is not None and bool(nsfw_workspace.get("enabled", False))
    if nsfw_enabled:
        _apply_nsfw_generation_profile(settings)
        nsfw_output = 应用NSFW工作台到阶段状态(
            nsfw_workspace,
            selected=selected,
            custom_tags=custom_tags,
            tag_group_index=tag_group_index,
        )
        selected = nsfw_output["selected"]
        custom_tags = nsfw_output["custom_tags"]
        settings["运行时随机保护标签"] = ",".join(
            _uniq([*_parse_tags(settings.get("运行时随机保护标签")), *nsfw_output.get("protected_tags", [])])
        )

    generated: list[str] = []
    requested_seed = int(settings.get("seed", 0) or 0)
    effective_seed = requested_seed
    if bool(settings.get("运行时随机标签", False)):
        if requested_seed == 0:
            effective_seed = random.SystemRandom().randint(1, 0x7FFFFFFF)
        settings["seed"] = effective_seed
        settings["运行时随机模式解析结果"] = _resolve_runtime_random_mode_impl(
            str(settings.get("运行时随机模式", "") or ""),
            selected,
            settings,
        )
        selected, custom_tags, generated = _build_runtime_tags(
            selected,
            custom_tags,
            settings,
            tag_groups=tag_groups,
            tag_group_index=tag_group_index,
        )
        effective_seed = int(settings.get("运行时随机有效种子", effective_seed) or effective_seed)
        settings["seed"] = requested_seed
    preview_template_style = _infer_template_style(_collect_all_tags(selected, custom_tags), str(settings["模板风格"]))
    _biased_style, selected, custom_tags = _apply_random_theme_pool_bias(
        preview_template_style,
        selected,
        custom_tags,
        settings,
        tag_group_index=tag_group_index,
        tag_group_memberships=tag_group_memberships,
    )
    selected, custom_tags = _apply_template_style_profile_bias(
        _biased_style,
        selected,
        custom_tags,
        settings,
        tag_group_index=tag_group_index,
        tag_group_memberships=tag_group_memberships,
    )
    selected, custom_tags, final_notes = _normalize_inference_state(
        selected,
        custom_tags,
        settings,
        tag_group_index=tag_group_index,
        tag_group_memberships=tag_group_memberships,
    )
    if final_notes:
        _merge_inference_notes(settings, final_notes)
    if nsfw_enabled and nsfw_workspace is not None:
        normalized_active_tags = set(_collect_all_tags(selected, custom_tags))
        nsfw_output = 应用NSFW工作台到阶段状态(
            nsfw_workspace,
            selected=selected,
            custom_tags=custom_tags,
            allowed_tags=normalized_active_tags,
            tag_group_index=tag_group_index,
        )
        selected = nsfw_output["selected"]
        custom_tags = nsfw_output["custom_tags"]
        settings["运行时随机保护标签"] = ",".join(nsfw_output.get("protected_tags", []))
        _merge_inference_notes(settings, ["NSFW工作台锚点保护：仅保留最终归一化后仍有效的工作台显式选择。"])
    for group_name, slot_count, _ in tag_groups:
        selected[group_name] = _bounded_runtime_preview_tags(
            selected.get(group_name, []),
            max_items=max(32, int(slot_count)),
            max_total_chars=16_384,
        )
    custom_tags = _bounded_runtime_preview_tags(custom_tags)
    theme_generated = [
        str(marker).split(":", 1)[1].strip()
        for marker in settings.get("随机主题池档案标记", [])
        if str(marker).startswith("tag:") and str(marker).split(":", 1)[1].strip()
    ]
    style_generated = [
        str(marker).split(":", 1)[1].strip()
        for marker in settings.get("模板风格档案标记", [])
        if str(marker).startswith("styletag:") and str(marker).split(":", 1)[1].strip()
    ]
    generated = _uniq([*generated, *theme_generated, *style_generated])
    if generated:
        active_tags = set(_collect_all_tags(selected, custom_tags))
        generated = [tag for tag in generated if tag in active_tags]
    profile_markers = [
        *list(settings.get("随机主题池档案标记", []) or []),
        *list(settings.get("模板风格档案标记", []) or []),
    ]
    if bool(settings.get("运行时随机标签", False)):
        settings["seed"] = effective_seed
        settings["运行时随机有效种子"] = effective_seed
        settings["运行时随机预览令牌"] = _new_runtime_random_preview_marker(settings, selected, custom_tags)
    else:
        settings["运行时随机预览令牌"] = ""

    public_settings = dict(settings)
    public_settings.pop("API密钥", None)
    public_settings.pop("API额外请求头", None)
    public_settings.pop("_API密钥脱敏值", None)
    result = {
        "selected": {key: list(value) for key, value in selected.items()},
        "customTags": list(custom_tags),
        "settings": public_settings,
        "meta": {
            "runtime_random_enabled": bool(settings.get("运行时随机标签", False)),
            "runtime_random_generated_tags": list(generated),
            "runtime_random_effective_seed": int(settings.get("运行时随机有效种子", settings.get("seed", 0)) or 0),
            "runtime_random_preview_marker": str(settings.get("运行时随机预览令牌", "") or ""),
            "normalization_notes": list(settings.get("推理纠偏说明", [])),
        },
        "_randomSupplementTags": _uniq([*generated, *profile_markers]),
    }
    if nsfw_workspace is not None:
        result["nsfwWorkspace"] = nsfw_workspace
    return result


def 构建状态可视化预览(payload: dict[str, Any]) -> dict[str, Any]:
    return 构建运行时随机预览状态(payload)


_阶段输入参数说明 = {
    "内置上下文长度": "内置 GGUF 路线的上下文窗口。默认 8192；越大越占内存/显存，普通提示词生成通常不需要超过 16384。",
    "内置GPU层数": "内置 GGUF 路线的 GPU 卸载层数。-1=尽可能使用 GPU，0=纯 CPU；显存不足时逐步降低。",
    "内置KV缓存K类型": "本地模型 K 缓存精度。默认 F16 最稳；显存紧张且 llama-cpp-python 支持时可用 q8_0。",
    "内置KV缓存V类型": "本地模型 V 缓存精度。默认 F16 最稳；显存紧张且 llama-cpp-python 支持时可用 q8_0。",
    "模板风格": "控制整体媒介和视觉风格。自动最通用；明确选风格可提高一致性，但批量变化会相对收敛。",
    "主体类型": "自动判断人物、非人物或场景主体；自动识别不准时再手动指定。",
    "案例输出结构": "控制提示词组织方式。自动会按当前任务选择；长段版适合直接出图，分段版更便于检查和编辑。",
    "运行时随机标签": "开启后每次运行按随机模式、强度和主题池改变标签；关闭时仍保留剧情轮换与连续避重。",
    "运行时随机模式": "自动判断会按当前标签密度选择保留或重写；全随机差异最大，保留核心最稳定，重写主体与场景用于换题材。",
    "运行时随机强度": "弱=小幅补充，中=平衡，强=明显变化，极限拉开=尽量扩大主体、场景、动作、服装和光影差异。",
    "随机主题池": "限制随机素材的题材来源。自动覆盖面最广；指定主题池可保持系列方向。",
    "锁定标签白名单": "逗号或换行分隔。白名单标签优先保留，且不受核心锁定数量和随机排除影响。",
    "随机排除标签": "逗号或换行分隔。用于阻止随机补入指定标签；不会删除白名单或 NSFW 保护标签。",
    "生成数量": "单次输出 1-20 条。数量越大，模型耗时、API token 和历史记录体积越高；日常建议 1-4。",
    "提示词语言": "选择纯中文、英文提示词加中文说明或纯英文；应按下游绘图模型的语言理解能力设置。",
    "详细度": "简洁用于预览；标准/详细使用长自然语言剧情合同，详细会保留更多空间、动作、光影和材质信息。",
    "输出模式": "完整结果包含说明与结构化信息；仅提示词优先便于直接连接下游文本编码节点。",
    "标签反推模式": "自动平衡适合普通任务；成人向成熟仅在合法成年内容且明确需要时使用。",
    "风格隔离策略": "平衡收敛最通用；严格隔离会清理跨媒介污染；允许漂移适合实验性混合风格。",
    "优先柔和肤质": "人物任务中偏向自然柔和的皮肤与高光过渡；非人物或需要粗粝质感时关闭。",
    "抑制文字伪影": "加强无文字、无水印和无 logo 约束；确实需要画面文字时关闭。",
    "自定义补充标签": "填写标签库之外的必要事实，支持逗号或换行；显式补充会高于模板和随机内容。",
    "额外要求": "自然语言补充镜头、剧情、限制和偏好。写具体可执行要求，避免与已选标签互相冲突。",
    "智能文本匹配": "开启后解析智能文本并合并到标签、模板、图片反推和模型链路；关闭时只使用节点现有状态。",
    "智能文本输入": "输入主体、事件、场景、动作和氛围。完整因果描述比堆叠关键词更容易生成清晰剧情。",
    "智能文本风格优先": "自动判断最通用；节点优先保持已选风格，文本优先更尊重输入描述中的媒介和题材。",
    "标签块编排启用": "按标签块顺序组织提示词。锁定块会作为高优先级事实保留。",
    "标签块编排JSON": "由编排面板维护的结构化数据；建议通过界面编辑，不要手工截断或填写无效 JSON。",
    "图片反推模式": "角色设定图默认生成正面、90度侧面、背面三幅等宽全身视图，并统一人物高度、基线和正交镜头；仅反推描述只提取参考图中的可见事实。",
    "图片反推最大边长": "送入视觉模型前的最长边。默认 960；越大细节越多，但编码和推理更慢、占用更高。",
    "系统提示词覆盖": "高级模型合同。默认模板已包含自然语言、剧情、语言和长度约束；只有明确了解后果时修改。",
    "最大生成token": "每条模型输出的 token 上限。默认 1800；太低可能截断长提示词，太高会增加本地/API 耗时和费用。",
    "温度": "控制模型随机性。0.45-0.65 稳定，0.7-0.9 更有变化；建议只小幅调整并与 top_p/top_k 配合。",
    "top_p": "核采样范围。默认 0.9；降低更保守，提高更多样。通常保持 0.85-0.95。",
    "top_k": "每步候选词数量。默认 40；降低更稳定，提高更多样，0 表示由模型/接口决定。",
    "重复惩罚": "抑制局部复读。默认 1.08；常用 1.05-1.15，过高可能破坏专有名词和句子连贯性。",
    "频率惩罚": "按已出现次数减少复读。默认 0；提示词重复明显时建议 0.1-0.3，过高会造成措辞生硬。",
    "存在惩罚": "只要词已出现就降低再次出现概率。默认 0；需要拓展新细节时建议 0.05-0.2。",
    "seed": "随机种子。运行时随机开启时 0=每次自动新种子，正数便于复现；ComfyUI 生成后控制仍可递增或随机。",
    "输出think块": "仅用于诊断模型思考文本。日常关闭可减少无关输出、历史体积和解析干扰。",
}


class QwenTE提示词合集拆分器:
    @classmethod
    def INPUT_TYPES(cls):
        required = OrderedDict()
        required["正向提示词合集"] = ("STRING", {"default": "", "multiline": True})
        required["分隔模式"] = (["双换行", "单换行"], {"default": "双换行"})
        return {"required": required}

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("提示词1", "提示词2", "提示词3", "提示词4")
    FUNCTION = "run"
    CATEGORY = "Qwen TE"

    def run(self, 正向提示词合集, 分隔模式):
        text = str(正向提示词合集 or "").strip()
        if not text:
            return ("", "", "", "")
        if str(分隔模式).strip() == "单换行":
            parts = [item.strip() for item in text.splitlines() if item.strip()]
        else:
            normalized = text.replace("\r\n", "\n").replace("\r", "\n")
            parts = [item.strip() for item in normalized.split("\n\n") if item.strip()]
        outputs = [str(parts[index]).strip() if index < len(parts) else "" for index in range(4)]
        return tuple(outputs)


class QwenTE阶段式提示词生成器:
    @classmethod
    def INPUT_TYPES(cls):
        model_list, mmproj_list = _内置模型文件选项()
        required = OrderedDict()
        required["模型来源"] = (模型来源选项, {"default": "仅Skill", "tooltip": "仅Skill=本地Skill直接生成图像、智能文本和视频提示词；本地模型=Skill先生成可靠底稿，再由外接兼容模型或 models/LLM 中的内置模型后置润色；API接口=Skill底稿交给云端、Ollama、LM Studio 或其他兼容服务润色。旧值本地GGUF会自动迁移。"})
        required["内置模型系列"] = (_内置模型系列选项, {"default": "Qwen3.5-VL", "tooltip": "本地模型未连接外部输入时，阶段提示词节点会按这里的设置直接加载内置 GGUF。"})
        required["内置主模型"] = (model_list, {"default": model_list[0], "tooltip": "内置加载路线使用的 GGUF 文件，放到 ComfyUI/models/LLM/；其他模型可连接 qwen模型 输入。"})
        required["内置视觉投影mmproj"] = (mmproj_list, {"default": "无", "tooltip": "多模态需要 mmproj；纯文本提示词生成可选“无”。"})
        required["内置启用思考"] = ("BOOLEAN", {"default": False, "tooltip": "Qwen/Gemma 思考开关；提示词生成通常可关闭。"})
        required["内置上下文长度"] = ("INT", {"default": 8192, "min": 1024, "max": 327680, "step": 256})
        required["内置GPU层数"] = ("INT", {"default": -1, "min": -1, "max": 9999, "step": 1})
        required["内置KV缓存K类型"] = (_内置模型KV缓存类型选项, {"default": _内置默认KV缓存类型})
        required["内置KV缓存V类型"] = (_内置模型KV缓存类型选项, {"default": _内置默认KV缓存类型})
        required["API服务商"] = (API服务商选项, {"default": "OpenAI兼容", "tooltip": "大多数云模型和本地服务都支持 OpenAI-compatible /v1/chat/completions；Claude/Gemini 也提供原生适配。"})
        required["API地址"] = ("STRING", {"default": "", "multiline": False, "tooltip": "可填 Base URL，例如 https://api.openai.com/v1；不得包含查询参数或片段。留空时使用服务商预设。"})
        required["API密钥"] = ("STRING", {"default": "env:QWEN_TE_API_KEY", "multiline": False, "tooltip": "推荐 env:环境变量名。环境变量密钥只会发送到服务商预设来源；自定义来源需加入 QWEN_TE_CUSTOM_API_SECRET_ORIGINS。直接填写的 key 会保存在工作流中。"})
        required["API模型"] = ("STRING", {"default": "", "multiline": False, "tooltip": "模型名，例如 gpt-4o-mini、deepseek-chat、qwen-plus、claude-3-5-haiku-latest、gemini-2.5-flash。"})
        required["API超时秒"] = (
            "INT",
            {
                "default": 120,
                "min": 5,
                "max": 600,
                "step": 1,
                "tooltip": "连接与响应读取超时。瞬时超时、断连、429 和服务端 5xx 会自动有界重试一次。",
            },
        )
        required["API额外请求头"] = ("STRING", {"default": "", "multiline": True, "tooltip": "可选。支持 JSON 或每行 Header: Value，例如 OpenRouter 的 HTTP-Referer / X-Title。"})
        required["模板风格"] = (模板选项, {"default": "自动"})
        required["主体类型"] = (主体类型选项, {"default": "自动"})
        required["案例输出结构"] = (案例输出结构选项, {"default": "自动"})
        required["运行时随机标签"] = ("BOOLEAN", {"default": False})
        required["运行时随机模式"] = (运行时随机模式选项, {"default": "自动判断"})
        required["核心标签锁定数量"] = ("INT", {"default": 10, "min": 0, "max": 500, "step": 1, "tooltip": "保留核心模式最多锁定 500 个槽位与自定义标签；显式白名单和 NSFW 保护标签不受该数量截断。"})
        required["运行时随机强度"] = (运行时随机强度选项, {"default": "中"})
        required["随机主题池"] = (随机主题池选项, {"default": "自动"})
        required["锁定标签白名单"] = ("STRING", {"default": "", "multiline": False})
        required["随机排除标签"] = ("STRING", {"default": "", "multiline": False})
        required["生成数量"] = ("INT", {"default": 3, "min": 1, "max": 20, "step": 1})
        required["提示词语言"] = (提示词语言选项, {"default": "纯中文"})
        required["详细度"] = (详细度选项, {"default": "标准"})
        required["输出模式"] = (输出模式选项, {"default": "完整结果"})
        required["标签反推模式"] = (标签反推模式选项, {"default": "自动平衡"})
        required["风格隔离策略"] = (风格隔离策略选项, {"default": "平衡收敛"})
        required["优先柔和肤质"] = ("BOOLEAN", {"default": False})
        required["抑制文字伪影"] = ("BOOLEAN", {"default": False})
        for group in 分组配置:
            group_name = str(group["name"])
            for index in range(1, int(group["slots"]) + 1):
                # The custom panel hydrates choices from /qwen_te/prompt_library.
                # Keeping the same lists in every raw slot made object_info exceed 1 MB.
                required[f"{group_name}标签{index}"] = (
                    "STRING",
                    {"default": "无", "multiline": False},
                )
        required["自定义补充标签"] = ("STRING", {"default": "", "multiline": False})
        required["额外要求"] = ("STRING", {"default": "", "multiline": True})
        required["智能文本匹配"] = ("BOOLEAN", {"default": False})
        required["智能文本输入"] = ("STRING", {"default": "", "multiline": True})
        required["智能文本风格优先"] = (智能文本风格优先选项, {"default": "自动判断"})
        required["标签块编排启用"] = ("BOOLEAN", {"default": False})
        required["标签块编排JSON"] = ("STRING", {"default": "", "multiline": True})
        required["图片反推生成"] = ("BOOLEAN", {"default": False, "tooltip": "接入参考图片后，先用视觉模型反推画面描述，再进入智能文本/标签/模板生成链路。"})
        required["图片反推模式"] = (["角色设定图", "仅反推描述"], {"default": "角色设定图"})
        required["图片反推最大边长"] = ("INT", {"default": 960, "min": 256, "max": 2048, "step": 64})
        required["系统提示词覆盖"] = ("STRING", {"default": DEFAULT_STAGE_PROMPT_SYSTEM_TEMPLATE, "multiline": True})
        required["最大生成token"] = ("INT", {"default": 1800, "min": 128, "max": 8192, "step": 1})
        required["温度"] = ("FLOAT", {"default": 0.62, "min": 0.0, "max": 2.0, "step": 0.01})
        required["top_p"] = ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.01})
        required["top_k"] = ("INT", {"default": 40, "min": 0, "max": 200, "step": 1})
        required["重复惩罚"] = ("FLOAT", {"default": 1.08, "min": 0.5, "max": 2.0, "step": 0.01})
        required["频率惩罚"] = ("FLOAT", {"default": 0.0, "min": 0.0, "max": 2.0, "step": 0.01})
        required["存在惩罚"] = ("FLOAT", {"default": 0.0, "min": 0.0, "max": 2.0, "step": 0.01})
        required["seed"] = ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF, "step": 1, "control_after_generate": True})
        required["输出think块"] = ("BOOLEAN", {"default": False})
        required["随机补充避重缓存"] = ("STRING", {"default": "", "multiline": False})
        required["连续生成避重缓存"] = ("STRING", {"default": "", "multiline": False})
        required["运行时随机保护标签"] = ("STRING", {"default": "", "multiline": False})
        required["运行时随机预览令牌"] = ("STRING", {"default": "", "multiline": False})
        for name, tooltip in _阶段输入参数说明.items():
            if name in required:
                required[name][1].setdefault("tooltip", tooltip)
        native_visible_names = {
            "模板风格",
            "运行时随机标签",
            "运行时随机模式",
            "随机主题池",
            "生成数量",
            "提示词语言",
            "详细度",
            "输出模式",
        }
        for name, input_spec in required.items():
            if name not in native_visible_names:
                input_spec[1].setdefault("advanced", True)
        return {
            "required": required,
            "optional": {"qwen模型": (_STAGE_MODEL_ANY_TYPE,), "参考图片": ("IMAGE",)},
            "hidden": {"unique_id": "UNIQUE_ID", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("结果全文", "首条正向提示词", "已选标签", "JSON结果", "推荐负面词", "正向提示词合集", "智能文本", "视频提示词")
    FUNCTION = "run"
    CATEGORY = "Qwen TE"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def run(self, qwen模型=None, **kwargs):
        settings = {k: v for k, v in kwargs.items()}
        settings["unique_id"] = str(kwargs.get("unique_id") or kwargs.get("id") or "").strip()
        settings["extra_pnginfo"] = kwargs.get("extra_pnginfo")
        source = _normalize_stage_model_source(
            settings.get("模型来源", SETTING_DEFAULTS["模型来源"]) or SETTING_DEFAULTS["模型来源"]
        )
        settings["模型来源"] = source
        if source in {"API接口", "仅Skill"}:
            qwen模型 = _安全加载阶段模型(settings)
        elif qwen模型 is None:
            qwen模型 = _安全加载阶段模型(settings)
        else:
            settings["模型来源实际"] = "外接本地模型"
            settings["模型回退说明"] = ""
            settings["模型调用基础来源"] = "外接本地模型"
            settings["模型调用状态"] = "已连接，等待调用"
            settings["模型调用尝试次数"] = 0
            settings["模型调用成功次数"] = 0
            settings["模型调用失败次数"] = 0
            settings["模型活动回退数量"] = 0
            settings["模型调用采纳次数"] = 0
            settings["模型调用错误"] = []
        outputs = _run_stage(qwen模型, **settings)
        cache_namespace = _extract_cache_namespace_from_extra_pnginfo(
            settings.get("extra_pnginfo"),
            settings.get("unique_id"),
        )
        cache_payload = 获取阶段节点输出缓存(
            settings.get("unique_id"),
            cache_namespace=cache_namespace or None,
        )
        execution_history = (
            cache_payload.get("execution_history", [])
            if isinstance(cache_payload, dict)
            else []
        )
        return {
            "ui": {
                "qwen_te_stage_output": list(outputs),
                "qwen_te_stage_output_history": execution_history,
            },
            "result": outputs,
        }


class QwenTE通用模型阶段式提示词生成器(QwenTE阶段式提示词生成器):
    @classmethod
    def INPUT_TYPES(cls):
        data = super().INPUT_TYPES()
        required = OrderedDict(data.get("required", {}))
        for name in [
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
        ]:
            required.pop(name, None)
        data["required"] = OrderedDict({"通用模型": (_STAGE_MODEL_ANY_TYPE,)})
        data["required"].update(required)
        data["optional"] = {"参考图片": ("IMAGE",)}
        return data

    def run(self, 通用模型, *args, **kwargs):
        kwargs["模型来源"] = 本地模型来源
        return super().run(通用模型, **kwargs)


__all__ = [
    "QwenTE提示词合集拆分器",
    "QwenTE阶段式提示词生成器",
    "QwenTE通用模型阶段式提示词生成器",
    "构建运行时随机预览状态",
    "构建状态可视化预览",
    "获取阶段节点输出缓存",
]
