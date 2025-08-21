# Timestamp normalizer and converter
# utils/timestamp_utils.py

import re
from datetime import datetime

def normalize_timestamp(line):
    """
    Finds a timestamp in a log line and converts it to ISO 8601 format.

    Supported formats (examples):
    - "2025/07/28 13:45:02"
    - "2025-07-28 13:45:02"
    
    After normalization:
    - "2025-07-28T13:45:02" (ISO 8601 format)

    Args:
        line (str): A log line possibly containing a timestamp.

    Returns:
        str: Log line with the timestamp normalized if found and parsable.
    """
    
    # Pattern to match common timestamp formats like YYYY-MM-DD HH:MM:SS or YYYY/MM/DD HH:MM:SS
    ts_pattern = r"\d{4}[-/]\d{2}[-/]\d{2}[ T]\d{2}:\d{2}:\d{2}"
    match = re.search(ts_pattern, line)

    # If no timestamp is found, return the original line
    if not match:
        return line

    raw_ts = match.group()

    # Try parsing with supported formats
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]:
        try:
            dt = datetime.strptime(raw_ts, fmt)
            iso_ts = dt.isoformat()  # Format as ISO 8601
            return line.replace(raw_ts, iso_ts)
        except ValueError:
            continue  # Try the next format if parsing fails

    # If all formats fail, return the original line
    return line
