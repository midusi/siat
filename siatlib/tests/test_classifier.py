"""
Pruebas unitarias para el submódulo analytics/classifier.py.
Valida el cálculo de entropía de Shannon, detección de incertidumbre y clasificación
por votación mayoritaria según el historial de detecciones.
"""

from collections import Counter
from siatlib.analytics import calculate_entropy, classify_track


def test_calculate_entropy_pure():
    """Valida que un objeto clasificado siempre con la misma clase tenga entropía de Shannon 0.0 (máxima certeza)."""
    track_data = [{"class_id": 2} for _ in range(10)]
    counts, entropy = calculate_entropy(track_data)
    assert counts[2] == 10
    assert entropy == 0.0


def test_calculate_entropy_mixed():
    """Valida que una distribución equiprobable de 2 clases tenga entropía igual a 1.0 (-sum(0.5 * log2(0.5)))."""
    track_data = [{"class_id": 0} for _ in range(5)] + [{"class_id": 1} for _ in range(5)]
    counts, entropy = calculate_entropy(track_data)
    assert counts[0] == 5
    assert counts[1] == 5
    assert round(entropy, 4) == 1.0


def test_calculate_entropy_empty():
    """Valida que una lista vacía de detecciones retorne un Counter vacío y entropía 0.0."""
    counts, entropy = calculate_entropy([])
    assert counts == Counter()
    assert entropy == 0.0


def test_classify_track_majority_vote():
    """Valida que se asigne la clase con mayor frecuencia acumulada a lo largo del track (votación de mayoría)."""
    mapping = {0: "Moto", 2: "Auto"}
    counts = Counter({0: 3, 2: 7})
    result = classify_track(counts, mapping)
    assert result == "Auto"


def test_classify_track_empty():
    """Valida que ante un conteo vacío se clasifique como 'indeterminado'."""
    mapping = {0: "Moto"}
    assert classify_track(Counter(), mapping) == "indeterminado"


def test_classify_track_unmapped_class():
    """Valida que si la clase dominante no existe en el diccionario de mapeo retorne 'indeterminado'."""
    mapping = {0: "Moto"}
    counts = Counter({99: 5})
    assert classify_track(counts, mapping) == "indeterminado"

