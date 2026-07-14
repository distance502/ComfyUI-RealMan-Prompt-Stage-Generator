# -*- coding: utf-8 -*-
"""Isolated character-sheet prompt strategy for stage prompt generation."""

from __future__ import annotations

import re
from typing import Any


CHARACTER_SHEET_STRATEGY_NOTE = "角色设定图策略：启用时将当前节点提示词重构为多视角角色设定展示；停用时不介入全局生成。"
CHARACTER_SHEET_PROMPT_BRIEF = (
    "角色设定图，多视角角色展示，头像特写，正面全身，侧面全身，背面全身，"
    "同一角色一致，服装结构完整，发型轮廓清晰，材质层次明确，背景跟随当前素材，无文字标注"
)
CHARACTER_SHEET_PROMPT_BRIEF_EN = (
    "character sheet, multi-view character turnaround, headshot close-up, "
    "front full-body view, side full-body view, back full-body view, "
    "consistent character identity across every view, complete outfit construction, "
    "clear hairstyle structure, readable material layers, concept-aware background, no text labels"
)
CHARACTER_SHEET_INTERNAL_POLICY = (
    "角色设定图内部策略：只把参考图可见角色特征、当前节点标签和用户补充整理成画面素材；"
    "参考图模式下以可见角色的脸型、发型、服装结构、主配色和材质逻辑优先，节点标签只作为风格、场景、光影和气氛补充；"
    "不要把策略说明、Thinking Process、任务分析、输出要求或规则文本写进最终提示词。"
)

_META_FRAGMENT_MARKERS = (
    "thinking process",
    "analyze the request",
    "analyze the reference image",
    "output requirements",
    "specific goal",
    "constraints",
    "task:",
    "role:",
    "no json",
    "do not",
    "don't",
    "here is",
    "ai painting reference",
    "ai绘画参考图反推助手",
    "角色设定图策略",
    "当前全局提示词上下文",
    "参考图反推上下文",
    "生成目标",
    "输出要求",
    "一致性要求",
    "构图要求",
    "规则",
    "不要输出",
    "不要把",
    "必须",
    "json",
)

_VISUAL_LABEL_RE = re.compile(
    r"^\s*(?:\d+\.\s*)?(?:\*\*)?"
    r"(?:Subject|Hair|Clothing|Outer|Inner|Pose|Lighting|Background|Style|Quality|Composition|Palette|"
    r"主体|发型|服装|外套|内搭|姿态|光影|背景|风格|画质|构图|配色|材质|气质|年龄)"
    r"(?:\*\*)?\s*[:：]\s*",
    flags=re.IGNORECASE,
)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _is_meta_fragment(text: str) -> bool:
    lowered = str(text or "").casefold()
    return any(marker in lowered for marker in _META_FRAGMENT_MARKERS)


def _strip_reasoning_preamble(text: str) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(r"<think\b[^>]*>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(
        r"(?is)thinking\s+process\s*:.*?(?=(?:\*\*)?\s*(?:analyze\s+the\s+reference\s+image|subject|hair|clothing|主体|发型|服装))",
        "",
        cleaned,
    )
    return cleaned


def _clean_visual_context(value: Any, *, max_fragments: int = 28, max_chars: int = 1400) -> str:
    """Keep drawable content while dropping strategy, analysis and prompt-rule text."""

    text = _strip_reasoning_preamble(_clean_text(value))
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("当前全局提示词上下文：", "").replace("参考图反推上下文：", "")
    text = text.replace("当前全局提示词上下文:", "").replace("参考图反推上下文:", "")
    raw_fragments = re.split(r"\n+|\s+\*\s+|(?<=。)|(?<=；)|(?<=;)", text)
    fragments: list[str] = []
    seen: set[str] = set()
    for raw in raw_fragments:
        item = raw.strip().strip("-*#> `")
        item = item.replace("**", "").strip()
        item = _VISUAL_LABEL_RE.sub("", item).strip()
        item = re.sub(r"\s+", " ", item).strip("，,。；;:： ")
        if not item or _is_meta_fragment(item):
            continue
        if len(item) > 240:
            item = item[:240].rstrip("，,。；;:： ") + "…"
        key = re.sub(r"\s+", "", item).casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        fragments.append(item)
        if len(fragments) >= max_fragments:
            break
    merged = "；".join(fragments).strip("；;，,。 ")
    if len(merged) > max_chars:
        merged = merged[:max_chars].rstrip("；;，,。 ") + "…"
    return merged


