#!/usr/bin/env python3
"""
Database Setup Script

Initializes the database schema and optionally creates an admin user.

Usage:
    python scripts/setup_db.py [--admin-dir <path>]

Example:
    python scripts/setup_db.py --admin-dir ./data/admin/incoming
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.schema import init_database
from src.config.settings import settings


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize database schema for vid-clip-ai"
    )
    parser.add_argument(
        '--admin-dir',
        type=str,
        help='Path to admin watch directory (will be created in database)'
    )
    parser.add_argument(
        '--db-url',
        type=str,
        default=settings.DATABASE_URL,
        help='Database URL (default from settings)'
    )

    args = parser.parse_args()

    print("Initializing database...")
    print(f"Database URL: {args.db_url}")

    init_database(
        db_url=args.db_url,
        admin_watch_dir=args.admin_dir
    )

    print("✓ Database initialized successfully!")

    if args.admin_dir:
        print(f"✓ Admin watch directory added: {args.admin_dir}")


if __name__ == "__main__":
    main()
