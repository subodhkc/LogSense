# Plot timelines and event frequency graphs
# visuals/plot_utils.py

import matplotlib.pyplot as plt

def plot_spikes(spike_dict):
    """
    Plots a simple bar chart of event frequency spikes by time window.

    Args:
        spike_dict (dict): Dictionary where keys are time buckets (e.g., "2025-07-27 13:45")
                           and values are event counts that exceeded the threshold.

    Returns:
        None: Displays a matplotlib bar chart inline.
    """
    if not spike_dict:
        print("No spikes to plot.")
        return

    # Extract time buckets and their corresponding frequencies
    times = list(spike_dict.keys())
    values = list(spike_dict.values())

    # Plot the spike chart
    plt.figure(figsize=(10, 4))
    plt.bar(times, values, color='red')
    plt.xticks(rotation=45, ha='right')
    plt.title("Event Frequency Spikes")
    plt.ylabel("Events per Minute")
    plt.xlabel("Time Bucket")
    plt.tight_layout()
    plt.show()
