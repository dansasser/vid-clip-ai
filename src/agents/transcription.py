"""
Audio Transcription Agent (WhisperX)

Role: Convert audio into timestamped text
Input: Raw video file
Output: Transcript lines (start_time, end_time, text)

Key responsibilities:
- Extract audio from video
- Use WhisperX for accurate timestamped transcription
- Store transcript segments in database
- Update video state to TRANSCRIBED

Critical: Timestamp accuracy is essential for all downstream tasks
"""

import os
import subprocess
import tempfile
from typing import Dict, Any, List
from pathlib import Path
import time

from .base_agent import BaseAgent
from ..database.operations import DatabaseOperations
from ..database.models import Transcript, ProcessingLog


class TranscriptionAgent(BaseAgent):
    """
    Transcribes video audio using WhisperX with word-level timestamps.
    """

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.model_name = config.get('whisper_model', 'base')
        self.device = config.get('device', 'cuda')
        self.whisperx_model = None
        self.whisperx_align_model = None

    def _load_whisperx(self):
        """Lazy load WhisperX models."""
        if self.whisperx_model is None:
            import whisperx
            self.logger.info(f"Loading WhisperX model: {self.model_name}")
            self.whisperx_model = whisperx.load_model(
                self.model_name,
                self.device,
                compute_type="float16" if self.device == "cuda" else "int8"
            )
            self.logger.info("WhisperX model loaded successfully")

    def _extract_audio(self, video_path: str, output_path: str) -> bool:
        """
        Extract audio from video using FFmpeg.

        Args:
            video_path: Path to input video file
            output_path: Path to output audio file (.wav)

        Returns:
            True if extraction succeeded, False otherwise
        """
        try:
            cmd = [
                'ffmpeg', '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '16000',  # 16kHz sample rate (WhisperX default)
                '-ac', '1',  # Mono
                '-y',  # Overwrite output file
                output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            self.logger.info(f"Audio extracted to {output_path}")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"FFmpeg audio extraction failed: {e.stderr}")
            return False

    def _transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using WhisperX.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary containing 'segments' with timestamped transcript data
        """
        import whisperx

        self._load_whisperx()

        self.logger.info("Starting transcription...")
        result = self.whisperx_model.transcribe(audio_path)

        # Align whisper output for word-level timestamps
        self.logger.info("Aligning transcript for word-level timestamps...")
        model_a, metadata = whisperx.load_align_model(
            language_code=result["language"],
            device=self.device
        )
        result = whisperx.align(
            result["segments"],
            model_a,
            metadata,
            audio_path,
            self.device
        )

        self.logger.info(f"Transcription complete: {len(result['segments'])} segments")
        return result

    def _save_transcript_to_db(
        self,
        video_id: int,
        segments: List[Dict[str, Any]],
        db_ops: DatabaseOperations
    ) -> int:
        """
        Save transcript segments to database.

        Args:
            video_id: Video identifier
            segments: List of transcript segments from WhisperX
            db_ops: Database operations instance

        Returns:
            Number of segments saved
        """
        transcript_records = []

        for segment in segments:
            transcript_records.append(Transcript(
                video_id=video_id,
                start_time=segment['start'],
                end_time=segment['end'],
                text=segment['text'].strip()
            ))

        # Bulk insert
        db_ops.session.bulk_save_objects(transcript_records)
        db_ops.session.commit()

        self.logger.info(f"Saved {len(transcript_records)} transcript segments to database")
        return len(transcript_records)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transcribe video audio.

        Args:
            context:
                - video_id: Video identifier
                - video_path: Path to video file
                - user_id: User identifier
                - base_path: User's base directory

        Returns:
            - success: True if transcription completed
            - transcript_segments: List of {start_time, end_time, text}
            - duration: Total video duration
            - segment_count: Number of transcript segments created
        """
        self.log_start(context)
        start_time = time.time()

        try:
            # Validate required context keys
            self.validate_context(context, ['video_id', 'video_path', 'user_id'])

            video_id = context['video_id']
            video_path = context['video_path']

            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")

            # Create database operations instance
            db_ops = DatabaseOperations()

            # Extract audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                audio_path = temp_audio.name

            self.logger.info(f"Extracting audio from {video_path}")
            if not self._extract_audio(video_path, audio_path):
                raise RuntimeError("Audio extraction failed")

            try:
                # Transcribe audio
                result = self._transcribe_audio(audio_path)

                # Save to database
                segment_count = self._save_transcript_to_db(
                    video_id,
                    result['segments'],
                    db_ops
                )

                # Update video status to 'transcribed'
                video = db_ops.get_video_by_id(video_id)
                video.status = 'transcribed'
                db_ops.session.commit()

                # Log success
                db_ops.log_processing_step(
                    video_id=video_id,
                    step='transcribe',
                    status='ok',
                    message=f"Transcribed {segment_count} segments"
                )

                duration = time.time() - start_time
                self.log_complete(context, duration)

                return {
                    'success': True,
                    'transcript_segments': result['segments'],
                    'segment_count': segment_count,
                    'duration': duration,
                    'language': result.get('language', 'unknown')
                }

            finally:
                # Clean up temporary audio file
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
                    self.logger.debug(f"Cleaned up temporary audio file: {audio_path}")

        except Exception as e:
            self.log_error(context, e)

            # Log failure to database if possible
            try:
                db_ops = DatabaseOperations()
                db_ops.log_processing_step(
                    video_id=context.get('video_id'),
                    step='transcribe',
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
