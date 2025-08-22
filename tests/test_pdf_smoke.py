# tests/test_pdf_smoke.py
# Lightweight end-to-end PDF generation smoke test
from types import SimpleNamespace
from datetime import datetime, UTC
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import report


def _fake_event(ts: str, component: str, severity: str, message: str):
    # Use a SimpleNamespace to mimic the event object with expected attributes
    return SimpleNamespace(timestamp=ts, component=component, severity=severity, message=message)


def test_pdf_generation_smoke():
    events = [
        _fake_event(datetime.now(UTC).isoformat(), "Installer", "INFO", "Setup started"),
        _fake_event(datetime.now(UTC).isoformat(), "Installer", "ERROR", "MSI action failed"),
        _fake_event(datetime.now(UTC).isoformat(), "System", "WARNING", "Low disk space"),
    ]

    metadata = {
        "Host": "test-host",
        "OS": "Windows 11",
        "User": "ci-user",
    }

    # Minimal context
    user_context = {
        "app_version": "1.0.0",
        "test_environment": "CI",
        "deployment_method": "Docker",
        "issue_severity": "Medium",
        "issue_description": "CI smoke test",
    }

    pdf_bytes = report.generate_pdf(
        events=events,
        metadata=metadata,
        test_results=[],
        recommendations={},
        user_name="CI",
        app_name="LogSense",
        ai_summary=None,
        user_context=user_context,
    )

    assert isinstance(pdf_bytes, (bytes, bytearray))
    # Ensure non-trivial output size
    assert len(pdf_bytes) > 1000
