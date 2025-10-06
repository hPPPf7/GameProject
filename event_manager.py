import json
import random


# 載入所有事件資料
def load_events(path="data/story_data.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# 所有事件資料暫存在這裡
ALL_EVENTS = load_events()

# 檢查該事件是否符合玩家狀態（for conditional 事件）
def is_event_condition_met(event, player):
    condition = event.get("condition")
    if not condition:
        return True

    # 命運值需達一定門檻
    if "fate_min" in condition and player.get("fate", 0) < condition["fate_min"]:
        return False

    # 你可在這裡擴充更多條件（如 has_item, flag_true 等）

    return True

# 隨機取得一個事件（包含條件過濾）
def get_random_event(event_types=["normal", "battle", "dialogue"], player=None):
    if player is None:
        player = {}

    candidates = [
        e for e in ALL_EVENTS
        if e["type"] in event_types and is_event_condition_met(e, player)
    ]

    if not candidates:
        return None
    return random.choice(candidates)
