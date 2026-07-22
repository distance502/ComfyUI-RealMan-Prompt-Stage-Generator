# -*- coding: utf-8 -*-
"""
Run stage prompt + image regression checks against a local ComfyUI instance.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = Path(__file__).resolve().parent
COMFY_BASE = "http://127.0.0.1:8188"
MODEL_LOADER_NODE_TYPE = "QwenTE_ModelLoader"
STAGE_NODE_TYPE = "QwenTE_StagePromptGenerator"
SHOW_TEXT_NODE_TYPE = "ShowText|pysssss"
IMAGE_WORKFLOW_PATH = ROOT / "user" / "default" / "workflows" / "Unsaved Workflow.json"
IMAGE_WORKFLOW_FALLBACK_PATHS = (
    ROOT / "user" / "default" / "workflows" / "Z-IMAGE电影光影工作流 by.TE.json",
    ROOT / "user" / "default" / "workflows" / "Kook_Zimage_瑶光.json",
)
REPORT_PATH = ROOT / "output" / "codex_stage_regression_report.json"
EXTERNAL_CASES_PATH = PLUGIN_ROOT / "tests" / "fixtures" / "regression_cases.json"
STYLE_MODE_CASES_PATH = PLUGIN_ROOT / "tests" / "fixtures" / "style_mode_cases.json"
CASE_GROUP_ORDER = ["realistic", "private", "sacred", "ancient", "cyber", "nonhuman", "conflict", "style_mode", "other"]
CONTROL_MARKERS = {"randomize", "fixed", "increment", "decrement"}
PRIVATE_SCENE_TERMS = {"卧室", "酒店氛围", "浴缸", "酒吧", "夜店", "晨光私房", "微醺夜色"}
OUTDOOR_SCENE_TERMS = {"校园", "林荫大道", "樱花树下", "街道", "海边", "海岸线", "公园"}
INDOOR_SCENE_TERMS = {"卧室", "酒店氛围", "落地窗夜景", "浴缸", "酒吧", "夜店", "厨房", "书房", "客厅"}
LENS_TERMS = {"35mm镜头", "50mm标准镜头", "85mm人像镜头", "广角", "超广角", "长焦", "定焦"}
BANNED_NOISE_PATTERNS = [
    re.compile(r"<\s*lora:[^>]+>", flags=re.IGNORECASE),
    re.compile(r"\bscore_[0-9]+(?:_up)?\b", flags=re.IGNORECASE),
    re.compile(r"\bembedding\s*:[^\s,;，；]+", flags=re.IGNORECASE),
]
MODEL_LOADER_PREFERRED_INPUTS = {
    "模型系列": "Qwen3.5-VL",
    "主模型": "Huihui-Qwen3-VL-8B-Instruct-abliterated.Q4_K_M.gguf",
    "视觉投影mmproj": "无",
}
CASES: list[dict[str, Any]] = []


def normalize_case_entry(item: Any, *, group_name: str | None = None) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get("name", "")).strip()
    stage = item.get("stage")
    expect = item.get("expect", {})
    if not name or not isinstance(stage, dict):
        return None
    if not isinstance(expect, dict):
        expect = {}
    normalized = dict(item)
    normalized["name"] = name
    normalized["stage"] = stage
    normalized["expect"] = expect
    normalized["image"] = bool(item.get("image", False))
    normalized["group"] = str(item.get("group", group_name or "other") or "other").strip() or "other"
    return normalized


def load_external_cases() -> list[dict[str, Any]]:
    if not EXTERNAL_CASES_PATH.exists():
        return []
    payload = json.loads(EXTERNAL_CASES_PATH.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        cases = payload.get("cases", [])
        case_groups = payload.get("case_groups", {})
    else:
        cases = payload
        case_groups = {}
    if not isinstance(cases, list):
        return []
    if not isinstance(case_groups, dict):
        case_groups = {}
    normalized: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for item in cases:
        item_name = str(item.get("name", "")).strip() if isinstance(item, dict) else ""
        normalized_item = normalize_case_entry(item, group_name=str(case_groups.get(item_name, "other") or "other"))
        if not normalized_item:
            continue
        if normalized_item["name"] in seen_names:
            continue
        seen_names.add(normalized_item["name"])
        normalized.append(normalized_item)
    return normalized


CASES.extend(load_external_cases())


def load_style_mode_cases() -> list[dict[str, Any]]:
    if not STYLE_MODE_CASES_PATH.exists():
        return []
    payload = json.loads(STYLE_MODE_CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return []
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        return []
    normalized: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for item in cases:
        normalized_item = normalize_case_entry(item, group_name="style_mode")
        if not normalized_item:
            continue
        normalized_item["group"] = "style_mode"
        if normalized_item["name"] in seen_names:
            continue
        seen_names.add(normalized_item["name"])
        normalized.append(normalized_item)
    return normalized


CASES.extend(load_style_mode_cases())


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run stage prompt regression cases against local ComfyUI.")
    parser.add_argument(
        "--case",
        action="append",
        dest="case_names",
        help="Only run the named regression case. Can be passed multiple times or with comma-separated names.",
    )
    parser.add_argument(
        "--group",
        action="append",
        dest="group_names",
        help="Only run regression cases from the named group. Can be passed multiple times or with comma-separated names.",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="List available regression case names and exit.",
    )
    parser.add_argument(
        "--report-suffix",
        help="Append a suffix to the default report filename, for example --report-suffix campus -> codex_stage_regression_report_campus.json",
    )
    parser.add_argument(
        "--output",
        help="Write the regression report to a specific file path instead of the default output location.",
    )
    return parser.parse_args(argv)


def resolve_requested_case_names(case_names: list[str] | None) -> list[str]:
    if not case_names:
        return []
    requested: list[str] = []
    seen: set[str] = set()
    for raw in case_names:
        for item in str(raw or "").split(","):
            name = item.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            requested.append(name)
    return requested


def resolve_requested_group_names(group_names: list[str] | None) -> list[str]:
    if not group_names:
        return []
    requested: list[str] = []
    seen: set[str] = set()
    for raw in group_names:
        for item in str(raw or "").split(","):
            name = item.strip()
            if not name:
                continue
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            requested.append(name)
    return requested


def resolve_case_name(cases: list[dict[str, Any]], query: str) -> str:
    normalized_query = str(query or "").strip()
    if not normalized_query:
        raise ValueError("Regression case query must not be empty.")

    names = list_case_names(cases)
    if normalized_query in names:
        return normalized_query

    query_key = normalized_query.casefold()
    lowered_map = {name.casefold(): name for name in names}
    if query_key in lowered_map:
        return lowered_map[query_key]

    prefix_matches = [name for name in names if name.casefold().startswith(query_key)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if len(prefix_matches) > 1:
        raise ValueError(
            f"Ambiguous regression case query '{normalized_query}'. Prefix matches: {', '.join(prefix_matches)}"
        )

    substring_matches = [name for name in names if query_key in name.casefold()]
    if len(substring_matches) == 1:
        return substring_matches[0]
    if len(substring_matches) > 1:
        raise ValueError(
            f"Ambiguous regression case query '{normalized_query}'. Substring matches: {', '.join(substring_matches)}"
        )

    available = ", ".join(sorted(names))
    raise ValueError(f"Unknown regression case '{normalized_query}'. Available: {available}")


def select_cases(cases: list[dict[str, Any]], requested_names: list[str] | None = None) -> list[dict[str, Any]]:
    normalized_names = resolve_requested_case_names(requested_names)
    if not normalized_names:
        return list(cases)
    case_map = {str(case.get("name", "")).strip(): case for case in cases}
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for requested_name in normalized_names:
        resolved_name = resolve_case_name(cases, requested_name)
        if resolved_name in seen:
            continue
        seen.add(resolved_name)
        selected.append(case_map[resolved_name])
    return selected


def list_group_names(cases: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for case in cases:
        name = str(case.get("group", "other") or "other").strip() or "other"
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    ordered: list[str] = []
    for group_name in CASE_GROUP_ORDER:
        if group_name in seen and group_name not in ordered:
            ordered.append(group_name)
    for group_name in names:
        if group_name not in ordered:
            ordered.append(group_name)
    return ordered


def resolve_group_name(cases: list[dict[str, Any]], query: str) -> str:
    normalized_query = str(query or "").strip()
    if not normalized_query:
        raise ValueError("Regression group query must not be empty.")

    groups = list_group_names(cases)
    if normalized_query in groups:
        return normalized_query

    query_key = normalized_query.casefold()
    lowered_map = {name.casefold(): name for name in groups}
    if query_key in lowered_map:
        return lowered_map[query_key]

    prefix_matches = [name for name in groups if name.casefold().startswith(query_key)]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if len(prefix_matches) > 1:
        raise ValueError(
            f"Ambiguous regression group query '{normalized_query}'. Prefix matches: {', '.join(prefix_matches)}"
        )

    substring_matches = [name for name in groups if query_key in name.casefold()]
    if len(substring_matches) == 1:
        return substring_matches[0]
    if len(substring_matches) > 1:
        raise ValueError(
            f"Ambiguous regression group query '{normalized_query}'. Substring matches: {', '.join(substring_matches)}"
        )

    available = ", ".join(groups)
    raise ValueError(f"Unknown regression group '{normalized_query}'. Available: {available}")


def filter_cases_by_group(cases: list[dict[str, Any]], requested_groups: list[str] | None = None) -> list[dict[str, Any]]:
    normalized_groups = resolve_requested_group_names(requested_groups)
    if not normalized_groups:
        return list(cases)
    resolved_groups = [resolve_group_name(cases, group_name) for group_name in normalized_groups]
    allowed = set(resolved_groups)
    return [case for case in cases if str(case.get("group", "other") or "other").strip() in allowed]


def list_case_names(cases: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for case in cases:
        name = str(case.get("name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names


def list_grouped_case_names(cases: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for case in cases:
        name = str(case.get("name", "")).strip()
        if not name:
            continue
        group = str(case.get("group", "other") or "other").strip() or "other"
        grouped.setdefault(group, [])
        if name not in grouped[group]:
            grouped[group].append(name)
    ordered: dict[str, list[str]] = {}
    for group_name in CASE_GROUP_ORDER:
        if group_name in grouped:
            ordered[group_name] = grouped[group_name]
    for group_name in sorted(grouped.keys()):
        if group_name not in ordered:
            ordered[group_name] = grouped[group_name]
    return ordered


def sanitize_report_suffix(suffix: str | None) -> str:
    text = str(suffix or "").strip()
    if not text:
        return ""
    text = re.sub(r"[\\/:\s]+", "_", text)
    text = re.sub(r"[^0-9A-Za-z_.-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._")
    return text


def resolve_report_path(*, default_path: Path, suffix: str | None = None, output: str | None = None) -> Path:
    if output:
        return Path(output).expanduser()
    normalized_suffix = sanitize_report_suffix(suffix)
    if not normalized_suffix:
        return default_path
    return default_path.with_name(f"{default_path.stem}_{normalized_suffix}{default_path.suffix}")


def get_json(url: str, timeout: int = 30) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def post_json(url: str, payload: dict[str, Any], timeout: int = 90) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="ignore"))


def build_prompt_map_from_workflow(workflow: dict[str, Any]) -> dict[str, dict[str, Any]]:
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


def resolve_image_workflow_path() -> Path:
    if IMAGE_WORKFLOW_PATH.exists():
        return IMAGE_WORKFLOW_PATH
    for fallback_path in IMAGE_WORKFLOW_FALLBACK_PATHS:
        if fallback_path.exists():
            return fallback_path
    raise FileNotFoundError(f"Missing image workflow template: {IMAGE_WORKFLOW_PATH}")


def resolve_prompt_text_node_ids(prompt_map: dict[str, dict[str, Any]]) -> tuple[str | None, str | None]:
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


def resolve_required_input_value(config: Any, *, preferred: Any = None) -> Any:
    if not (isinstance(config, list) and config):
        return preferred if preferred is not None else ""

    first = config[0]
    settings = config[1] if len(config) > 1 and isinstance(config[1], dict) else {}
    if isinstance(first, list):
        if preferred is not None and preferred in first:
            return preferred
        default = settings.get("default")
        if default in first:
            return default
        return first[0] if first else ""

    if preferred is not None:
        return preferred
    if "default" in settings:
        return settings["default"]
    if first == "STRING":
        return ""
    if first == "BOOLEAN":
        return False
    if first in {"INT", "FLOAT"}:
        return 0
    return ""


def build_required_input_defaults(
    required_inputs: dict[str, Any],
    *,
    links: dict[str, Any] | None = None,
    preferred: dict[str, Any] | None = None,
) -> dict[str, Any]:
    links = links or {}
    preferred = preferred or {}
    inputs: dict[str, Any] = {}
    for name, config in required_inputs.items():
        if name in links:
            inputs[name] = links[name]
            continue
        inputs[name] = resolve_required_input_value(config, preferred=preferred.get(name))
    return inputs


def build_stage_workflow(case: dict[str, Any]) -> tuple[dict[str, Any], str, str]:
    object_info = get_json(f"{COMFY_BASE}/object_info/{STAGE_NODE_TYPE}")[STAGE_NODE_TYPE]
    model_loader_info = get_json(f"{COMFY_BASE}/object_info/{MODEL_LOADER_NODE_TYPE}")[MODEL_LOADER_NODE_TYPE]
    stage_inputs = build_required_input_defaults(
        object_info["input"]["required"],
        links={"qwen模型": ["1", 0]},
    )
    model_loader_inputs = build_required_input_defaults(
        model_loader_info["input"]["required"],
        preferred=MODEL_LOADER_PREFERRED_INPUTS,
    )

    stage_inputs.update(case["stage"])
    stage_inputs["seed"] = int(stage_inputs.get("seed", random.randint(10**8, 10**12)))

    payload = {
        "client_id": "codex-stage-regression",
        "prompt": {
            "1": {
                "class_type": MODEL_LOADER_NODE_TYPE,
                "inputs": model_loader_inputs,
            },
            "2": {
                "class_type": STAGE_NODE_TYPE,
                "inputs": stage_inputs,
            },
            "3": {
                "class_type": SHOW_TEXT_NODE_TYPE,
                "inputs": {"text": ["2", 1]},
            },
            "4": {
                "class_type": SHOW_TEXT_NODE_TYPE,
                "inputs": {"text": ["2", 4]},
            },
        },
        "partial_execution_targets": ["3", "4"],
    }
    return payload, "3", "4"


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


def split_prompt_lines(text: str) -> list[str]:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    blocks = [block.strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()]
    if blocks:
        return blocks
    return [normalized.strip()] if normalized.strip() else []


def build_image_payload(prompt_text: str, *, negative_text: str, filename_prefix: str) -> dict[str, Any]:
    workflow = json.loads(resolve_image_workflow_path().read_text(encoding="utf-8"))
    prompt_map = build_prompt_map_from_workflow(workflow)
    positive_id, negative_id = resolve_prompt_text_node_ids(prompt_map)
    if positive_id is None:
        raise RuntimeError("No CLIPTextEncode node found for positive prompt injection")
    prompt_map[positive_id]["inputs"]["text"] = prompt_text
    if negative_id is not None:
        prompt_map[negative_id]["inputs"]["text"] = negative_text or "text, watermark, logo, signature, blurry, low quality"

    ksampler_ids = [
        node_id
        for node_id, payload in prompt_map.items()
        if payload.get("class_type") == "KSampler"
    ]
    if not ksampler_ids:
        raise RuntimeError("No KSampler node found in image workflow template")
    for node_id in ksampler_ids:
        sampler_inputs = prompt_map[node_id]["inputs"]
        sampler_inputs["seed"] = random.randint(10**10, 10**15)
        sampler_inputs["steps"] = 6

    for node_id, payload in prompt_map.items():
        if payload.get("class_type") == "ImpactInt":
            value = payload.get("inputs", {}).get("value")
            if value == 1920:
                payload["inputs"]["value"] = 1024
            elif value == 1080:
                payload["inputs"]["value"] = 576
        elif payload.get("class_type") == "EmptyLatentImage":
            latent_inputs = payload.get("inputs", {})
            if latent_inputs.get("width") == 1920:
                latent_inputs["width"] = 1024
            if latent_inputs.get("height") == 1080:
                latent_inputs["height"] = 576

    save_ids = [
        node_id
        for node_id, payload in prompt_map.items()
        if payload.get("class_type") == "SaveImage"
    ]
    if not save_ids:
        raise RuntimeError("No SaveImage node found in image workflow template")
    for node_id in save_ids:
        prompt_map[node_id]["inputs"]["filename_prefix"] = filename_prefix
    return {"client_id": "codex-stage-regression-image", "prompt": prompt_map}


def contains_noise(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in BANNED_NOISE_PATTERNS)


def evaluate_prompt(text: str, case: dict[str, Any]) -> dict[str, Any]:
    expected = case.get("expect", {})
    must_contain = [term for term in expected.get("must_contain", []) if term]
    must_not_contain = [term for term in expected.get("must_not_contain", []) if term]
    missing = [term for term in must_contain if term not in text]
    unexpected = [term for term in must_not_contain if term in text]
    selected_lenses = [term for term in must_contain if term in LENS_TERMS]
    found_lenses = [term for term in LENS_TERMS if term in text]
    private_scene_hit = [term for term in PRIVATE_SCENE_TERMS if term in text]
    return {
        "missing_terms": missing,
        "unexpected_terms": unexpected,
        "lens_terms": found_lenses,
        "private_scene_terms": private_scene_hit,
        "noise_hit": contains_noise(text),
        "ok": (not missing) and (not unexpected) and (not contains_noise(text)),
        "selected_lenses": selected_lenses,
    }


def run_stage_case(case: dict[str, Any]) -> dict[str, Any]:
    payload, output_node_id, negative_node_id = build_stage_workflow(case)
    submit = post_json(f"{COMFY_BASE}/prompt", payload)
    prompt_id = str(submit.get("prompt_id"))
    entry = poll_history(prompt_id, timeout_sec=1800)
    outputs = entry.get("outputs") or {}
    stage_text = ""
    negative_text = ""
    if isinstance(outputs.get(output_node_id), dict):
        text_blocks = outputs[output_node_id].get("text")
        if isinstance(text_blocks, list) and text_blocks:
            stage_text = str(text_blocks[0])
    if isinstance(outputs.get(negative_node_id), dict):
        text_blocks = outputs[negative_node_id].get("text")
        if isinstance(text_blocks, list) and text_blocks:
            negative_text = str(text_blocks[0])
    prompt_lines = split_prompt_lines(stage_text)
    evaluations = [evaluate_prompt(line, case) for line in prompt_lines]
    return {
        "prompt_id": prompt_id,
        "status": str((entry.get("status") or {}).get("status_str") or "unknown"),
        "raw_prompt_text": stage_text,
        "prompt_lines": prompt_lines,
        "negative_prompt": negative_text,
        "evaluations": evaluations,
    }


def run_image_case(prompt_text: str, *, negative_text: str, name: str) -> dict[str, Any]:
    filename_prefix = f"codex_stage_reg_{name}"
    submit = post_json(
        f"{COMFY_BASE}/prompt",
        build_image_payload(prompt_text, negative_text=negative_text, filename_prefix=filename_prefix),
    )
    prompt_id = str(submit.get("prompt_id"))
    entry = poll_history(prompt_id, timeout_sec=1800)
    images: list[str] = []
    for node_output in (entry.get("outputs") or {}).values():
        if not isinstance(node_output, dict):
            continue
        for image in node_output.get("images") or []:
            image_path = ROOT / str(image.get("type") or "output") / str(image.get("subfolder") or "") / str(image.get("filename") or "")
            images.append(str(image_path))
    return {
        "prompt_id": prompt_id,
        "status": str((entry.get("status") or {}).get("status_str") or "unknown"),
        "images": images,
    }


def build_style_mode_comparison_section(report: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparison: list[dict[str, Any]] = []
    for row in report:
        stage = row.get("stage")
        if not isinstance(stage, dict):
            continue
        evaluations = stage.get("evaluations") if isinstance(stage.get("evaluations"), list) else []
        evaluation_summary: dict[str, Any] = {
            "count": len(evaluations),
            "ok_count": sum(1 for item in evaluations if isinstance(item, dict) and item.get("ok")),
            "noise_hits": sum(1 for item in evaluations if isinstance(item, dict) and item.get("noise_hit")),
            "missing_terms": sorted(
                {
                    term
                    for item in evaluations
                    if isinstance(item, dict)
                    for term in item.get("missing_terms", [])
                    if term
                }
            ),
            "unexpected_terms": sorted(
                {
                    term
                    for item in evaluations
                    if isinstance(item, dict)
                    for term in item.get("unexpected_terms", [])
                    if term
                }
            ),
        }
        comparison.append(
            {
                "name": row.get("name"),
                "template_style": row.get("template_style")
                or stage.get("template_style")
                or stage.get("模板风格")
                or "",
                "prompt_text": row.get("prompt_text")
                or stage.get("prompt_text")
                or stage.get("raw_prompt_text")
                or "",
                "negative_text": row.get("negative_text")
                or stage.get("negative_text")
                or stage.get("negative_prompt")
                or "",
                "evaluation_summary": evaluation_summary,
            }
        )
    return comparison


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    filtered_cases = filter_cases_by_group(CASES, args.group_names)
    if args.list_cases:
        for group_name, names in list_grouped_case_names(filtered_cases).items():
            print(f"[{group_name}]")
            for name in names:
                print(name)
        return 0
    cases = select_cases(filtered_cases, args.case_names)
    report_path = resolve_report_path(default_path=REPORT_PATH, suffix=args.report_suffix, output=args.output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report: list[dict[str, Any]] = []
    selected_groups = {str(case.get("group", "other") or "other").strip() or "other" for case in cases}
    for index, case in enumerate(cases, start=1):
        record: dict[str, Any] = {
            "index": index,
            "name": case["name"],
        }
        try:
            stage_result = run_stage_case(case)
            record["stage"] = stage_result
            if case.get("group") == "style_mode":
                record["template_style"] = case.get("stage", {}).get("模板风格", "")
                record["prompt_text"] = stage_result.get("raw_prompt_text", "")
                record["negative_text"] = stage_result.get("negative_prompt", "")
            if case.get("image") and stage_result["prompt_lines"]:
                record["image"] = run_image_case(
                    stage_result["prompt_lines"][0],
                    negative_text=stage_result.get("negative_prompt", ""),
                    name=case["name"],
                )
        except Exception as exc:
            record["error"] = repr(exc)
        report.append(record)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        if "stage" in record:
            print(f"[{index}/{len(cases)}] {case['name']} stage={record['stage']['status']} lines={len(record['stage']['prompt_lines'])} image={bool(case.get('image'))}")
        else:
            print(f"[{index}/{len(cases)}] {case['name']} error={record['error']}")

    if selected_groups == {"style_mode"}:
        style_mode_section = build_style_mode_comparison_section(report)
        if report:
            report[-1]["style_mode_comparison"] = style_mode_section
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"REPORT {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
