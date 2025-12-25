# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Project

This project uses ES6 Modules and requires a local server (CORS blocks direct file:// access):

```bash
# Python 3
python -m http.server 8000
```

Then open http://localhost:8000 in a browser.

## Architecture

This is a client-side watermark removal tool for Google Gemini AI-generated images/videos. No build steps or dependencies—pure vanilla JavaScript with Tailwind CSS via CDN.

### Core Algorithm

The tool uses **Reverse Alpha Blending** to mathematically invert Gemini's watermark:

```
Original = (Watermarked - α × 255) / (1 - α)
```

Where α (alpha) values are extracted from reference images (`bg_48.png`, `bg_96.png`).

### Module Structure

- **`js/blendModes.js`** - Core math: `removeWatermark()` applies the reverse alpha blending formula pixel-by-pixel
- **`js/alphaMap.js`** - Extracts alpha transparency values from reference images into a Float32Array
- **`js/engine.js`** - `WatermarkEngine` class for image processing. Loads reference assets, determines watermark size (48px for ≤1024px images, 96px for larger), applies removal
- **`js/videoEngine.js`** - `VideoWatermarkEngine` class for frame-by-frame video processing using Canvas API + MediaRecorder. Preserves audio tracks
- **`js/app.js`** - UI controller: handles drag/drop, file input, progress display, download

### Watermark Detection Logic

Watermark size/position is determined by image dimensions (in `engine.js:31` and `videoEngine.js:37`):
- Images/videos ≤1024px in both dimensions: 48px watermark, 32px margin from corner
- Larger: 96px watermark, 64px margin from corner

### Key Constants (videoEngine.js)

- `DEFAULT_VIDEO_BITRATE`: 15 Mbps base, scales with resolution
- `DEFAULT_RECORDING_FPS`: 30 fps output
- Bitrate tiers: 8 Mbps (≤720p), 15 Mbps (1080p), 40 Mbps (4K), 60 Mbps (higher)
