# db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Depends

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
# 🔹 Construir DATABASE_URL desde variables
db_driver = os.getenv("POSTGRES_DRIVER")
db_user = os.getenv("POSTGRES_USER")
db_pass = os.getenv("POSTGRES_PASS")
db_host = os.getenv("POSTGRES_HOST")
db_port = os.getenv("POSTGRES_PORT")
db_name = os.getenv("POSTGRES_NAME")

DATABASE_URL = f"{db_driver}://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
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
