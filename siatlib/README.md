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