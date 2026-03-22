from __future__ import annotations

import json
from collections import Counter
from datetime import datetime

from config import ANALYTICS_DIR


EVENT_LOG_PATH = ANALYTICS_DIR / "events.jsonl"


def log_event(event_type: str, payload: dict) -> None:
    ANALYTICS_DIR.mkdir(exist_ok=True)
    record = {"timestamp": datetime.utcnow().isoformat(), "event_type": event_type, **payload}
    with EVENT_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def summarize_events() -> dict:
    if not EVENT_LOG_PATH.exists():
        return {
            "total_queries": 0,
            "language_distribution": {},
            "intent_distribution": {},
            "safety_distribution": {},
        }

    language_counter = Counter()
    intent_counter = Counter()
    safety_counter = Counter()
    total_queries = 0

    for line in EVENT_LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("event_type") != "query":
            continue
        total_queries += 1
        language_counter.update([event.get("language", "unknown")])
        intent_counter.update([event.get("intent", "unknown")])
        safety_counter.update([event.get("safety_status", "unknown")])

    return {
        "total_queries": total_queries,
        "language_distribution": dict(language_counter),
        "intent_distribution": dict(intent_counter),
        "safety_distribution": dict(safety_counter),
    }
