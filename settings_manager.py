"""Lightweight helper for persisting user settings (volumes, toggles, etc.)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from paths import user_data_path

_SETTINGS_FILE = Path(user_data_path("settings.json"))


def load_settings() -> Dict[str, Any]:
    """Read the settings file, returning an empty dict on failure."""

    if not _SETTINGS_FILE.exists():
        return {}

    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def save_settings(updates: Dict[str, Any]) -> None:
    """Merge ``updates`` into the settings file, ignoring write errors."""

    settings = load_settings()
    settings.update(updates)

    try:
        _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SETTINGS_FILE.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        # Avoid crashing the game if disk writes fail.
        pass
