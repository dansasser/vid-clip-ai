#!/usr/bin/env python3
"""
User Initialization Script

Creates a new user's directory structure and watch directory entry.

Usage:
    python scripts/init_user.py <user_id> [base_path]

Example:
    python scripts/init_user.py admin ./data
"""

import sys
import os
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.file_system import create_user_directory_tree
from src.database.schema import get_session
from src.database.operations import DatabaseOperations
from src.config.settings import settings


def init_user(user_id: str, base_path: str = None) -> None:
    """
    Initialize a new user with directory structure and database entry.

    This operation is atomic - if database registration fails, directories
    are cleaned up. If directories exist but DB entry doesn't, creates DB entry.

    Args:
        user_id: User identifier
        base_path: Base path for user directories (default from settings)

    Raises:
        ValueError: If user already exists with different path
        Exception: If initialization fails
    """
    if base_path is None:
        base_path = str(settings.BASE_DATA_DIR)

    print(f"Initializing user: {user_id}")
    print(f"Base path: {base_path}")

    session = None
    created_dirs = False

    try:
        # Check if user already exists in database
        session = get_session()
        db_ops = DatabaseOperations(session)

        existing = db_ops.get_watch_directory_by_user(user_id)
        if existing:
            print(f"\n⚠ User '{user_id}' already exists with watch directories:")
            for wd in existing:
                status = "✓ exists" if os.path.isdir(wd.directory_path) else "✗ missing"
                print(f"  - {wd.directory_path} ({status})")
            return

        # Create directory structure
        user_path = create_user_directory_tree(base_path, user_id)
        created_dirs = True
        print(f"✓ Created directory structure at: {user_path}")

        # Add watch directory to database (validates directory exists)
        watch_dir = user_path / "incoming"
        result = db_ops.create_watch_directory(
            user_id=user_id,
            directory_path=str(watch_dir),
            validate_exists=True  # Ensures directory exists before DB insert
        )

        print(f"✓ Added watch directory to database: {watch_dir}")
        print(f"  Watch directory ID: {result.id}")
        print(f"\n✅ User '{user_id}' initialized successfully!")
        print(f"\nDirectory structure:")
        print(f"  {user_path}/")
        print(f"  ├── incoming/     # Drop videos here (watched)")
        print(f"  ├── processed/    # Active processing")
        print(f"  └── archived/     # Long-term storage")
        print(f"\nTo start using:")
        print(f"  1. Place video files in: {watch_dir}")
        print(f"  2. Run: python -m src.main")

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        print("Directory creation may have failed.")
        raise

    except ValueError as e:
        print(f"\n✗ Error: {e}")
        # Directory already registered, don't clean up
        raise

    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        # Rollback: Clean up directories if we created them
        if created_dirs:
            print("Rolling back directory creation...")
            import shutil
            user_path = Path(base_path) / user_id
            if user_path.exists():
                shutil.rmtree(user_path)
                print(f"✓ Cleaned up: {user_path}")
        raise

    finally:
        if session:
            session.close()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/init_user.py <user_id> [base_path]")
        print("\nExample:")
        print("  python scripts/init_user.py admin ./data")
        sys.exit(1)

    user_id = sys.argv[1]
    base_path = sys.argv[2] if len(sys.argv) > 2 else None

    init_user(user_id, base_path)


if __name__ == "__main__":
    main()
