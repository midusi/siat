# Guía de Entrenamiento de Modelos YOLO (`train_guide.md`)

Esta guía explica en detalle cómo configurar, ejecutar y monitorear el entrenamiento de modelos YOLO (YOLO11) dentro de `siatlib`, contemplando dos escenarios de infraestructura:
1. **Entrenamiento Local:** Recursos limitados (GPU de gama media/baja como GTX 1650 de 4 GB VRAM o CPU).
2. **Entrenamiento Remoto vía SSH:** Servidor o clúster de alto rendimiento (GPUs como RTX 3090/4090, A100, T4, multi-GPU).

---

## 1. Estructura de Archivos de Entrenamiento

Los scripts de entrenamiento se encuentran organizados en:

```text
siatlib/src/experiments/
├── dataset/
│   └── process/test1/data.yaml        # Configuración del dataset (rutas y clases)
├── scripts/
│   └── train/
│       ├── config.py                  # Diccionario central de hiperparámetros y configuración
│       ├── train.py                   # Script de ejecución del entrenamiento
│       └── yolo11m.pt                 # Pesos base pre-entrenados
├── documentation/
│   ├── train_guide.md                 # Esta guía
│   └── transfer_samples_guide.md      # Guía de preparación y balanceo del dataset
└── pyproject.toml                     # Dependencias del entorno
```

---

## 2. Preparación del Entorno

Para evitar conflictos de compatibilidad de CUDA y Python, se utiliza `uv` y **Python 3.12**.

```bash
# 1. Posicionarse en la carpeta de la librería
cd siatlib

# 2. Crear entorno virtual con Python 3.12
uv venv .venv --python 3.12
source .venv/bin/activate

# 3. Instalar PyTorch con soporte CUDA 12.4
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# 4. Instalar Ultralytics y utilidades
uv pip install ultralytics ruff jupytext

# 5. Comprobar disponibilidad de GPU
python -c "import torch; print('CUDA disponible:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU')"
```

---

## 3. Escenario 1: Entrenamiento Local (GPU con VRAM Limitada)

En una máquina local con GPUs como la **NVIDIA GeForce GTX 1650 (4 GB VRAM)**, el cuello de botella principal es la memoria de video (VRAM). Si se solicita un tamaño de imagen muy grande o un batch alto, se producirá un error `torch.cuda.OutOfMemoryError`.

### Configuración Recomendada en `config.py`

Edita `siatlib/src/experiments/scripts/train/config.py`:

```python
FROM_SCRATCH = False  # Fine-tuning aprovecha pesos previos y converge más rápido

config = {
    # Trazabilidad
    "experiment_id": "SIATLIB-LOCAL-V1",
    "run_id": "traffic-local-y11s",
    "seed": 42,

    # Modelo y Dataset
    "from_scratch": FROM_SCRATCH,
    # Se recomienda modelo Nano (yolo11n.pt) o Small (yolo11s.pt) para 4GB VRAM
    "model_base": "yolo11s.pt",
    "data": "../../dataset/process/test1/data.yaml",

    # Hiperparámetros ajustados a recursos locales
    "epochs": 100,
    "imgsz": 640,       # 640px es seguro para 4GB. Si usas 1280px, usa batch=2
    "batch": 4,         # batch 4 o 2 (o -1 para AutoBatch de Ultralytics)
    "device": 0,        # 0 para GPU local

    "patience": 15,     # Early stopping si no mejora en 15 épocas
    "optimizer": "AdamW",
    "lr0": 0.001,

    # Data Augmentation
    "mosaic": True,
    "mixup": 0.2,

    "project": "runs",
    "output_figures_dir": "../../reports/figures",
    "output_result_dir": "../../reports/models"
}
```

### Ejecución Local

```bash
cd siatlib/src/experiments/scripts/train
python train.py
```

### Tips para Optimizar el Uso de GPU Local:
* **Batch Auto (`batch: -1`)**: Ultralytics evalúa automáticamente la memoria libre y ajusta el batch al máximo que soporte la GPU sin crashear.
* **Reducir resolución**: Pasar de `imgsz: 1280` a `imgsz: 640` reduce drásticamente el consumo de VRAM a una cuarta parte.
* **Cerrar navegadores u otras apps**: Aplicaciones aceleradas por hardware (navegadores, IDEs pesados) consumen entre 200MB y 600MB de VRAM.

---

## 4. Escenario 2: Entrenamiento Remoto vía SSH (Servidor de Alto Rendimiento)

Para entrenamientos con datasets grandes, resoluciones altas (1280px para objetos pequeños o tomas de dron) y modelos medianos/grandes (`yolo11m`, `yolo11l`, `yolo11x`), se recomienda transferir la carga a un servidor remoto con GPUs dedicadas (e.g., RTX 3090/4090 de 24 GB, A100 de 40/80 GB, o multi-GPU).

### Paso 4.1: Conexión y Gestión de Sesión Persistente (`tmux`)

Un error común es iniciar el entrenamiento en una sesión SSH directa; si se corta la conexión WiFi o la terminal, el proceso se interrumpe y se pierde el progreso. Usa siempre `tmux` o `screen`:

```bash
# 1. Conectarse al servidor remoto
ssh usuario@servidor-gpu.com -p 22

# 2. Crear una sesión persistente
tmux new -s entrenamiento_yolo
```

