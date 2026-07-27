# -*- coding: utf-8 -*-
"""Unified intent, scene-graph, model-strategy, and preference orchestration."""

from __future__ import annotations

from collections import OrderedDict
import re
from typing import Any, Iterable


INTELLIGENCE_PROFILE_VERSION = "qwen-te-intelligence-v5"

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

_LOCATION_WORLD_FAMILIES = {
    "underground_ruin", "ancient_human", "sacred_place", "urban_space", "industrial_scifi",
    "private_interior", "natural_wilderness", "underwater", "rural_life", "neutral_studio",
}
_INTENT_PATTERNS: dict[str, tuple[str, ...]] = {
    "character_sheet": (
        "角色设定图", "人物设定图", "角色设定表", "三视图", "正侧背", "正面侧面背面",
        "character sheet", "character turnaround", "front side back", "orthographic views",
    ),
    "video_first": (
        "视频提示词", "连续分镜", "镜头脚本", "故事分镜", "动态镜头", "运镜",
        "video prompt", "storyboard", "shot sequence", "camera movement",
    ),
    "non_person": (
        "非人物主体", "无人场景", "产品摄影", "产品设定图", "建筑概念图", "载具设定图",
        "non-human subject", "product shot", "vehicle design", "environment concept",
    ),
}
_ACTION_PROP_REQUIREMENTS: tuple[tuple[tuple[str, ...], tuple[str, ...], str], ...] = (
    (("举起火炬", "点燃火炬", "torch", "raises a torch", "lights a torch", "holds a torch", "carries a torch"), ("火炬", "torch"), "火炬"),
    (("挥剑", "拔剑", "持剑", "剑术", "sword", "swings a sword", "draws a sword", "holds a sword", "wields a sword"), ("长剑", "宝剑", "剑", "sword"), "剑"),
    (("射箭", "拉弓", "搭箭", "archery"), ("弓箭", "弓", "箭", "bow", "arrow"), "弓箭"),
    (("展开卷轴", "阅读卷轴", "scroll", "reads a scroll", "unrolls a scroll", "opens a scroll"), ("卷轴", "scroll"), "卷轴"),
    (("举起相机", "手持相机拍摄", "使用相机拍摄", "用相机拍摄", "camera in hand"), ("相机", "摄影机", "camera"), "相机"),
    (("手机拍摄", "举起手机", "查看手机", "用手机拍摄", "拍照手机", "holding a phone", "using a phone"), ("手机", "智能手机", "phone", "smartphone"), "手机"),
    (("撑伞", "举伞", "收伞", "holding an umbrella", "opens an umbrella"), ("雨伞", "伞", "umbrella"), "雨伞"),
    (("提灯", "举起灯笼", "点亮灯笼", "holding a lantern", "raises a lantern"), ("灯笼", "提灯", "lantern"), "灯笼"),
    (("举盾", "持盾", "用盾格挡", "shield block", "raises a shield"), ("盾牌", "盾", "shield"), "盾牌"),
    (("翻书", "读书", "阅读书籍", "reading a book", "opens a book"), ("书本", "书籍", "书", "book"), "书本"),
    (("举起望远镜", "用望远镜观察", "透过望远镜", "looking through binoculars"), ("望远镜", "binoculars"), "望远镜"),
    (("挥铲", "用铲挖掘", "持铲挖掘", "digging with a shovel"), ("铲子", "铁铲", "shovel"), "铲子"),
    (("挥杆钓鱼", "甩出鱼线", "抛出鱼线", "casting a fishing line"), ("钓竿", "鱼竿", "fishing rod"), "钓竿"),
)
_CONTEXT_NOUN_ONLY_ACTION_MARKERS = {"torch", "sword", "scroll"}
_STRONG_SCENE_CONFLICTS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("underwater", ("火炬", "篝火", "明火", "torch", "campfire", "open flame"), "水下场景与持续明火冲突"),
    ("neutral_studio", ("暴雨", "暴雪", "沙尘暴", "雷暴", "storm", "blizzard", "sandstorm"), "中性影棚与户外极端天气冲突"),
)

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


