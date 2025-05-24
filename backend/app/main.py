from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from app.auth.middleware import AuthMiddleware
from app.routers import all_routers  # tu lista de routers ya definidos
from pydantic import BaseModel

# Definición del modelo para los polígonos (ejemplo)
class Poligono(BaseModel):
    vertices: List[List[float]]  # por ejemplo [[x1, y1], [x2, y2], ...]

# Crear router específico para los polígonos
poligonos_router = APIRouter()

@poligonos_router.post("/guardar_poligonos")
async def guardar_poligonos(poligonos: List[Poligono]):
    # Aquí la lógica para guardar los polígonos, ej:
    print("Recibí polígonos:", poligonos)
    return {"mensaje": "Polígonos guardados", "cantidad": len(poligonos)}

# Crear la app FastAPI
app = FastAPI()

# Configurar CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de autenticación
app.add_middleware(AuthMiddleware)

# Incluir routers
app.include_router(poligonos_router)

for router in all_routers:
    app.include_router(router)
