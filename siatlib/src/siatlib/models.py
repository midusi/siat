from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any

class ZoneType(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"
    EXCLUDED = "excluded"

    # Aliases de compatibilidad
    IN = "entry"
    OUT = "exit"

@dataclass
class ZoneDefinition:
    name: str
    polygon: List[Tuple[int, int]]  # Lista de vértices [(x1, y1), (x2, y2), ...]
    zone_type: ZoneType

@dataclass
class VehicleTrajectory:
    track_id: int
    vehicle_class: str
    confidence: float
    first_entry_zone: Optional[str]
    first_exit_zone: Optional[str]
    history: List[Dict[str, Any]]

@dataclass
class MotionCompensationConfig:
    """
    Parámetros de la compensación de movimiento de cámara.

    Las zonas se definen sobre el primer frame (referencia). Si la cámara se
    mueve (p. ej. un dron), se estima una homografía por frame para mantener
    las zonas alineadas con la calle.
    """
    enabled: bool = True
    scale: float = 0.5           # Factor de reducción para el flujo óptico (0 < scale <= 1)
    smooth_sigma: float = 1.5    # Sigma (en frames) del suavizado gaussiano de fase cero
    anchor_interval: int = 30    # Cada cuántos frames se re-ancla al frame de referencia (ORB)

@dataclass
class AnalysisResult:
    transition_counts: Dict[str, Dict[str, Dict[str, int]]]
    determined_transitions: Dict[str, Any]
    undetermined_transitions: Dict[str, Any]
    trajectories: Dict[int, VehicleTrajectory]
    total_frames_processed: int
    output_video_path: Optional[str] = None
    camera_motion: Optional[Dict[str, Any]] = None

    def __getitem__(self, item: str) -> Any:
        if item == "total_frames":
            return self.total_frames_processed
        if item == "data_obj_history":
            return {k: v.history for k, v in self.trajectories.items()}
        if hasattr(self, item):
            return getattr(self, item)
        data = self.to_dict()
        if item in data:
            return data[item]
        raise KeyError(item)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_counts": self.transition_counts,
            "transition_determined_object": self.determined_transitions,
            "transition_undetermined_object": self.undetermined_transitions,
            "trajectories": {
                k: {
                    "track_id": v.track_id,
                    "vehicle_class": v.vehicle_class,
                    "confidence": v.confidence,
                    "first_entry_zone": v.first_entry_zone,
                    "first_exit_zone": v.first_exit_zone,
                    "history": v.history,
                }
                for k, v in self.trajectories.items()
            },
            "total_frames_processed": self.total_frames_processed,
            "output_video_path": self.output_video_path,
            "camera_motion": self.camera_motion,
        }

