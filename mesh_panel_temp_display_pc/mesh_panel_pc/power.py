from __future__ import annotations

import logging
import os
import sys
import threading
from typing import Callable

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    LRESULT = ctypes.c_int64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = LRESULT
    user32.PostQuitMessage.argtypes = [ctypes.c_int]
    user32.PostQuitMessage.restype = None

    WM_POWERBROADCAST = 0x0218
    PBT_APMSUSPEND = 0x0004
    PBT_APMRESUMEAUTOMATIC = 0x0012
    PBT_APMRESUMESUSPEND = 0x0007
    WM_QUERYENDSESSION = 0x0011
    WM_ENDSESSION = 0x0016
    WM_CLOSE = 0x0010
    WM_DESTROY = 0x0002
    DEVICE_NOTIFY_WINDOW_HANDLE = 0


class WindowsPowerService:
    """Listens for Windows power management events (suspend, resume, shutdown)
    using a dedicated hidden top-level window and Win32 message loop.
    """

    def __init__(
        self,
        on_suspend: Callable[[], None] | None = None,
        on_resume: Callable[[], None] | None = None,
        on_shutdown: Callable[[], None] | None = None,
    ) -> None:
        self._on_suspend = on_suspend
        self._on_resume = on_resume
        self._on_shutdown = on_shutdown

        self._thread: threading.Thread | None = None
        self._hwnd: int | None = None
        self._h_notify: int | None = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()

        if sys.platform == "win32":
            self._class_name = f"MeshPanelPowerWindow_{os.getpid()}_{id(self)}"
            self._hinstance = kernel32.GetModuleHandleW(None)
            self._wndproc = WNDPROC(self._window_proc)

    def start(self) -> None:
        if sys.platform != "win32":
            return
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._ready_event.clear()
        self._thread = threading.Thread(target=self._run_message_loop, name="WindowsPowerService", daemon=True)
        self._thread.start()
        self._ready_event.wait(timeout=2.0)

    def stop(self) -> None:
        if sys.platform != "win32":
            return
        self._stop_event.set()
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._hwnd = None

    def _window_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == WM_POWERBROADCAST:
            if wparam == PBT_APMSUSPEND:
                self._dispatch(self._on_suspend, "suspend")
            elif wparam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND):
                self._dispatch(self._on_resume, "resume")
            return 1

        if msg in (WM_QUERYENDSESSION, WM_ENDSESSION):
            if wparam:
                self._dispatch(self._on_shutdown, "shutdown")
            return 1

        if msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0

        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _dispatch(self, callback: Callable[[], None] | None, name: str) -> None:
        if not callback:
            return
        try:
            callback()
        except Exception:
            logger.exception("Error executing power callback: %s", name)

    def _run_message_loop(self) -> None:
        class WNDCLASSW(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HANDLE),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        wc = WNDCLASSW()
        wc.lpfnWndProc = self._wndproc
        wc.hInstance = self._hinstance
        wc.lpszClassName = self._class_name

        if not user32.RegisterClassW(ctypes.byref(wc)):
            self._ready_event.set()
            return

        self._hwnd = user32.CreateWindowExW(
            0,
            self._class_name,
            "MeshPanelPowerWindow",
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            self._hinstance,
            None,
        )

        if not self._hwnd:
            user32.UnregisterClassW(self._class_name, self._hinstance)
            self._ready_event.set()
            return

        try:
            user32.RegisterSuspendResumeNotification.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            user32.RegisterSuspendResumeNotification.restype = wintypes.HANDLE
            self._h_notify = user32.RegisterSuspendResumeNotification(self._hwnd, DEVICE_NOTIFY_WINDOW_HANDLE)
        except Exception:
            self._h_notify = None

        self._ready_event.set()

        msg = wintypes.MSG()
        while not self._stop_event.is_set():
            ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if ret <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._h_notify:
            try:
                user32.UnregisterSuspendResumeNotification.argtypes = [wintypes.HANDLE]
                user32.UnregisterSuspendResumeNotification(self._h_notify)
            except Exception:
                pass
            self._h_notify = None

        user32.UnregisterClassW(self._class_name, self._hinstance)

