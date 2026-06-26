# Guía de Testing: Upload Directo a MinIO

## Prerequisitos

Asegúrate de que:
1. ✅ Docker compose está corriendo (`docker-compose up`)
2. ✅ MinIO está accesible (puerto 9000)
3. ✅ Backend está corriendo (puerto 8000)
4. ✅ Frontend está corriendo (puerto 5173 o el que uses)

## Tests Básicos

### Test 1: Upload de archivo pequeño (< 10MB)

**Objetivo:** Verificar que el flujo básico funciona correctamente.

**Pasos:**
1. Ir a la página de crear tarea: `http://localhost:5173/tarea/crear`
2. Llenar el formulario con datos válidos
3. Seleccionar un video pequeño (< 10MB)
4. Hacer clic en "Crear Tarea"
5. Observar la barra de progreso

**Resultado esperado:**
- ✅ Progreso muestra de 0% a 100%
- ✅ Aparece mensaje "Creando tarea..."
- ✅ Redirige a página principal
- ✅ Tarea aparece en la lista

**Verificación en logs:**
```bash
# Backend logs (buscar en Docker o terminal)
Generated presigned URL for upload to 'traffic-analysis/uploads/...'
Objeto subido a 'traffic-analysis/task/{id}/...'
```

---

### Test 2: Upload de archivo mediano (50-100MB)

**Objetivo:** Verificar que no hay timeouts con archivos más grandes.

**Pasos:**
1. Repetir Test 1 con un video de ~100MB

**Resultado esperado:**
- ✅ Upload completa sin errores
- ✅ No hay timeout del navegador
- ✅ Progreso es fluido y actualiza constantemente

---

### Test 3: Upload de archivo grande (> 500MB)

**Objetivo:** Verificar escalabilidad y que el límite de 100MB fue efectivamente removido.

**Pasos:**
1. Repetir Test 1 con un video grande

**Resultado esperado:**
- ✅ Upload funciona sin límites
- ✅ Memoria del servidor backend NO crece significativamente
- ✅ Proceso completa exitosamente

**Verificar uso de memoria:**
```bash
# En otra terminal, monitorear Docker
docker stats
```

El contenedor del backend NO debe mostrar uso de memoria creciente durante el upload.

---

### Test 4: Verificar compatibilidad con método antiguo

**Objetivo:** Asegurar que el código antiguo sigue funcionando.

**Nota:** Este test requiere modificar temporalmente el frontend o usar una herramienta como curl/Postman.

**Usando curl:**
```bash
curl -X POST http://localhost:8000/api/task \
  -F "name=Test Tarea Old Method" \
  -F "locality_id=1" \
  -F "date=2024-01-01" \
  -F "file=@/path/to/video.mp4" \
  -H "Cookie: session=YOUR_SESSION_COOKIE"
```

**Resultado esperado:**
- ✅ Tarea se crea exitosamente
- ✅ Video se sube correctamente

---

## Tests de Casos de Error

### Test 5: Desconexión de red

**Objetivo:** Verificar manejo de errores de red.

**Pasos:**
1. Iniciar un upload de archivo mediano
2. Cuando el progreso esté en ~50%, desconectar wifi/ethernet
3. Esperar a que falle

**Resultado esperado:**
- ✅ Aparece mensaje de error: "Upload failed due to network error"
- ✅ No se crea la tarea
- ✅ Frontend vuelve a estado normal

---

### Test 6: Crear tarea sin subir archivo

**Objetivo:** Verificar validación de object_key.

**Usando curl:**
```bash
curl -X POST http://localhost:8000/api/task \
  -F "name=Test Invalid" \
  -F "locality_id=1" \
  -F "date=2024-01-01" \
  -F "object_key=uploads/nonexistent.mp4"
```

**Resultado esperado:**
- ✅ HTTP 400 Bad Request
- ✅ Mensaje: "El archivo no fue encontrado en el almacenamiento"

---

### Test 7: URL presignada expirada

**Objetivo:** Verificar que URLs presignadas expiran.

**Pasos:**
1. Obtener URL presignada con expiration=5 segundos (modificar código temporalmente)
2. Esperar 10 segundos
3. Intentar subir archivo con esa URL

