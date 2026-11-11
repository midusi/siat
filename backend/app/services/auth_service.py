from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import NamedTuple
import logging

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.config import BCRYPT_ROUNDS, AUTH_LOGIN_FAIL_LIMIT, AUTH_LOGIN_LOCK_MINUTES
from app.domain.entities import User
from app.domain.exceptions import UnauthorizedError
from app.observability.metrics import inc_login_attempt, inc_login_failed, inc_login_success
from app.ports.uow import UnitOfWork

logger = logging.getLogger("auth")
audit = logging.getLogger("audit")

_failed_attempts: dict[str, dict] = {}


def _attempt_key(username: str) -> str:
    return username.lower().strip()


class AuthSession(NamedTuple):
    access_token: str
    refresh_token: str
    user: User


class AuthService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=BCRYPT_ROUNDS)

    def _is_locked(self, username: str) -> bool:
        k = _attempt_key(username)
        info = _failed_attempts.get(k)
        if not info:
            return False
        until = info.get("locked_until")
        if until and datetime.utcnow() < until:
            return True
        if until and datetime.utcnow() >= until:
            _failed_attempts.pop(k, None)
            return False
        return False

    def _register_failure(self, username: str):
        k = _attempt_key(username)
        info = _failed_attempts.get(k) or {"count": 0, "locked_until": None, "last_fail": None}
        info["count"] += 1
        info["last_fail"] = datetime.utcnow()
        if info["count"] >= AUTH_LOGIN_FAIL_LIMIT:
            info["locked_until"] = datetime.utcnow() + timedelta(minutes=AUTH_LOGIN_LOCK_MINUTES)
            logger.warning(f"login lockout for user={k} until {info['locked_until']}")
        _failed_attempts[k] = info

    def _register_success(self, username: str):
        k = _attempt_key(username)
        if k in _failed_attempts:
            _failed_attempts.pop(k, None)

    def _login_failed(self, username: str) -> UnauthorizedError:
        inc_login_failed()
        audit.info(f"login failed username={username}")
        return UnauthorizedError("Credenciales inválidas")

    def login(self, username: str, password: str) -> AuthSession:
        inc_login_attempt()
        if self._is_locked(username):
            logger.warning(f"login attempt while locked user={username}")
            raise self._login_failed(username)
        user = self.uow.users.get_by_username(username)
        if not user or not user.active:
            self._register_failure(username)
            logger.info(f"login failed user={username} reason=not_found_or_inactive")
            raise self._login_failed(username)
        if not self.verify_password(password, user.password):
            self._register_failure(username)
            logger.info(f"login failed user={username} reason=bad_password")
            raise self._login_failed(username)
        if self.pwd_context.needs_update(user.password):
            try:
                user.password = self.pwd_context.hash(password)
                self.uow.commit()
            except Exception:
                self.uow.rollback()
        self._register_success(username)
        ver = user.refresh_token_version or 0
        payload = {"id": user.id, "username": user.username, "role": user.role}
        access = create_access_token(payload, ver)
        refresh = create_refresh_token(payload, ver)
        logger.info(f"login success user={username}")
        audit.info(f"login success user_id={user.id} username={user.username}")
        inc_login_success()
        return AuthSession(access, refresh, user)

    def refresh_from_token(self, raw_refresh_token: str | None) -> AuthSession:
        if not raw_refresh_token:
            raise UnauthorizedError("No hay refresh token")
        payload = decode_token(raw_refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise UnauthorizedError("Refresh token inválido")
        return self.refresh(int(payload.get("sub")), int(payload.get("ver", 0)))

    def refresh(self, user_id: int, token_version: int) -> AuthSession:
        user = self.uow.users.get(user_id)
        if not user or not user.active:
            raise UnauthorizedError("Refresh inválido o expirado")
        current_ver = user.refresh_token_version or 0
        if current_ver != (token_version or 0):
            raise UnauthorizedError("Refresh inválido o expirado")
        user.refresh_token_version = current_ver + 1
        self.uow.commit()
        self.uow.refresh(user)
        ver = user.refresh_token_version
        payload = {"id": user.id, "username": user.username, "role": user.role}
        access = create_access_token(payload, ver)
        refresh = create_refresh_token(payload, ver)
        logger.info(f"refresh success user_id={user_id}")
        return AuthSession(access, refresh, user)

    def logout_from_tokens(self, access_token: str | None, refresh_token: str | None) -> None:
        user_id = self._user_id_from_token(access_token, "access")
        if user_id is None:
            user_id = self._user_id_from_token(refresh_token, "refresh")
        if user_id is not None:
            self.logout(user_id)
            audit.info(f"logout user_id={user_id}")

    @staticmethod
    def _user_id_from_token(token: str | None, expected_type: str) -> int | None:
        if not token:
            return None
        payload = decode_token(token)
        if payload and payload.get("type") == expected_type:
            return int(payload.get("sub"))
        return None

    def logout(self, user_id: int):
        user = self.uow.users.get(user_id)
        if not user:
            return False
        user.refresh_token_version = (user.refresh_token_version or 0) + 1
        self.uow.commit()
        logger.info(f"logout user_id={user_id}")
        return True

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)
