"""Main entry point for the investigation diary game.

This script sets up pygame, loads assets, and enters the main event loop.
It coordinates the user interface, the event system, and player state.
It also handles game over: if the player's HP drops to zero the game
displays the final state, waits briefly, and then exits.
"""

import pygame
import sys
import text_log
from typing import Optional

from paths import res_path
import sound_manager

# 在匯入仰賴字型的模組前先初始化 pygame
pygame.init()
pygame.font.init()
sound_manager.init_sound()

from ui_manager import (
    UI_AREAS,
    get_option_rects,
    get_areas_for_mode,
    get_inventory_slots,
    is_cinematic_mode,
    render_ui,
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
        self.idle_frame_time = 0.35
        self.walk_frame_time = 0.1
        self.walk_duration = 1.2
        self.frame_index = 0
        self.frame_timer = 0.0
        self.state = "idle"
        self.walk_progress = 0.0
        self.walk_finished = False
        self.fade_state: Optional[str] = None
        self.fade_timer = 0.0
        self.fade_duration = 0.45
        self.fade_alpha = 0
        self.walk_start_x = UI_AREAS["image"].x + 16
        self.idle_x = UI_AREAS["image"].x + 32
        self.base_y = UI_AREAS["image"].y + 80
        first_walk_frame = self.walk_frames[0] if self.walk_frames else None
        walk_width = first_walk_frame.get_width() if first_walk_frame else self.target_height
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

    def update(self, dt: float):
        self.walk_finished = False
        self._update_fade(dt)
        if self.fade_state:
            return
        
        frames = self.walk_frames if self.state == "walking" else self.idle_frames
        frame_time = self.walk_frame_time if self.state == "walking" else self.idle_frame_time

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
        frames = self.walk_frames if self.state == "walking" else self.idle_frames
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

# 視窗設定
screen = pygame.display.set_mode((512, 768))
pygame.display.set_caption("菜鳥調查隊日誌")
icon = pygame.image.load(res_path("assets", "icon.png")).convert_alpha()
pygame.display.set_icon(icon)
clock = pygame.time.Clock()

sound_manager.play_bgm()

# 載入背景與標誌圖片
start_bg = pygame.image.load(res_path("assets", "start_background.png"))
logo_image = pygame.image.load(res_path("assets", "logo1.png")).convert_alpha()
logo_image = pygame.transform.scale(logo_image, (300, 300))


# 玩家立繪
player_image = pygame.image.load(res_path("assets", "player_idle.png")).convert_alpha()
player_image = pygame.transform.scale(player_image, (96, 96))
player_animator = PlayerAnimator(target_height=96)

current_enemy_image = None  # 事件中目前使用的敵人立繪

# 字型
FONT = pygame.font.Font(res_path("assets", "Cubic_11.ttf"), 20)

# 開始選單按鈕
start_button = pygame.Rect(156, 600, 200, 50)
button_color = (70, 70, 70)
start_text = FONT.render("開始冒險", True, (255, 255, 255))
start_text_rect = start_text.get_rect(center=start_button.center)

exit_button = pygame.Rect(156, 660, 200, 50)
exit_text = FONT.render("離開遊戲", True, (255, 255, 255))
exit_text_rect = exit_text.get_rect(center=exit_button.center)

VOLUME_STEP = 0.1
volume_button_size = 36
volume_row_y_start = 520
volume_row_gap = 52

bgm_down_button = pygame.Rect(
    156 - volume_button_size - 8, volume_row_y_start, volume_button_size, volume_button_size
)
bgm_up_button = pygame.Rect(
    356 + 8, volume_row_y_start, volume_button_size, volume_button_size
)
sfx_down_button = pygame.Rect(
    156 - volume_button_size - 8,
    volume_row_y_start + volume_row_gap,
    volume_button_size,
    volume_button_size,
)
sfx_up_button = pygame.Rect(
    356 + 8,
    volume_row_y_start + volume_row_gap,
    volume_button_size,
    volume_button_size,
)

# 道具使用設定
HEALTH_POTION_NAME = "治療藥水"
HEALTH_POTION_HEAL = 10


def use_inventory_item(player: dict, index: int) -> bool:
    """Use the item at ``index`` in the player's inventory if possible."""
    inventory = player.get("inventory")
    if not inventory or index < 0 or index >= len(inventory):
        return False

    item_name = inventory[index]
    if item_name == HEALTH_POTION_NAME:
        max_hp = player.get("max_hp", player.get("hp", 0))
        current_hp = player.get("hp", 0)
        if current_hp >= max_hp:
            text_log.add(
                "你的 HP 已經滿了，暫時不需要使用治療藥水。", category="system"
            )
            text_log.scroll_to_bottom()
            return False

        heal_amount = min(HEALTH_POTION_HEAL, max_hp - current_hp)
        player["hp"] = current_hp + heal_amount
        del inventory[index]
        sound_manager.play_sfx("heal")
        text_log.add(
            f"你使用了{item_name}，HP 回復 {heal_amount} 點。", category="system"
        )
        text_log.add(f"HP +{heal_amount} → {player['hp']}", category="system")
        text_log.scroll_to_bottom()
        return True

    text_log.add(f"{item_name} 暫時無法使用。", category="system")
    text_log.scroll_to_bottom()
    return False


# 初始化玩家狀態
player = init_player_state()

# 遊戲狀態變數
game_state = "start_menu"
sub_state = "wait"
current_event = None
pending_walk_event = False

pending_clear_event = False
clear_event_timer = 0

# 主要遊戲迴圈
running = True
while running:
    # 清空畫面
    screen.fill((30, 30, 30))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state == "start_menu" and start_button.collidepoint(event.pos):
                game_state = "main_screen"
            elif game_state == "start_menu" and exit_button.collidepoint(event.pos):
                pygame.quit()
                sys.exit()
            elif game_state == "start_menu" and bgm_down_button.collidepoint(
                event.pos
            ):
                sound_manager.change_bgm_volume(-VOLUME_STEP)
            elif game_state == "start_menu" and bgm_up_button.collidepoint(event.pos):
                sound_manager.change_bgm_volume(VOLUME_STEP)
            elif game_state == "start_menu" and sfx_down_button.collidepoint(
                event.pos
            ):
                sound_manager.change_sfx_volume(-VOLUME_STEP)
            elif game_state == "start_menu" and sfx_up_button.collidepoint(event.pos):
                sound_manager.change_sfx_volume(VOLUME_STEP)
            elif game_state == "main_screen":
                areas = get_areas_for_mode(player)
                cinematic = areas.get("mode") == "cinematic"
                option_rects = get_option_rects(sub_state, current_event, player, areas)
                handled_click = False

                # 點擊「前進」區域
                if (
                    sub_state == "wait"
                    and current_event is None
                    and option_rects
                    and option_rects[0].collidepoint(event.pos)
                ):
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
                    for i, rect in enumerate(option_rects):
                        if i >= len(current_event["options"]):
                            continue
                        if rect.collidepoint(event.pos):
                            chosen = current_event["options"][i]
                            text_log.add(
                                f"你選擇了：{chosen['text']}", category="choice"
                            )
                            text_log.scroll_to_bottom()
                            # 立即重繪以顯示選擇結果
                            render_ui(
                                screen,
                                player,
                                FONT,
                                current_event,
                                sub_state,
                                player_animator.current_frame() or player_image,
                                current_enemy_image,
                                player_position=tuple(player_animator.position),
                            )
                            pygame.display.flip()
                            result = chosen.get("result")
                            if result:
                                handle_event_result(player, result)
                                text_log.scroll_to_bottom()
                            # 套用結果後再次重繪
                            render_ui(
                                screen,
                                player,
                                FONT,
                                current_event,
                                sub_state,
                                player_animator.current_frame() or player_image,
                                current_enemy_image,
                                player_position=tuple(player_animator.position),
                            )
                            pygame.display.flip()
                            battle_continues = False
                            if current_event.get("type") == "battle":
                                battle_continues = is_battle_active(player)

                            if not battle_continues:
                                # 只在當前事件完全結束時才推進進度
                                forced_event = post_event_update(player)
                                if forced_event:
                                    player["forced_event"] = forced_event
                            if battle_continues:
                                pending_clear_event = False
                                clear_event_timer = 0
                                sub_state = "show_event"
                            else:
                                # 標記事件，於下一輪迴圈清除
                                pending_clear_event = True
                                clear_event_timer = 1
                                sub_state = "after_result"
                            handled_click = True
                            break
                if not handled_click and not cinematic:
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
                                    sub_state,
                                    player_animator.current_frame() or player_image,
                                    current_enemy_image,
                                    player_position=tuple(player_animator.position),
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

    # 檢查是否遊戲結束（玩家死亡）
    if player.get("game_over"):
        # 顯示最終狀態與死亡訊息
        render_ui(
            screen,
            player,
            FONT,
            current_event,
            sub_state,
            player_animator.current_frame() or player_image,
            current_enemy_image,
            player_position=tuple(player_animator.position),
        )
        pygame.display.flip()
        # 暫停兩秒讓玩家看清訊息
        pygame.time.delay(2000)
        running = False
        continue

    dt_ms = clock.tick(60)
    dt = dt_ms / 1000.0
    player_animator.update(dt)

    if sub_state == "walking" and player_animator.walk_finished:
        from event_manager import get_random_event

        if pending_walk_event:
            pending_walk_event = False
            current_event = get_random_event(player=player)
            if current_event:
                text_log.start_event(current_event.get("id"))
                text_log.add(current_event["text"])
                text_log.scroll_to_bottom()
                image_name = current_event.get("enemy_image")
                if image_name:
                    current_enemy_image = pygame.image.load(
                        res_path("assets", image_name)
                    ).convert_alpha()
                    current_enemy_image = pygame.transform.scale(
                        current_enemy_image, (96, 96)
                    )
                else:
                    current_enemy_image = None
                if current_event.get("type") == "battle":
                    start_battle(player, current_event)
                sub_state = "show_event"
            else:
                text_log.add("命運暫時沉寂，沒有新的事件發生。", category="system")
                text_log.scroll_to_bottom()
                sub_state = "wait"
        else:
            sub_state = "wait"

    # 繪製對應畫面
    if game_state == "start_menu":
        screen.blit(start_bg, start_bg.get_rect(center=(256, 384)))
        screen.blit(logo_image, (100, 80))

        def draw_button(rect: pygame.Rect, label: str):
            pygame.draw.rect(screen, button_color, rect)
            text_surface = FONT.render(label, True, (255, 255, 255))
            screen.blit(text_surface, text_surface.get_rect(center=rect.center))

        def draw_volume_row(label: str, down_rect: pygame.Rect, up_rect: pygame.Rect, value: float):
            row_center_y = down_rect.y + down_rect.height // 2
            label_surface = FONT.render(label, True, (255, 255, 255))
            label_rect = label_surface.get_rect(center=(256, row_center_y - 24))
            screen.blit(label_surface, label_rect)

            draw_button(down_rect, "-")
            draw_button(up_rect, "+")

            value_surface = FONT.render(f"{int(value * 100)}%", True, (255, 255, 255))
            value_rect = value_surface.get_rect(center=(256, row_center_y))
            screen.blit(value_surface, value_rect)

        pygame.draw.rect(screen, button_color, start_button)
        screen.blit(start_text, start_text_rect)
        pygame.draw.rect(screen, button_color, exit_button)
        screen.blit(exit_text, exit_text_rect)
        draw_volume_row(
            "音樂音量",
            bgm_down_button,
            bgm_up_button,
            sound_manager.get_bgm_volume(),
        )
        draw_volume_row(
            "音效音量",
            sfx_down_button,
            sfx_up_button,
            sound_manager.get_sfx_volume(),
        )
    elif game_state == "main_screen":
        render_ui(
            screen,
            player,
            FONT,
            current_event,
            sub_state,
            player_animator.current_frame() or player_image,
            current_enemy_image,
            player_position=tuple(player_animator.position),
        )
    if player_animator.fade_alpha > 0:
        fade_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        fade_surface.fill((0, 0, 0, player_animator.fade_alpha))
        screen.blit(fade_surface, (0, 0))
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
            sub_state = "wait"
            pending_clear_event = False

pygame.quit()
sys.exit()
