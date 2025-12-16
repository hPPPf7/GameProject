"""Centralised sound loading and playback utilities."""

from __future__ import annotations

from typing import Any

import pygame

import settings_manager
from paths import res_path

_sfx_cache: dict[str, pygame.mixer.Sound] = {}
_initialized = False

_bgm_volume = 0.7
_sfx_volume = 0.7

SFX_FILES = {
    "heal": "healing.wav",
    "attack": "attack.wav",
    "defense": "defense.wav",
    "monster_death": "monster_death.wav",
    "character_death": "character_death.wav",
    "pickup": "pickup.wav",
}


def init_sound() -> None:
    """Initialise the mixer and load sound effects if not already done."""

    global _initialized
    if _initialized:
        return

    _load_volumes()

    if not pygame.mixer.get_init():
        pygame.mixer.init()

    for key, filename in SFX_FILES.items():
        _sfx_cache[key] = pygame.mixer.Sound(
            res_path("assets", "sounds", "sfx", filename)
        )

    _apply_bgm_volume()
    _apply_sfx_volume()

    _initialized = True


def play_bgm(track: str = "Music-1.mp3") -> None:
    """Start background music in a loop from the bgm directory."""

    init_sound()
    pygame.mixer.music.load(res_path("assets", "sounds", "bgm", track))
    _apply_bgm_volume()
    pygame.mixer.music.play(-1)


def play_sfx(name: str) -> None:
    """Play a named sound effect if it exists."""

    init_sound()
    sound = _sfx_cache.get(name)
    if sound:
        sound.play()


def get_bgm_volume() -> float:
    return _bgm_volume


def get_sfx_volume() -> float:
    return _sfx_volume


def set_bgm_volume(value: float) -> float:
    """Clamp and apply background music volume, returning the new value."""

    global _bgm_volume
    _bgm_volume = max(0.0, min(1.0, value))
    _apply_bgm_volume()
    _save_volumes()
    return _bgm_volume


def set_sfx_volume(value: float) -> float:
    """Clamp and apply sound-effect volume, returning the new value."""

    global _sfx_volume
    _sfx_volume = max(0.0, min(1.0, value))
    _apply_sfx_volume()
    _save_volumes()
    return _sfx_volume


def change_bgm_volume(delta: float) -> float:
    """Adjust background-music volume by ``delta`` and return the result."""

    return set_bgm_volume(_bgm_volume + delta)


def change_sfx_volume(delta: float) -> float:
    """Adjust sound-effect volume by ``delta`` and return the result."""

    return set_sfx_volume(_sfx_volume + delta)


def _apply_bgm_volume() -> None:
    if not pygame.mixer.get_init():
        return
    pygame.mixer.music.set_volume(_bgm_volume)


def _apply_sfx_volume() -> None:
    if not pygame.mixer.get_init():
        return
    for sound in _sfx_cache.values():
        sound.set_volume(_sfx_volume)


def _load_volumes() -> None:
    """Load volume settings from disk if available."""

    global _bgm_volume, _sfx_volume
    data: dict[str, Any] = settings_manager.load_settings()
    _bgm_volume = _clamp_volume(data.get("bgm_volume", _bgm_volume))
    _sfx_volume = _clamp_volume(data.get("sfx_volume", _sfx_volume))


def _save_volumes() -> None:
    """Persist current volume settings to disk."""

    settings_manager.save_settings(
        {"bgm_volume": _bgm_volume, "sfx_volume": _sfx_volume}
    )


def _clamp_volume(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.7
