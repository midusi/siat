# Guía Técnica y Documentación de API: `siatlib`

`siatlib` es una librería modular en Python orientada a la inferencia de visión por computadora para la detección, seguimiento, clasificación y análisis de flujo de tráfico vehicular en videos (tomas aéreas con drones o cámaras fijas de tráfico).

---

## 1. Arquitectura y Estructura Modular

La librería sigue una arquitectura modular desacoplada del backend web, base de datos y colas de tareas:

```text
siatlib/
├── pyproject.toml                     # Metadatos del paquete, dependencias y CLI entrypoint
├── src/
│   └── siatlib/
│       ├── __init__.py                # Exportación de la API pública
│       ├── analyzer.py                # Fachada de alto nivel (TrafficAnalyzer)
│       ├── models.py                  # Dataclasses y Enums del dominio
│       ├── process.py                 # Motor de procesamiento (ObjectTracker) y CLI (siat-process)
│       ├── botsort_custom.yaml        # Configuración por defecto del tracker BoT-SORT
│       ├── analytics/                 # Analítica de tráfico
│       │   ├── classifier.py          # Clasificación ponderada por entropía de Shannon
│       │   └── transitions.py         # Matrices Origen-Destino (O/D) y reglas de exclusión
│       ├── spatial/                   # Geometría y relaciones espaciales
│       │   └── geometry.py            # Cálculo de centroides y pertenencia a polígonos
│       ├── tracking/                  # Detección y hardware
│       │   └── detector.py            # Resolución dinámica de dispositivos PyTorch (CUDA/MPS/CPU)
│       └── visualization/             # Renderizado y pipeline de video
│           └── annotator.py           # Anotación de polígonos y aplicación de máscaras de exclusión
└── tests/                             # Batería de pruebas unitarias (pytest)
    ├── test_analyzer.py               # Pruebas de orquestación y delegación
    ├── test_classifier.py             # Pruebas de entropía y votación de clases
    ├── test_geometry.py               # Pruebas de geometría y pertenencia a zonas
    ├── test_models.py                 # Pruebas de estructuras de datos e indexación
    └── test_transitions.py             # Pruebas de transiciones O/D y exclusiones de borde
```

---

## 2. Requisitos de Infraestructura, Recursos y Metadatos

### 2.1 Hardware
* **GPU Dedicada (Recomendado):** NVIDIA con soporte CUDA (ej. GTX 1650 4GB para resoluciones estándar de 640px; RTX 3060/3090/A100 para resoluciones nativas de dron de 1280px) o Apple Silicon (soporte MPS).
* **CPU:** Funcional en cualquier CPU x86_64 o ARM64, aunque la velocidad de procesamiento rondará 1-5 FPS según el modelo YOLO seleccionado.
* **Memoria RAM:** Mínimo 8 GB (16 GB recomendado para procesar videos largos de alta resolución).

### 2.2 Archivos y Metadatos Necesarios
Para ejecutar un análisis, se requieren los siguientes elementos:

1. **Video de entrada:** Archivo legible por OpenCV (`.mp4`, `.avi`, `.mov`, `.mkv`).
2. **Pesos del modelo YOLO:** Archivo de pesos entrenado (`.pt`), por ejemplo `yolo11m.pt` o pesos específicos ajustados para tomas cenitales (ej. `y11m-lh-sinvan.pt`).
3. **Configuración del Tracker (Opcional):** Archivo YAML de configuración de BoT-SORT/ByteTrack. Si no se especifica, `siatlib` utiliza su configuración integrada `botsort_custom.yaml`.
4. **Definición de Zonas (Polígonos):**
   * Coordenadas de los vértices en píxeles absolutos `(x, y)` respecto a la resolución del video fuente.
   * Clasificación de zona: `ENTRY` (ingreso), `EXIT` (egreso) o `EXCLUDED` (zonas enmascaradas con negro donde no se detecta).
   * Nombres identificadores de zona (ej: `"Acceso Norte"`, `"Ruta 2 Salida"`).

