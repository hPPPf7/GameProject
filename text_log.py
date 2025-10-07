"""A structured logging system for the investigation diary game.

The log keeps track of ``LogEntry`` objects that include text, category,
and an ``event_id`` used to visually group related messages.  Users can
scroll through the history via the mouse wheel.  ``get_visible_logs``
returns the subset of log entries that should be displayed given the
current scroll offset.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LogEntry:
    text: str
    category: str = "narration"
    event_id: int | None = None


log_history: list[LogEntry] = []
log_offset: int = 0  # 0 = bottom (most recent)
_current_event_id: int | None = None
_next_event_id: int = 1


def start_event(title: str | None = None) -> None:
    """Begin a new logical event block in the log."""

    global log_offset, _current_event_id, _next_event_id
    _current_event_id = _next_event_id
    _next_event_id += 1

    if log_history:
        log_history.append(LogEntry("", category="spacer", event_id=_current_event_id))

    if title:
        header = f"── 事件 {_current_event_id:02d}：{title} ──"
    else:
        header = f"── 事件 {_current_event_id:02d} ──"
    log_history.append(LogEntry(header, category="event_header", event_id=_current_event_id))

    log_offset = 0


def add(message: str, *, category: str = "narration", event_id: int | None = None) -> None:
    global log_offset, _current_event_id
    if event_id is None:
        event_id = _current_event_id
    log_history.append(LogEntry(message, category=category, event_id=event_id))
    # When a new message is added reset the scroll offset so the latest
    # messages are visible.
    log_offset = 0


def scroll_to_bottom() -> None:
    global log_offset
    log_offset = 0


def scroll_up() -> None:
    global log_offset
    # Only scroll up if there are more than 9 lines above the current view
    if log_offset + 9 < len(log_history):
        log_offset += 1


def scroll_down() -> None:
    global log_offset
    if log_offset > 0:
        log_offset -= 1


def get_visible_logs() -> list[LogEntry]:
    """
    Return a slice of the log appropriate for rendering.  The newest
    messages appear at the bottom of the log area, and up to nine entries
    (prior to wrapping) are drawn.  ``ui_manager`` performs its own text
    wrapping, so this function simply returns the raw log entries.
    """

    start = max(0, len(log_history) - 9 - log_offset)
    end = len(log_history) - log_offset
    return log_history[start:end]