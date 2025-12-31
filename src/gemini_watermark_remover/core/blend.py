import numpy as np
from numpy.typing import NDArray

from . import ALPHA_THRESHOLD, LOGO_VALUE, MAX_ALPHA
from .position import WatermarkPosition


def detect_gemini_watermark(
    region: NDArray[np.float32],
    alpha_map: NDArray[np.float32],
) -> bool:
    """
    Detect if Gemini sparkle watermark is actually present in the region.

    Uses correlation between alpha values and brightness to determine
    if a white watermark was applied via alpha blending.

    Returns True if watermark is likely present, False otherwise.
    """
    region_gray = np.mean(region, axis=2)

    # Check 1: High-alpha pixels should be significantly brighter than low-alpha pixels
    high_alpha_mask = alpha_map >= 0.1
    low_alpha_mask = alpha_map < 0.05

    if not (high_alpha_mask.any() and low_alpha_mask.any()):
        return False

    high_brightness = np.mean(region_gray[high_alpha_mask])
    low_brightness = np.mean(region_gray[low_alpha_mask])
    brightness_diff = high_brightness - low_brightness

    # Expected diff: avg_alpha * 255 * 0.5 (at least 50% of theoretical)
    # Reduced from 0.7 to handle more edge cases
    avg_high_alpha = np.mean(alpha_map[high_alpha_mask])
    expected_diff = avg_high_alpha * LOGO_VALUE * 0.5
    if brightness_diff < expected_diff:
        return False

    # Check 2: Verify brightness at high-alpha areas matches alpha blending formula
    # Expected: watermarked = original * (1 - alpha) + 255 * alpha
    # So: expected_brightness ≈ low_brightness * (1 - avg_alpha) + 255 * avg_alpha
    very_high_alpha = alpha_map >= 0.5
    if very_high_alpha.any():
        avg_very_high_alpha = np.mean(alpha_map[very_high_alpha])
        expected_brightness = low_brightness * (1 - avg_very_high_alpha) + LOGO_VALUE * avg_very_high_alpha
        actual_brightness = np.mean(region_gray[very_high_alpha])
        # Allow 30% tolerance from expected
        if actual_brightness < expected_brightness * 0.7:
            return False

    return True


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

    # Check if watermark is actually present using improved detection
    if not detect_gemini_watermark(region, alpha):
        return image_array

    alpha_expanded = alpha[:, :, np.newaxis]  # Shape: (h, w, 1)

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
