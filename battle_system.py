"""Battle system module for handling combat events."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Optional

import text_log


@dataclass
class EnemyState:
    """Internal representation of an enemy in battle."""

    name: str
    max_hp: int
    hp: int
    atk: int
    defense: int

    @classmethod
    def from_dict(cls, data: Dict) -> "EnemyState":
        return cls(
            name=data.get("name", "未知怪物"),
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
        # Fallback to legacy fields to avoid crashing if data is incomplete
        enemy_data = {
            "name": event.get("enemy_name", "未知怪物"),
            "hp": event.get("enemy_hp", 1),
            "atk": event.get("enemy_atk", 0),
            "def": event.get("enemy_def", 0),
        }

    state = _ensure_battle_state(player)
    enemy = EnemyState.from_dict(enemy_data)
    state.update(
        {
            "event_id": event.get("id"),
            "enemy": enemy,
            "active": True,
            "escaped": False,
            "victory": False,
        }
    )

    text_log.add(
        f"戰鬥開始：{enemy.name} (HP {enemy.hp}, ATK {enemy.atk}, DEF {enemy.defense})",
        category="system",
    )


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
        # Normalise legacy storage to EnemyState
        state["enemy"] = EnemyState.from_dict(enemy)
    return state


def is_battle_active(player: Dict) -> bool:
    state = get_battle_state(player)
    return bool(state and state.get("active"))


def calculate_damage(attacker_atk: int, defender_def: int) -> int:
    """Basic damage formula that always deals at least 1 damage."""

    return max(1, attacker_atk - defender_def)


def perform_battle_action(
    player: Dict, action: str, config: Optional[Dict] = None
) -> Dict:
    """Execute one turn of battle and return the outcome."""

    config = config or {}
    state = get_battle_state(player)
    if not state or not state.get("active"):
        return {
            "messages": ["目前沒有正在進行的戰鬥。"],
            "battle_over": True,
            "player_damage": 0,
            "enemy_damage": 0,
        }

    enemy: EnemyState = state["enemy"]
    player_atk = int(player.get("atk", 0))
    player_def = int(player.get("def", 0))

    messages: list[str] = []
    player_damage = 0
    enemy_damage = 0
    battle_over = False
    victory = False
    escaped = False

    if action == "attack":
        enemy_damage = calculate_damage(player_atk, enemy.defense)
        enemy.hp = max(0, enemy.hp - enemy_damage)
        messages.append(f"你對{enemy.name}造成 {enemy_damage} 點傷害！")
        messages.append(f"{enemy.name} 剩餘 {enemy.hp}/{enemy.max_hp} HP。")

        if enemy.hp <= 0:
            messages.append(f"{enemy.name} 被擊倒了！")
            battle_over = True
            victory = True
        else:
            # Counter attack
            base_damage = calculate_damage(enemy.atk, player_def)
            player_damage = base_damage
            messages.append(f"{enemy.name} 反擊，對你造成 {player_damage} 點傷害！")

    elif action == "defend":
        bonus = int(config.get("defense_bonus", player_def))
        effective_def = player_def + bonus
        base_damage = max(0, enemy.atk - effective_def)
        player_damage = base_damage
        messages.append(f"你專注防禦，減少了 {bonus} 點傷害。")
        if player_damage > 0:
            messages.append(f"{enemy.name} 仍造成 {player_damage} 點傷害。")
        else:
            messages.append(f"你完全擋下了{enemy.name}的攻擊。")

    elif action == "escape":
        chance = float(config.get("escape_chance", 0.5))
        roll = random.random()
        if roll < chance:
            messages.append("你成功脫離戰鬥！")
            battle_over = True
            escaped = True
        else:
            messages.append("逃跑失敗！")
            base_damage = calculate_damage(enemy.atk, player_def)
            player_damage = base_damage
            messages.append(f"{enemy.name} 乘勢攻擊，對你造成 {player_damage} 點傷害！")

    else:
        messages.append("你猶豫不決，什麼也沒做。")
        base_damage = calculate_damage(enemy.atk, player_def)
        player_damage = base_damage
        messages.append(f"{enemy.name} 對你造成 {player_damage} 點傷害！")

    if battle_over:
        state["active"] = False
        state["victory"] = victory
        state["escaped"] = escaped
    else:
        state["active"] = True

    state["enemy"] = enemy

    return {
        "messages": messages,
        "battle_over": battle_over,
        "player_damage": player_damage,
        "enemy_damage": enemy_damage,
        "victory": victory,
        "escaped": escaped,
    }
