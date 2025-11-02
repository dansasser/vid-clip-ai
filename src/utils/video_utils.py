"""
Video Utilities - Common video processing helpers.

Provides:
- Video metadata extraction
- Frame extraction
- Duration calculation
- FFmpeg command builders
"""

from typing import Tuple, Optional
import subprocess
import json


def get_video_info(video_path: str) -> dict:
    """
    Extract video metadata using ffprobe.

    Args:
        video_path: Path to video file

    Returns:
        Dictionary with duration, width, height, fps, etc.
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)

        # Extract video stream info
        video_stream = next(
            (s for s in data.get('streams', []) if s['codec_type'] == 'video'),
            None
        )

        if video_stream:
            return {
                'duration': float(data['format'].get('duration', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                'codec': video_stream.get('codec_name', ''),
                'bitrate': int(data['format'].get('bit_rate', 0))
            }
        else:
            return {}

    except Exception as e:
        print(f"Error getting video info: {e}")
        return {}


def get_video_duration(video_path: str) -> float:
    """
    Get video duration in seconds.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds
    """
    info = get_video_info(video_path)
    return info.get('duration', 0.0)


def get_video_resolution(video_path: str) -> Tuple[int, int]:
    """
    Get video resolution.

    Args:
        video_path: Path to video file

    Returns:
        Tuple of (width, height)
    """
    info = get_video_info(video_path)
    return (info.get('width', 0), info.get('height', 0))


def extract_frame_at_time(video_path: str, time_seconds: float,
                          output_path: str) -> bool:
    """
    Extract a single frame at specified time.

    Args:
        video_path: Path to video file
        time_seconds: Time in seconds
        output_path: Output image path

    Returns:
        True if successful
    """
    try:
        cmd = [
            'ffmpeg',
            '-ss', str(time_seconds),
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            output_path,
            '-y'
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error extracting frame: {e}")
        return False


def is_vertical_video(video_path: str) -> bool:
    """
    Check if video is vertical (height > width).

    Args:
        video_path: Path to video file

    Returns:
        True if vertical
    """
    width, height = get_video_resolution(video_path)
    return height > width
