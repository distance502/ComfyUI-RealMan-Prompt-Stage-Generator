# -*- coding: utf-8 -*-
import base64
import ctypes
import gc
import inspect
import io
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
    from llama_cpp.llama_chat_format import Gemma4ChatHandler
except Exception:
    Gemma4ChatHandler = None


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
TE通用模型系列选项 = ["Qwen3-VL", "Qwen3.5-VL", "Gemma4", "Llama", "Mistral", "DeepSeek", "通用GGUF"]
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


def _列出llm文件() -> list[str]:
    _确保_llm目录已注册()
    try:
        return folder_paths.get_filename_list("LLM")
    except Exception:
        return []


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
        guessed_chat_format = _推断llama默认聊天格式(model_name=" ".join(str(item) for item in candidates if item))
        _应用llama聊天格式兜底(llm, guessed_chat_format)
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


def _推断llama默认聊天格式(*, family: str | None = None, model_name: str | None = None) -> str | None:
    haystack = f"{family or ''} {model_name or ''}".lower()
    if "gemma" in haystack:
        return "gemma"
    if "qwen" in haystack:
        return "qwen"
    if "llama" in haystack:
        return "llama-3"
    if "mistral" in haystack:
        return "mistral-instruct"
    return None


def _应用llama聊天格式兜底(llm: object, chat_format: str | None) -> None:
    if not chat_format:
        chat_format = None
    try:
        current = getattr(llm, "chat_format", None)
    except Exception:
        current = None
    if not current and chat_format:
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


