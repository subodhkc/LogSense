# Convert results to PDF or HTML reports
# report/report_generator.py

import json
from datetime import datetime

def generate_text_report(rca_results, anomaly_summary, unmatched_count):
    """
    Generates a human-readable text report for CLI or export.

    Args:
        rca_results (List[dict]): List of RCA matches with line, pattern, and optional exception summary.
        anomaly_summary (dict): Output from summarize_anomalies().
        unmatched_count (int): Number of unmatched lines (Phase 5 feedback).

    Returns:
        str: Full plaintext report.
    """
    report = []

    # Header
    report.append(f"SKC Log Analyzer Report - {datetime.now().isoformat()}")
    report.append("=" * 60)

    # RCA Findings
    report.append("\nRCA Findings:")
    for issue in rca_results:
        report.append(f"- Line {issue['line']} | Pattern: {issue['pattern']} | Cause: {issue['rca']}")
        if issue.get("exception_summary"):
            report.append(f"  → {issue['exception_summary']}")

    # Anomaly Summary
    report.append("\nAnomaly Summary:")
    report.append(f"- Sequence Check: {anomaly_summary.get('sequence_status')}")
    report.append(f"- Missing Steps: {anomaly_summary.get('missing_steps')}")
    report.append(f"- Spikes: {', '.join(anomaly_summary.get('spike_times', []))}")
    report.append(f"- Diff Count: {anomaly_summary['diff_summary']['line_count']}")

    # Feedback
    report.append(f"\nUnmatched Logs: {unmatched_count}")

    return "\n".join(report)


def generate_json_report(rca_results, anomaly_summary, unmatched_count):
    """
    Generates a JSON-formatted version of the RCA and anomaly results.

    Args:
        rca_results (List[dict]): RCA match results.
        anomaly_summary (dict): Anomaly detection summary.
        unmatched_count (int): Number of unmatched lines.

    Returns:
        str: JSON-formatted string of the complete analysis results.
    """
    return json.dumps({
        "timestamp": datetime.now().isoformat(),
        "rca_findings": rca_results,
        "anomaly_summary": anomaly_summary,
        "unmatched_count": unmatched_count
    }, indent=2)
