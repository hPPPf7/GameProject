# event_result_handler.py
# 處理事件選項的結果邏輯（加數值、顯示訊息、給道具等）

import text_log

from fate_system import (
    FateChange,
    apply_fate_change,
    apply_major_choice,
    apply_normal_choice,
    handle_refusal,
    reset_refusal,
)


def handle_event_result(player, result):
    """
    根據事件選項中的 result 欄位對 player 狀態進行變更。
    result 格式範例：
    {
        "text": "你感覺更有精神了。",
        "effect": {
            "hp": +5,
            "atk": 0,
            "def": 0
        }
    }
    """
    forced_event = result.get("forced_event")
    
    # 顯示文字訊息
    if "text" in result:
        print("【事件結果】", result["text"])
        text_log.add(result["text"])  # 整合進訊息系統

    if "emit_log" in result:
        log_entry = result["emit_log"]
        if isinstance(log_entry, list):
            for entry in log_entry:
                text_log.add(entry)
        else:
            text_log.add(log_entry)

    # 處理數值變動
    if "effect" in result:
        effect = result["effect"]
        for key, value in effect.items():
            if key == "fate":
                apply_normal_choice(player, value, result.get("text", "命運波動"))
                continue
            if key == "fate_major":
                apply_major_choice(player, value, result.get("text", "重大抉擇"))
                continue
            if key == "fate_bias":
                apply_fate_change(player, FateChange(value, result.get("text", "命運微調"), "bias"))
                continue
            if key in player:
                original = player[key]
                player[key] += value
                if player[key] < 0:
                    player[key] = 0

                # 只有顯示玩家可見的屬性
                if key in ["hp", "atk", "def"]:
                    label = key.upper()
                    sign = "+" if value >= 0 else ""
                    msg = f"{label} {sign}{value} → {player[key]}"
                    text_log.add(msg)

                print(f"【數值變化】{key.upper()} {'+' if value >= 0 else ''}{value} → {player[key]}")

    # 額外處理：加入或移除道具
    if "inventory_add" in result:
        items = result["inventory_add"]
        if not isinstance(items, list):
            items = [items]
        for item in items:
            player["inventory"].append(item)
            text_log.add(f"你獲得了道具：{item}")

    if "inventory_remove" in result:
        items = result["inventory_remove"]
        if not isinstance(items, list):
            items = [items]
        for item in items:
            if item in player["inventory"]:
                player["inventory"].remove(item)
                text_log.add(f"你失去了道具：{item}")

    if "flags_set" in result:
        for flag in result["flags_set"]:
            player.setdefault("flags", {})[flag] = True
            text_log.add(f"旗標觸發：{flag}")

    if "flags_clear" in result:
        for flag in result["flags_clear"]:
            if player.setdefault("flags", {}).get(flag):
                player["flags"][flag] = False
                text_log.add(f"旗標解除：{flag}")

    if "goto_chapter" in result and result["goto_chapter"]:
        new_chapter = result["goto_chapter"]
        player["chapter"] = new_chapter
        text_log.add(f"章節推進至：第 {new_chapter} 章")

    tags = result.get("tags", [])
    if result.get("refuse") or "refuse" in tags:
        triggered = handle_refusal(player)
        if triggered and not forced_event:
            forced_event = triggered
    else:
        reset_refusal(player)

    if forced_event:
        player["forced_event"] = forced_event

    return forced_event