# -*- coding: utf-8 -*-
"""State building helpers for stage prompt nodes."""

from __future__ import annotations

from collections import OrderedDict
import json
import re
import unicodedata
from typing import Any, Callable


_TEXT_FIELD_NOISE_LINES = {"true", "false", "none", "null"}
_TEXT_FIELD_MAX_CHARS = 32_768
_TEXT_FIELD_SCAN_MAX_CHARS = 4 * _TEXT_FIELD_MAX_CHARS
_TEXT_FIELD_MAX_LINES = 256
_TEXT_FIELD_MAX_LINE_CHARS = 4_096
_CUSTOM_TAG_MAX_ITEMS = 256
_CUSTOM_TAG_MAX_ITEM_CHARS = 512
_CUSTOM_TAG_MAX_TOTAL_CHARS = 32_768
_CUSTOM_TAG_MAX_SCANNED_ITEMS = 4 * _CUSTOM_TAG_MAX_ITEMS
_SELECTED_GROUP_MAX_SCANNED_ITEMS = 64
_SETTING_TEXT_MAX_CHARS = 32_768
_SYSTEM_PROMPT_MAX_CHARS = 131_072
_NOTE_MAX_ITEMS = 64
_NOTE_MAX_ITEM_CHARS = 1_024
_NOTE_MAX_TOTAL_CHARS = 32_768
_TAG_BLOCK_JSON_MAX_CHARS = 262_144
_TAG_BLOCK_JSON_SCAN_MAX_CHARS = 4 * _TAG_BLOCK_JSON_MAX_CHARS
_TAG_BLOCK_JSON_MAX_NODES = 50_000
_TAG_BLOCK_JSON_MAX_DEPTH = 64
_SEED_MAX = 0xFFFFFFFFFFFFFFFF
_UNSAFE_JSON_CONTROL_CHARS = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]+")
_LEGACY_REVERSE_MODE_ALIASES = {
    "商业摄影": "自动平衡",
    "高密度站点": "自动平衡",
}
_TRUE_BOOLEAN_VALUES = {"1", "true", "yes", "on", "开启", "开", "是"}
_FALSE_BOOLEAN_VALUES = {"", "0", "false", "no", "off", "关闭", "关", "否", "none", "null", "undefined"}


def _clean_user_text_field(value: Any) -> str:
    """Remove widget-shift noise while preserving useful free-form requirements."""

    text = str(value or "")[:_TEXT_FIELD_SCAN_MAX_CHARS]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned_lines: list[str] = []
    seen: set[str] = set()
    total_chars = 0
    for raw_line in text.split("\n"):
        line = _UNSAFE_JSON_CONTROL_CHARS.sub("", raw_line).strip()
        if not line:
            continue
        if line.casefold() in _TEXT_FIELD_NOISE_LINES:
            continue
        line = line[:_TEXT_FIELD_MAX_LINE_CHARS].rstrip()
        if line in seen:
            continue
        separator_chars = 1 if cleaned_lines else 0
        remaining = _TEXT_FIELD_MAX_CHARS - total_chars - separator_chars
        if remaining <= 0:
            break
        line = line[:remaining].rstrip()
        if not line:
            break
        cleaned_lines.append(line)
        seen.add(line)
        total_chars += len(line) + separator_chars
        if len(cleaned_lines) >= _TEXT_FIELD_MAX_LINES:
            break
    return "\n".join(cleaned_lines).strip()


def _clean_bounded_text_field(value: Any, max_chars: int = _SETTING_TEXT_MAX_CHARS) -> str:
    limit = max(0, int(max_chars))
    text = str(value or "")[:limit].replace("\r\n", "\n").replace("\r", "\n")
    return _UNSAFE_JSON_CONTROL_CHARS.sub("", text)[:limit]


def _normalize_tag_text(value: Any) -> str:
    raw_text = str(value or "")[: 4 * _CUSTOM_TAG_MAX_ITEM_CHARS]
    text = unicodedata.normalize("NFKC", raw_text)
    text = _UNSAFE_JSON_CONTROL_CHARS.sub("", text)
    return re.sub(r"\s+", " ", text).strip()[:_CUSTOM_TAG_MAX_ITEM_CHARS].rstrip()


