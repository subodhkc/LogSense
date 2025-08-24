"""Async file storage with try/except and logging."""
import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Union, BinaryIO
import aiofiles
import aiofiles.tempfile

logger = logging.getLogger(__name__)

class StorageError(Exception):
    """Custom storage error for file operations."""
    pass

async def read_text_file(
    file_path: Union[str, Path], 
    encoding: str = "utf-8", 
    errors: str = "ignore"
) -> str:
    """Safely read text file with error handling."""
    try:
        async with aiofiles.open(file_path, 'r', encoding=encoding, errors=errors) as f:
            content = await f.read()
            logger.debug(f"Successfully read text file: {file_path}")
            return content
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise StorageError(f"File not found: {file_path}")
    except PermissionError:
        logger.error(f"Permission denied reading file: {file_path}")
        raise StorageError(f"Permission denied: {file_path}")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise StorageError(f"Failed to read file {file_path}: {e}")

async def read_binary_file(file_path: Union[str, Path]) -> bytes:
    """Safely read binary file with error handling."""
    try:
        async with aiofiles.open(file_path, 'rb') as f:
            content = await f.read()
            logger.debug(f"Successfully read binary file: {file_path}")
            return content
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise StorageError(f"File not found: {file_path}")
    except PermissionError:
        logger.error(f"Permission denied reading file: {file_path}")
        raise StorageError(f"Permission denied: {file_path}")
    except Exception as e:
        logger.error(f"Error reading binary file {file_path}: {e}")
        raise StorageError(f"Failed to read file {file_path}: {e}")

async def write_text_file(
    file_path: Union[str, Path], 
    content: str, 
    encoding: str = "utf-8",
    create_dirs: bool = True
) -> None:
    """Safely write text file with error handling."""
    try:
        if create_dirs:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        async with aiofiles.open(file_path, 'w', encoding=encoding) as f:
            await f.write(content)
            logger.debug(f"Successfully wrote text file: {file_path}")
    except PermissionError:
        logger.error(f"Permission denied writing file: {file_path}")
        raise StorageError(f"Permission denied: {file_path}")
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        raise StorageError(f"Failed to write file {file_path}: {e}")

async def write_binary_file(
    file_path: Union[str, Path], 
    content: bytes,
    create_dirs: bool = True
) -> None:
    """Safely write binary file with error handling."""
    try:
        if create_dirs:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
            logger.debug(f"Successfully wrote binary file: {file_path}")
    except PermissionError:
        logger.error(f"Permission denied writing file: {file_path}")
        raise StorageError(f"Permission denied: {file_path}")
    except Exception as e:
        logger.error(f"Error writing binary file {file_path}: {e}")
        raise StorageError(f"Failed to write file {file_path}: {e}")

async def create_temp_file(
    content: Union[str, bytes], 
    suffix: str = ".tmp",
    prefix: str = "logsense_",
    text_mode: bool = True
) -> str:
    """Create temporary file with content and return path."""
    try:
        if text_mode and isinstance(content, str):
            async with aiofiles.tempfile.NamedTemporaryFile(
                mode='w', 
                delete=False, 
                suffix=suffix, 
                prefix=prefix,
                encoding='utf-8'
            ) as temp_file:
                await temp_file.write(content)
                temp_path = temp_file.name
        elif not text_mode and isinstance(content, bytes):
            async with aiofiles.tempfile.NamedTemporaryFile(
                mode='wb', 
                delete=False, 
                suffix=suffix, 
                prefix=prefix
            ) as temp_file:
                await temp_file.write(content)
                temp_path = temp_file.name
        else:
            raise ValueError("Content type must match text_mode setting")
        
        logger.debug(f"Created temporary file: {temp_path}")
        return temp_path
    except Exception as e:
        logger.error(f"Error creating temporary file: {e}")
        raise StorageError(f"Failed to create temporary file: {e}")

async def cleanup_temp_file(file_path: str, delay: float = 0.1) -> None:
    """Safely clean up temporary file with optional delay."""
    try:
        if delay > 0:
            await asyncio.sleep(delay)  # Allow file handles to close
        
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")

def file_exists(file_path: Union[str, Path]) -> bool:
    """Check if file exists safely."""
    try:
        return os.path.exists(file_path) and os.path.isfile(file_path)
    except Exception:
        return False

def get_file_size(file_path: Union[str, Path]) -> int:
    """Get file size safely, returns -1 if error."""
    try:
        return os.path.getsize(file_path)
    except Exception:
        return -1

def validate_file_path(file_path: Union[str, Path], max_length: int = 260) -> bool:
    """Validate file path for security and length."""
    try:
        path_str = str(file_path)
        
        # Check length
        if len(path_str) > max_length:
            return False
        
        # Check for path traversal attempts
        if ".." in path_str or path_str.startswith("/"):
            return False
        
        # Check for invalid characters (Windows)
        invalid_chars = '<>:"|?*'
        if any(char in path_str for char in invalid_chars):
            return False
        
        return True
    except Exception:
        return False
