# -*- coding: utf-8 -*-
"""Output formatting helpers for stage prompt generation."""

from __future__ import annotations

from collections import OrderedDict
import json
import time
import urllib.parse
from typing import Any, Callable


_NEGATIVE_SAFETY_DISPLAY_MARKERS = (
    "未成年",
    "幼态",
    "萝莉感",
    "课堂情境",
    "校规情境",
    "违法暗示",
    "强迫暗示",
    "暴力羞辱",
    "露骨器官",
    "underage",
    "childlike",
    "loli",
    "classroom",
    "school discipline",
    "illegal",
    "forced",
    "violent humiliation",
    "explicit organ",
)


def _normalize_model_source_label(value: Any) -> str:
    source = str(value or "").strip()
    if not source:
        return "仅Skill"
    if source.startswith("本地"):
        suffix_index = source.find("（")
        suffix = source[suffix_index:] if suffix_index >= 0 else ""
        return f"本地模型{suffix}"
    return source


def _split_negative_terms(negative_prompt: str) -> tuple[list[str], str]:
    if "、" in negative_prompt:
        return [part.strip() for part in negative_prompt.split("、")], "、"
    return [part.strip() for part in negative_prompt.split(",")], ", "


def summarize_negative_prompt_for_display(negative_prompt: str) -> str:
    """Hide verbose safety guard terms in readable summaries without changing the real output."""

    prompt = str(negative_prompt or "").strip()
    if not prompt:
        return ""

    terms, separator = _split_negative_terms(prompt)
    visible_terms: list[str] = []
    removed_safety = False
    for term in terms:
        if not term:
            continue
        term_folded = term.casefold()
        if any(marker.casefold() in term_folded for marker in _NEGATIVE_SAFETY_DISPLAY_MARKERS):
            removed_safety = True
            continue
        visible_terms.append(term)

    if removed_safety:
        notice = "成人安全护栏已启用" if separator == "、" else "adult safety guardrails enabled"
        if notice not in visible_terms:
            visible_terms.append(notice)
    return separator.join(visible_terms)


def _model_skill_pipeline_label(settings: dict[str, Any]) -> str:
    source = _normalize_model_source_label(settings.get("模型来源", "仅Skill"))
    fallback_note = str(settings.get("模型回退说明", "") or "").strip()
    call_status = str(settings.get("模型调用状态", "") or "").strip()
    if fallback_note:
        return f"{call_status or '已回退仅Skill'}：{fallback_note}"
    if source == "仅Skill":
        return "仅Skill：不调用模型，本地Skill直接输出"
    if source == "API接口":
        provider = str(settings.get("API服务商有效", settings.get("API服务商", "")) or "").strip()
        model = str(settings.get("API模型有效", settings.get("API模型", "")) or "").strip()
        api_label = " / ".join(part for part in (provider, model) if part)
        return f"Skill前置 + API模型后置润色{f'（{api_label}）' if api_label else ''}"
    model_name = str(settings.get("内置主模型", "") or "").strip()
    return f"Skill前置 + 本地模型后置润色{f'（{model_name}）' if model_name else ''}"


def _safe_model_api_base_url(raw_url: Any) -> str:
    text = str(raw_url or "").strip()
    if not text or any(char.isspace() for char in text):
        return ""
    try:
        parsed = urllib.parse.urlsplit(text)
        port = parsed.port
    except (TypeError, ValueError):
        return ""
    scheme = str(parsed.scheme or "").lower()
    hostname = str(parsed.hostname or "").strip()
    if scheme not in {"http", "https"} or not hostname:
        return ""
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        return ""
    path = str(parsed.path or "").rstrip("/")
    decoded_path = urllib.parse.unquote(path)
    path_segments = [segment for segment in decoded_path.split("/") if segment]
    if (
        "\\" in decoded_path
        or any(segment in {".", ".."} for segment in path_segments)
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 or ord(char) > 127 for char in decoded_path)
    ):
        return ""
    try:
        host = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError:
        return ""
    if (scheme == "https" and port == 443) or (scheme == "http" and port == 80):
        port = None
    host_text = f"[{host}]" if ":" in host else host
    origin = f"{scheme}://{host_text}{f':{port}' if port is not None else ''}"
    return f"{origin}{path if path and path != '/' else ''}"


