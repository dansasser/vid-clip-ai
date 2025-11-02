"""
File Watcher Agent

Role: Detect new videos and trigger the pipeline automatically
Input: Monitors multiple directories from watch_directories table
Output: Pipeline execution start with user context

Key responsibilities:
- Watch all active directories in the database
- Detect new video files (mp4, mov, etc.)
- Identify which user the file belongs to
- Trigger pipeline with proper user context
- Move file to user's processing directory
"""

from typing import Dict, Any, Optional
from pathlib import Path
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from .base_agent import BaseAgent
from ..utils.file_system import is_video_file, move_file, get_file_size_mb
from ..utils.video_utils import get_video_info
from ..pipeline.context import PipelineContext


class VideoFileHandler(FileSystemEventHandler):
    """
    Watchdog event handler for video files.
    """

    def __init__(self, agent: 'FileWatcherAgent', watch_directory_id: int,
                 user_id: str, db_ops, orchestrator):
        self.agent = agent
        self.watch_directory_id = watch_directory_id
        self.user_id = user_id
        self.db_ops = db_ops
        self.orchestrator = orchestrator
        self.processing = set()  # Track files being processed

    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = event.src_path

        # Check if it's a video file
        if not is_video_file(file_path, self.agent.supported_formats):
            return

        # Avoid processing the same file multiple times
        if file_path in self.processing:
            return

        self.processing.add(file_path)

        try:
            self.agent.logger.info(f"Detected new video: {file_path}")
            print(f"📹 Detected: {os.path.basename(file_path)} [{self.user_id}]")

            # Wait a moment to ensure file is fully written
            # (some systems trigger event before write completes)
            time.sleep(1)

            # Process the file
            result = self.agent.process_file(
                file_path=file_path,
                watch_directory_id=self.watch_directory_id,
                user_id=self.user_id,
                db_ops=self.db_ops
            )

            if result.get('success'):
                print(f"  ✓ Registered as video_id={result['video_id']}")

                # Trigger pipeline if orchestrator available
                if self.orchestrator:
                    context = result['context']
                    print(f"  → Starting pipeline for video_id={context.video_id}")
                    self.orchestrator.execute_pipeline(context)

            else:
                print(f"  ✗ Failed: {result.get('error')}")

        except Exception as e:
            self.agent.logger.error(f"Error processing {file_path}: {e}")
            print(f"  ✗ Error: {e}")
        finally:
            self.processing.discard(file_path)


class FileWatcherAgent(BaseAgent):
    """
    Monitors user directories for new video files and initiates pipeline.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.supported_formats = config.get('supported_formats', ['.mp4', '.mov', '.avi'])
        self.watch_interval = config.get('watch_interval', 5)
        self.observer = None
        self.handlers = []

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a newly detected video file.

        This is called by the event handler when a new file is detected.

        Args:
            context:
                - file_path: Path to detected video file
                - watch_directory_id: ID of the watch directory
                - user_id: User who owns this directory
                - db_ops: Database operations handler

        Returns:
            - success: True if file moved and video registered
            - video_id: Generated unique identifier
            - context: PipelineContext object for orchestrator
            - error: Error message if failed
        """
        file_path = context['file_path']
        watch_directory_id = context['watch_directory_id']
        user_id = context['user_id']
        db_ops = context['db_ops']

        return self.process_file(file_path, watch_directory_id, user_id, db_ops)

    def process_file(self, file_path: str, watch_directory_id: int,
                    user_id: str, db_ops) -> Dict[str, Any]:
        """
        Process a detected video file.

        Args:
            file_path: Path to video file
            watch_directory_id: Watch directory ID
            user_id: User identifier
            db_ops: Database operations handler

        Returns:
            Result dictionary with success status and data
        """
        try:
            # Validate file exists and is accessible
            if not os.path.isfile(file_path):
                return {
                    'success': False,
                    'error': 'File does not exist or is not accessible'
                }

            # Get file info
            file_size_mb = get_file_size_mb(file_path)
            file_name = os.path.basename(file_path)

            self.logger.info(f"Processing {file_name} ({file_size_mb:.2f} MB)")

            # Try to get video metadata (validates it's a real video)
            video_info = get_video_info(file_path)
            if not video_info or video_info.get('duration', 0) == 0:
                return {
                    'success': False,
                    'error': 'Invalid video file or unable to read metadata'
                }

            # Create video record in database (status=INGESTED)
            video = db_ops.create_video(
                file_path=file_path,
                user_id=user_id,
                watch_directory_id=watch_directory_id,
                title=file_name,
                source_type='local',
                status='ingested'
            )

            self.logger.info(f"Created video record: video_id={video.id}")

            # Determine user's base path from watch directory
            watch_dir_path = Path(file_path).parent
            user_base_path = watch_dir_path.parent  # Go up one level from incoming/

            # Create processed directory for this video
            processed_dir = user_base_path / "processed" / str(video.id)
            processed_dir.mkdir(parents=True, exist_ok=True)

            # Move file to processed directory
            new_path = processed_dir / file_name
            if move_file(file_path, str(new_path)):
                # Update file path in database
                video.file_path = str(new_path)
                db_ops.session.commit()

                self.logger.info(f"Moved file to: {new_path}")

                # Log this step
                db_ops.log_step(
                    video_id=video.id,
                    step='ingest',
                    status='ok',
                    message=f'File ingested: {file_name} ({file_size_mb:.2f} MB)'
                )

                # Create pipeline context
                context = PipelineContext(
                    video_id=video.id,
                    user_id=user_id,
                    base_path=user_base_path,
                    video_path=str(new_path),
                    watch_directory_id=watch_directory_id,
                    metadata={
                        'file_name': file_name,
                        'file_size_mb': file_size_mb,
                        'duration': video_info.get('duration'),
                        'width': video_info.get('width'),
                        'height': video_info.get('height'),
                    }
                )

                # Ensure directories exist
                context.ensure_directories()

                return {
                    'success': True,
                    'video_id': video.id,
                    'processed_path': str(new_path),
                    'context': context
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to move file to processed directory'
                }

        except Exception as e:
            self.logger.error(f"Error processing file: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def start_watching(self, db_ops, orchestrator=None) -> None:
        """
        Start monitoring all active watch directories.

        Args:
            db_ops: Database operations handler
            orchestrator: Optional pipeline orchestrator to trigger processing
        """
        # Get all active watch directories
        watch_dirs = db_ops.get_active_watch_directories(validate_exists=True)

        if not watch_dirs:
            raise ValueError("No active watch directories found")

        # Create observer
        self.observer = Observer()
        self.handlers = []

        # Set up handler for each watch directory
        for watch_dir in watch_dirs:
            handler = VideoFileHandler(
                agent=self,
                watch_directory_id=watch_dir.id,
                user_id=watch_dir.user_id,
                db_ops=db_ops,
                orchestrator=orchestrator
            )

            self.observer.schedule(
                handler,
                watch_dir.directory_path,
                recursive=False
            )

            self.handlers.append(handler)
            self.logger.info(f"Watching: {watch_dir.directory_path} (user: {watch_dir.user_id})")

        # Start observer
        self.observer.start()

    def stop_watching(self) -> None:
        """Stop monitoring directories."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.logger.info("File watcher stopped")
