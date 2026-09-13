"""Small scene props drawn with pixels, using existing story state."""
from functools import lru_cache
import math

import pygame


def can_enter_research(background_name, player) -> bool:
    return (background_name == "bg024.png"
            and bool(player.get("flags", {}).get("visited_outpost")))


def research_door_target(area) -> tuple[int, int]:
    """The door threshold, shared by the light overlay and character movement."""
    return area.x + round(area.w * .438), area.y + round(area.h * .744)


@lru_cache(maxsize=4)
def _stone_frame(brightness: int) -> pygame.Surface:
    """Cache four stepped light levels; the stone itself stays on the ground."""
    frame = pygame.Surface((40, 32), pygame.SRCALPHA)
    # Low, angular light on the grass, with a contact shadow beneath the stone.
    glow = (255, 202, 105, 14 + brightness * 6)
    pygame.draw.rect(frame, glow, (6, 18, 28, 8))
    pygame.draw.rect(frame, glow, (10, 14, 20, 4))
    pygame.draw.rect(frame, glow, (10, 26, 20, 2))
    pygame.draw.rect(frame, (29, 43, 26, 150), (12, 24, 16, 2))
    pygame.draw.rect(frame, (61, 62, 45), (14, 20, 12, 4))
    pygame.draw.rect(frame, (108, 101, 69), (16, 18, 8, 4))
    pygame.draw.rect(frame, (161, 144, 91), (18, 16, 4, 2))
    light = (211 + brightness * 12, 172 + brightness * 19, 98 + brightness * 37)
    pygame.draw.rect(frame, light, (18, 18, 4, 4))
    if brightness == 3:
        # A brief two-pixel glint, without a large floating quest marker.
        pygame.draw.rect(frame, (255, 244, 195), (20, 10, 2, 8))
        pygame.draw.rect(frame, (255, 244, 195), (18, 12, 6, 2))
    return frame


def _draw_stone(surface, area, player, elapsed):
    # The pickup flag changes immediately; inventory supports older saves.
    if (player.get("flags", {}).get("got_weird_rock")
            or "奇怪的石頭" in player.get("inventory", [])):
        return
    brightness = round((.5 + .5 * math.sin(elapsed * math.tau / 2.8)) * 3)
    frame = _stone_frame(brightness)
    x = area.x + round(area.w * .58)
    y = area.bottom - 26
    surface.blit(frame, (x - 20, y - 24))


@lru_cache(maxsize=12)
def _spark_frame(shape: int, phase: int) -> pygame.Surface:
    frame = pygame.Surface((32, 24), pygame.SRCALPHA)
    paths = (
        ((4, 16), (10, 16), (10, 12), (16, 12), (16, 8), (24, 8)),
        ((4, 8), (10, 8), (10, 12), (18, 12), (18, 16), (26, 16)),
        ((6, 16), (12, 16), (12, 10), (20, 10), (20, 6), (26, 6)),
        ((4, 12), (10, 12), (10, 6), (18, 6), (18, 12), (26, 12)),
    )
    path = paths[shape]
    if phase == 0:
        path = path[:4]
    opacity = (170, 235, 100)[phase]
    # A muted blue edge keeps tiny sparks legible against the bright grass.
    pygame.draw.lines(frame, (27, 89, 107, opacity), False, path, 4)
    pygame.draw.lines(frame, (185, 238, 246, opacity), False, path, 2)
    if phase == 1:
        for x, y in ((8, 4), (24, 20)):
            pygame.draw.rect(frame, (218, 251, 255, 220), (x, y, 2, 2))
    return frame


def _draw_static_grass(surface, area, elapsed):
    # Authored offsets keep the effect sparse and never consume the story RNG.
    for index, (x, y, delay) in enumerate((
        (.43, .74, 0.0), (.67, .84, .95),
        (.85, .67, 2.1), (.48, .92, 2.85),
    )):
        age = (elapsed - delay) % 3.8
        if age >= .32:
            continue
        frame = _spark_frame(index, min(2, int(age * 3 / .32)))
        surface.blit(frame, (area.x + round(area.w * x) - 16,
                             area.y + round(area.h * y) - 12))


@lru_cache(maxsize=4)
def _door_overlay(size, unlocked: bool) -> pygame.Surface:
    overlay = pygame.Surface(size, pygame.SRCALPHA)
    width, height = size
    # These anchors align with the seam and masonry in bg024.png.
    x, bottom = research_door_target(overlay.get_rect())
    top = round(height * .416)
    if unlocked:
        ground = min(height - 1, bottom + 30)
        pygame.draw.polygon(overlay, (246, 211, 138, 22), (
            (x - 2, bottom), (x + 2, bottom), (x + 26, ground), (x - 26, ground),
        ))
        pygame.draw.polygon(overlay, (255, 226, 163, 30), (
            (x - 2, bottom), (x + 2, bottom), (x + 14, ground - 6), (x - 14, ground - 6),
        ))
        pygame.draw.rect(overlay, (245, 197, 110, 24), (x - 5, top, 10, bottom - top))
        pygame.draw.rect(overlay, (244, 208, 141, 135), (x - 2, top + 2, 4, bottom - top - 2))
        pygame.draw.rect(overlay, (255, 235, 186, 175), (x, top + 4, 2, bottom - top - 4))

    panel_x, panel_y = round(width * .565), round(height * .54)
    pygame.draw.rect(overlay, (18, 24, 24), (panel_x, panel_y, 12, 18))
    pygame.draw.rect(overlay, (44, 49, 45), (panel_x, panel_y, 12, 2))
    lamp = (115, 191, 138) if unlocked else (184, 78, 65)
    pygame.draw.rect(overlay, lamp, (panel_x + 4, panel_y + 4, 4, 4))
    pygame.draw.rect(overlay, (74, 79, 70), (panel_x + 3, panel_y + 12, 6, 2))
    return overlay


def draw_scene_details(surface, area, background_name, player, elapsed=0.0):
    """Draw only the current background's details, including result reading/walking.

    The caller supplies the paused gameplay clock and clips to the scene area.
    Existing story flags determine persistent changes; effects need no save data.
    """
    if background_name == "bg007.png":
        _draw_stone(surface, area, player, elapsed)
    elif background_name == "bg020.png":
        _draw_static_grass(surface, area, elapsed)
    elif background_name == "bg024.png":
        unlocked = bool(player.get("flags", {}).get("visited_outpost"))
        surface.blit(_door_overlay(area.size, unlocked), area.topleft)
