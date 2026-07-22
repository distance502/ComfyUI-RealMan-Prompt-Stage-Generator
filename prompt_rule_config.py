# -*- coding: utf-8 -*-
"""
阶段式提示词规则配置
"""

from __future__ import annotations

成人向附加负面词_ZH = [
    "未成年",
    "幼态",
    "萝莉感",
    "课堂情境",
    "校规情境",
    "违法暗示",
    "强迫暗示",
    "暴力羞辱",
    "露骨器官特写",
]
成人向附加负面词_EN = [
    "underage",
    "childlike",
    "loli-like",
    "classroom scenario",
    "school discipline scenario",
    "illegal implication",
    "coercion implication",
    "sexual violence implication",
    "explicit anatomy close-up",
]
低遮挡附加负面词_ZH = [
    "大面积前景遮挡",
    "过度环境遮挡",
    "浓雾遮挡",
    "烟雾遮挡",
    "厚重披帛遮挡",
    "厚重长袍遮挡",
]
低遮挡附加负面词_EN = [
    "heavy foreground obstruction",
    "excessive environmental occlusion",
    "dense fog obstruction",
    "smoke obstruction",
    "heavy drapery covering the body",
    "heavy robe covering the body",
]
成人向构图附加负面词_ZH = [
    "臀部前景抢镜",
    "夸张臀腿透视",
    "极端近大远小",
    "下半身贴脸前景",
    "躯干缺失",
    "身体主体不完整",
    "头身分离构图",
    "过度折叠姿态",
]
成人向构图附加负面词_EN = [
    "buttocks dominating foreground",
    "exaggerated hip and leg perspective",
    "extreme foreshortening",
    "lower body pressed into face foreground",
    "missing torso",
    "incomplete body subject",
    "head and body disconnected composition",
    "over-folded pose",
]
模板附加负面词_ZH = {
    "真实感": ["OVA风", "插画感", "赛璐璐", "低保真", "印刷网点", "自然噪点", "3D渲染", "虚幻引擎", "Octane渲染", "score_9", "score_8_up", "score_7_up", "<lora:", "embedding:"],
    "插画感": ["照片级", "raw photo", "CCD感", "手机抓拍", "纪实", "score_9", "score_8_up", "score_7_up", "<lora:", "embedding:"],
    "CG感": ["糖水片", "手机抓拍", "无滤镜直出", "插画感", "手绘画风", "赛璐璐", "怀旧动画", "复古动画", "低保真", "印刷网点", "自然噪点", "score_9", "score_8_up", "score_7_up", "<lora:", "embedding:"],
    "古风": ["赛博朋克", "霓虹都市", "未来都市", "手机抓拍", "score_9", "score_8_up", "score_7_up", "<lora:", "embedding:"],
    "神话感": ["私房写真", "糖水片", "手机抓拍", "普通影楼写真", "插画感", "手绘画风", "怀旧动画", "复古动画", "低保真", "印刷网点", "自然噪点", "液态金属长裙", "液态金属礼服", "金属礼服", "镜面镀铬布料", "镜面布料", "通体金属盔甲裙", "过强中轴光柱", "主体被神光柱吞没", "score_9", "score_8_up", "score_7_up", "<lora:", "embedding:"],
}
模板附加负面词_EN = {
    "真实感": ["ova style", "cel shading", "3d render", "unreal engine look", "score_9", "score_8_up", "score_7_up", "<lora:", "embedding:"],
    "插画感": ["photorealistic", "raw photo", "ccd look", "phone snapshot", "documentary photo", "score_9", "score_8_up", "score_7_up", "<lora:", "embedding:"],
    "CG感": ["sweet portrait style", "phone snapshot", "unfiltered snapshot", "hand-drawn linework", "score_9", "score_8_up", "score_7_up", "<lora:", "embedding:"],
    "古风": ["cyberpunk", "neon city", "futuristic city", "phone snapshot", "score_9", "score_8_up", "score_7_up", "<lora:", "embedding:"],
    "神话感": ["boudoir photoshoot", "sweet portrait style", "phone snapshot", "ordinary studio portrait", "liquid metal dress", "liquid metal gown", "metallic gown", "mirror chrome fabric", "mirror cloth", "full metallic armor gown", "oversized central light pillar", "subject swallowed by holy light column", "score_9", "score_8_up", "score_7_up", "<lora:", "embedding:"],
}
近景人像附加负面词_ZH = [
    "微距镜头",
    "硬光打脸",
    "粗糙毛孔",
    "皮肤锐化过度",
    "法令纹过深",
    "眼周皱纹过重",
    "额头纹理过硬",
    "皮肤褶皱夸张",
    "妆面干裂",
]
近景人像附加负面词_EN = [
    "macro shot",
    "harsh facial light",
    "coarse pores",
    "over-sharpened skin",
    "deep nasolabial folds",
    "heavy under-eye wrinkles",
    "hard forehead lines",
    "exaggerated skin creases",
    "cracked makeup",
]
全身构图附加负面词_ZH = ["截断双腿", "截断脚部", "局部裁切身体"]
全身构图附加负面词_EN = ["cropped legs", "cropped feet", "partial body crop"]
全局单帧附加负面词_ZH = [
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
    "前后两段重复画面",
    "同一画面上下复制",
    "双重曝光人物构图",
]
全局单帧附加负面词_EN = [
    "vertically duplicated image",
    "top-bottom split screen",
    "left-right split screen",
    "split-screen composition",
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
    "front and back duplicated frame",
    "same image copied top and bottom",
    "double-exposure person layout",
]
主体复制附加负面词_ZH = [
    "同一人物重复出现",
    "复制人物",
    "克隆主体",
    "重复脸",
    "重复头部",
    "额外头部",
    "一人多脸",
    "双重面孔",
    "镜像复制主体",
    "倒影变成第二人物",
    "人物前后重复",
    "前景背景同一人物",
    "半透明人物残影",
    "脸部重影",
    "背景幽灵脸",
    "动作残影复制身体",
]
主体复制附加负面词_EN = [
    "same person repeated",
    "duplicated person",
    "cloned subject",
    "repeated face",
    "duplicate head",
    "extra head",
    "multiple faces on one person",
    "double face",
    "mirror-cloned subject",
    "reflection becoming a second person",
    "same person repeated in foreground and background",
    "foreground and background duplicate subject",
    "transparent duplicate person",
    "ghosted face",
    "ghost face in background",
    "motion trail duplicating the body",
]
多视图一致性附加负面词_ZH = [
    "同一视图重复",
    "无意义重复角度",
    "跨视图身份漂移",
    "跨视图服装变化",
    "单个视图出现多张脸",
    "设定图混入无关人物",
    "叙事时间切片混入设定图",
]
多视图一致性附加负面词_EN = [
    "duplicated identical view",
    "redundant camera angle",
    "identity drift across views",
    "wardrobe drift across views",
    "multiple faces inside one view",
    "unrelated person in character sheet",
    "narrative time slice inside character sheet",
]
多主体构图附加负面词_ZH = [
    "单人前景过大压缩另一人",
    "一人清晰另一人模糊失焦",
    "双人头身比例失衡",
    "双人前后距离过大",
    "一人遮挡另一人脸部",
    "只剩单人主体可读",
    "前景人物腰臀抢镜",
    "双人站位断裂",
    "多人脸部融合",
    "人物身份互换",
    "同一人克隆成群像",
    "额外未指定人物",
]
多主体构图附加负面词_EN = [
    "one subject oversized in foreground overpowering the other",
    "one person sharp while the other is blurred out of focus",
    "imbalanced head to body ratio between two subjects",
    "excessive front to back distance between two subjects",
    "one subject blocking the other's face",
    "only one readable subject in a supposed duo shot",
    "foreground torso or hips stealing focus in duo composition",
    "disconnected duo staging",
    "fused faces in a group",
    "swapped identities between subjects",
    "one person cloned into a group",
    "extra unspecified person",
]
年龄一致性附加负面词_ZH = [
    "年轻脸老手同框",
    "年轻脸老颈纹",
    "脸部年龄与手部年龄不一致",
    "脸部年龄与颈部年龄不一致",
    "过重手背皱纹",
    "过重颈纹",
    "手部老态喧宾夺主",
]
年龄一致性附加负面词_EN = [
    "young face with aged hands",
    "young face with aged neck lines",
    "face age inconsistent with hand age",
    "face age inconsistent with neck age",
    "over-pronounced hand wrinkles",
    "over-pronounced neck lines",
    "aged hands stealing focus",
]
单人构图附加负面词_ZH = [
    "单人图混入背景路人",
    "单人图误入第二人物",
    "背景人物抢戏",
    "大件前景家具抢镜",
    "环境物件成为第二视觉中心",
    "场景元素过满挤压主体",
    "单人主体出现两张脸",
    "单人主体出现额外头部",
    "单人主体被复制",
    "单人前后景各出现一次",
    "单人背后出现同脸人物",
    "单人脸部产生重影",
    "单人身体双重曝光",
]
单人构图附加负面词_EN = [
    "background bystander intruding into a single-subject shot",
    "accidental second person in a supposed solo composition",
    "background figure stealing attention",
    "large foreground furniture stealing focus",
    "environment props becoming a second visual center",
    "overloaded scene elements squeezing the subject",
    "two faces on one solo subject",
    "extra head on a solo subject",
    "duplicated solo subject",
    "solo subject repeated across depth planes",
    "same face appearing behind the solo subject",
    "ghosted face on a solo subject",
    "double-exposed solo body",
]
手部构图附加负面词_ZH = [
    "前景大手抢镜",
    "手指过长",
    "手部比例失衡",
    "掌背皱线过重",
    "手势悬空无支撑",
    "手部遮挡脸部",
]
手部构图附加负面词_EN = [
    "oversized foreground hand stealing focus",
    "overlong fingers",
    "imbalanced hand proportions",
    "over-emphasized back-of-hand wrinkles",
    "unsupported floating hand gesture",
    "hands blocking the face",
]
配饰构图附加负面词_ZH = [
    "珠宝堆满头胸",
    "头饰项链胸针同时抢戏",
    "饰品主次失衡",
    "头饰过大压脸",
    "首饰密度过高",
]
配饰构图附加负面词_EN = [
    "jewelry overcrowding the head and chest",
    "headdress necklace and brooch competing at once",
    "accessory hierarchy imbalance",
    "oversized headdress pressing on the face",
    "excessive jewelry density",
]

