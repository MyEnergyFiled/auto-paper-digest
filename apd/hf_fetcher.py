"""
Hugging Face papers fetcher module.

Scrapes weekly papers from Hugging Face and stores them in the database.
"""

import re
from datetime import datetime, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .config import (
    ARXIV_PDF_URL,
    HF_PAPERS_DATE_URL,
    HF_PAPERS_URL,
    HF_PAPERS_WEEK_URL,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from .db import get_paper, upsert_paper
from .utils import get_logger, parse_week_id

logger = get_logger()


def get_dates_for_week(week_id: str) -> list[str]:
    """
    Get all dates (YYYY-MM-DD) for a given week.
    
    Args:
        week_id: Week identifier (e.g., "2026-01")
        
    Returns:
        List of date strings for that week (Monday to Sunday)
    """
    year, week = parse_week_id(week_id)
    
    # Get the Monday of the given ISO week
    # ISO week 1 is the week containing January 4th
    jan4 = datetime(year, 1, 4)
    start_of_week1 = jan4 - timedelta(days=jan4.weekday())
    monday = start_of_week1 + timedelta(weeks=week - 1)
    
    # Generate all 7 days of the week
    dates = []
    for i in range(7):
        day = monday + timedelta(days=i)
        dates.append(day.strftime("%Y-%m-%d"))
    
    return dates


def week_id_to_iso_week(week_id: str) -> str:
    """
    Convert week_id format (e.g., "2026-01") to ISO week format (e.g., "2026-W01").
    
    Args:
        week_id: Week identifier in format "YYYY-WW"
        
    Returns:
        ISO week string in format "YYYY-WXX"
    """
    year, week = parse_week_id(week_id)
    return f"{year}-W{week:02d}"


def fetch_papers_for_week_url(week_id: str, max_papers: Optional[int] = None) -> list[dict]:
    """
    Fetch papers from HF using the week URL format.
    
    Uses https://huggingface.co/papers/week/YYYY-WXX
    
    Args:
        week_id: Week identifier (e.g., "2026-01")
        max_papers: Maximum papers to fetch (None for all)
        
    Returns:
        List of paper dicts with keys: paper_id, title, hf_url, pdf_url
    """
    iso_week = week_id_to_iso_week(week_id)
    url = HF_PAPERS_WEEK_URL.format(week=iso_week)
    logger.info(f"Fetching papers from week URL: {url}")
    
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch papers for week {iso_week}: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "lxml")
    papers = []
    
    # Find paper links - they're in article elements or links matching the pattern
    # HF paper URLs are like: /papers/2601.03252
    paper_pattern = re.compile(r"^/papers/(\d{4}\.\d{4,5})$")
    
    # Look for article elements with paper links
    for link in soup.find_all("a", href=paper_pattern):
        href = link.get("href", "")
        match = paper_pattern.match(href)
        if not match:
            continue
            
        paper_id = match.group(1)
        
        # Avoid duplicates
        if any(p["paper_id"] == paper_id for p in papers):
            continue
        
        # Try to get the title from the link text or parent
        title = link.get_text(strip=True)
        if not title or len(title) < 5:
            # Try to find title in parent elements
            parent = link.find_parent(["article", "div"])
            if parent:
                h3 = parent.find(["h3", "h2", "h1"])
                if h3:
                    title = h3.get_text(strip=True)
        
        hf_url = f"{HF_PAPERS_URL}/{paper_id}"
        pdf_url = ARXIV_PDF_URL.format(paper_id=paper_id)
        
        papers.append({
            "paper_id": paper_id,
            "title": title or f"Paper {paper_id}",
            "hf_url": hf_url,
            "pdf_url": pdf_url,
        })
        
        if max_papers and len(papers) >= max_papers:
            break
    
    logger.info(f"Found {len(papers)} papers for week {iso_week}")
    return papers


def fetch_papers_for_date(date: str, max_papers: Optional[int] = None) -> list[dict]:
    """
    Fetch papers from HF for a specific date.
    
    Args:
        date: Date string (YYYY-MM-DD)
        max_papers: Maximum papers to fetch (None for all)
        
    Returns:
        List of paper dicts with keys: paper_id, title, hf_url, pdf_url
    """
    url = HF_PAPERS_DATE_URL.format(date=date)
    logger.debug(f"Fetching papers from: {url}")
    
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch papers for {date}: {e}")
        return []
    
    soup = BeautifulSoup(response.text, "lxml")
    papers = []
    
    # Find paper links - they're in article elements or links matching the pattern
    # HF paper URLs are like: /papers/2601.03252
    paper_pattern = re.compile(r"^/papers/(\d{4}\.\d{4,5})$")
    
    # Look for article elements with paper links
    for link in soup.find_all("a", href=paper_pattern):
        href = link.get("href", "")
        match = paper_pattern.match(href)
        if not match:
            continue
            
        paper_id = match.group(1)
        
        # Avoid duplicates
        if any(p["paper_id"] == paper_id for p in papers):
            continue
        
        # Try to get the title from the link text or parent
        title = link.get_text(strip=True)
        if not title or len(title) < 5:
            # Try to find title in parent elements
            parent = link.find_parent(["article", "div"])
            if parent:
                h3 = parent.find(["h3", "h2", "h1"])
                if h3:
                    title = h3.get_text(strip=True)
        
        hf_url = f"{HF_PAPERS_URL}/{paper_id}"
        pdf_url = ARXIV_PDF_URL.format(paper_id=paper_id)
        
        papers.append({
            "paper_id": paper_id,
            "title": title or f"Paper {paper_id}",
            "hf_url": hf_url,
            "pdf_url": pdf_url,
        })
        
        if max_papers and len(papers) >= max_papers:
            break
    
    logger.info(f"Found {len(papers)} papers for date {date}")
    return papers


