"""Main entry point for the investigation diary game.

This script sets up pygame, loads assets, and enters the main event loop.
It coordinates the user interface, the event system, and player state.
"""

import pygame
import sys
import text_log
from typing import Optional

from paths import res_path
import sound_manager
import save_manager

BGM_START_MENU = "Music-0.mp3"
BGM_CHAPTER_TRACKS = {
    1: "Music-1.mp3",
    2: "Music-2.mp3",
}
BGM_LATE_TRACK = "Music-345.mp3"
ENDING_EXIT_DELAY_MS = 2000
ENDING_FADE_SPEED = 160.0
ENDING_LAYOUT_TRANSITION_SEC = 0.6
INTRO_FADE_SPEED = 260.0


def get_bgm_for_chapter(chapter: int) -> str:
    if chapter >= 3:
        return BGM_LATE_TRACK
    return BGM_CHAPTER_TRACKS.get(chapter, BGM_CHAPTER_TRACKS[1])


def play_bgm_for_chapter(chapter: int) -> None:
    sound_manager.play_bgm(get_bgm_for_chapter(chapter))


# 在匯入仰賴字型的模組前先初始化 pygame
pygame.init()
pygame.font.init()
sound_manager.init_sound()

from ui_manager import (
    UI_AREAS,
    UI_HEIGHT,
    get_option_rects,
    get_areas_for_mode,
    get_inventory_slots,
    is_cinematic_mode,
    render_ui,
    DEFAULT_BACKGROUND,
)
from player_state import init_player_state
from event_result_handler import handle_event_result
from fate_system import post_event_update
from battle_system import start_battle, is_battle_active, clear_battle_state


# 簡易的玩家動畫控制器
class PlayerAnimator:
    def __init__(self, target_height: int = 96):
        self.target_height = target_height
        self.idle_frames = self._load_idle_frames()
        self.walk_frames = self._load_walk_frames()
        self.attack_frames = self._load_attack_frames()
        self.idle_frame_time = 0.35
        self.walk_frame_time = 0.1
        self.attack_frame_time = 0.07
        self.walk_duration = 1.2
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

    def _scale_to_height(self, surface: pygame.Surface) -> pygame.Surface:
        width = surface.get_width()
        height = surface.get_height()
        if height == 0:
            return surface
        ratio = self.target_height / height
        scaled = pygame.transform.smoothscale(
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
        ).convert_alpha()
        # idle 圖只有兩格，直接左右切成 2 張
        return self._slice_sheet(idle_sheet, columns=2, rows=1)

    def _load_walk_frames(self) -> list[pygame.Surface]:
        frames: list[pygame.Surface] = []
        for i in range(1, 7):
            frame = pygame.image.load(
                res_path("assets", "images", "player", "walk", f"walk{i}.png")
            ).convert_alpha()
            frames.append(self._scale_to_height(frame))
        return frames

    def _load_attack_frames(self) -> list[pygame.Surface]:
        frames: list[pygame.Surface] = []
        for i in range(1, 10):
            frame = pygame.image.load(
                res_path("assets", "images", "player", "attack", f"{i}.png")
            ).convert_alpha()
            frames.append(self._scale_to_height(frame))
        return frames

    def start_walk(self):
        if not self.walk_frames:
            self.walk_finished = True
            self.state = "idle"
            return
        self.state = "walking"
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

    def start_attack(
        self,
        enemy_width: Optional[int] = None,
        enemy_position: Optional[tuple[float, float]] = None,
    ):
        frames_width = (
            self.attack_frames[0].get_width()
            if self.attack_frames
            else self.target_height
        )
        enemy_w = enemy_width or self.target_height
        if enemy_position:
            enemy_x = float(enemy_position[0])
        else:
            enemy_x = UI_AREAS["image"].right - enemy_w - 32
        target_x = enemy_x - frames_width + self.attack_gap
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
        self.position[0] = self.idle_x
        self.attack_sfx_played = False

    def update(self, dt: float):
        self.walk_finished = False
        self.attack_finished = False

        if self.state in ("attack_approach", "attacking", "attack_return"):
            self._update_attack(dt)
            return

        self._update_fade(dt)
        if self.fade_state:
            return

        frames = self.walk_frames if self.state == "walking" else self.idle_frames
        frame_time = (
            self.walk_frame_time if self.state == "walking" else self.idle_frame_time
        )

        self.frame_timer += dt
        if self.frame_timer >= frame_time and frames:
            self.frame_timer %= frame_time
            self.frame_index = (self.frame_index + 1) % len(frames)

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
                self.position[0] = self.idle_x
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
                if not self.attack_sfx_played:
                    sound_manager.play_sfx("attack")
                    self.attack_sfx_played = True
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
                    self.frame_timer = 0.0
                    self.frame_index += 1
                    if self.frame_index >= len(frames):
                        self.state = "attack_return"
                        self.frame_index = 0
                        self.frame_timer = 0.0
                        self.walk_progress = 0.0
                        self.attack_return_start_x = self.position[0]
        elif self.state == "attack_return":
            self._advance_frames(self.walk_frames, self.walk_frame_time, dt)
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

    def _advance_frames(
        self, frames: list[pygame.Surface], frame_time: float, dt: float
    ):
        if not frames:
            return
        self.frame_timer += dt
        if self.frame_timer >= frame_time:
            self.frame_timer %= frame_time
            self.frame_index = (self.frame_index + 1) % len(frames)


# 敵人動畫目標高度與垂直偏移（讓野豬更大且略微靠下）
ENEMY_DEFAULT_CONFIG = {
    # Default enemies scale roughly to player size, no extra offsets
    "target_height": 110,
    "vertical_offset": 0,
    "right_margin": 0,
}
ENEMY_VISUAL_CONFIGS = {
    # Keep boar at the original larger scale
    "wild_boar": {
        "target_height": 230,
        "vertical_offset": 60,
        "right_margin": -20,
    },
    "axe_villager": {
        "target_height": 110,
        "vertical_offset": -5,
        "right_margin": 10,
        "approach_frame_count": 5,
        "attack_frame_count": 2,
    },
    "villager": {
        "target_height": 144,  # Enlarge static villager to match player idle scale
        "vertical_offset": 20,
        "right_margin": 0,
    },
    "variant": {
        "target_height": 160,
        "vertical_offset": 12,
        "right_margin": 20,
    },
    "robot": {
        "target_height": 230,
        "vertical_offset": 45,  # slightly higher
        "right_margin": -20,
        "approach_frame_count": 2,
        "attack_frame_count": 2,
        # Heavier transparent padding: push both sides closer during attacks.
        "enemy_attack_gap": -30,
        "player_attack_gap": 60,
    },
}