def _model_api_config_meta(settings: dict[str, Any]) -> tuple[str, str, str, str]:
    source = _normalize_model_source_label(settings.get("模型来源", "仅Skill"))
    if source != "API接口":
        return "", "", "", ""
    provider = str(settings.get("API服务商有效", settings.get("API服务商", "")) or "").strip()
    base_url = _safe_model_api_base_url(
        settings.get("API地址有效", settings.get("API地址", ""))
    )
    model = str(settings.get("API模型有效", settings.get("API模型", "")) or "").strip()
    key_reference = str(settings.get("API密钥", "") or "").strip()
    extra_headers = str(settings.get("API额外请求头", "") or "").strip().replace("\r\n", "\n").replace("\r", "\n")
    canonical = json.dumps(
        [source, provider, base_url, model, key_reference, extra_headers],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest = 0xCBF29CE484222325
    for byte in canonical.encode("utf-16le"):
        digest ^= byte
        digest = (digest * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return provider, base_url, model, f"model-api-v1:{digest:016x}"


def build_selected_tags_text(
    *,
    template_style: str,
    subject_type: str,
    output_structure: str,
    runtime_random_enabled: bool,
    settings: dict[str, Any],
    adult_subpool: str,
    scene_group: str,
    identity: str,
    style_track: str,
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    recent_tracks: list[str],
    negative_prompt: str,
    format_grouped_summary: Callable[[OrderedDict[str, list[str]], list[str]], str],
) -> str:
    display_negative_prompt = summarize_negative_prompt_for_display(negative_prompt)
    model_source = _normalize_model_source_label(settings.get("模型来源", "仅Skill"))
    model_source_effective = _normalize_model_source_label(
        settings.get("模型来源实际", model_source) or model_source
    )
    return "\n".join(
        [
            f"模板风格：{template_style}",
            f"主体类型：{subject_type}",
            f"案例输出结构：{output_structure}",
            f"运行时随机标签：{'开启' if runtime_random_enabled else '关闭'}",
            f"运行时随机模式：{settings['运行时随机模式']}",
            f"运行时随机模式解析：{settings.get('运行时随机模式解析结果', '') or '未触发'}",
            f"核心标签锁定数量：{settings['核心标签锁定数量']}",
            f"运行时随机强度：{settings['运行时随机强度']}",
            f"随机主题池：{settings.get('随机主题池', '自动')}",
            f"标签反推模式：{settings['标签反推模式']}",
            f"NSFW策略状态：{'开启' if settings.get('NSFW策略启用', False) else '关闭'} / {settings.get('NSFW策略来源', '') or '无'}",
            f"风格隔离策略：{settings.get('风格隔离策略', '平衡收敛')}",
            f"模型来源：{model_source}",
            f"模型实际来源：{model_source_effective}",
            f"模型调用状态：{settings.get('模型调用状态', '未记录')}",
            f"图片反推状态：{settings.get('图片反推状态', '未启用')}",
            f"模型与Skill链路：{_model_skill_pipeline_label(settings)}",
            f"NSFW Skill解析：{settings.get('NSFW策略解析结果', '') or '未触发'}",
            f"智能文本风格优先：{settings.get('智能文本风格优先', '自动判断')}",
            f"智能文本风格解析：{settings.get('智能文本风格优先解析结果', '自动判断')} / {settings.get('智能文本风格解析结果', '') or '未触发'}",
            f"随机诊断：成人池 {adult_subpool or 'none'} | 片场组 {scene_group} | 主身份 {identity or 'none'} | 轨道 {style_track}",
            f"推理纠偏：{' | '.join(settings.get('推理纠偏说明', [])) if settings.get('推理纠偏说明') else '无'}",
            format_grouped_summary(selected, custom_tags),
            f"最近轨道：{' → '.join(recent_tracks) if recent_tracks else '无'}",
            f"推荐负面词：{display_negative_prompt}",
        ]
    )


def build_json_payload(
    *,
    full_text: str,
    prompt_only: str,
    prompt_list: list[str],
    selected_tags_text: str,
    selected: OrderedDict[str, list[str]],
    tags: list[str],
    template_style: str,
    subject_type: str,
    output_structure: str,
    runtime_random_enabled: bool,
    settings: dict[str, Any],
    generated: list[str],
    lock_tag_whitelist: list[str],
    random_exclude_tags: list[str],
    scene_group: str,
    identity: str,
    adult_subpool: str,
    style_track: str,
    recent_tracks: list[str],
    negative_prompt: str,
    smart_text_prompt: str = "",
) -> dict[str, Any]:
    display_negative_prompt = summarize_negative_prompt_for_display(negative_prompt)
    model_api_provider, model_api_base_url, model_api_model, model_config_signature = _model_api_config_meta(settings)
    model_source = _normalize_model_source_label(settings.get("模型来源", "仅Skill"))
    model_source_effective = _normalize_model_source_label(
        settings.get("模型来源实际", model_source) or model_source
    )
    return {
        "full_text": full_text,
        "prompt_text": prompt_only,
        "prompt_list": prompt_list,
        "prompt_collection": "\n\n".join(prompt_list),
        "smart_text_prompt": str(smart_text_prompt or ""),
        "selected_tags_text": selected_tags_text,
        "selected_tags_by_category": {key: list(value) for key, value in selected.items()},
        "selected_tags_flat": tags,
        "template_style": template_style,
        "subject_type": subject_type,
        "output_structure": output_structure,
        "runtime_random_enabled": runtime_random_enabled,
        "runtime_random_mode": str(settings["运行时随机模式"]),
        "runtime_random_mode_resolved": str(settings.get("运行时随机模式解析结果", "") or ""),
        "runtime_random_intensity": str(settings["运行时随机强度"]),
        "runtime_random_theme_pool": str(settings.get("随机主题池", "自动")),
        "style_isolation_mode": str(settings.get("风格隔离策略", "平衡收敛") or "平衡收敛"),
        "global_creative_spine": dict(settings.get("全局创作主线合同", {}) or {}),
        "global_creative_spine_summary": str(settings.get("全局创作主线摘要", "") or ""),
        "model_source": model_source,
        "model_source_effective": model_source_effective,
        "model_fallback_note": str(settings.get("模型回退说明", "") or ""),
        "model_call_status": str(settings.get("模型调用状态", "") or ""),
        "model_call_attempt_count": int(settings.get("模型调用尝试次数", 0) or 0),
        "model_call_success_count": int(settings.get("模型调用成功次数", 0) or 0),
        "model_call_failure_count": int(settings.get("模型调用失败次数", 0) or 0),
        "model_call_adopted_count": int(settings.get("模型调用采纳次数", 0) or 0),
        "model_active_fallback_count": int(settings.get("模型活动回退数量", 0) or 0),
        "model_transport_retry_count": int(settings.get("模型传输重试次数", 0) or 0),
        "model_last_transient_error": str(settings.get("模型最近瞬时错误", "") or ""),
        "image_reverse_status": str(settings.get("图片反推状态", "未启用") or "未启用"),
        "image_reverse_error": str(settings.get("图片反推错误", "") or ""),
        "model_call_errors": [str(item) for item in settings.get("模型调用错误", []) if str(item).strip()],
        "model_skill_pipeline": _model_skill_pipeline_label(settings),
        "model_api_provider": model_api_provider,
        "model_api_base_url": model_api_base_url,
        "model_api_model": model_api_model,
        "model_config_signature": model_config_signature,
        "nsfw_skill_strategy": str(settings.get("NSFW策略解析结果", "") or ""),
        "skill_dynamic_strategy": str(settings.get("Skill动态变化策略", "") or ""),
        "recent_prompt_fingerprint_count": len([item for item in settings.get("最近提示词指纹", []) if str(item).strip()]),
        "locked_core_tag_count": int(settings["核心标签锁定数量"]),
        "lock_tag_whitelist": list(lock_tag_whitelist),
        "random_exclude_tags": list(random_exclude_tags),
        "runtime_random_generated_tags": generated,
        "runtime_random_main_scene_group": scene_group,
        "runtime_random_main_identity": identity,
        "runtime_random_adult_subpool": adult_subpool,
        "runtime_random_style_track": style_track,
        "normalization_notes": list(settings.get("推理纠偏说明", [])),
        "recent_style_tracks": recent_tracks,
        "requested_generation_count": int(settings["生成数量"]),
        "effective_generation_count": int(settings["生成数量"]),
        "random_detail_count_clamped": False,
        "prefer_soft_skin": bool(settings["优先柔和肤质"]),
        "suppress_text_artifacts": bool(settings["抑制文字伪影"]),
        "generation_count": int(settings["生成数量"]),
        "prompt_language": str(settings["提示词语言"]),
        "detail_level": str(settings["详细度"]),
        "output_mode": str(settings["输出模式"]),
        "extra_requirement": str(settings.get("额外要求", "") or ""),
        "style_isolation_mode_display": str(settings.get("风格隔离策略", "平衡收敛") or "平衡收敛"),
        "smart_text_style_priority": str(settings.get("智能文本风格优先", "自动判断") or "自动判断"),
        "smart_text_style_priority_resolved": str(settings.get("智能文本风格优先解析结果", "") or ""),
        "smart_text_style_resolved": str(settings.get("智能文本风格解析结果", "") or ""),
        "negative_prompt_recommendation": negative_prompt,
        "negative_prompt_display": display_negative_prompt,
        "negative_prompt_language": str(settings["提示词语言"]),
    }


def _json_cache_meta(json_result: str) -> dict[str, Any]:
    text = str(json_result or "").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_cache_payload(
    *,
    full_text: str = "",
    primary_prompt: str = "",
    prompt_only: str,
    prompt_collection: str = "",
    selected_tags_text: str,
    json_result: str,
    negative_prompt: str,
    style_track: str,
    smart_text_prompt: str = "",
) -> dict[str, Any]:
    positive_prompt = str(primary_prompt or "").strip()
    collection = str(prompt_collection or prompt_only or "").strip()
    if not positive_prompt and collection:
        positive_prompt = collection.split("\n\n", 1)[0].strip()
    full = str(full_text or "").strip()
    smart = str(smart_text_prompt or "").strip()
    json_meta = _json_cache_meta(json_result)
    outputs = [
        full,
        positive_prompt,
        str(selected_tags_text or "").strip(),
        str(json_result or "").strip(),
        str(negative_prompt or "").strip(),
        collection,
        smart,
    ]
    return {
        "status": "done",
        "updated_at": int(time.time() * 1000),
        "full_text": full,
        "prompt_text": positive_prompt,
        "prompt_collection": collection,
        "smart_text_prompt": smart,
        "selected_tags_text": selected_tags_text,
        "json_result": json_result,
        "negative_prompt": negative_prompt,
        "runtime_random_style_track": style_track,
        "runtime_random_mode_resolved": str(json_meta.get("runtime_random_mode_resolved", "") or ""),
        "smart_text_style_priority_resolved": str(json_meta.get("smart_text_style_priority_resolved", "") or ""),
        "smart_text_style_resolved": str(json_meta.get("smart_text_style_resolved", "") or ""),
        "model_skill_pipeline": str(json_meta.get("model_skill_pipeline", "") or ""),
        "model_call_status": str(json_meta.get("model_call_status", "") or ""),
        "model_call_attempt_count": int(json_meta.get("model_call_attempt_count", 0) or 0),
        "model_call_success_count": int(json_meta.get("model_call_success_count", 0) or 0),
        "model_call_failure_count": int(json_meta.get("model_call_failure_count", 0) or 0),
        "model_call_adopted_count": int(json_meta.get("model_call_adopted_count", 0) or 0),
        "skill_dynamic_strategy": str(json_meta.get("skill_dynamic_strategy", "") or ""),
        "model_active_fallback_count": int(json_meta.get("model_active_fallback_count", 0) or 0),
        "image_reverse_status": str(json_meta.get("image_reverse_status", "") or ""),
        "recent_prompt_fingerprint_count": int(json_meta.get("recent_prompt_fingerprint_count", 0) or 0),
        "normalization_notes": list(json_meta.get("normalization_notes", [])) if isinstance(json_meta.get("normalization_notes"), list) else [],
        "outputs": outputs,
    }
