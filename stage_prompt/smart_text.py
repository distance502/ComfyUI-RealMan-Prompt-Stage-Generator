# -*- coding: utf-8 -*-
"""Smart text matching helpers for stage prompt generation."""

from __future__ import annotations

from collections import OrderedDict
import re
from typing import Any, Callable

try:
    from .skills import resolve_base_template_style
except ImportError:  # Standalone module tests load skills under this compatibility name.
    from stage_prompt_skills_test import resolve_base_template_style  # type: ignore

try:
    from .narrative import GLOBAL_NARRATIVE_MODEL_CONTRACT
except Exception:  # pragma: no cover - standalone module tests
    from stage_prompt_narrative_test import GLOBAL_NARRATIVE_MODEL_CONTRACT  # type: ignore


SMART_TEXT_SYSTEM_TEMPLATE = """
你是 Qwen TE 节点内置的 Smart Prompt Skill。任务：把用户描述、节点标签和 NSFW 成熟写真工作台标签压成一段可直接出图的正向提示词。

输出方式：先明确此刻正在发生的事件和主体动机，再让服装、场景、动作、环境反馈、光影镜头、材质与画质围绕事件自然展开。
核心规则：
1. 先判断画面主线，只选最有用的元素；冲突标签只保留一个方向。
2. 写成自然连贯的摄影/美术 brief，不要标签清单，不要逐项罗列，不要照抄节点标签原文。
3. 中文输出建议 700-1100 字；英文输出建议 360-600 words；中英模式先输出英文提示词，再用一小段中文说明总结视觉方向。内容必须精细，但不要用近义词反复堆叠凑字数。
4. 成人成熟模式只表达明确成年主体、成熟写真氛围、服装与光影；若出现女孩/少女/校园语义，改写为年轻成年女性、青春感成年女性、学院风穿搭或大学场景。
5. 优先吸收已匹配入槽位的成熟标签，把它们融合成句子，不要一条一条列出来。
6. 默认使用全景全身或完整人物入镜；只有用户明确写近景、特写、半身、头像时，才切换到对应景别。
7. 不要把风格、景别、场景或主体写死；用户输入与已选标签优先，默认项只是兜底。
8. 每个维度只保留一条主方向：一种主风格、一种主场景、一种主景别、一种主情绪、一组主光线；其余元素作为细节融入，不要重复叠加。
9. 只输出提示词正文；不要标题、解释、Markdown、分析过程、参数或“以下是为您优化”等话术。
10. 不要只输出“成年女性”“CG感”“真实感”这类单点结论；必须把主体、外观、服装、场景、动作、镜头、光线、材质和质量控制组织成完整画面。
11. 全局写法遵循“事件触发 → 主体回应 → 情绪转折 → 环境与光线反馈 → 镜头定格”：每个视觉细节都要服务同一条因果清楚的剧情。
12. 具体描述优先：把“好看、精致、高级、震撼”改成可见细节，例如雾气层次、侧逆光轮廓、胶片颗粒、丝绸褶皱、金属边缘高光、雨水反光、背景虚化程度。
13. 外部 MJ 参数或码图信息只作为灵感，不进入正文；丢弃 --ar、--profile、--stylize、--raw、--hd、--seed、UUID、preview、profile code 等非画面词。
14. 不要锁死素材库风格。古风电影、港式武侠、都市生活流、科幻机甲、东方赛博、商业广告、时尚编辑、神话史诗等只作为可选风格通道，必须跟随用户输入、节点标签、NSFW 工作台和随机主题池动态切换。
15. 中文模式必须输出自然中文正向提示词，不要混入英文系统说明；英文模式必须输出自然英文画面描述，不要出现“Create / Keep / Use / Finish”这类命令式教程句。
16. 如果当前上下文已经给出本次运行形成的主体、服装、场景、动作、光影或 NSFW 工作台主线，优先沿着这条主线扩写，不要退回成标签摘要或把多个主线硬拼成一条。
17. 允许吸收随机运行时的差异，但必须像同一张图里的统一拍摄方案，不要把多个风格、多个场景、多个镜头、多个动作并列堆叠。
18. 连续使用智能文本、随机运行时或 API 后置时，最近输出只作为避重参考，不是素材来源；至少变化主体身份、场景空间、服装材质、动作道具、光影色彩或镜头组织中的三个维度，不要复读上一轮画面骨架。

示例：
输入：书店女孩，霓虹夜色，面部聚焦
输出：杂志感人像，年轻成年女性站在书店玻璃窗前回望，全景全身构图，人物完整入镜，霓虹反光落在面部、发梢与书架玻璃边缘，姿态自然克制，服装线条干净，背景保持轻微虚化但能看出书店层次；画面以面部神情和完整身体比例为视觉中心，柔和高光勾出轮廓，整体干净、细腻、有电影感与封面感。
""".strip()
SMART_TEXT_SYSTEM_TEMPLATE = f"{SMART_TEXT_SYSTEM_TEMPLATE}\n\n{GLOBAL_NARRATIVE_MODEL_CONTRACT}"

