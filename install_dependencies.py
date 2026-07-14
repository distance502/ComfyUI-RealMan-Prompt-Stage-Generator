# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


NODE_DIR = Path(__file__).resolve().parent
PROBE_SCRIPT = NODE_DIR / "dependency_probe.py"

PACKAGE_GROUPS: list[tuple[str, list[str], bool]] = [
    ("质检依赖", ["opencv-python", "rapidocr-onnxruntime"], False),
    ("模型依赖", ["llama-cpp-python"], False),
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


def resolve_comfy_root(raw: str | None) -> Path:
    if raw and raw.strip():
        return Path(raw.strip().strip('"')).expanduser().resolve()
    return NODE_DIR.parent.parent.resolve()


def is_comfy_root(path: Path) -> bool:
    return path.is_dir() and (path / "folder_paths.py").is_file()


def build_install_commands(*, include_llama: bool = True, upgrade_pip: bool = False) -> list[tuple[str, list[str], bool]]:
    commands: list[tuple[str, list[str], bool]] = []
    if upgrade_pip:
        commands.append(("升级 pip", [sys.executable, "-m", "pip", "install", "--upgrade", "pip"], True))
    for group_name, packages, required in PACKAGE_GROUPS:
        if packages == ["llama-cpp-python"] and not include_llama:
            continue
        commands.append(
            (
                group_name,
                [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *packages],
                required,
            )
        )
    return commands


def run_command(label: str, command: list[str], *, required: bool, dry_run: bool) -> bool:
    printable = " ".join(f'"{item}"' if " " in item else item for item in command)
    if dry_run:
        line("DRY", f"{label}: {printable}")
        return True

    line("RUN", f"{label}: {printable}")
    completed = subprocess.run(command, check=False)
    if completed.returncode == 0:
        line("OK", f"{label} 安装完成。")
        return True

    level = "FAIL" if required else "WARN"
    line(level, f"{label} 安装失败，退出码 {completed.returncode}。")
    return False


def run_probe(comfy_root: Path, *, dry_run: bool) -> int:
    command = [sys.executable, str(PROBE_SCRIPT), str(comfy_root)]
    printable = " ".join(f'"{item}"' if " " in item else item for item in command)
    if dry_run:
        line("DRY", f"安装后自检: {printable}")
        return 0
    line("RUN", "开始安装后自检。")
    completed = subprocess.run(command, check=False)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Qwen TE 节点依赖自动补装脚本")
    parser.add_argument("comfy_root", nargs="?", help="ComfyUI 根目录")
    parser.add_argument("--skip-llama", action="store_true", help="跳过 llama-cpp-python")
    parser.add_argument("--upgrade-pip", action="store_true", help="补装前先升级 pip")
    parser.add_argument("--dry-run", action="store_true", help="只打印将执行的命令，不实际安装")
    args = parser.parse_args()

    comfy_root = resolve_comfy_root(args.comfy_root)

    print("Qwen TE 依赖自动补装")
    print(f"- 节点目录: {NODE_DIR}")
    print(f"- ComfyUI 根目录: {comfy_root}")
    print(f"- 当前 Python: {sys.executable}")
    print("")

    if not is_comfy_root(comfy_root):
        line("FAIL", "提供或推导出的 ComfyUI 根目录无效：目录下缺少 folder_paths.py。")
        line("FAIL", "为避免把依赖安装到错误的 Python 环境，本次没有执行任何 pip 命令。")
        return 1

    required_failed = False
    optional_failed = False
    for label, command, required in build_install_commands(
        include_llama=not args.skip_llama,
        upgrade_pip=args.upgrade_pip,
    ):
        ok = run_command(label, command, required=required, dry_run=args.dry_run)
        if ok:
            continue
        if required:
            required_failed = True
        else:
            optional_failed = True

    print("")
    probe_code = run_probe(comfy_root, dry_run=args.dry_run)
    print("")

    if args.dry_run:
        line("SUMMARY", "dry-run 完成，未实际安装。")
        return 0

    if required_failed:
        line("SUMMARY", "必需安装步骤失败；即使当前自检通过，也不能把本次补装报告为成功。")
        return 1
    if optional_failed:
        line("SUMMARY", "主节点无需这些可选依赖也能显示；失败项只影响质检或内置模型调用。")
        return 1
    if probe_code != 0:
        line("SUMMARY", "补装已执行，但自检仍未通过，请把输出发回来继续排。")
        return int(probe_code)

    line("SUMMARY", "依赖补装完成，自检通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
