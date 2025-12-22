from typing import Optional, NamedTuple, List

import pygame
import text_log

from paths import res_path
from battle_system import DEFAULT_DURABILITY


def is_cinematic_mode(player: dict) -> bool:
    """Return True when the UI should collapse into the cinematic layout."""
    if not player:
        return False
    flags = player.get("flags", {})
    return bool(flags.get("ending_cinematic") or player.get("intro_cinematic_active"))


# 定義介面區域的尺寸與位置：縮窄狀態區塊的寬度，並相應放寬選項區域，
# 加上邊距後整列總寬仍維持 448 像素。

STATUS_WIDTH = 200  # 較窄的狀態面板
GAP = 24  # 狀態與選項之間的水平間距
STATUS_X = 32
OPTIONS_X = STATUS_X + STATUS_WIDTH + GAP
OPTIONS_WIDTH = 448 - (OPTIONS_X - STATUS_X)

UI_AREAS = {
    "image": pygame.Rect(32, 16, 448, 299),
    "log": pygame.Rect(32, 331, 448, 256),
    "status": pygame.Rect(STATUS_X, 603, STATUS_WIDTH, 132),
    "options": [
        pygame.Rect(OPTIONS_X, 603 + i * 45, OPTIONS_WIDTH, 40) for i in range(3)
    ],
    "inventory_preview": pygame.Rect(32, 751, 448, 80),
}

# Updated layout: narrower status, wider options, longer log, and panels shifted down.
STATUS_WIDTH = 170
OPTIONS_X = STATUS_X + STATUS_WIDTH + GAP
OPTIONS_WIDTH = 448 - (OPTIONS_X - STATUS_X)

UI_AREAS = {
    "image": pygame.Rect(32, 16, 448, 299),
    "log": pygame.Rect(32, 331, 448, 256),
    "status": pygame.Rect(STATUS_X, 603, STATUS_WIDTH, 132),
    "options": [
        pygame.Rect(OPTIONS_X, 603 + i * 45, OPTIONS_WIDTH, 40) for i in range(3)
    ],
    "inventory_preview": pygame.Rect(32, 751, 448, 80),
}
UI_HEIGHT = UI_AREAS["inventory_preview"].bottom + 16

BACKGROUND_DIR = ("assets", "background")
DEFAULT_BACKGROUND = "starting_area.png"

# Cache scaled backgrounds so we only load and resize each file once.
_BACKGROUND_CACHE: dict[str, pygame.Surface] = {}


def _load_background(name: str) -> pygame.Surface:
    if not name:
        name = DEFAULT_BACKGROUND
    cached = _BACKGROUND_CACHE.get(name)
    if cached:
        return cached
    loaded: Optional[pygame.Surface] = None
    search_paths = [
        res_path(*BACKGROUND_DIR, name),
        res_path("assets", name),  # fallback for legacy locations
    ]
    for path in search_paths:
        try:
            loaded = pygame.image.load(path)
            break
        except (FileNotFoundError, pygame.error):
            continue
    if loaded is None:
        if name != DEFAULT_BACKGROUND:
            return _load_background(DEFAULT_BACKGROUND)
        fallback = pygame.Surface(UI_AREAS["image"].size)
        fallback.fill((20, 20, 20))
        _BACKGROUND_CACHE[name] = fallback
        return fallback
    scaled = pygame.transform.scale(loaded, UI_AREAS["image"].size)
    _BACKGROUND_CACHE[name] = scaled
    return scaled


def get_background_surface(name: Optional[str]) -> pygame.Surface:
    """Return the background surface for the given background name (cached)."""

    return _load_background(name or DEFAULT_BACKGROUND)


ITEM_ICON_DIR = ("assets", "items")
ITEM_ICON_FILES = {
    "治療藥水": "health_potion.png",
    "奇怪的石頭": "weird_rock.png",
    "草織護符": "grasswove_talisman.png",
    "塗黑報告": "redacted_report.png",
}

_ITEM_ICON_CACHE: dict[str, Optional[pygame.Surface]] = {}
_SCALED_ICON_CACHE: dict[tuple[str, int], pygame.Surface] = {}



class InventorySlot(NamedTuple):
    rect: pygame.Rect
    item_name: Optional[str]
    icon: Optional[pygame.Surface]
    label: Optional[str]
    item_index: Optional[int]


def load_item_icon(name: str) -> Optional[pygame.Surface]:
    filename = ITEM_ICON_FILES.get(name)
    if not filename:
        return None

    if name not in _ITEM_ICON_CACHE:
        cached_icon: Optional[pygame.Surface] = None
        search_paths = [
            res_path(*ITEM_ICON_DIR, filename),
            res_path("assets", filename),  # fallback for legacy locations
        ]
        for path in search_paths:
            try:
                cached_icon = pygame.image.load(path).convert_alpha()
                break
            except (FileNotFoundError, pygame.error):
                continue
        _ITEM_ICON_CACHE[name] = cached_icon
    return _ITEM_ICON_CACHE.get(name)


