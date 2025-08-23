# modal_windows_safe.py - Windows encoding safe Modal deployment
import modal

APP_NAME = "logsense-enterprise-safe"

# Minimal dependencies to avoid encoding issues
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install([
        "fastapi",
        "jinja2", 
        "python-multipart",
        "uvicorn"
    ])
)

app = modal.App(name=APP_NAME, image=image)

@app.function(
    timeout=120,
    memory=1024,
    min_containers=1
)
@modal.asgi_app()
def safe_app():
    from fastapi import FastAPI, File, UploadFile, Request, Form
    from fastapi.responses import HTMLResponse, JSONResponse
    import tempfile
    import json
    import zipfile
    import re
    from datetime import datetime
    
    # Create FastAPI instance
    web_app = FastAPI(title="LogSense Enterprise", version="2.0.0")
    
    # Global storage
    user_context = {}
    analysis_cache = {}
    
    # Helper functions
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
    
    # Enterprise UI HTML template with Windows-safe characters only
    ENTERPRISE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LogSense Enterprise - AI Log Analysis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
            min-height: 100vh; 
            color: #333;
            line-height: 1.6;
        }
        
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
        }
        
        .header { 
            text-align: center; 
            color: white; 
            margin-bottom: 40px; 
            padding: 30px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }
        
        .header h1 { 
            font-size: 3.5em; 
            margin-bottom: 15px; 
            font-weight: 300;
        }
        
        .header p { 
            opacity: 0.9; 
            font-size: 1.2em; 
        }
        
        .main-section { 
            background: white; 
            padding: 40px; 
            border-radius: 15px; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.1); 
            margin-bottom: 30px;
        }
        
        .section-title {
            color: #2c3e50;
            font-size: 2em;
            font-weight: 600;
            margin-bottom: 30px;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
        }
        
        .form-group { 
            margin-bottom: 25px; 
        }
        
        .form-group label { 
            display: block; 
            margin-bottom: 8px; 
            font-weight: 600; 
            color: #34495e;
        }
        
        .form-group input, .form-group textarea { 
            width: 100%; 
            padding: 15px; 
            border: 2px solid #e0e6ed; 
            border-radius: 8px; 
            font-size: 16px;
            transition: all 0.3s ease;
            background: #f8f9fa;
        }
        
        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #3498db;
            background: white;
            box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
        }
        
        .upload-area { 
            background: linear-gradient(135deg, #f8f9fa, #ffffff); 
            padding: 50px; 
            border-radius: 15px; 
            border: 3px dashed #3498db; 
            text-align: center; 
            transition: all 0.4s ease;
            cursor: pointer;
        }
        
        .upload-area:hover { 
            border-color: #27ae60; 
            background: linear-gradient(135deg, #f0fff4, #e8f5e8);
            transform: translateY(-5px);
        }
        
        .upload-icon {
            font-size: 4em;
            color: #3498db;
            margin-bottom: 20px;
            font-weight: bold;
        }
        
        .btn { 
            background: linear-gradient(135deg, #3498db, #2980b9); 
            color: white; 
            padding: 15px 30px; 
            border: none; 
            border-radius: 8px; 
            cursor: pointer; 
            font-size: 16px; 
            font-weight: 600;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .btn:hover { 
            background: linear-gradient(135deg, #2980b9, #1f5f8b);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(52, 152, 219, 0.3);
        }
        
        .btn-success { 
            background: linear-gradient(135deg, #27ae60, #229954);
        }
        
        .btn-success:hover { 
            background: linear-gradient(135deg, #229954, #1e8449);
        }
        
        .results-section {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            margin-top: 30px;
            display: none;
        }
        
        .metric-cards { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 25px; 
            margin: 30px 0; 
        }
        
        .metric-card { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 30px; 
            border-radius: 15px; 
            text-align: center;
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            transform: translateY(-10px);
            box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
        }
        
        .metric-card h3 { 
            font-size: 2.5em; 
            margin-bottom: 10px;
            font-weight: 700;
        }
        
        .metric-card p { 
            font-size: 1.2em;
            opacity: 0.95;
        }
        
        .status-success { color: #27ae60; font-weight: 600; }
        .status-error { color: #e74c3c; font-weight: 600; }
        .status-warning { color: #f39c12; font-weight: 600; }
        
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2em;
            color: #7f8c8d;
        }
        
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            display: inline-block;
            margin-right: 15px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .hidden { display: none; }
        
        @media (max-width: 768px) {
            .container { padding: 15px; }
            .header h1 { font-size: 2.5em; }
            .main-section { padding: 25px; }
            .metric-cards { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LogSense Enterprise</h1>
            <p>Professional AI-Powered Log Analysis Platform</p>
            <p>Advanced Analytics | Enterprise Security | Real-time Insights</p>
        </div>
        
        <div class="main-section">
            <h2 class="section-title">User Information</h2>
            <form id="contextForm">
                <div class="form-group">
                    <label for="userName">Your Name *</label>
                    <input type="text" id="userName" placeholder="Enter your full name" required>
                </div>
                <div class="form-group">
                    <label for="appName">Application Being Tested *</label>
                    <input type="text" id="appName" placeholder="Application or system name" required>
                </div>
                <div class="form-group">
                    <label for="issueDescription">Issue Description *</label>
                    <textarea id="issueDescription" rows="4" placeholder="Describe the problem you're experiencing..." required></textarea>
                </div>
                <button type="submit" class="btn">Save Context</button>
            </form>
        </div>
        
        <div class="main-section" id="uploadSection" style="display: none;">
            <h2 class="section-title">Log File Upload</h2>
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">UPLOAD</div>
                <h3>Upload Log Files</h3>
                <p>Drag and drop your log file or ZIP archive here</p>
                <p style="margin-top: 15px; color: #7f8c8d;">Supported: .log, .txt, .out, .zip</p>
                <input type="file" id="fileInput" accept=".log,.txt,.out,.zip" style="display: none;">
            </div>
            <button type="button" class="btn btn-success" id="analyzeBtn" style="display: none; margin-top: 20px;">
                Analyze Logs
            </button>
        </div>
        
        <div class="results-section" id="resultsSection">
            <h2 class="section-title">Analysis Results</h2>
            <div id="loadingIndicator" class="loading">
                <div class="spinner"></div>
                Analyzing your log files...
            </div>
            <div id="metricsContainer" class="hidden">
                <div class="metric-cards" id="metricCards"></div>
                <div id="analysisDetails"></div>
            </div>
        </div>
    </div>
    
    <script>
        let selectedFile = null;
        
        document.getElementById('contextForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData();
            formData.append('userName', document.getElementById('userName').value);
            formData.append('appName', document.getElementById('appName').value);
            formData.append('issueDescription', document.getElementById('issueDescription').value);
            
            try {
                const response = await fetch('/submit_context', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    document.getElementById('uploadSection').style.display = 'block';
                    document.querySelector('#contextForm button').textContent = 'Context Saved!';
                    document.querySelector('#contextForm button').style.background = 'linear-gradient(135deg, #27ae60, #229954)';
                }
            } catch (error) {
                alert('Error saving context: ' + error.message);
            }
        });
        
        document.getElementById('fileInput').addEventListener('change', (e) => {
            selectedFile = e.target.files[0];
            if (selectedFile) {
                document.querySelector('.upload-area h3').textContent = 'File Selected: ' + selectedFile.name;
                document.getElementById('analyzeBtn').style.display = 'block';
            }
        });
        
        document.getElementById('analyzeBtn').addEventListener('click', async () => {
            if (!selectedFile) return;
            
            document.getElementById('resultsSection').style.display = 'block';
            document.getElementById('loadingIndicator').style.display = 'block';
            document.getElementById('metricsContainer').classList.add('hidden');
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    displayResults(result);
                } else {
                    throw new Error(result.message);
                }
            } catch (error) {
                document.getElementById('loadingIndicator').innerHTML = 
                    '<div class="status-error">Analysis failed: ' + error.message + '</div>';
            }
        });
        
        function displayResults(data) {
            document.getElementById('loadingIndicator').style.display = 'none';
            document.getElementById('metricsContainer').classList.remove('hidden');
            
            const metricsHtml = `
                <div class="metric-card">
                    <h3>${data.total_events}</h3>
                    <p>Total Events</p>
                </div>
                <div class="metric-card">
                    <h3>${data.critical_errors}</h3>
                    <p>Critical Errors</p>
                </div>
                <div class="metric-card">
                    <h3>${data.warnings}</h3>
                    <p>Warnings</p>
                </div>
                <div class="metric-card">
                    <h3>${data.issues.length}</h3>
                    <p>Issues Found</p>
                </div>
            `;
            
            document.getElementById('metricCards').innerHTML = metricsHtml;
            
            let detailsHtml = '<h3>Analysis Summary</h3><p>' + data.summary + '</p>';
            
            if (data.issues.length > 0) {
                detailsHtml += '<h3 style="margin-top: 30px;">Top Issues</h3>';
                data.issues.slice(0, 5).forEach(issue => {
                    detailsHtml += `
                        <div style="background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #e74c3c;">
                            <strong>Line ${issue.line}:</strong> ${issue.description}
                        </div>
                    `;
                });
            }
            
            document.getElementById('analysisDetails').innerHTML = detailsHtml;
        }
    </script>
</body>
</html>'''
    
    @web_app.get("/", response_class=HTMLResponse)
    async def home():
        return HTMLResponse(content=ENTERPRISE_HTML)
    
    @web_app.post("/submit_context")
    async def submit_context(request: Request):
        try:
            form_data = await request.form()
            user_context.update({
                "user_name": form_data.get("userName", ""),
                "app_name": form_data.get("appName", ""),
                "issue_description": form_data.get("issueDescription", ""),
                "timestamp": datetime.now().isoformat()
            })
            return JSONResponse({"status": "success", "message": "Context saved"})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    
    @web_app.post("/analyze")
    async def analyze_logs(file: UploadFile = File(...)):
        try:
            content = await file.read()
            
            if file.filename.endswith('.zip'):
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
                text_content = content.decode('utf-8', errors='ignore')
                events = parse_log_content(text_content, file.filename)
            
            analysis_result = analyze_events(events)
            analysis_cache['events'] = events[:100]
            analysis_cache['analysis'] = analysis_result
            
            return JSONResponse({
                "status": "success",
                "total_events": len(events),
                "critical_errors": analysis_result["critical_errors"],
                "warnings": analysis_result["warnings"],
                "issues": analysis_result["issues"],
                "summary": analysis_result["summary"]
            })
            
        except Exception as e:
            return JSONResponse({"status": "error", "message": f"Analysis failed: {str(e)}"}, status_code=500)
    
    @web_app.get("/health")
    async def health_check():
        return JSONResponse({
            "status": "healthy",
            "service": "LogSense Enterprise",
            "version": "2.0.0",
            "features": {
                "enterprise_ui": True,
                "log_analysis": True,
                "windows_compatible": True
            }
        })
    
    return web_app
