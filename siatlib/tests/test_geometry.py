import numpy as np
from siatlib.spatial import get_center_bb, get_zone_index

def test_get_center_bb():
    box = np.array([10, 20, 30, 40])
    center = get_center_bb(box)
    assert center == (20, 30)

def test_get_zone_index_inside():
    # Square polygon from (0,0) to (100, 100)
    polygon = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.int32)
    # Box centered at (50, 50)
    box_inside = np.array([40, 40, 60, 60])
    
    idx = get_zone_index(box_inside, [polygon])
    assert idx == 0

def test_get_zone_index_outside():
    polygon = np.array([[0, 0], [100, 0], [100, 100], [0, 100]], dtype=np.int32)
    # Box centered at (200, 200)
    box_outside = np.array([190, 190, 210, 210])
    
    idx = get_zone_index(box_outside, [polygon])
    assert idx == -1
