# text_log.py

log_history = []
log_offset = 0  # 目前滾動位置（0 = 最新）

def add(message):
    global log_offset
    log_history.append(message)
    log_offset = 0  # 每次加入新訊息時滾到底部

def scroll_to_bottom():
    global log_offset
    log_offset = 0

def scroll_up():
    global log_offset
    if log_offset + 9 < len(log_history):
        log_offset += 1

def scroll_down():
    global log_offset
    if log_offset > 0:
        log_offset -= 1

def get_visible_logs():
    start = max(0, len(log_history) - 9 - log_offset)
    end = len(log_history) - log_offset
    return log_history[start:end]