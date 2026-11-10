"""
Pruebas unitarias para visualization/annotator.py.
Valida la aplicación de máscaras de exclusión y dibujo de polígonos sobre frames.
"""

import numpy as np
from siatlib.models import ZoneType
from siatlib.visualization import apply_exclusion_mask, draw_polygon


def test_apply_exclusion_mask_empty():
    """Valida que un frame sin zonas excluidas se retorne sin alteraciones."""
    frame = np.ones((100, 100, 3), dtype=np.uint8) * 255
    res = apply_exclusion_mask(frame, [])
    assert np.array_equal(frame, res)


def test_apply_exclusion_mask_blacks_out_polygon():
    """Valida que los píxeles dentro del polígono excluido sean pintados de negro (valor 0)."""
    frame = np.ones((100, 100, 3), dtype=np.uint8) * 255
    poly = np.array([[20, 20], [80, 20], [80, 80], [20, 80]], dtype=np.int32)

    masked = apply_exclusion_mask(frame, [poly])

    # El centro (50, 50) debe estar en negro (0, 0, 0)
    assert np.all(masked[50, 50] == 0)
    # Una esquina exterior (5, 5) debe mantenerse inalterada (255, 255, 255)
    assert np.all(masked[5, 5] == 255)


def test_draw_polygon_annotates_frame():
    """Valida que draw_polygon dibuje sobre el frame sin alterar sus dimensiones."""
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    poly = np.array([[10, 10], [100, 10], [100, 100], [10, 100]], dtype=np.int32)

    annotated = draw_polygon(frame, poly, "Entrada 1", ZoneType.ENTRY, thickness=2)

    assert annotated.shape == (200, 200, 3)
    # Al menos algunos píxeles en el área del dibujo no deben ser negros
    assert np.any(annotated > 0)