人物细分负面词权重包_ZH = {
    "female_realistic": ["前景脚部抢镜", "高跟鞋前景放大", "局部身体压脸", "珠宝喧宾夺主", "多套服装并列", "多场景拼贴", "年轻脸老手同框", "背景人物抢戏"],
    "male_realistic": ["女性化服装语义漂移", "珠宝主导画面", "薄纱主导画面", "局部身体展示替代结构", "多场景拼贴", "肩线塌陷", "年轻脸老颈纹", "背景人物抢戏"],
    "female_adult": ["大脚前景", "高跟鞋压镜头", "胸臀腿抢戏", "极端低角度畸变", "身体局部压脸", "卧室海边酒吧拼贴"],
    "male_adult": ["女性私房构图逻辑", "御姐语义漂移", "女性化面料主导", "局部身体抢戏", "酒瓶道具前景放大", "多场景拼贴"],
}
人物细分负面词权重包_EN = {
    "female_realistic": ["foreground feet dominance", "enlarged high heels in foreground", "body part overpowering face", "jewelry stealing focus", "multiple outfit states", "multi-scene collage", "young face with aged hands", "background figure stealing attention"],
    "male_realistic": ["feminized outfit drift", "jewelry-dominant framing", "sheer fabric dominance", "body-part display replacing structure", "multi-scene collage", "collapsed shoulder line", "young face with aged neck lines", "background figure stealing attention"],
    "female_adult": ["giant feet in foreground", "high heels pressed into lens", "breast hip leg dominance", "extreme low-angle distortion", "body parts overpowering face", "bedroom beach bar collage"],
    "male_adult": ["female boudoir composition logic", "onee-san semantic drift", "feminine fabric dominance", "body-part dominance", "liquor bottle enlarged in foreground", "multi-scene collage"],
}

