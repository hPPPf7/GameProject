from typing import Optional

import pygame
import text_log

def is_cinematic_mode(player: dict) -> bool:
    """Return True when the UI should collapse into the cinematic layout."""
    flags = player.get("flags", {}) if player else {}
    return not flags.get("mission_briefed", False)

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


def get_areas_for_mode(player: dict) -> dict:
    """Return the rectangle layout for the current UI mode."""

    image_rect = UI_AREAS["image"].copy()
    log_rect = UI_AREAS["log"].copy()

    if is_cinematic_mode(player):
        left_x = STATUS_X
        right_x = STATUS_X + STATUS_WIDTH + GAP + OPTIONS_WIDTH
        options_rect = pygame.Rect(
            left_x,
            log_rect.bottom + 16,
            right_x - left_x,
            240,
        )
        return {
            "image": image_rect,
            "log": log_rect,
            "options_rect": options_rect,
            "mode": "cinematic",
        }

    return {
        "image": image_rect,
        "log": log_rect,
        "status_rect": UI_AREAS["status"].copy(),
        "options_rects": [rect.copy() for rect in UI_AREAS["options"]],
        "inventory_bar": UI_AREAS["inventory_bar"].copy(),
        "inventory_preview": UI_AREAS["inventory_preview"].copy(),
        "inventory_full": UI_AREAS["inventory_full"].copy(),
        "mode": "normal",
    }


def get_option_rects(
    sub_state: str,
    current_event,
    player: dict,
    areas: Optional[dict] = None,
) -> list[pygame.Rect]:
    """Return the list of option rectangles for the current UI state."""

    areas = areas or get_areas_for_mode(player)
    mode = areas.get("mode")

    if mode == "cinematic":
        base_rect = areas["options_rect"].copy()
        if sub_state == "show_event" and current_event:
            options = current_event.get("options", [])
            count = max(len(options), 1)
            height = base_rect.height // count
            rects: list[pygame.Rect] = []
            for i in range(count):
                rect = pygame.Rect(
                    base_rect.x,
                    base_rect.y + i * height,
                    base_rect.width,
                    height,
                )
                if i == count - 1:
                    rect.height = base_rect.bottom - rect.y
                rects.append(rect)
            return rects
        return [base_rect]

    # Normal mode
    option_rects = [rect.copy() for rect in areas["options_rects"]]
    if sub_state == "show_event" and current_event:
        return option_rects

    full_rect = option_rects[0].unionall(option_rects)
    return [full_rect]


def render_ui(
    screen,
    player,
    font,
    current_event=None,
    sub_state="wait",
    player_image=None,
    enemy_image=None,
    inventory_open=False,
):
    """
    Draw the main UI components: image area, log area, status panel, options,
    and inventory.  This version wraps log text so it never spills out of
    the log rectangle and uses the new status/options widths.
    """
    mouse_pos = pygame.mouse.get_pos()
    areas = get_areas_for_mode(player)
    mode = areas.get("mode")

    # Image area
    screen.blit(starting_image, areas["image"].topleft)

    # Draw player and enemy sprites if provided
    if player_image:
        screen.blit(player_image, (areas["image"].x + 32, areas["image"].y + 80))
    if enemy_image:
        enemy_pos = (areas["image"].right - 96 - 32, areas["image"].y + 80)
        screen.blit(enemy_image, enemy_pos)

    # Draw log area
    pygame.draw.rect(screen, COLORS["log"], areas["log"])
    # Build wrapped log lines
    raw_logs = text_log.get_visible_logs()
    wrapped_lines: list[tuple[str, str]] = []
    max_width = areas["log"].width - 16  # account for margins
    for entry in raw_logs:
        lines = wrap_text(entry.text, font, max_width) if entry.text else [""]
        wrapped_lines.extend((line, entry.category) for line in lines)
    # Only display the last 9 visual lines
    visible_lines = wrapped_lines[-9:]
    color_map = {
        "narration": (255, 255, 255),
        "choice": (180, 200, 255),
        "system": (255, 180, 80),
        "event_header": (120, 220, 200),
        "spacer": (255, 255, 255),
    }
    for i, (line, category) in enumerate(visible_lines):
        color = color_map.get(category, (255, 255, 255))
        draw_text(screen, line, areas["log"], font, center=False, line_offset=i, color=color)

    # Draw status panel (skip in cinematic mode)
    if mode == "normal":
        pygame.draw.rect(screen, COLORS["status"], areas["status_rect"])
        lines = [
            f"HP: {player['hp']}",
            f"ATK: {player['atk']}",
            f"DEF: {player['def']}"
        ]
        for i, line in enumerate(lines):
            draw_text(screen, line, areas["status_rect"], font, center=False, line_offset=i)

    option_rects = get_option_rects(sub_state, current_event, player, areas)

    # Draw options
    if sub_state == "wait":
        wait_rect = option_rects[0]
        is_hover = wait_rect.collidepoint(mouse_pos)
        color = COLORS["option_hover"] if is_hover else COLORS["option"]
        pygame.draw.rect(screen, color, wait_rect)
        draw_text(screen, "前進", wait_rect, font, center=True)
    elif sub_state == "show_event" and current_event:
        options = current_event.get("options", [])
        for i, rect in enumerate(option_rects):
            is_hover = rect.collidepoint(mouse_pos)
            if i < len(options):
                color = COLORS["option_hover"] if is_hover else COLORS["option"]
                pygame.draw.rect(screen, color, rect)
                option_text = options[i]["text"]
                draw_text(screen, option_text, rect, font, center=True)
            else:
                pygame.draw.rect(screen, COLORS["option_disabled"], rect)
                draw_text(screen, "……", rect, font, center=True)

    if mode == "normal":
        # Draw inventory bar
        inventory_bar_rect = areas["inventory_bar"]
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
            if total_items == 0:
                empty_rect = pygame.Rect(
                    inventory_bar_rect.x,
                    inventory_bar_rect.y - 32,
                    inventory_bar_rect.width,
                    32,
                )
                pygame.draw.rect(screen, COLORS["inventory"], empty_rect)
                draw_text(screen, "（目前無道具）", empty_rect, font, center=False)
            else:
                content_height = visible_count * item_height + padding
                inventory_full_rect = pygame.Rect(
                    inventory_bar_rect.x,
                    inventory_bar_rect.y - content_height,
                    inventory_bar_rect.width,
                    content_height,
                )
                pygame.draw.rect(screen, COLORS["inventory"], inventory_full_rect)
                for i, item in enumerate(visible_items):
                    draw_text(screen, f"- {item}", inventory_full_rect, font, center=False, line_offset=i)
                if total_items > max_visible_items and visible_count < max_visible_items:
                    draw_text(
                        screen,
                        "（使用滑鼠滾輪瀏覽）",
                        inventory_full_rect,
                        font,
                        center=False,
                        line_offset=visible_count,
                    )
            if total_items == 0:
                pass
            elif total_items > max_visible_items:
                hint_rect = pygame.Rect(
                    inventory_bar_rect.x,
                    inventory_bar_rect.y - 24,
                    inventory_bar_rect.width,
                    24,
                )
                draw_text(screen, "（使用滑鼠滾輪瀏覽）", hint_rect, font, center=False)
        else:
            # Collapsed preview
            inventory_preview_rect = areas["inventory_preview"]
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