class EnemyAnimator:
    def __init__(
        self,
        target_height: int = 96,
        *,
        vertical_offset: int = 0,
        right_margin: int = 0,
        approach_frame_count: Optional[int] = None,
        attack_frame_count: Optional[int] = None,
        attack_gap: int = 0,
    ):
        self.target_height = target_height
        self.vertical_offset = vertical_offset
        self.right_margin = right_margin
        self.approach_frame_count = approach_frame_count
        self.attack_frame_count = attack_frame_count
        self.attack_gap = attack_gap
        self.frames: list[pygame.Surface] = []
        self.idle_frame: Optional[pygame.Surface] = None
        self.frame_index = 0
        self.frame_timer = 0.0
        self.idle_frame_time = 0.25
        self.attack_frame_time = 0.08
        self.approach_duration = 0.32
        self.return_duration = 0.32
        self.attack_progress = 0.0
        self.state = "idle"
        self.attack_finished = True
        self.attack_sfx_played = False
        self._reset_position()

    def _scale_to_height(self, surface: pygame.Surface) -> pygame.Surface:
        width = surface.get_width()
        height = surface.get_height()
        if height <= 0:
            return surface
        ratio = self.target_height / height
        return pygame.transform.smoothscale(
            surface, (int(width * ratio), self.target_height)
        )

    def _reset_position(self, frame_size: Optional[tuple[int, int]] = None):
        frame_w, frame_h = (
            frame_size if frame_size else (self.target_height, self.target_height)
        )
        self.base_y = UI_AREAS["image"].bottom - frame_h - 16 + self.vertical_offset
        self.idle_x = UI_AREAS["image"].right - frame_w - self.right_margin
        self.position = [self.idle_x, self.base_y]
        self.attack_target_x = self.idle_x
        self.attack_start_x = self.idle_x
        self.attack_return_start_x = self.idle_x

    def apply_config(
        self,
        *,
        target_height: int,
        vertical_offset: int,
        right_margin: int,
        approach_frame_count: Optional[int] = None,
        attack_frame_count: Optional[int] = None,
        attack_gap: int = 0,
    ):
        self.target_height = target_height
        self.vertical_offset = vertical_offset
        self.right_margin = right_margin
        self.approach_frame_count = approach_frame_count
        self.attack_frame_count = attack_frame_count
        self.attack_gap = attack_gap
        self._reset_position()

    def clear(self):
        self.frames = []
        self.idle_frame = None
        self.frame_index = 0
        self.frame_timer = 0.0
        self.attack_progress = 0.0
        self.state = "idle"
        self.attack_finished = True
        self.attack_sfx_played = False
        self._reset_position()

    def set_frames(self, frames: list[pygame.Surface]):
        scaled = [self._scale_to_height(frame) for frame in frames if frame]
        self.frames = scaled
        self.idle_frame = scaled[0] if scaled else None
        self.frame_index = 0
        self.frame_timer = 0.0
        self.attack_progress = 0.0
        self.state = "idle"
        first = self.current_frame()
        if first:
            self._reset_position((first.get_width(), first.get_height()))
        else:
            self._reset_position()
        self.attack_finished = True
        self.attack_sfx_played = False

    def set_static_image(self, frame: Optional[pygame.Surface]):
        if frame is None:
            self.clear()
            return
        self.set_frames([frame])

    def current_frame(self) -> Optional[pygame.Surface]:
        if self.state in {"attack_approach", "attacking", "attack_return"}:
            if self.frames:
                return self.frames[self.frame_index % len(self.frames)]
        return self.idle_frame or (self.frames[0] if self.frames else None)

    def start_attack(
        self,
        player_surface: Optional[pygame.Surface],
        player_position: Optional[tuple[float, float]],
    ) -> bool:
        frame = self.current_frame()
        if frame is None:
            self.attack_finished = True
            return False

        player_w = player_surface.get_width() if player_surface else self.target_height
        player_h = player_surface.get_height() if player_surface else self.target_height
        if player_position:
            player_x, player_y = player_position
        else:
            player_x = UI_AREAS["image"].x + 32
            player_y = UI_AREAS["image"].bottom - player_h - 16

        self.base_y = player_y + player_h - frame.get_height() + self.vertical_offset
        self.position[1] = self.base_y
        self.attack_start_x = self.idle_x
        target_x = player_x + player_w - 12 + self.attack_gap
        min_x = UI_AREAS["image"].x + 24
        max_x = self.idle_x - 12
        self.attack_target_x = max(min_x, min(target_x, max_x))
        self.attack_progress = 0.0
        self.frame_index = 0
        self.frame_timer = 0.0
        self.state = "attack_approach"
        self.attack_finished = False
        self.attack_sfx_played = False
        return True

    def update(self, dt: float):
        if self.state == "attack_approach":
            segment_end = (
                self.approach_frame_count
                if self.approach_frame_count
                else len(self.frames)
            )
            self._advance_frames_segment(
                self.attack_frame_time,
                dt,
                0,
                max(1, segment_end),
                loop=True,
            )
            duration = max(0.01, self.approach_duration)
            self.attack_progress += dt / duration
            self.attack_progress = min(self.attack_progress, 1.0)
            delta_x = self.attack_target_x - self.attack_start_x
            self.position[0] = self.attack_start_x + delta_x * self.attack_progress
            if self.attack_progress >= 1.0:
                self.state = "attacking"
                self.frame_index = (
                    self.approach_frame_count if self.approach_frame_count else 0
                )
                self.frame_timer = 0.0
                self.attack_progress = 0.0
        elif self.state == "attacking":
            if not self.frames:
                self.state = "attack_return"
                self.frame_index = 0
                self.frame_timer = 0.0
                self.attack_progress = 0.0
                self.attack_return_start_x = self.position[0]
            else:
                attack_start_index = (
                    self.approach_frame_count if self.approach_frame_count else 0
                )
                attack_end_index = (
                    attack_start_index + self.attack_frame_count
                    if self.attack_frame_count
                    else len(self.frames)
                )
                self._advance_frames_segment(
                    self.attack_frame_time,
                    dt,
                    attack_start_index,
                    max(attack_start_index + 1, attack_end_index),
                    loop=False,
                )
                at_segment_end = self.frame_index >= attack_end_index - 1
                if at_segment_end:
                    if not self.attack_sfx_played:
                        sound_manager.play_sfx("attack")
                        self.attack_sfx_played = True
                    self.state = "attack_return"
                    self.frame_index = max(attack_start_index, attack_end_index - 1)
                    self.frame_timer = 0.0
                    self.attack_progress = 0.0
                    self.attack_return_start_x = self.position[0]
        elif self.state == "attack_return":
            self._advance_frames(self.attack_frame_time, dt)
            duration = max(0.01, self.return_duration)
            self.attack_progress += dt / duration
            self.attack_progress = min(self.attack_progress, 1.0)
            delta_x = self.idle_x - self.attack_return_start_x
            self.position[0] = (
                self.attack_return_start_x + delta_x * self.attack_progress
            )
            if self.attack_progress >= 1.0:
                self.state = "idle"
                self.frame_index = 0
                self.frame_timer = 0.0
                self.position[0] = self.idle_x
                self.attack_finished = True
        else:
            if self.frames and len(self.frames) > 1:
                self.frame_timer += dt
                if self.frame_timer >= self.idle_frame_time:
                    self.frame_timer %= self.idle_frame_time
                    self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.position[0] = self.idle_x
            self.position[1] = self.base_y
            if self.attack_finished is False:
                self.attack_finished = True

    def is_attacking(self) -> bool:
        return self.state in {"attack_approach", "attacking", "attack_return"}

    def _advance_frames(self, frame_time: float, dt: float):
        if not self.frames:
            return
        self.frame_timer += dt
        if self.frame_timer >= frame_time:
            self.frame_timer %= frame_time
            self.frame_index = (self.frame_index + 1) % len(self.frames)

    def _advance_frames_segment(
        self,
        frame_time: float,
        dt: float,
        start_index: int,
        end_index_exclusive: int,
        *,
        loop: bool,
    ):
        if not self.frames:
            return
        if end_index_exclusive <= start_index:
            return
        self.frame_timer += dt
        if self.frame_timer >= frame_time:
            self.frame_timer %= frame_time
            next_index = self.frame_index + 1
            if next_index >= end_index_exclusive:
                self.frame_index = start_index if loop else end_index_exclusive - 1
            else:
                self.frame_index = next_index


