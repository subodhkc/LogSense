"""
redaction_reconstruction.py - Redaction-aware log reconstruction engine
Patent Implementation: Claims 1c, 5 - Template alignment and token clustering
"""

import re
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer

@dataclass
class RedactionPattern:
    pattern: str
    placeholder: str
    confidence: float
    context_tokens: List[str]
    reconstruction_hint: Optional[str] = None

@dataclass
class TokenCluster:
    cluster_id: int
    tokens: List[str]
    frequency: int
    context_similarity: float
    template_match: Optional[str] = None

class RedactionReconstructionEngine:
    """
    Reconstructs redacted logs using template alignment and fuzzy token clustering
    Implements patent claims for redaction-resilient processing
    """
    
    def __init__(self):
        self.redaction_patterns = self._initialize_patterns()
        self.template_profiles = {}
        self.token_clusters = []
        self.reconstruction_history = []
        
    def _initialize_patterns(self) -> List[RedactionPattern]:
        """Initialize common redaction patterns"""
        return [
            RedactionPattern(
                pattern=r'\[REDACTED\]',
                placeholder='[REDACTED]',
                confidence=0.9,
                context_tokens=['user', 'password', 'key', 'token', 'secret']
            ),
            RedactionPattern(
                pattern=r'\*{3,}',
                placeholder='***',
                confidence=0.8,
                context_tokens=['path', 'file', 'directory', 'name']
            ),
            RedactionPattern(
                pattern=r'X{4,}',
                placeholder='XXXX',
                confidence=0.7,
                context_tokens=['id', 'serial', 'number', 'code']
            ),
            RedactionPattern(
                pattern=r'<MASKED>',
                placeholder='<MASKED>',
                confidence=0.9,
                context_tokens=['ip', 'address', 'hostname', 'domain']
            ),
            RedactionPattern(
                pattern=r'\[HIDDEN\]',
                placeholder='[HIDDEN]',
                confidence=0.8,
                context_tokens=['config', 'setting', 'value', 'parameter']
            )
        ]
    
    def analyze_redaction_patterns(self, events: List) -> Dict[str, Any]:
        """
        Analyze log events to identify redaction patterns and build reconstruction profiles
        """
        redaction_analysis = {
            'detected_patterns': [],
            'redaction_density': 0.0,
            'affected_components': set(),
            'reconstruction_candidates': [],
            'confidence_scores': {}
        }
        
        total_events = len(events)
        redacted_events = 0
        
        for event in events:
            message = getattr(event, 'message', '')
            component = getattr(event, 'component', 'unknown')
            
            # Check for redaction patterns
            for pattern in self.redaction_patterns:
                matches = re.findall(pattern.pattern, message)
                if matches:
                    redacted_events += 1
                    redaction_analysis['detected_patterns'].append({
                        'pattern': pattern.placeholder,
                        'component': component,
                        'context': self._extract_context(message, pattern.placeholder),
                        'confidence': pattern.confidence
                    })
                    redaction_analysis['affected_components'].add(component)
        
        redaction_analysis['redaction_density'] = redacted_events / total_events if total_events > 0 else 0
        
        # Build template profiles
        self._build_template_profiles(events)
        
        # Generate reconstruction candidates
        redaction_analysis['reconstruction_candidates'] = self._generate_reconstruction_candidates(events)
        
        return redaction_analysis
    
    def reconstruct_redacted_content(self, events: List, confidence_threshold: float = 0.6) -> List:
        """
        Attempt to reconstruct redacted content using template alignment and clustering
        """
        reconstructed_events = []
        reconstruction_stats = {
            'attempted': 0,
            'successful': 0,
            'confidence_scores': []
        }
        
        for event in events:
            original_message = getattr(event, 'message', '')
            reconstructed_message = original_message
            
            # Check if message contains redacted content
            if self._contains_redaction(original_message):
                reconstruction_stats['attempted'] += 1
                
                # Attempt reconstruction
                reconstruction_result = self._reconstruct_message(original_message, event)
                
                if reconstruction_result['confidence'] >= confidence_threshold:
                    reconstructed_message = reconstruction_result['reconstructed_text']
                    reconstruction_stats['successful'] += 1
                    reconstruction_stats['confidence_scores'].append(reconstruction_result['confidence'])
                    
                    # Create new event with reconstructed content
                    reconstructed_event = type(event)(
                        timestamp=event.timestamp,
                        component=event.component,
                        message=reconstructed_message,
                        severity=event.severity
                    )
                    reconstructed_events.append(reconstructed_event)
                else:
                    reconstructed_events.append(event)
            else:
                reconstructed_events.append(event)
        
        # Store reconstruction history
        self.reconstruction_history.append({
            'timestamp': datetime.now(),
            'stats': reconstruction_stats,
            'events_processed': len(events)
        })
        
        return reconstructed_events
    
    def _extract_context(self, message: str, placeholder: str) -> List[str]:
        """Extract context tokens around redacted content"""
        # Split message and find placeholder position
        tokens = message.split()
        context_tokens = []
        
        for i, token in enumerate(tokens):
            if placeholder in token:
                # Get surrounding context (2 tokens before and after)
                start = max(0, i - 2)
                end = min(len(tokens), i + 3)
                context_tokens.extend(tokens[start:i] + tokens[i+1:end])
        
        return [token.lower().strip('.,!?:;') for token in context_tokens]
    
    def _build_template_profiles(self, events: List):
        """Build template profiles from non-redacted log patterns"""
        component_templates = defaultdict(list)
        
        for event in events:
            message = getattr(event, 'message', '')
            component = getattr(event, 'component', 'unknown')
            
            # Skip redacted messages for template building
            if not self._contains_redaction(message):
                # Extract template pattern (replace variable parts with placeholders)
                template = self._extract_template_pattern(message)
                component_templates[component].append(template)
        
        # Build frequency-based templates for each component
        for component, templates in component_templates.items():
            template_counts = Counter(templates)
            self.template_profiles[component] = [
                {'template': template, 'frequency': count}
                for template, count in template_counts.most_common(10)
            ]
    
    def _extract_template_pattern(self, message: str) -> str:
        """Extract template pattern by replacing variable content with placeholders"""
        # Replace common variable patterns
        template = message
        
        # Replace timestamps
        template = re.sub(r'\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}', '{TIMESTAMP}', template)
        
        # Replace file paths
        template = re.sub(r'[A-Z]:\\[^\s]+', '{FILEPATH}', template)
        template = re.sub(r'/[^\s]+', '{FILEPATH}', template)
        
        # Replace numbers
        template = re.sub(r'\b\d+\b', '{NUMBER}', template)
        
        # Replace hex values
        template = re.sub(r'0x[0-9a-fA-F]+', '{HEX}', template)
        
        # Replace GUIDs
        template = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '{GUID}', template)
        
        return template
    
    def _contains_redaction(self, message: str) -> bool:
        """Check if message contains redacted content"""
        for pattern in self.redaction_patterns:
            if re.search(pattern.pattern, message):
                return True
        return False
    
    def _reconstruct_message(self, message: str, event) -> Dict[str, Any]:
        """Attempt to reconstruct a single redacted message"""
        component = getattr(event, 'component', 'unknown')
        
        # Find best matching template
        best_template_match = self._find_best_template_match(message, component)
        
        if best_template_match:
            # Use template-based reconstruction
            return self._template_based_reconstruction(message, best_template_match)
        else:
            # Use clustering-based reconstruction
            return self._clustering_based_reconstruction(message, component)
    
    def _find_best_template_match(self, message: str, component: str) -> Optional[Dict]:
        """Find best matching template for reconstruction"""
        if component not in self.template_profiles:
            return None
        
        message_template = self._extract_template_pattern(message)
        best_match = None
        best_similarity = 0.0
        
        for template_info in self.template_profiles[component]:
            similarity = self._calculate_template_similarity(message_template, template_info['template'])
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = template_info
        
        if best_similarity > 0.7:  # Threshold for template matching
            return best_match
        
        return None
    
    def _calculate_template_similarity(self, template1: str, template2: str) -> float:
        """Calculate similarity between two templates"""
        tokens1 = set(template1.split())
        tokens2 = set(template2.split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _template_based_reconstruction(self, message: str, template_match: Dict) -> Dict[str, Any]:
        """Reconstruct using template matching"""
        template = template_match['template']
        confidence = min(0.8, template_match['frequency'] / 100.0)  # Frequency-based confidence
        
        # Simple placeholder replacement (could be enhanced with ML)
        reconstructed = message
        for pattern in self.redaction_patterns:
            if re.search(pattern.pattern, message):
                # Use context-aware replacement
                replacement = self._get_contextual_replacement(message, pattern)
                reconstructed = re.sub(pattern.pattern, replacement, reconstructed)
        
        return {
            'reconstructed_text': reconstructed,
            'confidence': confidence,
            'method': 'template_based',
            'template_used': template
        }
    
    def _clustering_based_reconstruction(self, message: str, component: str) -> Dict[str, Any]:
        """Reconstruct using token clustering"""
        # Extract context tokens
        context_tokens = []
        for pattern in self.redaction_patterns:
            if re.search(pattern.pattern, message):
                context_tokens.extend(self._extract_context(message, pattern.placeholder))
        
        if not context_tokens:
            return {
                'reconstructed_text': message,
                'confidence': 0.1,
                'method': 'clustering_based',
                'reason': 'no_context_tokens'
            }
        
        # Find similar contexts in historical data
        similar_contexts = self._find_similar_contexts(context_tokens, component)
        
        if similar_contexts:
            # Use most frequent reconstruction
            best_reconstruction = max(similar_contexts, key=lambda x: x['frequency'])
            confidence = min(0.7, best_reconstruction['frequency'] / 50.0)
            
            reconstructed = message
            for pattern in self.redaction_patterns:
                if re.search(pattern.pattern, message):
                    reconstructed = re.sub(pattern.pattern, best_reconstruction['value'], reconstructed)
            
            return {
                'reconstructed_text': reconstructed,
                'confidence': confidence,
                'method': 'clustering_based',
                'cluster_info': best_reconstruction
            }
        
        return {
            'reconstructed_text': message,
            'confidence': 0.2,
            'method': 'clustering_based',
            'reason': 'no_similar_contexts'
        }
    
    def _get_contextual_replacement(self, message: str, pattern: RedactionPattern) -> str:
        """Get contextual replacement for redacted content"""
        context_tokens = self._extract_context(message, pattern.placeholder)
        
        # Simple heuristic-based replacement
        if any(token in ['user', 'username', 'account'] for token in context_tokens):
            return '[USER_ID]'
        elif any(token in ['password', 'pass', 'pwd'] for token in context_tokens):
            return '[PASSWORD]'
        elif any(token in ['path', 'file', 'directory'] for token in context_tokens):
            return '[FILE_PATH]'
        elif any(token in ['ip', 'address'] for token in context_tokens):
            return '[IP_ADDRESS]'
        else:
            return '[RECONSTRUCTED]'
    
    def _find_similar_contexts(self, context_tokens: List[str], component: str) -> List[Dict]:
        """Find similar contexts in historical data"""
        # This would typically query a database of historical patterns
        # For now, return mock similar contexts
        return [
            {'value': '[SYSTEM_PATH]', 'frequency': 25, 'similarity': 0.8},
            {'value': '[CONFIG_VALUE]', 'frequency': 15, 'similarity': 0.6}
        ]
    
    def _generate_reconstruction_candidates(self, events: List) -> List[Dict]:
        """Generate potential reconstruction candidates"""
        candidates = []
        
        for event in events:
            message = getattr(event, 'message', '')
            if self._contains_redaction(message):
                candidate = {
                    'original_message': message,
                    'component': getattr(event, 'component', 'unknown'),
                    'timestamp': getattr(event, 'timestamp', datetime.now()),
                    'redaction_patterns': [],
                    'reconstruction_confidence': 0.0
                }
                
                # Identify specific patterns
                for pattern in self.redaction_patterns:
                    if re.search(pattern.pattern, message):
                        candidate['redaction_patterns'].append(pattern.placeholder)
                
                # Calculate reconstruction confidence
                candidate['reconstruction_confidence'] = self._estimate_reconstruction_confidence(message, event)
                
                candidates.append(candidate)
        
        return sorted(candidates, key=lambda x: x['reconstruction_confidence'], reverse=True)
    
    def _estimate_reconstruction_confidence(self, message: str, event) -> float:
        """Estimate confidence for successful reconstruction"""
        base_confidence = 0.3
        
        # More context = higher confidence
        context_tokens = []
        for pattern in self.redaction_patterns:
            if re.search(pattern.pattern, message):
                context_tokens.extend(self._extract_context(message, pattern.placeholder))
        
        context_bonus = min(len(context_tokens) * 0.1, 0.4)
        
        # Component with templates = higher confidence
        component = getattr(event, 'component', 'unknown')
        template_bonus = 0.2 if component in self.template_profiles else 0.0
        
        return min(base_confidence + context_bonus + template_bonus, 0.9)
    
    def get_reconstruction_stats(self) -> Dict[str, Any]:
        """Get reconstruction performance statistics"""
        if not self.reconstruction_history:
            return {'total_sessions': 0}
        
        total_attempted = sum(session['stats']['attempted'] for session in self.reconstruction_history)
        total_successful = sum(session['stats']['successful'] for session in self.reconstruction_history)
        
        all_confidence_scores = []
        for session in self.reconstruction_history:
            all_confidence_scores.extend(session['stats']['confidence_scores'])
        
        return {
            'total_sessions': len(self.reconstruction_history),
            'total_attempted': total_attempted,
            'total_successful': total_successful,
            'success_rate': total_successful / total_attempted if total_attempted > 0 else 0,
            'average_confidence': np.mean(all_confidence_scores) if all_confidence_scores else 0,
            'template_profiles_built': len(self.template_profiles)
        }
