# Redact sensitive information from logs
import re

# Predefined regex patterns to detect and redact sensitive data
REDACTION_PATTERNS = {
    # Original categories
    "IP": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "USERNAME": r"(?i)(user=)[^\s]+",

    # Additional redactions from your list
    "PII": r"\b(?:\d{3}-\d{2}-\d{4}|\(\d{3}\)\s*\d{3}-\d{4}|\d{10})\b",  # SSN/phone
    "SERIAL": r"\b[A-Z0-9]{4,}-[A-Z0-9]{4,}(?:-[A-Z0-9]{4,})?\b",  # License-style keys
    "FOLDER": r"(\/[\w\-.]+)+",  # Linux/Unix paths
    "VERSION": r"\bv?(ersion)?\s*[:=]?\s*\d+\.\d+(\.\d+)?(-[a-zA-Z0-9]+)?\b",  # v1.2.3 or version: 1.2.0-beta
    "TOOL": r"\b(?:internal_[a-zA-Z0-9_]+|tool_[a-zA-Z0-9_]+)\b",  # internal_toolX or tool_xyz
}

def redact_line(line):
    """
    Redacts sensitive patterns in a single line.
    
    Args:
        line (str): A log line.

    Returns:
        str: Redacted log line.
    """
    for label, pattern in REDACTION_PATTERNS.items():
        line = re.sub(pattern, f"[REDACTED_{label}]", line)
    return line

def redact_log(lines):
    """
    Applies redaction to a list of log lines.

    Args:
        lines (List[str]): Cleaned log lines.

    Returns:
        List[str]: Redacted log lines.
    """
    return [redact_line(line) for line in lines]
