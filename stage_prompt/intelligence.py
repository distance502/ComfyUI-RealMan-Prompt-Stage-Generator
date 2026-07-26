# -*- coding: utf-8 -*-
"""Unified intent, scene-graph, model-strategy, and preference orchestration."""

from __future__ import annotations

from collections import OrderedDict
import re
from typing import Any, Iterable


INTELLIGENCE_PROFILE_VERSION = "qwen-te-intelligence-v1"

_GROUP_LIMITS = {
    "主体": 6,
    "画面风格": 5,
    "服装造型": 5,
    "场景背景": 5,
    "动作姿态": 5,
    "光影氛围": 5,
    "构图视角": 5,
    "道具世界观": 5,
    "技术画质": 4,
    "成人向表达": 4,
}
_PREFERENCE_GROUPS = ("画面风格", "服装造型", "光影氛围", "构图视角", "技术画质")
_PREFERENCE_EXCLUSIONS = {
    "无", "自动", "自动判断", "高细节", "清晰对焦", "人物完整入镜", "全身完整入镜",
    "主体轮廓清晰", "空间层次明确", "无文字", "无水印", "无logo",
}

WORLD_FAMILY_MARKERS: dict[str, tuple[str, ...]] = {
    "underground_ruin": (
        "地下城", "地牢", "地下遗迹", "洞窟", "洞穴", "矿井", "墓穴", "陵墓", "石窟",
        "dungeon", "underground ruin", "cavern", "cave", "mine shaft", "crypt", "tomb",
    ),
    "ancient_human": (
        "宫殿", "宫道", "古城", "古街", "古镇", "庭院", "回廊", "水榭", "书院", "客栈",
        "ancient palace", "ancient city", "old town", "courtyard", "covered corridor",
    ),
    "sacred_place": (
        "神殿", "祭坛", "教堂", "圣所", "寺庙", "神社", "宗教空间",
        "temple", "altar", "church", "cathedral", "sanctuary", "shrine",
    ),
    "urban_space": (
        "城市街道", "街头", "街巷", "街区", "小巷", "站台", "车站", "列车", "地铁", "公交车",
        "汽车", "站牌", "天台", "停车场", "办公室", "咖啡厅", "便利店", "酒吧", "夜店",
        "urban street", "city street", "alley", "station", "train", "subway", "bus", "car", "rooftop",
    ),
    "industrial_scifi": (
        "机库", "维修舱", "太空船", "飞船", "工业废墟", "未来都市", "霓虹街区", "机械舱", "轨道空间站",
        "监控屏幕", "显示屏", "控制台", "机械关节", "机械臂", "义体接口", "月球车", "机器人", "全息界面",
        "hangar", "maintenance bay", "spaceship", "spacecraft", "industrial ruin", "futuristic city",
        "monitor screen", "control console", "mechanical joint", "robotic arm", "lunar rover", "holographic interface",
    ),
    "private_interior": (
        "卧室", "酒店套房", "浴室", "浴缸", "淋浴", "温泉", "更衣室", "床边", "沙发", "双人床", "梳妆台",
        "bedroom", "hotel suite", "bathroom", "bathtub", "shower room", "dressing room", "sofa", "double bed",
    ),
    "natural_wilderness": (
        "森林", "竹林", "山谷", "草原", "草甸", "沙漠", "荒野", "海滩", "海岸", "湖畔", "溪流", "瀑布",
        "forest", "bamboo grove", "valley", "grassland", "meadow", "desert", "wilderness", "beach", "coast",
    ),
    "underwater": (
        "海底", "水下", "深海", "珊瑚礁", "沉船", "海沟",
        "underwater", "deep sea", "coral reef", "shipwreck", "ocean trench",
    ),
    "rural_life": (
        "农舍", "农场", "乡村小道", "田野", "谷仓", "厨房", "餐厅",
        "farmhouse", "farm", "country road", "field", "barn", "kitchen", "dining room",
    ),
    "neutral_studio": (
        "摄影棚", "影棚", "白棚", "纯色背景", "无缝背景", "极简背景", "白色背景", "中性背景",
        "studio", "seamless backdrop", "plain background", "minimal background", "neutral background",
    ),
    "fantasy_adventure_gear": (
        "火炬", "长剑", "宝剑", "盾牌", "法杖", "卷轴", "药水", "弓箭", "盔甲",
        "torch", "longsword", "sword", "shield", "staff", "scroll", "potion", "bow", "armor",
    ),
}

_WORLD_COMPATIBILITY: dict[str, tuple[str, ...]] = {
    "underground_ruin": ("fantasy_adventure_gear", "ancient_human", "sacred_place"),
    "ancient_human": ("fantasy_adventure_gear", "sacred_place"),
    "sacred_place": ("fantasy_adventure_gear", "ancient_human"),
    "urban_space": (),
    "industrial_scifi": ("urban_space",),
    "private_interior": (),
    "natural_wilderness": ("fantasy_adventure_gear",),
    "underwater": ("natural_wilderness",),
    "rural_life": ("natural_wilderness",),
    "neutral_studio": (),
    "fantasy_adventure_gear": (),
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _unique(values: Iterable[Any], limit: int = 12) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if not text or key in {"无", "none", "null"} or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) >= max(1, int(limit)):
            break
    return result