_SMART_TEXT_WORD_SPLIT_PATTERN = re.compile(r"[\s,，、;；|/\\]+")
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_SMART_TEXT_ADULT_STRONG_MARKERS = (
    "nsfw",
    "成人向",
    "成人内容",
    "成人主题",
    "成人写真",
    "限制级",
    "情色",
    "色情",
    "性感",
    "内衣",
    "情趣",
    "裸体",
    "裸照",
    "全裸",
    "半裸",
    "私房写真",
    "自慰",
    "性爱",
    "性行为",
    "性暗示",
    "adult content",
    "adult-only",
    "explicit content",
    "explicit sexual",
    "erotic",
    "erotica",
    "lingerie",
    "nude",
    "nudity",
    "naked",
    "topless",
    "boudoir",
    "masturbation",
    "sexual content",
)
_SMART_TEXT_ADULT_EXPLICIT_TOKENS = {"成人", "adult", "nsfw", "18+"}
_SMART_TEXT_ADULT_WEAK_MARKER_GROUPS = (
    (
        "成年",
        "成年女性",
        "成年男性",
        "成熟女性",
        "成熟男性",
        "成熟",
        "女性",
        "女人",
        "男性",
        "男人",
        "adult woman",
        "adult man",
        "mature woman",
        "mature man",
    ),
    (
        "私房",
        "私密",
        "卧室",
        "酒店",
        "浴室",
        "浴缸",
        "淋浴",
        "蒸汽",
        "霓虹",
        "private room",
        "bedroom",
        "hotel room",
        "bathroom",
        "bathtub",
        "shower",
        "steam",
        "neon",
    ),
    (
        "睡袍",
        "湿发",
        "湿身",
        "吊带",
        "贴身",
        "暧昧",
        "妩媚",
        "欲感",
        "微醺",
        "曲线",
        "bathrobe",
        "wet hair",
        "wet body",
        "slip dress",
        "suggestive",
        "seductive",
        "intimate mood",
    ),
)
_SMART_TEXT_FULL_BODY_MARKERS = (
    "全身",
    "全景",
    "全景全身",
    "远景",
    "head to toe",
    "full body",
    "wide shot",
    "full-length",
)
_SMART_TEXT_WIDE_SHOT_TAGS = {"大全景", "大远景", "远景", "全景", "全景全身", "全身"}
_SMART_TEXT_MID_SHOT_CONFLICT_TAGS = {
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
_SMART_TEXT_ADULT_MALE_SUBJECT_TAGS = {"成年男性", "中年男性", "成熟男性"}
_SMART_TEXT_ADULT_FEMALE_SUBJECT_TAGS = {
    "成年女性",
    "中年女性",
    "成熟女性",
    "年轻成年女性",
    "青春感成年女性",
}
_SMART_TEXT_ADULT_MALE_MARKERS = ("成年男性", "中年男性", "成熟男性", "adult man", "mature man")
_SMART_TEXT_ADULT_FEMALE_MARKERS = ("成年女性", "中年女性", "成熟女性", "adult woman", "mature woman")
_FALLBACK_NOISE_TERMS = {
    "true",
    "false",
    "标准",
    "自动",
    "none",
    "null",
    "低保真",
    "高保真",
}
_SMART_TEXT_META_PATTERNS = (
    re.compile(r"^\s*(?:这是|以下是|下面是|为您|我将|我会|已为您|这里是).{0,40}?(?:提示词|正向提示词|prompt)\s*[（(]?.*?[）)]?\s*[:：,，]\s*", re.IGNORECASE),
    re.compile(r"^\s*(?:最终|优化后|整理后|成品|可直接使用的|适配主流AI绘画平台的)?\s*(?:正向)?提示词\s*[:：]\s*", re.IGNORECASE),
)
_SMART_TEXT_META_FRAGMENT_PATTERN = re.compile(
    r"(?:以下是|下面是|为您优化|已严格使用|适配主流AI绘画平台|最终正向提示词|正向提示词正文|不要输出|Markdown|参数)"
)
_SMART_TEXT_OUTLINE_MARKERS = (
    "主体身份",
    "关键外观",
    "主场景",
    "动作情绪",
    "光影镜头",
    "画质约束",
)
_SMART_TEXT_SUBJECT_ONLY_TERMS = {
    "人物主体",
    "女性",
    "成年女性",
    "年轻成年女性",
    "青春感成年女性",
    "男性",
    "成年男性",
    "中年女性",
    "中年男性",
}
_SMART_TEXT_CONTENT_MARKERS = (
    "摄影",
    "风格",
    "构图",
    "镜头",
    "场景",
    "背景",
    "光",
    "色调",
    "氛围",
    "姿态",
    "动作",
    "回眸",
    "俯身",
    "半身",
    "全身",
    "近景",
    "中景",
    "远景",
    "面部",
    "皮肤",
    "画面",
    "细节",
)
_SMART_TEXT_UNCERTAIN_MINOR_TERMS = ("女孩", "少女", "萝莉", "女学生", "校服", "校园")
_SMART_TEXT_ADULT_YOUTH_REPLACEMENTS = (
    ("书店女孩", "书店里的年轻成年女性"),
    ("女学生", "年轻成年女性"),
    ("一个女孩", "一位年轻成年女性"),
    ("女孩", "年轻成年女性"),
    ("少女感", "青春感成年女性"),
    ("少女", "青春感成年女性"),
    ("校服", "学院风穿搭"),
    ("校园", "大学校园"),
    ("教室", "大学教室"),
    ("课堂", "大学课堂"),
)
# Keep ordinary adult wording intact; only the separate high-risk guard below is filtered.
_SMART_TEXT_EXPLICIT_ACTION_REPLACEMENTS: dict[str, str] = {}
_SMART_TEXT_EXPLICIT_DROP_TERMS = ("未成年", "幼态", "萝莉", "强迫", "暴力羞辱")
_FALLBACK_STYLE_TERMS = {
    "自然写实图像",
    "真实感",
    "照片级",
    "杂志编辑风格",
    "杂志编辑摄影",
    "35mm胶片摄影",
    "大画幅棚拍",
    "港式武侠",
    "东方古风武侠",
    "都市电影人文",
    "时尚编辑商业广告",
    "高端时尚编辑肖像",
    "日韩影像",
    "日系电影感",
    "韩系极简影像",
    "生活流写实",
    "动漫",
    "国风美学",
    "水彩线稿",
    "水粉插画",
    "墨洗留白",
    "古风",
    "古风电影氛围",
    "港风惊悚志怪",
    "敦煌神性",
    "电影感",
    "CG感",
    "东方赛博机甲",
    "东方赛博武侠朋克",
    "西方奇幻史诗",
}
_FALLBACK_STYLE_LABELS = {
    "自然写实图像": "自然写实图像",
    "真实感": "写实摄影",
    "照片级": "照片级写实摄影",
    "杂志编辑风格": "杂志编辑风格",
    "杂志编辑摄影": "杂志编辑摄影",
    "35mm胶片摄影": "35mm胶片摄影",
    "大画幅棚拍": "大画幅棚拍",
    "港式武侠": "港式武侠电影感",
    "东方古风武侠": "东方古风武侠",
    "都市电影人文": "都市电影人文风格",
    "时尚编辑商业广告": "时尚编辑商业广告",
    "高端时尚编辑肖像": "高端时尚编辑肖像",
    "日韩影像": "日韩影像",
    "日系电影感": "日系电影感",
    "韩系极简影像": "韩系极简影像",
    "生活流写实": "生活流写实",
    "动漫": "高完成度动漫美术",
    "国风美学": "国风美学",
    "水彩线稿": "水彩线稿风格",
    "水粉插画": "水粉插画风格",
    "墨洗留白": "墨洗留白风格",
    "古风": "古风人像",
    "古风电影氛围": "古风电影氛围",
    "港风惊悚志怪": "港风惊悚志怪",
    "敦煌神性": "敦煌神性风格",
    "电影感": "电影感影像",
    "CG感": "电影级CG",
    "东方赛博机甲": "东方赛博机甲",
    "东方赛博武侠朋克": "东方赛博武侠朋克",
    "西方奇幻史诗": "西方奇幻史诗",
}
_FALLBACK_SUBJECT_TERMS = {
    "成年女性",
    "书店女孩",
    "影棚时尚女性",
    "居家游戏女孩",
    "湖畔金发女性",
    "女武士",
    "神女",
    "祭司",
    "魔女",
    "女冒险者",
    "神圣骑士",
    "冰霜骑士",
    "炎魔天使",
    "女孩",
    "傲娇",
    "温柔",
    "霸气",
    "少女",
    "丰满",
    "银白长发",
    "短发",
    "湿发",
}
_FALLBACK_SCENE_TERMS = {
    "书店",
    "地下通道",
    "月夜森林",
    "浴室",
    "浴缸",
    "海边",
    "雪地",
    "厨房",
    "卧室",
    "湖畔夕照",
    "幽暗竹林",
    "废弃地下老屋",
    "雨夜站台",
    "独立书店",
    "影棚纯色背景",
    "图书馆",
    "雨后街头",
    "霓虹街区",
    "工业废墟",
    "北欧海岸",
    "冰冻森林",
    "黑铁王座",
    "火山洞穴",
    "云端阶梯",
    "古建道场",
    "月下庭院",
    "神圣祭坛",
    "星海神殿",
    "悬空神庙",
}
_FALLBACK_LIGHT_TERMS = {
    "霓虹夜色",
    "光束尘埃",
    "柔光",
    "轮廓光",
    "逆光",
    "黄金时刻侧光",
    "阴天柔散光",
    "黑色电影硬光",
    "暖色轮廓逆光",
    "蓝灰月光",
    "高对比",
    "低饱和",
    "玫瑰粉调",
    "青橙色调（Teal and Orange）",
    "青橙色调",
    "红雾表现主义打光",
    "青蓝冷雾",
    "柔和光晕",
}
_FALLBACK_COMPOSITION_TERMS = {
    "近景",
    "面部聚焦",
    "镜头近距离",
    "中景半身构图",
    "中景半身",
    "半身",
    "全景全身",
    "人物完整入镜",
    "环境遮挡",
    "俯视平铺",
    "荷兰式倾斜",
    "过肩镜头",
    "微距特写",
    "200mm长焦压缩",
}
_FALLBACK_OUTFIT_TERMS = {
    "白色斗篷",
    "黑金重甲",
    "银白雕花重甲",
    "神官长袍",
    "鎏金头冠",
    "修身礼服",
    "机能外套",
    "长款大衣",
    "风衣",
    "奶油针织",
    "丝质睡袍",
    "吊带睡裙",
    "露背礼服",
    "白衬衫",
    "和服",
    "Lolita",
    "披风",
    "褙子",
    "诃子裙",
    "飞鱼服",
    "宽袖法袍",
    "劲装",
}
_FALLBACK_TRACK_DEFAULTS: dict[str, dict[str, list[str]]] = {
    "城市天台纪实": {
        "scene": ["城市天台"],
        "outfit": ["长款大衣"],
        "light": ["日落逆光"],
        "action": ["侧目看向远处"],
        "props": ["有线耳机"],
        "composition": ["侧脸构图", "负空间留白"],
    },
    "都市电影人文": {
        "scene": ["雨夜站台"],
        "outfit": ["长款大衣"],
        "light": ["阴天柔散光"],
        "action": ["回眸"],
        "props": ["相机"],
    },
    "时尚编辑商业广告": {
        "scene": ["极简白棚"],
        "outfit": ["修身礼服"],
        "light": ["高窗冷天光"],
        "action": ["看向镜头"],
        "props": ["手提包"],
    },
    "私房写实": {
        "scene": ["落地窗"],
        "outfit": ["丝质睡袍"],
        "light": ["柔和光晕"],
        "action": ["低头浅笑"],
        "props": ["酒杯"],
    },
    "插画叙事": {
        "scene": ["梦境"],
        "outfit": ["Lolita"],
        "light": ["高调粉彩"],
        "action": ["轻拈发梢"],
        "props": ["花束"],
    },
    "复古OVA": {
        "scene": ["霓虹小巷"],
        "outfit": ["和服"],
        "light": ["浮光"],
        "action": ["回眸"],
        "props": ["花束"],
    },
    "东方古风武侠": {
        "scene": ["竹林"],
        "outfit": ["劲装"],
        "light": ["暖色轮廓逆光"],
        "action": ["扶剑而立"],
        "props": ["剑"],
    },
    "国风暗黑志怪": {
        "scene": ["废弃地下老屋"],
        "outfit": ["宽袖法袍"],
        "light": ["冷雾惊悚侧光"],
        "action": ["低头凝视"],
        "props": ["神谕石碑"],
    },
    "东方赛博武侠朋克": {
        "scene": ["赛博街区"],
        "outfit": ["机能外套"],
        "light": ["全息投影光"],
        "action": ["持物待发"],
        "props": ["能量刀"],
    },
    "神殿史诗": {
        "scene": ["神殿"],
        "outfit": ["神官长袍"],
        "light": ["圣辉逆光"],
        "action": ["站姿挺拔"],
        "props": ["权杖"],
    },
    "山谷圣城史诗": {
        "scene": ["山谷圣城"],
        "outfit": [],
        "light": ["云隙光"],
        "action": [],
        "props": ["史诗城市中轴"],
        "composition": ["超广角全景", "中轴对称巨构"],
    },
    "工业树灵巨像": {
        "scene": ["工业舱室"],
        "outfit": [],
        "light": ["冷色工业顶光"],
        "action": [],
        "props": ["朽木树皮纹理", "苔藓附生质感"],
        "composition": ["巨物压迫近景", "低角度"],
    },
    "西方奇幻神话史诗": {
        "scene": ["北欧海岸"],
        "outfit": ["白色斗篷"],
        "light": ["蓝灰月光"],
        "action": ["扶剑而立"],
        "props": ["圣火"],
    },
}
_FALLBACK_ACTION_TERMS = {
    "持物待发",
    "站姿挺拔",
    "双手负后",
    "倚靠栏杆",
    "双人互动",
    "抬臂撑墙",
    "身体微微前倾俯身",
    "俯身",
}
_FALLBACK_PROP_TERMS = {
    "透明高跟凉鞋",
    "眼镜",
    "耳环",
    "项链",
    "手提包",
    "托特包",
    "斜挎包",
    "单肩包",
    "帽子",
    "围巾",
    "相机",
    "手机",
    "咖啡杯",
    "手持咖啡杯",
    "书本",
    "雨伞",
    "耳机",
    "能量刀",
    "面具",
    "武器",
    "全息界面",
    "日轮",
    "月轮",
    "圣火",
    "权杖",
}
_FALLBACK_QUALITY_TERMS = {
    "高细节",
    "材质细节丰富",
    "清晰对焦",
    "皮肤着色干净",
    "中画幅质感",
    "广告成片质感",
    "冷白皮",
    "脸部表情与妆发细节优先",
    "面部作为第一视觉中心",
    "面部与主体关系清晰",
    "时尚成片感更强",
    "人物视觉重心更偏封面肖像",
    "复古非镀膜镜头",
    "RGB轻微分离",
    "轻微色差",
    "柔和光晕",
    "老胶片褪色感",
    "港片胶片质感",
    "白色斗篷",
    "黑金重甲",
    "银白雕花重甲",
    "神官长袍",
    "鎏金头冠",
}
_FALLBACK_FRAGMENT_HINTS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("成年女性", "成熟女性", "女人", "女性"), ("成年女性",)),
    (("女孩", "少女", "女学生"), ("女孩",)),
    (("杂志", "编辑", "封面"), ("杂志编辑风格",)),
    (("35mm", "胶片摄影", "film photograph"), ("35mm胶片摄影",)),
    (("大画幅", "棚拍", "large-format studio"), ("大画幅棚拍",)),
    (("水粉", "gouache"), ("水粉插画",)),
    (("墨洗", "留白", "ink wash"), ("墨洗留白",)),
    (("书店",), ("书店",)),
    (("independent bookstore", "独立书店"), ("独立书店",)),
    (("studio fashion woman", "影棚时尚女性"), ("影棚时尚女性",)),
    (("clean studio backdrop", "影棚纯色背景"), ("影棚纯色背景",)),
    (("library", "图书馆"), ("图书馆",)),
    (("homebody gamer girl", "居家游戏女孩"), ("居家游戏女孩",)),
    (("blonde woman by the lakeside", "湖畔金发女性"), ("湖畔金发女性",)),
    (("female warrior", "女武士"), ("女武士",)),
    (("library", "图书馆"), ("图书馆",)),
    (("street after rain", "雨后街头"), ("雨后街头",)),
    (("neon district", "霓虹街区"), ("霓虹街区",)),
    (("industrial ruins", "工业废墟"), ("工业废墟",)),
    (("Nordic coast", "北欧海岸"), ("北欧海岸",)),
    (("frozen forest", "冰冻森林"), ("冰冻森林",)),
    (("black iron throne", "黑铁王座"), ("黑铁王座",)),
    (("volcanic cave", "火山洞穴"), ("火山洞穴",)),
    (("stairway above the clouds", "云端阶梯"), ("云端阶梯",)),
    (("goddess", "神女"), ("神女",)),
    (("priestess", "祭司"), ("祭司",)),
    (("sorceress", "魔女"), ("魔女",)),
    (("female adventurer", "女冒险者"), ("女冒险者",)),
    (("ancient training hall", "古建道场"), ("古建道场",)),
    (("moonlit courtyard", "月下庭院"), ("月下庭院",)),
    (("sacred altar", "神圣祭坛"), ("神圣祭坛",)),
    (("star-sea temple", "星海神殿"), ("星海神殿",)),
    (("suspended sky temple", "悬空神庙"), ("悬空神庙",)),
    (("窗边", "窗前"), ("窗边",)),
    (("urban rooftop documentary mood", "城市屋顶纪实"), ("城市屋顶纪实",)),
    (("city rooftop", "城市天台"), ("城市天台",)),
    (("rooftop clothesline frame", "屋顶晾衣架"), ("屋顶晾衣架",)),
    (("sunset backlight", "日落逆光"), ("日落逆光",)),
    (("golden rim sidelight", "金色侧逆光"), ("金色侧逆光",)),
    (("wired earphones", "有线耳机"), ("有线耳机",)),
    (("profile composition", "侧脸构图"), ("侧脸构图",)),
    (("holy city in a mountain valley", "山谷圣城"), ("山谷圣城",)),
    (("megastructure temple", "巨构神殿"), ("巨构神殿",)),
    (("waterfall canyon", "瀑布峡谷"), ("瀑布峡谷",)),
    (("snow peaks in the far distance", "远山雪峰"), ("远山雪峰",)),
    (("epic city central axis", "史诗城市中轴"), ("史诗城市中轴",)),
    (("mountain-integrated architecture", "山体建筑一体化"), ("山体建筑一体化",)),
    (("axial symmetric megastructure framing", "中轴对称巨构"), ("中轴对称巨构",)),
    (("ultra-wide panoramic framing", "超广角全景"), ("超广角全景",)),
    (("colossal tree spirit", "树灵巨像"), ("树灵巨像",)),
    (("ancient wood guardian", "古木守卫"), ("古木守卫",)),
    (("vinebound wood fiend", "藤蔓木妖"), ("藤蔓木妖",)),
    (("industrial chamber", "工业舱室"), ("工业舱室",)),
    (("intimidating colossal close shot", "巨物压迫近景"), ("巨物压迫近景",)),
    (("rotted bark texture", "朽木树皮纹理"), ("朽木树皮纹理",)),
    (("moss-covered overgrowth texture", "苔藓附生质感"), ("苔藓附生质感",)),
    (("glowing fissures", "发光裂隙"), ("发光裂隙",)),
    (("浴室", "浴缸", "淋浴"), ("浴室",)),
    (("湖畔", "夕照"), ("湖畔夕照",)),
    (("霓虹",), ("霓虹夜色",)),
    (("黄金时刻侧光", "golden-hour side-light"), ("黄金时刻侧光",)),
    (("阴天柔散光", "overcast softbox diffusion"), ("阴天柔散光",)),
    (("黑色电影硬光", "hard noir key-light"), ("黑色电影硬光",)),
    (("暖色轮廓逆光", "warm rim light"), ("暖色轮廓逆光",)),
    (("蓝灰月光", "moonlight"), ("蓝灰月光",)),
    (("red mist expressionist lighting", "红雾", "表现主义打光"), ("红雾表现主义打光",)),
    (("blue-cyan cold mist", "青蓝冷雾", "cold mist"), ("青蓝冷雾",)),
    (("青橙", "Teal and Orange"), ("青橙色调",)),
    (("近景", "特写"), ("近景", "面部聚焦")),
    (("中景半身", "半身构图"), ("中景半身构图",)),
    (("镜头近距离", "贴近", "近距离"), ("镜头近距离",)),
    (("俯视平铺", "flat-lay", "top-down"), ("俯视平铺",)),
    (("荷兰式倾斜", "dutch tilt"), ("荷兰式倾斜",)),
    (("过肩镜头", "over-the-shoulder"), ("过肩镜头",)),
    (("微距特写", "macro close-up"), ("微距特写",)),
    (("200mm长焦压缩", "long-lens compression", "200mm"), ("200mm长焦压缩",)),
    (("old uncoated glass lens", "uncoated glass", "non-coated lens"), ("复古非镀膜镜头",)),
    (("rgb split", "rgb separation"), ("RGB轻微分离",)),
    (("chromatic aberration", "color fringing"), ("轻微色差",)),
    (("halation", "soft halation", "soft halo"), ("柔和光晕",)),
    (("faded old-film", "faded film", "old-film patina"), ("老胶片褪色感",)),
    (("hong kong film stock", "hk film stock"), ("港片胶片质感",)),
    (("white cloak", "白色斗篷"), ("白色斗篷",)),
    (("black-gold heavy armor", "黑金重甲"), ("黑金重甲",)),
    (("silver-white engraved heavy armor", "银白雕花重甲"), ("银白雕花重甲",)),
    (("high priest ceremonial robe", "神官长袍"), ("神官长袍",)),
    (("gilded ceremonial crown", "鎏金头冠"), ("鎏金头冠",)),
    (("holy knight", "神圣骑士"), ("神圣骑士",)),
    (("frost knight", "冰霜骑士"), ("冰霜骑士",)),
    (("infernal angel", "炎魔天使"), ("炎魔天使",)),
    (("sun disc", "日轮"), ("日轮",)),
    (("moon disc", "月轮"), ("月轮",)),
    (("sacred flame", "圣火"), ("圣火",)),
    (("scepter", "权杖"), ("权杖",)),
    (("站在", "站姿", "挺拔"), ("站姿挺拔",)),
    (("倚靠", "靠着"), ("倚靠栏杆",)),
    (("双手负后",), ("双手负后",)),
    (("俯身", "前倾"), ("身体微微前倾俯身",)),
    (("持物待发", "持刀", "持枪", "手持"), ("持物待发",)),
    (("皮肤着色", "皮肤干净"), ("皮肤着色干净",)),
    (("冷白皮",), ("冷白皮",)),
    (("时尚成片", "成片感"), ("时尚成片感更强",)),
    (("封面肖像", "视觉重心"), ("人物视觉重心更偏封面肖像",)),
    (("高细节", "精细", "细节"), ("高细节",)),
    (("中画幅质感", "large-format"), ("中画幅质感",)),
    (("广告成片质感", "editorial finish"), ("广告成片质感",)),
    (("低保真", "标准", "True", "False"), tuple()),
)

