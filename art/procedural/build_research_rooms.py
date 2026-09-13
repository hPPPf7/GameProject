"""Build two small pixel interiors without external artwork (run from any cwd)."""
from pathlib import Path
import random

import pygame

OUTPUT = Path(__file__).resolve().parents[2] / "assets" / "background"
SIZE = (448, 299)


def rect(surface, color, box):
    pygame.draw.rect(surface, color, box)


def panel(surface, box, color=(50, 54, 48)):
    x, y, w, h = box
    rect(surface, (15, 21, 21), box)
    rect(surface, color, (x + 2, y + 2, w - 4, h - 4))
    rect(surface, (74, 77, 63), (x + 2, y + 2, w - 4, 2))
    for px in (x + 4, x + w - 6):
        for py in (y + 6, y + h - 8):
            rect(surface, (93, 89, 69), (px, py, 2, 2))


def screen(surface, box):
    x, y, w, h = box
    panel(surface, box, (35, 49, 45))
    rect(surface, (13, 36, 35), (x + 6, y + 6, w - 12, h - 12))
    rect(surface, (112, 180, 154), (x + 10, y + 10, w - 24, 2))
    for row in range(3):
        rect(surface, (66, 118, 102), (x + 10, y + 18 + row * 6, max(4, w - 28 - row * 8), 2))


def room(seed):
    surface = pygame.Surface(SIZE)
    surface.fill((34, 39, 37))
    # Back wall, two side walls, and a floor with a clear foreground for actors.
    rect(surface, (44, 49, 44), (62, 32, 324, 190))
    pygame.draw.polygon(surface, (25, 31, 30), ((0, 0), (62, 32), (62, 222), (0, 299)))
    pygame.draw.polygon(surface, (29, 34, 31), ((448, 0), (386, 32), (386, 222), (448, 299)))
    pygame.draw.polygon(surface, (23, 29, 28), ((0, 0), (448, 0), (386, 32), (62, 32)))
    pygame.draw.polygon(surface, (53, 51, 42), ((62, 222), (386, 222), (448, 299), (0, 299)))
    for x in range(66, 386, 40):
        rect(surface, (25, 33, 31), (x, 38, 2, 178))
        rect(surface, (60, 63, 53), (x + 2, 38, 2, 178))
    for y in (58, 118, 180, 218):
        rect(surface, (23, 31, 29), (62, y, 324, 2))
    for y in (232, 250, 272, 296):
        rect(surface, (28, 34, 29), (0, y, 448, 2))
        rect(surface, (68, 64, 50), (0, y + 2, 448, 2))
    for x in range(-160, 640, 80):
        pygame.draw.line(surface, (29, 34, 29), (224 + (x - 224) * .55, 222), (x, 299), 2)
    # Ceiling conduits and modest strips of warm light.
    for y in (14, 24):
        rect(surface, (13, 21, 21), (0, y, 448, 8))
        rect(surface, (66, 67, 54), (0, y, 448, 2))
    for x in (86, 308):
        panel(surface, (x, 42, 54, 12))
        rect(surface, (169, 175, 134), (x + 6, 46, 42, 4))
        rect(surface, (213, 218, 174), (x + 10, 46, 34, 2))
    for x in (40, 398):
        rect(surface, (15, 23, 23), (x, 32, 10, 210))
        rect(surface, (77, 75, 56), (x, 32, 2, 210))
        for y in (70, 156, 226):
            rect(surface, (63, 65, 50), (x - 2, y, 14, 4))
    return surface, random.Random(seed)


def finish(surface, rng):
    # Consistent two-pixel grain, using a private RNG unrelated to story choices.
    for y in range(0, SIZE[1], 2):
        for x in range(0, SIZE[0], 2):
            color = surface.get_at((x, y))
            grain = rng.choice((-4, -2, 0, 0, 2, 3))
            rect(surface, tuple(max(0, min(255, c + grain)) for c in color[:3]), (x, y, 2, 2))
    return surface


def corridor():
    surface, rng = room(724)
    # A recessed projection screen recalls the staff meeting described in the event.
    panel(surface, (128, 72, 160, 106), (40, 53, 47))
    rect(surface, (20, 43, 41), (136, 80, 144, 88))
    for y in range(84, 166, 6):
        rect(surface, (25, 52, 47), (138, y, 138, 2))
    for x, h in ((152, 25), (186, 32), (220, 26), (250, 30)):
        rect(surface, (51, 88, 75), (x, 130 - h, 10, 12))
        rect(surface, (44, 78, 67), (x - 4, 144 - h, 18, h - 2))
    rect(surface, (66, 103, 85), (144, 142, 126, 4))
    rect(surface, (35, 65, 57), (144, 146, 126, 10))
    # The inner passage looks into the building, never back out to the LAB facade.
    panel(surface, (320, 74, 60, 150), (57, 57, 46))
    rect(surface, (10, 21, 23), (328, 82, 44, 136))
    for offset in (0, 8, 16):
        pygame.draw.lines(surface, (32 + offset, 47 + offset, 43 + offset), False,
                          ((330 + offset//2, 214-offset), (330 + offset//2, 86+offset),
                           (368-offset//2, 86+offset), (368-offset//2, 214-offset)), 2)
    rect(surface, (104, 151, 117), (342, 88, 18, 2))
    panel(surface, (74, 174, 48, 48))
    screen(surface, (78, 180, 40, 28))
    rect(surface, (112, 105, 76), (80, 212, 30, 4))
    panel(surface, (166, 186, 90, 38))
    rect(surface, (18, 29, 28), (172, 194, 74, 6))
    for x in range(176, 244, 10):
        rect(surface, (96, 106, 79), (x, 208, 4, 2))
    return finish(surface, rng)


def archive():
    surface, rng = room(726)
    for x in (74, 280):
        panel(surface, (x, 68, 94, 156), (44, 51, 44))
        for y in (80, 124, 168):
            rect(surface, (13, 28, 27), (x + 8, y, 78, 34))
            for jar in range(3):
                px = x + 14 + jar * 24
                rect(surface, (66, 79, 61), (px, y + 4, 14, 4))
                rect(surface, (31, 64, 55), (px, y + 8, 14, 20))
                rect(surface, (89, 134, 109), (px + 2, y + 8, 2, 20))
                rect(surface, (45, 91, 75), (px + 4, y + 14, 8, 12))
                rect(surface, (110, 125, 86), (px + 6, y + 16, 4, 6))
                rect(surface, (112, 107, 78), (px + 2, y + 30, 10, 2))
            rect(surface, (76, 77, 57), (x + 6, y + 36, 82, 4))
    # A separate data terminal and abandoned notes identify the journal location.
    screen(surface, (188, 84, 72, 68))
    rect(surface, (48, 57, 45), (218, 152, 10, 24))
    panel(surface, (178, 178, 92, 12), (77, 74, 52))
    for x in (184, 256):
        rect(surface, (23, 31, 28), (x, 190, 8, 34))
        rect(surface, (62, 66, 48), (x, 190, 2, 34))
    rect(surface, (156, 143, 100), (186, 168, 24, 10))
    rect(surface, (81, 89, 69), (216, 168, 42, 10))
    for x in range(220, 254, 6):
        rect(surface, (127, 131, 99), (x, 170, 4, 2))
    return finish(surface, rng)


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, make in (("research_corridor.png", corridor), ("research_archive.png", archive)):
        pygame.image.save(make(), OUTPUT / name)
        print(OUTPUT / name)
