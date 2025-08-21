"""
clustering_model.py - Clustering log events using KMeans for pattern discovery
"""

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from datetime import datetime
from utils import safe_component

def cluster_events(events):
    if not events:
        return None

    try:
        # Convert events to DataFrame for clustering
        df = pd.DataFrame([{
            "timestamp": (ev.timestamp - datetime(1970, 1, 1)).total_seconds() if hasattr(ev.timestamp, 'total_seconds') else 0,
            "severity": 0 if ev.severity == "INFO" else 1 if ev.severity == "WARNING" else 2 if ev.severity == "ERROR" else 3,
            "component": hash(safe_component(ev.component)) % 1000
        } for ev in events])
        
        if df.empty or len(df) < 3:
            return None

        # Normalize features
        scaler = StandardScaler()
        scaled = scaler.fit_transform(df)

        # Apply KMeans clustering with dynamic cluster count
        n_clusters = min(3, len(df))
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        df['cluster'] = kmeans.fit_predict(scaled)

        # Generate plot using matplotlib
        fig, ax = plt.subplots(figsize=(10, 5))
        colors = ['red', 'green', 'blue']
        for c in df['cluster'].unique():
            subset = df[df['cluster'] == c]
            ax.scatter(subset['timestamp'], subset['component'], label=f"Cluster {c}", c=colors[c % len(colors)], alpha=0.7)

        ax.set_xlabel("Time")
        ax.set_ylabel("Component Index")
        ax.set_title("Log Event Clustering")
        ax.legend()
        fig.tight_layout()

        return fig  # Return the matplotlib figure
    
    except Exception as e:
        return None
