import cv2
import numpy as np
import supervision as sv
from typing import List
from ..models import ZoneType

ZONE_COLORS = sv.ColorPalette.from_hex(["#00FF00", "#FF0000"])

def draw_polygon(annotated_frame: np.ndarray, polygon: np.ndarray, name_polygon: str, zone_type: ZoneType, thickness: int) -> np.ndarray:
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    
    color_idx = 0 if zone_type == ZoneType.ENTRY else 1
    color = ZONE_COLORS.colors[color_idx].as_bgr()
    
    cv2.polylines(annotated_frame, [polygon], isClosed=True, color=color, thickness=thickness)
    
    zone_center = sv.get_polygon_center(polygon=polygon)
    cv2.putText(annotated_frame, name_polygon, (int(zone_center.x), int(zone_center.y)), font, font_scale, color, thickness=thickness)
    
    return annotated_frame

def apply_exclusion_mask(frame: np.ndarray, excluded_polygons: List[np.ndarray]) -> np.ndarray:
    """Rellena con negro todas las zonas excluidas sobre el frame."""
    if not excluded_polygons:
        return frame
    overlay = frame.copy()
    for poly in excluded_polygons:
        pts = poly.reshape((-1, 1, 2))
        cv2.fillPoly(overlay, [pts], color=(0, 0, 0))
    return overlay
