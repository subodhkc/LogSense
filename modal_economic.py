"""
Economic Modal deployment for LogSense - optimized for cost
"""

import modal

app = modal.App("logsense-economic")

# Lightweight image with all required dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .run_commands("git clone https://github.com/subodhkc/LogSense.git /app")
    .pip_install(
        "streamlit>=1.28.0",
        "pandas>=1.5.0", 
        "scikit-learn>=1.3.0",
        "numpy>=1.24.0",
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
        "reportlab>=4.2.2",
        "pyyaml>=6.0.1",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        "plotly>=5.15.0",
        "pypdf>=3.0.0",
        "altair>=5.0.0"
        # Still excluding: torch, transformers, peft (heavy ML libs)
    )
    .workdir("/app")
    .env({"PYTHONPATH": "/app"})  # Fix import paths
)

# CPU-only web server (no GPU unless needed)
@app.function(
    image=image,
    # No GPU - uses CPU only
    memory=2048,  # Reduced to 2GB
    cpu=1,        # Single CPU
    secrets=[modal.Secret.from_name("openai-api-key")],
    # Auto-scale to zero when idle
    min_containers=0,  # Don't keep containers warm
    timeout=1800, # 30 min timeout
)
@modal.concurrent(max_inputs=100)
@modal.web_server(8000)
def web():
    import subprocess
    import os
    import time
    
    # Set environment variables
    os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
    os.environ["MODEL_BACKEND"] = "openai"  # Use OpenAI instead of local models
    os.environ["DISABLE_ML_MODELS"] = "true"  # Disable heavy ML models
    os.environ["PYTHONPATH"] = "/app"
    
    # Change to app directory
    os.chdir("/app")
    
    # Use shell=True for proper command execution (ChatGPT's approach)
    cmd = (
        "streamlit run skc_log_analyzer.py "
        "--server.port 8000 "
        "--server.address 0.0.0.0 "
        "--server.headless true "
        "--server.enableCORS false "
        "--server.enableXsrfProtection false"
    )
    
    # Start Streamlit in background
    process = subprocess.Popen(cmd, shell=True)
    
    # Give Streamlit time to start before Modal begins serving
    time.sleep(5)
    
    # Keep the function alive - wait for Streamlit process to finish
    # This prevents Modal from thinking the web server is done
    process.wait()

# On-demand GPU function for heavy ML tasks only
@app.function(
    image=image.pip_install("torch>=2.0.0", "transformers>=4.30.0", "peft>=0.11.1"),
    gpu="A10G",
    memory=8192,
    secrets=[modal.Secret.from_name("openai-api-key")],
    min_containers=0,  # Scale to zero when not used
    timeout=600,  # 10 min timeout for ML tasks
)
def ml_inference(text_input: str, task_type: str):
    """On-demand ML inference - only spins up GPU when called"""
    if task_type == "summarize":
        # Import heavy libraries only when needed
        from modules.phi2_inference import phi2_summarize
        return phi2_summarize(text_input)
    elif task_type == "cluster":
        from clustering_model import perform_clustering
        return perform_clustering(text_input)
    # Add other ML tasks as needed

if __name__ == "__main__":
    print("Economic deployment - CPU web server + on-demand GPU ML")
    print("Deploy with: modal deploy modal_economic.py")
