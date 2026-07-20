# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib
import importlib.util
import sys
import traceback
from pathlib import Path


NODE_DIR = Path(__file__).resolve().parent

CORE_FILES = [
    "__init__.py",
    "nodes.py",
    "stage_prompt_generator.py",
    "prompt_tag_library.py",
    "web/stage_prompt_generator_ui_v2.js",
    "web/stage_prompt_generator_mini_toolbar.js",
]

BLOCKING_MODULES = [
    ("folder_paths", "ComfyUI 运行环境"),
]

OPTIONAL_MODULES = [
    ("numpy", "旧图像/模型节点张量处理"),
    ("PIL", "旧图像/模型节点图像读写"),
    ("comfy.model_management", "旧模型节点管理"),
    ("llama_cpp", "内置模型加载 / 模型推理"),
    ("cv2", "质检功能"),
    ("rapidocr_onnxruntime", "质检 OCR"),
    ("aiohttp", "扩展接口路由"),
]

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def line(level: str, message: str) -> None:
    print(f"[{level}] {message}")


def is_comfy_root(path: Path) -> bool:
    return (path / "folder_paths.py").exists()


def find_comfy_root_from_module_path() -> Path | None:
    try:
        spec = importlib.util.find_spec("folder_paths")
    except Exception:
        return None
    origin = Path(str(getattr(spec, "origin", "") or ""))
    if origin.name == "folder_paths.py" and origin.parent.exists():
        return origin.parent.resolve()
    return None


def find_comfy_root_from_node_dir() -> Path | None:
    for candidate in (NODE_DIR.parent.parent, *NODE_DIR.parents):
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        if is_comfy_root(resolved):
            return resolved
    return None


def find_comfy_root_from_python_executable() -> Path | None:
    """Detect ComfyUI portable layouts when the probe is run from a copied share package."""
    try:
        exe = Path(sys.executable).resolve()
    except Exception:
        return None
    candidates = [
        exe.parent,
        exe.parent.parent,
        exe.parent.parent / "ComfyUI",
        exe.parent.parent.parent / "ComfyUI",
    ]
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        if is_comfy_root(resolved):
            return resolved
    return None


def resolve_comfy_root() -> Path:
    if len(sys.argv) >= 2 and str(sys.argv[1]).strip():
        return Path(sys.argv[1]).expanduser().resolve()
    return (
        find_comfy_root_from_node_dir()
        or find_comfy_root_from_python_executable()
        or find_comfy_root_from_module_path()
        or NODE_DIR.parent.parent.resolve()
    )


def has_explicit_comfy_root_argument() -> bool:
    return len(sys.argv) >= 2 and bool(str(sys.argv[1]).strip())


def ensure_search_paths(comfy_root: Path) -> None:
    for candidate in (str(comfy_root), str(NODE_DIR.parent)):
        if candidate not in sys.path:
            sys.path.insert(0, candidate)


def check_files() -> list[str]:
    missing: list[str] = []
    for relative in CORE_FILES:
        target = NODE_DIR / relative
        if target.exists():
            line("OK", f"文件存在: {relative}")
        else:
            missing.append(relative)
            line("FAIL", f"缺少文件: {relative}")
    return missing


def probe_module(module_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, ""
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def probe_plugin_entry() -> tuple[bool, str]:
    alias = "qwen_te_dependency_probe_pkg"
    init_path = NODE_DIR / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        alias,
        init_path,
        submodule_search_locations=[str(NODE_DIR)],
    )
    if spec is None or spec.loader is None:
        return False, "无法构造插件入口加载器。"

    module = importlib.util.module_from_spec(spec)
    saved_modules = {
        key: value
        for key, value in list(sys.modules.items())
        if key == alias or key.startswith(f"{alias}.")
    }
    for key in saved_modules:
        sys.modules.pop(key, None)
    sys.modules[alias] = module
    try:
        spec.loader.exec_module(module)
        node_map = getattr(module, "NODE_CLASS_MAPPINGS", {})
        if "QwenTE_StagePromptGenerator" not in node_map:
            return False, "插件入口已导入，但没有注册 QwenTE_StagePromptGenerator。"
        names = ", ".join(sorted(node_map.keys()))
        return True, f"插件入口导入成功，已注册节点: {names}"
    except Exception:
        return False, traceback.format_exc()
    finally:
        for key in [key for key in list(sys.modules.keys()) if key == alias or key.startswith(f"{alias}.")]:
            sys.modules.pop(key, None)
        sys.modules.update(saved_modules)


