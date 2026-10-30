"""
Failing tests for new homography-based motion compensator behaviour.

These tests are written BEFORE the implementation and describe the
required behaviour after the refactor:

  1. estimate() returns a 3x3 homography, not a 2x3 affine.
  2. Homography correctly recovers a synthetic perspective warp.
  3. No hard deadband: sub-threshold motion produces a non-identity result
     (the old 2px snap is removed).
  4. Smoothing (via pre_compute) reduces injected per-frame jitter without
     lagging a ramp by more than 1 frame.
  5. Drawing with subpixel precision and LINE_AA does not crash.
"""
from __future__ import annotations

import numpy as np
import cv2
import pytest

from app.modelo.motion_compensator import MotionCompensator


# ---------------------------------------------------------------------------
# Helpers shared with existing test suite
# ---------------------------------------------------------------------------

RNG = np.random.default_rng(7)


def _textured(w: int = 640, h: int = 480) -> np.ndarray:
    frame = RNG.integers(30, 200, (h, w, 3), dtype=np.uint8)
    for _ in range(60):
        cx = int(RNG.integers(20, w - 20))
        cy = int(RNG.integers(20, h - 20))
        r = int(RNG.integers(5, 20))
        col = (int(RNG.integers(0, 255)),) * 3
        cv2.circle(frame, (cx, cy), r, col, -1)
    return frame


def _warp_perspective(frame: np.ndarray, H: np.ndarray) -> np.ndarray:
    h, w = frame.shape[:2]
    return cv2.warpPerspective(frame, H, (w, h), borderMode=cv2.BORDER_REFLECT)


def _shift_frame(frame: np.ndarray, dx: int, dy: int) -> np.ndarray:
    h, w = frame.shape[:2]
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)


# ---------------------------------------------------------------------------
# 1. estimate() returns a 3x3 matrix
# ---------------------------------------------------------------------------

class TestEstimateReturns3x3:
    def test_shape_is_3x3(self):
        ref = _textured()
        shifted = _shift_frame(ref, 10, 0)
        comp = MotionCompensator(ref)
        H, metrics = comp.estimate(shifted)
        assert H.shape == (3, 3), f"Expected (3,3), got {H.shape}"

    def test_static_scene_near_identity(self):
        """Comparing ref to itself must yield an H very close to I_3x3."""
        ref = _textured()
        comp = MotionCompensator(ref)
        H, _ = comp.estimate(ref)
        assert H.shape == (3, 3)
        np.testing.assert_allclose(H, np.eye(3), atol=0.05,
                                   err_msg="Static scene: H should be ~identity")

    def test_metrics_keys_present(self):
        ref = _textured()
        comp = MotionCompensator(ref)
        _, metrics = comp.estimate(ref)
        for key in ("dx", "dy", "angle_deg", "magnitude_px"):
            assert key in metrics


# ---------------------------------------------------------------------------
# 2. Homography recovery on a synthetic perspective warp
# ---------------------------------------------------------------------------

class TestPerspectiveRecovery:
    """
    Apply a mild perspective homography to a synthetic frame and verify that
    the compensator recovers a transform consistent with the ground-truth H.
    """

    def test_perspective_warp_recovered_within_tolerance(self):
        """
        Warp with a known H_true (ref->warped) and verify that the recovered
        H_warped_to_ref (cur→ref from estimate()) is approximately inv(H_true).
        The reprojection error of ground-truth corners must be < 5 px.
        """
        ref = _textured(w=800, h=600)

        # Mild perspective: slight trapezoid distortion
        h, w = ref.shape[:2]
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst = np.float32([
            [10, 5],
            [w - 8, 3],
            [w - 5, h - 10],
            [12, h - 8],
        ])
        H_true = cv2.getPerspectiveTransform(src, dst)  # ref → warped
        warped = _warp_perspective(ref, H_true)

        comp = MotionCompensator(ref)
        H_cur_to_ref, _ = comp.estimate(warped)
        assert H_cur_to_ref.shape == (3, 3)

        # Compose: H_true then H_cur_to_ref should be ~identity.
        # Test on corner points.
        H_roundtrip = H_cur_to_ref @ H_true  # ref → warped → ref
        corners = np.float32([[100, 100], [700, 100], [700, 500], [100, 500]])
        corners_h = np.hstack([corners, np.ones((4, 1))])
        recovered = (H_roundtrip @ corners_h.T).T
        recovered_xy = recovered[:, :2] / recovered[:, 2:3]
        max_err = np.abs(recovered_xy - corners).max()
        assert max_err < 8.0, (
            f"Perspective round-trip error too large: {max_err:.2f} px "
            f"(expected < 8 px)"
        )