_SMART_TEXT_TAG_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("杂志", "封面", "编辑", "editorial", "magazine", "cover"), ("杂志编辑摄影", "时尚写真", "人物完整入镜", "主体突出")),
    (("真实", "写实", "真人", "摄影", "photo", "photoreal", "realistic"), ("真实感", "照片级", "真实皮肤质感", "50mm标准镜头")),
    (("电影", "cinematic", "胶片", "film"), ("电影感", "电影调色", "侧光", "浅景深")),
    (("35mm", "film photograph"), ("35mm胶片摄影", "电影感", "35mm镜头")),
    (("大画幅", "large-format studio"), ("大画幅棚拍", "中画幅质感", "广告成片质感")),
    (("港式武侠", "hong kong wuxia"), ("港式武侠", "港风", "35mm胶片摄影", "电影剧照感")),
    (("东方古风武侠", "wuxia cinema"), ("东方古风武侠", "港式武侠", "港式武侠胶片", "35mm胶片摄影")),
    (("都市电影人文", "urban cinema humanism"), ("都市电影人文", "真实感", "纪实电影摄影")),
    (("时尚编辑商业广告", "fashion editorial campaign"), ("时尚编辑商业广告", "高端时尚编辑肖像", "杂志编辑摄影")),
    (("高端时尚编辑", "fashion editorial portrait"), ("高端时尚编辑肖像", "杂志编辑摄影", "大画幅棚拍")),
    (("日韩", "日系", "韩系", "japanese", "korean"), ("日韩影像", "日系电影感", "生活流写实")),
    (("水粉", "gouache"), ("水粉插画", "插画感")),
    (("墨洗", "ink wash", "留白"), ("墨洗留白", "古风")),
    (("私房", "内衣", "睡袍", "lingerie", "boudoir"), ("成年女性", "私房写真", "内衣风", "全景全身", "柔光")),
    (("浴室", "浴缸", "淋浴", "蒸汽", "湿滑", "bath", "shower", "steam"), ("浴室", "温泉雾气", "湿发", "全景全身", "柔光")),
    (("霓虹", "夜店", "酒吧", "neon", "club"), ("彩色霓虹光", "夜晚", "高对比", "电影调色")),
    (("海边", "海滩", "beach", "ocean"), ("海边", "黄昏", "自然光", "低饱和")),
    (("雪", "冰", "snow", "winter"), ("雪地", "冷色调", "柔和逆光")),
    (("黄金时刻侧光", "golden-hour side-light"), ("黄金时刻侧光", "暖色调")),
    (("阴天柔散光", "overcast softbox diffusion"), ("阴天柔散光", "低对比")),
    (("黑色电影硬光", "hard noir key-light"), ("黑色电影硬光", "高对比")),
    (("暖色轮廓逆光", "warm rim light"), ("暖色轮廓逆光", "轮廓光")),
    (("蓝灰月光", "moonlight"), ("蓝灰月光", "冷色调")),
    (("red mist expressionist lighting", "红雾", "表现主义打光"), ("红雾表现主义打光", "高对比")),
    (("blue-cyan cold mist", "青蓝冷雾", "cold mist"), ("青蓝冷雾", "低饱和")),
    (("俯视平铺", "flat-lay", "top-down"), ("俯视平铺",)),
    (("荷兰式倾斜", "dutch tilt"), ("荷兰式倾斜",)),
    (("过肩镜头", "over-the-shoulder"), ("过肩镜头",)),
    (("微距特写", "macro close-up"), ("微距特写",)),
    (("200mm长焦压缩", "long-lens compression", "200mm"), ("200mm长焦压缩",)),
    (("old uncoated glass lens", "uncoated glass", "non-coated lens"), ("复古非镀膜镜头",)),
    (("rgb split", "rgb separation"), ("RGB轻微分离",)),
    (("chromatic aberration", "color fringing"), ("轻微色差",)),
    (("halation", "soft halation", "soft halo"), ("柔和光晕",)),
    (("faded old-film", "faded film", "old-film patina"), ("老胶片褪色感",)),
    (("hong kong film stock", "hk film stock"), ("港片胶片质感",)),
    (("古风", "国风", "汉服", "唐风", "宋韵"), ("古风", "古风人像", "成年女性", "东方建筑", "柔光")),
    (("古风电影氛围", "ancient cinematic mood"), ("古风电影氛围", "古风电影剧照", "柔光", "人物完整入镜")),
    (("志怪", "惊悚", "雾夜", "supernatural thriller"), ("志怪古风", "港风惊悚志怪", "黑色电影硬光")),
    (("神话", "神女", "祭司", "神殿", "myth", "goddess"), ("神话感", "神女", "神殿", "体积光", "神圣")),
    (("敦煌神性", "dunhuang"), ("敦煌神性", "神庙壁画感", "神话感", "圣辉逆光")),
    (("赛博", "科幻", "机甲", "cyber", "sci-fi", "scifi"), ("CG感", "科幻场景", "金属舱室", "全息界面", "电影级CG")),
    (("东方赛博机甲", "oriental cyber mecha"), ("东方赛博机甲", "机能赛博", "CG感", "义体金属细节")),
    (("东方赛博武侠朋克", "cyber wuxia punk"), ("东方赛博武侠朋克", "东方赛博机甲", "能量刀", "全息界面")),
    (("西方奇幻", "western fantasy"), ("西方奇幻史诗", "神话感", "体积光")),
    (("holy knight", "神圣骑士"), ("神圣骑士", "白色斗篷", "黑金重甲")),
    (("frost knight", "冰霜骑士"), ("冰霜骑士", "白色斗篷", "银白雕花重甲")),
    (("infernal angel", "炎魔天使"), ("炎魔天使", "黑金重甲", "圣火")),
    (("goddess", "神女"), ("神女", "神话感")),
    (("priestess", "祭司"), ("祭司", "神话感")),
    (("sorceress", "魔女"), ("魔女", "神话感")),
    (("female adventurer", "女冒险者"), ("女冒险者",)),
    (("homebody gamer girl", "居家游戏女孩"), ("居家游戏女孩",)),
    (("blonde woman by the lakeside", "湖畔金发女性"), ("湖畔金发女性",)),
    (("female warrior", "女武士"), ("女武士",)),
    (("library", "图书馆"), ("图书馆",)),
    (("street after rain", "雨后街头"), ("雨后街头",)),
    (("neon district", "霓虹街区"), ("霓虹街区",)),
    (("industrial ruins", "工业废墟"), ("工业废墟",)),
    (("Nordic coast", "北欧海岸"), ("北欧海岸",)),
    (("frozen forest", "冰冻森林"), ("冰冻森林",)),
    (("black iron throne", "黑铁王座"), ("黑铁王座",)),
    (("volcanic cave", "火山洞穴"), ("火山洞穴",)),
    (("stairway above the clouds", "云端阶梯"), ("云端阶梯",)),
    (("ancient training hall", "古建道场"), ("古建道场",)),
    (("moonlit courtyard", "月下庭院"), ("月下庭院",)),
    (("sacred altar", "神圣祭坛"), ("神圣祭坛",)),
    (("star-sea temple", "星海神殿"), ("星海神殿",)),
    (("suspended sky temple", "悬空神庙"), ("悬空神庙",)),
    (("backless gown", "露背礼服"), ("露背礼服",)),
    (("high priest ceremonial robe", "神官长袍"), ("神官长袍", "鎏金头冠")),
    (("sun disc", "日轮"), ("日轮",)),
    (("moon disc", "月轮"), ("月轮",)),
    (("sacred flame", "圣火"), ("圣火",)),
    (("scepter", "权杖"), ("权杖",)),
    (("long silver-white hair", "银白长发"), ("银白长发",)),
    (("center-parted short hair", "中分短发"), ("中分短发",)),
    (("classical Chinese architecture", "古风建筑"), ("古风建筑",)),
    (("religious sanctuary", "宗教圣所"), ("宗教圣所",)),
    (("cafe", "咖啡厅"), ("咖啡厅",)),
    (("art studio", "画室"), ("画室",)),
    (("flying fish robe", "飞鱼服"), ("飞鱼服",)),
    (("wide-sleeved ceremonial robe", "宽袖法袍"), ("宽袖法袍",)),
    (("martial outfit", "劲装"), ("劲装",)),
    (("holding a camera", "手持相机"), ("手持相机",)),
    (("urban rooftop documentary", "城市屋顶纪实", "roof documentary"), ("城市屋顶纪实", "真实感", "生活电影剧照")),
    (("city rooftop", "城市天台", "rooftop"), ("城市天台", "日落逆光", "负空间留白")),
    (("rooftop clothesline", "屋顶晾衣架"), ("屋顶晾衣架",)),
    (("sunset backlight", "日落逆光"), ("日落逆光", "自然光")),
    (("golden rim sidelight", "金色侧逆光"), ("金色侧逆光", "轮廓光")),
    (("wired earphones", "有线耳机"), ("有线耳机",)),
    (("profile composition", "侧脸构图"), ("侧脸构图", "负空间留白")),
    (("holy city in a mountain valley", "山谷圣城"), ("山谷圣城", "神话感", "大全景")),
    (("megastructure temple", "巨构神殿"), ("巨构神殿", "神话感")),
    (("waterfall canyon", "瀑布峡谷"), ("瀑布峡谷",)),
    (("snow peaks in the far distance", "远山雪峰"), ("远山雪峰",)),
    (("epic city central axis", "史诗城市中轴"), ("史诗城市中轴",)),
    (("mountain-integrated architecture", "山体建筑一体化"), ("山体建筑一体化",)),
    (("axial symmetric megastructure framing", "中轴对称巨构"), ("中轴对称巨构",)),
    (("ultra-wide panoramic framing", "超广角全景"), ("超广角全景", "大全景")),
    (("colossal tree spirit", "树灵巨像"), ("树灵巨像", "CG感")),
    (("ancient wood guardian", "古木守卫"), ("古木守卫", "CG感")),
    (("vinebound wood fiend", "藤蔓木妖"), ("藤蔓木妖", "CG感")),
    (("industrial chamber", "工业舱室"), ("工业舱室",)),
    (("intimidating colossal close shot", "巨物压迫近景"), ("巨物压迫近景",)),
    (("rotted bark texture", "朽木树皮纹理"), ("朽木树皮纹理",)),
    (("moss-covered overgrowth texture", "苔藓附生质感"), ("苔藓附生质感",)),
    (("glowing fissures", "发光裂隙"), ("发光裂隙",)),
    (("independent bookstore", "独立书店"), ("独立书店", "书店女孩")),
    (("clean studio backdrop", "影棚纯色背景"), ("影棚纯色背景", "影棚时尚女性")),
    (("港式武侠", "港风武侠", "hong kong wuxia"), ("港式武侠", "港风", "35mm胶片摄影", "电影剧照感")),
    (("古风电影氛围", "ancient cinematic mood"), ("古风电影氛围", "古风电影剧照", "柔光", "人物完整入镜")),
    (("敦煌神性", "神庙壁画", "dunhuang"), ("敦煌神性", "神庙壁画感", "神话感", "圣辉逆光")),
    (("东方赛博机甲", "oriental cyber mecha"), ("东方赛博机甲", "机能赛博", "CG感", "义体金属细节")),
    (("温柔", "柔和", "清冷", "优雅"), ("温柔", "优雅", "柔光", "高光过渡柔和")),
    (("霸气", "强势", "冷艳"), ("霸气", "低角度", "高对比", "主体突出")),
    (("湿发", "wet hair"), ("湿发", "真实皮肤质感", "高光过渡柔和")),
    (("白发", "银发", "银白", "silver hair", "white hair"), ("银白长发", "冷白皮")),
    (("俯视平铺", "flat-lay", "top-down"), ("俯视平铺",)),
    (("荷兰式倾斜", "dutch tilt"), ("荷兰式倾斜",)),
    (("过肩镜头", "over-the-shoulder"), ("过肩镜头",)),
    (("微距特写", "macro close-up"), ("微距特写",)),
    (("200mm长焦压缩", "long-lens compression", "200mm"), ("200mm长焦压缩",)),
    (("高马尾", "high ponytail"), ("高马尾",)),
    (("低马尾", "low ponytail"), ("低马尾",)),
    (("双马尾", "twin tails"), ("双马尾",)),
    (("麻花辫", "braid"), ("麻花辫",)),
    (("双麻花辫", "double braids"), ("双麻花辫",)),
    (("羊毛卷", "permed curls"), ("羊毛卷",)),
    (("短卷发", "short curly hair"), ("短卷发",)),
    (("长卷发", "long curly hair"), ("长卷发",)),
    (("短发", "齐耳", "bob", "short hair"), ("短发", "齐耳短发")),
    (("齐肩", "锁骨发", "shoulder length"), ("齐肩短发", "锁骨发")),
    (("长发", "long hair"), ("长发",)),
    (("及腰", "超长发", "very long hair"), ("及腰长发", "超长发")),
    (("卷发", "大波浪", "wavy hair", "curly hair"), ("波浪卷发", "大波浪长发")),
    (("直发", "straight hair"), ("自然直发",)),
    (("刘海", "bangs"), ("空气刘海",)),
    (("法式刘海", "french bangs"), ("法式刘海",)),
    (("龙须刘海", "face-framing side strands"), ("龙须刘海",)),
    (("中分", "middle part"), ("中分",)),
    (("侧分", "side part"), ("侧分",)),
    (("黑发", "black hair"), ("黑发",)),
    (("金发", "blonde"), ("金发",)),
    (("红发", "red hair"), ("红发",)),
    (("紫发", "purple hair"), ("紫发",)),
    (("青发", "teal hair"), ("青发",)),
    (("茶棕发", "tea brown hair"), ("茶棕发",)),
    (("长腿", "long legs"), ("长腿",)),
    (("腿部修长", "slender legs"), ("腿部修长",)),
    (("腰臀曲线", "waist-to-hip", "hourglass"), ("腰臀曲线自然",)),
    (("骨架轻盈", "light frame"), ("骨架轻盈",)),
    (("肩宽适中", "balanced shoulders"), ("肩宽适中",)),
    (("锁骨明显", "defined collarbones"), ("锁骨明显",)),
    (("下颌线", "jawline"), ("清晰下颌线",)),
    (("鹅蛋脸", "oval face"), ("鹅蛋脸",)),
    (("面部轮廓", "facial contour", "face contour"), ("面部轮廓清晰",)),
    (("大眼睛", "large eyes"), ("大眼睛",)),
    (("鼻梁挺直", "straight nose bridge", "upright nose bridge"), ("鼻梁挺直",)),
    (("高鼻梁", "nose bridge"), ("高鼻梁",)),
    (("鼻翼", "nostril", "nostrils"), ("鼻翼精致",)),
    (("饱满嘴唇", "full lips"), ("饱满嘴唇",)),
    (("唇峰", "cupid's bow"), ("唇峰明显",)),
    (("唇珠", "lip bead"), ("唇珠明显",)),
    (("眉形", "眉峰", "brow"), ("眉形清晰", "眉峰明显")),
    (("卧蚕", "under-eye puff"), ("卧蚕明显",)),
    (("眼尾上挑", "upturned eyes"), ("眼尾上挑",)),
    (("眼距", "eye spacing", "interocular"), ("眼距适中",)),
    (("眼型", "eye shape"), ("眼型清晰",)),
    (("微笑", "笑容", "smile"), ("微笑", "嘴角微扬")),
    (("冷眼", "cold stare"), ("冷眼凝视",)),
    (("温柔注视", "gentle gaze"), ("温柔注视",)),
    (("迷离", "hazy gaze"), ("迷离眼神",)),
    (("若有所思", "thoughtful"), ("若有所思",)),
    (("回眸", "looking back"), ("回眸眼神",)),
    (("倔强", "stubborn"), ("倔强眼神",)),
    (("平静神情", "calm expression"), ("平静神情",)),
    (("欲感", "sensual gaze"), ("欲感眼神",)),
    (("坚定", "determined"), ("坚定眼神",)),
    (("凌厉", "sharp intense"), ("凌厉眼神",)),
    (("眼神放空", "vacant gaze"), ("眼神放空",)),
    (("裸妆", "bare-face"), ("裸妆",)),
    (("淡妆", "light makeup"), ("淡妆",)),
    (("烟熏妆", "smoky makeup"), ("烟熏妆",)),
    (("红唇", "red lips"), ("红唇",)),
    (("清透底妆", "clear foundation"), ("清透底妆",)),
    (("豆沙唇", "rosewood lips"), ("豆沙唇",)),
    (("雾面妆", "matte makeup"), ("雾面妆",)),
    (("光泽唇", "glossy lips"), ("光泽唇",)),
    (("裸色唇", "nude lips"), ("裸色唇",)),
    (("眼线", "eyeliner"), ("眼线清晰",)),
    (("腮红", "blush"), ("腮红自然",)),
    (("腮红位置", "blush placement"), ("腮红位置清晰",)),
    (("眼影", "eyeshadow"), ("眼影层次分明",)),
    (("高光", "highlight"), ("高光提亮",)),
    (("修容", "contour", "contouring"), ("修容自然",)),
    (("看镜头", "看向镜头", "looking at camera"), ("看向镜头",)),
    (("回头看", "回头看向镜头", "looking back"), ("回头看向镜头",)),
    (("低头", "looking downward"), ("低头凝视",)),
    (("手部自然", "手部姿态", "natural hand"), ("手部姿态自然",)),
    (("撩头发", "brushing hair"), ("撩头发",)),
    (("扶眼镜", "adjusting glasses"), ("扶眼镜",)),
    (("眼镜", "glasses", "sunglasses"), ("扶眼镜", "眼镜")),
    (("耳环", "earrings", "ear cuff"), ("耳环",)),
    (("项链", "necklace", "choker"), ("项链",)),
    (("戒指", "ring"), ("戒指",)),
    (("帽子", "beret", "cap", "hat"), ("帽子",)),
    (("墨镜", "sunglasses"), ("墨镜",)),
    (("珍珠耳环", "pearl earrings"), ("珍珠耳环",)),
    (("耳钉", "stud earrings"), ("耳钉",)),
    (("耳骨夹", "ear cuff"), ("耳骨夹",)),
    (("手链", "bracelet"), ("手链",)),
    (("手镯", "bangle"), ("手镯",)),
    (("胸针", "brooch"), ("胸针",)),
    (("项圈", "choker"), ("项圈",)),
    (("围巾", "scarf", "silk scarf"), ("围巾",)),
    (("腰带", "belt"), ("腰带",)),
    (("手提包", "handbag"), ("手提包",)),
    (("托特包", "tote bag"), ("托特包",)),
    (("斜挎包", "crossbody bag"), ("斜挎包",)),
    (("单肩包", "shoulder bag"), ("单肩包",)),
    (("相机", "camera"), ("相机",)),
    (("单反相机", "dslr camera"), ("单反相机",)),
    (("摄影包", "camera bag"), ("摄影包",)),
    (("手机", "phone", "mobile"), ("手机",)),
    (("咖啡杯", "coffee cup"), ("手持咖啡杯",)),
    (("书本", "book", "notebook"), ("书本",)),
    (("雨伞", "umbrella"), ("雨伞",)),
    (("耳机", "headphones"), ("耳机",)),
    (("背包", "backpack"), ("背包",)),
    (("腰包", "waist bag"), ("腰包",)),
    (("脚完整", "脚部完整", "feet fully"), ("脚部完整入镜", "人物完整入镜")),
    (("全身留白", "breathing room"), ("全身留白",)),
    (("自然透视", "natural perspective"), ("自然透视",)),
    (("浅景深", "shallow depth of field"), ("浅景深",)),
    (("镜头近距离", "close camera distance", "close-up camera distance"), ("镜头近距离",)),
    (("35mm镜头", "35mm lens"), ("35mm镜头",)),
    (("50mm标准镜头", "50mm standard lens"), ("50mm标准镜头",)),
    (("85mm人像镜头", "85mm portrait lens"), ("85mm人像镜头",)),
    (("落地窗", "floor-to-ceiling"), ("落地窗",)),
    (("窗边", "by the window"), ("窗边",)),
    (("玻璃橱窗", "storefront"), ("玻璃橱窗",)),
    (("玄关", "entryway"), ("玄关",)),
    (("走廊", "hallway"), ("走廊",)),
    (("衣帽间", "walk-in closet"), ("衣帽间",)),
    (("厨房岛台", "kitchen island"), ("厨房岛台",)),
    (("浴室镜前", "bathroom mirror"), ("浴室镜前",)),
    (("短靴", "ankle boots"), ("短靴",)),
    (("长靴", "knee-high boots"), ("长靴",)),
    (("高跟", "high heels"), ("尖头高跟鞋",)),
    (("缎面", "satin"), ("缎面",)),
    (("收腰", "tailored waist"), ("收腰剪裁",)),
    (("真丝", "silk"), ("真丝",)),
    (("蕾丝", "lace"), ("蕾丝",)),
    (("针织", "knit"), ("针织纹理", "针织开衫")),
    (("皮革", "leather"), ("皮革",)),
    (("透明薄纱", "sheer"), ("透明薄纱",)),
    (("天鹅绒", "velvet"), ("天鹅绒",)),
    (("棉质衬衫", "cotton shirt"), ("棉质衬衫",)),
    (("粗花呢", "tweed"), ("粗花呢",)),
    (("层叠领口", "layered neckline"), ("层叠领口",)),
    (("露肩", "off-shoulder"), ("露肩设计",)),
    (("高领", "turtleneck"), ("高领结构",)),
    (("短外套", "cropped jacket"), ("短外套",)),
    (("长外套", "long coat"), ("长外套",)),
    (("开衩", "slit"), ("开衩设计",)),
    (("双眼清晰", "sharp eyes"), ("双眼清晰",)),
    (("手部结构", "hand anatomy"), ("手部结构自然",)),
    (("面部第一视觉中心", "face first", "focus on face"), ("面部第一视觉中心",)),
    (("景深稳定", "stable depth of field"), ("景深控制稳定",)),
    (("焦点在脸", "focus on face"), ("焦点落在面部",)),
    (("边缘干净", "clean edges"), ("边缘干净",)),
    (("背景不过分抢镜", "background not stealing focus"), ("背景不过分抢镜",)),
    (("背景不要抢镜", "背景不抢镜", "别抢镜", "不要抢镜", "background not stealing focus", "background not too dominant", "keep background subtle"), ("背景不过分抢镜",)),
    (("丰满", "curvy"), ("丰满", "全景全身")),
    (("双人", "couple", "互动"), ("双人互动", "全景全身")),
    (("特写", "close-up", "closeup"), ("近景", "面部聚焦", "85mm人像镜头")),
    (("半身", "portrait"), ("中景半身", "85mm人像镜头")),
    (("全身", "full body"), ("全景全身", "标准镜头")),
    (("逆光", "backlight"), ("柔和逆光", "轮廓光")),
    (("粉", "玫瑰", "rose"), ("玫瑰粉调", "柔光")),
    (("高饱和", "saturated"), ("高饱和",)),
    (("面具", "mask"), ("面具",)),
    (("武器", "weapon"), ("武器",)),
    (("全息", "hologram"), ("全息界面",)),
    (("高质量", "精细", "细节", "detail", "quality"), ("高细节", "材质细节丰富", "清晰对焦")),
)
_SMART_TEXT_STYLE_FAMILIES: dict[str, set[str]] = {
    "真实感": {"真实感", "照片级", "杂志编辑风格", "杂志编辑摄影", "杂志感", "时尚写真", "电影感", "写实摄影", "都市电影人文", "城市屋顶纪实", "时尚编辑商业广告", "高端时尚编辑肖像", "日韩影像", "日系电影感", "韩系极简影像", "生活流写实"},
    "古风": {"古风", "古风人像", "古风电影剧照", "国风美学", "东方建筑", "宋制", "明制", "汉服", "东方古风武侠", "港式武侠", "志怪古风", "港风惊悚志怪"},
    "CG感": {"CG感", "电影级CG", "科幻场景", "金属舱室", "全息界面", "虚幻引擎", "3D渲染", "PBR渲染", "东方赛博机甲", "东方赛博武侠朋克", "树灵巨像", "古木守卫", "藤蔓木妖"},
    "神话感": {"神话感", "神女", "神殿", "体积光", "神圣", "神话史诗感", "西方奇幻史诗", "山谷圣城", "巨构神殿"},
    "插画感": {"插画感", "水彩线稿", "动漫", "后印象派", "厚涂", "手绘画风", "OVA风"},
}
_SMART_TEXT_STYLE_PRIORITY = ("真实感", "古风", "CG感", "神话感", "插画感")
_SMART_TEXT_STYLE_EXCLUSION_TERMS: dict[str, set[str]] = {
    "真实感": {"古风电影剧照", "古风人像", "神殿", "东方建筑", "CG感", "电影级CG", "虚幻引擎", "3D渲染", "PBR渲染", "插画感", "水彩线稿", "OVA风", "东方赛博机甲", "东方赛博武侠朋克", "西方奇幻史诗"},
    "古风": {"真实感", "照片级", "港风", "写实摄影", "CG感", "电影级CG", "虚幻引擎", "3D渲染", "PBR渲染", "神殿", "神话感", "杂志编辑摄影", "杂志编辑风格", "时尚写真", "高端时尚编辑肖像", "日韩影像", "韩系极简影像"},
    "CG感": {"古风", "古风人像", "古风电影剧照", "东方建筑", "神殿", "神话感", "杂志编辑摄影", "杂志编辑风格", "时尚写真", "插画感", "水彩线稿", "OVA风", "高端时尚编辑肖像", "日韩影像", "日系电影感"},
    "神话感": {"CG感", "电影级CG", "虚幻引擎", "3D渲染", "PBR渲染", "杂志编辑摄影", "杂志编辑风格", "时尚写真", "古风电影剧照", "高端时尚编辑肖像", "日韩影像"},
    "插画感": {"真实感", "照片级", "杂志编辑摄影", "杂志编辑风格", "CG感", "电影级CG", "虚幻引擎", "3D渲染", "PBR渲染"},
}
_SMART_TEXT_STYLE_PRIORITY_MODES = {"自动判断", "节点优先", "文本优先"}


