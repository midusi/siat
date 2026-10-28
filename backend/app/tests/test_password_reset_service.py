import pytest

from app.adapters.persistence.memory import InMemoryUnitOfWork
from app.domain.entities import User
from app.domain.exceptions import ValidationError
from app.services.password_reset_service import PasswordResetService

NEW_PASSWORD = "Nueva456"


class FakeEmailService:
    def __init__(self):
        self.sent: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))


@pytest.fixture
def mailer():
    return FakeEmailService()


@pytest.fixture
def service(mailer):
    uow = InMemoryUnitOfWork()
    svc = PasswordResetService(uow, mailer)
    uow.users.add(
        User(
            username="operador",
            password=svc.user_service.hash_password("secret1"),
            email="op@example.com",
            first_name="Op",
            last_name="Erador",
            role="ROLE_OPERADOR",
        )
    )
    uow.commit()
    return svc


def _issued_token(mailer) -> str:
    return mailer.sent[-1][2].split("\n\n")[1].strip()


# --- request_reset ---------------------------------------------------------

@pytest.mark.parametrize("identifier", ["operador", "op@example.com"])
def test_request_reset_emails_the_token_to_the_user(service, mailer, identifier):
    service.request_reset(identifier)

    [(to, subject, body)] = mailer.sent
    assert to == "op@example.com"
    assert subject == "Recuperación de contraseña"
    assert "Usa este token para recuperar tu contraseña" in body
    assert _issued_token(mailer)


def test_request_reset_for_unknown_user_sends_nothing_and_does_not_raise(service, mailer):
    assert service.request_reset("ghost") is None
    assert mailer.sent == []


# --- perform_reset ---------------------------------------------------------

def test_perform_reset_changes_the_password_and_bumps_the_version(service, mailer):
    service.request_reset("operador")

    service.perform_reset(_issued_token(mailer), NEW_PASSWORD, NEW_PASSWORD)

    user = service.uow.users.get_by_username("operador")
    assert service.user_service.pwd_context.verify(NEW_PASSWORD, user.password)
    assert user.refresh_token_version == 1


def test_perform_reset_rejects_an_invalid_token(service):
    with pytest.raises(ValidationError) as error:
        service.perform_reset("garbage", NEW_PASSWORD, NEW_PASSWORD)

    assert error.value.status_code == 400
    assert error.value.detail == "Token inválido o expirado"


def test_perform_reset_rejects_a_token_whose_email_no_longer_matches(service, mailer):
    service.request_reset("operador")
    service.uow.users.get_by_username("operador").email = "otro@example.com"

    with pytest.raises(ValidationError, match="Token inválido o expirado"):
        service.perform_reset(_issued_token(mailer), NEW_PASSWORD, NEW_PASSWORD)


def test_perform_reset_checks_the_token_before_the_passwords(service):
    with pytest.raises(ValidationError, match="Token inválido o expirado"):
        service.perform_reset("garbage", "a", "b")


def test_perform_reset_validates_passwords_once_the_token_is_valid(service, mailer):
    service.request_reset("operador")

    with pytest.raises(ValidationError) as error:
        service.perform_reset(_issued_token(mailer), NEW_PASSWORD, "Otra789")

    assert error.value.detail == "Las contraseñas no coinciden"
    assert error.value.field == "confirm_password"
