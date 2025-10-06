# event_result_handler.py
# 處理事件選項的結果邏輯（加數值、顯示訊息、給道具等）

import text_log

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
    # 顯示文字訊息
    if "text" in result:
        print("【事件結果】", result["text"])
        text_log.add(result["text"])  # 整合進訊息系統

    # 處理數值變動
    if "effect" in result:
        effect = result["effect"]
        for key, value in effect.items():
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

    # 額外處理：加入道具
    if "inventory_add" in result:
        item = result["inventory_add"]
        player["inventory"].append(item)
        text_log.add(f"你獲得了道具：{item}")