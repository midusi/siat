import numpy as np
from siatlib.models import ZoneDefinition, ZoneType, AnalysisResult, VehicleTrajectory

def test_analysis_result_dict_access():
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

    # Test dictionary-like access
    assert res["total_frames"] == 120
    assert res["transition_counts"]["Norte"]["Sur"]["Auto"] == 5
    assert 1 in res["trajectories"]
    
    # Test to_dict conversion
    d = res.to_dict()
    assert d["total_frames_processed"] == 120
    assert d["trajectories"][1]["vehicle_class"] == "Auto"
