# analyzer/anomaly_summary.py

def summarize_anomalies(sequence_result, spike_result, diff_lines):
    """
    Produces a high-level summary of anomalies detected in the logs.

    Consolidates results from:
    - Sequence checker
    - Spike detector
    - Diff engine

    Args:
        sequence_result (dict): Output from check_sequence()
        spike_result (dict): Output from detect_spike()
        diff_lines (List[str]): Output from compare_logs()

    Returns:
        dict: Summary of anomaly status including:
            - sequence_status: "PASS" or "FAIL"
            - missing_steps: List of missing initialization steps
            - spike_times: Timestamps (minute resolution) with frequency spikes
            - diff_summary:
                - line_count: Total number of differing lines
                - has_diff: Boolean flag for whether any diff exists
    """
    return {
        "sequence_status": sequence_result.get("status"),
        "missing_steps": sequence_result.get("missing"),
        "spike_times": list(spike_result.keys()),
        "diff_summary": {
            "line_count": len(diff_lines),
            "has_diff": bool(diff_lines)
        }
    }
