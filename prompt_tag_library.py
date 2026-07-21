# -*- coding: utf-8 -*-
"""
阶段式文生图提示词生成器标签库
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
import time
import unicodedata
from collections import OrderedDict
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from .danbooru_tag_config import (
        DANBOORU_GENERAL_TAG_ALIASES,
        DANBOORU_GENERAL_TAG_EXTENSIONS,
        DANBOORU_REFERENCE_SHEET_BACKGROUND_TAGS,
        DANBOORU_REFERENCE_SHEET_DYNAMIC_TAGS,
        DANBOORU_REFERENCE_SHEET_TAGS,
        DANBOORU_VISUAL_INTENT_FAMILIES,
    )
except ImportError:  # Direct module loading in focused tests.
    try:
        from danbooru_tag_config import (  # type: ignore
            DANBOORU_GENERAL_TAG_ALIASES,
            DANBOORU_GENERAL_TAG_EXTENSIONS,
            DANBOORU_REFERENCE_SHEET_BACKGROUND_TAGS,
            DANBOORU_REFERENCE_SHEET_DYNAMIC_TAGS,
            DANBOORU_REFERENCE_SHEET_TAGS,
            DANBOORU_VISUAL_INTENT_FAMILIES,
        )
    except ImportError:
        import importlib.util

        _danbooru_spec = importlib.util.spec_from_file_location(
            "danbooru_tag_config",
            Path(__file__).with_name("danbooru_tag_config.py"),
        )
        if _danbooru_spec is None or _danbooru_spec.loader is None:
            raise RuntimeError("Unable to load danbooru_tag_config.py")
        _danbooru_module = importlib.util.module_from_spec(_danbooru_spec)
        _danbooru_spec.loader.exec_module(_danbooru_module)
        DANBOORU_GENERAL_TAG_ALIASES = _danbooru_module.DANBOORU_GENERAL_TAG_ALIASES
        DANBOORU_GENERAL_TAG_EXTENSIONS = _danbooru_module.DANBOORU_GENERAL_TAG_EXTENSIONS
        DANBOORU_REFERENCE_SHEET_BACKGROUND_TAGS = _danbooru_module.DANBOORU_REFERENCE_SHEET_BACKGROUND_TAGS
        DANBOORU_REFERENCE_SHEET_DYNAMIC_TAGS = _danbooru_module.DANBOORU_REFERENCE_SHEET_DYNAMIC_TAGS
        DANBOORU_REFERENCE_SHEET_TAGS = _danbooru_module.DANBOORU_REFERENCE_SHEET_TAGS
        DANBOORU_VISUAL_INTENT_FAMILIES = _danbooru_module.DANBOORU_VISUAL_INTENT_FAMILIES


_快照文件路径 = Path(__file__).with_name("prompt_library_snapshot.json")
_自定义标签库文件路径 = Path(__file__).with_name("prompt_tag_library_custom.json")
_自定义标签分隔模式 = re.compile(r"[,\n\r\t;；，、]+")
_自定义标签非法分隔符模式 = re.compile(r"[\n\r\t,;；，、]")
_标签库缓存锁 = threading.RLock()
_标签库缓存签名: Any = object()
_标签库缓存自定义: OrderedDict[str, OrderedDict[str, list[str]]] | None = None
_标签库缓存合并: OrderedDict[str, OrderedDict[str, list[str]]] | None = None
_标签库缓存展平: dict[str, list[str]] | None = None
_标签库缓存推荐索引: tuple[tuple[str, str, tuple[str, ...], frozenset[str]], ...] | None = None
_标签库下次签名检查时间 = 0.0
_标签库无效文件签名: tuple[bool, int, int] | None = None
_标签库无效文件错误 = ""
_标签库签名检查间隔秒 = 0.25
_自定义标签库最大小类数 = 256
_自定义标签库最大小类标签数 = 500
_自定义标签库最大标签总数 = 5_000
_自定义标签库最大JSON字节 = 2 * 1024 * 1024
_自定义标签批量输入最大字符 = 32_768
_自定义标签库单小类最大扫描项 = 4 * _自定义标签库最大小类标签数
_标签分组默认槽位数 = 20
_标签分组槽位硬上限 = 32


def _读取快照() -> dict[str, Any]:
    if not _快照文件路径.exists():
        raise FileNotFoundError(f"未找到标签库快照：{_快照文件路径}")
    payload = json.loads(_快照文件路径.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _规范化分组配置(value: Any) -> list[dict[str, Any]]:
    """Normalize slot metadata once so every consumer shares the same capacity."""
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_group in value[:64]:
        if not isinstance(raw_group, dict):
            continue
        name = _规范化标签文本(raw_group.get("name", ""))
        if not name or name in seen:
            continue
        try:
            raw_slots = int(raw_group.get("slots", _标签分组默认槽位数))
        except (TypeError, ValueError):
            raw_slots = _标签分组默认槽位数
        group = deepcopy(raw_group)
        group["name"] = name
        group["slots"] = max(
            _标签分组默认槽位数,
            min(_标签分组槽位硬上限, max(1, raw_slots)),
        )
        group["tooltip"] = _规范化标签文本(group.get("tooltip", ""))
        result.append(group)
        seen.add(name)
    return result


def _转为有序结构(value: Any) -> Any:
    if isinstance(value, dict):
        return OrderedDict((str(key), _转为有序结构(item)) for key, item in value.items())
    if isinstance(value, list):
        return [_转为有序结构(item) for item in value]
    return value


def _空自定义标签库() -> OrderedDict[str, OrderedDict[str, list[str]]]:
    return OrderedDict((item["name"], OrderedDict()) for item in 分组配置)


def _规范化标签文本(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or "")).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _标签规范键(text: str) -> str:
    return _规范化标签文本(text).casefold()


def _extend_unique_list(items: list[str], additions: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in [*items, *additions]:
        text = _规范化标签文本(raw)
        if not text:
            continue
        key = _标签规范键(text)
        if key in seen:
            continue
        result.append(text)
        seen.add(key)
    return result


_内置标签补强包: dict[str, dict[str, list[str]]] = {
    "主体": {
        "脸型轮廓": [
            "鹅蛋脸",
            "瓜子脸",
            "圆脸",
            "方脸",
            "小巧下巴",
            "清晰下颌线",
            "高颧骨",
            "面部轮廓清晰",
            "脸部轮廓柔和",
        ],
        "五官细节": [
            "大眼睛",
            "杏眼",
            "丹凤眼",
            "高鼻梁",
            "小巧鼻尖",
            "鼻梁挺直",
            "鼻翼精致",
            "饱满嘴唇",
            "薄唇",
            "唇峰明显",
            "唇珠明显",
            "酒窝",
            "泪痣",
            "眉形清晰",
            "眉峰明显",
            "卧蚕明显",
            "眼尾上挑",
            "眼距适中",
            "眼型清晰",
        ],
        "表情眼神": [
            "浅笑",
            "微笑",
            "嘴角微扬",
            "笑不露齿",
            "冷眼凝视",
            "温柔注视",
            "迷离眼神",
            "倔强眼神",
            "若有所思",
            "回眸眼神",
            "平静神情",
            "欲感眼神",
            "坚定眼神",
            "凌厉眼神",
            "含情脉脉",
            "轻微皱眉",
            "眼神放空",
        ],
        "妆容特征": [
            "裸妆",
            "淡妆",
            "浓妆",
            "红唇",
            "烟熏妆",
            "冷艳妆",
            "元气妆",
            "清透底妆",
            "豆沙唇",
            "橘调唇妆",
            "雾面妆",
            "光泽唇",
            "裸色唇",
            "眼线清晰",
            "腮红自然",
            "腮红位置清晰",
            "眼影层次分明",
            "高光提亮",
            "修容自然",
        ],
        "发型长度": [
            "短发",
            "齐肩短发",
            "锁骨发",
            "中长发",
            "长发",
            "及腰长发",
            "超长发",
        ],
        "发型轮廓": [
            "波波头",
            "齐耳短发",
            "层次短发",
            "狼尾发",
            "微湿背头",
            "高马尾",
            "低马尾",
            "双马尾",
            "麻花辫",
            "双麻花辫",
            "羊毛卷",
            "短卷发",
            "长卷发",
            "姬发式",
            "公主切长发",
            "蓬松卷发",
            "大波浪长发",
            "自然直发",
            "微卷发",
            "凌乱发丝",
            "贴脸碎发",
        ],
        "刘海与分线": [
            "空气刘海",
            "齐刘海",
            "斜刘海",
            "八字刘海",
            "法式刘海",
            "龙须刘海",
            "眉上刘海",
            "无刘海",
            "中分",
            "侧分",
            "偏分",
            "露额发型",
        ],
        "发色": [
            "黑发",
            "棕发",
            "栗色头发",
            "金发",
            "银发",
            "白发",
            "灰发",
            "红发",
            "紫发",
            "青发",
            "茶棕发",
            "粉色头发",
            "蓝黑发",
            "挑染发",
            "渐变发色",
        ],
        "体态比例": [
            "肩颈线条清晰",
            "直角肩",
            "长颈",
            "窄腰",
            "长腿",
            "腿部修长",
            "腰臀曲线自然",
            "骨架轻盈",
            "肩宽适中",
            "锁骨明显",
            "头身比例自然",
            "姿态舒展",
        ],
        "非人主体": [
            "树灵巨像",
            "古木守卫",
            "藤蔓木妖",
        ],
    },
    "画面风格": {
        "现代摄影": [
            "城市屋顶纪实",
            "晚风纪实",
            "生活电影感",
            "古风电影剧照",
            "高端时尚编辑肖像",
        ],
        "奇幻史诗": [
            "巨构史诗奇观",
            "山谷史诗城邦",
            "史诗概念图",
            "宏大视觉开发图",
        ],
        "概念设计": [
            "电影概念图",
            "游戏角色展示",
            "关卡场景概念图",
            "角色设定图",
            "视觉开发稿",
            "高完成度3D角色展示",
        ],
        "科幻美学": [
            "义体美学",
        ],
    },
    "光影氛围": {
        "光线类型": [
            "日落逆光",
            "金色侧逆光",
            "冷色工业顶光",
            "冷蓝工业光",
            "展台背光",
            "冷蓝辅光",
        ],
        "色调氛围": [
            "饱满色彩",
        ],
        "自然情绪": [
            "晚风感",
            "空气流动感",
        ],
    },
    "构图视角": {
        "景别": [
            "巨物压迫近景",
        ],
        "镜头": [
            "超广角全景",
        ],
        "构图方式": [
            "中轴对称巨构",
        ],
        "人像构图控制": [
            "头肩像",
            "腰部以上构图",
            "膝上构图",
            "全身留白",
            "脚部完整入镜",
            "人物完整入镜",
            "脸部第一视觉中心",
            "面部作为第一视觉中心",
            "人物视觉重心更偏封面肖像",
            "上半身完整",
            "环境比例适中",
            "人物居中",
            "负空间留白",
            "纵向构图",
            "海报主视觉",
            "侧脸构图",
        ],
        "稳定镜头": [
            "眼平视角",
            "轻微俯拍",
            "轻微仰拍",
            "长焦压缩透视",
            "自然透视",
            "背景轻微虚化",
            "浅景深",
            "镜头近距离",
            "35mm镜头",
            "50mm标准镜头",
            "85mm人像镜头",
        ],
    },
    "动作姿态": {
        "手部动作": [
            "手扶栏杆",
            "双手插袋",
            "手拿包",
            "撩头发",
            "扶眼镜",
            "指尖触脸",
            "手撑桌面",
            "自然垂手",
            "手部姿态自然",
            "托腮",
            "托下巴",
            "单手扶腰",
            "双手抱臂",
            "轻触锁骨",
            "手持咖啡杯",
            "握手机",
            "轻抚衣角",
        ],
        "视线互动": [
            "看向镜头",
            "侧目看向远处",
            "低头凝视",
            "回头看向镜头",
            "闭眼感受光线",
            "视线越过镜头",
        ],
    },
    "服装造型": {
        "鞋履": [
            "运动鞋",
            "短靴",
            "长靴",
            "乐福鞋",
            "玛丽珍鞋",
            "尖头高跟鞋",
            "细跟高跟鞋",
            "绑带凉鞋",
            "厚底鞋",
        ],
        "面料材质": [
            "棉麻",
            "羊毛",
            "针织纹理",
            "雪纺",
            "缎面",
            "牛仔布",
            "磨砂皮革",
            "哑光金属配饰",
            "钛合金",
            "镀层金属",
            "真丝",
            "蕾丝",
            "针织开衫",
            "皮革",
            "透明薄纱",
            "天鹅绒",
            "棉质衬衫",
            "粗花呢",
        ],
        "穿搭结构": [
            "高腰线",
            "收腰剪裁",
            "宽松外套",
            "短上衣",
            "叠穿层次",
            "领口结构清晰",
            "袖口细节",
            "层叠领口",
            "露肩设计",
            "高领结构",
            "短外套",
            "长外套",
            "开衩设计",
            "轻薄罩衫",
            "深灰丝绒礼服",
        ],
        "配饰": [
            "耳环",
            "耳坠",
            "耳夹",
            "项链",
            "锁骨链",
            "戒指",
            "手表",
            "眼镜",
            "黑框眼镜",
            "太阳镜",
            "发夹",
            "发卡",
            "发簪",
            "发绳",
            "发圈",
            "发带",
            "发箍",
            "帽子",
            "贝雷帽",
            "棒球帽",
            "鸭舌帽",
            "墨镜",
            "珍珠耳环",
            "耳钉",
            "耳骨夹",
            "手链",
            "手镯",
            "胸针",
            "项圈",
            "围巾",
            "丝巾",
            "腰带",
            "手提包",
            "托特包",
            "斜挎包",
            "单肩包",
        ],
    },
    "场景背景": {
        "室外场景": [
            "瀑布峡谷",
            "远山雪峰",
        ],
        "特殊场景": [
            "山谷圣城",
            "巨构神殿",
        ],
        "室内锚点": [
            "窗边",
            "落地窗",
            "沙发",
            "床边",
            "化妆台",
            "镜前",
            "书架",
            "吧台",
            "试衣间",
            "楼梯间",
            "玄关",
            "走廊",
            "衣帽间",
            "厨房岛台",
            "浴室镜前",
        ],
        "城市锚点": [
            "街角",
            "人行横道",
            "便利店门口",
            "天台栏杆",
            "城市天台",
            "屋顶晾衣架",
            "电梯间",
            "停车楼",
            "玻璃橱窗",
            "玻璃幕墙",
            "街边傍晚",
        ],
        "现代场景": [
            "工业舱室",
            "工业展台",
            "实验室",
            "蓝色工业空间",
            "窗边室内",
            "街头纪实",
            "都市纪实",
        ],
    },
    "道具世界观": {
        "持物道具": [
            "相机",
            "单反相机",
            "摄影包",
            "手机",
            "咖啡杯",
            "书本",
            "雨伞",
            "笔记本",
            "耳机",
            "有线耳机",
            "随身听",
            "手提袋",
            "背包",
            "腰包",
        ],
        "世界观元素": [
            "史诗城市中轴",
            "山体建筑一体化",
        ],
    },
    "技术画质": {
        "人像稳定": [
            "面部清晰对焦",
            "双眼清晰",
            "手部结构自然",
            "发丝边缘清晰",
            "发丝迎风清晰",
            "侧脸轮廓清晰",
            "皮肤纹理自然",
            "服装边缘清晰",
            "无多余手指",
            "身体结构完整",
            "景深控制稳定",
            "焦点落在面部",
            "边缘干净",
            "背景不过分抢镜",
        ],
        "材质细节": [
            "朽木树皮纹理",
            "苔藓附生质感",
            "山体建筑细节密度",
            "发光裂隙",
            "材质细节丰富",
            "主材质统一",
        ],
    }
}


def _应用内置标签补强(library: OrderedDict[str, OrderedDict[str, list[str]]]) -> OrderedDict[str, OrderedDict[str, list[str]]]:
    result = deepcopy(library)
    for group_name, sections in _内置标签补强包.items():
        if group_name not in result:
            continue
        for section_name, additions in sections.items():
            current = list(result[group_name].get(section_name, []))
            result[group_name][section_name] = _extend_unique_list(current, additions)
    return result


def _构建内置标签库(merged_library: OrderedDict[str, OrderedDict[str, list[str]]], custom_library: OrderedDict[str, OrderedDict[str, list[str]]]) -> OrderedDict[str, OrderedDict[str, list[str]]]:
    base_library = deepcopy(merged_library)
    for group_name, sections in custom_library.items():
        if group_name not in base_library:
            continue
        for section_name, tags in sections.items():
            if section_name not in base_library[group_name]:
                continue
            custom_keys = {_标签规范键(tag) for tag in tags}
            kept = [tag for tag in base_library[group_name][section_name] if _标签规范键(tag) not in custom_keys]
            if kept:
                base_library[group_name][section_name] = kept
            else:
                del base_library[group_name][section_name]
    return _应用内置标签补强(base_library)


_快照 = _读取快照()

分组配置 = _规范化分组配置(_快照.get("slot_config", []))
自定义标签默认小类 = deepcopy(_快照.get("custom_tag_rules", {}).get("default_sections", {}))
自定义标签规则 = deepcopy(_快照.get("custom_tag_rules", {}))
自定义标签规则.setdefault("max_groups", len(分组配置))
自定义标签规则.setdefault("max_sections", _自定义标签库最大小类数)
自定义标签规则.setdefault("max_tags_per_section", _自定义标签库最大小类标签数)
自定义标签规则.setdefault("max_total_tags", _自定义标签库最大标签总数)
自定义标签规则.setdefault("max_json_bytes", _自定义标签库最大JSON字节)
自定义标签规则.setdefault("max_batch_input_chars", _自定义标签批量输入最大字符)

_快照当前标签库 = _转为有序结构(_快照.get("tag_library", {}))
_默认自定义标签库 = _转为有序结构(_快照.get("custom_tag_library", {}))
内置标签库 = _构建内置标签库(_快照当前标签库, _默认自定义标签库)

模板说明 = deepcopy(_快照.get("template_desc", {}))
模板骨架说明 = deepcopy(_快照.get("template_outline", {}))
模板参考示例 = deepcopy(_快照.get("template_reference", {}))
模板详细参考示例 = deepcopy(_快照.get("template_reference", {}))
模板说明.update(
    {
        "自动": "根据已选标签自动判断更接近写实、插画、CG、古风还是神话，并优先套用“风格锚点 -> 角色身份 -> 主服装与材质 -> 主场景与环境锚点 -> 光影 -> 镜头 -> 质感收束”的一致性写法。",
        "真实感": "按商业写真与杂志摄影逻辑组织：先确定年龄、身份、职业与气质，再落实五官、发型、主服装版型、面料、场景锚点、光线与镜头，让人物、服装和环境像同一次真实拍摄，而不是装饰元素拼贴。",
        "插画感": "按单幅叙事角色插画逻辑组织：先固定画风、年代与线条气质，再写角色身份、服装轮廓、主配色、手上主道具、环境层次与动作关系，让角色设计与背景属于同一作品世界。",
        "CG感": "按游戏 CG / 电影概念设计逻辑组织：先确定世界观、身份、装备或服装功能，再写空间尺度、材质分件、光线结构、机位和完成度；强调结构与功能，不把宝石或装饰件默认写成主角。",
        "古风": "按朝代服饰与东方场景统一系统组织：先定人物身份、时代气质和景别，再写发髻发饰、主服装层次、刺绣或织物、园林/宫殿/市井空间与东方光线，让古风细节真实可见、来源统一。",
        "神话感": "按神性身份与祭仪空间组织：先确定祭司、神女、神使或圣职者等身份，再写主服装、法器、祭坛、神殿、云海与敬畏镜头；装饰必须有宗教或叙事意义，不要退化成满身珠宝的普通棚拍。",
    }
)
模板骨架说明.update(
    {
        "自动": "建议按“判断模板主轴 -> 风格锚点 -> 角色身份/年龄/职业 -> 主服装版型与主面料 -> 主场景与环境锚点 -> 光影气氛 -> 动作与镜头 -> 画质收束”组织；单人默认一套主服装、一个主场景，双人多人要补清角色对应关系。",
        "真实感": "建议按“商业摄影风格锚点 -> 年龄/身份/职业 -> 五官、眼神、发型 -> 一套主服装的版型、覆盖关系与主面料 -> 场景锚点与前后景层次 -> 光线色调 -> 姿态手势 -> 景别/镜头/构图 -> 摄影质感与成片收束”组织。",
        "插画感": "建议按“画风与年代锚点 -> 线条、色块与印刷/颗粒气质 -> 角色身份与情绪 -> 服装轮廓、主配色与关键配饰 -> 手上主道具 -> 场景空间与前中后景 -> 动作关系 -> 镜头 -> 限制项/安全项”组织。",
        "CG感": "建议按“渲染风格与世界观 -> 身份与装备/服装功能 -> 结构分件与材质层级 -> 空间尺度与环境装置 -> 光线结构与特效克制 -> 动作与机位 -> 镜头语言 -> 高完成度收束”组织。",
        "古风": "建议按“景别与时代气质 -> 脸部神态与发髻 -> 发饰与主服装层次 -> 面料、刺绣、披帛与配色 -> 东方建筑/园林/山水空间 -> 柔光、纸窗天光或斑驳光影 -> 动作姿态 -> 发丝、织物与肌理收束”组织。",
        "神话感": "建议按“神性身份与仪式角色 -> 主服装、法器与材料重心 -> 神殿/云海/祭坛/圣所空间 -> 天光、体积光与敬畏镜头 -> 动作与视线 -> 能量、金属、织物等材质收束”组织，并明确哪些装饰是圣职符号、哪些只是辅助。",
    }
)
模板参考示例.update(
    {
        "自动": "先判断最合适的模板主轴，再把角色身份、主服装、主场景、光线、镜头、道具和质感写成一条清晰图像 brief，避免散装词堆叠、场景拼贴和装饰失控。",
        "真实感": "商业写真风格，成年东亚女性，清醒而克制的眼神，短发与自然发丝走向，一件结构清晰的灰黑挂脖上衣配不对称肩部装饰，室内极简空间里保留墙面、桌面与背景虚化层次，柔和窗边光压住面部与服装整体轮廓，全景全身，50mm标准镜头，布料纹理、皮肤质感与姿态比例清晰，干净完整成片边界。",
        "插画感": "90年代 OVA 手绘插画风，清晰角色轮廓与赛璐璐色块，年轻女冒险者，短外套与披风形成明确层次，左手握短杖右手拨开枝叶，森林步道与远处石阶构成前中后景，黄昏逆光穿过树叶，全景全身，标准镜头，大师构图，低保真颗粒与印刷网点克制存在。",
        "CG感": "电影级科幻 CG，女性战术特工立于机库通道，功能性护甲与长外套结构清晰，金属、皮革与织物分件明确，腰间装备与手中装置各有归属，机库立柱、地面反射与远处机械臂交代空间尺度，冷暖混合轮廓光，低角度中景，广角但不过度夸张，高完成度材质与工业细节。",
        "古风": "宋韵古风人像，成年东亚女子，温静神态与完整发髻，步摇与耳饰只作点缀，一套主服装由褙子、内搭与裙装构成，丝绸褶裥和刺绣边缘清晰，月洞门与园林回廊构成借景，纸窗天光与柔和侧光勾出面部、衣摆和姿态，全景全身，50mm标准镜头，真实发丝与织物肌理收束。",
        "神话感": "东方神话史诗，祭司身份的成年女性站在神殿祭坛前，主服装以丝绸长袍和少量金属圣饰构成，权杖作为唯一核心法器，祭坛台阶、立柱、云海与天穹开口明确交代空间，体积光自高处落下，人物与法器形成叙事闭环，广角仰视中景，材质神圣但克制，不写满身珠宝和无主漂浮碎片。",
    }
)
模板详细参考示例.update(
    {
        "自动": "先判断标签更接近摄影、插画、CG、古风还是神话，再把整条 prompt 写成稳定的图像 brief：明确角色身份与年龄、主服装版型与面料、主场景与环境锚点、动作视线、镜头构图、道具归属和约束；单人只保留一套主服装和一个主场景，双人多人要补足左右位、主次关系和道具对应。",
        "真实感": "商业写实人像，成年东亚女性，略带冷感但自然的眼神，短碎发带轻微空气感，面部保持清晰但不裁掉身体，一套结构明确的灰黑挂脖上衣配单侧雕塑感肩饰与金属链坠，服装重点落在版型、拼接、布料纹理和整体轮廓而不是珠宝密度，室内极简空间中保留背景墙面、桌角、柔焦家具和远处虚化层次，人物与环境都像同一次真实拍摄所得，柔和窗边光与补光共同塑造面部和身体比例，高光过渡柔和，全景全身，50mm标准镜头，浅景深但不抹掉环境逻辑，布料、皮肤、发丝和金属小件细节清晰，干净完整成片边界。",
        "插画感": "复古 OVA 叙事插画，先铺稳定的手绘线条、赛璐璐分色和轻微印刷颗粒，再写年轻冒险者的身份、神情和动作，一套主服装由短外套、披风和腰间装备组成，配色有明确主次，左手握短杖右手拨开前景枝叶，手势与道具关系闭合，森林步道、石阶、树影和远处遗迹形成清晰前中后景，黄昏逆光透过树冠，全景全身，标准镜头，画面重点放在角色设计、服装轮廓、道具用途和环境叙事，而不是散装华丽装饰。",
        "CG感": "高完成度科幻 CG，成年角色立于机库或都市工业空间，先写世界观与职业身份，再写一套功能性主服装或装备的结构分件、保护逻辑、主材质和连接关系，金属、皮革、织物和透明件要各自有位置与功能，胸针、项链或发饰只能少量点缀，不能替代服装本体，场景里要交代地面、立柱、机械臂、通道、光源和远处结构，让空间尺度成立，轮廓光、体积光和工业反射要服务主体，动作与手中装置、腰间装备、背负机构一一对应，低角度或广角可以有张力但不能把局部变形推成主角。",
        "古风": "东方古风详细长句，先确定朝代气质、身份和景别，再写五官神态、完整发髻、少量发饰与耳饰，一套主服装由外层、内搭、裙装和披帛构成，重点落在织物垂坠、褶裥、苏绣、纹样和配色秩序，不要把发饰珠宝写成主叙事，场景需明确到回廊、月洞门、纸窗、山石、水榭、竹影或庭院层次，光线采用纸窗天光、柔和侧光或斑驳日影，让面部与服装都清楚可读，动作、视线和手部姿态要自然服务气质，最后用发丝、织物和细腻肌理收束。",
        "神话感": "东方神话详细长句，先明确神女、祭司、神使或守护者等身份与仪式处境，再写一套主服装的结构、材质和圣职符号，让丝绸、金属和少量圣饰有明确主次，法器只保留一件核心圣物并写明握持或悬置关系，神殿、祭坛、云海、立柱、阶梯和天穹开口交代完整空间逻辑，体积光、逆光和敬畏镜头共同服务神性叙事，装饰和能量效果要有来源与归属，不要写成满身宝石、到处漂浮碎片、人物与法器无对应的廉价神女图。",
    }
)
模板专属规则 = {
    "真实感": "优先写真人摄影逻辑：身份、年龄、肤感、主服装单品、环境锚点、场景光线、镜头与成片质感都要具体；不要默认给每套衣服加宝石或奇幻装饰。",
    "插画感": "优先把画风前缀写完整，再补角色设定、服装轮廓、手上主道具与前中后景环境层次；地点要可辨认，道具和姿态要服务角色身份，不要把手绘风写成散装摄影词。",
    "CG感": "优先写渲染风格、装备或服装功能、空间尺度、体积光与材质完成度，整体要像游戏 CG 或电影概念设定；少量配饰可以有，但不能让宝石、透明片或胸口装饰压过结构本体。",
    "古风": "优先写景别、五官神态、发髻发饰、主服装层次、东方场景和柔和光影，保持古风细节真实可见；发饰与珠饰只作点睛，不要取代服装和气质主线。",
    "神话感": "优先写神性身份、法器、主服装、神殿云海或祭坛空间，再写圣辉、镜头敬畏感和神性材质细节；装饰必须有宗教或世界观意义，不能只是满身珠宝。",
    "自动": "先判断更接近写实、插画、CG、古风或神话，再用对应骨架组织清晰图像 brief，并优先保证人物、服装、场景与道具属于同一叙事系统。",
}
模板禁忌说明 = {
    "真实感": "避免只堆“高级感、氛围感、唯美”而没有服装、光线、场景和镜头支撑，也不要把写实人像默认写成神话珠宝棚拍、多人镜像复制或场景拼贴。",
    "插画感": "避免手绘、赛璐璐、OVA 与过多写实摄影词混写，避免让风格锚点前后冲突；不要只写空泛氛围词而不交代可辨认环境，也不要让道具漂浮、角色无归属或多人关系失焦。",
    "CG感": "避免只有史诗、震撼、大片这类空词，没有装备、空间、材质与镜头调度支撑；也避免把 CG 角色写成浑身宝石片、透明装饰和无因果漂浮物的拼贴。",
    "古风": "避免只写古风、仙气、国风这种泛词而不写发髻、服装层次、配色、场景和材质；也避免现代服装、现代空间和古风身份硬拼。",
    "神话感": "避免只写神圣、空灵、史诗，不写法器、祭坛、神殿、云海与光影结构，最后变成普通古风人像；也避免把神性主体写成满身珠宝和装饰件的无主堆叠。",
    "自动": "避免风格摇摆、标签散装堆砌和人物服装场景各说各话，尽量让主体、服装、场景、道具、光影和镜头保持同一叙事轨道。",
}

快速推荐组合 = _转为有序结构(_快照.get("quick_presets", {}))
快速推荐元数据 = _转为有序结构(_快照.get("quick_preset_meta", {}))
快速推荐分组 = _转为有序结构(_快照.get("quick_preset_groups", {}))
快速推荐档位顺序 = tuple(_快照.get("quick_preset_tier_order", []))
快速推荐档位索引 = _转为有序结构(_快照.get("quick_preset_tiers", {}))
快速推荐分组档位索引 = _转为有序结构(_快照.get("quick_preset_group_tiers", {}))
快速推荐用途顺序 = tuple(_快照.get("quick_preset_use_case_order", []))
快速推荐用途索引 = _转为有序结构(_快照.get("quick_preset_use_cases", {}))
快速推荐分组用途索引 = _转为有序结构(_快照.get("quick_preset_group_use_cases", {}))
快速推荐分组用途映射 = OrderedDict((group, list(section_map.keys())) for group, section_map in 快速推荐分组用途索引.items())
快速推荐搜索别名映射 = OrderedDict(
    {
        "人像": ["写真", "肖像", "portrait"],
        "场景": ["环境", "建筑", "奇观", "landscape", "scene"],
        "巨物": ["怪兽", "妖兽", "巨像", "kaiju", "colossal", "beast"],
        "成人": ["私房", "adult", "nsfw"],
        "古风": ["国风", "武侠", "oriental"],
        "神话": ["史诗", "祭司", "myth"],
        "CG科幻": ["科幻", "赛博", "插画", "cg", "scifi"],
        "职业": ["职业角色", "纪实", "role"],
        "女性向": ["女生", "女像", "female"],
        "男性向": ["男像", "男性", "male"],
        "低遮挡": ["轮廓", "开放感", "low-cover"],
        "电影感": ["cinematic", "film", "movie"],
        "道具叙事": ["持物", "武器", "法器", "prop"],
        "测试": ["调试", "随机", "test"],
    }
)
快速推荐目录分组顺序 = ("写实", "私房", "男性", "场景", "巨物", "扩展")
快速推荐稳定家族目录 = OrderedDict(
    (
        ("写实", ["海边轻熟写实"]),
        ("私房", ["落地窗轻私房", "浴缸蒸汽私房"]),
        ("男性", ["夜色男性私房"]),
    )
)
快速推荐变体顺序 = OrderedDict((("标准", 0), ("近景", 1), ("全身", 2)))
快速推荐稳定家族说明映射 = {
    "海边轻熟写实": {
        "summary": "偏成熟写实的海边礼服人像，整体更克制，适合先跑稳定成片气质。",
        "recommended_for": ["海边黄昏写实", "礼服女性人像", "想先看稳定成片"],
    },
    "落地窗轻私房": {
        "summary": "卧室落地窗夜景私房，主打柔光、微醺感和丝质睡袍氛围。",
        "recommended_for": ["卧室夜景私房", "柔光女性半身", "想要微醺氛围"],
    },
    "浴缸蒸汽私房": {
        "summary": "浴后蒸汽私房，强调湿发、浴巾裹身和暖色雾气环境。",
        "recommended_for": ["浴后蒸汽氛围", "暖色浴室私房", "想要湿发状态"],
    },
    "夜色男性私房": {
        "summary": "夜景男性私房，重点是背头、侧光轮廓和丝质睡袍的气场。",
        "recommended_for": ["男性夜景私房", "侧光轮廓男像", "想要背头气质"],
    },
}
快速推荐变体选择建议映射 = {
    "标准": "先用这条确认家族风格、服装和空间关系是否对路。",
    "近景": "想优先看脸部、发型和上半身完成度时选它。",
    "全身": "想先看姿态、轮廓和环境比例时选它。",
}
快速推荐稳定家族分组索引: dict[str, str] = {}
快速推荐稳定家族顺序索引: dict[str, tuple[int, int]] = {}
for _group_order, (_catalog_group, _families) in enumerate(快速推荐稳定家族目录.items()):
    for _family_order, _family_name in enumerate(_families):
        快速推荐稳定家族分组索引[_family_name] = _catalog_group
        快速推荐稳定家族顺序索引[_family_name] = (_group_order, _family_order)


def _拆分快速推荐家族与变体(name: str) -> tuple[str, str]:
    preset_name = _规范化标签文本(name)
    if "·" not in preset_name:
        return preset_name, "标准"
    family_name, variant_name = preset_name.split("·", 1)
    variant_label = _规范化标签文本(variant_name) or "标准"
    return _规范化标签文本(family_name), variant_label


def _首个命中标签(tags: list[str], candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate in tags:
            return candidate
    return ""


def _构建快速推荐适配主体(tags: list[str], group: str) -> list[str]:
    if group == "场景史诗":
        return ["场景奇观"]
    if group == "巨物妖兽":
        subject = _首个命中标签(tags, ["树灵巨像", "古木守卫", "藤蔓木妖"])
        return [f"{subject}主体"] if subject else ["巨物主体"]
    if "成年女性" in tags:
        if group == "成人私房":
            return ["女性成人人像"]
        if group == "古风神话":
            return ["女性角色"]
        return ["女性人像"]
    if "成年男性" in tags:
        if group == "职业题材":
            return ["男性职业人像"]
        if group == "成人私房":
            return ["男性成人人像"]
        return ["男性人像"]
    special = _首个命中标签(tags, ["神女", "祭司", "骑士", "剑客", "律师", "机修师", "调酒师", "乐队主唱", "机械师", "特工", "战斗修女", "女冒险者", "机甲", "树灵巨像", "古木守卫", "藤蔓木妖"])
    if special == "机甲":
        return ["机甲主体"]
    if special:
        return [f"{special}角色"]
    return [f"{group}方向"]


def _构建快速推荐适配画面(tags: list[str], group: str) -> list[str]:
    if group == "场景史诗":
        scene = _首个命中标签(tags, ["山谷圣城", "巨构神殿", "瀑布峡谷", "远山雪峰", "史诗城市中轴"])
        return [f"{scene}场景"] if scene else ["史诗场景"]
    if group == "巨物妖兽":
        scene = _首个命中标签(tags, ["工业舱室", "古木森林", "废墟", "峡谷"])
        return [f"{scene}巨物画面"] if scene else ["巨物压迫画面"]
    if "落地窗夜景" in tags:
        if "卧室" in tags:
            return ["卧室落地窗夜景"]
        return ["落地窗夜景"]
    if "浴缸" in tags or "温泉雾气" in tags:
        return ["浴后蒸汽浴室"]
    scene = _首个命中标签(tags, ["窗边光", "海边", "海岸线", "花房温室", "花海", "雨后街头", "霓虹雨夜", "湖畔", "云海", "神殿", "宫殿", "月下庭院", "机库", "未来都市", "蒸汽都市", "酒吧", "白色背景", "维修车间", "摄影棚", "书房", "山谷圣城", "巨构神殿", "工业舱室", "城市天台"])
    if scene == "窗边光":
        return ["窗边自然光"]
    if scene == "白色背景":
        return ["白底轮廓画面"]
    if scene:
        return [f"{scene}场景"]
    if group == "CG科幻":
        return ["设定感场景"]
    return [f"{group}画面"]


def _构建快速推荐适配目标(tags: list[str], use_cases: list[str], group: str, variant_label: str, *, stable_variant: bool) -> list[str]:
    if "低遮挡" in use_cases:
        return ["先看轮廓表达"]
    if stable_variant and variant_label in 快速推荐变体选择建议映射:
        if variant_label == "标准":
            return ["先看整体方向"]
        if variant_label == "近景":
            return ["先看脸和上半身"]
        if variant_label == "全身":
            return ["先看姿态和比例"]
    if group == "人像写真":
        return ["先看气质成片"]
    if group == "古风神话":
        return ["先看世界观和服饰"]
    if group == "CG科幻":
        return ["先看设定完成度"]
    if group == "场景史诗":
        return ["先看空间奇观"]
    if group == "巨物妖兽":
        return ["先看巨物比例"]
    if group == "职业题材":
        return ["先看身份是否成立"]
    if group == "成人私房":
        return ["先看空间和边界"]
    return ["先看核心锚点"]


def _构建快速推荐扩展摘要(name: str, tags: list[str], use_cases: list[str], group: str, tier: str) -> str:
    subject = _首个命中标签(
        tags,
        [
            "成年女性",
            "成年男性",
            "树灵巨像",
            "古木守卫",
            "藤蔓木妖",
            "神女",
            "祭司",
            "骑士",
            "剑客",
            "律师",
            "机修师",
            "调酒师",
            "乐队主唱",
            "机械师",
            "特工",
            "战斗修女",
            "女冒险者",
            "机甲",
        ],
    )
    scene = _首个命中标签(
        tags,
        [
            "窗边光",
            "书房",
            "维修车间",
            "摄影棚",
            "海边",
            "海岸线",
            "花房温室",
            "花海",
            "雨后街头",
            "霓虹雨夜",
            "湖畔",
            "云海",
            "神殿",
            "宫殿",
            "月下庭院",
            "机库",
            "未来都市",
            "蒸汽都市",
            "酒吧",
            "白色背景",
            "浴缸",
            "山谷圣城",
            "巨构神殿",
            "瀑布峡谷",
            "工业舱室",
            "城市天台",
        ],
    )
    style = _首个命中标签(
        tags,
        [
            "日系",
            "糖水片",
            "高智感",
            "北欧冷感",
            "街拍",
            "中画幅",
            "国潮",
            "古风",
            "神话感",
            "CG感",
            "插画感",
            "OVA风",
            "巴洛克",
            "私房写真",
            "巨构史诗奇观",
            "游戏CG质感",
        ],
    )
    prop = _首个命中标签(
        tags,
        [
            "眼镜",
            "花束",
            "伞",
            "扇",
            "法杖",
            "法器",
            "权杖",
            "枪",
            "宝剑",
            "能量刀",
            "古琴",
        ],
    )

    if group == "场景史诗":
        focus = "、".join([item for item in [scene or "山谷圣城", style or "神话感", "空间奇观"] if item][:3])
        return f"偏{focus}的场景史诗模板，适合先确认空间尺度、建筑层次和光线主轴。"
    if group == "巨物妖兽":
        focus = "、".join([item for item in [subject or "巨物主体", scene or "工业舱室", style or "CG感"] if item][:3])
        return f"偏{focus}的巨物/妖兽模板，适合先看主体体量、材质和环境压迫感。"
    if group == "人像写真":
        focus = "、".join([item for item in [style or "真实感", scene, subject, prop] if item][:3])
        return f"偏{focus}的人像模板，适合先看人物气质、景别和成片方向是否成立。"
    if group == "古风神话":
        focus = "、".join([item for item in [style or "古风", subject, scene, prop] if item][:3])
        return f"偏{focus}的古风/神话叙事模板，适合先确认世界观、服装和道具主线。"
    if group == "CG科幻":
        focus = "、".join([item for item in [style or "CG科幻", subject, scene, prop] if item][:3])
        return f"偏{focus}的科幻设定模板，适合先看世界观锚点和装备完成度。"
    if group == "职业题材":
        focus = "、".join([item for item in [subject, scene, style or "真实感"] if item][:3])
        return f"偏{focus}的职业人物模板，适合先看身份是否成立，再细调服装和镜头。"
    if group == "成人私房":
        focus = "、".join([item for item in [subject, scene, style or "私房写真"] if item][:3])
        return f"偏{focus}的成人向扩展模板，适合先确认空间、轮廓和表达边界。"

    use_preview = " / ".join(_extend_unique_list([], use_cases)[:2])
    tag_preview = "、".join(_extend_unique_list([], tags)[:4])
    summary = f"{group}向{tier}预设"
    if use_preview:
        summary += f"，适合 {use_preview}"
    if tag_preview:
        summary += f"；核心锚点：{tag_preview}"
    return summary


def _构建快速推荐适用场景(tags: list[str], use_cases: list[str], group: str) -> list[str]:
    scene = _首个命中标签(
        tags,
        [
            "窗边光",
            "书房",
            "维修车间",
            "摄影棚",
            "海边",
            "海岸线",
            "花房温室",
            "花海",
            "雨后街头",
            "霓虹雨夜",
            "湖畔",
            "云海",
            "神殿",
            "宫殿",
            "月下庭院",
            "机库",
            "未来都市",
            "蒸汽都市",
            "酒吧",
            "白色背景",
            "浴缸",
            "山谷圣城",
            "巨构神殿",
            "瀑布峡谷",
            "工业舱室",
            "城市天台",
        ],
    )
    style = _首个命中标签(
        tags,
        [
            "日系",
            "糖水片",
            "高智感",
            "北欧冷感",
            "街拍",
            "中画幅",
            "国潮",
            "古风",
            "神话感",
            "CG感",
            "插画感",
            "OVA风",
            "巴洛克",
            "私房写真",
            "巨构史诗奇观",
            "游戏CG质感",
        ],
    )
    subject = _首个命中标签(
        tags,
        [
            "成年女性",
            "成年男性",
            "树灵巨像",
            "古木守卫",
            "藤蔓木妖",
            "神女",
            "祭司",
            "骑士",
            "剑客",
            "律师",
            "机修师",
            "调酒师",
            "乐队主唱",
            "机械师",
            "特工",
            "战斗修女",
            "女冒险者",
            "机甲",
        ],
    )
    scene_hint = f"{scene}场景" if scene else ""
    style_hint = f"{style}方向" if style else ""
    subject_hint = f"{subject}主体" if subject else ""
    if group == "场景史诗":
        subject_hint = "非人像场景奇观"
    if group == "巨物妖兽":
        subject_hint = f"{subject}巨物主体" if subject else "巨物主体"
    if group == "职业题材":
        subject_hint = f"{subject}职业人像" if subject else subject_hint
    return _extend_unique_list([], [scene_hint, style_hint, subject_hint, *_extend_unique_list([], use_cases)[:2]])


def _构建快速推荐选择建议(tags: list[str], use_cases: list[str], group: str, tier: str) -> str:
    if "低遮挡" in use_cases:
        return "先确认轮廓表达和遮挡边界，再决定是否继续加服装、场景或镜头细节。"
    if group == "人像写真":
        return "先看人物气质和镜头距离是否顺眼，再细调服装、光线和地域感。"
    if group == "古风神话":
        return "先确认世界观和服饰锚点是否成立，不够稳时优先补场景和道具。"
    if group == "CG科幻":
        return "先看设定感和装备是否成立，不够强时优先补世界观和光效词。"
    if group == "场景史诗":
        return "先确认空间尺度、建筑层级和主光方向，避免误跑成人像或小场景。"
    if group == "巨物妖兽":
        return "先确认巨物体量、材质纹理和环境压迫感，再决定是否加角色对比。"
    if group == "职业题材":
        return "先确认身份和工作场景是否对路，再决定要不要继续加成片风格。"
    if tier == "强风格":
        return "想先把风格锚点拉满时用它，不适合拿来做最泛用的起手模板。"
    if tier == "高完成度":
        return "想直接看信息更密、完成度更高的成片方向时优先选它。"
    return "想先用一个更稳妥的方向起手时选它。"


def _推断快速推荐展示元数据(name: str, tags: list[str], use_cases: list[str], group: str, tier: str) -> dict[str, Any]:
    preset_name = _规范化标签文本(name)
    family_name, variant_label = _拆分快速推荐家族与变体(preset_name)
    stable_info = 快速推荐稳定家族说明映射.get(family_name)
    is_stable_variant = stable_info is not None
    fit_subject = _构建快速推荐适配主体(tags, group)
    fit_scene = _构建快速推荐适配画面(tags, group)
    fit_goal = _构建快速推荐适配目标(tags, use_cases, group, variant_label, stable_variant=is_stable_variant)
    if stable_info is not None:
        return {
            "preset_summary": str(stable_info.get("summary", "")).strip(),
            "recommended_for": _extend_unique_list([], list(stable_info.get("recommended_for", []))),
            "selection_tip": str(快速推荐变体选择建议映射.get(variant_label, "")).strip(),
            "fit_subject": fit_subject,
            "fit_scene": fit_scene,
            "fit_goal": fit_goal,
        }

    return {
        "preset_summary": _构建快速推荐扩展摘要(preset_name, tags, use_cases, group, tier),
        "recommended_for": _构建快速推荐适用场景(tags, use_cases, group)[:3],
        "selection_tip": _构建快速推荐选择建议(tags, use_cases, group, tier),
        "fit_subject": fit_subject,
        "fit_scene": fit_scene,
        "fit_goal": fit_goal,
    }


def _推断快速推荐目录元数据(name: str, tags: list[str], use_cases: list[str], group: str = "", tier: str = "") -> dict[str, Any]:
    preset_name = _规范化标签文本(name)
    family_name, variant_label = _拆分快速推荐家族与变体(preset_name)
    stable_group = 快速推荐稳定家族分组索引.get(family_name)
    stable_order = 快速推荐稳定家族顺序索引.get(family_name)
    use_case_set = set(use_cases or [])
    tag_set = set(tags or [])
    if stable_group:
        catalog_group = stable_group
    elif group == "场景史诗" or "场景" in use_case_set or tag_set & {"山谷圣城", "巨构神殿", "瀑布峡谷", "远山雪峰", "史诗城市中轴"}:
        catalog_group = "场景"
    elif group == "巨物妖兽" or "巨物" in use_case_set or tag_set & {"树灵巨像", "古木守卫", "藤蔓木妖", "巨物压迫近景"}:
        catalog_group = "巨物"
    else:
        catalog_group = "扩展"
    catalog_group_order = stable_order[0] if stable_order is not None else 快速推荐目录分组顺序.index(catalog_group) if catalog_group in 快速推荐目录分组顺序 else len(快速推荐目录分组顺序) - 1
    family_order = stable_order[1] if stable_order is not None else 999
    variant_order = int(快速推荐变体顺序.get(variant_label, len(快速推荐变体顺序)))
    return {
        "catalog_group": catalog_group,
        "catalog_group_order": catalog_group_order,
        "catalog_family": family_name,
        "catalog_family_order": family_order,
        "catalog_variant": variant_label,
        "catalog_variant_order": variant_order,
        "is_stable_variant": bool(stable_group),
        "is_male_variant": catalog_group == "男性",
        "catalog_search_keywords": _extend_unique_list(
            [catalog_group, family_name, variant_label, preset_name],
            [str(item) for item in use_cases] + [str(item) for item in tags],
        ),
        **_推断快速推荐展示元数据(preset_name, tags, use_cases, group or catalog_group, tier or ""),
    }

快速推荐强风格标签集合 = {
    "古风",
    "神话感",
    "CG感",
    "插画感",
    "OVA风",
    "赛博朋克",
    "巴洛克",
    "蒸汽都市",
    "霓虹都市",
    "未来都市",
    "异世界",
    "水墨",
    "油画",
    "神殿",
    "云海",
}
快速推荐高完成度标签集合 = {
    "体积光",
    "商业广告大片",
    "电影剧照",
    "电影调色",
    "珠宝细节",
    "神圣祭坛",
    "云端阶梯",
    "法阵",
    "权杖",
    "法杖",
    "宝剑",
    "枪",
    "身体轮廓清晰",
    "遮挡最小化",
    "无遮挡感",
}
快速推荐女性向标签集合 = {
    "少女",
    "成年女性",
    "中年女性",
    "OL",
    "神女",
    "仙子",
    "魔女",
    "公主",
    "女王",
    "战斗修女",
    "女冒险者",
}
快速推荐男性向标签集合 = {
    "少年",
    "成年男性",
    "中年男性",
    "皇子",
    "帝王",
    "骑士",
    "剑客",
    "特工",
    "律师",
    "机修师",
    "机械师",
    "调酒师",
    "乐队主唱",
}
快速推荐低遮挡标签集合 = {"遮挡最小化", "无遮挡感", "少遮挡", "弱遮挡", "身体轮廓清晰"}
快速推荐电影感标签集合 = {"电影剧照", "电影调色", "商业广告大片", "胶片感"}
快速推荐道具叙事标签集合 = {
    "花束",
    "酒杯",
    "乐器",
    "卷轴",
    "灯笼",
    "面具",
    "扇",
    "伞",
    "武器",
    "剑",
    "宝剑",
    "刀",
    "枪",
    "弓",
    "盾",
    "长矛",
    "权杖",
    "法器",
    "法杖",
}

模板推断关键词 = {
    "插画感": {
        "插画感",
        "插画",
        "手绘画风",
        "OVA风",
        "复古动画",
        "怀旧动画",
        "赛璐璐",
        "吉卜力风",
        "Moebius风",
        "金政基风",
        "线条感",
        "饱满色彩",
        "低保真",
        "印刷网点",
    },
    "神话感": {
        "神话感",
        "神女",
        "神圣",
        "女王",
        "帝王",
        "史诗感",
        "战场",
        "异世界",
        "魔法森林",
        "云海",
        "星空",
        "未来都市",
    },
    "古风": {
        "古风",
        "汉服",
        "旗袍",
        "唐装",
        "宋制",
        "明制",
        "魏晋",
        "仙侠",
        "武侠",
        "宫廷",
        "古风建筑",
        "国潮",
        "国风美学",
        "异域风情",
        "水墨",
        "剑客",
        "神女",
        "皇子",
        "帝王",
    },
    "CG感": {
        "CG感",
        "3D渲染",
        "虚幻引擎",
        "Octane渲染",
        "游戏风",
        "赛博朋克",
        "未来感",
        "未来都市",
        "霓虹都市",
        "体积光",
        "辉光",
        "机甲",
        "工程机甲",
        "侦查机甲",
        "防御机甲",
        "机器人",
        "飞船",
        "战舰",
    },
    "真实感": {
        "真实感",
        "照片级",
        "胶片感",
        "CCD感",
        "手机抓拍",
        "纪实抓拍",
        "街拍",
        "写真",
        "纪实",
        "自然光",
        "电影感",
        "raw photo",
        "无滤镜直出",
        "私房写真",
        "糖水片",
        "时尚写真",
        "杂志感",
        "OOTD",
    },
}


def _extend_library_section(group: str, section: str, additions: list[str]) -> None:
    for library in (内置标签库,):
        if group not in library:
            library[group] = OrderedDict()
        if section not in library[group]:
            library[group][section] = []
        library[group][section] = _extend_unique_list(library[group][section], additions)


_四向扩展标签 = {
    ("主体", "特殊身份"): ["双人", "影棚时尚女性", "书店女孩", "居家游戏女孩", "湖畔金发女性", "神圣骑士", "冰霜骑士", "炎魔天使", "女武士"],
    ("画面风格", "写实风格"): ["中画幅", "街头纪实", "都市纪实", "街拍摄影", "Lookbook", "影棚人像", "品牌大片", "生活方式广告", "电影剧照感", "35mm胶片摄影", "大画幅棚拍", "大片级棚拍", "纪实电影摄影", "港式武侠胶片", "雾景实拍感", "写实真人质感", "复古颗粒", "日韩影像", "日系电影感", "韩系极简影像", "生活流写实", "港风恐怖电影调"],
    ("画面风格", "艺术风格"): ["水粉插画", "墨洗留白", "木刻版画", "平面矢量"],
    ("画面风格", "美学风格"): [
        "机能赛博",
        "宋韵美学",
        "志怪古风",
        "园林仕女",
        "东方神话史诗",
        "敦煌神性",
        "神庙壁画感",
        "圣像画神性",
        "单幅叙事角色插画",
        "叙事插画",
        "动画电影截图感",
        "单幅角色插画",
        "电影感单幅画面",
        "单人角色渲染",
        "关卡空间单幅画面",
        "高完成度单人角色渲染",
        "国风人像",
        "古装剧照感",
        "园林人像",
        "工笔插画感",
        "武侠剧照感",
        "史诗感单幅画面",
        "神性肖像",
        "祭仪场景",
        "宏大单幅神话场景",
        "包豪斯几何",
        "新艺术曲线",
        "世纪中叶现代",
        "粗野主义",
        "太阳朋克",
        "蒸汽波美学",
        "北欧极简",
        "巴洛克繁饰",
        "浮世绘",
        "港式武侠",
        "古风电影氛围",
        "东方赛博机甲",
        "东方古风武侠",
        "东方赛博武侠朋克",
        "都市电影人文",
        "时尚编辑商业广告",
        "西方奇幻史诗",
        "港风惊悚志怪",
        "日韩影像",
        "敦煌神性",
        "BJD娃娃质感",
    ],
    ("光影氛围", "光线类型"): ["阴天自然光", "钨丝灯实景光", "全息投影光", "广告屏反射光", "廊下斑驳光", "纸窗天光", "穹顶天光", "云隙光", "圣辉逆光", "黄金时刻侧光", "阴天柔散光", "黑色电影硬光", "暖色轮廓逆光", "烛火暖光", "冷荧顶光", "叶隙斑驳光", "体积神光", "蓝灰月光", "红雾表现主义打光", "冷雾惊悚侧光", "冷灰极简棚光", "高窗冷天光"],
    ("光影氛围", "色调氛围"): ["蓝洋红对撞", "金雾神光", "高调粉彩", "低饱和冷灰", "暖褐单色", "酸性霓虹黑", "宝石色调", "双双色调", "晒褪色调", "墨黑单色点缀", "青橙电影色调", "青蓝冷雾", "暖褪色胶片", "冷灰极简", "暗绿褐胶片", "冷白极简棚拍"],
    ("构图视角", "镜头"): ["28mm镜头", "135mm长焦", "变形宽银幕", "微距特写", "200mm长焦压缩"],
    ("构图视角", "构图方式"): ["卷轴式构图", "门框借景", "监控视角", "HUD视角", "祭坛对称构图", "神像式正立", "俯视平铺", "荷兰式倾斜", "过肩镜头"],
    ("动作姿态", "姿态语义"): ["并肩", "对视", "双人互动"],
    ("动作姿态", "手部动作"): ["手持相机"],
    ("服装造型", "古风细分"): ["宋韵美学", "志怪古风", "园林仕女", "褙子", "诃子裙", "比甲", "鹤氅"],
    ("服装造型", "特殊元素"): ["云肩", "绒花", "义体接口", "发光面料", "神官长袍", "鎏金头冠", "流光薄纱", "羽饰肩甲", "白色斗篷", "黑金重甲", "银白雕花重甲"],
    ("服装造型", "配饰"): ["玉佩", "香囊"],
    ("场景背景", "室内场景"): ["精品酒店", "无缝影棚", "茶寮", "数据机房", "神像殿堂", "影棚纯色背景", "独立书店", "图书馆"],
    ("场景背景", "特殊场景"): ["天穹祭坛", "月洞门", "水榭", "断柱遗迹", "星海神殿", "悬空神庙", "黑铁王座", "火山洞穴", "冰冻森林", "北欧海岸", "云端阶梯", "古建道场"],
    ("场景背景", "氛围场景"): ["广告屏街谷", "高架贫民区", "赛博地铁", "云上神国", "幽暗竹林", "废弃地下老屋", "都市便利店", "雨夜站台", "极简白棚", "韩系公寓走廊", "冷雾古巷", "霓虹街区"],
    ("场景背景", "室外场景"): ["雨后街头", "工业废墟"],
    ("道具世界观", "持物道具"): ["古琴"],
    ("道具世界观", "武器法器"): ["能量刀", "光刃", "日轮", "月轮"],
    ("道具世界观", "世界观元素"): ["全息界面", "云上神国", "天穹祭坛", "断柱遗迹", "星海神殿", "悬空神庙", "神谕石碑", "圣火"],
    ("技术画质", "画质描述"): ["中画幅质感", "广告成片质感", "神话壁画质感", "写实真人质感", "复古颗粒", "BJD娃娃质感", "雾景实拍感", "日系影像质感", "韩系广告质感", "电影胶片look", "游戏CG质感", "老胶片褪色感", "港片胶片质感"],
    ("技术画质", "特效"): ["全息投影", "电子噪辉", "神性尘辉", "RGB轻微分离", "轻微色差", "柔和光晕"],
    ("技术画质", "摄影质感"): ["复古非镀膜镜头"],
    ("技术画质", "材质"): ["义体金属细节", "神性皮肤光泽", "宝石能量晕光", "石像风化纹理", "服装褶皱真实", "丝绸褶裥清晰", "发髻结构完整", "肤色校正自然", "哑光陶瓷", "拉丝铝材", "风化木纹", "手吹玻璃", "粗粝混凝土", "旧皮革", "湿沥青反光", "磨砂亚克力", "锤纹黄铜", "亚麻织纹"],
}

for (_group, _section), _tags in _四向扩展标签.items():
    _extend_library_section(_group, _section, _tags)


# Natural environments are kept in focused sections so the browser can expose
# useful choices without mixing locations, weather, light, and composition.
_自然风光光影扩展标签 = {
    ("光影氛围", "光线类型"): [
        "丁达尔光效", "丁达尔光束", "森林丁达尔光", "峡谷丁达尔光", "窗缝丁达尔光",
        "雾中体积光柱", "林间穿透光", "树冠漏光", "云层破隙光", "雨幕后透光",
        "晨雾侧逆光", "雪地反射光", "水面波光反射", "洞穴入口天光", "瀑布水雾散射光",
        "日出低角度光", "落日余晖侧光", "月光穿云", "星光环境光", "极光漫反射",
        "雷暴云边缘光", "沙尘体积光", "海面粼光", "冰川蓝色透射光", "湿地晨光",
        "高原强日照", "阴云层次光", "远山轮廓光", "林下冷暖斑驳光", "逆光草穗",
    ],
    ("光影氛围", "大气光学"): [
        "可见光束", "空气透视", "大气散射", "瑞利散射蓝调", "米氏散射金雾",
        "云海光瀑", "雾虹", "日晕", "月晕", "幻日",
        "耶稣光", "海雾光墙", "雨雾光幕", "尘埃光路", "花粉浮尘光",
        "冰晶光柱", "暮光带", "反暮光", "山影投云", "云隙光扇",
        "水下焦散光纹", "浅水折射光", "薄雾层次", "远景蓝雾", "逆光水汽颗粒",
    ],
    ("光影氛围", "天气氛围"): [
        "晴空通透", "多云间晴", "阴天柔散", "暴雨将至", "雷雨过境",
        "阵雨光斑", "细雨薄雾", "雨后初晴", "晨露湿润", "海风低云",
        "山谷云雾", "高原卷云", "沙尘天气", "风雪弥漫", "初雪静谧",
        "冰雾天气", "热浪扭曲", "潮湿闷热", "台风前夕", "彩虹雨幕",
        "云瀑翻涌", "雾锁江面", "霜晨空气", "秋风卷叶", "春雨新绿",
    ],
    ("光影氛围", "时间氛围"): [
        "黎明前蓝调", "破晓微光", "日出金边", "清晨薄雾", "上午通透天光",
        "正午硬朗日光", "午后斜射光", "傍晚长影", "黄金时刻", "日落后余辉",
        "蓝调时刻", "暮色渐沉", "新月夜色", "满月夜色", "无月星空",
        "银河夜空", "极昼低阳", "极夜蓝光", "雨夜路面反光", "雪夜环境反光",
    ],
    ("场景背景", "山地地貌"): [
        "层叠远山", "云雾山脉", "雪山主峰", "高原山谷", "喀斯特峰林",
        "丹霞地貌", "花岗岩山脊", "火山口湖", "熔岩原野", "峡谷栈道",
        "深切河谷", "悬崖海岬", "山间盆地", "高山草甸", "山口风场",
        "盘山公路", "山寺远景", "梯田山坡", "石林地貌", "丘陵茶园",
        "云海山巅", "雪线营地", "冰斗湖", "山谷村落", "荒山古道",
    ],
    ("场景背景", "水域海岸"): [
        "镜面湖泊", "高山湖泊", "湿地湖湾", "蜿蜒河流", "江河峡谷",
        "河口三角洲", "芦苇浅滩", "红树林潮沟", "岩石海岸", "白沙海滩",
        "黑沙海滩", "珊瑚海湾", "热带岛屿", "孤岛灯塔", "海蚀拱门",
        "潮汐滩涂", "风暴海面", "平静内海", "悬崖瀑布", "多级瀑布",
        "森林溪流", "冰川融水河", "温泉溪谷", "水库群山", "雨后城市河岸",
    ],
    ("场景背景", "森林湿地"): [
        "原始森林", "温带落叶林", "北方针叶林", "热带雨林", "云雾森林",
        "竹海深处", "白桦林", "红杉森林", "苔藓森林", "蕨类谷地",
        "林间空地", "森林木栈道", "古树根系", "萤火虫湿地", "芦苇湿地",
        "沼泽水道", "泥炭湿地", "红树林湿地", "候鸟栖息地", "晨雾草泽",
        "雨后林地", "溪谷密林", "秋色森林", "雪覆森林", "花海林缘",
    ],
    ("场景背景", "荒漠极地"): [
        "沙丘海洋", "岩石荒漠", "盐湖荒原", "雅丹地貌", "戈壁长路",
        "沙漠绿洲", "风蚀峡谷", "干涸河床", "仙人掌荒原", "火山黑原",
        "冰川裂谷", "蓝冰洞穴", "浮冰海域", "极地雪原", "冻原苔原",
        "冰山海岸", "极光雪原", "风雪科考站", "盐沼镜面", "荒原孤树",
    ],
    ("场景背景", "田园乡野"): [
        "稻田阡陌", "金色麦田", "油菜花田", "葡萄园坡地", "薰衣草田",
        "茶园梯田", "果园小径", "牧场草坡", "草原河湾", "乡村土路",
        "水乡村落", "渔村海湾", "山脚农舍", "风车田野", "石墙牧场",
        "雨后村庄", "炊烟村落", "秋收田野", "春耕水田", "冬日原野",
    ],
    ("场景背景", "城市景观"): [
        "城市天际线", "高楼峡谷", "滨江城市夜景", "山城层叠街巷", "海港城市",
        "老城屋顶", "历史街区", "现代广场", "高架桥群", "城市中央公园",
        "雨后商业街", "清晨空街", "黄昏通勤街道", "夜市灯火", "工业港口",
        "铁路枢纽远景", "玻璃建筑群", "混凝土建筑群", "城郊交界", "城市观景台",
    ],
    ("场景背景", "季节景观"): [
        "早春融雪", "春日新绿", "樱花河岸", "暮春花雨", "盛夏浓荫",
        "夏日雷雨", "夏夜萤火", "初秋薄雾", "深秋红叶", "金秋草原",
        "晚秋芦苇", "初冬霜地", "冬日雪原", "雪后放晴", "冰封湖面",
        "梅雨水乡", "台风季海岸", "旱季草原", "雨季瀑布", "极光季雪山",
    ],
    ("构图视角", "风景构图"): [
        "前景框景", "前中后景分层", "引导线通向远山", "河流S形构图", "道路消失点",
        "山谷纵深构图", "水平线三分法", "低地平线天空构图", "高地平线地貌构图", "中央远景锚点",
        "左右山体夹景", "水面倒影对称", "广角环境建立镜头", "长焦压缩山峦", "航拍地貌纹理",
        "低机位草地前景", "高处俯瞰河谷", "雾层递进构图", "人物点景", "建筑点景",
    ],
    ("技术画质", "环境材质"): [
        "湿岩反光", "苔藓微观纹理", "树皮粗糙细节", "落叶堆积层次", "草叶露珠",
        "沙粒风纹", "盐壳结晶", "冰层裂纹", "雪面风蚀纹", "水面细碎波纹",
        "潮湿泥土质感", "河滩卵石细节", "云层明暗体积", "远山空气透视", "雨丝方向清楚",
        "雾气密度渐变", "城市湿地面反射", "风化石材纹理", "木栈道潮湿纹理", "植被层次清楚",
    ],
}
for (_group, _section), _tags in _自然风光光影扩展标签.items():
    _extend_library_section(_group, _section, _tags)

for (_group, _section), _tags in DANBOORU_GENERAL_TAG_EXTENSIONS.items():
    _extend_library_section(_group, _section, _tags)

_奇幻扩展标签 = {
    ("主体", "特殊身份"): ["精灵游侠", "龙骑士", "魔法学院学生", "宫廷魔法师", "圣骑士", "魔剑士", "龙语者", "遗迹探险家", "黑暗女巫", "黑暗女王", "沙漠祭司", "海洋祭司", "潮汐法师", "精灵吟游诗人", "机械魔导师", "幻想女战士"],
    ("画面风格", "艺术风格"): ["日式奇幻动画", "漆原智志画风", "结城信辉画风", "童话绘本", "魔幻油画", "奇幻概念设计", "史诗奇幻海报", "浪漫主义油画"],
    ("画面风格", "美学风格"): ["奇幻风格", "西方奇幻", "高等奇幻", "剑与魔法", "哥特奇幻", "黑暗童话", "精灵幻想", "梦幻奇境", "幻想宫廷", "地下城冒险", "龙骑士史诗", "沙漠神话", "海洋奇幻", "蒸汽魔法", "史诗群像"],
    ("光影氛围", "光线类型"): ["魔法辉光", "翡翠森林光", "龙焰逆光", "星辉月光", "彩窗圣光", "水下焦散", "水晶折射光", "金色晨辉", "火炬暖光", "火炬光", "锐利高光", "暮色天光"],
    ("服装造型", "特殊元素"): ["精灵轻甲", "龙鳞铠甲", "魔法学院制服", "星纹法袍", "哥特礼服", "羽翼圣甲", "冒险者披风", "黑色羽翼"],
    ("场景背景", "特殊场景"): ["浮空城", "精灵王都", "魔法学院", "地下城遗迹", "荆棘城堡", "水晶宫殿", "冰雪王宫", "沙漠神庙", "海底王国", "蒸汽魔法都市", "龙巢宝库", "远古遗迹", "奇幻集市", "天空堡垒", "云海战场", "奥术图书馆", "水晶洞窟", "乌鸦古堡", "天穹遗迹", "秘仪大厅", "天空宫殿", "幻想宴会厅", "冰封要塞", "海市蜃楼神殿", "风暴海岸", "精灵圣树", "飞空艇港", "异世界城镇", "边境村庄", "森林遗迹", "水晶湖", "浮空花园", "边境要塞", "森林神殿", "遗忘神殿"],
    ("道具世界观", "武器法器"): ["水晶法杖", "星辉权杖", "精灵长弓", "龙枪", "魔剑", "魔法书", "冰晶权杖"],
    ("道具世界观", "世界观元素"): ["魔法阵", "浮空水晶", "飞空艇", "星图仪", "魔导机械", "冒险地图", "传送门", "黑玫瑰", "龙蛋", "旗帜"],
    ("构图视角", "构图方式"): ["英雄海报构图", "冒险队群像", "巨龙俯瞰"],
    ("技术画质", "画质描述"): ["华丽奇幻角色设计", "优雅奇幻线稿", "宝石色调上色", "精细赛璐璐", "柔和赛璐璐", "90年代奇幻OVA质感", "史诗概念艺术完成度", "奇幻角色设定"],
    ("技术画质", "特效"): ["魔法粒子", "星尘辉光", "赛璐璐高光", "龙焰火星", "水晶折射", "手绘光效"],
}
for (_group, _section), _tags in _奇幻扩展标签.items():
    _extend_library_section(_group, _section, _tags)

模板推断关键词["插画感"].update({
    "赛璐璐上色", "厚涂绘画", "水彩晕染", "铅笔素描", "黑白线稿", "单色插画",
    "网点漫画", "复古画风", "90年代动画风", "动画截图感", "平涂上色", "粗线稿",
})
模板推断关键词["CG感"].update({"概念艺术", "角色设计稿", "参考设定表", "多视角展示"})

模板推断关键词["真实感"].update({"中画幅", "Lookbook", "品牌大片", "生活方式广告", "影棚人像", "都市纪实", "街头纪实", "街拍摄影", "电影剧照感", "35mm胶片摄影", "大画幅棚拍", "大片级棚拍", "纪实电影摄影", "港式武侠胶片", "雾景实拍感", "写实真人质感", "复古颗粒", "日韩影像", "日系电影感", "韩系极简影像", "生活流写实", "港风恐怖电影调", "高端时尚编辑肖像", "时尚编辑商业广告"})
模板推断关键词["插画感"].update({"单幅叙事角色插画", "叙事插画", "动画电影截图感", "单幅角色插画", "水粉插画", "墨洗留白", "木刻版画", "平面矢量", "浮世绘"})
模板推断关键词["CG感"].update({"机能赛博", "义体美学", "反乌托邦", "数据机房", "赛博地铁", "全息界面", "能量刀", "电影感单幅画面", "单人角色渲染", "关卡空间单幅画面", "高完成度单人角色渲染", "东方赛博机甲", "东方赛博武侠朋克", "游戏CG质感"})
模板推断关键词["古风"].update({"宋韵美学", "志怪古风", "园林仕女", "褙子", "诃子裙", "比甲", "鹤氅", "月洞门", "水榭", "古琴", "国风人像", "古装剧照感", "园林人像", "工笔插画感", "武侠剧照感", "墨洗留白", "港式武侠", "古风电影氛围", "东方古风武侠", "港风惊悚志怪"})
模板推断关键词["神话感"].update({"东方神话史诗", "敦煌神性", "神庙壁画感", "圣像画神性", "云上神国", "天穹祭坛", "星海神殿", "悬空神庙", "日轮", "月轮", "圣火", "神谕石碑", "史诗感单幅画面", "神性肖像", "祭仪场景", "宏大单幅神话场景", "都市电影人文", "西方奇幻史诗"})
模板推断关键词["插画感"].update({"日式奇幻动画", "漆原智志画风", "结城信辉画风", "童话绘本", "魔幻油画", "精细赛璐璐", "柔和赛璐璐", "90年代奇幻OVA质感"})
模板推断关键词["CG感"].update({"奇幻概念设计", "史诗奇幻海报", "史诗概念艺术完成度", "奇幻角色设定"})
模板推断关键词["神话感"].update({"奇幻风格", "西方奇幻", "高等奇幻", "剑与魔法", "哥特奇幻", "黑暗童话", "精灵幻想", "梦幻奇境", "幻想宫廷", "地下城冒险", "龙骑士史诗", "沙漠神话", "海洋奇幻", "蒸汽魔法", "史诗群像"})

快速推荐强风格标签集合.update({"机能赛博", "宋韵美学", "志怪古风", "东方神话史诗", "敦煌神性", "神庙壁画感", "东方古风武侠", "东方赛博武侠朋克", "日韩影像", "西方奇幻史诗"})
快速推荐高完成度标签集合.update({"品牌大片", "广告成片质感", "云上神国", "天穹祭坛", "星海神殿", "日系影像质感", "韩系广告质感", "游戏CG质感"})
快速推荐道具叙事标签集合.update({"古琴", "能量刀", "日轮", "月轮", "神谕石碑", "圣火"})
自定义标签归类关键词 = deepcopy(内置标签库)


def _清理快速推荐空列表() -> None:
    for mapping in (快速推荐分组, 快速推荐档位索引, 快速推荐用途索引):
        for key in list(mapping.keys()):
            items = [item for item in mapping[key] if item]
            if items:
                mapping[key] = items
            else:
                del mapping[key]

    for group_name in list(快速推荐分组档位索引.keys()):
        tier_map = 快速推荐分组档位索引[group_name]
        for tier_name in list(tier_map.keys()):
            items = [item for item in tier_map[tier_name] if item]
            if items:
                tier_map[tier_name] = items
            else:
                del tier_map[tier_name]
        if not tier_map:
            del 快速推荐分组档位索引[group_name]

    for group_name in list(快速推荐分组用途索引.keys()):
        use_map = 快速推荐分组用途索引[group_name]
        for use_case in list(use_map.keys()):
            items = [item for item in use_map[use_case] if item]
            if items:
                use_map[use_case] = items
            else:
                del use_map[use_case]
        if not use_map:
            del 快速推荐分组用途索引[group_name]


def _移除快速推荐组合(name: str) -> None:
    preset_name = str(name or "").strip()
    if not preset_name:
        return
    快速推荐组合.pop(preset_name, None)
    快速推荐元数据.pop(preset_name, None)

    for mapping in (快速推荐分组, 快速推荐档位索引, 快速推荐用途索引):
        for key in list(mapping.keys()):
            mapping[key] = [item for item in mapping[key] if item != preset_name]

    for tier_map in 快速推荐分组档位索引.values():
        for tier_name in list(tier_map.keys()):
            tier_map[tier_name] = [item for item in tier_map[tier_name] if item != preset_name]

    for use_map in 快速推荐分组用途索引.values():
        for use_case in list(use_map.keys()):
            use_map[use_case] = [item for item in use_map[use_case] if item != preset_name]

    _清理快速推荐空列表()


def _添加快速推荐组合(
    name: str,
    tags: list[str],
    *,
    group: str,
    tier: str,
    use_cases: list[str],
    search_keywords: list[str] | None = None,
) -> None:
    preset_name = str(name or "").strip()
    if not preset_name:
        return
    normalized_tags = _extend_unique_list([], tags)
    normalized_use_cases = _extend_unique_list([], use_cases)
    normalized_keywords = _extend_unique_list(
        [preset_name, group, tier, *normalized_use_cases, *normalized_tags],
        search_keywords or [],
    )

    快速推荐组合[preset_name] = normalized_tags
    快速推荐元数据[preset_name] = {
        "group": group,
        "tier": tier,
        "tag_count": len(normalized_tags),
        "use_cases": normalized_use_cases,
        "search_keywords": normalized_keywords,
        **_推断快速推荐目录元数据(preset_name, normalized_tags, normalized_use_cases, group, tier),
    }
    快速推荐分组[group] = _extend_unique_list(list(快速推荐分组.get(group, [])), [preset_name])
    快速推荐档位索引[tier] = _extend_unique_list(list(快速推荐档位索引.get(tier, [])), [preset_name])
    if group not in 快速推荐分组档位索引:
        快速推荐分组档位索引[group] = OrderedDict()
    快速推荐分组档位索引[group][tier] = _extend_unique_list(list(快速推荐分组档位索引[group].get(tier, [])), [preset_name])

    for use_case in normalized_use_cases:
        快速推荐用途索引[use_case] = _extend_unique_list(list(快速推荐用途索引.get(use_case, [])), [preset_name])
        if group not in 快速推荐分组用途索引:
            快速推荐分组用途索引[group] = OrderedDict()
        快速推荐分组用途索引[group][use_case] = _extend_unique_list(list(快速推荐分组用途索引[group].get(use_case, [])), [preset_name])


for _preset_name in (
    "糖水片成年写真",
    "古风美人",
    "神话史诗",
    "赛博朋克",
    "运行时弱随机",
    "运行时强随机",
    "纯欲成年女性",
    "成人私房",
    "白底低遮挡私房",
    "男性低遮挡轮廓",
    "酒店微醺夜景",
    "温泉雾气湿发",
    "雨夜窗边私房",
    "电影剧照机修师",
    "办公室律师男像",
    "欧式贵族",
    "巴洛克珠宝肖像",
    "古风月下庭院",
    "维修车间夜班",
    "新中式国潮",
    "窗边清晨男像",
    "史诗战斗修女",
    "未来都市女特工",
    "低遮挡轮廓写真",
    "浴缸微醺轮廓",
    "海边轻熟写实",
    "海边轻熟写实·中景",
    "落地窗轻私房",
    "落地窗轻私房·中景",
    "浴缸蒸汽私房",
    "浴缸蒸汽私房·中景",
    "夜色男性私房",
    "夜色男性私房·中景",
):
    _移除快速推荐组合(_preset_name)

_添加快速推荐组合(
    "日韩系生活影像",
    [
        "真实感",
        "日韩影像",
        "日系电影感",
        "韩系极简影像",
        "生活流写实",
        "35mm胶片摄影",
        "生活电影剧照",
        "雨夜站台",
        "阴天柔散光",
        "中景半身",
        "人物完整入镜",
        "电影胶片look",
    ],
    group="人像写真",
    tier="高完成度",
    use_cases=["人像", "电影感", "女性向"],
)
_添加快速推荐组合(
    "东方古风武侠",
    [
        "古风",
        "东方古风武侠",
        "港式武侠",
        "港式武侠胶片",
        "武侠剧照感",
        "幽暗竹林",
        "35mm胶片摄影",
        "黑色电影硬光",
        "暖色轮廓逆光",
        "全景全身",
        "人物完整入镜",
    ],
    group="古风神话",
    tier="高完成度",
    use_cases=["古风", "电影感", "人像"],
)
_添加快速推荐组合(
    "东方赛博武侠朋克",
    [
        "CG感",
        "东方赛博武侠朋克",
        "东方赛博机甲",
        "机能赛博",
        "全息界面",
        "能量刀",
        "赛博街区",
        "蓝洋红对撞",
        "变形宽银幕",
        "义体金属细节",
        "游戏CG质感",
    ],
    group="CG科幻",
    tier="高完成度",
    use_cases=["CG科幻", "电影感", "道具叙事"],
)
_添加快速推荐组合(
    "现代生活流写实",
    [
        "真实感",
        "生活流写实",
        "都市电影人文",
        "生活电影剧照",
        "街头纪实",
        "街道",
        "阴天柔散光",
        "中景半身",
        "人物完整入镜",
        "边缘干净",
        "背景不过分抢镜",
    ],
    group="人像写真",
    tier="稳妥",
    use_cases=["人像", "电影感", "职业"],
)
_添加快速推荐组合(
    "中画幅通勤大片",
    [
        "真实感",
        "成年女性",
        "东亚",
        "中画幅",
        "品牌大片",
        "Lookbook",
        "生活方式广告",
        "都市纪实",
        "白衬衫",
        "长款大衣",
        "街道",
        "阴天自然光",
        "全景全身",
        "50mm标准镜头",
        "电影调色",
        "肤色校正自然",
        "服装褶皱真实",
    ],
    group="人像写真",
    tier="高完成度",
    use_cases=["人像", "女性向", "电影感"],
)
_添加快速推荐组合(
    "城市天台晚风纪实",
    [
        "真实感",
        "成年女性",
        "东亚",
        "城市屋顶纪实",
        "晚风纪实",
        "城市天台",
        "屋顶晾衣架",
        "有线耳机",
        "黑长直",
        "日落逆光",
        "晚风感",
        "侧脸构图",
        "负空间留白",
        "背景轻微虚化",
        "发丝迎风清晰",
        "侧脸轮廓清晰",
        "生活电影感",
    ],
    group="人像写真",
    tier="高完成度",
    use_cases=["人像", "电影感", "女性向"],
    search_keywords=["天台", "屋顶", "晚风", "耳机", "侧脸", "纪实", "rooftop", "sunset"],
)
_添加快速推荐组合(
    "新中式国潮",
    [
        "真实感",
        "成年女性",
        "东亚",
        "国潮",
        "中式盘扣",
        "马面裙",
        "暖色调",
        "杂志感",
        "全景全身",
    ],
    group="人像写真",
    tier="稳妥",
    use_cases=["人像", "女性向"],
)
_添加快速推荐组合(
    "海边轻熟写实·标准",
    [
        "真实感",
        "成年女性",
        "东亚",
        "轻熟感",
        "海边",
        "黄昏",
        "黑长直",
        "深灰丝绒礼服",
        "自然光",
        "全景全身",
        "50mm标准镜头",
        "三分法",
        "低饱和",
    ],
    group="人像写真",
    tier="高完成度",
    use_cases=["人像", "女性向", "电影感"],
)
_添加快速推荐组合(
    "海边轻熟写实·近景",
    ["真实感", "成年女性", "东亚", "轻熟感", "海边", "黄昏", "黑长直", "深灰丝绒礼服", "自然光", "近景半身", "85mm人像镜头", "低饱和"],
    group="人像写真",
    tier="高完成度",
    use_cases=["人像", "女性向", "电影感"],
)
_添加快速推荐组合(
    "海边轻熟写实·全身",
    ["真实感", "成年女性", "东亚", "轻熟感", "海边", "黄昏", "黑长直", "深灰丝绒礼服", "自然光", "全景全身", "50mm标准镜头", "环境人像", "低饱和"],
    group="人像写真",
    tier="高完成度",
    use_cases=["人像", "女性向", "电影感"],
)
_添加快速推荐组合(
    "机能赛博雨夜",
    [
        "CG感",
        "成年女性",
        "机能赛博",
        "义体美学",
        "全息界面",
        "能量刀",
        "广告屏街谷",
        "霓虹雨夜",
        "全息投影光",
        "广告屏反射光",
        "低角度",
        "变形宽银幕",
        "义体金属细节",
        "霓虹反射克制",
    ],
    group="CG科幻",
    tier="高完成度",
    use_cases=["CG科幻", "女性向", "电影感", "道具叙事"],
)
_添加快速推荐组合(
    "港式武侠胶片",
    [
        "真实感",
        "港式武侠",
        "港风",
        "35mm胶片摄影",
        "电影剧照感",
        "复古颗粒",
        "幽暗竹林",
        "黑色电影硬光",
        "暖色轮廓逆光",
        "全景全身",
        "人物完整入镜",
        "写实真人质感",
    ],
    group="古风神话",
    tier="高完成度",
    use_cases=["古风", "电影感", "人像"],
)
_添加快速推荐组合(
    "古风电影氛围",
    [
        "古风",
        "古风电影氛围",
        "古风电影剧照",
        "月下庭院",
        "纸窗天光",
        "廊下斑驳光",
        "柔光",
        "全景全身",
        "人物完整入镜",
        "发髻结构完整",
        "丝绸褶裥清晰",
    ],
    group="古风神话",
    tier="高完成度",
    use_cases=["古风", "人像", "电影感"],
)
_添加快速推荐组合(
    "东方赛博机甲",
    [
        "CG感",
        "东方赛博机甲",
        "机能赛博",
        "义体美学",
        "全息界面",
        "能量刀",
        "广告屏街谷",
        "霓虹夜色",
        "蓝洋红对撞",
        "低角度",
        "变形宽银幕",
        "义体金属细节",
        "高完成度单人角色渲染",
    ],
    group="CG科幻",
    tier="高完成度",
    use_cases=["CG科幻", "电影感", "道具叙事"],
)
_添加快速推荐组合(
    "敦煌神性壁画",
    [
        "神话感",
        "敦煌神性",
        "神庙壁画感",
        "神话壁画质感",
        "天穹祭坛",
        "星海神殿",
        "圣辉逆光",
        "金雾神光",
        "神官长袍",
        "鎏金头冠",
        "日轮",
        "神谕石碑",
    ],
    group="古风神话",
    tier="高完成度",
    use_cases=["神话", "电影感", "道具叙事"],
)
_添加快速推荐组合(
    "宋韵园林仕女",
    [
        "古风",
        "成年女性",
        "东亚",
        "宋韵美学",
        "园林仕女",
        "褙子",
        "诃子裙",
        "云肩",
        "玉佩",
        "月洞门",
        "水榭",
        "纸窗天光",
        "卷轴式构图",
        "全景全身",
        "丝绸褶裥清晰",
        "发髻结构完整",
    ],
    group="古风神话",
    tier="高完成度",
    use_cases=["古风", "女性向"],
)
_添加快速推荐组合(
    "敦煌神庙神女",
    [
        "神话感",
        "成年女性",
        "神女",
        "东方神话史诗",
        "敦煌神性",
        "神庙壁画感",
        "鎏金头冠",
        "日轮",
        "天穹祭坛",
        "圣辉逆光",
        "云隙光",
        "祭坛对称构图",
        "广角",
        "神性皮肤光泽",
        "宝石能量晕光",
        "神话壁画质感",
    ],
    group="古风神话",
    tier="高完成度",
    use_cases=["神话", "女性向", "道具叙事"],
)
_添加快速推荐组合(
    "山谷圣城巨构",
    [
        "神话感",
        "巨构史诗奇观",
        "山谷圣城",
        "巨构神殿",
        "瀑布峡谷",
        "远山雪峰",
        "史诗城市中轴",
        "山体建筑一体化",
        "中轴对称巨构",
        "超广角全景",
        "云隙光",
        "体积光",
        "山体建筑细节密度",
    ],
    group="场景史诗",
    tier="高完成度",
    use_cases=["场景", "神话", "电影感"],
    search_keywords=["圣城", "神殿", "峡谷", "雪峰", "巨构", "奇观", "landscape", "epic city"],
)
_添加快速推荐组合(
    "都市电影人文",
    [
        "真实感",
        "都市电影人文",
        "纪实电影摄影",
        "街头纪实",
        "街道",
        "阴天柔散光",
        "中景半身",
        "人物完整入镜",
        "边缘干净",
        "背景不过分抢镜",
    ],
    group="人像写真",
    tier="稳妥",
    use_cases=["人像", "电影感", "职业"],
)
_添加快速推荐组合(
    "高端时尚编辑肖像",
    [
        "真实感",
        "高端时尚编辑肖像",
        "杂志编辑摄影",
        "大画幅棚拍",
        "中画幅质感",
        "广告成片质感",
        "冷色调",
        "高对比",
        "中景半身",
        "面部作为第一视觉中心",
        "人物视觉重心更偏封面肖像",
    ],
    group="人像写真",
    tier="高完成度",
    use_cases=["人像", "电影感", "女性向"],
)
_添加快速推荐组合(
    "国风暗黑志怪",
    [
        "古风",
        "志怪古风",
        "港式武侠",
        "雾景实拍感",
        "神谕石碑",
        "宗教圣所",
        "黑色电影硬光",
        "低饱和",
        "过肩镜头",
        "人物完整入镜",
    ],
    group="古风神话",
    tier="高完成度",
    use_cases=["古风", "电影感", "测试"],
)
_添加快速推荐组合(
    "落地窗轻私房·标准",
    [
        "真实感",
        "成年女性",
        "东亚",
        "私房写真",
        "卧室",
        "落地窗夜景",
        "微醺感",
        "丝质睡袍",
        "全景全身",
        "50mm标准镜头",
        "柔光",
        "胶片感",
    ],
    group="成人私房",
    tier="高完成度",
    use_cases=["成人", "女性向", "电影感"],
)
_添加快速推荐组合(
    "落地窗轻私房·近景",
    ["真实感", "成年女性", "东亚", "私房写真", "卧室", "落地窗夜景", "微醺感", "丝质睡袍", "近景半身", "85mm人像镜头", "柔光", "胶片感"],
    group="成人私房",
    tier="高完成度",
    use_cases=["成人", "女性向", "电影感"],
)
_添加快速推荐组合(
    "落地窗轻私房·全身",
    ["真实感", "成年女性", "东亚", "私房写真", "卧室", "落地窗夜景", "微醺感", "丝质睡袍", "全景全身", "50mm标准镜头", "柔光", "胶片感"],
    group="成人私房",
    tier="高完成度",
    use_cases=["成人", "女性向", "电影感"],
)
_添加快速推荐组合(
    "浴缸蒸汽私房·标准",
    [
        "真实感",
        "成年女性",
        "东亚",
        "私房写真",
        "浴缸",
        "浴室",
        "温泉雾气",
        "湿发",
        "浴巾裹身",
        "全景全身",
        "50mm标准镜头",
        "柔光",
        "暖色调",
    ],
    group="成人私房",
    tier="高完成度",
    use_cases=["成人", "女性向", "电影感"],
)
_添加快速推荐组合(
    "浴缸蒸汽私房·近景",
    ["真实感", "成年女性", "东亚", "私房写真", "浴缸", "浴室", "温泉雾气", "湿发", "浴巾裹身", "近景半身", "85mm人像镜头", "柔光", "暖色调"],
    group="成人私房",
    tier="高完成度",
    use_cases=["成人", "女性向", "电影感"],
)
_添加快速推荐组合(
    "浴缸蒸汽私房·全身",
    ["真实感", "成年女性", "东亚", "私房写真", "浴缸", "浴室", "温泉雾气", "湿发", "浴巾裹身", "全景全身", "50mm标准镜头", "柔光", "暖色调"],
    group="成人私房",
    tier="高完成度",
    use_cases=["成人", "女性向", "电影感"],
)
_添加快速推荐组合(
    "夜色男性私房·标准",
    [
        "真实感",
        "成年男性",
        "东亚",
        "私房写真",
        "卧室",
        "夜晚",
        "落地窗夜景",
        "微湿背头",
        "丝质睡袍",
        "全景全身",
        "50mm标准镜头",
        "侧光",
        "胶片感",
    ],
    group="成人私房",
    tier="高完成度",
    use_cases=["成人", "男性向", "电影感"],
)
_添加快速推荐组合(
    "夜色男性私房·近景",
    ["真实感", "成年男性", "东亚", "私房写真", "卧室", "夜晚", "落地窗夜景", "微湿背头", "丝质睡袍", "近景半身", "85mm人像镜头", "侧光", "胶片感"],
    group="成人私房",
    tier="高完成度",
    use_cases=["成人", "男性向", "电影感"],
)
_添加快速推荐组合(
    "夜色男性私房·全身",
    ["真实感", "成年男性", "东亚", "私房写真", "卧室", "夜晚", "落地窗夜景", "微湿背头", "丝质睡袍", "全景全身", "50mm标准镜头", "侧光", "胶片感"],
    group="成人私房",
    tier="高完成度",
    use_cases=["成人", "男性向", "电影感"],
)
_添加快速推荐组合(
    "工业树灵巨像",
    [
        "CG感",
        "树灵巨像",
        "古木守卫",
        "朽木树皮纹理",
        "苔藓附生质感",
        "工业舱室",
        "巨物压迫近景",
        "冷色工业顶光",
        "风化木纹",
        "发光裂隙",
        "游戏CG质感",
        "材质细节丰富",
    ],
    group="巨物妖兽",
    tier="高完成度",
    use_cases=["巨物", "CG科幻", "电影感"],
    search_keywords=["巨像", "树灵", "木妖", "工业舱室", "怪物", "巨物", "colossus", "monster"],
)


def _补齐快速推荐目录元数据() -> None:
    for preset_name, tags in 快速推荐组合.items():
        meta = 快速推荐元数据.get(preset_name)
        current_meta = dict(meta) if isinstance(meta, dict) else {}
        group = str(current_meta.get("group", "") or "")
        tier = str(current_meta.get("tier", "") or "")
        use_cases = current_meta.get("use_cases") if isinstance(current_meta.get("use_cases"), list) else []
        current_meta.update(_推断快速推荐目录元数据(str(preset_name), list(tags), list(use_cases), group, tier))
        快速推荐元数据[preset_name] = current_meta


_补齐快速推荐目录元数据()

_快速推荐用途优先顺序 = ["人像", "场景", "巨物", "成人", "古风", "神话", "CG科幻", "职业", "女性向", "男性向", "低遮挡", "电影感", "道具叙事", "测试"]
快速推荐用途顺序 = tuple(_extend_unique_list(_快速推荐用途优先顺序, list(快速推荐用途顺序)))

快速推荐分组用途映射 = OrderedDict((group, list(use_map.keys())) for group, use_map in 快速推荐分组用途索引.items())


def _默认自定义小类(category: str) -> str:
    return str(自定义标签默认小类.get(category, "自定义标签"))


def _校验自定义标签名称(text: str) -> str:
    max_length = int(自定义标签规则.get("max_tag_length", 40))
    value = _规范化标签文本(str(text or "")[: 4 * (max_length + 1)])
    if not value:
        raise ValueError("标签不能为空。")
    if len(value) > max_length:
        raise ValueError("标签长度超过限制。")
    if _自定义标签非法分隔符模式.search(value):
        raise ValueError("标签中不能包含分隔符。")
    if value in set(自定义标签规则.get("reserved_values", [])):
        raise ValueError("该标签属于保留值。")
    return value


def _校验自定义小类名称(text: str) -> str:
    max_length = int(自定义标签规则.get("max_section_length", 24))
    value = _规范化标签文本(str(text or "")[: 4 * (max_length + 1)])
    if not value:
        raise ValueError("小类不能为空。")
    if len(value) > max_length:
        raise ValueError("小类名称长度超过限制。")
    if _自定义标签非法分隔符模式.search(value):
        raise ValueError("小类名称中不能包含分隔符。")
    return value


def 解析标签文本列表(text: str, *, max_items: int | None = None) -> list[str]:
    source = str(text or "")[:_自定义标签批量输入最大字符]
    tags: list[str] = []
    seen: set[str] = set()
    for raw_part in _自定义标签分隔模式.split(source):
        part = _规范化标签文本(raw_part)
        if not part:
            continue
        key = _标签规范键(part)
        if key in seen:
            continue
        seen.add(key)
        tags.append(part)
        if max_items is not None and len(tags) >= max_items:
            break
    return tags


def _规范化自定义标签库(
    payload: Any,
    *,
    strict: bool = False,
) -> OrderedDict[str, OrderedDict[str, list[str]]]:
    result = _空自定义标签库()
    if not isinstance(payload, dict):
        if strict:
            raise ValueError("自定义标签库必须是 JSON 对象。")
        return result
    valid_groups = {item["name"] for item in 分组配置}
    section_count = 0
    tag_count = 0
    for category, sections in payload.items():
        raw_category_name = str(category)
        category_name = raw_category_name[:128]
        if category_name not in valid_groups:
            if strict:
                display_name = f"{category_name}..." if len(raw_category_name) > len(category_name) else category_name
                raise ValueError(f"自定义标签库包含无效大类：{display_name or '<空>'}。")
            continue
        if not isinstance(sections, dict):
            if strict:
                raise ValueError(f"大类“{category_name}”的小类数据必须是 JSON 对象。")
            continue
        for section, tags in sections.items():
            try:
                section_name = _校验自定义小类名称(str(section))
            except ValueError as exc:
                if strict:
                    raise ValueError(f"大类“{category_name}”中的{exc}") from exc
                continue
            if not isinstance(tags, list):
                if strict:
                    raise ValueError(f"小类“{section_name}”的标签数据必须是 JSON 数组。")
                continue
            section_count += 1
            if section_count > _自定义标签库最大小类数:
                raise ValueError(f"自定义小类总数不能超过 {_自定义标签库最大小类数} 个。")
            normalized_tags: list[str] = []
            seen: set[str] = set()
            for raw_index, raw_tag in enumerate(tags):
                if raw_index >= _自定义标签库单小类最大扫描项:
                    if strict:
                        raise ValueError(
                            f"小类“{section_name}”待校验条目过多；"
                            f"最多扫描 {_自定义标签库单小类最大扫描项} 项。"
                        )
                    break
                try:
                    tag_name = _校验自定义标签名称(str(raw_tag))
                except ValueError as exc:
                    if strict:
                        raise ValueError(f"小类“{section_name}”中的{exc}") from exc
                    continue
                key = _标签规范键(tag_name)
                if key in seen:
                    continue
                seen.add(key)
                normalized_tags.append(tag_name)
                if len(normalized_tags) > _自定义标签库最大小类标签数:
                    raise ValueError(
                        f"小类“{section_name}”的标签数不能超过 {_自定义标签库最大小类标签数} 个。"
                    )
                tag_count += 1
                if tag_count > _自定义标签库最大标签总数:
                    raise ValueError(f"自定义标签总数不能超过 {_自定义标签库最大标签总数} 个。")
            result[category_name][section_name] = normalized_tags
    return result


def _序列化自定义标签库(library: OrderedDict[str, OrderedDict[str, list[str]]]) -> str:
    serialized = json.dumps(library, ensure_ascii=False, indent=2) + "\n"
    byte_count = len(serialized.encode("utf-8"))
    if byte_count > _自定义标签库最大JSON字节:
        raise ValueError(
            f"自定义标签库 JSON 不能超过 {_自定义标签库最大JSON字节} 字节，当前为 {byte_count} 字节。"
        )
    return serialized


def _自定义标签库文件签名() -> tuple[bool, int, int]:
    try:
        stat = _自定义标签库文件路径.stat()
    except FileNotFoundError:
        return False, 0, 0
    except OSError:
        return _自定义标签库文件路径.exists(), 0, 0
    return True, int(stat.st_mtime_ns), int(stat.st_size)


def _读取自定义标签库文件() -> OrderedDict[str, OrderedDict[str, list[str]]]:
    if not _自定义标签库文件路径.exists():
        return deepcopy(_默认自定义标签库)
    with _自定义标签库文件路径.open("rb") as handle:
        raw_payload = handle.read(_自定义标签库最大JSON字节 + 1)
    if len(raw_payload) > _自定义标签库最大JSON字节:
        raise ValueError(
            f"自定义标签库文件不能超过 {_自定义标签库最大JSON字节} 字节。"
        )
    payload = json.loads(raw_payload.decode("utf-8"))
    return _规范化自定义标签库(payload, strict=True)


def _安装标签库缓存(
    custom_library: OrderedDict[str, OrderedDict[str, list[str]]],
    *,
    signature: tuple[bool, int, int] | None = None,
) -> None:
    global _标签库缓存签名, _标签库缓存自定义, _标签库缓存合并, _标签库缓存展平
    global _标签库缓存推荐索引, _标签库下次签名检查时间

    normalized_custom = _规范化自定义标签库(custom_library)
    current = deepcopy(内置标签库)
    for category_name, sections in normalized_custom.items():
        if category_name not in current:
            current[category_name] = OrderedDict()
        for section_name, tags in sections.items():
            merged = list(current[category_name].get(section_name, []))
            current[category_name][section_name] = _extend_unique_list(merged, tags)

    flattened: dict[str, list[str]] = {}
    recommendation_index: list[tuple[str, str, tuple[str, ...], frozenset[str]]] = []
    for category_name, sections in current.items():
        tags: list[str] = []
        for section_name, values in sections.items():
            tags = _extend_unique_list(tags, list(values))
            value_keys = tuple(_标签规范键(value) for value in values)
            recommendation_index.append(
                (str(category_name), str(section_name), value_keys, frozenset(value_keys))
            )
        flattened[str(category_name)] = tags

    _标签库缓存签名 = signature if signature is not None else _自定义标签库文件签名()
    _标签库缓存自定义 = normalized_custom
    _标签库缓存合并 = current
    _标签库缓存展平 = flattened
    _标签库缓存推荐索引 = tuple(recommendation_index)
    _标签库下次签名检查时间 = time.monotonic() + _标签库签名检查间隔秒


def _确保标签库缓存() -> None:
    global _标签库缓存签名, _标签库下次签名检查时间
    global _标签库无效文件签名, _标签库无效文件错误
    now = time.monotonic()
    if (
        now < _标签库下次签名检查时间
        and _标签库缓存自定义 is not None
        and _标签库缓存合并 is not None
        and _标签库缓存展平 is not None
        and _标签库缓存推荐索引 is not None
    ):
        return
    _标签库下次签名检查时间 = now + _标签库签名检查间隔秒
    signature = _自定义标签库文件签名()
    if (
        signature == _标签库缓存签名
        and _标签库缓存自定义 is not None
        and _标签库缓存合并 is not None
        and _标签库缓存展平 is not None
        and _标签库缓存推荐索引 is not None
    ):
        return
    try:
        custom_library = _读取自定义标签库文件()
    except Exception as exc:
        _标签库无效文件签名 = signature
        _标签库无效文件错误 = f"{type(exc).__name__}: {exc}"
        logging.warning("QwenTE 自定义标签库读取失败，将保留最近一次有效快照: %s: %s", type(exc).__name__, exc)
        if _标签库缓存自定义 is not None:
            _标签库缓存签名 = signature
            return
        custom_library = deepcopy(_默认自定义标签库)
    else:
        _标签库无效文件签名 = None
        _标签库无效文件错误 = ""
    _安装标签库缓存(custom_library, signature=signature)


def _清空标签库缓存() -> None:
    global _标签库缓存签名, _标签库缓存自定义, _标签库缓存合并, _标签库缓存展平
    global _标签库缓存推荐索引, _标签库下次签名检查时间
    global _标签库无效文件签名, _标签库无效文件错误
    with _标签库缓存锁:
        _标签库缓存签名 = object()
        _标签库缓存自定义 = None
        _标签库缓存合并 = None
        _标签库缓存展平 = None
        _标签库缓存推荐索引 = None
        _标签库下次签名检查时间 = 0.0
        _标签库无效文件签名 = None
        _标签库无效文件错误 = ""


def 读取自定义标签库() -> OrderedDict[str, OrderedDict[str, list[str]]]:
    with _标签库缓存锁:
        _确保标签库缓存()
        return deepcopy(_标签库缓存自定义 or _空自定义标签库())


def 保存自定义标签库(payload: OrderedDict[str, OrderedDict[str, list[str]]] | None = None) -> OrderedDict[str, OrderedDict[str, list[str]]]:
    global _标签库无效文件签名, _标签库无效文件错误
    with _标签库缓存锁:
        library = _规范化自定义标签库(
            payload if payload is not None else 读取自定义标签库(),
            strict=True,
        )
        serialized = _序列化自定义标签库(library)
        _自定义标签库文件路径.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix=f"{_自定义标签库文件路径.name}.",
            suffix=".tmp",
            dir=str(_自定义标签库文件路径.parent),
        )
        temporary_path = Path(temporary_name)
        quarantined_backup: Path | None = None
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())
            if _自定义标签库文件路径.exists():
                current_signature = _自定义标签库文件签名()
                validation_error: Exception | None = None
                if _标签库无效文件签名 == current_signature:
                    validation_error = ValueError(_标签库无效文件错误 or "现有自定义标签库无效。")
                elif not (
                    current_signature == _标签库缓存签名
                    and _标签库缓存自定义 is not None
                ):
                    try:
                        _读取自定义标签库文件()
                    except Exception as exc:
                        validation_error = exc
                if validation_error is not None:
                    backup_path = _自定义标签库文件路径.with_name(
                        f"{_自定义标签库文件路径.name}.invalid.bak"
                    )
                    try:
                        os.replace(_自定义标签库文件路径, backup_path)
                        quarantined_backup = backup_path
                    except OSError as backup_error:
                        raise OSError(
                            "现有自定义标签库无效且无法隔离到 .invalid.bak；已取消写入。"
                        ) from backup_error
                    logging.warning(
                        "QwenTE 写入前发现无效自定义标签库，已隔离到 %s: %s: %s",
                        backup_path,
                        type(validation_error).__name__,
                        validation_error,
                    )
            os.replace(temporary_path, _自定义标签库文件路径)
        except BaseException:
            if (
                quarantined_backup is not None
                and quarantined_backup.exists()
                and not _自定义标签库文件路径.exists()
            ):
                try:
                    os.replace(quarantined_backup, _自定义标签库文件路径)
                except OSError:
                    pass
            raise
        finally:
            if temporary_path.exists():
                try:
                    temporary_path.unlink()
                except OSError:
                    pass
        _安装标签库缓存(library)
        _标签库无效文件签名 = None
        _标签库无效文件错误 = ""
        return deepcopy(library)


def 当前标签库() -> OrderedDict[str, OrderedDict[str, list[str]]]:
    with _标签库缓存锁:
        _确保标签库缓存()
        return deepcopy(_标签库缓存合并 or 内置标签库)


def 展平标签分类(大类名称: str) -> list[str]:
    with _标签库缓存锁:
        _确保标签库缓存()
        return list((_标签库缓存展平 or {}).get(str(大类名称), []))


def _当前标签推荐索引() -> tuple[tuple[str, str, tuple[str, ...], frozenset[str]], ...]:
    with _标签库缓存锁:
        _确保标签库缓存()
        return _标签库缓存推荐索引 or ()


def _自定义标签统计(custom_library: OrderedDict[str, OrderedDict[str, list[str]]]) -> dict[str, Any]:
    group_stats: dict[str, int] = {}
    section_count = 0
    tag_count = 0
    for category_name, sections in custom_library.items():
        category_total = 0
        for tags in sections.values():
            section_count += 1
            category_total += len(tags)
            tag_count += len(tags)
        if category_total > 0:
            group_stats[category_name] = category_total
    return {
        "group_count": len(group_stats),
        "section_count": section_count,
        "tag_count": tag_count,
        "groups": group_stats,
    }


def 前端标签库数据() -> dict[str, Any]:
    custom_library = 读取自定义标签库()
    return {
        "slot_config": deepcopy(分组配置),
        "tag_library": 当前标签库(),
        "custom_tag_library": custom_library,
        "custom_tag_rules": deepcopy(自定义标签规则),
        "custom_tag_stats": _自定义标签统计(custom_library),
        "danbooru_general_tags": {
            "scope": "通用视觉标签白名单（不含画师、版权、角色、元数据、幼态与露骨性标签）",
            "tag_count": len(DANBOORU_GENERAL_TAG_ALIASES),
            "aliases": deepcopy(DANBOORU_GENERAL_TAG_ALIASES),
        },
        "template_desc": deepcopy(模板说明),
        "template_outline": deepcopy(模板骨架说明),
        "template_reference": deepcopy(模板参考示例),
        "quick_presets": deepcopy(快速推荐组合),
        "quick_preset_meta": deepcopy(快速推荐元数据),
        "quick_preset_groups": deepcopy(快速推荐分组),
        "quick_preset_tier_order": list(快速推荐档位顺序),
        "quick_preset_tiers": deepcopy(快速推荐档位索引),
        "quick_preset_group_tiers": deepcopy(快速推荐分组档位索引),
        "quick_preset_use_case_order": list(快速推荐用途顺序),
        "quick_preset_use_cases": deepcopy(快速推荐用途索引),
        "quick_preset_group_use_cases": deepcopy(快速推荐分组用途索引),
    }


def 添加自定义标签(category: str, section: str, tag: str) -> tuple[bool, str]:
    category_name = str(category or "")[:128].strip()
    valid_groups = {item["name"] for item in 分组配置}
    if category_name not in valid_groups:
        return False, "无效的大类名称。"
    try:
        section_name = _校验自定义小类名称(section or _默认自定义小类(category_name))
        tag_name = _校验自定义标签名称(tag)
    except ValueError as exc:
        return False, str(exc)

    with _标签库缓存锁:
        custom_library = 读取自定义标签库()
        if section_name not in custom_library[category_name]:
            custom_library[category_name][section_name] = []
        existing_keys = {_标签规范键(item) for item in custom_library[category_name][section_name]}
        if _标签规范键(tag_name) in existing_keys:
            return False, "标签已存在。"
        custom_library[category_name][section_name].append(tag_name)
        try:
            保存自定义标签库(custom_library)
        except (OSError, ValueError) as exc:
            return False, f"添加失败：{exc}"
    return True, f"已添加标签：{tag_name}"


def 批量添加自定义标签(category: str, section: str, tag: str) -> tuple[bool, str, dict[str, Any]]:
    category_name = str(category or "")[:128].strip()
    valid_groups = {item["name"] for item in 分组配置}
    if category_name not in valid_groups:
        detail = {"added": [], "skipped": [], "errors": ["无效的大类名称。"]}
        return False, "无效的大类名称。", detail

    try:
        section_name = _校验自定义小类名称(section or _默认自定义小类(category_name))
    except ValueError as exc:
        detail = {"added": [], "skipped": [], "errors": [str(exc)]}
        return False, str(exc), detail

    detail = {"added": [], "skipped": [], "errors": []}
    raw_text = str(tag or "")
    if len(raw_text) > _自定义标签批量输入最大字符:
        message = f"批量标签输入不能超过 {_自定义标签批量输入最大字符} 个字符。"
        detail["errors"].append(message)
        return False, message, detail
    raw_tags = 解析标签文本列表(raw_text, max_items=int(自定义标签规则.get("max_batch_add", 30)))
    with _标签库缓存锁:
        custom_library = 读取自定义标签库()
        next_section_tags = list(custom_library[category_name].get(section_name, []))
        existing_keys = {_标签规范键(item) for item in next_section_tags}

        for raw_tag in raw_tags:
            try:
                tag_name = _校验自定义标签名称(raw_tag)
            except ValueError as exc:
                detail["errors"].append(str(exc))
                continue
            key = _标签规范键(tag_name)
            if key in existing_keys:
                detail["skipped"].append(tag_name)
                continue
            next_section_tags.append(tag_name)
            existing_keys.add(key)
            detail["added"].append(tag_name)

        if detail["added"]:
            custom_library[category_name][section_name] = next_section_tags
            try:
                保存自定义标签库(custom_library)
            except (OSError, ValueError) as exc:
                detail["added"] = []
                detail["errors"].append(str(exc))
                return False, f"批量添加失败：{exc}", detail
    ok = bool(detail["added"]) or bool(detail["skipped"])
    message = f"已添加 {len(detail['added'])} 个标签。"
    return ok, message, detail


def 删除自定义标签(category: str, section: str, tag: str) -> tuple[bool, str]:
    category_name = str(category or "")[:128].strip()
    try:
        section_name = _校验自定义小类名称(section)
        tag_key = _标签规范键(_校验自定义标签名称(tag))
    except ValueError as exc:
        return False, str(exc)
    with _标签库缓存锁:
        custom_library = 读取自定义标签库()
        if category_name not in custom_library or section_name not in custom_library[category_name]:
            return False, "未找到对应的自定义标签。"
        next_tags = [item for item in custom_library[category_name][section_name] if _标签规范键(item) != tag_key]
        if len(next_tags) == len(custom_library[category_name][section_name]):
            return False, "未找到对应的自定义标签。"
        if next_tags:
            custom_library[category_name][section_name] = next_tags
        else:
            del custom_library[category_name][section_name]
        try:
            保存自定义标签库(custom_library)
        except (OSError, ValueError) as exc:
            return False, f"删除失败：{exc}"
    return True, "已删除自定义标签。"


def _命中关键词(tag: str, keyword: str) -> bool:
    tag_key = _标签规范键(tag)
    keyword_key = _标签规范键(keyword)
    return bool(keyword_key) and (keyword_key in tag_key or tag_key in keyword_key)


def 推荐自定义标签归类(tag: str, *, max_items: int = 12) -> dict[str, Any]:
    tags = 解析标签文本列表(tag, max_items=max_items)
    recommendation_index = _当前标签推荐索引()
    results: list[dict[str, Any]] = []
    total_hits = 0
    for item in tags:
        item_key = _标签规范键(item)
        best_group = "画面风格"
        best_section = _默认自定义小类(best_group)
        best_score = -1
        exists = False
        for group_name, section_name, value_keys, value_key_set in recommendation_index:
            if item_key in value_key_set:
                best_group = group_name
                best_section = section_name
                best_score = 999
                exists = True
                break
            score = sum(
                1
                for value_key in value_keys
                if value_key and (value_key in item_key or item_key in value_key)
            )
            if score > best_score:
                best_group = group_name
                best_section = section_name
                best_score = score
        if best_score > 0:
            total_hits += best_score
        results.append(
            {
                "tag": item,
                "recommended_group": best_group,
                "recommended_section": best_section,
                "exists": exists,
                "score": best_score,
            }
        )
    return {
        "summary": {
            "total": len(results),
            "matched": sum(1 for item in results if item["score"] > 0),
            "exists": sum(1 for item in results if item["exists"]),
            "hit_score": total_hits,
        },
        "tags": results,
    }


# Register data-driven advanced template/theme tags after all library helpers are available.
try:
    from .stage_prompt.expanded_profiles import (
        EXPANDED_PROFILE_TAGS_BY_SECTION,
        EXPANDED_STYLE_KEYWORDS_BY_BASE,
        EXPANDED_TEMPLATE_OPTIONS,
    )
except Exception:  # Direct module loading in focused tests.
    import importlib.util as _expanded_importlib_util

    _expanded_profile_spec = _expanded_importlib_util.spec_from_file_location(
        "prompt_tag_library_expanded_profiles",
        Path(__file__).resolve().parent / "stage_prompt" / "expanded_profiles.py",
    )
    if _expanded_profile_spec is None or _expanded_profile_spec.loader is None:
        raise RuntimeError("Unable to load expanded_profiles.py")
    _expanded_profile_module = _expanded_importlib_util.module_from_spec(_expanded_profile_spec)
    _expanded_profile_spec.loader.exec_module(_expanded_profile_module)
    EXPANDED_PROFILE_TAGS_BY_SECTION = _expanded_profile_module.EXPANDED_PROFILE_TAGS_BY_SECTION
    EXPANDED_STYLE_KEYWORDS_BY_BASE = _expanded_profile_module.EXPANDED_STYLE_KEYWORDS_BY_BASE
    EXPANDED_TEMPLATE_OPTIONS = _expanded_profile_module.EXPANDED_TEMPLATE_OPTIONS

for (_expanded_group, _expanded_section), _expanded_tags in EXPANDED_PROFILE_TAGS_BY_SECTION.items():
    _extend_library_section(_expanded_group, _expanded_section, _expanded_tags)
for _expanded_base, _expanded_keywords in EXPANDED_STYLE_KEYWORDS_BY_BASE.items():
    if _expanded_base in 模板推断关键词:
        模板推断关键词[_expanded_base].update(_expanded_keywords)
快速推荐强风格标签集合.update(EXPANDED_TEMPLATE_OPTIONS)
自定义标签归类关键词 = deepcopy(内置标签库)
_清空标签库缓存()
