from dataclasses import dataclass

from . import (
    LARGE_IMAGE_THRESHOLD,
    LARGE_MARGIN,
    LARGE_WATERMARK_SIZE,
    SMALL_MARGIN,
    SMALL_WATERMARK_SIZE,
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
