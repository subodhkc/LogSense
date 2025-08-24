# LogSense - Enterprise Log Analysis Platform

LogSense is a comprehensive log analysis platform that combines traditional analytics with AI-powered insights for enterprise system troubleshooting and root cause analysis.

## Features

- **Multi-format Log Support**: Process .log, .txt files and .zip archives
- **AI-Powered Analysis**: Local Phi-2 LLM and OpenAI integration for intelligent insights
- **Interactive Dashboard**: Modern web interface with real-time analysis
- **Template Extraction**: Automatic pattern recognition and log templating
- **ML Insights**: Clustering, anomaly detection, and severity prediction
- **Correlation Analysis**: Event relationship mapping and causal chain detection
- **Report Generation**: Comprehensive PDF reports with AI summaries
- **Modal Deployment**: Cloud-ready with GPU acceleration support

## Architecture & Security

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend/UI   │    │   Domain Logic  │    │ Infrastructure  │
│                 │    │                 │    │                 │
│ • HTML/CSS/JS   │───▶│ • Analysis      │───▶│ • HTTP Client   │
│ • Accessibility │    │ • AI/ML         │    │ • File Storage  │
│ • No inline JS  │    │ • Report Gen    │    │ • Async I/O     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │      Tests      │
                       │                 │
                       │ • Unit Tests    │
                       │ • Integration   │
                       │ • Security      │
                       └─────────────────┘
```

### Security Posture

## [U+1F9F0] Getting Started

### Installation
```bash
git clone <repository-url>
cd LogSense
pip install -r requirements.txt
```

### Quick Start
```bash
# Local development
streamlit run skc_log_analyzer.py

# Or use the web interface
python serve_streamlit.py
```

### Project Structure
```
LogSense/
├── skc_log_analyzer.py      # Main application entry point
├── analysis.py              # Core log analysis engine
├── ai_rca.py               # AI-powered root cause analysis
├── report/                 # PDF report generation
├── config/                 # Configuration files
│   ├── redact.json        # Privacy redaction rules
│   └── model.yaml         # AI model settings
├── plans/                  # Test plan templates
└── templates/              # Web UI templates
```

## [U+1F510] Security & Privacy

**Data Protection**
- All log processing happens locally on your machine
- PII redaction before any external API calls
- No sensitive data leaves your environment without explicit consent
- Configurable privacy rules for different data types

**Deployment Options**
- **Local**: Run on your desktop with `streamlit run skc_log_analyzer.py`
- **Modal Cloud**: Deploy to Modal for team access with GPU acceleration
- **Docker**: Containerized deployment for enterprise environments

## AI Configuration

LogSense supports multiple AI backends for enhanced analysis:

**Local AI (Recommended)**
- Uses Microsoft Phi-2 model running entirely offline
- No internet connection required for AI analysis
- Full privacy and data control

**Cloud AI (Optional)**
- OpenAI integration for advanced natural language processing
- Only redacted logs are sent to external services
- Requires `OPENAI_API_KEY` environment variable

**Configuration Options**
```bash
# Environment variables
MODEL_BACKEND=phi2          # or 'openai'
MODEL_NAME=microsoft/phi-2   # Local model path
QUANTIZATION=4bit           # Memory optimization
```

## Usage Tips

1. **Start with local analysis** - Use the Python analytics engine first
2. **Upload ZIP files** - Faster processing of multiple log files
3. **Review redaction** - Check privacy settings before enabling cloud AI
4. **Export reports** - Generate PDF summaries for stakeholders

---

**Developed by Subodh KC**  
*Enterprise log analysis made simple*