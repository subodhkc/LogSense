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

# Deploy the FastAPI app
@app.function(timeout=24*60*60)
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
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 LogSense - AI Log Analysis</h1>
        <p>Native Modal implementation - Upload your log files for analysis</p>
    </div>
    
    <div class="upload-area">
        <h3>Upload Log File</h3>
        <form id="uploadForm" enctype="multipart/form-data">
            <input type="file" id="fileInput" name="file" accept=".txt,.log,.zip" required>
            <br><br>
            <button type="submit" class="btn">Analyze Log File</button>
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
            resultsContent.innerHTML = '<div>🔄 Analyzing log file...</div>';
            
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
                        <h4>Results:</h4>
                        <pre>${JSON.stringify(result.analysis, null, 2)}</pre>
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
        """Analyze uploaded log file"""
        start_time = datetime.now()
        
        try:
            os.chdir("/root/app")
            content = await file.read()
            
            # Basic analysis without heavy imports for now
            analysis_result = {
                "file_processed": True,
                "file_size": len(content),
                "content_preview": content[:200].decode('utf-8', errors='ignore'),
                "lines_count": content.count(b'\n'),
                "summary": "File uploaded and processed successfully"
            }
            
            analysis_time = (datetime.now() - start_time).total_seconds()
            
            return JSONResponse({
                "success": True,
                "filename": file.filename,
                "file_size": len(content),
                "events_count": analysis_result.get("lines_count", 0),
                "analysis_time": round(analysis_time, 2),
                "analysis": analysis_result
            })
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "detail": f"Analysis failed: {str(e)}"}
            )

    @web_app.get("/health")
    async def health():
        """Health check endpoint"""
        return {"status": "healthy", "service": "LogSense Native"}

    return web_app
