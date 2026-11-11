import pytest

from app.adapters.persistence.memory import InMemoryUnitOfWork
from app.auth.jwt import create_access_token, create_refresh_token
from app.domain.entities import User
from app.domain.exceptions import UnauthorizedError
from app.services import auth_service
from app.services.auth_service import AuthService

PASSWORD = "secret1"


@pytest.fixture(autouse=True)
def clean_failed_attempts():
    auth_service._failed_attempts.clear()
    yield
    auth_service._failed_attempts.clear()


@pytest.fixture
def service():
    uow = InMemoryUnitOfWork()
    svc = AuthService(uow)
    uow.users.add(
        User(
            username="operador",
            password=svc.pwd_context.hash(PASSWORD),
            email="op@example.com",
            first_name="Op",
            last_name="Erador",
            role="ROLE_OPERADOR",
        )
    )
    uow.commit()
    return svc


def _user(service) -> User:
    return service.uow.users.get_by_username("operador")


def _tokens(service, version: int | None = None) -> tuple[str, str]:
    user = _user(service)
    ver = user.refresh_token_version if version is None else version
    payload = {"id": user.id, "username": user.username, "role": user.role}
    return create_access_token(payload, ver), create_refresh_token(payload, ver)


# --- login -----------------------------------------------------------------

def test_login_returns_a_session_with_both_tokens_and_the_user(service):
    session = service.login("operador", PASSWORD)

    assert session.access_token and session.refresh_token
    assert session.user.username == "operador"


@pytest.mark.parametrize("username, password", [
    ("ghost", PASSWORD),
    ("operador", "wrong1"),
])
def test_login_with_bad_credentials_raises_unauthorized(service, username, password):
    with pytest.raises(UnauthorizedError) as error:
        service.login(username, password)

    assert error.value.status_code == 401
    assert error.value.detail == "Credenciales inválidas"


def test_login_for_inactive_user_raises_unauthorized(service):
    _user(service).active = False

    with pytest.raises(UnauthorizedError, match="Credenciales inválidas"):
        service.login("operador", PASSWORD)


def test_login_is_rejected_while_the_account_is_locked(service):
    for _ in range(auth_service.AUTH_LOGIN_FAIL_LIMIT):
        with pytest.raises(UnauthorizedError):
            service.login("operador", "wrong1")

    with pytest.raises(UnauthorizedError, match="Credenciales inválidas"):
        service.login("operador", PASSWORD)


# --- refresh_from_token ----------------------------------------------------

@pytest.mark.parametrize("raw_token", [None, ""])
def test_refresh_from_token_without_token(service, raw_token):
    with pytest.raises(UnauthorizedError, match="No hay refresh token"):
        service.refresh_from_token(raw_token)


def test_refresh_from_token_rejects_garbage(service):
    with pytest.raises(UnauthorizedError, match="Refresh token inválido"):
        service.refresh_from_token("garbage")


def test_refresh_from_token_rejects_an_access_token(service):
    access, _ = _tokens(service)

    with pytest.raises(UnauthorizedError, match="Refresh token inválido"):
        service.refresh_from_token(access)


def test_refresh_from_token_rotates_the_version(service):
    _, refresh = _tokens(service)

    session = service.refresh_from_token(refresh)

    assert session.user.refresh_token_version == 1
    assert session.access_token and session.refresh_token


def test_refresh_from_token_rejects_a_stale_version(service):
    _, refresh = _tokens(service)
    service.refresh_from_token(refresh)

    with pytest.raises(UnauthorizedError, match="Refresh inválido o expirado"):
        service.refresh_from_token(refresh)


def test_refresh_from_token_rejects_an_inactive_user(service):
    _, refresh = _tokens(service)
    _user(service).active = False

    with pytest.raises(UnauthorizedError, match="Refresh inválido o expirado"):
        service.refresh_from_token(refresh)


# --- logout_from_tokens ----------------------------------------------------

def test_logout_with_access_token_bumps_the_version(service):
    access, _ = _tokens(service)

    service.logout_from_tokens(access, None)

    assert _user(service).refresh_token_version == 1


def test_logout_falls_back_to_the_refresh_token(service):
    _, refresh = _tokens(service)

    service.logout_from_tokens(None, refresh)

    assert _user(service).refresh_token_version == 1


def test_logout_ignores_a_token_of_the_wrong_type_in_the_access_slot(service):
    _, refresh = _tokens(service)

    service.logout_from_tokens(refresh, None)

    assert _user(service).refresh_token_version == 0


@pytest.mark.parametrize("access, refresh", [(None, None), ("garbage", "garbage")])
def test_logout_without_valid_tokens_does_nothing(service, access, refresh):
    service.logout_from_tokens(access, refresh)

    assert _user(service).refresh_token_version == 0
