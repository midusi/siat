# Guía de Migración: `process_command.py` a `siatlib` (`SIATLIB_MIGRATION.md`)

Esta guía describe el procedimiento técnico para desacoplar el comando de procesamiento de tareas (`backend/app/command/process_command.py`), reemplazando la invocación por subproceso CLI (`subprocess.Popen(["python", "process.py", ...])`) por la API unificada de alto nivel `TrafficAnalyzer` provista por la librería `siatlib`.

---

## 1. Motivación y Beneficios de la Migración

| Aspecto | Antes (`subprocess.Popen`) | Después (`TrafficAnalyzer`) |
| :--- | :--- | :--- |
| **Carga del Modelo en Memoria** | El modelo YOLO y pesos se cargan desde cero en disco y se instancian en cada ejecución del subproceso (overhead de 5 a 15 s por video). | El modelo se puede mantener precargado en memoria/VRAM durante el ciclo de vida del worker o instanciar de forma limpia y directa en Python. |
| **Paso de Parámetros** | Serialización compleja en strings vía argumentos CLI (ej: `ast.literal_eval`, listas serializadas a string en `--polygons_in`). Fragilidad ante errores de parseo y quoting. | Parámetros tipados en memoria usando dataclasses nativas: `ZoneDefinition(name=..., polygon=..., zone_type=ZoneType.ENTRY)`. |
| **Monitoreo y Cancelación** | Monitoreo indirecto mediante polling con `process.poll()` y archivos temporales en disco `stdout_{id}.txt` y `stderr_{id}.txt`. Manejo de señales `SIGTERM`/`SIGKILL` propenso a procesos zombies. | Cancelación limpia y reporte de progreso en tiempo real cuadro a cuadro mediante `progress_callback(act_frame, total_frames, fps)`. |
| **Consumo de Resultados** | `process.py` volcaba archivos JSON al disco (`transition_counts.json`, `data_obj_history.json`, etc.) que luego `process_command.py` debía leer de disco mediante `open().read()`. | Retorno directo del objeto tipado en memoria `AnalysisResult` con atributos y diccionarios directos, reduciendo accesos a disco. |
| **Manejo de Errores** | Se obtenían códigos de salida y strings de stderr difíciles de rastrear en sentry/logs. | Excepciones estándar de Python con stacktrace completo y trazable. |

---

## 2. Comparativa de Código: Antes vs. Después

### 2.1 El Código Anterior (`backend/app/command/process_command.py`)

El flujo anterior preparaba cadenas de texto, creaba archivos temporales para capturar la salida de terminal y ejecutaba un proceso separado:

```python
# --- ANTES (Flujo con subproceso) ---
command = [
    "python",
    str(path_modelo / "process.py"),
    f"--input_video_path={input_video_path}",
    f"--model_path={model_file}",
    f"--tracker_path={path_modelo / 'botsort_custom.yaml'}",
    f"--polygons_in={polygons_in}",
    f"--polygons_out={polygons_out}",
    f"--excluded_zones={excluded_zones}",
    "--names_polygons_in", str(names_polygons_in),
    "--names_polygons_out", str(names_polygons_out),
    "--no_display",
]
if imgsz:
    command.append(f"--imgsz={imgsz}")

with open(stdout_path, "w+") as stdout_file, open(stderr_path, "w+") as stderr_file:
    process = subprocess.Popen(command, stdout=stdout_file, stderr=stderr_file, text=True)
    while process.poll() is None:
        uow.expire_all()
        task_check = uow.tasks.get(task_to_process.id)
        if not task_check:
            process.terminate()
            cancelled = True
            break
        time.sleep(2)

# Luego debía leer los JSON del disco para guardar en la BD:
with open(os.path.join(output_dir, "transition_counts.json"), 'r') as f:
    counts_content = f.read()
# ...
```

---

### 2.2 El Código Migrado (`TrafficAnalyzer`)

Con la nueva librería `siatlib`, el flujo se simplifica notablemente:

