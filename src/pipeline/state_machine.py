"""
State Machine - Video lifecycle state management.

States:
- INGESTED: Video detected and registered
- TRANSCRIBED: WhisperX transcript stored
- SEGMENTED: Gemma meaning-based clip boundaries computed
- SCORED: Clip candidates evaluated by all scoring agents
- READY: Ranked clip list available for export
- ARCHIVED: Video moved to long-term storage

State transitions are recorded in the database and validated
to ensure proper pipeline flow.
"""

from enum import Enum
from typing import Optional, List


class VideoState(Enum):
    """Valid states in the video processing lifecycle."""

    INGESTED = "ingested"
    TRANSCRIBED = "transcribed"
    SEGMENTED = "segmented"
    SCORED = "scored"
    READY = "ready"
    ARCHIVED = "archived"
    ERROR = "error"


class StateMachine:
    """
    Manages video lifecycle state transitions.

    Ensures transitions follow the correct order and validates
    that prerequisites are met before state changes.
    """

    # Valid state transitions
    TRANSITIONS = {
        VideoState.INGESTED: [VideoState.TRANSCRIBED, VideoState.ERROR],
        VideoState.TRANSCRIBED: [VideoState.SEGMENTED, VideoState.ERROR],
        VideoState.SEGMENTED: [VideoState.SCORED, VideoState.ERROR],
        VideoState.SCORED: [VideoState.READY, VideoState.ERROR],
        VideoState.READY: [VideoState.ARCHIVED, VideoState.ERROR],
        VideoState.ARCHIVED: [],
        VideoState.ERROR: []  # Terminal state
    }

    @classmethod
    def can_transition(cls, current: VideoState, next_state: VideoState) -> bool:
        """
        Check if transition from current to next state is valid.

        Args:
            current: Current state
            next_state: Desired next state

        Returns:
            True if transition is valid
        """
        return next_state in cls.TRANSITIONS.get(current, [])

    @classmethod
    def validate_transition(cls, current: str, next_state: str) -> None:
        """
        Validate and convert string states to enum.

        Args:
            current: Current state as string
            next_state: Desired next state as string

        Raises:
            ValueError: If transition is invalid
        """
        try:
            current_enum = VideoState(current)
            next_enum = VideoState(next_state)
        except ValueError as e:
            raise ValueError(f"Invalid state: {e}")

        if not cls.can_transition(current_enum, next_enum):
            raise ValueError(
                f"Invalid transition from {current} to {next_state}"
            )

    @classmethod
    def get_next_states(cls, current: VideoState) -> List[VideoState]:
        """Get list of valid next states from current state."""
        return cls.TRANSITIONS.get(current, [])

    @classmethod
    def get_pipeline_order(cls) -> List[VideoState]:
        """Get the normal pipeline execution order."""
        return [
            VideoState.INGESTED,
            VideoState.TRANSCRIBED,
            VideoState.SEGMENTED,
            VideoState.SCORED,
            VideoState.READY
        ]