def fetch_weekly_papers(
    week_id: str,
    max_papers: Optional[int] = None
) -> list[dict]:
    """
    Fetch all papers for a given week and store in database.
    
    First tries the week URL format (https://huggingface.co/papers/week/YYYY-WXX),
    then falls back to date-by-date fetching if that returns empty.
    
    Args:
        week_id: Week identifier (e.g., "2026-01")
        max_papers: Maximum total papers to fetch
        
    Returns:
        List of paper dicts that were fetched
    """
    logger.info(f"Fetching papers for week {week_id}")
    
    all_papers = []
    seen_ids = set()
    
    # First, try the week URL format (more efficient)
    papers_from_week = fetch_papers_for_week_url(week_id, max_papers=max_papers)
    
    if papers_from_week:
        # Process papers from week URL
        for paper in papers_from_week:
            paper_id = paper["paper_id"]
            
            if paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)
            
            # Check if paper already exists in DB
            existing = get_paper(paper_id)
            if existing:
                logger.debug(f"Paper {paper_id} already in database")
                all_papers.append(paper)
                continue
            
            # Insert new paper
            upsert_paper(
                paper_id=paper_id,
                week_id=week_id,
                title=paper["title"],
                hf_url=paper["hf_url"],
                pdf_url=paper["pdf_url"],
            )
            logger.info(f"Added paper: {paper_id} - {paper['title'][:50]}...")
            all_papers.append(paper)
            
            if max_papers and len(all_papers) >= max_papers:
                break
    else:
        # Fallback: fetch by date if week URL returned no results
        logger.info("Week URL returned no results, falling back to date-by-date fetching")
        dates = get_dates_for_week(week_id)
        
        for date in dates:
            # Check if we've hit the limit
            remaining = None
            if max_papers:
                remaining = max_papers - len(all_papers)
                if remaining <= 0:
                    break
            
            papers = fetch_papers_for_date(date, max_papers=remaining)
            
            for paper in papers:
                paper_id = paper["paper_id"]
                
                # Skip if we've already seen this paper
                if paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)
                
                # Check if paper already exists in DB
                existing = get_paper(paper_id)
                if existing:
                    logger.debug(f"Paper {paper_id} already in database")
                    all_papers.append(paper)
                    continue
                
                # Insert new paper
                upsert_paper(
                    paper_id=paper_id,
                    week_id=week_id,
                    title=paper["title"],
                    hf_url=paper["hf_url"],
                    pdf_url=paper["pdf_url"],
                )
                logger.info(f"Added paper: {paper_id} - {paper['title'][:50]}...")
                all_papers.append(paper)
                
                if max_papers and len(all_papers) >= max_papers:
                    break
    
    logger.info(f"Total papers fetched for week {week_id}: {len(all_papers)}")
    return all_papers


def get_paper_details(paper_id: str) -> Optional[dict]:
    """
    Fetch detailed information about a specific paper from HF.
    
    Args:
        paper_id: The arXiv paper ID
        
    Returns:
        Paper details dict or None if not found
    """
    url = f"{HF_PAPERS_URL}/{paper_id}"
    headers = {"User-Agent": USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch paper details for {paper_id}: {e}")
        return None
    
    soup = BeautifulSoup(response.text, "lxml")
    
    # Extract title from h1
    title_elem = soup.find("h1")
    title = title_elem.get_text(strip=True) if title_elem else f"Paper {paper_id}"
    
    # Extract abstract
    abstract = ""
    abstract_section = soup.find("h2", string=re.compile(r"Abstract", re.I))
    if abstract_section:
        next_elem = abstract_section.find_next_sibling()
        if next_elem:
            abstract = next_elem.get_text(strip=True)
    
    return {
        "paper_id": paper_id,
        "title": title,
        "abstract": abstract,
        "hf_url": url,
        "pdf_url": ARXIV_PDF_URL.format(paper_id=paper_id),
    }
