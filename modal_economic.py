"""
Economic Modal deployment for LogSense - optimized for cost
"""

import modal

app = modal.App("logsense-economic")

# Lightweight image
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
        "pyyaml>=6.0.1"
        # Removed: torch, transformers, peft (heavy ML libs)
    )
    .workdir("/app")
)

# CPU-only web server (no GPU unless needed)
@app.function(
    image=image,
    # No GPU - uses CPU only
    memory=2048,  # Reduced to 2GB
    cpu=1,        # Single CPU
    secrets=[modal.Secret.from_name("openai-api-key")],
    # Auto-scale to zero when idle
    keep_warm=0,  # Don't keep containers warm
    timeout=1800, # 30 min timeout
)
@app.web_server(8000)
def web():
    import subprocess
    import os
    
    os.environ["STREAMLIT_WATCHER_TYPE"] = "none"
    os.environ["MODEL_BACKEND"] = "openai"  # Use OpenAI instead of local models
    
    subprocess.run([
        "streamlit", "run", "skc_log_analyzer.py",
        "--server.port", "8000",
        "--server.address", "0.0.0.0"
    ])

# On-demand GPU function for heavy ML tasks only
@app.function(
    image=image.pip_install("torch>=2.0.0", "transformers>=4.30.0", "peft>=0.11.1"),
    gpu="A10G",
    memory=8192,
    secrets=[modal.Secret.from_name("openai-api-key")],
    keep_warm=0,  # Scale to zero when not used
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
