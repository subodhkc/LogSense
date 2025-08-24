# modal_economic.py - known-good Streamlit launcher for Modal
import os, shlex, subprocess, threading
import modal
from modal import FilePatternMatcher

APP_NAME = "logsense-streamlit"
APP_ENTRY = "skc_log_analyzer_minimal.py"
PORT = 8000

# Build a lean image and pre-bake deps. Exclude heavy stuff to cut cold-starts.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .add_local_dir(".", remote_path="/root/app")
    .pip_install_from_requirements("/root/app/requirements-modal.txt")
)

app = modal.App(name=APP_NAME, image=image)

# ECON for web server: long timeout, slower scaledown for stability
WEB_ECON = dict(
    timeout=24 * 60 * 60,                     # 24h: web servers should not time out
    scaledown_window=120,                     # allow container to stay up between hits
    min_containers=0,
    buffer_containers=0,
)

# Optional: quick JSON canary to verify URL/label wiring
@app.function(timeout=15)
@modal.fastapi_endpoint(label="health", docs=False)
def health():
    return {"ok": True}

# The UI endpoint with proper lifecycle management
@app.function(**WEB_ECON)
@modal.web_server(port=PORT, startup_timeout=300, label="run")
def run():
    import os
    import sys
    import subprocess
    import time
    
    # Change to the app directory where files are mounted
    os.chdir("/root/app")
    
    print(f"[MODAL] Python version: {sys.version}", flush=True)
    print(f"[MODAL] Working directory: {os.getcwd()}", flush=True)
    print(f"[MODAL] Files in directory: {os.listdir('.')}", flush=True)
    print(f"[MODAL] APP_ENTRY: {APP_ENTRY}", flush=True)
    print(f"[MODAL] APP_ENTRY exists: {os.path.exists(APP_ENTRY)}", flush=True)
    
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
    os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

    # Test basic imports first
    try:
        import streamlit
        print(f"[MODAL] Streamlit version: {streamlit.__version__}", flush=True)
    except Exception as e:
        print(f"[MODAL] ERROR: Cannot import streamlit: {e}", flush=True)
        return

    # Test if entry file can be imported
    try:
        print(f"[MODAL] Testing import of {APP_ENTRY}...", flush=True)
        # Don't actually import, just check syntax
        with open(APP_ENTRY, 'r') as f:
            content = f.read()
            compile(content, APP_ENTRY, 'exec')
        print(f"[MODAL] {APP_ENTRY} syntax check passed", flush=True)
    except Exception as e:
        print(f"[MODAL] ERROR: {APP_ENTRY} has issues: {e}", flush=True)
        return

    cmd = [
        "streamlit", "run", APP_ENTRY,
        "--server.port", str(PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false"
    ]
    
    print(f"[MODAL] Starting command: {' '.join(cmd)}", flush=True)
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        print(f"[MODAL] Process started with PID: {proc.pid}", flush=True)

        # Stream stdout/stderr in real time so Modal logs show Streamlit output
        def _reader(pipe, prefix):
            try:
                for line in iter(pipe.readline, ''):
                    if not line:
                        break
                    print(f"[MODAL][{prefix}] {line.rstrip()}", flush=True)
            except Exception as e:
                print(f"[MODAL] Reader error ({prefix}): {e}", flush=True)

        t_out = threading.Thread(target=_reader, args=(proc.stdout, "STDOUT"), daemon=True)
        t_err = threading.Thread(target=_reader, args=(proc.stderr, "STDERR"), daemon=True)
        t_out.start(); t_err.start()

        # Wait for Streamlit to be ready by checking if port is accepting connections
        import socket
        start_time = time.time()
        streamlit_ready = False
        
        while time.time() - start_time < 120:  # Wait up to 2 minutes
            if proc.poll() is not None:
                print(f"[MODAL] Process exited early with code: {proc.returncode}", flush=True)
                return
                
            # Check if Streamlit is accepting connections
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', PORT))
                sock.close()
                if result == 0:
                    print(f"[MODAL] Streamlit is accepting connections after {int(time.time() - start_time)}s", flush=True)
                    streamlit_ready = True
                    break
            except:
                pass
                
            time.sleep(2)
            print(f"[MODAL] Waiting for Streamlit to accept connections... {int(time.time() - start_time)}s", flush=True)

        if not streamlit_ready:
            print(f"[MODAL] ERROR: Streamlit failed to accept connections after {int(time.time() - start_time)}s", flush=True)
            proc.terminate()
            return

        print(f"[MODAL] Streamlit is ready and accepting connections!", flush=True)
        proc.wait()

    except Exception as e:
        print(f"[MODAL] ERROR starting subprocess: {e}", flush=True)
        return
