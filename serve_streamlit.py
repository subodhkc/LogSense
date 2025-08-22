# serve_streamlit.py
import shlex, subprocess
from pathlib import Path
import os, time
import modal

APP_ENTRY_REMOTE = "/root/app/skc_log_analyzer.py"
PORT = 8000

# Build minimal image and pre-bake deps to avoid cold-start pip installs
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .add_local_dir(".", remote_path="/root/app")
)

# Optional cache-buster to force a rebuild ONLY when explicitly requested.
# Set MODAL_FORCE_REBUILD=1 in your environment before running serve/deploy.
if os.getenv("MODAL_FORCE_REBUILD") == "1":
    # Add a no-op layer with a timestamp to invalidate cache economically
    image = image.run_commands(f"bash -lc 'echo BUILD_TS={int(time.time())}'")

app = modal.App(name="logsense-streamlit", image=image)

# ECONOMIC GUARDRAILS (debug mode)
ECON = dict(
    timeout=60,  # keep request bound short while debugging
    retries=modal.Retries(max_retries=0),  # no multiplied charges on failure
    scaledown_window=2,  # kill idle containers quickly
    min_containers=0,    # don't keep warm containers in tests
    buffer_containers=0, # no prebuffering
)

@app.function(**ECON)
@modal.web_server(port=PORT, startup_timeout=60)
def run():
    import time
    
    # Start Streamlit bound to external iface and to the SAME port as web_server
    cmd = (
        f"streamlit run {shlex.quote(APP_ENTRY_REMOTE)} "
        f"--server.port {PORT} "
        f"--server.address 0.0.0.0 "
        f"--server.headless true "
        f"--server.enableCORS false "
        f"--server.enableXsrfProtection false"
    )
    
    process = subprocess.Popen(cmd, shell=True)
    
    # Give Streamlit time to start
    time.sleep(5)
    
    # Keep function alive
    process.wait()
