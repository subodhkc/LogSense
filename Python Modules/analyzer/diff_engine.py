# Compare logs against baselines
# analyzer/diff_engine.py

import difflib
import re

def mask_dynamic_fields(lines):
    """
    Masks dynamic values in log lines that should not affect diff comparison.

    Fields commonly masked:
    - Timestamps (e.g., 2025-07-27 14:22:01 → [TIMESTAMP])
    - GUIDs (e.g., 123e4567-e89b-12d3-a456-426614174000 → [GUID])
    - Absolute Windows paths (e.g., C:\\Program Files\\App → [PATH])

    Args:
        lines (List[str]): List of log lines to normalize.

    Returns:
        List[str]: Lines with dynamic fields replaced by static tokens.
    """
    masked = []

    for line in lines:
        # Mask ISO-like timestamp patterns
        line = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "[TIMESTAMP]", line)

        # Mask standard UUID/GUIDs
        line = re.sub(r"[a-fA-F0-9\-]{36}", "[GUID]", line)

        # Mask Windows file paths
        line = re.sub(r"[A-Z]:\\\\[^\s]+", "[PATH]", line)

        masked.append(line)

    return masked

def compare_logs(baseline_lines, target_lines):
    """
    Compares two sets of log lines after masking dynamic data.

    Uses unified diff to highlight changes while ignoring non-deterministic fields.

    Args:
        baseline_lines (List[str]): Reference log content.
        target_lines (List[str]): New log content to compare.

    Returns:
        List[str]: List of diff lines (added/removed/changed).
    """
    # Normalize dynamic content
    baseline = mask_dynamic_fields(baseline_lines)
    target = mask_dynamic_fields(target_lines)

    # Generate a unified diff (line-by-line)
    diff = list(difflib.unified_diff(baseline, target, lineterm=''))

    return diff