---

## 3. Instalación y Preparación del Entorno

### 3.1 Instalación con `uv` (Recomendado)

```bash
# 1. Posicionarse en la carpeta siatlib
cd siatlib

# 2. Crear entorno virtual con Python 3.12 (o >= 3.10)
uv venv .venv --python 3.12
source .venv/bin/activate

# 3. Instalar PyTorch con soporte CUDA (ejemplo CUDA 12.4 para Linux)
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# 4. Instalar siatlib en modo editable junto a dependencias de desarrollo
uv pip install -e ".[dev]"
```

### 3.2 Instalación estándar con `pip`

```bash
cd siatlib
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install torch torchvision
pip install -e ".[dev]"
```

### 3.3 Instalación y Automatización mediante Docker

Para automatizar la instalación de `siatlib` dentro del contenedor del backend (worker o API) y garantizar que el entorno cuente con la librería disponible de forma reproducible y segura:

#### Opción A (Recomendada para Monorepo): Instalación Local en Imagen
Al construir la imagen del backend/worker desde la raíz del monorepo (configurando `context: .` en `docker-compose.yaml` o copiando la carpeta en el build context):

```dockerfile
# Dockerfile (backend / worker)
WORKDIR /app

# 1. Copiar la librería siatlib antes del código de la app para optimizar cache de capas
COPY siatlib/ /libs/siatlib/

# 2. Instalar como paquete estándar (no editable en producción)
RUN pip install --no-cache-dir /libs/siatlib/
```

> [!TIP]
> **Modo desarrollo con Hot-Reload:** Si deseas modificar `siatlib` localmente y ver los cambios reflejados en el contenedor sin reconstruir la imagen, monta el volumen en `docker-compose.override.yaml`:
> ```yaml
> volumes:
>   - ./siatlib:/libs/siatlib:ro
> ```
> Y en el contenedor de desarrollo ejecuta `pip install -e /libs/siatlib`. En imágenes de producción final nunca uses `-e`.

#### Opción B: Instalación Remota Inmutable desde Git
Si el backend y `siatlib` se gestionan en repositorios separados, **siempre pina un tag o commit SHA específico** para garantizar builds reproducibles y evitar que el caché de Docker oculte cambios en ramas mutables:

```dockerfile
# Requiere git instalado en el contenedor base
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Pinar a un tag de versión inmutable (ej: v0.1.0) o commit SHA:
RUN pip install --no-cache-dir "siatlib @ git+https://github.com/midusi/siat.git@v0.1.0#subdirectory=siatlib"
```


#### Opción C: Integración en Requerimientos (`requirements.txt`)
Para evitar vulnerabilidades de *Dependency Confusion* asociadas a `--extra-index-url`, instala PyTorch en un paso dedicado con `--index-url` y referencia la librería de forma unívoca:

```dockerfile
# 1. PyTorch desde índice oficial seguro
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 2. Requerimientos de la aplicación
RUN pip install -r requirements.txt
```

Donde `requirements.txt` incluye la ruta relativa al monorepo:
```text
/libs/siatlib
```

---

## 4. Referencia de la API

### 4.1 Fachada de Alto Nivel: `TrafficAnalyzer`

Ubicación: `siatlib.analyzer.TrafficAnalyzer`

Es la clase recomendada para integrar en aplicaciones, servicios en segundo plano y notebooks. Mantiene el modelo en memoria/VRAM y permite procesar múltiples videos secuencialmente.

#### `__init__(model_path, tracker_config=None, device="auto")`
* **`model_path`** (`Union[str, Path, YOLO]`): Ruta al archivo `.pt` o una instancia ya creada de `YOLO`.
* **`tracker_config`** (`Optional[Union[str, Path]]`): Ruta al archivo `.yaml` del tracker. Si es `None`, se utiliza el `botsort_custom.yaml` provisto por `siatlib`.
* **`device`** (`str`): Dispositivo de cómputo (`"auto"`, `"cuda"`, `"cpu"`, `"mps"`, `"0"`, `"1"`).

