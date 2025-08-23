# Working LogSense - No problematic imports
import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

import streamlit as st
from datetime import datetime
import tempfile
import hashlib

# Streamlit app starts immediately - no heavy imports
st.set_page_config(
    page_title="LogSense - AI Log Analysis",
    page_icon="[SEARCH]",
    layout="wide"
)

st.title("[SEARCH] LogSense - AI Log Analysis")
st.write("**Working version - no problematic imports**")

# Show startup time
if 'startup_time' not in st.session_state:
    st.session_state.startup_time = datetime.now()
    
startup_duration = (datetime.now() - st.session_state.startup_time).total_seconds()
st.success(f"[OK] App loaded in {startup_duration:.2f} seconds")

# Simple file upload without heavy processing
uploaded_file = st.file_uploader("Upload log file", type=['txt', 'log', 'zip'])

if uploaded_file:
    st.success("[OK] File uploaded successfully!")
    
    # Basic file info without heavy processing
    st.write(f"**File**: {uploaded_file.name}")
    st.write(f"**Size**: {len(uploaded_file.getvalue())} bytes")
    
    # Show first few lines of file
    if uploaded_file.type == "text/plain":
        content = uploaded_file.getvalue().decode('utf-8')
        lines = content.split('\n')[:10]
        st.text_area("First 10 lines:", '\n'.join(lines), height=200)
    
    if st.button("Analyze Log"):
        with st.spinner("Analyzing..."):
            # Simulate analysis without heavy imports
            import time
            time.sleep(2)
            
        st.success("[OK] Analysis complete!")
        st.write("**Sample Analysis Results:**")
        st.write("- Total lines: ", len(content.split('\n')) if uploaded_file.type == "text/plain" else "Unknown")
        st.write("- File type: ", uploaded_file.type)
        st.write("- Status: Ready for processing")

st.info("[U+1F4A1] This version works without heavy ML imports - ready for enhancement")