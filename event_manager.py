import json
import random
from typing import Dict, List, Optional, Sequence, Tuple


MIDBAND_MIN = 40
MIDBAND_MAX = 60
MIDBAND_LIMIT = 3
FATE_TRIGGER_MIDBAND_ID = "event_fate_trigger_midband"


# 載入所有事件資料
def load_events(path="data/story_data.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# 所有事件資料暫存在這裡
ALL_EVENTS: List[Dict] = load_events()
EVENT_LOOKUP: Dict[str, Dict] = {event["id"]: event for event in ALL_EVENTS}


def _ensure_consumed_set(player) -> set:
    consumed = player.setdefault("consumed_events", set())
    if isinstance(consumed, list):
        consumed = set(consumed)
        player["consumed_events"] = consumed
    return consumed


def _tick_cooldowns(player) -> None:
    cooldowns = player.setdefault("event_cooldowns", {})
    to_remove: List[str] = []
    for event_id, turns in list(cooldowns.items()):
        if turns <= 0:
            to_remove.append(event_id)
            continue
        cooldowns[event_id] = turns - 1
        if cooldowns[event_id] <= 0:
            to_remove.append(event_id)
    for event_id in to_remove:
        cooldowns.pop(event_id, None)


def _is_on_cooldown(event: Dict, player) -> bool:
    cooldowns = player.get("event_cooldowns", {})
    return cooldowns.get(event["id"], 0) > 0


def _was_consumed(event: Dict, player) -> bool:
    consumed = player.get("consumed_events", set())
    if isinstance(consumed, list):
        consumed = set(consumed)
        player["consumed_events"] = consumed
    return event["id"] in consumed


def _apply_cooldown(event: Dict, player) -> None:
    cooldown = max(0, event.get("cooldown", 0))
    if cooldown:
        player.setdefault("event_cooldowns", {})[event["id"]] = cooldown


def _mark_consumed(event: Dict, player) -> None:
    if event.get("once"):
        consumed = _ensure_consumed_set(player)
        consumed.add(event["id"])


def _prepare_event(player, event: Optional[Dict]) -> Optional[Dict]:
    if not event:
        return None
    _apply_cooldown(event, player)
    _mark_consumed(event, player)
    return event


# 檢查該事件是否符合玩家狀態
def is_event_condition_met(event: Dict, player) -> bool:
    if player is None:
        player = {}

    required_chapter = event.get("chapter")
    if required_chapter and player.get("chapter", 1) < required_chapter:
        return False

    condition = event.get("condition") or {}

    fate_value = player.get("fate", 0)
    if "fate_min" in condition and fate_value < condition["fate_min"]:
        return False
    if "fate_max" in condition and fate_value > condition["fate_max"]:
        return False

    hp_value = player.get("hp", 0)
    if "hp_min" in condition and hp_value < condition["hp_min"]:
        return False
    if "hp_max" in condition and hp_value > condition["hp_max"]:
        return False

    current_chapter = player.get("chapter", 1)
    if "chapter_is" in condition and current_chapter != condition["chapter_is"]:
        return False
    if "chapter_min" in condition and current_chapter < condition["chapter_min"]:
        return False
    if "chapter_max" in condition and current_chapter > condition["chapter_max"]:
        return False

    inventory: Sequence[str] = player.get("inventory", [])
    for item in condition.get("inventory_has", []):
        if item not in inventory:
            return False
    for item in condition.get("inventory_not", []):
        if item in inventory:
            return False

    flags = player.get("flags", {})
    for flag in condition.get("flag_on", []):
        if not flags.get(flag):
            return False
    for flag in condition.get("flag_off", []):
        if flags.get(flag):
            return False

    return True


def get_event_by_id(event_id: str) -> Optional[Dict]:
    return EVENT_LOOKUP.get(event_id)


def _increment_midband_counter(player) -> int:
    fate_value = player.get("fate", 50)
    if MIDBAND_MIN <= fate_value <= MIDBAND_MAX:
        player["midband_counter"] = player.get("midband_counter", 0) + 1
    else:
        player["midband_counter"] = 0
    return player["midband_counter"]


# 隨機取得一個事件（包含條件過濾與命運限制）
def get_random_event(event_types=None, player=None):
    if event_types is None:
        event_types = ["normal", "battle", "dialogue", "conditional", "milestone"]
    if player is None:
        player = {}

    _tick_cooldowns(player)

    forced_event_id = player.get("forced_event") if player else None
    if forced_event_id:
        player["forced_event"] = None
        return _prepare_event(player, get_event_by_id(forced_event_id))

    streak = _increment_midband_counter(player)
    if streak >= MIDBAND_LIMIT:
        trigger_event = get_event_by_id(FATE_TRIGGER_MIDBAND_ID)
        if trigger_event and is_event_condition_met(trigger_event, player):
            player["midband_counter"] = 0
            return _prepare_event(player, trigger_event)

    candidates: List[Tuple[Dict, int]] = []
    for event in ALL_EVENTS:
        if event.get("type") not in event_types:
            continue
        if event.get("once") and _was_consumed(event, player):
            continue
        if _is_on_cooldown(event, player):
            continue
        if not is_event_condition_met(event, player):
            continue
        weight = int(event.get("weight", 1))
        if weight <= 0:
            continue
        candidates.append((event, weight))

    if not candidates:
        return None

    events, weights = zip(*candidates)
    chosen = random.choices(events, weights=weights, k=1)[0]
    return _prepare_event(player, chosen)
