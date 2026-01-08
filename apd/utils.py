"""
Utility functions for Auto Paper Digest.

Provides logging setup, file hashing, and common helpers.
"""

import hashlib
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    """
    Configure structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to write logs to file
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("apd")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Formatter with timestamp and structured output
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger() -> logging.Logger:
    """Get the application logger."""
    logger = logging.getLogger("apd")
    if not logger.handlers:
        setup_logging()
    return logger


def sha256_file(file_path: Path) -> str:
    """
    Compute SHA256 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Hexadecimal SHA256 hash string
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def ensure_dir(path: Path) -> Path:
    """
    Create directory if it doesn't exist.
    
    Args:
        path: Directory path to create
        
    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat(timespec="seconds")


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """
    Sanitize a string for use as a filename.
    
    Args:
        name: Original name
        max_length: Maximum length of the result
        
    Returns:
        Sanitized filename-safe string
    """
    # Replace problematic characters
    invalid_chars = '<>:"/\\|?*\n\r\t'
    for char in invalid_chars:
        name = name.replace(char, "_")
    
    # Collapse multiple underscores
    while "__" in name:
        name = name.replace("__", "_")
    
    # Strip leading/trailing whitespace and underscores
    name = name.strip().strip("_")
    
    # Truncate
    if len(name) > max_length:
        name = name[:max_length].rstrip("_")
    
    return name or "untitled"


def format_week_id(year: int, week: int) -> str:
    """
    Format year and week into week_id string.
    
    Args:
        year: Year (e.g., 2026)
        week: Week number (1-53)
        
    Returns:
        Week ID string (e.g., "2026-01")
    """
    return f"{year}-{week:02d}"


def parse_week_id(week_id: str) -> tuple[int, int]:
    """
    Parse week_id string into year and week.
    
    Args:
        week_id: Week ID string (e.g., "2026-01")
        
    Returns:
        Tuple of (year, week)
    """
    parts = week_id.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid week_id format: {week_id}")
    return int(parts[0]), int(parts[1])


def get_current_week_id() -> str:
    """Get the week_id for the current week."""
    now = datetime.now()
    year, week, _ = now.isocalendar()
    return format_week_id(year, week)
