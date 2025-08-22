# serve_streamlit.py
import shlex, subprocess
from pathlib import Path
import os, time
import socket, threading
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
    timeout=300,          # generous to cover slow Streamlit startup
    scaledown_window=600, # keep container warm longer during testing
    min_containers=1,     # ensure at least one warm container
    buffer_containers=0,  # no prebuffering
)

@app.function(**ECON)
@modal.web_server(port=PORT, startup_timeout=300)
def run():
    import time
    import sys
    
    print("[MODAL] Web server starting...", flush=True)
    
    # Start Streamlit bound to external iface and to the SAME port as web_server
    cmd = (
        f"streamlit run {shlex.quote(APP_ENTRY_REMOTE)} "
        f"--server.port {PORT} "
        f"--server.address 0.0.0.0 "
        f"--server.headless true "
        f"--server.enableCORS false "
        f"--server.enableXsrfProtection false"
    )
    
    print(f"[STREAMLIT] Starting: {cmd}", flush=True)
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Stream logs from Streamlit in a background thread for visibility
    def _pump_logs(proc: subprocess.Popen):
        try:
            assert proc.stdout is not None
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                print(f"[STREAMLIT] {line.rstrip()}", flush=True)
        except Exception as e:
            print(f"[LOG] Log pump error: {e}", flush=True)

    threading.Thread(target=_pump_logs, args=(process,), daemon=True).start()

    # Wait for TCP readiness on the bound port, with overall timeout
    start = time.time()
    deadline = start + 300  # seconds
    print("[WAIT] Probing for port readiness on 127.0.0.1:{port}...".format(port=PORT), flush=True)
    ready = False
    while time.time() < deadline:
        # If process died, surface the error
        rc = process.poll()
        if rc is not None:
            print(f"[ERROR] Streamlit exited with code {rc} before readiness", flush=True)
            # Drain remaining output
            try:
                out, _ = process.communicate(timeout=2)
                if out:
                    print(out, flush=True)
            except Exception:
                pass
            return
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
                ready = True
                break
        except OSError:
            time.sleep(0.5)

    if not ready:
        print("[WARN] Port did not open within timeout; continuing to wait for process.", flush=True)
    else:
        print("[SUCCESS] Streamlit is listening; web server ready.", flush=True)

    # Keep function alive while Streamlit runs
    process.wait()
