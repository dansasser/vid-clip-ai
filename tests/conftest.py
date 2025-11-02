"""
Pytest configuration and shared fixtures.

Provides:
- Database fixtures
- Temporary directory fixtures
- Mock model fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base
from src.database.operations import DatabaseOperations


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture
def db_ops(test_db):
    """Create database operations handler with test database."""
    return DatabaseOperations(test_db)


@pytest.fixture
def sample_video_path(temp_dir):
    """Create a sample video file path (empty file for testing)."""
    video_path = temp_dir / "test_video.mp4"
    video_path.touch()
    return str(video_path)


@pytest.fixture
def test_user():
    """Test user configuration."""
    return {
        'user_id': 'test_user',
        'base_path': '/tmp/test_data'
    }
