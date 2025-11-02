#!/usr/bin/env python3
"""
Video Clip Extraction System - Main Entry Point

Starts the file watcher and pipeline processing system.

Usage:
    python -m src.main [options]

Options:
    --db-url TEXT       Database URL (default: from .env)
    --log-level TEXT    Logging level (DEBUG, INFO, WARNING, ERROR)
    --daemon            Run as daemon (no output)
    --once              Process existing files once and exit
    --help              Show this message and exit
"""

import sys
import signal
import time
import argparse
from pathlib import Path
from typing import Optional

from .config.settings import settings
from .utils.logging_config import setup_logging
from .database.schema import get_session, get_engine
from .database.operations import DatabaseOperations
from .agents.file_watcher import FileWatcherAgent
from .pipeline.orchestrator import PipelineOrchestrator

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle CTRL+C and other termination signals."""
    global shutdown_requested
    print("\n\n⚠ Shutdown requested... cleaning up...")
    shutdown_requested = True


def check_database_connectivity(db_url: str) -> bool:
    """
    Verify database is accessible.

    Args:
        db_url: Database URL to check

    Returns:
        True if database is accessible
    """
    try:
        engine = get_engine(db_url)
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def check_prerequisites() -> bool:
    """
    Check that all prerequisites are met before starting.

    Returns:
        True if all checks pass
    """
    import subprocess

    print("Checking prerequisites...")

    # Check FFmpeg
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
            timeout=5
        )
        print("  ✓ FFmpeg found")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        print("  ✗ FFmpeg not found - install ffmpeg and add to PATH")
        return False

    return True


def run_once_mode(db_url: str, config: dict) -> int:
    """
    Process all existing files in watch directories once and exit.

    Args:
        db_url: Database URL
        config: Configuration dictionary

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    print("Running in ONCE mode - processing existing files only\n")

    session = get_session(db_url)
    db_ops = DatabaseOperations(session)

    # Get all active watch directories
    watch_dirs = db_ops.get_active_watch_directories(validate_exists=True)

    if not watch_dirs:
        print("⚠ No active watch directories found")
        print("  Run: python scripts/init_user.py <user_id> to create a user")
        session.close()
        return 0

    print(f"Found {len(watch_dirs)} watch directories to process\n")

    # Initialize file watcher and orchestrator
    file_watcher = FileWatcherAgent(config.get('file_watcher', {}))
    orchestrator = PipelineOrchestrator(db_ops, config)

    total_processed = 0
    total_errors = 0

    # Process each watch directory
    for watch_dir in watch_dirs:
        print(f"Processing: {watch_dir.directory_path}")

        # Get all video files in directory
        from .utils.file_system import is_video_file
        import os

        video_files = [
            f for f in os.listdir(watch_dir.directory_path)
            if os.path.isfile(os.path.join(watch_dir.directory_path, f))
            and is_video_file(f, file_watcher.supported_formats)
        ]

        if not video_files:
            print(f"  No video files found\n")
            continue

        print(f"  Found {len(video_files)} video file(s)")

        for video_file in video_files:
            file_path = os.path.join(watch_dir.directory_path, video_file)
            print(f"  → {video_file}")

            try:
                # Process file
                result = file_watcher.process_file(
                    file_path=file_path,
                    watch_directory_id=watch_dir.id,
                    user_id=watch_dir.user_id,
                    db_ops=db_ops
                )

                if result.get('success'):
                    total_processed += 1
                    print(f"    ✓ Registered as video_id={result['video_id']}")

                    # Trigger pipeline (will be implemented later)
                    # context = result['context']
                    # orchestrator.execute_pipeline(context)
                else:
                    total_errors += 1
                    print(f"    ✗ Failed: {result.get('error')}")

            except Exception as e:
                total_errors += 1
                print(f"    ✗ Error: {e}")

        print()

    print(f"Summary: {total_processed} processed, {total_errors} errors")
    session.close()
    return 0 if total_errors == 0 else 1


def run_watch_mode(db_url: str, config: dict) -> int:
    """
    Run in watch mode - continuously monitor directories.

    Args:
        db_url: Database URL
        config: Configuration dictionary

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    global shutdown_requested

    print("Starting in WATCH mode - monitoring directories...\n")

    session = get_session(db_url)
    db_ops = DatabaseOperations(session)

    # Get all active watch directories
    watch_dirs = db_ops.get_active_watch_directories(validate_exists=True)

    if not watch_dirs:
        print("✗ No active watch directories found")
        print("  Run: python scripts/init_user.py <user_id> to create a user")
        session.close()
        return 1

    print(f"Monitoring {len(watch_dirs)} directories:")
    for wd in watch_dirs:
        print(f"  [{wd.user_id}] {wd.directory_path}")
    print()

    # Initialize file watcher
    file_watcher = FileWatcherAgent(config.get('file_watcher', {}))
    orchestrator = PipelineOrchestrator(db_ops, config)

    # Start watching
    try:
        file_watcher.start_watching(db_ops, orchestrator)
        print("✓ File watcher started successfully")
        print("  Press CTRL+C to stop\n")

        # Keep running until shutdown requested
        while not shutdown_requested:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        print("Stopping file watcher...")
        file_watcher.stop_watching()
        session.close()
        print("✓ Shutdown complete")

    return 0


def main():
    """Main entry point."""
    global shutdown_requested

    parser = argparse.ArgumentParser(
        description="Video Clip Extraction System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in watch mode (default)
  python -m src.main

  # Process existing files once and exit
  python -m src.main --once

  # Use custom database
  python -m src.main --db-url postgresql://user:pass@localhost/vidclip

  # Enable debug logging
  python -m src.main --log-level DEBUG
        """
    )

    parser.add_argument(
        '--db-url',
        type=str,
        default=settings.DATABASE_URL,
        help='Database URL (default: from settings)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        default=settings.LOG_LEVEL,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Process existing files once and exit'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as daemon (minimal output)'
    )
    parser.add_argument(
        '--skip-checks',
        action='store_true',
        help='Skip prerequisite checks (for testing)'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(
        log_level=args.log_level,
        log_file=settings.LOG_FILE if not args.daemon else None
    )

    # Print banner
    if not args.daemon:
        print("=" * 70)
        print("VIDEO CLIP EXTRACTION SYSTEM")
        print("=" * 70)
        print()

    # Check prerequisites
    if not args.skip_checks and not check_prerequisites():
        print("\n✗ Prerequisites check failed")
        return 1

    # Check database connectivity
    if not check_database_connectivity(args.db_url):
        print("\n✗ Database connectivity check failed")
        print("  Run: python scripts/setup_db.py to initialize database")
        return 1

    print("  ✓ Database connected")
    print()

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Build configuration
    config = {
        'file_watcher': settings.get_agent_config('file_watcher'),
        'transcription': settings.get_agent_config('transcription'),
        'text_scoring': settings.get_agent_config('text_scoring'),
        'vision_scoring': settings.get_agent_config('vision_scoring'),
        'micro_emphasis': settings.get_agent_config('micro_emphasis'),
        'quality_assurance': settings.get_agent_config('quality_assurance'),
        'scoring_ranking': settings.get_agent_config('scoring_ranking'),
        'rendering': settings.get_agent_config('rendering'),
    }

    # Run in appropriate mode
    try:
        if args.once:
            return run_once_mode(args.db_url, config)
        else:
            return run_watch_mode(args.db_url, config)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
