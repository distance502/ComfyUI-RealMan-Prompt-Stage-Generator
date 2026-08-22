# -*- coding: utf-8 -*-
import base64
import ctypes
import gc
import inspect
import io
import json
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from functools import wraps

import numpy as np
import torch
import torch.nn.functional as torch_functional
from PIL import Image

import folder_paths
import comfy.model_management as mm

_LLAMA_IMPORT_ERROR = None

try:
    from llama_cpp import Llama
except Exception as exc:
    Llama = None
    _LLAMA_IMPORT_ERROR = exc

try:
    from llama_cpp import llama_cpp as _LLAMA_LOW_LEVEL
except Exception:
    _LLAMA_LOW_LEVEL = None

try:
    from llama_cpp.llama_tokenizer import LlamaTokenizer
except Exception:
    LlamaTokenizer = None

try:
    from llama_cpp import GGML_TYPE_Q8_0
except Exception:
    GGML_TYPE_Q8_0 = 8

try:
    from llama_cpp.llama_chat_format import Qwen3VLChatHandler
except Exception:
    Qwen3VLChatHandler = None

try:
    from llama_cpp.llama_chat_format import Qwen35ChatHandler
except Exception:
    Qwen35ChatHandler = None

try:
    # Newer llama.cpp builds may ship a dedicated Qwen3.8 visual handler.
    # Keep this optional: older builds must still load the GGUF through its
    # embedded chat template or the generic Qwen format.
    from llama_cpp.llama_chat_format import Qwen38ChatHandler
except Exception:
    Qwen38ChatHandler = None

try:
    from llama_cpp.llama_chat_format import Qwen38VLChatHandler
except Exception:
    Qwen38VLChatHandler = None

try:
    from llama_cpp.llama_chat_format import Gemma4ChatHandler
except Exception:
    Gemma4ChatHandler = None

_TRANSFORMERS_IMPORT_ERROR = None
try:
    import transformers as _TRANSFORMERS
except Exception as exc:
    _TRANSFORMERS = None
    _TRANSFORMERS_IMPORT_ERROR = exc


class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False


any_type = AnyType("*")


class _ReentrantLockAdapter:
    _qwen_te_reentrant_lock_adapter = True

    def __init__(self, lock) -> None:
        self._lock = lock
        self._owner: int | None = None
        self._depth = 0

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        owner = threading.get_ident()
        if self._owner == owner:
            self._depth += 1
            return True
        if timeout is None or float(timeout) < 0:
            acquired = self._lock.acquire(blocking)
        else:
            acquired = self._lock.acquire(blocking, float(timeout))
        if acquired:
            self._owner = owner
            self._depth = 1
        return bool(acquired)

    def release(self) -> None:
        if self._owner != threading.get_ident() or self._depth <= 0:
            raise RuntimeError("cannot release un-acquired model storage lock")
        self._depth -= 1
        if self._depth == 0:
            self._owner = None
            self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.release()
        return False

默认图片提示词 = ""
默认图片系统提示词 = (
    "描述这张图，约300字。"
    "先判断这是不是可正常理解的成片图像。"
    "如果画面是整屏方块、棋盘格、随机彩色噪声、latent/VAE 解码损坏、无主体无场景的失败图，"
    "只能把它描述为生成失败或损坏预览，不要幻想人物、服装、场景、姿态或抽象艺术风格。"
    "这类失败图优先输出 failure_output、corrupted_generation、full_frame_noise、square_pixel_blocks、checkerboard_artifacts、"
    "mosaic_noise、no_subject、failed_decode、latent_noise 等诊断性标签。"
    "如果图像主体清晰可辨，再按 主体 -> 外貌/身份 -> 服装 -> 姿态 -> 场景 -> 光线 -> 镜头/构图 -> 风格质量 的顺序反推。"
)
默认文本系统提示词 = "将用户输入扩写为可直接生图的高质量提示词，保持主体不变并补足构图、光线、材质和镜头参数。"
默认KV缓存类型 = "默认(F16)"
Q8_0缓存类型 = "q8_0"
KV缓存类型选项 = [默认KV缓存类型, Q8_0缓存类型]
Flash注意力选项 = ["自动", "开启", "关闭"]
TE通用模型系列选项 = [
    "Qwen3-VL",
    "Qwen3.5-VL",
    "Qwen3.8-VL",
    "Gemma4",
    "Llama",
    "Mistral",
    "DeepSeek",
    "通用模型",
    "通用GGUF",
]
_CHAT_COMPLETION_SIGNATURE_CACHE: dict[type, tuple[inspect.Signature | None, bool]] = {}
_LLAMA_INIT_PARAMS_CACHE: set[str] | None = None
_MODEL_CALL_DEADLINE_PARAM = "_qwen_te_deadline_monotonic"
_MODEL_LOCK_WAIT_POLL_SECONDS = 0.25
_MODEL_STORAGE_LOCK = getattr(mm, "_qwen_te_model_storage_lock", None)
_RLOCK_TYPE = type(threading.RLock())
if not isinstance(_MODEL_STORAGE_LOCK, _RLOCK_TYPE) and not bool(
    getattr(_MODEL_STORAGE_LOCK, "_qwen_te_reentrant_lock_adapter", False)
):
    legacy_lock = _MODEL_STORAGE_LOCK
    if all(callable(getattr(legacy_lock, name, None)) for name in ("acquire", "release")):
        _MODEL_STORAGE_LOCK = _ReentrantLockAdapter(legacy_lock)
    else:
        _MODEL_STORAGE_LOCK = threading.RLock()
mm._qwen_te_model_storage_lock = _MODEL_STORAGE_LOCK
mm._qwen_te_model_storage_lock_version = 2
_MODEL_STORAGE_MODELS = getattr(mm, "_qwen_te_model_storage_models", None)
if not isinstance(_MODEL_STORAGE_MODELS, dict):
    _MODEL_STORAGE_MODELS = {}
    mm._qwen_te_model_storage_models = _MODEL_STORAGE_MODELS
_文本模式基础约束 = (
    "硬约束：除非用户明确指定未成年，否则默认主体必须是成年人。"
    "不要输出“少女/少年/未成年/16-18岁”等低龄词，校园场景统一按成年大学生处理。"
    "避免幼态特征描述（稚嫩、娃娃脸、未发育感）。"
    "默认要求无文字、无水印、无边框、无logo。"
)
_文本模式单段输出约束 = (
    "输出格式仅限一段可直接生图的提示词，不要章节标题、说明文字、序号和总结；避免重复语句。"
)
_文本模式结构化输出约束 = (
    "如果用户明确要求“案例长段版”“案例分段版”、标题+正文+标签解析+适用模型，或给出了明确排版示例，"
    "必须优先遵守该结构化格式要求，不要强行改写成单段提示词。"
)
_低龄输入请求模式 = re.compile(r"(未成年|少女|少年|儿童|萝莉|幼态|小女孩|小男孩|中学|高中生|初中生)", flags=re.IGNORECASE)
_低龄年龄段模式 = re.compile(r"(?<!\d)(1[0-8])\s*(?:[-~至到]\s*(1[0-9]))?\s*岁")
_低龄词替换映射 = {
    "少女": "成年女性",
    "少年": "成年男性",
    "女孩": "成年女性",
    "男孩": "成年男性",
    "女生": "成年女性",
    "男生": "成年男性",
    "未成年": "成年",
}
_模型噪声LoRA模式 = re.compile(r"<\s*lora:[^>]+>", flags=re.IGNORECASE)
_模型噪声评分标签模式 = re.compile(r"\bscore_[0-9]+(?:_up)?\b", flags=re.IGNORECASE)
_模型噪声内嵌模式 = re.compile(r"\b(?:embedding|hypernet)\s*:[^\s,;，；]+", flags=re.IGNORECASE)


def _确保_llm目录已注册() -> None:
    folder_name = "LLM"
    llm_dir = os.path.join(folder_paths.models_dir, folder_name)

    supported_exts = set(getattr(folder_paths, "supported_pt_extensions", set()))
    llm_exts = supported_exts | {".gguf"}

    try:
        if folder_name not in folder_paths.folder_names_and_paths:
            folder_paths.folder_names_and_paths[folder_name] = ([llm_dir], llm_exts)
            return

        paths, exts = folder_paths.folder_names_and_paths[folder_name]
        if llm_dir not in paths:
            paths.append(llm_dir)

        if isinstance(exts, set):
            exts.update(llm_exts)
        else:
            folder_paths.folder_names_and_paths[folder_name] = (paths, set(exts) | llm_exts)
    except Exception:
        # 不阻断 ComfyUI 启动；后续节点会提示更具体错误
        return


_原始模型权重扩展名 = {".safetensors", ".bin", ".pt", ".pth", ".ckpt"}
_本地模型选项扩展名 = _原始模型权重扩展名 | {".gguf"}


def _llm根目录() -> str:
    _确保_llm目录已注册()
    return os.path.join(folder_paths.models_dir, "LLM")


def _规范化模型相对路径(value: object) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    raw = raw.lstrip("/")
    if raw in ("", "."):
        return ""
    root = os.path.abspath(_llm根目录())
    candidate = os.path.abspath(os.path.join(root, raw.replace("/", os.sep)))
    try:
        if os.path.commonpath((root, candidate)) != root:
            return ""
    except ValueError:
        return ""
    return os.path.relpath(candidate, root).replace("\\", "/")


def _原始模型目录有效(model_dir: str) -> bool:
    if not os.path.isdir(model_dir):
        return False
    if not os.path.isfile(os.path.join(model_dir, "config.json")):
        return False
    try:
        return any(
            os.path.splitext(name)[1].lower() in _原始模型权重扩展名
            for name in os.listdir(model_dir)
        )
    except OSError:
        return False


def _是本地模型选项(value: object) -> bool:
    """Return whether a selector value is a GGUF file or a Transformers model root."""

    normalized = _规范化模型相对路径(value)
    if not normalized:
        # Focused tests often provide virtual file names without creating them.
        return os.path.splitext(str(value or ""))[1].lower() in _本地模型选项扩展名
    full_path = os.path.join(_llm根目录(), normalized.replace("/", os.sep))
    if os.path.isdir(full_path):
        return _原始模型目录有效(full_path)
    return os.path.splitext(full_path)[1].lower() in _本地模型选项扩展名


def _本地模型格式(value: object) -> str:
    """Infer the backend from a selector value without opening the model."""

    normalized = _规范化模型相对路径(value)
    if not normalized:
        normalized = str(value or "").strip().replace("\\", "/")
    return "gguf" if os.path.splitext(normalized)[1].lower() == ".gguf" else "transformers"


def _推断本地模型系列(value: object) -> str:
    """Infer a loader family only when the model name is unambiguous."""

    text = str(value or "").strip().lower().replace("\\", "/")
    compact = re.sub(r"[^a-z0-9.]+", "", text)
    if not compact:
        return ""
    if (
        "qwen3.8" in text
        or "qwen3_8" in text
        or re.search(r"(?:^|[/_.-])qwen38(?:[/_.-]|vl|$)", text)
    ):
        return "Qwen3.8-VL"
    # Qwen3.6 uses the Qwen3.5 llama.cpp architecture/handler family.
    if (
        "qwen3.5" in text
        or "qwen3_5" in text
        or "qwen3.6" in text
        or "qwen3_6" in text
        or re.search(r"(?:^|[/_.-])qwen3[56](?:[/_.-]|vl|$)", text)
        or re.search(r"(?:^|[/_.-])3[._]5mmproj", text)
    ):
        return "Qwen3.5-VL"
    if re.search(r"qwen3(?:[-_]vl|[-_]\d+[bma]|$)", text) or "qwen3vl" in compact:
        return "Qwen3-VL"
    if "gemma4" in compact or re.search(r"gemma[._-]*4(?:[^0-9]|$)", text):
        return "Gemma4"
    if "deepseek" in text:
        return "DeepSeek"
    if "mistral" in text or "mixtral" in text:
        return "Mistral"
    if "llama" in text:
        return "Llama"
    return ""


def _推断qwen3模型版本(value: object) -> str:
    """Return an explicit Qwen3.x revision without confusing parameter sizes."""

    text = str(value or "").strip().lower().replace("\\", "/")
    if "qwen3.8" in text or "qwen3_8" in text or re.search(r"(?:^|[/_.-])qwen38(?:[/_.-]|vl|$)", text):
        return "3.8"
    if "qwen3.6" in text or "qwen3_6" in text or re.search(r"(?:^|[/_.-])qwen36(?:[/_.-]|vl|$)", text):
        return "3.6"
    if (
        "qwen3.5" in text
        or "qwen3_5" in text
        or re.search(r"(?:^|[/_.-])qwen35(?:[/_.-]|vl|$)", text)
        or re.search(r"(?:^|[/_.-])3[._]5mmproj", text)
    ):
        return "3.5"
    return ""


