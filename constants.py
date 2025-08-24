"""Constants for LogSense application to eliminate string literal duplication."""

# Server Configuration
DEFAULT_PORT = 8000
DEFAULT_HOST = "0.0.0.0"
STARTUP_TIMEOUT = 600
SCALEDOWN_WINDOW = 600
MEMORY_SIZE = 2048
CPU_COUNT = 2
MAX_TIMEOUT = 900

# File Extensions
SUPPORTED_LOG_EXTENSIONS = [".log", ".txt", ".zip"]
TEMP_FILE_PREFIX = "logsense_"

# API Endpoints
UPLOAD_ENDPOINT = "/upload"
HEALTH_ENDPOINT = "/health"
ML_ANALYSIS_ENDPOINT = "/ml_analysis"
GENERATE_REPORT_ENDPOINT = "/generate_report"

# Error Messages
FILE_NOT_FOUND_ERROR = "File not found or inaccessible"
PROCESSING_ERROR = "Error processing file"
INVALID_FILE_TYPE_ERROR = "Invalid file type. Supported: .log, .txt, .zip"
UPLOAD_FAILED_ERROR = "Upload failed"
NETWORK_ERROR = "Network error occurred"

# Success Messages
UPLOAD_SUCCESS = "File uploaded successfully"
ANALYSIS_COMPLETE = "Analysis completed successfully"
REPORT_GENERATED = "Report generated successfully"

# Log Levels
LOG_LEVELS = {
    "DEBUG": "debug",
    "INFO": "info", 
    "WARNING": "warning",
    "ERROR": "error",
    "CRITICAL": "critical",
    "FATAL": "fatal"
}

# Analysis Types
ML_ANALYSIS_TYPES = ["clustering", "severity", "anomaly"]
CORRELATION_TYPES = ["temporal", "causal"]
REPORT_TYPES = ["standard", "local_ai", "cloud_ai"]

# Environment Variables
ENV_STREAMLIT_STATS = "STREAMLIT_BROWSER_GATHER_USAGE_STATS"
ENV_STREAMLIT_WATCHER = "STREAMLIT_WATCHER_TYPE"
ENV_MODEL_BACKEND = "MODEL_BACKEND"
ENV_DISABLE_ML = "DISABLE_ML_MODELS"
ENV_PYTHON_PATH = "PYTHONPATH"

# UI Configuration
SESSION_ID_PREFIX = "LS-"
SESSION_ID_LENGTH = 8
MAX_EVENTS_DISPLAY = 20
PROGRESS_UPDATE_INTERVAL = 200

# File Processing
MAX_FILE_SIZE_MB = 100
CHUNK_SIZE = 8192
ENCODING_UTF8 = "utf-8"
