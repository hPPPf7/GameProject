"""Centralised sound loading and playback utilities."""

from __future__ import annotations

from typing import Any

import pygame

import settings_manager
from paths import res_path

_sfx_cache: dict[str, pygame.mixer.Sound] = {}
_initialized = False
_paused = False
_preview_ticks = 0
_preview_timer = 0.0
_preview_channel = None

_bgm_volume = 1.0
_sfx_volume = 1.0
_typewriter_volume = 1.0
_VOLUME_CURVE_EXPONENT = 2.2
_MAX_OUTPUT_VOLUME = 0.70
_VOLUME_STEP = 0.1
BGM_FADE_SECONDS = 0.8
_current_bgm_track: str | None = None
_bgm_fade_state: str | None = None
_bgm_fade_timer = 0.0
_bgm_fade_out_duration = BGM_FADE_SECONDS
_bgm_fade_in_duration = BGM_FADE_SECONDS
_bgm_fade_multiplier = 1.0
_pending_bgm_track: str | None = None

SFX_FILES = {
    "ui_click": "button_click.wav",
    "typewriter": "typewriter_tick.wav",
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

    if _paused:
        return
    init_sound()
    sound = _sfx_cache.get(name)
    if sound:
        sound.play()


def cancel_typewriter_preview() -> None:
    global _preview_ticks, _preview_channel
    _preview_ticks = 0
    if (_preview_channel is not None and pygame.mixer.get_init()
            and _preview_channel.get_sound() is _sfx_cache.get("typewriter")):
        _preview_channel.stop()
    _preview_channel = None


def preview_typewriter() -> None:
    """Preview three ticks at the selected volume, replacing any previous preview."""
    global _preview_ticks, _preview_timer
    cancel_typewriter_preview()
    if not _paused and _typewriter_volume > 0:
        _preview_ticks = 3
        _preview_timer = .08  # Let the button click finish first.


def set_paused(paused: bool) -> None:
    """Pause mixer channels and music together when the window loses focus."""
    global _paused
    if _paused == paused:
        return
    _paused = paused
    cancel_typewriter_preview()
    if pygame.mixer.get_init():
        if paused:
            pygame.mixer.pause()
            pygame.mixer.music.pause()
        else:
            pygame.mixer.unpause()
            pygame.mixer.music.unpause()


def get_bgm_volume() -> float:
    return _bgm_volume


def get_sfx_volume() -> float:
    return _sfx_volume


def get_typewriter_volume() -> float:
    return _typewriter_volume


def set_bgm_volume(value: float) -> float:
    """Clamp and apply background music volume, returning the new value."""

    global _bgm_volume
    _bgm_volume = _normalize_volume_step(value)
    _apply_bgm_volume()
    _save_volumes()
    return _bgm_volume


def set_sfx_volume(value: float) -> float:
    """Clamp and apply sound-effect volume, returning the new value."""

    global _sfx_volume
    _sfx_volume = _normalize_volume_step(value)
    _apply_sfx_volume()
    _save_volumes()
    return _sfx_volume


def change_bgm_volume(delta: float) -> float:
    """Adjust background-music volume by ``delta`` and return the result."""

    return set_bgm_volume(_bgm_volume + delta)


def change_sfx_volume(delta: float) -> float:
    """Adjust sound-effect volume by ``delta`` and return the result."""

    return set_sfx_volume(_sfx_volume + delta)


def set_typewriter_volume(value: float) -> float:
    """Adjust typing independently of music and the other sound effects."""
    global _typewriter_volume
    _typewriter_volume = _normalize_volume_step(value)
    _apply_sfx_volume()
    _save_volumes()
    return _typewriter_volume


def change_typewriter_volume(delta: float) -> float:
    return set_typewriter_volume(_typewriter_volume + delta)


def _apply_bgm_volume() -> None:
    if not pygame.mixer.get_init():
        return
    pygame.mixer.music.set_volume(_to_output_volume(_bgm_volume) * _bgm_fade_multiplier)


def _apply_sfx_volume() -> None:
    if not pygame.mixer.get_init():
        return
    for name, sound in _sfx_cache.items():
        volume = _typewriter_volume if name == "typewriter" else _sfx_volume
        sound.set_volume(_to_output_volume(volume))


def _load_volumes() -> None:
    """Load volume settings from disk if available."""

    global _bgm_volume, _sfx_volume, _typewriter_volume
    data: dict[str, Any] = settings_manager.load_settings()
    _bgm_volume = _clamp_volume(data.get("bgm_volume", _bgm_volume))
    _sfx_volume = _clamp_volume(data.get("sfx_volume", _sfx_volume))
    # Preserve the old typing level (including mute) until a separate value is saved.
    _typewriter_volume = _clamp_volume(data.get("typewriter_volume", _sfx_volume))


def _save_volumes() -> None:
    """Persist current volume settings to disk."""

    settings_manager.save_settings(
        {"bgm_volume": _bgm_volume, "sfx_volume": _sfx_volume,
         "typewriter_volume": _typewriter_volume}
    )


def _clamp_volume(value: Any) -> float:
    try:
        return _normalize_volume_step(float(value))
    except (TypeError, ValueError):
        return 1.0


def _normalize_volume_step(value: float) -> float:
    clamped = max(0.0, min(1.0, value))
    return round(clamped / _VOLUME_STEP) * _VOLUME_STEP


def _to_output_volume(value: float) -> float:
    """Map UI volume to a gentler output curve for perceived loudness."""

    normalized = max(0.0, min(1.0, value)) ** _VOLUME_CURVE_EXPONENT
    return normalized * _MAX_OUTPUT_VOLUME


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
    if _paused:
        pygame.mixer.music.pause()


def _start_bgm_fade_out() -> None:
    """Begin fading out the current BGM so we can swap tracks smoothly."""

    global _bgm_fade_state, _bgm_fade_timer
    _bgm_fade_state = "fading_out"
    _bgm_fade_timer = 0.0


def update(dt: float) -> None:
    """Advance BGM fade transitions; should be called once per frame."""

    global _bgm_fade_state, _bgm_fade_timer
    global _bgm_fade_multiplier, _pending_bgm_track, _current_bgm_track
    global _preview_ticks, _preview_timer, _preview_channel

    if _paused or dt <= 0 or not pygame.mixer.get_init():
        return
    if _preview_ticks:
        _preview_timer -= dt
        if _preview_timer <= 0:
            sound = _sfx_cache.get("typewriter")
            if sound and _typewriter_volume > 0:
                _preview_channel = sound.play()
            _preview_ticks -= 1
            _preview_timer = .10
    if _bgm_fade_state is None:
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
