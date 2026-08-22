# -*- coding: utf-8 -*-
"""Negative prompt generation helpers."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable
import re

try:
    from .narrative import (
        VISUAL_LAYOUT_MULTI_SUBJECT,
        VISUAL_LAYOUT_MULTI_VIEW,
        VISUAL_LAYOUT_SINGLE_PERSON,
        resolve_visual_layout_mode,
    )
except Exception:  # pragma: no cover - direct file loading in focused tests
    from stage_prompt_narrative_test import (  # type: ignore
        VISUAL_LAYOUT_MULTI_SUBJECT,
        VISUAL_LAYOUT_MULTI_VIEW,
        VISUAL_LAYOUT_SINGLE_PERSON,
        resolve_visual_layout_mode,
    )


_NEGATIVE_FRAGMENT_TRANSLATION_MAP = {
    "过度锐化": "over-sharpening",
    "硬光打脸": "harsh facial lighting",
    "法令纹过深": "overly deep nasolabial folds",
    "眼周纹理过重": "overly heavy eye wrinkles",
    "文字": "text",
    "水印": "watermark",
    "logo": "logo",
    "铭文": "inscriptions",
    "符文": "runes",
    "字样": "lettering",
}
_TEMPLATE_NEGATIVE_BASE_STYLE = {
    "商业摄影": "真实感",
    "时尚编辑": "真实感",
    "电影写实": "真实感",
    "私房写实": "真实感",
    "复古动画": "插画感",
    "东方赛博": "CG感",
    "硬表面科幻": "CG感",
    "国风电影": "古风",
    "武侠电影": "古风",
    "暗黑奇幻": "神话感",
    "奇幻风格": "神话感",
    "西方奇幻": "神话感",
    "高等奇幻": "神话感",
    "剑与魔法": "神话感",
    "哥特奇幻": "神话感",
    "黑暗童话": "神话感",
    "精灵幻想": "神话感",
    "梦幻奇境": "神话感",
    "日式奇幻动画": "插画感",
    "漆原智志画风": "插画感",
    "结城信辉画风": "插画感",
    "童话绘本": "插画感",
    "魔幻油画": "插画感",
    "奇幻概念设计": "CG感",
    "史诗奇幻海报": "CG感",
}

# Structural guardrails should survive downstream truncation before aesthetic
# suppressors do.  Matching is intentionally language-agnostic so the same
# JSON contract works for Chinese and English prompt channels.
_NEGATIVE_CORE_PATTERNS = (
    re.compile(
        r"duplicate|clone|repeated|extra\s+(?:head|face|person|body|finger)|\bdouble\b|"
        r"same\s+(?:person|face)|split[- ]?screen|diptych|triptych|collage|storyboard|"
        r"comic\s+panel|contact\s+sheet|tiling|picture[- ]?in[- ]?picture|multi[- ]?scene|"
        r"text|watermark|logo|lettering|caption|subtitle|inscription|rune|"
        r"deformed|bad\s+anatomy|missing\s+(?:limb|arm|leg|hand|head)|extra\s+(?:limb|arm|leg|finger)|"
        r"重复|复制|克隆|同一人物|重复脸|重复头部|额外头部|额外肢体|多余手指|手指错误|"
        r"分屏|拼贴|故事板|漫画分格|联系表|平铺|画中画|多场景|文字|水印|logo|字样|铭文|符文|"
        r"畸形|解剖错误|身体结构错误|缺失(?:手臂|腿|肢体|头部)|额外(?:手臂|腿|肢体)",
        flags=re.IGNORECASE,
    ),
)


def classify_negative_prompt(negative_prompt: str) -> dict[str, list[str]]:
    """Split a legacy negative string into structural core and optional terms.

    The returned terms preserve their original order and spelling.  This is a
    metadata-only operation; callers can continue passing the unchanged joined
    string to existing image nodes.
    """

    source = str(negative_prompt or "").strip()
    if not source:
        return {"negative_core": [], "negative_optional": []}
    terms = [part.strip() for part in re.split(r"[、,，;；\n]+", source) if part.strip()]
    core: list[str] = []
    optional: list[str] = []
    seen_core: set[str] = set()
    seen_optional: set[str] = set()
    for term in terms:
        key = re.sub(r"\s+", "", term).casefold()
        if not key:
            continue
        is_core = any(pattern.search(term) for pattern in _NEGATIVE_CORE_PATTERNS)
        bucket = core if is_core else optional
        seen = seen_core if is_core else seen_optional
        if key in seen:
            continue
        seen.add(key)
        bucket.append(term)
    return {"negative_core": core, "negative_optional": optional}


def _localize_negative_terms(terms: list[str], *, use_english: bool) -> list[str]:
    if not use_english:
        return list(terms)
    return [_NEGATIVE_FRAGMENT_TRANSLATION_MAP.get(str(term).strip(), str(term).strip()) for term in terms if str(term).strip()]


def _template_negative_key(settings: dict[str, Any]) -> str:
    style = str(settings.get("模板风格", "真实感") or "真实感").strip() or "真实感"
    return _TEMPLATE_NEGATIVE_BASE_STYLE.get(style, style)


def build_negative_prompt_from_tags(
    tags: list[str],
    settings: dict[str, Any],
    *,
    uniq: Callable[[list[str]], list[str]],
    adult_tag_keywords: set[str],
    adult_low_cover_tags: set[str],
    template_negative_zh: dict[str, list[str]],
    template_negative_en: dict[str, list[str]],
    adult_negative_zh: list[str],
    adult_negative_en: list[str],
    low_cover_negative_zh: list[str],
    low_cover_negative_en: list[str],
    composition_negative_zh: list[str],
    composition_negative_en: list[str],
    soft_skin_terms: list[str],
    text_artifact_terms: list[str],
    single_frame_negative_zh: list[str] | None = None,
    single_frame_negative_en: list[str] | None = None,
    duplicate_subject_negative_zh: list[str] | None = None,
    duplicate_subject_negative_en: list[str] | None = None,
    single_subject_negative_zh: list[str] | None = None,
    single_subject_negative_en: list[str] | None = None,
    multi_subject_negative_zh: list[str] | None = None,
    multi_subject_negative_en: list[str] | None = None,
    multi_view_negative_zh: list[str] | None = None,
    multi_view_negative_en: list[str] | None = None,
    separator: str = "、",
) -> str:
    language = str(settings.get("提示词语言", "纯中文"))
    use_english_negative = language in {"纯英文", "英文提示词+中文说明"}
    adult = bool(set(tags) & adult_tag_keywords or set(tags) & adult_low_cover_tags)
    neg: list[str] = []
    layout_mode = resolve_visual_layout_mode(tags, settings)
    settings["画面结构模式解析结果"] = layout_mode
    template_key = _template_negative_key(settings)
    if use_english_negative:
        neg.extend(template_negative_en.get(template_key, []))
        if adult:
            neg.extend(adult_negative_en)
            neg.extend(low_cover_negative_en)
            neg.extend(composition_negative_en)
        if layout_mode == VISUAL_LAYOUT_MULTI_VIEW:
            neg.extend(multi_view_negative_en or [])
        else:
            neg.extend(single_frame_negative_en or [])
            if layout_mode in {VISUAL_LAYOUT_SINGLE_PERSON, VISUAL_LAYOUT_MULTI_SUBJECT}:
                neg.extend(duplicate_subject_negative_en or [])
            if layout_mode == VISUAL_LAYOUT_SINGLE_PERSON:
                neg.extend(single_subject_negative_en or [])
            elif layout_mode == VISUAL_LAYOUT_MULTI_SUBJECT:
                neg.extend(multi_subject_negative_en or [])
    else:
        neg.extend(template_negative_zh.get(template_key, []))
        if adult:
            neg.extend(adult_negative_zh)
            neg.extend(low_cover_negative_zh)
            neg.extend(composition_negative_zh)
        if layout_mode == VISUAL_LAYOUT_MULTI_VIEW:
            neg.extend(multi_view_negative_zh or [])
        else:
            neg.extend(single_frame_negative_zh or [])
            if layout_mode in {VISUAL_LAYOUT_SINGLE_PERSON, VISUAL_LAYOUT_MULTI_SUBJECT}:
                neg.extend(duplicate_subject_negative_zh or [])
            if layout_mode == VISUAL_LAYOUT_SINGLE_PERSON:
                neg.extend(single_subject_negative_zh or [])
            elif layout_mode == VISUAL_LAYOUT_MULTI_SUBJECT:
                neg.extend(multi_subject_negative_zh or [])
    if bool(settings.get("优先柔和肤质")):
        neg.extend(_localize_negative_terms(soft_skin_terms, use_english=use_english_negative))
    if bool(settings.get("抑制文字伪影")):
        neg.extend(_localize_negative_terms(text_artifact_terms, use_english=use_english_negative))
    return separator.join(uniq(neg))


def build_negative_prompt_from_state(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    uniq: Callable[[list[str]], list[str]],
    adult_tag_keywords: set[str],
    adult_low_cover_tags: set[str],
    template_negative_zh: dict[str, list[str]],
    template_negative_en: dict[str, list[str]],
    adult_negative_zh: list[str],
    adult_negative_en: list[str],
    low_cover_negative_zh: list[str],
    low_cover_negative_en: list[str],
    composition_negative_zh: list[str],
    composition_negative_en: list[str],
    soft_skin_terms: list[str],
    text_artifact_terms: list[str],
    single_frame_negative_zh: list[str] | None = None,
    single_frame_negative_en: list[str] | None = None,
    duplicate_subject_negative_zh: list[str] | None = None,
    duplicate_subject_negative_en: list[str] | None = None,
    single_subject_negative_zh: list[str] | None = None,
    single_subject_negative_en: list[str] | None = None,
    multi_subject_negative_zh: list[str] | None = None,
    multi_subject_negative_en: list[str] | None = None,
    multi_view_negative_zh: list[str] | None = None,
    multi_view_negative_en: list[str] | None = None,
    separator: str = "、",
) -> str:
    tags = [tag for group_tags in selected.values() for tag in group_tags] + list(custom_tags)
    return build_negative_prompt_from_tags(
        tags,
        settings,
        uniq=uniq,
        adult_tag_keywords=adult_tag_keywords,
        adult_low_cover_tags=adult_low_cover_tags,
        template_negative_zh=template_negative_zh,
        template_negative_en=template_negative_en,
        adult_negative_zh=adult_negative_zh,
        adult_negative_en=adult_negative_en,
        low_cover_negative_zh=low_cover_negative_zh,
        low_cover_negative_en=low_cover_negative_en,
        composition_negative_zh=composition_negative_zh,
        composition_negative_en=composition_negative_en,
        soft_skin_terms=soft_skin_terms,
        text_artifact_terms=text_artifact_terms,
        single_frame_negative_zh=single_frame_negative_zh,
        single_frame_negative_en=single_frame_negative_en,
        duplicate_subject_negative_zh=duplicate_subject_negative_zh,
        duplicate_subject_negative_en=duplicate_subject_negative_en,
        single_subject_negative_zh=single_subject_negative_zh,
        single_subject_negative_en=single_subject_negative_en,
        multi_subject_negative_zh=multi_subject_negative_zh,
        multi_subject_negative_en=multi_subject_negative_en,
        multi_view_negative_zh=multi_view_negative_zh,
        multi_view_negative_en=multi_view_negative_en,
        separator=separator,
    )
