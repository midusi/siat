# crud/user.py
from sqlalchemy.orm import Session
from app.models import User

def get_by_username_or_email(db: Session, username: str, email: str) -> User | None:
    return db.query(User).filter((User.username == username) | (User.email == email)).first()

def list_all(db: Session, **filters) -> list[User]:
    return db.query(User).filter_by(**filters).all()

def get(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()

def get_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()

def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()
