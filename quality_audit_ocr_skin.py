# -*- coding: utf-8 -*-
"""
Image quality audit for generated outputs:
1) OCR/text leak risk (readable text, watermark-like artifacts)
2) Face skin texture risk (over-sharpened wrinkles / overly smooth skin)
"""

from __future__ import annotations

import io
import json
import re
import threading
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "output" / "codex_stage_regression_report.json"
OUT_JSON = ROOT / "output" / "codex_quality_audit_report.json"
OUT_MD = ROOT / "output" / "codex_quality_audit_report.md"

TEXT_TOKEN_RE = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]{2,}")

MAX_AUDIT_IMAGES = 24
MAX_AUDIT_IMAGE_FILE_BYTES = 64 * 1024 * 1024
MAX_AUDIT_IMAGE_EDGE = 8192
MAX_AUDIT_IMAGE_PIXELS = 40_000_000
MAX_AUDIT_OCR_ROWS = 256
MAX_AUDIT_FACES_PER_IMAGE = 64

_AUDIT_LOCK = threading.RLock()
_OCR_LOCK = threading.RLock()
_FACE_CASCADE_LOCK = threading.RLock()
_OCR_INSTANCE: RapidOCR | None = None
_FACE_CASCADE_INSTANCE: Any | None = None


def _get_ocr() -> RapidOCR:
    global _OCR_INSTANCE
    with _OCR_LOCK:
        if _OCR_INSTANCE is None:
            _OCR_INSTANCE = RapidOCR()
        return _OCR_INSTANCE


def _get_face_cascade() -> Any:
    global _FACE_CASCADE_INSTANCE
    with _FACE_CASCADE_LOCK:
        if _FACE_CASCADE_INSTANCE is None:
            cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            _FACE_CASCADE_INSTANCE = cv2.CascadeClassifier(str(cascade_path))
        return _FACE_CASCADE_INSTANCE


def _read_bounded_image(image_path: Path) -> tuple[np.ndarray | None, str | None, str | None]:
    try:
        file_size = image_path.stat().st_size
    except OSError as exc:
        return None, "image_read_failed", f"无法读取图片文件信息：{exc}"
    if file_size > MAX_AUDIT_IMAGE_FILE_BYTES:
        return (
            None,
            "image_file_too_large",
            f"图片文件为 {file_size} 字节，超过 {MAX_AUDIT_IMAGE_FILE_BYTES} 字节上限",
        )

    try:
        with image_path.open("rb") as image_file:
            encoded = image_file.read(MAX_AUDIT_IMAGE_FILE_BYTES + 1)
    except OSError as exc:
        return None, "image_read_failed", f"无法读取图片文件：{exc}"
    if len(encoded) > MAX_AUDIT_IMAGE_FILE_BYTES:
        return (
            None,
            "image_file_too_large",
            f"图片文件超过 {MAX_AUDIT_IMAGE_FILE_BYTES} 字节上限",
        )

    try:
        with Image.open(io.BytesIO(encoded)) as image_header:
            width, height = (int(value) for value in image_header.size)
    except Exception as exc:
        return None, "image_header_invalid", f"无法读取图片尺寸：{exc}"

    pixels = width * height
    if width <= 0 or height <= 0:
        return None, "image_header_invalid", f"图片尺寸无效：{width}x{height}"
    if width > MAX_AUDIT_IMAGE_EDGE or height > MAX_AUDIT_IMAGE_EDGE or pixels > MAX_AUDIT_IMAGE_PIXELS:
        return (
            None,
            "image_dimensions_too_large",
            (
                f"图片尺寸 {width}x{height} 超过限制：单边不超过 {MAX_AUDIT_IMAGE_EDGE}，"
                f"总像素不超过 {MAX_AUDIT_IMAGE_PIXELS}"
            ),
        )

    encoded_array = np.frombuffer(encoded, dtype=np.uint8)
    try:
        image = cv2.imdecode(encoded_array, cv2.IMREAD_COLOR)
    except cv2.error as exc:
        return None, "image_load_failed", f"OpenCV 解码图片失败：{exc}"
    if image is None:
        return None, "image_load_failed", "OpenCV 无法解码图片"
    return image, None, None


def _run_ocr(ocr: RapidOCR, image: np.ndarray) -> Any:
    # ONNX Runtime sessions may be shared, but RapidOCR's preprocessing state is not
    # documented as safe for concurrent calls.
    with _OCR_LOCK:
        return ocr(image)


def clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def risk_level(score: float) -> str:
    if score >= 0.65:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


def load_image_paths() -> list[Path]:
    if not REPORT_PATH.exists():
        return []
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    paths: list[Path] = []
    seen: set[str] = set()
    for item in payload:
        image = item.get("image")
        if not isinstance(image, dict):
            continue
        for image_path in image.get("images") or []:
            raw = str(image_path or "").strip()
            if not raw:
                continue
            normalized = str(Path(raw))
            if normalized in seen:
                continue
            seen.add(normalized)
            paths.append(Path(raw))
    return paths


