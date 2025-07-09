# Backend

Este proyecto es una API desarrollada con FastAPI.

## Configuración y Ejecución

Siga estos pasos para configurar y ejecutar el proyecto en su entorno local.

### Prerrequisitos

- Docker y Docker Compose instalados.
- Python 3.10+ instalado.
- pip (manejador de paquetes de Python) instalado.

### 1. Levantar la Base de Datos PostgreSQL con Docker Compose

Ejecute el siguiente comando para iniciar el servicio de PostgreSQL en segundo plano:

```bash
docker-compose up -d
```
Esto utilizará la configuración definida en su archivo `docker-compose.yml` para levantar el contenedor de PostgreSQL con las credenciales necesarias.

### 2. Instalar Dependencias

Instale las dependencias del proyecto utilizando pip y el archivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 3. Ejecutar Migraciones con Alembic

Para aplicar las migraciones de la base de datos, ejecute:

```bash
alembic upgrade head
```
Asegúrese de que Alembic esté configurado correctamente en su proyecto (generalmente a través de un archivo `alembic.ini`).

### 4. Ejecutar Seeds

Para poblar la base de datos con datos iniciales, ejecute el script de seeds:

```bash
python app/seeds.py
```
Este comando asume que su script de seeds se encuentra en `app/seeds.py` y es ejecutable directamente con Python.

### 5. Ejecutar el Servidor de Desarrollo

Finalmente, para iniciar el servidor de FastAPI con Uvicorn, ejecute:

```bash
uvicorn app.main:app --reload
```

Una vez que el servidor esté en funcionamiento, generalmente podrá acceder a la API en `http://127.0.0.1:8000`. 
