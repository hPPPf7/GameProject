"""Player animation; main.py uses 2D, with the Blender prototype retained for reuse."""

from typing import Optional
import math

import pygame

from paths import res_path
from sprite_sheet import SpriteSheet
import sound_manager
from ui_manager import UI_AREAS

STYLE_LABELS = {"2d": "2D 原版", "3d": "3D 風格"}


# 簡易的玩家動畫控制器
class PlayerAnimator:
    def __init__(self, target_height: int = 96, style: str = "2d", *,
                 sound_enabled: bool = True, smooth_scaling: bool = True,
                 sheet_overrides: Optional[dict[str, SpriteSheet]] = None):
        self.target_height = target_height
        self.sound_enabled = sound_enabled
        self.smooth_scaling = smooth_scaling
        self.sheet_overrides = sheet_overrides or {}
        self.attack_hit = False
        self.style = "2d"
        self.pending_style: Optional[str] = None
        self.style_locked = False
        self.idle_frames = self._load_idle_frames()
        self.walk_frames = self._load_walk_frames()
        self.attack_frames = self._load_attack_frames()
        self.idle_frame_time = 0.35
        self.walk_frame_time = 1.0 / self.walk_fps
        self.attack_frame_time = 1.0 / self.attack_fps
        self.attack_hit_frame = self.attack_2d_hit_frame
        self._style_cache = {"2d": (
            self.idle_frames, self.walk_frames, self.attack_frames,
            self.idle_frame_time, self.walk_frame_time, self.attack_frame_time,
        )}
        self.walk_duration = 1.2
        self.stride_distance = target_height * 1.25
        self.attack_approach_duration = 0.35
        self.attack_return_duration = 0.3
        self.attack_target_x = 0.0
        self.attack_start_x = 0.0
        self.attack_return_start_x = 0.0
        self.attack_gap = 0
        self.attack_sfx_played = False
        self.frame_index = 0
        self.frame_timer = 0.0
        self.state = "idle"
        self.walk_progress = 0.0
        self.walk_finished = False
        self.attack_finished = True
        self.fade_state: Optional[str] = None
        self.fade_timer = 0.0
        self.fade_duration = 0.45
        self.fade_alpha = 0
        self.walk_start_x = UI_AREAS["image"].x + 16
        self.idle_x = UI_AREAS["image"].x + 32
        self.base_y = UI_AREAS["image"].bottom - self.target_height - 16
        first_walk_frame = self.walk_frames[0] if self.walk_frames else None
        walk_width = (
            first_walk_frame.get_width() if first_walk_frame else self.target_height
        )
        self.walk_end_x = max(
            self.walk_start_x,
            UI_AREAS["image"].right - walk_width - 16,
        )
        self.position = [self.idle_x, self.base_y]
        self.entry_start = (0.0, 0.0)
        self.entry_target = (0.0, 0.0)
        self.entry_scale = 1.0
        self._entry_frames = {}
        self.request_style(style if isinstance(style, str) and style in STYLE_LABELS else "2d")

    @property
    def movement_speed(self) -> float:
        return self.stride_distance * self.walk_fps / max(1, len(self.walk_frames))

    def reset(self) -> None:
        """Reset transient playback when starting or loading an adventure."""
        self.state = "idle"
        self.frame_index = 0
        self.frame_timer = 0.0
        self.walk_progress = 0.0
        self.walk_finished = False
        self.attack_finished = False
        self.attack_hit = False
        self.attack_sfx_played = False
        self.fade_state = None
        self.fade_timer = 0.0
        self.fade_alpha = 0
        self.pending_style = None
        self.entry_scale = 1.0
        self._entry_frames.clear()
        self.position[:] = [self.idle_x, self.base_y]

    @property
    def selected_style(self) -> str:
        return self.pending_style or self.style

    def request_style(self, style: str) -> None:
        """Queue a visual change without cancelling movement or combat results."""
        if style not in STYLE_LABELS:
            raise ValueError(f"Unknown character style: {style}")
        if style not in self._style_cache:
            clips = []
            times = []
            for clip in ("idle", "walk", "attack"):
                sheet = SpriteSheet.load(res_path("assets", "characters", "rookie_3d", f"{clip}.png"))
                frames = []
                for number in sheet.settings.frame_order:
                    frame = sheet.frame(number)
                    if frame.get_height() != self.target_height:
                        size = (round(frame.get_width() * self.target_height / frame.get_height()), self.target_height)
                        frame = pygame.transform.scale(frame, size)
                    frames.append(frame)
                clips.append(frames)
                times.append(1.0 / sheet.settings.fps)
            self._style_cache[style] = (*clips, *times)
        self.pending_style = style if style != self.style else None
        self._apply_pending_style()

    def _apply_pending_style(self) -> None:
        if not self.pending_style or self.style_locked or self.state != "idle" or self.fade_state:
            return
        self.style = self.pending_style
        self.pending_style = None
        (
            self.idle_frames, self.walk_frames, self.attack_frames,
            self.idle_frame_time, self.walk_frame_time, self.attack_frame_time,
        ) = self._style_cache[self.style]
        self.walk_fps = 1.0 / self.walk_frame_time
        self.attack_fps = 1.0 / self.attack_frame_time
        self.attack_hit_frame = 6 if self.style == "3d" else self.attack_2d_hit_frame
        self.walk_end_x = max(self.walk_start_x, UI_AREAS["image"].right - self.walk_frames[0].get_width() - 16)
        self.frame_index = 0
        self.frame_timer = 0.0
        self.position[:] = [self.idle_x, self.base_y]

    def _scale_to_height(self, surface: pygame.Surface) -> pygame.Surface:
        width = surface.get_width()
        height = surface.get_height()
        if height == 0:
            return surface
        ratio = self.target_height / height
        scale = pygame.transform.smoothscale if self.smooth_scaling else pygame.transform.scale
        scaled = scale(
            surface, (int(width * ratio), self.target_height)
        )
        return scaled

    def _slice_sheet(self, sheet: pygame.Surface, columns: int, rows: int):
        frame_w = sheet.get_width() // columns
        frame_h = sheet.get_height() // rows
        frames: list[pygame.Surface] = []
        for row in range(rows):
            for col in range(columns):
                frame_rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                frame_surface = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
                frame_surface.blit(sheet, (0, 0), frame_rect)
                frames.append(self._scale_to_height(frame_surface))
        return frames

    def _load_idle_frames(self) -> list[pygame.Surface]:
        idle_sheet = pygame.image.load(
            res_path("assets", "images", "player", "idle", "idle.png")
        )
        # idle 圖只有兩格，直接左右切成 2 張
        return self._slice_sheet(idle_sheet, columns=2, rows=1)

    def _load_walk_frames(self) -> list[pygame.Surface]:
        walk_sheet = self.sheet_overrides.get("walk") or SpriteSheet.load(
            res_path("assets", "sprite_sheet", "player_walk.png")
        )
        self.walk_fps = walk_sheet.settings.fps
        return walk_sheet.scaled_frames(self.target_height, smooth=self.smooth_scaling)

    def _load_attack_frames(self) -> list[pygame.Surface]:
        attack_sheet = self.sheet_overrides.get("attack") or SpriteSheet.load(
            res_path("assets", "sprite_sheet", "player_attack.png"), columns=3, rows=3
        )
        self.attack_fps = attack_sheet.settings.fps
        # Source frame 5 is the extended sword pose, independent of playback order.
        order = attack_sheet.settings.frame_order
        self.attack_2d_hit_frame = order.index(5) if 5 in order else 0
        return attack_sheet.scaled_frames(self.target_height, smooth=self.smooth_scaling)

    def start_walk(self):
        if not self.walk_frames:
            self.walk_finished = True
            self.state = "idle"
            return
        self.state = "walking"
        self.walk_duration = abs(self.walk_end_x - self.walk_start_x) / self.movement_speed
        self.walk_progress = 0.0
        self.frame_index = 0
        self.frame_timer = 0.0
        self.walk_finished = False
        self.fade_state = None
        self.fade_alpha = 0
        self.position[0] = self.walk_start_x

    def start_transition_fade(self):
        self.state = "idle"
        self.walk_progress = 0.0
        self.frame_index = 0
        self.frame_timer = 0.0
        self.walk_finished = False
        self.fade_state = "out"
        self.fade_timer = 0.0
        self.fade_alpha = 0
        self.position[0] = self.idle_x

    def start_enter(self, target: tuple[int, int]):
        """Approach a doorway in depth, keeping the visible feet on its path."""
        current = self.current_frame()
        if current is None:
            self.start_transition_fade()
            return
        bounds = current.get_bounding_rect(min_alpha=128)
        self.entry_start = (self.position[0] + bounds.centerx,
                            self.position[1] + bounds.bottom)
        self.entry_target = target
        distance = math.hypot(target[0] - self.entry_start[0], target[1] - self.entry_start[1])
        self.walk_duration = max(.65, distance / max(1, self.movement_speed * .6))
        self.state = "entering"
        self.walk_progress = 0.0
        self.frame_index = 0
        self.frame_timer = 0.0
        self.walk_finished = False
        self.fade_state = None
        self.fade_timer = 0.0
        self.fade_alpha = 0
        self.entry_scale = 1.0
        self._entry_frames.clear()
        self._place_entry_frame()

    def _entry_frame(self):
        frames = self.walk_frames or self.idle_frames
        frame = frames[self.frame_index % len(frames)]
        size = (max(1, round(frame.get_width() * self.entry_scale)),
                max(1, round(frame.get_height() * self.entry_scale)))
        key = (self.frame_index % len(frames), size)
        if key not in self._entry_frames:
            self._entry_frames[key] = pygame.transform.scale(frame, size)
        return self._entry_frames[key]

    def _place_entry_frame(self):
        self.entry_scale = 1.0 - .28 * self.walk_progress
        bounds = self._entry_frame().get_bounding_rect(min_alpha=128)
        feet = tuple(start + (end - start) * self.walk_progress
                     for start, end in zip(self.entry_start, self.entry_target))
        self.position[:] = [round(feet[0] - bounds.centerx), round(feet[1] - bounds.bottom)]

    def start_attack(
        self,
        enemy_width: Optional[int] = None,
        enemy_position: Optional[tuple[float, float]] = None,
        enemy_bounds: Optional[pygame.Rect] = None,
    ):
        enemy_w = enemy_width or self.target_height
        if enemy_position:
            enemy_x = float(enemy_position[0])
        else:
            enemy_x = UI_AREAS["image"].right - enemy_w - 32
        # Approach until the sword reaches the enemy, ignoring transparent margins.
        reach = max(
            (frame.get_bounding_rect(min_alpha=128).right for frame in self.attack_frames),
            default=self.target_height,
        )
        target_x = enemy_x + (enemy_bounds.left if enemy_bounds else 0) - reach + self.attack_gap
        min_x = UI_AREAS["image"].x + 8
        self.attack_target_x = max(min_x, target_x)
        self.state = "attack_approach"
        self.walk_progress = 0.0
        self.frame_index = 0
        self.frame_timer = 0.0
        self.walk_finished = False
        self.attack_finished = False
        self.fade_state = None
        self.fade_alpha = 0
        self.attack_start_x = self.idle_x
        distance = abs(self.attack_target_x - self.attack_start_x)
        self.attack_approach_duration = max(0.01, distance / self.movement_speed)
        self.attack_return_duration = self.attack_approach_duration
        self.position[0] = self.idle_x
        self.attack_sfx_played = False

    def update(self, dt: float):
        self.attack_hit = False
        self.walk_finished = False
        self.attack_finished = False

        if self.state == "entering":
            self._update_fade(dt)
            if self.state == "entering" and not self.fade_state:
                self._advance_frames(self.walk_frames or self.idle_frames, self.walk_frame_time, dt)
                self.walk_progress = min(1.0, self.walk_progress + dt / self.walk_duration)
                self._place_entry_frame()
                if self.walk_progress >= 1.0:
                    self._start_fade_out()
            return

        if self.state in ("attack_approach", "attacking", "attack_return"):
            self._update_attack(dt)
            self._apply_pending_style()
            return

        self._update_fade(dt)
        if self.fade_state:
            return
        self._apply_pending_style()

        frames = self.walk_frames if self.state == "walking" else self.idle_frames
        frame_time = (
            self.walk_frame_time if self.state == "walking" else self.idle_frame_time
        )

        self.frame_timer += dt
        if self.frame_timer >= frame_time and frames:
            steps = int(self.frame_timer / frame_time)
            self.frame_timer %= frame_time
            self.frame_index = (self.frame_index + steps) % len(frames)

        if self.state == "walking":
            if self.walk_duration <= 0:
                self.position[0] = self.walk_end_x
                self._start_fade_out()
            else:
                self.walk_progress += dt / self.walk_duration
                self.walk_progress = min(self.walk_progress, 1.0)
                delta_x = self.walk_end_x - self.walk_start_x
                self.position[0] = self.walk_start_x + delta_x * self.walk_progress
                if self.walk_progress >= 1.0:
                    self._start_fade_out()
        else:
            self.position[0] = self.idle_x

    def current_frame(self) -> Optional[pygame.Surface]:
        if self.state == "entering":
            # Hold the small doorway pose until the screen is fully black.
            return self._entry_frame()
        if self.state == "attacking":
            frames = self.attack_frames
        elif self.state in ("attack_approach", "attack_return", "walking"):
            frames = self.walk_frames
        else:
            frames = self.idle_frames
        if not frames:
            return None
        if self.fade_state == "out":
            return None
        return frames[self.frame_index % len(frames)]

    def _start_fade_out(self):
        if self.fade_state:
            return
        self.fade_state = "out"
        self.fade_timer = 0.0
        self.fade_alpha = 0

    def _update_fade(self, dt: float):
        if not self.fade_state:
            return

        self.fade_timer += dt
        progress = min(self.fade_timer / self.fade_duration, 1.0)

        if self.fade_state == "out":
            self.fade_alpha = int(255 * progress)
            if progress >= 1.0:
                self.fade_state = "in"
                self.fade_timer = 0.0
                self.fade_alpha = 255
                self.state = "idle"
                self.walk_progress = 0.0
                self.frame_index = 0
                self.frame_timer = 0.0
                self.position[:] = [self.idle_x, self.base_y]
                self.entry_scale = 1.0
                self._entry_frames.clear()
        elif self.fade_state == "in":
            self.fade_alpha = int(255 * (1 - progress))
            if progress >= 1.0:
                self.fade_state = None
                self.fade_alpha = 0
                self.walk_finished = True

    def _update_attack(self, dt: float):
        if self.state == "attack_approach":
            self._advance_frames(self.walk_frames, self.walk_frame_time, dt)
            duration = max(0.01, self.attack_approach_duration)
            self.walk_progress += dt / duration
            self.walk_progress = min(self.walk_progress, 1.0)
            start_x = self.attack_start_x
            delta_x = self.attack_target_x - start_x
            self.position[0] = start_x + delta_x * self.walk_progress
            if self.walk_progress >= 1.0:
                self.state = "attacking"
                self.frame_index = 0
                self.frame_timer = 0.0
                self.walk_progress = 0.0
                if not self.attack_sfx_played and self.attack_hit_frame == 0:
                    self._emit_attack_hit()
        elif self.state == "attacking":
            frames = self.attack_frames
            if not frames:
                self.state = "attack_return"
                self.frame_index = 0
                self.frame_timer = 0.0
                self.walk_progress = 0.0
                self.attack_return_start_x = self.position[0]
            else:
                self.frame_timer += dt
                if self.frame_timer >= self.attack_frame_time:
                    steps = int(self.frame_timer / self.attack_frame_time)
                    self.frame_timer %= self.attack_frame_time
                    self.frame_index += steps
                    if not self.attack_sfx_played and self.frame_index >= self.attack_hit_frame:
                        self._emit_attack_hit()
                    if self.frame_index >= len(frames):
                        self.state = "attack_return"
                        self.frame_index = 0
                        self.frame_timer = 0.0
                        self.walk_progress = 0.0
                        self.attack_return_start_x = self.position[0]
        elif self.state == "attack_return":
            self._advance_frames(self.walk_frames, self.walk_frame_time, dt, direction=-1)
            duration = max(0.01, self.attack_return_duration)
            self.walk_progress += dt / duration
            self.walk_progress = min(self.walk_progress, 1.0)
            start_x = self.attack_return_start_x
            delta_x = self.idle_x - start_x
            self.position[0] = start_x + delta_x * self.walk_progress
            if self.walk_progress >= 1.0:
                self.state = "idle"
                self.frame_index = 0
                self.frame_timer = 0.0
                self.attack_finished = True

    def _emit_attack_hit(self):
        self.attack_hit = True
        self.attack_sfx_played = True
        if self.sound_enabled:
            sound_manager.play_sfx("attack")

    def _advance_frames(
        self, frames: list[pygame.Surface], frame_time: float, dt: float, *, direction: int = 1
    ):
        if not frames:
            return
        self.frame_timer += dt
        if self.frame_timer >= frame_time:
            steps = int(self.frame_timer / frame_time)
            self.frame_timer %= frame_time
            self.frame_index = (self.frame_index + direction * steps) % len(frames)
