# serve_streamlit.py
import shlex, subprocess
from pathlib import Path
import os, time
import modal

APP_ENTRY_REMOTE = "/root/app/skc_log_analyzer.py"
PORT = 8000

# Build minimal image and pre-bake deps to avoid cold-start pip installs
# IMPORTANT: add_local_dir must be applied LAST per Modal guidance.
base_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt")
    # Prebake environment setup to reduce cold start
    .env({"STREAMLIT_WATCHER_TYPE": "none", 
          "MODEL_BACKEND": "openai",
          "DISABLE_ML_MODELS": "true",
          "PYTHONPATH": "/root/app"})
    .workdir("/root/app")
    # Pre-warm Streamlit installation
    .run_commands("python -c 'import streamlit; print(\"Streamlit prebaked\")'")
)

# Optional cache-buster to force a rebuild ONLY when explicitly requested.
# Set MODAL_FORCE_REBUILD=1 in your environment before running serve/deploy.
if os.getenv("MODAL_FORCE_REBUILD") == "1":
    # Add a no-op layer with a timestamp to invalidate cache economically
    base_image = base_image.run_commands(f"bash -lc 'echo BUILD_TS={int(time.time())}'")

# Now add local source directory LAST to avoid rebuilds on every change
image = base_image.add_local_dir(".", remote_path="/root/app")

app = modal.App(name="logsense-streamlit", image=image)

# ECONOMIC GUARDRAILS (debug mode)
ECON = dict(
    timeout=60,  # keep request bound short while debugging
    scaledown_window=2,  # kill idle containers quickly
    min_containers=0,    # don't keep warm containers in tests
    buffer_containers=0, # no prebuffering
)

@app.function(**ECON)
@modal.web_server(port=PORT, startup_timeout=60)
def run():
    import time
    import sys
    
    print("🚀 Modal web server starting...", flush=True)
    
    # Start Streamlit bound to external iface and to the SAME port as web_server
    cmd = (
        f"streamlit run {shlex.quote(APP_ENTRY_REMOTE)} "
        f"--server.port {PORT} "
        f"--server.address 0.0.0.0 "
        f"--server.headless true "
        f"--server.enableCORS false "
        f"--server.enableXsrfProtection false"
    )
    
    print(f"📡 Starting Streamlit: {cmd}", flush=True)
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    # Give Streamlit time to start
    print("⏳ Waiting 5s for Streamlit boot...", flush=True)
    time.sleep(5)
    
    print("✅ Modal web server ready - Streamlit should be accessible", flush=True)
    
    # Keep function alive
    process.wait()
