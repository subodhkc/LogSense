# analysis/advanced_correlation.py
from __future__ import annotations
import re
import networkx as nx
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from datamodels.events import Event

@dataclass(frozen=True)
class CorrelationRule:
    name: str
    conditions: List[Dict[str, Any]]
    window_seconds: int
    confidence_threshold: float
    description: str

@dataclass(frozen=True)
class CorrelationMatch:
    rule_name: str
    event_indices: List[int]
    confidence: float
    start_time: datetime
    end_time: datetime
    metadata: Dict[str, Any]

class AdvancedCorrelationEngine:
    """
    Advanced event correlation engine that can:
    - Detect causal chains and dependency failures
    - Find recurring patterns across time windows
    - Identify cascading failures
    - Correlate across different log sources
    """
    
    def __init__(self):
        self.rules: List[CorrelationRule] = []
        self.event_graph = nx.DiGraph()
        self.pattern_cache: Dict[str, List[Event]] = {}
        
    def add_rule(self, rule: CorrelationRule):
        """Add a correlation rule to the engine"""
        self.rules.append(rule)
    
    def add_default_rules(self):
        """Add common correlation rules for Windows/application logs"""
        
        # Service failure cascade
        self.add_rule(CorrelationRule(
            name="service_failure_cascade",
            conditions=[
                {"level": "WARN", "contains": "service"},
                {"level": "ERROR", "contains": "dependency"},
                {"level": "FATAL", "contains": "shutdown"}
            ],
            window_seconds=300,
            confidence_threshold=0.8,
            description="Service dependency failure leading to shutdown"
        ))
        
        # Authentication failure pattern
        self.add_rule(CorrelationRule(
            name="auth_brute_force",
            conditions=[
                {"level": "WARN", "contains": "login"},
                {"level": "WARN", "contains": "login"},
                {"level": "ERROR", "contains": "account locked"}
            ],
            window_seconds=600,
            confidence_threshold=0.9,
            description="Multiple login failures leading to account lockout"
        ))
        
        # Disk space exhaustion
        self.add_rule(CorrelationRule(
            name="disk_space_exhaustion",
            conditions=[
                {"level": "WARN", "contains": "disk space"},
                {"level": "ERROR", "contains": "write failed"},
                {"level": "FATAL", "contains": "out of space"}
            ],
            window_seconds=1800,
            confidence_threshold=0.85,
            description="Progressive disk space exhaustion"
        ))
        
        # Network connectivity issues
        self.add_rule(CorrelationRule(
            name="network_degradation",
            conditions=[
                {"level": "WARN", "contains": "timeout"},
                {"level": "WARN", "contains": "retry"},
                {"level": "ERROR", "contains": "connection"}
            ],
            window_seconds=900,
            confidence_threshold=0.7,
            description="Network connectivity degradation pattern"
        ))
        
        # Memory pressure cascade
        self.add_rule(CorrelationRule(
            name="memory_pressure",
            conditions=[
                {"level": "WARN", "contains": "memory"},
                {"level": "ERROR", "contains": "allocation"},
                {"level": "FATAL", "contains": "out of memory"}
            ],
            window_seconds=600,
            confidence_threshold=0.9,
            description="Memory pressure leading to allocation failures"
        ))
    
    def _match_condition(self, event: Event, condition: Dict[str, Any]) -> bool:
        """Check if an event matches a condition"""
        if "level" in condition and (event.level or "").upper() != condition["level"].upper():
            return False
        
        if "contains" in condition and condition["contains"].lower() not in event.message.lower():
            return False
        
        if "event_id" in condition and str(event.event_id) != str(condition["event_id"]):
            return False
        
        if "source" in condition and condition["source"] not in event.source:
            return False
        
        if "tag" in condition and condition["tag"] not in event.tags:
            return False
        
        return True
    
    def find_correlations(self, events: List[Event]) -> List[CorrelationMatch]:
        """Find all correlation matches in the event stream"""
        matches = []
        
        # Sort events by timestamp
        sorted_events = sorted([e for e in events if e.ts], key=lambda x: x.ts)
        
        for rule in self.rules:
            rule_matches = self._find_rule_matches(sorted_events, rule)
            matches.extend(rule_matches)
        
        return sorted(matches, key=lambda x: x.confidence, reverse=True)
    
    def _find_rule_matches(self, events: List[Event], rule: CorrelationRule) -> List[CorrelationMatch]:
        """Find matches for a specific correlation rule"""
        matches = []
        window_delta = timedelta(seconds=rule.window_seconds)
        
        for i, start_event in enumerate(events):
            if not self._match_condition(start_event, rule.conditions[0]):
                continue
            
            # Try to match the sequence starting from this event
            matched_indices = [i]
            current_condition_idx = 1
            
            for j in range(i + 1, len(events)):
                if events[j].ts - start_event.ts > window_delta:
                    break
                
                if current_condition_idx >= len(rule.conditions):
                    break
                
                if self._match_condition(events[j], rule.conditions[current_condition_idx]):
                    matched_indices.append(j)
                    current_condition_idx += 1
            
            # Check if we matched all conditions
            if len(matched_indices) == len(rule.conditions):
                confidence = self._calculate_confidence(events, matched_indices, rule)
                
                if confidence >= rule.confidence_threshold:
                    matches.append(CorrelationMatch(
                        rule_name=rule.name,
                        event_indices=matched_indices,
                        confidence=confidence,
                        start_time=events[matched_indices[0]].ts,
                        end_time=events[matched_indices[-1]].ts,
                        metadata={
                            "description": rule.description,
                            "window_seconds": rule.window_seconds,
                            "event_count": len(matched_indices)
                        }
                    ))
        
        return matches
    
    def _calculate_confidence(self, events: List[Event], indices: List[int], rule: CorrelationRule) -> float:
        """Calculate confidence score for a correlation match"""
        base_confidence = 0.5
        
        # Time proximity bonus
        time_span = (events[indices[-1]].ts - events[indices[0]].ts).total_seconds()
        time_factor = max(0, 1 - (time_span / rule.window_seconds))
        base_confidence += 0.2 * time_factor
        
        # Severity escalation bonus
        levels = [events[i].level or "INFO" for i in indices]
        level_scores = {"DEBUG": 1, "INFO": 2, "WARN": 3, "ERROR": 4, "FATAL": 5}
        if all(level_scores.get(levels[i], 2) <= level_scores.get(levels[i+1], 2) for i in range(len(levels)-1)):
            base_confidence += 0.2
        
        # Source consistency bonus
        sources = [events[i].source for i in indices]
        if len(set(sources)) == 1:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def build_event_graph(self, events: List[Event], correlations: List[CorrelationMatch]):
        """Build a directed graph of event relationships"""
        self.event_graph.clear()
        
        # Add events as nodes
        for i, event in enumerate(events):
            self.event_graph.add_node(i, 
                                    timestamp=event.ts,
                                    level=event.level,
                                    message=event.message[:100],
                                    source=event.source)
        
        # Add correlation edges
        for correlation in correlations:
            indices = correlation.event_indices
            for i in range(len(indices) - 1):
                self.event_graph.add_edge(indices[i], indices[i+1],
                                        correlation=correlation.rule_name,
                                        confidence=correlation.confidence)
    
    def find_root_causes(self, events: List[Event], correlations: List[CorrelationMatch]) -> List[Dict[str, Any]]:
        """Identify potential root causes using graph analysis"""
        self.build_event_graph(events, correlations)
        root_causes = []
        
        # Find nodes with high out-degree (events that trigger many others)
        for node in self.event_graph.nodes():
            out_degree = self.event_graph.out_degree(node)
            in_degree = self.event_graph.in_degree(node)
            
            if out_degree > 2 and in_degree == 0:  # Potential root cause
                event = events[node]
                root_causes.append({
                    "event_index": node,
                    "event": event,
                    "triggered_count": out_degree,
                    "confidence": min(out_degree / 5.0, 1.0),
                    "type": "cascade_initiator"
                })
        
        # Find strongly connected components (circular dependencies)
        try:
            sccs = list(nx.strongly_connected_components(self.event_graph))
            for scc in sccs:
                if len(scc) > 2:  # Circular dependency
                    root_causes.append({
                        "event_indices": list(scc),
                        "events": [events[i] for i in scc],
                        "confidence": 0.8,
                        "type": "circular_dependency"
                    })
        except:
            pass
        
        return sorted(root_causes, key=lambda x: x["confidence"], reverse=True)
    
    def detect_recurring_patterns(self, events: List[Event], min_occurrences: int = 3) -> List[Dict[str, Any]]:
        """Detect recurring patterns in the event stream"""
        patterns = []
        
        # Group events by normalized message patterns
        pattern_groups = defaultdict(list)
        
        for i, event in enumerate(events):
            # Normalize message (remove timestamps, numbers, etc.)
            normalized = re.sub(r'\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}', '[TIMESTAMP]', event.message)
            normalized = re.sub(r'\b\d+\b', '[NUMBER]', normalized)
            normalized = re.sub(r'\b0x[0-9a-fA-F]+\b', '[HEX]', normalized)
            normalized = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP]', normalized)
            
            pattern_key = f"{event.level}:{normalized[:100]}"
            pattern_groups[pattern_key].append((i, event))
        
        # Find patterns that occur frequently
        for pattern_key, event_list in pattern_groups.items():
            if len(event_list) >= min_occurrences:
                # Analyze timing patterns
                timestamps = [e[1].ts for e in event_list if e[1].ts]
                if len(timestamps) >= 2:
                    intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() 
                               for i in range(len(timestamps)-1)]
                    avg_interval = sum(intervals) / len(intervals)
                    
                    patterns.append({
                        "pattern": pattern_key,
                        "occurrences": len(event_list),
                        "event_indices": [e[0] for e in event_list],
                        "avg_interval_seconds": avg_interval,
                        "confidence": min(len(event_list) / 10.0, 1.0),
                        "type": "recurring_pattern"
                    })
        
        return sorted(patterns, key=lambda x: x["occurrences"], reverse=True)
    
    def analyze_cascading_failures(self, events: List[Event], time_window: int = 300) -> List[Dict[str, Any]]:
        """Detect cascading failure patterns"""
        cascades = []
        window_delta = timedelta(seconds=time_window)
        
        # Find error/fatal events that might be cascade triggers
        critical_events = [(i, e) for i, e in enumerate(events) 
                          if e.level in ['ERROR', 'FATAL'] and e.ts]
        
        for i, (idx, trigger_event) in enumerate(critical_events):
            cascade_events = [idx]
            
            # Look for subsequent errors within the time window
            for j, (other_idx, other_event) in enumerate(critical_events[i+1:], i+1):
                if other_event.ts - trigger_event.ts > window_delta:
                    break
                
                # Check if this could be a consequence
                if (other_event.source != trigger_event.source or 
                    other_event.level in ['ERROR', 'FATAL']):
                    cascade_events.append(other_idx)
            
            # If we found a cascade (3+ related events)
            if len(cascade_events) >= 3:
                cascades.append({
                    "trigger_index": idx,
                    "trigger_event": trigger_event,
                    "cascade_indices": cascade_events,
                    "cascade_events": [events[i] for i in cascade_events],
                    "duration_seconds": (events[cascade_events[-1]].ts - trigger_event.ts).total_seconds(),
                    "affected_sources": len(set(events[i].source for i in cascade_events)),
                    "confidence": min(len(cascade_events) / 5.0, 1.0),
                    "type": "cascading_failure"
                })
        
        return sorted(cascades, key=lambda x: x["confidence"], reverse=True)
