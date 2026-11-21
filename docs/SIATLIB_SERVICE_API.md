# siatlib como servicio — Contrato de la API

> Estado: **borrador para validar** con SIATv2 y la dirección.
> Versión del contrato: `v1`.

siatlib se puede usar de dos formas, con el mismo código adentro:

| Modo | Cómo se usa | Para qué |
|---|---|---|
| **Librería** | `from siatlib import TrafficAnalyzer` | Scripts, notebooks, experimentos. Llamada síncrona. |
| **Servicio** | Contenedor Docker con API HTTP (`siat-service`) | Que otra aplicación (p. ej. el backend de SIATv2) encole videos y consulte su estado sin procesar nada ella misma. |

Este documento define el contrato del **modo servicio**.

---

## 1. Conceptos

- **Trabajo (job)**: un pedido de procesamiento de un video con sus zonas.
- **Cola**: los trabajos se procesan **de a uno, en orden de llegada** (FIFO). Un único worker usa la GPU.
- **Persistencia**: los trabajos se guardan en SQLite dentro del volumen `/data`. Si el contenedor se reinicia, los trabajos pendientes se conservan y los que estaban en proceso vuelven a la cola.

### Volúmenes

| Ruta en el contenedor | Contenido | Quién escribe |
|---|---|---|
| `/data/input/` | Videos a procesar | El cliente (p. ej. el backend de SIATv2) |
| `/data/output/{job_id}/` | `result.json` y `video.mp4` | El servicio |
| `/data/siat-service.db` | Base SQLite de trabajos | El servicio |
| `/models/` | Pesos de modelos YOLO (`.pt`) | Quien despliega (solo lectura) |

El video **no se sube por HTTP** en esta versión: el cliente lo copia al volumen compartido y en el pedido indica su ruta relativa a `/data/input/`.

---

## 2. Estados de un trabajo

```
             ┌──────────── DELETE /jobs/{id} ───────────┐
             │                                          ▼
 POST /jobs ─► PENDING ──► PROCESSING ──┬──► DONE     CANCELLED
                  ▲            │        └──► FAILED
                  └────────────┘
          (reinicio del servicio durante el proceso)
```

| Estado | Significado | ¿Final? |
|---|---|---|
| `PENDING` | En cola, esperando su turno | No |
| `PROCESSING` | El worker lo está procesando; `progress` va de 0 a 100 | No |
| `DONE` | Terminó bien; hay resultados disponibles | Sí |
| `FAILED` | Falló; el motivo está en `error` | Sí |
| `CANCELLED` | Se canceló antes de empezar a procesarse | Sí |

Solo se puede cancelar un trabajo en `PENDING`. Cancelar uno en `PROCESSING` devuelve `409` (se evaluará en una versión futura).

---

## 3. Endpoints

| Método | Ruta | Qué hace | Respuestas |
|---|---|---|---|
| `POST` | `/jobs` | Encola un trabajo | `202` Job · `422` pedido inválido |
| `GET` | `/jobs` | Lista trabajos (filtro opcional `?status=PENDING`, `?limit=50`) | `200` lista de Job |
| `GET` | `/jobs/{id}` | Estado y progreso | `200` Job · `404` |
| `GET` | `/jobs/{id}/result` | JSON de resultados | `200` · `404` · `409` si no está `DONE` |
| `GET` | `/jobs/{id}/video` | Video renderizado (`video/mp4`) | `200` · `404` · `409` si no está `DONE` |
| `DELETE` | `/jobs/{id}` | Cancela un trabajo pendiente | `200` Job · `404` · `409` si no está `PENDING` |
| `GET` | `/health` | Si el servicio está vivo, el dispositivo y el estado de la cola | `200` |

La documentación interactiva (OpenAPI/Swagger) queda en `/docs`.

Errores: siempre con el formato `{"detail": "<mensaje>"}`.

---

## 4. Entrada: `JobRequest`

```json
{
  "video": "rotonda_1/video.mp4",
  "zones": [
    {"name": "Entrada Sur",  "type": "entry",    "polygon": [[544, 913], [617, 1005], [824, 939], [705, 839]]},
    {"name": "Entrada Este", "type": "entry",    "polygon": [[1398, 620], [1438, 559], [1583, 629], [1582, 719]]},
    {"name": "Salida Sur",   "type": "exit",     "polygon": [[516, 890], [433, 837], [497, 735], [625, 773]]},
    {"name": "Salida Este",  "type": "exit",     "polygon": [[1373, 692], [1358, 781], [1551, 820], [1538, 721]]},
    {"name": "Cartel",       "type": "excluded", "polygon": [[10, 10], [200, 10], [200, 80], [10, 80]]}
  ],
  "model": "model-v5.pt",
  "options": {
    "max_frames": null,
    "imgsz": null,
    "render_video": true
  },
  "metadata": {"task_id": 123}
}
```

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `video` | string | Sí | Ruta del video **relativa a `/data/input/`**. No puede salir de ese directorio. |
| `zones` | lista | Sí | Al menos una zona `entry` y una `exit`. |
| `zones[].name` | string | Sí | Nombre visible de la zona (aparece en los resultados). |
| `zones[].type` | `"entry"` \| `"exit"` \| `"excluded"` | Sí | `excluded` se pinta de negro antes de la inferencia. |
| `zones[].polygon` | lista de `[x, y]` | Sí | Al menos 3 vértices, en píxeles del video original. |
| `model` | string | No | Archivo dentro de `/models/`. Por defecto, el configurado en `SIAT_DEFAULT_MODEL`. |
| `options.max_frames` | int | No | Procesar solo los primeros N frames (útil para pruebas). |
| `options.imgsz` | int | No | Resolución de inferencia. Por defecto, la resolución nativa del video. |
| `options.render_video` | bool | No | Generar el video anotado (por defecto `true`). |
| `metadata` | objeto | No | Datos libres del cliente (p. ej. su `task_id`). Se devuelven tal cual en el Job y en el resultado. |

