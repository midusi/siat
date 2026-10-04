"""
siatlib — Librería de visión por computadora para análisis de tráfico vehicular.

Uso básico:
    from siatlib import ObjectTracker
    tracker = ObjectTracker(model_path, tracker_path, zones_in, zones_out, ...)
    tracker.run(video_path=..., output_video_path=...)
"""

from .analyzer import TrafficAnalyzer
from .models import AnalysisResult, VehicleTrajectory, ZoneDefinition, ZoneType
from .process import ObjectTracker, main

__all__ = [
    "TrafficAnalyzer",
    "ObjectTracker",
    "main",
    "ZoneDefinition",
    "ZoneType",
    "VehicleTrajectory",
    "AnalysisResult",
]
