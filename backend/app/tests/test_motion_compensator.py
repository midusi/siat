"""
Unit tests for the MotionCompensator module.

All tests use purely synthetic frames (textured noise + solid shapes) so
they run without any video file or YOLO model.

Test coverage:
- Static scene  → identity transform
- Pure translation (known shift)  → recovered within ±TOL pixels
- Pure rotation (small angle)  → recovered within ±TOL_DEG degrees
- Vehicle blobs don't bias the translation estimate
- transform_point: identity and translation
- transform_polygon: translation applied to all vertices
- Below-deadband motion → identity returned
"""
import numpy as np
import cv2
import pytest

from app.modelo.motion_compensator import MotionCompensator


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

RNG = np.random.default_rng(42)

TRANSLATION_TOL_PX = 2.5   # accepted pixel error for recovered translation
ROTATION_TOL_DEG = 0.3     # accepted degree error for recovered rotation


def _textured_frame(w: int = 640, h: int = 480) -> np.ndarray:
    """
    Create a BGR frame with rich, reproducible random texture.
    Optical flow works well on textured images.
    """
    frame = RNG.integers(30, 200, (h, w, 3), dtype=np.uint8)
    # Add some strong gradient features so goodFeaturesToTrack finds corners.
    for _ in range(60):
        cx = int(RNG.integers(20, w - 20))
        cy = int(RNG.integers(20, h - 20))
        r = int(RNG.integers(5, 20))
        color = (int(RNG.integers(0, 255)), int(RNG.integers(0, 255)), int(RNG.integers(0, 255)))
        cv2.circle(frame, (cx, cy), r, color, -1)
    for _ in range(30):
        x1 = int(RNG.integers(0, w - 30))
        y1 = int(RNG.integers(0, h - 30))
        x2 = x1 + int(RNG.integers(10, 30))
        y2 = y1 + int(RNG.integers(10, 30))
        color = (int(RNG.integers(0, 255)), int(RNG.integers(0, 255)), int(RNG.integers(0, 255)))
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, -1)
    return frame


def _shift_frame(frame: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """Translate *frame* by (dx, dy) pixels using an affine warp."""
    h, w = frame.shape[:2]
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)


