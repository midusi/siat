from app import config
from app.tests.contract.support import (
    BYPASS_RATE_LIMIT,
    CSRF_HEADERS,
    PASSWORD,
    bearer,
    cookie_header,
    create_user,
    login,
    session_cookies,
    set_cookie_attributes,
)

INVALID_CREDENTIALS = {"detail": "Credenciales inválidas"}


def assert_session_cookies_set(response):
    cookies = set_cookie_attributes(response)

    access = cookies[config.COOKIE_NAME]
    assert access["httponly"] is True
    assert access["max-age"] == "3600"
    assert access["path"] == config.COOKIE_PATH
    assert access["samesite"].lower() == config.COOKIE_SAMESITE.lower()
    assert ("secure" in access) is config.COOKIE_SECURE
    assert ("domain" in access) is bool(config.COOKIE_DOMAIN)

    refresh = cookies[config.REFRESH_COOKIE_NAME]
    assert refresh["httponly"] is True
    assert refresh["max-age"] == str(60 * 60 * 24 * 7)
    assert refresh["path"] == config.REFRESH_COOKIE_PATH
    assert refresh["samesite"].lower() == config.REFRESH_COOKIE_SAMESITE.lower()
    assert ("secure" in refresh) is config.REFRESH_COOKIE_SECURE
    assert ("domain" in refresh) is bool(config.REFRESH_COOKIE_DOMAIN)


def assert_no_cookie_headers(response):
    # Comportamiento actual: logout llama a response.delete_cookie() pero devuelve un
    # Response nuevo, así que el cliente nunca recibe el borrado. Es un bug latente que el
    # refactor debe conservar (corregirlo cambia el contrato).
    assert response.headers.get_list("set-cookie") == []


# --- login -----------------------------------------------------------------

def test_login_success_returns_only_access_token_and_sets_both_cookies(client, db_session):
    create_user(db_session)

    response = login(client)

    assert response.status_code == 200
    assert set(response.json()) == {"access_token"}
    assert response.json()["access_token"] == response.cookies.get(config.COOKIE_NAME)
    assert_session_cookies_set(response)


def test_login_unknown_user_is_401_with_generic_detail(client):
    response = login(client, "ghost")

    assert response.status_code == 401
    assert response.json() == INVALID_CREDENTIALS
    assert "set-cookie" not in response.headers


def test_login_wrong_password_is_401_with_generic_detail(client, db_session):
    create_user(db_session)

    response = login(client, password="Wrong123")

    assert response.status_code == 401
    assert response.json() == INVALID_CREDENTIALS


def test_login_inactive_user_is_401_with_generic_detail(client, db_session):
    create_user(db_session, active=False)

    response = login(client)

    assert response.status_code == 401
    assert response.json() == INVALID_CREDENTIALS


def test_login_without_password_is_422(client):
    response = client.post("/auth/login", json={"username": "admin"}, headers=BYPASS_RATE_LIMIT)

    assert response.status_code == 422


# --- refresh ---------------------------------------------------------------

def test_refresh_without_cookie_is_401(client):
    response = client.post("/auth/refresh")

    assert response.status_code == 401
    assert response.json() == {"detail": "No hay refresh token"}


def test_refresh_with_garbage_token_is_401(client):
    response = client.post("/auth/refresh", headers=cookie_header(**{config.REFRESH_COOKIE_NAME: "garbage"}))

    assert response.status_code == 401
    assert response.json() == {"detail": "Refresh token inválido"}


def test_refresh_with_access_token_in_refresh_cookie_is_401(client, db_session):
    create_user(db_session)
    access = session_cookies(login(client))[config.COOKIE_NAME]

    response = client.post("/auth/refresh", headers=cookie_header(**{config.REFRESH_COOKIE_NAME: access}))

    assert response.status_code == 401
    assert response.json() == {"detail": "Refresh token inválido"}


