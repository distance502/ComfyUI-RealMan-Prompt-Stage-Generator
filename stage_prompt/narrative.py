# -*- coding: utf-8 -*-
"""Shared narrative planning and natural-language rendering for prompt outputs."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence, TypedDict


class NarrativePlan(TypedDict):
    signature: str
    arc_id: str
    arc_name_zh: str
    arc_name_en: str
    opening_zh: str
    opening_en: str
    trigger_zh: str
    trigger_en: str
    response_zh: str
    response_en: str
    motive_zh: str
    motive_en: str
    escalation_zh: str
    escalation_en: str
    feedback_zh: str
    feedback_en: str
    climax_zh: str
    climax_en: str
    turn_zh: str
    turn_en: str
    ending_zh: str
    ending_en: str
    emotion_zh: str
    emotion_en: str
    spatial_zh: str
    spatial_en: str
    camera_zh: str
    camera_en: str
    organization: int


CHINESE_NARRATIVE_LENGTH_CONTRACT = "中文成品必须为 800-1200 字自然语言"
ENGLISH_NARRATIVE_LENGTH_CONTRACT = "English target 420-560 words"

VISUAL_LAYOUT_SINGLE_PERSON = "single_person"
VISUAL_LAYOUT_SINGLE_NON_PERSON = "single_non_person"
VISUAL_LAYOUT_MULTI_SUBJECT = "multi_subject"
VISUAL_LAYOUT_MULTI_VIEW = "multi_view"

_MULTI_VIEW_CONTAINER_MARKERS = (
    "角色设定图",
    "角色三视图",
    "多视角角色展示",
    "四联画构图",
    "镜中视图",
    "character sheet",
    "character-sheet",
    "character turnaround",
    "turnaround",
    "multi-view",
    "multi-view character",
    "four-panel composition",
    "explicit mirror view",
)
_MULTI_VIEW_ANGLE_MARKERS = (
    "正面视图",
    "侧面视图",
    "背面视图",
    "front view",
    "side view",
    "back view",
)
_MULTI_SUBJECT_MARKERS = (
    "双人",
    "双女性",
    "双成年男性",
    "两人",
    "二人",
    "三人",
    "情侣",
    "伴侣",
    "夫妇",
    "男女配对",
    "多女性",
    "多人",
    "群像",
    "团队",
    "队伍",
    "小队",
    "duo",
    "couple",
    "two people",
    "two women",
    "two men",
    "group portrait",
    "ensemble cast",
)
_NEGATED_LAYOUT_TERMS = (
    "避免",
    "禁止",
    "不要",
    "不得",
    "不能",
    "并非",
    "不是",
    "不含",
    "没有",
    "排除",
    "no ",
    "not ",
    "without ",
    "avoid ",
    "exclude ",
)

_POSITIVE_IDENTITY_ARTIFACT_MARKERS = (
    "克隆主体",
    "克隆人物",
    "复制人物",
    "重复人物",
    "重复脸",
    "重复头部",
    "额外头部",
    "一人多脸",
    "双重面孔",
    "重影人物",
    "重影脸",
    "脸部重影",
    "背景幽灵脸",
    "幽灵脸",
    "人物前后重复",
    "前景背景同一人物",
    "前后景同一人物",
    "前后重复身体",
    "半透明人物残影",
    "透明复制人物",
    "动作残影复制身体",
    "身体双重曝光",
    "多个人脸",
    "cloned subject",
    "cloned person",
    "duplicated person",
    "repeated person",
    "repeated face",
    "duplicate face",
    "duplicate head",
    "extra head",
    "multiple faces on one person",
    "double face",
    "ghosted face",
    "ghost face",
    "foreground and background duplicate subject",
    "same person repeated in foreground and background",
    "transparent duplicate person",
    "motion trail duplicating the body",
    "double-exposed body",
)
_POSITIVE_SINGLE_FRAME_ARTIFACT_MARKERS = (
    "上下重复画面",
    "上下分屏",
    "左右分屏",
    "分屏构图",
    "纵向分屏",
    "横向分屏",
    "双联画",
    "三联画",
    "拼贴画",
    "故事板分镜",
    "漫画分格",
    "照片联系表",
    "堆叠肖像",
    "平铺重复图像",
    "画中画",
    "多场景并列",
    "时间切片",
    "复制倒影",
    "vertically duplicated image",
    "vertical split screen",
    "horizontal split screen",
    "diptych",
    "triptych",
    "collage",
    "storyboard panels",
    "comic panels",
    "contact sheet",
    "stacked portraits",
    "tiled repeated image",
    "picture-in-picture",
    "multiple scenes in one image",
    "time slicing",
    "cloned reflection",
)


def _layout_sources(tags: Sequence[Any] | str | None, settings: Mapping[str, Any] | None) -> list[str]:
    if isinstance(tags, str):
        values: list[Any] = [tags]
    else:
        values = list(tags or [])
    active_settings = settings or {}
    values.extend(
        active_settings.get(key, "")
        for key in (
            "额外要求",
            "智能文本输入",
            "NSFW工作台标签摘要",
            "角色设定图内部策略",
        )
    )
    return [str(value or "").strip() for value in values if str(value or "").strip()]


def _marker_is_negated(source: str, start: int) -> bool:
    prefix = source[max(0, start - 18) : start].casefold()
    prefix = re.split(r"[。！？.!?；;，,、：:\n]", prefix)[-1]
    compact = re.sub(r"\s+", " ", prefix)
    return any(term in compact for term in _NEGATED_LAYOUT_TERMS)


def _positive_marker_hits(sources: Sequence[str], markers: Sequence[str]) -> set[str]:
    hits: set[str] = set()
    for source in sources:
        lowered = source.casefold()
        for marker in markers:
            marker_key = marker.casefold()
            start = lowered.find(marker_key)
            while start >= 0:
                if not _marker_is_negated(lowered, start):
                    hits.add(marker_key)
                    break
                start = lowered.find(marker_key, start + len(marker_key))
    return hits


def _has_positive_layout_marker(sources: Sequence[str], markers: Sequence[str]) -> bool:
    return bool(_positive_marker_hits(sources, markers))


def resolve_visual_layout_mode(
    tags: Sequence[Any] | str | None = None,
    settings: Mapping[str, Any] | None = None,
    *,
    non_person: bool | None = None,
) -> str:
    """Resolve one global subject/layout contract without overriding explicit modes."""

    active_settings = settings or {}
    configured = str(active_settings.get("画面结构模式解析结果", "") or "").strip()
    valid_modes = {
        VISUAL_LAYOUT_SINGLE_PERSON,
        VISUAL_LAYOUT_SINGLE_NON_PERSON,
        VISUAL_LAYOUT_MULTI_SUBJECT,
        VISUAL_LAYOUT_MULTI_VIEW,
    }
    sources = _layout_sources(tags, active_settings)
    if _has_positive_layout_marker(sources, _MULTI_VIEW_CONTAINER_MARKERS):
        return VISUAL_LAYOUT_MULTI_VIEW
    if len(_positive_marker_hits(sources, _MULTI_VIEW_ANGLE_MARKERS)) >= 2:
        return VISUAL_LAYOUT_MULTI_VIEW
    if _has_positive_layout_marker(sources, _MULTI_SUBJECT_MARKERS):
        return VISUAL_LAYOUT_MULTI_SUBJECT
    explicit_tags = [str(value or "").strip() for value in ([tags] if isinstance(tags, str) else list(tags or []))]
    if configured in valid_modes and not any(explicit_tags):
        return configured
    if non_person is None:
        subject_type = str(
            active_settings.get("主体类型解析结果", "")
            or active_settings.get("主体类型", "")
            or ""
        ).strip()
        non_person = subject_type == "非人物主体"
    return VISUAL_LAYOUT_SINGLE_NON_PERSON if non_person else VISUAL_LAYOUT_SINGLE_PERSON


def visual_layout_contract(mode: str, *, english: bool = False) -> str:
    resolved = str(mode or VISUAL_LAYOUT_SINGLE_PERSON).strip()
    if english:
        if resolved == VISUAL_LAYOUT_MULTI_VIEW:
            return (
                "Honor the explicitly selected character-sheet, turnaround, panel, or mirror-view structure and use exactly the requested views. "
                "For a standard three-view character turnaround, place exactly three primary full-body views from left to right: front at 0 degrees, "
                "one true side profile at 90 degrees, and back at 180 degrees. Give them three equal-width columns in a balanced 1:1:1 layout, "
                "with identical character height, one shared head line and ground baseline, matching camera height, orthographic projection, neutral stance, "
                "complete head-to-foot framing, equal margins, and clearly separated silhouettes. Preserve one continuous identity with matching face, anatomy, hairstyle, wardrobe, palette, and materials. "
                "Only an explicitly requested headshot or material detail may enter a separate support strip without reducing the three primary views; "
                "an explicitly requested alternative multi-view structure keeps its requested count but distributes every view evenly."
            )
        if resolved == VISUAL_LAYOUT_MULTI_SUBJECT:
            return (
                "Use one continuous image at one decisive instant. Keep every explicitly selected person in the same space; "
                "each person has one complete body, one readable head and face, a fixed position, and an independent silhouette. "
                "Foreground, middle ground, and background continue one perspective and one moment."
            )
        if resolved == VISUAL_LAYOUT_SINGLE_NON_PERSON:
            return (
                "Use one continuous image at one decisive instant. The main non-human subject holds one complete, stable silhouette "
                "and one coherent structure; material traces and environmental response carry the surrounding story inside the same perspective."
            )
        return (
            "Use one continuous image at one decisive instant. The entire frame contains only this one person, with one complete body, "
            "one readable head and face, and one current pose. Foreground, middle ground, and background continue one perspective, one space, and one moment."
        )
    if resolved == VISUAL_LAYOUT_MULTI_VIEW:
        return (
            "标准三视图从左到右为正面0度、单个90度标准侧面、背面180度三幅全身，横向三栏等宽且1:1:1均衡布局。"
            "人物等高，同一头顶线与脚底基线、统一镜头高度、正交投影、中性站姿和完整头脚。各视图共享同一身份、服装和脸部结构，"
            "体型、发型、配色、材质一致；要求的细节另置且不改变主视图尺寸。其他多视图按指定数量均分。"
        )
    if resolved == VISUAL_LAYOUT_MULTI_SUBJECT:
        return (
            "一张连续画面定格在同一决定性时刻；所有显式人物同处一景，每位人物都有唯一完整的身体、头部和脸部，"
            "站位与轮廓彼此独立，前景、中景和背景延续同一透视、同一空间与同一时刻。"
        )
    if resolved == VISUAL_LAYOUT_SINGLE_NON_PERSON:
        return (
            "一张连续画面定格在同一决定性时刻；非人物主主体拥有唯一完整轮廓与统一结构，"
            "材质痕迹、功能状态和环境反馈在同一透视关系里共同呈现前因后果。"
        )
    return (
        "一张连续画面定格在同一决定性时刻；整张画面只有这一位人物，人物身份、身体、头部和脸部各自保持唯一且完整；"
        "相机沿一个视点记录当前姿态，前景、中景和背景延续同一透视、同一空间与同一时刻。"
    )


def prompt_is_positive_layout_safe(text: str, mode: str) -> bool:
    """Reject artifact vocabulary that should live in the negative prompt only."""

    source = str(text or "").casefold()
    if not source:
        return False
    if any(marker.casefold() in source for marker in _POSITIVE_IDENTITY_ARTIFACT_MARKERS):
        return False
    if str(mode or "").strip() != VISUAL_LAYOUT_MULTI_VIEW and any(
        marker.casefold() in source for marker in _POSITIVE_SINGLE_FRAME_ARTIFACT_MARKERS
    ):
        return False
    return True


def prompt_preserves_visual_layout(text: str, mode: str) -> bool:
    source = str(text or "").casefold()
    resolved = str(mode or "").strip()
    if not source or not resolved or not prompt_is_positive_layout_safe(source, resolved):
        return False
    if resolved == VISUAL_LAYOUT_MULTI_VIEW:
        return bool(_positive_marker_hits([source], _MULTI_VIEW_CONTAINER_MARKERS)) or len(
            _positive_marker_hits([source], _MULTI_VIEW_ANGLE_MARKERS)
        ) >= 2
    if resolved == VISUAL_LAYOUT_MULTI_SUBJECT:
        return any(
            marker in source
            for marker in (
                "每位人物都有唯一完整的身体",
                "每人只出现一次",
                "每位人物只出现一次",
                "each person has one complete body",
                "each person exactly once",
            )
        )
    if resolved == VISUAL_LAYOUT_SINGLE_NON_PERSON:
        return any(marker in source for marker in ("非人物主主体拥有唯一完整轮廓", "非人物主主体只出现一次", "one complete, stable silhouette", "main non-human subject once"))
    preserved = any(
        marker in source
        for marker in (
            "整张画面只有这一位人物",
            "同一人物只出现一次",
            "entire frame contains only this one person",
            "same person exactly once",
        )
    )
    return preserved and not _has_positive_layout_marker([source], _MULTI_SUBJECT_MARKERS)


GLOBAL_NARRATIVE_MODEL_CONTRACT = f"""
全局剧情与自然语言合同：
- 每条输出都必须像一段可被摄影机捕捉的视觉叙事，而不是标签清单或固定六段模板。先建立地点、事件前提和行动动机，再让动作、环境、光线和镜头围绕同一事件产生因果关系。
- 正文必须形成“处境与动机、事件触发、主体回应、局势升级、情绪转折、环境与光线反馈、视觉高潮、开放定格”的完整链路；即使是物体、机械、建筑或纯风景，也要用状态变化、功能响应或自然运动建立剧情，不得硬套人物情绪。
- 用户标签是必须保留的事实锚点；剧情扩写只能连接锚点和补足未指定的可见细节，不得替换用户选定的主体、服装、场景、动作、构图、风格或成人属性。
- 模板只决定媒介、渲染与成片质感，主题池只决定主体、事件和地点内容；每条只能有一个主模板轨道和一个主主题轨道。显式模板优先，主题不得注入冲突媒介；平衡模式最多保留一个兼容质感桥，严格模式不保留跨媒介词，漂移模式也只能有一个有意的次风格。
- 每次生成应重新选择叙事弧、行动目的、升级方式、空间动线、环境反馈、视觉高潮、镜头时机、情绪转折和结尾状态。批量各条至少在其中四项明显不同，不能只换同义词、开头或形容词；最近历史只用于避重，不得成为下一条的素材来源。
- 使用连续自然句和具体可见信息。少写“画面呈现、整体营造、高质量、氛围感”等空泛套话，多写动作造成的衣料变化、道具位移、视线方向、前中后景关系、光影迁移、空气与材质反馈。
- 所有渠道共用同一画面结构合同：默认人物模式是一张连续画面、一个决定性时刻、同一人物仅出现一次且只有一个清晰头部和一张脸；显式双人/群像保留用户人数，但每人只出现一次且站位可读；只有显式角色设定图、三视图、四联画或镜中视图允许多视图。除显式多视图外，禁止上下/左右分屏、双联画、三联画、拼贴、故事板、漫画分格、堆叠肖像、画中画、复制倒影和时间切片。
- 上一条中的排除词只属于创作指令和推荐负面提示词，最终正向正文不得复述“分屏、克隆、重复脸、额外头部、重影、拼贴”等错误视觉概念，也不得把它们包装在“不要/避免/无”后面。正向正文只写唯一主体、完整身体、清晰脸部、准确数量、同一透视和干净表面等期望结果。
- 剧情链是创作推理，不是要求模型同时画出开端、经过和结尾。最终画面只显示最有信息量的当前瞬间；此前与此后的事件只能通过姿态余势、道具状态、衣料变化、环境痕迹、视线和光线结果暗示，不能让同一主体以多个姿势、多个年龄或多个镜头重复出现。
- {CHINESE_NARRATIVE_LENGTH_CONTRACT}；{ENGLISH_NARRATIVE_LENGTH_CONTRACT}。简洁档靠近下限，标准档建议 900-1050 字，详细档靠近上限，但所有中文成品仍须处于 800-1200 字范围。长度必须来自新信息、空间关系和事件推进，禁止近义反复灌水。
""".strip()


_NARRATIVE_ARCS: tuple[dict[str, str], ...] = (
    {
        "id": "arrival_discovery",
        "name_zh": "抵达与发现",
        "name_en": "arrival and discovery",
        "opening_zh": "故事从一次刚刚发生的抵达开始，主体仍在确认陌生空间里的方向与距离",
        "opening_en": "The story begins just after an arrival, while the subject is still measuring the unfamiliar space and its distances",
        "trigger_zh": "环境里一个不合常态的细节打破了短暂平静",
        "trigger_en": "one detail in the environment breaks the brief calm",
        "response_zh": "主体先停顿辨认，再做出带有明确目的的回应",
        "response_en": "the subject pauses to read it and then answers with a deliberate movement",
        "turn_zh": "情绪由谨慎观察转为清醒决断",
        "turn_en": "the emotion turns from guarded observation to lucid resolve",
        "ending_zh": "答案尚未完全揭开，画面停在下一步即将发生的瞬间",
        "ending_en": "the answer remains incomplete, and the frame holds just before the next step",
    },
    {
        "id": "preparation_interruption",
        "name_zh": "准备与打断",
        "name_en": "preparation and interruption",
        "opening_zh": "故事从一项即将完成的准备开始，主体原本拥有稳定而清楚的行动节奏",
        "opening_en": "The story opens during a preparation that is almost complete, with the subject moving in a controlled rhythm",
        "trigger_zh": "一个突如其来的信号迫使原有计划中断",
        "trigger_en": "an abrupt signal interrupts the original plan",
        "response_zh": "主体没有仓促逃离，而是在短暂停顿后重新选择行动方向",
        "response_en": "rather than fleeing, the subject pauses and deliberately chooses a new direction",
        "turn_zh": "情绪由专注平稳转为克制警觉",
        "turn_en": "the emotion shifts from quiet focus to restrained alertness",
        "ending_zh": "画面定格在决定已经做出、后果尚未到来的间隙",
        "ending_en": "the frame settles in the interval after the decision but before its consequence",
    },
    {
        "id": "observation_change",
        "name_zh": "观察与异变",
        "name_en": "observation and change",
        "opening_zh": "镜头像偶然跟到一次安静观察，主体尚未介入眼前发生的事情",
        "opening_en": "The camera seems to arrive during a quiet observation, before the subject has intervened",
        "trigger_zh": "空间中的光、声音或运动方向突然发生可见变化",
        "trigger_en": "the direction of light, sound, or motion in the space changes visibly",
        "response_zh": "主体顺着变化调整视线与重心，让原本静止的关系开始流动",
        "response_en": "the subject follows the change with gaze and weight, setting the previously still relationships in motion",
        "turn_zh": "情绪由疏离旁观转为被事件牵引",
        "turn_en": "the emotion turns from detached observation to active involvement",
        "ending_zh": "最终定格保留一个悬而未决的方向，让背景继续讲述未说完的部分",
        "ending_en": "the final frame leaves one direction unresolved so the background can carry the unfinished thought",
    },
    {
        "id": "conflict_movement",
        "name_zh": "冲突与移动",
        "name_en": "conflict and movement",
        "opening_zh": "故事从冲突已经发生之后切入，现场留下的秩序正在被重新排列",
        "opening_en": "The story enters just after a conflict has begun, while the order of the location is being rearranged",
        "trigger_zh": "一股来自画外的压力逼近主体所在的位置",
        "trigger_en": "pressure from outside the frame closes in on the subject's position",
        "response_zh": "主体用一次有方向的移动夺回主动，并让周围材质留下动作痕迹",
        "response_en": "a directional movement lets the subject reclaim initiative and leaves physical traces in nearby materials",
        "turn_zh": "情绪由受压克制转为果断反击",
        "turn_en": "the emotion changes from contained pressure to decisive resistance",
        "ending_zh": "镜头停在力量刚刚释放、环境仍在回应的临界点",
        "ending_en": "the camera holds at the threshold after force is released while the environment is still responding",
    },
    {
        "id": "trace_revelation",
        "name_zh": "线索与揭示",
        "name_en": "trace and revelation",
        "opening_zh": "故事围绕一条不起眼的线索展开，主体先从空间边缘捕捉到它的存在",
        "opening_en": "The story develops around a minor trace first noticed at the edge of the space",
        "trigger_zh": "线索与场景中的另一处细节形成呼应，暗示这里刚刚发生过某件事",
        "trigger_en": "the trace echoes another detail and suggests that something has just happened here",
        "response_zh": "主体循着这层联系靠近，让动作同时承担观察与选择的意义",
        "response_en": "the subject follows that connection, making the movement carry both observation and choice",
        "turn_zh": "情绪由好奇试探转为理解后的沉静",
        "turn_en": "the emotion moves from tentative curiosity to the stillness of understanding",
        "ending_zh": "结尾不直接说明答案，而用主体的视线和空间留白完成揭示",
        "ending_en": "the ending avoids stating the answer and reveals it through gaze and spatial absence",
    },
    {
        "id": "waiting_signal",
        "name_zh": "等待与信号",
        "name_en": "waiting and signal",
        "opening_zh": "主体已经等待了一段时间，重复的环境节奏让这一刻显得格外安静",
        "opening_en": "The subject has been waiting, and the repeating rhythm of the environment makes the moment unusually quiet",
        "trigger_zh": "一个迟来的信号终于出现，却与预期并不完全相同",
        "trigger_en": "a delayed signal finally arrives, though it does not match the expectation",
        "response_zh": "主体在接受与离开之间作出选择，动作因此带着短暂犹豫后的确定感",
        "response_en": "the subject chooses between accepting it and leaving, so the movement carries certainty after hesitation",
        "turn_zh": "情绪由耐心压抑转为释然又保持戒备",
        "turn_en": "the emotion shifts from contained patience to relief that still retains caution",
        "ending_zh": "画面停在等待结束而新的问题刚刚开始的位置",
        "ending_en": "the frame ends where the waiting is over and a new question has only begun",
    },
    {
        "id": "routine_anomaly",
        "name_zh": "日常与异常",
        "name_en": "routine and anomaly",
        "opening_zh": "故事先建立一个可信的日常动作，让主体与空间显得彼此熟悉",
        "opening_en": "The story first establishes a believable routine, making the subject and location feel familiar to one another",
        "trigger_zh": "一处微小异常悄然进入画面，并逐渐改变原有节奏",
        "trigger_en": "a small anomaly enters the frame and gradually changes that rhythm",
        "response_zh": "主体保持表面平静，却通过视线、手势或重心变化暴露真实反应",
        "response_en": "the subject remains outwardly calm while gaze, gesture, or weight reveals the true reaction",
        "turn_zh": "情绪由松弛日常转为含蓄不安",
        "turn_en": "the emotion turns from relaxed routine to understated unease",
        "ending_zh": "最终定格让异常仍留在画面边缘，形成可以继续想象的余韵",
        "ending_en": "the final frame leaves the anomaly near the edge, preserving room for the story to continue",
    },
    {
        "id": "pursuit_obstacle",
        "name_zh": "追寻与阻碍",
        "name_en": "pursuit and obstacle",
        "opening_zh": "故事从主体已经明确目标的途中开始，画面天然带着向前推进的方向",
        "opening_en": "The story begins after the subject has chosen a goal, giving the frame a natural forward direction",
        "trigger_zh": "空间中的阻碍迫使行动路线发生改变",
        "trigger_en": "an obstacle in the space forces the route to change",
        "response_zh": "主体借助现有环境重新组织动作，在受限条件里找到新的出口",
        "response_en": "the subject uses the existing environment to reorganize the movement and find another way through",
        "turn_zh": "情绪由急切推进转为沉着应变",
        "turn_en": "the emotion turns from urgency to composed improvisation",
        "ending_zh": "镜头停在障碍被绕开、目标重新进入视线的时刻",
        "ending_en": "the camera holds when the obstacle is cleared and the goal comes back into view",
    },
    {
        "id": "exchange_misread",
        "name_zh": "交换与误读",
        "name_en": "exchange and misreading",
        "opening_zh": "故事从一次看似普通的交换开始，主体原本以为双方已经理解彼此意图",
        "opening_en": "The story begins with an apparently ordinary exchange, when the subject assumes the intention has been understood",
        "trigger_zh": "对方或环境给出的回应与预期错开，暴露出关键信息被误读",
        "trigger_en": "the answer arrives slightly off expectation and reveals that a crucial detail was misread",
        "response_zh": "主体没有立即纠正，而是改变动作节奏，用一个更清楚的可见信号重新表达意图",
        "response_en": "the subject does not correct it verbally, but changes the rhythm and offers a clearer visible signal",
        "turn_zh": "情绪由短暂尴尬转为审慎坦率",
        "turn_en": "the emotion turns from brief awkwardness to careful candor",
        "ending_zh": "画面停在新的理解刚刚建立、双方尚未给出最终答案的片刻",
        "ending_en": "the frame holds as a new understanding forms before either side gives a final answer",
    },
    {
        "id": "rescue_cost",
        "name_zh": "援助与代价",
        "name_en": "aid and consequence",
        "opening_zh": "故事从主体已经察觉某处失衡开始，时间与空间都不允许长久观望",
        "opening_en": "The story begins when the subject recognizes an imbalance and the location no longer permits passive observation",
        "trigger_zh": "一个正在扩大的变化让原本可以回避的问题变得必须处理",
        "trigger_en": "an expanding change turns an avoidable problem into one that must be addressed",
        "response_zh": "主体借助手边结构或道具介入，并承担位置、时间或安全感被改变的代价",
        "response_en": "the subject intervenes through an available structure or prop and accepts a visible cost in position, time, or security",
        "turn_zh": "情绪由克制评估转为专注承担",
        "turn_en": "the emotion moves from restrained assessment to focused commitment",
        "ending_zh": "危机暂时被控制，但留下的痕迹说明这次选择仍会继续影响下一刻",
        "ending_en": "the immediate danger is contained, yet its traces show that the choice will shape the next moment",
    },
    {
        "id": "threshold_choice",
        "name_zh": "门槛与选择",
        "name_en": "threshold and choice",
        "opening_zh": "主体来到一个无法同时保留两种可能的边界位置，动作因此带着明显停顿",
        "opening_en": "The subject reaches a threshold where two possibilities cannot both be kept, giving the movement a visible pause",
        "trigger_zh": "来自身后或前方的变化缩短了继续犹豫的时间",
        "trigger_en": "a change ahead or behind shortens the time available for hesitation",
        "response_zh": "主体先确认最重要的锚点，再跨出或收回决定性的一步",
        "response_en": "the subject confirms the most important anchor before taking or withdrawing one decisive step",
        "turn_zh": "情绪由拉扯迟疑转为承担结果的平静",
        "turn_en": "the emotion turns from divided hesitation to calm acceptance of consequence",
        "ending_zh": "镜头定格在边界已被越过、原有空间仍清晰可见的位置",
        "ending_en": "the camera holds after the boundary is crossed while the former space remains visibly present",
    },
    {
        "id": "departure_return",
        "name_zh": "离开与回返",
        "name_en": "departure and return",
        "opening_zh": "故事从主体已经开始离开时切入，空间中的细节正逐渐从近处退向背景",
        "opening_en": "The story enters after departure has begun, as details of the place begin to recede into the background",
        "trigger_zh": "一个被忽略的声音、反光或物件迫使主体重新看向来处",
        "trigger_en": "an overlooked sound, reflection, or object forces the subject to look back",
        "response_zh": "主体改变原有动线，以一次回返确认那个细节是否值得重新选择",
        "response_en": "the subject reverses the route long enough to decide whether the detail deserves a different choice",
        "turn_zh": "情绪由自我保护转为愿意面对未完成之事",
        "turn_en": "the emotion shifts from self-protection to willingness to face what remains unfinished",
        "ending_zh": "最终定格不说明主体会留下还是再次离开，只让回返的痕迹保持可见",
        "ending_en": "the final frame does not say whether the subject will stay or leave again, only preserving the trace of return",
    },
)


_SPATIAL_PROGRESSIONS_ZH = (
    "视觉动线从前景的细节线索进入中景行动，再由背景中的未完成信息收束",
    "空间先以背景建立处境，再让中景动作改变关系，最后用前景遮挡形成临场距离",
    "视线沿主体的动作方向横向穿过画面，并在远处的回应元素上停下",
    "景深由清晰前景逐渐过渡到带有空气层次的背景，使事件像正在真实空间里延续",
)
_SPATIAL_PROGRESSIONS_EN = (
    "the visual path moves from a foreground clue into the middle-ground action and resolves against unfinished information in the background",
    "the background establishes the situation first, the middle-ground action changes it, and a foreground overlap creates immediate distance",
    "the eye travels laterally with the subject's movement and settles on a responding element farther away",
    "depth moves from a precise foreground into an atmospheric background, letting the event continue through believable space",
)
_CAMERA_BEATS_ZH = (
    "镜头先交代空间，再在动作真正改变局势时靠近主体",
    "镜头像一位保持距离的见证者，在情绪转折处才让焦点落到表情与手部",
    "取景保留动作前后的空间余量，让观者能够读出主体从哪里来、将往哪里去",
    "镜头停在动作尚未完全结束的半拍，衣料、尘雾、反射或发丝继续证明运动方向",
)
_CAMERA_BEATS_EN = (
    "the camera establishes the location before moving closer when the action truly changes the situation",
    "the camera behaves like a distant witness and only gives focus to expression and hands at the emotional turn",
    "the framing preserves space before and after the movement so the viewer can read where the subject came from and where it may go",
    "the exposure holds half a beat before the movement is complete, allowing fabric, dust, reflections, or hair to preserve its direction",
)

_MOTIVATION_BEATS_ZH = (
    "这段行动有直接目标：在条件继续改变前确认异常来自哪里",
    "主体来到这里并非偶然，而是要完成一项仍缺最后证据的任务",
    "当前选择源于对某个承诺、关系或功能状态的维护",
    "行动的目的不是展示外观，而是把一条中断的路线重新接续起来",
    "主体需要在有限时间内判断眼前信号是否可信",
    "这一刻承担着取回、交付、保护或放下某件事的明确意图",
    "主体试图恢复空间原有秩序，却很快发现旧方法已经失效",
    "当前动机来自一次未完成的确认，任何移动都会改变后续结果",
)
_MOTIVATION_BEATS_EN = (
    "The immediate objective is to identify the source of the anomaly before conditions change again",
    "The subject is here to complete a task that still lacks its final piece of evidence",
    "The present choice comes from protecting a promise, relationship, or functional state",
    "The action is meant to reconnect an interrupted route rather than merely display appearance",
    "The subject must decide within limited time whether the visible signal can be trusted",
    "The moment carries a clear intention to retrieve, deliver, protect, or release something",
    "The subject attempts to restore the location's former order and discovers that the old method no longer works",
    "The motive comes from unfinished confirmation, with every movement changing what can happen next",
)
_ESCALATION_BEATS_ZH = (
    "原本局部的变化沿空间边缘扩散，迫使回应从观察升级为真正介入",
    "第二个信号从画外出现，使主体刚做出的判断立即面临修正",
    "环境节奏突然加快，留给动作完成的时间被明显压缩",
    "关键道具发生位移或状态改变，让原有退路不再可靠",
    "光线先于主体抵达新的位置，暴露出此前隐藏的空间关系",
    "前景遮挡被打破，背景中的后果第一次进入清楚视线",
    "主体的回应引发连锁反馈，使周围材质、空气与距离同时变化",
    "局势并未立刻失控，却出现一个足以改变下一步优先级的新细节",
)
_ESCALATION_BEATS_EN = (
    "The local disturbance spreads along the edge of the space, forcing observation to become intervention",
    "A second signal enters from outside the frame and immediately challenges the subject's decision",
    "The environmental rhythm accelerates and visibly shortens the time available to finish the movement",
    "A key prop shifts position or state, making the former route of retreat unreliable",
    "Light reaches the next position before the subject and exposes a previously hidden spatial relationship",
    "A foreground obstruction breaks apart and the consequence in the background becomes readable for the first time",
    "The response produces a chain reaction across material, air, and distance",
    "The situation remains controlled but a new detail changes the priority of the next step",
)
_ENVIRONMENT_FEEDBACKS_ZH = (
    "接触造成的细微振动沿地面或结构传开，近处尘粒、薄雾与反射依次响应",
    "风向随动作改变，衣料、草木、烟雾或附着物共同标出运动路径",
    "水面、玻璃或金属先映出变化，再把破碎高光送向背景深处",
    "温度与湿度差让呼吸、水汽、凝露或热浪成为可见的时间证据",
    "前景物体发生轻微位移，中景行动与远景结果因此被连成一条线",
    "阴影边界缓慢越过主体与道具，说明事件仍在画外继续推进",
    "空间回声与重复结构强化距离感，空处也保留刚发生过动作的痕迹",
    "环境颜色不是静态滤镜，而随主光迁移从冷静逐步转向紧张或释然",
)
_ENVIRONMENT_FEEDBACKS_EN = (
    "Fine vibration travels through the ground or structure, with dust, mist, and reflections answering in sequence",
    "The movement changes the airflow, allowing fabric, vegetation, smoke, or surface attachments to trace its path",
    "Water, glass, or metal registers the change first and sends fragmented highlights into the background",
    "Differences in temperature and humidity make breath, condensation, vapor, or heat distortion visible evidence of time",
    "A foreground object shifts slightly, linking the middle-ground action to its distant consequence",
    "A shadow boundary crosses subject and prop slowly enough to show that the event continues outside the frame",
    "Echo and repeating structure reinforce distance, while empty areas preserve the trace of recent movement",
    "Environmental color behaves as moving light rather than a static filter, turning from calm toward tension or release",
)
_VISUAL_CLIMAXES_ZH = (
    "视觉高潮落在主体、关键线索与背景后果短暂对齐的瞬间",
    "最高张力来自动作将要完成却被第二个变化截住的半拍",
    "画面最强的一刻不是夸张姿态，而是视线终于确认目标的微小改变",
    "高潮由主光突然穿过空气层次并照亮决定性接触点形成",
    "前中后景在一个动作方向上同时响应，构成清楚但不封闭的结果",
    "最亮高光从道具移到主体，再停在仍未解决的远景信息上",
    "静止与运动在同一帧交界，细小材质余势比大幅动作更有说服力",
    "镜头在关系刚刚改变时收紧，让表情、结构或手部成为新的视觉中心",
)
_VISUAL_CLIMAXES_EN = (
    "The visual climax occurs when subject, crucial clue, and background consequence align for one brief instant",
    "Peak tension comes half a beat before completion, when a second change interrupts the movement",
    "The strongest moment is not an exaggerated pose but the small shift that confirms the target",
    "The climax forms when key light cuts through atmospheric depth and reaches the decisive contact point",
    "Foreground, middle ground, and background answer along one direction, producing a clear but open result",
    "The brightest highlight travels from prop to subject and settles on unresolved information in the distance",
    "Stillness and motion meet in one frame, with material after-movement carrying more conviction than a broad gesture",
    "The camera tightens as the relationship changes, making expression, structure, or hands the new visual center",
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _stable_plan_number(
    anchors: Mapping[str, Any],
    *,
    output_index: int,
    output_count: int,
    recent_history: Sequence[str],
    seed: int,
) -> int:
    stable_anchors = {
        str(key): _clean(value)
        for key, value in sorted(anchors.items(), key=lambda item: str(item[0]))
        if _clean(value)
    }
    payload = {
        "anchors": stable_anchors,
        "index": max(0, int(output_index or 0)),
        "count": max(1, int(output_count or 1)),
        "recent": [_clean(item) for item in list(recent_history)[-12:] if _clean(item)],
        "seed": max(0, int(seed or 0)),
    }
    digest = hashlib.blake2b(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
        digest_size=16,
    ).digest()
    return int.from_bytes(digest, "big")


def build_narrative_plan(
    anchors: Mapping[str, Any],
    *,
    output_index: int = 0,
    output_count: int = 1,
    recent_history: Sequence[str] = (),
    seed: int = 0,
) -> NarrativePlan:
    """Create a stable per-output story plan that changes with batch index/history."""

    number = _stable_plan_number(
        anchors,
        output_index=0,
        output_count=output_count,
        recent_history=(),
        seed=seed,
    )
    history_number = _stable_plan_number(
        {},
        output_index=0,
        output_count=output_count,
        recent_history=recent_history,
        seed=seed,
    )
    history_step = len([item for item in recent_history if _clean(item)])
    index = max(0, int(output_index or 0))
    arc_index = (number + index * 3 + history_step) % len(_NARRATIVE_ARCS)
    spatial_index = ((number >> 9) + index + history_step * 3) % len(_SPATIAL_PROGRESSIONS_ZH)
    camera_index = ((number >> 17) + index * 2 + history_step) % len(_CAMERA_BEATS_ZH)
    motive_index = ((number >> 21) + index * 5 + history_step) % len(_MOTIVATION_BEATS_ZH)
    escalation_index = ((number >> 29) + index * 3 + history_step * 2) % len(_ESCALATION_BEATS_ZH)
    feedback_index = ((number >> 37) + index * 7 + history_step * 3) % len(_ENVIRONMENT_FEEDBACKS_ZH)
    climax_index = ((number >> 45) + index * 2 + history_step * 5) % len(_VISUAL_CLIMAXES_ZH)
    organization = ((number >> 25) + index + history_step + history_number) % 4
    arc = _NARRATIVE_ARCS[arc_index]
    signature = (
        f"{arc['id']}:{motive_index}:{escalation_index}:{feedback_index}:{climax_index}:"
        f"{spatial_index}:{camera_index}:{organization}:{index}:"
        f"{number & 0xFFFF:04x}:{history_number & 0xFFFF:04x}"
    )
    return {
        "signature": signature,
        "arc_id": arc["id"],
        "arc_name_zh": arc["name_zh"],
        "arc_name_en": arc["name_en"],
        "opening_zh": arc["opening_zh"],
        "opening_en": arc["opening_en"],
        "trigger_zh": arc["trigger_zh"],
        "trigger_en": arc["trigger_en"],
        "response_zh": arc["response_zh"],
        "response_en": arc["response_en"],
        "motive_zh": _MOTIVATION_BEATS_ZH[motive_index],
        "motive_en": _MOTIVATION_BEATS_EN[motive_index],
        "escalation_zh": _ESCALATION_BEATS_ZH[escalation_index],
        "escalation_en": _ESCALATION_BEATS_EN[escalation_index],
        "feedback_zh": _ENVIRONMENT_FEEDBACKS_ZH[feedback_index],
        "feedback_en": _ENVIRONMENT_FEEDBACKS_EN[feedback_index],
        "climax_zh": _VISUAL_CLIMAXES_ZH[climax_index],
        "climax_en": _VISUAL_CLIMAXES_EN[climax_index],
        "turn_zh": arc["turn_zh"],
        "turn_en": arc["turn_en"],
        "ending_zh": arc["ending_zh"],
        "ending_en": arc["ending_en"],
        "emotion_zh": arc["turn_zh"],
        "emotion_en": arc["turn_en"],
        "spatial_zh": _SPATIAL_PROGRESSIONS_ZH[spatial_index],
        "spatial_en": _SPATIAL_PROGRESSIONS_EN[spatial_index],
        "camera_zh": _CAMERA_BEATS_ZH[camera_index],
        "camera_en": _CAMERA_BEATS_EN[camera_index],
        "organization": int(organization),
    }


def summarize_narrative_plan(plan: Mapping[str, Any], *, english: bool = False) -> str:
    if english:
        return (
            f"arc={_clean(plan.get('arc_name_en'))}; motive={_clean(plan.get('motive_en'))}; "
            f"escalation={_clean(plan.get('escalation_en'))}; climax={_clean(plan.get('climax_en'))}; "
            f"emotional turn={_clean(plan.get('emotion_en'))}; "
            f"spatial path={_clean(plan.get('spatial_en'))}; ending={_clean(plan.get('ending_en'))}; "
            f"signature={_clean(plan.get('signature'))}"
        )
    return (
        f"叙事弧={_clean(plan.get('arc_name_zh'))}；行动动机={_clean(plan.get('motive_zh'))}；"
        f"局势升级={_clean(plan.get('escalation_zh'))}；视觉高潮={_clean(plan.get('climax_zh'))}；"
        f"情绪转折={_clean(plan.get('emotion_zh'))}；"
        f"空间动线={_clean(plan.get('spatial_zh'))}；结尾定格={_clean(plan.get('ending_zh'))}；"
        f"签名={_clean(plan.get('signature'))}"
    )


def _anchor(anchors: Mapping[str, Any], key: str, fallback: str = "") -> str:
    return _clean(anchors.get(key)) or fallback


def _render_chinese(
    anchors: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    detail_level: str,
    non_person: bool,
    adult_mode: bool,
    layout_mode: str,
) -> str:
    lead = _anchor(anchors, "lead", "高完成度图像")
    subject = _anchor(anchors, "subject", "非人物主体" if non_person else "人物主体")
    style = _anchor(anchors, "style")
    style_bridge = _anchor(anchors, "style_bridge")
    scene = _anchor(anchors, "scene", "当前空间")
    composition = _anchor(anchors, "composition", "具有明确主体占比的稳定构图")
    action = _anchor(anchors, "action", "一次克制而有方向的动作")
    adult = _anchor(anchors, "adult")
    outfit = _anchor(anchors, "outfit", "可信的表面结构" if non_person else "与身份相符的服装造型")
    lighting = _anchor(anchors, "lighting", "具有明确方向的主光与环境反射")
    props = _anchor(anchors, "props", "环境中的细节线索")
    custom = _anchor(anchors, "custom")
    residual = _anchor(anchors, "residual")
    quality = _anchor(anchors, "quality", "高细节、清晰对焦与稳定结构")
    layout_clause = visual_layout_contract(layout_mode, english=False)

    style_clause = f"，以{style}作为统一媒介语言" if style else ""
    if style_bridge:
        style_clause += f"，并保留{style_bridge}的成片质感"
    adult_clause = ""
    if adult and not non_person:
        adult_clause = f"；成人氛围通过{adult}被处理为明确成年、克制且服务剧情的造型与氛围"
    elif adult_mode and not non_person:
        adult_clause = "；主体年龄明确为成年，成熟私密氛围通过情境、视线和材质表达"

    anchor_sentence = (
        f"{lead}，画面以{subject}为{'非人物主题的' if non_person else ''}叙事中心{style_clause}。故事发生在{scene}，"
        f"构图采用{composition}，全部视觉锚点服从同一时刻{adult_clause}。{layout_clause}"
    )
    story_sentence = (
        f"{_anchor(plan, 'opening_zh')}；{_anchor(plan, 'motive_zh')}。这些前因凝结为当前动作留下的可见证据。"
        f"当前镜头准确截取回应瞬间：{props}已成线索，{_anchor(plan, 'trigger_zh')}，"
        f"因此{subject}正以{action}回应；{_anchor(plan, 'response_zh')}。"
        f"{_anchor(plan, 'escalation_zh')}，与此同时{_anchor(plan, 'turn_zh')}；全部因果统一收束在当前姿态、表情和环境结果里。"
    )
    motion_details = "重量、接触点、结构边缘、活动关节与表面高光" if non_person else "重量、接触点、边缘、褶皱与高光"
    subject_sentence = (
        f"{'主体结构与外观' if non_person else '人物造型'}围绕{outfit}展开，动作发生时，"
        f"{motion_details}都顺着{action}产生细微变化；"
        f"{'结构朝向与功能部件' if non_person else '视线、肩颈、手部与身体重心'}共同指向当前事件，"
        "使姿态自然传达犹豫、判断和下一步意图。"
    )
    space_sentence = (
        f"空间叙事遵循“{_anchor(plan, 'spatial_zh')}”的路径：前景提供可触摸的尺度和线索，"
        f"中景承接{subject}的行动，背景则保留事件来源或后果。环境并非静止布景，"
        f"{_anchor(plan, 'feedback_zh')}，使{scene}与主体形成清楚的因果联系。"
    )
    camera_beat = _anchor(plan, "camera_zh")
    if non_person:
        camera_beat = camera_beat.replace("表情与手部", "关键结构与功能部件").replace(
            "衣料、尘雾、反射或发丝",
            "表面附着物、尘雾、反射或活动部件",
        )
    subject_surface = "结构表面" if non_person else "脸部与皮肤表面"
    camera_sentence = (
        f"镜头从“{camera_beat}”中选取一个决定性拍摄时机，并保留{composition}的景别与透视。"
        f"{lighting}冻结在这个决定性瞬间，同时在{subject_surface}、{outfit}、{props}和背景之间建立清楚层级，"
        "主光说明行动方向，辅光保留暗部信息，轮廓光与环境反射把主体从空间中分离；"
        f"焦点锁定当前主体与动作，线索和后果通过同一景深内的前后景读出；{_anchor(plan, 'climax_zh')}。"
    )
    detail_bits = []
    if custom:
        detail_bits.append(f"用户补充的{custom}被写进同一事件并产生可见作用")
    if residual:
        detail_bits.append(f"其余细节{residual}只补充身份、材质或空间证据，不另起主题")
    detail_prefix = "；".join(detail_bits)
    close_details = (
        "近处可见真实的表面纹理、接触阴影、细小磨损、结构边缘或活动部件变化"
        if non_person
        else "近处可见真实的表面纹理、接触阴影、细小磨损、发丝或服装边缘变化"
    )
    stability_details = (
        "稳定几何、可信材质、清楚的功能结构与纯净环境轮廓"
        if non_person
        else "自然解剖、可信材质、清楚手部、准确肢体数量与完整身体关系"
    )
    detail_sentence = (
        (detail_prefix + "。" if detail_prefix else "")
        + f"{close_details}，中远处用空气层次、色温差和景深逐级收束；"
        + f"最终保持{quality}，同时维持{stability_details}，背景表面与画面边缘干净清晰。"
    )
    ending_sentence = (
        f"最终画面在视觉上完成一次清楚的剧情推进，同时保留开放结果：{_anchor(plan, 'ending_zh')}。"
        "这个唯一定格把动作余势、环境反馈与情绪余韵都压进当前时刻，形成一张能够暗示过去与未来的真实电影剧照。"
    )

    level = _clean(detail_level)
    if level in {"简洁", "短"}:
        sections = [anchor_sentence, story_sentence, subject_sentence, camera_sentence, detail_sentence, ending_sentence]
    else:
        middle = [subject_sentence, space_sentence, camera_sentence]
        organization = int(plan.get("organization", 0) or 0) % 4
        if organization == 1:
            middle = [space_sentence, subject_sentence, camera_sentence]
        elif organization == 2:
            middle = [camera_sentence, subject_sentence, space_sentence]
        elif organization == 3:
            middle = [subject_sentence, camera_sentence, space_sentence]
        sections = [anchor_sentence, story_sentence, *middle, detail_sentence, ending_sentence]
        if level == "详细":
            sections.insert(
                -1,
                "色彩和材质变化跟随情绪转折逐步展开，亮部不靠过曝制造刺激，暗部保留可读层次，局部对比只用于引导视线；每一个新增细节都应回答主体是谁、事件为何发生或空间如何回应，避免用近义形容词重复扩字数。",
            )
    return "".join(section.strip() for section in sections if section.strip())


def _render_english(
    anchors: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    detail_level: str,
    non_person: bool,
    adult_mode: bool,
    layout_mode: str,
) -> str:
    lead = _anchor(anchors, "lead", "A highly finished image")
    subject = _anchor(anchors, "subject", "the main non-human subject" if non_person else "the selected subject")
    style = _anchor(anchors, "style")
    style_bridge = _anchor(anchors, "style_bridge")
    scene = _anchor(anchors, "scene", "the selected setting")
    composition = _anchor(anchors, "composition", "a stable composition with a clear subject scale")
    action = _anchor(anchors, "action", "one restrained, directional movement")
    adult = _anchor(anchors, "adult")
    outfit = _anchor(anchors, "outfit", "credible surface design" if non_person else "wardrobe appropriate to the identity")
    lighting = _anchor(anchors, "lighting", "directional key light with environmental reflection")
    props = _anchor(anchors, "props", "a detail in the environment")
    custom = _anchor(anchors, "custom")
    residual = _anchor(anchors, "residual")
    quality = _anchor(anchors, "quality", "high detail, clean focus, and stable structure")
    layout_clause = visual_layout_contract(layout_mode, english=True)

    style_clause = f", unified by {style}" if style else ""
    if style_bridge:
        style_clause += f" while preserving the finished media texture of {style_bridge}"
    adult_clause = ""
    if adult and not non_person:
        adult_clause = f" {adult} is treated as clearly adult, controlled styling that serves the story."
    elif adult_mode and not non_person:
        adult_clause = " The subject is unambiguously adult, with maturity expressed through context, gaze, and materials."

    anchor_sentence = (
        f"{lead} is centered on {subject}{style_clause}. The event takes place in {scene}, using {composition}; "
        f"the selected visual anchors belong to one continuous moment instead of a chain of keywords.{adult_clause} {layout_clause}"
    )
    story_sentence = (
        f"The story background combines {_anchor(plan, 'opening_en')} with {_anchor(plan, 'motive_en')}, compressing both into visible evidence inside the present action. "
        f"The camera captures the most informative response instant: {props} is already a concrete clue when {_anchor(plan, 'trigger_en')}. "
        f"Because of it, {subject} answers through {action}, making a motivated choice in which {_anchor(plan, 'response_en')}. "
        f"{_anchor(plan, 'escalation_en')} and {_anchor(plan, 'turn_en')} converge in the current pose, expression, and environmental result."
    )
    motion_details = (
        "weight, contact points, structural edges, moving joints, and surface highlights"
        if non_person
        else "weight, contact points, edges, folds, and highlights"
    )
    design_subject = "surface construction" if non_person else "wardrobe and styling"
    design_verb = "develops" if non_person else "develop"
    subject_sentence = (
        f"The {design_subject} {design_verb} around {outfit}. During the movement, {motion_details} react to {action}. "
        f"{'Structural direction and functional components' if non_person else 'Gaze, shoulders, hands, and body weight'} point toward the event, carrying hesitation, judgment, and intended movement with natural continuity."
    )
    space_sentence = (
        f"Spatial storytelling follows this path: {_anchor(plan, 'spatial_en')}. Foreground information provides scale and a tangible clue, the middle ground carries the action, and the background retains the cause or consequence. "
        f"The location is not passive scenery; {_anchor(plan, 'feedback_en')}, making {scene} visibly respond to the subject."
    )
    camera_beat = _anchor(plan, "camera_en")
    if non_person:
        camera_beat = camera_beat.replace("expression and hands", "key structures and functional components").replace(
            "fabric, dust, reflections, or hair",
            "surface attachments, dust, reflections, or moving components",
        )
    subject_surface = "structural surfaces" if non_person else "the face and skin surfaces"
    camera_sentence = (
        f"The camera selects one decisive exposure from this timing: {camera_beat}, while preserving {composition}. {lighting} is frozen at that instant and establishes a readable hierarchy across {subject_surface}, {outfit}, {props}, and the background. "
        f"Key light explains movement, fill preserves readable shadow information, and rim light or environmental reflection separates the subject. Focus remains on the current subject and action, while clue and consequence are read through depth inside the same frame. {_anchor(plan, 'climax_en')}."
    )
    detail_parts = []
    if custom:
        detail_parts.append(f"The user detail {custom} is integrated into the event and produces a visible effect")
    if residual:
        detail_parts.append(f"Remaining cues such as {residual} provide identity, material, or spatial evidence without starting another theme")
    close_details = (
        "surface texture, contact shadows, slight wear, structural edges, and moving components"
        if non_person
        else "surface texture, contact shadows, slight wear, hair, and garment-edge variation"
    )
    stability_details = (
        "stable geometry, believable materials, readable functional structures, and a clean environmental silhouette"
        if non_person
        else "natural anatomy, believable materials, readable hands, accurate limb count, and a complete body relationship"
    )
    detail_sentence = (". ".join(detail_parts) + ". " if detail_parts else "") + (
        f"At close range, {close_details} remain visible; farther away, atmospheric depth, color-temperature separation, and controlled focus reduce information gradually. "
        f"The finish preserves {quality}, {stability_details}, and clean surfaces with crisp image edges."
    )
    ending_sentence = (
        f"The final image advances the narrative clearly while keeping the result open: {_anchor(plan, 'ending_en')}. This single held instant compresses the momentum of the action, the environment's response, and emotional aftertone into a cinematic still that suggests both a past and a possible next shot."
    )

    level = _clean(detail_level)
    if level in {"简洁", "短"}:
        sections = [anchor_sentence, story_sentence, subject_sentence, camera_sentence, detail_sentence, ending_sentence]
    else:
        middle = [subject_sentence, space_sentence, camera_sentence]
        organization = int(plan.get("organization", 0) or 0) % 4
        if organization == 1:
            middle = [space_sentence, subject_sentence, camera_sentence]
        elif organization == 2:
            middle = [camera_sentence, subject_sentence, space_sentence]
        elif organization == 3:
            middle = [subject_sentence, camera_sentence, space_sentence]
        sections = [anchor_sentence, story_sentence, *middle, detail_sentence, ending_sentence]
        if level == "详细":
            sections.insert(
                -1,
                "Color and material changes follow the emotional turn rather than appearing all at once. Highlights remain controlled, shadows keep readable depth, and local contrast only guides attention. Every added detail explains identity, cause, response, or spatial consequence instead of repeating decorative adjectives.",
            )
    return " ".join(section.strip() for section in sections if section.strip())


def render_narrative_prompt(
    anchors: Mapping[str, Any],
    plan: Mapping[str, Any],
    *,
    language: str = "纯中文",
    detail_level: str = "标准",
    non_person: bool = False,
    adult_mode: bool = False,
    layout_mode: str = "",
) -> str:
    """Render one long, causal, natural-language prompt from selected anchors."""

    resolved_layout = str(layout_mode or anchors.get("layout_mode", "") or "").strip()
    if not resolved_layout:
        resolved_layout = resolve_visual_layout_mode(non_person=non_person)
    if str(language or "纯中文").strip() in {"纯英文", "英文提示词+中文说明"}:
        return _render_english(
            anchors,
            plan,
            detail_level=detail_level,
            non_person=non_person,
            adult_mode=adult_mode,
            layout_mode=resolved_layout,
        )
    return _render_chinese(
        anchors,
        plan,
        detail_level=detail_level,
        non_person=non_person,
        adult_mode=adult_mode,
        layout_mode=resolved_layout,
    )
