# -*- coding: utf-8 -*-
"""Natural-language video prompt skill built from the normalized stage state."""

from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from typing import Any, Mapping, Sequence

try:
    from .narrative import build_narrative_plan, storyboard_number_token
except Exception:  # pragma: no cover - direct file loading in focused tests
    from stage_prompt_narrative_test import (  # type: ignore
        build_narrative_plan,
        storyboard_number_token,
    )


VIDEO_PROMPT_SKILL_VERSION = "video-prompt-skill-v8"
VIDEO_PROMPT_DURATION_SECONDS = 8
VIDEO_PROMPT_MIN_CHARS_ZH = 0  # Compatibility export: text length has been unbounded since v4.
VIDEO_PROMPT_MAX_CHARS_ZH = 0  # Zero means unbounded.
VIDEO_PROMPT_MIN_STORYBOARD_PARAGRAPHS = 3
VIDEO_PROMPT_MODEL_SYSTEM_TEMPLATE = """
你是 Qwen TE 的视频提示词后置导演 Skill。输入已经是独立视频 Skill 生成的可靠分镜故事底稿，你负责在同一剧情主线上把它润色得更自然、更具体、更适合视频生成。

硬规则：
1. 只输出最终视频提示词正文，不输出分析、思考过程、Markdown、标签列表、参数或“提示词：”。
2. 输出至少三段分镜；每段以“分镜一/二/三……”或“Shot 1/2/3...”开头，从 1 连续编号，不得重复、倒序或跳号，并使用完整自然语言写清景别或机位、镜头运动、主体动作、环境或光影反馈以及与前后分镜的承接关系。
3. 所有分镜共同组成一条完整故事：建立处境与动机，出现触发事件，主体作出回应，局势升级并形成视觉高潮，最后给出结果或开放结尾。不得把互不相关的镜头拼在一起。
4. 严格保留底稿中的主体、服装、场景、动作、道具、风格、光影和声音锚点；首镜明确建立主体、主场景和关键道具，后续每镜都要用全称、代词、同一空间参照或可见状态变化保持三者可追踪。可以在故事需要时改变景别和机位，但不得无理由换人、换地点，或让道具凭空出现、消失。
5. 使用连贯自然语言，不堆关键词，不复述规则，不写无法直接拍摄的抽象评价。每段必须是可独立拍摄、又能承接下一段的分镜描述。
6. 不限制正文总字数、单段字数或英文单词数；长度由剧情和分镜需要决定。正文仍不得写具体秒数或时长参数。
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
    action = _first(groups, "动作姿态") or ("完成一次有明确方向的状态变化" if non_person else "先停下确认线索，再做出一个明确动作")
    outfit = _first(groups, "服装造型")
    props = _series(groups, "道具世界观") or "场景中的关键线索"
    lighting = _first(groups, "光影氛围") or "主光随动作轻微移动，环境反射保留空间层次"
    composition = _primary_composition(groups)
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
    camera = _camera_move_zh(action, composition, scene, seed=seed).replace("主体", subject)
    feedback = _environment_feedback_zh(scene, action, reference, outfit)
    outfit_clause = f"身穿{outfit}，" if outfit and not non_person else ""
    brief_clause = f"这条故事围绕“{brief}”展开，" if brief else ""
    audio = _audio_zh(scene, action, non_person)
    paragraphs = (
        (
            f"分镜一（建立）：镜头以{composition}建立{scene}的空间关系，{subject}{outfit_clause}位于画面中心偏前，"
            f"{props}留在视线能够回到的位置。{brief_clause}{opening}；{motive}。"
            f"{style}决定画面的线条、色彩与材质表达，{lighting}先把主体与关键线索从背景中分离，{audio}。"
        ),
        (
            f"分镜二（触发）：镜头从环境关系推进到{reference}的视线、手部与{props}之间，先让观众读懂线索，再发生变化。"
            f"起初{reference}只是在确认现场，因为{trigger}，原有节奏被打破；焦点短暂落到{props}，随后回到{reference}的反应。"
            f"这一分镜承接开场动机，并把问题明确推向下一步行动，光线和环境声先出现细微偏移。"
        ),
        (
            f"分镜三（行动）：镜头{camera}，在完整记录重心变化的同时保持{scene}方向清楚。"
            f"{reference}随即{action}，{response}；{outfit or '主体外观'}的边缘、接触点与受力方向跟随动作变化，{feedback}。"
            f"动作不是孤立展示，而是对上一分镜线索的直接回应，并由{props}的位置变化把故事带向更大的后果。"
        ),
        (
            f"分镜四（升级）：镜头改变景别观察行动造成的连锁结果，前景遮挡、中景动作和背景信息沿同一方向展开。"
            f"{escalation}，{feedback_plan}；与此同时{turn}。{climax}，{lighting}随局势重新分配明暗与色温。"
            f"声音从近处材质接触扩展到{scene}的空间回声，让视觉高潮既有来源，也为最后一段留下可继续追踪的结果。"
        ),
        (
            f"分镜五（收束）：镜头在高潮之后放慢观察，不再引入无关人物或新地点，而是回看{subject}、{props}与环境后果之间的新关系。"
            f"最后，{ending}；{reference}的视线、{props}的状态和背景光共同说明这次选择已经改变局势。"
            f"结尾保留清楚结果与开放余韵，使五段分镜组成一条完整剧情，也让下一次行动拥有自然入口。"
        ),
    )
    return _join_storyboard_paragraphs(paragraphs)


def _build_english_video_prompt(settings: Mapping[str, Any], *, primary_prompt: str) -> str:
    seed = int(settings.get("运行时随机有效种子", 0) or settings.get("seed", 0) or 0)
    source = _english_source_clause(primary_prompt)
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
    opening = opening[:1].lower() + opening[1:]
    feedback = feedback[:1].lower() + feedback[1:]
    ending = ending[:1].lower() + ending[1:]
    camera = _camera_move_en(primary_prompt, seed=seed)
    paragraphs = (
        f"Shot 1 (setup): The camera opens on a readable wide view of this established visual world: {source}. {opening}. {motive}. Light, material, and ambient sound establish the location before the conflict begins.",
        f"Shot 2 (trigger): The camera moves from the location to the subject's attention and the key visual clue. At first the rhythm remains controlled; when {trigger}, that rhythm breaks and the focus returns to the subject's reaction. This shot turns the setup into a clear question that the next action must answer.",
        f"Shot 3 (action): The camera {camera} while preserving a readable direction of travel. The subject responds: {response}. Material contact, reflections, and spatial sound follow the movement in causal order, so the action grows directly from the preceding clue.",
        f"Shot 4 (escalation): The camera changes scale to reveal the consequence across foreground, middle ground, and background. {escalation}; {feedback}. The emotion shifts as {turn}, and {climax}. Light and sound expand the result without introducing an unrelated storyline.",
        f"Shot 5 (resolution): The camera settles after the climax and observes the new relationship between subject, clue, and location. Finally, {ending}. The final image makes the consequence readable, preserves an open emotional aftertone, and gives the complete storyboard a natural path into whatever happens next.",
    )
    return _join_storyboard_paragraphs(paragraphs)


_STORYBOARD_LABEL_ZH = re.compile(
    r"^(?:分镜|镜头)\s*(?P<index>[零一二两三四五六七八九十百0-9]+)(?:[（(][^）)]+[）)])?\s*[:：]"
)
_STORYBOARD_LABEL_EN = re.compile(
    r"^(?:shot|scene)\s*(?P<index>\d+)(?:\s*[（(][^）)]+[）)])?\s*:",
    flags=re.IGNORECASE,
)
def _storyboard_paragraph_number(paragraph: str, *, english: bool) -> int | None:
    pattern = _STORYBOARD_LABEL_EN if english else _STORYBOARD_LABEL_ZH
    match = pattern.match(str(paragraph or "").strip())
    return storyboard_number_token(match.group("index")) if match else None


def _has_contiguous_storyboard_numbers(paragraphs: Sequence[str], *, english: bool) -> bool:
    numbers = [_storyboard_paragraph_number(paragraph, english=english) for paragraph in paragraphs]
    return bool(numbers) and numbers == list(range(1, len(numbers) + 1))


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


def _valid_storyboard_paragraph(paragraph: str, *, english: bool) -> bool:
    label_pattern = _STORYBOARD_LABEL_EN if english else _STORYBOARD_LABEL_ZH
    if not label_pattern.match(paragraph):
        return False
    if len(re.findall(r"[。！？.!?]", paragraph)) < 2:
        return False
    lowered = paragraph.casefold()
    camera_markers = ("camera", "frame", "focus", "shot") if english else ("镜头", "画面", "焦点", "景别", "机位")
    return any(marker in lowered for marker in camera_markers)


def is_natural_video_prompt(text: str, *, language: str = "纯中文") -> bool:
    """Validate an unbounded natural-language storyboard with one causal story arc."""

    prompt = str(text or "").strip()
    mode = str(language or "纯中文").strip()
    if (
        not prompt
        or any(marker in prompt.casefold() for marker in _META_MARKERS)
        or _DURATION_EXPRESSION_PATTERN.search(prompt)
    ):
        return False
    if mode == "英文提示词+中文说明":
        english, marker, chinese = prompt.partition("中文说明：")
        return bool(
            marker
            and re.search(r"[\u4e00-\u9fff]", chinese)
            and is_natural_video_prompt(chinese.strip(), language="纯中文")
            and is_natural_video_prompt(english.strip(), language="纯英文")
        )
    if prompt.count("、") > 18 or len(re.findall(r"(?:^|[，,])[^。.!?]{0,18}(?:[，,]|$)", prompt)) > 48:
        return False
    if mode == "纯英文":
        lowered = prompt.casefold()
        paragraphs = _storyboard_paragraphs(prompt)
        return (
            not re.search(r"[\u4e00-\u9fff]", prompt)
            and len(paragraphs) >= VIDEO_PROMPT_MIN_STORYBOARD_PARAGRAPHS
            and _has_contiguous_storyboard_numbers(paragraphs, english=True)
            and all(_valid_storyboard_paragraph(paragraph, english=True) for paragraph in paragraphs)
            and all(marker in lowered for marker in ("setup", "trigger", "action", "resolution"))
            and any(marker in lowered for marker in ("when", "because", "causes", "consequence"))
        )
    body = prompt.split("中文说明：", 1)[-1] if mode == "英文提示词+中文说明" else prompt
    paragraphs = _storyboard_paragraphs(body)
    return (
        len(paragraphs) >= VIDEO_PROMPT_MIN_STORYBOARD_PARAGRAPHS
        and _has_contiguous_storyboard_numbers(paragraphs, english=False)
        and all(_valid_storyboard_paragraph(paragraph, english=False) for paragraph in paragraphs)
        and all(marker in body for marker in ("建立", "触发", "行动", "收束"))
        and any(marker in body for marker in ("因为", "带来", "随即", "结果"))
        and any(marker in body for marker in ("环境", "光", "声音"))
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
        english = _build_english_video_prompt(settings, primary_prompt=primary_prompt)
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
    "VIDEO_PROMPT_MODEL_SYSTEM_TEMPLATE",
    "VIDEO_PROMPT_SKILL_VERSION",
    "build_video_prompt",
    "is_natural_video_prompt",
    "video_prompt_anchor_roles",
    "video_prompt_required_anchors",
]
