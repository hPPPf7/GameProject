"""event_result_handler
This module contains logic for processing the outcome of an event option.

When the player selects an option in an event, the corresponding "result"
dictionary is passed into ``handle_event_result``.  This function applies
changes to the player's state (fate, inventory, flags, etc.), emits log
messages via ``text_log``, and may set a forced event if the story needs
to branch immediately.
"""

import text_log
from typing import Dict, Any, Optional

from battle_system import perform_battle_action
import sound_manager

MISSION_BRIEF_FLAG = "mission_briefed"
MISSION_POTION_NAME = "治療藥水"

from fate_system import (
    FateChange,
    apply_fate_change,
    apply_major_choice,
    apply_normal_choice,
)


def _apply_numeric_change(player: Dict, key: str, value: int) -> None:
    """Apply a numeric change to the given player stat with logging."""

    if key not in player:
        return

    old_value = player[key]
    player[key] += value

    if player[key] < 0:
        player[key] = 0
    print(
        f"【數值變化】{key.upper()} {old_value} {'+' if value >= 0 else ''}{value} → {player[key]}"
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
    - ``effect``: a dict mapping stat names to deltas (e.g. {"fate": 1}).
    - ``inventory_add`` / ``inventory_remove``: items to gain/lose.
    - ``flags_set`` / ``flags_clear``: booleans to toggle in the player's
      ``flags`` dict.
    - ``fate``/``fate_major``/``fate_bias``: special keys handled by
      ``fate_system`` to influence the story.
    - ``goto_chapter``: forces the player's chapter to the given number.
    - ``emit_log``: additional messages to append to the log.
    - ``end_game``: if truthy, return to start menu after the result finishes.
    - ``defeat_text`` / ``defeat_effect`` / ``defeat_log``: applied when a
      battle ends without 勝利 or 撤退（耐久耗盡等情況）。
    - ``forced_event_on_defeat``: optional forced jump when 戰鬥失敗。

    The return value is a forced event ID if one should be queued.
    """
    ending_segments = result.get("ending_segments")
    if ending_segments and not isinstance(ending_segments, list):
        ending_segments = [str(ending_segments)]

    primary_text = result.get("text")
    if result.get("end_game") and not ending_segments and primary_text:
        ending_segments = [segment for segment in primary_text.split("\n\n") if segment]

    if ending_segments:
        text_log.clear_history()
        player["ending_segments"] = ending_segments
        player["ending_segment_index"] = 1
        player["ending_active"] = True
        player["ending_exit_ready"] = False
        player["ending_exit_started"] = False
        primary_text = ending_segments[0] if ending_segments else None

    if primary_text:
        print("【事件結果】", primary_text)
        text_log.add(primary_text)

    forced_event = result.get("forced_event")

    # 戰鬥專用處理
    battle_action = result.get("battle_action")
    battle_outcome: Optional[Dict[str, Any]] = None
    if battle_action:
        battle_outcome = perform_battle_action(player, battle_action, result)
        for message in battle_outcome.get("messages", []):
            text_log.add(message, category="system")

        # 允許戰鬥行動指定後續的強制事件
        if battle_outcome.get("battle_over") and result.get("forced_event_on_end"):
            forced_event = forced_event or result.get("forced_event_on_end")
        if (
            battle_outcome.get("battle_over")
            and (not battle_outcome.get("victory"))
            and (not battle_outcome.get("escaped"))
        ):
            forced_event = forced_event or result.get("forced_event_on_defeat")

        if battle_outcome.get("battle_over"):
            if battle_outcome.get("victory"):
                _apply_effects(
                    player,
                    result.get("victory_effect") or {},
                    result.get("victory_text") or primary_text or "勝利獎勵",
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
                    result.get("escape_text") or primary_text or "撤退",
                )
            else:
                _apply_effects(
                    player,
                    result.get("defeat_effect") or {},
                    result.get("defeat_text") or primary_text or "戰鬥失敗",
                )
                defeat_log = result.get("defeat_log")
                if defeat_log:
                    if isinstance(defeat_log, list):
                        for entry in defeat_log:
                            text_log.add(entry, category="system")
                    else:
                        text_log.add(defeat_log, category="system")

    # 若有指定則額外寫入日誌
    if "emit_log" in result:
        log_entry = result["emit_log"]
        if isinstance(log_entry, list):
            for entry in log_entry:
                text_log.add(entry)
        else:
            text_log.add(log_entry)

    if result.get("end_game"):
        player.setdefault("flags", {})["ending_cinematic"] = True
        player["layout_transition"] = {"progress": 0.0}
        text_log.set_typewriter_override(True)
        player["ending_active"] = True

    # 套用數值屬性變化
    effect = result.get("effect") or {}
    if effect:
        _apply_effects(player, effect, primary_text or "事件效果")

    # 背包異動：在橘色提示出現時同步音效與背包更新
    inventory = player.setdefault("inventory", [])
    if "inventory_add" in result:
        items = result["inventory_add"]
        if not isinstance(items, list):
            items = [items]
        for item in items:
            def _apply_gain(item_name=item):
                if item_name not in player["inventory"]:
                    player["inventory"].append(item_name)
                    sound_manager.play_sfx("pickup")

            text_log.add(
                f"你獲得了道具:{item}",
                category="system",
                on_show=_apply_gain,
            )

    if "inventory_remove" in result:
        items = result["inventory_remove"]
        if not isinstance(items, list):
            items = [items]
        for item in items:
            def _apply_loss(item_name=item):
                if item_name in player["inventory"]:
                    player["inventory"].remove(item_name)
                    sound_manager.play_sfx("pickup")

            text_log.add(
                f"你失去了道具:{item}",
                category="system",
                on_show=_apply_loss,
            )

    # 旗標管理
    for flag in result.get("flags_set", []) or []:
        player.setdefault("flags", {})[flag] = True
        text_log.add(f"旗標觸發：{flag}", category="system")
        if flag == MISSION_BRIEF_FLAG:
            text_log.add("任務已建立：調查淺川村", category="system")
            inventory = player.setdefault("inventory", [])
            if MISSION_POTION_NAME not in inventory:
                def _apply_brief_reward():
                    if MISSION_POTION_NAME not in inventory:
                        inventory.append(MISSION_POTION_NAME)
                        sound_manager.play_sfx("pickup")

                text_log.add(
                    f"你獲得了道具:{MISSION_POTION_NAME}",
                    category="system",
                    on_show=_apply_brief_reward,
                )
    for flag in result.get("flags_clear", []) or []:
        if player.setdefault("flags", {}).get(flag):
            player["flags"][flag] = False
            text_log.add(f"旗標解除：{flag}", category="system")

    # 跳轉章節
    goto_chapter = result.get("goto_chapter")
    if goto_chapter:
        player["chapter"] = goto_chapter
        text_log.add(f"章節推進至：第 {goto_chapter} 章", category="system")

    return forced_event

