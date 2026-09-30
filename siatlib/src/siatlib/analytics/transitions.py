from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional

DEFAULT_CLASS_NAMES = [
    "Transporte liviano",
    "Transporte mediano",
    "Transporte pesado",
]

DEFAULT_SIMPLIFIED_CLASS_NAMES = {
    0: "Transporte liviano",  # Bicicleta
    1: "Transporte pesado",   # Colectivo
    2: "Transporte mediano",  # Auto
    3: "Transporte pesado",   # Camión pesado
    4: "Transporte pesado",   # Camión liviano
    5: "Transporte liviano",  # Moto
}

@dataclass
class TransitionsResult:
    transition_counts: Dict[str, Dict[str, Dict[str, int]]]
    transition_determined_object: Dict[int, Any] = field(default_factory=dict)
    transition_undetermined_object: Dict[int, Any] = field(default_factory=dict)
    excluded_undetermined_ids: Set[int] = field(default_factory=set)
    total_vehicles_by_class: Counter = field(default_factory=Counter)
    entry_zone_counts: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    exit_zone_counts: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))


def compute_transitions(
    track_results: Dict[int, Dict[str, Any]],
    data_obj_history: Dict[int, List[Dict[str, Any]]],
    track_first_in_zone: Dict[int, int],
    track_first_out_zone: Dict[int, int],
    zone_in_names: List[str],
    zone_out_names: List[str],
    last_frame_index: Optional[int] = None,
    class_names: Optional[List[str]] = None,
    simplified_class_display_names: Optional[Dict[int, str]] = None,
) -> TransitionsResult:
    """
    Calcula la matriz de transiciones (origen-destino), conteos por zona, y filtra
    objetos según su ingreso y egreso en las zonas de interés.
    """
    classes = class_names if class_names is not None else DEFAULT_CLASS_NAMES
    simplified_mapping = (
        simplified_class_display_names
        if simplified_class_display_names is not None
        else DEFAULT_SIMPLIFIED_CLASS_NAMES
    )

    total_vehicles_by_class: Counter = Counter()
    entry_zone_counts: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    exit_zone_counts: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    transition_counts: defaultdict[str, defaultdict[str, defaultdict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    for in_name in zone_in_names:
        for out_name in zone_out_names:
            transition_counts[in_name][out_name] = {cls: 0 for cls in classes}

    transition_determined_object: Dict[int, Any] = {}
    transition_undetermined_object: Dict[int, Any] = {}
    excluded_undetermined_ids: Set[int] = set()

    for track_id, data in track_results.items():
        classification = data.get("classification", "indeterminado")
        is_indeterminate_class = classification == "indeterminado"
        display_class = classification

        # Sumar conteos globales si no es indeterminada
        if not is_indeterminate_class:
            total_vehicles_by_class[display_class] += 1

        history_track: Dict[str, Any] = {}
        history = data_obj_history.get(track_id, [])
        if history:
            first_appearance_obj = history[0]
            last_appearance_obj = history[-1]

            history_track["first_appearance"] = {
                "frame": first_appearance_obj.get("act_frame"),
                "boundingBox": first_appearance_obj.get("box"),
            }
            history_track["last_appearance"] = {
                "frame": last_appearance_obj.get("act_frame"),
                "boundingBox": last_appearance_obj.get("box"),
            }
            history_track["class"] = simplified_mapping.get(
                last_appearance_obj.get("class_id"), classification
            )

        # Conteos por zona de entrada y salida
        if track_id in track_first_in_zone:
            in_zone_idx = track_first_in_zone[track_id]
            if 0 <= in_zone_idx < len(zone_in_names):
                in_zone_label = zone_in_names[in_zone_idx]
                entry_zone_counts[display_class][in_zone_label] += 1

        if track_id in track_first_out_zone:
            out_zone_idx = track_first_out_zone[track_id]
            if 0 <= out_zone_idx < len(zone_out_names):
                out_zone_label = zone_out_names[out_zone_idx]
                exit_zone_counts[display_class][out_zone_label] += 1

        # Matriz de transiciones y reglas de exclusión en bordes
        if track_id in track_first_in_zone:
            in_zone_idx = track_first_in_zone[track_id]
            in_zone_label = zone_in_names[in_zone_idx] if 0 <= in_zone_idx < len(zone_in_names) else ""
            if track_id in track_first_out_zone:
                out_zone_idx = track_first_out_zone[track_id]
                out_zone_label = zone_out_names[out_zone_idx] if 0 <= out_zone_idx < len(zone_out_names) else ""
                transition_data = history_track.copy()
                transition_data["labels"] = {"in": in_zone_label, "out": out_zone_label}
                transition_determined_object[track_id] = transition_data
                if not is_indeterminate_class and in_zone_label and out_zone_label:
                    transition_counts[in_zone_label][out_zone_label][display_class] += 1
            else:
                # Entrada conocida, salida indeterminada
                transition_data = history_track.copy()
                transition_data["labels"] = {"in": in_zone_label, "out": ""}
                last_fr = (history_track.get("last_appearance") or {}).get("frame")
                if last_frame_index is not None and last_fr == last_frame_index:
                    excluded_undetermined_ids.add(track_id)
                else:
                    transition_undetermined_object[track_id] = transition_data
        elif track_id in track_first_out_zone:
            # Salida conocida, entrada indeterminada
            out_zone_idx = track_first_out_zone[track_id]
            out_zone_label = zone_out_names[out_zone_idx] if 0 <= out_zone_idx < len(zone_out_names) else ""
            transition_data = history_track.copy()
            transition_data["labels"] = {"in": "", "out": out_zone_label}
            first_fr = (history_track.get("first_appearance") or {}).get("frame")
            if first_fr == 1:
                excluded_undetermined_ids.add(track_id)
            else:
                transition_undetermined_object[track_id] = transition_data
        else:
            # Entrada y salida indeterminadas
            transition_data = history_track.copy()
            transition_data["labels"] = {"in": "", "out": ""}
            first_fr = (history_track.get("first_appearance") or {}).get("frame")
            last_fr = (history_track.get("last_appearance") or {}).get("frame")
            exclude = False
            if first_fr == 1:
                exclude = True
            if last_frame_index is not None and last_fr == last_frame_index:
                exclude = True
            if exclude:
                excluded_undetermined_ids.add(track_id)
            else:
                transition_undetermined_object[track_id] = transition_data

    return TransitionsResult(
        transition_counts=transition_counts,
        transition_determined_object=transition_determined_object,
        transition_undetermined_object=transition_undetermined_object,
        excluded_undetermined_ids=excluded_undetermined_ids,
        total_vehicles_by_class=total_vehicles_by_class,
        entry_zone_counts=entry_zone_counts,
        exit_zone_counts=exit_zone_counts,
    )
