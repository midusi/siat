# from sqlmodel import SQLModel, Session, create_engine
# import os

# # 🔹 Cargar variables desde .env
# from dotenv import load_dotenv
# load_dotenv()

# # 🔹 Construir DATABASE_URL desde variables
# db_driver = os.getenv("DB_DRIVER")
# db_user = os.getenv("DB_USER")
# db_pass = os.getenv("DB_PASS")
# db_host = os.getenv("DB_HOST")
# db_port = os.getenv("DB_PORT", "5432")
# db_name = os.getenv("DB_NAME")

# DATABASE_URL = f"{db_driver}://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
# engine = create_engine(DATABASE_URL, echo=True)

# def get_session():
#     return Session(engine)

# database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastapi import Depends

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
# 🔹 Construir DATABASE_URL desde variables
db_driver = os.getenv("DB_DRIVER")
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")

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
