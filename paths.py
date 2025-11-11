"""Utilities for locating resource files regardless of execution mode."""

from __future__ import annotations

from pathlib import Path
import sys


def base_path() -> Path:
    """Return the base directory where bundled resources can be found."""
    if getattr(sys, "_MEIPASS", None):  # PyInstaller 暫存解壓目錄
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def res_path(*parts: str) -> str:
    """Build an absolute path to a resource under the project root."""
    return str(base_path().joinpath(*parts))
