import subprocess
import os
from pathlib import Path
import time
import httpx

import typer

from app.services.dependencies import get_task_service, get_bucket_service, get_inference_service
from app.db import get_db_session
from app.crud import task as task_crud

def notify_backend(task_id: int, status: str):
    try:
        # La URL del backend-api dentro de la red de Docker
        url = "http://backend-api:8000/internal/notify"
        httpx.post(url, json={"task_id": task_id, "status": status}, timeout=10.0)
        typer.echo(f"Notificación enviada al backend: Tarea {task_id} -> {status}")
    except Exception as e:
        typer.echo(f"Error notificando al backend: {e}")

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
    
    local_video_path = None
    # Obtener la sesión de base de datos y los servicios
    db_gen = get_db_session()
    db = next(db_gen)
    
    try:
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
            task_service.update_task_status(task_to_process.id, "PROCESSING", commit=True)
            notify_backend(task_to_process.id, "PROCESSING")
            
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
                "--no_display",
            ]
            
            typer.echo("Ejecutando el script `process.py`...")
            typer.echo(f"Comando: {' '.join(command)}")
            
            # Archivos temporales para capturar salida
            stdout_path = f"stdout_{task_to_process.id}.txt"
            stderr_path = f"stderr_{task_to_process.id}.txt"
            
            cancelled = False
            stdout = ""
            stderr = ""
            
            with open(stdout_path, "w+") as stdout_file, open(stderr_path, "w+") as stderr_file:
                # Ejecuta el comando en un subproceso sin bloquear
                process = subprocess.Popen(command, stdout=stdout_file, stderr=stderr_file, text=True)
                
                # Monitorear el proceso y la existencia de la tarea
                while process.poll() is None:
                    # Refrescar sesión y verificar si la tarea sigue existiendo
                    db.expire_all()
                    task_check = task_crud.find_one_by_fields(db, id=task_to_process.id)
                    
                    if not task_check:
                        typer.echo(f"ALERTA: La tarea {task_to_process.id} ha sido eliminada. Cancelando ejecución...")
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        cancelled = True
                        break
                    
                    time.sleep(2)
                
                if not cancelled:
                    # Leer salidas
                    stdout_file.seek(0)
                    stderr_file.seek(0)
                    stdout = stdout_file.read()
                    stderr = stderr_file.read()
                
            # Limpiar archivos de log temporales
            if os.path.exists(stdout_path):
                os.remove(stdout_path)
            if os.path.exists(stderr_path):
                os.remove(stderr_path)

            if cancelled:
                raise typer.Exit(code=0)

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command, output=stdout, stderr=stderr)
                
            # Objeto resultado compatible con subprocess.run
            class ProcessResult:
                def __init__(self, stdout, stderr):
                    self.stdout = stdout
                    self.stderr = stderr
            
            result = ProcessResult(stdout, stderr)
            
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
            notify_backend(task_to_process.id, "PROCESSED")
            
            # Mostrar resultados
            typer.echo("\n--- Salida del script process.py ---")
            typer.echo(result.stdout)
            typer.echo("-------------------------------------\n")
            typer.echo(f"Tarea finalizada exitosamente para el video {task_to_process.id}.")
            
        except subprocess.CalledProcessError as e:
            # Hacer rollback de toda la transacción
            db.rollback()
            typer.echo("Error en el procesamiento. Haciendo rollback de todos los cambios...")
            
            # Revertir estado a READY_TO_PROCESS
            try:
                typer.echo("Revirtiendo estado de tarea a READY_TO_PROCESS...")
                task_service.update_task_status(task_to_process.id, "READY_TO_PROCESS", commit=True)
            except Exception as ex:
                typer.echo(f"Error al revertir estado: {ex}")

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
            
            # Revertir estado a READY_TO_PROCESS
            try:
                typer.echo("Revirtiendo estado de tarea a READY_TO_PROCESS...")
                task_service.update_task_status(task_to_process.id, "READY_TO_PROCESS", commit=True)
            except Exception as ex:
                typer.echo(f"Error al revertir estado: {ex}")

            typer.echo("Error: Asegúrate de que `process.py` existe en la ruta especificada.")
            typer.echo(f"Error: {e}")
        except Exception as e:
            # Cualquier otro error
            db.rollback()
            typer.echo(f"Error inesperado: {str(e)}. Haciendo rollback de todos los cambios...")
            
            # Revertir estado a READY_TO_PROCESS
            try:
                typer.echo("Revirtiendo estado de tarea a READY_TO_PROCESS...")
                task_service.update_task_status(task_to_process.id, "READY_TO_PROCESS", commit=True)
            except Exception as ex:
                typer.echo(f"Error al revertir estado: {ex}")
            
    finally:
        # Limpiar el archivo temporal del video
        if local_video_path and os.path.exists(local_video_path):
            os.remove(local_video_path)
            typer.echo(f"Archivo temporal eliminado: {local_video_path}")
        
        db_gen.close()
        typer.Exit(code=0)

if __name__ == "__main__":
    app()