import pygame
import sys
from player_state import Player
from ui_manager import (
    draw_scene,
    draw_status_panel,
    draw_buttons,
    draw_text,
)
from event_manager import EventManager
from battle_manager import run_battle
from text_log import TextLogManager
from inventory_panel import InventoryPanel

# === 初始化 ===
pygame.init()
pygame.font.init()

# === 畫面設定 ===
WIDTH, HEIGHT = 720, 960
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("菜鳥調查隊日誌")
clock = pygame.time.Clock()

# === 區塊定義（由上而下）===
scene_panel = pygame.Rect(20, 20, 680, 200)
msg_panel = pygame.Rect(20, 230, 680, 200)
status_panel = pygame.Rect(20, 440, 340, 200)
button_panel = pygame.Rect(360, 440, 340, 200)
inventory_rect = pygame.Rect(20, 660, 680, 240)
inventory_toggle_btn = pygame.Rect(600, 910, 100, 30)

# === 字型與物件 ===
font = pygame.font.SysFont("Microsoft JhengHei", 22)
player = Player()
event_mgr = EventManager("story_data.json")
background_image = pygame.image.load("starting_area.png").convert_alpha()
background_scaled = pygame.transform.scale(
    background_image, (scene_panel.width, scene_panel.height)
)
log_manager = TextLogManager(font, msg_panel)
inventory = InventoryPanel(font, inventory_rect)

dummy_enemy = {"name": "???", "hp": 0, "max_hp": 0, "atk": 0, "desc": "未知的敵人..."}
log_manager.add("你踏入了草原... 點擊上方背景區域以探索。", "system")

buttons = []
button_rects = []


def update_buttons(option_list):
    global buttons, button_rects
    buttons = option_list
    button_rects.clear()
    btn_h, spacing = 60, 10
    for i in range(len(buttons)):
        x = button_panel.x + 15
        y = button_panel.y + 15 + i * (btn_h + spacing)
        button_rects.append(pygame.Rect(x, y, button_panel.width - 30, btn_h))


def load_next_event(event_id=None):
    global current_event, event_active
    current_event = (
        event_mgr.get_event_by_id(event_id)
        if event_id
        else event_mgr.get_random_event()
    )
    if current_event:
        event_active = True
        if current_event["type"] == "battle":
            log_manager.add(f"遭遇戰鬥：{current_event['enemy']['name']}！", "event")
            result = run_battle(screen, player, current_event["enemy"], font, [])
            outcome = (
                current_event["win_result"]
                if result["win"]
                else current_event["lose_result"]
            )
            log_manager.add(outcome["text"], "event")
            dummy_enemy.update(current_event["enemy"])
            if "add_item" in outcome:
                player.add_item(outcome["add_item"])
                log_manager.add(f"獲得道具：{outcome['add_item']}", "gain")
            if "fate_change" in outcome:
                player.increase_fate(outcome["fate_change"])
                log_manager.add(f"命運值 +{outcome['fate_change']}", "gain")
            if "set_flag" in outcome:
                player.set_flag(outcome["set_flag"])
            if "ending" in outcome:
                log_manager.add("你觸發了一個結局！", "system")
                buttons.clear()
            event_active = False
        else:
            log_manager.add(current_event["text"], "event")
            update_buttons(current_event.get("options", []))


# === 開始畫面 ===
def start_menu():
    menu_font = pygame.font.SysFont("Microsoft JhengHei", 28)
    title_font = pygame.font.SysFont("Microsoft JhengHei", 36, bold=True)
    background = pygame.image.load("start_background.png").convert()
    background = pygame.transform.scale(background, (WIDTH, HEIGHT))

    while True:
        screen.blit(background, (0, 0))
        title = title_font.render("菜鳥調查隊日誌", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        start_btn = pygame.Rect(260, 400, 200, 50)
        quit_btn = pygame.Rect(260, 470, 200, 50)
        mouse = pygame.mouse.get_pos()

        pygame.draw.rect(
            screen,
            (70, 130, 220) if start_btn.collidepoint(mouse) else (60, 60, 70),
            start_btn,
        )
        pygame.draw.rect(
            screen,
            (230, 60, 60) if quit_btn.collidepoint(mouse) else (60, 60, 70),
            quit_btn,
        )

        draw_text(
            screen,
            "開始冒險",
            (start_btn.x + 50, start_btn.y + 10),
            (255, 255, 255),
            menu_font,
        )
        draw_text(
            screen,
            "離開遊戲",
            (quit_btn.x + 50, quit_btn.y + 10),
            (255, 255, 255),
            menu_font,
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if start_btn.collidepoint(event.pos):
                    return
                elif quit_btn.collidepoint(event.pos):
                    pygame.quit()
                    sys.exit()

        pygame.display.flip()
        clock.tick(60)


# === 主迴圈 ===
current_event = None
event_active = False
running = True

start_menu()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if scene_panel.collidepoint(event.pos) and not event_active:
                log_manager.add("你往前邁出一步...", "system")
                load_next_event()
            for i, rect in enumerate(button_rects):
                if rect.collidepoint(event.pos):
                    option = buttons[i]
                    if "require_item" in option and not player.has_item(
                        option["require_item"]
                    ):
                        log_manager.add(
                            f"你沒有 {option['require_item']}，無法選擇此行動。",
                            "warning",
                        )
                    else:
                        result_text, effects, next_event = event_mgr.process_option(
                            player, option
                        )
                        log_manager.add(result_text, "event")
                        for e in effects:
                            log_manager.add(e, "event")
                        update_buttons([])
                        event_active = False
                        current_event = None
                        if next_event:
                            load_next_event(next_event)
            if inventory_toggle_btn.collidepoint(event.pos):
                inventory.toggle()
        elif event.type == pygame.MOUSEWHEEL:
            log_manager.scroll(-event.y)
            if inventory.visible:
                inventory.scroll_items(-event.y, len(player.items))

    screen.fill((0, 0, 0))
    draw_scene(screen, scene_panel, background_scaled, dummy_enemy, font)
    log_manager.draw(screen)
    draw_status_panel(screen, status_panel, player, font)
    draw_buttons(screen, button_rects, [opt["text"] for opt in buttons], font)
    inventory.draw_toggle_button(screen, inventory_toggle_btn)
    inventory.draw_panel(screen, player.items)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
