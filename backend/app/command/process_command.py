import subprocess
import os
from pathlib import Path

import typer

from app.services.dependencies import get_task_service, get_bucket_service, get_inference_service
from app.db import get_db_session



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
    inference_service = get_inference_service(db)
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
    input_video_path = local_video_path
    
    # Paso 4: Obtener los polígonos de entrada y salida
    roads = task_service.get_roads_by_task(task_to_process)
    
    polygons_in = [road.polygon for road in roads if road.direction == "Entrada"]
    polygons_out = [road.polygon for road in roads if road.direction == "Salida"]
    excluded_zones = [road.polygon for road in roads if road.direction == "Excluida"]
    
    names_polygons_in = [road.name for road in roads if road.direction == "Entrada"]
    names_polygons_out = [road.name for road in roads if road.direction == "Salida"]
    
    # Manejar la transacción completa
    try:
        typer.echo("Cambiando estado de tarea a PROCESSING...")
        task_service.update_task_status(task_to_process.id, "PROCESSING")
        
        # Paso 5: Construir y ejecutar el comando
        path_modelo = Path(__file__).resolve().parent.parent / "modelo"
        command = [
            "python",
            str(path_modelo / "process.py"),
            f"--input_video_path={input_video_path}",
            f"--model_path={path_modelo / 'model-v5.pt'}",
            f"--tracker_path={path_modelo / 'botsort_custom.yaml'}",
            f"--polygons_in={polygons_in}",
            f"--polygons_out={polygons_out}",
            f"--excluded_zones={excluded_zones}",
            "--names_polygons_in", str(names_polygons_in),
            "--names_polygons_out", str(names_polygons_out),
        ]
        
        typer.echo("Ejecutando el script `process.py`...")
        typer.echo(f"Comando: {' '.join(command)}")
        # Ejecuta el comando en un subproceso
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        
        # Paso 6: Obtener la información resultante del procesamiento
        # Obtener el directorio donde process.py generó los archivos
        video_name = os.path.splitext(os.path.basename(input_video_path))[0]
        output_dir = os.path.join(os.path.dirname(input_video_path), video_name)
        
        # Rutas locales de los archivos generados
        local_counts_path = os.path.join(output_dir, "transition_counts.json")
        local_undetermined_path = os.path.join(output_dir, "transition_undetermined_object.json")
        local_determined_path = os.path.join(output_dir, "transition_determined_object.json")
        local_data_obj_history_path = os.path.join(output_dir, "data_obj_history.json")
        
        # Obtener el nombre del video
        filename = os.path.basename(task_to_process.video.url)
        # Quitar la extensión
        hash_value, _ = os.path.splitext(filename)  
        
        bucket_video_path = f"task/{task_to_process.id}/{hash_value}_processed.mp4"
        bucket_data_obj_history_path = f"task/{task_to_process.id}/{hash_value}_data_obj_history.json"

        # Leer transition_counts.json
        with open(local_counts_path, 'r', encoding='utf-8') as f:
            counts_content = f.read()
        
        # Leer transition_undetermined_object.json
        with open(local_undetermined_path, 'r', encoding='utf-8') as f:
            undetermined_content = f.read()
        
        # Leer transition_determined_object.json
        with open(local_determined_path, 'r', encoding='utf-8') as f:
            determined_content = f.read()
        
        # Subir data_obj_history.json al bucket
        typer.echo("Subiendo el archivo data_obj_history.json al bucket...")
        with open(local_data_obj_history_path, 'rb') as f:
            bucket_service.upload(f, object_name=bucket_data_obj_history_path, content_type="application/json")
        
        # Paso 7: Crear el objeto de inferencia
        inference = inference_service.create_inference(
            task_id=task_to_process.id,
            transition_counts=counts_content,
            transition_undetermined=undetermined_content,
            transition_determined=determined_content,
            url_data_obj_history=bucket_data_obj_history_path,
            url_video_processed=bucket_video_path
        )
        
        # Paso 8: Cambiar estado de tarea a PROCESSED
        task_service.update_task_status(task_to_process.id, "PROCESSED")
        
        db.commit()
        
        # Mostrar resultados
        typer.echo("\n--- Salida del script process.py ---")
        typer.echo(result.stdout)
        typer.echo("-------------------------------------\n")
        typer.echo(f"Tarea finalizada exitosamente para el video {task_to_process.id}.")
        
    except subprocess.CalledProcessError as e:
        # Hacer rollback de toda la transacción
        db.rollback()
        typer.echo("Error en el procesamiento. Haciendo rollback de todos los cambios...")
        
        typer.echo(f"Error: El script `process.py` falló con código {e.returncode}")
        typer.echo("\n--- Salida estándar (stdout) ---")
        typer.echo(e.stdout)
        typer.echo("\n--- Salida de error (stderr) ---")
        typer.echo(e.stderr)
        typer.echo("-------------------------------------\n")
        
    except FileNotFoundError as e:
        # Hacer rollback de toda la transacción
        db.rollback()
        typer.echo("Error: Archivo no encontrado. Haciendo rollback de todos los cambios...")
        typer.echo("Error: Asegúrate de que `process.py` existe en la ruta especificada.")
        typer.echo(f"Error: {e}")
    except Exception as e:
        # Cualquier otro error
        db.rollback()
        typer.echo(f"Error inesperado: {str(e)}. Haciendo rollback de todos los cambios...")
        
    finally:
        # Limpiar el archivo temporal del video
        if os.path.exists(local_video_path):
            os.remove(local_video_path)
            typer.echo(f"Archivo temporal eliminado: {local_video_path}")
        
        typer.Exit(code=0)

if __name__ == "__main__":
    app()