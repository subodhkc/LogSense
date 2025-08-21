# Extract fields from parsed logs
# parser/extractor.py

def extract_fields(log_entry):
    """
    Extracts and normalizes common fields from a parsed log entry.

    Ensures consistent keys across log types (EVTX, MSI, text):
    - timestamp: when the event occurred
    - event_id: ID number (may be missing for some logs)
    - message: full log content or XML snippet

    This function uses `.get()` with defaults to safely handle missing keys.

    Args:
        log_entry (dict): Parsed log entry from a specific parser.

    Returns:
        dict: Normalized event with consistent field names.
    """
    return {
        "timestamp": log_entry.get("timestamp", ""),
        "event_id": log_entry.get("event_id", ""),
        "message": log_entry.get("message", "")
    }
