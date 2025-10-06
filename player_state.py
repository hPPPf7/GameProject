def init_player_state():
    return {
        # 顯示數值
        "hp": 20,         # 生命值
        "atk": 5,         # 攻擊力
        "def": 3,         # 防禦力
        "inventory": [],  # 背包

        # 隱性數值
        "fate": 0,        # 命運值：影響主線進度、分支與結局觸發
        "flags": {},      # 條件旗標（例如某角色是否出現過）例如 {"met_mysterious_villager": True}
        "steps": 0,        # 前進步數，用來觸發事件或主線

        # 背包介面狀態
        "inventory_scroll": 0  # 滾動偏移，用來控制背包捲動位置
    }