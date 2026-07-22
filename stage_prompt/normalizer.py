# -*- coding: utf-8 -*-
"""Normalization helpers for stage prompt generation."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable

try:  # Keep direct file loading in tests working when the package context is absent.
    from .skills import apply_stage_prompt_skills, resolve_base_template_style
except Exception:  # pragma: no cover - exercised by direct import tests
    from stage_prompt_skills_test import apply_stage_prompt_skills, resolve_base_template_style  # type: ignore

try:
    from .narrative import VISUAL_LAYOUT_MULTI_VIEW, resolve_visual_layout_mode
except Exception:  # pragma: no cover - exercised by direct import tests
    from stage_prompt_narrative_test import VISUAL_LAYOUT_MULTI_VIEW, resolve_visual_layout_mode  # type: ignore


_SINGLE_FRAME_TAG_REWRITES = {
    "从全身到半身，先交代服装轮廓再收束表情": "单一中景全身关系，服装轮廓与表情同时可读",
    "环绕式展示服装轮廓，保持单一主体比例": "三分之二侧面全身定格，服装轮廓与主体比例稳定",
    "镜前反射切换，主体与镜像关系清楚": "镜前斜侧定格，真实主体为主，镜像边界清楚",
    "低机位上摇至面部，强调腿部到肩颈线条": "低机位全身定格，腿部到肩颈比例连贯",
    "微距掠过材质，随后回到人物整体": "中近景定格，材质细节与人物整体同时可读",
    "快速推进至局部细节，随后回到全身关系": "中景全身定格，局部细节与完整身体关系同时可读",
    "360度环绕，捕捉全身轮廓与服装材质": "三分之二侧面全身定格，轮廓与服装材质清楚",
    "低角度慢扫，从脚踝到腰线，节奏渐强": "低机位全身定格，脚踝到腰线比例自然",
    "动态放大后拉远，强调身体曲线与空间": "中景全身定格，身体曲线与空间同时可读",
    "动态局部镜头，随后回到主体整体": "中景主体整体，局部材质仍然清楚可读",
    "快速场景切换，挑逗氛围定场": "单一场景情绪峰值定格，氛围集中",
    "从空间建立镜头缓慢推近，在视线相遇时停止": "环境中景定格，视线相遇成为唯一动作峰值",
    "沿人物移动方向侧向跟随，最后停在手部接触点": "侧向中景定格，移动方向与手部接触点同时可读",
    "先拍道具线索再移焦到人物回应，形成清楚因果": "道具位于前景线索位，人物回应保持唯一焦点",
    "从镜面反射平稳摇向真实主体，不产生人物复制": "镜后斜侧定格，真实主体为主且反射边界清楚",
    "低速环绕半圈，交代双人距离变化后回到眼平视角": "三分之二眼平定格，双人距离与脸部同时可读",
    "从门外长焦观察再缓慢靠近，保持私密但不窥视的距离": "门外长焦定格，保持私密但不窥视的观看距离",
    "跟随衣摆与脚步上移至表情，动作方向连续": "低机位全身定格，衣摆、脚步与表情在同一时刻可读",
    "亲密动作结束后轻微拉远，让环境承担开放结尾": "环境中景定格，亲密动作余势与开放结尾同框",
}


def normalize_inference_state(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    collect_all_tags: Callable[[OrderedDict[str, list[str]], list[str]], list[str]],
    remove_tag_from_state: Callable[[OrderedDict[str, list[str]], list[str], str], None],
    append_tag_to_state: Callable[[OrderedDict[str, list[str]], list[str], str], None],
    uniq: Callable[[list[str]], list[str]],
    context: dict[str, Any],
) -> tuple[OrderedDict[str, list[str]], list[str], list[str]]:
    normalized_selected = OrderedDict((name, uniq(list(tags))) for name, tags in selected.items())
    normalized_custom = uniq(list(custom_tags))
    notes: list[str] = []

    def tag_set() -> set[str]:
        return set(collect_all_tags(normalized_selected, normalized_custom))

    def base_template_style() -> str:
        style = str(settings.get("模板风格", "自动") or "自动").strip()
        return resolve_base_template_style(style, default="自动")

    tags = tag_set()
    ancient_modern_conflicts = set(context.get("ancient_modern_conflicts", set()))
    if settings.get("模板风格") == "自动" and "古风" in tags and tags & ancient_modern_conflicts:
        settings["模板风格"] = "真实感"
        notes.append("世界观纠偏：检测到古风与现代西装/现代场景同现，自动转入真实感轨道。")

    tags = tag_set()
    if base_template_style() == "古风":
        ancient_scene_conflict_tags = set(context.get("ancient_scene_conflict_tags", set()))
        removed_ancient_scene_conflicts = [tag for tag in list(tags) if tag in ancient_scene_conflict_tags]
        for scene_tag in removed_ancient_scene_conflicts:
            remove_tag_from_state(normalized_selected, normalized_custom, scene_tag)
        if removed_ancient_scene_conflicts:
            notes.append(f"古风场景纠偏：移除现代/西式场景 {'、'.join(removed_ancient_scene_conflicts)}。")

        tags = tag_set()
        ancient_style_clothing_conflicts = set(context.get("ancient_style_clothing_conflicts", set()))
        removed_ancient_clothing_conflicts = [tag for tag in list(tags) if tag in ancient_style_clothing_conflicts]
        for clothing_tag in removed_ancient_clothing_conflicts:
            remove_tag_from_state(normalized_selected, normalized_custom, clothing_tag)
        if removed_ancient_clothing_conflicts:
            notes.append(f"古风服装纠偏：移除现代服装冲突 {'、'.join(removed_ancient_clothing_conflicts)}。")

        tags = tag_set()
        ancient_clothing_tags = set(context.get("ancient_clothing_tags", set()))
        if not (tags & ancient_clothing_tags):
            append_tag_to_state(normalized_selected, normalized_custom, "汉服")
            notes.append("古风服装补锚：缺少明确朝代服装，自动补入“汉服”。")

        tags = tag_set()
        if {"宫殿", "回廊"} & tags and "古风建筑" not in tags:
            append_tag_to_state(normalized_selected, normalized_custom, "古风建筑")
            notes.append("古风场景补锚：宫殿/回廊语义偏泛，补入“古风建筑”防止西式宫廷漂移。")

    tags = tag_set()
    humanoid_fantasy_map: dict[str, str] = dict(context.get("humanoid_fantasy_map", {}))
    human_identity_tags = set(context.get("human_identity_tags", set()))
    for source_tag, target_tag in humanoid_fantasy_map.items():
        if source_tag in tags and tags & human_identity_tags:
            remove_tag_from_state(normalized_selected, normalized_custom, source_tag)
            append_tag_to_state(normalized_selected, normalized_custom, target_tag)
            notes.append(f"角色纠偏：{source_tag}与人物身份并存，改写为更稳定的人形奇幻标签“{target_tag}”。")

    tags = tag_set()
    sacred_scene_tags = set(context.get("sacred_scene_tags", set()))
    private_scene_tags = set(context.get("private_scene_tags", set()))
    urban_rain_scene_tags = set(context.get("urban_rain_scene_tags", set()))
    ambiguous_adult_tags = set(context.get("ambiguous_adult_tags", set()))
    scene_family_tags = {
        "sacred": tags & sacred_scene_tags,
        "private": tags & private_scene_tags,
        "urban": tags & urban_rain_scene_tags,
    }
    active_families = [name for name, family_tags in scene_family_tags.items() if family_tags]
    if len(active_families) > 1:
        chosen_family = ""
        if scene_family_tags["sacred"] and (
            base_template_style() in {"古风", "神话感", "真实感"} or {"压抑", "局部照明", "钨丝灯实景光"} & tags
        ):
            chosen_family = "sacred"
        elif scene_family_tags["private"] and (ambiguous_adult_tags & tags):
            chosen_family = "private"
        elif scene_family_tags["urban"]:
            chosen_family = "urban"
        else:
            chosen_family = active_families[0]
        removed_scenes: list[str] = []
        for family_name, family_tags in scene_family_tags.items():
            if family_name == chosen_family:
                continue
            for scene_tag in list(family_tags):
                remove_tag_from_state(normalized_selected, normalized_custom, scene_tag)
                removed_scenes.append(scene_tag)
        if removed_scenes:
            kept_scene = "、".join(scene_family_tags[chosen_family]) or chosen_family
            notes.append(f"场景收敛：保留 {kept_scene} 轨道，移除冲突场景 {'、'.join(removed_scenes)}。")

    tags = tag_set()
    half_body_shot_tags = set(context.get("half_body_shot_tags", set()))
    full_body_motion_conflicts = set(context.get("full_body_motion_conflicts", set()))
    half_body_hits = [tag for tag in half_body_shot_tags if tag in tags]
    full_body_action_hits = [tag for tag in full_body_motion_conflicts if tag in tags]
    if half_body_hits and len(full_body_action_hits) >= 2:
        if str(settings.get("随机主题池", "自动") or "自动").strip() == "自动":
            removed_actions: list[str] = []
            for action_tag in list(full_body_action_hits):
                remove_tag_from_state(normalized_selected, normalized_custom, action_tag)
                removed_actions.append(action_tag)
            if removed_actions:
                notes.append(f"景别优先：保留半身镜头，移除冲突动作 {'、'.join(removed_actions[:3])}。")
            tags = tag_set()
            half_body_hits = [tag for tag in half_body_shot_tags if tag in tags]
            full_body_action_hits = [tag for tag in full_body_motion_conflicts if tag in tags]
        else:
            for shot_tag in half_body_hits:
                remove_tag_from_state(normalized_selected, normalized_custom, shot_tag)
            append_tag_to_state(normalized_selected, normalized_custom, "中景")
            notes.append(f"景别修正：半身镜头与 {'、'.join(full_body_action_hits[:3])} 冲突，自动调整为中景。")

    tags = tag_set()
    subject_type = str(settings.get("主体类型解析结果", "") or settings.get("主体类型", "自动") or "自动").strip()
    layout_mode = resolve_visual_layout_mode(
        collect_all_tags(normalized_selected, normalized_custom),
        settings,
        non_person=subject_type == "非人物主体",
    )
    settings["画面结构模式解析结果"] = layout_mode
    if "纵向叙事分镜" in tags and layout_mode != VISUAL_LAYOUT_MULTI_VIEW:
        remove_tag_from_state(normalized_selected, normalized_custom, "纵向叙事分镜")
        append_tag_to_state(normalized_selected, normalized_custom, "海报主视觉")
        notes.append("构图修正：单张图语境下将“纵向叙事分镜”收敛为“海报主视觉”。")

    if layout_mode != VISUAL_LAYOUT_MULTI_VIEW:
        rewritten_motion_tags: list[str] = []
        for source_tag, target_tag in _SINGLE_FRAME_TAG_REWRITES.items():
            if source_tag not in tag_set():
                continue
            remove_tag_from_state(normalized_selected, normalized_custom, source_tag)
            append_tag_to_state(normalized_selected, normalized_custom, target_tag)
            rewritten_motion_tags.append(source_tag)
        if rewritten_motion_tags:
            notes.append(
                "单帧镜头收敛：将带时间顺序的运镜改为同一决定性时刻的静态构图，避免上下重复与人物复制："
                + "、".join(rewritten_motion_tags[:6])
                + ("等" if len(rewritten_motion_tags) > 6 else "")
                + "。"
            )

    tags = tag_set()
    strong_identity_tags = set(context.get("strong_identity_tags", set()))
    casual_conflict_clothing = set(context.get("casual_conflict_clothing", set()))
    strong_identity_hits = tags & strong_identity_tags
    if strong_identity_hits and base_template_style() in {"古风", "神话感"}:
        removed_clothing = [tag for tag in list(tags) if tag in casual_conflict_clothing]
        for clothing_tag in removed_clothing:
            remove_tag_from_state(normalized_selected, normalized_custom, clothing_tag)
        if removed_clothing:
            notes.append(f"服装纠偏：强设定身份下移除日常服装冲突 {'、'.join(removed_clothing)}。")

    apply_stage_prompt_skills(
        normalized_selected,
        normalized_custom,
        settings,
        notes,
        phase="early_normalize",
        collect_all_tags=collect_all_tags,
        remove_tag_from_state=remove_tag_from_state,
        append_tag_to_state=append_tag_to_state,
        uniq=uniq,
        context=context,
    )

    tags = tag_set()
    clothing_core_tags = set(context.get("clothing_core_tags", set()))
    ancient_clothing_tags = set(context.get("ancient_clothing_tags", set()))
    modern_formal_clothing_tags = set(context.get("modern_formal_clothing_tags", set()))
    intimate_clothing_tags = set(context.get("intimate_clothing_tags", set()))
    if base_template_style() == "真实感" and str(settings.get("标签反推模式", "") or "").strip() != "成人向成熟":
        clothing_hits = tags & clothing_core_tags
        if clothing_hits & modern_formal_clothing_tags and clothing_hits & intimate_clothing_tags:
            removed_private_clothing = [tag for tag in clothing_hits if tag in intimate_clothing_tags]
            if (ambiguous_adult_tags & tags) and "双排扣西装" in clothing_hits:
                removed_private_clothing = [tag for tag in removed_private_clothing if tag != "露背礼服"]
            for clothing_tag in removed_private_clothing:
                remove_tag_from_state(normalized_selected, normalized_custom, clothing_tag)
            if removed_private_clothing:
                notes.append(f"服装收敛：正式服装与私密服装并存，移除 {'、'.join(removed_private_clothing)}。")
        elif clothing_hits & ancient_clothing_tags and clothing_hits & modern_formal_clothing_tags:
            removed_ancient_clothing = [tag for tag in clothing_hits if tag in ancient_clothing_tags]
            for clothing_tag in removed_ancient_clothing:
                remove_tag_from_state(normalized_selected, normalized_custom, clothing_tag)
            if removed_ancient_clothing:
                notes.append(f"服装收敛：真实感轨道下保留现代正式服装，移除 {'、'.join(removed_ancient_clothing)}。")

    tags = tag_set()
    adult_mature_person = (
        str(settings.get("标签反推模式", "") or "").strip() == "成人向成熟"
        and str(settings.get("主体类型", "自动") or "自动").strip() != "非人物主体"
    )
    if adult_mature_person:
        all_tags_ordered = collect_all_tags(normalized_selected, normalized_custom)

        subject_anchors = set(context.get("adult_mature_subject_anchors", set()))
        default_subject_anchor = str(context.get("adult_mature_default_subject_anchor", "") or "").strip()
        if subject_anchors and default_subject_anchor and not (set(all_tags_ordered) & subject_anchors):
            append_tag_to_state(normalized_selected, normalized_custom, default_subject_anchor)
            notes.append(f"成人向主体补锚：补入 {default_subject_anchor}，避免反推模板缺少明确成年主体。")

        youth_risk_tags = set(context.get("adult_mature_youth_risk_tags", set()))
        youth_safe_map: dict[str, list[str]] = {
            str(key): [str(item).strip() for item in value if str(item).strip()]
            for key, value in dict(context.get("adult_mature_youth_safe_map", {})).items()
        }
        removed_youth_risks = [tag for tag in collect_all_tags(normalized_selected, normalized_custom) if tag in youth_risk_tags]
        rewritten_youth_risks: list[str] = []
        for youth_tag in removed_youth_risks:
            remove_tag_from_state(normalized_selected, normalized_custom, youth_tag)
            safe_tags = youth_safe_map.get(youth_tag, [])
            for safe_tag in safe_tags:
                append_tag_to_state(normalized_selected, normalized_custom, safe_tag)
            if safe_tags:
                rewritten_youth_risks.append(f"{youth_tag}->{'+'.join(safe_tags)}")
        if removed_youth_risks:
            rewrite_note = f"；安全转译 {'、'.join(rewritten_youth_risks)}" if rewritten_youth_risks else ""
            notes.append(f"成人向年龄收敛：移除幼态/校园风险标签 {'、'.join(uniq(removed_youth_risks))}{rewrite_note}。")

        hair_conflict_tags = set(context.get("hair_conflict_tags", set()))
        all_tags_ordered = collect_all_tags(normalized_selected, normalized_custom)
        hair_hits = [tag for tag in all_tags_ordered if tag in hair_conflict_tags]
        if len(hair_hits) > 1:
            keep_hair = hair_hits[0]
            removed_hair = hair_hits[1:]
            for hair_tag in removed_hair:
                remove_tag_from_state(normalized_selected, normalized_custom, hair_tag)
            notes.append(f"发型收敛：保留 {keep_hair}，移除冲突发型 {'、'.join(removed_hair)}。")

    apply_stage_prompt_skills(
        normalized_selected,
        normalized_custom,
        settings,
        notes,
        phase="mid_normalize",
        collect_all_tags=collect_all_tags,
        remove_tag_from_state=remove_tag_from_state,
        append_tag_to_state=append_tag_to_state,
        uniq=uniq,
        context=context,
    )

    if adult_mature_person:
        tags = tag_set()
        all_tags_ordered = collect_all_tags(normalized_selected, normalized_custom)
        adult_intimate_clothing = set(context.get("adult_mature_intimate_clothing", set())) | intimate_clothing_tags
        outfit_priority = list(context.get("adult_mature_outfit_priority", [])) or [
            "吊带睡裙",
            "丝质睡袍",
            "睡裙",
            "浴袍",
            "透明睡袍",
            "内衣风",
        ]
        adult_intimate_hits = [tag for tag in all_tags_ordered if tag in adult_intimate_clothing]
        if adult_intimate_hits:
            clothing_hits = [tag for tag in all_tags_ordered if tag in clothing_core_tags or tag in adult_intimate_clothing]
            keep_outfit = next((tag for tag in outfit_priority if tag in adult_intimate_hits), adult_intimate_hits[0])
            removed_outfits = [tag for tag in clothing_hits if tag != keep_outfit and tag in (clothing_core_tags | adult_intimate_clothing)]
            for outfit_tag in removed_outfits:
                remove_tag_from_state(normalized_selected, normalized_custom, outfit_tag)
            if removed_outfits:
                notes.append(f"成人向服装收敛：保留 {keep_outfit} 主服装，移除多套服装 {'、'.join(removed_outfits)}。")

        tags = tag_set()
        closeup_markers = tuple(str(marker) for marker in context.get("adult_mature_closeup_markers", set()) if str(marker).strip())
        removed_closeups: list[str] = []
        if closeup_markers:
            for tag in list(collect_all_tags(normalized_selected, normalized_custom)):
                if any(marker in tag for marker in closeup_markers):
                    remove_tag_from_state(normalized_selected, normalized_custom, tag)
                    removed_closeups.append(tag)
        if removed_closeups:
            notes.append(f"成人向局部收敛：移除局部特写/贴脸前景 {'、'.join(uniq(removed_closeups))}。")

        direct_noise_markers = tuple(str(marker) for marker in context.get("adult_mature_direct_noise_markers", set()) if str(marker).strip())
        removed_direct_noise: list[str] = []
        if direct_noise_markers:
            for tag in list(collect_all_tags(normalized_selected, normalized_custom)):
                if any(marker.casefold() in str(tag).casefold() for marker in direct_noise_markers):
                    remove_tag_from_state(normalized_selected, normalized_custom, tag)
                    removed_direct_noise.append(tag)
        if removed_direct_noise:
            notes.append(f"成人向自定义收敛：移除直出质量词或误导句 {'、'.join(uniq(removed_direct_noise))}。")

        tags = tag_set()
        composition_noise_tags = set(context.get("adult_mature_composition_noise_tags", set()))
        removed_composition_noise = [tag for tag in list(tags) if tag in composition_noise_tags]
        for composition_tag in removed_composition_noise:
            remove_tag_from_state(normalized_selected, normalized_custom, composition_tag)
        if removed_composition_noise:
            notes.append(f"成人向构图收敛：移除易遮挡或抢镜构图 {'、'.join(removed_composition_noise)}。")

        tags = tag_set()
        close_shot_risk_tags = set(context.get("adult_mature_close_shot_risk_tags", set()))
        stable_shot_tag = str(context.get("adult_mature_stable_shot_tag", "") or "").strip()
        close_shot_hits = [tag for tag in collect_all_tags(normalized_selected, normalized_custom) if tag in close_shot_risk_tags]
        if len(close_shot_hits) >= 2 and stable_shot_tag:
            for shot_tag in close_shot_hits:
                remove_tag_from_state(normalized_selected, normalized_custom, shot_tag)
            append_tag_to_state(normalized_selected, normalized_custom, stable_shot_tag)
            notes.append(f"成人向景别收敛：移除过近景别 {'、'.join(uniq(close_shot_hits))}，改为 {stable_shot_tag}。")

        all_tags_ordered = collect_all_tags(normalized_selected, normalized_custom)
        action_tags = set(context.get("adult_mature_action_tags", set()))
        action_priority = list(context.get("adult_mature_action_priority", []))
        action_hits = [tag for tag in all_tags_ordered if tag in action_tags]
        if len(action_hits) > 1:
            keep_action = next((tag for tag in action_priority if tag in action_hits), action_hits[0])
            removed_actions = [tag for tag in action_hits if tag != keep_action]
            for action_tag in removed_actions:
                remove_tag_from_state(normalized_selected, normalized_custom, action_tag)
            if removed_actions:
                notes.append(f"成人向动作收敛：保留 {keep_action} 主姿态，移除多动作拼贴 {'、'.join(removed_actions)}。")

        tags = tag_set()
        realistic_art_conflicts = set(context.get("adult_mature_realistic_style_conflicts", set()))
        if base_template_style() == "真实感" and realistic_art_conflicts:
            removed_style_conflicts = [tag for tag in list(tags) if tag in realistic_art_conflicts]
            for style_tag in removed_style_conflicts:
                remove_tag_from_state(normalized_selected, normalized_custom, style_tag)
            if removed_style_conflicts:
                notes.append(f"成人向风格收敛：真实感模式移除绘画/装饰风格漂移 {'、'.join(removed_style_conflicts)}。")

        tags = tag_set()
        prop_conflicts = set(context.get("adult_mature_prop_conflicts", set()))
        removed_prop_conflicts = [tag for tag in list(tags) if tag in prop_conflicts]
        for prop_tag in removed_prop_conflicts:
            remove_tag_from_state(normalized_selected, normalized_custom, prop_tag)
        if removed_prop_conflicts:
            notes.append(f"成人向道具收敛：移除与私密写真主线冲突的道具 {'、'.join(removed_prop_conflicts)}。")

    apply_stage_prompt_skills(
        normalized_selected,
        normalized_custom,
        settings,
        notes,
        phase="final_normalize",
        collect_all_tags=collect_all_tags,
        remove_tag_from_state=remove_tag_from_state,
        append_tag_to_state=append_tag_to_state,
        uniq=uniq,
        context=context,
    )

    tags = tag_set()
    reference_sheet_tags = set(context.get("danbooru_reference_sheet_tags", set()))
    reference_sheet_hits = [tag for tag in collect_all_tags(normalized_selected, normalized_custom) if tag in reference_sheet_tags]
    if reference_sheet_hits:
        allowed_backgrounds = set(context.get("danbooru_reference_sheet_background_tags", set()))
        removed_scenes = [
            tag
            for tag in list(normalized_selected.get("场景背景", []))
            if tag not in allowed_backgrounds
        ]
        for scene_tag in removed_scenes:
            remove_tag_from_state(normalized_selected, normalized_custom, scene_tag)
        if not (tag_set() & allowed_backgrounds):
            append_tag_to_state(normalized_selected, normalized_custom, "简单背景")
        dynamic_tags = set(context.get("danbooru_reference_sheet_dynamic_tags", set()))
        removed_dynamic = [tag for tag in collect_all_tags(normalized_selected, normalized_custom) if tag in dynamic_tags]
        for dynamic_tag in removed_dynamic:
            remove_tag_from_state(normalized_selected, normalized_custom, dynamic_tag)
        if removed_scenes or removed_dynamic:
            notes.append(
                "设定表收敛：保留多视角/参考表结构，移除具体场景或动态镜头 "
                + "、".join(uniq([*removed_scenes, *removed_dynamic]))
                + "，并使用简洁背景。"
            )

    for family in context.get("danbooru_visual_intent_families", ()):
        if not isinstance(family, dict):
            continue
        family_tags = {str(tag).strip() for tag in family.get("tags", ()) if str(tag).strip()}
        max_keep = max(1, int(family.get("max_keep", 1) or 1))
        active = [tag for tag in collect_all_tags(normalized_selected, normalized_custom) if tag in family_tags]
        if len(active) <= max_keep:
            continue
        removed_family = active[max_keep:]
        for family_tag in removed_family:
            remove_tag_from_state(normalized_selected, normalized_custom, family_tag)
        family_name = str(family.get("name", "视觉意图") or "视觉意图").strip()
        notes.append(
            f"{family_name}收敛：保留 {'、'.join(active[:max_keep])}，移除互斥标签 {'、'.join(removed_family)}。"
        )

    tags = tag_set()
    removed_emotions: list[str] = []
    for trigger_tags, conflict_tags in context.get("emotion_cleanup_rules", []):
        trigger_set = set(trigger_tags)
        conflict_set = set(conflict_tags)
        if not (tags & trigger_set):
            continue
        for emotion_tag in list(conflict_set):
            if emotion_tag in tags:
                remove_tag_from_state(normalized_selected, normalized_custom, emotion_tag)
                removed_emotions.append(emotion_tag)
        tags = tag_set()
    if removed_emotions:
        notes.append(f"情绪收敛：移除互斥情绪 {'、'.join(uniq(removed_emotions))}。")

    return normalized_selected, uniq(normalized_custom), notes
