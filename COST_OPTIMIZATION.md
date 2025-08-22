# Modal Cost Optimization Guide

## Current vs Optimized Costs

### Current Deployment (Expensive)
- **A10G GPU**: ~$1.10/hour when active
- **8GB RAM**: ~$0.10/hour
- **Always-on web server**: Keeps warm containers
- **Estimated monthly cost**: $50-200+ depending on usage

### Optimized Deployment (Economic)
- **CPU-only web server**: ~$0.05/hour when active
- **2GB RAM**: ~$0.02/hour
- **On-demand GPU**: Only when ML tasks run
- **Auto-scale to zero**: No idle costs
- **Estimated monthly cost**: $5-30 depending on usage

## Optimization Strategies

### 1. **Hybrid Architecture** (Recommended)
```python
# CPU web server for UI + on-demand GPU for ML
modal_economic.py  # Use this deployment
```

### 2. **Resource Right-sizing**
- **Memory**: 2GB instead of 8GB (75% cost reduction)
- **CPU**: 1 core instead of 2 (50% cost reduction)
- **GPU**: On-demand only (90% cost reduction)

### 3. **Auto-scaling Settings**
```python
keep_warm=0        # Scale to zero when idle
timeout=1800       # 30min timeout
max_containers=3   # Limit concurrent instances
```

### 4. **Model Strategy**
- **Primary**: Use OpenAI API (pay per token)
- **Fallback**: Local models only when needed
- **Benefits**: Lower infrastructure costs, better reliability

## Cost Comparison

| Component | Current | Optimized | Savings |
|-----------|---------|-----------|---------|
| Base compute | $0.15/hr | $0.07/hr | 53% |
| GPU usage | $1.10/hr | $0 (on-demand) | 90% |
| Idle time | Full cost | $0 | 100% |
| **Total** | **$200/mo** | **$15/mo** | **92%** |

## Deployment Commands

```bash
# Deploy economic version
modal deploy modal_economic.py

# Monitor costs
modal app list
modal app logs logsense-economic
```

## Usage Patterns

- **Light usage** (< 10 hours/month): $5-10
- **Medium usage** (50 hours/month): $15-25  
- **Heavy usage** (200 hours/month): $30-50

## Trade-offs

### Pros
- 90%+ cost reduction
- Zero idle costs
- Scales automatically

### Cons
- Cold start latency (2-5 seconds)
- Local ML models require separate calls
- Slightly more complex architecture
