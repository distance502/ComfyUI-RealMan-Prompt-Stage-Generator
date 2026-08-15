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
_ACTION_CONTRACT_FIELDS = ("selector_action", "action", "adult_action_style")
_ADULT_PAIR_MARKERS = ("成年情侣", "成熟夫妇", "男女配对")
_MALE_ROLE_MARKERS = ("成年男性", "成熟男性", "男人", "男性")
_FEMALE_ROLE_MARKERS = ("成年女性", "成熟女性", "女人", "女性")
_PENETRATION_MARKERS = ("插入", "性交")
_EXPLICIT_ACTION_PRIORITY = (
    "相互口部刺激",
    "相互手部刺激",
    "成人道具阴道插入",
    "成人道具肛门插入",
    "成人道具刺激外阴",
    "成人道具刺激阴茎",
    "伴侣辅助成人道具",
    "阴茎口部刺激",
    "外阴口部刺激",
    "阴茎手部刺激",
    "外阴手部刺激",
    "肛交",
    "口交",
    "自慰",
    "性交",
    "插入",
)
_EXPLICIT_RESULT_MARKERS = ("女性刺激潮吹结果", "男性刺激射精结果", "受控体液结果", "潮吹", "射精", "体液")
_EXPLICIT_RESULT_ALIASES = {
    "女性刺激潮吹结果": "潮吹",
    "男性刺激射精结果": "射精",
    "受控体液结果": "体液",
}
_EXPLICIT_RESULT_TYPES = {
    "潮吹": "female_stimulation_squirt",
    "射精": "male_stimulation_ejaculation",
    "体液": "controlled_fluid",
}
_RESULT_SOURCE_FIELDS = (
    "explicit_terms",
    "workspace_custom_tags",
    "trigger_words",
    "custom_prefix",
    "custom_suffix",
)
_RESULT_CONTACT_POINTS = ("外阴", "阴蒂", "阴道", "肛门", "阴茎", "口部")
_VALUE_FIELDS = (
    "workspace_custom_tags",
    *NSFW_SELECTOR_FIELDS,
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


def _workspace_fields_text(workspace: dict[str, Any], fields: Iterable[str]) -> str:
    values: list[str] = []
    for field in fields:
        raw_value = workspace.get(field, "")
        raw_values = raw_value if isinstance(raw_value, (list, tuple, set)) else [raw_value]
        for value in raw_values:
            text = _clean_text(value, _WORKSPACE_MAX_SCALAR_CHARS)
            if text:
                values.append(text)
    return "，".join(values)


def _has_explicit_vaginal_relation(value: Any) -> bool:
    text = _workspace_fields_text({"value": value}, ("value",))
    return "阴茎" in text and "阴道" in text and any(marker in text for marker in _PENETRATION_MARKERS)


def _has_complete_nsfw_action_contract(value: Any) -> bool:
    text = _workspace_fields_text({"value": value}, ("value",))
    return "成年" in text and "自愿" in text and (
        any(marker in text for marker in ("阴道插入", "肛门插入", "口部刺激", "手部刺激", "自慰"))
        or ("成人道具" in text and any(marker in text for marker in ("刺激", "插入")))
    )


def _is_nsfw_action_contract_source(value: Any) -> bool:
    return _has_complete_nsfw_action_contract(value) or _has_explicit_vaginal_relation(value)


def _first_present_marker(text: str, markers: Iterable[str]) -> str:
    positioned = [(text.find(marker), marker) for marker in markers if marker in text]
    return min(positioned, key=lambda item: item[0], default=(-1, ""))[1]


def _resolve_nsfw_action_contract_base(workspace: dict[str, Any]) -> str:
    """Resolve explicit opt-in fragments into one adult subject-action-object sentence."""

    for field in _ACTION_CONTRACT_FIELDS:
        candidate = _workspace_fields_text(workspace, (field,))
        if _has_complete_nsfw_action_contract(candidate):
            return candidate

    action_text = _workspace_fields_text(workspace, _ACTION_CONTRACT_FIELDS)
    anatomy_text = _workspace_fields_text(workspace, ("anatomy_terms",))
    explicit_text = _workspace_fields_text(workspace, ("explicit_terms",))
    role_text = _workspace_fields_text(
        workspace,
        ("selector_character", "workspace_custom_tags", "trigger_words", "custom_prefix", "custom_suffix"),
    )
    has_adult_pair = any(marker in role_text for marker in _ADULT_PAIR_MARKERS) or (
        any(marker in role_text for marker in _MALE_ROLE_MARKERS)
        and any(marker in role_text for marker in _FEMALE_ROLE_MARKERS)
    )
    has_adult_female_pair = "双成年女性" in role_text
    has_adult_male_pair = "双成年男性" in role_text
    has_any_adult_pair = has_adult_pair or has_adult_female_pair or has_adult_male_pair
    has_adult_female = any(marker in role_text for marker in ("成年女性", "成熟女性"))
    has_adult_male = any(marker in role_text for marker in ("成年男性", "成熟男性"))
    direct_vaginal = _has_explicit_vaginal_relation(action_text)
    direct_anal = "阴茎" in action_text and "肛门" in action_text and any(
        marker in action_text for marker in ("插入", "肛交")
    )
    chosen_explicit = _first_present_marker(explicit_text, _EXPLICIT_ACTION_PRIORITY)

    toy_target = (
        "外阴"
        if chosen_explicit == "成人道具刺激外阴"
        else "阴道"
        if chosen_explicit == "成人道具阴道插入"
        else "肛门"
        if chosen_explicit == "成人道具肛门插入"
        else _first_present_marker(anatomy_text, ("外阴", "阴蒂", "阴道", "肛门", "阴茎"))
    )
    direct_toy = "成人道具" in action_text and any(marker in action_text for marker in ("刺激", "插入"))
    if direct_toy or chosen_explicit in {
        "成人道具阴道插入",
        "成人道具肛门插入",
        "成人道具刺激外阴",
        "成人道具刺激阴茎",
        "伴侣辅助成人道具",
    }:
        if chosen_explicit == "伴侣辅助成人道具" or (direct_toy and has_adult_pair):
            if toy_target in {"外阴", "阴蒂", "阴道"}:
                return (
                    "伴侣辅助成人道具刺激女性: 一名成年伴侣使用成人道具刺激另一名成年女性的外阴与阴蒂; "
                    "双方均为成年人且自愿, 道具持有者、接触点、女性腿部位置与双人轮廓保持清楚"
                )
            if toy_target == "阴茎":
                return (
                    "伴侣辅助成人道具刺激男性: 一名成年伴侣使用成人道具刺激另一名成年男性的阴茎; "
                    "双方均为成年人且自愿, 道具持有者、接触点、男性身体支撑与双人轮廓保持清楚"
                )
        if has_adult_female and chosen_explicit == "成人道具肛门插入":
            return (
                "成年女性成人道具肛门插入: 一名成年女性自愿使用成人道具进行肛门插入; 成年主体自主自愿, "
                "道具方向、接触点、骨盆朝向与四肢支撑保持清楚"
            )
        if has_adult_female and chosen_explicit == "成人道具阴道插入":
            return (
                "成年女性成人道具阴道插入: 一名成年女性自愿使用成人道具进行阴道插入; 成年主体自主自愿, "
                "道具方向、插入接触点、骨盆朝向与四肢支撑保持清楚"
            )
        if has_adult_female and chosen_explicit in {"成人道具刺激外阴", ""} and toy_target in {"外阴", "阴蒂"}:
            return (
                "成年女性成人道具外阴刺激: 一名成年女性使用成人道具刺激自己的外阴与阴蒂; 成年主体自主自愿, "
                "道具握持关系、接触点、腿部位置与完整身体轮廓保持清楚"
            )
        if has_adult_male and toy_target == "阴茎":
            return (
                "成年男性成人道具刺激: 一名成年男性使用成人道具刺激自己的阴茎; 成年主体自主自愿, "
                "道具握持关系、接触点、手臂路径与完整身体轮廓保持清楚"
            )

    if direct_anal or (
        has_adult_pair
        and "阴茎" in anatomy_text
        and "肛门" in anatomy_text
        and chosen_explicit == "肛交"
    ):
        if "侧卧" in action_text:
            return (
                "侧卧肛门插入: 一名成年男性与一名成年女性保持侧卧, 由成年男性以阴茎插入成年女性肛门; "
                "双方均为成年人且自愿, 侧卧朝向、骨盆接触点、腿部交叠与身体轮廓保持清楚"
            )
        return (
            "后方肛门插入: 一名成年男性从后方以阴茎插入一名成年女性肛门; 双方均为成年人且自愿, "
            "前后站位、骨盆接触点、腰背支撑与四肢位置保持清楚"
        )

    if chosen_explicit == "相互口部刺激" and has_any_adult_pair:
        if has_adult_female_pair:
            return (
                "双成年女性相互口部刺激: 两名成年女性以相反身体朝向同时刺激对方的外阴与阴蒂; "
                "双方均为成年人且自愿, 两处口部接触点、头脚方向与四肢支撑保持清楚"
            )
        if has_adult_male_pair:
            return (
                "双成年男性相互口部刺激: 两名成年男性以相反身体朝向同时刺激对方的阴茎; "
                "双方均为成年人且自愿, 两处口部接触点、头脚方向与四肢支撑保持清楚"
            )
        return (
            "双向口部刺激: 两名成年伴侣以相反身体朝向同时进行口部刺激; 双方均为成年人且自愿, "
            "两处口部接触关系、头脚方向、躯干间距与四肢支撑保持清楚"
        )

    if chosen_explicit in {"口交", "阴茎口部刺激", "外阴口部刺激"}:
        oral_target = (
            "阴茎"
            if chosen_explicit == "阴茎口部刺激"
            else "外阴"
            if chosen_explicit == "外阴口部刺激"
            else _first_present_marker(anatomy_text, ("阴茎", "外阴", "阴蒂", "阴道"))
        )
        if oral_target == "阴茎" and (has_adult_pair or has_adult_male_pair):
            if has_adult_male_pair:
                return (
                    "双成年男性单向口部刺激: 一名成年男性以口部刺激另一名成年男性的阴茎; "
                    "双方均为成年人且自愿, 主客体身份、口部接触点、跪坐支撑与双人身体间距保持清楚"
                )
            return (
                "女性对男性口部刺激: 一名成年女性以口部刺激一名成年男性的阴茎; 双方均为成年人且自愿, "
                "头部朝向、口部接触点、跪坐支撑与双人身体间距保持清楚"
            )
        if oral_target and (has_adult_pair or has_adult_female_pair):
            if has_adult_female_pair:
                return (
                    "双成年女性单向口部刺激: 一名成年女性以口部和舌部刺激另一名成年女性的外阴与阴蒂; "
                    "双方均为成年人且自愿, 主客体身份、口部接触点、腿部位置与双人轮廓保持清楚"
                )
            return (
                "男性对女性口部刺激: 一名成年男性以口部和舌部刺激一名成年女性的外阴与阴蒂; "
                "双方均为成年人且自愿, 面部朝向、口部接触点、女性腿部位置与双人轮廓保持清楚"
            )

    if chosen_explicit == "相互手部刺激" and has_any_adult_pair:
        if has_adult_female_pair:
            return (
                "双成年女性相互手部刺激: 两名成年女性分别以手指刺激对方的外阴与阴蒂; "
                "双方均为成年人且自愿, 每只手的归属、两处接触点、双人轮廓与四肢路径保持清楚"
            )
        if has_adult_male_pair:
            return (
                "双成年男性相互手部刺激: 两名成年男性分别以手部刺激对方的阴茎; "
                "双方均为成年人且自愿, 每只手的归属、两处接触点、双人轮廓与四肢路径保持清楚"
            )
        return (
            "双人相互手部刺激: 两名成年伴侣分别以手部刺激对方的私密部位; 双方均为成年人且自愿, "
            "每只手的归属、两处接触点、双人轮廓与四肢路径保持清楚"
        )

    if chosen_explicit == "阴茎手部刺激" and (has_adult_pair or has_adult_male_pair):
        if has_adult_male_pair:
            return (
                "双成年男性单向手部刺激: 一名成年男性以手掌和手指刺激另一名成年男性的阴茎; "
                "双方均为成年人且自愿, 手部归属、接触点、手臂路径与双人身体边界保持清楚"
            )
        return (
            "女性对男性手部刺激: 一名成年女性以手掌和手指刺激一名成年男性的阴茎; "
            "双方均为成年人且自愿, 手部归属、接触点、手臂路径与双人身体边界保持清楚"
        )

    if chosen_explicit == "外阴手部刺激" and (has_adult_pair or has_adult_female_pair):
        if has_adult_female_pair:
            return (
                "双成年女性单向手部刺激: 一名成年女性以手指刺激另一名成年女性的外阴与阴蒂; "
                "双方均为成年人且自愿, 手部归属、指尖接触点、腿部位置与双人身体边界保持清楚"
            )
        return (
            "男性对女性手部刺激: 一名成年男性以手指刺激一名成年女性的外阴与阴蒂; "
            "双方均为成年人且自愿, 手部归属、指尖接触点、腿部位置与双人身体边界保持清楚"
        )

    if chosen_explicit == "自慰":
        if has_adult_female and any(marker in anatomy_text for marker in ("外阴", "阴蒂", "阴道")):
            return (
                "成年女性自慰: 一名成年女性以自己的手指刺激自己的外阴与阴蒂; 成年主体自主自愿, "
                "双手归属、指尖接触点、腿部位置与完整身体轮廓保持清楚"
            )
        if has_adult_male and "阴茎" in anatomy_text:
            return (
                "成年男性自慰: 一名成年男性以自己的手掌刺激自己的阴茎; 成年主体自主自愿, "
                "双手归属、手掌接触点、手臂路径与完整身体轮廓保持清楚"
            )

    legacy_vaginal = (
        has_adult_pair
        and "阴茎" in anatomy_text
        and "阴道" in anatomy_text
        and chosen_explicit in _PENETRATION_MARKERS
    )
    if direct_vaginal or legacy_vaginal:
        if "女上位" in action_text or "跨坐" in action_text:
            return (
                "女上位阴道插入: 一名成年女性跨坐在一名成年男性上方, 由成年男性的阴茎插入成年女性阴道; "
                "双方均为成年人且自愿, 骨盆接触点、跨坐承重、四肢位置与身体朝向保持清楚"
            )
        if any(marker in action_text for marker in ("后方", "从后", "背后")):
            return (
                "后方阴道插入: 一名成年男性从后方以阴茎插入一名成年女性阴道; 双方均为成年人且自愿, "
                "前后站位、骨盆接触点、腰背支撑与四肢位置保持清楚"
            )
        if "侧卧" in action_text:
            return (
                "侧卧阴道插入: 一名成年男性与一名成年女性保持侧卧, 由成年男性以阴茎插入成年女性阴道; "
                "双方均为成年人且自愿, 侧卧朝向、骨盆接触点、腿部交叠与身体轮廓保持清楚"
            )
        return (
            "正面阴道插入: 一名成年男性面对一名成年女性, 以阴茎插入成年女性阴道; 双方均为成年人且自愿, "
            "面对面骨盆接触点、四肢支撑与身体朝向保持清楚"
        )
    return ""


def _ordered_nsfw_result_markers(explicit_text: str) -> list[str]:
    canonical_positions: dict[str, int] = {}
    for marker in _EXPLICIT_RESULT_MARKERS:
        index = explicit_text.find(marker)
        if index < 0:
            continue
        canonical = _EXPLICIT_RESULT_ALIASES.get(marker, marker)
        canonical_positions[canonical] = min(index, canonical_positions.get(canonical, index))
    return [
        marker
        for marker, _ in sorted(canonical_positions.items(), key=lambda item: item[1])
    ]


def _empty_nsfw_result_contract(
    action_contract: str = "",
    *,
    requested_markers: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "enabled": False,
        "requested_markers": list(requested_markers),
        "markers": [],
        "types": [],
        "action_contract": action_contract,
        "contact_points": [],
        "person_count": 0,
        "camera_axis": "",
        "end_state": "",
        "continuity_clause": "",
        "required_anchors": [],
        "text": "",
    }


def _infer_nsfw_result_person_count(action_contract: str) -> int:
    if any(
        marker in action_contract
        for marker in ("双方", "两名", "双成年", "双人", "另一名", "伴侣", "夫妇", "情侣", "男女配对")
    ):
        return 2
    if any(marker in action_contract for marker in ("三名", "三人")):
        return 3
    return 1


def _build_nsfw_result_contract(action_contract: str, explicit_text: str) -> dict[str, Any]:
    requested_markers = _ordered_nsfw_result_markers(explicit_text)
    if not action_contract or not requested_markers:
        return _empty_nsfw_result_contract(
            action_contract,
            requested_markers=requested_markers,
        )

    clauses: list[str] = []
    markers: list[str] = []
    result_types: list[str] = []
    for marker in requested_markers:
        if marker == "潮吹" and any(target in action_contract for target in ("外阴", "阴蒂", "阴道")):
            clauses.append(
                "潮吹仅作为当前女性刺激动作的结果，液体来源、方向与落点受既有接触关系约束，不新增人物或动作分支"
            )
        elif marker == "射精" and "阴茎" in action_contract:
            clauses.append(
                "射精仅作为当前男性刺激动作的结果，体液来源、方向与落点受既有接触关系约束，不改变主客体身份"
            )
        elif marker == "体液":
            clauses.append(
                "其他体液仅出现在当前接触区域与已存在的身体或道具表面，不扩散成新的场景元素"
            )
        else:
            continue
        markers.append(marker)
        result_types.append(_EXPLICIT_RESULT_TYPES[marker])
    if not clauses:
        return _empty_nsfw_result_contract(
            action_contract,
            requested_markers=requested_markers,
        )

    contact_points = [point for point in _RESULT_CONTACT_POINTS if point in action_contract]
    if not contact_points:
        contact_points = ["当前既有接触点"]
    person_count = _infer_nsfw_result_person_count(action_contract)
    contact_text = "、".join(contact_points)
    camera_axis = "沿当前镜头轴线保持不变，不换轴、不跳切"
    continuity_clause = "结果发生前后保持原有姿态、接触点、人物数量与镜头轴线，结束状态能够连续追踪"
    end_state = (
        f"动作结束后保持原有姿态与空间关系，结果只停留在{contact_text}，"
        "不新增人物、地点、道具或动作分支"
    )
    fixed_state_clause = (
        f"固定接触点为{contact_text}，人物数量固定为{person_count}名，{camera_axis}；{end_state}"
    )
    clauses.extend((continuity_clause, fixed_state_clause))
    text = f"动作结果阶段: {'; '.join(clauses)}"
    required_anchors = [
        f"固定接触点为{contact_text}",
        f"人物数量固定为{person_count}名",
        "沿当前镜头轴线保持不变",
        "结束状态能够连续追踪",
    ]
    return {
        "enabled": True,
        "requested_markers": requested_markers,
        "markers": markers,
        "types": result_types,
        "action_contract": action_contract,
        "contact_points": contact_points,
        "person_count": person_count,
        "camera_axis": camera_axis,
        "end_state": end_state,
        "continuity_clause": continuity_clause,
        "required_anchors": required_anchors,
        "text": text,
    }


def _append_nsfw_result_contract(action_contract: str, explicit_text: str) -> str:
    if not action_contract:
        return ""
    result_contract = _build_nsfw_result_contract(action_contract, explicit_text)
    result_text = str(result_contract.get("text") or "").strip()
    return f"{action_contract}；{result_text}" if result_text else action_contract


def _nsfw_result_source_text(workspace: dict[str, Any]) -> str:
    return _workspace_fields_text(workspace, _RESULT_SOURCE_FIELDS)


def _is_standalone_nsfw_result_term(value: Any) -> bool:
    text = _clean_text(value)
    return bool(text and text in {*_EXPLICIT_RESULT_MARKERS, *_EXPLICIT_RESULT_ALIASES.values()})


def resolve_nsfw_action_contract(workspace: dict[str, Any]) -> str:
    """Resolve an adult action and fold compatible result terms into the same contract."""

    action_contract = _resolve_nsfw_action_contract_base(workspace)
    explicit_text = _nsfw_result_source_text(workspace)
    return _append_nsfw_result_contract(action_contract, explicit_text)


def _iter_workspace_terms(workspace: dict[str, Any]) -> Iterable[str]:
    action_contract = resolve_nsfw_action_contract(workspace)

    def iter_terms(value: Any, *, selector: bool = False) -> Iterable[str]:
        source = _iter_selector_terms(value) if selector else _iter_split_terms(value)
        for term in source:
            if action_contract and _is_standalone_nsfw_result_term(term):
                continue
            yield term

    trigger_words = workspace.get("trigger_words", [])
    if isinstance(trigger_words, (list, tuple, set)):
        for item in trigger_words:
            yield from iter_terms(item)
    else:
        yield from iter_terms(trigger_words)

    action_contract_emitted = False
    for field in _VALUE_FIELDS:
        if action_contract and field in {"anatomy_terms", "explicit_terms"}:
            continue
        raw_value = workspace.get(field, "")
        if action_contract and field in _ACTION_CONTRACT_FIELDS and _is_nsfw_action_contract_source(raw_value):
            if not action_contract_emitted:
                yield action_contract
                action_contract_emitted = True
            continue
        if field in NSFW_SELECTOR_FIELDS:
            yield from iter_terms(raw_value, selector=True)
        elif isinstance(raw_value, (list, tuple, set)):
            for item in raw_value:
                yield from iter_terms(item)
        else:
            yield from iter_terms(raw_value)
        if action_contract and field == "action" and not action_contract_emitted:
            yield action_contract
            action_contract_emitted = True

    if action_contract and not action_contract_emitted:
        yield action_contract


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
    action_contract_base = _resolve_nsfw_action_contract_base(effective_workspace)
    result_contract = _build_nsfw_result_contract(
        action_contract_base,
        _nsfw_result_source_text(effective_workspace),
    )
    action_contract = _append_nsfw_result_contract(
        action_contract_base,
        _nsfw_result_source_text(effective_workspace),
    )
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
        for term in _iter_split_terms(workspace.get(field, "")):
            if action_contract and _is_standalone_nsfw_result_term(term):
                continue
            append_custom_tag(term)

    # Content choices define the scene; generic finish tags should never crowd
    # them out of compact prompt summaries.
    for tag in _resolve_quality_tags(effective_workspace):
        append_custom_tag(tag)

    return {
        "selected": selected,
        "custom_tags": custom_tags,
        "negative_prompt": resolve_nsfw_negative_prompt(workspace),
        "negative": _resolve_negative_branch(workspace),
        "result_contract": result_contract,
    }
