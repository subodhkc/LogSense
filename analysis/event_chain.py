# analysis/event_chain.py
from __future__ import annotations
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from datamodels.events import Event

@dataclass(frozen=True)
class ChainSpec:
    steps: List[Dict[str, Any]]
    window_sec: int = 300

@dataclass(frozen=True)
class ChainHit:
    indices: List[int]
    start: datetime
    end: datetime
    label: str

def _match_step(ev: Event, filt: Dict[str, Any]) -> bool:
    lvl = filt.get("level")
    if lvl and (ev.level or "").upper() != str(lvl).upper():
        return False
    eid = filt.get("event_id")
    if eid and str(ev.event_id) != str(eid):
        return False
    tag = filt.get("tag")
    if tag and tag not in (ev.tags or []):
        return False
    substr = filt.get("contains")
    if substr and substr.lower() not in ev.message.lower():
        return False
    return True

def detect_sequences(events: List[Event], spec: ChainSpec, label: str = "SEQ") -> List[ChainHit]:
    seq = [e for e in events if e.ts]
    out: List[ChainHit] = []
    n = len(seq)
    k = len(spec.steps)
    if k == 0 or n == 0:
        return out
    win = timedelta(seconds=spec.window_sec)

    for i in range(0, n):
        if not _match_step(seq[i], spec.steps[0]):
            continue
        idxs = [i]
        t0 = seq[i].ts
        ok = True
        last_j = i
        for s in range(1, k):
            found = False
            for j in range(last_j + 1, n):
                if seq[j].ts - t0 > win:
                    ok = False
                    break
                if _match_step(seq[j], spec.steps[s]):
                    found = True
                    idxs.append(j)
                    last_j = j
                    break
            if not ok or not found:
                ok = False
                break
        if ok:
            out.append(ChainHit(indices=idxs, start=seq[idxs[0]].ts, end=seq[idxs[-1]].ts, label=label))
    return out
