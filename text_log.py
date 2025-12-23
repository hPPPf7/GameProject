"""A structured logging system for the investigation diary game.

The log keeps track of ``LogEntry`` objects that include text, category,
and an ``event_id`` used to visually group related messages.  Users can
scroll through the history via the mouse wheel.  ``get_visible_lines``
returns the wrapped text lines that should be displayed given the
current scroll offset.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

import settings_manager


def _load_typewriter_preference() -> bool:
    """Read the persisted typewriter toggle; default to True on missing/invalid data."""

    settings = settings_manager.load_settings()
    stored = settings.get("typewriter_enabled")
    if isinstance(stored, bool):
        return stored
    if stored is None:
        return True
    return bool(stored)


def _save_typewriter_preference(enabled: bool) -> None:
    """Write the current typewriter toggle to the shared settings file."""

    settings_manager.save_settings({"typewriter_enabled": bool(enabled)})


def _load_dev_log_preference() -> bool:
    """Read the persisted dev log toggle; default to False when missing/invalid."""

    settings = settings_manager.load_settings()
    stored = settings.get("dev_log_enabled")
    if isinstance(stored, bool):
        return stored
    if stored is None:
        return False
    return bool(stored)


def _save_dev_log_preference(enabled: bool) -> None:
    """Write the current dev log toggle to the shared settings file."""

    settings_manager.save_settings({"dev_log_enabled": bool(enabled)})


@dataclass
class LogEntry:
    text: str
    category: str = "narration"
    event_id: int | None = None
    on_show: Optional[Callable[[], None]] = None


log_history: list[LogEntry] = []
log_offset: int = 0  # 以行數計算的捲動位移；0 = 底部（最新）
_current_event_id: int | None = None
_next_event_id: int = 1
_pending_entries: List[LogEntry] = []
_active_entry: Optional[LogEntry] = None
_active_progress: float = 0.0
_typewriter_enabled: bool = _load_typewriter_preference()
_typewriter_override: bool | None = None
_dev_log_enabled: bool = _load_dev_log_preference()
TYPEWRITER_SPEED = 40.0  # characters per second
_TYPEWRITER_CATEGORIES = {"narration"}
_DEV_LOG_CATEGORIES = {"dev"}
_log_version: int = 0
_wrap_cache: list[tuple[str, str]] = []
_wrap_cache_version: int = -1
_wrap_cache_key: tuple[int, int] | None = None


def _invalidate_wrap_cache() -> None:
    global _log_version, _wrap_cache_version, _wrap_cache
    _log_version += 1
    _wrap_cache_version = -1
    _wrap_cache = []


def start_event(title: str | None = None) -> None:
    """Begin a new logical event block in the log."""

    global log_offset, _current_event_id, _next_event_id
    _current_event_id = _next_event_id
    _next_event_id += 1

    if log_history:
        _enqueue(LogEntry("", category="spacer", event_id=_current_event_id))

    if title:
        header = f"── 事件 {_current_event_id:02d}：{title} ──"
    else:
        header = f"── 事件 {_current_event_id:02d} ──"
    _enqueue(LogEntry(header, category="event_header", event_id=_current_event_id))

    log_offset = 0


def add(
    message: str,
    *,
    category: str = "narration",
    event_id: int | None = None,
    on_show: Optional[Callable[[], None]] = None,
) -> None:
    global _current_event_id
    if category in _DEV_LOG_CATEGORIES and not _dev_log_enabled:
        return
    if event_id is None:
        event_id = _current_event_id
    _enqueue(LogEntry(message, category=category, event_id=event_id, on_show=on_show))


def scroll_to_bottom() -> None:
    global log_offset
    log_offset = 0


def reset() -> None:
    """Clear the log and restore default counters."""

    global log_history, log_offset, _current_event_id, _next_event_id
    global _pending_entries, _active_entry, _active_progress, _typewriter_enabled
    global _typewriter_override, _dev_log_enabled

    log_history = []
    log_offset = 0
    _current_event_id = None
    _next_event_id = 1
    _pending_entries = []
    _active_entry = None
    _active_progress = 0.0
    _typewriter_enabled = _load_typewriter_preference()
    _typewriter_override = None
    _dev_log_enabled = _load_dev_log_preference()
    _invalidate_wrap_cache()


def clear_history() -> None:
    """Clear visible log history without touching the typewriter setting."""

    global log_history, log_offset, _current_event_id, _next_event_id
    global _pending_entries, _active_entry, _active_progress

    log_history = []
    log_offset = 0
    _current_event_id = None
    _next_event_id = 1
    _pending_entries = []
    _active_entry = None
    _active_progress = 0.0
    _invalidate_wrap_cache()


def get_current_event_id() -> int | None:
    return _current_event_id


def snapshot_history() -> list[dict]:
    return [
        {
            "text": entry.text,
            "category": entry.category,
            "event_id": entry.event_id,
        }
        for entry in log_history
    ]


def set_history(entries: list[dict]) -> None:
    clear_history()
    for entry in entries:
        log_history.append(
            LogEntry(
                text=entry.get("text", ""),
                category=entry.get("category", "narration"),
                event_id=entry.get("event_id"),
            )
        )
    scroll_to_bottom()
    _invalidate_wrap_cache()


def wrap_text(text: str, font, max_width: int) -> list[str]:
    """Wrap ``text`` so that each line fits within ``max_width`` pixels."""

    if not text:
        return [""]

    lines: list[str] = []
    current = ""
    for ch in text:
        if ch == "\n":
            lines.append(current)
            current = ""
            continue

        if font.size(current + ch)[0] > max_width and current:
            lines.append(current)
            current = ch
        else:
            current += ch

    lines.append(current)
    return lines


def _get_wrapped_lines(font, max_width: int) -> list[tuple[str, str]]:
    """Return every log line after wrapping along with its category."""

    global _wrap_cache_version, _wrap_cache_key
    cache_key = (id(font), max_width)
    if _wrap_cache_version == _log_version and _wrap_cache_key == cache_key:
        return _wrap_cache

    wrapped: list[tuple[str, str]] = []
    for entry in log_history:
        if entry.category in _DEV_LOG_CATEGORIES and not _dev_log_enabled:
            continue
        lines = wrap_text(entry.text, font, max_width) if entry.text else [""]
        wrapped.extend((line, entry.category) for line in lines)
    _wrap_cache_key = cache_key
    _wrap_cache_version = _log_version
    _wrap_cache[:] = wrapped
    return wrapped


def _effective_typewriter_enabled() -> bool:
    if _typewriter_override is None:
        return _typewriter_enabled
    return _typewriter_override


def _should_typewriter(entry: LogEntry) -> bool:
    return _effective_typewriter_enabled() and entry.category in _TYPEWRITER_CATEGORIES


def _trigger_on_show(entry: LogEntry) -> None:
    callback = entry.on_show
    if callback:
        entry.on_show = None
        try:
            callback()
        except Exception:
            # Avoid crashing the log pipeline because of side-effect failures.
            pass


def _append_entry(entry: LogEntry) -> None:
    """Append entry to history and fire its on_show callback once."""
    global log_offset
    log_history.append(entry)
    _trigger_on_show(entry)
    log_offset = 0
    _invalidate_wrap_cache()


def _start_active_entry(entry: LogEntry) -> None:
    global _active_entry, _active_progress
    _active_entry = entry
    _active_progress = 0.0


def _enqueue(entry: LogEntry) -> None:
    """Insert a new entry, respecting the typewriter queue."""
    if _active_entry:
        _pending_entries.append(entry)
        return

    if _should_typewriter(entry):
        _start_active_entry(entry)
        return

    _append_entry(entry)


def _flush_pending_entries() -> None:
    """Push all pending entries directly into history (no animation)."""
    global log_offset, _pending_entries, _active_entry, _active_progress
    if _active_entry:
        _append_entry(_active_entry)
        _active_entry = None
        _active_progress = 0.0
    while _pending_entries:
        _append_entry(_pending_entries.pop(0))
    log_offset = 0


def _promote_pending() -> None:
    """Move queued entries into the active slot or history when possible."""
    global _active_entry, _active_progress
    if _active_entry:
        return
    while _pending_entries:
        candidate = _pending_entries.pop(0)
        if _should_typewriter(candidate):
            _start_active_entry(candidate)
            return
        _append_entry(candidate)


def scroll_up(font, max_width: int, visible_lines: int = 9) -> None:
    global log_offset
    wrapped = list(_get_wrapped_lines(font, max_width))
    if _active_entry:
        visible_chars = int(_active_progress)
        visible_text = _active_entry.text[:visible_chars]
        lines = wrap_text(visible_text, font, max_width) if visible_text else [""]
        wrapped.extend((line, _active_entry.category) for line in lines)
    max_offset = max(0, len(wrapped) - visible_lines)
    if log_offset < max_offset:
        log_offset += 1


def scroll_down() -> None:
    global log_offset
    if log_offset > 0:
        log_offset -= 1


def export_state() -> dict:
    """Serialize the current log for persistence."""

    return {
        "log_history": [
            {
                "text": entry.text,
                "category": entry.category,
                "event_id": entry.event_id,
            }
            for entry in log_history
        ],
        "log_offset": log_offset,
        "current_event_id": _current_event_id,
        "next_event_id": _next_event_id,
        "typewriter_enabled": _typewriter_enabled,
        "pending_entries": [
            {
                "text": entry.text,
                "category": entry.category,
                "event_id": entry.event_id,
            }
            for entry in _pending_entries
        ],
        "active_entry": {
            "text": _active_entry.text,
            "category": _active_entry.category,
            "event_id": _active_entry.event_id,
        }
        if _active_entry
        else None,
        "active_progress": _active_progress,
    }


def load_state(state: dict | None) -> None:
    """Restore the log from serialized data."""

    reset()
    if not state:
        return

    global log_history, log_offset, _current_event_id, _next_event_id
    global _pending_entries, _active_entry, _active_progress, _typewriter_enabled
    global _dev_log_enabled
    history = []
    for entry in state.get("log_history", []):
        history.append(
            LogEntry(
                text=entry.get("text", ""),
                category=entry.get("category", "narration"),
                event_id=entry.get("event_id"),
            )
        )

    log_history = history
    log_offset = state.get("log_offset", 0)
    _current_event_id = state.get("current_event_id")
    _next_event_id = state.get("next_event_id", 1)
    _typewriter_enabled = state.get("typewriter_enabled", True)
    _save_typewriter_preference(_typewriter_enabled)
    _dev_log_enabled = _load_dev_log_preference()

    _pending_entries = [
        LogEntry(
            text=entry.get("text", ""),
            category=entry.get("category", "narration"),
            event_id=entry.get("event_id"),
        )
        for entry in state.get("pending_entries", [])
    ]

    active_data = state.get("active_entry")
    if active_data and _typewriter_enabled:
        _active_entry = LogEntry(
            text=active_data.get("text", ""),
            category=active_data.get("category", "narration"),
            event_id=active_data.get("event_id"),
        )
        _active_progress = float(state.get("active_progress", 0.0))
        _active_progress = max(0.0, min(_active_progress, len(_active_entry.text)))
    else:
        _active_entry = None
        _active_progress = 0.0
        if active_data:
            # If typewriter is disabled, immediately show the pending text.
            log_history.append(
                LogEntry(
                    text=active_data.get("text", ""),
                    category=active_data.get("category", "narration"),
                    event_id=active_data.get("event_id"),
                )
            )
            log_offset = 0
        if not _typewriter_enabled and _pending_entries:
            log_history.extend(_pending_entries)
            _pending_entries = []
            log_offset = 0
    _invalidate_wrap_cache()


def get_visible_lines(font, max_width: int, visible_lines: int = 9) -> list[tuple[str, str]]:
    """Return the wrapped lines that should be rendered for the log panel."""

    wrapped = list(_get_wrapped_lines(font, max_width))
    if _active_entry:
        visible_chars = int(_active_progress)
        visible_text = _active_entry.text[:visible_chars]
        lines = wrap_text(visible_text, font, max_width) if visible_text else [""]
        wrapped.extend((line, _active_entry.category) for line in lines)
    if not wrapped:
        return []

    max_offset = max(0, len(wrapped) - visible_lines)
    offset = min(log_offset, max_offset)
    start = max(0, len(wrapped) - visible_lines - offset)
    end = len(wrapped) - offset
    return wrapped[start:end]


def update_typewriter(dt: float) -> None:
    """Advance the typewriter animation by ``dt`` seconds."""
    global _active_progress, log_offset, _active_entry

    if not _effective_typewriter_enabled():
        # Keep scroll position intact when the typewriter is disabled; only flush
        # queued text once if there is anything pending.
        if _active_entry or _pending_entries:
            _flush_pending_entries()
        return

    if not _active_entry:
        _promote_pending()
        return

    _active_progress += TYPEWRITER_SPEED * dt

    if _active_progress >= len(_active_entry.text):
        # Finish the entry and move on.
        _append_entry(_active_entry)
        _active_progress = 0.0
        _active_entry = None
        _promote_pending()


def set_typewriter_enabled(enabled: bool) -> None:
    """Toggle the typewriter effect; flushing queued text if disabling."""
    global _typewriter_enabled
    if _typewriter_enabled == enabled:
        return
    _typewriter_enabled = enabled
    _save_typewriter_preference(_typewriter_enabled)
    if not enabled:
        _flush_pending_entries()
    else:
        _promote_pending()


def is_typewriter_enabled() -> bool:
    return _typewriter_enabled


def set_dev_log_enabled(enabled: bool) -> None:
    """Toggle dev log visibility and persist the setting."""
    global _dev_log_enabled
    if _dev_log_enabled == enabled:
        return
    _dev_log_enabled = enabled
    _save_dev_log_preference(_dev_log_enabled)
    _invalidate_wrap_cache()


def is_dev_log_enabled() -> bool:
    return _dev_log_enabled


def is_typewriter_animating() -> bool:
    """Return True while the current entry is still revealing characters."""

    return bool(_active_entry and _effective_typewriter_enabled())


def set_typewriter_override(enabled: bool | None) -> None:
    global _typewriter_override
    _typewriter_override = enabled
    if enabled is False:
        _flush_pending_entries()
    elif enabled is True:
        _promote_pending()
