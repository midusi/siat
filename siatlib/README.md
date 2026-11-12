# siatlib - Biblioteca de Análisis de Tráfico en Video

**siatlib** es una biblioteca ligera en Python que proporciona una API de alto nivel para procesar videos de cámaras de tráfico, detectar y rastrear vehículos, clasificarlos y generar métricas de trayectoria y matrices de transición. Está pensada como un MVP que puede importarse directamente en otros servicios o desplegarse mediante Docker.

---

## 📦 Instalación

### Desde el código (desarrollo)
```bash
# Crear un entorno virtual aislado (uv es recomendado)
uv venv .venv                # crea .venv
source .venv/bin/activate
uv sync                      # instala dependencias desde pyproject.toml
```


### Como servicio (Docker)
siatlib también se distribuye como un servicio HTTP con cola de inferencia, listo para sumar a un `docker compose`. Ver [Usar como servicio](#-usar-como-servicio-docker--api-http).

### Extra del servicio (sin Docker)
```bash
uv sync --extra service      # o: pip install "siatlib[service]"
```

---

## 🚀 Ejemplo rápido
```python
from siatlib import TrafficAnalyzer, ZoneDefinition, ZoneType

# Definir zonas de entrada y salida (coordenadas en píxeles)
entrada = ZoneDefinition(
    name="Entrada-Norte",
    zone_type=ZoneType.ENTRY,
    polygon=[(100, 200), (400, 200), (400, 500), (100, 500)],
)

salida = ZoneDefinition(
    name="Salida-Sur",
    zone_type=ZoneType.EXIT,
    polygon=[(800, 200), (1100, 200), (1100, 500), (800, 500)],
)

# Inicializar el analizador (descarga el modelo YOLO la primera vez)
analyzer = TrafficAnalyzer(
    device="cpu",               # o "cuda" si hay GPU disponible
    zones=[entrada, salida],
    model_path="models/yolov8n.pt",  # opcional, usa modelo por defecto
)

# Procesar un video
resultado = analyzer.process_video("/data/video_trafico.mp4")

# El objeto ``AnalysisResult`` contiene la información del análisis:
print("Frames procesados:", resultado.frame_count)
print("Número de objetos detectados:", len(resultado.tracks))
print("Matriz de transición O/D:")
print(resultado.transition_matrix)

# Guardar video anotado (opcional)
resultado.save_annotated_video("out/video_anotado.mp4")
```

---

## 🛠️ Resumen de la API
| Clase / Función | Descripción |
|-------------------|-------------|
| **`TrafficAnalyzer`** | Fachada principal que carga el modelo YOLO, ejecuta inferencia, rastrea con BoT‑SORT, aplica la lógica de zonas y devuelve un `AnalysisResult`. Método clave: `process_video(video_path: str) -> AnalysisResult`. |
| **`ZoneDefinition`** | Dataclass que representa un polígono y su tipo (`ENTRY`, `EXIT`, `EXCLUDED`). Se usa para indicar zonas de interés o exclusión. |
| **`ZoneType`** | Enum con los valores `ENTRY`, `EXIT` y `EXCLUDED`. |
| **`AnalysisResult`** | Contenedor con todas las salidas: tracks de vehículos, matriz de transición, valores de entropía, número total de frames y método `save_annotated_video`. |
| **`ObjectTracker`** (interno) | Implementación de BoT‑SORT; expuesto solo a través de `TrafficAnalyzer`. |
| **Funciones auxiliares** (`apply_exclusion_mask`, `draw_polygon`, `calculate_entropy`, …) | Utilidades internas que pueden importarse para crear pipelines personalizados. |

Para la especificación completa de cada atributo y método, revisa `docs/SIATLIB_GUIDE.md`.

---

## 🧪 Ejecutar la suite de pruebas
El proyecto incluye pruebas unitarias basadas en **pytest** bajo `siatlib/tests/`.
```bash
# Activar el entorno virtual si no está activo
source .venv/bin/activate

# Ejecutar todas las pruebas
pytest siatlib/tests/
```
Se espera que todas pasen en un entorno con Python 3.11+, `opencv-python` y `ffmpeg` instalados. Para CI ver la configuración en `.github/workflows/`.

---

## 🐳 Usar como servicio (Docker + API HTTP)

Además de `import siatlib`, la librería trae un **servicio de inferencia**: una API HTTP con una **cola de trabajos** persistente (SQLite) y **estados** (`PENDING → PROCESSING → DONE | FAILED`, más `CANCELLED`). Los trabajos se procesan de a uno, en orden de llegada. El contrato completo está en [`docs/SIATLIB_SERVICE_API.md`](../docs/SIATLIB_SERVICE_API.md).

### Levantarlo con Docker Compose
```bash
cd siatlib
mkdir -p models data/input
cp /ruta/a/model-v5.pt models/model.pt
docker compose -f docker-compose.example.yaml up --build
curl localhost:8000/health
```
Sin GPU, descomentá en `docker-compose.example.yaml` los `args` de la variante CPU y comentá el bloque `deploy`.

Para sumarlo a otro proyecto (p. ej. SIATv2) copiá el servicio `siat-inference` de `docker-compose.example.yaml` a su `docker-compose.yaml`; dentro de la red de compose queda accesible en `http://siat-inference:8000`.

### Encolar un video
El video se deja en el volumen compartido (`data/input/`) y se pide por su ruta relativa:
```bash
cp mi_video.mp4 data/input/
curl -X POST localhost:8000/jobs -H 'Content-Type: application/json' -d '{
  "video": "mi_video.mp4",
  "zones": [
    {"name": "Entrada Sur", "type": "entry", "polygon": [[544,913],[617,1005],[824,939],[705,839]]},
    {"name": "Salida Sur",  "type": "exit",  "polygon": [[516,890],[433,837],[497,735],[625,773]]}
  ],
  "metadata": {"task_id": 123}
}'
# -> {"id": "<job_id>", "status": "PENDING", ...}

curl localhost:8000/jobs/<job_id>          # estado y progreso (%)
curl localhost:8000/jobs/<job_id>/result   # JSON de resultados (cuando está DONE)
curl -o out.mp4 localhost:8000/jobs/<job_id>/video
```
Documentación interactiva (Swagger): `http://localhost:8000/docs`.

### Sin Docker
```bash
uv sync --extra service
uv run siat-service --data-dir ./data --models-dir ./models --port 8000
```

### Desde Python, sin HTTP
```python
from pathlib import Path
from siatlib.service import JobRequest, JobStore, ServiceSettings, Worker

settings = ServiceSettings(data_dir=Path("data"), models_dir=Path("models"))
settings.ensure_dirs()
store = JobStore(settings.db_path)
job = store.create(JobRequest.from_dict({"video": "mi_video.mp4", "zones": [...]}))
Worker(store, settings).run_once()      # o .start() para procesar en un hilo
print(store.get(job.id).status)          # JobStatus.DONE
```

### Configuración
| Variable | Default | Descripción |
|---|---|---|
| `SIAT_DATA_DIR` | `/data` | `input/`, `output/` y la base SQLite |
| `SIAT_MODELS_DIR` | `/models` | Pesos `.pt` |
| `SIAT_DEFAULT_MODEL` | `model.pt` | Modelo si el pedido no indica uno |
| `SIAT_DEVICE` | `auto` | `auto`, `cpu`, `cuda`, `0`, … |
| `SIAT_TRACKER_CONFIG` | incluido | YAML de BoT-SORT |
| `SIAT_HOST` / `SIAT_PORT` | `0.0.0.0` / `8000` | Dónde escucha la API |

---

## 🤝 Guía de integración
* **Como paquete Python** – Añade `siatlib` a tu `pyproject.toml` o `requirements.txt` e importa las clases directamente.
* **Con Docker** – Construye la imagen con el Dockerfile anterior y ejecútala como contenedor lateral (side‑car) o dentro de tu pipeline de CI/CD. Monta los videos mediante volúmenes o expón una API REST (consulta el CLI `siat-process` en la guía).
* **Versionado** – La biblioteca sigue Semantic Versioning. Pincha la versión (`siatlib==0.3.0`) para evitar rupturas inesperadas.
* **Colaboración** – Cuando necesites actualizar la biblioteca, sube los cambios a la rama `siatlib-dev`, abre un Pull Request, solicita revisión al equipo consumidor y, tras la aprobación, fusiona a `main`. El equipo receptor deberá actualizar su dependencia (tag o SHA) y validar su pipeline.

---

## 📖 Lecturas adicionales
* Referencia completa de la API y ejemplos avanzados: `docs/SIATLIB_GUIDE.md`.
* Guía de migración del backend (reemplazo de `subprocess.Popen`): `docs/SIATLIB_MIGRATION.md`.
* Directrices de contribución: `CONTRIBUTING.md` (si existe).

---

*© 2026 SIAT – Todos los derechos reservados.*
### Desde el código (desarrollo)
```bash
# Clonar el repositorio (si aún no lo tienes)
git clone https://github.com/tuorg/siat.git
cd SIAT/siat

# Crear un entorno virtual aislado (uv es recomendado)
uv venv .venv                # crea .venv
source .venv/bin/activate
uv sync                      # instala dependencias desde pyproject.toml
```

### Con pip (producción)
Si el paquete está publicado en un índice PyPI interno puedes instalarlo directamente:
```bash
pip install siatlib
```

### Docker (ver sección completa en `docs/SIATLIB_GUIDE.md`)
La biblioteca puede ejecutarse dentro de un contenedor Docker que incluya todas las dependencias nativas (FFmpeg, OpenCV, pesos YOLO, etc.). Un Dockerfile genérico:
```Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
RUN python -m venv .venv && . .venv/bin/activate && uv sync
ENV PATH="/app/.venv/bin:${PATH}"
CMD ["python", "-m", "siatlib"]
```
Para una imagen lista, consulta la sección *Docker* de la guía.

---

## 🚀 Ejemplo rápido
```python
from siatlib import TrafficAnalyzer, ZoneDefinition, ZoneType

# Definir zonas de entrada y salida (coordenadas en píxeles)
entrada = ZoneDefinition(
    name="Entrada-Norte",
    zone_type=ZoneType.ENTRY,
    polygon=[(100, 200), (400, 200), (400, 500), (100, 500)],
)

salida = ZoneDefinition(
    name="Salida-Sur",
    zone_type=ZoneType.EXIT,
    polygon=[(800, 200), (1100, 200), (1100, 500), (800, 500)],
)

# Inicializar el analizador (descarga el modelo YOLO la primera vez)
analyzer = TrafficAnalyzer(
    device="cpu",               # o "cuda" si hay GPU disponible
    zones=[entrada, salida],
    model_path="models/yolov8n.pt",  # opcional, usa modelo por defecto
)

# Procesar un video
resultado = analyzer.process_video("/data/video_trafico.mp4")

# El objeto ``AnalysisResult`` contiene la información del análisis:
print("Frames procesados:", resultado.frame_count)
print("Número de objetos detectados:", len(resultado.tracks))
print("Matriz de transición O/D:")
print(resultado.transition_matrix)

# Guardar video anotado (opcional)
resultado.save_annotated_video("out/video_anotado.mp4")
```

---

## 🛠️ Resumen de la API
| Clase / Función | Descripción |
|-------------------|-------------|
| **`TrafficAnalyzer`** | Fachada principal que carga el modelo YOLO, ejecuta inferencia, rastrea con BoT‑SORT, aplica la lógica de zonas y devuelve un `AnalysisResult`. Método clave: `process_video(video_path: str) -> AnalysisResult`. |
| **`ZoneDefinition`** | Dataclass que representa un polígono y su tipo (`ENTRY`, `EXIT`, `EXCLUDED`). Se usa para indicar zonas de interés o exclusión. |
| **`ZoneType`** | Enum con los valores `ENTRY`, `EXIT` y `EXCLUDED`. |
| **`AnalysisResult`** | Contenedor con todas las salidas: tracks de vehículos, matriz de transición, valores de entropía, número total de frames y método `save_annotated_video`. |
| **`ObjectTracker`** (interno) | Implementación de BoT‑SORT; expuesto solo a través de `TrafficAnalyzer`. |
| **Funciones auxiliares** (`apply_exclusion_mask`, `draw_polygon`, `calculate_entropy`, …) | Utilidades internas que pueden importarse para crear pipelines personalizados. |

Para la especificación completa de cada atributo y método, revisa `docs/SIATLIB_GUIDE.md`.

---

## 🧪 Ejecutar la suite de pruebas
El proyecto incluye pruebas unitarias basadas en **pytest** bajo `siatlib/tests/`.
```bash
# Activar el entorno virtual si no está activo
source .venv/bin/activate

# Ejecutar todas las pruebas
pytest siatlib/tests/
```
Se espera que todas pasen en un entorno con Python 3.11+, `opencv-python` y `ffmpeg` instalados. Para CI ver la configuración en `.github/workflows/`.

---

## 🤝 Guía de integración
* **Como paquete Python** – Añade `siatlib` a tu `pyproject.toml` o `requirements.txt` e importa las clases directamente.
* **Con Docker** – Construye la imagen con el Dockerfile anterior y ejecútala como contenedor lateral (side‑car) o dentro de tu pipeline de CI/CD. Monta los videos mediante volúmenes o expón una API REST (consulta el CLI `siat-process` en la guía).
* **Versionado** – La biblioteca sigue Semantic Versioning. Pincha la versión (`siatlib==0.3.0`) para evitar rupturas inesperadas.
* **Colaboración** – Cuando necesites actualizar la biblioteca, sube los cambios a la rama `siatlib-dev`, abre un Pull Request, solicita revisión al equipo consumidor y, tras la aprobación, fusiona a `main`. El equipo receptor deberá actualizar su dependencia (tag o SHA) y validar su pipeline.

---

## 📖 Lecturas adicionales
* Referencia completa de la API y ejemplos avanzados: `docs/SIATLIB_GUIDE.md`.
* Guía de migración del backend (reemplazo de `subprocess.Popen`): `docs/SIATLIB_MIGRATION.md`.
* Directrices de contribución: `CONTRIBUTING.md` (si existe).

---

*© 2026 SIAT – Todos los derechos reservados.*