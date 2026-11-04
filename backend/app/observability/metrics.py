from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any

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
