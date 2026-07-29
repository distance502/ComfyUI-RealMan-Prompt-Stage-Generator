# -*- coding: utf-8 -*-
"""Unified intent, scene-graph, model-strategy, and preference orchestration."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import re
from typing import Any, Iterable


INTELLIGENCE_PROFILE_VERSION = "qwen-te-intelligence-v31"

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
        "城市街道", "城市", "街头", "街巷", "街区", "小巷", "站台", "车站", "列车", "地铁", "公交车",
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
SCENE_ATTRIBUTE_MARKERS: dict[str, dict[str, tuple[str, ...]]] = {
    "time_of_day": {
        "dawn": (
            "清晨", "黎明", "拂晓", "日出", "晨光",
            "dawn", "sunrise", "early morning",
        ),
        "day": (
            "白天", "日间", "正午", "午后", "硬日光", "阳光明媚",
            "daytime", "daylight", "noon", "midday", "afternoon",
        ),
        "dusk": (
            "黄昏", "傍晚", "日落", "夕阳", "蓝调时刻",
            "dusk", "twilight", "sunset", "evening",
        ),
        "night": (
            "夜晚", "夜间", "深夜", "月光", "月下", "夜景", "夜色", "雨夜", "霓虹夜色",
            "night", "nighttime", "midnight", "moonlight",
        ),
    },
    "precipitation": {
        "clear": (
            "晴天", "晴朗", "万里无云", "clear sky", "sunny",
        ),
        "rain": (
            "雨天", "下雨", "雨中", "雨夜", "暴雨", "雷雨", "阵雨", "霓虹雨夜",
            "rainy", "rainfall", "rainstorm", "thunderstorm", "in the rain",
        ),
        "snow": (
            "雪天", "下雪", "飘雪", "暴雪", "snowfall", "snowy", "blizzard",
        ),
    },
}
_SCENE_ATTRIBUTE_LABELS = {
    "time_of_day": "昼夜",
    "precipitation": "降水",
    "dawn": "清晨",
    "day": "白天",
    "dusk": "黄昏",
    "night": "夜晚",
    "clear": "晴朗",
    "rain": "降雨",
    "snow": "降雪",
}
SUBJECT_CARDINALITY_MARKERS: dict[str, tuple[str, ...]] = {
    "single": (
        "单人", "一个人", "一位人物", "独自一人", "独自",
        "solo", "single person", "one person", "alone",
    ),
    "pair": (
        "双人", "两人", "二人", "两位人物", "情侣", "伴侣", "夫妇",
        "duo", "romantic couple", "adult couple", "couple portrait", "couple interaction",
        "two people", "two women", "two men",
    ),
    "group": (
        "多人", "群像", "团队", "队伍", "小队", "冒险队", "人群", "众人",
        "背景人物", "路人", "旁观者", "每位人物", "每人",
        "group portrait", "ensemble cast", "team", "crowd", "background person", "bystander", "passerby",
    ),
    "none": (
        "无人场景", "无人物", "空无一人", "不出现人物", "无人荒城",
        "no people", "without people", "empty scene",
    ),
}
_SUBJECT_CARDINALITY_LABELS = {
    "single": "单人",
    "pair": "双人",
    "group": "群像",
    "none": "无人",
}
_CARDINALITY_FURNITURE_RE = re.compile(r"(?:单人|双人)(?:床|房|间|沙发|座椅|座位)", flags=re.IGNORECASE)
HUMAN_SUBJECT_INTRUSION_MARKERS: dict[str, tuple[str, ...]] = {
    "identity": (
        "年轻成年女性", "青春感成年女性", "东亚成年女性", "成年女性", "成年男性",
        "中年女性", "中年男性", "年轻女性", "年轻男性", "女性冒险者", "男性冒险者",
        "女冒险者", "男冒险者", "女性角色", "男性角色", "女性", "男性", "女人", "男人",
        "女孩", "少女", "男孩", "模特", "冒险者", "背景人物", "路人", "旁观者", "人物",
        "adult woman", "adult man", "young woman", "young man", "middle-aged woman",
        "middle-aged man", "female model", "male model", "fashion model", "adventurer",
        "background person", "bystander", "passerby", "human character", "human figure",
        "woman", "man", "girl", "boy", "person", "people",
    ),
    "portrait_body": (
        "人物写真", "角色肖像", "人物肖像", "人像写真", "人像", "自拍", "脸部", "面部", "五官",
        "发型", "发丝", "头发", "皮肤", "手指", "人体解剖", "身材", "胸部", "腰臀",
        "fashion portrait", "beauty portrait", "human portrait", "woman portrait", "man portrait",
        "character portrait", "selfie", "visible face", "human face", "facial features",
        "visible skin", "natural skin", "skin texture", "detailed hair", "flowing hair",
        "human anatomy", "human body", "fingers",
    ),
    "human_styling": (
        "丝质睡袍", "晚礼服", "礼服", "内衣", "高跟鞋", "白衬衫", "人物服装",
        "手提包", "胸针", "妆容", "口红", "美甲",
        "elegant dress", "evening dress", "lingerie", "high heels", "white shirt",
        "handbag", "makeup", "lipstick", "manicure",
    ),
}
_HUMAN_PRESENCE_CATEGORIES = {"identity", "portrait_body"}
_HUMAN_SUBJECT_INTRUSION_LABELS = {
    "identity": "人物身份",
    "portrait_body": "人物肖像或身体细节",
    "human_styling": "人物服装或造型",
}
SUBJECT_ORIENTATION_MARKERS: dict[str, tuple[str, ...]] = {
    "front": (
        "正面", "正脸", "正对镜头", "面向镜头", "正面视图", "正面全身", "正面构图",
        "正侧背", "正面侧面背面", "front view", "frontal view", "front-facing", "facing the camera",
        "front side back",
    ),
    "side": (
        "侧面", "侧脸", "标准侧面", "侧面视图", "侧面全身", "侧身构图",
        "正侧背", "正面侧面背面", "side view", "side profile", "profile view", "side-facing",
        "front side back",
    ),
    "back": (
        "背面", "背影", "背对镜头", "从背后拍摄", "背面视图", "背面全身", "背面构图",
        "正侧背", "正面侧面背面", "back view", "rear view", "back-facing", "from behind",
        "front side back",
    ),
}
_SUBJECT_ORIENTATION_LABELS = {
    "front": "正面",
    "side": "侧面",
    "back": "背面",
}
_GENERIC_ORIENTATION_MARKERS = {"正面", "侧面", "背面"}
_ORIENTATION_GLOBAL_SCOPE_RE = re.compile(
    r"(?:角色设定图|人物设定图|三视图|三幅视图|正侧背|正面侧面背面)",
    flags=re.IGNORECASE,
)
_ORIENTATION_PREFIX_SCOPE_RE = re.compile(
    r"(?:保持|采用|使用|要求|只要|拍摄|展示|转向|朝向|面向|不要|排除|避免)[^，,；;。！？.!?\n]{0,8}$",
    flags=re.IGNORECASE,
)
_ORIENTATION_SUFFIX_SCOPE_RE = re.compile(
    r"^(?:视图|全身|构图|朝向|镜头|站姿|轮廓|[、，,；;。/])",
    flags=re.IGNORECASE,
)
SUBJECT_POSE_MARKERS: dict[str, tuple[str, ...]] = {
    "standing": ("站姿", "站立", "直立", "standing pose", "standing upright", "standing"),
    "sitting": ("坐姿", "坐着", "落座", "seated pose", "seated", "sitting"),
    "kneeling": ("跪姿", "单膝跪地", "跪地", "kneeling pose", "kneeling"),
    "lying": ("躺姿", "躺卧", "平躺", "仰卧", "俯卧", "lying pose", "lying down"),
    "crouching": ("蹲姿", "蹲伏", "下蹲", "crouching pose", "crouching", "squatting"),
}
_SUBJECT_POSE_LABELS = {
    "standing": "站姿",
    "sitting": "坐姿",
    "kneeling": "跪姿",
    "lying": "躺姿",
    "crouching": "蹲姿",
}
SHOT_SCALE_MARKERS: dict[str, tuple[str, ...]] = {
    "closeup": (
        "大特写", "面部特写", "眼部特写", "特写镜头", "头肩像", "头像特写", "特写",
        "extreme close-up", "close-up", "close up", "headshot",
    ),
    "medium": (
        "近景半身", "中景半身", "半身像", "半身构图", "牛仔景别", "中景", "半身",
        "medium close-up", "medium shot", "waist-up", "waist up", "cowboy shot",
    ),
    "full_body": (
        "全景全身", "人物完整入镜", "全身完整入镜", "正面全身", "侧面全身", "背面全身",
        "全身像", "全身构图", "全身", "full-body", "full body", "head-to-toe",
    ),
    "wide": (
        "大远景", "远景构图", "全景建立镜头", "建立镜头", "环境远景", "远景",
        "establishing shot", "wide shot", "long shot",
    ),
}
_SHOT_SCALE_LABELS = {
    "closeup": "特写",
    "medium": "半身/中景",
    "full_body": "全身",
    "wide": "远景",
}
_GENERIC_SHOT_SCALE_MARKERS = {"半身", "全身", "远景"}
_SHOT_SCALE_GLOBAL_SCOPE_RE = re.compile(
    r"(?:景别|构图|镜头|取景|画面|人像|照片|视图|拍摄)",
    flags=re.IGNORECASE,
)
_SHOT_SCALE_PREFIX_SCOPE_RE = re.compile(
    r"(?:保持|采用|使用|要求|只要|拍摄|展示|改为|改成|换为|换成|拉到|推进到|景别为)"
    r"[^，,；;。！？.!?\n]{0,10}$",
    flags=re.IGNORECASE,
)
_SHOT_SCALE_SUFFIX_SCOPE_RE = re.compile(
    r"^(?:镜头|景别|构图|画面|视图|人像|像|照)",
    flags=re.IGNORECASE,
)
CAMERA_ANGLE_MARKERS: dict[str, tuple[str, ...]] = {
    "low_angle": (
        "低角度广角仰拍", "低角度仰拍", "仰拍镜头", "虫视角", "仰拍", "低角度",
        "worm's-eye view", "low-angle shot", "low angle shot", "low-angle", "low angle",
    ),
    "eye_level": (
        "视线高度平视", "眼平机位", "平视镜头", "平视视角", "平视",
        "eye-level shot", "eye level shot", "eye-level", "eye level",
    ),
    "high_angle": (
        "高角度俯拍", "高机位俯拍", "俯拍镜头", "高机位", "俯拍", "高角度",
        "high-angle shot", "high angle shot", "high-angle", "high angle",
    ),
    "top_down": (
        "正俯视顶拍", "垂直顶拍", "顶视图", "顶视镜头", "顶视鸟瞰", "鸟瞰视角", "鸟瞰",
        "航拍俯视", "正俯视",
        "top-down shot", "top down shot", "overhead shot", "bird's-eye view", "bird eye view",
    ),
}
_CAMERA_ANGLE_LABELS = {
    "low_angle": "低角度仰拍",
    "eye_level": "平视",
    "high_angle": "高角度俯拍",
    "top_down": "顶视/鸟瞰",
}
_GENERIC_CAMERA_ANGLE_MARKERS = {"低角度", "高角度", "low-angle", "low angle", "high-angle", "high angle"}
_CAMERA_ANGLE_GLOBAL_SCOPE_RE = re.compile(
    r"(?:机位|镜头|摄影机|摄像机|拍摄|取景|构图|视角|camera|shot|view)",
    flags=re.IGNORECASE,
)
_CAMERA_ANGLE_PREFIX_SCOPE_RE = re.compile(
    r"(?:保持|采用|使用|要求|只要|拍摄|切到|切换到|改为|改成|换为|换成|机位为|镜头为)"
    r"[^，,；;。！？.!?\n]{0,10}$",
    flags=re.IGNORECASE,
)
_CAMERA_ANGLE_SUFFIX_SCOPE_RE = re.compile(
    r"^(?:机位|镜头|视角|角度|构图|拍摄|camera|shot|view)",
    flags=re.IGNORECASE,
)
LIGHT_TEMPERATURE_MARKERS: dict[str, tuple[str, ...]] = {
    "warm": (
        "烛火暖光", "暖金柔光", "暖色轮廓逆光", "暖色灯光", "暖色调", "暖色光",
        "琥珀色光", "琥珀光", "橙色灯光", "金色灯光", "黄金时刻暖光", "暖光", "暖色",
        "warm color palette", "warm colour palette", "warm color grading", "warm lighting",
        "warm light", "amber light", "golden light", "orange lighting",
    ),
    "cool": (
        "冷色工业顶光", "冷雾惊悚侧光", "冷硬侧光", "冷白顶光", "冷白光", "冷月光",
        "蓝灰月光", "青蓝冷光", "蓝色冷光", "冷色调", "冷色光", "冷光", "冷色",
        "cool color palette", "cool colour palette", "cool color grading", "cool lighting",
        "cool light", "cold light", "blue-gray lighting", "blue grey lighting",
    ),
    "neutral": (
        "中性色调", "中性灰调", "中性白光", "中性光", "无偏色色温",
        "neutral color palette", "neutral colour palette", "neutral color grading",
        "neutral lighting", "neutral light", "color-neutral light", "colour-neutral light",
    ),
}
_LIGHT_TEMPERATURE_LABELS = {
    "warm": "暖色温",
    "cool": "冷色温",
    "neutral": "中性色温",
}
_GENERIC_LIGHT_TEMPERATURE_MARKERS = {"暖色", "冷色"}
_LIGHT_TEMPERATURE_GLOBAL_SCOPE_RE = re.compile(
    r"(?:色温|色调|调色|配色|灯光|光线|照明|主光|辅光|轮廓光|氛围|"
    r"color|colour|palette|grading|lighting|light)",
    flags=re.IGNORECASE,
)
_LIGHT_TEMPERATURE_PREFIX_SCOPE_RE = re.compile(
    r"(?:保持|采用|使用|要求|只要|固定为|设为|改为|改成|调为|调成|排除|不要)"
    r"[^，,；;。！？.!?\n]{0,12}$",
    flags=re.IGNORECASE,
)
_LIGHT_TEMPERATURE_SUFFIX_SCOPE_RE = re.compile(
    r"^(?:色温|色调|调色|配色|灯光|光线|照明|主光|辅光|轮廓光|氛围|"
    r"color|colour|palette|grading|lighting|light)",
    flags=re.IGNORECASE,
)
COLOR_RENDERING_MARKERS: dict[str, tuple[str, ...]] = {
    "monochrome": (
        "高对比黑白", "黑白线稿", "黑白漫画", "黑白摄影", "黑白版画", "黑白画面",
        "灰度画面", "灰阶画面", "灰阶渲染", "单色画面", "单色渲染", "水墨单色",
        "black-and-white", "black and white", "monochrome", "grayscale", "greyscale",
        "gray-scale rendering", "grey-scale rendering", "monochrome rendering",
    ),
    "full_color": (
        "全彩画面", "全彩插画", "全彩漫画", "全彩渲染", "彩色画面", "彩色摄影", "彩色渲染",
        "彩色霓虹光", "鲜艳色彩", "高饱和色彩", "多彩画面",
        "full-color", "full color", "full-colour", "full colour", "color image", "colour image",
        "color rendering", "colour rendering", "vivid colors", "vivid colours",
        "vibrant colors", "vibrant colours",
    ),
}
_COLOR_RENDERING_LABELS = {
    "monochrome": "黑白/单色",
    "full_color": "全彩",
}
_SELECTIVE_COLOR_RE = re.compile(
    r"(?:局部彩色|选择性色彩|单色点缀|只保留[^，,；;。！？.!?\n]{0,12}(?:红|橙|黄|绿|青|蓝|紫|粉|金|银)色|"
    r"selective colou?r|colou?r splash|single colou?r accent)",
    flags=re.IGNORECASE,
)
DEPTH_OF_FIELD_MARKERS: dict[str, tuple[str, ...]] = {
    "shallow": (
        "大光圈浅景深", "浅景深", "背景虚化", "前景虚化", "大光圈虚化", "柔和散景",
        "奶油散景", "焦外光斑", "散景光斑",
        "shallow depth of field", "shallow focus", "blurred background", "defocused background",
        "out-of-focus background", "foreground blur", "background blur", "creamy bokeh", "bokeh",
    ),
    "deep": (
        "前中后景全部清晰", "前中后景均清晰", "前景中景背景均清晰", "前后景同时清晰",
        "全画面清晰", "全景深", "深景深", "深焦摄影", "深焦构图",
        "deep depth of field", "deep focus", "everything in focus", "front-to-back sharpness",
        "foreground and background in focus", "near and far in focus",
    ),
}
_DEPTH_OF_FIELD_LABELS = {
    "shallow": "浅景深",
    "deep": "深景深/深焦",
}
_COMPLEX_FOCUS_RE = re.compile(
    r"(?:分区对焦|双焦点|分割焦点|移焦|焦点转移|焦点拉动|焦点从[^，,；;。！？.!?\n]{0,32}(?:转向|移动到)|"
    r"split diopter|split focus|rack focus|focus pull|pull focus)",
    flags=re.IGNORECASE,
)
LIGHTING_QUALITY_MARKERS: dict[str, tuple[str, ...]] = {
    "hard": (
        "黑色电影硬光", "硬质侧逆光", "硬质侧光", "锐利硬光", "冷硬侧光", "硬日光",
        "直闪硬光", "硬光照明", "硬光",
        "hard side light", "hard backlight", "hard lighting", "hard light",
        "harsh lighting", "harsh light", "crisp shadows", "sharp-edged shadows",
    ),
    "soft": (
        "阴天柔散光", "窗纱柔光", "暖金柔光", "清晨柔光", "柔和侧光", "柔和漫射光",
        "柔散光", "漫射光", "柔和光线", "柔光照明", "柔光",
        "soft diffused light", "soft side light", "soft lighting", "soft light",
        "diffused lighting", "diffused light", "diffuse lighting", "overcast light",
        "soft-edged shadows",
    ),
}
_LIGHTING_QUALITY_LABELS = {
    "hard": "硬光",
    "soft": "柔光/漫射光",
}
MOTION_RENDERING_MARKERS: dict[str, tuple[str, ...]] = {
    "frozen": (
        "高速快门凝固动作", "高速快门冻结", "高速快门", "动作冻结", "凝固动作", "瞬间凝固",
        "冻结瞬间", "清晰定格", "无运动模糊",
        "high shutter speed", "fast shutter speed", "freeze motion", "frozen motion",
        "motion frozen", "crisp action", "action frozen", "no motion blur",
    ),
    "motion_trail": (
        "长曝光拖影", "慢门拖影", "动作拖影", "速度拖影", "运动模糊", "动态模糊",
        "光轨拖影", "光线轨迹", "光轨", "长曝光", "慢门",
        "motion blur", "long exposure", "shutter drag", "dragged shutter",
        "motion trail", "motion trails", "light trail", "light trails",
    ),
}
_MOTION_RENDERING_LABELS = {
    "frozen": "高速快门凝固",
    "motion_trail": "运动模糊/慢门拖影",
}
_PANNING_MOTION_RE = re.compile(
    r"(?:追焦拍摄|追随摇摄|摇摄追随|横向摇摄|主体清晰[^，,；;。！？.!?\n]{0,32}背景[^，,；;。！？.!?\n]{0,16}(?:模糊|拖影)|"
    r"panning shot|pan(?:ning)? with (?:the )?subject|sharp subject[^;.!?\n]{0,48}(?:blurred|motion-blurred) background)",
    flags=re.IGNORECASE,
)
CAMERA_STABILITY_MARKERS: dict[str, tuple[str, ...]] = {
    "stable": (
        "三脚架固定拍摄", "三脚架固定机位", "锁定机位", "固定机位", "镜头保持稳定",
        "稳定镜头", "稳定器拍摄", "平稳运镜", "无镜头晃动",
        "locked-off camera", "locked off camera", "tripod-mounted camera", "tripod shot",
        "stabilized camera", "stable camera", "steady camera", "smooth stabilized shot",
        "no camera shake",
    ),
    "handheld": (
        "手持纪实镜头", "手持纪实感", "手持摄影", "手持拍摄", "手持镜头",
        "肩扛摄影", "肩扛镜头", "镜头晃动", "晃动镜头", "手持晃动",
        "handheld documentary shot", "handheld photography", "handheld camera", "handheld shot",
        "shoulder-mounted camera", "shoulder mounted camera", "shaky camera", "camera shake",
    ),
}
_CAMERA_STABILITY_LABELS = {
    "stable": "稳定/固定机位",
    "handheld": "手持/晃动镜头",
}
_HYBRID_CAMERA_STABILITY_RE = re.compile(
    r"(?:手持(?:稳定器|云台)|(?:稳定器|云台)手持|手持[^，,；;。！？.!?\n]{0,24}(?:稳定|平稳)|"
    r"handheld (?:gimbal|stabilizer)|stabili[sz]ed handheld|handheld[^;.!?\n]{0,32}(?:stable|steady|smooth))",
    flags=re.IGNORECASE,
)
FOCAL_PERSPECTIVE_MARKERS: dict[str, tuple[str, ...]] = {
    "wide": (
        "低角度广角仰拍", "广角环境建立镜头", "广角环境镜头", "广角全身", "广角透视",
        "超广角全景", "超广角镜头", "超广角", "广角镜头", "28mm镜头", "24mm镜头", "广角",
        "ultra-wide panoramic framing", "ultra-wide-angle lens", "ultra wide angle lens",
        "ultra-wide lens", "ultra wide lens", "wide-angle lens", "wide angle lens",
        "wide-angle perspective", "wide angle perspective", "28mm lens", "24mm lens",
    ),
    "telephoto": (
        "200mm长焦压缩", "135mm长焦", "长焦压缩透视", "长焦压缩空间", "长焦压缩定格",
        "长焦压缩", "长焦镜头", "望远镜头", "中长焦", "长焦",
        "200mm long-lens compression", "200mm telephoto", "135mm telephoto",
        "telephoto compression perspective", "telephoto compression", "telephoto lens",
        "long-lens compression", "long lens compression", "long lens",
    ),
}
_FOCAL_PERSPECTIVE_LABELS = {
    "wide": "广角空间延展",
    "telephoto": "长焦空间压缩",
}
_FOCAL_TRANSITION_RE = re.compile(
    r"(?:希区柯克变焦|滑动变焦|推拉变焦|变焦推拉|焦段(?:连续)?变化|焦段从[^，,；;。！？.!?\n]{0,32}(?:变为|切换到|过渡到)|"
    r"dolly zoom|vertigo effect|focal length transition|zoom transition|zoom from[^;.!?\n]{0,48}(?:to|into))",
    flags=re.IGNORECASE,
)
KEY_LIGHT_DIRECTION_MARKERS: dict[str, tuple[str, ...]] = {
    "front": (
        "正面主光", "正面打光", "正面光照", "正面光", "顺光照明", "顺光",
        "frontal key light", "front key light", "front lighting", "frontal lighting",
        "front-lit", "front lit",
    ),
    "side": (
        "冷雾惊悚侧光", "黄金时刻侧光", "落日余晖侧光", "柔和侧光", "硬质侧光",
        "冷硬侧光", "侧向主光", "侧面主光", "侧光照明", "侧光",
        "side key light", "side lighting", "side light", "sidelight",
    ),
    "back": (
        "暖色轮廓逆光", "日落逆光", "黄昏逆光", "圣辉逆光", "戏剧逆光",
        "星际逆光", "霓虹逆光", "沙尘逆光", "背后主光", "背光照明", "逆光",
        "back key light", "back lighting", "backlighting", "back light", "backlight",
    ),
    "top": (
        "冷色工业顶光", "冷白顶光", "冷荧顶光", "顶光烟雾", "顶部主光",
        "顶光照明", "顶光",
        "overhead key light", "top lighting", "top light", "overhead lighting",
    ),
}
_KEY_LIGHT_DIRECTION_LABELS = {
    "front": "正面主光",
    "side": "侧向主光",
    "back": "逆光/背后主光",
    "top": "顶部主光",
}
_COMPLEX_LIGHT_DIRECTION_RE = re.compile(
    r"(?:侧逆光|侧后方(?:主)?光|三点布光|交叉布光|双侧布光|多方向布光|多灯位|"
    r"主光[^，,；;。！？.!?\n]{0,36}(?:补光|轮廓光)|(?:补光|轮廓光)[^，,；;。！？.!?\n]{0,36}主光|"
    r"three-point lighting|cross lighting|multiple light directions|key light[^;.!?\n]{0,48}(?:fill light|rim light)|"
    r"(?:fill light|rim light)[^;.!?\n]{0,48}key light)",
    flags=re.IGNORECASE,
)


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
    r"(?:不要|不需要|不必|不出现|不展示|不包含|无需|不能|别(?:再)?|未(?:启用|使用|包含|生成)?|避免|禁止|排除|移除|去掉|不是|并非|不得|不可|"
    r"\b(?:do\s+not|don't|does\s+not|doesn't|cannot|can't|should\s+not|shouldn't|must\s+not|"
    r"will\s+not|won't|not|never|without|avoid|exclude|remove|omit)\b)"
    r"[^，,；;。！？.!?\n]{0,48}$",
    flags=re.IGNORECASE,
)
_NEGATION_CANCEL_RE = re.compile(
    r"(?:不仅|不只|不止|不光|\bnot\s+only\b)[^，,；;。！？.!?\n]{0,48}$",
    flags=re.IGNORECASE,
)
_DIRECT_NEGATION_RE = re.compile(
    r"(?:没有|不含|无|非|\bno\b)\s*(?:任何|任意|any)?\s*$",
    flags=re.IGNORECASE,
)
_PRIMARY_SCENE_CUE_PATTERNS = (
    re.compile(
        r"(?:主场景|主要场景|核心地点|主要地点|故事发生地)\s*"
        r"(?:设(?:定|置)?\s*)?(?:在|为|是|位于|放在|选在|[:：])\s*"
        r"([^；;。！？!?\n]{1,64})",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?:故事|画面|镜头)\s*(?:发生|展开|定格)\s*(?:在|于)\s*"
        r"([^；;。！？!?\n]{1,64})",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:primary|main|core)\s+(?:scene|setting|location)\s*"
        r"(?:is|at|in|:)?\s*([^;.!?\n]{1,80})",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:the\s+)?(?:story|scene)\s+(?:takes\s+place|is\s+set)\s+"
        r"(?:in|at)\s+([^;.!?\n]{1,80})",
        flags=re.IGNORECASE,
    ),
)
_PRIMARY_SCENE_OVERRIDE_PATTERNS = (
    re.compile(
        r"(?:改为|改成|换为|换成|调整为|切换到|切换为|转为)\s*"
        r"([^，,；;。！？!?\n]{1,64})",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"(?:最终|最后)\s*(?:将|把)?\s*"
        r"(?:主场景|主要场景|核心地点|主要地点|故事发生地)\s*"
        r"(?:设(?:定|置)?\s*)?(?:在|为|是|位于|放在|选在|[:：])\s*"
        r"([^，,；;。！？!?\n]{1,64})",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:change|switch)\s+(?:(?:the\s+)?(?:primary|main|core)\s+"
        r"(?:scene|setting|location)|it)\s+(?:to|into)\s+([^,;.!?\n]{1,80})",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:use|choose|set|place)\s+([^,;.!?\n]{1,80}?)\s+instead\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:finally|ultimately)\s+(?:set|place|use|choose)\s+"
        r"(?:(?:the\s+)?(?:primary|main|core)\s+(?:scene|setting|location)\s+)?"
        r"(?:in|at|to|as)?\s*([^,;.!?\n]{1,80})",
        flags=re.IGNORECASE,
    ),
)
_PRIMARY_SCENE_SCOPE_RE = re.compile(
    r"(?:主场景|主要场景|核心地点|主要地点|故事发生地|"
    r"\b(?:primary|main|core)\s+(?:scene|setting|location)\b)",
    flags=re.IGNORECASE,
)
_SENTENCE_BOUNDARY_RE = re.compile(r"[。！？.!?\n]")


def _marker_matches(text: str, marker: str) -> list[re.Match[str]]:
    source = str(text or "").casefold()
    needle = str(marker or "").casefold()
    if not source or not needle:
        return []
    if needle.isascii() and re.fullmatch(r"[a-z0-9][a-z0-9 ._-]*", needle):
        return list(re.finditer(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", source))
    return list(re.finditer(re.escape(needle), source))


def _marker_match_is_negated(source: str, match_start: int) -> bool:
    prefix = source[max(0, match_start - 80) : match_start]
    clause_prefix = _CLAUSE_BOUNDARY_RE.split(prefix)[-1][-48:]
    broad_negation = _BROAD_NEGATION_RE.search(clause_prefix)
    return bool(
        (broad_negation and not _NEGATION_CANCEL_RE.search(clause_prefix))
        or _DIRECT_NEGATION_RE.search(clause_prefix)
    )


def _marker_polarity(text: str, marker: str) -> tuple[bool, bool]:
    source = str(text or "").casefold()
    positive = False
    negated = False
    for match in _marker_matches(source, marker):
        if _marker_match_is_negated(source, match.start()):
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


def detect_negated_world_families(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    hits: dict[str, list[str]] = {}
    for family, markers in WORLD_FAMILY_MARKERS.items():
        matched = [marker for marker in markers if _marker_polarity(source, marker)[1]]
        if matched:
            hits[family] = matched
    return hits


def _detect_scene_attributes(text: Any, *, negated: bool) -> dict[str, dict[str, list[str]]]:
    source = _clean(text)
    hits: dict[str, dict[str, list[str]]] = {}
    for axis, values in SCENE_ATTRIBUTE_MARKERS.items():
        axis_hits: dict[str, list[str]] = {}
        for value, markers in values.items():
            matched = [
                marker
                for marker in markers
                if _marker_polarity(source, marker)[1 if negated else 0]
            ]
            if matched:
                axis_hits[value] = matched
        if axis_hits:
            hits[axis] = axis_hits
    return hits


def detect_scene_attributes(text: Any) -> dict[str, dict[str, list[str]]]:
    return _detect_scene_attributes(text, negated=False)


def detect_negated_scene_attributes(text: Any) -> dict[str, dict[str, list[str]]]:
    return _detect_scene_attributes(text, negated=True)


def _context_scene_attribute_constraints(text: Any) -> dict[str, dict[str, Any]]:
    positive = detect_scene_attributes(text)
    negated = detect_negated_scene_attributes(text)
    constraints: dict[str, dict[str, Any]] = {}
    for axis in SCENE_ATTRIBUTE_MARKERS:
        positive_values = list(positive.get(axis, {}))
        negated_values = list(negated.get(axis, {}))
        overlap = set(positive_values) & set(negated_values)
        positive_values = [value for value in positive_values if value not in overlap]
        negated_values = [value for value in negated_values if value not in overlap]
        required = positive_values[0] if len(positive_values) == 1 else ""
        if not required and not negated_values:
            continue
        constraints[axis] = {
            "axis_label": _SCENE_ATTRIBUTE_LABELS[axis],
            "required_value": required,
            "required_label": _SCENE_ATTRIBUTE_LABELS.get(required, "") if required else "",
            "positive_values": positive_values,
            "negated_values": negated_values,
            "negated_labels": [_SCENE_ATTRIBUTE_LABELS.get(value, value) for value in negated_values],
            "positive_evidence": {
                value: list(positive.get(axis, {}).get(value, [])) for value in positive_values
            },
            "negated_evidence": {
                value: list(negated.get(axis, {}).get(value, [])) for value in negated_values
            },
        }
    return constraints


def _detect_subject_cardinality(text: Any, *, negated: bool) -> dict[str, list[str]]:
    source = _CARDINALITY_FURNITURE_RE.sub("", _clean(text))
    hits: dict[str, list[str]] = {}
    for value, markers in SUBJECT_CARDINALITY_MARKERS.items():
        matched = [
            marker
            for marker in markers
            if _marker_polarity(source, marker)[1 if negated else 0]
        ]
        if matched:
            hits[value] = matched
    return hits


def detect_subject_cardinality(text: Any) -> dict[str, list[str]]:
    return _detect_subject_cardinality(text, negated=False)


def detect_negated_subject_cardinality(text: Any) -> dict[str, list[str]]:
    return _detect_subject_cardinality(text, negated=True)


def _context_subject_cardinality_constraint(text: Any) -> dict[str, Any]:
    positive = detect_subject_cardinality(text)
    negated = detect_negated_subject_cardinality(text)
    positive_values = list(positive)
    negated_values = list(negated)
    overlap = set(positive_values) & set(negated_values)
    positive_values = [value for value in positive_values if value not in overlap]
    negated_values = [value for value in negated_values if value not in overlap]
    required = positive_values[0] if len(positive_values) == 1 else ""
    if not required and not negated_values:
        return {}
    return {
        "required_value": required,
        "required_label": _SUBJECT_CARDINALITY_LABELS.get(required, "") if required else "",
        "positive_values": positive_values,
        "negated_values": negated_values,
        "negated_labels": [_SUBJECT_CARDINALITY_LABELS.get(value, value) for value in negated_values],
        "positive_evidence": {value: list(positive.get(value, [])) for value in positive_values},
        "negated_evidence": {value: list(negated.get(value, [])) for value in negated_values},
    }


def detect_human_subject_intrusions(text: Any) -> dict[str, list[str]]:
    """Return positive human-only details while respecting local negation."""

    source = _clean(text)
    hits: dict[str, list[str]] = {}
    for category, markers in HUMAN_SUBJECT_INTRUSION_MARKERS.items():
        matched = [marker for marker in markers if _marker_present(source, marker)]
        if matched:
            hits[category] = matched
    return hits


def introduced_human_subject_intrusions(original: Any, candidate: Any) -> dict[str, list[str]]:
    """Return human-only markers introduced by a candidate rather than inherited from its baseline."""

    original_hits = detect_human_subject_intrusions(original)
    candidate_hits = detect_human_subject_intrusions(candidate)
    introduced: dict[str, list[str]] = {}
    for category, markers in candidate_hits.items():
        original_markers = set(original_hits.get(category, []))
        new_markers = [marker for marker in markers if marker not in original_markers]
        if new_markers:
            introduced[category] = new_markers
    return introduced


def _context_subject_presence_constraint(text: Any, subject_type: Any) -> dict[str, Any]:
    context = _clean(text)
    cardinality = _context_subject_cardinality_constraint(context)
    required_cardinality = _clean(cardinality.get("required_value"))
    context_human_hits = {
        category: markers
        for category, markers in detect_human_subject_intrusions(context).items()
        if category in _HUMAN_PRESENCE_CATEGORIES
    }
    # A story may deliberately begin empty and later introduce a person. Multiple
    # temporal states must remain available to video and long-form narrative modes.
    if required_cardinality == "none" and not context_human_hits:
        return {
            "required_value": "none",
            "required_label": "无人场景",
            "source": "natural_context",
            "forbidden_categories": list(HUMAN_SUBJECT_INTRUSION_MARKERS),
            "evidence": list(cardinality.get("positive_evidence", {}).get("none", [])),
        }
    if _clean(subject_type) == "非人物主体" and not context_human_hits:
        return {
            "required_value": "non_person",
            "required_label": "非人物主体",
            "source": "task_subject_type",
            "forbidden_categories": list(HUMAN_SUBJECT_INTRUSION_MARKERS),
            "evidence": ["非人物主体"],
        }
    return {}


def _human_intrusion_anchor_hits(anchor: dict[str, Any]) -> dict[str, list[str]]:
    hits = detect_human_subject_intrusions(anchor.get("value"))
    group = _clean(anchor.get("group"))
    if group in {"主体", "场景背景", "道具世界观", "技术画质"}:
        hits.pop("human_styling", None)
    return hits


def _detect_subject_orientation(
    text: Any,
    *,
    negated: bool,
    require_context_scope: bool = False,
) -> dict[str, list[str]]:
    source = _clean(text)
    hits: dict[str, list[str]] = {}
    for value, markers in SUBJECT_ORIENTATION_MARKERS.items():
        matched = []
        for marker in markers:
            if not require_context_scope or marker not in _GENERIC_ORIENTATION_MARKERS:
                if _marker_polarity(source, marker)[1 if negated else 0]:
                    matched.append(marker)
                continue
            for match in _marker_matches(source, marker):
                match_negated = _marker_match_is_negated(source.casefold(), match.start())
                if match_negated != negated:
                    continue
                prefix = source[max(0, match.start() - 24) : match.start()]
                suffix = source[match.end() : match.end() + 10]
                if (
                    _ORIENTATION_GLOBAL_SCOPE_RE.search(source)
                    or _ORIENTATION_PREFIX_SCOPE_RE.search(prefix)
                    or _ORIENTATION_SUFFIX_SCOPE_RE.search(suffix)
                ):
                    matched.append(marker)
                    break
        if matched:
            hits[value] = matched
    return hits


def detect_subject_orientation(text: Any) -> dict[str, list[str]]:
    return _detect_subject_orientation(text, negated=False)


def detect_negated_subject_orientation(text: Any) -> dict[str, list[str]]:
    return _detect_subject_orientation(text, negated=True)


def _context_subject_orientation_constraint(text: Any) -> dict[str, Any]:
    positive = _detect_subject_orientation(text, negated=False, require_context_scope=True)
    negated = _detect_subject_orientation(text, negated=True, require_context_scope=True)
    positive_values = list(positive)
    negated_values = list(negated)
    overlap = set(positive_values) & set(negated_values)
    positive_values = [value for value in positive_values if value not in overlap]
    negated_values = [value for value in negated_values if value not in overlap]
    required = positive_values[0] if len(positive_values) == 1 else ""
    if not required and not negated_values:
        return {}
    return {
        "required_value": required,
        "required_label": _SUBJECT_ORIENTATION_LABELS.get(required, "") if required else "",
        "positive_values": positive_values,
        "negated_values": negated_values,
        "negated_labels": [_SUBJECT_ORIENTATION_LABELS.get(value, value) for value in negated_values],
        "positive_evidence": {value: list(positive.get(value, [])) for value in positive_values},
        "negated_evidence": {value: list(negated.get(value, [])) for value in negated_values},
    }


def _detect_exclusive_visual_axis(
    text: Any,
    markers_by_value: dict[str, tuple[str, ...]],
    *,
    negated: bool,
    require_context_scope: bool = False,
    generic_markers: set[str] | None = None,
    global_scope_re: re.Pattern[str] | None = None,
    prefix_scope_re: re.Pattern[str] | None = None,
    suffix_scope_re: re.Pattern[str] | None = None,
) -> dict[str, list[str]]:
    source = _clean(text)
    generic = generic_markers or set()
    hits: dict[str, list[str]] = {}
    for value, markers in markers_by_value.items():
        matched: list[str] = []
        for marker in markers:
            if not require_context_scope or marker not in generic:
                if _marker_polarity(source, marker)[1 if negated else 0]:
                    matched.append(marker)
                continue
            for match in _marker_matches(source, marker):
                match_negated = _marker_match_is_negated(source.casefold(), match.start())
                if match_negated != negated:
                    continue
                prefix = source[max(0, match.start() - 28) : match.start()]
                suffix = source[match.end() : match.end() + 12]
                local_prefix = _CLAUSE_BOUNDARY_RE.split(
                    source[max(0, match.start() - 64) : match.start()]
                )[-1]
                local_suffix = _CLAUSE_BOUNDARY_RE.split(
                    source[match.end() : match.end() + 64]
                )[0]
                local_scope = f"{local_prefix}{marker}{local_suffix}"
                broad_local_negation = _BROAD_NEGATION_RE.search(local_prefix)
                terminal_negated_scope = bool(
                    negated
                    and broad_local_negation
                    and not _NEGATION_CANCEL_RE.search(local_prefix)
                    and not local_suffix.strip()
                )
                if (
                    (global_scope_re is not None and global_scope_re.search(local_scope))
                    or (prefix_scope_re is not None and prefix_scope_re.search(prefix))
                    or (suffix_scope_re is not None and suffix_scope_re.search(suffix))
                    or terminal_negated_scope
                ):
                    matched.append(marker)
                    break
        if matched:
            hits[value] = matched
    return hits


def _exclusive_visual_axis_constraint(
    positive: dict[str, list[str]],
    negated: dict[str, list[str]],
    labels: dict[str, str],
    *,
    axis_label: str,
) -> dict[str, Any]:
    positive_values = list(positive)
    negated_values = list(negated)
    overlap = set(positive_values) & set(negated_values)
    positive_values = [value for value in positive_values if value not in overlap]
    negated_values = [value for value in negated_values if value not in overlap]
    required = positive_values[0] if len(positive_values) == 1 else ""
    if not required and not negated_values:
        return {}
    return {
        "axis_label": axis_label,
        "required_value": required,
        "required_label": labels.get(required, "") if required else "",
        "positive_values": positive_values,
        "negated_values": negated_values,
        "negated_labels": [labels.get(value, value) for value in negated_values],
        "positive_evidence": {value: list(positive.get(value, [])) for value in positive_values},
        "negated_evidence": {value: list(negated.get(value, [])) for value in negated_values},
    }


def detect_subject_pose(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(text, SUBJECT_POSE_MARKERS, negated=False)


def detect_negated_subject_pose(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(text, SUBJECT_POSE_MARKERS, negated=True)


def _context_subject_pose_constraint(text: Any) -> dict[str, Any]:
    positive = detect_subject_pose(text)
    negated = detect_negated_subject_pose(text)
    return _exclusive_visual_axis_constraint(
        positive,
        negated,
        _SUBJECT_POSE_LABELS,
        axis_label="主体姿态",
    )


def detect_shot_scale(text: Any, *, require_context_scope: bool = False) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SHOT_SCALE_MARKERS,
        negated=False,
        require_context_scope=require_context_scope,
        generic_markers=_GENERIC_SHOT_SCALE_MARKERS,
        global_scope_re=_SHOT_SCALE_GLOBAL_SCOPE_RE,
        prefix_scope_re=_SHOT_SCALE_PREFIX_SCOPE_RE,
        suffix_scope_re=_SHOT_SCALE_SUFFIX_SCOPE_RE,
    )


def detect_negated_shot_scale(text: Any, *, require_context_scope: bool = False) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SHOT_SCALE_MARKERS,
        negated=True,
        require_context_scope=require_context_scope,
        generic_markers=_GENERIC_SHOT_SCALE_MARKERS,
        global_scope_re=_SHOT_SCALE_GLOBAL_SCOPE_RE,
        prefix_scope_re=_SHOT_SCALE_PREFIX_SCOPE_RE,
        suffix_scope_re=_SHOT_SCALE_SUFFIX_SCOPE_RE,
    )


def _context_shot_scale_constraint(text: Any) -> dict[str, Any]:
    positive = detect_shot_scale(text, require_context_scope=True)
    negated = detect_negated_shot_scale(text, require_context_scope=True)
    return _exclusive_visual_axis_constraint(
        positive,
        negated,
        _SHOT_SCALE_LABELS,
        axis_label="景别",
    )


def detect_camera_angle(text: Any, *, require_context_scope: bool = False) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        CAMERA_ANGLE_MARKERS,
        negated=False,
        require_context_scope=require_context_scope,
        generic_markers=_GENERIC_CAMERA_ANGLE_MARKERS,
        global_scope_re=_CAMERA_ANGLE_GLOBAL_SCOPE_RE,
        prefix_scope_re=_CAMERA_ANGLE_PREFIX_SCOPE_RE,
        suffix_scope_re=_CAMERA_ANGLE_SUFFIX_SCOPE_RE,
    )


def detect_negated_camera_angle(text: Any, *, require_context_scope: bool = False) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        CAMERA_ANGLE_MARKERS,
        negated=True,
        require_context_scope=require_context_scope,
        generic_markers=_GENERIC_CAMERA_ANGLE_MARKERS,
        global_scope_re=_CAMERA_ANGLE_GLOBAL_SCOPE_RE,
        prefix_scope_re=_CAMERA_ANGLE_PREFIX_SCOPE_RE,
        suffix_scope_re=_CAMERA_ANGLE_SUFFIX_SCOPE_RE,
    )


def _context_camera_angle_constraint(text: Any) -> dict[str, Any]:
    positive = detect_camera_angle(text, require_context_scope=True)
    negated = detect_negated_camera_angle(text, require_context_scope=True)
    return _exclusive_visual_axis_constraint(
        positive,
        negated,
        _CAMERA_ANGLE_LABELS,
        axis_label="机位",
    )


def detect_light_temperature(text: Any, *, require_context_scope: bool = False) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        LIGHT_TEMPERATURE_MARKERS,
        negated=False,
        require_context_scope=require_context_scope,
        generic_markers=_GENERIC_LIGHT_TEMPERATURE_MARKERS,
        global_scope_re=_LIGHT_TEMPERATURE_GLOBAL_SCOPE_RE,
        prefix_scope_re=_LIGHT_TEMPERATURE_PREFIX_SCOPE_RE,
        suffix_scope_re=_LIGHT_TEMPERATURE_SUFFIX_SCOPE_RE,
    )


def detect_negated_light_temperature(
    text: Any,
    *,
    require_context_scope: bool = False,
) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        LIGHT_TEMPERATURE_MARKERS,
        negated=True,
        require_context_scope=require_context_scope,
        generic_markers=_GENERIC_LIGHT_TEMPERATURE_MARKERS,
        global_scope_re=_LIGHT_TEMPERATURE_GLOBAL_SCOPE_RE,
        prefix_scope_re=_LIGHT_TEMPERATURE_PREFIX_SCOPE_RE,
        suffix_scope_re=_LIGHT_TEMPERATURE_SUFFIX_SCOPE_RE,
    )


def _context_light_temperature_constraint(text: Any) -> dict[str, Any]:
    positive = detect_light_temperature(text, require_context_scope=True)
    negated = detect_negated_light_temperature(text, require_context_scope=True)
    return _exclusive_visual_axis_constraint(
        positive,
        negated,
        _LIGHT_TEMPERATURE_LABELS,
        axis_label="整体色温",
    )


def detect_color_rendering(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        COLOR_RENDERING_MARKERS,
        negated=False,
    )


def detect_negated_color_rendering(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        COLOR_RENDERING_MARKERS,
        negated=True,
    )


def _context_color_rendering_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _SELECTIVE_COLOR_RE.search(source):
        return {}
    positive = detect_color_rendering(source)
    negated = detect_negated_color_rendering(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _COLOR_RENDERING_LABELS,
        axis_label="颜色呈现",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_color_rendering_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_color_rendering_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _SELECTIVE_COLOR_RE.search(context) or len(detect_color_rendering(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    positive = detect_color_rendering(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _COLOR_RENDERING_LABELS,
        axis_label="颜色呈现",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_depth_of_field(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        DEPTH_OF_FIELD_MARKERS,
        negated=False,
    )


def detect_negated_depth_of_field(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        DEPTH_OF_FIELD_MARKERS,
        negated=True,
    )


def _context_depth_of_field_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _COMPLEX_FOCUS_RE.search(source):
        return {}
    positive = detect_depth_of_field(source)
    negated = detect_negated_depth_of_field(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _DEPTH_OF_FIELD_LABELS,
        axis_label="景深",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_depth_of_field_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_depth_of_field_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _COMPLEX_FOCUS_RE.search(context) or len(detect_depth_of_field(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    positive = detect_depth_of_field(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _DEPTH_OF_FIELD_LABELS,
        axis_label="景深",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_lighting_quality(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        LIGHTING_QUALITY_MARKERS,
        negated=False,
    )


def detect_negated_lighting_quality(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        LIGHTING_QUALITY_MARKERS,
        negated=True,
    )


def _context_lighting_quality_constraint(text: Any) -> dict[str, Any]:
    positive = detect_lighting_quality(text)
    negated = detect_negated_lighting_quality(text)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _LIGHTING_QUALITY_LABELS,
        axis_label="光质",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_lighting_quality_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_lighting_quality_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if len(detect_lighting_quality(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    positive = detect_lighting_quality(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _LIGHTING_QUALITY_LABELS,
        axis_label="光质",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_motion_rendering(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        MOTION_RENDERING_MARKERS,
        negated=False,
    )


def detect_negated_motion_rendering(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        MOTION_RENDERING_MARKERS,
        negated=True,
    )


def _context_motion_rendering_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _PANNING_MOTION_RE.search(source):
        return {}
    positive = detect_motion_rendering(source)
    negated = detect_negated_motion_rendering(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _MOTION_RENDERING_LABELS,
        axis_label="运动呈现",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_motion_rendering_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_motion_rendering_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _PANNING_MOTION_RE.search(context) or len(detect_motion_rendering(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    positive = detect_motion_rendering(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _MOTION_RENDERING_LABELS,
        axis_label="运动呈现",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_camera_stability(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        CAMERA_STABILITY_MARKERS,
        negated=False,
    )


def detect_negated_camera_stability(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        CAMERA_STABILITY_MARKERS,
        negated=True,
    )


def _context_camera_stability_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _HYBRID_CAMERA_STABILITY_RE.search(source):
        return {}
    positive = detect_camera_stability(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_camera_stability(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _CAMERA_STABILITY_LABELS,
        axis_label="镜头稳定性",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_camera_stability_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_camera_stability_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _HYBRID_CAMERA_STABILITY_RE.search(context) or len(detect_camera_stability(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    positive = detect_camera_stability(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _CAMERA_STABILITY_LABELS,
        axis_label="镜头稳定性",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_focal_perspective(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        FOCAL_PERSPECTIVE_MARKERS,
        negated=False,
    )


def detect_negated_focal_perspective(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        FOCAL_PERSPECTIVE_MARKERS,
        negated=True,
    )


def _context_focal_perspective_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _FOCAL_TRANSITION_RE.search(source):
        return {}
    positive = detect_focal_perspective(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_focal_perspective(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _FOCAL_PERSPECTIVE_LABELS,
        axis_label="焦段透视",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_focal_perspective_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_focal_perspective_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _FOCAL_TRANSITION_RE.search(context) or len(detect_focal_perspective(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    positive = detect_focal_perspective(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _FOCAL_PERSPECTIVE_LABELS,
        axis_label="焦段透视",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_key_light_direction(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        KEY_LIGHT_DIRECTION_MARKERS,
        negated=False,
    )


def detect_negated_key_light_direction(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        KEY_LIGHT_DIRECTION_MARKERS,
        negated=True,
    )


def _context_key_light_direction_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _COMPLEX_LIGHT_DIRECTION_RE.search(source):
        return {}
    positive = detect_key_light_direction(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_key_light_direction(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _KEY_LIGHT_DIRECTION_LABELS,
        axis_label="主光方向",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_key_light_direction_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_key_light_direction_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _COMPLEX_LIGHT_DIRECTION_RE.search(context) or len(detect_key_light_direction(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _COMPLEX_LIGHT_DIRECTION_RE.search(selected_text):
        return {}
    positive = detect_key_light_direction(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _KEY_LIGHT_DIRECTION_LABELS,
        axis_label="主光方向",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def _conflicting_exclusive_axis_anchors(
    anchors: Iterable[dict[str, Any]],
    constraint: dict[str, Any],
    detector: Any,
    labels: dict[str, str],
) -> list[dict[str, Any]]:
    if not constraint:
        return []
    required = _clean(constraint.get("required_value"))
    negated_values = set(constraint.get("negated_values", []) or [])
    conflicts: list[dict[str, Any]] = []
    for raw_anchor in anchors:
        anchor = dict(raw_anchor)
        hits = detector(anchor.get("value"))
        conflicting_values = [
            value
            for value in hits
            if value in negated_values or (required and value != required)
        ]
        if conflicting_values:
            conflicts.append(
                {
                    **anchor,
                    "actual_values": conflicting_values,
                    "actual_labels": [labels.get(value, value) for value in conflicting_values],
                }
            )
    return conflicts


def _primary_world_family_in_text(text: Any) -> tuple[str, str]:
    source = _clean(text).casefold()
    ranked: list[tuple[int, int, int, str, str]] = []
    for family_index, (family, markers) in enumerate(WORLD_FAMILY_MARKERS.items()):
        for marker in markers:
            for match in _marker_matches(source, marker):
                if _marker_match_is_negated(source, match.start()):
                    continue
                ranked.append((match.start(), -len(marker), family_index, family, marker))
    if not ranked:
        return "", ""
    _position, _specificity, _family_index, family, marker = min(ranked)
    return family, marker


def _resolve_primary_world_family(
    scene_values: Iterable[Any],
    natural_context: Any,
) -> tuple[str, str, str]:
    for scene in _unique(scene_values, 8):
        family, marker = _primary_world_family_in_text(scene)
        if family:
            return family, marker, "selected_scene"
    context = _clean(natural_context)
    folded_context = context.casefold()
    raw_cue_matches = [
        match
        for pattern in _PRIMARY_SCENE_CUE_PATTERNS
        for match in pattern.finditer(context)
    ]

    def override_has_scene_scope(match: re.Match[str]) -> bool:
        if _PRIMARY_SCENE_SCOPE_RE.search(match.group(0)):
            return True
        return any(
            cue.start() < match.start()
            and not _SENTENCE_BOUNDARY_RE.search(context[cue.start() : match.start()])
            for cue in raw_cue_matches
        )

    override_matches: list[tuple[int, str]] = []
    for pattern in _PRIMARY_SCENE_OVERRIDE_PATTERNS:
        override_matches.extend(
            (match.start(), _clean(match.group(1)))
            for match in pattern.finditer(context)
            if _clean(match.group(1))
            and not _marker_match_is_negated(folded_context, match.start())
            and override_has_scene_scope(match)
        )
    for _position, override_text in sorted(override_matches, key=lambda item: item[0], reverse=True):
        family, marker = _primary_world_family_in_text(override_text)
        if family:
            return family, marker, "natural_context_override"
    cue_matches = [
        (match.start(), _clean(match.group(1)))
        for match in raw_cue_matches
        if _clean(match.group(1))
        and not _marker_match_is_negated(folded_context, match.start())
    ]
    for _position, cue_text in sorted(cue_matches, key=lambda item: item[0]):
        family, marker = _primary_world_family_in_text(cue_text)
        if family:
            return family, marker, "natural_context_cue"
    family, marker = _primary_world_family_in_text(natural_context)
    return (family, marker, "natural_context") if family else ("", "", "")


def _contains_any(text: Any, markers: Iterable[str]) -> bool:
    source = _clean(text)
    return any(_marker_present(source, marker) for marker in markers)


def _compatible_world_families(family: str) -> set[str]:
    if not family:
        return set()
    return {
        family,
        *_WORLD_COMPATIBILITY.get(family, ()),
        *(
            candidate
            for candidate, compatible in _WORLD_COMPATIBILITY.items()
            if family in compatible
        ),
    }


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
    subject_type: Any = "",
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
                "effective_satisfied": satisfied,
                "resolution": "explicit" if satisfied else "pending",
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
            natural_context,
        ]
    )
    explicit_hits = detect_world_families(scene_text)
    scene_only_hits = detect_world_families("，".join(groups.get("场景背景", [])))
    context_world_hits = detect_world_families(natural_context)
    negated_context_world_hits = detect_negated_world_families(natural_context)
    context_scene_attributes = detect_scene_attributes(natural_context)
    negated_context_scene_attributes = detect_negated_scene_attributes(natural_context)
    context_scene_attribute_constraints = _context_scene_attribute_constraints(natural_context)
    context_subject_cardinality = detect_subject_cardinality(natural_context)
    negated_context_subject_cardinality = detect_negated_subject_cardinality(natural_context)
    context_subject_cardinality_constraint = _context_subject_cardinality_constraint(natural_context)
    context_subject_presence_constraint = _context_subject_presence_constraint(
        natural_context,
        subject_type,
    )
    context_subject_orientation = _detect_subject_orientation(
        natural_context,
        negated=False,
        require_context_scope=True,
    )
    negated_context_subject_orientation = _detect_subject_orientation(
        natural_context,
        negated=True,
        require_context_scope=True,
    )
    context_subject_orientation_constraint = _context_subject_orientation_constraint(natural_context)
    context_subject_pose = detect_subject_pose(natural_context)
    negated_context_subject_pose = detect_negated_subject_pose(natural_context)
    context_subject_pose_constraint = _context_subject_pose_constraint(natural_context)
    context_shot_scale = detect_shot_scale(natural_context, require_context_scope=True)
    negated_context_shot_scale = detect_negated_shot_scale(natural_context, require_context_scope=True)
    context_shot_scale_constraint = _context_shot_scale_constraint(natural_context)
    context_camera_angle = detect_camera_angle(natural_context, require_context_scope=True)
    negated_context_camera_angle = detect_negated_camera_angle(natural_context, require_context_scope=True)
    context_camera_angle_constraint = _context_camera_angle_constraint(natural_context)
    context_light_temperature = detect_light_temperature(natural_context, require_context_scope=True)
    negated_context_light_temperature = detect_negated_light_temperature(
        natural_context,
        require_context_scope=True,
    )
    context_light_temperature_constraint = _context_light_temperature_constraint(natural_context)
    context_color_rendering = detect_color_rendering(natural_context)
    negated_context_color_rendering = detect_negated_color_rendering(natural_context)
    color_rendering_values = [
        value
        for group in ("画面风格", "光影氛围", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    color_rendering_constraint = _resolve_color_rendering_constraint(
        natural_context,
        color_rendering_values,
    )
    context_depth_of_field = detect_depth_of_field(natural_context)
    negated_context_depth_of_field = detect_negated_depth_of_field(natural_context)
    depth_of_field_values = [
        value
        for group in ("构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + list(custom)
    depth_of_field_constraint = _resolve_depth_of_field_constraint(
        natural_context,
        depth_of_field_values,
    )
    context_lighting_quality = detect_lighting_quality(natural_context)
    negated_context_lighting_quality = detect_negated_lighting_quality(natural_context)
    lighting_quality_values = [
        value
        for group in ("光影氛围", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    lighting_quality_constraint = _resolve_lighting_quality_constraint(
        natural_context,
        lighting_quality_values,
    )
    context_motion_rendering = detect_motion_rendering(natural_context)
    negated_context_motion_rendering = detect_negated_motion_rendering(natural_context)
    motion_rendering_values = [
        value
        for group in ("技术画质", "构图视角", "画面风格", "动作姿态", "光影氛围")
        for value in groups.get(group, [])
    ] + list(custom)
    motion_rendering_constraint = _resolve_motion_rendering_constraint(
        natural_context,
        motion_rendering_values,
    )
    context_camera_stability = detect_camera_stability(natural_context)
    negated_context_camera_stability = detect_negated_camera_stability(natural_context)
    camera_stability_values = [
        value
        for group in ("构图视角", "技术画质", "画面风格", "动作姿态")
        for value in groups.get(group, [])
    ] + list(custom)
    camera_stability_constraint = _resolve_camera_stability_constraint(
        natural_context,
        camera_stability_values,
    )
    context_focal_perspective = detect_focal_perspective(natural_context)
    negated_context_focal_perspective = detect_negated_focal_perspective(natural_context)
    focal_perspective_values = [
        value
        for group in ("构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + list(custom)
    focal_perspective_constraint = _resolve_focal_perspective_constraint(
        natural_context,
        focal_perspective_values,
    )
    context_key_light_direction = detect_key_light_direction(natural_context)
    negated_context_key_light_direction = detect_negated_key_light_direction(natural_context)
    key_light_direction_values = [
        value
        for group in ("光影氛围", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    key_light_direction_constraint = _resolve_key_light_direction_constraint(
        natural_context,
        key_light_direction_values,
    )
    primary_family, primary_world_evidence, primary_world_source = _resolve_primary_world_family(
        groups.get("场景背景", []),
        natural_context,
    )
    context_primary_family, context_primary_marker, context_primary_source = _resolve_primary_world_family(
        [],
        natural_context,
    )
    compatible_context_families = _compatible_world_families(context_primary_family)
    superseded_context_world_families = (
        [
            family
            for family in context_world_hits
            if family in _LOCATION_WORLD_FAMILIES and family not in compatible_context_families
        ]
        if context_primary_source == "natural_context_override"
        else []
    )
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
    allowed.difference_update(superseded_context_world_families)
    forbidden = [family for family in WORLD_FAMILY_MARKERS if family not in allowed]
    hard_anchors = {
        group: values
        for group, values in groups.items()
        if values and group in {"主体", "服装造型", "场景背景", "动作姿态", "道具世界观", "画面风格", "构图视角"}
    }
    coherence_issues: list[dict[str, Any]] = []
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
            scene_anchors = [
                {"group": "场景背景", "value": value}
                for value in groups.get("场景背景", [])
                if family in detect_world_families(value)
            ]
            conflicting_anchors = [
                {"group": group, "value": value}
                for group in ("道具世界观", "动作姿态", "光影氛围")
                for value in groups.get(group, [])
                if _contains_any(value, markers)
            ]
            coherence_issues.append(
                {
                    "kind": "scene_affordance_conflict",
                    "severity": "error",
                    "world_family": family,
                    "scene_anchors": scene_anchors,
                    "conflicting_anchors": conflicting_anchors,
                    "message": message,
                }
            )
    active_anchors = [
        {"group": group, "value": value}
        for group in ("场景背景", "道具世界观", "动作姿态", "光影氛围")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    attribute_anchors = [
        {"group": group, "value": value}
        for group in ("画面风格", "场景背景", "光影氛围")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_attribute_anchors: list[dict[str, Any]] = []
    for anchor in attribute_anchors:
        anchor_hits = detect_scene_attributes(anchor["value"])
        conflicts: list[dict[str, Any]] = []
        for axis, constraint in context_scene_attribute_constraints.items():
            actual_values = list(anchor_hits.get(axis, {}))
            required = _clean(constraint.get("required_value"))
            negated_values = set(constraint.get("negated_values", []) or [])
            conflicting_values = [
                value
                for value in actual_values
                if value in negated_values or (required and value != required)
            ]
            if conflicting_values:
                conflicts.append(
                    {
                        "axis": axis,
                        "axis_label": constraint["axis_label"],
                        "required_value": required,
                        "required_label": constraint["required_label"],
                        "actual_values": conflicting_values,
                        "actual_labels": [_SCENE_ATTRIBUTE_LABELS.get(value, value) for value in conflicting_values],
                    }
                )
        if conflicts:
            conflicting_attribute_anchors.append({**anchor, "attribute_conflicts": conflicts})
    if conflicting_attribute_anchors:
        constraint_summary = "、".join(
            (
                f"{constraint['axis_label']}={constraint['required_label']}"
                if constraint.get("required_value")
                else f"{constraint['axis_label']}排除{'/'.join(constraint['negated_labels'])}"
            )
            for constraint in context_scene_attribute_constraints.values()
        )
        coherence_issues.append(
            {
                "kind": "context_scene_attribute_conflict",
                "severity": "error",
                "constraints": deepcopy(context_scene_attribute_constraints),
                "conflicting_anchors": conflicting_attribute_anchors,
                "message": (
                    f"自然语言已明确场景属性“{constraint_summary}”，"
                    "但当前风格、场景、光影或补充标签仍包含相反的昼夜或天气状态。"
                ),
            }
        )
    cardinality_anchors = [
        {"group": group, "value": value}
        for group in ("主体", "画面风格", "动作姿态", "构图视角")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_cardinality_anchors: list[dict[str, Any]] = []
    if context_subject_cardinality_constraint:
        required_cardinality = _clean(context_subject_cardinality_constraint.get("required_value"))
        negated_cardinalities = set(context_subject_cardinality_constraint.get("negated_values", []) or [])
        for anchor in cardinality_anchors:
            anchor_hits = detect_subject_cardinality(anchor["value"])
            conflicting_values = [
                value
                for value in anchor_hits
                if value in negated_cardinalities or (required_cardinality and value != required_cardinality)
            ]
            if conflicting_values:
                conflicting_cardinality_anchors.append(
                    {
                        **anchor,
                        "actual_values": conflicting_values,
                        "actual_labels": [
                            _SUBJECT_CARDINALITY_LABELS.get(value, value) for value in conflicting_values
                        ],
                    }
                )
    if conflicting_cardinality_anchors:
        required_label = _clean(context_subject_cardinality_constraint.get("required_label"))
        negated_labels = list(context_subject_cardinality_constraint.get("negated_labels", []) or [])
        cardinality_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_subject_cardinality_conflict",
                "severity": "error",
                "constraint": deepcopy(context_subject_cardinality_constraint),
                "conflicting_anchors": conflicting_cardinality_anchors,
                "message": (
                    f"自然语言已明确人物数量“{cardinality_summary}”，"
                    "但当前主体、风格、动作、构图或补充标签仍包含相反的人数结构。"
                ),
            }
        )
    presence_anchors = [
        {"group": group, "value": value}
        for group, values in groups.items()
        for value in values
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_presence_anchors: list[dict[str, Any]] = []
    if context_subject_presence_constraint:
        forbidden_categories = set(
            context_subject_presence_constraint.get("forbidden_categories", []) or []
        )
        for anchor in presence_anchors:
            anchor_hits = _human_intrusion_anchor_hits(anchor)
            matched_categories = [
                category for category in anchor_hits if category in forbidden_categories
            ]
            if matched_categories:
                conflicting_presence_anchors.append(
                    {
                        **anchor,
                        "intrusion_categories": matched_categories,
                        "intrusion_labels": [
                            _HUMAN_SUBJECT_INTRUSION_LABELS.get(category, category)
                            for category in matched_categories
                        ],
                        "intrusion_markers": {
                            category: list(anchor_hits.get(category, []))
                            for category in matched_categories
                        },
                    }
                )
    if conflicting_presence_anchors:
        presence_label = _clean(context_subject_presence_constraint.get("required_label"))
        coherence_issues.append(
            {
                "kind": "context_subject_presence_conflict",
                "severity": "error",
                "constraint": deepcopy(context_subject_presence_constraint),
                "conflicting_anchors": conflicting_presence_anchors,
                "message": (
                    f"当前任务已明确“{presence_label}”，"
                    "但主体、服装、动作、构图或补充标签仍包含人物身份、肖像身体或人物造型。"
                ),
            }
        )
    orientation_anchors = [
        {"group": group, "value": value}
        for group in ("主体", "动作姿态", "构图视角")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_orientation_anchors: list[dict[str, Any]] = []
    if context_subject_orientation_constraint:
        required_orientation = _clean(context_subject_orientation_constraint.get("required_value"))
        negated_orientations = set(context_subject_orientation_constraint.get("negated_values", []) or [])
        for anchor in orientation_anchors:
            anchor_hits = detect_subject_orientation(anchor["value"])
            conflicting_values = [
                value
                for value in anchor_hits
                if value in negated_orientations or (required_orientation and value != required_orientation)
            ]
            if conflicting_values:
                conflicting_orientation_anchors.append(
                    {
                        **anchor,
                        "actual_values": conflicting_values,
                        "actual_labels": [
                            _SUBJECT_ORIENTATION_LABELS.get(value, value) for value in conflicting_values
                        ],
                    }
                )
    if conflicting_orientation_anchors:
        required_label = _clean(context_subject_orientation_constraint.get("required_label"))
        negated_labels = list(context_subject_orientation_constraint.get("negated_labels", []) or [])
        orientation_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_subject_orientation_conflict",
                "severity": "error",
                "constraint": deepcopy(context_subject_orientation_constraint),
                "conflicting_anchors": conflicting_orientation_anchors,
                "message": (
                    f"自然语言已明确主体朝向“{orientation_summary}”，"
                    "但当前主体、动作、构图或补充标签仍包含相反视图。"
                ),
            }
        )
    pose_anchors = [
        {"group": group, "value": value}
        for group in ("主体", "动作姿态", "构图视角")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_pose_anchors = _conflicting_exclusive_axis_anchors(
        pose_anchors,
        context_subject_pose_constraint,
        detect_subject_pose,
        _SUBJECT_POSE_LABELS,
    )
    if conflicting_pose_anchors:
        required_label = _clean(context_subject_pose_constraint.get("required_label"))
        negated_labels = list(context_subject_pose_constraint.get("negated_labels", []) or [])
        pose_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_subject_pose_conflict",
                "severity": "error",
                "constraint": deepcopy(context_subject_pose_constraint),
                "conflicting_anchors": conflicting_pose_anchors,
                "message": (
                    f"自然语言已明确主体姿态“{pose_summary}”，"
                    "但当前主体、动作、构图或补充标签仍包含相反姿态。"
                ),
            }
        )
    shot_scale_anchors = [
        {"group": group, "value": value}
        for group in ("构图视角", "动作姿态")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_shot_scale_anchors = _conflicting_exclusive_axis_anchors(
        shot_scale_anchors,
        context_shot_scale_constraint,
        detect_shot_scale,
        _SHOT_SCALE_LABELS,
    )
    if conflicting_shot_scale_anchors:
        required_label = _clean(context_shot_scale_constraint.get("required_label"))
        negated_labels = list(context_shot_scale_constraint.get("negated_labels", []) or [])
        shot_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_shot_scale_conflict",
                "severity": "error",
                "constraint": deepcopy(context_shot_scale_constraint),
                "conflicting_anchors": conflicting_shot_scale_anchors,
                "message": (
                    f"自然语言已明确景别“{shot_summary}”，"
                    "但当前构图、动作或补充标签仍包含相反景别。"
                ),
            }
        )
    camera_angle_anchors = [
        {"group": group, "value": value}
        for group in ("构图视角", "动作姿态")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_camera_angle_anchors = _conflicting_exclusive_axis_anchors(
        camera_angle_anchors,
        context_camera_angle_constraint,
        detect_camera_angle,
        _CAMERA_ANGLE_LABELS,
    )
    if conflicting_camera_angle_anchors:
        required_label = _clean(context_camera_angle_constraint.get("required_label"))
        negated_labels = list(context_camera_angle_constraint.get("negated_labels", []) or [])
        angle_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_camera_angle_conflict",
                "severity": "error",
                "constraint": deepcopy(context_camera_angle_constraint),
                "conflicting_anchors": conflicting_camera_angle_anchors,
                "message": (
                    f"自然语言已明确机位“{angle_summary}”，"
                    "但当前构图、动作或补充标签仍包含相反拍摄角度。"
                ),
            }
        )
    light_temperature_anchors = [
        {"group": group, "value": value}
        for group in ("光影氛围", "画面风格", "场景背景", "技术画质")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_light_temperature_anchors = _conflicting_exclusive_axis_anchors(
        light_temperature_anchors,
        context_light_temperature_constraint,
        detect_light_temperature,
        _LIGHT_TEMPERATURE_LABELS,
    )
    if conflicting_light_temperature_anchors:
        required_label = _clean(context_light_temperature_constraint.get("required_label"))
        negated_labels = list(context_light_temperature_constraint.get("negated_labels", []) or [])
        temperature_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_light_temperature_conflict",
                "severity": "error",
                "constraint": deepcopy(context_light_temperature_constraint),
                "conflicting_anchors": conflicting_light_temperature_anchors,
                "message": (
                    f"自然语言已明确整体色温“{temperature_summary}”，"
                    "但当前光影、风格、场景、画质或补充标签仍包含相反色温。"
                ),
            }
        )
    color_rendering_anchors = [
        {"group": group, "value": value}
        for group in ("画面风格", "光影氛围", "技术画质")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_color_rendering_anchors = _conflicting_exclusive_axis_anchors(
        color_rendering_anchors,
        color_rendering_constraint,
        detect_color_rendering,
        _COLOR_RENDERING_LABELS,
    )
    if conflicting_color_rendering_anchors:
        required_label = _clean(color_rendering_constraint.get("required_label"))
        negated_labels = list(color_rendering_constraint.get("negated_labels", []) or [])
        rendering_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_color_rendering_conflict",
                "severity": "error",
                "constraint": deepcopy(color_rendering_constraint),
                "conflicting_anchors": conflicting_color_rendering_anchors,
                "message": (
                    f"自然语言已明确颜色呈现“{rendering_summary}”，"
                    "但当前风格、光影、画质或补充标签仍包含相反的黑白或全彩模式。"
                ),
            }
        )
    depth_of_field_anchors = [
        {"group": group, "value": value}
        for group in ("构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_depth_of_field_anchors = _conflicting_exclusive_axis_anchors(
        depth_of_field_anchors,
        depth_of_field_constraint,
        detect_depth_of_field,
        _DEPTH_OF_FIELD_LABELS,
    )
    if conflicting_depth_of_field_anchors:
        required_label = _clean(depth_of_field_constraint.get("required_label"))
        negated_labels = list(depth_of_field_constraint.get("negated_labels", []) or [])
        depth_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_depth_of_field_conflict",
                "severity": "error",
                "constraint": deepcopy(depth_of_field_constraint),
                "conflicting_anchors": conflicting_depth_of_field_anchors,
                "message": (
                    f"自然语言已明确景深“{depth_summary}”，"
                    "但当前构图、画质、风格或补充标签仍包含相反景深。"
                ),
            }
        )
    lighting_quality_anchors = [
        {"group": group, "value": value}
        for group in ("光影氛围", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_lighting_quality_anchors = _conflicting_exclusive_axis_anchors(
        lighting_quality_anchors,
        lighting_quality_constraint,
        detect_lighting_quality,
        _LIGHTING_QUALITY_LABELS,
    )
    if conflicting_lighting_quality_anchors:
        required_label = _clean(lighting_quality_constraint.get("required_label"))
        negated_labels = list(lighting_quality_constraint.get("negated_labels", []) or [])
        lighting_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_lighting_quality_conflict",
                "severity": "error",
                "constraint": deepcopy(lighting_quality_constraint),
                "conflicting_anchors": conflicting_lighting_quality_anchors,
                "message": (
                    f"自然语言已明确光质“{lighting_summary}”，"
                    "但当前光影、风格、画质或补充标签仍包含相反硬度的光线。"
                ),
            }
        )
    motion_rendering_anchors = [
        {"group": group, "value": value}
        for group in ("技术画质", "构图视角", "画面风格", "动作姿态", "光影氛围")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_motion_rendering_anchors = _conflicting_exclusive_axis_anchors(
        motion_rendering_anchors,
        motion_rendering_constraint,
        detect_motion_rendering,
        _MOTION_RENDERING_LABELS,
    )
    if conflicting_motion_rendering_anchors:
        required_label = _clean(motion_rendering_constraint.get("required_label"))
        negated_labels = list(motion_rendering_constraint.get("negated_labels", []) or [])
        motion_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_motion_rendering_conflict",
                "severity": "error",
                "constraint": deepcopy(motion_rendering_constraint),
                "conflicting_anchors": conflicting_motion_rendering_anchors,
                "message": (
                    f"自然语言已明确运动呈现“{motion_summary}”，"
                    "但当前动作、构图、风格、光影、画质或补充标签仍包含相反快门表现。"
                ),
            }
        )
    camera_stability_anchors = [
        {"group": group, "value": value}
        for group in ("构图视角", "技术画质", "画面风格", "动作姿态")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_camera_stability_anchors = _conflicting_exclusive_axis_anchors(
        camera_stability_anchors,
        camera_stability_constraint,
        detect_camera_stability,
        _CAMERA_STABILITY_LABELS,
    )
    if conflicting_camera_stability_anchors:
        required_label = _clean(camera_stability_constraint.get("required_label"))
        negated_labels = list(camera_stability_constraint.get("negated_labels", []) or [])
        stability_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_camera_stability_conflict",
                "severity": "error",
                "constraint": deepcopy(camera_stability_constraint),
                "conflicting_anchors": conflicting_camera_stability_anchors,
                "message": (
                    f"自然语言已明确镜头稳定性“{stability_summary}”，"
                    "但当前构图、画质、风格、动作或补充标签仍包含相反镜头状态。"
                ),
            }
        )
    focal_perspective_anchors = [
        {"group": group, "value": value}
        for group in ("构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_focal_perspective_anchors = _conflicting_exclusive_axis_anchors(
        focal_perspective_anchors,
        focal_perspective_constraint,
        detect_focal_perspective,
        _FOCAL_PERSPECTIVE_LABELS,
    )
    if conflicting_focal_perspective_anchors:
        required_label = _clean(focal_perspective_constraint.get("required_label"))
        negated_labels = list(focal_perspective_constraint.get("negated_labels", []) or [])
        focal_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_focal_perspective_conflict",
                "severity": "error",
                "constraint": deepcopy(focal_perspective_constraint),
                "conflicting_anchors": conflicting_focal_perspective_anchors,
                "message": (
                    f"自然语言已明确焦段透视“{focal_summary}”，"
                    "但当前构图、画质、风格或补充标签仍包含相反空间透视。"
                ),
            }
        )
    key_light_direction_anchors = [
        {"group": group, "value": value}
        for group in ("光影氛围", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_key_light_direction_anchors = _conflicting_exclusive_axis_anchors(
        key_light_direction_anchors,
        key_light_direction_constraint,
        detect_key_light_direction,
        _KEY_LIGHT_DIRECTION_LABELS,
    )
    if conflicting_key_light_direction_anchors:
        required_label = _clean(key_light_direction_constraint.get("required_label"))
        negated_labels = list(key_light_direction_constraint.get("negated_labels", []) or [])
        direction_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_key_light_direction_conflict",
                "severity": "error",
                "constraint": deepcopy(key_light_direction_constraint),
                "conflicting_anchors": conflicting_key_light_direction_anchors,
                "message": (
                    f"自然语言已明确主光方向“{direction_summary}”，"
                    "但当前光影、风格、画质或补充标签仍包含相反灯位。"
                ),
            }
        )
    context_veto_anchor_keys: set[tuple[str, str]] = set()
    for family, negated_markers in negated_context_world_hits.items():
        family_wide_veto = bool(context_primary_family and context_primary_family != family)
        conflicting_anchors = [
            anchor
            for anchor in active_anchors
            if (
                (family_wide_veto and family in detect_world_families(anchor["value"]))
                or _contains_any(anchor["value"], negated_markers)
            )
        ]
        if not conflicting_anchors:
            continue
        context_veto_anchor_keys.update(
            (_clean(anchor["group"]), _clean(anchor["value"]).casefold())
            for anchor in conflicting_anchors
        )
        coherence_issues.append(
            {
                "kind": "context_world_conflict",
                "severity": "error",
                "world_family": family,
                "negated_markers": list(negated_markers),
                "context_primary_world_family": context_primary_family,
                "conflicting_anchors": conflicting_anchors,
                "message": (
                    f"自然语言已排除世界族“{family}”中的 {'、'.join(negated_markers[:3])}，"
                    "但当前标签仍包含对应元素。"
                ),
            }
        )
    if context_primary_family and context_primary_source in {
        "natural_context_cue",
        "natural_context_override",
    }:
        conflicting_scene_anchors = []
        for value in groups.get("场景背景", []):
            anchor_key = ("场景背景", _clean(value).casefold())
            if anchor_key in context_veto_anchor_keys:
                continue
            location_hits = {
                family
                for family in detect_world_families(value)
                if family in _LOCATION_WORLD_FAMILIES
            }
            if location_hits and location_hits.isdisjoint(compatible_context_families):
                conflicting_scene_anchors.append({"group": "场景背景", "value": value})
        if conflicting_scene_anchors:
            coherence_issues.append(
                {
                    "kind": "context_primary_scene_conflict",
                    "severity": "error",
                    "world_family": context_primary_family,
                    "context_primary_marker": context_primary_marker,
                    "context_primary_source": context_primary_source,
                    "conflicting_anchors": conflicting_scene_anchors,
                    "message": (
                        f"自然语言已明确主场景为“{context_primary_marker}”，"
                        "但当前标签仍包含不兼容的其他主场景。"
                    ),
                }
            )
        conflicting_context_anchors = []
        for anchor in active_anchors:
            if anchor["group"] == "场景背景":
                continue
            anchor_key = (_clean(anchor["group"]), _clean(anchor["value"]).casefold())
            if anchor_key in context_veto_anchor_keys:
                continue
            world_hits = {
                family
                for family in detect_world_families(anchor["value"])
                if family in _LOCATION_WORLD_FAMILIES
            }
            if world_hits and world_hits.isdisjoint(compatible_context_families):
                conflicting_context_anchors.append(dict(anchor))
        if conflicting_context_anchors:
            coherence_issues.append(
                {
                    "kind": "context_primary_anchor_conflict",
                    "severity": "error",
                    "world_family": context_primary_family,
                    "context_primary_marker": context_primary_marker,
                    "context_primary_source": context_primary_source,
                    "conflicting_anchors": conflicting_context_anchors,
                    "message": (
                        f"自然语言已明确主场景为“{context_primary_marker}”，"
                        "但动作、道具、光影或补充标签仍包含不兼容的跨世界元素。"
                    ),
                }
            )
    for requirement in inferred_requirements:
        if not requirement.get("satisfied"):
            coherence_issues.append(
                {
                    "kind": "implicit_prop_anchor",
                    "severity": "info",
                    "target": requirement["target"][0],
                    "message": f"动作已隐含道具“{requirement['target'][0]}”，生成时必须保持该动作-道具关系。",
                }
            )
    return {
        "nodes": groups,
        "custom_context": custom,
        "natural_context_present": bool(natural_context),
        "natural_context_world_families": list(context_world_hits),
        "negated_context_world_families": {
            family: list(markers) for family, markers in negated_context_world_hits.items()
        },
        "natural_context_scene_attributes": context_scene_attributes,
        "negated_context_scene_attributes": negated_context_scene_attributes,
        "context_scene_attribute_constraints": context_scene_attribute_constraints,
        "natural_context_subject_cardinality": context_subject_cardinality,
        "negated_context_subject_cardinality": negated_context_subject_cardinality,
        "context_subject_cardinality_constraint": context_subject_cardinality_constraint,
        "context_subject_presence_constraint": context_subject_presence_constraint,
        "natural_context_subject_orientation": context_subject_orientation,
        "negated_context_subject_orientation": negated_context_subject_orientation,
        "context_subject_orientation_constraint": context_subject_orientation_constraint,
        "natural_context_subject_pose": context_subject_pose,
        "negated_context_subject_pose": negated_context_subject_pose,
        "context_subject_pose_constraint": context_subject_pose_constraint,
        "natural_context_shot_scale": context_shot_scale,
        "negated_context_shot_scale": negated_context_shot_scale,
        "context_shot_scale_constraint": context_shot_scale_constraint,
        "natural_context_camera_angle": context_camera_angle,
        "negated_context_camera_angle": negated_context_camera_angle,
        "context_camera_angle_constraint": context_camera_angle_constraint,
        "natural_context_light_temperature": context_light_temperature,
        "negated_context_light_temperature": negated_context_light_temperature,
        "context_light_temperature_constraint": context_light_temperature_constraint,
        "natural_context_color_rendering": context_color_rendering,
        "negated_context_color_rendering": negated_context_color_rendering,
        "color_rendering_constraint": color_rendering_constraint,
        "natural_context_depth_of_field": context_depth_of_field,
        "negated_context_depth_of_field": negated_context_depth_of_field,
        "depth_of_field_constraint": depth_of_field_constraint,
        "natural_context_lighting_quality": context_lighting_quality,
        "negated_context_lighting_quality": negated_context_lighting_quality,
        "lighting_quality_constraint": lighting_quality_constraint,
        "natural_context_motion_rendering": context_motion_rendering,
        "negated_context_motion_rendering": negated_context_motion_rendering,
        "motion_rendering_constraint": motion_rendering_constraint,
        "natural_context_camera_stability": context_camera_stability,
        "negated_context_camera_stability": negated_context_camera_stability,
        "camera_stability_constraint": camera_stability_constraint,
        "natural_context_focal_perspective": context_focal_perspective,
        "negated_context_focal_perspective": negated_context_focal_perspective,
        "focal_perspective_constraint": focal_perspective_constraint,
        "natural_context_key_light_direction": context_key_light_direction,
        "negated_context_key_light_direction": negated_context_key_light_direction,
        "key_light_direction_constraint": key_light_direction_constraint,
        "context_primary_world_family": context_primary_family,
        "context_primary_world_evidence": context_primary_marker,
        "context_primary_world_source": context_primary_source,
        "superseded_context_world_families": superseded_context_world_families,
        "relations": relations,
        "hard_anchors": hard_anchors,
        "inferred_requirements": inferred_requirements,
        "coherence_issues": coherence_issues,
        "resolved_coherence_issues": [],
        "resolved_issue_count": 0,
        "coherence_status": "conflict" if any(item["severity"] == "error" for item in coherence_issues) else ("review" if coherence_issues else "coherent"),
        "primary_world_family": primary_family,
        "primary_world_evidence": primary_world_evidence,
        "primary_world_evidence_source": primary_world_source,
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
    has_unresolved_error = any(
        isinstance(item, dict) and item.get("severity") == "error"
        for item in coherence_issues
    )
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
    elif has_unresolved_error:
        mode = "skill_only_guarded"
        reason = "场景关系图仍有强语义冲突；为避免模型擅自改写显式选择，本次跳过后置模型并保留 Skill 成品。"
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
        "video_mode": (
            "skill_only_guarded"
            if mode == "skill_only_guarded"
            else ("incremental_storyboard_blend" if mode != "skill_only" else "skill_only")
        ),
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


def apply_relation_hint_resolution(scene_graph: Any, relation_hints: Any) -> dict[str, Any]:
    if not isinstance(scene_graph, dict):
        return {}
    resolved_graph = deepcopy(scene_graph)
    hint_groups = relation_hints if isinstance(relation_hints, dict) else {}
    hinted_props = {
        value.casefold()
        for value in _unique(hint_groups.get("道具世界观", []), 8)
    }
    resolved_targets: set[str] = set()
    requirements: list[dict[str, Any]] = []
    for raw_requirement in list(resolved_graph.get("inferred_requirements", []) or []):
        if not isinstance(raw_requirement, dict):
            continue
        requirement = dict(raw_requirement)
        targets = _unique(requirement.get("target", []), 4)
        resolved_by_hint = bool(
            not requirement.get("satisfied")
            and any(target.casefold() in hinted_props for target in targets)
        )
        requirement["resolved_by_hint"] = resolved_by_hint
        requirement["effective_satisfied"] = bool(requirement.get("satisfied") or resolved_by_hint)
        requirement["resolution"] = (
            "explicit"
            if requirement.get("satisfied")
            else ("relation_hint" if resolved_by_hint else "pending")
        )
        if resolved_by_hint:
            resolved_targets.update(targets)
        requirements.append(requirement)
    resolved_graph["inferred_requirements"] = requirements

    unresolved_issues: list[dict[str, Any]] = []
    resolved_issues = [
        dict(item)
        for item in list(resolved_graph.get("resolved_coherence_issues", []) or [])
        if isinstance(item, dict)
    ]
    for raw_issue in list(resolved_graph.get("coherence_issues", []) or []):
        if not isinstance(raw_issue, dict):
            continue
        issue = dict(raw_issue)
        target = _clean(issue.get("target"))
        if issue.get("kind") == "implicit_prop_anchor" and target in resolved_targets:
            issue["resolved"] = True
            issue["resolution"] = "relation_hint"
            issue["message"] = f"动作隐含道具“{target}”已由关系软补全加入本次 Skill 成品。"
            resolved_issues.append(issue)
        else:
            unresolved_issues.append(issue)
    resolved_graph["coherence_issues"] = unresolved_issues
    resolved_graph["resolved_coherence_issues"] = resolved_issues
    resolved_graph["resolved_issue_count"] = len(resolved_issues)
    resolved_graph["coherence_status"] = (
        "conflict"
        if any(item.get("severity") == "error" for item in unresolved_issues)
        else ("review" if unresolved_issues else "coherent")
    )
    resolved_graph["resolution_status"] = (
        "partially_resolved"
        if resolved_issues and unresolved_issues
        else ("resolved" if resolved_issues else "unchanged")
    )
    return resolved_graph


def resolve_soft_scene_conflicts(
    selected: OrderedDict[str, list[str]] | dict[str, list[str]],
    custom_tags: Iterable[Any],
    scene_graph: Any,
    *,
    soft_tags: Iterable[Any] = (),
    protected_tags: Iterable[Any] = (),
) -> tuple[OrderedDict[str, list[str]], list[str], dict[str, Any]]:
    """Remove only proven low-priority automatic anchors in a hard scene conflict."""
    next_selected = OrderedDict((group, list(values or [])) for group, values in selected.items())
    next_custom = _unique(custom_tags, 64)
    soft_keys = {value.casefold() for value in _unique(soft_tags, 128)}
    protected_keys = {value.casefold() for value in _unique(protected_tags, 128)}
    removed: list[dict[str, str]] = []
    resolved_issues: list[dict[str, Any]] = []

    def removable(anchor: dict[str, Any]) -> bool:
        key = _clean(anchor.get("value")).casefold()
        return bool(key and key in soft_keys and key not in protected_keys)

    def remove_anchors(anchors: list[dict[str, Any]], *, side: str, issue: dict[str, Any]) -> None:
        removed_for_issue: list[dict[str, Any]] = []
        for anchor in anchors:
            group = _clean(anchor.get("group"))
            value = _clean(anchor.get("value"))
            if not group or not value:
                continue
            if group == "自定义补充":
                before = len(next_custom)
                next_custom[:] = [item for item in next_custom if _clean(item).casefold() != value.casefold()]
                changed = len(next_custom) != before
            else:
                values = next_selected.get(group, [])
                next_values = [item for item in values if _clean(item).casefold() != value.casefold()]
                changed = len(next_values) != len(values)
                next_selected[group] = next_values
            if not changed:
                continue
            removed.append({"group": group, "value": value, "side": side})
            removed_for_issue.append(dict(anchor))
        if not removed_for_issue:
            return
        resolved = dict(issue)
        resolved["resolved"] = True
        resolved["resolution"] = "soft_tag_removal"
        resolved["removed_side"] = side
        resolved["removed_anchors"] = removed_for_issue
        resolved["message"] = f"{_clean(issue.get('message'))}；已仅移除低优先级自动派生侧标签。"
        resolved_issues.append(resolved)

    if isinstance(scene_graph, dict):
        for raw_issue in list(scene_graph.get("coherence_issues", []) or []):
            if not isinstance(raw_issue, dict):
                continue
            issue = dict(raw_issue)
            if issue.get("kind") in {
                "context_world_conflict",
                "context_primary_scene_conflict",
                "context_primary_anchor_conflict",
                "context_scene_attribute_conflict",
                "context_subject_cardinality_conflict",
                "context_subject_presence_conflict",
                "context_subject_orientation_conflict",
                "context_subject_pose_conflict",
                "context_shot_scale_conflict",
                "context_camera_angle_conflict",
                "context_light_temperature_conflict",
                "context_color_rendering_conflict",
                "context_depth_of_field_conflict",
                "context_lighting_quality_conflict",
                "context_motion_rendering_conflict",
                "context_camera_stability_conflict",
                "context_focal_perspective_conflict",
                "context_key_light_direction_conflict",
            }:
                conflict_anchors = [
                    dict(item) for item in issue.get("conflicting_anchors", []) if isinstance(item, dict)
                ]
                if conflict_anchors and all(removable(item) for item in conflict_anchors):
                    side = {
                        "context_world_conflict": "context_veto",
                        "context_primary_scene_conflict": "context_primary_scene",
                        "context_primary_anchor_conflict": "context_primary_anchor",
                        "context_scene_attribute_conflict": "context_scene_attribute",
                        "context_subject_cardinality_conflict": "context_subject_cardinality",
                        "context_subject_presence_conflict": "context_subject_presence",
                        "context_subject_orientation_conflict": "context_subject_orientation",
                        "context_subject_pose_conflict": "context_subject_pose",
                        "context_shot_scale_conflict": "context_shot_scale",
                        "context_camera_angle_conflict": "context_camera_angle",
                        "context_light_temperature_conflict": "context_light_temperature",
                        "context_color_rendering_conflict": "context_color_rendering",
                        "context_depth_of_field_conflict": "context_depth_of_field",
                        "context_lighting_quality_conflict": "context_lighting_quality",
                        "context_motion_rendering_conflict": "context_motion_rendering",
                        "context_camera_stability_conflict": "context_camera_stability",
                        "context_focal_perspective_conflict": "context_focal_perspective",
                        "context_key_light_direction_conflict": "context_key_light_direction",
                    }[issue["kind"]]
                    remove_anchors(conflict_anchors, side=side, issue=issue)
                continue
            if issue.get("kind") != "scene_affordance_conflict":
                continue
            scene_anchors = [dict(item) for item in issue.get("scene_anchors", []) if isinstance(item, dict)]
            conflict_anchors = [dict(item) for item in issue.get("conflicting_anchors", []) if isinstance(item, dict)]
            can_remove_scene = bool(scene_anchors) and all(removable(item) for item in scene_anchors)
            can_remove_conflict = bool(conflict_anchors) and all(removable(item) for item in conflict_anchors)
            if can_remove_conflict:
                remove_anchors(conflict_anchors, side="conflicting_affordance", issue=issue)
            elif can_remove_scene:
                remove_anchors(scene_anchors, side="scene", issue=issue)

    report = {
        "applied": bool(removed),
        "removed_count": len(removed),
        "removed": removed,
        "resolved_issue_count": len(resolved_issues),
        "resolved_issues": resolved_issues,
        "policy": "provenance_soft_tags_only",
        "legacy_policy": "soft_tags_only",
    }
    return next_selected, next_custom, report


def classify_repair_reason(reason: Any) -> dict[str, str]:
    text = _clean(reason)
    folded = text.casefold()
    rules = (
        ("missing_anchor", ("缺少", "锚点"), "只补回缺失锚点，并保持其与主体、动作和场景的原有关联。"),
        ("world_conflict", ("世界族",), "只删除越界世界族及其附属物件，再用当前场景已有材质或环境反馈补足语句。"),
        ("scene_conflict", ("冲突场景",), "只移除错误场景，所有动作、道具和光线必须回到当前唯一主场景。"),
        ("scene_attribute", ("场景属性",), "只移除与用户昼夜或天气要求相反的光影和环境状态，不改变主体、动作与剧情顺序。"),
        ("subject_cardinality", ("人物数量",), "只修正人物数量与站位，不改变已有角色身份、服装、动作、场景或镜头顺序。"),
        ("subject_presence", ("主体存在性",), "只移除无人或非人物任务中新增加的人物身份、肖像身体与人物造型，不改变非人物主体、场景、材质或剧情顺序。"),
        ("subject_orientation", ("主体朝向",), "只修正主体正面、侧面或背面的朝向，不改变人物数量、身份、动作、场景或景别。"),
        ("subject_pose", ("主体姿态",), "只修正站、坐、跪、躺或蹲的主体姿态，不改变人物身份、服装、场景、道具或景别。"),
        ("shot_scale", ("景别",), "只修正特写、半身、全身或远景的取景范围，不改变人物身份、姿态、服装、场景或剧情顺序。"),
        ("camera_angle", ("机位",), "只修正低角度、平视、高角度或顶视机位，不改变人物身份、姿态、景别、场景或剧情顺序。"),
        ("light_temperature", ("整体色温",), "只修正与冷色、暖色或中性色温主线相反的灯光与调色，不改变主体、场景、动作、材质或剧情顺序。"),
        ("color_rendering", ("颜色呈现",), "只修正黑白、单色或全彩呈现冲突，不改变主体、场景、动作、光影结构或剧情顺序。"),
        ("depth_of_field", ("景深",), "只修正浅景深、背景虚化或深景深冲突，不改变景别、机位、主体、场景或剧情顺序。"),
        ("lighting_quality", ("光质",), "只修正硬光、柔光或漫射光冲突，不改变色温、主光方向、主体、场景或剧情顺序。"),
        ("motion_rendering", ("运动呈现",), "只修正高速快门凝固、运动模糊或慢门拖影冲突，不改变动作内容、主体、场景或剧情顺序。"),
        ("camera_stability", ("镜头稳定性",), "只修正稳定固定机位与手持晃动镜头冲突，不改变机位角度、景别、动作、主体、场景或剧情顺序。"),
        ("focal_perspective", ("焦段透视",), "只修正广角空间延展与长焦空间压缩冲突，不改变景别、机位、主体、动作、场景或剧情顺序。"),
        ("key_light_direction", ("主光方向",), "只修正正面、侧向、背后或顶部主光冲突，不改变光质、色温、主体、场景、材质或剧情顺序。"),
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
    graph_subject_type = (
        "非人物主体"
        if _clean(task_intent.get("task_type")) == "non_person_visual_story"
        else _clean(task_intent.get("subject_type"))
    )
    scene_graph = build_scene_relationship_graph(
        selected,
        custom_tags,
        context_text=context_text,
        subject_type=graph_subject_type,
    )
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
    original_hits = detect_world_families(original)
    candidate_hits = detect_world_families(candidate)
    for family in WORLD_FAMILY_MARKERS:
        if family not in forbidden or family not in candidate_hits or family in original_hits:
            continue
        marker = candidate_hits[family][0]
        return f"模型响应越过场景关系图：引入未获允许的世界族“{family}”元素“{marker}”。"
    presence_constraint = dict(scene_graph.get("context_subject_presence_constraint", {}) or {})
    if presence_constraint:
        forbidden_categories = set(presence_constraint.get("forbidden_categories", []) or [])
        introduced = introduced_human_subject_intrusions(original, candidate)
        for category, markers in introduced.items():
            if category not in forbidden_categories:
                continue
            expected = _clean(presence_constraint.get("required_label")) or "非人物画面"
            category_label = _HUMAN_SUBJECT_INTRUSION_LABELS.get(category, category)
            return (
                f"模型响应越过主体存在性约束：当前要求“{expected}”，"
                f"却新增了{category_label}“{markers[0]}”。"
            )
    constraints = dict(scene_graph.get("context_scene_attribute_constraints", {}) or {})
    if constraints:
        original_attributes = detect_scene_attributes(original)
        candidate_attributes = detect_scene_attributes(candidate)
        for axis, constraint in constraints.items():
            if not isinstance(constraint, dict):
                continue
            required = _clean(constraint.get("required_value"))
            negated_values = set(constraint.get("negated_values", []) or [])
            original_values = set(original_attributes.get(axis, {}))
            for value, markers in candidate_attributes.get(axis, {}).items():
                if value in original_values:
                    continue
                if value in negated_values or (required and value != required):
                    marker = markers[0]
                    axis_label = _clean(constraint.get("axis_label")) or axis
                    expected = _clean(constraint.get("required_label")) or "排除状态"
                    return (
                        f"模型响应越过场景属性约束：{axis_label}要求“{expected}”，"
                        f"却新增了“{marker}”。"
                    )
    cardinality_constraint = dict(scene_graph.get("context_subject_cardinality_constraint", {}) or {})
    if cardinality_constraint:
        required = _clean(cardinality_constraint.get("required_value"))
        negated_values = set(cardinality_constraint.get("negated_values", []) or [])
        original_cardinality = set(detect_subject_cardinality(original))
        candidate_cardinality = detect_subject_cardinality(candidate)
        for value, markers in candidate_cardinality.items():
            if value in original_cardinality:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(cardinality_constraint.get("required_label")) or "排除人数"
                return (
                    f"模型响应越过人物数量约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    orientation_constraint = dict(scene_graph.get("context_subject_orientation_constraint", {}) or {})
    if orientation_constraint:
        required = _clean(orientation_constraint.get("required_value"))
        negated_values = set(orientation_constraint.get("negated_values", []) or [])
        original_orientation = set(detect_subject_orientation(original))
        candidate_orientation = detect_subject_orientation(candidate)
        for value, markers in candidate_orientation.items():
            if value in original_orientation:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(orientation_constraint.get("required_label")) or "排除朝向"
                return (
                    f"模型响应越过主体朝向约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    pose_constraint = dict(scene_graph.get("context_subject_pose_constraint", {}) or {})
    if pose_constraint:
        required = _clean(pose_constraint.get("required_value"))
        negated_values = set(pose_constraint.get("negated_values", []) or [])
        original_pose = set(detect_subject_pose(original))
        candidate_pose = detect_subject_pose(candidate)
        for value, markers in candidate_pose.items():
            if value in original_pose:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(pose_constraint.get("required_label")) or "排除姿态"
                return (
                    f"模型响应越过主体姿态约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    shot_scale_constraint = dict(scene_graph.get("context_shot_scale_constraint", {}) or {})
    if shot_scale_constraint:
        required = _clean(shot_scale_constraint.get("required_value"))
        negated_values = set(shot_scale_constraint.get("negated_values", []) or [])
        original_shot_scale = set(detect_shot_scale(original, require_context_scope=True))
        candidate_shot_scale = detect_shot_scale(candidate, require_context_scope=True)
        for value, markers in candidate_shot_scale.items():
            if value in original_shot_scale:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(shot_scale_constraint.get("required_label")) or "排除景别"
                return (
                    f"模型响应越过景别约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    camera_angle_constraint = dict(scene_graph.get("context_camera_angle_constraint", {}) or {})
    if camera_angle_constraint:
        required = _clean(camera_angle_constraint.get("required_value"))
        negated_values = set(camera_angle_constraint.get("negated_values", []) or [])
        original_camera_angle = set(detect_camera_angle(original, require_context_scope=True))
        candidate_camera_angle = detect_camera_angle(candidate, require_context_scope=True)
        for value, markers in candidate_camera_angle.items():
            if value in original_camera_angle:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(camera_angle_constraint.get("required_label")) or "排除机位"
                return (
                    f"模型响应越过机位约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    light_temperature_constraint = dict(
        scene_graph.get("context_light_temperature_constraint", {}) or {}
    )
    if light_temperature_constraint:
        required = _clean(light_temperature_constraint.get("required_value"))
        negated_values = set(light_temperature_constraint.get("negated_values", []) or [])
        original_temperature = set(detect_light_temperature(original, require_context_scope=True))
        candidate_temperature = detect_light_temperature(candidate, require_context_scope=True)
        for value, markers in candidate_temperature.items():
            if value in original_temperature:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(light_temperature_constraint.get("required_label")) or "排除色温"
                return (
                    f"模型响应越过整体色温约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    color_rendering_constraint = dict(scene_graph.get("color_rendering_constraint", {}) or {})
    if color_rendering_constraint:
        required = _clean(color_rendering_constraint.get("required_value"))
        negated_values = set(color_rendering_constraint.get("negated_values", []) or [])
        original_rendering = set(detect_color_rendering(original))
        candidate_rendering = detect_color_rendering(candidate)
        for value, markers in candidate_rendering.items():
            if value in original_rendering:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(color_rendering_constraint.get("required_label")) or "排除颜色模式"
                return (
                    f"模型响应越过颜色呈现约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    depth_of_field_constraint = dict(scene_graph.get("depth_of_field_constraint", {}) or {})
    if depth_of_field_constraint:
        required = _clean(depth_of_field_constraint.get("required_value"))
        negated_values = set(depth_of_field_constraint.get("negated_values", []) or [])
        original_depth = set(detect_depth_of_field(original))
        candidate_depth = detect_depth_of_field(candidate)
        for value, markers in candidate_depth.items():
            if value in original_depth:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(depth_of_field_constraint.get("required_label")) or "排除景深"
                return (
                    f"模型响应越过景深约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    lighting_quality_constraint = dict(scene_graph.get("lighting_quality_constraint", {}) or {})
    if lighting_quality_constraint:
        required = _clean(lighting_quality_constraint.get("required_value"))
        negated_values = set(lighting_quality_constraint.get("negated_values", []) or [])
        original_quality = set(detect_lighting_quality(original))
        candidate_quality = detect_lighting_quality(candidate)
        for value, markers in candidate_quality.items():
            if value in original_quality:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(lighting_quality_constraint.get("required_label")) or "排除光质"
                return (
                    f"模型响应越过光质约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    motion_rendering_constraint = dict(scene_graph.get("motion_rendering_constraint", {}) or {})
    if motion_rendering_constraint:
        required = _clean(motion_rendering_constraint.get("required_value"))
        negated_values = set(motion_rendering_constraint.get("negated_values", []) or [])
        original_motion = set(detect_motion_rendering(original))
        candidate_motion = detect_motion_rendering(candidate)
        for value, markers in candidate_motion.items():
            if value in original_motion:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(motion_rendering_constraint.get("required_label")) or "排除运动呈现"
                return (
                    f"模型响应越过运动呈现约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    camera_stability_constraint = dict(scene_graph.get("camera_stability_constraint", {}) or {})
    if camera_stability_constraint:
        required = _clean(camera_stability_constraint.get("required_value"))
        negated_values = set(camera_stability_constraint.get("negated_values", []) or [])
        original_stability = set(detect_camera_stability(original))
        candidate_stability = detect_camera_stability(candidate)
        for value, markers in candidate_stability.items():
            if value in original_stability:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(camera_stability_constraint.get("required_label")) or "排除镜头状态"
                return (
                    f"模型响应越过镜头稳定性约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    focal_perspective_constraint = dict(scene_graph.get("focal_perspective_constraint", {}) or {})
    if focal_perspective_constraint:
        required = _clean(focal_perspective_constraint.get("required_value"))
        negated_values = set(focal_perspective_constraint.get("negated_values", []) or [])
        original_focal = set(detect_focal_perspective(original))
        candidate_focal = detect_focal_perspective(candidate)
        for value, markers in candidate_focal.items():
            if value in original_focal:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(focal_perspective_constraint.get("required_label")) or "排除焦段透视"
                return (
                    f"模型响应越过焦段透视约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    key_light_direction_constraint = dict(scene_graph.get("key_light_direction_constraint", {}) or {})
    if key_light_direction_constraint:
        required = _clean(key_light_direction_constraint.get("required_value"))
        negated_values = set(key_light_direction_constraint.get("negated_values", []) or [])
        original_direction = set(detect_key_light_direction(original))
        candidate_direction = detect_key_light_direction(candidate)
        for value, markers in candidate_direction.items():
            if value in original_direction:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(key_light_direction_constraint.get("required_label")) or "排除主光方向"
                return (
                    f"模型响应越过主光方向约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
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
    "HUMAN_SUBJECT_INTRUSION_MARKERS",
    "LIGHT_TEMPERATURE_MARKERS",
    "COLOR_RENDERING_MARKERS",
    "DEPTH_OF_FIELD_MARKERS",
    "LIGHTING_QUALITY_MARKERS",
    "MOTION_RENDERING_MARKERS",
    "CAMERA_STABILITY_MARKERS",
    "FOCAL_PERSPECTIVE_MARKERS",
    "KEY_LIGHT_DIRECTION_MARKERS",
    "apply_relation_hint_resolution",
    "build_intelligence_profile",
    "build_scene_relationship_graph",
    "candidate_world_violation",
    "classify_repair_reason",
    "detect_camera_angle",
    "detect_camera_stability",
    "detect_color_rendering",
    "detect_depth_of_field",
    "detect_focal_perspective",
    "detect_lighting_quality",
    "detect_motion_rendering",
    "detect_human_subject_intrusions",
    "detect_key_light_direction",
    "detect_light_temperature",
    "detect_negated_camera_angle",
    "detect_negated_camera_stability",
    "detect_negated_color_rendering",
    "detect_negated_depth_of_field",
    "detect_negated_focal_perspective",
    "detect_negated_key_light_direction",
    "detect_negated_lighting_quality",
    "detect_negated_motion_rendering",
    "detect_negated_light_temperature",
    "detect_negated_world_families",
    "detect_negated_scene_attributes",
    "detect_negated_subject_cardinality",
    "detect_negated_subject_orientation",
    "detect_negated_subject_pose",
    "detect_negated_shot_scale",
    "detect_scene_attributes",
    "detect_subject_cardinality",
    "detect_subject_orientation",
    "detect_subject_pose",
    "detect_shot_scale",
    "introduced_human_subject_intrusions",
    "detect_world_families",
    "infer_task_intent",
    "resolve_model_strategy",
    "resolve_preference_hints",
    "resolve_relation_hints",
    "resolve_soft_scene_conflicts",
    "summarize_intelligence_profile",
    "update_preference_memory",
]
