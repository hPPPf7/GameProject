from dataclasses import dataclass, field
from typing import Set, Dict, List


def init_player_state() -> Dict:
    """
    Initialize the player's state.

    This function returns a dictionary containing both visible and hidden
    attributes that control the game's logic.  See the README for more
    details on what each field represents.
    """
    return {
        # Visible stats
        "hp": 20,          # Health points
        "atk": 5,          # Attack power
        "def": 3,          # Defense power
        "inventory": [],   # Inventory list

        # Hidden values
        "fate": 50,        # Fate value controlling story direction
        "fate_history": [],
        "fate_path_locked": False,
        "fate_locked_band": None,
        "refusal_streak": 0,
        "flags": {},       # Arbitrary flags for conditional events
        "steps": 0,         # Number of steps taken (used for chapter advancement)
        "chapter": 1,
        "forced_event": None,
        "ending_prepared": False,
        "midband_counter": 0,
        "event_cooldowns": {},  # Per‑event cooldown counter
        "consumed_events": set(),

        # Game over flag – set to True when the player dies
        "game_over": False,
    }