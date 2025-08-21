"""
tiered_rca_engine.py - Multi-tier RCA pipeline with fallback escalation
Patent Implementation: Claims 1, 2, 4, 7, 9
"""

import uuid
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Import existing modules
from rca_rules import get_all_rca_summaries
from ai_rca import analyze_with_ai
from clustering_model import cluster_events
from decision_tree_model import analyze_event_severity
from anomaly_svm import detect_anomalies

class DiagnosticTier(Enum):
    RULE_BASED = "rule_based"
    MACHINE_LEARNING = "machine_learning"
    LOCAL_LLM = "local_llm"
    EXTERNAL_GENAI = "external_genai"

@dataclass
class DiagnosticResult:
    tier: DiagnosticTier
    confidence_score: float
    outcome: Any
    execution_time: float
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None

@dataclass
class SessionSnapshot:
    session_id: str
    timestamp: datetime
    input_hash: str
    diagnostic_path: List[DiagnosticTier]
    results: List[DiagnosticResult]
    final_outcome: Any
    redaction_applied: bool
    compliance_tags: List[str]

class TieredRCAEngine:
    """
    Multi-tier diagnostic engine with confidence-based fallback escalation
    Implements patent claims for autonomous RCA with traceability
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.session_history: List[SessionSnapshot] = []
        
    def _default_config(self) -> Dict:
        """Default configuration for tier thresholds and escalation rules"""
        return {
            "confidence_thresholds": {
                DiagnosticTier.RULE_BASED: 0.7,
                DiagnosticTier.MACHINE_LEARNING: 0.8,
                DiagnosticTier.LOCAL_LLM: 0.85,
                DiagnosticTier.EXTERNAL_GENAI: 0.9
            },
            "max_tier": DiagnosticTier.LOCAL_LLM,  # Configurable ceiling
            "enable_genai_fallback": False,
            "session_retention_days": 90,
            "compliance_mode": True
        }
    
    def analyze(self, events: List, metadata: Dict, user_context: Dict) -> Tuple[Any, SessionSnapshot]:
        """
        Main analysis entry point with tiered escalation
        Returns final result and complete session snapshot
        """
        session_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # Create input hash for traceability
        input_data = {
            "events_count": len(events),
            "metadata": metadata,
            "context": user_context
        }
        input_hash = hashlib.sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest()
        
        diagnostic_path = []
        results = []
        final_outcome = None
        
        # Start with rule-based tier
        current_tier = DiagnosticTier.RULE_BASED
        
        while current_tier and not self._is_sufficient_confidence(results):
            try:
                result = self._execute_tier(current_tier, events, metadata, user_context)
                results.append(result)
                diagnostic_path.append(current_tier)
                
                if result.confidence_score >= self.config["confidence_thresholds"][current_tier]:
                    final_outcome = result.outcome
                    break
                    
                # Escalate to next tier
                current_tier = self._get_next_tier(current_tier)
                
            except Exception as e:
                # Log failure and escalate
                failed_result = DiagnosticResult(
                    tier=current_tier,
                    confidence_score=0.0,
                    outcome=None,
                    execution_time=0.0,
                    error_message=str(e)
                )
                results.append(failed_result)
                current_tier = self._get_next_tier(current_tier)
        
        # Create session snapshot
        snapshot = SessionSnapshot(
            session_id=session_id,
            timestamp=start_time,
            input_hash=input_hash,
            diagnostic_path=diagnostic_path,
            results=results,
            final_outcome=final_outcome or self._get_best_result(results),
            redaction_applied=self._detect_redaction(events),
            compliance_tags=self._generate_compliance_tags(user_context)
        )
        
        # Store for audit trail
        self.session_history.append(snapshot)
        
        return final_outcome, snapshot
    
    def _execute_tier(self, tier: DiagnosticTier, events: List, metadata: Dict, user_context: Dict) -> DiagnosticResult:
        """Execute specific diagnostic tier and return result with confidence"""
        start_time = datetime.now()
        
        try:
            if tier == DiagnosticTier.RULE_BASED:
                outcome = get_all_rca_summaries(events, metadata, user_context)
                confidence = self._calculate_rule_confidence(outcome)
                
            elif tier == DiagnosticTier.MACHINE_LEARNING:
                # Combine ML insights
                ml_results = {
                    "clustering": cluster_events(events),
                    "decision_tree": analyze_event_severity(events),
                    "anomaly_detection": detect_anomalies(events)
                }
                outcome = ml_results
                confidence = self._calculate_ml_confidence(ml_results)
                
            elif tier == DiagnosticTier.LOCAL_LLM:
                outcome = analyze_with_ai(events, metadata, None, user_context, offline=True)
                confidence = self._calculate_llm_confidence(outcome)
                
            elif tier == DiagnosticTier.EXTERNAL_GENAI:
                outcome = analyze_with_ai(events, metadata, None, user_context, offline=False)
                confidence = self._calculate_genai_confidence(outcome)
                
            else:
                raise ValueError(f"Unknown tier: {tier}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return DiagnosticResult(
                tier=tier,
                confidence_score=confidence,
                outcome=outcome,
                execution_time=execution_time,
                metadata={"events_processed": len(events)}
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return DiagnosticResult(
                tier=tier,
                confidence_score=0.0,
                outcome=None,
                execution_time=execution_time,
                error_message=str(e)
            )
    
    def _calculate_rule_confidence(self, outcome: List) -> float:
        """Calculate confidence for rule-based results"""
        if not outcome:
            return 0.1
        
        # Higher confidence for more specific matches
        specificity_score = min(len(outcome) * 0.2, 0.8)
        base_confidence = 0.6 if outcome else 0.1
        
        return min(base_confidence + specificity_score, 1.0)
    
    def _calculate_ml_confidence(self, ml_results: Dict) -> float:
        """Calculate confidence for ML results"""
        valid_results = sum(1 for result in ml_results.values() if result is not None)
        total_models = len(ml_results)
        
        if total_models == 0:
            return 0.1
            
        # Confidence based on model agreement
        return min(0.5 + (valid_results / total_models) * 0.3, 0.85)
    
    def _calculate_llm_confidence(self, outcome: str) -> float:
        """Calculate confidence for LLM results"""
        if not outcome or len(outcome) < 100:
            return 0.3
        
        # Simple heuristic based on response completeness
        confidence_indicators = [
            "root cause" in outcome.lower(),
            "recommendation" in outcome.lower(),
            len(outcome) > 500,
            "error" in outcome.lower() or "critical" in outcome.lower()
        ]
        
        return min(0.6 + sum(confidence_indicators) * 0.1, 0.9)
    
    def _calculate_genai_confidence(self, outcome: str) -> float:
        """Calculate confidence for external GenAI results"""
        # Assume higher confidence for external AI
        return min(self._calculate_llm_confidence(outcome) + 0.1, 0.95)
    
    def _get_next_tier(self, current_tier: DiagnosticTier) -> Optional[DiagnosticTier]:
        """Determine next escalation tier"""
        tier_order = [
            DiagnosticTier.RULE_BASED,
            DiagnosticTier.MACHINE_LEARNING,
            DiagnosticTier.LOCAL_LLM,
            DiagnosticTier.EXTERNAL_GENAI
        ]
        
        try:
            current_index = tier_order.index(current_tier)
            if current_index + 1 < len(tier_order):
                next_tier = tier_order[current_index + 1]
                
                # Check configuration limits
                if next_tier == DiagnosticTier.EXTERNAL_GENAI and not self.config["enable_genai_fallback"]:
                    return None
                    
                max_tier_index = tier_order.index(self.config["max_tier"])
                if tier_order.index(next_tier) <= max_tier_index:
                    return next_tier
                    
        except (ValueError, IndexError):
            pass
            
        return None
    
    def _is_sufficient_confidence(self, results: List[DiagnosticResult]) -> bool:
        """Check if any result meets confidence threshold"""
        for result in results:
            if result.confidence_score >= self.config["confidence_thresholds"].get(result.tier, 0.8):
                return True
        return False
    
    def _get_best_result(self, results: List[DiagnosticResult]) -> Any:
        """Get highest confidence result as fallback"""
        if not results:
            return None
            
        valid_results = [r for r in results if r.outcome is not None]
        if not valid_results:
            return None
            
        return max(valid_results, key=lambda r: r.confidence_score).outcome
    
    def _detect_redaction(self, events: List) -> bool:
        """Detect if logs contain redacted content"""
        redaction_patterns = ["[REDACTED]", "***", "XXXXX", "<MASKED>"]
        
        for event in events[:50]:  # Sample first 50 events
            message = getattr(event, 'message', '')
            if any(pattern in message for pattern in redaction_patterns):
                return True
        return False
    
    def _generate_compliance_tags(self, user_context: Dict) -> List[str]:
        """Generate compliance tags based on context"""
        tags = ["rca_session"]
        
        if user_context.get("test_environment") == "Production":
            tags.append("production_analysis")
        
        if user_context.get("issue_severity") in ["High - System Down", "Critical - Data Loss"]:
            tags.append("critical_incident")
            
        if user_context.get("business_impact") in ["High - Revenue Impact", "Critical - Business Stoppage"]:
            tags.append("business_critical")
            
        return tags
    
    def get_session_by_id(self, session_id: str) -> Optional[SessionSnapshot]:
        """Retrieve session snapshot by ID for audit purposes"""
        for snapshot in self.session_history:
            if snapshot.session_id == session_id:
                return snapshot
        return None
    
    def export_audit_trail(self, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Export audit trail for compliance reporting"""
        filtered_sessions = self.session_history
        
        if start_date:
            filtered_sessions = [s for s in filtered_sessions if s.timestamp >= start_date]
        if end_date:
            filtered_sessions = [s for s in filtered_sessions if s.timestamp <= end_date]
            
        return [asdict(session) for session in filtered_sessions]
