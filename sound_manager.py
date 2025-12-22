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
BGM_FADE_SECONDS = 0.8
_current_bgm_track: str | None = None
_bgm_fade_state: str | None = None
_bgm_fade_timer = 0.0
_bgm_fade_out_duration = BGM_FADE_SECONDS
_bgm_fade_in_duration = BGM_FADE_SECONDS
_bgm_fade_multiplier = 1.0
_pending_bgm_track: str | None = None

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
    """Start background music in a loop from the bgm directory with fade."""

    init_sound()
    global _current_bgm_track, _pending_bgm_track
    global _bgm_fade_out_duration, _bgm_fade_in_duration
    global _bgm_fade_state, _bgm_fade_timer

    # Avoid restarting the same track unless we are in the middle of a fade out.
    if track == _current_bgm_track and _bgm_fade_state != "fading_out":
        return

    _pending_bgm_track = track
    _bgm_fade_out_duration = BGM_FADE_SECONDS
    _bgm_fade_in_duration = BGM_FADE_SECONDS
    _bgm_fade_timer = 0.0

    if pygame.mixer.music.get_busy() and _current_bgm_track:
        _start_bgm_fade_out()
        return

    pygame.mixer.music.stop()
    _start_bgm_playback(track)


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
    pygame.mixer.music.set_volume(_bgm_volume * _bgm_fade_multiplier)


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


def _start_bgm_playback(track: str) -> None:
    """Load and start a BGM track, optionally fading it in."""

    global _current_bgm_track, _bgm_fade_state, _bgm_fade_timer, _bgm_fade_multiplier
    global _pending_bgm_track
    pygame.mixer.music.load(res_path("assets", "sounds", "bgm", track))
    _current_bgm_track = track
    _pending_bgm_track = None

    if _bgm_fade_in_duration > 0:
        _bgm_fade_state = "fading_in"
        _bgm_fade_timer = 0.0
        _bgm_fade_multiplier = 0.0
    else:
        _bgm_fade_state = None
        _bgm_fade_timer = 0.0
        _bgm_fade_multiplier = 1.0

    _apply_bgm_volume()
    pygame.mixer.music.play(-1)


def _start_bgm_fade_out() -> None:
    """Begin fading out the current BGM so we can swap tracks smoothly."""

    global _bgm_fade_state, _bgm_fade_timer
    _bgm_fade_state = "fading_out"
    _bgm_fade_timer = 0.0


def update(dt: float) -> None:
    """Advance BGM fade transitions; should be called once per frame."""

    global _bgm_fade_state, _bgm_fade_timer
    global _bgm_fade_multiplier, _pending_bgm_track, _current_bgm_track

    if not pygame.mixer.get_init() or _bgm_fade_state is None:
        return

    if _bgm_fade_state == "fading_out":
        progress = (
            1.0
            if _bgm_fade_out_duration <= 0
            else min(1.0, _bgm_fade_timer / _bgm_fade_out_duration)
        )
        _bgm_fade_multiplier = 1.0 - progress
        _apply_bgm_volume()
        _bgm_fade_timer += dt

        if progress >= 1.0:
            pygame.mixer.music.stop()
            _current_bgm_track = None
            _bgm_fade_state = None
            _bgm_fade_timer = 0.0
            next_track = _pending_bgm_track
            _pending_bgm_track = None
            if next_track:
                _start_bgm_playback(next_track)

    elif _bgm_fade_state == "fading_in":
        progress = (
            1.0
            if _bgm_fade_in_duration <= 0
            else min(1.0, _bgm_fade_timer / _bgm_fade_in_duration)
        )
        _bgm_fade_multiplier = progress
        _apply_bgm_volume()
        _bgm_fade_timer += dt

        if progress >= 1.0:
            _bgm_fade_state = None
            _bgm_fade_timer = 0.0
            _bgm_fade_multiplier = 1.0
