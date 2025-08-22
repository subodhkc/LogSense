# serve_streamlit.py - Minimal working Modal deployment
import modal
import subprocess
import os

APP_ENTRY_REMOTE = "/root/app/skc_log_analyzer.py"
PORT = 8000

# Minimal image build
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt")
    .env({
        "STREAMLIT_WATCHER_TYPE": "none", 
        "MODEL_BACKEND": "openai",
        "DISABLE_ML_MODELS": "true",
        "PYTHONPATH": "/root/app"
    })
    .workdir("/root/app")
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name="logsense-streamlit", image=image)

@app.function(
    memory=2048,
    cpu=2,
    timeout=300,
    min_containers=1,
    scaledown_window=600,  # Keep warm longer during debugging
)
@modal.web_server(port=PORT, startup_timeout=60)  # Reduced timeout to fail fast
def run():
    """Direct Streamlit server - no subprocess"""
    import streamlit.web.cli as stcli
    import sys
    
    print("[MODAL] Starting Streamlit directly...", flush=True)
    
    # Set Streamlit args directly
    sys.argv = [
        "streamlit",
        "run",
        "test_streamlit_basic.py",
        "--server.port", str(PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--server.fileWatcherType", "none",
        "--browser.gatherUsageStats", "false"
    ]
    
    print(f"[MODAL] Streamlit args: {sys.argv}", flush=True)
    
    # Run Streamlit directly
    try:
        stcli.main()
    except SystemExit as e:
        print(f"[MODAL] Streamlit exited with: {e}", flush=True)
        if e.code != 0:
            raise

# Health check endpoint for debugging
@app.function(timeout=15)
@modal.fastapi_endpoint(label="health")
def health():
    """Health check endpoint to verify Modal routing"""
    return {"status": "ok", "service": "logsense-streamlit"}
