# modal_asgi.py - Direct ASGI approach to serve Streamlit
import modal
import subprocess
import threading
import time
import socket

APP_NAME = "logsense-streamlit"

# Build a lean image
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt")
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=image)

# Global variable to track Streamlit process
streamlit_proc = None

def start_streamlit():
    """Start Streamlit in background on port 8501"""
    global streamlit_proc
    import os
    os.chdir("/root/app")
    
    cmd = [
        "streamlit", "run", "skc_log_analyzer_minimal.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0", 
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false"
    ]
    
    print("[MODAL] Starting Streamlit on port 8501...")
    streamlit_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for Streamlit to be ready
    for i in range(60):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 8501))
            sock.close()
            if result == 0:
                print(f"[MODAL] Streamlit ready on port 8501 after {i+1} seconds")
                return True
        except:
            pass
        time.sleep(1)
    
    print("[MODAL] Streamlit failed to start on port 8501")
    return False

async def asgi_app(scope, receive, send):
    """Simple ASGI app that proxies to Streamlit"""
    if scope["type"] == "http":
        # Start Streamlit if not running
        if streamlit_proc is None:
            threading.Thread(target=start_streamlit, daemon=True).start()
            time.sleep(5)  # Give it time to start
        
        # Simple response for now
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"text/html"]],
        })
        
        if streamlit_proc and streamlit_proc.poll() is None:
            body = b"""
            <html>
            <head><title>LogSense</title></head>
            <body>
                <h1>LogSense is Starting...</h1>
                <p>Streamlit is running on port 8501</p>
                <p>Please wait while the application initializes...</p>
                <script>
                    setTimeout(() => {
                        window.location.href = 'https://subodhkc--streamlit-direct.modal.run';
                    }, 2000);
                </script>
            </body>
            </html>
            """
        else:
            body = b"<h1>Error: Streamlit failed to start</h1>"
            
        await send({
            "type": "http.response.body",
            "body": body,
        })

@app.function(timeout=24*60*60)
@modal.asgi_app()
def web_app():
    return asgi_app

# Also create a direct Streamlit web_server
@app.function(timeout=24*60*60)
@modal.web_server(port=8501, startup_timeout=300, label="streamlit-direct")
def streamlit_direct():
    import os
    os.chdir("/root/app")
    
    import subprocess
    cmd = [
        "streamlit", "run", "skc_log_analyzer_minimal.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false", 
        "--server.enableXsrfProtection", "false"
    ]
    
    proc = subprocess.Popen(cmd)
    proc.wait()
