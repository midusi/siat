from fastapi import FastAPI
from app.routers import all_routers

app = FastAPI()

# Include all routers from the routers package
for router in all_routers:
    app.include_router(router)