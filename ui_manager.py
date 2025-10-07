import pygame
import text_log

# Define UI area dimensions and positions.  We shrink the status block
# horizontally and widen the options area accordingly.  The total width of
# the row remains 448 pixels (with margins).

STATUS_WIDTH = 200  # narrower status panel
GAP = 24            # horizontal gap between status and options
STATUS_X = 32
OPTIONS_X = STATUS_X + STATUS_WIDTH + GAP
OPTIONS_WIDTH = 448 - (OPTIONS_X - STATUS_X)

UI_AREAS = {
    "image": pygame.Rect(32, 32, 448, 200),
    "log": pygame.Rect(32, 244, 448, 230),
    "status": pygame.Rect(STATUS_X, 488, STATUS_WIDTH, 132),
    "options": [
        pygame.Rect(OPTIONS_X, 488 + i * 45, OPTIONS_WIDTH, 40) for i in range(3)
    ],
    "inventory_bar": pygame.Rect(32, 712, 448, 24),
    "inventory_preview": pygame.Rect(32, 656, 448, 56),
    "inventory_full": pygame.Rect(32, 524, 448, 132),
}

starting_image = pygame.image.load("assets/starting_area.png")
starting_image = pygame.transform.scale(starting_image, UI_AREAS["image"].size)

COLORS = {
    "image": (40, 80, 40),
    "log": (30, 30, 30),
    "status": (40, 40, 80),
    "option": (60, 60, 60),
    "option_disabled": (40, 40, 40),
    "option_hover": (100, 100, 100),
    "inventory": (90, 90, 40),
    "inventory_bar": (110, 110, 110),
}


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """
    Break ``text`` into a list of strings so that each line fits within
    ``max_width`` pixels.  Uses a simple character‑by‑character approach to
    accommodate languages without spaces.  Preserves the order of characters.
    """
    if not text:
        return [""]
    lines: list[str] = []
    current: str = ""
    for ch in text:
        # If adding this character would exceed the allowed width, start a new line
        if font.size(current + ch)[0] > max_width and current:
            lines.append(current)
            current = ch
        else:
            current += ch
    if current:
        lines.append(current)
    return lines


def draw_main_ui(screen, player, font, current_event=None, sub_state="wait",
                  player_image=None, enemy_image=None, inventory_open=False):
    """
    Draw the main UI components: image area, log area, status panel, options,
    and inventory.  This version wraps log text so it never spills out of
    the log rectangle and uses the new status/options widths.
    """
    mouse_pos = pygame.mouse.get_pos()

    # Image area
    screen.blit(starting_image, UI_AREAS["image"].topleft)

    # Draw player and enemy sprites if provided
    if player_image:
        screen.blit(player_image, (UI_AREAS["image"].x + 32, UI_AREAS["image"].y + 80))
    if enemy_image:
        enemy_pos = (UI_AREAS["image"].right - 96 - 32, UI_AREAS["image"].y + 80)
        screen.blit(enemy_image, enemy_pos)

    # Draw log area
    pygame.draw.rect(screen, COLORS["log"], UI_AREAS["log"])
    # Build wrapped log lines
    raw_logs = text_log.get_visible_logs()
    wrapped_lines: list[str] = []
    max_width = UI_AREAS["log"].width - 16  # account for margins
    for entry in raw_logs:
        wrapped_lines.extend(wrap_text(entry, font, max_width))
    # Only display the last 9 visual lines
    visible_lines = wrapped_lines[-9:]
    for i, line in enumerate(visible_lines):
        # Highlight any lines mentioning key stats
        highlight = any(word in line for word in ["HP", "ATK", "DEF", "fate"])
        color = (255, 80, 80) if highlight else (255, 255, 255)
        draw_text(screen, line, UI_AREAS["log"], font, center=False, line_offset=i, color=color)

    # Draw status panel
    pygame.draw.rect(screen, COLORS["status"], UI_AREAS["status"])
    lines = [
        f"HP: {player['hp']}",
        f"ATK: {player['atk']}",
        f"DEF: {player['def']}"
    ]
    for i, line in enumerate(lines):
        draw_text(screen, line, UI_AREAS["status"], font, center=False, line_offset=i)

    # Draw options
    if sub_state == "wait":
        full_rect = UI_AREAS["options"][0].unionall(UI_AREAS["options"])
        is_hover = full_rect.collidepoint(mouse_pos)
        color = COLORS["option_hover"] if is_hover else COLORS["option"]
        pygame.draw.rect(screen, color, full_rect)
        draw_text(screen, "前進", full_rect, font, center=True)
    elif sub_state == "show_event" and current_event:
        for i, rect in enumerate(UI_AREAS["options"]):
            is_hover = rect.collidepoint(mouse_pos)
            if i < len(current_event.get("options", [])):
                color = COLORS["option_hover"] if is_hover else COLORS["option"]
                pygame.draw.rect(screen, color, rect)
                option_text = current_event["options"][i]["text"]
                draw_text(screen, option_text, rect, font, center=True)
            else:
                pygame.draw.rect(screen, COLORS["option_disabled"], rect)
                draw_text(screen, "……", rect, font, center=True)

    # Draw inventory bar
    bar_y = 712
    inventory_bar_rect = pygame.Rect(32, bar_y, 448, 24)
    pygame.draw.rect(screen, COLORS["inventory_bar"], inventory_bar_rect)
    symbol = "▲" if inventory_open else "▼"
    draw_text(screen, f"{symbol} 背包（共 {len(player['inventory'])} 項）", inventory_bar_rect, font, center=True)

    # Expanded inventory view
    if inventory_open:
        items = player["inventory"]
        max_visible_items = 5
        item_height = 24
        total_items = len(items)
        scroll_offset = player.get("inventory_scroll", 0)
        visible_items = items[scroll_offset:scroll_offset + max_visible_items]
        visible_count = len(visible_items)
        padding = 7
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
        # Scroll hint
        if total_items > max_visible_items:
            if visible_count < max_visible_items:
                draw_text(screen, "（使用滑鼠滾輪瀏覽）", inventory_full_rect, font, center=False, line_offset=visible_count)
    else:
        # Collapsed preview
        inventory_preview_rect = pygame.Rect(32, bar_y - 56, 448, 56)
        pygame.draw.rect(screen, COLORS["inventory"], inventory_preview_rect)
        preview = "、".join(player["inventory"][:2])
        if len(player["inventory"]) > 2:
            preview += "、……"
        elif not player["inventory"]:
            preview = "（目前無道具）"
        draw_text(screen, preview, inventory_preview_rect, font, center=False)


def draw_text(screen, text, rect, font, center=False, line_offset=0, color=(255, 255, 255)):
    """
    Render a single line of text inside the given rectangle.  If ``center``
    is True the text is centred; otherwise it is drawn with a small
    margin and ``line_offset`` controls vertical offset for multiple lines.
    """
    rendered = font.render(text, True, color)
    if center:
        text_rect = rendered.get_rect(center=rect.center)
    else:
        text_rect = rendered.get_rect(topleft=(rect.x + 8, rect.y + 8 + line_offset * 24))
    screen.blit(rendered, text_rect)