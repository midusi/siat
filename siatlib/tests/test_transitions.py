"""
Pruebas unitarias para analytics/transitions.py.
Valida el cálculo de la matriz de transiciones (Origen-Destino), conteos por zona,
y reglas de exclusión de artefactos en los bordes temporales del video.
"""

from siatlib.analytics import compute_transitions


def test_compute_transitions_determined():
    """Valida que un vehículo con zona de entrada y salida registradas compute en la matriz O/D y en determined_transitions."""
    track_results = {
        1: {"classification": "Transporte mediano", "entropy": 0.0}
    }
    data_obj_history = {
        1: [
            {"act_frame": 10, "class_id": 2, "box": [10, 10, 20, 20]},
            {"act_frame": 30, "class_id": 2, "box": [80, 80, 90, 90]},
        ]
    }
    track_first_in_zone = {1: 0}   # Zona de entrada índice 0 ("Norte")
    track_first_out_zone = {1: 0}  # Zona de salida índice 0 ("Sur")
    zone_in_names = ["Norte"]
    zone_out_names = ["Sur"]

    res = compute_transitions(
        track_results=track_results,
        data_obj_history=data_obj_history,
        track_first_in_zone=track_first_in_zone,
        track_first_out_zone=track_first_out_zone,
        zone_in_names=zone_in_names,
        zone_out_names=zone_out_names,
        last_frame_index=100,
    )

    assert 1 in res.transition_determined_object
    assert res.transition_determined_object[1]["labels"] == {"in": "Norte", "out": "Sur"}
    assert res.transition_counts["Norte"]["Sur"]["Transporte mediano"] == 1
    assert res.total_vehicles_by_class["Transporte mediano"] == 1
    assert res.entry_zone_counts["Transporte mediano"]["Norte"] == 1
    assert res.exit_zone_counts["Transporte mediano"]["Sur"] == 1


def test_compute_transitions_edge_exclusion_first_frame():
    """Valida que un vehículo presente en el primer frame (act_frame == 1) sin zona de entrada sea excluido como artefacto de borde."""
    track_results = {
        2: {"classification": "Transporte pesado", "entropy": 0.0}
    }
    data_obj_history = {
        2: [
            {"act_frame": 1, "class_id": 1, "box": [50, 50, 60, 60]},
            {"act_frame": 20, "class_id": 1, "box": [80, 80, 90, 90]},
        ]
    }
    track_first_in_zone = {}
    track_first_out_zone = {2: 0}

    res = compute_transitions(
        track_results=track_results,
        data_obj_history=data_obj_history,
        track_first_in_zone=track_first_in_zone,
        track_first_out_zone=track_first_out_zone,
        zone_in_names=["Norte"],
        zone_out_names=["Sur"],
        last_frame_index=100,
    )

    assert 2 in res.excluded_undetermined_ids
    assert 2 not in res.transition_undetermined_object


# def test_compute_transitions_edge_exclusion_last_frame():
#     """Valida que un vehículo con zona de entrada pero que sigue presente en el último frame sin salir sea excluido."""
#     track_results = {
#         3: {"classification": "Transporte mediano", "entropy": 0.0}
#     }
#     data_obj_history = {
#         3: [
#             {"act_frame": 70, "class_id": 2, "box": [50, 50, 60, 60]},
#             {"act_frame": 100, "class_id": 2, "box": [80, 80, 90, 90]},
#         ]
#     }
#     track_first_in_zone = {3: 0}  # Entró por Norte
#     track_first_out_zone = {}     # No salió aún

#     res = compute_transitions(
#         track_results=track_results,
#         data_obj_history=data_obj_history,
#         track_first_in_zone=track_first_in_zone,
#         track_first_out_zone=track_first_out_zone,
#         zone_in_names=["Norte"],
#         zone_out_names=["Sur"],
#         last_frame_index=100,  # Coincide con last_appearance -> excluido
#     )

#     assert 3 in res.excluded_undetermined_ids
#     assert 3 not in res.transition_undetermined_object


def test_compute_transitions_undetermined_middle_sequence():
    """Valida que un vehículo que desaparece en medio del video sin salida conocida quede registrado en undetermined_transitions."""
    track_results = {
        4: {"classification": "Transporte liviano", "entropy": 0.0}
    }
    data_obj_history = {
        4: [
            {"act_frame": 20, "class_id": 0, "box": [50, 50, 60, 60]},
            {"act_frame": 40, "class_id": 0, "box": [80, 80, 90, 90]},
        ]
    }
    track_first_in_zone = {4: 0}
    track_first_out_zone = {}

    res = compute_transitions(
        track_results=track_results,
        data_obj_history=data_obj_history,
        track_first_in_zone=track_first_in_zone,
        track_first_out_zone=track_first_out_zone,
        zone_in_names=["Norte"],
        zone_out_names=["Sur"],
        last_frame_index=100,  # 40 < 100, por lo que NO se excluye por último frame
    )

    assert 4 not in res.excluded_undetermined_ids
    assert 4 in res.transition_undetermined_object
    assert res.transition_undetermined_object[4]["labels"] == {"in": "Norte", "out": ""}

