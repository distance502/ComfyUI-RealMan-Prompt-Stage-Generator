# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from collections import OrderedDict
from typing import Any

try:
    from .narrative import (
        build_narrative_plan,
        render_narrative_prompt,
        resolve_visual_layout_mode,
        summarize_narrative_plan,
    )
except Exception:  # pragma: no cover - direct file loading in focused tests
    from stage_prompt_narrative_test import (  # type: ignore
        build_narrative_plan,
        render_narrative_prompt,
        resolve_visual_layout_mode,
        summarize_narrative_plan,
    )

try:  # Reuse the main prompt vocabulary when the plugin package is loaded normally.
    from .prompt_builder import _translate_prompt_fragment as _translate_shared_prompt_fragment
except Exception:  # pragma: no cover - direct file loading in focused tests
    try:
        from stage_prompt_prompt_builder_test import _translate_prompt_fragment as _translate_shared_prompt_fragment  # type: ignore
    except Exception:  # pragma: no cover - standalone fallback
        _translate_shared_prompt_fragment = None


MAX_BLOCKS = 40
MAX_TAGS_PER_BLOCK = 24
MAX_EXTRA_REQUIREMENT_LENGTH = 1200

_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_ENGLISH_GROUP_FALLBACKS = {
    "主体": "selected subject detail",
    "画面风格": "selected visual style",
    "成人向表达": "selected mature styling detail",
    "服装造型": "selected outfit detail",
    "场景背景": "selected environment detail",
    "构图视角": "selected camera framing detail",
    "动作姿态": "selected pose detail",
    "光影氛围": "selected lighting detail",
    "道具世界观": "selected narrative prop detail",
    "技术画质": "selected image quality detail",
    "自定义补充": "user-provided visual detail",
}

_INTERNAL_REQUIREMENT_MARKERS = (
    "skill前置上下文",
    "模型调用上下文",
    "角色设定图内部策略",
    "推理纠偏说明",
    "系统提示词覆盖",
    "待整理提示词正文",
    "thinking process",
    "analyze the request",
    "output requirements",
)


GROUP_ROLE_HINTS_ZH = {
    "主体": "主体身份、年龄气质、发型、体态和表情",
    "画面风格": "媒介风格、审美方向和成片质感",
    "成人向表达": "成熟氛围、造型尺度和情绪张力",
    "服装造型": "服装结构、材质、配饰和轮廓关系",
    "场景背景": "环境空间、前中后景和叙事地点",
    "构图视角": "镜头距离、视角、画面比例和主体占比",
    "动作姿态": "动作重心、肢体关系和视线方向",
    "光影氛围": "主光、辅光、轮廓光、色调和空气感",
    "道具世界观": "道具、职业线索、世界观符号和叙事锚点",
    "技术画质": "清晰度、材质纹理、完成度和画质控制",
    "自定义补充": "用户补充的特殊要求",
}

GROUP_ROLE_HINTS_EN = {
    "主体": "subject identity, age impression, hairstyle, body language and expression",
    "画面风格": "medium, visual style, finish and aesthetic direction",
    "成人向表达": "mature mood, styling intensity and emotional tension",
    "服装造型": "outfit structure, fabric, accessories and silhouette",
    "场景背景": "environment, spatial depth and narrative location",
    "构图视角": "camera distance, viewpoint, framing and subject scale",
    "动作姿态": "pose weight, limb relationship and gaze direction",
    "光影氛围": "key light, fill, rim light, color mood and atmosphere",
    "道具世界观": "props, role clues, worldbuilding symbols and narrative anchors",
    "技术画质": "clarity, material detail, finish and quality control",
    "自定义补充": "user-provided custom direction",
}

NOISE_TERMS = {
    "无",
    "中",
    "强",
    "弱",
    "开",
    "关",
    "true",
    "false",
    "none",
    "null",
    "undefined",
    "nan",
}