def parse_ocr_result(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if result is None:
        return rows
    if isinstance(result, tuple) and result:
        result = result[0]
    if not isinstance(result, list):
        return rows
    for item in result:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        text = str(item[1] or "").strip()
        try:
            score = float(item[2])
        except Exception:
            score = 0.0
        if not text:
            continue
        if not TEXT_TOKEN_RE.search(text):
            continue
        rows.append({"text": text, "score": score})
        if len(rows) >= MAX_AUDIT_OCR_ROWS:
            break
    return rows


def compute_ocr_risk(ocr_rows: list[dict[str, Any]]) -> tuple[float, str]:
    if not ocr_rows:
        return 0.0, "low"
    weighted = 0.0
    for row in ocr_rows:
        text = str(row["text"])
        score = float(row["score"])
        token_len = min(8.0, max(1.0, float(len(text))))
        weighted += clamp01(score) * (token_len / 8.0)
    norm = clamp01(weighted / 2.2)
    return norm, risk_level(norm)


def detect_faces(gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    with _FACE_CASCADE_LOCK:
        cascade = _get_face_cascade()
        if cascade.empty():
            return []
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.08,
            minNeighbors=5,
            minSize=(64, 64),
        )
    return [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]


def face_texture_metrics(gray_face: np.ndarray) -> dict[str, float]:
    lap_var = float(cv2.Laplacian(gray_face, cv2.CV_64F).var())
    edges = cv2.Canny(gray_face, 70, 160)
    edge_density = float((edges > 0).mean())
    blur = cv2.GaussianBlur(gray_face, (0, 0), sigmaX=2.0, sigmaY=2.0)
    high_freq = float(np.mean(np.abs(gray_face.astype(np.float32) - blur.astype(np.float32))))

    wrinkle_risk = (
        clamp01((lap_var - 350.0) / 900.0) * 0.45
        + clamp01((edge_density - 0.11) / 0.20) * 0.35
        + clamp01((high_freq - 14.0) / 22.0) * 0.20
    )
    oversmooth_risk = (
        clamp01((120.0 - lap_var) / 120.0) * 0.6
        + clamp01((0.04 - edge_density) / 0.04) * 0.4
    )
    return {
        "lap_var": lap_var,
        "edge_density": edge_density,
        "high_freq": high_freq,
        "wrinkle_risk": clamp01(wrinkle_risk),
        "oversmooth_risk": clamp01(oversmooth_risk),
    }


def audit_one_image(ocr: RapidOCR, image_path: Path) -> dict[str, Any]:
    row: dict[str, Any] = {
        "image": str(image_path),
        "exists": image_path.exists(),
    }
    if not image_path.exists():
        row["error"] = "file_not_found"
        return row

    image, load_error, error_detail = _read_bounded_image(image_path)
    if load_error is not None or image is None:
        row["error"] = load_error or "image_load_failed"
        if error_detail:
            row["error_detail"] = error_detail
        return row

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    ocr_rows = parse_ocr_result(_run_ocr(ocr, image))
    ocr_score, ocr_level = compute_ocr_risk(ocr_rows)

    faces = detect_faces(gray)[:MAX_AUDIT_FACES_PER_IMAGE]
    face_rows: list[dict[str, Any]] = []
    wrinkle_scores: list[float] = []
    oversmooth_scores: list[float] = []
    for (x, y, w, h) in faces:
        face = gray[y : y + h, x : x + w]
        if face.size == 0:
            continue
        # Center crop in face box for more stable skin-region estimate.
        cx0 = int(w * 0.15)
        cx1 = int(w * 0.85)
        cy0 = int(h * 0.18)
        cy1 = int(h * 0.90)
        core = face[cy0:cy1, cx0:cx1] if cy1 > cy0 and cx1 > cx0 else face
        metrics = face_texture_metrics(core)
        wrinkle_scores.append(float(metrics["wrinkle_risk"]))
        oversmooth_scores.append(float(metrics["oversmooth_risk"]))
        face_rows.append(
            {
                "box": [x, y, w, h],
                "lap_var": round(float(metrics["lap_var"]), 3),
                "edge_density": round(float(metrics["edge_density"]), 4),
                "high_freq": round(float(metrics["high_freq"]), 3),
                "wrinkle_risk": round(float(metrics["wrinkle_risk"]), 4),
                "oversmooth_risk": round(float(metrics["oversmooth_risk"]), 4),
            }
        )

    wrinkle_score = float(np.mean(wrinkle_scores)) if wrinkle_scores else None
    oversmooth_score = float(np.mean(oversmooth_scores)) if oversmooth_scores else None

    findings: list[str] = []
    if ocr_score >= 0.35:
        findings.append("detected_readable_text_risk")
    if wrinkle_score is not None and wrinkle_score >= 0.35:
        findings.append("skin_wrinkle_or_oversharpen_risk")
    if oversmooth_score is not None and oversmooth_score >= 0.45:
        findings.append("skin_oversmooth_risk")

    recommendations: list[str] = []
    if "detected_readable_text_risk" in findings:
        recommendations.append("increase text/typography negative weight and avoid signboard/screen-like scene tokens")
    if "skin_wrinkle_or_oversharpen_risk" in findings:
        recommendations.append("reduce harsh-light/high-contrast/film-grain tokens and keep soft highlight roll-off")
    if "skin_oversmooth_risk" in findings:
        recommendations.append("add natural micro-texture cues to avoid waxy skin")
    if not recommendations:
        recommendations.append("no immediate risk found")

    row.update(
        {
            "ocr": {
                "detected_count": len(ocr_rows),
                "detected_rows": ocr_rows[:12],
                "risk_score": round(ocr_score, 4),
                "risk_level": ocr_level,
            },
            "faces": {
                "count": len(face_rows),
                "rows": face_rows,
                "wrinkle_risk_score": round(wrinkle_score, 4) if wrinkle_score is not None else None,
                "wrinkle_risk_level": risk_level(wrinkle_score) if wrinkle_score is not None else "n/a",
                "oversmooth_risk_score": round(oversmooth_score, 4) if oversmooth_score is not None else None,
                "oversmooth_risk_level": risk_level(oversmooth_score) if oversmooth_score is not None else "n/a",
            },
            "findings": findings,
            "recommendations": recommendations,
        }
    )
    return row


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Codex OCR + Skin Quality Audit",
        "",
        f"- images: {result['summary']['total_images']}",
        f"- ocr_risk_images: {result['summary']['ocr_risk_images']}",
        f"- wrinkle_risk_images: {result['summary']['wrinkle_risk_images']}",
        f"- oversmooth_risk_images: {result['summary']['oversmooth_risk_images']}",
        "",
        "## Per Image",
        "",
    ]
    for row in result["images"]:
        lines.append(f"### {Path(row['image']).name}")
        if row.get("error"):
            lines.append(f"- error: {row['error']}")
            if row.get("error_detail"):
                lines.append(f"- detail: {row['error_detail']}")
            lines.append("")
            continue
        ocr = row["ocr"]
        faces = row["faces"]
        lines.append(f"- ocr: {ocr['risk_level']} ({ocr['risk_score']}) | hits={ocr['detected_count']}")
        lines.append(
            f"- skin_wrinkle: {faces['wrinkle_risk_level']} ({faces['wrinkle_risk_score']}) | "
            f"oversmooth: {faces['oversmooth_risk_level']} ({faces['oversmooth_risk_score']}) | faces={faces['count']}"
        )
        lines.append(f"- findings: {', '.join(row['findings']) if row['findings'] else 'none'}")
        lines.append(f"- recommendations: {', '.join(row['recommendations'])}")
        lines.append("")
    return "\n".join(lines)