def _merge_unique_lines(*parts: Any) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for raw in parts:
        text = _clean_text(raw)
        if not text:
            continue
        for line in text.splitlines():
            item = line.strip()
            if not item or item in seen:
                continue
            seen.add(item)
            lines.append(item)
    return "\n".join(lines)


def build_character_sheet_instruction(*, has_reference_image: bool, source_text: str = "", reference_text: str = "") -> str:
    """Build a drawable, non-locking seed for character reference sheets.

    This text is fed to smart matching, so it must stay close to visible/material
    content and avoid internal rules that could leak into the final prompt.
    """
    mode_line = (
        "参考单人图模式，参考图可见角色特征优先，节点标签作为风格、场景、光影和气氛补充"
        if has_reference_image
        else "纯提示词模式，使用当前节点标签和用户补充生成角色设定展示"
    )
    source_line = _clean_visual_context(source_text, max_fragments=16)
    reference_line = _clean_visual_context(reference_text, max_fragments=18)
    context_lines = []
    if source_line:
        context_lines.append(source_line)
    if reference_line:
        context_lines.append(reference_line)
    return _merge_unique_lines(
        mode_line,
        *context_lines,
        CHARACTER_SHEET_PROMPT_BRIEF,
    )


def apply_character_sheet_strategy(
    settings: dict[str, Any],
    *,
    source_text: str = "",
    reference_text: str = "",
    has_reference_image: bool = False,
    merge_requirement_text,
) -> bool:
    """Apply character-sheet strategy to settings only when enabled."""
    if not bool(settings.get("图片反推生成", False)):
        return False
    settings["图片反推模式"] = "角色设定图"
    settings["主体类型"] = "人物角色"
    settings["案例输出结构"] = "案例长段版"
    settings["详细度"] = "详细"
    settings["输出模式"] = "完整结果"
    settings["优先柔和肤质"] = True
    settings["抑制文字伪影"] = True
    settings["智能文本匹配"] = True
    settings["角色设定图内部策略"] = CHARACTER_SHEET_INTERNAL_POLICY
    clean_user_text = _clean_visual_context(settings.get("智能文本输入"), max_fragments=10, max_chars=700)
    clean_extra = _clean_visual_context(settings.get("额外要求"), max_fragments=10, max_chars=700)
    clean_reference = _clean_visual_context(reference_text, max_fragments=18, max_chars=1200)
    instruction = build_character_sheet_instruction(
        has_reference_image=has_reference_image,
        source_text=source_text,
        reference_text=reference_text,
    )
    seed_text = merge_requirement_text(clean_user_text, clean_extra, instruction)
    settings["智能文本输入"] = seed_text
    if str(settings.get("提示词语言", "纯中文") or "纯中文").strip() == "纯英文":
        english_context = [
            text
            for text in (clean_extra, clean_reference)
            if text and not re.search(r"[\u4e00-\u9fff]", text)
        ]
        settings["额外要求"] = merge_requirement_text(*english_context, CHARACTER_SHEET_PROMPT_BRIEF_EN)
    else:
        settings["额外要求"] = merge_requirement_text(clean_extra, clean_reference, CHARACTER_SHEET_PROMPT_BRIEF)
    notes = [str(note).strip() for note in settings.get("推理纠偏说明", []) if str(note).strip()]
    if CHARACTER_SHEET_STRATEGY_NOTE not in notes:
        notes.append(CHARACTER_SHEET_STRATEGY_NOTE)
    settings["推理纠偏说明"] = notes
    return True