GROUP_ALIASES = {
    "自定义": "自定义补充",
    "自定义补充": "自定义补充",
    "主体": "主体",
    "主体类型": "主体",
    "画面风格": "画面风格",
    "成人向表达": "成人向表达",
    "服装造型": "服装造型",
    "场景背景": "场景背景",
    "构图视角": "构图视角",
    "动作姿态": "动作姿态",
    "光影氛围": "光影氛围",
    "道具世界观": "道具世界观",
    "技术画质": "技术画质",
}


VARIATION_FOCUS_ZH = (
    "主体轮廓与环境层次",
    "动作重心与视线方向",
    "明暗结构与轮廓分离",
    "前中后景的空间关系",
    "材质纹理与边缘细节",
)

VARIATION_TREATMENT_ZH = (
    "清晰的主次关系",
    "紧凑而稳定的视觉节奏",
    "平衡的空间留白",
    "有序的层次递进",
)

VARIATION_FOCUS_EN = (
    "the subject silhouette and environmental depth",
    "pose weight and gaze direction",
    "light-shadow structure and edge separation",
    "foreground, midground and background spacing",
    "material texture and edge detail",
)

VARIATION_TREATMENT_EN = (
    "a clear visual hierarchy",
    "a compact and stable visual rhythm",
    "balanced negative space",
    "an orderly progression of depth",
)


def _clean_text(value: Any, *, max_length: int = 1200) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f]+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:max_length].strip()


def _dedupe(items: list[Any], *, limit: int = MAX_TAGS_PER_BLOCK) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = _clean_text(item, max_length=80)
        if not text or text == "无" or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _dedupe_meaningful(items: list[Any], *, limit: int = MAX_TAGS_PER_BLOCK) -> list[str]:
    out: list[str] = []
    for item in _dedupe(items, limit=limit * 2):
        key = item.strip().lower()
        if key in NOISE_TERMS:
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out


def _join_terms(items: list[str], *, sep: str = "、", fallback: str = "") -> str:
    clean = _dedupe_meaningful(items, limit=16)
    return sep.join(clean) if clean else fallback


def _append_sentence(parts: list[str], sentence: str, *, punctuation: str = "。") -> None:
    text = _clean_text(sentence, max_length=900).rstrip("。.;；")
    if text:
        parts.append(text + punctuation)


def _english_fallback(group: str, index: int = 0) -> str:
    base = _ENGLISH_GROUP_FALLBACKS.get(_canonical_group(group), "selected visual detail")
    return f"{base} {index}" if index > 0 else base


def _localize_english_text(value: Any, *, fallback: str) -> str:
    text = _clean_text(value, max_length=900)
    if not text:
        return ""
    if not _CJK_PATTERN.search(text):
        return text
    translated = ""
    if callable(_translate_shared_prompt_fragment):
        try:
            translated = str(_translate_shared_prompt_fragment(text) or "").strip()
        except Exception:
            translated = ""
    return translated if translated and not _CJK_PATTERN.search(translated) else fallback


def _localize_english_terms(items: list[Any], group: str) -> list[str]:
    localized: list[str] = []
    unknown_index = 0
    for item in _dedupe_meaningful(items):
        fallback = _english_fallback(group, unknown_index + 1)
        translated = _localize_english_text(item, fallback=fallback)
        if translated == fallback:
            unknown_index += 1
        if translated and translated not in localized:
            localized.append(translated)
    return localized


