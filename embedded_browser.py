# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import atexit
import base64
import hashlib
import json
import math
import os
import secrets
import socket
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import aiohttp


EMBEDDED_BROWSER_MIN_WIDTH = 640
EMBEDDED_BROWSER_MAX_WIDTH = 1920
EMBEDDED_BROWSER_MIN_HEIGHT = 360
EMBEDDED_BROWSER_MAX_HEIGHT = 1080
EMBEDDED_BROWSER_DEFAULT_WIDTH = 1360
EMBEDDED_BROWSER_DEFAULT_HEIGHT = 760
EMBEDDED_BROWSER_FRAME_MAX_BYTES = 8 * 1024 * 1024
EMBEDDED_BROWSER_FRAME_JPEG_QUALITY = 76
EMBEDDED_BROWSER_FRAME_MIN_WIDTH = 480
EMBEDDED_BROWSER_FRAME_MIN_HEIGHT = 270
EMBEDDED_BROWSER_FRAME_MAX_WIDTH = 2880
EMBEDDED_BROWSER_FRAME_MAX_HEIGHT = 1620
EMBEDDED_BROWSER_FRAME_MAX_SCALE = 1.5
EMBEDDED_BROWSER_FRAME_CACHE_SECONDS = 0.055
EMBEDDED_BROWSER_TEXT_MAX_CHARS = 4096
EMBEDDED_BROWSER_SESSION_TTL_SECONDS = 20 * 60.0
EMBEDDED_BROWSER_EXPIRY_MIN_DELAY_SECONDS = 0.05
EMBEDDED_BROWSER_DEBUG_PORT_WAIT_SECONDS = 4.0
EMBEDDED_BROWSER_CDP_STARTUP_TIMEOUT_SECONDS = 4.0
EMBEDDED_BROWSER_DIAGNOSTIC_MAX_CHARS = 1600
EMBEDDED_BROWSER_PROFILE_CLEANUP_ATTEMPTS = 5

_EMBEDDED_BROWSER_SINGLE_PAGE_NAVIGATION_SCRIPT = r"""
(() => {
    if (window.__qwenTeSinglePageNavigationInstalled) return;
    window.__qwenTeSinglePageNavigationInstalled = true;
    const keepLinkInCurrentPage = (event) => {
        const target = event && event.target;
        const link = target && typeof target.closest === "function" ? target.closest("a[href]") : null;
        if (!link) return;
        if (String(link.getAttribute("target") || "").toLowerCase() === "_blank") {
            link.setAttribute("target", "_self");
        }
    };
    document.addEventListener("pointerdown", keepLinkInCurrentPage, true);
    document.addEventListener("click", keepLinkInCurrentPage, true);
    window.open = function(url) {
        if (url !== undefined && url !== null && String(url).trim()) {
            try {
                location.assign(new URL(String(url), location.href).href);
            } catch (_error) {}
        }
        return window;
    };
})();
""".strip()
EMBEDDED_BROWSER_START_MIN_INTERVAL_SECONDS = 1.0
EMBEDDED_BROWSER_STARTS_PER_MINUTE = 8


class EmbeddedBrowserError(RuntimeError):
    pass


class EmbeddedBrowserUnavailable(EmbeddedBrowserError):
    pass


class EmbeddedBrowserBusy(EmbeddedBrowserError):
    def __init__(self, message: str, retry_after: float = 1.0):
        super().__init__(message)
        self.retry_after = max(0.1, float(retry_after))


class EmbeddedBrowserSessionNotFound(EmbeddedBrowserError):
    pass


def normalize_embedded_browser_viewport(width: Any, height: Any) -> tuple[int, int]:
    try:
        normalized_width = int(width)
    except (TypeError, ValueError):
        normalized_width = EMBEDDED_BROWSER_DEFAULT_WIDTH
    try:
        normalized_height = int(height)
    except (TypeError, ValueError):
        normalized_height = EMBEDDED_BROWSER_DEFAULT_HEIGHT
    return (
        max(EMBEDDED_BROWSER_MIN_WIDTH, min(EMBEDDED_BROWSER_MAX_WIDTH, normalized_width)),
        max(EMBEDDED_BROWSER_MIN_HEIGHT, min(EMBEDDED_BROWSER_MAX_HEIGHT, normalized_height)),
    )


