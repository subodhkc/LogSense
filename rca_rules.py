# rca_rules.py - Pattern-based Root Cause Analysis logic engine for SKC Log Reader

from typing import List, Dict

def detect_os_incompatibility(events: List, metadata: Dict) -> str:
    os_build = (metadata.get("OS", "") + " " + metadata.get("Build", "")).lower()
    os_detected = "25h2" in os_build or any("25h2" in ev.message.lower() for ev in events)
    failure_related = any(
        "unsupported" in ev.message.lower()
        or "failed to install" in ev.message.lower()
        or "not compatible" in ev.message.lower()
        or "version mismatch" in ev.message.lower()
        or "install failed" in ev.message.lower()
        for ev in events
    )
    if os_detected and failure_related:
        return "Detected possible incompatibility between the build and Windows 25H2 target system."
    return ""

def detect_driver_conflict(events: List) -> str:
    conflict_keywords = [
        "driver conflict", "conflicting drivers", "driver failed",
        "unable to load driver", "driver installation failed",
        "missing driver"
    ]
    if any(any(kw in ev.message.lower() for kw in conflict_keywords) for ev in events):
        return "Detected possible driver conflict during installation."
    return ""

def detect_network_failure(events: List) -> str:
    if any(
        "network timeout" in ev.message.lower()
        or "connection failed" in ev.message.lower()
        or "unable to reach server" in ev.message.lower()
        or "dns error" in ev.message.lower()
        or "network unreachable" in ev.message.lower()
        for ev in events
    ):
        return "Network failure detected - logs indicate timeouts or server connectivity issues."
    return ""

def detect_corrupt_media(events: List) -> str:
    keywords = [
        "corrupt iso", "media unreadable", "checksum failed",
        "bad block", "unexpected eof", "invalid media",
        "file read error", "media error"
    ]
    if any(any(kw in ev.message.lower() for kw in keywords) for ev in events):
        return "Installation media appears to be corrupted or incomplete."
    return ""

def detect_permission_issue(events: List) -> str:
    if any(
        "access denied" in ev.message.lower()
        or "permission denied" in ev.message.lower()
        or "requires admin privileges" in ev.message.lower()
        or "not authorized" in ev.message.lower()
        or "elevation required" in ev.message.lower()
        for ev in events
    ):
        return "Permission issue detected - process may require administrative access."
    return ""

def detect_unsupported_hardware(events: List) -> str:
    if any(
        "unsupported hardware" in ev.message.lower()
        or "cpu not supported" in ev.message.lower()
        or "incompatible chipset" in ev.message.lower()
        or "hardware requirement not met" in ev.message.lower()
        or "unsupported platform" in ev.message.lower()
        for ev in events
    ):
        return "Detected unsupported or incompatible hardware."
    return ""

def detect_version_mismatch(events: List, context: Dict) -> str:
    """Detect version compatibility issues based on context"""
    app_version = context.get("app_version", "").lower()
    previous_version = context.get("previous_version", "").lower()
    build_changes = context.get("build_changes", "").lower()
    
    version_issues = any(
        "version mismatch" in ev.message.lower() or
        "incompatible version" in ev.message.lower() or
        "unsupported version" in ev.message.lower()
        for ev in events
    )
    
    if version_issues and (app_version or previous_version):
        return f"Version compatibility issue detected. Current: {context.get('app_version', 'Unknown')}, Previous: {context.get('previous_version', 'Unknown')}"
    
    if "dependency" in build_changes and any("dependency" in ev.message.lower() for ev in events):
        return "Dependency-related failure detected - likely related to recent build changes"
    
    return ""

def detect_deployment_method_issues(events: List, context: Dict) -> str:
    """Detect issues specific to deployment method"""
    deployment_method = context.get("deployment_method", "").lower()
    
    if "dash" in deployment_method and any("dash" in ev.message.lower() and "fail" in ev.message.lower() for ev in events):
        return "DASH imaging deployment failure detected"
    
    if "softpaq" in deployment_method and any("softpaq" in ev.message.lower() and "error" in ev.message.lower() for ev in events):
        return "SoftPaq installation failure detected"
    
    if "silent" in deployment_method and any("user interaction" in ev.message.lower() or "prompt" in ev.message.lower() for ev in events):
        return "Silent installation failed - user interaction required"
    
    return ""

def detect_environment_specific_issues(events: List, context: Dict) -> str:
    """Detect issues specific to test environment"""
    environment = context.get("test_environment", "").lower()
    
    if environment == "production" and any("test" in ev.message.lower() or "debug" in ev.message.lower() for ev in events):
        return "Test/debug artifacts detected in production environment"
    
    if environment in ["staging", "development"] and any("certificate" in ev.message.lower() and "invalid" in ev.message.lower() for ev in events):
        return f"Certificate validation issues in {environment} environment"
    
    return ""

def get_all_rca_summaries(events: List, metadata: Dict, context: Dict = None) -> List[str]:
    """Enhanced RCA with user context"""
    if context is None:
        context = {}
    
    summaries = [
        detect_os_incompatibility(events, metadata),
        detect_driver_conflict(events),
        detect_network_failure(events),
        detect_corrupt_media(events),
        detect_permission_issue(events),
        detect_unsupported_hardware(events),
        detect_version_mismatch(events, context),
        detect_deployment_method_issues(events, context),
        detect_environment_specific_issues(events, context)
    ]
    return [s for s in summaries if s]