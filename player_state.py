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
        "fate_history": [],
        "fate_path_locked": False,
        "fate_locked_band": None,
        "refusal_streak": 0,
        "flags": {},  # 條件事件用的任意旗標
        "steps": 0,  # 前進步數（用於章節推進）
        "chapter": 1,
        "forced_event": None,
        "ending_prepared": False,
        "midband_counter": 0,
        "event_cooldowns": {},  # 各事件的冷卻計數
        "consumed_events": set(),
    }
