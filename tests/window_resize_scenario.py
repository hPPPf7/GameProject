"""Exercise real Win32 resize messages on an invisible SDL window."""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.update(SDL_VIDEODRIVER="windows", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")

import pygame
from window_resize import (
    WindowsAspectResize, _MinMaxInfo, WM_SIZING, WM_ENTERSIZEMOVE,
    WM_EXITSIZEMOVE, WM_GETMINMAXINFO,
)


def main():
    pygame.display.init()
    pygame.display.set_mode((512, 847), pygame.RESIZABLE | pygame.HIDDEN)
    hwnd = pygame.display.get_wm_info()["window"]
    resize = WindowsAspectResize((512, 847), (307, 508))
    assert resize.install(hwnd), resize.error
    assert resize.install(hwnd), "Installing twice should keep the same callback"
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
    user.SendMessageW.restype = ctypes.c_ssize_t
    user.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user.SetWindowPos.restype = wintypes.BOOL
    redraw_sizes = []

    def redraw():
        surface = pygame.display.get_surface()
        surface.fill((27, 63, 89))
        pygame.display.flip()
        redraw_sizes.append(surface.get_size())

    resize.on_resize = redraw
    try:
        frame_w, frame_h = resize._frame_size(hwnd)
        info = _MinMaxInfo()
        user.SendMessageW(hwnd, WM_GETMINMAXINFO, 0, ctypes.addressof(info))
        assert (info.min_track.x, info.min_track.y) == (307 + frame_w, 508 + frame_h)
        user.SendMessageW(hwnd, WM_ENTERSIZEMOVE, 0, 0)
        assert resize.active and resize.consume_pause()
        for edge in range(1, 9):
            for requested in ((650, 800), (100, 100), (511, 846), (513, 848)):
                rect = wintypes.RECT(50, 50, 50 + requested[0] + frame_w, 50 + requested[1] + frame_h)
                assert user.SendMessageW(hwnd, WM_SIZING, edge, ctypes.addressof(rect)) == 1
                width, height = rect.right - rect.left, rect.bottom - rect.top
                assert abs((width - frame_w) / 512 - (height - frame_h) / 847) < 1 / 512
                assert user.SetWindowPos(hwnd, None, rect.left, rect.top, width, height, 0x0014)
                pygame.event.pump()
                assert pygame.display.get_surface().get_size() == (width - frame_w, height - frame_h), (edge, requested, (frame_w, frame_h), (width - frame_w, height - frame_h), pygame.display.get_surface().get_size(), redraw_sizes)
                assert redraw_sizes[-1] == pygame.display.get_surface().get_size()
                assert resize.error is None, resize.error
        user.SendMessageW(hwnd, WM_EXITSIZEMOVE, 0, 0)
        assert not resize.active and resize.consume_pause()
        assert not resize.consume_pause(), "Resume pause should be consumed exactly once"
        resize.close()
        resize.close()
        assert not resize.installed
        assert resize.install(hwnd)
        pygame.quit()  # WM_NCDESTROY must release the hook before callback collection.
        assert not resize.installed
        print("PASS: native eight-handle resizing, minimum, redraw, pause and cleanup")
    finally:
        resize.close()
        pygame.quit()


if __name__ == "__main__":
    main()