> **Comandos básicos de `tmux`:**
> * Desacoplarse de la sesión (sin matar el proceso): Presionar `Ctrl + B`, luego presionar `D`.
> * Volver a entrar a la sesión tras reconectar SSH: `tmux attach -t entrenamiento_yolo`.
> * Listar sesiones activas: `tmux ls`.

### Paso 4.2: Sincronización de Archivos (Local $\leftrightarrow$ Remoto)

Sincronizar el código y el dataset usando `rsync`:

```bash
# Desde la máquina local, subir dataset y scripts al servidor remoto:
rsync -avzP --exclude '.venv' --exclude '__pycache__' --exclude 'runs' \
  /home/lucas/repositorios/siat/siatlib/ usuario@servidor-gpu.com:/home/usuario/siat/siatlib/
```

### Paso 4.3: Configuración de Alto Rendimiento en `config.py`

En el servidor remoto, podemos aprovechar la capacidad de cómputo completa:

```python
FROM_SCRATCH = True  # O False según el experimento

config = {
    "experiment_id": "SIATLIB-REMOTE-V1",
    "run_id": "traffic-highres-y11m",
    "seed": 42,

    # Modelo más potente y resolución nativa para drones
    "from_scratch": FROM_SCRATCH,
    "model_base": "yolo11m.pt",
    "data": "../../dataset/process/test1/data.yaml",

    "epochs": 300,
    "imgsz": 1280,      # Alta resolución ideal para objetos pequeños
    "batch": 16,        # Batch mayor (16, 32 o 64 según VRAM disponible)
    "device": 0,        # O lista de GPUs para multi-GPU: "0,1" o [0, 1]

    "patience": 30,
    "optimizer": "SGD" if FROM_SCRATCH else "AdamW",
    "lr0": 0.01,

    "mosaic": True,
    "mixup": 0.5,
    "project": "runs",
    "output_figures_dir": "../../reports/figures",
    "output_result_dir": "../../reports/models"
}
```

### Paso 4.4: Ejecución y Monitoreo Remoto

```bash
# Dentro de la sesión de tmux en el servidor:
cd siatlib/src/experiments/scripts/train
python train.py
```

Para monitorear el consumo de GPU y temperatura en otra ventana de la terminal:
```bash
watch -n 1 nvidia-smi
```

### Paso 4.5: Descargar Resultados y Pesos al Entorno Local

Al finalizar el entrenamiento, los pesos óptimos (`best.pt`), métricas (`results.png`, `confusion_matrix.png`) y curvas PR se guardan en la carpeta `runs/`.

Desde la máquina local, descargar la carpeta de resultados:

```bash
# Descargar solo la carpeta del experimento completado:
rsync -avzP usuario@servidor-gpu.com:/home/usuario/siat/siatlib/src/experiments/scripts/train/runs/ /home/lucas/repositorios/siat/siatlib/src/experiments/scripts/train/runs/
```

---

## 5. Tabla Comparativa: Local vs. Remoto (SSH)

| Característica | Entrenamiento Local | Entrenamiento Remoto (SSH) |
| :--- | :--- | :--- |
| **Hardware Típico** | GTX 1650 / RTX 3050 (4 - 6 GB VRAM) | RTX 3090/4090 / A100 / T4 (16 - 80 GB VRAM) |
| **Modelo Sugerido** | `yolo11n.pt` o `yolo11s.pt` | `yolo11m.pt`, `yolo11l.pt` o `yolo11x.pt` |
| **Resolución (`imgsz`)** | 640 (o 1280 con batch=2) | 1280 o superior (detección fina de drones) |
| **Tamaño de Batch** | 2 a 4 | 16 a 64 |
| **Tiempo Estimado** | Lento / Moderado (horas a días) | Rápido (minutos a pocas horas) |
| **Gestor de Sesión** | Terminal estándar / IDE | Requiere `tmux` o `screen` |
| **Propósito Ideal** | Pruebas de código, pipeline y debugging | Entrenamiento final de modelos para producción |

---

## 6. Solución de Problemas Frecuentes

### 1. `ValueError: Invalid CUDA 'device=0' requested`
* **Causa**: Discrepancia entre la versión de CUDA con la que se compiló PyTorch y el driver de la GPU, o entorno con Python 3.14 sin soporte de ruedas CUDA.
* **Solución**: Asegurarse de usar Python 3.12 y reinstalar PyTorch con `uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124`.

### 2. `torch.cuda.OutOfMemoryError: CUDA out of memory`
* **Causa**: El modelo, las imágenes o el batch exceden la VRAM.
* **Solución**:
  1. Reducir `batch` en `config.py` a `2` o `1`.
  2. Reducir `imgsz` de `1280` a `640`.
  3. Cambiar a una variante más ligera (ej. de `yolo11m` a `yolo11s` o `yolo11n`).

### 3. La conexión SSH se desconectó y se detuvo el entrenamiento
* **Solución**: Iniciar siempre los entrenamientos dentro de `tmux`. Si se interrumpió, Ultralytics permite reanudar desde el último checkpoint pasando `resume=True` o cargando los pesos parciales:
  ```python
  model = YOLO('runs/nombre_experimento/weights/last.pt')
  model.train(resume=True)
  ```

