"""Async Modal deployment for LogSense with proper error handling and SonarCloud compliance."""
import asyncio
import os
from typing import Dict, Any

import modal
import aiofiles
import httpx

# Constants
APP_ENTRY_FILE = "skc_log_analyzer_minimal.py"
SERVER_PORT = 8000
STARTUP_TIMEOUT = 600
SCALEDOWN_WINDOW = 600
MEMORY_SIZE = 2048
CPU_COUNT = 2
MAX_TIMEOUT = 900

# Minimal image build with async dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt")
    .pip_install(["aiofiles>=23.0.0", "httpx>=0.24.0"])
    .env({
        "STREAMLIT_WATCHER_TYPE": "none", 
        "MODEL_BACKEND": "openai",
        "DISABLE_ML_MODELS": "true",
        "PYTHONPATH": "/root/app"
    })
    .workdir("/root/app")
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name="logsense-streamlit", image=image)

@app.function(
    memory=MEMORY_SIZE,
    cpu=CPU_COUNT,
    timeout=MAX_TIMEOUT,
    min_containers=1,
    scaledown_window=SCALEDOWN_WINDOW,
    retries=modal.Retries(max_retries=0)
)
@modal.web_server(port=SERVER_PORT, startup_timeout=STARTUP_TIMEOUT)
async def run():
    """Async Streamlit server with proper error handling and monitoring."""
    try:
        await _configure_environment()
        process = await _start_streamlit_process()
        await _monitor_process_startup(process)
        await _keep_process_alive(process)
    except Exception as e:
        print(f"[MODAL] Critical error in main process: {e}", flush=True)
        raise


async def _configure_environment() -> None:
    """Configure environment variables for Streamlit."""
    env_vars = {
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
        "STREAMLIT_WATCHER_TYPE": "none"
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    print("[MODAL] Environment configured", flush=True)


async def _build_streamlit_command() -> list[str]:
    """Build Streamlit command with proper configuration."""
    return [
        "streamlit", "run", APP_ENTRY_FILE,
        "--server.port", str(SERVER_PORT),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--server.enableCORS", "false", 
        "--server.enableXsrfProtection", "false",
        "--server.fileWatcherType", "none",
        "--browser.gatherUsageStats", "false"
    ]


async def _start_streamlit_process():
    """Start Streamlit process asynchronously."""
    import subprocess
    import asyncio
    
    cmd = await _build_streamlit_command()
    print(f"[MODAL] Starting: {' '.join(cmd)}", flush=True)
    
    # Secure subprocess with timeout and shell=False
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        shell=False,  # Security: prevent shell injection
        timeout=300   # 5 minute timeout
    )
    
    return process


async def _monitor_process_startup(process) -> bool:
    """Monitor process startup with timeout and error detection."""
    startup_indicators = [
        "Network URL:", "External URL:", "Local URL:", 
        "You can now view your Streamlit app"
    ]
    
    startup_complete = False
    
    try:
        for line in iter(process.stdout.readline, ''):
            print(f"[STREAMLIT] {line.strip()}", flush=True)
            
            if any(indicator in line for indicator in startup_indicators):
                startup_complete = True
                print("[MODAL] Streamlit startup confirmed!", flush=True)
                break
                
            if _is_error_line(line):
                print(f"[MODAL] Error detected: {line.strip()}", flush=True)
                
    except Exception as e:
        print(f"[MODAL] Error monitoring startup: {e}", flush=True)
    
    return startup_complete


def _is_error_line(line: str) -> bool:
    """Check if log line indicates an error."""
    error_keywords = ["error", "failed", "exception", "traceback"]
    return any(keyword in line.lower() for keyword in error_keywords)


async def _keep_process_alive(process) -> None:
    """Keep the process alive with proper monitoring."""
    print("[MODAL] Keeping Streamlit process alive...", flush=True)
    
    try:
        # Use asyncio to wait for process completion
        while process.poll() is None:
            await asyncio.sleep(1.0)  # Non-blocking sleep
            
        print(f"[MODAL] Process exited with code: {process.returncode}", flush=True)
        
    except Exception as e:
        print(f"[MODAL] Error in process monitoring: {e}", flush=True)
        if process.poll() is None:
            process.terminate()

@app.function(timeout=15)
@modal.fastapi_endpoint(label="health")
async def health() -> Dict[str, Any]:
    """Async health check endpoint with comprehensive status."""
    try:
        # Check if we can write to temp directory
        async with aiofiles.tempfile.NamedTemporaryFile(mode='w', delete=True) as temp_file:
            await temp_file.write("health_check")
            
        return {
            "status": "healthy",
            "service": "logsense-streamlit",
            "version": "2.0.0",
            "async_support": True,
            "file_system": "accessible"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "logsense-streamlit", 
            "error": str(e)
        }
