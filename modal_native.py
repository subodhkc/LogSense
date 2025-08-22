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
        """Main page with file upload interface"""
        return """<!DOCTYPE html>
<html>
<head>
    <title>LogSense - AI Log Analysis</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f8f9fa; color: #333; }
        .header { text-align: center; margin-bottom: 40px; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .upload-area { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; border: 2px dashed #ddd; text-align: center; }
        .btn { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .results { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-top: 20px; }
        .success { color: #28a745; }
        .error { color: #dc3545; }
        .info { background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .ai-section { background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #007bff; }
        .event-item { background: #f9f9f9; padding: 10px; margin: 5px 0; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 LogSense - AI Log Analysis</h1>
        <p>Native Modal implementation with <strong>In-House Phi-2 LLM</strong></p>
        <p>Upload your log files for intelligent analysis and AI-powered insights</p>
    </div>
    
    <div class="upload-area">
        <h3>Upload Log File</h3>
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" id="fileInput" name="file" accept=".txt,.log,.zip" required>
            <br><br>
            <button type="submit" class="btn">🚀 Analyze with AI</button>
        </form>
    </div>
    
    <div id="results" class="results" style="display: none;">
        <h3>Analysis Results</h3>
        <div id="resultsContent"></div>
    </div>
    
    <script>
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('fileInput');
            const results = document.getElementById('results');
            const resultsContent = document.getElementById('resultsContent');
            
            if (!fileInput.files[0]) { alert('Please select a file'); return; }
            
            results.style.display = 'block';
            resultsContent.innerHTML = '<div>🔄 Analyzing log file with Phi-2 LLM...</div>';
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            try {
                const response = await fetch('/analyze', { method: 'POST', body: formData });
                const result = await response.json();
                
                if (response.ok) {
                    resultsContent.innerHTML = `
                        <div class="success">✅ Analysis Complete!</div>
                        <div class="info">
                            <strong>File:</strong> ${result.filename}<br>
                            <strong>Size:</strong> ${result.file_size} bytes<br>
                            <strong>Events Found:</strong> ${result.events_count}<br>
                            <strong>Analysis Time:</strong> ${result.analysis_time}s
                        </div>
                        
                        ${result.analysis.ai_analysis ? `
                        <div class="ai-section">
                            <h4>🧠 AI Analysis (${result.analysis.ai_analysis.model_used || 'Phi-2'})</h4>
                            <p><strong>Summary:</strong> ${result.analysis.ai_analysis.summary || result.analysis.ai_analysis.error}</p>
                            ${result.analysis.ai_analysis.events_analyzed ? `<p><strong>Events Analyzed:</strong> ${result.analysis.ai_analysis.events_analyzed}</p>` : ''}
                        </div>
                        ` : ''}
                        
                        ${result.analysis.event_distribution ? `
                        <h4>📊 Event Distribution</h4>
                        <div>${Object.entries(result.analysis.event_distribution).map(([type, count]) => 
                            `<div class="event-item"><strong>${type}:</strong> ${count} events</div>`
                        ).join('')}</div>
                        ` : ''}
                        
                        ${result.analysis.sample_events ? `
                        <h4>📝 Sample Events</h4>
                        <div>${result.analysis.sample_events.map(event => 
                            `<div class="event-item">
                                <strong>${event.timestamp}</strong> [${event.event_type}]<br>
                                ${event.description}
                            </div>`
                        ).join('')}</div>
                        ` : ''}
                        
                        <h4>🔧 Capabilities</h4>
                        <div class="info">
                            ${result.capabilities ? Object.entries(result.capabilities).map(([key, value]) => 
                                `<span style="color: ${value ? 'green' : 'red'}">
                                    ${value ? '✅' : '❌'} ${key.replace('_', ' ').toUpperCase()}
                                </span><br>`
                            ).join('') : ''}
                        </div>
                    `;
                } else {
                    resultsContent.innerHTML = `<div class="error">❌ Error: ${result.detail}</div>`;
                }
            } catch (error) {
                resultsContent.innerHTML = `<div class="error">❌ Network Error: ${error.message}</div>`;
            }
        });
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
            
            # Import LogSense analysis modules
            import analysis
            import ai_rca
            import redaction
            
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
                
                # Step 3: AI Analysis with in-house Phi-2 LLM
                ai_summary = None
                if events and events_count > 0:
                    try:
                        print(f"[AI_RCA] Starting AI analysis with {events_count} events...")
                        
                        # Use in-house Phi-2 LLM (offline first, OpenAI fallback)
                        ai_summary = ai_rca.generate_summary(events[:20])  # Limit for performance
                        
                        if ai_summary:
                            analysis_result["ai_analysis"] = {
                                "summary": ai_summary,
                                "model_used": "phi2_offline" if "phi2" in str(ai_summary).lower() else "openai_fallback",
                                "events_analyzed": min(events_count, 20)
                            }
                            print(f"[AI_RCA] AI analysis completed successfully")
                        else:
                            analysis_result["ai_analysis"] = {"error": "AI analysis returned empty result"}
                            
                    except Exception as ai_error:
                        print(f"[AI_RCA] AI analysis failed: {ai_error}")
                        analysis_result["ai_analysis"] = {
                            "error": f"AI analysis failed: {str(ai_error)}",
                            "fallback_available": True
                        }
                
                # Step 4: Additional analysis if events found
                if events_count > 0:
                    # Event type distribution
                    event_types = {}
                    for event in events[:50]:  # Sample for performance
                        event_type = getattr(event, 'event_type', 'unknown')
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                    
                    analysis_result["event_distribution"] = event_types
                    analysis_result["sample_events"] = [
                        {
                            "timestamp": getattr(event, 'timestamp', 'N/A'),
                            "event_type": getattr(event, 'event_type', 'unknown'),
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
