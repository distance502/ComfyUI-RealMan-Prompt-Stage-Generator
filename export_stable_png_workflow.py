# -*- coding: utf-8 -*-
"""
Export a stable workflow JSON from a ComfyUI PNG by bypassing risky cleanup nodes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image

if __package__:
    from .workflow_cleanup import 旁路清理节点工作流
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from workflow_cleanup import 旁路清理节点工作流


def _load_png_workflow(png_path: Path) -> dict[str, Any]:
    image = Image.open(png_path)
    workflow_text = image.info.get("workflow")
    if not workflow_text:
        raise ValueError(f"PNG 不包含 workflow 元数据：{png_path}")
    return json.loads(str(workflow_text))


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args:
        raise SystemExit("Usage: export_stable_png_workflow.py <png_path> [output_json]")

    png_path = Path(args[0]).resolve()
    if not png_path.exists():
        raise FileNotFoundError(f"未找到 PNG：{png_path}")

    if len(args) >= 2:
        output_path = Path(args[1]).resolve()
    else:
        output_path = png_path.with_suffix(".stable.workflow.json")

    workflow = _load_png_workflow(png_path)
    workflow = 旁路清理节点工作流(workflow)
    output_path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
