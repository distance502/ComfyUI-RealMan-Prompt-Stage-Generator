# -*- coding: utf-8 -*-
"""Unified intent, scene-graph, model-strategy, and preference orchestration."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import re
from typing import Any, Iterable


INTELLIGENCE_PROFILE_VERSION = "qwen-te-intelligence-v90"

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
    "wind": {
        "calm": (
            "无风", "静风", "风平浪静", "空气静止", "windless", "still air", "calm air",
        ),
        "breeze": (
            "微风", "轻风", "徐徐清风", "轻柔气流", "breeze", "gentle wind", "light wind",
        ),
        "strong_wind": (
            "强风", "大风", "狂风", "烈风", "猛烈阵风", "strong wind", "gale", "violent wind", "gusty wind",
        ),
    },
    "ambient_temperature": {
        "cold": (
            "严寒环境", "寒冷环境", "低温环境", "冰冷空气", "零下低温", "刺骨寒冷",
            "freezing cold", "cold weather", "subzero temperature", "icy air",
        ),
        "mild": (
            "温和气温", "舒适气温", "不冷不热", "宜人温度",
            "mild temperature", "temperate weather", "comfortable temperature",
        ),
        "hot": (
            "炎热环境", "酷热天气", "高温环境", "热浪天气", "闷热空气", "灼热空气",
            "scorching heat", "hot weather", "high ambient temperature", "heatwave",
        ),
    },
    "ground_surface": {
        "dry_ground": (
            "干燥地面", "干燥路面", "地表干燥", "路面无积水",
            "dry ground", "dry pavement", "dry roadway",
        ),
        "wet_ground": (
            "湿润地面", "潮湿地面", "湿滑路面", "雨水路面", "地面积水", "水洼路面",
            "wet ground", "wet pavement", "rain-soaked street", "puddled ground",
        ),
        "icy_ground": (
            "结冰地面", "冰封路面", "薄冰地表", "冻结路面",
            "icy ground", "frozen ground", "ice-covered pavement",
        ),
    },
    "spatial_enclosure": {
        "indoor": (
            "室内场景", "室内空间", "房间内部", "建筑内部", "封闭室内",
            "indoor scene", "indoor space", "inside the room", "inside the building",
        ),
        "outdoor": (
            "户外场景", "户外环境", "室外空间", "露天环境",
            "outdoor scene", "outdoor setting", "open-air setting", "outdoors",
        ),
        "semi_open": (
            "半开放空间", "有顶棚的开放空间", "开放式廊亭", "四面通风的顶棚空间",
            "semi-open space", "covered outdoor area", "open-sided shelter",
        ),
    },
    "dominant_light_source": {
        "natural_light": (
            "自然光照明", "纯自然光照明", "仅自然光照明", "日光主导照明", "窗外日光照明",
            "natural-light illumination", "daylight-dominant lighting", "lit only by daylight",
        ),
        "artificial_light": (
            "人工光照明", "纯人工光照明", "仅人工灯光照明", "电气灯光主导", "棚灯主导照明",
            "artificial-light illumination", "electric-light-dominant lighting", "lit only by artificial lights",
        ),
        "mixed_light": (
            "自然光与人工光混合", "日光与灯光混合照明", "混合光源照明",
            "mixed natural and artificial lighting", "mixed-source lighting",
        ),
    },
}
_SCENE_ATTRIBUTE_LABELS = {
    "time_of_day": "昼夜",
    "precipitation": "降水",
    "wind": "风势",
    "ambient_temperature": "环境温度",
    "ground_surface": "地表状态",
    "spatial_enclosure": "空间围合",
    "dominant_light_source": "主导照明来源",
    "dawn": "清晨",
    "day": "白天",
    "dusk": "黄昏",
    "night": "夜晚",
    "clear": "晴朗",
    "rain": "降雨",
    "snow": "降雪",
    "calm": "静风",
    "breeze": "微风",
    "strong_wind": "强风",
    "cold": "寒冷",
    "mild": "温和",
    "hot": "炎热",
    "dry_ground": "干燥",
    "wet_ground": "湿润积水",
    "icy_ground": "结冰",
    "indoor": "室内",
    "outdoor": "户外",
    "semi_open": "半开放",
    "natural_light": "自然光",
    "artificial_light": "人工光",
    "mixed_light": "混合光源",
}
_SCENE_ATTRIBUTE_REPAIR_RULES: tuple[tuple[str, str, str], ...] = (
    (
        "time_of_day",
        "昼夜",
        "只修正天空明暗、太阳或月亮可见性以及对应时段光线，不改变主体、动作、场景与剧情顺序。",
    ),
    (
        "precipitation",
        "降水",
        "只修正晴朗、降雨或降雪状态及其直接落点反馈，不改变主体、动作、场景与剧情顺序。",
    ),
    (
        "wind",
        "风势",
        "只修正发丝、衣摆、植被与既有空气介质的受力状态，不新增空气介质，不改变主体、动作、场景与剧情顺序。",
    ),
    (
        "ambient_temperature",
        "环境温度",
        "只修正呼气、汗液、衣着反馈、凝露与热浪表现，不改变主体、动作、场景与剧情顺序。",
    ),
    (
        "ground_surface",
        "地表状态",
        "只修正地面反光、水洼、结冰、脚印、接触阴影与移动接触反馈，不改变主体、动作、场景与剧情顺序。",
    ),
    (
        "spatial_enclosure",
        "空间围合",
        "只修正墙体、顶棚、原文已有开口、天空可见性与内外边界，不新增门窗、洞口或室外远景，不改变主体、动作、道具与剧情顺序。",
    ),
    (
        "dominant_light_source",
        "主导照明来源",
        "只修正全局阴影、反射高光、综合色偏以及主光与辅助光关系，不改变主体、动作、场景与剧情顺序。",
    ),
)
# These patterns infer only candidate-side physical feedback. They never create
# a user constraint, so descriptive details cannot silently lock an open axis.
SCENE_ATTRIBUTE_FEEDBACK_PATTERNS: dict[str, dict[str, tuple[re.Pattern[str], ...]]] = {
    "time_of_day": {
        "dawn": (
            re.compile(r"(?:晨曦|破晓微光)[^。！？.!?\n]{0,16}(?:铺开|泛起|照亮)|\bfirst light\b[^.!?\n]{0,32}\b(?:spreads|fills|illuminates)\b", re.IGNORECASE),
        ),
        "day": (
            re.compile(r"太阳[^。！？.!?\n]{0,16}(?:高悬|直射|投下短影)|\b(?:the sun|sunlight)\b[^.!?\n]{0,32}\b(?:overhead|casts short shadows|shines directly)\b", re.IGNORECASE),
        ),
        "dusk": (
            re.compile(r"(?:暮色|落日余晖)[^。！？.!?\n]{0,16}(?:笼罩|染红|铺满)|\b(?:evening glow|sunset afterglow)\b[^.!?\n]{0,32}\b(?:settles|fills|turns)\b", re.IGNORECASE),
        ),
        "night": (
            re.compile(r"(?:繁星|星光)[^。！？.!?\n]{0,16}(?:铺满|笼罩|照亮)|\b(?:stars|starlight)\b[^.!?\n]{0,32}\b(?:fill|fills|cover|covers|illuminate|illuminates)\b", re.IGNORECASE),
        ),
    },
    "precipitation": {
        "clear": (
            re.compile(r"(?:雨雪|降水)[^。！？.!?\n]{0,12}(?:完全停止|已经停止)|云层[^。！？.!?\n]{0,10}(?:完全散尽|彻底散尽)|\b(?:rain|snow|precipitation)\b[^.!?\n]{0,24}\b(?:has|have) stopped completely\b", re.IGNORECASE),
        ),
        "rain": (
            re.compile(r"雨滴[^。！？.!?\n]{0,14}(?:落下|敲打|打湿)|\braindrops?\b[^.!?\n]{0,28}\b(?:fall|falls|strike|strikes|soak|soaks)\b", re.IGNORECASE),
        ),
        "snow": (
            re.compile(r"雪花[^。！？.!?\n]{0,14}(?:飘落|落下|覆盖)|\bsnowflakes?\b[^.!?\n]{0,28}\b(?:fall|falls|drift|drifts|cover|covers)\b", re.IGNORECASE),
        ),
    },
    "wind": {
        "calm": (
            re.compile(r"(?:发丝|头发|衣摆|披风|烟柱|烟雾)[^。！？.!?\n]{0,16}(?:自然垂落|纹丝不动|垂直上升)|\b(?:hair|hem|cape|smoke)\b[^.!?\n]{0,32}\b(?:hangs still|remains motionless|rises vertically)\b", re.IGNORECASE),
            re.compile(r"(?:雨滴|雨线|雪花)[^。！？.!?\n]{0,14}(?:近乎垂直|垂直落下|笔直落下)|\b(?:rain|raindrops|snowflakes)\b[^.!?\n]{0,32}\b(?:falls?|descends?) (?:almost )?vertically\b", re.IGNORECASE),
            re.compile(r"(?:雾层|水汽层)[^。！？.!?\n]{0,16}(?:近乎静止|纹丝不动|不产生横向漂移)|\b(?:mist|moisture) layers?\b[^.!?\n]{0,32}\b(?:remains? nearly still|shows? no lateral drift)\b", re.IGNORECASE),
        ),
        "breeze": (
            re.compile(r"(?:发丝|衣角|树叶)[^。！？.!?\n]{0,14}(?:轻轻摆动|微微拂动|缓慢摇曳)|\b(?:hair|hem|leaves)\b[^.!?\n]{0,32}\b(?:sways gently|flutter gently|flutters gently)\b", re.IGNORECASE),
            re.compile(r"(?:雨滴|雨线|雪花)[^。！？.!?\n]{0,14}(?:轻微倾斜|缓慢偏移|轻柔侧移)|\b(?:rain|raindrops|snowflakes)\b[^.!?\n]{0,32}\b(?:tilts? slightly|drifts? gently)\b", re.IGNORECASE),
            re.compile(r"(?:雾层|水汽层)[^。！？.!?\n]{0,16}(?:缓慢侧移|轻柔偏移|低幅横移)|\b(?:mist|moisture) layers?\b[^.!?\n]{0,32}\b(?:drifts? gently|shifts? slowly sideways)\b", re.IGNORECASE),
        ),
        "strong_wind": (
            re.compile(r"(?:发丝|长发|衣摆|披风|树枝|烟雾|尘粒)[^。！？.!?\n]{0,18}(?:猛烈掀起|剧烈翻飞|压向一侧|掀向一侧|横向卷走|大幅弯折)|\b(?:hair|hem|cape|branches|smoke|dust)\b[^.!?\n]{0,40}\b(?:whips violently|is blown sideways|are blown sideways|bends sharply)\b", re.IGNORECASE),
            re.compile(r"(?:雨线|雨滴|雪花)[^。！？.!?\n]{0,16}(?:斜向扫过|横向飞掠|横飞|几乎平行地面)|\b(?:rain|raindrops|snowflakes)\b[^.!?\n]{0,36}\b(?:lashes diagonally|drives sideways|flies horizontally)\b", re.IGNORECASE),
            re.compile(r"(?:雾层|水汽层)[^。！？.!?\n]{0,18}(?:横向卷过|快速侧移|沿单一方向扫过)|\b(?:mist|moisture) layers?\b[^.!?\n]{0,36}\b(?:sweeps? sideways|races? laterally|drives? in one direction)\b", re.IGNORECASE),
        ),
    },
    "ambient_temperature": {
        "cold": (
            re.compile(r"(?:呼气|气息)[^。！？.!?\n]{0,10}(?:凝成|化作|形成)[^。！？.!?\n]{0,6}白雾|(?:睫毛|发梢|衣领)[^。！？.!?\n]{0,10}(?:结霜|凝霜)|\b(?:breath|exhalation)\b[^.!?\n]{0,28}\b(?:forms|turns into) white mist\b", re.IGNORECASE),
        ),
        "hot": (
            re.compile(r"空气[^。！？.!?\n]{0,10}(?:因高热|被热量)[^。！？.!?\n]{0,10}(?:扭曲|晃动)|皮肤[^。！？.!?\n]{0,10}(?:因酷热|被高温)[^。！？.!?\n]{0,10}(?:泛红|冒汗)|\bair\b[^.!?\n]{0,32}\b(?:shimmers|warps) from (?:the )?heat\b", re.IGNORECASE),
        ),
    },
    "ground_surface": {
        "dry_ground": (
            re.compile(r"(?:脚下|鞋底)[^。！？.!?\n]{0,12}(?:扬起|带起)[^。！？.!?\n]{0,6}(?:干尘|尘土)|路面[^。！？.!?\n]{0,10}(?:没有水痕|毫无水痕)|\b(?:footsteps?|boots?)\b[^.!?\n]{0,32}\b(?:kick up|kicks up|raise|raises) dry dust\b", re.IGNORECASE),
        ),
        "wet_ground": (
            re.compile(r"(?:脚步|鞋底)[^。！？.!?\n]{0,14}(?:溅起|踩出)[^。！？.!?\n]{0,6}(?:水花|涟漪)|(?:地面|路面)[^。！？.!?\n]{0,10}(?:湿亮反光|湿光倒影)|\b(?:footsteps?|boots?)\b[^.!?\n]{0,32}\b(?:splash|splashes) (?:water|through puddles)\b", re.IGNORECASE),
        ),
        "icy_ground": (
            re.compile(r"(?:鞋底|脚步)[^。！？.!?\n]{0,12}(?:在冰面打滑|失去抓地)|薄冰[^。！？.!?\n]{0,10}(?:开裂|龟裂)|\b(?:boots?|feet)\b[^.!?\n]{0,28}\b(?:slip|slides?) on (?:the )?ice\b", re.IGNORECASE),
        ),
    },
    "spatial_enclosure": {
        "indoor": (
            re.compile(r"(?:墙壁|墙体)[^。！？.!?\n]{0,14}(?:与|和)[^。！？.!?\n]{0,8}(?:顶棚|天花板)[^。！？.!?\n]{0,14}(?:完全闭合|封闭四周)|四周[^。！？.!?\n]{0,12}(?:封闭|闭合)[^。！？.!?\n]{0,10}(?:没有门窗|无门无窗)|\bwalls?\b[^.!?\n]{0,32}\b(?:and|with) (?:a )?(?:ceiling|roof)\b[^.!?\n]{0,28}\bfully enclose\b", re.IGNORECASE),
        ),
        "outdoor": (
            re.compile(r"(?:头顶|人物上方)[^。！？.!?\n]{0,12}(?:毫无遮蔽|完全无遮蔽)[^。！？.!?\n]{0,8}(?:天空|天际)|四周[^。！？.!?\n]{0,12}(?:没有|不存在)[^。！？.!?\n]{0,8}(?:墙体|顶棚)|\b(?:open|unobstructed) sky\b[^.!?\n]{0,28}\b(?:directly above|overhead)\b", re.IGNORECASE),
        ),
        "semi_open": (
            re.compile(r"(?:顶棚|雨棚)[^。！？.!?\n]{0,12}(?:遮住|覆盖)[^。！？.!?\n]{0,10}(?:头顶|上方)[^。！？.!?\n]{0,18}(?:四周|侧面)[^。！？.!?\n]{0,8}(?:敞开|通风)|\b(?:roof|canopy)\b[^.!?\n]{0,32}\boverhead\b[^.!?\n]{0,32}\bopen sides\b", re.IGNORECASE),
        ),
    },
    "dominant_light_source": {
        "natural_light": (
            re.compile(r"(?:日光|阳光|窗外天光)[^。！？.!?\n]{0,14}(?:成为|构成|作为)[^。！？.!?\n]{0,8}(?:唯一|全局|主要)[^。！？.!?\n]{0,8}(?:光源|主光)|\b(?:daylight|sunlight)\b[^.!?\n]{0,32}\b(?:is|becomes|remains) the (?:only|primary|global) light\b", re.IGNORECASE),
        ),
        "artificial_light": (
            re.compile(r"(?:棚灯|顶灯|霓虹灯|电灯)[^。！？.!?\n]{0,14}(?:成为|接管|构成)[^。！？.!?\n]{0,8}(?:唯一|全局|主要)[^。！？.!?\n]{0,8}(?:光源|主光|照明)|\b(?:studio lights?|ceiling lights?|neon lights?|electric lights?)\b[^.!?\n]{0,36}\b(?:become|becomes|take over as) the (?:only|primary|global) light\b", re.IGNORECASE),
        ),
        "mixed_light": (
            re.compile(r"(?:日光|天光)[^。！？.!?\n]{0,14}(?:与|和)[^。！？.!?\n]{0,10}(?:灯光|棚灯|电灯)[^。！？.!?\n]{0,14}(?:共同|同时)[^。！？.!?\n]{0,10}(?:照明|塑造阴影|成为主光)|\b(?:daylight|sunlight)\b[^.!?\n]{0,32}\b(?:and|with) (?:artificial|electric|studio) lights?\b[^.!?\n]{0,32}\b(?:jointly|together|both)\b", re.IGNORECASE),
        ),
    },
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
SUBJECT_ORIENTATION_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "front": (
        re.compile(
            r"(?:双眼|两眼)[^。！？.!?\n]{0,18}(?:同时|均|都)?[^。！？.!?\n]{0,8}(?:清晰)?可见[^。！？.!?\n]{0,24}(?:完整五官|面部中线|左右对称的脸部)|"
            r"(?:完整五官|面部中线|左右对称的脸部)[^。！？.!?\n]{0,24}(?:双眼|两眼)[^。！？.!?\n]{0,16}(?:同时|均|都)?[^。！？.!?\n]{0,8}(?:清晰)?可见|"
            r"\bboth eyes\b[^.!?\n]{0,24}\b(?:clearly )?visible\b[^.!?\n]{0,32}\b(?:full facial features|facial midline|symmetrical face)\b|"
            r"\b(?:full facial features|facial midline|symmetrical face)\b[^.!?\n]{0,32}\bboth eyes\b[^.!?\n]{0,24}\b(?:clearly )?visible\b",
            re.IGNORECASE,
        ),
    ),
    "side": (
        re.compile(
            r"(?:只有|仅有|只露出)[^。！？.!?\n]{0,6}(?:一只眼睛|单眼)[^。！？.!?\n]{0,18}(?:可见|入镜)[^。！？.!?\n]{0,28}(?:鼻梁|鼻尖|下颌)[^。！？.!?\n]{0,16}(?:形成|构成|呈现)[^。！？.!?\n]{0,8}(?:单侧)?轮廓|"
            r"\bonly one eye\b[^.!?\n]{0,24}\bvisible\b[^.!?\n]{0,36}\b(?:nose|nasal bridge|chin|jaw)\b[^.!?\n]{0,24}\b(?:profile|silhouette|outline)\b",
            re.IGNORECASE,
        ),
    ),
    "back": (
        re.compile(
            r"(?:后脑|后脑勺)[^。！？.!?\n]{0,24}(?:双肩|肩背|背部)[^。！？.!?\n]{0,24}(?:朝向镜头|面向镜头|成为主要可见面)|"
            r"\bback of (?:the )?head\b[^.!?\n]{0,36}\b(?:both shoulders|shoulders|upper back|back)\b[^.!?\n]{0,36}\b(?:faces? (?:the )?camera|forms? the primary visible surface)\b",
            re.IGNORECASE,
        ),
    ),
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
_OPEN_ORIENTATION_LAYOUT_RE = re.compile(
    r"(?:角色设定图|人物设定图|三视图|三幅视图|正侧背|正面侧面背面|镜中视图|镜中倒影|镜前[^，,；;。！？.!?\n]{0,20}倒影|"
    r"character sheet|character turnaround|front side back|mirror view|mirrored view)",
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
SUBJECT_POSE_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "standing": (
        re.compile(
            r"(?:人物|角色|主体)[^。！？.!?\n]{0,28}(?:双脚|两脚)[^。！？.!?\n]{0,18}(?:落地|着地|承重)[^。！？.!?\n]{0,28}(?:髋部|膝盖|双腿)[^。！？.!?\n]{0,18}(?:伸展|伸直|直立)|"
            r"\b(?:subject|character)\b[^.!?\n]{0,36}\bboth feet\b[^.!?\n]{0,24}\b(?:planted|bear(?:ing)? weight|supporting the body)\b[^.!?\n]{0,36}\b(?:hips?|knees?|legs?)\b[^.!?\n]{0,24}\b(?:extended|straight|upright)\b",
            re.IGNORECASE,
        ),
    ),
    "sitting": (
        re.compile(
            r"(?:人物|角色|主体)[^。！？.!?\n]{0,28}(?:臀部|髋部)[^。！？.!?\n]{0,18}(?:由|被)?(?:座面|座椅|椅面|台阶|石沿)[^。！？.!?\n]{0,14}(?:承托|支撑|托住)[^。！？.!?\n]{0,28}(?:双腿|双膝|膝盖)[^。！？.!?\n]{0,18}(?:向前|弯曲|垂落)|"
            r"\b(?:subject|character)\b[^.!?\n]{0,36}\b(?:hips?|pelvis)\b[^.!?\n]{0,28}\b(?:supported|resting) (?:on|by) (?:the )?(?:seat|chair|step|ledge)\b[^.!?\n]{0,40}\b(?:legs?|knees?)\b[^.!?\n]{0,24}\b(?:bent|forward|hanging)\b",
            re.IGNORECASE,
        ),
    ),
    "kneeling": (
        re.compile(
            r"(?:人物|角色|主体)[^。！？.!?\n]{0,28}(?:单膝|双膝|膝盖)[^。！？.!?\n]{0,18}(?:着地|触地|压在地面|跪压地面|以膝承重)|"
            r"\b(?:subject|character)\b[^.!?\n]{0,36}\b(?:one knee|both knees|knees?)\b[^.!?\n]{0,24}\b(?:touch(?:es|ing)?|press(?:es|ing)? (?:against|into)|bear(?:s|ing)? weight on) (?:the )?(?:ground|floor)\b",
            re.IGNORECASE,
        ),
    ),
    "lying": (
        re.compile(
            r"(?:人物|角色|主体)[^。！？.!?\n]{0,28}(?:背部|胸腹|躯干|身体侧面)[^。！？.!?\n]{0,18}(?:贴住|接触|由|被)[^。！？.!?\n]{0,8}(?:地面|床面|平台)[^。！？.!?\n]{0,16}(?:支撑|承托|托住|展开)|"
            r"\b(?:subject|character)\b[^.!?\n]{0,36}\b(?:back|torso|chest|side of the body)\b[^.!?\n]{0,28}\b(?:rests?|lies?|is supported) (?:flat )?(?:on|by) (?:the )?(?:ground|floor|bed|platform)\b",
            re.IGNORECASE,
        ),
    ),
    "crouching": (
        re.compile(
            r"(?:人物|角色|主体)[^。！？.!?\n]{0,28}(?:髋部|重心)[^。！？.!?\n]{0,18}(?:降低|下沉|贴近地面)[^。！？.!?\n]{0,28}(?:双膝|膝盖)[^。！？.!?\n]{0,18}(?:深度弯曲|大幅弯曲)[^。！？.!?\n]{0,28}(?:双脚|脚掌)[^。！？.!?\n]{0,14}(?:承重|着地)|"
            r"\b(?:subject|character)\b[^.!?\n]{0,36}\b(?:hips?|center of gravity)\b[^.!?\n]{0,24}\b(?:lowered|close to the ground)\b[^.!?\n]{0,36}\bknees?\b[^.!?\n]{0,24}\bdeeply bent\b[^.!?\n]{0,36}\bfeet\b[^.!?\n]{0,20}\b(?:planted|bearing weight)\b",
            re.IGNORECASE,
        ),
    ),
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
SHOT_SCALE_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "closeup": (
        re.compile(
            r"(?:画面|取景|构图)[^。！？.!?\n]{0,20}(?:边界|裁切|下缘)[^。！？.!?\n]{0,16}(?:收在|停在|裁到)[^。！？.!?\n]{0,10}(?:肩部|锁骨)[^。！？.!?\n]{0,28}(?:脸部|面部)[^。！？.!?\n]{0,16}(?:占据|填满)[^。！？.!?\n]{0,10}(?:大部分|主要)(?:画幅|面积)|"
            r"\b(?:frame|framing)\b[^.!?\n]{0,28}\b(?:ends?|crops?|stops?) just below (?:the )?(?:shoulders|collarbone)\b[^.!?\n]{0,40}\b(?:face|facial area)\b[^.!?\n]{0,24}\b(?:fills?|occupies?) most of (?:the )?frame\b",
            re.IGNORECASE,
        ),
    ),
    "medium": (
        re.compile(
            r"(?:画面|取景|构图)[^。！？.!?\n]{0,20}(?:从|覆盖)[^。！？.!?\n]{0,8}(?:头顶|头部)[^。！？.!?\n]{0,18}(?:延伸到|收至|裁到)[^。！？.!?\n]{0,10}(?:腰部|胯部|大腿中段)[^。！？.!?\n]{0,28}(?:躯干|双臂|上半身)[^。！？.!?\n]{0,18}(?:完整|清晰)(?:可见|入镜)?|"
            r"\b(?:frame|framing)\b[^.!?\n]{0,28}\b(?:runs?|extends?|crops?) from (?:the )?(?:head|top of the head) to (?:the )?(?:waist|hips|mid-thigh)\b[^.!?\n]{0,40}\b(?:torso|arms|upper body)\b[^.!?\n]{0,24}\b(?:fully |clearly )?(?:visible|framed)\b",
            re.IGNORECASE,
        ),
    ),
    "full_body": (
        re.compile(
            r"(?:人物|角色|主体)[^。！？.!?\n]{0,24}(?:从头顶到双脚|从头到脚|头顶至双脚)[^。！？.!?\n]{0,16}(?:完整入镜|完整可见|全部纳入画面)[^。！？.!?\n]{0,28}(?:双脚|鞋底)[^。！？.!?\n]{0,18}(?:位于|留在|保持在)[^。！？.!?\n]{0,10}(?:画面|取景|构图)(?:边界)?(?:内|以内)|"
            r"\b(?:subject|character)\b[^.!?\n]{0,32}\b(?:head to toe|from head to feet)\b[^.!?\n]{0,24}\b(?:fully visible|fully contained|inside the frame)\b[^.!?\n]{0,40}\b(?:both feet|shoes)\b[^.!?\n]{0,24}\b(?:inside|within) (?:the )?frame\b",
            re.IGNORECASE,
        ),
    ),
    "wide": (
        re.compile(
            r"(?:人物|角色|主体)[^。！？.!?\n]{0,24}(?:只占|仅占)[^。！？.!?\n]{0,10}(?:画面|画幅|构图)[^。！？.!?\n]{0,10}(?:很小|小比例|少量)[^。！？.!?\n]{0,28}(?:环境|场景|空间)[^。！？.!?\n]{0,16}(?:占据|覆盖|构成)[^。！？.!?\n]{0,10}(?:大部分|主要)(?:画幅|面积|视觉信息)|"
            r"\b(?:subject|character)\b[^.!?\n]{0,28}\boccupies? (?:only )?a small (?:part|fraction|portion) of (?:the )?frame\b[^.!?\n]{0,40}\b(?:environment|setting|space)\b[^.!?\n]{0,24}\b(?:fills?|occupies?|dominates?) most of (?:the )?frame\b",
            re.IGNORECASE,
        ),
    ),
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
CAMERA_ANGLE_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "low_angle": (
        re.compile(
            r"(?:摄影机|摄像机|镜头|机位)[^。！？.!?\n]{0,24}(?:低于|处于)[^。！？.!?\n]{0,12}(?:视线|眼平线|眼睛)[^。！？.!?\n]{0,36}(?:下颌|下巴)(?:底面|下侧|下方)[^。！？.!?\n]{0,12}(?:可见|显露|入镜)[^。！？.!?\n]{0,36}(?:垂直线|竖线|垂直结构)[^。！？.!?\n]{0,16}(?:向上汇聚|朝上汇聚|上方汇聚)|"
            r"\b(?:camera|lens)\b[^.!?\n]{0,32}\bbelow (?:the )?(?:subject(?:'s)? )?(?:eye line|eyes)\b[^.!?\n]{0,40}\b(?:underside|bottom) of (?:the )?(?:chin|jaw)\b[^.!?\n]{0,20}\b(?:visible|shown)\b[^.!?\n]{0,40}\bverticals?\b[^.!?\n]{0,20}\bconverge(?:s|d)? upward\b",
            re.IGNORECASE,
        ),
    ),
    "eye_level": (
        re.compile(
            r"(?:镜头|机位|镜头轴线|摄影机轴线)[^。！？.!?\n]{0,20}(?:与|对齐)[^。！？.!?\n]{0,10}(?:双眼|眼睛|视线|眼平线)[^。！？.!?\n]{0,36}(?:地平线|水平线)[^。！？.!?\n]{0,16}(?:位于|保持在|对齐)[^。！？.!?\n]{0,10}(?:眼高|眼睛高度|视线高度)[^。！？.!?\n]{0,36}(?:垂直线|竖线|垂直结构)[^。！？.!?\n]{0,16}(?:保持中性|没有倾斜|不发生汇聚|平直)|"
            r"\b(?:lens|camera) axis\b[^.!?\n]{0,28}\b(?:aligned|level) with (?:the )?(?:subject(?:'s)? )?(?:eyes|eye line)\b[^.!?\n]{0,40}\bhorizon\b[^.!?\n]{0,20}\bat eye (?:height|level)\b[^.!?\n]{0,40}\bverticals?\b[^.!?\n]{0,20}\b(?:remain(?:s)? neutral|stay(?:s)? neutral|are neutral)\b",
            re.IGNORECASE,
        ),
    ),
    "high_angle": (
        re.compile(
            r"(?:摄影机|摄像机|镜头|机位)[^。！？.!?\n]{0,24}(?:高于|处于)[^。！？.!?\n]{0,12}(?:视线|眼平线|眼睛)[^。！？.!?\n]{0,36}(?:头顶|头冠|肩部上表面|双肩上表面)[^。！？.!?\n]{0,16}(?:可见|显露|入镜)[^。！？.!?\n]{0,36}(?:地面|地表)[^。！？.!?\n]{0,18}(?:向主体后方展开|在主体后方展开|向后铺开)|"
            r"\b(?:camera|lens)\b[^.!?\n]{0,32}\babove (?:the )?(?:subject(?:'s)? )?(?:eye line|eyes)\b[^.!?\n]{0,40}\b(?:crown|top of (?:the )?head|tops? of (?:the )?shoulders)\b[^.!?\n]{0,20}\b(?:visible|shown)\b[^.!?\n]{0,40}\bground\b[^.!?\n]{0,24}\b(?:expands?|extends?|opens?) behind (?:the )?subject\b",
            re.IGNORECASE,
        ),
    ),
    "top_down": (
        re.compile(
            r"(?:摄影机|摄像机|镜头|机位)(?:轴线)?[^。！？.!?\n]{0,24}(?:垂直向下|竖直向下|正对地面)[^。！？.!?\n]{0,36}(?:头顶|顶部表面|朝上表面)[^。！？.!?\n]{0,16}(?:占据|成为|构成)[^。！？.!?\n]{0,12}(?:主要|大部分)[^。！？.!?\n]{0,12}(?:画面|视觉信息)[^。！？.!?\n]{0,36}(?:地面|地平面|地表)[^。！？.!?\n]{0,16}(?:铺满|填满|占满)(?:画面|画幅)|"
            r"\b(?:camera|lens) axis\b[^.!?\n]{0,28}\bpoints? vertically downward\b[^.!?\n]{0,40}\b(?:crown|top surfaces?|upward-facing surfaces?)\b[^.!?\n]{0,24}\b(?:dominates?|fills?) (?:the )?frame\b[^.!?\n]{0,40}\bground plane\b[^.!?\n]{0,20}\b(?:fills?|covers?) (?:the )?frame\b",
            re.IGNORECASE,
        ),
    ),
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
LIGHT_TEMPERATURE_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "warm": (
        re.compile(
            r"(?:全局|整体)(?:画面)?(?:白点|白平衡)[^。！？.!?\n]{0,18}(?:偏向|移向|落在)[^。！？.!?\n]{0,10}(?:琥珀|橙金|黄橙)[^。！？.!?\n]{0,36}(?:中性白色|白色参考|中性灰|灰色表面)[^。！？.!?\n]{0,28}(?:一致|统一|持续)[^。！？.!?\n]{0,12}(?:偏黄|琥珀染色|橙金染色|暖染)|"
            r"\b(?:global|overall) white point\b[^.!?\n]{0,28}\b(?:shifts?|leans?|moves?) (?:toward|to)\b[^.!?\n]{0,16}\b(?:amber|orange-gold|yellow-orange)\b[^.!?\n]{0,44}\b(?:neutral whites?|neutral grays?|neutral greys?|white reference surfaces?)\b[^.!?\n]{0,32}\b(?:carry|show|have) (?:a )?consistent (?:amber|golden|yellow) cast\b",
            re.IGNORECASE,
        ),
    ),
    "cool": (
        re.compile(
            r"(?:全局|整体)(?:画面)?(?:白点|白平衡)[^。！？.!?\n]{0,18}(?:偏向|移向|落在)[^。！？.!?\n]{0,10}(?:蓝青|青蓝|蓝灰)[^。！？.!?\n]{0,36}(?:中性白色|白色参考|中性灰|灰色表面)[^。！？.!?\n]{0,28}(?:一致|统一|持续)[^。！？.!?\n]{0,12}(?:偏蓝|蓝青染色|青蓝染色|冷染)|"
            r"\b(?:global|overall) white point\b[^.!?\n]{0,28}\b(?:shifts?|leans?|moves?) (?:toward|to)\b[^.!?\n]{0,16}\b(?:blue-cyan|cyan-blue|blue-gray|blue-grey)\b[^.!?\n]{0,44}\b(?:neutral whites?|neutral grays?|neutral greys?|white reference surfaces?)\b[^.!?\n]{0,32}\b(?:carry|show|have) (?:a )?consistent (?:blue|cyan|blue-cyan) cast\b",
            re.IGNORECASE,
        ),
    ),
    "neutral": (
        re.compile(
            r"(?:全局|整体)(?:画面)?(?:白点|白平衡)[^。！？.!?\n]{0,20}(?:保持|呈现)[^。！？.!?\n]{0,12}(?:色彩平衡|准确白平衡|无偏色)[^。！？.!?\n]{0,36}(?:中性白色|白色参考|中性灰|灰色表面)[^。！？.!?\n]{0,28}(?:没有|不带|不呈现)[^。！？.!?\n]{0,12}(?:持续|统一|整体)?(?:综合色偏|偏色|染色)|"
            r"\b(?:global|overall) white point\b[^.!?\n]{0,28}\b(?:remains?|stays?|is) (?:chromatically )?balanced\b[^.!?\n]{0,44}\b(?:neutral whites?|neutral grays?|neutral greys?|white reference surfaces?)\b[^.!?\n]{0,32}\b(?:show|carry|have) no (?:consistent |overall )?colou?r cast\b",
            re.IGNORECASE,
        ),
    ),
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
COLOR_RENDERING_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "monochrome": (
        re.compile(
            r"(?:全局|整体|全幅|整个画面)(?:综合色度|色彩信息|颜色通道)[^。！？.!?\n]{0,18}(?:归零|消失|关闭)[^。！？.!?\n]{0,28}(?:所有|各个|可见)(?:表面|区域)[^。！？.!?\n]{0,18}(?:只由|仅由)[^。！？.!?\n]{0,12}(?:亮度|明度)[^。！？.!?\n]{0,18}(?:层级|差异)[^。！？.!?\n]{0,12}(?:区分|表达)[^。！？.!?\n]{0,24}(?:不再形成|没有)(?:可辨色相|独立色相)|"
            r"\b(?:global|overall) chroma\b[^.!?\n]{0,18}\b(?:is absent|disappears|is removed)\b[^.!?\n]{0,36}\b(?:every|all) (?:visible )?surfaces?\b[^.!?\n]{0,24}\b(?:represented|defined) only by luminance\b[^.!?\n]{0,36}\b(?:no distinct hues?|no recognizable color separation)\b",
            re.IGNORECASE,
        ),
    ),
    "full_color": (
        re.compile(
            r"(?:红、蓝、绿|红色[^。！？.!?\n]{0,10}蓝色[^。！？.!?\n]{0,10}绿色)(?:三个)?(?:区域|表面|色块)[^。！？.!?\n]{0,24}(?:保持|呈现|拥有)[^。！？.!?\n]{0,16}(?:彼此可辨|独立|清晰分离)[^。！？.!?\n]{0,16}(?:色相|色彩)[^。！？.!?\n]{0,20}(?:与|和)[^。！？.!?\n]{0,8}(?:饱和度|综合色度)|"
            r"\bred, blue, and green\b[^.!?\n]{0,20}\b(?:regions?|areas?|surfaces?)\b[^.!?\n]{0,28}\b(?:retain|keep|show)\b[^.!?\n]{0,18}\b(?:distinct|separate) hues?\b[^.!?\n]{0,20}\b(?:and|with)\b[^.!?\n]{0,12}\b(?:preserved )?(?:saturation|chroma)\b",
            re.IGNORECASE,
        ),
    ),
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
DEPTH_OF_FIELD_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "shallow": (
        re.compile(
            r"(?:主体|主要对象)[^。！？.!?\n]{0,24}(?:所在)?焦平面[^。！？.!?\n]{0,24}(?:细节|纹理|边缘)[^。！？.!?\n]{0,12}(?:保持|呈现)[^。！？.!?\n]{0,10}(?:锐利|清晰)[^。！？.!?\n]{0,36}(?:离开|远离)焦平面[^。！？.!?\n]{0,24}(?:前景|背景)[^。！？.!?\n]{0,12}(?:与|和|及)[^。！？.!?\n]{0,10}(?:背景|前景)[^。！？.!?\n]{0,24}(?:迅速|逐渐)[^。！？.!?\n]{0,12}(?:失去|衰减)[^。！？.!?\n]{0,10}(?:细节|纹理)|"
            r"\b(?:subject|main object)\b[^.!?\n]{0,28}\b(?:on|within) (?:the )?focus plane\b[^.!?\n]{0,28}\b(?:details?|textures?|edges?)\b[^.!?\n]{0,16}\b(?:remain|stay|are) sharp\b[^.!?\n]{0,44}\b(?:foreground and background|background and foreground)\b[^.!?\n]{0,32}\b(?:lose|shed) (?:fine )?detail\b[^.!?\n]{0,24}\baway from (?:the )?focus plane\b",
            re.IGNORECASE,
        ),
    ),
    "deep": (
        re.compile(
            r"(?:近处前景|近距离前景)[^。！？.!?\n]{0,18}(?:中距离主体|中景主体|中距离区域)[^。！？.!?\n]{0,18}(?:远处背景|远距离背景)[^。！？.!?\n]{0,28}(?:纹理|边缘|细节)[^。！？.!?\n]{0,16}(?:保持|呈现)[^。！？.!?\n]{0,12}(?:同等|一致)[^。！？.!?\n]{0,8}(?:清晰|可读)[^。！？.!?\n]{0,28}(?:各距离|所有距离|不同距离)(?:层级)?[^。！？.!?\n]{0,16}(?:同时可辨|同时清楚|均可辨认)|"
            r"\bnear foreground\b[^.!?\n]{0,24}\b(?:mid-distance subject|middle distance|midground)\b[^.!?\n]{0,24}\bfar background\b[^.!?\n]{0,36}\b(?:textures?|edges?|details?)\b[^.!?\n]{0,20}\b(?:remain|stay|are) equally (?:clear|readable|resolved)\b[^.!?\n]{0,36}\b(?:all|each) distance (?:layer|plane)s?\b[^.!?\n]{0,20}\b(?:remain|are) simultaneously discernible\b",
            re.IGNORECASE,
        ),
    ),
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
LIGHTING_QUALITY_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "hard": (
        re.compile(
            r"(?:主体|主要对象)(?:的)?主要投影[^。！？.!?\n]{0,20}(?:边缘|边界)[^。！？.!?\n]{0,12}(?:清楚|清晰|锐利)[^。！？.!?\n]{0,8}(?:且|而|并且)[^。！？.!?\n]{0,8}(?:狭窄|窄)[^。！？.!?\n]{0,32}(?:明暗交界|明暗过渡)[^。！？.!?\n]{0,20}(?:很短|极短|狭小)[^。！？.!?\n]{0,10}(?:距离|范围)[^。！？.!?\n]{0,12}(?:内完成|内结束)[^。！？.!?\n]{0,32}(?:材质)?高光[^。！？.!?\n]{0,16}(?:集中|收束)[^。！？.!?\n]{0,12}(?:小面积|窄小)(?:亮斑|亮区)|"
            r"\b(?:subject|main object)(?:'s)? primary shadow\b[^.!?\n]{0,28}\b(?:edge|boundary)\b[^.!?\n]{0,16}\b(?:is|remains) (?:crisp|sharp) and narrow\b[^.!?\n]{0,40}\btonal transition\b[^.!?\n]{0,24}\b(?:completes|occurs) over (?:a )?(?:very )?short distance\b[^.!?\n]{0,40}\b(?:material )?highlights?\b[^.!?\n]{0,20}\b(?:concentrate|contract) into (?:a )?small bright (?:spot|area)\b",
            re.IGNORECASE,
        ),
    ),
    "soft": (
        re.compile(
            r"(?:主体|主要对象)(?:的)?主要投影[^。！？.!?\n]{0,20}(?:边缘|边界)[^。！？.!?\n]{0,12}(?:宽阔|宽大)[^。！？.!?\n]{0,8}(?:且|而|并且)[^。！？.!?\n]{0,8}(?:渐变|羽化)[^。！？.!?\n]{0,32}(?:明暗交界|明暗过渡)[^。！？.!?\n]{0,20}(?:较大|宽广|较宽)[^。！？.!?\n]{0,10}(?:距离|范围)[^。！？.!?\n]{0,12}(?:内完成|内展开|内延伸)[^。！？.!?\n]{0,32}(?:材质)?高光[^。！？.!?\n]{0,16}(?:扩散|铺开)[^。！？.!?\n]{0,12}(?:宽面积|大面积)(?:亮斑|亮区)|"
            r"\b(?:subject|main object)(?:'s)? primary shadow\b[^.!?\n]{0,28}\b(?:edge|boundary)\b[^.!?\n]{0,16}\b(?:is|remains) broad and (?:feathered|gradual)\b[^.!?\n]{0,40}\btonal transition\b[^.!?\n]{0,24}\b(?:extends|spreads) across (?:a )?(?:wide|broad) range\b[^.!?\n]{0,40}\b(?:material )?highlights?\b[^.!?\n]{0,20}\b(?:spread|diffuse) into (?:a )?(?:wide|broad) bright area\b",
            re.IGNORECASE,
        ),
    ),
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
MOTION_RENDERING_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "frozen": (
        re.compile(
            r"(?:运动中的|移动中的)(?:主体|对象)[^。！？.!?\n]{0,18}(?:轮廓|边缘)[^。！？.!?\n]{0,12}(?:保持|呈现)[^。！？.!?\n]{0,10}(?:单一|唯一)[^。！？.!?\n]{0,8}(?:清楚|清晰)[^。！？.!?\n]{0,32}(?:动作部件|运动部件|肢体)[^。！？.!?\n]{0,24}(?:连续路径|运动路径)[^。！？.!?\n]{0,16}(?:只占|位于)[^。！？.!?\n]{0,10}(?:一个|单个)[^。！？.!?\n]{0,8}(?:离散位置|确定位置)[^。！？.!?\n]{0,32}(?:动作阶段|整个动作)[^。！？.!?\n]{0,16}(?:呈现|停留在)[^。！？.!?\n]{0,12}(?:同一|一个)[^。！？.!?\n]{0,8}(?:确定瞬间|确定相位)|"
            r"\b(?:moving subject|moving object)\b[^.!?\n]{0,28}\b(?:outline|edges?)\b[^.!?\n]{0,16}\b(?:remains?|stays?|are) single and (?:clear|crisp)\b[^.!?\n]{0,40}\b(?:moving parts?|limbs?)\b[^.!?\n]{0,28}\b(?:occupy|hold) one discrete position\b[^.!?\n]{0,40}\b(?:action phase|entire action)\b[^.!?\n]{0,24}\b(?:shows?|presents?) one definite instant\b",
            re.IGNORECASE,
        ),
    ),
    "motion_trail": (
        re.compile(
            r"(?:运动|移动)(?:主体|对象)[^。！？.!?\n]{0,20}(?:沿|顺着)[^。！？.!?\n]{0,12}(?:移动方向|运动方向)[^。！？.!?\n]{0,18}(?:留下|形成)[^。！？.!?\n]{0,12}(?:连续|连贯)[^。！？.!?\n]{0,10}(?:半透明)?(?:位移带|轮廓带)[^。！？.!?\n]{0,32}(?:起点|初始位置)[^。！？.!?\n]{0,12}(?:与|和)[^。！？.!?\n]{0,10}(?:终点|最终位置)[^。！？.!?\n]{0,22}(?:轨迹|路径)[^。！？.!?\n]{0,14}(?:连接|连成一体)[^。！？.!?\n]{0,32}(?:点状亮光|点光|亮点)[^。！？.!?\n]{0,18}(?:被拉成|延伸为)[^。！？.!?\n]{0,10}(?:长线|线状亮带)|"
            r"\b(?:moving subject|moving object)\b[^.!?\n]{0,28}\b(?:leaves?|forms?) (?:a )?continuous (?:translucent )?(?:displacement|outline) band\b[^.!?\n]{0,40}\b(?:start|initial position)\b[^.!?\n]{0,20}\b(?:and|to) (?:the )?(?:end|final position)\b[^.!?\n]{0,28}\b(?:connected|linked) by (?:the )?same directional path\b[^.!?\n]{0,40}\bpoint lights?\b[^.!?\n]{0,20}\b(?:stretch|extend) into long lines?\b",
            re.IGNORECASE,
        ),
    ),
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
CAMERA_STABILITY_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "stable": (
        re.compile(
            r"(?:连续帧|相邻帧)(?:之间|中)?[^。！？.!?\n]{0,24}(?:背景锚点|背景垂直线)[^。！？.!?\n]{0,18}(?:保持|停留)[^。！？.!?\n]{0,10}(?:同一|固定)(?:屏幕|画面)位置[^。！？.!?\n]{0,32}地平线[^。！？.!?\n]{0,18}(?:不发生|没有|不存在)[^。！？.!?\n]{0,10}(?:随机|不规则)(?:摆动|晃动|偏移)[^。！？.!?\n]{0,32}(?:取景中心|画面中心)[^。！？.!?\n]{0,20}(?:沿|遵循)[^。！？.!?\n]{0,16}(?:既定|预定)(?:机位|路径|运镜路径)[^。！？.!?\n]{0,16}(?:平滑|稳定)(?:移动|推进|保持)|"
            r"\b(?:consecutive|adjacent) frames\b[^.!?\n]{0,32}\bbackground (?:anchors?|verticals?)\b[^.!?\n]{0,24}\b(?:remain|stay) in (?:the )?same screen position\b[^.!?\n]{0,40}\bhorizon\b[^.!?\n]{0,24}\b(?:has|shows|keeps) no (?:random|irregular) (?:wobble|shake|shift)\b[^.!?\n]{0,40}\b(?:framing|frame) cent(?:er|re)\b[^.!?\n]{0,24}\b(?:moves?|follows?|holds?) smoothly along (?:the )?(?:intended|planned) (?:camera path|path|position)\b",
            re.IGNORECASE,
        ),
    ),
    "handheld": (
        re.compile(
            r"(?:连续帧|相邻帧)(?:之间|中)?[^。！？.!?\n]{0,24}(?:背景锚点|背景垂直线)[^。！？.!?\n]{0,18}(?:产生|出现|保留)[^。！？.!?\n]{0,12}(?:细小|轻微)(?:的)?(?:随机|不规则)(?:位移|偏移|漂移)[^。！？.!?\n]{0,32}地平线[^。！？.!?\n]{0,18}(?:随机|不规则|受控随机)(?:摆动|晃动|偏移)[^。！？.!?\n]{0,32}(?:取景中心|画面中心)[^。！？.!?\n]{0,20}(?:围绕|相对)[^。！？.!?\n]{0,12}(?:主体|主要对象)[^。！？.!?\n]{0,12}(?:轻微|细小)(?:漂移|游移|抖动)|"
            r"\b(?:consecutive|adjacent) frames\b[^.!?\n]{0,32}\bbackground (?:anchors?|verticals?)\b[^.!?\n]{0,24}\b(?:show|retain|undergo) (?:small|subtle) (?:random|irregular) (?:displacements?|shifts?|drift)\b[^.!?\n]{0,40}\bhorizon\b[^.!?\n]{0,24}\b(?:shows?|retains?|has) (?:controlled )?(?:random|irregular) (?:wobble|shake|shift)\b[^.!?\n]{0,40}\b(?:framing|frame) cent(?:er|re)\b[^.!?\n]{0,28}\b(?:drifts?|wanders?|jitters?) slightly around (?:the )?(?:subject|main object)\b",
            re.IGNORECASE,
        ),
    ),
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
FOCAL_PERSPECTIVE_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "wide": (
        re.compile(
            r"(?:近处对象|近景物体|前景主体)[^。！？.!?\n]{0,20}(?:相对|相比|比)[^。！？.!?\n]{0,14}(?:远处背景|远景物体|远景)[^。！？.!?\n]{0,16}(?:明显|显著)(?:放大|更大)[^。！？.!?\n]{0,36}(?:前景|近景)[^。！？.!?\n]{0,14}(?:中景|中距离)[^。！？.!?\n]{0,14}(?:远景|远处背景)[^。！？.!?\n]{0,20}(?:尺度差|大小差)[^。！？.!?\n]{0,14}(?:迅速|明显|显著)(?:拉开|增大)[^。！？.!?\n]{0,36}(?:沿视轴|纵深方向)[^。！？.!?\n]{0,18}(?:空间间距|空间距离|距离)[^。！？.!?\n]{0,12}(?:被)?(?:夸张|明显|显著)(?:延展|拉长)|"
            r"\b(?:near object|foreground object|foreground subject)\b[^.!?\n]{0,28}\bappears? (?:markedly|noticeably|significantly) larger than (?:the )?(?:distant background|far background|far object)\b[^.!?\n]{0,44}\bscale difference\b[^.!?\n]{0,28}\b(?:foreground|near plane)\b[^.!?\n]{0,20}\bmidground\b[^.!?\n]{0,20}\b(?:far background|far plane)\b[^.!?\n]{0,24}\b(?:expands?|opens?|increases?) (?:rapidly|noticeably|significantly)\b[^.!?\n]{0,44}\bspacing along (?:the )?(?:viewing|optical) axis\b[^.!?\n]{0,24}\b(?:is|appears) (?:visibly|strongly|noticeably) (?:stretched|extended|elongated)\b",
            re.IGNORECASE,
        ),
    ),
    "telephoto": (
        re.compile(
            r"(?:近处主体|近景主体|前景对象)[^。！？.!?\n]{0,20}(?:与|和)[^。！？.!?\n]{0,12}(?:远处背景|远景物体|远景)[^。！？.!?\n]{0,18}(?:保持|呈现)[^。！？.!?\n]{0,12}(?:相近|接近|近似)(?:的)?(?:视觉尺度|画面尺度|大小)[^。！？.!?\n]{0,36}(?:前景|近景)[^。！？.!?\n]{0,14}(?:中景|中距离)[^。！？.!?\n]{0,14}(?:远景|远处背景)[^。！？.!?\n]{0,20}(?:层级|空间层)[^。！？.!?\n]{0,14}(?:紧密|密集)(?:叠合|堆叠|贴合)[^。！？.!?\n]{0,36}(?:沿视轴|纵深方向)[^。！？.!?\n]{0,18}(?:空间间距|空间距离|距离)[^。！？.!?\n]{0,12}(?:被)?(?:明显|显著)?压缩|"
            r"\b(?:near subject|foreground subject|foreground object)\b[^.!?\n]{0,28}\b(?:and|with) (?:the )?(?:distant background|far background|far object)\b[^.!?\n]{0,28}\b(?:retain|keep|show) (?:a )?(?:similar|nearly equal|comparable) (?:visual |image )?scale\b[^.!?\n]{0,44}\b(?:foreground|near plane)\b[^.!?\n]{0,20}\bmidground\b[^.!?\n]{0,20}\b(?:far background|far plane)\b[^.!?\n]{0,24}\b(?:stack|overlap|sit) tightly together\b[^.!?\n]{0,44}\bspacing along (?:the )?(?:viewing|optical) axis\b[^.!?\n]{0,24}\b(?:is|appears) (?:visibly|strongly|noticeably) compressed\b",
            re.IGNORECASE,
        ),
    ),
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
# Candidate-only physical feedback. These patterns do not create a user
# constraint; they only expose a model candidate that implies another key
# light direction without naming that direction directly.
KEY_LIGHT_DIRECTION_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "front": (
        re.compile(
            r"(?:主体|人物|角色)[^。！？.!?\n]{0,24}(?:投影|主阴影)[^。！？.!?\n]{0,18}(?:收在|落在|延伸到?)[^。！？.!?\n]{0,8}(?:身后|正后方)|"
            r"\b(?:the )?(?:subject|character)'?s? (?:cast |main )?shadow\b[^.!?\n]{0,32}\b(?:falls?|extends?|stays?) directly behind\b",
            re.IGNORECASE,
        ),
    ),
    "side": (
        re.compile(
            r"(?:面部|脸部|主体|人物)[^。！？.!?\n]{0,24}(?:一侧|一边)[^。！？.!?\n]{0,16}(?:受光|明亮|照亮)[^。！？.!?\n]{0,24}(?:另一侧|另一边|对侧)[^。！？.!?\n]{0,16}(?:入暗|沉入阴影|保持阴影|压暗)|"
            r"\b(?:one side of (?:the )?(?:face|subject|character))\b[^.!?\n]{0,32}\b(?:lit|illuminated|bright)\b[^.!?\n]{0,32}\b(?:opposite|other) side\b[^.!?\n]{0,24}\b(?:shadow|darkness|dark)\b",
            re.IGNORECASE,
        ),
    ),
    "back": (
        re.compile(
            r"(?:主体|人物|角色|面部|脸部)[^。！？.!?\n]{0,24}(?:迎镜头一面|正面|面部)[^。！？.!?\n]{0,16}(?:沉入阴影|保持阴影|相对压暗)[^。！？.!?\n]{0,28}(?:轮廓|边缘)[^。！？.!?\n]{0,16}(?:亮线|高光|勾亮|发亮)|"
            r"\b(?:front|camera-facing side) of (?:the )?(?:subject|character|face)\b[^.!?\n]{0,32}\b(?:remains?|falls?|stays?) (?:in )?(?:shadow|dark)\b[^.!?\n]{0,40}\b(?:rim|edge|silhouette) (?:highlight|highlights|light|glow)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:主体|人物|角色)[^。！？.!?\n]{0,24}(?:投影|主阴影)[^。！？.!?\n]{0,18}(?:朝向|延伸向|伸向)[^。！？.!?\n]{0,8}(?:镜头|前景)|"
            r"\b(?:the )?(?:subject|character)'?s? (?:cast |main )?shadow\b[^.!?\n]{0,32}\b(?:extends?|reaches?|falls?) toward (?:the )?(?:camera|foreground)\b",
            re.IGNORECASE,
        ),
    ),
    "top": (
        re.compile(
            r"(?:眼窝|下颌|眉骨)[^。！？.!?\n]{0,18}(?:下方|下侧)?[^。！？.!?\n]{0,12}(?:形成|留下|压出)[^。！？.!?\n]{0,10}(?:向下|垂直)?(?:阴影|暗部)|"
            r"\b(?:eye sockets?|brow ridge|under (?:the )?chin)\b[^.!?\n]{0,28}\b(?:cast|form|hold|show) (?:a )?(?:downward |vertical )?(?:shadow|shadows|darkness)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:脚下|足下|主体正下方)[^。！？.!?\n]{0,18}(?:阴影|投影)[^。！？.!?\n]{0,16}(?:紧凑|短促|收束|集中)|"
            r"\b(?:compact|short|tight) (?:cast )?shadow\b[^.!?\n]{0,24}\b(?:directly )?(?:beneath|under) (?:the )?(?:feet|subject|character)\b",
            re.IGNORECASE,
        ),
    ),
}
_COMPLEX_LIGHT_DIRECTION_RE = re.compile(
    r"(?:侧逆光|侧后方(?:主)?光|三点布光|交叉布光|双侧布光|多方向布光|多灯位|"
    r"主光[^，,；;。！？.!?\n]{0,36}(?:补光|轮廓光)|(?:补光|轮廓光)[^，,；;。！？.!?\n]{0,36}主光|"
    r"three-point lighting|cross lighting|multiple light directions|key light[^;.!?\n]{0,48}(?:fill light|rim light)|"
    r"(?:fill light|rim light)[^;.!?\n]{0,48}key light)",
    flags=re.IGNORECASE,
)
EXPOSURE_KEY_MARKERS: dict[str, tuple[str, ...]] = {
    "high_key": (
        "明亮高调棚拍", "白色高调棚拍", "高调人像摄影", "高调摄影", "高调照明",
        "高调画面", "高键照明", "高键布光", "高键光",
        "high-key portrait photography", "high key portrait photography",
        "high-key photography", "high key photography", "high-key lighting", "high key lighting",
        "bright airy exposure", "bright and airy lighting",
    ),
    "low_key": (
        "暗调低键布光", "暗调低键", "低调人像摄影", "低调摄影", "低调照明",
        "低调画面", "低键照明", "低键布光", "低键光",
        "low-key portrait photography", "low key portrait photography",
        "low-key photography", "low key photography", "low-key lighting", "low key lighting",
        "dark low-key exposure", "dark low key exposure",
    ),
}
_EXPOSURE_KEY_LABELS = {
    "high_key": "高调/高键曝光",
    "low_key": "低调/低键曝光",
}
EXPOSURE_KEY_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "high_key": (
        re.compile(
            r"(?:画面|图像)(?:的)?大部分区域[^。！？.!?\n]{0,18}(?:分布|落在|处于)[^。！？.!?\n]{0,12}(?:中高亮度|中高明度|亮部与中间调)[^。！？.!?\n]{0,36}(?:深阴影|暗部)[^。！？.!?\n]{0,16}(?:只占|仅占)[^。！？.!?\n]{0,10}(?:很小|少量|较小)(?:面积|区域)[^。！？.!?\n]{0,18}(?:且|并)(?:仍)?保留(?:可辨)?(?:层次|细节)[^。！？.!?\n]{0,36}(?:黑位|黑色基准)[^。！？.!?\n]{0,16}(?:整体)?(?:抬高|抬升)[^。！？.!?\n]{0,16}(?:但|同时)[^。！？.!?\n]{0,12}(?:高光|亮部)[^。！？.!?\n]{0,12}(?:不过曝|不溢出|保持不过曝)|"
            r"\bmost of (?:the )?(?:frame|image)\b[^.!?\n]{0,28}\b(?:occupies?|falls? within|sits? in) (?:the )?(?:upper midtones?|upper-middle tones?|highlights? and midtones?)\b[^.!?\n]{0,44}\b(?:deep shadows?|dark regions?)\b[^.!?\n]{0,24}\b(?:cover|occupy) only (?:a )?(?:small|limited) area\b[^.!?\n]{0,24}\bwhile retaining (?:readable )?(?:detail|tonal separation)\b[^.!?\n]{0,44}\bblack (?:level|point)\b[^.!?\n]{0,20}\b(?:is )?(?:lifted|raised)\b[^.!?\n]{0,28}\b(?:without|while avoiding) (?:highlight )?(?:clipping|overexposure)\b",
            re.IGNORECASE,
        ),
    ),
    "low_key": (
        re.compile(
            r"(?:画面|图像)(?:的)?大部分区域[^。！？.!?\n]{0,18}(?:停留|落在|处于)[^。！？.!?\n]{0,12}(?:低亮度|低明度|暗部)[^。！？.!?\n]{0,36}(?:亮部|高光)[^。！？.!?\n]{0,16}(?:只集中|仅集中|限制)[^。！？.!?\n]{0,14}(?:少量|局部|小面积)(?:受光区域|亮区|区域)[^。！？.!?\n]{0,36}(?:阴影|暗部)[^。！？.!?\n]{0,16}(?:占据|覆盖)[^。！？.!?\n]{0,10}(?:大面积|大部分画面|主要面积)[^。！？.!?\n]{0,18}(?:且|并)(?:仍)?保留(?:可辨)?(?:层次|细节)|"
            r"\bmost of (?:the )?(?:frame|image)\b[^.!?\n]{0,28}\b(?:remains?|sits?|falls?) in (?:the )?(?:low luminance|low brightness|dark tonal) (?:values?|range)\b[^.!?\n]{0,44}\b(?:highlights?|bright regions?)\b[^.!?\n]{0,24}\b(?:are|remain) (?:confined|limited) to (?:a )?(?:small|few) (?:lit |bright )?areas?\b[^.!?\n]{0,44}\bshadows?\b[^.!?\n]{0,20}\b(?:occupy|cover) (?:a )?(?:large|dominant) area\b[^.!?\n]{0,24}\bwhile retaining (?:readable )?(?:detail|tonal separation)\b",
            re.IGNORECASE,
        ),
    ),
}
_COMPLEX_EXPOSURE_KEY_RE = re.compile(
    r"(?:高低调(?:并置|对比|分区)|明暗分区曝光|局部高调[^，,；;。！？.!?\n]{0,32}局部低调|"
    r"局部低调[^，,；;。！？.!?\n]{0,32}局部高调|split exposure|mixed high[- ]key and low[- ]key|"
    r"high[- ]key[^;.!?\n]{0,48}low[- ]key|low[- ]key[^;.!?\n]{0,48}high[- ]key)",
    flags=re.IGNORECASE,
)
CONTRAST_LEVEL_MARKERS: dict[str, tuple[str, ...]] = {
    "high": (
        "高对比戏剧光", "高对比滤镜", "高对比黑白", "高反差黑色电影", "高反差照明",
        "高反差画面", "强烈明暗对比", "强对比照明", "强对比", "高对比",
        "high-contrast film noir", "high contrast film noir", "high-contrast lighting",
        "high contrast lighting", "high-contrast image", "high contrast image",
        "strong tonal contrast", "high contrast",
    ),
    "low": (
        "整体低对比", "柔和低对比画面", "低对比画面", "低对比照明", "低反差照明",
        "低反差画面", "柔和反差", "柔和对比度",
        "overall low contrast", "low-contrast lighting", "low contrast lighting",
        "low-contrast image", "low contrast image", "soft tonal contrast",
    ),
}
_CONTRAST_LEVEL_LABELS = {
    "high": "高对比/高反差",
    "low": "低对比/低反差",
}
CONTRAST_LEVEL_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "high": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,22}(?:最亮部|亮部)[^。！？.!?\n]{0,18}(?:最暗部|暗部)[^。！？.!?\n]{0,18}(?:保持|形成|拉开)[^。！？.!?\n]{0,12}(?:很大|较大|宽广|强烈)(?:的)?(?:明度|亮度|色调)?跨度[^。！？.!?\n]{0,32}(?:中间调|中间灰阶)[^。！？.!?\n]{0,16}(?:只占|限制在|压缩到)[^。！？.!?\n]{0,12}(?:狭窄|很窄|较窄|少量)(?:的)?(?:范围|区域)?[^。！？.!?\n]{0,32}(?:亮度|明度)?直方图[^。！？.!?\n]{0,22}(?:同时)?(?:延伸|展开|覆盖|触及)[^。！？.!?\n]{0,16}(?:亮暗|明暗|高低)(?:两端|双端)|"
            r"\b(?:the )?(?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,28}\b(?:brightest|lightest) (?:area|region|values?|tones?)\b[^.!?\n]{0,30}\b(?:darkest|deepest) (?:area|region|values?|tones?)\b[^.!?\n]{0,36}\b(?:maintain|form|span|show) (?:a )?(?:very |substantially )?(?:wide|large|strong) (?:luminance|brightness|tonal) (?:range|span)\b[^.!?\n]{0,36}\bmidtones?\b[^.!?\n]{0,24}\b(?:occupy|cover|are confined to) (?:a )?(?:narrow|limited|small) (?:range|band)\b[^.!?\n]{0,36}\b(?:luminance|brightness) histogram\b[^.!?\n]{0,28}\b(?:extends?|reaches?|stretches?) (?:to|toward) both (?:the )?(?:bright and dark|light and dark|high and low) ends\b",
            re.IGNORECASE,
        ),
    ),
    "low": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,22}(?:亮部|最亮部)[^。！？.!?\n]{0,18}(?:暗部|最暗部)[^。！？.!?\n]{0,18}(?:保持|形成|压缩为)[^。！？.!?\n]{0,12}(?:较小|很小|狭窄|有限)(?:的)?(?:明度|亮度|色调)?跨度[^。！？.!?\n]{0,32}(?:中间调|中间灰阶)[^。！？.!?\n]{0,16}(?:覆盖|占据|铺开)[^。！？.!?\n]{0,12}(?:宽广|很宽|较宽|大部分)(?:的)?(?:范围|区域)?[^。！？.!?\n]{0,32}(?:亮度|明度)?直方图[^。！？.!?\n]{0,22}(?:集中|聚集|收拢)[^。！？.!?\n]{0,12}(?:在|于)?(?:中部|中央|中间)[^。！？.!?\n]{0,18}(?:且|并|同时)[^。！？.!?\n]{0,8}(?:两端|亮暗端|明暗端)[^。！？.!?\n]{0,12}(?:保留|留有)[^。！？.!?\n]{0,8}(?:余量|空间)|"
            r"\b(?:the )?(?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,28}\b(?:bright|light|brightest) (?:areas?|regions?|values?|tones?)\b[^.!?\n]{0,30}\b(?:dark|darkest) (?:areas?|regions?|values?|tones?)\b[^.!?\n]{0,36}\b(?:maintain|form|show) (?:a )?(?:relatively )?(?:small|narrow|limited) (?:luminance|brightness|tonal) (?:range|span)\b[^.!?\n]{0,36}\bmidtones?\b[^.!?\n]{0,24}\b(?:occupy|cover|span) (?:a )?(?:broad|wide|large) (?:range|band)\b[^.!?\n]{0,36}\b(?:luminance|brightness) histogram\b[^.!?\n]{0,28}\b(?:is |remains? )?(?:centered|concentrated|clustered) in (?:the )?(?:middle|center)\b[^.!?\n]{0,28}\b(?:leaving|with) (?:headroom|room|margin) at both ends\b",
            re.IGNORECASE,
        ),
    ),
}
_COMPLEX_CONTRAST_RE = re.compile(
    r"(?:局部对比|局部反差|分区对比|分区反差|对比度分区|高动态范围|\bHDR\b|"
    r"镜(?:像|面)[^，,；;。！？.!?\n]{0,28}低对比|倒影[^，,；;。！？.!?\n]{0,28}低对比|"
    r"(?:前景|背景|反射|折射)[^，,；;。！？.!?\n]{0,28}低对比|"
    r"local contrast|zonal contrast|split contrast|high dynamic range|"
    r"(?:reflection|foreground|background)[^;.!?\n]{0,36}low contrast)",
    flags=re.IGNORECASE,
)
SATURATION_LEVEL_MARKERS: dict[str, tuple[str, ...]] = {
    "high": (
        "高饱和感官色调", "高饱和图形化", "高饱和色彩", "高饱和画面", "高饱和滤镜",
        "鲜艳饱和色彩", "鲜艳色彩", "高饱和",
        "high-saturation palette", "high saturation palette", "highly saturated colors",
        "highly saturated colours", "high saturation", "vibrant saturated colors",
        "vibrant saturated colours", "vivid saturated colors", "vivid saturated colours",
    ),
    "low": (
        "低饱和黑金胶片", "低饱和亲密影像", "克制低饱和电影", "低饱和冷灰",
        "低饱和霓虹", "低饱和滤镜", "低饱和情绪", "低饱和色彩", "低饱和画面",
        "去饱和处理", "去饱和色彩", "去饱和画面", "低饱和",
        "low-saturation palette", "low saturation palette", "low-saturation colors",
        "low saturation colors", "low-saturation colours", "low saturation colours",
        "desaturated palette", "desaturated colors", "desaturated colours",
        "muted color palette", "muted colour palette", "muted colors", "muted colours",
    ),
}
_SATURATION_LEVEL_LABELS = {
    "high": "高饱和",
    "low": "低饱和/去饱和",
}
SATURATION_LEVEL_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "high": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:大多数|大部分)(?:彩色区域|有色区域|颜色)[^。！？.!?\n]{0,18}(?:保持|呈现)[^。！？.!?\n]{0,10}(?:较高|很高|强烈)(?:的)?(?:综合色度|色彩浓度|色度)[^。！？.!?\n]{0,32}(?:综合色度|色度)(?:直方图|分布)[^。！？.!?\n]{0,20}(?:集中|聚集|落在)[^。！？.!?\n]{0,12}(?:中高值区|高值区|中高范围)[^。！？.!?\n]{0,32}(?:鲜艳颜色|高色度颜色|浓艳色彩)[^。！？.!?\n]{0,20}(?:覆盖|占据)[^。！？.!?\n]{0,18}(?:主体与环境|主体和环境|主要色块)[^。！？.!?\n]{0,32}(?:中性灰|中性色)[^。！？.!?\n]{0,18}(?:只占|仅占)[^。！？.!?\n]{0,12}(?:少量|很小|较小)(?:必要)?(?:区域|面积)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bmost (?:colou?red|chromatic) regions?\b[^.!?\n]{0,28}\b(?:maintain|show|retain) (?:a )?(?:high|strong) overall chroma\b[^.!?\n]{0,40}\bchroma (?:histogram|distribution)\b[^.!?\n]{0,28}\b(?:clusters?|concentrates?|falls?) in (?:the )?(?:mid-to-high|middle-to-high|high) range\b[^.!?\n]{0,44}\bvivid colou?rs?\b[^.!?\n]{0,24}\b(?:cover|occupy) (?:the )?(?:main colou?r masses|main regions)\b[^.!?\n]{0,44}\bneutral gr[ae]y\b[^.!?\n]{0,24}\b(?:occupies|covers) only (?:a )?(?:small|limited) (?:necessary )?area\b",
            re.IGNORECASE,
        ),
    ),
    "low": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:大多数|大部分)(?:彩色区域|有色区域|颜色)[^。！？.!?\n]{0,18}(?:靠近|接近|收拢于)[^。！？.!?\n]{0,10}(?:中性灰轴|灰度轴|中性色轴)[^。！？.!?\n]{0,32}(?:综合色度|色度)(?:直方图|分布)[^。！？.!?\n]{0,20}(?:集中|聚集|落在)[^。！？.!?\n]{0,12}(?:低值区|低值范围|低色度区)[^。！？.!?\n]{0,32}(?:鲜艳颜色|高色度颜色|浓艳色彩)[^。！？.!?\n]{0,18}(?:只占|仅占|限制在)[^。！？.!?\n]{0,12}(?:少量|很小|较小)(?:必要)?(?:区域|面积)[^。！？.!?\n]{0,28}(?:同时|且|并)[^。！？.!?\n]{0,10}(?:仍)?保留[^。！？.!?\n]{0,12}(?:可辨|清楚)(?:的)?(?:主色相|色相)(?:关系|差异)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bmost (?:colou?red|chromatic) regions?\b[^.!?\n]{0,28}\b(?:stay|remain|sit) close to (?:the )?neutral gr[ae]y axis\b[^.!?\n]{0,40}\bchroma (?:histogram|distribution)\b[^.!?\n]{0,28}\b(?:clusters?|concentrates?|falls?) in (?:the )?low range\b[^.!?\n]{0,44}\bvivid colou?rs?\b[^.!?\n]{0,24}\b(?:occupy|cover) only (?:a )?(?:small|limited) (?:necessary )?area\b[^.!?\n]{0,44}\b(?:primary|main) hue relationships?\b[^.!?\n]{0,24}\b(?:remain|stay) (?:distinguishable|readable|discernible)\b",
            re.IGNORECASE,
        ),
    ),
}
_SELECTIVE_SATURATION_RE = re.compile(
    r"(?:局部(?:高|低|去)饱和|选择性饱和|饱和度分区|局部彩色|选择性色彩|色彩点缀|"
    r"(?:环境|背景)[^。！？.!?\n]{0,48}低饱和[^。！？.!?\n]{0,48}(?:主体|人物|肤色)|"
    r"(?:主体|人物|肤色)[^。！？.!?\n]{0,48}(?:自然|鲜明|独立)[^。！？.!?\n]{0,48}(?:环境|背景)[^。！？.!?\n]{0,32}低饱和|"
    r"selective saturation|selectively saturated|saturation zoning|color pop|colour pop|"
    r"(?:background|environment)[^;.!?\n]{0,48}(?:low saturation|desaturated)[^;.!?\n]{0,48}(?:subject|skin tone))",
    flags=re.IGNORECASE,
)
IMAGE_GRAIN_MARKERS: dict[str, tuple[str, ...]] = {
    "grainy": (
        "35mm胶片颗粒", "胶片颗粒", "柔和颗粒感", "颗粒质感", "颗粒感",
        "VHS噪点", "模拟噪点", "自然噪点", "粗粝噪点", "复古噪点",
        "35mm film grain", "film grain", "analog grain", "analogue grain",
        "grainy texture", "grainy image", "visible grain", "VHS noise",
    ),
    "clean": (
        "干净无颗粒画面", "无颗粒数字画面", "纯净数字成像", "干净数字质感",
        "数字无噪点", "无胶片颗粒", "无可见颗粒", "低噪点画面", "无颗粒",
        "noise-free digital image", "clean digital image", "clean digital rendering",
        "grain-free image", "no film grain", "no visible grain",
    ),
}
_IMAGE_GRAIN_LABELS = {
    "grainy": "胶片颗粒/可见噪点",
    "clean": "干净无颗粒数字成像",
}
IMAGE_GRAIN_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "grainy": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:平坦色块|均匀色块|平滑色块)[^。！？.!?\n]{0,16}(?:和|与|及)[^。！？.!?\n]{0,8}(?:中间调区域|中间调|灰阶区域)[^。！？.!?\n]{0,20}(?:分布|出现|保留)[^。！？.!?\n]{0,14}(?:细小|微细|可见)(?:的)?(?:随机)?(?:亮度|明度)?(?:颗粒|斑点|噪点)[^。！？.!?\n]{0,32}(?:颗粒尺度|颗粒大小|噪点尺度)[^。！？.!?\n]{0,20}(?:在)?(?:主体与背景|主体和背景|前景与背景)[^。！？.!?\n]{0,18}(?:保持|维持)[^。！？.!?\n]{0,10}(?:一致|统一|相近)[^。！？.!?\n]{0,32}(?:轮廓边缘|物体边缘|主体边缘)[^。！？.!?\n]{0,20}(?:仍)?(?:可见|保留|呈现)[^。！？.!?\n]{0,18}(?:连续但不规则|连续而随机|不规则连续)(?:的)?(?:颗粒起伏|噪点起伏|颗粒扰动)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bflat colou?r (?:fields?|areas?|blocks?)\b[^.!?\n]{0,24}\b(?:and|with) midtone regions?\b[^.!?\n]{0,28}\b(?:contain|show|retain) fine random luminance (?:speckles?|grain|noise)\b[^.!?\n]{0,44}\bgrain (?:size|scale)\b[^.!?\n]{0,28}\b(?:stays?|remains?) consistent between (?:the )?subject and (?:the )?background\b[^.!?\n]{0,44}\bcontour edges?\b[^.!?\n]{0,28}\b(?:retain|show|carry) continuous but irregular grain fluctuations?\b",
            re.IGNORECASE,
        ),
    ),
    "clean": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:平坦色块|均匀色块|平滑色块)[^。！？.!?\n]{0,16}(?:和|与|及)[^。！？.!?\n]{0,8}(?:中间调区域|中间调|灰阶区域)[^。！？.!?\n]{0,20}(?:保持|呈现)[^。！？.!?\n]{0,12}(?:均匀纯净|平滑纯净|均一干净)[^。！？.!?\n]{0,32}(?:不出现|没有|不存在)[^。！？.!?\n]{0,14}(?:随机)?(?:亮度|明度)[^。！？.!?\n]{0,10}(?:或|与)[^。！？.!?\n]{0,8}(?:色彩|彩色)(?:斑点|噪点)[^。！？.!?\n]{0,32}(?:主体与背景|主体和背景|前景与背景)[^。！？.!?\n]{0,18}(?:的)?(?:轮廓边缘|物体边缘)[^。！？.!?\n]{0,20}(?:保持|维持)[^。！？.!?\n]{0,14}(?:连续平滑|完整连续)[^。！？.!?\n]{0,18}(?:且|并|而)[^。！？.!?\n]{0,8}(?:不被|没有被)[^。！？.!?\n]{0,10}(?:噪点|随机斑点|颗粒)[^。！？.!?\n]{0,8}(?:打断|干扰|扰乱)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bflat colou?r (?:fields?|areas?|blocks?)\b[^.!?\n]{0,24}\b(?:and|with) midtone regions?\b[^.!?\n]{0,28}\b(?:remain|stay|appear) uniformly clean\b[^.!?\n]{0,40}\bno random luminance or colou?r speckles? (?:appear|are present)\b[^.!?\n]{0,44}\bcontour edges? of (?:the )?subject and (?:the )?background\b[^.!?\n]{0,32}\b(?:stay|remain) continuous and smooth without noise interruptions?\b",
            re.IGNORECASE,
        ),
    ),
}
_SELECTIVE_IMAGE_GRAIN_RE = re.compile(
    r"(?:局部(?:颗粒|噪点)|颗粒(?:感)?分区|噪点分区|扫描纹理|印刷网点|半色调网点|"
    r"(?:背景|环境|边缘|阴影)[^。！？.!?\n]{0,48}(?:颗粒|噪点)[^。！？.!?\n]{0,48}(?:主体|人物|面部|肤色)[^。！？.!?\n]{0,32}(?:干净|清晰|纯净)|"
    r"(?:主体|人物|面部|肤色)[^。！？.!?\n]{0,48}(?:干净|清晰|纯净)[^。！？.!?\n]{0,48}(?:背景|环境|边缘|阴影)[^。！？.!?\n]{0,32}(?:颗粒|噪点)|"
    r"local(?:ized)? (?:film )?grain|selective grain|grain zoning|halftone dots|print dots|"
    r"(?:background|environment)[^;.!?\n]{0,48}(?:grain|noise)[^;.!?\n]{0,48}(?:subject|face|skin)[^;.!?\n]{0,32}(?:clean|clear))",
    flags=re.IGNORECASE,
)
_NONVISUAL_GRAIN_RE = re.compile(
    r"(?:(?:谷物|粮食|砂糖|食盐|药粉|粉末|砂石|泥土|土壤|药片|食材|原料)"
    r"[^，,；;。！？.!?\n]{0,20}(?:颗粒感|颗粒质感)|"
    r"(?:颗粒感|颗粒质感)[^，,；;。！？.!?\n]{0,20}"
    r"(?:谷物|粮食|砂糖|食盐|药粉|粉末|砂石|泥土|土壤|药片|食材|原料))",
    flags=re.IGNORECASE,
)
IMAGE_SHARPNESS_MARKERS: dict[str, tuple[str, ...]] = {
    "sharp": (
        "整体锐利清晰", "全画面锐利", "高锐度成像", "锐利清晰成像", "边缘锐利清晰",
        "清晰锐利画面", "超清晰画面", "锐利细节", "锐利焦点", "高锐度", "锐利", "清晰",
        "razor-sharp image", "razor sharp image", "tack-sharp image", "tack sharp image",
        "crisp sharp image", "high image sharpness", "sharp rendering", "sharp focus",
    ),
    "soft_focus": (
        "整体柔焦画面", "全画面柔化", "朦胧柔焦", "柔焦滤镜", "软焦镜头",
        "柔焦成像", "柔焦效果", "全局柔焦", "整体软焦", "柔焦",
        "soft-focus image", "soft focus image", "dreamy soft focus", "diffusion filter",
        "soft-focus rendering", "soft focus rendering",
    ),
}
_IMAGE_SHARPNESS_LABELS = {
    "sharp": "锐利清晰成像",
    "soft_focus": "整体柔焦/软焦成像",
}
IMAGE_SHARPNESS_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "sharp": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体与背景|主体和背景|前景与背景)[^。！？.!?\n]{0,18}(?:的)?(?:轮廓|边缘)[^。！？.!?\n]{0,18}(?:具有|保持|呈现)[^。！？.!?\n]{0,12}(?:狭窄|很窄|短促)(?:且|而|、)?(?:明确|清楚|清晰)(?:的)?(?:亮度|明度)(?:过渡|变化带)[^。！？.!?\n]{0,32}(?:细线|细小线条|细密线条)[^。！？.!?\n]{0,18}(?:与|和)[^。！？.!?\n]{0,10}(?:相邻纹理|邻近纹理|周围纹理)[^。！？.!?\n]{0,18}(?:保持|维持)[^。！？.!?\n]{0,12}(?:清楚|明确|完整)(?:分离|分开)[^。！？.!?\n]{0,32}(?:微细材质|微小材质|微纹理)(?:边缘|轮廓)[^。！？.!?\n]{0,22}(?:呈现|保持|保留)[^。！？.!?\n]{0,16}(?:稳定|明确)(?:的)?(?:局部反差|边缘反差|微反差)[^。！？.!?\n]{0,18}(?:且|并|同时)[^。！？.!?\n]{0,10}(?:没有|不出现|不产生)[^。！？.!?\n]{0,10}(?:扩散光晕|边缘光晕|柔化晕染)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,36}\bcontours? of (?:the )?subject and (?:the )?background\b[^.!?\n]{0,32}\b(?:have|show|retain) narrow,? well-defined luminance transitions?\b[^.!?\n]{0,44}\bfine lines?\b[^.!?\n]{0,28}\bremain separated from (?:the )?(?:neighboring|adjacent) textures?\b[^.!?\n]{0,44}\bmicrotexture edges?\b[^.!?\n]{0,28}\b(?:retain|show) stable local contrast\b[^.!?\n]{0,28}\bwithout (?:diffusion|edge) halos?\b",
            re.IGNORECASE,
        ),
    ),
    "soft_focus": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体与背景|主体和背景|前景与背景)[^。！？.!?\n]{0,18}(?:的)?(?:轮廓|边缘)[^。！？.!?\n]{0,18}(?:具有|保持|呈现)[^。！？.!?\n]{0,12}(?:宽缓|宽而平缓|较宽)(?:且|而|、)?(?:连续|平滑)(?:的)?(?:亮度|明度)(?:过渡|变化带)[^。！？.!?\n]{0,32}(?:细线|细小线条|细密线条)[^。！？.!?\n]{0,18}(?:与|和)[^。！？.!?\n]{0,10}(?:相邻纹理|邻近纹理|周围纹理)[^。！？.!?\n]{0,18}(?:轻微|均匀)(?:融合|混合|相融)[^。！？.!?\n]{0,32}(?:微细材质|微小材质|微纹理)(?:边缘|轮廓)[^。！？.!?\n]{0,22}(?:的)?(?:局部反差|边缘反差|微反差)[^。！？.!?\n]{0,18}(?:被)?(?:均匀|整体)(?:压低|降低|减弱)[^。！？.!?\n]{0,20}(?:并|且|从而)[^。！？.!?\n]{0,10}(?:形成|呈现)[^。！？.!?\n]{0,10}(?:受控柔化|均匀柔化|柔和扩散)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,36}\bcontours? of (?:the )?subject and (?:the )?background\b[^.!?\n]{0,32}\b(?:have|show|retain) broad,? gradual luminance transitions?\b[^.!?\n]{0,44}\bfine lines?\b[^.!?\n]{0,28}\bblend slightly (?:into|with) (?:the )?(?:neighboring|adjacent) textures?\b[^.!?\n]{0,44}\blocal contrast at microtexture edges?\b[^.!?\n]{0,32}\b(?:is |remains? )?uniformly reduced\b[^.!?\n]{0,28}\b(?:into|to form) controlled softness\b",
            re.IGNORECASE,
        ),
    ),
}
_GENERIC_IMAGE_SHARPNESS_MARKERS = {"锐利", "清晰", "柔焦"}
_IMAGE_SHARPNESS_GLOBAL_SCOPE_RE = re.compile(
    r"(?:整体|全局|全画面|画面|图像|影像|成像|照片|摄影|渲染|镜头|滤镜|焦点|锐度|清晰度|"
    r"image|render(?:ing)?|photo(?:graphy)?|camera|lens|filter|focus|sharpness)",
    flags=re.IGNORECASE,
)
_IMAGE_SHARPNESS_PREFIX_SCOPE_RE = re.compile(
    r"(?:整体|全局|全画面|画面|图像|影像|成像|照片|摄影|渲染|镜头|滤镜|焦点|锐度|清晰度|"
    r"保持|采用|使用|要求|固定为|设为|改为|改成|转为|变为)"
    r"[^，,；;。！？.!?\n]{0,14}$",
    flags=re.IGNORECASE,
)
_IMAGE_SHARPNESS_SUFFIX_SCOPE_RE = re.compile(
    r"^(?:画面|图像|影像|成像|效果|滤镜|质感|细节|边缘|焦点|锐度|清晰度|"
    r"image|render(?:ing)?|effect|filter|detail|edge|focus|sharpness)",
    flags=re.IGNORECASE,
)
_SELECTIVE_IMAGE_SHARPNESS_RE = re.compile(
    r"(?:局部(?:锐化|柔化|柔焦)|选择性锐化|锐度分区|清晰度分区|皮肤(?:柔化|磨皮|柔焦)|"
    r"(?:背景|前景|边缘|倒影|反射)[^。！？.!?\n]{0,40}(?:虚化|模糊|柔焦)|"
    r"(?:主体|人物|面部|眼睛|产品)[^。！？.!?\n]{0,48}(?:锐利|清晰)[^。！？.!?\n]{0,48}(?:背景|前景)[^。！？.!?\n]{0,32}(?:虚化|模糊|柔焦)|"
    r"(?:背景|前景)[^。！？.!?\n]{0,48}(?:虚化|模糊|柔焦)[^。！？.!?\n]{0,48}(?:主体|人物|面部|眼睛|产品)[^。！？.!?\n]{0,32}(?:锐利|清晰)|"
    r"浅景深|背景虚化|前景虚化|散景|运动模糊|动态模糊|慢门拖影|长曝光拖影|追焦|"
    r"local(?:ized)? sharpen(?:ing)?|selective sharpen(?:ing)?|sharpness zoning|skin softening|"
    r"(?:background|foreground)[^;.!?\n]{0,48}(?:blur|soft focus)[^;.!?\n]{0,48}(?:subject|face|eyes|product)[^;.!?\n]{0,32}(?:sharp|crisp)|"
    r"(?:subject|face|eyes|product)[^;.!?\n]{0,48}(?:sharp|crisp)[^;.!?\n]{0,48}(?:background|foreground)[^;.!?\n]{0,32}(?:blur|soft focus)|"
    r"shallow depth of field|background blur|foreground blur|motion blur|rack focus|focus pull)",
    flags=re.IGNORECASE,
)
DETAIL_DENSITY_MARKERS: dict[str, tuple[str, ...]] = {
    "high": (
        "超高细节", "高细节", "超精细", "极致纹理", "材质细节丰富", "细节密度高",
        "高密度细节", "复杂精细纹理", "细密纹理", "丰富纹理细节",
        "ultra-detailed", "ultra detailed", "highly detailed", "extremely detailed",
        "high detail density", "dense visual detail", "intricate texture detail",
        "rich texture detail",
    ),
    "low": (
        "整体低细节", "低细节渲染", "简化低细节", "简洁低细节", "细节简化",
        "减少纹理细节", "无复杂纹理", "扁平简化造型", "简化渲染", "低细节",
        "minimal detail", "low-detail rendering", "low detail rendering", "simplified rendering",
        "reduced texture detail", "no intricate textures", "clean simple shapes",
    ),
}
_DETAIL_DENSITY_LABELS = {
    "high": "高细节/高密度纹理",
    "low": "简化/低细节渲染",
}
DETAIL_DENSITY_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "high": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:单位区域|每个局部区域|单位画幅)[^。！？.!?\n]{0,18}(?:内|中)[^。！？.!?\n]{0,8}(?:保留|包含|呈现)[^。！？.!?\n]{0,12}(?:大量|密集|许多)(?:彼此)?(?:独立|可分辨)(?:的)?(?:小尺度结构|微小结构|细小结构)[^。！？.!?\n]{0,32}(?:主纹理|一级纹理|主要纹理)[^。！？.!?\n]{0,18}(?:继续|能够|仍可)(?:分解|拆分|展开)[^。！？.!?\n]{0,16}(?:出|为)[^。！？.!?\n]{0,12}(?:次级和三级纹理|二级与三级纹理|多级细纹|多层次细纹)[^。！？.!?\n]{0,32}(?:简化留白区域|低信息区域|简洁区域)[^。！？.!?\n]{0,18}(?:只占|仅占)[^。！？.!?\n]{0,12}(?:少量|很小|较小)(?:面积|区域)[^。！？.!?\n]{0,24}(?:且|并|同时)[^。！？.!?\n]{0,10}(?:不吞并|不丢失|不省略)[^。！？.!?\n]{0,12}(?:关键材质信息|关键纹理信息|核心材质特征)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\b(?:each|every) unit area\b[^.!?\n]{0,28}\b(?:retains?|contains?|shows?) many independent small-scale structures?\b[^.!?\n]{0,44}\bprimary textures?\b[^.!?\n]{0,28}\b(?:split|break down|resolve) into secondary and tertiary texture layers?\b[^.!?\n]{0,44}\bsimplified (?:blank|low-information) regions?\b[^.!?\n]{0,28}\b(?:occupy|cover) only (?:a )?(?:small|limited) area\b[^.!?\n]{0,36}\bwithout (?:erasing|losing|omitting) key material information\b",
            re.IGNORECASE,
        ),
    ),
    "low": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:单位区域|每个局部区域|单位画幅)[^。！？.!?\n]{0,18}(?:内|中)[^。！？.!?\n]{0,8}(?:只保留|仅保留|限制为)[^。！？.!?\n]{0,12}(?:少量|有限)(?:的)?(?:必要结构|核心结构|主要结构)[^。！？.!?\n]{0,32}(?:主纹理|一级纹理|主要纹理)[^。！？.!?\n]{0,18}(?:不再|不会|无需)(?:分解|拆分|展开)[^。！？.!?\n]{0,16}(?:为|出)?[^。！？.!?\n]{0,10}(?:多级细纹|二级与三级纹理|次级和三级纹理|多层次细纹)[^。！？.!?\n]{0,32}(?:简化留白区域|低信息区域|简洁区域)[^。！？.!?\n]{0,18}(?:占据|覆盖)[^。！？.!?\n]{0,12}(?:较大|大部分|宽广)(?:的)?(?:面积|区域)[^。！？.!?\n]{0,24}(?:但|同时|且)[^。！？.!?\n]{0,10}(?:主体轮廓|主要轮廓)[^。！？.!?\n]{0,16}(?:和|与)[^。！？.!?\n]{0,10}(?:关键识别特征|核心识别特征)[^。！？.!?\n]{0,14}(?:保持|仍然)?(?:完整|可辨|清楚)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\b(?:each|every) unit area\b[^.!?\n]{0,28}\b(?:retains?|keeps?|contains?) only (?:a )?(?:few|limited number of) necessary structures?\b[^.!?\n]{0,44}\bprimary textures?\b[^.!?\n]{0,28}\bno longer (?:split|break down|resolve) into multiple fine layers?\b[^.!?\n]{0,44}\bsimplified (?:blank|low-information) regions?\b[^.!?\n]{0,28}\b(?:occupy|cover) (?:a )?(?:large|broad) area\b[^.!?\n]{0,40}\b(?:while|but) (?:the )?subject contours? and key identifying features? remain (?:intact|readable|recognizable)\b",
            re.IGNORECASE,
        ),
    ),
}
_SELECTIVE_DETAIL_DENSITY_RE = re.compile(
    r"(?:局部(?:高|低)细节|选择性细化|细节密度分区|纹理密度分区|层级细节|"
    r"(?:背景|远景|边缘|阴影)[^。！？.!?\n]{0,48}(?:简化|低细节|减少纹理)[^。！？.!?\n]{0,48}(?:主体|人物|产品|服装|道具|前景)[^。！？.!?\n]{0,32}(?:高细节|精细|丰富纹理)|"
    r"(?:主体|人物|产品|服装|道具|前景)[^。！？.!?\n]{0,48}(?:高细节|精细|丰富纹理)[^。！？.!?\n]{0,48}(?:背景|远景|边缘|阴影)[^。！？.!?\n]{0,32}(?:简化|低细节|减少纹理)|"
    r"随距离(?:降低|减少)细节|远近细节层级|逐步细化|细节逐渐(?:增加|减少)|"
    r"从草图[^。！？.!?\n]{0,48}(?:细化|高细节)|由高细节[^。！？.!?\n]{0,48}(?:简化|低细节)|"
    r"local(?:ized)? detail|selective detail|detail density zoning|level of detail|\bLOD\b|"
    r"(?:background|distance)[^;.!?\n]{0,48}(?:simplified|low detail)[^;.!?\n]{0,48}(?:subject|character|product|foreground)[^;.!?\n]{0,32}(?:highly detailed|intricate)|"
    r"(?:subject|character|product|foreground)[^;.!?\n]{0,48}(?:highly detailed|intricate)[^;.!?\n]{0,48}(?:background|distance)[^;.!?\n]{0,32}(?:simplified|low detail)|"
    r"progressive detail|detail gradually (?:increases|decreases)|sketch[^;.!?\n]{0,48}(?:refined|high detail))",
    flags=re.IGNORECASE,
)
VISUAL_MEDIUM_MARKERS: dict[str, tuple[str, ...]] = {
    "drawn_2d": (
        "二维绘制", "二维插画", "2D插画", "2D 绘制", "手绘插画", "漫画插画",
        "暗黑漫画", "恐怖漫画", "黑白漫画", "漫画线稿", "黑白线稿", "网点漫画",
        "赛璐璐动画", "赛璐璐上色", "动画截图感", "平面矢量", "铅笔素描",
        "水彩插画", "水粉插画", "木刻版画", "手绘画面",
        "2d illustration", "2d drawing", "hand-drawn illustration", "hand drawn illustration",
        "comic illustration", "comic line art", "manga line art", "cel animation",
        "cel-shaded animation", "flat vector illustration", "watercolor illustration",
    ),
    "rendered_3d": (
        "三维渲染", "3D渲染", "3D 渲染", "三维建模渲染", "CG渲染", "CG 渲染",
        "游戏CG质感", "游戏 CG 质感", "C4D渲染", "Blender渲染", "虚幻引擎渲染",
        "写实三维渲染", "三维角色渲染", "三维场景渲染", "黏土渲染",
        "3d rendering", "3d render", "three-dimensional rendering", "cgi rendering",
        "cinema 4d render", "blender render", "unreal engine render", "octane render",
        "photorealistic 3d render", "clay render",
    ),
    "photographic": (
        "真人实拍", "真实实拍", "实景拍摄", "实拍照片", "摄影照片", "写实摄影",
        "真人摄影", "纪实摄影", "街拍摄影", "胶片摄影", "电影实拍", "实拍电影画面",
        "生活流写实", "雾景实拍感", "写实真人质感",
        "live-action photography", "live action photography", "live-action footage",
        "live action footage", "real-world photography", "documentary photography",
        "street photography", "film photography", "photographic image",
    ),
}
_VISUAL_MEDIUM_LABELS = {
    "drawn_2d": "二维绘制/插画漫画",
    "rendered_3d": "三维/CG 渲染",
    "photographic": "摄影实拍",
}
VISUAL_MEDIUM_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "drawn_2d": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:轮廓|形体边界)[^。！？.!?\n]{0,18}(?:由|通过)[^。！？.!?\n]{0,12}(?:闭合线条|勾勒线条)[^。！？.!?\n]{0,14}(?:与|和)[^。！？.!?\n]{0,10}(?:平面色块边界|色块分界)[^。！？.!?\n]{0,14}(?:组织|构成|建立)[^。！？.!?\n]{0,32}(?:明暗层次|明度层次|光影层次)[^。！？.!?\n]{0,18}(?:通过|采用)[^。！？.!?\n]{0,12}(?:排线密度|笔触密度)[^。！？.!?\n]{0,14}(?:或|与)[^。！？.!?\n]{0,10}(?:离散色阶|分段明度|平涂分区)[^。！？.!?\n]{0,14}(?:表达|呈现)[^。！？.!?\n]{0,32}(?:表面纹理|材质纹理)[^。！？.!?\n]{0,18}(?:固定|贴合|停留)[^。！？.!?\n]{0,14}(?:在|于)(?:画面平面|二维平面)[^。！？.!?\n]{0,20}(?:而|且|并)[^。！？.!?\n]{0,8}(?:不随|不会随)[^。！？.!?\n]{0,12}(?:空间法线|表面法线)[^。！？.!?\n]{0,14}(?:连续变化|平滑变化)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bcontours?\b[^.!?\n]{0,28}\b(?:are organized|are formed|are built) by closed lines? and flat colou?r-block boundaries\b[^.!?\n]{0,44}\btonal layers?\b[^.!?\n]{0,28}\b(?:are expressed|are rendered) through hatching density or discrete value steps?\b[^.!?\n]{0,44}\bsurface textures?\b[^.!?\n]{0,28}\b(?:stay|remain) on (?:the )?image plane instead of changing continuously with spatial normals?\b",
            re.IGNORECASE,
        ),
    ),
    "rendered_3d": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:轮廓|形体边界)[^。！？.!?\n]{0,18}(?:由|通过)[^。！？.!?\n]{0,12}(?:连续几何曲面|连续曲面几何)[^。！？.!?\n]{0,14}(?:投影|映射)[^。！？.!?\n]{0,10}(?:形成|构成)[^。！？.!?\n]{0,32}(?:材质高光|表面高光)[^。！？.!?\n]{0,18}(?:沿|跟随)[^。！？.!?\n]{0,12}(?:表面法线|曲面法线)[^。！？.!?\n]{0,14}(?:连续变化|平滑移动|连续移动)[^。！？.!?\n]{0,32}(?:接触阴影|接触投影)[^。！？.!?\n]{0,16}(?:与|和)[^。！？.!?\n]{0,10}(?:物体遮挡|几何遮挡)[^。！？.!?\n]{0,18}(?:服从|遵循|保持)[^。！？.!?\n]{0,16}(?:同一|统一)(?:的)?(?:空间光照关系|空间照明关系|光照解算关系)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bcontours?\b[^.!?\n]{0,28}\b(?:are formed|are produced) by (?:the )?projection of continuous geometric surfaces?\b[^.!?\n]{0,44}\bmaterial highlights?\b[^.!?\n]{0,28}\b(?:move|change|vary) continuously along surface normals?\b[^.!?\n]{0,44}\bcontact shadows? and object occlusion\b[^.!?\n]{0,32}\b(?:follow|obey|share) (?:the )?same spatial lighting relationship\b",
            re.IGNORECASE,
        ),
    ),
    "photographic": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:细节|像素细节|成像细节)[^。！？.!?\n]{0,18}(?:保留|包含|呈现)[^。！？.!?\n]{0,12}(?:非周期|不规则)(?:的)?(?:微噪声|细微噪声|微小噪声)[^。！？.!?\n]{0,32}(?:焦点前后|焦平面前后|对焦面前后)[^。！？.!?\n]{0,18}(?:呈现|呈|形成|保留)[^。！？.!?\n]{0,14}(?:连续光学弥散|连续弥散圆|渐进光学弥散)[^。！？.!?\n]{0,32}(?:强光边缘|高亮边缘|高光边缘)[^。！？.!?\n]{0,18}(?:出现|保留|带有)[^。！？.!?\n]{0,12}(?:轻微色散|细微色散|轻度色差)[^。！？.!?\n]{0,24}(?:并|且|同时)[^。！？.!?\n]{0,10}(?:具有|呈现|保留)[^。！？.!?\n]{0,12}(?:自然的)?(?:高光滚降|亮部滚降)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\b(?:pixel|image) details?\b[^.!?\n]{0,28}\b(?:retain|contain|show) (?:nonperiodic|non-periodic|irregular) micro-noise\b[^.!?\n]{0,44}\b(?:in front of and behind|around) (?:the )?focus plane\b[^.!?\n]{0,28}\b(?:shows?|forms?|retains?) continuous optical diffusion\b[^.!?\n]{0,44}\b(?:bright-light|highlight) edges?\b[^.!?\n]{0,28}\b(?:show|retain|carry) slight chromatic dispersion\b[^.!?\n]{0,32}\b(?:with|and have) natural highlight roll-off\b",
            re.IGNORECASE,
        ),
    ),
}
_MIXED_VISUAL_MEDIUM_RE = re.compile(
    r"(?:2\.5D|2\.5d|二点五维|二维[^。！？.!?\n]{0,32}(?:与|和|结合|融合|混合|叠加)[^。！？.!?\n]{0,32}三维|"
    r"三维[^。！？.!?\n]{0,32}(?:与|和|结合|融合|混合|叠加)[^。！？.!?\n]{0,32}二维|"
    r"实拍[^。！？.!?\n]{0,32}(?:与|和|结合|融合|混合|叠加)[^。！？.!?\n]{0,32}(?:动画|插画|漫画|CG|三维)|"
    r"(?:动画|插画|漫画|CG|三维)[^。！？.!?\n]{0,32}(?:与|和|结合|融合|混合|叠加)[^。！？.!?\n]{0,32}实拍|"
    r"(?:屏幕|海报|壁画|画框|书页|投影|全息界面)[^。！？.!?\n]{0,40}(?:二维|2D|插画|漫画|动画|三维|3D|CG|实拍|摄影)|"
    r"(?:二维|2D|插画|漫画|动画|三维|3D|CG|实拍|摄影)[^。！？.!?\n]{0,40}(?:屏幕|海报|壁画|画框|书页|投影|全息界面)|"
    r"从(?:二维|2D|插画|漫画|动画|三维|3D|CG|实拍|摄影)[^。！？.!?\n]{0,48}(?:转为|变为|过渡到|切换到)[^。！？.!?\n]{0,24}(?:二维|2D|插画|漫画|动画|三维|3D|CG|实拍|摄影)|"
    r"(?:二维|2D|插画|漫画|动画|三维|3D|CG|实拍|摄影)[^。！？.!?\n]{0,48}(?:随后|逐渐|渐渐|最终|再)?[^。！？.!?\n]{0,12}(?:转为|变为|过渡到|切换到)[^。！？.!?\n]{0,24}(?:二维|2D|插画|漫画|动画|三维|3D|CG|实拍|摄影)|"
    r"(?:mixed[- ]media|2d[^;.!?\n]{0,32}(?:and|with|hybrid|mixed|combined)[^;.!?\n]{0,32}3d|"
    r"3d[^;.!?\n]{0,32}(?:and|with|hybrid|mixed|combined)[^;.!?\n]{0,32}2d|"
    r"live[- ]action[^;.!?\n]{0,32}(?:animation|illustration|cgi|3d)|"
    r"(?:screen|poster|mural|painting|book page|projection|hologram)[^;.!?\n]{0,40}(?:2d|illustration|comic|animation|3d|cgi|photograph)|"
    r"transition[^;.!?\n]{0,32}(?:2d|illustration|animation|3d|cgi|live[- ]action|photography)))",
    flags=re.IGNORECASE,
)
PROJECTION_GEOMETRY_MARKERS: dict[str, tuple[str, ...]] = {
    "orthographic": (
        "正交投影视角", "正交投影", "标准正投影", "正投影视图", "平行投影",
        "无透视投影", "无透视畸变", "正交相机",
        "orthographic projection", "orthographic camera", "orthographic view",
        "parallel projection", "no perspective distortion",
    ),
    "perspective": (
        "透视投影", "线性透视", "单点透视", "一点透视", "两点透视", "三点透视",
        "夸张透视", "强烈透视", "广角畸变",
        "perspective projection", "linear perspective", "one-point perspective",
        "two-point perspective", "three-point perspective", "exaggerated perspective",
        "wide-angle distortion", "wide angle distortion",
    ),
    "axonometric": (
        "轴测投影", "轴测视图", "等轴测投影", "等距投影", "等距视图",
        "isometric projection", "isometric view", "axonometric projection", "axonometric view",
    ),
    "fisheye": (
        "鱼眼镜头", "鱼眼畸变", "圆形鱼眼", "全景鱼眼",
        "fisheye lens", "fisheye distortion", "circular fisheye", "full-frame fisheye",
    ),
}
_PROJECTION_GEOMETRY_LABELS = {
    "orthographic": "正交/平行投影",
    "perspective": "线性透视投影",
    "axonometric": "轴测/等距投影",
    "fisheye": "鱼眼投影",
}
PROJECTION_GEOMETRY_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "orthographic": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:同方向|同一方向)(?:的)?(?:平行边|平行线)[^。！？.!?\n]{0,18}(?:始终|持续)?(?:保持|维持)[^。！？.!?\n]{0,8}平行[^。！？.!?\n]{0,32}(?:同尺寸|相同尺寸|等尺寸)(?:对象|物体)[^。！？.!?\n]{0,20}(?:不因|不会因|不随)[^。！？.!?\n]{0,10}深度[^。！？.!?\n]{0,12}(?:改变|变化)(?:画面|成像)?尺度[^。！？.!?\n]{0,32}沿(?:视轴|镜头轴线|观察轴)延伸(?:的)?(?:结构|物体)[^。！？.!?\n]{0,18}(?:不产生|不会产生|不形成)[^。！？.!?\n]{0,10}(?:消失点)?汇聚|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bparallel (?:edges?|lines?) (?:sharing|with) the same direction\b[^.!?\n]{0,28}\bremain parallel\b[^.!?\n]{0,44}\b(?:equally|same)[- ]sized objects?\b[^.!?\n]{0,28}\bdo not change (?:their )?(?:image|screen) scale with depth\b[^.!?\n]{0,44}\bstructures? extending along the (?:view|camera|viewing) axis\b[^.!?\n]{0,28}\bdo not converge (?:toward|to) (?:a )?vanishing point\b",
            re.IGNORECASE,
        ),
    ),
    "perspective": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:同方向|同一方向)(?:的)?(?:平行边|平行线)[^。！？.!?\n]{0,18}(?:向|朝向)[^。！？.!?\n]{0,10}(?:一致|同一)(?:的)?消失点[^。！？.!?\n]{0,12}汇聚[^。！？.!?\n]{0,32}(?:同尺寸|相同尺寸|等尺寸)(?:对象|物体)[^。！？.!?\n]{0,18}随[^。！？.!?\n]{0,8}深度增加[^。！？.!?\n]{0,12}(?:逐渐|连续)?缩小[^。！？.!?\n]{0,32}沿(?:视轴|镜头轴线|观察轴)延伸(?:的)?(?:结构|物体)[^。！？.!?\n]{0,18}(?:产生|形成|呈现)[^。！？.!?\n]{0,12}(?:连续)?透视缩短|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bparallel (?:edges?|lines?) (?:sharing|with) the same direction\b[^.!?\n]{0,28}\bconverge (?:toward|to) (?:a )?(?:consistent|shared|single) vanishing point\b[^.!?\n]{0,44}\b(?:equally|same)[- ]sized objects?\b[^.!?\n]{0,28}\b(?:become|get|grow) smaller with (?:increasing )?depth\b[^.!?\n]{0,44}\bstructures? extending along the (?:view|camera|viewing) axis\b[^.!?\n]{0,28}\b(?:show|produce|form) continuous perspective foreshortening\b",
            re.IGNORECASE,
        ),
    ),
    "axonometric": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:每组|各组)(?:同方向|同一方向)(?:的)?(?:轴线|主轴)[^。！？.!?\n]{0,18}(?:始终|持续)?(?:保持|维持)[^。！？.!?\n]{0,8}平行[^。！？.!?\n]{0,32}(?:对应轴|相应轴)(?:上|向)(?:的)?(?:同长度|相同长度|等长)(?:线段|结构)[^。！？.!?\n]{0,18}(?:保持|维持)[^。！？.!?\n]{0,10}(?:恒定|一致)(?:画面|成像)?尺度[^。！？.!?\n]{0,32}(?:所有|全部)(?:主轴|轴线)[^。！？.!?\n]{0,18}(?:都不|不会|不向)[^。！？.!?\n]{0,10}(?:向)?消失点汇聚|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\beach family of same-direction axes\b[^.!?\n]{0,28}\bremains? parallel\b[^.!?\n]{0,44}\bequal-length segments? along corresponding axes\b[^.!?\n]{0,28}\b(?:keep|retain|maintain) (?:a )?constant image scale\b[^.!?\n]{0,44}\bno principal axis converges? (?:toward|to) (?:a )?vanishing point\b",
            re.IGNORECASE,
        ),
    ),
    "fisheye": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:直线结构|直线边缘|笔直结构)[^。！？.!?\n]{0,18}从(?:同一)?光学中心[^。！？.!?\n]{0,18}(?:向|朝向)(?:画幅|图像|画面)(?:的)?边缘[^。！？.!?\n]{0,18}(?:逐渐|连续)?(?:产生|形成|呈现)[^。！？.!?\n]{0,10}径向弯曲[^。！？.!?\n]{0,32}(?:边缘|外围)(?:空间)?间距[^。！？.!?\n]{0,18}(?:连续|逐渐)?压缩[^。！？.!?\n]{0,32}(?:全部|所有)(?:曲率|弯曲)[^。！？.!?\n]{0,18}(?:围绕|环绕)[^。！？.!?\n]{0,10}(?:同一|统一)(?:的)?光学中心(?:组织|分布)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bstraight structures?\b[^.!?\n]{0,28}\bdevelop increasing radial curvature\b[^.!?\n]{0,32}\bfrom the optical cent(?:er|re) toward the frame edge\b[^.!?\n]{0,44}\bperipheral spatial intervals? compress continuously\b[^.!?\n]{0,44}\ball curvature is organized around one optical cent(?:er|re)\b",
            re.IGNORECASE,
        ),
    ),
}
_MIXED_PROJECTION_GEOMETRY_RE = re.compile(
    r"(?:透视[^。！？.!?\n]{0,36}(?:与|和|结合|配合|并列|加上|混合)[^。！？.!?\n]{0,36}(?:轴测|等距|鱼眼)|"
    r"(?:轴测|等距|鱼眼)[^。！？.!?\n]{0,36}(?:与|和|结合|配合|并列|加上|混合)[^。！？.!?\n]{0,36}透视|"
    r"(?:轴测|等距)[^。！？.!?\n]{0,36}(?:与|和|结合|配合|并列|加上|混合)[^。！？.!?\n]{0,36}鱼眼|"
    r"鱼眼[^。！？.!?\n]{0,36}(?:与|和|结合|配合|并列|加上|混合)[^。！？.!?\n]{0,36}(?:轴测|等距)|"
    r"正交[^。！？.!?\n]{0,36}(?:与|和|结合|配合|并列|加上)[^。！？.!?\n]{0,36}(?:透视|轴测|等距|鱼眼)|"
    r"(?:透视|轴测|等距|鱼眼)[^。！？.!?\n]{0,36}(?:与|和|结合|配合|并列|加上)[^。！？.!?\n]{0,36}正交|"
    r"(?:主视图|主体|三视图)[^。！？.!?\n]{0,40}正交[^。！？.!?\n]{0,48}(?:辅助图|插图|小窗|局部|细节图)[^。！？.!?\n]{0,32}(?:透视|轴测|等距|鱼眼)|"
    r"(?:辅助图|插图|小窗|局部|细节图)[^。！？.!?\n]{0,32}(?:透视|轴测|等距|鱼眼)[^。！？.!?\n]{0,48}(?:主视图|主体|三视图)[^。！？.!?\n]{0,40}正交|"
    r"(?:正交|透视|轴测|等距|鱼眼)[^。！？.!?\n]{0,48}(?:随后|逐渐|渐渐|最终|再)?[^。！？.!?\n]{0,12}(?:转为|变为|过渡到|切换到)[^。！？.!?\n]{0,24}(?:正交|透视|轴测|等距|鱼眼)|"
    r"(?:perspective[^;.!?\n]{0,36}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,36}(?:isometric|axonometric|fisheye)|"
    r"(?:isometric|axonometric|fisheye)[^;.!?\n]{0,36}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,36}perspective|"
    r"(?:isometric|axonometric)[^;.!?\n]{0,36}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,36}fisheye|"
    r"fisheye[^;.!?\n]{0,36}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,36}(?:isometric|axonometric)|"
    r"orthographic[^;.!?\n]{0,36}(?:and|with|combined|alongside)[^;.!?\n]{0,36}(?:perspective|isometric|axonometric|fisheye)|"
    r"(?:perspective|isometric|axonometric|fisheye)[^;.!?\n]{0,36}(?:and|with|combined|alongside)[^;.!?\n]{0,36}orthographic|"
    r"(?:main views?|turnaround)[^;.!?\n]{0,40}orthographic[^;.!?\n]{0,48}(?:inset|detail view|support view)[^;.!?\n]{0,32}(?:perspective|isometric|axonometric|fisheye)|"
    r"(?:orthographic|perspective|isometric|axonometric|fisheye)[^;.!?\n]{0,48}(?:transition|shift|change)[^;.!?\n]{0,24}(?:orthographic|perspective|isometric|axonometric|fisheye)))",
    flags=re.IGNORECASE,
)
PERSPECTIVE_LAYOUT_MARKERS: dict[str, tuple[str, ...]] = {
    "one_point": (
        "单点透视", "一点透视", "单消失点透视",
        "one-point perspective", "one point perspective", "single-vanishing-point perspective",
        "single vanishing point perspective",
    ),
    "two_point": (
        "两点透视", "二点透视", "双消失点透视",
        "two-point perspective", "two point perspective", "dual-vanishing-point perspective",
        "dual vanishing point perspective",
    ),
    "three_point": (
        "三点透视", "三消失点透视",
        "three-point perspective", "three point perspective", "triple-vanishing-point perspective",
        "triple vanishing point perspective",
    ),
}
_PERSPECTIVE_LAYOUT_LABELS = {
    "one_point": "一点/单消失点透视",
    "two_point": "两点/双消失点透视",
    "three_point": "三点/三消失点透视",
}
PERSPECTIVE_LAYOUT_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "one_point": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}沿(?:视轴|镜头轴线|观察轴)延伸(?:的)?(?:水平边|水平线)[^。！？.!?\n]{0,18}(?:统一|全部|共同)汇聚到[^。！？.!?\n]{0,12}地平线上的(?:单一|一个)消失点[^。！？.!?\n]{0,32}正对镜头平面(?:的)?(?:竖直边|垂直边)[^。！？.!?\n]{0,16}(?:与|和)(?:水平边|横向边)[^。！？.!?\n]{0,16}(?:保持|维持)平行[^。！？.!?\n]{0,32}(?:不产生|不会形成|没有)第二个水平消失点|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bhorizontal (?:edges?|lines?) extending along the (?:view|camera|viewing) axis\b[^.!?\n]{0,28}\bconverge (?:together )?(?:to|toward) (?:a )?single vanishing point on the horizon\b[^.!?\n]{0,44}\bvertical and horizontal edges? on the camera-facing plane\b[^.!?\n]{0,28}\bremain parallel\b[^.!?\n]{0,44}\bno second horizontal vanishing point (?:appears|is formed)\b",
            re.IGNORECASE,
        ),
    ),
    "two_point": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:两组|两族)(?:水平方向边|水平边|水平线)[^。！？.!?\n]{0,18}(?:分别|各自)汇聚到[^。！？.!?\n]{0,14}地平线(?:左|左右)(?:右)?(?:两侧|两端)?(?:的)?两个消失点[^。！？.!?\n]{0,32}(?:竖直边|垂直边|竖线)[^。！？.!?\n]{0,18}(?:始终|持续)?(?:保持|维持)平行[^。！？.!?\n]{0,32}(?:不向|不会向|不产生)[^。！？.!?\n]{0,10}第三个消失点汇聚|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\btwo families of horizontal edges?\b[^.!?\n]{0,28}\bconverge separately (?:to|toward) two vanishing points on the left and right of the horizon\b[^.!?\n]{0,44}\bvertical edges?\b[^.!?\n]{0,28}\bremain parallel\b[^.!?\n]{0,44}\bdo not converge (?:to|toward) a third vanishing point\b",
            re.IGNORECASE,
        ),
    ),
    "three_point": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:两组|两族)水平边[^。！？.!?\n]{0,16}(?:与|和)(?:竖直边|垂直边)[^。！？.!?\n]{0,18}(?:分别|各自)向[^。！？.!?\n]{0,12}三个(?:独立|不同)(?:的)?消失点汇聚[^。！？.!?\n]{0,32}(?:垂直结构|竖直结构)[^。！？.!?\n]{0,18}随高度[^。！？.!?\n]{0,12}(?:连续|逐渐)收束[^。！？.!?\n]{0,32}(?:不存在|没有)(?:保持平行的)?全局竖直线族|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\btwo horizontal edge families and the vertical edge family\b[^.!?\n]{0,28}\bconverge separately (?:to|toward) three distinct vanishing points\b[^.!?\n]{0,44}\bvertical structures?\b[^.!?\n]{0,28}\bconverge progressively with height\b[^.!?\n]{0,44}\bno global family of parallel vertical lines? remains?\b",
            re.IGNORECASE,
        ),
    ),
}
_MIXED_PERSPECTIVE_LAYOUT_RE = re.compile(
    r"(?:(?:单点|一点)[^。！？.!?\n]{0,28}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,28}(?:两点|二点|三点)|"
    r"(?:两点|二点|三点)[^。！？.!?\n]{0,28}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,28}(?:单点|一点)|"
    r"(?:两点|二点)[^。！？.!?\n]{0,28}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,28}三点|"
    r"三点[^。！？.!?\n]{0,28}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,28}(?:两点|二点)|"
    r"(?:主视图|主画面|主体|三视图)[^。！？.!?\n]{0,40}(?:单点|一点|两点|二点|三点)透视[^。！？.!?\n]{0,48}(?:辅助图|插图|小窗|局部|细节图)[^。！？.!?\n]{0,32}(?:单点|一点|两点|二点|三点)透视|"
    r"(?:单点|一点|两点|二点|三点)透视[^。！？.!?\n]{0,48}(?:随后|逐渐|渐渐|最终|再)?[^。！？.!?\n]{0,12}(?:转为|变为|过渡到|切换到)[^。！？.!?\n]{0,24}(?:单点|一点|两点|二点|三点)透视|"
    r"(?:(?:one|two|three)[- ]point perspective[^;.!?\n]{0,32}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,32}(?:one|two|three)[- ]point perspective|"
    r"(?:main view|main image|turnaround)[^;.!?\n]{0,40}(?:one|two|three)[- ]point perspective[^;.!?\n]{0,48}(?:inset|detail view|support view)[^;.!?\n]{0,32}(?:one|two|three)[- ]point perspective|"
    r"(?:one|two|three)[- ]point perspective[^;.!?\n]{0,48}(?:transition|shift|change)[^;.!?\n]{0,24}(?:one|two|three)[- ]point perspective))",
    flags=re.IGNORECASE,
)
CAMERA_ROLL_MARKERS: dict[str, tuple[str, ...]] = {
    "level": (
        "零度滚转", "零度镜头滚转", "无镜头滚转", "无相机滚转",
        "地平线保持水平", "水平地平线", "画幅无倾斜", "水平画幅基准",
        "zero camera roll", "zero-degree camera roll", "zero degree camera roll",
        "level horizon", "uncanted frame", "no camera roll",
    ),
    "dutch": (
        "荷兰角", "荷兰式倾斜构图", "倾斜构图", "倾斜画幅",
        "明显镜头滚转", "明显相机滚转", "斜置镜头",
        "dutch angle", "canted frame", "canted camera", "canted angle",
        "pronounced camera roll", "intentional camera roll", "rolled camera",
    ),
}
_CAMERA_ROLL_LABELS = {
    "level": "零度滚转/水平地平线",
    "dutch": "荷兰角/倾斜画幅",
}
CAMERA_ROLL_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "level": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:中心|中央)(?:的)?重力竖直方向[^。！？.!?\n]{0,18}(?:与|和)画幅竖轴[^。！？.!?\n]{0,14}(?:重合|对齐)[^。！？.!?\n]{0,32}地平基准[^。！？.!?\n]{0,18}(?:始终|持续)?平行于画幅横轴[^。！？.!?\n]{0,32}(?:主体|人物)[^。！？.!?\n]{0,14}(?:与|和)环境[^。！？.!?\n]{0,18}(?:共享|服从)[^。！？.!?\n]{0,12}(?:零度|无)(?:镜头|相机)?滚转基准|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe gravity-vertical direction at the (?:frame )?cent(?:er|re)\b[^.!?\n]{0,28}\b(?:aligns|coincides) with the frame vertical axis\b[^.!?\n]{0,44}\bthe horizon reference remains parallel to the frame horizontal axis\b[^.!?\n]{0,44}\bthe subject and environment share (?:a )?zero camera-roll reference\b",
            re.IGNORECASE,
        ),
    ),
    "dutch": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:中心|中央)(?:的)?重力竖直方向[^。！？.!?\n]{0,18}(?:与|和)画幅竖轴[^。！？.!?\n]{0,18}形成(?:一致的)?非零夹角[^。！？.!?\n]{0,32}地平基准[^。！？.!?\n]{0,18}相对画幅横轴[^。！？.!?\n]{0,14}(?:稳定|持续)倾斜[^。！？.!?\n]{0,32}(?:主体|人物)[^。！？.!?\n]{0,14}(?:与|和)环境[^。！？.!?\n]{0,18}(?:共享|服从)[^。！？.!?\n]{0,12}同一(?:镜头|相机)?滚转角|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe gravity-vertical direction at the (?:frame )?cent(?:er|re)\b[^.!?\n]{0,28}\bforms (?:a )?consistent nonzero angle with the frame vertical axis\b[^.!?\n]{0,44}\bthe horizon reference remains tilted relative to the frame horizontal axis\b[^.!?\n]{0,44}\bthe subject and environment share the same camera-roll angle\b",
            re.IGNORECASE,
        ),
    ),
}
_MIXED_CAMERA_ROLL_RE = re.compile(
    r"(?:(?:零度滚转|无镜头滚转|无相机滚转|地平线保持水平|水平地平线|画幅无倾斜)[^。！？.!?\n]{0,32}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,32}(?:荷兰角|倾斜构图|倾斜画幅|明显镜头滚转|明显相机滚转)|"
    r"(?:荷兰角|倾斜构图|倾斜画幅|明显镜头滚转|明显相机滚转)[^。！？.!?\n]{0,32}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,32}(?:零度滚转|无镜头滚转|无相机滚转|地平线保持水平|水平地平线|画幅无倾斜)|"
    r"(?:主视图|主画面|主体|三视图)[^。！？.!?\n]{0,40}(?:零度滚转|水平地平线|荷兰角|倾斜构图)[^。！？.!?\n]{0,48}(?:辅助图|插图|小窗|局部|细节图)[^。！？.!?\n]{0,32}(?:零度滚转|水平地平线|荷兰角|倾斜构图)|"
    r"(?:零度滚转|水平地平线|荷兰角|倾斜构图)[^。！？.!?\n]{0,48}(?:随后|逐渐|渐渐|最终|再)?[^。！？.!?\n]{0,12}(?:转为|变为|过渡到|切换到|滚转为)[^。！？.!?\n]{0,24}(?:零度滚转|水平地平线|荷兰角|倾斜构图)|"
    r"(?:(?:zero camera roll|level horizon|uncanted frame)[^;.!?\n]{0,32}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,32}(?:dutch angle|canted frame|canted camera)|"
    r"(?:dutch angle|canted frame|canted camera)[^;.!?\n]{0,32}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,32}(?:zero camera roll|level horizon|uncanted frame)|"
    r"(?:zero camera roll|level horizon|uncanted frame|dutch angle|canted frame)[^;.!?\n]{0,48}(?:transition|shift|change|roll)[^;.!?\n]{0,24}(?:zero camera roll|level horizon|uncanted frame|dutch angle|canted frame)))",
    flags=re.IGNORECASE,
)
COMPOSITION_PLACEMENT_MARKERS: dict[str, tuple[str, ...]] = {
    "centered": (
        "中心构图", "居中构图", "人物居中", "主体居中", "对称构图", "轴对称构图",
        "centered composition", "center composition", "subject centered",
        "symmetrical composition", "axially symmetrical composition",
    ),
    "offset": (
        "三分法", "三分法构图", "三分构图", "偏心构图", "主体偏置", "偏置构图",
        "rule of thirds", "thirds composition", "off-center composition",
        "off-center subject", "offset subject composition",
    ),
}
_COMPOSITION_PLACEMENT_LABELS = {
    "centered": "居中/轴对称落点",
    "offset": "三分法/偏心落点",
}
COMPOSITION_PLACEMENT_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "centered": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体|人物|主要视觉)[^。！？.!?\n]{0,18}(?:重心|视觉中心)[^。！？.!?\n]{0,14}(?:落在|位于|保持在)[^。！？.!?\n]{0,12}(?:画幅)?竖直中轴[^。！？.!?\n]{0,32}(?:左右|两侧)(?:主要)?(?:视觉质量|视觉重量|画面质量)[^。！？.!?\n]{0,18}(?:和|与)[^。！？.!?\n]{0,10}留白[^。！？.!?\n]{0,18}(?:形成|保持)[^。！？.!?\n]{0,12}(?:近似|基本)?镜像平衡[^。！？.!?\n]{0,32}(?:视线|动作)轴[^。！？.!?\n]{0,18}(?:保持|服从)[^。！？.!?\n]{0,12}(?:中央|中轴)(?:组织|安排)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe subject(?:'s)? primary visual centroid\b[^.!?\n]{0,28}\bfalls on the frame vertical centerline\b[^.!?\n]{0,44}\bleft and right visual mass(?:es)? and negative space\b[^.!?\n]{0,28}\bform near-mirror balance\b[^.!?\n]{0,44}\bthe gaze or action axis remains centered\b",
            re.IGNORECASE,
        ),
    ),
    "offset": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体|人物|主要视觉)[^。！？.!?\n]{0,18}(?:重心|视觉中心)[^。！？.!?\n]{0,14}(?:稳定)?落在[^。！？.!?\n]{0,16}(?:左|右)(?:侧)?三分线(?:或|及)?交点[^。！？.!?\n]{0,32}(?:主体|人物)[^。！？.!?\n]{0,16}(?:视线|动作)(?:方向)?前方[^。！？.!?\n]{0,18}(?:保留|留出)[^。！？.!?\n]{0,12}(?:较大|宽阔|明确)(?:的)?负空间[^。！？.!?\n]{0,32}(?:不回到|不恢复|避免回到)[^。！？.!?\n]{0,12}(?:中央|中心)(?:对称|平衡)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe subject(?:'s)? primary visual centroid\b[^.!?\n]{0,28}\bfalls steadily on the left or right third line or intersection\b[^.!?\n]{0,44}\bthe space ahead of the gaze or action direction retains broad negative space\b[^.!?\n]{0,44}\bthe composition does not return to centered mirror balance\b",
            re.IGNORECASE,
        ),
    ),
}
_MIXED_COMPOSITION_PLACEMENT_RE = re.compile(
    r"(?:(?:中心构图|居中构图|人物居中|主体居中|对称构图|轴对称构图)[^。！？.!?\n]{0,32}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,32}(?:三分法|三分构图|偏心构图|主体偏置|偏置构图)|"
    r"(?:三分法|三分构图|偏心构图|主体偏置|偏置构图)[^。！？.!?\n]{0,32}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,32}(?:中心构图|居中构图|人物居中|主体居中|对称构图|轴对称构图)|"
    r"(?:主视图|主画面|主体|三视图)[^。！？.!?\n]{0,40}(?:中心构图|居中构图|三分法|偏心构图)[^。！？.!?\n]{0,48}(?:辅助图|插图|小窗|局部|细节图)[^。！？.!?\n]{0,32}(?:中心构图|居中构图|三分法|偏心构图)|"
    r"(?:中心构图|居中构图|三分法|偏心构图)[^。！？.!?\n]{0,48}(?:随后|逐渐|渐渐|最终|再)?[^。！？.!?\n]{0,12}(?:转为|变为|过渡到|切换到)[^。！？.!?\n]{0,24}(?:中心构图|居中构图|三分法|偏心构图)|"
    r"(?:(?:centered composition|center composition|subject centered|symmetrical composition)[^;.!?\n]{0,32}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,32}(?:rule of thirds|thirds composition|off-center composition|off-center subject)|"
    r"(?:rule of thirds|thirds composition|off-center composition|off-center subject)[^;.!?\n]{0,32}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,32}(?:centered composition|center composition|subject centered|symmetrical composition)|"
    r"(?:centered composition|center composition|rule of thirds|thirds composition|off-center composition)[^;.!?\n]{0,48}(?:transition|shift|change)[^;.!?\n]{0,24}(?:centered composition|center composition|rule of thirds|thirds composition|off-center composition)))",
    flags=re.IGNORECASE,
)
SCREEN_DIRECTION_MARKERS: dict[str, tuple[str, ...]] = {
    "left_to_right": (
        "屏幕方向从左向右", "主体从左向右", "人物从左向右", "角色从左向右",
        "从左向右移动", "从左向右行走", "从左向右奔跑", "从左向右疾跑", "由左向右移动",
        "左进右出", "朝画面右侧移动", "向画面右侧移动",
        "面向画面右侧", "视线朝画面右侧", "动作指向画面右侧",
        "left-to-right screen direction", "left to right screen direction",
        "moving left to right", "facing screen right", "screen-right movement",
    ),
    "right_to_left": (
        "屏幕方向从右向左", "主体从右向左", "人物从右向左", "角色从右向左",
        "从右向左移动", "从右向左行走", "从右向左奔跑", "从右向左疾跑", "由右向左移动",
        "右进左出", "朝画面左侧移动", "向画面左侧移动",
        "面向画面左侧", "视线朝画面左侧", "动作指向画面左侧",
        "right-to-left screen direction", "right to left screen direction",
        "moving right to left", "facing screen left", "screen-left movement",
    ),
}
_SCREEN_DIRECTION_LABELS = {
    "left_to_right": "从左向右/朝画面右侧",
    "right_to_left": "从右向左/朝画面左侧",
}
SCREEN_DIRECTION_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "left_to_right": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体|人物)(?:的)?(?:头肩|躯干|动作)(?:方向|轴线)?[^。！？.!?\n]{0,18}(?:稳定)?指向画面右侧[^。！？.!?\n]{0,32}(?:视线|运动|动作)(?:方向)?前方[^。！？.!?\n]{0,18}(?:在|于)画面右侧[^。！？.!?\n]{0,14}(?:保留|留出)[^。！？.!?\n]{0,12}(?:引导|前导|行动)空间[^。！？.!?\n]{0,32}(?:运动轨迹|道具指向|衣摆拖曳)[^。！？.!?\n]{0,18}(?:统一|共同)?沿[^。！？.!?\n]{0,12}左到右(?:的)?屏幕方向|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe subject(?:'s)? head, torso, or action axis\b[^.!?\n]{0,28}\bpoints steadily toward screen right\b[^.!?\n]{0,44}\bthe space ahead of the gaze, motion, or action\b[^.!?\n]{0,28}\bis retained on the right side of the frame\b[^.!?\n]{0,44}\bmotion traces, prop direction, or trailing fabric continue from left toward right across the frame\b",
            re.IGNORECASE,
        ),
    ),
    "right_to_left": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体|人物)(?:的)?(?:头肩|躯干|动作)(?:方向|轴线)?[^。！？.!?\n]{0,18}(?:稳定)?指向画面左侧[^。！？.!?\n]{0,32}(?:视线|运动|动作)(?:方向)?前方[^。！？.!?\n]{0,18}(?:在|于)画面左侧[^。！？.!?\n]{0,14}(?:保留|留出)[^。！？.!?\n]{0,12}(?:引导|前导|行动)空间[^。！？.!?\n]{0,32}(?:运动轨迹|道具指向|衣摆拖曳)[^。！？.!?\n]{0,18}(?:统一|共同)?沿[^。！？.!?\n]{0,12}右到左(?:的)?屏幕方向|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe subject(?:'s)? head, torso, or action axis\b[^.!?\n]{0,28}\bpoints steadily toward screen left\b[^.!?\n]{0,44}\bthe space ahead of the gaze, motion, or action\b[^.!?\n]{0,28}\bis retained on the left side of the frame\b[^.!?\n]{0,44}\bmotion traces, prop direction, or trailing fabric continue from right toward left across the frame\b",
            re.IGNORECASE,
        ),
    ),
}
_MIXED_SCREEN_DIRECTION_RE = re.compile(
    r"(?:(?:从左向右|由左向右|朝画面右侧|向画面右侧)[^。！？.!?\n]{0,36}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,36}(?:从右向左|由右向左|朝画面左侧|向画面左侧)|"
    r"(?:从右向左|由右向左|朝画面左侧|向画面左侧)[^。！？.!?\n]{0,36}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,36}(?:从左向右|由左向右|朝画面右侧|向画面右侧)|"
    r"(?:主视图|主画面|主体|三视图)[^。！？.!?\n]{0,40}(?:从左向右|从右向左|朝画面右侧|朝画面左侧)[^。！？.!?\n]{0,48}(?:辅助图|插图|小窗|局部|细节图)[^。！？.!?\n]{0,32}(?:从左向右|从右向左|朝画面右侧|朝画面左侧)|"
    r"(?:从左向右|从右向左|朝画面右侧|朝画面左侧)[^。！？.!?\n]{0,48}(?:随后|逐渐|突然|最终|再)?[^。！？.!?\n]{0,16}(?:转身|掉头|反向|转为|切换到|越轴|过轴|跨越动作轴)[^。！？.!?\n]{0,28}(?:从左向右|从右向左|朝画面右侧|朝画面左侧)|"
    r"(?:(?:left-to-right|left to right|screen right)[^;.!?\n]{0,36}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,36}(?:right-to-left|right to left|screen left)|"
    r"(?:right-to-left|right to left|screen left)[^;.!?\n]{0,36}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,36}(?:left-to-right|left to right|screen right)|"
    r"(?:left-to-right|left to right|screen right|right-to-left|right to left|screen left)[^;.!?\n]{0,48}(?:turns around|reverses|crosses the axis|axis crossing|transition|shift|change)[^;.!?\n]{0,32}(?:left-to-right|left to right|screen right|right-to-left|right to left|screen left)))",
    flags=re.IGNORECASE,
)
SPATIAL_AXIS_CONTINUITY_MARKERS: dict[str, tuple[str, ...]] = {
    "axis_hold": (
        "180度轴线规则", "180度规则", "不越轴", "保持不越轴", "禁止越轴",
        "固定摄影机半空间", "固定机位半区", "同侧机位连续性", "保持动作轴线",
        "180-degree rule", "180 degree rule", "no axis crossing", "do not cross the axis",
        "stay on one side of the action axis", "same camera half-space",
        "maintain the line of action",
    ),
    "planned_cross": (
        "计划越轴", "明确越轴镜头", "可见越轴运动", "摄影机跨越动作轴",
        "镜头跨越动作轴", "越轴换边", "连续越轴路径",
        "planned axis crossing", "deliberate axis crossing", "visible axis-crossing move",
        "camera crosses the action axis", "camera crosses the line of action",
        "continuous axis-crossing path",
    ),
}
_SPATIAL_AXIS_CONTINUITY_LABELS = {
    "axis_hold": "遵守180度轴线/不越轴",
    "planned_cross": "计划越轴/可见路径换边",
}
SPATIAL_AXIS_CONTINUITY_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "axis_hold": (
        re.compile(
            r"(?:整个|全部|完整|全)(?:分镜|镜头)(?:序列|段落|组)[^。！？.!?\n]{0,24}(?:摄影机|摄像机|镜头)[^。！？.!?\n]{0,18}(?:始终|持续)(?:停留|保持)在(?:人物)?互动轴线同一侧[^。！？.!?\n]{0,32}(?:角色|人物)[^。！？.!?\n]{0,16}(?:与|和)(?:关键)?(?:物件|道具)[^。！？.!?\n]{0,18}(?:画面)?左右位置[^。！？.!?\n]{0,14}(?:保持|维持)稳定[^。！？.!?\n]{0,32}反打镜头[^。！？.!?\n]{0,18}(?:继续|始终)?服从同一空间半区|"
            r"\b(?:across|throughout) the (?:entire|whole|complete) (?:shot|storyboard) sequence\b[^.!?\n]{0,40}\bthe camera (?:remains|stays) on the same side of the interaction axis\b[^.!?\n]{0,52}\bthe screen-left and screen-right positions of (?:the )?characters? and key props? remain stable\b[^.!?\n]{0,52}\breverse angles? continue to obey the same spatial half-space\b",
            re.IGNORECASE,
        ),
    ),
    "planned_cross": (
        re.compile(
            r"(?:整个|全部|完整)(?:分镜|镜头)(?:序列|段落|组)[^。！？.!?\n]{0,24}(?:摄影机|摄像机|镜头)[^。！？.!?\n]{0,18}(?:沿|以)(?:连续)?可见路径[^。！？.!?\n]{0,18}跨越(?:人物)?互动轴线[^。！？.!?\n]{0,32}(?:角色|人物)[^。！？.!?\n]{0,16}(?:与|和)(?:关键)?(?:物件|道具)[^。！？.!?\n]{0,24}只在越轴过程完成后交换(?:画面)?左右位置[^。！？.!?\n]{0,32}越轴前后[^。！？.!?\n]{0,18}环境锚点[^。！？.!?\n]{0,14}(?:保持|仍然)?可追踪|"
            r"\b(?:across|throughout) the (?:entire|whole|complete) (?:shot|storyboard) sequence\b[^.!?\n]{0,40}\bthe camera crosses the interaction axis along a continuous visible path\b[^.!?\n]{0,52}\bcharacters? and key props? exchange screen sides only after the crossing move is complete\b[^.!?\n]{0,52}\benvironmental anchors? remain traceable before and after the crossing\b",
            re.IGNORECASE,
        ),
    ),
}
_MIXED_SPATIAL_AXIS_CONTINUITY_RE = re.compile(
    r"(?:(?:180度轴线规则|180度规则|不越轴|固定摄影机半空间|同侧机位连续性)[^。！？.!?\n]{0,40}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,40}(?:计划越轴|明确越轴镜头|可见越轴运动|摄影机跨越动作轴)|"
    r"(?:计划越轴|明确越轴镜头|可见越轴运动|摄影机跨越动作轴)[^。！？.!?\n]{0,40}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,40}(?:180度轴线规则|180度规则|不越轴|固定摄影机半空间)|"
    r"(?:主视图|主画面|主体|三视图)[^。！？.!?\n]{0,40}(?:不越轴|计划越轴|摄影机跨越动作轴)[^。！？.!?\n]{0,48}(?:辅助图|插图|小窗|局部|细节图)[^。！？.!?\n]{0,32}(?:不越轴|计划越轴|摄影机跨越动作轴)|"
    r"(?:不越轴|固定摄影机半空间)[^。！？.!?\n]{0,52}(?:随后|逐渐|最终|再)?[^。！？.!?\n]{0,12}(?:转为|变为|过渡到|通过)[^。！？.!?\n]{0,24}(?:计划越轴|可见越轴运动|连续越轴路径)|"
    r"(?:(?:180-degree rule|180 degree rule|no axis crossing|same camera half-space)[^;.!?\n]{0,40}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,40}(?:planned axis crossing|deliberate axis crossing|camera crosses the action axis)|"
    r"(?:planned axis crossing|deliberate axis crossing|camera crosses the action axis)[^;.!?\n]{0,40}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,40}(?:180-degree rule|180 degree rule|no axis crossing|same camera half-space)|"
    r"(?:180-degree rule|no axis crossing|same camera half-space)[^;.!?\n]{0,52}(?:then|gradually|eventually|transition|shift)[^;.!?\n]{0,28}(?:planned axis crossing|visible axis-crossing move|camera crosses the action axis)))",
    flags=re.IGNORECASE,
)
FOREGROUND_OCCLUSION_MARKERS: dict[str, tuple[str, ...]] = {
    "clear_subject": (
        "主体无遮挡", "人物无遮挡", "面部无遮挡", "脸部无遮挡",
        "无前景遮挡", "不要前景遮挡", "无遮挡构图", "主体轮廓无遮挡",
        "subject free of foreground occlusion", "character free of foreground occlusion",
        "face free of foreground occlusion", "no foreground occlusion",
        "unobstructed subject composition",
    ),
    "foreground_frame": (
        "前景遮挡", "受控前景遮挡", "前景框景", "遮挡式构图",
        "框中框构图", "窥视构图", "前景元素框住主体",
        "foreground occlusion", "controlled foreground occlusion",
        "foreground framing", "frame-within-a-frame composition",
        "frame within a frame composition", "peek-through framing",
    ),
}
_FOREGROUND_OCCLUSION_LABELS = {
    "clear_subject": "主体无遮挡/轮廓清楚",
    "foreground_frame": "受控前景遮挡/框景",
}
FOREGROUND_OCCLUSION_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "clear_subject": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体|人物)(?:的)?主要轮廓[^。！？.!?\n]{0,18}(?:始终|持续)?保持连续可读[^。！？.!?\n]{0,32}(?:任何|所有)前景(?:物|元素)[^。！？.!?\n]{0,18}(?:都不|不得|不会)覆盖(?:人物|主体)?(?:的)?面部、双手(?:或|和)动作关节[^。！？.!?\n]{0,32}(?:主体|人物)[^。！？.!?\n]{0,12}(?:与|和)背景(?:的)?边界[^。！？.!?\n]{0,18}(?:始终|持续)?清楚分离|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe subject(?:'s)? primary silhouette remains continuously readable\b[^.!?\n]{0,52}\bno foreground element covers the face, hands, or action joints\b[^.!?\n]{0,52}\bthe boundary between the subject and background stays clearly separated\b",
            re.IGNORECASE,
        ),
    ),
    "foreground_frame": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:仅由|只由)场景中已有前景元素[^。！？.!?\n]{0,18}覆盖(?:主体|人物)(?:的)?次要边缘[^。！？.!?\n]{0,32}(?:面部|脸部)、双手(?:与|和)动作支点[^。！？.!?\n]{0,18}(?:始终|持续)?保持可见[^。！？.!?\n]{0,32}前景、主体(?:与|和)背景(?:的)?遮挡顺序[^。！？.!?\n]{0,18}(?:保持|维持)稳定一致|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bonly foreground elements already present in the scene overlap the subject's secondary edges\b[^.!?\n]{0,52}\bthe face, hands, and action fulcrum remain visible\b[^.!?\n]{0,52}\bthe occlusion order of foreground, subject, and background remains stable\b",
            re.IGNORECASE,
        ),
    ),
}
_MIXED_FOREGROUND_OCCLUSION_RE = re.compile(
    r"(?:(?:主体无遮挡|人物无遮挡|面部无遮挡|无前景遮挡|无遮挡构图)[^。！？.!?\n]{0,40}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,40}(?:前景遮挡|前景框景|遮挡式构图|框中框构图)|"
    r"(?:前景遮挡|前景框景|遮挡式构图|框中框构图)[^。！？.!?\n]{0,40}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,40}(?:主体无遮挡|人物无遮挡|面部无遮挡|无前景遮挡|无遮挡构图)|"
    r"(?:主视图|主画面|主体|三视图)[^。！？.!?\n]{0,40}(?:主体无遮挡|无前景遮挡|前景遮挡|前景框景)[^。！？.!?\n]{0,48}(?:辅助图|插图|小窗|局部|细节图)[^。！？.!?\n]{0,32}(?:主体无遮挡|无前景遮挡|前景遮挡|前景框景)|"
    r"(?:主体无遮挡|人物无遮挡|无前景遮挡)[^。！？.!?\n]{0,52}(?:随后|逐渐|最终|再)?[^。！？.!?\n]{0,12}(?:转为|变为|过渡到|进入)[^。！？.!?\n]{0,24}(?:前景遮挡|前景框景|遮挡式构图)|"
    r"(?:前景遮挡|前景框景|遮挡式构图)[^。！？.!?\n]{0,52}(?:随后|逐渐|最终|再)?[^。！？.!?\n]{0,12}(?:解除|移开|退去|转为|过渡到)[^。！？.!?\n]{0,24}(?:主体无遮挡|人物无遮挡|无前景遮挡)|"
    r"(?:(?:subject free of foreground occlusion|no foreground occlusion|unobstructed subject composition)[^;.!?\n]{0,40}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,40}(?:foreground occlusion|foreground framing|frame-within-a-frame composition)|"
    r"(?:foreground occlusion|foreground framing|frame-within-a-frame composition)[^;.!?\n]{0,40}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,40}(?:subject free of foreground occlusion|no foreground occlusion|unobstructed subject composition)|"
    r"(?:subject free of foreground occlusion|no foreground occlusion)[^;.!?\n]{0,52}(?:then|gradually|eventually|transition|shift)[^;.!?\n]{0,28}(?:foreground occlusion|foreground framing)|"
    r"(?:foreground occlusion|foreground framing)[^;.!?\n]{0,52}(?:clears|moves away|recedes|transitions|shifts)[^;.!?\n]{0,28}(?:subject free of foreground occlusion|no foreground occlusion)))",
    flags=re.IGNORECASE,
)
SUBJECT_SUPPORT_STATE_MARKERS: dict[str, tuple[str, ...]] = {
    "supported": (
        "主体稳定着地", "人物稳定着地", "双脚稳定着地", "双脚着地",
        "脚踏地面", "足底接触地面", "明确接触支撑面", "身体由支撑面承托",
        "主体有明确支撑", "人物有明确支撑", "稳定承重接触",
        "subject firmly grounded", "character firmly grounded", "both feet planted",
        "feet planted on the ground", "clear load-bearing contact",
        "body supported by the surface",
    ),
    "suspended": (
        "主体悬浮", "人物悬浮", "角色悬浮", "悬浮待机",
        "主体腾空", "人物腾空", "角色腾空", "跳跃腾空",
        "主体离地", "人物离地", "角色离地", "整体离地",
        "主体浮空", "人物浮空", "角色浮空", "漂浮在空中",
        "subject suspended", "character suspended", "subject airborne",
        "character airborne", "subject off the ground", "character off the ground",
        "levitating subject", "levitating character", "floating in midair",
    ),
}
_SUBJECT_SUPPORT_STATE_LABELS = {
    "supported": "稳定承重/接触支撑面",
    "suspended": "整体离地/悬浮腾空",
}
SUBJECT_SUPPORT_STATE_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "supported": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体|人物)(?:的)?重量[^。！？.!?\n]{0,18}(?:通过|经由)(?:双脚|膝部|髋部|躯干)[^。！？.!?\n]{0,18}传递到场景中已有支撑面[^。！？.!?\n]{0,32}(?:承重点|接触点)[^。！？.!?\n]{0,18}(?:出现|保留)(?:受压|形变|接触阴影)(?:反馈)?[^。！？.!?\n]{0,32}(?:身体|主体)(?:的)?重心投影[^。！？.!?\n]{0,18}(?:落在|位于)支撑范围内|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe subject's weight transfers through the feet, knees, hips, or torso to an existing support surface\b[^.!?\n]{0,56}\bcompression, deformation, or contact-shadow feedback appears at the load-bearing points\b[^.!?\n]{0,56}\bthe body's projected center of mass falls within the support area\b",
            re.IGNORECASE,
        ),
    ),
    "suspended": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体|人物)(?:的)?整体轮廓[^。！？.!?\n]{0,18}(?:与|和)(?:地面|座面|支撑面)[^。！？.!?\n]{0,18}保持可见离地间隙[^。！？.!?\n]{0,32}(?:身体姿态|发丝衣摆|周围颗粒)[^。！？.!?\n]{0,18}(?:共同|统一)响应同一[^。！？.!?\n]{0,18}(?:上升|飞行|浮力|腾空)(?:受力|状态)[^。！？.!?\n]{0,32}(?:投影|接触线索)[^。！？.!?\n]{0,18}(?:不形成|不会形成|没有)虚假承重接触|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe subject's complete silhouette keeps a visible gap from the ground, seat, or support surface\b[^.!?\n]{0,56}\bthe body pose, hair, clothing, and surrounding particles respond to the same[^.!?\n]{0,28}(?:upward|flight|buoyant) force\b[^.!?\n]{0,56}\bshadow or contact cues do not create false load-bearing contact\b",
            re.IGNORECASE,
        ),
    ),
}
_MIXED_SUBJECT_SUPPORT_STATE_RE = re.compile(
    r"(?:(?:主体稳定着地|人物稳定着地|双脚稳定着地|双脚着地|脚踏地面|明确接触支撑面)[^。！？.!?\n]{0,40}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,40}(?:主体悬浮|人物悬浮|角色悬浮|主体腾空|人物腾空|整体离地)|"
    r"(?:主体悬浮|人物悬浮|角色悬浮|主体腾空|人物腾空|整体离地)[^。！？.!?\n]{0,40}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,40}(?:主体稳定着地|人物稳定着地|双脚稳定着地|双脚着地|脚踏地面|明确接触支撑面)|"
    r"(?:主视图|主画面|主体|三视图)[^。！？.!?\n]{0,40}(?:稳定着地|双脚着地|人物悬浮|人物腾空|整体离地)[^。！？.!?\n]{0,48}(?:辅助图|插图|小窗|局部|细节图)[^。！？.!?\n]{0,32}(?:稳定着地|双脚着地|人物悬浮|人物腾空|整体离地)|"
    r"(?:稳定着地|双脚着地|脚踏地面|明确接触支撑面)[^。！？.!?\n]{0,52}(?:随后|逐渐|突然|最终|再)?[^。！？.!?\n]{0,12}(?:跳起|跃起|腾空|离地|转为|过渡到)[^。！？.!?\n]{0,24}(?:悬浮|腾空|离地|浮空)|"
    r"(?:主体悬浮|人物悬浮|角色悬浮|主体腾空|人物腾空|整体离地)[^。！？.!?\n]{0,52}(?:随后|逐渐|最终|再)?[^。！？.!?\n]{0,12}(?:落地|着地|坐下|跪地|接触|转为|过渡到)[^。！？.!?\n]{0,24}(?:稳定着地|双脚着地|支撑面|承重)|"
    r"(?:(?:subject firmly grounded|both feet planted|clear load-bearing contact)[^;.!?\n]{0,40}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,40}(?:subject suspended|subject airborne|subject off the ground|levitating subject)|"
    r"(?:subject suspended|subject airborne|subject off the ground|levitating subject)[^;.!?\n]{0,40}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,40}(?:subject firmly grounded|both feet planted|clear load-bearing contact)|"
    r"(?:subject firmly grounded|both feet planted|clear load-bearing contact)[^;.!?\n]{0,52}(?:then|gradually|suddenly|eventually|jumps|leaps|transitions)[^;.!?\n]{0,28}(?:subject suspended|subject airborne|off the ground)|"
    r"(?:subject suspended|subject airborne|subject off the ground|levitating subject)[^;.!?\n]{0,52}(?:lands|touches down|sits|kneels|transitions)[^;.!?\n]{0,28}(?:firmly grounded|both feet planted|load-bearing contact)))",
    flags=re.IGNORECASE,
)
GAZE_TARGET_MARKERS: dict[str, tuple[str, ...]] = {
    "camera_lock": (
        "看向镜头", "直视镜头", "视线朝镜头", "与镜头对视", "眼神直达镜头", "回头看向镜头",
        "looking into camera", "looking into the camera", "looking at the camera",
        "direct eye contact", "eye contact with camera", "camera-facing gaze",
    ),
    "off_camera": (
        "视线离开镜头", "不看镜头", "视线看向道具", "看向道具", "视线锁定道具",
        "侧目看向远处", "视线越过镜头", "看向场景目标",
        "off-camera gaze", "looking away from camera", "looking away from the camera",
        "looking at the prop", "looking at the object", "gaze locked on the prop",
    ),
}
_GAZE_TARGET_LABELS = {
    "camera_lock": "直视镜头/镜头对视",
    "off_camera": "离开镜头/锁定场景目标",
}
GAZE_TARGET_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "camera_lock": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体|人物)(?:的)?双眼视线[^。！？.!?\n]{0,18}(?:向|朝)同一(?:镜头)?光轴[^。！？.!?\n]{0,14}(?:汇聚|对齐)[^。！？.!?\n]{0,32}(?:瞳孔|双瞳)方向[^。！？.!?\n]{0,18}(?:与|和)镜头中心[^。！？.!?\n]{0,14}(?:保持|形成)一致[^。！？.!?\n]{0,32}(?:面部朝向|头部朝向)[^。！？.!?\n]{0,18}(?:可以|允许)(?:独立)?变化[^。！？.!?\n]{0,32}双眼不偏离既定光轴|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe subject's two eyes converge toward the same camera optical axis\b[^.!?\n]{0,44}\bpupil directions align with the camera center\b[^.!?\n]{0,44}\bhead orientation may change independently\b[^.!?\n]{0,32}\bwithout the gaze passing beyond the camera\b",
            re.IGNORECASE,
        ),
    ),
    "off_camera": (
        re.compile(
            r"(?:全画面|整个画面|整体画面|画面整体)[^。！？.!?\n]{0,18}(?:主体|人物)(?:的)?双眼视线[^。！？.!?\n]{0,18}(?:避开|离开)镜头光轴[^。！？.!?\n]{0,32}(?:并|且|同时)汇聚到画面内明确(?:对象|物体|区域)[^。！？.!?\n]{0,32}(?:目标方向|视线方向)[^。！？.!?\n]{0,18}(?:与|和)(?:对象|物体|区域)位置[^。！？.!?\n]{0,14}(?:保持|对应)一致[^。！？.!?\n]{0,32}(?:不回到|不会回到)(?:镜头对视|直视镜头)|"
            r"\b(?:across|throughout) the (?:full|entire|whole) (?:frame|image)\b[^.!?\n]{0,32}\bthe subject's two eyes avoid the camera optical axis and converge on an explicit object or region inside the frame\b[^.!?\n]{0,44}\bthe gaze direction matches the object's position\b[^.!?\n]{0,32}\bwithout redirecting the pupils toward the lens\b",
            re.IGNORECASE,
        ),
    ),
}
_MIXED_GAZE_TARGET_RE = re.compile(
    r"(?:(?:直视镜头|看向镜头|与镜头对视|视线朝镜头)[^。！？.!?\n]{0,32}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,32}(?:视线离开镜头|不看镜头|看向道具|视线锁定道具|侧目看向远处)|"
    r"(?:视线离开镜头|不看镜头|看向道具|视线锁定道具|侧目看向远处)[^。！？.!?\n]{0,32}(?:与|和|结合|配合|并列|混合)[^。！？.!?\n]{0,32}(?:直视镜头|看向镜头|与镜头对视|视线朝镜头)|"
    r"(?:双人|两人|人物甲|人物乙|主角与配角)[^。！？.!?\n]{0,40}(?:互相|彼此|相互)(?:对视|看向对方|视线交汇)|"
    r"(?:直视镜头|看向镜头|视线离开镜头|看向道具)[^。！？.!?\n]{0,48}(?:随后|逐渐|渐渐|最终|再)?[^。！？.!?\n]{0,12}(?:转为|变为|过渡到|切换到|转头|回头看)[^。！？.!?\n]{0,28}(?:直视镜头|看向镜头|视线离开镜头|看向道具)|"
    r"(?:(?:looking at the camera|direct eye contact|camera-facing gaze)[^;.!?\n]{0,36}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,36}(?:off-camera gaze|looking away from the camera|looking at the prop)|"
    r"(?:off-camera gaze|looking away from the camera|looking at the prop)[^;.!?\n]{0,36}(?:and|with|combined|alongside|mixed)[^;.!?\n]{0,36}(?:looking at the camera|direct eye contact|camera-facing gaze)|"
    r"(?:two subjects?|two characters?)[^;.!?\n]{0,40}(?:look at each other|exchange eye contact|gaze at one another)|"
    r"(?:looking at the camera|direct eye contact|off-camera gaze|looking at the prop)[^;.!?\n]{0,48}(?:then|gradually|eventually|transition|turns?)[^;.!?\n]{0,28}(?:looking at the camera|direct eye contact|off-camera gaze|looking at the prop)))",
    flags=re.IGNORECASE,
)
ATMOSPHERIC_MEDIUM_MARKERS: dict[str, tuple[str, ...]] = {
    "clear_air": (
        "空气通透", "通透空气", "清澈空气", "无雾空气", "无烟空气", "无雾无烟",
        "高能见度空气", "高能见度画面", "能见度通透", "上午通透天光",
        "crystal-clear air", "crystal clear air", "clear haze-free air", "haze-free air",
        "fog-free atmosphere", "smoke-free air", "high-visibility atmosphere",
    ),
    "mist_fog": (
        "冷雾惊悚侧光", "冷雾侧光", "青蓝冷雾", "冷雾", "红雾表现主义打光", "红雾",
        "清晨薄雾", "细雨薄雾", "初秋薄雾", "薄雾层次", "海雾", "远景蓝雾",
        "雾气弥漫", "浓雾", "体积雾", "低垂雾气", "冷雾古巷", "雾林吊脚楼",
        "cold mist", "morning mist", "thin mist", "layered mist", "sea fog",
        "foggy atmosphere", "mist-filled air", "mist filled air", "dense fog",
        "volumetric fog", "low-lying fog", "low lying fog", "red mist expressionist lighting",
    ),
    "smoke_dust": (
        "顶光烟雾", "舞台烟雾", "烟雾弥漫", "烟雾中", "浓烟", "烟尘天光",
        "烟尘", "沙尘逆光", "沙尘体积光", "沙尘天气", "粉尘空气", "扬尘",
        "火山灰弥漫", "灰烬弥漫",
        "smoky atmosphere", "smoke-filled air", "smoke filled air", "dense smoke",
        "stage smoke", "airborne dust", "dust-filled air", "dust filled air",
        "sandstorm haze", "volcanic ash in the air",
    ),
}
_ATMOSPHERIC_MEDIUM_LABELS = {
    "clear_air": "通透高能见度空气",
    "mist_fog": "雾化低能见度空气",
    "smoke_dust": "颗粒烟尘空气",
}
_MIXED_ATMOSPHERIC_MEDIUM_RE = re.compile(
    r"(?:(?:前景|主体|人物|面部|产品)[^。！？.!?\n]{0,40}(?:清晰|通透|无雾|无烟)[^。！？.!?\n]{0,48}(?:背景|远景|地面|脚边)[^。！？.!?\n]{0,32}(?:薄雾|浓雾|冷雾|烟雾|烟尘|沙尘)|"
    r"(?:背景|远景|地面|脚边)[^。！？.!?\n]{0,32}(?:薄雾|浓雾|冷雾|烟雾|烟尘|沙尘)[^。！？.!?\n]{0,48}(?:主体|人物|面部|产品|前景)[^。！？.!?\n]{0,32}(?:清晰|通透|无雾|无烟)|"
    r"(?:薄雾|浓雾|冷雾|雾气)[^。！？.!?\n]{0,36}(?:与|和|混合|交织|叠加)[^。！？.!?\n]{0,36}(?:烟雾|烟尘|沙尘|粉尘)|"
    r"(?:烟雾|烟尘|沙尘|粉尘)[^。！？.!?\n]{0,36}(?:与|和|混合|交织|叠加)[^。！？.!?\n]{0,36}(?:薄雾|浓雾|冷雾|雾气)|"
    r"(?:火炬|香炉|烟囱|排气口|枪口|火堆)[^。！？.!?\n]{0,32}(?:局部|少量|一缕)?(?:烟雾|烟气|烟尘)|"
    r"(?:薄雾|浓雾|冷雾|雾气|烟雾|浓烟|烟尘|沙尘)[^。！？.!?\n]{0,40}(?:逐渐|开始|随后|最终)?(?:散去|消散|退去|退开|变淡|被吹散|转为通透)|"
    r"(?:(?:foreground|subject|character|face|product)[^;.!?\n]{0,40}(?:clear|haze-free|fog-free|smoke-free)[^;.!?\n]{0,48}(?:background|distance|ground)[^;.!?\n]{0,32}(?:mist|fog|smoke|dust)|"
    r"(?:background|distance|ground)[^;.!?\n]{0,32}(?:mist|fog|smoke|dust)[^;.!?\n]{0,48}(?:subject|character|face|product|foreground)[^;.!?\n]{0,32}(?:clear|haze-free|fog-free|smoke-free)|"
    r"(?:mist|fog)[^;.!?\n]{0,36}(?:and|with|mixed|interwoven)[^;.!?\n]{0,36}(?:smoke|dust)|"
    r"(?:torch|incense|chimney|vent|muzzle|campfire)[^;.!?\n]{0,32}(?:local|small|thin)?[^;.!?\n]{0,12}(?:smoke|fumes)|"
    r"(?:mist|fog|smoke|dust)[^;.!?\n]{0,40}(?:dissipates|clears|thins|fades|is blown away)))",
    flags=re.IGNORECASE,
)
# Candidate-only feedback patterns catch an implicit medium change without
# turning ordinary depth of field, soft focus, or isolated particles into a
# new scene constraint.
ATMOSPHERIC_MEDIUM_FEEDBACK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "clear_air": (
        re.compile(
            r"(?:远景|远处(?:轮廓|建筑|石墙)?|背景轮廓)[^。！？.!?\n]{0,24}(?:始终|依然|保持)?(?:清晰锐利|清楚分明|毫无衰减)|"
            r"(?:光束|光线)[^。！？.!?\n]{0,16}(?:穿过|通过)空气[^。！？.!?\n]{0,12}(?:毫无|没有|不产生)(?:介质)?散射|"
            r"\b(?:distant|faraway) (?:contours?|architecture|background)\b[^.!?\n]{0,36}\b(?:remains?|stays?) (?:crisp|sharply defined)\b|"
            r"\b(?:distant|faraway) (?:contours?|architecture|background)\b[^.!?\n]{0,36}\bshows? no atmospheric (?:falloff|scattering)\b",
            re.IGNORECASE,
        ),
    ),
    "mist_fog": (
        re.compile(
            r"(?:远景|远处(?:轮廓|建筑|石墙)?|背景轮廓)[^。！？.!?\n]{0,24}(?:在|穿过)[^。！？.!?\n]{0,8}(?:悬浮水汽|细密水滴|湿润微滴)[^。！？.!?\n]{0,16}(?:逐层衰减|层层隐没|逐渐消失)|"
            r"(?:光束|光线)[^。！？.!?\n]{0,12}(?:穿过|经过)[^。！？.!?\n]{0,8}(?:悬浮水汽|细密水滴|湿润微滴)[^。！？.!?\n]{0,12}(?:乳白散射|柔和漫散|扩散成乳白光晕)|"
            r"\b(?:distant contours?|background silhouettes?)\b[^.!?\n]{0,32}\b(?:fade|recede|disappear)\b[^.!?\n]{0,24}\b(?:through )?(?:suspended moisture|fine water droplets)\b|"
            r"\b(?:suspended moisture|fine water droplets)\b[^.!?\n]{0,24}\b(?:soften|diffuse|scatter) (?:the )?(?:light|light beams?)\b",
            re.IGNORECASE,
        ),
    ),
    "smoke_dust": (
        re.compile(
            r"(?:密集|大量)(?:灰黑|焦黑|干燥|粗粝)?(?:悬浮)?颗粒[^。！？.!?\n]{0,20}(?:遮住|遮蔽|吞没)(?:远景|背景|视线)|"
            r"(?:光束|光线)[^。！？.!?\n]{0,16}(?:干燥悬浮物|灰黑颗粒|焦黑颗粒)[^。！？.!?\n]{0,16}(?:浑浊散射|棕黄散射|变得浑浊)|"
            r"\b(?:dense|thick) (?:gritty|charred|dark|dry|suspended) particles\b[^.!?\n]{0,32}\b(?:obscure|veil|swallow) (?:the )?(?:distance|background|view)\b|"
            r"\b(?:light|light beams?)\b[^.!?\n]{0,24}\b(?:through|among) (?:dry suspended matter|charred particles)\b[^.!?\n]{0,24}\b(?:turn|turns|become|becomes) murky\b",
            re.IGNORECASE,
        ),
    ),
}
BACKGROUND_COMPLEXITY_MARKERS: dict[str, tuple[str, ...]] = {
    "minimal": (
        "简洁连续中性背景", "简洁连续背景", "简洁中性背景", "简洁背景", "简单背景",
        "极简背景", "干净背景", "纯色背景", "无缝背景", "空白背景", "背景无杂物",
        "简洁无杂物", "简单无杂物",
        "simple continuous neutral background", "simple continuous background",
        "simple neutral background", "simple background", "minimal background",
        "clean uncluttered background", "plain background", "seamless backdrop",
    ),
    "environment_rich": (
        "复杂背景", "繁复背景", "丰富环境背景", "高密度场景元素", "密集背景元素",
        "背景堆满杂物", "背景布满道具", "大量背景道具", "繁复环境陈设", "拥挤背景",
        "complex background", "elaborate background", "rich environmental background",
        "dense background elements", "cluttered background", "background crowded with props",
        "busy environmental backdrop",
    ),
}
_BACKGROUND_COMPLEXITY_LABELS = {
    "minimal": "简洁/无杂物背景",
    "environment_rich": "丰富/繁复环境背景",
}
_MIXED_BACKGROUND_COMPLEXITY_RE = re.compile(
    r"(?:(?:背景|主背景)[^。！？.!?\n]{0,40}(?:简洁|简单|极简|纯色|无缝|无杂物)[^。！？.!?\n]{0,48}(?:单个|唯一|一件|必要)[^。！？.!?\n]{0,24}(?:道具|底座|地面阴影|接触阴影)|"
    r"(?:单个|唯一|一件|必要)[^。！？.!?\n]{0,24}(?:道具|底座|地面阴影|接触阴影)[^。！？.!?\n]{0,48}(?:背景|主背景)[^。！？.!?\n]{0,32}(?:简洁|简单|极简|纯色|无缝|无杂物)|"
    r"(?:主视图|三视图)[^。！？.!?\n]{0,40}(?:简洁|简单|极简)[^。！？.!?\n]{0,48}(?:辅助图|情境图|小窗)[^。！？.!?\n]{0,32}(?:复杂|丰富|环境)|"
    r"(?:简洁|简单|极简|纯色|无缝)[^。！？.!?\n]{0,48}(?:随后|逐渐|最终|再)?[^。！？.!?\n]{0,12}(?:转为|变为|展开为|过渡到)[^。！？.!?\n]{0,24}(?:复杂|繁复|丰富|真实环境)|"
    r"(?:(?:background|backdrop)[^;.!?\n]{0,40}(?:simple|minimal|plain|uncluttered)[^;.!?\n]{0,48}(?:single|one|necessary)[^;.!?\n]{0,24}(?:prop|pedestal|contact shadow)|"
    r"(?:main views?|turnaround)[^;.!?\n]{0,40}(?:simple|minimal)[^;.!?\n]{0,48}(?:inset|context view)[^;.!?\n]{0,32}(?:complex|rich|environmental)|"
    r"(?:simple|minimal|plain)[^;.!?\n]{0,48}(?:transition|change|expand)[^;.!?\n]{0,24}(?:complex|rich|environmental)))",
    flags=re.IGNORECASE,
)
SEASON_MARKERS: dict[str, tuple[str, ...]] = {
    "spring": (
        "春季", "春日", "早春", "暮春", "春日新绿", "早春融雪", "暮春花雨",
        "春耕水田", "樱花春景", "春季景色",
        "springtime", "spring season", "early spring", "late spring", "spring scenery",
    ),
    "summer": (
        "夏季", "夏日", "盛夏", "仲夏", "夏夜", "盛夏浓荫", "夏日雷雨",
        "夏夜萤火", "夏季景色",
        "summertime", "summer season", "midsummer", "summer night", "summer scenery",
    ),
    "autumn": (
        "秋季", "秋日", "初秋", "深秋", "晚秋", "金秋", "秋收田野",
        "初秋薄雾", "深秋红叶", "金秋草原", "晚秋芦苇", "秋季景色",
        "autumn season", "fall season", "early autumn", "late autumn", "autumn scenery",
    ),
    "winter": (
        "冬季", "冬日", "初冬", "寒冬", "隆冬", "冬日原野", "初冬霜地",
        "冬日雪原", "冬季景色",
        "wintertime", "winter season", "early winter", "deep winter", "winter scenery",
    ),
}
_SEASON_LABELS = {
    "spring": "春季",
    "summer": "夏季",
    "autumn": "秋季",
    "winter": "冬季",
}
_MIXED_SEASON_RE = re.compile(
    r"(?:四季|春夏秋冬|四时景色|四季组图|四季变化|季节轮回|跨季节|"
    r"(?:春季|春日|早春|暮春|夏季|夏日|盛夏|仲夏|秋季|秋日|初秋|深秋|晚秋|冬季|冬日|初冬|寒冬)[^。！？.!?\n]{0,48}"
    r"(?:随后|逐渐|最终|再)?[^。！？.!?\n]{0,12}(?:转为|进入|过渡到|变化为)[^。！？.!?\n]{0,24}"
    r"(?:春季|春日|夏季|夏日|秋季|秋日|冬季|冬日)|"
    r"four seasons|seasonal cycle|seasonal transition|across seasons|"
    r"(?:springtime|spring season|summer season|summertime|autumn season|fall season|winter season|wintertime)"
    r"[^;.!?\n]{0,48}(?:transition|change|shift|turn)[^;.!?\n]{0,24}"
    r"(?:springtime|spring season|summer season|summertime|autumn season|fall season|winter season|wintertime))",
    flags=re.IGNORECASE,
)

# Fifty exact language expansions share the established relation and model-guard pipeline.
INTELLIGENCE_V42_RULE_EXPANSIONS: tuple[tuple[str, str, str], ...] = (
    ("subject_cardinality", "single", "仅有一名角色"),
    ("subject_cardinality", "pair", "恰好两名角色"),
    ("subject_orientation", "front", "人物正对观众"),
    ("subject_orientation", "back", "人物背朝观众"),
    ("subject_pose", "standing", "保持直立站姿"),
    ("subject_pose", "sitting", "端正坐下姿态"),
    ("shot_scale", "closeup", "头肩肖像特写"),
    ("shot_scale", "full_body", "完整头脚全身像"),
    ("camera_angle", "low_angle", "贴地仰视镜头"),
    ("camera_angle", "top_down", "垂直向下俯视"),
    ("light_temperature", "cool", "冰蓝冷调照明"),
    ("light_temperature", "warm", "琥珀暖调照明"),
    ("color_rendering", "monochrome", "纯灰阶画面"),
    ("color_rendering", "full_color", "完整彩色成像"),
    ("depth_of_field", "shallow", "奶油散景浅焦"),
    ("depth_of_field", "deep", "全场景深焦"),
    ("lighting_quality", "hard", "刀锋般硬光"),
    ("lighting_quality", "soft", "包裹式柔光"),
    ("motion_rendering", "frozen", "高速快门定格"),
    ("motion_rendering", "motion_trail", "明显动态拖影"),
    ("camera_stability", "stable", "锁死三脚架机位"),
    ("camera_stability", "handheld", "肩扛晃动摄影"),
    ("focal_perspective", "wide", "14毫米超广角"),
    ("focal_perspective", "telephoto", "300毫米长焦压缩"),
    ("key_light_direction", "side", "左侧主光照明"),
    ("key_light_direction", "back", "正后方轮廓主光"),
    ("exposure_key", "high_key", "明亮白场高键"),
    ("exposure_key", "low_key", "深黑低键曝光"),
    ("contrast_level", "high", "强烈明暗反差"),
    ("contrast_level", "low", "柔和平缓反差"),
    ("saturation_level", "high", "浓烈高彩度"),
    ("saturation_level", "low", "克制低彩度"),
    ("image_grain", "grainy", "明显银盐颗粒"),
    ("image_grain", "clean", "无噪纯净数码"),
    ("image_sharpness", "sharp", "全局锐利成像"),
    ("image_sharpness", "soft_focus", "全局朦胧软焦"),
    ("detail_density", "high", "精密复杂细节"),
    ("detail_density", "low", "概括化低细节"),
    ("visual_medium", "drawn_2d", "传统手绘漫画"),
    ("visual_medium", "rendered_3d", "PBR三维渲染"),
    ("visual_medium", "photographic", "高保真人像实拍"),
    ("projection_geometry", "orthographic", "工程正交视图"),
    ("projection_geometry", "perspective", "建筑两点透视"),
    ("projection_geometry", "axonometric", "标准等轴测视图"),
    ("atmospheric_medium", "clear_air", "澄澈无霾空气"),
    ("atmospheric_medium", "mist_fog", "乳白薄雾空气"),
    ("atmospheric_medium", "smoke_dust", "工业烟尘空气"),
    ("background_complexity", "minimal", "单色无杂物背景"),
    ("background_complexity", "environment_rich", "层次繁密环境背景"),
    ("camera_angle", "eye_level", "人物眼高平视镜头"),
)

_V42_MARKER_TARGETS: dict[str, dict[str, tuple[str, ...]]] = {
    "subject_cardinality": SUBJECT_CARDINALITY_MARKERS,
    "subject_orientation": SUBJECT_ORIENTATION_MARKERS,
    "subject_pose": SUBJECT_POSE_MARKERS,
    "shot_scale": SHOT_SCALE_MARKERS,
    "camera_angle": CAMERA_ANGLE_MARKERS,
    "light_temperature": LIGHT_TEMPERATURE_MARKERS,
    "color_rendering": COLOR_RENDERING_MARKERS,
    "depth_of_field": DEPTH_OF_FIELD_MARKERS,
    "lighting_quality": LIGHTING_QUALITY_MARKERS,
    "motion_rendering": MOTION_RENDERING_MARKERS,
    "camera_stability": CAMERA_STABILITY_MARKERS,
    "focal_perspective": FOCAL_PERSPECTIVE_MARKERS,
    "key_light_direction": KEY_LIGHT_DIRECTION_MARKERS,
    "exposure_key": EXPOSURE_KEY_MARKERS,
    "contrast_level": CONTRAST_LEVEL_MARKERS,
    "saturation_level": SATURATION_LEVEL_MARKERS,
    "image_grain": IMAGE_GRAIN_MARKERS,
    "image_sharpness": IMAGE_SHARPNESS_MARKERS,
    "detail_density": DETAIL_DENSITY_MARKERS,
    "visual_medium": VISUAL_MEDIUM_MARKERS,
    "projection_geometry": PROJECTION_GEOMETRY_MARKERS,
    "atmospheric_medium": ATMOSPHERIC_MEDIUM_MARKERS,
    "background_complexity": BACKGROUND_COMPLEXITY_MARKERS,
}
for _axis_name, _axis_value, _marker in INTELLIGENCE_V42_RULE_EXPANSIONS:
    _target = _V42_MARKER_TARGETS[_axis_name]
    if _marker not in _target[_axis_value]:
        _target[_axis_value] = (*_target[_axis_value], _marker)
del _axis_name, _axis_value, _marker, _target


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


def detect_scene_attribute_feedback(text: Any) -> dict[str, dict[str, list[str]]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, dict[str, list[str]]] = {}
    for axis, values in SCENE_ATTRIBUTE_FEEDBACK_PATTERNS.items():
        axis_hits: dict[str, list[str]] = {}
        for value, patterns in values.items():
            evidence: list[str] = []
            for pattern in patterns:
                for match in pattern.finditer(source):
                    if _marker_match_is_negated(folded, match.start()):
                        continue
                    fragment = _clean(match.group(0))
                    if fragment and fragment not in evidence:
                        evidence.append(fragment)
            if evidence:
                axis_hits[value] = evidence
        if axis_hits:
            hits[axis] = axis_hits
    return hits


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
            "source": "natural_context",
        }
    return constraints


def _resolve_scene_attribute_constraints(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, dict[str, Any]]:
    constraints = _context_scene_attribute_constraints(context_text)
    context_positive = detect_scene_attributes(context_text)
    selected_hits = detect_scene_attributes("，".join(_unique(selected_values, 32)))
    for axis in SCENE_ATTRIBUTE_MARKERS:
        if axis in constraints:
            continue
        # Multiple context states describe a sequence or comparison and must not
        # fall back to a static tag-derived constraint.
        if len(context_positive.get(axis, {})) > 1:
            continue
        selected_axis_hits = dict(selected_hits.get(axis, {}) or {})
        if len(selected_axis_hits) != 1:
            continue
        required = next(iter(selected_axis_hits))
        constraints[axis] = {
            "axis_label": _SCENE_ATTRIBUTE_LABELS[axis],
            "required_value": required,
            "required_label": _SCENE_ATTRIBUTE_LABELS.get(required, required),
            "positive_values": [required],
            "negated_values": [],
            "negated_labels": [],
            "positive_evidence": {required: list(selected_axis_hits[required])},
            "negated_evidence": {},
            "source": "selected_state",
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


def detect_subject_orientation_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in SUBJECT_ORIENTATION_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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
        "source": "natural_context",
    }


def _resolve_subject_orientation_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context = _clean(context_text)
    context_positive = _detect_subject_orientation(
        context,
        negated=False,
        require_context_scope=True,
    )
    if len(context_positive) > 1 or _OPEN_ORIENTATION_LAYOUT_RE.search(context):
        return {}
    context_constraint = _context_subject_orientation_constraint(context)
    if context_constraint:
        return context_constraint
    selected_text = "，".join(_unique(selected_values, 32))
    if _OPEN_ORIENTATION_LAYOUT_RE.search(selected_text):
        return {}
    positive = detect_subject_orientation(selected_text)
    if len(positive) != 1:
        return {}
    required = next(iter(positive))
    return {
        "required_value": required,
        "required_label": _SUBJECT_ORIENTATION_LABELS.get(required, required),
        "positive_values": [required],
        "negated_values": [],
        "negated_labels": [],
        "positive_evidence": {required: list(positive.get(required, []))},
        "negated_evidence": {},
        "source": "selected_state",
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


def detect_subject_pose_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in SUBJECT_POSE_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_subject_pose(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(text, SUBJECT_POSE_MARKERS, negated=True)


def _context_subject_pose_constraint(text: Any) -> dict[str, Any]:
    positive = detect_subject_pose(text)
    negated = detect_negated_subject_pose(text)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _SUBJECT_POSE_LABELS,
        axis_label="主体姿态",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_subject_pose_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context = _clean(context_text)
    context_positive = detect_subject_pose(context)
    if len(context_positive) > 1:
        return {}
    context_constraint = _context_subject_pose_constraint(context)
    if context_constraint:
        return context_constraint
    selected_text = "，".join(_unique(selected_values, 32))
    positive = detect_subject_pose(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _SUBJECT_POSE_LABELS,
        axis_label="主体姿态",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


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


def detect_shot_scale_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in SHOT_SCALE_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _SHOT_SCALE_LABELS,
        axis_label="景别",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_shot_scale_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context = _clean(context_text)
    context_positive = detect_shot_scale(context, require_context_scope=True)
    if len(context_positive) > 1:
        return {}
    context_constraint = _context_shot_scale_constraint(context)
    if context_constraint:
        return context_constraint
    selected_text = "，".join(_unique(selected_values, 32))
    positive = detect_shot_scale(selected_text, require_context_scope=True)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _SHOT_SCALE_LABELS,
        axis_label="景别",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


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


def detect_camera_angle_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in CAMERA_ANGLE_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _CAMERA_ANGLE_LABELS,
        axis_label="机位",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_camera_angle_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context = _clean(context_text)
    context_positive = detect_camera_angle(context, require_context_scope=True)
    if len(context_positive) > 1:
        return {}
    context_constraint = _context_camera_angle_constraint(context)
    if context_constraint:
        return context_constraint
    selected_text = "，".join(_unique(selected_values, 32))
    positive = detect_camera_angle(selected_text, require_context_scope=True)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _CAMERA_ANGLE_LABELS,
        axis_label="机位",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


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


def detect_light_temperature_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in LIGHT_TEMPERATURE_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _LIGHT_TEMPERATURE_LABELS,
        axis_label="整体色温",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_light_temperature_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context = _clean(context_text)
    context_positive = detect_light_temperature(context, require_context_scope=True)
    if len(context_positive) > 1:
        return {}
    context_constraint = _context_light_temperature_constraint(context)
    if context_constraint:
        return context_constraint
    selected_text = "，".join(_unique(selected_values, 32))
    positive = detect_light_temperature(selected_text, require_context_scope=True)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _LIGHT_TEMPERATURE_LABELS,
        axis_label="整体色温",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_color_rendering(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        COLOR_RENDERING_MARKERS,
        negated=False,
    )


def detect_color_rendering_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in COLOR_RENDERING_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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


def detect_depth_of_field_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in DEPTH_OF_FIELD_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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


def detect_lighting_quality_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in LIGHTING_QUALITY_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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


def detect_motion_rendering_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in MOTION_RENDERING_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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


def detect_camera_stability_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in CAMERA_STABILITY_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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


def detect_focal_perspective_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in FOCAL_PERSPECTIVE_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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


def detect_key_light_direction_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in KEY_LIGHT_DIRECTION_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


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


def detect_exposure_key(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        EXPOSURE_KEY_MARKERS,
        negated=False,
    )


def detect_exposure_key_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in EXPOSURE_KEY_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_exposure_key(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        EXPOSURE_KEY_MARKERS,
        negated=True,
    )


def _context_exposure_key_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _COMPLEX_EXPOSURE_KEY_RE.search(source):
        return {}
    positive = detect_exposure_key(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_exposure_key(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _EXPOSURE_KEY_LABELS,
        axis_label="曝光调性",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_exposure_key_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_exposure_key_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _COMPLEX_EXPOSURE_KEY_RE.search(context) or len(detect_exposure_key(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _COMPLEX_EXPOSURE_KEY_RE.search(selected_text):
        return {}
    positive = detect_exposure_key(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _EXPOSURE_KEY_LABELS,
        axis_label="曝光调性",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_contrast_level(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    hits = _detect_exclusive_visual_axis(
        source,
        CONTRAST_LEVEL_MARKERS,
        negated=False,
    )
    if source.casefold() in {"低对比", "low contrast", "low-contrast"}:
        hits.setdefault("low", []).append(source)
    return hits


def detect_contrast_level_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in CONTRAST_LEVEL_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_contrast_level(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        CONTRAST_LEVEL_MARKERS,
        negated=True,
    )


def _context_contrast_level_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _COMPLEX_CONTRAST_RE.search(source):
        return {}
    positive = detect_contrast_level(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_contrast_level(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _CONTRAST_LEVEL_LABELS,
        axis_label="整体对比度",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_contrast_level_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_contrast_level_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _COMPLEX_CONTRAST_RE.search(context) or len(detect_contrast_level(context)) > 1:
        return {}
    selected = _unique(selected_values, 32)
    selected_text = "，".join(selected)
    if _COMPLEX_CONTRAST_RE.search(selected_text):
        return {}
    positive: dict[str, list[str]] = {}
    for value in selected:
        for contrast, markers in detect_contrast_level(value).items():
            positive.setdefault(contrast, []).extend(markers)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _CONTRAST_LEVEL_LABELS,
        axis_label="整体对比度",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_saturation_level(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SATURATION_LEVEL_MARKERS,
        negated=False,
    )


def detect_saturation_level_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in SATURATION_LEVEL_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_saturation_level(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SATURATION_LEVEL_MARKERS,
        negated=True,
    )


def _context_saturation_level_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _SELECTIVE_SATURATION_RE.search(source):
        return {}
    positive = detect_saturation_level(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_saturation_level(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _SATURATION_LEVEL_LABELS,
        axis_label="整体饱和度",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_saturation_level_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_saturation_level_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _SELECTIVE_SATURATION_RE.search(context) or len(detect_saturation_level(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _SELECTIVE_SATURATION_RE.search(selected_text):
        return {}
    positive = detect_saturation_level(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _SATURATION_LEVEL_LABELS,
        axis_label="整体饱和度",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def _without_nonvisual_grain_hits(
    source: str,
    hits: dict[str, list[str]],
) -> dict[str, list[str]]:
    if _NONVISUAL_GRAIN_RE.search(source) and "grainy" in hits:
        explicit_imaging_markers = {
            marker
            for marker in hits["grainy"]
            if marker not in {"颗粒感", "颗粒质感"}
        }
        if explicit_imaging_markers:
            hits["grainy"] = [
                marker for marker in hits["grainy"] if marker in explicit_imaging_markers
            ]
        else:
            hits.pop("grainy", None)
    return hits


def detect_image_grain(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    return _without_nonvisual_grain_hits(
        source,
        _detect_exclusive_visual_axis(
            source,
            IMAGE_GRAIN_MARKERS,
            negated=False,
        ),
    )


def detect_image_grain_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in IMAGE_GRAIN_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_image_grain(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    return _without_nonvisual_grain_hits(
        source,
        _detect_exclusive_visual_axis(
            source,
            IMAGE_GRAIN_MARKERS,
            negated=True,
        ),
    )


def _context_image_grain_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _SELECTIVE_IMAGE_GRAIN_RE.search(source):
        return {}
    positive = detect_image_grain(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_image_grain(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _IMAGE_GRAIN_LABELS,
        axis_label="成像颗粒质感",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_image_grain_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_image_grain_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _SELECTIVE_IMAGE_GRAIN_RE.search(context) or len(detect_image_grain(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _SELECTIVE_IMAGE_GRAIN_RE.search(selected_text):
        return {}
    positive = detect_image_grain(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _IMAGE_GRAIN_LABELS,
        axis_label="成像颗粒质感",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_image_sharpness(
    text: Any,
    *,
    require_context_scope: bool = False,
) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        IMAGE_SHARPNESS_MARKERS,
        negated=False,
        require_context_scope=require_context_scope,
        generic_markers=_GENERIC_IMAGE_SHARPNESS_MARKERS,
        global_scope_re=_IMAGE_SHARPNESS_GLOBAL_SCOPE_RE,
        prefix_scope_re=_IMAGE_SHARPNESS_PREFIX_SCOPE_RE,
        suffix_scope_re=_IMAGE_SHARPNESS_SUFFIX_SCOPE_RE,
    )


def detect_image_sharpness_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in IMAGE_SHARPNESS_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_image_sharpness(
    text: Any,
    *,
    require_context_scope: bool = False,
) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        IMAGE_SHARPNESS_MARKERS,
        negated=True,
        require_context_scope=require_context_scope,
        generic_markers=_GENERIC_IMAGE_SHARPNESS_MARKERS,
        global_scope_re=_IMAGE_SHARPNESS_GLOBAL_SCOPE_RE,
        prefix_scope_re=_IMAGE_SHARPNESS_PREFIX_SCOPE_RE,
        suffix_scope_re=_IMAGE_SHARPNESS_SUFFIX_SCOPE_RE,
    )


def _context_image_sharpness_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _SELECTIVE_IMAGE_SHARPNESS_RE.search(source):
        return {}
    positive = detect_image_sharpness(source, require_context_scope=True)
    if len(positive) > 1:
        return {}
    negated = detect_negated_image_sharpness(source, require_context_scope=True)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _IMAGE_SHARPNESS_LABELS,
        axis_label="整体成像锐度",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_image_sharpness_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_image_sharpness_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if (
        _SELECTIVE_IMAGE_SHARPNESS_RE.search(context)
        or len(detect_image_sharpness(context, require_context_scope=True)) > 1
    ):
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _SELECTIVE_IMAGE_SHARPNESS_RE.search(selected_text):
        return {}
    positive = detect_image_sharpness(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _IMAGE_SHARPNESS_LABELS,
        axis_label="整体成像锐度",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_detail_density(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        DETAIL_DENSITY_MARKERS,
        negated=False,
    )


def detect_detail_density_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in DETAIL_DENSITY_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_detail_density(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        DETAIL_DENSITY_MARKERS,
        negated=True,
    )


def _context_detail_density_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _SELECTIVE_DETAIL_DENSITY_RE.search(source):
        return {}
    positive = detect_detail_density(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_detail_density(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _DETAIL_DENSITY_LABELS,
        axis_label="整体细节密度",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_detail_density_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_detail_density_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _SELECTIVE_DETAIL_DENSITY_RE.search(context) or len(detect_detail_density(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _SELECTIVE_DETAIL_DENSITY_RE.search(selected_text):
        return {}
    positive = detect_detail_density(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _DETAIL_DENSITY_LABELS,
        axis_label="整体细节密度",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_visual_medium(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        VISUAL_MEDIUM_MARKERS,
        negated=False,
    )


def detect_visual_medium_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in VISUAL_MEDIUM_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_visual_medium(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        VISUAL_MEDIUM_MARKERS,
        negated=True,
    )


def _context_visual_medium_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_VISUAL_MEDIUM_RE.search(source):
        return {}
    positive = detect_visual_medium(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_visual_medium(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _VISUAL_MEDIUM_LABELS,
        axis_label="画面媒介",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_visual_medium_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_visual_medium_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _MIXED_VISUAL_MEDIUM_RE.search(context) or len(detect_visual_medium(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_VISUAL_MEDIUM_RE.search(selected_text):
        return {}
    positive = detect_visual_medium(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _VISUAL_MEDIUM_LABELS,
        axis_label="画面媒介",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_projection_geometry(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        PROJECTION_GEOMETRY_MARKERS,
        negated=False,
    )


def detect_projection_geometry_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in PROJECTION_GEOMETRY_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_projection_geometry(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        PROJECTION_GEOMETRY_MARKERS,
        negated=True,
    )


def _context_projection_geometry_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_PROJECTION_GEOMETRY_RE.search(source):
        return {}
    positive = detect_projection_geometry(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_projection_geometry(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _PROJECTION_GEOMETRY_LABELS,
        axis_label="投影几何",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_projection_geometry_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_projection_geometry_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if (
        _MIXED_PROJECTION_GEOMETRY_RE.search(context)
        or len(detect_projection_geometry(context)) > 1
    ):
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_PROJECTION_GEOMETRY_RE.search(selected_text):
        return {}
    positive = detect_projection_geometry(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _PROJECTION_GEOMETRY_LABELS,
        axis_label="投影几何",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_perspective_layout(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        PERSPECTIVE_LAYOUT_MARKERS,
        negated=False,
    )


def detect_perspective_layout_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in PERSPECTIVE_LAYOUT_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_perspective_layout(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        PERSPECTIVE_LAYOUT_MARKERS,
        negated=True,
    )


def _context_perspective_layout_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_PERSPECTIVE_LAYOUT_RE.search(source):
        return {}
    positive = detect_perspective_layout(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_perspective_layout(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _PERSPECTIVE_LAYOUT_LABELS,
        axis_label="透视消失点结构",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_perspective_layout_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_perspective_layout_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if (
        _MIXED_PERSPECTIVE_LAYOUT_RE.search(context)
        or len(detect_perspective_layout(context)) > 1
    ):
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_PERSPECTIVE_LAYOUT_RE.search(selected_text):
        return {}
    positive = detect_perspective_layout(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _PERSPECTIVE_LAYOUT_LABELS,
        axis_label="透视消失点结构",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_camera_roll(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        CAMERA_ROLL_MARKERS,
        negated=False,
    )


def detect_camera_roll_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in CAMERA_ROLL_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_camera_roll(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        CAMERA_ROLL_MARKERS,
        negated=True,
    )


def _context_camera_roll_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_CAMERA_ROLL_RE.search(source):
        return {}
    positive = detect_camera_roll(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_camera_roll(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _CAMERA_ROLL_LABELS,
        axis_label="画幅滚转",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_camera_roll_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_camera_roll_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _MIXED_CAMERA_ROLL_RE.search(context) or len(detect_camera_roll(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_CAMERA_ROLL_RE.search(selected_text):
        return {}
    positive = detect_camera_roll(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _CAMERA_ROLL_LABELS,
        axis_label="画幅滚转",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_composition_placement(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        COMPOSITION_PLACEMENT_MARKERS,
        negated=False,
    )


def detect_composition_placement_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in COMPOSITION_PLACEMENT_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_composition_placement(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        COMPOSITION_PLACEMENT_MARKERS,
        negated=True,
    )


def _context_composition_placement_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_COMPOSITION_PLACEMENT_RE.search(source):
        return {}
    positive = detect_composition_placement(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_composition_placement(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _COMPOSITION_PLACEMENT_LABELS,
        axis_label="主体构图落点",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_composition_placement_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_composition_placement_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if (
        _MIXED_COMPOSITION_PLACEMENT_RE.search(context)
        or len(detect_composition_placement(context)) > 1
    ):
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_COMPOSITION_PLACEMENT_RE.search(selected_text):
        return {}
    positive = detect_composition_placement(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _COMPOSITION_PLACEMENT_LABELS,
        axis_label="主体构图落点",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_screen_direction(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SCREEN_DIRECTION_MARKERS,
        negated=False,
    )


def detect_screen_direction_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in SCREEN_DIRECTION_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_screen_direction(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SCREEN_DIRECTION_MARKERS,
        negated=True,
    )


def _context_screen_direction_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_SCREEN_DIRECTION_RE.search(source):
        return {}
    positive = detect_screen_direction(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_screen_direction(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _SCREEN_DIRECTION_LABELS,
        axis_label="横向屏幕方向",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_screen_direction_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_screen_direction_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _MIXED_SCREEN_DIRECTION_RE.search(context) or len(detect_screen_direction(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_SCREEN_DIRECTION_RE.search(selected_text):
        return {}
    positive = detect_screen_direction(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _SCREEN_DIRECTION_LABELS,
        axis_label="横向屏幕方向",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_spatial_axis_continuity(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SPATIAL_AXIS_CONTINUITY_MARKERS,
        negated=False,
    )


def detect_spatial_axis_continuity_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in SPATIAL_AXIS_CONTINUITY_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_spatial_axis_continuity(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SPATIAL_AXIS_CONTINUITY_MARKERS,
        negated=True,
    )


def _context_spatial_axis_continuity_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_SPATIAL_AXIS_CONTINUITY_RE.search(source):
        return {}
    positive = detect_spatial_axis_continuity(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_spatial_axis_continuity(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _SPATIAL_AXIS_CONTINUITY_LABELS,
        axis_label="空间轴线连续性",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_spatial_axis_continuity_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_spatial_axis_continuity_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if (
        _MIXED_SPATIAL_AXIS_CONTINUITY_RE.search(context)
        or len(detect_spatial_axis_continuity(context)) > 1
    ):
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_SPATIAL_AXIS_CONTINUITY_RE.search(selected_text):
        return {}
    positive = detect_spatial_axis_continuity(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _SPATIAL_AXIS_CONTINUITY_LABELS,
        axis_label="空间轴线连续性",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_foreground_occlusion(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        FOREGROUND_OCCLUSION_MARKERS,
        negated=False,
    )


def detect_foreground_occlusion_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in FOREGROUND_OCCLUSION_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_foreground_occlusion(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        FOREGROUND_OCCLUSION_MARKERS,
        negated=True,
    )


def _context_foreground_occlusion_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_FOREGROUND_OCCLUSION_RE.search(source):
        return {}
    positive = detect_foreground_occlusion(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_foreground_occlusion(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _FOREGROUND_OCCLUSION_LABELS,
        axis_label="前景遮挡关系",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_foreground_occlusion_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_foreground_occlusion_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if (
        _MIXED_FOREGROUND_OCCLUSION_RE.search(context)
        or len(detect_foreground_occlusion(context)) > 1
    ):
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_FOREGROUND_OCCLUSION_RE.search(selected_text):
        return {}
    positive = detect_foreground_occlusion(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _FOREGROUND_OCCLUSION_LABELS,
        axis_label="前景遮挡关系",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_subject_support_state(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SUBJECT_SUPPORT_STATE_MARKERS,
        negated=False,
    )


def detect_subject_support_state_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in SUBJECT_SUPPORT_STATE_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_subject_support_state(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SUBJECT_SUPPORT_STATE_MARKERS,
        negated=True,
    )


def _context_subject_support_state_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_SUBJECT_SUPPORT_STATE_RE.search(source):
        return {}
    positive = detect_subject_support_state(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_subject_support_state(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _SUBJECT_SUPPORT_STATE_LABELS,
        axis_label="主体支撑状态",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_subject_support_state_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_subject_support_state_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if (
        _MIXED_SUBJECT_SUPPORT_STATE_RE.search(context)
        or len(detect_subject_support_state(context)) > 1
    ):
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_SUBJECT_SUPPORT_STATE_RE.search(selected_text):
        return {}
    positive = detect_subject_support_state(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _SUBJECT_SUPPORT_STATE_LABELS,
        axis_label="主体支撑状态",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_gaze_target(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        GAZE_TARGET_MARKERS,
        negated=False,
    )


def detect_gaze_target_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in GAZE_TARGET_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_gaze_target(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        GAZE_TARGET_MARKERS,
        negated=True,
    )


def _context_gaze_target_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_GAZE_TARGET_RE.search(source):
        return {}
    positive = detect_gaze_target(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_gaze_target(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _GAZE_TARGET_LABELS,
        axis_label="视线目标",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_gaze_target_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_gaze_target_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _MIXED_GAZE_TARGET_RE.search(context) or len(detect_gaze_target(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_GAZE_TARGET_RE.search(selected_text):
        return {}
    positive = detect_gaze_target(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _GAZE_TARGET_LABELS,
        axis_label="视线目标",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_atmospheric_medium(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        ATMOSPHERIC_MEDIUM_MARKERS,
        negated=False,
    )


def detect_atmospheric_medium_feedback(text: Any) -> dict[str, list[str]]:
    source = _clean(text)
    folded = source.casefold()
    hits: dict[str, list[str]] = {}
    for value, patterns in ATMOSPHERIC_MEDIUM_FEEDBACK_PATTERNS.items():
        evidence: list[str] = []
        for pattern in patterns:
            for match in pattern.finditer(source):
                if _marker_match_is_negated(folded, match.start()):
                    continue
                fragment = _clean(match.group(0))
                if fragment and fragment not in evidence:
                    evidence.append(fragment)
        if evidence:
            hits[value] = evidence
    return hits


def detect_negated_atmospheric_medium(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        ATMOSPHERIC_MEDIUM_MARKERS,
        negated=True,
    )


def _context_atmospheric_medium_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_ATMOSPHERIC_MEDIUM_RE.search(source):
        return {}
    positive = detect_atmospheric_medium(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_atmospheric_medium(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _ATMOSPHERIC_MEDIUM_LABELS,
        axis_label="大气介质与能见度",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_atmospheric_medium_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_atmospheric_medium_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if (
        _MIXED_ATMOSPHERIC_MEDIUM_RE.search(context)
        or len(detect_atmospheric_medium(context)) > 1
    ):
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_ATMOSPHERIC_MEDIUM_RE.search(selected_text):
        return {}
    positive = detect_atmospheric_medium(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _ATMOSPHERIC_MEDIUM_LABELS,
        axis_label="大气介质与能见度",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_background_complexity(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        BACKGROUND_COMPLEXITY_MARKERS,
        negated=False,
    )


def detect_negated_background_complexity(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        BACKGROUND_COMPLEXITY_MARKERS,
        negated=True,
    )


def _context_background_complexity_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_BACKGROUND_COMPLEXITY_RE.search(source):
        return {}
    positive = detect_background_complexity(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_background_complexity(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _BACKGROUND_COMPLEXITY_LABELS,
        axis_label="背景复杂度",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_background_complexity_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_background_complexity_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _MIXED_BACKGROUND_COMPLEXITY_RE.search(context) or len(detect_background_complexity(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_BACKGROUND_COMPLEXITY_RE.search(selected_text):
        return {}
    positive = detect_background_complexity(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _BACKGROUND_COMPLEXITY_LABELS,
        axis_label="背景复杂度",
    )
    if constraint:
        constraint["source"] = "selected_state"
    return constraint


def detect_season(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SEASON_MARKERS,
        negated=False,
    )


def detect_negated_season(text: Any) -> dict[str, list[str]]:
    return _detect_exclusive_visual_axis(
        text,
        SEASON_MARKERS,
        negated=True,
    )


def _context_season_constraint(text: Any) -> dict[str, Any]:
    source = _clean(text)
    if _MIXED_SEASON_RE.search(source):
        return {}
    positive = detect_season(source)
    if len(positive) > 1:
        return {}
    negated = detect_negated_season(source)
    constraint = _exclusive_visual_axis_constraint(
        positive,
        negated,
        _SEASON_LABELS,
        axis_label="季节连续性",
    )
    if constraint:
        constraint["source"] = "natural_context"
    return constraint


def _resolve_season_constraint(
    context_text: Any,
    selected_values: Iterable[Any],
) -> dict[str, Any]:
    context_constraint = _context_season_constraint(context_text)
    if context_constraint:
        return context_constraint
    context = _clean(context_text)
    if _MIXED_SEASON_RE.search(context) or len(detect_season(context)) > 1:
        return {}
    selected_text = "，".join(_unique(selected_values, 32))
    if _MIXED_SEASON_RE.search(selected_text):
        return {}
    positive = detect_season(selected_text)
    if len(positive) != 1:
        return {}
    constraint = _exclusive_visual_axis_constraint(
        positive,
        {},
        _SEASON_LABELS,
        axis_label="季节连续性",
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
    scene_attribute_values = [
        value
        for group in ("画面风格", "场景背景", "光影氛围", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    scene_attribute_constraints = _resolve_scene_attribute_constraints(
        natural_context,
        scene_attribute_values,
    )
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
    subject_orientation_values = [
        value
        for group in ("构图视角", "动作姿态")
        for value in groups.get(group, [])
    ] + list(custom)
    context_subject_orientation_constraint = _resolve_subject_orientation_constraint(
        natural_context,
        subject_orientation_values,
    )
    context_subject_pose = detect_subject_pose(natural_context)
    negated_context_subject_pose = detect_negated_subject_pose(natural_context)
    subject_pose_values = list(groups.get("动作姿态", [])) + list(custom)
    context_subject_pose_constraint = _resolve_subject_pose_constraint(
        natural_context,
        subject_pose_values,
    )
    context_shot_scale = detect_shot_scale(natural_context, require_context_scope=True)
    negated_context_shot_scale = detect_negated_shot_scale(natural_context, require_context_scope=True)
    shot_scale_values = list(groups.get("构图视角", [])) + list(custom)
    context_shot_scale_constraint = _resolve_shot_scale_constraint(
        natural_context,
        shot_scale_values,
    )
    context_camera_angle = detect_camera_angle(natural_context, require_context_scope=True)
    negated_context_camera_angle = detect_negated_camera_angle(natural_context, require_context_scope=True)
    camera_angle_values = list(groups.get("构图视角", [])) + list(custom)
    context_camera_angle_constraint = _resolve_camera_angle_constraint(
        natural_context,
        camera_angle_values,
    )
    context_light_temperature = detect_light_temperature(natural_context, require_context_scope=True)
    negated_context_light_temperature = detect_negated_light_temperature(
        natural_context,
        require_context_scope=True,
    )
    light_temperature_values = [
        value
        for group in ("光影氛围", "画面风格", "场景背景", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    context_light_temperature_constraint = _resolve_light_temperature_constraint(
        natural_context,
        light_temperature_values,
    )
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
    context_exposure_key = detect_exposure_key(natural_context)
    negated_context_exposure_key = detect_negated_exposure_key(natural_context)
    exposure_key_values = [
        value
        for group in ("光影氛围", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    exposure_key_constraint = _resolve_exposure_key_constraint(
        natural_context,
        exposure_key_values,
    )
    context_contrast_level = detect_contrast_level(natural_context)
    negated_context_contrast_level = detect_negated_contrast_level(natural_context)
    contrast_level_values = [
        value
        for group in ("光影氛围", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    contrast_level_constraint = _resolve_contrast_level_constraint(
        natural_context,
        contrast_level_values,
    )
    context_saturation_level = detect_saturation_level(natural_context)
    negated_context_saturation_level = detect_negated_saturation_level(natural_context)
    saturation_level_values = [
        value
        for group in ("光影氛围", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    saturation_level_constraint = _resolve_saturation_level_constraint(
        natural_context,
        saturation_level_values,
    )
    context_image_grain = detect_image_grain(natural_context)
    negated_context_image_grain = detect_negated_image_grain(natural_context)
    image_grain_values = [
        value
        for group in ("技术画质", "画面风格", "光影氛围")
        for value in groups.get(group, [])
    ] + list(custom)
    image_grain_constraint = _resolve_image_grain_constraint(
        natural_context,
        image_grain_values,
    )
    context_image_sharpness = detect_image_sharpness(
        natural_context,
        require_context_scope=True,
    )
    negated_context_image_sharpness = detect_negated_image_sharpness(
        natural_context,
        require_context_scope=True,
    )
    image_sharpness_values = [
        value
        for group in ("技术画质", "画面风格", "光影氛围", "构图视角")
        for value in groups.get(group, [])
    ] + list(custom)
    image_sharpness_constraint = _resolve_image_sharpness_constraint(
        natural_context,
        image_sharpness_values,
    )
    context_detail_density = detect_detail_density(natural_context)
    negated_context_detail_density = detect_negated_detail_density(natural_context)
    detail_density_values = [
        value
        for group in ("技术画质", "画面风格", "光影氛围", "构图视角")
        for value in groups.get(group, [])
    ] + list(custom)
    detail_density_constraint = _resolve_detail_density_constraint(
        natural_context,
        detail_density_values,
    )
    context_visual_medium = detect_visual_medium(natural_context)
    negated_context_visual_medium = detect_negated_visual_medium(natural_context)
    visual_medium_values = [
        value
        for group in ("画面风格", "技术画质", "构图视角", "光影氛围")
        for value in groups.get(group, [])
    ] + list(custom)
    visual_medium_constraint = _resolve_visual_medium_constraint(
        natural_context,
        visual_medium_values,
    )
    context_projection_geometry = detect_projection_geometry(natural_context)
    negated_context_projection_geometry = detect_negated_projection_geometry(natural_context)
    projection_geometry_values = [
        value
        for group in ("构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + list(custom)
    projection_geometry_constraint = _resolve_projection_geometry_constraint(
        natural_context,
        projection_geometry_values,
    )
    context_perspective_layout = detect_perspective_layout(natural_context)
    negated_context_perspective_layout = detect_negated_perspective_layout(natural_context)
    perspective_layout_values = [
        value
        for group in ("构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + list(custom)
    perspective_layout_constraint = _resolve_perspective_layout_constraint(
        natural_context,
        perspective_layout_values,
    )
    context_camera_roll = detect_camera_roll(natural_context)
    negated_context_camera_roll = detect_negated_camera_roll(natural_context)
    camera_roll_values = [
        value
        for group in ("构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + list(custom)
    camera_roll_constraint = _resolve_camera_roll_constraint(
        natural_context,
        camera_roll_values,
    )
    context_composition_placement = detect_composition_placement(natural_context)
    negated_context_composition_placement = detect_negated_composition_placement(natural_context)
    composition_placement_values = [
        value
        for group in ("主体", "构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + list(custom)
    composition_placement_constraint = _resolve_composition_placement_constraint(
        natural_context,
        composition_placement_values,
    )
    context_screen_direction = detect_screen_direction(natural_context)
    negated_context_screen_direction = detect_negated_screen_direction(natural_context)
    screen_direction_values = [
        value
        for group in ("主体", "动作姿态", "构图视角", "道具世界观")
        for value in groups.get(group, [])
    ] + list(custom)
    screen_direction_constraint = _resolve_screen_direction_constraint(
        natural_context,
        screen_direction_values,
    )
    context_spatial_axis_continuity = detect_spatial_axis_continuity(natural_context)
    negated_context_spatial_axis_continuity = detect_negated_spatial_axis_continuity(
        natural_context
    )
    spatial_axis_continuity_values = [
        value
        for group in ("主体", "动作姿态", "构图视角", "场景背景", "道具世界观")
        for value in groups.get(group, [])
    ] + list(custom)
    spatial_axis_continuity_constraint = _resolve_spatial_axis_continuity_constraint(
        natural_context,
        spatial_axis_continuity_values,
    )
    context_foreground_occlusion = detect_foreground_occlusion(natural_context)
    negated_context_foreground_occlusion = detect_negated_foreground_occlusion(
        natural_context
    )
    foreground_occlusion_values = [
        value
        for group in ("主体", "构图视角", "场景背景", "道具世界观", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    foreground_occlusion_constraint = _resolve_foreground_occlusion_constraint(
        natural_context,
        foreground_occlusion_values,
    )
    context_subject_support_state = detect_subject_support_state(natural_context)
    negated_context_subject_support_state = detect_negated_subject_support_state(
        natural_context
    )
    subject_support_state_values = [
        value
        for group in ("主体", "动作姿态", "构图视角", "场景背景", "道具世界观")
        for value in groups.get(group, [])
    ] + list(custom)
    subject_support_state_constraint = _resolve_subject_support_state_constraint(
        natural_context,
        subject_support_state_values,
    )
    context_gaze_target = detect_gaze_target(natural_context)
    negated_context_gaze_target = detect_negated_gaze_target(natural_context)
    gaze_target_values = [
        value
        for group in ("主体", "动作姿态", "构图视角", "道具世界观")
        for value in groups.get(group, [])
    ] + list(custom)
    gaze_target_constraint = _resolve_gaze_target_constraint(
        natural_context,
        gaze_target_values,
    )
    context_atmospheric_medium = detect_atmospheric_medium(natural_context)
    negated_context_atmospheric_medium = detect_negated_atmospheric_medium(natural_context)
    atmospheric_medium_values = [
        value
        for group in ("光影氛围", "场景背景", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + list(custom)
    atmospheric_medium_constraint = _resolve_atmospheric_medium_constraint(
        natural_context,
        atmospheric_medium_values,
    )
    context_background_complexity = detect_background_complexity(natural_context)
    negated_context_background_complexity = detect_negated_background_complexity(natural_context)
    background_complexity_values = [
        value
        for group in ("场景背景", "构图视角", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    background_complexity_constraint = _resolve_background_complexity_constraint(
        natural_context,
        background_complexity_values,
    )
    context_season = detect_season(natural_context)
    negated_context_season = detect_negated_season(natural_context)
    season_values = [
        value
        for group in ("场景背景", "光影氛围", "画面风格", "服装造型", "技术画质")
        for value in groups.get(group, [])
    ] + list(custom)
    season_constraint = _resolve_season_constraint(
        natural_context,
        season_values,
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
        for axis, constraint in scene_attribute_constraints.items():
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
            for constraint in scene_attribute_constraints.values()
        )
        coherence_issues.append(
            {
                "kind": "context_scene_attribute_conflict",
                "severity": "error",
                "constraints": deepcopy(context_scene_attribute_constraints),
                "conflicting_anchors": conflicting_attribute_anchors,
                "message": (
                    f"自然语言已明确场景属性“{constraint_summary}”，"
                    "但当前风格、场景、光影或补充标签仍包含相反的昼夜、降水、风势、环境温度、地表状态、空间围合或主导照明来源。"
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
    exposure_key_anchors = [
        {"group": group, "value": value}
        for group in ("光影氛围", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_exposure_key_anchors = _conflicting_exclusive_axis_anchors(
        exposure_key_anchors,
        exposure_key_constraint,
        detect_exposure_key,
        _EXPOSURE_KEY_LABELS,
    )
    if conflicting_exposure_key_anchors:
        required_label = _clean(exposure_key_constraint.get("required_label"))
        negated_labels = list(exposure_key_constraint.get("negated_labels", []) or [])
        exposure_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_exposure_key_conflict",
                "severity": "error",
                "constraint": deepcopy(exposure_key_constraint),
                "conflicting_anchors": conflicting_exposure_key_anchors,
                "message": (
                    f"自然语言已明确曝光调性“{exposure_summary}”，"
                    "但当前光影、风格、画质或补充标签仍包含相反高低键关系。"
                ),
            }
        )
    contrast_level_anchors = [
        {"group": group, "value": value}
        for group in ("光影氛围", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_contrast_level_anchors = _conflicting_exclusive_axis_anchors(
        contrast_level_anchors,
        contrast_level_constraint,
        detect_contrast_level,
        _CONTRAST_LEVEL_LABELS,
    )
    if conflicting_contrast_level_anchors:
        required_label = _clean(contrast_level_constraint.get("required_label"))
        negated_labels = list(contrast_level_constraint.get("negated_labels", []) or [])
        contrast_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_contrast_level_conflict",
                "severity": "error",
                "constraint": deepcopy(contrast_level_constraint),
                "conflicting_anchors": conflicting_contrast_level_anchors,
                "message": (
                    f"自然语言已明确整体对比度“{contrast_summary}”，"
                    "但当前光影、风格、画质或补充标签仍包含相反反差关系。"
                ),
            }
        )
    saturation_level_anchors = [
        {"group": group, "value": value}
        for group in ("光影氛围", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_saturation_level_anchors = _conflicting_exclusive_axis_anchors(
        saturation_level_anchors,
        saturation_level_constraint,
        detect_saturation_level,
        _SATURATION_LEVEL_LABELS,
    )
    if conflicting_saturation_level_anchors:
        required_label = _clean(saturation_level_constraint.get("required_label"))
        negated_labels = list(saturation_level_constraint.get("negated_labels", []) or [])
        saturation_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_saturation_level_conflict",
                "severity": "error",
                "constraint": deepcopy(saturation_level_constraint),
                "conflicting_anchors": conflicting_saturation_level_anchors,
                "message": (
                    f"自然语言已明确整体饱和度“{saturation_summary}”，"
                    "但当前光影、风格、画质或补充标签仍包含相反色彩浓度。"
                ),
            }
        )
    image_grain_anchors = [
        {"group": group, "value": value}
        for group in ("技术画质", "画面风格", "光影氛围")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_image_grain_anchors = _conflicting_exclusive_axis_anchors(
        image_grain_anchors,
        image_grain_constraint,
        detect_image_grain,
        _IMAGE_GRAIN_LABELS,
    )
    if conflicting_image_grain_anchors:
        required_label = _clean(image_grain_constraint.get("required_label"))
        negated_labels = list(image_grain_constraint.get("negated_labels", []) or [])
        grain_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_image_grain_conflict",
                "severity": "error",
                "constraint": deepcopy(image_grain_constraint),
                "conflicting_anchors": conflicting_image_grain_anchors,
                "message": (
                    f"自然语言已明确成像颗粒质感“{grain_summary}”，"
                    "但当前风格、光影、画质或补充标签仍包含相反颗粒关系。"
                ),
            }
        )
    image_sharpness_anchors = [
        {"group": group, "value": value}
        for group in ("技术画质", "画面风格", "光影氛围", "构图视角")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_image_sharpness_anchors = _conflicting_exclusive_axis_anchors(
        image_sharpness_anchors,
        image_sharpness_constraint,
        detect_image_sharpness,
        _IMAGE_SHARPNESS_LABELS,
    )
    if conflicting_image_sharpness_anchors:
        required_label = _clean(image_sharpness_constraint.get("required_label"))
        negated_labels = list(image_sharpness_constraint.get("negated_labels", []) or [])
        sharpness_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_image_sharpness_conflict",
                "severity": "error",
                "constraint": deepcopy(image_sharpness_constraint),
                "conflicting_anchors": conflicting_image_sharpness_anchors,
                "message": (
                    f"自然语言已明确整体成像锐度“{sharpness_summary}”，"
                    "但当前风格、光影、构图、画质或补充标签仍包含相反锐度关系。"
                ),
            }
        )
    detail_density_anchors = [
        {"group": group, "value": value}
        for group in ("技术画质", "画面风格", "光影氛围", "构图视角")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_detail_density_anchors = _conflicting_exclusive_axis_anchors(
        detail_density_anchors,
        detail_density_constraint,
        detect_detail_density,
        _DETAIL_DENSITY_LABELS,
    )
    if conflicting_detail_density_anchors:
        required_label = _clean(detail_density_constraint.get("required_label"))
        negated_labels = list(detail_density_constraint.get("negated_labels", []) or [])
        detail_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_detail_density_conflict",
                "severity": "error",
                "constraint": deepcopy(detail_density_constraint),
                "conflicting_anchors": conflicting_detail_density_anchors,
                "message": (
                    f"自然语言已明确整体细节密度“{detail_summary}”，"
                    "但当前风格、光影、构图、画质或补充标签仍包含相反细节密度。"
                ),
            }
        )
    visual_medium_anchors = [
        {"group": group, "value": value}
        for group in ("画面风格", "技术画质", "构图视角", "光影氛围")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_visual_medium_anchors = _conflicting_exclusive_axis_anchors(
        visual_medium_anchors,
        visual_medium_constraint,
        detect_visual_medium,
        _VISUAL_MEDIUM_LABELS,
    )
    if conflicting_visual_medium_anchors:
        required_label = _clean(visual_medium_constraint.get("required_label"))
        negated_labels = list(visual_medium_constraint.get("negated_labels", []) or [])
        medium_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_visual_medium_conflict",
                "severity": "error",
                "constraint": deepcopy(visual_medium_constraint),
                "conflicting_anchors": conflicting_visual_medium_anchors,
                "message": (
                    f"自然语言已明确画面媒介“{medium_summary}”，"
                    "但当前风格、画质、构图、光影或补充标签仍包含相反成片媒介。"
                ),
            }
        )
    projection_geometry_anchors = [
        {"group": group, "value": value}
        for group in ("构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_projection_geometry_anchors = _conflicting_exclusive_axis_anchors(
        projection_geometry_anchors,
        projection_geometry_constraint,
        detect_projection_geometry,
        _PROJECTION_GEOMETRY_LABELS,
    )
    if conflicting_projection_geometry_anchors:
        required_label = _clean(projection_geometry_constraint.get("required_label"))
        negated_labels = list(projection_geometry_constraint.get("negated_labels", []) or [])
        projection_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_projection_geometry_conflict",
                "severity": "error",
                "constraint": deepcopy(projection_geometry_constraint),
                "conflicting_anchors": conflicting_projection_geometry_anchors,
                "message": (
                    f"自然语言已明确投影几何“{projection_summary}”，"
                    "但当前构图、画质、风格或补充标签仍包含相反投影关系。"
                ),
            }
        )
    perspective_layout_anchors = [
        {"group": group, "value": value}
        for group in ("构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_perspective_layout_anchors = _conflicting_exclusive_axis_anchors(
        perspective_layout_anchors,
        perspective_layout_constraint,
        detect_perspective_layout,
        _PERSPECTIVE_LAYOUT_LABELS,
    )
    if conflicting_perspective_layout_anchors:
        required_label = _clean(perspective_layout_constraint.get("required_label"))
        negated_labels = list(perspective_layout_constraint.get("negated_labels", []) or [])
        layout_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_perspective_layout_conflict",
                "severity": "error",
                "constraint": deepcopy(perspective_layout_constraint),
                "conflicting_anchors": conflicting_perspective_layout_anchors,
                "message": (
                    f"自然语言已明确透视消失点结构“{layout_summary}”，"
                    "但当前构图、画质、风格或补充标签仍包含相反消失点布局。"
                ),
            }
        )
    camera_roll_anchors = [
        {"group": group, "value": value}
        for group in ("构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_camera_roll_anchors = _conflicting_exclusive_axis_anchors(
        camera_roll_anchors,
        camera_roll_constraint,
        detect_camera_roll,
        _CAMERA_ROLL_LABELS,
    )
    if conflicting_camera_roll_anchors:
        required_label = _clean(camera_roll_constraint.get("required_label"))
        negated_labels = list(camera_roll_constraint.get("negated_labels", []) or [])
        roll_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_camera_roll_conflict",
                "severity": "error",
                "constraint": deepcopy(camera_roll_constraint),
                "conflicting_anchors": conflicting_camera_roll_anchors,
                "message": (
                    f"自然语言已明确画幅滚转“{roll_summary}”，"
                    "但当前构图、画质、风格或补充标签仍包含相反滚转关系。"
                ),
            }
        )
    composition_placement_anchors = [
        {"group": group, "value": value}
        for group in ("主体", "构图视角", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_composition_placement_anchors = _conflicting_exclusive_axis_anchors(
        composition_placement_anchors,
        composition_placement_constraint,
        detect_composition_placement,
        _COMPOSITION_PLACEMENT_LABELS,
    )
    if conflicting_composition_placement_anchors:
        required_label = _clean(composition_placement_constraint.get("required_label"))
        negated_labels = list(composition_placement_constraint.get("negated_labels", []) or [])
        placement_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_composition_placement_conflict",
                "severity": "error",
                "constraint": deepcopy(composition_placement_constraint),
                "conflicting_anchors": conflicting_composition_placement_anchors,
                "message": (
                    f"自然语言已明确主体构图落点“{placement_summary}”，"
                    "但当前主体、构图、画质、风格或补充标签仍包含相反落点关系。"
                ),
            }
        )
    screen_direction_anchors = [
        {"group": group, "value": value}
        for group in ("主体", "动作姿态", "构图视角", "道具世界观")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_screen_direction_anchors = _conflicting_exclusive_axis_anchors(
        screen_direction_anchors,
        screen_direction_constraint,
        detect_screen_direction,
        _SCREEN_DIRECTION_LABELS,
    )
    if conflicting_screen_direction_anchors:
        required_label = _clean(screen_direction_constraint.get("required_label"))
        negated_labels = list(screen_direction_constraint.get("negated_labels", []) or [])
        direction_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_screen_direction_conflict",
                "severity": "error",
                "constraint": deepcopy(screen_direction_constraint),
                "conflicting_anchors": conflicting_screen_direction_anchors,
                "message": (
                    f"自然语言已明确横向屏幕方向“{direction_summary}”，"
                    "但当前主体、动作、构图、道具或补充标签仍包含相反屏幕方向。"
                ),
            }
        )
    spatial_axis_continuity_anchors = [
        {"group": group, "value": value}
        for group in ("主体", "动作姿态", "构图视角", "场景背景", "道具世界观")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_spatial_axis_continuity_anchors = _conflicting_exclusive_axis_anchors(
        spatial_axis_continuity_anchors,
        spatial_axis_continuity_constraint,
        detect_spatial_axis_continuity,
        _SPATIAL_AXIS_CONTINUITY_LABELS,
    )
    if conflicting_spatial_axis_continuity_anchors:
        required_label = _clean(spatial_axis_continuity_constraint.get("required_label"))
        negated_labels = list(
            spatial_axis_continuity_constraint.get("negated_labels", []) or []
        )
        axis_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_spatial_axis_continuity_conflict",
                "severity": "error",
                "constraint": deepcopy(spatial_axis_continuity_constraint),
                "conflicting_anchors": conflicting_spatial_axis_continuity_anchors,
                "message": (
                    f"自然语言已明确空间轴线连续性“{axis_summary}”，"
                    "但当前主体、动作、构图、场景、道具或补充标签仍包含相反越轴关系。"
                ),
            }
        )
    foreground_occlusion_anchors = [
        {"group": group, "value": value}
        for group in ("主体", "构图视角", "场景背景", "道具世界观", "技术画质")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_foreground_occlusion_anchors = _conflicting_exclusive_axis_anchors(
        foreground_occlusion_anchors,
        foreground_occlusion_constraint,
        detect_foreground_occlusion,
        _FOREGROUND_OCCLUSION_LABELS,
    )
    if conflicting_foreground_occlusion_anchors:
        required_label = _clean(foreground_occlusion_constraint.get("required_label"))
        negated_labels = list(
            foreground_occlusion_constraint.get("negated_labels", []) or []
        )
        occlusion_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_foreground_occlusion_conflict",
                "severity": "error",
                "constraint": deepcopy(foreground_occlusion_constraint),
                "conflicting_anchors": conflicting_foreground_occlusion_anchors,
                "message": (
                    f"自然语言已明确前景遮挡关系“{occlusion_summary}”，"
                    "但当前主体、构图、场景、道具、画质或补充标签仍包含相反遮挡关系。"
                ),
            }
        )
    subject_support_state_anchors = [
        {"group": group, "value": value}
        for group in ("主体", "动作姿态", "构图视角", "场景背景", "道具世界观")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_subject_support_state_anchors = _conflicting_exclusive_axis_anchors(
        subject_support_state_anchors,
        subject_support_state_constraint,
        detect_subject_support_state,
        _SUBJECT_SUPPORT_STATE_LABELS,
    )
    if conflicting_subject_support_state_anchors:
        required_label = _clean(subject_support_state_constraint.get("required_label"))
        negated_labels = list(
            subject_support_state_constraint.get("negated_labels", []) or []
        )
        support_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_subject_support_state_conflict",
                "severity": "error",
                "constraint": deepcopy(subject_support_state_constraint),
                "conflicting_anchors": conflicting_subject_support_state_anchors,
                "message": (
                    f"自然语言已明确主体支撑状态“{support_summary}”，"
                    "但当前主体、动作、构图、场景、道具或补充标签仍包含相反承重或离地关系。"
                ),
            }
        )
    gaze_target_anchors = [
        {"group": group, "value": value}
        for group in ("主体", "动作姿态", "构图视角", "道具世界观")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_gaze_target_anchors = _conflicting_exclusive_axis_anchors(
        gaze_target_anchors,
        gaze_target_constraint,
        detect_gaze_target,
        _GAZE_TARGET_LABELS,
    )
    if conflicting_gaze_target_anchors:
        required_label = _clean(gaze_target_constraint.get("required_label"))
        negated_labels = list(gaze_target_constraint.get("negated_labels", []) or [])
        gaze_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_gaze_target_conflict",
                "severity": "error",
                "constraint": deepcopy(gaze_target_constraint),
                "conflicting_anchors": conflicting_gaze_target_anchors,
                "message": (
                    f"自然语言已明确视线目标“{gaze_summary}”，"
                    "但当前主体、动作、构图、道具或补充标签仍包含相反视线关系。"
                ),
            }
        )
    atmospheric_medium_anchors = [
        {"group": group, "value": value}
        for group in ("光影氛围", "场景背景", "技术画质", "画面风格")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_atmospheric_medium_anchors = _conflicting_exclusive_axis_anchors(
        atmospheric_medium_anchors,
        atmospheric_medium_constraint,
        detect_atmospheric_medium,
        _ATMOSPHERIC_MEDIUM_LABELS,
    )
    if conflicting_atmospheric_medium_anchors:
        required_label = _clean(atmospheric_medium_constraint.get("required_label"))
        negated_labels = list(atmospheric_medium_constraint.get("negated_labels", []) or [])
        atmosphere_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_atmospheric_medium_conflict",
                "severity": "error",
                "constraint": deepcopy(atmospheric_medium_constraint),
                "conflicting_anchors": conflicting_atmospheric_medium_anchors,
                "message": (
                    f"自然语言已明确大气介质与能见度“{atmosphere_summary}”，"
                    "但当前光影、场景、画质、风格或补充标签仍包含相反空气状态。"
                ),
            }
        )
    background_complexity_anchors = [
        {"group": group, "value": value}
        for group in ("场景背景", "构图视角", "画面风格", "技术画质")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_background_complexity_anchors = _conflicting_exclusive_axis_anchors(
        background_complexity_anchors,
        background_complexity_constraint,
        detect_background_complexity,
        _BACKGROUND_COMPLEXITY_LABELS,
    )
    if conflicting_background_complexity_anchors:
        required_label = _clean(background_complexity_constraint.get("required_label"))
        negated_labels = list(background_complexity_constraint.get("negated_labels", []) or [])
        background_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_background_complexity_conflict",
                "severity": "error",
                "constraint": deepcopy(background_complexity_constraint),
                "conflicting_anchors": conflicting_background_complexity_anchors,
                "message": (
                    f"自然语言已明确背景复杂度“{background_summary}”，"
                    "但当前场景、构图、风格、画质或补充标签仍包含相反背景密度。"
                ),
            }
        )
    season_anchors = [
        {"group": group, "value": value}
        for group in ("场景背景", "光影氛围", "画面风格", "服装造型", "技术画质")
        for value in groups.get(group, [])
    ] + [{"group": "自定义补充", "value": value} for value in custom]
    conflicting_season_anchors = _conflicting_exclusive_axis_anchors(
        season_anchors,
        season_constraint,
        detect_season,
        _SEASON_LABELS,
    )
    if conflicting_season_anchors:
        required_label = _clean(season_constraint.get("required_label"))
        negated_labels = list(season_constraint.get("negated_labels", []) or [])
        season_summary = (
            f"固定为{required_label}"
            if required_label
            else "排除" + "/".join(str(item) for item in negated_labels)
        )
        coherence_issues.append(
            {
                "kind": "context_season_conflict",
                "severity": "error",
                "constraint": deepcopy(season_constraint),
                "conflicting_anchors": conflicting_season_anchors,
                "message": (
                    f"自然语言已明确季节连续性“{season_summary}”，"
                    "但当前场景、光影、风格、服装、画质或补充标签仍包含相反季节。"
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
        "scene_attribute_constraints": scene_attribute_constraints,
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
        "natural_context_exposure_key": context_exposure_key,
        "negated_context_exposure_key": negated_context_exposure_key,
        "exposure_key_constraint": exposure_key_constraint,
        "natural_context_contrast_level": context_contrast_level,
        "negated_context_contrast_level": negated_context_contrast_level,
        "contrast_level_constraint": contrast_level_constraint,
        "natural_context_saturation_level": context_saturation_level,
        "negated_context_saturation_level": negated_context_saturation_level,
        "saturation_level_constraint": saturation_level_constraint,
        "natural_context_image_grain": context_image_grain,
        "negated_context_image_grain": negated_context_image_grain,
        "image_grain_constraint": image_grain_constraint,
        "natural_context_image_sharpness": context_image_sharpness,
        "negated_context_image_sharpness": negated_context_image_sharpness,
        "image_sharpness_constraint": image_sharpness_constraint,
        "natural_context_detail_density": context_detail_density,
        "negated_context_detail_density": negated_context_detail_density,
        "detail_density_constraint": detail_density_constraint,
        "natural_context_visual_medium": context_visual_medium,
        "negated_context_visual_medium": negated_context_visual_medium,
        "visual_medium_constraint": visual_medium_constraint,
        "natural_context_projection_geometry": context_projection_geometry,
        "negated_context_projection_geometry": negated_context_projection_geometry,
        "projection_geometry_constraint": projection_geometry_constraint,
        "natural_context_perspective_layout": context_perspective_layout,
        "negated_context_perspective_layout": negated_context_perspective_layout,
        "perspective_layout_constraint": perspective_layout_constraint,
        "natural_context_camera_roll": context_camera_roll,
        "negated_context_camera_roll": negated_context_camera_roll,
        "camera_roll_constraint": camera_roll_constraint,
        "natural_context_composition_placement": context_composition_placement,
        "negated_context_composition_placement": negated_context_composition_placement,
        "composition_placement_constraint": composition_placement_constraint,
        "natural_context_screen_direction": context_screen_direction,
        "negated_context_screen_direction": negated_context_screen_direction,
        "screen_direction_constraint": screen_direction_constraint,
        "natural_context_spatial_axis_continuity": context_spatial_axis_continuity,
        "negated_context_spatial_axis_continuity": negated_context_spatial_axis_continuity,
        "spatial_axis_continuity_constraint": spatial_axis_continuity_constraint,
        "natural_context_foreground_occlusion": context_foreground_occlusion,
        "negated_context_foreground_occlusion": negated_context_foreground_occlusion,
        "foreground_occlusion_constraint": foreground_occlusion_constraint,
        "natural_context_subject_support_state": context_subject_support_state,
        "negated_context_subject_support_state": negated_context_subject_support_state,
        "subject_support_state_constraint": subject_support_state_constraint,
        "natural_context_gaze_target": context_gaze_target,
        "negated_context_gaze_target": negated_context_gaze_target,
        "gaze_target_constraint": gaze_target_constraint,
        "natural_context_atmospheric_medium": context_atmospheric_medium,
        "negated_context_atmospheric_medium": negated_context_atmospheric_medium,
        "atmospheric_medium_constraint": atmospheric_medium_constraint,
        "natural_context_background_complexity": context_background_complexity,
        "negated_context_background_complexity": negated_context_background_complexity,
        "background_complexity_constraint": background_complexity_constraint,
        "natural_context_season": context_season,
        "negated_context_season": negated_context_season,
        "season_constraint": season_constraint,
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
                "context_exposure_key_conflict",
                "context_contrast_level_conflict",
                "context_saturation_level_conflict",
                "context_image_grain_conflict",
                "context_image_sharpness_conflict",
                "context_detail_density_conflict",
                "context_visual_medium_conflict",
                "context_projection_geometry_conflict",
                "context_perspective_layout_conflict",
                "context_camera_roll_conflict",
                "context_composition_placement_conflict",
                "context_screen_direction_conflict",
                "context_spatial_axis_continuity_conflict",
                "context_foreground_occlusion_conflict",
                "context_subject_support_state_conflict",
                "context_gaze_target_conflict",
                "context_atmospheric_medium_conflict",
                "context_background_complexity_conflict",
                "context_season_conflict",
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
                        "context_exposure_key_conflict": "context_exposure_key",
                        "context_contrast_level_conflict": "context_contrast_level",
                        "context_saturation_level_conflict": "context_saturation_level",
                        "context_image_grain_conflict": "context_image_grain",
                        "context_image_sharpness_conflict": "context_image_sharpness",
                        "context_detail_density_conflict": "context_detail_density",
                        "context_visual_medium_conflict": "context_visual_medium",
                        "context_projection_geometry_conflict": "context_projection_geometry",
                        "context_perspective_layout_conflict": "context_perspective_layout",
                        "context_camera_roll_conflict": "context_camera_roll",
                        "context_composition_placement_conflict": "context_composition_placement",
                        "context_screen_direction_conflict": "context_screen_direction",
                        "context_spatial_axis_continuity_conflict": "context_spatial_axis_continuity",
                        "context_foreground_occlusion_conflict": "context_foreground_occlusion",
                        "context_subject_support_state_conflict": "context_subject_support_state",
                        "context_gaze_target_conflict": "context_gaze_target",
                        "context_atmospheric_medium_conflict": "context_atmospheric_medium",
                        "context_background_complexity_conflict": "context_background_complexity",
                        "context_season_conflict": "context_season",
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
    if "场景属性" in text:
        for axis, axis_label, instruction in _SCENE_ATTRIBUTE_REPAIR_RULES:
            if axis_label in text or axis.casefold() in folded:
                return {
                    "kind": f"scene_attribute_{axis}",
                    "instruction": instruction,
                    "reason": text,
                }
    rules = (
        ("missing_anchor", ("缺少", "锚点"), "只补回缺失锚点，并保持其与主体、动作和场景的原有关联。"),
        ("world_conflict", ("世界族",), "只删除越界世界族及其附属物件，再用当前场景已有材质或环境反馈补足语句。"),
        ("scene_conflict", ("冲突场景",), "只移除错误场景，所有动作、道具和光线必须回到当前唯一主场景。"),
        ("scene_attribute", ("场景属性",), "只移除与用户昼夜、降水、风势、环境温度、地表状态、空间围合或主导照明来源要求相反的光影和环境状态，不改变主体、动作与剧情顺序。"),
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
        ("exposure_key", ("曝光调性",), "只修正高调高键与低调低键曝光冲突，不改变光质、色温、主光方向、主体、场景或剧情顺序。"),
        ("contrast_level", ("整体对比度",), "只修正整体高对比与低对比冲突，不改变曝光调性、光质、色温、主光方向、主体或剧情顺序。"),
        ("saturation_level", ("整体饱和度",), "只修正整体高饱和与低饱和或去饱和冲突，不改变颜色模式、色温、对比度、主体、场景或剧情顺序。"),
        ("image_grain", ("成像颗粒质感",), "只修正胶片颗粒、可见噪点与干净无颗粒数字成像的冲突，不改变景深、运动呈现、光质、主体、场景或剧情顺序。"),
        ("image_sharpness", ("整体成像锐度",), "只修正锐利清晰成像与整体柔焦或软焦冲突，不改变景深、运动模糊、雾气、光质、主体、场景或剧情顺序。"),
        ("detail_density", ("整体细节密度",), "只修正高细节、高密度纹理与简化低细节渲染冲突，不改变分辨率、锐度、颗粒、风格、主体、场景或剧情顺序。"),
        ("visual_medium", ("画面媒介",), "只修正二维绘制、三维渲染与摄影实拍之间的成片媒介冲突，不改变画风、材质、锐度、细节、主体、场景或剧情顺序。"),
        ("projection_geometry", ("投影几何",), "只修正正交、线性透视、轴测或鱼眼投影冲突，不改变景别、机位方向、焦段、画面媒介、主体、场景或剧情顺序。"),
        ("perspective_layout", ("透视消失点结构",), "只修正一点、两点或三点透视的消失点数量与竖直线汇聚关系，不改变投影类型、焦段、机位、景别、主体、场景或剧情顺序。"),
        ("camera_roll", ("画幅滚转",), "只修正零度滚转与荷兰角倾斜之间的全局画幅冲突，不改变高低机位、透视消失点、焦段、主体、场景或剧情顺序。"),
        ("composition_placement", ("主体构图落点",), "只修正主体居中/轴对称与三分法/偏心落点之间的全局构图重心冲突，不改变景别、机位、画幅滚转、主体、场景或剧情顺序。"),
        ("screen_direction", ("横向屏幕方向",), "只修正从左向右与从右向左的主体指向、前导空间和运动轨迹关系，不改变主体身份、动作内容、景别、机位、画幅滚转或剧情顺序；明确越轴或转身时才改变方向。"),
        ("spatial_axis_continuity", ("空间轴线连续性",), "只修正180度动作轴线、摄影机半空间和角色左右位置的连续关系，不改变主体身份、视线、横向运动、景别、机位、构图落点或剧情顺序；只有明确的连续越轴路径才允许换边。"),
        ("foreground_occlusion", ("前景遮挡关系",), "只修正主体无遮挡与受控前景框景之间的遮挡层级，不改变服装覆盖、景深、雾气、景别、机位、主体身份、动作或剧情顺序；框景只能使用 Skill 底稿已有前景元素。"),
        ("subject_support_state", ("主体支撑状态",), "只修正主体稳定承重接触与整体离地悬浮之间的支撑关系，不改变站坐跪躺姿态、动作内容、运动模糊、机位、场景或剧情顺序；承托面必须来自 Skill 底稿已有场景或道具。"),
        ("gaze_target", ("视线目标",), "只修正直视镜头与离开镜头、锁定场景目标之间的双眼视线关系，不改变面部朝向、主体姿态、屏幕方向、景别、机位或剧情顺序。"),
        ("atmospheric_medium", ("大气介质", "能见度"), "只修正当前空气介质的能见度、轮廓衰减、散射与颗粒密度，使其回到关系图已固定状态，不改变光质、色温、天气、景深、主体、场景或剧情顺序。"),
        ("background_complexity", ("背景复杂度",), "只修正简洁无杂物背景与丰富繁复环境背景之间的冲突，不改变主体、必要道具、接触阴影、画面媒介、场景世界或剧情顺序。"),
        ("season", ("季节连续性",), "只修正春夏秋冬之间的季节冲突，不改变昼夜、降水、主体、动作、主场景或剧情顺序。"),
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
    constraints = dict(
        scene_graph.get("scene_attribute_constraints", {})
        or scene_graph.get("context_scene_attribute_constraints", {})
        or {}
    )
    if constraints:
        original_attributes = detect_scene_attributes(original)
        candidate_attributes = detect_scene_attributes(candidate)
        original_feedback = detect_scene_attribute_feedback(original)
        candidate_feedback = detect_scene_attribute_feedback(candidate)
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
            original_feedback_values = set(original_feedback.get(axis, {}))
            for value, evidence in candidate_feedback.get(axis, {}).items():
                if value in original_feedback_values:
                    continue
                if value in negated_values or (required and value != required):
                    axis_label = _clean(constraint.get("axis_label")) or axis
                    expected = _clean(constraint.get("required_label")) or "排除状态"
                    return (
                        f"模型响应越过场景属性约束：{axis_label}要求“{expected}”，"
                        f"却新增了相反的直接视觉反馈“{evidence[0]}”。"
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
        original_orientation_feedback = set(detect_subject_orientation_feedback(original))
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
        candidate_orientation_feedback = detect_subject_orientation_feedback(candidate)
        for value, evidence in candidate_orientation_feedback.items():
            if value in original_orientation_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(orientation_constraint.get("required_label")) or "排除朝向"
                return (
                    f"模型响应越过主体朝向约束：要求“{expected}”，"
                    f"却新增了相反的五官可见性、侧面轮廓或头肩反馈“{evidence[0]}”。"
                )
    pose_constraint = dict(scene_graph.get("context_subject_pose_constraint", {}) or {})
    if pose_constraint:
        required = _clean(pose_constraint.get("required_value"))
        negated_values = set(pose_constraint.get("negated_values", []) or [])
        original_pose = set(detect_subject_pose(original))
        original_pose_feedback = set(detect_subject_pose_feedback(original))
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
        candidate_pose_feedback = detect_subject_pose_feedback(candidate)
        for value, evidence in candidate_pose_feedback.items():
            if value in original_pose_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(pose_constraint.get("required_label")) or "排除姿态"
                return (
                    f"模型响应越过主体姿态约束：要求“{expected}”，"
                    f"却新增了相反的身体承重、支撑面或关节反馈“{evidence[0]}”。"
                )
    shot_scale_constraint = dict(scene_graph.get("context_shot_scale_constraint", {}) or {})
    if shot_scale_constraint:
        required = _clean(shot_scale_constraint.get("required_value"))
        negated_values = set(shot_scale_constraint.get("negated_values", []) or [])
        original_shot_scale = set(detect_shot_scale(original, require_context_scope=True))
        original_shot_scale_feedback = set(detect_shot_scale_feedback(original))
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
        candidate_shot_scale_feedback = detect_shot_scale_feedback(candidate)
        for value, evidence in candidate_shot_scale_feedback.items():
            if value in original_shot_scale_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(shot_scale_constraint.get("required_label")) or "排除景别"
                return (
                    f"模型响应越过景别约束：要求“{expected}”，"
                    f"却新增了相反的画幅边界、身体覆盖范围或主体占比反馈“{evidence[0]}”。"
                )
    camera_angle_constraint = dict(scene_graph.get("context_camera_angle_constraint", {}) or {})
    if camera_angle_constraint:
        required = _clean(camera_angle_constraint.get("required_value"))
        negated_values = set(camera_angle_constraint.get("negated_values", []) or [])
        original_camera_angle = set(detect_camera_angle(original, require_context_scope=True))
        original_camera_angle_feedback = set(detect_camera_angle_feedback(original))
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
        candidate_camera_angle_feedback = detect_camera_angle_feedback(candidate)
        for value, evidence in candidate_camera_angle_feedback.items():
            if value in original_camera_angle_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(camera_angle_constraint.get("required_label")) or "排除机位"
                return (
                    f"模型响应越过机位约束：要求“{expected}”，"
                    f"却新增了相反的镜头高度、主体可见表面或地面透视反馈“{evidence[0]}”。"
                )
    light_temperature_constraint = dict(
        scene_graph.get("context_light_temperature_constraint", {}) or {}
    )
    if light_temperature_constraint:
        required = _clean(light_temperature_constraint.get("required_value"))
        negated_values = set(light_temperature_constraint.get("negated_values", []) or [])
        original_temperature = set(detect_light_temperature(original, require_context_scope=True))
        original_temperature_feedback = set(detect_light_temperature_feedback(original))
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
        candidate_temperature_feedback = detect_light_temperature_feedback(candidate)
        for value, evidence in candidate_temperature_feedback.items():
            if value in original_temperature_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(light_temperature_constraint.get("required_label")) or "排除色温"
                return (
                    f"模型响应越过整体色温约束：要求“{expected}”，"
                    f"却新增了相反的全局白点、中性表面或综合色偏反馈“{evidence[0]}”。"
                )
    color_rendering_constraint = dict(scene_graph.get("color_rendering_constraint", {}) or {})
    if color_rendering_constraint:
        required = _clean(color_rendering_constraint.get("required_value"))
        negated_values = set(color_rendering_constraint.get("negated_values", []) or [])
        original_rendering = set(detect_color_rendering(original))
        original_rendering_feedback = set(detect_color_rendering_feedback(original))
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
        candidate_rendering_feedback = detect_color_rendering_feedback(candidate)
        for value, evidence in candidate_rendering_feedback.items():
            if value in original_rendering_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(color_rendering_constraint.get("required_label")) or "排除颜色模式"
                return (
                    f"模型响应越过颜色呈现约束：要求“{expected}”，"
                    f"却新增了相反的色度、独立色相或明度反馈“{evidence[0]}”。"
                )
    depth_of_field_constraint = dict(scene_graph.get("depth_of_field_constraint", {}) or {})
    if depth_of_field_constraint:
        required = _clean(depth_of_field_constraint.get("required_value"))
        negated_values = set(depth_of_field_constraint.get("negated_values", []) or [])
        original_depth = set(detect_depth_of_field(original))
        original_depth_feedback = set(detect_depth_of_field_feedback(original))
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
        candidate_depth_feedback = detect_depth_of_field_feedback(candidate)
        for value, evidence in candidate_depth_feedback.items():
            if value in original_depth_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(depth_of_field_constraint.get("required_label")) or "排除景深"
                return (
                    f"模型响应越过景深约束：要求“{expected}”，"
                    f"却新增了相反的焦平面、距离层级或细节衰减反馈“{evidence[0]}”。"
                )
    lighting_quality_constraint = dict(scene_graph.get("lighting_quality_constraint", {}) or {})
    if lighting_quality_constraint:
        required = _clean(lighting_quality_constraint.get("required_value"))
        negated_values = set(lighting_quality_constraint.get("negated_values", []) or [])
        original_quality = set(detect_lighting_quality(original))
        original_quality_feedback = set(detect_lighting_quality_feedback(original))
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
        candidate_quality_feedback = detect_lighting_quality_feedback(candidate)
        for value, evidence in candidate_quality_feedback.items():
            if value in original_quality_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(lighting_quality_constraint.get("required_label")) or "排除光质"
                return (
                    f"模型响应越过光质约束：要求“{expected}”，"
                    f"却新增了相反的投影边缘、明暗过渡或高光范围反馈“{evidence[0]}”。"
                )
    motion_rendering_constraint = dict(scene_graph.get("motion_rendering_constraint", {}) or {})
    if motion_rendering_constraint:
        required = _clean(motion_rendering_constraint.get("required_value"))
        negated_values = set(motion_rendering_constraint.get("negated_values", []) or [])
        original_motion = set(detect_motion_rendering(original))
        original_motion_feedback = set(detect_motion_rendering_feedback(original))
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
        candidate_motion_feedback = detect_motion_rendering_feedback(candidate)
        for value, evidence in candidate_motion_feedback.items():
            if value in original_motion_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(motion_rendering_constraint.get("required_label")) or "排除运动呈现"
                return (
                    f"模型响应越过运动呈现约束：要求“{expected}”，"
                    f"却新增了相反的主体轮廓、位移连续性或动作相位反馈“{evidence[0]}”。"
                )
    camera_stability_constraint = dict(scene_graph.get("camera_stability_constraint", {}) or {})
    if camera_stability_constraint:
        required = _clean(camera_stability_constraint.get("required_value"))
        negated_values = set(camera_stability_constraint.get("negated_values", []) or [])
        original_stability = set(detect_camera_stability(original))
        original_stability_feedback = set(detect_camera_stability_feedback(original))
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
        candidate_stability_feedback = detect_camera_stability_feedback(candidate)
        for value, evidence in candidate_stability_feedback.items():
            if value in original_stability_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(camera_stability_constraint.get("required_label")) or "排除镜头状态"
                return (
                    f"模型响应越过镜头稳定性约束：要求“{expected}”，"
                    f"却新增了相反的帧间背景锚点、地平线或取景中心反馈“{evidence[0]}”。"
                )
    focal_perspective_constraint = dict(scene_graph.get("focal_perspective_constraint", {}) or {})
    if focal_perspective_constraint:
        required = _clean(focal_perspective_constraint.get("required_value"))
        negated_values = set(focal_perspective_constraint.get("negated_values", []) or [])
        original_focal = set(detect_focal_perspective(original))
        original_focal_feedback = set(detect_focal_perspective_feedback(original))
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
        candidate_focal_feedback = detect_focal_perspective_feedback(candidate)
        for value, evidence in candidate_focal_feedback.items():
            if value in original_focal_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(focal_perspective_constraint.get("required_label")) or "排除焦段透视"
                return (
                    f"模型响应越过焦段透视约束：要求“{expected}”，"
                    f"却新增了相反的近远尺度、空间层叠或视轴距离反馈“{evidence[0]}”。"
                )
    key_light_direction_constraint = dict(scene_graph.get("key_light_direction_constraint", {}) or {})
    if key_light_direction_constraint:
        required = _clean(key_light_direction_constraint.get("required_value"))
        negated_values = set(key_light_direction_constraint.get("negated_values", []) or [])
        original_direction = set(detect_key_light_direction(original))
        original_direction_feedback = set(detect_key_light_direction_feedback(original))
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
        candidate_direction_feedback = detect_key_light_direction_feedback(candidate)
        for value, evidence in candidate_direction_feedback.items():
            if value in original_direction_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(key_light_direction_constraint.get("required_label")) or "排除主光方向"
                return (
                    f"模型响应越过主光方向约束：要求“{expected}”，"
                    f"却新增了相反的投影、受光面或轮廓反馈“{evidence[0]}”。"
                )
    exposure_key_constraint = dict(scene_graph.get("exposure_key_constraint", {}) or {})
    if exposure_key_constraint:
        required = _clean(exposure_key_constraint.get("required_value"))
        negated_values = set(exposure_key_constraint.get("negated_values", []) or [])
        original_exposure = set(detect_exposure_key(original))
        original_exposure_feedback = set(detect_exposure_key_feedback(original))
        candidate_exposure = detect_exposure_key(candidate)
        for value, markers in candidate_exposure.items():
            if value in original_exposure:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(exposure_key_constraint.get("required_label")) or "排除曝光调性"
                return (
                    f"模型响应越过曝光调性约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_exposure_feedback = detect_exposure_key_feedback(candidate)
        for value, evidence in candidate_exposure_feedback.items():
            if value in original_exposure_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(exposure_key_constraint.get("required_label")) or "排除曝光调性"
                return (
                    f"模型响应越过曝光调性约束：要求“{expected}”，"
                    f"却新增了相反的全局亮度分布、暗部占比或黑位反馈“{evidence[0]}”。"
                )
    contrast_level_constraint = dict(scene_graph.get("contrast_level_constraint", {}) or {})
    if contrast_level_constraint:
        required = _clean(contrast_level_constraint.get("required_value"))
        negated_values = set(contrast_level_constraint.get("negated_values", []) or [])
        original_contrast = set(detect_contrast_level(original))
        original_contrast_feedback = set(detect_contrast_level_feedback(original))
        candidate_contrast = detect_contrast_level(candidate)
        for value, markers in candidate_contrast.items():
            if value in original_contrast:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(contrast_level_constraint.get("required_label")) or "排除整体对比度"
                return (
                    f"模型响应越过整体对比度约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_contrast_feedback = detect_contrast_level_feedback(candidate)
        for value, evidence in candidate_contrast_feedback.items():
            if value in original_contrast_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(contrast_level_constraint.get("required_label")) or "排除整体对比度"
                return (
                    f"模型响应越过整体对比度约束：要求“{expected}”，"
                    f"却新增了相反的全局明度跨度、中间调范围或直方图反馈“{evidence[0]}”。"
                )
    saturation_level_constraint = dict(scene_graph.get("saturation_level_constraint", {}) or {})
    if saturation_level_constraint:
        required = _clean(saturation_level_constraint.get("required_value"))
        negated_values = set(saturation_level_constraint.get("negated_values", []) or [])
        original_saturation = set(detect_saturation_level(original))
        original_saturation_feedback = set(detect_saturation_level_feedback(original))
        candidate_saturation = detect_saturation_level(candidate)
        for value, markers in candidate_saturation.items():
            if value in original_saturation:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(saturation_level_constraint.get("required_label")) or "排除整体饱和度"
                return (
                    f"模型响应越过整体饱和度约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_saturation_feedback = detect_saturation_level_feedback(candidate)
        for value, evidence in candidate_saturation_feedback.items():
            if value in original_saturation_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(saturation_level_constraint.get("required_label")) or "排除整体饱和度"
                return (
                    f"模型响应越过整体饱和度约束：要求“{expected}”，"
                    f"却新增了相反的全局综合色度分布、中性灰占比或鲜艳色覆盖反馈“{evidence[0]}”。"
                )
    image_grain_constraint = dict(scene_graph.get("image_grain_constraint", {}) or {})
    if image_grain_constraint:
        required = _clean(image_grain_constraint.get("required_value"))
        negated_values = set(image_grain_constraint.get("negated_values", []) or [])
        original_grain = set(detect_image_grain(original))
        original_grain_feedback = set(detect_image_grain_feedback(original))
        candidate_grain = detect_image_grain(candidate)
        for value, markers in candidate_grain.items():
            if value in original_grain:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(image_grain_constraint.get("required_label")) or "排除成像颗粒质感"
                return (
                    f"模型响应越过成像颗粒质感约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_grain_feedback = detect_image_grain_feedback(candidate)
        for value, evidence in candidate_grain_feedback.items():
            if value in original_grain_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(image_grain_constraint.get("required_label")) or "排除成像颗粒质感"
                return (
                    f"模型响应越过成像颗粒质感约束：要求“{expected}”，"
                    f"却新增了相反的平坦区域噪点分布、颗粒尺度或轮廓连续性反馈“{evidence[0]}”。"
                )
    image_sharpness_constraint = dict(scene_graph.get("image_sharpness_constraint", {}) or {})
    if image_sharpness_constraint:
        required = _clean(image_sharpness_constraint.get("required_value"))
        negated_values = set(image_sharpness_constraint.get("negated_values", []) or [])
        original_sharpness = set(
            detect_image_sharpness(original, require_context_scope=True)
        )
        original_sharpness_feedback = set(detect_image_sharpness_feedback(original))
        selective_sharpness = bool(_SELECTIVE_IMAGE_SHARPNESS_RE.search(_clean(candidate)))
        candidate_sharpness = (
            {}
            if selective_sharpness
            else detect_image_sharpness(candidate, require_context_scope=True)
        )
        for value, markers in candidate_sharpness.items():
            if value in original_sharpness:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(image_sharpness_constraint.get("required_label")) or "排除整体成像锐度"
                return (
                    f"模型响应越过整体成像锐度约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_sharpness_feedback = (
            {} if selective_sharpness else detect_image_sharpness_feedback(candidate)
        )
        for value, evidence in candidate_sharpness_feedback.items():
            if value in original_sharpness_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(image_sharpness_constraint.get("required_label")) or "排除整体成像锐度"
                return (
                    f"模型响应越过整体成像锐度约束：要求“{expected}”，"
                    f"却新增了相反的轮廓过渡宽度、细线分离度或微纹理边缘反馈“{evidence[0]}”。"
                )
    detail_density_constraint = dict(scene_graph.get("detail_density_constraint", {}) or {})
    if detail_density_constraint:
        required = _clean(detail_density_constraint.get("required_value"))
        negated_values = set(detail_density_constraint.get("negated_values", []) or [])
        original_detail = set(detect_detail_density(original))
        original_detail_feedback = set(detect_detail_density_feedback(original))
        selective_detail = bool(_SELECTIVE_DETAIL_DENSITY_RE.search(_clean(candidate)))
        candidate_detail = (
            {}
            if selective_detail
            else detect_detail_density(candidate)
        )
        for value, markers in candidate_detail.items():
            if value in original_detail:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(detail_density_constraint.get("required_label")) or "排除整体细节密度"
                return (
                    f"模型响应越过整体细节密度约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_detail_feedback = (
            {} if selective_detail else detect_detail_density_feedback(candidate)
        )
        for value, evidence in candidate_detail_feedback.items():
            if value in original_detail_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(detail_density_constraint.get("required_label")) or "排除整体细节密度"
                return (
                    f"模型响应越过整体细节密度约束：要求“{expected}”，"
                    f"却新增了相反的单位区域结构数量、纹理层级或简化区域占比反馈“{evidence[0]}”。"
                )
    visual_medium_constraint = dict(scene_graph.get("visual_medium_constraint", {}) or {})
    if visual_medium_constraint:
        required = _clean(visual_medium_constraint.get("required_value"))
        negated_values = set(visual_medium_constraint.get("negated_values", []) or [])
        original_medium = set(detect_visual_medium(original))
        original_medium_feedback = set(detect_visual_medium_feedback(original))
        mixed_medium = bool(_MIXED_VISUAL_MEDIUM_RE.search(_clean(candidate)))
        candidate_medium = (
            {}
            if mixed_medium
            else detect_visual_medium(candidate)
        )
        for value, markers in candidate_medium.items():
            if value in original_medium:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(visual_medium_constraint.get("required_label")) or "排除画面媒介"
                return (
                    f"模型响应越过画面媒介约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_medium_feedback = (
            {} if mixed_medium else detect_visual_medium_feedback(candidate)
        )
        for value, evidence in candidate_medium_feedback.items():
            if value in original_medium_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(visual_medium_constraint.get("required_label")) or "排除画面媒介"
                return (
                    f"模型响应越过画面媒介约束：要求“{expected}”，"
                    f"却新增了相反的线条色块组织、曲面材质响应或光学采样反馈“{evidence[0]}”。"
                )
    projection_geometry_constraint = dict(
        scene_graph.get("projection_geometry_constraint", {}) or {}
    )
    if projection_geometry_constraint:
        required = _clean(projection_geometry_constraint.get("required_value"))
        negated_values = set(projection_geometry_constraint.get("negated_values", []) or [])
        original_projection = set(detect_projection_geometry(original))
        original_projection_feedback = set(detect_projection_geometry_feedback(original))
        mixed_projection = bool(_MIXED_PROJECTION_GEOMETRY_RE.search(_clean(candidate)))
        candidate_projection = (
            {}
            if mixed_projection
            else detect_projection_geometry(candidate)
        )
        for value, markers in candidate_projection.items():
            if value in original_projection:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(projection_geometry_constraint.get("required_label"))
                    or "排除投影几何"
                )
                return (
                    f"模型响应越过投影几何约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_projection_feedback = (
            {} if mixed_projection else detect_projection_geometry_feedback(candidate)
        )
        for value, evidence in candidate_projection_feedback.items():
            if value in original_projection_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(projection_geometry_constraint.get("required_label"))
                    or "排除投影几何"
                )
                return (
                    f"模型响应越过投影几何约束：要求“{expected}”，"
                    f"却新增了相反的平行线汇聚、深度尺度变化或视轴缩短反馈“{evidence[0]}”。"
                )
    perspective_layout_constraint = dict(
        scene_graph.get("perspective_layout_constraint", {}) or {}
    )
    if perspective_layout_constraint:
        required = _clean(perspective_layout_constraint.get("required_value"))
        negated_values = set(perspective_layout_constraint.get("negated_values", []) or [])
        original_layout = set(detect_perspective_layout(original))
        original_layout_feedback = set(detect_perspective_layout_feedback(original))
        mixed_layout = bool(_MIXED_PERSPECTIVE_LAYOUT_RE.search(_clean(candidate)))
        candidate_layout = (
            {} if mixed_layout else detect_perspective_layout(candidate)
        )
        for value, markers in candidate_layout.items():
            if value in original_layout:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(perspective_layout_constraint.get("required_label"))
                    or "排除透视消失点结构"
                )
                return (
                    f"模型响应越过透视消失点结构约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_layout_feedback = (
            {} if mixed_layout else detect_perspective_layout_feedback(candidate)
        )
        for value, evidence in candidate_layout_feedback.items():
            if value in original_layout_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(perspective_layout_constraint.get("required_label"))
                    or "排除透视消失点结构"
                )
                return (
                    f"模型响应越过透视消失点结构约束：要求“{expected}”，"
                    f"却新增了相反的水平边消失点数量或竖直线汇聚反馈“{evidence[0]}”。"
                )
    camera_roll_constraint = dict(scene_graph.get("camera_roll_constraint", {}) or {})
    if camera_roll_constraint:
        required = _clean(camera_roll_constraint.get("required_value"))
        negated_values = set(camera_roll_constraint.get("negated_values", []) or [])
        original_roll = set(detect_camera_roll(original))
        original_roll_feedback = set(detect_camera_roll_feedback(original))
        mixed_roll = bool(_MIXED_CAMERA_ROLL_RE.search(_clean(candidate)))
        candidate_roll = {} if mixed_roll else detect_camera_roll(candidate)
        for value, markers in candidate_roll.items():
            if value in original_roll:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(camera_roll_constraint.get("required_label"))
                    or "排除画幅滚转"
                )
                return (
                    f"模型响应越过画幅滚转约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_roll_feedback = (
            {} if mixed_roll else detect_camera_roll_feedback(candidate)
        )
        for value, evidence in candidate_roll_feedback.items():
            if value in original_roll_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(camera_roll_constraint.get("required_label"))
                    or "排除画幅滚转"
                )
                return (
                    f"模型响应越过画幅滚转约束：要求“{expected}”，"
                    f"却新增了相反的重力竖直方向、地平基准或全局滚转反馈“{evidence[0]}”。"
                )
    composition_placement_constraint = dict(
        scene_graph.get("composition_placement_constraint", {}) or {}
    )
    if composition_placement_constraint:
        required = _clean(composition_placement_constraint.get("required_value"))
        negated_values = set(composition_placement_constraint.get("negated_values", []) or [])
        original_placement = set(detect_composition_placement(original))
        original_placement_feedback = set(detect_composition_placement_feedback(original))
        mixed_placement = bool(_MIXED_COMPOSITION_PLACEMENT_RE.search(_clean(candidate)))
        candidate_placement = {} if mixed_placement else detect_composition_placement(candidate)
        for value, markers in candidate_placement.items():
            if value in original_placement:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(composition_placement_constraint.get("required_label"))
                    or "排除主体构图落点"
                )
                return (
                    f"模型响应越过主体构图落点约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_placement_feedback = (
            {} if mixed_placement else detect_composition_placement_feedback(candidate)
        )
        for value, evidence in candidate_placement_feedback.items():
            if value in original_placement_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(composition_placement_constraint.get("required_label"))
                    or "排除主体构图落点"
                )
                return (
                    f"模型响应越过主体构图落点约束：要求“{expected}”，"
                    f"却新增了相反的视觉重心、三分线落点或中央平衡反馈“{evidence[0]}”。"
                )
    screen_direction_constraint = dict(
        scene_graph.get("screen_direction_constraint", {}) or {}
    )
    if screen_direction_constraint:
        required = _clean(screen_direction_constraint.get("required_value"))
        negated_values = set(screen_direction_constraint.get("negated_values", []) or [])
        original_direction = set(detect_screen_direction(original))
        original_direction_feedback = set(detect_screen_direction_feedback(original))
        mixed_direction = bool(_MIXED_SCREEN_DIRECTION_RE.search(_clean(candidate)))
        candidate_direction = {} if mixed_direction else detect_screen_direction(candidate)
        for value, markers in candidate_direction.items():
            if value in original_direction:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(screen_direction_constraint.get("required_label"))
                    or "排除横向屏幕方向"
                )
                return (
                    f"模型响应越过横向屏幕方向约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_direction_feedback = (
            {} if mixed_direction else detect_screen_direction_feedback(candidate)
        )
        for value, evidence in candidate_direction_feedback.items():
            if value in original_direction_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(screen_direction_constraint.get("required_label"))
                    or "排除横向屏幕方向"
                )
                return (
                    f"模型响应越过横向屏幕方向约束：要求“{expected}”，"
                    f"却新增了相反的主体指向、前导空间或运动轨迹反馈“{evidence[0]}”。"
                )
    spatial_axis_continuity_constraint = dict(
        scene_graph.get("spatial_axis_continuity_constraint", {}) or {}
    )
    if spatial_axis_continuity_constraint:
        required = _clean(spatial_axis_continuity_constraint.get("required_value"))
        negated_values = set(
            spatial_axis_continuity_constraint.get("negated_values", []) or []
        )
        original_axis = set(detect_spatial_axis_continuity(original))
        original_axis_feedback = set(detect_spatial_axis_continuity_feedback(original))
        mixed_axis = bool(_MIXED_SPATIAL_AXIS_CONTINUITY_RE.search(_clean(candidate)))
        candidate_axis = {} if mixed_axis else detect_spatial_axis_continuity(candidate)
        for value, markers in candidate_axis.items():
            if value in original_axis:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(spatial_axis_continuity_constraint.get("required_label"))
                    or "排除空间轴线连续性"
                )
                return (
                    f"模型响应越过空间轴线连续性约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_axis_feedback = (
            {} if mixed_axis else detect_spatial_axis_continuity_feedback(candidate)
        )
        for value, evidence in candidate_axis_feedback.items():
            if value in original_axis_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(spatial_axis_continuity_constraint.get("required_label"))
                    or "排除空间轴线连续性"
                )
                return (
                    f"模型响应越过空间轴线连续性约束：要求“{expected}”，"
                    f"却新增了相反的摄影机半空间、角色左右位置或越轴路径反馈“{evidence[0]}”。"
                )
    foreground_occlusion_constraint = dict(
        scene_graph.get("foreground_occlusion_constraint", {}) or {}
    )
    if foreground_occlusion_constraint:
        required = _clean(foreground_occlusion_constraint.get("required_value"))
        negated_values = set(
            foreground_occlusion_constraint.get("negated_values", []) or []
        )
        original_occlusion = set(detect_foreground_occlusion(original))
        original_occlusion_feedback = set(detect_foreground_occlusion_feedback(original))
        mixed_occlusion = bool(_MIXED_FOREGROUND_OCCLUSION_RE.search(_clean(candidate)))
        candidate_occlusion = (
            {} if mixed_occlusion else detect_foreground_occlusion(candidate)
        )
        for value, markers in candidate_occlusion.items():
            if value in original_occlusion:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(foreground_occlusion_constraint.get("required_label"))
                    or "排除前景遮挡关系"
                )
                return (
                    f"模型响应越过前景遮挡关系约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_occlusion_feedback = (
            {} if mixed_occlusion else detect_foreground_occlusion_feedback(candidate)
        )
        for value, evidence in candidate_occlusion_feedback.items():
            if value in original_occlusion_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(foreground_occlusion_constraint.get("required_label"))
                    or "排除前景遮挡关系"
                )
                return (
                    f"模型响应越过前景遮挡关系约束：要求“{expected}”，"
                    f"却新增了相反的主体轮廓、关键部位可见性或遮挡层级反馈“{evidence[0]}”。"
                )
    subject_support_state_constraint = dict(
        scene_graph.get("subject_support_state_constraint", {}) or {}
    )
    if subject_support_state_constraint:
        required = _clean(subject_support_state_constraint.get("required_value"))
        negated_values = set(
            subject_support_state_constraint.get("negated_values", []) or []
        )
        original_support = set(detect_subject_support_state(original))
        original_support_feedback = set(detect_subject_support_state_feedback(original))
        mixed_support = bool(_MIXED_SUBJECT_SUPPORT_STATE_RE.search(_clean(candidate)))
        candidate_support = {} if mixed_support else detect_subject_support_state(candidate)
        for value, markers in candidate_support.items():
            if value in original_support:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(subject_support_state_constraint.get("required_label"))
                    or "排除主体支撑状态"
                )
                return (
                    f"模型响应越过主体支撑状态约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_support_feedback = (
            {} if mixed_support else detect_subject_support_state_feedback(candidate)
        )
        for value, evidence in candidate_support_feedback.items():
            if value in original_support_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(subject_support_state_constraint.get("required_label"))
                    or "排除主体支撑状态"
                )
                return (
                    f"模型响应越过主体支撑状态约束：要求“{expected}”，"
                    f"却新增了相反的承重点、离地间隙、重心或接触阴影反馈“{evidence[0]}”。"
                )
    gaze_target_constraint = dict(scene_graph.get("gaze_target_constraint", {}) or {})
    if gaze_target_constraint:
        required = _clean(gaze_target_constraint.get("required_value"))
        negated_values = set(gaze_target_constraint.get("negated_values", []) or [])
        original_gaze = set(detect_gaze_target(original))
        original_gaze_feedback = set(detect_gaze_target_feedback(original))
        mixed_gaze = bool(_MIXED_GAZE_TARGET_RE.search(_clean(candidate)))
        candidate_gaze = {} if mixed_gaze else detect_gaze_target(candidate)
        for value, markers in candidate_gaze.items():
            if value in original_gaze:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(gaze_target_constraint.get("required_label"))
                    or "排除视线目标"
                )
                return (
                    f"模型响应越过视线目标约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_gaze_feedback = {} if mixed_gaze else detect_gaze_target_feedback(candidate)
        for value, evidence in candidate_gaze_feedback.items():
            if value in original_gaze_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(gaze_target_constraint.get("required_label"))
                    or "排除视线目标"
                )
                return (
                    f"模型响应越过视线目标约束：要求“{expected}”，"
                    f"却新增了相反的镜头光轴、瞳孔方向或场景目标反馈“{evidence[0]}”。"
                )
    atmospheric_medium_constraint = dict(
        scene_graph.get("atmospheric_medium_constraint", {}) or {}
    )
    if atmospheric_medium_constraint:
        required = _clean(atmospheric_medium_constraint.get("required_value"))
        negated_values = set(atmospheric_medium_constraint.get("negated_values", []) or [])
        original_atmosphere = set(detect_atmospheric_medium(original))
        original_atmosphere_feedback = set(detect_atmospheric_medium_feedback(original))
        mixed_atmosphere = bool(_MIXED_ATMOSPHERIC_MEDIUM_RE.search(_clean(candidate)))
        candidate_atmosphere = (
            {}
            if mixed_atmosphere
            else detect_atmospheric_medium(candidate)
        )
        for value, markers in candidate_atmosphere.items():
            if value in original_atmosphere:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(atmospheric_medium_constraint.get("required_label"))
                    or "排除大气介质与能见度"
                )
                return (
                    f"模型响应越过大气介质与能见度约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
        candidate_atmosphere_feedback = (
            {} if mixed_atmosphere else detect_atmospheric_medium_feedback(candidate)
        )
        for value, evidence in candidate_atmosphere_feedback.items():
            if value in original_atmosphere_feedback:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(atmospheric_medium_constraint.get("required_label"))
                    or "排除大气介质与能见度"
                )
                return (
                    f"模型响应越过大气介质与能见度约束：要求“{expected}”，"
                    f"却新增了相反的直接视觉反馈“{evidence[0]}”。"
                )
    background_complexity_constraint = dict(
        scene_graph.get("background_complexity_constraint", {}) or {}
    )
    if background_complexity_constraint:
        required = _clean(background_complexity_constraint.get("required_value"))
        negated_values = set(background_complexity_constraint.get("negated_values", []) or [])
        original_background = set(detect_background_complexity(original))
        candidate_background = (
            {}
            if _MIXED_BACKGROUND_COMPLEXITY_RE.search(_clean(candidate))
            else detect_background_complexity(candidate)
        )
        for value, markers in candidate_background.items():
            if value in original_background:
                continue
            if value in negated_values or (required and value != required):
                expected = (
                    _clean(background_complexity_constraint.get("required_label"))
                    or "排除背景复杂度"
                )
                return (
                    f"模型响应越过背景复杂度约束：要求“{expected}”，"
                    f"却新增了“{markers[0]}”。"
                )
    season_constraint = dict(scene_graph.get("season_constraint", {}) or {})
    if season_constraint:
        required = _clean(season_constraint.get("required_value"))
        negated_values = set(season_constraint.get("negated_values", []) or [])
        original_seasons = set(detect_season(original))
        candidate_seasons = (
            {}
            if _MIXED_SEASON_RE.search(_clean(candidate))
            else detect_season(candidate)
        )
        for value, markers in candidate_seasons.items():
            if value in original_seasons:
                continue
            if value in negated_values or (required and value != required):
                expected = _clean(season_constraint.get("required_label")) or "排除季节"
                return (
                    f"模型响应越过季节连续性约束：要求“{expected}”，"
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
    "SUBJECT_ORIENTATION_FEEDBACK_PATTERNS",
    "SUBJECT_POSE_FEEDBACK_PATTERNS",
    "SHOT_SCALE_FEEDBACK_PATTERNS",
    "CAMERA_ANGLE_FEEDBACK_PATTERNS",
    "LIGHT_TEMPERATURE_FEEDBACK_PATTERNS",
    "COLOR_RENDERING_FEEDBACK_PATTERNS",
    "DEPTH_OF_FIELD_FEEDBACK_PATTERNS",
    "LIGHTING_QUALITY_FEEDBACK_PATTERNS",
    "MOTION_RENDERING_FEEDBACK_PATTERNS",
    "HUMAN_SUBJECT_INTRUSION_MARKERS",
    "LIGHT_TEMPERATURE_MARKERS",
    "COLOR_RENDERING_MARKERS",
    "DEPTH_OF_FIELD_MARKERS",
    "LIGHTING_QUALITY_MARKERS",
    "MOTION_RENDERING_MARKERS",
    "CAMERA_STABILITY_MARKERS",
    "FOCAL_PERSPECTIVE_MARKERS",
    "KEY_LIGHT_DIRECTION_MARKERS",
    "KEY_LIGHT_DIRECTION_FEEDBACK_PATTERNS",
    "EXPOSURE_KEY_MARKERS",
    "CONTRAST_LEVEL_FEEDBACK_PATTERNS",
    "CONTRAST_LEVEL_MARKERS",
    "SATURATION_LEVEL_FEEDBACK_PATTERNS",
    "SATURATION_LEVEL_MARKERS",
    "IMAGE_GRAIN_FEEDBACK_PATTERNS",
    "IMAGE_GRAIN_MARKERS",
    "IMAGE_SHARPNESS_FEEDBACK_PATTERNS",
    "IMAGE_SHARPNESS_MARKERS",
    "DETAIL_DENSITY_FEEDBACK_PATTERNS",
    "DETAIL_DENSITY_MARKERS",
    "VISUAL_MEDIUM_FEEDBACK_PATTERNS",
    "VISUAL_MEDIUM_MARKERS",
    "PROJECTION_GEOMETRY_FEEDBACK_PATTERNS",
    "PROJECTION_GEOMETRY_MARKERS",
    "PERSPECTIVE_LAYOUT_FEEDBACK_PATTERNS",
    "PERSPECTIVE_LAYOUT_MARKERS",
    "CAMERA_ROLL_FEEDBACK_PATTERNS",
    "CAMERA_ROLL_MARKERS",
    "COMPOSITION_PLACEMENT_FEEDBACK_PATTERNS",
    "COMPOSITION_PLACEMENT_MARKERS",
    "SCREEN_DIRECTION_FEEDBACK_PATTERNS",
    "SCREEN_DIRECTION_MARKERS",
    "SPATIAL_AXIS_CONTINUITY_FEEDBACK_PATTERNS",
    "SPATIAL_AXIS_CONTINUITY_MARKERS",
    "FOREGROUND_OCCLUSION_FEEDBACK_PATTERNS",
    "FOREGROUND_OCCLUSION_MARKERS",
    "SUBJECT_SUPPORT_STATE_FEEDBACK_PATTERNS",
    "SUBJECT_SUPPORT_STATE_MARKERS",
    "GAZE_TARGET_FEEDBACK_PATTERNS",
    "GAZE_TARGET_MARKERS",
    "ATMOSPHERIC_MEDIUM_MARKERS",
    "ATMOSPHERIC_MEDIUM_FEEDBACK_PATTERNS",
    "BACKGROUND_COMPLEXITY_MARKERS",
    "INTELLIGENCE_V42_RULE_EXPANSIONS",
    "SEASON_MARKERS",
    "apply_relation_hint_resolution",
    "build_intelligence_profile",
    "build_scene_relationship_graph",
    "candidate_world_violation",
    "classify_repair_reason",
    "detect_camera_angle",
    "detect_camera_angle_feedback",
    "detect_camera_roll",
    "detect_camera_roll_feedback",
    "detect_composition_placement",
    "detect_composition_placement_feedback",
    "detect_screen_direction",
    "detect_screen_direction_feedback",
    "detect_spatial_axis_continuity",
    "detect_spatial_axis_continuity_feedback",
    "detect_foreground_occlusion",
    "detect_foreground_occlusion_feedback",
    "detect_subject_support_state",
    "detect_subject_support_state_feedback",
    "detect_gaze_target",
    "detect_gaze_target_feedback",
    "detect_camera_stability",
    "detect_color_rendering",
    "detect_color_rendering_feedback",
    "detect_contrast_level",
    "detect_contrast_level_feedback",
    "detect_detail_density",
    "detect_detail_density_feedback",
    "detect_visual_medium",
    "detect_visual_medium_feedback",
    "detect_projection_geometry",
    "detect_projection_geometry_feedback",
    "detect_perspective_layout",
    "detect_perspective_layout_feedback",
    "detect_atmospheric_medium",
    "detect_atmospheric_medium_feedback",
    "detect_background_complexity",
    "detect_season",
    "detect_depth_of_field",
    "detect_depth_of_field_feedback",
    "detect_exposure_key",
    "detect_focal_perspective",
    "detect_image_grain",
    "detect_image_grain_feedback",
    "detect_image_sharpness",
    "detect_image_sharpness_feedback",
    "detect_lighting_quality",
    "detect_lighting_quality_feedback",
    "detect_motion_rendering",
    "detect_motion_rendering_feedback",
    "detect_saturation_level",
    "detect_saturation_level_feedback",
    "detect_human_subject_intrusions",
    "detect_key_light_direction",
    "detect_key_light_direction_feedback",
    "detect_light_temperature",
    "detect_light_temperature_feedback",
    "detect_negated_camera_angle",
    "detect_negated_camera_roll",
    "detect_negated_composition_placement",
    "detect_negated_screen_direction",
    "detect_negated_spatial_axis_continuity",
    "detect_negated_foreground_occlusion",
    "detect_negated_subject_support_state",
    "detect_negated_gaze_target",
    "detect_negated_camera_stability",
    "detect_negated_color_rendering",
    "detect_negated_contrast_level",
    "detect_negated_detail_density",
    "detect_negated_visual_medium",
    "detect_negated_projection_geometry",
    "detect_negated_perspective_layout",
    "detect_negated_atmospheric_medium",
    "detect_negated_background_complexity",
    "detect_negated_season",
    "detect_negated_depth_of_field",
    "detect_negated_exposure_key",
    "detect_negated_focal_perspective",
    "detect_negated_image_grain",
    "detect_negated_image_sharpness",
    "detect_negated_key_light_direction",
    "detect_negated_lighting_quality",
    "detect_negated_motion_rendering",
    "detect_negated_saturation_level",
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
    "detect_subject_orientation_feedback",
    "detect_subject_pose",
    "detect_subject_pose_feedback",
    "detect_shot_scale",
    "detect_shot_scale_feedback",
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
