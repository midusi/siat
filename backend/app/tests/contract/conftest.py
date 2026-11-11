"""Fixtures de los tests de contrato HTTP.

Congelan el comportamiento observable de la API (status, bodies, cookies) para poder
refactorizar los controllers sin cambiar el contrato. Ninguno toca la base real:
usan SQLite en memoria, storage en memoria y un EmailService falso.
"""
import os

# Deben definirse antes de importar `app`: `app.db` arma la URL al importarse.
# Son valores de relleno; nunca se abre una conexión (ver `forbid_real_database`).
for _name, _value in {
    "POSTGRES_DRIVER": "postgresql+psycopg2",
    "POSTGRES_USER": "contract",
    "POSTGRES_PASSWORD": "contract",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "contract",
    "BCRYPT_ROUNDS": "4",
}.items():
    os.environ.setdefault(_name, _value)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import db as app_db
from app.adapters.storage.memory import InMemoryObjectStorage
from app.main import app
from app.models import Base
from app.security import rate_limit
from app.services import auth_service, dependencies
from app.services.email_service import EmailService
from app.services.video_service import VideoService


@pytest.fixture(autouse=True)
def forbid_real_database(monkeypatch):
    def _forbidden(*_args, **_kwargs):
        raise AssertionError("Los tests de contrato no deben abrir sesiones contra la base real")

    monkeypatch.setattr(app_db, "SessionLocal", _forbidden)


@pytest.fixture(autouse=True)
def reset_in_memory_auth_state():
    auth_service._failed_attempts.clear()
    rate_limit._windows.clear()
    yield
    auth_service._failed_attempts.clear()
    rate_limit._windows.clear()


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False)
    engine.dispose()


@pytest.fixture
def db_session(session_factory):
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def storage(monkeypatch) -> InMemoryObjectStorage:
    shared = InMemoryObjectStorage(bucket_name="siat-bucket")
    monkeypatch.setattr(dependencies, "build_object_storage", lambda: shared)
    return shared


@pytest.fixture
def sent_emails(monkeypatch) -> list[dict]:
    outbox: list[dict] = []

    def fake_send(_self, to, subject, body):
        outbox.append({"to": to, "subject": subject, "body": body})

    monkeypatch.setattr(EmailService, "send", fake_send)
    return outbox


@pytest.fixture
def video_frame(monkeypatch) -> str:
    frame = "ZnJhbWU="
    monkeypatch.setattr(VideoService, "get_frame", lambda _self, _key, _index: frame)
    return frame


@pytest.fixture
def client(session_factory, storage, sent_emails):
    def override_db_session():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[app_db.get_db_session] = override_db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
