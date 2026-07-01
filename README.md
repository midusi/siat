# Traffic Analysis - Sistema de Análisis de Tráfico

Este proyecto es una aplicación full-stack para análisis de tráfico vehicular usando visión por computadora, desarrollada con FastAPI (backend), SvelteKit (frontend), PostgreSQL, y MinIO para almacenamiento de objetos.

## Arquitectura

El sistema está completamente dockerizado y consiste en 5 servicios:

1. **PostgreSQL** - Base de datos principal (puerto interno 5432)
2. **MinIO** - Almacenamiento de objetos para videos y resultados (puertos 9000 y 9001)
3. **Backend API** - Servidor FastAPI que maneja todas las peticiones HTTP (puerto interno 8000)
4. **Backend Worker** - Procesa tareas de inferencia YOLO de forma asíncrona (polling cada 30s)
5. **Frontend** - Aplicación SvelteKit con SSR (puerto 3000)

Todos los servicios se comunican a través de la red interna `siat_network`.

## Inicio Rápido con Docker

### Prerrequisitos

- Docker Engine 20.10+
- Docker Compose 2.0+
- (Opcional) NVIDIA Container Toolkit para soporte GPU

### 1. Clonar y configurar variables de entorno

```bash
cd siat
cp .env.example .env
```

Edite el archivo `.env` y cambie `SECRET_KEY` por un valor aleatorio seguro.

### 2. Verificar que el modelo YOLO existe

```bash
ls -lh backend/app/modelo/model-v5.pt
```

Si no existe, coloque el archivo del modelo en esa ubicación.

### 3. Configurar soporte GPU (opcional)

Si **no tiene GPU NVIDIA**, comente o elimine la sección `deploy` del servicio `backend-worker` en `docker-compose.yaml`:

```yaml
# Comentar estas líneas si NO tiene GPU:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: all
    #           capabilities: [gpu]
```

Si **tiene GPU**, instale NVIDIA Container Toolkit:

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 4. Levantar todos los servicios

```bash
docker compose up -d
```

Esto iniciará automáticamente:
- PostgreSQL y MinIO
- Backend API (ejecuta migraciones automáticamente al iniciar)
- Backend Worker (comienza polling de tareas)
- Frontend

### 5. Verificar estado

```bash
docker compose ps
docker compose logs -f
```

### 6. Acceder a la aplicación

- **Frontend**: http://localhost:3000
- **MinIO Console**: http://localhost:9001 (usuario: `minioadmin`, contraseña: `minioadmin`)

**Nota**: El Backend API (puerto 8000) NO está expuesto públicamente por seguridad. Solo es accesible desde el contenedor del frontend a través de la red interna.

## Flujo de Trabajo

### Procesamiento de Videos

1. Usuario sube video → Se almacena en MinIO
2. Usuario configura polígonos (roads) → La tarea cambia a estado `READY_TO_PROCESS`
3. **Backend Worker** detecta automáticamente la tarea (polling cada 30 segundos)
4. Worker descarga el video, ejecuta inferencia YOLO, y sube los resultados a MinIO
5. La tarea cambia a estado `PROCESSED`
6. Usuario puede visualizar los resultados en el frontend

## Comandos Útiles

### Ver logs
```bash
# Todos los servicios
docker compose logs -f

# Solo un servicio específico
docker compose logs -f backend-worker
docker compose logs -f backend-api
docker compose logs -f frontend
```

### Reiniciar servicios
```bash
# Reiniciar todo
docker compose restart

# Reiniciar solo un servicio
docker compose restart backend-worker
```

### Rebuild después de cambios en código
```bash
# Rebuild y reiniciar todo
docker compose up -d --build

# Rebuild solo backend
docker compose up -d --build backend-api backend-worker
```

### Ejecutar comandos dentro de contenedores
```bash
# Shell en backend
docker compose exec backend-api bash

# Ejecutar migraciones manualmente
docker compose exec backend-api alembic upgrade head

# Ejecutar seeds
docker compose exec backend-api python -m app.seeds
```

### Detener y limpiar
```bash
# Detener contenedores
docker compose down

# Detener y eliminar volúmenes (⚠️ CUIDADO: elimina datos de BD y MinIO)
docker compose down -v
```

## Desarrollo Local (sin Docker)

Si prefiere desarrollo local sin Docker:

### Backend

```bash
cd backend/app
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements_test.txt

# Levantar solo PostgreSQL y MinIO con Docker
docker compose up -d db minio

# Ejecutar migraciones
alembic upgrade head

# (Opcional) Ejecutar seeds
python seeds.py

# Iniciar servidor de desarrollo
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Servidor disponible en: `http://localhost:5173`

## Configuración de Variables de Entorno

### Para Docker

Las variables principales se configuran en `docker-compose.yaml` y pueden sobrescribirse con un archivo `.env` en la raíz del proyecto.

