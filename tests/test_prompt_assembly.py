from ai_rca import format_logs_for_ai

class Ev:
    def __init__(self, ts, sev, comp, msg):
        self.timestamp = ts
        self.severity = sev
        self.component = comp
        self.message = msg

def test_format_logs_for_ai_includes_context_and_filters_errors():
    events = [
        Ev("2025-01-01 00:00:01", "INFO", "Agent", "Started"),
        Ev("2025-01-01 00:00:02", "ERROR", "Installer", "Failed to copy file"),
        Ev("2025-01-01 00:00:03", "CRITICAL", "Boot", "Halt"),
    ]
    metadata = {"OS": "Win11", "Build": "26000"}
    test_results = [
        {"Step": "1", "Status": "Pass", "Step Action": "Open App"},
        {"Step": "2", "Status": "Fail", "Step Action": "Install BIOS"},
    ]
    context = {
        "issue_description": "Provisioning fails intermittently",
        "expected_behavior": "Install succeeds",
        "reproduction_steps": "Run installer",
        "build_changes": "Updated BIOS package",
        "test_environment": "Lab",
        "issue_severity": "High",
        "issue_frequency": "3/10",
        "app_name": "SKC",
        "app_version": "1.2.3",
    }

    text = format_logs_for_ai(events, metadata, test_results, context)

    assert "USER CONTEXT" in text
    assert "Issue Description" in text and "Provisioning fails intermittently" in text
    assert "SYSTEM METADATA" in text and "OS: Win11" in text
    assert "TEST PLAN RESULTS" in text and "Step 2" in text
    # Only ERROR/CRITICAL should be listed under key events
    assert "ERROR" in text and "CRITICAL" in text
    assert "INFO" not in text.split("=== ERROR & CRITICAL EVENTS ===")[-1]
