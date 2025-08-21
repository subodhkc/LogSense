# analysis/ml_anomaly.py
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import logging
from datetime import datetime, timedelta
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
from datamodels.events import Event

@dataclass(frozen=True)
class AnomalyResult:
    event_index: int
    anomaly_score: float
    anomaly_type: str
    confidence: float
    features: Dict[str, float]

class MLAnomalyDetector:
    """
    Advanced ML-based anomaly detection combining multiple approaches:
    - Isolation Forest for numerical features
    - TF-IDF + clustering for message content
    - Time-series pattern detection
    - Behavioral baseline comparison
    """
    
    def __init__(self, contamination: float = 0.1, min_samples: int = 5):
        self.logger = logging.getLogger("MLAnomaly")
        self.contamination = contamination
        self.min_samples = min_samples
        self.isolation_forest = IsolationForest(contamination=contamination, random_state=42)
        self.scaler = StandardScaler()
        self.tfidf = TfidfVectorizer(max_features=1000, stop_words='english', ngram_range=(1, 2))
        self.dbscan = DBSCAN(eps=0.3, min_samples=min_samples)
        self.baseline_stats: Dict[str, Any] = {}
        
    def _extract_numerical_features(self, events: List[Event]) -> np.ndarray:
        """Extract numerical features for anomaly detection"""
        features = []
        
        for ev in events:
            # Time-based features
            hour = ev.ts.hour if ev.ts else 12
            day_of_week = ev.ts.weekday() if ev.ts else 0
            
            # Message length and complexity
            msg_len = len(ev.message)
            word_count = len(ev.message.split())
            digit_ratio = sum(c.isdigit() for c in ev.message) / max(len(ev.message), 1)
            upper_ratio = sum(c.isupper() for c in ev.message) / max(len(ev.message), 1)
            
            # Level encoding
            level_map = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'ERROR': 3, 'FATAL': 4}
            level_score = level_map.get(ev.level or 'INFO', 1)
            
            # Tag count and criticality
            tag_count = len(ev.tags)
            has_critical = 1 if 'CRITICAL' in ev.tags else 0
            
            features.append([
                hour, day_of_week, msg_len, word_count, digit_ratio, 
                upper_ratio, level_score, tag_count, has_critical
            ])
            
        return np.array(features)
    
    def _detect_time_anomalies(self, events: List[Event]) -> List[AnomalyResult]:
        """Detect temporal anomalies like unusual timing patterns"""
        anomalies = []
        ts_events = [ev for ev in events if ev.ts]
        
        if len(ts_events) < 3:
            self.logger.debug("Not enough timestamped events for temporal anomaly detection")
            return anomalies
            
        # Calculate inter-arrival times
        intervals = []
        for i in range(1, len(ts_events)):
            delta = (ts_events[i].ts - ts_events[i-1].ts).total_seconds()
            intervals.append(delta)
        
        if not intervals:
            self.logger.debug("No intervals computed between timestamped events")
            return anomalies
            
        # Statistical outlier detection for intervals
        intervals_arr = np.array(intervals)
        q75, q25 = np.percentile(intervals_arr, [75, 25])
        iqr = q75 - q25
        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr
        
        for i, interval in enumerate(intervals):
            if interval < lower_bound or interval > upper_bound:
                anomaly_score = abs(interval - np.median(intervals_arr)) / (iqr + 1e-6)
                anomalies.append(AnomalyResult(
                    event_index=i+1,
                    anomaly_score=min(anomaly_score, 1.0),
                    anomaly_type="temporal",
                    confidence=0.8,
                    features={"interval": interval, "median": np.median(intervals_arr)}
                ))
        
        return anomalies
    
    def _detect_content_anomalies(self, events: List[Event]) -> List[AnomalyResult]:
        """Detect content-based anomalies using TF-IDF and clustering"""
        anomalies = []
        messages = [ev.message for ev in events]
        
        if len(messages) < self.min_samples:
            self.logger.debug("Not enough messages for content anomaly detection")
            return anomalies
            
        try:
            # TF-IDF vectorization
            tfidf_matrix = self.tfidf.fit_transform(messages)
            
            # DBSCAN clustering to find outliers
            clusters = self.dbscan.fit_predict(tfidf_matrix.toarray())
            
            # Events in cluster -1 are considered anomalies
            for i, cluster in enumerate(clusters):
                if cluster == -1:  # Outlier
                    # Calculate distance to nearest cluster center
                    distances = []
                    for cluster_id in set(clusters):
                        if cluster_id != -1:
                            cluster_points = tfidf_matrix[clusters == cluster_id]
                            if cluster_points.shape[0] > 0:
                                center = cluster_points.mean(axis=0)
                                dist = np.linalg.norm(tfidf_matrix[i] - center)
                                distances.append(dist)
                    
                    if distances:
                        anomaly_score = min(np.mean(distances), 1.0)
                        anomalies.append(AnomalyResult(
                            event_index=i,
                            anomaly_score=anomaly_score,
                            anomaly_type="content",
                            confidence=0.7,
                            features={"cluster": cluster, "message_length": len(messages[i])}
                        ))
                        
        except Exception as e:
            # Fallback to simple statistical analysis
            self.logger.warning(f"TF-IDF/DBSCAN content anomaly path failed: {e}")
            msg_lengths = [len(msg) for msg in messages]
            mean_len = np.mean(msg_lengths)
            std_len = np.std(msg_lengths)
            
            for i, length in enumerate(msg_lengths):
                if abs(length - mean_len) > 2 * std_len:
                    anomalies.append(AnomalyResult(
                        event_index=i,
                        anomaly_score=min(abs(length - mean_len) / (std_len + 1e-6), 1.0),
                        anomaly_type="content_statistical",
                        confidence=0.6,
                        features={"message_length": length, "mean_length": mean_len}
                    ))
        
        return anomalies
    
    def detect_anomalies(self, events: List[Event], baseline_events: Optional[List[Event]] = None) -> List[AnomalyResult]:
        """
        Comprehensive anomaly detection combining multiple approaches
        """
        all_anomalies = []
        
        if len(events) < self.min_samples:
            self.logger.debug("Not enough events for anomaly detection; returning empty list")
            return all_anomalies
        
        # 1. Numerical feature anomalies
        try:
            features = self._extract_numerical_features(events)
            if features.shape[0] > 0:
                features_scaled = self.scaler.fit_transform(features)
                anomaly_scores = self.isolation_forest.fit_predict(features_scaled)
                decision_scores = self.isolation_forest.decision_function(features_scaled)
                
                for i, (is_anomaly, score) in enumerate(zip(anomaly_scores, decision_scores)):
                    if is_anomaly == -1:  # Anomaly
                        all_anomalies.append(AnomalyResult(
                            event_index=i,
                            anomaly_score=min(abs(score), 1.0),
                            anomaly_type="numerical",
                            confidence=0.8,
                            features={f"feature_{j}": features[i][j] for j in range(features.shape[1])}
                        ))
        except Exception as e:
            self.logger.warning(f"Numerical anomaly path failed: {e}")
        
        # 2. Temporal anomalies
        all_anomalies.extend(self._detect_time_anomalies(events))
        
        # 3. Content anomalies
        all_anomalies.extend(self._detect_content_anomalies(events))
        
        # 4. Baseline comparison (if available)
        if baseline_events:
            baseline_anomalies = self._compare_with_baseline(events, baseline_events)
            all_anomalies.extend(baseline_anomalies)
        
        # Sort by anomaly score and remove duplicates
        unique_anomalies = {}
        for anomaly in all_anomalies:
            key = anomaly.event_index
            if key not in unique_anomalies or anomaly.anomaly_score > unique_anomalies[key].anomaly_score:
                unique_anomalies[key] = anomaly
        
        return sorted(unique_anomalies.values(), key=lambda x: x.anomaly_score, reverse=True)
    
    def _compare_with_baseline(self, current_events: List[Event], baseline_events: List[Event]) -> List[AnomalyResult]:
        """Compare current events against baseline to find deviations"""
        anomalies = []
        
        # Build baseline statistics
        baseline_levels = {}
        baseline_sources = {}
        baseline_patterns = set()
        
        for ev in baseline_events:
            baseline_levels[ev.level or 'UNKNOWN'] = baseline_levels.get(ev.level or 'UNKNOWN', 0) + 1
            baseline_sources[ev.source] = baseline_sources.get(ev.source, 0) + 1
            # Simple pattern: first 50 chars of message
            pattern = ev.message[:50] if len(ev.message) > 50 else ev.message
            baseline_patterns.add(pattern)
        
        # Check current events against baseline
        for i, ev in enumerate(current_events):
            anomaly_score = 0.0
            features = {}
            
            # Check if level is unusual
            current_level = ev.level or 'UNKNOWN'
            if current_level not in baseline_levels:
                anomaly_score += 0.3
                features['new_level'] = current_level
            
            # Check if source is unusual
            if ev.source not in baseline_sources:
                anomaly_score += 0.2
                features['new_source'] = ev.source
            
            # Check if message pattern is new
            pattern = ev.message[:50] if len(ev.message) > 50 else ev.message
            if pattern not in baseline_patterns:
                anomaly_score += 0.4
                features['new_pattern'] = True
            
            # Check for critical tags not seen in baseline
            baseline_tags = set()
            for bev in baseline_events:
                baseline_tags.update(bev.tags)
            
            new_critical_tags = [tag for tag in ev.tags if tag not in baseline_tags and 'CRITICAL' in tag]
            if new_critical_tags:
                anomaly_score += 0.5
                features['new_critical_tags'] = new_critical_tags
            
            if anomaly_score > 0.2:  # Threshold for baseline anomaly
                anomalies.append(AnomalyResult(
                    event_index=i,
                    anomaly_score=min(anomaly_score, 1.0),
                    anomaly_type="baseline_deviation",
                    confidence=0.9,
                    features=features
                ))
        
        return anomalies
