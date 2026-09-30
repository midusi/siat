from siatlib.analytics import compute_transitions

def test_compute_transitions_determined():
    track_results = {
        1: {"classification": "Transporte mediano", "entropy": 0.0}
    }
    data_obj_history = {
        1: [
            {"act_frame": 10, "class_id": 2, "box": [10, 10, 20, 20]},
            {"act_frame": 30, "class_id": 2, "box": [80, 80, 90, 90]},
        ]
    }
    track_first_in_zone = {1: 0}   # Entry zone idx 0 ("Norte")
    track_first_out_zone = {1: 0}  # Exit zone idx 0 ("Sur")
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

def test_compute_transitions_edge_exclusion():
    # Vehicle appears in first frame (act_frame == 1) with out zone only -> must be excluded
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
