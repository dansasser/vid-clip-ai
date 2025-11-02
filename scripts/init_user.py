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

    Args:
        user_id: User identifier
        base_path: Base path for user directories (default from settings)
    """
    if base_path is None:
        base_path = str(settings.BASE_DATA_DIR)

    print(f"Initializing user: {user_id}")
    print(f"Base path: {base_path}")

    # Create directory structure
    user_path = create_user_directory_tree(base_path, user_id)
    print(f"✓ Created directory structure at: {user_path}")

    # Add watch directory to database
    session = get_session()
    db_ops = DatabaseOperations(session)

    watch_dir = user_path / "incoming"
    existing = session.query(
        db_ops.session.query(
            # Check if directory already exists
        )
    )

    result = db_ops.create_watch_directory(
        user_id=user_id,
        directory_path=str(watch_dir)
    )

    print(f"✓ Added watch directory to database: {watch_dir}")
    print(f"  Watch directory ID: {result.id}")
    print(f"\nUser '{user_id}' initialized successfully!")
    print(f"\nTo start using:")
    print(f"  1. Place video files in: {watch_dir}")
    print(f"  2. Start the pipeline to process them automatically")

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
