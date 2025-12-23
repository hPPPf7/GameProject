"""Fate system utilities to control narrative flow.

This module centralises rules around the player's fate value. It exposes
helper functions for adjusting fate during story events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import text_log

FATE_MIN = 0
FATE_MAX = 100

MAX_NORMAL_DELTA = 10
MAX_MAJOR_DELTA = 20
MAX_BIAS_DELTA = 5


@dataclass
class FateChange:
    value: int
    reason: str
    kind: str  # "normal", "major", "bias"


def clamp(value: int, minimum: int = FATE_MIN, maximum: int = FATE_MAX) -> int:
    """Clamp *value* into the inclusive [minimum, maximum] range."""
    return max(minimum, min(maximum, value))


def _limit_delta(delta: int, kind: str) -> int:
    limit = {
        "normal": MAX_NORMAL_DELTA,
        "major": MAX_MAJOR_DELTA,
        "bias": MAX_BIAS_DELTA,
    }.get(kind, MAX_NORMAL_DELTA)
    return max(-limit, min(limit, delta))


def _get_fate_label(value: int) -> str:
    if value >= 67:
        return "荒謬"
    if value <= 33:
        return "理性"
    return "正常"


def apply_fate_change(player: Dict, change: FateChange) -> None:
    """Apply a fate delta while respecting narrative limits."""
    limited_delta = _limit_delta(change.value, change.kind)
    if limited_delta != change.value:
        text_log.add("命運增減被系統限制住了。", category="system")
    if limited_delta == 0:
        return

    old_value = player.get("fate", 50)
    new_value = clamp(old_value + limited_delta)
    player["fate"] = new_value

    fate_label = _get_fate_label(new_value)
    text_log.add(f"命運值 {old_value} → {new_value}（{fate_label}）", category="dev")


def post_event_update(player: Dict) -> Optional[str]:
    """Update progression after each event."""
    return None


def apply_major_choice(player: Dict, delta: int, reason: str) -> None:
    apply_fate_change(player, FateChange(delta, reason, "major"))


def apply_normal_choice(player: Dict, delta: int, reason: str) -> None:
    apply_fate_change(player, FateChange(delta, reason, "normal"))
