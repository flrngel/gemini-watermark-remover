#!/usr/bin/env python3
"""
Watermark detection test framework.
Detects Gemini sparkle and Veo text watermarks in video frames.
"""

import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image


def extract_frames(video_path: str, output_dir: str) -> int:
    """Extract all frames from video."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        f"{output_dir}/frame_%03d.png"
    ], capture_output=True)
    return len(list(Path(output_dir).glob("frame_*.png")))


def detect_veo_watermark(frame: np.ndarray, threshold: float = 0.3) -> tuple[bool, float]:
    """
    Detect Veo text watermark in bottom-right corner.
    Returns (detected, confidence).
    """
    h, w = frame.shape[:2]

    # Veo region (bottom-right)
    vx, vy, vw, vh = w - 118, h - 64, 100, 45
    if vx < 0 or vy < 0:
        return False, 0.0

    region = frame[vy:vy+vh, vx:vx+vw]
    gray = np.mean(region, axis=2)

    # Veo text appears as lighter pixels on the background
    background_mean = np.percentile(gray, 25)
    bright_pixels = gray > background_mean + 30
    bright_ratio = bright_pixels.sum() / gray.size

    # Key indicator: Veo text creates strong horizontal row variance
    # Natural content has much lower row variance
    row_variance = np.var(gray.mean(axis=1))

    # Veo text has row_variance > 50 typically (original: ~160-230)
    # Focus on row variance as primary indicator
    # After good removal, row_variance drops to <10
    # Partial removal leaves 20-50
    if row_variance < 30:
        # Low horizontal variance - likely clean or acceptable
        confidence = 0.0
    else:
        # Has text-like patterns - weight row variance heavily
        confidence = min(1.0, (row_variance - 20) / 80 + bright_ratio * 0.3)

    detected = confidence > threshold

    return detected, confidence


def detect_gemini_watermark(frame: np.ndarray, threshold: float = 0.5) -> tuple[bool, float]:
    """
    Detect Gemini sparkle watermark in bottom-right corner.
    Returns (detected, confidence).
    """
    h, w = frame.shape[:2]

    # Gemini region (bottom-right, above Veo)
    is_large = w > 1024 or h > 1024
    size = 96 if is_large else 48
    margin = 64 if is_large else 32
    gx = w - margin - size
    gy = h - margin - size

    if gx < 0 or gy < 0:
        return False, 0.0

    region = frame[gy:gy+size, gx:gx+size]
    gray = np.mean(region, axis=2)

    # Gemini sparkle is a 4-pointed star, creates radial bright pattern
    center = size // 2

    # Check for bright center area (sparkle center)
    center_region = gray[center-5:center+5, center-5:center+5]
    edge_region = np.concatenate([gray[0:5, :].flatten(), gray[-5:, :].flatten()])

    center_brightness = center_region.mean()
    edge_brightness = edge_region.mean()

    brightness_diff = center_brightness - edge_brightness

    # Gemini sparkle creates ~20-50 brightness difference when present
    # Natural content rarely has >15 difference
    # Use higher threshold to avoid false positives
    confidence = min(1.0, max(0, brightness_diff - 10) / 25)
    detected = confidence > threshold

    return detected, confidence


def detect_rectangle_artifact(frame: np.ndarray) -> tuple[bool, float]:
    """
    Detect visible rectangle artifact from bad watermark removal.
    Returns (detected, confidence).
    """
    h, w = frame.shape[:2]

    # Check Veo region for sharp rectangular edges
    vx, vy, vw, vh = w - 118, h - 64, 100, 45
    if vx < 0 or vy < 0:
        return False, 0.0

    region = frame[vy:vy+vh, vx:vx+vw]
    gray = np.mean(region, axis=2)

    # Get surrounding context
    left_context = frame[vy:vy+vh, max(0, vx-20):vx]

    if left_context.size == 0:
        return False, 0.0

    left_gray = np.mean(left_context, axis=2)

    # Check for sharp edge at left boundary
    region_left_edge = gray[:, 0:5].mean()
    context_right_edge = left_gray[:, -5:].mean() if left_gray.shape[1] >= 5 else left_gray.mean()

    edge_diff = abs(region_left_edge - context_right_edge)

    # Also check for overall brightness mismatch
    region_mean = gray.mean()
    context_mean = left_gray.mean()
    mismatch = abs(region_mean - context_mean)

    # Rectangle artifact has sharp edges AND brightness mismatch
    confidence = min(1.0, (edge_diff / 30) * (mismatch / 20))
    detected = edge_diff > 15 and mismatch > 10

    return detected, confidence


def analyze_video(video_path: str, sample_interval: int = 6) -> dict:
    """
    Analyze video for watermarks and artifacts.
    Returns analysis results.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        num_frames = extract_frames(video_path, tmpdir)

        results = {
            "total_frames": num_frames,
            "veo_detected": [],
            "gemini_detected": [],
            "artifacts_detected": [],
            "clean_frames": [],
        }

        for i in range(1, num_frames + 1, sample_interval):
            frame_path = Path(tmpdir) / f"frame_{i:03d}.png"
            if not frame_path.exists():
                continue

            frame = np.array(Image.open(frame_path).convert("RGB"))

            veo_detected, veo_conf = detect_veo_watermark(frame)
            gemini_detected, gemini_conf = detect_gemini_watermark(frame)
            artifact_detected, artifact_conf = detect_rectangle_artifact(frame)

            if veo_detected:
                results["veo_detected"].append((i, veo_conf))
            if gemini_detected:
                results["gemini_detected"].append((i, gemini_conf))
            if artifact_detected:
                results["artifacts_detected"].append((i, artifact_conf))
            if not veo_detected and not gemini_detected and not artifact_detected:
                results["clean_frames"].append(i)

        return results


