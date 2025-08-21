# analysis/templates.py
from __future__ import annotations
import re
from typing import Dict, List, Tuple
from datamodels.events import Event

class _NaiveTemplateMiner:
    """
    Fallback template miner when Drain3 is unavailable.
    Replaces volatile tokens (numbers, hex, GUIDs, IPs) to yield a stable template.
    Deterministic and fast.
    """
    _GUID = re.compile(r"\b\{?[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\}?\b")
    _HEX = re.compile(r"\b0x[0-9A-Fa-f]+\b")
    _IP  = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _NUM = re.compile(r"\b\d+\b")

    def add_log_message(self, msg: str) -> str:
        t = self._GUID.sub("<GUID>", msg)
        t = self._HEX.sub("<HEX>", t)
        t = self._IP.sub("<IP>", t)
        # keep small counters to avoid over-generalization
        t = self._NUM.sub(lambda m: "<N>" if len(m.group(0)) > 2 else m.group(0), t)
        return t

def _drain3_available() -> bool:
    try:
        import drain3  # noqa: F401
        return True
    except Exception:
        return False

class TemplateExtractor:
    """
    Thin wrapper: uses Drain3 if present, otherwise the naive miner.
    Produces per-event meta: template_id, template, and maintains a count summary.
    """
    def __init__(self) -> None:
        self._use_drain = _drain3_available()
        if self._use_drain:
            from drain3 import TemplateMiner
            from drain3.template_miner_config import TemplateMinerConfig
            cfg = TemplateMinerConfig()
            cfg.load_default_config()
            cfg.profiling_enabled = False
            self._tm = TemplateMiner(config=cfg)
        else:
            self._tm = _NaiveTemplateMiner()
        self._counts: Dict[str, int] = {}
        self._id_for_template: Dict[str, str] = {}
        self._next_id = 1

    def _id_for(self, template: str) -> str:
        if template not in self._id_for_template:
            self._id_for_template[template] = f"T{self._next_id:04d}"
            self._next_id += 1
        return self._id_for_template[template]

    def assign(self, events: List[Event]) -> List[Event]:
        out: List[Event] = []
        if self._use_drain:
            for ev in events:
                r = self._tm.add_log_message(ev.message)
                template = r["template_mined"] if r else ev.message
                tid = self._id_for(template)
                self._counts[template] = self._counts.get(template, 0) + 1
                meta = dict(ev.meta)
                meta["template_id"] = tid
                meta["template"] = template
                out.append(Event(ts=ev.ts, source=ev.source, level=ev.level, event_id=ev.event_id,
                                 message=ev.message, meta=meta, tags=list(ev.tags)))
        else:
            for ev in events:
                template = self._tm.add_log_message(ev.message)
                tid = self._id_for(template)
                self._counts[template] = self._counts.get(template, 0) + 1
                meta = dict(ev.meta)
                meta["template_id"] = tid
                meta["template"] = template
                out.append(Event(ts=ev.ts, source=ev.source, level=ev.level, event_id=ev.event_id,
                                 message=ev.message, meta=meta, tags=list(ev.tags)))
        return out

    def summary(self) -> List[Tuple[str, int, str]]:
        """
        Returns a stable list of (template_id, count, template), sorted by count desc then id.
        """
        rows: List[Tuple[str, int, str]] = []
        for template, cnt in self._counts.items():
            tid = self._id_for(template)
            rows.append((tid, cnt, template))
        return sorted(rows, key=lambda r: (-r[1], r[0]))
