# %%
import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import math
from collections import Counter, defaultdict, deque
from enum import Enum
from typing import Optional, Dict, List, Tuple
from ultralytics.utils.plotting import Annotator, colors

# --- CONFIGURACIÓN Y CONSTANTES ---

# Paleta de colores para las zonas: [verde para entrada, rojo para salida]
ZONE_COLORS = sv.ColorPalette.from_hex(["#00FF00", "#FF0000"])

# Definición de las zonas de entrada (polígonos)
# Cada polígono es un array de puntos [x, y]
ZONE_IN_POLYGONS = [
    np.array([[1021, 969], [1154, 982], [1218, 825], [1088, 808]]),
    np.array([[1510, 514], [1583, 459], [1378, 402], [1359, 453]]),
    np.array([[995, 227], [923, 211], [834, 268], [921, 288]]),
    np.array([[393, 540], [449, 467], [549, 507], [480, 593]]),
]

# Definición de las zonas de salida (polígonos)
ZONE_OUT_POLYGONS = [
    np.array([[759, 962], [921, 951], [863, 806], [714, 823]]),
    np.array([[1419, 562], [1433, 654], [1586, 619], [1547, 536]]),
    np.array([[1063, 290], [1156, 271], [1138, 197], [1029, 207]]),
    np.array([[462, 452], [456, 366], [624, 347], [607, 434]]),
]

# Ruta del modelo YOLO pre-entrenado
MODEL_PATH = "model-v5.pt"

# Longitud máxima del historial de seguimiento de un objeto
TRACK_HISTORY_LENGTH = 30 

# Mapeo de índices de zona a etiquetas (A, B, C, D) para el informe
ZONE_LABELS = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}

