import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from loguru import logger


def setup_logging(log_level: str):
    """Setup logging configuration."""
    from src.config.settings import config

    logger.remove()
    # Add console logging
    logger.add(
        sys.stdout,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )

    # Add file logging when DEBUG level is specified
    if log_level == "DEBUG":
        # Create the session logs directory if it doesn't exist
        os.makedirs(config.logging.logs_dir, exist_ok=True)

        # Create a unique log file name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"debug_session_{timestamp}.log"
        log_file = os.path.join(config.logging.logs_dir, log_filename)

        # Add file logger without rotation since we're creating new files per session
        logger.add(
            log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
        )
        logger.debug(f"Debug logging enabled. Logs will be stored in {log_file}")

        # Clean up old log files if there are too many
        cleanup_old_logs(config.logging.logs_dir, max_files=10)


def cleanup_old_logs(log_dir: str, max_files: int = 50):
    """Clean up old log files if there are too many in the directory."""
    try:
        # List all debug log files
        log_files = [f for f in os.listdir(log_dir) if f.startswith("debug_session_") and f.endswith(".log")]

        # If we have more files than the maximum allowed
        if len(log_files) > max_files:
            # Sort files by modification time (oldest first)
            log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)))

            # Remove the oldest files
            for f in log_files[:-max_files]:
                try:
                    os.remove(os.path.join(log_dir, f))
                    logger.debug(f"Cleaned up old log file: {f}")
                except OSError as e:
                    logger.warning(f"Failed to remove old log file {f}: {e}")
    except Exception as e:
        logger.warning(f"Failed to clean up old log files: {e}")
