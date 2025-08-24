"""Global error handling and logging utilities."""
import logging
import traceback
import tempfile
import os
from typing import Any, Dict, Optional
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .security import ErrorCodes, sanitize_log_data, create_error_response

logger = logging.getLogger(__name__)

class GlobalErrorHandler:
    """Global error handler for FastAPI applications."""
    
    def __init__(self, app):
        self.app = app
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup global exception handlers."""
        
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            """Handle HTTP exceptions."""
            logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
            
            # If detail is already structured, return as-is
            if isinstance(exc.detail, dict):
                return JSONResponse(
                    status_code=exc.status_code,
                    content=exc.detail
                )
            
            # Otherwise, wrap in standard format
            return create_error_response(
                error_code=ErrorCodes.PROCESSING_FAILED,
                message=str(exc.detail),
                status_code=exc.status_code
            )
        
        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(request: Request, exc: RequestValidationError):
            """Handle request validation errors."""
            logger.warning(f"Validation error: {exc.errors()}")
            
            return create_error_response(
                error_code=ErrorCodes.MISSING_REQUIRED_FIELD,
                message="Invalid request data",
                status_code=422
            )
        
        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle all other exceptions."""
            # Log full traceback for debugging
            logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
            
            # Clean up any temp files that might be left behind
            await self.cleanup_temp_files()
            
            # Return generic error to client (no stack trace)
            return create_error_response(
                error_code=ErrorCodes.PROCESSING_FAILED,
                message="An internal error occurred",
                status_code=500
            )
    
    async def cleanup_temp_files(self):
        """Clean up temporary files after errors."""
        try:
            temp_dir = tempfile.gettempdir()
            for filename in os.listdir(temp_dir):
                if filename.startswith(('tmp', 'upload_', 'log_analysis_')):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")

def setup_logging():
    """Setup secure logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Set specific log levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.ERROR)

class SecureLogger:
    """Logger that automatically sanitizes sensitive data."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log info message with optional sanitized data."""
        if data:
            sanitized_data = sanitize_log_data(data)
            self.logger.info(f"{message} - Data: {sanitized_data}")
        else:
            self.logger.info(message)
    
    def warning(self, message: str, data: Optional[Dict[str, Any]] = None):
        """Log warning message with optional sanitized data."""
        if data:
            sanitized_data = sanitize_log_data(data)
            self.logger.warning(f"{message} - Data: {sanitized_data}")
        else:
            self.logger.warning(message)
    
    def error(self, message: str, data: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log error message with optional sanitized data."""
        if data:
            sanitized_data = sanitize_log_data(data)
            self.logger.error(f"{message} - Data: {sanitized_data}", exc_info=exc_info)
        else:
            self.logger.error(message, exc_info=exc_info)

def handle_ai_analysis_error(error: Exception) -> JSONResponse:
    """Handle AI analysis specific errors."""
    error_msg = str(error)
    
    if "timeout" in error_msg.lower():
        return create_error_response(
            error_code=ErrorCodes.AI_ANALYSIS_FAILED,
            message="AI analysis timed out. Please try with a smaller file.",
            status_code=408
        )
    elif "memory" in error_msg.lower() or "cuda" in error_msg.lower():
        return create_error_response(
            error_code=ErrorCodes.AI_ANALYSIS_FAILED,
            message="Insufficient resources for AI analysis.",
            status_code=503
        )
    else:
        return create_error_response(
            error_code=ErrorCodes.AI_ANALYSIS_FAILED,
            message="AI analysis failed. Please try again.",
            status_code=500
        )

def handle_storage_error(error: Exception) -> JSONResponse:
    """Handle storage specific errors."""
    return create_error_response(
        error_code=ErrorCodes.STORAGE_ERROR,
        message="File storage operation failed.",
        status_code=500
    )
