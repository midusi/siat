from __future__ import annotations
from collections import deque
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from typing import Deque, Dict
from app.config import AUTH_RATE_LIMIT_PER_MIN

# Simple in-memory sliding window limiter per client IP for /auth/login
# Structure: { ip: deque[timestamps] }
_windows: Dict[str, Deque[datetime]] = {}
_WINDOW = timedelta(minutes=1)


def _now() -> datetime:
    return datetime.utcnow()


def _client_ip(request: Request) -> str:
    # Best-effort client IP detection; prefer X-Forwarded-For if behind proxy
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        # may contain multiple, take first
        return fwd.split(",")[0].strip()
    client = request.client
    return client.host if client else "unknown"


async def rate_limit_login(request: Request) -> None:
    # Test bypass
    if request.headers.get("x-test-bypass-ratelimit") == "1":
        return
    ip = _client_ip(request)
    dq = _windows.get(ip)
    if dq is None:
        dq = deque()
        _windows[ip] = dq
    now = _now()
    # drop entries older than window
    while dq and (now - dq[0]) > _WINDOW:
        dq.popleft()
    if len(dq) >= AUTH_RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts. Try again later.")
    dq.append(now)
