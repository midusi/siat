import argparse
import ast
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import cv2
import imageio_ffmpeg
import numpy as np
from ultralytics import YOLO
from ultralytics.utils.plotting import Annotator

from .analytics import (
    DEFAULT_CLASS_NAMES,
    DEFAULT_SIMPLIFIED_CLASS_NAMES,
    calculate_entropy,
    classify_track,
    compute_transitions,
)
from .models import AnalysisResult, VehicleTrajectory, ZoneDefinition, ZoneType
from .spatial import get_center_bb, get_zone_index
from .tracking import get_torch_device
from .visualization import ZONE_COLORS, apply_exclusion_mask, draw_polygon

# --- Constantes por defecto ---
SIMPLIFIED_CLASS_DISPLAY_NAMES = DEFAULT_SIMPLIFIED_CLASS_NAMES
CLASSES_NAMES = DEFAULT_CLASS_NAMES
DEVICE_TO_USE = "auto"


class ObjectTracker:
    """
    Clase para el seguimiento de objetos y análisis de zonas en videos.

    Gestiona la detección, el seguimiento, la clasificación basada en el historial
    y la interacción con zonas predefinidas en un feed de video, delegando la
    geometría, visión y analítica a sus respectivos submódulos.
    """

    def __init__(
        self,
        model_path: Union[str, YOLO],
        tracker_path: str,
        zone_in_polygons: Optional[List[np.ndarray]] = None,
        zone_out_polygons: Optional[List[np.ndarray]] = None,
        device: Optional[str] = None,
        names_polygons_in: Optional[List[str]] = None,
        names_polygons_out: Optional[List[str]] = None,
        excluded_polygons: Optional[List[np.ndarray]] = None,
        zones: Optional[List[ZoneDefinition]] = None,
    ):
        self.device = get_torch_device(device)

        # Cargar el modelo YOLO o reutilizar instancia existente
        if isinstance(model_path, (str, Path)):
            self.model = YOLO(str(model_path))
            self.model.to(str(self.device))
        else:
            self.model = model_path

        self.tracker_path = tracker_path
        self.class_names = SIMPLIFIED_CLASS_DISPLAY_NAMES
        self.all_class_names = list(self.class_names.values()) + ["indeterminado"]

        # Soporte para inicialización moderna mediante List[ZoneDefinition]
        if zones is not None:
            self.zone_in_polygons = [
                {"polygon": np.array(z.polygon, dtype=np.int32), "name": z.name}
                for z in zones
                if z.zone_type in (ZoneType.ENTRY, ZoneType.IN)
            ]
            self.zone_out_polygons = [
                {"polygon": np.array(z.polygon, dtype=np.int32), "name": z.name}
                for z in zones
                if z.zone_type in (ZoneType.EXIT, ZoneType.OUT)
            ]
            self.excluded_polygons = [
                np.array(z.polygon, dtype=np.int32)
                for z in zones
                if z.zone_type == ZoneType.EXCLUDED
            ]
        else:
            zin = zone_in_polygons or []
            zout = zone_out_polygons or []
            nin = names_polygons_in or []
            nout = names_polygons_out or []
            self.zone_in_polygons = [
                {"polygon": zin[i], "name": nin[i] if i < len(nin) else f"In_{i}"}
                for i in range(len(zin))
            ]
            self.zone_out_polygons = [
                {"polygon": zout[i], "name": nout[i] if i < len(nout) else f"Out_{i}"}
                for i in range(len(zout))
            ]
            self.excluded_polygons = excluded_polygons or []

        # --- Variables de estado para el seguimiento de objetos ---
        self.track_first_in_zone: Dict[int, int] = {}
        self.track_first_out_zone: Dict[int, int] = {}
        self.track_results: Dict[int, Dict[str, Any]] = {}
        self.track_history: defaultdict = defaultdict(list)
        self.data_obj_history: defaultdict[int, List[Dict[str, Any]]] = defaultdict(list)

        # Contadores y resultados analíticos
        self.total_vehicles_by_class: Counter[str] = Counter()
        self.entry_zone_counts: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.exit_zone_counts: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.transition_counts: defaultdict[str, defaultdict[str, defaultdict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )

        for pin in self.zone_in_polygons:
            for pout in self.zone_out_polygons:
                self.transition_counts[pin["name"]][pout["name"]] = {cls: 0 for cls in CLASSES_NAMES}

        self.transition_determined_object: Dict[int, Any] = defaultdict(dict)
        self.transition_undetermined_object: Dict[int, Any] = defaultdict(dict)

        print(f"Modelo YOLO cargado. Utilizando dispositivo: {self.device}")
        self.last_frame_index: Optional[int] = None
        self.excluded_undetermined_ids: Set[int] = set()

    # --- Métodos delegados a submódulos (compatibilidad hacia atrás) ---

    def _get_torch_device(self, preferred_device: Optional[str]):
        return get_torch_device(preferred_device)

    def _get_center_bb(self, box: np.ndarray) -> Tuple[int, int]:
        return get_center_bb(box)

    def _apply_exclusion_mask(self, frame: np.ndarray) -> np.ndarray:
        return apply_exclusion_mask(frame, self.excluded_polygons)

    def _get_zone_index(self, box: np.ndarray, polygons: List[np.ndarray]) -> int:
        return get_zone_index(box, polygons)

    def _draw_polygon(
        self, annotated_frame: np.ndarray, polygon: np.ndarray, name_polygon: str, zone_type: ZoneType, thickness: int
    ) -> np.ndarray:
        return draw_polygon(annotated_frame, polygon, name_polygon, zone_type, thickness)

    def _draw_zones_in_out(self, annotated_frame: np.ndarray, thickness: int = 2) -> np.ndarray:
        """Dibuja todos los polígonos de entrada y salida en el frame."""
        for zone_in in self.zone_in_polygons:
            draw_polygon(annotated_frame, zone_in["polygon"], zone_in["name"], ZoneType.ENTRY, thickness)
        for zone_out in self.zone_out_polygons:
            draw_polygon(annotated_frame, zone_out["polygon"], zone_out["name"], ZoneType.EXIT, thickness)
        return annotated_frame

    def _register_zone_entry_exit(self, box: np.ndarray, track_id: int):
        """Registra la primera zona de entrada y/o salida que un objeto visita."""
        if track_id not in self.track_first_in_zone:
            zone_in_idx = get_zone_index(box, [zone["polygon"] for zone in self.zone_in_polygons])
            if zone_in_idx >= 0:
                self.track_first_in_zone[track_id] = zone_in_idx

        if track_id not in self.track_first_out_zone:
            zone_out_idx = get_zone_index(box, [zone["polygon"] for zone in self.zone_out_polygons])
            if zone_out_idx >= 0:
                self.track_first_out_zone[track_id] = zone_out_idx

    def _draw_bbox_and_track(
        self, box: np.ndarray, class_id: int, track_id: int, act_frame: int, confidence: float, annotator: Optional[Annotator] = None
    ):
        """Almacena el historial y punto central del objeto detectado."""
        center_x, center_y = get_center_bb(box)
        self.data_obj_history[track_id].append({
            "act_frame": act_frame,
            "class_id": class_id,
            "confidence": confidence,
            "box": box.tolist(),
            "track_history_point": (center_x, center_y),
        })

    def _calculate_entropy(self, track_data: List[Dict[str, Any]]) -> Tuple[Counter, float]:
        return calculate_entropy(track_data)

    def _classify_track(self, class_counts: Counter) -> str:
        return classify_track(class_counts, self.class_names)

    def _get_final_track_classifications(self):
        """Calcula la clasificación y entropía final para cada objeto rastreado."""
        for track_id, data in self.data_obj_history.items():
            class_counts, entropy = calculate_entropy(data)
            classification = classify_track(class_counts, self.class_names)
            self.track_results[track_id] = {
                "entropy": entropy,
                "classification": classification,
            }

    def _get_final_track_transitions(self):
        """Calcula transiciones O/D y reglas de exclusión en bordes usando el submódulo analytics."""
        transitions_res = compute_transitions(
            track_results=self.track_results,
            data_obj_history=self.data_obj_history,
            track_first_in_zone=self.track_first_in_zone,
            track_first_out_zone=self.track_first_out_zone,
            zone_in_names=[z["name"] for z in self.zone_in_polygons],
            zone_out_names=[z["name"] for z in self.zone_out_polygons],
            last_frame_index=self.last_frame_index,
            class_names=CLASSES_NAMES,
            simplified_class_display_names=SIMPLIFIED_CLASS_DISPLAY_NAMES,
        )
        self.transition_counts = transitions_res.transition_counts
        self.transition_determined_object = transitions_res.transition_determined_object
        self.transition_undetermined_object = transitions_res.transition_undetermined_object
        self.excluded_undetermined_ids = transitions_res.excluded_undetermined_ids
        self.total_vehicles_by_class = transitions_res.total_vehicles_by_class
        self.entry_zone_counts = transitions_res.entry_zone_counts
        self.exit_zone_counts = transitions_res.exit_zone_counts

    def process_frame(self, frame: np.ndarray, results: list, act_frame: int) -> np.ndarray:
        """Procesa un solo frame del video para detectar, rastrear y registrar objetos."""
        self._draw_zones_in_out(frame, 2)

        if results and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu()
            class_ids = results[0].boxes.cls.cpu().tolist()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            confs = results[0].boxes.conf.float().cpu().tolist()

            annotator = Annotator(frame, line_width=1)

            for box, class_id, track_id, confidence in zip(boxes, class_ids, track_ids, confs):
                self._register_zone_entry_exit(box, track_id)
                self._draw_bbox_and_track(box, class_id, track_id, act_frame, confidence, annotator)

        return frame

    def run(
        self,
        video_path: str,
        max_frames: Optional[int] = None,
        output_video_path: Optional[str] = None,
        display_video: bool = False,
        imgsz: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
    ) -> AnalysisResult:
        """
        Ejecuta el proceso de seguimiento de objetos en un video.

        Args:
            video_path: Ruta al archivo de video de entrada.
            max_frames: Número máximo de frames a procesar (None = video completo).
            output_video_path: Ruta donde guardar el video anotado (opcional).
            display_video: Si es True, muestra la ventana del video mediante OpenCV GUI.
            imgsz: Resolución de inferencia YOLO (opcional).
            progress_callback: Callback opcional invocado como fn(act_frame, total_frames, fps).

        Returns:
            AnalysisResult con las matrices de transición y trayectorias en memoria.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: No se pudo abrir el video en {video_path}")
            return AnalysisResult(
                transition_counts={},
                determined_transitions={},
                undetermined_transitions={},
                trajectories={},
                total_frames_processed=0,
                output_video_path=None,
            )

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames_to_process = total_frames
        if max_frames is not None:
            frames_to_process = min(total_frames if total_frames > 0 else float("inf"), max_frames)

        progress_enabled = frames_to_process > 0 and frames_to_process != float("inf")
        infer_imgsz = imgsz if imgsz else max(32, ((max(w, h) + 31) // 32) * 32)

        act_frame = 0
        print(f"Procesando video: {video_path} (dimensiones: {w}x{h}, FPS: {fps})")
        print(f"Resolución de inferencia: {infer_imgsz}")

        writer = None
        if output_video_path:
            os.makedirs(os.path.dirname(output_video_path) or ".", exist_ok=True)
            out_fps = fps if fps and fps > 0 else 25
            writer = subprocess.Popen(
                [
                    imageio_ffmpeg.get_ffmpeg_exe(),
                    "-y",
                    "-loglevel",
                    "error",
                    "-f",
                    "rawvideo",
                    "-pix_fmt",
                    "bgr24",
                    "-s",
                    f"{w}x{h}",
                    "-r",
                    str(out_fps),
                    "-i",
                    "-",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    output_video_path,
                ],
                stdin=subprocess.PIPE,
            )
            print(f"Guardando video procesado en: {output_video_path}")
        else:
            print("No se guardará el video procesado (output_video_path no especificado).")

        last_reported_percentage = -1
        start_time = time.time()
        success = True

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                print("\nFin del video o error al leer frame.")
                break

            act_frame += 1
            elapsed = time.time() - start_time
            current_fps = act_frame / elapsed if elapsed > 0 else 0.0

            # Notificar progreso vía callback si fue provisto
            if progress_callback is not None:
                progress_callback(act_frame, frames_to_process, current_fps)
            elif progress_enabled:
                current_percentage = int((act_frame / frames_to_process) * 100)
                if current_percentage > last_reported_percentage or (
                    act_frame % 50 == 0 and last_reported_percentage < 100
                ):
                    sys.stdout.write(
                        f"\rProgreso: {current_percentage}% completado ({act_frame}/{frames_to_process} frames - {current_fps:.1f} FPS)"
                    )
                    sys.stdout.flush()
                    last_reported_percentage = current_percentage
            else:
                if act_frame % 50 == 0:
                    sys.stdout.write(".")
                    sys.stdout.flush()

            if max_frames is not None and act_frame > max_frames:
                print(f"\nAlcanzado el número máximo de frames ({max_frames}). Deteniendo.")
                break

            masked_for_inference = apply_exclusion_mask(frame, self.excluded_polygons)
            results = self.model.track(
                masked_for_inference,
                conf=0.3,
                iou=0.6,
                persist=True,
                verbose=False,
                agnostic_nms=True,
                imgsz=infer_imgsz,
                tracker=self.tracker_path,
            )

            masked_for_output = apply_exclusion_mask(frame, self.excluded_polygons)
            processed_frame = self.process_frame(masked_for_output, results, act_frame)

            if writer is not None:
                if processed_frame.shape[:2] != (h, w):
                    raise RuntimeError(
                        f"El frame {act_frame} mide {processed_frame.shape[1]}x{processed_frame.shape[0]}, "
                        f"se esperaba {w}x{h}."
                    )
                writer.stdin.write(processed_frame.tobytes())

            if display_video:
                cv2.imshow("Video", processed_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("\nTecla 'q' presionada. Deteniendo.")
                    break

        if progress_callback is None:
            if progress_enabled:
                sys.stdout.write(
                    f"\rProgreso: 100% completado ({act_frame-1 if not success else act_frame}/{frames_to_process} frames)\n"
                )
                sys.stdout.flush()
            else:
                print("\n")

        self.last_frame_index = act_frame

        cap.release()
        if writer is not None:
            writer.stdin.close()
            if writer.wait() != 0:
                raise RuntimeError(f"ffmpeg terminó con código {writer.returncode} al escribir {output_video_path}.")

        if display_video:
            cv2.destroyAllWindows()

        self._get_final_track_classifications()
        self._get_final_track_transitions()

        # Construir objetos tipados VehicleTrajectory para AnalysisResult
        trajectories: Dict[int, VehicleTrajectory] = {}
        for track_id, history in self.data_obj_history.items():
            if track_id in self.excluded_undetermined_ids:
                continue
            in_idx = self.track_first_in_zone.get(track_id)
            in_name = (
                self.zone_in_polygons[in_idx]["name"]
                if in_idx is not None and 0 <= in_idx < len(self.zone_in_polygons)
                else None
            )

            out_idx = self.track_first_out_zone.get(track_id)
            out_name = (
                self.zone_out_polygons[out_idx]["name"]
                if out_idx is not None and 0 <= out_idx < len(self.zone_out_polygons)
                else None
            )

            classification = self.track_results.get(track_id, {}).get("classification", "indeterminado")
            conf = history[-1].get("confidence", 0.0) if history else 0.0

            trajectories[track_id] = VehicleTrajectory(
                track_id=track_id,
                vehicle_class=classification,
                confidence=conf,
                first_entry_zone=in_name,
                first_exit_zone=out_name,
                history=history,
            )

        return AnalysisResult(
            transition_counts=self.transition_counts,
            determined_transitions=self.transition_determined_object,
            undetermined_transitions=self.transition_undetermined_object,
            trajectories=trajectories,
            total_frames_processed=act_frame,
            output_video_path=output_video_path,
        )


def main():
    """Punto de entrada del CLI de siatlib."""
    parser = argparse.ArgumentParser(
        description="Realiza seguimiento de objetos en videos y genera un informe de tránsito.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--input_video_path", "-i", type=str, required=True, help="Ruta al video de entrada.")
    parser.add_argument("--model_path", "-m", type=str, required=True, help="Ruta al modelo YOLO (.pt).")
    parser.add_argument("--tracker_path", "-t", type=str, required=True, help="Ruta al tracker config.")
    parser.add_argument("--polygons_in", "-pi", type=ast.literal_eval, required=True, help="Polígonos de entrada.")
    parser.add_argument("--polygons_out", "-po", type=ast.literal_eval, required=True, help="Polígonos de salida.")
    parser.add_argument("--excluded_zones", "-ez", type=ast.literal_eval, required=False, default=[], help="Zonas excluidas.")
    parser.add_argument("--names_polygons_in", "-ni", type=ast.literal_eval, required=True, help="Nombres zonas entrada.")
    parser.add_argument("--names_polygons_out", "-no", type=ast.literal_eval, required=True, help="Nombres zonas salida.")
    parser.add_argument("--output_video_path", "-o", type=str, default=None, help="Ruta video salida.")
    parser.add_argument("--imgsz", type=int, default=None, help="Resolución de inferencia.")
    parser.add_argument("--max_frames", "-f", type=int, default=None, help="Máximo frames a procesar.")
    parser.add_argument("--no_display", action="store_true", help="No mostrar ventana.")

    args = parser.parse_args()

    final_output_video_path = args.output_video_path
    if final_output_video_path is None:
        input_dir = os.path.dirname(args.input_video_path) or "."
        input_filename_without_ext, input_ext = os.path.splitext(os.path.basename(args.input_video_path))
        output_dir = os.path.join(input_dir, input_filename_without_ext)
        os.makedirs(output_dir, exist_ok=True)
        final_output_video_path = os.path.join(output_dir, f"processed{input_ext}")
    else:
        output_dir = os.path.dirname(final_output_video_path) or "."
        os.makedirs(output_dir, exist_ok=True)

    zone_in = [np.array(p, dtype=np.int32) for p in args.polygons_in]
    zone_out = [np.array(p, dtype=np.int32) for p in args.polygons_out]
    excluded = [np.array(p, dtype=np.int32) for p in (args.excluded_zones or [])]

    tracker = ObjectTracker(
        args.model_path,
        args.tracker_path,
        zone_in,
        zone_out,
        device=DEVICE_TO_USE,
        names_polygons_in=args.names_polygons_in,
        names_polygons_out=args.names_polygons_out,
        excluded_polygons=excluded,
    )

    results = tracker.run(
        video_path=args.input_video_path,
        max_frames=args.max_frames,
        output_video_path=final_output_video_path,
        display_video=not args.no_display,
        imgsz=args.imgsz,
    )

    # Volcado de compatibilidad a archivos JSON
    with open(f"{output_dir}/data_obj_history.json", "w", encoding="utf-8") as f:
        serializable_dict = {
            str(k): v
            for k, v in tracker.data_obj_history.items()
            if int(k) not in tracker.excluded_undetermined_ids
        }
        json.dump(serializable_dict, f, ensure_ascii=False, indent=2)

    with open(f"{output_dir}/transition_determined_object.json", "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in tracker.transition_determined_object.items()}, f, ensure_ascii=False, indent=2)

    with open(f"{output_dir}/transition_undetermined_object.json", "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in tracker.transition_undetermined_object.items()}, f, ensure_ascii=False, indent=2)

    with open(f"{output_dir}/transition_counts.json", "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in tracker.transition_counts.items()}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()