景别负面词权重包_ZH = {
    "close": ["前景脚部放大", "前景道具压脸", "局部身体透视畸变", "脸部不居中", "只剩局部身体"],
    "mid": ["腰臀前景抢镜", "胸腰压脸", "手脚比例异常", "半身躯干缺失", "场景信息过满"],
    "wide": ["脚部裁切", "双腿裁切", "头身比例异常", "关节弯折异常", "站姿重心漂浮"],
}
景别负面词权重包_EN = {
    "close": ["foreground feet enlargement", "props covering the face", "body-part perspective distortion", "face losing visual center", "partial body only"],
    "mid": ["hips dominating foreground", "torso overpowering face", "abnormal hand or foot proportions", "missing half-body torso", "overloaded scene details"],
    "wide": ["cropped feet", "cropped legs", "abnormal head-body ratio", "broken joint anatomy", "floating body balance"],
}

成人向标签关键词 = {
    "成人向",
    "私房写真",
    "暧昧",
    "性感氛围",
    "NSFW感",
    "纯欲风",
    "轻熟感",
    "微醺感",
    "私密氛围",
    "比基尼",
    "连体泳衣",
    "睡裙",
    "浴袍",
    "内衣风",
    "高跟鞋",
    "锁骨特写",
    "贴身布料感",
}
成人向低遮挡标签集合 = {"弱遮挡", "少遮挡", "遮挡最小化", "无遮挡感"}
成人向低遮挡弱化片段集合 = {"环境遮挡", "雾气遮挡", "前景遮挡", "烟雾", "烟尘"}
本地回退风格优先级映射 = {
    "真实感": ["真实感", "时尚写真", "糖水片", "杂志感", "胶片感", "CCD感", "照片级", "写真", "纪实"],
    "插画感": ["插画感", "OVA风", "手绘画风", "怀旧动画", "赛璐璐", "线条感", "低保真", "印刷网点"],
    "CG感": ["CG感", "3D渲染", "虚幻引擎", "Octane渲染", "史诗感", "游戏风", "未来感"],
    "古风": ["古风", "玄幻古风", "国风美学", "水墨", "国潮", "异域风情"],
    "神话感": ["神话感", "神圣", "史诗感", "国风美学", "CG感"],
}
本地回退成人优先级 = ["私房", "性感氛围", "暧昧", "成人向", "NSFW感", "纯欲风", "轻熟感", "微醺感", "私密氛围", "比基尼", "睡裙", "高跟鞋", "落地窗夜景", "浴缸", "锁骨特写", "贴身布料感", "弱遮挡", "少遮挡", "遮挡最小化", "无遮挡感"]
本地回退光影优先级 = ["自然光", "柔光", "逆光", "轮廓光", "体积光", "暖色调", "黄昏", "夜晚", "朦胧感"]
本地回退主体成人优先级 = ["成年女性", "成年男性", "中年女性", "中年男性", "御姐", "成熟", "性感", "妩媚"]
本地回退成人场景优先级 = ["卧室", "厨房", "阳台", "落地窗夜景", "海边", "酒店氛围"]
本地回退成人低遮挡场景优先级 = ["白色背景", "纯色背景", "落地窗夜景", "卧室", "阳台", "浴缸", "海边", "酒店氛围"]
本地回退成人低遮挡构图优先级 = ["全身", "全景全身", "全景", "中景半身", "半身", "侧面", "平视", "45度角", "定焦", "标准镜头", "中心构图", "三分法"]
本地回退双人构图优先级 = [
    "中景半身",
    "中景",
    "全景全身",
    "全景",
    "全身",
    "平视",
    "45度角",
    "侧面",
    "低角度",
    "标准镜头",
    "定焦",
    "中心构图",
    "三分法",
    "引导线",
    "对称构图",
]
本地回退成人低遮挡光影优先级 = ["柔光", "自然光", "侧光", "逆光", "暖色调", "低饱和", "黄昏", "夜晚"]
本地回退构图优先级 = ["面部特写", "近景", "中近景", "中景", "全景", "全身", "45度角", "低角度", "平视", "侧面", "定焦", "标准镜头", "广角", "中心构图", "三分法"]
本地回退柔和人像光影优先级 = ["自然光", "柔光", "侧光", "逆光", "漫射光", "黄昏", "黄金时刻", "暖色调", "朦胧感"]
本地主提示词人物链配饰优先级映射 = {
    "真实感": ["耳环", "项链", "眼镜", "帽子", "发饰"],
    "插画感": ["发饰", "胸针", "耳环", "项链", "帽子"],
    "CG感": ["胸针", "项链", "发饰", "耳环", "戒指"],
    "古风": ["步摇", "花钿", "簪花", "珠帘", "鬓边帘", "发饰", "耳环"],
    "神话感": ["发冠", "发饰", "项链", "耳环", "胸针"],
}
本地主提示词人物链发型优先级 = ["发髻", "长发", "短发", "刘海", "编发", "马尾", "发丝"]
本地主提示词人物链妆容优先级 = ["裸妆", "淡妆", "红唇", "浓妆", "烟熏"]
本地主提示词人物链女性发型优先级 = ["黑长直", "长直发", "波浪卷发", "高马尾", "低马尾", "麻花辫", "公主切", "丸子头", "齐刘海", "银白长发"]
本地主提示词人物链男性发型优先级 = ["短碎发", "中分短发", "背头", "寸头", "狼尾短发"]
本地主提示词人物链女性配饰优先级映射 = {
    "真实感": ["耳环", "珍珠耳坠", "项链", "发饰", "帽子"],
    "插画感": ["发饰", "耳环", "珍珠耳坠", "胸针", "发冠"],
    "CG感": ["发饰", "胸针", "耳环", "项链", "发冠"],
    "古风": ["步摇", "花钿", "簪花", "珠帘", "鬓边帘", "发饰", "珍珠耳坠"],
    "神话感": ["发冠", "发饰", "耳环", "珍珠耳坠", "项链"],
}
本地主提示词人物链男性配饰优先级映射 = {
    "真实感": ["眼镜", "领带", "领结", "袖扣", "帽子"],
    "插画感": ["帽子", "眼镜", "领结", "胸针", "耳钉"],
    "CG感": ["胸针", "领结", "耳钉", "眼镜", "帽子"],
    "古风": ["帷帽", "帽子", "耳钉", "胸针", "领结"],
    "神话感": ["胸针", "耳钉", "帽子", "领结", "眼镜"],
}
本地主提示词人物链成人向发型优先级 = ["黑长直", "长直发", "波浪卷发", "高马尾", "低马尾", "短碎发", "中分短发"]
本地主提示词人物链成人向女性配饰优先级 = ["耳环", "珍珠耳坠", "项链", "发饰", "眼镜"]
本地主提示词人物链成人向男性配饰优先级 = ["领带", "耳钉", "眼镜", "胸针", "项链"]
成人向克制头饰标签集合 = {"步摇", "花钿", "簪花", "珠帘", "鬓边帘", "发冠", "帷帽"}
成人向身体局部标签集合 = {
    "锁骨特写",
    "锁骨线条",
    "背部曲线",
    "腰臀线条",
    "腿部线条",
    "腹肌线条",
    "人鱼线",
    "大面积肌肤裸露",
    "身体轮廓清晰",
    "湿发",
    "湿发贴肤",
    "贴身布料感",
}
本地主提示词成人身体局部优先级映射 = {
    "close": ["锁骨特写", "锁骨线条", "湿发", "湿发贴肤", "贴身布料感", "身体轮廓清晰"],
    "mid": ["背部曲线", "腰臀线条", "腹肌线条", "人鱼线", "贴身布料感", "身体轮廓清晰"],
    "wide": ["腿部线条", "腰臀线条", "人鱼线", "腹肌线条", "大面积肌肤裸露", "身体轮廓清晰"],
}
本地主提示词人物链动作优先级映射 = {
    "close": ["回眸", "扶发", "抬手", "托腮", "整理衣领", "侧身", "低头浅笑", "抬眼凝视", "轻微歪头"],
    "mid": ["侧身", "回眸", "倚靠栏杆", "伸手触碰", "单手叉腰", "双手抱臂", "站姿放松", "站姿挺拔"],
    "wide": ["行走", "转身", "跨步", "奔跑", "跳跃", "提裙摆", "持物待发", "披风扬起", "裙摆飞扬"],
}
本地主提示词人物链女性动作优先级映射 = {
    "close": ["回眸", "扶发", "轻拈发梢", "扶簪回眸", "托腮", "低头浅笑", "轻微歪头"],
    "mid": ["侧身", "回眸", "提裙摆", "提裙回身", "轻提裙角", "拈花而立", "倚靠栏杆"],
    "wide": ["提裙摆", "提裙回身", "轻提裙角", "踮脚回望", "双手提裙摆", "裙摆飞扬", "行走"],
}
本地主提示词人物链男性动作优先级映射 = {
    "close": ["整理衣领", "整理袖口", "拉领带", "抬眼凝视", "侧身", "抱臂而立"],
    "mid": ["双手抱臂", "双手负后", "侧身", "扶剑而立", "抬臂撑墙", "站姿挺拔"],
    "wide": ["扶剑而立", "阔步前行", "持刀回身", "跨步", "行走", "持物待发", "披风扬起"],
}
本地主提示词人物链成人低遮挡女性动作优先级映射 = {
    "close": ["侧身", "回眸", "抬手", "扶发", "低头浅笑"],
    "mid": ["侧身", "提裙回身", "轻提裙角", "站姿挺拔", "转身", "倚靠栏杆"],
    "wide": ["站姿挺拔", "转身", "提裙回身", "轻提裙角", "双手提裙摆", "行走"],
}
本地主提示词人物链成人低遮挡男性动作优先级映射 = {
    "close": ["侧身", "抬眼凝视", "整理衣领", "抬臂撑墙"],
    "mid": ["侧身", "双手负后", "站姿挺拔", "转身", "抬臂撑墙"],
    "wide": ["站姿挺拔", "双手负后", "转身", "阔步前行", "持物待发"],
}
本地主提示词世界观链场景优先级映射 = {
    "真实感": ["卧室", "落地窗夜景", "阳台", "海边", "街道", "公园", "厨房", "校园", "咖啡厅"],
    "插画感": ["森林", "乡村小道", "图书馆", "画室", "花海", "异世界", "中世纪城镇"],
    "CG感": ["未来都市", "机库", "工业展台", "实验室", "战场", "宫殿", "异世界", "云海", "神殿"],
    "古风": ["宫殿", "竹林", "古风建筑", "寺庙", "山顶", "樱花树下", "市井"],
    "神话感": ["神殿", "宫殿", "宗教圣所", "云海", "星空", "异世界"],
}
本地主提示词世界观链光影优先级映射 = {
    "真实感": ["自然光", "柔光", "侧光", "逆光", "黄金时刻", "黄昏", "暖色调", "蓝调时刻"],
    "插画感": ["柔光", "光影斑驳", "浮光", "轮廓光", "黄昏", "朦胧感", "怀旧"],
    "CG感": ["体积光", "轮廓光", "发丝光", "硬光", "电影色调", "夜晚", "低饱和"],
    "古风": ["柔光", "浮光", "光影斑驳", "自然光", "黄昏", "暖色调"],
    "神话感": ["体积光", "轮廓光", "黄金时刻", "夜晚", "史诗", "神圣"],
}
本地主提示词世界观链材质优先级映射 = {
    "真实感": ["布料质感", "针织", "皮革", "发丝细节", "皮肤纹理"],
    "插画感": ["布料质感", "金属", "发丝细节", "低保真"],
    "CG感": ["金属", "皮革", "镜面反射", "丝绸", "玻璃质感", "次表面散射"],
    "古风": ["香云纱", "苏绣", "丝绸", "真实发丝", "细腻肌理"],
    "神话感": ["丝绸", "金属", "布料质感", "细腻肌理", "次表面散射"],
}
本地主提示词世界观链道具优先级映射 = {
    "真实感": ["花束", "酒杯", "眼镜", "帽子"],
    "插画感": ["法杖", "面具", "卷轴", "剑"],
    "CG感": ["法器", "剑", "枪", "盾"],
    "古风": ["剑", "扇", "伞", "卷轴", "灯笼"],
    "神话感": ["法器", "权杖", "法杖", "卷轴"],
}
本地主提示词世界观链特效优先级 = ["体积光", "轮廓光", "辉光", "光晕", "粒子", "法阵", "烟尘", "烟雾"]

__all__ = [name for name in globals() if not name.startswith("_")]
