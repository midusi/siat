# routers/__init__.py
from .district import router as district_router 
from .example import router as example_router 

all_routers = [district_router, example_router]
