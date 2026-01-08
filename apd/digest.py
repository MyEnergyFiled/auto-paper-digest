"""
Digest generator module for Auto Paper Digest.

Generates weekly digest files in Markdown and JSON formats.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import DIGEST_DIR, Status
from .db import count_papers, list_papers
from .utils import ensure_dir, get_logger, parse_week_id

logger = get_logger()


def generate_digest(week_id: str, include_all: bool = False) -> tuple[Path, Path]:
    """
    Generate weekly digest files.
    
    Args:
        week_id: Week identifier (e.g., "2026-01")
        include_all: Include papers without VIDEO_OK status
        
    Returns:
        Tuple of (markdown_path, json_path)
    """
    logger.info(f"Generating digest for week {week_id}")
    
    # Get papers for this week
    if include_all:
        papers = list_papers(week_id=week_id)
    else:
        papers = list_papers(week_id=week_id, status=Status.VIDEO_OK)
    
    if not papers:
        logger.warning(f"No papers found for week {week_id}")
    
    # Prepare output directory
    digest_dir = ensure_dir(DIGEST_DIR)
    md_path = digest_dir / f"{week_id}.md"
    json_path = digest_dir / f"{week_id}.json"
    
    # Get week info
    year, week = parse_week_id(week_id)
    
    # Build paper data for JSON
    papers_data = []
    for paper in papers:
        papers_data.append({
            "paper_id": paper.paper_id,
            "title": paper.title,
            "hf_url": paper.hf_url,
            "pdf_url": paper.pdf_url,
            "pdf_path": paper.pdf_path,
            "video_path": paper.video_path,
            "status": paper.status,
        })
    
    # Generate JSON
    digest_json = {
        "week_id": week_id,
        "year": year,
        "week": week,
        "generated_at": datetime.now().isoformat(),
        "total_papers": len(papers),
        "papers": papers_data,
        "stats": {
            "total": count_papers(week_id=week_id),
            "video_ok": count_papers(week_id=week_id, status=Status.VIDEO_OK),
            "pdf_ok": count_papers(week_id=week_id, status=Status.PDF_OK),
            "new": count_papers(week_id=week_id, status=Status.NEW),
            "error": count_papers(week_id=week_id, status=Status.ERROR),
        }
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(digest_json, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Generated JSON digest: {json_path}")
    
    # Generate Markdown
    md_content = generate_markdown(week_id, year, week, papers, digest_json["stats"])
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    logger.info(f"Generated Markdown digest: {md_path}")
    
    return md_path, json_path


def generate_markdown(
    week_id: str,
    year: int,
    week: int,
    papers: list,
    stats: dict
) -> str:
    """
    Generate Markdown content for the digest.
    
    Args:
        week_id: Week identifier
        year: Year number
        week: Week number
        papers: List of Paper objects
        stats: Statistics dict
        
    Returns:
        Markdown content string
    """
    lines = [
        f"# Weekly AI Paper Digest - {week_id}",
        "",
        f"**Year:** {year} | **Week:** {week}",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        "",
        f"- Total papers: {stats['total']}",
        f"- Videos generated: {stats['video_ok']}",
        f"- PDFs downloaded: {stats['pdf_ok']}",
        f"- Pending: {stats['new']}",
        f"- Errors: {stats['error']}",
        "",
        "---",
        "",
        "## Papers",
        "",
    ]
    
    if not papers:
        lines.append("*No papers with completed videos for this week.*")
    else:
        for i, paper in enumerate(papers, 1):
            lines.append(f"### {i}. {paper.title or 'Untitled'}")
            lines.append("")
            lines.append(f"**Paper ID:** `{paper.paper_id}`")
            lines.append("")
            
            # Links
            links = []
            if paper.hf_url:
                links.append(f"[HuggingFace]({paper.hf_url})")
            if paper.pdf_url:
                links.append(f"[arXiv PDF]({paper.pdf_url})")
            if links:
                lines.append(f"**Links:** {' | '.join(links)}")
                lines.append("")
            
            # Local files
            files = []
            if paper.pdf_path:
                files.append(f"PDF: `{paper.pdf_path}`")
            if paper.video_path:
                files.append(f"Video: `{paper.video_path}`")
            if files:
                lines.append(f"**Local files:**")
                for f in files:
                    lines.append(f"- {f}")
                lines.append("")
            
            lines.append(f"**Status:** {paper.status}")
            lines.append("")
            lines.append("---")
            lines.append("")
    
    # Footer
    lines.extend([
        "",
        "## About",
        "",
        "This digest was automatically generated by [Auto Paper Digest](https://github.com/brianxiadong/auto-paper-digest).",
        "Videos are created using NotebookLM's Audio Overview feature.",
    ])
    
    return "\n".join(lines)


def list_available_weeks() -> list[str]:
    """
    List all weeks that have papers in the database.
    
    Returns:
        List of week_id strings, sorted descending
    """
    from .db import get_connection
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT week_id FROM papers ORDER BY week_id DESC")
        rows = cursor.fetchall()
        return [row[0] for row in rows]


def print_digest_summary(week_id: str) -> None:
    """Print a summary of the digest to console."""
    stats = {
        "total": count_papers(week_id=week_id),
        "video_ok": count_papers(week_id=week_id, status=Status.VIDEO_OK),
        "pdf_ok": count_papers(week_id=week_id, status=Status.PDF_OK),
        "new": count_papers(week_id=week_id, status=Status.NEW),
        "error": count_papers(week_id=week_id, status=Status.ERROR),
    }
    
    print(f"\n📊 Week {week_id} Summary:")
    print(f"   Total papers:     {stats['total']}")
    print(f"   ✅ Videos ready:   {stats['video_ok']}")
    print(f"   📄 PDFs ready:     {stats['pdf_ok']}")
    print(f"   🆕 Pending:        {stats['new']}")
    print(f"   ❌ Errors:         {stats['error']}")
