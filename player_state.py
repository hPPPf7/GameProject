from typing import Dict, List


STARTING_INVENTORY: List[str] = []


def init_player_state() -> Dict:
    """
    Initialize the player's state.

    This function returns a dictionary containing both visible and hidden
    attributes that control the game's logic.  See the README for more
    details on what each field represents.
    """
    return {
        # 可見屬性
        "inventory": STARTING_INVENTORY.copy(),  # 背包清單
        # 隱藏數值
        "fate": 50,  # 決定故事走向的命運值
        "flags": {},  # 條件事件用的任務狀態
        "chapter": 1,
        "forced_event": None,
        "midband_counter": 0,
        "event_cooldowns": {},  # 事件冷卻計數
        "consumed_events": set(),
    }
