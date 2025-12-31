# Algorithm constants from original JS implementation
ALPHA_THRESHOLD: float = 0.002  # Skip if alpha below this
MAX_ALPHA: float = 0.99  # Clamp alpha to prevent division by near-zero
LOGO_VALUE: int = 255  # White watermark value

# Resolution thresholds
LARGE_IMAGE_THRESHOLD: int = 1024

# Watermark sizes
SMALL_WATERMARK_SIZE: int = 48
LARGE_WATERMARK_SIZE: int = 96
SMALL_MARGIN: int = 32
LARGE_MARGIN: int = 64

# Video bitrate tiers (in bits per second)
BITRATE_720P: int = 8_000_000  # 8 Mbps
BITRATE_1080P: int = 15_000_000  # 15 Mbps
BITRATE_4K: int = 40_000_000  # 40 Mbps
BITRATE_HIGHER: int = 60_000_000  # 60 Mbps

# Resolution thresholds (pixels)
PIXELS_720P: int = 1280 * 720  # 921,600
PIXELS_1080P: int = 1920 * 1080  # 2,073,600
PIXELS_4K: int = 3840 * 2160  # 8,294,400

# Veo watermark settings
# Veo watermark is "Veo" text in bottom-right corner
# Uses fixed dimensions with ratio-based margins (based on actual measurements)
VEO_WATERMARK_WIDTH: int = 100      # Fixed width with safety margin
VEO_WATERMARK_HEIGHT: int = 45      # Fixed height with safety margin
VEO_MARGIN_X_RATIO: float = 0.025   # ~2.5% from right edge
VEO_MARGIN_Y_RATIO: float = 0.015   # ~1.5% from bottom edge
VEO_MIN_MARGIN_X: int = 15          # Minimum margin from right
VEO_MIN_MARGIN_Y: int = 15          # Minimum margin from bottom

# Temporal consistency constants (for video processing)
# Optical flow parameters (Farneback algorithm)
OPTICAL_FLOW_PYR_SCALE: float = 0.5    # Pyramid scale
OPTICAL_FLOW_LEVELS: int = 3            # Pyramid levels
OPTICAL_FLOW_WIN_SIZE: int = 15         # Window size
OPTICAL_FLOW_ITERATIONS: int = 3        # Iterations at each level
OPTICAL_FLOW_POLY_N: int = 5            # Pixel neighborhood size
OPTICAL_FLOW_POLY_SIGMA: float = 1.2    # Gaussian std for derivatives

# Temporal blending parameters
TEMPORAL_BLEND_ALPHA: float = 0.7       # Weight for current frame (0.7 = 70% current, 30% previous)
SCENE_CUT_THRESHOLD: float = 30.0       # Max average flow magnitude before scene cut detection
CHANGE_CLAMP_THRESHOLD: float = 50.0    # Max per-pixel change between frames
FLOW_MAGNITUDE_THRESHOLD: float = 100.0 # Max flow magnitude before treating as scene cut
