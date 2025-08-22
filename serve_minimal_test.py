# serve_minimal_test.py - Test minimal Streamlit deployment
import modal
import subprocess
import os

PORT = 8000

# Minimal test image
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("streamlit>=1.28.0", "pandas>=1.5.0", "numpy>=1.24.0", "matplotlib>=3.6.0")
    .env({
        "STREAMLIT_WATCHER_TYPE": "none", 
        "MODEL_BACKEND": "openai",
        "DISABLE_ML_MODELS": "true",
        "PYTHONPATH": "/root/app"
    })
    .workdir("/root/app")
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name="logsense-test", image=image)

@app.function(
    memory=1024,
    cpu=1,
    timeout=300,
)
@modal.web_server(port=PORT, startup_timeout=60)
def run():
    """Test minimal Streamlit server"""
    
    print("[TEST] Starting minimal Streamlit test...", flush=True)
    
    # Use the test file instead of main app
    subprocess.run([
        "streamlit", "run", "test_minimal.py",
        "--server.port", str(PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--server.fileWatcherType", "none",
        "--browser.gatherUsageStats", "false"
    ])
