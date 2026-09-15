from __future__ import annotations

import json
import os
from typing import Optional

from fastapi import UploadFile

from app.domain.exceptions import StorageError, StorageNotFound


class MinioObjectStorage:
    BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME")

    def __init__(self):
        import boto3
        from botocore.client import Config

        self.endpoint_url = os.getenv("MINIO_ENDPOINT_URL")
        self.public_endpoint_url = os.getenv("MINIO_PUBLIC_URL")
        access_key = os.getenv("MINIO_ROOT_USER")
        access_secret = os.getenv("MINIO_ROOT_PASSWORD")
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=access_secret,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self._s3_client_public = boto3.client(
            "s3",
            endpoint_url=self.public_endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=access_secret,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    @classmethod
    def from_env(cls) -> "MinioObjectStorage":
        return cls()

    @property
    def bucket_name(self) -> str:
        return self.BUCKET_NAME or ""

    def public_url(self, key: str) -> str:
        return f"/bucket/{self.bucket_name}/{key}"

    def set_public_read_policy(self):
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.BUCKET_NAME}/*"],
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:ListBucket"],
                    "Resource": [f"arn:aws:s3:::{self.BUCKET_NAME}"],
                },
            ],
        }
        try:
            self._s3_client.put_bucket_policy(Bucket=self.BUCKET_NAME, Policy=json.dumps(policy))
            print(f"Política de lectura pública aplicada al bucket '{self.BUCKET_NAME}'.")
        except Exception as e:
            print(f"Error al aplicar la política de bucket: {e}")

    def _infer_content_type(self, object_name: str, default: Optional[str] = None) -> str:
        if default:
            return default
        ext = os.path.splitext(object_name)[1].lower()
        if ext == ".json":
            return "application/json"
        if ext in (".mp4", ".m4v"):
            return "video/mp4"
        if ext in (".avi",):
            return "video/x-msvideo"
        if ext in (".mov",):
            return "video/quicktime"
        if ext in (".txt",):
            return "text/plain; charset=utf-8"
        return "application/octet-stream"

    def upload(self, data, object_name: str, content_type: Optional[str] = None):
        self.set_public_read_policy()
        try:
            ct = content_type or self._infer_content_type(object_name)
            body = None

            if isinstance(data, UploadFile) or hasattr(data, "file") and hasattr(getattr(data, "file"), "read"):
                f = getattr(data, "file", None) or data.file
                try:
                    f.seek(0)
                except Exception:
                    pass
                body = f.read()
            elif isinstance(data, (bytes, bytearray)):
                body = bytes(data)
            elif isinstance(data, str):
                body = data.encode("utf-8")
            elif hasattr(data, "read") and callable(getattr(data, "read")):
                body = data.read()
            else:
                raise TypeError("Tipo de dato no soportado para upload. Use UploadFile, bytes, str o file-like object.")

            if not isinstance(body, (bytes, bytearray)):
                raise TypeError("El cuerpo a subir debe ser bytes; verifique si intentó usar un método async sin await.")

            self._s3_client.put_object(
                Bucket=self.BUCKET_NAME,
                Key=object_name,
                Body=body,
                ContentType=ct,
            )
            print(f"Objeto subido a '{self.BUCKET_NAME}/{object_name}'")
        except Exception as e:
            print(f"Error al subir el archivo: {e}")
            raise

    def download(self, path: str, object_name: str):
        try:
            print(f"Descargando '{object_name}' desde bucket '{self.BUCKET_NAME}' a '{path}'...")
            self._s3_client.download_file(self.BUCKET_NAME, object_name, path)
            print(f"'{object_name}' descargado a '{path}'")
        except Exception as e:
            print(f"Error al descargar el archivo: {e}")

    def delete_object(self, key: str):
        try:
            self._s3_client.delete_object(Bucket=self.BUCKET_NAME, Key=key)
            print(f"Objeto eliminado '{self.BUCKET_NAME}/{key}'")
        except Exception as e:
            print(f"Error al eliminar el objeto: {e}")
            raise

    def delete_prefix(self, prefix: str):
        try:
            continuation_token = None
            while True:
                kwargs = {
                    "Bucket": self.BUCKET_NAME,
                    "Prefix": prefix.rstrip("/") + "/",
                    "MaxKeys": 1000,
                }
                if continuation_token:
                    kwargs["ContinuationToken"] = continuation_token

                resp = self._s3_client.list_objects_v2(**kwargs)
                objects = resp.get("Contents", [])
                if not objects:
                    break

                delete_payload = {
                    "Objects": [{"Key": obj["Key"]} for obj in objects],
                    "Quiet": True,
                }
                self._s3_client.delete_objects(Bucket=self.BUCKET_NAME, Delete=delete_payload)

                if resp.get("IsTruncated"):
                    continuation_token = resp.get("NextContinuationToken")
                else:
                    break
            print(f"Objetos bajo prefijo '{self.BUCKET_NAME}/{prefix}' eliminados")
        except Exception as e:
            print(f"Error al eliminar por prefijo: {e}")
            raise

    def stream_object(self, object_name: str, chunk_size: int = 1024 * 1024):
        try:
            obj = self._s3_client.get_object(Bucket=self.BUCKET_NAME, Key=object_name)
            body = obj["Body"]
            content_type = obj.get("ContentType") or self._infer_content_type(object_name)
            content_length = obj.get("ContentLength")

            def iter_chunks():
                while True:
                    chunk = body.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            return iter_chunks(), content_type, content_length
        except self._s3_client.exceptions.NoSuchKey:
            raise StorageNotFound(f"Objeto no encontrado: {object_name}")
        except Exception as e:
            raise StorageError(f"Error al obtener objeto '{object_name}': {e}")

    def generate_presigned_upload_url(
        self, object_name: str, expiration: int = 3600, content_type: Optional[str] = None
    ) -> str:
        try:
            params = {
                "Bucket": self.BUCKET_NAME,
                "Key": object_name,
            }
            if content_type:
                params["ContentType"] = content_type
            url = self._s3_client_public.generate_presigned_url(
                "put_object",
                Params=params,
                ExpiresIn=expiration,
                HttpMethod="PUT",
            )
            print(f"Generated presigned URL for upload to '{self.BUCKET_NAME}/{object_name}'")
            print(f"Public URL: {url}")
            return url
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            raise

    def exists(self, object_name: str) -> bool:
        try:
            self._s3_client.head_object(Bucket=self.BUCKET_NAME, Key=object_name)
            return True
        except Exception:
            return False

    def copy(self, source_key: str, dest_key: str) -> None:
        self._s3_client.copy_object(
            Bucket=self.BUCKET_NAME,
            CopySource={"Bucket": self.BUCKET_NAME, "Key": source_key},
            Key=dest_key,
        )

    def ensure_bucket(self) -> None:
        buckets = self._s3_client.list_buckets()
        bucket_names = [bucket["Name"] for bucket in buckets.get("Buckets", [])]
        if self.BUCKET_NAME not in bucket_names:
            print(f"🪣 Creando bucket '{self.BUCKET_NAME}'...")
            self._s3_client.create_bucket(Bucket=self.BUCKET_NAME)
            print(f"✔ Bucket '{self.BUCKET_NAME}' creado exitosamente")
        else:
            print(f"🔁 Bucket '{self.BUCKET_NAME}' ya existe")
        self.set_public_read_policy()
