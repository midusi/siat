import os
import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext

from app.main import app
from app.db import SessionLocal
from app.models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

client = TestClient(app)


def setup_user(username: str = "testuser_auth", password: str = "secret", active: bool = True) -> User:
    db = SessionLocal()
    try:
        # cleanup existing
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            db.delete(existing)
            db.commit()
        user = User(
            username=username,
            password=pwd.hash(password),
            email=f"{username}@example.com",
            first_name="Test",
            last_name="User",
            role="ROLE_ADMIN",
            active=active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


def test_me_unauthenticated_returns_401():
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_login_wrong_password_returns_401():
    setup_user()
    r = client.post("/auth/login", json={"username": "testuser_auth", "password": "wrong"})
    assert r.status_code == 401


def test_login_success_and_me():
    setup_user()
    r = client.post("/auth/login", json={"username": "testuser_auth", "password": "secret"})
    assert r.status_code == 200
    assert "access_token" in r.json()

    # cookie should be set
    assert any(c.name == os.getenv("AUTH_COOKIE_NAME", "access_token") for c in r.cookies.jar)

    # call /auth/me with cookie
    r2 = client.get("/auth/me", cookies=r.cookies)
    assert r2.status_code == 200
    body = r2.json()
    assert body["username"] == "testuser_auth"


def test_inactive_user_gets_401_on_me():
    setup_user(active=False)
    # even if we login (should fail), ensure /auth/me is 401
    r_me = client.get("/auth/me")
    assert r_me.status_code == 401
