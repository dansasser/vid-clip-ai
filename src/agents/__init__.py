"""
Agent modules - Each agent is responsible for a distinct part of the pipeline.

Available agents:
- FileWatcherAgent: Detects new videos in watched directories
- TranscriptionAgent: Converts audio to timestamped text (WhisperX)
- TextScoringAgent: Identifies speech-based clip candidates (Gemma)
- VisionScoringAgent: Evaluates visual salience (Qwen2-VL)
- MicroEmphasisAgent: Audio prosody and facial movement analysis
- QualityAssuranceAgent: Cloud-based re-evaluation for ambiguous clips (Qwen3-VL)
- ScoringRankingAgent: Combines scores and ranks clips
- RenderingAgent: Generates final clips with captions (FFmpeg)
"""

from .base_agent import BaseAgent

__all__ = ["BaseAgent"]
