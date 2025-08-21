# parser/msi_parser.py

import re

# Regular expressions to extract structured error information
TIMESTAMP_PATTERN = re.compile(r"\d{1,2}:\d{2}:\d{2}\s*(AM|PM)?")
ERROR_CODE_PATTERN = re.compile(r"Error\s*(\d+)")
ACTION_PATTERN = re.compile(r"Action\s+start\s+\d+:\d+:\d+\s+([^\r\n]+)")
RETURN_3_PATTERN = re.compile(r"Return value 3")

def parse_msi_log(path):
    """
    Parses an MSI installer log file for structured error-related information.

    Extracts lines that contain:
    - "Return value 3" (critical failure indicator)
    - Any line with "Error"

    Also attempts to extract:
    - Timestamp (if present)
    - Error code (e.g., Error 1603)
    - Action or component name (if found in context)

    Args:
        path (str): Path to the .msi log file

    Returns:
        List[dict]: Parsed and structured error events
    """
    results = []

    with open(path, 'r', errors='ignore') as f:
        for line in f:
            if "Return value 3" in line or "Error" in line:
                entry = {
                    "raw": line.strip(),
                    "timestamp": None,
                    "error_code": None,
                    "action": None,
                    "return_value_3": False
                }

                # Extract timestamp if available
                ts_match = TIMESTAMP_PATTERN.search(line)
                if ts_match:
                    entry["timestamp"] = ts_match.group()

                # Extract error code (e.g., Error 1603)
                error_match = ERROR_CODE_PATTERN.search(line)
                if error_match:
                    entry["error_code"] = error_match.group(1)

                # Try to extract an action/component name
                action_match = ACTION_PATTERN.search(line)
                if action_match:
                    entry["action"] = action_match.group(1).strip()

                # Flag if line contains "Return value 3"
                if RETURN_3_PATTERN.search(line):
                    entry["return_value_3"] = True

                results.append(entry)

    return results
