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

# Longitud máxima del historial de seguimiento de un objeto
TRACK_HISTORY_LENGTH = 30 

# Mapeo de índices de zona a etiquetas (A, B, C, D) para el informe
ZONE_LABELS = {0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'IND'}
# Orden de las etiquetas de zona para iterar consistentemente
ORDERED_ZONE_LABELS = ['A', 'B', 'C', 'D', 'IND']

# Mapeo de ID de clases a nombres de clases simplificadas
SIMPLIFIED_CLASS_DISPLAY_NAMES = {
    0: "light_transport", # Bicicleta
    1: "heavy_transport", # Colectivo
    2: "medium_transport", # Auto
    3: "heavy_transport", # Camión pesado
    4: "heavy_transport", # Camión liviano
    5: "light_transport" # Moto
}


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

    def __init__(self, model_path: str, zone_in_polygons: list[np.ndarray], zone_out_polygons: list[np.ndarray], device: Optional[str] = None):
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
        
        # self.class_names = self.model.model.names # Nombres de clases del modelo (ej: 'car', 'bus')
        self.class_names = SIMPLIFIED_CLASS_DISPLAY_NAMES
        
        # Lista de todos los nombres de clases conocidos, incluyendo 'indeterminado'
        self.all_class_names = list(self.class_names.values()) + ["indeterminado"]
        
        self.zone_in_polygons = zone_in_polygons
        self.zone_out_polygons = zone_out_polygons

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
        
        # Matriz de transición de zonas
        self.transition_object: defaultdict[int, list[str, str]] = defaultdict(list)
            
        print(f"Modelo YOLO cargado. Utilizando dispositivo: {self.device}")

    def _get_torch_device(self, preferred_device: Optional[str]) -> torch.device: # type: ignore
        """
        Determina el dispositivo PyTorch a usar (CPU o GPU) basado en la preferencia
        y la disponibilidad del hardware.
        """
        if torch is None:
            return torch.device("cpu") # PyTorch no está disponible, forzar CPU

        if preferred_device == "cpu":
            return torch.device("cpu")
        elif preferred_device == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            else:
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

    def _draw_polygon(self, annotated_frame: np.ndarray, polygon: np.ndarray, number_polygon: int, zone_type: ZoneType, thickness: int) -> np.ndarray:
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
        cv2.putText(annotated_frame, str(number_polygon), (int(zone_center.x), int(zone_center.y)), font, font_scale, color, thickness=thickness)
        
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
            self._draw_polygon(annotated_frame, zone_in, i, ZoneType.IN, thickness)
            self._draw_polygon(annotated_frame, zone_out, i, ZoneType.OUT, thickness)
        return annotated_frame

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
            zone_in_idx = self._get_zone_index(box, self.zone_in_polygons)
            if zone_in_idx >= 0:
                self.track_first_in_zone[track_id] = zone_in_idx

        # Registrar la primera entrada en una zona OUT
        if track_id not in self.track_first_out_zone:
            zone_out_idx = self._get_zone_index(box, self.zone_out_polygons)
            if zone_out_idx >= 0:
                self.track_first_out_zone[track_id] = zone_out_idx

                
    def _draw_bbox_and_track(self, box: np.ndarray, class_id: int, track_id: int, act_frame: int, confidence: float, frame: np.ndarray):
        """
        Dibuja el bounding box y el historial de seguimiento de un objeto en el frame.
        También almacena los datos del objeto para el análisis posterior.

        Args:
            frame (np.ndarray): Frame actual.
            annotator (Annotator): Objeto Annotator de Ultralytics para dibujar.
            box (np.ndarray): Bounding box del objeto.
            class_id (int): Mapeo del ID de la clase detectada a la clase simplificada.
            track_id (int): ID de seguimiento del objeto.
            act_frame (int): Número del frame actual.
            confidence (float): Confianza de la detección.
        """

        # Almacenar historial de datos del objeto para el cálculo de entropía
        self.data_obj_history[track_id].append({
            "act_frame": act_frame,
            "class_id": class_id,
            "confidence": confidence,
            "box": box.tolist()
        })

        # Almacenar punto central del bounding box para dibujar el trazado
        center_x, center_y = self._get_center_bb(box)
        self.track_history[track_id].append((center_x, center_y))
        
        # Dibujar el bounding box (bbox) del objeto
        label = self.class_names.get(class_id, "indeterminado")
        annotator = Annotator(frame, line_width=1)
        annotator.box_label(box, f"{track_id} - {label}")

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
            
            if classification == "indeterminado":
                continue

            # Cálculo de la Matriz de Transiciones para cada objeto
            if track_id in self.track_first_in_zone:
                in_zone_label = ZONE_LABELS.get(self.track_first_in_zone[track_id], f"Zona {self.track_first_in_zone[track_id]}")
                
                if track_id in self.track_first_out_zone:
                    out_zone_label = ZONE_LABELS.get(self.track_first_out_zone[track_id], f"Zona {self.track_first_out_zone[track_id]}")
                    self.transition_object[track_id].append((in_zone_label, out_zone_label))
                else:
                    # Objeto entró a una zona IN pero no salió por ninguna zona OUT definida
                    self.transition_object[track_id].append((in_zone_label, "IND"))
            elif track_id in self.track_first_out_zone:
                out_zone_label = ZONE_LABELS.get(self.track_first_out_zone[track_id], f"Zona {self.track_first_out_zone[track_id]}")
                self.transition_object[track_id].append(("IND", out_zone_label))
            else:
                self.transition_object[track_id].append(("IND", "IND"))


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
                self._draw_bbox_and_track(box, class_id, track_id, act_frame, confidence, frame)
        
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
        
        video_writer = None
        # Solo intentar crear el VideoWriter si output_video_path no es None
        if output_video_path is not None:
            try:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
                video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (w, h))
                if not video_writer.isOpened():
                    print(f"Advertencia: No se pudo abrir VideoWriter para {output_video_path}. El video no se guardará.")
                    video_writer = None
            except Exception as e:
                print(f"Error al inicializar VideoWriter: {e}. El video no se guardará.")
                video_writer = None

        act_frame = 0 # Contador de frames leídos (no de frames procesados por YOLO)
        print(f"Procesando video: {video_path} (dimensiones: {w}x{h}, FPS: {fps})")
        if output_video_path:
            print(f"Guardando video procesado en: {output_video_path}")
        else:
            print(f"No se guardará el video procesado (output_video_path no especificado y no se pudo determinar un valor por defecto).")

        last_reported_percentage = -1
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

            # Procesar solo cada segundo frame, como en el código original
            if act_frame % 2 == 0:
                # Si el frame se redimensiona, aplicar aquí si es necesario
                # alto_original, ancho_original = frame.shape[:2]
                # ancho_nuevo = 1920
                # alto_nuevo = int(alto_original * (ancho_nuevo / ancho_original))
                # frame = cv2.resize(frame, (ancho_nuevo, alto_nuevo))

                # Realizar seguimiento de objetos
                results = self.model.track(frame, persist=True, verbose=False, agnostic_nms=True, tracker="botsort_custom.yaml")
                
                # Procesar el frame (dibujar zonas, BBs, etc.)
                processed_frame = self.process_frame(frame, results, act_frame)
                
                # Escribir el frame en el archivo de salida si el VideoWriter está activo
                if video_writer:
                    video_writer.write(processed_frame)

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
            print("\n") # Nueva línea después de los puntos de progreso si no se usó el progreso porcentual

        # Liberar recursos
        cap.release()
        if video_writer:
            video_writer.release()
        
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

    # --- Determinar la ruta de salida del video ---
    final_output_video_path = args.output_video_path
    
    # Si no se proporcionó una ruta de salida, generar la por defecto
    if final_output_video_path is None:
        input_dir = os.path.dirname(args.input_video_path)
        if not input_dir:
            input_dir = "."
        
        input_filename_without_ext, input_ext = os.path.splitext(os.path.basename(args.input_video_path))
        
        model_base_name = os.path.splitext(os.path.basename(args.model_path))[0]
        
        output_dir = os.path.join(input_dir, model_base_name)
        os.makedirs(output_dir, exist_ok=True)
        
        output_filename = f"{input_filename_without_ext}_processed{input_ext}"
        final_output_video_path = os.path.join(output_dir, output_filename)
    
    show_video_window = not args.no_display
    
    # 1. Obtener las zonas de entrada y salida del video
    with open('polygons_dictionary.json', 'r') as f:
        polygons_dictionary = json.load(f)
    
    video_name = os.path.splitext(os.path.basename(args.input_video_path))[0]
    if video_name not in polygons_dictionary:
        print(f"Error: El video '{video_name}' no tiene zonas definidas en polygons_dictionary.json.")
        sys.exit(1)
    if "ZONE_IN_POLYGONS" not in polygons_dictionary[video_name] or "ZONE_OUT_POLYGONS" not in polygons_dictionary[video_name]:
        print(f"Error: Faltan claves 'ZONE_IN_POLYGONS' o 'ZONE_OUT_POLYGONS' para el video '{video_name}' en polygons_dictionary.json.")
        sys.exit(1)
        
    ZONE_IN_POLYGONS = [np.array(p) for p in polygons_dictionary[video_name]["ZONE_IN_POLYGONS"]]
    ZONE_OUT_POLYGONS = [np.array(p) for p in polygons_dictionary[video_name]["ZONE_OUT_POLYGONS"]]
    
    # 2. Crear una instancia del ObjectTracker
    tracker = ObjectTracker(args.model_path, ZONE_IN_POLYGONS, ZONE_OUT_POLYGONS, device=DEVICE_TO_USE)

    # 3. Ejecutar el proceso de seguimiento
    tracker.run(
        video_path=args.input_video_path, 
        max_frames=args.max_frames, 
        output_video_path=final_output_video_path,
        display_video=show_video_window
    )

    # 4. Imprimir el informe final
    # tracker.get_report()
    
    # Guardar tracker.data_obj_history en un archivo JSON
    with open("data_obj_history.json", "w", encoding="utf-8") as f:
        # Convertir las claves a str para que sea serializable en JSON
        serializable_dict = {str(k): v for k, v in tracker.data_obj_history.items()}
        json.dump(serializable_dict, f, ensure_ascii=False, indent=2)
        
    print(tracker.transition_object)
    with open("transition_object.json", "w", encoding="utf-8") as f:
        # Convertir las claves a str para que sea serializable en JSON
        serializable_dict = {str(k): v for k, v in tracker.transition_object.items()}
        json.dump(serializable_dict, f, ensure_ascii=False, indent=2)
        