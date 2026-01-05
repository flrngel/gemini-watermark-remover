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

Python CLI tool using `uv` for package management. Removes **all** AI watermarks (Gemini + Veo) from images/videos in a single pass.

### Core Algorithm

For videos, both watermarks are removed together:
1. Extract frames
2. Apply Gemini alpha blending reversal to each frame
3. Reassemble with ffmpeg, applying Veo delogo filter during encoding

```python
# Gemini: Reverse Alpha Blending
original = (watermarked - alpha * 255) / (1 - alpha)

# Veo: ffmpeg delogo filter
ffmpeg.filter("delogo", x=pos.x, y=pos.y, w=pos.width, h=pos.height)
```

Constants in `src/gemini_watermark_remover/core/__init__.py`:
- `ALPHA_THRESHOLD = 0.002` - Skip pixels with negligible alpha
- `MAX_ALPHA = 0.99` - Prevent division by near-zero
- `LOGO_VALUE = 255` - White watermark

### Module Structure

- **`core/blend.py`** - Vectorized numpy watermark removal (Gemini)
- **`core/alpha_map.py`** - Loads reference PNGs, extracts alpha as `max(R,G,B)/255`
- **`core/position.py`** - Calculates watermark positions for both Gemini and Veo
- **`processors/image.py`** - Pillow-based single image processing (Gemini only)
- **`processors/video.py`** - Combined Gemini + Veo video processing
- **`cli.py`** - typer CLI with `process` and `info` commands

### Gemini Watermark Position

```python
is_large = width > 1024 or height > 1024
size = 96 if is_large else 48
margin = 64 if is_large else 32
x, y = width - margin - size, height - margin - size
```

### Veo Watermark Position

```python
# Scales with video resolution
width = max(60, int(video_width * 0.05))   # ~5% of width
height = max(24, int(video_height * 0.03))  # ~3% of height
margin = max(8, int(dimension * 0.01))      # ~1% margin
x, y = video_width - margin - width, video_height - margin - height
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

### CLI Features

- Supports both files and directories as input
- `-r` flag for recursive directory processing
- Outputs `_output` suffix by default (configurable with `-s`)

### macOS Finder Integration

`scripts/remove-watermark.sh` - Shell script for Automator Quick Action integration.

To create a Finder right-click action:
1. Open Automator → Quick Action
2. Set "Workflow receives: files or folders in Finder"
3. Add "Run Shell Script" with shell `/bin/bash` and pass input `as arguments`
4. Paste script contents (update `PROJECT_DIR` path)
5. Save as "Remove Watermark"

Debug log location: `/tmp/gwr-debug.log`
