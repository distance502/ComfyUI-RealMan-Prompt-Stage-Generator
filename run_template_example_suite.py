# -*- coding: utf-8 -*-
"""
Run one image for each built-in example template preset and export a report + contact sheet.
"""

from __future__ import annotations

import json
import math
import sys
import time
import urllib.request
import importlib.util
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
COMFY_BASE = "http://127.0.0.1:8188"
WORKFLOW_PATH = ROOT / "user" / "default" / "workflows" / "QwenTE_阶段节点精简生图.json"
LIVE_COMFYUI_ROOT = ROOT
LIVE_COMFYUI_OUTPUT_ROOT = LIVE_COMFYUI_ROOT / "output"
WORKFLOW_FALLBACK_PATHS = (
    LIVE_COMFYUI_ROOT / "user" / "default" / "workflows" / "Z-IMAGE电影光影工作流 by.TE.json",
    LIVE_COMFYUI_ROOT / "user" / "default" / "workflows" / "Kook_Zimage_瑶光.json",
)
REPORT_JSON = ROOT / "output" / "template_example_suite_report.json"
CONTACT_SHEET = ROOT / "output" / "template_example_suite_sheet.png"
CONTROL_MARKERS = {"randomize", "fixed", "increment", "decrement"}
REGRESSION_RUNNER_PATH = Path(__file__).resolve().with_name("stage_prompt_regression_runner.py")


CASE_PRESETS: list[dict[str, Any]] = [
    {
        "name": "auto_林荫街头白衬衫",
        "template_style": "自动",
        "settings": {"主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果"},
        "tags": ["成年女性", "东亚", "清冷", "真实感", "时尚写真", "杂志感", "白衬衫", "奶油针织", "街道", "林荫大道", "自然光", "柔光", "近景", "半身", "平视", "浅景深", "冷白皮", "清透肌肤", "高细节", "8K"],
        "extra": "自动模板需要给出稳定成年人像，不要未成年气质，不要任何文字元素。",
    },
    {
        "name": "真实感_糖水片成年写真",
        "template_style": "真实感",
        "settings": {"主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果"},
        "tags": ["成年女性", "东亚", "甜美", "灵动", "真实感", "糖水片", "CCD感", "奶油针织", "白衬衫", "樱花树下", "柔光", "暖色调", "治愈", "近景", "半身", "镜头近距离", "中心构图", "浅景深", "光斑", "冷白皮", "清透肌肤", "成年大学生气质", "无幼态感", "8K"],
        "extra": "保持成年感，不要未成年气质，不要任何文字元素。",
    },
    {
        "name": "插画感_OVA复古动画",
        "template_style": "插画感",
        "settings": {"主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果"},
        "tags": ["成年女性", "女冒险者", "神秘", "插画感", "OVA风", "手绘画风", "怀旧动画", "赛璐璐", "线条感", "中世纪哥特", "森林", "乡村小道", "梦幻", "中景", "45度角", "广角", "低保真", "印刷网点", "自然噪点", "高细节"],
        "extra": "避免现代摄影腔，保持动画质感，不要任何文字元素。",
    },
    {
        "name": "CG感_史诗战斗修女CG",
        "template_style": "CG感",
        "settings": {"主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果"},
        "tags": ["成年女性", "战斗修女", "神秘", "CG感", "3D渲染", "史诗感", "宗教核", "中世纪哥特", "体积光", "轮廓光", "低角度", "全身", "广角", "神殿", "战场", "盔甲", "斗篷", "金属", "8K", "电影感", "高细节"],
        "extra": "保证角色和神殿尺度清晰，不要文字，不要海报感排版。",
    },
    {
        "name": "古风_古风玄幻半身",
        "template_style": "古风",
        "settings": {"主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果"},
        "tags": ["成年女性", "东亚", "清丽", "空灵", "古风", "玄幻古风", "汉服", "苏绣", "披帛", "步摇", "花钿", "鬓边帘", "发髻", "黑长直", "宫殿", "柔光", "光影斑驳", "浮光", "近景", "半身", "镜头近距离", "面部聚焦", "真实发丝", "冷白皮", "瓷肌", "8K"],
        "extra": "保持古典衣料层次，不要现代都市元素，不要文字。",
    },
    {
        "name": "神话感_云海神女",
        "template_style": "神话感",
        "settings": {"主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果"},
        "tags": ["成年女性", "神女", "神圣", "神话感", "丝绸", "披帛", "发冠", "宝石", "云海", "神殿", "神圣祭坛", "体积光", "柔光", "仰视", "广角", "史诗", "8K", "电影感"],
        "extra": "避免液态金属长裙，避免过强中轴神光柱，神殿台座和建筑轮廓要清晰。",
    },
]