_CLAUSE_BOUNDARY_RE = re.compile(
    r"(?:[，,；;。！？.!?\n]+|(?:但(?:是|要)?|不过|然而|而是|反而)|"
    r"\b(?:but|however|instead|yet)\b)",
    flags=re.IGNORECASE,
)
_BROAD_NEGATION_RE = re.compile(
    r"(?:不要|不需要|不必|无需|不能|别(?:再)?|未(?:启用|使用|包含|生成)?|避免|禁止|排除|移除|去掉|不是|并非|不得|不可|"
    r"\b(?:do\s+not|don't|does\s+not|doesn't|cannot|can't|should\s+not|shouldn't|must\s+not|"
    r"will\s+not|won't|not|never|without|avoid|exclude|remove|omit)\b)"
    r"[^，,；;。！？.!?\n]{0,24}$",
    flags=re.IGNORECASE,
)
_NEGATION_CANCEL_RE = re.compile(
    r"(?:不仅|不只|不止|不光|\bnot\s+only\b)[^，,；;。！？.!?\n]{0,24}$",
    flags=re.IGNORECASE,
)
_DIRECT_NEGATION_RE = re.compile(
    r"(?:没有|不含|无|非|\bno\b)\s*(?:任何|任意|any)?\s*$",
    flags=re.IGNORECASE,
)


