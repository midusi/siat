# services/user_service.py
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import logging

from app.crud import user as user_crud
from app.schemas.user import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
    AdminResetPasswordRequest,
    ChangePasswordRequest,
    UserProfileUpdateRequest,
)
from app.models import User
from app.config import BCRYPT_ROUNDS

logger = logging.getLogger("audit")

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=BCRYPT_ROUNDS)
        
    def create(self, user_request: UserCreateRequest) -> UserResponse:
        self._validate_passwords(user_request.password, user_request.confirm_password)
        existing_user = self.user_exists(user_request.username, user_request.email)
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ya existe un usuario con el mismo email o username")
        
        try:
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
            self.db.commit()
            self.db.refresh(user_obj)
            logger.info(f"user created id={user_obj.id} username={user_obj.username} role={user_obj.role}")
            return UserResponse.model_validate(user_obj)
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    def update(self, user_id: int, req: UserUpdateRequest) -> UserResponse:
        user = user_crud.find_one_by_fields(self.db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        # Email/username uniqueness check when email changes
        if req.email and req.email != user.email and self.user_exists(user.username, req.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya en uso")
        old_role = user.role
        # Apply changes
        if req.email is not None:
            user.email = req.email
        if req.first_name is not None:
            user.first_name = req.first_name
        if req.last_name is not None:
            user.last_name = req.last_name
        if req.role is not None:
            user.role = req.role
        self.db.commit()
        self.db.refresh(user)
        if req.role is not None and req.role != old_role:
            logger.info(f"user role changed id={user.id} from={old_role} to={req.role}")
        return UserResponse.model_validate(user)

    def get_list(self) -> list[UserResponse]:
        users = user_crud.find_by_fields(self.db)
        return [UserResponse.model_validate(u) for u in users]
    
    def disable(self, user_id: int) -> UserResponse:
        user = user_crud.find_one_by_fields(self.db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        user.active = False
        self.db.commit()
        self.db.refresh(user)
        logger.info(f"user disabled id={user.id}")
        return UserResponse.model_validate(user)
    
    def enable(self, user_id: int) -> UserResponse:
        user = user_crud.find_one_by_fields(self.db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        user.active = True
        self.db.commit()
        self.db.refresh(user)
        logger.info(f"user enabled id={user.id}")
        return UserResponse.model_validate(user)

    def delete(self, user_id: int) -> None:
        user = user_crud.find_one_by_fields(self.db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        try:
            self.db.delete(user)
            self.db.commit()
            logger.info(f"user deleted id={user.id} username={user.username}")
        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Admin: reset password
    def admin_reset_password(self, user_id: int, req: AdminResetPasswordRequest) -> None:
        if req.new_password != req.confirm_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Las contraseñas no coinciden")
        self._validate_policy(req.new_password)
        user = user_crud.find_one_by_fields(self.db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        user.password = self.hash_password(req.new_password)
        # invalidar tokens
        user.refresh_token_version = (user.refresh_token_version or 0) + 1
        self.db.commit()
        logger.info(f"user password reset by admin id={user.id}")

    # Self-service: change password
    def change_password(self, user_id: int, req: ChangePasswordRequest) -> None:
        if req.new_password != req.confirm_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Las contraseñas no coinciden")
        self._validate_policy(req.new_password)
        user = user_crud.find_one_by_fields(self.db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        if not self.verify_password(req.current_password, user.password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta")
        user.password = self.hash_password(req.new_password)
        # invalidar tokens
        user.refresh_token_version = (user.refresh_token_version or 0) + 1
        self.db.commit()
        logger.info(f"user changed own password id={user.id}")

    # Self-service: update profile
    def update_profile(self, user_id: int, req: UserProfileUpdateRequest) -> UserResponse:
        user = user_crud.find_one_by_fields(self.db, id=user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
        if req.email and req.email != user.email and self.user_exists(user.username, req.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya en uso")
        if req.first_name is not None:
            user.first_name = req.first_name
        if req.last_name is not None:
            user.last_name = req.last_name
        if req.email is not None:
            user.email = req.email
        self.db.commit()
        self.db.refresh(user)
        return UserResponse.model_validate(user)

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)
        
    def user_exists(self, username: str, email: str) -> bool:
        return user_crud.get_by_username_email(self.db, username, email) is not None

    def _validate_passwords(self, p1: str, p2: str):
        if p1 != p2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Las contraseñas no coinciden")
        self._validate_policy(p1)

    def _validate_policy(self, pwd: str):
        # Política básica: longitud mínima 6, al menos una letra y un número (ajustable)
        if len(pwd) < 6:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña debe tener al menos 6 caracteres")
        if not any(c.isalpha() for c in pwd) or not any(c.isdigit() for c in pwd):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La contraseña debe incluir letras y números")