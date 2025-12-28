from dataclasses import dataclass

from . import (
    LARGE_IMAGE_THRESHOLD,
    LARGE_MARGIN,
    LARGE_WATERMARK_SIZE,
    SMALL_MARGIN,
    SMALL_WATERMARK_SIZE,
    VEO_MARGIN_X_RATIO,
    VEO_MARGIN_Y_RATIO,
    VEO_MIN_MARGIN_X,
    VEO_MIN_MARGIN_Y,
    VEO_WATERMARK_HEIGHT,
    VEO_WATERMARK_WIDTH,
)


@dataclass
class WatermarkPosition:
    """Represents watermark position and dimensions."""

    x: int
    y: int
    width: int
    height: int
    size: int  # 48 or 96


def calculate_watermark_position(image_width: int, image_height: int) -> WatermarkPosition:
    """
    Calculate watermark position based on image dimensions.

    Watermark is positioned in the bottom-right corner.
    Size and margin depend on whether either dimension exceeds 1024px.
    """
    is_large = image_width > LARGE_IMAGE_THRESHOLD or image_height > LARGE_IMAGE_THRESHOLD

    size = LARGE_WATERMARK_SIZE if is_large else SMALL_WATERMARK_SIZE
    margin = LARGE_MARGIN if is_large else SMALL_MARGIN

    x = image_width - margin - size
    y = image_height - margin - size

    return WatermarkPosition(x=x, y=y, width=size, height=size, size=size)


@dataclass
class VeoWatermarkPosition:
    """Represents Veo watermark position and dimensions for delogo filter."""

    x: int
    y: int
    width: int
    height: int


def calculate_veo_watermark_position(video_width: int, video_height: int) -> VeoWatermarkPosition:
    """
    Calculate Veo watermark position based on video dimensions.

    Veo watermark is "Veo" text in bottom-right corner.
    Uses fixed dimensions with ratio-based margins.
    """
    # Fixed dimensions with safety margin
    width = VEO_WATERMARK_WIDTH
    height = VEO_WATERMARK_HEIGHT

    # Ratio-based margins from edges
    margin_x = max(VEO_MIN_MARGIN_X, int(video_width * VEO_MARGIN_X_RATIO))
    margin_y = max(VEO_MIN_MARGIN_Y, int(video_height * VEO_MARGIN_Y_RATIO))

    # Position in bottom-right corner
    x = max(0, video_width - margin_x - width)
    y = max(0, video_height - margin_y - height)

    # Ensure we don't exceed image bounds
    if x + width > video_width:
        x = video_width - width
    if y + height > video_height:
        y = video_height - height

    return VeoWatermarkPosition(x=x, y=y, width=width, height=height)
