from importlib import resources

import numpy as np
from numpy.typing import NDArray
from PIL import Image

# Cache alpha maps to avoid reloading
_alpha_map_cache: dict[int, NDArray[np.float32]] = {}


def load_alpha_map(size: int) -> NDArray[np.float32]:
    """
    Load and calculate alpha map from reference PNG.

    Args:
        size: Watermark size (48 or 96)

    Returns:
        Float32 numpy array of alpha values (0.0 to 1.0)
    """
    filename = f"bg_{size}.png"

    # Load from package assets using importlib.resources
    with resources.files("gemini_watermark_remover.assets").joinpath(filename).open("rb") as f:
        img = Image.open(f)
        img_array = np.array(img, dtype=np.float32)

    # Calculate alpha as max(R, G, B) / 255.0
    # The reference images encode alpha in RGB channels
    if img_array.ndim == 3:
        alpha_map = np.max(img_array[:, :, :3], axis=2) / 255.0
    else:
        alpha_map = img_array / 255.0

    return alpha_map.astype(np.float32)


def get_alpha_map(size: int) -> NDArray[np.float32]:
    """Get cached alpha map or load if not cached."""
    if size not in _alpha_map_cache:
        _alpha_map_cache[size] = load_alpha_map(size)
    return _alpha_map_cache[size]
