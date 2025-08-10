# services/district_service.py
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from datetime import datetime, timedelta
import logging

from app.crud.district import *
from app.crud import user as user_crud
from app.auth.jwt import create_access_token, create_refresh_token
from app.config import BCRYPT_ROUNDS, AUTH_LOGIN_FAIL_LIMIT, AUTH_LOGIN_LOCK_MINUTES
from app.observability.metrics import inc_login_attempt, inc_login_failed, inc_login_success

logger = logging.getLogger("auth")

# In-memory trackers for failed attempts and locks (simple, per-process)
_failed_attempts: dict[str, dict] = {}
# structure: { key: { count: int, locked_until: datetime | None, last_fail: datetime } }

def _attempt_key(username: str) -> str:
    return username.lower().strip()

class AuthService:
    def __init__(self, db: sessionmaker):
        self.db = db
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
            # lock expired -> reset
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

    def login(self, username: str, password: str):
        inc_login_attempt()
        if self._is_locked(username):
            logger.warning(f"login attempt while locked user={username}")
            inc_login_failed()
            return None
        user = user_crud.find_one_by_fields(self.db, username=username)
        if not user or not user.active:
            self._register_failure(username)
            logger.info(f"login failed user={username} reason=not_found_or_inactive")
            inc_login_failed()
            return None
        if not self.verify_password(password, user.password):
            self._register_failure(username)
            logger.info(f"login failed user={username} reason=bad_password")
            inc_login_failed()
            return None
        # transparent rehash if needed (e.g., rounds changed)
        if self.pwd_context.needs_update(user.password):
            try:
                user.password = self.pwd_context.hash(password)
                self.db.commit()
            except Exception:
                self.db.rollback()
        self._register_success(username)
        ver = user.refresh_token_version or 0
        payload = {"id": user.id, "username": user.username, "role": user.role}
        access = create_access_token(payload, ver)
        refresh = create_refresh_token(payload, ver)
        logger.info(f"login success user={username}")
        inc_login_success()
        return access, refresh, user

    def refresh(self, user_id: int, token_version: int):
        user = user_crud.find_one_by_fields(self.db, id=user_id)
        if not user or not user.active:
            return None
        current_ver = user.refresh_token_version or 0
        if current_ver != (token_version or 0):
            return None
        # rotate
        user.refresh_token_version = current_ver + 1
        self.db.commit()
        self.db.refresh(user)
        ver = user.refresh_token_version
        payload = {"id": user.id, "username": user.username, "role": user.role}
        access = create_access_token(payload, ver)
        refresh = create_refresh_token(payload, ver)
        logger.info(f"refresh success user_id={user_id}")
        return access, refresh, user

    def logout(self, user_id: int):
        user = user_crud.find_one_by_fields(self.db, id=user_id)
        if not user:
            return False
        user.refresh_token_version = (user.refresh_token_version or 0) + 1
        self.db.commit()
        logger.info(f"logout user_id={user_id}")
        return True

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)