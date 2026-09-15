import os
from fastapi import APIRouter, Depends, HTTPException
from app.ports.storage import ObjectStorage
from app.services.dependencies import get_object_storage
from app.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/example", tags=["example"], dependencies=[Depends(get_current_user)])

@router.post("/upload", dependencies=[Depends(require_role("ROLE_ADMIN", "ROLE_OPERADOR"))])
def upload(
        storage: ObjectStorage = Depends(get_object_storage)
    ):
    file_path = os.path.join("..", "videos/video_03", "transition_counts.json")
    object_name = "transition_counts.json"

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Archivo no encontrado en '{file_path}'. "
                   f"Por favor, asegúrate que la ruta relativa es correcta desde el directorio de trabajo actual: {os.getcwd()}"
        )

    try:
        with open(file_path, "rb") as f:
            storage.upload(f, object_name=object_name)
        return {"message": f"Se inició con éxito la subida de {file_path} como {object_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir el archivo: {e}")
