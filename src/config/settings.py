"""
Global Settings - Application configuration.

Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Dict, Any


class Settings:
    """Global application settings."""

    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///vid_clip_ai.db')

    # Paths
    BASE_DATA_DIR: Path = Path(os.getenv('BASE_DATA_DIR', './data'))
    LOG_FILE: str = os.getenv('LOG_FILE', './logs/vid_clip_ai.log')

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # File Watcher
    SUPPORTED_VIDEO_FORMATS: list = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    WATCH_INTERVAL_SECONDS: int = int(os.getenv('WATCH_INTERVAL_SECONDS', '5'))

    # Models
    WHISPER_MODEL: str = os.getenv('WHISPER_MODEL', 'base')
    WHISPER_DEVICE: str = os.getenv('WHISPER_DEVICE', 'cuda')

    GEMMA_MODEL: str = os.getenv('GEMMA_MODEL', 'google/gemma-2-2b-it')
    GEMMA_DEVICE: str = os.getenv('GEMMA_DEVICE', 'cuda')

    # Ollama VLM models (used with 'ollama run <model>' command)
    LOCAL_VLM_MODEL: str = os.getenv('LOCAL_VLM_MODEL', 'qwen2.5vl:3b')
    CLOUD_VLM_MODEL: str = os.getenv('CLOUD_VLM_MODEL', 'qwen3-vl:235b-cloud')

    # Ollama options
    OLLAMA_TIMEOUT: int = int(os.getenv('OLLAMA_TIMEOUT', '300'))  # seconds

    # Scoring
    CONFIDENCE_THRESHOLD_LOW: float = float(os.getenv('CONFIDENCE_THRESHOLD_LOW', '0.40'))
    CONFIDENCE_THRESHOLD_HIGH: float = float(os.getenv('CONFIDENCE_THRESHOLD_HIGH', '0.65'))

    # Scoring weights
    SCORE_WEIGHT_TEXT: float = float(os.getenv('SCORE_WEIGHT_TEXT', '0.30'))
    SCORE_WEIGHT_VISION: float = float(os.getenv('SCORE_WEIGHT_VISION', '0.30'))
    SCORE_WEIGHT_AUDIO_EMPHASIS: float = float(os.getenv('SCORE_WEIGHT_AUDIO_EMPHASIS', '0.15'))
    SCORE_WEIGHT_FACIAL_EMPHASIS: float = float(os.getenv('SCORE_WEIGHT_FACIAL_EMPHASIS', '0.15'))
    SCORE_WEIGHT_CLOUD: float = float(os.getenv('SCORE_WEIGHT_CLOUD', '0.10'))

    # Export
    TOP_N_AUTO_EXPORT: int = int(os.getenv('TOP_N_AUTO_EXPORT', '3'))
    MAX_PARALLEL_EXPORTS: int = int(os.getenv('MAX_PARALLEL_EXPORTS', '2'))

    # Caption styling
    CAPTION_FONTSIZE: int = int(os.getenv('CAPTION_FONTSIZE', '32'))
    CAPTION_OUTLINE: int = int(os.getenv('CAPTION_OUTLINE', '2'))
    CAPTION_SHADOW: int = int(os.getenv('CAPTION_SHADOW', '1'))

    # FFmpeg
    VIDEO_CODEC: str = os.getenv('VIDEO_CODEC', 'libx264')
    AUDIO_CODEC: str = os.getenv('AUDIO_CODEC', 'aac')
    FFMPEG_PRESET: str = os.getenv('FFMPEG_PRESET', 'veryfast')

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith('_') and key.isupper()
        }

    @classmethod
    def get_agent_config(cls, agent_name: str) -> Dict[str, Any]:
        """Get configuration dictionary for a specific agent."""
        configs = {
            'file_watcher': {
                'supported_formats': cls.SUPPORTED_VIDEO_FORMATS,
                'watch_interval': cls.WATCH_INTERVAL_SECONDS
            },
            'transcription': {
                'whisper_model': cls.WHISPER_MODEL,
                'device': cls.WHISPER_DEVICE
            },
            'text_scoring': {
                'gemma_model': cls.GEMMA_MODEL,
                'device': cls.GEMMA_DEVICE
            },
            'vision_scoring': {
                'vlm_model': cls.LOCAL_VLM_MODEL,
                'ollama_timeout': cls.OLLAMA_TIMEOUT,
                'frames_per_segment': 5
            },
            'micro_emphasis': {
                'threshold_low': cls.CONFIDENCE_THRESHOLD_LOW,
                'threshold_high': cls.CONFIDENCE_THRESHOLD_HIGH
            },
            'quality_assurance': {
                'vlm_model': cls.CLOUD_VLM_MODEL,
                'ollama_timeout': cls.OLLAMA_TIMEOUT,
                'preview_duration': 2,
                'preview_resolution': '320p'
            },
            'scoring_ranking': {
                'weights': {
                    'text_score': cls.SCORE_WEIGHT_TEXT,
                    'vision_score': cls.SCORE_WEIGHT_VISION,
                    'audio_emphasis': cls.SCORE_WEIGHT_AUDIO_EMPHASIS,
                    'facial_emphasis': cls.SCORE_WEIGHT_FACIAL_EMPHASIS,
                    'cloud_score': cls.SCORE_WEIGHT_CLOUD
                },
                'top_n_auto_export': cls.TOP_N_AUTO_EXPORT
            },
            'rendering': {
                'caption_style': {
                    'fontsize': cls.CAPTION_FONTSIZE,
                    'outline': cls.CAPTION_OUTLINE,
                    'shadow': cls.CAPTION_SHADOW
                },
                'video_codec': cls.VIDEO_CODEC,
                'audio_codec': cls.AUDIO_CODEC,
                'preset': cls.FFMPEG_PRESET
            }
        }
        return configs.get(agent_name, {})


settings = Settings()
