import jwt
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict

from app.config import SECRET_KEY, ALGORITHM, access_token_timedelta, refresh_token_timedelta

UTC = ZoneInfo("UTC")


def create_access_token(user: Dict[str, Any], version: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "role": user["role"],
        "type": "access",
        "ver": version,
        "iat": int(now.timestamp()),
        "exp": int((now + access_token_timedelta()).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user: Dict[str, Any], version: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user["id"]),
        "type": "refresh",
        "ver": version,
        "iat": int(now.timestamp()),
        "exp": int((now + refresh_token_timedelta()).timestamp()),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any] | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
