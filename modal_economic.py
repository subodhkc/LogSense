# modal_economic.py — known-good Streamlit launcher for Modal
import os, shlex, subprocess
import modal
from modal import FilePatternMatcher

APP_NAME = "logsense-streamlit"
APP_ENTRY = "/root/app/skc_log_analyzer_minimal.py"
PORT = 8000

# Build a lean image and pre-bake deps. Exclude heavy stuff to cut cold-starts.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt")
    .pip_install("fastapi[standard]>=0.100.0")
    .add_local_dir(".", remote_path="/root/app")
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
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    # optional stability knobs:
    os.environ["STREAMLIT_SERVER_RUN_ON_SAVE"] = "false"
    os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

    cmd = (
        f"streamlit run {shlex.quote(APP_ENTRY)} "
        f"--server.port {PORT} "
        f"--server.address 0.0.0.0 "
        f"--server.headless true "
        f"--server.enableCORS false "
        f"--server.enableXsrfProtection false"
    )
    proc = subprocess.Popen(cmd, shell=True)
    proc.wait()  # <— CRITICAL: ties container lifecycle to the Streamlit process
