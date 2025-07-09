# services/district_service.py
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from app.crud.district import *
from app.crud import user as user_crud
from app.auth.jwt import create_token

class AuthService:
    def __init__(self, db: sessionmaker):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
    def login(self, username: str, password: str):
        user = user_crud.find_one_by_fields(self.db, username=username)
        if not user:
            return None
        if not self.verify_password(password, user.password):
            return None
        user = {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        }
        return create_token(user)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)