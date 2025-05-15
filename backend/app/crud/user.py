# crud/user.py
from sqlalchemy.orm import sessionmaker
from app.models import User

def get_by_username_email(db: sessionmaker, username: str, email: str) -> list[User]:
    return db.query(User).filter((User.username == username) | (User.email == email)).first()

def find_by_fields(db: sessionmaker, **filters) -> list[User] | None:
    return db.query(User).filter_by(**filters).all()

def find_one_by_fields(db: sessionmaker, **filters) -> list[User] | None:
    return db.query(User).filter_by(**filters).first()