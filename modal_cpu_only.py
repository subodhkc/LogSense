"""Modal CPU-only deployment - no GPU dependencies."""
import os
import modal
from datetime import datetime
from typing import Dict, Any

# Environment configuration
MODAL_USE_GPU = int(os.getenv("MODAL_USE_GPU", "0"))
APP_NAME = "logsense-cpu"

# CPU-only image - slim Python base
cpu_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt")
    .env({
        "MODAL_USE_GPU": "0",
        "PYTHONPATH": "/root/app"
    })
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=cpu_image)

@app.function(
    timeout=300,
    memory=1024,  # Reduced memory for CPU-only
    min_containers=0,  # Scale to zero for cost efficiency
    retries=modal.Retries(max_retries=2)
)
@modal.asgi_app()
def cpu_app():
    """CPU-only FastAPI app - no torch imports."""
    import sys
    sys.path.insert(0, '/root/app')
    
    from fastapi import FastAPI, File, UploadFile, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from infra.http import AsyncHTTPClient
    from infra.storage import read_text_file, create_temp_file, cleanup_temp_file
    
    web_app = FastAPI(title="LogSense CPU - Basic Analysis", version="1.0.0")
    
    # Mount static files and templates
    web_app.mount("/static", StaticFiles(directory="/root/app/static"), name="static")
    templates = Jinja2Templates(directory="/root/app/templates")
    
    # Session cache
    session_cache: Dict[str, Any] = {}
    
    @web_app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Serve main page."""
        return templates.TemplateResponse("index.html", {"request": request})
    
    @web_app.get("/health")
    async def health_check():
        """CPU health check."""
        return {
            "status": "healthy",
            "deployment": "cpu-only",
            "gpu_enabled": False,
            "memory": "1024MB",
            "timestamp": datetime.now().isoformat()
        }
    
    @web_app.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        """CPU-only file upload and basic analysis."""
        try:
            # Validate file
            if not file.filename or not file.filename.endswith(('.log', '.txt')):
                return JSONResponse({
                    "success": False,
                    "message": "Invalid file type. Supported: .log, .txt"
                }, status_code=400)
            
            # Read file content
            content = await file.read()
            text_content = content.decode('utf-8', errors='ignore')
            
            # Basic CPU analysis - no ML
            events = _parse_basic_events(text_content, file.filename)
            analysis = _basic_cpu_analysis(events)
            
            # Store in cache
            session_cache["current"] = {
                "events": events[:50],  # Limit for CPU
                "analysis": analysis,
                "filename": file.filename,
                "upload_time": datetime.now().isoformat()
            }
            
            return JSONResponse({
                "success": True,
                "message": f"File processed. Found {len(events)} events.",
                "event_count": len(events),
                "analysis": analysis
            })
            
        except Exception as e:
            return JSONResponse({
                "success": False,
                "message": f"Upload failed: {str(e)}"
            }, status_code=500)
    
    @web_app.post("/submit_context")
    async def submit_context(request: Request):
        """Handle context submission."""
        try:
            data = await request.json()
            current_data = session_cache.get("current", {})
            current_data["context"] = data
            session_cache["current"] = current_data
            
            return JSONResponse({
                "status": "success",
                "message": "Context saved"
            })
        except Exception as e:
            return JSONResponse({
                "status": "error",
                "message": str(e)
            }, status_code=500)
    
    def _parse_basic_events(content: str, filename: str):
        """Basic event parsing without heavy dependencies."""
        events = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines[:1000]):  # Limit for CPU
            if line.strip():
                events.append({
                    "line_number": i + 1,
                    "content": line.strip(),
                    "filename": filename,
                    "level": _guess_log_level(line)
                })
        
        return events
    
    def _guess_log_level(line: str):
        """Simple log level detection."""
        line_upper = line.upper()
        if any(word in line_upper for word in ['ERROR', 'FAIL']):
            return 'ERROR'
        elif any(word in line_upper for word in ['WARN', 'WARNING']):
            return 'WARNING'
        elif 'INFO' in line_upper:
            return 'INFO'
        return 'DEBUG'
    
    def _basic_cpu_analysis(events):
        """Basic analysis without ML dependencies."""
        total = len(events)
        errors = sum(1 for e in events if e.get('level') == 'ERROR')
        warnings = sum(1 for e in events if e.get('level') == 'WARNING')
        
        return {
            "total_events": total,
            "error_count": errors,
            "warning_count": warnings,
            "summary": f"Processed {total} events: {errors} errors, {warnings} warnings",
            "processing_mode": "cpu-basic"
        }
    
    return web_app

if __name__ == "__main__":
    print("LogSense CPU-Only Deployment")
    print("- No GPU dependencies")
    print("- Basic log analysis only")
    print("- Lightweight and cost-efficient")
