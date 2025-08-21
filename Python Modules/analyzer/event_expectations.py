# analyzer/event_expectations.py

# Define a list of critical events expected to appear in healthy logs
EXPECTED_EVENTS = [
    "System Ready",
    "Driver Initialized",
    "Self-Test Passed",
    "Install Success"
]

def find_missing_events(log_lines):
    """
    Checks whether expected event markers are missing from the logs.

    This function is useful for detecting:
    - Incomplete installation or boot sequences
    - System anomalies where key phases didn’t complete

    Args:
        log_lines (List[str]): Full list of cleaned log lines.

    Returns:
        List[str]: List of expected events that were not found in the logs.
    """
    missing = [
        event
        for event in EXPECTED_EVENTS
        if not any(event in line for line in log_lines)
    ]
    return missing
