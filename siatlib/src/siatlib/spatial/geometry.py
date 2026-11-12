import cv2
import numpy as np
from typing import List, Optional, Tuple

from .motion_compensator import MotionCompensator


def get_center_bb(box: np.ndarray) -> Tuple[int, int]:
    """Calcula el punto central de un bounding box."""
    x_center = int((box[0] + box[2]) / 2)
    y_center = int((box[1] + box[3]) / 2)
    return (x_center, y_center)


def get_zone_index(
    box: np.ndarray,
    polygons: List[np.ndarray],
    motion_transform: Optional[np.ndarray] = None,
) -> int:
    """
    Detecta si el centro de un bounding box está dentro de alguno de los polígonos.

    Si se provee ``motion_transform`` (homografía 3x3 o afín 2x3 que mapea
    coordenadas del frame actual al frame de referencia), el centro se remapea
    antes del test, de modo que los polígonos definidos sobre el frame de
    referencia sigan siendo válidos aunque la cámara se mueva.
    """
    center = get_center_bb(box)
    if motion_transform is not None:
        center = MotionCompensator.transform_point(center, motion_transform)
    for i, polygon in enumerate(polygons):
        if cv2.pointPolygonTest(polygon, center, False) > 0:
            return i
    return -1
