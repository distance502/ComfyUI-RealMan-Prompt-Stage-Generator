from __future__ import annotations

import base64
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from embedded_browser import (
    EmbeddedBrowserError,
    EmbeddedBrowserManager,
    embedded_browser_history_index,
    embedded_browser_virtual_key_code,
    normalize_embedded_browser_coordinate,
    normalize_embedded_browser_viewport,
)


class _RecordingConnection:
    def __init__(self):
        self.calls = []
        self.responses = {}

    async def call(self, method, params=None, **_kwargs):
        self.calls.append((method, params or {}))
        return dict(self.responses.get(method, {}))


class _RunningProcess:
    def poll(self):
        return None


class EmbeddedBrowserHelperTests(unittest.TestCase):
    def test_viewport_and_coordinates_are_bounded(self):
        self.assertEqual(normalize_embedded_browser_viewport(1, 99999), (640, 1000))
        self.assertEqual(normalize_embedded_browser_viewport("bad", None), (1360, 760))
        self.assertEqual(normalize_embedded_browser_coordinate(-2, 1360), 0.0)
        self.assertEqual(normalize_embedded_browser_coordinate(2000, 1360), 1360.0)
        with self.assertRaises(EmbeddedBrowserError):
            normalize_embedded_browser_coordinate(math.nan, 1360)

    def test_history_index_preserves_zero_and_key_codes_are_stable(self):
        self.assertEqual(embedded_browser_history_index({"currentIndex": 0}), 0)
        self.assertEqual(embedded_browser_history_index({"currentIndex": "2"}), 2)
        self.assertEqual(embedded_browser_history_index({"currentIndex": "bad"}), -1)
        self.assertEqual(embedded_browser_virtual_key_code("a"), 65)
        self.assertEqual(embedded_browser_virtual_key_code("Enter"), 13)
        self.assertEqual(embedded_browser_virtual_key_code("", "F12"), 123)

    def test_launch_arguments_keep_debugging_loopback_and_security_defaults(self):
        manager = EmbeddedBrowserManager(
            executable_finder=lambda: (None, "", ""),
            profile_root=Path("browser-profile"),
        )
        arguments = manager._build_arguments(
            Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
            Path("browser-profile/runtime/session"),
            1360,
            760,
        )
        joined = " ".join(arguments)
        self.assertIn("--headless=new", arguments)
        self.assertIn("--remote-debugging-address=127.0.0.1", arguments)
        self.assertIn("--remote-debugging-port=0", arguments)
        self.assertIn("--window-size=1360,760", arguments)
        self.assertNotIn("--no-sandbox", joined)
        self.assertNotIn("--disable-web-security", joined)

    def test_page_configuration_keeps_blank_links_in_the_current_embedded_page(self):
        async def run():
            connection = _RecordingConnection()
            manager = EmbeddedBrowserManager(
                executable_finder=lambda: (None, "", ""),
                profile_root=Path("browser-profile"),
            )
            await manager._configure_page(SimpleNamespace(connection=connection, width=1360, height=760))
            scripts = [
                params.get("source") or params.get("expression") or ""
                for method, params in connection.calls
                if method in {"Page.addScriptToEvaluateOnNewDocument", "Runtime.evaluate"}
            ]
            self.assertEqual(len(scripts), 2)
            self.assertTrue(all('target", "_self"' in script for script in scripts))
            self.assertTrue(all("window.open = function" in script for script in scripts))

        import asyncio
        asyncio.run(run())


class EmbeddedBrowserInputTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.connection = _RecordingConnection()
        self.manager = EmbeddedBrowserManager(
            executable_finder=lambda: (None, "", ""),
            profile_root=Path("browser-profile"),
            monotonic=lambda: 10.0,
        )
        self.manager._sessions["session"] = SimpleNamespace(
            session_id="session",
            process=_RunningProcess(),
            last_used_at=10.0,
            width=1360,
            height=760,
            connection=self.connection,
            frame_lock=__import__("asyncio").Lock(),
            last_frame=b"",
            last_frame_id="",
            last_frame_captured_at=0.0,
        )

    async def test_mouse_events_are_mapped_to_cdp_names(self):
        await self.manager.dispatch_input(
            "session",
            {
                "type": "mouseDown",
                "x": 120,
                "y": 240,
                "button": "left",
                "buttons": 1,
                "click_count": 1,
                "modifiers": 0,
            },
        )
        method, params = self.connection.calls[-1]
        self.assertEqual(method, "Input.dispatchMouseEvent")
        self.assertEqual(params["type"], "mousePressed")
        self.assertEqual(params["x"], 120.0)
        self.assertEqual(params["y"], 240.0)

    async def test_frame_cache_returns_unchanged_without_recapturing(self):
        frame = b"jpeg-frame-content"
        self.connection.responses["Page.captureScreenshot"] = {
            "data": base64.b64encode(frame).decode("ascii"),
        }
        first, frame_id = await self.manager.capture_frame("session")
        second, second_id = await self.manager.capture_frame("session", frame_id)
        captures = [method for method, _params in self.connection.calls if method == "Page.captureScreenshot"]
        self.assertEqual(first, frame)
        self.assertIsNone(second)
        self.assertEqual(second_id, frame_id)
        self.assertEqual(len(captures), 1)

    async def test_mouse_input_invalidates_frame_throttle(self):
        session = self.manager._sessions["session"]
        session.last_frame_captured_at = 9.9
        await self.manager.dispatch_input(
            "session",
            {"type": "mouseUp", "x": 80, "y": 40, "button": "left", "buttons": 0},
        )
        self.assertEqual(session.last_frame_captured_at, 0.0)

    async def test_invalid_numeric_input_is_rejected_as_browser_error(self):
        with self.assertRaises(EmbeddedBrowserError):
            await self.manager.dispatch_input(
                "session",
                {
                    "type": "mouseWheel",
                    "x": 10,
                    "y": 10,
                    "delta_x": "not-a-number",
                    "delta_y": 1,
                },
            )
        with self.assertRaises(EmbeddedBrowserError):
            await self.manager.dispatch_input(
                "session",
                {
                    "type": "key",
                    "key": "Enter",
                    "code": "Enter",
                    "modifiers": "bad",
                },
            )


if __name__ == "__main__":
    unittest.main()
