from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from app.routers import all_routers  # tu lista de routers ya definidos
from pydantic import BaseModel
import logging
from app.config import LOG_LEVEL, LOG_FILE
import os

# Definición del modelo para los polígonos (ejemplo)
class Punto(BaseModel):
    x: float
    y: float

class Poligono(BaseModel):
    via: str
    sentido: str
    vertices: List[Punto]

# Crear router específico para los polígonos
poligonos_router = APIRouter()

@poligonos_router.post("/guardar_poligonos")
async def guardar_poligonos(poligonos: List[Poligono]):
    print("Recibí polígonos:", poligonos)
    return {"mensaje": "Polígonos guardados", "cantidad": len(poligonos)}

# Logging básico
def _configure_logging():
    level = getattr(logging, (LOG_LEVEL or "INFO").upper(), logging.INFO)
    handlers = []
    if LOG_FILE:
        handlers.append(logging.FileHandler(LOG_FILE))
    else:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=level, handlers=handlers, format='%(asctime)s %(levelname)s %(name)s: %(message)s')

# Crear la app FastAPI
_configure_logging()
app = FastAPI(title="Traffic Analysis API")

# Configurar CORS
origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
origins = [o.strip() for o in origins_env.split(",")] if origins_env else [
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

# Incluir routers
app.include_router(poligonos_router)

for router in all_routers:
    app.include_router(router)
