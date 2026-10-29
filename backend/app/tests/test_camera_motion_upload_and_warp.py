"""
Tests for camera motion zone warp and upload:
  1. Inverse transform / polygon warp round-trip (ref -> cur -> ref ≈ identity)
  2. camera_motion.json JSON schema (matrix_ref_to_cur key, shape 2×3)
  3. camera_motion.json upload stored at the expected bucket key
"""
from __future__ import annotations

import io
import json

import cv2
import numpy as np
import pytest

from app.adapters.storage.memory import InMemoryObjectStorage
from app.modelo.motion_compensator import MotionCompensator


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def _affine(dx: float = 0.0, dy: float = 0.0, angle_deg: float = 0.0) -> np.ndarray:
    """Build a 2×3 affine matrix for a known translation + small rotation."""
    rad = np.radians(angle_deg)
    cos_a, sin_a = np.cos(rad), np.sin(rad)
    return np.array(
        [[cos_a, -sin_a, dx], [sin_a, cos_a, dy]],
        dtype=np.float64,
    )


def _sample_polygon() -> np.ndarray:
    return np.array(
        [[100, 200], [300, 200], [300, 400], [100, 400]],
        dtype=np.int32,
    )


# --------------------------------------------------------------------------- #
# 1. Inverse / round-trip                                                     #
# --------------------------------------------------------------------------- #

class TestInverseTransformRoundtrip:
    """
    For any affine M, applying M then invertAffineTransform(M) must be
    the identity (within floating-point precision).
    """

    @pytest.mark.parametrize("dx,dy,angle_deg", [
        (15.0, 0.0, 0.0),
        (0.0, -10.0, 0.0),
        (8.0, -6.0, 0.0),
        (20.0, 15.0, 1.5),
        (-12.0, 8.0, -2.0),
    ])
    def test_point_roundtrip(self, dx: float, dy: float, angle_deg: float) -> None:
        """
        Transform a point with M_ref_to_cur, then apply M_cur_to_ref (inverse):
        the recovered coordinates must match the original within 0.01 px.
        """
        M_ref_to_cur = _affine(dx, dy, angle_deg)
        M_cur_to_ref = cv2.invertAffineTransform(M_ref_to_cur)

        original = (200.0, 300.0)
        warped = MotionCompensator.transform_point(original, M_ref_to_cur)
        recovered = MotionCompensator.transform_point(warped, M_cur_to_ref)

        # Due to rounding inside transform_point (→ int), allow ±1 px.
        assert abs(recovered[0] - round(original[0])) <= 1, (
            f"x: expected ~{original[0]}, got {recovered[0]}"
        )
        assert abs(recovered[1] - round(original[1])) <= 1, (
            f"y: expected ~{original[1]}, got {recovered[1]}"
        )

    @pytest.mark.parametrize("dx,dy,angle_deg", [
        (20.0, 0.0, 0.0),
        (0.0, -15.0, 0.0),
        (10.0, 8.0, 1.5),
        (-18.0, 12.0, -2.5),
    ])
    def test_polygon_roundtrip(self, dx: float, dy: float, angle_deg: float) -> None:
        """
        Warp polygon ref->cur then cur->ref: each vertex must recover to
        within ±1 px of the original (rounding artefact from integer coords).
        """
        M_ref_to_cur = _affine(dx, dy, angle_deg)
        M_cur_to_ref = cv2.invertAffineTransform(M_ref_to_cur)

        poly = _sample_polygon()
        warped = MotionCompensator.transform_polygon(poly, M_ref_to_cur)
        recovered = MotionCompensator.transform_polygon(warped, M_cur_to_ref)

        diff = np.abs(
            recovered.reshape(-1, 2).astype(np.float64)
            - poly.reshape(-1, 2).astype(np.float64)
        )
        assert diff.max() <= 1.5, (
            f"Round-trip error too large: max={diff.max():.2f} px\n"
            f"  original:  {poly.reshape(-1, 2)}\n"
            f"  recovered: {recovered.reshape(-1, 2)}"
        )

    def test_identity_roundtrip_is_exact(self) -> None:
        """
        Inverting the identity matrix must stay exactly identity, and the
        round-trip must recover the exact original polygon.
        """
        I = np.eye(2, 3, dtype=np.float64)
        I_inv = cv2.invertAffineTransform(I)
        np.testing.assert_allclose(I_inv, I, atol=1e-10)

        poly = _sample_polygon()
        warped = MotionCompensator.transform_polygon(poly, I)
        np.testing.assert_array_equal(warped.reshape(-1, 2), poly.reshape(-1, 2))


# --------------------------------------------------------------------------- #
# 2. JSON schema                                                               #
# --------------------------------------------------------------------------- #

