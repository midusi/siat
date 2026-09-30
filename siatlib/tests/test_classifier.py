from collections import Counter
from siatlib.analytics import calculate_entropy, classify_track

def test_calculate_entropy_pure():
    # Only 1 class repeated -> entropy must be 0.0
    track_data = [{"class_id": 2} for _ in range(10)]
    counts, entropy = calculate_entropy(track_data)
    assert counts[2] == 10
    assert entropy == 0.0

def test_calculate_entropy_mixed():
    # 5 items of class 0 and 5 items of class 1 -> 50/50 -> entropy = 1.0 (log2)
    track_data = [{"class_id": 0} for _ in range(5)] + [{"class_id": 1} for _ in range(5)]
    counts, entropy = calculate_entropy(track_data)
    assert counts[0] == 5
    assert counts[1] == 5
    assert round(entropy, 4) == 1.0

def test_classify_track_majority_vote():
    mapping = {0: "Moto", 2: "Auto"}
    counts = Counter({0: 3, 2: 7})
    result = classify_track(counts, mapping)
    assert result == "Auto"

def test_classify_track_empty():
    mapping = {0: "Moto"}
    assert classify_track(Counter(), mapping) == "indeterminado"