def get_json(url: str, timeout: int = 30) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def load_regression_runner():
    spec = importlib.util.spec_from_file_location("qwen_te_stage_regression_runner", REGRESSION_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载回归脚本：{REGRESSION_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def post_json(url: str, payload: dict[str, Any], timeout: int = 90) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def build_prompt_map(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
    links = {
        int(link[0]): (int(link[1]), int(link[2]), int(link[3]), int(link[4]))
        for link in workflow.get("links", [])
        if isinstance(link, list) and len(link) >= 5
    }
    prompt: dict[str, dict[str, Any]] = {}
    for node in workflow.get("nodes", []):
        node_id = str(node.get("id"))
        class_type = str(node.get("type", "")).strip()
        if not node_id or not class_type:
            continue
        widget_values = list(node.get("widgets_values") or [])
        widget_index = 0

        def consume(expected_type: str) -> Any:
            nonlocal widget_index
            while widget_index < len(widget_values):
                value = widget_values[widget_index]
                widget_index += 1
                if isinstance(value, str) and value.lower() in CONTROL_MARKERS and expected_type not in {"STRING", "COMBO"}:
                    continue
                return value
            return None

        inputs: dict[str, Any] = {}
        for slot in node.get("inputs", []):
            name = str(slot.get("name", "")).strip()
            if not name:
                continue
            expected_type = str(slot.get("type", ""))
            has_widget = isinstance(slot.get("widget"), dict) and bool(slot.get("widget", {}).get("name"))
            link_id = slot.get("link")
            if isinstance(link_id, int) and link_id in links:
                if has_widget:
                    _ = consume(expected_type)
                src_id, src_slot, _dst_id, _dst_slot = links[link_id]
                inputs[name] = [str(src_id), int(src_slot)]
            elif has_widget:
                value = consume(expected_type)
                if value is not None:
                    inputs[name] = value
        prompt[node_id] = {"class_type": class_type, "inputs": inputs}
    return prompt


def poll_history(prompt_id: str, timeout_sec: int = 1800) -> dict[str, Any]:
    started = time.time()
    while time.time() - started < timeout_sec:
        try:
            history = get_json(f"{COMFY_BASE}/history/{prompt_id}")
            entry = history.get(prompt_id)
            if entry:
                return entry
        except Exception:
            pass
        time.sleep(3)
    raise TimeoutError(f"Timed out waiting for prompt {prompt_id}")


def fetch_prompt_library() -> dict[str, Any]:
    return get_json(f"{COMFY_BASE}/qwen_te/prompt_library")


def build_tag_group_index(library: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for group in library.get("slot_config", []):
        group_name = str(group.get("name", ""))
        sections = (library.get("tag_library") or {}).get(group_name, {})
        for tags in sections.values():
            for tag in tags or []:
                tag_text = str(tag)
                mapping.setdefault(tag_text, group_name)
    return mapping


def assign_stage_tags(prompt_map: dict[str, dict[str, Any]], stage_id: str, library: dict[str, Any], tags: list[str], settings: dict[str, Any], extra: str) -> None:
    stage_inputs = prompt_map[stage_id]["inputs"]
    slot_config = library.get("slot_config", [])
    mapping = build_tag_group_index(library)
    grouped: dict[str, list[str]] = {str(group.get("name")): [] for group in slot_config}
    custom_tags: list[str] = []
    for tag in tags:
        group_name = mapping.get(tag)
        if not group_name:
            custom_tags.append(tag)
            continue
        group = next((item for item in slot_config if str(item.get("name")) == group_name), None)
        if group is None:
            custom_tags.append(tag)
            continue
        limit = int(group.get("slots", 0))
        if len(grouped[group_name]) < limit and tag not in grouped[group_name]:
            grouped[group_name].append(tag)
        else:
            custom_tags.append(tag)

    stage_inputs["模板风格"] = settings.get("模板风格", "自动")
    stage_inputs["主体类型"] = settings.get("主体类型", "自动")
    stage_inputs["案例输出结构"] = settings.get("案例输出结构", "自动")
    stage_inputs["提示词语言"] = settings.get("提示词语言", "纯中文")
    stage_inputs["详细度"] = settings.get("详细度", "详细")
    stage_inputs["输出模式"] = settings.get("输出模式", "完整结果")
    stage_inputs["生成数量"] = 1
    stage_inputs["自定义补充标签"] = ", ".join(custom_tags)
    stage_inputs["额外要求"] = extra
    stage_inputs["技术画质标签1"] = stage_inputs.get("技术画质标签1", "无")
    stage_inputs["技术画质标签2"] = stage_inputs.get("技术画质标签2", "无")
    stage_inputs["技术画质标签3"] = stage_inputs.get("技术画质标签3", "无")

    for group in slot_config:
        group_name = str(group.get("name"))
        limit = int(group.get("slots", 0))
        values = grouped.get(group_name, [])
        for index in range(1, limit + 1):
            stage_inputs[f"{group_name}标签{index}"] = values[index - 1] if index - 1 < len(values) else "无"


def resolve_workflow_path() -> Path:
    if WORKFLOW_PATH.exists():
        return WORKFLOW_PATH
    for fallback_path in WORKFLOW_FALLBACK_PATHS:
        if fallback_path.exists():
            return fallback_path
    portable_comfyui_root = Path(sys.executable).resolve().parent.parent / "ComfyUI"
    for filename in ("Z-IMAGE电影光影工作流 by.TE.json", "Kook_Zimage_瑶光.json"):
        portable_fallback = portable_comfyui_root / "user" / "default" / "workflows" / filename
        if portable_fallback.exists():
            return portable_fallback
    raise FileNotFoundError(f"Missing workflow template: {WORKFLOW_PATH}")


def _resolve_prompt_text_node_ids(prompt_map: dict[str, dict[str, Any]]) -> tuple[str | None, str | None]:
    clip_text_nodes = [
        (node_id, payload)
        for node_id, payload in prompt_map.items()
        if payload.get("class_type") == "CLIPTextEncode"
    ]
    if not clip_text_nodes:
        return None, None

    positive_id: str | None = None
    negative_id: str | None = None
    for node_id, payload in clip_text_nodes:
        text_value = str((payload.get("inputs") or {}).get("text", "") or "")
        lowered = text_value.lower()
        if negative_id is None and any(term in lowered for term in ("watermark", "blurry", "low quality", "noise", "bad")):
            negative_id = node_id
            continue
        if positive_id is None:
            positive_id = node_id

    if positive_id is None and clip_text_nodes:
        positive_id = clip_text_nodes[0][0]
    if negative_id is None:
        for node_id, _payload in clip_text_nodes:
            if node_id != positive_id:
                negative_id = node_id
                break
    return positive_id, negative_id


def _inject_prompt_text(
    prompt_map: dict[str, dict[str, Any]],
    prompt_text: str,
    negative_text: str,
    positive_clip_id: str | None,
    negative_clip_id: str | None,
) -> None:
    resolved_positive_id = positive_clip_id
    resolved_negative_id = negative_clip_id
    if resolved_positive_id is None and resolved_negative_id is None:
        resolved_positive_id, resolved_negative_id = _resolve_prompt_text_node_ids(prompt_map)

    if resolved_positive_id:
        prompt_map[resolved_positive_id]["inputs"]["text"] = prompt_text
    if resolved_negative_id:
        prompt_map[resolved_negative_id]["inputs"]["text"] = negative_text or "text, watermark, logo, signature, blurry, low quality"


def build_case_prompt_map(case: dict[str, Any], library: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], str, str | None, str | None]:
    workflow_path = resolve_workflow_path()
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    prompt_map = build_prompt_map(workflow)
    model_loader_id = next((node_id for node_id, payload in prompt_map.items() if payload["class_type"] == "QwenTE_ModelLoader"), None)
    stage_id = next((node_id for node_id, payload in prompt_map.items() if payload["class_type"] == "QwenTE_StagePromptGenerator"), None)
    ksampler_id = next((node_id for node_id, payload in prompt_map.items() if payload["class_type"] == "KSampler"), None)
    save_id = next((node_id for node_id, payload in prompt_map.items() if payload["class_type"] == "SaveImage"), None)
    positive_clip_id, negative_clip_id = _resolve_prompt_text_node_ids(prompt_map)

    if model_loader_id is not None:
        prompt_map[model_loader_id]["inputs"]["上下文长度"] = max(16384, int(prompt_map[model_loader_id]["inputs"].get("上下文长度", 8192)))
    if stage_id is not None:
        assign_stage_tags(prompt_map, stage_id, library, case["tags"], case["settings"], case["extra"])
        prompt_map[stage_id]["inputs"]["seed"] = random_seed(case["name"], offset=1)
    if ksampler_id is not None:
        prompt_map[ksampler_id]["inputs"]["seed"] = random_seed(case["name"], offset=2)
        prompt_map[ksampler_id]["inputs"]["steps"] = 4
    if save_id is not None:
        prompt_map[save_id]["inputs"]["filename_prefix"] = f"template_example_{case['name']}"
    return prompt_map, stage_id or "", positive_clip_id, negative_clip_id


def random_seed(label: str, *, offset: int = 0) -> int:
    base = sum(ord(ch) for ch in label)
    return int(f"{base % 100000}{offset + 1}13579")


def extract_stage_outputs(entry: dict[str, Any]) -> tuple[str, str]:
    outputs = entry.get("outputs") or {}
    prompt_text = ""
    negative_text = ""
    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        text_blocks = node_output.get("text")
        if not isinstance(text_blocks, list) or not text_blocks:
            continue
        text = str(text_blocks[0]).strip()
        if not text:
            continue
        if "推荐负面词" in text or "watermark" in text or "bad anatomy" in text:
            negative_text = text
        elif len(text) > len(prompt_text):
            prompt_text = text
    return prompt_text, negative_text


def build_style_matrix_summary(report: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "case_count": len(report),
        "styles": [],
    }
    styles: list[dict[str, Any]] = []
    for row in report:
        stage = row.get("stage") if isinstance(row.get("stage"), dict) else {}
        prompt_text = str(row.get("prompt_text") or "").strip()
        negative_text = str(row.get("negative_text") or "").strip()
        styles.append(
            {
                "name": row.get("name"),
                "template_style": row.get("template_style"),
                "prompt_preview": prompt_text[:220],
                "negative_preview": negative_text[:160],
                "image_status": (row.get("image") or {}).get("status"),
                "prompt_status": stage.get("status"),
            }
        )
    summary["styles"] = styles
    return summary


def build_contact_sheet(report: list[dict[str, Any]]) -> None:
    card_width = 480
    card_height = 320
    margin = 20
    columns = 2
    rows = math.ceil(len(report) / columns)
    canvas = Image.new("RGB", (columns * card_width + (columns + 1) * margin, rows * card_height + (rows + 1) * margin), (24, 26, 33))
    draw = ImageDraw.Draw(canvas)
    for index, row in enumerate(report):
        col = index % columns
        row_index = index // columns
        x = margin + col * (card_width + margin)
        y = margin + row_index * (card_height + margin)
        label = str(row.get("name") or "case")
        image_list = (row.get("image") or {}).get("images", [])
        image_path = Path(image_list[0]) if image_list else None
        if image_path and image_path.exists():
            image = Image.open(image_path).convert("RGB")
            image.thumbnail((card_width, card_height - 40))
            canvas.paste(image, (x, y))
        else:
            draw.rectangle((x, y, x + card_width - 1, y + card_height - 40), outline=(80, 86, 96), width=2)
            draw.text((x + 18, y + 24), "NO IMAGE", fill=(235, 160, 160))
        draw.text((x, y + card_height - 28), label, fill=(235, 238, 245))
    canvas.save(CONTACT_SHEET)


def main() -> int:
    library = fetch_prompt_library()
    regression_runner = load_regression_runner()
    report: list[dict[str, Any]] = []
    for index, case in enumerate(CASE_PRESETS, start=1):
        record: dict[str, Any] = {
            "index": index,
            "name": case["name"],
            "template_style": case["template_style"],
        }
        try:
            stage_case = {
                "name": case["name"],
                "image": False,
                "stage": {
                    "模板风格": case["template_style"],
                    **case["settings"],
                    "生成数量": 1,
                    "自定义补充标签": ", ".join(case["tags"]),
                    "额外要求": case["extra"],
                },
                "expect": {"must_contain": [], "must_not_contain": []},
            }
            stage_result = regression_runner.run_stage_case(stage_case)
            prompt_text = (stage_result.get("prompt_lines") or [""])[0]
            negative_text = stage_result.get("negative_prompt", "")
            prompt_map, _stage_id, positive_clip_id, negative_clip_id = build_case_prompt_map(case, library)
            _inject_prompt_text(prompt_map, prompt_text, negative_text, positive_clip_id, negative_clip_id)
            submit = post_json(f"{COMFY_BASE}/prompt", {"client_id": "codex-template-suite", "prompt": prompt_map})
            prompt_id = str(submit.get("prompt_id"))
            entry = poll_history(prompt_id, timeout_sec=1800)
            images: list[str] = []
            for node_output in (entry.get("outputs") or {}).values():
                if not isinstance(node_output, dict):
                    continue
                for image in node_output.get("images") or []:
                    image_root = LIVE_COMFYUI_ROOT / str(image.get("type") or "output")
                    images.append(str(image_root / str(image.get("subfolder") or "") / str(image.get("filename") or "")))
            record.update(
                {
                    "prompt_id": prompt_id,
                    "prompt_text": prompt_text,
                    "negative_text": negative_text,
                    "stage": stage_result,
                    "image": {"status": str((entry.get("status") or {}).get("status_str") or "unknown"), "images": images},
                }
            )
        except Exception as exc:
            record["error"] = repr(exc)
            record["image"] = {"status": "error", "images": []}
        record["style_matrix"] = {
            "case_index": index,
            "case_count": len(CASE_PRESETS),
            "template_style": case["template_style"],
            "comparison_label": f"{index}/{len(CASE_PRESETS)}",
        }
        report.append(record)
        REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        image_list = (record.get("image") or {}).get("images", [])
        print(f"[{index}/{len(CASE_PRESETS)}] {case['name']} -> {image_list[0] if image_list else 'no-image'}")
    style_matrix_summary = build_style_matrix_summary(report)
    report[-1]["style_matrix_summary"] = style_matrix_summary
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    build_contact_sheet(report)
    print(f"REPORT {REPORT_JSON}")
    print(f"SHEET {CONTACT_SHEET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
