from dataclasses import dataclass

from . import (
    LARGE_IMAGE_THRESHOLD,
    LARGE_MARGIN,
    LARGE_WATERMARK_SIZE,
    SMALL_MARGIN,
    SMALL_WATERMARK_SIZE,
    VEO_MIN_HEIGHT,
    VEO_MIN_WIDTH,
    VEO_WATERMARK_HEIGHT_RATIO,
    VEO_WATERMARK_MARGIN_RATIO,
    VEO_WATERMARK_WIDTH_RATIO,
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
    Size scales with video resolution.
    """
    # Calculate dimensions based on video size
    width = max(VEO_MIN_WIDTH, int(video_width * VEO_WATERMARK_WIDTH_RATIO))
    height = max(VEO_MIN_HEIGHT, int(video_height * VEO_WATERMARK_HEIGHT_RATIO))
    margin_x = max(8, int(video_width * VEO_WATERMARK_MARGIN_RATIO))
    margin_y = max(8, int(video_height * VEO_WATERMARK_MARGIN_RATIO))

    # Position in bottom-right corner
    x = video_width - margin_x - width
    y = video_height - margin_y - height

    return VeoWatermarkPosition(x=x, y=y, width=width, height=height)
