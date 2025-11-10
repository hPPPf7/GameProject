"""Main entry point for the investigation diary game.

This script sets up pygame, loads assets, and enters the main event loop.
It coordinates the user interface, the event system, and player state.
It also handles game over: if the player's HP drops to zero the game
displays the final state, waits briefly, and then exits.
"""

import pygame
import sys
import text_log

# Initialise pygame before importing other modules that depend on fonts
pygame.init()
pygame.font.init()

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


# Window setup
screen = pygame.display.set_mode((512, 768))
pygame.display.set_caption("菜鳥調查隊日誌")
icon = pygame.image.load("assets/icon.png").convert_alpha()
pygame.display.set_icon(icon)
clock = pygame.time.Clock()

# Load background and logo images
start_bg = pygame.image.load("assets/start_background.png")
logo_image = pygame.image.load("assets/logo1.png").convert_alpha()
logo_image = pygame.transform.scale(logo_image, (300, 300))

# Player sprite
player_image = pygame.image.load("assets/player_idle.png").convert_alpha()
player_image = pygame.transform.scale(player_image, (96, 96))

current_enemy_image = None  # current enemy sprite for events

# Font
FONT = pygame.font.Font("assets/Cubic_11.ttf", 20)

# Start menu buttons
start_button = pygame.Rect(156, 600, 200, 50)
button_color = (70, 70, 70)
start_text = FONT.render("開始冒險", True, (255, 255, 255))
start_text_rect = start_text.get_rect(center=start_button.center)

exit_button = pygame.Rect(156, 660, 200, 50)
exit_text = FONT.render("離開遊戲", True, (255, 255, 255))
exit_text_rect = exit_text.get_rect(center=exit_button.center)

# Item usage configuration
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
        text_log.add(
            f"你使用了{item_name}，HP 回復 {heal_amount} 點。", category="system"
        )
        text_log.add(f"HP +{heal_amount} → {player['hp']}", category="system")
        text_log.scroll_to_bottom()
        return True

    text_log.add(f"{item_name} 暫時無法使用。", category="system")
    text_log.scroll_to_bottom()
    return False


# Initialise player state
player = init_player_state()

# Game state variables
game_state = "start_menu"
sub_state = "wait"
current_event = None

pending_clear_event = False
clear_event_timer = 0

# Main game loop
running = True
while running:
    # Clear screen
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
            elif game_state == "main_screen":
                areas = get_areas_for_mode(player)
                cinematic = areas.get("mode") == "cinematic"
                option_rects = get_option_rects(sub_state, current_event, player, areas)
                handled_click = False

                # Click "前進" area
                if (
                    sub_state == "wait"
                    and current_event is None
                    and option_rects
                    and option_rects[0].collidepoint(event.pos)
                ):
                    from event_manager import get_random_event

                    current_event = get_random_event(player=player)
                    if current_event:
                        text_log.start_event(current_event.get("id"))
                        text_log.add(current_event["text"])
                        text_log.scroll_to_bottom()
                        image_name = current_event.get("enemy_image")
                        if image_name:
                            current_enemy_image = pygame.image.load(
                                f"assets/{image_name}"
                            ).convert_alpha()
                            current_enemy_image = pygame.transform.scale(
                                current_enemy_image, (96, 96)
                            )
                        else:
                            current_enemy_image = None
                        if current_event.get("type") == "battle":
                            start_battle(player, current_event)
                    sub_state = "show_event"
                    handled_click = True
                # Click event option
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
                            # Immediate redraw to show choice
                            render_ui(
                                screen,
                                player,
                                FONT,
                                current_event,
                                sub_state,
                                player_image,
                                current_enemy_image,
                            )
                            pygame.display.flip()
                            result = chosen.get("result")
                            if result:
                                handle_event_result(player, result)
                                text_log.scroll_to_bottom()
                            # Redraw after applying result
                            render_ui(
                                screen,
                                player,
                                FONT,
                                current_event,
                                sub_state,
                                player_image,
                                current_enemy_image,
                            )
                            pygame.display.flip()
                            battle_continues = False
                            if current_event.get("type") == "battle":
                                battle_continues = is_battle_active(player)

                            if not battle_continues:
                                # Only advance progression when the current event is fully resolved
                                forced_event = post_event_update(player)
                                if forced_event:
                                    player["forced_event"] = forced_event
                            if battle_continues:
                                pending_clear_event = False
                                clear_event_timer = 0
                                sub_state = "show_event"
                            else:
                                # Mark event for clearing on next iteration
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
                                    player_image,
                                    current_enemy_image,
                                )
                                pygame.display.flip()
                            break
        elif event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            if UI_AREAS["log"].collidepoint((mouse_x, mouse_y)):
                if event.y > 0:
                    text_log.scroll_up()
                else:
                    text_log.scroll_down()

    # Check for game over (player death)
    if player.get("game_over"):
        # Display final state and death message
        render_ui(
            screen,
            player,
            FONT,
            current_event,
            sub_state,
            player_image,
            current_enemy_image,
        )
        pygame.display.flip()
        # Wait for two seconds to let the player see the message
        pygame.time.delay(2000)
        running = False
        continue

    # Render appropriate screen
    if game_state == "start_menu":
        screen.blit(start_bg, start_bg.get_rect(center=(256, 384)))
        screen.blit(logo_image, (100, 80))
        pygame.draw.rect(screen, button_color, start_button)
        screen.blit(start_text, start_text_rect)
        pygame.draw.rect(screen, button_color, exit_button)
        screen.blit(exit_text, exit_text_rect)
    elif game_state == "main_screen":
        render_ui(
            screen,
            player,
            FONT,
            current_event,
            sub_state,
            player_image,
            current_enemy_image,
        )
    pygame.display.flip()
    clock.tick(60)

    # Clear event after delay
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
