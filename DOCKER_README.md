# Dockerización de Traffic Analysis

## Arquitectura

El sistema está compuesto por 5 contenedores:

1. **PostgreSQL** - Base de datos principal
2. **MinIO** - Almacenamiento de objetos (videos y resultados)
3. **Backend API** - Servidor FastAPI que maneja todas las consultas HTTP
4. **Backend Worker** - Procesa tareas de inferencia de forma asíncrona
5. **Frontend** - Aplicación SvelteKit con SSR

## Requisitos Previos

- Docker Engine 20.10+
- Docker Compose 2.0+
- (Opcional) NVIDIA Container Toolkit para soporte GPU

### Configuración GPU (Opcional)

Si tienes una GPU NVIDIA y quieres usarla para inferencia:

```bash
# Instalar NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

Si **no tienes GPU**, comenta o elimina la sección `deploy` del servicio `backend-worker` en `docker-compose.yaml`:

```yaml
# Comentar o eliminar estas líneas:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]
```

## Inicio Rápido

### 1. Clonar y configurar

```bash
cd traffic_analysis
cp .env.example .env
# Edita .env y cambia SECRET_KEY por un valor seguro
```

### 2. Asegurar que el modelo YOLO esté presente

Verifica que existe el archivo del modelo:
```bash
ls -lh backend/app/modelo/model-v5.pt
```

### 3. Levantar todos los servicios

```bash
docker compose up -d
```

Esto iniciará:
- PostgreSQL en puerto interno (no expuesto)
- MinIO en puertos 9000 (API) y 9001 (consola web)
- Backend API (accesible solo desde frontend)
- Backend Worker (polling cada 30s)
- Frontend en puerto 3000

### 4. Verificar estado

```bash
docker compose ps
docker compose logs -f backend-api
docker compose logs -f backend-worker
```

### 5. Acceder a la aplicación

- **Frontend**: http://localhost:3000
- **MinIO Console**: http://localhost:9001 (user: minioadmin, pass: minioadmin)

**Nota**: El backend API (puerto 8000) NO está expuesto públicamente. Solo es accesible desde el contenedor frontend.

## Flujo de Trabajo

### Procesamiento de Videos

1. Usuario sube video → Se guarda en MinIO
2. Usuario configura polígonos (roads) → Task cambia a `READY_TO_PROCESS`
3. **Backend Worker** detecta automáticamente la tarea (polling cada 30s)
4. Worker descarga video, ejecuta inferencia YOLO, sube resultados
5. Task cambia a `PROCESSED`
6. Usuario puede ver resultados en el frontend

### Backend Worker

El worker ejecuta un loop infinito:
```bash
while true; do
  python -m app.command.process_command run_process
  sleep 30
done
```

Revisa logs:
```bash
docker compose logs -f backend-worker
```

## Comandos Útiles

### Ver logs
```bash
# Todos los servicios
docker compose logs -f

# Solo un servicio
docker compose logs -f backend-worker
docker compose logs -f frontend
```

### Reiniciar servicios
```bash
# Reiniciar todo
docker compose restart

# Reiniciar solo worker
docker compose restart backend-worker
```

### Rebuild después de cambios en código
```bash
# Rebuild y reiniciar
docker compose up -d --build

# Rebuild solo backend
docker compose up -d --build backend-api backend-worker
```

### Ejecutar comandos en contenedores
```bash
# Shell en backend
docker compose exec backend-api bash

# Ejecutar migraciones manualmente
docker compose exec backend-api alembic upgrade head

# Ejecutar seeds
docker compose exec backend-api python -m app.seeds
```

### Limpiar todo
```bash
# Detener y eliminar contenedores
docker compose down

# Eliminar también volúmenes (CUIDADO: borra BD y MinIO)
docker compose down -v
```

## Estructura de Red

Todos los contenedores están en la red `traffic_network`:

- `db` → PostgreSQL (puerto 5432 interno)
- `minio` → MinIO (puertos 9000 y 9001)
- `backend-api` → FastAPI (puerto 8000 interno)
- `backend-worker` → Worker de inferencia (sin puertos)
- `frontend` → SvelteKit (puerto 3000 → **expuesto**)

**Comunicación**:
- Frontend → Backend API: `http://backend-api:8000`
- Frontend → MinIO: `http://minio:9000`
- Backend → PostgreSQL: `postgresql://admin:admin123@db:5432/traffic_analysis`
- Backend → MinIO: `http://minio:9000`

## Troubleshooting

### Error: "No module named 'app'"
El Dockerfile ha sido actualizado. Rebuild:
```bash
docker compose up -d --build backend-api backend-worker
```

### Worker no procesa tareas
Verifica logs y que la tarea esté en estado `READY_TO_PROCESS`:
```bash
docker compose logs backend-worker
docker compose exec backend-api python -c "from app.db import SessionLocal; from app.models import Task; db = SessionLocal(); print([t.status for t in db.query(Task).all()])"
```

### GPU no se detecta
Verifica NVIDIA runtime:
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Frontend no se conecta al backend
Verifica variables de entorno:
```bash
docker compose exec frontend env | grep BACKEND_URL
# Debe mostrar: BACKEND_URL=http://backend-api:8000
```

### MinIO no está accesible
Espera a que el healthcheck pase:
```bash
docker compose ps minio
# Debe mostrar: healthy
```

## Variables de Entorno

Principales variables configurables en `docker-compose.yaml`:

**Backend**:
- `DB_*`: Configuración de PostgreSQL
- `MINIO_*`: Configuración de MinIO
- `SECRET_KEY`: Clave secreta para JWT (cambiar en producción)
- `CORS_ALLOWED_ORIGINS`: Orígenes permitidos para CORS

**Frontend**:
- `BACKEND_URL`: URL interna del backend API
- `MINIO_URL`: URL interna de MinIO
- `ORIGIN`: URL pública del frontend

## Producción

Para deployment en producción:

1. **Cambiar `SECRET_KEY`** en `.env` por un valor aleatorio seguro
2. **Configurar CORS** con el dominio real
3. **Usar nginx** como reverse proxy delante del frontend
4. **Configurar SSL/TLS** (Let's Encrypt)
5. **Cambiar credenciales** de PostgreSQL y MinIO
6. **Configurar backups** de volúmenes
7. **Monitorear logs** con herramientas como Loki/Grafana

## Desarrollo Local

Para desarrollo sin Docker:

```bash
# Backend
cd backend/app
python -m venv venv
source venv/bin/activate
pip install -r requirements_test.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Asegúrate de tener PostgreSQL y MinIO corriendo (puedes usar solo esos servicios de Docker):
```bash
docker compose up -d db minio
```
