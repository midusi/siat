from passlib.context import CryptContext
import logging

from app.schemas.user import (
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
    AdminResetPasswordRequest,
    ChangePasswordRequest,
    UserProfileUpdateRequest,
)
from app.domain.entities import User
from app.config import BCRYPT_ROUNDS
from app.domain.exceptions import NotFoundError, ValidationError, InternalError
from app.ports.uow import UnitOfWork

logger = logging.getLogger("audit")


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=BCRYPT_ROUNDS)

    def create(self, user_request: UserCreateRequest) -> UserResponse:
        self._validate_passwords(user_request.password, user_request.confirm_password)
        existing_user = self.user_exists(user_request.username, user_request.email)
        if existing_user:
            raise ValidationError("Ya existe un usuario con el mismo email o username")

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
            self.uow.users.add(user_obj)
            self.uow.commit()
            self.uow.refresh(user_obj)
            logger.info(f"user created id={user_obj.id} username={user_obj.username} role={user_obj.role}")
            return UserResponse.model_validate(user_obj)
        except Exception as e:
            self.uow.rollback()
            raise InternalError(str(e))

    def update(self, user_id: int, req: UserUpdateRequest) -> UserResponse:
        user = self.uow.users.get(user_id)
        if not user:
            raise NotFoundError("Usuario no encontrado")
        if req.email and req.email != user.email and self.user_exists(user.username, req.email):
            raise ValidationError("Email ya en uso")
        old_role = user.role
        if req.email is not None:
            user.email = req.email
        if req.first_name is not None:
            user.first_name = req.first_name
        if req.last_name is not None:
            user.last_name = req.last_name
        if req.role is not None:
            user.role = req.role
        self.uow.commit()
        self.uow.refresh(user)
        if req.role is not None and req.role != old_role:
            logger.info(f"user role changed id={user.id} from={old_role} to={req.role}")
        return UserResponse.model_validate(user)

    def get_list(self) -> list[UserResponse]:
        users = self.uow.users.list_all()
        return [UserResponse.model_validate(u) for u in users]

    def disable(self, user_id: int) -> UserResponse:
        user = self._require(user_id)
        user.active = False
        self.uow.commit()
        self.uow.refresh(user)
        logger.info(f"user disabled id={user.id}")
        return UserResponse.model_validate(user)

    def enable(self, user_id: int) -> UserResponse:
        user = self._require(user_id)
        user.active = True
        self.uow.commit()
        self.uow.refresh(user)
        logger.info(f"user enabled id={user.id}")
        return UserResponse.model_validate(user)

    def delete(self, user_id: int) -> None:
        user = self._require(user_id)
        try:
            self.uow.users.delete(user)
            self.uow.commit()
            logger.info(f"user deleted id={user.id} username={user.username}")
        except Exception as e:
            self.uow.rollback()
            raise InternalError(str(e))

    def admin_reset_password(self, user_id: int, req: AdminResetPasswordRequest) -> None:
        if req.new_password != req.confirm_password:
            raise ValidationError("Las contraseñas no coinciden")
        self._validate_policy(req.new_password)
        user = self._require(user_id)
        user.password = self.hash_password(req.new_password)
        user.refresh_token_version = (user.refresh_token_version or 0) + 1
        self.uow.commit()
        logger.info(f"user password reset by admin id={user.id}")

    def change_password(self, user_id: int, req: ChangePasswordRequest) -> None:
        if req.new_password != req.confirm_password:
            raise ValidationError("Las contraseñas no coinciden")
        self._validate_policy(req.new_password)
        user = self._require(user_id)
        if not self.verify_password(req.current_password, user.password):
            raise ValidationError("Contraseña actual incorrecta")
        user.password = self.hash_password(req.new_password)
        user.refresh_token_version = (user.refresh_token_version or 0) + 1
        self.uow.commit()
        logger.info(f"user changed own password id={user.id}")

    def update_profile(self, user_id: int, req: UserProfileUpdateRequest) -> UserResponse:
        user = self._require(user_id)
        if req.email and req.email != user.email and self.user_exists(user.username, req.email):
            raise ValidationError("Email ya en uso")
        if req.first_name is not None:
            user.first_name = req.first_name
        if req.last_name is not None:
            user.last_name = req.last_name
        if req.email is not None:
            user.email = req.email
        self.uow.commit()
        self.uow.refresh(user)
        return UserResponse.model_validate(user)

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def user_exists(self, username: str, email: str) -> bool:
        return self.uow.users.get_by_username_or_email(username, email) is not None

    def _require(self, user_id: int) -> User:
        user = self.uow.users.get(user_id)
        if not user:
            raise NotFoundError("Usuario no encontrado")
        return user

    def _validate_passwords(self, p1: str, p2: str):
        if p1 != p2:
            raise ValidationError("Las contraseñas no coinciden")
        self._validate_policy(p1)

    def _validate_policy(self, pwd: str):
        if len(pwd) < 6:
            raise ValidationError("La contraseña debe tener al menos 6 caracteres")
        if not any(c.isalpha() for c in pwd) or not any(c.isdigit() for c in pwd):
            raise ValidationError("La contraseña debe incluir letras y números")