def _style_isolation_mode(settings: dict[str, Any]) -> str:
    mode = str(settings.get("风格隔离策略", "平衡收敛") or "平衡收敛").strip()
    return mode if mode in {"平衡收敛", "严格风格隔离", "允许风格漂移"} else "平衡收敛"


def _normalize_text(text: str) -> str:
    return str(text or "").strip()


def _contains_marker(haystack: str, marker: str) -> bool:
    if not marker:
        return False
    folded = haystack.casefold()
    marker_folded = marker.casefold()
    if _CJK_PATTERN.search(marker):
        return marker in haystack
    if re.fullmatch(r"[a-z0-9]{1,3}", marker_folded):
        return re.search(
            rf"(?<![a-z0-9]){re.escape(marker_folded)}(?![a-z0-9])",
            folded,
        ) is not None
    return marker_folded in folded


def _append_unique(items: list[str], tag: str) -> None:
    text = _normalize_text(tag)
    if text and text not in items:
        items.append(text)


def _collect_state_tags(selected: OrderedDict[str, list[str]], custom_tags: list[str]) -> set[str]:
    tags = {item for values in selected.values() for item in values}
    tags.update(custom_tags)
    return tags


def _remove_state_tag(selected: OrderedDict[str, list[str]], custom_tags: list[str], tag: str) -> None:
    for group_name in list(selected.keys()):
        selected[group_name] = [item for item in selected[group_name] if item != tag]
    custom_tags[:] = [item for item in custom_tags if item != tag]


