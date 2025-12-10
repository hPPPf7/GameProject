"""Persistence helpers for storing and loading adventure progress."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from paths import res_path


def _save_file() -> Path:
    return Path(res_path("data", "save.json"))


def has_save() -> bool:
    return _save_file().exists()


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, dict):
        return {key: _to_json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _serialize_player(player: Dict[str, Any]) -> Dict[str, Any]:
    return {key: _to_json_safe(value) for key, value in player.items()}


def _deserialize_player(data: Dict[str, Any]) -> Dict[str, Any]:
    player = dict(data)
    if "consumed_events" in player and isinstance(player["consumed_events"], list):
        player["consumed_events"] = set(player["consumed_events"])
    return player


def save_game(payload: Dict[str, Any]) -> None:
    save_file = _save_file()
    save_file.parent.mkdir(parents=True, exist_ok=True)

    serializable = dict(payload)
    player = payload.get("player")
    if isinstance(player, dict):
        serializable["player"] = _serialize_player(player)

    with save_file.open("w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)


def load_game() -> Dict[str, Any] | None:
    save_file = _save_file()
    if not save_file.exists():
        return None

    try:
        data = json.loads(save_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if "player" in data and isinstance(data["player"], dict):
        data["player"] = _deserialize_player(data["player"])
    return data


def clear_save() -> None:
    if not has_save():
        return
    try:
        _save_file().unlink()
    except OSError:
        pass
