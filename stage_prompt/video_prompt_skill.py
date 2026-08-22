# -*- coding: utf-8 -*-
"""Natural-language video prompt skill built from the normalized stage state."""

from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from typing import Any, Mapping, Sequence

try:
    from .narrative import (
        build_narrative_plan,
        storyboard_number_token,
        storyboard_phase_token,
        storyboard_phases_are_ordered,
    )
except Exception:  # pragma: no cover - direct file loading in focused tests
    from stage_prompt_narrative_test import (  # type: ignore
        build_narrative_plan,
        storyboard_number_token,
        storyboard_phase_token,
        storyboard_phases_are_ordered,
    )


VIDEO_PROMPT_SKILL_VERSION = "video-prompt-skill-v11"
VIDEO_PROMPT_DURATION_SECONDS = 8
VIDEO_PROMPT_MIN_CHARS_ZH = 0  # Compatibility export: text length has been unbounded since v4.
VIDEO_PROMPT_MAX_CHARS_ZH = 0  # Zero means unbounded.
VIDEO_PROMPT_MIN_STORYBOARD_PARAGRAPHS = 3
VIDEO_PROMPT_TARGET_MODEL_OPTIONS = ("通用", "H3", "Wan", "LTX", "Seedance", "自定义")
VIDEO_PROMPT_INPUT_MODE_OPTIONS = ("T2V", "I2V", "FL2V", "L2V", "Ref2V")
VIDEO_PROMPT_SHOT_COUNT_OPTIONS = ("自动", "单镜头", "短动作", "标准剧情", "长剧情")
VIDEO_PROMPT_MODEL_PROFILES: dict[str, dict[str, Any]] = {
    "通用": {
        "target_model": "通用",
        "input_mode": "T2V",
        "timeline": "optional",
        "audio_schema": "inline_natural_language",
        "continuity": "subject_scene_prop_lighting_axis",
    },
    "H3": {
        "target_model": "H3",
        "input_mode": "T2V",
        "timeline": "recommended",
        "audio_schema": "overall_soundscape_dialogue_music",
        "continuity": "reference_labels_keyframes_lighting_audio_bridge",
    },
    "Wan": {
        "target_model": "Wan",
        "input_mode": "T2V",
        "timeline": "optional",
        "audio_schema": "inline_natural_language",
        "continuity": "motion_direction_subject_identity_camera_axis",
    },
    "LTX": {
        "target_model": "LTX",
        "input_mode": "T2V",
        "timeline": "recommended",
        "audio_schema": "inline_natural_language",
        "continuity": "motion_path_keyframe_handoff",
    },
    "Seedance": {
        "target_model": "Seedance",
        "input_mode": "T2V",
        "timeline": "recommended",
        "audio_schema": "inline_natural_language",
        "continuity": "cinematic_camera_performance_spatial_handoff",
    },
    "自定义": {
        "target_model": "自定义",
        "input_mode": "T2V",
        "timeline": "optional",
        "audio_schema": "inline_natural_language",
        "continuity": "preserve_explicit_creative_spine",
    },
}
VIDEO_PROMPT_TIMELINE_SEGMENTS = (
    (0, 2),
    (2, 4),
    (4, 6),
    (6, 7),
    (7, 8),
)


def _setting_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    normalized = str(value or "").strip().casefold()
    if normalized in {"1", "true", "yes", "on", "开启", "开", "是"}:
        return True
    if normalized in {"0", "false", "no", "off", "关闭", "关", "否", "未启用"}:
        return False
    return default


def resolve_video_shot_count(settings: Mapping[str, Any] | None) -> int:
    """Resolve a bounded storyboard size from explicit mode or task intent."""

    source = settings or {}
    mode = str(source.get("视频提示词镜头段数", "自动") or "自动").strip()
    explicit = {"单镜头": 1, "短动作": 3, "标准剧情": 5, "长剧情": 7}
    if mode in explicit:
        return explicit[mode]
    task_type = str((source.get("智能任务意图") or {}).get("task_type", "") or "").casefold()
    if any(marker in task_type for marker in ("single_shot", "single-shot", "one_shot")):
        return 1
    if any(marker in task_type for marker in ("short_action", "short-action")):
        return 3
    if any(marker in task_type for marker in ("long_form", "long-form", "episodic")):
        return 7
    return 5


def _timeline_segments_for_count(count: int) -> tuple[tuple[float, float], ...]:
    if count == 5:
        return VIDEO_PROMPT_TIMELINE_SEGMENTS
    unit = VIDEO_PROMPT_DURATION_SECONDS / max(1, count)
    return tuple((round(index * unit, 2), round((index + 1) * unit, 2)) for index in range(count))


