"""
test_plan.py - Validates parsed logs against structured test plans (JSON/YAML)
"""

import json
import yaml
import os
from typing import Any, Dict, List

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

def _infer_phase(text: str) -> str | None:
    """Lightweight heuristic to infer phase from step text."""
    if not text:
        return None
    t = text.lower()
    if any(w in t for w in ["download", "fetch"]):
        return "Download"
    if any(w in t for w in ["extract", "unpack", "decompress"]):
        return "Extraction"
    if any(w in t for w in ["verify", "signature", "hash"]):
        return "Verification"
    if any(w in t for w in ["install", "apply", "execute", "msi", "setup"]):
        return "Install/Apply"
    if any(w in t for w in ["reboot", "restart"]):
        return "Reboot"
    if any(w in t for w in ["launch", "start service", "service start"]):
        return "Post-Install/Start"
    return None

def validate_plan(plan: Dict[str, Any] | List[Dict[str, Any]], events: List[Any], plan_name: str | None = None) -> Dict[str, Any]:
    """
    Matches each test plan step to actual log events.

    Returns a rich, evidence-backed structure:
      {
        'plan_name': str | None,
        'summary': { pass_count, fail_count, first_failure_step, first_failure_phase },
        'steps': [ { 'Step', 'Step Action', 'Expected Result', 'Status', 'phase', 'evidence': [ {timestamp, component, message} ], 'first_hit_time', 'last_hit_time' } ]
      }
    """
    result: Dict[str, Any] = {"plan_name": plan_name, "summary": {}, "steps": []}

    if not plan:
        return result

    # Handle both direct list and {"steps": [...]} format
    steps = plan if isinstance(plan, list) else (plan.get("steps", []) or [])
    if not steps:
        return result

    pass_count = 0
    fail_count = 0
    first_failure_step = None
    first_failure_phase = None

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
        keywords = step.get("keywords", []) or []
        neg_keywords = step.get("negative_patterns", []) or []
        phase = step.get("phase") or _infer_phase(step_text)

        found = False
        ev_hits: List[Dict[str, Any]] = []

        # Build simple corpus pass for efficiency
        for ev in events:
            try:
                msg = str(getattr(ev, 'message', ''))
                line = " ".join([
                    str(getattr(ev, 'timestamp', '')),
                    str(getattr(ev, 'component', '')),
                    str(getattr(ev, 'severity', '')),
                    msg,
                ])
                low = line.lower()
            except Exception:
                continue

            # Negative pattern takes precedence for failure evidence (still records evidence)
            neg_hit = any((kw or "").lower() in low for kw in neg_keywords if kw)

            # Positive matches: main step text or any keyword
            pos_hit = False
            if step_text and step_text.lower() in low:
                pos_hit = True
            elif keywords and any((kw or "").lower() in low for kw in keywords if kw):
                pos_hit = True

            if pos_hit or neg_hit:
                ev_hits.append({
                    "timestamp": str(getattr(ev, 'timestamp', '')),
                    "component": str(getattr(ev, 'component', '')),
                    "message": msg,
                })

        # Decide status: if any negative hit present in hits, mark Fail; else Pass if any positive; else Fail
        if ev_hits:
            # Determine if any hit came from a negative pattern
            any_negative = False
            for h in ev_hits:
                low_msg = (h.get("message") or "").lower()
                if any((kw or "").lower() in low_msg for kw in neg_keywords if kw):
                    any_negative = True
                    break
            status = "Fail" if any_negative else "Pass"
        else:
            status = "Fail"

        if status == "Pass":
            pass_count += 1
        else:
            fail_count += 1
            if first_failure_step is None:
                first_failure_step = idx + 1
                first_failure_phase = phase

        # Timestamps for first/last evidence
        first_hit_time = ev_hits[0]["timestamp"] if ev_hits else None
        last_hit_time = ev_hits[-1]["timestamp"] if ev_hits else None

        result["steps"].append({
            "Step": idx + 1,
            "Step Action": step_text.strip(),
            "Expected Result": expected.strip(),
            "Status": status,
            "phase": phase,
            "evidence": ev_hits[:3],  # limit evidence in payload
            "first_hit_time": first_hit_time,
            "last_hit_time": last_hit_time,
        })

    result["summary"] = {
        "pass_count": pass_count,
        "fail_count": fail_count,
        "first_failure_step": first_failure_step,
        "first_failure_phase": first_failure_phase,
    }

    return result
