# routers/__init__.py
from .district import router as district_router 
from .auth import router as auth_router 
from .admin import router as admin_router 
from .task import router as task_router
from .locality import router as locality_router 
from .province import router as province_router
from .example import router as example_router 
from .user_self import router as user_router
from .password_reset import router as password_reset_router
from .observability import router as observability_router

all_routers = [
    district_router, 
    auth_router, 
    admin_router,
    task_router,
    locality_router,
    province_router,
    example_router,
    user_router,
    password_reset_router,
    observability_router,
]