def _marker_present(text: str, marker: str) -> bool:
    source = str(text or "").casefold()
    needle = str(marker or "").casefold()
    if not source or not needle:
        return False
    if needle.isascii() and re.fullmatch(r"[a-z0-9][a-z0-9 ._-]*", needle):
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", source))
    return needle in source


def detect_world_families(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    hits: dict[str, list[str]] = {}
    for family, markers in WORLD_FAMILY_MARKERS.items():
        matched = [marker for marker in markers if _marker_present(source, marker)]
        if matched:
            hits[family] = matched
    return hits


def infer_task_intent(
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    settings: dict[str, Any],
    *,
    has_reference_image: bool = False,
) -> dict[str, Any]:
    subject_type = _clean(settings.get("主体类型解析结果") or settings.get("主体类型") or "自动")
    image_reverse_enabled = bool(settings.get("图片反推生成", False))
    reverse_mode = _clean(settings.get("图片反推模式") or "角色设定图")
    character_sheet_enabled = bool(_clean(settings.get("角色设定图内部策略"))) or (
        image_reverse_enabled and reverse_mode == "角色设定图"
    )
    tag_block_enabled = bool(settings.get("标签块编排启用", False))
    smart_enabled = bool(settings.get("智能文本匹配", False)) and bool(
        _clean(settings.get("智能文本输入") or settings.get("额外要求"))
    )
    if character_sheet_enabled:
        task_type = "character_sheet_from_reference" if has_reference_image else "character_sheet_from_text"
        confidence = 1.0
    elif image_reverse_enabled and has_reference_image:
        task_type = "image_reverse_description"
        confidence = 1.0
    elif subject_type == "非人物主体":
        task_type = "non_person_visual_story"
        confidence = 0.96
    elif tag_block_enabled:
        task_type = "ordered_tag_block_story"
        confidence = 0.94
    elif smart_enabled:
        task_type = "smart_text_visual_story"
        confidence = 0.9
    else:
        task_type = "standard_visual_story"
        confidence = 0.84
    return {
        "task_type": task_type,
        "confidence": confidence,
        "subject_type": subject_type,
        "has_reference_image": bool(has_reference_image),
        "image_reverse_mode": reverse_mode if image_reverse_enabled else "disabled",
        "character_sheet_enabled": character_sheet_enabled,
        "channels": ["image_prompt", "video_storyboard"],
    }


def build_scene_relationship_graph(
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    custom_tags: Iterable[Any] = (),
) -> dict[str, Any]:
    groups = {
        group: _unique(selected.get(group, []), limit)
        for group, limit in _GROUP_LIMITS.items()
    }
    custom = _unique(custom_tags, 8)
    subject = groups.get("主体", [])
    relations: list[dict[str, Any]] = []
    relation_map = (
        ("服装造型", "wears"),
        ("动作姿态", "performs"),
        ("场景背景", "located_in"),
        ("道具世界观", "uses_or_carries"),
        ("光影氛围", "illuminated_by"),
        ("构图视角", "captured_as"),
        ("画面风格", "rendered_as"),
    )
    for group, relation in relation_map:
        targets = groups.get(group, [])
        if targets:
            relations.append({"source": subject or ["主主体"], "relation": relation, "target": targets})

    scene_text = "，".join([*groups.get("场景背景", []), *groups.get("道具世界观", []), *custom])
    explicit_hits = detect_world_families(scene_text)
    scene_only_hits = detect_world_families("，".join(groups.get("场景背景", [])))
    primary_family = next(iter(scene_only_hits), "")
    allowed = set(explicit_hits)
    if primary_family:
        allowed.add(primary_family)
        allowed.update(_WORLD_COMPATIBILITY.get(primary_family, ()))
    forbidden = [family for family in WORLD_FAMILY_MARKERS if family not in allowed]
    hard_anchors = {
        group: values
        for group, values in groups.items()
        if values and group in {"主体", "服装造型", "场景背景", "动作姿态", "道具世界观", "画面风格", "构图视角"}
    }
    return {
        "nodes": groups,
        "custom_context": custom,
        "relations": relations,
        "hard_anchors": hard_anchors,
        "primary_world_family": primary_family,
        "explicit_world_families": list(explicit_hits),
        "allowed_world_families": sorted(allowed),
        "forbidden_world_families": forbidden,
    }


def resolve_model_strategy(settings: dict[str, Any], task_intent: dict[str, Any]) -> dict[str, Any]:
    source = _clean(settings.get("模型调用基础来源") or settings.get("模型来源") or "仅Skill")
    task_type = _clean(task_intent.get("task_type"))
    strict = _clean(settings.get("风格隔离策略")) == "严格风格隔离"
    adult = bool(settings.get("NSFW工作台启用", False) or settings.get("NSFW策略启用", False))
    if source in {"", "仅Skill"}:
        mode = "skill_only"
        reason = "当前未启用模型，直接使用已校验 Skill 成品。"
    elif (
        source.startswith("本地")
        or task_type.startswith("character_sheet")
        or task_type == "ordered_tag_block_story"
        or strict
        or adult
    ):
        mode = "incremental_blend"
        reason = "当前链路对结构或锚点敏感，模型只补充可安全融合的局部细节。"
    else:
        mode = "conservative_rewrite"
        reason = "API 可整理完整自然语言，但必须保留全部关系图锚点并通过场景校验。"
    return {
        "mode": mode,
        "video_mode": "incremental_storyboard_blend" if mode != "skill_only" else "skill_only",
        "repair_mode": "targeted_patch",
        "preserve_skill_baseline": True,
        "reason": reason,
    }


def update_preference_memory(
    memory: Any,
    explicit_selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    *,
    task_type: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = dict(memory) if isinstance(memory, dict) else {}
    channels = dict(state.get("channels")) if isinstance(state.get("channels"), dict) else {}
    channel = dict(channels.get(task_type)) if isinstance(channels.get(task_type), dict) else {}
    observations = max(0, int(channel.get("observations", 0) or 0)) + 1
    counts = {
        group: dict(values) if isinstance(values, dict) else {}
        for group, values in dict(channel.get("counts", {})).items()
    }
    for group in _PREFERENCE_GROUPS:
        group_counts = counts.setdefault(group, {})
        for tag in _unique(explicit_selected.get(group, []), 8):
            if tag in _PREFERENCE_EXCLUSIONS:
                continue
            group_counts[tag] = max(0, int(group_counts.get(tag, 0) or 0)) + 1
        counts[group] = dict(
            sorted(group_counts.items(), key=lambda item: (-int(item[1]), item[0]))[:24]
        )
    if observations > 32:
        observations = 16
        counts = {
            group: {tag: max(1, int(count) // 2) for tag, count in values.items()}
            for group, values in counts.items()
        }
    channel = {"observations": observations, "counts": counts}
    channels[task_type] = channel
    state = {"version": 1, "channels": channels}

    stable: dict[str, list[str]] = {}
    for group in _PREFERENCE_GROUPS:
        ranked = []
        for tag, count in counts.get(group, {}).items():
            ratio = int(count) / max(1, observations)
            if int(count) >= 2 and ratio >= 0.5:
                ranked.append((tag, int(count), ratio))
        ranked.sort(key=lambda item: (-item[1], -item[2], item[0]))
        if ranked:
            stable[group] = [tag for tag, _count, _ratio in ranked[:3]]
    profile = {
        "task_type": task_type,
        "observations": observations,
        "stable_preferences": stable,
        "application": "soft_unlocked_details_only",
    }
    return state, profile


def build_intelligence_profile(
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    custom_tags: Iterable[Any],
    settings: dict[str, Any],
    *,
    has_reference_image: bool = False,
    preference_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task_intent = infer_task_intent(selected, settings, has_reference_image=has_reference_image)
    scene_graph = build_scene_relationship_graph(selected, custom_tags)
    model_strategy = resolve_model_strategy(settings, task_intent)
    return {
        "version": INTELLIGENCE_PROFILE_VERSION,
        "task_intent": task_intent,
        "scene_graph": scene_graph,
        "model_strategy": model_strategy,
        "preference_profile": dict(preference_profile or {}),
    }


def candidate_world_violation(original: str, candidate: str, scene_graph: Any) -> str:
    if not isinstance(scene_graph, dict):
        return ""
    forbidden = set(str(item) for item in scene_graph.get("forbidden_world_families", []) if str(item))
    if not forbidden:
        return ""
    original_hits = detect_world_families(original)
    candidate_hits = detect_world_families(candidate)
    for family in WORLD_FAMILY_MARKERS:
        if family not in forbidden or family not in candidate_hits or family in original_hits:
            continue
        marker = candidate_hits[family][0]
        return f"模型响应越过场景关系图：引入未获允许的世界族“{family}”元素“{marker}”。"
    return ""


def summarize_intelligence_profile(profile: Any) -> str:
    if not isinstance(profile, dict):
        return "未建立"
    task = dict(profile.get("task_intent", {}))
    graph = dict(profile.get("scene_graph", {}))
    strategy = dict(profile.get("model_strategy", {}))
    preference = dict(profile.get("preference_profile", {}))
    stable = dict(preference.get("stable_preferences", {}))
    stable_text = "、".join(
        f"{group}={','.join(str(item) for item in values)}"
        for group, values in stable.items()
        if values
    ) or "尚未形成"
    return (
        f"任务 {task.get('task_type', 'unknown')} ({float(task.get('confidence', 0) or 0):.2f}) | "
        f"世界族 {graph.get('primary_world_family') or '未限定'} | "
        f"模型策略 {strategy.get('mode', 'skill_only')} | 偏好 {stable_text}"
    )


__all__ = [
    "INTELLIGENCE_PROFILE_VERSION",
    "WORLD_FAMILY_MARKERS",
    "build_intelligence_profile",
    "build_scene_relationship_graph",
    "candidate_world_violation",
    "detect_world_families",
    "infer_task_intent",
    "resolve_model_strategy",
    "summarize_intelligence_profile",
    "update_preference_memory",
]
