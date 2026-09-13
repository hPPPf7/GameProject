"""Keep desktop drag resizing proportional without recreating the SDL window."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import sys
from typing import Callable, Optional


LEFT, RIGHT, TOP, TOPLEFT, TOPRIGHT, BOTTOM, BOTTOMLEFT, BOTTOMRIGHT = range(1, 9)
WM_GETMINMAXINFO = 0x0024
WM_SIZE = 0x0005
WM_NCDESTROY = 0x0082
WM_SIZING = 0x0214
WM_ENTERSIZEMOVE = 0x0231
WM_EXITSIZEMOVE = 0x0232


def proportional_size(size, base_size, minimum_size, axis=None, maximum_size=None) -> tuple[int, int]:
    """Project a requested client size onto the game's aspect ratio."""
    width, height = size
    base_w, base_h = base_size
    if axis == "width":
        scale = width / base_w
    elif axis == "height":
        scale = height / base_h
    else:
        # At corners, keep the constrained corner as close to the pointer as possible.
        scale = (width * base_w + height * base_h) / (base_w**2 + base_h**2)
    scale = max(scale, minimum_size[0] / base_w, minimum_size[1] / base_h)
    if maximum_size:
        scale = min(scale, maximum_size[0] / base_w, maximum_size[1] / base_h)
    return max(1, round(base_w * scale)), max(1, round(base_h * scale))


def constrain_drag_rect(rect, edge, base_size, minimum_size, frame_size=(0, 0), maximum_size=None):
    """Constrain an outer window rectangle, anchoring the opposite corner/edge."""
    left, top, right, bottom = rect
    if edge not in range(1, 9):
        return tuple(rect)
    frame_w, frame_h = frame_size
    axis = "width" if edge in (LEFT, RIGHT) else "height" if edge in (TOP, BOTTOM) else None
    width, height = proportional_size(
        (right - left - frame_w, bottom - top - frame_h), base_size, minimum_size, axis, maximum_size,
    )
    width += frame_w
    height += frame_h
    if edge in (TOP, BOTTOM):
        left = round((left + right - width) / 2)
        right = left + width
    elif edge in (LEFT, TOPLEFT, BOTTOMLEFT):
        left = right - width
    else:
        right = left + width
    if edge in (LEFT, RIGHT):
        top = round((top + bottom - height) / 2)
        bottom = top + height
    elif edge in (TOP, TOPLEFT, TOPRIGHT):
        top = bottom - height
    else:
        bottom = top + height
    return left, top, right, bottom


class _MinMaxInfo(ctypes.Structure):
    _fields_ = [(name, wintypes.POINT) for name in (
        "reserved", "max_size", "max_position", "min_track", "max_track",
    )]


