"""
Database Operations - CRUD operations with user scoping.

Provides:
- User-scoped queries
- Video lifecycle state updates
- Transcript and segment management
- Score recording and retrieval
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from .models import (
    WatchDirectory, Video, Transcript, Segment, SegmentScore, ProcessingLog
)


class DatabaseOperations:
    """Database operations handler with user scoping."""

    def __init__(self, session: Session):
        self.session = session

    # Watch Directory Operations
    def get_active_watch_directories(self, validate_exists: bool = False) -> List[WatchDirectory]:
        """
        Get all active watch directories.

        Args:
            validate_exists: If True, filter out directories that don't exist on filesystem

        Returns:
            List of active WatchDirectory objects
        """
        watch_dirs = self.session.query(WatchDirectory).filter_by(is_active=True).all()

        if validate_exists:
            import os
            watch_dirs = [wd for wd in watch_dirs if os.path.isdir(wd.directory_path)]

        return watch_dirs

    def get_watch_directory_by_user(self, user_id: str) -> List[WatchDirectory]:
        """Get all watch directories for a specific user."""
        return self.session.query(WatchDirectory).filter_by(user_id=user_id).all()

    def create_watch_directory(self, user_id: str, directory_path: str,
                              validate_exists: bool = True) -> WatchDirectory:
        """
        Create a new watch directory for a user.

        Args:
            user_id: User identifier
            directory_path: Absolute path to directory
            validate_exists: If True, verify directory exists before creating DB entry

        Returns:
            WatchDirectory object

        Raises:
            FileNotFoundError: If validate_exists=True and directory doesn't exist
            ValueError: If directory already registered in database
        """
        import os

        # Validate directory exists if requested
        if validate_exists and not os.path.isdir(directory_path):
            raise FileNotFoundError(f"Directory does not exist: {directory_path}")

        # Check for duplicate
        existing = self.session.query(WatchDirectory).filter_by(
            user_id=user_id,
            directory_path=directory_path
        ).first()

        if existing:
            raise ValueError(
                f"Watch directory already exists for user '{user_id}': {directory_path}"
            )

        watch_dir = WatchDirectory(user_id=user_id, directory_path=directory_path)
        self.session.add(watch_dir)
        self.session.commit()
        return watch_dir

    # Video Operations
    def create_video(self, file_path: str, user_id: str,
                     watch_directory_id: int, **kwargs) -> Video:
        """Create a new video record."""
        video = Video(
            file_path=file_path,
            user_id=user_id,
            watch_directory_id=watch_directory_id,
            **kwargs
        )
        self.session.add(video)
        self.session.commit()
        return video

    def get_video(self, video_id: int) -> Optional[Video]:
        """Get video by ID."""
        return self.session.query(Video).filter_by(id=video_id).first()

    def get_user_videos(self, user_id: str) -> List[Video]:
        """Get all videos for a user."""
        return self.session.query(Video).filter_by(user_id=user_id).all()

    def update_video_status(self, video_id: int, status: str) -> None:
        """Update video lifecycle state."""
        video = self.get_video(video_id)
        if video:
            video.status = status
            self.session.commit()

    # Transcript Operations
    def add_transcript_segments(self, video_id: int,
                               segments: List[Dict[str, Any]]) -> None:
        """Add transcript segments for a video."""
        for seg in segments:
            transcript = Transcript(
                video_id=video_id,
                start_time=seg['start_time'],
                end_time=seg['end_time'],
                text=seg['text']
            )
            self.session.add(transcript)
        self.session.commit()

    def get_transcript(self, video_id: int) -> List[Transcript]:
        """Get transcript for a video."""
        return self.session.query(Transcript).filter_by(video_id=video_id).all()

    # Segment Operations
    def add_segment(self, video_id: int, start_time: float,
                   end_time: float, source: str) -> Segment:
        """Add a clip candidate segment."""
        segment = Segment(
            video_id=video_id,
            start_time=start_time,
            end_time=end_time,
            source=source
        )
        self.session.add(segment)
        self.session.commit()
        return segment

    def get_segments(self, video_id: int) -> List[Segment]:
        """Get all segments for a video."""
        return self.session.query(Segment).filter_by(video_id=video_id).all()

    # Score Operations
    def add_or_update_score(self, segment_id: int, **scores) -> None:
        """Add or update scores for a segment."""
        score = self.session.query(SegmentScore).filter_by(segment_id=segment_id).first()

        if score:
            # Update existing
            for key, value in scores.items():
                if value is not None:
                    setattr(score, key, value)
        else:
            # Create new
            score = SegmentScore(segment_id=segment_id, **scores)
            self.session.add(score)

        self.session.commit()

    def get_segment_scores(self, video_id: int) -> List[Dict[str, Any]]:
        """Get all segments with scores for a video."""
        segments = self.session.query(Segment).filter_by(video_id=video_id).all()
        result = []
        for seg in segments:
            result.append({
                'segment_id': seg.id,
                'start_time': seg.start_time,
                'end_time': seg.end_time,
                'source': seg.source,
                'scores': seg.scores.__dict__ if seg.scores else None
            })
        return result

    # Logging Operations
    def log_step(self, video_id: int, step: str, status: str, message: str = None) -> None:
        """Log a pipeline step."""
        log_entry = ProcessingLog(
            video_id=video_id,
            step=step,
            status=status,
            message=message
        )
        self.session.add(log_entry)
        self.session.commit()

    def get_processing_logs(self, video_id: int) -> List[ProcessingLog]:
        """Get processing logs for a video."""
        return self.session.query(ProcessingLog).filter_by(video_id=video_id).all()
