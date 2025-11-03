"""
Text Scoring Agent (Gemma Local)

Role: Identify speech-based clip candidates from the transcript
Input: Transcript from database
Output: Candidate segments + text_score

Key responsibilities:
- Semantic segmentation based on meaning boundaries
- Identify topic shifts and emotional intensity
- Generate initial clip candidates quickly
- Assign relevance scores to each segment

Notes:
- Fast and cheap - runs first in the pipeline
- Produces many potential clips for further evaluation
"""

import subprocess
import json
import time
from typing import Dict, Any, List
from .base_agent import BaseAgent
from ..database.operations import DatabaseOperations
from ..database.models import Segment, SegmentScore
from ..prompts.provider import prompt_provider


class TextScoringAgent(BaseAgent):
    """
    Performs semantic segmentation and text-based scoring using Gemma.
    Uses the prompt protocol system for structured prompting.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.model_name = config.get('gemma_model', 'gemma3:3b')
        self.device = config.get('device', 'cuda')
        self.ollama_timeout = config.get('ollama_timeout', 300)

    def _run_ollama(self, prompt: str) -> str:
        """
        Run Ollama with Gemma model using subprocess.

        Args:
            prompt: The formatted prompt text

        Returns:
            Model output as string
        """
        cmd = ['ollama', 'run', self.model_name, prompt]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.ollama_timeout,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ollama command failed: {e.stderr}")
            raise
        except subprocess.TimeoutExpired:
            self.logger.error(f"Ollama command timed out after {self.ollama_timeout}s")
            raise

    def _format_transcript(self, transcript_segments: List[Dict[str, Any]]) -> str:
        """
        Format transcript segments into a readable text string with timestamps.

        Args:
            transcript_segments: List of {start_time, end_time, text}

        Returns:
            Formatted transcript string
        """
        lines = []
        for seg in transcript_segments:
            timestamp = f"[{seg['start_time']:.2f}s - {seg['end_time']:.2f}s]"
            lines.append(f"{timestamp} {seg['text']}")

        return "\n".join(lines)

    def _save_segments_to_db(
        self,
        video_id: int,
        segments: List[Dict[str, Any]],
        db_ops: DatabaseOperations
    ) -> int:
        """
        Save identified segments to database.

        Args:
            video_id: Video identifier
            segments: List of segment data from prompt output
            db_ops: Database operations instance

        Returns:
            Number of segments saved
        """
        segment_records = []

        for seg_data in segments:
            # Create segment record
            segment = Segment(
                video_id=video_id,
                start_time=seg_data['start_time'],
                end_time=seg_data['end_time'],
                source='asr'  # Text-based segmentation from ASR transcript
            )
            db_ops.session.add(segment)
            db_ops.session.flush()  # Get segment ID

            # Create associated score record
            score = SegmentScore(
                segment_id=segment.id,
                text_score=seg_data['score'],
                combined_score=seg_data['score']  # Initially just text score
            )
            db_ops.session.add(score)

            segment_records.append({
                'segment_id': segment.id,
                'start_time': seg_data['start_time'],
                'end_time': seg_data['end_time'],
                'text_score': seg_data['score'],
                'reason': seg_data['reason']
            })

        db_ops.session.commit()
        self.logger.info(f"Saved {len(segment_records)} segments to database")

        return len(segment_records)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Segment transcript and score segments using Gemma + prompt protocol.

        Args:
            context:
                - video_id: Video identifier
                - user_id: User identifier
                - base_path: User's base directory

        Returns:
            - success: True if segmentation completed
            - segments: List of {start_time, end_time, text_score, reason}
            - segment_count: Number of segments identified
        """
        self.log_start(context)
        start_time = time.time()

        try:
            # Validate context
            self.validate_context(context, ['video_id', 'user_id'])

            video_id = context['video_id']

            # Create database operations instance
            db_ops = DatabaseOperations()

            # Load transcript from database
            transcript_segments = db_ops.get_transcript_segments(video_id)
            if not transcript_segments:
                raise ValueError(f"No transcript found for video_id={video_id}")

            self.logger.info(f"Loaded {len(transcript_segments)} transcript segments")

            # Format transcript for prompt
            transcript_text = self._format_transcript(transcript_segments)

            # Load prompt from protocol system
            prompt_obj = prompt_provider.get('text_scoring', version=1)

            # Format prompt with transcript
            formatted_prompt = prompt_obj.format(transcript_text=transcript_text)

            self.logger.info("Running Gemma model for text scoring...")
            # Run model
            model_output = self._run_ollama(formatted_prompt)

            self.logger.debug(f"Model output: {model_output}")

            # Parse output using protocol validation
            parsed_output = prompt_obj.parse_output(model_output)

            segments_data = parsed_output['segments']
            self.logger.info(f"Identified {len(segments_data)} clip candidates")

            # Save segments to database
            segment_count = self._save_segments_to_db(video_id, segments_data, db_ops)

            # Update video status to 'segmented'
            video = db_ops.get_video(video_id)
            video.status = 'segmented'
            db_ops.session.commit()

            # Log success
            db_ops.log_processing_step(
                video_id=video_id,
                step='text_scoring',
                status='ok',
                message=f"Identified {segment_count} clip candidates"
            )

            duration = time.time() - start_time
            self.log_complete(context, duration)

            return {
                'success': True,
                'segments': segments_data,
                'segment_count': segment_count,
                'duration': duration
            }

        except Exception as e:
            self.log_error(context, e)

            # Log failure to database
            try:
                db_ops = DatabaseOperations()
                db_ops.log_processing_step(
                    video_id=context.get('video_id'),
                    step='text_scoring',
                    status='fail',
                    message=str(e)
                )
            except:
                pass  # Don't fail on logging failure

            return {
                'success': False,
                'error': str(e),
                'errors': [str(e)]
            }