def _规范化本地模型配置(config: dict) -> dict:
    """Resolve obvious family choices and reject cross-family vision pairs."""

    resolved = dict(config or {})
    resolved.pop("family_auto_note", None)
    requested = str(resolved.get("family") or "通用GGUF").strip() or "通用GGUF"
    model_name = str(resolved.get("model") or "").strip()
    mmproj_name = str(resolved.get("mmproj") or "无").strip()
    model_family = _推断本地模型系列(model_name)
    mmproj_family = "" if mmproj_name in {"", "无"} else _推断本地模型系列(mmproj_name)
    if model_family and mmproj_family and model_family != mmproj_family:
        raise RuntimeError(
            "主模型与视觉投影 mmproj 属于不同模型家族："
            f"主模型识别为 {model_family}，mmproj 识别为 {mmproj_family}。"
            "请选择与主模型同版本的 mmproj，纯文本调用则把视觉投影设为“无”。"
        )
    model_revision = _推断qwen3模型版本(model_name)
    mmproj_revision = "" if mmproj_name in {"", "无"} else _推断qwen3模型版本(mmproj_name)
    if model_revision and mmproj_revision and model_revision != mmproj_revision:
        raise RuntimeError(
            "主模型与视觉投影 mmproj 属于不同 Qwen3 版本："
            f"主模型为 Qwen3.{model_revision.split('.', 1)[1]}，"
            f"mmproj 为 Qwen3.{mmproj_revision.split('.', 1)[1]}。"
            "Qwen3.5 与 Qwen3.6 虽共用兼容 handler，但视觉投影不可互换。"
        )

    inferred = model_family or mmproj_family
    effective = inferred or requested
    resolved["family"] = effective
    if inferred and requested != inferred:
        resolved["family_auto_note"] = (
            f"本地模型智能识别：根据主模型/mmproj 将模型系列从“{requested}”纠正为“{inferred}”。"
        )
    elif inferred == "Qwen3.5-VL" and re.search(r"qwen3[._]6|qwen36", model_name, re.IGNORECASE):
        resolved["family_auto_note"] = (
            "本地模型智能识别：Qwen3.6 使用当前 llama.cpp 的 Qwen3.5 兼容家族与模型内嵌聊天模板。"
        )
    return resolved


def _解析本地模型路径(value: object) -> tuple[str, str]:
    normalized = _规范化模型相对路径(value)
    if not normalized:
        raise ValueError("本地模型路径为空或超出 ComfyUI/models/LLM 目录。")
    full_path = os.path.join(_llm根目录(), normalized.replace("/", os.sep))
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"找不到模型文件或目录：{full_path}")
    if os.path.isdir(full_path):
        if not _原始模型目录有效(full_path):
            raise RuntimeError(f"原始模型目录缺少 config.json 或权重文件：{full_path}")
        return full_path, "transformers"
    if os.path.splitext(full_path)[1].lower() == ".gguf":
        return full_path, "gguf"
    if os.path.splitext(full_path)[1].lower() in _原始模型权重扩展名:
        parent = os.path.dirname(full_path)
        if _原始模型目录有效(parent):
            return parent, "transformers"
        raise RuntimeError(
            f"原始模型权重旁边缺少完整模型目录：{parent}\n"
            "需要同目录的 config.json、tokenizer 文件和完整权重分片。"
        )
    raise ValueError(f"不支持的本地模型格式：{full_path}")


def _列出llm文件() -> list[str]:
    llm_dir = _llm根目录()
    values: set[str] = set()
    try:
        values.update(str(item).replace("\\", "/") for item in folder_paths.get_filename_list("LLM"))
    except Exception:
        pass

    # ComfyUI's filename registry intentionally omits model directories. Scan
    # the plugin-owned root so Hugging Face layouts with config.json become
    # selectable while keeping the existing flat GGUF entries intact.
    if os.path.isdir(llm_dir):
        for root, dirs, files in os.walk(llm_dir):
            dirs[:] = [name for name in dirs if not name.startswith(".")]
            relative_root = os.path.relpath(root, llm_dir).replace("\\", "/")
            if relative_root != "." and _原始模型目录有效(root):
                values.add(relative_root)
            for filename in files:
                if os.path.splitext(filename)[1].lower() not in _本地模型选项扩展名:
                    continue
                relative = os.path.relpath(os.path.join(root, filename), llm_dir).replace("\\", "/")
                values.add(relative)

    return sorted(values, key=lambda item: (item.lower().count("/"), item.lower()))


def _图片转base64(image_tensor) -> str:
    """
    编码为 JPEG base64。
    """
    if image_tensor is None:
        return ""

    img = image_tensor[0].cpu().numpy()
    return _图片数组转base64(img, 最大边长=0)


def _编码PIL为JPEG_base64(pil: Image.Image) -> str:
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _缩放图片到最大边(pil: Image.Image, 最大边长: int) -> Image.Image:
    if 最大边长 <= 0:
        return pil
    w, h = pil.size
    long_edge = max(w, h)
    if long_edge <= 最大边长:
        return pil
    scale = 最大边长 / float(long_edge)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return pil.resize((new_w, new_h), resample=Image.BICUBIC)


def _图片数组转base64(image_array: np.ndarray, 最大边长: int) -> str:
    source = np.asarray(image_array)
    if source.ndim < 2:
        raise ValueError("图片数组至少需要二维空间尺寸。")
    height, width = int(source.shape[0]), int(source.shape[1])
    resized_before_convert = False
    if 最大边长 > 0 and max(width, height) > 最大边长:
        scale = float(最大边长) / float(max(width, height))
        target_width = max(1, int(round(width * scale)))
        target_height = max(1, int(round(height * scale)))
        try:
            if source.dtype != np.float32 or source.ndim not in {2, 3}:
                raise TypeError("area resize requires a float32 image array")
            tensor = torch.from_numpy(source)
            squeeze_channel = tensor.ndim == 2
            if squeeze_channel:
                tensor = tensor.unsqueeze(-1)
            tensor = tensor.permute(2, 0, 1).unsqueeze(0)
            resized = torch_functional.interpolate(
                tensor,
                size=(target_height, target_width),
                mode="area",
            )[0].permute(1, 2, 0)
            source = resized[..., 0].numpy() if squeeze_channel else resized.numpy()
        except (AttributeError, TypeError, ValueError):
            y_indices = np.linspace(0, height - 1, target_height, dtype=np.intp)
            x_indices = np.linspace(0, width - 1, target_width, dtype=np.intp)
            source = source[y_indices[:, None], x_indices[None, :]]
        resized_before_convert = True
    if np.issubdtype(source.dtype, np.floating):
        working = source if resized_before_convert else np.array(source, copy=True)
        np.clip(working, 0.0, 1.0, out=working)
        working *= 255.0
        img = working.astype(np.uint8)
    else:
        img = np.clip(source, 0, 255).astype(np.uint8)
    pil = Image.fromarray(img)
    pil = _缩放图片到最大边(pil, 最大边长)
    return _编码PIL为JPEG_base64(pil)


def _批量图片索引转base64(image_tensor, index: int, 最大边长: int) -> str:
    if image_tensor is None:
        return ""
    if index < 0 or index >= int(image_tensor.shape[0]):
        return ""
    img = image_tensor[index].cpu().numpy()
    return _图片数组转base64(img, 最大边长)


def _去重帧索引(frame_indices: list[int]) -> list[int]:
    unique_indices: list[int] = []
    seen: set[int] = set()
    for raw_index in frame_indices:
        index = int(raw_index)
        if index in seen:
            continue
        seen.add(index)
        unique_indices.append(index)
    return unique_indices


_MAX_MULTIFRAME_INFERENCE_FRAMES = 64
_MAX_IMAGE_INFERENCE_EDGE = 4096
_MAX_MULTIFRAME_TOTAL_PIXEL_BUDGET = 64 * 1024 * 1024
_MAX_MULTIFRAME_DATA_URL_BYTES = 64 * 1024 * 1024