def normalize_embedded_browser_frame_size(
    width: Any,
    height: Any,
    *,
    viewport_width: int,
    viewport_height: int,
) -> tuple[int, int]:
    try:
        requested_width = int(width)
    except (TypeError, ValueError):
        requested_width = int(viewport_width)
    try:
        requested_height = int(height)
    except (TypeError, ValueError):
        requested_height = int(viewport_height)
    return (
        max(EMBEDDED_BROWSER_FRAME_MIN_WIDTH, min(EMBEDDED_BROWSER_FRAME_MAX_WIDTH, requested_width)),
        max(EMBEDDED_BROWSER_FRAME_MIN_HEIGHT, min(EMBEDDED_BROWSER_FRAME_MAX_HEIGHT, requested_height)),
    )

def normalize_embedded_browser_coordinate(value: Any, maximum: int) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise EmbeddedBrowserError("浏览器输入坐标无效。") from exc
    if not math.isfinite(number):
        raise EmbeddedBrowserError("浏览器输入坐标无效。")
    return max(0.0, min(float(max(0, int(maximum))), number))


def normalize_embedded_browser_integer(value: Any, minimum: int, maximum: int, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise EmbeddedBrowserError(f"Invalid embedded browser input field: {field_name}.") from exc
    return max(int(minimum), min(int(maximum), number))


def normalize_embedded_browser_number(value: Any, minimum: float, maximum: float, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise EmbeddedBrowserError(f"Invalid embedded browser input field: {field_name}.") from exc
    if not math.isfinite(number):
        raise EmbeddedBrowserError(f"Invalid embedded browser input field: {field_name}.")
    return max(float(minimum), min(float(maximum), number))


def embedded_browser_history_index(history: dict[str, Any]) -> int:
    try:
        return int(history.get("currentIndex", -1))
    except (TypeError, ValueError):
        return -1


_KEY_VIRTUAL_CODES = {
    "Backspace": 8,
    "Tab": 9,
    "Enter": 13,
    "Shift": 16,
    "Control": 17,
    "Alt": 18,
    "Pause": 19,
    "CapsLock": 20,
    "Escape": 27,
    " ": 32,
    "PageUp": 33,
    "PageDown": 34,
    "End": 35,
    "Home": 36,
    "ArrowLeft": 37,
    "ArrowUp": 38,
    "ArrowRight": 39,
    "ArrowDown": 40,
    "Insert": 45,
    "Delete": 46,
    "Meta": 91,
}


def embedded_browser_virtual_key_code(key: Any, code: Any = "") -> int:
    text = str(key or "")
    if text in _KEY_VIRTUAL_CODES:
        return _KEY_VIRTUAL_CODES[text]
    if len(text) == 1:
        character = text.upper()
        if "A" <= character <= "Z" or "0" <= character <= "9":
            return ord(character)
    code_text = str(code or "")
    if code_text.startswith("F") and code_text[1:].isdigit():
        number = int(code_text[1:])
        if 1 <= number <= 24:
            return 111 + number
    return 0


class _CdpConnection:
    def __init__(self, websocket: aiohttp.ClientWebSocketResponse):
        self._websocket = websocket
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._send_lock = asyncio.Lock()
        self._next_id = 0
        self._closed = False
        self._reader_task = asyncio.create_task(self._reader())

    async def _reader(self) -> None:
        failure: BaseException | None = None
        try:
            async for message in self._websocket:
                if message.type != aiohttp.WSMsgType.TEXT:
                    if message.type in {aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR}:
                        break
                    continue
                try:
                    payload = json.loads(message.data)
                except (TypeError, ValueError):
                    continue
                request_id = payload.get("id")
                if not isinstance(request_id, int):
                    continue
                future = self._pending.pop(request_id, None)
                if future is not None and not future.done():
                    future.set_result(payload)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            failure = exc
        finally:
            self._closed = True
            error = EmbeddedBrowserUnavailable(
                f"浏览器调试连接已关闭：{failure}" if failure else "浏览器调试连接已关闭。"
            )
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(error)
            self._pending.clear()

    async def call(self, method: str, params: dict[str, Any] | None = None, *, timeout: float = 15.0) -> dict[str, Any]:
        if self._closed or self._websocket.closed:
            raise EmbeddedBrowserUnavailable("浏览器调试连接不可用。")
        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        async with self._send_lock:
            self._next_id += 1
            request_id = self._next_id
            self._pending[request_id] = future
            try:
                await self._websocket.send_json({"id": request_id, "method": str(method), "params": dict(params or {})})
            except Exception:
                self._pending.pop(request_id, None)
                raise
        try:
            payload = await asyncio.wait_for(future, timeout=max(1.0, float(timeout)))
        finally:
            self._pending.pop(request_id, None)
        error = payload.get("error")
        if isinstance(error, dict):
            message = str(error.get("message") or "浏览器命令失败。").strip()
            raise EmbeddedBrowserError(f"{method}：{message[:300]}")
        result = payload.get("result")
        return result if isinstance(result, dict) else {}

    async def close(self) -> None:
        if not self._websocket.closed:
            await self._websocket.close()
        if self._reader_task is not asyncio.current_task() and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass


@dataclass
class _EmbeddedBrowserSession:
    session_id: str
    browser: str
    process: subprocess.Popen
    profile_directory: Path
    client: aiohttp.ClientSession
    connection: _CdpConnection
    width: int
    height: int
    created_at: float
    last_used_at: float
    frame_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_frame: bytes = b""
    last_frame_id: str = ""
    last_frame_captured_at: float = 0.0
    last_frame_size: tuple[int, int, int] = (0, 0, 0)
    expiry_handle: asyncio.TimerHandle | None = None


class EmbeddedBrowserManager:
    def __init__(
        self,
        *,
        executable_finder: Callable[[], tuple[Path | None, str, str]],
        profile_root: Path,
        process_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self._executable_finder = executable_finder
        self._profile_root = Path(profile_root)
        self._process_factory = process_factory
        self._monotonic = monotonic
        self._sessions: dict[str, _EmbeddedBrowserSession] = {}
        self._sessions_lock = asyncio.Lock()
        self._start_lock = asyncio.Lock()
        self._start_times: list[float] = []
        atexit.register(self.close_processes_sync)

    def _schedule_session_expiry(
        self,
        session: _EmbeddedBrowserSession,
        delay: float | None = None,
    ) -> None:
        existing = getattr(session, "expiry_handle", None)
        if existing is not None:
            existing.cancel()
        wait_seconds = EMBEDDED_BROWSER_SESSION_TTL_SECONDS if delay is None else float(delay)
        loop = asyncio.get_running_loop()
        handle: asyncio.TimerHandle | None = None

        def expire() -> None:
            if getattr(session, "expiry_handle", None) is handle:
                session.expiry_handle = None
            loop.create_task(self._expire_session_if_idle(session.session_id))

        handle = loop.call_later(
            max(EMBEDDED_BROWSER_EXPIRY_MIN_DELAY_SECONDS, wait_seconds),
            expire,
        )
        session.expiry_handle = handle

    async def _expire_session_if_idle(self, session_id: str) -> None:
        session_to_close: _EmbeddedBrowserSession | None = None
        async with self._sessions_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            remaining = EMBEDDED_BROWSER_SESSION_TTL_SECONDS - (
                self._monotonic() - session.last_used_at
            )
            if remaining > 0:
                self._schedule_session_expiry(session, remaining)
                return
            session_to_close = self._sessions.pop(session_id, None)
        if session_to_close is not None:
            await self._close_session(session_to_close)

    def _reserve_start(self) -> None:
        now = self._monotonic()
        self._start_times[:] = [stamp for stamp in self._start_times if now - stamp < 60.0]
        if self._start_times:
            elapsed = now - self._start_times[-1]
            if elapsed < EMBEDDED_BROWSER_START_MIN_INTERVAL_SECONDS:
                raise EmbeddedBrowserBusy("内嵌浏览器启动过于频繁，请稍后再试。", EMBEDDED_BROWSER_START_MIN_INTERVAL_SECONDS - elapsed)
        if len(self._start_times) >= EMBEDDED_BROWSER_STARTS_PER_MINUTE:
            retry_after = 60.0 - (now - self._start_times[0])
            raise EmbeddedBrowserBusy("内嵌浏览器启动次数过多，请稍后再试。", max(1.0, retry_after))
        self._start_times.append(now)

    def _build_arguments(self, executable: Path, profile: Path, width: int, height: int) -> list[str]:
        return self._build_arguments_with_port(executable, profile, width, height, 0)

    def _build_arguments_with_port(
        self,
        executable: Path,
        profile: Path,
        width: int,
        height: int,
        remote_debugging_port: int,
    ) -> list[str]:
        port = int(remote_debugging_port or 0)
        return [
            str(executable),
            "--headless=new",
            "--remote-debugging-address=127.0.0.1",
            f"--remote-debugging-port={port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--disable-component-update",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-background-media-suspend",
            "--metrics-recording-only",
            "--no-pings",
            "--disable-breakpad",
            "--disable-crash-reporter",
            f"--window-size={width},{height}",
            "about:blank",
        ]

    def _launch_process(
        self,
        executable: Path,
        profile: Path,
        width: int,
        height: int,
        remote_debugging_port: int = 0,
    ) -> subprocess.Popen:
        creation_flags = 0
        if os.name == "nt":
            creation_flags |= int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
            creation_flags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        log_handle = None
        try:
            log_path = profile / "browser.log"
            log_handle = log_path.open("ab")
            process = self._process_factory(
                self._build_arguments_with_port(
                    executable,
                    profile,
                    width,
                    height,
                    remote_debugging_port,
                ),
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=log_handle,
                close_fds=True,
                creationflags=creation_flags,
                cwd=str(executable.parent),
            )
            setattr(process, "_qwen_te_embedded_log_handle", log_handle)
            return process
        except OSError as exc:
            if log_handle is not None:
                log_handle.close()
            raise EmbeddedBrowserUnavailable("内嵌浏览器进程启动失败。") from exc

    @staticmethod
    def _read_diagnostic_tail(profile: Path) -> str:
        try:
            text = (profile / "browser.log").read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            return ""
        cleaned = " ".join(line.strip() for line in text.splitlines() if line.strip())
        return cleaned[-EMBEDDED_BROWSER_DIAGNOSTIC_MAX_CHARS:]

    @staticmethod
    def _reserve_debug_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    async def _debug_port_is_open(self, port: int) -> bool:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", int(port)),
                timeout=0.25,
            )
        except (OSError, asyncio.TimeoutError, ValueError):
            return False
        writer.close()
        try:
            await writer.wait_closed()
        except (OSError, RuntimeError):
            pass
        return True

    async def _wait_for_debug_port(
        self,
        process: subprocess.Popen,
        profile: Path,
        *,
        expected_port: int = 0,
        timeout: float = EMBEDDED_BROWSER_DEBUG_PORT_WAIT_SECONDS,
    ) -> int:
        port_file = profile / "DevToolsActivePort"
        deadline = self._monotonic() + max(2.0, float(timeout))
        while self._monotonic() < deadline:
            if process.poll() is not None:
                diagnostic = self._read_diagnostic_tail(profile)
                suffix = f" 启动日志：{diagnostic}" if diagnostic else ""
                raise EmbeddedBrowserUnavailable(f"内嵌浏览器启动后立即退出。{suffix}")
            try:
                lines = port_file.read_text(encoding="utf-8").splitlines()
            except (FileNotFoundError, OSError, UnicodeError):
                lines = []
            if lines:
                try:
                    port = int(lines[0])
                except (TypeError, ValueError):
                    port = 0
                if 1 <= port <= 65535:
                    return port
            if expected_port and await self._debug_port_is_open(expected_port):
                return int(expected_port)
            await asyncio.sleep(0.1)
        diagnostic = self._read_diagnostic_tail(profile)
        suffix = f" 启动日志：{diagnostic}" if diagnostic else ""
        raise EmbeddedBrowserUnavailable(
            f"浏览器未开放本机调试端口，等待超时。请检查 Edge 的远程调试策略或使用独立浏览器窗口。{suffix}"
        )

    async def _find_page_websocket(self, client: aiohttp.ClientSession, port: int) -> str:
        endpoint = f"http://127.0.0.1:{port}/json/list"
        for _attempt in range(30):
            try:
                async with client.get(endpoint) as response:
                    if response.status == 200:
                        payload = await response.json(content_type=None)
                        for item in payload if isinstance(payload, list) else []:
                            if isinstance(item, dict) and item.get("type") == "page" and item.get("webSocketDebuggerUrl"):
                                return str(item["webSocketDebuggerUrl"])
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                pass
            await asyncio.sleep(0.1)
        raise EmbeddedBrowserUnavailable("没有找到内嵌浏览器页面目标。")

    async def _configure_page(self, session: _EmbeddedBrowserSession) -> None:
        connection = session.connection
        startup_timeout = EMBEDDED_BROWSER_CDP_STARTUP_TIMEOUT_SECONDS
        try:
            await connection.call("Page.enable", timeout=startup_timeout)
            await connection.call("Runtime.enable", timeout=startup_timeout)
            await connection.call("Network.enable", timeout=startup_timeout)
            await connection.call(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": _EMBEDDED_BROWSER_SINGLE_PAGE_NAVIGATION_SCRIPT},
                timeout=startup_timeout,
            )
            await connection.call(
                "Runtime.evaluate",
                {"expression": _EMBEDDED_BROWSER_SINGLE_PAGE_NAVIGATION_SCRIPT},
                timeout=startup_timeout,
            )
            await self._set_device_metrics(session, session.width, session.height, timeout=startup_timeout)
            await connection.call(
                "Emulation.setFocusEmulationEnabled",
                {"enabled": True},
                timeout=startup_timeout,
            )
        except asyncio.TimeoutError as exc:
            raise EmbeddedBrowserUnavailable(
                "浏览器调试连接建立后没有响应，请使用独立浏览器窗口。"
            ) from exc
        try:
            await connection.call(
                "Browser.setDownloadBehavior",
                {"behavior": "deny"},
                timeout=startup_timeout,
            )
        except (EmbeddedBrowserError, asyncio.TimeoutError):
            pass

    @staticmethod
    async def _set_device_metrics(
        session: _EmbeddedBrowserSession,
        width: int,
        height: int,
        *,
        timeout: float = 15.0,
    ) -> None:
        await session.connection.call(
            "Emulation.setDeviceMetricsOverride",
            {
                "width": int(width),
                "height": int(height),
                "deviceScaleFactor": 1,
                "mobile": False,
                "screenWidth": int(width),
                "screenHeight": int(height),
            },
            timeout=timeout,
        )

    async def start(self, url: str, *, width: Any = None, height: Any = None) -> dict[str, Any]:
        normalized_width, normalized_height = normalize_embedded_browser_viewport(width, height)
        async with self._start_lock:
            self._reserve_start()
            await self.close_all()
            executable, family, error = self._executable_finder()
            if executable is None:
                raise EmbeddedBrowserUnavailable(error or "没有找到可用的 Edge/Chromium。")
            session_id = secrets.token_urlsafe(24)
            profile = (self._profile_root / "runtime" / session_id).resolve()
            profile.mkdir(parents=True, exist_ok=False)
            process: subprocess.Popen | None = None
            client: aiohttp.ClientSession | None = None
            connection: _CdpConnection | None = None
            try:
                requested_port = self._reserve_debug_port()
                process = self._launch_process(
                    executable,
                    profile,
                    normalized_width,
                    normalized_height,
                    requested_port,
                )
                port = await self._wait_for_debug_port(
                    process,
                    profile,
                    expected_port=requested_port,
                )
                client = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=20.0, connect=5.0, sock_connect=5.0, sock_read=20.0),
                    trust_env=False,
                )
                websocket_url = await self._find_page_websocket(client, port)
                websocket = await client.ws_connect(websocket_url, heartbeat=15.0, max_msg_size=20 * 1024 * 1024)
                connection = _CdpConnection(websocket)
                now = self._monotonic()
                session = _EmbeddedBrowserSession(
                    session_id=session_id,
                    browser=family or "Chromium",
                    process=process,
                    profile_directory=profile,
                    client=client,
                    connection=connection,
                    width=normalized_width,
                    height=normalized_height,
                    created_at=now,
                    last_used_at=now,
                )
                await self._configure_page(session)
                async with self._sessions_lock:
                    self._sessions[session_id] = session
                    self._schedule_session_expiry(session)
                await connection.call("Page.navigate", {"url": str(url)})
                return {
                    "session_id": session_id,
                    "browser": session.browser,
                    "width": session.width,
                    "height": session.height,
                    "url": str(url),
                }
            except Exception:
                async with self._sessions_lock:
                    self._sessions.pop(session_id, None)
                if connection is not None:
                    try:
                        await connection.close()
                    except Exception:
                        pass
                if client is not None and not client.closed:
                    await client.close()
                if process is not None:
                    await asyncio.to_thread(self._stop_process_sync, process)
                await self._remove_profile_directory(profile)
                raise

    async def _get_session(self, session_id: Any) -> _EmbeddedBrowserSession:
        key = str(session_id or "").strip()
        if not key or len(key) > 128:
            raise EmbeddedBrowserSessionNotFound("内嵌浏览器会话无效或已关闭。")
        async with self._sessions_lock:
            session = self._sessions.get(key)
        if session is None:
            raise EmbeddedBrowserSessionNotFound("内嵌浏览器会话无效或已关闭。")
        now = self._monotonic()
        if now - session.last_used_at > EMBEDDED_BROWSER_SESSION_TTL_SECONDS:
            await self.close(key)
            raise EmbeddedBrowserSessionNotFound("内嵌浏览器会话已超时。")
        if session.process.poll() is not None:
            await self.close(key)
            raise EmbeddedBrowserUnavailable("内嵌浏览器进程已经退出。")
        session.last_used_at = now
        return session

    async def status(self, session_id: Any) -> dict[str, Any]:
        session = await self._get_session(session_id)
        evaluated = await session.connection.call(
            "Runtime.evaluate",
            {
                "expression": (
                    "(()=>{const videos=Array.from(document.querySelectorAll('video'));"
                    "return {url:String(location.href),title:String(document.title),"
                    "readyState:String(document.readyState),mediaActive:videos.some((video)=>"
                    "!video.paused&&!video.ended&&video.readyState>=2&&video.offsetWidth>0&&video.offsetHeight>0),"
                    "videoCount:videos.length};})()"
                ),
                "returnByValue": True,
            },
        )
        value = ((evaluated.get("result") or {}).get("value") or {}) if isinstance(evaluated, dict) else {}
        history = await session.connection.call("Page.getNavigationHistory")
        entries = history.get("entries") if isinstance(history.get("entries"), list) else []
        current_index = embedded_browser_history_index(history)
        return {
            "session_id": session.session_id,
            "browser": session.browser,
            "width": session.width,
            "height": session.height,
            "url": str(value.get("url") or ""),
            "title": str(value.get("title") or "")[:300],
            "ready_state": str(value.get("readyState") or ""),
            "media_active": bool(value.get("mediaActive", False)),
            "video_count": max(0, int(value.get("videoCount", 0) or 0)),
            "can_go_back": current_index > 0,
            "can_go_forward": current_index >= 0 and current_index < len(entries) - 1,
        }

    async def navigate(self, session_id: Any, url: str) -> dict[str, Any]:
        session = await self._get_session(session_id)
        session.last_frame_captured_at = 0.0
        await session.connection.call("Page.navigate", {"url": str(url)})
        return await self.status(session.session_id)

    async def resize(self, session_id: Any, width: Any, height: Any) -> dict[str, Any]:
        session = await self._get_session(session_id)
        normalized_width, normalized_height = normalize_embedded_browser_viewport(width, height)
        if (normalized_width, normalized_height) != (session.width, session.height):
            async with session.frame_lock:
                await self._set_device_metrics(session, normalized_width, normalized_height)
                session.width = normalized_width
                session.height = normalized_height
                session.last_frame = b""
                session.last_frame_id = ""
                session.last_frame_captured_at = 0.0
                session.last_frame_size = (0, 0, 0)
        return await self.status(session.session_id)

    async def command(self, session_id: Any, action: Any) -> dict[str, Any]:
        session = await self._get_session(session_id)
        command = str(action or "").strip().lower()
        if command == "reload":
            await session.connection.call("Page.reload", {"ignoreCache": False})
        elif command == "stop":
            await session.connection.call("Page.stopLoading")
        elif command in {"back", "forward"}:
            history = await session.connection.call("Page.getNavigationHistory")
            entries = history.get("entries") if isinstance(history.get("entries"), list) else []
            current_index = embedded_browser_history_index(history)
            target_index = current_index + (-1 if command == "back" else 1)
            if 0 <= target_index < len(entries):
                entry_id = entries[target_index].get("id") if isinstance(entries[target_index], dict) else None
                if entry_id is not None:
                    await session.connection.call("Page.navigateToHistoryEntry", {"entryId": int(entry_id)})
        else:
            raise EmbeddedBrowserError("不支持的浏览器导航命令。")
        session.last_frame_captured_at = 0.0
        return await self.status(session.session_id)

    async def capture_frame(
        self,
        session_id: Any,
        previous_frame_id: Any = "",
        max_width: Any = None,
        max_height: Any = None,
        quality: Any = None,
    ) -> tuple[bytes | None, str]:
        session = await self._get_session(session_id)
        previous_id = str(previous_frame_id or "").strip()[:128]
        frame_width, frame_height = normalize_embedded_browser_frame_size(
            max_width,
            max_height,
            viewport_width=session.width,
            viewport_height=session.height,
        )
        try:
            frame_quality = int(quality)
        except (TypeError, ValueError):
            frame_quality = EMBEDDED_BROWSER_FRAME_JPEG_QUALITY
        frame_quality = max(40, min(92, frame_quality))
        frame_size_key = (frame_width, frame_height, frame_quality)
        async with session.frame_lock:
            now = self._monotonic()
            cached_frame = bytes(getattr(session, "last_frame", b"") or b"")
            cached_id = str(getattr(session, "last_frame_id", "") or "")
            cached_at = float(getattr(session, "last_frame_captured_at", 0.0) or 0.0)
            if (
                cached_frame
                and cached_id
                and getattr(session, "last_frame_size", (0, 0, 0)) == frame_size_key
                and now - cached_at < EMBEDDED_BROWSER_FRAME_CACHE_SECONDS
            ):
                return (None if previous_id == cached_id else cached_frame), cached_id
            scale = min(
                EMBEDDED_BROWSER_FRAME_MAX_SCALE,
                frame_width / float(session.width),
                frame_height / float(session.height),
            )
            scale = max(0.1, scale)
            result = await session.connection.call(
                "Page.captureScreenshot",
                {
                    "format": "jpeg",
                    "quality": frame_quality,
                    "fromSurface": True,
                    "captureBeyondViewport": False,
                    "optimizeForSpeed": True,
                    "clip": {
                        "x": 0,
                        "y": 0,
                        "width": session.width,
                        "height": session.height,
                        "scale": scale,
                    },
                },
                timeout=20.0,
            )
            encoded = str(result.get("data") or "")
            if not encoded:
                raise EmbeddedBrowserError("内嵌浏览器没有返回画面。")
            try:
                frame = base64.b64decode(encoded, validate=True)
            except (TypeError, ValueError) as exc:
                raise EmbeddedBrowserError("内嵌浏览器画面数据无效。") from exc
            if not frame or len(frame) > EMBEDDED_BROWSER_FRAME_MAX_BYTES:
                raise EmbeddedBrowserError("内嵌浏览器画面超过大小限制。")
            frame_id = hashlib.blake2s(frame, digest_size=12).hexdigest()
            session.last_frame = frame
            session.last_frame_id = frame_id
            session.last_frame_captured_at = now
            session.last_frame_size = frame_size_key
        return (None if previous_id == frame_id else frame), frame_id

    async def dispatch_input(self, session_id: Any, payload: dict[str, Any]) -> None:
        session = await self._get_session(session_id)
        input_type = str(payload.get("type") or "").strip()
        connection = session.connection
        if input_type in {"mouseDown", "mouseUp", "mouseMove"}:
            cdp_event_type = {
                "mouseDown": "mousePressed",
                "mouseUp": "mouseReleased",
                "mouseMove": "mouseMoved",
            }[input_type]
            x = normalize_embedded_browser_coordinate(payload.get("x"), session.width)
            y = normalize_embedded_browser_coordinate(payload.get("y"), session.height)
            button = str(payload.get("button") or "left")
            if button not in {"none", "left", "middle", "right", "back", "forward"}:
                button = "left"
            params = {
                "type": cdp_event_type,
                "x": x,
                "y": y,
                "button": button,
                "buttons": normalize_embedded_browser_integer(payload.get("buttons", 0) or 0, 0, 31, "buttons"),
                "clickCount": normalize_embedded_browser_integer(
                    payload.get("click_count", 1) or 1,
                    0,
                    3,
                    "click_count",
                ),
                "modifiers": normalize_embedded_browser_integer(
                    payload.get("modifiers", 0) or 0,
                    0,
                    15,
                    "modifiers",
                ),
            }
            await connection.call("Input.dispatchMouseEvent", params)
            session.last_frame_captured_at = 0.0
            return
        if input_type == "mouseWheel":
            await connection.call(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseWheel",
                    "x": normalize_embedded_browser_coordinate(payload.get("x"), session.width),
                    "y": normalize_embedded_browser_coordinate(payload.get("y"), session.height),
                    "deltaX": normalize_embedded_browser_number(
                        payload.get("delta_x", 0) or 0,
                        -2400.0,
                        2400.0,
                        "delta_x",
                    ),
                    "deltaY": normalize_embedded_browser_number(
                        payload.get("delta_y", 0) or 0,
                        -2400.0,
                        2400.0,
                        "delta_y",
                    ),
                    "modifiers": normalize_embedded_browser_integer(
                        payload.get("modifiers", 0) or 0,
                        0,
                        15,
                        "modifiers",
                    ),
                },
            )
            session.last_frame_captured_at = 0.0
            return
        if input_type == "text":
            text = str(payload.get("text") or "")
            if not text or len(text) > EMBEDDED_BROWSER_TEXT_MAX_CHARS:
                raise EmbeddedBrowserError("浏览器文本输入为空或过长。")
            await connection.call("Input.insertText", {"text": text})
            session.last_frame_captured_at = 0.0
            return
        if input_type == "key":
            key = str(payload.get("key") or "")[:32]
            code = str(payload.get("code") or "")[:64]
            if not key:
                raise EmbeddedBrowserError("浏览器按键为空。")
            modifiers = normalize_embedded_browser_integer(
                payload.get("modifiers", 0) or 0,
                0,
                15,
                "modifiers",
            )
            virtual_key = embedded_browser_virtual_key_code(key, code)
            common = {
                "key": key,
                "code": code,
                "modifiers": modifiers,
                "windowsVirtualKeyCode": virtual_key,
                "nativeVirtualKeyCode": virtual_key,
            }
            await connection.call("Input.dispatchKeyEvent", {"type": "keyDown", **common})
            await connection.call("Input.dispatchKeyEvent", {"type": "keyUp", **common})
            session.last_frame_captured_at = 0.0
            return
        raise EmbeddedBrowserError("不支持的浏览器输入类型。")

    async def close(self, session_id: Any) -> bool:
        key = str(session_id or "").strip()
        async with self._sessions_lock:
            session = self._sessions.pop(key, None)
        if session is None:
            return False
        await self._close_session(session)
        return True

    async def close_all(self) -> None:
        async with self._sessions_lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            await self._close_session(session)

    async def _close_session(self, session: _EmbeddedBrowserSession) -> None:
        expiry_handle = getattr(session, "expiry_handle", None)
        if expiry_handle is not None:
            expiry_handle.cancel()
            session.expiry_handle = None
        try:
            await session.connection.close()
        except Exception:
            pass
        if not session.client.closed:
            try:
                await session.client.close()
            except Exception:
                pass
        await asyncio.to_thread(self._stop_process_sync, session.process)
        await self._remove_profile_directory(session.profile_directory)

    @staticmethod
    async def _remove_profile_directory(profile_directory: Path) -> None:
        profile = Path(profile_directory)
        for attempt in range(EMBEDDED_BROWSER_PROFILE_CLEANUP_ATTEMPTS):
            await asyncio.to_thread(shutil.rmtree, profile, True)
            if not profile.exists():
                return
            await asyncio.sleep(0.12 * (attempt + 1))

    @staticmethod
    def _stop_process_sync(process: subprocess.Popen) -> None:
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2.0)
        except Exception:
            pass
        log_handle = getattr(process, "_qwen_te_embedded_log_handle", None)
        if log_handle is not None:
            try:
                log_handle.close()
            except Exception:
                pass

    def close_processes_sync(self) -> None:
        for session in list(self._sessions.values()):
            self._stop_process_sync(session.process)
