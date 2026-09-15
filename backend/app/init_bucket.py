"""
Script de inicialización del bucket de object storage.
Crea el bucket 'MINIO_BUCKET_NAME' si no existe y aplica la política de lectura pública.
"""
from app.adapters.wiring import build_object_storage

def init_bucket():
    """Inicializa el bucket si no existe."""
    storage = build_object_storage()
    try:
        print(f"🔧 Inicializando bucket '{storage.bucket_name}'...")
        storage.ensure_bucket()
        print(f"✔ Inicialización del bucket completada")
    except Exception as e:
        print(f"❌ Error al inicializar el bucket {storage.bucket_name} : {e}")
        raise

if __name__ == "__main__":
    init_bucket()
