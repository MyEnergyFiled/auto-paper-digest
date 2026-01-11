"""
CLI module for Auto Paper Digest.

Provides commands for fetching papers, downloading PDFs,
running NotebookLM automation, and generating digests.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .config import Status, ensure_directories
from .db import count_papers, get_paper, init_db, list_papers
from .utils import get_current_week_id, get_logger, setup_logging


# =============================================================================
# CLI Group
# =============================================================================

@click.group()
@click.version_option(version=__version__, prog_name="apd")
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging"
)
@click.pass_context
def main(ctx: click.Context, debug: bool) -> None:
    """
    Auto Paper Digest - Fetch HF papers, generate NotebookLM video overviews.
    
    Run 'apd COMMAND --help' for more information on a command.
    """
    ctx.ensure_object(dict)
    
    # Setup logging
    level = "DEBUG" if debug else "INFO"
    setup_logging(level=level)
    
    # Initialize database and directories
    ensure_directories()
    init_db()


# =============================================================================
# Fetch Command
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=50,
    type=int,
    help="Maximum papers to fetch (default: 50)"
)
def fetch(week: Optional[str], max_papers: int) -> None:
    """
    Fetch papers from Hugging Face for a given week.
    
    Scrapes the HF daily papers pages and stores paper metadata
    in the local database.
    """
    from .hf_fetcher import fetch_weekly_papers
    
    logger = get_logger()
    week_id = week or get_current_week_id()
    
    click.echo(f"📚 Fetching papers for week {week_id}...")
    
    try:
        papers = fetch_weekly_papers(week_id, max_papers=max_papers)
        click.echo(f"✅ Fetched {len(papers)} papers")
        
        # Show stats
        total = count_papers(week_id=week_id)
        click.echo(f"   Total papers in database for {week_id}: {total}")
        
    except Exception as e:
        logger.exception("Fetch failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Download Command
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--paper-id", "-p",
    default=None,
    help="Download a specific paper by ID"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-download even if PDF exists"
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=None,
    type=int,
    help="Maximum papers to download"
)
def download(
    week: Optional[str],
    paper_id: Optional[str],
    force: bool,
    max_papers: Optional[int]
) -> None:
    """
    Download PDFs from arXiv for fetched papers.
    
    Downloads are idempotent - existing files with matching
    SHA256 hashes will be skipped unless --force is used.
    """
    from .pdf_downloader import download_pdfs_for_week, download_single_paper
    
    logger = get_logger()
    
    try:
        if paper_id:
            # Download single paper
            click.echo(f"📄 Downloading PDF for paper {paper_id}...")
            result = download_single_paper(paper_id, force=force)
            if result:
                click.echo(f"✅ Downloaded: {result}")
            else:
                click.echo("❌ Download failed", err=True)
                sys.exit(1)
        else:
            # Download all papers for week
            week_id = week or get_current_week_id()
            click.echo(f"📄 Downloading PDFs for week {week_id}...")
            
            success, failure = download_pdfs_for_week(
                week_id, force=force, max_papers=max_papers
            )
            
            click.echo(f"✅ Downloads complete: {success} success, {failure} failed")
            
    except Exception as e:
        logger.exception("Download failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# NotebookLM Command
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--paper-id", "-p",
    default=None,
    help="Process a specific paper by ID"
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run browser in visible mode (required for first-time login)"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force reprocessing even if already done"
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=None,
    type=int,
    help="Maximum papers to process"
)
@click.option(
    "--prompt",
    default=None,
    help="Steering prompt for video generation"
)
def nblm(
    week: Optional[str],
    paper_id: Optional[str],
    headful: bool,
    force: bool,
    max_papers: Optional[int],
    prompt: Optional[str]
) -> None:
    """
    Process papers through NotebookLM.
    
    Creates notebooks, uploads PDFs, generates Audio Overview videos,
    and downloads them locally.
    
    First-time usage requires --headful for manual Google login.
    Subsequent runs can be headless (the session is persisted).
    """
    from pathlib import Path
    from .nblm_bot import NotebookLMBot, process_papers_for_week
    
    logger = get_logger()
    headless = not headful
    
    try:
        if paper_id:
            # Process single paper
            paper = get_paper(paper_id)
            if not paper:
                click.echo(f"❌ Paper not found: {paper_id}", err=True)
                sys.exit(1)
            
            if not paper.pdf_path:
                click.echo(f"❌ Paper has no PDF downloaded: {paper_id}", err=True)
                sys.exit(1)
            
            click.echo(f"🤖 Processing paper {paper_id} through NotebookLM...")
            
            with NotebookLMBot(headless=headless) as bot:
                result = bot.process_paper(
                    paper_id=paper_id,
                    pdf_path=Path(paper.pdf_path),
                    week_id=paper.week_id,
                    steering_prompt=prompt,
                    force=force
                )
            
            if result:
                click.echo(f"✅ Successfully processed paper {paper_id}")
            else:
                click.echo(f"❌ Failed to process paper {paper_id}", err=True)
                sys.exit(1)
        else:
            # Process all papers for week
            week_id = week or get_current_week_id()
            
            # Check how many papers are ready
            ready = count_papers(week_id=week_id, status=Status.PDF_OK)
            if ready == 0:
                click.echo(f"⚠️  No papers ready for NotebookLM processing in week {week_id}")
                click.echo("   Run 'apd download' first to download PDFs.")
                return
            
            click.echo(f"🤖 Processing {ready} papers for week {week_id}...")
            
            success, failure = process_papers_for_week(
                week_id=week_id,
                headless=headless,
                max_papers=max_papers,
                force=force,
                steering_prompt=prompt
            )
            
            click.echo(f"✅ Processing complete: {success} success, {failure} failed")
            
    except Exception as e:
        logger.exception("NotebookLM processing failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Upload Command (Phase 1 of two-phase workflow)
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run browser in visible mode (required for first-time login)"
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=10,
    type=int,
    help="Maximum papers to process (default: 10)"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-processing even if already done"
)
def upload(
    week: Optional[str],
    headful: bool,
    max_papers: int,
    force: bool
) -> None:
    """
    Phase 1: Fetch papers, download PDFs, upload to NotebookLM, trigger video generation.
    
    Complete first phase of the two-phase workflow:
    1. Fetches papers from Hugging Face
    2. Downloads PDFs from arXiv
    3. Creates notebooks named {week_id}_{paper_id}
    4. Uploads PDF and waits for content to load
    5. Triggers video generation (doesn't wait for completion)
    
    After this completes, wait a few minutes for videos to generate,
    then run 'apd download-video' to download them.
    
    Use --force to re-process papers that have already been uploaded.
    """
    from .hf_fetcher import fetch_weekly_papers
    from .nblm_bot import upload_papers_for_week
    from .pdf_downloader import download_pdfs_for_week
    
    logger = get_logger()
    week_id = week or get_current_week_id()
    headless = not headful
    
    click.echo(f"🚀 Phase 1: Upload pipeline for week {week_id}")
    click.echo(f"   Max papers: {max_papers}")
    if force:
        click.echo(f"   Force mode: ON (will re-process already uploaded papers)")
    click.echo()
    
    try:
        # Step 1: Fetch papers
        click.echo("=" * 50)
        click.echo("📚 Step 1: Fetching papers from Hugging Face...")
        papers = fetch_weekly_papers(week_id, max_papers=max_papers)
        click.echo(f"   Fetched {len(papers)} papers")
        
        if not papers:
            click.echo("⚠️  No papers found for this week.")
            return
        
        # Step 2: Download PDFs
        click.echo()
        click.echo("=" * 50)
        click.echo("📄 Step 2: Downloading PDFs from arXiv...")
        dl_success, dl_failure = download_pdfs_for_week(
            week_id, force=force, max_papers=max_papers
        )
        click.echo(f"   Downloads: {dl_success} success, {dl_failure} failed")
        
        # Step 3: Upload to NotebookLM
        click.echo()
        click.echo("=" * 50)
        click.echo("📤 Step 3: Uploading to NotebookLM & triggering video generation...")
        click.echo(f"   Notebooks will be named: {week_id}_{{paper_id}}")
        
        success, failure = upload_papers_for_week(
            week_id=week_id,
            headless=headless,
            max_papers=max_papers,
            force=force
        )
        
        # Summary
        click.echo()
        click.echo("=" * 50)
        click.echo(f"✅ Phase 1 complete: {success} success, {failure} failed")
        if success > 0:
            click.echo()
            click.echo("💡 Videos are now generating in NotebookLM.")
            click.echo("   Wait a few minutes, then run:")
            click.echo(f"   apd download-video --week {week_id}")
            
    except KeyboardInterrupt:
        click.echo("\n⚠️  Upload interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Upload failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Download Video Command (Phase 2 of two-phase workflow)
# =============================================================================

@main.command("download-video")
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run browser in visible mode"
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=None,
    type=int,
    help="Maximum papers to process"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-download even if video already exists"
)
def download_video(
    week: Optional[str],
    headful: bool,
    max_papers: Optional[int],
    force: bool
) -> None:
    """
    Download generated videos from NotebookLM.
    
    Phase 2 of the two-phase workflow:
    1. Opens NotebookLM home page
    2. Finds notebooks with {week_id}_ prefix
    3. Checks if video is ready for each
    4. Downloads completed videos
    
    Run this after 'apd upload' and waiting for videos to generate.
    """
    from .nblm_bot import download_videos_for_week
    
    logger = get_logger()
    week_id = week or get_current_week_id()
    headless = not headful
    
    try:
        # Check how many papers are awaiting download
        awaiting = count_papers(week_id=week_id, status=Status.NBLM_OK)
        video_ok = count_papers(week_id=week_id, status=Status.VIDEO_OK)
        
        if awaiting == 0 and (video_ok == 0 or not force):
            click.echo(f"⚠️  No papers awaiting video download in week {week_id}")
            if video_ok > 0:
                click.echo(f"   ({video_ok} videos already downloaded. Use --force to re-download)")
            else:
                click.echo("   Run 'apd upload' first to upload PDFs to NotebookLM.")
            return
        
        total = awaiting + (video_ok if force else 0)
        click.echo(f"📥 Downloading videos for {total} papers in week {week_id}...")
        if force and video_ok > 0:
            click.echo(f"   (--force: will re-check {video_ok} already downloaded videos)")
        click.echo()
        
        success, failure, skipped = download_videos_for_week(
            week_id=week_id,
            headless=headless,
            max_papers=max_papers,
            force=force
        )
        
        click.echo()
        result_msg = f"✅ Download complete: {success} success, {failure} failed"
        if skipped > 0:
            result_msg += f", {skipped} skipped (already downloaded)"
        click.echo(result_msg)
        if failure > 0:
            click.echo()
            click.echo("💡 Some videos may still be generating. Try again later.")
            
    except Exception as e:
        logger.exception("Video download failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Digest Command
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--all", "-a",
    "include_all",
    is_flag=True,
    help="Include all papers, not just those with videos"
)
def digest(week: Optional[str], include_all: bool) -> None:
    """
    Generate weekly digest files.
    
    Creates Markdown and JSON files summarizing all processed
    papers for the specified week.
    """
    from .digest import generate_digest, print_digest_summary
    
    logger = get_logger()
    week_id = week or get_current_week_id()
    
    try:
        click.echo(f"📝 Generating digest for week {week_id}...")
        
        md_path, json_path = generate_digest(week_id, include_all=include_all)
        
        click.echo(f"✅ Digest generated:")
        click.echo(f"   Markdown: {md_path}")
        click.echo(f"   JSON: {json_path}")
        
        print_digest_summary(week_id)
        
    except Exception as e:
        logger.exception("Digest generation failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Run Command (Full Pipeline)
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--max", "-m",
    "max_papers",
    default=10,
    type=int,
    help="Maximum papers to process (default: 10)"
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run browser in visible mode (required for first-time login)"
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force reprocessing of already completed papers"
)
@click.option(
    "--skip-nblm",
    is_flag=True,
    help="Skip NotebookLM processing (fetch + download only)"
)
def run(
    week: Optional[str],
    max_papers: int,
    headful: bool,
    force: bool,
    skip_nblm: bool
) -> None:
    """
    Run the full pipeline: fetch → download → nblm → digest.
    
    This is the main command for processing a week's worth of papers
    through the entire workflow.
    """
    from .digest import generate_digest, print_digest_summary
    from .hf_fetcher import fetch_weekly_papers
    from .nblm_bot import process_papers_for_week
    from .pdf_downloader import download_pdfs_for_week
    
    logger = get_logger()
    week_id = week or get_current_week_id()
    headless = not headful
    
    click.echo(f"🚀 Running full pipeline for week {week_id}")
    click.echo(f"   Max papers: {max_papers}")
    click.echo(f"   Mode: {'Headful' if headful else 'Headless'}")
    click.echo()
    
    try:
        # Step 1: Fetch
        click.echo("=" * 50)
        click.echo("📚 Step 1: Fetching papers from Hugging Face...")
        papers = fetch_weekly_papers(week_id, max_papers=max_papers)
        click.echo(f"   Fetched {len(papers)} papers")
        
        if not papers:
            click.echo("⚠️  No papers found for this week.")
            return
        
        # Step 2: Download
        click.echo()
        click.echo("=" * 50)
        click.echo("📄 Step 2: Downloading PDFs from arXiv...")
        dl_success, dl_failure = download_pdfs_for_week(
            week_id, force=force, max_papers=max_papers
        )
        click.echo(f"   Downloads: {dl_success} success, {dl_failure} failed")
        
        # Step 3: NotebookLM (optional)
        if not skip_nblm:
            click.echo()
            click.echo("=" * 50)
            click.echo("🤖 Step 3: Processing through NotebookLM...")
            nblm_success, nblm_failure = process_papers_for_week(
                week_id=week_id,
                headless=headless,
                max_papers=max_papers,
                force=force
            )
            click.echo(f"   NotebookLM: {nblm_success} success, {nblm_failure} failed")
        else:
            click.echo()
            click.echo("=" * 50)
            click.echo("⏭️  Step 3: Skipping NotebookLM processing (--skip-nblm)")
        
        # Step 4: Digest
        click.echo()
        click.echo("=" * 50)
        click.echo("📝 Step 4: Generating digest...")
        md_path, json_path = generate_digest(week_id)
        click.echo(f"   Markdown: {md_path}")
        click.echo(f"   JSON: {json_path}")
        
        # Summary
        click.echo()
        click.echo("=" * 50)
        click.echo("🎉 Pipeline complete!")
        print_digest_summary(week_id)
        
    except KeyboardInterrupt:
        click.echo("\n⚠️  Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Pipeline failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Status Command
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--status", "-s",
    "filter_status",
    default=None,
    type=click.Choice(["NEW", "PDF_OK", "NBLM_OK", "VIDEO_OK", "ERROR"]),
    help="Filter by status"
)
@click.option(
    "--limit", "-l",
    default=20,
    type=int,
    help="Maximum papers to show (default: 20)"
)
def status(
    week: Optional[str],
    filter_status: Optional[str],
    limit: int
) -> None:
    """
    Show status of papers in the database.
    
    Lists papers with their current processing status.
    """
    from .digest import print_digest_summary
    
    week_id = week or get_current_week_id()
    
    # Get papers
    papers = list_papers(week_id=week_id, status=filter_status, limit=limit)
    
    if not papers:
        click.echo(f"No papers found for week {week_id}")
        if filter_status:
            click.echo(f"   (filtered by status: {filter_status})")
        return
    
    # Print header
    click.echo(f"\n📋 Papers for week {week_id}")
    if filter_status:
        click.echo(f"   (filtered by status: {filter_status})")
    click.echo()
    
    # Print table
    click.echo(f"{'Paper ID':<15} {'Status':<10} {'Title':<50}")
    click.echo("-" * 75)
    
    for paper in papers:
        title = (paper.title or "Untitled")[:47]
        if len(paper.title or "") > 47:
            title += "..."
        status_icon = {
            Status.NEW: "🆕",
            Status.PDF_OK: "📄",
            Status.NBLM_OK: "📓",
            Status.VIDEO_OK: "✅",
            Status.ERROR: "❌",
        }.get(paper.status, "❓")
        click.echo(f"{paper.paper_id:<15} {status_icon} {paper.status:<8} {title}")
    
    # Print summary
    print_digest_summary(week_id)


# =============================================================================
# Login Command
# =============================================================================

@main.command()
def login() -> None:
    """
    Open browser for Google login to NotebookLM.
    
    Use this command for first-time setup to authenticate
    with your Google account. The session will be saved
    for future headless runs.
    """
    from .nblm_bot import NotebookLMBot
    
    click.echo("🔐 Opening browser for Google login...")
    click.echo("   Please complete the login process in the browser window.")
    click.echo("   The session will be saved for future use.")
    click.echo()
    
    with NotebookLMBot(headless=False) as bot:
        if bot.navigate_to_notebooklm():
            click.echo("✅ Already logged in!")
        else:
            click.echo("⏳ Waiting for login...")
            if bot.wait_for_login(timeout=300):
                click.echo("✅ Login successful! Session saved.")
            else:
                click.echo("❌ Login timeout. Please try again.", err=True)
                sys.exit(1)


# =============================================================================
# Publish Command (Phase 3)
# =============================================================================

@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-upload even if already published"
)
@click.option(
    "--digest-only",
    is_flag=True,
    help="Only generate digest markdown, don't upload videos"
)
def publish(
    week: Optional[str],
    force: bool,
    digest_only: bool
) -> None:
    """
    Publish videos to HuggingFace and generate digest.
    
    Phase 3 of the workflow:
    1. Upload videos to HuggingFace Dataset
    2. Update metadata.json with video links
    3. Generate markdown digest with embedded video links
    
    Requires HF_TOKEN and HF_USERNAME in .env file.
    """
    from .publisher import (
        generate_digest_markdown,
        get_hf_dataset_id,
        publish_week,
    )
    
    logger = get_logger()
    week_id = week or get_current_week_id()
    
    try:
        dataset_id = get_hf_dataset_id()
        click.echo(f"🚀 Publishing videos for week {week_id}")
        click.echo(f"   Dataset: {dataset_id}")
        click.echo()
        
        if not digest_only:
            # Upload videos
            click.echo("=" * 50)
            click.echo("📤 Uploading videos to HuggingFace...")
            
            success, failure = publish_week(week_id, force=force)
            
            click.echo(f"   Uploaded: {success} success, {failure} failed")
            
            if success == 0 and failure == 0:
                click.echo("⚠️  No videos to publish. Run 'apd download-video' first.")
                return
        
        # Generate digest
        click.echo()
        click.echo("=" * 50)
        click.echo("📝 Generating digest markdown...")
        
        try:
            md_path = generate_digest_markdown(week_id)
            click.echo(f"   Generated: {md_path}")
        except ValueError as e:
            click.echo(f"⚠️  {e}")
            click.echo("   Digest generation skipped.")
            return
        
        # Summary
        click.echo()
        click.echo("=" * 50)
        click.echo("🎉 Publish complete!")
        click.echo()
        click.echo(f"   📺 Videos: https://huggingface.co/datasets/{dataset_id}")
        click.echo(f"   📄 Digest: {md_path}")
        
    except ValueError as e:
        click.echo(f"❌ Configuration error: {e}", err=True)
        click.echo("   Please check your .env file.", err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Publish failed")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Douyin Commands (Phase 4)
# =============================================================================

@main.command()
def douyin_login() -> None:
    """
    Open browser for manual login to Douyin Creator Studio.
    
    This will open a headful browser for you to scan the QR code.
    The session will be saved for future automated publishing.
    """
    from .douyin_bot import DouyinBot
    
    click.echo("🔐 Opening browser for Douyin login...")
    click.echo("   Please scan the QR code to log in to Creator Studio.")
    click.echo("   The session will be saved for future automated publishing.")
    click.echo()
    
    with DouyinBot(headless=False) as bot:
        if bot.login():
            click.echo("✅ Douyin login successful! Session saved.")
        else:
            click.echo("❌ Douyin login failed or timed out.", err=True)
            sys.exit(1)


@main.command()
@click.option(
    "--week", "-w",
    default=None,
    help="Week ID (e.g., 2026-01). Defaults to current week."
)
@click.option(
    "--paper-id", "-p",
    help="ArXiv ID of a specific paper to publish."
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-publish even if already marked as VIDEO_OK."
)
@click.option(
    "--headful",
    is_flag=True,
    help="Run in headful mode (visible browser)."
)
def publish_douyin(
    week: Optional[str],
    paper_id: Optional[str],
    force: bool,
    headful: bool
) -> None:
    """
    Publish videos to Douyin Creator Studio.
    
    Phase 4 of the workflow:
    1. Authenticate using saved session
    2. Upload video file
    3. Fill in title, description, and tags
    4. Click Publish
    """
    from .douyin_bot import DouyinBot
    from .db import get_paper, list_papers
    
    logger = get_logger()
    week_id = week or get_current_week_id()
    
    # Identify papers to publish
    if paper_id:
        papers = [get_paper(paper_id)]
        if not papers[0]:
            click.echo(f"❌ Paper {paper_id} not found in database.", err=True)
            sys.exit(1)
    else:
        # Publish all papers for the week that have videos
        papers = list_papers(week_id=week_id, status=Status.VIDEO_OK)
        
    if not papers:
        click.echo(f"⚠️  No papers with videos found for week {week_id}.")
        click.echo("   Run 'apd download-video' first.")
        return
        
    click.echo(f"🚀 Publishing {len(papers)} videos to Douyin...")
    
    with DouyinBot(headless=not headful) as bot:
        # Check login first (only once at the beginning)
        if not bot.is_logged_in():
            click.echo("❌ Not logged into Douyin. Please run 'apd douyin-login' first.", err=True)
            sys.exit(1)
            
        success_count = 0
        total_papers = len(papers)
        
        for idx, paper in enumerate(papers, 1):
            click.echo(f"\n{'='*50}")
            click.echo(f"📹 Processing video {idx}/{total_papers}")
            
            if not paper.video_path:
                click.echo(f"⏭️  Skipping {paper.paper_id}: No video path found.")
                continue
                
            video_path = Path(paper.video_path)
            if not video_path.exists():
                click.echo(f"❌ Skipping {paper.paper_id}: Video file not found at {video_path}")
                continue
                
            click.echo(f"📤 Uploading {paper.paper_id}: {paper.title}")
            
            # Construct description and tags
            description = f"arXiv: {paper.paper_id}\n{paper.title}\n\nAutomated digest generated by Auto-Paper-Digest."
            tags = ["AI", "Research", "Arxiv", "MachineLearning"]
            
            # Skip login check since we already verified at the start
            if bot.publish_video(
                video_path=video_path,
                title=f"AI Paper Review: {paper.title}"[:50], # Douyin title limit
                description=description,
                tags=tags,
                skip_login_check=True  # Skip login check for batch publishing
            ):
                click.echo(f"✅ Successfully published {paper.paper_id}!")
                success_count += 1
            else:
                click.echo(f"❌ Failed to publish {paper.paper_id}.")
                
        click.echo()
        click.echo(f"🎉 Douyin publish complete: {success_count}/{total_papers} successful.")


if __name__ == "__main__":
    main()

