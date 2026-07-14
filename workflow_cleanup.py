# -*- coding: utf-8 -*-
"""
Helpers for stripping passthrough cleanup nodes from ComfyUI workflow/prompt JSON.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


默认清理节点类型 = {
    "RAMCleanup",
    "VRAMCleanup",
    "easy cleanGpuUsed",
}


def _工作流下一链接ID(workflow: dict[str, Any]) -> int:
    existing = [
        int(link[0])
        for link in workflow.get("links", [])
        if isinstance(link, list) and len(link) >= 1 and isinstance(link[0], int | float)
    ]
    return max(existing, default=0) + 1


def _重建工作流链接索引(workflow: dict[str, Any]) -> None:
    incoming_map: dict[tuple[int, int], int] = {}
    outgoing_map: dict[tuple[int, int], list[int]] = {}
    for link in workflow.get("links", []):
        if not isinstance(link, list) or len(link) < 5:
            continue
        link_id = int(link[0])
        origin_id = int(link[1])
        origin_slot = int(link[2])
        target_id = int(link[3])
        target_slot = int(link[4])
        incoming_map[(target_id, target_slot)] = link_id
        outgoing_map.setdefault((origin_id, origin_slot), []).append(link_id)

    for node in workflow.get("nodes", []):
        node_id = int(node.get("id", -1))
        for slot_index, input_slot in enumerate(node.get("inputs", []) or []):
            if isinstance(input_slot, dict) and "link" in input_slot:
                input_slot["link"] = incoming_map.get((node_id, slot_index))
        for slot_index, output_slot in enumerate(node.get("outputs", []) or []):
            if isinstance(output_slot, dict):
                output_slot["links"] = list(outgoing_map.get((node_id, slot_index), []))

    workflow["last_node_id"] = max((int(node.get("id", 0)) for node in workflow.get("nodes", [])), default=0)
    workflow["last_link_id"] = max(
        (int(link[0]) for link in workflow.get("links", []) if isinstance(link, list) and len(link) >= 1),
        default=0,
    )


def 旁路清理节点工作流(
    workflow: dict[str, Any],
    cleanup_types: Iterable[str] | None = None,
) -> dict[str, Any]:
    cleanup_set = {str(item) for item in (cleanup_types or 默认清理节点类型)}
    links = [
        list(link)
        for link in workflow.get("links", [])
        if isinstance(link, list) and len(link) >= 5
    ]
    next_link_id = _工作流下一链接ID(workflow)
    remove_node_ids: set[int] = set()

    for node in list(workflow.get("nodes", [])):
        node_type = str(node.get("type"))
        node_id = int(node.get("id", -1))
        if node_type not in cleanup_set or node_id < 0:
            continue

        incoming_links = [link for link in links if int(link[3]) == node_id]
        outgoing_links = [link for link in links if int(link[1]) == node_id]
        passthrough_source = incoming_links[0] if incoming_links else None

        if passthrough_source is not None:
            origin_id = int(passthrough_source[1])
            origin_slot = int(passthrough_source[2])
            for out_link in outgoing_links:
                target_id = int(out_link[3])
                target_slot = int(out_link[4])
                link_type = out_link[5] if len(out_link) > 5 else ""
                duplicate = any(
                    isinstance(existing, list)
                    and len(existing) >= 6
                    and int(existing[1]) == origin_id
                    and int(existing[2]) == origin_slot
                    and int(existing[3]) == target_id
                    and int(existing[4]) == target_slot
                    and existing[5] == link_type
                    for existing in links
                )
                if duplicate:
                    continue
                links.append([next_link_id, origin_id, origin_slot, target_id, target_slot, link_type])
                next_link_id += 1

        links = [
            link
            for link in links
            if int(link[1]) != node_id and int(link[3]) != node_id
        ]
        remove_node_ids.add(node_id)

    if remove_node_ids:
        workflow["nodes"] = [
            node for node in workflow.get("nodes", [])
            if int(node.get("id", -1)) not in remove_node_ids
        ]
        workflow["links"] = links
        _重建工作流链接索引(workflow)
    return workflow


def 旁路清理节点提示图(
    prompt: dict[str, Any],
    cleanup_types: Iterable[str] | None = None,
) -> dict[str, Any]:
    cleanup_set = {str(item) for item in (cleanup_types or 默认清理节点类型)}
    remove_keys: list[str] = []

    for node_key, node in list(prompt.items()):
        if not isinstance(node, dict):
            continue
        if str(node.get("class_type")) not in cleanup_set:
            continue
        inputs = node.get("inputs", {}) or {}
        source = inputs.get("anything")
        if not isinstance(source, list) or len(source) < 2:
            remove_keys.append(str(node_key))
            continue
        source_node = str(source[0])
        source_slot = int(source[1])
        cleanup_key = str(node_key)

        for target_node in prompt.values():
            if not isinstance(target_node, dict):
                continue
            target_inputs = target_node.get("inputs", {}) or {}
            for input_name, input_value in list(target_inputs.items()):
                if isinstance(input_value, list) and len(input_value) >= 2 and str(input_value[0]) == cleanup_key:
                    target_inputs[input_name] = [source_node, source_slot]
        remove_keys.append(cleanup_key)

    for node_key in remove_keys:
        prompt.pop(node_key, None)
    return prompt
