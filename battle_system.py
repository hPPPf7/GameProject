"""Battle system module using a durability-based flow instead of HP/ATK/DEF."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Optional

import text_log
import sound_manager

# Durability model defaults
DEFAULT_ATTACK_CHANCE = 0.6
DEFAULT_ESCAPE_CHANCE = 0.5
DEFAULT_DURABILITY = 3
DEFAULT_MAX_TURNS = 3


@dataclass
class EnemyState:
    """Internal representation of an enemy in battle."""

    name: str
    # Legacy stats kept only for compatibility with saved data/story definitions.
    max_hp: int
    hp: int
    atk: int
    defense: int

    @classmethod
    def from_dict(cls, data: Dict) -> "EnemyState":
        return cls(
            name=data.get("name", "未知生物"),
            max_hp=int(data.get("hp", 1)),
            hp=int(data.get("hp", 1)),
            atk=int(data.get("atk", 0)),
            defense=int(data.get("def", 0)),
        )


def _ensure_battle_state(player: Dict) -> Dict:
    return player.setdefault("battle_state", {})


def start_battle(player: Dict, event: Dict) -> None:
    """Initialise battle state for the given event."""

    enemy_data = event.get("enemy")
    if not enemy_data:
        # Backwards compatibility with older story fields.
        enemy_data = {
            "name": event.get("enemy_name", "未知生物"),
            "hp": event.get("enemy_hp", 1),
            "atk": event.get("enemy_atk", 0),
            "def": event.get("enemy_def", 0),
        }

    state = _ensure_battle_state(player)
    enemy = EnemyState.from_dict(enemy_data)
    durability = int(event.get("battle_durability", DEFAULT_DURABILITY))
    max_turns = int(event.get("battle_max_turns", DEFAULT_MAX_TURNS))
    durability = durability if durability > 0 else DEFAULT_DURABILITY
    max_turns = max_turns if max_turns > 0 else DEFAULT_MAX_TURNS

    state.update(
        {
            "event_id": event.get("id"),
            "enemy": enemy,
            "active": True,
            "escaped": False,
            "victory": False,
            "defeat": False,
            "turn_count": 0,
            "attack_attempts": 0,
            "escape_attempts": 0,
            "max_turns": max_turns,
            "durability": durability,
            "max_durability": durability,
        }
    )

    text_log.add(f"戰鬥開始：{enemy.name}", category="system")
    text_log.add(f"可承受失敗次數：{state['durability']}", category="system")


def clear_battle_state(player: Dict) -> None:
    """Remove any cached battle state from the player."""

    if "battle_state" in player:
        player["battle_state"].clear()
        del player["battle_state"]


def get_battle_state(player: Dict) -> Optional[Dict]:
    state = player.get("battle_state")
    if not state:
        return None
    enemy = state.get("enemy")
    if enemy and isinstance(enemy, dict):
        # Convert legacy enemy dicts into EnemyState.
        state["enemy"] = EnemyState.from_dict(enemy)
    return state


def is_battle_active(player: Dict) -> bool:
    state = get_battle_state(player)
    return bool(state and state.get("active"))


def perform_battle_action(
    player: Dict, action: str, config: Optional[Dict] = None
) -> Dict:
    """Execute one turn of a durability-based battle and return the outcome."""

    config = config or {}
    state = get_battle_state(player)
    if not state or not state.get("active"):
        return {
            "messages": ["現在沒有正在進行的戰鬥。"],
            "battle_over": True,
            "player_damage": 0,
            "enemy_damage": 0,
        }

    enemy: EnemyState = state["enemy"]
    max_turns = max(state.get("max_turns", DEFAULT_MAX_TURNS), 1)
    durability = max(state.get("durability", DEFAULT_DURABILITY), 0)
    max_durability = max(state.get("max_durability", durability or DEFAULT_DURABILITY), 1)

    messages: list[str] = []
    battle_over = False
    victory = False
    escaped = False
    defeat = False
    durability_loss = 0

    state["turn_count"] = state.get("turn_count", 0) + 1

    if action == "attack":
        state["attack_attempts"] = state.get("attack_attempts", 0) + 1
        attempt = state["attack_attempts"]
        chance = float(config.get("attack_chance", DEFAULT_ATTACK_CHANCE))
        success = attempt >= max_turns or random.random() < chance
        sound_manager.play_sfx("attack")
        if success:
            messages.append(f"你擊倒了 {enemy.name}！")
            battle_over = True
            victory = True
            sound_manager.play_sfx("monster_death")
        else:
            durability_loss = 1
            durability = max(0, durability - durability_loss)
            messages.append("攻擊未能奏效，你的耐久下降。")
            messages.append(f"耐久 {durability}/{max_durability}")

    elif action == "escape":
        state["escape_attempts"] = state.get("escape_attempts", 0) + 1
        attempt = state["escape_attempts"]
        base_chance = float(config.get("escape_chance", DEFAULT_ESCAPE_CHANCE))
        incremental = max(0.0, 0.15 * (attempt - 1))
        chance = 1.0 if attempt >= max_turns else min(1.0, base_chance + incremental)
        if random.random() < chance:
            messages.append("你成功脫離戰鬥。")
            battle_over = True
            escaped = True
        else:
            durability_loss = 1
            durability = max(0, durability - durability_loss)
            messages.append("逃跑失敗，你耗費了體力。")
            messages.append(f"耐久 {durability}/{max_durability}")
            sound_manager.play_sfx("attack")

    else:
        durability_loss = 1
        durability = max(0, durability - durability_loss)
        messages.append("你猶豫不決，錯失時機。")
        messages.append(f"耐久 {durability}/{max_durability}")
        sound_manager.play_sfx("attack")

    if not battle_over and durability <= 0:
        battle_over = True
        defeat = True
        messages.append("你已經筋疲力竭，無法繼續戰鬥。")

    if battle_over:
        # 戰鬥結束後重置耐久，離開戰鬥時顯示為滿值
        durability = max_durability

    state["active"] = not battle_over
    state["victory"] = victory
    state["escaped"] = escaped
    state["defeat"] = defeat
    state["durability"] = durability
    state["max_durability"] = max_durability
    state["enemy"] = enemy

    return {
        "messages": messages,
        "battle_over": battle_over,
        "victory": victory,
        "escaped": escaped,
        "defeat": defeat,
        "durability_loss": durability_loss,
        "remaining_durability": durability,
        "turn_count": state["turn_count"],
        # Legacy keys kept for compatibility with callers.
        "player_damage": 0,
        "enemy_damage": 0,
    }
