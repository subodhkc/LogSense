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

#### Async I/O Implementation
- All file operations use `aiofiles` for non-blocking I/O
- HTTP requests use `httpx.AsyncClient` with retry logic
- Replaced `time.sleep()` with `asyncio.sleep()` throughout

#### HTTP and File Safety Wrappers
- `infra/http.py`: Async HTTP client with timeout and error handling
- `infra/storage.py`: Safe file operations with cleanup and validation
- `infra/security.py`: Content-Type validation, CORS, security headers
- `infra/error_handler.py`: Global error handling with standardized codes

#### Security Features
- Input validation and XSS protection on all user inputs
- Secure subprocess calls with `shell=False` and timeouts
- No dangerous primitives (unsafe tarfile, raw XML-RPC, MD5/SHA1 for security)
- Defensive imports and probes for GPU availability
- Security headers: CSP, HSTS, X-Content-Type-Options, X-Frame-Options
- CORS allowlist (no wildcard origins)
- Request size limits (25MB uploads, 1MB JSON)

#### Data Handling and Compliance
**Input Processing**
- File uploads limited to `.log`, `.txt`, `.zip` formats
- Maximum file size: 25MB per upload
- Content-Type validation enforced on all endpoints
- Input sanitization prevents XSS and injection attacks

**Storage and Retention**
- Temporary files created in system temp directory
- Automatic cleanup after processing completion or errors
- No persistent storage of user data beyond session cache
- Session data cleared on container restart

**Data Export and Redaction**
- Sensitive data (tokens, emails, passwords) redacted from logs
- Error responses use standardized codes (E.REQ.001, E.SRV.001, etc.)
- No stack traces exposed to clients
- SBOM (Software Bill of Materials) generated for compliance

**Error Code Taxonomy**
- **E.REQ.xxx**: Client request errors (invalid content-type, file too large)
- **E.SRV.xxx**: Server processing errors (analysis failed, storage error)
- **E.SEC.xxx**: Security-related errors (unauthorized, rate limited)

#### Quality Gates
- CI pipeline includes security scanning (pip-audit, bandit)
- SBOM generation for license compliance
- Pytest configuration excludes non-test files
- All tests pass with strict collection rules

#### ADRs (Architectural Decision Records)
- **ADR-001**: Async I/O & httpx choice for performance and scalability
- **ADR-002**: Schema validation at input boundaries for security and reliability

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