def _rotate_frame(frame: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate *frame* around its center by *angle_deg* degrees."""
    h, w = frame.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    M = cv2.getRotationMatrix2D((cx, cy), angle_deg, 1.0)
    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)


# --------------------------------------------------------------------------- #
# Tests                                                                       #
# --------------------------------------------------------------------------- #

class TestStaticScene:
    def test_identity_when_no_motion(self):
        """
        Comparing the reference frame to itself should yield a transform very
        close to identity (within the deadband, so we get back exactly the
        eye matrix).
        """
        ref = _textured_frame()
        comp = MotionCompensator(ref, deadband_px=2.0)
        M, metrics = comp.estimate(ref)
        # Should be identity (deadband collapses tiny numerical errors).
        assert M.shape == (2, 3)
        np.testing.assert_allclose(M, np.eye(2, 3), atol=0.05)
        assert metrics["magnitude_px"] < 2.0


class TestTranslationRecovery:
    @pytest.mark.parametrize("dx,dy", [
        (10, 0),
        (0, 10),
        (8, 6),
        (-12, 5),
        (0, -15),
    ])
    def test_pure_translation_recovered(self, dx, dy):
        """
        Shifting the frame by a known (dx, dy) should produce a recovered
        (dx, dy) within TRANSLATION_TOL_PX of the ground truth.

        Note: the camera moved (dx, dy) relative to the reference, so the
        compensator maps current → reference via a shift of (-dx, -dy) at
        full resolution.  We verify the forward motion magnitude & sign
        through the metrics dict (which reports reference→current shift).
        """
        ref = _textured_frame()
        shifted = _shift_frame(ref, dx, dy)
        comp = MotionCompensator(ref, deadband_px=1.0)
        M, metrics = comp.estimate(shifted)

        assert M.shape == (2, 3)
        # metrics reports the reference→current camera displacement.
        assert abs(metrics["dx"] - dx) <= TRANSLATION_TOL_PX, (
            f"dx: expected {dx}, got {metrics['dx']:.2f}"
        )
        assert abs(metrics["dy"] - dy) <= TRANSLATION_TOL_PX, (
            f"dy: expected {dy}, got {metrics['dy']:.2f}"
        )

    def test_compensated_point_lands_in_reference_frame(self):
        """
        A point P in the shifted frame should map back to P - (dx, dy)
        in the reference frame when the compensating transform M is applied.
        """
        dx, dy = 15, -8
        ref = _textured_frame()
        shifted = _shift_frame(ref, dx, dy)
        comp = MotionCompensator(ref, deadband_px=1.0)
        M, _ = comp.estimate(shifted)

        # A point in the current (shifted) frame.
        px, py = 200, 150
        rx, ry = MotionCompensator.transform_point((px, py), M)

        # In the reference frame this should be approximately px-dx, py-dy.
        assert abs(rx - (px - dx)) <= TRANSLATION_TOL_PX + 1
        assert abs(ry - (py - dy)) <= TRANSLATION_TOL_PX + 1


class TestRotationRecovery:
    @pytest.mark.parametrize("angle_deg", [1.5, -2.0, 3.0])
    def test_small_rotation_recovered(self, angle_deg):
        """
        A small rotation should be detected and reported within ROTATION_TOL_DEG.
        """
        ref = _textured_frame(w=800, h=600)
        rotated = _rotate_frame(ref, angle_deg)
        comp = MotionCompensator(ref, deadband_px=1.0)
        _, metrics = comp.estimate(rotated)

        # The reported angle is reference→current (same sign as the warp).
        assert abs(metrics["angle_deg"] - angle_deg) <= ROTATION_TOL_DEG, (
            f"angle: expected {angle_deg}, got {metrics['angle_deg']:.3f}"
        )


class TestVehicleMasking:
    def test_vehicle_blobs_do_not_bias_translation(self):
        """
        Add bright "vehicle" blobs in the shifted frame at arbitrary positions.
        The masking mechanism should exclude those regions and still recover
        the correct translation.
        """
        dx, dy = 9, -7
        ref = _textured_frame()
        shifted = _shift_frame(ref, dx, dy)

        # Paint large, high-contrast blobs where "vehicles" would appear.
        blob_boxes = np.array([
            [50, 50, 200, 150],   # left region
            [400, 300, 550, 420], # right-bottom region
        ], dtype=np.float32)
        for box in blob_boxes:
            x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
            shifted[y1:y2, x1:x2] = 255  # white: maximally different from reference

        comp = MotionCompensator(ref, deadband_px=1.0)
        _, metrics = comp.estimate(shifted, vehicle_boxes=blob_boxes)

        assert abs(metrics["dx"] - dx) <= TRANSLATION_TOL_PX, (
            f"dx: expected {dx}, got {metrics['dx']:.2f} (vehicle masking failed?)"
        )
        assert abs(metrics["dy"] - dy) <= TRANSLATION_TOL_PX, (
            f"dy: expected {dy}, got {metrics['dy']:.2f} (vehicle masking failed?)"
        )


class TestDeadbandBehavior:
    def test_sub_deadband_motion_returns_identity(self):
        """
        Motion below the deadband threshold should return an identity matrix.
        """
        ref = _textured_frame()
        # Very small shift (1 px) — below default deadband of 2.0 px.
        shifted = _shift_frame(ref, 1, 0)
        comp = MotionCompensator(ref, deadband_px=2.0)
        M, _ = comp.estimate(shifted)
        np.testing.assert_allclose(M, np.eye(2, 3), atol=0.05)

    def test_above_deadband_motion_not_identity(self):
        """
        Motion well above the deadband should return a non-identity matrix.
        """
        ref = _textured_frame()
        shifted = _shift_frame(ref, 20, 0)
        comp = MotionCompensator(ref, deadband_px=2.0)
        M, _ = comp.estimate(shifted)
        # Translation component should be non-zero.
        tx = M[0, 2]
        assert abs(tx) > 5.0, f"Expected non-zero tx, got {tx}"


class TestTransformHelpers:
    def test_transform_point_identity(self):
        M = np.eye(2, 3, dtype=np.float64)
        assert MotionCompensator.transform_point((100, 200), M) == (100, 200)

    def test_transform_point_translation(self):
        M = np.eye(2, 3, dtype=np.float64)
        M[0, 2] = 10.0  # shift x by +10
        M[1, 2] = -5.0  # shift y by -5
        rx, ry = MotionCompensator.transform_point((100, 200), M)
        assert rx == 110
        assert ry == 195

    def test_transform_polygon_identity(self):
        poly = np.array([[10, 20], [30, 40], [50, 60]], dtype=np.int32)
        M = np.eye(2, 3, dtype=np.float64)
        result = MotionCompensator.transform_polygon(poly, M)
        expected = poly.reshape(-1, 1, 2)
        np.testing.assert_array_equal(result, expected)

    def test_transform_polygon_translation(self):
        poly = np.array([[0, 0], [100, 0], [100, 50], [0, 50]], dtype=np.int32)
        M = np.eye(2, 3, dtype=np.float64)
        M[0, 2] = 20.0
        M[1, 2] = 10.0
        result = MotionCompensator.transform_polygon(poly, M)
        result_flat = result.reshape(-1, 2)
        expected = poly + np.array([20, 10])
        np.testing.assert_array_equal(result_flat, expected)

    def test_transform_polygon_accepts_various_shapes(self):
        """Polygon in (N,1,2) shape (OpenCV convention) should also work."""
        poly = np.array([[[10, 20]], [[30, 40]], [[50, 60]]], dtype=np.int32)
        M = np.eye(2, 3, dtype=np.float64)
        result = MotionCompensator.transform_polygon(poly, M)
        assert result.shape == (3, 1, 2)


class TestMetricsSchema:
    def test_metrics_always_has_required_keys(self):
        """estimate() must always return all four metric keys."""
        ref = _textured_frame()
        comp = MotionCompensator(ref)
        _, metrics = comp.estimate(ref)
        for key in ("dx", "dy", "angle_deg", "magnitude_px"):
            assert key in metrics, f"Missing metric key: {key}"

    def test_metrics_are_floats(self):
        ref = _textured_frame()
        comp = MotionCompensator(ref)
        _, metrics = comp.estimate(ref)
        for key, val in metrics.items():
            assert isinstance(val, float), f"{key} is not float: {type(val)}"
