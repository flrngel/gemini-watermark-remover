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
# Size scales with video resolution
VEO_WATERMARK_WIDTH_RATIO: float = 0.05  # ~5% of video width
VEO_WATERMARK_HEIGHT_RATIO: float = 0.03  # ~3% of video height
VEO_WATERMARK_MARGIN_RATIO: float = 0.01  # ~1% margin from corner
VEO_MIN_WIDTH: int = 60  # Minimum watermark width
VEO_MIN_HEIGHT: int = 24  # Minimum watermark height