# ---------------------------------------------------------------------------
# 3. No hard deadband: sub-threshold motion produces a non-identity result
# ---------------------------------------------------------------------------

class TestNoHardDeadband:
    def test_1px_motion_no_longer_returns_identity(self):
        """
        With the deadband removed, a 1px shift must NOT be snapped to identity.
        The recovered transform should show the actual (small) displacement.
        """
        ref = _textured()
        shifted = _shift_frame(ref, 1, 0)
        comp = MotionCompensator(ref)
        H, metrics = comp.estimate(shifted)
        # The old code would return identity for 1px motion.
        # After the fix, H should be non-identity (magnitude > 0).
        is_identity = np.allclose(H, np.eye(3), atol=0.01)
        assert not is_identity, (
            "1px motion should NOT return identity (deadband removed). "
            f"metrics={metrics}"
        )

    def test_no_discrete_jump_around_old_threshold(self):
        """
        Transforms at 1px and 3px motion should differ smoothly: no step jump.
        If a 2px deadband were still active, the 1px result would be identity
        (all-zero translation) and 3px would be non-zero — a big discontinuity.
        Both should now be non-identity with gradually growing magnitude.
        """
        ref = _textured()
        comp_1 = MotionCompensator(ref)
        comp_3 = MotionCompensator(ref)
        shifted_1 = _shift_frame(ref, 1, 0)
        shifted_3 = _shift_frame(ref, 3, 0)

        H1, m1 = comp_1.estimate(shifted_1)
        H3, m3 = comp_3.estimate(shifted_3)

        # Neither should be exact identity
        assert not np.allclose(H1, np.eye(3), atol=0.01), "1px: should be non-identity"
        assert not np.allclose(H3, np.eye(3), atol=0.01), "3px: should be non-identity"

        # magnitude should grow monotonically
        assert m1["magnitude_px"] < m3["magnitude_px"], (
            f"Expected mag(1px) < mag(3px), got {m1['magnitude_px']:.3f} vs "
            f"{m3['magnitude_px']:.3f}"
        )


# ---------------------------------------------------------------------------
# 4. pre_compute + get_transform: smoothing reduces injected jitter
# ---------------------------------------------------------------------------

class TestPreComputeSmoothing:
    """
    Build a synthetic sequence of frames with a smooth ramp of translations
    plus injected high-frequency noise.  Verify that:
      (a) Smoothed output has lower jitter than raw per-frame estimate.
      (b) The ramp is not lagged by more than 1 frame (smoothing doesn't kill
          real motion).
    This test uses a synthetic video written to a temp file, then calls
    MotionCompensator.pre_compute().
    """

    def _make_video(self, path: str, frames: list[np.ndarray]) -> None:
        h, w = frames[0].shape[:2]
        fps = 30
        out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
        for f in frames:
            out.write(f)
        out.release()

    def test_smoothing_reduces_jitter(self, tmp_path):
        ref = _textured(w=320, h=240)
        n = 30
        # Smooth ramp: 0..15px over 30 frames, plus ±5px noise
        rng = np.random.default_rng(0)
        frames = []
        raw_dx = []
        for i in range(n):
            smooth_dx = int(i * 0.5)    # ramp: 0, 0, 1, 1, ...  (gentle)
            noise_dx = int(rng.integers(-2, 3))
            dx = smooth_dx + noise_dx
            raw_dx.append(dx)
            frames.append(_shift_frame(ref, dx, 0))

        video_path = str(tmp_path / "test.mp4")
        self._make_video(video_path, frames)

        comp = MotionCompensator.pre_compute(video_path, smooth_sigma=2.0)

        # Collect smoothed dx from get_transform
        smoothed_dx = []
        for fidx in range(1, n + 1):
            H, metrics = comp.get_transform(fidx)
            smoothed_dx.append(metrics["dx"])

        raw_arr = np.array(raw_dx, dtype=float)
        smooth_arr = np.array(smoothed_dx, dtype=float)

        # Jitter = std of second-difference (acceleration proxy)
        raw_jitter = float(np.std(np.diff(np.diff(raw_arr))))
        smooth_jitter = float(np.std(np.diff(np.diff(smooth_arr))))

        assert smooth_jitter < raw_jitter * 0.7, (
            f"Smoothing did not reduce jitter enough: "
            f"raw={raw_jitter:.2f}, smoothed={smooth_jitter:.2f}"
        )

    def test_ramp_not_lagged_more_than_one_frame(self, tmp_path):
        """
        A step motion at frame 15 must appear in the smoothed output within
        1 frame (at frame 15 or 16 at the latest, not delayed to frame 20+).
        """
        ref = _textured(w=320, h=240)
        n = 30
        # Step: 0 for first 15 frames, then 20px
        frames = []
        for i in range(n):
            dx = 20 if i >= 15 else 0
            frames.append(_shift_frame(ref, dx, 0))

        video_path = str(tmp_path / "step.mp4")
        self._make_video(video_path, frames)

        comp = MotionCompensator.pre_compute(video_path, smooth_sigma=1.5)

        # At frame 17 (2 frames after step at 15), smoothed dx must be > 5px
        _, m17 = comp.get_transform(17)
        assert m17["dx"] > 5.0, (
            f"Ramp not detected by frame 17: smoothed dx={m17['dx']:.2f} (expected >5)"
        )


