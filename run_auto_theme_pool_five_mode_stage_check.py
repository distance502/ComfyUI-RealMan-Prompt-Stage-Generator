# -*- coding: utf-8 -*-
"""Run a five-mode stage-only live check for one shared auto theme-pool bone."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PLUGIN_ROOT / "output"
REPORT_PATH = OUTPUT_DIR / "auto_theme_pool_five_mode_stage_report.json"
REGRESSION_RUNNER_PATH = PLUGIN_ROOT / "stage_prompt_regression_runner.py"


CASES: list[dict[str, Any]] = [
    {
        "name": "five_mode_realistic_campus",
        "template_style": "真实感",
        "tags": ["成年女性", "东亚", "清冷", "校园", "中景半身", "高细节"],
        "extra": "保持校园单一主场景，不要切到室内棚拍或夜场，不要任何文字元素。",
        "must_have_any": ["写实摄影", "时装广告大片", "杂志编辑摄影", "纪实抓拍", "真实感"],
        "must_not_have": ["虚幻引擎", "OVA风", "神殿", "古风建筑"],
    },
    {
        "name": "five_mode_illustration_campus",
        "template_style": "插画感",
        "tags": ["成年女性", "东亚", "清冷", "校园", "中景半身", "高细节"],
        "extra": "保持校园单一主场景，不要切到室内棚拍或夜场，不要任何文字元素。",
        "must_have_any": ["高完成度插画", "厚涂插画", "水彩线稿", "复古未来动漫", "OVA风", "插画感"],
        "must_not_have": ["raw photo", "纪实抓拍", "神殿", "古风建筑"],
    },
    {
        "name": "five_mode_cg_campus",
        "template_style": "CG感",
        "tags": ["成年女性", "东亚", "清冷", "校园", "中景半身", "高细节"],
        "extra": "保持校园单一主场景，不要切到室内棚拍或夜场，不要任何文字元素。",
        "must_have_any": ["电影级CG", "概念设计稿", "虚幻引擎渲染", "Octane渲染", "PBR渲染", "CG感"],
        "must_not_have": ["水彩", "神殿", "古风建筑"],
    },
    {
        "name": "five_mode_ancient_campus",
        "template_style": "古风",
        "tags": ["成年女性", "东亚", "清冷", "校园", "中景半身", "高细节"],
        "extra": "保持校园单一主场景，不要切到室内棚拍或夜场，不要任何文字元素。",
        "must_have_any": ["古风人像", "古风电影剧照", "工笔重彩", "玄幻古风", "水墨写意", "古风"],
        "must_not_have": ["虚幻引擎", "未来都市", "机库", "神殿"],
    },
    {
        "name": "five_mode_myth_campus",
        "template_style": "神话感",
        "tags": ["成年女性", "东亚", "清冷", "校园", "中景半身", "高细节"],
        "extra": "保持校园单一主场景，不要切到室内棚拍或夜场，不要任何文字元素。",
        "must_have_any": ["神话史诗感", "神圣史诗", "魔幻现实主义", "暗黑奇幻", "冰雪奇幻", "神话感"],
        "must_not_have": ["虚幻引擎", "未来都市", "机库", "古风建筑"],
    },
]


def load_regression_runner():
    spec = importlib.util.spec_from_file_location("qwen_te_stage_regression_runner", REGRESSION_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载回归脚本：{REGRESSION_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_stage_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(case["name"]),
        "image": False,
        "stage": {
            "模板风格": case["template_style"],
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "运行时随机标签": True,
            "运行时随机模式": "全随机",
            "运行时随机强度": "中",
            "随机主题池": "自动",
            "生成数量": 1,
            "提示词语言": "纯中文",
            "详细度": "详细",
            "输出模式": "完整结果",
            "标签反推模式": "自动平衡",
            "优先柔和肤质": False,
            "抑制文字伪影": False,
            "自定义补充标签": ", ".join(case["tags"]),
            "额外要求": case["extra"],
        },
        "expect": {"must_contain": [], "must_not_contain": []},
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    regression_runner = load_regression_runner()
    report: list[dict[str, Any]] = []
    for case in CASES:
        row: dict[str, Any] = {"name": case["name"], "template_style": case["template_style"]}
        try:
            stage_result = regression_runner.run_stage_case(build_stage_case(case))
            prompt_text = str(stage_result.get("raw_prompt_text") or "").strip()
            row["prompt_id"] = str(stage_result.get("prompt_id") or "")
            row["status"] = str(stage_result.get("status") or "unknown")
            row["prompt_text"] = prompt_text
            row["prompt_lines"] = list(stage_result.get("prompt_lines") or [])
            row["checks"] = {
                "has_subject": "成年女性" in prompt_text,
                "has_scene": "校园" in prompt_text,
                "has_composition": "中景半身" in prompt_text,
                "has_mode_core": any(term in prompt_text for term in case["must_have_any"]),
                "cross_mode_pollution": [term for term in case["must_not_have"] if term in prompt_text],
            }
        except Exception as exc:
            row["error"] = repr(exc)
        report.append(row)
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"REPORT {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
