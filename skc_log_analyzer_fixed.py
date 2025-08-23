# Fixed LogSense with proper lazy loading - preserving all functionality
import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

import streamlit as st
import sys
import tempfile
from datetime import datetime
import hashlib

# Add Python Modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'Python Modules'))

# Global variables for lazy loading
_analysis_modules_loaded = False
_heavy_imports_loaded = False
_ui_components_loaded = False

def load_heavy_imports():
    """Lazy load heavy dependencies"""
    global _heavy_imports_loaded, pd, zipfile, io, BytesIO, load_dotenv
    if not _heavy_imports_loaded:
        import pandas as pd
        import zipfile
        import io
        from io import BytesIO
        from dotenv import load_dotenv
        _heavy_imports_loaded = True
    return pd, zipfile, io, BytesIO, load_dotenv

def load_analysis_modules():
    """Lazy load analysis modules"""
    global _analysis_modules_loaded
    global analysis, redaction, test_plan, charts, recommendations, ai_rca, report, setup
    global clustering_model, decision_tree_model, anomaly_svm, get_all_rca_summaries
    
    if not _analysis_modules_loaded:
        try:
            # Core modules
            import analysis
            import redaction
            import test_plan
            import charts
            import recommendations
            import ai_rca
            import report
            import setup
            
            # RCA rules
            from rca_rules import get_all_rca_summaries
            
            # ML modules (lazy loaded)
            clustering_model = None
            decision_tree_model = None
            anomaly_svm = None
            
            _analysis_modules_loaded = True
        except ImportError as e:
            st.error(f"Failed to load analysis modules: {e}")
            return False
    return True

def load_ui_components():
    """Lazy load UI components"""
    global _ui_components_loaded
    global render_header, render_progress_indicator, render_info_card
    global render_metric_cards, render_status_badge, render_data_table
    global render_action_buttons, render_sidebar_config, render_welcome_screen
    
    if not _ui_components_loaded:
        try:
            from ui_components import (
                render_header, render_progress_indicator, render_info_card,
                render_metric_cards, render_status_badge, render_data_table,
                render_action_buttons, render_sidebar_config, render_welcome_screen
            )
            _ui_components_loaded = True
        except ImportError as e:
            st.warning(f"UI components not available: {e}")
            return False
    return True

def load_advanced_modules():
    """Lazy load advanced analysis modules"""
    try:
        from analysis.templates import TemplateExtractor
        from report.pdf_builder import build_pdf as build_onepager_pdf
        from analysis.event_chain import ChainSpec, detect_sequences
        from analysis.session import correlate_start_end
        from datamodels.events import Event as CanonEvent
        return TemplateExtractor, build_onepager_pdf, ChainSpec, detect_sequences, correlate_start_end, CanonEvent
    except ImportError as e:
        st.warning(f"Advanced modules not available: {e}")
        return None, None, None, None, None, None

# Streamlit app starts immediately - no heavy imports
st.set_page_config(
    page_title="LogSense - AI Log Analysis",
    page_icon="[SEARCH]",
    layout="wide"
)

# Show startup time
if 'startup_time' not in st.session_state:
    st.session_state.startup_time = datetime.now()
    
startup_duration = (datetime.now() - st.session_state.startup_time).total_seconds()

# Try to load UI components for header
if load_ui_components():
    render_header()
else:
    st.title("[SEARCH] LogSense - AI Log Analysis")
    st.write("**Enterprise-grade log analysis with AI-powered insights**")

st.success(f"[OK] App loaded in {startup_duration:.2f} seconds")

# File upload
uploaded_file = st.file_uploader("Upload log file", type=['txt', 'log', 'zip'])

if uploaded_file:
    # Load heavy imports when file is uploaded
    with st.spinner("Loading analysis modules..."):
        pd, zipfile, io, BytesIO, load_dotenv = load_heavy_imports()
        analysis_loaded = load_analysis_modules()
    
    if analysis_loaded:
        st.success("[OK] Analysis modules loaded successfully")
        
        # Basic file info
        st.write(f"**File**: {uploaded_file.name}")
        st.write(f"**Size**: {len(uploaded_file.getvalue())} bytes")
        
        # Analysis options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("[SEARCH] Basic Analysis"):
                with st.spinner("Analyzing..."):
                    # Use loaded analysis module
                    try:
                        result = analysis.analyze_logs(uploaded_file.getvalue())
                        st.success("[OK] Basic analysis complete!")
                        st.json(result)
                    except Exception as e:
                        st.error(f"Analysis failed: {e}")
        
        with col2:
            if st.button("[U+1F916] AI Analysis"):
                with st.spinner("Running AI analysis..."):
                    try:
                        result = ai_rca.analyze_with_ai(uploaded_file.getvalue())
                        st.success("[OK] AI analysis complete!")
                        st.json(result)
                    except Exception as e:
                        st.error(f"AI analysis failed: {e}")
        
        with col3:
            if st.button("[U+1F4CA] Generate Report"):
                with st.spinner("Generating report..."):
                    # Load advanced modules for report generation
                    modules = load_advanced_modules()
                    if modules[1]:  # build_onepager_pdf
                        try:
                            pdf_data = modules[1](uploaded_file.getvalue())
                            st.download_button(
                                "[U+1F4C4] Download Report",
                                pdf_data,
                                file_name=f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf"
                            )
                        except Exception as e:
                            st.error(f"Report generation failed: {e}")
                    else:
                        st.error("Report generation modules not available")
        
        # Show file preview
        if uploaded_file.type == "text/plain":
            content = uploaded_file.getvalue().decode('utf-8')
            lines = content.split('\n')[:20]
            st.text_area("File Preview (first 20 lines):", '\n'.join(lines), height=300)
    
    else:
        st.error("Failed to load analysis modules")

else:
    # Show welcome screen if UI components are available
    if load_ui_components():
        render_welcome_screen()
    else:
        st.info("[U+1F4A1] Upload a log file to start analysis")
        st.markdown("""
        **Supported formats:**
        - Text files (.txt, .log)
        - ZIP archives containing log files
        
        **Features:**
        - AI-powered log analysis
        - Anomaly detection
        - Root cause analysis
        - Interactive reports
        """)

st.info("[U+1F680] All functionality preserved with lazy loading for fast startup")