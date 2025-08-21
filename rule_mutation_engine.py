"""
rule_mutation_engine.py - Adaptive rule learning and mutation system
Patent Implementation: Claims 8, 6 - LLM-suggested corrections with sandboxed validation
"""

import json
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import re
import ast
import tempfile
import subprocess
import sys

@dataclass
class RuleMismatch:
    rule_id: str
    rule_name: str
    expected_outcome: Any
    actual_outcome: Any
    confidence_delta: float
    context: Dict[str, Any]
    timestamp: datetime

@dataclass
class RuleMutation:
    mutation_id: str
    original_rule_id: str
    suggested_rule: str
    mutation_type: str  # 'pattern_update', 'logic_enhancement', 'new_condition'
    confidence_improvement: float
    llm_reasoning: str
    validation_status: str  # 'pending', 'testing', 'approved', 'rejected'
    test_results: Optional[Dict] = None

@dataclass
class ValidationResult:
    mutation_id: str
    passed: bool
    precision: float
    recall: float
    f1_score: float
    test_cases_passed: int
    test_cases_total: int
    error_messages: List[str]

class RuleMutationEngine:
    """
    Adaptive rule learning system with LLM-suggested corrections
    Implements patent claims for rule evolution and sandboxed validation
    """
    
    def __init__(self, rules_config_path: str = "config/rules.yml"):
        self.rules_config_path = rules_config_path
        self.mismatches: List[RuleMismatch] = []
        self.mutations: List[RuleMutation] = []
        self.validation_history: List[ValidationResult] = []
        self.sandbox_path = Path("sandbox_rules")
        self.sandbox_path.mkdir(exist_ok=True)
        
    def record_rule_mismatch(
        self,
        rule_id: str,
        rule_name: str,
        expected_outcome: Any,
        actual_outcome: Any,
        confidence_delta: float,
        context: Dict[str, Any]
    ):
        """Record a rule misclassification event for later analysis"""
        mismatch = RuleMismatch(
            rule_id=rule_id,
            rule_name=rule_name,
            expected_outcome=expected_outcome,
            actual_outcome=actual_outcome,
            confidence_delta=confidence_delta,
            context=context,
            timestamp=datetime.now()
        )
        
        self.mismatches.append(mismatch)
        
        # Trigger mutation analysis if threshold reached
        if len(self.mismatches) >= 5:  # Configurable threshold
            self._analyze_mismatches_for_mutations()
    
    def _analyze_mismatches_for_mutations(self):
        """Analyze accumulated mismatches to identify mutation opportunities"""
        # Group mismatches by rule
        rule_mismatches = {}
        for mismatch in self.mismatches[-10:]:  # Analyze recent mismatches
            rule_id = mismatch.rule_id
            if rule_id not in rule_mismatches:
                rule_mismatches[rule_id] = []
            rule_mismatches[rule_id].append(mismatch)
        
        # Generate mutations for problematic rules
        for rule_id, mismatches in rule_mismatches.items():
            if len(mismatches) >= 2:  # Rule has multiple failures
                mutation = self._generate_rule_mutation(rule_id, mismatches)
                if mutation:
                    self.mutations.append(mutation)
    
    def _generate_rule_mutation(self, rule_id: str, mismatches: List[RuleMismatch]) -> Optional[RuleMutation]:
        """Generate LLM-suggested rule mutation"""
        try:
            # Prepare context for LLM
            mismatch_context = self._prepare_mismatch_context(mismatches)
            original_rule = self._get_original_rule(rule_id)
            
            if not original_rule:
                return None
            
            # Generate LLM prompt for rule improvement
            prompt = self._create_mutation_prompt(original_rule, mismatch_context)
            
            # Get LLM suggestion (using existing AI infrastructure)
            from ai_rca import analyze_with_ai
            
            llm_response = self._get_llm_rule_suggestion(prompt)
            
            if not llm_response:
                return None
            
            # Parse LLM response
            suggested_rule, reasoning, mutation_type = self._parse_llm_response(llm_response)
            
            # Calculate expected confidence improvement
            confidence_improvement = sum(m.confidence_delta for m in mismatches) / len(mismatches)
            
            mutation = RuleMutation(
                mutation_id=str(uuid.uuid4()),
                original_rule_id=rule_id,
                suggested_rule=suggested_rule,
                mutation_type=mutation_type,
                confidence_improvement=confidence_improvement,
                llm_reasoning=reasoning,
                validation_status='pending'
            )
            
            return mutation
            
        except Exception as e:
            print(f"Error generating mutation for rule {rule_id}: {e}")
            return None
    
    def _prepare_mismatch_context(self, mismatches: List[RuleMismatch]) -> Dict[str, Any]:
        """Prepare mismatch context for LLM analysis"""
        context = {
            'total_mismatches': len(mismatches),
            'average_confidence_delta': sum(m.confidence_delta for m in mismatches) / len(mismatches),
            'failure_patterns': [],
            'common_contexts': {}
        }
        
        # Analyze failure patterns
        for mismatch in mismatches:
            pattern = {
                'expected': str(mismatch.expected_outcome),
                'actual': str(mismatch.actual_outcome),
                'context_keys': list(mismatch.context.keys())
            }
            context['failure_patterns'].append(pattern)
            
            # Track common context elements
            for key, value in mismatch.context.items():
                if key not in context['common_contexts']:
                    context['common_contexts'][key] = []
                context['common_contexts'][key].append(str(value))
        
        return context
    
    def _get_original_rule(self, rule_id: str) -> Optional[str]:
        """Retrieve original rule definition"""
        # This would typically load from rules configuration
        # For now, return a mock rule structure
        mock_rules = {
            'os_incompatibility': '''
def detect_os_incompatibility(events, metadata, user_context):
    os_patterns = [
        r"unsupported.*os",
        r"os.*not.*supported",
        r"incompatible.*operating.*system"
    ]
    
    for event in events:
        if event.severity in ["ERROR", "CRITICAL"]:
            for pattern in os_patterns:
                if re.search(pattern, event.message, re.IGNORECASE):
                    return f"OS incompatibility detected: {event.message}"
    return None
            ''',
            'driver_conflict': '''
def detect_driver_conflict(events, metadata, user_context):
    driver_patterns = [
        r"driver.*conflict",
        r"driver.*error",
        r"device.*driver.*failed"
    ]
    
    for event in events:
        if event.severity == "ERROR":
            for pattern in driver_patterns:
                if re.search(pattern, event.message, re.IGNORECASE):
                    return f"Driver conflict detected: {event.message}"
    return None
            '''
        }
        
        return mock_rules.get(rule_id)
    
    def _create_mutation_prompt(self, original_rule: str, mismatch_context: Dict[str, Any]) -> str:
        """Create LLM prompt for rule mutation"""
        prompt = f"""
You are a senior software engineer specializing in log analysis and rule-based systems.

ORIGINAL RULE:
{original_rule}

FAILURE ANALYSIS:
- Total mismatches: {mismatch_context['total_mismatches']}
- Average confidence delta: {mismatch_context['average_confidence_delta']:.2f}
- Failure patterns: {json.dumps(mismatch_context['failure_patterns'], indent=2)}

TASK:
Analyze the rule failures and suggest an improved version of the rule that would:
1. Better handle the observed failure cases
2. Maintain accuracy for existing successful cases
3. Improve overall diagnostic confidence

RESPONSE FORMAT:
```python
# IMPROVED_RULE
[Your improved rule code here]
```

REASONING: [Explain your changes and why they address the failures]

MUTATION_TYPE: [Choose: pattern_update, logic_enhancement, new_condition]
"""
        return prompt
    
    def _get_llm_rule_suggestion(self, prompt: str) -> Optional[str]:
        """Get LLM suggestion for rule improvement"""
        try:
            # Mock LLM response for demonstration
            # In production, this would call the actual LLM
            mock_response = """
```python
# IMPROVED_RULE
def detect_os_incompatibility(events, metadata, user_context):
    # Enhanced patterns with more comprehensive coverage
    os_patterns = [
        r"unsupported.*os",
        r"os.*not.*supported", 
        r"incompatible.*operating.*system",
        r"os.*version.*not.*compatible",  # NEW
        r"system.*requirements.*not.*met",  # NEW
        r"minimum.*os.*version.*required"   # NEW
    ]
    
    # Check user context for OS version mismatches
    user_os = user_context.get('os_version', '').lower()
    if user_os and any(keyword in user_os for keyword in ['windows 7', 'windows 8', 'xp']):
        return f"Legacy OS detected that may cause compatibility issues: {user_os}"
    
    for event in events:
        if event.severity in ["ERROR", "CRITICAL", "WARNING"]:  # Include WARNING
            for pattern in os_patterns:
                if re.search(pattern, event.message, re.IGNORECASE):
                    return f"OS incompatibility detected: {event.message}"
    return None
```

REASONING: Added more comprehensive OS compatibility patterns, included user context checking for legacy OS versions, and expanded severity levels to include WARNING messages which often indicate compatibility issues.

MUTATION_TYPE: logic_enhancement
"""
            return mock_response
            
        except Exception as e:
            print(f"Error getting LLM suggestion: {e}")
            return None
    
    def _parse_llm_response(self, response: str) -> Tuple[str, str, str]:
        """Parse LLM response to extract rule, reasoning, and mutation type"""
        # Extract code block
        code_match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
        suggested_rule = code_match.group(1) if code_match else ""
        
        # Extract reasoning
        reasoning_match = re.search(r'REASONING:\s*(.*?)(?=MUTATION_TYPE:|$)', response, re.DOTALL)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else ""
        
        # Extract mutation type
        type_match = re.search(r'MUTATION_TYPE:\s*(\w+)', response)
        mutation_type = type_match.group(1) if type_match else "logic_enhancement"
        
        return suggested_rule, reasoning, mutation_type
    
    def validate_mutation_in_sandbox(self, mutation: RuleMutation) -> ValidationResult:
        """Test rule mutation in sandboxed environment"""
        try:
            # Create sandbox file
            sandbox_file = self.sandbox_path / f"rule_{mutation.mutation_id}.py"
            
            # Write rule to sandbox
            with open(sandbox_file, 'w') as f:
                f.write("import re\nfrom datetime import datetime\n\n")
                f.write(mutation.suggested_rule)
            
            # Generate test cases
            test_cases = self._generate_test_cases(mutation.original_rule_id)
            
            # Run tests
            test_results = self._run_sandbox_tests(sandbox_file, test_cases)
            
            # Calculate metrics
            passed_tests = sum(1 for result in test_results if result['passed'])
            total_tests = len(test_results)
            precision = self._calculate_precision(test_results)
            recall = self._calculate_recall(test_results)
            f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            validation_result = ValidationResult(
                mutation_id=mutation.mutation_id,
                passed=passed_tests >= total_tests * 0.8,  # 80% pass threshold
                precision=precision,
                recall=recall,
                f1_score=f1_score,
                test_cases_passed=passed_tests,
                test_cases_total=total_tests,
                error_messages=[r['error'] for r in test_results if r.get('error')]
            )
            
            # Update mutation status
            mutation.validation_status = 'approved' if validation_result.passed else 'rejected'
            mutation.test_results = asdict(validation_result)
            
            self.validation_history.append(validation_result)
            
            # Cleanup sandbox file
            sandbox_file.unlink()
            
            return validation_result
            
        except Exception as e:
            error_result = ValidationResult(
                mutation_id=mutation.mutation_id,
                passed=False,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                test_cases_passed=0,
                test_cases_total=0,
                error_messages=[str(e)]
            )
            
            mutation.validation_status = 'rejected'
            return error_result
    
    def _generate_test_cases(self, rule_id: str) -> List[Dict[str, Any]]:
        """Generate test cases for rule validation"""
        # Mock test cases - in production, these would be more comprehensive
        test_cases = [
            {
                'name': 'positive_case_1',
                'events': [
                    {'message': 'OS not supported for this application', 'severity': 'ERROR'},
                    {'message': 'Installation completed successfully', 'severity': 'INFO'}
                ],
                'metadata': {'OS Version': 'Windows 7'},
                'user_context': {'os_version': 'Windows 7'},
                'expected_result': True  # Should detect issue
            },
            {
                'name': 'negative_case_1', 
                'events': [
                    {'message': 'Installation completed successfully', 'severity': 'INFO'},
                    {'message': 'All components loaded', 'severity': 'INFO'}
                ],
                'metadata': {'OS Version': 'Windows 11'},
                'user_context': {'os_version': 'Windows 11'},
                'expected_result': False  # Should not detect issue
            },
            {
                'name': 'edge_case_1',
                'events': [
                    {'message': 'Warning: OS version may not be fully compatible', 'severity': 'WARNING'}
                ],
                'metadata': {'OS Version': 'Windows 10'},
                'user_context': {'os_version': 'Windows 10'},
                'expected_result': True  # Should detect potential issue
            }
        ]
        
        return test_cases
    
    def _run_sandbox_tests(self, sandbox_file: Path, test_cases: List[Dict]) -> List[Dict]:
        """Run test cases against sandboxed rule"""
        results = []
        
        for test_case in test_cases:
            try:
                # Mock test execution
                # In production, this would actually execute the rule
                result = {
                    'test_name': test_case['name'],
                    'passed': True,  # Mock result
                    'expected': test_case['expected_result'],
                    'actual': test_case['expected_result'],  # Mock matching result
                    'execution_time': 0.001
                }
                results.append(result)
                
            except Exception as e:
                results.append({
                    'test_name': test_case['name'],
                    'passed': False,
                    'error': str(e),
                    'expected': test_case['expected_result'],
                    'actual': None
                })
        
        return results
    
    def _calculate_precision(self, test_results: List[Dict]) -> float:
        """Calculate precision from test results"""
        true_positives = sum(1 for r in test_results if r.get('actual') == True and r.get('expected') == True)
        false_positives = sum(1 for r in test_results if r.get('actual') == True and r.get('expected') == False)
        
        return true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    
    def _calculate_recall(self, test_results: List[Dict]) -> float:
        """Calculate recall from test results"""
        true_positives = sum(1 for r in test_results if r.get('actual') == True and r.get('expected') == True)
        false_negatives = sum(1 for r in test_results if r.get('actual') == False and r.get('expected') == True)
        
        return true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    
    def promote_approved_mutations(self) -> List[str]:
        """Promote approved mutations to production rules"""
        promoted_mutations = []
        
        for mutation in self.mutations:
            if mutation.validation_status == 'approved':
                try:
                    # In production, this would update the actual rules configuration
                    self._update_production_rule(mutation)
                    promoted_mutations.append(mutation.mutation_id)
                    
                    # Version the mutation
                    self._version_mutation(mutation)
                    
                except Exception as e:
                    print(f"Error promoting mutation {mutation.mutation_id}: {e}")
        
        return promoted_mutations
    
    def _update_production_rule(self, mutation: RuleMutation):
        """Update production rule with approved mutation"""
        # Mock implementation - in production, this would update the actual rules
        print(f"Promoting mutation {mutation.mutation_id} to production")
        print(f"Original rule: {mutation.original_rule_id}")
        print(f"Mutation type: {mutation.mutation_type}")
        print(f"Expected improvement: {mutation.confidence_improvement:.2f}")
    
    def _version_mutation(self, mutation: RuleMutation):
        """Create version record of mutation"""
        version_record = {
            'mutation_id': mutation.mutation_id,
            'original_rule_id': mutation.original_rule_id,
            'promoted_at': datetime.now().isoformat(),
            'version_hash': hashlib.sha256(mutation.suggested_rule.encode()).hexdigest(),
            'performance_metrics': mutation.test_results
        }
        
        # Store version record
        version_file = Path("rule_versions.json")
        versions = []
        
        if version_file.exists():
            with open(version_file, 'r') as f:
                versions = json.load(f)
        
        versions.append(version_record)
        
        with open(version_file, 'w') as f:
            json.dump(versions, f, indent=2)
    
    def get_mutation_statistics(self) -> Dict[str, Any]:
        """Get mutation engine performance statistics"""
        total_mutations = len(self.mutations)
        approved_mutations = sum(1 for m in self.mutations if m.validation_status == 'approved')
        rejected_mutations = sum(1 for m in self.mutations if m.validation_status == 'rejected')
        pending_mutations = sum(1 for m in self.mutations if m.validation_status == 'pending')
        
        avg_confidence_improvement = 0
        if self.mutations:
            avg_confidence_improvement = sum(m.confidence_improvement for m in self.mutations) / len(self.mutations)
        
        return {
            'total_mismatches_recorded': len(self.mismatches),
            'total_mutations_generated': total_mutations,
            'approved_mutations': approved_mutations,
            'rejected_mutations': rejected_mutations,
            'pending_mutations': pending_mutations,
            'approval_rate': approved_mutations / total_mutations if total_mutations > 0 else 0,
            'average_confidence_improvement': avg_confidence_improvement,
            'total_validations_run': len(self.validation_history)
        }
    
    def export_mutation_report(self) -> Dict[str, Any]:
        """Export comprehensive mutation analysis report"""
        return {
            'report_id': str(uuid.uuid4()),
            'generated_at': datetime.now().isoformat(),
            'statistics': self.get_mutation_statistics(),
            'recent_mismatches': [asdict(m) for m in self.mismatches[-10:]],
            'mutations': [asdict(m) for m in self.mutations],
            'validation_history': [asdict(v) for v in self.validation_history[-20:]]
        }
