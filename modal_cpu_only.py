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
    import os
    import asyncio
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from infra.http import AsyncHTTPClient
    from infra.storage import read_text_file, create_temp_file, cleanup_temp_file
    from infra.security import add_security_headers, add_cors_middleware, validate_content_type, validate_file_upload, ErrorCodes
    from infra.error_handler import GlobalErrorHandler, setup_logging, SecureLogger
    
    web_app = FastAPI(title="LogSense CPU - Basic Analysis", version="1.0.0")
    
    # Setup security and error handling
    setup_logging()
    add_security_headers(web_app)
    add_cors_middleware(web_app)
    GlobalErrorHandler(web_app)
    
    # Mount static files and templates
    web_app.mount("/static", StaticFiles(directory="/root/app/static"), name="static")
    templates = Jinja2Templates(directory="/root/app/templates")
    
    # Session cache
    session_cache: Dict[str, Any] = {}
    logger = SecureLogger(__name__)
    
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
    async def upload_file(request: Request, file: UploadFile = File(...), context: str = Form("")):
        """Handle file upload - CPU only basic parsing."""
        try:
            # Validate file upload
            content = await file.read()
            validate_file_upload(content, file.filename)
            
            logger.info(f"File upload started: {file.filename}")
            
            # Create temp file for processing
            temp_path = await create_temp_file(content, file.filename)
            
            try:
                # Basic log parsing without ML
                from analysis import parse_log_file
                events = parse_log_file(temp_path)
                
                # Store in session cache
                session_id = f"cpu_session_{len(session_cache)}"
                session_cache[session_id] = {
                    "events": events[:100],  # Limit for CPU
                    "filename": file.filename,
                    "context": context
                }
                
                logger.info(f"File processed successfully: {len(events)} events found")
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "events_found": len(events),
                    "message": "File processed successfully (CPU-only mode)"
                }
                
            finally:
                await cleanup_temp_file(temp_path)
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail={
                    "error_code": ErrorCodes.PROCESSING_FAILED,
                    "message": "File upload failed"
                }
            )
    
    @web_app.post("/analyze")
    async def analyze_logs(request: Request):
        """Basic log analysis without ML."""
        try:
            validate_content_type(request, "application/json")
            data = await request.json()
            session_id = data.get("session_id")
            
            if not session_id or session_id not in session_cache:
                raise HTTPException(
                    status_code=404, 
                    detail={
                        "error_code": ErrorCodes.PROCESSING_FAILED,
                        "message": "Session not found"
                    }
                )
            
            session_data = session_cache[session_id]
            events = session_data["events"]
            
            # Basic analysis without ML
            analysis_result = {
                "total_events": len(events),
                "event_types": {},
                "severity_distribution": {},
                "sample_events": events[:5]
            }
            
            # Count event types and severities
            for event in events:
                event_type = event.get("type", "unknown")
                severity = event.get("severity", "info")
                
                analysis_result["event_types"][event_type] = analysis_result["event_types"].get(event_type, 0) + 1
                analysis_result["severity_distribution"][severity] = analysis_result["severity_distribution"].get(severity, 0) + 1
            
            logger.info(f"Analysis completed for session {session_id}")
            
            return {
                "success": True,
                "analysis": analysis_result,
                "message": "Basic analysis complete (CPU-only mode)"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail={
                    "error_code": ErrorCodes.PROCESSING_FAILED,
                    "message": "Analysis failed"
                }
            )
    
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
