# db.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Depends

from app import config
DATABASE_URL = config.db_url()
print(f"Backend using database URL: {DATABASE_URL}")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Esta función será inyectada con Depends()
def get_db_session():   
    db = SessionLocal()
    try:
        yield db  # ← esto es clave para que FastAPI maneje bien el cierre
    finally:
        db.close()
