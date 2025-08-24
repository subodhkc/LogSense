import logging
import os
import time
from pathlib import Path

LOG_DIR = Path("/tmp/cascade_logs")
LOG_FILE_LIFESPAN_SECONDS = 2 * 24 * 60 * 60  # 2 days

def cleanup_old_logs():
    """Deletes log files older than the specified lifespan."""
    if not LOG_DIR.is_dir():
        return

    cutoff = time.time() - LOG_FILE_LIFESPAN_SECONDS
    for log_file in LOG_DIR.glob("cascade_*.log"):
        try:
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                print(f"[Cascade Logger] Deleted old log file: {log_file.name}")
        except OSError as e:
            print(f"[Cascade Logger] Error deleting log {log_file.name}: {e}")

def get_cascade_logger(name: str) -> logging.Logger:
    """Initializes and returns a logger for Cascade's troubleshooting.

    - Logs to a dedicated, timestamped file in /tmp/cascade_logs.
    - Cleans up logs older than 2 days on initialization.
    """
    LOG_DIR.mkdir(exist_ok=True)
    cleanup_old_logs()

    logger = logging.getLogger(f"cascade.{name}")
    if logger.hasHandlers():
        return logger  # Avoid adding duplicate handlers

    logger.setLevel(logging.INFO)
    log_filename = LOG_DIR / f"cascade_{time.strftime('%Y%m%d')}.log"

    # Create a file handler
    handler = logging.FileHandler(log_filename)
    handler.setLevel(logging.INFO)

    # Create a logging format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)

    return logger
