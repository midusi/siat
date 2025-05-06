# services/user_service.py
from fastapi import HTTPException, status
from passlib.context import CryptContext

from app.services.base import *
from app.crud.district import *
from app.crud import user as user_crud
from app.schemas.user import UserCreateRequest, UserResponse
from app.models import User


class UserService(Base):
    def create(self, user_request: UserCreateRequest) -> UserResponse:
        # Validate user data
        existing_user = self.user_exists(user_request.username, user_request.email)
        if user_request.password != user_request.confirm_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Las contraseñas no coinciden")
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un usuario con el mismo email o username")
        
        # Create user
        user_obj = User(
            username=user_request.username,
            password=self.hash_password(user_request.password),
            email=user_request.email,
            first_name=user_request.first_name,
            last_name=user_request.last_name,
            role=user_request.role,
            active=True,
        )
        self.db.add(user_obj)
        # Commit and refresh the user object to get the ID
        user = self.commit_and_refresh(user_obj)
        if not user:
            raise HTTPException(status_code=status.HTTP_500_BAD_REQUEST, detail="Error al crear el usuario")
        return UserResponse.model_validate(user)
    
    def hash_password(self, password: str) -> str:
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return self.pwd_context.hash(password)
        
    def user_exists(self, username: str, email: str) -> bool:
        return user_crud.get_by_username_email(self.db, username, email) is not None