# 視窗設定
SCREEN_WIDTH = 512
SCREEN_HEIGHT = UI_HEIGHT
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("菜鳥調查隊日誌")
icon = pygame.image.load(res_path("assets", "icon.png")).convert_alpha()
pygame.display.set_icon(icon)
SCREEN_RECT = screen.get_rect()
clock = pygame.time.Clock()

sound_manager.play_bgm(BGM_START_MENU)

# 載入背景與標誌圖片
start_bg = pygame.image.load(res_path("assets", "start_background.png"))
logo_image = pygame.image.load(res_path("assets", "logo1.png")).convert_alpha()
logo_image = pygame.transform.scale(logo_image, (300, 300))


# 玩家立繪
player_image = pygame.image.load(res_path("assets", "player_idle.png")).convert_alpha()
player_image = pygame.transform.scale(player_image, (96, 96))
player_animator = PlayerAnimator(target_height=96)

enemy_animator = EnemyAnimator(
    target_height=ENEMY_DEFAULT_CONFIG["target_height"],
    vertical_offset=ENEMY_DEFAULT_CONFIG["vertical_offset"],
    right_margin=ENEMY_DEFAULT_CONFIG["right_margin"],
)
current_enemy_image = None  # 事件中目前使用的敵人立繪
enemy_attack_active = False

# 字型
FONT = pygame.font.Font(res_path("assets", "Cubic_11.ttf"), 20)
SMALL_FONT = pygame.font.Font(res_path("assets", "Cubic_11.ttf"), 16)

# 開始選單按鈕
button_width = 200
button_height = 50
button_gap = 60
button_base_y = SCREEN_HEIGHT - 240
start_button = pygame.Rect(
    (SCREEN_WIDTH - button_width) // 2, button_base_y, button_width, button_height
)
continue_button = pygame.Rect(
    (SCREEN_WIDTH - button_width) // 2,
    button_base_y - button_gap,
    button_width,
    button_height,
)
button_color = (70, 70, 70)
continue_color = (90, 70, 40)

exit_button = pygame.Rect(
    (SCREEN_WIDTH - button_width) // 2,
    button_base_y + button_gap,
    button_width,
    button_height,
)

VOLUME_STEP = 0.1
settings_button = pygame.Rect(452, 24, 36, 36)


def use_inventory_item(player: dict, index: int) -> bool:
    """Use the item at ``index`` in the player's inventory if possible."""
    inventory = player.get("inventory")
    if not inventory or index < 0 or index >= len(inventory):
        return False

    item_name = inventory[index]
    text_log.add(f"{item_name} 暫時無法使用。", category="system")
    text_log.scroll_to_bottom()
    return False


def get_settings_layout(include_navigation: bool):
    modal_width = 340
    modal_height = 280 + (130 if include_navigation else 0)
    screen_width, screen_height = screen.get_size()
    modal_rect = pygame.Rect(
        (screen_width - modal_width) // 2,
        (screen_height - modal_height) // 2,
        modal_width,
        modal_height,
    )
    row_y_start = modal_rect.y + 60
    button_size = 28
    row_gap = 16
    button_width = 140
    button_height = 32
    center_x = modal_rect.centerx
    label_x = modal_rect.x + 24
    toggle_left = modal_rect.centerx + 40 - button_width // 2
    toggle_right = toggle_left + button_width
    down_x = toggle_left
    up_x = toggle_right - button_size
    controls = {
        "modal": modal_rect,
        "bgm_down": pygame.Rect(
            down_x,
            row_y_start,
            button_size,
            button_size,
        ),
        "bgm_up": pygame.Rect(
            up_x,
            row_y_start,
            button_size,
            button_size,
        ),
        "sfx_down": pygame.Rect(
            down_x,
            row_y_start + row_gap + button_size,
            button_size,
            button_size,
        ),
        "sfx_up": pygame.Rect(
            up_x,
            row_y_start + row_gap + button_size,
            button_size,
            button_size,
        ),
        "typewriter_toggle": pygame.Rect(
            toggle_left,
            row_y_start + 2 * (row_gap + button_size),
            button_width,
            button_height,
        ),
        "close": pygame.Rect(
            center_x - button_width // 2,
            modal_rect.bottom - 48,
            button_width,
            button_height,
        ),
    }

    if include_navigation:
        nav_gap = 12
        nav_margin = 16
        nav_block_height = button_height * 2 + nav_gap
        nav_y = controls["close"].y - nav_block_height - nav_margin
        controls["to_menu"] = pygame.Rect(
            center_x - button_width // 2, nav_y, button_width, button_height
        )
        controls["quit"] = pygame.Rect(
            center_x - button_width // 2,
            nav_y + button_height + nav_gap,
            button_width,
            button_height,
        )

    return controls


