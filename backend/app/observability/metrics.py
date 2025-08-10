from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.models import User

# Simple in-memory counters (process-local)
_total_login_attempts: int = 0
_failed_login_attempts: int = 0
_successful_logins: int = 0


def inc_login_attempt() -> None:
    global _total_login_attempts
    _total_login_attempts += 1


def inc_login_failed() -> None:
    global _failed_login_attempts
    _failed_login_attempts += 1


def inc_login_success() -> None:
    global _successful_logins
    _successful_logins += 1


def get_counters() -> Dict[str, int]:
    return {
        "total_login_attempts": _total_login_attempts,
        "failed_login_attempts": _failed_login_attempts,
        "successful_logins": _successful_logins,
    }


def snapshot(db: Session) -> Dict[str, Any]:
    active_users = db.query(User).filter(User.active == True).count()
    data: Dict[str, Any] = get_counters().copy()
    data["active_users"] = active_users
    return data
