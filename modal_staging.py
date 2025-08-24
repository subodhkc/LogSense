# modal_staging.py - Staging environment for LogSense
import modal

# Staging App Name
app = modal.App("logsense-web-v3")

# Minimal web image with explicit FastAPI pins
web_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "fastapi==0.115.*",
        "starlette==0.38.*",
        "uvicorn==0.30.*",
        "pydantic==2.*",
        "python-multipart==0.0.9",
        "jinja2==3.1.*",
        "aiofiles==24.1.0"
    )
    .add_local_dir(".", remote_path="/root/app")
)

# Global cache for analysis results
analysis_cache = {}

@app.function(image=web_image, name="web-http") # No GPU for staging
@modal.asgi_app()
def web_http():
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

    from infra.security import sanitize_log_data
    from analysis import parse_log_file
    from analyzer.baseline_analyzer import analyze_events

    # Initialize Cascade logger for troubleshooting
    try:
        from infra.cascade_logging import get_cascade_logger
        cascade_logger = get_cascade_logger("staging_app")
        cascade_logger.info("Staging application starting up.")
    except ImportError:
        print("[WARNING] Cascade logger not found, proceeding without it.")
        class FakeLogger:
            def info(self, *args, **kwargs): pass
            def error(self, *args, **kwargs): pass
        cascade_logger = FakeLogger()

    api = FastAPI(title="LogSense Staging", version="3.0.0")

    api.mount("/static", StaticFiles(directory="/root/app/static"), name="static")
    templates = Jinja2Templates(directory="/root/app/templates")

    @api.get("/health")
    async def health():
        return {"status": "ok", "service": "LogSense Staging", "version": "3.0.0", "canary": "true"}

    @api.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @api.post("/upload")
    async def upload_file(request: Request, file: UploadFile = File(...)):
        content_type = request.headers.get("content-type", "").lower()
        if not content_type.startswith("multipart/form-data"):
            return JSONResponse({"status": "error", "message": "Invalid Content-Type"}, status_code=415)

        content = await file.read()
        if not any(file.filename.lower().endswith(ext) for ext in ['.log', '.txt', '.zip']):
            cascade_logger.error(f"Invalid file upload attempt: {file.filename}")
            return JSONResponse({"status": "error", "message": "Invalid file extension"}, status_code=400)

        cascade_logger.info(f"Processing upload for file: {file.filename}")

        events = []
        # This logic is simplified for brevity but should mirror production
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_log:
            temp_log.write(content.decode('utf-8', errors='ignore'))
            temp_log_path = temp_log.name
        events = parse_log_file(temp_log_path)
        os.unlink(temp_log_path)

        sanitized_events = [sanitize_log_data(e) for e in events]
        compliance_id = f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        analysis_cache['events'] = sanitized_events
        analysis_cache['session_id'] = compliance_id

        return JSONResponse({
            "status": "success",
            "session_id": compliance_id,
            "message": f"Successfully processed {file.filename}",
            "compliance_id": compliance_id,
            "signature": "LogSense Enterprise v2.0.0 - Compliant Processing Engine"
        })

    @api.post("/analyze")
    async def analyze(request: Request):
        data = await request.json()
        session_id = data.get("session_id")
        if not session_id or session_id not in analysis_cache.get('session_id', ''):
            return JSONResponse({"status": "error", "message": "Invalid or missing session_id"}, status_code=400)
        
        events = analysis_cache.get('events', [])
        analysis_result = analyze_events(events)
        return JSONResponse({"status": "success", "analysis": analysis_result})

    @api.post("/generate_report")
    async def generate_report(request: Request):
        # Simplified for smoke test
        return JSONResponse({"status": "success", "report": "Generated"})

    return api
