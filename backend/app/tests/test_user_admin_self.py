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


def delete_user_if_exists(username):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def test_admin_user_crud_and_self_service():
    setup_admin()
    delete_user_if_exists("operador1")
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
    assert r_dis.json()["user"]["active"] is False

    # A disabled user cannot log in
    r_login_disabled = client.post("/auth/login", json={"username": "operador1", "password": "Operador123"})
    assert r_login_disabled.status_code == 401

    # Enable
    r_en = client.patch(f"/admin/user/{user_id}/enable", cookies=cookies)
    assert r_en.status_code == 200
    assert r_en.json()["user"]["active"] is True

    # Reset password
    r_reset = client.post(f"/admin/user/{user_id}/reset-password", json={"new_password": "NewPass123", "confirm_password": "NewPass123"}, cookies=cookies)
    assert r_reset.status_code == 204

    # Self-service: login as operador1 and change password
    r_login_user = client.post("/auth/login", json={"username": "operador1", "password": "NewPass123"})
    assert r_login_user.status_code == 200
    cookies_user = r_login_user.cookies

    r_change_pwd = client.post("/user/me/change-password", json={"current_password": "NewPass123", "new_password": "NewPass456", "confirm_password": "NewPass456"}, cookies=cookies_user)
    assert r_change_pwd.status_code == 204

    # Changing the password invalidates the existing session
    r_stale = client.patch("/user/me", json={"first_name": "Oper"}, cookies=cookies_user)
    assert r_stale.status_code == 401

    # Log in again with the new password and update profile
    r_relogin = client.post("/auth/login", json={"username": "operador1", "password": "NewPass456"})
    assert r_relogin.status_code == 200
    r_prof = client.patch("/user/me", json={"first_name": "Oper", "last_name": "Dos"}, cookies=r_relogin.cookies)
    assert r_prof.status_code == 200
    assert r_prof.json()["first_name"] == "Oper"


def test_admin_user_conflicts_report_the_failing_field():
    setup_admin()
    delete_user_if_exists("conflict_a")
    delete_user_if_exists("conflict_b")
    cookies = auth_cookies()

    def body(username, email):
        return {
            "username": username,
            "password": "Operador123",
            "confirm_password": "Operador123",
            "email": email,
            "first_name": "Con",
            "last_name": "Flicto",
            "role": "ROLE_OPERADOR",
        }

    r_a = client.post("/admin/user-register", json=body("conflict_a", "conflict_a@example.com"), cookies=cookies)
    assert r_a.status_code == 200
    r_b = client.post("/admin/user-register", json=body("conflict_b", "conflict_b@example.com"), cookies=cookies)
    assert r_b.status_code == 200
    id_a = r_a.json()["user"]["id"]
    id_b = r_b.json()["user"]["id"]

    try:
        # Duplicate username / email on create point at the offending field
        r_dup_user = client.post("/admin/user-register", json=body("conflict_a", "otro@example.com"), cookies=cookies)
        assert r_dup_user.status_code == 400
        assert r_dup_user.json()["field"] == "username"

        r_dup_mail = client.post("/admin/user-register", json=body("conflict_c", "conflict_a@example.com"), cookies=cookies)
        assert r_dup_mail.status_code == 400
        assert r_dup_mail.json()["field"] == "email"

        # Changing to an email that belongs to someone else is rejected on the email field
        r_taken = client.patch(f"/admin/user/{id_b}", json={"email": "conflict_a@example.com"}, cookies=cookies)
        assert r_taken.status_code == 400
        assert r_taken.json()["field"] == "email"

        # Changing to a free email works, and resending the current one is not a conflict
        r_free = client.patch(f"/admin/user/{id_b}", json={"email": "conflict_b2@example.com"}, cookies=cookies)
        assert r_free.status_code == 200
        assert r_free.json()["user"]["email"] == "conflict_b2@example.com"
        r_same = client.patch(f"/admin/user/{id_b}", json={"email": "conflict_b2@example.com"}, cookies=cookies)
        assert r_same.status_code == 200

        # Password problems are reported on their own fields and leave the profile untouched
        r_pwd = client.patch(f"/admin/user/{id_a}", json={"first_name": "Cambiado", "password": "abc", "confirm_password": "abc"}, cookies=cookies)
        assert r_pwd.status_code == 400
        assert r_pwd.json()["field"] == "password"
        r_mismatch = client.patch(f"/admin/user/{id_a}", json={"password": "Abc12345", "confirm_password": "Abc12346"}, cookies=cookies)
        assert r_mismatch.status_code == 400
        assert r_mismatch.json()["field"] == "confirm_password"
        users = client.get("/admin/user", cookies=cookies).json()["users"]
        assert next(u for u in users if u["id"] == id_a)["first_name"] == "Con"
    finally:
        delete_user_if_exists("conflict_a")
        delete_user_if_exists("conflict_b")
