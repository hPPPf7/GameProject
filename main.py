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

from ui_manager import draw_main_ui, UI_AREAS
from player_state import init_player_state
from event_result_handler import handle_event_result
from fate_system import post_event_update


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


# Initialise player state
player = init_player_state()
inventory_open = False

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
                full_rect = UI_AREAS["options"][0].unionall(UI_AREAS["options"])

                # Click inventory bar to toggle
                inventory_bar_rect = pygame.Rect(32, 712, 448, 24)
                if inventory_bar_rect.collidepoint(event.pos):
                    inventory_open = not inventory_open
                # Click "前進" area
                if sub_state == "wait" and current_event is None and full_rect.collidepoint(event.pos):
                    from event_manager import get_random_event
                    current_event = get_random_event(player=player)
                    if current_event:
                        text_log.add(current_event["text"])
                        text_log.scroll_to_bottom()
                        image_name = current_event.get("enemy_image")
                        if image_name:
                            current_enemy_image = pygame.image.load(f"assets/{image_name}").convert_alpha()
                            current_enemy_image = pygame.transform.scale(current_enemy_image, (96, 96))
                        else:
                            current_enemy_image = None
                    sub_state = "show_event"
                # Click event option
                elif sub_state == "show_event" and current_event and "options" in current_event:
                    for i, rect in enumerate(UI_AREAS["options"]):
                        if i >= len(current_event["options"]):
                            continue
                        if rect.collidepoint(event.pos):
                            chosen = current_event["options"][i]
                            text_log.add(f"你選擇了：{chosen['text']}")
                            text_log.scroll_to_bottom()
                            # Immediate redraw to show choice
                            draw_main_ui(screen, player, FONT, current_event, sub_state, player_image, current_enemy_image, inventory_open)
                            pygame.display.flip()
                            result = chosen.get("result")
                            if result:
                                handle_event_result(player, result)
                                text_log.scroll_to_bottom()
                            # Check for chapter/fate updates
                            forced_event = post_event_update(player)
                            if forced_event:
                                player["forced_event"] = forced_event
                            # Redraw after applying result
                            draw_main_ui(screen, player, FONT, current_event, sub_state, player_image, current_enemy_image, inventory_open)
                            pygame.display.flip()
                            # Mark event for clearing on next iteration
                            pending_clear_event = True
                            clear_event_timer = 1
                            sub_state = "after_result"
                            break
        elif event.type == pygame.MOUSEWHEEL:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            if UI_AREAS["log"].collidepoint((mouse_x, mouse_y)):
                if event.y > 0:
                    text_log.scroll_up()
                else:
                    text_log.scroll_down()
            elif inventory_open:
                max_scroll = max(len(player["inventory"]) - 5, 0)
                if event.y > 0:
                    player["inventory_scroll"] = max(player["inventory_scroll"] - 1, 0)
                elif event.y < 0:
                    player["inventory_scroll"] = min(player["inventory_scroll"] + 1, max_scroll)

    # Check for game over (player death)
    if player.get("game_over"):
        # Display final state and death message
        draw_main_ui(screen, player, FONT, current_event, sub_state, player_image, current_enemy_image, inventory_open)
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
        draw_main_ui(screen, player, FONT, current_event, sub_state, player_image, current_enemy_image, inventory_open)
    pygame.display.flip()
    clock.tick(60)

    # Clear event after delay
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