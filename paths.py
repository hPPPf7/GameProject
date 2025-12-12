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


def res_path(*parts: str) -> str:
    """Build an absolute path to a resource under the project root."""
    return str(base_path().joinpath(*parts))


def user_data_dir() -> Path:
    """
    Return a writable directory for user save/settings data.

    On Windows prefers LOCALAPPDATA; otherwise falls back to the home directory.
    """
    root = Path(os.getenv("LOCALAPPDATA") or Path.home())
    return root / APP_NAME


def user_data_path(*parts: str) -> str:
    """Build an absolute path inside the user data directory."""
    return str(user_data_dir().joinpath(*parts))
