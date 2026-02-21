from __future__ import annotations
import json
from typing import Any, Dict, Iterable


def read_events(path_jsonl: str) -> Iterable[Dict[str, Any]]:
    with open(path_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def replay_print(path_jsonl: str) -> None:
    for ev in read_events(path_jsonl):
        print(ev)