from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any

class ZoneType(str, Enum):
    ENTRY = "entry"
    EXIT = "exit"
    EXCLUDED = "excluded"

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
class AnalysisResult:
    transition_counts: Dict[str, Dict[str, Dict[str, int]]]
    determined_transitions: Dict[str, Any]
    undetermined_transitions: Dict[str, Any]
    trajectories: Dict[int, VehicleTrajectory]
    total_frames_processed: int
    output_video_path: Optional[str] = None
