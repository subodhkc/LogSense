# modal_fastapi.py - FastAPI approach to serve Streamlit
import modal
import subprocess
import threading
import time

APP_NAME = "logsense-streamlit"
PORT = 8000
STREAMLIT_PORT = 8501  # Run Streamlit on different port

# Build a lean image
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt")
    .pip_install("fastapi[standard]>=0.100.0", "requests")
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=image)

# Create FastAPI instance
web_app = FastAPI()

# Global variable to track Streamlit process
streamlit_proc = None

def start_streamlit():
    """Start Streamlit in background"""
    global streamlit_proc
    import os
    os.chdir("/root/app")
    
    cmd = [
        "streamlit", "run", "streamlit_test.py",
        "--server.port", str(STREAMLIT_PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false"
    ]
    
    streamlit_proc = subprocess.Popen(cmd)
    
    # Wait for Streamlit to be ready
    for i in range(30):
        try:
            response = requests.get(f"http://localhost:{STREAMLIT_PORT}", timeout=2)
            if response.status_code == 200:
                print(f"Streamlit ready after {i+1} seconds")
                return True
        except:
            time.sleep(1)
    
    print("Streamlit failed to start")
    return False

@web_app.on_event("startup")
async def startup_event():
    """Start Streamlit when FastAPI starts"""
    threading.Thread(target=start_streamlit, daemon=True).start()

@web_app.get("/")
async def proxy_streamlit():
    """Proxy requests to Streamlit"""
    try:
        response = requests.get(f"http://localhost:{STREAMLIT_PORT}")
        return Response(content=response.content, media_type="text/html")
    except Exception as e:
        return HTMLResponse(f"<h1>Streamlit not ready</h1><p>Error: {e}</p>")

@web_app.get("/health")
async def health():
    return {"ok": True, "streamlit_running": streamlit_proc is not None and streamlit_proc.poll() is None}

# Deploy FastAPI app
@app.function(timeout=24*60*60)
@modal.asgi_app()
def fastapi_app():
    return web_app
