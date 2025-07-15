import pygame
from player_state import Player

# 顏色設定
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK = (25, 25, 35)
GRAY = (60, 60, 70)
BLUE = (70, 130, 220)
RED = (230, 60, 60)
YELLOW = (255, 200, 40)


# 單行文字
def draw_text(surface, text, pos, color=WHITE, font=None):
    if font:
        text_surf = font.render(text, True, color)
        surface.blit(text_surf, pos)


# 換行繪製（回傳最後一行底部 Y 座標）
def draw_wrapped_text(surface, text, rect, font, color, line_spacing=4):
    words = text.split(" ")
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] < rect.width - 20:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word + " "
    lines.append(current_line)

    y = rect.y + 10
    for line in lines:
        surface.blit(font.render(line.strip(), True, color), (rect.x + 10, y))
        y += font.get_linesize() + line_spacing
    return y


# 場景區塊（含敵人名稱）
def draw_scene(surface, scene_rect, image_scaled, enemy, font):
    surface.blit(image_scaled, (scene_rect.x, scene_rect.y))
    pygame.draw.rect(surface, WHITE, scene_rect, 2)
    draw_text(surface, enemy["name"], (scene_rect.x + 20, scene_rect.y + 10), RED, font)


# 狀態欄
def draw_status_panel(surface, rect, player: Player, font):
    pygame.draw.rect(surface, DARK, rect)
    pygame.draw.rect(surface, WHITE, rect, 2)

    draw_text(
        surface,
        f"生命值：{player.hp} / {player.max_hp}",
        (rect.x + 10, rect.y + 20),
        RED,
        font,
    )
    draw_text(
        surface, f"攻擊力：{player.atk}", (rect.x + 10, rect.y + 50), YELLOW, font
    )
    draw_text(
        surface, f"防禦力：{player.defense}", (rect.x + 10, rect.y + 80), YELLOW, font
    )
    draw_text(
        surface,
        "道具：" + "  ".join(player.items),
        (rect.x + 10, rect.y + 120),
        WHITE,
        font,
    )


# 按鈕區（選項按鈕）
def draw_buttons(surface, button_rects, labels, font):
    for i, rect in enumerate(button_rects):
        pygame.draw.rect(surface, BLUE, rect)
        pygame.draw.rect(surface, WHITE, rect, 2)
        draw_wrapped_text(surface, labels[i], rect, font, WHITE)


# 額外功能：敵人資訊彈窗（暫未使用）
def draw_enemy_popup(surface, enemy, font):
    info_rect = pygame.Rect(100, 200, 280, 180)
    pygame.draw.rect(surface, GRAY, info_rect)
    pygame.draw.rect(surface, WHITE, info_rect, 2)

    draw_text(surface, "敵人資訊", (info_rect.x + 10, info_rect.y + 10), YELLOW, font)
    draw_text(
        surface,
        f"名稱：{enemy['name']}",
        (info_rect.x + 10, info_rect.y + 50),
        WHITE,
        font,
    )
    draw_text(
        surface,
        f"血量：{enemy['hp']} / {enemy['max_hp']}",
        (info_rect.x + 10, info_rect.y + 80),
        WHITE,
        font,
    )
    draw_text(
        surface,
        f"攻擊力：{enemy['atk']}",
        (info_rect.x + 10, info_rect.y + 110),
        WHITE,
        font,
    )
    draw_text(
        surface,
        f"描述：{enemy['desc']}",
        (info_rect.x + 10, info_rect.y + 140),
        WHITE,
        font,
    )