def _looks_like_full_body_request(text: str, tags: set[str]) -> bool:
    source = _normalize_text(text)
    return bool(tags & _SMART_TEXT_WIDE_SHOT_TAGS) or any(_contains_marker(source, marker) for marker in _SMART_TEXT_FULL_BODY_MARKERS)


def _resolve_adult_subject_anchor(text: str, current_tags: set[str], available_tags: set[str]) -> str:
    existing_gendered_subjects = current_tags & (
        _SMART_TEXT_ADULT_MALE_SUBJECT_TAGS | _SMART_TEXT_ADULT_FEMALE_SUBJECT_TAGS
    )
    if existing_gendered_subjects:
        return ""
    if any(_contains_marker(text, marker) for marker in _SMART_TEXT_ADULT_MALE_MARKERS):
        return "成年男性" if "成年男性" in available_tags else ""
    if any(_contains_marker(text, marker) for marker in _SMART_TEXT_ADULT_FEMALE_MARKERS):
        return "成年女性" if "成年女性" in available_tags else ""
    return "成年女性" if "成年女性" in available_tags else ""


def _resolve_smart_text_target_style(
    text: str,
    settings: dict[str, Any],
    selected: OrderedDict[str, list[str]],
    inferred: list[str],
) -> tuple[str, str]:
    priority_mode = str(settings.get("智能文本风格优先", "自动判断") or "自动判断").strip()
    if priority_mode not in _SMART_TEXT_STYLE_PRIORITY_MODES:
        priority_mode = "自动判断"

    explicit_style = str(settings.get("模板风格", "自动") or "自动").strip()
    selected_style_tags = {
        tag
        for values in selected.values()
        for tag in values
        if tag in {style_tag for family in _SMART_TEXT_STYLE_FAMILIES.values() for style_tag in family}
    }
    inferred_text_terms = set(inferred)
    inferred_text_terms.update(_split_prompt_terms(text))

    def score_style(candidates: set[str]) -> dict[str, int]:
        return {
            style_name: sum(1 for tag in candidates if tag in family_tags)
            for style_name, family_tags in _SMART_TEXT_STYLE_FAMILIES.items()
        }

    node_scores = score_style(selected_style_tags)
    text_scores = score_style(inferred_text_terms)

    def pick_best(scores: dict[str, int]) -> str:
        best_score = max(scores.values() or [0])
        if best_score <= 0:
            return ""
        return next(
            (style_name for style_name in _SMART_TEXT_STYLE_PRIORITY if scores.get(style_name, 0) == best_score),
            "",
        )

    node_style = explicit_style if explicit_style and explicit_style != "自动" else pick_best(node_scores)
    text_style = pick_best(text_scores)

    if priority_mode == "节点优先":
        return node_style or text_style, "节点优先"
    if priority_mode == "文本优先":
        return text_style or node_style, "文本优先"

    if explicit_style and explicit_style != "自动":
        return explicit_style, "自动判断→节点优先"
    if text_style and text_scores.get(text_style, 0) >= max(2, node_scores.get(node_style, 0) + 1 if node_style else 2):
        return text_style, "自动判断→文本优先"
    resolved_style = node_style or text_style
    if resolved_style == node_style and resolved_style:
        return resolved_style, "自动判断→节点优先"
    if resolved_style == text_style and resolved_style:
        return resolved_style, "自动判断→文本优先"
    return "", "自动判断"


