# -*- coding: utf-8 -*-
"""
Create a multi-branch workflow that splits the stage prompt collection into
up to four prompts and duplicates the full downstream image branch so each
prompt is sampled, decoded, and saved independently.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

if __package__:
    from .workflow_cleanup import 旁路清理节点工作流
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from workflow_cleanup import 旁路清理节点工作流


ROOT = Path(__file__).resolve().parents[2]
SOURCE_WORKFLOW = ROOT / "user" / "default" / "workflows" / "QwenTE_阶段节点正负桥接生图.json"
OUTPUT_WORKFLOW = ROOT / "user" / "default" / "workflows" / "QwenTE_阶段节点多提示词生图.json"


def _next_id(items: list[dict[str, Any]], key: str = "id") -> int:
    return max((int(item.get(key, 0)) for item in items), default=0) + 1


def _next_link_id(workflow: dict[str, Any]) -> int:
    return max((int(link[0]) for link in workflow.get("links", []) if isinstance(link, list) and link), default=0) + 1


def _find_node(workflow: dict[str, Any], node_type: str) -> dict[str, Any] | None:
    for node in workflow.get("nodes", []):
        if str(node.get("type")) == node_type:
            return node
    return None


def _find_nodes(workflow: dict[str, Any], node_type: str) -> list[dict[str, Any]]:
    return [node for node in workflow.get("nodes", []) if str(node.get("type")) == node_type]


def _append_link(
    workflow: dict[str, Any],
    *,
    origin_id: int,
    origin_slot: int,
    target_id: int,
    target_slot: int,
    link_type: str,
) -> int:
    link_id = _next_link_id(workflow)
    workflow.setdefault("links", []).append([link_id, origin_id, origin_slot, target_id, target_slot, link_type])
    workflow["last_link_id"] = link_id
    for node in workflow.get("nodes", []):
        if int(node.get("id", -1)) == origin_id:
            outputs = node.get("outputs", []) or []
            if len(outputs) > origin_slot and isinstance(outputs[origin_slot], dict):
                outputs[origin_slot]["links"] = list(outputs[origin_slot].get("links") or []) + [link_id]
        if int(node.get("id", -1)) == target_id:
            inputs = node.get("inputs", []) or []
            if len(inputs) > target_slot and isinstance(inputs[target_slot], dict):
                inputs[target_slot]["link"] = link_id
    return link_id


def _remove_links_for_target(workflow: dict[str, Any], *, target_id: int, target_slot: int) -> None:
    keep_links = []
    removed: set[int] = set()
    for link in workflow.get("links", []):
        if not isinstance(link, list) or len(link) < 5:
            keep_links.append(link)
            continue
        if int(link[3]) == target_id and int(link[4]) == target_slot:
            removed.add(int(link[0]))
            continue
        keep_links.append(link)
    workflow["links"] = keep_links
    for node in workflow.get("nodes", []):
        for output in node.get("outputs", []) or []:
            if isinstance(output, dict):
                output["links"] = [link_id for link_id in (output.get("links") or []) if int(link_id) not in removed]
        for input_slot in node.get("inputs", []) or []:
            if isinstance(input_slot, dict) and isinstance(input_slot.get("link"), int) and int(input_slot["link"]) in removed:
                input_slot["link"] = None


def _copy_node(node: dict[str, Any], *, new_id: int, dx: float, dy: float, title: str) -> dict[str, Any]:
    clone = deepcopy(node)
    clone["id"] = new_id
    pos = clone.get("pos", [0, 0]) or [0, 0]
    clone["pos"] = [float(pos[0]) + dx, float(pos[1]) + dy]
    clone["title"] = title
    for input_slot in clone.get("inputs", []) or []:
        if isinstance(input_slot, dict):
            input_slot["link"] = None
    for output in clone.get("outputs", []) or []:
        if isinstance(output, dict):
            output["links"] = []
    return clone


def _collect_downstream_node_ids(workflow: dict[str, Any], start_id: int) -> set[int]:
    links = [link for link in workflow.get("links", []) if isinstance(link, list) and len(link) >= 6]
    keep: set[int] = set()
    stack = [int(start_id)]
    while stack:
        origin_id = stack.pop()
        for link in links:
            if int(link[1]) != origin_id:
                continue
            target_id = int(link[3])
            if target_id in keep:
                continue
            keep.add(target_id)
            stack.append(target_id)
    return keep


def _copy_downstream_subgraph(
    workflow: dict[str, Any],
    *,
    root_node: dict[str, Any],
    downstream_ids: set[int],
    dx: float,
    dy: float,
    title_suffix: str,
) -> tuple[dict[int, int], list[dict[str, Any]]]:
    node_map = {int(node.get("id")): node for node in workflow.get("nodes", [])}
    id_map: dict[int, int] = {}
    clones: list[dict[str, Any]] = []

    root_clone_id = _next_id(workflow["nodes"] + clones)
    root_clone = _copy_node(
        root_node,
        new_id=root_clone_id,
        dx=dx,
        dy=dy,
        title=f"{str(root_node.get('title') or root_node.get('type') or 'Node')} {title_suffix}",
    )
    id_map[int(root_node["id"])] = root_clone_id
    clones.append(root_clone)

    for original_id in sorted(downstream_ids):
        original = node_map.get(original_id)
        if not original:
            continue
        clone_id = _next_id(workflow["nodes"] + clones)
        clone = _copy_node(
            original,
            new_id=clone_id,
            dx=dx,
            dy=dy,
            title=f"{str(original.get('title') or original.get('type') or 'Node')} {title_suffix}",
        )
        if str(original.get("type")) == "SaveImage":
            widget_values = list(clone.get("widgets_values") or [])
            if widget_values:
                widget_values[0] = f"{str(widget_values[0]).strip() or 'QwenTE_multi'}_{title_suffix.lower().replace(' ', '_')}"
                clone["widgets_values"] = widget_values
        id_map[original_id] = clone_id
        clones.append(clone)
    return id_map, clones


def _wire_copied_subgraph(
    workflow: dict[str, Any],
    *,
    original_root_id: int,
    copied_id_map: dict[int, int],
) -> None:
    for link in workflow.get("links", []):
        if not isinstance(link, list) or len(link) < 6:
            continue
        origin_id = int(link[1])
        target_id = int(link[3])
        if origin_id not in copied_id_map:
            continue
        if target_id not in copied_id_map:
            continue
        _append_link(
            workflow,
            origin_id=copied_id_map[origin_id],
            origin_slot=int(link[2]),
            target_id=copied_id_map[target_id],
            target_slot=int(link[4]),
            link_type=str(link[5]),
        )


def main() -> int:
    workflow = json.loads(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
    workflow = 旁路清理节点工作流(workflow)

    stage_node = _find_node(workflow, "QwenTE_StagePromptGenerator")
    positive_clip = _find_node(workflow, "CLIPTextEncode")
    negative_clip_candidates = _find_nodes(workflow, "CLIPTextEncode")
    ksampler = _find_node(workflow, "KSampler")

    if not stage_node or not positive_clip or not ksampler or len(negative_clip_candidates) < 2:
        raise RuntimeError("Bridge workflow missing stage node, CLIPTextEncode nodes, or KSampler")

    negative_clip = next(
        (node for node in negative_clip_candidates if str(node.get("title", "")).strip() == "QwenTE 推荐负面桥接"),
        negative_clip_candidates[1],
    )

    splitter_id = _next_id(workflow["nodes"])
    splitter_node = {
        "id": splitter_id,
        "type": "QwenTE_PromptCollectionSplitter",
        "pos": [
            float(stage_node.get("pos", [0, 0])[0] + 420),
            float(stage_node.get("pos", [0, 0])[1] + 60),
        ],
        "size": [320, 180],
        "flags": {},
        "order": max(int(node.get("order", 0)) for node in workflow["nodes"]) + 1,
        "mode": 0,
        "inputs": [
            {"name": "正向提示词合集", "type": "STRING", "link": None, "widget": {"name": "正向提示词合集"}},
            {"name": "分隔模式", "type": "STRING", "link": None, "widget": {"name": "分隔模式"}},
        ],
        "outputs": [
            {"name": "提示词1", "type": "STRING", "links": []},
            {"name": "提示词2", "type": "STRING", "links": []},
            {"name": "提示词3", "type": "STRING", "links": []},
            {"name": "提示词4", "type": "STRING", "links": []},
        ],
        "properties": {"Node name for S&R": "QwenTE_PromptCollectionSplitter"},
        "widgets_values": ["", "双换行"],
    }
    workflow["nodes"].append(splitter_node)
    workflow["last_node_id"] = max(int(workflow.get("last_node_id", 0)), splitter_id)

    _append_link(
        workflow,
        origin_id=int(stage_node["id"]),
        origin_slot=5,
        target_id=splitter_id,
        target_slot=0,
        link_type="STRING",
    )

    _remove_links_for_target(workflow, target_id=int(positive_clip["id"]), target_slot=1)
    _append_link(
        workflow,
        origin_id=splitter_id,
        origin_slot=0,
        target_id=int(positive_clip["id"]),
        target_slot=1,
        link_type="STRING",
    )

    downstream_ids = _collect_downstream_node_ids(workflow, int(ksampler["id"]))
    branch_specs = [
        {"slot": 1, "dx": 0.0, "dy": 340.0, "suffix": "P02"},
        {"slot": 2, "dx": 0.0, "dy": 680.0, "suffix": "P03"},
        {"slot": 3, "dx": 0.0, "dy": 1020.0, "suffix": "P04"},
    ]
    for spec in branch_specs:
        clip_id = _next_id(workflow["nodes"])
        clip_clone = _copy_node(
            positive_clip,
            new_id=clip_id,
            dx=spec["dx"],
            dy=spec["dy"],
            title=f"QwenTE 正向桥接 {spec['suffix']}",
        )
        workflow["nodes"].append(clip_clone)
        workflow["last_node_id"] = max(int(workflow.get("last_node_id", 0)), clip_id)

        copied_id_map, clones = _copy_downstream_subgraph(
            workflow,
            root_node=ksampler,
            downstream_ids=downstream_ids,
            dx=spec["dx"] + 320.0,
            dy=spec["dy"],
            title_suffix=spec["suffix"],
        )
        workflow["nodes"].extend(clones)
        workflow["last_node_id"] = max(
            int(workflow.get("last_node_id", 0)),
            max((int(node.get("id", 0)) for node in clones), default=0),
        )

        cloned_ksampler_id = copied_id_map[int(ksampler["id"])]
        _append_link(
            workflow,
            origin_id=splitter_id,
            origin_slot=spec["slot"],
            target_id=clip_id,
            target_slot=1,
            link_type="STRING",
        )
        _append_link(
            workflow,
            origin_id=int(negative_clip["id"]),
            origin_slot=0,
            target_id=cloned_ksampler_id,
            target_slot=2,
            link_type="CONDITIONING",
        )
        _append_link(
            workflow,
            origin_id=clip_id,
            origin_slot=0,
            target_id=cloned_ksampler_id,
            target_slot=1,
            link_type="CONDITIONING",
        )
        _wire_copied_subgraph(
            workflow,
            original_root_id=int(ksampler["id"]),
            copied_id_map=copied_id_map,
        )

    OUTPUT_WORKFLOW.write_text(json.dumps(workflow, ensure_ascii=False), encoding="utf-8")
    print(f"Created: {OUTPUT_WORKFLOW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
