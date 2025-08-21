# Capture unmatched logs for analysis
# feedback/unmatched_collector.py

import re
import yaml

def load_signature_rules(yaml_path="config/rules.yml"):
    """
    Loads pattern-matching rules from a YAML file.

    Args:
        yaml_path (str): Path to the rules YAML file.

    Returns:
        dict: Dictionary of pattern labels and regex strings.
    """
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)

def collect_unmatched_lines(log_lines, rules):
    """
    Identifies log lines that do not match any known signature rule.

    This is useful for:
    - Discovering new error patterns
    - Feeding unknowns into future rule updates or ML clustering

    Args:
        log_lines (List[str]): List of cleaned, redacted log lines.
        rules (dict): Dictionary of known regex patterns.

    Returns:
        List[str]: Lines that didn’t match any known rule.
    """
    unmatched = []

    for line in log_lines:
        # Check if line matches any pattern; if not, collect it
        if not any(re.search(pattern, line) for pattern in rules.values()):
            unmatched.append(line.strip())

    return unmatched

def save_unmatched_lines(unmatched_lines, out_path="unmatched_logs.txt"):
    """
    Saves unmatched log lines to a file for review or clustering.

    Args:
        unmatched_lines (List[str]): Lines that didn't match known patterns.
        out_path (str): Output path for saving unmatched entries.
    """
    with open(out_path, "w", encoding="utf-8") as f:
        for line in unmatched_lines:
            f.write(line + "\n")
