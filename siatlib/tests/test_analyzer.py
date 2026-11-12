"""
Pruebas unitarias para analyzer.py (TrafficAnalyzer).
Valida la inicialización de la fachada de alto nivel, resolución de modelos,
configuración del tracker y la correcta delegación del pipeline hacia ObjectTracker.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from ultralytics import YOLO

from siatlib import AnalysisResult, TrafficAnalyzer, ZoneDefinition, ZoneType


def test_traffic_analyzer_init_defaults():
    """Valida la inicialización con configuración por defecto (dispositivo CPU y archivo botsort_custom.yaml integrado)."""
    mock_model = MagicMock(spec=YOLO)
    analyzer = TrafficAnalyzer(model_path=mock_model, device="cpu")

    assert analyzer.model == mock_model
    assert analyzer.device.type == "cpu"
    assert "botsort_custom.yaml" in analyzer.tracker_config
    assert Path(analyzer.tracker_config).exists()


@patch("siatlib.analyzer.YOLO")
def test_traffic_analyzer_init_with_path_str(mock_yolo_cls):
    """Valida la carga del modelo pasando una ruta en string y su transferencia al dispositivo de inferencia."""
    mock_instance = MagicMock(spec=YOLO)
    mock_yolo_cls.return_value = mock_instance

    analyzer = TrafficAnalyzer(model_path="weights.pt", device="cpu")

    mock_yolo_cls.assert_called_once_with("weights.pt")
    mock_instance.to.assert_called_once_with("cpu")
    assert analyzer.model == mock_instance


def test_traffic_analyzer_custom_tracker_config():
    """Valida que una ruta personalizada de configuración del tracker no sea sobrescrita por el default."""
    mock_model = MagicMock(spec=YOLO)
    custom_cfg = "/path/to/custom_tracker.yaml"
    analyzer = TrafficAnalyzer(model_path=mock_model, tracker_config=custom_cfg, device="cpu")

    assert analyzer.tracker_config == custom_cfg


@patch("siatlib.analyzer.ObjectTracker")
def test_traffic_analyzer_process_video_delegation(mock_tracker_class):
    """Valida que process_video() instancie ObjectTracker con las zonas provistas y delegue los argumentos a run()."""
    mock_tracker_instance = MagicMock()
    mock_result = AnalysisResult(
        transition_counts={},
        determined_transitions={},
        undetermined_transitions={},
        trajectories={},
        total_frames_processed=10,
        output_video_path="out.mp4",
    )
    mock_tracker_instance.run.return_value = mock_result
    mock_tracker_class.return_value = mock_tracker_instance

    mock_model = MagicMock(spec=YOLO)
    analyzer = TrafficAnalyzer(model_path=mock_model, device="cpu")

    zones = [
        ZoneDefinition(name="In1", polygon=[(0, 0), (10, 0), (10, 10)], zone_type=ZoneType.ENTRY),
        ZoneDefinition(name="Out1", polygon=[(50, 50), (60, 50), (60, 60)], zone_type=ZoneType.EXIT),
    ]

    cb = MagicMock()
    result = analyzer.process_video(
        video_path="test_video.mp4",
        zones=zones,
        output_video_path="out.mp4",
        max_frames=50,
        progress_callback=cb,
        imgsz=640,
        display_video=False,
    )

    # Verifica construcción del ObjectTracker
    mock_tracker_class.assert_called_once_with(
        model_path=mock_model,
        tracker_path=analyzer.tracker_config,
        zones=zones,
        device=str(analyzer.device),
        motion_compensation=None,
    )

    # Verifica invocación y parámetros delegados a tracker.run
    mock_tracker_instance.run.assert_called_once_with(
        video_path="test_video.mp4",
        max_frames=50,
        output_video_path="out.mp4",
        display_video=False,
        imgsz=640,
        progress_callback=cb,
    )

    assert result == mock_result
    assert result.total_frames_processed == 10

