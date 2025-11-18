"""Centralised sound loading and playback utilities."""

from __future__ import annotations

import pygame

from paths import res_path

_sfx_cache: dict[str, pygame.mixer.Sound] = {}
_initialized = False

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

    if not pygame.mixer.get_init():
        pygame.mixer.init()

    for key, filename in SFX_FILES.items():
        _sfx_cache[key] = pygame.mixer.Sound(
            res_path("assets", "sounds", "sfx", filename)
        )

    _initialized = True


def play_bgm(track: str = "Music-1.mp3") -> None:
    """Start background music in a loop from the bgm directory."""

    init_sound()
    pygame.mixer.music.load(res_path("assets", "sounds", "bgm", track))
    pygame.mixer.music.play(-1)


def play_sfx(name: str) -> None:
    """Play a named sound effect if it exists."""

    init_sound()
    sound = _sfx_cache.get(name)
    if sound:
        sound.play()