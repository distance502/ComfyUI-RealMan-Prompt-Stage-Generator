# -*- coding: utf-8 -*-
"""
Export the stage regression JSON report to a compact Markdown summary.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT / "output" / "codex_stage_regression_report.json"
REPORT_MD = ROOT / "output" / "codex_stage_regression_report.md"


def main() -> int:
    data = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    lines: list[str] = ["# QwenTE Stage Regression Report", ""]
    ok_count = 0
    total_count = 0
    for row in data:
        stage = row.get("stage") or {}
        evaluations = stage.get("evaluations") or []
        stage_ok = bool(evaluations) and all(item.get("ok") for item in evaluations)
        total_count += 1
        ok_count += 1 if stage_ok else 0
    lines.append(f"- Summary: `{ok_count}/{total_count}` stage cases passed")
    lines.append("")

    for row in data:
        name = str(row.get("name") or "unknown")
        stage = row.get("stage") or {}
        evaluations = stage.get("evaluations") or []
        stage_ok = bool(evaluations) and all(item.get("ok") for item in evaluations)
        image = row.get("image") or {}
        image_status = image.get("status")
        lines.append(f"## {name}")
        lines.append(f"- Stage: `{'PASS' if stage_ok else 'FAIL'}`")
        if image_status:
            lines.append(f"- Image: `{image_status}`")
        if row.get("error"):
            lines.append(f"- Error: `{row['error']}`")
        prompt_lines = stage.get("prompt_lines") or []
        for index, prompt_line in enumerate(prompt_lines[:2], start=1):
            clean = " ".join(str(prompt_line).split())
            lines.append(f"- Prompt {index}: `{clean[:220]}{'...' if len(clean) > 220 else ''}`")
        images = image.get("images") or []
        for image_path in images[:1]:
            lines.append(f"- Output: `{image_path}`")
        lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Created: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
