# -*- coding: utf-8 -*-
"""
Export the template example suite report to Markdown.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPORT_JSON = ROOT / "output" / "template_example_suite_report.json"
REPORT_MD = ROOT / "output" / "template_example_suite_report.md"


def main() -> int:
    rows = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    lines = ["# Template Example Suite", ""]
    success_count = sum(1 for row in rows if str((row.get("image") or {}).get("status")) == "success")
    lines.append(f"- Images generated: `{success_count}/{len(rows)}`")
    lines.append("")
    for row in rows:
        lines.append(f"## {row.get('name')}")
        lines.append(f"- Template: `{row.get('template_style')}`")
        lines.append(f"- Image status: `{(row.get('image') or {}).get('status')}`")
        images = (row.get("image") or {}).get("images") or []
        if images:
            lines.append(f"- Output: `{images[0]}`")
        prompt_text = " ".join(str(row.get("prompt_text") or "").split())
        if prompt_text:
            lines.append(f"- Prompt: `{prompt_text[:220]}{'...' if len(prompt_text) > 220 else ''}`")
        lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Created: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
