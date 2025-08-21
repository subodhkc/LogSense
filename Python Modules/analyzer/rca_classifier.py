# Rule-based RCA classification
# analyzer/rca_classifier.py

def classify_root_cause(event):
    """
    Classifies the root cause category of a log event based on message content.

    Categories include:
    - Network Issue
    - Security/Permission
    - Storage I/O
    - Code Defect
    - Resource Exhaustion
    - Unclassified (default fallback)

    Args:
        event (dict): A parsed log event with at least a 'message' field.

    Returns:
        str: Root cause classification label.
    """
    message = event.get("message", "").lower()

    # Identify common network-related errors
    if "timeout" in message or "unreachable" in message:
        return "Network Issue"

    # Identify permission/security issues
    elif "permission denied" in message or "access is denied" in message:
        return "Security/Permission"

    # Identify storage-related errors
    elif "disk" in message or "io error" in message:
        return "Storage I/O"

    # Identify null/undefined or exception triggers
    elif "nullreference" in message or "undefined" in message:
        return "Code Defect"

    # Identify memory/resource exhaustion
    elif "outofmemory" in message:
        return "Resource Exhaustion"

    # Fallback when no known pattern matches
    else:
        return "Unclassified"
