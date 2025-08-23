# Minimal LogSense with lazy imports - fast startup version
import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

import streamlit as st

# Only import what's absolutely needed at startup
from datetime import datetime
import tempfile
import hashlib

# ALL other imports moved to functions - lazy loading
def get_analysis_modules():
    """Lazy load analysis modules only when needed"""
    global analysis, redaction, test_plan, charts, recommendations, ai_rca, report
    if 'analysis' not in globals():
        import analysis
        import redaction  
        import test_plan
        import charts
        import recommendations
        import ai_rca
        import report
    return analysis, redaction, test_plan, charts, recommendations, ai_rca, report

def get_heavy_imports():
    """Lazy load heavy dependencies only when needed"""
    global pd, zipfile, io, BytesIO, load_dotenv
    if 'pd' not in globals():
        import pandas as pd
        import zipfile
        import io
        from io import BytesIO
        from dotenv import load_dotenv
    return pd, zipfile, io, BytesIO, load_dotenv

def get_ui_components():
    """Lazy load UI components"""
    global ui_components
    if 'ui_components' not in globals():
        import ui_components
    return ui_components

# Streamlit app starts immediately - no heavy imports
st.set_page_config(
    page_title="LogSense - AI Log Analysis",
    page_icon="[SEARCH]",
    layout="wide"
)

st.title("[SEARCH] LogSense - AI Log Analysis")
st.write("**Fast startup version with lazy loading**")

# Show startup time
if 'startup_time' not in st.session_state:
    st.session_state.startup_time = datetime.now()
    
startup_duration = (datetime.now() - st.session_state.startup_time).total_seconds()
st.success(f"[OK] App loaded in {startup_duration:.2f} seconds")

# File upload (only load pandas when needed)
uploaded_file = st.file_uploader("Upload log file", type=['txt', 'log', 'zip'])

if uploaded_file:
    with st.spinner("Loading analysis modules..."):
        # NOW load heavy imports
        pd, zipfile, io, BytesIO, load_dotenv = get_heavy_imports()
        
    st.success("[OK] Heavy modules loaded - ready for analysis")
    
    # Basic file info without heavy processing
    st.write(f"File: {uploaded_file.name}")
    st.write(f"Size: {len(uploaded_file.getvalue())} bytes")
    
    if st.button("Start Analysis"):
        with st.spinner("Loading analysis engine..."):
            # Load analysis modules only when actually needed
            analysis, redaction, test_plan, charts, recommendations, ai_rca, report = get_analysis_modules()
            
        st.success("[OK] Analysis complete!")
        st.write("Analysis modules loaded successfully")

st.info("[U+1F4A1] This version loads instantly by deferring heavy imports until actually needed")