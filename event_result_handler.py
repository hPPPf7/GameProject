"""event_result_handler
This module contains logic for processing the outcome of an event option.

When the player selects an option in an event, the corresponding "result"
dictionary is passed into ``handle_event_result``.  This function applies
changes to the player's state (HP, ATK, DEF, fate, inventory, flags, etc.),
emits log messages via ``text_log``, and may set a forced event if the
story needs to branch immediately.

In addition to the upstream logic, this version adds a simple check for
player death: whenever HP drops to zero or below, ``game_over`` is set
to ``True`` and a death message is logged.  Later in the main loop this
flag is checked to end the game gracefully.
"""

import text_log
from typing import Dict, Any, Optional

from battle_system import perform_battle_action

MISSION_BRIEF_FLAG = "mission_briefed"
MISSION_POTION_NAME = "治療藥水"

from fate_system import (
    FateChange,
    apply_fate_change,
    apply_major_choice,
    apply_normal_choice,
    handle_refusal,
    reset_refusal,
)


def _apply_numeric_change(player: Dict, key: str, value: int) -> None:
    """Apply a numeric change to the given player stat with logging."""

    if key not in player:
        return

    player[key] += value

    if key == "hp" and player[key] <= 0:
        player[key] = 0
        if not player.get("game_over"):
            text_log.add("你因傷重不治，離開人世。", category="system")
        player["game_over"] = True
    elif player[key] < 0:
        player[key] = 0

    if key in ["hp", "atk", "def"]:
        label = key.upper()
        sign = "+" if value >= 0 else ""
        text_log.add(f"{label} {sign}{value} → {player[key]}", category="system")
    print(
        f"【數值變化】{key.upper()} {'+' if value >= 0 else ''}{value} → {player[key]}"
    )


def _apply_effects(player: Dict, effects: Dict, source_text: str | None) -> None:
    for key, value in (effects or {}).items():
        if key == "fate":
            apply_normal_choice(player, value, source_text or "命運波動")
            continue
        if key == "fate_major":
            apply_major_choice(player, value, source_text or "重大抉擇")
            continue
        if key == "fate_bias":
            apply_fate_change(
                player,
                FateChange(value, source_text or "命運微調", "bias"),
            )
            continue
        _apply_numeric_change(player, key, value)


def handle_event_result(player: Dict, result: Dict) -> str | None:
    """
    Apply the effects of a chosen event option to the player's state.

    ``result`` should have the following optional keys:

    - ``text``: a message describing the immediate outcome.
    - ``effect``: a dict mapping stat names to deltas (e.g. {"hp": -2}).
    - ``inventory_add`` / ``inventory_remove``: items to gain/lose.
    - ``flags_set`` / ``flags_clear``: booleans to toggle in the player's
      ``flags`` dict.
    - ``fate``/``fate_major``/``fate_bias``: special keys handled by
      ``fate_system`` to influence the story.
    - ``goto_chapter``: forces the player's chapter to the given number.
    - ``emit_log``: additional messages to append to the log.
    - ``refuse``: if truthy, increment the refusal streak and potentially
      trigger a fate trigger event.

    The return value is a forced event ID if one should be queued.
    """
    forced_event = result.get("forced_event")

    # Battle specific handling
    battle_action = result.get("battle_action")
    battle_outcome: Optional[Dict[str, Any]] = None
    if battle_action:
        battle_outcome = perform_battle_action(player, battle_action, result)
        for message in battle_outcome.get("messages", []):
            text_log.add(message, category="system")
        player_damage = battle_outcome.get("player_damage", 0)
        if player_damage:
            _apply_numeric_change(player, "hp", -player_damage)

        # Allow battle actions to specify follow-up forced events
        if battle_outcome.get("battle_over") and result.get("forced_event_on_end"):
            forced_event = forced_event or result.get("forced_event_on_end")

        if battle_outcome.get("battle_over"):
            if battle_outcome.get("victory"):
                _apply_effects(
                    player,
                    result.get("victory_effect") or {},
                    result.get("victory_text") or result.get("text", "勝利獎勵"),
                )
                victory_log = result.get("victory_log")
                if victory_log:
                    if isinstance(victory_log, list):
                        for entry in victory_log:
                            text_log.add(entry, category="system")
                    else:
                        text_log.add(victory_log, category="system")
            elif battle_outcome.get("escaped"):
                _apply_effects(
                    player,
                    result.get("escape_effect") or {},
                    result.get("escape_text") or result.get("text", "撤退"),
                )

    # Show the primary result text (if provided)
    if "text" in result:
        msg = result["text"]
        print("【事件結果】", msg)
        text_log.add(msg)

    # Emit additional log entries if specified
    if "emit_log" in result:
        log_entry = result["emit_log"]
        if isinstance(log_entry, list):
            for entry in log_entry:
                text_log.add(entry)
        else:
            text_log.add(log_entry)

    # Apply numeric stat changes
    effect = result.get("effect") or {}
    if effect:
        _apply_effects(player, effect, result.get("text", "事件效果"))

    # Inventory modifications
    if "inventory_add" in result:
        items = result["inventory_add"]
        if not isinstance(items, list):
            items = [items]
        for item in items:
            player["inventory"].append(item)
            text_log.add(f"你獲得了道具：{item}", category="system")

    if "inventory_remove" in result:
        items = result["inventory_remove"]
        if not isinstance(items, list):
            items = [items]
        for item in items:
            if item in player["inventory"]:
                player["inventory"].remove(item)
                text_log.add(f"你失去了道具：{item}", category="system")

    # Flag management
    for flag in result.get("flags_set", []) or []:
        player.setdefault("flags", {})[flag] = True
        text_log.add(f"旗標觸發：{flag}", category="system")
        if flag == MISSION_BRIEF_FLAG:
            text_log.add("任務已建立：調查淺川村", category="system")
            inventory = player.setdefault("inventory", [])
            if MISSION_POTION_NAME not in inventory:
                inventory.append(MISSION_POTION_NAME)
                text_log.add(f"你獲得了道具：{MISSION_POTION_NAME}", category="system")
    for flag in result.get("flags_clear", []) or []:
        if player.setdefault("flags", {}).get(flag):
            player["flags"][flag] = False
            text_log.add(f"旗標解除：{flag}", category="system")

    # Chapter jump
    goto_chapter = result.get("goto_chapter")
    if goto_chapter:
        player["chapter"] = goto_chapter
        text_log.add(f"章節推進至：第 {goto_chapter} 章", category="system")

    # Refusal logic: mark as a refusal if requested
    tags = result.get("tags", [])
    if result.get("refuse") or "refuse" in tags:
        triggered = handle_refusal(player)
        if triggered and not forced_event:
            forced_event = triggered
    else:
        reset_refusal(player)

    # Queue forced event if present
    if forced_event:
        player["forced_event"] = forced_event
    return forced_event