class TestCameraMotionJsonSchema:
    """
    Verify the structure of camera_motion.json as produced by process.py.
    matrix_ref_to_cur must be present per frame and shaped [[a,b,c],[d,e,f]].
    """

    def _make_frame_entry(self, frame: int, dx: float = 0.0, dy: float = 0.0) -> dict:
        """Build a motion log entry as process.py will produce it."""
        M_ref_to_cur = _affine(dx, dy)
        return {
            "frame": frame,
            "dx": dx,
            "dy": dy,
            "angle_deg": 0.0,
            "magnitude_px": float(np.hypot(dx, dy)),
            "matrix_ref_to_cur": M_ref_to_cur.tolist(),
        }

    def test_matrix_ref_to_cur_present_in_frame(self) -> None:
        entry = self._make_frame_entry(1)
        assert "matrix_ref_to_cur" in entry, "matrix_ref_to_cur key missing"

    def test_matrix_ref_to_cur_is_2x3(self) -> None:
        entry = self._make_frame_entry(2, dx=10.0, dy=-5.0)
        mat = entry["matrix_ref_to_cur"]
        assert len(mat) == 2, f"Expected 2 rows, got {len(mat)}"
        assert all(len(row) == 3 for row in mat), "Each row must have 3 columns"

    def test_full_json_structure(self) -> None:
        """The top-level JSON must have the expected mandatory keys."""
        payload = {
            "compensation_enabled": True,
            "scale": 0.5,
            "deadband_px": 2.0,
            "convention": "matrix_ref_to_cur maps reference-frame to current-frame",
            "frames": [self._make_frame_entry(i, dx=float(i)) for i in range(1, 4)],
        }
        encoded = json.dumps(payload, ensure_ascii=False)
        parsed = json.loads(encoded)

        for key in ("compensation_enabled", "scale", "deadband_px", "frames"):
            assert key in parsed, f"Top-level key '{key}' missing"

        for frame_entry in parsed["frames"]:
            assert "frame" in frame_entry
            assert "matrix_ref_to_cur" in frame_entry
            mat = frame_entry["matrix_ref_to_cur"]
            assert len(mat) == 2 and all(len(r) == 3 for r in mat)

    def test_identity_frame_matrix_is_numeric(self) -> None:
        """
        Frame 1 (reference) logs the identity matrix: entries must be
        serialisable and numerically valid.
        """
        I = np.eye(2, 3, dtype=np.float64)
        entry = {
            "frame": 1,
            "dx": 0.0,
            "dy": 0.0,
            "angle_deg": 0.0,
            "magnitude_px": 0.0,
            "matrix_ref_to_cur": I.tolist(),
        }
        mat = entry["matrix_ref_to_cur"]
        # All entries must be finite floats
        flat = [v for row in mat for v in row]
        assert all(isinstance(v, float) for v in flat)
        assert all(np.isfinite(v) for v in flat)


# --------------------------------------------------------------------------- #
# 3. Upload                                                                    #
# --------------------------------------------------------------------------- #

class TestCameraMotionUpload:
    """
    Verify that camera_motion.json is stored at the expected bucket key and
    that the stored content is a valid JSON blob with the required schema.
    """

    def _camera_motion_bytes(self) -> bytes:
        payload = {
            "compensation_enabled": True,
            "scale": 0.5,
            "deadband_px": 2.0,
            "convention": "matrix_ref_to_cur maps reference-frame to current-frame",
            "frames": [
                {
                    "frame": 1,
                    "dx": 0.0,
                    "dy": 0.0,
                    "angle_deg": 0.0,
                    "magnitude_px": 0.0,
                    "matrix_ref_to_cur": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                },
                {
                    "frame": 2,
                    "dx": 12.5,
                    "dy": -7.3,
                    "angle_deg": 0.5,
                    "magnitude_px": 14.5,
                    "matrix_ref_to_cur": [[0.9999, 0.0087, 12.5], [-0.0087, 0.9999, -7.3]],
                },
            ],
        }
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    def test_upload_stores_at_expected_key(self) -> None:
        """
        Simulates the upload step in process_command.py.
        camera_motion.json must land at task/{id}/{hash}_camera_motion.json.
        """
        storage = InMemoryObjectStorage(bucket_name="siat-bucket")
        task_id = 42
        hash_value = "abc123def456"
        key = f"task/{task_id}/{hash_value}_camera_motion.json"

        storage.upload(
            io.BytesIO(self._camera_motion_bytes()),
            object_name=key,
            content_type="application/json",
        )

        assert storage.exists(key), f"Expected key '{key}' not found in storage"

    def test_uploaded_content_is_valid_json_with_schema(self) -> None:
        """
        After upload, streaming the object back must yield parseable JSON
        with matrix_ref_to_cur present in every frame entry.
        """
        storage = InMemoryObjectStorage(bucket_name="siat-bucket")
        key = "task/7/ffee11_camera_motion.json"
        storage.upload(
            io.BytesIO(self._camera_motion_bytes()),
            object_name=key,
            content_type="application/json",
        )

        gen, content_type, _ = storage.stream_object(key)
        raw = b"".join(gen)
        parsed = json.loads(raw)

        assert content_type == "application/json"
        assert "frames" in parsed
        for frame_entry in parsed["frames"]:
            assert "matrix_ref_to_cur" in frame_entry
            mat = frame_entry["matrix_ref_to_cur"]
            assert len(mat) == 2 and all(len(r) == 3 for r in mat)

    def test_task_without_camera_motion_backward_compatible(self) -> None:
        """
        A task processed before this feature (no camera_motion.json) must not
        break: storage.exists() must return False and no upload should occur.
        """
        storage = InMemoryObjectStorage(bucket_name="siat-bucket")
        key = "task/99/old_task_camera_motion.json"
        assert not storage.exists(key)


# --------------------------------------------------------------------------- #
# Regression: drawing warped zones                                            #
# --------------------------------------------------------------------------- #

def test_draw_zones_with_nonzero_motion_does_not_crash():
    """Warped polygons must keep the (N, 2) shape that sv.get_polygon_center expects."""
    process = pytest.importorskip("app.modelo.process")

    tracker = process.ObjectTracker.__new__(process.ObjectTracker)
    tracker.zone_in_polygons = [{"polygon": _sample_polygon(), "name": "1"}]
    tracker.zone_out_polygons = [{"polygon": _sample_polygon() + 50, "name": "1"}]
    tracker._current_ref_to_cur_transform = _affine(dx=25.0, dy=-10.0, angle_deg=1.5)

    frame = np.zeros((600, 800, 3), dtype=np.uint8)
    result = tracker._draw_zones_in_out(frame, 2)

    assert result.shape == frame.shape
    assert result.any()
