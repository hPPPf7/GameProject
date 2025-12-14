"""Fate system utilities to control narrative flow.

This module centralises every rule around the player's fate value so that
it never drifts endlessly inside the neutral band.  It exposes helper
functions for adjusting fate, applying automatic chapter bias, and deciding
when the story must inject a fate trigger or lock the main route.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import text_log

# 命運範圍與臨界值 -------------------------------------------------
FATE_MIN = 0
FATE_MAX = 100
HIGH_THRESHOLD = 67
LOW_THRESHOLD = 33

# 調校常數 ----------------------------------------------------------
MAX_NORMAL_DELTA = 10
MAX_MAJOR_DELTA = 20
MAX_BIAS_DELTA = 5

CHAPTER_THRESHOLDS = {
    2: 3,  # 第二章：前三個事件結束後開啟微調
    3: 6,  # 第三章：六次探索後開始根據平均值偏移
    4: 9,  # 第四章：九次探索後鎖定命運走向
    5: 12,  # 第五章：十二次探索後推進至結局
}

LOCK_EVENTS = {
    "high": "fate_lock_high",
    "mid": "fate_lock_mid",
    "low": "fate_lock_low",
}

ENDING_EVENTS = {
    "high": "fate_ending_high",
    "mid": "fate_ending_mid",
    "low": "fate_ending_low",
}


@dataclass
class FateChange:
    value: int
    reason: str
    kind: str  # 「normal」、「major」、「bias」


def clamp(value: int, minimum: int = FATE_MIN, maximum: int = FATE_MAX) -> int:
    """Clamp *value* into the inclusive [minimum, maximum] range."""
    return max(minimum, min(maximum, value))


def determine_band(value: int) -> str:
    if value >= HIGH_THRESHOLD:
        return "high"
    if value <= LOW_THRESHOLD:
        return "low"
    return "mid"


def _limit_delta(delta: int, kind: str) -> int:
    limit = {
        "normal": MAX_NORMAL_DELTA,
        "major": MAX_MAJOR_DELTA,
        "bias": MAX_BIAS_DELTA,
    }.get(kind, MAX_NORMAL_DELTA)
    return max(-limit, min(limit, delta))


def apply_fate_change(player: Dict, change: FateChange) -> None:
    """Apply a fate delta while respecting narrative limits."""
    limited_delta = _limit_delta(change.value, change.kind)
    if limited_delta != change.value:
        text_log.add("命運的擺盪被某種力量限制住了……", category="system")
    if limited_delta == 0:
        return

    old_value = player.get("fate", 50)
    new_value = clamp(old_value + limited_delta)
    player["fate"] = new_value

    # 保存最近 10 次命運結果用於第三章平均偏移
    history: list[int] = player.setdefault("fate_history", [])
    history.append(new_value)
    if len(history) > 10:
        history.pop(0)

    # 標記本事件已經變更過命運值，避免後續再自動微調
    player["_fate_changed_in_event"] = True

    text_log.add(f"命運值 {old_value} → {new_value}", category="system")


def nudge_toward_band(player: Dict, target_band: str, reason: str) -> None:
    """Gently pull fate toward a narrative band during auto adjustments."""
    current = player.get("fate", 50)
    target = {
        "high": 75,
        "mid": 50,
        "low": 25,
    }[target_band]
    delta = target - current
    if delta > 0:
        delta = min(delta, MAX_BIAS_DELTA)
    else:
        delta = max(delta, -MAX_BIAS_DELTA)
    if delta == 0:
        return
    apply_fate_change(player, FateChange(delta, reason, "bias"))


def advance_chapter_if_needed(player: Dict) -> Optional[int]:
    """Raise the chapter index when step thresholds are reached."""
    steps = player.get("steps", 0)
    current_chapter = player.get("chapter", 1)
    new_chapter = current_chapter
    for chapter, threshold in sorted(CHAPTER_THRESHOLDS.items()):
        if steps >= threshold and chapter > new_chapter:
            new_chapter = chapter
    if new_chapter != current_chapter:
        player["chapter"] = new_chapter
        text_log.add(f"第 {new_chapter} 章揭開帷幕，命運的重量更加沈重。")
        return new_chapter
    return None


def apply_chapter_bias(player: Dict) -> None:
    # 若本事件已經變更命運值，避免再自動微調造成重複日誌
    if player.get("_fate_changed_in_event"):
        return

    chapter = player.get("chapter", 1)
    current_band = determine_band(player.get("fate", 50))

    if chapter == 2:
        # 若玩家沒有極端選擇，慢慢把命運拉回中性
        if current_band == "high":
            nudge_toward_band(player, "mid", "第二章：系統校準你的理性")
        elif current_band == "low":
            nudge_toward_band(player, "mid", "第二章：系統校準你的荒謬")
    elif chapter == 3:
        history = player.get("fate_history", [])
        if history:
            avg = sum(history) / len(history)
            if avg >= 55:
                nudge_toward_band(player, "high", "第三章：理性線索逐漸成形")
            elif avg <= 45:
                nudge_toward_band(player, "low", "第三章：荒謬低語愈發清晰")
            else:
                nudge_toward_band(player, "mid", "第三章：命運保持微妙平衡")


def maybe_lock_main_path(player: Dict) -> Optional[str]:
    if player.get("chapter", 1) < 4:
        return None
    if player.get("fate_path_locked"):
        return None

    band = determine_band(player.get("fate", 50))
    player["fate_path_locked"] = True
    player["fate_locked_band"] = band
    text_log.add("命運緊緊扣住了你的方向，主線已成定局。")
    return LOCK_EVENTS[band]


def maybe_prepare_ending(player: Dict) -> Optional[str]:
    if player.get("chapter", 1) < 5:
        return None
    if player.get("ending_prepared"):
        return None

    band = player.get("fate_locked_band") or determine_band(player.get("fate", 50))
    player["ending_prepared"] = True
    text_log.add("結局的陰影浮現，你無法再回頭。")
    return ENDING_EVENTS[band]


def post_event_update(player: Dict) -> Optional[str]:
    """Update progression after每次事件，回傳需要強制觸發的事件 id。"""
    player["steps"] = player.get("steps", 0) + 1

    advance_chapter_if_needed(player)
    apply_chapter_bias(player)

    forced_event = maybe_lock_main_path(player)
    if forced_event:
        player["_fate_changed_in_event"] = False
        return forced_event

    result = maybe_prepare_ending(player)
    # 清除本事件的命運變更記號
    player["_fate_changed_in_event"] = False
    return result


def handle_refusal(player: Dict) -> Optional[str]:
    """Call when the player refuses任務以追蹤自我懷疑觸發。"""
    streak = player.get("refusal_streak", 0) + 1
    player["refusal_streak"] = streak
    if streak >= 2:
        player["refusal_streak"] = 0
        text_log.add("連續的拒絕讓命運質疑你的存在。")
        return "fate_trigger_self_doubt"
    return None


def reset_refusal(player: Dict) -> None:
    player["refusal_streak"] = 0


def apply_major_choice(player: Dict, delta: int, reason: str) -> None:
    apply_fate_change(player, FateChange(delta, reason, "major"))


def apply_normal_choice(player: Dict, delta: int, reason: str) -> None:
    apply_fate_change(player, FateChange(delta, reason, "normal"))