def _多帧预算最大边长(frame_count: int, requested_edge: int) -> int:
    count = max(1, int(frame_count))
    budget_edge = math.isqrt(max(1, _MAX_MULTIFRAME_TOTAL_PIXEL_BUDGET // count))
    return max(128, min(_MAX_IMAGE_INFERENCE_EDGE, budget_edge, int(requested_edge)))


def _批量帧索引转data_url(image_tensor, frame_indices: list[int], 最大边长: int) -> dict[int, str]:
    if image_tensor is None or not frame_indices:
        return {}

    total_images = int(image_tensor.shape[0])
    valid_indices = _去重帧索引([index for index in frame_indices if 0 <= int(index) < total_images])
    if len(valid_indices) > _MAX_MULTIFRAME_INFERENCE_FRAMES:
        raise ValueError(
            f"单次多帧推理最多处理 {_MAX_MULTIFRAME_INFERENCE_FRAMES} 帧；"
            "请改用视频模式抽帧或拆分批次。"
        )
    if not valid_indices:
        return {}

    最大边长 = _多帧预算最大边长(len(valid_indices), 最大边长)

    encoded: dict[int, str] = {}
    encoded_bytes = 0
    for frame_index in valid_indices:
        if mm.processing_interrupted():
            raise mm.InterruptProcessingException()
        try:
            frame_array = image_tensor[frame_index : frame_index + 1].cpu().numpy()
            if getattr(frame_array, "ndim", 0) == 4 and int(frame_array.shape[0]) == 1:
                frame_array = frame_array[0]
            img_b64 = _图片数组转base64(frame_array, 最大边长)
        except (AttributeError, IndexError, TypeError, ValueError):
            img_b64 = _批量图片索引转base64(image_tensor, frame_index, 最大边长)
        if img_b64:
            data_url = f"data:image/jpeg;base64,{img_b64}"
            encoded_bytes += len(data_url)
            if encoded_bytes > _MAX_MULTIFRAME_DATA_URL_BYTES:
                raise ValueError(
                    f"单次多帧推理编码载荷超过 {_MAX_MULTIFRAME_DATA_URL_BYTES // (1024 * 1024)} MiB；"
                    "请减少帧数或最大边长。"
                )
            encoded[frame_index] = data_url
    return encoded


def _预编码帧data_url(
    image_tensor,
    frame_indices: list[int],
    最大边长: int,
    *,
    最大预编码帧数: int = 64,
) -> dict[int, str]:
    device = getattr(image_tensor, "device", None)
    device_type = str(getattr(device, "type", "") or "").strip().lower()
    if device_type in {"", "cpu"}:
        return {}
    unique_count = len(_去重帧索引(frame_indices))
    if unique_count <= 0 or unique_count > 最大预编码帧数:
        return {}
    return _批量帧索引转data_url(image_tensor, frame_indices, 最大边长)


def _视频抽帧索引(total_images: int, 最多帧数: int) -> list[int]:
    if total_images <= 1:
        return [0] if total_images == 1 else []
    count = min(max(int(最多帧数), 2), total_images)
    sampled = np.linspace(0, total_images - 1, count)
    return _去重帧索引([int(round(item)) for item in sampled])


def _图像推理最大生成token(
    *,
    输入模式: str,
    提示词: str,
    系统提示词: str,
    最大生成token: int,
) -> int:
    token_limit = int(最大生成token)
    if token_limit <= 0 or 输入模式 == "文本":
        return token_limit

    prompt_text = str(提示词 or "").strip()
    system_text = str(系统提示词 or "").strip()
    default_reverse_prompt = system_text == 默认图片系统提示词 or system_text.endswith(默认图片系统提示词)
    if prompt_text or not default_reverse_prompt:
        return token_limit
    return min(token_limit, 512)


def _文本模式要求结构化输出(prompt_text: str) -> bool:
    text = str(prompt_text or "")
    markers = (
        "案例长段版",
        "案例分段版",
        "标签解析",
        "适用模型",
        "单行提示词正文",
        "### 提示词",
        "Label Analysis",
        "Applicable Models",
    )
    return any(marker in text for marker in markers)


def _增强文本模式系统提示词(system_text: str, user_prompt: str = "") -> str:
    normalized = str(system_text or "").strip()
    constraints = [
        _文本模式基础约束,
        _文本模式结构化输出约束 if _文本模式要求结构化输出(user_prompt) else _文本模式单段输出约束,
    ]
    merged_constraints = "\n".join(constraints)
    if all(part in normalized for part in constraints):
        return normalized
    if not normalized or normalized in {默认图片系统提示词, 默认文本系统提示词}:
        return f"{默认文本系统提示词}\n{merged_constraints}"
    return f"{normalized}\n{merged_constraints}"


def _文本结果去低龄化(text: str, user_prompt: str) -> str:
    normalized_text = str(text or "")
    if not normalized_text:
        return normalized_text
    prompt_text = str(user_prompt or "")
    if _低龄输入请求模式.search(prompt_text):
        return normalized_text

    normalized_text = _低龄年龄段模式.sub("22岁", normalized_text)
    for source, target in _低龄词替换映射.items():
        normalized_text = normalized_text.replace(source, target)
    return normalized_text


def _清理模型专有提示词噪声(text: str) -> str:
    normalized_text = str(text or "")
    if not normalized_text:
        return normalized_text
    normalized_text = _模型噪声LoRA模式.sub("", normalized_text)
    normalized_text = _模型噪声评分标签模式.sub("", normalized_text)
    normalized_text = _模型噪声内嵌模式.sub("", normalized_text)
    normalized_text = re.sub(r"[,，;；]{2,}", ", ", normalized_text)
    normalized_text = re.sub(r"\s{2,}", " ", normalized_text)
    normalized_text = re.sub(r"\s*[,，;；]\s*$", "", normalized_text)
    return normalized_text.strip()


def _规范化模型调用截止时间(value) -> float | None:
    try:
        deadline = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return deadline if 0.0 < deadline < float("inf") else None


def _检查Comfy处理中断() -> None:
    checker = getattr(mm, "processing_interrupted", None)
    if callable(checker) and bool(checker()):
        error_type = getattr(mm, "InterruptProcessingException", RuntimeError)
        raise error_type()


def _合作获取模型存储锁(deadline_monotonic: float | None) -> bool:
    while True:
        _检查Comfy处理中断()
        wait_seconds = _MODEL_LOCK_WAIT_POLL_SECONDS
        if deadline_monotonic is not None:
            remaining = deadline_monotonic - time.monotonic()
            if remaining <= 0.0:
                return False
            wait_seconds = min(wait_seconds, remaining)
        acquired = bool(_MODEL_STORAGE_LOCK.acquire(timeout=wait_seconds))
        if not acquired:
            continue
        try:
            _检查Comfy处理中断()
        except BaseException:
            _MODEL_STORAGE_LOCK.release()
            raise
        return True


def _安装llama合作中断(llm, deadline_monotonic: float | None):
    low_level = _LLAMA_LOW_LEVEL
    callback_type = getattr(low_level, "ggml_abort_callback", None)
    set_callback = getattr(low_level, "llama_set_abort_callback", None)
    context_wrapper = getattr(llm, "_ctx", None)
    context = getattr(context_wrapper, "ctx", None)
    if callback_type is None or not callable(set_callback) or context is None:
        return None

    state = {"timed_out": False, "interrupted": False, "disabled": False}

    def should_abort(_data) -> bool:
        try:
            if state.get("disabled"):
                return False
            if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
                state["timed_out"] = True
                return True
            interrupted = getattr(mm, "processing_interrupted", None)
            if callable(interrupted) and bool(interrupted()):
                state["interrupted"] = True
                return True
        except Exception:
            return False
        return False

    try:
        callback = callback_type(should_abort)
        null_data = ctypes.c_void_p()
        set_callback(context, callback, null_data)
    except Exception:
        return None

    def cleanup() -> bool:
        try:
            set_callback(context, callback_type(), ctypes.c_void_p())
        except Exception:
            state["disabled"] = True
            return False
        return True

    guard = (callback, state, cleanup)
    try:
        llm._qwen_te_abort_callback_guard = guard
    except Exception:
        pass
    return guard


def _执行chat_completion(
    llm,
    *,
    messages,
    params: dict,
    owner_storage=None,
    deadline_monotonic: float | None = None,
    _allow_recover: bool = True,
) -> dict:
    """
    兼容不同 llama-cpp-python 版本的参数名差异（例如 presence_penalty vs present_penalty）。
    """
    if owner_storage is not None:
        _重置llm推理状态(llm)

    try:
        candidates = [
            getattr(llm, "model_path", None),
            getattr(llm, "_model_path", None),
            getattr(llm, "__class__", type(llm)).__name__,
        ]
        model_descriptor = " ".join(str(item) for item in candidates if item)
        managed_settings = getattr(llm, "_qwen_te_settings", None)
        prefer_embedded_template = isinstance(managed_settings, dict) and _应使用llama内置聊天模板(
            family=managed_settings.get("family"),
            model_name=managed_settings.get("model") or model_descriptor,
        )
        guessed_chat_format = _推断llama默认聊天格式(
            family=managed_settings.get("family") if isinstance(managed_settings, dict) else None,
            model_name=managed_settings.get("model") if isinstance(managed_settings, dict) else model_descriptor,
        )
        _应用llama聊天格式兜底(
            llm,
            guessed_chat_format,
            prefer_embedded_template=prefer_embedded_template,
        )
    except Exception:
        pass

    kwargs = dict(params or {})
    kwargs.pop(_MODEL_CALL_DEADLINE_PARAM, None)
    kwargs["messages"] = messages

    llm_type = type(llm)
    cached = _CHAT_COMPLETION_SIGNATURE_CACHE.get(llm_type)
    if cached is None:
        try:
            sig = inspect.signature(llm.create_chat_completion)
            has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        except Exception:
            sig = None
            has_var_kw = True
        _CHAT_COMPLETION_SIGNATURE_CACHE[llm_type] = (sig, has_var_kw)
    else:
        sig, has_var_kw = cached

    if sig is not None and not has_var_kw:
        allowed = sig.parameters
        if "presence_penalty" in kwargs and "presence_penalty" not in allowed and "present_penalty" in allowed:
            kwargs["present_penalty"] = kwargs.pop("presence_penalty")
        if "present_penalty" in kwargs and "present_penalty" not in allowed and "presence_penalty" in allowed:
            kwargs["presence_penalty"] = kwargs.pop("present_penalty")
        kwargs = {k: v for k, v in kwargs.items() if k in allowed}

    abort_guard = _安装llama合作中断(llm, deadline_monotonic)
    abort_state = abort_guard[1] if abort_guard is not None else {}
    abort_cleaned = False

    def cleanup_abort_callback() -> bool:
        nonlocal abort_cleaned
        if abort_cleaned:
            return True
        if abort_guard is None:
            abort_cleaned = True
            return True
        if not abort_guard[2]():
            return False
        abort_cleaned = True
        try:
            if getattr(llm, "_qwen_te_abort_callback_guard", None) is abort_guard:
                del llm._qwen_te_abort_callback_guard
        except Exception:
            pass
        return True

    try:
        try:
            try:
                result = llm.create_chat_completion(**kwargs)
            except Exception as format_error:
                if not _尝试修复llama无效聊天格式(llm, format_error, guessed_chat_format):
                    raise
                _重置llm推理状态(llm)
                result = llm.create_chat_completion(**kwargs)
            if deadline_monotonic is not None and time.monotonic() >= deadline_monotonic:
                abort_state["timed_out"] = True
                raise TimeoutError("本地模型推理已超过截止时间，结果已丢弃。")
            interrupted = getattr(mm, "processing_interrupted", None)
            if callable(interrupted) and bool(interrupted()):
                abort_state["interrupted"] = True
                interrupt_error = getattr(mm, "InterruptProcessingException", RuntimeError)
                raise interrupt_error()
            return result
        except (OSError, AttributeError, RuntimeError) as error:
            deadline_expired = deadline_monotonic is not None and time.monotonic() >= deadline_monotonic
            if abort_state.get("timed_out") or deadline_expired:
                raise TimeoutError("本地模型推理超过截止时间，已请求 llama.cpp 合作中止。") from error
            interrupted = abort_state.get("interrupted")
            if not interrupted:
                interrupted_check = getattr(mm, "processing_interrupted", None)
                try:
                    interrupted = callable(interrupted_check) and bool(interrupted_check())
                except Exception:
                    interrupted = False
            if interrupted:
                interrupt_error = getattr(mm, "InterruptProcessingException", RuntimeError)
                raise interrupt_error() from error
            if not _allow_recover or not _应尝试恢复llama异常(error):
                raise
            if deadline_monotonic is not None:
                raise
            settings = getattr(llm, "_qwen_te_settings", None)
            if not isinstance(settings, dict):
                raise
            cleanup_abort_callback()
            recovered_llm = _按设置重载托管模型(
                settings,
                force_reload=True,
                owner_storage=owner_storage or getattr(llm, "_qwen_te_storage_owner", None),
            )
            if recovered_llm is None or recovered_llm is llm:
                raise
            return _调用chat_completion(
                recovered_llm,
                messages=messages,
                params=params,
                _allow_recover=False,
                _deadline_monotonic=deadline_monotonic,
            )
    finally:
        cleanup_abort_callback()


def _调用chat_completion(
    llm,
    *,
    messages,
    params: dict,
    _allow_recover: bool = True,
    _deadline_monotonic: float | None = None,
) -> dict:
    call_params = dict(params or {})
    if bool(call_params.get("stream", False)):
        raise ValueError("QwenTE 托管模型调用不支持 stream=True；流式迭代无法安全覆盖模型锁和中断回调生命周期。")
    deadline_monotonic = _规范化模型调用截止时间(
        _deadline_monotonic
        if _deadline_monotonic is not None
        else call_params.pop(_MODEL_CALL_DEADLINE_PARAM, None)
    )
    settings = getattr(llm, "_qwen_te_settings", None)
    owner_storage = _解析llm托管存储(llm, settings)
    if owner_storage is None:
        _重置llm推理状态(llm)
        return _执行chat_completion(
            llm,
            messages=messages,
            params=call_params,
            owner_storage=None,
            deadline_monotonic=deadline_monotonic,
            _allow_recover=_allow_recover,
        )

    acquired = _合作获取模型存储锁(deadline_monotonic)
    if not acquired:
        raise TimeoutError("本地模型等待可用推理槽位超过截止时间。")
    try:
        active_llm = _同步托管llm实例(llm, settings, owner_storage)
        return _执行chat_completion(
            active_llm,
            messages=messages,
            params=call_params,
            owner_storage=owner_storage,
            deadline_monotonic=deadline_monotonic,
            _allow_recover=_allow_recover,
        )
    finally:
        _MODEL_STORAGE_LOCK.release()


def _清洗think块文本(text: str) -> str:
    if not isinstance(text, str) or not text:
        return "" if text is None else str(text)

    cleaned = text
    cleaned = re.sub(r"<think\b[^>]*>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

    if re.search(r"</think>", cleaned, flags=re.IGNORECASE):
        cleaned = re.sub(r"^.*?</think>\s*", "", cleaned, count=1, flags=re.DOTALL | re.IGNORECASE)

    cleaned = cleaned.replace("<think>", "").replace("</think>", "")
    return cleaned


def _清洗gemma4输出文本(text: str, 保留think块: bool) -> str:
    if not isinstance(text, str) or not text:
        return "" if text is None else str(text)

    cleaned = text.replace("\r\n", "\n")

    if not 保留think块 and "<channel|>" in cleaned:
        cleaned = re.sub(r"^.*?<channel\|>\s*", "", cleaned, count=1, flags=re.DOTALL)

    if not 保留think块:
        cleaned = re.sub(r"<think\b[^>]*>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if re.search(r"</think>", cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(r"^.*?</think>\s*", "", cleaned, count=1, flags=re.DOTALL | re.IGNORECASE)

    cleaned = re.sub(r"<\|channel\>\s*[\w-]*\s*\n?", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("<channel|>", "")
    cleaned = cleaned.replace("<|think|>", "")
    cleaned = cleaned.replace("<think>", "").replace("</think>", "")
    return cleaned.strip()


def _llama构造参数是否可用(param_name: str) -> bool | None:
    global _LLAMA_INIT_PARAMS_CACHE

    if Llama is None:
        return None

    if _LLAMA_INIT_PARAMS_CACHE is None:
        try:
            sig = inspect.signature(Llama.__init__)
        except Exception:
            return None
        _LLAMA_INIT_PARAMS_CACHE = set(sig.parameters)

    return param_name in _LLAMA_INIT_PARAMS_CACHE


def _规范化llama高级加载参数(config: dict) -> dict[str, object]:
    """Normalize optional Llama constructor settings without changing legacy defaults."""

    def integer(name: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(config.get(name, default))
        except (TypeError, ValueError):
            value = default
        return max(minimum, min(maximum, value))

    def real(name: str, default: float, minimum: float, maximum: float) -> float:
        try:
            value = float(config.get(name, default))
        except (TypeError, ValueError):
            value = default
        if not math.isfinite(value):
            value = default
        return max(minimum, min(maximum, value))

    flash = str(config.get("flash_attn", "自动") or "自动").strip()
    if flash not in Flash注意力选项:
        flash = "自动"
    n_batch = integer("n_batch", 2048, 32, 131072)
    n_ubatch = min(n_batch, integer("n_ubatch", 512, 32, 131072))
    return {
        "n_batch": n_batch,
        "n_ubatch": n_ubatch,
        "n_threads": integer("n_threads", 0, 0, 512),
        "n_threads_batch": integer("n_threads_batch", 0, 0, 512),
        "flash_attn": flash,
        "offload_kqv": bool(config.get("offload_kqv", True)),
        "use_mmap": bool(config.get("use_mmap", True)),
        "use_mlock": bool(config.get("use_mlock", False)),
        "rope_freq_base": real("rope_freq_base", 0.0, 0.0, 1_000_000.0),
        "rope_freq_scale": real("rope_freq_scale", 0.0, 0.0, 100.0),
    }


def _加入llama高级加载参数(llama_kwargs: dict[str, object], config: dict) -> None:
    """Add only constructor keywords supported by the installed llama-cpp-python."""

    options = _规范化llama高级加载参数(config)
    for name in ("n_batch", "n_ubatch", "n_threads", "n_threads_batch"):
        value = int(options[name])
        # Zero means "let llama.cpp decide" for thread counts.
        if name.startswith("n_threads") and value <= 0:
            continue
        if _llama构造参数是否可用(name) is True:
            llama_kwargs[name] = value

    for name in ("offload_kqv", "use_mmap", "use_mlock"):
        if _llama构造参数是否可用(name) is True:
            llama_kwargs[name] = bool(options[name])

    for name in ("rope_freq_base", "rope_freq_scale"):
        value = float(options[name])
        # 0.0 preserves the model's metadata/default RoPE settings.
        if value > 0.0 and _llama构造参数是否可用(name) is True:
            llama_kwargs[name] = value

    flash_value = {"自动": -1, "关闭": 0, "开启": 1}[str(options["flash_attn"])]
    if _llama构造参数是否可用("flash_attn_type") is True:
        llama_kwargs["flash_attn_type"] = flash_value
    elif _llama构造参数是否可用("flash_attn") is True:
        llama_kwargs["flash_attn"] = flash_value == 1


_LLAMA_CUSTOM_BLOCKED_PARAMS = {
    "model_path",
    "chat_handler",
    "chat_format",
    "tokenizer",
    "draft_model",
    "n_ctx",
    "n_gpu_layers",
    "ctx_checkpoints",
    "type_k",
    "type_v",
    "verbose",
}


def _解析llama自定义参数(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        parsed = dict(value)
    elif value is None or not str(value).strip():
        return {}
    else:
        try:
            parsed = json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("本地模型参数JSON必须是合法 JSON 对象。") from exc
    if not isinstance(parsed, dict):
        raise ValueError("本地模型参数JSON必须是 JSON 对象，例如 {\"n_seq_max\": 2}。")
    return {str(key).strip(): item for key, item in parsed.items() if str(key).strip()}


def _加入llama自定义参数(llama_kwargs: dict[str, object], config: dict) -> None:
    """Apply user JSON parameters that the installed Llama accepts.

    The explicit node controls remain authoritative for model identity and
    chat formatting. Unsupported keys are ignored for older llama.cpp builds
    instead of making the whole local-model route fail.
    """

    custom = _解析llama自定义参数(config.get("custom_llama_params"))
    for name, value in custom.items():
        if name in _LLAMA_CUSTOM_BLOCKED_PARAMS:
            continue
        if _llama构造参数是否可用(name) is not True:
            continue
        llama_kwargs[name] = value


def _应使用llama内置聊天模板(*, family: str | None = None, model_name: str | None = None) -> bool:
    # Only an explicit Qwen3.x revision should prefer the embedded template.
    # A plain Qwen3 model often has a size suffix such as ``Qwen3-8B``; a
    # compact ``qwen3[5-9]`` search would mistake that 8B size for Qwen3.8.
    haystack = f"{family or ''} {model_name or ''}".lower()
    return bool(re.search(r"qwen3(?:[._]?)[5-9](?:[^0-9]|$)", haystack))


def _是qwen38系列(*, family: str | None = None, model_name: str | None = None) -> bool:
    haystack = re.sub(r"[^a-z0-9]+", "", f"{family or ''} {model_name or ''}".lower())
    return "qwen38" in haystack


def _构造qwen38视觉处理器(mmproj_path: str, think: bool):
    """Construct an optional Qwen3.8 handler without making it a dependency.

    Handler signatures have changed across llama-cpp-python releases.  Try
    the known names and argument variants, then return ``None`` so the caller
    can use the GGUF embedded template when this runtime predates Qwen3.8.
    """

    handlers = [Qwen38VLChatHandler, Qwen38ChatHandler]
    seen: set[type] = set()
    for handler_type in handlers:
        if handler_type is None or handler_type in seen:
            continue
        seen.add(handler_type)
        attempts = (
            {"clip_model_path": mmproj_path, "enable_thinking": think, "add_vision_id": True, "verbose": False},
            {"clip_model_path": mmproj_path, "force_reasoning": think, "verbose": False},
            {"clip_model_path": mmproj_path, "use_think_prompt": think, "verbose": False},
            {"clip_model_path": mmproj_path, "verbose": False},
            {"clip_model_path": mmproj_path},
        )
        for kwargs in attempts:
            try:
                return handler_type(**kwargs)
            except (TypeError, ValueError):
                continue
            except Exception:
                # A handler can be present but reject a newer mmproj.  Keep
                # loading the text path and let the normal Skill fallback
                # report image-specific incompatibility instead of failing
                # the whole node at model-load time.
                break
    return None


def _推断llama默认聊天格式(*, family: str | None = None, model_name: str | None = None) -> str | None:
    haystack = f"{family or ''} {model_name or ''}".lower()
    if _应使用llama内置聊天模板(family=family, model_name=model_name):
        return None
    if "gemma" in haystack:
        return "gemma"
    if "qwen" in haystack:
        return "qwen"
    if "llama" in haystack:
        if re.search(r"llama[\s._-]*4", haystack):
            return "llama-4"
        if re.search(r"llama[\s._-]*2", haystack):
            return "llama-2"
        return "llama-3"
    if "mistral" in haystack:
        return "mistral-instruct"
    if "deepseek" in haystack:
        return "chatml"
    return None


def _应用llama聊天格式兜底(
    llm: object,
    chat_format: str | None,
    *,
    prefer_embedded_template: bool = False,
) -> None:
    if not chat_format:
        chat_format = None
    try:
        current = getattr(llm, "chat_format", None)
    except Exception:
        current = None
    try:
        chat_handler = getattr(llm, "chat_handler", None)
    except Exception:
        chat_handler = None
    if chat_handler is None:
        try:
            registered_handlers = getattr(llm, "_chat_handlers", None)
        except Exception:
            registered_handlers = None
        embedded_format = None
        if isinstance(registered_handlers, dict):
            if "chat_template.default" in registered_handlers:
                embedded_format = "chat_template.default"
            elif current in registered_handlers:
                embedded_format = current

        # Prefer the model's own GGUF template for every family. This also
        # repairs cached instances whose chat_format was previously cleared.
        resolved_format = embedded_format
        if resolved_format is None and prefer_embedded_template:
            resolved_format = current if current and current != "llama-2" else "qwen"
        if resolved_format is not None and current != resolved_format:
            try:
                llm.chat_format = resolved_format
            except Exception:
                pass
        elif not current and chat_format:
            try:
                llm.chat_format = chat_format
            except Exception:
                pass
    elif not current and chat_format:
        try:
            llm.chat_format = chat_format
        except Exception:
            pass

    try:
        tokenizer = getattr(llm, "tokenizer_", None)
    except Exception:
        tokenizer = None
    if tokenizer is None and LlamaTokenizer is not None:
        try:
            llm.tokenizer_ = LlamaTokenizer(llm)
        except Exception:
            pass


def _尝试修复llama无效聊天格式(llm: object, error: Exception, suggested_format: str | None) -> bool:
    message = str(error)
    if "invalid chat handler:" not in message.lower():
        return False

    valid_match = re.search(r"valid formats:\s*\[(.*?)\]", message, flags=re.IGNORECASE | re.DOTALL)
    valid_formats = set(re.findall(r"['\"]([^'\"]+)['\"]", valid_match.group(1))) if valid_match else set()
    try:
        registered_handlers = getattr(llm, "_chat_handlers", None)
    except Exception:
        registered_handlers = None
    registered_formats = set(registered_handlers) if isinstance(registered_handlers, dict) else set()

    try:
        managed_settings = getattr(llm, "_qwen_te_settings", None)
    except Exception:
        managed_settings = None
    if suggested_format is None and isinstance(managed_settings, dict):
        if _应使用llama内置聊天模板(
            family=managed_settings.get("family"),
            model_name=managed_settings.get("model"),
        ):
            suggested_format = "qwen"

    candidates = []
    if "chat_template.default" in registered_formats:
        candidates.append("chat_template.default")
    candidates.extend((suggested_format, "chatml", "qwen", "llama-3", "llama-2"))
    for candidate in candidates:
        if not candidate:
            continue
        if candidate not in registered_formats and valid_formats and candidate not in valid_formats:
            continue
        try:
            llm.chat_format = candidate
        except Exception:
            continue
        return True
    return False


def _按键获取模型存储(storage_key: str):
    normalized_key = str(storage_key or "").strip().lower()
    if normalized_key == "qwen":
        return globals().get("_QwenStorage")
    if normalized_key == "gemma4":
        return globals().get("_Gemma4Storage")
    return None


def _解析当前模型存储(owner_storage):
    if owner_storage is globals().get("_QwenStorage") or owner_storage is globals().get("_Gemma4Storage"):
        return owner_storage
    storage_key = str(getattr(owner_storage, "storage_key", "") or "").strip().lower()
    if not storage_key:
        owner_name = str(getattr(owner_storage, "__name__", "") or "").strip()
        storage_key = {"_QwenStorage": "qwen", "_Gemma4Storage": "gemma4"}.get(owner_name, "")
    return _按键获取模型存储(storage_key)


def _选择模型存储(settings: dict, owner_storage=None):
    current_owner = _解析当前模型存储(owner_storage)
    if current_owner is not None:
        return current_owner
    family = str(settings.get("family", "")).strip().lower()
    storage_name = "_Gemma4Storage" if "gemma" in family else "_QwenStorage"
    return globals().get(storage_name)


def _解析llm托管存储(llm: object, settings=None):
    owner_storage = getattr(llm, "_qwen_te_storage_owner", None)
    current_owner = _解析当前模型存储(owner_storage)
    if current_owner is not None:
        return current_owner
    storage_key = str(getattr(llm, "_qwen_te_storage_key", "") or "").strip().lower()
    current_owner = _按键获取模型存储(storage_key)
    if current_owner is not None:
        return current_owner
    return _选择模型存储(settings) if isinstance(settings, dict) else None


def _同步托管llm实例(llm: object, settings, owner_storage):
    current_model = getattr(owner_storage, "model", None)
    current_llm = getattr(current_model, "llm", None)
    if current_llm is llm:
        return llm
    if not isinstance(settings, dict):
        raise RuntimeError("托管模型已卸载或切换，且旧模型缺少可用于恢复的配置信息。")
    if current_llm is not None and getattr(current_model, "settings", None) == settings:
        return current_llm
    recovered_llm = _按设置重载托管模型(settings, owner_storage=owner_storage)
    if recovered_llm is None:
        raise RuntimeError("托管模型已卸载或切换，自动重载失败。")
    return recovered_llm


def _标记llm托管元数据(llm: object, settings: dict, *, owner_storage=None) -> None:
    try:
        llm._qwen_te_settings = dict(settings)
    except Exception:
        pass
    if owner_storage is not None:
        try:
            llm._qwen_te_storage_owner = owner_storage
            llm._qwen_te_storage_key = str(getattr(owner_storage, "storage_key", "") or "").strip().lower()
        except Exception:
            pass


def _按设置重载托管模型(settings: dict, *, force_reload: bool = False, owner_storage=None) -> object | None:
    storage = _选择模型存储(settings, owner_storage)
    if storage is None:
        return None
    model = storage.load(dict(settings), force_reload=force_reload)
    return getattr(model, "llm", None)


def _应尝试恢复llama异常(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        keyword in message
        for keyword in (
            "access violation",
            "tokenize",
            "tokenizer",
            "null pointer",
            "reading 0x0000000000000000",
        )
    )


def _llama不可用错误() -> RuntimeError:
    detail = str(_LLAMA_IMPORT_ERROR).strip() if _LLAMA_IMPORT_ERROR else ""
    message = "未检测到 llama-cpp-python（llama_cpp），或其 DLL 依赖加载失败。"
    if detail:
        message = f"{message}\n原始错误：{detail}"
    return RuntimeError(message)


def _解析kv缓存类型(value: str | None) -> int | None:
    if not value or value == 默认KV缓存类型:
        return None
    if value == Q8_0缓存类型:
        return GGML_TYPE_Q8_0
    raise ValueError(f"未知 KV 缓存类型：{value}")


def _规范化随机种子(seed_value):
    try:
        seed_value = int(seed_value)
    except Exception:
        return None

    if seed_value < 0:
        return None
    return seed_value


def _重置llm推理状态(llm) -> None:
    try:
        ctx = getattr(llm, "_ctx", None)
        if ctx is not None and hasattr(ctx, "memory_clear"):
            ctx.memory_clear(True)
    except Exception:
        pass

    try:
        hybrid_cache_mgr = getattr(llm, "_hybrid_cache_mgr", None)
        if hybrid_cache_mgr is not None and hasattr(hybrid_cache_mgr, "clear"):
            hybrid_cache_mgr.clear()
    except Exception:
        pass

    try:
        batch = getattr(llm, "_batch", None)
        if batch is not None and hasattr(batch, "reset"):
            batch.reset()
    except Exception:
        pass

    try:
        input_ids = getattr(llm, "input_ids", None)
        if input_ids is not None and hasattr(input_ids, "fill"):
            input_ids.fill(0)
    except Exception:
        pass

    try:
        reset = getattr(llm, "reset", None)
        if callable(reset):
            reset()
        elif hasattr(llm, "n_tokens"):
            llm.n_tokens = 0
    except Exception:
        pass


def _原始模型依赖错误() -> RuntimeError:
    detail = f"\n原始错误：{_TRANSFORMERS_IMPORT_ERROR}" if _TRANSFORMERS_IMPORT_ERROR else ""
    return RuntimeError(
        "当前原始模型需要 transformers、accelerate 和 safetensors。"
        "请在 ComfyUI 使用的 Python 环境运行“自动补装依赖.bat”，或手动安装 transformers。"
        + detail
    )


def _原始模型加载参数(config: dict) -> dict[str, object]:
    custom = _解析llama自定义参数(config.get("custom_llama_params"))
    allowed = {
        "device_map",
        "torch_dtype",
        "low_cpu_mem_usage",
        "use_safetensors",
        "trust_remote_code",
        "attn_implementation",
        "offload_folder",
        "offload_state_dict",
        "max_memory",
        "revision",
        "subfolder",
        "local_files_only",
        "load_in_4bit",
        "load_in_8bit",
        "quantization_config",
    }
    options = {key: value for key, value in custom.items() if key in allowed}
    if isinstance(options.get("torch_dtype"), str):
        dtype = str(options["torch_dtype"]).strip().lower()
        options["torch_dtype"] = {
            "auto": "auto",
            "float16": torch.float16,
            "fp16": torch.float16,
            "bfloat16": torch.bfloat16,
            "bf16": torch.bfloat16,
            "float32": torch.float32,
            "fp32": torch.float32,
        }.get(dtype, "auto")
    options.setdefault("trust_remote_code", True)
    if "device_map" not in options:
        if int(config.get("n_gpu_layers", -1) or -1) == 0 or not torch.cuda.is_available():
            options["device_map"] = None
        else:
            options["device_map"] = "auto"
    if "torch_dtype" not in options and options.get("device_map") == "auto":
        options["torch_dtype"] = "auto"
    return options


def _原始模型消息(messages: list[dict]) -> tuple[list[dict], list[Image.Image]]:
    normalized: list[dict] = []
    images: list[Image.Image] = []
    for message in messages or []:
        role = str(message.get("role", "user") or "user")
        content = message.get("content", "")
        if not isinstance(content, list):
            normalized.append({"role": role, "content": str(content or "")})
            continue
        parts: list[dict] = []
        for item in content:
            if not isinstance(item, dict):
                parts.append({"type": "text", "text": str(item)})
                continue
            item_type = str(item.get("type", "text") or "text").lower()
            if item_type == "text":
                parts.append({"type": "text", "text": str(item.get("text", "") or "")})
                continue
            if item_type not in {"image", "image_url"}:
                parts.append({"type": "text", "text": str(item.get("text", "") or "")})
                continue
            image_url = item.get("image_url", item.get("image", ""))
            if isinstance(image_url, dict):
                image_url = image_url.get("url", "")
            raw_url = str(image_url or "")
            if raw_url.startswith("data:") and "," in raw_url:
                try:
                    image = Image.open(io.BytesIO(base64.b64decode(raw_url.split(",", 1)[1]))).convert("RGB")
                except Exception as exc:
                    raise ValueError(f"原始模型输入图片无法解码：{exc}") from exc
                images.append(image)
                parts.append({"type": "image", "image": image})
            else:
                parts.append({"type": "text", "text": "[图片]"})
        normalized.append({"role": role, "content": parts})
    return normalized, images


class _TransformersChatAdapter:
    """Expose a small OpenAI-compatible chat surface for Hugging Face models."""

    def __init__(self, model, tokenizer, processor, model_path: str, settings: dict):
        self.model = model
        self.tokenizer = tokenizer
        self.processor = processor
        self.model_path = model_path
        self._model_path = model_path
        self.settings = dict(settings)
        self._qwen_te_transformers = True
        self.supports_images = bool(
            processor is not None
            and (
                getattr(processor, "image_processor", None) is not None
                or getattr(processor, "feature_extractor", None) is not None
            )
        )

    @property
    def device(self):
        try:
            return next(self.model.parameters()).device
        except Exception:
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def reset(self) -> None:
        return None

    def close(self) -> None:
        try:
            self.model.to("cpu")
        except Exception:
            pass
        self.model = None
        self.tokenizer = None
        self.processor = None
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

    def _prompt_and_inputs(self, messages, max_length: int):
        normalized, images = _原始模型消息(messages)
        if images and not self.supports_images:
            raise RuntimeError("当前原始模型没有视觉处理器，无法处理图片；请使用对应的 Vision 模型目录。")
        processor = self.processor if images else self.tokenizer
        if processor is None:
            raise RuntimeError("原始模型缺少 tokenizer/processor。")
        template_messages = normalized
        apply_template = getattr(processor, "apply_chat_template", None)
        if not callable(apply_template):
            apply_template = getattr(self.tokenizer, "apply_chat_template", None)
        if callable(apply_template):
            prompt = apply_template(template_messages, tokenize=False, add_generation_prompt=True)
        else:
            prompt = "\n".join(f"{item['role']}: {item['content']}" for item in normalized)
            prompt += "\nassistant:"
        if images:
            encoded = processor(
                text=[prompt],
                images=images,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=max_length,
            )
        else:
            encoded = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=max_length,
            )
        return encoded

    def create_chat_completion(self, messages, max_tokens=512, temperature=0.7, top_p=0.9, top_k=20,
                               repeat_penalty=1.0, repetition_penalty=None, seed=None, stop=None,
                               **_kwargs):
        if self.model is None:
            raise RuntimeError("原始模型已经卸载，请重新加载模型。")
        max_tokens = max(1, min(int(max_tokens or 512), 32768))
        context_length = max(256, int(self.settings.get("n_ctx", 8192) or 8192))
        input_limit = max(1, context_length - max_tokens)
        encoded = self._prompt_and_inputs(messages, input_limit)
        model_device = self.device
        moved = {}
        for key, value in encoded.items():
            moved[key] = value.to(model_device) if hasattr(value, "to") else value
        if seed not in (None, 0):
            torch.manual_seed(int(seed) & 0xFFFFFFFF)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(int(seed) & 0xFFFFFFFF)
        generation = {
            "max_new_tokens": max_tokens,
            "do_sample": float(temperature or 0.0) > 0.0,
            "repetition_penalty": float(repetition_penalty if repetition_penalty is not None else repeat_penalty or 1.0),
        }
        if generation["do_sample"]:
            generation["temperature"] = max(0.01, float(temperature))
            if top_p is not None and float(top_p) < 1.0:
                generation["top_p"] = max(0.01, min(1.0, float(top_p)))
            if top_k is not None and int(top_k) > 0:
                generation["top_k"] = int(top_k)
        pad_token_id = getattr(self.tokenizer, "pad_token_id", None)
        eos_token_id = getattr(self.tokenizer, "eos_token_id", None)
        if pad_token_id is not None:
            generation["pad_token_id"] = pad_token_id
        if eos_token_id is not None:
            generation["eos_token_id"] = eos_token_id
        with torch.inference_mode():
            output = self.model.generate(**moved, **generation)
        input_ids = moved.get("input_ids")
        prompt_tokens = int(input_ids.shape[-1]) if input_ids is not None else 0
        generated = output[:, prompt_tokens:] if prompt_tokens else output
        text = self.tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()
        for marker in stop or []:
            marker = str(marker or "")
            if marker and marker in text:
                text = text.split(marker, 1)[0].rstrip()
        return {"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]}


def _加载Transformers原始模型(config: dict, model_path: str, storage) -> "_QwenModel":
    if _TRANSFORMERS is None:
        raise _原始模型依赖错误()
    model_root = model_path
    if os.path.isfile(model_root):
        model_root = os.path.dirname(model_root)
    if not os.path.isfile(os.path.join(model_root, "config.json")):
        raise RuntimeError(
            f"原始模型目录缺少 config.json：{model_root}\n"
            "请在 models/LLM 下选择包含 config.json 和权重文件的 Hugging Face 模型目录。"
        )
    options = _原始模型加载参数(config)
    tokenizer_options = {
        key: value
        for key, value in options.items()
        if key in {"trust_remote_code", "revision", "subfolder", "local_files_only"}
    }
    tokenizer_cls = getattr(_TRANSFORMERS, "AutoTokenizer", None)
    if tokenizer_cls is None:
        raise _原始模型依赖错误()
    tokenizer = tokenizer_cls.from_pretrained(model_root, **tokenizer_options)
    processor = None
    processor_cls = getattr(_TRANSFORMERS, "AutoProcessor", None)
    if processor_cls is not None:
        try:
            processor = processor_cls.from_pretrained(model_root, **tokenizer_options)
        except Exception:
            processor = None
    model = None
    errors = []
    for class_name in ("AutoModelForImageTextToText", "AutoModelForVision2Seq", "AutoModelForCausalLM"):
        model_cls = getattr(_TRANSFORMERS, class_name, None)
        if model_cls is None:
            continue
        try:
            model = model_cls.from_pretrained(model_root, **options)
            break
        except Exception as exc:
            errors.append(f"{class_name}: {exc}")
    if model is None:
        detail = "；".join(errors[-3:])
        raise RuntimeError(f"原始模型加载失败：{model_root}\n{detail}")
    adapter = _TransformersChatAdapter(model, tokenizer, processor, model_root, config)
    _标记llm托管元数据(adapter, config, owner_storage=storage)
    return _QwenModel(llm=adapter, settings=dict(config), chat_handler=adapter if adapter.supports_images else None)


@dataclass
class _QwenModel:
    llm: object
    settings: dict
    chat_handler: object | None = None


def _本地模型支持视觉输入(model: object) -> bool:
    llm = getattr(model, "llm", None)
    return bool(
        getattr(model, "chat_handler", None) is not None
        or (
            bool(getattr(llm, "_qwen_te_transformers", False))
            and bool(getattr(llm, "supports_images", False))
        )
    )


def _更新模型存储记录(storage, model: _QwenModel | None) -> None:
    storage.model = model
    storage_key = str(getattr(storage, "storage_key", "") or "").strip().lower()
    if not storage_key:
        return
    if model is None:
        _MODEL_STORAGE_MODELS.pop(storage_key, None)
    else:
        _MODEL_STORAGE_MODELS[storage_key] = model


def _锁定模型存储操作(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        with _MODEL_STORAGE_LOCK:
            return func(*args, **kwargs)

    return wrapped


class _QwenStorage:
    storage_key = "qwen"
    model: _QwenModel | None = _MODEL_STORAGE_MODELS.get(storage_key)

    @classmethod
    @_锁定模型存储操作
    def unload(cls) -> None:
        try:
            if cls.model and getattr(cls.model.llm, "close", None):
                cls.model.llm.close()
        except Exception:
            pass
        _更新模型存储记录(cls, None)
        gc.collect()
        mm.soft_empty_cache()

    @classmethod
    @_锁定模型存储操作
    def load(cls, config: dict, *, force_reload: bool = False) -> _QwenModel:
        config = _规范化本地模型配置(config)
        if not force_reload and cls.model and cls.model.settings == config:
            return cls.model

        model_path, backend = _解析本地模型路径(config.get("model"))
        cls.unload()

        if backend == "transformers":
            if config.get("mmproj") not in (None, "", "无"):
                raise RuntimeError("原始 Transformers 模型不使用 GGUF mmproj；请将“视觉投影mmproj”设为“无”。")
            model = _加载Transformers原始模型(config, model_path, cls)
            _更新模型存储记录(cls, model)
            return model

        if Llama is None:
            raise _llama不可用错误()

        mmproj = config.get("mmproj", "无")
        mmproj_path = None
        if mmproj and mmproj != "无":
            mmproj_path = os.path.join(folder_paths.models_dir, "LLM", mmproj)
            if not os.path.exists(mmproj_path):
                raise FileNotFoundError(f"找不到 mmproj 文件：{mmproj_path}")

        family = config["family"]
        think = config["think"]
        cache_type_k = config.get("cache_type_k", 默认KV缓存类型)
        cache_type_v = config.get("cache_type_v", 默认KV缓存类型)

        chat_handler = None
        if mmproj_path:
            if family == "Qwen3-VL":
                if Qwen3VLChatHandler is None:
                    raise RuntimeError("当前 llama-cpp-python 不支持 Qwen3VLChatHandler，请更新 llama-cpp-python。")
                # Qwen3 的 thinking 参数名在不同版本可能不同，这里做兜底。
                try:
                    chat_handler = Qwen3VLChatHandler(clip_model_path=mmproj_path, force_reasoning=think, verbose=False)
                except Exception:
                    try:
                        chat_handler = Qwen3VLChatHandler(clip_model_path=mmproj_path, use_think_prompt=think, verbose=False)
                    except Exception:
                        chat_handler = Qwen3VLChatHandler(clip_model_path=mmproj_path, verbose=False)
            elif family == "Qwen3.5-VL":
                if Qwen35ChatHandler is None:
                    raise RuntimeError("当前 llama-cpp-python 不支持 Qwen35ChatHandler，请更新 llama-cpp-python。")
                try:
                    chat_handler = Qwen35ChatHandler(
                        clip_model_path=mmproj_path,
                        enable_thinking=think,
                        add_vision_id=True,
                        verbose=False,
                    )
                except TypeError:
                    # 兼容少数版本的参数名差异
                    chat_handler = Qwen35ChatHandler(clip_model_path=mmproj_path, enable_thinking=think, verbose=False)
            elif _是qwen38系列(family=family, model_name=config.get("model")):
                # Qwen3.8 landed after many released llama-cpp-python wheels.
                # Use its dedicated handler when available, otherwise leave
                # handler unset so Llama can use the GGUF chat template.
                # This keeps text prompt generation usable instead of raising
                # an Invalid chat handler error during model loading.
                chat_handler = _构造qwen38视觉处理器(mmproj_path, bool(think))
            elif family == "Gemma4":
                if Gemma4ChatHandler is None:
                    raise RuntimeError(
                        "当前 llama-cpp-python 不支持 Gemma4ChatHandler，"
                        "因此 Gemma4 只能先做纯文本推理；如果要启用 mmproj / 图像推理，请安装带 Gemma4ChatHandler 的版本。"
                    )
                chat_handler = Gemma4ChatHandler(
                    clip_model_path=mmproj_path,
                    enable_thinking=think,
                    verbose=False,
                )
            else:
                raise RuntimeError(f"{family} 暂未配置专用视觉 mmproj handler。请把“视觉投影mmproj”设为“无”，按纯文本 GGUF 模型加载。")

        n_ctx = int(config.get("n_ctx", 8192))
        n_gpu_layers = int(config.get("n_gpu_layers", -1))
        prefer_embedded_template = _应使用llama内置聊天模板(
            family=family,
            model_name=config.get("model"),
        )
        chat_format = _推断llama默认聊天格式(family=family, model_name=config.get("model"))

        llama_kwargs = {
            "model_path": model_path,
            "n_ctx": n_ctx,
            "n_gpu_layers": n_gpu_layers,
            "verbose": False,
        }
        _加入llama高级加载参数(llama_kwargs, config)
        _加入llama自定义参数(llama_kwargs, config)
        if chat_handler is not None:
            llama_kwargs["chat_handler"] = chat_handler
        elif chat_format and _llama构造参数是否可用("chat_format") is not False:
            llama_kwargs["chat_format"] = chat_format

        if _llama构造参数是否可用("ctx_checkpoints") is not False:
            llama_kwargs["ctx_checkpoints"] = 0

        type_k = _解析kv缓存类型(cache_type_k)
        type_v = _解析kv缓存类型(cache_type_v)
        wants_custom_kv_type = type_k is not None or type_v is not None
        supports_type_k = _llama构造参数是否可用("type_k")
        supports_type_v = _llama构造参数是否可用("type_v")

        if wants_custom_kv_type and (supports_type_k is False or supports_type_v is False):
            raise RuntimeError("当前 llama-cpp-python 不支持 type_k/type_v（KV cache 量化），请更新该依赖后再使用 q8_0。")

        if type_k is not None:
            llama_kwargs["type_k"] = type_k
        if type_v is not None:
            llama_kwargs["type_v"] = type_v

        try:
            llm = Llama(**llama_kwargs)
        except ValueError as exc:
            if family == "Gemma4":
                detail = (
                    "当前环境能加载其他 GGUF，但无法加载该 Gemma4 文件；"
                    "这通常不是路径错误，而是当前 llama-cpp-python / llama.cpp 二进制"
                    "对该 Gemma4 GGUF 架构不兼容。"
                )
            else:
                detail = (
                    "请核对模型文件完整性、模型系列、mmproj 版本、上下文/KV 参数，"
                    "并确认当前 llama-cpp-python 支持该 GGUF 架构。"
                )
            raise RuntimeError(
                f"{family} 模型加载失败。{detail}"
                f"\n模型文件：{model_path}"
                f"\n原始错误：{exc}"
            ) from exc

        _应用llama聊天格式兜底(
            llm,
            chat_format,
            prefer_embedded_template=prefer_embedded_template,
        )
        _标记llm托管元数据(llm, config, owner_storage=cls)

        model = _QwenModel(llm=llm, settings=dict(config), chat_handler=chat_handler)
        _更新模型存储记录(cls, model)
        return model


class _Gemma4Storage:
    storage_key = "gemma4"
    model: _QwenModel | None = _MODEL_STORAGE_MODELS.get(storage_key)

    @classmethod
    @_锁定模型存储操作
    def unload(cls) -> None:
        try:
            if cls.model and getattr(cls.model.llm, "close", None):
                cls.model.llm.close()
        except Exception:
            pass
        _更新模型存储记录(cls, None)
        gc.collect()
        mm.soft_empty_cache()

    @classmethod
    @_锁定模型存储操作
    def load(cls, config: dict, *, force_reload: bool = False) -> _QwenModel:
        if not force_reload and cls.model and cls.model.settings == config:
            return cls.model

        model_path, backend = _解析本地模型路径(config.get("model"))
        cls.unload()

        if backend == "transformers":
            if config.get("mmproj") not in (None, "", "无"):
                raise RuntimeError("原始 Transformers 模型不使用 GGUF mmproj；请将“视觉投影mmproj”设为“无”。")
            model = _加载Transformers原始模型(config, model_path, cls)
            _更新模型存储记录(cls, model)
            return model

        if Llama is None:
            raise _llama不可用错误()

        mmproj = config.get("mmproj", "无")
        mmproj_path = None
        if mmproj and mmproj != "无":
            mmproj_path = os.path.join(folder_paths.models_dir, "LLM", mmproj)
            if not os.path.exists(mmproj_path):
                raise FileNotFoundError(f"找不到 mmproj 文件：{mmproj_path}")

        think = bool(config.get("think", False))
        cache_type_k = config.get("cache_type_k", 默认KV缓存类型)
        cache_type_v = config.get("cache_type_v", 默认KV缓存类型)

        chat_handler = None
        if mmproj_path:
            if Gemma4ChatHandler is None:
                raise RuntimeError(
                    "当前 llama-cpp-python 不支持 Gemma4ChatHandler，"
                    "因此 Gemma4 只能先做纯文本推理；如果要启用 mmproj / 图像推理，请安装带 Gemma4ChatHandler 的版本。"
                )
            chat_handler = Gemma4ChatHandler(
                clip_model_path=mmproj_path,
                enable_thinking=think,
                verbose=False,
            )

        n_ctx = int(config.get("n_ctx", 8192))
        n_gpu_layers = int(config.get("n_gpu_layers", -1))
        chat_format = _推断llama默认聊天格式(family="Gemma4", model_name=config.get("model"))

        llama_kwargs = {
            "model_path": model_path,
            "n_ctx": n_ctx,
            "n_gpu_layers": n_gpu_layers,
            "verbose": False,
        }
        _加入llama高级加载参数(llama_kwargs, config)
        _加入llama自定义参数(llama_kwargs, config)
        if chat_handler is not None:
            llama_kwargs["chat_handler"] = chat_handler
        elif chat_format and _llama构造参数是否可用("chat_format") is not False:
            llama_kwargs["chat_format"] = chat_format

        if _llama构造参数是否可用("ctx_checkpoints") is not False:
            llama_kwargs["ctx_checkpoints"] = 0

        type_k = _解析kv缓存类型(cache_type_k)
        type_v = _解析kv缓存类型(cache_type_v)
        wants_custom_kv_type = type_k is not None or type_v is not None
        supports_type_k = _llama构造参数是否可用("type_k")
        supports_type_v = _llama构造参数是否可用("type_v")

        if wants_custom_kv_type and (supports_type_k is False or supports_type_v is False):
            raise RuntimeError("当前 llama-cpp-python 不支持 type_k/type_v（KV cache 量化），请更新该依赖后再使用 q8_0。")

        if type_k is not None:
            llama_kwargs["type_k"] = type_k
        if type_v is not None:
            llama_kwargs["type_v"] = type_v

        llm = Llama(**llama_kwargs)
        _应用llama聊天格式兜底(llm, chat_format)
        _标记llm托管元数据(llm, config, owner_storage=cls)

        model = _QwenModel(llm=llm, settings=dict(config), chat_handler=chat_handler)
        _更新模型存储记录(cls, model)
        return model


def _接管热重载前的托管模型() -> None:
    with _MODEL_STORAGE_LOCK:
        for storage in (_QwenStorage, _Gemma4Storage):
            model = _MODEL_STORAGE_MODELS.get(storage.storage_key)
            storage.model = model
            llm = getattr(model, "llm", None)
            if llm is None:
                continue
            previous_owner = getattr(llm, "_qwen_te_storage_owner", None)
            if previous_owner is not storage and getattr(previous_owner, "model", None) is model:
                try:
                    previous_owner.model = None
                except Exception:
                    pass
            _标记llm托管元数据(llm, getattr(model, "settings", {}) or {}, owner_storage=storage)


_接管热重载前的托管模型()


def _卸载当前托管模型() -> None:
    try:
        _QwenStorage.unload()
    except Exception:
        pass
    try:
        _Gemma4Storage.unload()
    except Exception:
        pass


def _安装全局卸载挂钩() -> None:
    """
    将 ComfyUI 全局卸载（comfy.model_management.unload_all_models）挂钩到本插件的卸载逻辑上。

    效果：
    - 点击 TEA/ComfyUI 的“释放显存/释放内存”（/free）触发全局卸载时，会同时 close 掉本插件的 llama_cpp 模型。
    """
    try:
        mm._qwen_te_unload_callback = _卸载当前托管模型
        if getattr(mm, "_qwen_te_unload_hook_version", 0) == 2:
            return

        original = getattr(mm, "unload_all_models", None)
        if original is None or not callable(original):
            return

        @wraps(original)
        def wrapped_unload_all_models(*args, **kwargs):
            callback = getattr(mm, "_qwen_te_unload_callback", None)
            if callable(callback):
                try:
                    callback()
                except Exception:
                    pass
            return original(*args, **kwargs)

        mm.unload_all_models = wrapped_unload_all_models
        mm._qwen_te_unload_hook_installed = True
        mm._qwen_te_unload_hook_version = 2
    except Exception:
        # 不影响 ComfyUI 启动
        return


_安装全局卸载挂钩()


class QwenTE模型加载器:
    @classmethod
    def INPUT_TYPES(s):
        all_files = _列出llm文件()
        model_list = [f for f in all_files if "mmproj" not in f.lower() and _是本地模型选项(f)]
        mmproj_list = ["无"] + [f for f in all_files if "mmproj" in f.lower() and os.path.splitext(f)[1].lower() in [".gguf", ".safetensors", ".bin"]]

        if not model_list:
            model_list = ["（请把模型放到 models/LLM）"]

        return {
            "required": {
                "模型系列": (TE通用模型系列选项, {"default": "Qwen3.5-VL", "tooltip": "同一加载器自动支持 GGUF 和 Hugging Face 原始模型目录；明确的文件名会自动纠正模型家族，Qwen3.6 使用 Qwen3.5 兼容路径。"}),
                "主模型": (model_list, {"tooltip": "选择 GGUF 文件，或选择包含 config.json 与权重的原始模型目录；模型放到 ComfyUI/models/LLM/。"}),
                "视觉投影mmproj": (mmproj_list, {"default": "无", "tooltip": "多模态需要 mmproj；纯文本可选“无”。"}),
                "启用思考": ("BOOLEAN", {"default": False, "tooltip": "Qwen/Gemma 思考开关；通用 GGUF 纯文本模型通常可保持关闭。"}),
                "上下文长度": ("INT", {"default": 8192, "min": 1024, "max": 327680, "step": 256, "tooltip": "对应 llama.cpp 的 n_ctx。"}),
                "GPU层数": ("INT", {"default": -1, "min": -1, "max": 9999, "step": 1, "tooltip": "对应 llama.cpp 的 n_gpu_layers；-1=尽可能多上GPU；0=纯CPU。"}),
                "KV缓存K类型": (KV缓存类型选项, {"default": 默认KV缓存类型, "tooltip": "对应 llama.cpp 的 --cache-type-k / type_k。推荐默认；q8_0-27B模型以上可能提速。"}),
                "KV缓存V类型": (KV缓存类型选项, {"default": 默认KV缓存类型, "tooltip": "对应 llama.cpp 的 --cache-type-v / type_v。推荐默认；q8_0-27B模型以上可能提速。"}),
                "批处理大小": ("INT", {"default": 2048, "min": 32, "max": 131072, "step": 32, "tooltip": "对应 llama.cpp 的 n_batch；显存不足时降低，长上下文可适当提高。"}),
                "微批处理大小": ("INT", {"default": 512, "min": 32, "max": 131072, "step": 32, "tooltip": "对应 llama.cpp 的 n_ubatch；通常不大于批处理大小。"}),
                "线程数": ("INT", {"default": 0, "min": 0, "max": 512, "step": 1, "tooltip": "对应 n_threads；0=由 llama.cpp 自动选择。"}),
                "批处理线程数": ("INT", {"default": 0, "min": 0, "max": 512, "step": 1, "tooltip": "对应 n_threads_batch；0=跟随运行时默认。"}),
                "Flash注意力": (Flash注意力选项, {"default": "自动", "tooltip": "自动遵循 llama.cpp；开启可能降低显存与长上下文开销，但依赖编译能力。"}),
                "KQV卸载": ("BOOLEAN", {"default": True, "tooltip": "对应 offload_kqv；开启时将 K/Q/V 计算尽量放到 GPU。"}),
                "内存映射": ("BOOLEAN", {"default": True, "tooltip": "对应 use_mmap；关闭后模型读取更慢且占用更多内存，通常保持开启。"}),
                "锁定内存": ("BOOLEAN", {"default": False, "tooltip": "对应 use_mlock；防止模型页被换出，但可能导致系统内存不足。"}),
                "RoPE频率基值": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1000000.0, "step": 1.0, "tooltip": "对应 rope_freq_base；0=使用模型元数据，通常不要改。"}),
                "RoPE频率缩放": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 100.0, "step": 0.01, "tooltip": "对应 rope_freq_scale；0=使用模型元数据，长上下文实验时再调整。"}),
                "模型参数JSON": ("STRING", {"default": "", "multiline": True, "tooltip": "可选 JSON，例如 {\"n_seq_max\": 2, \"use_direct_io\": true}；只应用当前 llama-cpp-python 支持的安全构造参数。"}),
            }
        }

    RETURN_TYPES = ("QWENLLAMA",)
    RETURN_NAMES = ("qwen模型",)
    FUNCTION = "load"
    CATEGORY = "Qwen TE"

    def load(
        self,
        模型系列,
        主模型,
        视觉投影mmproj,
        启用思考,
        上下文长度,
        GPU层数,
        KV缓存K类型,
        KV缓存V类型,
        批处理大小=2048,
        微批处理大小=512,
        线程数=0,
        批处理线程数=0,
        Flash注意力="自动",
        KQV卸载=True,
        内存映射=True,
        锁定内存=False,
        RoPE频率基值=0.0,
        RoPE频率缩放=0.0,
        模型参数JSON="",
    ):
        if 主模型.startswith("（请把模型放到"):
            raise RuntimeError("未找到可用模型文件。请把模型放到 ComfyUI/models/LLM/ 后重启。")

        config = {
            "family": 模型系列,
            "model": 主模型,
            "mmproj": 视觉投影mmproj,
            "think": bool(启用思考),
            "n_ctx": int(上下文长度),
            "n_gpu_layers": int(GPU层数),
            "cache_type_k": KV缓存K类型,
            "cache_type_v": KV缓存V类型,
            "n_batch": int(批处理大小),
            "n_ubatch": int(微批处理大小),
            "n_threads": int(线程数),
            "n_threads_batch": int(批处理线程数),
            "flash_attn": Flash注意力,
            "offload_kqv": bool(KQV卸载),
            "use_mmap": bool(内存映射),
            "use_mlock": bool(锁定内存),
            "rope_freq_base": float(RoPE频率基值),
            "rope_freq_scale": float(RoPE频率缩放),
            "custom_llama_params": 模型参数JSON,
        }
        model = _QwenStorage.load(config)
        return (model,)


class QwenTE图像推理:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "qwen模型": ("QWENLLAMA",),
                "输入模式": (["图片", "逐帧", "视频", "文本"], {"default": "图片", "tooltip": "图片=只读第1张；逐帧=一张一张推理；视频=抽帧后一次性推理；文本=仅文字输入，无需图片。"}),
                "提示词": ("STRING", {"default": 默认图片提示词, "multiline": True, "tooltip": "告诉模型要识别、描述或回答什么；文本模式下就是用户问题。"}),
                "系统提示词": ("STRING", {"default": 默认图片系统提示词, "multiline": True, "tooltip": "定义输出角色、格式和约束。没有明确需求时保留默认。"}),
                "最多帧数": ("INT", {"default": 24, "min": 2, "max": 64, "step": 1, "tooltip": "视频模式下从输入图片序列中均匀抽取的帧数；单次最多 64 帧。"}),
                "最大边长": ("INT", {"default": 512, "min": 128, "max": 4096, "step": 64, "tooltip": "对输入图片做缩放以提速（取最长边，最高 4096）。"}),
                "最大生成token": ("INT", {"default": 512, "min": 20, "max": 8192, "step": 1, "tooltip": "默认反推描述用 512 通常足够；需要更长分析再手动调大。"}),
                "温度": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.01, "tooltip": "随机性；0.4-0.7 更稳定，0.8-1.0 更多样。"}),
                "top_p": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "核采样范围；通常保持 0.85-0.95。"}),
                "top_k": ("INT", {"default": 20, "min": 0, "max": 200, "step": 1, "tooltip": "每步候选词数量；提高会增加变化，0 交由模型默认处理。"}),
                "重复惩罚": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.01, "tooltip": "抑制局部复读；出现重复时可尝试 1.05-1.15。"}),
                "频率惩罚": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 2.0, "step": 0.01, "tooltip": "按出现次数抑制重复；建议从 0.1-0.3 小幅增加。"}),
                "存在惩罚": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 2.0, "step": 0.01, "tooltip": "鼓励引入新内容；建议从 0.05-0.2 小幅增加。"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1, "control_after_generate": True, "tooltip": "随机种子。可用 ComfyUI 的生成后控制来固定、递增、递减或随机。"}),
                "输出think块": ("BOOLEAN", {"default": True, "tooltip": "开启=保留模型原始 `<think>...</think>` 输出；关闭=仅在最终结果里移除 think 块。"}),
            },
            "optional": {
                "图片": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "run"
    CATEGORY = "Qwen TE"

    def run(
        self,
        qwen模型,
        输入模式,
        提示词,
        系统提示词,
        最多帧数,
        最大边长,
        最大生成token,
        温度,
        top_p,
        top_k,
        重复惩罚,
        频率惩罚,
        存在惩罚,
        seed,
        输出think块,
        图片=None,
    ):
        # 卸载后 / 引用失效时：自动重载与同步到当前有效模型
        need_reload = False
        if _QwenStorage.model is None:
            need_reload = True
        elif qwen模型 is not _QwenStorage.model:
            if hasattr(qwen模型, "settings") and getattr(qwen模型, "settings") == _QwenStorage.model.settings:
                qwen模型 = _QwenStorage.model
            else:
                need_reload = True

        if need_reload:
            if not hasattr(qwen模型, "settings"):
                raise RuntimeError("输入的模型对象缺少配置信息，无法自动重载。请先运行“Qwen TE 模型加载器”。")
            _QwenStorage.load(qwen模型.settings)
            qwen模型 = _QwenStorage.model

        if not hasattr(qwen模型, "llm") or qwen模型.llm is None:
            raise RuntimeError("模型对象内部 llm 实例无效，请检查模型文件完整性，或重新加载模型。")

        llm = qwen模型.llm

        messages = []
        prompt_text = (提示词 or "").strip()
        system_text = (系统提示词 or "").strip()

        if 输入模式 == "文本":
            system_text = _增强文本模式系统提示词(system_text, prompt_text)
        elif 输入模式 == "视频" and system_text:
            system_text = "请将输入的图片序列当做视频而不是静态帧序列, " + system_text

        if system_text:
            messages.append({"role": "system", "content": system_text})

        total_images = int(图片.shape[0]) if 图片 is not None else 0
        if 输入模式 in ("图片", "逐帧", "视频") and total_images == 0:
            raise ValueError("未检测到图片输入。")
        if 输入模式 in ("图片", "逐帧", "视频"):
            if not _本地模型支持视觉输入(qwen模型):
                family = str(getattr(qwen模型, "settings", {}).get("family", "当前系列") or "当前系列")
                raise RuntimeError(
                    f"{family} 本地模型当前只具备文本能力，未加载可用的视觉处理器。"
                    "请匹配该主模型版本的 mmproj 并安装含对应视觉 handler 的 llama-cpp-python；"
                    "原始模型则需提供可加载的视觉 processor。"
                )
        最多帧数 = max(2, min(_MAX_MULTIFRAME_INFERENCE_FRAMES, int(最多帧数)))
        最大边长 = max(128, min(_MAX_IMAGE_INFERENCE_EDGE, int(最大边长)))
        if 输入模式 == "逐帧" and total_images > _MAX_MULTIFRAME_INFERENCE_FRAMES:
            raise ValueError(
                f"逐帧模式单次最多处理 {_MAX_MULTIFRAME_INFERENCE_FRAMES} 帧；"
                "请改用视频模式抽帧或拆分批次。"
            )

        if 输入模式 == "图片":
            frame_indices = [0]
        elif 输入模式 == "逐帧":
            frame_indices = list(range(total_images))
        elif 输入模式 == "视频":
            frame_indices = _视频抽帧索引(total_images, int(最多帧数))
        elif 输入模式 == "文本":
            frame_indices = []
        else:
            raise ValueError(f"未知输入模式：{输入模式}")
        最大边长 = _多帧预算最大边长(len(frame_indices), 最大边长)

        params = {
            "max_tokens": _图像推理最大生成token(
                输入模式=输入模式,
                提示词=prompt_text,
                系统提示词=system_text,
                最大生成token=int(最大生成token),
            ),
            "temperature": float(温度),
            "top_p": float(top_p),
            "top_k": int(top_k),
            "repeat_penalty": float(重复惩罚),
            "frequency_penalty": float(频率惩罚),
            "presence_penalty": float(存在惩罚),
            "seed": _规范化随机种子(seed),
            "stream": False,
            "stop": ["</s>"],
        }

        if 输入模式 == "文本":
            if not prompt_text:
                raise ValueError("文本模式下，提示词不能为空。")

            messages.append({"role": "user", "content": prompt_text})
            out = _调用chat_completion(llm, messages=messages, params=params)
            try:
                text = out["choices"][0]["message"]["content"]
            except Exception:
                text = str(out)
            text = _文本结果去低龄化(str(text), prompt_text)
            text = _清理模型专有提示词噪声(str(text))
        elif 输入模式 == "逐帧":
            user_content = [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": {"url": ""}}]
            messages.append({"role": "user", "content": user_content})
            frame_data_urls = _预编码帧data_url(图片, frame_indices, int(最大边长))

            out_parts = []
            for idx, frame_index in enumerate(frame_indices):
                if mm.processing_interrupted():
                    raise mm.InterruptProcessingException()
                img_url = frame_data_urls.get(frame_index, "")
                if not img_url:
                    img_b64 = _批量图片索引转base64(图片, frame_index, int(最大边长))
                    if not img_b64:
                        continue
                    img_url = f"data:image/jpeg;base64,{img_b64}"
                user_content[1]["image_url"]["url"] = img_url
                out = _调用chat_completion(llm, messages=messages, params=params)
                try:
                    part = out["choices"][0]["message"]["content"]
                except Exception:
                    part = str(out)
                if len(frame_indices) > 1:
                    out_parts.append(f"====== 第{idx+1}帧 ======\n{part}".strip())
                else:
                    out_parts.append(str(part).strip())
            text = "\n\n".join([p for p in out_parts if p])
        else:
            user_content = [{"type": "text", "text": prompt_text}]
            frame_data_urls = _批量帧索引转data_url(图片, frame_indices, int(最大边长))
            for frame_index in frame_indices:
                if mm.processing_interrupted():
                    raise mm.InterruptProcessingException()
                img_url = frame_data_urls.get(frame_index, "")
                if not img_url:
                    continue
                user_content.append({"type": "image_url", "image_url": {"url": img_url}})
            messages.append({"role": "user", "content": user_content})
            out = _调用chat_completion(llm, messages=messages, params=params)
            try:
                text = out["choices"][0]["message"]["content"]
            except Exception:
                text = str(out)

        if not bool(输出think块):
            text = _清洗think块文本(text)

        if mm.processing_interrupted():
            raise mm.InterruptProcessingException()

        return (text.lstrip().removeprefix(": ").strip(),)


class QwenTE卸载模型:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"任意输入": (any_type,)}}

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("任意输出",)
    FUNCTION = "run"
    CATEGORY = "Qwen TE"

    def run(self, 任意输入):
        _QwenStorage.unload()
        return (任意输入,)


