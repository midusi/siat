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

from ultralytics.utils.plotting import Annotator, colors

# --- CONFIGURACIÓN Y CONSTANTES (internas del script, no de línea de comandos) ---

# Paleta de colores para las zonas: [verde para entrada, rojo para salida]
ZONE_COLORS = sv.ColorPalette.from_hex(["#00FF00", "#FF0000"])

ZONE_IN_POLYGONS = []
ZONE_OUT_POLYGONS = []

# Longitud máxima del historial de seguimiento de un objeto
TRACK_HISTORY_LENGTH = 30 

# Mapeo de ID de clases a nombres de clases simplificadas
SIMPLIFIED_CLASS_DISPLAY_NAMES = {
    0: "light_transport", # Bicicleta
    1: "heavy_transport", # Colectivo
    2: "medium_transport", # Auto
    3: "heavy_transport", # Camión pesado
    4: "heavy_transport", # Camión liviano
    5: "light_transport" # Moto
}

class ZoneType(Enum):
    """Enumeración para definir los tipos de zonas."""
    IN = 0  # Zona de entrada
    OUT = 1 # Zona de salida

class ObjectDisplayer:
    """
    Clase para el seguimiento de objetos y análisis de zonas en videos.

    Gestiona la detección, el seguimiento, la clasificación basada en el historial
    y la interacción con zonas predefinidas en un feed de video.
    """

    def __init__(self, zone_in_polygons: list[np.ndarray], zone_out_polygons: list[np.ndarray]):
        """
        Inicializa el ObjectDisplayer.

        Args:
            zone_in_polygons (list[np.ndarray]): Lista de polígonos NumPy que definen las zonas de entrada.
            zone_out_polygons (list[np.ndarray]): Lista de polígonos NumPy que definen las zonas de salida.
        """
        
        self.frames_dict = dict()
        
        self.class_names = SIMPLIFIED_CLASS_DISPLAY_NAMES
        
        self.zone_in_polygons = zone_in_polygons
        self.zone_out_polygons = zone_out_polygons
        
        self.track_history: defaultdict[int, deque] = defaultdict(lambda: deque(maxlen=TRACK_HISTORY_LENGTH))
        
    def _load_data(self, output_dir: str):
        """
        Carga los datos de los archivos JSON y los procesa para obtener el diccionario de frames.
        Crea un diccionario donde cada clave sea el "act_frame" y su valor sea una lista de objetos con ese act_frame.
        También carga los datos de transiciones de objetos determinados y no determinados.
        """
        with open(f'{output_dir}/data_obj_history.json', 'r') as f:
            data_obj_history = json.load(f)
        with open(f'{output_dir}/transition_determined_object.json', 'r') as f:
            self.transition_determined_object = json.load(f)
        with open(f'{output_dir}/transition_undetermined_object.json', 'r') as f:
            self.transition_undetermined_object = json.load(f)
            
        for track_id, obj_list in data_obj_history.items():
            for obj in obj_list:
                act_frame = obj.get("act_frame")
                if act_frame is not None:
                    if act_frame not in self.frames_dict:
                        self.frames_dict[act_frame] = []
                    # Se agrega el objeto completo, y también el track_id
                    obj_with_id = obj.copy()
                    obj_with_id["track_id"] = track_id
                    self.frames_dict[act_frame].append(obj_with_id)
        
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
                
    def _draw_bbox_and_track(self, frame: np.ndarray, annotator: Annotator, act_frame: int, obj: dict):
        """
        Dibuja el bounding box, agergandole un tick o una cruz, dependiendo de si el objeto es determinado o no,
        y el historial de seguimiento de un objeto en el frame.

        Args:
            frame (np.ndarray): Frame actual.
            annotator (Annotator): Objeto Annotator de Ultralytics para dibujar.
            obj (dict): Objeto con la información del objeto.
        """
        box = obj["box"]
        track_id = obj["track_id"]
        class_name = self.class_names.get(obj["class_id"], "indeterminado")
        
        obj_is_determined = True if track_id in self.transition_determined_object else False
        if obj_is_determined:
            # Dibujar bounding box y etiqueta
            transition = self.transition_determined_object[track_id][0]
            annotator.box_label(box, label=f"ID: {track_id} - ({transition[0]} -> {transition[1]}) - {class_name}", color=(255, 255, 255), txt_color=(0, 0, 0))
            # self._draw_tick(frame, box)
            
        else:
            # Dibujar bounding box y etiqueta
            transition = self.transition_undetermined_object[track_id][0]
            # Obtener el primer y segundo elemento de la transición
            annotator.box_label(box, label=f"ID: {track_id} - ({transition[0]} -> {transition[1]}) - {class_name}", color=(255, 255, 255), txt_color=(0, 0, 0))
            # self._draw_cross(frame, box)
        

        # Almacenar punto central del bounding box para dibujar el trazado
        center_x, center_y = self._get_center_bb(box)
        self.track_history[track_id].append((center_x, center_y))

        # # Dibujar trazado del historial de seguimiento
        # points = np.array(self.track_history[track_id], dtype=np.int32).reshape((-1, 1, 2))
        # if len(points) > 1:
        #     color = (255, 255, 255)  # BGR para blanco
        #     cv2.polylines(frame, [points], isClosed=False, color=color, thickness=2)

    def process_frame(self, frame: np.ndarray, act_frame: int, objects_in_frame: dict) -> np.ndarray:
        """
        Procesa un solo frame del video para dibujar el historial de seguimiento de los objetos.

        Args:
            frame (np.ndarray): El frame actual del video.
            act_frame (int): El número del frame actual.
            objects_in_frame (list): Lista de objetos en el frame.

        Returns:
            np.ndarray: El frame anotado con bounding boxes, trazas y zonas.
        """
        # Dibujar las zonas de entrada y salida
        self._draw_zones_in_out(frame, 2)
            
        # Inicializar el anotador de Ultralytics
        annotator = Annotator(frame, line_width=1)

        # Dibujar bounding box, ruta y etiqueta de los objetos en el frame
        for obj in objects_in_frame:
            self._draw_bbox_and_track(frame, annotator, act_frame, obj)
        
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
        
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
            video_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (w, h))
            if not video_writer.isOpened():
                print(f"Advertencia: No se pudo abrir VideoWriter para {output_video_path}.")
                exit()
        except Exception as e:
            print(f"Error al inicializar VideoWriter: {e}.")
            exit()

        act_frame = 0 # Contador de frames leídos
        print(f"Procesando video: {video_path} (dimensiones: {w}x{h}, FPS: {fps})")
        print(f"Guardando video procesado en: {output_video_path}")

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
                
                # Procesar el frame (dibujar zonas, BBs, etc.)
                # Obtener el valor correspondiente al act_frame en frames_dict
                objects_in_frame = self.frames_dict.get(act_frame, [])
                processed_frame = self.process_frame(frame, act_frame, objects_in_frame)
                
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
    
    # Si no se proporcionó una ruta de salida, generarla por defecto
    if final_output_video_path is None:
        input_dir = os.path.dirname(args.input_video_path)
        if not input_dir:
            input_dir = "."
        
        input_filename_without_ext, input_ext = os.path.splitext(os.path.basename(args.input_video_path))
        
        output_dir = os.path.join(input_dir, input_filename_without_ext)
        os.makedirs(output_dir, exist_ok=True)
        
        output_filename = f"postprocessed{input_ext}"
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
    
    # 2. Crear una instancia del ObjectDisplayer
    displayer = ObjectDisplayer(ZONE_IN_POLYGONS, ZONE_OUT_POLYGONS)
    
    # 3. Cargar los datos
    displayer._load_data(output_dir)

    # 4. Ejecutar el proceso de display
    displayer.run(
        video_path=args.input_video_path, 
        max_frames=args.max_frames, 
        output_video_path=final_output_video_path,
        display_video=show_video_window
    )
        