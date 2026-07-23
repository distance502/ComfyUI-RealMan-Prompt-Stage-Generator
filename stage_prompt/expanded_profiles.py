# -*- coding: utf-8 -*-
"""Large data-driven template-style and theme-pool expansion profiles."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _style_row(
    name: str,
    base: str,
    lead_zh: str,
    lead_en: str,
    first: tuple[str, str, str, str],
    second: tuple[str, str, str, str],
) -> tuple[Any, ...]:
    return name, base, lead_zh, lead_en, first, second


_EXPANDED_TEMPLATE_ROWS = (
    _style_row("纪实摄影", "真实感", "具有现场感的纪实摄影", "observational documentary photography", ("纪实抓拍", "雨后街头", "阴天柔散光", "35mm胶片摄影"), ("都市纪实", "火车站台", "自然光", "电影胶片look")),
    _style_row("街头摄影", "真实感", "自然松弛的街头摄影", "candid street photography", ("街拍", "城市街边", "午后自然光", "复古颗粒"), ("街头纪实", "老城街巷", "广告屏反射光", "湿沥青反光")),
    _style_row("人文电影", "真实感", "克制而有叙事感的人文电影剧照", "restrained humanist cinematic still", ("都市电影人文", "雨夜站台", "阴天柔散光", "35mm胶片摄影"), ("生活电影剧照", "独立书店", "窗边光", "电影胶片look")),
    _style_row("黑色电影", "真实感", "高反差黑色电影剧照", "high-contrast film noir still", ("黑色电影", "夜间街道", "黑色电影硬光", "低饱和冷灰"), ("港风恐怖电影调", "废弃地下老屋", "冷雾惊悚侧光", "港片胶片质感")),
    _style_row("日系电影", "真实感", "清透克制的日系电影定帧", "quiet Japanese cinematic still", ("日系电影感", "雨后街头", "阴天柔散光", "日系影像质感"), ("生活流写实", "火车站台", "黄昏逆光", "35mm胶片摄影")),
    _style_row("韩系极简", "真实感", "干净克制的韩系极简影像", "clean Korean minimalist imagery", ("韩系极简影像", "韩系公寓走廊", "冷灰极简棚光", "韩系广告质感"), ("高端时尚编辑肖像", "极简白棚", "高窗冷天光", "肤色校正自然")),
    _style_row("港片胶片", "真实感", "潮湿浓郁的港片胶片剧照", "moody Hong Kong film still", ("港片胶片质感", "霓虹街区", "广告屏反射光", "复古非镀膜镜头"), ("港风惊悚志怪", "冷雾古巷", "冷雾惊悚侧光", "老胶片褪色感")),
    _style_row("欧洲艺术电影", "真实感", "低饱和欧洲艺术电影定帧", "muted European art-house cinema still", ("电影剧照感", "旧酒店大堂", "窗边自然光", "低饱和"), ("纪实电影摄影", "石板路", "暮色天光", "35mm胶片摄影")),
    _style_row("新复古胶片", "真实感", "新复古胶片时尚影像", "neo-vintage film photography", ("奶油胶片", "复古公寓", "暖褪色胶片", "复古颗粒"), ("胶片时装片", "旧酒店大堂", "钨丝灯实景光", "电影胶片look")),
    _style_row("宝丽来摄影", "真实感", "即时成像质感的宝丽来摄影", "instant-film Polaroid photography", ("宝丽来质感", "纯色背景", "正面闪光", "白边相纸"), ("生活抓拍", "卧室", "窗边光", "褪色胶片")),
    _style_row("湿版肖像", "真实感", "古典湿版工艺肖像", "antique wet-plate portrait", ("湿版摄影", "暗色布景", "柔和侧光", "银盐颗粒"), ("古典肖像", "旧摄影棚", "伦勃朗光", "旧玻璃划痕")),
    _style_row("水下摄影", "真实感", "清澈有层次的水下摄影", "layered underwater photography", ("水下摄影", "海底王国", "水下焦散", "漂浮气泡"), ("水下人像", "水晶湖", "水晶折射光", "流动薄纱")),
    _style_row("舞台摄影", "真实感", "戏剧化舞台摄影", "dramatic stage photography", ("舞台摄影", "剧院舞台", "聚光灯", "舞台烟雾"), ("演唱会摄影", "音乐节后台", "彩色轮廓光", "动态颗粒")),
    _style_row("音乐MV", "真实感", "节奏鲜明的音乐MV定帧", "rhythmic music-video still", ("音乐MV", "霓虹街区", "蓝洋红对撞", "变形宽银幕"), ("概念MV", "极简影棚", "红雾表现主义打光", "慢门拖影")),
    _style_row("建筑摄影", "真实感", "强调秩序与尺度的建筑摄影", "ordered architectural photography", ("建筑摄影", "现代建筑", "穹顶天光", "广角透视"), ("室内建筑摄影", "极简大厅", "自然光", "材质细节丰富")),
    _style_row("产品广告", "真实感", "高控制度产品广告摄影", "high-control product advertising photography", ("产品广告", "金属展台", "轮廓光", "高光材质"), ("商业广告大片", "极简白棚", "硬光", "广告成片质感")),
    _style_row("珠宝广告", "真实感", "精密闪耀的珠宝广告摄影", "precision jewelry advertising photography", ("珠宝广告", "暗色丝绒展台", "锐利高光", "宝石色调"), ("奢侈品广告", "镜面展台", "轮廓光", "水晶折射")),
    _style_row("汽车广告", "真实感", "电影级汽车广告画面", "cinematic automotive advertising image", ("汽车广告", "城市高架", "日落逆光", "金属反光"), ("性能广告", "山路弯道", "硬光", "运动模糊")),
    _style_row("运动广告", "真实感", "充满力量与速度的运动广告", "dynamic sports advertising photography", ("运动广告", "专业赛场", "高对比", "汗水飞溅"), ("户外运动大片", "山地公路", "黄金时刻侧光", "动态抓拍")),
    _style_row("超现实摄影", "真实感", "真实材质与奇异空间融合的超现实摄影", "surreal photography with realistic materials", ("超现实摄影", "镜面空间", "体积光", "漂浮物体"), ("梦境摄影", "无边水面", "柔和光晕", "尺度错位")),
    _style_row("梦核摄影", "真实感", "熟悉而疏离的梦核摄影", "uncanny dreamcore photography", ("梦核", "空旷商场", "冷荧顶光", "低保真"), ("阈限空间", "无尽走廊", "暖褪色胶片", "轻微色差")),
    _style_row("水彩插画", "插画感", "通透柔和的水彩叙事插画", "luminous watercolor narrative illustration", ("水彩晕染", "湖畔", "柔和色彩", "纸张纹理"), ("水彩线稿", "花园", "清晨柔光", "手绘光效")),
    _style_row("水粉绘本", "插画感", "厚实温暖的水粉绘本插画", "warm gouache storybook illustration", ("水粉插画", "奇幻集市", "暖色灯光", "颗粒质感"), ("童话绘本", "森林小屋", "叶隙斑驳光", "手绘纸纹")),
    _style_row("工笔重彩", "古风", "细密华丽的工笔重彩画", "meticulous Chinese gongbi painting", ("工笔插画感", "宫殿", "柔和侧光", "矿物重彩"), ("国风美学", "水榭", "纸窗天光", "丝绢纹理")),
    _style_row("敦煌壁画", "神话感", "矿物色与飞天构成的敦煌壁画", "Dunhuang mural with mineral pigments", ("敦煌神性", "悬空神庙", "金雾神光", "神话壁画质感"), ("神庙壁画感", "天穹祭坛", "圣辉逆光", "风化壁画纹理")),
    _style_row("浮世绘", "插画感", "平面节奏鲜明的浮世绘版画", "rhythmic ukiyo-e woodblock print", ("浮世绘", "海岸", "扁平色块", "木刻纹理"), ("日式版画", "古城街道", "暮色天光", "套色印刷")),
    _style_row("新艺术运动", "插画感", "植物曲线与装饰边框构成的新艺术插画", "Art Nouveau decorative illustration", ("新艺术运动", "花卉拱门", "柔和光晕", "装饰线条"), ("穆夏式装饰画", "圆形花窗", "金色晨辉", "平面纹样")),
    _style_row("装饰艺术", "插画感", "几何秩序鲜明的装饰艺术海报", "geometric Art Deco poster", ("装饰艺术", "豪华酒店", "金色侧光", "几何边框"), ("复古海报", "剧院大厅", "高对比", "金黑配色")),
    _style_row("波普艺术", "插画感", "高饱和图形化波普艺术", "graphic high-saturation pop art", ("波普艺术", "纯色背景", "高调硬光", "印刷网点"), ("漫画广告", "都市橱窗", "双色调", "粗线条")),
    _style_row("美式漫画", "插画感", "强轮廓与戏剧动作的美式漫画", "bold American comic-book illustration", ("美式漫画", "城市屋顶", "高对比", "粗重墨线"), ("超级英雄漫画", "街道战场", "戏剧逆光", "网点印刷")),
    _style_row("暗黑漫画", "插画感", "浓重阴影与压迫构图的暗黑漫画", "dark graphic-novel illustration", ("暗黑漫画", "地下通道", "冷雾惊悚侧光", "黑白线稿"), ("恐怖漫画", "废弃老屋", "顶光烟雾", "刮擦纹理")),
    _style_row("漫画线稿", "插画感", "干净有表现力的漫画线稿", "clean expressive manga line art", ("黑白线稿", "纯色背景", "柔和光晕", "干净线条"), ("网点漫画", "城市街道", "高对比", "印刷网点")),
    _style_row("像素艺术", "插画感", "层次清晰的高完成度像素艺术", "highly finished pixel art", ("像素艺术", "异世界城镇", "霓虹夜色", "有限色板"), ("16位像素风", "森林遗迹", "黄昏逆光", "逐帧动画感")),
    _style_row("剪纸艺术", "插画感", "层叠镂空的剪纸艺术", "layered paper-cut illustration", ("剪纸艺术", "山水庭院", "平面侧光", "纸张纤维"), ("民俗剪纸", "节庆街市", "高饱和", "对称纹样")),
    _style_row("木刻版画", "插画感", "粗粝有力量的木刻版画", "expressive woodcut print", ("木刻版画", "山谷", "高对比", "刀刻纹理"), ("黑白版画", "古城", "侧逆光", "纸张颗粒")),
    _style_row("粘土定格", "CG感", "手工质感鲜明的粘土定格动画", "handcrafted clay stop-motion frame", ("粘土定格", "微缩房间", "柔和棚光", "手工指纹"), ("定格动画", "奇幻森林", "暖色灯光", "微缩道具")),
    _style_row("电影概念艺术", "CG感", "电影级世界观概念艺术", "cinematic world-building concept art", ("概念艺术", "巨型城市", "体积光", "空间透视"), ("电影感单幅画面", "远古遗迹", "风暴天光", "史诗概念艺术完成度")),
    _style_row("游戏角色原画", "CG感", "高辨识度游戏角色原画", "high-readability game character concept", ("角色设计稿", "极简影棚", "轮廓光", "奇幻角色设定"), ("游戏风", "战场", "戏剧逆光", "材质细节丰富")),
    _style_row("环境概念设计", "CG感", "空间叙事明确的环境概念设计", "narrative environment concept design", ("环境概念设计", "浮空城", "云隙光", "大气透视"), ("关卡空间单幅画面", "工业废墟", "冷色工业顶光", "空间层次")),
    _style_row("科幻概念设计", "CG感", "结构可信的科幻概念设计", "believable science-fiction concept design", ("科幻概念设计", "环形空间站", "冷白顶光", "硬表面细节"), ("未来工业设计", "火星基地", "日落侧光", "功能结构清晰")),
    _style_row("机甲设定", "CG感", "功能结构明确的机甲设定图", "functional mecha design concept", ("机甲设定", "机库", "冷色工业顶光", "机械关节细节"), ("东方赛博机甲", "地下基地", "全息投影光", "义体金属细节")),
    _style_row("太空歌剧", "CG感", "宏大华丽的太空歌剧主视觉", "grand space-opera key visual", ("太空歌剧", "舰桥", "星际逆光", "变形宽银幕"), ("星际史诗", "深空战场", "爆炸轮廓光", "电影级CG")),
    _style_row("赛博朋克", "CG感", "潮湿高密度的赛博朋克影像", "dense rain-soaked cyberpunk image", ("赛博朋克", "赛博街区", "蓝洋红对撞", "湿沥青反光"), ("机能赛博", "赛博地铁", "全息投影光", "义体金属细节")),
    _style_row("生物机械", "CG感", "有机组织与机械结构融合的生物机械设计", "biomechanical concept design", ("生物机械", "生物实验室", "冷荧顶光", "湿润有机材质"), ("异星生物设计", "异星洞窟", "体积光", "半透明组织")),
    _style_row("蒸汽朋克", "CG感", "黄铜机械与维多利亚造型融合的蒸汽朋克", "Victorian brass steampunk design", ("蒸汽朋克", "飞空艇港", "暖色轮廓逆光", "锤纹黄铜"), ("蒸汽机械", "钟表工坊", "火炬暖光", "旧皮革")),
    _style_row("柴油朋克", "CG感", "重工业与复古军工融合的柴油朋克", "heavy industrial dieselpunk design", ("柴油朋克", "装甲列车站", "烟尘天光", "铆钉钢板"), ("复古军工", "柴油空港", "高对比", "旧金属磨损")),
    _style_row("废土科幻", "CG感", "风化粗粝的废土科幻概念画", "weathered post-apocalyptic sci-fi concept", ("废土科幻", "工业废墟", "沙尘逆光", "风化金属"), ("核后废土", "无人荒城", "低饱和", "旧皮革")),
    _style_row("复古未来", "CG感", "怀旧科技想象的复古未来主视觉", "retro-futurist key visual", ("复古未来主义", "未来都市", "霓虹夜色", "镀铬材质"), ("90年代复古未来动漫", "空间站", "双色调", "VHS噪点")),
    _style_row("超现实CG", "CG感", "真实材质与不可能空间结合的超现实CG", "surreal CG with impossible spatial logic", ("超现实CG", "无边镜面", "体积神光", "漂浮几何"), ("梦境概念设计", "巨物都市", "暮色天光", "尺度错位")),
    _style_row("微缩景观", "CG感", "精密可爱的微缩景观摄影", "detailed miniature-diorama imagery", ("微缩景观", "微缩街区", "柔和棚光", "模型材质"), ("沙盘世界", "微缩工厂", "窗边光", "景深模型感")),
    _style_row("建筑可视化", "CG感", "材质与空间精确的建筑可视化", "precise architectural visualization", ("建筑可视化", "现代大厅", "自然天光", "PBR渲染"), ("未来建筑概念", "云端塔楼", "日落逆光", "玻璃金属材质")),
    _style_row("宋韵工笔", "古风", "清雅克制的宋韵工笔画", "refined Song-dynasty gongbi painting", ("宋韵美学", "月洞门", "纸窗天光", "丝绢纹理"), ("工笔插画感", "水榭", "雨后柔光", "矿物淡彩")),
    _style_row("水墨山水", "古风", "留白与墨韵构成的水墨山水", "Chinese ink-wash landscape", ("水墨", "远山雾气", "云隙光", "负空间留白"), ("墨洗留白", "江南水乡", "阴天柔散光", "宣纸纹理")),
    _style_row("志怪绘卷", "古风", "幽暗诡谲的志怪绘卷", "mysterious Chinese supernatural scroll", ("志怪古风", "冷雾古巷", "冷雾惊悚侧光", "卷轴式构图"), ("港风惊悚志怪", "废弃地下老屋", "烛火暖光", "神谕石碑")),
    _style_row("仙侠电影", "古风", "云海剑影交织的仙侠电影剧照", "cinematic xianxia fantasy still", ("玄幻古风", "仙门云海", "圣辉逆光", "剑刃高光"), ("武侠电影感", "悬崖古道", "蓝灰月光", "衣料褶皱清晰")),
    _style_row("唐风壁画", "神话感", "华丽饱满的唐风壁画主视觉", "ornate Tang-dynasty mural key visual", ("唐风壁画", "长安宫阙", "金色晨辉", "矿物重彩"), ("敦煌神性", "天穹祭坛", "金雾神光", "流光薄纱")),
    _style_row("苗疆奇谭", "古风", "银饰、雾林与秘仪构成的苗疆奇谭", "Miao-inspired mystical cinematic imagery", ("苗疆奇谭", "雾林吊脚楼", "冷雾侧光", "银饰"), ("志怪古风", "山谷祭坛", "火炬暖光", "符铃")),
    _style_row("山海经绘卷", "神话感", "异兽与山川共构的山海经绘卷", "Classic of Mountains and Seas scroll", ("山海经绘卷", "荒古山海", "云隙光", "异兽图谱"), ("东方神话史诗", "昆仑神域", "金雾神光", "神谕石碑")),
    _style_row("东方神话", "神话感", "庄严宏阔的东方神话主视觉", "grand East Asian mythic key visual", ("东方神话史诗", "云上神国", "圣辉逆光", "日轮"), ("神话叙事", "星海神殿", "体积神光", "月轮")),
    _style_row("宇宙神话", "神话感", "星云、巨构与神性符号融合的宇宙神话", "cosmic myth with celestial megastructures", ("宇宙神话", "星海神殿", "星际逆光", "星图仪"), ("神圣史诗", "量子神殿", "金雾神光", "浮空水晶")),
)


def _theme_row(
    name: str,
    english_name: str,
    style: str,
    first: tuple[str, str, str, str],
    second: tuple[str, str, str, str],
) -> tuple[Any, ...]:
    return name, english_name, style, first, second


_EXPANDED_THEME_ROWS = (
    _theme_row("雨夜都市", "rainy-night city", "人文电影", ("摄影师", "雨后街头", "广告屏反射光", "相机"), ("调酒师", "霓虹街区", "蓝洋红对撞", "透明雨伞")),
    _theme_row("清晨通勤", "morning commute", "纪实摄影", ("成年女性", "地铁站", "清晨自然光", "通勤包"), ("成年男性", "火车站台", "阴天柔散光", "有线耳机")),
    _theme_row("深夜便利店", "late-night convenience store", "日系电影", ("成年女性", "都市便利店", "冷荧顶光", "手持饮料"), ("成年男性", "便利店门口", "广告屏反射光", "购物袋")),
    _theme_row("独立书店", "independent bookstore", "人文电影", ("书店女孩", "独立书店", "窗边光", "书本"), ("摄影师", "图书馆", "钨丝灯实景光", "相机")),
    _theme_row("老城漫步", "old-town walk", "街头摄影", ("成年女性", "老城街巷", "午后自然光", "手持相机"), ("成年男性", "石板路", "暮色天光", "行李箱")),
    _theme_row("地铁末班车", "last subway train", "黑色电影", ("成年女性", "赛博地铁", "冷荧顶光", "有线耳机"), ("成年男性", "地下通道", "黑色电影硬光", "公文包")),
    _theme_row("屋顶黄昏", "rooftop at dusk", "日系电影", ("成年女性", "城市天台", "日落逆光", "耳机"), ("成年男性", "屋顶", "黄金时刻侧光", "相机")),
    _theme_row("港口清晨", "harbor morning", "纪实摄影", ("成年女性", "港口", "清晨柔光", "旅行包"), ("成年男性", "码头", "阴天自然光", "绳索")),
    _theme_row("雪夜小镇", "snowy town at night", "欧洲艺术电影", ("成年女性", "雪地", "蓝灰月光", "暖色围巾"), ("成年男性", "小镇街道", "橱窗暖光", "手提灯")),
    _theme_row("复古旅馆", "vintage hotel", "新复古胶片", ("成年女性", "旧酒店大堂", "钨丝灯实景光", "行李箱"), ("调酒师", "酒店酒吧", "暖色轮廓逆光", "酒杯")),
    _theme_row("公路旅行", "road trip", "纪实摄影", ("成年女性", "沙漠公路", "黄金时刻侧光", "旅行地图"), ("成年男性", "山地公路", "日落逆光", "复古汽车")),
    _theme_row("音乐节后台", "music-festival backstage", "音乐MV", ("偶像", "音乐节后台", "彩色轮廓光", "麦克风"), ("摄影师", "演出后台", "舞台灯光", "相机")),
    _theme_row("剧院舞台", "theater stage", "舞台摄影", ("舞者", "剧院舞台", "聚光灯", "红色幕布"), ("成年女性", "空剧场", "顶光烟雾", "面具")),
    _theme_row("爵士酒吧", "jazz bar", "黑色电影", ("调酒师", "爵士酒吧", "钨丝灯实景光", "酒杯"), ("成年女性", "复古酒吧", "暖色轮廓逆光", "麦克风")),
    _theme_row("未来办公室", "future office", "科幻概念设计", ("研究员", "未来办公室", "冷白顶光", "全息界面"), ("律师", "高层会议室", "窗外城市光", "透明终端")),
    _theme_row("奢侈品广告", "luxury campaign", "产品广告", ("影棚时尚女性", "极简影棚", "高窗冷天光", "手提包"), ("成年男性", "大理石大厅", "轮廓光", "腕表")),
    _theme_row("香水广告", "perfume campaign", "超现实摄影", ("成年女性", "镜面空间", "柔和光晕", "香水瓶"), ("影棚时尚女性", "无边水面", "水晶折射光", "花瓣")),
    _theme_row("珠宝广告", "jewelry campaign", "珠宝广告", ("成年女性", "暗色布景", "锐利高光", "宝石项链"), ("影棚时尚女性", "镜面展台", "轮廓光", "水晶耳饰")),
    _theme_row("汽车广告", "automotive campaign", "汽车广告", ("成年男性", "城市高架", "日落逆光", "跑车"), ("成年女性", "山路弯道", "硬光", "复古汽车")),
    _theme_row("运动赛场", "sports arena", "运动广告", ("运动员", "专业赛场", "高对比", "运动器材"), ("成年女性", "夜间跑道", "轮廓光", "水壶")),
    _theme_row("水下人像", "underwater portrait", "水下摄影", ("成年女性", "水晶湖", "水下焦散", "流动薄纱"), ("海洋祭司", "海底王国", "水晶折射光", "水晶法杖")),
    _theme_row("沙漠公路", "desert highway", "纪实摄影", ("成年女性", "沙漠公路", "日落逆光", "旅行地图"), ("成年男性", "荒漠加油站", "硬光", "复古汽车")),
    _theme_row("山谷营地", "valley campsite", "纪实摄影", ("女冒险者", "山谷营地", "清晨柔光", "帐篷"), ("成年男性", "森林营地", "火炬暖光", "冒险地图")),
    _theme_row("极地远征", "polar expedition", "电影概念艺术", ("遗迹探险家", "冰冻森林", "冷冽神性", "探险装备"), ("研究员", "冰原基地", "蓝灰月光", "信号灯")),
    _theme_row("热带雨林", "tropical rainforest", "环境概念设计", ("遗迹探险家", "远古森林", "叶隙斑驳光", "冒险地图"), ("精灵游侠", "森林遗迹", "翡翠森林光", "精灵长弓")),
    _theme_row("火山地貌", "volcanic landscape", "电影概念艺术", ("冰霜骑士", "火山洞穴", "龙焰逆光", "魔剑"), ("遗迹探险家", "熔岩峡谷", "红雾表现主义打光", "神谕石碑")),
    _theme_row("山海经异兽", "mythic beasts of Shanhaijing", "山海经绘卷", ("异兽", "荒古山海", "云隙光", "异兽图谱"), ("神女", "昆仑神域", "金雾神光", "神谕石碑")),
    _theme_row("敦煌天宫", "Dunhuang celestial palace", "敦煌壁画", ("神女", "悬空神庙", "金雾神光", "日轮"), ("祭司", "天穹祭坛", "圣辉逆光", "流光薄纱")),
    _theme_row("唐风长安", "Tang-dynasty Chang'an", "唐风壁画", ("公主", "长安宫阙", "金色晨辉", "鎏金头冠"), ("成年男性", "长安街市", "暖色灯光", "灯笼")),
    _theme_row("宋代汴京", "Song-dynasty Bianjing", "宋韵工笔", ("成年女性", "汴京街市", "阴天柔散光", "油纸伞"), ("书店女孩", "宋代书肆", "纸窗天光", "书卷")),
    _theme_row("江南烟雨", "misty Jiangnan", "水墨山水", ("成年女性", "江南水乡", "雨后柔光", "油纸伞"), ("成年男性", "石桥", "远山雾气", "竹笛")),
    _theme_row("苗疆秘境", "mystical Miao highlands", "苗疆奇谭", ("祭司", "雾林吊脚楼", "冷雾侧光", "银饰"), ("魔女", "山谷祭坛", "火炬暖光", "符铃")),
    _theme_row("西域商路", "Silk Road caravan", "东方神话", ("成年女性", "沙漠商路", "黄金时刻侧光", "旅行地图"), ("成年男性", "沙漠驿站", "暮色天光", "旗帜")),
    _theme_row("海上丝路", "maritime Silk Road", "东方神话", ("成年女性", "古代港口", "清晨柔光", "航海图"), ("成年男性", "商船甲板", "风暴天光", "星图仪")),
    _theme_row("仙门云海", "xianxia sect above the clouds", "仙侠电影", ("女武士", "仙门云海", "圣辉逆光", "飞剑"), ("神圣骑士", "云端阶梯", "金色晨辉", "星辉权杖")),
    _theme_row("妖市夜行", "night market of spirits", "志怪绘卷", ("魔女", "妖市夜行", "暖色灯光", "面具"), ("女冒险者", "奇幻集市", "霓虹夜色", "黑玫瑰")),
    _theme_row("阴司古城", "underworld ancient city", "志怪绘卷", ("黑暗女王", "阴司古城", "冷雾惊悚侧光", "魂灯"), ("祭司", "古城牌楼", "烛火暖光", "神谕石碑")),
    _theme_row("龙宫盛宴", "dragon-palace banquet", "东方神话", ("海洋祭司", "海底王国", "水下焦散", "水晶法杖"), ("公主", "水晶宫殿", "水晶折射光", "珍珠冠冕")),
    _theme_row("昆仑神域", "Kunlun divine realm", "山海经绘卷", ("神女", "昆仑神域", "金雾神光", "日轮"), ("异兽", "荒古山海", "云隙光", "神谕石碑")),
    _theme_row("月宫神话", "moon-palace myth", "东方神话", ("神女", "月宫", "星辉月光", "月轮"), ("祭司", "天穹遗迹", "蓝灰月光", "星图仪")),
    _theme_row("竹林决斗", "bamboo-forest duel", "武侠电影", ("女武士", "幽暗竹林", "暖色轮廓逆光", "剑"), ("成年男性", "竹林", "青蓝冷雾", "长刀")),
    _theme_row("古寺夜雨", "rainy ancient temple", "志怪绘卷", ("魔女", "古寺", "烛火暖光", "油纸伞"), ("成年男性", "冷雾古巷", "蓝灰月光", "灯笼")),
    _theme_row("边塞风雪", "snowy frontier fortress", "武侠电影", ("女武士", "边境要塞", "风暴天光", "披风"), ("成年男性", "雪地", "蓝灰月光", "长枪")),
    _theme_row("星际远征", "interstellar expedition", "太空歌剧", ("研究员", "星际飞船", "星际逆光", "全息界面"), ("成年女性", "深空舰桥", "冷白顶光", "星图仪")),
    _theme_row("火星殖民", "Mars colony", "科幻概念设计", ("研究员", "火星基地", "日落侧光", "透明头盔"), ("工程师", "殖民舱室", "冷色工业顶光", "机械外骨骼")),
    _theme_row("深空遗迹", "deep-space ruins", "电影概念艺术", ("遗迹探险家", "深空遗迹", "体积神光", "浮空水晶"), ("机器人", "废弃空间站", "冷荧顶光", "神谕石碑")),
    _theme_row("环形空间站", "orbital ring station", "科幻概念设计", ("成年女性", "环形空间站", "穹顶天光", "透明终端"), ("机器人", "空间站走廊", "冷白顶光", "全息界面")),
    _theme_row("月球基地", "lunar base", "建筑可视化", ("研究员", "月球基地", "星际逆光", "透明头盔"), ("机器人", "月面机库", "冷色工业顶光", "月球车")),
    _theme_row("生物实验室", "biological laboratory", "生物机械", ("研究员", "生物实验室", "冷荧顶光", "培养舱"), ("异星生物", "地下实验室", "体积光", "全息界面")),
    _theme_row("赛博雨城", "cyberpunk rain city", "赛博朋克", ("未来都市女特工", "霓虹雨夜", "广告屏反射光", "能量刀"), ("成年男性", "赛博街区", "蓝洋红对撞", "机械外骨骼")),
    _theme_row("霓虹九龙", "neon Kowloon", "东方赛博", ("女武士", "高架贫民区", "全息投影光", "能量刀"), ("调酒师", "霓虹街区", "广告屏反射光", "义体接口")),
    _theme_row("机甲机库", "mecha hangar", "机甲设定", ("机甲", "机库", "冷色工业顶光", "机械关节细节"), ("工程师", "地下基地", "全息投影光", "机械外骨骼")),
    _theme_row("无人荒城", "abandoned megacity", "废土科幻", ("机器人", "无人荒城", "沙尘逆光", "破损广告牌"), ("遗迹探险家", "工业废墟", "低饱和", "防毒面具")),
    _theme_row("核后废土", "post-nuclear wasteland", "废土科幻", ("成年女性", "核后废土", "暮色天光", "防毒面具"), ("成年男性", "废弃地下基地", "冷雾侧光", "旧皮革")),
    _theme_row("蒸汽帝国", "steampunk empire", "蒸汽朋克", ("机械魔导师", "蒸汽魔法都市", "暖色轮廓逆光", "魔导机械"), ("成年女性", "飞空艇港", "金色晨辉", "星图仪")),
    _theme_row("柴油空港", "dieselpunk airfield", "柴油朋克", ("成年男性", "柴油空港", "烟尘天光", "飞行夹克"), ("成年女性", "装甲列车站", "高对比", "机械义肢")),
    _theme_row("时间旅行", "time travel", "复古未来", ("研究员", "时间实验室", "全息投影光", "时钟装置"), ("成年女性", "复古车站", "暖褪色胶片", "怀表")),
    _theme_row("平行世界", "parallel worlds", "超现实CG", ("成年女性", "镜像城市", "双色调", "传送门"), ("成年男性", "分裂街道", "体积光", "漂浮几何")),
    _theme_row("梦核空间", "dreamcore space", "梦核摄影", ("成年女性", "空旷商场", "冷荧顶光", "气球"), ("成年男性", "无尽走廊", "暖褪色胶片", "旧电视")),
    _theme_row("后室迷宫", "backrooms maze", "梦核摄影", ("成年男性", "无尽走廊", "冷荧顶光", "手电筒"), ("机器人", "空旷办公室", "低饱和", "监控屏幕")),
    _theme_row("巨物都市", "city of colossal structures", "超现实CG", ("成年女性", "巨物都市", "暮色天光", "尺度参照人物"), ("机器人", "巨大建筑峡谷", "体积光", "飞行载具")),
    _theme_row("海底文明", "underwater civilization", "环境概念设计", ("海洋祭司", "海底王国", "水下焦散", "水晶法杖"), ("机器人", "海底遗迹", "水晶折射光", "潜水器")),
    _theme_row("云端列车", "train above the clouds", "复古未来", ("成年女性", "云端列车", "金色晨辉", "旅行箱"), ("成年男性", "天空站台", "云隙光", "怀表")),
    _theme_row("异星生态", "alien ecology", "生物机械", ("异星生物", "异星森林", "体积光", "发光孢子"), ("研究员", "异星洞窟", "冷色侧光", "采样器")),
    _theme_row("量子神殿", "quantum temple", "宇宙神话", ("祭司", "量子神殿", "金雾神光", "浮空水晶"), ("机器人", "星海神殿", "星际逆光", "星图仪")),
    _theme_row("机器人市集", "robot market", "赛博朋克", ("机器人", "机器人市集", "霓虹夜色", "全息界面"), ("机械魔导师", "奇幻集市", "暖色灯光", "魔导机械")),
    _theme_row("太空歌剧", "space opera", "太空歌剧", ("成年女性", "深空舰桥", "星际逆光", "星图仪"), ("成年男性", "云海战场", "爆炸轮廓光", "旗帜")),
)


EXPANDED_TEMPLATE_BASE_MAP = {row[0]: row[1] for row in _EXPANDED_TEMPLATE_ROWS}
EXPANDED_TEMPLATE_OPTIONS = tuple(EXPANDED_TEMPLATE_BASE_MAP)
EXPANDED_STYLE_LEAD_ZH = {row[0]: row[2] for row in _EXPANDED_TEMPLATE_ROWS}
EXPANDED_STYLE_LEAD_EN = {row[0]: row[3] for row in _EXPANDED_TEMPLATE_ROWS}
EXPANDED_STYLE_TRANSLATIONS = {
    **{row[0]: row[3] for row in _EXPANDED_TEMPLATE_ROWS},
    **{row[2]: row[3] for row in _EXPANDED_TEMPLATE_ROWS},
    **{row[0]: row[1] for row in _EXPANDED_THEME_ROWS},
}


def _style_variant(style_name: str, variant_id: str, values: tuple[str, str, str, str]) -> dict[str, Any]:
    accent, scene, light, finish = values
    return {
        "id": variant_id,
        "tags": [
            (style_name, "画面风格"),
            (accent, "画面风格"),
            (scene, "场景背景"),
            (light, "光影氛围"),
            (finish, "技术画质"),
        ],
    }


EXPANDED_TEMPLATE_STYLE_VARIANTS = {
    row[0]: [
        _style_variant(row[0], "profile-a", row[4]),
        _style_variant(row[0], "profile-b", row[5]),
    ]
    for row in _EXPANDED_TEMPLATE_ROWS
}


def _theme_variant(style: str, variant_id: str, values: tuple[str, str, str, str]) -> dict[str, Any]:
    subject, scene, light, prop = values
    return {
        "id": variant_id,
        "style": style,
        "tags": [
            (style, "画面风格"),
            (subject, "主体"),
            (scene, "场景背景"),
            (light, "光影氛围"),
            (prop, "道具世界观"),
        ],
    }


EXPANDED_THEME_POOL_OPTIONS = tuple(row[0] for row in _EXPANDED_THEME_ROWS)
EXPANDED_THEME_VARIANTS = {
    row[0]: [
        _theme_variant(row[2], "profile-a", row[3]),
        _theme_variant(row[2], "profile-b", row[4]),
    ]
    for row in _EXPANDED_THEME_ROWS
}


_SECTION_BY_GROUP = {
    "主体": "扩展主题身份",
    "画面风格": "扩展模板风格",
    "光影氛围": "扩展光影",
    "服装造型": "扩展服装",
    "场景背景": "扩展主题场景",
    "道具世界观": "扩展叙事元素",
    "构图视角": "扩展构图",
    "动作姿态": "扩展动作",
    "技术画质": "扩展媒介质感",
}
_profile_tags: dict[tuple[str, str], list[str]] = defaultdict(list)
for variants in (*EXPANDED_TEMPLATE_STYLE_VARIANTS.values(), *EXPANDED_THEME_VARIANTS.values()):
    for variant in variants:
        for tag, group in variant.get("tags", []):
            section = _SECTION_BY_GROUP.get(str(group), "扩展档案")
            key = (str(group), section)
            cleaned = str(tag).strip()
            if cleaned and cleaned not in _profile_tags[key]:
                _profile_tags[key].append(cleaned)

for _style_name in EXPANDED_TEMPLATE_OPTIONS:
    _style_key = ("画面风格", "扩展模板风格")
    if _style_name not in _profile_tags[_style_key]:
        _profile_tags[_style_key].append(_style_name)
for _theme_name in EXPANDED_THEME_POOL_OPTIONS:
    _theme_key = ("场景背景", "扩展主题场景")
    if _theme_name not in _profile_tags[_theme_key]:
        _profile_tags[_theme_key].append(_theme_name)

EXPANDED_PROFILE_TAGS_BY_SECTION = dict(_profile_tags)
EXPANDED_STYLE_KEYWORDS_BY_BASE: dict[str, set[str]] = defaultdict(set)
for style_name, base_style in EXPANDED_TEMPLATE_BASE_MAP.items():
    EXPANDED_STYLE_KEYWORDS_BY_BASE[base_style].add(style_name)
    for variant in EXPANDED_TEMPLATE_STYLE_VARIANTS.get(style_name, []):
        EXPANDED_STYLE_KEYWORDS_BY_BASE[base_style].update(
            str(tag).strip()
            for tag, group in variant.get("tags", [])
            if str(group) == "画面风格" and str(tag).strip()
        )
EXPANDED_STYLE_KEYWORDS_BY_BASE = dict(EXPANDED_STYLE_KEYWORDS_BY_BASE)
