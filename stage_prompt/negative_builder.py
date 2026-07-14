# -*- coding: utf-8 -*-
"""Negative prompt generation helpers."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable


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
}


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
    separator: str = "、",
) -> str:
    language = str(settings.get("提示词语言", "纯中文"))
    use_english_negative = language in {"纯英文", "英文提示词+中文说明"}
    adult = bool(set(tags) & adult_tag_keywords or set(tags) & adult_low_cover_tags)
    neg: list[str] = []
    template_key = _template_negative_key(settings)
    if use_english_negative:
        neg.extend(template_negative_en.get(template_key, []))
        if adult:
            neg.extend(adult_negative_en)
            neg.extend(low_cover_negative_en)
            neg.extend(composition_negative_en)
    else:
        neg.extend(template_negative_zh.get(template_key, []))
        if adult:
            neg.extend(adult_negative_zh)
            neg.extend(low_cover_negative_zh)
            neg.extend(composition_negative_zh)
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
        separator=separator,
    )
