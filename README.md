# Backend

Este proyecto es una API desarrollada con FastAPI.

## Configuración y Ejecución

Siga estos pasos para configurar y ejecutar el proyecto en su entorno local.

### Prerrequisitos

- Docker y Docker Compose instalados.
- Python 3.10+ instalado.
- pip (manejador de paquetes de Python) instalado.

### 0. Variables de entorno

Copie el archivo `backend/.env.example` a `backend/.env` y ajuste los valores (especialmente `SECRET_KEY`).

- Seguridad y cookies:
  - En desarrollo (`docker-compose` local), mantenga `AUTH_COOKIE_SECURE=false` y `AUTH_REFRESH_COOKIE_SECURE=false` y `AUTH_COOKIE_SAMESITE=Lax`.
  - En producción sobre HTTPS, ponga `*_SECURE=true` y ajuste `*_SAMESITE=None` y `AUTH_COOKIE_DOMAIN` acorde a su dominio.
- CORS: configure `CORS_ALLOWED_ORIGINS` (coma-separado) para el/los orígenes del frontend en producción.

### 1. Levantar la Base de Datos PostgreSQL con Docker Compose

```bash
# desde la raíz del repo
docker-compose up -d db minio
```

### 2. Instalar Dependencias (backend)

Desde el directorio `backend/`:

```bash
pip install -r requirements.txt
```

### 3. Ejecutar Migraciones con Alembic

```bash
alembic upgrade head
```

### 4. Ejecutar Seeds

```bash
python app/seeds.py
```

### 5. Ejecutar el Servidor de Desarrollo

Desde `backend/`:

```bash
uvicorn app.main:app --reload
```

Una vez que el servidor esté en funcionamiento: `http://127.0.0.1:8000`.

### 6. Despliegue con Docker Compose

Se agregó un servicio `backend` (opcional). Antes de build, cree `backend/Dockerfile` y configure envs. Variables clave pasan por `docker-compose.yaml`.

## Autenticación y Autorización

- Login/refresh/logout y cookies httpOnly.
- Roles: `ROLE_ADMIN`, `ROLE_OPERADOR`.
- Rutas protegidas por `get_current_user` y `require_role`.

## Hardening (Hito 5)

- Rate limiting y lockout en `/auth/login`.
- Bcrypt con costo configurable y rehash transparente.
- Auditoría de eventos de seguridad.

## Recuperación de contraseña (Hito 6)

- Tokens HMAC firmados con expiración.
- Endpoints `/auth/password/request` y `/auth/password/perform`.
- Servicio de email con stub (por defecto) o SMTP.

## Observabilidad (Hito 8)

- Métricas mínimas expuestas en `GET /observability/metrics` (solo admin):
  - `total_login_attempts`, `failed_login_attempts`, `successful_logins`, `active_users`.

## Frontend

- SvelteKit con proxy `/api` hacia el backend.
- Cookies y CORS ajustados para SSR.

## Flujos y roles

- Admin puede crear/editar/habilitar/inhabilitar usuarios y resetear contraseñas.
- Operador puede gestionar tareas según permisos.

## Crear el usuario admin

- Vía seeds: `python app/seeds.py` crea `admin:admin` si no existe.
- O automáticamente al correr el runner de tests E2E.

## Tests

- Runner E2E e integración: `python backend/scripts/run_functional_tests.py`
  - Incluye smoke del frontend (opcional con `RUN_FRONT_TESTS=1`).
  - Agregados tests unitarios ligeros de JWT y hashing, y métricas.

## Notas de producción

- Habilite HTTPS y `*_SECURE=true` para cookies.
- Ajuste `CORS_ALLOWED_ORIGINS` con el dominio del frontend.
- Mantenga `SECRET_KEY` y credenciales en variables de entorno/secretos del entorno, nunca en código.
