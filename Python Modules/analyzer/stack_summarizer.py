# analyzer/stack_summarizer.py

import re

def summarize_stack_trace(entry):
    """
    Extracts a high-level summary and top stack frame from a multi-line error entry.

    This function is designed to help with RCA (root cause analysis) by:
    - Identifying the first 'Exception' or 'Error' line as the summary
    - Extracting the topmost stack frame (first line starting with 'at ')

    Args:
        entry (str): A multi-line log string (e.g., a merged stack trace)

    Returns:
        dict: Summary including:
            - 'summary': The first matching exception/error line
            - 'top_frame': The first stack frame line, if present
    """
    lines = entry.split("\n")
    summary = None

    # Look for the first line that mentions an Exception or Error
    for line in lines:
        if "Exception" in line or "Error" in line:
            summary = line.strip()
            break

    # Extract lines that look like stack frames (e.g., "at com.foo.Bar.method...")
    top_frames = [line.strip() for line in lines if line.strip().startswith("at ")]

    return {
        "summary": summary or "Unknown Exception",              # Fallback if no match
        "top_frame": top_frames[0] if top_frames else "No frame detected"
    }
