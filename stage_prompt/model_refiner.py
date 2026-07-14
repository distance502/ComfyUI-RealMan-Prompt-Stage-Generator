# -*- coding: utf-8 -*-
"""Model refinement helpers for stage prompt generation."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any, Callable

DEFAULT_STAGE_PROMPT_SYSTEM_TEMPLATE = """
你是 Qwen TE 阶段式提示词生成器的默认图像提示词整理模板，兼具资深视觉艺术总监、电影摄影指导、高端人像修图审美和生成式图像 Prompt 工程能力。

任务：把用户输入的节点标签链整理成一段可直接用于 ComfyUI / Stable Diffusion / Flux / Midjourney / Krea 的最终正向提示词正文。输入通常已经包含主体、风格、服装、场景、光影、构图、动作、画质、随机主题池和额外要求，你必须保留这些节点选择，不要擅自改主题，不要抹掉随机差异。

输出硬规则：
1. 只输出最终提示词正文，不输出标题、解释、分析、参数、表格、Markdown、代码块、引号、前后缀或“提示词：”。
2. 默认跟随输入语言；中文输入输出中文，英文输入输出英文，中英混合时优先保留可出图的英文美学词。
3. 输出为一段自然完整的提示词，可用逗号/顿号分隔短语；不要分条，不要换行，不要写成教程或摄影分析。中文目标 650-900 字并尽量接近 800 字；英文目标 320-520 words。
4. 保留主体身份、年龄锚点、人数、服装、动作、场景、构图景别、镜头、光影、材质、风格、画质和负面规避意图；尤其不要删除“中景半身、全景全身、近景、侧逆光、古风、CG感、神话感、NSFW”等关键锚点。
5. 同一批多条提示词必须保持各自差异，不要合并成同一条，也不要把不同随机主题池改成相同画面。
6. 按“主体身份与气质、发型五官与服装材质、动作姿态与情绪、场景空间与前中后景、光影色彩与镜头语言、画质结构与生成稳定性”六个维度展开。只补足缺失的合理细节，不要锁死用户没选的主题，不要用近义词反复灌水。
7. 全局构图方法来自用户素材库的可泛化规则：按“主体 → 环境 → 光线 → 风格/媒介 → 镜头”组织画面；先写清楚谁/什么、在哪里、由什么光照亮、属于什么媒介质感、如何取景。
8. 具体描述优先于空泛形容：用“暖色侧逆光、雨雾竹林、35mm 胶片颗粒、丝绸边缘高光、湿润石阶反光”这类可见信息替代“好看、震撼、顶级、神级”等空词。
9. 外部平台参数、码图 --profile / profile code、UUID、--ar、--stylize、--raw、--hd、--seed 等只可作为参考来源信息，绝对不要进入最终提示词正文。
10. 素材库只提供写法和词汇方向，不提供固定模板；不得锁死“古风、武侠、CG、全身、白底、某个角色、某个场景”。用户已选标签和当前随机结果永远优先。
11. 如果当前上下文已形成一条明确主线，例如运行时随机结果、NSFW 工作台成熟主线、智能文本主线或角色设定图主线，优先沿这条主线补足服装、场景、动作、光影和材质，不要退回成标签清单，也不要把多个互斥主线强拼到同一条提示词里。
12. 如果主体类型为“非人物主体”，必须按物体、载具、机甲、建筑、场景、生物或概念主体处理；禁止改写成成年女性、男性、女孩、模特、人像写真或角色肖像；不要补脸部、皮肤、发型、手指、身材、内衣、礼服、高跟鞋等人物细节，改写重点应为结构、比例、材质、功能部件、尺度关系、空间层次、光影和画质。
13. 不要复用固定开头、固定段落或固定模板句。每次必须依据当前按钮、标签、随机结果、NSFW 工作台和智能文本输入重新组织画面主线；相同语义只写一次，禁止用近义句反复扩字数。
14. API、本地模型和 Skill-only 都必须遵守同一套全局 Skill 判断：先读当前节点选择、随机运行时解析、智能文本解析、NSFW 工作台摘要、标签块编排顺序和高级按钮设置，再决定主体、场景、服装、动作、光影、道具和风格；不得把未选择的固定素材塞回输出。
15. 批量生成、运行时随机、智能文本连续匹配或 API 连续调用时，每一条都要形成独立视觉档案：主体身份、环境、服装、动作、持物、光影、色彩、镜头组织中至少三个核心维度明确变化；最近输出只用于避让，不是可复写素材，不要把上一条输出的主体/场景/动作/配色机械复制到下一条。

美学方向：
- 真实感/摄影向：强调真实存在感、自然脸型、非网红脸、非塑料 AI 皮肤；保留真实毛孔、细微肤色差、绒毛、唇纹、眼下细纹、鼻翼微油光等“真实但美”的肌肤细节；使用自然镜头透视、轻微抓拍感、浅景深、电影光影、真实环境曝光。
- 高端人像/时尚向：强调视觉和谐、优雅仪态、清澈有故事感的眼神、精致但不过度磨皮的肤质、真丝/蕾丝/羊绒/皮革/金属等材质的垂坠、纹理和边缘高光。
- 插画感/CG感/古风/神话感：严格服从节点模式，不要强行改成写实摄影；把材质、光影、构图和画质转换为对应媒介的高完成度表达，如电影级 CG、概念设计、工笔重彩、东方古风、神圣史诗、魔幻现实主义等。
- 场景与构图：补足前景/中景/背景层次、主体占比、镜头距离、视角、留白、焦点层级、空间深度和环境细节，但不要添加与节点主题冲突的道具或地点。
- 光线与色彩：明确主光、辅光、轮廓光、软硬、色温、阴影、反射、对比度、胶片颗粒、低饱和或高级配色；若输入含参考色调或风格锚点，只迁移色相、光感、影调、材质和情绪，不复制无关空间、文字、品牌或具体道具。
- 素材库常见优秀结构包括：古风电影氛围、港式武侠胶片、现代都市生活流、科幻机甲、东方赛博、商业广告、时尚编辑、神话史诗、日韩影像等。它们只能作为“风格通道”，必须随当前模式与标签自动切换，不可混成一个杂烩。