def test_refresh_success_rotates_tokens_and_sets_both_cookies(client, db_session):
    create_user(db_session)
    first = session_cookies(login(client))

    response = client.post("/auth/refresh", headers=cookie_header(**{config.REFRESH_COOKIE_NAME: first[config.REFRESH_COOKIE_NAME]}))

    assert response.status_code == 200
    assert set(response.json()) == {"access_token"}
    assert_session_cookies_set(response)
    assert response.cookies.get(config.REFRESH_COOKIE_NAME) != first[config.REFRESH_COOKIE_NAME]


def test_refresh_with_already_rotated_token_is_401(client, db_session):
    create_user(db_session)
    first = session_cookies(login(client))
    headers = cookie_header(**{config.REFRESH_COOKIE_NAME: first[config.REFRESH_COOKIE_NAME]})
    assert client.post("/auth/refresh", headers=headers).status_code == 200
    client.cookies.clear()

    response = client.post("/auth/refresh", headers=headers)

    assert response.status_code == 401
    assert response.json() == {"detail": "Refresh inválido o expirado"}


def test_refresh_for_inactive_user_is_401(client, db_session):
    user = create_user(db_session)
    refresh = session_cookies(login(client))[config.REFRESH_COOKIE_NAME]
    user.active = False
    db_session.commit()

    response = client.post("/auth/refresh", headers=cookie_header(**{config.REFRESH_COOKIE_NAME: refresh}))

    assert response.status_code == 401
    assert response.json() == {"detail": "Refresh inválido o expirado"}


# --- logout ----------------------------------------------------------------

def test_logout_without_csrf_header_is_400(client):
    response = client.post("/auth/logout")

    assert response.status_code == 400
    assert response.json() == {"detail": "CSRF token faltante"}


def test_logout_without_session_is_204_and_sends_no_cookie_headers(client):
    response = client.post("/auth/logout", headers=CSRF_HEADERS)

    assert response.status_code == 204
    assert response.content == b""
    assert_no_cookie_headers(response)


def test_logout_with_access_cookie_invalidates_issued_tokens(client, db_session):
    create_user(db_session)
    tokens = session_cookies(login(client))

    response = client.post(
        "/auth/logout",
        headers={**CSRF_HEADERS, **cookie_header(**{config.COOKIE_NAME: tokens[config.COOKIE_NAME]})},
    )

    assert response.status_code == 204
    assert response.content == b""
    assert_no_cookie_headers(response)

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens[config.COOKIE_NAME]}"})
    assert me.status_code == 401
    assert me.json() == {"detail": "Token inválido (versión)"}

    refresh = client.post("/auth/refresh", headers=cookie_header(**{config.REFRESH_COOKIE_NAME: tokens[config.REFRESH_COOKIE_NAME]}))
    assert refresh.status_code == 401
    assert refresh.json() == {"detail": "Refresh inválido o expirado"}


def test_logout_falls_back_to_refresh_cookie_when_there_is_no_access_cookie(client, db_session):
    create_user(db_session)
    refresh = session_cookies(login(client))[config.REFRESH_COOKIE_NAME]
    headers = {**CSRF_HEADERS, **cookie_header(**{config.REFRESH_COOKIE_NAME: refresh})}

    response = client.post("/auth/logout", headers=headers)

    assert response.status_code == 204
    again = client.post("/auth/refresh", headers=cookie_header(**{config.REFRESH_COOKIE_NAME: refresh}))
    assert again.status_code == 401


# --- me --------------------------------------------------------------------

def test_me_without_credentials_is_401(client):
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "No autenticado"}


def test_me_with_invalid_token_is_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Token inválido o expirado"}


def test_me_returns_user_without_password(client, db_session):
    user = create_user(db_session)

    response = client.get("/auth/me", headers=bearer(client))

    assert response.status_code == 200
    assert response.json() == {
        "id": user.id,
        "username": "admin",
        "email": "admin@example.com",
        "role": "ROLE_ADMIN",
        "first_name": "Test",
        "last_name": "User",
        "active": True,
    }
