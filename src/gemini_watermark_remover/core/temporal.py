"""Temporal consistency for video watermark removal using optical flow."""

import cv2
import numpy as np
from numpy.typing import NDArray

from . import (
    CHANGE_CLAMP_THRESHOLD,
    FLOW_MAGNITUDE_THRESHOLD,
    OPTICAL_FLOW_ITERATIONS,
    OPTICAL_FLOW_LEVELS,
    OPTICAL_FLOW_POLY_N,
    OPTICAL_FLOW_POLY_SIGMA,
    OPTICAL_FLOW_PYR_SCALE,
    OPTICAL_FLOW_WIN_SIZE,
    SCENE_CUT_THRESHOLD,
    TEMPORAL_BLEND_ALPHA,
)
from .position import VeoWatermarkPosition, WatermarkPosition


def compute_optical_flow(
    prev_gray: NDArray[np.uint8],
    curr_gray: NDArray[np.uint8],
) -> NDArray[np.float32]:
    """
    Compute dense optical flow between two grayscale frames.

    Uses Farneback algorithm for dense optical flow estimation.

    Args:
        prev_gray: Previous frame in grayscale (H, W)
        curr_gray: Current frame in grayscale (H, W)

    Returns:
        flow: Optical flow field (H, W, 2) where [:,:,0] is dx and [:,:,1] is dy
    """
    flow = cv2.calcOpticalFlowFarneback(
        prev_gray,
        curr_gray,
        None,
        pyr_scale=OPTICAL_FLOW_PYR_SCALE,
        levels=OPTICAL_FLOW_LEVELS,
        winsize=OPTICAL_FLOW_WIN_SIZE,
        iterations=OPTICAL_FLOW_ITERATIONS,
        poly_n=OPTICAL_FLOW_POLY_N,
        poly_sigma=OPTICAL_FLOW_POLY_SIGMA,
        flags=0,
    )
    return flow


def detect_scene_cut(
    flow: NDArray[np.float32],
    threshold: float = SCENE_CUT_THRESHOLD,
) -> bool:
    """
    Detect scene cut by analyzing optical flow magnitude.

    Large average flow magnitude indicates scene cut or camera jump.

    Args:
        flow: Optical flow field (H, W, 2)
        threshold: Maximum average magnitude before scene cut

    Returns:
        True if scene cut detected
    """
    magnitude = np.sqrt(flow[:, :, 0] ** 2 + flow[:, :, 1] ** 2)
    avg_magnitude = np.mean(magnitude)
    max_magnitude = np.max(magnitude)

    return avg_magnitude > threshold or max_magnitude > FLOW_MAGNITUDE_THRESHOLD


def warp_region(
    region: NDArray[np.uint8],
    flow_region: NDArray[np.float32],
) -> NDArray[np.float32]:
    """
    Warp a region using optical flow to align with current frame.

    Uses cv2.remap with bilinear interpolation for sub-pixel accuracy.

    Args:
        region: Region to warp (H, W, C)
        flow_region: Corresponding flow (H, W, 2)

    Returns:
        Warped region as float32 (H, W, C)
    """
    h, w = region.shape[:2]

    # Create coordinate grid
    y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)

    # Apply flow (forward warp approximation using inverse mapping)
    map_x = x_coords + flow_region[:, :, 0]
    map_y = y_coords + flow_region[:, :, 1]

    # Warp using bilinear interpolation
    warped = cv2.remap(
        region.astype(np.float32),
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )

    return warped


def blend_with_temporal(
    current_result: NDArray[np.float32],
    warped_previous: NDArray[np.float32],
    alpha: float = TEMPORAL_BLEND_ALPHA,
) -> NDArray[np.float32]:
    """
    Blend current frame result with motion-compensated previous frame.

    Args:
        current_result: Current frame's watermark removal result
        warped_previous: Previous frame's result warped to align with current
        alpha: Weight for current frame (higher = less smoothing)

    Returns:
        Blended result as float32
    """
    return alpha * current_result + (1 - alpha) * warped_previous


def clamp_changes(
    current: NDArray[np.float32],
    previous: NDArray[np.float32],
    max_change: float = CHANGE_CLAMP_THRESHOLD,
) -> NDArray[np.uint8]:
    """
    Clamp aggressive pixel changes between frames.

    Prevents flickering by limiting how much each pixel can change.

    Args:
        current: Current frame result (float32)
        previous: Previous frame result, motion-compensated (float32)
        max_change: Maximum allowed change per pixel per channel

    Returns:
        Clamped result as uint8
    """
    diff = current - previous
    clamped_diff = np.clip(diff, -max_change, max_change)
    result = previous + clamped_diff
    return np.clip(result, 0, 255).astype(np.uint8)


