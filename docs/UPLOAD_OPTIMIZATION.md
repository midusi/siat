# Optimización de Uploads para Archivos Grandes

## Problema Identificado

### ¿Por qué apareció el límite de 512KB?

**Antes de dockerizar:**
- Frontend usaba `@sveltejs/adapter-auto` en modo desarrollo con `vite dev`
- En desarrollo, Vite no aplica límites estrictos de body size

**Después de dockerizar:**
- Frontend usa `@sveltejs/adapter-node` para producción
- SvelteKit aplica un límite predeterminado de **512KB** por seguridad
- Esto es intencional para prevenir ataques DoS (Denial of Service)

**Configuración actual (temporal):**
```yaml
BODY_SIZE_LIMIT: 104857600  # 100MB
```

## ⚠️ Problema con la Solución Actual

Aumentar `BODY_SIZE_LIMIT` a 100MB funciona para pruebas, pero **NO es escalable para producción**:

1. **Límites de HTTP Timeout**: Archivos de GB tardan mucho y pueden timeout
2. **Consumo de Memoria**: Cargar GBs en memoria del servidor puede causar crashes
3. **Recursos desperdiciados**: El servidor web no debería manejar transferencias masivas
4. **Bloqueo**: Mientras se sube un archivo grande, ese worker está ocupado
5. **No resistente a interrupciones**: Si la conexión se corta, se pierde todo el progreso

## ✅ Solución Recomendada: Upload Directo a MinIO

### Arquitectura Propuesta

```
┌──────────┐         1. Request        ┌──────────────┐
│ Browser  │────────────────────────────>│  Backend API │
│          │<────────────────────────────│              │
└──────────┘    2. Presigned URL        └──────────────┘
     │                                           │
     │                                           │
     │ 3. Upload directo                         │
     │    (PUT con archivo)                      │
     │                                           │
     ▼                                           ▼
┌──────────────────────────────────────────────────┐
│              MinIO Storage                       │
│          (No pasa por backend)                   │
└──────────────────────────────────────────────────┘
     │
     │ 4. Notificar completado
     ▼
┌──────────────┐
│  Backend API │
│  (Crear task)│
└──────────────┘
```

### Ventajas

✅ **Sin límites de tamaño**: Archivos de cualquier tamaño (GBs)
✅ **Progreso resistente**: Upload chunked con retry automático
✅ **No bloquea el servidor**: Backend solo genera URLs, no maneja bytes
✅ **Mejor rendimiento**: Upload directo a almacenamiento es mucho más rápido
✅ **Escalable**: Múltiples uploads simultáneos sin problema
✅ **Barra de progreso**: El navegador puede mostrar progreso real

## Implementación

### Backend: Ya implementado

He agregado el método `generate_presigned_upload_url()` en `BucketService`:

```python
def generate_presigned_upload_url(
    self, 
    object_name: str, 
    expiration: int = 3600,
    content_type: Optional[str] = None
) -> str:
    """
    Genera una URL presignada para upload directo desde navegador.
    La URL expira después de 'expiration' segundos (default: 1 hora).
    """
```

### Frontend: Cambios necesarios

#### 1. Nuevo endpoint para obtener URL presignada

Agregar en `backend/app/routers/task.py`:

```python
from pydantic import BaseModel

class PresignedUploadRequest(BaseModel):
    filename: str
    content_type: str

class PresignedUploadResponse(BaseModel):
    upload_url: str
    object_key: str
    expires_in: int

@router.post("/upload/presigned-url", response_model=PresignedUploadResponse)
async def get_presigned_upload_url(
    request: PresignedUploadRequest,
    bucket_service: BucketService = Depends(get_bucket_service)
):
    """
    Genera una URL presignada para que el cliente suba archivos directamente a MinIO.
    """
    import hashlib
    import time
    
    # Generar object key único
    file_hash = hashlib.sha256(f"{request.filename}{int(time.time())}".encode()).hexdigest()
    file_extension = os.path.splitext(request.filename)[1]
    object_key = f"uploads/{file_hash}{file_extension}"
    
    # Generar URL presignada (expira en 1 hora)
    upload_url = bucket_service.generate_presigned_upload_url(
        object_name=object_key,
        expiration=3600,
        content_type=request.content_type
    )
    
    return PresignedUploadResponse(
        upload_url=upload_url,
        object_key=object_key,
        expires_in=3600
    )
```

#### 2. Modificar endpoint de creación de tarea

```python
@router.post("", dependencies=[Depends(require_role("ROLE_ADMIN", "ROLE_OPERADOR"))])
async def create(
    name: str = Form(...),
    locality_id: int = Form(...),
    date: datetime = Form(...), 
    object_key: str = Form(...),  # ← Ya subido a MinIO
    service: TaskService = Depends(get_task_service),
):
    """
    Crea una tarea con un video ya subido a MinIO.
    El frontend debe primero:
    1. Obtener presigned URL con POST /task/upload/presigned-url
    2. Subir archivo directo a MinIO usando esa URL
    3. Llamar a este endpoint con el object_key
    """
    task_request = TaskCreateRequest(
        name=name,
        locality_id=locality_id,
        date=date
    )
    
    # Verificar que el objeto existe en MinIO
    try:
        bucket_service = get_bucket_service()
        bucket_service.s3_client.head_object(
            Bucket=bucket_service.BUCKET_NAME,
            Key=object_key
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="El archivo no fue encontrado en el almacenamiento"
        )
    
    # Obtener metadata del video desde MinIO
    video_url = f"task/temp/{object_key}"  # Será movido después
    task = service.create_from_object_key(task_request, object_key)
    
    return {"task": task}
```

