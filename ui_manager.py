import pygame
import text_log


# 區塊尺寸與位置設定
UI_AREAS = {
    "image": pygame.Rect(32, 32, 448, 200),
    "log": pygame.Rect(32, 244, 448, 230),
    "status": pygame.Rect(32, 488, 240, 132),
    "options": [
        pygame.Rect(296, 488 + i * 45, 184, 40) for i in range(3)
    ],
    "inventory_bar": pygame.Rect(32, 712, 448, 24),
    "inventory_preview": pygame.Rect(32, 656, 448, 56),
    "inventory_full": pygame.Rect(32, 524, 448, 132),
}

# 載入畫面圖片
starting_image = pygame.image.load("assets/starting_area.png")
starting_image = pygame.transform.scale(starting_image, UI_AREAS["image"].size)

# 區塊顏色
COLORS = {
    "image": (40, 80, 40),
    "log": (30, 30, 30),
    "status": (40, 40, 80),
    "option": (60, 60, 60),
    "option_disabled": (40, 40, 40),
    "option_hover": (100, 100, 100),
    "inventory": (90, 90, 40),         # 展開或預覽內容背景
    "inventory_bar": (110, 110, 110),  # 背包條
}

# 主 UI 繪製
# 傳入 screen（畫面）、player（狀態）、font（字型）
def draw_main_ui(screen, player, font, current_event=None, sub_state="wait",
                 player_image=None, enemy_image=None, inventory_open=False):
    mouse_pos = pygame.mouse.get_pos()

    # 畫圖像區塊（顯示圖片）
    screen.blit(starting_image, UI_AREAS["image"].topleft)

    # 畫主角（畫面區左側）
    if player_image:
        screen.blit(player_image, (UI_AREAS["image"].x + 32, UI_AREAS["image"].y + 80))

    # ➤ 畫怪物圖（如果有指定）
    if enemy_image:
        enemy_pos = (UI_AREAS["image"].right - 96 - 32, UI_AREAS["image"].y + 80)
        screen.blit(enemy_image, enemy_pos)

    # 畫紀錄文字框
    pygame.draw.rect(screen, COLORS["log"], UI_AREAS["log"])
    log_messages = text_log.get_visible_logs()
    max_lines = 9
    for i, line in enumerate(log_messages[:max_lines]):
        if any(word in line for word in ["HP", "ATK", "DEF", "fate"]):
            draw_text(screen, line, UI_AREAS["log"], font, center=False, line_offset=i, color=(255, 80, 80))  # 紅色
        else:
            draw_text(screen, line, UI_AREAS["log"], font, center=False, line_offset=i)

    # 畫數值欄
    pygame.draw.rect(screen, COLORS["status"], UI_AREAS["status"])
    lines = [
        f"HP: {player['hp']}",
        f"ATK: {player['atk']}",
        f"DEF: {player['def']}"
    ]
    for i, line in enumerate(lines):
        draw_text(screen, line, UI_AREAS["status"], font, center=False, line_offset=i)

    # 畫選項
    if sub_state == "wait":
        # ➤ 狀態是等待中：整塊選項區合併成一個大按鈕
        full_rect = UI_AREAS["options"][0].unionall(UI_AREAS["options"])  # 合併三格成一個區域
        is_hover = full_rect.collidepoint(mouse_pos)
        color = COLORS["option_hover"] if is_hover else COLORS["option"]
        pygame.draw.rect(screen, color, full_rect)
        draw_text(screen, "前進", full_rect, font, center=True)

    elif sub_state == "show_event" and current_event:
        # ➤ 有事件時才顯示個別選項
        for i, rect in enumerate(UI_AREAS["options"]):
            is_hover = rect.collidepoint(mouse_pos)

            if i < len(current_event["options"]):
                # 有對應選項的格子：顯示選項文字
                color = COLORS["option_hover"] if is_hover else COLORS["option"]
                pygame.draw.rect(screen, color, rect)
                option_text = current_event["options"][i]["text"]
                draw_text(screen, option_text, rect, font, center=True)
            else:
                # 超出選項數的格子：灰色無效
                pygame.draw.rect(screen, COLORS["option_disabled"], rect)
                draw_text(screen, "……", rect, font, center=True)

    # 固定背包條的位置
    bar_y = 712
    inventory_bar_rect = pygame.Rect(32, bar_y, 448, 24)

    # 畫背包條（永遠在最底下）
    pygame.draw.rect(screen, COLORS["inventory_bar"], inventory_bar_rect)
    symbol = "▲" if inventory_open else "▼"
    draw_text(screen, f"{symbol} 背包（共 {len(player['inventory'])} 項）", inventory_bar_rect, font, center=True)

    # 展開內容向上長（貼在背包條「上方」），根據道具數量調整高度（最多顯示 5 項）
    if inventory_open:
        items = player["inventory"]
        max_visible_items = 5
        item_height = 24

        # 計算實際顯示項目與高度（加入可滾動邏輯）
        total_items = len(items)
        scroll_offset = player.get("inventory_scroll", 0)
        visible_items = items[scroll_offset:scroll_offset + max_visible_items]
        visible_count = len(visible_items)
        padding = 7  # 額外高度空間，避免最後一行被背包條壓到
        content_height = visible_count * item_height + padding
        inventory_full_rect = pygame.Rect(32, bar_y - content_height, 448, content_height)
        pygame.draw.rect(screen, COLORS["inventory"], inventory_full_rect)

        if total_items == 0:
            inventory_full_rect = pygame.Rect(32, bar_y - 32, 448, 32)
            pygame.draw.rect(screen, COLORS["inventory"], inventory_full_rect)
            draw_text(screen, "（目前無道具）", inventory_full_rect, font, center=False)
        else:
            inventory_full_rect = pygame.Rect(32, bar_y - content_height, 448, content_height)
            pygame.draw.rect(screen, COLORS["inventory"], inventory_full_rect)
            for i, item in enumerate(visible_items):
                draw_text(screen, f"- {item}", inventory_full_rect, font, center=False, line_offset=i)
            if total_items > max_visible_items and visible_count < max_visible_items:
                draw_text(screen, "（使用滑鼠滾輪瀏覽）", inventory_full_rect, font, center=False, line_offset=visible_count)

        # 滾動提示（如果道具數超過顯示上限）
        if total_items > max_visible_items:
            if visible_count < max_visible_items:
                draw_text(screen, "（使用滑鼠滾輪瀏覽）", inventory_full_rect, font, center=False, line_offset=visible_count)

    else:
        # 收合狀態只顯示預覽（往上 56px）
        inventory_preview_rect = pygame.Rect(32, bar_y - 56, 448, 56)
        pygame.draw.rect(screen, COLORS["inventory"], inventory_preview_rect)
        preview = "、".join(player["inventory"][:2])
        if len(player["inventory"]) > 2:
            preview += "、……"
        elif not player["inventory"]:
            preview = "（目前無道具）"
        draw_text(screen, preview, inventory_preview_rect, font, center=False)

# 顯示文字（可置中）
def draw_text(screen, text, rect, font, center=False, line_offset=0, color=(255, 255, 255)):
    rendered = font.render(text, True, color)
    if center:
        text_rect = rendered.get_rect(center=rect.center)
    else:
        text_rect = rendered.get_rect(topleft=(rect.x + 8, rect.y + 8 + line_offset * 24))
    screen.blit(rendered, text_rect)
