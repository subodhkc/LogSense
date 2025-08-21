"""
recommendations.py - Rule-based RCA generation from log timeline
"""

def generate_recommendations(events, context=None):
    recs = []
    context = context or {}

    # Context-aware recommendations based on user input
    if context.get("deployment_method") == "Silent Install" and context.get("issue_description"):
        if "prompt" in context["issue_description"].lower() or "user interaction" in context["issue_description"].lower():
            recs.append({
                "severity": "High",
                "message": "Silent installation requiring user interaction detected",
                "category": "Deployment",
                "timestamp": "Context-based",
                "action": "Review silent install parameters and remove interactive components"
            })
    
    if context.get("build_changes") and "dependency" in context.get("build_changes", "").lower():
        dependency_errors = any("dependency" in ev.message.lower() or "missing" in ev.message.lower() for ev in events)
        if dependency_errors:
            recs.append({
                "severity": "High",
                "message": "Dependency issues correlate with recent build changes",
                "category": "Build",
                "timestamp": "Context-based",
                "action": f"Review dependency changes: {context.get('build_changes', '')[:100]}..."
            })

    for e in events:
        msg = e.message.lower()

        # SoftPaq / Installers
        if "os version not supported" in msg or "unsupported os" in msg:
            recs.append({
                "severity": "High",
                "message": "Detected OS version incompatibility.",
                "category": "SoftPaq",
                "timestamp": e.timestamp,
                "action": "Use a CVA-supported SoftPaq compatible with the current OS."
            })

        elif "install failed" in msg or "setup exited with error" in msg:
            recs.append({
                "severity": "High",
                "message": "Install failure detected.",
                "category": "SoftPaq",
                "timestamp": e.timestamp,
                "action": "Match SoftPaq version with supported OS/CVA and reattempt install."
            })

        elif "signature verification failed" in msg:
            recs.append({
                "severity": "High",
                "message": "Installer failed due to signature check.",
                "category": "SoftPaq",
                "timestamp": e.timestamp,
                "action": "Re-download SoftPaq or disable Secure Boot temporarily."
            })

        elif "dependency missing" in msg or "prerequisite not found" in msg:
            recs.append({
                "severity": "Medium",
                "message": "Missing dependency or required component.",
                "category": "SoftPaq",
                "timestamp": e.timestamp,
                "action": "Verify prerequisite packages are installed first."
            })

        # BIOS / Firmware
        elif "bios mismatch" in msg or "bios not supported" in msg:
            recs.append({
                "severity": "High",
                "message": "BIOS version mismatch detected.",
                "category": "BIOS",
                "timestamp": e.timestamp,
                "action": "Update BIOS to latest approved version before testing."
            })

        # Fusion Agent
        elif "fusion agent" in msg and "old" in msg:
            recs.append({
                "severity": "Medium",
                "message": "Outdated Fusion agent detected.",
                "category": "Fusion",
                "timestamp": e.timestamp,
                "action": "Install latest Fusion agent version before running test."
            })

        # Dash Imaging / Component Drop
        elif "component missing" in msg:
            recs.append({
                "severity": "Medium",
                "message": "Component was not bundled correctly.",
                "category": "Image",
                "timestamp": e.timestamp,
                "action": "Check ML list and verify bundling in image server."
            })

        elif "red screen" in msg or "failure.flg" in msg:
            recs.append({
                "severity": "High",
                "message": "Platform boot error detected.",
                "category": "Platform",
                "timestamp": e.timestamp,
                "action": "Collect system.sav and escalate to Imaging or BIOS team."
            })

        elif "oobe hang" in msg or "unbundle failed" in msg:
            recs.append({
                "severity": "Medium",
                "message": "Unbundling/OOBE flow interrupted.",
                "category": "Image",
                "timestamp": e.timestamp,
                "action": "Check scripts or registry config related to OOBE post-dash."
            })

        # Scripting / Automation
        elif "script error" in msg or "syntax error" in msg:
            recs.append({
                "severity": "High",
                "message": "Setup script failed due to syntax.",
                "category": "Automation",
                "timestamp": e.timestamp,
                "action": "Validate custom install/unbundle scripts or tasks scheduler setup."
            })

        # Connectivity / Network issues
        elif "cannot connect to server" in msg or "download failed" in msg:
            recs.append({
                "severity": "Medium",
                "message": "Log shows network provisioning issue.",
                "category": "Connectivity",
                "timestamp": e.timestamp,
                "action": "Check if image server is reachable and correctly mapped."
            })

        elif "timeout occurred" in msg:
            recs.append({
                "severity": "Medium",
                "message": "Timed out waiting for response.",
                "category": "Connectivity",
                "timestamp": e.timestamp,
                "action": "Check network stability or image download size."
            })

        # System / Infra
        elif "blue screen" in msg or "bugcheck" in msg:
            recs.append({
                "severity": "Critical",
                "message": "BSOD detected during provisioning.",
                "category": "System",
                "timestamp": e.timestamp,
                "action": "Collect memory dump. Analyze for faulty drivers or firmware issues."
            })

        elif "disk full" in msg or "insufficient space" in msg:
            recs.append({
                "severity": "High",
                "message": "System ran out of space during install.",
                "category": "System",
                "timestamp": e.timestamp,
                "action": "Clear disk, shrink image, or resize partitions before retry."
            })

    return {
        "rules_fired": len(recs),
        "categories_hit": list(set(r["category"] for r in recs)),
        "recommendations": recs
    }