质量与限制：
加入必要的高质量约束，如顶级画质、清晰对焦、精致纹理、真实材质、自然解剖、手部自然、无多余肢体、无畸形、无文字、无水印、无 logo、无低清伪影。不要生成廉价网红感、证件照感、商业棚拍过修感、塑料皮肤、卡通化、过度磨皮、过曝高光或脏乱背景。

最终目标：输出一段“主题明确、细节丰富、模式一致、可直接出图”的高质量正向提示词。目标接近 800 字，但必须靠有效画面信息、镜头组织、材质与光影细节自然展开，不能为了字数重复叠加标签。
""".strip()

_DEFAULT_IMAGE_REFINER_SYSTEM = DEFAULT_STAGE_PROMPT_SYSTEM_TEMPLATE
_PROMPT_LABEL_PATTERN = re.compile(
    r"^\s*(?:成品提示词|最终提示词|图像提示词|提示词|Prompt|prompt|image prompt|final prompt)\s*[:：]\s*",
    flags=re.IGNORECASE,
)
_META_LINE_PATTERN = re.compile(
    r"^\s*(?:以下(?:是|为)|整理后|优化后|输出如下|成品如下|可直接用于出图(?:的)?|请使用以下)\b",
    flags=re.IGNORECASE,
)
_BATCH_SEPARATOR = "<<<QWEN_TE_SPLIT>>>"
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_ENGLISH_WORD_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z'-]{2,}\b")
_LEADING_SCENE_WRAPPER_PATTERN = re.compile(
    r"^\s*(?:一张|一幅)\s*(?:描绘|展示|呈现|表现|刻画)?\s*(.+?)\s*的(?:画面|图像)(?:中)?\s*[，,]?\s*(.*)$"
)
_NARRATIVE_FILLER_PATTERNS = (
    re.compile(r"(?:画面中|图像中|镜头中|场景中)\s*[，,]?\s*"),
    re.compile(r"(?:这个角色|该角色|这个场景|该场景)\s*[，,]?\s*"),
    re.compile(r"(?:整体呈现(?:出)?|整体营造出|整体展现出)\s*"),
    re.compile(r"(?:仿佛|宛如|如同)\s*"),
    re.compile(r"(?:给人一种|营造出|展现出|呈现出|散发出)\s*"),
)
_ANALYSIS_MARKERS = (
    "分析用户请求",
    "理解输入",
    "核心主题",
    "主要目标",
    "格式要求",
    "Skill前置上下文",
    "模型调用上下文",
    "待整理提示词正文",
    "完整的、符合图像描述要求的文本",
    "自述风格",
    "根据用户拖拽后的标签块顺序",
    "画面阅读顺序依次为",
    "块顺序摘要",
    "请把这些块自然织入",
)
_NUMBERED_ANALYSIS_LINE_PATTERN = re.compile(r"^\s*\d+[.、]\s*")
_FRAGMENT_SPLIT_PATTERN = re.compile(r"[\n\r\t,，;；、|]+")
_CONSECUTIVE_REPEAT_PATTERN = re.compile(r"(?P<frag>[\u4e00-\u9fffA-Za-z]{2,8})(?:[，,、\s]{0,2}(?P=frag)){5,}")
_PROMPT_FRAGMENT_DEDUPE_SPLIT_PATTERN = re.compile(r"\s*[，,；;。]\s*")
_COMPOSITION_ANCHOR_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("中景半身", ("中景半身", "半身", "中景")),
    ("近景半身", ("近景半身", "半身", "近景")),
    ("全景全身", ("全景全身", "全身", "全景")),
)
_MODE_LITERAL_GUARD_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]], ...] = (
    (("CG感", "电影级CG", "概念设计稿", "虚幻引擎渲染", "Octane渲染", "PBR渲染"), ("CG感",), ("成年女性",)),
    (("古风", "古风人像", "古风电影剧照", "工笔重彩", "玄幻古风", "水墨写意"), ("古风",), ("成年女性",)),
    (("神话感", "神话史诗感", "神圣史诗", "魔幻现实主义", "暗黑奇幻", "冰雪奇幻"), ("神话感",), ("成年女性",)),
)
_STYLE_ONLY_PROMPT_TERMS = frozenset({
    "自动",
    "真实感",
    "插画感",
    "CG感",
    "古风",
    "神话感",
    "电影级CG",
    "写实摄影",
    "高完成度插画",
    "古风人像",
    "神话史诗感",
})
_STYLE_ONLY_COMPANION_TERMS = frozenset({"成年女性", "成年男性", "人物角色", "人物主体"})
_STYLE_ONLY_PROMPT_TERM_KEYS = frozenset(term.casefold() for term in _STYLE_ONLY_PROMPT_TERMS)
_STYLE_ONLY_COMPANION_TERM_KEYS = frozenset(term.casefold() for term in _STYLE_ONLY_COMPANION_TERMS)
_STYLE_ONLY_ALL_TERM_KEYS = _STYLE_ONLY_PROMPT_TERM_KEYS | _STYLE_ONLY_COMPANION_TERM_KEYS
_PLACEHOLDER_FRAGMENT_KEYS = {"[]", "【】", "()", "（ ）", "true", "false", "none", "null", "undefined", "nan"}
_COMMAND_STYLE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:create|keep|use|finish|make|ensure|preserve|organize|add)\b",
    flags=re.IGNORECASE,
)
_SEMANTIC_REPEAT_FAMILIES: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    (
        "composition_full_body",
        3,
        (
            "全景全身",
            "全身",
            "全景",
            "人物完整入镜",
            "完整入镜",
            "完整画面",
            "wide full-body shot",
            "full body",
            "entire subject fully in frame",
            "complete figure",
        ),
    ),
    (
        "quality_detail",
        4,
        (
            "高细节",
            "高质量",
            "高清",
            "清晰",
            "清晰对焦",
            "超清画质",
            "高分辨率",
            "masterpiece",
            "best quality",
            "high detail",
            "high resolution",
            "ultra-detailed",
            "sharp focus",
        ),
    ),
    (
        "focus_anatomy",
        4,
        (
            "焦点层级清晰",
            "主体清晰",
            "自然解剖",
            "解剖结构自然",
            "手指数量稳定",
            "手部自然",
            "clear focus hierarchy",
            "natural anatomy",
            "stable hands",
            "correct fingers",
        ),
    ),
    (
        "artifact_negative",
        4,
        (
            "无文字",
            "无文本",
            "无水印",
            "无logo",
            "无低清伪影",
            "no text",
            "no watermark",
            "no logo",
            "no low-resolution artifacts",
        ),
    ),
)


def extract_text(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        for key in ("text", "output_text", "response"):
            value = response.get(key)
            if isinstance(value, str):
                return value
        try:
            return str(response["choices"][0]["message"]["content"])
        except Exception:
            pass
    try:
        return str(getattr(response, "text"))
    except Exception:
        return str(response)


def _postprocess_prompt_text(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*", "", normalized)
    normalized = re.sub(r"\s*```\s*$", "", normalized)
    lines: list[str] = []
    for raw_line in normalized.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        line = line.lstrip("-*#> \t")
        line = _PROMPT_LABEL_PATTERN.sub("", line).strip()
        if not line or _META_LINE_PATTERN.match(line):
            continue
        wrapper_match = _LEADING_SCENE_WRAPPER_PATTERN.match(line)
        if wrapper_match:
            lead = wrapper_match.group(1).strip()
            tail = wrapper_match.group(2).strip()
            line = f"{lead}，{tail}" if tail else lead
        for pattern in _NARRATIVE_FILLER_PATTERNS:
            line = pattern.sub("", line)
        line = re.sub(r"(?:\[\s*\]|【\s*】|\(\s*\)|（\s*）)", "", line)
        line = re.sub(r"\s+", " ", line)
        line = re.sub(r"^[，,。；;:\s]+", "", line)
        line = re.sub(r"\s*[，,。；;:]\s*$", "", line)
        line = line.strip("“”\"'` ")
        if not line:
            continue
        lines.append(line)
    collapsed = "，".join(lines) if lines else normalized
    collapsed = re.sub(r"\s+", " ", collapsed)
    collapsed = re.sub(r"[，,]{2,}", "，", collapsed)
    collapsed = re.sub(r"\s*[，,]\s*", "，", collapsed)
    collapsed = _dedupe_prompt_fragments(collapsed)
    return collapsed.strip("，,;； \n\t")


def _dedupe_prompt_fragments(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    note_prefix = "中文说明："
    note = ""
    body = normalized
    if note_prefix in normalized:
        body, note_tail = normalized.split(note_prefix, 1)
        note = f"{note_prefix}{note_tail.strip()}"

    fragments = []
    fragment_keys: dict[str, str] = {}
    for fragment in _PROMPT_FRAGMENT_DEDUPE_SPLIT_PATTERN.split(body):
        item = fragment.strip("，,；;。 \n\t")
        if not item:
            continue
        item_key = _normalize_for_compare(item)
        if item_key in _PLACEHOLDER_FRAGMENT_KEYS:
            continue
        fragments.append(item)
        fragment_keys[item] = item_key
    if not fragments:
        return note
    non_command_fragments = [fragment for fragment in fragments if not _looks_like_prompt_command_fragment(fragment)]
    if len(non_command_fragments) >= max(1, len(fragments) // 2):
        fragments = non_command_fragments
    if len(fragments) <= 1:
        return f"{fragments[0]}。{note}" if note else fragments[0]

    seen: set[str] = set()
    family_counts: dict[str, int] = {}
    deduped: list[str] = []
    for fragment in fragments:
        key = fragment_keys[fragment]
        if not key:
            continue
        if key in seen:
            continue
        semantic_family = _semantic_repeat_family(fragment)
        if semantic_family:
            family_name, family_limit = semantic_family
            current_count = family_counts.get(family_name, 0)
            if current_count >= family_limit:
                continue
            family_counts[family_name] = current_count + 1
        seen.add(key)
        deduped.append(fragment)
    body_text = "，".join(deduped).strip("，,;； \n\t")
    if note:
        return f"{body_text}。{note}" if body_text else note
    return body_text


def _looks_like_broken_prompt(text: str) -> bool:
    normalized = str(text or "").strip()
    if not normalized:
        return True
    if _normalize_for_compare(normalized) in _PLACEHOLDER_FRAGMENT_KEYS:
        return True
    if any(marker in normalized for marker in _ANALYSIS_MARKERS):
        return True
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    if sum(1 for line in lines if _NUMBERED_ANALYSIS_LINE_PATTERN.match(line)) >= 2:
        return True
    if normalized.count("**") >= 2:
        return True
    if _CONSECUTIVE_REPEAT_PATTERN.search(normalized):
        return True

    fragments = [fragment.strip() for fragment in _FRAGMENT_SPLIT_PATTERN.split(normalized) if fragment.strip()]
    meaningful = [fragment for fragment in fragments if len(fragment) >= 2]
    if not meaningful:
        return False
    normalized_fragments = {fragment.casefold() for fragment in meaningful}
    if len(meaningful) <= 2 and normalized_fragments.issubset(_STYLE_ONLY_PROMPT_TERM_KEYS):
        return True
    style_terms = _STYLE_ONLY_PROMPT_TERM_KEYS
    if len(meaningful) <= 3 and normalized_fragments.issubset(_STYLE_ONLY_ALL_TERM_KEYS) and bool(normalized_fragments & style_terms):
        return True
    counts = Counter(meaningful)
    if any(count >= 6 for fragment, count in counts.items() if len(fragment) >= 2):
        return True
    if len(meaningful) >= 12:
        top_count = max(counts.values(), default=0)
        diversity = len(set(meaningful)) / float(len(meaningful))
        if top_count >= max(6, len(meaningful) // 3):
            return True
        if diversity < 0.45:
            return True
    return False


def _normalize_for_compare(text: str) -> str:
    normalized = str(text or "").strip().lower()
    normalized = re.sub(r"[\s，,。；;:!！?？、】【（）()“”\"'`]+", "", normalized)
    return normalized


_SEMANTIC_REPEAT_NORMALIZED_FAMILIES: tuple[tuple[str, int, tuple[str, ...]], ...] = tuple(
    (
        family_name,
        limit,
        tuple(dict.fromkeys(filter(None, (_normalize_for_compare(term) for term in terms)))),
    )
    for family_name, limit, terms in _SEMANTIC_REPEAT_FAMILIES
)


def _looks_like_prompt_command_fragment(fragment: str) -> bool:
    text = str(fragment or "").strip()
    if not text or not _COMMAND_STYLE_PREFIX_PATTERN.match(text):
        return False
    lowered = text.casefold()
    return any(
        marker in lowered
        for marker in (
            "image",
            "subject",
            "composition",
            "frame",
            "prompt",
            "quality",
            "lighting",
            "background",
            "the face",
            "the body",
        )
    )


def _semantic_repeat_family(fragment: str) -> tuple[str, int] | None:
    text = str(fragment or "").strip()
    if not text:
        return None
    key = _normalize_for_compare(text)
    if not key:
        return None
    word_count = len([part for part in re.split(r"\s+", text) if part.strip()])
    is_short_fragment = len(key) <= 56 or word_count <= 8
    for family_name, limit, term_keys in _SEMANTIC_REPEAT_NORMALIZED_FAMILIES:
        for term_key in term_keys:
            if key == term_key:
                return family_name, limit
            if is_short_fragment and (term_key in key or key in term_key):
                return family_name, limit
    return None


def stabilize_prompt_output(text: str, settings: dict[str, Any] | None = None) -> str:
    """Clean one final prompt body without changing the selected creative anchors."""

    del settings
    original = str(text or "").strip()
    if not original:
        return ""
    cleaned = _postprocess_prompt_text(original)
    return cleaned or original


def _restore_composition_anchors(original_prompt: str, candidate_prompt: str) -> str:
    original = str(original_prompt or "").strip()
    candidate = str(candidate_prompt or "").strip()
    if not original or not candidate:
        return candidate
    fragments = [fragment.strip() for fragment in re.split(r"\s*[，,]\s*", candidate) if fragment.strip()]
    if not fragments:
        return candidate
    for anchor, family in _COMPOSITION_ANCHOR_RULES:
        if anchor not in original:
            continue
        if anchor in candidate:
            continue
        if any(term in candidate for term in family if term != anchor):
            insert_at = 0
            for index, fragment in enumerate(fragments):
                if any(term in fragment for term in family if term != anchor):
                    insert_at = index
                    break
            fragments.insert(insert_at, anchor)
            candidate = "，".join(fragments)
            continue
        fragments.insert(0, anchor)
        candidate = "，".join(fragments)
    return candidate


def _restore_mode_literal_guards(original_prompt: str, candidate_prompt: str) -> str:
    original = str(original_prompt or "").strip()
    candidate = str(candidate_prompt or "").strip()
    if not original or not candidate:
        return candidate
    fragments = [fragment.strip() for fragment in re.split(r"\s*[，,]\s*", candidate) if fragment.strip()]
    if not fragments:
        return candidate
    for source_terms, guard_terms, companion_terms in _MODE_LITERAL_GUARD_RULES:
        if not any(term in original for term in source_terms):
            continue
        for guard in guard_terms:
            if guard in candidate:
                continue
            fragments.insert(0, guard)
            candidate = "，".join(fragments)
        for companion in companion_terms:
            if companion not in original or companion in candidate:
                continue
            fragments.insert(0, companion)
            candidate = "，".join(fragments)
    return candidate


def _prompt_language_mode(settings: dict[str, Any]) -> str:
    return str(settings.get("提示词语言", "纯中文") or "纯中文").strip()


def _language_instruction(settings: dict[str, Any]) -> str:
    language = _prompt_language_mode(settings)
    if language == "纯英文":
        return (
            "\n\nLanguage override: The final positive prompt must be English only. "
            "Target 320-520 English words. Do not output Chinese characters, Chinese labels, explanations, headings, Markdown, or bilingual notes."
        )
    if language == "英文提示词+中文说明":
        return (
            "\n\nLanguage override: Output an English prompt body first, targeting 320-520 English words, "
            "then append one short Chinese companion note beginning with `中文说明：` to summarize the visual direction. "
            "Keep the English prompt usable by itself; do not add headings, Markdown, or analysis."
        )
    if language == "纯中文":
        return "\n\n语言覆盖：最终正向提示词正文必须使用中文，不要改成英文提示词；中文目标 650-900 字，尽量接近 800 字。"
    return ""


def _resolve_system_prompt(settings: dict[str, Any]) -> str:
    base_prompt = str(settings.get("系统提示词覆盖") or _DEFAULT_IMAGE_REFINER_SYSTEM)
    return f"{base_prompt}{_language_instruction(settings)}"


def _violates_language(text: str, settings: dict[str, Any]) -> bool:
    # Legacy/direct callers may not provide a language contract. The stage node
    # always supplies this field, so strict validation remains active there.
    if "提示词语言" not in settings:
        return False
    language = _prompt_language_mode(settings)
    source = str(text or "").strip()
    if language == "纯英文":
        return bool(_CJK_PATTERN.search(source))
    if language == "纯中文":
        cjk_count = len(_CJK_PATTERN.findall(source))
        english_words = _ENGLISH_WORD_PATTERN.findall(source)
        english_letter_count = sum(char.isascii() and char.isalpha() for char in source)
        return cjk_count == 0 or (
            len(english_words) >= 6
            and english_letter_count > max(12, cjk_count * 2)
        )
    if language == "英文提示词+中文说明":
        marker = re.search(r"中文说明\s*[:：]", source)
        if marker is None:
            return True
        english_body = source[: marker.start()].strip(" ，,;；。")
        chinese_note = source[marker.end() :].strip(" ，,;；。")
        return (
            not english_body
            or bool(_CJK_PATTERN.search(english_body))
            or len(_ENGLISH_WORD_PATTERN.findall(english_body)) < 4
            or not _CJK_PATTERN.search(chinese_note)
        )
    return False


_NON_PERSON_HUMAN_INTRUSION_TERMS = (
    "成年女性",
    "成年男性",
    "年轻成年女性",
    "青春感成年女性",
    "中年女性",
    "中年男性",
    "东亚成年女性",
    "女性",
    "男性",
    "女孩",
    "少女",
    "模特",
    "人像",
    "人物写真",
    "角色肖像",
    "脸部",
    "面部",
    "五官",
    "发型",
    "发丝",
    "皮肤",
    "手指",
    "解剖",
    "身材",
    "胸针",
    "手提包",
    "高跟鞋",
    "礼服",
    "内衣",
)
_NON_PERSON_HUMAN_INTRUSION_TERMS_EN = (
    "adult woman",
    "adult man",
    "young woman",
    "young man",
    "female model",
    "male model",
    "fashion portrait",
    "beauty portrait",
    "human portrait",
    "woman portrait",
    "man portrait",
    "visible face",
    "human face",
    "facial features",
    "visible skin",
    "natural skin",
    "skin texture",
    "detailed hair",
    "flowing hair",
    "elegant dress",
    "evening dress",
    "lingerie",
    "high heels",
)


def _violates_subject_type(original_prompt: str, candidate_prompt: str, settings: dict[str, Any]) -> bool:
    subject_type = str(settings.get("主体类型解析结果", "") or settings.get("主体类型", "自动") or "自动").strip()
    if subject_type != "非人物主体":
        return False
    original = str(original_prompt or "")
    candidate = str(candidate_prompt or "")
    if not candidate:
        return False
    if any(term in candidate and term not in original for term in _NON_PERSON_HUMAN_INTRUSION_TERMS):
        return True
    original_en = original.casefold()
    candidate_en = candidate.casefold()
    return any(
        term in candidate_en and term not in original_en
        for term in _NON_PERSON_HUMAN_INTRUSION_TERMS_EN
    )


def _batch_language_instruction(settings: dict[str, Any]) -> str:
    language = _prompt_language_mode(settings)
    if language == "纯英文":
        return "Language requirement: output every final prompt body in English only, 320-520 words per item, with no Chinese characters.\n"
    if language == "英文提示词+中文说明":
        return "Language requirement: each item outputs an English prompt body first, 320-520 words per item, then one short Chinese note beginning with 中文说明： before the separator.\n"
    if language == "纯中文":
        return "语言要求：每条成品提示词正文必须使用中文，不要改成英文提示词；每条目标 650-900 字，尽量接近 800 字。\n"
    return ""


def _refiner_token_limit(settings: dict[str, Any], *, prompt_count: int = 1) -> int:
    try:
        requested = int(settings.get("最大生成token", 1800) or 1800)
    except Exception:
        requested = 1800
    count = max(1, int(prompt_count or 1))
    floor = 1280 if count == 1 else min(8192, 1280 * count)
    return min(8192, max(floor, requested))


def _safe_float_setting(settings: dict[str, Any], key: str, default: float, min_value: float, max_value: float) -> float:
    raw_value = settings.get(key, default)
    if raw_value is None or raw_value == "":
        raw_value = default
    try:
        value = float(raw_value)
    except Exception:
        value = default
    return max(min_value, min(max_value, value))


def _safe_int_setting(settings: dict[str, Any], key: str, default: int, min_value: int, max_value: int) -> int:
    raw_value = settings.get(key, default)
    if raw_value is None or raw_value == "":
        raw_value = default
    try:
        value = int(raw_value)
    except Exception:
        value = default
    return max(min_value, min(max_value, value))


def _is_runtime_diversity_context(settings: dict[str, Any], *, prompt_count: int) -> bool:
    if prompt_count > 1:
        return True
    if settings.get("最近提示词指纹"):
        return True
    if settings.get("标签块编排摘要"):
        return True
    if bool(settings.get("运行时随机标签", False)):
        return True
    runtime_mode = str(settings.get("运行时随机模式解析结果", "") or settings.get("运行时随机模式", "") or "").strip()
    return runtime_mode in {"全随机", "重写主体与场景", "重写主线"}


def _refiner_sampling_params(settings: dict[str, Any], *, prompt_count: int = 1) -> dict[str, Any]:
    temperature = _safe_float_setting(settings, "温度", 0.75, 0.0, 2.0)
    top_p = _safe_float_setting(settings, "top_p", 0.9, 0.0, 1.0)
    top_k = _safe_int_setting(settings, "top_k", 40, 0, 200)
    repeat_penalty = _safe_float_setting(settings, "重复惩罚", 1.08, 0.0, 2.0)
    frequency_penalty = _safe_float_setting(settings, "频率惩罚", 0.0, -2.0, 2.0)
    presence_penalty = _safe_float_setting(settings, "存在惩罚", 0.0, -2.0, 2.0)
    diversity_context = _is_runtime_diversity_context(settings, prompt_count=prompt_count)

    if diversity_context:
        temperature = max(temperature, 0.72)
        top_p = max(top_p, 0.9)
        repeat_penalty = max(repeat_penalty, 1.1)
        frequency_penalty = max(frequency_penalty, 0.18)
        presence_penalty = max(presence_penalty, 0.1)
    else:
        repeat_penalty = max(repeat_penalty, 1.08)
        frequency_penalty = max(frequency_penalty, 0.08)
        presence_penalty = max(presence_penalty, 0.04)

    params: dict[str, Any] = {
        "max_tokens": _refiner_token_limit(settings, prompt_count=prompt_count),
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "repeat_penalty": repeat_penalty,
        "frequency_penalty": frequency_penalty,
        "presence_penalty": presence_penalty,
        "stream": False,
        "stop": [],
    }
    seed = _safe_int_setting(settings, "seed", 0, 0, 0xFFFFFFFFFFFFFFFF)
    if seed > 0:
        params["seed"] = seed
    return params


_VISUAL_HISTORY_LABELS = {
    "identity": "主体",
    "style": "风格",
    "scene": "场景",
    "outfit": "服装",
    "action": "动作",
    "light": "光影",
    "composition": "构图",
    "prop": "道具",
    "adult": "成熟表达",
}


def _summarize_recent_prompt_history(items: list[str]) -> str:
    tags: list[str] = []
    visual_segments: list[str] = []
    core_samples: list[str] = []
    for raw_item in items:
        item = str(raw_item or "").strip()
        if not item:
            continue
        if item.startswith("tag:"):
            tag = item.removeprefix("tag:").strip()
            if tag and tag not in tags:
                tags.append(tag)
            continue
        if item.startswith("visual:"):
            visual = item.removeprefix("visual:").strip()
            for segment in visual.split("|"):
                if ":" not in segment:
                    continue
                prefix, values = segment.split(":", 1)
                label = _VISUAL_HISTORY_LABELS.get(prefix.strip(), prefix.strip() or "维度")
                clean_values = [value.strip() for value in values.split(",") if value.strip()]
                if clean_values:
                    visual_segments.append(f"{label}={'+'.join(clean_values[:3])}")
            continue
        if item not in core_samples:
            core_samples.append(item)
    parts: list[str] = []
    if tags:
        parts.append("近期标签：" + "、".join(tags[:12]))
    if visual_segments:
        parts.append("视觉档案：" + "；".join(dict.fromkeys(visual_segments[:8])))
    if core_samples:
        parts.append("文本骨架：" + "；".join(core_samples[:2]))
    return "；".join(parts)


def _skill_context_for_model(settings: dict[str, Any]) -> str:
    notes = [str(note).strip() for note in settings.get("推理纠偏说明", []) if str(note).strip()]
    compact_notes = " | ".join(notes[:8]) if notes else "无"
    model_source = str(settings.get("模型来源", "仅Skill") or "仅Skill").strip()
    model_source_effective = str(settings.get("模型来源实际", model_source) or model_source).strip()
    model_fallback_note = str(settings.get("模型回退说明", "") or "").strip()
    post_context = str(settings.get("模型后置素材摘要", "") or "").strip()
    nsfw_context = str(settings.get("NSFW工作台标签摘要", "") or "").strip()
    tag_block_context = str(settings.get("标签块编排摘要", "") or "").strip()
    dynamic_strategy = str(settings.get("Skill动态变化策略", "") or "").strip()
    diversity_markers = [
        str(marker).strip()
        for marker in [
            *list(settings.get("随机主题池档案标记", []) or []),
            *list(settings.get("运行时随机档案标记", []) or []),
        ]
        if str(marker).strip()
    ]
    recent_prompt_fingerprints = [
        str(item).strip()
        for item in list(settings.get("最近提示词指纹", []) or [])
        if str(item).strip()
    ]
    extra_lines = []
    if post_context:
        extra_lines.append(f"当前激活素材摘要：{post_context}")
    if nsfw_context:
        extra_lines.append(f"NSFW 工作台素材：{nsfw_context}")
    if tag_block_context:
        extra_lines.append(f"标签块编排顺序：{tag_block_context}")
    if dynamic_strategy:
        extra_lines.append(f"Skill动态变化策略：{dynamic_strategy}")
    extra_lines.append(
        "全局非锁死策略：当前标签、NSFW 工作台、智能文本和标签块只提供本次素材锚点；"
        "不要把历史输出、示例、默认词或上一轮随机档案当成固定模板。若某个维度没有被用户明确选择，"
        "可以按当前主风格补入新的合理细节；若已经明确选择，则保留它并优先变化其他未锁定维度。"
    )
    character_sheet_policy = str(settings.get("角色设定图内部策略", "") or "").strip()
    if character_sheet_policy:
        extra_lines.append(f"角色设定图策略：{character_sheet_policy}")
    if diversity_markers:
        extra_lines.append(f"本次差异档案：{'、'.join(dict.fromkeys(diversity_markers[:12]))}")
    if recent_prompt_fingerprints:
        recent_summary = _summarize_recent_prompt_history(recent_prompt_fingerprints)
        extra_lines.append(
            "最近输出避重档案："
            + (recent_summary or "；".join(dict.fromkeys(recent_prompt_fingerprints[:4])))
            + "。最近输出只用于避让，不能复写进正文；本次不能只换开头或换同义词，至少更换三个视觉维度，"
            "例如主体身份、场景空间、服装材质、动作姿态、光影色调、持物道具或镜头组织；"
            "如果用户已锁定其中一项，就保留该项并变化其他维度，避免复读历史主线。"
        )
    if model_fallback_note:
        extra_lines.append(f"模型回退状态：{model_fallback_note}")
    extra_context = ("\n" + "\n".join(extra_lines)) if extra_lines else ""
    return (
        "Skill前置上下文：以下正文已经过 Qwen TE Skill 引擎、标签库、随机运行时、标签块编排、NSFW 工作台和智能文本匹配链路整理；"
        "你是后置润色层，只能扩写与连贯化，不得推翻 Skill 已经收敛出的主体、风格、景别、服装、场景、动作、光影和语言。\n"
        f"模型来源：{model_source}；"
        f"模型实际来源：{model_source_effective}；"
        f"提示词语言：{settings.get('提示词语言', '纯中文')}；"
        f"详细度：{settings.get('详细度', '标准')}；"
        f"输出模式：{settings.get('输出模式', '完整结果')}；"
        f"模板风格：{settings.get('模板风格', '自动')}；"
        f"主体类型：{settings.get('主体类型解析结果', '') or settings.get('主体类型', '自动')}；"
        f"案例输出结构：{settings.get('案例输出结构', '自动')}；"
        f"标签反推模式：{settings.get('标签反推模式', '自动平衡')}；"
        f"随机主题池：{settings.get('随机主题池', '自动')}；"
        f"生成数量：{settings.get('生成数量', 1)}；"
        f"运行时随机解析：{settings.get('运行时随机模式解析结果', '') or '未触发'}；"
        f"智能文本解析：{settings.get('智能文本风格优先解析结果', '') or '自动判断'} / {settings.get('智能文本风格解析结果', '') or '未触发'}；"
        f"NSFW策略状态：{'开启' if settings.get('NSFW策略启用', False) else '关闭'} / {settings.get('NSFW策略来源', '') or '无'}；"
        f"NSFW Skill解析：{settings.get('NSFW策略解析结果', '') or '未触发'}；"
        f"风格隔离策略：{settings.get('风格隔离策略', '平衡收敛')}；"
        f"Skill纠偏摘要：{compact_notes}。{extra_context}\n"
        "输出时不要复述本上下文、不要输出标题、不要输出分析，只输出最终正向提示词正文。"
    )


def _compose_model_user_prompt(prompt: str, settings: dict[str, Any]) -> str:
    return f"{_skill_context_for_model(settings)}\n\n待整理提示词正文：\n{str(prompt or '').strip()}"


def _prompt_signature(prompt: str, *, limit: int = 14) -> str:
    fragments = []
    for fragment in _FRAGMENT_SPLIT_PATTERN.split(str(prompt or "")):
        item = fragment.strip()
        if not item:
            continue
        key = _normalize_for_compare(item)
        if not key or key in _PLACEHOLDER_FRAGMENT_KEYS:
            continue
        if item not in fragments:
            fragments.append(item)
        if len(fragments) >= limit:
            break
    return "、".join(fragments)


def _compose_batch_prompt(prompts: list[str], settings: dict[str, Any]) -> str:
    diversity_lines = []
    for index, prompt in enumerate(prompts, start=1):
        signature = _prompt_signature(prompt)
        diversity_lines.append(
            f"第{index}条差异锚点：{signature or '按该条输入自行提炼'}。"
            "输出时围绕本条锚点重组主体、场景、服装、动作、持物、光影和色彩，并至少保留两个维度与其他条不同，不要复制其他条的主线。"
        )
    return (
        _batch_language_instruction(settings)
        + f"请按原顺序整理以下 {len(prompts)} 组图像提示词。"
        f"每组输出一条单行成品提示词，必须使用 `{_BATCH_SEPARATOR}` 作为唯一分隔符。"
        "每组必须保留输入之间的差异，不要把多组内容合并或改写成几乎相同的句子。"
        "如果某条来自运行时随机、标签块编排、NSFW 工作台或智能文本，只能沿本条已经形成的主线补足，不要套用上一条的主体、场景、服装、动作或配色。"
        "不要输出标题、序号、解释、Markdown、额外前后缀。任何分析步骤、任务拆解、重复灌水词都视为失败。\n"
        + "\n差异化合同：\n"
        + "\n".join(diversity_lines)
        + "\n\n待整理提示词：\n"
        + f"\n{_BATCH_SEPARATOR}\n".join(prompts)
    )


def _call_model_text(
    llm: Any,
    prompt: str,
    settings: dict[str, Any],
    *,
    chat_completion: Callable[..., Any],
    clean_think_text: Callable[[str], str],
    prompt_count: int = 1,
) -> str:
    if hasattr(llm, "create_chat_completion"):
        response = chat_completion(
            llm,
            messages=[{"role": "system", "content": _resolve_system_prompt(settings)}, {"role": "user", "content": _compose_model_user_prompt(prompt, settings)}],
            params=_refiner_sampling_params(settings, prompt_count=prompt_count),
        )
        text = extract_text(response) or prompt
        return clean_think_text(str(text).strip())
    if hasattr(llm, "invoke"):
        return clean_think_text(str(llm.invoke(_compose_model_user_prompt(prompt, settings))).strip())
    if hasattr(llm, "generate_content"):
        return clean_think_text(str(llm.generate_content(_compose_model_user_prompt(prompt, settings))).strip())
    return prompt


def maybe_model_refine(
    model: Any,
    prompt: str,
    settings: dict[str, Any],
    *,
    chat_completion: Callable[..., Any],
    clean_think_text: Callable[[str], str],
) -> str:
    llm = getattr(model, "llm", None) or model
    if llm is None:
        return prompt
    try:
        raw_text = _call_model_text(
            llm,
            prompt,
            settings,
            chat_completion=chat_completion,
            clean_think_text=clean_think_text,
            prompt_count=1,
        )
        if _looks_like_broken_prompt(raw_text):
            return prompt
        cleaned = _postprocess_prompt_text(raw_text)
        cleaned = _restore_composition_anchors(prompt, cleaned)
        cleaned = _restore_mode_literal_guards(prompt, cleaned)
        return cleaned if cleaned and not _looks_like_broken_prompt(cleaned) and not _violates_language(cleaned, settings) and not _violates_subject_type(prompt, cleaned, settings) else prompt
    except Exception:
        return prompt
    return prompt


def maybe_model_refine_batch(
    model: Any,
    prompts: list[str],
    settings: dict[str, Any],
    *,
    chat_completion: Callable[..., Any],
    clean_think_text: Callable[[str], str],
) -> list[str]:
    clean_prompts = [str(prompt).strip() for prompt in prompts if str(prompt).strip()]
    if not clean_prompts:
        return []
    if len(clean_prompts) == 1:
        return [maybe_model_refine(model, clean_prompts[0], settings, chat_completion=chat_completion, clean_think_text=clean_think_text)]

    llm = getattr(model, "llm", None) or model
    if llm is None:
        return list(clean_prompts)

    batch_prompt = _compose_batch_prompt(clean_prompts, settings)
    try:
        raw_text = _call_model_text(
            llm,
            batch_prompt,
            settings,
            chat_completion=chat_completion,
            clean_think_text=clean_think_text,
            prompt_count=len(clean_prompts),
        )
    except Exception:
        return list(clean_prompts)

    parts = [part.strip() for part in str(raw_text).split(_BATCH_SEPARATOR)]
    if len(parts) != len(clean_prompts):
        return list(clean_prompts)

    resolved: list[str] = []
    seen_keys: set[str] = set()
    for original_prompt, part in zip(clean_prompts, parts):
        if _looks_like_broken_prompt(part):
            resolved.append(original_prompt)
            seen_keys.add(_normalize_for_compare(original_prompt))
            continue
        cleaned = _postprocess_prompt_text(part)
        cleaned = _restore_composition_anchors(original_prompt, cleaned)
        cleaned = _restore_mode_literal_guards(original_prompt, cleaned)
        candidate = cleaned if cleaned and not _looks_like_broken_prompt(cleaned) and not _violates_language(cleaned, settings) and not _violates_subject_type(original_prompt, cleaned, settings) else original_prompt
        candidate_key = _normalize_for_compare(candidate)
        if candidate_key in seen_keys:
            candidate = original_prompt
            candidate_key = _normalize_for_compare(candidate)
        resolved.append(candidate)
        seen_keys.add(candidate_key)
    return resolved
