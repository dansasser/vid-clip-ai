"""
File System Utilities - Directory management and file operations.

Provides:
- User directory initialization
- File moving and copying
- Path validation
- Directory cleanup
"""

from pathlib import Path
from typing import Optional
import shutil
import os


def create_user_directory_tree(base_path: str, user_id: str) -> Path:
    """
    Create directory structure for a new user.

    Structure:
    <base_path>/<user_id>/
        ├── incoming/     # Watch directory
        ├── processed/    # Active processing
        └── archived/     # Long-term storage

    Args:
        base_path: Root directory for user data
        user_id: User identifier

    Returns:
        Path to user's base directory
    """
    user_path = Path(base_path) / user_id

    # Create subdirectories
    (user_path / "incoming").mkdir(parents=True, exist_ok=True)
    (user_path / "processed").mkdir(parents=True, exist_ok=True)
    (user_path / "archived").mkdir(parents=True, exist_ok=True)

    return user_path


def move_file(source: str, destination: str) -> bool:
    """
    Move file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path

    Returns:
        True if successful
    """
    try:
        shutil.move(source, destination)
        return True
    except Exception as e:
        print(f"Error moving file: {e}")
        return False


def get_file_extension(file_path: str) -> str:
    """Get file extension (lowercase, with dot)."""
    return Path(file_path).suffix.lower()


def is_video_file(file_path: str, supported_formats: list = None) -> bool:
    """
    Check if file is a supported video format.

    Args:
        file_path: Path to file
        supported_formats: List of supported extensions (default: ['.mp4', '.mov', '.avi'])

    Returns:
        True if file is a supported video format
    """
    if supported_formats is None:
        supported_formats = ['.mp4', '.mov', '.avi', '.mkv', '.webm']

    ext = get_file_extension(file_path)
    return ext in supported_formats


def ensure_directory(directory: str) -> Path:
    """
    Ensure directory exists, create if it doesn't.

    Args:
        directory: Directory path

    Returns:
        Path object
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes."""
    return os.path.getsize(file_path) / (1024 * 1024)
