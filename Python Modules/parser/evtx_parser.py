# EVTX parser logic placeholder
# parser/evtx_parser.py

import xml.etree.ElementTree as ET
from Evtx.Evtx import Evtx

def parse_evtx(file_path):
    """
    Parses a Windows EVTX log file and extracts relevant event data.

    Each log entry is converted to a dictionary with:
    - event_id: The numeric Event ID (e.g., 4624 for login)
    - timestamp: The time the event occurred (raw from TimeCreated tag)
    - message: Full XML string of the log record for downstream use

    Args:
        file_path (str): Path to the .evtx log file

    Returns:
        List[Dict[str, str]]: Parsed list of event records
    """
    events = []

    # Open the EVTX log file using the Evtx module
    with Evtx(file_path) as log:
        for record in log.records():
            try:
                # Parse the XML representation of each event
                xml_str = record.xml()
                root = ET.fromstring(xml_str)

                # Extract key fields from the XML structure
                event_id = root.findtext(".//EventID")
                timestamp = root.findtext(".//TimeCreated")
                message = ET.tostring(root, encoding='unicode')  # Full XML as string

                # Append parsed event data to the results list
                events.append({
                    "event_id": event_id,
                    "timestamp": timestamp,
                    "message": message
                })

            except Exception:
                # If a record is malformed or raises an error, skip it
                continue

    return events
