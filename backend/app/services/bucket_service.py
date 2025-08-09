# services/bucket_service.py
from fastapi import UploadFile
import json
import boto3
from botocore.client import Config
from typing import Optional
import io
import os

class BucketService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url='http://localhost:9000',
            aws_access_key_id='minioadmin', # Cambia esto por tu clave de acceso de MinIO
            aws_secret_access_key='minioadmin', # Cambia esto por tu clave secreta de MinIO
            config=Config(signature_version='s3v4'),
            region_name='us-east-1' # La región no es crítica para MinIO, pero el SDK la requiere
        )
        
    BUCKET_NAME = 'traffic-analysis' # El nombre del bucket que creaste

    def set_public_read_policy(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": ["*"] # Permite acceso a cualquier entidad (público)
                    },
                    "Action": ["s3:GetObject"], # Permite la acción de obtener objetos
                    "Resource": [
                        f"arn:aws:s3:::{self.BUCKET_NAME}/*" # Aplica a todos los objetos en este bucket
                    ]
                }
            ]
        }
        policy_json = json.dumps(policy)

        try:
            self.s3_client.put_bucket_policy(Bucket=self.BUCKET_NAME, Policy=policy_json)
            print(f"Política de lectura pública aplicada al bucket '{self.BUCKET_NAME}'.")
        except Exception as e:
            print(f"Error al aplicar la política de bucket: {e}")
    
    def _infer_content_type(self, object_name: str, default: Optional[str] = None) -> str:
        if default:
            return default
        ext = os.path.splitext(object_name)[1].lower()
        if ext == '.json':
            return 'application/json'
        if ext in ('.mp4', '.m4v'):
            return 'video/mp4'
        if ext in ('.avi',):
            return 'video/x-msvideo'
        if ext in ('.mov',):
            return 'video/quicktime'
        if ext in ('.txt',):
            return 'text/plain; charset=utf-8'
        return 'application/octet-stream'

    def upload(self, data, object_name: str, content_type: Optional[str] = None):
        """
        Sube un objeto al bucket.
        - Si `data` es UploadFile (FastAPI), usa upload_fileobj.
        - Si `data` es bytes o str, usa put_object (convierte str a UTF-8).
        - `content_type` es opcional; si no se provee se infiere por extensión.
        """
        self.set_public_read_policy()
        try:
            # Caso 1: FastAPI UploadFile
            if isinstance(data, UploadFile):
                ct = content_type or self._infer_content_type(object_name)
                # ExtraArgs solo es soportado por upload_file, no upload_fileobj; para asegurar ContentType usamos put_object
                # leyendo el stream a memoria de forma segura.
                file_bytes = data.file.read()
                self.s3_client.put_object(
                    Bucket=self.BUCKET_NAME,
                    Key=object_name,
                    Body=file_bytes,
                    ContentType=ct
                )
                print(f"'{data.filename}' subido a '{self.BUCKET_NAME}/{object_name}'")
                return

            # Caso 2: file-like object con método read()
            if hasattr(data, 'read') and callable(getattr(data, 'read')):
                ct = content_type or self._infer_content_type(object_name)
                self.s3_client.put_object(
                    Bucket=self.BUCKET_NAME,
                    Key=object_name,
                    Body=data.read(),
                    ContentType=ct
                )
                print(f"Objeto file-like subido a '{self.BUCKET_NAME}/{object_name}'")
                return

            # Caso 3: bytes o str (por ejemplo JSON serializado)
            if isinstance(data, bytes):
                body = data
            elif isinstance(data, str):
                body = data.encode('utf-8')
            else:
                raise TypeError("Tipo de dato no soportado para upload. Use UploadFile, bytes, str o file-like object.")

            ct = content_type or self._infer_content_type(object_name)
            self.s3_client.put_object(
                Bucket=self.BUCKET_NAME,
                Key=object_name,
                Body=body,
                ContentType=ct
            )
            print(f"Objeto subido a '{self.BUCKET_NAME}/{object_name}'")
        except Exception as e:
            print(f"Error al subir el archivo: {e}")
            raise
            
    def download(self, path: str, object_name: str):
        try:
            self.s3_client.download_file(self.BUCKET_NAME, object_name, path)
            print(f"'{object_name}' descargado a '{path}'")
        except Exception as e:
            print(f"Error al descargar el archivo: {e}")