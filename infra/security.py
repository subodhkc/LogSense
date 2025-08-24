"""Security middleware and hardening utilities."""
import logging
import re
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Security constants
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25MB
MAX_JSON_SIZE = 1 * 1024 * 1024     # 1MB
ALLOWED_ORIGINS = [
    "https://subodhkc--logsense-native-native-app.modal.run",
    "https://subodhkc--logsense-async-async-app.modal.run", 
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

# Error code taxonomy
class ErrorCodes:
    # Client errors (4xx)
    INVALID_CONTENT_TYPE = "E.REQ.001"
    FILE_TOO_LARGE = "E.REQ.002"
    INVALID_FILE_TYPE = "E.REQ.003"
    MISSING_REQUIRED_FIELD = "E.REQ.004"
    
    # Server errors (5xx)
    PROCESSING_FAILED = "E.SRV.001"
    AI_ANALYSIS_FAILED = "E.SRV.002"
    STORAGE_ERROR = "E.SRV.003"
    
    # Security errors
    UNAUTHORIZED_ACCESS = "E.SEC.001"
    RATE_LIMIT_EXCEEDED = "E.SEC.002"

def add_security_headers(app):
    """Add security headers middleware to FastAPI app."""
    
    @app.middleware("http")
    async def security_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://assets.website-files.com; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "upgrade-insecure-requests"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # HSTS for HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return response

def add_cors_middleware(app):
    """Add CORS middleware with strict allowlist."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
        max_age=3600
    )

def validate_content_type(request: Request, expected_type: str):
    """Validate request Content-Type header."""
    content_type = request.headers.get("content-type", "").lower()
    
    if expected_type == "application/json":
        if not content_type.startswith("application/json"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={
                    "error_code": ErrorCodes.INVALID_CONTENT_TYPE,
                    "message": "Content-Type must be application/json"
                }
            )
    elif expected_type == "multipart/form-data":
        if not content_type.startswith("multipart/form-data"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={
                    "error_code": ErrorCodes.INVALID_CONTENT_TYPE,
                    "message": "Content-Type must be multipart/form-data"
                }
            )

async def validate_request_size(request: Request, max_size: int = MAX_JSON_SIZE):
    """Validate request body size."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error_code": ErrorCodes.FILE_TOO_LARGE,
                "message": f"Request too large. Maximum size: {max_size // (1024*1024)}MB"
            }
        )

def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize sensitive data from logs."""
    sensitive_patterns = [
        r'token["\s]*[:=]["\s]*([^"\s,}]+)',
        r'password["\s]*[:=]["\s]*([^"\s,}]+)',
        r'api[_-]?key["\s]*[:=]["\s]*([^"\s,}]+)',
        r'secret["\s]*[:=]["\s]*([^"\s,}]+)',
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # emails
    ]
    
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized_value = value
            for pattern in sensitive_patterns:
                sanitized_value = re.sub(pattern, "[REDACTED]", sanitized_value, flags=re.IGNORECASE)
            sanitized[key] = sanitized_value
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    
    return sanitized

def create_error_response(error_code: str, message: str, status_code: int = 500) -> JSONResponse:
    """Create standardized error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error_code": error_code,
            "message": message,
            "timestamp": "2025-08-24T12:40:00Z"
        }
    )

def validate_file_upload(file_content: bytes, filename: str) -> None:
    """Validate uploaded file."""
    # Size check
    if len(file_content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error_code": ErrorCodes.FILE_TOO_LARGE,
                "message": f"File too large. Maximum size: {MAX_UPLOAD_SIZE // (1024*1024)}MB"
            }
        )
    
    # File type check
    allowed_extensions = ['.log', '.txt', '.zip']
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": ErrorCodes.INVALID_FILE_TYPE,
                "message": f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            }
        )