def collect_recent_output_images(limit: int = 6, output_dir: Path | None = None, after_timestamp_ms: int | float | None = None) -> list[Path]:
    target_dir = output_dir or (ROOT / "output")
    if not target_dir.exists():
        return []
    threshold = None
    if after_timestamp_ms is not None:
        try:
            threshold = float(after_timestamp_ms) / 1000.0
        except Exception:
            threshold = None
    image_paths = [
        path
        for path in target_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        and (threshold is None or path.stat().st_mtime >= threshold)
    ]
    image_paths.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return image_paths[: max(1, int(limit))]


def build_quality_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total_images": len(rows),
        "ocr_risk_images": sum(
            1 for row in rows if isinstance(row.get("ocr"), dict) and float(row["ocr"]["risk_score"]) >= 0.35
        ),
        "wrinkle_risk_images": sum(
            1
            for row in rows
            if isinstance(row.get("faces"), dict)
            and row["faces"].get("wrinkle_risk_score") is not None
            and float(row["faces"]["wrinkle_risk_score"]) >= 0.35
        ),
        "oversmooth_risk_images": sum(
            1
            for row in rows
            if isinstance(row.get("faces"), dict)
            and row["faces"].get("oversmooth_risk_score") is not None
            and float(row["faces"]["oversmooth_risk_score"]) >= 0.45
        ),
    }


def audit_images(image_paths: list[Path | str]) -> dict[str, Any]:
    bounded_paths = list(image_paths)
    if len(bounded_paths) > MAX_AUDIT_IMAGES:
        raise ValueError(f"一次最多审计 {MAX_AUDIT_IMAGES} 张图片，当前收到 {len(bounded_paths)} 张")
    if not bounded_paths:
        return {"summary": build_quality_summary([]), "images": []}
    with _AUDIT_LOCK:
        ocr = _get_ocr()
        rows = [audit_one_image(ocr, Path(path)) for path in bounded_paths]
        return {"summary": build_quality_summary(rows), "images": rows}


def main() -> int:
    image_paths = load_image_paths()
    result = audit_images(image_paths)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(build_markdown(result), encoding="utf-8")

    print(f"json={OUT_JSON}")
    print(f"md={OUT_MD}")
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
