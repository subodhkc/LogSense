"""
Baseline Analyzer - Provides a stable, JSON-serializable interface to the advanced analytics engine.
"""

from typing import List, Dict, Any
from .advanced_analytics import AdvancedAnalyticsEngine

# Initialize the engine once to be reused
engine = AdvancedAnalyticsEngine()

def analyze_events(events: List[Any]) -> Dict[str, Any]:
    """ 
    Analyzes events using the advanced analytics engine and returns a serializable dictionary.
    """
    if not engine.initialized:
        return {"error": "Advanced analytics engine not initialized"}

    # Run the comprehensive analysis
    analysis_results = engine.run_comprehensive_analysis(events)

    # Convert the results to a serializable format
    serializable_results = {
        'total_events': analysis_results.get('total_events', 0),
        'analysis_timestamp': analysis_results.get('analysis_timestamp'),
        'key_insights': analysis_results.get('key_insights', []),        
        'root_cause_ranking': analysis_results.get('root_cause_ranking', []),
        'error_spikes': analysis_results.get('error_spikes', []),
        'frequent_sequences': analysis_results.get('frequent_sequences', []),
        'component_correlations': analysis_results.get('component_correlations', []),
        'dependency_analysis': analysis_results.get('dependency_analysis', {}),
        'entropy_analysis': analysis_results.get('entropy_analysis', {}),
    }

    return serializable_results
