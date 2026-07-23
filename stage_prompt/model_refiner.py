# -*- coding: utf-8 -*-
"""Model refinement helpers for stage prompt generation."""

from __future__ import annotations

from collections import Counter
import inspect
import json
import os
import re
import time
from typing import Any, Callable

try:
    from .narrative import (
        GLOBAL_NARRATIVE_MODEL_CONTRACT,
        prompt_preserves_visual_layout,
        resolve_visual_layout_mode,
        visual_layout_contract,
    )
except Exception:  # pragma: no cover - exercised by direct import tests
    from stage_prompt_narrative_test import (  # type: ignore
        GLOBAL_NARRATIVE_MODEL_CONTRACT,
        prompt_preserves_visual_layout,
        resolve_visual_layout_mode,
        visual_layout_contract,
    )

DEFAULT_STAGE_PROMPT_SYSTEM_TEMPLATE = """
你是 Qwen TE 阶段式提示词生成器的默认图像提示词整理模板，兼具资深视觉艺术总监、电影摄影指导、高端人像修图审美和生成式图像 Prompt 工程能力。

任务：把用户输入的节点标签链整理成一段可直接用于 ComfyUI / Stable Diffusion / Flux / Midjourney / Krea 的最终正向提示词正文。输入通常已经包含主体、风格、服装、场景、光影、构图、动作、画质、随机主题池和额外要求，你必须保留这些节点选择，不要擅自改主题，不要抹掉随机差异。

输出硬规则：
1. 只输出最终提示词正文，不输出标题、解释、分析、参数、表格、Markdown、代码块、引号、前后缀或“提示词：”。
2. 默认跟随输入语言；中文输入输出中文，英文输入输出英文，中英混合时优先保留可出图的英文美学词。
3. 输出为一段自然完整的提示词正文；不要分条，不要换行，不要写成教程或摄影分析。中文成品必须为 800-1200 字自然语言；英文目标 420-560 words。
4. 保留主体身份、年龄锚点、人数、服装、动作、场景、构图景别、镜头、光影、材质、风格、画质和负面规避意图；尤其不要删除“中景半身、全景全身、近景、侧逆光、古风、CG感、神话感、NSFW”等关键锚点。
5. 同一批多条提示词必须保持各自差异，不要合并成同一条，也不要把不同随机主题池改成相同画面。
6. 先建立事件与因果，再自然展开主体身份、服装材质、动作目的、情绪转折、场景空间、环境反馈、光影迁移、镜头时机和画质稳定性。不要按固定维度逐段点名，不要用近义词反复灌水。
7. 全局构图必须服务剧情：主体的动作改变环境，环境或道具给出回应，光线与焦点随事件推进，最后让镜头定格在具有前因后果和继续想象空间的状态。
8. 具体描述优先于空泛形容：用“暖色侧逆光、雨雾竹林、35mm 胶片颗粒、丝绸边缘高光、湿润石阶反光”这类可见信息替代“好看、震撼、顶级、神级”等空词。
9. 外部平台参数、码图 --profile / profile code、UUID、--ar、--stylize、--raw、--hd、--seed 等只可作为参考来源信息，绝对不要进入最终提示词正文。
10. 素材库只提供写法和词汇方向，不提供固定模板；不得锁死“古风、武侠、CG、全身、白底、某个角色、某个场景”。用户已选标签和当前随机结果永远优先。
11. 如果当前上下文已形成一条明确主线，例如运行时随机结果、NSFW 工作台成熟主线、智能文本主线或角色设定图主线，优先沿这条主线补足服装、场景、动作、光影和材质，不要退回成标签清单，也不要把多个互斥主线强拼到同一条提示词里。
12. 如果主体类型为“非人物主体”，必须按物体、载具、机甲、建筑、场景、生物或概念主体处理；禁止改写成成年女性、男性、女孩、模特、人像写真或角色肖像；不要补脸部、皮肤、发型、手指、身材、内衣、礼服、高跟鞋等人物细节，改写重点应为结构、比例、材质、功能部件、尺度关系、空间层次、光影和画质。
13. 不要复用固定开头、固定段落或固定模板句。每次必须依据当前按钮、标签、随机结果、NSFW 工作台和智能文本输入重新组织画面主线；相同语义只写一次，禁止用近义句反复扩字数。
14. API、本地模型和 Skill-only 都必须遵守同一套全局 Skill 判断：先读当前节点选择、随机运行时解析、智能文本解析、NSFW 工作台摘要、标签块编排顺序和高级按钮设置，再决定主体、场景、服装、动作、光影、道具和风格；不得把未选择的固定素材塞回输出。
15. 批量生成、运行时随机、智能文本连续匹配或 API 连续调用时，每一条都要形成独立视觉档案：主体身份、环境、服装、动作、持物、光影、色彩、镜头组织中至少三个核心维度明确变化；最近输出只用于避让，不是可复写素材，不要把上一条输出的主体/场景/动作/配色机械复制到下一条。
16. 剧情链只用于确定因果，最终图只显示一个决定性时刻。默认同一人物仅出现一次且只有一个清晰头部和一张脸；显式双人或群像保留人数但每人只出现一次；仅显式角色设定图、三视图、四联画或镜中视图允许多视图。禁止模型自行添加上下重复、分屏、拼贴、故事板、堆叠肖像、复制倒影或时间切片。
17. 正向正文只写希望实际出现的视觉事实。把唯一主体、完整身体、清晰脸部、准确肢体数量、干净表面写成肯定句；分屏、克隆、重复脸、额外头部、重影、文字和水印等排除概念由节点的推荐负面提示词承载，严禁把这些错误视觉词连同“不要/避免/无”复制进正向正文。

美学方向：
- 真实感/摄影向：强调真实存在感、自然脸型、非网红脸、非塑料 AI 皮肤；保留真实毛孔、细微肤色差、绒毛、唇纹、眼下细纹、鼻翼微油光等“真实但美”的肌肤细节；使用自然镜头透视、轻微抓拍感、浅景深、电影光影、真实环境曝光。
- 高端人像/时尚向：强调视觉和谐、优雅仪态、清澈有故事感的眼神、精致但不过度磨皮的肤质、真丝/蕾丝/羊绒/皮革/金属等材质的垂坠、纹理和边缘高光。
- 插画感/CG感/古风/神话感：严格服从节点模式，不要强行改成写实摄影；把材质、光影、构图和画质转换为对应媒介的高完成度表达，如电影级 CG、概念设计、工笔重彩、东方古风、神圣史诗、魔幻现实主义等。
- 场景与构图：补足前景/中景/背景层次、主体占比、镜头距离、视角、留白、焦点层级、空间深度和环境细节，但不要添加与节点主题冲突的道具或地点。
- 光线与色彩：明确主光、辅光、轮廓光、软硬、色温、阴影、反射、对比度、胶片颗粒、低饱和或高级配色；若输入含参考色调或风格锚点，只迁移色相、光感、影调、材质和情绪，不复制无关空间、文字、品牌或具体道具。
- 素材库常见优秀结构包括：古风电影氛围、港式武侠胶片、现代都市生活流、科幻机甲、东方赛博、商业广告、时尚编辑、神话史诗、日韩影像等。它们只能作为“风格通道”，必须随当前模式与标签自动切换，不可混成一个杂烩。

质量与限制：
正向正文使用纯正向质量描述，例如清晰对焦、精致纹理、真实材质、自然解剖、手部结构与数量准确、身体关系完整、肤质保留真实微细节、亮暗层次稳定、背景表面干净。所有排除性质量词留在节点推荐负面提示词中，不得混入最终正向正文。

最终目标：输出一段“主题明确、剧情清楚、细节丰富、模式一致、可直接出图”的高质量正向提示词。长度必须靠事件推进、空间关系、镜头组织、材质与光影反馈自然展开，不能为了字数重复叠加标签。
""".strip()
DEFAULT_STAGE_PROMPT_SYSTEM_TEMPLATE = (
    f"{DEFAULT_STAGE_PROMPT_SYSTEM_TEMPLATE}\n\n{GLOBAL_NARRATIVE_MODEL_CONTRACT}"
)

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
_MODEL_REASONING_BLOCK_PATTERN = re.compile(
    r"<(?:think|analysis|reasoning)\b[^>]*>.*?</(?:think|analysis|reasoning)>",
    flags=re.DOTALL | re.IGNORECASE,
)
_MODEL_REASONING_CLOSE_PATTERN = re.compile(
    r"</(?:think|analysis|reasoning)>\s*",
    flags=re.IGNORECASE,
)
_MODEL_REASONING_OPEN_PATTERN = re.compile(
    r"<(?:think|analysis|reasoning)\b[^>]*>\s*",
    flags=re.IGNORECASE,
)
_MODEL_FINAL_SECTION_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:#{1,6}\s*)?(?:\*{1,2})?\s*"
    r"(?:最终(?:正向)?提示词|成品提示词|最终正文|最终答案|图像提示词|"
    r"final\s+(?:image\s+)?prompt|final\s+answer|answer)\s*"
    r"(?:\*{1,2})?\s*[:：]\s*",
    flags=re.IGNORECASE,
)
_MODEL_ECHO_BODY_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:待整理提示词正文|待改写提示词|prompt\s+to\s+(?:refine|rewrite))\s*[:：]\s*",
    flags=re.IGNORECASE,
)
_MODEL_ASSISTANT_BOUNDARY_PATTERN = re.compile(
    r"(?:<\|im_start\|>\s*assistant\b|"
    r"<\|start_header_id\|>\s*assistant\s*<\|end_header_id\|>|"
    r"<\|assistant\|>|(?:^|\n)\s*(?:#{1,6}\s*)?assistant\s*[:：]\s*)",
    flags=re.IGNORECASE,
)
_MODEL_SPECIAL_TOKEN_PATTERN = re.compile(
    r"<\|/?(?:assistant|final|analysis|reasoning|im_start|im_end|start_header_id|end_header_id|eot_id)[^>]*\|?>",
    flags=re.IGNORECASE,
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
_FANTASY_STYLE_LITERAL_GUARDS = (
    "奇幻风格",
    "西方奇幻",
    "高等奇幻",
    "剑与魔法",
    "哥特奇幻",
    "黑暗童话",
    "精灵幻想",
    "梦幻奇境",
    "日式奇幻动画",
    "漆原智志画风",
    "结城信辉画风",
    "童话绘本",
    "魔幻油画",
    "奇幻概念设计",
    "史诗奇幻海报",
    "highly finished fantasy key visual",
    "western fantasy epic illustration",
    "high fantasy epic key visual",
    "sword-and-sorcery adventure illustration",
    "gothic fantasy narrative illustration",
    "dark fairy-tale storybook key visual",
    "elven fantasy character illustration",
    "dreamlike fantasy wonderland illustration",
    "Japanese fantasy anime key frame",
    "Satoshi Urushihara-inspired ornate fantasy anime illustration",
    "Nobuteru Yuki-inspired elegant fantasy character illustration",
    "fantasy fairy-tale storybook illustration",
    "magical narrative oil painting",
    "highly finished fantasy concept design",
    "epic fantasy cinematic poster",
)
_MODE_LITERAL_GUARD_RULES += tuple(
    ((anchor,), (anchor,), ()) for anchor in _FANTASY_STYLE_LITERAL_GUARDS
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
_CREATIVE_SPINE_GROUP_LIMITS: tuple[tuple[str, int], ...] = (
    ("主体", 6),
    ("画面风格", 5),
    ("服装造型", 5),
    ("场景背景", 5),
    ("动作姿态", 4),
    ("光影氛围", 5),
    ("构图视角", 5),
    ("道具世界观", 4),
    ("技术画质", 4),
    ("成人向表达", 4),
)
_CREATIVE_SPINE_REQUIRED_ANCHOR_GROUPS = ("主体", "服装造型", "场景背景", "动作姿态")
_CREATIVE_SPINE_STYLE_FAMILIES: dict[str, tuple[str, ...]] = {
    "真实感": (
        "照片级", "写实摄影", "摄影写实", "电影写实", "纪实抓拍", "商业摄影", "杂志摄影",
        "photorealistic", "photographic", "documentary photography", "editorial photography", "raw photo",
        "胶片感", "胶片摄影", "film photography",
    ),
    "插画感": (
        "插画", "水彩", "油画", "厚涂", "手绘", "动漫", "二次元", "赛璐璐", "OVA风", "绘本",
        "illustration", "watercolor", "oil painting", "anime", "cel-shaded", "storybook",
    ),
    "CG感": (
        "电影级CG", "3D渲染", "PBR渲染", "Octane渲染", "虚幻引擎", "概念设计稿", "赛博朋克",
        "机能赛博", "全息投影", "photorealistic 3d", "3d render", "pbr render", "octane render",
        "unreal engine", "cyberpunk",
    ),
    "古风": (
        "古风", "国风", "古装", "武侠", "仙侠", "工笔", "水墨写意", "宋韵", "唐风", "明制",
        "ancient chinese", "wuxia", "xianxia", "gongbi", "ink wash",
    ),
    "神话感": (
        "神话", "神圣史诗", "暗黑奇幻", "高等奇幻", "剑与魔法", "哥特奇幻", "精灵幻想",
        "mythic", "mythological", "epic fantasy", "dark fantasy", "high fantasy", "sword and sorcery",
    ),
}
_CREATIVE_SPINE_SCENE_FAMILIES: dict[str, tuple[str, ...]] = {
    "古代人文": (
        "宫殿", "宫道", "古城", "古街", "古镇", "庭院", "回廊", "水榭", "月洞门", "书院", "客栈",
        "ancient palace", "ancient city", "old town", "courtyard", "covered corridor",
    ),
    "私密室内": (
        "卧室", "酒店套房", "浴室", "浴缸", "淋浴", "温泉", "更衣室", "床边", "落地窗夜景",
        "bedroom", "hotel suite", "bathroom", "bathtub", "shower room", "dressing room",
    ),
    "都市空间": (
        "城市街道", "城市街边", "街头", "街巷", "小巷", "站台", "车站", "地铁", "天台", "停车场",
        "办公室", "咖啡厅", "便利店", "酒吧", "夜店", "urban street", "city street", "alley", "station",
        "subway", "rooftop", "parking garage", "office", "cafe", "bar",
    ),
    "工业科幻": (
        "机库", "维修舱", "太空船", "飞船", "工业废墟", "未来都市", "霓虹街区", "机械舱", "轨道空间站",
        "hangar", "maintenance bay", "spaceship", "spacecraft", "industrial ruin", "futuristic city",
        "mechanical bay", "orbital station",
    ),
    "自然荒野": (
        "森林", "竹林", "山谷", "草原", "草甸", "沙漠", "荒野", "海滩", "海岸", "湖畔", "溪流", "瀑布",
        "forest", "bamboo grove", "valley", "grassland", "meadow", "desert", "wilderness", "beach",
        "coast", "lakeside", "stream", "waterfall",
    ),
    "神圣场所": (
        "神殿", "祭坛", "教堂", "圣所", "寺庙", "神社", "宗教空间", "throne temple", "temple", "altar",
        "church", "cathedral", "sanctuary", "shrine",
    ),
    "影棚极简": (
        "摄影棚", "影棚", "白棚", "纯色背景", "无缝背景", "极简背景", "白色背景", "studio",
        "seamless backdrop", "plain background", "minimal background", "white background",
    ),
}
_CREATIVE_SPINE_NEGATION_PATTERN = re.compile(
    r"(?:不要|避免|禁止|并非|不是|没有|无|非|no|not|without|avoid|exclude)\s*$",
    flags=re.IGNORECASE,
)


def _normalize_model_source_label(value: Any) -> str:
    """Collapse legacy or backend-specific local labels into the public local-model source."""

    source = str(value or "").strip()
    if not source:
        return "仅Skill"
    if source.startswith("本地"):
        suffix_index = source.find("（")
        suffix = source[suffix_index:] if suffix_index >= 0 else ""
        return f"本地模型{suffix}"
    return source


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


def _extract_content_text(content: Any, *, _depth: int = 0) -> str:
    if _depth > 6:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        for key in ("text", "output_text", "generated_text", "content", "prompt", "final_prompt", "completion"):
            if key not in content:
                continue
            text = _extract_content_text(content.get(key), _depth=_depth + 1)
            if text:
                return text
        return ""
    if not isinstance(content, (list, tuple)):
        return ""
    assistant_blocks = [
        block
        for block in content
        if isinstance(block, dict) and str(block.get("role") or "").strip().casefold() == "assistant"
    ]
    if assistant_blocks:
        content = assistant_blocks[-1:]
    parts: list[str] = []
    for block in content:
        text = _extract_content_text(block, _depth=_depth + 1).strip()
        if text:
            parts.append(text)
    return "\n".join(parts)


def extract_text(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, (list, tuple)):
        return _extract_content_text(response)
    if isinstance(response, dict):
        error = response.get("error")
        if error:
            if isinstance(error, dict):
                reason = error.get("message") or error.get("type") or error.get("code") or "未知 API 错误"
            else:
                reason = error
            raise RuntimeError(f"模型 API 返回错误：{reason}")
        for key in (
            "text", "output_text", "generated_text", "response", "answer", "content", "result", "output",
            "prompt", "final_prompt", "completion",
        ):
            text = _extract_content_text(response.get(key))
            if text:
                return text
        choices = response.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            choice = choices[0]
            message = choice.get("message")
            if isinstance(message, dict):
                text = _extract_content_text(message.get("content"))
                if text:
                    return text
            text = _extract_content_text(choice.get("text"))
            if text:
                return text
        return ""
    for attribute in ("text", "output_text", "generated_text", "content", "response", "answer", "completion"):
        text = _extract_content_text(getattr(response, attribute, None))
        if text:
            return text
    choices = getattr(response, "choices", None)
    if isinstance(choices, (list, tuple)) and choices:
        message = getattr(choices[0], "message", None)
        text = _extract_content_text(getattr(message, "content", None))
        if text:
            return text
    return ""



_NATURAL_PROSE_MARKERS = (
    "画面以", "主体处于", "主体位于", "整体遵循", "镜头采用", "最终画面",
    "塑造主光", "叙事锚点", "自然融入", "保持主题", "避免标签堆叠",
    " centered on ", " situated in ", " unified through ", " the camera uses ",
    " the final image ", " narrative anchors", "visual direction", "without tag-chain phrasing",
)
_NATURAL_SENTENCE_PATTERN = re.compile(r".+?(?:[。！？.!?]+|$)", re.DOTALL)


def _looks_like_natural_prose_prompt(text: str) -> bool:
    body = str(text or "").split("中文说明：", 1)[0].strip()
    if not body:
        return False
    lowered = f" {body.casefold()} "
    marker_hits = sum(1 for marker in _NATURAL_PROSE_MARKERS if marker in lowered)
    terminator_count = len(re.findall(r"[。！？.!?]", body))
    if re.search(r"[\u4e00-\u9fff]", body):
        return marker_hits >= 2 or (terminator_count >= 2 and len(body) >= 60)
    return marker_hits >= 2 or (terminator_count >= 2 and len(body.split()) >= 18)


def _dedupe_natural_prompt_units(text: str) -> str:
    source = str(text or "").strip()
    if not source:
        return ""
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", source))
    seen_sentences: set[str] = set()
    output_units: list[str] = []
    for match in _NATURAL_SENTENCE_PATTERN.finditer(source):
        unit = match.group(0).strip()
        if not unit:
            continue
        terminal_match = re.search(r"([。！？.!?]+)$", unit)
        terminal = terminal_match.group(1) if terminal_match else ""
        body = unit[: -len(terminal)].strip() if terminal else unit
        clauses = [clause.strip(" ，,；;。.!?！？") for clause in re.split(r"\s*[；;]\s*", body)]
        clauses = [clause for clause in clauses if clause]
        seen_clauses: set[str] = set()
        deduped_clauses: list[str] = []
        for clause in clauses:
            key = _normalize_for_compare(clause)
            if not key or key in seen_clauses:
                continue
            seen_clauses.add(key)
            deduped_clauses.append(clause)
        if not deduped_clauses:
            continue
        rebuilt = ("；" if has_cjk else "; ").join(deduped_clauses)
        sentence_key = _normalize_for_compare(rebuilt)
        if not sentence_key or sentence_key in seen_sentences:
            continue
        seen_sentences.add(sentence_key)
        output_units.append(f"{rebuilt}{terminal}")
    result = ("" if has_cjk else " ").join(output_units).strip()
    if not result:
        return ""
    if not re.search(r"[。！？.!?]$", result):
        result += "。" if has_cjk else "."
    return result


def _postprocess_natural_prompt_text(text: str) -> str:
    normalized = str(text or "").strip().replace("\r\n", "\n").replace("\r", "\n")
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
        line = re.sub(r"\s+", " ", line).strip("“”\"'` ")
        if line:
            lines.append(line)
    collapsed = " ".join(lines) if lines else normalized
    collapsed = re.sub(r"\s+", " ", collapsed)
    collapsed = re.sub(r"\s*([，。；！？])\s*", r"\1", collapsed)
    collapsed = re.sub(r"\s*([,;.!?])\s*", lambda match: f"{match.group(1)} ", collapsed).strip()
    collapsed = re.sub(r"([。！？])\1+", r"\1", collapsed)
    collapsed = re.sub(r"([,;])\1+", r"\1", collapsed)
    return _dedupe_natural_prompt_units(collapsed)

def _postprocess_prompt_text(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*", "", normalized)
    normalized = re.sub(r"\s*```\s*$", "", normalized)
    if _looks_like_natural_prose_prompt(normalized):
        return _postprocess_natural_prompt_text(normalized)
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



def _looks_like_tag_chain_prompt(text: str) -> bool:
    """Detect unique but list-like model output so the natural Skill prompt can be retained."""

    body = str(text or "").split("中文说明：", 1)[0].strip()
    if not body:
        return False
    fragments = [item.strip() for item in re.split(r"[，,、；;]+", body) if item.strip()]
    if len(fragments) < 6:
        return False
    lowered = body.casefold()
    natural_markers = (
        "画面以", "主体", "场景", "镜头", "光影", "呈现", "采用", "位于", "处于", "保持", "强调", "塑造", "让", "融入",
        " centered on ", " in a ", " within ", " while ", " where ", " with ", " the scene ", " the camera ", " lighting ", " remains ", " creates ",
    )
    if sum(1 for marker in natural_markers if marker in lowered) >= 2:
        return False
    has_cjk = bool(re.search(r"[\u4e00-\u9fff]", body))
    if has_cjk:
        average_length = sum(len(re.sub(r"\s+", "", item)) for item in fragments) / len(fragments)
        return average_length <= 10 and body.count("。") <= 1
    average_words = sum(len(item.split()) for item in fragments) / len(fragments)
    return average_words <= 4 and body.count(".") <= 1


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
    if _looks_like_tag_chain_prompt(normalized):
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


def _prepare_model_response_text(text: str) -> tuple[str, bool]:
    """Extract a final prompt from common local-model reasoning and wrapper formats."""

    source = str(text or "").strip()
    if not source:
        return "", False
    recovered = False

    if source[:1] in {"{", "["}:
        try:
            decoded = json.loads(source)
        except (TypeError, ValueError, json.JSONDecodeError):
            decoded = None
        if decoded is not None:
            extracted = str(extract_text(decoded) or "").strip()
            if extracted and extracted != source:
                source = extracted
                recovered = True

    # Text-generation pipelines often return the complete rendered chat prompt
    # followed by the assistant continuation. Only the continuation is model output.
    assistant_matches = list(_MODEL_ASSISTANT_BOUNDARY_PATTERN.finditer(source))
    if assistant_matches:
        source = source[assistant_matches[-1].end() :]
        recovered = True

    stripped = _MODEL_REASONING_BLOCK_PATTERN.sub("", source)
    if stripped != source:
        source = stripped
        recovered = True
    close_matches = list(_MODEL_REASONING_CLOSE_PATTERN.finditer(source))
    if close_matches:
        source = source[close_matches[-1].end() :]
        recovered = True
    open_stripped = _MODEL_REASONING_OPEN_PATTERN.sub("", source)
    if open_stripped != source:
        source = open_stripped
        recovered = True
    special_stripped = _MODEL_SPECIAL_TOKEN_PATTERN.sub("", source)
    if special_stripped != source:
        source = special_stripped
        recovered = True

    final_matches = list(_MODEL_FINAL_SECTION_PATTERN.finditer(source))
    if final_matches:
        source = source[final_matches[-1].end() :]
        recovered = True
    elif any(marker in source for marker in _ANALYSIS_MARKERS):
        echo_matches = list(_MODEL_ECHO_BODY_PATTERN.finditer(source))
        if echo_matches:
            source = source[echo_matches[-1].end() :]
            recovered = True

    cleaned_lines: list[str] = []
    analysis_preamble = any(marker in source for marker in _ANALYSIS_MARKERS) or bool(
        re.search(r"(?:^|\n)\s*(?:分析|思考|推理|reasoning|analysis)\s*[:：]", source, flags=re.IGNORECASE)
    )
    prompt_body_started = not analysis_preamble
    for raw_line in source.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        plain = line.strip("#* ")
        if any(marker in plain for marker in _ANALYSIS_MARKERS) and len(plain) <= 180:
            recovered = True
            continue
        if re.match(r"^(?:分析|思考|推理|reasoning|analysis)\s*[:：]", plain, flags=re.IGNORECASE):
            recovered = True
            continue
        if not prompt_body_started:
            looks_like_body = _looks_like_natural_prose_prompt(plain) or (
                len(_CJK_PATTERN.findall(plain)) >= 24 and bool(re.search(r"[。！？]", plain))
            )
            if not looks_like_body:
                recovered = True
                continue
            prompt_body_started = True
        cleaned_lines.append(line.replace("**", ""))
    return "\n".join(cleaned_lines).strip(), recovered


def _split_prompt_sentences(text: str) -> list[str]:
    source = str(text or "").strip()
    if not source:
        return []
    units = [match.group(0).strip() for match in _NATURAL_SENTENCE_PATTERN.finditer(source)]
    return [unit for unit in units if unit]


def _bounded_cjk_excerpt(text: str, max_chars: int) -> str:
    budget = max(0, int(max_chars or 0))
    if budget < 24:
        return ""
    pieces: list[str] = []
    used = 0
    for unit in _split_prompt_sentences(text):
        compact = re.sub(r"\s+", "", unit)
        if not compact:
            continue
        if used + len(compact) <= budget:
            pieces.append(unit)
            used += len(compact)
            continue
        remaining = budget - used
        if remaining < 24:
            break
        body = unit.rstrip("。！？.!?")
        clauses = [item.strip() for item in re.split(r"(?<=[，,；;])", body) if item.strip()]
        partial = ""
        for clause in clauses:
            clause_length = len(re.sub(r"\s+", "", clause))
            if len(re.sub(r"\s+", "", partial)) + clause_length > remaining:
                break
            partial += clause
        if len(re.sub(r"\s+", "", partial)) >= 24:
            pieces.append(partial.rstrip("，,；;") + "。")
        break
    return "".join(pieces).strip()


def _blend_model_draft_with_skill_prompt(original_prompt: str, model_prompt: str, settings: dict[str, Any]) -> str:
    """Keep the valid Skill story spine while adopting useful detail from a shorter model draft."""

    original = str(original_prompt or "").strip()
    candidate = str(model_prompt or "").strip()
    if not original or not candidate or not _CJK_PATTERN.search(original):
        return original
    if not _looks_like_natural_prose_prompt(candidate) or _looks_like_tag_chain_prompt(candidate):
        return original

    original_key = _normalize_for_compare(original)
    candidate_units = [
        unit
        for unit in _split_prompt_sentences(candidate)
        if _normalize_for_compare(unit) and _normalize_for_compare(unit) not in original_key
    ]
    if not candidate_units:
        return original
    candidate_text = "".join(candidate_units)
    original_units = _split_prompt_sentences(original)
    if len(original_units) < 3:
        return original

    original_length = len(re.sub(r"\s+", "", original))
    insert_budget = min(260, max(0, 1200 - original_length))
    excerpt = _bounded_cjk_excerpt(candidate_text, insert_budget)
    insert_at = max(1, len(original_units) - 1)
    if excerpt:
        original_units.insert(insert_at, excerpt)
    else:
        protected = ("故事", "事件", "因此", "于是", "因为", "情绪", "镜头", "最终画面", "最后一帧", "结尾", "定格")
        replace_candidates = [
            (index, unit)
            for index, unit in enumerate(original_units[1:-1], start=1)
            if not any(marker in unit for marker in protected)
        ]
        if not replace_candidates:
            return original
        replace_index, replace_unit = max(replace_candidates, key=lambda item: len(item[1]))
        replace_budget = min(260, max(24, 1200 - original_length + len(re.sub(r"\s+", "", replace_unit))))
        excerpt = _bounded_cjk_excerpt(candidate_text, replace_budget)
        if not excerpt:
            return original
        original_units[replace_index] = excerpt

    blended = _postprocess_natural_prompt_text("".join(original_units))
    blended = _restore_composition_anchors(original, blended)
    blended = _restore_mode_literal_guards(original, blended)
    if blended == original or _violates_language(blended, settings) or _violates_subject_type(original, blended, settings):
        return original
    return blended if _looks_like_narrative_prompt(blended, settings) else original


def _validated_model_blend(
    original_prompt: str,
    model_prompt: str,
    settings: dict[str, Any],
    *,
    layout_mode: str,
) -> str:
    blended = _blend_model_draft_with_skill_prompt(original_prompt, model_prompt, settings)
    if blended == str(original_prompt or "").strip():
        return str(original_prompt or "").strip()
    if layout_mode and not prompt_preserves_visual_layout(blended, layout_mode):
        return str(original_prompt or "").strip()
    if _creative_spine_violation(original_prompt, blended, settings):
        return str(original_prompt or "").strip()
    return blended


def _resolve_model_prompt_candidate(
    original_prompt: str,
    raw_text: str,
    settings: dict[str, Any],
) -> tuple[str, str, str]:
    prepared, recovered = _prepare_model_response_text(raw_text)
    if not prepared or _looks_like_broken_prompt(prepared):
        return original_prompt, "rejected", "模型响应清洗后仍只有分析、占位符、标签串或不可用正文。"
    cleaned = _postprocess_prompt_text(prepared)
    cleaned = _restore_composition_anchors(original_prompt, cleaned)
    cleaned = _restore_mode_literal_guards(original_prompt, cleaned)
    if not cleaned or _looks_like_broken_prompt(cleaned):
        return original_prompt, "rejected", "模型响应清洗后没有可用提示词正文。"
    if _violates_language(cleaned, settings):
        return original_prompt, "rejected", "模型响应未遵守当前提示词语言。"
    if _violates_subject_type(original_prompt, cleaned, settings):
        return original_prompt, "rejected", "模型响应改变了当前主体类型。"
    layout_mode = str(settings.get("画面结构模式解析结果", "") or "").strip()
    if layout_mode and not prompt_preserves_visual_layout(cleaned, layout_mode):
        blended = _validated_model_blend(original_prompt, cleaned, settings, layout_mode=layout_mode)
        if blended != str(original_prompt or "").strip():
            return blended, "blended", ""
        return original_prompt, "rejected", "模型响应未保留当前单帧、人数或多视图画面结构合同。"
    spine_violation = _creative_spine_violation(original_prompt, cleaned, settings)
    if spine_violation:
        blended = _validated_model_blend(original_prompt, cleaned, settings, layout_mode=layout_mode)
        if blended != str(original_prompt or "").strip():
            return blended, "blended", ""
        return original_prompt, "rejected", spine_violation
    if not _looks_like_narrative_prompt(cleaned, settings):
        blended = _validated_model_blend(original_prompt, cleaned, settings, layout_mode=layout_mode)
        if blended != str(original_prompt or "").strip():
            return blended, "blended", ""
        return original_prompt, "rejected", "模型正文可读，但缺少完整剧情链或未达到当前 800-1200 字合同。"
    return cleaned, ("cleaned" if recovered else "direct"), ""


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
            "Target 420-560 English words. Do not output Chinese characters, Chinese labels, explanations, headings, Markdown, or bilingual notes."
        )
    if language == "英文提示词+中文说明":
        return (
            "\n\nLanguage override: Output an English prompt body first, targeting 420-560 English words, "
            "then append one short Chinese companion note beginning with `中文说明：` to summarize the visual direction. "
            "Keep the English prompt usable by itself; do not add headings, Markdown, or analysis."
        )
    if language == "纯中文":
        return "\n\n语言覆盖：最终正向提示词正文必须使用中文，不要改成英文提示词；中文成品必须为 800-1200 字自然语言。"
    return ""


def _resolve_system_prompt(settings: dict[str, Any]) -> str:
    if str(settings.get("模型任务", "") or "").strip() == "视频提示词":
        video_prompt = str(settings.get("视频提示词模型系统提示", "") or "").strip()
        if video_prompt:
            language = _prompt_language_mode(settings)
            if language == "纯中文":
                video_prompt += "\n\n最终中文正文必须为 800-1200 字。"
            elif language == "纯英文":
                video_prompt += "\n\n最终英文正文必须为 90-230 个英文单词。"
            else:
                video_prompt += "\n\n英文正文后必须保留完整的中文说明，中文说明必须为 800-1200 字。"
            return video_prompt
    base_prompt = str(settings.get("系统提示词覆盖") or _DEFAULT_IMAGE_REFINER_SYSTEM)
    narrative_contract = "" if GLOBAL_NARRATIVE_MODEL_CONTRACT in base_prompt else f"\n\n{GLOBAL_NARRATIVE_MODEL_CONTRACT}"
    layout_mode = resolve_visual_layout_mode(settings=settings)
    layout_contract = visual_layout_contract(
        layout_mode,
        english=_prompt_language_mode(settings) in {"纯英文", "英文提示词+中文说明"},
    )
    return f"{base_prompt}{narrative_contract}\n\n当前画面结构硬约束：{layout_contract}{_language_instruction(settings)}"


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


def is_natural_language_prompt(text: str, settings: dict[str, Any] | None = None) -> bool:
    """Validate the final natural-language contract shared by every positive-output mode."""

    prompt = str(text or "").strip()
    if not prompt or _looks_like_tag_chain_prompt(prompt):
        return False
    active_settings = settings or {}
    if active_settings and _violates_language(prompt, active_settings):
        return False
    if active_settings and not _looks_like_narrative_prompt(prompt, active_settings):
        return False
    layout_mode = str(active_settings.get("画面结构模式解析结果", "") or "").strip()
    if layout_mode and not prompt_preserves_visual_layout(prompt, layout_mode):
        return False
    return _looks_like_natural_prose_prompt(prompt)


_NARRATIVE_MARKER_GROUPS_ZH = (
    ("故事", "事件", "发生", "随后", "当", "起初"),
    ("因此", "于是", "因为", "迫使", "打破", "触发"),
    ("回应", "选择", "动作", "移动", "停下", "转身", "靠近"),
    ("情绪", "神情", "警觉", "犹豫", "决断", "释然", "不安"),
    ("环境", "空间", "光线", "反射", "阴影", "空气", "材质"),
    ("镜头", "定格", "最后一帧", "结尾", "画面停在", "最终画面"),
)


def _bounded_creative_spine_values(values: Any, limit: int) -> list[str]:
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        return []
    result: list[str] = []
    for value in values:
        text = " ".join(str(value or "").strip().split()).strip("，,；; ")
        if not text or text in {"自动", "无", "未启用"} or text in result:
            continue
        result.append(text[:96])
        if len(result) >= limit:
            break
    return result


def build_global_creative_spine_contract(
    selected: dict[str, Any],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    template_style: str,
    subject_type: str,
    layout_mode: str,
    primary_style_family: str,
) -> dict[str, Any]:
    """Freeze the normalized visual mainline shared by Skill, smart text and model refiners."""

    groups: dict[str, list[str]] = {}
    for group_name, limit in _CREATIVE_SPINE_GROUP_LIMITS:
        values = _bounded_creative_spine_values(selected.get(group_name, []), limit)
        if values:
            groups[group_name] = values
    custom = _bounded_creative_spine_values(custom_tags, 6)
    if custom:
        groups["自定义补充"] = custom
    return {
        "version": 1,
        "template": str(template_style or settings.get("模板风格", "自动") or "自动").strip(),
        "theme_pool": str(settings.get("随机主题池", "自动") or "自动").strip(),
        "style_isolation": str(settings.get("风格隔离策略", "平衡收敛") or "平衡收敛").strip(),
        "primary_style_family": str(primary_style_family or "").strip(),
        "subject_type": str(subject_type or settings.get("主体类型", "自动") or "自动").strip(),
        "layout": str(layout_mode or settings.get("画面结构模式解析结果", "") or "").strip(),
        "groups": groups,
    }


def summarize_global_creative_spine_contract(contract: Any) -> str:
    if not isinstance(contract, dict):
        return ""
    parts = [
        f"模板={contract.get('template', '自动')}",
        f"主题池={contract.get('theme_pool', '自动')}",
        f"主风格族={contract.get('primary_style_family', '') or '自动'}",
        f"隔离={contract.get('style_isolation', '平衡收敛')}",
        f"画面结构={contract.get('layout', '') or '自动'}",
    ]
    groups = contract.get("groups")
    if isinstance(groups, dict):
        for group_name, _limit in _CREATIVE_SPINE_GROUP_LIMITS:
            values = _bounded_creative_spine_values(groups.get(group_name, []), 5)
            if values:
                parts.append(f"{group_name}={'、'.join(values)}")
        custom = _bounded_creative_spine_values(groups.get("自定义补充", []), 4)
        if custom:
            parts.append(f"自定义补充={'、'.join(custom)}")
    return "；".join(parts)


def _positive_creative_marker_present(text: str, marker: str) -> bool:
    source = str(text or "")
    needle = str(marker or "").strip()
    if not source or not needle:
        return False
    source_key = source.casefold()
    needle_key = needle.casefold()
    if needle_key.isascii() and re.fullmatch(r"[a-z0-9][a-z0-9 ._-]*", needle_key):
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(needle_key)}(?![a-z0-9])", flags=re.IGNORECASE)
        matches = pattern.finditer(source_key)
    else:
        matches = (match for match in re.finditer(re.escape(needle_key), source_key))
    for match in matches:
        prefix = source_key[max(0, match.start() - 12) : match.start()]
        if not _CREATIVE_SPINE_NEGATION_PATTERN.search(prefix):
            return True
    return False


def _creative_family_hits(text: str, families: dict[str, tuple[str, ...]]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for family_name, markers in families.items():
        matched = [marker for marker in markers if _positive_creative_marker_present(text, marker)]
        if matched:
            hits[family_name] = matched
    return hits


def _creative_spine_violation(original_prompt: str, candidate_prompt: str, settings: dict[str, Any]) -> str:
    contract = settings.get("全局创作主线合同")
    if not isinstance(contract, dict):
        return ""
    groups = contract.get("groups")
    if not isinstance(groups, dict):
        groups = {}
    original = str(original_prompt or "")
    candidate = str(candidate_prompt or "")
    language = str(settings.get("提示词语言", "纯中文") or "纯中文").strip()
    if language not in {"纯英文", "英文提示词+中文说明"}:
        original_key = original.casefold()
        candidate_key = candidate.casefold()
        for group_name in _CREATIVE_SPINE_REQUIRED_ANCHOR_GROUPS:
            for anchor in _bounded_creative_spine_values(groups.get(group_name, []), 6):
                anchor_key = anchor.casefold()
                if anchor_key in original_key and anchor_key not in candidate_key:
                    return f"模型响应改变了当前创作主线：缺少{group_name}锚点“{anchor}”。"

    allowed_style_values = [str(contract.get("template", "") or "")]
    for group_values in groups.values():
        allowed_style_values.extend(_bounded_creative_spine_values(group_values, 8))
    allowed_style_text = "，".join(allowed_style_values)
    primary_style_family = str(contract.get("primary_style_family", "") or "").strip()
    candidate_style_hits = _creative_family_hits(candidate, _CREATIVE_SPINE_STYLE_FAMILIES)
    allowed_style_hits = _creative_family_hits(allowed_style_text, _CREATIVE_SPINE_STYLE_FAMILIES)
    for family_name, markers in candidate_style_hits.items():
        if family_name == primary_style_family:
            continue
        disallowed_markers = [
            marker
            for marker in markers
            if not _positive_creative_marker_present(allowed_style_text, marker)
        ]
        if primary_style_family and disallowed_markers:
            return f"模型响应改变了当前创作主线：引入冲突风格“{disallowed_markers[0]}”。"
        if not primary_style_family and family_name not in allowed_style_hits:
            return f"模型响应改变了当前创作主线：引入未选择的风格族“{family_name}”。"

    allowed_scene_text = "，".join(str(item) for item in list(groups.get("场景背景", []) or []))
    allowed_scene_hits = _creative_family_hits(allowed_scene_text, _CREATIVE_SPINE_SCENE_FAMILIES)
    if allowed_scene_hits:
        candidate_scene_hits = _creative_family_hits(candidate, _CREATIVE_SPINE_SCENE_FAMILIES)
        for family_name, markers in candidate_scene_hits.items():
            if family_name in allowed_scene_hits:
                continue
            return f"模型响应改变了当前创作主线：引入冲突场景“{markers[0]}”。"
    return ""
_NARRATIVE_MARKER_GROUPS_EN = (
    ("story", "event", "begins", "opens", "then", "during"),
    ("because", "therefore", "forces", "interrupts", "breaks", "trigger"),
    ("respond", "answers", "chooses", "movement", "pauses", "turns"),
    ("emotion", "resolve", "alert", "hesitation", "unease", "relief"),
    ("environment", "space", "lighting", "reflection", "shadow", "material"),
    ("camera", "final frame", "last frame", "ending", "holds", "settles"),
)


def _requires_narrative_contract(settings: dict[str, Any]) -> bool:
    return bool(settings.get("全局剧情规划")) or bool(settings.get("全局叙事合同启用", False))


def _looks_like_narrative_prompt(text: str, settings: dict[str, Any]) -> bool:
    if not _requires_narrative_contract(settings):
        return True
    body = str(text or "").split("中文说明：", 1)[0].strip()
    if not body:
        return False
    if _CJK_PATTERN.search(body):
        hits = sum(any(marker in body for marker in group) for group in _NARRATIVE_MARKER_GROUPS_ZH)
        compact_length = len(re.sub(r"\s+", "", body))
        return hits >= 5 and 800 <= compact_length <= 1200
    lowered = body.casefold()
    hits = sum(any(marker in lowered for marker in group) for group in _NARRATIVE_MARKER_GROUPS_EN)
    return hits >= 5 and len(_ENGLISH_WORD_PATTERN.findall(body)) >= 150


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
        return "Language requirement: output every final prompt body in English only, 420-560 words per item, with no Chinese characters.\n"
    if language == "英文提示词+中文说明":
        return "Language requirement: each item outputs an English prompt body first, 420-560 words per item, then one short Chinese note beginning with 中文说明： before the separator.\n"
    if language == "纯中文":
        return "语言要求：每条成品提示词正文必须使用中文，不要改成英文提示词；每条必须为 800-1200 字自然语言。\n"
    return ""


def _refiner_token_limit(settings: dict[str, Any], *, prompt_count: int = 1) -> int:
    try:
        requested = int(settings.get("最大生成token", 1800) or 1800)
    except Exception:
        requested = 1800
    count = max(1, int(prompt_count or 1))
    per_prompt = max(128, min(8192, requested))
    return min(8192, per_prompt * count)


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
    model_source = _normalize_model_source_label(settings.get("模型来源", "仅Skill"))
    model_source_effective = _normalize_model_source_label(settings.get("模型来源实际", model_source) or model_source)
    model_fallback_note = str(settings.get("模型回退说明", "") or "").strip()
    post_context = str(settings.get("模型后置素材摘要", "") or "").strip()
    nsfw_context = str(settings.get("NSFW工作台标签摘要", "") or "").strip()
    tag_block_context = str(settings.get("标签块编排摘要", "") or "").strip()
    danbooru_context = str(settings.get("Danbooru通用视觉标签摘要", "") or "").strip()
    creative_spine_context = str(settings.get("全局创作主线摘要", "") or "").strip()
    if not creative_spine_context:
        creative_spine_context = summarize_global_creative_spine_contract(settings.get("全局创作主线合同"))
    dynamic_strategy = str(settings.get("Skill动态变化策略", "") or "").strip()
    narrative_plans = [
        str(item).strip()
        for item in settings.get("全局剧情规划", [])
        if str(item).strip()
    ]
    diversity_markers = [
        str(marker).strip()
        for marker in [
            *list(settings.get("随机主题池档案标记", []) or []),
            *list(settings.get("模板风格档案标记", []) or []),
            *list(settings.get("运行时随机档案标记", []) or []),
        ]
        if str(marker).strip()
    ]
    recent_prompt_fingerprints = [
        str(item).strip()
        for item in list(settings.get("最近提示词指纹", []) or [])
        if str(item).strip()
    ]
    active_modes: list[str] = []
    if bool(settings.get("运行时随机标签", False)):
        active_modes.append("运行时随机")
    if bool(settings.get("智能文本匹配", False)):
        active_modes.append("智能文本")
    if bool(settings.get("标签块编排启用", False)):
        active_modes.append("标签块编排")
    if str(settings.get("角色设定图内部策略", "") or "").strip():
        active_modes.append("角色设定图")
    image_reverse_status = str(settings.get("图片反推状态", "") or "").strip()
    if bool(settings.get("图片反推生成", False)) or image_reverse_status not in {"", "未启用"}:
        active_modes.append("图片反推")
    if bool(settings.get("NSFW工作台启用", False)) or bool(settings.get("NSFW策略启用", False)):
        active_modes.append("NSFW工作台")
    if not active_modes:
        active_modes.append("常规标签与模板")

    layout_mode = resolve_visual_layout_mode(settings=settings)
    layout_policy = visual_layout_contract(
        layout_mode,
        english=str(settings.get("提示词语言", "纯中文") or "纯中文").strip() in {"纯英文", "英文提示词+中文说明"},
    )

    extra_lines = [
        f"当前激活模式：{'、'.join(dict.fromkeys(active_modes))}。",
        f"当前画面结构：{layout_mode}；硬约束：{layout_policy}",
        (
            "模式合并优先级：用户显式输入与锁定标签 > 角色设定图或图片反推的可见事实 > "
            "标签块顺序与锁定块 > NSFW 保护锚点 > 运行时随机、主题池和模板档案 > 模型补充细节。"
            "高优先级已经确定的内容不得被低优先级模式覆盖；未明确的维度才允许扩写。"
        ),
    ]
    if post_context:
        extra_lines.append(f"当前激活素材摘要：{post_context}")
    if nsfw_context:
        extra_lines.append(f"NSFW 工作台素材：{nsfw_context}")
    if tag_block_context:
        extra_lines.append(f"标签块编排顺序：{tag_block_context}")
    if danbooru_context:
        extra_lines.append(
            "Danbooru通用视觉词：" + danbooru_context
            + "。这些词只描述画面结构与视觉属性，润色时必须保留其具体镜头、构图、光影或媒介含义。"
        )
    if creative_spine_context:
        extra_lines.append(
            "本次全局创作主线：" + creative_spine_context
            + "。这是所有生成渠道共用的已解析合同；只能补全未指定细节，不得另起媒介、场景、服装或动作主线。"
        )
    if dynamic_strategy:
        extra_lines.append(f"Skill动态变化策略：{dynamic_strategy}")
    if narrative_plans:
        extra_lines.append(
            "本次全局剧情规划：" + " | ".join(narrative_plans[:20])
            + "。必须保留每条规划中的事件、情绪转折、空间动线与结尾状态，但要把它们写成自然正文，不能复述规划字段名。"
        )
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
    if str(settings.get("模型任务", "") or "").strip() == "视频提示词":
        anchors = [str(item).strip() for item in settings.get("视频提示词必保留锚点", []) if str(item).strip()]
        anchor_text = "、".join(dict.fromkeys(anchors)) or "无额外锚点"
        spine = str(settings.get("全局创作主线摘要", "") or "").strip() or "按视频 Skill 底稿为准"
        return (
            "视频 Skill 已先生成一条可直接使用的单镜头底稿。你只能在这条底稿内部润色，不能另起主线。\n"
            f"必须原样保留的主体、场景、动作等锚点：{anchor_text}\n"
            f"全局创作主线摘要：{spine}\n"
            "请把底稿写成自然、连贯、按时间顺序发生的可拍摄正文；变化必须有原因，不能增加人物、地点或第二个镜头。\n"
            "只输出最终正文，不输出分析、标题、列表或 Markdown。\n\n"
            f"视频 Skill 底稿：\n{str(prompt or '').strip()}"
        )
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
    narrative_plans = [str(item).strip() for item in settings.get("全局剧情规划", []) if str(item).strip()]
    for index, prompt in enumerate(prompts, start=1):
        signature = _prompt_signature(prompt)
        narrative_plan = narrative_plans[index - 1] if index - 1 < len(narrative_plans) else "沿本条正文提炼独立事件"
        diversity_lines.append(
            f"第{index}条差异锚点：{signature or '按该条输入自行提炼'}。"
            f"第{index}条剧情规划：{narrative_plan}。"
            "输出时围绕本条锚点与剧情规划重组主体、场景、服装、动作目的、环境响应、镜头时机、光影和色彩，并至少保留四个叙事维度与其他条不同，不要复制其他条的主线。"
        )
    return (
        _skill_context_for_model(settings)
        + "\\n\\n"
        + _batch_language_instruction(settings)
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


_COMMON_MODEL_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:bearer|token|basic)\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{8,}"),
    re.compile(r"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{16,}"),
    re.compile(r"\bhf_[A-Za-z0-9]{16,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{12,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
)
_MODEL_SECRET_LABEL_PATTERN = re.compile(
    r"(?i)(\b(?:authorization|proxy-authorization|api[-_ ]?key|x-api-key|x-goog-api-key|"
    r"access[-_ ]?token|auth[-_ ]?token)\b\s*[:=]\s*)([^,;\r\n}\]]+)"
)
_MODEL_SECRET_QUERY_PATTERN = re.compile(
    r"(?i)([?&](?:key|api[-_]?key|token|access[-_]?token|auth[-_]?token)=)([^&#\s]+)"
)


def _nonempty_secret_scalars(raw: Any) -> list[str]:
    if isinstance(raw, dict):
        values: list[str] = []
        for value in raw.values():
            values.extend(_nonempty_secret_scalars(value))
        return values
    if isinstance(raw, (list, tuple, set)):
        values = []
        for value in raw:
            values.extend(_nonempty_secret_scalars(value))
        return values
    text = str(raw or "").strip()
    return [text] if text else []


def _extra_header_secret_values(raw: Any) -> list[str]:
    if isinstance(raw, (dict, list, tuple, set)):
        return _nonempty_secret_scalars(raw)
    text = str(raw or "").strip()
    if not text:
        return []
    if text[:1] in {"{", "["}:
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, (dict, list)):
            return _nonempty_secret_scalars(parsed)
    values: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if ":" not in line:
            continue
        value = line.split(":", 1)[1].strip()
        if value:
            values.append(value)
    return values


def _model_secret_candidates(settings: dict[str, Any] | None) -> list[str]:
    if not isinstance(settings, dict):
        return []
    candidates: list[str] = []
    for key in ("_API密钥脱敏值", "API密钥解析值", "API密钥已解析", "api_key"):
        candidates.extend(_nonempty_secret_scalars(settings.get(key)))
    raw_api_key = str(settings.get("API密钥", "") or "").strip()
    if raw_api_key.lower().startswith("env:"):
        env_name = raw_api_key[4:].strip()
        if env_name:
            candidates.extend(_nonempty_secret_scalars(os.getenv(env_name, "")))
    elif raw_api_key:
        candidates.append(raw_api_key)
    for key in ("API额外请求头", "API额外请求头解析值", "extra_headers"):
        candidates.extend(_extra_header_secret_values(settings.get(key)))

    expanded: list[str] = []
    for value in candidates:
        secret = str(value or "").strip().strip('"\'')
        if not secret:
            continue
        expanded.append(secret)
        prefix_match = re.match(r"(?i)^(?:bearer|token|basic)\s+(.+)$", secret)
        if prefix_match and prefix_match.group(1).strip():
            expanded.append(prefix_match.group(1).strip())
    return sorted(set(expanded), key=len, reverse=True)


def sanitize_model_error(raw: Any, settings: dict[str, Any] | None = None) -> str:
    """Return a bounded model error string with configured credentials removed."""

    text = str(raw or "").strip() or "未知错误"
    for secret in _model_secret_candidates(settings):
        text = text.replace(secret, "[REDACTED]")
    for pattern in _COMMON_MODEL_SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    text = _MODEL_SECRET_QUERY_PATTERN.sub(r"\1[REDACTED]", text)
    text = _MODEL_SECRET_LABEL_PATTERN.sub(r"\1[REDACTED]", text)
    text = re.sub(r"\s+", " ", text).strip() or "未知错误"
    return text if len(text) <= 240 else f"{text[:237]}..."


def _safe_model_call_reason(raw: Any, settings: dict[str, Any] | None = None) -> str:
    return sanitize_model_error(raw, settings)


def _append_model_runtime_note(settings: dict[str, Any], note: str) -> None:
    text = str(note or "").strip()
    if not text:
        return
    current = settings.get("推理纠偏说明", [])
    if isinstance(current, (list, tuple, set)):
        notes = [str(item).strip() for item in current if str(item).strip()]
    else:
        notes = [line.strip() for line in str(current or "").splitlines() if line.strip()]
    if text not in notes:
        notes.append(text)
    settings["推理纠偏说明"] = notes


def _runtime_base_source(settings: dict[str, Any]) -> str:
    return _normalize_model_source_label(
        settings.get("模型调用基础来源")
        or settings.get("模型来源")
        or settings.get("模型来源实际")
        or "仅Skill"
    )


def _refresh_model_runtime_status(settings: dict[str, Any]) -> None:
    success_count = max(0, int(settings.get("模型调用成功次数", 0) or 0))
    failure_count = max(0, int(settings.get("模型调用失败次数", 0) or 0))
    adopted_count = max(0, int(settings.get("模型调用采纳次数", 0) or 0))
    active_fallback_count = max(0, int(settings.get("模型活动回退数量", 0) or 0))
    settings["模型调用尝试次数"] = success_count + failure_count
    base_source = _runtime_base_source(settings)

    if active_fallback_count:
        if success_count:
            if adopted_count:
                settings["模型调用状态"] = (
                    f"部分采用：{success_count} 次成功，{failure_count} 次失败；"
                    f"最终仍有 {active_fallback_count} 条回退 Skill，采纳 {adopted_count} 次"
                )
            else:
                settings["模型调用状态"] = (
                    f"调用成功但输出未采用：{success_count} 次；"
                    f"最终仍有 {active_fallback_count} 条回退 Skill"
                )
        else:
            settings["模型调用状态"] = (
                f"调用失败：{failure_count} 次；最终仍有 {active_fallback_count} 条回退 Skill"
            )
        settings["模型来源实际"] = f"{base_source}（部分回退）" if adopted_count else "仅Skill回退"
        return
    settings["模型回退说明"] = ""
    if success_count:
        if failure_count:
            settings["模型调用状态"] = (
                f"调用已恢复：{success_count} 次成功，{failure_count} 次失败；"
                f"最终无输出回退，采纳 {adopted_count} 次"
            )
        else:
            settings["模型调用状态"] = (
                f"调用成功：{success_count} 次，采纳 {adopted_count} 次"
                if adopted_count
                else f"调用成功：{success_count} 次，结果未产生有效变化"
            )
        settings["模型来源实际"] = base_source
    else:
        settings["模型调用状态"] = f"调用失败：{failure_count} 次，已回退 Skill"
        settings["模型来源实际"] = "仅Skill回退"


def _merge_fallback_note(settings: dict[str, Any], note: str) -> None:
    text = str(note or "").strip()
    if not text:
        return
    previous = str(settings.get("模型回退说明", "") or "").strip()
    if previous:
        text = previous if text in previous else f"{previous}；{text}"
    settings["模型回退说明"] = text[-720:]
    _append_model_runtime_note(settings, note)


def _record_model_call_result(
    settings: dict[str, Any],
    *,
    outcome: str,
    changed: bool = False,
    adopted_outputs: int | None = None,
    fallback_outputs: int = 0,
    output_count: int = 1,
    reason: Any = "",
    report_fallback: bool = True,
) -> None:
    result = str(outcome or "failure").strip().lower()
    succeeded = result in {"success", "partial"}
    success_count = max(0, int(settings.get("模型调用成功次数", 0) or 0))
    failure_count = max(0, int(settings.get("模型调用失败次数", 0) or 0))
    if succeeded:
        success_count += 1
    else:
        failure_count += 1
    settings["模型调用成功次数"] = success_count
    settings["模型调用失败次数"] = failure_count

    adopted_increment = max(0, int(adopted_outputs if adopted_outputs is not None else (1 if changed else 0)))
    settings["模型调用采纳次数"] = max(0, int(settings.get("模型调用采纳次数", 0) or 0)) + adopted_increment
    total_outputs = max(1, int(output_count or 1))
    fallback_output_count = max(0, min(int(fallback_outputs or 0), total_outputs))
    if not succeeded and fallback_output_count == 0:
        fallback_output_count = 1

    if not succeeded or fallback_output_count:
        safe_reason = _safe_model_call_reason(reason, settings)
        errors = [
            _safe_model_call_reason(item, settings)
            for item in settings.get("模型调用错误", [])
            if str(item).strip()
        ]
        if safe_reason not in errors:
            errors.append(safe_reason)
        settings["模型调用错误"] = errors[-4:]
        if report_fallback:
            settings["模型活动回退数量"] = max(0, int(settings.get("模型活动回退数量", 0) or 0)) + fallback_output_count
            configured_source = _normalize_model_source_label(settings.get("模型来源", "仅Skill"))
            if fallback_outputs:
                fallback_note = (
                    f"模型输出回退：{configured_source} 返回结果中有 {fallback_output_count}/{total_outputs} 条"
                    f"未通过校验，已保留对应 Skill 结果；原因：{safe_reason}"
                )
            else:
                fallback_note = (
                    f"模型调用回退：{configured_source} 请求或响应处理失败，当前对应输出保留 Skill 结果；"
                    f"原因：{safe_reason}"
                )
            _merge_fallback_note(settings, fallback_note)
    _refresh_model_runtime_status(settings)


def reconcile_model_output_fallback(
    settings: dict[str, Any],
    *,
    fallback_outputs: int,
    output_count: int,
    reason: Any,
    adopted_outputs_to_revert: int | None = None,
) -> None:
    total = max(1, int(output_count or 1))
    fallback = max(0, min(int(fallback_outputs or 0), total))
    if fallback <= 0:
        return
    adopted_revert = fallback if adopted_outputs_to_revert is None else max(
        0,
        min(int(adopted_outputs_to_revert or 0), fallback),
    )
    settings["模型调用采纳次数"] = max(
        0,
        int(settings.get("模型调用采纳次数", 0) or 0) - adopted_revert,
    )
    settings["模型活动回退数量"] = max(0, int(settings.get("模型活动回退数量", 0) or 0)) + fallback
    safe_reason = _safe_model_call_reason(reason, settings)
    note = f"模型最终结果回退：后处理有 {fallback}/{total} 条未采用模型候选，已恢复 Skill 结果；原因：{safe_reason}"
    _merge_fallback_note(settings, note)
    _refresh_model_runtime_status(settings)


def _finalize_batch_retry_status(
    settings: dict[str, Any],
    *,
    output_count: int,
    adopted_outputs: int,
    fallback_outputs: int,
    reason: Any,
    baseline_fallback_count: int = 0,
    baseline_fallback_note: str = "",
) -> None:
    total = max(1, int(output_count or 1))
    fallback = max(0, min(int(fallback_outputs or 0), total))
    baseline = max(0, int(baseline_fallback_count or 0))
    settings["模型活动回退数量"] = baseline + fallback
    settings["模型回退说明"] = str(baseline_fallback_note or "").strip()
    if fallback:
        safe_reason = _safe_model_call_reason(reason, settings)
        note = f"批量重试后仍有 {fallback}/{total} 条模型输出不可用，已保留对应 Skill 结果；原因：{safe_reason}"
        _merge_fallback_note(settings, note)
    elif baseline == 0:
        settings["模型回退说明"] = ""
        _append_model_runtime_note(settings, "批量响应格式异常，但逐条重试已恢复，最终无输出回退。")
    _refresh_model_runtime_status(settings)


_MODEL_TEXT_METHOD_NAMES = (
    "create_chat_completion",
    "invoke",
    "generate_content",
    "complete",
    "predict",
    "chat",
)


def _supports_model_text_call(candidate: Any) -> bool:
    if candidate is None:
        return False
    for name in _MODEL_TEXT_METHOD_NAMES:
        try:
            if callable(getattr(candidate, name, None)):
                return True
        except Exception:
            continue
    return callable(candidate) and not isinstance(candidate, (str, bytes, dict, list, tuple, set))


def _resolve_model_backend(model: Any) -> Any:
    """Unwrap common ComfyUI, LangChain and local-pipeline model containers."""

    queue = [model]
    seen: set[int] = set()
    fallback = model
    while queue:
        candidate = queue.pop(0)
        if candidate is None or id(candidate) in seen:
            continue
        seen.add(id(candidate))
        fallback = candidate
        if _supports_model_text_call(candidate):
            return candidate
        if isinstance(candidate, dict):
            queue.extend(candidate.get(key) for key in ("llm", "model", "client", "pipeline", "generator") if key in candidate)
            continue
        if isinstance(candidate, (list, tuple)):
            queue.extend(candidate[:8])
            continue
        for attribute in ("llm", "model", "client", "pipeline", "generator"):
            try:
                nested = getattr(candidate, attribute, None)
            except Exception:
                nested = None
            if nested is not None and nested is not candidate:
                queue.append(nested)
    return fallback


def _call_flexible_model_method(method: Callable[..., Any], *, prompt: str, messages: list[dict[str, str]]) -> Any:
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        signature = None
    parameters = signature.parameters if signature is not None else {}
    if "messages" in parameters:
        return method(messages=messages)
    return method(prompt)


def _call_model_text(
    llm: Any,
    prompt: str,
    settings: dict[str, Any],
    *,
    chat_completion: Callable[..., Any],
    clean_think_text: Callable[[str], str],
    prompt_count: int = 1,
) -> str:
    llm = _resolve_model_backend(llm)
    system_prompt = _resolve_system_prompt(settings)
    user_prompt = _compose_model_user_prompt(prompt, settings)
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    combined_prompt = f"{system_prompt}\n\n{user_prompt}".strip()
    if callable(getattr(llm, "create_chat_completion", None)):
        response = chat_completion(
            llm,
            messages=messages,
            params=_refiner_sampling_params(settings, prompt_count=prompt_count),
        )
        text = str(extract_text(response) or "").strip()
        if not text:
            raise RuntimeError("模型 API 返回空文本。")
        return clean_think_text(text)
    if callable(getattr(llm, "invoke", None)):
        response = llm.invoke(combined_prompt)
        text = str(extract_text(response) or "").strip()
        if not text:
            raise RuntimeError("模型返回空文本。")
        return clean_think_text(text)
    if callable(getattr(llm, "generate_content", None)):
        response = llm.generate_content(combined_prompt)
        text = str(extract_text(response) or "").strip()
        if not text:
            raise RuntimeError("模型返回空文本。")
        return clean_think_text(text)
    for method_name in ("complete", "predict", "chat"):
        method = getattr(llm, method_name, None)
        if not callable(method):
            continue
        response = _call_flexible_model_method(method, prompt=combined_prompt, messages=messages)
        text = str(extract_text(response) or "").strip()
        if not text:
            raise RuntimeError(f"模型 {method_name} 返回空文本。")
        return clean_think_text(text)
    if callable(llm):
        response = llm(combined_prompt)
        text = str(extract_text(response) or "").strip()
        if not text:
            raise RuntimeError("可调用模型返回空文本。")
        return clean_think_text(text)
    raise RuntimeError(
        "当前模型对象不支持 create_chat_completion、invoke、generate_content、complete、predict、chat 或可调用文本接口。"
    )


_TRANSIENT_MODEL_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
_TRANSIENT_MODEL_ERROR_MARKERS = (
    "timed out",
    "timeout",
    "read operation timed out",
    "读取超过总时限",
    "连接超时",
    "connection reset",
    "connection aborted",
    "connection refused",
    "temporarily unavailable",
    "temporary failure",
    "server disconnected",
    "remote end closed",
    "incomplete read",
    "eof occurred",
    "rate limit",
    "too many requests",
)


def _is_transient_model_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    status = getattr(exc, "status", None)
    if status is None:
        status = getattr(exc, "code", None)
    try:
        if int(status) in _TRANSIENT_MODEL_STATUS_CODES:
            return True
        if 400 <= int(status) < 500:
            return False
    except (TypeError, ValueError):
        pass
    reason = getattr(exc, "reason", None)
    if isinstance(reason, (TimeoutError, ConnectionError)):
        return True
    text = f"{type(exc).__name__}: {exc}".casefold()
    return any(marker in text for marker in _TRANSIENT_MODEL_ERROR_MARKERS)


def _call_model_text_with_retry(
    llm: Any,
    prompt: str,
    settings: dict[str, Any],
    *,
    chat_completion: Callable[..., Any],
    clean_think_text: Callable[[str], str],
    prompt_count: int,
) -> str:
    retry_limit = _safe_int_setting(settings, "模型瞬时重试次数", 1, 0, 2)
    retry_index = 0
    while True:
        try:
            text = _call_model_text(
                llm,
                prompt,
                settings,
                chat_completion=chat_completion,
                clean_think_text=clean_think_text,
                prompt_count=prompt_count,
            )
            if retry_index:
                _append_model_runtime_note(
                    settings,
                    f"模型传输瞬时失败后第 {retry_index + 1} 次请求已恢复，最终未因该错误回退 Skill。",
                )
            return text
        except Exception as exc:
            if retry_index >= retry_limit or not _is_transient_model_error(exc):
                raise
            retry_index += 1
            settings["模型传输重试次数"] = max(
                0,
                int(settings.get("模型传输重试次数", 0) or 0),
            ) + 1
            settings["模型最近瞬时错误"] = _safe_model_call_reason(exc, settings)
            time.sleep(min(0.35, 0.12 * (2 ** (retry_index - 1))))


def maybe_model_refine(
    model: Any,
    prompt: str,
    settings: dict[str, Any],
    *,
    chat_completion: Callable[..., Any],
    clean_think_text: Callable[[str], str],
) -> str:
    llm = _resolve_model_backend(model)
    if llm is None:
        return prompt
    try:
        raw_text = _call_model_text_with_retry(
            llm,
            prompt,
            settings,
            chat_completion=chat_completion,
            clean_think_text=clean_think_text,
            prompt_count=1,
        )
    except Exception as exc:
        _record_model_call_result(settings, outcome="failure", reason=exc)
        return prompt
    resolved, mode, reason = _resolve_model_prompt_candidate(prompt, raw_text, settings)
    if mode == "rejected":
        _record_model_call_result(
            settings,
            outcome="partial",
            fallback_outputs=1,
            output_count=1,
            reason=reason,
        )
        return prompt
    if mode == "cleaned":
        _append_model_runtime_note(settings, "模型响应中的思考、分析或包装字段已清洗，仅采用最终提示词正文。")
    elif mode == "blended":
        _append_model_runtime_note(settings, "模型返回了可用短草稿，已融入 Skill 的 800-1200 字剧情骨架，未触发输出回退。")
    _record_model_call_result(settings, outcome="success", changed=resolved != str(prompt or "").strip())
    return resolved


def maybe_model_refine_video(
    model: Any,
    prompt: str,
    settings: dict[str, Any],
    *,
    chat_completion: Callable[..., Any],
    clean_think_text: Callable[[str], str],
    validator: Callable[..., bool],
) -> str:
    """Use the configured local/API model to polish a video Skill result conservatively."""

    original = str(prompt or "").strip()
    llm = _resolve_model_backend(model)
    if llm is None or not original:
        return original
    video_settings = dict(settings)
    video_settings["模型任务"] = "视频提示词"
    try:
        raw_text = _call_model_text_with_retry(
            llm,
            original,
            video_settings,
            chat_completion=chat_completion,
            clean_think_text=clean_think_text,
            prompt_count=1,
        )
    except Exception as exc:
        _record_model_call_result(video_settings, outcome="failure", reason=exc)
        settings.update({key: value for key, value in video_settings.items() if key.startswith("模型") or key == "推理纠偏说明"})
        return original

    prepared, recovered = _prepare_model_response_text(raw_text)
    candidate = _postprocess_prompt_text(prepared)
    language = str(settings.get("提示词语言", "纯中文") or "纯中文")
    anchors = [str(item).strip() for item in settings.get("视频提示词必保留锚点", []) if str(item).strip()]
    missing = [anchor for anchor in anchors if anchor not in candidate]
    if (
        not candidate
        or _looks_like_broken_prompt(candidate)
        or missing
        or not bool(validator(candidate, language=language))
    ):
        reason = "视频模型候选未通过 800-1200 字、自然语言、单镜头或锚点校验。"
        if missing:
            reason += f" 缺少锚点：{'、'.join(missing[:3])}。"
        _record_model_call_result(
            video_settings,
            outcome="partial",
            fallback_outputs=1,
            output_count=1,
            reason=reason,
        )
        settings.update({key: value for key, value in video_settings.items() if key.startswith("模型") or key == "推理纠偏说明"})
        return original
    if recovered:
        _append_model_runtime_note(video_settings, "视频模型响应中的思考或包装字段已清洗，仅采用最终正文。")
    _record_model_call_result(
        video_settings,
        outcome="success",
        changed=candidate != original,
        adopted_outputs=1 if candidate != original else 0,
    )
    settings.update({key: value for key, value in video_settings.items() if key.startswith("模型") or key == "推理纠偏说明"})
    return candidate


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

    llm = _resolve_model_backend(model)
    if llm is None:
        return list(clean_prompts)

    batch_prompt = _compose_batch_prompt(clean_prompts, settings)
    try:
        raw_text = _call_model_text_with_retry(
            llm,
            batch_prompt,
            settings,
            chat_completion=chat_completion,
            clean_think_text=clean_think_text,
            prompt_count=len(clean_prompts),
        )
    except Exception as exc:
        _record_model_call_result(
            settings,
            outcome="failure",
            fallback_outputs=len(clean_prompts),
            output_count=len(clean_prompts),
            reason=exc,
        )
        return list(clean_prompts)

    parts = [part.strip() for part in str(raw_text).split(_BATCH_SEPARATOR)]
    if len(parts) != len(clean_prompts):
        separator_reason = f"批量响应分隔数量不匹配：需要 {len(clean_prompts)} 条，实际解析到 {len(parts)} 条。"
        baseline_fallback_count = max(0, int(settings.get("模型活动回退数量", 0) or 0))
        baseline_fallback_note = str(settings.get("模型回退说明", "") or "").strip()
        _record_model_call_result(
            settings,
            outcome="failure",
            fallback_outputs=len(clean_prompts),
            output_count=len(clean_prompts),
            reason=separator_reason,
            report_fallback=len(clean_prompts) > 8,
        )
        if len(clean_prompts) <= 8:
            retry_results: list[str] = []
            retry_fallback_count = 0
            for prompt in clean_prompts:
                failure_count_before = max(0, int(settings.get("模型调用失败次数", 0) or 0))
                result = maybe_model_refine(
                    model,
                    prompt,
                    settings,
                    chat_completion=chat_completion,
                    clean_think_text=clean_think_text,
                )
                retry_results.append(result)
                failure_count_after = max(0, int(settings.get("模型调用失败次数", 0) or 0))
                if failure_count_after > failure_count_before:
                    retry_fallback_count += 1
            adopted_count = sum(
                candidate != original
                for candidate, original in zip(retry_results, clean_prompts)
            )
            _finalize_batch_retry_status(
                settings,
                output_count=len(clean_prompts),
                adopted_outputs=adopted_count,
                fallback_outputs=retry_fallback_count,
                reason=(
                    separator_reason
                    if retry_fallback_count == 0
                    else f"批量响应分隔错误后逐条重试，仍有 {retry_fallback_count} 条未通过调用或输出校验。"
                ),
                baseline_fallback_count=baseline_fallback_count,
                baseline_fallback_note=baseline_fallback_note,
            )
            return retry_results
        return list(clean_prompts)

    resolved: list[str] = []
    seen_keys: set[str] = set()
    rejected_count = 0
    rejection_reasons: list[str] = []
    resolution_modes: set[str] = set()
    for original_prompt, part in zip(clean_prompts, parts):
        candidate, mode, reason = _resolve_model_prompt_candidate(original_prompt, part, settings)
        if mode == "rejected":
            resolved.append(original_prompt)
            seen_keys.add(_normalize_for_compare(original_prompt))
            rejected_count += 1
            if reason and reason not in rejection_reasons:
                rejection_reasons.append(reason)
            continue
        resolution_modes.add(mode)
        rejected = False
        candidate_key = _normalize_for_compare(candidate)
        if candidate_key in seen_keys:
            candidate = original_prompt
            candidate_key = _normalize_for_compare(candidate)
            rejected = True
            if "模型批量响应与前一条重复，未采用重复候选。" not in rejection_reasons:
                rejection_reasons.append("模型批量响应与前一条重复，未采用重复候选。")
        resolved.append(candidate)
        seen_keys.add(candidate_key)
        if rejected:
            rejected_count += 1
    if "cleaned" in resolution_modes:
        _append_model_runtime_note(settings, "批量模型响应中的思考、分析或包装字段已清洗，仅采用最终提示词正文。")
    if "blended" in resolution_modes:
        _append_model_runtime_note(settings, "批量模型短草稿已分别融入 Skill 的 800-1200 字剧情骨架，未将可用草稿误判为调用失败。")
    changed = any(candidate != original for candidate, original in zip(resolved, clean_prompts))
    if rejected_count:
        _record_model_call_result(
            settings,
            outcome="partial",
            changed=changed,
            adopted_outputs=sum(candidate != original for candidate, original in zip(resolved, clean_prompts)),
            fallback_outputs=rejected_count,
            output_count=len(clean_prompts),
            reason=(
                f"批量响应有 {rejected_count} 条未通过正文、语言、主体或重复校验。"
                + (f" {'；'.join(rejection_reasons[:2])}" if rejection_reasons else "")
            ),
        )
    else:
        _record_model_call_result(
            settings,
            outcome="success",
            changed=changed,
            adopted_outputs=len(clean_prompts),
            output_count=len(clean_prompts),
        )
    return resolved
