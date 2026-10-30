"""
Camera motion compensator for traffic video analysis.

Estimates per-frame global camera motion relative to a fixed reference frame
and exposes helpers to map current-frame polygons / points back to reference-
frame coordinates (or forward to current-frame coordinates for drawing).

Model: 3x3 projective homography (cv2.findHomography, RANSAC).  This
correctly models perspective distortion from drone footage where the ground
plane is viewed at an angle, and captures the full scope of pan/tilt/roll
motion that a similarity or affine transform cannot represent at frame edges.

Algorithm (two-phase, offline):
  Phase 1 — pre_compute(video_path):
    Read the video once at reduced resolution (no YOLO), compute per-frame
    raw homographies via frame-to-frame LK optical flow chained into a
    cumulative ref→cur transform, with periodic ORB feature-matching
    re-anchoring to the reference frame to prevent drift accumulation.
    Apply zero-phase Gaussian smoothing across all frames to eliminate
    estimation noise (jitter) while preserving real camera motion.

  Phase 2 — get_transform(frame_idx):
    O(1) lookup of the pre-computed, smoothed homography for each frame.

Deadband: removed.  The old hard 2px snap caused visible discontinuities
whenever motion hovered around the threshold.  Smoothing is the correct way
to suppress noise.

CPU cost: Phase 1 adds roughly 3-8 ms/frame for the optical-flow pass on a
downscaled (0.5×) grayscale image.  YOLO is not involved.

Backward compatibility: transform_point() and transform_polygon() accept
both 2x3 affine (legacy) and 3x3 homography matrices so that existing test
helpers and any code that still has 2x3 matrices continue to work.
"""
from __future__ import annotations

import numpy as np
import cv2
from typing import Dict, Optional, Tuple


# --------------------------------------------------------------------------- #
# Internal helpers                                                             #
# --------------------------------------------------------------------------- #

def _gaussian_smooth_1d(arr: np.ndarray, sigma: float) -> np.ndarray:
    """
    Zero-phase Gaussian smoothing of a 1-D float array.

    Uses a symmetric Gaussian kernel with reflect padding so edge frames are
    not biased.  A symmetric kernel produces zero phase shift on the signal,
    which is what we want: smooth noise away without lagging real motion.
    """
    if sigma <= 0.0 or len(arr) < 3:
        return arr.copy()
    radius = max(1, int(4.0 * sigma + 0.5))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= kernel.sum()
    padded = np.pad(arr, radius, mode="reflect")
    return np.convolve(padded, kernel, mode="valid")


def _scale_homography(H: np.ndarray, inv_scale: float) -> np.ndarray:
    """
    Convert a homography estimated at scaled resolution back to full resolution.

    If H_s is the homography at scale s and S = diag(s, s, 1), then
    H_full = S_inv @ H_s @ S  where S_inv = diag(1/s, 1/s, 1).
    """
    s = inv_scale  # == 1 / scale
    S_inv = np.diag([s, s, 1.0])
    S = np.diag([1.0 / s, 1.0 / s, 1.0])
    return S_inv @ H @ S


def _h_to_metrics(H: np.ndarray) -> Dict[str, float]:
    """
    Extract approximate motion metrics from a ref→cur homography.

    For OpenCV's image-coordinate rotation convention (y-axis pointing down),
    a rotation by +θ degrees produces:
        H[0,0] = cos(θ),  H[0,1] = sin(θ)   ← positive sin in row 0
        H[1,0] = -sin(θ), H[1,1] = cos(θ)
    so the angle is recovered as arctan2(H[0,1], H[0,0]) = θ.
    Using H[1,0] would give -θ.
    """
    dx = float(H[0, 2])
    dy = float(H[1, 2])
    angle_deg = float(np.degrees(np.arctan2(float(H[0, 1]), float(H[0, 0]))))
    magnitude = float(np.hypot(dx, dy))
    return {
        "dx": dx,
        "dy": dy,
        "angle_deg": angle_deg,
        "magnitude_px": magnitude,
    }


# --------------------------------------------------------------------------- #
# Public API                                                                  #
# --------------------------------------------------------------------------- #

