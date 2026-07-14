# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


NODE_DIR = Path(__file__).resolve().parent
TARGET_DIR_NAME = "ComfyUI-RealMan-Prompt-Stage-Generator"
LEGACY_DIR_NAMES = ("comfyUI-qwen3_5-llama-TE",)
USER_DATA_FILES = (
    "prompt_tag_library_custom.json",
    "prompt_tag_library_custom.json.invalid.bak",
    "online_search_config.json",
    "user_tag_library.json",
)
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "output",
    "temp",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".log"}


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def line(level: str, message: str) -> None:
    print(f"[{level}] {message}")


def resolve_comfy_root(raw: str | None) -> Path:
    if raw and raw.strip():
        return Path(raw.strip().strip('"')).expanduser().resolve()
    return NODE_DIR.parent.parent.resolve()


def should_ignore(path: Path) -> bool:
    if path.name in EXCLUDE_DIRS:
        return True
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    return False


def path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def copy_tree(
    source: Path,
    target: Path,
    *,
    preserve_existing: set[str] | None = None,
) -> tuple[int, int]:
    copied_files = 0
    copied_dirs = 0
    preserved = set(preserve_existing or set())
    target.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        if any(part in EXCLUDE_DIRS for part in relative.parts):
            continue
        if should_ignore(item):
            continue
        destination = target / relative
        if item.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            copied_dirs += 1
            continue
        if relative.as_posix() in preserved and path_exists(destination):
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)
        copied_files += 1
    return copied_files, copied_dirs


def migrate_missing_user_data(
    legacy: Path,
    target: Path,
    target_files_before_update: set[str],
) -> list[str]:
    migrated: list[str] = []
    for relative in USER_DATA_FILES:
        if relative in target_files_before_update:
            continue
        source_file = legacy / relative
        if not source_file.is_file():
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)
        migrated.append(relative)
    return migrated


def disable_legacy_directory(legacy: Path) -> Path:
    if not legacy.is_dir():
        raise NotADirectoryError(f"旧插件路径不是目录，无法安全禁用：{legacy}")

    candidates = [legacy.with_name(f"{legacy.name}.backup.disabled")]
    candidates.extend(
        legacy.with_name(f"{legacy.name}.backup-{index}.disabled")
        for index in range(1, 10_000)
    )
    for candidate in candidates:
        if path_exists(candidate):
            continue
        try:
            legacy.rename(candidate)
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError(f"无法为旧插件目录生成不冲突的 .disabled 备份名：{legacy}")


def main() -> int:
    parser = argparse.ArgumentParser(description="把真男人提示词阶段生成器内嵌安装到 ComfyUI/custom_nodes")
    parser.add_argument("comfy_root", nargs="?", help="ComfyUI 根目录，例如 F:\\ComfyUI\\ComfyUI")
    args = parser.parse_args()

    comfy_root = resolve_comfy_root(args.comfy_root)
    custom_nodes = comfy_root / "custom_nodes"
    target = custom_nodes / TARGET_DIR_NAME

    print("真男人提示词阶段生成器内嵌安装到 ComfyUI")
    print(f"- 源节点目录: {NODE_DIR}")
    print(f"- ComfyUI 根目录: {comfy_root}")
    print(f"- 目标目录: {target}")
    print("")

    if not (comfy_root / "folder_paths.py").exists():
        line("FAIL", "没有识别到 ComfyUI 根目录：目标目录下缺少 folder_paths.py。")
        return 1
    if not custom_nodes.exists():
        line("FAIL", "目标 ComfyUI 缺少 custom_nodes 目录。")
        return 1

    target_files_before_update = {
        relative for relative in USER_DATA_FILES if path_exists(target / relative)
    }
    legacy_directories = [
        custom_nodes / name
        for name in LEGACY_DIR_NAMES
        if path_exists(custom_nodes / name)
    ]

    try:
        if NODE_DIR.resolve() == target.resolve():
            line("OK", "当前节点已经位于目标 ComfyUI/custom_nodes 中，无需复制代码文件。")
        else:
            copied_files, copied_dirs = copy_tree(
                NODE_DIR,
                target,
                preserve_existing=set(USER_DATA_FILES),
            )
            line("OK", f"已复制 {copied_files} 个文件、准备 {copied_dirs} 个目录。")

        if not (target / "__init__.py").is_file():
            raise RuntimeError(f"更新后的目标目录缺少 __init__.py：{target}")

        for legacy in legacy_directories:
            if legacy.resolve() == target.resolve():
                raise RuntimeError(f"旧目录与新目标指向同一位置，拒绝执行可能破坏数据的迁移：{legacy}")
            migrated = migrate_missing_user_data(
                legacy,
                target,
                target_files_before_update,
            )
            if migrated:
                line("OK", f"已从旧目录迁移用户文件：{', '.join(migrated)}")
            backup = disable_legacy_directory(legacy)
            line("OK", f"旧插件目录已无损禁用并保留为：{backup}")
    except Exception as exc:
        line("FAIL", f"安装或旧目录迁移失败：{type(exc).__name__}: {exc}")
        line("FAIL", "旧目录未能确认安全禁用；请不要启动 ComfyUI，以免新旧插件同时加载。")
        return 1

    line("NEXT", "请重启 ComfyUI，并在浏览器里 Ctrl+F5 强制刷新。")
    line("NEXT", "如果仍不显示，运行目标目录里的 一键检查依赖.bat。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