def _normalize_custom_tags(value: Any) -> list[str]:
    raw_items = value if isinstance(value, (list, tuple, set)) else [value]
    result: list[str] = []
    seen: set[str] = set()
    total_chars = 0
    for raw_index, raw in enumerate(raw_items):
        if raw_index >= _CUSTOM_TAG_MAX_SCANNED_ITEMS:
            break
        tag = _normalize_tag_text(raw)
        if not tag or tag in seen:
            continue
        separator_chars = 1 if result else 0
        remaining = _CUSTOM_TAG_MAX_TOTAL_CHARS - total_chars - separator_chars
        if remaining <= 0:
            break
        tag = tag[:remaining].rstrip()
        if not tag:
            break
        result.append(tag)
        seen.add(tag)
        total_chars += len(tag) + separator_chars
        if len(result) >= _CUSTOM_TAG_MAX_ITEMS:
            break
    return result


def _normalize_selected_tags(
    selected: OrderedDict[str, list[str]],
    group_slot_limits: dict[str, int],
) -> OrderedDict[str, list[str]]:
    result: OrderedDict[str, list[str]] = OrderedDict()
    for group_index, (raw_group_name, raw_tags) in enumerate(selected.items()):
        if group_index >= _SELECTED_GROUP_MAX_SCANNED_ITEMS:
            break
        group_name = str(raw_group_name)
        limit = max(0, int(group_slot_limits.get(group_name, _CUSTOM_TAG_MAX_ITEMS)))
        result[group_name] = _normalize_custom_tags(raw_tags)[:limit]
    return result


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in _TRUE_BOOLEAN_VALUES:
            return True
        if normalized in _FALSE_BOOLEAN_VALUES:
            return False
        return bool(default)
    if value is None:
        return bool(default)
    return bool(default)


def _tag_block_json_structure_is_bounded(value: Any) -> bool:
    counters = {"nodes": 0, "chars": 0}

    def visit(item: Any, depth: int) -> bool:
        counters["nodes"] += 1
        if counters["nodes"] > _TAG_BLOCK_JSON_MAX_NODES or depth > _TAG_BLOCK_JSON_MAX_DEPTH:
            return False
        if isinstance(item, str):
            counters["chars"] += len(item)
            return counters["chars"] <= _TAG_BLOCK_JSON_MAX_CHARS
        if item is None or isinstance(item, (bool, int, float)):
            return True
        if isinstance(item, (list, tuple)):
            return all(visit(child, depth + 1) for child in item)
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, (str, int, float, bool, type(None))):
                    return False
                if isinstance(key, str):
                    counters["chars"] += len(key)
                    if counters["chars"] > _TAG_BLOCK_JSON_MAX_CHARS:
                        return False
                if not visit(child, depth + 1):
                    return False
            return True
        return False

    return visit(value, 0)


def _clean_tag_block_json_field(value: Any) -> str:
    """Keep normal payloads intact and compact oversized valid JSON safely."""

    if isinstance(value, (dict, list)):
        if not _tag_block_json_structure_is_bounded(value):
            return ""
        try:
            text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError, OverflowError):
            return ""
    else:
        text = str(value or "")[:_TAG_BLOCK_JSON_SCAN_MAX_CHARS]
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    was_oversized = len(text) > _TAG_BLOCK_JSON_MAX_CHARS
    text = _UNSAFE_JSON_CONTROL_CHARS.sub("", text).strip()
    if not was_oversized and len(text) <= _TAG_BLOCK_JSON_MAX_CHARS:
        return text
    try:
        parsed = json.loads(text)
        compact = json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError, OverflowError):
        return ""
    return compact if len(compact) <= _TAG_BLOCK_JSON_MAX_CHARS else ""


def _resolve_system_prompt_override(value: Any, default_value: Any) -> str:
    text = _clean_bounded_text_field(value, _SYSTEM_PROMPT_MAX_CHARS).strip()
    fallback = _clean_bounded_text_field(default_value, _SYSTEM_PROMPT_MAX_CHARS).strip()
    if not text:
        return fallback
    # Old workflows can shift numeric widgets into this multiline system prompt slot.
    # A numeric/boolean override would disable the real Skill template, so recover safely.
    if text.casefold() in _TEXT_FIELD_NOISE_LINES or text.isdigit():
        return fallback
    return text


