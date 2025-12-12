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
import save_manager

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
        self.base_y = UI_AREAS["image"].bottom - self.target_height - 16
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
SCREEN_WIDTH = 512
SCREEN_HEIGHT = UI_HEIGHT
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("菜鳥調查隊日誌")
icon = pygame.image.load(res_path("assets", "icon.png")).convert_alpha()
pygame.display.set_icon(icon)
SCREEN_RECT = screen.get_rect()
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
SMALL_FONT = pygame.font.Font(res_path("assets", "Cubic_11.ttf"), 16)

# 開始選單按鈕
button_width = 200
button_height = 50
button_gap = 60
button_base_y = SCREEN_HEIGHT - 240
start_button = pygame.Rect((SCREEN_WIDTH - button_width) // 2, button_base_y, button_width, button_height)
continue_button = pygame.Rect((SCREEN_WIDTH - button_width) // 2, button_base_y - button_gap, button_width, button_height)
button_color = (70, 70, 70)
continue_color = (90, 70, 40)

exit_button = pygame.Rect((SCREEN_WIDTH - button_width) // 2, button_base_y + button_gap, button_width, button_height)

VOLUME_STEP = 0.1
settings_button = pygame.Rect(452, 24, 36, 36)

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


def get_settings_layout(include_navigation: bool):
    modal_width = 340
    modal_height = 230 + (130 if include_navigation else 0)
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
    horizontal_offset = 40
    button_width = 140
    button_height = 32
    center_x = modal_rect.centerx
    controls = {
        "modal": modal_rect,
        "bgm_down": pygame.Rect(center_x - horizontal_offset - button_size, row_y_start, button_size, button_size),
        "bgm_up": pygame.Rect(center_x + horizontal_offset, row_y_start, button_size, button_size),
        "sfx_down": pygame.Rect(
            center_x - horizontal_offset - button_size, row_y_start + row_gap + button_size, button_size, button_size
        ),
        "sfx_up": pygame.Rect(center_x + horizontal_offset, row_y_start + row_gap + button_size, button_size, button_size),
        "close": pygame.Rect(center_x - button_width // 2, modal_rect.bottom - 48, button_width, button_height),
    }

    if include_navigation:
        nav_gap = 12
        nav_margin = 16
        nav_block_height = button_height * 2 + nav_gap
        nav_y = controls["close"].y - nav_block_height - nav_margin
        controls["to_menu"] = pygame.Rect(center_x - button_width // 2, nav_y, button_width, button_height)
        controls["quit"] = pygame.Rect(
            center_x - button_width // 2, nav_y + button_height + nav_gap, button_width, button_height
        )

    return controls


def draw_button(surface: pygame.Surface, rect: pygame.Rect, label: str, *, color=(70, 70, 70), font=FONT):
    pygame.draw.rect(surface, color, rect, border_radius=6)
    text_surface = font.render(label, True, (255, 255, 255))
    surface.blit(text_surface, text_surface.get_rect(center=rect.center))


def draw_settings_popup(surface: pygame.Surface, include_navigation: bool):
    controls = get_settings_layout(include_navigation)
    modal = controls["modal"]
    pygame.draw.rect(surface, (40, 40, 60), modal, border_radius=8)
    pygame.draw.rect(surface, (120, 120, 140), modal, 2, border_radius=8)

    title = FONT.render("設定", True, (255, 255, 255))
    surface.blit(title, title.get_rect(center=(modal.centerx, modal.y + 24)))

    def draw_volume_row(label: str, down_rect: pygame.Rect, up_rect: pygame.Rect, value: float):
        label_surface = SMALL_FONT.render(label, True, (230, 230, 230))
        surface.blit(label_surface, (modal.x + 28, down_rect.y + 4))
        draw_button(surface, down_rect, "-", font=SMALL_FONT)
        draw_button(surface, up_rect, "+", font=SMALL_FONT)
        value_surface = SMALL_FONT.render(f"{int(value * 100)}%", True, (255, 255, 255))
        surface.blit(value_surface, value_surface.get_rect(center=(modal.centerx, down_rect.centery)))

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

    if include_navigation:
        if controls["to_menu"].collidepoint(pos):
            persist_game_state()
            show_settings_popup = False
            game_state = "start_menu"
            return True
        if controls["quit"].collidepoint(pos):
            persist_game_state()
            pygame.quit()
            sys.exit()

    if controls["close"].collidepoint(pos):
        show_settings_popup = False
        return True

    return False


def load_enemy_image_from_event(event_data):
    if not event_data:
        return None
    image_name = event_data.get("enemy_image")
    if not image_name:
        return None
    try:
        image_surface = pygame.image.load(res_path("assets", image_name)).convert_alpha()
    except (FileNotFoundError, pygame.error):
        return None
    return pygame.transform.scale(image_surface, (96, 96))


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
    global has_save_file

    text_log.reset()
    player = init_player_state()
    game_state = "main_screen"
    sub_state = "wait"
    current_event = None
    pending_walk_event = False
    pending_clear_event = False
    clear_event_timer = 0
    current_enemy_image = None
    show_settings_popup = False
    save_manager.clear_save()
    has_save_file = False


def load_saved_adventure() -> bool:
    global player, game_state, sub_state, current_event, pending_walk_event
    global pending_clear_event, clear_event_timer, current_enemy_image, show_settings_popup
    global has_save_file

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
    pending_walk_event = data.get("pending_walk_event", False)
    pending_clear_event = data.get("pending_clear_event", False)
    clear_event_timer = data.get("clear_event_timer", 0)
    current_enemy_image = load_enemy_image_from_event(current_event)
    show_settings_popup = False
    has_save_file = True
    return True


# 初始化玩家狀態
text_log.reset()
player = init_player_state()

# 遊戲狀態變數
game_state = "start_menu"
sub_state = "wait"
current_event = None
pending_walk_event = False

pending_clear_event = False
clear_event_timer = 0
show_settings_popup = False
has_save_file = save_manager.has_save()

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

            if game_state == "start_menu" and has_save_file and continue_button.collidepoint(
                event.pos
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
        summary_rect = summary_surface.get_rect(right=settings_button.x - 8, centery=settings_button.centery)
        screen.blit(summary_surface, summary_rect)
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
    draw_button(screen, settings_button, "設定", font=SMALL_FONT)
    if show_settings_popup:
        draw_settings_popup(screen, game_state == "main_screen")
    if player_animator.fade_alpha > 0:
        fade_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        fade_surface.fill((0, 0, 0, player_animator.fade_alpha))
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
            sub_state = "wait"
            pending_clear_event = False

pygame.quit()
sys.exit()
