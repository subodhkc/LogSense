# modal_economic.py — known-good Streamlit launcher for Modal
import os, shlex, subprocess
import modal
from modal import FilePatternMatcher

APP_NAME = "logsense-streamlit"
APP_ENTRY = "/root/app/skc_log_analyzer.py"
PORT = 8000

# Build a lean image and pre-bake deps. Exclude heavy stuff to cut cold-starts.
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements.txt")
    .pip_install("fastapi[standard]>=0.100.0")
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=image)

# Cost controls while debugging
ECON = dict(
    timeout=60,
    scaledown_window=10,    # make first green run reliable; later drop to 2–5
    min_containers=0,
    buffer_containers=0,
)

# Optional: quick JSON canary to verify URL/label wiring
@app.function(timeout=15)
@modal.fastapi_endpoint(label="health", docs=False)
def health():
    return {"ok": True}

# The UI endpoint. IMPORTANT: do NOT call stcli.main(); spawn a background process.
@app.function(**ECON)
@modal.web_server(port=PORT, startup_timeout=180, label="run")
def run():
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    cmd = (
        f"streamlit run {shlex.quote(APP_ENTRY)} "
        f"--server.port {PORT} "
        f"--server.address 0.0.0.0 "
        f"--server.headless true "
        f"--server.enableCORS false "
        f"--server.enableXsrfProtection false"
    )
    subprocess.Popen(cmd, shell=True)