```python
# --- DESPUÉS (Flujo directo con siatlib) ---
import json
from siatlib import TrafficAnalyzer, ZoneDefinition, ZoneType

# 1. Mapear las zonas de la BD a ZoneDefinition
zones = []
for road in roads:
    if road.direction == "Entrada":
        z_type = ZoneType.ENTRY
    elif road.direction == "Salida":
        z_type = ZoneType.EXIT
    elif road.direction == "Excluida":
        z_type = ZoneType.EXCLUDED
    else:
        continue
    zones.append(
        ZoneDefinition(
            name=road.name,
            polygon=road.polygon,
            zone_type=z_type,
        )
    )

# 2. Instanciar el analizador
# Recomendado: configurar ruta de pesos desacoplada vía variables de entorno
model_file = os.getenv("YOLO_MODEL_PATH", str(path_modelo / "model-v5.pt"))
analyzer = TrafficAnalyzer(
    model_path=model_file,
    device=os.getenv("YOLO_DEVICE", "auto"),
)

# 3. Definir callback para progreso y cancelación cooperativa
# Buena práctica: Chequear cancelación por tiempo transcurrido (wall-clock) en vez de
# consultar la base de datos en cada frame o módulo fijo, evitando sobrecargar el pool de conexiones.
last_db_check = 0.0
CHECK_INTERVAL_SECONDS = 5.0

def on_progress(act_frame: int, total_frames: int, fps: float):
    global last_db_check
    now = time.time()
    
    # Comprobación de cancelación throttled cada 5 segundos
    if now - last_db_check > CHECK_INTERVAL_SECONDS:
        last_db_check = now
        uow.expire_all()
        if not uow.tasks.get(task_to_process.id):
            raise InterruptedError(f"Tarea {task_to_process.id} eliminada por el usuario.")

    porcentaje = int((act_frame / total_frames) * 100) if total_frames > 0 else 0
    typer.echo(f"Progreso tarea {task_to_process.id}: {porcentaje}% ({act_frame}/{total_frames}) a {fps:.1f} FPS")

# 4. Procesar el video directamente en Python
try:
    result = analyzer.process_video(
        video_path=input_video_path,
        zones=zones,
        output_video_path=local_processed_video_path,
        imgsz=int(imgsz) if imgsz else None,
        progress_callback=on_progress,
        display_video=False,
    )
except InterruptedError:
    typer.echo("Procesamiento cancelado.")
    return True

# 5. Obtener los resultados directamente en memoria (sin leer JSONs intermedios de disco)
counts_content = json.dumps(result.transition_counts, ensure_ascii=False)
undetermined_content = json.dumps(result.undetermined_transitions, ensure_ascii=False)
determined_content = json.dumps(result.determined_transitions, ensure_ascii=False)

# Guardar y subir data_obj_history serializado desde result.trajectories
with open(local_data_obj_history_path, 'w', encoding='utf-8') as f:
    json.dump(
        {str(k): v.history for k, v in result.trajectories.items()},
        f,
        ensure_ascii=False,
        indent=2,
    )
```

---

## 3. Pasos para Implementar la Migración en el Backend

1. **Instalación de la Dependencia:**
   Verificar que `siatlib` se encuentre instalada en el entorno del backend o en el Dockerfile:
   ```bash
   # En producción / contenedor: instalación estándar reproducible
   pip install --no-cache-dir /libs/siatlib

   # En desarrollo local: modo editable opcional con volúmenes montados
   # pip install -e /libs/siatlib
   ```
2. **Eliminar dependencias de rutas locales hacia `backend/app/modelo/process.py`:**
   El archivo `backend/app/modelo/process.py` y `run.py` ya no necesitan residir dentro de `backend/app/modelo/`.
3. **Actualizar `backend/app/command/process_command.py`:**
   * Importar `TrafficAnalyzer`, `ZoneDefinition`, `ZoneType` desde `siatlib`.
   * Reemplazar la preparación de argumentos CLI de `subprocess.Popen` por la lista `zones`.
   * Invocar `analyzer.process_video(...)`.
   * Utilizar `result.transition_counts`, `result.determined_transitions`, etc.
4. **Verificación:**
   Ejecutar las pruebas del worker o una tarea de prueba:
   ```bash
   python -m app.command.process_command
   ```

