"""
test_plan.py - Validates parsed logs against structured test plans (JSON/YAML)
"""

import json
import yaml
import os

def load_test_plan(path):
    """
    Loads a test plan from a .json or .yaml file.
    """
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            if path.endswith(".yaml") or path.endswith(".yml"):
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        print(f"[Test Plan] Failed to load: {e}")
        return None

def validate_plan(plan, events):
    """
    Matches each test plan step to actual log events.
    Returns a list of dicts with Step, Action, Expected Result, Status
    """
    results = []

    if not plan:
        return results
    
    # Handle both direct list and {"steps": [...]} format
    steps = plan if isinstance(plan, list) else plan.get("steps", [])
    
    if not steps:
        return results

    for idx, step in enumerate(steps):
        # Support multiple field name formats
        step_text = (
            step.get("Step Action") or 
            step.get("name") or 
            step.get("[HPPM] Image System - DASH") or 
            ""
        )
        expected = (
            step.get("Expected Result") or 
            step.get("expected") or 
            ""
        )
        
        # Enhanced matching using keywords if available
        keywords = step.get("keywords", [])
        found = False

        for ev in events:
            msg_lower = ev.message.lower()
            # Check main step text
            if step_text and step_text.lower() in msg_lower:
                found = True
                break
            # Check keywords for better matching
            if keywords and any(kw.lower() in msg_lower for kw in keywords if kw):
                found = True
                break

        results.append({
            "Step": idx + 1,
            "Step Action": step_text.strip(),
            "Expected Result": expected.strip(),
            "Status": "Pass" if found else "Fail"
        })

    return results
