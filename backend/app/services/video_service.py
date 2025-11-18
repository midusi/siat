import base64
import tempfile
import shutil
import cv2
import numpy as np
from fastapi import UploadFile
from sqlalchemy.orm import sessionmaker
from pymediainfo import MediaInfo
from app.services.bucket_service import BucketService


class VideoService:
    def __init__(self, db: sessionmaker, bucket_service: BucketService):
        self.db = db
        self.bucket_service = bucket_service

    def get_metadata_video(self, file: UploadFile) -> dict:
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name

            media_info = MediaInfo.parse(tmp_path)
            for track in media_info.tracks:
                if track.track_type == "Video":
                    duration = int(track.duration / 1000) if track.duration else None
                    fps = float(track.frame_rate) if track.frame_rate else None
                    width = int(track.width) if track.width else None
                    height = int(track.height) if track.height else None

                    return {
                        "duration": duration, #in secords
                        "fps": fps,
                        "width": width,
                        "height": height
                    }
        except Exception as e:
            file.file.close()
            raise ValueError(f"No se pudo obtener la duración del video: {e}")
        finally:
            file.file.seek(0)
            
    def get_frame(self, video_key: str, frame_number: int) -> str:
        """
        Obtiene un frame específico de un video almacenado en MinIO.

        Args:
            video_key (str): La key (URL del objeto) del video en MinIO.
            frame_number (int): El número del frame a extraer.

        Returns:
            str: El frame codificado en Base64.
        """
        # Usamos un archivo temporal que se elimina automáticamente al salir del bloque 'with'
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
            temp_path = tmp.name
            
            try:
                # 1. Descargar el video desde MinIO al archivo temporal
                self.bucket_service.download(temp_path, video_key)
            except Exception as e:
                # Si falla la descarga, lanza un error claro.
                raise ValueError(f"Could not download video '{video_key}' from bucket: {e}")

            # 2. Abrir el video desde el archivo temporal con OpenCV
            cap = cv2.VideoCapture(temp_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open temporary video file: {temp_path}")

            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            cap.release()

            if not ret:
                raise ValueError(f"Cannot read frame {frame_number} from video: {video_key}")

            # 3. Codificar el frame a JPG y luego a Base64
            _, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')

            # 4. Devolver la cadena Base64
            return jpg_as_text
        
    def get_video_stream(self, video_key: str):
        """Obtiene un generador de bytes para transmitir el video desde el bucket.
        Devuelve (generator, content_type, content_length)
        """
        return self.bucket_service.stream_object(video_key)
    
    def get_metadata_from_s3(self, object_key: str) -> dict:
        """
        Obtiene metadata de un video ya almacenado en MinIO.
        Descarga temporalmente el video, extrae la metadata y lo elimina.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp_path = tmp.name
        
        try:
            # Descargar video desde MinIO
            self.bucket_service.download(tmp_path, object_key)
            
            # Extraer metadata
            media_info = MediaInfo.parse(tmp_path)
            for track in media_info.tracks:
                if track.track_type == "Video":
                    duration = int(track.duration / 1000) if track.duration else None
                    fps = float(track.frame_rate) if track.frame_rate else None
                    width = int(track.width) if track.width else None
                    height = int(track.height) if track.height else None

                    return {
                        "duration": duration,  # in seconds
                        "fps": fps,
                        "width": width,
                        "height": height
                    }
            
            raise ValueError("No se encontró track de video en el archivo")
        except Exception as e:
            raise ValueError(f"No se pudo obtener metadata del video: {e}")
        finally:
            # Limpiar archivo temporal
            try:
                import os
                os.unlink(tmp_path)
            except:
                pass