def _normalize_reverse_mode(value: Any, default_value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return str(default_value or "").strip()
    return _LEGACY_REVERSE_MODE_ALIASES.get(text, text)


def _coerce_note_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_text = str(value or "")[: 4 * _NOTE_MAX_TOTAL_CHARS]
        raw_items = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    notes: list[str] = []
    total_chars = 0
    for raw in raw_items:
        text = _clean_bounded_text_field(raw, _NOTE_MAX_ITEM_CHARS).strip()
        if not text or text in notes:
            continue
        separator_chars = 1 if notes else 0
        remaining = _NOTE_MAX_TOTAL_CHARS - total_chars - separator_chars
        if remaining <= 0:
            break
        text = text[:remaining].rstrip()
        if not text:
            break
        notes.append(text)
        total_chars += len(text) + separator_chars
        if len(notes) >= _NOTE_MAX_ITEMS:
            break
    return notes


def _absorb_groupable_custom_tags(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    *,
    tag_group_index: dict[str, str],
    group_slot_limits: dict[str, int],
) -> tuple[OrderedDict[str, list[str]], list[str]]:
    next_selected = OrderedDict((group_name, list(tags)) for group_name, tags in selected.items())
    remaining_custom: list[str] = []
    for raw_tag in list(custom_tags):
        tag = str(raw_tag).strip()
        if not tag:
            continue
        group_name = tag_group_index.get(tag)
        if not group_name:
            remaining_custom.append(tag)
            continue
        bucket = next_selected.get(group_name)
        if bucket is None:
            remaining_custom.append(tag)
            continue
        if tag in bucket:
            continue
        limit = max(0, int(group_slot_limits.get(group_name, len(bucket) + 1)))
        if len(bucket) < limit:
            bucket.append(tag)
        else:
            remaining_custom.append(tag)
    return next_selected, remaining_custom


def build_state_from_kwargs(
    kwargs: dict[str, Any],
    *,
    collect_selected: Callable[[dict[str, Any]], tuple[OrderedDict[str, list[str]], list[str]]],
    tag_group_index: Callable[[], dict[str, str]],
    group_slot_limits: dict[str, int],
    setting_defaults: dict[str, Any],
    safe_int: Callable[[Any, int, int, int], int],
    safe_float: Callable[[Any, float, float, float], float],
    normalize_inference_state: Callable[[OrderedDict[str, list[str]], list[str], dict[str, Any]], tuple[OrderedDict[str, list[str]], list[str], list[str]]],
    collect_all_tags: Callable[[OrderedDict[str, list[str]], list[str]], list[str]],
) -> tuple[OrderedDict[str, list[str]], list[str], dict[str, Any], str]:
    selected, custom_tags = collect_selected(kwargs)
    selected = _normalize_selected_tags(selected, group_slot_limits)
    custom_tags = _normalize_custom_tags(custom_tags)
    selected, custom_tags = _absorb_groupable_custom_tags(
        selected,
        custom_tags,
        tag_group_index=tag_group_index(),
        group_slot_limits=group_slot_limits,
    )
    settings = {name: kwargs.get(name, default) for name, default in setting_defaults.items()}
    settings["运行时随机标签"] = _coerce_bool(
        kwargs.get("运行时随机标签", setting_defaults.get("运行时随机标签", False)),
        bool(setting_defaults.get("运行时随机标签", False)),
    )
    settings["运行时随机模式"] = str(kwargs.get("运行时随机模式", setting_defaults["运行时随机模式"]))
    settings["运行时随机强度"] = str(kwargs.get("运行时随机强度", setting_defaults["运行时随机强度"]))
    settings["核心标签锁定数量"] = safe_int(kwargs.get("核心标签锁定数量", 10), 10, 0, 500)
    settings["标签反推模式"] = _normalize_reverse_mode(
        kwargs.get("标签反推模式", setting_defaults["标签反推模式"]),
        setting_defaults["标签反推模式"],
    )
    settings["生成数量"] = safe_int(kwargs.get("生成数量", 5), 5, 1, 20)
    settings["提示词语言"] = str(kwargs.get("提示词语言", setting_defaults["提示词语言"]))
    settings["详细度"] = str(kwargs.get("详细度", setting_defaults["详细度"]))
    settings["输出模式"] = str(kwargs.get("输出_mode", kwargs.get("输出模式", setting_defaults["输出模式"])))
    settings["优先柔和肤质"] = _coerce_bool(
        kwargs.get("优先柔和肤质", setting_defaults.get("优先柔和肤质", False)),
        bool(setting_defaults.get("优先柔和肤质", False)),
    )
    settings["抑制文字伪影"] = _coerce_bool(
        kwargs.get("抑制文字伪影", setting_defaults.get("抑制文字伪影", False)),
        bool(setting_defaults.get("抑制文字伪影", False)),
    )
    settings["额外要求"] = _clean_user_text_field(kwargs.get("额外要求", ""))
    settings["智能文本匹配"] = _coerce_bool(
        kwargs.get("智能文本匹配", setting_defaults.get("智能文本匹配", False)),
        bool(setting_defaults.get("智能文本匹配", False)),
    )
    settings["智能文本输入"] = _clean_user_text_field(kwargs.get("智能文本输入", setting_defaults.get("智能文本输入", "")))
    settings["标签块编排启用"] = _coerce_bool(
        kwargs.get("标签块编排启用", setting_defaults.get("标签块编排启用", False)),
        bool(setting_defaults.get("标签块编排启用", False)),
    )
    settings["标签块编排JSON"] = _clean_tag_block_json_field(
        kwargs.get("标签块编排JSON", setting_defaults.get("标签块编排JSON", ""))
    )
    settings["图片反推生成"] = _coerce_bool(
        kwargs.get("图片反推生成", setting_defaults.get("图片反推生成", False)),
        bool(setting_defaults.get("图片反推生成", False)),
    )
    settings["图片反推模式"] = str(kwargs.get("图片反推模式", setting_defaults.get("图片反推模式", "角色设定图")))
    settings["图片反推最大边长"] = safe_int(
        kwargs.get("图片反推最大边长", setting_defaults.get("图片反推最大边长", 960)),
        int(setting_defaults.get("图片反推最大边长", 960)),
        256,
        2048,
    )
    for name in (
        "内置模型系列",
        "内置主模型",
        "内置视觉投影mmproj",
        "内置启用思考",
        "内置上下文长度",
        "内置GPU层数",
        "内置KV缓存K类型",
        "内置KV缓存V类型",
    ):
        if name in setting_defaults:
            settings[name] = kwargs.get(name, setting_defaults.get(name))
    settings["锁定标签白名单"] = str(kwargs.get("锁定标签白名单", ""))
    settings["随机排除标签"] = str(kwargs.get("随机排除标签", ""))
    settings["随机补充避重缓存"] = str(kwargs.get("随机补充避重缓存", ""))
    settings["连续生成避重缓存"] = str(kwargs.get("连续生成避重缓存", setting_defaults.get("连续生成避重缓存", "")))
    settings["运行时随机保护标签"] = str(kwargs.get("运行时随机保护标签", setting_defaults.get("运行时随机保护标签", "")))
    settings["运行时随机预览令牌"] = str(kwargs.get("运行时随机预览令牌", setting_defaults.get("运行时随机预览令牌", "")))
    settings["系统提示词覆盖"] = _resolve_system_prompt_override(
        kwargs.get("系统提示词覆盖"),
        setting_defaults.get("系统提示词覆盖", ""),
    )
    settings["最大生成token"] = safe_int(kwargs.get("最大生成token", 1800), 1800, 128, 8192)
    settings["温度"] = safe_float(kwargs.get("温度", 0.75), 0.75, 0.0, 2.0)
    settings["top_p"] = safe_float(kwargs.get("top_p", 0.9), 0.9, 0.0, 1.0)
    settings["top_k"] = safe_int(kwargs.get("top_k", 40), 40, 0, 200)
    settings["重复惩罚"] = safe_float(kwargs.get("重复惩罚", 1.05), 1.05, 0.5, 2.0)
    settings["频率惩罚"] = safe_float(kwargs.get("频率惩罚", 0.0), 0.0, 0.0, 2.0)
    settings["存在惩罚"] = safe_float(kwargs.get("存在惩罚", 0.0), 0.0, 0.0, 2.0)
    settings["seed"] = safe_int(kwargs.get("seed", 0), 0, 0, _SEED_MAX)
    settings["输出think块"] = _coerce_bool(
        kwargs.get("输出think块", setting_defaults.get("输出think块", False)),
        bool(setting_defaults.get("输出think块", False)),
    )
    settings["qwen模型"] = kwargs.get("qwen模型")
    settings["unique_id"] = _clean_bounded_text_field(
        kwargs.get("unique_id") or kwargs.get("id") or "",
        256,
    ).strip()
    settings["extra_pnginfo"] = kwargs.get("extra_pnginfo")

    string_limits = {
        "系统提示词覆盖": _SYSTEM_PROMPT_MAX_CHARS,
        "标签块编排JSON": _TAG_BLOCK_JSON_MAX_CHARS,
        "连续生成避重缓存": _SYSTEM_PROMPT_MAX_CHARS,
    }
    for name, value in list(settings.items()):
        if isinstance(value, str):
            settings[name] = _clean_bounded_text_field(value, string_limits.get(name, _SETTING_TEXT_MAX_CHARS))

    selected, custom_tags, normalization_notes = normalize_inference_state(selected, custom_tags, settings)
    selected = _normalize_selected_tags(selected, group_slot_limits)
    custom_tags = _normalize_custom_tags(custom_tags)
    external_notes = _coerce_note_list(kwargs.get("推理纠偏说明", []))
    settings["推理纠偏说明"] = _coerce_note_list([*external_notes, *normalization_notes])

    all_tags = collect_all_tags(selected, custom_tags)
    return selected, custom_tags, settings, "、".join(all_tags)
