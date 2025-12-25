# Asset loading utilities
from importlib import resources
from pathlib import Path


def get_asset_path(filename: str) -> Path:
    """Get the path to a bundled asset file."""
    return resources.files(__package__).joinpath(filename)
