# Placeholder for future ML rule suggestor
# feedback/template_suggester.py

import re
from collections import defaultdict

def mask_variables(line):
    """
    Generalizes a log line by masking dynamic elements like:
    - Numbers (e.g., timestamps, error codes)
    - Long hex strings (e.g., hashes, GUIDs)
    - Windows paths

    Args:
        line (str): Raw log line.

    Returns:
        str: Masked/generalized version of the line.
    """
    line = re.sub(r"\b\d+\b", "<NUM>", line)                        # Replace integers
    line = re.sub(r"[a-fA-F0-9]{8,}", "<HEX>", line)                # Replace long hex/GUIDs
    line = re.sub(r"[A-Z]:\\\\[^\s]+", "<PATH>", line)              # Replace Windows paths
    return line

def suggest_templates(unmatched_lines, min_count=3):
    """
    Suggests log message templates by grouping generalized log lines.

    Args:
        unmatched_lines (List[str]): Raw unmatched log lines.
        min_count (int): Minimum number of occurrences for a template to be suggested.

    Returns:
        List[dict]: Suggested templates with sample example and frequency.
    """
    templates = defaultdict(list)

    for line in unmatched_lines:
        masked = mask_variables(line)
        templates[masked].append(line.strip())

    # Filter out infrequent templates and prepare result list
    suggestions = []
    for template, examples in templates.items():
        if len(examples) >= min_count:
            suggestions.append({
                "template": template,
                "occurrences": len(examples),
                "example": examples[0]
            })

    return suggestions
