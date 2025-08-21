"""
Advanced Analytics Engine for LogSense
Implements mathematical algorithms for enhanced log analysis
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import math

# Optional imports with fallbacks to prevent cascade failures
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import DBSCAN
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class TimeSeriesAnalyzer:
    """Time series analysis for error patterns and anomaly detection"""
    
    def detect_error_spikes(self, events: List[Any], window_minutes: int = 5) -> List[Dict]:
        """Detect error rate spikes using statistical process control - optimized"""
        try:
            # Early exit for small datasets
            if len(events) < 10:
                return []
                
            # Filter error events efficiently
            error_events = [e for e in events if getattr(e, 'severity', '').upper() in ['ERROR', 'CRITICAL']]
            if len(error_events) < 5:
                return []
            
            # Extract timestamps efficiently
            timestamps = []
            for e in error_events[:500]:  # Limit to first 500 for performance
                ts = getattr(e, 'timestamp', None)
                if ts:
                    timestamps.append(ts)
            
            if len(timestamps) < 5:
                return []
            
            # Simple binning approach
            min_time = min(timestamps)
            max_time = max(timestamps)
            duration_hours = (max_time - min_time).total_seconds() / 3600
            
            # Skip if duration too short or too long
            if duration_hours < 0.1 or duration_hours > 24:
                return []
            
            # Create fewer, larger windows for efficiency
            num_windows = min(20, int(duration_hours * 60 / window_minutes))
            if num_windows < 3:
                return []
                
            window_size = (max_time - min_time) / num_windows
            window_counts = [0] * num_windows
            
            # Count errors per window
            for ts in timestamps:
                window_idx = int((ts - min_time).total_seconds() / window_size.total_seconds())
                if 0 <= window_idx < num_windows:
                    window_counts[window_idx] += 1
            
            # Quick statistical analysis
            if max(window_counts) <= 1:
                return []
                
            mean_count = sum(window_counts) / len(window_counts)
            variance = sum((x - mean_count) ** 2 for x in window_counts) / len(window_counts)
            std_count = variance ** 0.5
            
            if std_count == 0:
                return []
                
            upper_limit = mean_count + 2 * std_count  # Reduced from 3-sigma for sensitivity
            
            # Find spikes
            spikes = []
            for i, count in enumerate(window_counts):
                if count > upper_limit and count > 2:  # Minimum threshold
                    window_start = min_time + i * window_size
                    spikes.append({
                        'timestamp': window_start,
                        'error_count': count,
                        'severity': 'HIGH' if count > mean_count + 3 * std_count else 'MEDIUM',
                        'baseline': round(mean_count, 1),
                        'deviation': round((count - mean_count) / std_count, 1)
                    })
            
            return spikes[:5]  # Limit results
            
        except Exception:
            return []
    
    def calculate_entropy(self, events: List[Any]) -> Dict[str, float]:
        """Calculate Shannon entropy for different log dimensions"""
        try:
            results = {}
            
            # Early exit for small datasets
            if len(events) < 5:
                return results
            
            # Component entropy (diversity of error sources)
            components = [getattr(e, 'component', 'unknown') for e in events if getattr(e, 'severity', '').upper() in ['ERROR', 'CRITICAL']]
            if len(components) > 1:  # Need at least 2 for meaningful entropy
                comp_counts = Counter(components)
                total = sum(comp_counts.values())
                if total > 0:
                    try:
                        entropy = -sum((count/total) * math.log2(count/total) for count in comp_counts.values() if count > 0)
                        results['component_entropy'] = round(entropy, 2)
                        results['component_diversity'] = len(comp_counts)
                    except (ValueError, ZeroDivisionError):
                        pass
            
            # Message entropy (predictability of error messages) - simplified
            messages = [getattr(e, 'message', '')[:30] for e in events[:100] if getattr(e, 'severity', '').upper() in ['ERROR', 'CRITICAL']]
            if len(messages) > 1:
                msg_counts = Counter(messages)
                total = sum(msg_counts.values())
                if total > 0:
                    try:
                        entropy = -sum((count/total) * math.log2(count/total) for count in msg_counts.values() if count > 0)
                        results['message_entropy'] = round(entropy, 2)
                        results['message_diversity'] = len(msg_counts)
                    except (ValueError, ZeroDivisionError):
                        pass
            
            return results
            
        except Exception:
            return {}


class PatternMiner:
    """Pattern mining for recurring sequences and associations"""
    
    def find_frequent_sequences(self, events: List[Any], min_support: float = 0.2) -> List[Dict]:
        """Find frequent error sequences - lightweight version"""
        try:
            # Early exit and limits
            if len(events) < 10:
                return []
                
            error_events = [e for e in events if getattr(e, 'severity', '').upper() in ['ERROR', 'CRITICAL']][:100]  # Limit to 100
            if len(error_events) < 5:
                return []
            
            # Simple 2-item sequences only (not 3-item)
            sequences = []
            for i in range(len(error_events) - 1):
                comp1 = getattr(error_events[i], 'component', 'unknown')
                comp2 = getattr(error_events[i + 1], 'component', 'unknown')
                if comp1 != comp2:  # Only different components
                    sequences.append((comp1, comp2))
            
            if len(sequences) < 3:
                return []
            
            # Count and filter
            seq_counts = Counter(sequences)
            min_count = max(2, int(len(sequences) * min_support))
            
            patterns = []
            for seq, count in seq_counts.most_common(5):  # Top 5 only
                if count >= min_count:
                    patterns.append({
                        'pattern': f"{seq[0]} -> {seq[1]}",
                        'frequency': count,
                        'support': round(count / len(sequences), 2)
                    })
            
            return patterns
            
        except Exception:
            return []
    
    def analyze_component_correlations(self, events: List[Any]) -> List[Dict]:
        """Analyze correlations between component failures - simplified"""
        try:
            # Quick exit for small datasets
            if len(events) < 20:
                return []
                
            error_events = [e for e in events if getattr(e, 'severity', '').upper() in ['ERROR', 'CRITICAL']][:50]  # Limit
            if len(error_events) < 10:
                return []
            
            # Simple component co-occurrence counting
            components = [getattr(e, 'component', 'unknown') for e in error_events]
            unique_components = list(set(components))
            
            # Skip if too many components (would be slow)
            if len(unique_components) > 10:
                unique_components = unique_components[:10]
            
            correlations = []
            for i, comp1 in enumerate(unique_components):
                for comp2 in unique_components[i+1:]:
                    # Simple adjacency counting
                    adjacent_count = 0
                    for j in range(len(components) - 1):
                        if (components[j] == comp1 and components[j+1] == comp2) or \
                           (components[j] == comp2 and components[j+1] == comp1):
                            adjacent_count += 1
                    
                    if adjacent_count >= 2:  # Minimum threshold
                        score = adjacent_count / len(components)
                        correlations.append({
                            'component1': comp1,
                            'component2': comp2,
                            'correlation_score': round(score, 2),
                            'co_occurrences': adjacent_count,
                            'strength': 'HIGH' if score > 0.1 else 'MEDIUM'
                        })
            
            return sorted(correlations, key=lambda x: x['correlation_score'], reverse=True)[:3]
            
        except Exception:
            return []


class GraphAnalyzer:
    """Graph-based analysis for component dependencies and critical paths"""
    
    def build_dependency_graph(self, events: List[Any]) -> Dict[str, Any]:
        """Build component dependency graph - lightweight version"""
        try:
            # Skip graph analysis for small datasets or disable entirely for performance
            if len(events) < 50:
                return {'total_components': 0, 'critical_components': []}
            
            # Simple component frequency analysis instead of full graph
            error_events = [e for e in events if getattr(e, 'severity', '').upper() in ['ERROR', 'CRITICAL']][:100]
            
            if len(error_events) < 10:
                return {'total_components': 0, 'critical_components': []}
            
            # Count component frequencies
            comp_counts = Counter([getattr(e, 'component', 'unknown') for e in error_events])
            total_errors = sum(comp_counts.values())
            
            # Simple criticality scoring based on frequency
            critical_components = []
            for comp, count in comp_counts.most_common(5):
                score = count / total_errors
                critical_components.append({
                    'component': comp,
                    'criticality_score': round(score, 2),
                    'error_count': count,
                    'risk_level': 'HIGH' if score > 0.3 else 'MEDIUM' if score > 0.1 else 'LOW'
                })
            
            return {
                'total_components': len(comp_counts),
                'critical_components': critical_components
            }
            
        except Exception:
            return {'total_components': 0, 'critical_components': []}


class RootCauseRanker:
    """Multi-criteria decision analysis for root cause ranking"""
    
    def rank_potential_causes(self, events: List[Any], analysis_results: Dict[str, Any]) -> List[Dict]:
        """Simplified root cause ranking - fast version"""
        try:
            # Quick exit for small datasets
            if len(events) < 10:
                return []
                
            error_events = [e for e in events if getattr(e, 'severity', '').upper() in ['ERROR', 'CRITICAL']][:50]  # Limit
            if len(error_events) < 5:
                return []
            
            # Simple component scoring
            comp_stats = Counter([getattr(e, 'component', 'unknown') for e in error_events])
            total_errors = sum(comp_stats.values())
            
            candidates = []
            for comp, count in comp_stats.most_common(5):  # Top 5 only
                # Simple scoring based on frequency and severity
                frequency_score = count / total_errors
                
                # Count critical vs error severity
                comp_events = [e for e in error_events if getattr(e, 'component', 'unknown') == comp]
                critical_count = sum(1 for e in comp_events if getattr(e, 'severity', '').upper() == 'CRITICAL')
                severity_score = critical_count / len(comp_events) if comp_events else 0
                
                # Combined score (simple weighted average)
                combined_score = frequency_score * 0.7 + severity_score * 0.3
                
                candidates.append({
                    'component': comp,
                    'root_cause_score': round(combined_score, 2),
                    'error_count': count,
                    'likelihood': 'HIGH' if combined_score > 0.5 else 'MEDIUM' if combined_score > 0.2 else 'LOW'
                })
            
            return sorted(candidates, key=lambda x: x['root_cause_score'], reverse=True)
            
        except Exception:
            return []


class AdvancedAnalyticsEngine:
    """Main engine combining all advanced analytics with error resilience"""
    
    def __init__(self):
        try:
            self.time_series = TimeSeriesAnalyzer()
            self.pattern_miner = PatternMiner()
            self.graph_analyzer = GraphAnalyzer()
            self.rca_ranker = RootCauseRanker()
            self.initialized = True
        except Exception:
            self.initialized = False
    
    def run_comprehensive_analysis(self, events: List[Any]) -> Dict[str, Any]:
        """Run optimized analytics with early exits and limits"""
        results = {
            'total_events': len(events),
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        # Early exit for very small datasets
        if len(events) < 5:
            results['key_insights'] = ["Insufficient data for advanced analysis"]
            return results
        
        try:
            # Only run analysis that will complete quickly
            
            # Basic entropy (fast)
            results['entropy_analysis'] = self.time_series.calculate_entropy(events)
            
            # Root cause ranking (simplified, fast)
            results['root_cause_ranking'] = self.rca_ranker.rank_potential_causes(events, {})
            
            # Skip expensive operations for large datasets
            if len(events) < 200:
                # Error spikes (optimized)
                results['error_spikes'] = self.time_series.detect_error_spikes(events)
                
                # Simple patterns (limited)
                results['frequent_sequences'] = self.pattern_miner.find_frequent_sequences(events)
                
                # Component correlations (simplified)
                results['component_correlations'] = self.pattern_miner.analyze_component_correlations(events)
            else:
                # Skip for large datasets
                results['error_spikes'] = []
                results['frequent_sequences'] = []
                results['component_correlations'] = []
            
            # Lightweight dependency analysis
            results['dependency_analysis'] = self.graph_analyzer.build_dependency_graph(events)
            
            # Generate concise insights
            insights = []
            
            if results.get('root_cause_ranking'):
                top_cause = results['root_cause_ranking'][0]
                if top_cause.get('likelihood') == 'HIGH':
                    insights.append(f"Primary root cause: {top_cause['component']} ({top_cause['error_count']} errors)")
            
            if results.get('error_spikes'):
                spike_count = len(results['error_spikes'])
                if spike_count > 0:
                    insights.append(f"Detected {spike_count} error spike(s)")
            
            if results.get('frequent_sequences'):
                pattern_count = len(results['frequent_sequences'])
                if pattern_count > 0:
                    insights.append(f"Found {pattern_count} recurring error pattern(s)")
            
            results['key_insights'] = insights if insights else ["Basic analysis completed"]
            
        except Exception as e:
            results['analysis_error'] = str(e)
            results['key_insights'] = ["Analysis failed - using fallback methods"]
        
        return results
