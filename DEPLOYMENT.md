# LogSense Modal Deployment Guide

This guide walks you through deploying LogSense to Modal with GPU support for ML features.

## Prerequisites

1. **Modal Account**: Sign up at https://modal.com/signup
2. **OpenAI API Key**: For cloud AI features (optional)

## Setup Steps

### 1. Install Modal CLI
```bash
pip install modal
modal setup
```

### 2. Configure Secrets (Optional)
If you want cloud AI features, set up your OpenAI API key:
```bash
modal secret create openai-api-key OPENAI_API_KEY=your_openai_key_here
```

### 3. Deploy to Modal

**Development (with hot reload):**
```bash
modal serve modal_deploy.py
```

**Production deployment:**
```bash
modal deploy modal_deploy.py
```

## Features

### GPU-Accelerated ML
- **Clustering**: Groups similar log events
- **Anomaly Detection**: Flags unusual patterns
- **AI Analysis**: Phi-2 model for offline RCA

### Auto-Scaling
- Handles multiple concurrent users
- Scales GPU resources on demand
- 8GB RAM + A10G GPU for ML workloads

### Security
- Environment variables via Modal secrets
- No hardcoded API keys
- Secure file handling

## Configuration

### Hardware Specs
- **GPU**: NVIDIA A10G (24GB VRAM)
- **RAM**: 8GB (16GB for ML operations)
- **CPU**: 2-4 cores
- **Concurrent Users**: Up to 10

### Environment Variables
```bash
STREAMLIT_WATCHER_TYPE=none
MODEL_BACKEND=phi2
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TIMEOUT=30
```

## Costs

Modal pricing (approximate):
- **GPU (A10G)**: ~$0.60/hour when active
- **CPU/RAM**: ~$0.10/hour when active
- **Storage**: Minimal for this app
- **Auto-scaling**: Pay only when users are active

## Monitoring

After deployment, Modal provides:
- Real-time logs and metrics
- Usage analytics
- Performance monitoring
- Error tracking

## Troubleshooting

**Common Issues:**
1. **Import errors**: Check requirements-modal.txt
2. **GPU timeout**: Increase timeout in modal_deploy.py
3. **Memory issues**: Adjust memory limits
4. **Secrets not found**: Run modal secret list to verify

**Support:**
- Modal Slack: https://modal.com/slack
- Documentation: https://modal.com/docs
- GitHub Issues: Create issues in LogSense repo