class MotionCompensator:
    """
    Homography-based camera motion compensator.

    Typical usage (production):
        comp = MotionCompensator.pre_compute(video_path)
        ...
        H_ref_to_cur, metrics = comp.get_transform(frame_idx)

    Single-frame usage (unit tests / fallback):
        comp = MotionCompensator(reference_frame)
        H_cur_to_ref, metrics = comp.estimate(current_frame)

    Parameters
    ----------
    reference_frame:
        First (anchor) video frame in BGR or grayscale.
    scale:
        Downscale factor for optical flow (0 < scale <= 1).
    max_corners:
        Max features for goodFeaturesToTrack.
    quality_level:
        Quality threshold for goodFeaturesToTrack.
    min_distance:
        Minimum inter-feature pixel distance (at scaled res).
    min_features:
        Minimum inlier count to accept a homography estimate.
    """

    def __init__(
        self,
        reference_frame: np.ndarray,
        scale: float = 0.5,
        max_corners: int = 300,
        quality_level: float = 0.01,
        min_distance: float = 10.0,
        min_features: int = 8,
        # Kept for backward compat but ignored — deadband is removed.
        deadband_px: float = 0.0,
        anchor_interval: int = 30,
    ) -> None:
        self.scale = scale
        self.max_corners = max_corners
        self.quality_level = quality_level
        self.min_distance = min_distance
        self.min_features = min_features
        self.anchor_interval = anchor_interval

        self._ref_gray: np.ndarray = self._prepare(reference_frame)
        self._ref_kps: Optional[np.ndarray] = self._detect_features(self._ref_gray)

        # Pre-computed smoothed homographies indexed by 1-based frame number.
        # Set by pre_compute(); None means single-frame estimate() mode.
        self._homographies: Optional[Dict[int, np.ndarray]] = None

    # ------------------------------------------------------------------ #
    # Phase 1: pre-compute (two-pass, offline)                            #
    # ------------------------------------------------------------------ #

    @classmethod
    def pre_compute(
        cls,
        video_path: str,
        scale: float = 0.5,
        anchor_interval: int = 30,
        smooth_sigma: float = 1.5,
        max_corners: int = 300,
        quality_level: float = 0.01,
        min_distance: float = 10.0,
        min_features: int = 8,
        max_frames: Optional[int] = None,
        verbose: bool = False,
    ) -> "MotionCompensator":
        """
        First pass over the video: estimate per-frame homographies, smooth,
        and return a ready compensator.

        Parameters
        ----------
        video_path:
            Path to the source video file.
        scale:
            Downscale factor for optical flow (< 1 speeds up the pass).
        anchor_interval:
            Re-anchor to the reference frame every this many frames via ORB
            feature matching to prevent drift accumulation.
        smooth_sigma:
            Standard deviation (in frames) of the Gaussian smoothing kernel.
            Larger = smoother but slightly more lag; 1.5 is a good default.
        max_frames:
            Stop after this many frames (None = full video).
        verbose:
            Print per-anchor diagnostics when True.

        Returns
        -------
        MotionCompensator instance ready for get_transform().
        """
        instance = cls.__new__(cls)
        instance.scale = scale
        instance.max_corners = max_corners
        instance.quality_level = quality_level
        instance.min_distance = min_distance
        instance.min_features = min_features
        instance.anchor_interval = anchor_interval
        instance._ref_gray = None
        instance._ref_kps = None
        instance._homographies = {}

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"MotionCompensator.pre_compute: cannot open {video_path!r}")

        # Full-resolution dimensions — needed later to define smoothing corners.
        frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        raw_Hs: list[np.ndarray] = []
        frame_indices: list[int] = []

        ref_gray: Optional[np.ndarray] = None
        ref_kps: Optional[np.ndarray] = None
        prev_gray: Optional[np.ndarray] = None
        prev_kps: Optional[np.ndarray] = None
        H_cumulative = np.eye(3, dtype=np.float64)

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            if max_frames is not None and frame_idx > max_frames:
                break

            curr_gray = instance._prepare(frame)

            if frame_idx == 1:
                ref_gray = curr_gray.copy()
                ref_kps = instance._detect_features(ref_gray)
                prev_gray = curr_gray.copy()
                prev_kps = ref_kps.copy() if ref_kps is not None else None
                H_cumulative = np.eye(3, dtype=np.float64)
                raw_Hs.append(np.eye(3, dtype=np.float64))
                frame_indices.append(frame_idx)
                continue

            # --- Frame-to-frame LK tracking ---
            stepped = False
            if prev_kps is not None and len(prev_kps) >= min_features:
                curr_kps_lk, status, _ = cv2.calcOpticalFlowPyrLK(
                    prev_gray, curr_gray, prev_kps, None
                )
                if curr_kps_lk is not None and status is not None:
                    ok = status.ravel().astype(bool)
                    src_pts = prev_kps[ok]
                    dst_pts = curr_kps_lk[ok]

                    if len(src_pts) >= min_features:
                        H_step, hmask = cv2.findHomography(
                            src_pts, dst_pts,
                            cv2.RANSAC, 3.0,
                            maxIters=1000, confidence=0.995,
                        )
                        if (
                            H_step is not None
                            and hmask is not None
                            and int(hmask.sum()) >= min_features
                        ):
                            # H_step maps prev→curr; chain: ref→prev→curr
                            H_cumulative = H_step @ H_cumulative
                            prev_kps = dst_pts[hmask.ravel().astype(bool)].reshape(-1, 1, 2)
                            prev_gray = curr_gray.copy()
                            stepped = True

            # --- Periodic ORB re-anchoring (drift prevention) ---
            needs_anchor = (
                not stepped
                or frame_idx % anchor_interval == 0
                or (prev_kps is not None and len(prev_kps) < min_features)
            )
            if needs_anchor:
                H_anchor = instance._match_to_reference(
                    ref_gray, curr_gray, min_features=min_features
                )
                if H_anchor is not None:
                    if verbose:
                        print(f"  [motion] frame {frame_idx}: re-anchored via ORB")
                    H_cumulative = H_anchor
                    # Continue chaining FROM curr (not from ref!).
                    # If we set prev=ref here, the next H_step would map ref→t+1
                    # and we'd chain H_ref_to_t1 @ H_ref_to_t — wrong.
                    # Setting prev=curr means H_step next iteration = H_t_to_t+1,
                    # so H_cumulative = H_t_to_t+1 @ H_anchor = H_ref_to_t+1 ✓
                else:
                    if verbose:
                        print(f"  [motion] frame {frame_idx}: ORB re-anchor failed, replenishing")
                # Either way, continue tracking from current frame.
                prev_gray = curr_gray.copy()
                prev_kps = instance._detect_features(curr_gray)
            elif prev_kps is None or len(prev_kps) < min_features:
                # Replenish sparse point set
                prev_kps = instance._detect_features(curr_gray)

            raw_Hs.append(H_cumulative.copy())
            frame_indices.append(frame_idx)

        cap.release()

        if not raw_Hs:
            return instance  # empty video; all lookups fall back to identity

        # --- Convert scaled-resolution Hs to full resolution ---
        inv_s = 1.0 / scale
        full_Hs = [_scale_homography(H, inv_s) for H in raw_Hs]

        # --- Zero-phase Gaussian smoothing (geometrically valid) ---
        #
        # Smoothing raw H[i,j] entries independently is NOT valid: those entries
        # have no isolated geometric meaning and their averages produce matrices
        # that are not geometrically meaningful averages of the transformations.
        #
        # Correct approach:
        #   1. Warp the 4 frame corners through each raw H — this gives the actual
        #      pixel displacement of known points over time.
        #   2. Apply Gaussian smoothing to each corner's (x, y) trajectory.
        #   3. Refit a new H from the 4 smoothed src→dst pairs using
        #      getPerspectiveTransform (exact DLT — 4 points determine H uniquely).
        n = len(full_Hs)
        corners_ref = np.array(
            [
                [0.0,           0.0          ],
                [frame_w - 1.0, 0.0          ],
                [frame_w - 1.0, frame_h - 1.0],
                [0.0,           frame_h - 1.0],
            ],
            dtype=np.float64,
        )

        warped = np.zeros((n, 4, 2), dtype=np.float64)
        for k, H in enumerate(full_Hs):
            pts = corners_ref.reshape(-1, 1, 2).astype(np.float32)
            w = cv2.perspectiveTransform(pts, H.astype(np.float32))
            warped[k] = w.reshape(-1, 2)

        warped_sm = np.empty_like(warped)
        for ci in range(4):
            for d in range(2):
                warped_sm[:, ci, d] = _gaussian_smooth_1d(warped[:, ci, d], smooth_sigma)

        src_corners = corners_ref.astype(np.float32)
        smooth_Hs: list[np.ndarray] = []
        for k in range(n):
            dst_corners = warped_sm[k].astype(np.float32)
            H_fit = cv2.getPerspectiveTransform(src_corners, dst_corners)
            smooth_Hs.append(H_fit if H_fit is not None else full_Hs[k])

        # --- Store indexed by 1-based frame number ---
        for k, fidx in enumerate(frame_indices):
            instance._homographies[fidx] = smooth_Hs[k]

        return instance

    # ------------------------------------------------------------------ #
    # Phase 2: lookup (O(1) per frame)                                    #
    # ------------------------------------------------------------------ #

    def get_transform(
        self,
        frame_idx: int,
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Return the pre-computed, smoothed reference→current homography for
        frame *frame_idx* (1-based).

        Returns the 3x3 identity and zero metrics when the compensator has
        no pre-computed data for this frame (out of range or pre_compute
        was not called).
        """
        identity = np.eye(3, dtype=np.float64)
        zero_metrics: Dict[str, float] = {
            "dx": 0.0,
            "dy": 0.0,
            "angle_deg": 0.0,
            "magnitude_px": 0.0,
        }
        if self._homographies is None:
            return identity, zero_metrics
        H = self._homographies.get(frame_idx, identity)
        return H, _h_to_metrics(H)

    # ------------------------------------------------------------------ #
    # Single-frame estimation (used by unit tests / as fallback)          #
    # ------------------------------------------------------------------ #

    def estimate(
        self,
        current_frame: np.ndarray,
        vehicle_boxes: Optional[np.ndarray] = None,
    ) -> Tuple[np.ndarray, Dict[str, float]]:
        """
        Single-frame homography estimation: tracks goodFeaturesToTrack from the
        reference frame into *current_frame* via LK optical flow, then fits a
        3x3 RANSAC homography.

        Returns
        -------
        H_cur_to_ref : np.ndarray, shape (3, 3)
            Homography mapping current-frame coordinates to reference-frame
            coordinates.  Identity when estimation fails.
        metrics : dict
            ``dx``, ``dy``, ``angle_deg``, ``magnitude_px`` from the
            ref→cur forward homography.
        """
        identity = np.eye(3, dtype=np.float64)
        zero_metrics: Dict[str, float] = {
            "dx": 0.0,
            "dy": 0.0,
            "angle_deg": 0.0,
            "magnitude_px": 0.0,
        }

        if self._ref_kps is None or len(self._ref_kps) < self.min_features:
            return identity.copy(), zero_metrics

        curr_gray = self._prepare(current_frame)

        curr_kps, status, _ = cv2.calcOpticalFlowPyrLK(
            self._ref_gray, curr_gray, self._ref_kps, None
        )
        if curr_kps is None or status is None:
            return identity.copy(), zero_metrics

        status_flat = status.ravel().astype(bool)

        # Mask out vehicle regions
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

        # Fit 3x3 homography at scaled resolution (src=ref, dst=curr)
        H_small, hmask = cv2.findHomography(
            src_pts, dst_pts,
            cv2.RANSAC, 3.0,
            maxIters=2000, confidence=0.99,
        )
        if H_small is None:
            return identity.copy(), zero_metrics
        if hmask is not None and int(hmask.sum()) < self.min_features:
            return identity.copy(), zero_metrics

        # Convert to full-resolution homography
        H_ref_to_cur = _scale_homography(H_small, 1.0 / self.scale)
        metrics = _h_to_metrics(H_ref_to_cur)

        # Invert to get cur→ref (for zone membership tests)
        try:
            H_cur_to_ref = np.linalg.inv(H_ref_to_cur)
        except np.linalg.LinAlgError:
            return identity.copy(), metrics

        return H_cur_to_ref, metrics

    # ------------------------------------------------------------------ #
    # Transform helpers (public static)                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def transform_point(
        pt: Tuple[float, float],
        M: np.ndarray,
    ) -> Tuple[int, int]:
        """
        Apply a 3x3 homography or 2x3 affine matrix to a single point.

        Supports both shapes for backward compatibility with code that
        still uses the old 2x3 affine API.

        Returns
        -------
        (x', y') rounded to integer pixel coordinates.
        """
        x, y = float(pt[0]), float(pt[1])
        M = np.asarray(M, dtype=np.float64)
        if M.shape == (3, 3):
            p = M @ np.array([x, y, 1.0], dtype=np.float64)
            w = p[2]
            if abs(w) < 1e-10:
                return (int(round(p[0])), int(round(p[1])))
            return (int(round(p[0] / w)), int(round(p[1] / w)))
        # 2x3 affine (legacy)
        xn = M[0, 0] * x + M[0, 1] * y + M[0, 2]
        yn = M[1, 0] * x + M[1, 1] * y + M[1, 2]
        return (int(round(xn)), int(round(yn)))

    @staticmethod
    def transform_polygon(
        polygon: np.ndarray,
        M: np.ndarray,
    ) -> np.ndarray:
        """
        Apply a 3x3 homography or 2x3 affine matrix to every vertex of
        *polygon*.

        Parameters
        ----------
        polygon:
            Array of shape (N, 2) or (N, 1, 2) with point coordinates.
        M:
            3x3 homography or 2x3 affine matrix.

        Returns
        -------
        Transformed polygon as (N, 1, 2) int32 array.
        """
        M = np.asarray(M, dtype=np.float64)
        pts = polygon.reshape(-1, 1, 2).astype(np.float64)
        if M.shape == (3, 3):
            result = cv2.perspectiveTransform(pts, M)
            return np.round(result).astype(np.int32)
        # 2x3 affine (legacy)
        pts_flat = pts.reshape(-1, 2)
        ones = np.ones((len(pts_flat), 1), dtype=np.float64)
        pts_h = np.hstack([pts_flat, ones])
        transformed = (M @ pts_h.T).T
        return np.round(transformed).astype(np.int32).reshape(-1, 1, 2)

    @staticmethod
    def invert_transform(M: np.ndarray) -> np.ndarray:
        """
        Invert a 3x3 homography or 2x3 affine transform.

        Parameters
        ----------
        M:
            3x3 homography or 2x3 affine.

        Returns
        -------
        Inverse transform of the same shape convention.
        """
        M = np.asarray(M, dtype=np.float64)
        if M.shape == (3, 3):
            return np.linalg.inv(M)
        return cv2.invertAffineTransform(M)

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
        """Detect good features to track in *gray* (scaled grayscale)."""
        return cv2.goodFeaturesToTrack(
            gray,
            maxCorners=self.max_corners,
            qualityLevel=self.quality_level,
            minDistance=self.min_distance,
            mask=mask,
            blockSize=3,
        )

    def _match_to_reference(
        self,
        ref_gray: np.ndarray,
        curr_gray: np.ndarray,
        min_features: int = 8,
    ) -> Optional[np.ndarray]:
        """
        ORB feature matching between reference and current frame.

        Returns the 3x3 homography H_ref_to_curr at scaled resolution,
        or None if insufficient matches.
        """
        orb = cv2.ORB_create(nfeatures=1000)
        kp_ref, des_ref = orb.detectAndCompute(ref_gray, None)
        kp_curr, des_curr = orb.detectAndCompute(curr_gray, None)

        if des_ref is None or des_curr is None:
            return None
        if len(kp_ref) < min_features or len(kp_curr) < min_features:
            return None

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des_ref, des_curr)

        if len(matches) < min_features:
            return None

        matches = sorted(matches, key=lambda m: m.distance)[: min(200, len(matches))]
        src_pts = np.float32(
            [kp_ref[m.queryIdx].pt for m in matches]
        ).reshape(-1, 1, 2)
        dst_pts = np.float32(
            [kp_curr[m.trainIdx].pt for m in matches]
        ).reshape(-1, 1, 2)

        H, hmask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 3.0)
        if H is None or hmask is None or int(hmask.sum()) < min_features:
            return None

        return H

    def _build_vehicle_mask(
        self,
        gray_shape: Tuple[int, int],
        vehicle_boxes: np.ndarray,
    ) -> np.ndarray:
        """
        Build a uint8 mask (255 = usable, 0 = vehicle region) at scaled
        resolution so that tracked features inside vehicle bounding boxes
        are rejected during single-frame estimation.
        """
        h, w = gray_shape
        mask = np.full((h, w), 255, dtype=np.uint8)
        for box in vehicle_boxes:
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            x1s = max(0, int(x1 * self.scale))
            y1s = max(0, int(y1 * self.scale))
            x2s = min(w, int(x2 * self.scale))
            y2s = min(h, int(y2 * self.scale))
            if x2s > x1s and y2s > y1s:
                mask[y1s:y2s, x1s:x2s] = 0
        return mask
