"""
Database module for Auto Paper Digest.

Provides SQLite-based paper tracking with status management.
"""

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from .config import DB_PATH, Status
from .utils import get_logger, now_iso

logger = get_logger()


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Paper:
    """Represents a paper record in the database."""
    paper_id: str
    week_id: str
    title: Optional[str] = None
    hf_url: Optional[str] = None
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None
    pdf_sha256: Optional[str] = None
    notebooklm_note_name: Optional[str] = None
    video_path: Optional[str] = None
    status: str = Status.NEW
    retry_count: int = 0
    last_error: Optional[str] = None
    updated_at: Optional[str] = None


# =============================================================================
# Database Management
# =============================================================================

@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """
    Context manager for database connections.
    
    Yields:
        SQLite connection with row factory enabled
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Create papers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                paper_id TEXT PRIMARY KEY,
                week_id TEXT NOT NULL,
                title TEXT,
                hf_url TEXT,
                pdf_url TEXT,
                pdf_path TEXT,
                pdf_sha256 TEXT,
                notebooklm_note_name TEXT,
                video_path TEXT,
                status TEXT DEFAULT 'NEW',
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                updated_at TEXT
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_week 
            ON papers(week_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_status 
            ON papers(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_week_status 
            ON papers(week_id, status)
        """)
        
        logger.debug("Database initialized")


# =============================================================================
# CRUD Operations
# =============================================================================

def get_paper(paper_id: str) -> Optional[Paper]:
    """
    Get a paper by its ID.
    
    Args:
        paper_id: The paper ID (arXiv ID)
        
    Returns:
        Paper object or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
        row = cursor.fetchone()
        
        if row:
            return Paper(**dict(row))
        return None


def upsert_paper(
    paper_id: str,
    week_id: str,
    title: Optional[str] = None,
    hf_url: Optional[str] = None,
    pdf_url: Optional[str] = None,
    pdf_path: Optional[str] = None,
    pdf_sha256: Optional[str] = None,
    notebooklm_note_name: Optional[str] = None,
    video_path: Optional[str] = None,
    status: Optional[str] = None,
    last_error: Optional[str] = None,
) -> Paper:
    """
    Insert or update a paper record.
    
    Only updates fields that are explicitly provided (not None).
    
    Args:
        paper_id: The paper ID (arXiv ID)
        week_id: Week identifier
        Other args: Optional fields to set/update
        
    Returns:
        The updated Paper object
    """
    existing = get_paper(paper_id)
    now = now_iso()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if existing:
            # Build UPDATE query dynamically for non-None fields
            updates = []
            values = []
            
            if title is not None:
                updates.append("title = ?")
                values.append(title)
            if hf_url is not None:
                updates.append("hf_url = ?")
                values.append(hf_url)
            if pdf_url is not None:
                updates.append("pdf_url = ?")
                values.append(pdf_url)
            if pdf_path is not None:
                updates.append("pdf_path = ?")
                values.append(pdf_path)
            if pdf_sha256 is not None:
                updates.append("pdf_sha256 = ?")
                values.append(pdf_sha256)
            if notebooklm_note_name is not None:
                updates.append("notebooklm_note_name = ?")
                values.append(notebooklm_note_name)
            if video_path is not None:
                updates.append("video_path = ?")
                values.append(video_path)
            if status is not None:
                updates.append("status = ?")
                values.append(status)
            if last_error is not None:
                updates.append("last_error = ?")
                values.append(last_error)
            
            updates.append("updated_at = ?")
            values.append(now)
            values.append(paper_id)
            
            if updates:
                query = f"UPDATE papers SET {', '.join(updates)} WHERE paper_id = ?"
                cursor.execute(query, values)
                
            logger.debug(f"Updated paper: {paper_id}")
        else:
            # INSERT new record
            cursor.execute("""
                INSERT INTO papers (
                    paper_id, week_id, title, hf_url, pdf_url, pdf_path,
                    pdf_sha256, notebooklm_note_name, video_path, status,
                    retry_count, last_error, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper_id, week_id, title, hf_url, pdf_url, pdf_path,
                pdf_sha256, notebooklm_note_name, video_path,
                status or Status.NEW, 0, last_error, now
            ))
            logger.debug(f"Inserted paper: {paper_id}")
    
    return get_paper(paper_id)  # type: ignore


def update_status(
    paper_id: str,
    status: str,
    error: Optional[str] = None,
    increment_retry: bool = False
) -> Optional[Paper]:
    """
    Update the status of a paper.
    
    Args:
        paper_id: The paper ID
        status: New status value
        error: Optional error message
        increment_retry: Whether to increment retry_count
        
    Returns:
        Updated Paper object or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        now = now_iso()
        
        if increment_retry:
            cursor.execute("""
                UPDATE papers 
                SET status = ?, last_error = ?, retry_count = retry_count + 1, updated_at = ?
                WHERE paper_id = ?
            """, (status, error, now, paper_id))
        else:
            cursor.execute("""
                UPDATE papers 
                SET status = ?, last_error = ?, updated_at = ?
                WHERE paper_id = ?
            """, (status, error, now, paper_id))
        
        if cursor.rowcount == 0:
            logger.warning(f"Paper not found for status update: {paper_id}")
            return None
            
        logger.debug(f"Updated status for {paper_id}: {status}")
    
    return get_paper(paper_id)


def list_papers(
    week_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None
) -> list[Paper]:
    """
    List papers with optional filtering.
    
    Args:
        week_id: Filter by week
        status: Filter by status
        limit: Maximum number of results
        
    Returns:
        List of Paper objects
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM papers WHERE 1=1"
        params: list = []
        
        if week_id:
            query += " AND week_id = ?"
            params.append(week_id)
        if status:
            query += " AND status = ?"
            params.append(status)
            
        query += " ORDER BY updated_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [Paper(**dict(row)) for row in rows]


def count_papers(week_id: Optional[str] = None, status: Optional[str] = None) -> int:
    """
    Count papers with optional filtering.
    
    Args:
        week_id: Filter by week
        status: Filter by status
        
    Returns:
        Count of matching papers
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) FROM papers WHERE 1=1"
        params: list = []
        
        if week_id:
            query += " AND week_id = ?"
            params.append(week_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        
        cursor.execute(query, params)
        return cursor.fetchone()[0]


def get_papers_for_processing(
    week_id: str,
    target_status: str,
    max_retries: int = 3,
    limit: Optional[int] = None
) -> list[Paper]:
    """
    Get papers that need processing to reach a target status.
    
    Args:
        week_id: Week to process
        target_status: The status we want papers to reach
        max_retries: Maximum retry attempts before skipping
        limit: Maximum papers to return
        
    Returns:
        List of papers that need processing
    """
    # Define status precedence
    status_order = [Status.NEW, Status.PDF_OK, Status.NBLM_OK, Status.VIDEO_OK]
    
    if target_status not in status_order:
        return []
    
    target_idx = status_order.index(target_status)
    needed_statuses = status_order[:target_idx]
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        placeholders = ",".join("?" * len(needed_statuses))
        query = f"""
            SELECT * FROM papers 
            WHERE week_id = ? 
            AND status IN ({placeholders})
            AND retry_count < ?
            ORDER BY paper_id
        """
        
        if limit:
            query += " LIMIT ?"
            params = [week_id] + needed_statuses + [max_retries, limit]
        else:
            params = [week_id] + needed_statuses + [max_retries]
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [Paper(**dict(row)) for row in rows]
