"""
Configuration module for Auto Paper Digest.

Centralizes all paths, URLs, and default settings.
"""

from pathlib import Path

# =============================================================================
# Directory Paths
# =============================================================================

# Base directories
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"

# Data subdirectories
PDF_DIR = DATA_DIR / "pdfs"
VIDEO_DIR = DATA_DIR / "videos"
DIGEST_DIR = DATA_DIR / "digests"
PROFILE_DIR = DATA_DIR / "profiles"

# Database
DB_PATH = DATA_DIR / "apd.db"

# Default browser profile name
DEFAULT_PROFILE = "default"

# =============================================================================
# URLs
# =============================================================================

# Hugging Face papers page (date-based and week-based)
HF_PAPERS_URL = "https://huggingface.co/papers"
HF_PAPERS_DATE_URL = "https://huggingface.co/papers?date={date}"
HF_PAPERS_WEEK_URL = "https://huggingface.co/papers/week/{week}"  # e.g., /week/2026-W01

# arXiv PDF download template
ARXIV_PDF_URL = "https://export.arxiv.org/pdf/{paper_id}.pdf"

# NotebookLM
NOTEBOOKLM_URL = "https://notebooklm.google.com"

# =============================================================================
# Defaults
# =============================================================================

# Maximum papers to fetch per week
DEFAULT_MAX_PAPERS = 50

# Maximum retry attempts for failed operations
MAX_RETRIES = 3

# Request timeout in seconds
REQUEST_TIMEOUT = 60

# Download chunk size
DOWNLOAD_CHUNK_SIZE = 8192

# Delay between downloads (seconds) to respect arXiv rate limits
DOWNLOAD_DELAY_SECONDS = 3

# Playwright timeouts (milliseconds)
PLAYWRIGHT_TIMEOUT = 60000  # 60 seconds for general operations
PLAYWRIGHT_NAVIGATION_TIMEOUT = 120000  # 120 seconds for page navigation
PLAYWRIGHT_VIDEO_TIMEOUT = 600000  # 10 minutes for video generation

# User agent for requests
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# =============================================================================
# Status Constants
# =============================================================================

class Status:
    """Paper processing status values."""
    NEW = "NEW"
    PDF_OK = "PDF_OK"
    NBLM_OK = "NBLM_OK"  # Notebook created, PDF uploaded
    VIDEO_OK = "VIDEO_OK"
    ERROR = "ERROR"


def ensure_directories() -> None:
    """Create all required directories if they don't exist."""
    for directory in [PDF_DIR, VIDEO_DIR, DIGEST_DIR, PROFILE_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
