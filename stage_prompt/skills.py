# -*- coding: utf-8 -*-
"""Composable skill engine for smarter stage prompt normalization."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import re
from typing import Any, Callable

try:
    from .expanded_profiles import EXPANDED_TEMPLATE_BASE_MAP
except Exception:  # pragma: no cover - direct file loading in focused tests
    import importlib.util as _expanded_importlib_util
    from pathlib import Path as _ExpandedPath

    _expanded_spec = _expanded_importlib_util.spec_from_file_location(
        "stage_prompt_expanded_profiles_skills_test",
        _ExpandedPath(__file__).with_name("expanded_profiles.py"),
    )
    if _expanded_spec is None or _expanded_spec.loader is None:
        raise RuntimeError("Unable to load expanded_profiles.py")
    _expanded_module = _expanded_importlib_util.module_from_spec(_expanded_spec)
    _expanded_spec.loader.exec_module(_expanded_module)
    EXPANDED_TEMPLATE_BASE_MAP = _expanded_module.EXPANDED_TEMPLATE_BASE_MAP


SelectedTags = OrderedDict[str, list[str]]
TagListFn = Callable[[SelectedTags, list[str]], list[str]]
TagRemoveFn = Callable[[SelectedTags, list[str], str], None]
TagAppendFn = Callable[[SelectedTags, list[str], str], None]
UniqFn = Callable[[list[str]], list[str]]


TEMPLATE_STYLE_BASE_MAP = {
    "真实感": "真实感",
    "商业摄影": "真实感",
    "时尚编辑": "真实感",
    "电影写实": "真实感",
    "私房写实": "真实感",
    "插画感": "插画感",
    "复古动画": "插画感",
    "CG感": "CG感",
    "东方赛博": "CG感",
    "硬表面科幻": "CG感",
    "古风": "古风",
    "国风电影": "古风",
    "武侠电影": "古风",
    "神话感": "神话感",
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
TEMPLATE_STYLE_BASE_MAP.update(EXPANDED_TEMPLATE_BASE_MAP)
BASE_TEMPLATE_STYLES = frozenset(TEMPLATE_STYLE_BASE_MAP.values())

_AUTO_NON_PERSON_SUBJECT_TAGS = {
    "机甲",
    "机械",
    "载具",
    "机器人",
    "战舰",
    "飞船",
    "工程机甲",
    "防御机甲",
    "侦查机甲",
    "步兵机甲",
    "装甲",
}
_AUTO_HUMAN_SUBJECT_TAGS = {
    "人物主体",
    "人物角色",
    "成年女性",
    "成年男性",
    "中年女性",
    "中年男性",
    "女性",
    "男性",
    "女人",
    "男人",
    "御姐",
}


def resolve_base_template_style(value: Any, *, default: str = "") -> str:
    cleaned = str(value or "").strip()
    return TEMPLATE_STYLE_BASE_MAP.get(cleaned, cleaned or str(default or "").strip())


@dataclass(frozen=True)
class StagePromptSkill:
    name: str
    phase: str
    enabled: Callable[[dict[str, Any], dict[str, Any]], bool]
    apply: Callable[..., None]


def _is_adult_mature(settings: dict[str, Any]) -> bool:
    return str(settings.get("标签反推模式", "") or "").strip() == "成人向成熟"


def _is_person_adult_mature(settings: dict[str, Any]) -> bool:
    if str(settings.get("主体类型", "自动") or "自动").strip() == "非人物主体":
        return False
    return _is_adult_mature(settings)


def _is_nsfw_strategy_enabled(settings: dict[str, Any], context: dict[str, Any]) -> bool:
    if str(settings.get("主体类型", "自动") or "自动").strip() == "非人物主体":
        return False
    return bool(settings.get("NSFW工作台启用", False)) or bool(settings.get("NSFW策略启用", False)) or _is_adult_mature(settings)


def _apply_auto_non_person_subject_resolution(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    settings: dict[str, Any],
    notes: list[str],
    context: dict[str, Any],
    collect_all_tags: TagListFn,
    **_: Any,
) -> None:
    subject_type = str(settings.get("主体类型", "自动") or "自动").strip()
    if subject_type not in {"", "自动"}:
        return

    all_tags = set(collect_all_tags(selected, custom_tags))
    non_person_tags = _AUTO_NON_PERSON_SUBJECT_TAGS | {
        str(tag).strip()
        for tag in context.get("non_person_subject_tags", set())
        if str(tag).strip()
    }
    if not (all_tags & non_person_tags):
        return

    human_tags = _AUTO_HUMAN_SUBJECT_TAGS | {
        str(tag).strip()
        for tag in context.get("human_identity_tags", set())
        if str(tag).strip()
    }
    human_tags.update(
        str(tag).strip()
        for tag in context.get("adult_mature_subject_anchors", set())
        if any(marker in str(tag) for marker in ("女性", "男性", "女人", "男人", "人物"))
    )
    if all_tags & human_tags:
        return

    settings["主体类型"] = "非人物主体"
    notes.append("Skill主体解析：自动模式检测到明确非人物主体，切换为非人物主体护栏，跳过人物与成人主体补锚。")


def _style_isolation_mode(settings: dict[str, Any]) -> str:
    mode = str(settings.get("风格隔离策略", "平衡收敛") or "平衡收敛").strip()
    return mode if mode in {"平衡收敛", "严格风格隔离", "允许风格漂移"} else "平衡收敛"


def _noise_tags(context: dict[str, Any]) -> set[str]:
    defaults = {
        "True",
        "False",
        "true",
        "false",
        "none",
        "null",
        "自动",
        "标准",
        "详细",
        "简洁",
    }
    noise = defaults | {str(tag).strip() for tag in context.get("prompt_noise_tags", set()) if str(tag).strip()}
    noise.discard("低保真")
    return noise


_MJ_PARAMETER_FRAGMENT_PATTERN = re.compile(
    r"^--(?:ar|s|stylize|chaos|weird|raw|hd|sd|niji|v|q|iw|sw|sv|ow|oref|sref|profile|p|seed|draft|tile|no|exp|pre)\b(?:\s+.+)?$",
    flags=re.IGNORECASE,
)
_MJ_PROFILE_CODE_PATTERN = re.compile(r"^(?:[a-z0-9]{6,10}|[0-9a-f]{8,})$", flags=re.IGNORECASE)
_UUID_FRAGMENT_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:[_-]?\d+)?$",
    flags=re.IGNORECASE,
)


def _looks_like_external_prompt_parameter_noise(tag: str) -> bool:
    text = str(tag or "").strip()
    if not text:
        return False
    compact = re.sub(r"\s+", "", text)
    if compact.casefold() in {"[]", "{}", "()", "（）", "【】", "null", "none", "undefined"}:
        return True
    if compact and not compact.strip("[]{}()（）【】"):
        return True
    if _MJ_PARAMETER_FRAGMENT_PATTERN.match(text) or _UUID_FRAGMENT_PATTERN.match(text):
        return True
    if text.startswith("--"):
        return True
    lowered = text.casefold()
    if lowered in {"profile", "preview", "pre", "raw", "hd", "ar 16:9", "ar 9:16"}:
        return True
    return False


def _custom_group_map(settings: dict[str, Any], context: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    mapping.update({str(key): str(value) for key, value in dict(context.get("skill_custom_group_map", {})).items()})
    if _is_person_adult_mature(settings):
        mapping.update({str(key): str(value) for key, value in dict(context.get("adult_mature_custom_group_map", {})).items()})
    return mapping


def _person_shot_tags(context: dict[str, Any]) -> set[str]:
    defaults = {
        "大全景",
        "大远景",
        "远景",
        "全景",
        "全景全身",
        "全身",
        "中景",
        "中景半身",
        "近景",
        "近景半身",
        "半身",
        "肩部以上特写",
        "面部特写",
        "特写",
        "局部特写",
    }
    return defaults | {str(tag).strip() for tag in context.get("person_shot_tags", set()) if str(tag).strip()}


def _quality_anchor_tags(context: dict[str, Any]) -> set[str]:
    defaults = {
        "16K",
        "8K",
        "高质量",
        "高细节",
        "材质细节丰富",
        "清晰对焦",
        "超清画质",
        "高分辨率",
        "真实材质",
        "自然解剖",
        "手部自然",
        "主体结构完整",
    }
    return defaults | {str(tag).strip() for tag in context.get("quality_anchor_tags", set()) if str(tag).strip()}


def _nsfw_signal_terms(context: dict[str, Any]) -> set[str]:
    defaults = {
        "成人向",
        "成人向成熟",
        "私房",
        "私密氛围",
        "成熟",
        "轻熟感",
        "高级性感",
        "内衣风",
        "吊带睡裙",
        "丝质睡袍",
        "湿身薄纱",
        "透肤薄纱",
        "贴身布料感",
        "镂空蕾丝内衣",
        "透明黑色纱裙",
        "短款皮质热裤",
        "紧身乳胶装",
        "蕾丝饰带缠绕",
        "渔网连体装",
        "情趣吊带袜",
        "透明睡袍",
        "情趣制服",
        "皮质束缚装",
        "欲念张力",
        "禁忌诱惑",
        "支配感",
        "情绪迷醉",
        "强烈感官氛围",
        "亲密互动",
        "成人动作",
        "成人器官",
        "乳房",
        "乳头",
        "外阴",
        "阴道",
        "阴蒂",
        "阴茎",
        "性交",
        "插入",
        "自慰",
        "潮吹",
        "脱衣动作",
        "舔唇表情",
        "弯腰姿态",
        "手部抚摸动作",
        "身体扭动",
        "胸部抚摸动作",
        "臀部慢摇",
        "低姿爬行动作",
        "成人道具参与",
        "跨坐互动",
        "从后拥抱",
        "口部亲密互动",
        "轻拍臀部互动",
        "推拉节奏互动",
        "亲密低语",
        "腿部打开姿态",
        "主从感跪姿互动",
    }
    return defaults | {str(tag).strip() for tag in context.get("nsfw_workspace_signal_terms", set()) if str(tag).strip()}


def _append_skill_anchor(
    selected: SelectedTags,
    custom_tags: list[str],
    tag: str,
    group_name: str,
    *,
    collect_all_tags: TagListFn,
    append_tag_to_state: TagAppendFn,
) -> bool:
    text = str(tag or "").strip()
    if not text or text in set(collect_all_tags(selected, custom_tags)):
        return False
    if group_name in selected:
        selected[group_name].append(text)
    else:
        append_tag_to_state(selected, custom_tags, text)
    return text in set(collect_all_tags(selected, custom_tags))


def _apply_default_person_full_body_guard(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    settings: dict[str, Any],
    notes: list[str],
    context: dict[str, Any],
    collect_all_tags: TagListFn,
    append_tag_to_state: TagAppendFn,
    **_: Any,
) -> None:
    if str(settings.get("主体类型", "自动") or "自动").strip() == "非人物主体":
        return
    if "构图视角" not in selected:
        return

    tags = set(collect_all_tags(selected, custom_tags))
    if tags & _person_shot_tags(context):
        return

    default_tag = str(context.get("default_person_shot_tag", "全景全身") or "全景全身").strip()
    if not default_tag or default_tag in tags:
        return
    append_tag_to_state(selected, custom_tags, default_tag)
    if default_tag in set(collect_all_tags(selected, custom_tags)):
        notes.append(f"Skill景别护栏：未检测到明确景别，默认补入 {default_tag}；用户已选近景/半身/中景/全身时不会覆盖。")


def _apply_global_detail_anchor_guard(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    settings: dict[str, Any],
    notes: list[str],
    context: dict[str, Any],
    collect_all_tags: TagListFn,
    append_tag_to_state: TagAppendFn,
    **_: Any,
) -> None:
    tags = set(collect_all_tags(selected, custom_tags))
    added: list[str] = []

    if "技术画质" in selected and not selected["技术画质"] and not (tags & _quality_anchor_tags(context)):
        quality_tag = str(context.get("default_quality_anchor_tag", "高细节") or "高细节").strip()
        if quality_tag and quality_tag not in tags:
            selected["技术画质"].append(quality_tag)
            tags = set(collect_all_tags(selected, custom_tags))
            if quality_tag in tags:
                added.append(quality_tag)

    subject_type = str(settings.get("主体类型", "自动") or "自动").strip()
    if (
        subject_type != "非人物主体"
        and "构图视角" in selected
        and ("全景全身" in tags or "全身" in tags)
        and "人物完整入镜" not in tags
    ):
        append_tag_to_state(selected, custom_tags, "人物完整入镜")
        tags = set(collect_all_tags(selected, custom_tags))
        if "人物完整入镜" in tags:
            added.append("人物完整入镜")

    if added:
        notes.append(f"Skill细节锚点：补入 {'、'.join(added)}，用于让模型展开完整画面与稳定结构；已选同类标签时不会重复补。")


def _apply_custom_tag_router(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    settings: dict[str, Any],
    notes: list[str],
    context: dict[str, Any],
    **_: Any,
) -> None:
    group_map = _custom_group_map(settings, context)
    moved: list[str] = []
    if not group_map:
        return

    for tag in list(custom_tags):
        target_group = str(group_map.get(tag, "") or "").strip()
        if not target_group or target_group not in selected:
            continue
        custom_tags[:] = [item for item in custom_tags if item != tag]
        if tag not in selected[target_group]:
            selected[target_group].append(tag)
            moved.append(f"{tag}->{target_group}")

    if not moved:
        return
    if _is_adult_mature(settings):
        notes.append(f"成人向分组归位：{'、'.join(moved)}。")
    else:
        notes.append(f"Skill标签归位：{'、'.join(moved)}。")


def _apply_prompt_noise_filter(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    notes: list[str],
    context: dict[str, Any],
    **_: Any,
) -> None:
    noise = _noise_tags(context)
    removed: list[str] = []
    for group_name in list(selected.keys()):
        kept: list[str] = []
        for tag in selected[group_name]:
            clean_tag = str(tag).strip()
            if clean_tag in noise or _looks_like_external_prompt_parameter_noise(clean_tag):
                removed.append(str(tag).strip())
                continue
            kept.append(tag)
        selected[group_name] = kept

    next_custom: list[str] = []
    for tag in custom_tags:
        clean_tag = str(tag).strip()
        if clean_tag in noise or _looks_like_external_prompt_parameter_noise(clean_tag):
            removed.append(str(tag).strip())
            continue
        next_custom.append(tag)
    custom_tags[:] = next_custom

    if removed:
        deduped = list(dict.fromkeys(removed))
        notes.append(f"Skill噪声清理：移除非画面控制词 {'、'.join(deduped)}。")


def _non_person_blocked_tags(context: dict[str, Any]) -> set[str]:
    blocked = {
        "成年人物主体",
        "人物主体",
        "人物角色",
        "人物完整入镜",
        "成年女性",
        "成年男性",
        "中年女性",
        "中年男性",
        "年轻成年女性",
        "青春感成年女性",
        "女人",
        "男性",
        "女性",
        "女孩",
        "少女",
        "模特",
        "国潮模特",
        "潮女模特",
        "影棚时尚女性",
        "书店女孩",
        "学生",
        "偶像",
        "公主",
        "女王",
        "神女",
        "女武士",
        "魔女",
        "祭司",
        "特工",
        "机械师",
        "长发",
        "黑长直",
        "银白长发",
        "中分短发",
        "短碎发",
        "高马尾",
        "盘发",
        "发髻",
        "披发",
        "湿发",
        "自然解剖",
        "手部自然",
        "空气感奶油肌",
        "冷白皮",
        "清透肌肤",
        "真实发丝",
    }
    for key in (
        "human_identity_tags",
        "adult_mature_subject_anchors",
        "hair_conflict_tags",
        "adult_mature_intimate_clothing",
        "modern_formal_clothing_tags",
        "ancient_clothing_tags",
        "intimate_clothing_tags",
    ):
        blocked.update(str(tag).strip() for tag in context.get(key, set()) if str(tag).strip())
    return blocked


def _apply_non_person_subject_guard(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    settings: dict[str, Any],
    notes: list[str],
    context: dict[str, Any],
    **_: Any,
) -> None:
    if str(settings.get("主体类型", "自动") or "自动").strip() != "非人物主体":
        return

    blocked = _non_person_blocked_tags(context)
    removed: list[str] = []
    for group_name in list(selected.keys()):
        kept: list[str] = []
        for tag in selected[group_name]:
            text = str(tag).strip()
            if text in blocked:
                removed.append(text)
                continue
            kept.append(tag)
        selected[group_name] = kept

    next_custom: list[str] = []
    for tag in custom_tags:
        text = str(tag).strip()
        if text in blocked:
            removed.append(text)
            continue
        next_custom.append(tag)
    custom_tags[:] = next_custom

    if "成人向表达" in selected and selected["成人向表达"]:
        removed.extend(str(tag).strip() for tag in selected["成人向表达"] if str(tag).strip())
        selected["成人向表达"] = []

    if removed:
        deduped = list(dict.fromkeys(removed))
        notes.append(f"非人物主体护栏：移除人物/成人/服装污染词 {'、'.join(deduped[:12])}。")


def _append_to_group_if_empty(
    selected: SelectedTags,
    group_name: str,
    tag: str,
) -> bool:
    text = str(tag or "").strip()
    if not text or group_name not in selected or selected[group_name]:
        return False
    selected[group_name].append(text)
    return True


def _apply_sparse_skill_scaffold(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    settings: dict[str, Any],
    notes: list[str],
    collect_all_tags: TagListFn,
    **_: Any,
) -> None:
    if str(settings.get("主体类型", "自动") or "自动").strip() == "非人物主体":
        return
    source = str(settings.get("模型来源", "") or "").strip()
    smart_text_enabled = bool(settings.get("智能文本匹配", False)) and bool(str(settings.get("智能文本输入", "") or "").strip())
    runtime_random_enabled = bool(settings.get("运行时随机标签", False))
    if source not in {"", "仅Skill"} or smart_text_enabled or runtime_random_enabled:
        return
    if str(settings.get("随机主题池", "自动") or "自动").strip() not in {"", "自动"}:
        return

    user_groups = ("主体", "画面风格", "成人向表达", "光影氛围", "动作姿态", "服装造型", "场景背景", "道具世界观")
    user_anchor_count = sum(len([tag for tag in selected.get(group, []) if str(tag).strip()]) for group in user_groups)
    meaningful_custom = [
        tag
        for tag in custom_tags
        if str(tag).strip() and not _looks_like_external_prompt_parameter_noise(str(tag).strip())
    ]
    if user_anchor_count > 0 or meaningful_custom:
        return

    configured_style = str(settings.get("模板风格", "自动") or "自动").strip() or "自动"
    scaffold_style = resolve_base_template_style(configured_style, default="真实感")
    if scaffold_style not in BASE_TEMPLATE_STYLES:
        scaffold_style = "真实感"

    added: list[str] = []
    for group_name, tag in (
        ("主体", "成年人物主体"),
        ("画面风格", scaffold_style),
        ("场景背景", "简洁室内"),
        ("光影氛围", "自然光"),
        ("动作姿态", "站姿挺拔"),
    ):
        if _append_to_group_if_empty(selected, group_name, tag):
            added.append(tag)

    if added:
        if configured_style == "自动":
            settings["模板风格"] = "真实感"
        notes.append(f"Skill空输入脚手架：补入 {'、'.join(added)}，避免仅输出空泛结构词；用户选择任一主体/风格/场景/动作后自动停用。")


def _apply_prompt_craft_source_guard(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    notes: list[str],
    context: dict[str, Any],
    collect_all_tags: TagListFn,
    **_: Any,
) -> None:
    """Keep external MJ-style source hints as guidance, not locked prompt content."""

    all_tags = collect_all_tags(selected, custom_tags)
    source_hits = [
        tag
        for tag in all_tags
        if any(
            cue in str(tag)
            for cue in ("电影剧照", "写实人像", "胶片", "古风电影", "武侠", "赛博", "机甲", "商业广告", "时尚编辑")
        )
    ]
    if not source_hits:
        return
    if context.get("_prompt_craft_source_guard_noted"):
        return
    context["_prompt_craft_source_guard_noted"] = True
    notes.append("Skill构图语义：参考素材只作为主体、环境、光线、媒介、镜头的写法指导；不会锁死固定码图、参数、场景或人物。")


def _resolve_runtime_random_target_style(
    settings: dict[str, Any],
    context: dict[str, Any],
    all_tags: list[str],
) -> str:
    explicit_style = str(settings.get("模板风格", "自动") or "自动").strip()
    if explicit_style and explicit_style != "自动":
        return resolve_base_template_style(explicit_style)

    style_families = {
        str(name): {str(tag).strip() for tag in tags if str(tag).strip()}
        for name, tags in dict(context.get("runtime_style_isolation_families", {})).items()
    }
    if not style_families:
        return ""

    scores = {
        style_name: sum(1 for tag in all_tags if tag in family_tags)
        for style_name, family_tags in style_families.items()
    }
    best_style = max(scores, key=scores.get) if scores else ""
    if scores.get(best_style, 0) > 0:
        return best_style

    # Theme pools are allowed to choose the primary medium when the pool has
    # not yet contributed a style tag (for example during an empty preview).
    theme_pool = str(settings.get("随机主题池", "自动") or "自动").strip()
    theme_defaults = {
        "古风园林": "古风", "武侠江湖": "古风", "国风": "古风",
        "洛可可宫廷": "神话感", "神话史诗": "神话感", "暗黑哥特": "神话感",
        "赛博工业": "CG感", "东方赛博": "CG感", "机甲科幻": "CG感",
        "废土荒原": "CG感", "复古插画": "插画感",
    }
    return theme_defaults.get(theme_pool, "真实感" if theme_pool not in {"", "自动"} else "")


def _apply_runtime_random_style_isolation(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    settings: dict[str, Any],
    notes: list[str],
    context: dict[str, Any],
    collect_all_tags: TagListFn,
    remove_tag_from_state: TagRemoveFn,
    **_: Any,
) -> None:
    all_tags = collect_all_tags(selected, custom_tags)
    target_style = _resolve_runtime_random_target_style(settings, context, all_tags)
    if not target_style:
        return

    style_families = {
        str(name): {str(tag).strip() for tag in tags if str(tag).strip()}
        for name, tags in dict(context.get("runtime_style_isolation_families", {})).items()
    }
    target_family = set(style_families.get(target_style, set()))
    if not target_family:
        return
    blocked_terms = {
        str(tag).strip()
        for tag in dict(context.get("style_positive_exclusion_terms", {})).get(target_style, ())
        if str(tag).strip()
    }
    cross_style_terms = {
        tag
        for style_name, family_tags in style_families.items()
        if style_name != target_style
        for tag in family_tags
    }
    mode = _style_isolation_mode(settings)
    removable_terms = (blocked_terms | cross_style_terms) - target_family

    # Balanced mode may retain one neutral texture bridge. Drift mode may
    # retain one deliberate secondary style track, while every other track is
    # still removed. This keeps the narrative medium coherent without making
    # all mixed-media prompts impossible.
    preserved_foreign: set[str] = set()
    if mode == "平衡收敛":
        bridge_hints = {
            str(tag).strip()
            for tag in context.get("style_bridge_hints", ("胶片感", "杂志感", "港风", "真实感", "照片级"))
            if str(tag).strip()
        }
        preserved_foreign = next(
            ({tag} for tag in all_tags if tag in cross_style_terms and tag in bridge_hints),
            set(),
        )
    elif mode == "允许风格漂移":
        secondary_scores = {
            style_name: sum(1 for tag in all_tags if tag in family_tags)
            for style_name, family_tags in style_families.items()
            if style_name != target_style
        }
        secondary_style = max(secondary_scores, key=secondary_scores.get) if secondary_scores else ""
        if secondary_scores.get(secondary_style, 0) > 0:
            secondary_family = style_families.get(secondary_style, set())
            preserved_foreign = next(
                ({tag} for tag in all_tags if tag in secondary_family),
                set(),
            )
    removable_terms -= preserved_foreign
    if not removable_terms:
        return

    removed: list[str] = []
    for tag in list(collect_all_tags(selected, custom_tags)):
        text = str(tag).strip()
        if text and text in removable_terms:
            remove_tag_from_state(selected, custom_tags, text)
            removed.append(text)

    if removed:
        notes.append(
            f"全局风格隔离（运行随机风格隔离兼容）：当前按 {target_style} 轨道生成，{mode}策略移除跨风格污染词 {'、'.join(dict.fromkeys(removed))}。"
        )


_DEFAULT_REPETITION_FAMILIES: tuple[dict[str, Any], ...] = (
    {
        "name": "写实风格",
        "tags": ("杂志编辑摄影", "杂志编辑风格", "时尚写真", "自然写实图像", "真实感", "照片级", "写实摄影"),
        "priority": ("杂志编辑摄影", "真实感", "照片级", "时尚写真", "自然写实图像", "杂志编辑风格", "写实摄影"),
        "limit": 3,
    },
    {
        "name": "人物景别",
        "tags": ("全景全身", "人物完整入镜", "脚部完整入镜", "全身", "全景", "远景"),
        "priority": ("全景全身", "人物完整入镜", "脚部完整入镜", "全身", "全景", "远景"),
        "limit": 2,
    },
    {
        "name": "近景景别",
        "tags": ("近景", "镜头近距离", "面部聚焦", "面部特写", "肩部以上特写", "特写", "局部特写"),
        "priority": ("近景", "面部聚焦", "镜头近距离", "面部特写", "肩部以上特写", "特写", "局部特写"),
        "limit": 2,
    },
    {
        "name": "画质细节",
        "tags": ("16K", "8K", "高质量", "高细节", "材质细节丰富", "清晰对焦", "超清画质", "高分辨率"),
        "priority": ("高质量", "高细节", "材质细节丰富", "清晰对焦", "16K", "8K", "超清画质", "高分辨率"),
        "limit": 4,
    },
    {
        "name": "镜头焦段",
        "tags": ("35mm镜头", "50mm标准镜头", "85mm人像镜头", "浅景深", "景深控制稳定"),
        "priority": ("50mm标准镜头", "85mm人像镜头", "35mm镜头", "浅景深", "景深控制稳定"),
        "limit": 2,
    },
)


def _apply_semantic_repetition_compactor(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    notes: list[str],
    context: dict[str, Any],
    collect_all_tags: TagListFn,
    remove_tag_from_state: TagRemoveFn,
    **_: Any,
) -> None:
    raw_families = context.get("skill_repetition_families") or _DEFAULT_REPETITION_FAMILIES
    all_tags = collect_all_tags(selected, custom_tags)
    all_index = {tag: index for index, tag in enumerate(all_tags)}
    compacted: list[str] = []

    for raw_family in raw_families:
        if not isinstance(raw_family, dict):
            continue
        name = str(raw_family.get("name", "同类标签") or "同类标签")
        family_tags = tuple(str(tag).strip() for tag in raw_family.get("tags", ()) if str(tag).strip())
        if not family_tags:
            continue
        try:
            limit = max(1, int(raw_family.get("limit", 2)))
        except Exception:
            limit = 2
        family_set = set(family_tags)
        hits = [tag for tag in all_tags if tag in family_set]
        if len(hits) <= limit:
            continue

        priority = [str(tag).strip() for tag in raw_family.get("priority", family_tags) if str(tag).strip()]
        priority_index = {tag: index for index, tag in enumerate(priority)}
        ranked = sorted(
            hits,
            key=lambda tag: (priority_index.get(tag, len(priority)), all_index.get(tag, 0)),
        )
        keep = set(ranked[:limit])
        removed = [tag for tag in hits if tag not in keep]
        for tag in removed:
            remove_tag_from_state(selected, custom_tags, tag)
        if removed:
            compacted.append(f"{name} 保留 {'、'.join(ranked[:limit])}")

    if compacted:
        notes.append(f"Skill重复收敛：{'；'.join(compacted)}，避免同类提示词重复叠加。")


_DIVERSITY_DIMENSION_ORDER: tuple[tuple[str, str], ...] = (
    ("主体", "主体身份"),
    ("画面风格", "媒介风格"),
    ("成人向表达", "成熟表达"),
    ("服装造型", "服装材质"),
    ("场景背景", "场景空间"),
    ("动作姿态", "动作姿态"),
    ("光影氛围", "光影色彩"),
    ("道具世界观", "持物道具"),
    ("构图视角", "镜头组织"),
    ("技术画质", "画质结构"),
)


def _apply_global_nonlocking_diversity_director(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    settings: dict[str, Any],
    notes: list[str],
    collect_all_tags: TagListFn,
    **_: Any,
) -> None:
    """Publish a global non-locking diversity plan without changing user tags."""

    all_tags = collect_all_tags(selected, custom_tags)
    if not all_tags:
        return

    anchored_labels = [
        label
        for group_name, label in _DIVERSITY_DIMENSION_ORDER
        if selected.get(group_name)
    ]
    flexible_labels = [
        label
        for group_name, label in _DIVERSITY_DIMENSION_ORDER
        if not selected.get(group_name)
    ]
    if custom_tags:
        anchored_labels.append("自定义补充")

    runtime_mode = str(settings.get("运行时随机模式解析结果", "") or settings.get("运行时随机模式", "") or "").strip()
    signals: list[str] = []
    if bool(settings.get("运行时随机标签", False)):
        signals.append(f"运行时随机:{runtime_mode or '自动判断'}")
    if bool(settings.get("智能文本匹配", False)):
        signals.append("智能文本")
    if bool(settings.get("NSFW工作台启用", False)) or bool(settings.get("NSFW策略启用", False)):
        signals.append("NSFW工作台")
    if bool(settings.get("标签块编排启用", False)):
        signals.append("标签块编排")

    anchored_text = "、".join(dict.fromkeys(anchored_labels[:7])) or "暂无强锚点"
    flexible_text = "、".join(dict.fromkeys(flexible_labels[:7])) or "镜头组织、材质层次、空间纵深、动作重心、局部道具关系"
    signal_text = "、".join(signals) if signals else "普通正向"
    strategy = (
        f"{signal_text}；标签作为素材锚点而非固定模板；已选维度：{anchored_text}；"
        f"优先变化未明确锁定维度：{flexible_text}；连续生成、随机运行时、智能文本或 API 后置时，"
        "至少让三个视觉维度形成实质差异，不复读上一轮主体/场景/服装/动作/光影组合。"
    )
    settings["Skill动态变化策略"] = strategy
    should_note = bool(signals) or bool(settings.get("最近提示词指纹"))
    if should_note and not any("Skill动态变化" in str(note) for note in notes):
        notes.append(f"Skill动态变化：{signal_text}，标签只作锚点，优先变化 {flexible_text}。")


def _apply_adult_mature_group_compactor(
    *,
    selected: SelectedTags,
    notes: list[str],
    context: dict[str, Any],
    uniq: UniqFn,
    **_: Any,
) -> None:
    group_limits = dict(context.get("adult_mature_group_limits", {}))
    group_priorities = dict(context.get("adult_mature_group_priorities", {}))
    compacted_groups: list[str] = []

    for group_name, raw_limit in group_limits.items():
        group_key = str(group_name)
        if group_key not in selected:
            continue
        try:
            limit = max(0, int(raw_limit))
        except Exception:
            continue
        if not limit:
            continue

        bucket = uniq(list(selected[group_key]))
        priority = [str(tag) for tag in group_priorities.get(group_key, [])]
        priority_index = {tag: index for index, tag in enumerate(priority)}
        original_index = {tag: index for index, tag in enumerate(bucket)}
        bucket.sort(key=lambda tag: (priority_index.get(tag, len(priority)), original_index.get(tag, 0)))
        kept = bucket[:limit]
        if kept != selected[group_key]:
            selected[group_key] = kept
        if len(bucket) > limit:
            compacted_groups.append(f"{group_key} 保留 {'、'.join(kept)}")

    if compacted_groups:
        notes.append(f"成人向分组精简：{'；'.join(compacted_groups)}。")


def _apply_adult_mature_scene_consistency(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    notes: list[str],
    context: dict[str, Any],
    collect_all_tags: TagListFn,
    remove_tag_from_state: TagRemoveFn,
    **_: Any,
) -> None:
    scene_families = context.get("adult_mature_scene_families", {})
    scene_priority = list(context.get("adult_mature_scene_priority", []))
    if not isinstance(scene_families, dict) or not scene_families:
        return

    all_tags_ordered = collect_all_tags(selected, custom_tags)
    family_hits: dict[str, list[str]] = {}
    for family_name, family_tags in scene_families.items():
        family_set = set(family_tags)
        hits = [tag for tag in all_tags_ordered if tag in family_set]
        if hits:
            family_hits[str(family_name)] = hits

    if len(family_hits) <= 1:
        return

    chosen_family = next((name for name in scene_priority if name in family_hits), next(iter(family_hits)))
    removed_scenes: list[str] = []
    for family_name, hits in family_hits.items():
        if family_name == chosen_family:
            continue
        for scene_tag in hits:
            remove_tag_from_state(selected, custom_tags, scene_tag)
            removed_scenes.append(scene_tag)

    if removed_scenes:
        kept_scene = "、".join(family_hits.get(chosen_family, [])[:3])
        notes.append(f"成人向场景收敛：保留 {kept_scene} 主场景，移除拼贴场景 {'、'.join(removed_scenes)}。")


def _apply_nsfw_workspace_strategy(
    *,
    selected: SelectedTags,
    custom_tags: list[str],
    settings: dict[str, Any],
    notes: list[str],
    context: dict[str, Any],
    collect_all_tags: TagListFn,
    append_tag_to_state: TagAppendFn,
    **_: Any,
) -> None:
    all_tags = collect_all_tags(selected, custom_tags)
    signal_terms = _nsfw_signal_terms(context)
    signal_hits = [tag for tag in all_tags if tag in signal_terms]
    explicit_hits = [
        tag
        for tag in signal_hits
        if tag in {"乳房", "乳头", "外阴", "阴道", "阴蒂", "阴茎", "性交", "插入", "自慰", "潮吹", "成人器官", "成人动作"}
    ]
    if not signal_hits and not bool(settings.get("NSFW工作台启用", False)) and not _is_adult_mature(settings):
        return

    changes: list[str] = []
    subject_anchors = {str(tag).strip() for tag in context.get("adult_mature_subject_anchors", set()) if str(tag).strip()}
    default_subject_anchor = str(context.get("adult_mature_default_subject_anchor", "成年女性") or "成年女性").strip()
    if default_subject_anchor and not (set(all_tags) & subject_anchors):
        if _append_skill_anchor(
            selected,
            custom_tags,
            default_subject_anchor,
            "主体",
            collect_all_tags=collect_all_tags,
            append_tag_to_state=append_tag_to_state,
        ):
            changes.append(f"成年主体:{default_subject_anchor}")
            all_tags = collect_all_tags(selected, custom_tags)

    stable_shot = str(context.get("adult_mature_stable_shot_tag", "") or context.get("default_person_shot_tag", "全景全身") or "全景全身").strip()
    shot_hits = [tag for tag in all_tags if tag in _person_shot_tags(context)]
    if stable_shot and not shot_hits:
        if _append_skill_anchor(
            selected,
            custom_tags,
            stable_shot,
            "构图视角",
            collect_all_tags=collect_all_tags,
            append_tag_to_state=append_tag_to_state,
        ):
            changes.append(f"默认景别:{stable_shot}")
            all_tags = collect_all_tags(selected, custom_tags)

    if {"全景全身", "全身", stable_shot} & set(all_tags) and "人物完整入镜" not in set(all_tags):
        if _append_skill_anchor(
            selected,
            custom_tags,
            "人物完整入镜",
            "构图视角",
            collect_all_tags=collect_all_tags,
            append_tag_to_state=append_tag_to_state,
        ):
            changes.append("完整入镜")
            all_tags = collect_all_tags(selected, custom_tags)

    quality_tags = _quality_anchor_tags(context)
    if "技术画质" in selected and not (set(all_tags) & quality_tags):
        quality_anchor = str(context.get("default_quality_anchor_tag", "高细节") or "高细节").strip()
        if quality_anchor and _append_skill_anchor(
            selected,
            custom_tags,
            quality_anchor,
            "技术画质",
            collect_all_tags=collect_all_tags,
            append_tag_to_state=append_tag_to_state,
        ):
            changes.append(f"质量锚点:{quality_anchor}")
            all_tags = collect_all_tags(selected, custom_tags)

    if bool(settings.get("NSFW工作台启用", False)):
        source = "工作台启用"
    elif str(settings.get("NSFW策略来源", "") or "").strip():
        source = str(settings.get("NSFW策略来源", "") or "").strip()
    else:
        source = "成人向成熟"
    intensity = "显式成人字段" if explicit_hits else ("成熟氛围字段" if signal_hits else "策略模式")
    change_text = "、".join(changes) if changes else "保留已有锚点"
    settings["NSFW策略解析结果"] = f"{source}/{intensity}/{change_text}"
    notes.append(f"NSFW Skill策略：{source}，识别{intensity}，{change_text}；保留工作台自选标签，只补稳定锚点，不锁死风格。")


_STAGE_PROMPT_SKILLS: tuple[StagePromptSkill, ...] = (
    StagePromptSkill(
        name="prompt_noise_filter",
        phase="early_normalize",
        enabled=lambda settings, context: True,
        apply=_apply_prompt_noise_filter,
    ),
    StagePromptSkill(
        name="auto_non_person_subject_resolution",
        phase="early_normalize",
        enabled=lambda settings, context: str(settings.get("主体类型", "自动") or "自动").strip() in {"", "自动"},
        apply=_apply_auto_non_person_subject_resolution,
    ),
    StagePromptSkill(
        name="prompt_craft_source_guard",
        phase="early_normalize",
        enabled=lambda settings, context: True,
        apply=_apply_prompt_craft_source_guard,
    ),
    StagePromptSkill(
        name="runtime_random_style_isolation",
        phase="final_normalize",
        enabled=lambda settings, context: True,
        apply=_apply_runtime_random_style_isolation,
    ),
    StagePromptSkill(
        name="custom_tag_router",
        phase="early_normalize",
        enabled=lambda settings, context: bool(_custom_group_map(settings, context)),
        apply=_apply_custom_tag_router,
    ),
    StagePromptSkill(
        name="non_person_subject_guard",
        phase="early_normalize",
        enabled=lambda settings, context: str(settings.get("主体类型", "自动") or "自动").strip() == "非人物主体",
        apply=_apply_non_person_subject_guard,
    ),
    StagePromptSkill(
        name="sparse_skill_scaffold",
        phase="early_normalize",
        enabled=lambda settings, context: True,
        apply=_apply_sparse_skill_scaffold,
    ),
    StagePromptSkill(
        name="default_person_full_body_guard",
        phase="early_normalize",
        enabled=lambda settings, context: True,
        apply=_apply_default_person_full_body_guard,
    ),
    StagePromptSkill(
        name="global_detail_anchor_guard",
        phase="early_normalize",
        enabled=lambda settings, context: True,
        apply=_apply_global_detail_anchor_guard,
    ),
    StagePromptSkill(
        name="semantic_repetition_compactor",
        phase="early_normalize",
        enabled=lambda settings, context: True,
        apply=_apply_semantic_repetition_compactor,
    ),
    StagePromptSkill(
        name="global_nonlocking_diversity_director",
        phase="early_normalize",
        enabled=lambda settings, context: True,
        apply=_apply_global_nonlocking_diversity_director,
    ),
    StagePromptSkill(
        name="adult_mature_scene_consistency",
        phase="mid_normalize",
        enabled=lambda settings, context: _is_person_adult_mature(settings),
        apply=_apply_adult_mature_scene_consistency,
    ),
    StagePromptSkill(
        name="nsfw_workspace_strategy",
        phase="final_normalize",
        enabled=_is_nsfw_strategy_enabled,
        apply=_apply_nsfw_workspace_strategy,
    ),
    StagePromptSkill(
        name="non_person_subject_final_guard",
        phase="final_normalize",
        enabled=lambda settings, context: str(settings.get("主体类型", "自动") or "自动").strip() == "非人物主体",
        apply=_apply_non_person_subject_guard,
    ),
    StagePromptSkill(
        name="adult_mature_group_compactor",
        phase="final_normalize",
        enabled=lambda settings, context: _is_person_adult_mature(settings),
        apply=_apply_adult_mature_group_compactor,
    ),
)


def apply_stage_prompt_skills(
    selected: SelectedTags,
    custom_tags: list[str],
    settings: dict[str, Any],
    notes: list[str],
    *,
    phase: str,
    collect_all_tags: TagListFn,
    remove_tag_from_state: TagRemoveFn,
    append_tag_to_state: TagAppendFn,
    uniq: UniqFn,
    context: dict[str, Any],
) -> None:
    """Run enabled prompt skills for the current normalization phase."""

    for skill in _STAGE_PROMPT_SKILLS:
        if skill.phase != phase or not skill.enabled(settings, context):
            continue
        skill.apply(
            selected=selected,
            custom_tags=custom_tags,
            settings=settings,
            notes=notes,
            context=context,
            collect_all_tags=collect_all_tags,
            remove_tag_from_state=remove_tag_from_state,
            append_tag_to_state=append_tag_to_state,
            uniq=uniq,
        )


def list_stage_prompt_skills() -> list[dict[str, str]]:
    return [{"name": skill.name, "phase": skill.phase} for skill in _STAGE_PROMPT_SKILLS]