#### `process_video(...) -> AnalysisResult`
* **`video_path`** (`Union[str, Path]`): Ruta del video a analizar.
* **`zones`** (`List[ZoneDefinition]`): Lista de polígonos que delimitan entradas, salidas y exclusiones.
* **`output_video_path`** (`Optional[Union[str, Path]]`): Ruta donde guardar el video resultante anotado con cajas, identificadores y zonas. Si es `None`, no se genera video procesado en disco.
* **`max_frames`** (`Optional[int]`): Límite de cuadros a procesar (ideal para pruebas y validaciones rápidas).
* **`progress_callback`** (`Optional[Callable[[int, int, float], None]]`): Función que recibe `(frame_actual, total_frames, fps_actuales)`.
* **`imgsz`** (`Optional[int]`): Tamaño de imagen para inferencia de YOLO (múltiplo de 32, ej. 640 o 1280).
* **`display_video`** (`bool`): Si es `True`, abre una ventana OpenCV GUI durante el procesamiento (requiere entorno gráfico con display).

---

### 4.2 Modelos de Datos: `models.py`

#### `ZoneType` (Enum)
* `ZoneType.ENTRY` (alias compatible: `ZoneType.IN`): Zona de ingreso al área de análisis.
* `ZoneType.EXIT` (alias compatible: `ZoneType.OUT`): Zona de egreso del área de análisis.
* `ZoneType.EXCLUDED`: Zona descartada (se aplica máscara negra antes de la inferencia).

#### `ZoneDefinition` (Dataclass)
Define una zona poligonal en el plano del video:
```python
@dataclass
class ZoneDefinition:
    name: str                        # Identificador único de la zona
    polygon: List[Tuple[int, int]]  # Vértices [(x1, y1), (x2, y2), ...]
    zone_type: ZoneType             # ENTRY, EXIT o EXCLUDED
```

#### `VehicleTrajectory` (Dataclass)
Contiene la trayectoria completa y datos consolidados de un vehículo:
```python
@dataclass
class VehicleTrajectory:
    track_id: int
    vehicle_class: str              # Clase consolidada por entropía/votación mayoritaria
    confidence: float               # Nivel de confianza de la última detección
    first_entry_zone: Optional[str] # Nombre de la zona de ingreso registrada
    first_exit_zone: Optional[str]  # Nombre de la zona de egreso registrada
    history: List[Dict[str, Any]]   # Cuadro a cuadro: frame, box, clase, confianza, centro
```

#### `AnalysisResult` (Dataclass)
Resultado final retornado por `process_video` o `tracker.run()`:
* **`transition_counts`**: Matriz de transiciones con conteos agrupados por `[origen][destino][clase]`.
* **`determined_transitions`**: Vehículos con origen y destino identificados.
* **`undetermined_transitions`**: Vehículos con origen o destino no identificados.
* **`trajectories`**: Diccionario `Dict[int, VehicleTrajectory]`.
* **`total_frames_processed`**: Entero con el número total de frames procesados.
* **`output_video_path`**: Ruta al video renderizado (si se generó).
* **Compatibilidad de acceso:** Admite acceso como diccionario: `result["total_frames"]`, `result["transition_counts"]` y conversión completa mediante `result.to_dict()`.

---

### 4.3 Submódulos Internos

#### `analytics`
* `calculate_entropy(track_data: List[Dict]) -> Tuple[Counter, float]`:
  Calcula la entropía de Shannon ($-\sum p_i \log_2 p_i$) para evaluar la consistencia de las predicciones de clase a lo largo del tiempo para un mismo objeto.
* `classify_track(class_counts: Counter, class_names_mapping: Dict[int, str]) -> str`:
  Asigna la clase definitiva por votación de mayoría descartando fluctuaciones momentáneas.
* `compute_transitions(...) -> TransitionsResult`:
  Construye la matriz Origen-Destino y aplica las **reglas de exclusión de bordes**:
  * Vehículos presentes desde el frame 1 sin zona de entrada conocida son excluidos como artefactos de borde.
  * Vehículos detectados en el último frame sin salida conocida se descartan para evitar conteos incompletos.