def _filter_smart_text_style_pollution(tags: list[str], target_style: str) -> tuple[list[str], list[str]]:
    blocked = _smart_text_style_exclusion_terms(target_style)
    if not blocked:
        return list(tags), []
    kept: list[str] = []
    removed: list[str] = []
    for tag in tags:
        text = _normalize_text(tag)
        if text in blocked:
            removed.append(text)
            continue
        kept.append(text)
    return kept, removed


def _smart_text_style_exclusion_terms(target_style: str) -> set[str]:
    base_style = resolve_base_template_style(target_style)
    return _SMART_TEXT_STYLE_EXCLUSION_TERMS.get(base_style, set())


def infer_smart_text_tags(text: str, available_tags: set[str]) -> list[str]:
    """Infer concise, high-signal tags from free text without stuffing the state."""

    source = _normalize_text(text)
    if not source:
        return []

    inferred: list[str] = []
    for tag in sorted(available_tags, key=len, reverse=True):
        if len(tag) < 2:
            continue
        if _contains_marker(source, tag):
            _append_unique(inferred, tag)

    for markers, tags in _SMART_TEXT_TAG_RULES:
        if not any(_contains_marker(source, marker) for marker in markers):
            continue
        for tag in tags:
            if tag in available_tags:
                _append_unique(inferred, tag)
            elif tag not in inferred:
                _append_unique(inferred, tag)

    return inferred[:40]


def looks_like_adult_request(text: str, tags: list[str]) -> bool:
    source = f"{text} {' '.join(tags)}".strip()
    if not source:
        return False
    if any(_contains_marker(source, marker) for marker in _SMART_TEXT_ADULT_STRONG_MARKERS):
        return True

    explicit_tokens = {
        token.casefold()
        for token in re.split(r"[\s,，、;；|/\\:：()（）]+", source)
        if token.strip()
    }
    if explicit_tokens & _SMART_TEXT_ADULT_EXPLICIT_TOKENS:
        return True

    weak_group_hits = [
        {marker for marker in group if _contains_marker(source, marker)}
        for group in _SMART_TEXT_ADULT_WEAK_MARKER_GROUPS
    ]
    return all(weak_group_hits) and sum(len(matches) for matches in weak_group_hits) >= 3


def _looks_like_tag_chain(text: str) -> bool:
    source = _normalize_text(text)
    if not source:
        return False
    if any(marker in source for marker in ("。", "！", "？", ".", "!", "?")):
        return False
    fragments = [fragment.strip() for fragment in re.split(r"[，,、;；\n]+", source) if fragment.strip()]
    if len(fragments) < 5:
        return False
    short_fragments = sum(1 for fragment in fragments if len(fragment) <= 5)
    return short_fragments / len(fragments) >= 0.55


def _looks_like_outline_echo(text: str) -> bool:
    source = _normalize_text(text)
    if not source:
        return False
    if not any(marker in source for marker in _SMART_TEXT_OUTLINE_MARKERS):
        return False
    return bool(re.search(r"(?:[:：]|\+|、)", source))


def _looks_like_underbuilt_smart_text(text: str, *, user_text: str = "", primary_prompt: str = "") -> bool:
    source = _strip_smart_text_meta(text)
    if not source:
        return False

    fragments = [fragment.strip() for fragment in re.split(r"[，,、;；。.!?\n]+", source) if fragment.strip()]
    if not fragments:
        return False

    primary_fragments = [
        fragment.strip()
        for fragment in re.split(r"[，,、;；。.!?\n]+", _strip_smart_text_meta(primary_prompt))
        if fragment.strip()
    ]
    has_context = len(primary_fragments) >= 3 or len(_normalize_text(user_text)) >= 6
    if not has_context:
        return False

    normalized_fragments = {fragment.casefold() for fragment in fragments}
    if len(fragments) <= 2 and normalized_fragments.issubset({term.casefold() for term in _SMART_TEXT_SUBJECT_ONLY_TERMS}):
        return True
    if len(fragments) <= 2 and normalized_fragments.issubset({term.casefold() for term in _FALLBACK_STYLE_TERMS}):
        return True

    has_content_marker = any(marker in source for marker in _SMART_TEXT_CONTENT_MARKERS)
    cjk_count = len(_CJK_PATTERN.findall(source))
    if len(fragments) <= 1 and cjk_count <= 8 and not has_content_marker:
        return True

    return False


def apply_smart_text_to_state(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    text: str,
    available_tags: set[str],
    tag_group_index: dict[str, str],
    append_tag_to_state: Callable[[OrderedDict[str, list[str]], list[str], str], None],
) -> tuple[OrderedDict[str, list[str]], list[str], list[str]]:
    """Match smart text into the existing selected/custom tag state."""

    smart_text = _normalize_text(text)
    if not smart_text:
        return selected, custom_tags, []

    inferred = infer_smart_text_tags(smart_text, available_tags)
    notes: list[str] = []
    target_style, resolved_priority = _resolve_smart_text_target_style(smart_text, settings, selected, inferred)
    settings["智能文本风格解析结果"] = target_style
    settings["智能文本风格优先解析结果"] = resolved_priority
    isolation_mode = _style_isolation_mode(settings)
    removed_inferred_style_noise: list[str] = []
    if isolation_mode != "允许风格漂移":
        inferred, removed_inferred_style_noise = _filter_smart_text_style_pollution(inferred, target_style)
    if removed_inferred_style_noise:
        notes.append(f"智能文本风格隔离：按 {target_style} 轨道过滤冲突风格词 {'、'.join(dict.fromkeys(removed_inferred_style_noise))}")
    for tag in inferred:
        before = {item for values in selected.values() for item in values}
        before.update(custom_tags)
        append_tag_to_state(selected, custom_tags, tag)
        after = {item for values in selected.values() for item in values}
        after.update(custom_tags)
        if tag in after and tag not in before:
            group = tag_group_index.get(tag) or "自定义补充"
            notes.append(f"智能文本匹配：{group} 补入 {tag}")

    if target_style and isolation_mode != "允许风格漂移":
        blocked_existing = _smart_text_style_exclusion_terms(target_style)
        removed_existing: list[str] = []
        for tag in list(_collect_state_tags(selected, custom_tags)):
            if tag in blocked_existing:
                _remove_state_tag(selected, custom_tags, tag)
                removed_existing.append(tag)
        if removed_existing:
            notes.append(f"智能文本风格收敛：保留 {target_style} 主风格，移除状态里的冲突词 {'、'.join(dict.fromkeys(removed_existing))}")

    def append_default_full_body_guard(note: str) -> None:
        current_tags = _collect_state_tags(selected, custom_tags)
        if current_tags & (_SMART_TEXT_WIDE_SHOT_TAGS | _SMART_TEXT_MID_SHOT_CONFLICT_TAGS):
            return
        if "全景全身" in available_tags:
            append_tag_to_state(selected, custom_tags, "全景全身")
            notes.append(note)
        elif "全身" in available_tags:
            append_tag_to_state(selected, custom_tags, "全身")
            notes.append(note.replace("全景全身", "全身"))
        elif "中景半身" in available_tags:
            append_tag_to_state(selected, custom_tags, "中景半身")

    adult_mode = str(settings.get("标签反推模式", "") or "").strip() == "成人向成熟"
    if adult_mode or looks_like_adult_request(smart_text, inferred):
        settings["标签反推模式"] = "成人向成熟"
        settings["模板风格"] = "真实感" if str(settings.get("模板风格", "自动") or "自动") == "自动" else settings.get("模板风格")
        settings["主体类型"] = "人物角色" if str(settings.get("主体类型", "自动") or "自动") == "自动" else settings.get("主体类型")
        notes.append("智能文本匹配：启用成人向成熟收敛与明确成年主体护栏")
        adult_subject_anchor = _resolve_adult_subject_anchor(
            smart_text,
            _collect_state_tags(selected, custom_tags),
            available_tags,
        )
        if adult_subject_anchor:
            append_tag_to_state(selected, custom_tags, adult_subject_anchor)

        current_tags = _collect_state_tags(selected, custom_tags)
        if _looks_like_full_body_request(smart_text, current_tags):
            for conflict_tag in _SMART_TEXT_MID_SHOT_CONFLICT_TAGS & current_tags:
                _remove_state_tag(selected, custom_tags, conflict_tag)
            if "全景全身" in available_tags:
                append_tag_to_state(selected, custom_tags, "全景全身")
            elif "全身" in available_tags:
                append_tag_to_state(selected, custom_tags, "全身")
            notes.append("智能文本匹配：检测到全身构图意图，切换为全景全身护栏")
        else:
            append_default_full_body_guard("智能文本匹配：默认使用全景全身构图护栏")
    elif str(settings.get("主体类型", "自动") or "自动").strip() != "非人物主体":
        append_default_full_body_guard("智能文本匹配：普通模式默认使用全景全身构图")

    return selected, custom_tags, notes


def build_smart_text_seed(
    *,
    user_text: str,
    primary_prompt: str,
    selected_tags_text: str,
    settings: dict[str, Any],
    style_track: str = "",
) -> str:
    language = str(settings.get("提示词语言", "纯中文") or "纯中文")
    adult_mode = str(settings.get("标签反推模式", "") or "").strip() == "成人向成熟"
    non_person = str(settings.get("主体类型解析结果", "") or settings.get("主体类型", "自动") or "自动").strip() == "非人物主体"
    runtime_mode = str(settings.get("运行时随机模式解析结果", "") or settings.get("运行时随机模式", "") or "").strip()
    runtime_intensity = str(settings.get("运行时随机强度", "") or "").strip()
    isolation_mode = str(settings.get("风格隔离策略", "") or "").strip()
    nsfw_context = _normalize_text(str(settings.get("NSFW工作台标签摘要", "") or ""))
    dynamic_strategy = _normalize_text(str(settings.get("Skill动态变化策略", "") or ""))
    recent_context = _normalize_text(
        "；".join(
            str(item).strip()
            for item in list(settings.get("最近提示词指纹", []) or [])[:8]
            if str(item).strip()
        )
    )
    adult_instruction = (
        "成人成熟模式：已启用。优先吸收 NSFW 成熟写真工作台标签，明确成年主体与成熟氛围，把标签融合成连续成片文案，不要逐条罗列。"
        if adult_mode
        else "成人成熟模式：未启用。按普通图像提示词处理，把输入整理成自然连贯的成片描述。"
    )
    if language == "纯英文":
        language_instruction = "语言要求：只输出英文正向提示词，目标 360-600 words，不要包含中文解释。"
    elif language == "英文提示词+中文说明":
        language_instruction = "语言要求：先输出英文正向提示词，目标 360-600 words；末尾追加一小段中文说明，以“中文说明：”开头，说明画面主线。"
    else:
        language_instruction = "语言要求：只输出中文正向提示词，目标 700-1100 字。"
    output_instruction = (
        "输出：当前是非人物主体，优先吸收基础提示词和当前主线，写清事件触发、主体状态变化、功能或运动回应、环境反馈、光影迁移与最后定格；聚焦物体、机械、建筑、场景或概念设计本身，只补结构、材质、尺度、功能部件和空间关系；目标 700-1100 中文字/或 360-600 英文词；不要原样抄写标签，不要锁死风格和景别，不要重复堆同义标签。"
        if non_person
        else "输出：优先吸收基础提示词和当前主线，写清此刻发生的事件、人物动机、动作回应、情绪转折、环境与光线反馈以及镜头最终定格；目标 700-1100 中文字/或 360-600 英文词；默认完整人物入镜，除非用户明确要求近景、特写或半身；不要原样抄写标签，不要锁死风格和景别，不要重复堆同义标签，语气像具有剧情的电影剧照说明，不像标签列表。"
    )
    return "\n".join(
        [
            f"语言：{language}",
            language_instruction,
            adult_instruction,
            f"主体类型：{'非人物主体' if non_person else str(settings.get('主体类型解析结果', '') or settings.get('主体类型', '自动'))}",
            f"用户：{_normalize_text(user_text)}",
            f"当前轨道：{_normalize_text(style_track)}",
            f"运行时随机：{_normalize_text(runtime_mode)} / {_normalize_text(runtime_intensity)}",
            f"风格隔离：{_normalize_text(isolation_mode)}",
            f"NSFW工作台摘要：{nsfw_context or '未启用或无工作台标签'}",
            f"Skill动态变化策略：{dynamic_strategy or '无'}",
            f"最近输出避重：{recent_context or '无'}",
            "可用标签素材（只作素材，不要原样抄写）：",
            _normalize_text(selected_tags_text),
            "基础提示词：",
            _normalize_text(primary_prompt),
            output_instruction,
        ]
    ).strip()


