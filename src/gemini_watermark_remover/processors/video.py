import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

import ffmpeg
import numpy as np
from PIL import Image

from ..core import BITRATE_720P, BITRATE_1080P, BITRATE_4K, BITRATE_HIGHER
from ..core import PIXELS_720P, PIXELS_1080P, PIXELS_4K
from ..core.alpha_map import get_alpha_map
from ..core.blend import remove_watermark
from ..core.position import calculate_veo_watermark_position, calculate_watermark_position

SUPPORTED_VIDEO_FORMATS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}


def is_supported_video(path: Path) -> bool:
    """Check if file is a supported video format."""
    return path.suffix.lower() in SUPPORTED_VIDEO_FORMATS


def get_video_info(input_path: Path) -> dict:
    """Get video metadata using ffprobe."""
    probe = ffmpeg.probe(str(input_path))
    video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")

    # Check for audio stream
    audio_stream = next(
        (s for s in probe["streams"] if s["codec_type"] == "audio"),
        None,
    )

    width = int(video_stream["width"])
    height = int(video_stream["height"])

    # Parse frame rate (can be "30/1" or "29.97")
    fps_str = video_stream.get("r_frame_rate", "30/1")
    if "/" in fps_str:
        num, den = map(int, fps_str.split("/"))
        fps = num / den if den != 0 else 30.0
    else:
        fps = float(fps_str)

    duration = float(probe["format"].get("duration", 0))
    total_frames = int(duration * fps) if duration > 0 else 0

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "duration": duration,
        "total_frames": total_frames,
        "has_audio": audio_stream is not None,
    }


def calculate_bitrate(width: int, height: int) -> int:
    """Calculate optimal bitrate based on resolution."""
    pixels = width * height

    if pixels <= PIXELS_720P:
        return BITRATE_720P
    elif pixels <= PIXELS_1080P:
        return BITRATE_1080P
    elif pixels <= PIXELS_4K:
        return BITRATE_4K
    else:
        return BITRATE_HIGHER


def process_video(
    input_path: Path,
    output_path: Path | None = None,
    suffix: str = "_cleaned",
    progress_callback: Callable[[int, int], None] | None = None,
) -> Path:
    """
    Process video to remove ALL watermarks (Gemini + Veo).

    Combines two watermark removal techniques:
    1. Gemini: Frame-by-frame alpha blending reversal
    2. Veo: ffmpeg delogo filter applied during reassembly

    Args:
        input_path: Path to input video
        output_path: Optional explicit output path
        suffix: Suffix for auto-generated output filename
        progress_callback: Optional callback(current_frame, total_frames)

    Returns:
        Path to output MP4 file
    """
    # Determine output path (always MP4)
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}{suffix}.mp4"

    # Ensure output has .mp4 extension
    if output_path.suffix.lower() != ".mp4":
        output_path = output_path.with_suffix(".mp4")

    # Get video metadata
    info = get_video_info(input_path)
    width, height = info["width"], info["height"]
    fps = info["fps"]
    has_audio = info["has_audio"]

    # Calculate Gemini watermark position and get alpha map
    gemini_pos = calculate_watermark_position(width, height)
    alpha_map = get_alpha_map(gemini_pos.size)

    # Calculate Veo watermark position
    veo_pos = calculate_veo_watermark_position(width, height)

    # Calculate bitrate
    bitrate = calculate_bitrate(width, height)

    # Create temporary directory for frame processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        frames_dir = temp_path / "frames"
        frames_dir.mkdir()

        # Extract frames using ffmpeg
        extract_cmd = (
            ffmpeg.input(str(input_path))
            .output(str(frames_dir / "frame_%06d.png"), format="image2")
            .overwrite_output()
            .compile()
        )
        subprocess.run(extract_cmd, stdin=subprocess.DEVNULL,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Process each frame for Gemini watermark removal
        frame_files = sorted(frames_dir.glob("frame_*.png"))
        processed_dir = temp_path / "processed"
        processed_dir.mkdir()

        for i, frame_file in enumerate(frame_files):
            # Load frame
            with Image.open(frame_file) as img:
                frame_array = np.array(img.convert("RGB"), dtype=np.uint8)

            # Remove Gemini watermark (alpha blending)
            result_array = remove_watermark(frame_array, alpha_map, gemini_pos)

            # Save processed frame
            result_image = Image.fromarray(result_array)
            result_image.save(processed_dir / frame_file.name)

            # Report progress
            if progress_callback:
                progress_callback(i + 1, len(frame_files))

        # Reassemble video with ffmpeg, applying Veo delogo filter
        video_input = ffmpeg.input(
            str(processed_dir / "frame_%06d.png"),
            framerate=fps,
        )

        # Apply Veo delogo filter during reassembly
        video_stream = video_input.filter(
            "delogo",
            x=veo_pos.x,
            y=veo_pos.y,
            w=veo_pos.width,
            h=veo_pos.height,
        )

        if has_audio:
            # Extract and merge audio from original
            audio_input = ffmpeg.input(str(input_path)).audio
            reassemble_cmd = (
                ffmpeg.output(
                    video_stream,
                    audio_input,
                    str(output_path),
                    vcodec="libx264",
                    preset="medium",
                    crf=18,
                    video_bitrate=bitrate,
                    pix_fmt="yuv420p",
                    acodec="aac",
                    audio_bitrate="192k",
                )
                .overwrite_output()
                .compile()
            )
        else:
            reassemble_cmd = (
                ffmpeg.output(
                    video_stream,
                    str(output_path),
                    vcodec="libx264",
                    preset="medium",
                    crf=18,
                    video_bitrate=bitrate,
                    pix_fmt="yuv420p",
                )
                .overwrite_output()
                .compile()
            )

        subprocess.run(reassemble_cmd, stdin=subprocess.DEVNULL,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    return output_path
