import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import math
from collections import Counter, defaultdict, deque
from enum import Enum
from typing import Optional, Dict, List, Tuple
import sys # Importar sys para manejar la salida en la terminal
import argparse # Importar argparse para manejar argumentos de línea de comandos
import ast # Para convertir strings a listas/arrays
import os # Importar os para operaciones de sistema de archivos (rutas)
import json

# Importar torch para la detección de GPU
try:
    import torch
except ImportError:
    print("Advertencia: PyTorch no está instalado. Solo se podrá usar la CPU.")
    torch = None

from ultralytics.utils.plotting import Annotator, colors

# --- CONFIGURACIÓN Y CONSTANTES (internas del script, no de línea de comandos) ---

# Paleta de colores para las zonas: [verde para entrada, rojo para salida]
ZONE_COLORS = sv.ColorPalette.from_hex(["#00FF00", "#FF0000"])

ZONE_IN_POLYGONS = []
ZONE_OUT_POLYGONS = []
EXCLUDED_POLYGONS = []

# Longitud máxima del historial de seguimiento de un objeto
TRACK_HISTORY_LENGTH = 30 

# Mapeo de ID de clases a nombres de clases simplificadas
SIMPLIFIED_CLASS_DISPLAY_NAMES = {
    0: "Transporte liviano", # Bicicleta
    1: "Transporte pesado", # Colectivo
    2: "Transporte mediano", # Auto
    3: "Transporte pesado", # Camión pesado
    4: "Transporte pesado", # Camión liviano
    5: "Transporte liviano" # Moto
}

CLASSES_NAMES = [
    "Transporte liviano",
    "Transporte mediano",
    "Transporte pesado",
]


# Configuración del dispositivo para el modelo YOLO:
# "auto": Intenta usar GPU si está disponible (CUDA), de lo contrario, usa CPU.
# "cpu": Fuerza el uso de la CPU.
# "0", "1", ...: Usa la GPU con el índice especificado.
DEVICE_TO_USE = "auto" # Puedes cambiar esto a "cpu", "0", etc.

class ZoneType(Enum):
    """Enumeración para definir los tipos de zonas."""
    IN = 0  # Zona de entrada
    OUT = 1 # Zona de salida