def build_smart_text_settings(settings: dict[str, Any]) -> dict[str, Any]:
    next_settings = dict(settings)
    next_settings["系统提示词覆盖"] = SMART_TEXT_SYSTEM_TEMPLATE
    next_settings["最大生成token"] = max(128, min(2200, int(next_settings.get("最大生成token", 1800) or 1800)))
    next_settings["温度"] = min(0.62, max(0.28, float(next_settings.get("温度", 0.48) or 0.48)))
    next_settings["top_p"] = min(0.9, max(0.72, float(next_settings.get("top_p", 0.86) or 0.86)))
    next_settings["top_k"] = min(40, max(16, int(next_settings.get("top_k", 32) or 32)))
    next_settings["重复惩罚"] = min(1.22, max(1.1, float(next_settings.get("重复惩罚", 1.12) or 1.12)))
    next_settings["频率惩罚"] = min(0.6, max(0.12, float(next_settings.get("频率惩罚", 0.16) or 0.16)))
    next_settings["存在惩罚"] = min(0.5, max(0.06, float(next_settings.get("存在惩罚", 0.08) or 0.08)))
    return next_settings


def _split_prompt_terms(*texts: str) -> list[str]:
    terms: list[str] = []
    for text in texts:
        for item in _SMART_TEXT_WORD_SPLIT_PATTERN.split(str(text or "")):
            term = item.strip()
            if not term or term.casefold() in _FALLBACK_NOISE_TERMS:
                continue
            if term not in terms:
                terms.append(term)
            for markers, hints in _FALLBACK_FRAGMENT_HINTS:
                if not any(_contains_marker(term, marker) for marker in markers):
                    continue
                for hint in hints:
                    if hint and hint.casefold() not in _FALLBACK_NOISE_TERMS and hint not in terms:
                        terms.append(hint)
    return terms


def _pick_terms(terms: list[str], pool: set[str], limit: int) -> list[str]:
    picked = [term for term in terms if term in pool]
    return picked[:limit]


def _remaining_terms(terms: list[str], used: set[str], limit: int) -> list[str]:
    results: list[str] = []
    for term in terms:
        if term in used or term.casefold() in _FALLBACK_NOISE_TERMS:
            continue
        if term not in results:
            results.append(term)
        if len(results) >= limit:
            break
    return results


def _join_terms(terms: list[str]) -> str:
    return "、".join(term for term in terms if term)


def _join_style_terms(terms: list[str]) -> str:
    return "、".join(_FALLBACK_STYLE_LABELS.get(term, term) for term in terms if term)


def _apply_track_defaults(
    picked: list[str],
    defaults: list[str],
    *,
    limit: int,
) -> list[str]:
    next_values = list(picked)
    if next_values:
        return next_values[:limit]
    for value in defaults:
        if len(next_values) >= limit:
            break
        if value not in next_values:
            next_values.append(value)
    return next_values


def _strip_smart_text_meta(text: str) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    cleaned = cleaned.strip("“”\"'` \n\t")
    for pattern in _SMART_TEXT_META_PATTERNS:
        cleaned = pattern.sub("", cleaned).strip()
    fragments = []
    for raw in re.split(r"[\n]+", cleaned):
        line = raw.strip().lstrip("-*#> \t")
        if _SMART_TEXT_META_FRAGMENT_PATTERN.search(line):
            before_meta = _SMART_TEXT_META_FRAGMENT_PATTERN.split(line, maxsplit=1)[0].strip("，,。；;:： \n\t")
            after_meta = re.split(r"[:：]", line)[-1].strip("，,。；;:： \n\t") if re.search(r"[:：]", line) else ""
            line = "，".join(part for part in (before_meta, after_meta) if part)
        for pattern in _SMART_TEXT_META_PATTERNS:
            line = pattern.sub("", line).strip()
        if not line or _SMART_TEXT_META_FRAGMENT_PATTERN.search(line):
            continue
        fragments.append(line)
    cleaned = "，".join(fragments) if fragments else cleaned
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[，,]{2,}", "，", cleaned)
    return cleaned.strip("，,。；;:： \n\t")


def _normalize_adult_subject_terms(text: str, *, adult: bool) -> str:
    cleaned = str(text or "")
    if not adult:
        return cleaned
    for source, target in _SMART_TEXT_ADULT_YOUTH_REPLACEMENTS:
        cleaned = cleaned.replace(source, target)
    if "成年女性" not in cleaned and not re.search(r"成年男性|中年女性|中年男性", cleaned):
        cleaned = f"成年女性，{cleaned}"
    return cleaned