@dataclass
class _QwenModel:
    llm: object
    settings: dict
    chat_handler: object | None = None


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
        if Llama is None:
            raise _llama不可用错误()

        if not force_reload and cls.model and cls.model.settings == config:
            return cls.model

        cls.unload()

        model_path = os.path.join(folder_paths.models_dir, "LLM", config["model"])
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"找不到模型文件：{model_path}")

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
        chat_format = _推断llama默认聊天格式(family=family, model_name=config.get("model"))

        llama_kwargs = {
            "model_path": model_path,
            "n_ctx": n_ctx,
            "n_gpu_layers": n_gpu_layers,
            "verbose": False,
        }
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
            raise RuntimeError(
                "Gemma4 模型加载失败。当前环境能加载其他 GGUF，但无法加载该 Gemma4 文件；"
                "这通常不是路径错误，而是当前 llama-cpp-python / llama.cpp 二进制对该 Gemma4 GGUF 架构不兼容。"
                f"\n模型文件：{model_path}"
                f"\n原始错误：{exc}"
            ) from exc

        _应用llama聊天格式兜底(llm, chat_format)
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
        if Llama is None:
            raise _llama不可用错误()

        if not force_reload and cls.model and cls.model.settings == config:
            return cls.model

        cls.unload()

        model_path = os.path.join(folder_paths.models_dir, "LLM", config["model"])
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"找不到模型文件：{model_path}")

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
        model_list = [f for f in all_files if "mmproj" not in f.lower() and os.path.splitext(f)[1].lower() in [".gguf", ".safetensors", ".bin", ".pth", ".pt"]]
        mmproj_list = ["无"] + [f for f in all_files if "mmproj" in f.lower() and os.path.splitext(f)[1].lower() in [".gguf", ".safetensors", ".bin"]]

        if not model_list:
            model_list = ["（请把模型放到 models/LLM）"]

        return {
            "required": {
                "模型系列": (TE通用模型系列选项, {"default": "Qwen3.5-VL", "tooltip": "同一加载器支持 Qwen / Gemma / Llama / Mistral / DeepSeek / 通用 GGUF。只有 Qwen/Gemma 系列会尝试专用视觉 mmproj handler。"}),
                "主模型": (model_list, {"tooltip": "主模型文件（建议 .gguf）放到 ComfyUI/models/LLM/"}),
                "视觉投影mmproj": (mmproj_list, {"default": "无", "tooltip": "多模态需要 mmproj；纯文本可选“无”。"}),
                "启用思考": ("BOOLEAN", {"default": False, "tooltip": "Qwen/Gemma 思考开关；通用 GGUF 纯文本模型通常可保持关闭。"}),
                "上下文长度": ("INT", {"default": 8192, "min": 1024, "max": 327680, "step": 256, "tooltip": "对应 llama.cpp 的 n_ctx。"}),
                "GPU层数": ("INT", {"default": -1, "min": -1, "max": 9999, "step": 1, "tooltip": "对应 llama.cpp 的 n_gpu_layers；-1=尽可能多上GPU；0=纯CPU。"}),
                "KV缓存K类型": (KV缓存类型选项, {"default": 默认KV缓存类型, "tooltip": "对应 llama.cpp 的 --cache-type-k / type_k。推荐默认；q8_0-27B模型以上可能提速。"}),
                "KV缓存V类型": (KV缓存类型选项, {"default": 默认KV缓存类型, "tooltip": "对应 llama.cpp 的 --cache-type-v / type_v。推荐默认；q8_0-27B模型以上可能提速。"}),
            }
        }

    RETURN_TYPES = ("QWENLLAMA",)
    RETURN_NAMES = ("qwen模型",)
    FUNCTION = "load"
    CATEGORY = "Qwen TE"

    def load(self, 模型系列, 主模型, 视觉投影mmproj, 启用思考, 上下文长度, GPU层数, KV缓存K类型, KV缓存V类型):
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
                "提示词": ("STRING", {"default": 默认图片提示词, "multiline": True}),
                "系统提示词": ("STRING", {"default": 默认图片系统提示词, "multiline": True}),
                "最多帧数": ("INT", {"default": 24, "min": 2, "max": 64, "step": 1, "tooltip": "视频模式下从输入图片序列中均匀抽取的帧数；单次最多 64 帧。"}),
                "最大边长": ("INT", {"default": 512, "min": 128, "max": 4096, "step": 64, "tooltip": "对输入图片做缩放以提速（取最长边，最高 4096）。"}),
                "最大生成token": ("INT", {"default": 512, "min": 20, "max": 8192, "step": 1, "tooltip": "默认反推描述用 512 通常足够；需要更长分析再手动调大。"}),
                "温度": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.01}),
                "top_p": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.01}),
                "top_k": ("INT", {"default": 20, "min": 0, "max": 200, "step": 1}),
                "重复惩罚": ("FLOAT", {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.01}),
                "频率惩罚": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 2.0, "step": 0.01}),
                "存在惩罚": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 2.0, "step": 0.01}),
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
        model_list = [f for f in all_files if "mmproj" not in f.lower() and os.path.splitext(f)[1].lower() in [".gguf", ".safetensors", ".bin", ".pth", ".pt"]]
        mmproj_list = ["无"] + [f for f in all_files if "mmproj" in f.lower() and os.path.splitext(f)[1].lower() in [".gguf", ".safetensors", ".bin"]]

        if not model_list:
            model_list = ["（请把模型放到 models/LLM）"]

        return {
            "required": {
                "主模型": (model_list, {"tooltip": "Gemma4 主模型文件（建议 .gguf）放到 ComfyUI/models/LLM/"}),
                "视觉投影mmproj": (mmproj_list, {"default": "无", "tooltip": "Gemma4 多模态需要 mmproj；纯文本可选“无”。"}),
                "启用思考": ("BOOLEAN", {"default": False, "tooltip": "Gemma4 专用 enable_thinking 开关。"}),
                "上下文长度": ("INT", {"default": 8192, "min": 1024, "max": 327680, "step": 256, "tooltip": "对应 llama.cpp 的 n_ctx。"}),
                "GPU层数": ("INT", {"default": -1, "min": -1, "max": 9999, "step": 1, "tooltip": "对应 llama.cpp 的 n_gpu_layers；-1=尽可能多上GPU；0=纯CPU。"}),
                "KV缓存K类型": (KV缓存类型选项, {"default": 默认KV缓存类型, "tooltip": "对应 llama.cpp 的 --cache-type-k / type_k。"}),
                "KV缓存V类型": (KV缓存类型选项, {"default": 默认KV缓存类型, "tooltip": "对应 llama.cpp 的 --cache-type-v / type_v。"}),
            }
        }

    RETURN_TYPES = ("GEMMA4LLAMA",)
    RETURN_NAMES = ("gemma4模型",)
    FUNCTION = "load"
    CATEGORY = "Gemma4 TE"

    def load(self, 主模型, 视觉投影mmproj, 启用思考, 上下文长度, GPU层数, KV缓存K类型, KV缓存V类型):
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
                "提示词": ("STRING", {"default": 默认图片提示词, "multiline": True}),
                "系统提示词": ("STRING", {"default": 默认图片系统提示词, "multiline": True}),
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
