# Merge multi-line log entries
#Detects a timestamp at the beginning of the line (e.g., 2025-07-27 12:30)

#Any line not starting with a timestamp is treated as part of the previous log entry

#Ensures multi-line events like exceptions, tracebacks, or nested logs are grouped properly

# preprocessor/multiline.py

import re

# Pattern to identify the beginning of a new log event using a timestamp.
# This helps separate distinct log entries from continuation lines like stack traces.
TIMESTAMP_PATTERN = re.compile(r"^\[?\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}")

def merge_multiline_events(lines):
    """
    Merges multi-line log entries into single strings.

    Many logs (e.g., with stack traces) span multiple lines,
    but only the first line starts with a timestamp.
    This function stitches related lines together.

    Args:
        lines (List[str]): Redacted and cleansed log lines.

    Returns:
        List[str]: Log entries where multi-line messages have been merged.
    """
    merged = []  # Final output list
    buffer = ""  # Temporary accumulator for a single merged log entry

    for line in lines:
        if TIMESTAMP_PATTERN.match(line):
            # If a new log line starts and buffer has data, finalize it
            if buffer:
                merged.append(buffer.strip())
            buffer = line  # Start a new log entry
        else:
            # Append continuation lines (like stack traces)
            buffer += "\n" + line

    # Append the last buffered entry if it exists
    if buffer:
        merged.append(buffer.strip())

    return merged
