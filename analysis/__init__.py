"""analysis package

Expose helpers used by the UI, while keeping submodules (event_chain, session, etc.).
"""

from __future__ import annotations

import os
import re
from datetime import datetime

try:
    # Prefer python-dateutil if available
    from dateutil import parser as dt_parser  # type: ignore
except Exception:  # pragma: no cover
    dt_parser = None  # Fallback to naive timestamping


def _guess_severity(msg: str) -> str:
    m = msg.lower()
    if "error" in m or "failed" in m:
        return "ERROR"
    if "critical" in m or "fatal" in m:
        return "CRITICAL"
    if "warning" in m or "deprecated" in m:
        return "WARNING"
    return "INFO"


def parse_logs(text: str, fname: str = "log.txt"):
    """Parse raw text logs into a list of simple event objects.

    Returned objects have attributes: timestamp, component, message, severity.
    This mirrors what the UI expects for downstream processing.
    """
    events = []
    for line in str(text).splitlines():
        try:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            ts = datetime.now()
            m = re.match(r"^\[?(\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})", line)
            if m and dt_parser is not None:
                try:
                    ts = dt_parser.parse(m.group(1))  # type: ignore[arg-type]
                except Exception:
                    ts = datetime.now()
            component = os.path.splitext(os.path.basename(fname))[0]
            msg = line.strip()
            sev = _guess_severity(msg)
            events.append(
                {'timestamp': ts, 'component': component, 'message': msg, 'severity': sev}
            )
        except Exception:
            continue
    events.sort(key=lambda e: getattr(e, "timestamp", datetime.now()))
    return events

