# -*- coding: utf-8 -*-
"""Prompt list and formatting helpers for stage prompt generation."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable, NotRequired, TypedDict

try:  # Keep direct file loading in tests working when the package context is absent.
    from .skills import resolve_base_template_style
except Exception:  # pragma: no cover - exercised by direct import tests
    from stage_prompt_skills_test import resolve_base_template_style  # type: ignore

try:
    from ..danbooru_tag_config import DANBOORU_GENERAL_TAG_ALIASES
except Exception:  # pragma: no cover - direct file loading in focused tests
    try:
        from danbooru_tag_config import DANBOORU_GENERAL_TAG_ALIASES  # type: ignore
    except ImportError:
        import importlib.util
        from pathlib import Path

        _danbooru_spec = importlib.util.spec_from_file_location(
            "danbooru_tag_config",
            Path(__file__).resolve().parents[1] / "danbooru_tag_config.py",
        )
        if _danbooru_spec is None or _danbooru_spec.loader is None:
            raise RuntimeError("Unable to load danbooru_tag_config.py")
        _danbooru_module = importlib.util.module_from_spec(_danbooru_spec)
        _danbooru_spec.loader.exec_module(_danbooru_module)
        DANBOORU_GENERAL_TAG_ALIASES = _danbooru_module.DANBOORU_GENERAL_TAG_ALIASES


class _PersonPromptVariantProfile(TypedDict):
    label: str
    replace_shot_tags: list[str]
    extra_fragments: list[str]


class _RuntimeStyleVariantProfile(TypedDict):
    style_lead: str
    style_tags: list[str]
    extra_fragments: list[str]


class _RuntimeDiversityVariantProfile(TypedDict):
    replace_subject_tags: list[str]
    replace_scene_tags: list[str]
    replace_outfit_tags: NotRequired[list[str]]
    replace_light_tags: NotRequired[list[str]]
    replace_action_tags: NotRequired[list[str]]
    replace_prop_tags: NotRequired[list[str]]
    replace_composition_tags: NotRequired[list[str]]
    preserve_selected_subject: NotRequired[bool]
    subject_identity: str
    scene_group: str
    scene_bucket: str
    macro_direction: str
    diversity_signature: str


class _PromptBuildContext(TypedDict):
    scene_group: str
    identity: str
    style_track: str
    recent_tracks: list[str]


class _PromptFragmentItem(TypedDict):
    text: str
    priority: int
    order: int


_PROMPT_FRAGMENT_LIMIT = 32
_PROMPT_REQUIRED_PRIORITY = 94
_PROMPT_GROUP_PRIORITY = {
    "主体": 104,
    "场景背景": 100,
    "构图视角": 98,
    "成人向表达": 94,
    "服装造型": 88,
    "动作姿态": 86,
    "光影氛围": 84,
    "道具世界观": 82,
    "技术画质": 80,
    "画面风格": 78,
}
_PROMPT_TAIL_PRIORITY = {
    "lead": 120,
    "extra": 112,
    "custom": 90,
    "person_variant": 76,
    "style_variant": 74,
    "focus": 72,
}


_STYLE_LEAD_MAP = {
    "自动": "完整画面",
    "真实感": "写实摄影",
    "商业摄影": "商业摄影成片",
    "时尚编辑": "时尚编辑摄影",
    "电影写实": "电影写实剧照",
    "私房写实": "私房写实摄影",
    "插画感": "高完成度插画",
    "复古动画": "复古动画定帧",
    "CG感": "电影级CG",
    "东方赛博": "东方赛博CG",
    "硬表面科幻": "硬表面科幻CG",
    "古风": "古风人像",
    "国风电影": "国风电影剧照",
    "武侠电影": "武侠电影剧照",
    "神话感": "神话史诗感",
    "暗黑奇幻": "暗黑奇幻史诗",
}
_STYLE_LEAD_MAP_EN = {
    "自动": "coherent finished image",
    "真实感": "realistic photography",
    "商业摄影": "commercial photography campaign",
    "时尚编辑": "fashion editorial photography",
    "电影写实": "cinematic realistic still",
    "私房写实": "intimate realistic photography",
    "插画感": "highly finished illustration",
    "复古动画": "retro animation key visual",
    "CG感": "cinematic CG render",
    "东方赛博": "oriental cyber cinematic CG",
    "硬表面科幻": "hard-surface sci-fi CG render",
    "古风": "oriental historical portrait",
    "国风电影": "Chinese period cinematic still",
    "武侠电影": "wuxia cinematic still",
    "神话感": "mythic epic fantasy",
    "暗黑奇幻": "dark fantasy epic",
}


def _has_auto_style_signal(
    selected: OrderedDict[str, list[str]],
    *,
    style: str,
    style_track: str,
) -> bool:
    inferred_style = _clean_fragment(style)
    if inferred_style and inferred_style not in {"自动", "真实感"}:
        return True
    if _clean_fragment(style_track):
        return True
    return any(
        _clean_fragment(tag) and _clean_fragment(tag) != "自动"
        for tag in selected.get("画面风格", [])
    )


def _resolve_prompt_style_lead(
    selected: OrderedDict[str, list[str]],
    *,
    explicit_template_style: str,
    inferred_style: str,
    style_track: str,
    english_prompt: bool,
) -> str:
    style_lead_map = _STYLE_LEAD_MAP_EN if english_prompt else _STYLE_LEAD_MAP
    fallback = "highly finished image" if english_prompt else "高完成度图像"
    explicit_style = _clean_fragment(explicit_template_style)
    inferred = _clean_fragment(inferred_style)

    if explicit_style and explicit_style != "自动":
        return style_lead_map.get(explicit_style, style_lead_map.get(inferred, fallback))

    if _has_auto_style_signal(selected, style=inferred, style_track=style_track):
        return style_lead_map.get(inferred, style_lead_map.get("自动", fallback))

    return style_lead_map.get("自动", fallback)


_PROMPT_LANGUAGE_ENGLISH_MODES = {"纯英文", "英文提示词+中文说明"}
_PROMPT_FRAGMENT_TRANSLATION_MAP = {
    "完整画面": "coherent finished image",
    "自然写实图像": "natural realistic image",
    "写实摄影": "realistic photography",
    "高完成度插画": "highly finished illustration",
    "电影级CG": "cinematic CG render",
    "古风人像": "oriental historical portrait",
    "神话史诗感": "mythic epic fantasy",
    "成年人物主体": "adult human subject",
    "成年女性": "adult woman",
    "成年男性": "adult man",
    "东亚": "East Asian",
    "成熟": "mature",
    "轻熟感": "mature elegant aura",
    "清冷": "cool reserved expression",
    "甜美": "sweet expression",
    "优雅": "elegant",
    "真实感": "photorealistic",
    "照片级": "photorealistic",
    "时尚写真": "fashion portrait",
    "杂志感": "editorial magazine look",
    "商业写真": "commercial portrait photography",
    "私房写真": "boudoir photography",
    "成人向": "adult-oriented",
    "暧昧": "sensual mood",
    "卧室": "bedroom",
    "豪华卧室": "luxury bedroom",
    "酒店套房": "hotel suite",
    "落地窗夜景": "night city view through floor-to-ceiling windows",
    "摄影棚": "photo studio",
    "影棚纯色背景": "clean studio backdrop",
    "街道": "street",
    "海边": "seaside",
    "黄昏": "dusk",
    "校园": "campus",
    "教室": "classroom",
    "神殿": "temple",
    "宫殿": "palace",
    "机库": "hangar",
    "未来都市": "futuristic city",
    "卧室落地窗夜景": "bedroom with floor-to-ceiling night city view",
    "中景": "medium shot",
    "中景半身": "medium half-body shot",
    "近景": "close-up shot",
    "近景半身": "close half-body shot",
    "半身": "half-body shot",
    "全身": "full-body shot",
    "全景全身": "wide full-body shot",
    "面部特写": "facial close-up",
    "面部聚焦": "face-focused composition",
    "镜头近距离": "close camera distance",
    "环境人像": "environmental portrait",
    "平视": "eye-level view",
    "低角度": "low angle",
    "广角": "wide-angle lens",
    "标准镜头": "standard lens",
    "50mm标准镜头": "50mm standard lens",
    "85mm人像镜头": "85mm portrait lens",
    "中心构图": "centered composition",
    "三分法": "rule-of-thirds composition",
    "浅景深": "shallow depth of field",
    "柔光": "soft light",
    "自然光": "natural light",
    "简洁室内": "simple interior",
    "站姿挺拔": "upright standing pose",
    "逆光": "backlight",
    "侧光": "side light",
    "侧逆光": "side backlight",
    "轮廓光": "rim light",
    "体积光": "volumetric light",
    "暖色调": "warm color tone",
    "冷色调": "cool color tone",
    "低饱和": "low saturation",
    "电影调色": "cinematic color grading",
    "胶片感": "film look",
    "高动态范围": "high dynamic range",
    "皮肤纹理": "natural skin texture",
    "清透肌肤": "clear translucent skin",
    "空气感奶油肌": "soft airy creamy skin",
    "冷白皮": "cool fair skin tone",
    "真实发丝": "realistic hair strands",
    "黑长直": "long straight black hair",
    "银白长发": "long silver-white hair",
    "短碎发": "short layered hair",
    "中分短发": "center-parted short hair",
    "高马尾": "high ponytail",
    "白衬衫": "white shirt",
        "修身礼服": "tailored evening dress",
        "深灰丝绒礼服": "dark gray velvet gown",
        "丝质睡袍": "silk robe",
        "吊带睡裙": "slip dress",
        "露背礼服": "backless gown",
        "浴袍": "bathrobe",
    "浴巾裹身": "wrapped bath towel",
    "服装褶皱真实": "realistic clothing folds",
    "材质细节丰富": "rich material details",
    "主体突出": "clear subject emphasis",
    "空间层次明确": "clear spatial depth",
    "场景空间层次明确": "clear scene depth",
    "面部与主体关系清晰": "clear relationship between face and subject",
    "服装结构与材质层次清晰": "clear clothing structure and material layers",
    "姿态自然，镜头透视稳定": "natural pose with stable camera perspective",
    "主体轮廓清晰": "clear subject silhouette",
    "材质结构关系明确": "clear material and structural relationship",
    "环境衬托克制": "restrained environmental support",
    "光影体积关系稳定": "stable light volume relationship",
    "脸部表情与妆发细节优先": "prioritize facial expression, makeup, and hair details",
    "面部作为第一视觉中心": "face as the primary visual focus",
    "服装版型与材质层次优先": "prioritize clothing silhouette and material layering",
    "肩颈与上半身结构清晰": "clear shoulder, neck, and upper-body structure",
    "人物与场景比例自然": "natural scale between subject and environment",
    "环境空间关系完整": "complete environmental spatial relationship",
    "动作起伏自然": "natural motion rhythm",
    "手部与肢体关系稳定": "stable hand and limb relationship",
    "高细节": "high detail",
    "杰作": "masterpiece",
    "最佳质量": "best quality",
    "锐利焦点": "sharp focus",
    "无文字": "no text",
    "无水印": "no watermark",
    "无logo": "no logo",
    "8K": "8K",
    "raw photo": "raw photo",
    "masterpiece": "masterpiece",
    "best quality": "best quality",
}
_PROMPT_FRAGMENT_TRANSLATION_MAP.update(
    {
        "高完成度图像": "highly finished image",
        "35mm胶片摄影": "35mm film photograph",
        "大画幅棚拍": "large-format studio photo",
        "大片级棚拍": "blockbuster-grade studio photography",
        "纪实电影摄影": "documentary cinematic photography",
        "港式武侠": "Hong Kong wuxia cinema style",
        "东方古风武侠": "oriental wuxia cinema",
        "都市电影人文": "urban cinematic humanism",
        "时尚编辑商业广告": "fashion editorial commercial campaign",
        "高端时尚编辑肖像": "high-fashion editorial portrait",
        "日韩影像": "Japanese-Korean cinematic imagery",
        "日系电影感": "Japanese cinematic mood",
        "韩系极简影像": "Korean minimalist visual styling",
        "生活流写实": "slice-of-life realism",
        "水粉插画": "gouache illustration",
        "墨洗留白": "ink wash with negative space",
        "中近景": "medium close-up shot",
        "全景": "wide shot",
        "远景": "long shot",
        "大远景": "extreme wide shot",
        "85mm人像镜头": "85mm portrait lens",
        "生活电影剧照": "lifestyle cinematic still",
        "夜间闪光摄影": "night flash photography",
        "纪实抓拍": "documentary candid photography",
        "杂志编辑摄影": "editorial magazine photography",
        "电影剧照": "cinematic still",
        "古风电影剧照": "oriental historical cinematic still",
        "古风电影氛围": "ancient Chinese cinematic atmosphere",
        "港风惊悚志怪": "Hong Kong supernatural thriller mood",
        "港风恐怖电影调": "Hong Kong horror cinema color mood",
        "欧美风": "western editorial style",
        "西方奇幻史诗": "western fantasy epic",
        "公主": "princess",
        "盘发": "updo hairstyle",
        "清贵": "refined noble aura",
        "高智感": "intelligent refined aura",
        "冷艳": "cool alluring aura",
        "英气": "heroic bearing",
        "空灵": "ethereal aura",
        "庄严": "solemn aura",
        "神秘": "mysterious aura",
        "冷静": "calm restrained aura",
        "国潮模特": "fashion model from Chinese chic styling",
        "偶像": "idol",
        "摄影师": "photographer",
        "调酒师": "bartender",
        "书店女孩": "bookstore girl",
        "湖畔金发女性": "blonde woman by the lakeside",
        "潮女模特": "trend-forward fashion model",
        "影棚时尚女性": "studio fashion woman",
        "居家游戏女孩": "homebody gamer girl",
        "学生": "student",
        "医生": "doctor",
        "律师": "lawyer",
        "研究员": "researcher",
        "女武士": "female warrior",
        "神女": "goddess",
        "祭司": "priestess",
        "魔女": "sorceress",
        "女冒险者": "female adventurer",
        "神圣骑士": "holy knight",
        "冰霜骑士": "frost knight",
        "炎魔天使": "infernal angel",
        "敦煌神性": "Dunhuang-inspired divine aesthetic",
        "时尚街拍": "fashion street photography",
        "街拍": "street photography",
        "私密氛围": "intimate private atmosphere",
        "生活纪实": "documentary lifestyle photography",
        "亲密感更强": "stronger intimate mood",
        "人物状态更偏私密叙事": "more private narrative character state",
        "落地窗轻私房": "soft boudoir by a floor-to-ceiling window",
        "浴缸蒸汽私房": "steamy bathtub boudoir",
        "浴后蒸汽浴室": "steamy bathroom after bathing",
        "浴缸": "bathtub",
        "浴室": "bathroom",
        "酒吧": "bar",
        "夜店": "nightclub",
        "温泉雾气": "hot spring steam",
        "高窗冷天光": "cool skylight from a high window",
        "冷雾惊悚侧光": "cold-fog thriller sidelight",
        "黄金时刻侧光": "golden-hour side-light",
        "阴天柔散光": "overcast softbox diffusion",
        "黑色电影硬光": "hard noir key-light",
        "暖色轮廓逆光": "warm rim light from behind",
        "烛火暖光": "candlelit warm glow",
        "冷荧顶光": "cold fluorescent overhead light",
        "叶隙斑驳光": "dappled light through leaves",
        "体积神光": "volumetric god rays",
        "蓝灰月光": "blue-grey moonlight",
        "冷静": "cool composed aura",
        "慵懒感": "languid relaxed aura",
        "灵动": "lively agile aura",
        "温柔": "gentle aura",
        "迷离": "dreamy intoxicated aura",
        "内衣风": "lingerie-inspired styling",
        "逆光剪影全裸": "backlit nude silhouette",
        "白色斗篷": "white cloak",
        "黑金重甲": "black-and-gold heavy armor",
        "银白雕花重甲": "silver-white engraved heavy armor",
        "神官长袍": "high priest ceremonial robe",
        "鎏金头冠": "gilded ceremonial crown",
        "飞鱼服": "flying fish robe",
        "宽袖法袍": "wide-sleeved ceremonial robe",
        "劲装": "martial outfit",
        "宋制": "Song-dynasty-inspired clothing",
        "回廊": "covered corridor",
        "影棚纯色背景": "clean studio backdrop",
        "独立书店": "independent bookstore",
        "图书馆": "library",
        "咖啡厅": "cafe",
        "画室": "art studio",
        "雨后街头": "street after rain",
        "古风建筑": "classical Chinese architecture",
        "宗教圣所": "religious sanctuary",
        "赛博街区": "cyberpunk street district",
        "霓虹街区": "neon district",
        "工业废墟": "industrial ruins",
        "北欧海岸": "Nordic coast",
        "冰冻森林": "frozen forest",
        "黑铁王座": "black iron throne",
        "火山洞穴": "volcanic cave",
        "云端阶梯": "stairway above the clouds",
        "古建道场": "ancient training hall",
        "月下庭院": "moonlit courtyard",
        "云海": "sea of clouds",
        "神圣祭坛": "sacred altar",
        "星海神殿": "star-sea temple",
        "悬空神庙": "suspended sky temple",
        "东方赛博机甲": "oriental cyber mecha aesthetic",
        "东方赛博武侠朋克": "oriental cyber wuxia punk",
        "幽暗竹林": "dim bamboo grove",
        "废弃地下老屋": "abandoned underground old house",
        "雨夜站台": "rainy night platform",
        "极简白棚": "minimal white studio set",
        "玫瑰粉调": "rose-pink color tone",
        "高调粉彩": "high-key pastel palette",
        "低饱和冷灰": "desaturated cool grey palette",
        "暖褐单色": "warm sepia monochrome",
        "酸性霓虹黑": "acid neon on black",
        "宝石色调": "jewel-tone palette",
        "双双色调": "limited two-color duotone",
        "晒褪色调": "sun-bleached faded palette",
        "墨黑单色点缀": "ink-black palette with single accent",
        "青橙电影色调": "teal-and-orange cinematic palette",
        "红雾表现主义打光": "red-mist expressionist lighting",
        "青蓝冷雾": "blue-cyan cold mist",
        "冷白极简棚拍": "cold-white minimalist studio lighting",
        "暖褪色胶片": "warm faded film palette",
        "高饱和": "high saturation",
        "慵懒": "languid mood",
        "四联画构图": "four-panel composition",
        "俯视平铺": "top-down flat-lay composition",
        "荷兰式倾斜": "dutch tilt composition",
        "过肩镜头": "over-the-shoulder framing",
        "微距特写": "macro close-up shot",
        "200mm长焦压缩": "200mm long-lens compression",
        "变形宽银幕": "anamorphic widescreen framing",
        "持刀回身": "turning back while holding a blade",
        "扶剑而立": "standing with a sword in hand",
        "手持相机": "holding a camera",
        "回眸": "looking back over the shoulder",
        "倚靠栏杆": "leaning against a railing",
        "低头浅笑": "lowering the gaze with a faint smile",
        "双手负后": "hands clasped behind the back",
        "手持相机": "holding a camera",
        "轻拈发梢": "lightly twirling a strand of hair",
        "拈花而立": "standing while holding a flower",
        "侧坐回眸": "side-seated glance back",
        "抬头仰望": "looking upward",
        "伸手触碰": "reaching out to touch",
        "城市屋顶纪实": "urban rooftop documentary mood",
        "城市天台": "city rooftop",
        "屋顶晾衣架": "rooftop clothesline frame",
        "通勤女孩": "commuter girl",
        "日落逆光": "sunset backlight",
        "金色侧逆光": "golden rim sidelight",
        "有线耳机": "wired earphones",
        "侧脸构图": "profile composition",
        "山谷圣城": "holy city in a mountain valley",
        "巨构神殿": "megastructure temple",
        "瀑布峡谷": "waterfall canyon",
        "远山雪峰": "snow peaks in the far distance",
        "史诗城市中轴": "epic city central axis",
        "山体建筑一体化": "mountain-integrated architecture",
        "中轴对称巨构": "axial symmetric megastructure framing",
        "超广角全景": "ultra-wide panoramic framing",
        "树灵巨像": "colossal tree spirit",
        "古木守卫": "ancient wood guardian",
        "藤蔓木妖": "vinebound wood fiend",
        "工业舱室": "industrial chamber",
        "巨物压迫近景": "intimidating colossal close shot",
        "朽木树皮纹理": "rotted bark texture",
        "苔藓附生质感": "moss-covered overgrowth texture",
        "发光裂隙": "glowing fissures",
        "锐利": "crisp sharp rendering",
        "义体金属细节": "cybernetic metallic details",
        "BJD娃娃质感": "BJD doll-like texture finish",
        "复古颗粒": "retro grain texture",
        "雾景实拍感": "misty live-action atmosphere",
        "写实真人质感": "lifelike live-action realism",
        "电影胶片look": "cinematic film look",
        "游戏CG质感": "AAA game CG finish",
        "复古非镀膜镜头": "vintage uncoated glass lens",
        "RGB轻微分离": "subtle RGB split",
        "轻微色差": "slight chromatic aberration",
        "柔和光晕": "soft halation",
        "老胶片褪色感": "faded old-film patina",
        "港片胶片质感": "Hong Kong wuxia film stock look",
        "湿发": "wet hair",
        "长款大衣": "long overcoat",
        "风衣": "trench coat",
        "奶油针织": "cream knitwear",
        "丝质睡袍氛围": "silk robe atmosphere",
        "微醺": "slightly tipsy mood",
        "低遮挡": "low-cover styling",
        "遮挡最小化": "minimal coverage",
        "无遮挡感": "unobstructed silhouette",
        "少遮挡": "low coverage",
        "弱遮挡": "light coverage",
        "身体轮廓清晰": "clear body silhouette",
        "角色设定图": "character sheet",
        "角色三视图": "multi-view character turnaround",
        "多视角角色展示": "multi-view character turnaround",
        "头像特写": "headshot close-up",
        "正面视图": "front view",
        "侧面视图": "side view",
        "背面视图": "back view",
        "正面全身": "front full-body view",
        "侧面全身": "side full-body view",
        "背面全身": "back full-body view",
        "服装结构完整": "complete outfit construction",
        "发型结构完整": "complete hairstyle structure",
        "发型轮廓清晰": "clear hairstyle silhouette",
        "材质层次明确": "readable material layers",
        "同一角色一致": "consistent character identity across every view",
        "无文字标注": "no text labels",
        "参考图一致性": "reference-image character consistency",
        "纯提示词角色设计": "prompt-only character design",
        "轮廓": "silhouette",
        "开放感": "open composition",
        "NSFW": "NSFW",
        "女仆": "maid",
        "丝绒床单": "velvet bed sheets",
        "镜面天花板": "mirrored ceiling",
        "红色丝绒床单": "red velvet bed sheets",
        "豪华卧室，红色丝绒床单，镜面天花板": "luxury bedroom with red velvet bed sheets and a mirrored ceiling",
        "人物更像特工题材影片定格主角": "the subject feels like the frozen-frame lead in an agent film",
        "任务叙事感更强": "stronger mission narrative feeling",
        "行动现场感更强": "stronger on-site action feeling",
        "人物更像夜间任务中的主角": "the subject feels like the lead of a night mission",
        "隐蔽行动感更强": "stronger covert operation feeling",
        "人物更像任务间隙的真实瞬间": "the subject feels like a real moment between missions",
        "冷静控制感更强": "stronger calm sense of control",
        "人物更偏角色企划封面": "the subject leans toward a character concept cover",
        "舞台感染力更强": "stronger stage presence",
        "人物更像演出主视觉主角": "the subject feels like the main visual of a performance",
        "镜头表现欲更强": "stronger camera presence",
        "人物更像企划封面主角": "the subject feels like a planning-cover lead",
        "青春感更自然": "more natural youthful feeling",
        "表情与姿态更轻盈": "lighter expression and pose",
        "职业干练感更明确": "clearer professional competence",
        "人物更像都市职场主角": "the subject feels like an urban workplace lead",
        "场域掌控感更强": "stronger control of the scene",
        "人物更像夜场叙事主角": "the subject feels like the lead of a nightlife narrative",
        "理性探索感更明确": "clearer rational exploratory feeling",
        "人物更像实验专题主角": "the subject feels like the lead of an experimental feature",
        "英气更明确": "clearer heroic bearing",
        "人物姿态更偏战斗定妆": "the pose leans toward a combat character still",
        "神性表达更明确": "clearer divine expression",
        "人物气场更稳定": "more stable character presence",
        "统御感更明确": "clearer commanding aura",
        "人物更像王权叙事中心": "the subject feels like the center of a royal narrative",
        "神秘压迫感更强": "stronger mysterious pressure",
        "人物更像异术叙事主角": "the subject feels like an occult narrative lead",
        "观察者气质更强": "stronger observer temperament",
        "画面更像创作者人物专题": "the image feels like a creator-focused portrait feature",
        "技术职业感更明确": "clearer technical profession identity",
        "人物更像工业角色主角": "the subject feels like an industrial character lead",
        "专业可信度更强": "stronger professional credibility",
        "人物更像医疗人物专题主角": "the subject feels like the lead of a medical portrait feature",
        "理性气场更明确": "clearer rational aura",
        "人物更像律政主题主角": "the subject feels like a legal-drama lead",
        "仪式指向更清晰": "clearer ritual direction",
        "人物更像祭典叙事中心": "the subject feels like the center of a ceremonial narrative",
        "任务紧张感更强": "stronger mission tension",
        "人物更像行动中的主角": "the subject feels like a lead in action",
        "角色张力更强": "stronger character tension",
        "姿态更偏角色定妆": "the pose leans toward a character still",
        "仪式感表达更明确": "clearer ceremonial feeling",
        "职业设定更清晰": "clearer professional setup",
        "画面更像人物主题企划": "the image feels like a character-themed feature",
    }
)
_PROMPT_FRAGMENT_TRANSLATION_MAP.update(
    {
        "商业摄影成片": "commercial photography campaign",
        "时尚编辑摄影": "fashion editorial photography",
        "电影写实剧照": "cinematic realistic still",
        "私房写实摄影": "intimate realistic photography",
        "复古动画定帧": "retro animation key visual",
        "东方赛博CG": "oriental cyber cinematic CG",
        "硬表面科幻CG": "hard-surface sci-fi CG render",
        "国风电影剧照": "Chinese period cinematic still",
        "武侠电影剧照": "wuxia cinematic still",
        "暗黑奇幻史诗": "dark fantasy epic",
        "商业广告大片": "commercial advertising campaign",
        "品牌大片": "brand campaign image",
        "产品广告": "product advertising image",
        "高级定制大片": "haute couture editorial campaign",
        "胶片时装片": "film fashion editorial",
        "黑色电影感": "film noir mood",
        "纪实电影摄影": "documentary cinematic photography",
        "胶片私房": "intimate film photography",
        "高级私房": "elevated intimate photography",
        "复古动画": "retro animation",
        "90年代复古未来动漫": "1990s retro-futurist anime",
        "硬表面科幻": "hard-surface sci-fi",
        "工业科幻": "industrial sci-fi",
        "太空歌剧": "space opera",
        "古风电影氛围": "Chinese period cinematic atmosphere",
        "武侠电影感": "wuxia cinematic mood",
        "水墨武侠": "ink-wash wuxia",
        "暗黑奇幻": "dark fantasy",
        "巫术暗黑": "occult dark fantasy",
        "冷冽神性": "cold divine atmosphere",
        "商业棚拍主视觉": "commercial studio key visual",
        "品牌campaign影像": "brand campaign image",
        "产品级材质表达": "product-grade material presentation",
        "Lookbook版型展示": "lookbook silhouette presentation",
        "极简商品目录感": "minimal catalog mood",
        "商业站姿": "commercial standing pose",
        "产品广告主视觉": "product advertising key visual",
        "金属展台广告": "metal display advertising setup",
        "物料质感广告": "material-focused advertising image",
        "主刊封面企划": "main magazine cover concept",
        "高级编辑片": "high-end editorial feature",
        "时装专题视觉": "fashion feature visual",
        "高级定制服装企划": "haute couture feature concept",
        "高定campaign影像": "couture campaign image",
        "主刊时装叙事": "main magazine fashion narrative",
        "胶片时装专题": "film fashion feature",
        "时装片颗粒": "fashion film grain",
        "编辑部胶片感": "editorial film texture",
        "写实电影定格": "realistic cinematic still",
        "剧情片场瞬间": "narrative set moment",
        "叙事镜头": "narrative shot",
        "冷硬黑片光影": "cold hard noir lighting",
        "夜色悬疑剧照": "night suspense film still",
        "暗部层次": "layered shadow detail",
        "纪实片场摄影": "documentary set photography",
        "长镜头生活感": "long-take slice-of-life feeling",
        "克制低饱和电影": "restrained low-saturation cinema",
        "室内亲密写实": "intimate indoor realism",
        "窗纱私密光线": "private sheer-curtain light",
        "柔和居家氛围": "soft home atmosphere",
        "复古公寓私房": "retro apartment intimate scene",
        "暖胶片室内": "warm film indoor tone",
        "安静室内颗粒": "quiet indoor film grain",
        "高级室内私房": "elevated indoor intimate scene",
        "低饱和亲密影像": "low-saturation intimate image",
        "克制肤色质感": "restrained skin-tone texture",
        "怀旧赛璐璐定帧": "nostalgic cel-animation still",
        "旧动画主视觉": "vintage animation key visual",
        "手绘动画色块": "hand-drawn animation color blocks",
        "番剧定帧颗粒": "anime still grain",
        "复古低保真动画": "retro lo-fi animation",
        "旧时代角色卡": "old-era character card",
        "霓虹复古动画海报": "neon retro animation poster",
        "旧科幻动画感": "vintage sci-fi animation mood",
        "动画海报构图": "animation poster composition",
        "东方赛博主视觉": "oriental cyber key visual",
        "武侠朋克城市": "wuxia-punk city",
        "赛博东方器物": "cyber oriental artifacts",
        "东方装甲角色": "oriental armored character",
        "机械经络结构": "mechanical meridian structure",
        "赛博金属服饰": "cyber metal clothing",
        "霓虹雨巷任务感": "neon rainy alley mission mood",
        "湿地面广告反射": "wet pavement ad reflections",
        "城市全息纵深": "urban holographic depth",
        "硬表面科幻主视觉": "hard-surface sci-fi key visual",
        "工业外壳结构": "industrial shell structure",
        "机械材质层次": "layered mechanical materials",
        "科幻棚景工业光": "industrial light on a sci-fi set",
        "冷调设备空间": "cool-toned equipment space",
        "工程舱室质感": "engineering compartment texture",
        "星舰走廊史诗": "epic starship corridor",
        "宇航装备主视觉": "space gear key visual",
        "深空尺度感": "deep-space sense of scale",
        "国风片场定格": "Chinese period set still",
        "礼制空间叙事": "ritual spatial narrative",
        "古装电影主视觉": "period-film key visual",
        "宋韵园林镜头": "Song-inspired garden shot",
        "庭院纸窗气韵": "courtyard paper-window atmosphere",
        "雅致衣冠秩序": "elegant clothing hierarchy",
        "设色华服电影感": "cinematic colored ceremonial attire",
        "东方纹样叙事": "oriental pattern narrative",
        "古典海报设色": "classical poster color design",
        "江湖电影定格": "jianghu cinematic still",
        "刀剑出场动势": "sword-drawn entrance motion",
        "侠客主视觉": "wuxia hero key visual",
        "老港武行镜头": "old Hong Kong wuxia action shot",
        "屋檐雨夜江湖": "rainy eaves jianghu night",
        "胶片江湖气": "film-grain jianghu mood",
        "留白侠影构图": "wuxia silhouette composition with negative space",
        "衣袍风势线": "wind-swept robe motion lines",
        "远山武侠意境": "distant mountain wuxia atmosphere",
        "暗黑史诗主视觉": "dark epic key visual",
        "黑铁王座氛围": "black iron throne atmosphere",
        "戏剧烛火阴影": "dramatic candlelit shadows",
        "秘仪黑暗叙事": "occult dark narrative",
        "咒术圣坛气场": "ritual altar aura",
        "符器阴影空间": "shadowed talismanic space",
        "霜雾暗黑神殿": "frost-fog dark temple",
        "冷辉命运感": "cold luminous sense of fate",
        "冰裂圣域气息": "ice-cracked sanctuary atmosphere",
    }
)
_PROMPT_FRAGMENT_TRANSLATION_MAP.update(
    {
        "鹅蛋脸": "oval face",
        "瓜子脸": "slender V-shaped face",
        "圆脸": "round face",
        "方脸": "square face",
        "小巧下巴": "delicate chin",
        "清晰下颌线": "defined jawline",
        "高颧骨": "high cheekbones",
        "脸部轮廓柔和": "soft facial contour",
        "面部轮廓清晰": "clear facial contour",
        "大眼睛": "large eyes",
        "杏眼": "almond eyes",
        "丹凤眼": "phoenix eyes",
        "高鼻梁": "high nose bridge",
        "小巧鼻尖": "delicate nose tip",
        "鼻梁挺直": "straight nose bridge",
        "鼻翼精致": "refined nostrils",
        "饱满嘴唇": "full lips",
        "薄唇": "thin lips",
        "唇峰明显": "defined cupid's bow",
        "唇珠明显": "defined lip bead",
        "酒窝": "dimples",
        "泪痣": "tear mole",
        "眉形清晰": "clear eyebrow shape",
        "眉峰明显": "defined brow peak",
        "卧蚕明显": "defined under-eye puff",
        "眼尾上挑": "upturned eye corners",
        "眼距适中": "balanced eye spacing",
        "眼型清晰": "distinct eye shape",
        "浅笑": "gentle smile",
        "微笑": "smile",
        "嘴角微扬": "slight smile",
        "笑不露齿": "smile without showing teeth",
        "冷眼凝视": "cold stare",
        "温柔注视": "gentle gaze",
        "迷离眼神": "distant hazy gaze",
        "倔强眼神": "stubborn gaze",
        "若有所思": "thoughtful expression",
        "回眸眼神": "looking back over the shoulder",
        "平静神情": "calm expression",
        "欲感眼神": "sensual gaze",
        "坚定眼神": "determined gaze",
        "凌厉眼神": "sharp intense gaze",
        "含情脉脉": "affectionate gaze",
        "轻微皱眉": "slight frown",
        "眼神放空": "vacant gaze",
        "裸妆": "bare-face makeup",
        "淡妆": "light makeup",
        "浓妆": "heavy makeup",
        "红唇": "red lips",
        "烟熏妆": "smoky makeup",
        "冷艳妆": "cool glamorous makeup",
        "元气妆": "fresh lively makeup",
        "清透底妆": "clear foundation",
        "豆沙唇": "rosewood lips",
        "橘调唇妆": "orange-toned lip makeup",
        "雾面妆": "matte makeup",
        "光泽唇": "glossy lips",
        "裸色唇": "nude lips",
        "眼线清晰": "defined eyeliner",
        "腮红自然": "natural blush",
        "腮红位置清晰": "clearly placed blush",
        "眼影层次分明": "defined eyeshadow layers",
        "高光提亮": "highlighted cheekbones",
        "修容自然": "natural contouring",
        "真丝": "silk fabric",
        "蕾丝": "lace fabric",
        "针织开衫": "knitted cardigan",
        "皮革": "leather",
        "透明薄纱": "sheer tulle",
        "天鹅绒": "velvet",
        "棉质衬衫": "cotton shirt",
        "粗花呢": "tweed fabric",
        "哑光陶瓷": "matte ceramic",
        "拉丝铝材": "brushed aluminium",
        "风化木纹": "weathered oak grain",
        "手吹玻璃": "hand-blown glass",
        "粗粝混凝土": "raw concrete",
        "旧皮革": "worn leather",
        "湿沥青反光": "wet asphalt reflections",
        "磨砂亚克力": "frosted acrylic",
        "锤纹黄铜": "hammered brass",
        "亚麻织纹": "linen weave",
        "层叠领口": "layered neckline",
        "露肩设计": "off-shoulder design",
        "高领结构": "turtleneck structure",
        "短外套": "cropped jacket",
        "长外套": "long coat",
        "机能外套": "functional techwear jacket",
        "战术服": "tactical outfit",
        "开衩设计": "slit design",
        "高马尾": "high ponytail",
        "低马尾": "low ponytail",
        "双马尾": "twin tails",
        "麻花辫": "braid hairstyle",
        "双麻花辫": "double braids",
        "羊毛卷": "permed curls",
        "短卷发": "short curly hair",
        "长卷发": "long curly hair",
        "法式刘海": "french bangs",
        "龙须刘海": "face-framing side strands",
        "耳环": "earrings",
        "耳坠": "drop earrings",
        "耳夹": "ear cuffs",
        "项链": "necklace",
        "锁骨链": "choker necklace",
        "戒指": "ring",
        "手表": "wristwatch",
        "眼镜": "glasses",
        "太阳镜": "sunglasses",
        "发夹": "hair clip",
        "发卡": "barrette",
        "发簪": "hairpin",
        "发绳": "hair tie",
        "发圈": "hair scrunchie",
        "发带": "headband",
        "发箍": "hair hoop",
        "帽子": "hat",
        "贝雷帽": "beret",
        "棒球帽": "baseball cap",
        "鸭舌帽": "cap",
        "墨镜": "sunglasses",
        "珍珠耳环": "pearl earrings",
        "耳钉": "stud earrings",
        "耳骨夹": "ear cuff",
        "手链": "bracelet",
        "手镯": "bangle",
        "胸针": "brooch",
        "项圈": "choker",
        "围巾": "scarf",
        "丝巾": "silk scarf",
        "腰带": "belt",
        "手提包": "handbag",
        "托特包": "tote bag",
        "斜挎包": "crossbody bag",
        "单肩包": "shoulder bag",
        "景深控制稳定": "stable depth of field control",
        "焦点落在面部": "focus placed on the face",
        "边缘干净": "clean edges",
        "背景不过分抢镜": "background does not steal focus",
        "短发": "short hair",
        "齐肩短发": "shoulder-length short hair",
        "锁骨发": "collarbone-length hair",
        "中长发": "medium-long hair",
        "长发": "long hair",
        "及腰长发": "waist-length long hair",
        "超长发": "extra-long hair",
        "波波头": "bob haircut",
        "齐耳短发": "ear-length short hair",
        "层次短发": "layered short hair",
        "狼尾发": "wolf cut hair",
        "姬发式": "hime cut",
        "公主切长发": "long hime cut",
        "蓬松卷发": "voluminous curly hair",
        "大波浪长发": "long wavy hair",
        "自然直发": "natural straight hair",
        "微卷发": "slightly wavy hair",
        "凌乱发丝": "messy hair strands",
        "贴脸碎发": "face-framing wisps",
        "空气刘海": "airy bangs",
        "斜刘海": "side-swept bangs",
        "八字刘海": "curtain bangs",
        "眉上刘海": "short bangs above the eyebrows",
        "无刘海": "no bangs",
        "中分": "middle part",
        "侧分": "side part",
        "偏分": "off-center part",
        "露额发型": "forehead-revealing hairstyle",
        "黑发": "black hair",
        "棕发": "brown hair",
        "栗色头发": "chestnut hair",
        "金发": "blonde hair",
        "银发": "silver hair",
        "白发": "white hair",
        "灰发": "gray hair",
        "红发": "red hair",
        "紫发": "purple hair",
        "青发": "teal hair",
        "茶棕发": "tea brown hair",
        "粉色头发": "pink hair",
        "蓝黑发": "blue-black hair",
        "挑染发": "highlighted hair",
        "渐变发色": "gradient hair color",
        "肩颈线条清晰": "clear shoulder and neck lines",
        "直角肩": "squared shoulders",
        "长颈": "long neck",
        "窄腰": "narrow waist",
        "长腿": "long legs",
        "腿部修长": "slender legs",
        "腰臀曲线自然": "natural waist-to-hip curve",
        "骨架轻盈": "light frame",
        "肩宽适中": "balanced shoulders",
        "锁骨明显": "defined collarbones",
        "头身比例自然": "natural head-to-body proportion",
        "姿态舒展": "relaxed open posture",
        "头肩像": "head-and-shoulders portrait",
        "腰部以上构图": "waist-up framing",
        "膝上构图": "above-the-knee framing",
        "全身留白": "full-body framing with breathing room",
        "脚部完整入镜": "feet fully in frame",
        "人物完整入镜": "entire subject fully in frame",
        "脸部第一视觉中心": "face as the primary visual focus",
        "上半身完整": "complete upper-body framing",
        "环境比例适中": "balanced subject-to-environment ratio",
        "人物居中": "centered subject",
        "负空间留白": "negative space breathing room",
        "纵向构图": "vertical composition",
        "海报主视觉": "poster-style hero framing",
        "眼平视角": "eye-level angle",
        "轻微俯拍": "slight high angle",
        "轻微仰拍": "slight low angle",
        "长焦压缩透视": "telephoto compression perspective",
        "自然透视": "natural perspective",
        "背景轻微虚化": "slightly blurred background",
        "浅景深": "shallow depth of field",
        "镜头近距离": "close camera distance",
        "35mm镜头": "35mm lens",
        "50mm标准镜头": "50mm standard lens",
        "85mm人像镜头": "85mm portrait lens",
        "手扶栏杆": "hand resting on a railing",
        "双手插袋": "both hands in pockets",
        "手拿包": "holding a bag",
        "撩头发": "brushing hair aside",
        "扶眼镜": "adjusting glasses",
        "指尖触脸": "fingertips touching the face",
        "手撑桌面": "hands resting on a tabletop",
        "自然垂手": "hands hanging naturally",
        "手部姿态自然": "natural hand pose",
        "托腮": "chin resting on hand",
        "托下巴": "chin resting on hand",
        "单手扶腰": "one hand on the waist",
        "双手抱臂": "arms crossed",
        "轻触锁骨": "touching the collarbone lightly",
        "手持咖啡杯": "holding a coffee cup",
        "握手机": "holding a phone",
        "轻抚衣角": "gently holding the hem",
        "看向镜头": "looking at the camera",
        "侧目看向远处": "glancing into the distance",
        "低头凝视": "looking downward",
        "回头看向镜头": "looking back at the camera",
        "闭眼感受光线": "eyes closed, feeling the light",
        "视线越过镜头": "gaze passing beyond the camera",
        "运动鞋": "sneakers",
        "短靴": "ankle boots",
        "长靴": "knee-high boots",
        "乐福鞋": "loafers",
        "玛丽珍鞋": "Mary Jane shoes",
        "尖头高跟鞋": "pointed high heels",
        "细跟高跟鞋": "stiletto heels",
        "绑带凉鞋": "strappy sandals",
        "厚底鞋": "platform shoes",
        "棉麻": "cotton-linen fabric",
        "羊毛": "wool fabric",
        "针织纹理": "knitted texture",
        "雪纺": "chiffon fabric",
        "缎面": "satin fabric",
        "牛仔布": "denim fabric",
        "磨砂皮革": "matte leather",
        "哑光金属配饰": "matte metal accessories",
        "高腰线": "high waistline",
        "收腰剪裁": "tailored waist",
        "宽松外套": "loose jacket",
        "短上衣": "cropped top",
        "叠穿层次": "layered outfit",
        "领口结构清晰": "clear neckline structure",
        "袖口细节": "cuff details",
        "窗边": "by the window",
        "落地窗": "floor-to-ceiling window",
        "沙发": "sofa",
        "床边": "bedside",
        "化妆台": "vanity table",
        "镜前": "in front of a mirror",
        "书架": "bookshelf",
        "吧台": "bar counter",
        "试衣间": "fitting room",
        "楼梯间": "stairwell",
        "玄关": "entryway",
        "走廊": "hallway",
        "衣帽间": "walk-in closet",
        "厨房岛台": "kitchen island",
        "浴室镜前": "bathroom mirror",
        "街角": "street corner",
        "人行横道": "crosswalk",
        "便利店门口": "convenience store entrance",
        "天台栏杆": "rooftop railing",
        "电梯间": "elevator lobby",
        "停车楼": "parking garage",
        "玻璃橱窗": "glass storefront",
        "广告屏街谷": "billboard canyon street",
        "高架贫民区": "elevated shanty district",
        "赛博地铁": "cyber subway",
        "冷雾古巷": "cold-fog alley",
        "相机": "camera",
        "单反相机": "DSLR camera",
        "摄影包": "camera bag",
        "手机": "phone",
        "咖啡杯": "coffee cup",
        "酒杯": "wine glass",
        "书本": "book",
        "雨伞": "umbrella",
        "笔记本": "notebook",
        "耳机": "headphones",
        "手提袋": "shopping bag",
        "背包": "backpack",
        "腰包": "waist bag",
        "神谕石碑": "oracle stone stele",
        "古琴": "guqin zither",
        "卷轴": "scroll",
        "花束": "bouquet",
        "日轮": "sun disc",
        "月轮": "moon disc",
        "圣火": "sacred flame",
        "权杖": "scepter",
        "面部清晰对焦": "sharp facial focus",
        "双眼清晰": "sharp eyes",
        "手部结构自然": "natural hand anatomy",
        "发丝边缘清晰": "clean hair edges",
        "皮肤纹理自然": "natural skin texture",
        "服装边缘清晰": "clean clothing edges",
        "无多余手指": "no extra fingers",
        "身体结构完整": "complete body structure",
    }
)
_PROMPT_FRAGMENT_TRANSLATION_MAP.update(DANBOORU_GENERAL_TAG_ALIASES)

_RUNTIME_RANDOM_INTENSITY_STRONG_BASELINE = "强"
_RUNTIME_RANDOM_INTENSITY_STRONG_EXTREME = "强 / 极限拉开"
_STRONG_DIVERSITY_SCENE_BUCKET_ORDER = ["indoor", "outdoor", "special"]
_STYLE_POSITIVE_EXCLUSION_TERMS: dict[str, tuple[str, ...]] = {
    "真实感": (
        "二次元",
        "水彩线稿",
        "赛璐璐",
        "OVA风",
        "版画",
        "Q版",
        "神殿",
        "古风建筑",
        "虚幻引擎",
        "3D渲染",
        "Octane渲染",
    ),
    "插画感": (
        "raw photo",
        "纪实抓拍",
        "摄影棚",
        "影棚纯色背景",
        "手机抓拍",
        "虚幻引擎",
        "3D渲染",
    ),
    "CG感": (
        "二次元",
        "水彩线稿",
        "水彩",
        "赛璐璐",
        "OVA风",
        "版画",
        "Q版",
        "古风建筑",
        "神殿",
    ),
    "古风": (
        "杂志感",
        "轻熟感",
        "摄影棚",
        "影棚纯色背景",
        "手机抓拍",
        "未来都市",
        "机库",
        "维修车间",
        "广告屏反射光",
        "钨丝灯实景光",
        "窗边光",
        "古风建筑",
    ),
    "神话感": (
        "二次元",
        "赛璐璐画风",
        "赛璐璐",
        "水墨水彩融合",
        "水彩线稿",
        "广告屏反射光",
        "未来都市",
        "机库",
        "维修车间",
        "古风建筑",
    ),
}
_MULTI_PROMPT_FOCUS_CUES = {
    "人物角色": [
        "面部与主体关系清晰",
        "服装结构与材质层次清晰",
        "场景空间层次明确",
        "姿态自然，镜头透视稳定",
    ],
    "非人物主体": [
        "主体轮廓清晰",
        "材质结构关系明确",
        "环境衬托克制",
        "光影体积关系稳定",
    ],
}
_SHOT_TAGS = {
    "近景",
    "近景半身",
    "中近景",
    "半身",
    "中景",
    "中景半身",
    "全身",
    "全景",
    "全景全身",
    "远景",
    "大远景",
    "大全景",
    "面部特写",
    "面部聚焦",
    "镜头近距离",
}
_PERSON_VARIANT_PROFILES: list[_PersonPromptVariantProfile] = [
    {
        "label": "全身主体版",
        "replace_shot_tags": ["全景全身", "环境人像"],
        "extra_fragments": ["人物完整入镜", "头身比例与姿态优先"],
    },
    {
        "label": "全身服装版",
        "replace_shot_tags": ["全景全身"],
        "extra_fragments": ["服装整体轮廓与材质层次优先", "肩颈、腰线与下摆结构清晰"],
    },
    {
        "label": "全身场景版",
        "replace_shot_tags": ["全景全身", "环境人像"],
        "extra_fragments": ["人物与场景比例自然", "环境空间关系完整"],
    },
    {
        "label": "动作姿态版",
        "replace_shot_tags": ["全身", "中景"],
        "extra_fragments": ["动作起伏自然", "手部与全身肢体关系稳定"],
    },
]
_RUNTIME_DIVERSITY_VARIANT_PROFILES: dict[str, list[_RuntimeDiversityVariantProfile]] = {
    "真实感": [
        {
            "replace_subject_tags": ["成年女性", "东亚", "偶像", "银白长发", "甜美"],
            "replace_scene_tags": ["摄影棚", "影棚纯色背景"],
            "subject_identity": "偶像",
            "scene_group": "minimal",
            "scene_bucket": "indoor",
            "macro_direction": "clean_editorial",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "摄影师", "短碎发", "清冷"],
            "replace_scene_tags": ["街道", "咖啡厅"],
            "subject_identity": "摄影师",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "urban_observer",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "调酒师", "黑长直", "成熟"],
            "replace_scene_tags": ["酒吧", "夜店"],
            "subject_identity": "调酒师",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "nightlife_noir",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "学生", "高马尾", "灵动"],
            "replace_scene_tags": ["教室", "校园"],
            "subject_identity": "学生",
            "scene_group": "indoor",
            "scene_bucket": "indoor",
            "macro_direction": "youth_daily",
        },
    ],
    "插画感": [
        {
            "replace_subject_tags": ["成年女性", "东亚", "偶像", "银白长发", "甜美"],
            "replace_scene_tags": ["梦境", "花海"],
            "subject_identity": "偶像",
            "scene_group": "nature",
            "scene_bucket": "outdoor",
            "macro_direction": "dream_blossom",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "摄影师", "短碎发", "清冷"],
            "replace_scene_tags": ["街道", "独立书店"],
            "subject_identity": "摄影师",
            "scene_group": "city",
            "scene_bucket": "indoor",
            "macro_direction": "art_bookish",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "乐队主唱", "公主切", "叛逆"],
            "replace_scene_tags": ["霓虹小巷", "夜店"],
            "subject_identity": "乐队主唱",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "retro_stage",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "学生", "高马尾", "灵动"],
            "replace_scene_tags": ["校园", "樱花树下"],
            "subject_identity": "学生",
            "scene_group": "nature",
            "scene_bucket": "outdoor",
            "macro_direction": "spring_slice",
        },
    ],
    "CG感": [
        {
            "replace_subject_tags": ["成年女性", "东亚", "机械师", "短碎发", "高智感"],
            "replace_scene_tags": ["机库", "维修车间"],
            "subject_identity": "机械师",
            "scene_group": "industrial",
            "scene_bucket": "special",
            "macro_direction": "industrial_mecha",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "特工", "高马尾", "冷艳"],
            "replace_scene_tags": ["未来都市", "霓虹街区"],
            "subject_identity": "特工",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "cyber_agent",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "女武士", "银白长发", "英气"],
            "replace_scene_tags": ["工业废墟", "训练场"],
            "subject_identity": "女武士",
            "scene_group": "industrial",
            "scene_bucket": "special",
            "macro_direction": "battle_demo",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "研究员", "中分短发", "冷静"],
            "replace_scene_tags": ["办公室", "玻璃幕墙室内"],
            "subject_identity": "研究员",
            "scene_group": "indoor",
            "scene_bucket": "indoor",
            "macro_direction": "lab_minimal",
        },
    ],
    "古风": [
        {
            "replace_subject_tags": ["成年女性", "东亚", "神女", "发髻", "空灵"],
            "replace_scene_tags": ["月下庭院", "古风建筑"],
            "subject_identity": "神女",
            "scene_group": "ancient",
            "scene_bucket": "special",
            "macro_direction": "moonlit_oriental",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "女武士", "高马尾", "英气"],
            "replace_scene_tags": ["竹林", "古建道场"],
            "subject_identity": "女武士",
            "scene_group": "ancient",
            "scene_bucket": "outdoor",
            "macro_direction": "martial_bamboo",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "公主", "盘发", "清贵"],
            "replace_scene_tags": ["宫殿", "古风建筑", "回廊"],
            "subject_identity": "公主",
            "scene_group": "ancient",
            "scene_bucket": "indoor",
            "macro_direction": "oriental_palace",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "祭司", "披发", "神秘"],
            "replace_scene_tags": ["神圣祭坛", "云海", "古风建筑"],
            "subject_identity": "祭司",
            "scene_group": "sacred",
            "scene_bucket": "special",
            "macro_direction": "altar_prophecy",
        },
    ],
    "神话感": [
        {
            "replace_subject_tags": ["成年女性", "东亚", "神女", "银白长发", "空灵"],
            "replace_scene_tags": ["神殿", "云海"],
            "subject_identity": "神女",
            "scene_group": "sacred",
            "scene_bucket": "outdoor",
            "macro_direction": "cloud_goddess",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "祭司", "发髻", "庄严"],
            "replace_scene_tags": ["神圣祭坛", "宗教圣所"],
            "subject_identity": "祭司",
            "scene_group": "sacred",
            "scene_bucket": "indoor",
            "macro_direction": "ritual_sanctum",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "女王", "盘发", "霸气"],
            "replace_scene_tags": ["黑铁王座", "神谕圣所"],
            "subject_identity": "女王",
            "scene_group": "sacred",
            "scene_bucket": "special",
            "macro_direction": "oracle_throne",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "魔女", "湿发", "神秘"],
            "replace_scene_tags": ["法阵", "幻境"],
            "subject_identity": "魔女",
            "scene_group": "sacred",
            "scene_bucket": "special",
            "macro_direction": "arcane_phantasm",
        },
    ],
}
_RUNTIME_DIVERSITY_TRACK_OVERRIDES: dict[tuple[str, str], list[_RuntimeDiversityVariantProfile]] = {
    ("真实感", "写实人像"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "偶像", "银白长发", "甜美"],
            "replace_scene_tags": ["摄影棚", "影棚纯色背景"],
            "replace_outfit_tags": ["修身礼服", "白衬衫"],
            "replace_light_tags": ["自然光", "冷白极简棚拍"],
            "replace_action_tags": ["回眸", "手部姿态自然"],
            "replace_prop_tags": ["书本", "胸针"],
            "subject_identity": "偶像",
            "scene_group": "minimal",
            "scene_bucket": "indoor",
            "macro_direction": "clean_editorial",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "摄影师", "短碎发", "清冷"],
            "replace_scene_tags": ["街道", "咖啡厅"],
            "replace_outfit_tags": ["长款大衣", "白衬衫"],
            "replace_light_tags": ["阴天柔散光", "暖褪色胶片"],
            "replace_action_tags": ["若有所思", "双手插袋"],
            "replace_prop_tags": ["相机", "托特包"],
            "subject_identity": "摄影师",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "street_realism",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "调酒师", "黑长直", "成熟"],
            "replace_scene_tags": ["酒吧", "夜店"],
            "replace_outfit_tags": ["风衣", "针织开衫"],
            "replace_light_tags": ["电影胶片look", "暖褪色胶片"],
            "replace_action_tags": ["倚靠栏杆", "低头浅笑"],
            "replace_prop_tags": ["咖啡杯", "酒杯"],
            "subject_identity": "调酒师",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "nightlife_character",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "学生", "高马尾", "灵动"],
            "replace_scene_tags": ["教室", "校园"],
            "replace_outfit_tags": ["针织开衫", "白衬衫"],
            "replace_light_tags": ["自然光", "阴天柔散光"],
            "replace_action_tags": ["自然垂手", "回头看向镜头"],
            "replace_prop_tags": ["书本", "背包"],
            "subject_identity": "学生",
            "scene_group": "indoor",
            "scene_bucket": "indoor",
            "macro_direction": "youth_slice_frame",
        },
    ],
    ("真实感", "生活纪实"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "摄影师", "短碎发", "清冷"],
            "replace_scene_tags": ["街道", "雨后街头"],
            "replace_outfit_tags": ["长款大衣", "白衬衫"],
            "replace_light_tags": ["阴天柔散光", "暖褪色胶片"],
            "replace_action_tags": ["若有所思", "自然垂手"],
            "replace_prop_tags": ["相机", "书本"],
            "subject_identity": "摄影师",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "documentary_street_day",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "学生", "高马尾", "灵动"],
            "replace_scene_tags": ["校园", "走廊"],
            "replace_outfit_tags": ["针织开衫", "棉质衬衫"],
            "replace_light_tags": ["自然光", "阴天柔散光"],
            "replace_action_tags": ["回头看向镜头", "手部姿态自然"],
            "replace_prop_tags": ["背包", "书本"],
            "subject_identity": "学生",
            "scene_group": "indoor",
            "scene_bucket": "indoor",
            "macro_direction": "campus_documentary",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "调酒师", "黑长直", "慵懒感"],
            "replace_scene_tags": ["酒吧", "便利店门口"],
            "replace_outfit_tags": ["风衣", "白衬衫"],
            "replace_light_tags": ["电影胶片look", "暖褪色胶片"],
            "replace_action_tags": ["侧身", "双手插袋"],
            "replace_prop_tags": ["咖啡杯", "雨伞"],
            "subject_identity": "调酒师",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "night_shift_documentary",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "医生", "中分短发", "沉稳"],
            "replace_scene_tags": ["窗边", "电梯间"],
            "replace_outfit_tags": ["长外套", "白衬衫"],
            "replace_light_tags": ["自然光", "暖褪色胶片"],
            "replace_action_tags": ["视线越过镜头", "自然垂手"],
            "replace_prop_tags": ["笔记本", "手提袋"],
            "subject_identity": "医生",
            "scene_group": "indoor",
            "scene_bucket": "indoor",
            "macro_direction": "quiet_professional_slice",
        },
    ],
    ("真实感", "都市电影人文"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "摄影师", "短碎发", "清冷"],
            "replace_scene_tags": ["街道", "雨夜站台"],
            "replace_outfit_tags": ["长款大衣", "白衬衫"],
            "replace_light_tags": ["阴天柔散光", "青蓝冷雾"],
            "replace_action_tags": ["回眸", "手持相机"],
            "replace_prop_tags": ["相机", "摄影包"],
            "subject_identity": "摄影师",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "urban_observer",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "律师", "中分短发", "沉稳"],
            "replace_scene_tags": ["都市便利店", "街道"],
            "replace_outfit_tags": ["西装", "长外套"],
            "replace_light_tags": ["暖褪色胶片", "阴天柔散光"],
            "replace_action_tags": ["双手负后", "侧身"],
            "replace_prop_tags": ["书本", "咖啡杯"],
            "subject_identity": "律师",
            "scene_group": "city",
            "scene_bucket": "indoor",
            "macro_direction": "urban_professional",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "调酒师", "黑长直", "慵懒感"],
            "replace_scene_tags": ["雨夜站台", "咖啡厅"],
            "replace_outfit_tags": ["风衣", "针织开衫"],
            "replace_light_tags": ["电影胶片look", "青蓝冷雾"],
            "replace_action_tags": ["倚靠栏杆", "低头浅笑"],
            "replace_prop_tags": ["手持咖啡杯", "雨伞"],
            "subject_identity": "调酒师",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "late_city_mood",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "书店女孩", "长发", "温柔"],
            "replace_scene_tags": ["独立书店", "都市便利店"],
            "replace_outfit_tags": ["针织开衫", "白衬衫"],
            "replace_light_tags": ["阴天柔散光", "柔和光晕"],
            "replace_action_tags": ["侧身", "若有所思"],
            "replace_prop_tags": ["书本", "托特包"],
            "subject_identity": "书店女孩",
            "scene_group": "city",
            "scene_bucket": "indoor",
            "macro_direction": "bookish_slice",
        },
    ],
    ("真实感", "时尚编辑商业广告"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "偶像", "盘发", "清贵"],
            "replace_scene_tags": ["极简白棚", "影棚纯色背景"],
            "replace_outfit_tags": ["修身礼服", "尖头高跟鞋"],
            "replace_light_tags": ["冷灰极简棚光", "高窗冷天光"],
            "replace_action_tags": ["指尖触脸", "看向镜头"],
            "replace_prop_tags": ["手提包", "耳环"],
            "subject_identity": "偶像",
            "scene_group": "minimal",
            "scene_bucket": "indoor",
            "macro_direction": "cold_editorial_cover",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "国潮模特", "中分短发", "高智感"],
            "replace_scene_tags": ["玻璃橱窗", "极简白棚"],
            "replace_outfit_tags": ["白衬衫", "长款大衣"],
            "replace_light_tags": ["冷白极简棚拍", "阴天柔散光"],
            "replace_action_tags": ["双手插袋", "侧身"],
            "replace_prop_tags": ["单肩包", "墨镜"],
            "subject_identity": "国潮模特",
            "scene_group": "minimal",
            "scene_bucket": "indoor",
            "macro_direction": "minimal_campaign",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "潮女模特", "长发", "冷艳"],
            "replace_scene_tags": ["影棚纯色背景", "镜前"],
            "replace_outfit_tags": ["露肩设计", "细跟高跟鞋"],
            "replace_light_tags": ["冷灰极简棚光", "柔和光晕"],
            "replace_action_tags": ["手拿包", "回头看向镜头"],
            "replace_prop_tags": ["手提包", "项链"],
            "subject_identity": "潮女模特",
            "scene_group": "minimal",
            "scene_bucket": "special",
            "macro_direction": "glossy_editorial_pose",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "影棚时尚女性", "短碎发", "优雅"],
            "replace_scene_tags": ["极简白棚", "玻璃橱窗"],
            "replace_outfit_tags": ["长外套", "缎面"],
            "replace_light_tags": ["高窗冷天光", "冷白极简棚拍"],
            "replace_action_tags": ["自然垂手", "视线越过镜头"],
            "replace_prop_tags": ["胸针", "耳钉"],
            "subject_identity": "影棚时尚女性",
            "scene_group": "minimal",
            "scene_bucket": "indoor",
            "macro_direction": "quiet_editorial_studio",
        },
    ],
    ("真实感", "日韩影像"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "书店女孩", "长发", "温柔"],
            "replace_scene_tags": ["便利店门口", "雨夜站台"],
            "replace_outfit_tags": ["针织开衫", "白衬衫"],
            "replace_light_tags": ["暖褪色胶片", "柔和光晕"],
            "replace_action_tags": ["低头凝视", "手持咖啡杯"],
            "replace_prop_tags": ["咖啡杯", "托特包"],
            "subject_identity": "书店女孩",
            "scene_group": "city",
            "scene_bucket": "indoor",
            "macro_direction": "jpkr_slice_station",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "学生", "高马尾", "灵动"],
            "replace_scene_tags": ["走廊", "窗边"],
            "replace_outfit_tags": ["棉质衬衫", "针织开衫"],
            "replace_light_tags": ["阴天柔散光", "柔和光晕"],
            "replace_action_tags": ["侧目看向远处", "自然垂手"],
            "replace_prop_tags": ["书本", "背包"],
            "subject_identity": "学生",
            "scene_group": "indoor",
            "scene_bucket": "indoor",
            "macro_direction": "campus_corridor_slice",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "居家游戏女孩", "短碎发", "慵懒感"],
            "replace_scene_tags": ["玻璃橱窗", "便利店门口"],
            "replace_outfit_tags": ["短外套", "短靴"],
            "replace_light_tags": ["电影胶片look", "青蓝冷雾"],
            "replace_action_tags": ["回头看向镜头", "握手机"],
            "replace_prop_tags": ["手机", "耳机"],
            "subject_identity": "居家游戏女孩",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "night_store_glance",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "湖畔金发女性", "长发", "清冷"],
            "replace_scene_tags": ["窗边", "玻璃橱窗"],
            "replace_outfit_tags": ["长外套", "围巾"],
            "replace_light_tags": ["暖褪色胶片", "阴天柔散光"],
            "replace_action_tags": ["若有所思", "侧身"],
            "replace_prop_tags": ["雨伞", "书本"],
            "subject_identity": "湖畔金发女性",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "quiet_window_memory",
        },
    ],
    ("真实感", "商业摄影"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "国潮模特", "中分短发", "高智感"],
            "replace_scene_tags": ["极简白棚", "玻璃橱窗"],
            "replace_outfit_tags": ["修身礼服", "细跟高跟鞋"],
            "replace_light_tags": ["冷白极简棚拍", "高窗冷天光"],
            "replace_action_tags": ["手拿包", "看向镜头"],
            "replace_prop_tags": ["手提包", "胸针"],
            "subject_identity": "国潮模特",
            "scene_group": "minimal",
            "scene_bucket": "indoor",
            "macro_direction": "editorial_cover_luxe",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "潮女模特", "长发", "冷艳"],
            "replace_scene_tags": ["玻璃橱窗", "街角"],
            "replace_outfit_tags": ["白衬衫", "长款大衣"],
            "replace_light_tags": ["阴天柔散光", "暖褪色胶片"],
            "replace_action_tags": ["双手插袋", "侧身"],
            "replace_prop_tags": ["墨镜", "单肩包"],
            "subject_identity": "潮女模特",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "street_campaign",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "影棚时尚女性", "短碎发", "优雅"],
            "replace_scene_tags": ["影棚纯色背景", "镜前"],
            "replace_outfit_tags": ["露肩设计", "细跟高跟鞋"],
            "replace_light_tags": ["冷灰极简棚光", "柔和光晕"],
            "replace_action_tags": ["自然垂手", "回头看向镜头"],
            "replace_prop_tags": ["手提包", "项链"],
            "subject_identity": "影棚时尚女性",
            "scene_group": "minimal",
            "scene_bucket": "special",
            "macro_direction": "glossy_studio_pose",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "偶像", "盘发", "清贵"],
            "replace_scene_tags": ["极简白棚", "玻璃橱窗"],
            "replace_outfit_tags": ["修身礼服", "白衬衫"],
            "replace_light_tags": ["高窗冷天光", "冷白极简棚拍"],
            "replace_action_tags": ["手部姿态自然", "视线越过镜头"],
            "replace_prop_tags": ["手提包", "墨镜"],
            "subject_identity": "偶像",
            "scene_group": "minimal",
            "scene_bucket": "indoor",
            "macro_direction": "quiet_luxury_editorial",
        },
    ],
    ("真实感", "私房写实"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "调酒师", "黑长直", "慵懒感"],
            "replace_scene_tags": ["落地窗", "镜前"],
            "replace_outfit_tags": ["丝质睡袍", "吊带睡裙"],
            "replace_light_tags": ["暖色轮廓逆光", "柔和光晕"],
            "replace_action_tags": ["低头浅笑", "手部姿态自然"],
            "replace_prop_tags": ["酒杯", "咖啡杯"],
            "subject_identity": "调酒师",
            "scene_group": "indoor",
            "scene_bucket": "indoor",
            "macro_direction": "window_boudoir_glow",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "居家游戏女孩", "短碎发", "温柔"],
            "replace_scene_tags": ["浴室镜前", "吧台"],
            "replace_outfit_tags": ["露背礼服", "针织开衫"],
            "replace_light_tags": ["电影胶片look", "暖褪色胶片"],
            "replace_action_tags": ["侧身", "倚靠栏杆"],
            "replace_prop_tags": ["雨伞", "酒杯"],
            "subject_identity": "居家游戏女孩",
            "scene_group": "indoor",
            "scene_bucket": "special",
            "macro_direction": "private_noir_pause",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "影棚时尚女性", "长发", "迷离"],
            "replace_scene_tags": ["镜前", "浴室镜前"],
            "replace_outfit_tags": ["吊带睡裙", "露背礼服"],
            "replace_light_tags": ["柔和光晕", "电影胶片look"],
            "replace_action_tags": ["手部姿态自然", "回头看向镜头"],
            "replace_prop_tags": ["酒杯", "雨伞"],
            "subject_identity": "影棚时尚女性",
            "scene_group": "indoor",
            "scene_bucket": "indoor",
            "macro_direction": "mirror_intimacy",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "书店女孩", "湿发", "清冷"],
            "replace_scene_tags": ["落地窗", "吧台"],
            "replace_outfit_tags": ["丝质睡袍", "针织开衫"],
            "replace_light_tags": ["暖色轮廓逆光", "暖褪色胶片"],
            "replace_action_tags": ["低头浅笑", "侧身"],
            "replace_prop_tags": ["手持咖啡杯", "雨伞"],
            "subject_identity": "书店女孩",
            "scene_group": "indoor",
            "scene_bucket": "special",
            "macro_direction": "soft_private_story",
        },
    ],
    ("插画感", "插画叙事"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "偶像", "银白长发", "空灵"],
            "replace_scene_tags": ["梦境", "花海"],
            "replace_outfit_tags": ["Lolita", "奶油针织"],
            "replace_light_tags": ["浮光", "高调粉彩"],
            "replace_action_tags": ["轻拈发梢", "拈花而立"],
            "replace_prop_tags": ["花束", "卷轴"],
            "subject_identity": "偶像",
            "scene_group": "nature",
            "scene_bucket": "outdoor",
            "macro_direction": "pastel_storybook",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "女冒险者", "长直发", "灵动"],
            "replace_scene_tags": ["画室", "乡村小道"],
            "replace_outfit_tags": ["和服", "披风"],
            "replace_light_tags": ["叶隙斑驳光", "暖褪色胶片"],
            "replace_action_tags": ["回眸", "侧坐回眸"],
            "replace_prop_tags": ["古琴", "伞"],
            "subject_identity": "女冒险者",
            "scene_group": "nature",
            "scene_bucket": "indoor",
            "macro_direction": "illustrated_travelogue",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "书店女孩", "短碎发", "温柔"],
            "replace_scene_tags": ["图书馆", "独立书店"],
            "replace_outfit_tags": ["奶油针织", "Lolita"],
            "replace_light_tags": ["浮光", "叶隙斑驳光"],
            "replace_action_tags": ["轻拈发梢", "若有所思"],
            "replace_prop_tags": ["卷轴", "书本"],
            "subject_identity": "书店女孩",
            "scene_group": "indoor",
            "scene_bucket": "indoor",
            "macro_direction": "bookish_illustration",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "仙子", "高马尾", "空灵"],
            "replace_scene_tags": ["花海", "梦境"],
            "replace_outfit_tags": ["披风", "和服"],
            "replace_light_tags": ["高调粉彩", "暖褪色胶片"],
            "replace_action_tags": ["拈花而立", "侧坐回眸"],
            "replace_prop_tags": ["花束", "古琴"],
            "subject_identity": "仙子",
            "scene_group": "nature",
            "scene_bucket": "special",
            "macro_direction": "ornamental_fairytale",
        },
    ],
    ("插画感", "复古OVA"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "摄影师", "短碎发", "清冷"],
            "replace_scene_tags": ["街道", "独立书店"],
            "replace_outfit_tags": ["披风", "和服"],
            "replace_light_tags": ["浮光", "暖褪色胶片"],
            "replace_action_tags": ["回眸", "双手抱臂"],
            "replace_prop_tags": ["花束", "伞"],
            "subject_identity": "摄影师",
            "scene_group": "city",
            "scene_bucket": "indoor",
            "macro_direction": "retro_bookstore_frame",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "女冒险者", "高马尾", "英气"],
            "replace_scene_tags": ["中世纪城镇", "乡村小道"],
            "replace_outfit_tags": ["披风", "Lolita"],
            "replace_light_tags": ["叶隙斑驳光", "暖褪色胶片"],
            "replace_action_tags": ["轻拈发梢", "拈花而立"],
            "replace_prop_tags": ["卷轴", "古琴"],
            "subject_identity": "女冒险者",
            "scene_group": "nature",
            "scene_bucket": "outdoor",
            "macro_direction": "ova_fantasy_journey",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "偶像", "高马尾", "灵动"],
            "replace_scene_tags": ["梦境", "花海"],
            "replace_outfit_tags": ["奶油针织", "和服"],
            "replace_light_tags": ["高调粉彩", "浮光"],
            "replace_action_tags": ["侧坐回眸", "回眸"],
            "replace_prop_tags": ["花束", "伞"],
            "subject_identity": "偶像",
            "scene_group": "nature",
            "scene_bucket": "outdoor",
            "macro_direction": "youthful_ova_slice",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "乐队主唱", "公主切", "叛逆"],
            "replace_scene_tags": ["霓虹小巷", "夜店"],
            "replace_outfit_tags": ["Lolita", "披风"],
            "replace_light_tags": ["暖褪色胶片", "高调粉彩"],
            "replace_action_tags": ["拈花而立", "轻拈发梢"],
            "replace_prop_tags": ["花束", "卷轴"],
            "subject_identity": "乐队主唱",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "nostalgic_character_frame",
        },
    ],
    ("神话感", "神话人像"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "神女", "银白长发", "空灵"],
            "replace_scene_tags": ["云海", "月下庭院"],
            "replace_outfit_tags": ["白色斗篷", "神官长袍"],
            "replace_light_tags": ["蓝灰月光", "体积神光"],
            "replace_action_tags": ["抬头仰望", "伸手触碰"],
            "replace_prop_tags": ["日轮", "月轮"],
            "subject_identity": "神女",
            "scene_group": "sacred",
            "scene_bucket": "outdoor",
            "macro_direction": "moonlit_divine_portrait",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "祭司", "发髻", "庄严"],
            "replace_scene_tags": ["宗教圣所", "云海"],
            "replace_outfit_tags": ["神官长袍", "鎏金头冠"],
            "replace_light_tags": ["金雾神光", "圣辉逆光"],
            "replace_action_tags": ["拈花而立", "站姿挺拔"],
            "replace_prop_tags": ["权杖", "圣火"],
            "subject_identity": "祭司",
            "scene_group": "sacred",
            "scene_bucket": "indoor",
            "macro_direction": "ritual_oracle_portrait",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "女王", "盘发", "霸气"],
            "replace_scene_tags": ["宫殿", "云端阶梯"],
            "replace_outfit_tags": ["黑金重甲", "白色斗篷"],
            "replace_light_tags": ["圣辉逆光", "蓝灰月光"],
            "replace_action_tags": ["站姿挺拔", "抬头仰望"],
            "replace_prop_tags": ["权杖", "月轮"],
            "subject_identity": "女王",
            "scene_group": "sacred",
            "scene_bucket": "special",
            "macro_direction": "royal_myth_portrait",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "魔女", "披发", "神秘"],
            "replace_scene_tags": ["幻境", "星空"],
            "replace_outfit_tags": ["神官长袍", "黑金重甲"],
            "replace_light_tags": ["体积神光", "金雾神光"],
            "replace_action_tags": ["伸手触碰", "拈花而立"],
            "replace_prop_tags": ["圣火", "日轮"],
            "subject_identity": "魔女",
            "scene_group": "sacred",
            "scene_bucket": "special",
            "macro_direction": "occult_divine_closeup",
        },
    ],
    ("神话感", "神殿史诗"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "神女", "银白长发", "空灵"],
            "replace_scene_tags": ["神殿", "天穹祭坛"],
            "replace_outfit_tags": ["神官长袍", "鎏金头冠"],
            "replace_light_tags": ["圣辉逆光", "体积神光"],
            "replace_action_tags": ["抬头仰望", "站姿挺拔"],
            "replace_prop_tags": ["日轮", "权杖"],
            "subject_identity": "神女",
            "scene_group": "sacred",
            "scene_bucket": "outdoor",
            "macro_direction": "temple_epic_entrance",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "祭司", "发髻", "庄严"],
            "replace_scene_tags": ["星海神殿", "神圣祭坛"],
            "replace_outfit_tags": ["白色斗篷", "神官长袍"],
            "replace_light_tags": ["金雾神光", "蓝灰月光"],
            "replace_action_tags": ["伸手触碰", "站姿挺拔"],
            "replace_prop_tags": ["月轮", "圣火"],
            "subject_identity": "祭司",
            "scene_group": "sacred",
            "scene_bucket": "indoor",
            "macro_direction": "altar_procession",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "女王", "盘发", "霸气"],
            "replace_scene_tags": ["神谕圣所", "天穹祭坛"],
            "replace_outfit_tags": ["黑金重甲", "鎏金头冠"],
            "replace_light_tags": ["体积神光", "圣辉逆光"],
            "replace_action_tags": ["抬头仰望", "拈花而立"],
            "replace_prop_tags": ["权杖", "日轮"],
            "subject_identity": "女王",
            "scene_group": "sacred",
            "scene_bucket": "special",
            "macro_direction": "throne_epic_icon",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "魔女", "披发", "神秘"],
            "replace_scene_tags": ["悬空神庙", "星海神殿"],
            "replace_outfit_tags": ["白色斗篷", "黑金重甲"],
            "replace_light_tags": ["蓝灰月光", "金雾神光"],
            "replace_action_tags": ["伸手触碰", "站姿挺拔"],
            "replace_prop_tags": ["圣火", "月轮"],
            "subject_identity": "魔女",
            "scene_group": "sacred",
            "scene_bucket": "special",
            "macro_direction": "sky_temple_omen",
        },
    ],
    ("CG感", "赛博雨夜"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "特工", "高马尾", "冷艳"],
            "replace_scene_tags": ["未来都市", "霓虹街区"],
            "replace_outfit_tags": ["战术服", "机能外套"],
            "replace_light_tags": ["全息投影光", "蓝洋红对撞"],
            "replace_action_tags": ["持物待发", "回头看向镜头"],
            "replace_prop_tags": ["能量刀", "耳机"],
            "subject_identity": "特工",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "neon_mission_sprint",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "机械师", "短碎发", "高智感"],
            "replace_scene_tags": ["赛博地铁", "广告屏街谷"],
            "replace_outfit_tags": ["机能外套", "短外套"],
            "replace_light_tags": ["广告屏反射光", "青蓝冷雾"],
            "replace_action_tags": ["双手插袋", "侧身"],
            "replace_prop_tags": ["手机", "全息界面"],
            "subject_identity": "机械师",
            "scene_group": "city",
            "scene_bucket": "indoor",
            "macro_direction": "subway_rain_pause",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "近战法师", "银白长发", "霸气"],
            "replace_scene_tags": ["广告屏街谷", "霓虹街区"],
            "replace_outfit_tags": ["战术服", "皮革"],
            "replace_light_tags": ["蓝洋红对撞", "全息投影光"],
            "replace_action_tags": ["抬手", "站姿挺拔"],
            "replace_prop_tags": ["全息界面", "能量刀"],
            "subject_identity": "近战法师",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "caster_neon_attack",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "忍者", "中分短发", "英气"],
            "replace_scene_tags": ["高架贫民区", "赛博地铁"],
            "replace_outfit_tags": ["机能外套", "皮革"],
            "replace_light_tags": ["广告屏反射光", "蓝洋红对撞"],
            "replace_action_tags": ["双手负后", "回头看向镜头"],
            "replace_prop_tags": ["耳机", "能量刀"],
            "subject_identity": "忍者",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "shadow_runner_return",
        },
    ],
    ("CG感", "工业科幻"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "研究员", "中分短发", "冷静"],
            "replace_scene_tags": ["办公室", "玻璃幕墙室内"],
            "replace_outfit_tags": ["短外套", "机能外套"],
            "replace_light_tags": ["冷荧顶光", "广告屏反射光"],
            "replace_action_tags": ["双手负后", "看向镜头"],
            "replace_prop_tags": ["全息界面", "手机"],
            "subject_identity": "研究员",
            "scene_group": "indoor",
            "scene_bucket": "indoor",
            "macro_direction": "lab_command_frame",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "特工", "高马尾", "冷艳"],
            "replace_scene_tags": ["未来都市", "霓虹街区"],
            "replace_outfit_tags": ["战术服", "机能外套"],
            "replace_light_tags": ["全息投影光", "蓝洋红对撞"],
            "replace_action_tags": ["持物待发", "回头看向镜头"],
            "replace_prop_tags": ["能量刀", "耳机"],
            "subject_identity": "特工",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "city_infiltration",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "机械师", "短碎发", "高智感"],
            "replace_scene_tags": ["机库", "维修车间"],
            "replace_outfit_tags": ["机能外套", "皮革"],
            "replace_light_tags": ["青蓝冷雾", "广告屏反射光"],
            "replace_action_tags": ["站姿挺拔", "双手负后"],
            "replace_prop_tags": ["全息界面", "手机"],
            "subject_identity": "机械师",
            "scene_group": "industrial",
            "scene_bucket": "special",
            "macro_direction": "hangar_engineer_pose",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "女武士", "银白长发", "英气"],
            "replace_scene_tags": ["工业废墟", "训练场"],
            "replace_outfit_tags": ["战术服", "皮革"],
            "replace_light_tags": ["全息投影光", "青蓝冷雾"],
            "replace_action_tags": ["回头看向镜头", "持物待发"],
            "replace_prop_tags": ["能量刀", "耳机"],
            "subject_identity": "女武士",
            "scene_group": "industrial",
            "scene_bucket": "special",
            "macro_direction": "battlefield_drill_frame",
        },
    ],
    ("古风", "古风园林"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "公主", "盘发", "清贵"],
            "replace_scene_tags": ["宫殿", "回廊"],
            "replace_outfit_tags": ["褙子", "诃子裙"],
            "replace_light_tags": ["纸窗天光", "柔光"],
            "replace_action_tags": ["拈花而立", "侧身"],
            "replace_prop_tags": ["玉佩", "花束"],
            "subject_identity": "公主",
            "scene_group": "ancient",
            "scene_bucket": "indoor",
            "macro_direction": "garden_palace_refinement",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "女武士", "高马尾", "英气"],
            "replace_scene_tags": ["竹林", "古建道场"],
            "replace_outfit_tags": ["劲装", "披风"],
            "replace_light_tags": ["柔光", "叶隙斑驳光"],
            "replace_action_tags": ["回眸", "站姿挺拔"],
            "replace_prop_tags": ["伞", "剑"],
            "subject_identity": "女武士",
            "scene_group": "ancient",
            "scene_bucket": "outdoor",
            "macro_direction": "garden_martial_path",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "神女", "发髻", "空灵"],
            "replace_scene_tags": ["月下庭院", "云海"],
            "replace_outfit_tags": ["褙子", "云肩"],
            "replace_light_tags": ["蓝灰月光", "柔光"],
            "replace_action_tags": ["轻拈发梢", "若有所思"],
            "replace_prop_tags": ["古琴", "花束"],
            "subject_identity": "神女",
            "scene_group": "ancient",
            "scene_bucket": "special",
            "macro_direction": "moon_garden_ritual",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "女武士", "高马尾", "英气"],
            "replace_scene_tags": ["竹林", "月洞门"],
            "replace_outfit_tags": ["劲装", "披风"],
            "replace_light_tags": ["叶隙斑驳光", "柔光"],
            "replace_action_tags": ["回眸", "站姿挺拔"],
            "replace_prop_tags": ["伞", "剑"],
            "subject_identity": "女武士",
            "scene_group": "ancient",
            "scene_bucket": "outdoor",
            "macro_direction": "martial_garden_entry",
        },
    ],
    ("古风", "武侠剧照"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "女武士", "高马尾", "英气"],
            "replace_scene_tags": ["竹林", "古建道场"],
            "replace_outfit_tags": ["劲装", "披风"],
            "replace_light_tags": ["暖色轮廓逆光", "烛火暖光"],
            "replace_action_tags": ["扶剑而立", "回头看向镜头"],
            "replace_prop_tags": ["剑", "灯笼"],
            "subject_identity": "女武士",
            "scene_group": "ancient",
            "scene_bucket": "outdoor",
            "macro_direction": "classic_wuxia_entry",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "剑客", "盘发", "清冷"],
            "replace_scene_tags": ["回廊", "月下庭院"],
            "replace_outfit_tags": ["飞鱼服", "长衫"],
            "replace_light_tags": ["烛火暖光", "青蓝冷雾"],
            "replace_action_tags": ["持刀回身", "双手负后"],
            "replace_prop_tags": ["刀", "伞"],
            "subject_identity": "剑客",
            "scene_group": "ancient",
            "scene_bucket": "indoor",
            "macro_direction": "corridor_duel_pause",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "祭司", "披发", "神秘"],
            "replace_scene_tags": ["古风建筑", "神圣祭坛"],
            "replace_outfit_tags": ["宽袖法袍", "披风"],
            "replace_light_tags": ["红雾表现主义打光", "暖色轮廓逆光"],
            "replace_action_tags": ["站姿挺拔", "侧目看向远处"],
            "replace_prop_tags": ["面具", "灯笼"],
            "subject_identity": "祭司",
            "scene_group": "ancient",
            "scene_bucket": "special",
            "macro_direction": "ritual_wuxia_stage",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "公主", "发髻", "清贵"],
            "replace_scene_tags": ["宫殿", "回廊"],
            "replace_outfit_tags": ["长衫", "披风"],
            "replace_light_tags": ["烛火暖光", "柔光"],
            "replace_action_tags": ["侧身", "看向镜头"],
            "replace_prop_tags": ["伞", "剑"],
            "subject_identity": "公主",
            "scene_group": "ancient",
            "scene_bucket": "indoor",
            "macro_direction": "royal_wuxia_portrait",
        },
    ],
    ("神话感", "西方奇幻神话史诗"): [
        {
            "replace_subject_tags": ["成年女性", "神圣骑士", "银白长发", "庄严"],
            "replace_scene_tags": ["北欧海岸", "冰冻森林"],
            "replace_outfit_tags": ["白色斗篷", "银白雕花重甲"],
            "replace_light_tags": ["蓝灰月光", "体积神光"],
            "replace_action_tags": ["扶剑而立", "抬头仰望"],
            "replace_prop_tags": ["剑", "圣火"],
            "subject_identity": "神圣骑士",
            "scene_group": "sacred",
            "scene_bucket": "outdoor",
            "macro_direction": "holy_knight_coast",
        },
        {
            "replace_subject_tags": ["成年女性", "冰霜骑士", "长发", "清冷"],
            "replace_scene_tags": ["冰冻森林", "北欧海岸"],
            "replace_outfit_tags": ["白色斗篷", "黑金重甲"],
            "replace_light_tags": ["蓝灰月光", "圣辉逆光"],
            "replace_action_tags": ["站姿挺拔", "伸手触碰"],
            "replace_prop_tags": ["剑", "月轮"],
            "subject_identity": "冰霜骑士",
            "scene_group": "sacred",
            "scene_bucket": "indoor",
            "macro_direction": "frost_knight_halo",
        },
        {
            "replace_subject_tags": ["成年女性", "女王", "盘发", "霸气"],
            "replace_scene_tags": ["黑铁王座", "宫殿"],
            "replace_outfit_tags": ["黑金重甲", "鎏金头冠"],
            "replace_light_tags": ["金雾神光", "体积神光"],
            "replace_action_tags": ["抬头仰望", "站姿挺拔"],
            "replace_prop_tags": ["权杖", "圣火"],
            "subject_identity": "女王",
            "scene_group": "sacred",
            "scene_bucket": "special",
            "macro_direction": "throne_queen_epic",
        },
        {
            "replace_subject_tags": ["成年女性", "炎魔天使", "披发", "神秘"],
            "replace_scene_tags": ["火山洞穴", "黑铁王座"],
            "replace_outfit_tags": ["黑金重甲", "白色斗篷"],
            "replace_light_tags": ["金雾神光", "圣辉逆光"],
            "replace_action_tags": ["伸手触碰", "扶剑而立"],
            "replace_prop_tags": ["圣火", "权杖"],
            "subject_identity": "炎魔天使",
            "scene_group": "sacred",
            "scene_bucket": "special",
            "macro_direction": "infernal_epic_icon",
        },
    ],
    ("古风", "东方古风武侠"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "女武士", "高马尾", "英气"],
            "replace_scene_tags": ["幽暗竹林", "竹林"],
            "replace_outfit_tags": ["劲装", "披风"],
            "replace_light_tags": ["红雾表现主义打光", "暖色轮廓逆光"],
            "replace_action_tags": ["扶剑而立", "回头看向镜头"],
            "replace_prop_tags": ["剑", "灯笼"],
            "subject_identity": "女武士",
            "scene_group": "ancient",
            "scene_bucket": "outdoor",
            "macro_direction": "bamboo_duel_entry",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "剑客", "盘发", "清冷"],
            "replace_scene_tags": ["冷雾古巷", "月下庭院"],
            "replace_outfit_tags": ["飞鱼服", "长衫"],
            "replace_light_tags": ["烛火暖光", "青蓝冷雾"],
            "replace_action_tags": ["持刀回身", "双手负后"],
            "replace_prop_tags": ["刀", "伞"],
            "subject_identity": "剑客",
            "scene_group": "ancient",
            "scene_bucket": "special",
            "macro_direction": "alley_blade_turn",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "祭司", "披发", "神秘"],
            "replace_scene_tags": ["古建道场", "回廊"],
            "replace_outfit_tags": ["宽袖法袍", "披风"],
            "replace_light_tags": ["暖色轮廓逆光", "烛火暖光"],
            "replace_action_tags": ["自然垂手", "侧目看向远处"],
            "replace_prop_tags": ["灯笼", "面具"],
            "subject_identity": "祭司",
            "scene_group": "ancient",
            "scene_bucket": "indoor",
            "macro_direction": "ritual_corridor_wuxia",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "公主", "发髻", "清贵"],
            "replace_scene_tags": ["月下庭院", "回廊"],
            "replace_outfit_tags": ["宽袖法袍", "飞鱼服"],
            "replace_light_tags": ["青蓝冷雾", "红雾表现主义打光"],
            "replace_action_tags": ["侧身", "看向镜头"],
            "replace_prop_tags": ["伞", "剑"],
            "subject_identity": "公主",
            "scene_group": "ancient",
            "scene_bucket": "special",
            "macro_direction": "mooncourt_heroine",
        },
    ],
    ("古风", "国风暗黑志怪"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "妖女", "披发", "神秘"],
            "replace_scene_tags": ["废弃地下老屋", "冷雾古巷"],
            "replace_outfit_tags": ["宽袖法袍", "披风"],
            "replace_light_tags": ["冷雾惊悚侧光", "青蓝冷雾"],
            "replace_action_tags": ["低头凝视", "自然垂手"],
            "replace_prop_tags": ["灯笼", "面具"],
            "subject_identity": "妖女",
            "scene_group": "ancient",
            "scene_bucket": "special",
            "macro_direction": "haunted_house_reveal",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "祭司", "发髻", "庄严"],
            "replace_scene_tags": ["宗教圣所", "废弃教堂"],
            "replace_outfit_tags": ["长衫", "披风"],
            "replace_light_tags": ["黑色电影硬光", "冷雾惊悚侧光"],
            "replace_action_tags": ["侧目看向远处", "回头看向镜头"],
            "replace_prop_tags": ["神谕石碑", "灯笼"],
            "subject_identity": "祭司",
            "scene_group": "ancient",
            "scene_bucket": "indoor",
            "macro_direction": "oracle_horror_shrine",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "魔女", "湿发", "冷艳"],
            "replace_scene_tags": ["冷雾古巷", "废弃地下老屋"],
            "replace_outfit_tags": ["宽袖法袍", "长衫"],
            "replace_light_tags": ["青蓝冷雾", "红雾表现主义打光"],
            "replace_action_tags": ["侧身", "低头凝视"],
            "replace_prop_tags": ["面具", "伞"],
            "subject_identity": "魔女",
            "scene_group": "ancient",
            "scene_bucket": "outdoor",
            "macro_direction": "fog_alley_occult",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "神女", "披发", "空灵"],
            "replace_scene_tags": ["废弃教堂", "宗教圣所"],
            "replace_outfit_tags": ["披风", "宽袖法袍"],
            "replace_light_tags": ["黑色电影硬光", "青蓝冷雾"],
            "replace_action_tags": ["视线越过镜头", "自然垂手"],
            "replace_prop_tags": ["神谕石碑", "面具"],
            "subject_identity": "神女",
            "scene_group": "ancient",
            "scene_bucket": "special",
            "macro_direction": "ghostly_shrine_icon",
        },
    ],
    ("CG感", "东方赛博武侠朋克"): [
        {
            "replace_subject_tags": ["成年女性", "东亚", "特工", "高马尾", "冷艳"],
            "replace_scene_tags": ["赛博街区", "广告屏街谷"],
            "replace_outfit_tags": ["机能外套", "战术服"],
            "replace_light_tags": ["全息投影光", "蓝洋红对撞"],
            "replace_action_tags": ["持物待发", "回头看向镜头"],
            "replace_prop_tags": ["能量刀", "全息界面"],
            "subject_identity": "特工",
            "scene_group": "city",
            "scene_bucket": "outdoor",
            "macro_direction": "neon_blade_hunt",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "机械师", "短碎发", "高智感"],
            "replace_scene_tags": ["赛博地铁", "高架贫民区"],
            "replace_outfit_tags": ["机能外套", "短外套"],
            "replace_light_tags": ["广告屏反射光", "青蓝冷雾"],
            "replace_action_tags": ["双手插袋", "侧身"],
            "replace_prop_tags": ["手机", "耳机"],
            "subject_identity": "机械师",
            "scene_group": "city",
            "scene_bucket": "indoor",
            "macro_direction": "subway_hacker_pause",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "近战法师", "银白长发", "霸气"],
            "replace_scene_tags": ["广告屏街谷", "赛博街区"],
            "replace_outfit_tags": ["战术服", "皮革"],
            "replace_light_tags": ["蓝洋红对撞", "全息投影光"],
            "replace_action_tags": ["抬手", "站姿挺拔"],
            "replace_prop_tags": ["全息界面", "手机"],
            "subject_identity": "近战法师",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "arcane_cyber_cast",
        },
        {
            "replace_subject_tags": ["成年女性", "东亚", "忍者", "中分短发", "英气"],
            "replace_scene_tags": ["高架贫民区", "赛博地铁"],
            "replace_outfit_tags": ["机能外套", "皮革"],
            "replace_light_tags": ["广告屏反射光", "蓝洋红对撞"],
            "replace_action_tags": ["回头看向镜头", "双手负后"],
            "replace_prop_tags": ["能量刀", "耳机"],
            "subject_identity": "忍者",
            "scene_group": "city",
            "scene_bucket": "special",
            "macro_direction": "underpass_shadow_runner",
        },
    ],
}
_RUNTIME_DIVERSITY_TRACK_OVERRIDES.update(
    {
        ("真实感", "城市天台纪实"): [
            {
                "replace_subject_tags": ["成年女性", "东亚", "摄影师", "长发", "清冷"],
                "replace_scene_tags": ["城市天台", "屋顶晾衣架"],
                "replace_outfit_tags": ["长款大衣", "白衬衫"],
                "replace_light_tags": ["日落逆光", "自然光"],
                "replace_action_tags": ["侧目看向远处", "自然垂手"],
                "replace_prop_tags": ["有线耳机", "手机"],
                "replace_composition_tags": ["中景半身", "侧脸构图", "负空间留白"],
                "subject_identity": "摄影师",
                "scene_group": "city",
                "scene_bucket": "outdoor",
                "macro_direction": "rooftop_sunset_listener",
            },
            {
                "replace_subject_tags": ["成年女性", "东亚", "学生", "黑长直", "灵动"],
                "replace_scene_tags": ["城市天台", "天台栏杆"],
                "replace_outfit_tags": ["宽松外套", "白衬衫"],
                "replace_light_tags": ["金色侧逆光", "自然光"],
                "replace_action_tags": ["回头看向镜头", "双手插袋"],
                "replace_prop_tags": ["有线耳机", "手提袋"],
                "replace_composition_tags": ["中景半身", "镜头近距离", "负空间留白"],
                "subject_identity": "学生",
                "scene_group": "city",
                "scene_bucket": "outdoor",
                "macro_direction": "rooftop_youth_breeze",
            },
            {
                "replace_subject_tags": ["成年女性", "东亚", "书店女孩", "长发", "温柔"],
                "replace_scene_tags": ["城市天台", "街角"],
                "replace_outfit_tags": ["针织开衫", "长外套"],
                "replace_light_tags": ["日落逆光", "自然光"],
                "replace_action_tags": ["若有所思", "手部姿态自然"],
                "replace_prop_tags": ["耳机", "书本"],
                "replace_composition_tags": ["中景半身", "侧脸构图", "负空间留白"],
                "subject_identity": "书店女孩",
                "scene_group": "city",
                "scene_bucket": "outdoor",
                "macro_direction": "rooftop_reflective_pause",
            },
            {
                "replace_subject_tags": ["成年女性", "东亚", "通勤女孩", "中分短发", "沉稳"],
                "replace_scene_tags": ["城市天台", "停车楼"],
                "replace_outfit_tags": ["短外套", "白衬衫"],
                "replace_light_tags": ["金色侧逆光", "自然光"],
                "replace_action_tags": ["视线越过镜头", "握手机"],
                "replace_prop_tags": ["手机", "有线耳机"],
                "replace_composition_tags": ["中景半身", "侧脸构图", "背景轻微虚化"],
                "subject_identity": "通勤女孩",
                "scene_group": "city",
                "scene_bucket": "outdoor",
                "macro_direction": "rooftop_commute_pause",
            },
        ],
        ("神话感", "山谷圣城史诗"): [
            {
                "replace_subject_tags": [],
                "replace_scene_tags": ["山谷圣城", "瀑布峡谷", "远山雪峰"],
                "replace_light_tags": ["云隙光", "体积光"],
                "replace_prop_tags": ["史诗城市中轴", "山体建筑一体化"],
                "replace_composition_tags": ["大全景", "中轴对称巨构", "超广角全景"],
                "subject_identity": "圣城远景",
                "scene_group": "sacred",
                "scene_bucket": "outdoor",
                "macro_direction": "valley_holy_city",
            },
            {
                "replace_subject_tags": [],
                "replace_scene_tags": ["巨构神殿", "瀑布峡谷", "远山雪峰"],
                "replace_light_tags": ["圣辉逆光", "云隙光"],
                "replace_prop_tags": ["史诗城市中轴", "山体建筑一体化"],
                "replace_composition_tags": ["大全景", "祭坛对称构图", "超广角全景"],
                "subject_identity": "神殿远景",
                "scene_group": "sacred",
                "scene_bucket": "outdoor",
                "macro_direction": "mountain_temple_axis",
            },
            {
                "replace_subject_tags": [],
                "replace_scene_tags": ["山谷圣城", "巨构神殿", "远山雪峰"],
                "replace_light_tags": ["金雾神光", "体积光"],
                "replace_prop_tags": ["山体建筑一体化", "史诗城市中轴"],
                "replace_composition_tags": ["大远景", "中轴对称巨构", "超广角全景"],
                "subject_identity": "远山圣城",
                "scene_group": "sacred",
                "scene_bucket": "outdoor",
                "macro_direction": "distant_epic_capital",
            },
            {
                "replace_subject_tags": [],
                "replace_scene_tags": ["巨构神殿", "山谷圣城", "瀑布峡谷"],
                "replace_light_tags": ["云隙光", "圣辉逆光"],
                "replace_prop_tags": ["史诗城市中轴", "山体建筑一体化"],
                "replace_composition_tags": ["大全景", "中轴对称巨构", "超广角全景"],
                "subject_identity": "峡谷圣所",
                "scene_group": "sacred",
                "scene_bucket": "outdoor",
                "macro_direction": "canyon_sanctum_scale",
            },
        ],
        ("CG感", "工业树灵巨像"): [
            {
                "replace_subject_tags": ["树灵巨像", "古木守卫"],
                "replace_scene_tags": ["工业舱室", "维修车间"],
                "replace_light_tags": ["冷色工业顶光", "体积光"],
                "replace_prop_tags": ["朽木树皮纹理", "苔藓附生质感"],
                "replace_composition_tags": ["巨物压迫近景", "低角度"],
                "subject_identity": "树灵巨像",
                "scene_group": "industrial",
                "scene_bucket": "indoor",
                "macro_direction": "industrial_bark_colossus",
            },
            {
                "replace_subject_tags": ["古木守卫", "藤蔓木妖"],
                "replace_scene_tags": ["工业舱室", "机库"],
                "replace_light_tags": ["冷色工业顶光", "青蓝冷雾"],
                "replace_prop_tags": ["发光裂隙", "苔藓附生质感"],
                "replace_composition_tags": ["巨物压迫近景", "超广角全景"],
                "subject_identity": "古木守卫",
                "scene_group": "industrial",
                "scene_bucket": "indoor",
                "macro_direction": "hangar_wood_guardian",
            },
            {
                "replace_subject_tags": ["藤蔓木妖", "树灵巨像"],
                "replace_scene_tags": ["维修车间", "工业舱室"],
                "replace_light_tags": ["体积光", "冷色工业顶光"],
                "replace_prop_tags": ["朽木树皮纹理", "发光裂隙"],
                "replace_composition_tags": ["低角度", "巨物压迫近景"],
                "subject_identity": "藤蔓木妖",
                "scene_group": "industrial",
                "scene_bucket": "special",
                "macro_direction": "garage_vine_fiend",
            },
            {
                "replace_subject_tags": ["树灵巨像", "藤蔓木妖"],
                "replace_scene_tags": ["机库", "工业舱室"],
                "replace_light_tags": ["青蓝冷雾", "体积光"],
                "replace_prop_tags": ["苔藓附生质感", "发光裂隙"],
                "replace_composition_tags": ["超广角全景", "低角度"],
                "subject_identity": "树灵巨像",
                "scene_group": "industrial",
                "scene_bucket": "special",
                "macro_direction": "bay_colossus_reveal",
            },
        ],
    }
)
_RUNTIME_STYLE_VARIANT_PROFILES: dict[str, list[_RuntimeStyleVariantProfile]] = {
    "真实感": [
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志感", "杂志编辑摄影"],
            "extra_fragments": ["时尚成片感更强", "人物视觉重心更偏封面肖像"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "生活纪实", "生活电影剧照"],
            "extra_fragments": ["叙事情绪更强", "保留生活化镜头瞬间感"],
        },
        {
            "style_lead": "纪实抓拍",
            "style_tags": ["真实感", "纪实抓拍", "街拍"],
            "extra_fragments": ["抓拍感更强", "人物状态更自然松弛"],
        },
        {
            "style_lead": "黑白摄影",
            "style_tags": ["真实感", "黑白摄影", "高对比黑白"],
            "extra_fragments": ["明暗反差更明确", "画面情绪更克制"],
        },
    ],
    "插画感": [
        {
            "style_lead": "厚涂插画",
            "style_tags": ["插画感", "厚涂", "手绘画风"],
            "extra_fragments": ["笔触塑形更明显", "角色塑造更偏概念插画"],
        },
        {
            "style_lead": "水彩线稿",
            "style_tags": ["插画感", "水彩线稿", "水彩"],
            "extra_fragments": ["边缘更轻盈", "色彩过渡更柔和"],
        },
        {
            "style_lead": "复古未来动漫",
            "style_tags": ["插画感", "90年代复古未来动漫", "OVA风"],
            "extra_fragments": ["动画叙事感更强", "角色更像复古番剧定帧"],
        },
        {
            "style_lead": "后印象派插画",
            "style_tags": ["插画感", "后印象派", "复古未来主义"],
            "extra_fragments": ["色块节奏更强", "画面更偏艺术海报"],
        },
    ],
    "CG感": [
        {
            "style_lead": "电影级CG",
            "style_tags": ["CG感", "PBR渲染", "商业CG海报"],
            "extra_fragments": ["体积光与材质表现更强", "角色更像高预算宣传图"],
        },
        {
            "style_lead": "概念设计稿",
            "style_tags": ["CG感", "概念设计稿", "游戏风"],
            "extra_fragments": ["识别度更强", "轮廓设计更明确"],
        },
        {
            "style_lead": "虚幻引擎渲染",
            "style_tags": ["CG感", "虚幻引擎", "3D渲染"],
            "extra_fragments": ["空间透视更强", "光影更偏实时引擎成片"],
        },
        {
            "style_lead": "Octane渲染",
            "style_tags": ["CG感", "Octane渲染", "高光材质"],
            "extra_fragments": ["高光材质更通透", "整体更偏商业CG成片"],
        },
    ],
    "古风": [
        {
            "style_lead": "古风电影剧照",
            "style_tags": ["古风", "国风美学", "古装定格"],
            "extra_fragments": ["人物仪态更偏古典写真", "服饰与气韵更统一", "庭院叙事更人间"],
        },
        {
            "style_lead": "工笔重彩",
            "style_tags": ["古风", "工笔重彩", "国风美学"],
            "extra_fragments": ["设色更华丽", "服饰纹样更突出", "回廊与器物更偏书卷气"],
        },
        {
            "style_lead": "玄幻古风",
            "style_tags": ["古风", "玄幻古风", "传奇气韵"],
            "extra_fragments": ["世界观氛围更强", "人物更有传奇感", "江湖行旅感更强"],
        },
        {
            "style_lead": "水墨写意",
            "style_tags": ["古风", "水墨", "空灵"],
            "extra_fragments": ["留白感更明显", "气韵更轻盈", "书卷留白更克制"],
        },
    ],
    "神话感": [
        {
            "style_lead": "神圣史诗",
            "style_tags": ["神话感", "神圣史诗", "神圣"],
            "extra_fragments": ["庄严感更强", "人物更像祭典主角", "祭典仪式感更明确"],
        },
        {
            "style_lead": "魔幻现实主义",
            "style_tags": ["神话感", "魔幻现实主义", "神话叙事"],
            "extra_fragments": ["现实与奇观混合更强", "人物叙事感更浓", "圣坛叙事更稳定"],
        },
        {
            "style_lead": "暗黑奇幻",
            "style_tags": ["神话感", "暗黑奇幻", "巴洛克"],
            "extra_fragments": ["明暗戏剧性更强", "角色更偏黑暗史诗", "神性压迫感更强"],
        },
        {
            "style_lead": "冰雪奇幻",
            "style_tags": ["神话感", "冰雪奇幻", "神性幻境"],
            "extra_fragments": ["冷冽神性更突出", "角色更偏幻境感", "云海幻境更纯粹"],
        },
    ],
}
_RUNTIME_STYLE_VARIANT_PROFILES.update(
    {
        "商业摄影": [
            {
                "style_lead": "商业摄影成片",
                "style_tags": ["商业棚拍主视觉", "品牌campaign影像", "产品级材质表达"],
                "extra_fragments": ["布光更像品牌 campaign", "材质与服装卖点更清晰"],
            },
            {
                "style_lead": "Lookbook摄影",
                "style_tags": ["Lookbook版型展示", "极简商品目录感", "商业站姿"],
                "extra_fragments": ["主体轮廓更干净", "服装结构与站姿更利于出图"],
            },
            {
                "style_lead": "产品广告摄影",
                "style_tags": ["产品广告主视觉", "金属展台广告", "物料质感广告"],
                "extra_fragments": ["画面更偏商业主视觉", "道具与材质细节更克制清楚"],
            },
        ],
        "时尚编辑": [
            {
                "style_lead": "时尚编辑摄影",
                "style_tags": ["主刊封面企划", "高级编辑片", "时装专题视觉"],
                "extra_fragments": ["版面感更强", "人物更像主刊企划中心"],
            },
            {
                "style_lead": "高级定制大片",
                "style_tags": ["高级定制服装企划", "高定campaign影像", "主刊时装叙事"],
                "extra_fragments": ["服装材质与身体轮廓关系更高级", "画面更像成片 campaign"],
            },
            {
                "style_lead": "胶片时装片",
                "style_tags": ["胶片时装专题", "时装片颗粒", "编辑部胶片感"],
                "extra_fragments": ["颗粒与色彩更像时装专题", "人物状态更自然但完成度高"],
            },
        ],
        "电影写实": [
            {
                "style_lead": "电影写实剧照",
                "style_tags": ["写实电影定格", "剧情片场瞬间", "叙事镜头"],
                "extra_fragments": ["叙事场面更完整", "人物像处在真实电影片段中"],
            },
            {
                "style_lead": "黑色电影感",
                "style_tags": ["冷硬黑片光影", "夜色悬疑剧照", "暗部层次"],
                "extra_fragments": ["明暗关系更戏剧化", "动作与视线更有故事张力"],
            },
            {
                "style_lead": "纪实电影摄影",
                "style_tags": ["纪实片场摄影", "长镜头生活感", "克制低饱和电影"],
                "extra_fragments": ["镜头更克制", "环境细节更像真实片场捕捉"],
            },
        ],
        "私房写实": [
            {
                "style_lead": "私房写实摄影",
                "style_tags": ["室内亲密写实", "窗纱私密光线", "柔和居家氛围"],
                "extra_fragments": ["室内呼吸感更强", "人物姿态更自然亲密"],
            },
            {
                "style_lead": "胶片私房",
                "style_tags": ["复古公寓私房", "暖胶片室内", "安静室内颗粒"],
                "extra_fragments": ["色温与颗粒更柔和", "画面更像安静室内胶片"],
            },
            {
                "style_lead": "高级私房",
                "style_tags": ["高级室内私房", "低饱和亲密影像", "克制肤色质感"],
                "extra_fragments": ["氛围更克制", "肤色与布料质感更干净"],
            },
        ],
        "复古动画": [
            {
                "style_lead": "复古动画定帧",
                "style_tags": ["怀旧赛璐璐定帧", "旧动画主视觉", "手绘动画色块"],
                "extra_fragments": ["画面更像经典动画主视觉", "线条与色块关系更明确"],
            },
            {
                "style_lead": "OVA复古动画",
                "style_tags": ["番剧定帧颗粒", "复古低保真动画", "旧时代角色卡"],
                "extra_fragments": ["角色更像番剧定帧", "颗粒与低保真质感更自然"],
            },
            {
                "style_lead": "复古未来动画",
                "style_tags": ["霓虹复古动画海报", "旧科幻动画感", "动画海报构图"],
                "extra_fragments": ["霓虹与旧动画质感结合更强", "构图更像动画海报"],
            },
        ],
        "东方赛博": [
            {
                "style_lead": "东方赛博CG",
                "style_tags": ["东方赛博主视觉", "武侠朋克城市", "赛博东方器物"],
                "extra_fragments": ["东方器物与赛博结构关系更统一", "人物更像高预算世界观主视觉"],
            },
            {
                "style_lead": "东方赛博机甲",
                "style_tags": ["东方装甲角色", "机械经络结构", "赛博金属服饰"],
                "extra_fragments": ["机械结构与服装骨架更清晰", "金属与霓虹反射更克制"],
            },
            {
                "style_lead": "赛博雨夜",
                "style_tags": ["霓虹雨巷任务感", "湿地面广告反射", "城市全息纵深"],
                "extra_fragments": ["雨夜反射更强", "角色与城市纵深关系更完整"],
            },
        ],
        "硬表面科幻": [
            {
                "style_lead": "硬表面科幻CG",
                "style_tags": ["硬表面科幻主视觉", "工业外壳结构", "机械材质层次"],
                "extra_fragments": ["工业结构更清楚", "装备、地面和背景材质更统一"],
            },
            {
                "style_lead": "工业科幻",
                "style_tags": ["科幻棚景工业光", "冷调设备空间", "工程舱室质感"],
                "extra_fragments": ["空间更像真实科幻棚景", "机械尺度与人物比例更稳定"],
            },
            {
                "style_lead": "太空歌剧",
                "style_tags": ["星舰走廊史诗", "宇航装备主视觉", "深空尺度感"],
                "extra_fragments": ["空间纵深更宏大", "人物像处在高预算科幻场景中"],
            },
        ],
        "国风电影": [
            {
                "style_lead": "国风电影剧照",
                "style_tags": ["国风片场定格", "礼制空间叙事", "古装电影主视觉"],
                "extra_fragments": ["人物与服饰更像古装电影定格", "场景礼制与光影更统一"],
            },
            {
                "style_lead": "宋韵园林电影感",
                "style_tags": ["宋韵园林镜头", "庭院纸窗气韵", "雅致衣冠秩序"],
                "extra_fragments": ["庭院空间更克制", "服饰纹样与发髻结构更清楚"],
            },
            {
                "style_lead": "工笔电影感",
                "style_tags": ["设色华服电影感", "东方纹样叙事", "古典海报设色"],
                "extra_fragments": ["色彩更有国风设色层次", "人物更像古风主视觉海报"],
            },
        ],
        "武侠电影": [
            {
                "style_lead": "武侠电影剧照",
                "style_tags": ["江湖电影定格", "刀剑出场动势", "侠客主视觉"],
                "extra_fragments": ["动作出场感更强", "兵器、衣袍和空间动势更统一"],
            },
            {
                "style_lead": "港式武侠胶片",
                "style_tags": ["老港武行镜头", "屋檐雨夜江湖", "胶片江湖气"],
                "extra_fragments": ["颗粒与侧逆光更像老港片", "江湖气更集中"],
            },
            {
                "style_lead": "水墨武侠",
                "style_tags": ["留白侠影构图", "衣袍风势线", "远山武侠意境"],
                "extra_fragments": ["留白和衣袍动势更明显", "人物更偏意境型武侠主角"],
            },
        ],
        "暗黑奇幻": [
            {
                "style_lead": "暗黑奇幻史诗",
                "style_tags": ["暗黑史诗主视觉", "黑铁王座氛围", "戏剧烛火阴影"],
                "extra_fragments": ["戏剧光影更强", "人物更像黑暗史诗分支主角"],
            },
            {
                "style_lead": "巫术暗黑",
                "style_tags": ["秘仪黑暗叙事", "咒术圣坛气场", "符器阴影空间"],
                "extra_fragments": ["仪式叙事更明确", "道具与神秘空间关系更完整"],
            },
            {
                "style_lead": "冰雪暗黑奇幻",
                "style_tags": ["霜雾暗黑神殿", "冷辉命运感", "冰裂圣域气息"],
                "extra_fragments": ["冷雾与神性更克制", "角色气场更偏命运感"],
            },
        ],
    }
)
_RUNTIME_STYLE_TRACK_OVERRIDES: dict[tuple[str, str], list[_RuntimeStyleVariantProfile]] = {
    ("真实感", "商业摄影"): [
        {
            "style_lead": "时装广告大片",
            "style_tags": ["真实感", "时装广告", "商业广告大片"],
            "extra_fragments": ["灯光更偏商业大片成片", "人物更像品牌主视觉主角"],
        },
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志感", "杂志编辑摄影"],
            "extra_fragments": ["版面感更强", "成片更偏时尚编辑企划"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "生活纪实", "生活电影剧照"],
            "extra_fragments": ["叙事感保留但更克制", "人物状态更像广告剧情定格"],
        },
        {
            "style_lead": "棚拍写真",
            "style_tags": ["真实感", "棚拍", "写真"],
            "extra_fragments": ["布光更干净利落", "主体轮廓更利于商业出图"],
        },
    ],
    ("真实感", "都市电影人文"): [
        {
            "style_lead": "都市电影人文",
            "style_tags": ["真实感", "都市电影人文", "纪实电影摄影"],
            "extra_fragments": ["城市叙事更克制", "人物更像电影人文片段主角"],
        },
        {
            "style_lead": "35mm胶片摄影",
            "style_tags": ["真实感", "35mm胶片摄影", "生活电影剧照"],
            "extra_fragments": ["胶片颗粒与瞬时感更自然", "环境更像真实街头截帧"],
        },
        {
            "style_lead": "生活流写实",
            "style_tags": ["真实感", "生活流写实", "街头纪实"],
            "extra_fragments": ["生活细节更自然", "人物状态更像日常叙事片段"],
        },
        {
            "style_lead": "纪实抓拍",
            "style_tags": ["真实感", "纪实抓拍", "街拍"],
            "extra_fragments": ["抓拍味更强", "画面更像被真实捕捉到的片刻"],
        },
    ],
    ("真实感", "时尚编辑商业广告"): [
        {
            "style_lead": "高端时尚编辑肖像",
            "style_tags": ["真实感", "高端时尚编辑肖像", "大画幅棚拍"],
            "extra_fragments": ["封面企划感更强", "人物更像主刊封面主角"],
        },
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志编辑摄影", "广告成片质感"],
            "extra_fragments": ["版面与商业感更完整", "主体更偏高端时尚广告人物"],
        },
        {
            "style_lead": "时装广告大片",
            "style_tags": ["真实感", "时装广告", "商业广告大片"],
            "extra_fragments": ["布光更偏硬朗大片", "服装与材质更像品牌 campaign"],
        },
        {
            "style_lead": "韩系极简影像",
            "style_tags": ["真实感", "韩系极简影像", "中画幅质感"],
            "extra_fragments": ["极简棚拍更克制", "主体轮廓与肤色更偏冷静高级"],
        },
    ],
    ("真实感", "日韩影像"): [
        {
            "style_lead": "日韩影像",
            "style_tags": ["真实感", "日韩影像", "日系电影感"],
            "extra_fragments": ["情绪更像东亚电影静帧", "人物更偏含蓄生活化镜头"],
        },
        {
            "style_lead": "韩系极简影像",
            "style_tags": ["真实感", "韩系极简影像", "生活流写实"],
            "extra_fragments": ["背景更简洁", "人物更偏韩系极简广告叙事"],
        },
        {
            "style_lead": "35mm胶片摄影",
            "style_tags": ["真实感", "35mm胶片摄影", "电影胶片look"],
            "extra_fragments": ["胶片颗粒更自然", "氛围更偏日系长镜头质感"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "生活电影剧照", "低饱和"],
            "extra_fragments": ["生活感更松弛", "镜头更像安静叙事片段"],
        },
    ],
    ("真实感", "生活纪实"): [
        {
            "style_lead": "纪实抓拍",
            "style_tags": ["真实感", "纪实抓拍", "街拍"],
            "extra_fragments": ["状态更像街头真实瞬间", "人物情绪更松弛自然"],
        },
        {
            "style_lead": "手机抓拍",
            "style_tags": ["真实感", "手机抓拍", "无滤镜直出"],
            "extra_fragments": ["瞬时感更强", "画面更像随手拍到的自然片段"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "生活纪实", "生活电影剧照"],
            "extra_fragments": ["叙事氛围更完整", "人物与环境互动更强"],
        },
        {
            "style_lead": "黑白摄影",
            "style_tags": ["真实感", "黑白摄影", "纪实"],
            "extra_fragments": ["纪实情绪更凝练", "画面更偏故事摄影"],
        },
    ],
    ("真实感", "私房写实"): [
        {
            "style_lead": "私房写真",
            "style_tags": ["真实感", "私房写真", "微醺感"],
            "extra_fragments": ["亲密感更强", "人物状态更偏私密叙事"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "私密氛围", "生活纪实"],
            "extra_fragments": ["情绪更像室内镜头瞬间", "画面更强调呼吸感"],
        },
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志感", "时尚写真"],
            "extra_fragments": ["人物更像室内时尚企划", "成片更偏审美化肖像"],
        },
        {
            "style_lead": "黑白摄影",
            "style_tags": ["真实感", "黑白摄影", "高对比黑白"],
            "extra_fragments": ["情绪更克制冷静", "人物轮廓更突出"],
        },
    ],
    ("插画感", "复古OVA"): [
        {
            "style_lead": "复古未来动漫",
            "style_tags": ["插画感", "90年代复古未来动漫", "OVA风"],
            "extra_fragments": ["角色更像动画定帧", "叙事性更偏番剧海报"],
        },
        {
            "style_lead": "怀旧动画海报",
            "style_tags": ["插画感", "怀旧动画", "复古动画"],
            "extra_fragments": ["画面更像经典动画主视觉", "色彩关系更偏旧时代赛璐璐感"],
        },
        {
            "style_lead": "厚涂插画",
            "style_tags": ["插画感", "厚涂", "手绘画风"],
            "extra_fragments": ["笔触塑形更明显", "人物设计感更强"],
        },
        {
            "style_lead": "水彩线稿",
            "style_tags": ["插画感", "水彩线稿", "水彩"],
            "extra_fragments": ["轮廓更轻盈", "画面更偏抒情插图"],
        },
    ],
    ("CG感", "赛博雨夜"): [
        {
            "style_lead": "虚幻引擎渲染",
            "style_tags": ["CG感", "虚幻引擎", "赛博朋克"],
            "extra_fragments": ["霓虹空间感更强", "人物更像赛博潜入任务现场主角"],
        },
        {
            "style_lead": "Octane渲染",
            "style_tags": ["CG感", "Octane渲染", "电影剧照"],
            "extra_fragments": ["材质高光更鲜明", "雨夜反射更偏湿地面与装备材质反馈"],
        },
        {
            "style_lead": "概念设计稿",
            "style_tags": ["CG感", "概念设计稿", "游戏风"],
            "extra_fragments": ["识别度更强", "人物更像世界观主视觉角色"],
        },
        {
            "style_lead": "电影级CG",
            "style_tags": ["CG感", "PBR渲染", "未来科技感"],
            "extra_fragments": ["整体更像高完成度科幻任务场景", "角色完成度更偏可执行任务镜头"],
        },
    ],
    ("CG感", "工业科幻"): [
        {
            "style_lead": "概念设计稿",
            "style_tags": ["CG感", "概念设计稿", "游戏风"],
            "extra_fragments": ["设定说明感更强", "人物更像工业科幻角色方案图"],
        },
        {
            "style_lead": "电影级CG",
            "style_tags": ["CG感", "PBR渲染", "商业CG海报"],
            "extra_fragments": ["结构材质更厚重", "空间层次更像科幻布景成片"],
        },
        {
            "style_lead": "虚幻引擎渲染",
            "style_tags": ["CG感", "虚幻引擎", "3D渲染"],
            "extra_fragments": ["透视与空间关系更强", "人物更像实时引擎宣传图"],
        },
        {
            "style_lead": "Octane渲染",
            "style_tags": ["CG感", "Octane渲染", "概念设计稿"],
            "extra_fragments": ["质感更精致", "金属与灯光更偏商业海报"],
        },
    ],
    ("CG感", "东方赛博武侠朋克"): [
        {
            "style_lead": "东方赛博机甲",
            "style_tags": ["CG感", "东方赛博武侠朋克", "东方赛博机甲"],
            "extra_fragments": ["东方兵器与赛博骨架结合更强", "人物更像武侠朋克世界观主角"],
        },
        {
            "style_lead": "电影级CG",
            "style_tags": ["CG感", "机能赛博", "全息界面"],
            "extra_fragments": ["城市空间更偏高密度赛博武侠片场", "材质与霓虹反射更像高预算 CG 成片"],
        },
        {
            "style_lead": "概念设计稿",
            "style_tags": ["CG感", "能量刀", "游戏CG质感"],
            "extra_fragments": ["道具识别度更强", "人物更像游戏世界观 key visual 角色"],
        },
        {
            "style_lead": "虚幻引擎渲染",
            "style_tags": ["CG感", "PBR渲染", "赛博街区"],
            "extra_fragments": ["镜头更像实时引擎宣传图", "环境纵深与动作空间更完整"],
        },
    ],
    ("古风", "古风园林"): [
        {
            "style_lead": "工笔重彩",
            "style_tags": ["古风", "工笔重彩", "国风美学"],
            "extra_fragments": ["园林细节与服饰纹样更突出", "人物更偏古典仕女企划"],
        },
        {
            "style_lead": "古风电影剧照",
            "style_tags": ["古风", "国风美学", "古装定格"],
            "extra_fragments": ["氛围更像古装剧定格", "人物与园林空间更协调"],
        },
        {
            "style_lead": "水墨写意",
            "style_tags": ["古风", "水墨", "空灵"],
            "extra_fragments": ["留白更有呼吸感", "人物气韵更轻盈"],
        },
        {
            "style_lead": "玄幻古风",
            "style_tags": ["古风", "玄幻古风", "传奇气韵"],
            "extra_fragments": ["世界观感更强", "人物更偏传奇感古风人像"],
        },
    ],
    ("古风", "东方古风武侠"): [
        {
            "style_lead": "港式武侠胶片",
            "style_tags": ["古风", "东方古风武侠", "港式武侠"],
            "extra_fragments": ["动作出场感更强", "人物更像港式武侠电影主角登场"],
        },
        {
            "style_lead": "古风电影剧照",
            "style_tags": ["古风", "古风电影氛围", "武侠剧照感"],
            "extra_fragments": ["镜头更偏武侠叙事定格", "衣袍与气流更有动势"],
        },
        {
            "style_lead": "35mm胶片摄影",
            "style_tags": ["古风", "35mm胶片摄影", "港式武侠胶片"],
            "extra_fragments": ["颗粒与光晕更明显", "画面更像老港片定格"],
        },
        {
            "style_lead": "雾景实拍感",
            "style_tags": ["古风", "雾景实拍感", "低饱和"],
            "extra_fragments": ["雾气与空间层次更强", "环境更像实拍片场而非插画背景"],
        },
    ],
    ("古风", "国风暗黑志怪"): [
        {
            "style_lead": "志怪古风",
            "style_tags": ["古风", "志怪古风", "港风惊悚志怪"],
            "extra_fragments": ["惊悚氛围更浓", "人物更像志怪叙事中心角色"],
        },
        {
            "style_lead": "雾景实拍感",
            "style_tags": ["古风", "雾景实拍感", "黑色电影硬光"],
            "extra_fragments": ["冷雾与侧光更克制", "环境更像雾夜惊悚剧照"],
        },
        {
            "style_lead": "古风电影剧照",
            "style_tags": ["古风", "古风电影氛围", "低饱和"],
            "extra_fragments": ["场面更像暗黑古装电影定格", "人物轮廓更强调惊悚压迫感"],
        },
        {
            "style_lead": "港式武侠胶片",
            "style_tags": ["古风", "港式武侠胶片", "复古颗粒"],
            "extra_fragments": ["老港片诡谲感更强", "色彩更偏暗绿褐与冷雾"],
        },
    ],
    ("古风", "武侠剧照"): [
        {
            "style_lead": "古风电影剧照",
            "style_tags": ["古风", "国风美学", "古装定格"],
            "extra_fragments": ["出场感更强", "人物更像武侠定妆宣传照"],
        },
        {
            "style_lead": "玄幻古风",
            "style_tags": ["古风", "玄幻古风", "传奇气韵"],
            "extra_fragments": ["动作张力更强", "人物更偏江湖传奇主角"],
        },
        {
            "style_lead": "水墨写意",
            "style_tags": ["古风", "水墨", "空灵"],
            "extra_fragments": ["气韵更克制", "人物更偏东方意境肖像"],
        },
        {
            "style_lead": "工笔重彩",
            "style_tags": ["古风", "工笔重彩", "国风美学"],
            "extra_fragments": ["服饰细节更明确", "人物更像古风海报角色"],
        },
    ],
    ("神话感", "神殿史诗"): [
        {
            "style_lead": "神圣史诗",
            "style_tags": ["神话感", "神圣史诗", "神圣"],
            "extra_fragments": ["仪式氛围更强", "人物更像祭典中心角色"],
        },
        {
            "style_lead": "魔幻现实主义",
            "style_tags": ["神话感", "魔幻现实主义", "神话叙事"],
            "extra_fragments": ["奇观与现实融合更自然", "人物更偏叙事型神话主角"],
        },
        {
            "style_lead": "冰雪奇幻",
            "style_tags": ["神话感", "冰雪奇幻", "神性幻境"],
            "extra_fragments": ["冷冽神性更突出", "人物更偏幻境感神话肖像"],
        },
        {
            "style_lead": "暗黑奇幻",
            "style_tags": ["神话感", "暗黑奇幻", "巴洛克"],
            "extra_fragments": ["戏剧光影更强", "角色更像黑暗史诗分支主角"],
        },
    ],
    ("神话感", "西方奇幻神话史诗"): [
        {
            "style_lead": "西方奇幻史诗",
            "style_tags": ["神话感", "西方奇幻史诗", "神圣史诗"],
            "extra_fragments": ["奇观尺度更大", "人物更像西幻神话主角"],
        },
        {
            "style_lead": "暗黑奇幻",
            "style_tags": ["神话感", "暗黑奇幻", "巴洛克"],
            "extra_fragments": ["盔甲与神殿感更浓", "画面更偏西幻史诗黑暗分支"],
        },
        {
            "style_lead": "冰雪奇幻",
            "style_tags": ["神话感", "冰雪奇幻", "体积光"],
            "extra_fragments": ["冰雾与神性更突出", "氛围更偏西幻高地奇观"],
        },
        {
            "style_lead": "电影级CG",
            "style_tags": ["神话感", "电影级CG", "史诗感单幅画面"],
            "extra_fragments": ["镜头更像西幻电影主视觉", "空间透视更偏奇观场景化"],
        },
    ],
}
_RUNTIME_STYLE_SCENE_CUES: dict[tuple[str, str], list[str]] = {
    ("真实感", "city"): ["都市环境参与感更强", "人物与街景关系更完整"],
    ("真实感", "indoor"): ["室内布光更完整", "人物与前后景层次更稳定"],
    ("真实感", "nature"): ["自然空气感更明显", "环境留白更舒展"],
    ("插画感", "nature"): ["背景更像叙事绘本场景", "色彩节奏更有层次"],
    ("CG感", "industrial"): ["机械结构与空间透视更突出", "材质层级更清晰"],
    ("CG感", "city"): ["赛博城市空间感更强", "环境反射更偏设定场景"],
    ("古风", "ancient"): ["古典空间语义更完整", "人物与东方景致更协调"],
    ("神话感", "sacred"): ["仪式空间感更强", "画面更偏神性叙事"],
}
_GENERIC_SCENE_CUES: dict[str, list[str]] = {
    "indoor": ["空间层次更稳定", "主体与布景关系更清晰"],
    "city": ["环境参与感更强", "人物与空间透视更完整"],
    "nature": ["空气感更明显", "景深与远近关系更自然"],
    "industrial": ["结构质感更突出", "材质关系更清楚"],
    "ancient": ["东方场景语义更统一", "人物与环境气质更协调"],
    "sacred": ["仪式感更明确", "空间氛围更庄严"],
    "minimal": ["背景控制更克制", "视觉中心更集中"],
}
_RUNTIME_STYLE_IDENTITY_OVERRIDES: dict[tuple[str, str], list[_RuntimeStyleVariantProfile]] = {
    ("真实感", "lead_singer"): [
        {
            "style_lead": "夜间闪光摄影",
            "style_tags": ["真实感", "夜间闪光摄影", "时尚街拍"],
            "extra_fragments": ["人物更像舞台外演出主角", "演出余韵与现场感更强"],
        },
        {
            "style_lead": "时装广告大片",
            "style_tags": ["真实感", "时装广告", "商业广告大片"],
            "extra_fragments": ["人物更像乐队主视觉封面主角", "表现欲更强"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "电影剧照", "生活电影剧照"],
            "extra_fragments": ["人物更像音乐题材影片定格主角", "情绪更偏演出叙事"],
        },
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志感", "杂志编辑摄影"],
            "extra_fragments": ["人物更偏音乐企划封面肖像", "版面感更完整"],
        },
    ],
    ("真实感", "idol"): [
        {
            "style_lead": "时装广告大片",
            "style_tags": ["真实感", "时装广告", "商业广告大片"],
            "extra_fragments": ["人物更像企划封面主角", "镜头表现欲更强"],
        },
        {
            "style_lead": "夜间闪光摄影",
            "style_tags": ["真实感", "夜间闪光摄影", "时尚街拍"],
            "extra_fragments": ["舞台外抓拍感更强", "人物更像明星街头出片瞬间"],
        },
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志感", "杂志编辑摄影"],
            "extra_fragments": ["版面感更强", "人物更偏人物企划封面"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "电影剧照", "生活电影剧照"],
            "extra_fragments": ["叙事感保留但更像明星短片定格", "人物完成度更高"],
        },
    ],
    ("真实感", "student"): [
        {
            "style_lead": "青春写真",
            "style_tags": ["真实感", "写真", "胶片感"],
            "extra_fragments": ["人物更像校园企划主角", "状态更偏青春日常出片"],
        },
        {
            "style_lead": "CCD感",
            "style_tags": ["真实感", "CCD感", "纪实抓拍"],
            "extra_fragments": ["随拍感更强", "画面更像放学后的即时抓拍"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "电影剧照", "生活电影剧照"],
            "extra_fragments": ["人物更像青春片定格主角", "情绪更偏校园叙事"],
        },
        {
            "style_lead": "纪实抓拍",
            "style_tags": ["真实感", "纪实抓拍", "手机抓拍"],
            "extra_fragments": ["动作更自然", "人物更像校园场景中的真实瞬间"],
        },
    ],
    ("真实感", "office_lady"): [
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志编辑摄影", "杂志感"],
            "extra_fragments": ["人物更像都市职场封面主角", "职业干练感更明确"],
        },
        {
            "style_lead": "棚拍写真",
            "style_tags": ["真实感", "棚拍", "写真"],
            "extra_fragments": ["人物更偏职业人物企划肖像", "轮廓表达更利落"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "电影剧照", "生活电影剧照"],
            "extra_fragments": ["人物更像都市职场剧定格主角", "叙事感更稳定"],
        },
        {
            "style_lead": "黑白摄影",
            "style_tags": ["真实感", "黑白摄影", "高对比黑白"],
            "extra_fragments": ["秩序感更强", "人物更偏职业主题海报肖像"],
        },
    ],
    ("真实感", "bartender"): [
        {
            "style_lead": "夜间闪光摄影",
            "style_tags": ["真实感", "夜间闪光摄影", "时尚街拍"],
            "extra_fragments": ["人物更像夜场人物企划主角", "夜场叙事感更强"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "电影剧照", "生活电影剧照"],
            "extra_fragments": ["人物更像酒吧题材影片定格主角", "情绪更偏夜色叙事"],
        },
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志编辑摄影", "杂志感"],
            "extra_fragments": ["人物更偏夜生活专题封面", "场景控制感更明确"],
        },
        {
            "style_lead": "黑白摄影",
            "style_tags": ["真实感", "黑白摄影", "纪实"],
            "extra_fragments": ["人物更偏夜场纪实肖像", "情绪张力更克制"],
        },
    ],
    ("真实感", "researcher"): [
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志编辑摄影", "杂志感"],
            "extra_fragments": ["人物更像实验专题主角", "理性探索感更明确"],
        },
        {
            "style_lead": "纪实抓拍",
            "style_tags": ["真实感", "纪实", "纪实抓拍"],
            "extra_fragments": ["人物更像研究现场的真实主角", "观察记录感更强"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "电影剧照", "生活电影剧照"],
            "extra_fragments": ["人物更像科研题材剧定格主角", "叙事完整度更高"],
        },
        {
            "style_lead": "黑白摄影",
            "style_tags": ["真实感", "黑白摄影", "高对比黑白"],
            "extra_fragments": ["人物更偏理性专题肖像", "思辨感更强"],
        },
    ],
    ("插画感", "idol"): [
        {
            "style_lead": "复古未来动漫",
            "style_tags": ["插画感", "90年代复古未来动漫", "OVA风"],
            "extra_fragments": ["角色更像偶像企划动画海报", "人物视觉中心更强"],
        },
        {
            "style_lead": "厚涂插画",
            "style_tags": ["插画感", "厚涂", "手绘画风"],
            "extra_fragments": ["舞台视觉感更强", "人物更偏宣传插画主角"],
        },
        {
            "style_lead": "水彩线稿",
            "style_tags": ["插画感", "水彩线稿", "水彩"],
            "extra_fragments": ["情绪更柔和", "角色更像纪念插图封面"],
        },
        {
            "style_lead": "后印象派插画",
            "style_tags": ["插画感", "后印象派", "复古未来主义"],
            "extra_fragments": ["色块更有海报感", "人物更偏艺术企划主视觉"],
        },
    ],
    ("插画感", "student"): [
        {
            "style_lead": "水彩线稿",
            "style_tags": ["插画感", "水彩线稿", "水彩"],
            "extra_fragments": ["人物更像青春绘本主角", "线条情绪更轻盈"],
        },
        {
            "style_lead": "复古未来动漫",
            "style_tags": ["插画感", "90年代复古未来动漫", "OVA风"],
            "extra_fragments": ["人物更像校园番剧定帧主角", "叙事感更偏青春动画海报"],
        },
        {
            "style_lead": "厚涂插画",
            "style_tags": ["插画感", "厚涂", "手绘画风"],
            "extra_fragments": ["人物更偏角色海报企划", "青春张力更明显"],
        },
        {
            "style_lead": "后印象派插画",
            "style_tags": ["插画感", "后印象派", "复古未来主义"],
            "extra_fragments": ["色块情绪更强", "人物更偏校园艺术海报主角"],
        },
    ],
    ("插画感", "lead_singer"): [
        {
            "style_lead": "厚涂插画",
            "style_tags": ["插画感", "厚涂", "手绘画风"],
            "extra_fragments": ["人物更像乐队海报主角", "舞台张力更强"],
        },
        {
            "style_lead": "复古未来动漫",
            "style_tags": ["插画感", "90年代复古未来动漫", "OVA风"],
            "extra_fragments": ["人物更像音乐番剧定帧主角", "演出叙事感更明显"],
        },
        {
            "style_lead": "后印象派插画",
            "style_tags": ["插画感", "后印象派", "复古未来主义"],
            "extra_fragments": ["色块节奏更像演出海报", "人物更偏艺术企划主视觉"],
        },
        {
            "style_lead": "水彩线稿",
            "style_tags": ["插画感", "水彩线稿", "水彩"],
            "extra_fragments": ["人物更偏抒情音乐封面", "情绪更柔和"],
        },
    ],
    ("CG感", "warrior"): [
        {
            "style_lead": "战术机能CG",
            "style_tags": ["CG感", "战术装甲", "高速机动"],
            "extra_fragments": ["人物更像战斗主视觉主角", "战斗定位更明确", "重甲结构与受力关系更清楚", "前线压迫感与冲锋姿态更明确"],
        },
        {
            "style_lead": "机能战斗海报",
            "style_tags": ["CG感", "机能战士", "战场动势"],
            "extra_fragments": ["英雄感更强", "角色更像战术出击镜头中的前线主角", "前线压迫感与冲锋姿态更明确"],
        },
        {
            "style_lead": "实时战场演示",
            "style_tags": ["CG感", "战术演示", "空间突进"],
            "extra_fragments": ["空间张力更强", "人物更偏实时演示定格", "冲锋路径与机动方向更清晰"],
        },
        {
            "style_lead": "高预算机甲海报",
            "style_tags": ["CG感", "机甲质感", "战术主视觉"],
            "extra_fragments": ["材质更精致", "角色更偏重装机动角色镜头", "装甲轮廓与前线空间尺度更稳定"],
        },
    ],
    ("CG感", "female_warrior"): [
        {
            "style_lead": "概念设计稿",
            "style_tags": ["CG感", "女武士设定", "战斗草图"],
            "extra_fragments": ["人物更像女武士主视觉主角", "英气与战斗定位更明确"],
        },
        {
            "style_lead": "电影级CG",
            "style_tags": ["CG感", "PBR渲染", "女武士海报"],
            "extra_fragments": ["英雄气场更强", "人物更像女武士战备镜头主角"],
        },
        {
            "style_lead": "虚幻引擎渲染",
            "style_tags": ["CG感", "虚幻引擎", "3D渲染"],
            "extra_fragments": ["空间张力更强", "人物更像战斗演示定格主角"],
        },
        {
            "style_lead": "Octane渲染",
            "style_tags": ["CG感", "Octane渲染", "概念设计稿"],
            "extra_fragments": ["甲胄材质更精致", "人物更偏重甲角色设定镜头"],
        },
    ],
    ("CG感", "mechanic"): [
        {
            "style_lead": "概念设计稿",
            "style_tags": ["CG感", "概念设计稿", "游戏风"],
            "extra_fragments": ["人物更像机械维护主角", "功能分工感更明确"],
        },
        {
            "style_lead": "虚幻引擎渲染",
            "style_tags": ["CG感", "虚幻引擎", "3D渲染"],
            "extra_fragments": ["机修空间感更强", "人物更像工业科幻演示定格"],
        },
        {
            "style_lead": "电影级CG",
            "style_tags": ["CG感", "PBR渲染", "电影剧照"],
            "extra_fragments": ["机械协作感更强", "人物更像工业基地宣传主角"],
        },
        {
            "style_lead": "Octane渲染",
            "style_tags": ["CG感", "Octane渲染", "概念设计稿"],
            "extra_fragments": ["金属与工具材质更清晰", "人物更偏高预算设定海报"],
        },
    ],
    ("CG感", "agent"): [
        {
            "style_lead": "概念设计稿",
            "style_tags": ["CG感", "概念设计稿", "游戏风"],
            "extra_fragments": ["人物更像潜入任务主视觉主角", "装备特征更明确", "通讯器与潜入工具更具体", "霓虹雨巷与目标现场关系更明确"],
        },
        {
            "style_lead": "电影级CG",
            "style_tags": ["CG感", "PBR渲染", "潜入任务感"],
            "extra_fragments": ["人物更像夜间潜入行动主角", "任务紧张感更强", "霓虹雨巷与目标现场关系更明确", "湿地面反射与装备高光反馈更明确"],
        },
        {
            "style_lead": "虚幻引擎渲染",
            "style_tags": ["CG感", "虚幻引擎", "3D渲染"],
            "extra_fragments": ["空间潜入感更强", "人物更像实时演示中的任务主角", "低位追踪机位与狭窄通道压迫感更强", "低位追踪机位更明确"],
        },
        {
            "style_lead": "Octane渲染",
            "style_tags": ["CG感", "Octane渲染", "概念设计稿"],
            "extra_fragments": ["装备材质更精致", "人物更偏战术装备特写镜头", "湿地面反射与装备高光反馈更明确"],
        },
    ],
    ("古风", "warrior"): [
        {
            "style_lead": "古风侠客定格",
            "style_tags": ["古风", "侠客定格", "刀光行走"],
            "extra_fragments": ["人物更像武侠定妆宣传照", "出场感更强"],
        },
        {
            "style_lead": "江湖传奇章",
            "style_tags": ["古风", "江湖传奇", "武行叙事"],
            "extra_fragments": ["江湖传奇感更强", "人物更像故事主角海报"],
        },
        {
            "style_lead": "水墨写意",
            "style_tags": ["古风", "水墨", "侠影留白"],
            "extra_fragments": ["东方气韵更突出", "人物更偏意境型侠客肖像"],
        },
        {
            "style_lead": "工笔武行",
            "style_tags": ["古风", "工笔武行", "江湖主角"],
            "extra_fragments": ["服饰刻画更明确", "人物更偏主视觉海报"],
        },
    ],
    ("古风", "female_warrior"): [
        {
            "style_lead": "古风电影剧照",
            "style_tags": ["古风", "武侠定格", "国风美学"],
            "extra_fragments": ["人物更像女武士定妆宣传照", "出场气场更强"],
        },
        {
            "style_lead": "玄幻古风",
            "style_tags": ["古风", "女武士叙事", "战意"],
            "extra_fragments": ["战斗感与英气更强", "人物更像传奇女武士主角"],
        },
        {
            "style_lead": "工笔重彩",
            "style_tags": ["古风", "女武士工笔", "华服甲胄"],
            "extra_fragments": ["甲胄与服饰刻画更明确", "人物更偏主视觉海报"],
        },
        {
            "style_lead": "水墨写意",
            "style_tags": ["古风", "女武士水墨", "留白"],
            "extra_fragments": ["东方气韵更克制", "人物更偏意境型女武士肖像"],
        },
    ],
    ("古风", "goddess"): [
        {
            "style_lead": "工笔重彩",
            "style_tags": ["古风", "神女工笔", "云纹华服"],
            "extra_fragments": ["人物更像神女仪典主角", "服饰与神性装饰更突出"],
        },
        {
            "style_lead": "古风电影剧照",
            "style_tags": ["古风", "云庭神女", "云庭定格"],
            "extra_fragments": ["人物更像神女传说定格形象", "气场更偏庄严叙事"],
        },
        {
            "style_lead": "水墨写意",
            "style_tags": ["古风", "神女水墨", "云雾留白"],
            "extra_fragments": ["人物更偏空灵神女意境肖像", "留白感更强"],
        },
        {
            "style_lead": "玄幻古风",
            "style_tags": ["古风", "神女史诗", "天命感"],
            "extra_fragments": ["世界观感更强", "人物更偏东方神话主角"],
        },
    ],
    ("古风", "queen"): [
        {
            "style_lead": "工笔重彩",
            "style_tags": ["古风", "工笔重彩", "国风美学"],
            "extra_fragments": ["人物更像王权叙事主角", "礼制与华服表达更突出"],
        },
        {
            "style_lead": "古风电影剧照",
            "style_tags": ["古风", "国风美学", "王朝定格"],
            "extra_fragments": ["人物更像王朝题材定格主角", "统御感更明确"],
        },
        {
            "style_lead": "玄幻古风",
            "style_tags": ["古风", "玄幻古风", "史诗感"],
            "extra_fragments": ["人物更像传奇王权主角", "世界观压场感更强"],
        },
        {
            "style_lead": "水墨写意",
            "style_tags": ["古风", "水墨", "空灵"],
            "extra_fragments": ["人物更偏克制型王者肖像", "气韵更沉稳"],
        },
    ],
    ("古风", "priest"): [
        {
            "style_lead": "工笔重彩",
            "style_tags": ["古风", "祭司工笔", "祭仪纹样"],
            "extra_fragments": ["人物更像古典祭仪主角", "礼制与服饰表达更明确"],
        },
        {
            "style_lead": "古风电影剧照",
            "style_tags": ["古风", "祭司定格", "庄严叙事"],
            "extra_fragments": ["人物更像祭司题材古装定格主角", "庄严感更稳定"],
        },
        {
            "style_lead": "水墨写意",
            "style_tags": ["古风", "祭司水墨", "香火留白"],
            "extra_fragments": ["人物更偏东方祭仪意境肖像", "留白感更强"],
        },
        {
            "style_lead": "玄幻古风",
            "style_tags": ["古风", "祭仪史诗", "香火神谕"],
            "extra_fragments": ["世界观祭仪感更强", "人物更像神谕叙事主角"],
        },
    ],
    ("神话感", "sacred"): [
        {
            "style_lead": "神圣史诗",
            "style_tags": ["神话感", "神坛叙事", "神性主视觉"],
            "extra_fragments": ["人物更像神谕中心角色", "气场更偏神性主视觉"],
        },
        {
            "style_lead": "冰雪圣坛",
            "style_tags": ["神话感", "霜辉圣坛", "圣洁幻境"],
            "extra_fragments": ["冷冽神性更强", "人物更偏圣洁幻境形象"],
        },
        {
            "style_lead": "神谕现实",
            "style_tags": ["神话感", "神谕现实", "圣域叙事"],
            "extra_fragments": ["叙事性更强", "人物更像神话故事主角"],
        },
        {
            "style_lead": "暗黑奇幻",
            "style_tags": ["神话感", "暗影圣坛", "神性海报"],
            "extra_fragments": ["戏剧张力更强", "人物更偏命运感神话海报"],
        },
    ],
    ("神话感", "goddess"): [
        {
            "style_lead": "神圣史诗",
            "style_tags": ["神话感", "神女主祭", "神圣"],
            "extra_fragments": ["人物更像神女主祭形象", "神性气场更集中"],
        },
        {
            "style_lead": "冰雪奇幻",
            "style_tags": ["神话感", "神性幻境", "霜辉神女"],
            "extra_fragments": ["圣洁感更强", "人物更像幻境中的神女降临"],
        },
        {
            "style_lead": "魔幻现实主义",
            "style_tags": ["神话感", "神话女主", "宿命感"],
            "extra_fragments": ["叙事感更浓", "人物更像神话故事中的引导者"],
        },
        {
            "style_lead": "暗黑奇幻",
            "style_tags": ["神话感", "暗系神女", "夜纹神女"],
            "extra_fragments": ["命运感更强", "人物更像神话分支中的暗系神女"],
        },
    ],
    ("神话感", "queen"): [
        {
            "style_lead": "神圣史诗",
            "style_tags": ["神话感", "神圣史诗", "神圣"],
            "extra_fragments": ["人物更像神权王座主角", "统御感更明确"],
        },
        {
            "style_lead": "暗黑奇幻",
            "style_tags": ["神话感", "王权暗黑", "巴洛克"],
            "extra_fragments": ["人物更像命运系王权主角", "压迫感更强"],
        },
        {
            "style_lead": "魔幻现实主义",
            "style_tags": ["神话感", "王权神话", "王朝叙事"],
            "extra_fragments": ["人物更像神话王朝叙事中心", "戏剧感更稳定"],
        },
        {
            "style_lead": "冰雪奇幻",
            "style_tags": ["神话感", "王权幻境", "冰雪"],
            "extra_fragments": ["人物更偏冷冽王权形象", "圣洁压场感更强"],
        },
    ],
    ("神话感", "witch"): [
        {
            "style_lead": "暗黑奇幻",
            "style_tags": ["神话感", "巫术暗黑", "巴洛克"],
            "extra_fragments": ["人物更像咒术叙事主角", "神秘压迫感更强"],
        },
        {
            "style_lead": "魔幻现实主义",
            "style_tags": ["神话感", "巫术叙事", "奇诡感"],
            "extra_fragments": ["人物更像异术故事中的魔女主角", "奇诡叙事感更浓"],
        },
        {
            "style_lead": "冰雪奇幻",
            "style_tags": ["神话感", "冷调幻境", "冰雪"],
            "extra_fragments": ["人物更偏冷调幻境魔女形象", "危险感更克制"],
        },
        {
            "style_lead": "神圣史诗",
            "style_tags": ["神话感", "仪式反差", "神圣"],
            "extra_fragments": ["人物更像高仪式感魔女分支主角", "反差张力更强"],
        },
    ],
    ("神话感", "priest"): [
        {
            "style_lead": "神圣史诗",
            "style_tags": ["神话感", "祭仪中心", "圣坛"],
            "extra_fragments": ["人物更像祭仪中心角色", "仪式引导感更明确"],
        },
        {
            "style_lead": "魔幻现实主义",
            "style_tags": ["神话感", "祭仪叙事", "神谕空间"],
            "extra_fragments": ["人物更像神谕叙事中的祭司主角", "叙事重量更强"],
        },
        {
            "style_lead": "冰雪奇幻",
            "style_tags": ["神话感", "祭司幻境", "霜辉祭司"],
            "extra_fragments": ["圣洁感更强", "人物更像幻境祭司形象"],
        },
        {
            "style_lead": "暗黑奇幻",
            "style_tags": ["神话感", "仪式阴影", "夜纹祭司"],
            "extra_fragments": ["宿命感更强", "人物更像仪式分支中的暗系祭司"],
        },
    ],
    ("真实感", "photographer"): [
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志编辑摄影", "纪实"],
            "extra_fragments": ["人物更像创作者主题企划主角", "观察者气质更强"],
        },
        {
            "style_lead": "黑白摄影",
            "style_tags": ["真实感", "黑白摄影", "纪实"],
            "extra_fragments": ["纪实气质更凝练", "人物更像摄影专题封面角色"],
        },
        {
            "style_lead": "胶片感",
            "style_tags": ["真实感", "胶片感", "生活电影剧照"],
            "extra_fragments": ["故事感更强", "画面更像创作者随行纪录片定格"],
        },
        {
            "style_lead": "纪实抓拍",
            "style_tags": ["真实感", "纪实抓拍", "街拍"],
            "extra_fragments": ["现场感更强", "人物更像街头拍摄中的真实瞬间"],
        },
    ],
    ("真实感", "doctor"): [
        {
            "style_lead": "纪实抓拍",
            "style_tags": ["真实感", "纪实", "纪实抓拍"],
            "extra_fragments": ["人物更像医疗现场主角", "职业可信度更强"],
        },
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志编辑摄影", "杂志感"],
            "extra_fragments": ["人物更像医疗专题封面角色", "专业表达更克制"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "电影剧照", "生活电影剧照"],
            "extra_fragments": ["人物更像医疗题材剧集定格主角", "叙事感更完整"],
        },
        {
            "style_lead": "黑白摄影",
            "style_tags": ["真实感", "黑白摄影", "纪实"],
            "extra_fragments": ["专业权威感更强", "人物更偏医疗纪实肖像"],
        },
    ],
    ("真实感", "lawyer"): [
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志编辑摄影", "杂志感"],
            "extra_fragments": ["人物更像律政专题封面主角", "理性气场更明确"],
        },
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "电影剧照", "生活电影剧照"],
            "extra_fragments": ["人物更像律政题材剧集定格主角", "叙事张力更稳定"],
        },
        {
            "style_lead": "黑白摄影",
            "style_tags": ["真实感", "黑白摄影", "高对比黑白"],
            "extra_fragments": ["秩序感更强", "人物更偏律政海报肖像"],
        },
        {
            "style_lead": "棚拍写真",
            "style_tags": ["真实感", "棚拍", "写真"],
            "extra_fragments": ["人物更偏正式人物主题企划", "轮廓表达更利落"],
        },
    ],
    ("真实感", "mechanic"): [
        {
            "style_lead": "纪实抓拍",
            "style_tags": ["真实感", "纪实抓拍", "纪实"],
            "extra_fragments": ["人物更像机修现场的真实主角", "工作状态感更强"],
        },
        {
            "style_lead": "夜间闪光摄影",
            "style_tags": ["真实感", "夜间闪光摄影", "时尚街拍"],
            "extra_fragments": ["金属反光与工具细节更突出", "人物更像工业夜班主题企划主角"],
        },
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志感", "杂志编辑摄影"],
            "extra_fragments": ["人物更偏工业人物专题封面", "职业设定展示更明确"],
        },
        {
            "style_lead": "黑白摄影",
            "style_tags": ["真实感", "黑白摄影", "高对比黑白"],
            "extra_fragments": ["结构感更强", "人物更偏工业纪实肖像"],
        },
    ],
    ("真实感", "agent"): [
        {
            "style_lead": "生活电影剧照",
            "style_tags": ["真实感", "电影剧照", "生活电影剧照"],
            "extra_fragments": ["人物更像特工题材影片定格主角", "任务叙事感更强"],
        },
        {
            "style_lead": "夜间闪光摄影",
            "style_tags": ["真实感", "夜间闪光摄影", "时尚街拍"],
            "extra_fragments": ["行动现场感更强", "人物更像夜间任务中的主角"],
        },
        {
            "style_lead": "纪实抓拍",
            "style_tags": ["真实感", "纪实抓拍", "街拍"],
            "extra_fragments": ["隐蔽行动感更强", "人物更像任务间隙的真实瞬间"],
        },
        {
            "style_lead": "杂志编辑摄影",
            "style_tags": ["真实感", "杂志编辑摄影", "高智感"],
            "extra_fragments": ["冷静控制感更强", "人物更偏角色企划封面"],
        },
    ],
}
_RUNTIME_IDENTITY_GROUPS: dict[str, set[str]] = {
    "lead_singer": {"乐队主唱"},
    "idol": {"偶像", "潮女模特", "国潮模特", "公主"},
    "student": {"学生"},
    "office_lady": {"OL"},
    "bartender": {"调酒师"},
    "researcher": {"研究员"},
    "female_warrior": {"女武士"},
    "goddess": {"神女"},
    "queen": {"女王"},
    "witch": {"魔女"},
    "photographer": {"摄影师"},
    "mechanic": {"机械师", "机修师"},
    "doctor": {"医生"},
    "lawyer": {"律师"},
    "priest": {"祭司"},
    "agent": {"特工"},
    "youth": set(),
    "warrior": {"战士", "骑士", "神圣骑士", "冰霜骑士", "剑客", "忍者", "近战法师"},
    "sacred": {"战斗修女", "仙子"},
    "professional": set(),
}
_RUNTIME_IDENTITY_CUES: dict[str, list[str]] = {
    "lead_singer": ["舞台感染力更强", "人物更像演出主视觉主角"],
    "idol": ["镜头表现欲更强", "人物更像企划封面主角"],
    "student": ["青春感更自然", "表情与姿态更轻盈"],
    "office_lady": ["职业干练感更明确", "人物更像都市职场主角"],
    "bartender": ["场域掌控感更强", "人物更像夜场叙事主角"],
    "researcher": ["理性探索感更明确", "人物更像实验专题主角"],
    "female_warrior": ["英气更明确", "人物姿态更偏战斗出场镜头"],
    "goddess": ["神性表达更明确", "人物气场更稳定"],
    "queen": ["统御感更明确", "人物更像王权叙事中心"],
    "witch": ["神秘压迫感更强", "人物更像异术叙事主角"],
    "photographer": ["观察者气质更强", "画面更像创作者人物专题"],
    "mechanic": ["技术职业感更明确", "人物更像工业角色主角"],
    "doctor": ["专业可信度更强", "人物更像医疗人物专题主角"],
    "lawyer": ["理性气场更明确", "人物更像律政主题主角"],
    "priest": ["仪式指向更清晰", "人物更像祭典叙事中心"],
    "agent": ["任务紧张感更强", "人物更像行动中的主角"],
    "youth": ["青春感更自然", "表情与姿态更轻盈"],
    "warrior": ["角色张力更强", "姿态更偏出场镜头"],
    "sacred": ["人物气场更稳定", "仪式感表达更明确"],
    "professional": ["职业设定更清晰", "画面更像人物主题企划"],
}


def format_grouped_summary(selected: OrderedDict[str, list[str]], custom_tags: list[str]) -> str:
    lines = []
    for name, tags in selected.items():
        if tags:
            lines.append(f"{name}：{'、'.join(tags)}")
    if custom_tags:
        lines.append(f"自定义补充：{'、'.join(custom_tags)}")
    return "\n".join(lines)


def _clean_fragment(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip("，,;； ")
    if not text or text == "无":
        return ""
    compact = "".join(text.split())
    if compact.casefold() in {"[]", "{}", "()", "（）", "【】", "null", "none", "undefined"}:
        return ""
    if compact and not compact.strip("[]{}()（）【】"):
        return ""
    return text.replace("brief", "").replace("Brief", "").strip("，,;； ")


def _prompt_language_mode(settings: dict[str, Any]) -> str:
    return str(settings.get("提示词语言", "纯中文") or "纯中文").strip()


def _use_english_prompt(settings: dict[str, Any]) -> bool:
    return _prompt_language_mode(settings) in _PROMPT_LANGUAGE_ENGLISH_MODES


def _has_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in str(text or ""))


def _translate_prompt_fragment(fragment: Any) -> str:
    text = _clean_fragment(fragment)
    if not text:
        return ""
    if text in _PROMPT_FRAGMENT_TRANSLATION_MAP:
        return _PROMPT_FRAGMENT_TRANSLATION_MAP[text]
    if not _has_cjk(text):
        return text

    translated = text
    for source in sorted(_PROMPT_FRAGMENT_TRANSLATION_MAP, key=len, reverse=True):
        target = _PROMPT_FRAGMENT_TRANSLATION_MAP[source]
        if source in translated:
            translated = translated.replace(source, target)
    return "" if _has_cjk(translated) else translated


def _localize_prompt_fragments(fragments: list[str], settings: dict[str, Any]) -> list[str]:
    if not _use_english_prompt(settings):
        return list(fragments)

    localized: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        translated = _translate_prompt_fragment(fragment)
        key = _fragment_key(translated)
        if not translated or key in seen:
            continue
        localized.append(translated)
        seen.add(key)

    for tail in ("masterpiece", "best quality", "high detail", "sharp focus"):
        key = _fragment_key(tail)
        if key not in seen:
            localized.append(tail)
            seen.add(key)
    return localized


def _nonempty_group_values(selected: OrderedDict[str, list[str]], group_name: str) -> list[str]:
    return [_clean_fragment(tag) for tag in selected.get(group_name, []) if _clean_fragment(tag)]


def _nonempty_group_values_from_fragments(
    selected: OrderedDict[str, list[str]],
    group_name: str,
    fragments: list[str],
    *,
    english: bool = False,
) -> list[str]:
    fragment_keys = {_fragment_key(fragment) for fragment in fragments if _clean_fragment(fragment)}
    values: list[str] = []
    for value in _nonempty_group_values(selected, group_name):
        output = _translate_prompt_fragment(value) if english else value
        key = _fragment_key(output)
        if key and key in fragment_keys:
            values.append(output)
    return values


def _join_limited(values: list[str], *, limit: int = 5, english: bool = False) -> str:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_fragment(value)
        key = _fragment_key(text)
        if not text or key in seen:
            continue
        cleaned.append(text)
        seen.add(key)
        if len(cleaned) >= limit:
            break
    if not cleaned:
        return ""
    separator = ", " if english else "、"
    return separator.join(cleaned)


_STYLE_CLUSTER_PRIORITY_ZH: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("古风", ("古风", "古风电影剧照", "宋韵美学", "国风美学", "玄幻古风")),
    ("真实感", ("真实感", "照片级", "写实摄影", "自然写实图像", "欧美风", "港风")),
    ("CG感", ("CG感", "电影级CG", "赛博朋克", "复古未来主义", "手办风")),
    ("插画感", ("插画感", "动漫", "水彩线稿", "后印象派", "洛可可")),
)
_STYLE_CLUSTER_PRIORITY_EN: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("oriental historical style", ("oriental historical", "ancient", "hanfu", "song dynasty")),
    ("realistic photography", ("realistic", "photography", "photorealistic", "western editorial")),
    ("cinematic CG", ("CG", "render", "cyberpunk", "futuristic")),
    ("illustration", ("illustration", "anime", "watercolor", "line art")),
)
_STYLE_BRIDGE_HINTS_ZH = {"照片级", "真实感", "写实摄影", "港风", "胶片感", "杂志感"}
_STYLE_BRIDGE_HINTS_EN = {"photorealistic", "realistic photography", "film look", "hong kong cinema look", "editorial magazine look"}
_SCENE_CLUSTER_PRIORITY_ZH: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("古风空间", ("宫殿", "回廊", "古风建筑", "月洞门", "水榭", "庭院")),
    ("私密室内", ("化妆台", "卧室", "浴室", "酒店套房", "落地窗夜景")),
    ("赛博都市", ("赛博街区", "未来都市", "霓虹都市", "机库", "广告屏街谷")),
    ("自然户外", ("雪地", "湖畔", "海边", "森林", "花海")),
)
_SCENE_CLUSTER_PRIORITY_EN: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("oriental palace setting", ("palace", "corridor", "garden", "courtyard")),
    ("private interior", ("vanity", "bedroom", "bathroom", "hotel suite")),
    ("cyber city", ("cyber", "futuristic city", "neon", "hangar")),
    ("natural exterior", ("snow", "lakeside", "seaside", "forest")),
)


def _cluster_key_for_value(value: str, clusters: tuple[tuple[str, tuple[str, ...]], ...]) -> str:
    text = str(value or "").casefold()
    for name, terms in clusters:
        if any(str(term).casefold() in text for term in terms):
            return name
    return ""


def _join_coherent_values(
    values: list[str],
    *,
    limit: int,
    english: bool = False,
    clusters: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> str:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_fragment(value)
        key = _fragment_key(text)
        if not text or key in seen:
            continue
        cleaned.append(text)
        seen.add(key)
    if clusters and cleaned:
        cluster_order = [_cluster_key_for_value(value, clusters) for value in cleaned]
        present_clusters = {cluster for cluster in cluster_order if cluster}
        chosen_cluster = next((cluster_name for cluster_name, _terms in clusters if cluster_name in present_clusters), "")
        if chosen_cluster:
            primary = [value for value in cleaned if _cluster_key_for_value(value, clusters) == chosen_cluster]
            secondary = [value for value in cleaned if not _cluster_key_for_value(value, clusters)]
            cleaned = primary + secondary
    return _join_limited(cleaned, limit=limit, english=english)


def _build_style_bridge_hint(
    values: list[str],
    *,
    english: bool = False,
    style_isolation_mode: str = "平衡收敛",
) -> str:
    if style_isolation_mode == "严格风格隔离":
        return ""
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean_fragment(value)
        key = _fragment_key(text)
        if not text or key in seen:
            continue
        cleaned.append(text)
        seen.add(key)
    if not cleaned:
        return ""
    clusters = _STYLE_CLUSTER_PRIORITY_EN if english else _STYLE_CLUSTER_PRIORITY_ZH
    present_clusters = [_cluster_key_for_value(value, clusters) for value in cleaned]
    present_cluster_names = {cluster for cluster in present_clusters if cluster}
    if len(present_cluster_names) <= 1:
        return ""
    chosen_cluster = next((cluster_name for cluster_name, _terms in clusters if cluster_name in present_cluster_names), "")
    bridge_hints = _STYLE_BRIDGE_HINTS_EN if english else _STYLE_BRIDGE_HINTS_ZH
    secondary_values = [
        value
        for value in cleaned
        if _cluster_key_for_value(value, clusters) != chosen_cluster and value in bridge_hints
    ]
    return _join_limited(secondary_values, limit=2, english=english)


def _has_dense_conflicting_tracks(
    selected: OrderedDict[str, list[str]],
    fragments: list[str],
    *,
    english: bool = False,
    style_isolation_mode: str = "平衡收敛",
) -> bool:
    style_values = _nonempty_group_values_from_fragments(selected, "画面风格", fragments, english=english)
    scene_values = _nonempty_group_values_from_fragments(selected, "场景背景", fragments, english=english)
    action_values = _nonempty_group_values_from_fragments(selected, "动作姿态", fragments, english=english)
    adult_values = _nonempty_group_values_from_fragments(selected, "成人向表达", fragments, english=english)
    outfit_values = _nonempty_group_values_from_fragments(selected, "服装造型", fragments, english=english)
    style_clusters = {
        _cluster_key_for_value(value, _STYLE_CLUSTER_PRIORITY_EN if english else _STYLE_CLUSTER_PRIORITY_ZH)
        for value in style_values
    }
    scene_clusters = {
        _cluster_key_for_value(value, _SCENE_CLUSTER_PRIORITY_EN if english else _SCENE_CLUSTER_PRIORITY_ZH)
        for value in scene_values
    }
    style_clusters.discard("")
    scene_clusters.discard("")
    return (
        (style_isolation_mode != "允许风格漂移" and len(style_clusters) > 1)
        or len(scene_clusters) > 1
        or len(scene_values) > 3
        or ((len(style_clusters) > 0 or len(scene_clusters) > 0) and len(action_values) > 2 and len(adult_values) > 2 and len(outfit_values) > 1)
    )


def _detail_level_wants_expanded_prompt(settings: dict[str, Any]) -> bool:
    detail = str(settings.get("详细度", "标准") or "标准").strip()
    output_mode = str(settings.get("输出模式", "") or "").strip()
    if output_mode in {"标签", "JSON"}:
        return False
    return detail not in {"简洁", "短"}


def _style_isolation_mode(settings: dict[str, Any]) -> str:
    mode = str(settings.get("风格隔离策略", "平衡收敛") or "平衡收敛").strip()
    return mode if mode in {"平衡收敛", "严格风格隔离", "允许风格漂移"} else "平衡收敛"


def _english_subject_phrase(subject: str) -> str:
    text = _clean_fragment(subject)
    if not text:
        return "the selected subject"
    lowered = text.casefold()
    if lowered.startswith(("a ", "an ", "the ", "one ")):
        return text
    if lowered in {"adult woman", "woman", "female subject"}:
        return f"an {text}"
    if lowered in {"adult man", "man", "male subject"}:
        return f"an {text}" if lowered.startswith("adult ") else f"a {text}"
    if lowered.startswith(("adult ", "elderly ", "elegant ", "young adult ")):
        return f"an {text}" if text[0].lower() in "aeiou" else f"a {text}"
    return text


def _prompt_tags_look_adult(*tag_groups: list[str] | tuple[str, ...]) -> bool:
    adult_markers = (
        "成年",
        "adult",
        "mature",
        "nsfw",
        "私房",
        "内衣",
        "睡袍",
        "性感",
        "成人",
    )
    source = " ".join(str(tag) for group in tag_groups for tag in group)
    lowered = source.casefold()
    return any(str(marker).casefold() in lowered for marker in adult_markers)


def _is_non_person_subject(settings: dict[str, Any]) -> bool:
    resolved = str(settings.get("主体类型解析结果", "") or "").strip()
    explicit = str(settings.get("主体类型", "自动") or "自动").strip()
    return resolved == "非人物主体" or explicit == "非人物主体"


def _expand_english_prompt_locally(
    fragments: list[str],
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    scene_group: str,
    identity: str,
    style_track: str,
) -> str:
    lead = _clean_fragment(fragments[0] if fragments else "highly finished image")
    style_mode = _style_isolation_mode(settings)
    non_person = _is_non_person_subject(settings)
    subject_values = _nonempty_group_values_from_fragments(selected, "主体", fragments, english=True)
    adult_prompt = _prompt_tags_look_adult(fragments, custom_tags, subject_values)
    translated_identity = _translate_prompt_fragment(identity)
    translated_scene_group = _translate_prompt_fragment(scene_group)
    subject = _join_limited(subject_values, limit=5, english=True) or translated_identity or ("selected non-human subject" if non_person else ("adult woman" if adult_prompt else "selected subject"))
    style_values = _nonempty_group_values_from_fragments(selected, "画面风格", fragments, english=True)
    style = _join_coherent_values(style_values, limit=3, english=True, clusters=_STYLE_CLUSTER_PRIORITY_EN)
    style_bridge_hint = _build_style_bridge_hint(style_values, english=True, style_isolation_mode=style_mode)
    adult = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "成人向表达", fragments, english=True), limit=2, english=True)
    outfit = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "服装造型", fragments, english=True), limit=3, english=True)
    scene = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "场景背景", fragments, english=True), limit=2, english=True, clusters=_SCENE_CLUSTER_PRIORITY_EN) or translated_scene_group
    composition = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "构图视角", fragments, english=True), limit=3, english=True)
    action = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "动作姿态", fragments, english=True), limit=2, english=True)
    lighting = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "光影氛围", fragments, english=True), limit=3, english=True)
    props = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "道具世界观", fragments, english=True), limit=2, english=True)
    quality = _join_limited(_nonempty_group_values_from_fragments(selected, "技术画质", fragments, english=True), limit=6, english=True)
    custom = _join_limited([_translate_prompt_fragment(tag) for tag in custom_tags], limit=8, english=True)
    has_dense_conflict = _has_dense_conflicting_tracks(selected, fragments, english=True, style_isolation_mode=style_mode)
    if has_dense_conflict:
        anchors = _join_coherent_values(
            [subject, style, adult, outfit, scene, composition, action, lighting, props, quality],
            limit=14,
            english=True,
        )
    else:
        anchors = _join_limited(fragments[1:], limit=18, english=True)
    generic_subject = _fragment_key(subject) in {"selectedsubject", "theselectedsubject"}
    if not has_dense_conflict and subject and not generic_subject and _fragment_key(subject) not in {_fragment_key(fragment) for fragment in fragments}:
        anchors = _join_limited([subject, *fragments[1:]], limit=18, english=True)
    if generic_subject and anchors:
        lead_line = f"{lead} focused on the selected subject, {anchors}"
    else:
        lead_line = f"{lead}, {anchors}" if anchors else lead
    if lead_line and lead_line[-1] not in ".!?":
        lead_line = f"{lead_line}."
    subject_phrase = _english_subject_phrase(subject)

    if non_person:
        sections = [
            lead_line,
            f"The image reads as one coherent positive scene description, with {subject_phrase} keeping a stable silhouette, clear functional structure, believable scale, and a consistent relationship with the surrounding frame.",
            "The main volume, surface panels, joints, edges, materials, openings, attachments, and visible functional details share one believable camera perspective, giving the picture the feeling of a finished object, vehicle, creature, architecture, or environment concept frame.",
            "Subtle physical detail appears through surface wear, layered material transitions, edge highlights, seams, panel gaps, dust, moisture, reflections, and small asymmetries that make the subject feel present without turning it into a human portrait.",
            "The frame has a clean visual hierarchy: the non-human subject is the first read, secondary shapes guide the eye, and the background contrast stays controlled so the composition remains calm, legible, and image-like.",
        ]
    else:
        sections = [
            lead_line,
            f"The image reads as one coherent positive scene description, with {subject_phrase} keeping a stable body scale, readable facial structure, clear posture, and a consistent relationship with the surrounding frame.",
            "The face, torso, limbs, clothing silhouette, and visible gestures share one believable camera perspective, giving the picture the feeling of a finished photograph or polished concept frame with unified visual intent.",
            "Subtle human-scale detail appears in the facial planes, skin texture, hair edges, posture tension, fabric contact points, and small natural asymmetries, making the figure feel physically present without changing the selected concept.",
            "The frame has a clean visual hierarchy: the subject is the first read, secondary shapes guide the eye, and the background contrast stays controlled so the composition remains calm, legible, and image-like.",
        ]
    if style:
        sections.append(f"The visual direction follows {style}, with a stable mood, coherent medium language, and no sudden shift into an unrelated genre.")
    if style_bridge_hint:
        sections.append(f"At the same time, preserve the selected {style_bridge_hint} media texture and finish level without changing the main worldbuilding direction.")
    if adult and not non_person:
        sections.append(f"The mature styling appears through controlled atmosphere and visual cues such as {adult}, while the image remains composed, intentional, and centered on the full visual scene.")
    if outfit:
        if non_person:
            sections.append(f"The exterior design uses {outfit} as surface or material language, with visible weight, seams, panel layering, edge highlights, and believable contact between parts.")
        else:
            sections.append(f"The outfit and styling show {outfit}, with visible fabric weight, seams, silhouette, edge highlights, and believable contact between clothing and body.")
    if scene:
        sections.append(f"The setting is {scene}, built with foreground, middle-ground, and background depth so the environment supports the character and feels spatially grounded.")
    else:
        sections.append("The background stays controlled and readable, with enough spatial depth to separate the subject from the environment without adding an unrelated location.")
    if composition:
        if non_person:
            sections.append(f"The camera plan is {composition}, keeping the whole intended form readable, the scale relationship natural, and the key edges, openings, supports, or functional parts logically visible.")
        else:
            sections.append(f"The camera plan is {composition}, keeping the intended body area readable, the head-to-body relationship natural, and the hands and feet logically placed when visible.")
    if action:
        if non_person:
            sections.append(f"The motion or state expresses {action}, with believable weight, stable contact points, clear direction of force, and no random decorative clutter.")
        else:
            sections.append(f"The pose expresses {action}, with relaxed shoulders, believable weight balance, clear gesture direction, and no stiff mannequin feeling.")
    if lighting:
        sections.append(f"The lighting is shaped by {lighting}, balancing key light, fill light, rim light, shadow softness, reflections, and color temperature for a finished cinematic or editorial look.")
    else:
        sections.append("The lighting remains balanced, with readable key light, soft fill, gentle edge separation, controlled highlights, and shadows that reveal form without flattening the subject.")
    if props:
        sections.append(f"{props} appear as supporting story elements, scaled naturally and placed where they reinforce the scene rather than stealing focus.")
    if custom:
        sections.append(f"Additional user details are woven into the same scene: {custom}, keeping them subordinate to one clear visual direction.")
    sections.append("The overall creative direction stays cohesive, with every visual element connected through one consistent camera distance, color palette, material language, and narrative atmosphere.")
    if quality:
        if non_person:
            sections.append("The final image has clean focus hierarchy, stable geometry, coherent material layering, consistent perspective, controlled background detail, no unwanted text, no watermark, and no low-resolution artifacts.")
        else:
            sections.append("The final image has clean focus hierarchy, natural anatomy, stable hands, coherent fabric folds, controlled background detail, no unwanted text, no watermark, and no low-resolution artifacts.")
    else:
        if non_person:
            sections.append("The final image has clean focus hierarchy, stable geometry, coherent material layering, consistent perspective, controlled background detail, no unwanted text, no watermark, and no low-resolution artifacts.")
        else:
            sections.append("The final image has clean focus hierarchy, natural anatomy, stable hands, coherent fabric folds, controlled background detail, no extra fingers, no unwanted text, no watermark, and no low-resolution artifacts.")
    return " ".join(section.strip() for section in sections if section.strip())


def _expand_chinese_prompt_locally(
    fragments: list[str],
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    scene_group: str,
    identity: str,
    style_track: str,
) -> str:
    lead = _clean_fragment(fragments[0] if fragments else "高完成度图像")
    style_mode = _style_isolation_mode(settings)
    non_person = _is_non_person_subject(settings)
    subject_values = _nonempty_group_values_from_fragments(selected, "主体", fragments)
    subject = _join_limited(subject_values, limit=6) or _clean_fragment(identity) or ("非人物主体" if non_person else "当前主体")
    style_values = _nonempty_group_values_from_fragments(selected, "画面风格", fragments)
    style = _join_coherent_values(style_values, limit=3, clusters=_STYLE_CLUSTER_PRIORITY_ZH)
    style_bridge_hint = _build_style_bridge_hint(style_values, style_isolation_mode=style_mode)
    adult = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "成人向表达", fragments), limit=2)
    outfit = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "服装造型", fragments), limit=3)
    scene = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "场景背景", fragments), limit=2, clusters=_SCENE_CLUSTER_PRIORITY_ZH) or _clean_fragment(scene_group)
    composition = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "构图视角", fragments), limit=3)
    action = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "动作姿态", fragments), limit=2)
    lighting = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "光影氛围", fragments), limit=3)
    props = _join_coherent_values(_nonempty_group_values_from_fragments(selected, "道具世界观", fragments), limit=2)
    quality = _join_limited(_nonempty_group_values_from_fragments(selected, "技术画质", fragments), limit=7)
    custom = _join_limited(custom_tags, limit=10)

    if _has_dense_conflicting_tracks(selected, fragments, style_isolation_mode=style_mode):
        anchor_text = _join_coherent_values(
            [lead, subject, style, adult, outfit, scene, composition, action, lighting, props, quality],
            limit=18,
        )
    else:
        anchor_text = "，".join(fragments)
    if non_person:
        clauses = [
            "画面呈现为自然连贯的非人物主题正向画面说明，主体结构、功能轮廓、功能部件、比例尺度、材质层级和环境关系保持稳定",
        ]
    else:
        clauses = [
            "画面呈现为自然连贯的正向画面说明，主体身份、年龄气质、身体比例、脸部可读性和姿态关系保持稳定",
        ]
    if style:
        clauses.append(f"整体风格遵循{style}并让媒介感、色彩层次和完成度保持统一，不要突然偏向未选择的画风")
    if style_bridge_hint:
        clauses.append(f"同时保留{style_bridge_hint}的媒介质感与成片完成度，但不改变当前主体世界观主线")
    if adult and not non_person:
        clauses.append(f"成人向表达作为氛围与造型方向融入画面，保留{adult}的成熟感，同时让构图以完整、稳定、可出图为优先")
    if outfit:
        if non_person:
            clauses.append(f"外观结构与表面材质围绕{outfit}展开，强调体块转折、接缝、边缘高光、材质厚薄、结构层级和功能部件之间的自然关系")
        else:
            clauses.append(f"服装造型围绕{outfit}展开，强调面料厚薄、垂坠、褶皱、边缘高光、穿搭结构与身体轮廓之间的自然关系")
    if scene:
        clauses.append(f"场景设定为{scene}，需要有前景中景和背景层次，空间透视清楚，环境细节服务主体而不是遮挡主体")
    if composition:
        if non_person:
            clauses.append(f"镜头构图采用{composition}，主体在画面中占比清晰，整体轮廓、关键边缘、支撑点、开口、连接件和主要功能结构完整可读")
        else:
            clauses.append(f"镜头构图采用{composition}，主体在画面中占比清晰，头身关系自然，必要时保证全身、手部、脚部和服装轮廓完整入镜")
    if action:
        if non_person:
            clauses.append(f"运动状态或画面趋势表现为{action}，受力方向、接触点、悬浮关系、运动轨迹和结构朝向要互相协调，看起来像可信的产品展示、场景设定或概念设计瞬间")
        else:
            clauses.append(f"动作姿态表现为{action}，重心、肩颈、手臂、腰胯和视线方向要互相协调，看起来像真实摄影或成熟成片中的自然瞬间")
    if lighting:
        if non_person:
            clauses.append(f"光影氛围使用{lighting}，明确主光、辅光、轮廓光、阴影软硬、反射与色温，让主体表面、材质纹理、结构边缘和场景空间都有层次")
        else:
            clauses.append(f"光影氛围使用{lighting}，明确主光、辅光、轮廓光、阴影软硬、反射与色温，让肤色、服装材质和场景边缘都有层次")
    if props:
        if non_person:
            clauses.append(f"道具与世界观元素包含{props}，只作为功能说明、尺度参照或视觉锚点出现，不抢走非人物主体焦点")
        else:
            clauses.append(f"道具与世界观元素包含{props}，只作为叙事补充和视觉锚点出现，不抢走人物主体焦点")
    if custom:
        clauses.append(f"自定义补充自然融入同一个场景：{custom}，并服务同一条视觉主线")
    if quality:
        if non_person:
            clauses.append(f"最终画质强调{quality}，焦点层级清晰，几何结构稳定，透视一致，材质纹理真实，边缘干净，背景克制，无文字、水印、logo、低清伪影、随机人像或无关肢体")
        else:
            clauses.append(f"最终画质强调{quality}，焦点层级清晰，解剖结构自然，手指数量稳定，皮肤与材质纹理真实，背景干净，无文字、水印、logo、低清伪影和多余肢体")
    else:
        if non_person:
            clauses.append("最终画质强调焦点层级清晰、几何结构稳定、透视一致、材质纹理真实、边缘干净、背景克制，无文字、水印、logo、低清伪影、随机人像或无关肢体")
        else:
            clauses.append("最终画质强调焦点层级清晰、解剖结构自然、手指数量稳定、皮肤与材质纹理真实、背景干净，无文字、水印、logo、低清伪影和多余肢体")
    detail_text = "；".join(clause.strip("，,;； ") for clause in clauses if clause.strip())
    detail_text = detail_text.replace("，", "、").replace(",", "、")
    return f"{anchor_text}；{detail_text}" if detail_text else anchor_text


def _expand_prompt_fragments_locally(
    fragments: list[str],
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    context: _PromptBuildContext,
) -> str:
    clean_fragments = [_clean_fragment(fragment) for fragment in fragments if _clean_fragment(fragment)]
    if not clean_fragments:
        return ""
    if not _detail_level_wants_expanded_prompt(settings):
        return (", " if _use_english_prompt(settings) else "，").join(clean_fragments)
    if _use_english_prompt(settings):
        return _expand_english_prompt_locally(
            clean_fragments,
            selected,
            custom_tags,
            settings,
            scene_group=str(context.get("scene_group", "")),
            identity=str(context.get("identity", "")),
            style_track=str(context.get("style_track", "")),
        )
    return _expand_chinese_prompt_locally(
        clean_fragments,
        selected,
        custom_tags,
        settings,
        scene_group=str(context.get("scene_group", "")),
        identity=str(context.get("identity", "")),
        style_track=str(context.get("style_track", "")),
    )


def _contains_any_term(fragment: str, terms: tuple[str, ...]) -> bool:
    text = str(fragment).casefold()
    return any(str(term).casefold() in text for term in terms if str(term).strip())


def _is_negative_constraint_fragment(fragment: str) -> bool:
    text = str(fragment).strip()
    return any(marker in text for marker in ("不要", "避免", "禁止", "不得", "无文字", "无文本"))


def _filter_style_positive_fragments(fragments: list[str], style: str) -> list[str]:
    policy_style = resolve_base_template_style(style)
    blocked_terms = _STYLE_POSITIVE_EXCLUSION_TERMS.get(policy_style, ())
    if not blocked_terms:
        return list(fragments)
    return [
        fragment
        for fragment in fragments
        if fragment and (_is_negative_constraint_fragment(fragment) or not _contains_any_term(fragment, blocked_terms))
    ]


def _fragment_key(fragment: str) -> str:
    text = str(fragment or "").strip().casefold()
    return "".join(ch for ch in text if not ch.isspace() and ch not in "，,;；、。:：")


def _append_prompt_fragment(
    items: list[_PromptFragmentItem],
    value: Any,
    *,
    priority: int,
    order_index: int,
) -> int:
    text = _clean_fragment(value)
    if not text:
        return order_index
    items.append({"text": text, "priority": int(priority), "order": order_index})
    return order_index + 1


def _append_prompt_fragments(
    items: list[_PromptFragmentItem],
    values: list[Any],
    *,
    priority: int,
    order_index: int,
) -> int:
    for value in values:
        order_index = _append_prompt_fragment(
            items,
            value,
            priority=priority,
            order_index=order_index,
        )
    return order_index


def _finalize_prompt_fragments(
    items: list[_PromptFragmentItem],
    style: str,
    *,
    limit: int = _PROMPT_FRAGMENT_LIMIT,
) -> list[str]:
    filtered_texts = _filter_style_positive_fragments(
        [str(item["text"]).strip() for item in items if str(item.get("text", "")).strip()],
        style,
    )
    allowed_texts = set(filtered_texts)
    deduped: list[_PromptFragmentItem] = []
    seen: set[str] = set()
    for item in items:
        text = str(item.get("text", "")).strip()
        if not text or text not in allowed_texts:
            continue
        key = _fragment_key(text)
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        deduped.append(item)
    if len(deduped) <= limit:
        return [item["text"] for item in sorted(deduped, key=lambda item: item["order"])]

    required = [item for item in deduped if int(item["priority"]) >= _PROMPT_REQUIRED_PRIORITY]
    optional = [item for item in deduped if int(item["priority"]) < _PROMPT_REQUIRED_PRIORITY]
    kept: list[_PromptFragmentItem] = []
    kept_keys: set[str] = set()

    for item in sorted(required, key=lambda item: item["order"]):
        key = _fragment_key(item["text"])
        if key in kept_keys:
            continue
        kept.append(item)
        kept_keys.add(key)

    remaining = max(0, limit - len(kept))
    optional_ranked = sorted(optional, key=lambda item: (-int(item["priority"]), int(item["order"])))
    for item in optional_ranked:
        if remaining <= 0:
            break
        key = _fragment_key(item["text"])
        if key in kept_keys:
            continue
        kept.append(item)
        kept_keys.add(key)
        remaining -= 1

    if len(kept) > limit:
        kept = sorted(kept, key=lambda item: (-int(item["priority"]), int(item["order"])))[:limit]
    return [item["text"] for item in sorted(kept, key=lambda item: item["order"])]


def _should_preserve_auto_theme_bone(
    selected: OrderedDict[str, list[str]],
    settings: dict[str, Any],
    runtime_random_mode: str,
    runtime_random_intensity: str,
) -> bool:
    if str(settings.get("随机主题池", "") or "").strip() != "自动":
        return False
    if runtime_random_mode != "全随机":
        return False
    if _is_strong_baseline_intensity(runtime_random_intensity) or _is_strong_extreme_intensity(runtime_random_intensity):
        return False
    return bool(selected.get("主体") or selected.get("场景背景") or selected.get("构图视角"))


def _variant_focus_fragment(subject: str, index: int, generation_count: int) -> str:
    if generation_count <= 1:
        return ""
    cues = _MULTI_PROMPT_FOCUS_CUES.get(subject) or _MULTI_PROMPT_FOCUS_CUES["人物角色"]
    return str(cues[index % len(cues)]).strip()


def _build_person_variant_profile(
    subject: str,
    index: int,
    generation_count: int,
) -> _PersonPromptVariantProfile | None:
    if generation_count <= 1 or subject != "人物角色":
        return None
    profile = _PERSON_VARIANT_PROFILES[index % len(_PERSON_VARIANT_PROFILES)]
    return {
        "label": str(profile["label"]).strip(),
        "replace_shot_tags": list(profile["replace_shot_tags"]),
        "extra_fragments": list(profile["extra_fragments"]),
    }


def _build_runtime_diversity_variant_profile(
    subject: str,
    style: str,
    runtime_random_enabled: bool,
    runtime_random_mode: str,
    runtime_random_intensity: str,
    style_track: str,
    recent_tracks: list[str],
    index: int,
    generation_count: int,
) -> _RuntimeDiversityVariantProfile | None:
    diversity_modes = {"全随机", "重写主体与场景", "重写主线"}
    if not runtime_random_enabled or runtime_random_mode not in diversity_modes:
        return None
    track_profiles = _RUNTIME_DIVERSITY_TRACK_OVERRIDES.get((style, style_track), [])
    if subject != "人物角色" and not track_profiles:
        return None
    profiles = _resolve_runtime_diversity_profiles(style, style_track)
    if not profiles:
        return None
    ordered_profiles = _order_runtime_diversity_profiles(
        profiles,
        style=style,
        style_track=style_track,
        recent_tracks=recent_tracks,
        runtime_random_intensity=runtime_random_intensity,
    )
    profile = ordered_profiles[index % len(ordered_profiles)]
    next_profile: _RuntimeDiversityVariantProfile = {
        "replace_subject_tags": list(profile["replace_subject_tags"]),
        "replace_scene_tags": list(profile["replace_scene_tags"]),
        "subject_identity": str(profile["subject_identity"]).strip(),
        "scene_group": str(profile["scene_group"]).strip(),
        "scene_bucket": str(profile["scene_bucket"]).strip(),
        "macro_direction": str(profile.get("macro_direction", "")).strip(),
        "diversity_signature": _diversity_signature_for_profile(profile),
    }
    if runtime_random_mode in {"重写主体与场景", "重写主线"}:
        next_profile["preserve_selected_subject"] = True
    for key in ("replace_outfit_tags", "replace_light_tags", "replace_action_tags", "replace_prop_tags", "replace_composition_tags"):
        values = profile.get(key, [])
        if values:
            next_profile[key] = list(values)
    return next_profile


def _resolve_runtime_diversity_profiles(
    style: str,
    style_track: str,
) -> list[_RuntimeDiversityVariantProfile]:
    track_profiles = _RUNTIME_DIVERSITY_TRACK_OVERRIDES.get((style, style_track), [])
    if track_profiles:
        return list(track_profiles)
    return list(_RUNTIME_DIVERSITY_VARIANT_PROFILES.get(style, []))


def _identity_variant_group(identity: str) -> str:
    normalized_identity = str(identity).strip()
    if not normalized_identity:
        return ""
    for group_name, identities in _RUNTIME_IDENTITY_GROUPS.items():
        if normalized_identity in identities:
            return group_name
    return ""


def _diversity_signature_for_profile(profile: _RuntimeDiversityVariantProfile) -> str:
    scene_bucket = str(profile.get("scene_bucket", "")).strip()
    scene_group = str(profile.get("scene_group", "")).strip()
    identity = str(profile.get("subject_identity", "")).strip()
    macro_direction = str(profile.get("macro_direction", "")).strip()
    scene_tags = "|".join(
        _clean_fragment(tag)
        for tag in list(profile.get("replace_scene_tags", []))
        if _clean_fragment(tag)
    )
    return "::".join([scene_bucket, scene_group, identity, macro_direction, scene_tags])


def _recent_diversity_signatures(recent_tracks: list[str]) -> set[str]:
    signatures: set[str] = set()
    for item in recent_tracks:
        text = str(item).strip()
        if text.startswith("diversity:"):
            signatures.add(text.removeprefix("diversity:").strip())
    return signatures


def _recent_marker_values(recent_tracks: list[str], prefix: str) -> set[str]:
    marker = f"{prefix}:"
    values: set[str] = set()
    for item in recent_tracks:
        text = str(item).strip()
        if text.startswith(marker):
            value = text.removeprefix(marker).strip()
            if value:
                values.add(value)
    return values


def _recent_profile_identities(recent_tracks: list[str]) -> set[str]:
    identities = _recent_marker_values(recent_tracks, "identity")
    for signature in _recent_diversity_signatures(recent_tracks):
        parts = [part.strip() for part in signature.split("::")]
        if len(parts) >= 3 and parts[2]:
            identities.add(parts[2])
    return identities


def _recent_profile_identity_groups(recent_tracks: list[str]) -> set[str]:
    groups = _recent_marker_values(recent_tracks, "identity_group")
    for identity in _recent_profile_identities(recent_tracks):
        group = _identity_variant_group(identity)
        if group:
            groups.add(group)
    return groups


def _recent_scene_buckets(recent_tracks: list[str]) -> set[str]:
    buckets = _recent_marker_values(recent_tracks, "scene_bucket")
    for signature in _recent_diversity_signatures(recent_tracks):
        parts = [part.strip() for part in signature.split("::")]
        if parts and parts[0]:
            buckets.add(parts[0])
    return buckets


def _diversity_history_markers_for_profile(profile: _RuntimeDiversityVariantProfile | None) -> list[str]:
    if not profile:
        return []
    markers: list[str] = []
    signature = _diversity_signature_for_profile(profile)
    if signature:
        markers.append(f"diversity:{signature}")
    identity = str(profile.get("subject_identity", "")).strip()
    if identity:
        markers.append(f"identity:{identity}")
        identity_group = _identity_variant_group(identity)
        if identity_group:
            markers.append(f"identity_group:{identity_group}")
    scene_bucket = str(profile.get("scene_bucket", "")).strip()
    if scene_bucket:
        markers.append(f"scene_bucket:{scene_bucket}")
    macro_direction = str(profile.get("macro_direction", "")).strip()
    if macro_direction:
        markers.append(f"macro:{macro_direction}")
    for key in (
        "replace_subject_tags",
        "replace_scene_tags",
        "replace_outfit_tags",
        "replace_light_tags",
        "replace_action_tags",
        "replace_prop_tags",
        "replace_composition_tags",
    ):
        for raw_tag in profile.get(key, []):
            tag = _clean_fragment(raw_tag)
            if tag:
                markers.append(f"tag:{tag}")
    deduped: list[str] = []
    for marker in markers:
        if marker and marker not in deduped:
            deduped.append(marker)
    return deduped


def _recent_macro_directions(recent_tracks: list[str]) -> set[str]:
    directions: set[str] = set(_recent_marker_values(recent_tracks, "macro"))
    for signature in _recent_diversity_signatures(recent_tracks):
        parts = [part.strip() for part in signature.split("::")]
        if len(parts) >= 4 and parts[3]:
            directions.add(parts[3])
    return directions


def _track_history_with_diversity_signature(
    recent_tracks: list[str],
    diversity_signature: str,
) -> list[str]:
    signature_item = f"diversity:{diversity_signature}".strip()
    if not diversity_signature:
        return list(recent_tracks)
    next_tracks = [signature_item]
    next_tracks.extend(item for item in recent_tracks if str(item).strip() != signature_item)
    return next_tracks[:6]


def _is_strong_baseline_intensity(runtime_random_intensity: str) -> bool:
    return str(runtime_random_intensity).strip() == _RUNTIME_RANDOM_INTENSITY_STRONG_BASELINE


def _is_strong_extreme_intensity(runtime_random_intensity: str) -> bool:
    return str(runtime_random_intensity).strip() == _RUNTIME_RANDOM_INTENSITY_STRONG_EXTREME


def _order_runtime_diversity_profiles(
    profiles: list[_RuntimeDiversityVariantProfile],
    *,
    style: str,
    style_track: str,
    recent_tracks: list[str],
    runtime_random_intensity: str,
) -> list[_RuntimeDiversityVariantProfile]:
    if _is_strong_baseline_intensity(runtime_random_intensity):
        return _apply_recent_diversity_guard(
            _order_strong_baseline_diversity_profiles(profiles),
            recent_tracks=recent_tracks,
        )
    if _is_strong_extreme_intensity(runtime_random_intensity):
        return _apply_recent_diversity_guard(
            _order_strong_extreme_diversity_profiles(
                profiles,
                style=style,
                style_track=style_track,
            ),
            recent_tracks=recent_tracks,
        )
    return _apply_recent_diversity_guard(
        list(profiles),
        recent_tracks=recent_tracks,
    )


def _apply_recent_diversity_guard(
    profiles: list[_RuntimeDiversityVariantProfile],
    *,
    recent_tracks: list[str],
) -> list[_RuntimeDiversityVariantProfile]:
    recent_signatures = _recent_diversity_signatures(recent_tracks)
    recent_identities = _recent_profile_identities(recent_tracks)
    recent_identity_groups = _recent_profile_identity_groups(recent_tracks)
    recent_scene_buckets = _recent_scene_buckets(recent_tracks)
    recent_directions = _recent_macro_directions(recent_tracks)
    if not any([recent_signatures, recent_identities, recent_identity_groups, recent_scene_buckets, recent_directions]):
        return list(profiles)

    def is_fresh(
        profile: _RuntimeDiversityVariantProfile,
        *,
        check_signature: bool = True,
        check_identity: bool = True,
        check_identity_group: bool = True,
        check_scene_bucket: bool = True,
        check_macro: bool = True,
    ) -> bool:
        identity = str(profile.get("subject_identity", "")).strip()
        identity_group = _identity_variant_group(identity)
        scene_bucket = str(profile.get("scene_bucket", "")).strip()
        macro_direction = str(profile.get("macro_direction", "")).strip()
        if check_signature and _diversity_signature_for_profile(profile) in recent_signatures:
            return False
        if check_identity and identity and identity in recent_identities:
            return False
        if check_identity_group and identity_group and identity_group in recent_identity_groups:
            return False
        if check_scene_bucket and scene_bucket and scene_bucket in recent_scene_buckets:
            return False
        if check_macro and macro_direction and macro_direction in recent_directions:
            return False
        return True

    fresh_profiles = [
        profile
        for profile in profiles
        if is_fresh(profile)
    ]
    if not fresh_profiles:
        fresh_profiles = [
            profile
            for profile in profiles
            if is_fresh(profile, check_scene_bucket=False)
        ]
    if not fresh_profiles:
        fresh_profiles = [
            profile
            for profile in profiles
            if is_fresh(profile, check_identity_group=False, check_scene_bucket=False)
        ]
    if not fresh_profiles:
        fresh_profiles = [
            profile
            for profile in profiles
            if is_fresh(profile, check_identity_group=False, check_scene_bucket=False, check_macro=False)
        ]
    if not fresh_profiles:
        fresh_profiles = [
            profile
            for profile in profiles
            if is_fresh(profile, check_signature=False, check_identity_group=False, check_scene_bucket=False, check_macro=False)
        ]
    if not fresh_profiles:
        return list(profiles)
    stale_profiles = [
        profile
        for profile in profiles
        if profile not in fresh_profiles
    ]
    return fresh_profiles + stale_profiles


def _order_strong_baseline_diversity_profiles(
    profiles: list[_RuntimeDiversityVariantProfile],
) -> list[_RuntimeDiversityVariantProfile]:
    ordered_profiles: list[_RuntimeDiversityVariantProfile] = []
    used_indexes: set[int] = set()
    for bucket in _STRONG_DIVERSITY_SCENE_BUCKET_ORDER:
        for profile_index, candidate in enumerate(profiles):
            if profile_index in used_indexes or str(candidate.get("scene_bucket", "")).strip() != bucket:
                continue
            ordered_profiles.append(candidate)
            used_indexes.add(profile_index)
            break
    for profile_index, candidate in enumerate(profiles):
        if profile_index in used_indexes:
            continue
        ordered_profiles.append(candidate)
    return ordered_profiles


def _order_strong_extreme_diversity_profiles(
    profiles: list[_RuntimeDiversityVariantProfile],
    *,
    style: str,
    style_track: str,
) -> list[_RuntimeDiversityVariantProfile]:
    baseline_profiles = _order_strong_baseline_diversity_profiles(profiles)
    ordered_profiles: list[_RuntimeDiversityVariantProfile] = []
    used_indexes: set[int] = set()
    used_identities: set[str] = set()
    used_identity_groups: set[str] = set()
    used_style_leads: set[str] = set()

    for bucket in _STRONG_DIVERSITY_SCENE_BUCKET_ORDER:
        best_index = _select_strong_extreme_profile_index(
            baseline_profiles,
            style=style,
            style_track=style_track,
            position=len(ordered_profiles),
            style_bucket=bucket,
            used_indexes=used_indexes,
            used_identities=used_identities,
            used_identity_groups=used_identity_groups,
            used_style_leads=used_style_leads,
        )
        if best_index is None:
            continue
        candidate = baseline_profiles[best_index]
        ordered_profiles.append(candidate)
        used_indexes.add(best_index)
        identity = str(candidate.get("subject_identity", "")).strip()
        identity_group = _identity_variant_group(identity)
        if identity:
            used_identities.add(identity)
        if identity_group:
            used_identity_groups.add(identity_group)
        style_lead = _style_lead_for_extreme_position(
            candidate,
            style=style,
            style_track=style_track,
            position=len(ordered_profiles) - 1,
        )
        if style_lead:
            used_style_leads.add(style_lead)

    while len(ordered_profiles) < len(baseline_profiles):
        next_index = _select_strong_extreme_profile_index(
            baseline_profiles,
            style=style,
            style_track=style_track,
            position=len(ordered_profiles),
            style_bucket="",
            used_indexes=used_indexes,
            used_identities=used_identities,
            used_identity_groups=used_identity_groups,
            used_style_leads=used_style_leads,
        )
        if next_index is None:
            break
        candidate = baseline_profiles[next_index]
        ordered_profiles.append(candidate)
        used_indexes.add(next_index)
        identity = str(candidate.get("subject_identity", "")).strip()
        identity_group = _identity_variant_group(identity)
        if identity:
            used_identities.add(identity)
        if identity_group:
            used_identity_groups.add(identity_group)
        style_lead = _style_lead_for_extreme_position(
            candidate,
            style=style,
            style_track=style_track,
            position=len(ordered_profiles) - 1,
        )
        if style_lead:
            used_style_leads.add(style_lead)
    return ordered_profiles


def _select_strong_extreme_profile_index(
    profiles: list[_RuntimeDiversityVariantProfile],
    *,
    style: str,
    style_track: str,
    position: int,
    style_bucket: str,
    used_indexes: set[int],
    used_identities: set[str],
    used_identity_groups: set[str],
    used_style_leads: set[str],
) -> int | None:
    best_index: int | None = None
    best_score: tuple[int, int, int, int, int] | None = None
    for profile_index, candidate in enumerate(profiles):
        if profile_index in used_indexes:
            continue
        candidate_bucket = str(candidate.get("scene_bucket", "")).strip()
        if style_bucket and candidate_bucket != style_bucket:
            continue
        identity = str(candidate.get("subject_identity", "")).strip()
        identity_group = _identity_variant_group(identity)
        style_lead = _style_lead_for_extreme_position(
            candidate,
            style=style,
            style_track=style_track,
            position=position,
        )
        score = (
            1 if identity and identity not in used_identities else 0,
            1 if identity_group and identity_group not in used_identity_groups else 0,
            1 if style_lead and style_lead not in used_style_leads else 0,
            1 if candidate_bucket in _STRONG_DIVERSITY_SCENE_BUCKET_ORDER else 0,
            -profile_index,
        )
        if best_score is None or score > best_score:
            best_score = score
            best_index = profile_index
    return best_index


def _primary_style_lead_for_identity_profile(
    profile: _RuntimeDiversityVariantProfile,
    *,
    style: str,
) -> str:
    identity = str(profile.get("subject_identity", "")).strip()
    if not identity or not style:
        return ""
    identity_group = _identity_variant_group(identity)
    if not identity_group:
        return ""
    profiles = _RUNTIME_STYLE_IDENTITY_OVERRIDES.get((style, identity_group), [])
    if profiles:
        return str(profiles[0].get("style_lead", "")).strip()
    return ""


def _style_lead_for_extreme_position(
    profile: _RuntimeDiversityVariantProfile,
    *,
    style: str,
    style_track: str,
    position: int,
) -> str:
    identity = str(profile.get("subject_identity", "")).strip()
    identity_group = _identity_variant_group(identity)
    profiles = _resolve_runtime_style_profiles(style, style_track, identity_group)
    if profiles:
        return str(profiles[position % len(profiles)].get("style_lead", "")).strip()
    return _primary_style_lead_for_identity_profile(profile, style=style)


def _resolve_runtime_style_profiles(
    style: str,
    style_track: str,
    identity_group: str,
) -> list[_RuntimeStyleVariantProfile]:
    if identity_group:
        identity_profiles = _RUNTIME_STYLE_IDENTITY_OVERRIDES.get((style, identity_group), [])
        if identity_profiles:
            return identity_profiles
    track_profiles = _RUNTIME_STYLE_TRACK_OVERRIDES.get((style, style_track), [])
    if track_profiles:
        return track_profiles
    return _RUNTIME_STYLE_VARIANT_PROFILES.get(style, [])


def _runtime_style_scene_fragments(style: str, scene_group: str) -> list[str]:
    exact = _RUNTIME_STYLE_SCENE_CUES.get((style, scene_group), [])
    if exact:
        return list(exact)
    return list(_GENERIC_SCENE_CUES.get(scene_group, []))


def _runtime_style_identity_fragments(identity_group: str) -> list[str]:
    return list(_RUNTIME_IDENTITY_CUES.get(identity_group, []))


def _build_runtime_style_variant_profile(
    subject: str,
    style: str,
    runtime_random_enabled: bool,
    index: int,
    generation_count: int,
    context: _PromptBuildContext,
    explicit_template_style: str = "",
) -> _RuntimeStyleVariantProfile | None:
    if not runtime_random_enabled or subject != "人物角色":
        return None
    if str(explicit_template_style).strip() == "自动":
        return None
    identity_group = _identity_variant_group(context["identity"])
    profiles = _resolve_runtime_style_profiles(style, context["style_track"], identity_group)
    if not profiles:
        return None
    profile = profiles[index % len(profiles)]
    extra_fragments = list(profile["extra_fragments"])
    extra_fragments.extend(_runtime_style_scene_fragments(style, context["scene_group"]))
    extra_fragments.extend(_runtime_style_identity_fragments(identity_group))
    return {
        "style_lead": str(profile["style_lead"]).strip(),
        "style_tags": list(profile["style_tags"]),
        "extra_fragments": extra_fragments,
    }


def _variant_group_fragments(
    group_name: str,
    group_tags: list[str],
    person_profile: _PersonPromptVariantProfile | None,
    style_profile: _RuntimeStyleVariantProfile | None,
    diversity_profile: _RuntimeDiversityVariantProfile | None,
) -> list[str]:
    cleaned_tags = [_clean_fragment(tag) for tag in group_tags]
    base_tags = [tag for tag in cleaned_tags if tag]

    if group_name == "主体" and diversity_profile:
        if diversity_profile.get("preserve_selected_subject") and base_tags:
            return base_tags
        replacements = [
            _clean_fragment(tag)
            for tag in diversity_profile.get("replace_subject_tags", [])
            if _clean_fragment(tag)
        ]
        return replacements or base_tags

    if group_name == "场景背景" and diversity_profile:
        if len(base_tags) >= 2:
            preserved_anchor = base_tags[0]
            runtime_scene_tags = [
                _clean_fragment(tag)
                for tag in diversity_profile.get("replace_scene_tags", [])
                if _clean_fragment(tag) and _clean_fragment(tag) != preserved_anchor
            ]
            return [preserved_anchor, *runtime_scene_tags]
        preserved_anchor = next((tag for tag in base_tags if tag), "")
        runtime_scene_tags = [
            _clean_fragment(tag)
            for tag in diversity_profile.get("replace_scene_tags", [])
            if _clean_fragment(tag) and _clean_fragment(tag) != preserved_anchor
        ]
        fragments = [preserved_anchor]
        fragments.extend(runtime_scene_tags)
        return [tag for tag in fragments if tag]

    if group_name == "服装造型" and diversity_profile and diversity_profile.get("replace_outfit_tags"):
        if len(base_tags) >= 2:
            return base_tags[:2]
        return [
            _clean_fragment(tag)
            for tag in diversity_profile.get("replace_outfit_tags", [])
            if _clean_fragment(tag)
        ]

    if group_name == "光影氛围" and diversity_profile and diversity_profile.get("replace_light_tags"):
        if len(base_tags) >= 2:
            return base_tags[:2]
        return [
            _clean_fragment(tag)
            for tag in diversity_profile.get("replace_light_tags", [])
            if _clean_fragment(tag)
        ]

    if group_name == "动作姿态" and diversity_profile and diversity_profile.get("replace_action_tags"):
        if len(base_tags) >= 2:
            return base_tags[:2]
        return [
            _clean_fragment(tag)
            for tag in diversity_profile.get("replace_action_tags", [])
            if _clean_fragment(tag)
        ]

    if group_name == "道具世界观" and diversity_profile and diversity_profile.get("replace_prop_tags"):
        if len(base_tags) >= 2:
            return base_tags[:2]
        return [
            _clean_fragment(tag)
            for tag in diversity_profile.get("replace_prop_tags", [])
            if _clean_fragment(tag)
        ]

    if group_name == "构图视角" and diversity_profile and diversity_profile.get("replace_composition_tags"):
        preserved = [tag for tag in base_tags if tag not in _SHOT_TAGS]
        replacements = [
            _clean_fragment(tag)
            for tag in diversity_profile.get("replace_composition_tags", [])
            if _clean_fragment(tag)
        ]
        return preserved + replacements

    if group_name == "构图视角" and person_profile:
        preserved = [tag for tag in base_tags if tag not in _SHOT_TAGS]
        return preserved + [
            _clean_fragment(tag)
            for tag in person_profile.get("replace_shot_tags", [])
            if _clean_fragment(tag)
        ]

    if group_name == "画面风格" and style_profile:
        return base_tags + [
            _clean_fragment(tag)
            for tag in style_profile.get("style_tags", [])
            if _clean_fragment(tag)
        ]

    return base_tags



def build_prompt_list(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    scene_group: str = "",
    identity: str = "",
    style_track: str = "",
    recent_tracks: list[str] | None = None,
    uniq: Callable[[list[str]], list[str]],
    infer_template_style: Callable[[list[str], str], str],
    infer_subject_type: Callable[[list[str], str], str],
    infer_output_structure: Callable[[str, str], str],
) -> list[str]:
    custom_tags = [_clean_fragment(tag) for tag in custom_tags if _clean_fragment(tag)]
    tags = [tag for group_tags in selected.values() for tag in group_tags] + list(custom_tags)
    style = infer_template_style(tags, str(settings["模板风格"]))
    subject = infer_subject_type(tags, str(settings["主体类型"]))
    settings["主体类型解析结果"] = subject
    _ = infer_output_structure(subject, str(settings["案例输出结构"]))
    mode = str(settings["标签反推模式"])
    order_map = {
        "商业摄影": ["主体", "画面风格", "服装造型", "场景背景", "道具世界观", "光影氛围", "构图视角", "动作姿态", "技术画质"],
        "高密度站点": ["主体", "画面风格", "服装造型", "场景背景", "道具世界观", "光影氛围", "构图视角", "动作姿态", "成人向表达", "技术画质"],
        "成人向成熟": ["主体", "成人向表达", "服装造型", "场景背景", "构图视角", "动作姿态", "光影氛围", "道具世界观", "技术画质"],
        "自动平衡": ["主体", "画面风格", "成人向表达", "服装造型", "场景背景", "道具世界观", "光影氛围", "构图视角", "动作姿态", "技术画质"],
    }
    ordered_groups = order_map.get(mode, order_map["自动平衡"])
    prompt_list: list[str] = []
    explicit_template_style = str(settings.get("模板风格", "") or "").strip()
    english_prompt = _use_english_prompt(settings)
    generation_count = int(settings["生成数量"])
    runtime_random_enabled = bool(settings.get("运行时随机标签", False))
    runtime_random_mode = str(settings.get("运行时随机模式解析结果", "") or settings.get("运行时随机模式", "")).strip()
    runtime_random_intensity = str(settings.get("运行时随机强度", "")).strip()
    preserve_auto_theme_bone = _should_preserve_auto_theme_bone(
        selected,
        settings,
        runtime_random_mode,
        runtime_random_intensity,
    )
    base_context: _PromptBuildContext = {
        "scene_group": str(scene_group).strip(),
        "identity": str(identity).strip(),
        "style_track": str(style_track).strip(),
        "recent_tracks": list(recent_tracks or []),
    }
    runtime_diversity_markers: list[str] = []
    settings["运行时随机档案标记"] = runtime_diversity_markers
    style_lead = _resolve_prompt_style_lead(
        selected,
        explicit_template_style=explicit_template_style,
        inferred_style=style,
        style_track=str(base_context["style_track"]),
        english_prompt=english_prompt,
    )
    for index in range(generation_count):
        person_variant_profile = _build_person_variant_profile(subject, index, generation_count)
        diversity_variant_profile = _build_runtime_diversity_variant_profile(
            subject,
            style,
            runtime_random_enabled,
            runtime_random_mode,
            runtime_random_intensity,
            str(base_context["style_track"]).strip(),
            list(base_context["recent_tracks"]),
            index,
            generation_count,
        ) if not preserve_auto_theme_bone else None
        for marker in _diversity_history_markers_for_profile(diversity_variant_profile):
            if marker not in runtime_diversity_markers:
                runtime_diversity_markers.append(marker)
        prompt_context: _PromptBuildContext = {
            "scene_group": str(
                ""
                if preserve_auto_theme_bone
                else (
                    diversity_variant_profile["scene_group"]
                    if diversity_variant_profile and diversity_variant_profile.get("scene_group")
                    else base_context["scene_group"]
                )
            ).strip(),
            "identity": str(
                diversity_variant_profile["subject_identity"]
                if diversity_variant_profile and diversity_variant_profile.get("subject_identity")
                else base_context["identity"]
            ).strip(),
            "style_track": str(base_context["style_track"]).strip(),
            "recent_tracks": _track_history_with_diversity_signature(
                list(base_context["recent_tracks"]),
                str(
                    diversity_variant_profile["diversity_signature"]
                    if diversity_variant_profile and diversity_variant_profile.get("diversity_signature")
                    else ""
                ).strip(),
            ),
        }
        style_variant_profile = _build_runtime_style_variant_profile(
            subject,
            style,
            runtime_random_enabled,
            index,
            generation_count,
            prompt_context,
            explicit_template_style=explicit_template_style,
        )
        lead_fragment = style_lead
        if style_variant_profile and explicit_template_style != "自动":
            variant_lead = _clean_fragment(style_variant_profile.get("style_lead", ""))
            if variant_lead:
                lead_fragment = variant_lead
        fragment_items: list[_PromptFragmentItem] = []
        order_index = 0
        order_index = _append_prompt_fragment(
            fragment_items,
            lead_fragment,
            priority=_PROMPT_TAIL_PRIORITY["lead"],
            order_index=order_index,
        )
        for group_name in ordered_groups:
            group_fragments = _variant_group_fragments(
                group_name,
                selected.get(group_name, []),
                person_variant_profile,
                style_variant_profile,
                diversity_variant_profile,
            )
            group_priority = _PROMPT_GROUP_PRIORITY.get(group_name, 70)
            for offset, fragment in enumerate(group_fragments):
                order_index = _append_prompt_fragment(
                    fragment_items,
                    fragment,
                    priority=max(60, group_priority - min(offset, 8)),
                    order_index=order_index,
                )
        for custom_offset, custom_tag in enumerate(custom_tags):
            order_index = _append_prompt_fragment(
                fragment_items,
                custom_tag,
                priority=max(62, _PROMPT_TAIL_PRIORITY["custom"] - custom_offset),
                order_index=order_index,
            )
        extra_requirement = str(settings.get("额外要求", "") or "").strip()
        if extra_requirement:
            order_index = _append_prompt_fragment(
                fragment_items,
                extra_requirement,
                priority=_PROMPT_TAIL_PRIORITY["extra"],
                order_index=order_index,
            )
        if person_variant_profile:
            order_index = _append_prompt_fragments(
                fragment_items,
                list(person_variant_profile.get("extra_fragments", [])),
                priority=_PROMPT_TAIL_PRIORITY["person_variant"],
                order_index=order_index,
            )
        if style_variant_profile:
            order_index = _append_prompt_fragments(
                fragment_items,
                list(style_variant_profile.get("extra_fragments", [])),
                priority=_PROMPT_TAIL_PRIORITY["style_variant"],
                order_index=order_index,
            )
        focus_fragment = _variant_focus_fragment(subject, index, generation_count)
        if focus_fragment:
            order_index = _append_prompt_fragment(
                fragment_items,
                focus_fragment,
                priority=_PROMPT_TAIL_PRIORITY["focus"],
                order_index=order_index,
            )
        fragments = _finalize_prompt_fragments(
            fragment_items,
            style,
        )
        fragments = _localize_prompt_fragments(fragments, settings)
        prompt_list.append(
            _expand_prompt_fragments_locally(
                fragments,
                selected,
                custom_tags,
                settings,
                prompt_context,
            )
        )
    return prompt_list


def format_sections(prompt_list: list[str], selected_text: str, settings: dict[str, Any] | None = None) -> tuple[str, str]:
    language = _prompt_language_mode(settings or {})
    english_full_text = language == "纯英文"
    sections = []
    for index, prompt in enumerate(prompt_list, start=1):
        if english_full_text:
            sections.append(
                f"### Prompt {index}\n> {prompt}\n\n#### Tag Analysis\nSelected source tags are available in the node tag output and JSON payload.\n\n#### Suitable Models\nStable Diffusion, ComfyUI, Flux, Midjourney"
            )
        else:
            sections.append(
                f"### 提示词 {index}\n> {prompt}\n\n#### 标签解析\n使用标签：{selected_text}\n\n#### 适用模型\nStable Diffusion、ComfyUI、Flux、Midjourney"
            )
    return "\n\n".join(sections), "\n\n".join(prompt_list)