def draw_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    label: str,
    *,
    color=(70, 70, 70),
    font=FONT,
):
    pygame.draw.rect(surface, color, rect, border_radius=6)
    text_surface = font.render(label, True, (255, 255, 255))
    surface.blit(text_surface, text_surface.get_rect(center=rect.center))


def draw_settings_popup(surface: pygame.Surface, include_navigation: bool):
    controls = get_settings_layout(include_navigation)
    label_x = controls["modal"].x + 24
    toggle_center_x = controls["typewriter_toggle"].centerx
    modal = controls["modal"]
    pygame.draw.rect(surface, (40, 40, 60), modal, border_radius=8)
    pygame.draw.rect(surface, (120, 120, 140), modal, 2, border_radius=8)

    title = FONT.render("設定", True, (255, 255, 255))
    surface.blit(title, title.get_rect(center=(modal.centerx, modal.y + 24)))

    def draw_volume_row(
        label: str, down_rect: pygame.Rect, up_rect: pygame.Rect, value: float
    ):
        label_surface = SMALL_FONT.render(label, True, (230, 230, 230))
        surface.blit(label_surface, (label_x, down_rect.y + 4))
        draw_button(surface, down_rect, "-", font=SMALL_FONT)
        draw_button(surface, up_rect, "+", font=SMALL_FONT)
        value_surface = SMALL_FONT.render(f"{int(value * 100)}%", True, (255, 255, 255))
        surface.blit(
            value_surface,
            value_surface.get_rect(center=(toggle_center_x, down_rect.centery)),
        )

    draw_volume_row(
        "音樂音量",
        controls["bgm_down"],
        controls["bgm_up"],
        sound_manager.get_bgm_volume(),
    )
    draw_volume_row(
        "音效音量",
        controls["sfx_down"],
        controls["sfx_up"],
        sound_manager.get_sfx_volume(),
    )
    typewriter_label = "文字逐字播放"
    typewriter_rect = controls["typewriter_toggle"]
    typewriter_state = text_log.is_typewriter_enabled()
    state_text = "開啟" if typewriter_state else "關閉"
    label_surface = SMALL_FONT.render(typewriter_label, True, (230, 230, 230))
    surface.blit(label_surface, (label_x, typewriter_rect.y + 6))
    draw_button(
        surface,
        typewriter_rect,
        state_text,
        font=SMALL_FONT,
        color=(90, 70, 40) if typewriter_state else (70, 70, 70),
    )

    if include_navigation:
        draw_button(surface, controls["to_menu"], "回到主畫面", color=(90, 70, 40))
        draw_button(surface, controls["quit"], "離開遊戲", color=(100, 40, 40))

    draw_button(surface, controls["close"], "關閉")


def handle_settings_click(pos, include_navigation: bool):
    global game_state, show_settings_popup

    controls = get_settings_layout(include_navigation)
    modal = controls["modal"]

    if not modal.collidepoint(pos):
        show_settings_popup = False
        return True

    if controls["bgm_down"].collidepoint(pos):
        sound_manager.change_bgm_volume(-VOLUME_STEP)
        return True
    if controls["bgm_up"].collidepoint(pos):
        sound_manager.change_bgm_volume(VOLUME_STEP)
        return True
    if controls["sfx_down"].collidepoint(pos):
        sound_manager.change_sfx_volume(-VOLUME_STEP)
        return True
    if controls["sfx_up"].collidepoint(pos):
        sound_manager.change_sfx_volume(VOLUME_STEP)
        return True
    if controls["typewriter_toggle"].collidepoint(pos):
        text_log.set_typewriter_enabled(not text_log.is_typewriter_enabled())
        return True

    if include_navigation:
        if controls["to_menu"].collidepoint(pos):
            persist_game_state()
            show_settings_popup = False
            game_state = "start_menu"
            sound_manager.play_bgm(BGM_START_MENU)
            return True
        if controls["quit"].collidepoint(pos):
            persist_game_state()
            pygame.quit()
            sys.exit()

    if controls["close"].collidepoint(pos):
        show_settings_popup = False
        return True

    return False


def _derive_enemy_key_from_path(path: str) -> Optional[str]:
    normalized = str(path).replace("\\", "/")
    parts = [p for p in normalized.split("/") if p]
    if not parts:
        return None
    stem = parts[-1].split(".")[0]
    if stem.isdigit() and len(parts) >= 2:
        return parts[-2]
    return stem


def get_enemy_visual_config(event_data) -> dict:
    if not event_data:
        return ENEMY_DEFAULT_CONFIG
    image_candidates: list[str] = []
    image_name = event_data.get("enemy_image")
    if image_name:
        image_candidates.append(image_name)
    frame_names = event_data.get("enemy_frames") or []
    image_candidates.extend(frame_names)
    for name in image_candidates:
        key = _derive_enemy_key_from_path(name)
        if key and key in ENEMY_VISUAL_CONFIGS:
            return ENEMY_VISUAL_CONFIGS[key]
    return ENEMY_DEFAULT_CONFIG


def load_enemy_assets_from_event(event_data, *, config: dict):
    if not event_data:
        return None, []
    primary_image = None
    frames: list[pygame.Surface] = []
    frame_names = event_data.get("enemy_frames") or []
    for name in frame_names:
        try:
            frame_surface = pygame.image.load(res_path("assets", name)).convert_alpha()
        except (FileNotFoundError, pygame.error):
            continue
        frames.append(frame_surface)
    if frames:
        primary_image = frames[0]
    image_name = event_data.get("enemy_image")
    if primary_image is None and image_name:
        try:
            image_surface = pygame.image.load(
                res_path("assets", image_name)
            ).convert_alpha()
        except (FileNotFoundError, pygame.error):
            primary_image = None
        else:
            primary_image = image_surface
    return primary_image, frames


