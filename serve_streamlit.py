# serve_streamlit.py
import shlex, subprocess
from pathlib import Path
import os, time, signal
import socket, threading
import requests
import psutil
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
    memory=2048,          # allocate 2GB RAM to prevent OOM
    cpu=2,                # allocate 2 CPU cores for better performance
)

@app.function(**ECON)
@modal.web_server(port=PORT, startup_timeout=300)
def run():
    import time
    import sys
    
    print("[MODAL] Web server starting...", flush=True)
    
    # Global process reference for signal handling
    streamlit_process = None
    
    def signal_handler(signum, frame):
        print(f"[SIGNAL] Received signal {signum}, forwarding to Streamlit...", flush=True)
        if streamlit_process and streamlit_process.poll() is None:
            streamlit_process.terminate()
            try:
                streamlit_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                streamlit_process.kill()
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
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
    streamlit_process = process  # Store for signal handling

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

    # Memory watchdog thread
    def _memory_watchdog():
        try:
            parent_pid = os.getpid()
            while True:
                try:
                    parent_proc = psutil.Process(parent_pid)
                    parent_rss = parent_proc.memory_info().rss / 1024 / 1024  # MB
                    
                    streamlit_rss = 0
                    if streamlit_process and streamlit_process.poll() is None:
                        try:
                            streamlit_proc = psutil.Process(streamlit_process.pid)
                            streamlit_rss = streamlit_proc.memory_info().rss / 1024 / 1024  # MB
                        except psutil.NoSuchProcess:
                            pass
                    
                    print(f"[MEM] Parent: {parent_rss:.1f}MB, Streamlit: {streamlit_rss:.1f}MB", flush=True)
                    time.sleep(5)
                except Exception as e:
                    print(f"[MEM] Watchdog error: {e}", flush=True)
                    time.sleep(10)
        except Exception:
            pass

    threading.Thread(target=_memory_watchdog, daemon=True).start()

    # Wait for HTTP health readiness on Streamlit's health endpoint
    start = time.time()
    deadline = start + 300  # seconds
    print("[WAIT] Probing for HTTP health on 127.0.0.1:{port}/_stcore/health...".format(port=PORT), flush=True)
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
            response = requests.get(f"http://127.0.0.1:{PORT}/_stcore/health", timeout=1)
            if response.status_code == 200 and "ok" in response.text.lower():
                ready = True
                break
        except Exception:
            pass
        time.sleep(0.5)

    if not ready:
        print("[WARN] Health endpoint did not respond within timeout; continuing to wait for process.", flush=True)
    else:
        print("[SUCCESS] Streamlit health check passed; web server ready.", flush=True)

    # Keep function alive while Streamlit runs
    process.wait()
