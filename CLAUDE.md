# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install dependencies
uv sync

# Run the CLI
uv run gwr process <file>
uv run gwr info

# Run with long form
uv run gemini-watermark-remover process <file>
```

## Architecture

Python CLI tool using `uv` for package management. Removes Gemini AI watermarks from images/videos using reverse alpha blending.

### Core Algorithm

```python
# Reverse Alpha Blending Formula
original = (watermarked - alpha * 255) / (1 - alpha)
```

Constants in `src/gemini_watermark_remover/core/__init__.py`:
- `ALPHA_THRESHOLD = 0.002` - Skip pixels with negligible alpha
- `MAX_ALPHA = 0.99` - Prevent division by near-zero
- `LOGO_VALUE = 255` - White watermark

### Module Structure

- **`core/blend.py`** - Vectorized numpy watermark removal
- **`core/alpha_map.py`** - Loads reference PNGs, extracts alpha as `max(R,G,B)/255`
- **`core/position.py`** - Calculates watermark position (48px for ≤1024px, 96px for larger)
- **`processors/image.py`** - Pillow-based single image processing
- **`processors/video.py`** - ffmpeg frame extraction, processing, reassembly with H.264
- **`cli.py`** - typer CLI with `process` and `info` commands

### Watermark Position Logic

```python
is_large = width > 1024 or height > 1024
size = 96 if is_large else 48
margin = 64 if is_large else 32
x, y = width - margin - size, height - margin - size
```

### Video Bitrate Tiers

- ≤720p: 8 Mbps
- 1080p: 15 Mbps
- 4K: 40 Mbps
- Higher: 60 Mbps

### Assets

Reference alpha maps bundled in `src/gemini_watermark_remover/assets/`:
- `bg_48.png` - 48x48 alpha map for small images
- `bg_96.png` - 96x96 alpha map for large images
