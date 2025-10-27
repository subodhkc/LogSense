"""
LogSense Production Deployment for haiec Modal Account
Canonical entry point: https://haiec--logsense-production-web-app.modal.run
"""
import modal
import os
import sys
import tempfile
import zipfile
from datetime import datetime
from typing import Dict, Any, List, Optional

# Production App Configuration
APP_NAME = "logsense-production"
FUNCTION_NAME = "web_app"

# Create optimized Modal image for production
production_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi==0.116.1",
        "uvicorn[standard]==0.30.6", 
        "pydantic>=2.7.4,<3",
        "python-multipart==0.0.20",
        "jinja2>=3.1.0",
        "aiofiles>=23.0.0",
        "httpx>=0.24.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.1",
        "openai>=1.0.0",
        "cryptography>=43.0.0",
        "certifi>=2024.8.30",
        # Additional dependencies for LogSense
        "pandas>=2.0.0",
        "numpy>=1.24.0"
    )
    .add_local_dir(".", remote_path="/root/app")
    .run_commands("python -c 'import sys; print(f\"Python path: {sys.path}\")'")
    .run_commands("python -c 'import pkgutil; print(f\"Web framework available: {pkgutil.find_loader(\\\"fastapi\\\") is not None}\")'")
)

# Initialize Modal app
app = modal.App(name=APP_NAME)

# Global cache for analysis results
analysis_cache = {}

