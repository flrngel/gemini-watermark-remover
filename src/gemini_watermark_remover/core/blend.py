import numpy as np
from numpy.typing import NDArray

from . import ALPHA_THRESHOLD, LOGO_VALUE, MAX_ALPHA
from .position import WatermarkPosition


def remove_watermark(
    image_array: NDArray[np.uint8],
    alpha_map: NDArray[np.float32],
    position: WatermarkPosition,
) -> NDArray[np.uint8]:
    """
    Remove watermark from image using reverse alpha blending.

    Formula: original = (watermarked - alpha * 255) / (1 - alpha)

    Args:
        image_array: Input image as numpy array (H, W, C) in RGB/RGBA format
        alpha_map: Alpha transparency map (size x size)
        position: Watermark position information

    Returns:
        Modified image array with watermark removed (in-place modification)
    """
    x, y = position.x, position.y
    w, h = position.width, position.height

    # Extract the watermark region
    region = image_array[y : y + h, x : x + w, :3].astype(np.float32)

    # Create mask for pixels to process (alpha above threshold)
    alpha = alpha_map.copy()
    mask = alpha >= ALPHA_THRESHOLD

    # Clamp alpha to prevent division by near-zero
    alpha = np.clip(alpha, 0, MAX_ALPHA)

    # Apply reverse alpha blending formula:
    # original = (watermarked - alpha * LOGO_VALUE) / (1 - alpha)
    # Vectorized operation for all 3 color channels
    alpha_expanded = alpha[:, :, np.newaxis]  # Shape: (h, w, 1)

    # Only process pixels where mask is True
    denominator = 1.0 - alpha_expanded
    numerator = region - alpha_expanded * LOGO_VALUE

    # Calculate restored values
    restored = numerator / denominator

    # Apply mask: only update pixels with significant alpha
    mask_expanded = mask[:, :, np.newaxis]
    result = np.where(mask_expanded, restored, region)

    # Clamp to valid range and convert back to uint8
    result = np.clip(result, 0, 255).astype(np.uint8)

    # Write back to image array
    image_array[y : y + h, x : x + w, :3] = result

    return image_array
