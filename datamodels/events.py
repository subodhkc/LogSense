# datamodels/events.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

@dataclass(frozen=True)
class Event:
    ts: Optional[datetime]          # normalized UTC timestamp (None if unknown)
    source: str                     # e.g., "evtx:System", "msi", "text:app"
    level: Optional[str]            # INFO/WARN/ERROR/etc., if available
    event_id: Optional[str]         # numeric or string code if available
    message: str                    # full message text
    meta: Dict[str, str] = field(default_factory=dict)   # arbitrary parsed fields
    tags: List[str] = field(default_factory=list)        # detector-assigned tags