class Gemma4TE模型加载器:
    @classmethod
    def INPUT_TYPES(s):
        all_files = _列出llm文件()
        model_list = [f for f in all_files if "mmproj" not in f.lower() and _是本地模型选项(f)]
        mmproj_list = ["无"] + [f for f in all_files if "mmproj" in f.lower() and os.path.splitext(f)[1].lower() in [".gguf", ".safetensors", ".bin"]]

        if not model_list:
            model_list = ["（请把模型放到 models/LLM）"]

        return {
            "required": {
                "主模型": (model_list, {"tooltip": "选择 GGUF 文件，或选择包含 config.json 与权重的原始模型目录；模型放到 ComfyUI/models/LLM/。"}),
                "视觉投影mmproj": (mmproj_list, {"default": "无", "tooltip": "Gemma4 多模态需要 mmproj；纯文本可选“无”。"}),
                "启用思考": ("BOOLEAN", {"default": False, "tooltip": "Gemma4 专用 enable_thinking 开关。"}),
                "上下文长度": ("INT", {"default": 8192, "min": 1024, "max": 327680, "step": 256, "tooltip": "对应 llama.cpp 的 n_ctx。"}),
                "GPU层数": ("INT", {"default": -1, "min": -1, "max": 9999, "step": 1, "tooltip": "对应 llama.cpp 的 n_gpu_layers；-1=尽可能多上GPU；0=纯CPU。"}),
                "KV缓存K类型": (KV缓存类型选项, {"default": 默认KV缓存类型, "tooltip": "对应 llama.cpp 的 --cache-type-k / type_k。"}),
                "KV缓存V类型": (KV缓存类型选项, {"default": 默认KV缓存类型, "tooltip": "对应 llama.cpp 的 --cache-type-v / type_v。"}),
                "批处理大小": ("INT", {"default": 2048, "min": 32, "max": 131072, "step": 32, "tooltip": "对应 llama.cpp 的 n_batch。"}),
                "微批处理大小": ("INT", {"default": 512, "min": 32, "max": 131072, "step": 32, "tooltip": "对应 llama.cpp 的 n_ubatch；通常不大于批处理大小。"}),
                "线程数": ("INT", {"default": 0, "min": 0, "max": 512, "step": 1, "tooltip": "对应 n_threads；0=自动。"}),
                "批处理线程数": ("INT", {"default": 0, "min": 0, "max": 512, "step": 1, "tooltip": "对应 n_threads_batch；0=自动。"}),
                "Flash注意力": (Flash注意力选项, {"default": "自动", "tooltip": "自动遵循 llama.cpp；开启需要运行时支持。"}),
                "KQV卸载": ("BOOLEAN", {"default": True, "tooltip": "对应 offload_kqv。"}),
                "内存映射": ("BOOLEAN", {"default": True, "tooltip": "对应 use_mmap；通常保持开启。"}),
                "锁定内存": ("BOOLEAN", {"default": False, "tooltip": "对应 use_mlock；可能增加系统内存压力。"}),
                "RoPE频率基值": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1000000.0, "step": 1.0, "tooltip": "对应 rope_freq_base；0=模型默认。"}),
                "RoPE频率缩放": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 100.0, "step": 0.01, "tooltip": "对应 rope_freq_scale；0=模型默认。"}),
                "模型参数JSON": ("STRING", {"default": "", "multiline": True, "tooltip": "可选 JSON，例如 {\"n_seq_max\": 2, \"no_host\": true}；不支持或受保护的键会被忽略。"}),
            }
        }

    RETURN_TYPES = ("GEMMA4LLAMA",)
    RETURN_NAMES = ("gemma4模型",)
    FUNCTION = "load"
    CATEGORY = "Gemma4 TE"

    def load(
        self,
        主模型,
        视觉投影mmproj,
        启用思考,
        上下文长度,
        GPU层数,
        KV缓存K类型,
        KV缓存V类型,
        批处理大小=2048,
        微批处理大小=512,
        线程数=0,
        批处理线程数=0,
        Flash注意力="自动",
        KQV卸载=True,
        内存映射=True,
        锁定内存=False,
        RoPE频率基值=0.0,
        RoPE频率缩放=0.0,
        模型参数JSON="",
    ):
        if 主模型.startswith("（请把模型放到"):
            raise RuntimeError("未找到可用模型文件。请把模型放到 ComfyUI/models/LLM/ 后重启。")

        config = {
            "family": "Gemma4",
            "model": 主模型,
            "mmproj": 视觉投影mmproj,
            "think": bool(启用思考),
            "n_ctx": int(上下文长度),
            "n_gpu_layers": int(GPU层数),
            "cache_type_k": KV缓存K类型,
            "cache_type_v": KV缓存V类型,
            "n_batch": int(批处理大小),
            "n_ubatch": int(微批处理大小),
            "n_threads": int(线程数),
            "n_threads_batch": int(批处理线程数),
            "flash_attn": Flash注意力,
            "offload_kqv": bool(KQV卸载),
            "use_mmap": bool(内存映射),
            "use_mlock": bool(锁定内存),
            "rope_freq_base": float(RoPE频率基值),
            "rope_freq_scale": float(RoPE频率缩放),
            "custom_llama_params": 模型参数JSON,
        }
        model = _Gemma4Storage.load(config)
        return (model,)