def print_report(results: dict, video_name: str = "video"):
    """Print analysis report."""
    print(f"\n{'='*60}")
    print(f"WATERMARK ANALYSIS REPORT: {video_name}")
    print(f"{'='*60}")
    print(f"Total frames: {results['total_frames']}")
    print(f"\nVeo watermark detected in {len(results['veo_detected'])} frames:")
    for frame, conf in results['veo_detected'][:10]:
        print(f"  Frame {frame}: confidence={conf:.2f}")
    if len(results['veo_detected']) > 10:
        print(f"  ... and {len(results['veo_detected']) - 10} more")

    print(f"\nGemini watermark detected in {len(results['gemini_detected'])} frames:")
    for frame, conf in results['gemini_detected'][:10]:
        print(f"  Frame {frame}: confidence={conf:.2f}")
    if len(results['gemini_detected']) > 10:
        print(f"  ... and {len(results['gemini_detected']) - 10} more")

    print(f"\nRectangle artifacts detected in {len(results['artifacts_detected'])} frames:")
    for frame, conf in results['artifacts_detected'][:10]:
        print(f"  Frame {frame}: confidence={conf:.2f}")

    print(f"\nClean frames: {len(results['clean_frames'])}")

    # Summary
    total_sampled = len(results['veo_detected']) + len(results['gemini_detected']) + \
                    len(results['artifacts_detected']) + len(results['clean_frames'])
    clean_pct = len(results['clean_frames']) / total_sampled * 100 if total_sampled > 0 else 0
    print(f"\n{'='*60}")
    print(f"SUMMARY: {clean_pct:.1f}% clean frames")
    if results['veo_detected']:
        print(f"  - Veo watermark needs removal")
    if results['gemini_detected']:
        print(f"  - Gemini watermark needs removal")
    if results['artifacts_detected']:
        print(f"  - Rectangle artifacts need fixing")
    print(f"{'='*60}\n")

    return clean_pct == 100


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_watermark_detection.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]
    results = analyze_video(video_path, sample_interval=6)
    success = print_report(results, Path(video_path).name)
    sys.exit(0 if success else 1)