def main() -> int:
    explicit_comfy_root = has_explicit_comfy_root_argument()
    comfy_root = resolve_comfy_root()
    ensure_search_paths(comfy_root)

    print("Qwen TE 单节点分享包依赖自检")
    print(f"- 节点目录: {NODE_DIR}")
    print(f"- ComfyUI 根目录: {comfy_root}")
    print(f"- 当前 Python: {sys.executable}")
    print("")

    blocking = False

    if not comfy_root.exists():
        line("FAIL", "提供的 ComfyUI 根目录不存在。")
        return 1

    if explicit_comfy_root and not is_comfy_root(comfy_root):
        line("FAIL", "显式提供的 ComfyUI 根目录无效：目录下缺少 folder_paths.py。")
        line("FAIL", "为避免误检，不会回退到当前 Python 搜索路径中的另一套 ComfyUI。")
        return 1

    if is_comfy_root(comfy_root):
        line("OK", "已识别到 ComfyUI 根目录。")
    else:
        module_root = find_comfy_root_from_module_path()
        if module_root and is_comfy_root(module_root):
            line("WARN", f"提供的目录下没找到 folder_paths.py；但当前 Python 能导入 ComfyUI 环境: {module_root}")
        else:
            line("WARN", "当前根目录下没找到 folder_paths.py；如果不是便携版，请确认你传入的是 ComfyUI 根目录。")

    print("")
    missing_files = check_files()
    if missing_files:
        blocking = True

    print("")
    for module_name, label in BLOCKING_MODULES:
        ok, detail = probe_module(module_name)
        if ok:
            if module_name == "folder_paths" and explicit_comfy_root:
                module = sys.modules.get(module_name)
                origin = Path(str(getattr(module, "__file__", "") or ""))
                try:
                    module_root = origin.resolve().parent
                except Exception:
                    module_root = None
                if module_root != comfy_root:
                    blocking = True
                    line(
                        "FAIL",
                        f"folder_paths 实际来自另一套 ComfyUI：{module_root or '未知路径'}；"
                        f"期望：{comfy_root}",
                    )
                    continue
            line("OK", f"模块可用: {module_name} ({label})")
        else:
            blocking = True
            line("FAIL", f"模块缺失: {module_name} ({label}) -> {detail}")

    print("")
    for module_name, label in OPTIONAL_MODULES:
        ok, detail = probe_module(module_name)
        if ok:
            line("OK", f"可选模块可用: {module_name} ({label})")
        else:
            line("WARN", f"可选模块缺失: {module_name} ({label}) -> {detail}")

    print("")
    ok, detail = probe_plugin_entry()
    if ok:
        line("OK", detail)
    else:
        blocking = True
        line("FAIL", "插件入口导入失败。")
        print(detail)

    print("")
    if blocking:
        line("SUMMARY", "发现阻塞问题：当前环境下节点可能不显示，或无法正常注册。")
        print("建议先处理这些高优先级问题：")
        print("1. 确认节点目录是 ComfyUI/custom_nodes/ComfyUI-RealMan-Prompt-Stage-Generator")
        print("2. 用 ComfyUI 自己的 Python 环境运行，而不是随便一个系统 Python")
        print("3. 主节点 UI 不需要 numpy / Pillow / llama_cpp / cv2；这些只影响可选模型或质检能力。")
        return 1

    line("SUMMARY", "主节点注册环境正常。就算缺少质检、Pillow、numpy 或 llama_cpp，可视界面也应能显示。")
    print("如果对方仍然看不到节点，请把 ComfyUI 启动日志里包含 QwenTE / ModuleNotFoundError / RealMan-Prompt-Stage-Generator 的几行发回来。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
