# routers/__init__.py
from .district import router as district_router 
from .auth import router as auth_router 
from .admin import router as admin_router 
from .example import router as example_router 

all_routers = [district_router, example_router, auth_router, admin_router]