#### `spatial`
* `get_center_bb(box: np.ndarray) -> Tuple[int, int]`: Retorna el centro geométrico `(x, y)` del bounding box `[x1, y1, x2, y2]`.
* `get_zone_index(box: np.ndarray, polygons: List[np.ndarray]) -> int`: Comprueba si el centro del bounding box interseca alguno de los polígonos usando `cv2.pointPolygonTest`.

#### `visualization`
* `apply_exclusion_mask(frame: np.ndarray, excluded_polygons: List[np.ndarray]) -> np.ndarray`: Rellena de negro (`color=(0, 0, 0)`) las zonas excluidas para que YOLO no gaste cómputo ni genere falsos positivos.
* `draw_polygon(annotated_frame, polygon, name_polygon, zone_type, thickness)`: Dibuja las líneas delimitadoras y etiquetas de entrada (verde) y salida (rojo).

---

## 5. Ejemplos de Uso

### 5.1 Ejemplo en Python con `TrafficAnalyzer`

```python
from siatlib import TrafficAnalyzer, ZoneDefinition, ZoneType

# 1. Definir zonas de interés en coordenadas (x, y) de la resolución del video
zones = [
    ZoneDefinition(
        name="Entrada Norte",
        polygon=[(800, 200), (1100, 200), (1100, 350), (800, 350)],
        zone_type=ZoneType.ENTRY,
    ),
    ZoneDefinition(
        name="Salida Sur",
        polygon=[(850, 800), (1150, 800), (1150, 980), (850, 980)],
        zone_type=ZoneType.EXIT,
    ),
    ZoneDefinition(
        name="Zona Excluida Obra",
        polygon=[(100, 100), (400, 100), (400, 400), (100, 400)],
        zone_type=ZoneType.EXCLUDED,
    ),
]

# 2. Instanciar el analizador cargando el modelo YOLO
# Recomendado: resolver la ruta de pesos mediante Path o variables de entorno
model_file = Path(os.getenv("YOLO_MODEL_PATH", "siatlib/y11m-lh-sinvan.pt")).resolve()
analyzer = TrafficAnalyzer(
    model_path=model_file,
    device="cuda",  # o "cpu"
)

# 3. Definir un callback opcional de progreso
def on_progress(act_frame: int, total_frames: int, fps: float):
    porcentaje = (act_frame / total_frames) * 100 if total_frames > 0 else 0
    print(f"Frame {act_frame}/{total_frames} ({porcentaje:.1f}%) a {fps:.1f} FPS", end="\r")

# 4. Procesar video
result = analyzer.process_video(
    video_path="video_transito.mp4",
    zones=zones,
    output_video_path="resultado_renderizado.mp4",
    max_frames=300,  # Procesar primeros 300 cuadros
    progress_callback=on_progress,
)

# 5. Consultar métricas resultantes
print("\n--- Resultados del Análisis ---")
print("Total frames procesados:", result.total_frames_processed)
print("Matriz de Transiciones O/D:")
print(result.transition_counts)

# Acceder a una transición particular:
conteo_autos = result.transition_counts["Entrada Norte"]["Salida Sur"]["Transporte mediano"]
print(f"Vehículos medianos de Entrada Norte -> Salida Sur: {conteo_autos}")
```

---

### 5.2 Ejemplo usando el CLI `siat-process`

Una vez instalada la librería con `pip install -e .`, el comando de consola queda disponible en el PATH:

```bash
siat-process \
  -i "video_transito.mp4" \
  -m "y11m-lh-sinvan.pt" \
  -t "siatlib/src/siatlib/botsort_custom.yaml" \
  -pi "[[[800,200],[1100,200],[1100,350],[800,350]]]" \
  -po "[[[850,800],[1150,800],[1150,980],[850,980]]]" \
  -ni "['Entrada Norte']" \
  -no "['Salida Sur']" \
  -o "salida/video_anotado.mp4" \
  --no_display
```

