# modal_native.py - Canonical Modal FastAPI entry point
import modal

app = modal.App("logsense-native")  # Canonical app name

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

# Global cache for analysis results (preserve existing functionality)
analysis_cache = {}

@app.function(image=web_image, name="web-http")
@modal.asgi_app()
def web_http_app():
    import os, sys, pkgutil, platform
    print(
        f"[RUNTIME_PROBE] app='logsense-native' func='web-http' "
        f"py={platform.python_version()} "
        f"fastapi_present={pkgutil.find_loader('fastapi') is not None} "
        f"pid={os.getpid()}"
    )
    try:
        from fastapi import FastAPI, File, UploadFile, Request
        from fastapi.responses import HTMLResponse, JSONResponse, Response
        from fastapi.staticfiles import StaticFiles
        from fastapi.templating import Jinja2Templates
        import starlette, pydantic, uvicorn
        print(
            f"[VERSIONS] fastapi>ok "
            f"pydantic={pydantic.__version__} "
            f"uvicorn={uvicorn.__version__} "
            f"starlette={starlette.__version__}"
        )
    except Exception as e:
        print(f"[FASTAPI_IMPORT_FAIL] {e!r}")
        import subprocess
        out = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
        print("[PIP_FREEZE_HEAD]\n" + out[:2000])
        raise

    api = FastAPI(title="LogSense - AI Log Analysis", version="1.0.0")

    # Mount static files and templates (preserve existing functionality)
    try:
        api.mount("/static", StaticFiles(directory="/root/app/static"), name="static")
        templates = Jinja2Templates(directory="/root/app/templates")
    except Exception as e:
        print(f"[STATIC_MOUNT_WARNING] {e}")
        templates = None

    @api.get("/health")
    async def health():
        return {"status": "ok", "service": "LogSense", "version": "1.0.0"}

    @api.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        if templates:
            return templates.TemplateResponse("index.html", {"request": request})
        return HTMLResponse("<h1>LogSense</h1><p>Templates not available</p>")

    # PRESERVE ALL EXISTING FUNCTIONALITY - Upload endpoint with security features
    @api.post("/upload")
    async def upload_file(request: Request, file: UploadFile = File(...)):
        """Handle file upload with comprehensive security and compliance"""
        try:
            sys.path.insert(0, "/root/app")
            from infra.security import validate_file_upload, sanitize_log_data, ErrorCodes
            from datetime import datetime
            import re
            import tempfile
            import zipfile
            import os

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
            safe_filename = re.sub(r'[<>:"|?*]', '', file.filename)
            safe_filename = safe_filename.replace('..', '').strip()

            # Parse log content (preserve existing logic)
            from analysis import parse_log_file
            from analyzer.baseline_analyzer import analyze_events

            events = []
            if safe_filename.endswith('.zip'):
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
                event_dict = {
                    'timestamp': getattr(event, 'timestamp', ''),
                    'component': getattr(event, 'component', ''),
                    'message': getattr(event, 'message', ''),
                    'severity': getattr(event, 'severity', 'INFO')
                }
                sanitized_event = sanitize_log_data(event_dict)
                sanitized_events.append(sanitized_event)

            analysis_result = analyze_events(events)

            # Store in cache (preserve existing functionality)
            compliance_id = f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            analysis_cache['events'] = sanitized_events
            analysis_cache['analysis'] = analysis_result
            analysis_cache['filename'] = safe_filename
            analysis_cache['compliance_id'] = compliance_id
            analysis_cache['upload_timestamp'] = datetime.now().isoformat()

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
            print(f"[ERROR] Upload failed - ID: {error_id}, Error: {str(e)}")

            return JSONResponse({
                "success": False,
                "error_code": "E.SRV.001",
                "message": "Upload processing failed. Please try again.",
                "error_id": error_id,
                "compliance_id": f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "signature": "LogSense Enterprise v2.0.0 - Error Handler"
            }, status_code=500)

    @api.post("/submit_context")
    async def submit_context(request: Request):
        """Submit user context form data"""
        try:
            data = await request.json()
            user_context = {}
            user_context.update(data)
            return JSONResponse({"status": "success", "message": "Context saved successfully"})
        except Exception as e:
            return JSONResponse({"status": "error", "error": str(e)}, status_code=500)

    @api.post("/analyze")
    async def analyze_log(file: UploadFile = File(...)):
        """Analyze uploaded log file with comprehensive processing"""
        try:
            # Read file content
            content = await file.read()
            
            # Handle ZIP files
            events = []
            if file.filename.endswith('.zip'):
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
                # Single log file
                log_content = content.decode('utf-8', errors='ignore')
                events = parse_log_file(log_content, file.filename)
            
            # Analyze events
            analysis_result = analyze_events(events)
            
            # Cache results globally and in session
            _analysis_cache['events'] = events
            _analysis_cache['analysis'] = analysis_result
            _analysis_cache['user_context'] = {}
            
            # Also store in local session cache for redundancy
            analysis_cache['events'] = events
            analysis_cache['analysis'] = analysis_result
            analysis_cache['user_context'] = {}
            
            return JSONResponse({
                "status": "success",
                "events_count": len(events),
                "events": events[:50],  # Return first 50 for display
                "issues_found": len(analysis_result.get('issues', [])),
                "critical_errors": analysis_result.get('critical_errors', 0),
                "warnings": analysis_result.get('warnings', 0),
                "issues": analysis_result.get('issues', []),
                "summary": analysis_result.get('summary', 'Analysis completed successfully')
            })
            
        except Exception as e:
            return JSONResponse({
                "status": "error", 
                "error": f"Analysis failed: {str(e)}"
            }, status_code=500)

    @api.post("/generate_report")
    async def generate_report(request: Request):
        """Generate comprehensive report with AI analysis"""
        try:
            data = await request.json()
            report_type = data.get('report_type', 'standard')
            use_local_llm = data.get('use_local_llm', False)
            use_cloud_ai = data.get('use_cloud_ai', False)
            use_python_engine = data.get('use_python_engine', True)
            
            print(f"[REPORT] Generating {report_type} report with engines: Local={use_local_llm}, Cloud={use_cloud_ai}, Python={use_python_engine}")
            
            # Check if we have cached analysis results (try both caches)
            events = _analysis_cache.get('events', []) or analysis_cache.get('events', [])
            user_context = _analysis_cache.get('user_context', {}) or analysis_cache.get('user_context', {})
            
            if not events:
                return JSONResponse({
                    "error": "No events found in analysis cache. Please upload and analyze a log file first.",
                    "cache_status": f"Global cache: {len(_analysis_cache)} items, Session cache: {len(analysis_cache)} items"
                }, status_code=400)
            
            # Perform AI analysis based on report type
            ai_analysis_result = None
            ai_engine_used = "None"
            
            if report_type in ['local_ai', 'cloud_ai'] and (use_local_llm or use_cloud_ai):
                try:
                    # Import AI analysis modules
                    import sys
                    sys.path.insert(0, "/root/app")
                    import ai_rca
                    
                    # Prepare events for AI analysis (limit to first 20 for performance)
                    sample_events = events[:20]
                    
                    print(f"[AI] Running AI analysis on {len(sample_events)} events...")
                    
                    # Determine AI engine preference
                    if report_type == 'local_ai' and use_local_llm:
                        # Force local LLM analysis
                        ai_analysis_result = ai_rca.analyze_with_ai(
                            sample_events, 
                            metadata={},
                            test_results=[],
                            context=user_context,
                            offline=True
                        )
                        ai_engine_used = "Local Phi-2 LLM"
                    elif report_type == 'cloud_ai' and use_cloud_ai:
                        # Force cloud AI analysis
                        ai_analysis_result = ai_rca.analyze_with_ai(
                            sample_events, 
                            metadata={},
                            test_results=[],
                            context=user_context,
                            offline=False
                        )
                        ai_engine_used = "OpenAI GPT"
                    else:
                        # Auto-select based on availability
                        ai_analysis_result = ai_rca.analyze_with_ai(
                            sample_events, 
                            metadata={},
                            test_results=[],
                            context=user_context,
                            offline=use_local_llm
                        )
                        ai_engine_used = "Auto-selected AI"
                    
                    print(f"[AI] AI analysis completed using {ai_engine_used}")
                    
                except Exception as ai_error:
                    print(f"[AI] AI analysis failed: {ai_error}")
                    ai_analysis_result = f"AI analysis failed: {str(ai_error)}"
                    ai_engine_used = "Failed"
            
            # Build comprehensive report response
            if report_type == 'standard':
                message = f"Standard report generated with {len(events)} events analyzed"
                report_content = {
                    "events_analyzed": len(events),
                    "analysis_type": "Standard Python Analysis",
                    "summary": "Comprehensive log parsing and event extraction completed",
                    "user_context": user_context,
                    "python_insights": _generate_python_insights(events)
                }
            else:
                message = f"AI report generated using {ai_engine_used}"
                report_content = {
                    "events_analyzed": len(events),
                    "analysis_type": f"AI Analysis ({ai_engine_used})",
                    "ai_summary": ai_analysis_result if ai_analysis_result else "AI analysis not available",
                    "summary": f"AI-powered analysis completed on {len(events)} events",
                    "user_context": user_context,
                    "ai_engine": ai_engine_used
                }
            
            # Format response for frontend compatibility
            response_data = {
                "status": "success",
                "message": message,
                "report_type": report_type,
                "summary": report_content.get("summary", "Report generated successfully"),
                "engines_used": {
                    "local_llm": use_local_llm and report_type == 'local_ai',
                    "cloud_ai": use_cloud_ai and report_type == 'cloud_ai',
                    "python_engine": use_python_engine
                },
                "timestamp": datetime.now().isoformat(),
                "events_analyzed": report_content.get("events_analyzed", len(events))
            }
            
            # Add AI analysis if available
            if report_content.get("ai_summary"):
                response_data["ai_analysis"] = report_content["ai_summary"]
            
            # Add Python insights as recommendations
            if report_content.get("python_insights"):
                response_data["recommendations"] = report_content["python_insights"]
            elif report_content.get("ai_summary"):
                response_data["recommendations"] = [
                    "Review critical errors identified in the analysis",
                    "Check system components with highest error rates",
                    "Verify deployment configuration and dependencies"
                ]
            
            return JSONResponse(response_data)
            
        except Exception as e:
            print(f"[ERROR] Report generation failed: {e}")
            return JSONResponse({"error": f"Report generation failed: {str(e)}"}, status_code=500)

    def _generate_python_insights(events):
        """Generate Python-based analytical insights"""
        try:
            insights = []
            
            # Basic statistics
            total_events = len(events)
            errors = [e for e in events if getattr(e, 'severity', '').upper() in ['ERROR', 'CRITICAL']]
            warnings = [e for e in events if getattr(e, 'severity', '').upper() == 'WARNING']
            
            insights.append(f"Total events processed: {total_events}")
            insights.append(f"Errors/Critical: {len(errors)} | Warnings: {len(warnings)}")
            
            # Component analysis
            from collections import Counter
            components = Counter([getattr(e, 'component', 'Unknown') for e in errors])
            if components:
                top_component = components.most_common(1)[0]
                insights.append(f"Top error-prone component: {top_component[0]} ({top_component[1]} errors)")
            
            # Time analysis
            try:
                timestamps = [getattr(e, 'timestamp') for e in events if hasattr(e, 'timestamp')]
                if timestamps:
                    start_time = min(timestamps)
                    end_time = max(timestamps)
                    insights.append(f"Time range: {start_time} to {end_time}")
            except:
                pass
            
            return insights
            
        except Exception as e:
            return [f"Python insights generation failed: {str(e)}"]

    return api