def _localize_blocks_for_english(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    localized: list[dict[str, Any]] = []
    text_index = 0
    for block in blocks:
        if not isinstance(block, dict):
            continue
        next_block = dict(block)
        group = _canonical_group(next_block.get("group") or next_block.get("label")) or "自定义补充"
        if next_block.get("type") == "text":
            text_index += 1
            next_block["text"] = _localize_english_text(
                next_block.get("text", ""),
                fallback=_english_fallback("自定义补充", text_index),
            )
        else:
            raw_tags = next_block.get("tags") if isinstance(next_block.get("tags"), list) else []
            next_block["tags"] = _localize_english_terms(raw_tags, group)
        next_block["label"] = _ENGLISH_GROUP_FALLBACKS.get(group, "visual detail")
        localized.append(next_block)
    return localized


def _normalize_block(block: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(block, dict):
        return None
    block_type = _clean_text(block.get("type"), max_length=24) or "tag_group"
    if block_type not in {"tag_group", "text"}:
        block_type = "tag_group"
    group = _clean_text(block.get("group"), max_length=40)
    label = _clean_text(block.get("label"), max_length=60) or group or ("文字块" if block_type == "text" else f"标签块{index + 1}")
    tags = _dedupe(block.get("tags") if isinstance(block.get("tags"), list) else [])
    text = _clean_text(block.get("text"), max_length=1200)
    if block_type == "text":
        if not text:
            return None
        tags = []
    elif not tags and not text:
        return None
    block_id = _clean_text(block.get("id"), max_length=80) or f"block_{index + 1}"
    return {
        "id": block_id,
        "type": block_type,
        "group": group,
        "label": label,
        "tags": tags,
        "text": text,
        "locked": bool(block.get("locked", False)),
    }


def parse_tag_block_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        raw_text = raw.strip()
        if not raw_text:
            return {"version": 1, "enabled": False, "blocks": []}
        try:
            data = json.loads(raw_text)
        except Exception:
            return {"version": 1, "enabled": False, "blocks": []}
    elif isinstance(raw, dict):
        data = dict(raw)
    else:
        return {"version": 1, "enabled": False, "blocks": []}

    if not isinstance(data, dict):
        return {"version": 1, "enabled": False, "blocks": []}

    raw_blocks = data.get("blocks") if isinstance(data.get("blocks"), list) else []
    blocks: list[dict[str, Any]] = []
    for index, block in enumerate(raw_blocks[:MAX_BLOCKS]):
        normalized = _normalize_block(block, index)
        if normalized:
            blocks.append(normalized)
    try:
        version = int(data.get("version") or 1)
    except (TypeError, ValueError, OverflowError):
        version = 1
    if version <= 0:
        version = 1
    return {
        "version": version,
        "enabled": bool(data.get("enabled", bool(blocks))),
        "blocks": blocks,
    }


def _clean_extra_requirement(value: Any) -> str:
    text = _clean_text(value, max_length=MAX_EXTRA_REQUIREMENT_LENGTH)
    if not text:
        return ""
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        lowered = line.casefold()
        if not line or any(marker in lowered for marker in _INTERNAL_REQUIREMENT_MARKERS):
            continue
        key = re.sub(r"\s+", "", line).casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        lines.append(line)
    return "；".join(lines).strip("；;，,。 ")


def _append_extra_requirement_block(blocks: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, Any]]:
    extra = _clean_extra_requirement(settings.get("额外要求", ""))
    if not extra:
        return blocks
    extra_key = re.sub(r"\s+", "", extra).casefold()
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        existing = _clean_extra_requirement(block.get("text", ""))
        if existing and re.sub(r"\s+", "", existing).casefold() == extra_key:
            return blocks
    return [
        *blocks,
        {
            "id": "extra_requirement",
            "type": "text",
            "group": "自定义补充",
            "label": "用户补充",
            "tags": [],
            "text": extra,
            "locked": True,
            "_source": "extra_requirement",
        },
    ]


def summarize_tag_block_payload(payload: dict[str, Any]) -> str:
    blocks = payload.get("blocks") if isinstance(payload, dict) else []
    parts: list[str] = []
    for block in blocks if isinstance(blocks, list) else []:
        if not isinstance(block, dict):
            continue
        label = _clean_text(block.get("label"), max_length=30) or _clean_text(block.get("group"), max_length=30) or "标签块"
        if block.get("type") == "text":
            body = _clean_text(block.get("text"), max_length=70)
        else:
            body = "、".join(_dedupe(block.get("tags") if isinstance(block.get("tags"), list) else [], limit=6))
        if body:
            parts.append(f"{label}: {body}")
    return " -> ".join(parts[:12])


def _format_block_phrase_zh(block: dict[str, Any]) -> str:
    label = _clean_text(block.get("label"), max_length=40) or _clean_text(block.get("group"), max_length=40) or "标签块"
    if block.get("type") == "text":
        text = _clean_text(block.get("text"), max_length=900)
        return f"用户插入说明为：{text}"
    group = _clean_text(block.get("group"), max_length=40)
    tags = _dedupe(block.get("tags") if isinstance(block.get("tags"), list) else [])
    if not tags:
        return ""
    hint = GROUP_ROLE_HINTS_ZH.get(group, label)
    return f"【{label}】负责{hint}，使用 {('、'.join(tags))} 作为这一段的核心素材"


def _format_block_phrase_en(block: dict[str, Any]) -> str:
    label = _clean_text(block.get("label"), max_length=40) or _clean_text(block.get("group"), max_length=40) or "block"
    if block.get("type") == "text":
        text = _clean_text(block.get("text"), max_length=900)
        return f"the user text block adds: {text}"
    group = _clean_text(block.get("group"), max_length=40)
    tags = _dedupe(block.get("tags") if isinstance(block.get("tags"), list) else [])
    if not tags:
        return ""
    hint = GROUP_ROLE_HINTS_EN.get(group, label)
    return f"the [{label}] block controls {hint}, using {', '.join(tags)} as its main material"


def _fallback_block_from_state(selected: OrderedDict[str, list[str]], custom_tags: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for group, tags in selected.items():
        clean_tags = _dedupe(list(tags or []))
        if clean_tags:
            blocks.append({"id": f"group_{group}", "type": "tag_group", "group": str(group), "label": str(group), "tags": clean_tags, "text": "", "locked": False})
    clean_custom = _dedupe(list(custom_tags or []))
    if clean_custom:
        blocks.append({"id": "custom_tags", "type": "tag_group", "group": "自定义补充", "label": "自定义", "tags": clean_custom, "text": "", "locked": False})
    return blocks


def _canonical_group(value: Any) -> str:
    group = _clean_text(value, max_length=40)
    return GROUP_ALIASES.get(group, group)


def _reconcile_blocks_with_state(
    blocks: list[dict[str, Any]],
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
) -> list[dict[str, Any]]:
    """Keep block order while treating the normalized state as the content boundary."""
    if not selected:
        return [dict(block) for block in blocks]

    authoritative: OrderedDict[str, list[str]] = OrderedDict()
    for raw_group, raw_tags in selected.items():
        group = _canonical_group(raw_group)
        authoritative.setdefault(group, [])
        authoritative[group] = _dedupe_meaningful([*authoritative[group], *(raw_tags or [])])
    authoritative["自定义补充"] = _dedupe_meaningful(custom_tags)

    allowed_terms = {
        tag
        for tags in authoritative.values()
        for tag in tags
    }
    stale_terms: set[str] = set()
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") == "text":
            continue
        group = _canonical_group(block.get("group") or block.get("label"))
        raw_tags = _dedupe_meaningful(block.get("tags") if isinstance(block.get("tags"), list) else [])
        if group in authoritative:
            stale_terms.update(tag for tag in raw_tags if tag not in authoritative[group])
        else:
            stale_terms.update(tag for tag in raw_tags if tag not in allowed_terms)

    used_by_group: dict[str, set[str]] = {}
    used_unknown_terms: set[str] = set()
    reconciled: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        next_block = dict(block)
        if next_block.get("type") == "text":
            text = _clean_text(next_block.get("text"), max_length=900)
            if not text or any(term in text for term in stale_terms if len(term) >= 2):
                continue
            next_block["text"] = text
            reconciled.append(next_block)
            continue

        group = _canonical_group(next_block.get("group") or next_block.get("label")) or "自定义补充"
        raw_tags = _dedupe_meaningful(next_block.get("tags") if isinstance(next_block.get("tags"), list) else [])
        if group in authoritative:
            group_tags = authoritative[group]
            used = used_by_group.setdefault(group, set())
            remaining = [tag for tag in group_tags if tag not in used]
            retained = [tag for tag in raw_tags if tag in group_tags and tag not in used]
            if next_block.get("locked"):
                next_tags = remaining
            elif retained:
                next_tags = retained
            elif not used:
                next_tags = remaining
            else:
                next_tags = []
            used.update(next_tags)
        else:
            next_tags = [tag for tag in raw_tags if tag in allowed_terms and tag not in used_unknown_terms]
            used_unknown_terms.update(next_tags)
        if not next_tags:
            continue
        next_block["group"] = group
        next_block["tags"] = next_tags
        reconciled.append(next_block)

    # Normalization may add safety/style anchors in groups that were absent from
    # the saved block layout. Append only those still-unused authoritative tags
    # so block order remains stable without dropping the normalized state.
    for group, group_tags in authoritative.items():
        used = used_by_group.setdefault(group, set())
        remaining = [tag for tag in group_tags if tag not in used]
        if not remaining:
            continue
        reconciled.append(
            {
                "id": f"normalized_{group}",
                "type": "tag_group",
                "group": group,
                "label": group,
                "tags": remaining,
                "text": "",
                "locked": True,
            }
        )
        used.update(remaining)
    return reconciled


def _collect_block_material(blocks: list[dict[str, Any]]) -> tuple[OrderedDict[str, list[str]], list[str], list[tuple[str, str, list[str] | str]]]:
    by_group: OrderedDict[str, list[str]] = OrderedDict()
    text_blocks: list[str] = []
    ordered: list[tuple[str, str, list[str] | str]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text = _clean_text(block.get("text"), max_length=900)
            if text and text.lower() not in NOISE_TERMS:
                text_blocks.append(text)
                if block.get("_source") != "extra_requirement":
                    ordered.append(("text", _clean_text(block.get("label"), max_length=40) or "文字块", text))
            continue
        group = GROUP_ALIASES.get(_clean_text(block.get("group"), max_length=40), _clean_text(block.get("group"), max_length=40) or _clean_text(block.get("label"), max_length=40) or "自定义补充")
        tags = _dedupe_meaningful(block.get("tags") if isinstance(block.get("tags"), list) else [])
        if not tags:
            continue
        by_group.setdefault(group, [])
        by_group[group].extend(tags)
        ordered.append(("tag_group", group, tags))
    for group, tags in list(by_group.items()):
        by_group[group] = _dedupe_meaningful(tags)
        if not by_group[group]:
            del by_group[group]
    return by_group, text_blocks, ordered


def _find_text_subject(text_blocks: list[str]) -> str:
    for text in text_blocks:
        clean = _clean_text(text, max_length=160)
        if clean and any(token in clean.lower() for token in ("女人", "男人", "人物", "角色", "女孩", "男孩", "主体", "woman", "man", "person", "character", "subject")):
            return clean
    return ""


def _variation_sentence(language: str, variation_index: int) -> str:
    if variation_index <= 0:
        return ""
    pair_index = variation_index - 1
    if language == "纯英文":
        focus = VARIATION_FOCUS_EN[pair_index % len(VARIATION_FOCUS_EN)]
        treatment = VARIATION_TREATMENT_EN[(pair_index // len(VARIATION_FOCUS_EN)) % len(VARIATION_TREATMENT_EN)]
        return f"Composition emphasizes {focus}, organized through {treatment}"
    focus = VARIATION_FOCUS_ZH[pair_index % len(VARIATION_FOCUS_ZH)]
    treatment = VARIATION_TREATMENT_ZH[(pair_index // len(VARIATION_FOCUS_ZH)) % len(VARIATION_TREATMENT_ZH)]
    return f"构图重点放在{focus}，以{treatment}组织画面"


def _record_narrative_plan(
    settings: dict[str, Any],
    plan: dict[str, Any],
    *,
    variation_index: int,
    english: bool,
) -> None:
    plans = settings.setdefault("全局剧情规划", [])
    index = max(0, int(variation_index or 0))
    while len(plans) <= index:
        plans.append("")
    plans[index] = summarize_narrative_plan(plan, english=english)


def _ordered_zh_clauses(ordered: list[tuple[str, str, list[str] | str]]) -> list[str]:
    clauses: list[str] = []
    for kind, group, payload in ordered:
        if kind == "text":
            text = _clean_text(payload, max_length=180)
            if text:
                if any(token in text for token in ("女人", "男人", "人物", "角色", "女孩", "男孩", "主体")):
                    clauses.append(f"主体补充为{text}")
                else:
                    clauses.append(f"画面补充为{text}")
            continue
        tags = _dedupe_meaningful(payload if isinstance(payload, list) else [])
        if not tags:
            continue
        text = "、".join(tags)
        if group == "画面风格":
            continue
        if group == "主体":
            clauses.append(f"主体设定为{text}")
        elif group == "场景背景":
            clauses.append(f"场景先落在{text}")
        elif group == "构图视角":
            clauses.append(f"镜头采用{text}")
        elif group == "动作姿态":
            clauses.append(f"动作围绕{text}")
        elif group == "光影氛围":
            clauses.append(f"光影铺设{text}的空气感")
        elif group == "服装造型":
            clauses.append(f"服装造型围绕{text}")
        elif group == "成人向表达":
            clauses.append(f"成熟氛围保留{text}")
        elif group == "道具世界观":
            clauses.append(f"叙事道具包含{text}")
        elif group == "技术画质":
            clauses.append(f"画质目标保持{text}")
        elif group == "自定义补充":
            clauses.append(f"补充细节融入{text}")
    return clauses


def _build_tag_block_prompt_zh(blocks: list[dict[str, Any]], settings: dict[str, Any], *, style_track: str = "", subject_type: str = "", template_style: str = "", variation_index: int = 0) -> str:
    by_group, text_blocks, ordered = _collect_block_material(blocks)
    non_person = str(subject_type).strip() == "非人物主体"
    layout_mode = resolve_visual_layout_mode(
        [tag for group_tags in by_group.values() for tag in group_tags] + list(text_blocks),
        settings,
        non_person=non_person,
    )
    settings["画面结构模式解析结果"] = layout_mode
    detail = str(settings.get("详细度", "标准") or "标准")
    style_text = _join_terms(by_group.get("画面风格", []), fallback=_clean_text(style_track or template_style or settings.get("模板风格") or "完整画面", max_length=80))
    subject_text = _join_terms(by_group.get("主体", []), fallback=_find_text_subject(text_blocks) or ("非人物主体" if str(subject_type).strip() == "非人物主体" else "人物主体"))
    inserted_text = _join_terms([text for text in text_blocks if text != subject_text], fallback="")
    adult_text = _join_terms(by_group.get("成人向表达", []))
    outfit_text = _join_terms(by_group.get("服装造型", []))
    scene_text = _join_terms(by_group.get("场景背景", []))
    composition_text = _join_terms(by_group.get("构图视角", []), fallback="全景全身、人物完整入镜" if str(subject_type).strip() != "非人物主体" else "全景、主体完整入镜")
    action_text = _join_terms(by_group.get("动作姿态", []))
    light_text = _join_terms(by_group.get("光影氛围", []))
    prop_text = _join_terms(by_group.get("道具世界观", []))
    quality_text = _join_terms(by_group.get("技术画质", []), fallback="高细节、清晰对焦、材质纹理稳定")
    custom_text = _join_terms(by_group.get("自定义补充", []))

    ordered_clauses = _ordered_zh_clauses(ordered)
    variation_sentence = _variation_sentence("纯中文", variation_index)
    ordered_lead = "，".join(ordered_clauses)
    anchors = {
        "lead": f"{style_text}作为整体视觉方向，{ordered_lead}" if ordered_lead else style_text,
        "subject": subject_text,
        "scene": scene_text,
        "composition": composition_text,
        "action": action_text,
        "adult": adult_text,
        "outfit": outfit_text,
        "lighting": light_text,
        "props": prop_text,
        "custom": "、".join(value for value in (inserted_text, custom_text) if value),
        "residual": "；".join([*ordered_clauses, variation_sentence] if variation_sentence else ordered_clauses),
        "quality": quality_text,
        "style_track": style_track,
        "layout_mode": layout_mode,
    }
    plan = build_narrative_plan(
        anchors,
        output_index=variation_index,
        output_count=max(1, int(settings.get("生成数量", 1) or 1)),
        recent_history=[str(item).strip() for item in settings.get("最近提示词指纹", []) if str(item).strip()],
        seed=int(settings.get("运行时随机有效种子", 0) or settings.get("seed", 0) or 0),
    )
    _record_narrative_plan(settings, plan, variation_index=variation_index, english=False)
    return render_narrative_prompt(
        anchors,
        plan,
        language="纯中文",
        detail_level=detail,
        non_person=non_person,
        adult_mode=bool(adult_text),
        layout_mode=layout_mode,
    )


def _ordered_en_clauses(ordered: list[tuple[str, str, list[str] | str]]) -> list[str]:
    clauses: list[str] = []
    for kind, group, payload in ordered:
        if kind == "text":
            text = _clean_text(payload, max_length=180)
            if text:
                clauses.append(f"the composition also preserves {text}")
            continue
        tags = _dedupe_meaningful(payload if isinstance(payload, list) else [])
        if not tags or group == "画面风格":
            continue
        text = ", ".join(tags)
        if group == "主体":
            clauses.append(f"the subject is {text}")
        elif group == "场景背景":
            clauses.append(f"the scene is set in {text}")
        elif group == "构图视角":
            clauses.append(f"the camera uses {text}")
        elif group == "动作姿态":
            clauses.append(f"the pose follows {text}")
        elif group == "光影氛围":
            clauses.append(f"the lighting carries {text}")
        elif group == "服装造型":
            clauses.append(f"the outfit follows {text}")
        elif group == "成人向表达":
            clauses.append(f"the mature mood retains {text}")
        elif group == "道具世界观":
            clauses.append(f"narrative props include {text}")
        elif group == "技术画质":
            clauses.append(f"image quality targets {text}")
        elif group == "自定义补充":
            clauses.append(f"supporting detail includes {text}")
    return clauses


def _build_tag_block_prompt_en(blocks: list[dict[str, Any]], settings: dict[str, Any], *, style_track: str = "", subject_type: str = "", template_style: str = "", variation_index: int = 0) -> str:
    source_blocks = blocks
    blocks = _localize_blocks_for_english(source_blocks)
    by_group, text_blocks, ordered = _collect_block_material(blocks)
    source_by_group, source_text_blocks, _source_ordered = _collect_block_material(source_blocks)
    non_person = str(subject_type).strip() == "非人物主体"
    layout_mode = resolve_visual_layout_mode(
        [tag for group_tags in source_by_group.values() for tag in group_tags] + list(source_text_blocks),
        settings,
        non_person=non_person,
    )
    settings["画面结构模式解析结果"] = layout_mode
    detail = str(settings.get("详细度", "标准") or "标准")
    style_fallback = _localize_english_text(
        style_track or template_style or settings.get("模板风格") or "coherent finished image",
        fallback="coherent finished image",
    )
    style_text = _join_terms(by_group.get("画面风格", []), sep=", ", fallback=style_fallback)
    subject_text = _join_terms(by_group.get("主体", []), sep=", ", fallback=_find_text_subject(text_blocks) or ("non-human subject" if str(subject_type).strip() == "非人物主体" else "main character"))
    inserted_text = _join_terms([text for text in text_blocks if text != subject_text], sep="; ")
    adult_text = _join_terms(by_group.get("成人向表达", []), sep=", ")
    scene_text = _join_terms(by_group.get("场景背景", []), sep=", ")
    composition_text = _join_terms(by_group.get("构图视角", []), sep=", ", fallback="wide full-body shot, entire subject in frame")
    light_text = _join_terms(by_group.get("光影氛围", []), sep=", ")
    action_text = _join_terms(by_group.get("动作姿态", []), sep=", ")
    outfit_text = _join_terms(by_group.get("服装造型", []), sep=", ")
    prop_text = _join_terms(by_group.get("道具世界观", []), sep=", ")
    quality_text = _join_terms(by_group.get("技术画质", []), sep=", ", fallback="high detail, clean focus, stable material texture")
    custom_text = _join_terms(by_group.get("自定义补充", []), sep=", ")

    ordered_clauses = _ordered_en_clauses(ordered)
    variation_sentence = _variation_sentence("纯英文", variation_index)
    ordered_lead = "; ".join(ordered_clauses)
    article = "An" if style_text[:1].casefold() in {"a", "e", "i", "o", "u"} else "A"
    anchors = {
        "lead": (
            f"{article} {style_text} image follows one coherent visual sequence: {ordered_lead}"
            if ordered_lead
            else f"{article} {style_text} image"
        ),
        "subject": subject_text,
        "scene": scene_text,
        "composition": composition_text,
        "action": action_text,
        "adult": adult_text,
        "outfit": outfit_text,
        "lighting": light_text,
        "props": prop_text,
        "custom": "; ".join(value for value in (inserted_text, custom_text) if value),
        "residual": "; ".join([*ordered_clauses, variation_sentence] if variation_sentence else ordered_clauses),
        "quality": quality_text,
        "style_track": style_track,
        "layout_mode": layout_mode,
    }
    plan = build_narrative_plan(
        anchors,
        output_index=variation_index,
        output_count=max(1, int(settings.get("生成数量", 1) or 1)),
        recent_history=[str(item).strip() for item in settings.get("最近提示词指纹", []) if str(item).strip()],
        seed=int(settings.get("运行时随机有效种子", 0) or settings.get("seed", 0) or 0),
    )
    _record_narrative_plan(settings, plan, variation_index=variation_index, english=True)
    return render_narrative_prompt(
        anchors,
        plan,
        language="纯英文",
        detail_level=detail,
        non_person=non_person,
        adult_mode=bool(adult_text),
        layout_mode=layout_mode,
    )


def build_tag_block_prompt_list(
    payload: dict[str, Any],
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    grouped_summary: str = "",
    style_track: str = "",
    subject_type: str = "",
    template_style: str = "",
    generation_count: int = 1,
) -> list[str]:
    normalized = parse_tag_block_payload(payload)
    raw_blocks = list(normalized.get("blocks") or [])
    blocks = _reconcile_blocks_with_state(raw_blocks, selected, custom_tags) if raw_blocks else _fallback_block_from_state(selected, custom_tags)
    blocks = _append_extra_requirement_block(blocks, settings)
    count = max(1, min(20, int(generation_count or 1)))
    language = str(settings.get("提示词语言", "纯中文") or "纯中文")
    if not blocks:
        base = _clean_text(grouped_summary, max_length=1000) or "完整画面，主体明确，场景清晰，高细节"
        if language == "纯英文":
            base = _localize_english_text(
                base,
                fallback="coherent finished image with a clear subject, readable environment and high detail",
            )
        prompts: list[str] = []
        for index in range(count):
            variation = _variation_sentence("纯英文" if language == "纯英文" else "纯中文", index)
            prompts.append(f"{base}{(' ' if language == '纯英文' else '。') + variation + '.' if variation and language == '纯英文' else ('。' + variation + '。' if variation else '')}".strip())
        return prompts

    style_text = _clean_text(style_track or template_style or settings.get("模板风格") or "自动", max_length=60)
    subject_text = _clean_text(subject_type or settings.get("主体类型") or "自动", max_length=60)

    if language == "纯英文":
        return [
            _build_tag_block_prompt_en(blocks, settings, style_track=style_text, subject_type=subject_text, template_style=template_style, variation_index=index)
            for index in range(count)
        ]

    if language == "英文提示词+中文说明":
        return [
            _build_tag_block_prompt_en(blocks, settings, style_track=style_text, subject_type=subject_text, template_style=template_style, variation_index=index)
            + "\n中文说明："
            + _build_tag_block_prompt_zh(blocks, settings, style_track=style_text, subject_type=subject_text, template_style=template_style, variation_index=index)
            for index in range(count)
        ]
    return [
        _build_tag_block_prompt_zh(blocks, settings, style_track=style_text, subject_type=subject_text, template_style=template_style, variation_index=index)
        for index in range(count)
    ]
