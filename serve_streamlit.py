# serve_streamlit.py - Minimal working Modal deployment
import modal
import subprocess
import os

APP_ENTRY_REMOTE = "skc_log_analyzer_minimal.py"
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
    timeout=900,           # Increased from 300s to 900s (15 minutes)
    min_containers=1,
    scaledown_window=600,  # Keep warm longer during debugging
)
@modal.web_server(port=PORT, startup_timeout=600)  # Increased startup timeout to 10 minutes
def run():
    """Background subprocess Streamlit server - prevents SystemExit"""
    import subprocess
    import os
    
    print("[MODAL] Starting Streamlit via subprocess...", flush=True)
    
    # Set environment variables
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
    
    # Build command with explicit binding
    cmd = [
        "streamlit", "run", APP_ENTRY_REMOTE,
        "--server.port", str(PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false", 
        "--server.enableXsrfProtection", "false",
        "--server.fileWatcherType", "none",
        "--browser.gatherUsageStats", "false"
    ]
    
    print(f"[MODAL] Command: {' '.join(cmd)}", flush=True)
    
    # Start subprocess and keep it running
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Monitor startup and log output
    startup_complete = False
    for line in iter(process.stdout.readline, ''):
        print(f"[STREAMLIT] {line.strip()}", flush=True)
        
        # Check for successful startup indicators
        if any(indicator in line for indicator in [
            "Network URL:", "External URL:", "Local URL:", 
            "You can now view your Streamlit app"
        ]):
            startup_complete = True
            print("[MODAL] Streamlit server startup confirmed!", flush=True)
            break
            
        # Check for errors
        if "error" in line.lower() or "failed" in line.lower():
            print(f"[MODAL] Potential error detected: {line.strip()}", flush=True)
    
    # Keep the process alive
    if startup_complete:
        print("[MODAL] Streamlit running, keeping process alive...", flush=True)
        process.wait()  # Keep container alive
    else:
        print("[MODAL] Startup may not have completed, but keeping process alive...", flush=True)
        process.wait()

# Health check endpoint for debugging
@app.function(timeout=15)
@modal.fastapi_endpoint(label="health")
def health():
    """Health check endpoint to verify Modal routing"""
    return {"status": "ok", "service": "logsense-streamlit"}