**Resultado esperado:**
- ✅ MinIO rechaza el upload
- ✅ Error en frontend

---

## Tests de Verificación de Datos

### Test 8: Verificar ubicación del archivo en MinIO

**Objetivo:** Confirmar que el archivo se mueve correctamente.

**Pasos:**
1. Crear una tarea exitosamente
2. Acceder a MinIO UI: `http://localhost:9001`
3. Login con credenciales (minioadmin/minioadmin por defecto)
4. Navegar a bucket `traffic-analysis`

**Resultado esperado:**
- ✅ NO hay archivos en carpeta `uploads/` (fueron movidos)
- ✅ Archivo está en `task/{id}/` con nombre correcto
- ✅ Tamaño del archivo coincide con el original

---

### Test 9: Verificar metadata en Base de Datos

**Objetivo:** Confirmar que metadata se extrajo correctamente.

**Pasos:**
1. Crear una tarea
2. Consultar base de datos:
```sql
SELECT v.name, v.format, v.duration, v.fps, v.width, v.height, v.url
FROM video v
JOIN task t ON t.video_id = v.id
WHERE t.name = 'Tu Nombre de Tarea';
```

**Resultado esperado:**
- ✅ Todos los campos tienen valores válidos
- ✅ duration, fps, width, height son correctos
- ✅ url apunta a `task/{id}/...`

---

## Tests de Performance

### Test 10: Múltiples uploads simultáneos

**Objetivo:** Verificar que el servidor puede manejar múltiples uploads.

**Pasos:**
1. Abrir 3 tabs del navegador
2. En cada tab, iniciar upload de un archivo diferente simultáneamente
3. Observar progreso en cada tab

**Resultado esperado:**
- ✅ Todos los uploads progresan independientemente
- ✅ Servidor backend permanece estable
- ✅ Todas las tareas se crean exitosamente

---

## Debugging

### Ver logs del backend:
```bash
docker-compose logs -f backend
```

### Ver logs de MinIO:
```bash
docker-compose logs -f minio
```

### Verificar archivos en MinIO via CLI:
```bash
docker exec -it <minio-container> sh
mc ls local/traffic-analysis/
mc ls local/traffic-analysis/task/
mc ls local/traffic-analysis/uploads/
```

### Limpiar archivos huérfanos en uploads/:
```bash
# Si quedaron archivos por tests fallidos
docker exec -it <minio-container> sh
mc rm --recursive --force local/traffic-analysis/uploads/
```

---

## Checklist de Validación Final

Antes de considerar la implementación completa:

- [ ] Test 1: Upload pequeño ✅
- [ ] Test 2: Upload mediano ✅
- [ ] Test 3: Upload grande ✅
- [ ] Test 4: Compatibilidad ✅
- [ ] Test 5: Error de red ✅
- [ ] Test 6: Validación object_key ✅
- [ ] Test 8: Verificación en MinIO ✅
- [ ] Test 9: Metadata en BD ✅
- [ ] Test 10: Uploads simultáneos ✅
- [ ] Sin errores en logs ✅
- [ ] No hay memory leaks ✅

---

## Notas Adicionales

### Configuración de producción

Antes de ir a producción, considera:

1. **Aumentar expiration de URLs**: De 1 hora a 2-3 horas para uploads muy grandes
2. **Agregar rate limiting**: Limitar cantidad de solicitudes de presigned URLs por usuario
3. **Monitoreo**: Agregar métricas de uploads completados/fallidos
4. **Limpieza automática**: Cron job para limpiar archivos huérfanos en `uploads/`
5. **Validación de Content-Type**: Verificar que el archivo subido es realmente un video

### Troubleshooting Común

**Error: "Failed to get upload URL"**
- Verificar que el backend está corriendo
- Verificar autenticación (cookie de sesión)

**Error: "Upload failed with status 403"**
- Verificar configuración de CORS en MinIO
- Verificar permisos del bucket

**Upload se queda en 99% sin completar**
- Verificar que MinIO procesó el archivo
- Ver logs de MinIO para errores

**Tarea no aparece después de crear**
- Verificar logs del backend para errores de BD
- Verificar que el video se movió correctamente en MinIO
