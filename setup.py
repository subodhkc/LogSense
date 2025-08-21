"""
setup.py - Configuration loader for API keys, redaction patterns, and test plans
"""

import os
import json
import yaml
import streamlit as st

# === Configurable Paths ===
CONFIG_PATH = "config"
PLANS_PATH = "plans"
DEFAULT_PLAN = "dash_test_plan.json"
SOFTPAQ_PLAN = "softpaq_test_plan.json"
PRIVATE_API_KEY = os.getenv("OPENAI_API_KEY", "")

# === File Loaders ===

def load_json_file(path):
    """Helper to load a JSON file with robust error handling."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
        print(f"Warning: Failed to load JSON file {path}: {e}")
        return None

def load_yaml_file(path):
    """Helper to load a YAML file with robust error handling."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, IOError, UnicodeDecodeError) as e:
        print(f"Warning: Failed to load YAML file {path}: {e}")
        return None

# === Redaction Rules ===

def get_redaction_patterns():
    """Load redaction rules from config/redact.json or fallback to default patterns."""
    path = os.path.join(CONFIG_PATH, "redact.json")
    if os.path.exists(path):
        return load_json_file(path)
    return [
        {"pattern": r"\bHP[a-zA-Z0-9\-]*", "replacement": "[REDACTED_HP]"},
        {"pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}", "replacement": "[REDACTED_EMAIL]"},
        {"pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "replacement": "[REDACTED_IP]"},
        {"pattern": r"\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b", "replacement": "[REDACTED_MAC]"},
        {"pattern": r"\bSerial[\s:-]*\w+\b", "replacement": "[REDACTED_SERIAL]"},
    ]

# === API Key Access ===

def get_openai_key():
    """Return hardcoded OpenAI API key for private backend (optional use)."""
    return PRIVATE_API_KEY

# === Test Plan Handling ===

def get_test_plan(plan_name):
    """Return parsed test plan from the selected file name or label."""
    filename = DEFAULT_PLAN if plan_name == "Dash" else (
        SOFTPAQ_PLAN if plan_name == "SoftPaq" else plan_name)
    
    full_path = os.path.join(PLANS_PATH, filename)
    if filename.endswith(".json"):
        return load_json_file(full_path)
    elif filename.endswith((".yaml", ".yml")):
        return load_yaml_file(full_path)
    return None

def get_test_plan_by_name(name):
    """Alias for get_test_plan to maintain compatibility with older app references."""
    return get_test_plan(name)

def get_available_test_plans():
    """Return list of available test plans from the /plans directory."""
    if not os.path.exists(PLANS_PATH):
        return []
    return [f for f in os.listdir(PLANS_PATH) if f.endswith((".json", ".yaml", ".yml"))]

def load_custom_test_plan(file_obj):
    """Load user-uploaded test plan with robust error handling."""
    if not file_obj or not hasattr(file_obj, 'name'):
        return None
    try:
        if file_obj.name.endswith(".json"):
            return json.load(file_obj)
        elif file_obj.name.endswith((".yaml", ".yml")):
            return yaml.safe_load(file_obj)
        else:
            print(f"Warning: Unsupported file type: {file_obj.name}")
            return None
    except (json.JSONDecodeError, yaml.YAMLError, IOError) as e:
        print(f"Warning: Failed to parse uploaded file {file_obj.name}: {e}")
        return None