class ObjectTracker:
    """
    Clase para el seguimiento de objetos y análisis de zonas en videos.

    Gestiona la detección, el seguimiento, la clasificación basada en el historial
    y la interacción con zonas predefinidas en un feed de video.
    """

    def __init__(self, model_path: str, tracker_path: str, zone_in_polygons: list[np.ndarray], zone_out_polygons: list[np.ndarray], device: Optional[str] = None, names_polygons_in: list[str] = [], names_polygons_out: list[str] = [], excluded_polygons: list[np.ndarray] = []):
        """
        Inicializa el ObjectTracker.

        Args:
            model_path (str): Ruta al archivo del modelo YOLO.
            zone_in_polygons (list[np.ndarray]): Lista de polígonos NumPy que definen las zonas de entrada.
            zone_out_polygons (list[np.ndarray]): Lista de polígonos NumPy que definen las zonas de salida.
            device (Optional[str]): Dispositivo a usar para el modelo YOLO ("cpu", "cuda", "cuda:0", etc.).
                                     Si es None, YOLO decidirá automáticamente.
        """
        self.device = self._get_torch_device(device) # Determinar el dispositivo real

        # Cargar el modelo YOLO
        self.model = YOLO(model_path)
        # Mover el modelo al dispositivo especificado
        self.model.to(str(self.device))
        
        # Guardar el path del tracker
        self.tracker_path = tracker_path
        
        # self.class_names = self.model.model.names # Nombres de clases del modelo (ej: 'car', 'bus')
        self.class_names = SIMPLIFIED_CLASS_DISPLAY_NAMES
        
        # Lista de todos los nombres de clases conocidos, incluyendo 'indeterminado'
        self.all_class_names = list(self.class_names.values()) + ["indeterminado"]

        self.zone_in_polygons = [
            {"polygon": zone_in_polygons[i], "name": names_polygons_in[i]}
            for i in range(len(zone_in_polygons))
        ]
        self.zone_out_polygons = [
            {"polygon": zone_out_polygons[i], "name": names_polygons_out[i]}
            for i in range(len(zone_out_polygons))
        ]
        self.excluded_polygons = excluded_polygons or []
        
        # --- Variables de estado para el seguimiento de objetos ---
        
        # Diccionario para almacenar la PRIMERA zona IN que un objeto visitó
        # Ejemplo: {track_id: zone_idx}
        self.track_first_in_zone: Dict[int, int] = {}
        # Diccionario para almacenar la PRIMERA zona OUT que un objeto visitó
        # Ejemplo: {track_id: zone_idx}
        self.track_first_out_zone: Dict[int, int] = {}

        # Diccionario para almacenar los resultados finales de clasificación por track_id
        # Ejemplo: {track_id: {"entropy": 0.5, "classification": "car"}}
        self.track_results: Dict[int, Dict] = {}

        # Historial de puntos (centro de bounding box) para dibujar los trazados
        # Se usa deque para una gestión eficiente de un historial de tamaño fijo.
        self.track_history: defaultdict[int, deque] = defaultdict(lambda: deque(maxlen=TRACK_HISTORY_LENGTH))

        # Historial de datos de objetos (frame, clase, confianza) para el cálculo de entropía
        # Ejemplo: {track_id: [{"act_frame": 10, "class_id": 0, "confidence": 0.9}]}
        self.data_obj_history: defaultdict[int, List[Dict]] = defaultdict(list)
        
        # Contador de transiciones de objetos
        self.total_vehicles_by_class: Counter[str] = Counter()
        self.entry_zone_counts: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.exit_zone_counts: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.transition_counts: defaultdict[str, defaultdict[str, defaultdict[str, int]]] = \
            defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        # Inicializar transition_counts con la estructura jerárquica:
        # {nombre_poligono_entrada: {nombre_poligono_salida: {clase: 0}}}
        for pin in self.zone_in_polygons:
            for pout in self.zone_out_polygons:
                self.transition_counts[pin["name"]][pout["name"]] = {cls: 0 for cls in CLASSES_NAMES}

        # Matriz de transición de zonas
        self.transition_determined_object = defaultdict(dict)
        self.transition_undetermined_object = defaultdict(dict)

        # Log de dispositivo y variables auxiliares
        print(f"Modelo YOLO cargado. Utilizando dispositivo: {self.device}")
        # Último frame procesado del video (se setea en run)
        self.last_frame_index = None
        # IDs de tracks excluidos de indeterminados por estar en límites (frame 1 o último)
        self.excluded_undetermined_ids = set()

    def _get_torch_device(self, preferred_device: Optional[str]) -> torch.device: # type: ignore
        """
        Determina el dispositivo PyTorch a usar (CPU o GPU) basado en la preferencia
        y la disponibilidad del hardware.
        """
        if torch is None:
            print("Usando CPU0")
            return torch.device("cpu") # PyTorch no está disponible, forzar CPU

        if preferred_device == "cpu":
            print("Usando CPU1")
            return torch.device("cpu")
        elif preferred_device == "auto":
            if torch.cuda.is_available():
                print("Usando GPU")
                return torch.device("cuda")
            else:
                print("Usando CPU2")
                return torch.device("cpu")
        elif preferred_device and preferred_device.isdigit(): # Para "0", "1", etc.
            if torch.cuda.is_available() and int(preferred_device) < torch.cuda.device_count():
                return torch.device(f"cuda:{preferred_device}")
            else:
                print(f"Advertencia: GPU '{preferred_device}' no disponible o no válida. Usando CPU.")
                return torch.device("cpu")
        elif preferred_device and "cuda" in preferred_device: # Para "cuda", "cuda:0", etc.
             if torch.cuda.is_available():
                 return torch.device(preferred_device)
             else:
                 print(f"Advertencia: CUDA no disponible. Usando CPU.")
                 return torch.device("cpu")
        else: # Si es None o un valor inesperado
            if torch.cuda.is_available():
                return torch.device("cuda")
            else:
                return torch.device("cpu")

    def _get_center_bb(self, box: np.ndarray) -> Tuple[int, int]:
        """
        Calcula el punto central de un bounding box.

        Args:
            box (np.ndarray): Coordenadas del bounding box [x1, y1, x2, y2].

        Returns:
            tuple[int, int]: Coordenadas (x_center, y_center) del centro.
        """
        x_center = int((box[0] + box[2]) / 2)
        y_center = int((box[1] + box[3]) / 2)
        return (x_center, y_center)

    def _draw_polygon(self, annotated_frame: np.ndarray, polygon: np.ndarray, name_polygon: str, zone_type: ZoneType, thickness: int) -> np.ndarray:
        """
        Dibuja un polígono y su número en el frame.

        Args:
            annotated_frame (np.ndarray): Frame sobre el que dibujar.
            polygon (np.ndarray): Polígono a dibujar.
            number_polygon (int): Número de la zona a mostrar.
            zone_type (ZoneType): Tipo de zona (IN o OUT) para determinar el color.
            thickness (int): Grosor de la línea del polígono y del texto.

        Returns:
            np.ndarray: Frame con el polígono y el número dibujados.
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        color = ZONE_COLORS.colors[zone_type.value].as_bgr() # Utiliza el valor del Enum como índice
        
        cv2.polylines(
            annotated_frame, [polygon], isClosed=True, color=color, thickness=thickness
        )
        
        zone_center = sv.get_polygon_center(polygon=polygon)
        # Asegura que las coordenadas sean enteros para cv2.putText
        cv2.putText(annotated_frame, name_polygon, (int(zone_center.x), int(zone_center.y)), font, font_scale, color, thickness=thickness)
        
        return annotated_frame

    def _draw_zones_in_out(self, annotated_frame: np.ndarray, thickness: int) -> np.ndarray:
        """
        Dibuja todos los polígonos de entrada y salida en el frame.

        Args:
            annotated_frame (np.ndarray): Frame sobre el que dibujar las zonas.
            thickness (int): Grosor de las líneas de los polígonos.

        Returns:
            np.ndarray: Frame con todas las zonas dibujadas.
        """
        for i, (zone_in, zone_out) in enumerate(zip(self.zone_in_polygons, self.zone_out_polygons)):
            self._draw_polygon(annotated_frame, zone_in["polygon"], zone_in["name"], ZoneType.IN, thickness)
            self._draw_polygon(annotated_frame, zone_out["polygon"], zone_in["name"], ZoneType.OUT, thickness)
        return annotated_frame

    def _apply_exclusion_mask(self, frame: np.ndarray) -> np.ndarray:
        """Rellena con negro todas las zonas excluidas sobre el frame."""
        if not self.excluded_polygons:
            return frame
        overlay = frame.copy()
        for poly in self.excluded_polygons:
            pts = poly.reshape((-1, 1, 2))
            cv2.fillPoly(overlay, [pts], color=(0, 0, 0))
        return overlay

    def _get_zone_index(self, box: np.ndarray, polygons: list[np.ndarray]) -> int:
        """
        Detecta si el centro de un bounding box está dentro de alguno de los polígonos.

        Args:
            box (np.ndarray): Coordenadas del bounding box [x1, y1, x2, y2].
            polygons (list[np.ndarray]): Lista de polígonos a verificar.

        Returns:
            int: El índice del polígono si el centro está dentro, -1 en caso contrario.
        """
        center = self._get_center_bb(box)
        for i, polygon in enumerate(polygons):
            if cv2.pointPolygonTest(polygon, center, False) > 0:
                return i
        return -1

    def _register_zone_entry_exit(self, box: np.ndarray, track_id: int):
        """
        Registra la primera zona de entrada y/o salida que un objeto visita.
        
        Args:
            box (np.ndarray): Bounding box del objeto.
            track_id (int): ID de seguimiento del objeto.
        """
        # Registrar la primera entrada en una zona IN
        if track_id not in self.track_first_in_zone:
            zone_in_idx = self._get_zone_index(box, [zone["polygon"] for zone in self.zone_in_polygons])
            if zone_in_idx >= 0:
                self.track_first_in_zone[track_id] = zone_in_idx

        # Registrar la primera entrada en una zona OUT
        if track_id not in self.track_first_out_zone:
            zone_out_idx = self._get_zone_index(box, [zone["polygon"] for zone in self.zone_out_polygons])
            if zone_out_idx >= 0:
                self.track_first_out_zone[track_id] = zone_out_idx

                
    def _draw_bbox_and_track(self, box: np.ndarray, class_id: int, track_id: int, act_frame: int, confidence: float, annotator: Annotator):
        """
        Dibuja el bounding box y el historial de seguimiento de un objeto en el frame.
        También almacena los datos del objeto para el análisis posterior.

        Args:
            box (np.ndarray): Bounding box del objeto.
            class_id (int): Mapeo del ID de la clase detectada a la clase simplificada.
            track_id (int): ID de seguimiento del objeto.
            act_frame (int): Número del frame actual.
            confidence (float): Confianza de la detección.
            annotator (Annotator): Objeto Annotator de Ultralytics para dibujar.
        """

        # Dibujar el bounding box
        # annotator.box_label(box, label=f"ID: {track_id} - {self.class_names[class_id]}", color=(0, 0, 0), txt_color=(255, 255, 255))

        # Almacenar punto central del bounding box para dibujar el trazado
        center_x, center_y = self._get_center_bb(box)

        # Almacenar historial de datos del objeto
        self.data_obj_history[track_id].append({
            "act_frame": act_frame,
            "class_id": class_id,
            "confidence": confidence,
            "box": box.tolist(),
            "track_history_point": (center_x, center_y)
        })

    def _calculate_entropy(self, track_data: List[Dict]) -> Tuple[Counter, float]:
        """
        Calcula la entropía de Shanon para las clasificaciones de un objeto a lo largo de su seguimiento.

        Args:
            track_data (list[dict]): Lista de diccionarios con los datos de detección por frame
                                      para un track_id específico.

        Returns:
            tuple[Counter, float]: Un par que contiene:
                - Counter: Conteo de cada clase predicha para el objeto.
                - float: Valor de entropía calculado.
        """
        total_track = len(track_data)
        if total_track == 0:
            return Counter(), 0.0 # Evitar división por cero

        class_counts = Counter()
        for item in track_data:
            class_counts[item['class_id']] += 1
        
        probabilities = [count / total_track for class_id, count in class_counts.items()]
        
        entropy = -sum(p * math.log2(p) for p in probabilities if p > 0)
        
        return class_counts, entropy

    def _classify_track(self, class_counts: Counter) -> str:
        """
        Determina la clase final de un objeto basándose en su historial de clasificaciones.
        Prioriza la clase con el mayor conteo.

        Args:
            class_counts (Counter): Conteo de ocurrencias de cada clase en el historial.

        Returns:
            str: La clase asignada al objeto (ej: 'car', 'indeterminado').
        """
        if not class_counts:
            return "indeterminado" # No hay datos para clasificar
            
        # La clase asignada es la que tiene el mayor conteo
        assigned_class_id = max(class_counts, key=class_counts.get)
        # Usa .get para manejar casos donde un class_id podría no estar en self.class_names
        return self.class_names.get(assigned_class_id, "indeterminado")


    def _get_final_track_classifications(self):
        """
        Calcula la clasificación final para cada objeto rastreado basándose en su historial
        de datos de detección (clase y confianza por frame).
        Los resultados se almacenan en `self.track_results`.
        """
        for track_id, data in self.data_obj_history.items():
            class_counts, entropy = self._calculate_entropy(data)
            classification = self._classify_track(class_counts)
            self.track_results[track_id] = {
                "entropy": entropy,
                "classification": classification
            }

    def _get_final_track_transitions(self):
        """
        Calcula la clasificación final para cada objeto rastreado basándose en su historial
        de datos de detección (clase y confianza por frame).
        Los resultados se almacenan en `self.track_results`.
        """
        for track_id, data in self.track_results.items():
            classification = data.get("classification", "indeterminado")
            is_indeterminate_class = classification == "indeterminado"
            # La clasificación ya es el nombre "Transporte ..."
            display_class = classification

            # Solo sumar conteos globales por clase cuando no sea indeterminada
            if not is_indeterminate_class:
                self.total_vehicles_by_class[display_class] += 1

            # Crear el historial del objeto con sus datos
            history_track: Dict[str, Dict] = {}
            if track_id in self.data_obj_history and len(self.data_obj_history[track_id]) > 0:
                first_appearance_obj = self.data_obj_history[track_id][0]
                last_appearance_obj = self.data_obj_history[track_id][-1]

                history_track["first_appearance"] = {
                    "frame": first_appearance_obj.get("act_frame"),
                    "boundingBox": first_appearance_obj.get("box"),
                }
                history_track["last_appearance"] = {
                    "frame": last_appearance_obj.get("act_frame"),
                    "boundingBox": last_appearance_obj.get("box"),
                }
                # Guardar clase mostrable
                history_track["class"] = SIMPLIFIED_CLASS_DISPLAY_NAMES.get(
                    last_appearance_obj.get("class_id"), classification
                )

            # Conteos por zona de entrada y salida
            if track_id in self.track_first_in_zone:
                in_zone_idx = self.track_first_in_zone[track_id]
                in_zone_label = self.zone_in_polygons[in_zone_idx]["name"]
                self.entry_zone_counts[display_class][in_zone_label] += 1

            if track_id in self.track_first_out_zone:
                out_zone_idx = self.track_first_out_zone[track_id]
                out_zone_label = self.zone_out_polygons[out_zone_idx]["name"]
                self.exit_zone_counts[display_class][out_zone_label] += 1

            # Matriz de transiciones y reglas de exclusión en bordes
            if track_id in self.track_first_in_zone:
                in_zone_label = self.zone_in_polygons[self.track_first_in_zone[track_id]]["name"]
                if track_id in self.track_first_out_zone:
                    out_zone_label = self.zone_out_polygons[self.track_first_out_zone[track_id]]["name"]
                    transition_data = history_track.copy()
                    transition_data["labels"] = {"in": in_zone_label, "out": out_zone_label}
                    self.transition_determined_object[track_id] = transition_data
                    # Sumar a la matriz de conteo solo si la clase no es indeterminada
                    if not is_indeterminate_class:
                        self.transition_counts[in_zone_label][out_zone_label][display_class] += 1
                else:
                    # Entrada conocida, salida indeterminada
                    transition_data = history_track.copy()
                    transition_data["labels"] = {"in": in_zone_label, "out": ""}
                    last_fr = (history_track.get("last_appearance") or {}).get("frame")
                    if self.last_frame_index is not None and last_fr == self.last_frame_index:
                        # Excluir objetos que "se van" en el último frame
                        self.excluded_undetermined_ids.add(track_id)
                    else:
                        self.transition_undetermined_object[track_id] = transition_data
            elif track_id in self.track_first_out_zone:
                # Salida conocida, entrada indeterminada
                out_zone_label = self.zone_out_polygons[self.track_first_out_zone[track_id]]["name"]
                transition_data = history_track.copy()
                transition_data["labels"] = {"in": "", "out": out_zone_label}
                first_fr = (history_track.get("first_appearance") or {}).get("frame")
                if first_fr == 1:
                    # Excluir objetos que "aparecen" en el primer frame
                    self.excluded_undetermined_ids.add(track_id)
                else:
                    self.transition_undetermined_object[track_id] = transition_data
            else:
                # Entrada y salida indeterminadas
                transition_data = history_track.copy()
                transition_data["labels"] = {"in": "", "out": ""}
                first_fr = (history_track.get("first_appearance") or {}).get("frame")
                last_fr = (history_track.get("last_appearance") or {}).get("frame")
                exclude = False
                if first_fr == 1:
                    exclude = True
                if self.last_frame_index is not None and last_fr == self.last_frame_index:
                    exclude = True
                if exclude:
                    self.excluded_undetermined_ids.add(track_id)
                else:
                    self.transition_undetermined_object[track_id] = transition_data


    def process_frame(self, frame: np.ndarray, results: list, act_frame: int) -> np.ndarray:
        """
        Procesa un solo frame del video para detectar, rastrear y analizar objetos.

        Args:
            frame (np.ndarray): El frame actual del video.
            results (list): Resultados de la detección/seguimiento de YOLO para el frame.
            act_frame (int): El número del frame actual.

        Returns:
            np.ndarray: El frame anotado con bounding boxes, trazas y zonas.
        """
    # Dibujar las zonas de entrada y salida
        self._draw_zones_in_out(frame, 2)
        
        # Procesar los resultados de seguimiento si hay objetos detectados
        if results and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu()
            class_ids = results[0].boxes.cls.cpu().tolist()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            confs = results[0].boxes.conf.float().cpu().tolist()
            
            # Inicializar el anotador de Ultralytics
            annotator = Annotator(frame, line_width=1)

            # Iterar sobre cada objeto detectado y rastreado
            for box, class_id, track_id, confidence in zip(boxes, class_ids, track_ids, confs):
                # Registrar la primera entrada y salida en las zonas
                self._register_zone_entry_exit(box, track_id)
                
                # Dibujar bounding box, etiqueta y historial de seguimiento, y almacenar datos
                self._draw_bbox_and_track(box, class_id, track_id, act_frame, confidence, annotator)
        
        return frame

    def run(self, video_path: str, max_frames: Optional[int] = None, output_video_path: Optional[str] = None, display_video: bool = True):
        """
        Ejecuta el proceso de seguimiento de objetos en un video.

        Args:
            video_path (str): Ruta al archivo de video de entrada.
            max_frames (int, optional): Número máximo de frames a procesar. Por defecto, None (todo el video).
            output_video_path (str, optional): Ruta donde guardar el video de salida.
                                               Si es None, se usa la lógica de generación por defecto.
            display_video (bool): Si es True, muestra la ventana del video. Por defecto: True.
        """
            
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print(f"Error: No se pudo abrir el video en {video_path}")
            return

        w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))

        # Intentar obtener el número total de frames para el progreso
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames_to_process = total_frames
        if max_frames is not None:
            frames_to_process = min(total_frames if total_frames > 0 else float('inf'), max_frames)

        # Si el número de frames es incierto o 0, deshabilitar el progreso en porcentaje
        progress_enabled = frames_to_process > 0 and frames_to_process != float('inf')

        act_frame = 0  # Contador de frames leídos (no de frames procesados por YOLO)
        print(f"Procesando video: {video_path} (dimensiones: {w}x{h}, FPS: {fps})")

        # Escritor del video de salida. Se abre solo si se pidió una ruta.
        writer = None
        if output_video_path:
            os.makedirs(os.path.dirname(output_video_path) or ".", exist_ok=True)
            # FPS de respaldo: algunos contenedores reportan 0 y VideoWriter lo rechaza.
            out_fps = fps if fps and fps > 0 else 25
            writer = cv2.VideoWriter(
                output_video_path,
                cv2.VideoWriter_fourcc(*"mp4v"),
                out_fps,
                (w, h),
            )
            if not writer.isOpened():
                writer.release()
                cap.release()
                raise RuntimeError(
                    f"No se pudo abrir el escritor de video en {output_video_path} "
                    f"(codec mp4v, {w}x{h} @ {out_fps} FPS)."
                )
            print(f"Guardando video procesado en: {output_video_path}")
        else:
            print(
                "No se guardará el video procesado (output_video_path no especificado y no se pudo determinar un valor por defecto)."
            )

        last_reported_percentage = -1
        success = True
        while cap.isOpened():
            success, frame = cap.read()

            if not success:
                print("\nFin del video o error al leer frame.")
                break
            
            act_frame += 1

            # Mostrar progreso en la terminal
            if progress_enabled:
                current_percentage = int((act_frame / frames_to_process) * 100)
                # Actualiza el progreso solo si ha cambiado al menos un 1% para evitar spam de terminal
                # o cada 50 frames (para videos cortos o progreso lento)
                if current_percentage > last_reported_percentage or (act_frame % 50 == 0 and last_reported_percentage < 100):
                    sys.stdout.write(f"\rProgreso: {current_percentage}% completado ({act_frame}/{frames_to_process} frames)")
                    sys.stdout.flush()
                    last_reported_percentage = current_percentage
            else:
                if act_frame % 50 == 0: # Muestra un punto cada 50 frames si el progreso porcentual no es posible
                    sys.stdout.write(".")
                    sys.stdout.flush()


            # Si se especificó un número máximo de frames, detenerse al alcanzarlo
            if max_frames is not None and act_frame > max_frames:
                print(f"\nAlcanzado el número máximo de frames ({max_frames}). Deteniendo.")
                break

            # Realizar seguimiento de objetos
            # Aplicar máscara de exclusión antes de inferir
            masked_for_inference = self._apply_exclusion_mask(frame)
            results = self.model.track(masked_for_inference, conf=0.3, iou=0.6, persist=True, verbose=False, agnostic_nms=True, tracker=self.tracker_path)
            
            # Procesar el frame (dibujar zonas, BBs, etc.)
            # También aplicar la máscara al frame de salida para que "no se vea"
            masked_for_output = self._apply_exclusion_mask(frame)
            processed_frame = self.process_frame(masked_for_output, results, act_frame)

            if writer is not None:
                writer.write(processed_frame)

            # Mostrar el frame procesado SOLO SI display_video es True
            if display_video:
                cv2.imshow("Video", processed_frame)
                # Salir si se presiona 'q' (solo si la ventana de video está activa)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("\nTecla 'q' presionada. Deteniendo.")
                    break
        # Asegurarse de una nueva línea al final del progreso
        if progress_enabled:
            # El -1 en act_frame es porque act_frame se incrementa antes de la verificación de fin de video
            # Si el bucle termina por "not success", act_frame ya está un paso más allá del último frame válido.
            sys.stdout.write(f"\rProgreso: 100% completado ({act_frame-1 if not success else act_frame}/{frames_to_process} frames)\n")
            sys.stdout.flush()
        else:
            print("\n")  # Nueva línea después de los puntos de progreso si no se usó el progreso porcentual

        # Guardar último frame procesado
        self.last_frame_index = act_frame

        # Liberar recursos
        cap.release()
        if writer is not None:
            writer.release()

        # Destruir ventanas SOLO si se mostraron
        if display_video:
            cv2.destroyAllWindows()

        # Una vez terminado el procesamiento de frames, calcular los resultados finales de las clasificaciones y las transiciones
        self._get_final_track_classifications()
        self._get_final_track_transitions()


if __name__ == "__main__":
    # --- Configuración de Argumentos de Línea de Comandos ---
    parser = argparse.ArgumentParser(
        description="Realiza seguimiento de objetos en videos y genera un informe de tránsito.",
        formatter_class=argparse.RawTextHelpFormatter # Permite formatear el texto de ayuda
    )
    parser.add_argument(
        '--input_video_path', '-i', type=str, required=True,
        help='Ruta al archivo de video de entrada. Obligatorio.'
    )
    parser.add_argument(
        '--model_path', '-m', type=str, required=True,
        help='Ruta al archivo del modelo YOLO (.pt). Obligatorio.'
    )
    parser.add_argument(
        '--tracker_path', '-t', type=str, required=True,
        help='Ruta al archivo del tracker. Obligatorio.'
    )
    parser.add_argument(
        '--polygons_in', '-pi', type=ast.literal_eval, required=True,
        help='Polígonos de entrada como lista de listas. Ejemplo: "[[816, 922], [905, 869], [1095, 908], [987, 990]]". Obligatorio.'
    )
    parser.add_argument(
        '--polygons_out', '-po', type=ast.literal_eval, required=True,
        help='Polígonos de salida como lista de listas. Ejemplo: "[[816, 922], [905, 869], [1095, 908], [987, 990]]". Obligatorio.'
    )
    parser.add_argument(
        '--excluded_zones', '-ez', type=ast.literal_eval, required=False, default=[],
        help='Zonas excluidas (máscaras negras) como lista de polígonos.'
    )
    parser.add_argument(
        '--names_polygons_in', '-ni', type=ast.literal_eval, required=True,
        help='Nombres de los polígonos de entrada como lista de strings. Ejemplo: "["Zona 1", "Zona 2", "Zona 3"]". Obligatorio.'
    )
    parser.add_argument(
        '--names_polygons_out', '-no', type=ast.literal_eval, required=True,
        help='Nombres de los polígonos de salida como lista de strings. Ejemplo: "["Zona 1", "Zona 2", "Zona 3"]". Obligatorio.'
    )
    parser.add_argument(
        '--output_video_path', '-o', type=str, default=None,
        help='Ruta opcional para guardar el video de salida. \n'
             'Por defecto, el video se guarda en la misma ubicación del video de entrada, \n'
             'dentro de una subcarpeta con el nombre del modelo (sin .pt), \n'
             'y con el nombre original del video + "_processed". Ejemplo: si el video es \n'
             '"video.mp4" y el modelo es "model.pt", la salida será "video_dir/model/video_processed.mp4".'
    )
    parser.add_argument(
        '--max_frames', '-f', type=int, default=None,
        help='Número máximo de frames a procesar. Por defecto, se procesa el video completo.'
    )
    parser.add_argument(
        '--no_display', action='store_true',
        help='Si se incluye este flag, NO se mostrará la ventana del video durante el procesamiento. \n'
             'Por defecto (sin el flag), el video SÍ se muestra.'
    )

    args = parser.parse_args()

    # 1. Determinar la ruta de salida del video
    final_output_video_path = args.output_video_path
    
    # Si no se proporcionó una ruta de salida, generar la por defecto
    if final_output_video_path is None:
        input_dir = os.path.dirname(args.input_video_path)
        if not input_dir:
            input_dir = "."
        
        input_filename_without_ext, input_ext = os.path.splitext(os.path.basename(args.input_video_path))
        
        model_base_name = os.path.splitext(os.path.basename(args.model_path))[0]
        
        output_dir = os.path.join(input_dir, input_filename_without_ext)
        os.makedirs(output_dir, exist_ok=True)
        
        output_filename = f"processed{input_ext}"
        final_output_video_path = os.path.join(output_dir, output_filename)
    
    show_video_window = not args.no_display
    
    # 2. Obtener las zonas de entrada y salida del video
    ZONE_IN_POLYGONS = [np.array(p, dtype=np.int32) for p in args.polygons_in]
    ZONE_OUT_POLYGONS = [np.array(p, dtype=np.int32) for p in args.polygons_out]
    EXCLUDED_POLYGONS = [np.array(p, dtype=np.int32) for p in (args.excluded_zones or [])]
    
    # 3. Crear una instancia del ObjectTracker
    tracker = ObjectTracker(args.model_path, args.tracker_path, ZONE_IN_POLYGONS, ZONE_OUT_POLYGONS, device=DEVICE_TO_USE, names_polygons_in=args.names_polygons_in, names_polygons_out=args.names_polygons_out, excluded_polygons=EXCLUDED_POLYGONS)

    # 4. Ejecutar el proceso de seguimiento
    tracker.run(
        video_path=args.input_video_path, 
        max_frames=args.max_frames, 
        output_video_path=final_output_video_path,
        display_video=show_video_window
    )

    # 5. Guardar resultados en archivos JSON
    with open(f"{output_dir}/data_obj_history.json", "w", encoding="utf-8") as f:
        # Excluir IDs marcados como indeterminados en límites (frame 1 o último)
        serializable_dict = {str(k): v for k, v in tracker.data_obj_history.items() if int(k) not in tracker.excluded_undetermined_ids}
        json.dump(serializable_dict, f, ensure_ascii=False, indent=2)
        
    with open(f"{output_dir}/transition_determined_object.json", "w", encoding="utf-8") as f:
        serializable_dict = {str(k): v for k, v in tracker.transition_determined_object.items()}
        json.dump(serializable_dict, f, ensure_ascii=False, indent=2)
        
    with open(f"{output_dir}/transition_undetermined_object.json", "w", encoding="utf-8") as f:
        serializable_dict = {str(k): v for k, v in tracker.transition_undetermined_object.items()}
        json.dump(serializable_dict, f, ensure_ascii=False, indent=2)
    
    with open(f"{output_dir}/transition_counts.json", "w", encoding="utf-8") as f:
        serializable_dict = {str(k): v for k, v in tracker.transition_counts.items()}
        json.dump(serializable_dict, f, ensure_ascii=False, indent=2)