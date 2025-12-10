"""A structured logging system for the investigation diary game.

The log keeps track of ``LogEntry`` objects that include text, category,
and an ``event_id`` used to visually group related messages.  Users can
scroll through the history via the mouse wheel.  ``get_visible_lines``
returns the wrapped text lines that should be displayed given the
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
log_offset: int = 0  # 以行數計算的捲動位移；0 = 底部（最新）
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
    # 新增訊息時重設捲動位移，確保最新內容可見。
    log_offset = 0


def scroll_to_bottom() -> None:
    global log_offset
    log_offset = 0


def reset() -> None:
    """Clear the log and restore default counters."""

    global log_history, log_offset, _current_event_id, _next_event_id
    log_history = []
    log_offset = 0
    _current_event_id = None
    _next_event_id = 1


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

    wrapped: list[tuple[str, str]] = []
    for entry in log_history:
        lines = wrap_text(entry.text, font, max_width) if entry.text else [""]
        wrapped.extend((line, entry.category) for line in lines)
    return wrapped


def scroll_up(font, max_width: int, visible_lines: int = 9) -> None:
    global log_offset
    wrapped = _get_wrapped_lines(font, max_width)
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
    }


def load_state(state: dict | None) -> None:
    """Restore the log from serialized data."""

    reset()
    if not state:
        return

    global log_history, log_offset, _current_event_id, _next_event_id
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


def get_visible_lines(font, max_width: int, visible_lines: int = 9) -> list[tuple[str, str]]:
    """Return the wrapped lines that should be rendered for the log panel."""

    wrapped = _get_wrapped_lines(font, max_width)
    if not wrapped:
        return []

    max_offset = max(0, len(wrapped) - visible_lines)
    offset = min(log_offset, max_offset)
    start = max(0, len(wrapped) - visible_lines - offset)
    end = len(wrapped) - offset
    return wrapped[start:end]