def _soften_explicit_adult_terms(text: str) -> str:
    cleaned = str(text or "")
    for source, target in _SMART_TEXT_EXPLICIT_ACTION_REPLACEMENTS.items():
        cleaned = cleaned.replace(source, target)
    for term in _SMART_TEXT_EXPLICIT_DROP_TERMS:
        cleaned = cleaned.replace(term, "")
    cleaned = re.sub(r"[，,]{2,}", "，", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip("，,。；;:： \n\t")


def _normalize_smart_text_language(language: str) -> str:
    cleaned = str(language or "纯中文").strip()
    return cleaned if cleaned in {"纯中文", "纯英文", "英文提示词+中文说明"} else "纯中文"


def _has_substantive_english(text: str) -> bool:
    return bool(re.search(r"\b[A-Za-z]{3,}\b", str(text or "")))


def _matches_smart_text_language(text: str, language: str) -> bool:
    source = str(text or "").strip()
    if not source:
        return True
    has_cjk = bool(_CJK_PATTERN.search(source))
    mode = _normalize_smart_text_language(language)
    if mode == "纯英文":
        return not has_cjk
    if mode == "英文提示词+中文说明":
        return has_cjk and _has_substantive_english(source)
    return has_cjk


def _normalize_english_adult_subject_terms(text: str, *, adult: bool) -> str:
    cleaned = str(text or "")
    if not adult:
        return cleaned
    replacements = (
        (r"\bschoolgirl\b", "young adult woman in collegiate styling"),
        (r"\bteenage girl\b", "young adult woman"),
        (r"\byoung girl\b", "young adult woman"),
        (r"\bgirl\b", "young adult woman"),
    )
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    if not re.search(r"\badult (?:woman|man|person|subject)\b|\bmature (?:woman|man|adult)\b", cleaned, re.IGNORECASE):
        cleaned = f"Adult subject, {cleaned}"
    return cleaned


def _normalize_smart_text_adult_subject_terms(text: str, *, adult: bool, language: str) -> str:
    if _normalize_smart_text_language(language) == "纯英文":
        return _normalize_english_adult_subject_terms(text, adult=adult)
    return _normalize_adult_subject_terms(text, adult=adult)


def sanitize_smart_text_prompt(
    *,
    text: str,
    user_text: str = "",
    primary_prompt: str = "",
    adult_mode: bool = False,
    style_track: str = "",
    subject_type: str = "自动",
    language: str = "纯中文",
) -> str:
    """Clean final smart-text output so model chatter never reaches the prompt slot."""

    original_raw = _strip_smart_text_meta(text)
    raw = original_raw
    language_mode = _normalize_smart_text_language(language)
    adult = bool(adult_mode) or looks_like_adult_request(f"{user_text} {primary_prompt} {raw}", [])
    original_has_uncertain_minor_terms = any(term in original_raw for term in _SMART_TEXT_UNCERTAIN_MINOR_TERMS)
    original_needs_rewrite = not _matches_smart_text_language(original_raw, language_mode) or (
        not original_has_uncertain_minor_terms
        and (
            _looks_like_tag_chain(original_raw)
            or _looks_like_outline_echo(original_raw)
            or _looks_like_underbuilt_smart_text(original_raw, user_text=user_text, primary_prompt=primary_prompt)
        )
    )
    raw = _normalize_smart_text_adult_subject_terms(raw, adult=adult, language=language_mode)
    raw = _soften_explicit_adult_terms(raw)
    should_rewrite_tag_chain = _looks_like_tag_chain(raw) and not any(
        term in original_raw for term in _SMART_TEXT_UNCERTAIN_MINOR_TERMS
    )
    if (
        original_needs_rewrite
        or
        should_rewrite_tag_chain
        or _looks_like_outline_echo(raw)
        or _looks_like_underbuilt_smart_text(raw, user_text=user_text, primary_prompt=primary_prompt)
    ):
        raw = fallback_smart_text(
            user_text=user_text,
            primary_prompt=primary_prompt,
            style_track=style_track,
            subject_type=subject_type,
            language=language_mode,
            adult_mode=adult,
        )
    if adult and any(term in raw for term in _SMART_TEXT_UNCERTAIN_MINOR_TERMS):
        raw = _normalize_smart_text_adult_subject_terms(raw, adult=True, language=language_mode)
        raw = _soften_explicit_adult_terms(raw)
    if not raw:
        return ""
    if _SMART_TEXT_META_FRAGMENT_PATTERN.search(raw):
        fallback = fallback_smart_text(
            user_text=user_text,
            primary_prompt=primary_prompt,
            style_track=style_track,
            subject_type=subject_type,
            language=language_mode,
            adult_mode=adult,
        )
        return _soften_explicit_adult_terms(
            _normalize_smart_text_adult_subject_terms(_strip_smart_text_meta(fallback), adult=adult, language=language_mode)
        )
    if not _matches_smart_text_language(raw, language_mode):
        return fallback_smart_text(
            user_text=user_text,
            primary_prompt=primary_prompt,
            style_track=style_track,
            subject_type=subject_type,
            language=language_mode,
            adult_mode=adult,
        )
    return raw


def _looks_like_rich_narrative_prompt(text: str, *, english: bool = False) -> bool:
    source = _strip_smart_text_meta(text)
    if english:
        word_count = len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", source))
        markers = ("because", "therefore", "respond", "turns from", "final frame", "story")
        return word_count >= 220 and sum(marker in source.casefold() for marker in markers) >= 2
    cjk_count = len(_CJK_PATTERN.findall(source))
    markers = ("故事", "因此", "回应", "情绪", "镜头", "定格", "结尾", "动作")
    return cjk_count >= 420 and sum(marker in source for marker in markers) >= 3


def _merge_smart_text_into_rich_narrative(
    *,
    user_text: str,
    primary_prompt: str,
    english: bool = False,
) -> str:
    primary = _strip_smart_text_meta(primary_prompt)
    if not _looks_like_rich_narrative_prompt(primary, english=english):
        return ""
    user_terms = _split_prompt_terms(user_text)
    additions = [
        term
        for term in user_terms
        if term and term.casefold() not in primary.casefold() and term.casefold() not in _FALLBACK_NOISE_TERMS
    ][:6]
    if not additions:
        return primary
    if english:
        visible = "; ".join(term for term in additions if not _CJK_PATTERN.search(term))
        if not visible:
            return primary
        bridge = (
            f" The added intention, {visible}, becomes a concrete cause inside the same event: "
            "it changes the subject's attention, motivates the next movement, and produces a visible response in nearby light, materials, or space rather than forming a separate keyword list."
        )
        return f"{primary}{bridge}"
    visible = "、".join(additions)
    bridge = (
        f"其中，{visible}成为同一事件里的补充动机或具体线索，它会改变主体的注意方向与下一步动作，"
        "并让附近的光线、材质或空间出现可见回应，而不是另起一串互不相关的标签。"
    )
    return f"{primary}{bridge}"


def _fallback_smart_text_chinese(
    *,
    user_text: str,
    primary_prompt: str,
    style_track: str = "",
    subject_type: str = "自动",
    adult_mode: bool = False,
) -> str:
    rich_narrative = _merge_smart_text_into_rich_narrative(
        user_text=user_text,
        primary_prompt=primary_prompt,
        english=False,
    )
    if rich_narrative:
        adult = bool(adult_mode) or looks_like_adult_request(f"{user_text} {primary_prompt}", [])
        return _soften_explicit_adult_terms(
            _normalize_adult_subject_terms(rich_narrative, adult=adult)
        )
    terms = _split_prompt_terms(user_text, primary_prompt)
    if not terms:
        return _normalize_text(primary_prompt)
    non_person = str(subject_type or "自动").strip() == "非人物主体"

    track_defaults = _FALLBACK_TRACK_DEFAULTS.get(str(style_track).strip(), {})
    styles = _pick_terms(terms, _FALLBACK_STYLE_TERMS, 1)
    subjects = _pick_terms(terms, _FALLBACK_SUBJECT_TERMS, 2)
    scenes = _pick_terms(terms, _FALLBACK_SCENE_TERMS, 1)
    lights = _pick_terms(terms, _FALLBACK_LIGHT_TERMS, 2)
    compositions = _pick_terms(terms, _FALLBACK_COMPOSITION_TERMS, 2)
    outfits = _pick_terms(terms, _FALLBACK_OUTFIT_TERMS, 3)
    actions = _pick_terms(terms, _FALLBACK_ACTION_TERMS, 1)
    props = _pick_terms(terms, _FALLBACK_PROP_TERMS, 2)
    if style_track:
        scenes = _apply_track_defaults(scenes, track_defaults.get("scene", []), limit=1)
        outfits = _apply_track_defaults(outfits, track_defaults.get("outfit", []), limit=3)
        lights = _apply_track_defaults(lights, track_defaults.get("light", []), limit=2)
        actions = _apply_track_defaults(actions, track_defaults.get("action", []), limit=1)
        props = _apply_track_defaults(props, track_defaults.get("props", []), limit=2)
        compositions = _apply_track_defaults(compositions, track_defaults.get("composition", []), limit=2)
    quality = _pick_terms(terms, _FALLBACK_QUALITY_TERMS, 3)
    used = set(styles + subjects + scenes + lights + compositions + outfits + actions + props + quality)
    details = _remaining_terms(terms, used, 8)

    lead_style = _join_style_terms(styles) or "完整画面"
    adult = bool(adult_mode) or looks_like_adult_request(f"{user_text} {primary_prompt}", terms)
    subject_text = _join_terms(subjects) or _join_terms(details[:2]) or ("非人物主体" if non_person else ("成年女性" if adult else "人物主体"))
    subject_text = subject_text if non_person else _normalize_adult_subject_terms(subject_text, adult=adult)
    scene_text = _join_terms(scenes)
    light_text = _join_terms(lights)
    composition_text = _join_terms(compositions) or ("全景、主体完整入镜" if non_person else "全景全身、人物完整入镜")
    outfit_text = _join_terms(outfits)
    action_text = _join_terms(actions)
    prop_text = _join_terms(props)
    detail_text = _join_terms(details)
    quality_text = _join_terms(quality) or "高细节、清晰对焦、主体结构完整"

    first = f"{lead_style}，画面以{subject_text}为核心"
    if action_text:
        first += f"，呈现{action_text}的姿态"
    if prop_text:
        first += f"，通过{prop_text}强化叙事"
    if non_person:
        first += "；主体不要被背景吞没，主体结构、整体轮廓、结构朝向、尺度比例和关键功能部件需要一眼清楚。"
    else:
        first += "；主体不要被背景吞没，人物轮廓、脸部方向和身体比例需要一眼清楚。"

    second_parts = []
    if outfit_text:
        if non_person:
            second_parts.append(f"外观结构与表面材质围绕{outfit_text}展开，强调体块、接缝、边缘层次和功能部件之间的自然关系")
        else:
            second_parts.append(f"服装造型围绕{outfit_text}展开，强调材质、结构和边缘层次与人物轮廓的自然关系")
    if scene_text:
        second_parts.append(f"场景放在{scene_text}，空间层次要服务主体而不是抢镜")
    if light_text:
        second_parts.append(f"使用{light_text}塑造氛围，让亮部、暗部和轮廓过渡自然")
    second_parts.append(f"镜头采用{composition_text}，保持透视稳定和主体完整")
    second = "，".join(second_parts) + "。"

    if non_person:
        third = f"主体表面、结构边缘、材质纹理、功能部件、道具和环境材质需要有可辨识的细节，但不要把所有元素平均铺开；画面优先突出主体轮廓、结构关系和场景尺度。整体保持主题清晰、主体关系明确，{quality_text}"
    else:
        third = f"服装、发丝、皮肤、道具和环境材质需要有可辨识的细节，但不要把所有元素平均铺开；画面优先突出主体表情、姿态和场景关系。整体保持主题清晰、主体关系明确，{quality_text}"
    if detail_text:
        third += f"，补充细节可融入{detail_text}"
    third += "。"

    fourth = (
        ("生成时避免把近似风格反复叠加，也不要同时塞入多个互相冲突的场景、外观材质或镜头；" if non_person else "生成时避免把近似风格反复叠加，也不要同时塞入多个互相冲突的场景、服装或镜头；")
        + "如果存在多种素材，只选择最能支撑画面主线的一组，其余作为轻微点缀。"
        + "最终效果应像一段完整的拍摄说明，既有主体、环境、光线和构图，也有材质、情绪和质量控制。"
    )
    return _soften_explicit_adult_terms(_normalize_adult_subject_terms(_strip_smart_text_meta(f"{first}{second}{third}{fourth}"), adult=adult))


_FALLBACK_ENGLISH_HINT_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("东方赛博", "赛博", "cyberpunk"), "cinematic cyberpunk CG"),
    (("商业摄影", "广告", "commercial photography"), "commercial editorial photography"),
    (("时尚编辑", "杂志", "fashion editorial"), "fashion editorial photography"),
    (("古风", "武侠", "wuxia"), "cinematic historical Chinese styling"),
    (("神话", "史诗", "mythic", "epic"), "mythic cinematic imagery"),
    (("插画", "水彩", "illustration", "watercolor"), "editorial illustration"),
    (("CG感", "电影级CG", "cinematic cg"), "cinematic CG"),
    (("真实感", "写实", "photoreal"), "photorealistic photography"),
    (("成年女性", "成熟女性"), "adult woman"),
    (("成年男性", "成熟男性"), "adult man"),
    (("女性", "女人", "woman"), "woman"),
    (("男性", "男人", "man"), "man"),
    (("机甲", "mecha"), "detailed mecha"),
    (("书店", "bookstore"), "bookstore interior"),
    (("浴室", "浴缸", "淋浴", "bathroom"), "bathroom setting"),
    (("卧室", "bedroom"), "bedroom interior"),
    (("影棚", "studio"), "controlled studio setting"),
    (("街道", "街区", "street"), "urban street setting"),
    (("森林", "竹林", "forest"), "layered forest setting"),
    (("海边", "海岸", "coast"), "coastal setting"),
    (("神殿", "temple"), "monumental temple setting"),
    (("机库", "hangar"), "industrial hangar"),
    (("霓虹", "neon"), "controlled neon lighting"),
    (("柔光", "soft light"), "soft directional light"),
    (("逆光", "backlight"), "cinematic backlight"),
    (("体积光", "volumetric light"), "volumetric lighting"),
    (("全景全身", "全身", "full body"), "wide full-body composition"),
    (("中景半身", "半身", "medium shot"), "medium portrait composition"),
    (("近景", "特写", "close-up"), "controlled close-up composition"),
    (("高细节", "high detail"), "high material detail"),
    (("清晰对焦", "sharp focus"), "clear focal hierarchy"),
)


def _english_fallback_fragments(*texts: str) -> list[str]:
    fragments: list[str] = []
    for text in texts:
        cleaned = _strip_smart_text_meta(text)
        for raw in re.split(r"[,，、;；。.!?\n]+", cleaned):
            fragment = re.sub(r"\s+", " ", raw).strip(" -_*#>:：()（）")
            if not fragment or _CJK_PATTERN.search(fragment) or not _has_substantive_english(fragment):
                continue
            if fragment.casefold() in _FALLBACK_NOISE_TERMS or fragment in fragments:
                continue
            fragments.append(fragment)
    return fragments[:8]


def _english_fallback_hints(*texts: str) -> list[str]:
    source = " ".join(str(text or "") for text in texts)
    hints: list[str] = []
    for markers, hint in _FALLBACK_ENGLISH_HINT_RULES:
        if any(_contains_marker(source, marker) for marker in markers) and hint not in hints:
            hints.append(hint)
    return hints[:8]


def _fallback_smart_text_english(
    *,
    user_text: str,
    primary_prompt: str,
    style_track: str = "",
    subject_type: str = "自动",
    adult_mode: bool = False,
) -> str:
    rich_narrative = _merge_smart_text_into_rich_narrative(
        user_text=user_text,
        primary_prompt=primary_prompt,
        english=True,
    )
    if rich_narrative:
        adult = bool(adult_mode) or looks_like_adult_request(f"{user_text} {primary_prompt}", [])
        return _normalize_english_adult_subject_terms(rich_narrative, adult=adult)
    source = f"{user_text} {primary_prompt}".strip()
    non_person = str(subject_type or "自动").strip() == "非人物主体"
    adult = bool(adult_mode) or looks_like_adult_request(source, [])
    raw_fragments = _english_fallback_fragments(user_text, primary_prompt)
    hints = _english_fallback_hints(style_track, user_text, primary_prompt)
    context_parts = list(dict.fromkeys(raw_fragments + hints))[:10]
    context = "; ".join(context_parts) or "the requested visual concept"
    style_hints = _english_fallback_hints(style_track)
    lead_style = style_hints[0] if style_hints else "A coherent cinematic image"
    if non_person:
        subject = "the main non-human subject"
        structure = "Its silhouette, structural direction, scale, surface materials, and functional details remain immediately readable."
        detail_focus = "Surface texture, structural edges, props, and environmental materials support the subject without overwhelming it."
    else:
        subject = "an explicitly adult subject" if adult else "the main subject"
        structure = "The subject stays clearly separated from the background, with readable facial direction, body proportions, and pose."
        detail_focus = "Wardrobe, hair, skin, props, and environmental materials remain distinct while supporting the expression and pose."
    prompt = (
        f"{lead_style.capitalize()} centered on {subject}, based on {context}. "
        f"{structure} The scene uses one coherent environment, one lighting plan, and a stable camera perspective with clear focal hierarchy. "
        f"{detail_focus} High material detail, controlled contrast, clean focus, and a complete subject silhouette define the final image. "
        "Related ideas are consolidated instead of repeating similar styles, settings, outfits, or camera directions."
    )
    return _normalize_english_adult_subject_terms(_strip_smart_text_meta(prompt), adult=adult)


def fallback_smart_text(
    *,
    user_text: str,
    primary_prompt: str,
    style_track: str = "",
    subject_type: str = "自动",
    language: str = "纯中文",
    adult_mode: bool = False,
) -> str:
    language_mode = _normalize_smart_text_language(language)
    common = {
        "user_text": user_text,
        "primary_prompt": primary_prompt,
        "style_track": style_track,
        "subject_type": subject_type,
        "adult_mode": adult_mode,
    }
    if language_mode == "纯英文":
        return _fallback_smart_text_english(**common)
    chinese = _fallback_smart_text_chinese(**common)
    if language_mode == "英文提示词+中文说明":
        english = _fallback_smart_text_english(**common)
        return f"{english}\n中文说明：{chinese}"
    return chinese
