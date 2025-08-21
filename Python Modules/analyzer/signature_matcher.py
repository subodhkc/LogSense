# Signature-based pattern matching
# analyzer/signature_matcher.py

import re
import yaml

def load_signature_rules(yaml_path="config/rules.yml"):
    """
    Loads signature matching rules from a YAML file.

    Each rule should define a label and a regex pattern:
    ---
    auth_failure: "authentication failed for user .*"
    disk_error: "Disk read error at sector \\d+"

    Args:
        yaml_path (str): Path to the rules YAML file.

    Returns:
        dict: Dictionary of label-pattern pairs.
    """
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def match_signatures(log_lines, rules):
    """
    Matches log lines against known signature patterns.

    For each line, it applies all regex rules and stores matches
    with metadata including line number, pattern label, and content.

    Args:
        log_lines (List[str]): Cleaned and optionally redacted log lines.
        rules (dict): Signature rules with pattern labels as keys.

    Returns:
        List[dict]: List of matches with pattern label and line metadata.
    """
    matched = []

    for idx, line in enumerate(log_lines):
        for label, pattern in rules.items():
            if re.search(pattern, line):
                matched.append({
                    "line": idx + 1,           # 1-based line number
                    "pattern": label,          # Matched pattern name from rules.yml
                    "content": line.strip()    # Trimmed log line
                })

    return matched
