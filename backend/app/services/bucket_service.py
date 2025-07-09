# services/bucket_service.py
from fastapi import UploadFile
import json
import boto3
from botocore.client import Config

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
    
    def upload(self, file: UploadFile, object_name: str):
        self.set_public_read_policy()
        try:
            self.s3_client.upload_fileobj(file.file, self.BUCKET_NAME, object_name)
            print(f"'{file.filename}' subido a '{self.BUCKET_NAME}/{object_name}'")
        except Exception as e:
            print(f"Error al subir el archivo: {e}")
            
    def download(self, path: str, object_name: str):
        try:
            self.s3_client.download_file(self.BUCKET_NAME, object_name, path)
            print(f"'{object_name}' descargado a '{path}'")
        except Exception as e:
            print(f"Error al descargar el archivo: {e}")