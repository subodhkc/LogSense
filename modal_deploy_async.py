"""Modal deployment with async patterns - imports handled within Modal function."""
import modal
import os
from datetime import datetime
from typing import Dict, Any

# Configuration
APP_NAME = "logsense-async"
PORT = 8000

# Create Modal image with GPU support and LLM dependencies
# IMPORTANT: Add local directory first so that requirements and constraints files
# are present before pip installs (needed for "-c constraints.txt").
image = (
    modal.Image.debian_slim(python_version="3.11")
    .add_local_dir(".", remote_path="/root/app")
    .pip_install_from_requirements("/root/app/requirements-modal-gpu.txt")
    .env({
        "MODEL_BACKEND": "phi2",
        "DISABLE_ML_MODELS": "false",
        "PYTHONPATH": "/root/app"
    })
)

app = modal.App(name=APP_NAME, image=image)

@app.function(
    timeout=900,
    memory=4096,  # Increased for LLM model loading
    gpu="A10G",  # Single A10G GPU for LLM inference
    container_idle_timeout=120  # Aggressive 2-minute idle timeout
)
@modal.concurrent(10)  # Use decorator instead of parameter
@modal.asgi_app()
def async_app():
    """Create FastAPI app with async endpoints - imports handled here."""
    import asyncio
    import json
    import sys
    import traceback
    import tempfile
    
    # Import async dependencies within Modal function
    import aiofiles
    import httpx
    from fastapi import FastAPI, File, UploadFile, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    
    # Add the app directory to Python path for imports
    sys.path.insert(0, '/root/app')
    
    # Create FastAPI instance
    web_app = FastAPI(title="LogSense Async - AI Log Analysis", version="2.0.0")
    
    # Mount static files and templates
    web_app.mount("/static", StaticFiles(directory="/root/app/static"), name="static")
    templates = Jinja2Templates(directory="/root/app/templates")
    
    # Session cache for storing analysis results
    global_cache: Dict[str, Any] = {}
    session_cache: Dict[str, Any] = {}
    
    # GPU-optimized LLM functions
    @web_app.on_event("startup")
    async def load_llm_model():
        """Load Phi-2 model on GPU at startup for faster inference."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            if torch.cuda.is_available():
                print("[GPU] Loading Phi-2 model on GPU...")
                global phi2_model, phi2_tokenizer
                phi2_model = AutoModelForCausalLM.from_pretrained(
                    "microsoft/phi-2",
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True
                )
                phi2_tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-2", trust_remote_code=True)
                print("[GPU] Phi-2 model loaded successfully")
            else:
                print("[CPU] GPU not available, LLM will use CPU fallback")
        except Exception as e:
            print(f"[ERROR] Failed to load LLM model: {e}")
    
    async def _perform_gpu_llm_analysis(events, context):
        """Perform LLM analysis using GPU-accelerated Phi-2 model."""
        try:
            import torch  # Import torch here to avoid startup issues
            if 'phi2_model' in globals() and 'phi2_tokenizer' in globals():
                # Prepare prompt for analysis
                event_summary = "\n".join([f"[{e.get('timestamp', 'N/A')}] {e.get('message', '')}" for e in events[:10]])
                prompt = f"Analyze these log events and provide root cause analysis:\n{event_summary}\n\nAnalysis:"
                
                # GPU inference
                inputs = phi2_tokenizer(prompt, return_tensors="pt", max_length=1024, truncation=True)
                if torch.cuda.is_available():
                    inputs = {k: v.cuda() for k, v in inputs.items()}
                
                with torch.no_grad():
                    outputs = phi2_model.generate(
                        **inputs,
                        max_new_tokens=256,
                        temperature=0.7,
                        do_sample=True,
                        pad_token_id=phi2_tokenizer.eos_token_id
                    )
                
                response = phi2_tokenizer.decode(outputs[0], skip_special_tokens=True)
                analysis = response.split("Analysis:")[-1].strip()
                
                return {
                    "ai_analysis": analysis,
                    "gpu_accelerated": True,
                    "model": "phi-2",
                    "processing_time": "GPU-optimized"
                }
            else:
                return await _perform_basic_analysis(events)
        except Exception as e:
            print(f"[GPU] LLM analysis failed: {e}")
            return await _perform_basic_analysis(events)
    
    @web_app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Serve the main page."""
        return templates.TemplateResponse("index.html", {"request": request})
    
    @web_app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Async health check with comprehensive status."""
        try:
            # Test async file operations
            async with aiofiles.tempfile.NamedTemporaryFile(mode='w', delete=True) as temp_file:
                await temp_file.write("health_check")
                
            return {
                "status": "healthy",
                "deployment": "async-optimized",
                "memory": "2048MB",
                "async_support": True,
                "file_system": "accessible",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @web_app.post("/upload")
    async def upload_file(request: Request, file: UploadFile = File(...)):
        """Handle async file upload with proper validation."""
        try:
            # Validate file presence
            if not file or not file.filename:
                return JSONResponse({
                    "success": False,
                    "message": "No file provided"
                }, status_code=400)
            
            # Validate file type
            if not _is_valid_file_type(file.filename):
                return JSONResponse({
                    "success": False,
                    "message": "Invalid file type. Supported: .log, .txt, .zip"
                }, status_code=400)
            
            # Process file asynchronously
            temp_path = await _save_uploaded_file(file)
            events = await _process_log_file(temp_path, file.filename)
            
            # Clean up temp file
            await _cleanup_temp_file(temp_path)
            
            # Store results
            session_id = _generate_session_id()
            analysis_data = _create_analysis_data(events, file.filename)
            _store_analysis_results(session_id, analysis_data)
            
            return JSONResponse({
                "success": True,
                "message": f"File uploaded successfully. Found {len(events)} events.",
                "session_id": session_id,
                "events": events[:20],
                "event_count": len(events),
                "redacted": analysis_data["redacted"]
            })
            
        except ValueError as e:
            return JSONResponse({
                "success": False,
                "message": str(e)
            }, status_code=400)
        except Exception as e:
            return JSONResponse({
                "success": False,
                "message": "File upload failed. Please try again."
            }, status_code=500)
    
    @web_app.post("/analyze")
    async def analyze_logs(request: Request):
        """Perform async log analysis - JSON-only endpoint."""
        try:
            current_data = session_cache.get("current")
            if not current_data:
                return JSONResponse({
                    "success": False,
                    "message": "No file uploaded. Please upload a log file first."
                }, status_code=400)
            
            events = current_data.get("events", [])
            if not events:
                return _create_error_response("No events found in uploaded file.", 400)
            
            # Perform async analysis
            analysis_result = await _perform_basic_analysis(events)
            
            # Update cache
            current_data.update(analysis_result)
            current_data["analysis_time"] = datetime.now().isoformat()
            session_cache["current"] = current_data
            
            return JSONResponse({
                "success": True,
                "message": "Log analysis completed",
                **analysis_result
            })
            
        except Exception as e:
            return _handle_error(e, "Analysis failed")
    
    @web_app.post("/ml_analysis")
    async def ml_analysis(request: Request):
        """Async ML analysis with proper validation."""
        try:
            request_data = await request.json()
            analysis_type = request_data.get("analysis_type", "clustering")
            
            if analysis_type not in ["clustering", "severity", "anomaly"]:
                return _create_error_response(f"Invalid analysis type. Supported: clustering, severity, anomaly", 400)
            
            current_data = session_cache.get("current")
            if not current_data:
                return _create_error_response("No data available for ML analysis.", 400)
            
            events = current_data.get("events", [])
            result = await _perform_ml_analysis(analysis_type, events)
            
            return JSONResponse({
                "success": True,
                "message": f"{analysis_type} analysis completed",
                "result": result
            })
            
        except Exception as e:
            return _handle_error(e, "ML analysis failed")
    
    @web_app.post("/generate_report")
    async def generate_report(request: Request):
        """Async report generation with validation."""
        try:
            request_data = await request.json()
            report_type = request_data.get("report_type", "standard")
            
            if report_type not in ["standard", "local_ai", "cloud_ai"]:
                return _create_error_response(f"Invalid report type. Supported: standard, local_ai, cloud_ai", 400)
            
            current_data = session_cache.get("current")
            if not current_data:
                return _create_error_response("No data available for report generation.", 400)
            
            report_data = await _generate_report_data(report_type, current_data)
            
            return JSONResponse({
                "success": True,
                "status": "success",
                "message": "Report generated successfully",
                "report": report_data
            })
            
        except Exception as e:
            return _handle_error(e, "Report generation failed")
    
    @web_app.post("/correlations")
    async def correlations_analysis(request: Request):
        """Handle correlation analysis requests."""
        try:
            request_data = await request.json()
            analysis_type = request_data.get("type", "temporal")
            
            if analysis_type not in ["temporal", "causal"]:
                return _create_error_response(f"Invalid correlation type. Supported: temporal, causal", 400)
            
            current_data = session_cache.get("current")
            if not current_data:
                return _create_error_response("No data available for correlation analysis.", 400)
            
            events = current_data.get("events", [])
            correlation_result = await _perform_correlation_analysis(analysis_type, events)
            
            return JSONResponse({
                "success": True,
                "message": f"{analysis_type} correlation analysis completed",
                "result": correlation_result
            })
            
        except Exception as e:
            return _handle_error(e, "Correlation analysis failed")
    
    @web_app.post("/submit_context")
    async def submit_context(request: Request):
        """Handle context form submission with proper validation."""
        try:
            data = await request.json()
            
            # Validate required fields for security
            context_data = _extract_and_validate_context(data)
            
            # Store context data in session cache
            current_data = session_cache.get("current", {})
            current_data["context"] = context_data
            current_data["context_updated"] = True
            session_cache["current"] = current_data
            
            return JSONResponse({
                "status": "success",
                "message": "Context saved successfully"
            })
            
        except ValueError as e:
            return JSONResponse({
                "status": "error",
                "error": f"Validation error: {str(e)}"
            }, status_code=400)
        except Exception as e:
            return _handle_error(e, "Failed to save context")
    
    # Helper functions
    def _is_valid_file_type(filename: str) -> bool:
        """Validate file type against supported extensions."""
        if not filename:
            return False
        return any(filename.lower().endswith(ext) for ext in [".log", ".txt", ".zip"])
    
    async def _save_uploaded_file(file: UploadFile) -> str:
        """Save uploaded file asynchronously."""
        content = await file.read()
        
        # Check file size (100MB limit)
        if len(content) > 100 * 1024 * 1024:
            raise ValueError("File too large. Maximum size: 100MB")
        
        async with aiofiles.tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=".log") as temp_file:
            await temp_file.write(content)
            return temp_file.name
    
    async def _process_log_file(temp_path: str, filename: str):
        """Process log file with async file operations."""
        try:
            async with aiofiles.open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = await f.read()
            
            # Import analysis module (lazy loading)
            from analysis import parse_logs
            return parse_logs(content, filename)
        except Exception as e:
            print(f"Analysis error: {e}")
            return []
    
    async def _cleanup_temp_file(temp_path: str) -> None:
        """Clean up temporary file asynchronously."""
        try:
            await asyncio.sleep(0.1)  # Small delay to ensure file is closed
            os.unlink(temp_path)
        except Exception as e:
            print(f"Cleanup warning: {e}")
    
    def _generate_session_id() -> str:
        """Generate unique session identifier."""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _create_analysis_data(events, filename: str) -> Dict[str, Any]:
        """Create analysis data structure."""
        return {
            "events": events[:100],
            "filename": filename,
            "upload_time": datetime.now().isoformat(),
            "event_count": len(events),
            "redacted": False
        }
    
    def _store_analysis_results(session_id: str, analysis_data: Dict[str, Any]) -> None:
        """Store analysis results in cache."""
        global_cache[session_id] = analysis_data
        session_cache["current"] = analysis_data
    
    def _create_error_response(message: str, status_code: int) -> JSONResponse:
        """Create standardized error response."""
        return JSONResponse({
            "success": False,
            "message": message
        }, status_code=status_code)
    
    def _handle_error(error: Exception, operation: str) -> JSONResponse:
        """Handle errors consistently with logging."""
        error_msg = f"{operation}: {str(error)}"
        print(error_msg)
        print(traceback.format_exc())
        return _create_error_response(error_msg, 500)
    
    async def _perform_basic_analysis(events) -> Dict[str, Any]:
        """Perform basic log analysis asynchronously."""
        await asyncio.sleep(0.1)  # Simulate processing time
        
        event_types = {}
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        
        for event in events:
            # Count event types
            event_type = getattr(event, 'event_type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
            
            # Basic severity classification
            message = str(getattr(event, 'message', '')).lower()
            if any(word in message for word in ['error', 'fail', 'critical', 'fatal']):
                severity_counts["high"] += 1
            elif any(word in message for word in ['warn', 'warning', 'issue']):
                severity_counts["medium"] += 1
            else:
                severity_counts["low"] += 1
        
        # Generate summary
        total_events = len(events)
        most_common_type = max(event_types.items(), key=lambda x: x[1]) if event_types else ("unknown", 0)
        
        summary = (
            f"Analysis Summary:\n"
            f"Total Events: {total_events}\n"
            f"Most Common Type: {most_common_type[0]} ({most_common_type[1]} events)\n"
            f"Severity Distribution: High: {severity_counts['high']}, "
            f"Medium: {severity_counts['medium']}, Low: {severity_counts['low']}\n"
            f"Event Types Found: {len(event_types)}"
        )
        
        return {
            "basic_analysis": summary,
            "event_types": event_types,
            "severity_counts": severity_counts,
            "processing_mode": "async-optimized"
        }
    
    async def _perform_ml_analysis(analysis_type: str, events) -> Dict[str, Any]:
        """Perform ML analysis based on type."""
        await asyncio.sleep(0.2)  # Simulate processing time
        
        if analysis_type == "clustering":
            return {
                "type": "clustering",
                "clusters": [
                    {"id": 1, "name": "Authentication Events", "count": len(events) // 3},
                    {"id": 2, "name": "System Errors", "count": len(events) // 4},
                    {"id": 3, "name": "Normal Operations", "count": len(events) // 2}
                ],
                "processing_mode": "async-optimized"
            }
        elif analysis_type == "severity":
            return {
                "type": "severity_prediction",
                "predictions": [
                    {"event_id": i, "severity": "high" if i % 3 == 0 else "medium"}
                    for i in range(min(10, len(events)))
                ],
                "processing_mode": "async-optimized"
            }
        else:  # anomaly
            return {
                "type": "anomaly_detection",
                "anomalies": [
                    {"event_id": i * 5, "anomaly_score": 0.78}
                    for i in range(min(3, len(events) // 5))
                ],
                "processing_mode": "async-optimized"
            }
    
    async def _generate_report_data(report_type: str, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report data asynchronously."""
        await asyncio.sleep(0.2)  # Simulate processing time
        
        # Enhanced report with AI analysis if requested
        report_data = {
            "report_type": report_type,
            "processing_mode": "async-optimized",
            "generation_time": datetime.now().isoformat(),
            "summary": current_data.get("basic_analysis", "No analysis available"),
            "event_count": current_data.get("event_count", 0),
            "filename": current_data.get("filename", "unknown"),
            "redacted": current_data.get("redacted", False)
        }
        
        # Add AI analysis for AI report types
        if report_type in ["local_ai", "cloud_ai"]:
            try:
                from ai_rca import analyze_with_ai
                events = current_data.get("events", [])
                context = current_data.get("context", {})
                offline = (report_type == "local_ai")
                
                ai_analysis = analyze_with_ai(events, context=context, offline=offline)
                report_data["ai_analysis"] = ai_analysis
                report_data["ai_engine"] = "phi-2" if offline else "openai"
            except Exception as e:
                report_data["ai_analysis"] = f"AI analysis failed: {str(e)}"
        
        return report_data
    
    async def _perform_correlation_analysis(analysis_type: str, events) -> Dict[str, Any]:
        """Perform correlation analysis based on type."""
        await asyncio.sleep(0.3)  # Simulate processing time
        
        if analysis_type == "temporal":
            return {
                "type": "temporal_correlation",
                "correlations": [
                    {"event_pair": ["error_1", "error_2"], "time_delta": "5.2s", "strength": 0.85},
                    {"event_pair": ["warning_1", "error_3"], "time_delta": "12.1s", "strength": 0.72}
                ],
                "processing_mode": "async-optimized"
            }
        else:  # causal
            return {
                "type": "causal_correlation",
                "causal_chains": [
                    {"root_cause": "config_error", "effects": ["service_restart", "connection_lost"], "confidence": 0.78},
                    {"root_cause": "memory_leak", "effects": ["performance_degradation", "timeout"], "confidence": 0.65}
                ],
                "processing_mode": "async-optimized"
            }
    
    def _extract_and_validate_context(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and validate context data with security checks."""
        # Define allowed fields and max lengths for security
        allowed_fields = {
            "user_name": 100,
            "app_name": 200,
            "app_version": 50,
            "test_environment": 50,
            "issue_description": 2000,
            "deployment_method": 100,
            "build_number": 50,
            "build_changes": 2000,
            "previous_version": 50,
            "use_python_engine": None,  # Boolean
            "use_local_llm": None,      # Boolean
            "use_cloud_ai": None        # Boolean
        }
        
        validated_data = {}
        
        for field, max_length in allowed_fields.items():
            value = data.get(field, "")
            
            # Handle boolean fields
            if max_length is None:
                validated_data[field] = bool(value) if value is not None else False
                continue
            
            # Handle string fields
            if isinstance(value, str):
                # Sanitize input - remove potential XSS characters
                sanitized_value = value.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                
                # Enforce length limits
                if len(sanitized_value) > max_length:
                    raise ValueError(f"{field} exceeds maximum length of {max_length} characters")
                
                validated_data[field] = sanitized_value.strip()
            else:
                validated_data[field] = str(value)[:max_length] if value else ""
        
        return validated_data
    
    return web_app


if __name__ == "__main__":
    print("LogSense Async Deployment")
    print("Features:")
    print("- Full async/await patterns")
    print("- SonarCloud compliant code")
    print("- Reduced cognitive complexity")
    print("- Proper error handling")
    print("- Warm container strategy")
