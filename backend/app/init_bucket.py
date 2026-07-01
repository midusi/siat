"""
Script de inicialización del bucket de MinIO.
Crea el bucket 'MINIO_BUCKET_NAME' si no existe y aplica la política de lectura pública.
"""
from services.bucket_service import BucketService

def init_bucket():
    """Inicializa el bucket de MinIO si no existe."""
    try:
        bs = BucketService()
        print(f"🔧 Inicializando bucket '{bs.BUCKET_NAME}' en MinIO...")
        # Verificar si el bucket existe
        buckets = bs.s3_client.list_buckets()
        bucket_names = [bucket['Name'] for bucket in buckets.get('Buckets', [])]
        
        if bs.BUCKET_NAME not in bucket_names:
            print(f"🪣 Creando bucket '{bs.BUCKET_NAME}'...")
            bs.s3_client.create_bucket(Bucket=bs.BUCKET_NAME)
            print(f"✔ Bucket '{bs.BUCKET_NAME}' creado exitosamente")
        else:
            print(f"🔁 Bucket '{bs.BUCKET_NAME}' ya existe")
        
        # Aplicar política de lectura pública
        print(f"🔐 Aplicando política de lectura pública al bucket...")
        bs.set_public_read_policy()
        print(f"✔ Inicialización del bucket completada")
        
    except Exception as e:
        print(f"❌ Error al inicializar el bucket {bs.BUCKET_NAME} : {e}")
        raise

if __name__ == "__main__":
    init_bucket()
