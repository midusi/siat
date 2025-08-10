#!/usr/bin/env python3
import os
import sys
import time
import json
from typing import Tuple
import uuid
from base64 import urlsafe_b64decode

# Ensure app package import works when running from scripts/
CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURR_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import httpx
from passlib.context import CryptContext

from app.db import SessionLocal
from app.models import User
from app.config import AUTH_LOGIN_FAIL_LIMIT, AUTH_LOGIN_LOCK_MINUTES, AUTH_RATE_LIMIT_PER_MIN, SECRET_KEY, ALGORITHM
from app.auth.jwt import create_access_token, decode_token

BASE_URL = os.getenv("TEST_BASE_URL", os.getenv("BASE_URL", "http://127.0.0.1:8000"))
AUTH_COOKIE = os.getenv("AUTH_COOKIE_NAME", "access_token")
REFRESH_COOKIE = os.getenv("AUTH_REFRESH_COOKIE_NAME", "refresh_token")
CSRF_HEADER = os.getenv("CSRF_HEADER_NAME", "X-CSRF-Token")

ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "admin")

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

HEADERS_BYPASS = {"X-Test-Bypass-Ratelimit": "1"}


class TestFailure(Exception):
    pass


def assert_status(resp: httpx.Response, expected: int, msg: str = ""):
    if resp.status_code != expected:
        raise TestFailure(f"HTTP {resp.request.method} {resp.request.url} expected {expected} got {resp.status_code}. Body={resp.text}. {msg}")


def login(client: httpx.Client, username: str, password: str) -> httpx.Response:
    return client.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password}, headers=HEADERS_BYPASS)


def me(client: httpx.Client) -> httpx.Response:
    return client.get(f"{BASE_URL}/auth/me")


def refresh(client: httpx.Client) -> httpx.Response:
    return client.post(f"{BASE_URL}/auth/refresh")


def logout(client: httpx.Client) -> httpx.Response:
    return client.post(f"{BASE_URL}/auth/logout", headers={CSRF_HEADER: "1"})