def update_enemy_visuals(event_data):
    """Load enemy sprites for the current event and refresh the animator."""
    global current_enemy_image

    config = get_enemy_visual_config(event_data)
    enemy_animator.apply_config(
        target_height=config.get(
            "target_height", ENEMY_DEFAULT_CONFIG["target_height"]
        ),
        vertical_offset=config.get(
            "vertical_offset", ENEMY_DEFAULT_CONFIG["vertical_offset"]
        ),
        right_margin=config.get("right_margin", ENEMY_DEFAULT_CONFIG["right_margin"]),
        approach_frame_count=config.get("approach_frame_count"),
        attack_frame_count=config.get("attack_frame_count"),
        attack_gap=config.get("enemy_attack_gap", 0),
    )
    player_animator.attack_gap = config.get("player_attack_gap", 0)

    current_enemy_image, frames = load_enemy_assets_from_event(
        event_data, config=config
    )
    if frames:
        enemy_animator.set_frames(frames)
    elif current_enemy_image:
        enemy_animator.set_static_image(current_enemy_image)
    else:
        enemy_animator.clear()


def apply_event_on_enter_effects(player: dict, event: Optional[dict]) -> None:
    """Apply any passive on-enter effects for the event (e.g., auto-granted items)."""

    if not player or not event or event.get("_on_enter_applied"):
        return

    enter_effects = event.get("on_enter") or {}
    if not enter_effects:
        return

    inventory = player.setdefault("inventory", [])
    flags = player.setdefault("flags", {})

    for flag in enter_effects.get("flags_set", []) or []:
        flags[flag] = True
    for flag in enter_effects.get("flags_clear", []) or []:
        if flags.get(flag):
            flags[flag] = False

    inventory_add = enter_effects.get("inventory_add")
    if inventory_add:
        items = inventory_add if isinstance(inventory_add, list) else [inventory_add]
        for item in items:
            if item in inventory:
                continue

            def _apply_gain(item_name=item):
                if item_name not in inventory:
                    inventory.append(item_name)
                    sound_manager.play_sfx("pickup")

            text_log.add(
                f"你獲得了道具:{item}",
                category="system",
                on_show=_apply_gain,
            )

    inventory_remove = enter_effects.get("inventory_remove")
    if inventory_remove:
        items = (
            inventory_remove
            if isinstance(inventory_remove, list)
            else [inventory_remove]
        )
        for item in items:
            if item in inventory:

                def _apply_loss(item_name=item):
                    if item_name in inventory:
                        inventory.remove(item_name)
                        sound_manager.play_sfx("pickup")

                text_log.add(
                    f"你失去了道具:{item}",
                    category="system",
                    on_show=_apply_loss,
                )

    event["_on_enter_applied"] = True


def persist_game_state():
    if game_state != "main_screen":
        return

    save_manager.save_game(
        {
            "player": player,
            "game_state": game_state,
            "sub_state": sub_state,
            "current_event": current_event,
            "pending_walk_event": pending_walk_event,
            "pending_clear_event": pending_clear_event,
            "clear_event_timer": clear_event_timer,
            "text_log": text_log.export_state(),
        }
    )
    global has_save_file
    has_save_file = True


def start_new_adventure():
    global player, game_state, sub_state, current_event, pending_walk_event
    global pending_clear_event, clear_event_timer, current_enemy_image, show_settings_popup
    global has_save_file, pending_result, pending_result_requires_attack
    global enemy_attack_active, pending_result_is_battle_action, current_background_name
    global ending_exit_timer, ending_fade_alpha, intro_fade_alpha

    text_log.reset()
    player = init_player_state()
    game_state = "main_screen"
    sub_state = "wait"
    current_event = None
    pending_walk_event = False
    pending_clear_event = False
    clear_event_timer = 0
    current_enemy_image = None
    enemy_animator.apply_config(
        target_height=ENEMY_DEFAULT_CONFIG["target_height"],
        vertical_offset=ENEMY_DEFAULT_CONFIG["vertical_offset"],
        right_margin=ENEMY_DEFAULT_CONFIG["right_margin"],
    )
    enemy_animator.clear()
    enemy_attack_active = False
    current_background_name = DEFAULT_BACKGROUND
    show_settings_popup = False
    save_manager.clear_save()
    has_save_file = False
    pending_result = None
    pending_result_requires_attack = False
    pending_result_is_battle_action = False
    ending_exit_timer = 0
    ending_fade_alpha = 0.0
    intro_fade_alpha = 255.0
    player.pop("intro_cinematic_done", None)
    player.pop("intro_cinematic_active", None)
    player.pop("intro_cinematic_ready", None)
    player.pop("intro_cinematic_exiting", None)
    player.pop("intro_segments", None)
    player.pop("intro_segment_index", None)
    player.pop("layout_transition", None)
    from event_manager import get_random_event

    current_event = get_random_event(player=player)
    if current_event:
        current_background_name = current_event.get("background", DEFAULT_BACKGROUND)
        player["hide_player_sprite_until_next_event"] = (
            current_event.get("id") == "任務簡報"
        )
        text_log.start_event(current_event.get("id"))
        if (
            current_event.get("id") == "任務簡報"
            and not player.get("intro_cinematic_done")
        ):
            start_intro_cinematic(current_event)
        else:
            text_log.add(current_event["text"])
            text_log.scroll_to_bottom()
            update_enemy_visuals(current_event)
            if current_event.get("type") == "battle":
                start_battle(player, current_event)
        sub_state = "show_event"
    else:
        player["hide_player_sprite_until_next_event"] = False
    if current_event and current_event.get("id") == "任務簡報":
        sound_manager.play_bgm(BGM_START_MENU)
    else:
        play_bgm_for_chapter(player.get("chapter", 1))


