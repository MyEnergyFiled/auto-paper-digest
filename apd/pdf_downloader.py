"""
PDF downloader module for Auto Paper Digest.

Downloads arXiv PDFs with idempotency checks via SHA256 hashing.
"""

from pathlib import Path
import time
from typing import Optional

import requests

from .config import (
    ARXIV_PDF_URL,
    DOWNLOAD_CHUNK_SIZE,
    DOWNLOAD_DELAY_SECONDS,
    PDF_DIR,
    REQUEST_TIMEOUT,
    Status,
    USER_AGENT,
)
from .db import get_paper, update_status, upsert_paper
from .utils import ensure_dir, get_logger, sha256_file

logger = get_logger()


def download_pdf(
    paper_id: str,
    week_id: str,
    force: bool = False
) -> Optional[Path]:
    """
    Download a PDF from arXiv.
    
    Implements idempotency: if PDF exists and SHA256 matches, skip unless force.
    
    Args:
        paper_id: The arXiv paper ID
        week_id: Week identifier for directory organization
        force: Force re-download even if file exists
        
    Returns:
        Path to the downloaded PDF, or None on failure
    """
    # Check existing paper record
    paper = get_paper(paper_id)
    
    # Determine PDF path
    pdf_dir = ensure_dir(PDF_DIR / week_id)
    pdf_path = pdf_dir / f"{paper_id}.pdf"
    
    # Check for existing file
    if pdf_path.exists() and not force:
        existing_sha = sha256_file(pdf_path)
        
        # If we have a record with matching SHA, skip
        if paper and paper.pdf_sha256 == existing_sha:
            logger.info(f"PDF already exists with matching hash: {paper_id}")
            return pdf_path
        
        # File exists but hash doesn't match - re-download
        logger.warning(f"PDF hash mismatch for {paper_id}, re-downloading")
    
    # Build PDF URL
    pdf_url = ARXIV_PDF_URL.format(paper_id=paper_id)
    logger.info(f"Downloading PDF: {pdf_url}")
    
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(
            pdf_url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            stream=True
        )
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
            logger.warning(f"Unexpected content type for {paper_id}: {content_type}")
        
        # Download in chunks
        with open(pdf_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        
        # Compute hash
        pdf_sha256 = sha256_file(pdf_path)
        
        # Update database
        upsert_paper(
            paper_id=paper_id,
            week_id=week_id,
            pdf_url=pdf_url,
            pdf_path=str(pdf_path),
            pdf_sha256=pdf_sha256,
            status=Status.PDF_OK,
        )
        
        logger.info(f"Downloaded PDF: {pdf_path} ({pdf_path.stat().st_size / 1024:.1f} KB)")
        return pdf_path
        
    except requests.RequestException as e:
        error_msg = f"Failed to download PDF for {paper_id}: {e}"
        logger.error(error_msg)
        
        # Update status to ERROR
        if paper:
            update_status(paper_id, Status.ERROR, error=error_msg, increment_retry=True)
        
        return None


def download_pdfs_for_week(
    week_id: str,
    force: bool = False,
    max_papers: Optional[int] = None
) -> tuple[int, int]:
    """
    Download all PDFs for papers in a given week.
    
    Args:
        week_id: Week identifier
        force: Force re-download
        max_papers: Maximum papers to download
        
    Returns:
        Tuple of (success_count, failure_count)
    """
    from .db import list_papers
    
    papers = list_papers(week_id=week_id)
    
    if max_papers:
        papers = papers[:max_papers]
    
    success = 0
    failure = 0
    
    for idx, paper in enumerate(papers):
        # Skip if already downloaded (unless force)
        if paper.status in [Status.PDF_OK, Status.NBLM_OK, Status.VIDEO_OK] and not force:
            logger.debug(f"Skipping {paper.paper_id} - already has status {paper.status}")
            success += 1
            continue
        
        # Add delay between downloads to respect arXiv rate limits (skip for first paper)
        if idx > 0:
            logger.debug(f"Waiting {DOWNLOAD_DELAY_SECONDS} seconds before next download...")
            time.sleep(DOWNLOAD_DELAY_SECONDS)
        
        result = download_pdf(paper.paper_id, week_id, force=force)
        if result:
            success += 1
        else:
            failure += 1
    
    logger.info(f"Download complete for week {week_id}: {success} success, {failure} failed")
    return success, failure


def download_single_paper(paper_id: str, force: bool = False) -> Optional[Path]:
    """
    Download PDF for a single paper by ID.
    
    Args:
        paper_id: The paper ID
        force: Force re-download
        
    Returns:
        Path to PDF or None on failure
    """
    paper = get_paper(paper_id)
    if not paper:
        logger.error(f"Paper not found in database: {paper_id}")
        return None
    
    return download_pdf(paper_id, paper.week_id, force=force)