Variables clave:
- `SECRET_KEY`: Clave secreta para JWT (cambiar en producción)
- `DB_*`: Configuración de PostgreSQL
- `MINIO_*`: Configuración de MinIO
- `CORS_ALLOWED_ORIGINS`: Orígenes permitidos para CORS

### Para desarrollo local

Copie `backend/.env.example` a `backend/.env` y ajuste los valores:

- **Seguridad y cookies**:
  - En desarrollo local: `AUTH_COOKIE_SECURE=false`, `AUTH_REFRESH_COOKIE_SECURE=false`, `AUTH_COOKIE_SAMESITE=Lax`
  - En producción con HTTPS: `*_SECURE=true`, `*_SAMESITE=None`, configurar `AUTH_COOKIE_DOMAIN`
- **CORS**: Configure `CORS_ALLOWED_ORIGINS` (separado por comas) con los orígenes del frontend

## Características del Sistema

### Autenticación y Autorización

- Sistema de login/refresh/logout con cookies httpOnly
- Roles: `ROLE_ADMIN`, `ROLE_OPERADOR`
- Rutas protegidas mediante `get_current_user` y `require_role`
- Rate limiting y lockout en `/auth/login`
- Bcrypt con costo configurable y rehash transparente
- Auditoría de eventos de seguridad

### Recuperación de Contraseña

- Tokens HMAC firmados con expiración
- Endpoints: `/auth/password/request` y `/auth/password/perform`
- Servicio de email con stub (por defecto) o SMTP configurable

### Observabilidad

- Métricas expuestas en `GET /observability/metrics` (solo admin):
  - `total_login_attempts`, `failed_login_attempts`, `successful_logins`, `active_users`

### Procesamiento de Videos

- Inferencia YOLO asíncrona mediante worker dedicado
- Polling automático cada 30 segundos
- Soporte opcional para aceleración GPU (NVIDIA)
- Almacenamiento escalable con MinIO

## Roles y Permisos

- **Admin**: Puede crear/editar/habilitar/inhabilitar usuarios, resetear contraseñas, y gestionar todas las tareas
- **Operador**: Puede gestionar tareas según permisos asignados

### Crear el usuario admin

El usuario admin se crea automáticamente:
- Al ejecutar seeds: `docker compose exec backend-api python -m app.seeds` (crea `admin:admin` si no existe)
- Al ejecutar tests E2E

## Tests

Para ejecutar tests de integración y E2E:

```bash
# Dentro del contenedor backend
docker compose exec backend-api python backend/scripts/run_functional_tests.py

# Con tests del frontend (opcional)
docker compose exec backend-api bash -c "RUN_FRONT_TESTS=1 python backend/scripts/run_functional_tests.py"
```

## Troubleshooting

### Error: "No module named 'app'"
El Dockerfile ha sido actualizado. Ejecute rebuild:
```bash
docker compose up -d --build backend-api backend-worker
```

### Worker no procesa tareas
Verifique los logs y que la tarea esté en estado `READY_TO_PROCESS`:
```bash
docker compose logs backend-worker
docker compose exec backend-api python -c "from app.db import SessionLocal; from app.models import Task; db = SessionLocal(); print([t.status for t in db.query(Task).all()])"
```

### GPU no se detecta
Verifique que NVIDIA Container Toolkit esté instalado:
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Frontend no se conecta al backend
Verifique las variables de entorno:
```bash
docker compose exec frontend env | grep BACKEND_URL
# Debe mostrar: BACKEND_URL=http://backend-api:8000
```

### MinIO no está accesible
Espere a que el healthcheck pase:
```bash
docker compose ps minio
# Debe mostrar: healthy
```

## Despliegue en Producción

Para deployment en producción:

1. **Cambiar `SECRET_KEY`** en `.env` por un valor aleatorio seguro
2. **Configurar CORS** con el dominio real en `CORS_ALLOWED_ORIGINS`
3. **Habilitar HTTPS** y configurar cookies con `*_SECURE=true`
4. **Usar nginx** como reverse proxy delante del frontend
5. **Configurar SSL/TLS** (Let's Encrypt)
6. **Cambiar credenciales** de PostgreSQL y MinIO
7. **Configurar backups** de volúmenes (`postgres_data`, `minio_data`, `model_weights`)
8. **Monitorear logs** con herramientas como Loki/Grafana o servicios cloud
9. Mantener `SECRET_KEY` y credenciales en variables de entorno/secretos seguros, nunca en código

## Documentación Adicional

- Ver `DOCKER_README.md` para guía detallada de Docker y troubleshooting
- Ver `DOCKERIZACION_RESUMEN.md` para resumen técnico de la arquitectura dockerizada

Ejecuté el `docker-compose.yaml` y funcionó. Pero hacé un `docker ps` y fijate, no deberían haber 5 contenedores ejecutándose? Por qué solo hay 4? Analizá los logs si querés y el proyecto para entender qué pasó y solucionarlo.