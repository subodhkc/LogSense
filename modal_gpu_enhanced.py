"""Modal GPU deployment with MODAL_USE_GPU flag and defensive imports."""
import os
import modal
from datetime import datetime
from typing import Dict, Any, Optional

# Environment configuration
MODAL_USE_GPU = int(os.getenv("MODAL_USE_GPU", "1"))
APP_NAME = "logsense-gpu"

# GPU image with CUDA support
gpu_image = (
    modal.Image.from_registry("nvidia/cuda:12.1-devel-ubuntu22.04", add_python="3.11")
    .pip_install_from_requirements("requirements-modal-gpu.txt")
    .env({
        "MODAL_USE_GPU": "1",
        "PYTHONPATH": "/root/app",
        "CUDA_VISIBLE_DEVICES": "0"
    })
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=gpu_image)

@app.function(
    gpu=modal.gpu.A10G(),  # GPU allocation
    timeout=600,
    memory=4096,  # Higher memory for GPU workloads
    min_containers=1,  # Warm containers for ML
    retries=modal.Retries(max_retries=1)
)
@modal.asgi_app()
def gpu_app():
    """GPU-enabled FastAPI app with defensive torch imports."""
    import sys
    sys.path.insert(0, '/root/app')
    
    from fastapi import FastAPI, File, UploadFile, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from infra.http import AsyncHTTPClient
    from infra.storage import read_text_file, create_temp_file, cleanup_temp_file
    import asyncio
    import logging
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    web_app = FastAPI(title="LogSense GPU - AI Analysis", version="1.0.0")
    
    # Mount static files and templates
    web_app.mount("/static", StaticFiles(directory="/root/app/static"), name="static")
    templates = Jinja2Templates(directory="/root/app/templates")
    
    # Session cache and GPU status
    session_cache: Dict[str, Any] = {}
    gpu_available = False
    torch_available = False
    
    # Defensive GPU/torch probing
    def _probe_gpu_availability():
        """Safely probe GPU and torch availability."""
        nonlocal gpu_available, torch_available
        
        try:
            import torch
            torch_available = True
            logger.info("Torch imported successfully")
            
            if torch.cuda.is_available():
                gpu_available = True
                device_count = torch.cuda.device_count()
                logger.info(f"CUDA available with {device_count} devices")
            else:
                logger.warning("CUDA not available, falling back to CPU")
        except ImportError as e:
            logger.error(f"Torch import failed: {e}")
        except Exception as e:
            logger.error(f"GPU probe failed: {e}")
    
    # Initialize GPU on startup
    _probe_gpu_availability()
    
    @web_app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        """Serve main page."""
        return templates.TemplateResponse("index.html", {"request": request})
    
    @web_app.get("/health")
    async def health_check():
        """GPU health check with capability info."""
        return {
            "status": "healthy",
            "deployment": "gpu-enabled",
            "gpu_available": gpu_available,
            "torch_available": torch_available,
            "memory": "4096MB",
            "modal_use_gpu": MODAL_USE_GPU,
            "timestamp": datetime.now().isoformat()
        }
    
    @web_app.post("/upload")
    async def upload_file(file: UploadFile = File(...)):
        """GPU-enabled file upload with AI analysis."""
        try:
            # Validate file
            if not file.filename or not file.filename.endswith(('.log', '.txt')):
                return JSONResponse({
                    "success": False,
                    "message": "Invalid file type. Supported: .log, .txt"
                }, status_code=400)
            
            # Read file content
            content = await file.read()
            text_content = content.decode('utf-8', errors='ignore')
            
            # Create temporary file for analysis
            temp_path = await create_temp_file(text_content, suffix=".log")
            
            try:
                # Parse events using analysis module
                from analysis import parse_log_file
                events = parse_log_file(temp_path)
                
                # AI analysis if GPU available
                ai_analysis = None
                if gpu_available and torch_available:
                    ai_analysis = await _run_ai_analysis(events[:20])  # Limit for performance
                
                # Store in cache
                session_cache["current"] = {
                    "events": events[:100],  # Store more events for GPU
                    "ai_analysis": ai_analysis,
                    "filename": file.filename,
                    "upload_time": datetime.now().isoformat(),
                    "gpu_used": gpu_available
                }
                
                return JSONResponse({
                    "success": True,
                    "message": f"File processed with {'GPU AI' if gpu_available else 'CPU'} analysis. Found {len(events)} events.",
                    "event_count": len(events),
                    "gpu_analysis": gpu_available,
                    "ai_insights": ai_analysis
                })
                
            finally:
                await cleanup_temp_file(temp_path)
            
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return JSONResponse({
                "success": False,
                "message": f"Upload failed: {str(e)}"
            }, status_code=500)
    
    @web_app.post("/ml_analysis")
    async def ml_analysis():
        """Advanced ML analysis endpoint."""
        try:
            current_data = session_cache.get("current")
            if not current_data:
                return JSONResponse({
                    "success": False,
                    "message": "No data available. Upload a file first."
                }, status_code=400)
            
            if not gpu_available:
                return JSONResponse({
                    "success": False,
                    "message": "GPU not available for ML analysis"
                }, status_code=503)
            
            events = current_data.get("events", [])
            ml_results = await _run_advanced_ml_analysis(events)
            
            return JSONResponse({
                "success": True,
                "ml_results": ml_results,
                "gpu_accelerated": True
            })
            
        except Exception as e:
            logger.error(f"ML analysis error: {e}")
            return JSONResponse({
                "success": False,
                "message": f"ML analysis failed: {str(e)}"
            }, status_code=500)
    
    @web_app.post("/submit_context")
    async def submit_context(request: Request):
        """Handle context submission."""
        try:
            data = await request.json()
            current_data = session_cache.get("current", {})
            current_data["context"] = data
            session_cache["current"] = current_data
            
            return JSONResponse({
                "status": "success",
                "message": "Context saved"
            })
        except Exception as e:
            return JSONResponse({
                "status": "error",
                "message": str(e)
            }, status_code=500)
    
    async def _run_ai_analysis(events):
        """Run AI analysis with defensive imports."""
        if not torch_available:
            return {"error": "Torch not available"}
        
        try:
            # Lazy import AI modules only when needed
            from ai_rca import analyze_events_with_ai
            
            # Run AI analysis with timeout
            analysis_task = asyncio.create_task(
                asyncio.to_thread(analyze_events_with_ai, events)
            )
            
            try:
                result = await asyncio.wait_for(analysis_task, timeout=30.0)
                return result
            except asyncio.TimeoutError:
                return {"error": "AI analysis timeout", "fallback": "basic"}
                
        except ImportError as e:
            logger.error(f"AI module import failed: {e}")
            return {"error": "AI modules not available"}
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {"error": str(e)}
    
    async def _run_advanced_ml_analysis(events):
        """Advanced ML analysis with GPU acceleration."""
        if not gpu_available:
            return {"error": "GPU not available"}
        
        try:
            # Lazy import ML modules
            import torch
            from modules.phi2_inference import load_model_if_needed, generate_analysis
            
            # Load model on GPU
            model_info = load_model_if_needed()
            if not model_info:
                return {"error": "Model loading failed"}
            
            # Generate analysis
            analysis = generate_analysis(events, model_info)
            
            return {
                "model_used": "phi2-gpu",
                "device": "cuda" if torch.cuda.is_available() else "cpu",
                "analysis": analysis,
                "event_count": len(events)
            }
            
        except Exception as e:
            logger.error(f"Advanced ML analysis failed: {e}")
            return {"error": str(e)}
    
    return web_app

if __name__ == "__main__":
    print("LogSense GPU-Enhanced Deployment")
    print(f"- MODAL_USE_GPU: {MODAL_USE_GPU}")
    print("- GPU acceleration enabled")
    print("- AI/ML analysis capabilities")