class Gemma4TE图像推理:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "gemma4模型": ("GEMMA4LLAMA",),
                "输入模式": (["图片", "逐帧", "视频", "文本"], {"default": "图片", "tooltip": "图片=只读第1张；逐帧=一张一张推理；视频=抽帧后一次性推理；文本=仅文字输入，无需图片。"}),
                "提示词": ("STRING", {"default": 默认图片提示词, "multiline": True, "tooltip": "告诉模型要识别、描述或回答什么；文本模式下就是用户问题。"}),
                "系统提示词": ("STRING", {"default": 默认图片系统提示词, "multiline": True, "tooltip": "定义输出角色、格式和约束。没有明确需求时保留默认。"}),
                "最多帧数": ("INT", {"default": 24, "min": 2, "max": 64, "step": 1, "tooltip": "视频模式下从输入图片序列中均匀抽取的帧数；单次最多 64 帧。"}),
                "最大边长": ("INT", {"default": 512, "min": 128, "max": 4096, "step": 64, "tooltip": "对输入图片做缩放以提速（取最长边，最高 4096）。"}),
                "最大生成token": ("INT", {"default": 512, "min": 20, "max": 8192, "step": 1, "tooltip": "Gemma4 官方图片示例使用 512；文本长回复可手动调大。"}),
                "温度": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01, "tooltip": "Gemma4 官方推荐采样配置：temperature=1.0。"}),
                "top_p": ("FLOAT", {"default": 0.95, "min": 0.0, "max": 1.0, "step": 0.01, "tooltip": "Gemma4 官方推荐采样配置：top_p=0.95。"}),
                "top_k": ("INT", {"default": 64, "min": 0, "max": 200, "step": 1, "tooltip": "Gemma4 官方推荐采样配置：top_k=64。"}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "step": 1, "control_after_generate": True, "tooltip": "随机种子。可用 ComfyUI 的生成后控制来固定、递增、递减或随机。"}),
                "输出think块": ("BOOLEAN", {"default": False, "tooltip": "开启=尽量保留 Gemma4 思考文本；关闭=只保留最终答案，并清理通道控制标记。"}),
            },
            "optional": {
                "图片": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("文本",)
    FUNCTION = "run"
    CATEGORY = "Gemma4 TE"

    def run(
        self,
        gemma4模型,
        输入模式,
        提示词,
        系统提示词,
        最多帧数,
        最大边长,
        最大生成token,
        温度,
        top_p,
        top_k,
        seed,
        输出think块,
        图片=None,
    ):
        need_reload = False
        if _Gemma4Storage.model is None:
            need_reload = True
        elif gemma4模型 is not _Gemma4Storage.model:
            if hasattr(gemma4模型, "settings") and getattr(gemma4模型, "settings") == _Gemma4Storage.model.settings:
                gemma4模型 = _Gemma4Storage.model
            else:
                need_reload = True

        if need_reload:
            if not hasattr(gemma4模型, "settings"):
                raise RuntimeError("输入的 Gemma4 模型对象缺少配置信息，无法自动重载。请先运行“Gemma4 TE 模型加载器”。")
            _Gemma4Storage.load(gemma4模型.settings)
            gemma4模型 = _Gemma4Storage.model

        if not hasattr(gemma4模型, "llm") or gemma4模型.llm is None:
            raise RuntimeError("Gemma4 模型对象内部 llm 实例无效，请检查模型文件完整性，或重新加载模型。")

        llm = gemma4模型.llm
        chat_handler = getattr(gemma4模型, "chat_handler", None)

        messages = []
        prompt_text = (提示词 or "").strip()
        system_text = (系统提示词 or "").strip()

        if 输入模式 == "文本":
            system_text = _增强文本模式系统提示词(system_text, prompt_text)
        elif 输入模式 == "视频" and system_text:
            system_text = "请将输入的图片序列当做视频而不是静态帧序列, " + system_text

        if system_text:
            messages.append({"role": "system", "content": system_text})

        total_images = int(图片.shape[0]) if 图片 is not None else 0
        if 输入模式 in ("图片", "逐帧", "视频") and total_images == 0:
            raise ValueError("未检测到图片输入。")
        if 输入模式 in ("图片", "逐帧", "视频") and chat_handler is None:
            raise RuntimeError("当前 Gemma4 模型未加载 mmproj，无法进行图像推理。请在“Gemma4 TE 模型加载器”里选择对应的 mmproj。")
        最多帧数 = max(2, min(_MAX_MULTIFRAME_INFERENCE_FRAMES, int(最多帧数)))
        最大边长 = max(128, min(_MAX_IMAGE_INFERENCE_EDGE, int(最大边长)))
        if 输入模式 == "逐帧" and total_images > _MAX_MULTIFRAME_INFERENCE_FRAMES:
            raise ValueError(
                f"逐帧模式单次最多处理 {_MAX_MULTIFRAME_INFERENCE_FRAMES} 帧；"
                "请改用视频模式抽帧或拆分批次。"
            )

        if 输入模式 == "图片":
            frame_indices = [0]
        elif 输入模式 == "逐帧":
            frame_indices = list(range(total_images))
        elif 输入模式 == "视频":
            frame_indices = _视频抽帧索引(total_images, int(最多帧数))
        elif 输入模式 == "文本":
            frame_indices = []
        else:
            raise ValueError(f"未知输入模式：{输入模式}")
        最大边长 = _多帧预算最大边长(len(frame_indices), 最大边长)

        params = {
            "max_tokens": _图像推理最大生成token(
                输入模式=输入模式,
                提示词=prompt_text,
                系统提示词=system_text,
                最大生成token=int(最大生成token),
            ),
            "temperature": float(温度),
            "top_p": float(top_p),
            "top_k": int(top_k),
            "seed": _规范化随机种子(seed),
            "stream": False,
            "stop": ["</s>"],
        }

        if 输入模式 == "文本":
            if not prompt_text:
                raise ValueError("文本模式下，提示词不能为空。")

            messages.append({"role": "user", "content": prompt_text})
            out = _调用chat_completion(llm, messages=messages, params=params)
            try:
                text = out["choices"][0]["message"]["content"]
            except Exception:
                text = str(out)
            text = _文本结果去低龄化(str(text), prompt_text)
            text = _清理模型专有提示词噪声(str(text))
        elif 输入模式 == "逐帧":
            user_content = [{"type": "text", "text": prompt_text}, {"type": "image_url", "image_url": {"url": ""}}]
            messages.append({"role": "user", "content": user_content})
            frame_data_urls = _预编码帧data_url(图片, frame_indices, int(最大边长))

            out_parts = []
            for idx, frame_index in enumerate(frame_indices):
                if mm.processing_interrupted():
                    raise mm.InterruptProcessingException()
                img_url = frame_data_urls.get(frame_index, "")
                if not img_url:
                    img_b64 = _批量图片索引转base64(图片, frame_index, int(最大边长))
                    if not img_b64:
                        continue
                    img_url = f"data:image/jpeg;base64,{img_b64}"
                user_content[1]["image_url"]["url"] = img_url
                out = _调用chat_completion(llm, messages=messages, params=params)
                try:
                    part = out["choices"][0]["message"]["content"]
                except Exception:
                    part = str(out)
                part = _清洗gemma4输出文本(part, bool(输出think块))
                if len(frame_indices) > 1:
                    out_parts.append(f"====== 第{idx+1}帧 ======\n{part}".strip())
                else:
                    out_parts.append(str(part).strip())
            text = "\n\n".join([p for p in out_parts if p])
        else:
            user_content = [{"type": "text", "text": prompt_text}]
            frame_data_urls = _批量帧索引转data_url(图片, frame_indices, int(最大边长))
            for frame_index in frame_indices:
                if mm.processing_interrupted():
                    raise mm.InterruptProcessingException()
                img_url = frame_data_urls.get(frame_index, "")
                if not img_url:
                    continue
                user_content.append({"type": "image_url", "image_url": {"url": img_url}})
            messages.append({"role": "user", "content": user_content})
            out = _调用chat_completion(llm, messages=messages, params=params)
            try:
                text = out["choices"][0]["message"]["content"]
            except Exception:
                text = str(out)

        text = _清洗gemma4输出文本(text, bool(输出think块))

        if mm.processing_interrupted():
            raise mm.InterruptProcessingException()

        return (text.lstrip().removeprefix(": ").strip(),)


class Gemma4TE卸载模型:
    @classmethod
    def INPUT_TYPES(s):
        return {"required": {"任意输入": (any_type,)}}

    RETURN_TYPES = (any_type,)
    RETURN_NAMES = ("任意输出",)
    FUNCTION = "run"
    CATEGORY = "Gemma4 TE"

    def run(self, 任意输入):
        _Gemma4Storage.unload()
        return (任意输入,)
