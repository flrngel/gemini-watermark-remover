from pathlib import Path

import numpy as np
from PIL import Image

from ..core.alpha_map import get_alpha_map
from ..core.blend import remove_watermark
from ..core.position import calculate_watermark_position

SUPPORTED_IMAGE_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


def is_supported_image(path: Path) -> bool:
    """Check if file is a supported image format."""
    return path.suffix.lower() in SUPPORTED_IMAGE_FORMATS


def process_image(
    input_path: Path,
    output_path: Path | None = None,
    suffix: str = "_output",
) -> Path:
    """
    Process a single image to remove watermark.

    Args:
        input_path: Path to input image
        output_path: Optional explicit output path. If None, uses input name with suffix.
        suffix: Suffix to add to filename if output_path not specified

    Returns:
        Path to the output file
    """
    # Determine output path
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}{suffix}.png"

    # Load image
    with Image.open(input_path) as img:
        # Convert to RGB if necessary (handles RGBA, palette, etc.)
        if img.mode != "RGB":
            img = img.convert("RGB")

        image_array = np.array(img, dtype=np.uint8)

    # Calculate watermark position
    height, width = image_array.shape[:2]
    position = calculate_watermark_position(width, height)

    # Get alpha map for this watermark size
    alpha_map = get_alpha_map(position.size)

    # Remove watermark
    result_array = remove_watermark(image_array, alpha_map, position)

    # Save result
    result_image = Image.fromarray(result_array)
    result_image.save(output_path, quality=95)

    return output_path
