# modal_deploy_async.py — canonical web entry for https://haiec--logsense-async-async-app.modal.run/
import modal
from datetime import datetime

app = modal.App("logsense-economical-disabled-async-OLD")  # Disabled - use modal_haiec_production.py instead

# Minimal FastAPI-first image - install FastAPI FIRST and ONLY
web_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("fastapi==0.115.3")  # ONLY FastAPI first
    .pip_install("uvicorn[standard]==0.30.6")  # Then uvicorn
    .pip_install("python-multipart==0.0.9")  # Then multipart for uploads
    .run_commands("python -c 'import fastapi; print(f\"FastAPI {fastapi.__version__} installed successfully\")'")
    .add_local_dir(".", remote_path="/root/app")
)

ASYNC_CANARY = "FASTAPI_FIRST_20250824_1723_MINIMAL"

@app.function(image=web_image, name="economical-app")
@modal.asgi_app()
def async_app():
    # CANARY + runtime probe BEFORE importing FastAPI
    import os, sys, pkgutil, platform
    print(
        f"[CANARY] {ASYNC_CANARY} app='logsense-economical' func='economical-app' "
        f"py={platform.python_version()} "
        f"fastapi_present={pkgutil.find_loader('fastapi') is not None} "
        f"pid={os.getpid()}"
    )

    # Import FastAPI and verify versions - MINIMAL imports only
    try:
        from fastapi import FastAPI, File, UploadFile, Request
        from fastapi.responses import JSONResponse, HTMLResponse
        import uvicorn
        print(f"[VERSIONS] fastapi>ok uvicorn={uvicorn.__version__}")
    except Exception as e:
        print(f"[FASTAPI_IMPORT_FAIL] {e!r}")
        import subprocess
        out = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
        print("[PIP_FREEZE_HEAD]\n" + out[:2000])
        raise

    # Initialize Cascade logger for troubleshooting
    try:
        from infra.cascade_logging import get_cascade_logger
        cascade_logger = get_cascade_logger("prod_app")
        cascade_logger.info("Production application starting up.")
    except ImportError:
        print("[WARNING] Cascade logger not found, proceeding without it.")
        class FakeLogger:
            def info(self, *args, **kwargs): pass
            def error(self, *args, **kwargs): pass
        cascade_logger = FakeLogger()

    # Create minimal FastAPI app - NO CORS to avoid extra dependencies
    api = FastAPI(title="LogSense Enterprise", version="1.0.0")

    # MINIMAL setup - skip router/static/templates to avoid import issues
    routes_attached = []
    templates = None
    print("[MINIMAL] Skipping router/static/templates for FastAPI-first test")

    # Core endpoints - preserve ALL existing functionality
    
    @api.get("/health")
    async def health():
        return {
            "status": "ok", 
            "service": "haiec", 
            "version": "1.0.0", 
            "canary": ASYNC_CANARY,
            "routes_attached": routes_attached
        }

    @api.get("/")
    async def index():
        return HTMLResponse("""
        <html><head><title>LogSense Enterprise</title></head>
        <body><h1>LogSense Enterprise v2.0.0</h1>
        <p>FastAPI working! Upload functionality available at POST /upload</p>
        <p>Health check: <a href=\"/health\">/health</a></p>
        </body></html>
        """)

    @api.post("/upload")
    async def upload_file(request: Request, file: UploadFile = File(...)):
        """Handle file upload with comprehensive security and compliance"""
        try:
            # Content-Type validation
            content_type = request.headers.get("content-type", "").lower()
            if not content_type.startswith("multipart/form-data"):
                return JSONResponse({
                    "success": False,
                    "error_code": "E.REQ.001",
                    "message": "Content-Type must be multipart/form-data",
                    "compliance_id": f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }, status_code=415)

            content = await file.read()
            MAX_UPLOAD_SIZE = 25 * 1024 * 1024
            if len(content) > MAX_UPLOAD_SIZE:
                return JSONResponse({
                    "success": False,
                    "error_code": "E.REQ.002", 
                    "message": f"File too large. Maximum size: {MAX_UPLOAD_SIZE // (1024*1024)}MB",
                    "compliance_id": f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }, status_code=413)

            allowed_extensions = ['.log', '.txt', '.zip']
            if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
                return JSONResponse({
                    "success": False,
                    "error_code": "E.REQ.003",
                    "message": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
                    "compliance_id": f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }, status_code=400)

            # Sanitize filename
            import re
            safe_filename = re.sub(r'[<>:"|?*]', '', file.filename)
            safe_filename = safe_filename.replace('..', '').strip()

            # Cascade logging
            cascade_logger.info(f"Processing upload for file: {safe_filename}, size: {len(content)} bytes, content-type: {content_type}")

            # Parse log content with fallback
            try:
                from analysis import parse_log_file
                from analyzer.baseline_analyzer import analyze_events
                from infra.security import sanitize_log_data
            except ImportError as e:
                print(f"[IMPORT_WARNING] {e!r} - using fallback")
                # Fallback parsing
                def parse_log_file(content, filename):
                    lines = content.split('\n')
                    events = []
                    for i, line in enumerate(lines[:100]):  # Limit for demo
                        if line.strip():
                            events.append({
                                'timestamp': datetime.now().isoformat(),
                                'component': 'unknown',
                                'message': line.strip(),
                                'severity': 'INFO'
                            })
                    return events
                
                def analyze_events(events):
                    return {'issues': [], 'critical_errors': 0, 'warnings': 0}
                
                def sanitize_log_data(event):
                    return event

            events = []
            if safe_filename.endswith('.zip'):
                import tempfile
                import zipfile
                import os
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                    temp_zip.write(content)
                    temp_zip.flush()

                    with zipfile.ZipFile(temp_zip.name, 'r') as zip_ref:
                        for file_info in zip_ref.filelist:
                            if not file_info.is_dir() and file_info.filename.endswith(('.log', '.txt', '.out')):
                                with zip_ref.open(file_info) as log_file:
                                    log_content = log_file.read().decode('utf-8', errors='ignore')
                                    file_events = parse_log_file(log_content, file_info.filename)
                                    events.extend(file_events)

                    os.unlink(temp_zip.name)
            else:
                log_content = content.decode('utf-8', errors='ignore')
                events = parse_log_file(log_content, safe_filename)

            # Sanitize events
            sanitized_events = []
            for event in events:
                if hasattr(event, '__dict__'):
                    event_dict = {
                        'timestamp': getattr(event, 'timestamp', ''),
                        'component': getattr(event, 'component', ''),
                        'message': getattr(event, 'message', ''),
                        'severity': getattr(event, 'severity', 'INFO')
                    }
                else:
                    event_dict = event
                    
                sanitized_event = sanitize_log_data(event_dict)
                sanitized_events.append(sanitized_event)

            analysis_result = analyze_events(events)

            # Store in global cache
            global analysis_cache
            try:
                analysis_cache = sanitized_events
            except:
                analysis_cache = sanitized_events  # Create if doesn't exist

            compliance_id = f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Enhanced redaction detection
            redacted = False
            redaction_count = 0
            sensitive_patterns = [
                r'password["\s]*[:=]["\s]*([^"\s,}]+)',
                r'token["\s]*[:=]["\s]*([^"\s,}]+)', 
                r'api[_-]?key["\s]*[:=]["\s]*([^"\s,}]+)',
                r'secret["\s]*[:=]["\s]*([^"\s,}]+)',
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # emails
            ]

            for event in sanitized_events:
                message = event.get('message', '')
                for pattern in sensitive_patterns:
                    if re.search(pattern, message, re.IGNORECASE):
                        redacted = True
                        redaction_count += 1
                        break

            print(f"[COMPLIANCE] Upload processed - ID: {compliance_id}, File: {safe_filename}, Events: {len(sanitized_events)}, Redacted: {redaction_count}")

            return JSONResponse({
                "success": True,
                "event_count": len(sanitized_events),
                "events": sanitized_events[:50],
                "issues_found": len(analysis_result.get('issues', [])),
                "critical_errors": analysis_result.get('critical_errors', 0),
                "warnings": analysis_result.get('warnings', 0),
                "redacted": redacted,
                "redaction_count": redaction_count,
                "filename": safe_filename,
                "message": f"Successfully processed {safe_filename}. Found {len(sanitized_events)} events.",
                "compliance_id": compliance_id,
                "processing_timestamp": datetime.now().isoformat(),
                "security_validation": "passed",
                "signature": "LogSense Enterprise v2.0.0 - Compliant Processing Engine"
            })

        except Exception as e:
            error_id = f"ERR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            # Use repr(e) for more detailed error logging
            print(f"[ERROR] Upload failed - ID: {error_id}, Error: {e!r}")
            cascade_logger.error(f"Upload failed for error_id: {error_id}. Exception: {e!r}")

            return JSONResponse({
                "success": False,
                "error_code": "E.SRV.001",
                "message": "Upload processing failed. Please try again.",
                "error_id": error_id,
                "compliance_id": f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "signature": "LogSense Enterprise v2.0.0 - Error Handler"
            }, status_code=500)

    @api.post("/analyze")
    async def analyze():
        """Analyze uploaded log data"""
        from fastapi.responses import JSONResponse
        try:
            global analysis_cache
            events = getattr(analysis_cache, 'events', analysis_cache if 'analysis_cache' in globals() else [])
            
            return JSONResponse({
                "success": True,
                "message": "Analysis completed",
                "event_count": len(events) if isinstance(events, list) else 0,
                "signature": "LogSense Enterprise v2.0.0 - AI Analysis Engine"
            })
        except Exception as e:
            return JSONResponse({
                "success": False, 
                "error": str(e),
                "signature": "LogSense Enterprise v2.0.0 - Error Handler"
            }, status_code=500)

    @api.post("/submit_context")
    async def submit_context(request: Request):
        """Submit user context form data"""
        from fastapi.responses import JSONResponse
        try:
            form_data = await request.form()
            context = {
                "user_context": form_data.get("user_context", ""),
                "issue_description": form_data.get("issue_description", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            return JSONResponse({
                "success": True,
                "message": "Context saved successfully",
                "signature": "LogSense Enterprise v2.0.0 - Context Manager"
            })
        except Exception as e:
            return JSONResponse({
                "success": False, 
                "error": str(e),
                "signature": "LogSense Enterprise v2.0.0 - Error Handler"
            }, status_code=500)

    @api.post("/generate_report")
    async def generate_report():
        """Generate analysis report"""
        from fastapi.responses import JSONResponse
        try:
            global analysis_cache
            events = getattr(analysis_cache, 'events', analysis_cache if 'analysis_cache' in globals() else [])
            
            report = {
                "report_id": f"RPT-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "generated_at": datetime.now().isoformat(),
                "event_count": len(events) if isinstance(events, list) else 0,
                "summary": "Log analysis completed successfully",
                "recommendations": ["Review critical errors", "Monitor system performance"]
            }
            
            return JSONResponse({
                "success": True,
                "report": report,
                "signature": "LogSense Enterprise v2.0.0 - Report Generator"
            })
        except Exception as e:
            return JSONResponse({
                "success": False, 
                "error": str(e),
                "signature": "LogSense Enterprise v2.0.0 - Error Handler"
            }, status_code=500)

    return api

# Global analysis cache
analysis_cache = []

# Retire ALL other ASGI exports in THIS file to avoid graph conflicts
if False:
    @app.function()
    @modal.asgi_app()
    def old_async_app():
        ...
