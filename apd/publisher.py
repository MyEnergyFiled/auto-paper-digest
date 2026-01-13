"""
Publisher module for Auto Paper Digest.

Handles uploading videos to Hugging Face Datasets and generating metadata.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from huggingface_hub import HfApi, hf_hub_download, upload_file

from .config import DIGEST_DIR, SLIDES_DIR, VIDEO_DIR, Status
from .db import list_papers
from .utils import get_logger

# Load environment variables
load_dotenv()

logger = get_logger()

# HuggingFace configuration from environment
HF_TOKEN = os.getenv("HF_TOKEN")
HF_USERNAME = os.getenv("HF_USERNAME", "")
HF_DATASET_NAME = os.getenv("HF_DATASET_NAME", "paper-digest-videos")


def get_hf_dataset_id() -> str:
    """Get the full HuggingFace dataset ID."""
    if not HF_USERNAME:
        raise ValueError("HF_USERNAME not set in .env file")
    return f"{HF_USERNAME}/{HF_DATASET_NAME}"


def get_video_url(dataset_id: str, video_path: str) -> str:
    """
    Get the streaming URL for a video in the dataset.
    
    Uses the resolve URL which supports direct streaming/download.
    
    Args:
        dataset_id: HuggingFace dataset ID (username/dataset)
        video_path: Path to the video within the dataset
        
    Returns:
        Direct streaming URL to the video file
    """
    # Use resolve URL for direct video streaming
    return f"https://huggingface.co/datasets/{dataset_id}/resolve/main/{video_path}"


def upload_video_to_hf(
    local_path: Path,
    remote_path: str,
    dataset_id: Optional[str] = None,
) -> str:
    """
    Upload a video file to HuggingFace Dataset.
    
    Args:
        local_path: Local path to the video file
        remote_path: Path within the dataset (e.g., "2026-01/video.mp4")
        dataset_id: HF dataset ID (default from env)
        
    Returns:
        URL to the uploaded video
    """
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN not set in .env file")
    
    dataset_id = dataset_id or get_hf_dataset_id()
    
    logger.info(f"Uploading {local_path.name} to {dataset_id}/{remote_path}")
    
    api = HfApi(token=HF_TOKEN)
    
    # Ensure the dataset exists (create if not)
    try:
        api.create_repo(
            repo_id=dataset_id,
            repo_type="dataset",
            exist_ok=True,
            private=False,
        )
    except Exception as e:
        logger.debug(f"Dataset creation check: {e}")
    
    # Upload the file
    upload_file(
        path_or_fileobj=str(local_path),
        path_in_repo=remote_path,
        repo_id=dataset_id,
        repo_type="dataset",
        token=HF_TOKEN,
    )
    
    video_url = get_video_url(dataset_id, remote_path)
    logger.info(f"Uploaded: {video_url}")
    
    return video_url


def load_metadata(dataset_id: Optional[str] = None) -> dict:
    """
    Load existing metadata from HuggingFace Dataset.
    
    Returns:
        Metadata dict with structure: {"weeks": {"2026-01": [...]}}
    """
    dataset_id = dataset_id or get_hf_dataset_id()
    
    try:
        local_path = hf_hub_download(
            repo_id=dataset_id,
            filename="metadata.json",
            repo_type="dataset",
            token=HF_TOKEN,
        )
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.debug(f"No existing metadata found: {e}")
        return {"weeks": {}, "last_updated": None}


def save_metadata(metadata: dict, dataset_id: Optional[str] = None) -> None:
    """
    Save metadata to HuggingFace Dataset.
    
    Args:
        metadata: Metadata dict to save
        dataset_id: HF dataset ID
    """
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN not set in .env file")
    
    dataset_id = dataset_id or get_hf_dataset_id()
    
    # Update timestamp
    metadata["last_updated"] = datetime.now().isoformat()
    
    # Save to temp file then upload
    temp_path = DIGEST_DIR / "metadata_temp.json"
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    upload_file(
        path_or_fileobj=str(temp_path),
        path_in_repo="metadata.json",
        repo_id=dataset_id,
        repo_type="dataset",
        token=HF_TOKEN,
    )
    
    # Clean up temp file
    temp_path.unlink(missing_ok=True)
    
    logger.info(f"Metadata updated on {dataset_id}")


def publish_week(
    week_id: str,
    force: bool = False,
) -> tuple[int, int]:
    """
    Publish videos for a week to HuggingFace Dataset.
    
    Args:
        week_id: Week identifier (e.g., "2026-01")
        force: Force re-upload even if already published
        
    Returns:
        Tuple of (success_count, failure_count)
    """
    logger.info(f"Publishing videos for week {week_id}")
    
    # Get papers with videos
    papers = list_papers(week_id=week_id, status=Status.VIDEO_OK)
    
    if not papers:
        logger.warning(f"No papers with videos found for week {week_id}")
        return 0, 0
    
    dataset_id = get_hf_dataset_id()
    
    # Load existing metadata
    metadata = load_metadata(dataset_id)
    
    if week_id not in metadata["weeks"]:
        metadata["weeks"][week_id] = []
    
    existing_ids = {p["paper_id"] for p in metadata["weeks"][week_id]}
    
    success = 0
    failure = 0
    
    for paper in papers:
        # Skip if already published (unless force)
        if paper.paper_id in existing_ids and not force:
            logger.info(f"Paper {paper.paper_id} already published, skipping")
            success += 1
            continue
        
        # Check if video file exists
        if not paper.video_path:
            logger.warning(f"No video path for paper {paper.paper_id}")
            failure += 1
            continue
        
        video_path = Path(paper.video_path)
        if not video_path.exists():
            logger.warning(f"Video file not found: {video_path}")
            failure += 1
            continue
        
        try:
            # Upload video
            remote_path = f"{week_id}/{video_path.name}"
            video_url = upload_video_to_hf(video_path, remote_path, dataset_id)
            
            # Try to upload slides if available
            slides_url = None
            if paper.slides_path:
                slides_path = Path(paper.slides_path)
                if slides_path.exists():
                    remote_slides_path = f"{week_id}/{slides_path.name}"
                    try:
                        slides_url = upload_video_to_hf(slides_path, remote_slides_path, dataset_id)
                        logger.info(f"Uploaded slides: {slides_url}")
                    except Exception as e:
                        logger.warning(f"Failed to upload slides for {paper.paper_id}: {e}")
                else:
                    logger.debug(f"Slides file not found: {slides_path}")
            
            # Add to metadata
            paper_data = {
                "paper_id": paper.paper_id,
                "title": paper.title or f"Paper {paper.paper_id}",
                "pdf_url": f"https://arxiv.org/pdf/{paper.paper_id}.pdf",
                "hf_url": f"https://huggingface.co/papers/{paper.paper_id}",
                "video_url": video_url,
                "video_filename": video_path.name,
                "slides_url": slides_url,
                "published_at": datetime.now().isoformat(),
            }
            
            # Update or add paper in metadata
            found = False
            for i, p in enumerate(metadata["weeks"][week_id]):
                if p["paper_id"] == paper.paper_id:
                    metadata["weeks"][week_id][i] = paper_data
                    found = True
                    break
            
            if not found:
                metadata["weeks"][week_id].append(paper_data)
            
            logger.info(f"Published: {paper.paper_id}")
            success += 1
            
        except Exception as e:
            logger.error(f"Failed to publish {paper.paper_id}: {e}")
            failure += 1
    
    # Save updated metadata
    if success > 0:
        save_metadata(metadata, dataset_id)
    
    logger.info(f"Publish complete for week {week_id}: {success} success, {failure} failed")
    return success, failure


def generate_digest_markdown(week_id: str, dataset_id: Optional[str] = None) -> Path:
    """
    Generate a markdown digest file with video links.
    
    Args:
        week_id: Week identifier
        dataset_id: HF dataset ID
        
    Returns:
        Path to the generated markdown file
    """
    dataset_id = dataset_id or get_hf_dataset_id()
    metadata = load_metadata(dataset_id)
    
    if week_id not in metadata["weeks"]:
        raise ValueError(f"No data found for week {week_id}")
    
    papers = metadata["weeks"][week_id]
    
    # Generate markdown
    lines = [
        f"# 📚 Paper Digest - Week {week_id}",
        "",
        f"> Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> Videos hosted on [HuggingFace]({f'https://huggingface.co/datasets/{dataset_id}'})",
        "",
        "---",
        "",
    ]
    
    for i, paper in enumerate(papers, 1):
        lines.extend([
            f"## {i}. {paper['title']}",
            "",
            f"**Paper ID:** `{paper['paper_id']}`",
            "",
            f"📄 [arXiv PDF]({paper['pdf_url']}) | 🤗 [HuggingFace Paper]({paper['hf_url']})",
            "",
            f"### 🎬 Video Overview",
            "",
            f"[![Video]({paper['video_url']})]({paper['video_url']})",
            "",
            f"[▶️ Watch Video]({paper['video_url']})",
            "",
            "---",
            "",
        ])
    
    # Save markdown
    output_dir = DIGEST_DIR / "published"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    md_path = output_dir / f"{week_id}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    logger.info(f"Generated digest: {md_path}")
    return md_path
