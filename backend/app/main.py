from fastapi import FastAPI
from app.routers import all_routers
from app.auth.middleware import AuthMiddleware

app = FastAPI()

app.add_middleware(AuthMiddleware)

# Include all routers from the routers package
for router in all_routers:
    app.include_router(router)