class TemporalProcessor:
    """
    Manages temporal consistency across video frames.

    Tracks previous frame data and applies optical flow-based
    temporal smoothing to watermark removal regions.
    """

    def __init__(
        self,
        gemini_pos: WatermarkPosition,
        veo_pos: VeoWatermarkPosition,
        blend_alpha: float = TEMPORAL_BLEND_ALPHA,
        clamp_threshold: float = CHANGE_CLAMP_THRESHOLD,
    ):
        """
        Initialize temporal processor.

        Args:
            gemini_pos: Gemini watermark position
            veo_pos: Veo watermark position
            blend_alpha: Weight for current frame in blending
            clamp_threshold: Maximum pixel change per frame
        """
        self.gemini_pos = gemini_pos
        self.veo_pos = veo_pos
        self.blend_alpha = blend_alpha
        self.clamp_threshold = clamp_threshold

        # State from previous frame
        self.prev_gray: NDArray[np.uint8] | None = None
        self.prev_gemini_result: NDArray[np.uint8] | None = None
        self.prev_veo_result: NDArray[np.uint8] | None = None
        self.frame_count: int = 0

    def process_frame(
        self,
        original_frame: NDArray[np.uint8],
        current_result: NDArray[np.uint8],
    ) -> NDArray[np.uint8]:
        """
        Apply temporal consistency to a processed frame.

        Args:
            original_frame: Original frame before watermark removal (for flow computation)
            current_result: Frame after watermark removal

        Returns:
            Temporally smoothed result
        """
        self.frame_count += 1

        # Convert current frame to grayscale for flow computation
        curr_gray = cv2.cvtColor(original_frame, cv2.COLOR_RGB2GRAY)

        # First frame - no temporal processing possible
        if self.prev_gray is None:
            self._update_state(curr_gray, current_result)
            return current_result

        # Compute optical flow
        flow = compute_optical_flow(self.prev_gray, curr_gray)

        # Check for scene cut
        if detect_scene_cut(flow):
            self._update_state(curr_gray, current_result)
            return current_result

        # Apply temporal consistency to both watermark regions
        result = current_result.copy()

        # Process Gemini region
        result = self._process_region(
            result,
            flow,
            self.gemini_pos.x,
            self.gemini_pos.y,
            self.gemini_pos.width,
            self.gemini_pos.height,
            self.prev_gemini_result,
        )

        # Process Veo region
        result = self._process_region(
            result,
            flow,
            self.veo_pos.x,
            self.veo_pos.y,
            self.veo_pos.width,
            self.veo_pos.height,
            self.prev_veo_result,
        )

        # Update state for next frame
        self._update_state(curr_gray, result)

        return result

    def _process_region(
        self,
        result: NDArray[np.uint8],
        flow: NDArray[np.float32],
        x: int,
        y: int,
        w: int,
        h: int,
        prev_region_result: NDArray[np.uint8] | None,
    ) -> NDArray[np.uint8]:
        """Apply temporal consistency to a single watermark region."""
        if prev_region_result is None:
            return result

        # Bounds checking
        img_h, img_w = result.shape[:2]
        if x < 0 or y < 0 or x + w > img_w or y + h > img_h:
            return result

        # Extract flow for this region
        flow_region = flow[y : y + h, x : x + w]

        # Check if region has valid flow (not too extreme)
        region_magnitude = np.sqrt(flow_region[:, :, 0] ** 2 + flow_region[:, :, 1] ** 2)
        if np.mean(region_magnitude) > SCENE_CUT_THRESHOLD:
            return result  # Skip temporal for this region

        # Warp previous result to align with current
        warped_prev = warp_region(prev_region_result, flow_region)

        # Get current region result
        current_region = result[y : y + h, x : x + w].astype(np.float32)

        # Blend current with warped previous
        blended = blend_with_temporal(current_region, warped_prev, self.blend_alpha)

        # Clamp aggressive changes
        clamped = clamp_changes(blended, warped_prev, self.clamp_threshold)

        # Write back to result
        result[y : y + h, x : x + w] = clamped

        return result

    def _update_state(
        self,
        curr_gray: NDArray[np.uint8],
        result: NDArray[np.uint8],
    ) -> None:
        """Update state for next frame."""
        self.prev_gray = curr_gray.copy()

        # Store watermark regions from result
        gp = self.gemini_pos
        img_h, img_w = result.shape[:2]

        # Gemini region (with bounds checking)
        if 0 <= gp.x < img_w and 0 <= gp.y < img_h:
            self.prev_gemini_result = result[
                gp.y : gp.y + gp.height, gp.x : gp.x + gp.width
            ].copy()
        else:
            self.prev_gemini_result = None

        # Veo region (with bounds checking)
        vp = self.veo_pos
        if 0 <= vp.x < img_w and 0 <= vp.y < img_h:
            self.prev_veo_result = result[
                vp.y : vp.y + vp.height, vp.x : vp.x + vp.width
            ].copy()
        else:
            self.prev_veo_result = None

    def reset(self) -> None:
        """Reset temporal state (call on scene cut or new video)."""
        self.prev_gray = None
        self.prev_gemini_result = None
        self.prev_veo_result = None
        self.frame_count = 0