def get_scaled_item_icon(name: str, size: int) -> Optional[pygame.Surface]:
    if size <= 0:
        return None
    key = (name, size)
    if key in _SCALED_ICON_CACHE:
        return _SCALED_ICON_CACHE[key]

    base_icon = load_item_icon(name)
    if not base_icon:
        return None

    scaled = pygame.transform.smoothscale(base_icon, (size, size))
    _SCALED_ICON_CACHE[key] = scaled
    return scaled



COLORS = {
    "image": (40, 80, 40),
    "log": (30, 30, 30),
    "status": (40, 40, 80),
    "option": (60, 60, 60),
    "option_disabled": (40, 40, 40),
    "option_hover": (100, 100, 100),
    "inventory": (90, 90, 40),
    "inventory_slot": (120, 120, 70),
    "inventory_slot_border": (180, 180, 120),
}


def get_areas_for_mode(player: dict) -> dict:
    """Return the rectangle layout for the current UI mode."""

    image_rect = UI_AREAS["image"].copy()
    log_rect = UI_AREAS["log"].copy()

    if is_cinematic_mode(player):
        transition = player.get("layout_transition") if player else None
        base_height = UI_AREAS["inventory_preview"].bottom + 16
        image_height = int(image_rect.width * 2 / 3)
        log_height = 160
        gap = 16
        total_height = image_height + gap + log_height
        top_y = max(16, (base_height - total_height) // 2)
        cinematic_image = pygame.Rect(
            image_rect.x,
            top_y,
            image_rect.width,
            image_height,
        )
        cinematic_log = pygame.Rect(
            log_rect.x,
            cinematic_image.bottom + gap,
            log_rect.width,
            log_height,
        )
        image_rect = cinematic_image
        log_rect = cinematic_log

        if transition:
            progress = float(transition.get("progress", 0.0))
            progress = max(0.0, min(1.0, progress))
            normal_image = UI_AREAS["image"].copy()
            normal_log = UI_AREAS["log"].copy()

            def _lerp(a: int, b: int, t: float) -> int:
                return int(round(a + (b - a) * t))

            image_rect = pygame.Rect(
                _lerp(normal_image.x, cinematic_image.x, progress),
                _lerp(normal_image.y, cinematic_image.y, progress),
                _lerp(normal_image.width, cinematic_image.width, progress),
                _lerp(normal_image.height, cinematic_image.height, progress),
            )
            log_rect = pygame.Rect(
                _lerp(normal_log.x, cinematic_log.x, progress),
                _lerp(normal_log.y, cinematic_log.y, progress),
                _lerp(normal_log.width, cinematic_log.width, progress),
                _lerp(normal_log.height, cinematic_log.height, progress),
            )
        left_x = STATUS_X
        right_x = STATUS_X + STATUS_WIDTH + GAP + OPTIONS_WIDTH
        options_rect = pygame.Rect(
            left_x,
            log_rect.bottom + 10,
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
        "inventory_preview": UI_AREAS["inventory_preview"].copy(),
        "mode": "normal",
    }


def _get_durability_display(player: dict) -> tuple[int, int]:
    """
    Return (current, max) durability for display.

    During battle, read from battle_state; otherwise show full default durability.
    """
    if not player:
        return DEFAULT_DURABILITY, DEFAULT_DURABILITY

    battle_state = player.get("battle_state") or {}
    if battle_state:
        current = int(battle_state.get("durability", DEFAULT_DURABILITY))
        maximum = int(battle_state.get("max_durability", DEFAULT_DURABILITY))
        if maximum <= 0:
            maximum = DEFAULT_DURABILITY
        current = max(0, min(current, maximum))
        return current, maximum

    return DEFAULT_DURABILITY, DEFAULT_DURABILITY


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

    # 一般模式
    option_rects = [rect.copy() for rect in areas["options_rects"]]
    if sub_state == "show_event" and current_event:
        if current_event.get("type") != "battle":
            status_rect = areas["status_rect"]
            full_left = status_rect.x
            full_right = option_rects[-1].right if option_rects else status_rect.right
            expanded = []
            for rect in option_rects:
                expanded.append(
                    pygame.Rect(
                        full_left,
                        rect.y,
                        full_right - full_left,
                        rect.height,
                    )
                )
            return expanded
        return option_rects

    full_rect = option_rects[0].unionall(option_rects)
    if not (current_event and current_event.get("type") == "battle"):
        status_rect = areas["status_rect"]
        full_rect = pygame.Rect(
            status_rect.x,
            full_rect.y,
            full_rect.right - status_rect.x,
            full_rect.height,
        )
    return [full_rect]


def get_inventory_slots(
    player: dict,
    areas: Optional[dict] = None,
    slot_count: int = 6,
) -> List[InventorySlot]:
    """Return the rectangles and display info for inventory slots."""

    areas = areas or get_areas_for_mode(player)
    if areas.get("mode") != "normal":
        return []

    slot_count = max(1, slot_count)
    inventory_preview_rect = areas["inventory_preview"]
    min_gap = 3
    desired_gap = 6
    side_padding = 16
    vertical_padding = 10

    slot_size = max(1, inventory_preview_rect.height - vertical_padding * 2)

    gap = desired_gap
    available_width = inventory_preview_rect.width - side_padding * 2
    total_width = slot_count * slot_size + (slot_count - 1) * gap

    if total_width > available_width:
        gap_needed = (available_width - slot_count * slot_size) / max(1, slot_count - 1)
        if gap_needed < gap:
            gap = max(min_gap, gap_needed)
        total_width = slot_count * slot_size + (slot_count - 1) * gap

        if total_width > available_width:
            slot_size = max(
                1,
                (available_width - (slot_count - 1) * gap) / slot_count,
            )
            total_width = slot_count * slot_size + (slot_count - 1) * gap

    horizontal_offset = max(0, (inventory_preview_rect.width - total_width) / 2)
    vertical_margin = (inventory_preview_rect.height - slot_size) / 2

    items = list(player.get("inventory", []))
    total_items = len(items)
    icon_size = int(max(1, slot_size - 12))

    slots: List[InventorySlot] = []
    for index in range(slot_count):
        slot_x = (
            inventory_preview_rect.x + horizontal_offset + index * (slot_size + gap)
        )
        slot_y = inventory_preview_rect.y + vertical_margin
        slot_rect = pygame.Rect(
            round(slot_x),
            round(slot_y),
            int(slot_size),
            int(slot_size),
        )

        item_name: Optional[str] = None
        icon_surface: Optional[pygame.Surface] = None
        label: Optional[str] = None
        item_index: Optional[int] = None

        if index < total_items:
            if index == slot_count - 1 and total_items > slot_count:
                remaining = total_items - (slot_count - 1)
                label = f"+{remaining}"
            else:
                item_name = items[index]
                icon_surface = get_scaled_item_icon(item_name, icon_size)
                item_index = index
        slots.append(
            InventorySlot(slot_rect, item_name, icon_surface, label, item_index)
        )

    return slots


def render_ui(
    screen,
    player,
    font,
    current_event=None,
    background_name: Optional[str] = None,
    sub_state="wait",
    player_image=None,
    enemy_image=None,
    player_position=None,
    enemy_position=None,
):
    """
    Draw the main UI components: image area, log area, status panel, options,
    and inventory.  This version wraps log text so it never spills out of
    the log rectangle and uses the new status/options widths.
    """
    mouse_pos = pygame.mouse.get_pos()
    areas = get_areas_for_mode(player)
    mode = areas.get("mode")
    typewriter_active = text_log.is_typewriter_animating()
    ending_cinematic = is_cinematic_mode(player)

    # 圖像區域（裁切到背景範圍，避免角色或敵人超出）
    old_clip = screen.get_clip()
    screen.set_clip(areas["image"])
    background = get_background_surface(background_name)
    screen.blit(background, areas["image"].topleft)

    # 若有傳入立繪則繪製玩家與敵人（結局動畫不繪製）
    player_bottom = areas["image"].bottom - 16
    if player_image and not ending_cinematic:
        if player_position:
            player_pos = (int(player_position[0]), int(player_position[1]))
        else:
            player_height = player_image.get_height()
            player_pos = (
                areas["image"].x + 32,
                areas["image"].bottom - player_height - 16,
            )
        player_bottom = player_pos[1] + player_image.get_height()
        screen.blit(player_image, player_pos)
    enemy_rect: Optional[pygame.Rect] = None
    if enemy_image and not ending_cinematic:
        enemy_rect = enemy_image.get_rect()
        if enemy_position:
            enemy_rect.topleft = (int(enemy_position[0]), int(enemy_position[1]))
        else:
            enemy_rect.x = areas["image"].right - enemy_rect.width - 32
            enemy_rect.bottom = player_bottom
        screen.blit(enemy_image, enemy_rect.topleft)
    # 恢復全局裁切，後續 UI 不受限
    screen.set_clip(old_clip)

    # 繪製日誌區域
    pygame.draw.rect(screen, COLORS["log"], areas["log"])
    # 組出換行後的日誌內容
    max_width = areas["log"].width - 16  # 扣除邊距
    visible_line_count = max(1, (areas["log"].height - 16) // 24)
    visible_lines = text_log.get_visible_lines(
        font, max_width, visible_lines=visible_line_count
    )
    color_map = {
        "narration": (255, 255, 255),
        "choice": (180, 200, 255),
        "system": (255, 180, 80),
        "event_header": (120, 220, 200),
        "spacer": (255, 255, 255),
    }
    for i, (line, category) in enumerate(visible_lines):
        color = color_map.get(category, (255, 255, 255))
        draw_text(
            screen, line, areas["log"], font, center=False, line_offset=i, color=color
        )

    # 繪製狀態面板（電影模式略過；非戰鬥事件隱藏）
    if mode == "normal":
        hide_status = not (current_event and current_event.get("type") == "battle")
        if not hide_status:
            status_rect = areas["status_rect"]
            pygame.draw.rect(screen, COLORS["status"], status_rect)

            current_durability, max_durability = _get_durability_display(player)
            rows = [f"耐久 {current_durability}/{max_durability}"]

            row_height = 32
            padding_x = 12
            padding_y = 12
            row_spacing = 8
            text_left = status_rect.x + padding_x
            text_width = status_rect.width - (text_left - status_rect.x) - padding_x

            for i, label in enumerate(rows):
                row_top = status_rect.y + padding_y + i * (row_height + row_spacing)
                text_rect = pygame.Rect(
                    text_left,
                    row_top,
                    text_width,
                    row_height,
                )
                draw_text(
                    screen,
                    label,
                    text_rect,
                    font,
                    center=False,
                    line_offset=0,
                )

    option_rects = get_option_rects(sub_state, current_event, player, areas)

    # 繪製選項
    if player.get("intro_cinematic_active"):
        option_rects = []
    if sub_state == "wait":
        if not option_rects:
            wait_rect = None
        else:
            wait_rect = option_rects[0]
        if not wait_rect:
            pass
        else:
            can_interact = not typewriter_active
            is_hover = wait_rect.collidepoint(mouse_pos) and can_interact
            color = (
                COLORS["option_disabled"]
                if not can_interact
                else COLORS["option_hover"]
                if is_hover
                else COLORS["option"]
            )
            pygame.draw.rect(screen, color, wait_rect)
            if can_interact:
                draw_text(screen, "前進", wait_rect, font, center=True)
    elif sub_state == "show_event" and current_event:
        options = current_event.get("options", [])
        show_option_text = not typewriter_active
        for i, rect in enumerate(option_rects):
            is_hover = rect.collidepoint(mouse_pos) and show_option_text
            if i < len(options):
                color = (
                    COLORS["option_disabled"]
                    if typewriter_active
                    else COLORS["option_hover"]
                    if is_hover
                    else COLORS["option"]
                )
                pygame.draw.rect(screen, color, rect)
                if show_option_text:
                    option_text = options[i]["text"]
                    draw_text(screen, option_text, rect, font, center=True)
            else:
                pygame.draw.rect(screen, COLORS["option_disabled"], rect)
                if show_option_text:
                    draw_text(screen, "……", rect, font, center=True)
        if typewriter_active:
            for rect in option_rects:
                pygame.draw.rect(screen, COLORS["option_disabled"], rect)

    if mode == "normal":
        # 繪製固定六格的背包欄
        inventory_preview_rect = areas["inventory_preview"]
        pygame.draw.rect(screen, COLORS["inventory"], inventory_preview_rect)
        for slot in get_inventory_slots(player, areas):
            pygame.draw.rect(screen, COLORS["inventory_slot"], slot.rect)
            pygame.draw.rect(screen, COLORS["inventory_slot_border"], slot.rect, 2)
            if slot.icon:
                icon_rect = slot.icon.get_rect(center=slot.rect.center)
                screen.blit(slot.icon, icon_rect)
            elif slot.label:
                draw_text(screen, slot.label, slot.rect, font, center=True)


def draw_text(
    screen, text, rect, font, center=False, line_offset=0, color=(255, 255, 255)
):
    """
    Render a single line of text inside the given rectangle.  If ``center``
    is True the text is centred; otherwise it is drawn with a small
    margin and ``line_offset`` controls vertical offset for multiple lines.
    """
    rendered = font.render(text, True, color)
    if center:
        text_rect = rendered.get_rect(center=rect.center)
    else:
        text_rect = rendered.get_rect(
            topleft=(rect.x + 8, rect.y + 8 + line_offset * 24)
        )
    screen.blit(rendered, text_rect)
