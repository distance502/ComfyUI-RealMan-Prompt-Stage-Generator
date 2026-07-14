# -*- coding: utf-8 -*-
"""
Generate CG-focused prompts directly from prompt_builder with explicit runtime
context, then submit them to ComfyUI for image generation.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_SUITE_PATH = Path(__file__).resolve().with_name("run_template_example_suite.py")
TEST_MODULE_PATH = Path(__file__).resolve().parent / "tests" / "test_stage_prompt_modules.py"
PROMPT_BUILDER_PATH = Path(__file__).resolve().parent / "stage_prompt" / "prompt_builder.py"


CG_CASE_PRESETS: list[dict[str, Any]] = [
    {
        "name": "CG感_赛博雨夜_特工",
        "template_style": "CG感",
        "style_track": "赛博雨夜",
        "scene_group": "city",
        "identity": "特工",
        "selected": OrderedDict(
            {
                "主体": ["成年女性", "东亚", "特工", "冷艳"],
                "画面风格": ["CG感"],
                "场景背景": ["未来都市"],
                "构图视角": ["中景半身"],
                "技术画质": ["高细节", "8K"],
            }
        ),
        "custom_tags": ["雨夜", "装备材质", "湿地面反射"],
        "settings": {
            "模板风格": "CG感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 1,
            "额外要求": "强调潜入任务现场，不要宣传海报排版，不要文字。",
        },
    },
    {
        "name": "CG感_工业科幻_机械师",
        "template_style": "CG感",
        "style_track": "工业科幻",
        "scene_group": "industrial",
        "identity": "机械师",
        "selected": OrderedDict(
            {
                "主体": ["成年女性", "东亚", "机械师", "高智感"],
                "画面风格": ["CG感"],
                "场景背景": ["机库"],
                "构图视角": ["中景"],
                "技术画质": ["高细节", "8K"],
            }
        ),
        "custom_tags": ["维修车间", "金属结构", "工具台"],
        "settings": {
            "模板风格": "CG感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 1,
            "额外要求": "强调工业空间、机修结构和工具材质，不要商业海报感，不要文字。",
        },
    },
    {
        "name": "CG感_女武士",
        "template_style": "CG感",
        "style_track": "",
        "scene_group": "industrial",
        "identity": "女武士",
        "selected": OrderedDict(
            {
                "主体": ["成年女性", "东亚", "女武士", "英气"],
                "画面风格": ["CG感"],
                "场景背景": ["训练场"],
                "构图视角": ["全身"],
                "技术画质": ["高细节", "8K"],
            }
        ),
        "custom_tags": ["盔甲", "重甲结构", "战备状态"],
        "settings": {
            "模板风格": "CG感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 1,
            "额外要求": "强调战备镜头、重甲材质和战斗定位，不要高预算海报排版，不要文字。",
        },
    },
    {
        "name": "CG感_战士",
        "template_style": "CG感",
        "style_track": "",
        "scene_group": "industrial",
        "identity": "战士",
        "selected": OrderedDict(
            {
                "主体": ["成年女性", "东亚", "战士", "冷峻"],
                "画面风格": ["CG感"],
                "场景背景": ["战场"],
                "构图视角": ["全身"],
                "技术画质": ["高细节", "8K"],
            }
        ),
        "custom_tags": ["装甲", "战术机动", "工业结构"],
        "settings": {
            "模板风格": "CG感",
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": True,
            "生成数量": 1,
            "额外要求": "强调装甲结构和出击镜头，不要宣传海报文案感，不要文字。",
        },
    },
]


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载模块：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_template_suite():
    return load_module(TEMPLATE_SUITE_PATH, "qwen_te_template_suite_direct")


def load_prompt_builder():
    return load_module(PROMPT_BUILDER_PATH, "qwen_te_prompt_builder_direct")


def load_test_helpers():
    return load_module(TEST_MODULE_PATH, "qwen_te_test_helpers_direct")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CG-focused style cases via direct prompt_builder context.")
    parser.add_argument("--case-index", type=int, default=0, help="1-based case index to run; 0 runs all cases.")
    return parser.parse_args()


def build_direct_prompt(
    case: dict[str, Any],
    *,
    prompt_builder: Any,
    uniq: Any,
) -> str:
    prompt_list = prompt_builder.build_prompt_list(
        case["selected"],
        case["custom_tags"],
        case["settings"],
        scene_group=case["scene_group"],
        identity=case["identity"],
        style_track=case["style_track"],
        recent_tracks=[],
        uniq=uniq,
        infer_template_style=lambda tags, explicit: explicit,
        infer_subject_type=lambda tags, explicit: explicit,
        infer_output_structure=lambda subject, explicit: explicit,
    )
    if not prompt_list:
        raise RuntimeError(f"未生成提示词：{case['name']}")
    return str(prompt_list[0])


def build_negative_text(case: dict[str, Any]) -> str:
    base = [
        "糖水片",
        "手机抓拍",
        "无滤镜直出",
        "插画感",
        "手绘画风",
        "赛璐璐",
        "怀旧动画",
        "复古动画",
        "低保真",
        "印刷网点",
        "自然噪点",
        "score_9",
        "score_8_up",
        "score_7_up",
        "<lora:",
        "embedding:",
        "text",
        "watermark",
        "logo",
        "signature",
        "title",
        "poster",
        "typography",
        "billboard",
        "lettering",
        "subtitle",
    ]
    if case["identity"] in {"女武士", "战士"}:
        base.extend(["宣传海报排版", "巨幅标题字", "封面大字"])
    return "、".join(base)


def main() -> int:
    args = parse_args()
    cases = list(CG_CASE_PRESETS)
    if args.case_index:
        if args.case_index < 1 or args.case_index > len(cases):
            raise ValueError(f"case-index out of range: {args.case_index}")
        cases = [cases[args.case_index - 1]]

    template_suite = load_template_suite()
    prompt_builder = load_prompt_builder()
    test_helpers = load_test_helpers()

    for index, case in enumerate(cases, start=1):
        prompt_text = build_direct_prompt(case, prompt_builder=prompt_builder, uniq=test_helpers.uniq)
        negative_text = build_negative_text(case)
        prompt_map, _stage_id, positive_clip_id, negative_clip_id = template_suite.build_case_prompt_map(
            {
                "name": case["name"],
                "template_style": case["template_style"],
                "settings": {
                    "主体类型": "人物角色",
                    "案例输出结构": "案例长段版",
                    "提示词语言": "纯中文",
                    "详细度": "详细",
                    "输出模式": "完整结果",
                },
                "tags": [],
                "extra": "",
            },
            template_suite.fetch_prompt_library(),
        )
        template_suite._inject_prompt_text(prompt_map, prompt_text, negative_text, positive_clip_id, negative_clip_id)
        submit = template_suite.post_json(
            f"{template_suite.COMFY_BASE}/prompt",
            {"client_id": "codex-cg-style-focus-direct", "prompt": prompt_map},
        )
        prompt_id = str(submit.get("prompt_id"))
        entry = template_suite.poll_history(prompt_id, timeout_sec=1800)
        images: list[str] = []
        for node_output in (entry.get("outputs") or {}).values():
            if not isinstance(node_output, dict):
                continue
            for image in node_output.get("images") or []:
                image_root = template_suite.LIVE_COMFYUI_ROOT / str(image.get("type") or "output")
                images.append(str(image_root / str(image.get("subfolder") or "") / str(image.get("filename") or "")))
        record = {
            "index": index,
            "name": case["name"],
            "template_style": case["template_style"],
            "style_track": case["style_track"],
            "identity": case["identity"],
            "scene_group": case["scene_group"],
            "prompt_id": prompt_id,
            "prompt_text": prompt_text,
            "negative_text": negative_text,
            "image": {
                "status": str((entry.get("status") or {}).get("status_str") or "unknown"),
                "images": images,
            },
        }
        print(f"[{index}/{len(cases)}] {case['name']} -> {images[0] if images else 'no-image'}")
        print(json.dumps(record, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
