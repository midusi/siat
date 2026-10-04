from pathlib import Path
from typing import Callable, List, Optional, Union

from ultralytics import YOLO

from .models import AnalysisResult, ZoneDefinition
from .process import ObjectTracker
from .tracking import get_torch_device


class TrafficAnalyzer:
    """
    Punto de entrada unificado y de alto nivel para el análisis de tráfico vehicular en siatlib.

    Mantiene cargado el modelo en memoria/dispositivo y orquesta la ejecución del análisis
    sobre videos de forma agnóstica a la infraestructura (sin dependencias de bases de datos,
    frameworks web o colas de tareas).
    """

    def __init__(
        self,
        model_path: Union[str, Path, YOLO],
        tracker_config: Optional[Union[str, Path]] = None,
        device: str = "auto",
    ):
        """
        Inicializa el analizador cargando el detector YOLO.

        Args:
            model_path: Ruta al archivo de pesos del modelo (.pt) o instancia de YOLO.
            tracker_config: Ruta a la configuración del tracker (YAML).
                            Si es None, se utiliza botsort_custom.yaml incluido en la librería.
            device: Dispositivo de inferencia ('auto', 'cuda', 'cpu', 'mps', '0', etc.).
        """
        self.device = get_torch_device(device)

        if isinstance(model_path, (str, Path)):
            self.model = YOLO(str(model_path))
            self.model.to(str(self.device))
        else:
            self.model = model_path

        if tracker_config is None:
            default_config = Path(__file__).resolve().parent / "botsort_custom.yaml"
            self.tracker_config = str(default_config) if default_config.exists() else "botsort.yaml"
        else:
            self.tracker_config = str(tracker_config)

    def process_video(
        self,
        video_path: Union[str, Path],
        zones: List[ZoneDefinition],
        output_video_path: Optional[Union[str, Path]] = None,
        max_frames: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        imgsz: Optional[int] = None,
        display_video: bool = False,
    ) -> AnalysisResult:
        """
        Ejecuta el pipeline completo de análisis sobre un archivo de video.

        Args:
            video_path: Ruta al archivo de video fuente.
            zones: Lista de objetos ZoneDefinition (zonas de entrada, salida y exclusión).
            output_video_path: Ruta destino para el video renderizado con anotaciones (opcional).
            max_frames: Límite de cuadros a procesar (None = video completo).
            progress_callback: Función callback opcional que recibe:
                               (frame_actual, total_frames, fps_actuales).
            imgsz: Tamaño de imagen para inferencia YOLO (opcional).
            display_video: Si es True, muestra la ventana de OpenCV durante el procesamiento.

        Returns:
            AnalysisResult con las matrices de transición (O/D), trayectorias y métricas en memoria.
        """
        tracker = ObjectTracker(
            model_path=self.model,
            tracker_path=self.tracker_config,
            zones=zones,
            device=str(self.device),
        )

        return tracker.run(
            video_path=str(video_path),
            max_frames=max_frames,
            output_video_path=str(output_video_path) if output_video_path else None,
            display_video=display_video,
            imgsz=imgsz,
            progress_callback=progress_callback,
        )
