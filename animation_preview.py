"""Continuous movement/attack preview using the same actor as the game."""
import pygame


class AnimationSequencePreview:
    def __init__(self, sheet, *, smooth=True):
        pygame.font.init()
        from player_animation import PlayerAnimator
        key = {"player_walk.png": "walk", "player_attack.png": "attack"}.get(sheet.path.name)
        overrides = {key: sheet} if key else {}
        self.actor = PlayerAnimator(sound_enabled=False, smooth_scaling=smooth, sheet_overrides=overrides)
        self.actor.idle_x = 24
        self.actor.base_y = 30
        self.actor.reset()
        self.wait = 0.0
        self.surface_size = (320, 150)

    @property
    def label(self):
        return {"idle": "待機", "attack_approach": "接近", "attacking": "攻擊", "attack_return": "後跳"}[self.actor.state]

    def update(self, dt):
        dt = min(dt, .1)
        self.actor.update(dt)
        if self.actor.state == "idle":
            self.wait += dt
            if self.wait >= .8:
                self.actor.start_attack(enemy_width=40, enemy_position=(255, 30))
                self.wait = 0.0

    def render(self, font):
        surface = pygame.Surface(self.surface_size)
        surface.fill((25, 36, 47))
        pygame.draw.line(surface, (83, 125, 119), (8, 122), (312, 122))
        pygame.draw.line(surface, (150, 110, 75), (255, 52), (255, 122), 3)
        label = font.render(self.label, True, (225, 235, 240))
        surface.blit(label, (10, 7))
        frame = self.actor.current_frame()
        if frame is not None:
            surface.blit(frame, self.actor.position)
        return surface
