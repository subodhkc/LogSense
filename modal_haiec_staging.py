"""
LogSense Staging Deployment for haiec Modal Account
Canonical entry point: https://haiec--logsense-staging-web-app.modal.run
"""
import modal

# Staging App Configuration
APP_NAME = "logsense-staging"
FUNCTION_NAME = "web-app"

# Minimal staging image with explicit FastAPI pins
staging_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi==0.116.1",
        "starlette>=0.37.2,<0.39.0",
        "uvicorn==0.30.6",
        "pydantic>=2.7.4,<3",
        "python-multipart==0.0.20",
        "jinja2>=3.1.0",
        "aiofiles>=23.0.0"
    )
    .add_local_dir(".", remote_path="/root/app")
)

# Initialize Modal app
app = modal.App(name=APP_NAME)

# Global cache for analysis results
analysis_cache = {}

@app.function(
    image=staging_image, 
    name=FUNCTION_NAME,
    serialized=True,
    timeout=180,  # 3 minutes for staging
    memory=1024,  # 1GB for staging
    min_containers=0,  # Scale to zero for staging
    scaledown_window=300  # 5 minutes
)
@modal.asgi_app()
def web_app():
    """Staging FastAPI application for LogSense"""
    
    import os, sys, pkgutil, platform
    from fastapi import FastAPI, File, UploadFile, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import tempfile
    import zipfile
    import re
    from datetime import datetime

    # Add project root to path
    sys.path.insert(0, "/root/app")

    # Import LogSense modules with error handling
    try:
        # Add Python Modules to path for analyzer imports
        sys.path.insert(0, "/root/app/Python Modules")
        
        from infra.security import sanitize_log_data
        from analysis import parse_log_file
        from analyzer.baseline_analyzer import analyze_events
    except ImportError as e:
        print(f"[STAGING_IMPORT_WARNING] {e}")
        
        # Provide fallback functions if imports fail
        def sanitize_log_data(data):
            return str(data).replace('<', '&lt;').replace('>', '&gt;')
        
        def parse_log_file(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            return [{"timestamp": "unknown", "level": "INFO", "message": line.strip()} for line in lines[:100]]
        
        def analyze_events(events):
            return {"total_events": len(events), "analysis": "Basic analysis - full analyzer not available"}

    # Initialize Cascade logger for troubleshooting
    try:
        from infra.cascade_logging import get_cascade_logger
        cascade_logger = get_cascade_logger("staging_app")
        cascade_logger.info("Staging application starting up.")
    except ImportError:
        print("[WARNING] Cascade logger not found, proceeding without it.")
        cascade_logger = None

    # Initialize FastAPI app
    fastapi_app = FastAPI(
        title="LogSense Enterprise - Staging",
        description="Enterprise Log Analysis Platform - Staging Environment",
        version="2.0.0-staging"
    )

    # Setup templates and static files
    templates = Jinja2Templates(directory="/root/app/templates")
    
    try:
        fastapi_app.mount("/static", StaticFiles(directory="/root/app/static"), name="static")
    except Exception as e:
        print(f"[STATIC_WARNING] Could not mount static files: {e}")

    @fastapi_app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """Main staging interface"""
        try:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "title": "LogSense Enterprise - Staging",
                "version": "2.0.0-staging",
                "environment": "staging"
            })
        except Exception as e:
            return HTMLResponse(f"""
            <html><head><title>LogSense Enterprise - Staging</title></head>
            <body>
                <h1>LogSense Enterprise - Staging</h1>
                <p>Staging environment is running.</p>
                <p>Error: {str(e)}</p>
                <p><a href="/health">Health Check</a></p>
            </body></html>
            """)

    @fastapi_app.get("/health")
    async def health_check():
        """Health check endpoint for staging monitoring"""
        return {
            "status": "ok",
            "app": APP_NAME,
            "function": FUNCTION_NAME,
            "environment": "staging",
            "timestamp": datetime.utcnow().isoformat(),
            "canary": "STAGING_READY_2024",
            "signature": "LogSense Enterprise v2.0.0 - Compliant Processing Engine"
        }

    @fastapi_app.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        """Staging file upload endpoint"""
        
        # Generate compliance ID
        compliance_id = f"STAGE-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        try:
            # Basic security validation for staging
            if not file.content_type or not file.content_type.startswith(('text/', 'application/octet-stream')):
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Invalid file type. Only log files are allowed.",
                        "compliance_id": compliance_id,
                        "signature": "LogSense Enterprise v2.0.0 - Error Handler"
                    }
                )
            
            # File size validation (10MB limit for staging)
            content = await file.read()
            if len(content) > 10 * 1024 * 1024:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error", 
                        "message": "File too large for staging. Maximum size is 10MB.",
                        "compliance_id": compliance_id,
                        "signature": "LogSense Enterprise v2.0.0 - Error Handler"
                    }
                )
            
            # Process the file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.log') as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                # Parse the log file
                events = parse_log_file(tmp_file_path)
                
                # Store in cache for later analysis
                global analysis_cache
                analysis_cache[compliance_id] = {
                    "events": events,
                    "filename": file.filename,
                    "timestamp": datetime.utcnow().isoformat(),
                    "file_size": len(content)
                }
                
                if cascade_logger:
                    cascade_logger.info(f"Staging file processed: {file.filename} ({len(events)} events)")
                
                return {
                    "status": "success",
                    "message": f"File '{file.filename}' uploaded and processed in staging",
                    "events_found": len(events),
                    "compliance_id": compliance_id,
                    "signature": "LogSense Enterprise v2.0.0 - Compliant Processing Engine"
                }
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except Exception as e:
            error_id = f"STAGE-ERR-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            if cascade_logger:
                cascade_logger.error(f"Staging upload error {error_id}: {str(e)}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Staging processing error",
                    "error_id": error_id,
                    "signature": "LogSense Enterprise v2.0.0 - Error Handler"
                }
            )

    print(f"[STAGING_READY] LogSense Enterprise staging app initialized")
    return fastapi_app

# Export for Modal deployment
if __name__ == "__main__":
    print(f"LogSense Staging App: {APP_NAME}")
    print(f"Expected URL: https://haiec--{APP_NAME}-{FUNCTION_NAME.replace('_', '-')}.modal.run")