# Mapeo de nombres de clases (del modelo) a nombres para el informe
CLASS_DISPLAY_NAMES = {
    "car": "Auto",
    "bus": "Colectivo",
    "light_truck": "Camión liviano",
    "heavy_truck": "Camión pesado",
    "motorbike": "Moto",
    "bicycle": "Bicicleta",
    "indeterminado": "Indeterminado" 
}

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

    def __init__(self, model_path: str, zone_in_polygons: list[np.ndarray], zone_out_polygons: list[np.ndarray]):
        """
        Inicializa el ObjectTracker.

        Args:
            model_path (str): Ruta al archivo del modelo YOLO.
            zone_in_polygons (list[np.ndarray]): Lista de polígonos NumPy que definen las zonas de entrada.
            zone_out_polygons (list[np.ndarray]): Lista de polígonos NumPy que definen las zonas de salida.
        """
        self.model = YOLO(model_path)
        self.class_names = self.model.model.names # Nombres de clases del modelo (ej: 'car', 'bus')
        
        # Lista de todos los nombres de clases conocidos, incluyendo 'indeterminado'
        self.all_class_names = list(self.class_names.values()) 
        if "indeterminado" not in self.all_class_names: # Asegura que se añada solo una vez si no existe
            self.all_class_names.append("indeterminado")
        
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
        
        # Conteo final de transiciones por tipo de vehículo, zona de entrada y zona de salida
        # Estructura: {vehicle_type_display_name: {in_zone_label: {out_zone_label: count}}}
        self.transition_counts: defaultdict[str, defaultdict[str, defaultdict[str, int]]] = \
            defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

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

                
    def _draw_bbox_and_track(self, frame: np.ndarray, annotator: Annotator, box: np.ndarray, 
                             class_id: int, track_id: int, act_frame: int, confidence: float):
        """
        Dibuja el bounding box y el historial de seguimiento de un objeto en el frame.
        También almacena los datos del objeto para el análisis posterior.

        Args:
            frame (np.ndarray): Frame actual.
            annotator (Annotator): Objeto Annotator de Ultralytics para dibujar.
            box (np.ndarray): Bounding box del objeto.
            class_id (int): ID de la clase detectada.
            track_id (int): ID de seguimiento del objeto.
            act_frame (int): Número del frame actual.
            confidence (float): Confianza de la detección.
        """
        # Dibujar bounding box y etiqueta
        annotator.box_label(box, color=colors(class_id, True), label=f"{track_id} - {self.class_names[class_id]}")

        # Almacenar historial de datos del objeto para el cálculo de entropía
        self.data_obj_history[track_id].append({
            "act_frame": act_frame,
            "class_id": class_id,
            "confidence": confidence
        })

        # Almacenar punto central del bounding box para dibujar el trazado
        center_x, center_y = self._get_center_bb(box)
        self.track_history[track_id].append((center_x, center_y))

        # Dibujar trazado del historial de seguimiento
        points = np.array(self.track_history[track_id], dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [points], isClosed=False, color=colors(class_id, True), thickness=2)

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

    def _compile_transition_data(self):
        """
        Compila los datos de transición (entrada -> salida) para cada vehículo clasificado.
        Popula el diccionario `self.transition_counts`.
        """
        for track_id, result in self.track_results.items():
            classification = result.get("classification")
            
            # Solo procesamos si el objeto tiene una clasificación válida y pasó por ambas zonas
            if classification and track_id in self.track_first_in_zone and track_id in self.track_first_out_zone:
                in_zone_idx = self.track_first_in_zone[track_id]
                out_zone_idx = self.track_first_out_zone[track_id]

                in_zone_label = ZONE_LABELS.get(in_zone_idx, f"Zona {in_zone_idx}")
                out_zone_label = ZONE_LABELS.get(out_zone_idx, f"Zona {out_zone_idx}")

                # Usar los nombres amigables si están definidos, sino el nombre del modelo
                display_class = CLASS_DISPLAY_NAMES.get(classification, classification)

                self.transition_counts[display_class][in_zone_label][out_zone_label] += 1


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
            confidences = results[0].boxes.conf.float().cpu().tolist()
            
            # Inicializar el anotador de Ultralytics
            annotator = Annotator(frame, line_width=1)

            # Iterar sobre cada objeto detectado y rastreado
            for box, class_id, track_id, confidence in zip(boxes, class_ids, track_ids, confidences):
                # Registrar la primera entrada y salida en las zonas
                self._register_zone_entry_exit(box, track_id)
                
                # Dibujar bounding box, etiqueta y historial de seguimiento, y almacenar datos
                self._draw_bbox_and_track(frame, annotator, box, class_id, track_id, act_frame, confidence)
        
        return frame

    def run(self, video_path: str, max_frames: Optional[int] = None, output_video_path: Optional[str] = None):
        """
        Ejecuta el proceso de seguimiento de objetos en un video.

        Args:
            video_path (str): Ruta al archivo de video de entrada.
            max_frames (int, optional): Número máximo de frames a procesar. Por defecto, None (todo el video).
            output_video_path (str, optional): Ruta donde guardar el video de salida.
                                               Por defecto, None (no guarda el video).
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            print(f"Error: No se pudo abrir el video en {video_path}")
            return

        w, h, fps = (int(cap.get(x)) for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS))

        video_writer = None
        if output_video_path:
            try:
                # Codec para MP4V (compatible con .avi o .mp4 dependiendo del sistema)
                fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
                video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (w, h))
                if not video_writer.isOpened():
                    print(f"Advertencia: No se pudo abrir VideoWriter para {output_video_path}. El video no se guardará.")
                    video_writer = None
            except Exception as e:
                print(f"Error al inicializar VideoWriter: {e}. El video no se guardará.")
                video_writer = None

        act_frame = 0 # Contador de frames procesados
        print(f"Procesando video: {video_path} (dimensiones: {w}x{h}, FPS: {fps})")

        while cap.isOpened():
            success, frame = cap.read()

            if not success:
                print("Fin del video o error al leer frame.")
                break
            
            act_frame += 1

            # Si se especificó un número máximo de frames, detenerse al alcanzarlo
            if max_frames and act_frame > max_frames:
                print(f"Alcanzado el número máximo de frames ({max_frames}). Deteniendo.")
                break

            # Procesar solo cada segundo frame, como en el código original
            if act_frame % 2 == 0:
                # Si el frame se redimensiona, aplicar aquí si es necesario
                # alto_original, ancho_original = frame.shape[:2]
                # ancho_nuevo = 1920
                # alto_nuevo = int(alto_original * (ancho_nuevo / ancho_original))
                # frame = cv2.resize(frame, (ancho_nuevo, alto_nuevo))

                # Realizar seguimiento de objetos
                results = self.model.track(frame, persist=True, verbose=False, agnostic_nms=True)
                
                # Procesar el frame (dibujar zonas, BBs, etc.)
                processed_frame = self.process_frame(frame, results, act_frame)
                
                # Mostrar el frame procesado
                cv2.imshow("Video", processed_frame)
                
                # Escribir el frame en el archivo de salida si el VideoWriter está activo
                if video_writer:
                    video_writer.write(processed_frame)
                
                # Salir si se presiona 'q'
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("Tecla 'q' presionada. Deteniendo.")
                    break
        
        # Liberar recursos
        cap.release()
        if video_writer:
            video_writer.release()
        cv2.destroyAllWindows()
        
        # Una vez terminado el procesamiento de frames, calcular los resultados finales
        self._get_final_track_classifications()
        self._compile_transition_data()


    def get_report(self):
        """
        Imprime los resultados finales del seguimiento de objetos.
        Incluye el conteo total de vehículos por categoría y la matriz de transiciones
        (entrada a salida).
        """
        print("\n--- INFORME FINAL ---")

        # 1. Cuántos vehículos de cada categoría reconoció
        total_vehicles_by_class = Counter()
        for track_id, result in self.track_results.items():
            classification = result.get("classification")
            if classification and classification != "indeterminado": # Excluir indeterminados del total de vehículos clasificados
                # Usar los nombres amigables para la visualización
                display_class = CLASS_DISPLAY_NAMES.get(classification, classification)
                total_vehicles_by_class[display_class] += 1
        
        print("\nTotal de vehículos reconocidos por categoría (clasificados):")
        if not total_vehicles_by_class:
            print("  Ningún vehículo clasificado reconocido.")
        else:
            # Ordenar las clases para una salida consistente
            # Asegurarse de que todas las clases amigables estén en la lista, incluso si su cuenta es 0
            all_display_names = sorted(list(CLASS_DISPLAY_NAMES.values()))
            for cls_name in all_display_names:
                # No imprimir indeterminados aquí si su cuenta es 0
                if cls_name == "Indeterminado" and total_vehicles_by_class[cls_name] == 0:
                    continue
                print(f"  {cls_name}: {total_vehicles_by_class[cls_name]}")

        # 2. Matriz de transiciones entrada-salida por categoría
        print("\nMatriz de Tránsito (Entrada -> Salida):")
        
        # Obtener las etiquetas de las zonas de entrada y salida
        input_zone_labels = [ZONE_LABELS.get(i, f"Zona {i}") for i in range(len(self.zone_in_polygons))]
        output_zone_labels = [ZONE_LABELS.get(i, f"Zona {i}") for i in range(len(self.zone_out_polygons))]
        
        # Obtener una lista ordenada de todas las clases de vehículos para las filas de la tabla
        # Filtramos 'Indeterminado' porque no tiene sentido en una tabla de tránsito clasificado
        all_vehicle_types = sorted([name for name in CLASS_DISPLAY_NAMES.values() if name != "Indeterminado"]) 
        
        # Calcular el ancho máximo de la primera columna ('Vehículos') para alinear
        first_col_width = len("Vehículos")
        for v_type in all_vehicle_types:
            first_col_width = max(first_col_width, len(v_type))
        first_col_width = max(first_col_width, len("Total")) # Para la fila 'Total'

        # Imprimir encabezados
        # Línea principal: "Vehículos" | "Entrada A" | "Entrada B" | ...
        header_line_1_parts = [f"{'Vehículos':<{first_col_width}}"]
        for in_label in input_zone_labels:
            # Cada "Entrada X" abarcará el ancho de todas las "Salida" sub-columnas (num_out_zones * cell_width + (num_out_zones-1)*pipe_width)
            # asumiendo cell_width es 8 y pipe_width es 1, entonces 4*8 + 3 = 35. Ajustamos a 37 para el pipe final
            block_width = (len(output_zone_labels) * 8) + (len(output_zone_labels) - 1) * 1 + 1 # 8 chars per count, 1 for pipe. Last pipe is part of next block
            header_line_1_parts.append(f"| {('Entrada ' + in_label):^{block_width-1}}")
        print("".join(header_line_1_parts))
        
        # Línea de sub-encabezado: Vacío | "Salida A" | "Salida B" | ... (repetido para cada Entrada)
        sub_header_line_2_parts = [f"{'':<{first_col_width}}"]
        for _ in input_zone_labels:
            for out_label in output_zone_labels:
                sub_header_line_2_parts.append(f"| {('Salida ' + out_label):<8}") # 8 chars per 'Salida X'
        print("".join(sub_header_line_2_parts))

        # Imprimir línea separadora
        total_header_width = first_col_width + (len(input_zone_labels) * (len(output_zone_labels) * 9)) # first_col + (num_in_zones * (num_out_zones * 9))
        print("-" * (total_header_width + len(input_zone_labels) * 2)) # Ajuste manual para la longitud de la línea.

        # Pre-calcular totales por columna para la fila "Total"
        # Esto es un diccionario donde la clave es (in_label, out_label) y el valor es el total
        overall_column_totals: defaultdict[Tuple[str, str], int] = defaultdict(int)

        # Imprimir filas de datos
        for vehicle_type in all_vehicle_types:
            row_output_parts = [f"{vehicle_type:<{first_col_width}}"]
            for in_label in input_zone_labels:
                for out_label in output_zone_labels:
                    count = self.transition_counts[vehicle_type][in_label][out_label]
                    row_output_parts.append(f"| {count:<8}") # Cada celda de conteo: 8 caracteres para el número
                    overall_column_totals[(in_label, out_label)] += count
            print("".join(row_output_parts))

        # Imprimir línea separadora antes del total
        print("-" * (total_header_width + len(input_zone_labels) * 2))

        # Imprimir fila "Total"
        total_row_output_parts = [f"{'Total':<{first_col_width}}"]
        for in_label in input_zone_labels:
            for out_label in output_zone_labels:
                total_count = overall_column_totals[(in_label, out_label)]
                total_row_output_parts.append(f"| {total_count:<8}")
        print("".join(total_row_output_parts))
        
        print("\n--- Fin del informe ---")

# %%
if __name__ == "__main__":
    # Ruta del video de entrada
    VIDEO_INPUT_PATH = "vuelo03_1080p.mp4"
    # Ruta opcional para guardar el video de salida
    VIDEO_OUTPUT_PATH = "object_tracking_refactored_output.mp4" 
    # Número de frames a procesar (None para todo el video, 500 para limitar)
    # Se recomienda None si el video es corto o quieres procesarlo completo.
    # Si quieres replicar el comportamiento del log anterior que "terminó" el video, déjalo en None.
    MAX_FRAMES_TO_PROCESS = None 

    # 1. Crear una instancia del ObjectTracker
    tracker = ObjectTracker(MODEL_PATH, ZONE_IN_POLYGONS, ZONE_OUT_POLYGONS)

    # 2. Ejecutar el proceso de seguimiento
    tracker.run(
        video_path=VIDEO_INPUT_PATH, 
        max_frames=MAX_FRAMES_TO_PROCESS, 
        output_video_path=VIDEO_OUTPUT_PATH
    )

    # 3. Imprimir el informe final
    tracker.get_report()