# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import threading
import time
import unittest
from unittest import mock

import cv2
import numpy as np


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "quality_audit_ocr_skin.py"


def load_quality_audit_module():
    spec = importlib.util.spec_from_file_location("quality_audit_resource_test_module", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestQualityAuditResources(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_quality_audit_module()

    def setUp(self) -> None:
        self.module._OCR_INSTANCE = None
        self.module._FACE_CASCADE_INSTANCE = None

    @staticmethod
    def _write_png(path: pathlib.Path, *, width: int = 16, height: int = 12) -> None:
        image = np.zeros((height, width, 3), dtype=np.uint8)
        if not cv2.imwrite(str(path), image):
            raise RuntimeError(f"测试图片写入失败：{path}")

    def test_ocr_is_a_thread_safe_lazy_singleton(self) -> None:
        init_count = 0
        count_lock = threading.Lock()
        barrier = threading.Barrier(8)
        instances: list[object] = []

        class FakeOCR:
            def __init__(self):
                nonlocal init_count
                with count_lock:
                    init_count += 1
                time.sleep(0.02)

        def get_ocr() -> None:
            barrier.wait()
            instances.append(self.module._get_ocr())

        with mock.patch.object(self.module, "RapidOCR", FakeOCR):
            threads = [threading.Thread(target=get_ocr) for _ in range(8)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2.0)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(init_count, 1)
        self.assertEqual(len({id(instance) for instance in instances}), 1)

    def test_face_cascade_is_singleton_and_detection_is_serialized(self) -> None:
        init_count = 0
        active = 0
        max_active = 0
        count_lock = threading.Lock()
        barrier = threading.Barrier(6)

        class FakeCascade:
            @staticmethod
            def empty() -> bool:
                return False

            @staticmethod
            def detectMultiScale(_gray, **_kwargs):
                nonlocal active, max_active
                with count_lock:
                    active += 1
                    max_active = max(max_active, active)
                time.sleep(0.02)
                with count_lock:
                    active -= 1
                return np.empty((0, 4), dtype=np.int32)

        def make_cascade(_path: str):
            nonlocal init_count
            init_count += 1
            time.sleep(0.01)
            return FakeCascade()

        def detect() -> None:
            barrier.wait()
            self.module.detect_faces(np.zeros((96, 96), dtype=np.uint8))

        with mock.patch.object(self.module.cv2, "CascadeClassifier", side_effect=make_cascade):
            threads = [threading.Thread(target=detect) for _ in range(6)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2.0)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(init_count, 1)
        self.assertEqual(max_active, 1)

    def test_direct_audit_batches_are_serialized(self) -> None:
        active = 0
        max_active = 0
        count_lock = threading.Lock()
        barrier = threading.Barrier(2)

        def audit_one(_ocr, path):
            nonlocal active, max_active
            with count_lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.04)
            with count_lock:
                active -= 1
            return {"image": str(path)}

        def audit(path: str) -> None:
            barrier.wait()
            self.module.audit_images([path])

        with (
            mock.patch.object(self.module, "_get_ocr", return_value=object()),
            mock.patch.object(self.module, "audit_one_image", side_effect=audit_one),
        ):
            threads = [threading.Thread(target=audit, args=(f"image-{index}.png",)) for index in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2.0)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(max_active, 1)

    def test_direct_audit_rejects_more_than_twenty_four_images_before_ocr_init(self) -> None:
        with mock.patch.object(self.module, "_get_ocr") as get_ocr:
            with self.assertRaisesRegex(ValueError, "一次最多审计 24 张图片"):
                self.module.audit_images([f"image-{index}.png" for index in range(25)])
        get_ocr.assert_not_called()

    def test_empty_audit_does_not_initialize_ocr(self) -> None:
        with mock.patch.object(self.module, "_get_ocr") as get_ocr:
            result = self.module.audit_images([])
        get_ocr.assert_not_called()
        self.assertEqual(result["summary"]["total_images"], 0)
        self.assertEqual(result["images"], [])

    def test_oversized_file_is_rejected_before_header_decode_and_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = pathlib.Path(temp_dir) / "oversized.png"
            image_path.write_bytes(b"x" * 9)
            ocr = mock.Mock()
            with (
                mock.patch.object(self.module, "MAX_AUDIT_IMAGE_FILE_BYTES", 8),
                mock.patch.object(self.module.Image, "open") as image_open,
                mock.patch.object(self.module.cv2, "imdecode") as imdecode,
            ):
                row = self.module.audit_one_image(ocr, image_path)

        self.assertEqual(row["error"], "image_file_too_large")
        self.assertIn("8 字节上限", row["error_detail"])
        image_open.assert_not_called()
        imdecode.assert_not_called()
        ocr.assert_not_called()

    def test_image_edge_and_pixel_limits_are_checked_before_full_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = pathlib.Path(temp_dir) / "dimensions.png"
            self._write_png(image_path, width=4, height=3)

            for patched_name, patched_value in (
                ("MAX_AUDIT_IMAGE_EDGE", 3),
                ("MAX_AUDIT_IMAGE_PIXELS", 11),
            ):
                with self.subTest(limit=patched_name):
                    with (
                        mock.patch.object(self.module, patched_name, patched_value),
                        mock.patch.object(self.module.cv2, "imdecode") as imdecode,
                    ):
                        row = self.module.audit_one_image(mock.Mock(), image_path)
                    self.assertEqual(row["error"], "image_dimensions_too_large")
                    self.assertIn("4x3", row["error_detail"])
                    imdecode.assert_not_called()

    def test_normal_image_is_decoded_once_and_ocr_receives_ndarray(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = pathlib.Path(temp_dir) / "normal.png"
            self._write_png(image_path, width=16, height=12)
            received: list[np.ndarray] = []

            def ocr(image):
                received.append(image)
                return [], 0.0

            with (
                mock.patch.object(self.module, "detect_faces", return_value=[]),
                mock.patch.object(self.module.cv2, "imdecode", wraps=self.module.cv2.imdecode) as imdecode,
            ):
                row = self.module.audit_one_image(ocr, image_path)

        self.assertNotIn("error", row)
        self.assertEqual(row["ocr"]["detected_count"], 0)
        self.assertEqual(len(received), 1)
        self.assertIsInstance(received[0], np.ndarray)
        self.assertEqual(received[0].shape, (12, 16, 3))
        imdecode.assert_called_once()

    def test_per_image_ocr_and_face_results_are_bounded(self) -> None:
        raw_ocr_rows = [
            ([[0, 0], [1, 0], [1, 1], [0, 1]], f"token-{index}", 0.9)
            for index in range(400)
        ]
        parsed = self.module.parse_ocr_result(raw_ocr_rows)
        self.assertEqual(len(parsed), self.module.MAX_AUDIT_OCR_ROWS)

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = pathlib.Path(temp_dir) / "many-faces.png"
            self._write_png(image_path, width=96, height=96)
            metrics = {
                "lap_var": 10.0,
                "edge_density": 0.1,
                "high_freq": 5.0,
                "wrinkle_risk": 0.0,
                "oversmooth_risk": 0.0,
            }
            with (
                mock.patch.object(
                    self.module,
                    "detect_faces",
                    return_value=[(0, 0, 16, 16)] * 100,
                ),
                mock.patch.object(
                    self.module,
                    "face_texture_metrics",
                    return_value=metrics,
                ) as texture_metrics,
            ):
                row = self.module.audit_one_image(lambda _image: ([], 0.0), image_path)

        self.assertEqual(row["faces"]["count"], self.module.MAX_AUDIT_FACES_PER_IMAGE)
        self.assertEqual(texture_metrics.call_count, self.module.MAX_AUDIT_FACES_PER_IMAGE)

    def test_invalid_header_returns_a_clear_error_without_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = pathlib.Path(temp_dir) / "broken.png"
            image_path.write_bytes(b"not an image")
            ocr = mock.Mock()
            row = self.module.audit_one_image(ocr, image_path)

        self.assertEqual(row["error"], "image_header_invalid")
        self.assertTrue(row["error_detail"])
        ocr.assert_not_called()

        markdown = self.module.build_markdown(
            {
                "summary": {
                    "total_images": 1,
                    "ocr_risk_images": 0,
                    "wrinkle_risk_images": 0,
                    "oversmooth_risk_images": 0,
                },
                "images": [row],
            }
        )
        self.assertIn(f"- error: {row['error']}", markdown)
        self.assertIn(f"- detail: {row['error_detail']}", markdown)


if __name__ == "__main__":
    unittest.main()
