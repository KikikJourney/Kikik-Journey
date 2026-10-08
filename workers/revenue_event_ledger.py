#!/usr/bin/env python3
"""Idempotent append-only revenue event ledger used by the M3 sales loop."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path("data/revenue_events.json")


def event_id(event):
    explicit = str(event.get("event_id") or "").strip()
    if explicit:
        return explicit
    raw = json.dumps(event, sort_keys=True, ensure_ascii=False)
    return "auto-" + hashlib.sha256(raw.encode()).hexdigest()[:24]


def load_events(path=DEFAULT_PATH):
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("events", []) if isinstance(data, dict) else data


def append_events(new_events, path=DEFAULT_PATH):
    path = Path(path)
    existing = load_events(path)
    seen = {event_id(item) for item in existing}
    added = 0
    for raw in new_events:
        item = dict(raw)
        item["event_id"] = event_id(item)
        item.setdefault("occurred_at", datetime.now(timezone.utc).isoformat())
        if item["event_id"] in seen:
            continue
        existing.append(item)
        seen.add(item["event_id"])
        added += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"events": existing}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return added, existing