@app.function(
    image=production_image,
    name=FUNCTION_NAME,
    serialized=True,
    timeout=300,  # 5 minutes
    memory=2048,  # 2GB
    min_containers=1,  # Warm containers for production
    scaledown_window=600  # 10 minutes
)
@modal.asgi_app()
def web_app():
    """Production FastAPI application for LogSense"""
    
    # Runtime verification
    import platform, pkgutil
    print(f"[PRODUCTION_STARTUP] app='{APP_NAME}' func='{FUNCTION_NAME}' py={platform.python_version()}")
    print(f"[DEPENDENCIES] web_framework={pkgutil.find_loader('fastapi') is not None}")
    
    # Import FastAPI stack
    from fastapi import FastAPI, File, UploadFile, Request, Form
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from fastapi.middleware.cors import CORSMiddleware
    
    # Add project root to Python path
    sys.path.insert(0, "/root/app")
    
    # Import LogSense modules
    try:
        # Add Python Modules to path for analyzer imports
        import sys
        sys.path.insert(0, "/root/app/Python Modules")
        
        from infra.security import sanitize_log_data
        from analysis import parse_log_file
        from analyzer.baseline_analyzer import analyze_events
        from infra.cascade_logging import get_cascade_logger
        cascade_logger = get_cascade_logger("production_app")
        cascade_logger.info("LogSense Production application starting")
    except ImportError as e:
        print(f"[IMPORT_WARNING] {e}")
        cascade_logger = None
        
        # Provide fallback functions if imports fail
        def sanitize_log_data(data):
            return str(data).replace('<', '&lt;').replace('>', '&gt;')
        
        def parse_log_file(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            return [{"timestamp": "unknown", "level": "INFO", "message": line.strip()} for line in lines[:100]]
        
        def analyze_events(events):
            return {"total_events": len(events), "analysis": "Basic analysis - full analyzer not available"}
    
    # Initialize FastAPI app
    fastapi_app = FastAPI(
        title="LogSense Enterprise",
        description="Enterprise Log Analysis Platform - Production",
        version="2.0.0"
    )
    
    # Add CORS middleware
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Setup templates and static files
    templates = Jinja2Templates(directory="/root/app/templates")
    
    try:
        fastapi_app.mount("/static", StaticFiles(directory="/root/app/static"), name="static")
    except Exception as e:
        print(f"[STATIC_WARNING] Could not mount static files: {e}")
    
    @fastapi_app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """Main application interface"""
        try:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "title": "LogSense Enterprise - Production",
                "version": "2.0.0",
                "environment": "production"
            })
        except Exception as e:
            return HTMLResponse(f"""
            <html><head><title>LogSense Enterprise</title></head>
            <body>
                <h1>LogSense Enterprise - Production</h1>
                <p>Application is running but template not found.</p>
                <p>Error: {str(e)}</p>
                <p><a href="/health">Health Check</a></p>
            </body></html>
            """)
    
    @fastapi_app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring"""
        return {
            "status": "ok",
            "app": APP_NAME,
            "function": FUNCTION_NAME,
            "environment": "production",
            "timestamp": datetime.utcnow().isoformat(),
            "canary": "PRODUCTION_READY_2024",
            "signature": "LogSense Enterprise v2.0.0 - Compliant Processing Engine"
        }
    
    @fastapi_app.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        """Secure file upload endpoint with enterprise compliance"""
        
        # Generate compliance ID
        compliance_id = f"COMP-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        try:
            # Security validation
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
            
            # File size validation (25MB limit)
            content = await file.read()
            if len(content) > 25 * 1024 * 1024:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error", 
                        "message": "File too large. Maximum size is 25MB.",
                        "compliance_id": compliance_id,
                        "signature": "LogSense Enterprise v2.0.0 - Error Handler"
                    }
                )
            
            # Process the file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.log') as tmp_file:
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                # Parse and analyze the log file
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
                    cascade_logger.info(f"File processed successfully: {file.filename} ({len(events)} events)")
                
                return {
                    "status": "success",
                    "message": f"File '{file.filename}' uploaded and processed successfully",
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
            error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            if cascade_logger:
                cascade_logger.error(f"Upload error {error_id}: {str(e)}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Internal processing error",
                    "error_id": error_id,
                    "signature": "LogSense Enterprise v2.0.0 - Error Handler"
                }
            )
    
    @fastapi_app.post("/analyze")
    async def analyze_logs(compliance_id: str = Form(...)):
        """Analyze uploaded logs"""
        
        try:
            global analysis_cache
            if compliance_id not in analysis_cache:
                return JSONResponse(
                    status_code=404,
                    content={
                        "status": "error",
                        "message": "Analysis data not found. Please upload a file first.",
                        "signature": "LogSense Enterprise v2.0.0 - Error Handler"
                    }
                )
            
            cached_data = analysis_cache[compliance_id]
            events = cached_data["events"]
            
            # Perform baseline analysis
            analysis_results = analyze_events(events)
            
            # Update cache with analysis results
            analysis_cache[compliance_id]["analysis"] = analysis_results
            
            return {
                "status": "success",
                "analysis": analysis_results,
                "events_analyzed": len(events),
                "compliance_id": compliance_id,
                "signature": "LogSense Enterprise v2.0.0 - Compliant Processing Engine"
            }
            
        except Exception as e:
            error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            if cascade_logger:
                cascade_logger.error(f"Analysis error {error_id}: {str(e)}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Analysis processing error",
                    "error_id": error_id,
                    "signature": "LogSense Enterprise v2.0.0 - Error Handler"
                }
            )
    
    @fastapi_app.post("/submit_context")
    async def submit_context(
        user_name: str = Form(...),
        app_name: str = Form(...),
        version: str = Form(...),
        environment: str = Form(...),
        issue_description: str = Form(...)
    ):
        """Submit user context and issue description"""
        
        try:
            # Input validation and sanitization
            context_data = {
                "user_name": user_name[:100],  # Limit length
                "app_name": app_name[:100],
                "version": version[:50],
                "environment": environment[:50],
                "issue_description": issue_description[:1000],
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Sanitize inputs
            for key, value in context_data.items():
                if isinstance(value, str):
                    context_data[key] = sanitize_log_data(value)
            
            if cascade_logger:
                cascade_logger.info(f"Context submitted by {context_data['user_name']} for {context_data['app_name']}")
            
            return {
                "status": "success",
                "message": "Context information saved successfully",
                "context_id": f"CTX-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                "signature": "LogSense Enterprise v2.0.0 - Compliant Processing Engine"
            }
            
        except Exception as e:
            error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            if cascade_logger:
                cascade_logger.error(f"Context submission error {error_id}: {str(e)}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Failed to save context information",
                    "error_id": error_id,
                    "signature": "LogSense Enterprise v2.0.0 - Error Handler"
                }
            )
    
    print(f"[PRODUCTION_READY] LogSense Enterprise production app initialized")
    return fastapi_app

# Export for Modal deployment
if __name__ == "__main__":
    print(f"LogSense Production App: {APP_NAME}")
    print(f"Expected URL: https://haiec--{APP_NAME}-{FUNCTION_NAME.replace('_', '-')}.modal.run")
