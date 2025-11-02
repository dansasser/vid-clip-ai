"""
Database Models - SQLAlchemy ORM models for all tables.

Tables:
- WatchDirectory: User directories being monitored
- Video: Source video metadata and state
- Transcript: Timestamped transcript segments
- Segment: Clip candidate segments
- SegmentScore: Multi-model scoring results
- ProcessingLog: Audit trail of pipeline steps

Design principles:
- Portable types (INTEGER, REAL, TEXT, TIMESTAMP)
- Foreign key relationships
- Non-destructive schema (never loses data)
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class WatchDirectory(Base):
    """User directories being monitored for new videos."""
    __tablename__ = 'watch_directories'

    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    directory_path = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    videos = relationship("Video", back_populates="watch_directory")


class Video(Base):
    """Source video metadata and processing state."""
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True)
    file_path = Column(Text, nullable=False)
    title = Column(String)
    source_type = Column(String)  # 'local', 'youtube', 'gdrive', etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='pending')  # State machine status
    user_id = Column(String, nullable=False, index=True)
    watch_directory_id = Column(Integer, ForeignKey('watch_directories.id'))

    # Relationships
    watch_directory = relationship("WatchDirectory", back_populates="videos")
    transcript = relationship("Transcript", back_populates="video", cascade="all, delete-orphan")
    segments = relationship("Segment", back_populates="video", cascade="all, delete-orphan")
    processing_logs = relationship("ProcessingLog", back_populates="video", cascade="all, delete-orphan")


class Transcript(Base):
    """Timestamped transcript segments from WhisperX."""
    __tablename__ = 'transcript'

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=False, index=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="transcript")


class Segment(Base):
    """Clip candidate segments identified by text/vision scoring."""
    __tablename__ = 'segments'

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=False, index=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    source = Column(String, nullable=False)  # 'asr', 'local_vlm', 'cloud_vlm'

    # Relationships
    video = relationship("Video", back_populates="segments")
    scores = relationship("SegmentScore", back_populates="segment", uselist=False, cascade="all, delete-orphan")


class SegmentScore(Base):
    """Multi-model scoring results for each segment."""
    __tablename__ = 'segment_scores'

    segment_id = Column(Integer, ForeignKey('segments.id'), primary_key=True)
    text_score = Column(Float)
    vision_score = Column(Float)
    audio_emphasis_score = Column(Float)
    facial_emphasis_score = Column(Float)
    cloud_score = Column(Float)
    combined_score = Column(Float)
    escalated_to_cloud = Column(Boolean, default=False)

    # Relationships
    segment = relationship("Segment", back_populates="scores")


class ProcessingLog(Base):
    """Audit trail of pipeline steps for debugging and resumability."""
    __tablename__ = 'processing_log'

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey('videos.id'), nullable=False, index=True)
    step = Column(String, nullable=False)  # 'download', 'transcribe', 'segment', 'score', 'render'
    status = Column(String, nullable=False)  # 'ok', 'fail'
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="processing_logs")
