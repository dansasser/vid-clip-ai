"""
Vision Scoring Agent (Qwen2-VL via Ollama)

Role: Evaluate visual salience of each candidate segment
Input: Video segment reference (timestamps) + low-res frame samples
Output: vision_score

Key responsibilities:
- Sample 3-7 frames per segment
- Evaluate facial expressions, gestures, scene changes
- Assess visual storytelling strength
- Assign vision_score to each segment

Notes:
- Enhances segments where visuals matter
- Uses Qwen2-VL model via 'ollama run' command
"""

import os
import tempfile
import subprocess
import time
from typing import Dict, Any, List
from pathlib import Path
import cv2
from .base_agent import BaseAgent
from ..database.operations import DatabaseOperations
from ..prompts.provider import prompt_provider


class VisionScoringAgent(BaseAgent):
    """
    Scores visual salience using Qwen2-VL model via ollama run command.
    Uses the prompt protocol system for structured prompting.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.model_name = config.get('vlm_model', 'qwen2.5vl:3b')
        self.ollama_timeout = config.get('ollama_timeout', 300)
        self.frames_per_segment = config.get('frames_per_segment', 5)

    def _extract_frames(self, video_path: str, start_time: float,
                       end_time: float, output_dir: str) -> List[str]:
        """
        Extract evenly spaced frames from a segment using FFmpeg.

        Args:
            video_path: Path to video file
            start_time: Segment start time in seconds
            end_time: Segment end time in seconds
            output_dir: Directory to save frames

        Returns:
            List of paths to extracted frame images
        """
        duration = end_time - start_time
        frame_paths = []

        # Calculate frame extraction times
        if duration <= 0:
            self.logger.warning(f"Invalid segment duration: {duration}s")
            return []

        # Extract frames evenly spaced across the segment
        for i in range(self.frames_per_segment):
            # Calculate timestamp for this frame
            offset = (i / (self.frames_per_segment - 1)) * duration if self.frames_per_segment > 1 else 0
            timestamp = start_time + offset

            # Output path for frame
            frame_path = os.path.join(output_dir, f"frame_{i:03d}.jpg")

            # FFmpeg command to extract single frame
            cmd = [
                'ffmpeg', '-ss', str(timestamp),
                '-i', video_path,
                '-frames:v', '1',
                '-q:v', '2',  # High quality
                '-y',  # Overwrite
                frame_path
            ]

            try:
                subprocess.run(cmd, capture_output=True, check=True, timeout=30)
                if os.path.exists(frame_path):
                    frame_paths.append(frame_path)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                self.logger.error(f"Failed to extract frame at {timestamp}s: {e}")

        self.logger.info(f"Extracted {len(frame_paths)} frames from segment")
        return frame_paths

    def _format_frame_descriptions(self, frame_paths: List[str]) -> str:
        """
        Format frame paths for inclusion in prompt.

        Args:
            frame_paths: List of paths to frame images

        Returns:
            Formatted string describing frames
        """
        descriptions = []
        for i, path in enumerate(frame_paths, 1):
            descriptions.append(f"Frame {i}: {path}")
        return "\n".join(descriptions)

    def _get_transcript_text_for_segment(
        self,
        video_id: int,
        start_time: float,
        end_time: float,
        db_ops: DatabaseOperations
    ) -> str:
        """
        Get transcript text overlapping with segment timeframe.

        Args:
            video_id: Video identifier
            start_time: Segment start time
            end_time: Segment end time
            db_ops: Database operations instance

        Returns:
            Concatenated transcript text for segment
        """
        transcript_segments = db_ops.get_transcript_segments(video_id)

        # Filter segments that overlap with our timeframe
        overlapping = [
            seg for seg in transcript_segments
            if seg['start_time'] < end_time and seg['end_time'] > start_time
        ]

        return " ".join(seg['text'] for seg in overlapping)

    def _run_ollama(self, prompt: str, image_paths: List[str] = None) -> str:
        """
        Run ollama command with prompt and optional images.

        Note: Ollama VLM models can process images passed as file paths.
        The images are referenced in the prompt or automatically detected.

        Args:
            prompt: Text prompt for the model
            image_paths: Optional list of image file paths

        Returns:
            Model response text
        """
        # For vision models, ollama expects images to be passed inline
        # We'll construct the command to include image references
        cmd = ['ollama', 'run', self.model_name, prompt]

        # If images provided, we can append them as arguments
        # (Ollama's CLI supports this for vision models)
        if image_paths:
            cmd.extend(image_paths)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.ollama_timeout,
                check=True
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            self.logger.error(f"Ollama command timed out after {self.ollama_timeout}s")
            raise
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Ollama command failed: {e.stderr}")
            raise

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Score visual content of all segments using prompt protocol.

        Args:
            context:
                - video_id: Video identifier
                - video_path: Path to video file
                - user_id: User identifier
                - base_path: User's base directory

        Returns:
            - success: True if scoring completed
            - vision_scores: Dict mapping segment_id to vision_score
            - segments_scored: Number of segments scored
        """
        self.log_start(context)
        start_time = time.time()

        try:
            # Validate context
            self.validate_context(context, ['video_id', 'video_path', 'user_id'])

            video_id = context['video_id']
            video_path = context['video_path']

            # Create database operations instance
            db_ops = DatabaseOperations()

            # Load segments that need vision scoring
            segments = db_ops.get_segments(video_id)
            if not segments:
                raise ValueError(f"No segments found for video_id={video_id}")

            self.logger.info(f"Scoring {len(segments)} segments for visual content")

            # Load vision scoring prompt
            prompt_obj = prompt_provider.get('vision_scoring', version=1)

            vision_scores = {}
            scored_count = 0

            # Create temp directory for frames
            with tempfile.TemporaryDirectory() as temp_dir:
                for segment in segments:
                    self.logger.info(
                        f"Scoring segment {segment.id}: "
                        f"{segment.start_time:.2f}s - {segment.end_time:.2f}s"
                    )

                    # Extract frames for this segment
                    frame_paths = self._extract_frames(
                        video_path,
                        segment.start_time,
                        segment.end_time,
                        temp_dir
                    )

                    if not frame_paths:
                        self.logger.warning(f"No frames extracted for segment {segment.id}, skipping")
                        continue

                    # Get transcript text for this segment
                    transcript_text = self._get_transcript_text_for_segment(
                        video_id,
                        segment.start_time,
                        segment.end_time,
                        db_ops
                    )

                    # Format frame descriptions
                    frame_descriptions = self._format_frame_descriptions(frame_paths)

                    # Format prompt
                    formatted_prompt = prompt_obj.format(
                        transcript_text=transcript_text,
                        frame_descriptions=frame_descriptions
                    )

                    # Run model with frames
                    self.logger.debug(f"Running VLM for segment {segment.id}")
                    model_output = self._run_ollama(formatted_prompt, frame_paths)

                    # Parse output using protocol
                    parsed_output = prompt_obj.parse_output(model_output)

                    vision_score = parsed_output['vision_score']
                    emotional_intensity = parsed_output.get('emotional_intensity', 'unknown')

                    self.logger.info(
                        f"Segment {segment.id} vision score: {vision_score:.2f}, "
                        f"intensity: {emotional_intensity}"
                    )

                    # Update segment score in database
                    if segment.scores:
                        segment.scores.vision_score = vision_score
                        # Update combined score (simple average for now)
                        text_score = segment.scores.text_score or 0
                        segment.scores.combined_score = (text_score + vision_score) / 2
                    else:
                        self.logger.warning(f"Segment {segment.id} has no score record, skipping")
                        continue

                    vision_scores[segment.id] = vision_score
                    scored_count += 1

                    # Clean up frames for this segment
                    for frame_path in frame_paths:
                        try:
                            os.unlink(frame_path)
                        except:
                            pass

            # Commit all score updates
            db_ops.session.commit()

            # Update video status to 'scored'
            video = db_ops.get_video(video_id)
            video.status = 'scored'
            db_ops.session.commit()

            # Log success
            db_ops.log_processing_step(
                video_id=video_id,
                step='vision_scoring',
                status='ok',
                message=f"Scored {scored_count} segments for visual content"
            )

            duration = time.time() - start_time
            self.log_complete(context, duration)

            return {
                'success': True,
                'vision_scores': vision_scores,
                'segments_scored': scored_count,
                'duration': duration
            }

        except Exception as e:
            self.log_error(context, e)

            # Log failure to database
            try:
                db_ops = DatabaseOperations()
                db_ops.log_processing_step(
                    video_id=context.get('video_id'),
                    step='vision_scoring',
                    status='fail',
                    message=str(e)
                )
            except:
                pass

            return {
                'success': False,
                'error': str(e),
                'errors': [str(e)]
            }
