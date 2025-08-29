import os
from fastapi.testclient import TestClient
from passlib.context import CryptContext

from app.main import app
from app.db import SessionLocal
from app.models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
client = TestClient(app)


def setup_user(username: str = "refresh_user", password: str = "secret") -> User:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            db.delete(existing)
            db.commit()
        user = User(
            username=username,
            password=pwd.hash(password),
            email=f"{username}@example.com",
            first_name="Ref",
            last_name="User",
            role="ROLE_ADMIN",
            active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def test_refresh_and_logout_flow():
    setup_user()
    # login
    r = client.post("/auth/login", json={"username": "refresh_user", "password": "secret"})
    assert r.status_code == 200
    cookies = r.cookies
    assert cookies.get(os.getenv("AUTH_COOKIE_NAME", "access_token"))
    assert cookies.get(os.getenv("AUTH_REFRESH_COOKIE_NAME", "refresh_token"))

    # call refresh
    r2 = client.post("/auth/refresh", cookies=cookies)
    assert r2.status_code == 200
    # should set new access and refresh
    assert r2.cookies.get(os.getenv("AUTH_COOKIE_NAME", "access_token"))
    assert r2.cookies.get(os.getenv("AUTH_REFRESH_COOKIE_NAME", "refresh_token"))

    # call logout with CSRF header
    r3 = client.post("/auth/logout", cookies=r2.cookies, headers={os.getenv("CSRF_HEADER_NAME", "X-CSRF-Token"): "1"})
    assert r3.status_code == 204

    # refresh again should fail (version bumped)
    r4 = client.post("/auth/refresh", cookies=r2.cookies)
    # Depending on version validation; here rotate always increments; expect 200 but with new tokens if we didn't block.
    # Since logout increments version, old refresh should be invalid logically; we expect 401
    assert r4.status_code in (401, 403)
