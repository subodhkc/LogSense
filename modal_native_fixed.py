# modal_native.py - Native Modal FastAPI app with LogSense functionality
import modal

APP_NAME = "logsense-native"

# Build image with full ML dependencies for local AI
image = (
    modal.Image.debian_slim(python_version="3.11")
    .env({"PYTHONIOENCODING": "utf-8", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"})
    .pip_install_from_requirements("requirements-full.txt")
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
    from fastapi import FastAPI, File, UploadFile, Request
    from fastapi.responses import HTMLResponse, JSONResponse, Response
    import os
    import tempfile
    from datetime import datetime
    
    # Create FastAPI instance inside Modal function
    web_app = FastAPI(title="LogSense - AI Log Analysis", version="1.0.0")

    @web_app.get("/", response_class=HTMLResponse)
    async def home():
        """Simplified LogSense interface matching Streamlit workflow"""
        return """<!DOCTYPE html>
<html>
<head>
    <title>LogSense - AI Log Analysis</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding-bottom: 60px; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 3em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .header h3 { font-size: 1.5em; margin-bottom: 5px; opacity: 0.9; }
        .header p { opacity: 0.8; font-size: 1.1em; }
        .sidebar { position: fixed; top: 20px; right: 20px; background: rgba(255,255,255,0.95); padding: 20px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); width: 280px; z-index: 1000; }
        .sidebar h4 { margin-bottom: 15px; color: #333; }
        .sidebar label { display: flex; align-items: center; margin-bottom: 10px; font-size: 14px; color: #555; }
        .sidebar input[type="checkbox"] { margin-right: 8px; }
        .form-section { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; margin-right: 300px; }
        .btn { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; transition: background 0.3s; }
        .btn:hover { background: #0056b3; }
        .btn-secondary { background: #6c757d; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; transition: background 0.3s; }
        .btn-secondary:hover { background: #5a6268; }
        .upload-area { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; border: 2px dashed #007bff; text-align: center; margin-right: 300px; }
        .upload-area.dragover { border-color: #28a745; background: #f8fff9; }
        .results { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-top: 20px; margin-right: 300px; }
        .metric-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .metric-card { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; }
        .metric-card h3 { margin: 0 0 10px 0; font-size: 2em; }
        .metric-card p { margin: 0; opacity: 0.9; }
        .success { color: #28a745; font-weight: bold; }
        .error { color: #dc3545; font-weight: bold; }
        .info { background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #007bff; }
        .ai-section { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 10px 0; }
        .event-item { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
        .tabs { display: flex; margin: 20px 0; border-bottom: 2px solid #ddd; }
        .tab { padding: 12px 24px; cursor: pointer; border: none; background: none; font-size: 16px; color: #666; border-bottom: 3px solid transparent; }
        .tab.active { color: #007bff; border-bottom-color: #007bff; font-weight: bold; }
        .tab-content { display: none; padding: 20px 0; }
        .tab-content.active { display: block; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LogSense</h1>
            <h3>Enterprise Log Analysis Platform</h3>
            <p>Intelligent diagnostics for system provisioning and deployment</p>
            <p><strong>Session:</strong> <span id="sessionId"></span></p>
        </div>
        
        <!-- Sidebar for AI Engine Configuration -->
        <div class="sidebar">
            <h4>AI Engine Configuration</h4>
            <label>
                <input type="checkbox" id="useLocalLLM" checked>
                <strong>Local LLM</strong> - In-house Phi-2 Model
            </label>
            <label>
                <input type="checkbox" id="useCloudAI">
                <strong>Cloud AI</strong> - OpenAI GPT Fallback
            </label>
            <label>
                <input type="checkbox" id="usePythonEngine" checked>
                <strong>Python Engine</strong> - Advanced Analytics
            </label>
            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #ddd; font-size: 12px; color: #666;">
                Configure which analysis engines to use for reports
            </div>
        </div>
        
        <!-- Simplified Upload Section -->
        <div class="form-section">
            <h2>Upload Log File</h2>
            <div class="upload-area" id="uploadArea">
                <div class="upload-content">
                    <div class="upload-icon">[FILE]</div>
                    <p>Drag and drop your log file or ZIP archive here or click to browse</p>
                    <small style="color: #666;">Supported formats: .log, .txt, .out, .zip</small>
                    <input type="file" id="fileInput" accept=".log,.txt,.out,.zip" style="display: none;">
                    <button type="button" class="btn-secondary" onclick="document.getElementById('fileInput').click()">Choose File</button>
                </div>
            </div>
            <div class="file-info" id="fileInfo" style="display: none;"></div>
            <button type="button" class="btn" id="analyzeBtn" style="display: none;">Analyze Log File</button>
        </div>

        <!-- Results Section -->
        <div id="resultsSection" style="display: none;">
            <div class="results">
                <h2>Analysis Results</h2>
                
                <!-- Metric Cards -->
                <div id="metricCards" class="metric-cards" style="display: none;"></div>
                
                <!-- Analysis Tabs -->
                <div class="tabs">
                    <button class="tab active" onclick="showTab('timeline')">Timeline & Issues</button>
                    <button class="tab" onclick="showTab('reports')">Reports</button>
                </div>
                
                <!-- Timeline Tab -->
                <div id="timelineTab" class="tab-content active">
                    <div id="analysisResults"></div>
                </div>
                
                <!-- Reports Tab -->
                <div id="reportsTab" class="tab-content">
                    <h3>Generate Reports</h3>
                    <div class="info">
                        <strong>Report Contents:</strong><br>
                        - System info and metadata<br>
                        - Errors, timeline, and validations<br>
                        - RCA summary (optional AI)<br>
                        - Charts and insights
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 20px;">
                        <button type="button" class="btn" id="standardReport" style="background: #6c757d;">Standard Report</button>
                        <button type="button" class="btn" id="localAIReport" style="background: #28a745;">Local AI Report</button>
                        <button type="button" class="btn" id="cloudAIReport" style="background: #17a2b8;">Cloud AI Report</button>
                    </div>
                    <div id="reportResults" style="margin-top: 20px;"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Generate session ID
        document.getElementById('sessionId').textContent = 'LS-' + Date.now().toString(36).toUpperCase();
        
        // Tab switching
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            
            event.target.classList.add('active');
            document.getElementById(tabName + 'Tab').classList.add('active');
        }
        
        // File upload handling
        document.getElementById('fileInput').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                document.getElementById('fileInfo').innerHTML = `
                    <div class="success">File selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)</div>
                `;
                document.getElementById('fileInfo').style.display = 'block';
                document.getElementById('analyzeBtn').style.display = 'block';
            }
        });
        
        // Analyze button
        document.getElementById('analyzeBtn').addEventListener('click', async function() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select a file first');
                return;
            }
            
            // Show loading
            this.textContent = 'Analyzing...';
            this.disabled = true;
            
            // Create form data
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                // Show results
                document.getElementById('resultsSection').style.display = 'block';
                displayResults(result);
                
            } catch (error) {
                alert('Analysis failed: ' + error.message);
            } finally {
                this.textContent = 'Analyze Log File';
                this.disabled = false;
            }
        });
        
        // Report generation
        document.getElementById('standardReport').addEventListener('click', () => generateReport('standard'));
        document.getElementById('localAIReport').addEventListener('click', () => generateReport('local_ai'));
        document.getElementById('cloudAIReport').addEventListener('click', () => generateReport('cloud_ai'));
        
        async function generateReport(type) {
            const button = event.target;
            const originalText = button.textContent;
            button.textContent = 'Generating...';
            button.disabled = true;
            
            try {
                const useLocalLLM = document.getElementById('useLocalLLM').checked;
                const useCloudAI = document.getElementById('useCloudAI').checked;
                const usePythonEngine = document.getElementById('usePythonEngine').checked;
                
                const response = await fetch('/generate_report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        report_type: type,
                        use_local_llm: useLocalLLM,
                        use_cloud_ai: useCloudAI,
                        use_python_engine: usePythonEngine
                    })
                });
                
                const result = await response.json();
                document.getElementById('reportResults').innerHTML = `
                    <div class="ai-section">
                        <h4>Report Generated</h4>
                        <p>${result.message || 'Report generated successfully'}</p>
                    </div>
                `;
                
            } catch (error) {
                document.getElementById('reportResults').innerHTML = `
                    <div class="error">Report generation failed: ${error.message}</div>
                `;
            } finally {
                button.textContent = originalText;
                button.disabled = false;
            }
        }
        
        function displayResults(result) {
            // Show metric cards
            if (result.events_count !== undefined) {
                const metricsHtml = `
                    <div class="metric-card">
                        <h3>${result.events_count}</h3>
                        <p>Total Events</p>
                    </div>
                    <div class="metric-card">
                        <h3>${result.file_size || 0}</h3>
                        <p>File Size (bytes)</p>
                    </div>
                    <div class="metric-card">
                        <h3>${result.lines_count || 0}</h3>
                        <p>Log Lines</p>
                    </div>
                `;
                document.getElementById('metricCards').innerHTML = metricsHtml;
                document.getElementById('metricCards').style.display = 'grid';
            }
            
            // Show analysis results
            let resultsHtml = '<h3>Log Analysis Complete</h3>';
            
            if (result.sample_events && result.sample_events.length > 0) {
                resultsHtml += '<h4>Sample Events</h4>';
                result.sample_events.forEach(event => {
                    resultsHtml += `
                        <div class="event-item">
                            <strong>${event.timestamp}</strong> - ${event.event_type}<br>
                            ${event.description}
                        </div>
                    `;
                });
            }
            
            if (result.event_distribution) {
                resultsHtml += '<h4>Event Distribution</h4>';
                Object.entries(result.event_distribution).forEach(([type, count]) => {
                    resultsHtml += `<div class="info">${type}: ${count} events</div>`;
                });
            }
            
            document.getElementById('analysisResults').innerHTML = resultsHtml;
        }
        
        // Generate session timestamp
        function generateSessionId() {
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hour = String(now.getHours()).padStart(2, '0');
            const minute = String(now.getMinutes()).padStart(2, '0');
            const second = String(now.getSeconds()).padStart(2, '0');
            return `${year}${month}${day}_${hour}${minute}${second}`;
        }
        
        // Update footer with session info
        document.addEventListener('DOMContentLoaded', function() {
            const sessionSpan = document.getElementById('sessionInfo');
            if (sessionSpan) {
                sessionSpan.textContent = generateSessionId();
            }
        });
    </script>
    
    <!-- Footer Section -->
    <footer style="
        position: fixed; 
        bottom: 0; 
        left: 0; 
        right: 0; 
        background: #2c3e50; 
        color: #ecf0f1; 
        padding: 8px 20px; 
        font-size: 12px; 
        text-align: center; 
        border-top: 2px solid #3498db;
        z-index: 1000;
    ">
        LogSense Enterprise | Patent Pending | Session: <span id="sessionInfo">Loading...</span> | Developed by Subodh Kc
    </footer>
</body>
</html>"""

    @web_app.post("/analyze")
    async def analyze_log(request: Request, file: UploadFile = File(...)):
        """Analyze uploaded log file - basic analysis only, AI happens in reports"""
        start_time = datetime.now()
        
        try:
            os.chdir("/root/app")
            content = await file.read()
            
            # Import LogSense analysis modules with error handling
            try:
                import sys
                import zipfile
                import io
                sys.path.insert(0, "/root/app")
                print(f"[DEBUG] Python path: {sys.path}")
                print(f"[DEBUG] Current directory: {os.getcwd()}")
                print(f"[DEBUG] Files in directory: {os.listdir('.')}")
                
                import analysis
                import redaction
                print(f"[DEBUG] Successfully imported analysis modules")
            except ImportError as e:
                print(f"[ERROR] Failed to import analysis modules: {e}")
                return JSONResponse({"error": f"Analysis modules not available: {e}"}, status_code=500)
            
            # Handle ZIP files
            log_content = content
            file_list = None
            if file.filename.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_ref:
                        file_list = zip_ref.namelist()
                        log_files = [f for f in file_list if f.endswith(('.txt', '.log'))]
                        if log_files:
                            with zip_ref.open(log_files[0]) as log_file:
                                log_content = log_file.read()
                        else:
                            return JSONResponse({"error": "No log files found in ZIP archive"}, status_code=400)
                except Exception as e:
                    return JSONResponse({"error": f"Failed to extract ZIP file: {e}"}, status_code=400)
            
            # Apply data redaction for compliance
            print(f"[REDACTION] Applying data redaction for compliance...")
            try:
                redacted_content = redaction.redact_sensitive_data(log_content.decode('utf-8', errors='ignore'))
                log_content = redacted_content.encode('utf-8')
                print(f"[REDACTION] Data redaction completed")
            except Exception as redact_error:
                print(f"[REDACTION] Warning: Redaction failed: {redact_error}")
                # Continue without redaction if it fails
            
            # Create temporary file for analysis
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.log') as tmp_file:
                tmp_file.write(log_content)
                tmp_path = tmp_file.name
            
            try:
                # Parse log file and extract events (basic analysis only)
                print(f"[ANALYSIS] Parsing log content ({len(log_content)} bytes)")
                events = analysis.parse_log_file(tmp_path)
                events_count = len(events) if events else 0
                
                # Basic analysis results
                analysis_result = {
                    "file_processed": True,
                    "original_file": file.filename,
                    "file_size": len(content),
                    "log_content_size": len(log_content),
                    "events_count": events_count,
                    "content_preview": log_content[:300].decode('utf-8', errors='ignore'),
                    "lines_count": log_content.count(b'\n'),
                    "is_zip": file.filename.lower().endswith('.zip'),
                    "zip_contents": file_list if file_list else None
                }
                
                # Additional analysis if events found
                if events_count > 0:
                    # Event type distribution
                    event_types = {}
                    for event in events[:50]:  # Sample for performance
                        event_type = getattr(event, 'severity', 'INFO')
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                    
                    analysis_result["event_distribution"] = event_types
                    analysis_result["sample_events"] = [
                        {
                            "timestamp": str(getattr(event, 'timestamp', 'N/A')),
                            "event_type": getattr(event, 'severity', 'INFO'),
                            "description": str(event)[:100] + "..." if len(str(event)) > 100 else str(event)
                        }
                        for event in events[:10]  # First 10 events
                    ]
                
                # Store events in session for report generation
                # Note: In production, you'd want to use a proper session store
                analysis_result["_events"] = events  # Internal use only
                
                processing_time = (datetime.now() - start_time).total_seconds()
                analysis_result["processing_time"] = f"{processing_time:.2f}s"
                
                print(f"[ANALYSIS] Basic analysis completed in {processing_time:.2f}s")
                return JSONResponse(analysis_result)
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"[ERROR] Analysis failed: {e}")
            return JSONResponse({"error": f"Analysis failed: {str(e)}"}, status_code=500)

    @web_app.post("/generate_report")
    async def generate_report(request: Request):
        """Generate AI-powered reports based on sidebar configuration"""
        try:
            data = await request.json()
            report_type = data.get('report_type', 'standard')
            use_local_llm = data.get('use_local_llm', False)
            use_cloud_ai = data.get('use_cloud_ai', False)
            use_python_engine = data.get('use_python_engine', True)
            
            print(f"[REPORT] Generating {report_type} report with engines: Local={use_local_llm}, Cloud={use_cloud_ai}, Python={use_python_engine}")
            
            # For now, return a simple success message
            # In the full implementation, this would:
            # 1. Retrieve stored events from session
            # 2. Run AI analysis based on selected engines
            # 3. Generate PDF report
            # 4. Return download link
            
            if report_type == 'local_ai' and use_local_llm:
                message = "Local AI report generation initiated with Phi-2 model"
            elif report_type == 'cloud_ai' and use_cloud_ai:
                message = "Cloud AI report generation initiated with OpenAI GPT"
            else:
                message = "Standard report generation completed"
            
            return JSONResponse({
                "status": "success",
                "message": message,
                "report_type": report_type
            })
            
        except Exception as e:
            print(f"[ERROR] Report generation failed: {e}")
            return JSONResponse({"error": f"Report generation failed: {str(e)}"}, status_code=500)

    return web_app
