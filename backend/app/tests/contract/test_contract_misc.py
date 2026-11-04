import pytest

from app.tests.contract.support import PASSWORD, bearer, create_user, login, seed_task

NEW_PASSWORD = "Nueva456"

USER_PAYLOAD = {
    "username": "nuevo",
    "password": PASSWORD,
    "confirm_password": PASSWORD,
    "email": "nuevo@example.com",
    "role": "ROLE_OPERADOR",
    "first_name": "Nuevo",
    "last_name": "Usuario",
}


@pytest.fixture
def admin(client, db_session):
    create_user(db_session, "admin", "ROLE_ADMIN")
    return bearer(client, "admin")


@pytest.fixture
def operator(client, db_session):
    create_user(db_session, "operator", "ROLE_OPERADOR")
    return bearer(client, "operator")


# --- health y notificaciones ----------------------------------------------

def test_health_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_internal_notify_is_public_and_acknowledges(client):
    response = client.post("/internal/notify", json={"task_id": 1, "status": "RUNNING", "progress": 10})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_internal_notify_validates_body(client):
    assert client.post("/internal/notify", json={"status": "RUNNING"}).status_code == 422


# --- catálogos -------------------------------------------------------------

@pytest.mark.parametrize("url", ["/province", "/province/1/district", "/district/1/locality", "/locality"])
def test_catalog_endpoints_require_authentication(client, url):
    response = client.get(url)

    assert response.status_code == 401
    assert response.json() == {"detail": "No autenticado"}


def test_catalog_endpoints_return_seeded_data(client, db_session, operator):
    seed_task(db_session)

    assert client.get("/province", headers=operator).json() == [{"id": 1, "name": "Buenos Aires"}]
    assert client.get("/province/1/district", headers=operator).json() == [{"id": 1, "name": "La Plata"}]
    assert client.get("/district/1/locality", headers=operator).json() == [
        {"id": 1, "name": "Centro", "district_id": 1}
    ]
    assert client.get("/locality", headers=operator).json() == [
        {"id": 1, "name": "Centro", "district_id": 1}
    ]


def test_catalog_endpoints_return_empty_lists_for_unknown_parents(client, operator):
    assert client.get("/province/99/district", headers=operator).json() == []
    assert client.get("/district/99/locality", headers=operator).json() == []


# --- administración de usuarios -------------------------------------------

@pytest.mark.parametrize("method, url", [
    ("get", "/admin/user"),
    ("post", "/admin/user-register"),
    ("patch", "/admin/user/1"),
    ("patch", "/admin/user/1/disable"),
    ("patch", "/admin/user/1/enable"),
    ("post", "/admin/user/1/reset-password"),
    ("delete", "/admin/user/1"),
    ("get", "/observability/metrics"),
])
def test_admin_endpoints_reject_non_admins(client, operator, method, url):
    response = getattr(client, method)(url, headers=operator)

    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}


def test_admin_creates_lists_updates_and_toggles_users(client, admin):
    created = client.post("/admin/user-register", json=USER_PAYLOAD, headers=admin)
    assert created.status_code == 200
    user = created.json()["user"]
    assert set(created.json()) == {"user"}
    assert user["username"] == "nuevo" and "password" not in user

    listed = client.get("/admin/user", headers=admin)
    assert listed.status_code == 200
    assert {u["username"] for u in listed.json()["users"]} == {"admin", "nuevo"}

    updated = client.patch(f"/admin/user/{user['id']}", json={"first_name": "Otro"}, headers=admin)
    assert updated.status_code == 200
    assert updated.json()["user"]["first_name"] == "Otro"

    disabled = client.patch(f"/admin/user/{user['id']}/disable", headers=admin)
    assert disabled.json()["user"]["active"] is False
    enabled = client.patch(f"/admin/user/{user['id']}/enable", headers=admin)
    assert enabled.json()["user"]["active"] is True


def test_admin_register_rejects_duplicates_with_field(client, admin):
    client.post("/admin/user-register", json=USER_PAYLOAD, headers=admin)

    response = client.post("/admin/user-register", json=USER_PAYLOAD, headers=admin)

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Ya existe un usuario con ese nombre de usuario",
        "field": "username",
    }


def test_admin_reset_password_and_delete_return_204_with_empty_body(client, admin):
    user_id = client.post("/admin/user-register", json=USER_PAYLOAD, headers=admin).json()["user"]["id"]

    reset = client.post(
        f"/admin/user/{user_id}/reset-password",
        json={"new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
        headers=admin,
    )
    assert reset.status_code == 204
    assert reset.content == b""
    assert login(client, "nuevo", NEW_PASSWORD).status_code == 200

    deleted = client.delete(f"/admin/user/{user_id}", headers=admin)
    assert deleted.status_code == 204
    assert deleted.content == b""


def test_admin_operations_on_missing_user_are_404(client, admin):
    response = client.patch("/admin/user/999/disable", headers=admin)

    assert response.status_code == 404


# --- perfil propio ---------------------------------------------------------

def test_user_me_requires_authentication(client):
    assert client.get("/user/me").status_code == 401


def test_user_me_and_profile_update(client, operator):
    me = client.get("/user/me", headers=operator)
    assert me.status_code == 200
    assert me.json()["username"] == "operator"

    updated = client.patch("/user/me", json={"first_name": "Cambiado"}, headers=operator)
    assert updated.status_code == 200
    assert updated.json()["first_name"] == "Cambiado"
    assert set(updated.json()) == {"id", "username", "email", "role", "first_name", "last_name", "active"}


def test_change_password_returns_204_with_empty_body(client, operator):
    response = client.post(
        "/user/me/change-password",
        json={"current_password": PASSWORD, "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
        headers=operator,
    )

    assert response.status_code == 204
    assert response.content == b""
    assert login(client, "operator", NEW_PASSWORD).status_code == 200
