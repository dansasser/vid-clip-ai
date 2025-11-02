"""
Pipeline Orchestrator - Coordinates agent execution and state flow.

Responsibilities:
- Execute agents in correct order
- Manage state transitions
- Handle errors and retries
- Coordinate parallel operations
- Update database with progress
"""

from typing import Dict, Any, Optional
from .context import PipelineContext
from .state_machine import VideoState, StateMachine
from ..database.operations import DatabaseOperations
from ..agents.transcription import TranscriptionAgent
from ..agents.text_scoring import TextScoringAgent
from ..agents.vision_scoring import VisionScoringAgent
from ..agents.micro_emphasis import MicroEmphasisAgent
from ..agents.quality_assurance import QualityAssuranceAgent
from ..agents.scoring_ranking import ScoringRankingAgent
from ..agents.rendering import RenderingAgent
import logging


class PipelineOrchestrator:
    """
    Coordinates the execution of all agents through the pipeline.

    Manages state transitions, error handling, and database updates.
    """

    def __init__(self, db_ops: DatabaseOperations, config: Dict[str, Any]):
        """
        Initialize orchestrator with database connection and configuration.

        Args:
            db_ops: Database operations handler
            config: Global configuration dictionary
        """
        self.db_ops = db_ops
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Initialize agents
        self.agents = {
            'transcription': TranscriptionAgent(config.get('transcription')),
            'text_scoring': TextScoringAgent(config.get('text_scoring')),
            'vision_scoring': VisionScoringAgent(config.get('vision_scoring')),
            'micro_emphasis': MicroEmphasisAgent(config.get('micro_emphasis')),
            'quality_assurance': QualityAssuranceAgent(config.get('quality_assurance')),
            'scoring_ranking': ScoringRankingAgent(config.get('scoring_ranking')),
            'rendering': RenderingAgent(config.get('rendering'))
        }

    def execute_pipeline(self, context: PipelineContext) -> bool:
        """
        Execute the full pipeline for a video.

        Args:
            context: Pipeline execution context

        Returns:
            True if pipeline completed successfully
        """
        try:
            self.logger.info(
                f"Starting pipeline for video_id={context.video_id}, "
                f"user_id={context.user_id}"
            )

            # Ensure directories exist
            context.ensure_directories()

            # Execute pipeline stages in order
            if not self._run_transcription(context):
                return False

            if not self._run_text_scoring(context):
                return False

            if not self._run_vision_scoring(context):
                return False

            if not self._run_micro_emphasis(context):
                return False

            if not self._run_quality_assurance(context):
                return False

            if not self._run_scoring_ranking(context):
                return False

            if not self._run_rendering(context):
                return False

            self.logger.info(f"Pipeline completed for video_id={context.video_id}")
            return True

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            self._update_state(context.video_id, VideoState.ERROR)
            self.db_ops.log_step(
                context.video_id,
                step='pipeline',
                status='fail',
                message=str(e)
            )
            return False

    def _run_transcription(self, context: PipelineContext) -> bool:
        """Execute transcription stage."""
        self.logger.info(f"Running transcription for video_id={context.video_id}")

        result = self.agents['transcription'].execute(context.to_dict())

        if result.get('success'):
            # Store transcript in database
            self.db_ops.add_transcript_segments(
                context.video_id,
                result['transcript_segments']
            )
            self._update_state(context.video_id, VideoState.TRANSCRIBED)
            self.db_ops.log_step(context.video_id, 'transcribe', 'ok')
            return True
        else:
            self.db_ops.log_step(
                context.video_id,
                'transcribe',
                'fail',
                result.get('errors')
            )
            return False

    def _run_text_scoring(self, context: PipelineContext) -> bool:
        """Execute text scoring and segmentation stage."""
        # Implementation placeholder
        pass

    def _run_vision_scoring(self, context: PipelineContext) -> bool:
        """Execute vision scoring stage."""
        # Implementation placeholder
        pass

    def _run_micro_emphasis(self, context: PipelineContext) -> bool:
        """Execute micro-emphasis analysis stage."""
        # Implementation placeholder
        pass

    def _run_quality_assurance(self, context: PipelineContext) -> bool:
        """Execute cloud-based quality assurance stage."""
        # Implementation placeholder
        pass

    def _run_scoring_ranking(self, context: PipelineContext) -> bool:
        """Execute final scoring and ranking stage."""
        # Implementation placeholder
        pass

    def _run_rendering(self, context: PipelineContext) -> bool:
        """Execute clip rendering stage."""
        # Implementation placeholder
        pass

    def _update_state(self, video_id: int, new_state: VideoState) -> None:
        """
        Update video state in database with validation.

        Args:
            video_id: Video identifier
            new_state: New state to transition to
        """
        video = self.db_ops.get_video(video_id)
        if video:
            try:
                StateMachine.validate_transition(video.status, new_state.value)
                self.db_ops.update_video_status(video_id, new_state.value)
            except ValueError as e:
                self.logger.error(f"Invalid state transition: {e}")
                raise
