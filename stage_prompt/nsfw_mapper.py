# -*- coding: utf-8 -*-
"""Mapping helpers that translate NSFW workspace values into stage state."""

from __future__ import annotations

import json
import re
import importlib.util
import pathlib
import unicodedata
from collections import OrderedDict
from typing import Any, Iterable

try:
    from .nsfw_presets import (
        NSFW_NEGATIVE_PRESETS,
        NSFW_QUALITY_TAGS,
        NSFW_SELECTOR_FIELDS,
        NSFW_WORKSPACE_OPTIONS,
        NSFW_WORKSPACE_PRESETS,
    )
except ImportError:  # pragma: no cover - direct file loading in focused tests
    _MODULE_PATH = pathlib.Path(__file__).with_name("nsfw_presets.py")
    _SPEC = importlib.util.spec_from_file_location("stage_prompt_nsfw_presets_runtime", _MODULE_PATH)
    if _SPEC is None or _SPEC.loader is None:
        raise
    _MODULE = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_MODULE)
    NSFW_NEGATIVE_PRESETS = _MODULE.NSFW_NEGATIVE_PRESETS
    NSFW_QUALITY_TAGS = _MODULE.NSFW_QUALITY_TAGS
    NSFW_SELECTOR_FIELDS = _MODULE.NSFW_SELECTOR_FIELDS
    NSFW_WORKSPACE_OPTIONS = _MODULE.NSFW_WORKSPACE_OPTIONS
    NSFW_WORKSPACE_PRESETS = _MODULE.NSFW_WORKSPACE_PRESETS


_TEXT_SPLIT_PATTERN = re.compile(r"[,\n\r\t;；，、]+")
_ASCII_TOKEN_PATTERN = re.compile(r"\s+[A-Za-z0-9][A-Za-z0-9_\- ]*$")
_EMPTY_SENTINEL = "——"
_VALUE_FIELDS = (
    "scene",
    "action",
    "outfit",
    "mood",
    "anatomy_terms",
    "explicit_terms",
    "adult_action_style",
    "workspace_custom_tags",
    *NSFW_SELECTOR_FIELDS,
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
)
_RANDOM_ALL_FIELDS = (
    "scene",
    "action",
    "outfit",
    "mood",
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
)
_WORKSPACE_LIST_FIELDS = frozenset({"trigger_words", "workspace_custom_tags"})
_WORKSPACE_FIELD_ORDER = (
    "enabled",
    "preset",
    "quality_tier",
    "random_mode",
    "random_nonce",
    "negative_preset",
    "negative_apply_mode",
    "custom_negative",
    "trigger_words",
    *_VALUE_FIELDS,
    "custom_prefix",
    "custom_suffix",
)
_WORKSPACE_ALLOWED_FIELDS = frozenset(_WORKSPACE_FIELD_ORDER)
_WORKSPACE_MAX_JSON_BYTES = 128 * 1024
_WORKSPACE_MAX_LIST_ITEMS = 128
_WORKSPACE_MAX_TERM_CHARS = 512
_WORKSPACE_MAX_LIST_SCAN_CHARS = 4 * _WORKSPACE_MAX_LIST_ITEMS * _WORKSPACE_MAX_TERM_CHARS
_WORKSPACE_MAX_SCALAR_CHARS = 2_048
_WORKSPACE_MAX_CUSTOM_TEXT_CHARS = 512
_WORKSPACE_MAX_NEGATIVE_CHARS = 32_768
_WORKSPACE_MAX_CUSTOM_TAGS = 256
_WORKSPACE_MAX_CUSTOM_TAG_CHARS = 512
_WORKSPACE_MAX_CUSTOM_TAG_TOTAL_CHARS = 32_768
_WORKSPACE_MAX_SCANNED_LIST_VALUES = 4 * _WORKSPACE_MAX_LIST_ITEMS
_WORKSPACE_FIELD_ALIASES = {
    "triggerWords": "trigger_words",
    "workspaceCustomTags": "workspace_custom_tags",
    "selectorCharacter": "selector_character",
    "selectorOutfit": "selector_outfit",
    "selectorAction": "selector_action",
    "selectorScene": "selector_scene",
    "selectorExpression": "selector_expression",
    "selectorProp": "selector_prop",
    "anatomyTerms": "anatomy_terms",
    "explicitTerms": "explicit_terms",
    "adultActionStyle": "adult_action_style",
    "cameraMovement": "camera_movement",
    "cameraAngle": "camera_angle",
    "lightSource": "light_source",
    "lightType": "light_type",
    "lensType": "lens_type",
    "focalLength": "focal_length",
    "colorTone": "color_tone",
    "visualStyle": "visual_style",
    "randomMode": "random_mode",
    "randomNonce": "random_nonce",
    "qualityTier": "quality_tier",
    "negativePreset": "negative_preset",
    "negativeApplyMode": "negative_apply_mode",
    "customNegative": "custom_negative",
    "customPrefix": "custom_prefix",
    "customSuffix": "custom_suffix",
}


