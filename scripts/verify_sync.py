#!/usr/bin/env python3
"""
Database and Filesystem Sync Verification Script

Checks consistency between database watch_directories and actual filesystem.
Can report issues or auto-fix them.

Usage:
    python scripts/verify_sync.py [--fix]

Options:
    --fix    Attempt to fix inconsistencies (create missing dirs, deactivate missing DB entries)
"""

import sys
import os
from pathlib import Path
from typing import List, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.schema import get_session
from src.database.operations import DatabaseOperations
from src.database.models import WatchDirectory
from src.utils.file_system import create_user_directory_tree


def check_consistency(fix: bool = False) -> Tuple[bool, List[str]]:
    """
    Check consistency between database and filesystem.

    Args:
        fix: If True, attempt to fix inconsistencies

    Returns:
        Tuple of (is_consistent, list_of_issues)
    """
    session = get_session()
    db_ops = DatabaseOperations(session)
    issues = []
    is_consistent = True

    print("=" * 70)
    print("DATABASE & FILESYSTEM CONSISTENCY CHECK")
    print("=" * 70)

    # Get all watch directories (active and inactive)
    all_watch_dirs = session.query(WatchDirectory).all()

    if not all_watch_dirs:
        print("\n⚠ No watch directories found in database")
        print("  Run: python scripts/init_user.py <user_id> to create a user")
        session.close()
        return True, []

    print(f"\nChecking {len(all_watch_dirs)} watch directories...\n")

    for wd in all_watch_dirs:
        status_icon = "✓" if wd.is_active else "○"
        dir_exists = os.path.isdir(wd.directory_path)

        # Check 1: Directory exists in filesystem
        if not dir_exists:
            is_consistent = False
            issue = f"✗ [{wd.user_id}] Directory missing: {wd.directory_path}"
            issues.append(issue)
            print(f"{status_icon} {issue}")

            if fix and wd.is_active:
                print(f"    → Deactivating watch directory (ID: {wd.id})")
                wd.is_active = False
                session.commit()
        else:
            print(f"{status_icon} [{wd.user_id}] {wd.directory_path}")

            # Check 2: Verify full user directory structure exists
            user_base = Path(wd.directory_path).parent
            required_dirs = ['incoming', 'processed', 'archived']

            for subdir in required_dirs:
                subdir_path = user_base / subdir
                if not subdir_path.exists():
                    is_consistent = False
                    issue = f"✗ [{wd.user_id}] Missing subdirectory: {subdir_path}"
                    issues.append(issue)
                    print(f"    {issue}")

                    if fix:
                        print(f"      → Creating: {subdir_path}")
                        subdir_path.mkdir(parents=True, exist_ok=True)

    # Summary
    print("\n" + "=" * 70)
    if is_consistent:
        print("✅ ALL CHECKS PASSED - Database and filesystem are in sync")
    else:
        print(f"⚠ FOUND {len(issues)} ISSUE(S)")
        if not fix:
            print("\nRun with --fix to attempt automatic repair:")
            print("  python scripts/verify_sync.py --fix")

    print("=" * 70)

    session.close()
    return is_consistent, issues


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify database and filesystem consistency"
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Attempt to fix inconsistencies automatically'
    )

    args = parser.parse_args()

    is_consistent, issues = check_consistency(fix=args.fix)

    # Exit with error code if inconsistent
    sys.exit(0 if is_consistent else 1)


if __name__ == "__main__":
    main()
