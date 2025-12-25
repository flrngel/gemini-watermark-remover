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
    img_h, img_w = image_array.shape[:2]

    # Bounds checking - ensure we don't go out of image bounds
    if x < 0 or y < 0 or x + w > img_w or y + h > img_h:
        # Skip if watermark region is out of bounds
        return image_array

    # Extract the watermark region
    region = image_array[y : y + h, x : x + w, :3].astype(np.float32)

    # Create mask for pixels to process (alpha above threshold)
    alpha = alpha_map.copy()
    mask = alpha >= ALPHA_THRESHOLD

    # Clamp alpha to prevent division by near-zero
    alpha = np.clip(alpha, 0, MAX_ALPHA)

    # Check if this region actually has a watermark
    # If the pixels are too dark where alpha is high, there's no watermark
    # (applying the formula would produce negative/black values)
    alpha_expanded = alpha[:, :, np.newaxis]  # Shape: (h, w, 1)

    # For pixels with significant alpha, check if they're bright enough
    # to have been watermarked (watermarked pixels should be >= alpha * 255)
    high_alpha_mask = alpha >= 0.1  # Pixels with noticeable watermark effect
    if high_alpha_mask.any():
        # Get average brightness in high-alpha region
        high_alpha_region = region[high_alpha_mask]
        expected_min_brightness = np.mean(alpha[high_alpha_mask]) * LOGO_VALUE * 0.5
        actual_brightness = np.mean(high_alpha_region)

        # If the region is too dark, there's probably no watermark
        if actual_brightness < expected_min_brightness:
            return image_array

    # Apply reverse alpha blending formula:
    # original = (watermarked - alpha * LOGO_VALUE) / (1 - alpha)
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
