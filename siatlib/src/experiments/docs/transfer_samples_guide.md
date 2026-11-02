# Guía de Uso: `transfer_samples.py`

Guía completa para la utilización del script [`transfer_samples.py`](file:///home/usuario/repositorios/SIAT/siat/siatlib/src/experiments/scripts/utils/transfer_samples.py), diseñado para la selección, copia y migración controlada de imágenes y sus respectivas etiquetas YOLO (`.txt`) entre datasets anotados con Roboflow u organizados bajo la estructura estándar de YOLO (`train`, `valid`, `test`).

---

## 1. Estructura de Datasets Compatible

El script está optimizado para trabajar con la estructura habitual de datasets YOLO / Roboflow dentro de `experiments/dataset/`:

```text
experiments/dataset/
├── dataset_origen/
│   ├── train/
│   │   ├── images/   # ej: img_001.jpg, img_002.png
│   │   └── labels/   # ej: img_001.txt, img_002.txt
│   ├── valid/
│   │   ├── images/
│   │   └── labels/
│   └── test/
│       ├── images/
│       └── labels/
└── dataset_destino/
    ├── train/
    ├── valid/
    └── test/
```

> **Nota:** Al transferir una muestra, el script busca y traslada automáticamente tanto el archivo de imagen como su correspondiente archivo de etiquetas `.txt` con el mismo nombre base (*stem*), y crea las carpetas de destino si aún no existen.

---

## 2. Métodos de Ejecución

El script soporta dos formas de trabajo principales: **Modo Interactivo (REPL)** y **Línea de Comandos (CLI)**.

---

### Modo 1: Shell Interactivo (Recomendado para Selección Manual)

Permite seleccionar muestras una por una o en grupos, visualizar el estado actual y cambiar configuraciones sobre la marcha sin reiniciar el proceso.

#### Iniciar el modo interactivo

Desde la raíz del repositorio o dentro de `siatlib/src/experiments`:

```bash
# Iniciando con detección automática de datasets disponibles:
python3 siatlib/src/experiments/scripts/utils/transfer_samples.py

# O especificando dataset origen y destino de antemano:
python3 siatlib/src/experiments/scripts/utils/transfer_samples.py -s aerial_images -d siatlib-v1-a
```

Una vez iniciado, verás el encabezado de estado y el prompt interactivo:

```text
=================================================================
 DATASET SAMPLE TRANSFER TOOL 
=================================================================
 Source Dataset : .../experiments/dataset/aerial_images
 Dest Dataset   : .../experiments/dataset/siatlib-v1-a
 Action Mode    : COPY
 Target Split   : Auto (match source split)
 Overwrite      : False | Dry-run: False
-----------------------------------------------------------------
 Commands:
   :src <path/name>    Cambiar dataset origen
   :dst <path/name>    Cambiar dataset destino
   :split <name|auto>  Forzar split destino (train/valid/test/auto)
   :mode <copy|move>   Alternar entre 'copy' y 'move'
   :list [split]       Listar muestras disponibles en el origen
   :status             Ver configuración activa
   :help               Ver ayuda
   :quit o q           Salir
=================================================================

[COPY] aerial_images -> siatlib-v1-a >
```

#### Acciones en el Prompt Interactivo

1. **Transferir una muestra individual:**
   Introduce el nombre completo o solo el nombre sin extensión:
   ```text
   img_0.jpg
   # o simplemente:
   img_0
   ```
   *El script buscará en todos los splits (`train`, `valid`, `test`) del origen y copiará la imagen a `images/` y la etiqueta correspondiente a `labels/`.*

2. **Transferir un grupo de archivos en un único input:**
   Puedes ingresar múltiples nombres separados por comas o espacios:
   ```text
   # Separado por comas:
   img_1, img_2, img_3

   # O separado por espacios:
   img_1.jpg img_2.jpg img_3.jpg
   ```

3. **Uso de patrones y comodines (Wildcards):**
   ```text
   frame_000*
   *.jpg
   ```

4. **Comandos internos (inician con `:`):**
   * `:mode move` : Cambia la acción a mover (elimina del origen tras transferir).
   * `:mode copy` : Cambia la acción a copiar (mantiene el origen intacto).
   * `:split train` : Fuerza a que todas las muestras transferidas vayan a la carpeta `train` del destino (en lugar de respetar su split original).
   * `:split auto` : Restaura el comportamiento automático (ej. `valid` a `valid`, `train` a `train`).
   * `:src <nombre>` : Cambia el dataset de origen.
   * `:dst <nombre>` : Cambia el dataset de destino.
   * `:list` o `:list train` : Muestra una vista previa de las imágenes presentes en el origen.
   * `:status` : Imprime un resumen de la configuración actual.
   * `:quit` o `q` : Finaliza la sesión.

---

### Modo 2: Línea de Comandos (CLI / Automatización)

Ideal para scripts de automatización o transferencias directas sin entrar al menú interactivo:

```bash
python3 siatlib/src/experiments/scripts/utils/transfer_samples.py [OPCIONES]
```

#### Ejemplos de uso directo

* **Simulación previa sin modificar archivos (`--dry-run`):**
  ```bash
  python3 siatlib/src/experiments/scripts/utils/transfer_samples.py \
    --source aerial_images \
    --dest siatlib-v1-a \
    --files img_0 img_1 \
    --dry-run
  ```

* **Copiar un lote de archivos en un solo comando:**
  ```bash
  python3 siatlib/src/experiments/scripts/utils/transfer_samples.py \
    -s aerial_images \
    -d siatlib-v1-a \
    -f "img_0.jpg, img_1.jpg, img_2.jpg"
  ```

* **Mover archivos cambiando el split de destino a `train`:**
  ```bash
  python3 siatlib/src/experiments/scripts/utils/transfer_samples.py \
    -s aerial_images \
    -d siatlib-v1-a \
    --action move \
    --target-split train \
    -f img_10 img_11
  ```

* **Sobrescribir archivos si ya existen en el destino:**
  ```bash
  python3 siatlib/src/experiments/scripts/utils/transfer_samples.py \
    -s aerial_images \
    -d siatlib-v1-a \
    --overwrite \
    -f img_0
  ```

---

## 3. Referencia de Parámetros CLI

| Opción | Abreviación | Descripción | Valor por Defecto |
| :--- | :--- | :--- | :--- |
| `--source` | `-s` | Nombre o ruta absoluta/relativa del dataset de origen. | Primer dataset detectado |
| `--dest` | `-d` | Nombre o ruta absoluta/relativa del dataset de destino. | Segundo dataset detectado |
| `--files` | `-f` | Uno o más nombres de archivo, stems o cadenas separadas por coma. | None (entra a interactivo) |
| `--action` | `-a` | Acción a realizar: `copy` (copiar) o `move` (mover). | `copy` |
| `--target-split` | | Forzar split destino (`train`, `valid`, `test`). | `None` (mantiene split original) |
| `--source-split` | | Restringir la búsqueda a un split origen específico. | `None` (busca en todos) |
| `--dataset-dir` | | Carpeta base donde residen los datasets. | `experiments/dataset/` |
| `--images-dir` | | Nombre de la subcarpeta de imágenes. | `images` |
| `--labels-dir` | | Nombre de la subcarpeta de etiquetas. | `labels` |
| `--overwrite` | | Sobrescribir archivos destino existentes en caso de conflicto. | `False` |
| `--dry-run` | | Ejecutar simulación mostrando lo que se copiaría/movería. | `False` |
| `--interactive`| `-i` | Forzar la apertura del modo interactivo. | `False` |

---

## 4. Uso Programático como Módulo Python

Si necesitas integrar la lógica dentro de otro script de preprocesamiento, puedes importar directamente las clases:

```python
from pathlib import Path
from siatlib.src.experiments.scripts.utils.transfer_samples import (
    DatasetConfig,
    DatasetTransferManager
)

# 1. Configurar la operación
config = DatasetConfig(
    source_dataset=Path("experiments/dataset/aerial_images"),
    dest_dataset=Path("experiments/dataset/siatlib-v1-a"),
    action="copy",      # 'copy' o 'move'
    target_split=None,  # None conserva train->train, valid->valid, etc.
    overwrite=False,
    dry_run=False
)

# 2. Inicializar el administrador
manager = DatasetTransferManager(config)

# 3. Transferir una lista o cadena de archivos
resultados = manager.transfer_batch(["img_0.jpg", "img_1.jpg", "img_2.jpg"])

# 4. Revisar los resultados
for r in resultados:
    print(f"[{'OK' if r.success else 'FALLO'}] {r.message}")
```

---

## 5. Casos de Borde y Manejo de Errores

1. **Muestras sin archivo de etiquetas:**
   Si una imagen no tiene archivo `.txt` correspondiente en `labels/` (por ejemplo, imágenes negativas de fondo), el script transferirá la imagen y mostrará un mensaje de advertencia `(warning: no label file found)`.
2. **Archivos ya existentes:**
   Por defecto, el script protege los datos y rechaza sobrescribir si el archivo ya existe en el destino, reportándolo como error. Para autorizar el reemplazo, añade `--overwrite` o habilítalo en la configuración.
3. **Flujos de datos de Windows (`:Zone.Identifier`):**
   El buscador ignora automáticamente los metadatos de stream de Windows para evitar errores de búsqueda o corrupción del set de datos.
4. **Directorios inexistentes:**
   Si el dataset destino o las subcarpetas `images`/`labels` aún no existen, se crearán de forma automática con permisos estándar.
