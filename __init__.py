# -*- coding: utf-8 -*-
"""
ComfyUI Qwen3/Qwen3.5 llama TE 插件入口。
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from functools import wraps
from pathlib import Path
from typing import Any

try:
    from aiohttp import web
except Exception:
    web = None

try:
    import folder_paths
except Exception:
    folder_paths = None

from .prompt_tag_library import (
    前端标签库数据,
    删除自定义标签,
    添加自定义标签,
    批量添加自定义标签,
    推荐自定义标签归类,
)
from .stage_prompt_generator import (
    QwenTE阶段式提示词生成器,
    构建NSFW工作台目录,
    构建状态可视化预览,
    构建运行时随机预览状态,
    获取阶段节点输出缓存,
)

_QUALITY_AUDIT_IMPORT_ERROR: Exception | None = None
try:
    from .quality_audit_ocr_skin import audit_images, build_markdown as build_quality_markdown, collect_recent_output_images
except Exception as exc:
    _QUALITY_AUDIT_IMPORT_ERROR = exc
    _QUALITY_AUDIT_IMPORT_ERROR_TEXT = f"{type(exc).__name__}: {exc}"
    logging.warning(
        "QwenTE 质检功能依赖缺失，主节点将继续加载；缺少依赖: %s: %s",
        type(exc).__name__,
        exc,
    )

    def collect_recent_output_images(*_args, **_kwargs):
        return []

    def audit_images(_image_paths):
        return {
            "summary": {
                "total_images": 0,
                "ocr_risk_images": 0,
                "wrinkle_risk_images": 0,
                "oversmooth_risk_images": 0,
            },
            "images": [],
            "dependency_missing": True,
            "message": f"质检功能依赖缺失：{_QUALITY_AUDIT_IMPORT_ERROR_TEXT}",
        }

    def build_quality_markdown(result):
        message = str((result or {}).get("message") or f"质检功能依赖缺失：{_QUALITY_AUDIT_IMPORT_ERROR_TEXT}").strip()
        return f"# 质检功能不可用\n\n- {message}\n- 请安装 `opencv-python` 与 `rapidocr-onnxruntime` 后再使用质检。"

WEB_DIRECTORY = "./web"

_ROUTES_FLAG = "_qwen_te_routes_registered"
_INIT_HOOK_FLAG = "_qwen_te_routes_init_hook_registered"

_在线提示词片段分隔模式 = re.compile(r"[,\n\r\t;；，、|]+")
_在线提示词空白模式 = re.compile(r"\s+")
_在线提示词权重尾巴模式 = re.compile(r"[:：]\s*[-+]?\d+(?:\.\d+)?$")
_在线提示词命令参数模式 = re.compile(
    r"\s--(?:ar|stylize|style|v|chaos|no|iw|q|s|seed)\b(?:\s+(?!--)[^,\n\r;|]+)*",
    flags=re.IGNORECASE,
)
_在线提示词URL模式 = re.compile(r"^(?:https?://|www\.)", flags=re.IGNORECASE)
_在线提示词句读分隔模式 = re.compile(r"[。！？.!?/\\]+")
_在线英文短语模式 = re.compile(r"[A-Za-z][A-Za-z0-9'\-/ ]{1,50}")
_在线中文检测模式 = re.compile(r"[\u4e00-\u9fff]")
_在线噪声关键词模式 = re.compile(
    r"(duckduckgo|prompthero|url\s*source|markdown\s*content|search\s*results?|prompt\s*tags?|at\s+duckduckgo|snippet|result\s*page|please\s*try\s*again|unexpected\s*error|please\s*shorten(?:\s+and)?\s*try\s*again|search\s*query\s*entered\s*was\s*too\s*long|cached\s*snapshot|caching\s*opt-?out|consider\s*retry\s*with\s*caching\s*opt-?out|discover\s+millions\s+of\s+ai-generated)",
    flags=re.IGNORECASE,
)
_在线噪声短词集合 = {
    "prompt",
    "tags",
    "results",
    "search",
    "duckduckgo",
    "please",
    "try",
    "again",
    "unexpected",
    "error",
    "warning",
}
_在线提示词停用片段 = {
    "masterpiece",
    "best quality",
    "high quality",
    "ultra detailed",
    "best quality, masterpiece",
    "negative prompt",
    "worst quality",
    "low quality",
    "bad anatomy",
    "text",
    "watermark",
    "logo",
    "copyright",
}
_在线站点低信息短词集合 = {
    "solo",
    "1girl",
    "1boy",
    "girl",
    "boy",
    "woman",
    "man",
    "young",
    "beautiful",
    "warm",
    "anime",
    "signs",
    "dreamy",
    "night",
    "day",
}
_在线模型噪声模式 = re.compile(
    r"(<\s*lora:[^>]+>|<\s*lyco:[^>]+>|score_[0-9]+(?:_up)?|\b[a-z0-9]{4,8}\b(?=\s*$)|\b(?:easynegative|badhandv4|bad-artist|ng_deepnegative_v1_75t)\b)",
    flags=re.IGNORECASE,
)
_在线版本号模式 = re.compile(r"^v\d+(?:\.\d+)?$", flags=re.IGNORECASE)
_在线摄影器材短语模式 = re.compile(r"^(?:shot on|captured on|taken with)\b", flags=re.IGNORECASE)
_在线通用英文高价值短语集合 = {
    "cinematic",
    "photorealism",
    "photorealistic",
    "realistic",
    "hyper realism",
    "hyperrealistic",
    "ultra-realistic",
    "ultra detailed",
    "ultra-detailed",
    "high detail",
    "highly detailed",
    "professional",
    "editorial",
    "dramatic lighting",
    "volumetric lighting",
    "film grain",
    "shallow depth of field",
    "glitch art",
    "chromatic aberration",
    "greek mythology",
}

_在线查询关键词映射 = {
    "portrait": ["人像", "写真", "中景半身", "面部聚焦"],
    "cinematic": ["电影感", "电影调色", "电影剧照"],
    "editorial": ["社论人像", "编辑人像", "杂志感", "时尚写真"],
    "fashion": ["时尚写真", "杂志感", "商业广告大片"],
    "realistic": ["真实感", "raw photo", "高细节"],
    "photoreal": ["真实感", "raw photo", "高细节"],
    "rembrandt": ["伦勃朗光", "侧光", "高光过渡柔和"],
    "dutch angle": ["荷兰角", "电影静帧构图", "长焦"],
    "ancient": ["古风", "汉服", "古风建筑"],
    "hanfu": ["汉服", "古风", "披帛", "苏绣"],
    "myth": ["神话感", "神圣", "神殿"],
    "goddess": ["神女", "神话感", "云海"],
    "cyberpunk": ["CG感", "赛博朋克", "霓虹都市"],
    "scifi": ["CG感", "未来感", "未来都市"],
    "sci-fi": ["CG感", "未来感", "未来都市"],
    "mecha": ["机甲", "CG感", "金属"],
    "alley": ["小巷", "霓虹小巷", "雨巷"],
    "rooftop": ["屋顶", "天台", "未来都市"],
    "nsfw": ["成人向", "私房写真", "暧昧"],
    "boudoir": ["私房写真", "成人向", "微醺感"],
    "low angle": ["低角度", "广角", "电影感"],
    "close-up": ["近景", "面部特写", "面部聚焦"],
    "古风": ["古风", "汉服", "古风建筑", "云海", "神殿"],
    "神女": ["神女", "神话感", "神圣", "云海", "神殿"],
    "仙侠": ["仙侠", "古风", "云海", "神殿", "电影感"],
    "赛博朋克": ["赛博朋克", "CG感", "未来感", "霓虹都市"],
    "日系": ["日系", "写真", "胶片颗粒", "清新氛围"],
    "黑白": ["黑白", "纪实", "高反差", "真实质感"],
}
_在线查询同义词映射 = {
    "female": ["female", "woman", "women", "lady"],
    "male": ["male", "man", "men", "gentleman"],
    "portrait": ["portrait", "headshot", "face", "close-up"],
    "fashion": ["fashion", "editorial", "magazine", "runway", "stylish"],
    "ancient": ["ancient", "ruins", "temple", "mythology"],
    "goddess": ["goddess", "divine", "deity"],
    "cyberpunk": ["cyberpunk", "neon", "futuristic", "future"],
    "成人": ["adult", "nsfw", "sensual", "boudoir", "intimate"],
    "私房": ["boudoir", "intimate", "bedroom"],
    "半身": ["half body", "waist up", "upper body", "medium shot"],
    "全身": ["full body", "full length"],
    "写真": ["portrait", "editorial portrait"],
}
_在线查询英文扩展映射 = {
    "成人": ["adult", "nsfw", "sensual", "boudoir", "intimate"],
    "私房": ["boudoir", "intimate", "bedroom", "lingerie"],
    "半身": ["half body", "waist up", "upper body", "medium shot"],
    "全身": ["full body", "full length", "standing pose"],
    "写真": ["portrait", "editorial portrait"],
}
_在线定向高价值标签规则 = [
    {
        "name": "fashion_portrait_photo",
        "required_groups": [
            ["fashion", "editorial", "时尚", "杂志"],
            ["portrait", "headshot", "人像", "写真", "face", "写真感"],
        ],
        "target_min": 5,
        "target_max": 8,
        "tags": [
            "fashion editorial photography",
            "editorial photography",
            "studio lighting",
            "beauty lighting",
            "high fashion",
            "magazine style portrait",
            "professional retouching",
            "clean studio background",
        ],
    }
]
_回退镜头动作增强模式 = re.compile(
    r"(?:\d+\s*mm|度角|平视|俯视|仰视|定焦|逆光|侧光|特写|近景|中景|全景|全身|半身|抬手|回身|倚靠|扶发)",
    flags=re.IGNORECASE,
)
_回退通用标签降权默认列表 = [
    "8K",
    "东亚",
    "成年女性",
    "性感",
    "暖色调",
    "真实感",
    "复古",
    "电影感",
    "高细节",
    "摄影质感",
    "无文字",
    "无水印",
    "无logo",
    "主体突出",
    "景深层次自然",
    "材质细节丰富",
    "时尚摄影",
    "写实肤感自然",
    "皮肤质感柔和",
    "布料褶皱自然",
    "全裸",
    "巨乳",
    "微醺感",
    "私房写真",
    "魅惑凝视",
]
_在线搜索配置文件路径 = Path(__file__).with_name("online_search_config.json")
_在线搜索配置默认值 = {
    "fallback_generic_downweight_tags": list(_回退通用标签降权默认列表),
    "long_query_term_threshold": 16,
    "generic_penalty_score": 6,
}
_在线搜索配置缓存: dict[str, Any] = {
    "mtime": None,
    "config": dict(_在线搜索配置默认值),
}


def _清洗配置字符串列表(value: Any, *, max_items: int = 512) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
        if len(cleaned) >= max_items:
            break
    return cleaned


def _在线搜索配置整数(raw: Any, *, default: int, min_value: int, max_value: int) -> int:
    try:
        value = int(raw)
    except Exception:
        return default
    return max(min_value, min(max_value, value))


def _标准化在线搜索配置(raw: Any) -> dict[str, Any]:
    normalized = dict(_在线搜索配置默认值)
    if not isinstance(raw, dict):
        return normalized

    tags = _清洗配置字符串列表(raw.get("fallback_generic_downweight_tags"))
    if tags:
        normalized["fallback_generic_downweight_tags"] = tags

    normalized["long_query_term_threshold"] = _在线搜索配置整数(
        raw.get("long_query_term_threshold"),
        default=int(_在线搜索配置默认值["long_query_term_threshold"]),
        min_value=8,
        max_value=96,
    )
    normalized["generic_penalty_score"] = _在线搜索配置整数(
        raw.get("generic_penalty_score"),
        default=int(_在线搜索配置默认值["generic_penalty_score"]),
        min_value=1,
        max_value=30,
    )
    return normalized


def _读取在线搜索配置() -> dict[str, Any]:
    mtime: float | None
    try:
        mtime = _在线搜索配置文件路径.stat().st_mtime if _在线搜索配置文件路径.exists() else None
    except Exception:
        mtime = None

    cache_mtime = _在线搜索配置缓存.get("mtime")
    cache_config = _在线搜索配置缓存.get("config")
    if mtime == cache_mtime and isinstance(cache_config, dict):
        return cache_config

    raw_config: Any = {}
    if _在线搜索配置文件路径.exists():
        try:
            raw_text = _在线搜索配置文件路径.read_text(encoding="utf-8")
            raw_config = json.loads(raw_text)
        except Exception:
            raw_config = {}

    config = _标准化在线搜索配置(raw_config)
    _在线搜索配置缓存["mtime"] = mtime
    _在线搜索配置缓存["config"] = config
    return config


def _回退降权参数() -> tuple[set[str], int, int]:
    config = _读取在线搜索配置()
    tags = _清洗配置字符串列表(config.get("fallback_generic_downweight_tags"))
    tag_set = {item.casefold() for item in tags}
    if not tag_set:
        tag_set = {item.casefold() for item in _回退通用标签降权默认列表}
    term_threshold = _在线搜索配置整数(
        config.get("long_query_term_threshold"),
        default=int(_在线搜索配置默认值["long_query_term_threshold"]),
        min_value=8,
        max_value=96,
    )
    penalty_score = _在线搜索配置整数(
        config.get("generic_penalty_score"),
        default=int(_在线搜索配置默认值["generic_penalty_score"]),
        min_value=1,
        max_value=30,
    )
    return tag_set, term_threshold, penalty_score

NODE_CLASS_MAPPINGS = {
    "QwenTE_StagePromptGenerator": QwenTE阶段式提示词生成器,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "QwenTE_StagePromptGenerator": "真男人提示词阶段生成器",
}


def _get_prompt_server_class():
    try:
        server_module = importlib.import_module("server")
    except Exception:
        return None
    return getattr(server_module, "PromptServer", None)


_ONLINE_RESPONSE_MAX_BYTES = 8 * 1024 * 1024
_ONLINE_READ_CHUNK_BYTES = 64 * 1024


def _设置在线响应读取超时(response: Any, timeout: float) -> None:
    fp = getattr(response, "fp", None)
    raw = getattr(fp, "raw", None)
    socket_obj = getattr(raw, "_sock", None)
    for candidate in (socket_obj, raw, fp):
        setter = getattr(candidate, "settimeout", None)
        if callable(setter):
            try:
                setter(max(0.1, float(timeout)))
            except Exception:
                pass
            return


def _读取受限在线响应(response: Any, *, timeout: float, label: str) -> bytes:
    content_length = None
    try:
        content_length = int(response.headers.get("Content-Length", "") or 0)
    except (TypeError, ValueError, OverflowError, AttributeError):
        content_length = None
    if content_length is not None and content_length > _ONLINE_RESPONSE_MAX_BYTES:
        raise RuntimeError(
            f"{label}响应过大：Content-Length={content_length}，上限为 {_ONLINE_RESPONSE_MAX_BYTES} 字节。"
        )

    deadline = time.monotonic() + max(0.1, float(timeout))
    chunks: list[bytes] = []
    total = 0
    reader = getattr(response, "read1", None)
    if not callable(reader):
        reader = response.read
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"{label}读取超过总时限。")
        _设置在线响应读取超时(response, remaining)
        chunk = reader(min(_ONLINE_READ_CHUNK_BYTES, _ONLINE_RESPONSE_MAX_BYTES + 1 - total))
        if not chunk:
            break
        chunks.append(bytes(chunk))
        total += len(chunk)
        if total > _ONLINE_RESPONSE_MAX_BYTES:
            raise RuntimeError(f"{label}响应超过 {_ONLINE_RESPONSE_MAX_BYTES} 字节上限。")
    return b"".join(chunks)


def _在线JSON请求(url: str, *, timeout: float = 8.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = _读取受限在线响应(response, timeout=timeout, label="联网 JSON")
        charset = response.headers.get_content_charset() or "utf-8"
    data = json.loads(payload.decode(charset, errors="ignore"))
    return data if isinstance(data, dict) else {}


def _在线文本请求(url: str, *, timeout: float = 12.0) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/plain, text/markdown, text/html, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = _读取受限在线响应(response, timeout=timeout, label="联网文本")
        charset = response.headers.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="ignore")


def _规范化在线提示词片段(raw: str) -> str:
    text = _在线提示词空白模式.sub(" ", str(raw or "").strip())
    text = _在线提示词命令参数模式.sub("", text).strip()
    text = text.strip("`\"'“”‘’<>[]{}()（）【】「」『』《》")
    text = _在线提示词权重尾巴模式.sub("", text).strip().strip(",:;|")
    if not text:
        return ""
    if len(text) < 2 or len(text) > 48:
        return ""
    lowered = text.casefold()
    if _在线噪声关键词模式.search(lowered):
        return ""
    word_tokens = [token for token in re.split(r"\s+", lowered) if token]
    if word_tokens and all(token in _在线噪声短词集合 for token in word_tokens):
        return ""
    if lowered in _在线提示词停用片段:
        return ""
    if _在线提示词URL模式.match(text):
        return ""
    if _在线摄影器材短语模式.match(text):
        return ""
    digit_count = sum(char.isdigit() for char in text)
    if digit_count >= max(3, len(text) // 2):
        return ""
    return text


def _在线查询关键词列表(query: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for part in _在线提示词片段分隔模式.split(str(query or "").casefold()):
        cleaned = _在线提示词空白模式.sub(" ", str(part or "").strip())
        if not cleaned:
            continue
        for token in cleaned.split(" "):
            text = token.strip()
            if not text or len(text) < 2:
                continue
            if text in seen:
                continue
            seen.add(text)
            tokens.append(text)
    for phrase in _在线查询扩展英文关键词(query, max_items=8):
        if phrase in seen:
            continue
        seen.add(phrase)
        tokens.append(phrase)
    return tokens


def _在线查询扩展英文关键词(query: str, *, max_items: int = 8) -> list[str]:
    normalized_query = str(query or "").casefold()
    if not normalized_query:
        return []
    results: list[str] = []
    seen: set[str] = set()
    for key, terms in _在线查询英文扩展映射.items():
        key_text = str(key or "").strip().casefold()
        if not key_text or key_text not in normalized_query:
            continue
        for raw_term in terms:
            term = _在线提示词空白模式.sub(" ", str(raw_term or "").strip().casefold())
            if not term:
                continue
            if len(term) < 2 or len(term) > 40:
                continue
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9'\-/ ]*", term):
                continue
            if term in seen:
                continue
            seen.add(term)
            results.append(term)
            if len(results) >= max(1, max_items):
                return results
    return results


def _构建联网搜索查询(query: str, *, max_items: int = 4) -> str:
    text = _在线提示词空白模式.sub(" ", str(query or "").strip())
    if not text:
        return ""
    expanded = _在线查询扩展英文关键词(text, max_items=max_items)
    if not expanded:
        return text
    pieces: list[str] = [text]
    seen: set[str] = {text.casefold()}
    for term in expanded:
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        pieces.append(term)
    merged = " ".join(pieces).strip()
    return merged[:120].strip()


def _在线查询关键词组(query: str) -> list[set[str]]:
    groups: list[set[str]] = []
    seen: set[tuple[str, ...]] = set()
    for token in _在线查询关键词列表(query):
        expanded = {token}
        for synonym in _在线查询同义词映射.get(token, []):
            text = str(synonym or "").strip().casefold()
            if text:
                expanded.add(text)
        key = tuple(sorted(expanded))
        if key in seen:
            continue
        seen.add(key)
        groups.append(expanded)
    return groups


def _在线查询命中关键词组集合(query: str, required_groups: Any) -> bool:
    normalized_query = str(query or "").casefold()
    if not normalized_query:
        return False
    if not isinstance(required_groups, list):
        return False
    for raw_group in required_groups:
        if not isinstance(raw_group, list):
            return False
        matched = False
        for raw_term in raw_group:
            term = str(raw_term or "").strip().casefold()
            if term and term in normalized_query:
                matched = True
                break
        if not matched:
            return False
    return True


def _在线查询定向高价值标签配置(query: str, *, limit: int) -> tuple[list[str], int, int]:
    normalized_query = str(query or "").casefold()
    if not normalized_query:
        return [], 0, 0

    for rule in _在线定向高价值标签规则:
        if not isinstance(rule, dict):
            continue
        if not _在线查询命中关键词组集合(normalized_query, rule.get("required_groups")):
            continue
        tags = rule.get("tags")
        if not isinstance(tags, list):
            continue

        normalized_tags: list[str] = []
        seen: set[str] = set()
        for raw_tag in tags:
            normalized_tag = _规范化在线提示词片段(str(raw_tag or ""))
            if not normalized_tag:
                continue
            lowered = normalized_tag.casefold()
            if lowered in seen:
                continue
            if _在线噪声关键词模式.search(lowered):
                continue
            if _在线模型噪声模式.search(normalized_tag):
                continue
            if lowered in _在线站点低信息短词集合:
                continue
            if _在线版本号模式.match(normalized_tag):
                continue
            seen.add(lowered)
            normalized_tags.append(normalized_tag)

        if not normalized_tags:
            continue

        target_min = max(1, min(limit, int(rule.get("target_min", 5) or 5)))
        target_max = max(target_min, min(limit, int(rule.get("target_max", 8) or 8)))
        return normalized_tags, target_min, target_max
    return [], 0, 0


def _在线样本命中关键词数(query: str, sample: str) -> int:
    normalized_sample = str(sample or "").casefold()
    if not normalized_sample:
        return 0
    hits = 0
    for group in _在线查询关键词组(query):
        if any(token in normalized_sample for token in group):
            hits += 1
    return hits


def _在线样本相关度(query: str, sample: str) -> int:
    normalized_query = str(query or "").casefold()
    normalized_sample = str(sample or "").casefold()
    if not normalized_query or not normalized_sample:
        return 0

    score = 0
    for group in _在线查询关键词组(normalized_query):
        matched_token = next((token for token in group if token in normalized_sample), "")
        if matched_token:
            score += max(2, min(8, len(matched_token)))
    for term in _在线查询扩展英文关键词(normalized_query, max_items=8):
        if term in normalized_sample:
            score += max(3, min(7, len(term) // 2 + 2))
    for key, tags in _在线查询关键词映射.items():
        key_text = key.casefold()
        if key_text in normalized_query and any(str(tag).casefold() in normalized_sample for tag in tags):
            score += 4
    return score


def _在线片段与查询相关(query: str, token: str) -> bool:
    normalized_query = str(query or "").casefold()
    normalized_token = str(token or "").casefold()
    if not normalized_query or not normalized_token:
        return False
    if normalized_token in normalized_query:
        return True
    for group in _在线查询关键词组(normalized_query):
        if any((query_token in normalized_token) or (normalized_token in query_token) for query_token in group):
            return True
    for key, tags in _在线查询关键词映射.items():
        key_text = key.casefold()
        if key_text in normalized_query and any(str(tag).casefold() in normalized_token for tag in tags):
            return True
    for term in _在线查询扩展英文关键词(normalized_query, max_items=8):
        if term in normalized_token or normalized_token in term:
            return True
    return False


def _压缩英文查询相关片段(query: str, token: str) -> str:
    text = str(token or "").strip()
    if not text:
        return ""
    lowered = text.casefold()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9'\-/ ]*", text):
        return text
    if lowered in _在线通用英文高价值短语集合:
        return text

    matched_terms: list[str] = []
    for group in _在线查询关键词组(query):
        match = next((term for term in sorted(group, key=len, reverse=True) if term in lowered), "")
        if match and match not in matched_terms:
            matched_terms.append(match)
    if matched_terms:
        return " ".join(matched_terms[:3])

    if len(text.split()) > 3:
        return ""
    return text


def _规范化在线样本文本(sample: str) -> str:
    text = _在线提示词空白模式.sub(" ", str(sample or "").strip())
    text = _在线提示词命令参数模式.sub("", text)
    text = _在线提示词空白模式.sub(" ", text).strip()
    return text


def _收集在线样本(prompts: list[str], prompt: str, *, limit: int) -> list[str]:
    text = str(prompt or "").strip()
    if not text:
        return prompts
    if text in prompts:
        return prompts
    prompts.append(text)
    if len(prompts) > max(24, limit * 3):
        del prompts[max(24, limit * 3) :]
    return prompts


def _在线样本可接受(query: str, sample: str) -> bool:
    groups = _在线查询关键词组(query)
    if not groups:
        return False
    hit_count = _在线样本命中关键词数(query, sample)
    if len(groups) >= 2 and hit_count < 2:
        expanded_terms = _在线查询扩展英文关键词(query, max_items=8)
        normalized_sample = str(sample or "").casefold()
        expansion_hits = sum(1 for term in expanded_terms if term in normalized_sample)
        if expansion_hits < 1:
            return False
    return _在线样本相关度(query, sample) > 0


def _联网抓取提示词样本(query: str, *, limit: int) -> tuple[list[str], str]:
    prompts: list[str] = []
    used_sources: list[str] = []
    target_sample_count = max(12, limit * 2)
    search_query = _构建联网搜索查询(query, max_items=4) or str(query or "")

    # 优先尝试 Civitai 公开图片流，并在本地按 query 做相关性过滤。
    try:
        url = "https://civitai.com/api/v1/images?limit=50&nsfw=Soft&sort=Most+Reactions&period=Month"
        data = _在线JSON请求(url, timeout=10.0)
        items = data.get("items")
        ranked_samples: list[tuple[int, str]] = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                meta = item.get("meta")
                if not isinstance(meta, dict):
                    continue
                prompt = str(meta.get("prompt", "") or "").strip()
                if not prompt:
                    continue
                score = _在线样本相关度(query, prompt)
                if (score <= 0) or (not _在线样本可接受(query, prompt)):
                    continue
                ranked_samples.append((score, prompt))
        ranked_samples.sort(key=lambda item: (-item[0], len(item[1])))
        for _, prompt in ranked_samples[: max(18, limit * 2)]:
            _收集在线样本(prompts, prompt, limit=limit)
        if prompts:
            used_sources.append("civitai")
            if len(prompts) >= target_sample_count:
                return prompts, "+".join(used_sources)
    except Exception:
        pass

    # 第二优先：PromptHero 搜索页文本。
    try:
        encoded = urllib.parse.quote_plus(search_query)
        url = f"https://r.jina.ai/http://prompthero.com/search?q={encoded}"
        text = _在线文本请求(url, timeout=14.0)
        ranked_lines: list[tuple[int, str]] = []
        for raw_line in text.splitlines():
            line = _在线提示词空白模式.sub(" ", raw_line.strip()).strip("#*- ").strip()
            if not line or len(line) < 24:
                continue
            lowered = line.casefold()
            if lowered.startswith(("title:", "url source:", "markdown content:")):
                continue
            if _在线噪声关键词模式.search(lowered):
                continue
            score = _在线样本相关度(query, line)
            if (score <= 0) or (not _在线样本可接受(query, line)):
                continue
            ranked_lines.append((score, line))
        ranked_lines.sort(key=lambda item: (-item[0], len(item[1])))
        for _, line in ranked_lines[: max(18, limit * 2)]:
            _收集在线样本(prompts, line, limit=limit)
        if prompts and "prompthero" not in used_sources:
            used_sources.append("prompthero")
            if len(prompts) >= target_sample_count:
                return prompts, "+".join(used_sources)
    except Exception:
        pass

    # 第三优先：结构化来源（Lexica）。
    try:
        encoded = urllib.parse.quote_plus(search_query)
        url = f"https://lexica.art/api/v1/search?q={encoded}"
        data = _在线JSON请求(url, timeout=10.0)
        images = data.get("images")
        if isinstance(images, list):
            for item in images:
                if not isinstance(item, dict):
                    continue
                prompt = str(item.get("prompt", "") or "").strip()
                if not prompt:
                    continue
                if (not _在线样本可接受(query, prompt)):
                    continue
                _收集在线样本(prompts, prompt, limit=limit)
                if len(prompts) >= max(18, limit * 2):
                    break
        if prompts and "lexica" not in used_sources:
            used_sources.append("lexica")
            if len(prompts) >= target_sample_count:
                return prompts, "+".join(used_sources)
    except Exception:
        pass

    # 最后回退：通过 r.jina.ai 抓取 DuckDuckGo 文本检索结果。
    try:
        encoded = urllib.parse.quote_plus(f"{search_query} prompt tags")
        search_url = f"https://r.jina.ai/http://duckduckgo.com/html/?q={encoded}"
        text = _在线文本请求(search_url, timeout=14.0)
        for raw_line in text.splitlines():
            line = _在线提示词空白模式.sub(" ", raw_line.strip()).strip("#*- ").strip()
            if not line or len(line) < 12:
                continue
            lowered = line.casefold()
            if lowered.startswith(("title:", "url source:", "markdown content:")):
                continue
            if _在线噪声关键词模式.search(lowered):
                continue
            if "http://" in lowered or "https://" in lowered:
                continue
            if not _在线样本可接受(query, line):
                continue
            _收集在线样本(prompts, line, limit=limit)
            if len(prompts) >= max(18, limit * 2):
                break
    except Exception:
        pass

    if prompts:
        if "duckduckgo_text" not in used_sources:
            used_sources.append("duckduckgo_text")
        return prompts, "+".join(used_sources)
    return [], "none"


def _补齐在线定向高价值标签(
    counter: Counter[str],
    *,
    whitelist_tags: list[str],
    target_min: int,
    target_max: int,
) -> None:
    if not whitelist_tags or target_min <= 0 or target_max <= 0:
        return
    if len(counter) >= target_min:
        return
    for tag in whitelist_tags:
        if len(counter) >= target_max:
            break
        text = str(tag or "").strip()
        if not text:
            continue
        if counter.get(text, 0) > 0:
            continue
        # 低权重补齐：仅在候选不足时补位，不覆盖主干来源排序。
        counter[text] = 2


def _从在线提示词提取标签(samples: list[str], *, query: str, limit: int) -> tuple[list[dict[str, object]], list[str]]:
    counter: Counter[str] = Counter()
    cleaned_samples: list[str] = []
    whitelist_tags, whitelist_target_min, whitelist_target_max = _在线查询定向高价值标签配置(query, limit=limit)
    whitelist_set = {item.casefold() for item in whitelist_tags}
    for sample in samples:
        normalized_sample = _规范化在线样本文本(sample)
        if (
            normalized_sample
            and len(cleaned_samples) < 6
            and not _在线噪声关键词模式.search(normalized_sample.casefold())
        ):
            cleaned_samples.append(normalized_sample[:320])
        fragments: list[str] = []
        fragments.extend(_在线提示词片段分隔模式.split(normalized_sample))
        for sentence in _在线提示词句读分隔模式.split(normalized_sample):
            if sentence:
                fragments.append(sentence)
        for phrase in _在线英文短语模式.findall(normalized_sample):
            fragments.append(phrase)
        for fragment in fragments:
            token = _规范化在线提示词片段(fragment)
            if not token:
                continue
            token = _压缩英文查询相关片段(query, token)
            if not token:
                continue
            lowered = token.casefold()
            is_english_only = bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9'\-/ ]*", token))
            if _在线模型噪声模式.search(token):
                continue
            if lowered in _在线站点低信息短词集合:
                continue
            if _在线版本号模式.match(token):
                continue
            if re.fullmatch(r"[A-Za-z0-9]{4,8}", token) and not _在线片段与查询相关(query, token):
                continue
            if (
                is_english_only
                and (not _在线片段与查询相关(query, token))
                and lowered not in _在线通用英文高价值短语集合
                and lowered not in whitelist_set
            ):
                continue
            if (" " not in token) and (not _在线中文检测模式.search(token)) and len(token) <= 8 and (not _在线片段与查询相关(query, token)):
                continue
            counter[token] += 1
            if " " in token and _在线中文检测模式.search(token):
                for part in token.split():
                    sub_token = _规范化在线提示词片段(part)
                    if not sub_token or sub_token == token:
                        continue
                    sub_token = _压缩英文查询相关片段(query, sub_token)
                    if not sub_token:
                        continue
                    sub_lowered = sub_token.casefold()
                    if _在线模型噪声模式.search(sub_token):
                        continue
                    if sub_lowered in _在线站点低信息短词集合:
                        continue
                    if _在线版本号模式.match(sub_token):
                        continue
                    counter[sub_token] += 1

    _补齐在线定向高价值标签(
        counter,
        whitelist_tags=whitelist_tags,
        target_min=whitelist_target_min,
        target_max=whitelist_target_max,
    )

    ranked = sorted(counter.items(), key=lambda item: (-item[1], len(item[0]), item[0].casefold()))
    if not ranked:
        return [], cleaned_samples

    tag_names = [item[0] for item in ranked[: max(1, min(limit * 2, 120))]]
    suggest_payload = 推荐自定义标签归类("，".join(tag_names), max_items=max(12, min(120, len(tag_names))))
    suggest_map = {
        str(item.get("tag", "")): item
        for item in (suggest_payload.get("tags") if isinstance(suggest_payload, dict) else [])
        if isinstance(item, dict)
    }
    max_count = max(int(item[1]) for item in ranked) if ranked else 1

    tag_items: list[dict[str, object]] = []
    for tag, count in ranked[: max(1, limit)]:
        if " " in tag and _在线中文检测模式.search(tag) and len(tag.split()) >= 3:
            # 中文多词串通常是抓取噪声，真实标签应为离散短词。
            continue
        suggest = suggest_map.get(tag, {})
        group = str(suggest.get("recommended_group", "") or suggest.get("existing_group", ""))
        section = str(suggest.get("recommended_section", "") or suggest.get("existing_section", ""))
        suggest_conf = float(suggest.get("confidence", 0.0) or 0.0)
        freq_conf = 0.35 + 0.55 * (float(count) / float(max_count or 1))
        confidence = max(suggest_conf, freq_conf)
        exists = bool(suggest.get("exists", False))
        if exists:
            confidence = max(confidence, 0.95)
        if (not exists) and (not group) and (not section):
            confidence = min(confidence, 0.68)
        if (" " in tag and len(tag.split()) >= 4) and (not exists):
            confidence = min(confidence, 0.6)

        confidence = min(0.99, round(confidence, 3))
        tag_items.append(
            {
                "tag": tag,
                "count": int(count),
                "confidence": confidence,
                "group": group,
                "section": section,
                "exists": exists,
                "source": "online_extracted",
            }
        )
    return tag_items, cleaned_samples


def _拆分回退查询词(query: str) -> list[str]:
    normalized_query = _在线提示词空白模式.sub(" ", str(query or "").strip().casefold())
    if not normalized_query:
        return []

    raw_terms: list[str] = []
    for piece in _在线提示词片段分隔模式.split(normalized_query):
        fragment = _在线提示词空白模式.sub(" ", str(piece or "").strip()).strip(",:;|")
        if not fragment:
            continue
        raw_terms.append(fragment)
        if " " in fragment:
            for part in fragment.split(" "):
                part_text = part.strip()
                if part_text:
                    raw_terms.append(part_text)

    terms: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        cleaned = term.strip("`\"'“”‘’<>[]{}()（）【】「」『』《》").strip()
        if not cleaned or len(cleaned) > 48:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        terms.append(cleaned)
    return terms


def _应跳过联网搜索(query: str) -> bool:
    text = str(query or "").strip()
    if not text:
        return False
    if len(text) >= 120:
        return True
    separator_hits = sum(text.count(ch) for ch in (",", "，", ";", "；", "|", "\n", "\r"))
    return separator_hits >= 10


def _标签相似度(left: str, right: str) -> float:
    lhs = str(left or "").strip().casefold()
    rhs = str(right or "").strip().casefold()
    if not lhs or not rhs:
        return 0.0
    if lhs == rhs:
        return 1.0

    shorter, longer = (lhs, rhs) if len(lhs) <= len(rhs) else (rhs, lhs)
    contain_ratio = (len(shorter) / len(longer)) if shorter and shorter in longer else 0.0

    def _bigrams(text: str) -> set[str]:
        if len(text) < 2:
            return {text}
        return {text[index : index + 2] for index in range(len(text) - 1)}

    lhs_set = _bigrams(lhs)
    rhs_set = _bigrams(rhs)
    overlap_ratio = (len(lhs_set & rhs_set) / len(lhs_set | rhs_set)) if lhs_set and rhs_set else 0.0
    return max(contain_ratio, overlap_ratio)


def _本地回退联想标签(query: str, *, limit: int) -> list[str]:
    library = 前端标签库数据().get("tag_library", {})
    normalized_query = str(query or "").strip().casefold()
    if not normalized_query:
        return []

    downweight_tag_set, downweight_term_threshold, downweight_penalty = _回退降权参数()

    query_terms = _拆分回退查询词(normalized_query)
    if not query_terms:
        query_terms = [normalized_query]
    term_rank = {term: index for index, term in enumerate(query_terms)}

    mapped: list[str] = []
    mapped_seen: set[str] = set()
    for key, tags in _在线查询关键词映射.items():
        key_text = key.casefold()
        if key_text not in normalized_query and all((term not in key_text and key_text not in term) for term in query_terms):
            continue
        for tag in tags:
            tag_text = str(tag or "").strip()
            if not tag_text or tag_text in mapped_seen:
                continue
            mapped_seen.add(tag_text)
            mapped.append(tag_text)

    candidates: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for sections in library.values():
        if not isinstance(sections, dict):
            continue
        for tags in sections.values():
            if not isinstance(tags, list):
                continue
            for tag in tags:
                text = str(tag or "").strip()
                if not text:
                    continue
                key = text.casefold()
                if key in seen:
                    continue
                seen.add(key)
                score = 0
                if normalized_query in key:
                    score += 4
                if key and key in normalized_query:
                    score += 5
                exact_rank = term_rank.get(key)
                if exact_rank is not None:
                    score += max(14, 28 - min(18, exact_rank))
                if exact_rank is not None and _回退镜头动作增强模式.search(key):
                    score += 5
                if len(query_terms) >= downweight_term_threshold and key in downweight_tag_set:
                    if exact_rank is None or exact_rank >= 8:
                        score -= downweight_penalty
                for term in query_terms:
                    if not term or term == key:
                        continue
                    if len(term) >= 2 and term in key:
                        score += 3
                    elif len(key) >= 2 and key in term and len(term) <= 24:
                        score += 2
                if score > 0:
                    candidates.append((score, exact_rank if exact_rank is not None else 10_000, text))

    candidates.sort(key=lambda item: (-item[0], item[1], len(item[2]), item[2].casefold()))
    result: list[str] = []
    result_seen: set[str] = set()
    selected_keys: list[str] = []

    for score, _, tag in candidates:
        key = str(tag).casefold()
        if tag in result_seen:
            continue
        best_similarity = 0.0
        for existing_key in selected_keys:
            similarity = _标签相似度(key, existing_key)
            if similarity > best_similarity:
                best_similarity = similarity
        if best_similarity >= 0.92:
            continue
        if best_similarity >= 0.8:
            score -= 3
        elif best_similarity >= 0.65:
            score -= 1
        if score <= 0:
            continue
        result_seen.add(tag)
        selected_keys.append(key)
        result.append(tag)
        if len(result) >= max(1, limit):
            return result

    for tag in mapped:
        key = str(tag).casefold()
        if tag in result_seen:
            continue
        best_similarity = 0.0
        for existing_key in selected_keys:
            similarity = _标签相似度(key, existing_key)
            if similarity > best_similarity:
                best_similarity = similarity
        if best_similarity >= 0.92:
            continue
        result_seen.add(tag)
        selected_keys.append(key)
        result.append(tag)
        if len(result) >= max(1, limit):
            break
    return result


def _构建本地回退标签条目(tags: list[str], *, query: str, limit: int) -> list[dict[str, object]]:
    selected = [str(tag).strip() for tag in tags if str(tag).strip()][: max(1, limit)]
    if not selected:
        return []

    suggest_payload = 推荐自定义标签归类("，".join(selected), max_items=max(12, min(120, len(selected))))
    suggest_map = {
        str(item.get("tag", "")): item
        for item in (suggest_payload.get("tags") if isinstance(suggest_payload, dict) else [])
        if isinstance(item, dict)
    }

    lowered_query = str(query or "").casefold()
    items: list[dict[str, object]] = []
    for index, tag in enumerate(selected):
        suggest = suggest_map.get(tag, {})
        group = str(suggest.get("recommended_group", "") or suggest.get("existing_group", ""))
        section = str(suggest.get("recommended_section", "") or suggest.get("existing_section", ""))
        exists = bool(suggest.get("exists", False))
        suggest_conf = float(suggest.get("confidence", 0.0) or 0.0)
        mapped_hit = any(key in lowered_query for key in _在线查询关键词映射)
        rank_conf = max(0.45, 0.85 - 0.02 * index)
        confidence = max(suggest_conf, rank_conf if mapped_hit else rank_conf - 0.1)
        if exists:
            confidence = max(confidence, 0.9)
        items.append(
            {
                "tag": tag,
                "count": max(1, limit - index),
                "confidence": min(0.95, round(confidence, 3)),
                "group": group,
                "section": section,
                "exists": exists,
                "source": "local_fallback",
            }
        )
    return items


def _构建联网参考样本(
    query: str,
    tag_items: list[dict[str, object]],
    *,
    source: str,
    limit: int,
    warning: str = "",
) -> list[str]:
    cleaned_query = str(query or "").strip()
    if not isinstance(tag_items, list):
        tag_items = []

    normalized_items = [item for item in tag_items if isinstance(item, dict) and str(item.get("tag", "")).strip()]
    if not normalized_items and not cleaned_query:
        return []

    sample_texts: list[str] = []
    if cleaned_query:
        sample_texts.append(f"检索词：{cleaned_query}")

    top_tags = [str(item.get("tag", "")).strip() for item in normalized_items[:8] if str(item.get("tag", "")).strip()]
    if top_tags:
        sample_texts.append(f"候选预览：{'、'.join(top_tags)}")

    high_tags = [
        str(item.get("tag", "")).strip()
        for item in normalized_items
        if float(item.get("confidence", 0.0) or 0.0) >= 0.72 and str(item.get("tag", "")).strip()
    ][:6]
    if high_tags:
        sample_texts.append(f"高置信候选：{'、'.join(high_tags)}")

    grouped_lines: list[str] = []
    grouped: dict[str, list[str]] = {}
    for item in normalized_items:
        group = str(item.get("group", "")).strip()
        tag = str(item.get("tag", "")).strip()
        if not group or not tag:
            continue
        bucket = grouped.setdefault(group, [])
        if tag not in bucket:
            bucket.append(tag)
    for group, tags in grouped.items():
        shown = "、".join(tags[:4])
        remain = max(0, len(tags) - min(len(tags), 4))
        grouped_lines.append(f"{group}：{shown}{f' +{remain}' if remain > 0 else ''}")
        if len(grouped_lines) >= 3:
            break
    if grouped_lines:
        sample_texts.append("分组参考：\n" + "\n".join(grouped_lines))

    source_hint = ""
    normalized_source = str(source or "").strip().lower()
    if "local_fallback" in normalized_source:
        source_hint = "当前样本由本地回退摘要生成，可继续尝试更具体的英文词提升联网命中。"
    elif "network_error" in normalized_source:
        source_hint = "当前联网阶段发生异常，以下为回退参考摘要。"
    elif warning:
        source_hint = f"当前结果存在回退提示：{str(warning).strip()}"
    if source_hint:
        sample_texts.append(source_hint)

    deduped: list[str] = []
    seen: set[str] = set()
    for sample in sample_texts:
        text = _在线提示词空白模式.sub(" ", str(sample or "").strip())
        text = text.replace("： ", "：").replace(" \n", "\n").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        deduped.append(text)
        if len(deduped) >= max(3, min(6, limit)):
            break
    return deduped


def _json_response(payload: dict[str, Any], *, status: int = 200):
    if web is None:
        raise RuntimeError("aiohttp.web 不可用，无法返回 JSON 响应。")
    return web.json_response(
        payload,
        status=status,
        dumps=lambda data: json.dumps(data, ensure_ascii=False),
    )


def _no_store_file_response(path: Path):
    if web is None:
        raise RuntimeError("aiohttp.web 不可用，无法返回文件响应。")
    response = web.FileResponse(path)
    response.headers["Cache-Control"] = "no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


_REQUEST_JSON_MAX_BYTES = 2 * 1024 * 1024
_REQUEST_JSON_READ_CHUNK_BYTES = 64 * 1024


def _raise_request_json_too_large(actual_size: int) -> None:
    if web is not None:
        raise web.HTTPRequestEntityTooLarge(
            max_size=_REQUEST_JSON_MAX_BYTES,
            actual_size=max(0, int(actual_size)),
            text=json.dumps(
                {
                    "ok": False,
                    "message": f"请求 JSON 超过 {_REQUEST_JSON_MAX_BYTES // (1024 * 1024)} MiB 上限。",
                },
                ensure_ascii=False,
            ),
            content_type="application/json",
        )
    raise ValueError(f"请求 JSON 超过 {_REQUEST_JSON_MAX_BYTES} 字节上限。")


async def _read_request_json(request) -> dict[str, Any]:
    try:
        content_length = getattr(request, "content_length", None)
        if content_length is not None and int(content_length) > _REQUEST_JSON_MAX_BYTES:
            _raise_request_json_too_large(int(content_length))

        cached_body = getattr(request, "_read_bytes", None)
        if isinstance(cached_body, (bytes, bytearray)):
            raw = bytes(cached_body)
            if len(raw) > _REQUEST_JSON_MAX_BYTES:
                _raise_request_json_too_large(len(raw))
        else:
            content = getattr(request, "content", None)
            iter_chunked = getattr(content, "iter_chunked", None)
            if callable(iter_chunked):
                chunks: list[bytes] = []
                total = 0
                async for chunk in iter_chunked(_REQUEST_JSON_READ_CHUNK_BYTES):
                    total += len(chunk)
                    if total > _REQUEST_JSON_MAX_BYTES:
                        _raise_request_json_too_large(total)
                    chunks.append(bytes(chunk))
                raw = b"".join(chunks)
            else:
                data = await request.json()
                if not isinstance(data, dict):
                    return {}
                if len(json.dumps(data, ensure_ascii=False).encode("utf-8")) > _REQUEST_JSON_MAX_BYTES:
                    _raise_request_json_too_large(_REQUEST_JSON_MAX_BYTES + 1)
                return data

        charset = str(getattr(request, "charset", None) or "utf-8")
        data = json.loads(raw.decode(charset)) if raw else {}
    except Exception as exc:
        if web is not None and isinstance(exc, web.HTTPRequestEntityTooLarge):
            raise
        return {}
    return data if isinstance(data, dict) else {}


_QUALITY_AUDIT_MAX_PROMPT_IDS = 24
_QUALITY_AUDIT_MAX_PROMPT_ID_LENGTH = 256


def _normalize_prompt_id_list(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    prompt_ids: list[str] = []
    seen: set[str] = set()
    for item in items:
        prompt_id = str(item or "").strip()
        if (
            not prompt_id
            or len(prompt_id) > _QUALITY_AUDIT_MAX_PROMPT_ID_LENGTH
            or prompt_id in seen
        ):
            continue
        seen.add(prompt_id)
        prompt_ids.append(prompt_id)
        if len(prompt_ids) >= _QUALITY_AUDIT_MAX_PROMPT_IDS:
            break
    return prompt_ids


def _parse_quality_audit_source_request(data: Any) -> tuple[list[str], str | None]:
    if not isinstance(data, dict):
        return [], None
    if "image_paths" in data:
        return [], (
            "质检接口不接受客户端 image_paths。"
            "请使用 history_prompt_ids/history_prompt_id，或省略来源以检查 ComfyUI 输出目录中的最近图片。"
        )

    history_prompt_ids = _normalize_prompt_id_list(data.get("history_prompt_ids"))
    history_prompt_id = str(data.get("history_prompt_id", "") or "").strip()
    if len(history_prompt_id) > _QUALITY_AUDIT_MAX_PROMPT_ID_LENGTH:
        return [], "history_prompt_id 长度超过限制。"
    if history_prompt_id and history_prompt_id not in history_prompt_ids:
        history_prompt_ids.insert(0, history_prompt_id)
    return history_prompt_ids[:_QUALITY_AUDIT_MAX_PROMPT_IDS], None


def _resolve_history_image_path(image: Any) -> Path | None:
    if folder_paths is None or not isinstance(image, dict):
        return None

    filename = str(image.get("filename", "") or "").strip()
    if not filename:
        return None

    filename_path = Path(filename)
    if filename_path.is_absolute() or any(part == ".." for part in filename_path.parts):
        return None

    image_type = str(image.get("type", "output") or "output").strip().lower() or "output"
    base_dir_raw = folder_paths.get_directory_by_type(image_type)
    if not base_dir_raw:
        return None

    base_dir = Path(base_dir_raw).resolve()
    candidate_dir = base_dir
    subfolder = str(image.get("subfolder", "") or "").strip()
    if subfolder:
        subfolder_path = Path(subfolder)
        if subfolder_path.is_absolute() or any(part == ".." for part in subfolder_path.parts):
            return None
        candidate_dir = (base_dir / subfolder_path).resolve()

    image_path = (candidate_dir / filename_path).resolve()
    try:
        image_path.relative_to(base_dir)
    except ValueError:
        return None
    return image_path if image_path.exists() else None


def _collect_history_entry_image_paths(history_entry: Any, *, max_paths: int | None = None) -> list[Path]:
    if not isinstance(history_entry, dict):
        return []

    outputs = history_entry.get("outputs")
    if not isinstance(outputs, dict):
        return []

    preferred_paths: list[Path] = []
    fallback_paths: list[Path] = []
    preferred_seen: set[str] = set()
    fallback_seen: set[str] = set()
    limit = max(1, int(max_paths)) if max_paths is not None else None

    for output in outputs.values():
        if not isinstance(output, dict):
            continue
        images = output.get("images")
        if not isinstance(images, list):
            continue
        for image in images:
            image_type = str(image.get("type", "output") or "output").strip().lower() if isinstance(image, dict) else ""
            if image_type != "output" and limit is not None and len(fallback_paths) >= limit:
                continue
            image_path = _resolve_history_image_path(image)
            if image_path is None:
                continue
            normalized = str(image_path)
            if image_type == "output":
                if normalized in preferred_seen:
                    continue
                preferred_seen.add(normalized)
                preferred_paths.append(image_path)
                if limit is not None and len(preferred_paths) >= limit:
                    return preferred_paths
            else:
                if normalized in fallback_seen:
                    continue
                fallback_seen.add(normalized)
                fallback_paths.append(image_path)

    return preferred_paths or fallback_paths


def _collect_history_prompt_image_paths(
    prompt_server: Any,
    prompt_ids: list[str],
    *,
    max_images: int | None = None,
) -> list[Path]:
    prompt_queue = getattr(prompt_server, "prompt_queue", None)
    if prompt_queue is None:
        return []

    image_paths: list[Path] = []
    seen: set[str] = set()
    limit = max(1, int(max_images)) if max_images is not None else None
    for prompt_id in prompt_ids:
        history_payload = prompt_queue.get_history(prompt_id=prompt_id)
        if not isinstance(history_payload, dict):
            continue
        history_entry = history_payload.get(prompt_id)
        remaining = None if limit is None else max(1, limit - len(image_paths))
        for image_path in _collect_history_entry_image_paths(history_entry, max_paths=remaining):
            normalized = str(image_path)
            if normalized in seen:
                continue
            seen.add(normalized)
            image_paths.append(image_path)
            if limit is not None and len(image_paths) >= limit:
                return image_paths
    return image_paths


def _build_frontend_prompt_library_payload() -> dict[str, Any]:
    payload = dict(前端标签库数据())
    payload["nsfw_workspace_catalog"] = 构建NSFW工作台目录()
    return payload


def _add_prompt_tag_and_build_library(
    category: Any,
    section: Any,
    tag: Any,
) -> tuple[bool, str, dict[str, Any]]:
    ok, message = 添加自定义标签(category, section, tag)
    return ok, message, _build_frontend_prompt_library_payload()


def _add_prompt_tags_batch_and_build_library(
    category: Any,
    section: Any,
    tag: Any,
) -> tuple[bool, str, dict[str, Any], dict[str, Any]]:
    ok, message, detail = 批量添加自定义标签(category, section, tag)
    return ok, message, detail, _build_frontend_prompt_library_payload()


def _delete_prompt_tag_and_build_library(
    category: Any,
    section: Any,
    tag: Any,
) -> tuple[bool, str, dict[str, Any]]:
    ok, message = 删除自定义标签(category, section, tag)
    return ok, message, _build_frontend_prompt_library_payload()


def _register_tag_routes() -> bool:
    if web is None:
        return False

    prompt_server_class = _get_prompt_server_class()
    if prompt_server_class is None:
        return False

    prompt_server = getattr(prompt_server_class, "instance", None)
    if prompt_server is None or not hasattr(prompt_server, "routes"):
        return False

    if getattr(prompt_server, _ROUTES_FLAG, False):
        return True

    routes = prompt_server.routes
    tag_library_write_lock = asyncio.Lock()
    online_search_semaphore = asyncio.Semaphore(2)
    quality_audit_semaphore = asyncio.Semaphore(1)
    preview_worker_semaphore = asyncio.Semaphore(4)

    async def _run_thread_until_done(function, *args, **kwargs):
        worker_task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
        try:
            return await asyncio.shield(worker_task)
        except asyncio.CancelledError as cancelled_error:
            while not worker_task.done():
                try:
                    await asyncio.shield(worker_task)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if worker_task.done() and not worker_task.cancelled():
                try:
                    worker_task.result()
                except Exception:
                    pass
            raise cancelled_error

    async def _run_tag_library_transaction(function, *args):
        async with tag_library_write_lock:
            return await _run_thread_until_done(function, *args)

    async def _perform_online_search(query: str, limit: int):
        warning = ""
        source = "none"
        samples: list[str] = []
        tag_items: list[dict[str, object]] = []
        async with online_search_semaphore:
            if _应跳过联网搜索(query):
                source = "local_fallback"
                warning = "query_too_long_skip_online"
            else:
                try:
                    samples, source = await _run_thread_until_done(_联网抓取提示词样本, query, limit=limit)
                    tag_items, cleaned_samples = await _run_thread_until_done(
                        _从在线提示词提取标签,
                        samples,
                        query=query,
                        limit=limit,
                    )
                    samples = cleaned_samples
                except Exception as exc:
                    warning = str(exc)
                    source = "network_error"

            if not tag_items:
                fallback_tags = await _run_thread_until_done(_本地回退联想标签, query, limit=limit)
                if fallback_tags:
                    tag_items = await _run_thread_until_done(
                        _构建本地回退标签条目,
                        fallback_tags,
                        query=query,
                        limit=limit,
                    )
                    if source in {"none", "network_error"}:
                        source = "local_fallback"
                samples = []
        return samples, source, warning, tag_items

    @routes.get("/qwen_te/prompt_library")
    async def _get_prompt_library(_request):
        payload = await _run_tag_library_transaction(_build_frontend_prompt_library_payload)
        return _json_response(payload)

    @routes.get("/extensions/comfyUI-qwen3_5-llama-TE/stage_prompt_generator_ui.js")
    @routes.get("/extensions/ComfyUI-RealMan-Prompt-Stage-Generator/stage_prompt_generator_ui.js")
    async def _get_stage_prompt_generator_ui(_request):
        script_path = Path(__file__).with_name("web") / "stage_prompt_generator_ui.js"
        if not script_path.exists():
            raise web.HTTPNotFound(text="stage_prompt_generator_ui.js 不存在。")
        return _no_store_file_response(script_path)

    @routes.get("/qwen_te/stage_output/{node_id}")
    async def _get_stage_output(request):
        node_id = str(request.match_info.get("node_id", "") or "").strip()
        if not node_id:
            return _json_response({"ok": False, "message": "缺少节点 ID。"}, status=400)
        cache_namespace = str(request.query.get("namespace", "") or "").strip()
        async with preview_worker_semaphore:
            payload = await _run_thread_until_done(
                获取阶段节点输出缓存,
                node_id,
                cache_namespace=cache_namespace or None,
            )
        if not payload:
            return _json_response({"ok": False, "message": "当前节点还没有可读取的阶段输出。", "node_id": node_id}, status=404)
        return _json_response({"ok": True, "node_id": node_id, "output": payload})

    @routes.post("/qwen_te/tag_library/add")
    async def _add_prompt_tag(request):
        data = await _read_request_json(request)
        ok, message, library = await _run_tag_library_transaction(
            _add_prompt_tag_and_build_library,
            data.get("category", ""),
            data.get("section", ""),
            data.get("tag", ""),
        )
        return _json_response(
            {
                "ok": ok,
                "message": message,
                "library": library,
            },
            status=200 if ok else 400,
        )

    @routes.post("/qwen_te/tag_library/add_batch")
    async def _add_prompt_tags_batch(request):
        data = await _read_request_json(request)
        ok, message, detail, library = await _run_tag_library_transaction(
            _add_prompt_tags_batch_and_build_library,
            data.get("category", ""),
            data.get("section", ""),
            data.get("tag", ""),
        )
        return _json_response(
            {
                "ok": ok,
                "message": message,
                "detail": detail,
                "library": library,
            },
            status=200 if ok or detail.get("skipped") or detail.get("errors") else 400,
        )

    @routes.post("/qwen_te/tag_library/delete")
    async def _delete_prompt_tag(request):
        data = await _read_request_json(request)
        ok, message, library = await _run_tag_library_transaction(
            _delete_prompt_tag_and_build_library,
            data.get("category", ""),
            data.get("section", ""),
            data.get("tag", ""),
        )
        return _json_response(
            {
                "ok": ok,
                "message": message,
                "library": library,
            },
            status=200 if ok else 400,
        )

    @routes.post("/qwen_te/tag_library/suggest")
    async def _suggest_prompt_tag(request):
        data = await _read_request_json(request)
        async with preview_worker_semaphore:
            detail = await _run_thread_until_done(
                推荐自定义标签归类,
                data.get("tag", ""),
                max_items=12,
            )
        has_tags = bool(detail.get("tags"))
        return _json_response(
            {
                "ok": has_tags,
                "message": f"已分析 {detail.get('summary', {}).get('total', 0)} 个标签。" if has_tags else "没有可分析的标签。",
                "detail": detail,
            },
            status=200 if has_tags else 400,
        )

    @routes.post("/qwen_te/tag_library/online_search")
    async def _online_search_prompt_tags(request):
        data = await _read_request_json(request)
        query = str(data.get("query", "") or "").strip()
        if not query:
            return _json_response(
                {
                    "ok": False,
                    "message": "请输入联网搜索关键词。",
                    "query": "",
                    "source": "none",
                    "tags": [],
                    "tag_items": [],
                    "samples": [],
                },
                status=400,
            )

        raw_limit = data.get("limit", 24)
        try:
            limit = max(6, min(60, int(raw_limit)))
        except Exception:
            limit = 24

        samples, source, warning, tag_items = await _perform_online_search(query, limit)

        tags = [str(item.get("tag", "")).strip() for item in tag_items if isinstance(item, dict) and str(item.get("tag", "")).strip()]
        tag_items = [item for item in tag_items if isinstance(item, dict) and str(item.get("tag", "")).strip()]
        if not samples and tag_items:
            samples = _构建联网参考样本(
                query,
                tag_items,
                source=source,
                limit=limit,
                warning=warning,
            )

        return _json_response(
            {
                "ok": bool(tag_items),
                "message": (
                    f"已从 {source} 获取 {len(tag_items)} 个候选标签。"
                    if tag_items
                    else "未找到可用候选标签，请尝试更具体的关键词。"
                ),
                "query": query,
                "source": source,
                "tags": tags,
                "tag_items": tag_items,
                "samples": samples,
                "count": len(tag_items),
                "warning": warning,
            },
            status=200,
        )

    @routes.post("/qwen_te/runtime_random_state")
    async def _build_runtime_random_state(request):
        data = await _read_request_json(request)
        try:
            async with preview_worker_semaphore:
                state = await _run_thread_until_done(构建运行时随机预览状态, data)
        except Exception as exc:
            return _json_response(
                {
                    "ok": False,
                    "message": str(exc),
                },
                status=400,
            )
        return _json_response(
            {
                "ok": True,
                "state": state,
            }
        )

    @routes.post("/qwen_te/state_preview")
    async def _build_state_preview(request):
        data = await _read_request_json(request)
        try:
            async with preview_worker_semaphore:
                preview = await _run_thread_until_done(构建状态可视化预览, data)
        except Exception as exc:
            return _json_response(
                {
                    "ok": False,
                    "message": str(exc),
                },
                status=400,
            )
        return _json_response(
            {
                "ok": True,
                "preview": preview,
            }
        )

    @routes.post("/qwen_te/quality_audit")
    async def _quality_audit_images(request):
        data = await _read_request_json(request)
        history_prompt_ids, source_error = _parse_quality_audit_source_request(data)
        if source_error:
            return _json_response(
                {
                    "ok": False,
                    "message": source_error,
                    "result": {
                        "summary": {
                            "total_images": 0,
                            "ocr_risk_images": 0,
                            "wrinkle_risk_images": 0,
                            "oversmooth_risk_images": 0,
                        },
                        "images": [],
                    },
                },
                status=400,
            )
        if _QUALITY_AUDIT_IMPORT_ERROR is not None:
            missing_message = (
                "质检功能当前不可用：缺少依赖 "
                f"`{type(_QUALITY_AUDIT_IMPORT_ERROR).__name__}: {_QUALITY_AUDIT_IMPORT_ERROR}`。"
                " 请安装 `opencv-python` 与 `rapidocr-onnxruntime`。"
            )
            return _json_response(
                {
                    "ok": False,
                    "message": missing_message,
                    "result": {
                        "summary": {
                            "total_images": 0,
                            "ocr_risk_images": 0,
                            "wrinkle_risk_images": 0,
                            "oversmooth_risk_images": 0,
                        },
                        "images": [],
                        "dependency_missing": True,
                    },
                    "markdown": f"# 质检功能不可用\n\n- {missing_message}",
                },
                status=200,
            )
        limit = data.get("limit", 6)
        after_timestamp = data.get("after_timestamp")
        try:
            limit_value = max(1, min(24, int(limit)))
        except Exception:
            limit_value = 6

        async with quality_audit_semaphore:
            image_paths: list[Path]
            if history_prompt_ids:
                image_paths = await _run_thread_until_done(
                    _collect_history_prompt_image_paths,
                    prompt_server,
                    history_prompt_ids,
                    max_images=limit_value,
                )
            else:
                image_paths = await _run_thread_until_done(
                    collect_recent_output_images,
                    limit=limit_value,
                    after_timestamp_ms=after_timestamp,
                )
            image_paths = list(image_paths[:limit_value])

            if not image_paths:
                return _json_response(
                    {
                        "ok": False,
                        "message": "没有找到可质检的图片。",
                        "result": {"summary": {"total_images": 0, "ocr_risk_images": 0, "wrinkle_risk_images": 0, "oversmooth_risk_images": 0}, "images": []},
                    },
                    status=200,
                )

            result = await _run_thread_until_done(audit_images, image_paths)
            markdown = await _run_thread_until_done(build_quality_markdown, result)
        return _json_response(
            {
                "ok": True,
                "message": f"已完成 {result['summary']['total_images']} 张图片的质检。",
                "result": result,
                "markdown": markdown,
            },
            status=200,
        )

    @routes.get("/qwen_te/frontend_probe")
    async def _frontend_probe(request):
        kind = str(request.query.get("kind", "") or "").strip() or "unknown"
        marker = str(request.query.get("marker", "") or "").strip()
        if str(os.environ.get("QWEN_TE_FRONTEND_PROBE_LOG", "")).strip().lower() in {"1", "true", "yes", "on"}:
            logging.info(f"[QwenTE Frontend] probe received: kind={kind}, marker={marker}")
        return _json_response({"ok": True, "kind": kind, "marker": marker}, status=200)

    setattr(prompt_server, _ROUTES_FLAG, True)
    return True


def _ensure_routes_registered() -> None:
    if _register_tag_routes():
        return

    prompt_server_class = _get_prompt_server_class()
    if prompt_server_class is None:
        return

    if getattr(prompt_server_class, _INIT_HOOK_FLAG, False):
        return

    original_init = prompt_server_class.__init__

    @wraps(original_init)
    def _patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _register_tag_routes()

    prompt_server_class.__init__ = _patched_init
    setattr(prompt_server_class, _INIT_HOOK_FLAG, True)


_ensure_routes_registered()


__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]
