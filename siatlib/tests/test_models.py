"""
Pruebas unitarias para models.py.
Valida la creación, serialización y compatibilidad de estructuras de datos (AnalysisResult,
ZoneDefinition, ZoneType y VehicleTrajectory).
"""

import pytest
from siatlib.models import AnalysisResult, VehicleTrajectory, ZoneDefinition, ZoneType


def test_zone_type_and_aliases():
    """Valida los valores y alias compatibles del enum ZoneType (IN/ENTRY, OUT/EXIT, EXCLUDED)."""
    assert ZoneType.ENTRY.value == "entry"
    assert ZoneType.EXIT.value == "exit"
    assert ZoneType.EXCLUDED.value == "excluded"
    assert ZoneType.IN == ZoneType.ENTRY
    assert ZoneType.OUT == ZoneType.EXIT


def test_zone_definition_creation():
    """Valida la instanciación de ZoneDefinition con polígonos de vértices absolutos."""
    zone = ZoneDefinition(name="Entrada Norte", polygon=[(0, 0), (10, 0), (10, 10)], zone_type=ZoneType.ENTRY)
    assert zone.name == "Entrada Norte"
    assert len(zone.polygon) == 3
    assert zone.zone_type == ZoneType.ENTRY


def test_analysis_result_dict_access():
    """Valida el acceso indexado tipo diccionario y conversión completa con to_dict()."""
    res = AnalysisResult(
        transition_counts={"Norte": {"Sur": {"Auto": 5}}},
        determined_transitions={1: {"labels": {"in": "Norte", "out": "Sur"}}},
        undetermined_transitions={},
        trajectories={
            1: VehicleTrajectory(
                track_id=1,
                vehicle_class="Auto",
                confidence=0.95,
                first_entry_zone="Norte",
                first_exit_zone="Sur",
                history=[{"frame": 1, "box": [0, 0, 10, 10]}],
            )
        },
        total_frames_processed=120,
        output_video_path="output.mp4",
    )

    # Validación de acceso como diccionario
    assert res["total_frames"] == 120
    assert res["total_frames_processed"] == 120
    assert res["transition_counts"]["Norte"]["Sur"]["Auto"] == 5
    assert "data_obj_history" in res.to_dict() or res["data_obj_history"][1] == [{"frame": 1, "box": [0, 0, 10, 10]}]
    assert 1 in res["trajectories"]

    # Validación de to_dict()
    d = res.to_dict()
    assert d["total_frames_processed"] == 120
    assert d["trajectories"][1]["vehicle_class"] == "Auto"
    assert d["trajectories"][1]["track_id"] == 1
    assert d["output_video_path"] == "output.mp4"


def test_analysis_result_invalid_key():
    """Valida que acceder a una clave inexistente en AnalysisResult lance KeyError."""
    res = AnalysisResult(
        transition_counts={},
        determined_transitions={},
        undetermined_transitions={},
        trajectories={},
        total_frames_processed=0,
    )
    with pytest.raises(KeyError):
        _ = res["clave_invalida"]

