# modal_fixed.py - Fixed Modal deployment with proper configurations
import os, shlex, subprocess
import modal
from modal import FilePatternMatcher

APP_NAME = "logsense-streamlit"
APP_ENTRY = "skc_log_analyzer_minimal.py"  # Use minimal version for fast startup
PORT = 8000

# Build optimized image with proper requirements
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt")  # Use lightweight requirements
    .pip_install("fastapi[standard]>=0.100.0")
    .env({
        "STREAMLIT_WATCHER_TYPE": "none",
        "MODEL_BACKEND": "openai", 
        "DISABLE_ML_MODELS": "true",
        "PYTHONPATH": "/root/app",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false"
    })
    .workdir("/root/app")
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=image)

# Optimized configuration based on previous memory
OPTIMIZED_CONFIG = dict(
    timeout=300,           # Increased from 60s to handle heavy imports
    scaledown_window=600,  # Keep warm longer to prevent cold starts
    min_containers=1,      # Keep at least 1 container warm
    buffer_containers=0,   # No buffer during debugging
    memory=2048,          # Adequate memory for analysis
    cpu=2,                # Sufficient CPU
)

# Health check endpoint for debugging
@app.function(timeout=15)
@modal.fastapi_endpoint(label="health", docs=False)
def health():
    """Health check endpoint to verify Modal routing"""
    return {
        "status": "ok", 
        "service": "logsense-streamlit",
        "app_entry": APP_ENTRY,
        "timestamp": os.environ.get("MODAL_TASK_ID", "unknown")
    }

# Main UI endpoint with proper configuration
@app.function(**OPTIMIZED_CONFIG)
@modal.web_server(port=PORT, startup_timeout=300, label="run")  # Increased startup timeout
def run():
    """Streamlit server with subprocess approach for reliability"""
    print("[MODAL] Starting LogSense Streamlit app...", flush=True)
    print(f"[MODAL] App entry: {APP_ENTRY}", flush=True)
    print(f"[MODAL] Port: {PORT}", flush=True)
    
    # Set environment variables
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
    
    # Build streamlit command
    cmd = (
        f"streamlit run {shlex.quote(APP_ENTRY)} "
        f"--server.port {PORT} "
        f"--server.address 0.0.0.0 "
        f"--server.headless true "
        f"--server.enableCORS false "
        f"--server.enableXsrfProtection false "
        f"--server.fileWatcherType none "
        f"--browser.gatherUsageStats false"
    )
    
    print(f"[MODAL] Command: {cmd}", flush=True)
    
    # Use subprocess.Popen for non-blocking execution with safer argument parsing
    import shlex
    cmd_args = shlex.split(cmd) if isinstance(cmd, str) else cmd
    process = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Log initial output to verify startup
    try:
        for line in process.stdout:
            print(f"[STREAMLIT] {line.strip()}", flush=True)
            if "Network URL:" in line or "External URL:" in line:
                print("[MODAL] Streamlit server started successfully!", flush=True)
                break
    except Exception as e:
        print(f"[MODAL] Error reading Streamlit output: {e}", flush=True)

# Test endpoint for basic functionality
@app.function(timeout=30)
@modal.fastapi_endpoint(label="test", docs=False)
def test():
    """Test endpoint to verify basic functionality"""
    try:
        import streamlit
        import pandas
        import numpy
        return {
            "status": "ok",
            "streamlit_version": streamlit.__version__,
            "pandas_version": pandas.__version__,
            "numpy_version": numpy.__version__,
            "app_entry_exists": os.path.exists(APP_ENTRY)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
