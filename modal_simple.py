# modal_simple.py - Simple HTTP server approach
import modal
import os

APP_NAME = "logsense-simple"

# Create image with only essential dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install_from_requirements("requirements-modal.txt", find_links_args=["-c", "constraints.txt"])
    .copy_local_file("ai_rca.py", "/root/ai_rca.py")
    .copy_local_file("analysis.py", "/root/analysis.py")
    .env({"PYTHONPATH": "/root"})
    .add_local_dir(".", remote_path="/root/app")
)

app = modal.App(name=APP_NAME, image=image)

@app.function(image=image, timeout=300)
@modal.web_endpoint(method="POST")
def test_ai_fix():
    """Test the AI analysis fix"""
    try:
        import sys
        sys.path.insert(0, "/root")
        
        import ai_rca
        
        # Create test event
        class TestEvent:
            def __init__(self):
                self.timestamp = "2025-08-22 10:00:00"
                self.severity = "ERROR"
                self.component = "TestComponent"
                self.message = "Test error message"
        
        events = [TestEvent()]
        
        # Test AI analysis with timeout protection
        result = ai_rca.generate_summary(events, offline=True)
        
        return {
            "status": "success",
            "ai_result": result[:200] if result else "No result",
            "message": "AI analysis fix working"
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "message": "AI analysis failed"
        }

@app.function(timeout=24*60*60)
@modal.web_server(port=8000, startup_timeout=600)
def run():
    os.chdir("/root/app")
    
    # Direct exec - no subprocess
    os.system("streamlit run skc_log_analyzer_minimal.py --server.port 8000 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false")
