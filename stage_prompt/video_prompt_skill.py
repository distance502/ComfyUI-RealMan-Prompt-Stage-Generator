# -*- coding: utf-8 -*-
"""Natural-language video prompt skill built from the normalized stage state."""

from __future__ import annotations

import hashlib
import re
from collections import OrderedDict
from typing import Any, Mapping, Sequence

try:
    from .narrative import build_narrative_plan
except Exception:  # pragma: no cover - direct file loading in focused tests
    from stage_prompt_narrative_test import build_narrative_plan  # type: ignore


VIDEO_PROMPT_SKILL_VERSION = "video-prompt-skill-v3"
VIDEO_PROMPT_DURATION_SECONDS = 8
VIDEO_PROMPT_MIN_CHARS_ZH = 800
VIDEO_PROMPT_MAX_CHARS_ZH = 1200
VIDEO_PROMPT_MODEL_SYSTEM_TEMPLATE = """
你是 Qwen TE 的视频提示词后置导演 Skill。输入已经是独立视频 Skill 生成的可靠底稿，你只负责把它润色得更自然、更具体、更适合视频生成，不得另起故事。

硬规则：
1. 只输出最终视频提示词正文，不输出标题、分析、思考过程、Markdown、标签列表、参数或“提示词：”。
2. 严格保留底稿中的主体、服装、场景、动作、道具、镜头方向、光影、声音和最终定格；不得更换地点、增加人物或制造第二条剧情线。
3. 按可见时间顺序写清起因、触发、动作、环境反馈和结果。所有变化都要有前因，不使用互相冲突的动作、机位或时间描述。
4. 使用连贯自然语言，不堆关键词，不复述规则，不写模型无法直接拍摄的抽象评价。
5. 保持连续单镜头，只允许一个主要运镜。可以优化措辞和补足连续性，但不能把底稿改成分镜表、多镜头剪辑或旁白脚本；正文不得出现具体秒数或时长参数。
6. 中文正文必须为 800-1200 字；纯英文正文保持 90-230 个英文单词；双语模式的英文正文后必须保留“中文说明：”，且中文说明为 800-1200 字。
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


def _first(groups: Mapping[str, list[str]], name: str, fallback: str = "") -> str:
    values = groups.get(name, [])
    return values[0] if values else fallback


def _pair(groups: Mapping[str, list[str]], name: str) -> str:
    values = groups.get(name, [])[:2]
    if not values:
        return ""
    return values[0] if len(values) == 1 else f"{values[0]}和{values[1]}"


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
    if any(marker in subject for marker in ("女性", "女人", "女孩", "少女", "母亲", "姐姐", "妹妹", "女主")):
        return "她"
    if any(marker in subject for marker in ("男性", "男人", "男孩", "少年", "父亲", "哥哥", "弟弟", "男主")):
        return "他"
    if any(marker in subject for marker in ("两人", "众人", "人群", "团队", "一行人")):
        return "他们"
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


def _fit_chinese_video_prompt(text: str, details: Sequence[str]) -> str:
    """Keep Chinese video prose in the requested range without cutting a sentence in half."""

    result = _dedupe_sentences(text)
    for detail in details:
        if len(result) >= VIDEO_PROMPT_MIN_CHARS_ZH:
            break
        candidate = _dedupe_sentences(f"{result}{detail}")
        if candidate == result:
            continue
        result = candidate
    if len(result) <= VIDEO_PROMPT_MAX_CHARS_ZH:
        return result
    sentences = [part.strip() for part in re.split(r"(?<=[。！？.!?])\s*", result) if part.strip()]
    while sentences and len("".join(sentences)) > VIDEO_PROMPT_MAX_CHARS_ZH:
        sentences.pop()
    return "".join(sentences).strip()


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
    props = _first(groups, "道具世界观") or "场景中的关键线索"
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
    trigger = _personalize(plan.get("trigger_zh"), reference, scene)
    escalation = _personalize(plan.get("escalation_zh"), reference, scene)
    ending = _personalize(plan.get("ending_zh"), reference, scene)
    camera = _camera_move_zh(action, composition, scene, seed=seed).replace("主体", subject)
    feedback = _environment_feedback_zh(scene, action, reference, outfit)
    outfit_clause = f"身穿{outfit}，" if outfit and not non_person else ""
    brief_clause = f"这一小段围绕“{brief}”展开。" if brief else ""
    text = (
        f"这是一段采用{style}表现的连续单镜头视频。{brief_clause}"
        f"{scene}里，{subject}{outfit_clause}把{props}当作眼前唯一需要确认的线索。"
        f"起初，{reference}只是停下来观察；但因为{trigger}，{reference}立刻{action}。"
        f"这个动作随即带来可见结果：{escalation}。{feedback}。"
        f"镜头从{composition}开始，{camera}，全程只围绕这一次行动，不切换地点，也不突然增加人物。"
        f"{lighting}贯穿镜头，明暗和色温随着{reference}的位置自然变化。"
        f"{_audio_zh(scene, action, non_person)}。最后，{ending}，让故事停在结果已经出现、下一步仍可继续的时刻。"
    )
    details = (
        f"开场先交代{scene}的空间关系：{reference}位于画面中心偏前，{props}留在视线能够回到的位置，背景始终保持同一处空间，不用新的地点解释变化。",
        f"随后，{reference}先收紧动作再改变方向，手部、肩膀和脚步按照同一个重心完成转身，{action}不是突然跳切，而是由前一刻的观察自然接上。",
        f"动作推进时，镜头保留足够的前方空间，让观众先看见{reference}要去哪里，再看见{reference}如何到达；画面不使用快速摇晃、无理由变焦或额外的蒙太奇切换。",
        f"中段的重点不是堆放更多物件，而是让{props}与{scene}中已有的表面、遮挡和距离变化共同证明刚才发生过什么；环境反馈只在{action}之后出现，不凭空抢在动作前面。",
        f"焦点可以从{reference}的表情和手部短暂移到{props}，随后回到{reference}，景深变化保持缓慢；{outfit or '主体外观'}的材质、边缘和运动方向在前后画面中保持一致。",
        f"声音也按同一条因果线推进：{_audio_zh(scene, action, non_person)}；动作结束后只保留当前空间自然产生的短暂余音，不加入旁白、字幕或突然出现的对白。",
        f"结尾不再安排新的任务，镜头继续观察已经产生的结果；{reference}的视线、{props}的位置和背景灯光共同指向下一步，让定格像故事暂停，而不是把剧情强行结束。",
    )
    return _fit_chinese_video_prompt(text, details)


def _build_english_video_prompt(settings: Mapping[str, Any], *, primary_prompt: str) -> str:
    seed = int(settings.get("运行时随机有效种子", 0) or settings.get("seed", 0) or 0)
    source = _english_source_clause(primary_prompt)
    plan = build_narrative_plan({"source": source}, seed=seed, output_count=1)
    opening = _clean(plan.get("opening_en"), limit=220)
    trigger = _clean(plan.get("trigger_en"), limit=180)
    response = _clean(plan.get("response_en"), limit=180)
    feedback = _clean(plan.get("feedback_en"), limit=200)
    ending = _clean(plan.get("ending_en"), limit=180)
    opening = opening[:1].lower() + opening[1:]
    feedback = feedback[:1].lower() + feedback[1:]
    ending = ending[:1].lower() + ending[1:]
    camera = _camera_move_en(primary_prompt, seed=seed)
    text = (
        f"A continuous single-take video continues this established visual world: {source}. "
        f"At first, {opening}. When {trigger}, the previous rhythm breaks and {response}. "
        f"That decision causes a visible response in the location: {feedback}. "
        f"The camera begins on a readable medium-wide view and {camera}, using only this one motivated movement without changing location or introducing another subject. "
        "Light, reflections, fabric, dust, or moisture react after the movement so every change has a visible cause. "
        "Sound stays grounded in footsteps, material contact, breathing, and the natural ambience of the location, with no narration. "
        f"Finally, {ending}, holding long enough for the consequence to register while leaving the next action open."
    )
    return _dedupe_sentences(text)


def is_natural_video_prompt(text: str, *, language: str = "纯中文") -> bool:
    """Validate prose, temporal continuity, camera intent, and anti-tag-chain rules."""

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
    if "\n" in prompt:
        return False
    if prompt.count("、") > 18 or len(re.findall(r"(?:^|[，,])[^。.!?]{0,18}(?:[，,]|$)", prompt)) > 48:
        return False
    if mode == "纯英文":
        lowered = prompt.casefold()
        return (
            not re.search(r"[\u4e00-\u9fff]", prompt)
            and 90 <= len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", prompt)) <= 230
            and all(marker in lowered for marker in ("at first", "camera", "finally"))
            and any(marker in lowered for marker in ("when", "because", "causes"))
        )
    body = prompt.split("中文说明：", 1)[-1] if mode == "英文提示词+中文说明" else prompt
    return (
        VIDEO_PROMPT_MIN_CHARS_ZH <= len(body) <= VIDEO_PROMPT_MAX_CHARS_ZH
        and all(marker in body for marker in ("起初", "镜头", "最后"))
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
    """Build one independent, single-shot video prompt from the shared creative spine."""

    groups = _normalized_groups(selected, custom_tags, settings)
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
    "VIDEO_PROMPT_MODEL_SYSTEM_TEMPLATE",
    "VIDEO_PROMPT_SKILL_VERSION",
    "build_video_prompt",
    "is_natural_video_prompt",
    "video_prompt_required_anchors",
]
