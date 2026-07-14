# -*- coding: utf-8 -*-
"""
Prune the bridge workflow down to the nodes required for stage-prompt image generation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__:
    from .workflow_cleanup import 旁路清理节点工作流
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from workflow_cleanup import 旁路清理节点工作流


ROOT = Path(__file__).resolve().parents[2]
SOURCE_WORKFLOW = ROOT / "user" / "default" / "workflows" / "QwenTE_阶段节点正负桥接生图.json"
OUTPUT_WORKFLOW = ROOT / "user" / "default" / "workflows" / "QwenTE_阶段节点精简生图.json"


def _find_nodes_by_type(workflow: dict[str, Any], node_type: str) -> list[dict[str, Any]]:
    return [node for node in workflow.get("nodes", []) if str(node.get("type")) == node_type]


def _reachable_node_ids(workflow: dict[str, Any], seed_ids: set[int]) -> set[int]:
    links = {
        int(link[0]): (int(link[1]), int(link[2]), int(link[3]), int(link[4]))
        for link in workflow.get("links", [])
        if isinstance(link, list) and len(link) >= 5
    }
    node_map = {int(node.get("id")): node for node in workflow.get("nodes", [])}
    keep = set(seed_ids)
    stack = list(seed_ids)
    while stack:
        node_id = stack.pop()
        node = node_map.get(node_id)
        if not node:
            continue
        for input_slot in node.get("inputs", []) or []:
            if not isinstance(input_slot, dict):
                continue
            link_id = input_slot.get("link")
            if not isinstance(link_id, int) or link_id not in links:
                continue
            origin_id = int(links[link_id][0])
            if origin_id in keep:
                continue
            keep.add(origin_id)
            stack.append(origin_id)
    return keep


def _trim_workflow(workflow: dict[str, Any], keep_ids: set[int]) -> dict[str, Any]:
    trimmed = json.loads(json.dumps(workflow))
    trimmed["nodes"] = [node for node in trimmed.get("nodes", []) if int(node.get("id")) in keep_ids]
    keep_link_ids: set[int] = set()
    next_links = []
    for link in trimmed.get("links", []):
        if not isinstance(link, list) or len(link) < 5:
            continue
        origin_id = int(link[1])
        target_id = int(link[3])
        if origin_id not in keep_ids or target_id not in keep_ids:
            continue
        keep_link_ids.add(int(link[0]))
        next_links.append(link)
    trimmed["links"] = next_links
    for node in trimmed.get("nodes", []):
        for output in node.get("outputs", []) or []:
            if isinstance(output, dict):
                output["links"] = [link_id for link_id in (output.get("links") or []) if int(link_id) in keep_link_ids]
        for input_slot in node.get("inputs", []) or []:
            if isinstance(input_slot, dict) and isinstance(input_slot.get("link"), int) and int(input_slot["link"]) not in keep_link_ids:
                input_slot["link"] = None
    trimmed["last_node_id"] = max((int(node.get("id", 0)) for node in trimmed.get("nodes", [])), default=0)
    trimmed["last_link_id"] = max((int(link[0]) for link in trimmed.get("links", [])), default=0)
    return trimmed


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


def _append_link(workflow: dict[str, Any], *, origin_id: int, origin_slot: int, target_id: int, target_slot: int, link_type: str) -> None:
    next_link_id = max((int(link[0]) for link in workflow.get("links", []) if isinstance(link, list) and link), default=0) + 1
    workflow["links"].append([next_link_id, origin_id, origin_slot, target_id, target_slot, link_type])
    workflow["last_link_id"] = next_link_id
    for node in workflow.get("nodes", []):
        if int(node.get("id", -1)) == origin_id:
            outputs = node.get("outputs", []) or []
            if len(outputs) > origin_slot and isinstance(outputs[origin_slot], dict):
                outputs[origin_slot]["links"] = list(outputs[origin_slot].get("links") or []) + [next_link_id]
        if int(node.get("id", -1)) == target_id:
            inputs = node.get("inputs", []) or []
            if len(inputs) > target_slot and isinstance(inputs[target_slot], dict):
                inputs[target_slot]["link"] = next_link_id


def _simplify_latent_branch(workflow: dict[str, Any]) -> dict[str, Any]:
    node_map = {int(node.get("id")): node for node in workflow.get("nodes", [])}
    ksampler = next((node for node in workflow.get("nodes", []) if str(node.get("type")) == "KSampler"), None)
    latent = node_map.get(33)
    if not ksampler or not latent:
        return workflow

    _remove_links_for_target(workflow, target_id=int(ksampler["id"]), target_slot=3)
    _append_link(workflow, origin_id=int(latent["id"]), origin_slot=0, target_id=int(ksampler["id"]), target_slot=3, link_type="LATENT")

    remove_ids = {7, 32, 34, 39}
    workflow["nodes"] = [node for node in workflow.get("nodes", []) if int(node.get("id", -1)) not in remove_ids]
    workflow["links"] = [
        link for link in workflow.get("links", [])
        if isinstance(link, list) and int(link[1]) not in remove_ids and int(link[3]) not in remove_ids
    ]
    workflow["last_node_id"] = max((int(node.get("id", 0)) for node in workflow.get("nodes", [])), default=0)
    workflow["last_link_id"] = max((int(link[0]) for link in workflow.get("links", [])), default=0)
    return workflow


def main() -> int:
    workflow = json.loads(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
    workflow = 旁路清理节点工作流(workflow)
    save_nodes = _find_nodes_by_type(workflow, "SaveImage")
    stage_nodes = _find_nodes_by_type(workflow, "QwenTE_StagePromptGenerator")
    if not save_nodes or not stage_nodes:
        raise RuntimeError("Bridge workflow missing SaveImage or stage node")

    seed_ids = {int(save_nodes[0]["id"]), int(stage_nodes[0]["id"])}
    keep_ids = _reachable_node_ids(workflow, seed_ids)
    trimmed = _trim_workflow(workflow, keep_ids)
    trimmed = _simplify_latent_branch(trimmed)
    OUTPUT_WORKFLOW.write_text(json.dumps(trimmed, ensure_ascii=False), encoding="utf-8")
    print(f"Created: {OUTPUT_WORKFLOW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
