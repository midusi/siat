"""
Camera motion compensator for traffic video analysis.

Estimates per-frame global camera motion (affine: translation + rotation)
relative to a fixed reference frame using sparse optical flow.

Algorithm: goodFeaturesToTrack on the reference frame (downscaled grayscale),
tracked forward with calcOpticalFlowPyrLK to the current frame, then
estimateAffinePartial2D (RANSAC) to fit the motion model.

The returned transform maps current-frame coordinates to reference-frame
coordinates, so zone polygons defined on the reference frame can be tested
directly against compensated bounding-box centers.

CPU cost: ~3-8 ms / frame at scale=0.5 on a 1920x1080 source (grayscale
optical flow on a 960x540 image is cheap; no GPU required).
"""
from __future__ import annotations

import numpy as np
import cv2
from typing import Dict, Optional, Tuple


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #

class MotionCompensator:
    """
    Estimates rigid camera motion relative to a reference frame and exposes
    helpers to map current-frame points/polygons back to reference-frame
    coordinates.

    Parameters
    ----------
    reference_frame:
        The first (or any fixed anchor) frame in BGR or grayscale.
    scale:
        Downscale factor applied before optical flow (0 < scale <= 1).
        0.5 gives a good speed/accuracy trade-off.
    deadband_px:
        Minimum estimated translation magnitude (pixels, full-res) below
        which the transform is replaced with the identity. Prevents jitter
        from tiny noise.
    anchor_interval:
        Re-detect features in the reference frame every this many frames,
        or when the tracked feature count drops below ``min_features``.
    max_corners:
        Maximum number of features to detect via goodFeaturesToTrack.
    quality_level:
        Quality threshold for goodFeaturesToTrack (0 < q <= 1).
    min_distance:
        Minimum pixel distance between detected features (at scaled res).
    min_features:
        Minimum inlier count required to accept the estimated transform;
        below this the identity is returned.
    """

    def __init__(
        self,
        reference_frame: np.ndarray,
        scale: float = 0.5,
        deadband_px: float = 2.0,
        anchor_interval: int = 50,
        max_corners: int = 200,
        quality_level: float = 0.01,
        min_distance: float = 10.0,
        min_features: int = 6,
    ) -> None:
        self.scale = scale
        self.deadband_px = deadband_px
        self.anchor_interval = anchor_interval
        self.max_corners = max_corners
        self.quality_level = quality_level
        self.min_distance = min_distance
        self.min_features = min_features

        self._ref_gray: np.ndarray = self._prepare(reference_frame)
        self._ref_kps: Optional[np.ndarray] = self._detect_features(self._ref_gray)
        self._frame_count: int = 0

    # ------------------------------------------------------------------ #
    # Core estimate                                                        #
    # ------------------------------------------------------------------ #

    def estimate(
        self,
        current_frame: np.ndarray,
        vehicle_boxes: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Estimate the affine transform that maps *current-frame* coordinates
        to *reference-frame* coordinates.

        Parameters
        ----------
        current_frame:
            Current video frame (BGR or grayscale, same resolution as the
            reference frame supplied at construction time).
        vehicle_boxes:
            Optional array of shape (N, 4) with full-resolution bounding
            boxes [x1, y1, x2, y2] for detected vehicles.  These regions
            are masked out so moving vehicles do not bias the estimate.

        Returns
        -------
        M : np.ndarray, shape (2, 3)
            Affine matrix mapping current-frame to reference-frame coords.
            Identity when motion is below the deadband or estimation fails.
        metrics : dict
            Per-frame motion summary::

                {
                    "dx": float,          # camera shift X (+ = right), full-res px
                    "dy": float,          # camera shift Y (+ = down), full-res px
                    "angle_deg": float,   # camera rotation in degrees
                    "magnitude_px": float # Euclidean magnitude of shift
                }
        """
        self._frame_count += 1
        identity = np.eye(2, 3, dtype=np.float64)
        zero_metrics: Dict[str, float] = {
            "dx": 0.0,
            "dy": 0.0,
            "angle_deg": 0.0,
            "magnitude_px": 0.0,
        }

        # Periodically re-anchor reference features.
        if (
            self._ref_kps is None
            or len(self._ref_kps) < self.min_features
            or self._frame_count % self.anchor_interval == 0
        ):
            self._ref_kps = self._detect_features(self._ref_gray)

        if self._ref_kps is None or len(self._ref_kps) < self.min_features:
            return identity.copy(), zero_metrics

        curr_gray = self._prepare(current_frame)

        # Track reference keypoints into the current frame.
        curr_kps, status, _ = cv2.calcOpticalFlowPyrLK(
            self._ref_gray, curr_gray, self._ref_kps, None
        )

        if curr_kps is None or status is None:
            return identity.copy(), zero_metrics

        status_flat = status.ravel().astype(bool)

        # Discard points that landed inside masked vehicle regions.
        if vehicle_boxes is not None and len(vehicle_boxes) > 0:
            veh_mask = self._build_vehicle_mask(curr_gray.shape[:2], vehicle_boxes)
            for i, kp in enumerate(curr_kps):
                if status_flat[i]:
                    cx, cy = int(kp[0, 0]), int(kp[0, 1])
                    if 0 <= cy < veh_mask.shape[0] and 0 <= cx < veh_mask.shape[1]:
                        if veh_mask[cy, cx] == 0:
                            status_flat[i] = False

        src_pts = self._ref_kps[status_flat]
        dst_pts = curr_kps[status_flat]

        if len(src_pts) < self.min_features:
            return identity.copy(), zero_metrics

        # Fit affine (translation + rotation + isotropic scale) at scaled res.
        # src_pts (reference) -> dst_pts (current).
        M_small, inliers = cv2.estimateAffinePartial2D(
            src_pts,
            dst_pts,
            method=cv2.RANSAC,
            ransacReprojThreshold=3.0,
            maxIters=2000,
            confidence=0.99,
        )

        if M_small is None:
            return identity.copy(), zero_metrics

        if inliers is not None and int(inliers.sum()) < self.min_features:
            return identity.copy(), zero_metrics

        # Scale translation back to full-resolution.
        M_full = M_small.astype(np.float64).copy()
        M_full[0, 2] /= self.scale
        M_full[1, 2] /= self.scale

        # M_full maps reference -> current.  Extract metrics from it.
        # estimateAffinePartial2D returns [[cos(θ), sin(θ), tx], [-sin(θ), cos(θ), ty]]
        # so the rotation angle θ lives in M[0,1] (= sin θ) and M[0,0] (= cos θ).
        dx = float(M_full[0, 2])
        dy = float(M_full[1, 2])
        angle_deg = float(np.degrees(np.arctan2(M_full[0, 1], M_full[0, 0])))
        magnitude = float(np.hypot(dx, dy))

        metrics: Dict[str, float] = {
            "dx": dx,
            "dy": dy,
            "angle_deg": angle_deg,
            "magnitude_px": magnitude,
        }

        # Deadband: tiny motion is treated as zero.
        if magnitude < self.deadband_px and abs(angle_deg) < 0.1:
            return identity.copy(), metrics

        # Invert M_full to get current -> reference transform.
        M_inv = cv2.invertAffineTransform(M_full)
        return M_inv, metrics

    # ------------------------------------------------------------------ #
    # Transform helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def transform_point(
        pt: Tuple[float, float],
        M: np.ndarray,
    ) -> Tuple[int, int]:
        """
        Apply a 2x3 affine matrix *M* to a single 2-D point.

        Parameters
        ----------
        pt:
            (x, y) in source coordinates.
        M:
            2x3 affine matrix.

        Returns
        -------
        (x', y') rounded to integer pixel coordinates.
        """
        x, y = float(pt[0]), float(pt[1])
        xn = M[0, 0] * x + M[0, 1] * y + M[0, 2]
        yn = M[1, 0] * x + M[1, 1] * y + M[1, 2]
        return (int(round(xn)), int(round(yn)))

    @staticmethod
    def transform_polygon(
        polygon: np.ndarray,
        M: np.ndarray,
    ) -> np.ndarray:
        """
        Apply a 2x3 affine matrix *M* to every vertex of *polygon*.

        Parameters
        ----------
        polygon:
            Array of shape (N, 2) or (N, 1, 2) with integer coordinates.
        M:
            2x3 affine matrix.

        Returns
        -------
        Transformed polygon as (N, 1, 2) int32 array.
        """
        pts = polygon.reshape(-1, 2).astype(np.float64)
        ones = np.ones((len(pts), 1), dtype=np.float64)
        pts_h = np.hstack([pts, ones])          # (N, 3)
        transformed = (M @ pts_h.T).T            # (N, 2)
        return np.round(transformed).astype(np.int32).reshape(-1, 1, 2)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _prepare(self, frame: np.ndarray) -> np.ndarray:
        """Downscale and convert to grayscale."""
        h, w = frame.shape[:2]
        new_w = max(1, int(w * self.scale))
        new_h = max(1, int(h * self.scale))
        small = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        if small.ndim == 3:
            return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return small

    def _detect_features(
        self,
        gray: np.ndarray,
        mask: Optional[np.ndarray] = None,
    ) -> Optional[np.ndarray]:
        """Detect good features to track on *gray* (scaled grayscale)."""
        kps = cv2.goodFeaturesToTrack(
            gray,
            maxCorners=self.max_corners,
            qualityLevel=self.quality_level,
            minDistance=self.min_distance,
            mask=mask,
            blockSize=3,
        )
        return kps

    def _build_vehicle_mask(
        self,
        gray_shape: Tuple[int, int],
        vehicle_boxes: np.ndarray,
    ) -> np.ndarray:
        """
        Build a uint8 mask (255 = usable, 0 = vehicle region) at scaled
        resolution so that tracked features inside vehicle bounding boxes
        are rejected.
        """
        h, w = gray_shape
        mask = np.full((h, w), 255, dtype=np.uint8)
        for box in vehicle_boxes:
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            # Scale to downscaled frame.
            x1s = max(0, int(x1 * self.scale))
            y1s = max(0, int(y1 * self.scale))
            x2s = min(w, int(x2 * self.scale))
            y2s = min(h, int(y2 * self.scale))
            if x2s > x1s and y2s > y1s:
                mask[y1s:y2s, x1s:x2s] = 0
        return mask