def load_saved_adventure() -> bool:
    global player, game_state, sub_state, current_event, pending_walk_event
    global pending_clear_event, clear_event_timer, current_enemy_image, show_settings_popup
    global has_save_file, pending_result, pending_result_requires_attack
    global enemy_attack_active, pending_result_is_battle_action, current_background_name
    global ending_exit_timer, ending_fade_alpha, intro_fade_alpha

    data = save_manager.load_game()
    if not data:
        return False

    player = data.get("player", init_player_state())
    text_log.load_state(data.get("text_log"))
    game_state = "main_screen"
    sub_state = data.get("sub_state", "wait")
    if sub_state == "walking":
        sub_state = "wait"
        data["pending_walk_event"] = False
    current_event = data.get("current_event")
    current_background_name = (
        current_event.get("background", DEFAULT_BACKGROUND)
        if current_event
        else DEFAULT_BACKGROUND
    )
    player["hide_player_sprite_until_next_event"] = bool(
        current_event and current_event.get("id") == "任務簡報"
    )
    if (
        current_event
        and current_event.get("id") == "任務簡報"
        and not player.get("intro_cinematic_done")
        and not player.get("intro_cinematic_active")
    ):
        start_intro_cinematic(current_event)
    pending_walk_event = data.get("pending_walk_event", False)
    pending_clear_event = data.get("pending_clear_event", False)
    clear_event_timer = data.get("clear_event_timer", 0)
    update_enemy_visuals(current_event)
    show_settings_popup = False
    has_save_file = True
    pending_result = None
    pending_result_requires_attack = False
    pending_result_is_battle_action = False
    enemy_attack_active = False
    ending_exit_timer = 0
    ending_fade_alpha = 0.0
    intro_fade_alpha = 0.0
    if current_event and current_event.get("id") == "任務簡報":
        sound_manager.play_bgm(BGM_START_MENU)
    else:
        play_bgm_for_chapter(player.get("chapter", 1))
    return True


def apply_result_and_advance(result, *, from_battle_action: bool = False) -> bool:
    """Apply the chosen result, advance battle state, and refresh UI."""

    global pending_clear_event, clear_event_timer, sub_state, current_event
    global current_background_name
    global ending_exit_timer
    if not result:
        return False
    previous_chapter = player.get("chapter", 1)

    handle_event_result(player, result)
    text_log.scroll_to_bottom()

    render_ui(
        screen,
        player,
        FONT,
        current_event,
        current_background_name,
        sub_state,
        player_animator.current_frame() or player_image,
        enemy_animator.current_frame() or current_enemy_image,
        player_position=tuple(player_animator.position),
        enemy_position=tuple(enemy_animator.position),
    )
    pygame.display.flip()

    battle_continues = False
    if current_event and current_event.get("type") == "battle":
        battle_continues = is_battle_active(player)

    if not battle_continues:
        if not player.get("ending_active"):
            forced_event = post_event_update(player)
            if forced_event:
                player["forced_event"] = forced_event
    current_chapter = player.get("chapter", 1)
    if current_chapter != previous_chapter:
        play_bgm_for_chapter(current_chapter)
    if battle_continues:
        pending_clear_event = False
        clear_event_timer = 0
        sub_state = "show_event"
    else:
        if player.get("ending_active"):
            pending_clear_event = False
            clear_event_timer = 0
            ending_exit_timer = 0
            sub_state = "ending"
        else:
            if current_event and current_event.get("id") == "任務簡報":
                player["skip_walk_once"] = True
                player["hide_player_sprite_until_next_event"] = True
                player["pending_chapter_bgm"] = True
            pending_clear_event = True
            clear_event_timer = 1
            sub_state = "after_result"
    return battle_continues


def advance_ending_segment() -> bool:
    """Append the next ending segment to the log if available."""
    segments = player.get("ending_segments") or []
    index = player.get("ending_segment_index", 0)
    if index >= len(segments):
        return False
    text_log.clear_history()
    text_log.add(segments[index])
    player["ending_segment_index"] = index + 1
    text_log.scroll_to_bottom()
    return True


def advance_intro_segment() -> bool:
    """Append the next intro segment to the log if available."""
    global current_background_name, current_event
    segments = player.get("intro_segments") or []
    index = player.get("intro_segment_index", 0)
    if index >= len(segments):
        return False
    if current_event and current_event.get("id") == "任務簡報" and index == 1:
        current_background_name = "1_任務簡報2.png"
    if "intro_log_history" not in player:
        player["intro_log_history"] = text_log.snapshot_history()
    player["intro_log_history"].append(
        {
            "text": segments[index],
            "category": "narration",
            "event_id": text_log.get_current_event_id(),
        }
    )
    text_log.clear_history()
    text_log.add(segments[index])
    player["intro_segment_index"] = index + 1
    text_log.scroll_to_bottom()
    return True


def start_intro_cinematic(event: dict) -> None:
    segments = event.get("intro_segments") or []
    if not isinstance(segments, list):
        segments = [str(segments)]
    player["intro_segments"] = segments
    player["intro_segment_index"] = 0
    player["intro_cinematic_active"] = True
    player["intro_cinematic_ready"] = False
    player["intro_log_history"] = text_log.snapshot_history()
    player["intro_pending_start"] = True
    text_log.set_typewriter_override(True)
    text_log.clear_history()


def try_apply_pending_result(force: bool = False):
    """Apply pending result once ready (after attack animation when required)."""

    global pending_result, pending_result_requires_attack
    global pending_result_is_battle_action, enemy_attack_active

    if not pending_result:
        return

    if pending_result_requires_attack and not force:
        if not player_animator.attack_finished:
            return

    result = pending_result
    pending_result = None
    pending_result_requires_attack = False
    is_battle_action = pending_result_is_battle_action
    pending_result_is_battle_action = False

    battle_continues = apply_result_and_advance(
        result, from_battle_action=is_battle_action
    )

    if is_battle_action and battle_continues:
        player_surface = player_animator.current_frame() or player_image
        player_pos = tuple(player_animator.position)
        if enemy_animator.start_attack(player_surface, player_pos):
            enemy_attack_active = True


# 初始化玩家狀態
text_log.reset()
player = init_player_state()
current_background_name = DEFAULT_BACKGROUND

# 遊戲狀態變數
game_state = "start_menu"
sub_state = "wait"
current_event = None
pending_walk_event = False

pending_clear_event = False
clear_event_timer = 0
show_settings_popup = False
has_save_file = save_manager.has_save()
pending_result = None
pending_result_requires_attack = False
pending_result_is_battle_action = False
enemy_attack_active = False
ending_exit_timer = 0
ending_fade_alpha = 0.0
intro_fade_alpha = 0.0

