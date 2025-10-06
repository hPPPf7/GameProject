import pygame
import sys
import text_log


# 必須在 import 其他模組之前初始化
pygame.init()
pygame.font.init()

# 初始化完再 import 其他模組（這樣 FONT 才能成功定義）
from ui_manager import draw_main_ui
from player_state import init_player_state
from event_result_handler import handle_event_result

# 畫面設定
screen = pygame.display.set_mode((512, 768))
pygame.display.set_caption("菜鳥調查隊日誌")

# 設定視窗 icon（角色圖示）
icon = pygame.image.load("assets/icon.png").convert_alpha()
pygame.display.set_icon(icon)

clock = pygame.time.Clock()

# 載入背景圖與 logo 圖（請放到 assets/）
start_bg = pygame.image.load("assets/start_background.png")
logo_image = pygame.image.load("assets/logo1.png").convert_alpha()
logo_image = pygame.transform.scale(logo_image, (300, 300))

player_image = pygame.image.load("assets/player_idle.png").convert_alpha()
player_image = pygame.transform.scale(player_image, (96, 96))

current_enemy_image = None  # ➤ 目前事件用到的怪物圖片

# 字體
FONT = pygame.font.Font("assets/Cubic_11.ttf", 20)

# ➤ 等待清除事件用的旗標（在畫面更新後才清除 current_event）
pending_clear_event = False
log_has_been_drawn = False  # ➤ 確保 log 已畫出才清除事件

# ➤ 強制立即繪製畫面（為了馬上顯示 log 訊息）
def force_draw_screen():
    global log_has_been_drawn
    text_log.scroll_to_bottom()
    draw_main_ui(screen, player, FONT, current_event, sub_state, player_image, current_enemy_image, inventory_open)
    pygame.display.flip()
    log_has_been_drawn = True

# 遊戲狀態定義
# 可擴充: start_menu, event_play, main_story, ending
game_state = "start_menu"  # 開始畫面
sub_state = "wait"          # 子狀態：等待點擊 or 顯示事件
current_event = None        # 目前事件

# 按鈕設定
start_button = pygame.Rect(156, 600, 200, 50)
button_color = (70, 70, 70)
start_text = FONT.render("開始冒險", True, (255, 255, 255))
start_text_rect = start_text.get_rect(center=start_button.center)

exit_button = pygame.Rect(156, 660, 200, 50)
exit_text = FONT.render("離開遊戲", True, (255, 255, 255))
exit_text_rect = exit_text.get_rect(center=exit_button.center)


# 玩家狀態初始化
player = init_player_state()
inventory_open = False  # 背包是否展開

# 主迴圈
running = True
pending_clear_event = False
clear_event_timer = 0  # 新增：延遲幀數
inventory_scroll = 0

while running:
    screen.fill((30, 30, 30))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # 只允許滑鼠左鍵觸發
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state == "start_menu" and start_button.collidepoint(event.pos):
                game_state = "main_screen"

            elif game_state == "start_menu" and exit_button.collidepoint(event.pos):
                pygame.quit()
                sys.exit()

            elif game_state == "main_screen":
                from ui_manager import UI_AREAS
                full_rect = UI_AREAS["options"][0].unionall(UI_AREAS["options"])

                # 點擊背包展開條
                inventory_bar_rect = pygame.Rect(32, 712, 448, 24)
                if inventory_bar_rect.collidepoint(event.pos):
                    inventory_open = not inventory_open

                # 點擊「前進」格子觸發事件
                if sub_state == "wait" and current_event is None and full_rect.collidepoint(event.pos):
                    from event_manager import get_random_event
                    current_event = get_random_event(["normal", "battle", "dialogue"], player)
                    if current_event:
                        text_log.add(current_event["text"])
                        text_log.scroll_to_bottom()

                        # ➤ 如果事件有指定 enemy_image，就載入圖檔
                        image_name = current_event.get("enemy_image")
                        if image_name:
                            current_enemy_image = pygame.image.load(f"assets/{image_name}").convert_alpha()
                            current_enemy_image = pygame.transform.scale(current_enemy_image, (96, 96))
                        else:
                            current_enemy_image = None
                    sub_state = "show_event"

                # 點擊事件選項
                elif sub_state == "show_event" and current_event and "options" in current_event:
                    for i, rect in enumerate(UI_AREAS["options"]):
                        if i >= len(current_event["options"]):
                            continue
                        if rect.collidepoint(event.pos):
                            chosen = current_event["options"][i]

                            text_log.add(f"你選擇了：{chosen['text']}")
                            text_log.scroll_to_bottom()

                            # 強制畫面刷新顯示選擇
                            draw_main_ui(screen, player, FONT, current_event, sub_state, player_image, current_enemy_image, inventory_open)
                            pygame.display.flip()

                            result = chosen.get("result")
                            if result:
                                from event_result_handler import handle_event_result
                                handle_event_result(player, result)
                                text_log.scroll_to_bottom()

                            # 畫一次處理完的內容
                            draw_main_ui(screen, player, FONT, current_event, sub_state, player_image, current_enemy_image, inventory_open)
                            pygame.display.flip()

                            # ➤ 設定延遲清除旗標（下一輪才清除）
                            pending_clear_event = True
                            clear_event_timer = 1  # ➤ 延遲 1 frame
                            sub_state = "after_result"
                            break

        # 使用滾輪控制紀錄
        elif event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()

            # 滾動文字紀錄欄（滑鼠在 log 區）
            if UI_AREAS["log"].collidepoint((mouse_x, mouse_y)):
                if event.y > 0:
                    text_log.scroll_up()
                else:
                    text_log.scroll_down()

            # 滾動背包（滑鼠在背包展開區）
            elif inventory_open:
                max_scroll = max(len(player["inventory"]) - 5, 0)
                if event.y > 0:
                    player["inventory_scroll"] = max(player["inventory_scroll"] - 1, 0)
                elif event.y < 0:
                    player["inventory_scroll"] = min(player["inventory_scroll"] + 1, max_scroll)


    # 畫面切換邏輯
    if game_state == "start_menu":
        screen.blit(start_bg, start_bg.get_rect(center=(256, 384)))

        # 顯示 logo
        screen.blit(logo_image, (100, 80))

        # 開始與離開按鈕
        pygame.draw.rect(screen, button_color, start_button)
        screen.blit(start_text, start_text_rect)

        pygame.draw.rect(screen, button_color, exit_button)
        screen.blit(exit_text, exit_text_rect)

    # 畫面更新後的邏輯（主畫面狀態結束才清除事件）
    elif game_state == "main_screen":
        draw_main_ui(screen, player, FONT, current_event, sub_state, player_image, current_enemy_image, inventory_open)

    pygame.display.flip()
    clock.tick(60)

    # ➤ 清除上一個事件（延遲一幀）
    if pending_clear_event:
        if clear_event_timer > 0:
            clear_event_timer -= 1
        else:
            current_event = None
            current_enemy_image = None
            sub_state = "wait"
            pending_clear_event = False

pygame.quit()
sys.exit()
