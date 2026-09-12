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


def _button_shape(size):
    width, height = size[0] - 1, size[1] - 1
    cut = min(3, width // 4, height // 4)
    return [(cut, 0), (width - cut, 0), (width, cut),
            (width, height - cut), (width - cut, height), (cut, height),
            (0, height - cut), (0, cut)]


@lru_cache(maxsize=128)
def _button_material(size, kind, emphasis, pressed):
    """Matte material with broad lighting and fixed pixel grain, without an outline."""
    surface = pygame.Surface(size, pygame.SRCALPHA)
    width, height = size
    base = {'button': (49, 62, 72), 'selected': (74, 62, 44), 'disabled': (30, 39, 47)}[kind]
    base = mix(base, (111, 98, 75), emphasis / 6 * .42)
    if pressed:
        base = mix(base, (17, 25, 31), .12)
    light = 3 if kind == 'disabled' else 11
    for y in range(height):
        # Lighting covers the entire face; it is not an edge highlight.
        shade = round(light * (1 - 1.6 * y / max(1, height - 1)))
        color = tuple(max(0, min(255, value + shade)) for value in base)
        surface.fill(color, (0, y, width, 1))
    for y in range(2, height - 2, 3):
        for x in range(2, width - 2, 3):
            code = (x * 37 + y * 61 + x * y * 7) % 31
            if code > 8:
                continue
            delta = (2 if code < 4 else -2) if kind == 'disabled' else (6 if code < 4 else -5)
            color = tuple(max(0, min(255, value + delta)) for value in surface.get_at((x, y))[:3])
            surface.fill(color, (x, y, 2, 2))
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), _button_shape(size))
    surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return surface


def draw_button_face(surface, rect, *, hover=0, pressed=False, enabled=True, selected=False):
    """Return the label rectangle while keeping the original hit area fixed."""
    pressed = pressed and enabled
    depth = max(2, min(4, rect.h // 10)) if enabled else 2
    # A filled lower layer provides depth without drawing a stroked border.
    shadow = [(rect.x + x, rect.y + y) for x, y in _button_shape(rect.size)]
    pygame.draw.polygon(surface, (12, 20, 27), shadow)
    face = rect.copy()
    face.height = max(1, face.h - depth)
    if pressed:
        face.y += 1
    kind = 'disabled' if not enabled else 'selected' if selected else 'button'
    emphasis = max(hover, .45 if selected else 0) if enabled else 0
    surface.blit(_button_material(face.size, kind, max(0, min(6, round(emphasis * 6))), pressed), face)
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