# 主要遊戲迴圈
running = True
while running:
    # 清空畫面
    screen.fill((30, 30, 30))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if show_settings_popup:
                if handle_settings_click(event.pos, game_state == "main_screen"):
                    continue

            if settings_button.collidepoint(event.pos):
                show_settings_popup = True
                continue

            if (
                game_state == "start_menu"
                and has_save_file
                and continue_button.collidepoint(event.pos)
            ):
                load_saved_adventure()
            elif game_state == "start_menu" and start_button.collidepoint(event.pos):
                start_new_adventure()
            elif game_state == "start_menu" and exit_button.collidepoint(event.pos):
                pygame.quit()
                sys.exit()
            elif game_state == "main_screen":
                areas = get_areas_for_mode(player)
                cinematic = areas.get("mode") == "cinematic"
                option_rects = get_option_rects(sub_state, current_event, player, areas)
                handled_click = False

                if player.get("intro_cinematic_active"):
                    if player.get("intro_pending_start"):
                        handled_click = True
                        continue
                    if text_log.is_typewriter_animating():
                        handled_click = True
                    else:
                        if advance_intro_segment():
                            handled_click = True
                        elif player.get("intro_cinematic_ready"):
                            if not player.get("intro_cinematic_exiting"):
                                player["intro_cinematic_exiting"] = True
                                player["layout_transition"] = {
                                    "progress": 1.0,
                                    "direction": "out",
                                }
                            handled_click = True
                    if handled_click:
                        continue

                if player.get("ending_active"):
                    if text_log.is_typewriter_animating():
                        handled_click = True
                    else:
                        if advance_ending_segment():
                            handled_click = True
                        elif player.get("ending_exit_ready"):
                            if not player.get("ending_exit_started"):
                                player["ending_exit_started"] = True
                                ending_exit_timer = ENDING_EXIT_DELAY_MS
                                ending_fade_alpha = 0.0
                            handled_click = True
                    if handled_click:
                        continue

                # 點擊「前進」區域
                if (
                    sub_state == "wait"
                    and current_event is None
                    and option_rects
                    and option_rects[0].collidepoint(event.pos)
                    and not text_log.is_typewriter_animating()
                ):
                    if player.pop("skip_walk_once", None):
                        player_animator.start_transition_fade()
                        pending_walk_event = True
                        sub_state = "walking"
                    else:
                        player_animator.start_walk()
                        pending_walk_event = True
                        sub_state = "walking"
                    handled_click = True
                # 點擊事件選項
                elif (
                    sub_state == "show_event"
                    and current_event
                    and "options" in current_event
                ):
                    option_rects = get_option_rects(
                        sub_state, current_event, player, areas
                    )
                    if text_log.is_typewriter_animating() and any(
                        rect.collidepoint(event.pos) for rect in option_rects
                    ):
                        handled_click = True
                    elif pending_result_requires_attack or enemy_attack_active:
                        handled_click = True
                    else:
                        for i, rect in enumerate(option_rects):
                            if i >= len(current_event["options"]):
                                continue
                            if rect.collidepoint(event.pos):
                                chosen = current_event["options"][i]
                                text_log.add(
                                    f"你選擇了：{chosen['text']}", category="choice"
                                )
                                text_log.scroll_to_bottom()
                                if (
                                    current_event.get("id") == "任務簡報"
                                    and chosen.get("text") == "「任務簡報請說。」"
                                ):
                                    current_background_name = "1_任務簡報3.png"
                                result = chosen.get("result")
                                pending_result_is_battle_action = bool(
                                    result and result.get("battle_action")
                                )
                                wait_for_attack = bool(
                                    result and result.get("battle_action") == "attack"
                                )
                                if wait_for_attack:
                                    enemy_surface = (
                                        enemy_animator.current_frame()
                                        or current_enemy_image
                                    )
                                    enemy_w = (
                                        enemy_surface.get_width()
                                        if enemy_surface
                                        else None
                                    )
                                    enemy_pos = tuple(enemy_animator.position)
                                    player_animator.start_attack(
                                        enemy_width=enemy_w, enemy_position=enemy_pos
                                    )
                                pending_result = result
                                pending_result_requires_attack = wait_for_attack
                                # 立即重繪以顯示選擇或攻擊起手
                                render_ui(
                                    screen,
                                    player,
                                    FONT,
                                    current_event,
                                    current_background_name,
                                    sub_state,
                                    player_animator.current_frame() or player_image,
                                    enemy_animator.current_frame()
                                    or current_enemy_image,
                                    player_position=tuple(player_animator.position),
                                    enemy_position=tuple(enemy_animator.position),
                                )
                                pygame.display.flip()
                                try_apply_pending_result(force=not wait_for_attack)
                                handled_click = True
                                break
                if (
                    not handled_click
                    and not cinematic
                    and not pending_result_requires_attack
                    and not enemy_attack_active
                ):
                    for slot in get_inventory_slots(player, areas):
                        if (
                            slot.rect.collidepoint(event.pos)
                            and slot.item_index is not None
                        ):
                            if use_inventory_item(player, slot.item_index):
                                render_ui(
                                    screen,
                                    player,
                                    FONT,
                                    current_event,
                                    current_background_name,
                                    sub_state,
                                    player_animator.current_frame() or player_image,
                                    enemy_animator.current_frame()
                                    or current_enemy_image,
                                    player_position=tuple(player_animator.position),
                                    enemy_position=tuple(enemy_animator.position),
                                )
                                pygame.display.flip()
                            break
        elif event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            if UI_AREAS["log"].collidepoint((mouse_x, mouse_y)):
                log_width = UI_AREAS["log"].width - 16
                if event.y > 0:
                    text_log.scroll_up(FONT, log_width)
                else:
                    text_log.scroll_down()

    dt_ms = clock.tick(60)
    dt = dt_ms / 1000.0
    text_log.update_typewriter(dt)
    sound_manager.update(dt)
    player_animator.update(dt)
    enemy_animator.update(dt)
    if enemy_attack_active and enemy_animator.attack_finished:
        enemy_attack_active = False
    try_apply_pending_result()

    if intro_fade_alpha > 0:
        intro_fade_alpha = max(0.0, intro_fade_alpha - INTRO_FADE_SPEED * dt)

    if player.get("intro_pending_start") and intro_fade_alpha == 0.0:
        player["intro_pending_start"] = False
        advance_intro_segment()

    if player.get("intro_cinematic_active") and not text_log.is_typewriter_animating():
        segments = player.get("intro_segments") or []
        if player.get("intro_segment_index", 0) >= len(segments):
            player["intro_cinematic_ready"] = True

    if player.get("ending_active"):
        if not text_log.is_typewriter_animating():
            segments = player.get("ending_segments") or []
            if (
                player.get("ending_segment_index", 0) >= len(segments)
                and not player.get("ending_exit_ready")
            ):
                player["ending_exit_ready"] = True
        if player.get("ending_exit_started"):
            if ending_exit_timer > 0:
                ending_exit_timer = max(0, ending_exit_timer - dt_ms)
            else:
                ending_fade_alpha = min(
                    255.0, ending_fade_alpha + ENDING_FADE_SPEED * dt
                )
                if ending_fade_alpha >= 255.0:
                    player["return_to_menu"] = True

    transition = player.get("layout_transition")
    if transition:
        progress = float(transition.get("progress", 0.0))
        direction = transition.get("direction", "in")
        step = dt / max(0.01, ENDING_LAYOUT_TRANSITION_SEC)
        if direction == "out":
            progress -= step
            if progress <= 0.0:
                progress = 0.0
                player.pop("layout_transition", None)
                if player.get("intro_cinematic_exiting"):
                    intro_log = player.get("intro_log_history") or []
                    if intro_log:
                        text_log.set_history(intro_log)
                        text_log.scroll_to_bottom()
                    player["intro_cinematic_exiting"] = False
                    player["intro_cinematic_active"] = False
                    player["intro_cinematic_ready"] = False
                    player["intro_cinematic_done"] = True
                    text_log.set_typewriter_override(None)
            else:
                transition["progress"] = progress
        else:
            progress += step
            if progress >= 1.0:
                progress = 1.0
                player.pop("layout_transition", None)
            else:
                transition["progress"] = progress

    if (
        sub_state == "walking"
        and pending_walk_event
        and player_animator.fade_state == "in"
    ):
        from event_manager import get_random_event

        pending_walk_event = False
        current_event = get_random_event(player=player)
        if current_event:
            current_background_name = current_event.get(
                "background", DEFAULT_BACKGROUND
            )
            player["hide_player_sprite_until_next_event"] = (
                current_event.get("id") == "任務簡報"
            )
            if player.pop("pending_chapter_bgm", None):
                play_bgm_for_chapter(player.get("chapter", 1))
            text_log.start_event(current_event.get("id"))
            if (
                current_event.get("id") == "任務簡報"
                and not player.get("intro_cinematic_done")
            ):
                start_intro_cinematic(current_event)
            else:
                text_log.add(current_event["text"])
                apply_event_on_enter_effects(player, current_event)
                text_log.scroll_to_bottom()
                update_enemy_visuals(current_event)
                enemy_attack_active = False
                if current_event.get("type") == "battle":
                    start_battle(player, current_event)
            sub_state = "show_event"
        else:
            text_log.add("命運暫時沉寂，沒有新的事件發生。", category="system")
            text_log.scroll_to_bottom()
            sub_state = "wait"
            player["hide_player_sprite_until_next_event"] = False
    elif sub_state == "walking" and player_animator.walk_finished:
        sub_state = "wait"

    # 繪製對應畫面
    if game_state == "start_menu":
        screen.blit(start_bg, start_bg.get_rect(center=SCREEN_RECT.center))
        screen.blit(logo_image, (100, 80))

        if has_save_file:
            draw_button(screen, continue_button, "繼續冒險", color=continue_color)

        draw_button(screen, start_button, "開始冒險")
        draw_button(screen, exit_button, "離開遊戲")

        summary_surface = SMALL_FONT.render(
            f"音樂 {int(sound_manager.get_bgm_volume() * 100)}% / 音效 {int(sound_manager.get_sfx_volume() * 100)}%",
            True,
            (230, 230, 230),
        )
        summary_rect = summary_surface.get_rect(
            right=settings_button.x - 8, centery=settings_button.centery
        )
        screen.blit(summary_surface, summary_rect)
    elif game_state == "main_screen":
        render_ui(
            screen,
            player,
            FONT,
            current_event,
            current_background_name,
            sub_state,
            player_animator.current_frame() or player_image,
            enemy_animator.current_frame() or current_enemy_image,
            player_position=tuple(player_animator.position),
            enemy_position=tuple(enemy_animator.position),
        )
    draw_button(screen, settings_button, "設定", font=SMALL_FONT)
    if show_settings_popup:
        draw_settings_popup(screen, game_state == "main_screen")
    if player_animator.fade_alpha > 0:
        fade_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        fade_surface.fill((0, 0, 0, player_animator.fade_alpha))
        screen.blit(fade_surface, (0, 0))
    if ending_fade_alpha > 0:
        fade_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        fade_surface.fill((0, 0, 0, int(ending_fade_alpha)))
        screen.blit(fade_surface, (0, 0))
    if intro_fade_alpha > 0:
        fade_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        fade_surface.fill((0, 0, 0, int(intro_fade_alpha)))
        screen.blit(fade_surface, (0, 0))
    persist_game_state()
    pygame.display.flip()

    # 延遲後清除事件
    if pending_clear_event:
        if clear_event_timer > 0:
            clear_event_timer -= 1
        else:
            if current_event and current_event.get("type") == "battle":
                clear_battle_state(player)
            current_event = None
            current_enemy_image = None
            enemy_animator.clear()
            enemy_attack_active = False
            sub_state = "wait"
            pending_clear_event = False

    if game_state == "main_screen" and player.get("return_to_menu"):
        player["return_to_menu"] = False
        text_log.set_typewriter_override(None)
        for key in (
            "ending_active",
            "ending_segments",
            "ending_segment_index",
            "ending_exit_ready",
            "ending_exit_started",
            "intro_cinematic_active",
            "intro_cinematic_ready",
            "intro_cinematic_exiting",
            "intro_pending_start",
            "intro_segments",
            "intro_segment_index",
            "intro_log_history",
        ):
            player.pop(key, None)
        player.setdefault("flags", {}).pop("ending_cinematic", None)
        player.pop("layout_transition", None)
        ending_exit_timer = 0
        ending_fade_alpha = 0.0
        save_manager.clear_save()
        has_save_file = False
        show_settings_popup = False
        game_state = "start_menu"
        sound_manager.play_bgm(BGM_START_MENU)

pygame.quit()
sys.exit()