---

## 5. Salida

### `Job` (respuesta de `POST /jobs`, `GET /jobs/{id}`, `DELETE /jobs/{id}`)

```json
{
  "id": "3f6c2a9e8b1d4c0f9a7e5d3b1c2a4e6f",
  "status": "PROCESSING",
  "progress": 42.5,
  "error": null,
  "created_at": "2026-11-12T20:15:03.120Z",
  "started_at": "2026-11-12T20:15:04.002Z",
  "finished_at": null,
  "request": { "...": "el JobRequest tal como se recibió" },
  "metadata": {"task_id": 123}
}
```

### Resultado (`GET /jobs/{id}/result`, también en `/data/output/{id}/result.json`)

```json
{
  "job_id": "3f6c2a9e8b1d4c0f9a7e5d3b1c2a4e6f",
  "metadata": {"task_id": 123},
  "video": "3f6c2a9e8b1d4c0f9a7e5d3b1c2a4e6f/video.mp4",
  "transition_counts": {
    "Entrada Sur": {"Salida Este": {"Transporte liviano": 2, "Transporte mediano": 12, "Transporte pesado": 1}}
  },
  "transition_determined_object": {"17": {"...": "..."}},
  "transition_undetermined_object": {"42": {"...": "..."}},
  "trajectories": {
    "17": {
      "track_id": 17,
      "vehicle_class": "Transporte mediano",
      "confidence": 0.91,
      "first_entry_zone": "Entrada Sur",
      "first_exit_zone": "Salida Este",
      "history": [{"act_frame": 1, "class_id": 2, "confidence": 0.9, "box": [0, 0, 10, 10], "track_history_point": [5, 5]}]
    }
  },
  "total_frames_processed": 1500
}
```

- Los campos de análisis son los mismos que devuelve `AnalysisResult.to_dict()` en el modo librería y los mismos que hoy escribe el backend en `transition_counts.json`, `transition_determined_object.json`, etc.
- `video` es la ruta del video renderizado **relativa a `/data/output/`** (o `null` si `render_video` era `false`).
- **Compatibilidad hacia adelante**: se pueden agregar campos nuevos (p. ej. `camera_motion` cuando se incorpore la compensación de movimiento de cámara). Los clientes deben ignorar los campos que no conozcan.

---

## 6. Flujo típico desde SIATv2

```
backend SIATv2                               siat-inference
──────────────                               ──────────────
1. copia el video a /data/input/tarea_123.mp4
2. POST /jobs {video: "tarea_123.mp4", zones, metadata:{task_id:123}}
                                       ──►   202 {id, status: PENDING}
3. guarda job_id en su tarea
4. cada N segundos: GET /jobs/{id}     ──►   {status: PROCESSING, progress: 37.0}
5. cuando status == DONE:
   GET /jobs/{id}/result               ──►   JSON de resultados
   GET /jobs/{id}/video                ──►   video.mp4 (o lo lee del volumen)
6. sube el video a MinIO / guarda las métricas como hace hoy
```

Esto reemplaza al `backend-worker` actual (`process_command.py`), que hoy busca tareas `READY_TO_PROCESS` en la base del backend y lanza `process.py` como subproceso.

---

## 7. Configuración (variables de entorno)

| Variable | Default | Descripción |
|---|---|---|
| `SIAT_DATA_DIR` | `/data` | Raíz de `input/`, `output/` y la base SQLite |
| `SIAT_MODELS_DIR` | `/models` | Directorio de modelos |
| `SIAT_DEFAULT_MODEL` | `model.pt` | Modelo usado si el pedido no indica uno |
| `SIAT_DEVICE` | `auto` | `auto`, `cpu`, `cuda`, `0`, … |
| `SIAT_TRACKER_CONFIG` | (incluido) | YAML de BoT-SORT; por defecto, el que trae la librería |
| `SIAT_HOST` / `SIAT_PORT` | `0.0.0.0` / `8000` | Dónde escucha la API |

---

## 8. Fuera de alcance en `v1`

Subida de videos por HTTP, webhooks/callbacks al terminar, varios workers o GPUs, cancelación de trabajos en curso, autenticación (se asume red interna de docker compose) y monitoreo en tiempo real.

## 9. Preguntas abiertas para SIATv2

1. ¿Les sirve compartir un volumen para los videos, o prefieren mandarlos por HTTP o por una URL de MinIO?
2. ¿Polling cada N segundos les alcanza, o necesitan un webhook al terminar?
3. ¿El formato de resultados (idéntico al de los JSON actuales) les evita cambios en su lado?