def _workspace_json_size(payload: dict[str, Any]) -> int:
    return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _clean_workspace_scalar(value: Any, max_chars: int) -> str:
    if isinstance(value, (dict, list, tuple, set)):
        return ""
    limit = max(0, int(max_chars))
    raw_text = ("" if value is None else str(value))[: 4 * limit]
    text = unicodedata.normalize("NFKC", raw_text)
    text = re.sub(r"[\u0000-\u001f\u007f]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:limit].rstrip()


def _normalize_workspace_list(value: Any) -> list[str]:
    if isinstance(value, dict):
        return []
    raw_values = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    seen: set[str] = set()
    for value_index, raw_value in enumerate(raw_values):
        if value_index >= _WORKSPACE_MAX_SCANNED_LIST_VALUES:
            break
        if isinstance(raw_value, (dict, list, tuple, set)):
            continue
        raw_text = ("" if raw_value is None else str(raw_value))[:_WORKSPACE_MAX_LIST_SCAN_CHARS]
        normalized = unicodedata.normalize("NFKC", raw_text)
        for term_index, raw_term in enumerate(_TEXT_SPLIT_PATTERN.split(normalized)):
            if term_index >= _WORKSPACE_MAX_SCANNED_LIST_VALUES:
                break
            term = _clean_workspace_scalar(raw_term, _WORKSPACE_MAX_TERM_CHARS)
            if not term or term == _EMPTY_SENTINEL or term in seen:
                continue
            seen.add(term)
            result.append(term)
            if len(result) >= _WORKSPACE_MAX_LIST_ITEMS:
                return result
    return result


def _fit_workspace_value(
    payload: dict[str, Any],
    field: str,
    value: Any,
) -> Any | None:
    if isinstance(value, list):
        fitted: list[str] = []
        for item in value:
            candidate = [*fitted, item]
            if _workspace_json_size({**payload, field: candidate}) > _WORKSPACE_MAX_JSON_BYTES:
                break
            fitted = candidate
        return fitted
    if not isinstance(value, str):
        return value if _workspace_json_size({**payload, field: value}) <= _WORKSPACE_MAX_JSON_BYTES else None
    if _workspace_json_size({**payload, field: value}) <= _WORKSPACE_MAX_JSON_BYTES:
        return value
    low = 0
    high = len(value)
    while low < high:
        middle = (low + high + 1) // 2
        if _workspace_json_size({**payload, field: value[:middle]}) <= _WORKSPACE_MAX_JSON_BYTES:
            low = middle
        else:
            high = middle - 1
    return value[:low].rstrip() if low > 0 else None


def normalize_nsfw_workspace(workspace: Any) -> dict[str, Any]:
    """Whitelist and bound untrusted workspace state before mapping or caching it."""

    if not isinstance(workspace, dict):
        return {}
    source = {field: workspace[field] for field in _WORKSPACE_FIELD_ORDER if field in workspace}
    for legacy_field, current_field in _WORKSPACE_FIELD_ALIASES.items():
        if current_field not in source and legacy_field in workspace:
            source[current_field] = workspace[legacy_field]
    normalized: dict[str, Any] = {}
    for field in _WORKSPACE_FIELD_ORDER:
        if field not in source or field not in _WORKSPACE_ALLOWED_FIELDS:
            continue
        raw_value = source.get(field)
        if field == "enabled":
            if isinstance(raw_value, str):
                value: Any = raw_value.strip().casefold() in {"1", "true", "yes", "on", "开启", "是"}
            else:
                value = bool(raw_value)
        elif field in _WORKSPACE_LIST_FIELDS:
            value = _normalize_workspace_list(raw_value)
        else:
            max_chars = (
                _WORKSPACE_MAX_NEGATIVE_CHARS
                if field == "custom_negative"
                else _WORKSPACE_MAX_CUSTOM_TEXT_CHARS
                if field in {"custom_prefix", "custom_suffix"}
                else _WORKSPACE_MAX_SCALAR_CHARS
            )
            value = _clean_workspace_scalar(raw_value, max_chars)
        fitted = _fit_workspace_value(normalized, field, value)
        if fitted is not None:
            normalized[field] = fitted
    return normalized


def _clean_text(value: Any, max_chars: int = _WORKSPACE_MAX_TERM_CHARS) -> str:
    text = _clean_workspace_scalar(value, max_chars)
    return "" if not text or text == _EMPTY_SENTINEL else text


def _iter_split_terms(value: Any) -> Iterable[str]:
    if isinstance(value, (list, tuple, set)):
        parts = value
    elif isinstance(value, str):
        parts = _TEXT_SPLIT_PATTERN.split(value[:_WORKSPACE_MAX_LIST_SCAN_CHARS])
    else:
        parts = [value]
    emitted = 0
    for part_index, part in enumerate(parts):
        if part_index >= _WORKSPACE_MAX_SCANNED_LIST_VALUES:
            break
        text = _clean_text(part)
        if text:
            yield text
            emitted += 1
            if emitted >= _WORKSPACE_MAX_LIST_ITEMS:
                break


def _iter_selector_terms(value: Any) -> Iterable[str]:
    for term in _iter_split_terms(value):
        alias = _ASCII_TOKEN_PATTERN.sub("", term).strip(" /()") if re.search(r"[\u4e00-\u9fff]", term) else term
        yield alias or term


def _iter_workspace_terms(workspace: dict[str, Any]) -> Iterable[str]:
    trigger_words = workspace.get("trigger_words", [])
    if isinstance(trigger_words, (list, tuple, set)):
        for item in trigger_words:
            yield from _iter_split_terms(item)
    else:
        yield from _iter_split_terms(trigger_words)

    for field in _VALUE_FIELDS:
        raw_value = workspace.get(field, "")
        if field in NSFW_SELECTOR_FIELDS:
            yield from _iter_selector_terms(raw_value)
        elif isinstance(raw_value, (list, tuple, set)):
            for item in raw_value:
                yield from _iter_split_terms(item)
        else:
            yield from _iter_split_terms(raw_value)


def _canonical_seed_value(value: Any) -> str:
    if isinstance(value, (dict, list, tuple, set)):
        return ""
    raw_text = ("" if value is None else str(value))[: 4 * _WORKSPACE_MAX_SCALAR_CHARS]
    text = unicodedata.normalize("NFKC", raw_text)[:_WORKSPACE_MAX_SCALAR_CHARS]
    text = re.sub(r"\s+", " ", text).strip()
    return "" if text == _EMPTY_SENTINEL else text


def _canonical_trigger_word_seed(value: Any) -> str:
    raw_values = value if isinstance(value, (list, tuple, set)) else [value]
    terms: set[str] = set()
    for value_index, raw_value in enumerate(raw_values):
        if value_index >= _WORKSPACE_MAX_SCANNED_LIST_VALUES:
            break
        if isinstance(raw_value, (dict, list, tuple, set)):
            continue
        raw_text = ("" if raw_value is None else str(raw_value))[:_WORKSPACE_MAX_LIST_SCAN_CHARS]
        normalized = unicodedata.normalize("NFKC", raw_text)
        for term_index, raw_term in enumerate(_TEXT_SPLIT_PATTERN.split(normalized)):
            if term_index >= _WORKSPACE_MAX_SCANNED_LIST_VALUES:
                break
            term = re.sub(r"\s+", " ", raw_term).strip()[:_WORKSPACE_MAX_TERM_CHARS]
            if term and term != _EMPTY_SENTINEL:
                terms.add(term)
                if len(terms) >= _WORKSPACE_MAX_LIST_ITEMS:
                    break
        if len(terms) >= _WORKSPACE_MAX_LIST_ITEMS:
            break
    return "|".join(sorted(terms, key=lambda term: term.encode("utf-16-be")))


def _selection_hash(value: str) -> int:
    result = 0
    for character in value:
        result = ((result * 31) + ord(character)) & 0xFFFFFFFF
    return result


def _pick_random_option(workspace: dict[str, Any], field: str) -> str:
    options = [
        str(option).strip()
        for option in NSFW_WORKSPACE_OPTIONS.get(field, [])
        if str(option or "").strip() and str(option).strip() != _EMPTY_SENTINEL
    ]
    if not options:
        return _EMPTY_SENTINEL
    seed_text = "|".join(
        [
            _canonical_seed_value(workspace.get("preset", "")),
            _canonical_seed_value(workspace.get("quality_tier", "")),
            _canonical_seed_value(workspace.get("negative_preset", "")),
            _canonical_seed_value(workspace.get("random_mode", "")),
            field,
            _canonical_trigger_word_seed(workspace.get("trigger_words", [])),
            _canonical_seed_value(workspace.get("random_nonce", "")),
        ]
    )
    return options[_selection_hash(seed_text) % len(options)]


def _resolve_preset_workspace(workspace: dict[str, Any]) -> dict[str, str]:
    preset_name = _clean_text(workspace.get("preset", "——")) or "——"
    preset = dict(NSFW_WORKSPACE_PRESETS.get(preset_name, {}))
    return {
        field: value
        for field, value in preset.items()
        if not _clean_text(workspace.get(field, ""))
        and _clean_text(value)
    }


def _resolve_quality_tags(workspace: dict[str, Any]) -> list[str]:
    quality_name = _clean_text(workspace.get("quality_tier", "高质量")) or "高质量"
    return [tag for tag in NSFW_QUALITY_TAGS.get(quality_name, NSFW_QUALITY_TAGS["高质量"]) if tag]


def _resolve_effective_workspace(workspace: dict[str, Any]) -> dict[str, Any]:
    effective = normalize_nsfw_workspace(workspace)
    effective.update(_resolve_preset_workspace(effective))
    random_mode = _clean_text(effective.get("random_mode", "关闭")) or "关闭"
    if random_mode in {"场景随机", "全部随机"}:
        effective["scene"] = _pick_random_option(effective, "scene")
    if random_mode in {"动作随机", "全部随机"}:
        effective["action"] = _pick_random_option(effective, "action")
    if random_mode == "全部随机":
        for field in _RANDOM_ALL_FIELDS:
            effective[field] = _pick_random_option(effective, field)
    return effective


def resolve_nsfw_negative_prompt(workspace: dict[str, Any]) -> str:
    """Resolve the active negative prompt string for the current workspace."""

    preset_name = _clean_text(workspace.get("negative_preset", "标准负面提示词")) or "标准负面提示词"
    if preset_name == "自定义负面提示词":
        return _clean_text(workspace.get("custom_negative", ""), _WORKSPACE_MAX_NEGATIVE_CHARS)
    return _clean_text(
        NSFW_NEGATIVE_PRESETS.get(preset_name, NSFW_NEGATIVE_PRESETS["标准负面提示词"]),
        _WORKSPACE_MAX_NEGATIVE_CHARS,
    )


def _resolve_negative_branch(workspace: dict[str, Any]) -> dict[str, str]:
    preset_name = _clean_text(workspace.get("negative_preset", "标准负面提示词")) or "标准负面提示词"
    mode = _clean_text(workspace.get("negative_apply_mode", "preview")) or "preview"
    if mode not in {"preview", "override", "append"}:
        mode = "preview"
    prompt = resolve_nsfw_negative_prompt(workspace)
    return {
        "mode": mode,
        "prompt": prompt,
        "preset": preset_name,
    }


def map_nsfw_workspace_to_stage_state(
    workspace: dict[str, Any],
    *,
    tag_group_index: dict[str, str],
    group_slot_limits: dict[str, int],
) -> dict[str, Any]:
    """Map a workspace payload into grouped stage-state selections."""

    normalized_workspace = normalize_nsfw_workspace(workspace)
    workspace.clear()
    workspace.update(normalized_workspace)
    effective_workspace = _resolve_effective_workspace(workspace)
    selected = OrderedDict((group_name, []) for group_name in group_slot_limits.keys())
    custom_tags: list[str] = []
    custom_tag_chars = 0

    def append_custom_tag(value: Any) -> None:
        nonlocal custom_tag_chars
        text = _clean_text(value, _WORKSPACE_MAX_CUSTOM_TAG_CHARS)
        if not text or text in custom_tags or len(custom_tags) >= _WORKSPACE_MAX_CUSTOM_TAGS:
            return
        separator_chars = 1 if custom_tags else 0
        remaining = _WORKSPACE_MAX_CUSTOM_TAG_TOTAL_CHARS - custom_tag_chars - separator_chars
        if remaining <= 0:
            return
        text = text[:remaining].rstrip()
        if not text:
            return
        custom_tags.append(text)
        custom_tag_chars += len(text) + separator_chars

    for tag in _resolve_quality_tags(effective_workspace):
        append_custom_tag(tag)

    for tag in _iter_workspace_terms(effective_workspace):
        group_name = tag_group_index.get(tag)
        if group_name is None:
            append_custom_tag(tag)
            continue

        bucket = selected.setdefault(group_name, [])
        limit = max(0, int(group_slot_limits.get(group_name, len(bucket) + 1)))
        if tag in bucket:
            continue
        if len(bucket) < limit:
            bucket.append(tag)
        else:
            append_custom_tag(tag)

    for field in ("custom_prefix", "custom_suffix"):
        append_custom_tag(workspace.get(field, ""))

    return {
        "selected": selected,
        "custom_tags": custom_tags,
        "negative_prompt": resolve_nsfw_negative_prompt(workspace),
        "negative": _resolve_negative_branch(workspace),
    }
