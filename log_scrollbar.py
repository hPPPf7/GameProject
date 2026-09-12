"""Shared log geometry for rendering, wheel, touch and scrollbar dragging."""
from dataclasses import dataclass
import pygame
import text_log
from ui_theme import AMBER


@dataclass
class LogViewport:
    text_rect: pygame.Rect
    text_width: int
    visible_lines: int
    maximum: int
    offset: int
    hit_area: pygame.Rect
    track: pygame.Rect
    thumb: pygame.Rect
    footer: pygame.Rect
    latest_button: pygame.Rect


def get_log_viewport(rect, font):
    # Reserve a stable gutter so revealing more text never changes wrapping.
    text_rect = rect.copy()
    text_rect.width -= 20
    width = max(1, text_rect.w - 16)
    # Always reserve one footer row; showing a prompt must not move the text.
    count = max(1, (rect.h - 40) // 24)
    total, maximum, offset = text_log.get_scroll_metrics(font, width, count)
    hit = pygame.Rect(rect.right - 22, rect.top + 8, 18, max(1, rect.h - 16))
    track = pygame.Rect(rect.right - 15, hit.top + 12, 6, max(1, hit.h - 24))
    thumb_height = min(track.h, max(24, round(track.h * min(1, count / max(1, total)))))
    travel = track.h - thumb_height
    top = track.y + (round(travel * (maximum - offset) / maximum) if maximum else 0)
    thumb = pygame.Rect(track.x - 1, top, 8, thumb_height)
    footer = pygame.Rect(rect.x + 8, rect.bottom - 30, max(1, rect.w - 36), 24)
    latest_button = pygame.Rect(footer.right - 132, footer.y, 132, footer.h)
    return LogViewport(text_rect, width, count, maximum, offset, hit, track, thumb, footer, latest_button)


def draw_log_scrollbar(surface, view, *, active=False, mouse_pos=None):
    if view.maximum == 0:
        return
    pygame.draw.rect(surface, (35, 46, 55), view.track)
    hovered = mouse_pos is not None and view.hit_area.collidepoint(mouse_pos)
    color = AMBER if active or hovered else (134, 153, 159)
    pygame.draw.rect(surface, color, view.thumb)
    x = view.track.centerx
    up_color = color if view.offset < view.maximum else (58, 72, 81)
    down_color = color if view.offset > 0 else (58, 72, 81)
    pygame.draw.lines(surface, up_color, False, [(x - 3, view.hit_area.y + 5), (x, view.hit_area.y + 2), (x + 3, view.hit_area.y + 5)], 1)
    pygame.draw.lines(surface, down_color, False, [(x - 3, view.hit_area.bottom - 6), (x, view.hit_area.bottom - 3), (x + 3, view.hit_area.bottom - 6)], 1)


class LogScrollbar:
    def __init__(self):
        self.cancel()

    def cancel(self):
        self.pointer = None
        self.grab_offset = None

    def begin(self, pos, view, font, pointer):
        if not view.maximum or not view.hit_area.collidepoint(pos):
            return False
        self.pointer = pointer
        self.grab_offset = None
        if view.thumb.top <= pos[1] < view.thumb.bottom:
            self.grab_offset = pos[1] - view.thumb.y
        else:
            if pos[1] < view.track.top:
                delta = 1
            elif pos[1] >= view.track.bottom:
                delta = -1
            else:
                delta = view.visible_lines if pos[1] < view.thumb.top else -view.visible_lines
            text_log.set_scroll_offset(view.offset + delta, font, view.text_width, view.visible_lines)
        return True

    def move(self, pos, view, font, pointer):
        if self.pointer != pointer:
            return False
        if self.grab_offset is not None and view.maximum:
            travel = max(1, view.track.h - view.thumb.h)
            ratio = max(0, min(1, (pos[1] - self.grab_offset - view.track.y) / travel))
            text_log.set_scroll_offset(round(view.maximum * (1 - ratio)), font, view.text_width, view.visible_lines)
        return True

    def release(self, pointer):
        if self.pointer != pointer:
            return False
        self.cancel()
        return True
