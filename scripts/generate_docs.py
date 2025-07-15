#!/usr/bin/env python3
"""Generate Markdown docs from JSON data."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"


def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def write_characters_md(characters):
    out = DOCS_DIR / "characters.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("# 角色資料\n\n")
        if not characters:
            f.write("尚未提供角色資料。\n")
            return
        keys = sorted({k for c in characters for k in c})
        f.write("| " + " | ".join(keys) + " |\n")
        f.write("| " + " | ".join(["---"] * len(keys)) + " |\n")
        for char in characters:
            f.write("| " + " | ".join(str(char.get(k, "")) for k in keys) + " |\n")


def write_events_md(events):
    out = DOCS_DIR / "events.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("# 劇情事件\n\n")
        if not events:
            f.write("尚未提供事件資料。\n")
            return
        headers = ["id", "type", "text"]
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")
        for ev in events:
            row = [ev.get(h, "") for h in headers]
            row[2] = row[2].replace("|", "\|")  # escape pipes
            f.write("| " + " | ".join(row) + " |\n")


def write_timeline_md(events):
    out = DOCS_DIR / "timeline.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("# 劇情流程\n\n")
        f.write("```mermaid\n")
        f.write("graph TD\n")
        previous = None
        for i, ev in enumerate(events, 1):
            node = f"E{i}['{ev.get('id', '')}']"
            if previous:
                f.write(f"    {previous} --> {node}\n")
            else:
                f.write(f"    start((Start)) --> {node}\n")
            previous = node
        if not events:
            f.write("    start((Start))\n")
        f.write("```\n")
        f.write("\n此圖可依 `data/events.json` 進行擴充。\n")


def main():
    characters = load_json(DATA_DIR / "characters.json")
    events = load_json(DATA_DIR / "events.json")
    write_characters_md(characters)
    write_events_md(events)
    write_timeline_md(events)


if __name__ == "__main__":
    main()