def _marker_matches(text: str, marker: str) -> list[re.Match[str]]:
    source = str(text or "").casefold()
    needle = str(marker or "").casefold()
    if not source or not needle:
        return []
    if needle.isascii() and re.fullmatch(r"[a-z0-9][a-z0-9 ._-]*", needle):
        return list(re.finditer(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", source))
    return list(re.finditer(re.escape(needle), source))


def _marker_polarity(text: str, marker: str) -> tuple[bool, bool]:
    source = str(text or "").casefold()
    positive = False
    negated = False
    for match in _marker_matches(source, marker):
        prefix = source[max(0, match.start() - 80) : match.start()]
        clause_prefix = _CLAUSE_BOUNDARY_RE.split(prefix)[-1][-48:]
        broad_negation = _BROAD_NEGATION_RE.search(clause_prefix)
        if (broad_negation and not _NEGATION_CANCEL_RE.search(clause_prefix)) or _DIRECT_NEGATION_RE.search(clause_prefix):
            negated = True
            continue
        positive = True
    return positive, negated


def _marker_present(text: str, marker: str) -> bool:
    return _marker_polarity(text, marker)[0]


def detect_world_families(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    hits: dict[str, list[str]] = {}
    for family, markers in WORLD_FAMILY_MARKERS.items():
        matched = [marker for marker in markers if _marker_present(source, marker)]
        if matched:
            hits[family] = matched
    return hits


def _contains_any(text: Any, markers: Iterable[str]) -> bool:
    source = _clean(text)
    return any(_marker_present(source, marker) for marker in markers)


def _intent_signals(
    settings: dict[str, Any],
) -> tuple[str, list[str], dict[str, list[str]], dict[str, list[str]]]:
    text = "，".join(
        _clean(settings.get(key))
        for key in ("智能文本输入", "额外要求", "图片反推附加要求")
        if _clean(settings.get(key))
    )
    polarity = {
        name: {marker: _marker_polarity(text, marker) for marker in markers}
        for name, markers in _INTENT_PATTERNS.items()
    }
    evidence = {
        name: [marker for marker, (positive, _negated) in markers.items() if positive]
        for name, markers in polarity.items()
    }
    evidence = {name: markers for name, markers in evidence.items() if markers}
    negated_evidence = {
        name: [marker for marker, (_positive, negated) in markers.items() if negated]
        for name, markers in polarity.items()
    }
    negated_evidence = {name: markers for name, markers in negated_evidence.items() if markers}
    return text, list(evidence), evidence, negated_evidence


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
    intent_text, text_signals, text_evidence, negated_text_evidence = _intent_signals(settings)
    character_sheet_enabled = character_sheet_enabled or "character_sheet" in text_signals
    tag_block_enabled = bool(settings.get("标签块编排启用", False))
    smart_enabled = bool(settings.get("智能文本匹配", False)) and bool(
        _clean(settings.get("智能文本输入") or settings.get("额外要求"))
    )
    if character_sheet_enabled:
        task_type = "character_sheet_from_reference" if has_reference_image and image_reverse_enabled else "character_sheet_from_text"
        confidence = 1.0
    elif image_reverse_enabled and has_reference_image:
        task_type = "image_reverse_description"
        confidence = 1.0
    elif subject_type == "非人物主体" or "non_person" in text_signals:
        task_type = "non_person_visual_story"
        confidence = 0.96 if subject_type == "非人物主体" else 0.88
    elif tag_block_enabled:
        task_type = "ordered_tag_block_story"
        confidence = 0.94
    elif "video_first" in text_signals:
        task_type = "video_first_story"
        confidence = 0.86
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
        "text_signals": text_signals,
        "text_evidence": text_evidence,
        "negated_text_evidence": negated_text_evidence,
        "intent_text_present": bool(intent_text),
        "primary_channel": "video_storyboard" if "video_first" in text_signals else "image_prompt",
        "channels": ["image_prompt", "video_storyboard"],
    }


def build_scene_relationship_graph(
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    custom_tags: Iterable[Any] = (),
    *,
    context_text: Any = "",
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

    natural_context = _clean(context_text)
    selected_action_text = "，".join(groups.get("动作姿态", []))
    action_text = "，".join([selected_action_text, natural_context])
    prop_text = "，".join(groups.get("道具世界观", []))
    inferred_requirements: list[dict[str, Any]] = []
    for action_markers, prop_markers, label in _ACTION_PROP_REQUIREMENTS:
        evidence = [
            marker
            for marker in action_markers
            if _marker_present(selected_action_text, marker)
            or (
                marker.casefold() not in _CONTEXT_NOUN_ONLY_ACTION_MARKERS
                and _marker_present(natural_context, marker)
            )
        ]
        if not evidence:
            continue
        satisfied = _contains_any(prop_text, prop_markers)
        inferred_requirements.append(
            {
                "source": groups.get("动作姿态", []) or [action_text],
                "relation": "requires_prop",
                "target": [label],
                "satisfied": satisfied,
                "evidence": evidence[:3],
            }
        )
        relations.append(
            {
                "source": groups.get("动作姿态", []) or [action_text],
                "relation": "supported_by",
                "target": [label],
            }
        )

    scene_text = "，".join(
        [
            *groups.get("场景背景", []),
            *groups.get("道具世界观", []),
            *groups.get("动作姿态", []),
            *custom,
        ]
    )
    explicit_hits = detect_world_families(scene_text)
    scene_only_hits = detect_world_families("，".join(groups.get("场景背景", [])))
    primary_family = next(iter(scene_only_hits), "")
    allowed = set(explicit_hits)
    inferred_world_hits = detect_world_families(
        "，".join(
            str(value)
            for requirement in inferred_requirements
            for value in list(requirement.get("target", []) or [])
        )
    )
    allowed.update(inferred_world_hits)
    if primary_family:
        allowed.add(primary_family)
        allowed.update(_WORLD_COMPATIBILITY.get(primary_family, ()))
    forbidden = [family for family in WORLD_FAMILY_MARKERS if family not in allowed]
    hard_anchors = {
        group: values
        for group, values in groups.items()
        if values and group in {"主体", "服装造型", "场景背景", "动作姿态", "道具世界观", "画面风格", "构图视角"}
    }
    coherence_issues: list[dict[str, str]] = []
    location_families = [family for family in scene_only_hits if family in _LOCATION_WORLD_FAMILIES]
    if len(location_families) > 1:
        coherence_issues.append(
            {
                "kind": "multiple_scene_families",
                "severity": "warning",
                "message": f"场景同时包含多个世界族：{'、'.join(location_families)}；模型只能按用户主线融合，不得继续增加第三种场景。",
            }
        )
    combined_text = "，".join(
        [
            *groups.get("场景背景", []),
            *groups.get("道具世界观", []),
            *groups.get("动作姿态", []),
            *groups.get("光影氛围", []),
        ]
    )
    for family, markers, message in _STRONG_SCENE_CONFLICTS:
        if family in scene_only_hits and _contains_any(combined_text, markers):
            coherence_issues.append({"kind": "scene_affordance_conflict", "severity": "error", "message": message})
    for requirement in inferred_requirements:
        if not requirement.get("satisfied"):
            coherence_issues.append(
                {
                    "kind": "implicit_prop_anchor",
                    "severity": "info",
                    "message": f"动作已隐含道具“{requirement['target'][0]}”，生成时必须保持该动作-道具关系。",
                }
            )
    return {
        "nodes": groups,
        "custom_context": custom,
        "natural_context_present": bool(natural_context),
        "relations": relations,
        "hard_anchors": hard_anchors,
        "inferred_requirements": inferred_requirements,
        "coherence_issues": coherence_issues,
        "coherence_status": "conflict" if any(item["severity"] == "error" for item in coherence_issues) else ("review" if coherence_issues else "coherent"),
        "primary_world_family": primary_family,
        "explicit_world_families": list(explicit_hits),
        "inferred_world_families": list(inferred_world_hits),
        "allowed_world_families": sorted(allowed),
        "forbidden_world_families": forbidden,
    }


def resolve_model_strategy(
    settings: dict[str, Any],
    task_intent: dict[str, Any],
    scene_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = _clean(settings.get("模型调用基础来源") or settings.get("模型来源") or "仅Skill")
    task_type = _clean(task_intent.get("task_type"))
    strict = _clean(settings.get("风格隔离策略")) == "严格风格隔离"
    adult = bool(settings.get("NSFW工作台启用", False) or settings.get("NSFW策略启用", False))
    coherence_issues = list((scene_graph or {}).get("coherence_issues", []) or [])
    structure_sensitive = (
        task_type.startswith("character_sheet")
        or task_type in {"ordered_tag_block_story", "video_first_story"}
    )
    risk_score = min(
        100,
        (35 if source.startswith("本地") else 0)
        + (25 if structure_sensitive else 0)
        + (15 if strict else 0)
        + (15 if adult else 0)
        + min(20, len(coherence_issues) * 8),
    )
    if source in {"", "仅Skill"}:
        mode = "skill_only"
        reason = "当前未启用模型，直接使用已校验 Skill 成品。"
    elif (
        source.startswith("本地")
        or structure_sensitive
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
        "risk_score": risk_score,
        "coherence_issue_count": len(coherence_issues),
        "reason": reason,
    }


def update_preference_memory(
    memory: Any,
    explicit_selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    *,
    task_type: str,
    context_key: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = dict(memory) if isinstance(memory, dict) else {}
    channels = dict(state.get("channels")) if isinstance(state.get("channels"), dict) else {}
    context = _clean(context_key) or "general"
    channel_key = task_type if context == "general" else f"{task_type}::{context}"
    channel = dict(channels.get(channel_key)) if isinstance(channels.get(channel_key), dict) else {}
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
    channels[channel_key] = channel
    state = {"version": 2, "channels": channels}

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
        "context_key": context,
        "channel_key": channel_key,
        "observations": observations,
        "stable_preferences": stable,
        "application": "soft_unlocked_details_only",
    }
    return state, profile


def resolve_preference_hints(
    preference_profile: Any,
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    settings: dict[str, Any],
    *,
    scene_graph: Any = None,
) -> dict[str, list[str]]:
    if not isinstance(preference_profile, dict):
        return {}
    stable = preference_profile.get("stable_preferences")
    if not isinstance(stable, dict):
        return {}
    task_type = _clean(preference_profile.get("task_type"))
    subject_type = _clean(settings.get("主体类型解析结果") or settings.get("主体类型"))
    template_style = _clean(settings.get("模板风格") or "自动")
    hints: dict[str, list[str]] = {}
    for group in _PREFERENCE_GROUPS:
        if _unique(selected.get(group, []), 4):
            continue
        if group == "画面风格" and template_style not in {"", "自动"}:
            continue
        if group == "服装造型" and (subject_type == "非人物主体" or task_type.startswith("character_sheet")):
            continue
        if group == "构图视角" and task_type.startswith("character_sheet"):
            continue
        values = [
            value
            for value in _unique(stable.get(group, []), 3)
            if value not in _PREFERENCE_EXCLUSIONS
        ]
        if not values:
            continue
        candidate = values[0]
        scene_text = "，".join(_unique(selected.get("场景背景", []), 5))
        if candidate_world_violation(scene_text, f"{scene_text}，{candidate}", scene_graph):
            continue
        hints[group] = [candidate]
    return hints


def resolve_relation_hints(
    scene_graph: Any,
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    settings: dict[str, Any],
) -> dict[str, list[str]]:
    if not isinstance(scene_graph, dict):
        return {}
    issues = list(scene_graph.get("coherence_issues", []) or [])
    if any(isinstance(item, dict) and item.get("severity") == "error" for item in issues):
        return {}
    inferred: list[str] = []
    for requirement in list(scene_graph.get("inferred_requirements", []) or []):
        if not isinstance(requirement, dict) or requirement.get("satisfied"):
            continue
        for value in _unique(requirement.get("target", []), 2):
            if value not in inferred:
                inferred.append(value)
    if not inferred:
        return {}
    scene_text = "，".join(_unique(selected.get("场景背景", []), 5))
    allowed = [
        value
        for value in inferred[:2]
        if value not in _unique(selected.get("道具世界观", []), 8)
        and not candidate_world_violation(scene_text, f"{scene_text}，{value}", scene_graph)
    ]
    return {"道具世界观": allowed} if allowed else {}


def classify_repair_reason(reason: Any) -> dict[str, str]:
    text = _clean(reason)
    folded = text.casefold()
    rules = (
        ("missing_anchor", ("缺少", "锚点"), "只补回缺失锚点，并保持其与主体、动作和场景的原有关联。"),
        ("world_conflict", ("世界族",), "只删除越界世界族及其附属物件，再用当前场景已有材质或环境反馈补足语句。"),
        ("scene_conflict", ("冲突场景",), "只移除错误场景，所有动作、道具和光线必须回到当前唯一主场景。"),
        ("language", ("语言",), "只把正文改为当前要求的语言，不改变任何视觉事实与剧情顺序。"),
        ("layout", ("画面结构",), "只修正单帧、人数或多视图结构，不增加人物副本、额外视角或分屏。"),
        ("wrapper", ("分析", "占位符"), "删除分析、占位符、标题和标签包装，只返回可直接使用的自然语言正文。"),
        ("narrative", ("自然语言",), "只补齐动作因果、环境反馈和完整句子，不替换已有视觉锚点。"),
        ("duplicate", ("重复",), "只改写重复表达并恢复本条独有的主体、场景、动作与镜头差异。"),
    )
    for kind, markers, instruction in rules:
        if all(marker.casefold() in folded for marker in markers):
            return {"kind": kind, "instruction": instruction, "reason": text}
    return {
        "kind": "invalid_output",
        "instruction": "只修复校验指出的问题，其他已经正确的视觉事实与剧情结构保持不变。",
        "reason": text,
    }


def build_intelligence_profile(
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    custom_tags: Iterable[Any],
    settings: dict[str, Any],
    *,
    has_reference_image: bool = False,
    preference_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task_intent = infer_task_intent(selected, settings, has_reference_image=has_reference_image)
    context_text = "，".join(
        _clean(settings.get(key))
        for key in ("智能文本输入", "额外要求", "图片反推附加要求")
        if _clean(settings.get(key))
    )
    scene_graph = build_scene_relationship_graph(selected, custom_tags, context_text=context_text)
    model_strategy = resolve_model_strategy(settings, task_intent, scene_graph)
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
    hints = dict(profile.get("preference_hints", {}))
    relation_hints = dict(profile.get("relation_hints", {}))
    stable = dict(preference.get("stable_preferences", {}))
    stable_text = "、".join(
        f"{group}={','.join(str(item) for item in values)}"
        for group, values in stable.items()
        if values
    ) or "尚未形成"
    hint_text = "、".join(
        f"{group}={','.join(str(item) for item in values)}"
        for group, values in hints.items()
        if values
    ) or "未应用"
    relation_text = "、".join(
        f"{group}={','.join(str(item) for item in values)}"
        for group, values in relation_hints.items()
        if values
    ) or "无需补全"
    positive_evidence = _unique(
        marker
        for markers in dict(task.get("text_evidence", {}) or {}).values()
        for marker in list(markers or [])
    )[:3]
    negated_evidence = _unique(
        marker
        for markers in dict(task.get("negated_text_evidence", {}) or {}).values()
        for marker in list(markers or [])
    )[:3]
    evidence_parts = []
    if positive_evidence:
        evidence_parts.append("正向=" + ",".join(positive_evidence))
    if negated_evidence:
        evidence_parts.append("排除=" + ",".join(negated_evidence))
    evidence_text = "；".join(evidence_parts) or "无文本触发"
    return (
        f"任务 {task.get('task_type', 'unknown')} ({float(task.get('confidence', 0) or 0):.2f}) | "
        f"证据 {evidence_text} | "
        f"世界族 {graph.get('primary_world_family') or '未限定'} | "
        f"模型策略 {strategy.get('mode', 'skill_only')} (风险 {int(strategy.get('risk_score', 0) or 0)}) | "
        f"偏好 {stable_text} | 本次软应用 {hint_text} | 关系补全 {relation_text}"
    )


__all__ = [
    "INTELLIGENCE_PROFILE_VERSION",
    "WORLD_FAMILY_MARKERS",
    "build_intelligence_profile",
    "build_scene_relationship_graph",
    "candidate_world_violation",
    "classify_repair_reason",
    "detect_world_families",
    "infer_task_intent",
    "resolve_model_strategy",
    "resolve_preference_hints",
    "resolve_relation_hints",
    "summarize_intelligence_profile",
    "update_preference_memory",
]
