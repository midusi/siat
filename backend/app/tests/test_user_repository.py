import ast
from pathlib import Path

from app.adapters.persistence.memory import InMemoryUnitOfWork
from app.domain.entities import User, TaskStatus
from app.schemas.user import UserCreateRequest
from app.services.auth_service import AuthService
from app.services.user_service import UserService


SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"
FORBIDDEN = ("app.models", "sqlalchemy.orm")
ALLOWED_SESSION_FILES = {"dependencies.py"}


def test_services_do_not_import_orm_or_session():
    offenders = []
    for path in SERVICES_DIR.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("app.models"):
                    offenders.append(f"{path.name}: from {node.module}")
                if node.module.startswith("sqlalchemy") and path.name not in ALLOWED_SESSION_FILES:
                    offenders.append(f"{path.name}: from {node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("app.models"):
                        offenders.append(f"{path.name}: import {alias.name}")
                    if alias.name.startswith("sqlalchemy") and path.name not in ALLOWED_SESSION_FILES:
                        offenders.append(f"{path.name}: import {alias.name}")
        src = path.read_text()
        if "Session" in src and path.name not in ALLOWED_SESSION_FILES:
            if "from sqlalchemy" in src or "Session" in {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}:
                if "from sqlalchemy" in src:
                    offenders.append(f"{path.name}: Session/sqlalchemy")
    assert offenders == [], offenders


def test_user_service_create_uses_repository_not_orm():
    uow = InMemoryUnitOfWork()
    service = UserService(uow)
    created = service.create(
        UserCreateRequest(
            username="franco",
            password="secret1",
            confirm_password="secret1",
            email="franco@example.com",
            role="ROLE_ADMIN",
            first_name="Franco",
            last_name="Cirielli",
        )
    )
    assert created.id == 1
    assert created.username == "franco"
    stored = uow.users.get(1)
    assert isinstance(stored, User)
    assert stored.email == "franco@example.com"


def test_auth_service_login_with_memory_uow():
    uow = InMemoryUnitOfWork()
    users = UserService(uow)
    created = users.create(
        UserCreateRequest(
            username="operador",
            password="secret1",
            confirm_password="secret1",
            email="op@example.com",
            role="ROLE_OPERADOR",
            first_name="Op",
            last_name="Erador",
        )
    )
    auth = AuthService(uow)
    result = auth.login("operador", "secret1")
    assert result is not None
    access, refresh, user = result
    assert access
    assert refresh
    assert user.id == created.id
    assert auth.login("operador", "wrong1") is None
