# crud/district.py
from sqlalchemy.orm import Session
from app.models import User

def get_active_by_username(db: Session, username: str) -> list[User]:
    return db.query(User).filter(User.username == username, User.active == True).first()

def get_by_username_email(db: Session, username: str, email: str) -> list[User]:
    return db.query(User).filter((User.username == username) | (User.email == email)).first()
