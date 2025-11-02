"""
Database Schema - Initialization and migration utilities.

Provides functions to:
- Create all tables
- Initialize database
- Add default admin user watch directory
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, WatchDirectory
import os


def init_database(db_url: str = None, admin_watch_dir: str = None) -> None:
    """
    Initialize database with schema and optional admin user.

    Args:
        db_url: SQLAlchemy database URL (default: sqlite:///vid_clip_ai.db)
        admin_watch_dir: Path to admin's watch directory
    """
    if db_url is None:
        db_url = os.getenv('DATABASE_URL', 'sqlite:///vid_clip_ai.db')

    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

    # Create admin watch directory if specified
    if admin_watch_dir:
        Session = sessionmaker(bind=engine)
        session = Session()

        # Check if admin watch directory already exists
        existing = session.query(WatchDirectory).filter_by(
            user_id='admin',
            directory_path=admin_watch_dir
        ).first()

        if not existing:
            watch_dir = WatchDirectory(
                user_id='admin',
                directory_path=admin_watch_dir,
                is_active=True
            )
            session.add(watch_dir)
            session.commit()

        session.close()


def get_engine(db_url: str = None):
    """Get database engine."""
    if db_url is None:
        db_url = os.getenv('DATABASE_URL', 'sqlite:///vid_clip_ai.db')
    return create_engine(db_url)


def get_session(db_url: str = None):
    """Get database session."""
    engine = get_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()
