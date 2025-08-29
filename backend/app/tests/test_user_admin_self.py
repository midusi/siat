from fastapi.testclient import TestClient
from passlib.context import CryptContext

from app.main import app
from app.db import SessionLocal
from app.models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
client = TestClient(app)


def setup_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin_test").first()
        if admin:
            db.delete(admin)
            db.commit()
        admin = User(
            username="admin_test",
            password=pwd.hash("Admin123"),
            email="admin_test@example.com",
            first_name="Admin",
            last_name="Test",
            role="ROLE_ADMIN",
            active=True,
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()


def auth_cookies(username="admin_test", password="Admin123"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.cookies


def test_admin_user_crud_and_self_service():
    setup_admin()
    cookies = auth_cookies()

    # Create user
    create_body = {
        "username": "operador1",
        "password": "Operador123",
        "confirm_password": "Operador123",
        "email": "operador1@example.com",
        "first_name": "Op",
        "last_name": "Uno",
        "role": "ROLE_OPERADOR"
    }
    r_create = client.post("/admin/user-register", json=create_body, cookies=cookies)
    assert r_create.status_code == 200
    user_id = r_create.json()["user"]["id"]

    # List users
    r_list = client.get("/admin/user", cookies=cookies)
    assert r_list.status_code == 200

    # Update user
    r_upd = client.patch(f"/admin/user/{user_id}", json={"first_name": "Op2"}, cookies=cookies)
    assert r_upd.status_code == 200
    assert r_upd.json()["user"]["first_name"] == "Op2"

    # Disable
    r_dis = client.patch(f"/admin/user/{user_id}/disable", cookies=cookies)
    assert r_dis.status_code == 200
    assert r_dis.json()["user"]["active"] is True or r_dis.json()["user"]["active"] is False

    # Reset password
    r_reset = client.post(f"/admin/user/{user_id}/reset-password", json={"new_password": "NewPass123", "confirm_password": "NewPass123"}, cookies=cookies)
    assert r_reset.status_code == 204

    # Self-service: login as operador1 and change password
    r_login_user = client.post("/auth/login", json={"username": "operador1", "password": "NewPass123"})
    assert r_login_user.status_code == 200
    cookies_user = r_login_user.cookies

    r_change_pwd = client.post("/user/me/change-password", json={"current_password": "NewPass123", "new_password": "NewPass456", "confirm_password": "NewPass456"}, cookies=cookies_user)
    assert r_change_pwd.status_code == 204

    # Update profile
    r_prof = client.patch("/user/me", json={"first_name": "Oper", "last_name": "Dos"}, cookies=cookies_user)
    assert r_prof.status_code == 200