Archivos generados en la carpeta destino:
* `video_anotado.mp4`: Video procesado con H.264 compatible con reproductores web.
* `transition_counts.json`: Matriz de conteos origen-destino por clase.
* `transition_determined_object.json`: Objetos con transiciones válidas registradas.
* `transition_undetermined_object.json`: Objetos sin completar el circuito.
* `data_obj_history.json`: Trazabilidad cuadro a cuadro de cada vehículo.

---

## 6. Estructura de Datos: Formatos de Entrada y Salida

### 6.1 Mapeo de Clases por Defecto
El modelo YOLO mapea las detecciones a las siguientes categorías consolidadas de tráfico:

| ID Original | Etiqueta Original | Categoría Consolidada |
| :--- | :--- | :--- |
| `0` | Bicicleta | `Transporte liviano` |
| `1` | Colectivo / Autobús | `Transporte pesado` |
| `2` | Auto / Camioneta | `Transporte mediano` |
| `3` | Camión pesado | `Transporte pesado` |
| `4` | Camión liviano | `Transporte pesado` |
| `5` | Moto | `Transporte liviano` |

---

### 6.2 Ejemplo de Salida: Matriz de Transiciones (`transition_counts`)

```json
{
  "Entrada Norte": {
    "Salida Sur": {
      "Transporte liviano": 3,
      "Transporte mediano": 15,
      "Transporte pesado": 2
    },
    "Salida Este": {
      "Transporte liviano": 0,
      "Transporte mediano": 4,
      "Transporte pesado": 1
    }
  }
}
```

---

### 6.3 Ejemplo de Salida: Trayectoria (`VehicleTrajectory`)

```json
{
  "track_id": 42,
  "vehicle_class": "Transporte mediano",
  "confidence": 0.92,
  "first_entry_zone": "Entrada Norte",
  "first_exit_zone": "Salida Sur",
  "history": [
    {
      "act_frame": 12,
      "class_id": 2,
      "confidence": 0.88,
      "box": [820.5, 210.0, 890.0, 290.5],
      "track_history_point": [855, 250]
    },
    {
      "act_frame": 13,
      "class_id": 2,
      "confidence": 0.92,
      "box": [822.0, 215.0, 892.0, 296.0],
      "track_history_point": [857, 255]
    }
  ]
}
```

---

## 7. Ejecución de la Batería de Pruebas Unitarias

La librería cuenta con pruebas unitarias implementadas con `pytest` que validan el correcto funcionamiento de cada submódulo sin necesidad de descargar videos reales ni disponer de GPUs (mediante mocks de `ultralytics.YOLO`):

### 7.1 Ejecutar todos los tests

```bash
# Desde la raíz del repositorio o dentro de siatlib/:
pytest siatlib/tests/
```

### 7.2 Ejecutar con detalle y cobertura

```bash
pytest siatlib/tests/ -v -s
```

### 7.3 Descripción de los Tests
* **`test_models.py`**: Comprueba la creación de `AnalysisResult`, la conversión bidireccional a diccionario (`to_dict()`) y el acceso por clave (`result["total_frames"]`).
* **`test_geometry.py`**: Verifica el cálculo del centro de bounding boxes y el chequeo geométrico de puntos interiores y exteriores en polígonos.
* **`test_classifier.py`**: Evalúa que la entropía de Shannon sea 0.0 para detecciones unívocas, 1.0 para mezclas binarias uniformes, y valida la regla de votación por mayoría.
* **`test_transitions.py`**: Comprueba que una trayectoria con entrada y salida válidas compute correctamente en la matriz de transiciones y valida la exclusión de artefactos en los bordes del video.
* **`test_analyzer.py`**: Comprueba la inicialización de `TrafficAnalyzer`, la asignación del dispositivo (`CPU`/`CUDA`), el uso del tracker YAML por defecto y la correcta delegación hacia `ObjectTracker.run()`.

