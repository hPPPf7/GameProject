import json
import random


# 載入所有事件資料
def load_events(path="data/story_data.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# 所有事件資料暫存在這裡
ALL_EVENTS = load_events()


def _is_condition_met(condition, player):
    """通用條件判定函式，可用於事件與選項。"""
    if not condition:
        return True

    # 命運值需達一定門檻
    if "fate_min" in condition and player.get("fate", 0) < condition["fate_min"]:
        return False

    # 前進步數需達門檻
    if "step_min" in condition and player.get("steps", 0) < condition["step_min"]:
        return False

    # 指定旗標需為 True
    if "flag_true" in condition:
        flag = condition["flag_true"]
        if not player.get("flags", {}).get(flag):
            return False

    # 指定旗標需為 False
    if "flag_false" in condition:
        flag = condition["flag_false"]
        if player.get("flags", {}).get(flag):
            return False

    return True


# 檢查該事件是否符合玩家狀態（for conditional 事件）
def is_event_condition_met(event, player):
    return _is_condition_met(event.get("condition"), player)


def is_option_available(option, player):
    """判斷選項是否可供玩家選擇。"""
    return _is_condition_met(option.get("condition"), player)


def get_available_options(event, player):
    """取得符合條件的選項列表。"""
    return [opt for opt in event.get("options", []) if is_option_available(opt, player)]


# 隨機取得一個事件（包含條件過濾）
def get_random_event(
    event_types=["normal", "battle", "dialogue", "conditional"], player=None
):
    if player is None:
        player = {}

    candidates = [
        e
        for e in ALL_EVENTS
        if e["type"] in event_types and is_event_condition_met(e, player)
    ]

    if not candidates:
        return None
    return random.choice(candidates)
