# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import pathlib
import tempfile
import threading
import time
import types
import unittest
from collections import OrderedDict
from unittest import mock

import numpy as np

from test_stage_prompt_modules import (
    load_nodes_for_storage_test,
    load_plugin_init_for_integration_test,
    load_stage_prompt_generator_for_integration_test,
)


class _Headers(dict):
    def get_content_charset(self):
        return "utf-8"


class _BufferedResponse:
    def __init__(self, payload: bytes = b"", *, content_length: int | None = None):
        self._payload = payload
        self._offset = 0
        self.headers = _Headers()
        if content_length is not None:
            self.headers["Content-Length"] = str(content_length)

    def read1(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._payload) - self._offset
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    read = read1

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class TestOnlineResponseLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plugin_init = load_plugin_init_for_integration_test()

    def test_online_response_limit_is_eight_mebibytes(self) -> None:
        self.assertEqual(self.plugin_init._ONLINE_RESPONSE_MAX_BYTES, 8 * 1024 * 1024)

    def test_online_response_rejects_oversized_content_length_before_reading(self) -> None:
        response = _BufferedResponse(
            b"not-read",
            content_length=self.plugin_init._ONLINE_RESPONSE_MAX_BYTES + 1,
        )

        with self.assertRaisesRegex(RuntimeError, "Content-Length"):
            self.plugin_init._读取受限在线响应(response, timeout=1.0, label="测试联网")

        self.assertEqual(response._offset, 0)

    def test_online_response_rejects_chunked_body_after_cumulative_limit(self) -> None:
        response = _BufferedResponse(b"123456789")
        with (
            mock.patch.object(self.plugin_init, "_ONLINE_RESPONSE_MAX_BYTES", 8),
            mock.patch.object(self.plugin_init, "_ONLINE_READ_CHUNK_BYTES", 4),
        ):
            with self.assertRaisesRegex(RuntimeError, "8 字节上限"):
                self.plugin_init._读取受限在线响应(response, timeout=1.0, label="测试联网")

        self.assertEqual(response._offset, 9)


