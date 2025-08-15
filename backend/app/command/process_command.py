import subprocess
import os
from pathlib import Path

import typer

from app.services.dependencies import get_task_service, get_bucket_service
from app.db import get_db_session

def get_params_from_db(video_id: str):
    """
    Función que simula la obtención de parámetros desde una base de datos.
    Aquí iría tu lógica de conexión a la BD, una consulta, etc.
    """
    # En un caso real, esto sería una consulta a SQLAlchemy o similar
    # Ejemplo de datos simulados:
    return {
        "input_video_path": f"/path/to/videos/{video_id}.mp4",
        "polygons_in": "[0,0,10,10],[20,20,30,30]",
        "polygons_out": "[0,100,10,110],[20,120,30,130]"
    }

# Crea una instancia de Typer para tu aplicación CLI
app = typer.Typer(
    help="Orquestador para ejecutar el script de procesamiento de video."
)

@app.command()
def run_process():
    """
    Obtiene la primer tarea lista para procesar de la cola de tareas (más antigua en la BD).
    """
    typer.echo(f"Verificando que no haya ninguna tarea procesando actualmente...")
    
    # Obtener la sesión de base de datos y los servicios
    db = next(get_db_session())
    task_service = get_task_service(db)
    bucket_service = get_bucket_service()
    
    # Paso1: Verificar si hay alguna tarea en estado "processing"
    processing_tasks = task_service.get_tasks_by_status(status_id="PROCESSING")
    if processing_tasks:
        typer.echo(f"Hay una tarea en proceso. ID: {processing_tasks[0].id}")
        raise typer.Exit(code=1)

    # Paso2: Verificar que haya alguna tarea lista para procesar y obtener sus parámetros
    typer.echo(f"Verificando que haya alguna tarea lista para procesar y obteniendo sus parámetros...")
    ready_to_process_tasks = task_service.get_tasks_by_status(status_id="READY_TO_PROCESS")
    if not ready_to_process_tasks:
        typer.echo(f"No hay ninguna tarea lista para procesar. Finalizando...")
        raise typer.Exit(code=0)
    task_to_process = ready_to_process_tasks[0]
    
    # Paso 3: Descargar el video del bucket
    typer.echo(f"Descargando video desde el bucket: {task_to_process.video.url}")
    video_key = task_to_process.video.url  # Asumiendo que url contiene la key del bucket
    local_video_path = f"temp_video_{task_to_process.id}.mp4"
    bucket_service.download(local_video_path, video_key)
    typer.echo(f"Video descargado localmente: {local_video_path}")
    input_video_path = local_video_path
    
    # Paso 4: Obtener los polígonos de entrada y salida
    roads = task_service.get_roads_by_task(task_to_process)
    print(f"Tipo de roads[0].polygon: {type(roads[0].polygon)}")
    print(f"roads[0].polygon: {roads[0].polygon}")
    
    # Usar directamente como listas (después de la migración a JSON)
    polygons_in = [road.polygon for road in roads if road.direction == "Entrada"]
    polygons_out = [road.polygon for road in roads if road.direction == "Salida"]
    
    typer.echo("Parámetros obtenidos de la base de datos. Procediendo a ejecutar el script `process.py`.")
    
    # Paso 5: Construir y ejecutar el comando
    try:
        path_modelo = Path(__file__).resolve().parent.parent / "modelo"
        command = [
            "python",
            str(path_modelo / "process.py"),
            f"--input_video_path={input_video_path}",
            f"--model_path={path_modelo / 'modelo.pt'}",
            f"--tracker_path={path_modelo / 'botsort_custom.yaml'}",
            f"--polygons_in={polygons_in}",
            f"--polygons_out={polygons_out}"
        ]
        
        # Ejecuta el comando en un subproceso
        # `check=True` hará que Python lance una excepción si el comando falla
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        
        # Opcional: imprimir la salida del subproceso en el log principal
        typer.echo("\n--- Salida del script process.py ---")
        typer.echo(result.stdout)
        typer.echo("-------------------------------------\n")
        
        typer.echo(f"Tarea finalizada exitosamente para el video {task_to_process.id}.")
        
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error: El script `process.py` falló con código {e.returncode}")
        typer.echo("\n--- Salida estándar (stdout) ---")
        typer.echo(e.stdout)
        typer.echo("\n--- Salida de error (stderr) ---")
        typer.echo(e.stderr)
        typer.echo("-------------------------------------\n")
        
    except FileNotFoundError:
        typer.echo("Error: Asegúrate de que `process.py` existe en la ruta especificada.")
        
    finally:
        # Limpiar el archivo temporal del video
        if os.path.exists(local_video_path):
            os.remove(local_video_path)
            typer.echo(f"Archivo temporal eliminado: {local_video_path}")
        
        typer.Exit(code=0)

if __name__ == "__main__":
    app()