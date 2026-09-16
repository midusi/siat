# crud/user.py
from sqlalchemy.orm import Session
from app.models import User

def get_by_username_email(db: Session, username: str, email: str) -> User | None:
    return db.query(User).filter((User.username == username) | (User.email == email)).first()

def find_by_fields(db: Session, **filters) -> list[User]:
    return db.query(User).filter_by(**filters).all()

def find_one_by_fields(db: Session, **filters) -> User | None:
    return db.query(User).filter_by(**filters).first()
