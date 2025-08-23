# test_minimal.py - Minimal test to isolate Streamlit startup issues
import streamlit as st
import os

# Set environment variables
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
os.environ["MODEL_BACKEND"] = "openai"
os.environ["DISABLE_ML_MODELS"] = "true"

st.title("LogSense Test - Minimal")
st.write("If you see this, Streamlit is working!")
st.write(f"Python path: {os.environ.get('PYTHONPATH', 'Not set')}")
st.write(f"Current directory: {os.getcwd()}")

# Test basic imports
try:
    import pandas as pd
    st.success("[OK] pandas imported successfully")
except Exception as e:
    st.error(f"[X] pandas import failed: {e}")

try:
    import numpy as np
    st.success("[OK] numpy imported successfully")
except Exception as e:
    st.error(f"[X] numpy import failed: {e}")

try:
    import matplotlib.pyplot as plt
    st.success("[OK] matplotlib imported successfully")
except Exception as e:
    st.error(f"[X] matplotlib import failed: {e}")

# Test file system access
import os
files = os.listdir('.')
st.write(f"Files in current directory: {len(files)}")
st.write("Sample files:", files[:10])