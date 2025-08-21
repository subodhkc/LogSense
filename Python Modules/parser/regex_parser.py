# Regex parser for generic logs
# parser/regex_parser.py

import re
import yaml

def load_patterns(yaml_file="config/rules.yml"):
    """
    Loads regex patterns from a YAML file.

    The YAML should have the structure:
    pattern_name: regex_pattern

    Example:
    --------
    login_failure: "Failed login for user .*"
    timeout_error: "Request timed out after \d+ ms"

    Args:
        yaml_file (str): Path to the rules YAML file.

    Returns:
        dict: Dictionary of named regex patterns.
    """
    with open(yaml_file, "r") as f:
        return yaml.safe_load(f)


def parse_text_log(lines, patterns):
    """
    Parses plain text logs using user-defined regex rules.

    For each line in the log:
    - It is checked against each loaded pattern
    - All matches are captured along with their pattern names

    Args:
        lines (List[str]): List of log lines (cleaned + redacted).
        patterns (dict): Dictionary of named regex rules.

    Returns:
        List[dict]: List of matched results containing pattern name and matched line.
    """
    results = []

    for line in lines:
        for name, rule in patterns.items():
            # Use re.search to find matches anywhere in the line
            if re.search(rule, line):
                results.append({
                    "pattern": name,
                    "matched": line
                })

    return results
