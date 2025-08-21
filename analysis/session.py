# analysis/session.py
from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from datamodels.events import Event

@dataclass(frozen=True)
class Session:
    key: str
    user: Optional[str]
    start: datetime
    end: Optional[datetime]
    duration_sec: Optional[float]
    source: str
    meta: Dict[str, Any]

def correlate_start_end(events: List[Event], start_contains: str, end_contains: str,
                        correlate_key: str = "process", key_from_meta: str | None = None) -> List[Session]:
    seq = [e for e in events if e.ts]
    open_map: Dict[str, Event] = {}
    out: List[Session] = []

    def key_of(e: Event) -> str:
        if key_from_meta and e.meta and key_from_meta in e.meta:
            return str(e.meta[key_from_meta])
        return f"{correlate_key}:{hash(e.message) % (10**6)}"

    for e in sorted(seq, key=lambda x: x.ts):
        if start_contains in e.message:
            k = key_of(e)
            open_map[k] = e
        elif end_contains in e.message:
            k = key_of(e)
            s = open_map.pop(k, None)
            if s:
                out.append(Session(
                    key=k, user=None, start=s.ts, end=e.ts,
                    duration_sec=(e.ts - s.ts).total_seconds(),
                    source=e.source, meta={}
                ))
    for k, s in open_map.items():
        out.append(Session(key=k, user=None, start=s.ts, end=None, duration_sec=None, source=s.source, meta={}))
    return out
