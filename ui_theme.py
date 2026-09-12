"""Cached pixel panels; textures stay fixed instead of flickering each frame."""
from functools import lru_cache
import pygame

BACKGROUND = (16, 23, 30)
TEXT = (232, 231, 219)
MUTED = (139, 151, 158)
AMBER = (220, 180, 110)
RED = (244, 145, 133)


def mix(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


@lru_cache(maxsize=64)
def _panel(size, kind, emphasis):
    surface = pygame.Surface(size)
    rect = surface.get_rect()
    base = {
        'log': (21, 29, 36), 'panel': (30, 39, 47),
        'slot': (23, 31, 38), 'button': (43, 51, 57),
        'disabled': (29, 36, 43), 'selected': (63, 55, 43),
    }[kind]
    if emphasis:
        base = mix(base, (86, 77, 59), emphasis / 6 * .4)
    surface.fill(base)
    if kind != 'log':
        # Integer coordinates and a fixed pattern preserve the pixel texture.
        for y in range(4, rect.h - 3, 4):
            for x in range(4, rect.w - 3, 4):
                code = (x * 17 + y * 31) % 29
                if code < 3:
                    surface.set_at((x, y), tuple(v + 3 for v in base))
                elif code == 6:
                    surface.set_at((x, y), tuple(v - 2 for v in base))
    return surface


def draw_panel(surface, rect, *, kind='panel', emphasis=0):
    surface.blit(_panel(rect.size, kind, max(0, min(6, round(emphasis * 6)))), rect)


def draw_button_face(surface, rect, *, hover=0, pressed=False, enabled=True, selected=False):
    """Return the label rectangle while keeping the original hit area fixed."""
    face = rect.copy()
    if pressed:
        face.y += 1
    kind = 'disabled' if not enabled else 'selected' if selected else 'button'
    draw_panel(surface, face, kind=kind, emphasis=max(hover, .45 if selected and enabled else 0))
    return face


def shake_scene(surface, area, offset):
    """Move only scene pixels, extending edge pixels into the revealed strips."""
    dx, dy = offset
    if not (dx or dy):
        return
    source = surface.subsurface(area).copy()
    previous_clip = surface.get_clip()
    surface.set_clip(area.clip(previous_clip))
    surface.blit(source, area.move(dx, dy))
    if dx:
        strip = pygame.Rect(area.left if dx > 0 else area.right + dx, area.top, abs(dx), area.h)
        edge = source.subsurface((0 if dx > 0 else area.w - 1, 0, 1, area.h))
        surface.blit(pygame.transform.scale(edge, strip.size), strip)
    if dy:
        strip = pygame.Rect(area.left, area.top if dy > 0 else area.bottom + dy, area.w, abs(dy))
        edge = source.subsurface((0, 0 if dy > 0 else area.h - 1, area.w, 1))
        surface.blit(pygame.transform.scale(edge, strip.size), strip)
    surface.set_clip(previous_clip)
