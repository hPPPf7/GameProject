"""A simple logging system for the investigation diary game.

The log is a scrolling list of strings that are displayed in the UI.  New
messages are appended to ``log_history``.  Users can scroll up and down
through previous messages via the mouse wheel.  ``get_visible_logs``
returns the subset of log entries that should be shown given the current
scroll offset.
"""

log_history: list[str] = []
log_offset: int = 0  # 0 = bottom (most recent)


def add(message: str) -> None:
    global log_offset
    log_history.append(message)
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


def get_visible_logs() -> list[str]:
    """
    Return a slice of the log appropriate for rendering.  The newest
    messages appear at the bottom of the log area, and up to nine lines
    (after wrapping) are drawn.  ``ui_manager`` performs its own text
    wrapping, so this function simply returns the raw log entries.
    """
    start = max(0, len(log_history) - 9 - log_offset)
    end = len(log_history) - log_offset
    return log_history[start:end]