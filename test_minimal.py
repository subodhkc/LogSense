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
    st.success("✅ pandas imported successfully")
except Exception as e:
    st.error(f"❌ pandas import failed: {e}")

try:
    import numpy as np
    st.success("✅ numpy imported successfully")
except Exception as e:
    st.error(f"❌ numpy import failed: {e}")

try:
    import matplotlib.pyplot as plt
    st.success("✅ matplotlib imported successfully")
except Exception as e:
    st.error(f"❌ matplotlib import failed: {e}")

# Test file system access
import os
files = os.listdir('.')
st.write(f"Files in current directory: {len(files)}")
st.write("Sample files:", files[:10])
