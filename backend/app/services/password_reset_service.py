from __future__ import annotations
import hmac
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import SECRET_KEY, RESET_TOKEN_EXPIRES_MIN
from app.ports.uow import UnitOfWork
from app.services.user_service import UserService

UTC = timezone.utc


class PasswordResetService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.user_service = UserService(uow)

    def _sign(self, data: str) -> str:
        digest = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode()

    def _make_token(self, user_id: int, email: str, iat: datetime) -> str:
        exp = iat + timedelta(minutes=RESET_TOKEN_EXPIRES_MIN)
        payload = f"uid={user_id}&email={email}&iat={int(iat.timestamp())}&exp={int(exp.timestamp())}"
        sig = self._sign(payload)
        return base64.urlsafe_b64encode(f"{payload}&sig={sig}".encode()).decode()

    def _parse_and_verify(self, token: str) -> Optional[dict]:
        try:
            raw = base64.urlsafe_b64decode(token.encode()).decode()
            parts: dict[str, str] = {}
            for kv in raw.split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    parts[k] = v
            uid = int(parts.get("uid", "0"))
            email = parts.get("email")
            iat = int(parts.get("iat", "0"))
            exp = int(parts.get("exp", "0"))
            sig = parts.get("sig", "")
            if not uid or not email or not iat or not exp or not sig:
                return None
            payload = f"uid={uid}&email={email}&iat={iat}&exp={exp}"
            if not hmac.compare_digest(sig, self._sign(payload)):
                return None
            now = datetime.now(UTC).timestamp()
            if now > exp:
                return None
            return {"uid": uid, "email": email, "iat": iat, "exp": exp}
        except Exception:
            return None

    def request_reset(self, identifier: str) -> Optional[str]:
        token, _email = self.request_reset_with_email(identifier)
        return token

    def request_reset_with_email(self, identifier: str) -> tuple[Optional[str], Optional[str]]:
        user = self.uow.users.find_by_identifier(identifier)
        if not user:
            return None, None
        iat = datetime.now(UTC)
        token = self._make_token(user.id, user.email, iat)
        return token, user.email

    def perform_reset(self, token: str, new_password: str, confirm_password: str) -> bool:
        data = self._parse_and_verify(token)
        if not data:
            return False
        user = self.uow.users.get(data["uid"])
        if not user or user.email != data["email"]:
            return False
        self.user_service._validate_passwords(new_password, confirm_password)
        user.password = self.user_service.hash_password(new_password)
        user.refresh_token_version = (user.refresh_token_version or 0) + 1
        self.uow.commit()
        return True
