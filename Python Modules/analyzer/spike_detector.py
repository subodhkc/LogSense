# Frequency-based anomaly detection
# analyzer/spike_detector.py

from collections import defaultdict
from datetime import datetime
import re

def parse_time(line):
    """
    Extracts a timestamp from a log line and converts it to a datetime object.

    Expected format:
    - YYYY-MM-DD HH:MM:SS
    - YYYY-MM-DDTHH:MM:SS

    Args:
        line (str): A single log line.

    Returns:
        datetime or None: Parsed datetime object or None if parsing fails.
    """
    try:
        # Match ISO-style timestamp (e.g., 2025-07-27 13:45:01)
        ts_match = re.search(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}", line)
        if ts_match:
            # Convert to ISO format (replace space with 'T') and parse
            return datetime.fromisoformat(ts_match.group().replace(" ", "T"))
        return None
    except Exception:
        return None

def detect_spike(log_lines, threshold_per_min=10):
    """
    Detects time-based spikes in log event frequency.

    Aggregates events by minute and flags any time window with
    more than `threshold_per_min` entries.

    Args:
        log_lines (List[str]): List of log lines (with timestamps).
        threshold_per_min (int): Threshold count of events per minute to flag a spike.

    Returns:
        dict: Time buckets (YYYY-MM-DD HH:MM) that exceed the threshold.
    """
    time_buckets = defaultdict(int)

    for line in log_lines:
        ts = parse_time(line)
        if ts:
            # Bucket by minute: "2025-07-27 13:45"
            bucket = ts.strftime("%Y-%m-%d %H:%M")
            time_buckets[bucket] += 1

    # Filter buckets that exceed the spike threshold
    spikes = {k: v for k, v in time_buckets.items() if v > threshold_per_min}
    return spikes