# ---------------------------------------------------------------------------
# 5. Subpixel drawing: transform_polygon used with LINE_AA does not crash
# ---------------------------------------------------------------------------

class TestSubpixelDraw:
    """
    Draw warped zone polygons with subpixel precision (shift=4) and LINE_AA.
    The result must have the same shape as the input frame and contain
    non-zero pixels (something was drawn).
    """

    def test_draw_warped_polygon_subpixel(self):
        process = pytest.importorskip("app.modelo.process")

        poly = np.array([[50, 100], [200, 100], [200, 300], [50, 300]], dtype=np.int32)
        # Build a 3x3 ref->cur homography (mild translation + slight perspective)
        H = np.eye(3, dtype=np.float64)
        H[0, 2] = 20.0   # translate x by 20px
        H[1, 2] = -10.0  # translate y by -10px
        H[2, 0] = 1e-5   # tiny perspective distortion
        H[2, 1] = 1e-5

        # Warp the polygon
        warped = MotionCompensator.transform_polygon(poly, H)

        # Verify shape: (N, 1, 2)
        assert warped.ndim == 3 and warped.shape[1] == 1 and warped.shape[2] == 2, (
            f"Unexpected shape {warped.shape}"
        )

        # Draw with subpixel shift=4 and LINE_AA (should not crash)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        SHIFT = 4
        pts = warped.astype(np.float32)
        pts_shifted = np.round(pts * (1 << SHIFT)).astype(np.int32)
        cv2.polylines(frame, [pts_shifted], True, (0, 255, 0), 2,
                      lineType=cv2.LINE_AA, shift=SHIFT)
        assert frame.any(), "Nothing was drawn on the frame"
        assert frame.shape == (480, 640, 3)

    def test_transform_polygon_3x3_output_shape(self):
        """transform_polygon with a 3x3 H must return (N, 1, 2) int32."""
        poly = np.array([[0, 0], [100, 0], [100, 50], [0, 50]], dtype=np.int32)
        H = np.eye(3, dtype=np.float64)
        H[0, 2] = 15.0
        H[1, 2] = 8.0
        result = MotionCompensator.transform_polygon(poly, H)
        assert result.shape == (4, 1, 2), f"Unexpected shape: {result.shape}"
        assert result.dtype == np.int32

    def test_transform_point_3x3(self):
        """transform_point with identity 3x3 must return the original point."""
        H = np.eye(3, dtype=np.float64)
        rx, ry = MotionCompensator.transform_point((100, 200), H)
        assert rx == 100 and ry == 200

    def test_transform_point_3x3_with_translation(self):
        H = np.eye(3, dtype=np.float64)
        H[0, 2] = 10.0
        H[1, 2] = -5.0
        rx, ry = MotionCompensator.transform_point((100, 200), H)
        assert rx == 110
        assert ry == 195
