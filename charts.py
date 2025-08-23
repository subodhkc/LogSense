# charts.py - Additional bar chart visualizations for SKC Log Reader

import matplotlib.pyplot as plt
from collections import Counter

def plot_severity_distribution(events):
    """
    Create a bar chart showing the distribution of severity levels.
    """
    severity_counts = Counter(ev.severity for ev in events)
    labels = list(severity_counts.keys())
    values = list(severity_counts.values())

    fig, ax = plt.subplots()
    ax.bar(labels, values)
    ax.set_title("Log Severity Distribution")
    ax.set_xlabel("Severity Level")
    ax.set_ylabel("Number of Events")
    return fig

def plot_top_error_components(events, top_n=5):
    """
    Create a bar chart showing top N components that caused ERROR or CRITICAL logs.
    """
    error_components = [ev.component for ev in events if ev.severity in ["ERROR", "CRITICAL"]]
    counts = Counter(error_components).most_common(top_n)

    if not counts:
        return None

    labels, values = zip(*counts)
    fig, ax = plt.subplots()
    ax.bar(labels, values)
    ax.set_title(f"Top {top_n} Error-Prone Components")
    ax.set_xlabel("Component")
    ax.set_ylabel("Error Count")
    return fig

def plot_event_frequency_by_hour(events):
    """
    Create a bar chart showing number of events per hour of day.
    """
    hours = [ev.timestamp.hour for ev in events if hasattr(ev.timestamp, "hour")]
    hour_counts = Counter(hours)
    labels = sorted(hour_counts.keys())
    values = [hour_counts[h] for h in labels]

    fig, ax = plt.subplots()
    ax.bar(labels, values)
    ax.set_title("Log Events by Hour of Day")
    ax.set_xlabel("Hour (0-23)")
    ax.set_ylabel("Number of Events")
    return fig