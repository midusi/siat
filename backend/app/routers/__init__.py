# routers/__init__.py
from .district import router as district_router 
from .auth import router as auth_router 
from .admin import router as admin_router 
from .task import router as task_router 

all_routers = [
    district_router, 
    auth_router, 
    admin_router,
    task_router
]
