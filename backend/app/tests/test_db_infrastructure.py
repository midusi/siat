import pytest

from app import config
from app.db import get_db_session


DATABASE_ENV = {
    "POSTGRES_DRIVER": "postgresql+psycopg2",
    "POSTGRES_USER": "test-user",
    "POSTGRES_PASSWORD": "p@ss:word/ok",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "test-db",
}


def test_db_url_preserves_special_characters_in_password(monkeypatch):
    for name, value in DATABASE_ENV.items():
        monkeypatch.setenv(name, value)

    url = config.db_url()

    assert url.drivername == "postgresql+psycopg2"
    assert url.username == "test-user"
    assert url.password == "p@ss:word/ok"
    assert url.host == "localhost"
    assert url.port == 5432
    assert url.database == "test-db"
    assert "p@ss:word/ok" not in url.render_as_string(hide_password=True)


def test_db_url_rejects_missing_configuration(monkeypatch):
    for name in DATABASE_ENV:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValueError, match="POSTGRES_DRIVER") as error:
        config.db_url()

    assert "test-user" not in str(error.value)
    assert "p@ss:word/ok" not in str(error.value)


def test_get_db_session_closes_session(monkeypatch):
    class FakeSession:
        closed = False

        def close(self):
            self.closed = True

    session = FakeSession()
    monkeypatch.setattr("app.db.SessionLocal", lambda: session)

    db_generator = get_db_session()
    assert next(db_generator) is session

    db_generator.close()

    assert session.closed is True