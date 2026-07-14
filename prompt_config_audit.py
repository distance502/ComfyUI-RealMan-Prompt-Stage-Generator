# -*- coding: utf-8 -*-
"""
标签/规则/模板配置一致性审核脚本
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

预设允许值 = {
    "自动",
    "真实感",
    "插画感",
    "CG感",
    "古风",
    "神话感",
    "人物角色",
    "非人物主体",
    "自动判断",
    "保留已选核心标签",
    "全随机",
    "重写主体与场景",
    "平衡收敛",
    "严格风格隔离",
    "允许风格漂移",
    "弱",
    "中",
    "强",
    "强 / 极限拉开",
}
允许推荐档位 = {"稳妥", "强风格", "高完成度"}
允许推荐用途 = {"人像", "场景", "巨物", "成人", "古风", "神话", "CG科幻", "职业", "女性向", "男性向", "低遮挡", "电影感", "道具叙事", "测试"}

模板字段允许大类 = {
    "style_primary": ("画面风格", "主体", "服装造型", "场景背景", "道具世界观", "光影氛围"),
    "style_secondary": ("画面风格", "主体", "服装造型", "场景背景", "道具世界观", "光影氛围"),
    "style_optional": ("画面风格", "主体", "服装造型", "场景背景", "道具世界观", "光影氛围"),
    "light_primary": ("光影氛围", "技术画质"),
    "light_secondary": ("光影氛围", "技术画质"),
    "mood_pool": ("光影氛围", "成人向表达", "主体"),
    "shot_pool": ("构图视角",),
    "angle_pool": ("构图视角",),
    "lens_pool": ("构图视角", "技术画质"),
    "action_pool": ("动作姿态",),
    "hair_pool": ("主体", "成人向表达"),
    "accessory_pool": ("服装造型", "道具世界观"),
    "clothing_pool": ("服装造型", "成人向表达"),
    "scene_pool": ("场景背景", "成人向表达", "道具世界观"),
    "scene_optional": ("场景背景", "成人向表达", "道具世界观"),
    "quality_primary": ("技术画质", "成人向表达", "光影氛围"),
    "quality_secondary": ("技术画质", "成人向表达", "光影氛围"),
}

语义集合审核跳过关键词 = ("关键词", "线索", "风险")


def _加载模块(module_name: str, file_name: str):
    path = ROOT / file_name
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _收集标签库(tag_library_module) -> tuple[dict[str, set[str]], set[str]]:
    category_tags: dict[str, set[str]] = {}
    all_tags: set[str] = set()
    current_library = tag_library_module.当前标签库()
    for category, sections in current_library.items():
        category_tags[category] = set()
        for tags in sections.values():
            category_tags[category].update(tags)
            all_tags.update(tags)
    return category_tags, all_tags


def _列表重复项(items: list[str]) -> list[str]:
    counter = Counter(items)
    return [item for item, count in counter.items() if count > 1]


def _审核预设(tag_library_module, all_tags: set[str]) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {}
    for preset_name, tags in tag_library_module.快速推荐组合.items():
        missing = [tag for tag in tags if tag not in all_tags and tag not in 预设允许值]
        if missing:
            issues[preset_name] = missing
    return issues


def _审核预设元数据(tag_library_module) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {}
    metadata = getattr(tag_library_module, "快速推荐元数据", {})
    tier_index = getattr(tag_library_module, "快速推荐档位索引", {})
    use_case_index = getattr(tag_library_module, "快速推荐用途索引", {})
    tier_order = set(getattr(tag_library_module, "快速推荐档位顺序", ()))
    use_case_order = set(getattr(tag_library_module, "快速推荐用途顺序", ()))

    for preset_name in tag_library_module.快速推荐组合:
        preset_issues: list[str] = []
        meta = metadata.get(preset_name)
        if not isinstance(meta, dict):
            preset_issues.append("缺少元数据")
        else:
            group_name = str(meta.get("group", "") or "")
            tier_name = str(meta.get("tier", "") or "")
            tag_count = meta.get("tag_count")
            use_cases = meta.get("use_cases")
            search_keywords = meta.get("search_keywords")
            if group_name not in tag_library_module.快速推荐分组:
                preset_issues.append(f"未知分组:{group_name}")
            if tier_name not in 允许推荐档位 or tier_name not in tier_order:
                preset_issues.append(f"未知档位:{tier_name}")
            if not isinstance(tag_count, int) or tag_count <= 0:
                preset_issues.append("无效标签数")
            if not isinstance(use_cases, list) or not use_cases:
                preset_issues.append("缺少用途标签")
            elif any(str(label) not in 允许推荐用途 or str(label) not in use_case_order for label in use_cases):
                preset_issues.append("用途标签非法")
            if not isinstance(search_keywords, list) or not search_keywords:
                preset_issues.append("缺少搜索关键词")
        if preset_issues:
            issues[preset_name] = preset_issues

    indexed_presets: set[str] = set()
    if isinstance(tier_index, dict):
        for tier_name, preset_names in tier_index.items():
            if tier_name not in 允许推荐档位:
                issues[f"档位:{tier_name}"] = ["非法档位键"]
                continue
            if not isinstance(preset_names, list):
                issues[f"档位:{tier_name}"] = ["档位索引不是列表"]
                continue
            indexed_presets.update(str(name) for name in preset_names)

    missing_in_index = [name for name in tag_library_module.快速推荐组合 if name not in indexed_presets]
    if missing_in_index:
        issues["档位索引缺失"] = missing_in_index

    indexed_use_case_presets: set[str] = set()
    if isinstance(use_case_index, dict):
        for use_case_name, preset_names in use_case_index.items():
            if use_case_name not in 允许推荐用途:
                issues[f"用途:{use_case_name}"] = ["非法用途键"]
                continue
            if not isinstance(preset_names, list):
                issues[f"用途:{use_case_name}"] = ["用途索引不是列表"]
                continue
            indexed_use_case_presets.update(str(name) for name in preset_names)

    missing_in_use_case_index = [name for name in tag_library_module.快速推荐组合 if name not in indexed_use_case_presets]
    if missing_in_use_case_index:
        issues["用途索引缺失"] = missing_in_use_case_index

    return issues


def _审核模板配置(template_module, category_tags: dict[str, set[str]]) -> dict[str, dict[str, list[str]]]:
    configs = {
        "非人物模板随机补充配置": template_module.非人物模板随机补充配置,
        "非人物真实感模板随机补充配置": template_module.非人物真实感模板随机补充配置,
        "成人向模板随机补充配置": template_module.成人向模板随机补充配置,
        **{f"模板随机补充配置映射:{key}": value for key, value in template_module.模板随机补充配置映射.items()},
    }

    issues: dict[str, dict[str, list[str]]] = {}
    for config_name, config in configs.items():
        config_issues: dict[str, list[str]] = {}
        for field_name, category_names in 模板字段允许大类.items():
            values = config.get(field_name)
            if not isinstance(values, list):
                continue
            available: set[str] = set()
            for category_name in category_names:
                available.update(category_tags.get(category_name, set()))
            missing = [value for value in values if value not in available]
            if missing:
                config_issues[field_name] = missing
        if config_issues:
            issues[config_name] = config_issues
    return issues


def _审核语义集合(semantic_module, all_tags: set[str]) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {}
    for name, value in vars(semantic_module).items():
        if not name.endswith("集合"):
            continue
        if any(keyword in name for keyword in 语义集合审核跳过关键词):
            continue
        if not isinstance(value, set):
            continue
        missing = [item for item in sorted(value) if item not in all_tags]
        if missing:
            issues[name] = missing
    return issues


def _审核重复项(template_module, rule_module) -> dict[str, list[str]]:
    issues: dict[str, list[str]] = {}
    template_groups = {
        "成人向模板随机补充配置.scene_optional": template_module.成人向模板随机补充配置.get("scene_optional", []),
        "成人向模板随机补充配置.quality_secondary": template_module.成人向模板随机补充配置.get("quality_secondary", []),
    }
    for name, items in template_groups.items():
        if isinstance(items, list):
            duplicates = _列表重复项(items)
            if duplicates:
                issues[name] = duplicates

    rule_groups = {
        "本地回退成人优先级": rule_module.本地回退成人优先级,
        "本地主提示词人物链妆容优先级": rule_module.本地主提示词人物链妆容优先级,
    }
    for name, items in rule_groups.items():
        duplicates = _列表重复项(items)
        if duplicates:
            issues[name] = duplicates
    return issues


def _审核在线搜索配置() -> dict[str, list[str]]:
    path = ROOT / "online_search_config.json"
    issues: dict[str, list[str]] = {}
    if not path.exists():
        issues["file"] = [f"配置文件不存在: {path.name}"]
        return issues

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues["json"] = [f"JSON 解析失败: {exc}"]
        return issues

    if not isinstance(payload, dict):
        issues["schema"] = ["根节点必须是对象"]
        return issues

    tags = payload.get("fallback_generic_downweight_tags")
    if not isinstance(tags, list):
        issues["fallback_generic_downweight_tags"] = ["必须是字符串列表"]
    else:
        seen: set[str] = set()
        duplicates: list[str] = []
        invalid: list[str] = []
        for item in tags:
            text = str(item or "").strip()
            if not text:
                invalid.append(str(item))
                continue
            key = text.casefold()
            if key in seen:
                duplicates.append(text)
                continue
            seen.add(key)
        if duplicates:
            issues["fallback_generic_downweight_tags.duplicates"] = sorted(set(duplicates))
        if invalid:
            issues["fallback_generic_downweight_tags.invalid"] = invalid[:12]

    threshold = payload.get("long_query_term_threshold")
    if not isinstance(threshold, int) or threshold < 8 or threshold > 96:
        issues["long_query_term_threshold"] = ["必须是 8-96 的整数"]

    penalty = payload.get("generic_penalty_score")
    if not isinstance(penalty, int) or penalty < 1 or penalty > 30:
        issues["generic_penalty_score"] = ["必须是 1-30 的整数"]

    return issues


def 生成审核报告() -> dict[str, Any]:
    tag_library_module = _加载模块("prompt_tag_library_audit", "prompt_tag_library.py")
    rule_module = _加载模块("prompt_rule_config_audit", "prompt_rule_config.py")
    semantic_module = _加载模块("prompt_semantic_config_audit", "prompt_semantic_config.py")
    template_module = _加载模块("prompt_template_config_audit", "prompt_template_config.py")

    category_tags, all_tags = _收集标签库(tag_library_module)
    report = {
        "summary": {
            "category_count": len(category_tags),
            "tag_count": len(all_tags),
            "preset_count": len(tag_library_module.快速推荐组合),
            "preset_group_count": len(tag_library_module.快速推荐分组),
        },
        "preset_missing_tags": _审核预设(tag_library_module, all_tags),
        "preset_metadata_issues": _审核预设元数据(tag_library_module),
        "template_pool_missing_tags": _审核模板配置(template_module, category_tags),
        "semantic_set_missing_tags": _审核语义集合(semantic_module, all_tags),
        "duplicate_items": _审核重复项(template_module, rule_module),
        "online_search_config_issues": _审核在线搜索配置(),
    }
    return report


def main(argv: list[str]) -> int:
    report = 生成审核报告()
    as_json = "--json" in argv
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Summary:")
        for key, value in report["summary"].items():
            print(f"  {key}: {value}")
        for section in ("preset_missing_tags", "preset_metadata_issues", "template_pool_missing_tags", "semantic_set_missing_tags", "duplicate_items", "online_search_config_issues"):
            print(f"\n{section}:")
            payload = report[section]
            if not payload:
                print("  none")
                continue
            print(json.dumps(payload, ensure_ascii=False, indent=2))
    has_issues = any(
        report[section]
        for section in (
            "preset_missing_tags",
            "preset_metadata_issues",
            "template_pool_missing_tags",
            "semantic_set_missing_tags",
            "duplicate_items",
            "online_search_config_issues",
        )
    )
    return 1 if has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
