"""Small combat effects drawn from existing sprites, without extra assets."""
import math
import pygame


SHAKE_LABELS = {"off": "關閉", "weak": "輕微", "normal": "標準"}


class CombatFeedback:
    def __init__(self, shake_level="weak"):
        self.set_shake_level(shake_level)
        self.reset()

    def set_shake_level(self, level):
        self.shake_level = level if isinstance(level, str) and level in SHAKE_LABELS else "weak"

    def camera_offset(self):
        duration = .18 if self.kind == "victory" else .14
        if self.shake_level == "off" or self.kind is None or self.elapsed >= duration:
            return (0, 0)
        amplitude = {"victory": 5, "hurt": 3, "blocked": 2}.get(self.kind, 0)
        if self.shake_level == "weak":
            amplitude *= .6
        amplitude *= (1 - self.elapsed / duration)
        x = round(amplitude * math.cos(self.elapsed * 105))
        y = round(amplitude * .5 * math.sin(self.elapsed * 130))
        return x, y

    def reset(self):
        self.kind = None
        self.elapsed = 0.0
        self.freeze_remaining = 0.0

    def start(self, kind: str):
        self.kind = kind
        self.elapsed = 0.0
        self.freeze_remaining = 0.045

    def update(self, dt: float) -> float:
        """Return animation time after consuming the brief impact pause."""
        self.elapsed += dt
        pause = min(dt, self.freeze_remaining)
        self.freeze_remaining -= pause
        if self.kind != "victory" and self.elapsed > 0.6:
            self.kind = None
        return max(0.0, dt - pause)

    def sprite(self, frame, target: str):
        affected = "player" if self.kind == "hurt" else "enemy"
        if frame is None or self.kind is None or target != affected:
            return frame, (0, 0)
        result = frame
        if self.kind in ("victory", "hurt") and self.elapsed < 0.10:
            result = frame.copy()
            result.fill((150, 150, 150, 0), special_flags=pygame.BLEND_RGBA_ADD)
        if self.kind == "victory":
            if result is frame:
                result = frame.copy()
            result.set_alpha(round(255 * max(0.0, 1 - max(0, self.elapsed - .1) / .4)))
        direction = -1 if target == "player" else 1
        recoil = round(5 * math.sin(math.pi * min(1, self.elapsed / .25)))
        return result, (direction * recoil, 0)

    def draw(self, surface, area, font, player_pos, enemy_pos, player_frame, enemy_frame):
        if self.kind is None or self.elapsed > .55:
            return
        target_frame = player_frame if self.kind == "hurt" else enemy_frame
        target_pos = player_pos if self.kind == "hurt" else enemy_pos
        if target_frame is None or target_pos is None:
            return
        bounds = target_frame.get_bounding_rect(min_alpha=128)
        text, color = {
            "victory": ("擊倒！", (255, 222, 130)),
            "blocked": ("未奏效", (215, 225, 245)),
            "hurt": ("受擊", (255, 155, 145)),
        }[self.kind]
        label = font.render(text, True, color)
        x = target_pos[0] + bounds.centerx
        y = target_pos[1] + bounds.top - 18 - round(self.elapsed * 14)
        rect = label.get_rect(midbottom=(x, y)).clamp(area.inflate(-8, -8))
        pygame.draw.rect(surface, (28, 30, 40), rect.inflate(8, 4), border_radius=3)
        surface.blit(label, rect)
