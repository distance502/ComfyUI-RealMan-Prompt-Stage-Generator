# -*- coding: utf-8 -*-
"""
Create a bridge workflow that feeds stage prompt positive + negative outputs
into CLIPTextEncode nodes for downstream image generation.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from copy import deepcopy
from pathlib import Path
from typing import Any

if __package__:
    from .workflow_cleanup import 旁路清理节点工作流
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from workflow_cleanup import 旁路清理节点工作流


ROOT = Path(__file__).resolve().parents[2]
SOURCE_WORKFLOW = ROOT / "user" / "default" / "workflows" / "Unsaved Workflow.json"
OUTPUT_WORKFLOW = ROOT / "user" / "default" / "workflows" / "QwenTE_阶段节点正负桥接生图.json"


def _next_id(items: list[dict[str, Any]], key: str = "id") -> int:
    return max((int(item.get(key, 0)) for item in items), default=0) + 1


def _find_node(workflow: dict[str, Any], node_type: str) -> dict[str, Any] | None:
    for node in workflow.get("nodes", []):
        if str(node.get("type")) == node_type:
            return node
    return None


def _remove_links_for_target(workflow: dict[str, Any], *, target_id: int, target_slot: int) -> None:
    links = workflow.get("links", [])
    keep_links = []
    remove_ids: set[int] = set()
    for link in links:
        if not isinstance(link, list) or len(link) < 5:
            keep_links.append(link)
            continue
        if int(link[3]) == target_id and int(link[4]) == target_slot:
            remove_ids.add(int(link[0]))
            continue
        keep_links.append(link)
    workflow["links"] = keep_links
    for node in workflow.get("nodes", []):
        for output in node.get("outputs", []) or []:
            if not isinstance(output, dict):
                continue
            output["links"] = [link_id for link_id in (output.get("links") or []) if int(link_id) not in remove_ids]
        for input_slot in node.get("inputs", []) or []:
            if not isinstance(input_slot, dict):
                continue
            if isinstance(input_slot.get("link"), int) and int(input_slot["link"]) in remove_ids:
                input_slot["link"] = None


def _append_link(workflow: dict[str, Any], *, origin_id: int, origin_slot: int, target_id: int, target_slot: int, link_type: str) -> int:
    next_link_id = int(workflow.get("last_link_id", 0)) + 1
    workflow["last_link_id"] = next_link_id
    workflow.setdefault("links", []).append([next_link_id, origin_id, origin_slot, target_id, target_slot, link_type])
    for node in workflow.get("nodes", []):
        if int(node.get("id", -1)) == origin_id:
            outputs = node.get("outputs", []) or []
            if len(outputs) > origin_slot and isinstance(outputs[origin_slot], dict):
                outputs[origin_slot]["links"] = list(outputs[origin_slot].get("links") or []) + [next_link_id]
        if int(node.get("id", -1)) == target_id:
            inputs = node.get("inputs", []) or []
            if len(inputs) > target_slot and isinstance(inputs[target_slot], dict):
                inputs[target_slot]["link"] = next_link_id
    return next_link_id


def _get_json(url: str, timeout: int = 30) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def main() -> int:
    workflow = json.loads(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
    workflow = 旁路清理节点工作流(workflow)

    model_loader = _find_node(workflow, "QwenTE_ModelLoader")
    clip_loader = _find_node(workflow, "CLIPLoaderGGUF")
    ksampler = _find_node(workflow, "KSampler")
    positive_clip = _find_node(workflow, "CLIPTextEncode")

    if not model_loader or not clip_loader or not ksampler or not positive_clip:
        raise RuntimeError("Source workflow missing key nodes")

    negative_clip = deepcopy(positive_clip)
    negative_clip["id"] = _next_id(workflow["nodes"])
    negative_clip["pos"] = [
        float(positive_clip.get("pos", [0, 0])[0]),
        float(positive_clip.get("pos", [0, 0])[1] + 280),
    ]
    negative_clip["title"] = "QwenTE 推荐负面桥接"
    negative_clip["widgets_values"] = [""]
    negative_clip["inputs"][0]["link"] = None
    negative_clip["inputs"][1]["link"] = None
    negative_clip["outputs"][0]["links"] = []
    workflow["nodes"].append(negative_clip)
    workflow["last_node_id"] = max(int(workflow.get("last_node_id", 0)), int(negative_clip["id"]))

    stage_node_id = _next_id(workflow["nodes"])
    stage_node = {
        "id": stage_node_id,
        "type": "QwenTE_StagePromptGenerator",
        "pos": [
            float(model_loader.get("pos", [0, 0])[0] + 440),
            float(model_loader.get("pos", [0, 0])[1] - 220),
        ],
        "size": [420, 1400],
        "flags": {},
        "order": max(int(node.get("order", 0)) for node in workflow["nodes"]) + 1,
        "mode": 0,
        "inputs": [],
        "outputs": [
            {"name": "结果全文", "type": "STRING", "links": []},
            {"name": "首条正向提示词", "type": "STRING", "links": []},
            {"name": "已选标签", "type": "STRING", "links": []},
            {"name": "JSON结果", "type": "STRING", "links": []},
            {"name": "推荐负面词", "type": "STRING", "links": []},
            {"name": "正向提示词合集", "type": "STRING", "links": []},
        ],
        "properties": {"Node name for S&R": "QwenTE_StagePromptGenerator"},
        "widgets_values": [],
    }
    workflow["nodes"].append(stage_node)
    workflow["last_node_id"] = max(int(workflow.get("last_node_id", 0)), int(stage_node_id))

    stage_info = _get_json("http://127.0.0.1:8188/object_info/QwenTE_StagePromptGenerator")["QwenTE_StagePromptGenerator"]
    required_inputs = stage_info["input"]["required"]
    stage_inputs = []
    widget_values = []
    widget_name_to_index: dict[str, int] = {}
    for name, config in required_inputs.items():
        first = config[0]
        second = config[1] if len(config) > 1 and isinstance(config[1], dict) else {}
        if name == "qwen模型":
            stage_inputs.append({"name": name, "type": "QWENLLAMA", "link": None})
            continue
        input_type = first[0] if isinstance(first, list) else first
        widget_name = name
        stage_inputs.append({"name": name, "type": input_type, "widget": {"name": widget_name}, "link": None})
        widget_name_to_index[name] = len(widget_values)
        if isinstance(first, list):
            widget_values.append(second.get("default", first[0] if first else ""))
        elif input_type == "STRING":
            widget_values.append(second.get("default", ""))
        elif input_type == "BOOLEAN":
            widget_values.append(bool(second.get("default", False)))
        else:
            widget_values.append(second.get("default", 0))
    stage_node["inputs"] = stage_inputs
    stage_node["widgets_values"] = widget_values

    # Sensible defaults for the bridge template.
    for name, value in {
        "模板风格": "自动",
        "主体类型": "自动",
        "案例输出结构": "自动",
        "运行时随机标签": False,
        "运行时随机模式": "全随机",
        "核心标签锁定数量": 6,
        "运行时随机强度": "中",
        "生成数量": 2,
        "提示词语言": "纯中文",
        "详细度": "标准",
        "输出模式": "完整结果",
        "技术画质标签1": "无文字",
        "技术画质标签2": "无水印",
        "技术画质标签3": "无logo",
        "自定义补充标签": "无边框",
    }.items():
        index = widget_name_to_index.get(name)
        if index is not None:
            stage_node["widgets_values"][index] = value

    # Connect model + clip + downstream positive/negative branches.
    _append_link(workflow, origin_id=int(model_loader["id"]), origin_slot=0, target_id=stage_node_id, target_slot=0, link_type="QWENLLAMA")
    _append_link(workflow, origin_id=int(clip_loader["id"]), origin_slot=0, target_id=int(positive_clip["id"]), target_slot=0, link_type="CLIP")
    _append_link(workflow, origin_id=int(clip_loader["id"]), origin_slot=0, target_id=int(negative_clip["id"]), target_slot=0, link_type="CLIP")

    _remove_links_for_target(workflow, target_id=int(positive_clip["id"]), target_slot=1)
    _append_link(workflow, origin_id=stage_node_id, origin_slot=1, target_id=int(positive_clip["id"]), target_slot=1, link_type="STRING")

    _remove_links_for_target(workflow, target_id=int(negative_clip["id"]), target_slot=1)
    _append_link(workflow, origin_id=stage_node_id, origin_slot=4, target_id=int(negative_clip["id"]), target_slot=1, link_type="STRING")

    _remove_links_for_target(workflow, target_id=int(ksampler["id"]), target_slot=2)
    _append_link(workflow, origin_id=int(negative_clip["id"]), origin_slot=0, target_id=int(ksampler["id"]), target_slot=2, link_type="CONDITIONING")

    OUTPUT_WORKFLOW.write_text(json.dumps(workflow, ensure_ascii=False), encoding="utf-8")
    print(f"Created: {OUTPUT_WORKFLOW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
