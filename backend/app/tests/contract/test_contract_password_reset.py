import re

from app.tests.contract.support import PASSWORD, create_user, login

REQUEST_URL = "/auth/password/request"
PERFORM_URL = "/auth/password/perform"
NEW_PASSWORD = "Nueva456"


def request_reset(client, identifier="admin"):
    return client.post(REQUEST_URL, json={"identifier": identifier})


def perform_reset(client, token, new_password=NEW_PASSWORD, confirm_password=NEW_PASSWORD):
    return client.post(
        PERFORM_URL,
        json={"token": token, "new_password": new_password, "confirm_password": confirm_password},
    )


def issued_token(sent_emails) -> str:
    body = sent_emails[-1]["body"]
    return re.search(r"\n\n(\S+)\n", body).group(1)


# --- request ---------------------------------------------------------------

def test_request_for_known_user_is_204_and_sends_one_email(client, db_session, sent_emails):
    create_user(db_session)

    response = request_reset(client, "admin")

    assert response.status_code == 204
    assert response.content == b""
    assert len(sent_emails) == 1
    assert sent_emails[0]["to"] == "admin@example.com"
    assert sent_emails[0]["subject"] == "Recuperación de contraseña"
    assert "Usa este token para recuperar tu contraseña" in sent_emails[0]["body"]


def test_request_accepts_email_as_identifier(client, db_session, sent_emails):
    create_user(db_session)

    response = request_reset(client, "admin@example.com")

    assert response.status_code == 204
    assert len(sent_emails) == 1


def test_request_for_unknown_user_is_indistinguishable_and_sends_nothing(client, sent_emails):
    response = request_reset(client, "ghost")

    assert response.status_code == 204
    assert response.content == b""
    assert sent_emails == []


def test_request_without_identifier_is_422(client):
    assert client.post(REQUEST_URL, json={}).status_code == 422


# --- perform ---------------------------------------------------------------

def test_perform_with_valid_token_changes_the_password(client, db_session, sent_emails):
    create_user(db_session)
    request_reset(client)

    response = perform_reset(client, issued_token(sent_emails))

    assert response.status_code == 204
    assert response.content == b""
    assert login(client, password=NEW_PASSWORD).status_code == 200
    assert login(client, password=PASSWORD).status_code == 401


def test_perform_invalidates_sessions_issued_before_the_reset(client, db_session, sent_emails):
    create_user(db_session)
    old_access = login(client).json()["access_token"]
    request_reset(client)

    perform_reset(client, issued_token(sent_emails))

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {old_access}"})
    assert me.status_code == 401


def test_perform_with_invalid_token_is_400(client):
    response = perform_reset(client, "garbage")

    assert response.status_code == 400
    assert response.json() == {"detail": "Token inválido o expirado"}


def test_perform_checks_token_before_validating_passwords(client):
    response = perform_reset(client, "garbage", new_password="a", confirm_password="b")

    assert response.status_code == 400
    assert response.json() == {"detail": "Token inválido o expirado"}


def test_perform_with_mismatched_passwords_is_400_with_field(client, db_session, sent_emails):
    create_user(db_session)
    request_reset(client)

    response = perform_reset(client, issued_token(sent_emails), confirm_password="Otra789")

    assert response.status_code == 400
    assert response.json() == {"detail": "Las contraseñas no coinciden", "field": "confirm_password"}


def test_perform_with_weak_password_is_400_with_field(client, db_session, sent_emails):
    create_user(db_session)
    request_reset(client)

    response = perform_reset(client, issued_token(sent_emails), new_password="abc", confirm_password="abc")

    assert response.status_code == 400
    assert response.json() == {"detail": "La contraseña debe tener al menos 6 caracteres", "field": "password"}


def test_perform_with_missing_fields_is_422(client):
    assert client.post(PERFORM_URL, json={"token": "x"}).status_code == 422
