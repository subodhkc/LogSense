"""
redaction.py - Redaction engine for masking sensitive info from logs
"""

import re
import zipfile
from io import BytesIO
from types import SimpleNamespace
import os
import json

class Redactor:
    def __init__(self, patterns):
        self.patterns = patterns

    def redact_string(self, text):
        """Apply all redaction patterns to a single string."""
        if not isinstance(text, str):
            return text
        for pattern in self.patterns:
            if isinstance(pattern, dict) and "pattern" in pattern and "replacement" in pattern:
                text = re.sub(pattern["pattern"], pattern["replacement"], text, flags=re.IGNORECASE)
        return text

    def redact_events(self, events):
        """Apply redaction to all InstallEvent objects."""
        redacted = []
        for ev in events:
            redacted.append(
                SimpleNamespace(
                    timestamp=getattr(ev, "timestamp", None),
                    component=self.redact_string(getattr(ev, "component", "")),
                    message=self.redact_string(getattr(ev, "message", "")),
                    severity=getattr(ev, "severity", "INFO"),
                )
            )
        return redacted

    def redact_metadata(self, metadata):
        """Redact fields in system metadata."""
        redacted_meta = {}
        for k, v in metadata.items():
            redacted_meta[k] = self.redact_string(str(v))
        return redacted_meta

    def redact_text(self, text):
        """Redact a raw log file content (string)."""
        return self.redact_string(text)


def get_redacted_zip(zipfile_obj, redactor):
    """Redacts log/txt files inside a ZIP and returns a new redacted ZIP as BytesIO."""
    redacted_zip = BytesIO()
    with zipfile.ZipFile(redacted_zip, mode="w") as zout:
        with zipfile.ZipFile(zipfile_obj) as zin:
            for file in zin.namelist():
                if file.endswith(".log") or file.endswith(".txt"):
                    # Sanitize entry name to prevent path traversal in output ZIP
                    norm = os.path.normpath(file).replace("\\", "/")
                    parts = [p for p in norm.split("/") if p not in ("", ".", "..")]
                    safe_name = "/".join(parts) if parts else os.path.basename(norm)
                    if not safe_name:
                        continue
                    with zin.open(file) as f:
                        try:
                            raw = f.read().decode("utf-8", errors="ignore")
                            clean = redactor.redact_string(raw)
                            zout.writestr(safe_name, clean)
                        except Exception:
                            continue
    redacted_zip.seek(0)
    return redacted_zip


def _load_default_patterns():
    """Try to load default redaction patterns from config/redact.json if present."""
    candidates = [
        os.path.join(os.path.dirname(__file__), "config", "redact.json"),
        os.path.join(os.getcwd(), "config", "redact.json"),
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Expect a list of {"pattern": "...", "replacement": "..."}
                    if isinstance(data, list):
                        return data
        except Exception:
            continue
    # Sensible minimal defaults
    return [
        {"pattern": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "replacement": "<email>"},
        {"pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "replacement": "<ip>"},
        {"pattern": r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b", "replacement": "<uuid>"},
    ]


def apply_redaction(events, metadata, patterns=None):
    """Convenience function used by the UI to redact events and metadata.

    patterns: list of {"pattern": str, "replacement": str}. If None or empty,
    will try to load defaults from config/redact.json, otherwise use built-ins.
    Returns (redacted_events, redacted_metadata).
    """
    if not patterns:
        patterns = _load_default_patterns()
    redactor = Redactor(patterns)
    return redactor.redact_events(events), redactor.redact_metadata(metadata)
