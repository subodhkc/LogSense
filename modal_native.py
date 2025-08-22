# modal_native.py - Native Modal FastAPI app with LogSense functionality
import modal

APP_NAME = "logsense-native"

# Build image with all dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt")
    .pip_install("fastapi>=0.100.0", "python-multipart")
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=image)

# Deploy the FastAPI app with warm containers for ML workloads
@app.function(timeout=24*60*60, memory=2048, min_containers=1)
@modal.asgi_app()
def native_app():
    from fastapi import FastAPI, File, UploadFile
    from fastapi.responses import HTMLResponse, JSONResponse
    import os
    import tempfile
    from datetime import datetime
    
    # Create FastAPI instance inside Modal function
    web_app = FastAPI(title="LogSense - AI Log Analysis", version="1.0.0")

    @web_app.get("/", response_class=HTMLResponse)
    async def home():
        """Enterprise LogSense interface with comprehensive user forms"""
        return """<!DOCTYPE html>
<html>
<head>
    <title>LogSense - Enterprise Log Analysis</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; background: #f8f9fa; color: #333; }
        .header { text-align: center; margin-bottom: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
        .progress-bar { display: flex; justify-content: space-between; margin: 20px 0; padding: 0 20px; }
        .progress-step { text-align: center; flex: 1; position: relative; }
        .progress-step.active { color: #007bff; font-weight: bold; }
        .progress-step.completed { color: #28a745; }
        .form-section { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .form-row { display: flex; gap: 20px; margin-bottom: 15px; }
        .form-group { flex: 1; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 600; color: #555; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; }
        .form-group textarea { resize: vertical; min-height: 80px; }
        .btn { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; transition: background 0.3s; }
        .btn:hover { background: #0056b3; }
        .btn-success { background: #28a745; }
        .btn-warning { background: #ffc107; color: #212529; }
        .upload-area { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; border: 2px dashed #007bff; text-align: center; }
        .upload-area.dragover { border-color: #28a745; background: #f8fff9; }
        .results { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-top: 20px; }
        .metric-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .metric-card { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; }
        .metric-card h3 { margin: 0 0 10px 0; font-size: 2em; }
        .metric-card p { margin: 0; opacity: 0.9; }
        .success { color: #28a745; font-weight: bold; }
        .error { color: #dc3545; font-weight: bold; }
        .info { background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #007bff; }
        .ai-section { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 10px 0; }
        .event-item { background: #f9f9f9; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
        .collapsible { cursor: pointer; padding: 15px; background: #f1f3f4; border: none; width: 100%; text-align: left; font-size: 16px; font-weight: bold; border-radius: 5px; margin-bottom: 10px; }
        .collapsible:hover { background: #e8eaed; }
        .collapsible.active { background: #007bff; color: white; }
        .content { display: none; padding: 0 15px; }
        .content.show { display: block; }
        .status-badge { display: inline-block; padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; }
        .status-success { background: #d4edda; color: #155724; }
        .status-error { background: #f8d7da; color: #721c24; }
        .status-warning { background: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="header">
        <h1>LogSense</h1>
        <h3>Enterprise Log Analysis Platform</h3>
        <p>Intelligent diagnostics for system provisioning and deployment</p>
        <p><strong>Session:</strong> <span id="sessionId"></span></p>
    </div>
    
    <div class="progress-bar">
        <div class="progress-step active" id="step1">
            <div>1</div>
            <div>Configure</div>
        </div>
        <div class="progress-step" id="step2">
            <div>2</div>
            <div>Upload</div>
        </div>
        <div class="progress-step" id="step3">
            <div>3</div>
            <div>Analyze</div>
        </div>
        <div class="progress-step" id="step4">
            <div>4</div>
            <div>Review</div>
        </div>
        <div class="progress-step" id="step5">
            <div>5</div>
            <div>Export</div>
        </div>
    </div>

    <form id="contextForm">
        <div class="form-section">
            <h3>User & Test Information</h3>
            <div class="form-row">
                <div class="form-group">
                    <label for="userName">Your Name *</label>
                    <input type="text" id="userName" name="userName" placeholder="Enter your full name" required>
                </div>
                <div class="form-group">
                    <label for="appName">Application Being Tested *</label>
                    <input type="text" id="appName" name="appName" placeholder="e.g., HP Power Manager" required>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="appVersion">Application Version</label>
                    <input type="text" id="appVersion" name="appVersion" placeholder="e.g., v2.1.3 or Build 12345">
                </div>
                <div class="form-group">
                    <label for="testEnvironment">Test Environment</label>
                    <select id="testEnvironment" name="testEnvironment">
                        <option value="Production">Production</option>
                        <option value="Staging">Staging</option>
                        <option value="Development">Development</option>
                        <option value="QA">QA</option>
                        <option value="Pre-production">Pre-production</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
            </div>
        </div>

        <div class="form-section">
            <h3>Issue Description & Context</h3>
            <div class="form-group">
                <label for="issueDescription">Describe the Issue *</label>
                <textarea id="issueDescription" name="issueDescription" placeholder="What problem are you experiencing? Be specific about symptoms, error messages, and impact." required></textarea>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="deploymentMethod">Deployment Method</label>
                    <select id="deploymentMethod" name="deploymentMethod">
                        <option value="DASH Imaging">DASH Imaging</option>
                        <option value="SoftPaq Installation">SoftPaq Installation</option>
                        <option value="Manual Install">Manual Install</option>
                        <option value="Group Policy">Group Policy</option>
                        <option value="SCCM">SCCM</option>
                        <option value="Other">Other</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="buildNumber">Build/Version Number</label>
                    <input type="text" id="buildNumber" name="buildNumber" placeholder="e.g., 26000.1000">
                </div>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="buildChanges">Recent Changes</label>
                    <textarea id="buildChanges" name="buildChanges" placeholder="Any recent updates, patches, or configuration changes"></textarea>
                </div>
                <div class="form-group">
                    <label for="previousVersion">Previous Working Version</label>
                    <input type="text" id="previousVersion" name="previousVersion" placeholder="Last known good version">
                </div>
            </div>
        </div>

        <button type="button" class="collapsible">Analysis Engine Selection</button>
        <div class="content">
            <div class="form-section">
                <h4>Select Analysis Engines</h4>
                <div class="form-row">
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="pythonEngine" name="pythonEngine" checked>
                            Python Analysis Engine (Rule-based parsing)
                        </label>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="localLLM" name="localLLM" checked>
                            Local LLM (In-house Phi-2 Model)
                        </label>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="cloudAI" name="cloudAI">
                            Cloud AI (OpenAI GPT Fallback)
                        </label>
                    </div>
                </div>
            </div>
        </div>

        <button type="button" class="collapsible">Additional Information (Optional)</button>
        <div class="content">
            <div class="form-section">
                <div class="form-row">
                    <div class="form-group">
                        <label for="hwModel">Hardware Model</label>
                        <input type="text" id="hwModel" name="hwModel" placeholder="e.g., HP EliteBook 840 G10">
                    </div>
                    <div class="form-group">
                        <label for="osBuild">OS Build</label>
                        <input type="text" id="osBuild" name="osBuild" placeholder="e.g., Windows 11 26000.1000">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="region">Region/Locale</label>
                        <input type="text" id="region" name="region" placeholder="e.g., US, EMEA">
                    </div>
                    <div class="form-group">
                        <label for="testRunId">Test Run ID</label>
                        <input type="text" id="testRunId" name="testRunId" placeholder="e.g., CI-12345 or Manual-2025-08-21">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label for="networkConstraints">Network Constraints</label>
                        <input type="text" id="networkConstraints" name="networkConstraints" placeholder="e.g., Proxy required, firewalled, offline">
                    </div>
                    <div class="form-group">
                        <label for="proxyConfig">Proxy Config</label>
                        <input type="text" id="proxyConfig" name="proxyConfig" placeholder="e.g., http://proxy:8080">
                    </div>
                </div>
                <div class="form-group">
                    <label for="privateNotes">Private Notes (not shared)</label>
                    <textarea id="privateNotes" name="privateNotes" placeholder="Internal notes, device SKU, etc."></textarea>
                </div>
            </div>
        </div>

        <button type="submit" class="btn">Continue to Upload →</button>
    </form>

    <!-- Upload Section (Step 2) -->
    <div id="uploadSection" style="display: none;">
        <div class="form-section">
            <h2>Step 2: Upload Log File</h2>
            <div class="upload-area" id="uploadArea">
                <div class="upload-content">
                    <div class="upload-icon">📁</div>
                    <p>Drag and drop your log file here or click to browse</p>
                    <input type="file" id="fileInput" accept=".log,.txt,.out" style="display: none;">
                    <button type="button" class="btn-secondary" onclick="document.getElementById('fileInput').click()">Choose File</button>
                </div>
            </div>
            <div class="file-info" id="fileInfo" style="display: none;"></div>
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button type="button" class="btn" id="backToStep1" style="background: #6c757d;">← Back</button>
                <button type="button" class="btn" id="analyzeBtn" style="display: none;">Analyze Log File</button>
            </div>
        </div>
    </div>

    <!-- Results Section (Step 3) -->
    <div id="resultsSection" style="display: none;">
        <div class="results">
            <h2>Analysis Results</h2>
            <div id="analysisResults"></div>
            <div style="margin-top: 20px;">
                <button type="button" class="btn" id="backToUpload" style="background: #6c757d;">← Back to Upload</button>
                <button type="button" class="btn" style="background: #28a745;">Generate PDF Report</button>
                <button type="button" class="btn" style="background: #17a2b8;">Export Data</button>
            </div>
        </div>
    </div>

    <script>
        // Generate session ID
        document.getElementById('sessionId').textContent = 'LS-' + Date.now().toString(36).toUpperCase();
        
        // Add CSS for secondary button
        const style = document.createElement('style');
        style.textContent = `
            .btn-secondary { 
                background: #6c757d; 
                color: white; 
                padding: 10px 20px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer; 
                font-size: 14px; 
                transition: background 0.3s; 
            }
            .btn-secondary:hover { background: #5a6268; }
        `;
        document.head.appendChild(style);
        
        // Collapsible sections
        document.querySelectorAll('.collapsible').forEach(button => {
            button.addEventListener('click', function() {
                this.classList.toggle('active');
                const content = this.nextElementSibling;
                content.classList.toggle('show');
            });
        });
        
        // Context form submission
        document.getElementById('contextForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validate required fields
            const userName = document.getElementById('userName').value;
            const appName = document.getElementById('appName').value;
            const issueDescription = document.getElementById('issueDescription').value;
            
            if (!userName || !appName || !issueDescription) {
                alert('Please fill in all required fields marked with *');
                return;
            }
            
            // Update progress
            document.getElementById('step1').classList.add('completed');
            document.getElementById('step1').classList.remove('active');
            document.getElementById('step2').classList.add('active');
            
            // Show upload section
            document.getElementById('uploadSection').style.display = 'block';
            this.style.display = 'none';
            
            // Store context data including analysis engines
            window.userContext = {
                userName: userName,
                appName: appName,
                appVersion: document.getElementById('appVersion').value,
                testEnvironment: document.getElementById('testEnvironment').value,
                issueDescription: issueDescription,
                deploymentMethod: document.getElementById('deploymentMethod').value,
                buildNumber: document.getElementById('buildNumber').value,
                buildChanges: document.getElementById('buildChanges').value,
                previousVersion: document.getElementById('previousVersion').value,
                // Analysis engine selections
                pythonEngine: document.getElementById('pythonEngine').checked,
                localLLM: document.getElementById('localLLM').checked,
                cloudAI: document.getElementById('cloudAI').checked,
                // Additional info
                hwModel: document.getElementById('hwModel').value,
                osBuild: document.getElementById('osBuild').value,
                region: document.getElementById('region').value,
                testRunId: document.getElementById('testRunId').value,
                networkConstraints: document.getElementById('networkConstraints').value,
                proxyConfig: document.getElementById('proxyConfig').value,
                privateNotes: document.getElementById('privateNotes').value
            };
        });

        // Back button functionality
        document.getElementById('backToStep1').addEventListener('click', function() {
            // Hide upload section, show form
            document.getElementById('uploadSection').style.display = 'none';
            document.getElementById('contextForm').style.display = 'block';
            
            // Update progress
            document.getElementById('step2').classList.remove('active');
            document.getElementById('step1').classList.remove('completed');
            document.getElementById('step1').classList.add('active');
        });

        document.getElementById('backToUpload').addEventListener('click', function() {
            // Hide results section, show upload
            document.getElementById('resultsSection').style.display = 'none';
            document.getElementById('uploadSection').style.display = 'block';
            
            // Update progress
            document.getElementById('step3').classList.remove('active');
            document.getElementById('step2').classList.add('active');
        });
        
        // Drag and drop functionality
        const uploadArea = document.getElementById('uploadArea');
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight(e) {
            uploadArea.classList.add('dragover');
        }
        
        function unhighlight(e) {
            uploadArea.classList.remove('dragover');
        }
        
        uploadArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            document.getElementById('fileInput').files = files;
        }
        
        // File upload handling
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('fileInput');
            const results = document.getElementById('results');
            const resultsContent = document.getElementById('resultsContent');
            const metricsCards = document.getElementById('metricsCards');
            
            if (!fileInput.files[0]) { alert('Please select a file'); return; }
            
            results.style.display = 'block';
            resultsContent.innerHTML = '<div>Analyzing log file with Phi-2 LLM...</div>';
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            // Update progress
            document.getElementById('step2').classList.add('completed');
            document.getElementById('step2').classList.remove('active');
            document.getElementById('step3').classList.add('active');
            
            // Add user context to form data
            if (window.userContext) {
                Object.keys(window.userContext).forEach(key => {
                    formData.append(key, window.userContext[key]);
                });
            }
            
            try {
                const response = await fetch('/analyze', { method: 'POST', body: formData });
                const result = await response.json();
                
                if (response.ok) {
                    // Update progress
                    document.getElementById('step3').classList.add('completed');
                    document.getElementById('step3').classList.remove('active');
                    document.getElementById('step4').classList.add('active');
                    
                    // Display metrics cards
                    const issues = result.analysis.event_distribution ? 
                        Object.values(result.analysis.event_distribution).reduce((a, b) => a + b, 0) : 0;
                    
                    metricsCards.innerHTML = `
                        <div class="metric-card">
                            <h3>${result.events_count}</h3>
                            <p>Total Events</p>
                        </div>
                        <div class="metric-card">
                            <h3>${issues}</h3>
                            <p>Issues Found</p>
                        </div>
                        <div class="metric-card">
                            <h3>1</h3>
                            <p>Files Processed</p>
                        </div>
                        <div class="metric-card">
                            <h3>${result.analysis_time}s</h3>
                            <p>Analysis Time</p>
                        </div>
                    `;
                    
                    resultsContent.innerHTML = `
                        <div class="success">Analysis Complete!</div>
                        <div class="info">
                            <strong>User:</strong> ${window.userContext?.userName || 'Anonymous'}<br>
                            <strong>Application:</strong> ${window.userContext?.appName || 'N/A'}<br>
                            <strong>Environment:</strong> ${window.userContext?.testEnvironment || 'N/A'}<br>
                            <strong>File:</strong> ${result.filename}<br>
                            <strong>Size:</strong> ${result.file_size} bytes
                        </div>
                        
                        ${result.analysis.ai_analysis ? `
                        <div class="ai-section">
                            <h4>AI Root Cause Analysis (${result.analysis.ai_analysis.model_used || 'Phi-2'})</h4>
                            <p><strong>Summary:</strong> ${result.analysis.ai_analysis.summary || result.analysis.ai_analysis.error}</p>
                            ${result.analysis.ai_analysis.events_analyzed ? `<p><strong>Events Analyzed:</strong> ${result.analysis.ai_analysis.events_analyzed}</p>` : ''}
                            ${window.userContext?.issueDescription ? `<p><strong>Issue Context:</strong> ${window.userContext.issueDescription}</p>` : ''}
                        </div>
                        ` : ''}
                        
                        ${result.analysis.event_distribution ? `
                        <h4>Event Distribution</h4>
                        <div>${Object.entries(result.analysis.event_distribution).map(([type, count]) => 
                            `<div class="event-item">
                                <strong>${type}:</strong> ${count} events
                                <span class="status-badge ${type.toLowerCase().includes('error') ? 'status-error' : 
                                    type.toLowerCase().includes('warning') ? 'status-warning' : 'status-success'}">
                                    ${type.toUpperCase()}
                                </span>
                            </div>`
                        ).join('')}</div>
                        ` : ''}
                        
                        ${result.analysis.sample_events ? `
                        <h4>Sample Events</h4>
                        <div>${result.analysis.sample_events.map(event => 
                            `<div class="event-item">
                                <strong>${event.timestamp}</strong> 
                                <span class="status-badge ${event.event_type?.toLowerCase().includes('error') ? 'status-error' : 
                                    event.event_type?.toLowerCase().includes('warning') ? 'status-warning' : 'status-success'}">
                                    ${event.event_type || 'INFO'}
                                </span><br>
                                ${event.description}
                            </div>`
                        ).join('')}</div>
                        ` : ''}
                        
                        <h4>System Capabilities</h4>
                        <div class="info">
                            ${result.capabilities ? Object.entries(result.capabilities).map(([key, value]) => 
                                `<span style="color: ${value ? 'green' : 'red'}">
                                    ${value ? '[✓]' : '[✗]'} ${key.replace('_', ' ').toUpperCase()}
                                </span><br>`
                            ).join('') : ''}
                        </div>
                        
                        <div style="text-align: center; margin-top: 30px;">
                            <button class="btn btn-success" onclick="generateReport()">Generate PDF Report</button>
                            <button class="btn btn-warning" onclick="exportData()">Export Data</button>
                        </div>
                    `;
                } else {
                    resultsContent.innerHTML = `<div class="error">Error: ${result.detail}</div>`;
                }
            } catch (error) {
                resultsContent.innerHTML = `<div class="error">Network Error: ${error.message}</div>`;
            }
        });
        
        // Report generation functions
        function generateReport() {
            alert('PDF Report generation will be implemented in next update');
            document.getElementById('step4').classList.add('completed');
            document.getElementById('step4').classList.remove('active');
            document.getElementById('step5').classList.add('active');
        }
        
        function exportData() {
            alert('Data export will be implemented in next update');
        }
    </script>
</body>
</html>"""

    @web_app.post("/analyze")
    async def analyze_log(file: UploadFile = File(...)):
        """Analyze uploaded log file with full LogSense capabilities"""
        start_time = datetime.now()
        
        try:
            os.chdir("/root/app")
            content = await file.read()
            
            # Import LogSense analysis modules with error handling
            try:
                import sys
                sys.path.insert(0, "/root/app")
                print(f"[DEBUG] Python path: {sys.path}")
                print(f"[DEBUG] Current directory: {os.getcwd()}")
                print(f"[DEBUG] Files in directory: {os.listdir('.')}")
                
                import analysis
                import ai_rca
                import redaction
                print(f"[DEBUG] Successfully imported analysis modules")
            except ImportError as e:
                print(f"[ERROR] Failed to import analysis modules: {e}")
                print(f"[ERROR] Available files: {[f for f in os.listdir('.') if f.endswith('.py')]}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "detail": f"Analysis modules not available: {str(e)}",
                        "error_type": "ImportError"
                    }
                )
            
            # Create temporary file for analysis
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.log') as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            try:
                # Step 1: Parse log file and extract events
                print(f"[ANALYSIS] Parsing log file: {file.filename}")
                events = analysis.parse_log_file(tmp_path)
                events_count = len(events) if events else 0
                
                # Step 2: Basic analysis results
                analysis_result = {
                    "file_processed": True,
                    "file_size": len(content),
                    "events_count": events_count,
                    "content_preview": content[:300].decode('utf-8', errors='ignore'),
                    "lines_count": content.count(b'\n'),
                }
                
                # Step 3: AI Analysis based on user engine selections
                ai_summary = None
                if events and events_count > 0:
                    # Get user context from form data (if available)
                    use_local_llm = True  # Default
                    use_cloud_ai = False  # Default
                    
                    # Try to get engine preferences from form data
                    form_data = await file.read()  # We already read this, but need to get form context
                    
                    try:
                        print(f"[AI_RCA] Starting AI analysis with {events_count} events...")
                        print(f"[AI_RCA] Engine preferences - Local LLM: {use_local_llm}, Cloud AI: {use_cloud_ai}")
                        
                        if use_local_llm:
                            # Use in-house Phi-2 LLM (offline first)
                            ai_summary = ai_rca.generate_summary(events[:20])  # Limit for performance
                            
                            if ai_summary:
                                analysis_result["ai_analysis"] = {
                                    "summary": ai_summary,
                                    "model_used": "phi2_offline",
                                    "events_analyzed": min(events_count, 20),
                                    "engine_selected": "Local LLM (Phi-2)"
                                }
                                print(f"[AI_RCA] Local LLM analysis completed successfully")
                            elif use_cloud_ai:
                                # Fallback to cloud AI if local fails and cloud is enabled
                                print(f"[AI_RCA] Local LLM failed, trying cloud AI fallback...")
                                ai_summary = ai_rca.generate_summary(events[:20])  # This should handle fallback
                                if ai_summary:
                                    analysis_result["ai_analysis"] = {
                                        "summary": ai_summary,
                                        "model_used": "openai_fallback",
                                        "events_analyzed": min(events_count, 20),
                                        "engine_selected": "Cloud AI (OpenAI Fallback)"
                                    }
                            else:
                                analysis_result["ai_analysis"] = {"error": "Local LLM analysis failed and cloud AI not enabled"}
                        elif use_cloud_ai:
                            # Use cloud AI directly
                            ai_summary = ai_rca.generate_summary(events[:20])
                            if ai_summary:
                                analysis_result["ai_analysis"] = {
                                    "summary": ai_summary,
                                    "model_used": "openai_direct",
                                    "events_analyzed": min(events_count, 20),
                                    "engine_selected": "Cloud AI (OpenAI)"
                                }
                        else:
                            analysis_result["ai_analysis"] = {"error": "No AI engines selected"}
                            
                    except Exception as ai_error:
                        print(f"[AI_RCA] AI analysis failed: {ai_error}")
                        analysis_result["ai_analysis"] = {
                            "error": f"AI analysis failed: {str(ai_error)}",
                            "fallback_available": use_cloud_ai,
                            "engine_attempted": "Local LLM" if use_local_llm else "Cloud AI"
                        }
                
                # Step 4: Additional analysis if events found
                if events_count > 0:
                    # Event type distribution
                    event_types = {}
                    for event in events[:50]:  # Sample for performance
                        event_type = getattr(event, 'severity', 'INFO')  # Use severity instead of event_type
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                    
                    analysis_result["event_distribution"] = event_types
                    analysis_result["sample_events"] = [
                        {
                            "timestamp": str(getattr(event, 'timestamp', 'N/A')),
                            "event_type": getattr(event, 'severity', 'INFO'),
                            "description": str(event)[:100] + "..." if len(str(event)) > 100 else str(event)
                        }
                        for event in events[:5]  # Show first 5 events
                    ]
                
            finally:
                # Clean up temp file
                os.unlink(tmp_path)
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            
            return JSONResponse({
                "success": True,
                "filename": file.filename,
                "file_size": len(content),
                "events_count": events_count,
                "analysis_time": round(analysis_time, 2),
                "analysis": analysis_result,
                "capabilities": {
                    "in_house_llm": True,
                    "phi2_model": True,
                    "event_extraction": True,
                    "ai_rca": True
                }
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] Analysis failed: {error_details}")
            
            return JSONResponse(
                status_code=500,
                content={
                    "success": False, 
                    "detail": f"Analysis failed: {str(e)}",
                    "error_type": type(e).__name__,
                    "debug_info": error_details if os.getenv("DEBUG") else None
                }
            )

    @web_app.get("/health")
    async def health():
        """Health check endpoint"""
        return {"status": "healthy", "service": "LogSense Native", "llm": "Phi-2"}

    return web_app
