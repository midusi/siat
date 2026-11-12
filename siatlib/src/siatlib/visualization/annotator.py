import cv2
import numpy as np
import supervision as sv
from typing import List, Optional
from ..models import ZoneType
from ..spatial.motion_compensator import MotionCompensator

ZONE_COLORS = sv.ColorPalette.from_hex(["#00FF00", "#FF0000"])

# Precisión subpíxel para el dibujo de polígonos (shift=4 → 1/16 px).
_SUBPIXEL_SHIFT = 4


def needs_warp(ref_to_cur: Optional[np.ndarray]) -> bool:
    """Indica si la transformación ref→actual difiere de la identidad."""
    if ref_to_cur is None:
        return False
    if ref_to_cur.shape == (3, 3):
        return not np.allclose(ref_to_cur, np.eye(3))
    return not np.allclose(ref_to_cur, np.eye(2, 3))


def warp_polygon(polygon: np.ndarray, ref_to_cur: Optional[np.ndarray]) -> np.ndarray:
    """Lleva un polígono de coordenadas de referencia a coordenadas del frame actual, como (N, 2)."""
    if not needs_warp(ref_to_cur):
        return polygon
    return MotionCompensator.transform_polygon(polygon, ref_to_cur).reshape(-1, 2)


def draw_polygon(annotated_frame: np.ndarray, polygon: np.ndarray, name_polygon: str, zone_type: ZoneType, thickness: int) -> np.ndarray:
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1

    color_idx = 0 if zone_type in (ZoneType.ENTRY, ZoneType.IN) else 1
    color = ZONE_COLORS.colors[color_idx].as_bgr()

    pts = polygon.reshape(-1, 1, 2).astype(np.float32)
    pts_shifted = np.round(pts * (1 << _SUBPIXEL_SHIFT)).astype(np.int32)
    cv2.polylines(
        annotated_frame,
        [pts_shifted],
        isClosed=True,
        color=color,
        thickness=thickness,
        lineType=cv2.LINE_AA,
        shift=_SUBPIXEL_SHIFT,
    )

    zone_center = sv.get_polygon_center(polygon=polygon.reshape(-1, 2))
    cv2.putText(annotated_frame, name_polygon, (int(zone_center.x), int(zone_center.y)), font, font_scale, color, thickness=thickness)

    return annotated_frame


def apply_exclusion_mask(
    frame: np.ndarray,
    excluded_polygons: List[np.ndarray],
    ref_to_cur: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Rellena con negro todas las zonas excluidas sobre el frame.

    Los polígonos están en coordenadas del frame de referencia; si se provee
    ``ref_to_cur`` se deforman al frame actual para que la máscara siga a la
    región física aunque la cámara se mueva.
    """
    if not excluded_polygons:
        return frame
    overlay = frame.copy()
    warp = needs_warp(ref_to_cur)
    for poly in excluded_polygons:
        if warp:
            pts = MotionCompensator.transform_polygon(poly, ref_to_cur)
        else:
            pts = poly.reshape((-1, 1, 2))
        cv2.fillPoly(overlay, [pts], color=(0, 0, 0))
    return overlay
