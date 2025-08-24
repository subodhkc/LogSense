# modal_webserver.py - Windows-compatible Modal deployment using @modal.web_server
import modal
import os
import sys
import tempfile
import zipfile
from datetime import datetime
import json

APP_NAME = "logsense-webserver"

# Build image with dependencies - using modal.txt for lighter startup
image = (
    modal.Image.debian_slim(python_version="3.11")
    .env({"PYTHONIOENCODING": "utf-8", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"})
    .pip_install_from_requirements("requirements-modal.txt")
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=image)

# Global cache for analysis results
_analysis_cache = {}

@app.function(
    timeout=300,
    memory=2048,
    min_containers=1
)
@modal.web_server(port=8000, startup_timeout=300)
def run_webserver():
    from fastapi import FastAPI, File, UploadFile, Request, Form
    from fastapi.responses import HTMLResponse, JSONResponse, Response
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import traceback
    
    # Change to app directory
    os.chdir("/root/app")
    sys.path.insert(0, '/root/app')
    
    # Create FastAPI instance
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
            _analysis_cache['events'] = events
            _analysis_cache['analysis'] = analysis_result
            _analysis_cache['user_context'] = user_context
            
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
            if not _analysis_cache:
                return JSONResponse({"error": "No analysis data available. Please upload and analyze a log file first."}, status_code=400)
            
            events = _analysis_cache.get('events', [])
            user_context = _analysis_cache.get('user_context', {})
            
            if not events:
                return JSONResponse({"error": "No events found in analysis cache."}, status_code=400)
            
            # Perform AI analysis based on report type
            ai_analysis_result = None
            ai_engine_used = "None"
            
            if report_type in ['local_ai', 'cloud_ai'] and (use_local_llm or use_cloud_ai):
                try:
                    # Import AI analysis modules
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

    @web_app.get("/health")
    async def health_check():
        """Health check endpoint for Modal deployment verification"""
        try:
            # Check if AI modules are available
            ai_status = "unknown"
            try:
                import ai_rca
                ai_status = "available"
            except ImportError as e:
                ai_status = f"unavailable: {str(e)}"
            
            return JSONResponse({
                "status": "healthy",
                "service": "LogSense WebServer",
                "version": "2.0.0",
                "ai_modules": ai_status,
                "cache_status": f"{len(_analysis_cache)} items cached",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return JSONResponse({
                "status": "error",
                "error": str(e)
            }, status_code=500)

    # Helper functions
    def parse_log_content(content: str, filename: str):
        """Parse log content into structured events"""
        events = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if line.strip():
                event = {
                    "line_number": i + 1,
                    "content": line.strip(),
                    "filename": filename,
                    "timestamp": extract_timestamp(line),
                    "level": extract_log_level(line),
                    "message": line.strip()
                }
                events.append(event)
        
        return events

    def extract_timestamp(line: str):
        """Extract timestamp from log line"""
        import re
        patterns = [
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
            r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',
            r'\d{2}:\d{2}:\d{2}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line)
            if match:
                return match.group()
        return None

    def extract_log_level(line: str):
        """Extract log level from line"""
        line_upper = line.upper()
        levels = ['ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'TRACE']
        
        for level in levels:
            if level in line_upper:
                return level
        return 'INFO'

    def analyze_events(events):
        """Analyze events for issues and patterns"""
        issues = []
        error_count = 0
        warning_count = 0
        
        for event in events:
            level = event.get('level', '').upper()
            if 'ERROR' in level:
                error_count += 1
                issues.append({
                    "type": "Error",
                    "description": event.get('message', ''),
                    "line": event.get('line_number', 0)
                })
            elif 'WARN' in level:
                warning_count += 1
        
        return {
            "issues": issues[:20],
            "critical_errors": error_count,
            "warnings": warning_count,
            "summary": f"Found {error_count} errors and {warning_count} warnings in {len(events)} events"
        }

    return web_app