class WindowsAspectResize:
    """Constrain WM_SIZING before Windows commits each drag rectangle.

    Install and remove on SDL's window thread. Keep the callback alive until
    WM_NCDESTROY or close(); all unrelated messages continue through SDL.
    https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-sizing
    https://learn.microsoft.com/en-us/windows/win32/api/commctrl/nf-commctrl-setwindowsubclass
    """

    def __init__(self, base_size, minimum_size):
        self.base_size = base_size
        self.minimum_size = minimum_size
        self.hwnd = None
        self.active = False
        self._pause_elapsed = False
        self._callback = None
        self._subclass_id = id(self)
        self._maximum_size = None
        self.on_resize: Optional[Callable[[], None]] = None
        self.error = None

    @property
    def installed(self):
        return self.hwnd is not None

    def install(self, hwnd) -> bool:
        if sys.platform != "win32" or not hwnd:
            return False
        if self.installed:
            return self.hwnd == hwnd
        try:
            self._user = ctypes.WinDLL("user32", use_last_error=True)
            self._comctl = ctypes.WinDLL("comctl32", use_last_error=True)
            callback_type = ctypes.WINFUNCTYPE(
                ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT,
                ctypes.c_size_t, ctypes.c_ssize_t, ctypes.c_size_t, ctypes.c_size_t,
            )
            self._callback = callback_type(self._dispatch)
            self._comctl.SetWindowSubclass.argtypes = [wintypes.HWND, callback_type, ctypes.c_size_t, ctypes.c_size_t]
            self._comctl.SetWindowSubclass.restype = wintypes.BOOL
            self._comctl.RemoveWindowSubclass.argtypes = [wintypes.HWND, callback_type, ctypes.c_size_t]
            self._comctl.RemoveWindowSubclass.restype = wintypes.BOOL
            self._comctl.DefSubclassProc.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
            self._comctl.DefSubclassProc.restype = ctypes.c_ssize_t
            for name in ("GetWindowRect", "GetClientRect"):
                function = getattr(self._user, name)
                function.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
                function.restype = wintypes.BOOL
            self._user.GetSystemMetrics.argtypes = [ctypes.c_int]
            self._user.GetSystemMetrics.restype = ctypes.c_int
            if not self._comctl.SetWindowSubclass(hwnd, self._callback, self._subclass_id, 0):
                return False
            self.hwnd = hwnd
            frame_w, frame_h = self._frame_size(hwnd)
            # Start with the system tracking bounds; subsequent WM_GETMINMAXINFO
            # messages can refine them for the current display/window style.
            self._maximum_size = (
                max(1, self._user.GetSystemMetrics(59) - frame_w),
                max(1, self._user.GetSystemMetrics(60) - frame_h),
            )
            return True
        except (OSError, AttributeError) as exc:
            self.error = str(exc)
            return False

    def _frame_size(self, hwnd):
        outer, client = wintypes.RECT(), wintypes.RECT()
        if not (self._user.GetWindowRect(hwnd, ctypes.byref(outer))
                and self._user.GetClientRect(hwnd, ctypes.byref(client))):
            return 0, 0
        return (max(0, outer.right - outer.left - client.right + client.left),
                max(0, outer.bottom - outer.top - client.bottom + client.top))

    def _dispatch(self, hwnd, message, wparam, lparam, subclass_id, ref_data):
        forwarded = False
        result = 0
        try:
            if message == WM_SIZING and lparam:
                rect = ctypes.cast(lparam, ctypes.POINTER(wintypes.RECT)).contents
                adjusted = constrain_drag_rect(
                    (rect.left, rect.top, rect.right, rect.bottom), wparam,
                    self.base_size, self.minimum_size, self._frame_size(hwnd), self._maximum_size,
                )
                rect.left, rect.top, rect.right, rect.bottom = adjusted
                self._pause_elapsed = True
                return 1
            if message == WM_ENTERSIZEMOVE:
                self.active = True
                self._pause_elapsed = True
            elif message == WM_EXITSIZEMOVE:
                self.active = False
                self._pause_elapsed = True
            elif message == WM_NCDESTROY:
                self.close()
            result = self._comctl.DefSubclassProc(hwnd, message, wparam, lparam)
            forwarded = True
            if message == WM_GETMINMAXINFO and lparam:
                info = ctypes.cast(lparam, ctypes.POINTER(_MinMaxInfo)).contents
                frame_w, frame_h = self._frame_size(hwnd)
                info.min_track.x = self.minimum_size[0] + frame_w
                info.min_track.y = self.minimum_size[1] + frame_h
                if info.max_track.x > frame_w and info.max_track.y > frame_h:
                    self._maximum_size = (info.max_track.x - frame_w, info.max_track.y - frame_h)
            elif message == WM_SIZE and self.active and self.on_resize:
                self.on_resize()
            return result
        except Exception as exc:
            # Exceptions must not escape a native callback or lose SDL's message handling.
            if self.error is None:
                logging.getLogger(__name__).exception("Window resize callback failed")
            self.error = str(exc)
            return result if forwarded else self._comctl.DefSubclassProc(hwnd, message, wparam, lparam)

    def consume_pause(self) -> bool:
        paused = self._pause_elapsed or self.active
        self._pause_elapsed = False
        return paused

    def close(self):
        if self.hwnd is not None:
            self._comctl.RemoveWindowSubclass(self.hwnd, self._callback, self._subclass_id)
            self.hwnd = None
        self.active = False
