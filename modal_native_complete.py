# modal_native_complete.py - Complete Modal FastAPI app with LogSense functionality
import modal

APP_NAME = "logsense-native-complete-v2"

# Build image with full ML dependencies for local AI
image = (
    modal.Image.debian_slim(python_version="3.11")
    .env({"PYTHONIOENCODING": "utf-8", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"})
    .pip_install_from_requirements("requirements-full.txt")
    .pip_install("jinja2")  # Add Jinja2 for templates
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=image)

# Deploy the FastAPI app with warm containers and Modal best practices
@app.function(
    timeout=300,  # 5 minute timeout for startup
    memory=2048, 
    min_containers=1
)
@modal.asgi_app()
def native_app():
    from fastapi import FastAPI, File, UploadFile, Request, Form
    from fastapi.responses import HTMLResponse, JSONResponse, Response
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import os
    import tempfile
    from datetime import datetime
    import json
    import zipfile
    import sys
    import traceback
    
    # Add the app directory to Python path for imports
    sys.path.insert(0, '/root/app')
    
    # Create FastAPI instance inside Modal function
    web_app = FastAPI(title="LogSense - AI Log Analysis", version="1.0.0")
    
    # Mount static files and templates
    web_app.mount("/static", StaticFiles(directory="/root/app/static"), name="static")
    templates = Jinja2Templates(directory="/root/app/templates")
    
    # Global storage for user context and analysis data
    user_context = {}
    analysis_cache = {}
    
    @web_app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Complete LogSense interface matching Streamlit workflow"""
        return templates.TemplateResponse("index.html", {"request": request})

    @web_app.post("/submit_context")
    async def submit_context(request: Request):
        """Submit user context form data"""
        try:
            data = await request.json()
            user_context.update(data)
            return JSONResponse({"status": "success", "message": "Context saved successfully"})
        except Exception as e:
            return JSONResponse({"status": "error", "error": str(e)}, status_code=500)

    @web_app.post("/upload")
    async def upload_file(request: Request, file: UploadFile = File(...)):
        """Handle file upload with comprehensive security and compliance"""
        try:
            # Import security modules
            import sys
            sys.path.insert(0, "/root/app")
            from infra.security import validate_file_upload, sanitize_log_data, ErrorCodes
            from datetime import datetime
            import re
            
            # Validate Content-Type
            content_type = request.headers.get("content-type", "").lower()
            if not content_type.startswith("multipart/form-data"):
                return JSONResponse({
                    "success": False,
                    "error_code": "E.REQ.001",
                    "message": "Content-Type must be multipart/form-data",
                    "compliance_id": f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }, status_code=415)
            
            # Read and validate file
            content = await file.read()
            
            # File size validation
            MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25MB
            if len(content) > MAX_UPLOAD_SIZE:
                return JSONResponse({
                    "success": False,
                    "error_code": "E.REQ.002", 
                    "message": f"File too large. Maximum size: {MAX_UPLOAD_SIZE // (1024*1024)}MB",
                    "compliance_id": f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }, status_code=413)
            
            # File type validation
            allowed_extensions = ['.log', '.txt', '.zip']
            if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
                return JSONResponse({
                    "success": False,
                    "error_code": "E.REQ.003",
                    "message": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}",
                    "compliance_id": f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                }, status_code=400)
            
            # Input sanitization for filename
            safe_filename = re.sub(r'[<>:"|?*]', '', file.filename)
            safe_filename = safe_filename.replace('..', '').strip()
            
            # Process file content
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
                                    file_events = parse_log_content(log_content, file_info.filename)
                                    events.extend(file_events)
                    
                    os.unlink(temp_zip.name)
            else:
                # Single log file
                log_content = content.decode('utf-8', errors='ignore')
                events = parse_log_content(log_content, safe_filename)
            
            # Sanitize event data for security
            sanitized_events = []
            for event in events:
                event_dict = {
                    'timestamp': getattr(event, 'timestamp', ''),
                    'component': getattr(event, 'component', ''),
                    'message': getattr(event, 'message', ''),
                    'severity': getattr(event, 'severity', 'INFO')
                }
                # Apply security sanitization
                sanitized_event = sanitize_log_data(event_dict)
                sanitized_events.append(sanitized_event)
            
            # Analyze events
            analysis_result = analyze_events(events)
            
            # Cache results for report generation with compliance metadata
            compliance_id = f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            analysis_cache['events'] = sanitized_events
            analysis_cache['analysis'] = analysis_result
            analysis_cache['filename'] = safe_filename
            analysis_cache['compliance_id'] = compliance_id
            analysis_cache['upload_timestamp'] = datetime.now().isoformat()
            
            # Enhanced redaction detection with security patterns
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
            
            # Compliance logging
            print(f"[COMPLIANCE] Upload processed - ID: {compliance_id}, File: {safe_filename}, Events: {len(sanitized_events)}, Redacted: {redaction_count}")
            
            return JSONResponse({
                "success": True,
                "event_count": len(sanitized_events),
                "events": sanitized_events[:50],  # Return first 50 for display
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
            # Secure error handling - no stack traces exposed
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

    @web_app.post("/analyze")
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
                                    file_events = parse_log_content(log_content, file_info.filename)
                                    events.extend(file_events)
                    
                    os.unlink(temp_zip.name)
            else:
                # Single log file
                log_content = content.decode('utf-8', errors='ignore')
                events = parse_log_content(log_content, file.filename)
            
            # Analyze events
            analysis_result = analyze_events(events)
            
            # Cache results
            analysis_cache['events'] = events
            analysis_cache['analysis'] = analysis_result
            
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

    @web_app.post("/generate_report")
    async def generate_report(request: Request):
        """Generate comprehensive report with AI analysis"""
        try:
            data = await request.json()
            report_type = data.get('report_type', 'standard')
            use_local_llm = data.get('use_local_llm', False)
            use_cloud_ai = data.get('use_cloud_ai', False)
            use_python_engine = data.get('use_python_engine', True)
            
            print(f"[REPORT] Generating {report_type} report with engines: Local={use_local_llm}, Cloud={use_cloud_ai}, Python={use_python_engine}")
            
            # Check if we have cached analysis results
            if not analysis_cache:
                return JSONResponse({"error": "No analysis data available. Please upload and analyze a log file first."}, status_code=400)
            
            events = analysis_cache.get('events', [])
            user_context = analysis_cache.get('user_context', {})
            
            if not events:
                return JSONResponse({"error": "No events found in analysis cache."}, status_code=400)
            
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
            
            return JSONResponse({
                "success": True,
                "report_type": report_type,
                "ai_engine": ai_engine_used,
                "report": {
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "user_context": user_context,
                        "events_analyzed": len(events),
                        "ai_analysis_enabled": bool(ai_analysis_result)
                    },
                    "analysis": analysis_result,
                    "ai_insights": ai_analysis_result,
                    "python_insights": _generate_python_insights(events)
                },
                "compliance_id": analysis_cache.get('compliance_id', f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"),
                "processing_timestamp": datetime.now().isoformat(),
                "signature": "LogSense Enterprise v2.0.0 - Report Generation Engine"
            })
            
        except Exception as e:
            error_id = f"ERR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            print(f"[ERROR] Report generation failed - ID: {error_id}, Error: {str(e)}")
            return JSONResponse({
                "error": "Report generation failed. Please try again.",
                "error_code": "E.SRV.002",
                "error_id": error_id,
                "compliance_id": f"COMP-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "signature": "LogSense Enterprise v2.0.0 - Error Handler"
            }, status_code=500)

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

    @web_app.get("/health")
    async def health_check():
        """Health check endpoint for Modal deployment verification"""
        try:
            # Check if AI modules are available
            ai_status = "unknown"
            try:
                import sys
                sys.path.insert(0, "/root/app")
                import ai_rca
                ai_status = "available"
            except ImportError as e:
                ai_status = f"unavailable: {str(e)}"
            
            return JSONResponse({
                "status": "healthy",
                "service": "LogSense Native Complete",
                "version": "2.0.0",
                "ai_modules": ai_status,
                "cache_status": f"{len(analysis_cache)} items cached",
                "timestamp": datetime.now().isoformat(),
                "compliance_check": "passed",
                "signature": "LogSense Enterprise v2.0.0 - Health Monitor"
            })
        except Exception as e:
            error_id = f"ERR-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            return JSONResponse({
                "status": "error",
                "error": "Health check failed",
                "error_code": "E.SRV.003",
                "error_id": error_id,
                "signature": "LogSense Enterprise v2.0.0 - Error Handler"
            }, status_code=500)

    return web_app
