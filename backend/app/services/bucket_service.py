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
        # URL interna para operaciones del backend
        self.endpoint_url = os.getenv('MINIO_ENDPOINT_URL', 'http://localhost:9000')
        # URL pública para que el navegador pueda acceder (usada en presigned URLs)
        self.public_endpoint_url = os.getenv('MINIO_PUBLIC_URL', 'http://localhost:9000')
        
        # Cliente S3 para operaciones internas (upload, download, delete, etc.)
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            config=Config(signature_version='s3v4'),
            region_name='us-east-1' # La región no es crítica para MinIO, pero el SDK la requiere
        )
        
        # Cliente S3 separado para generar URLs presignadas con el endpoint público
        # Esto es necesario porque la firma criptográfica incluye el endpoint URL
        self.s3_client_public = boto3.client(
            's3',
            endpoint_url=self.public_endpoint_url,
            aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            config=Config(signature_version='s3v4'),
            region_name='us-east-1'
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
        - Si `data` es UploadFile (FastAPI) o tiene atributo `.file`, lee bytes desde `data.file.read()`.
        - Si `data` es bytes/bytearray o str, usa put_object.
        - Si `data` es file-like object con `.read()`, lee bytes desde allí.
        - `content_type` es opcional; si no se provee se infiere por extensión.
        """
        self.set_public_read_policy()
        try:
            ct = content_type or self._infer_content_type(object_name)
            body = None

            # Caso 1: FastAPI/Starlette UploadFile o cualquier objeto con `.file.read()`
            if isinstance(data, UploadFile) or hasattr(data, 'file') and hasattr(getattr(data, 'file'), 'read'):
                f = getattr(data, 'file', None) or data.file  # por claridad
                try:
                    f.seek(0)
                except Exception:
                    pass
                body = f.read()
            # Caso 2: bytes o bytearray
            elif isinstance(data, (bytes, bytearray)):
                body = bytes(data)
            # Caso 3: str
            elif isinstance(data, str):
                body = data.encode('utf-8')
            # Caso 4: file-like con read() síncrono
            elif hasattr(data, 'read') and callable(getattr(data, 'read')):
                # Nota: si `data.read` es async (como UploadFile.read), no caemos aquí gracias a los casos previos
                body = data.read()
            else:
                raise TypeError("Tipo de dato no soportado para upload. Use UploadFile, bytes, str o file-like object.")

            if not isinstance(body, (bytes, bytearray)):
                raise TypeError("El cuerpo a subir debe ser bytes; verifique si intentó usar un método async sin await.")

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

    # --- NEW: deletion helpers ---
    def delete_object(self, key: str):
        """Elimina un objeto por su key"""
        try:
            self.s3_client.delete_object(Bucket=self.BUCKET_NAME, Key=key)
            print(f"Objeto eliminado '{self.BUCKET_NAME}/{key}'")
        except Exception as e:
            print(f"Error al eliminar el objeto: {e}")
            raise

    def delete_prefix(self, prefix: str):
        """
        Elimina recursivamente todos los objetos bajo un prefijo (carpeta lógica).
        Ej: prefix='task/123' elimina 'task/123/...'
        """
        try:
            continuation_token = None
            while True:
                kwargs = {
                    'Bucket': self.BUCKET_NAME,
                    'Prefix': prefix.rstrip('/') + '/',
                    'MaxKeys': 1000,
                }
                if continuation_token:
                    kwargs['ContinuationToken'] = continuation_token

                resp = self.s3_client.list_objects_v2(**kwargs)
                objects = resp.get('Contents', [])
                if not objects:
                    break

                # Borrar por lotes (máximo 1000 por request)
                delete_payload = {
                    'Objects': [{'Key': obj['Key']} for obj in objects],
                    'Quiet': True
                }
                self.s3_client.delete_objects(Bucket=self.BUCKET_NAME, Delete=delete_payload)

                if resp.get('IsTruncated'):
                    continuation_token = resp.get('NextContinuationToken')
                else:
                    break
            print(f"Objetos bajo prefijo '{self.BUCKET_NAME}/{prefix}' eliminados")
        except Exception as e:
            print(f"Error al eliminar por prefijo: {e}")
            raise
    
    def stream_object(self, object_name: str, chunk_size: int = 1024 * 1024):
        """Devuelve un generador para transmitir (stream) un objeto grande desde el bucket.
        Retorna (generator, content_type, content_length)
        """
        try:
            obj = self.s3_client.get_object(Bucket=self.BUCKET_NAME, Key=object_name)
            body = obj['Body']
            content_type = obj.get('ContentType') or self._infer_content_type(object_name)
            content_length = obj.get('ContentLength')

            def iter_chunks():
                while True:
                    chunk = body.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            return iter_chunks(), content_type, content_length
        except self.s3_client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"Objeto no encontrado: {object_name}")
        except Exception as e:
            raise RuntimeError(f"Error al obtener objeto '{object_name}': {e}")
    
    def generate_presigned_upload_url(self, object_name: str, expiration: int = 3600, content_type: Optional[str] = None) -> str:
        """
        Genera una URL presignada para permitir uploads directos desde el navegador a MinIO/S3.
        Esto evita pasar archivos grandes a través del servidor backend.
        
        Args:
            object_name: La key/nombre del objeto en el bucket
            expiration: Tiempo en segundos hasta que expire la URL (default: 1 hora)
            content_type: Content-Type esperado del archivo (opcional pero recomendado)
        
        Returns:
            URL presignada que el cliente puede usar para hacer PUT directo
        """
        try:
            params = {
                'Bucket': self.BUCKET_NAME,
                'Key': object_name,
            }
            
            # Si se especifica content_type, requerirlo en la firma
            if content_type:
                params['ContentType'] = content_type
            
            # IMPORTANTE: Usar el cliente público para generar la URL
            # Esto asegura que la firma criptográfica sea válida para el endpoint público
            url = self.s3_client_public.generate_presigned_url(
                'put_object',
                Params=params,
                ExpiresIn=expiration,
                HttpMethod='PUT'
            )
            
            print(f"Generated presigned URL for upload to '{self.BUCKET_NAME}/{object_name}'")
            print(f"Public URL: {url}")
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            raise