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
)
@modal.web_server(port=PORT, startup_timeout=120)
def run():
    """Simple Streamlit server - no complex subprocess management"""
    
    print("[MODAL] Starting Streamlit server...", flush=True)
    
    # Use subprocess.run() - blocks until Streamlit exits
    subprocess.run([
        "streamlit", "run", APP_ENTRY_REMOTE,
        "--server.port", str(PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false",
        "--server.fileWatcherType", "none",
        "--browser.gatherUsageStats", "false"
    ])
