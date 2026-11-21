"""
Tests de ObjectTracker.run sobre un video sintético y un modelo falso (sin YOLO real).

Cubren el corte por max_frames: la cantidad de frames procesados reportada y la regla
que descarta objetos que siguen en pantalla en el último frame.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import cv2
import numpy as np
import pytest
import torch

from siatlib.process import ObjectTracker

N_FRAMES = 10


@pytest.fixture
def video_path(tmp_path):
    path = tmp_path / "sintetico.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (64, 48))
    assert writer.isOpened(), "OpenCV no pudo crear el video de prueba"
    for i in range(N_FRAMES):
        writer.write(np.full((48, 64, 3), i * 20, dtype=np.uint8))
    writer.release()
    return str(path)


def _result_with_track(track_id: int):
    boxes = SimpleNamespace(
        xyxy=torch.tensor([[10.0, 10.0, 20.0, 20.0]]),
        cls=torch.tensor([2.0]),
        id=torch.tensor([float(track_id)]),
        conf=torch.tensor([0.9]),
    )
    return [SimpleNamespace(boxes=boxes)]


def _fake_model(track_from_call: int = None, track_id: int = 7):
    """Modelo cuyo track() no detecta nada, o detecta un objeto desde la llamada indicada (1-based)."""
    model = MagicMock()
    calls = {"n": 0}

    def track(*args, **kwargs):
        calls["n"] += 1
        if track_from_call is not None and calls["n"] >= track_from_call:
            return _result_with_track(track_id)
        return []

    model.track.side_effect = track
    return model


def _tracker(model):
    return ObjectTracker(model_path=model, tracker_path="botsort.yaml", zones=[], device="cpu")


def test_run_sin_limite_procesa_todo_el_video(video_path):
    model = _fake_model()
    result = _tracker(model).run(video_path)

    assert result.total_frames_processed == N_FRAMES
    assert model.track.call_count == N_FRAMES


def test_run_con_max_frames_reporta_los_frames_procesados(video_path):
    model = _fake_model()
    progress = []
    result = _tracker(model).run(
        video_path, max_frames=5, progress_callback=lambda f, total, fps: progress.append((f, total))
    )

    assert model.track.call_count == 5
    assert result.total_frames_processed == 5
    assert progress[-1] == (5, 5)


def test_run_con_max_frames_descarta_objetos_presentes_en_el_ultimo_frame(video_path):
    # El objeto aparece en el frame 3 y sigue hasta el corte (frame 5), sin pasar por zonas:
    # el video lo corta, así que no debe contarse como transición indeterminada.
    model = _fake_model(track_from_call=3)
    tracker = _tracker(model)
    result = tracker.run(video_path, max_frames=5)

    assert tracker.last_frame_index == 5
    assert 7 in tracker.excluded_undetermined_ids
    assert 7 not in result.undetermined_transitions
    assert 7 not in result.trajectories
