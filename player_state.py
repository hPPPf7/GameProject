def init_player_state():
    return {
        # 顯示數值
        "hp": 20,         # 生命值
        "atk": 5,         # 攻擊力
        "def": 3,         # 防禦力
        "inventory": [],  # 背包

        # 隱性數值
        "fate": 50,       # 命運值：影響主線進度、分支與結局觸發
        "fate_history": [],
        "fate_path_locked": False,
        "fate_locked_band": None,
        "refusal_streak": 0,
        "flags": {},      # 條件旗標（例如某角色是否出現過）例如 {"met_mysterious_villager": True}
        "steps": 0,        # 前進步數，用來觸發事件或主線
        "chapter": 1,
        "forced_event": None,
        "ending_prepared": False,
        "midband_counter": 0,       # 連續停留在命運中段的次數
        "event_cooldowns": {},      # 事件冷卻計數
        "consumed_events": set(),   # 只會觸發一次的事件紀錄

        # 背包介面狀態
        "inventory_scroll": 0  # 滾動偏移，用來控制背包捲動位置
    }