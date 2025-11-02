"""
Pipeline Context - User-scoped execution context propagation.

The context object carries all necessary information through the pipeline:
- User identification
- Video identification
- File paths
- State information
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineContext:
    """
    Execution context for pipeline operations.

    All agents receive this context and can access user-scoped
    information without coupling to specific implementations.
    """

    video_id: int
    user_id: str
    base_path: Path
    video_path: str
    watch_directory_id: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for agent execution."""
        return {
            'video_id': self.video_id,
            'user_id': self.user_id,
            'base_path': str(self.base_path),
            'video_path': self.video_path,
            'watch_directory_id': self.watch_directory_id,
            **self.metadata
        }

    @property
    def processed_dir(self) -> Path:
        """Get processed directory for this video."""
        return self.base_path / "processed" / str(self.video_id)

    @property
    def clips_dir(self) -> Path:
        """Get clips output directory."""
        return self.processed_dir / "clips"

    @property
    def temp_dir(self) -> Path:
        """Get temporary files directory."""
        return self.processed_dir / "temp"

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.clips_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