class TestRequestJsonLimits(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_plugin_init_for_integration_test()

    def test_content_length_is_rejected_before_json_parsing(self) -> None:
        request = types.SimpleNamespace(
            content_length=self.module._REQUEST_JSON_MAX_BYTES + 1,
            _read_bytes=None,
            json=mock.AsyncMock(side_effect=AssertionError("must not parse")),
        )
        with self.assertRaises(self.module.web.HTTPRequestEntityTooLarge):
            self.module.asyncio.run(self.module._read_request_json(request))
        request.json.assert_not_awaited()

    def test_chunked_json_body_is_bounded_before_decode(self) -> None:
        class Content:
            async def iter_chunked(self, _size):
                for chunk in (b"1234", b"56789"):
                    yield chunk

        request = types.SimpleNamespace(
            content_length=None,
            _read_bytes=None,
            content=Content(),
            charset="utf-8",
        )
        with mock.patch.object(self.module, "_REQUEST_JSON_MAX_BYTES", 8):
            with self.assertRaises(self.module.web.HTTPRequestEntityTooLarge):
                self.module.asyncio.run(self.module._read_request_json(request))

    def test_small_chunked_json_body_is_parsed(self) -> None:
        class Content:
            async def iter_chunked(self, _size):
                yield b'{"ok":'
                yield b"true}"

        request = types.SimpleNamespace(
            content_length=None,
            _read_bytes=None,
            content=Content(),
            charset="utf-8",
        )
        self.assertEqual(
            self.module.asyncio.run(self.module._read_request_json(request)),
            {"ok": True},
        )


class TestQualityAuditLimits(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_plugin_init_for_integration_test()

    def test_quality_audit_prompt_ids_are_deduplicated_validated_and_capped(self) -> None:
        raw_ids = ["first", "first", "x" * 257] + [f"prompt-{index}" for index in range(40)]
        prompt_ids, error = self.module._parse_quality_audit_source_request(
            {"history_prompt_ids": raw_ids}
        )

        self.assertIsNone(error)
        self.assertEqual(len(prompt_ids), 24)
        self.assertEqual(prompt_ids[:2], ["first", "prompt-0"])
        self.assertEqual(len(prompt_ids), len(set(prompt_ids)))
        self.assertNotIn("x" * 257, prompt_ids)

    def test_quality_audit_route_caps_history_ids_and_images(self) -> None:
        handlers: dict[tuple[str, str], object] = {}

        class FakeRoutes:
            def get(self, path):
                return lambda handler: handlers.setdefault(("GET", path), handler)

            def post(self, path):
                return lambda handler: handlers.setdefault(("POST", path), handler)

        class FakeRequest:
            async def json(self):
                return {
                    "history_prompt_ids": [f"prompt-{index}" for index in range(40)],
                    "limit": 5,
                }

        prompt_server = types.SimpleNamespace(routes=FakeRoutes())
        self.module._get_prompt_server_class = lambda: types.SimpleNamespace(instance=prompt_server)
        self.module._QUALITY_AUDIT_IMPORT_ERROR = None
        captured: dict[str, object] = {}

        def collect_history(_server, prompt_ids, *, max_images=None):
            captured["prompt_ids"] = list(prompt_ids)
            captured["max_images"] = max_images
            return [pathlib.Path(f"image-{index}.png") for index in range(40)]

        def audit_images(image_paths):
            captured["image_paths"] = list(image_paths)
            return {
                "summary": {
                    "total_images": len(image_paths),
                    "ocr_risk_images": 0,
                    "wrinkle_risk_images": 0,
                    "oversmooth_risk_images": 0,
                },
                "images": [],
            }

        self.module._collect_history_prompt_image_paths = collect_history
        self.module.audit_images = audit_images
        self.module.build_quality_markdown = lambda _result: "# audit"

        self.assertTrue(self.module._register_tag_routes())
        handler = handlers[("POST", "/qwen_te/quality_audit")]
        response = self.module.asyncio.run(handler(FakeRequest()))
        payload = json.loads(response.text)

        self.assertEqual(response.status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(len(captured["prompt_ids"]), 24)
        self.assertEqual(captured["max_images"], 5)
        self.assertEqual(len(captured["image_paths"]), 5)
        self.assertEqual(payload["result"]["summary"]["total_images"], 5)

    def test_history_image_collection_stops_at_requested_limit(self) -> None:
        module = self.module
        get_history_calls: list[str] = []
        resolve_calls: list[str] = []

        class PromptQueue:
            def get_history(self, *, prompt_id):
                get_history_calls.append(prompt_id)
                return {
                    prompt_id: {
                        "outputs": {
                            "node": {
                                "images": [
                                    {"filename": f"image-{index}.png", "type": "output"}
                                    for index in range(100)
                                ]
                            }
                        }
                    }
                }

        def resolve(image):
            resolve_calls.append(image["filename"])
            return pathlib.Path(image["filename"])

        server = types.SimpleNamespace(prompt_queue=PromptQueue())
        with mock.patch.object(module, "_resolve_history_image_path", side_effect=resolve):
            paths = module._collect_history_prompt_image_paths(
                server,
                ["prompt-a", "prompt-b"],
                max_images=3,
            )

        self.assertEqual(paths, [pathlib.Path(f"image-{index}.png") for index in range(3)])
        self.assertEqual(get_history_calls, ["prompt-a"])
        self.assertEqual(resolve_calls, [f"image-{index}.png" for index in range(3)])


class TestApiResponseLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.stage_generator = load_stage_prompt_generator_for_integration_test()

    def test_api_response_limit_is_sixteen_mebibytes(self) -> None:
        self.assertEqual(self.stage_generator._API_RESPONSE_MAX_BYTES, 16 * 1024 * 1024)

    def test_api_response_rejects_oversized_content_length_and_chunked_body(self) -> None:
        response = _BufferedResponse(b"not-read", content_length=9)
        with self.assertRaisesRegex(RuntimeError, "Content-Length"):
            self.stage_generator._read_http_response_limited(
                response,
                max_bytes=8,
                timeout=1.0,
                label="测试 API",
            )
        self.assertEqual(response._offset, 0)

        chunked_response = _BufferedResponse(b"123456789")
        with mock.patch.object(self.stage_generator, "_HTTP_READ_CHUNK_BYTES", 4):
            with self.assertRaisesRegex(RuntimeError, "8 字节上限"):
                self.stage_generator._read_http_response_limited(
                    chunked_response,
                    max_bytes=8,
                    timeout=1.0,
                    label="测试 API",
                )
        self.assertEqual(chunked_response._offset, 9)

    def test_http_post_uses_response_limit(self) -> None:
        response = _BufferedResponse(
            content_length=self.stage_generator._API_RESPONSE_MAX_BYTES + 1
        )
        opener = mock.Mock()
        opener.open.return_value = response

        with mock.patch.object(self.stage_generator, "_API_HTTP_OPENER", opener):
            with self.assertRaisesRegex(RuntimeError, "Content-Length"):
                self.stage_generator._http_post_json(
                    "https://api.example.test/chat",
                    {"messages": []},
                    {"Authorization": "Bearer secret"},
                    1.0,
                )

        opener.open.assert_called_once()

    def test_api_redirect_handler_refuses_all_redirects(self) -> None:
        handler = self.stage_generator._NoSecretRedirectHandler()
        request = self.stage_generator.urllib.request.Request(
            "https://api.example.test/chat",
            headers={"Authorization": "Bearer secret"},
        )

        with self.assertRaisesRegex(RuntimeError, "不会自动跟随") as raised:
            handler.redirect_request(
                request,
                None,
                307,
                "Temporary Redirect",
                {},
                "https://user:password-secret@other.example.test/token-path-secret?key=top-secret",
            )
        self.assertNotIn("top-secret", str(raised.exception))
        self.assertNotIn("password-secret", str(raised.exception))
        self.assertNotIn("token-path-secret", str(raised.exception))
        self.assertIn("redacted", str(raised.exception))

    def test_gemini_api_key_is_sent_in_header_instead_of_url(self) -> None:
        captured: dict[str, object] = {}

        def fake_post(url, payload, headers, timeout):
            captured.update(url=url, payload=payload, headers=dict(headers), timeout=timeout)
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

        model = self.stage_generator._TEAPIChatModel(
            {
                "provider": "Gemini 原生",
                "kind": "gemini",
                "model": "gemini-test",
                "url": "https://generativelanguage.googleapis.com/v1beta",
                "api_key": "top-secret",
                "timeout": 5,
                "extra_headers": {},
            }
        )
        with mock.patch.object(self.stage_generator, "_http_post_json", side_effect=fake_post):
            result = model.create_chat_completion(
                messages=[{"role": "user", "content": "hello"}],
                max_tokens=20,
            )

        self.assertEqual(result["choices"][0]["message"]["content"], "ok")
        self.assertNotIn("top-secret", str(captured["url"]))
        self.assertNotIn("?key=", str(captured["url"]))
        self.assertEqual(captured["headers"]["x-goog-api-key"], "top-secret")


class TestCooperativeWaits(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_stage_prompt_generator_for_integration_test()

    def test_stage_key_lock_wait_observes_comfy_interruption(self) -> None:
        module = self.module
        key = "cooperative-stage-lock"
        lock = module._cache_key_lock(key)
        locked = threading.Event()
        release = threading.Event()

        def hold_lock() -> None:
            lock.acquire()
            locked.set()
            release.wait(2.0)
            lock.release()

        holder = threading.Thread(target=hold_lock)
        holder.start()
        self.assertTrue(locked.wait(1.0))

        class Interrupted(RuntimeError):
            pass

        checks = iter((False, True))
        fake_mm = types.SimpleNamespace(
            processing_interrupted=lambda: next(checks),
            InterruptProcessingException=Interrupted,
        )
        transaction = module._StageCacheTransaction()
        started = time.monotonic()
        try:
            with (
                mock.patch.object(module, "_comfy_mm", fake_mm),
                mock.patch.object(module, "_COOPERATIVE_WAIT_POLL_SECONDS", 0.01),
            ):
                with self.assertRaises(Interrupted):
                    transaction.bind(key)
        finally:
            release.set()
            holder.join(1.0)

        self.assertLess(time.monotonic() - started, 0.5)
        self.assertFalse(transaction.owns_key_lock)
        self.assertNotIn(key, module._STAGE_CACHE_PINNED_KEYS)

    def test_stage_key_lock_is_released_when_cancel_arrives_after_acquire(self) -> None:
        module = self.module

        class Interrupted(RuntimeError):
            pass

        class RecordingLock:
            def __init__(self) -> None:
                self.released = False

            def acquire(self, **_kwargs) -> bool:
                return True

            def release(self) -> None:
                self.released = True

        lock = RecordingLock()
        checks = iter((False, True))
        fake_mm = types.SimpleNamespace(
            processing_interrupted=lambda: next(checks),
            InterruptProcessingException=Interrupted,
        )
        with (
            mock.patch.object(module, "_cache_key_lock", return_value=lock),
            mock.patch.object(module, "_comfy_mm", fake_mm),
        ):
            with self.assertRaises(Interrupted):
                module._StageCacheTransaction().bind("cancel-after-lock")

        self.assertTrue(lock.released)
        self.assertNotIn("cancel-after-lock", module._STAGE_CACHE_PINNED_KEYS)

    def test_image_singleflight_waits_observe_comfy_interruption(self) -> None:
        module = self.module

        class Interrupted(RuntimeError):
            pass

        def fake_mm():
            checks = iter((False, True))
            return types.SimpleNamespace(
                processing_interrupted=lambda: next(checks),
                InterruptProcessingException=Interrupted,
            )

        follower = module._ImageReverseInFlight()
        with (
            mock.patch.object(module, "_comfy_mm", fake_mm()),
            mock.patch.object(module, "_COOPERATIVE_WAIT_POLL_SECONDS", 0.01),
        ):
            with self.assertRaises(Interrupted):
                module._wait_image_reverse_singleflight(
                    "follower-cancel",
                    follower,
                    wait_timeout=1.0,
                    stale_after=1.0,
                )

        blocker = module._ImageReverseInFlight()
        module._IMAGE_REVERSE_INFLIGHT.clear()
        module._IMAGE_REVERSE_INFLIGHT["busy"] = blocker
        try:
            with (
                mock.patch.object(module, "_comfy_mm", fake_mm()),
                mock.patch.object(module, "_COOPERATIVE_WAIT_POLL_SECONDS", 0.01),
            ):
                with self.assertRaises(Interrupted):
                    module._begin_image_reverse_singleflight(
                        "new-key",
                        wait_timeout=1.0,
                        stale_after=1.0,
                    )
        finally:
            module._IMAGE_REVERSE_INFLIGHT.clear()

    def test_singleflight_guard_cleans_leader_published_before_interrupt(self) -> None:
        module = self.module

        class InterruptingDict(dict):
            def __setitem__(self, key, value):
                super().__setitem__(key, value)
                raise KeyboardInterrupt("interrupt after publish")

        original = module._IMAGE_REVERSE_INFLIGHT
        flights = InterruptingDict()
        module._IMAGE_REVERSE_INFLIGHT = flights
        guard = module._ImageReverseSingleflightGuard("publish-interrupt")
        try:
            with self.assertRaisesRegex(KeyboardInterrupt, "after publish"):
                try:
                    guard.begin()
                finally:
                    guard.finish(error=KeyboardInterrupt("cleanup"))
        finally:
            module._IMAGE_REVERSE_INFLIGHT = original

        self.assertEqual(flights, {})
        self.assertIsNotNone(guard.flight)
        self.assertTrue(guard.flight.event.is_set())


class TestRuntimePreviewLimits(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_stage_prompt_generator_for_integration_test()

    def test_runtime_preview_bounds_inputs_and_does_not_echo_api_secrets(self) -> None:
        module = self.module
        result = module.构建运行时随机预览状态(
            {
                "unique_id": "node-" + ("x" * 1000),
                "selected": {"主体": [f"selected-{index}" for index in range(1000)]},
                "customTags": [f"custom-{index}" for index in range(1000)],
                "_randomDedupeCache": ["dedupe-a", "dedupe-b"],
                "settings": {
                    "运行时随机标签": False,
                    "额外要求": "r" * 100_000,
                    "API密钥": "top-secret",
                    "API额外请求头": "Authorization: top-secret",
                    "unknown_large_field": {"payload": "z" * 100_000},
                },
            }
        )

        settings = result["settings"]
        self.assertLessEqual(len(settings["额外要求"]), 32_768)
        self.assertLessEqual(len(settings["unique_id"]), 256)
        self.assertEqual(settings["随机补充避重缓存"], "dedupe-a,dedupe-b")
        self.assertNotIn("API密钥", settings)
        self.assertNotIn("API额外请求头", settings)
        self.assertNotIn("unknown_large_field", settings)
        self.assertLessEqual(len(result["customTags"]), 256)
        self.assertLessEqual(sum(len(item) for item in result["customTags"]), 32_768)
        self.assertLessEqual(len(result["selected"]["主体"]), 32)

        false_result = module.构建运行时随机预览状态(
            {"settings": {"运行时随机标签": "false"}}
        )
        self.assertFalse(false_result["settings"]["运行时随机标签"])
        self.assertEqual(false_result["settings"]["运行时随机预览令牌"], "")

    def test_real_widget_tag_collection_applies_limits_before_state_building(self) -> None:
        module = self.module
        selected, custom = module._collect_selected(
            {
                "主体标签1": {"invalid": "x" * 100_000},
                "自定义补充标签": ",".join(
                    f"tag-{index}-" + ("x" * 1000) for index in range(1000)
                ),
            }
        )
        self.assertEqual(selected["主体"], [])
        self.assertLessEqual(len(custom), 256)
        self.assertTrue(all(len(tag) <= 512 for tag in custom))

    def test_runtime_preview_marker_rejects_oversized_or_noncanonical_tokens(self) -> None:
        module = self.module

        def marker(token: str, source: str = "backend") -> str:
            return json.dumps(
                {
                    "v": 2,
                    "source": source,
                    "token": token,
                    "state_fingerprint": "a" * 64,
                }
            )

        self.assertIsNotNone(module._parse_runtime_random_preview_marker(marker("b" * 32)))
        self.assertIsNone(module._parse_runtime_random_preview_marker(marker("not-hex")))
        self.assertIsNone(module._parse_runtime_random_preview_marker(marker("b" * 33)))
        self.assertIsNone(module._parse_runtime_random_preview_marker(marker("b" * 32, "ui")))
        self.assertIsNone(
            module._parse_runtime_random_preview_marker(
                " " * (module._RUNTIME_RANDOM_PREVIEW_MARKER_MAX_CHARS + 1)
            )
        )

    def test_nsfw_custom_prefix_has_the_same_bound_in_preview_and_direct_mapping(self) -> None:
        module = self.module
        long_prefix = "prefix-" * 200
        preview = module.构建运行时随机预览状态(
            {
                "selected": {},
                "customTags": [],
                "settings": {"运行时随机标签": False},
                "nsfwWorkspace": {"enabled": True, "customPrefix": long_prefix},
            }
        )
        normalized_prefix = preview["nsfwWorkspace"]["custom_prefix"]
        self.assertEqual(len(normalized_prefix), 512)
        self.assertIn(normalized_prefix, preview["customTags"])

        selected = OrderedDict(
            (name, []) for name, _slots, _options in module._all_tag_groups()
        )
        direct = module.应用NSFW工作台到阶段状态(
            {"enabled": True, "customPrefix": long_prefix},
            selected=selected,
            custom_tags=[],
        )
        self.assertIn(normalized_prefix, direct["custom_tags"])
        self.assertTrue(all(len(tag) <= 512 for tag in direct["custom_tags"]))


class TestVideoInferenceLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.nodes, _fake_llama, _runtime = load_nodes_for_storage_test(
            pathlib.Path(cls.temp_dir.name)
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_video_ui_and_runtime_constants_cap_frames_and_edge(self) -> None:
        self.assertEqual(self.nodes._MAX_MULTIFRAME_INFERENCE_FRAMES, 64)
        self.assertEqual(self.nodes._MAX_IMAGE_INFERENCE_EDGE, 4096)
        for node_class in (self.nodes.QwenTE图像推理, self.nodes.Gemma4TE图像推理):
            required = node_class.INPUT_TYPES()["required"]
            self.assertEqual(required["最多帧数"][1]["max"], 64)
            self.assertEqual(required["最大边长"][1]["max"], 4096)

    def test_batch_encoder_rejects_more_than_sixty_four_frames(self) -> None:
        image_tensor = types.SimpleNamespace(shape=(65, 1, 1, 3))
        with self.assertRaisesRegex(ValueError, "最多处理 64 帧"):
            self.nodes._批量帧索引转data_url(image_tensor, list(range(65)), 512)

    def test_batch_encoder_clamps_edge_to_4096(self) -> None:
        class FakeTensor:
            shape = (1, 2, 2, 3)

            def __getitem__(self, _indices):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return np.zeros(self.shape, dtype=np.float32)

        captured_edges: list[int] = []
        with mock.patch.object(
            self.nodes,
            "_图片数组转base64",
            side_effect=lambda _image, edge: captured_edges.append(edge) or "encoded",
        ):
            result = self.nodes._批量帧索引转data_url(FakeTensor(), [0], 99999)

        self.assertEqual(captured_edges, [4096])
        self.assertEqual(result, {0: "data:image/jpeg;base64,encoded"})

    def test_image_array_is_downsampled_before_float_to_uint8_conversion(self) -> None:
        observed_sizes: list[tuple[int, int]] = []

        def observe_resize(pil_image, _edge):
            observed_sizes.append(pil_image.size)
            return pil_image

        image = np.zeros((80, 100, 3), dtype=np.float32)
        with mock.patch.object(
            self.nodes,
            "_缩放图片到最大边",
            side_effect=observe_resize,
        ):
            encoded = self.nodes._图片数组转base64(image, 10)

        self.assertTrue(encoded)
        self.assertEqual(observed_sizes, [(10, 8)])

    def test_float_image_pre_resize_uses_area_sampling(self) -> None:
        checker = (np.indices((4, 4)).sum(axis=0) % 2).astype(np.float32)
        image = np.repeat(checker[..., None], 3, axis=2)
        pixels: list[tuple[int, int, int]] = []

        def capture_pixel(pil_image):
            pixels.append(tuple(pil_image.getpixel((0, 0))))
            return "encoded"

        with mock.patch.object(
            self.nodes,
            "_编码PIL为JPEG_base64",
            side_effect=capture_pixel,
        ):
            encoded = self.nodes._图片数组转base64(image, 1)

        self.assertEqual(encoded, "encoded")
        self.assertTrue(all(126 <= channel <= 128 for channel in pixels[0]))

    def test_batch_encoder_applies_combined_pixel_budget_and_slices_one_frame_at_a_time(self) -> None:
        class FakeTensor:
            shape = (64, 2, 2, 3)

            def __init__(self) -> None:
                self.indices: list[object] = []

            def __getitem__(self, index):
                self.indices.append(index)
                return self

            def cpu(self):
                return self

            def numpy(self):
                return np.zeros((1, 2, 2, 3), dtype=np.float32)

        tensor = FakeTensor()
        captured_edges: list[int] = []
        with mock.patch.object(
            self.nodes,
            "_图片数组转base64",
            side_effect=lambda _image, edge: captured_edges.append(edge) or "encoded",
        ):
            result = self.nodes._批量帧索引转data_url(tensor, list(range(64)), 4096)

        self.assertEqual(len(result), 64)
        self.assertEqual(set(captured_edges), {1024})
        self.assertEqual(len(tensor.indices), 64)
        self.assertTrue(all(isinstance(index, slice) for index in tensor.indices))

    def test_batch_encoder_rejects_oversized_combined_data_url_payload(self) -> None:
        class FakeTensor:
            shape = (1, 2, 2, 3)

            def __getitem__(self, _index):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return np.zeros((1, 2, 2, 3), dtype=np.float32)

        with (
            mock.patch.object(self.nodes, "_MAX_MULTIFRAME_DATA_URL_BYTES", 20),
            mock.patch.object(self.nodes, "_图片数组转base64", return_value="encoded"),
        ):
            with self.assertRaisesRegex(ValueError, "编码载荷超过"):
                self.nodes._批量帧索引转data_url(FakeTensor(), [0], 512)

    def test_batch_encoder_does_not_retry_resource_runtime_errors(self) -> None:
        class FailingTensor:
            shape = (1, 2, 2, 3)

            def __getitem__(self, _index):
                return self

            def cpu(self):
                return self

            def numpy(self):
                raise RuntimeError("CUDA out of memory")

        with mock.patch.object(self.nodes, "_批量图片索引转base64") as fallback:
            with self.assertRaisesRegex(RuntimeError, "out of memory"):
                self.nodes._批量帧索引转data_url(FailingTensor(), [0], 512)
        fallback.assert_not_called()

    def test_cpu_video_paths_use_the_bounded_batch_encoder(self) -> None:
        image = types.SimpleNamespace(shape=(64, 1, 1, 3))
        encoded = {index: f"data:image/jpeg;base64,{index}" for index in range(64)}

        def run_qwen(model):
            return self.nodes.QwenTE图像推理().run(
                model, "视频", "describe", "", 64, 4096, 64,
                0.7, 0.9, 20, 1.0, 0.0, 0.0, 1, False, image,
            )

        def run_gemma(model):
            return self.nodes.Gemma4TE图像推理().run(
                model, "视频", "describe", "", 64, 4096, 64,
                1.0, 0.95, 64, 1, False, image,
            )

        for label, storage, runner in (
            ("qwen", self.nodes._QwenStorage, run_qwen),
            ("gemma", self.nodes._Gemma4Storage, run_gemma),
        ):
            with self.subTest(model=label):
                model = types.SimpleNamespace(llm=object(), chat_handler=object())
                with (
                    mock.patch.object(storage, "model", model),
                    mock.patch.object(
                        self.nodes,
                        "_批量帧索引转data_url",
                        return_value=encoded,
                    ) as batch_encoder,
                    mock.patch.object(
                        self.nodes,
                        "_批量图片索引转base64",
                    ) as unbounded_fallback,
                    mock.patch.object(
                        self.nodes,
                        "_调用chat_completion",
                        return_value={"choices": [{"message": {"content": "ok"}}]},
                    ),
                ):
                    self.assertEqual(runner(model), ("ok",))

                batch_encoder.assert_called_once()
                self.assertEqual(len(batch_encoder.call_args.args[1]), 64)
                self.assertEqual(batch_encoder.call_args.args[2], 1024)
                unbounded_fallback.assert_not_called()

    def test_batch_encoder_checks_interruption_between_frames(self) -> None:
        class Interrupted(RuntimeError):
            pass

        class FakeTensor:
            shape = (2, 2, 2, 3)

            def __getitem__(self, _indices):
                return self

            def cpu(self):
                return self

            def numpy(self):
                return np.zeros(self.shape, dtype=np.float32)

        checks = iter((False, True))
        encoded_frames: list[int] = []
        with (
            mock.patch.object(
                self.nodes.mm,
                "processing_interrupted",
                side_effect=lambda: next(checks),
            ),
            mock.patch.object(self.nodes.mm, "InterruptProcessingException", Interrupted),
            mock.patch.object(
                self.nodes,
                "_图片数组转base64",
                side_effect=lambda _image, _edge: encoded_frames.append(1) or "encoded",
            ),
        ):
            with self.assertRaises(Interrupted):
                self.nodes._批量帧索引转data_url(FakeTensor(), [0, 1], 512)

        self.assertEqual(encoded_frames, [1])

    def test_model_lock_wait_without_deadline_observes_interruption(self) -> None:
        class Interrupted(RuntimeError):
            pass

        lock_held = threading.Event()
        release_lock = threading.Event()

        def hold_lock() -> None:
            with self.nodes._MODEL_STORAGE_LOCK:
                lock_held.set()
                release_lock.wait(2.0)

        holder = threading.Thread(target=hold_lock)
        holder.start()
        self.assertTrue(lock_held.wait(1.0))
        checks = iter((False, True))
        started = time.monotonic()
        try:
            with (
                mock.patch.object(
                    self.nodes.mm,
                    "processing_interrupted",
                    side_effect=lambda: next(checks),
                ),
                mock.patch.object(self.nodes.mm, "InterruptProcessingException", Interrupted),
                mock.patch.object(self.nodes, "_MODEL_LOCK_WAIT_POLL_SECONDS", 0.01),
            ):
                with self.assertRaises(Interrupted):
                    self.nodes._合作获取模型存储锁(None)
        finally:
            release_lock.set()
            holder.join(1.0)

        self.assertLess(time.monotonic() - started, 0.5)
        self.assertFalse(holder.is_alive())

    def test_model_lock_is_released_when_cancel_arrives_after_acquire(self) -> None:
        class Interrupted(RuntimeError):
            pass

        class RecordingLock:
            def __init__(self) -> None:
                self.released = False

            def acquire(self, **_kwargs) -> bool:
                return True

            def release(self) -> None:
                self.released = True

        lock = RecordingLock()
        checks = iter((False, True))
        with (
            mock.patch.object(self.nodes, "_MODEL_STORAGE_LOCK", lock),
            mock.patch.object(
                self.nodes.mm,
                "processing_interrupted",
                side_effect=lambda: next(checks),
            ),
            mock.patch.object(self.nodes.mm, "InterruptProcessingException", Interrupted),
        ):
            with self.assertRaises(Interrupted):
                self.nodes._合作获取模型存储锁(None)

        self.assertTrue(lock.released)


if __name__ == "__main__":
    unittest.main()