#### 3. Frontend: Upload con progreso

Crear `frontend/src/lib/services/upload.ts`:

```typescript
export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export async function uploadVideoToMinio(
  file: File,
  onProgress?: (progress: UploadProgress) => void
): Promise<string> {
  // 1. Obtener URL presignada
  const response = await fetch('/api/task/upload/presigned-url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filename: file.name,
      content_type: file.type
    })
  });

  if (!response.ok) {
    throw new Error('Failed to get upload URL');
  }

  const { upload_url, object_key } = await response.json();

  // 2. Upload directo a MinIO con progreso
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    // Mostrar progreso
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress({
          loaded: e.loaded,
          total: e.total,
          percentage: Math.round((e.loaded / e.total) * 100)
        });
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        resolve(object_key);
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed'));
    });

    xhr.open('PUT', upload_url);
    xhr.setRequestHeader('Content-Type', file.type);
    xhr.send(file);
  });
}
```

#### 4. Modificar componente de creación de tarea

```svelte
<script lang="ts">
  import { uploadVideoToMinio } from '$lib/services/upload';
  
  let uploadProgress = 0;
  let isUploading = false;
  
  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    const formData = new FormData(event.target as HTMLFormElement);
    const videoFile = formData.get('video') as File;
    
    if (!videoFile) return;
    
    try {
      isUploading = true;
      
      // Upload directo a MinIO con progreso
      const objectKey = await uploadVideoToMinio(videoFile, (progress) => {
        uploadProgress = progress.percentage;
      });
      
      // Crear tarea con el object_key
      const response = await fetch('/api/task', {
        method: 'POST',
        body: new FormData({
          name: formData.get('name'),
          locality_id: formData.get('locality_id'),
          date: formData.get('date'),
          object_key: objectKey
        })
      });
      
      if (!response.ok) throw new Error('Failed to create task');
      
      // Redirigir o mostrar éxito
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      isUploading = false;
      uploadProgress = 0;
    }
  }
</script>

<form on:submit={handleSubmit}>
  <!-- Campos del formulario -->
  
  {#if isUploading}
    <div class="progress-bar">
      <div class="progress-fill" style="width: {uploadProgress}%">
        {uploadProgress}%
      </div>
    </div>
  {/if}
  
  <button type="submit" disabled={isUploading}>
    {isUploading ? 'Subiendo...' : 'Crear Tarea'}
  </button>
</form>
```

## Comparación de Enfoques

| Aspecto | Upload a través del Backend | Upload Directo a MinIO |
|---------|----------------------------|------------------------|
| **Tamaño máximo** | Limitado (100MB actual) | Ilimitado (GBs) |
| **Velocidad** | Lenta (2 saltos) | Rápida (1 salto) |
| **Memoria servidor** | Alta (carga archivo completo) | Mínima (solo genera URL) |
| **Progreso en UI** | Difícil | Fácil (nativo) |
| **Resilencia** | Baja (si falla, reintenta todo) | Alta (chunked, retry) |
| **Escalabilidad** | Baja | Alta |
| **Complejidad implementación** | Simple | Moderada |

## Recomendación Final

### Para Producción: **USAR UPLOAD DIRECTO**

Implementar presigned URLs es la solución correcta y estándar de la industria para manejar archivos grandes. Es lo que usan servicios como:
- YouTube (uploads directos a Google Cloud Storage)
- Dropbox (uploads directos a S3)
- AWS S3 Transfer Acceleration

### Para Testing Inmediato: **OK con 100MB**

La configuración actual de `BODY_SIZE_LIMIT: 104857600` es aceptable para:
- Desarrollo y pruebas con videos pequeños
- Demos con clips cortos
- Validación del flujo completo del sistema

Pero debes planear la migración a presigned URLs antes de producción.

## Próximos Pasos

1. ✅ **Implementado**: Método `generate_presigned_upload_url` en BucketService
2. ⏳ **Pendiente**: Nuevo endpoint `/task/upload/presigned-url` en backend
3. ⏳ **Pendiente**: Modificar endpoint `/task` para recibir `object_key` en lugar de archivo
4. ⏳ **Pendiente**: Implementar upload directo en frontend
5. ⏳ **Pendiente**: Agregar barra de progreso en UI
6. ⏳ **Opcional**: Implementar uploads multipart para archivos >5GB

## Referencias

- [AWS S3 Presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)
- [MinIO Presigned URLs](https://min.io/docs/minio/linux/developers/python/API.html#presigned_put_object)
- [SvelteKit Body Size Limit](https://kit.svelte.dev/docs/configuration#bodysizelimit)