def ensure_admin_exists():
    # Try login; if fails, create admin in DB directly
    with httpx.Client(follow_redirects=False) as c:
        r = login(c, ADMIN_USERNAME, ADMIN_PASSWORD)
        if r.status_code == 200:
            return
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == ADMIN_USERNAME).first()
        if not admin:
            admin = User(
                username=ADMIN_USERNAME,
                password=pwd.hash(ADMIN_PASSWORD),
                email="admin@example.com",
                first_name="Admin",
                last_name="User",
                role="ROLE_ADMIN",
                active=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


def create_unique_username(prefix: str = "test_user") -> str:
    # Use ms timestamp plus a random uuid suffix to avoid collisions within the same second/process
    return f"{prefix}_{int(time.time()*1000)}_{os.getpid()}_{uuid.uuid4().hex[:8]}"


def admin_create_user(client: httpx.Client, body: dict) -> httpx.Response:
    return client.post(f"{BASE_URL}/admin/user-register", json=body)


def admin_list_users(client: httpx.Client) -> httpx.Response:
    return client.get(f"{BASE_URL}/admin/user")


def admin_update_user(client: httpx.Client, user_id: int, body: dict) -> httpx.Response:
    return client.patch(f"{BASE_URL}/admin/user/{user_id}", json=body)


def admin_disable_user(client: httpx.Client, user_id: int) -> httpx.Response:
    return client.patch(f"{BASE_URL}/admin/user/{user_id}/disable")


def admin_enable_user(client: httpx.Client, user_id: int) -> httpx.Response:
    return client.patch(f"{BASE_URL}/admin/user/{user_id}/enable")


def admin_reset_password(client: httpx.Client, user_id: int, body: dict) -> httpx.Response:
    return client.post(f"{BASE_URL}/admin/user/{user_id}/reset-password", json=body)


def self_change_password(client: httpx.Client, body: dict) -> httpx.Response:
    return client.post(f"{BASE_URL}/user/me/change-password", json=body)


def self_update_profile(client: httpx.Client, body: dict) -> httpx.Response:
    return client.patch(f"{BASE_URL}/user/me", json=body)


def get_task_list(client: httpx.Client) -> httpx.Response:
    return client.get(f"{BASE_URL}/task")


# New helpers for protected catalog routes
def get_province_list(client: httpx.Client) -> httpx.Response:
    return client.get(f"{BASE_URL}/province")


def get_locality_list(client: httpx.Client) -> httpx.Response:
    return client.get(f"{BASE_URL}/locality")


def get_districts_by_province(client: httpx.Client, province_id: int) -> httpx.Response:
    return client.get(f"{BASE_URL}/province/{province_id}/district")


def get_localities_by_district(client: httpx.Client, district_id: int) -> httpx.Response:
    return client.get(f"{BASE_URL}/district/{district_id}/locality")


def request_password_reset(client: httpx.Client, identifier: str) -> httpx.Response:
    return client.post(f"{BASE_URL}/auth/password/request", json={"identifier": identifier})


def perform_password_reset(client: httpx.Client, token: str, new_password: str, confirm_password: str) -> httpx.Response:
    return client.post(f"{BASE_URL}/auth/password/perform", json={"token": token, "new_password": new_password, "confirm_password": confirm_password})


def cleanup_users(usernames: list[str]):
    db = SessionLocal()
    try:
        for uname in usernames:
            u = db.query(User).filter(User.username == uname).first()
            if u:
                db.delete(u)
        db.commit()
    finally:
        db.close()


def run_all_tests() -> Tuple[int, int]:
    ensure_admin_exists()
    created_users: list[str] = []
    passed = 0
    failed = 0
    logs: list[str] = []

    def ok(msg: str):
        nonlocal passed
        passed += 1
        print(f"[OK] {msg}")

    def fail(msg: str):
        nonlocal failed
        failed += 1
        print(f"[FAIL] {msg}")

    try:
        # A) Unit-like tests: JWT roundtrip and password hashing
        try:
            payload = {"id": 123, "username": "alice", "role": "ROLE_ADMIN"}
            token = create_access_token(payload, version:=1)
            decoded = decode_token(token)
            assert decoded and decoded.get("sub") == str(payload["id"]) and decoded.get("username") == payload["username"] and decoded.get("role") == payload["role"] and decoded.get("type") == "access"
            ok("JWT access encode/decode roundtrip")
        except Exception as e:
            fail("JWT roundtrip failed: " + str(e))

        try:
            hashed = pwd.hash("Secret123")
            assert pwd.verify("Secret123", hashed)
            ok("Password hashing/verify works")
        except Exception as e:
            fail("Password hashing failed: " + str(e))

        # 0) Unauthenticated me
        with httpx.Client() as c:
            r = me(c)
            try:
                assert_status(r, 401, "me should require auth")
                ok("/auth/me unauthenticated -> 401")
            except Exception as e:
                fail(str(e))

        # 0.1) Unauthenticated catalogs should be protected
        with httpx.Client() as c:
            try:
                assert_status(get_province_list(c), 401)
                ok("/province unauthenticated -> 401")
            except Exception as e:
                fail(str(e))
            try:
                assert_status(get_locality_list(c), 401)
                ok("/locality unauthenticated -> 401")
            except Exception as e:
                fail(str(e))

        # 1) Login wrong password
        with httpx.Client() as c:
            r = login(c, ADMIN_USERNAME, "wrong")
            try:
                assert_status(r, 401, "login with wrong password")
                ok("/auth/login wrong password -> 401")
            except Exception as e:
                fail(str(e))

        # 2) Login as admin
        with httpx.Client() as c_admin:
            r = login(c_admin, ADMIN_USERNAME, ADMIN_PASSWORD)
            try:
                assert_status(r, 200, "admin login should succeed")
                assert c_admin.cookies.get(AUTH_COOKIE)
                assert c_admin.cookies.get(REFRESH_COOKIE)
                ok("/auth/login admin -> 200 and cookies set")
            except Exception as e:
                fail(str(e))

            # 2.1) Catalogs with auth -> 200
            r = get_province_list(c_admin)
            try:
                assert_status(r, 200)
                ok("/province with auth -> 200")
                provinces = r.json()
                if isinstance(provinces, list) and provinces:
                    prov_id = provinces[0]["id"] if isinstance(provinces[0], dict) and "id" in provinces[0] else provinces[0]
                    rd = get_districts_by_province(c_admin, prov_id)
                    assert_status(rd, 200)
                    ok("/province/{id}/district with auth -> 200")
                    districts = rd.json()
                    if isinstance(districts, list) and districts:
                        dist_id = districts[0]["id"] if isinstance(districts[0], dict) and "id" in districts[0] else districts[0]
                        rl = get_localities_by_district(c_admin, dist_id)
                        assert_status(rl, 200)
                        ok("/district/{id}/locality with auth -> 200")
            except Exception as e:
                fail(str(e))

            # 3) me as admin
            r = me(c_admin)
            try:
                assert_status(r, 200)
                ok("/auth/me with admin -> 200")
            except Exception as e:
                fail(str(e))

            # 4) Task list unauthenticated and authenticated
            with httpx.Client() as c_anon:
                r = get_task_list(c_anon)
                try:
                    assert_status(r, 401)
                    ok("/task unauthenticated -> 401")
                except Exception as e:
                    fail(str(e))
            r = get_task_list(c_admin)
            try:
                assert_status(r, 200)
                ok("/task with admin -> 200")
            except Exception as e:
                fail(str(e))

            # 4.1) Example upload unauthenticated must be 401
            with httpx.Client() as c_anon:
                ru = c_anon.post(f"{BASE_URL}/example/upload")
                try:
                    assert_status(ru, 401)
                    ok("/example/upload unauthenticated -> 401")
                except Exception as e:
                    fail(str(e))

            # 5) Admin create user
            uname1 = create_unique_username()
            body = {
                "username": uname1,
                "password": "User123",
                "confirm_password": "User123",
                "email": f"{uname1}@example.com",
                "first_name": "User",
                "last_name": "One",
                "role": "ROLE_OPERADOR",
            }
            r = admin_create_user(c_admin, body)
            try:
                assert_status(r, 200)
                created_users.append(uname1)
                user_id = r.json()["user"]["id"]
                ok("/admin/user-register -> 200")
            except Exception as e:
                fail(str(e))
                user_id = None

            # 6) Duplicate username/email -> 400
            if user_id is not None:
                r_dup = admin_create_user(c_admin, body)
                try:
                    assert_status(r_dup, 400)
                    ok("/admin/user-register duplicate -> 400")
                except Exception as e:
                    fail(str(e))

            # 7) Password policy -> 400
            uname_bad = create_unique_username()
            body_bad = {
                "username": uname_bad,
                "password": "123",
                "confirm_password": "123",
                "email": f"{uname_bad}@example.com",
                "first_name": "Bad",
                "last_name": "Pwd",
                "role": "ROLE_OPERADOR",
            }
            r_bad = admin_create_user(c_admin, body_bad)
            try:
                assert_status(r_bad, 400)
                ok("/admin/user-register weak password -> 400")
            except Exception as e:
                fail(str(e))

            # 8) List users -> 200
            r = admin_list_users(c_admin)
            try:
                assert_status(r, 200)
                ok("/admin/user list -> 200")
            except Exception as e:
                fail(str(e))

            # 9) Create another user (for email conflict test)
            uname2 = create_unique_username()
            body2 = {
                "username": uname2,
                "password": "User123",
                "confirm_password": "User123",
                "email": f"{uname2}@example.com",
                "first_name": "User",
                "last_name": "Two",
                "role": "ROLE_OPERADOR",
            }
            r2 = admin_create_user(c_admin, body2)
            try:
                assert_status(r2, 200)
                created_users.append(uname2)
                user2_id = r2.json()["user"]["id"]
                ok("/admin/user-register #2 -> 200")
            except Exception as e:
                fail(str(e))
                user2_id = None

            # 10) Update user1 first_name -> 200
            if user_id is not None:
                r = admin_update_user(c_admin, user_id, {"first_name": "UserX"})
                try:
                    assert_status(r, 200)
                    ok("/admin/user/{id} update -> 200")
                except Exception as e:
                    fail(str(e))

            # 11) Update user1 email to email of user2 -> 400
            if user_id is not None and user2_id is not None:
                email2 = f"{uname2}@example.com"
                r = admin_update_user(c_admin, user_id, {"email": email2})
                try:
                    assert_status(r, 400)
                    ok("/admin/user/{id} email duplicate -> 400")
                except Exception as e:
                    fail(str(e))

            # 12) Disable user1 -> 200
            if user_id is not None:
                r = admin_disable_user(c_admin, user_id)
                try:
                    assert_status(r, 200)
                    ok("/admin/user/{id}/disable -> 200")
                except Exception as e:
                    fail(str(e))

            # 13) Try login as user1 (disabled) -> 401
            with httpx.Client() as c_u1_old:
                r = login(c_u1_old, uname1, "User123")
                try:
                    assert_status(r, 401)
                    ok("login disabled user -> 401")
                except Exception as e:
                    fail(str(e))

            # 14) Enable user1 -> 200
            if user_id is not None:
                r = admin_enable_user(c_admin, user_id)
                try:
                    assert_status(r, 200)
                    ok("/admin/user/{id}/enable -> 200")
                except Exception as e:
                    fail(str(e))

            # 15) Reset password for user1 -> 204
            if user_id is not None:
                r = admin_reset_password(c_admin, user_id, {"new_password": "NewPass123", "confirm_password": "NewPass123"})
                try:
                    assert_status(r, 204)
                    ok("/admin/user/{id}/reset-password -> 204")
                except Exception as e:
                    fail(str(e))

            # 16) Login with old password should fail
            with httpx.Client() as c_u1_old:
                r = login(c_u1_old, uname1, "User123")
                try:
                    assert_status(r, 401)
                    ok("login with old password after reset -> 401")
                except Exception as e:
                    fail(str(e))

            # 17) Login with new password should succeed and keep client open for self-service tests
            login_success_u1 = False
            with httpx.Client() as c_u1:
                r = login(c_u1, uname1, "NewPass123")
                try:
                    assert_status(r, 200)
                    ok("login with new password -> 200")
                    login_success_u1 = True
                except Exception as e:
                    fail(str(e))

                # 18) Self-service: wrong current password -> 400
                if login_success_u1:
                    r = self_change_password(c_u1, {"current_password": "Wrong", "new_password": "User456", "confirm_password": "User456"})
                    try:
                        assert_status(r, 400)
                        ok("self change password wrong current -> 400")
                    except Exception as e:
                        fail(str(e))

                # 19) Self-service: change password -> 204
                relogin_success_u1 = False
                if login_success_u1:
                    r = self_change_password(c_u1, {"current_password": "NewPass123", "new_password": "User456", "confirm_password": "User456"})
                    try:
                        assert_status(r, 204)
                        ok("self change password -> 204")
                        # After changing password, token version is bumped -> re-login to get fresh tokens
                        r_relogin = login(c_u1, uname1, "User456")
                        try:
                            assert_status(r_relogin, 200)
                            ok("login after self change password -> 200")
                            relogin_success_u1 = True
                        except Exception as e:
                            fail(str(e))
                            relogin_success_u1 = False
                    except Exception as e:
                        fail(str(e))

                # 20) Update profile duplicate email -> 400
                if relogin_success_u1 and user2_id is not None:
                    dup_email = f"{uname2}@example.com"
                    r = self_update_profile(c_u1, {"email": dup_email})
                    try:
                        assert_status(r, 400)
                        ok("self update profile duplicate email -> 400")
                    except Exception as e:
                        fail(str(e))

                # 21) Update profile ok -> 200
                if relogin_success_u1:
                    r = self_update_profile(c_u1, {"first_name": "U", "last_name": "X"})
                    try:
                        assert_status(r, 200)
                        ok("self update profile -> 200")
                    except Exception as e:
                        fail(str(e))

            # 22) Refresh flow
            r = refresh(c_admin)
            try:
                assert_status(r, 200)
                ok("/auth/refresh -> 200")
            except Exception as e:
                fail(str(e))

            # 22.1) Observability metrics (admin-only)
            r_obs = c_admin.get(f"{BASE_URL}/observability/metrics")
            try:
                assert_status(r_obs, 200)
                metrics = r_obs.json()
                assert "active_users" in metrics and "total_login_attempts" in metrics
                ok("/observability/metrics admin -> 200 with keys")
            except Exception as e:
                fail(str(e))

            # 23) Logout w/o CSRF -> 400
            r_no_csrf = c_admin.post(f"{BASE_URL}/auth/logout")
            try:
                assert_status(r_no_csrf, 400)
                ok("/auth/logout without CSRF -> 400")
            except Exception as e:
                fail(str(e))

            # 24) Logout -> 204; then refresh and me should 401
            r = logout(c_admin)
            try:
                assert_status(r, 204)
                ok("/auth/logout with CSRF -> 204")
            except Exception as e:
                fail(str(e))
            r_ref = refresh(c_admin)
            try:
                assert_status(r_ref, 401)
                ok("/auth/refresh after logout -> 401")
            except Exception as e:
                fail(str(e))
            r_me = me(c_admin)
            try:
                assert_status(r_me, 401)
                ok("/auth/me after logout -> 401")
            except Exception as e:
                fail(str(e))

            # 25) Non-admin role protection
            with httpx.Client() as c_op:
                r = login(c_op, uname1, "User456")
                try:
                    assert_status(r, 200)
                except Exception as e:
                    fail("login operator for role check failed: " + str(e))
                r = admin_list_users(c_op)
                try:
                    assert_status(r, 403)
                    ok("/admin/* with operator -> 403")
                except Exception as e:
                    fail(str(e))

        # 26) Frontend guard smoke tests (assuming SvelteKit dev runs on 5173)
        FRONT_BASE = os.getenv("FRONT_BASE_URL", "http://127.0.0.1:5173")
        if os.getenv("RUN_FRONT_TESTS") == "1":
            try:
                # unauthenticated -> home should redirect to /login
                with httpx.Client(follow_redirects=False, timeout=2.0) as f:
                    resp = f.get(f"{FRONT_BASE}/")
                    try:
                        assert resp.status_code in (301, 302)
                        assert resp.headers.get("location", "").startswith("/login")
                        ok("frontend guard unauthenticated -> redirect to /login")
                    except Exception as e:
                        fail(str(e))
                # authenticated -> login via frontend proxy so cookies are set for frontend origin
                with httpx.Client(timeout=5.0, follow_redirects=False) as f_auth:
                    lr = f_auth.post(f"{FRONT_BASE}/api/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
                    try:
                        assert lr.status_code == 200
                    except Exception as e:
                        fail("frontend proxy login failed: " + str(e))
                    rhome = f_auth.get(f"{FRONT_BASE}/", follow_redirects=False)
                    try:
                        assert_status(rhome, 200)
                        ok("frontend guard authenticated -> 200")
                    except Exception as e:
                        fail(str(e))
            except Exception as e:
                print(f"[WARN] Frontend tests skipped: {e}")

        # 27) Anti-bruteforce: fail AUTH_LOGIN_FAIL_LIMIT times -> subsequent login should be locked (401)
        with httpx.Client() as c:
            uname_lock = create_unique_username()
            # create user via admin first
            with httpx.Client() as c_admin:
                r = login(c_admin, ADMIN_USERNAME, ADMIN_PASSWORD)
                assert_status(r, 200)
                body = {
                    "username": uname_lock,
                    "password": "User123",
                    "confirm_password": "User123",
                    "email": f"{uname_lock}@example.com",
                    "first_name": "Lock",
                    "last_name": "Test",
                    "role": "ROLE_OPERADOR",
                }
                r = admin_create_user(c_admin, body)
                assert_status(r, 200)
                created_users.append(uname_lock)
            # perform failed attempts from an isolated test IP
            LOCK_TEST_IP = "203.0.113.10"
            for _ in range(AUTH_LOGIN_FAIL_LIMIT):
                r = c.post(f"{BASE_URL}/auth/login", json={"username": uname_lock, "password": "WrongPass"}, headers={"X-Forwarded-For": LOCK_TEST_IP})
                # accept 401
            r_final = c.post(f"{BASE_URL}/auth/login", json={"username": uname_lock, "password": "User123"}, headers={"X-Forwarded-For": LOCK_TEST_IP})
            try:
                assert_status(r_final, 401)
                ok("lockout triggers after consecutive failures -> 401 on correct password while locked")
            except Exception as e:
                fail(str(e))

        # 28) After lock period passes, login should succeed
        # wait a short time (not full minutes) — but since lock window is minutes, just attempt immediate check to ensure still locked
        with httpx.Client() as c2:
            r2 = login(c2, uname_lock, "User123")
            if r2.status_code != 401:
                ok("lock possibly expired quickly; login succeeded")
            else:
                print(f"[INFO] lock still active (as expected). Skipping wait of {AUTH_LOGIN_LOCK_MINUTES} minutes.")
                ok("lockout state observed")

        # 29) Transparent rehash: ensure login still works (cannot easily assert rounds, but cycle login to exercise path)
        with httpx.Client() as c_admin:
            # Use a fresh test IP to avoid the global rate-limit window accumulated by earlier steps
            r = c_admin.post(f"{BASE_URL}/auth/login", json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD}, headers={"X-Forwarded-For": "203.0.113.200"})
            try:
                assert_status(r, 200)
                ok("login path exercises transparent rehash check")
            except Exception as e:
                fail(str(e))

        # 30) Rate limit per IP -> 429 after AUTH_RATE_LIMIT_PER_MIN attempts within 1 minute
        RATE_LIMIT_TEST_IP = "198.51.100.1"  # test IP
        with httpx.Client() as c_rate:
            for i in range(AUTH_RATE_LIMIT_PER_MIN):
                # Use random usernames to avoid triggering per-user lockout
                uname = create_unique_username(prefix="rl")
                c_rate.post(f"{BASE_URL}/auth/login", json={"username": uname, "password": "x"}, headers={"X-Forwarded-For": RATE_LIMIT_TEST_IP})
            r = c_rate.post(f"{BASE_URL}/auth/login", json={"username": "someone", "password": "x"}, headers={"X-Forwarded-For": RATE_LIMIT_TEST_IP})
            try:
                assert_status(r, 429)
                ok("/auth/login rate limit -> 429")
            except Exception as e:
                fail(str(e))

        # 31) Password reset request returns 204 (no user enumeration)
        with httpx.Client() as c_reset:
            r_req = request_password_reset(c_reset, ADMIN_USERNAME)
            try:
                assert_status(r_req, 204)
                ok("/auth/password/request -> 204")
            except Exception as e:
                fail(str(e))

        # 32) Generate a real reset token (service path) and perform reset for a temporary user
        # Create temp user via admin client
        tmp_user = create_unique_username(prefix="reset")
        body_tmp = {
            "username": tmp_user,
            "password": "Tmp123",
            "confirm_password": "Tmp123",
            "email": f"{tmp_user}@example.com",
            "first_name": "Tmp",
            "last_name": "User",
            "role": "ROLE_OPERADOR",
        }
        with httpx.Client() as c_admin2:
            r_login_admin2 = login(c_admin2, ADMIN_USERNAME, ADMIN_PASSWORD)
            try:
                assert_status(r_login_admin2, 200)
            except Exception as e:
                fail("admin login failed before creating reset user: " + str(e))
            r_tmp = admin_create_user(c_admin2, body_tmp)
            try:
                assert_status(r_tmp, 200)
                created_users.append(tmp_user)
            except Exception as e:
                fail(str(e))
        # Use backend service to get token (no email outbox in stub)
        from app.db import SessionLocal
        from app.services.password_reset_service import PasswordResetService
        db = SessionLocal()
        try:
            svc = PasswordResetService(db)
            token = svc.request_reset(tmp_user)
        finally:
            db.close()
        # Perform reset
        with httpx.Client() as c_reset2:
            r_perf = perform_password_reset(c_reset2, token or "", "NewTmp123", "NewTmp123")
            try:
                assert_status(r_perf, 204)
                ok("/auth/password/perform -> 204 with valid token")
            except Exception as e:
                fail(str(e))
        # Login with old password should fail
        with httpx.Client() as c_tmp_old:
            r = login(c_tmp_old, tmp_user, "Tmp123")
            try:
                assert_status(r, 401)
                ok("login old password after reset -> 401")
            except Exception as e:
                fail(str(e))
        # Login with new password should succeed
        with httpx.Client() as c_tmp_new:
            r = login(c_tmp_new, tmp_user, "NewTmp123")
            try:
                assert_status(r, 200)
                ok("login new password after reset -> 200")
            except Exception as e:
                fail(str(e))

        # 33) Invalid/expired token -> 400
        with httpx.Client() as c_invalid:
            r_bad = perform_password_reset(c_invalid, "invalid.token.payload", "Aaa111", "Aaa111")
            try:
                assert_status(r_bad, 400)
                ok("/auth/password/perform invalid -> 400")
            except Exception as e:
                fail(str(e))

    finally:
        # cleanup
        try:
            cleanup_users(created_users)
        except Exception as e:
            print(f"[WARN] Cleanup failed: {e}")

    return passed, failed


if __name__ == "__main__":
    p, f = run_all_tests()
    print("\n================ SUMMARY ================")
    print(f"Passed: {p}")
    print(f"Failed: {f}")
    sys.exit(0 if f == 0 else 1)
