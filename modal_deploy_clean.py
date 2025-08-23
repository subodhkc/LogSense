# modal_deploy_clean.py - Clean Modal deployment without encoding issues
import modal
import os

APP_NAME = "logsense-enterprise"

# Minimal image to avoid encoding issues
image = (
    modal.Image.debian_slim(python_version="3.11")
    .env({
        "PYTHONIOENCODING": "utf-8", 
        "LC_ALL": "C.UTF-8", 
        "LANG": "C.UTF-8",
        "PYTHONPATH": "/root/app"
    })
    .pip_install([
        "fastapi>=0.100.0",
        "jinja2>=3.1.0",
        "python-multipart>=0.0.6",
        "uvicorn>=0.20.0"
    ])
    .add_local_file("templates/index.html", remote_path="/root/app/templates/index.html")
    .add_local_file("static/styles.css", remote_path="/root/app/static/styles.css")
    .add_local_file("static/app.js", remote_path="/root/app/static/app.js")
)

app = modal.App(name=APP_NAME, image=image)

@app.function(
    timeout=120,
    memory=1024,
    min_containers=1
)
@modal.asgi_app()
def enterprise_app():
    from fastapi import FastAPI, File, UploadFile, Request, Form
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    import tempfile
    import json
    import zipfile
    import re
    from datetime import datetime
    
    # Create FastAPI instance
    web_app = FastAPI(title="LogSense Enterprise - AI Log Analysis", version="2.0.0")
    
    # Mount static files and templates
    web_app.mount("/static", StaticFiles(directory="/root/app/static"), name="static")
    templates = Jinja2Templates(directory="/root/app/templates")
    
    # Global storage
    user_context = {}
    analysis_cache = {}
    
    # Helper functions for log parsing
    def extract_timestamp(line: str):
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
        line_upper = line.upper()
        levels = ['ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'TRACE']
        for level in levels:
            if level in line_upper:
                return level
        return 'INFO'
    
    def parse_log_content(content: str, filename: str):
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
    
    def analyze_events(events):
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
    
    @web_app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})
    
    @web_app.post("/submit_context")
    async def submit_context(request: Request):
        try:
            form_data = await request.form()
            user_context.update({
                "user_name": form_data.get("userName", ""),
                "app_name": form_data.get("appName", ""),
                "issue_description": form_data.get("issueDescription", ""),
                "test_environment": form_data.get("testEnvironment", ""),
                "deployment_method": form_data.get("deploymentMethod", ""),
                "previous_version": form_data.get("previousVersion", ""),
                "hw_model": form_data.get("hwModel", ""),
                "os_build": form_data.get("osBuild", ""),
                "timestamp": datetime.now().isoformat()
            })
            return JSONResponse({"status": "success", "message": "Context saved successfully"})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    
    @web_app.post("/analyze")
    async def analyze_logs(file: UploadFile = File(...)):
        try:
            # Read file content
            content = await file.read()
            
            # Handle different file types
            if file.filename.endswith('.zip'):
                # Process ZIP file
                with tempfile.NamedTemporaryFile() as temp_file:
                    temp_file.write(content)
                    temp_file.flush()
                    
                    events = []
                    with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
                        for file_info in zip_ref.filelist:
                            if not file_info.is_dir() and file_info.filename.endswith(('.log', '.txt', '.out')):
                                file_content = zip_ref.read(file_info.filename).decode('utf-8', errors='ignore')
                                file_events = parse_log_content(file_content, file_info.filename)
                                events.extend(file_events)
            else:
                # Process single file
                text_content = content.decode('utf-8', errors='ignore')
                events = parse_log_content(text_content, file.filename)
            
            # Analyze events
            analysis_result = analyze_events(events)
            
            # Cache results
            analysis_cache['events'] = events[:100]  # Limit for performance
            analysis_cache['analysis'] = analysis_result
            analysis_cache['filename'] = file.filename
            
            # Return analysis results
            return JSONResponse({
                "status": "success",
                "total_events": len(events),
                "critical_errors": analysis_result["critical_errors"],
                "warnings": analysis_result["warnings"],
                "issues": analysis_result["issues"],
                "summary": analysis_result["summary"],
                "sample_events": events[:10]  # First 10 events for preview
            })
            
        except Exception as e:
            return JSONResponse({"status": "error", "message": f"Analysis failed: {str(e)}"}, status_code=500)
    
    @web_app.get("/ml_analysis")
    async def ml_analysis():
        try:
            # Mock ML analysis results
            return JSONResponse({
                "status": "success",
                "clustering": {
                    "clusters": [
                        {"name": "Authentication Errors", "count": 15, "severity": "high"},
                        {"name": "Network Timeouts", "count": 8, "severity": "medium"},
                        {"name": "Database Warnings", "count": 23, "severity": "low"}
                    ]
                },
                "anomalies": [
                    {"timestamp": "2024-01-15 14:30:22", "description": "Unusual error spike detected", "severity": "high"},
                    {"timestamp": "2024-01-15 15:45:10", "description": "Memory usage anomaly", "severity": "medium"}
                ],
                "predictions": {
                    "next_failure_probability": 0.23,
                    "recommended_actions": ["Check authentication service", "Monitor network connectivity"]
                }
            })
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    
    @web_app.post("/generate_report")
    async def generate_report(request: Request):
        try:
            form_data = await request.form()
            report_type = form_data.get("reportType", "standard")
            
            # Generate mock report
            report_data = {
                "status": "success",
                "report_type": report_type,
                "generated_at": datetime.now().isoformat(),
                "user_context": user_context,
                "analysis_summary": analysis_cache.get('analysis', {}),
                "recommendations": [
                    "Review authentication service configuration",
                    "Implement better error handling for network timeouts",
                    "Consider database query optimization"
                ]
            }
            
            return JSONResponse(report_data)
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    
    @web_app.get("/health")
    async def health_check():
        return JSONResponse({
            "status": "healthy",
            "service": "LogSense Enterprise",
            "version": "2.0.0",
            "features": {
                "file_upload": True,
                "log_analysis": True,
                "enterprise_ui": True,
                "report_generation": True
            },
            "cache_info": {
                "events_cached": len(analysis_cache.get('events', [])),
                "context_set": bool(user_context)
            }
        })
    
    return web_app
