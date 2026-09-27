import cv2
import numpy as np
from typing import Tuple, List

def get_center_bb(box: np.ndarray) -> Tuple[int, int]:
    """Calcula el punto central de un bounding box."""
    x_center = int((box[0] + box[2]) / 2)
    y_center = int((box[1] + box[3]) / 2)
    return (x_center, y_center)

def get_zone_index(box: np.ndarray, polygons: List[np.ndarray]) -> int:
    """Detecta si el centro de un bounding box está dentro de alguno de los polígonos."""
    center = get_center_bb(box)
    for i, polygon in enumerate(polygons):
        if cv2.pointPolygonTest(polygon, center, False) > 0:
            return i
    return -1
