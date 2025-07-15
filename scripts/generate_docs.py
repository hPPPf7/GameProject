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


def _format_result_details(result):
    """Combine effect and other result fields into a readable string."""
    effect = result.get("effect") or {}
    others = {k: v for k, v in result.items() if k not in {"text", "effect"}}
    parts = []
    if effect:
        parts.extend(f"{k}:{v}" for k, v in effect.items())
    parts.extend(f"{k}:{v}" for k, v in others.items())
    return "; ".join(parts)


def write_events_md(events):
    out = DOCS_DIR / "events.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("# 劇情事件\n\n")
        if not events:
            f.write("尚未提供事件資料。\n")
            return

        for ev in events:
            f.write(f"## {ev.get('id', '')} ({ev.get('type', '')})\n\n")
            f.write(ev.get("text", "") + "\n\n")
            cond = ev.get("condition")
            if cond:
                f.write("**條件**: " + json.dumps(cond, ensure_ascii=False) + "\n\n")

            f.write("| 選項 | 結果 | 影響 |\n")
            f.write("| --- | --- | --- |\n")
            for opt in ev.get("options", []):
                opt_text = str(opt.get("text", "")).replace("|", "\\|")
                result = opt.get("result", {})
                res_text = str(result.get("text", "")).replace("|", "\\|")
                details = _format_result_details(result).replace("|", "\\|")
                f.write(f"| {opt_text} | {res_text} | {details} |\n")
            f.write("\n")


def write_timeline_md(events, source_name="data/events.json"):
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
        f.write(f"\n此圖可依 `{source_name}` 進行擴充。\n")


def main():
    characters = load_json(DATA_DIR / "characters.json")

    # Prefer events.json if it exists, otherwise fall back to story_data.json
    events_path = DATA_DIR / "events.json"
    if not events_path.exists():
        events_path = DATA_DIR / "story_data.json"

    events = load_json(events_path)

    write_characters_md(characters)
    write_events_md(events)
    write_timeline_md(events, str(events_path.relative_to(ROOT)))


if __name__ == "__main__":
    main()