def _format_timecode(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def resolve_video_prompt_profile(settings: Mapping[str, Any] | None) -> dict[str, Any]:
    """Resolve video target metadata while keeping the generic prompt contract stable."""

    source = settings or {}
    target = str(source.get("视频提示词目标模型", "通用") or "通用").strip()
    input_mode = str(source.get("视频提示词输入模式", "T2V") or "T2V").strip()
    if target not in VIDEO_PROMPT_MODEL_PROFILES:
        target = "通用"
    if input_mode not in VIDEO_PROMPT_INPUT_MODE_OPTIONS:
        input_mode = "T2V"
    requested_timeline = _setting_bool(source.get("视频提示词启用时间轴", False))
    timeline_enabled = requested_timeline and target != "通用"
    shot_count = resolve_video_shot_count(source)
    segments = _timeline_segments_for_count(shot_count)
    subject_type = str(
        source.get("主体类型解析结果", source.get("主体类型", "自动")) or "自动"
    ).strip()
    subject_kind = "non_person" if subject_type == "非人物主体" else "person_or_auto"
    return {
        **VIDEO_PROMPT_MODEL_PROFILES[target],
        "target_model": target,
        "input_mode": input_mode,
        "timeline_enabled": timeline_enabled,
        "shot_count": shot_count,
        "shot_count_mode": str(source.get("视频提示词镜头段数", "自动") or "自动"),
        "subject_kind": subject_kind,
        "timeline_segments": [
            {"start": start, "end": end, "label": f"{_format_timecode(start)}-{_format_timecode(end)}s"}
            for start, end in segments
        ] if timeline_enabled else [],
        "duration_seconds": VIDEO_PROMPT_DURATION_SECONDS if timeline_enabled else None,
    }


VIDEO_PROMPT_MODEL_SYSTEM_TEMPLATE = """
你是 Qwen TE 的视频提示词后置导演 Skill。输入已经是独立视频 Skill 生成的可靠分镜故事底稿，你负责在同一剧情主线上把它润色得更自然、更具体、更适合视频生成。

硬规则：
1. 只输出最终视频提示词正文，不输出分析、思考过程、Markdown、标签列表、参数或“提示词：”。
2. 输出至少三段分镜；每段以“分镜一/二/三……”或“Shot 1/2/3...”开头，从 1 连续编号，不得重复、倒序或跳号。括号中的建立、触发、行动、升级、收束阶段标签也必须按剧情顺序对应，不得把收束写在开场或把触发写在高潮之后。每段使用完整自然语言写清景别或机位、镜头运动、主体动作、环境或光影反馈以及与前后分镜的承接关系。
3. 所有分镜共同组成一条完整故事：建立处境与动机，出现触发事件，主体作出回应，局势升级并形成视觉高潮，最后给出结果或开放结尾。不得把互不相关的镜头拼在一起。
4. 严格保留底稿中的主体、服装、场景、动作、道具、风格、光影和声音锚点；首镜明确建立主体、服装、主场景和关键道具，后续每镜都要用全称、代词、同一空间参照或可见状态变化保持它们可追踪。可以在故事需要时改变景别和机位，也允许有动作因果的服装撕裂、沾湿、脱落或明确换装，但不得无理由换人、换地点、换服装，或让道具凭空出现、消失。
5. 使用连贯自然语言，不堆关键词，不复述规则，不写无法直接拍摄的抽象评价。每段必须是可独立拍摄、又能承接下一段的分镜描述。
6. 不限制正文总字数、单段字数或英文单词数；长度由剧情和分镜需要决定。正文仍不得写具体秒数或时长参数。
7. 输入包含动作结果阶段时，必须把结果写成既有动作的因果结果，不得拆成独立标签或无来源事件；结果前后固定接触点、人物数量、镜头轴线与结束状态，不得新增人物、地点、道具、接触关系或跳轴镜头。
""".strip()

_EMPTY_VALUES = {"", "无", "自动", "未启用", "none", "null", "undefined"}
_META_MARKERS = (
    "thinking process",
    "output requirements",
    "prompt requirements",
    "system prompt",
    "提示词要求",
    "输出要求",
    "任务分析",
    "思考过程",
    "不要输出",
    "必须输出",
    "标签解析",
)
_DURATION_EXPRESSION_PATTERN = re.compile(
    r"(?:(?:\d+|[一二三四五六七八九十两几]+)\s*秒钟?|\d+(?:\.\d+)?\s*(?:s|secs?|seconds?)\b)",
    flags=re.IGNORECASE,
)
_CAMERA_MOVES_ZH = (
    "以稳定的低速跟拍贴着主体前进",
    "从环境中景缓慢推近到主体的动作细节",
    "沿主体的移动方向做一次平稳横移",
    "保持见证者距离，轻微向前推进",
)
_CAMERA_MOVES_EN = (
    "tracks the subject at a steady, restrained pace",
    "makes one slow push from the environment into the action",
    "moves laterally once along the direction of travel",
    "holds a witness-like distance and advances gently",
)


def _clean(value: Any, *, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ，,。；;：:|/\\")
    if not text or text.casefold() in _EMPTY_VALUES:
        return ""
    lowered = text.casefold()
    if any(marker in lowered for marker in _META_MARKERS):
        return ""
    text = re.sub(r"(?:^|\s)--[a-z][\w-]*(?:\s+\S+)?", "", text, flags=re.IGNORECASE).strip()
    return text[:limit].rstrip(" ，,。；;：:")


def _unique_values(values: Any, *, limit: int = 3) -> list[str]:
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for raw in values:
        text = _clean(raw, limit=96)
        key = re.sub(r"[\s，,。；;：:、]+", "", text).casefold()
        if not text or not key or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _normalized_groups(
    selected: Mapping[str, Sequence[Any]] | None,
    custom_tags: Sequence[Any] | None,
    settings: Mapping[str, Any],
    *,
    include_preferences: bool = False,
) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    contract = settings.get("全局创作主线合同")
    contract_groups = contract.get("groups") if isinstance(contract, dict) else None
    source_groups = contract_groups if isinstance(contract_groups, dict) else (selected or {})
    for name, values in source_groups.items():
        cleaned = _unique_values(values, limit=4)
        if cleaned:
            groups[str(name)] = cleaned
    custom = _unique_values(custom_tags, limit=4)
    if custom and "自定义补充" not in groups:
        groups["自定义补充"] = custom
    if include_preferences:
        for hint_key, limit in (("智能关系补全", 2), ("智能偏好应用", 1)):
            hint_groups = settings.get(hint_key)
            if not isinstance(hint_groups, dict):
                continue
            merge_relation_hints = bool(
                hint_key == "智能关系补全" and settings.get("智能关系补全并入显式道具", False)
            )
            for name, values in hint_groups.items():
                group_name = str(name)
                if groups.get(group_name) and (hint_key != "智能关系补全" or not merge_relation_hints):
                    continue
                cleaned = _unique_values(values, limit=limit)
                if cleaned:
                    if hint_key == "智能关系补全" and merge_relation_hints and groups.get(group_name):
                        existing = list(groups.get(group_name, []))
                        existing_keys = {str(item).casefold() for item in existing}
                        groups[group_name] = (existing + [
                            item for item in cleaned if item.casefold() not in existing_keys
                        ])[:5]
                    else:
                        groups[group_name] = cleaned
    return groups


def video_prompt_required_anchors(
    selected: Mapping[str, Sequence[Any]] | None,
    custom_tags: Sequence[Any] | None,
    settings: Mapping[str, Any],
) -> list[str]:
    """Return explicit story anchors that a model-refined video prompt must retain."""

    groups = _normalized_groups(selected, custom_tags, settings)
    anchors: list[str] = []
    for name in ("主体", "场景背景", "动作姿态", "服装造型", "道具世界观"):
        values = groups.get(name, [])
        if not values:
            continue
        anchor = _clean(values[0], limit=96)
        if anchor and anchor not in anchors:
            anchors.append(anchor)
    result_contract = _video_result_contract(settings)
    if result_contract:
        english = str(settings.get("提示词语言", "纯中文") or "纯中文").strip() == "纯英文"
        for anchor in _video_result_required_anchors(result_contract, english=english):
            if anchor and anchor not in anchors:
                anchors.append(anchor)
    return anchors


def video_prompt_anchor_roles(
    selected: Mapping[str, Sequence[Any]] | None,
    custom_tags: Sequence[Any] | None,
    settings: Mapping[str, Any],
) -> dict[str, list[str]]:
    """Return model-validation anchors grouped by their narrative role."""

    groups = _normalized_groups(selected, custom_tags, settings)
    role_groups = (
        ("subject", "主体"),
        ("scene", "场景背景"),
        ("action", "动作姿态"),
        ("outfit", "服装造型"),
        ("prop", "道具世界观"),
    )
    result: dict[str, list[str]] = {}
    for role, group_name in role_groups:
        values = groups.get(group_name, [])
        if not values:
            continue
        anchor = _clean(values[0], limit=96)
        if anchor:
            result[role] = [anchor]
    result_contract = _video_result_contract(settings)
    if result_contract:
        english = str(settings.get("提示词语言", "纯中文") or "纯中文").strip() == "纯英文"
        result["result"] = _video_result_required_anchors(result_contract, english=english)
    return result


def _first(groups: Mapping[str, list[str]], name: str, fallback: str = "") -> str:
    values = groups.get(name, [])
    return values[0] if values else fallback


def _series(groups: Mapping[str, list[str]], name: str, *, limit: int = 4) -> str:
    values = groups.get(name, [])[: max(1, int(limit))]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    return "、".join(values[:-1]) + "和" + values[-1]


def _video_result_contract(settings: Mapping[str, Any]) -> dict[str, Any]:
    raw = settings.get("视频提示词结果合同")
    if not isinstance(raw, Mapping):
        raw = settings.get("NSFW结果合同")
    if not isinstance(raw, Mapping) or not bool(raw.get("enabled", False)):
        return {}
    return dict(raw)


def _video_result_required_anchors(
    contract: Mapping[str, Any],
    *,
    english: bool,
) -> list[str]:
    if english:
        count = max(1, int(contract.get("person_count", 1) or 1))
        return [
            "fixed contact points",
            f"participant count remains {count}",
            "camera axis does not change",
            "ending state remains traceable",
        ]
    anchors = _unique_values(contract.get("required_anchors"), limit=8)
    marker_anchors = {
        "潮吹": "潮吹仅作为当前女性刺激动作的结果",
        "射精": "射精仅作为当前男性刺激动作的结果",
        "体液": "其他体液仅出现在当前接触区域",
    }
    for marker in contract.get("markers", []) if isinstance(contract.get("markers"), list) else []:
        anchor = marker_anchors.get(str(marker))
        if anchor and anchor not in anchors:
            anchors.append(anchor)
    return anchors


def _video_result_phrases_zh(contract: Mapping[str, Any]) -> dict[str, str]:
    contact_points = _unique_values(contract.get("contact_points"), limit=8) or ["当前既有接触点"]
    contact_text = "、".join(contact_points)
    person_count = max(1, int(contract.get("person_count", 1) or 1))
    action_contract = _clean(contract.get("action_contract"), limit=800)
    result_text = _clean(contract.get("text"), limit=1600)
    camera_axis = _clean(contract.get("camera_axis"), limit=180) or "沿当前镜头轴线保持不变，不换轴、不跳切"
    end_state = _clean(contract.get("end_state"), limit=420) or (
        f"动作结束后保持原有姿态与空间关系，结果只停留在{contact_text}"
    )
    continuity = _clean(contract.get("continuity_clause"), limit=300) or (
        "结果发生前后保持原有姿态、接触点、人物数量与镜头轴线，结束状态能够连续追踪"
    )
    return {
        "setup": (
            f"画面从一开始就把既有动作关系交代清楚：{action_contract}。"
            f"固定接触点为{contact_text}，人物数量固定为{person_count}名，所有人的身份与空间位置保持可辨。"
        ),
        "trace": (
            f"过渡中仍以{contact_text}为唯一接触区域，人物数量不变，既有主客体关系持续可见。"
        ),
        "action": f"动作沿既有接触方向继续，{continuity}；镜头{camera_axis}。",
        "result": f"{result_text}。结果只由上一分镜的连续动作引发，画面不另起事件。",
        "ending": f"{end_state}，结束状态能够连续追踪；镜头{camera_axis}。",
    }


def _video_result_phrases_en(contract: Mapping[str, Any]) -> dict[str, str]:
    point_names = {
        "外阴": "vulva",
        "阴蒂": "clitoris",
        "阴道": "vagina",
        "肛门": "anus",
        "阴茎": "penis",
        "口部": "mouth",
        "当前既有接触点": "the established contact area",
    }
    raw_points = contract.get("contact_points", [])
    points = [point_names.get(str(point), "the established contact area") for point in raw_points] if isinstance(raw_points, list) else []
    points = list(dict.fromkeys(points)) or ["the established contact area"]
    contact_text = ", ".join(points)
    count = max(1, int(contract.get("person_count", 1) or 1))
    types = set(str(value) for value in contract.get("types", []) if str(value))
    result_events: list[str] = []
    if "female_stimulation_squirt" in types:
        result_events.append("squirting occurs only as the result of the established female stimulation")
    if "male_stimulation_ejaculation" in types:
        result_events.append("ejaculation occurs only as the result of the established male stimulation")
    if "controlled_fluid" in types:
        result_events.append("other fluid remains limited to the established contact area and existing surfaces")
    event_text = "; ".join(result_events) or "the visible result follows only from the established action"
    return {
        "setup": (
            f"Result continuity begins with fixed contact points at {contact_text}; "
            f"participant count remains {count}, and every identity and spatial relation stays readable."
        ),
        "trace": "The same contact relation remains visible through the transition without adding a person, place, prop, or action branch.",
        "action": "The movement continues through the same contact direction, and the camera axis does not change or jump across the action.",
        "result": f"At the visual climax, {event_text}; the result does not become a separate event.",
        "ending": "The original pose, contact relation, participant count, and spatial order remain intact, so the ending state remains traceable.",
    }


def _primary_composition(groups: Mapping[str, list[str]]) -> str:
    values = groups.get("构图视角", [])
    for tag in values:
        if any(
            marker in tag
            for marker in ("大全景", "大远景", "远景", "全景", "全身", "中景", "近景", "半身", "特写", "头肩", "头部")
        ):
            return tag
    return values[0] if values else "中景"


def _stable_index(parts: Sequence[str], size: int, seed: int) -> int:
    payload = "|".join([*(str(part or "") for part in parts), str(int(seed or 0))])
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % max(1, size)


def _camera_move_zh(action: str, composition: str, scene: str, *, seed: int) -> str:
    source = f"{action} {composition} {scene}"
    if any(marker in source for marker in ("奔跑", "行走", "追", "移动", "穿过", "飞行", "驶过")):
        return _CAMERA_MOVES_ZH[0]
    if any(marker in composition for marker in ("特写", "近景")):
        return _CAMERA_MOVES_ZH[1]
    return _CAMERA_MOVES_ZH[_stable_index([action, composition, scene], len(_CAMERA_MOVES_ZH), seed)]


def _camera_move_en(source_prompt: str, *, seed: int) -> str:
    lowered = source_prompt.casefold()
    if any(marker in lowered for marker in ("walk", "run", "chase", "move", "fly", "drive")):
        return _CAMERA_MOVES_EN[0]
    if any(marker in lowered for marker in ("close-up", "close up", "portrait")):
        return _CAMERA_MOVES_EN[1]
    return _CAMERA_MOVES_EN[_stable_index([source_prompt[:320]], len(_CAMERA_MOVES_EN), seed)]


def _audio_zh(scene: str, action: str, non_person: bool) -> str:
    source = f"{scene} {action}"
    if any(marker in source for marker in ("雨", "暴风", "雷")):
        return "声音以雨点落在地面和衣料上的轻重变化为主，远处环境声保持模糊"
    if any(marker in source for marker in ("海", "沙滩", "海岸", "码头")):
        return "声音保留海浪、风和脚步之间自然的远近层次"
    if any(marker in source for marker in ("森林", "树林", "草地", "山谷")):
        return "声音只保留风穿过枝叶、脚步触地和远处自然回声"
    if any(marker in source for marker in ("城市", "街", "车站", "地铁", "市场")):
        return "环境声由远处交通、人群底噪和主体近处的脚步组成"
    if non_person:
        return "声音跟随结构运转、材质接触和空间回声变化，不额外加入旁白"
    return "声音只保留呼吸、脚步、衣料摩擦和当前空间原本存在的环境声"


def _audio_metadata(scene: str, action: str, settings: Mapping[str, Any], *, english: bool) -> dict[str, str]:
    """Expose audio channels without inventing dialogue or off-screen events."""

    target = resolve_video_prompt_profile(settings).get("target_model", "通用")
    if english:
        return {
            "overall_soundscape": f"natural ambience of {scene}, kept spatially consistent",
            "dialogue": "none unless already present in the source brief",
            "sound_effects": f"footsteps, material contact, and the direct sound of {action}",
            "non_diegetic_music": "restrained score only" if target == "H3" else "N/A",
        }
    return {
        "overall_soundscape": f"{scene}原本存在的环境底噪，保持远近层次连续",
        "dialogue": "除非源文本已有对白，否则不新增对白",
        "sound_effects": f"脚步、材质接触声以及{action}直接产生的声音",
        "non_diegetic_music": "只保留克制的非叙事配乐" if target == "H3" else "无",
    }


def _subject_reference_zh(subject: str, non_person: bool) -> str:
    if non_person:
        return "它"
    if any(marker in subject for marker in ("两人", "众人", "人群", "团队", "一行人")):
        return "他们"
    if any(marker in subject for marker in ("女性", "女人", "女孩", "少女", "母亲", "姐姐", "妹妹", "女主")):
        return "她"
    if re.search(r"(?:^|[、，,\s])女[^、，,\s]{1,12}(?:$|[、，,\s])", subject):
        return "她"
    if any(marker in subject for marker in ("男性", "男人", "男孩", "少年", "父亲", "哥哥", "弟弟", "男主")):
        return "他"
    if re.search(r"(?:^|[、，,\s])男[^、，,\s]{1,12}(?:$|[、，,\s])", subject):
        return "他"
    return "这个人物"


def _environment_feedback_zh(scene: str, action: str, reference: str, outfit: str) -> str:
    source = f"{scene} {action}"
    if any(marker in source for marker in ("雨", "暴风", "雷")):
        clothing = "衣摆" if outfit else "身体边缘"
        return f"{reference}的动作带起水花，湿透的{clothing}稍后才跟上转身的方向"
    if any(marker in source for marker in ("海", "沙滩", "海岸", "码头")):
        return f"脚边的浪、水面反光和迎面风依次回应{reference}的移动，清楚标出前进方向"
    if any(marker in source for marker in ("森林", "树林", "草地", "山谷")):
        return f"近处枝叶被{reference}带动后回弹，落叶和影子沿着同一条动线延迟移动"
    if any(marker in source for marker in ("城市", "街", "车站", "地铁", "市场")):
        return f"地面反光和近处物件在{reference}经过后依次改变，空间距离随动作变得清楚"
    return f"近处材质和投影在{reference}移动后才发生变化，让动作的方向与力度都有可见结果"


def _source_brief(settings: Mapping[str, Any]) -> str:
    for key in ("智能文本输入", "额外要求"):
        text = _clean(settings.get(key), limit=160)
        if not text:
            continue
        first = re.split(r"[。！？!?\n]", text, maxsplit=1)[0].strip(" ，,。；;")
        if 4 <= len(first) <= 140:
            return first
    return ""


def _personalize(text: Any, subject: str, scene: str) -> str:
    value = _clean(text, limit=180)
    if not value:
        return ""
    value = value.replace("主体", subject).replace("当前空间", scene)
    return value[0].lower() + value[1:] if value[:1].isascii() else value


def _dedupe_sentences(text: str) -> str:
    sentences = [part.strip() for part in re.split(r"(?<=[。！？.!?])\s*", text) if part.strip()]
    result: list[str] = []
    seen: set[str] = set()
    for sentence in sentences:
        key = re.sub(r"[\W_]+", "", sentence, flags=re.UNICODE).casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        if not re.search(r"[。！？.!?]$", sentence):
            sentence += "。" if re.search(r"[\u4e00-\u9fff]", sentence) else "."
        result.append(sentence)
    separator = "" if re.search(r"[\u4e00-\u9fff]", text) else " "
    return separator.join(result)


def _join_storyboard_paragraphs(paragraphs: Sequence[str]) -> str:
    result: list[str] = []
    for paragraph in paragraphs:
        cleaned = _dedupe_sentences(paragraph)
        if cleaned:
            result.append(cleaned)
    return "\n\n".join(result)


def _timeline_label(index: int, phase: str, settings: Mapping[str, Any], *, english: bool) -> str:
    """Return a storyboard label with an optional profile timecode."""

    profile = resolve_video_prompt_profile(settings)
    suffix = ""
    segments = _timeline_segments_for_count(int(profile.get("shot_count", 5) or 5))
    if profile.get("timeline_enabled") and 1 <= index <= len(segments):
        start, end = segments[index - 1]
        start_text, end_text = _format_timecode(start), _format_timecode(end)
        suffix = f", {start_text}-{end_text}s" if english else f"，{start_text}-{end_text}秒"
    if english:
        return f"Shot {index} ({phase}{suffix}):"
    return f"分镜{['一', '二', '三', '四', '五', '六', '七', '八', '九'][index - 1]}（{phase}{suffix}）："


def _replace_storyboard_label(
    paragraph: str,
    index: int,
    phase: str,
    settings: Mapping[str, Any],
    *,
    english: bool,
) -> str:
    pattern = _STORYBOARD_LABEL_EN if english else _STORYBOARD_LABEL_ZH
    match = pattern.match(paragraph.strip())
    if not match:
        return paragraph
    return _timeline_label(index, phase, settings, english=english) + paragraph.strip()[match.end():].lstrip()


def _adapt_storyboard_paragraphs(
    paragraphs: Sequence[str],
    settings: Mapping[str, Any],
    *,
    english: bool,
) -> tuple[str, ...]:
    """Project the five-phase base story onto the requested bounded shot count."""

    base = list(paragraphs)
    count = resolve_video_shot_count(settings)
    if count == 5 or len(base) < 5:
        return tuple(base)
    if count == 1:
        return (
            _replace_storyboard_label(base[2], 1, "action" if english else "行动", settings, english=english),
        )
    if count == 3:
        indexes = (0, 2, 4)
        phases = ("setup", "action", "resolution") if english else ("建立", "行动", "收束")
        return tuple(
            _replace_storyboard_label(base[source], index, phase, settings, english=english)
            for index, (source, phase) in enumerate(zip(indexes, phases), start=1)
        )
    # Long-form mode adds two connective shots without changing the world or
    # the causal spine of the original five phases.
    if english:
        bridge = (
            "The camera stays on the same axis and follows the immediate physical trace left by the action, "
            "so the trigger becomes a visible consequence before the escalation continues. "
            "The established lighting and spatial sound preserve the same location."
        )
        aftermath = (
            "The camera holds the same location for one final breath and records how the established subject, "
            "prop, and light settle after the consequence, without adding a new event. "
            "The ending remains on the existing axis and hands the state forward."
        )
        return (
            _replace_storyboard_label(base[0], 1, "setup", settings, english=True),
            _replace_storyboard_label(base[1], 2, "trigger", settings, english=True),
            _replace_storyboard_label(base[2], 3, "action", settings, english=True),
            _timeline_label(4, "action", settings, english=True) + bridge,
            _replace_storyboard_label(base[3], 5, "escalation", settings, english=True),
            _replace_storyboard_label(base[4], 6, "resolution", settings, english=True),
            _timeline_label(7, "aftermath", settings, english=True) + aftermath,
        )
    bridge = "镜头沿同一条轴线记录动作留下的直接痕迹，让触发事件在升级前先形成可见后果，不改变人物、道具和地点。光线与空间声音继续证明镜头仍在同一处。"
    aftermath = "镜头在原有地点多停留片刻，记录主体、道具与光线在结果之后如何稳定下来，不再引入新的事件。结尾保持原有轴线，并把结束状态交给后续行动。"
    return (
        _replace_storyboard_label(base[0], 1, "建立", settings, english=False),
        _replace_storyboard_label(base[1], 2, "触发", settings, english=False),
        _replace_storyboard_label(base[2], 3, "行动", settings, english=False),
        _timeline_label(4, "行动", settings, english=False) + bridge,
        _replace_storyboard_label(base[3], 5, "升级", settings, english=False),
        _replace_storyboard_label(base[4], 6, "收束", settings, english=False),
        _timeline_label(7, "余波", settings, english=False) + aftermath,
    )


def _english_source_clause(primary_prompt: str) -> str:
    source = re.sub(r"\s+", " ", str(primary_prompt or "")).strip()
    source = re.sub(r"中文说明\s*[:：].*$", "", source, flags=re.DOTALL).strip()
    if not source or re.search(r"[\u4e00-\u9fff]", source):
        return "the established subject in the selected location"
    sentence = re.split(r"(?<=[.!?])\s+", source, maxsplit=1)[0].strip()
    if len(sentence) <= 260:
        return sentence.rstrip(".!?")
    clauses = [part.strip() for part in sentence.split(",") if part.strip()]
    result: list[str] = []
    for clause in clauses:
        candidate = ", ".join([*result, clause])
        if result and len(candidate) > 240:
            break
        result.append(clause)
    return ", ".join(result).rstrip(".!?") or "the established subject in the selected location"


def _build_chinese_video_prompt(
    groups: Mapping[str, list[str]],
    settings: Mapping[str, Any],
    *,
    primary_prompt: str,
) -> str:
    subject_type = str(settings.get("主体类型解析结果", "") or settings.get("主体类型", "自动") or "自动").strip()
    non_person = subject_type == "非人物主体"
    subject = _first(groups, "主体", "非人物主体" if non_person else "画面中的成年人物")
    reference = _subject_reference_zh(subject, non_person)
    style = _first(groups, "画面风格", str(settings.get("模板风格", "电影写实") or "电影写实"))
    scene = _first(groups, "场景背景") or "当前主场景"
    result_contract = _video_result_contract(settings)
    action = _first(groups, "动作姿态") or ("完成一次有明确方向的状态变化" if non_person else "先停下确认线索，再做出一个明确动作")
    outfit = _first(groups, "服装造型")
    props = _series(groups, "道具世界观") or ("既有接触关系" if result_contract else "场景中的关键线索")
    lighting = _first(groups, "光影氛围") or "主光随动作轻微移动，环境反射保留空间层次"
    composition = _primary_composition(groups)
    style_skill = settings.get("模板风格Skill")
    if not isinstance(style_skill, Mapping):
        style_skill = {}
    medium = _clean(style_skill.get("medium"), limit=120)
    rendering = _clean(style_skill.get("rendering"), limit=180)
    video_rules = _clean(style_skill.get("video_rules"), limit=180)
    brief = _source_brief(settings)
    seed = int(settings.get("运行时随机有效种子", 0) or settings.get("seed", 0) or 0)
    anchors = {
        "subject": subject,
        "scene": scene,
        "action": action,
        "props": props,
        "style": style,
        "lighting": lighting,
        "outfit": outfit,
        "composition": composition,
        "source": primary_prompt[:600],
    }
    plan = build_narrative_plan(anchors, seed=seed, output_count=1)
    opening = _personalize(plan.get("opening_zh"), reference, scene)
    motive = _personalize(plan.get("motive_zh"), reference, scene)
    trigger = _personalize(plan.get("trigger_zh"), reference, scene)
    response = _personalize(plan.get("response_zh"), reference, scene)
    escalation = _personalize(plan.get("escalation_zh"), reference, scene)
    feedback_plan = _personalize(plan.get("feedback_zh"), reference, scene)
    climax = _personalize(plan.get("climax_zh"), reference, scene)
    turn = _personalize(plan.get("turn_zh"), reference, scene)
    ending = _personalize(plan.get("ending_zh"), reference, scene)
    if result_contract:
        contact_points = _unique_values(result_contract.get("contact_points"), limit=8) or ["当前既有接触点"]
        contact_text = "、".join(contact_points)
        opening = f"{reference}在同一空间位置保持既有姿态，动作从{contact_text}的接触关系自然延续"
        motive = "画面的推进只来自成年主体之间已经建立的自愿动作，不添加外部任务或旁支事件"
        trigger = f"{contact_text}处的刺激节奏沿原有方向逐步增强"
        response = f"{reference}维持原有主客体关系，只以呼吸、肌肉张力和重心变化回应"
        escalation = "动作幅度、呼吸节奏与身体反馈按同一因果顺序增强"
        feedback_plan = f"所有可见反馈都从{contact_text}向既有身体轮廓和接触表面传递"
        turn = "人物情绪由持续紧张转向结果即将发生时的集中"
        climax = "既有动作进入结果阶段，前后空间关系保持不变"
        ending = "动作在原有位置收束，人物姿态、接触关系和可见结果共同形成明确结束状态"
    camera = _camera_move_zh(action, composition, scene, seed=seed).replace("主体", subject)
    feedback = _environment_feedback_zh(scene, action, reference, outfit)
    outfit_clause = f"身穿{outfit}，" if outfit and not non_person else ""
    brief_clause = f"这条故事围绕“{brief}”展开，" if brief else ""
    audio = _audio_zh(scene, action, non_person)
    result_phrases = _video_result_phrases_zh(result_contract) if result_contract else {}
    paragraphs = (
        (
            f"{_timeline_label(1, '建立', settings, english=False)}镜头以{composition}建立{scene}的空间关系，{subject}{outfit_clause}位于画面中心偏前，"
            f"{props}留在视线能够回到的位置。{brief_clause}{opening}；{motive}。"
            f"{style}决定画面的线条、色彩与材质表达；{medium or '当前媒介'}保持统一，{rendering or '材质与光线保持空间关系连续'}。"
            f"{lighting}先把主体与关键线索从背景中分离，{audio}。{result_phrases.get('setup', '')}"
        ),
        (
            f"{_timeline_label(2, '触发', settings, english=False)}镜头从环境关系推进到{reference}的视线、手部与{props}之间，先让观众读懂线索，再发生变化。"
            f"起初{reference}只是在确认现场，因为{trigger}，原有节奏被打破；焦点短暂落到{props}，随后回到{reference}的反应。"
            f"这一分镜承接开场动机，并把问题明确推向下一步行动，光线和环境声先出现细微偏移。"
            f"{result_phrases.get('trace', '')}"
        ),
        (
            f"{_timeline_label(3, '行动', settings, english=False)}镜头{camera}，在完整记录重心变化的同时保持{scene}方向清楚。"
            f"{reference}随即{action}，{response}；{outfit or '主体外观'}的边缘、接触点与受力方向跟随动作变化，{feedback}。"
            f"动作不是孤立展示，而是对上一分镜线索的直接回应，并由{props}的位置变化把故事带向更大的后果。"
            f"{result_phrases.get('action', '')}"
        ),
        (
            f"{_timeline_label(4, '升级', settings, english=False)}镜头改变景别观察行动造成的连锁结果，前景遮挡、中景动作和背景信息沿同一方向展开。"
            f"{escalation}，{feedback_plan}；与此同时{turn}。{climax}，{lighting}随局势重新分配明暗与色温。"
            f"声音从近处材质接触扩展到{scene}的空间回声，让视觉高潮既有来源，也为最后一段留下可继续追踪的结果。"
            f"{result_phrases.get('result', '')}"
        ),
        (
            f"{_timeline_label(5, '收束', settings, english=False)}镜头在高潮之后放慢观察，不再引入无关人物或新地点，而是回看{subject}、{props}与环境后果之间的新关系。"
            f"最后，{ending}；{reference}的视线、{props}的状态和背景光共同说明这次选择已经改变局势。"
            f"结尾保留清楚结果与开放余韵，使五段分镜组成一条完整剧情，也让下一次行动拥有自然入口。"
            f"全程遵守{video_rules or '同一媒介、空间与主体的连续性'}。{result_phrases.get('ending', '')}"
        ),
    )
    return _join_storyboard_paragraphs(_adapt_storyboard_paragraphs(paragraphs, settings, english=False))


def _english_group_value(groups: Mapping[str, list[str]] | None, name: str) -> str:
    """Return an ASCII-safe explicit anchor for the English storyboard path."""

    if not isinstance(groups, Mapping):
        return ""
    for value in groups.get(name, []) or []:
        text = _clean(value, limit=120)
        if text and not re.search(r"[\u4e00-\u9fff]", text):
            return text
    return ""


def _english_anchor_sentence(groups: Mapping[str, list[str]] | None) -> str:
    labels = (
        ("主体", "the subject"),
        ("场景背景", "the location"),
        ("动作姿态", "the central action"),
        ("服装造型", "the outfit"),
        ("道具世界观", "the key prop"),
        ("画面风格", "the visual style"),
        ("光影氛围", "the lighting"),
        ("构图视角", "the composition"),
    )
    clauses = [
        f"{label} is {value}"
        for name, label in labels
        if (value := _english_group_value(groups, name))
    ]
    if not clauses:
        return ""
    return "The explicit creative anchors remain consistent: " + "; ".join(clauses) + "."


def _build_english_video_prompt(
    settings: Mapping[str, Any],
    *,
    primary_prompt: str,
    groups: Mapping[str, list[str]] | None = None,
) -> str:
    seed = int(settings.get("运行时随机有效种子", 0) or settings.get("seed", 0) or 0)
    source = _english_source_clause(primary_prompt)
    anchor_sentence = _english_anchor_sentence(groups)
    non_person = str(settings.get("主体类型解析结果", settings.get("主体类型", "")) or "").strip() == "非人物主体"
    subject = _english_group_value(groups, "主体") or "the established subject"
    scene = _english_group_value(groups, "场景背景") or "the established location"
    action = _english_group_value(groups, "动作姿态") or "the established action"
    outfit = "" if non_person else (_english_group_value(groups, "服装造型") or "the established outfit")
    prop = _english_group_value(groups, "道具世界观") or "the key visual clue"
    style = _english_group_value(groups, "画面风格") or "the selected visual style"
    lighting = _english_group_value(groups, "光影氛围") or "the established lighting"
    composition = _english_group_value(groups, "构图视角") or "a readable wide composition"
    plan = build_narrative_plan({"source": source}, seed=seed, output_count=1)
    opening = _clean(plan.get("opening_en"), limit=220)
    motive = _clean(plan.get("motive_en"), limit=200)
    trigger = _clean(plan.get("trigger_en"), limit=180)
    response = _clean(plan.get("response_en"), limit=180)
    escalation = _clean(plan.get("escalation_en"), limit=200)
    feedback = _clean(plan.get("feedback_en"), limit=200)
    climax = _clean(plan.get("climax_en"), limit=200)
    turn = _clean(plan.get("turn_en"), limit=160)
    ending = _clean(plan.get("ending_en"), limit=180)
    result_contract = _video_result_contract(settings)
    if result_contract:
        opening = "the adult participants hold their established positions as the action continues from the same contact relation"
        motive = "the scene advances only through the already established consensual action, without an outside task or subplot"
        trigger = "the stimulation increases gradually along the same direction and contact points"
        response = "the participants answer only through breathing, muscle tension, and a readable shift of weight while preserving their roles"
        escalation = "movement, breathing, and physical feedback intensify in one causal order"
        feedback = "every visible response travels from the same contact points across the already visible bodies and surfaces"
        turn = "the emotional focus narrows as the established result approaches"
        climax = "the same action reaches its result phase without changing the spatial relation"
        ending = "the action resolves in place, leaving pose, contact relation, and visible result in one readable ending state"
    opening = opening[:1].lower() + opening[1:]
    feedback = feedback[:1].lower() + feedback[1:]
    ending = ending[:1].lower() + ending[1:]
    camera = _camera_move_en(primary_prompt, seed=seed)
    result_phrases = _video_result_phrases_en(result_contract) if result_contract else {}
    focus_object = "the established contact relation" if result_contract else "the key visual clue"
    outfit_clause = f" in {outfit}" if outfit else ""
    appearance_clause = f"the {outfit} silhouette, " if outfit else "the established surface, "
    paragraphs = (
        f"{_timeline_label(1, 'setup', settings, english=True)} The camera opens on {composition} in {scene}, showing {subject}{outfit_clause} with {prop}. {source}. {anchor_sentence} {opening}. {motive}. {style} shapes the medium and material language, while {lighting} and ambient sound establish the location before the conflict begins. {result_phrases.get('setup', '')}",
        f"{_timeline_label(2, 'trigger', settings, english=True)} The camera moves from {scene} to {subject}'s attention and {prop}. At first the rhythm remains controlled; when {trigger}, that rhythm breaks and the focus returns to {subject}'s reaction. This shot turns the setup into a clear cause that the next action must continue. {result_phrases.get('trace', '')}",
        f"{_timeline_label(3, 'action', settings, english=True)} The camera {camera} while preserving a readable direction of travel. {subject} responds through {action}; {appearance_clause}contact points, reflections, and spatial sound follow the movement in causal order, so the action grows directly from the preceding clue. {result_phrases.get('action', '')}",
        f"{_timeline_label(4, 'escalation', settings, english=True)} The camera changes scale to reveal the consequence across foreground, middle ground, and background of {scene}. {escalation}; {feedback}. The emotion shifts as {turn}, and {climax}. {lighting} and sound expand the result without introducing an unrelated storyline. {result_phrases.get('result', '')}",
        f"{_timeline_label(5, 'resolution', settings, english=True)} The camera settles after the climax and observes the new relationship between {subject}, {prop}, and {scene}. Finally, {ending}. The final image preserves {composition}, makes the consequence readable, and keeps {style} visually consistent while leaving an open emotional aftertone for what happens next. {result_phrases.get('ending', '')}",
    )
    return _join_storyboard_paragraphs(_adapt_storyboard_paragraphs(paragraphs, settings, english=True))


_STORYBOARD_LABEL_ZH = re.compile(
    r"^(?:分镜|镜头)\s*(?P<index>[零一二两三四五六七八九十百0-9]+)(?:[（(](?P<title>[^）)]+)[）)])?\s*[:：]"
)
_STORYBOARD_LABEL_EN = re.compile(
    r"^(?:shot|scene)\s*(?P<index>\d+)(?:\s*[（(](?P<title>[^）)]+)[）)])?\s*:",
    flags=re.IGNORECASE,
)
def _storyboard_paragraph_number(paragraph: str, *, english: bool) -> int | None:
    pattern = _STORYBOARD_LABEL_EN if english else _STORYBOARD_LABEL_ZH
    match = pattern.match(str(paragraph or "").strip())
    return storyboard_number_token(match.group("index")) if match else None


def _has_contiguous_storyboard_numbers(paragraphs: Sequence[str], *, english: bool) -> bool:
    numbers = [_storyboard_paragraph_number(paragraph, english=english) for paragraph in paragraphs]
    return bool(numbers) and numbers == list(range(1, len(numbers) + 1))


def _has_ordered_storyboard_phases(paragraphs: Sequence[str], *, english: bool) -> bool:
    pattern = _STORYBOARD_LABEL_EN if english else _STORYBOARD_LABEL_ZH
    phases: list[str | None] = []
    for paragraph in paragraphs:
        match = pattern.match(str(paragraph or "").strip())
        phases.append(storyboard_phase_token(match.group("title")) if match else None)
    return storyboard_phases_are_ordered(phases)


def _storyboard_paragraphs(text: str) -> list[str]:
    source = str(text or "").strip().replace("\r\n", "\n").replace("\r", "\n")
    if not source:
        return []
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", source) if part.strip()]
    if len(paragraphs) >= VIDEO_PROMPT_MIN_STORYBOARD_PARAGRAPHS:
        return paragraphs
    lines = [line.strip() for line in source.split("\n") if line.strip()]
    if len(lines) >= VIDEO_PROMPT_MIN_STORYBOARD_PARAGRAPHS:
        return lines
    return paragraphs


def build_video_storyboard_metadata(
    prompt: str,
    settings: Mapping[str, Any] | None = None,
    *,
    selected: Mapping[str, Sequence[Any]] | None = None,
    custom_tags: Sequence[Any] | None = None,
) -> list[dict[str, Any]]:
    """Expose shot-level metadata alongside the human-readable storyboard."""

    resolved = resolve_video_prompt_profile(settings)
    language = str((settings or {}).get("提示词语言", "纯中文") or "纯中文").strip()
    english = language == "纯英文"
    groups = _normalized_groups(selected, custom_tags, settings or {})
    anchor_names = ("主体", "场景背景", "动作姿态", "服装造型", "道具世界观", "光影氛围", "构图视角")
    anchors = {
        name: list(groups.get(name, []))[:4]
        for name in anchor_names
        if groups.get(name)
    }
    scene = _first(groups, "场景背景") or "当前主场景"
    action = _first(groups, "动作姿态") or "当前动作"
    audio_fields = _audio_metadata(scene, action, settings or {}, english=english)
    result: list[dict[str, Any]] = []
    timeline_segments = _timeline_segments_for_count(int(resolved.get("shot_count", 5) or 5))
    for paragraph in _storyboard_paragraphs(prompt):
        number = _storyboard_paragraph_number(paragraph, english=english)
        if number is None:
            continue
        pattern = _STORYBOARD_LABEL_EN if english else _STORYBOARD_LABEL_ZH
        match = pattern.match(paragraph.strip())
        phase = storyboard_phase_token(match.group("title")) if match else None
        phase = phase or (match.group("title").strip() if match and match.group("title") else "story")
        timeline_segment = (
            timeline_segments[number - 1]
            if resolved.get("timeline_enabled") and 1 <= number <= len(timeline_segments)
            else None
        )
        result.append(
            {
                "shot_id": f"S{number:02d}",
                "number": number,
                "phase": phase,
                "duration": (timeline_segment[1] - timeline_segment[0]) if timeline_segment else None,
                "time_axis": (
                    f"{_format_timecode(timeline_segment[0])}-{_format_timecode(timeline_segment[1])}s"
                    if timeline_segment
                    else resolved["timeline"]
                ),
                "timeline_enabled": bool(resolved.get("timeline_enabled")),
                "input_mode": resolved["input_mode"],
                "target_model": resolved["target_model"],
                "subject_kind": resolved.get("subject_kind", "person_or_auto"),
                "camera": "镜头与机位见 description" if not english else "camera and framing are in description",
                "spatial_anchors": anchors,
                "lighting_baseline": anchors.get("光影氛围", []),
                "audio_schema": resolved["audio_schema"],
                "overall_soundscape": audio_fields["overall_soundscape"],
                "dialogue": audio_fields["dialogue"],
                "sound_effects": audio_fields["sound_effects"],
                "non_diegetic_music": audio_fields["non_diegetic_music"],
                "continuity_handoff": (
                    "承接上一镜头的主体、场景、道具、光影和镜头轴线，并把本镜结束状态交给下一镜头。"
                    if not english
                    else "Inherit the subject, location, prop, lighting, and camera axis from the previous shot and hand this ending state to the next shot."
                ),
                "description": paragraph,
            }
        )
    return result


def _valid_storyboard_paragraph(paragraph: str, *, english: bool) -> bool:
    label_pattern = _STORYBOARD_LABEL_EN if english else _STORYBOARD_LABEL_ZH
    if not label_pattern.match(paragraph):
        return False
    if len(re.findall(r"[。！？.!?]", paragraph)) < 2:
        return False
    lowered = paragraph.casefold()
    camera_markers = ("camera", "frame", "focus", "shot") if english else ("镜头", "画面", "焦点", "景别", "机位")
    return any(marker in lowered for marker in camera_markers)


def is_natural_video_prompt(
    text: str,
    *,
    language: str = "纯中文",
    allow_timeline: bool = False,
) -> bool:
    """Validate an unbounded natural-language storyboard with one causal story arc."""

    prompt = str(text or "").strip()
    mode = str(language or "纯中文").strip()
    if (
        not prompt
        or any(marker in prompt.casefold() for marker in _META_MARKERS)
        or (not allow_timeline and _DURATION_EXPRESSION_PATTERN.search(prompt))
    ):
        return False
    if mode == "英文提示词+中文说明":
        english, marker, chinese = prompt.partition("中文说明：")
        return bool(
            marker
            and re.search(r"[\u4e00-\u9fff]", chinese)
            and is_natural_video_prompt(chinese.strip(), language="纯中文", allow_timeline=allow_timeline)
            and is_natural_video_prompt(english.strip(), language="纯英文", allow_timeline=allow_timeline)
        )
    enumeration_limit = max(18, len(prompt) // 40)
    if prompt.count("、") > enumeration_limit or len(re.findall(r"(?:^|[，,])[^。.!?]{0,18}(?:[，,]|$)", prompt)) > 48:
        return False
    if mode == "纯英文":
        lowered = prompt.casefold()
        paragraphs = _storyboard_paragraphs(prompt)
        timeline_valid = (
            not allow_timeline
            or len(re.findall(r"\b\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*s\b", prompt, flags=re.IGNORECASE))
            >= len(paragraphs)
        )
        if len(paragraphs) == 1:
            first_match = _STORYBOARD_LABEL_EN.match(paragraphs[0])
            first_phase = storyboard_phase_token(first_match.group("title")) if first_match else None
            return (
                not re.search(r"[\u4e00-\u9fff]", prompt)
                and first_phase == "action"
                and _has_contiguous_storyboard_numbers(paragraphs, english=True)
                and all(_valid_storyboard_paragraph(paragraph, english=True) for paragraph in paragraphs)
                and any(marker in lowered for marker in ("action", "respond", "moves", "acts"))
                and any(marker in lowered for marker in ("environment", "light", "sound", "camera"))
                and timeline_valid
            )
        if len(paragraphs) == 3:
            return (
                not re.search(r"[\u4e00-\u9fff]", prompt)
                and _has_contiguous_storyboard_numbers(paragraphs, english=True)
                and _has_ordered_storyboard_phases(paragraphs, english=True)
                and all(_valid_storyboard_paragraph(paragraph, english=True) for paragraph in paragraphs)
                and all(marker in lowered for marker in ("setup", "action", "resolution"))
                and any(marker in lowered for marker in ("when", "because", "causes", "consequence"))
                and timeline_valid
            )
        return (
            not re.search(r"[\u4e00-\u9fff]", prompt)
            and len(paragraphs) >= VIDEO_PROMPT_MIN_STORYBOARD_PARAGRAPHS
            and _has_contiguous_storyboard_numbers(paragraphs, english=True)
            and _has_ordered_storyboard_phases(paragraphs, english=True)
            and all(_valid_storyboard_paragraph(paragraph, english=True) for paragraph in paragraphs)
            and all(marker in lowered for marker in ("setup", "trigger", "action", "resolution"))
            and any(marker in lowered for marker in ("when", "because", "causes", "consequence"))
            and timeline_valid
        )
    body = prompt.split("中文说明：", 1)[-1] if mode == "英文提示词+中文说明" else prompt
    paragraphs = _storyboard_paragraphs(body)
    timeline_valid = (
        not allow_timeline
        or len(re.findall(r"\d+(?:\.\d+)?\s*[-到至]\s*\d+(?:\.\d+)?\s*(?:秒|s)", body, flags=re.IGNORECASE))
        >= len(paragraphs)
    )
    if len(paragraphs) == 1:
        first_match = _STORYBOARD_LABEL_ZH.match(paragraphs[0])
        first_phase = storyboard_phase_token(first_match.group("title")) if first_match else None
        return (
            not re.search(r"[A-Za-z]", body)
            and first_phase == "action"
            and _has_contiguous_storyboard_numbers(paragraphs, english=False)
            and all(_valid_storyboard_paragraph(paragraph, english=False) for paragraph in paragraphs)
            and any(marker in body for marker in ("行动", "回应", "移动", "动作"))
            and any(marker in body for marker in ("环境", "光", "声音", "镜头"))
            and timeline_valid
        )
    if len(paragraphs) == 3:
        return (
            not re.search(r"[A-Za-z]", body)
            and _has_contiguous_storyboard_numbers(paragraphs, english=False)
            and _has_ordered_storyboard_phases(paragraphs, english=False)
            and all(_valid_storyboard_paragraph(paragraph, english=False) for paragraph in paragraphs)
            and all(marker in body for marker in ("建立", "行动", "收束"))
            and any(marker in body for marker in ("因为", "带来", "随即", "结果"))
            and timeline_valid
        )
    return (
        len(paragraphs) >= VIDEO_PROMPT_MIN_STORYBOARD_PARAGRAPHS
        and _has_contiguous_storyboard_numbers(paragraphs, english=False)
        and _has_ordered_storyboard_phases(paragraphs, english=False)
        and all(_valid_storyboard_paragraph(paragraph, english=False) for paragraph in paragraphs)
        and all(marker in body for marker in ("建立", "触发", "行动", "收束"))
        and any(marker in body for marker in ("因为", "带来", "随即", "结果"))
        and any(marker in body for marker in ("环境", "光", "声音"))
        and timeline_valid
    )


def build_video_prompt(
    selected: OrderedDict[str, list[str]] | Mapping[str, Sequence[Any]] | None,
    custom_tags: Sequence[Any] | None,
    settings: Mapping[str, Any],
    *,
    primary_prompt: str = "",
) -> str:
    """Build one multi-paragraph storyboard whose shots form a complete story."""

    groups = _normalized_groups(selected, custom_tags, settings, include_preferences=True)
    language = str(settings.get("提示词语言", "纯中文") or "纯中文").strip()
    if language in {"纯英文", "英文提示词+中文说明"}:
        english = _build_english_video_prompt(
            settings,
            primary_prompt=primary_prompt,
            groups=groups,
        )
        if language == "纯英文":
            return english
        chinese = _build_chinese_video_prompt(groups, settings, primary_prompt=primary_prompt)
        return f"{english}\n中文说明：{chinese}"
    return _build_chinese_video_prompt(groups, settings, primary_prompt=primary_prompt)


__all__ = [
    "VIDEO_PROMPT_DURATION_SECONDS",
    "VIDEO_PROMPT_MAX_CHARS_ZH",
    "VIDEO_PROMPT_MIN_CHARS_ZH",
    "VIDEO_PROMPT_MIN_STORYBOARD_PARAGRAPHS",
    "VIDEO_PROMPT_TARGET_MODEL_OPTIONS",
    "VIDEO_PROMPT_INPUT_MODE_OPTIONS",
    "VIDEO_PROMPT_SHOT_COUNT_OPTIONS",
    "VIDEO_PROMPT_MODEL_PROFILES",
    "VIDEO_PROMPT_MODEL_SYSTEM_TEMPLATE",
    "VIDEO_PROMPT_SKILL_VERSION",
    "VIDEO_PROMPT_TIMELINE_SEGMENTS",
    "build_video_prompt",
    "build_video_storyboard_metadata",
    "is_natural_video_prompt",
    "resolve_video_prompt_profile",
    "resolve_video_shot_count",
    "video_prompt_anchor_roles",
    "video_prompt_required_anchors",
]
