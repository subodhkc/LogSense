# Check for expected log event sequences
# analyzer/sequence_checker.py

# Define the expected order of critical steps in a process log
EXPECTED_SEQUENCE = [
    "Initialize",
    "Load Config",
    "Validate Settings",
    "Start Services",
    "Complete"
]

def check_sequence(log_lines):
    """
    Checks whether expected log steps occur in the defined sequence.

    It evaluates if each required checkpoint appears in the logs.
    This helps identify:
    - Incomplete flows (missing steps)
    - Abnormal startup sequences

    Args:
        log_lines (List[str]): Cleaned and parsed log lines

    Returns:
        dict: Summary of observed steps, missing steps, and pass/fail status
    """
    # Collect which expected steps are observed in the actual log lines
    observed = [step for step in EXPECTED_SEQUENCE if any(step in line for line in log_lines)]

    # Determine which expected steps were not found
    missing = [step for step in EXPECTED_SEQUENCE if step not in observed]

    return {
        "observed": observed,
        "missing": missing,
        "status": "PASS" if not missing else "FAIL"
    }
