"""Utilities for locating resource files and user-writable locations."""

from __future__ import annotations

import os
from pathlib import Path
import sys

APP_NAME = "GameProject"


def base_path() -> Path:
    """Return the base directory where bundled resources can be found."""
    if getattr(sys, "_MEIPASS", None):  # PyInstaller extraction dir when frozen
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def is_frozen_app() -> bool:
    """Return True when running from a packaged executable."""

    return bool(getattr(sys, "frozen", False))


def res_path(*parts: str) -> str:
    """Build an absolute path to a resource under the project root."""
    return str(base_path().joinpath(*parts))


def user_data_dir() -> Path:
    """
    Return a writable directory for user save/settings data.

    Packaged builds use a portable `userdata` folder next to the executable.
    Development runs prefer LOCALAPPDATA; otherwise fall back to the home directory.
    """
    if is_frozen_app():
        return Path(sys.executable).resolve().parent / "userdata"

    root = Path(os.getenv("LOCALAPPDATA") or Path.home())
    return root / APP_NAME


def user_data_path(*parts: str) -> str:
    """Build an absolute path inside the user data directory."""
    return str(user_data_dir().joinpath(*parts))
