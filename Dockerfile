# Dockerfile for SKC Log Reader with Phi-2 inference
# CPU-only base; for GPU, use nvidia/cuda base and install cudnn + matching torch
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRANSFORMERS_CACHE=/root/.cache/huggingface

WORKDIR /app

# System deps minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir streamlit

COPY . .

EXPOSE 8501

# Default to CPU; override MODEL_NAME/QUANTIZATION at runtime
ENV MODEL_NAME=microsoft/phi-2 \
    QUANTIZATION=none \
    MODEL_BACKEND=phi2

CMD ["streamlit", "run", "skc_log_analyzer.py", "--server.port=8501", "--server.address=0.0.0.0"]
