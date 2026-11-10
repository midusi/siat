"""
Pruebas unitarias para el submódulo spatial (geometry.py).
Valida cálculos geométricos espaciales, centroides y pertenencia a zonas poligonales.
"""

import numpy as np
from siatlib.spatial import get_center_bb, get_zone_index


def test_get_center_bb():
    """Valida el cálculo del punto central (x_center, y_center) de un bounding box [x1, y1, x2, y2]."""
    box = np.array([10, 20, 30, 40])
    center = get_center_bb(box)
    assert center == (20, 30)


def test_get_zone_index_inside():
    """Valida que un bounding box cuyo centroide cae dentro del polígono retorne el índice correcto de la zona."""
    # Polígono cuadrado de (0,0) a (100, 100)
    polygon = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.int32)
    # Bounding box centrado en (50, 50)
    box_inside = np.array([40, 40, 60, 60])

    idx = get_zone_index(box_inside, [polygon])
    assert idx == 0


def test_get_zone_index_outside():
    """Valida que un bounding box exterior a todos los polígonos retorne -1."""
    polygon = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.int32)
    # Bounding box centrado en (200, 200)
    box_outside = np.array([190, 190, 210, 210])

    idx = get_zone_index(box_outside, [polygon])
    assert idx == -1


def test_get_zone_index_multiple_zones():
    """Valida la detección correcta cuando existen múltiples zonas adyacentes."""
    poly_0 = np.array([[0, 0], [50, 0], [50, 50], [0, 50]], dtype=np.int32)
    poly_1 = np.array([[60, 0], [110, 0], [110, 50], [60, 50]], dtype=np.int32)

    # Box centrado en (85, 25) -> dentro de poly_1
    box = np.array([80, 20, 90, 30])
    idx = get_zone_index(box, [poly_0, poly_1])
    assert idx == 1

