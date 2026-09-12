"""Transient UI feedback. None of these values enter a game save."""
from collections import Counter
import math
import pygame
from ui_theme import AMBER, RED


class UIFeedback:
    def __init__(self):
        self.hover = {}
        self.hover_targets = {}
        self.pressed_rect = None
        self.press_remaining = 0.0
        self.modal_progress = 0.0
        self.reset_player()

    def reset_player(self):
        self.reading_time = 0.0
        self.previous = None
        self.durability_delta = 0
        self.durability_time = 0.0
        self.item_times = {}
        self.pressed_rect = None
        self.press_remaining = 0.0

    def press(self, rect):
        self.pressed_rect = tuple(rect)
        self.press_remaining = .12

    def button_state(self, rect, *, enabled=True, hovered=False):
        key = tuple(rect)
        self.hover_targets[key] = bool(hovered and enabled)
        return (self.hover.get(key, 0.0) if enabled else 0.0,
                key == self.pressed_rect and self.press_remaining > 0)

    def update_ui(self, dt, modal_open):
        dt = max(0, min(dt, .1))
        self.press_remaining = max(0, self.press_remaining - dt)
        for key in set(self.hover) | set(self.hover_targets):
            target = float(self.hover_targets.get(key, False))
            value = self.hover.get(key, 0.0)
            step = dt / .10
            value = min(target, value + step) if target > value else max(target, value - step)
            if value:
                self.hover[key] = value
            else:
                self.hover.pop(key, None)
        self.hover_targets.clear()
        step = dt / (.14 if modal_open else .10)
        self.modal_progress = min(1, self.modal_progress + step) if modal_open else max(0, self.modal_progress - step)

    def update_player(self, dt):
        self.reading_time += dt
        self.durability_time = max(0, self.durability_time - dt)
        self.item_times = {i: t - dt for i, t in self.item_times.items() if t > dt}

    def observe(self, player):
        state = player.get('battle_state') or {}
        current = (state.get('event_id'), state.get('durability'), tuple(player.get('inventory', [])))
        if self.previous is not None:
            old_id, old_durability, old_items = self.previous
            if current[0] == old_id and isinstance(current[1], (int, float)) and isinstance(old_durability, (int, float)):
                if current[1] < old_durability:
                    self.durability_delta = current[1] - old_durability
                    self.durability_time = .75
            elif current[0] != old_id:
                self.durability_time = 0
            if current[2] != old_items:
                remaining = Counter(old_items)
                self.item_times.clear()
                for i, item in enumerate(current[2]):
                    if remaining[item]:
                        remaining[item] -= 1
                    else:
                        self.item_times[i] = .75
        self.previous = current

    def item_pulse(self, index, *, overflow=False):
        remaining = max((t for i, t in self.item_times.items() if i >= index), default=0) if overflow else self.item_times.get(index, 0)
        if remaining <= 0:
            return 0.0, 0
        elapsed = .75 - remaining
        bounce = round(3 * math.sin(math.pi * min(1, elapsed / .35)))
        return remaining / .75, -bounce

    def draw_durability(self, surface, rect, font):
        if self.durability_time <= 0:
            return
        elapsed = .75 - self.durability_time
        label = font.render(f'{self.durability_delta:+g}', True, RED)
        label.set_alpha(round(255 * min(1, self.durability_time / .25)))
        target = label.get_rect(midtop=(rect.centerx, rect.y + 55 - round(elapsed * 12)))
        surface.blit(label, target)


class CampfireAtmosphere:
    def __init__(self):
        self.time = 0.0
        # Build a faint, soft pool of light once. No gameplay RNG is consumed.
        self.glow = pygame.Surface((240, 240), pygame.SRCALPHA)
        for radius in range(116, 3, -4):
            alpha = round(9 * (1 - radius / 120) ** 1.4)
            pygame.draw.circle(self.glow, (255, 156, 55, alpha), (120, 120), radius)

    def update(self, dt):
        self.time += min(.1, max(0, dt))

    def draw(self, surface, background_rect):
        cx = background_rect.x + round(background_rect.w * .605)
        cy = background_rect.y + round(background_rect.h * .715)
        strength = .78 + .13 * math.sin(self.time * 2.3) + .09 * math.sin(self.time * 4.1)
        self.glow.set_alpha(round(255 * strength))
        surface.blit(self.glow, (cx - 120, cy - 120))
        for i in range(10):
            age = (self.time * (.25 + (i % 3) * .045) + i * .173) % 1
            x = cx + round(math.sin(i * 2.3) * 33 + math.sin(self.time * .7 + i) * age * 13)
            y = cy - 35 - round(age * 105)
            alpha = math.sin(math.pi * age) * .6
            color = tuple(round(a * alpha + b * (1 - alpha)) for a, b in zip(AMBER, (59, 45, 29)))
            size = 2 + (i % 3 == 0)
            pygame.draw.rect(surface, color, (x, y, size, size))
