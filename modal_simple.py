# modal_simple.py - Simple HTTP server approach
import modal
import os

APP_NAME = "logsense-simple"

# Build image with streamlit
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt")
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=image)

@app.function(timeout=24*60*60)
@modal.web_server(port=8000, startup_timeout=600)
def run():
    os.chdir("/root/app")
    
    # Direct exec - no subprocess
    os.system("streamlit run skc_log_analyzer_minimal.py --server.port 8000 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false")
