"""Helpers compartidos por los tests de contrato."""
from datetime import datetime

from passlib.context import CryptContext

from app.config import COOKIE_NAME, CSRF_HEADER_NAME, REFRESH_COOKIE_NAME
from app.models import (
    District,
    Inference,
    Locality,
    Province,
    Task,
    TaskStatus,
    TaskStatusHistory,
    User,
    Video,
)

PASSWORD = "Secret123"
BYPASS_RATE_LIMIT = {"x-test-bypass-ratelimit": "1"}
CSRF_HEADERS = {CSRF_HEADER_NAME: "1"}

_pwd = CryptContext(schemes=["bcrypt"], bcrypt__rounds=4)


def create_user(db, username="admin", role="ROLE_ADMIN", active=True, password=PASSWORD) -> User:
    user = User(
        username=username,
        password=_pwd.hash(password),
        email=f"{username}@example.com",
        first_name="Test",
        last_name="User",
        role=role,
        active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(client, username="admin", password=PASSWORD):
    """Hace login y deja el cliente sin cookies: cada test envía las que necesita."""
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
        headers=BYPASS_RATE_LIMIT,
    )
    client.cookies.clear()
    return response


def session_cookies(response) -> dict[str, str]:
    return {
        COOKIE_NAME: response.cookies.get(COOKIE_NAME),
        REFRESH_COOKIE_NAME: response.cookies.get(REFRESH_COOKIE_NAME),
    }


def cookie_header(**cookies: str) -> dict[str, str]:
    return {"Cookie": "; ".join(f"{name}={value}" for name, value in cookies.items())}


def bearer(client, username="admin", password=PASSWORD) -> dict[str, str]:
    token = login(client, username, password).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def set_cookie_attributes(response) -> dict[str, dict[str, str | bool]]:
    """Parsea los headers Set-Cookie a {nombre: {"value": ..., atributo: valor|True}}."""
    parsed: dict[str, dict[str, str | bool]] = {}
    for raw in response.headers.get_list("set-cookie"):
        name_value, *attributes = [part.strip() for part in raw.split(";")]
        name, _, value = name_value.partition("=")
        entry: dict[str, str | bool] = {"value": value}
        for attribute in attributes:
            key, sep, attr_value = attribute.partition("=")
            entry[key.lower()] = attr_value if sep else True
        parsed[name] = entry
    return parsed


def seed_task(db, name="Tarea 1", video_url="task/1/clip.mp4", processed_url=None, with_history=True) -> Task:
    db.add(Province(id=1, name="Buenos Aires"))
    db.add(District(id=1, name="La Plata", province_id=1))
    db.add(Locality(id=1, name="Centro", district_id=1))
    db.add(TaskStatus(id="VIDEO_UPLOADED", name="Video cargado"))
    db.add(TaskStatus(id="ARCHIVED", name="Archivada"))
    db.add(Video(id=1, name="clip", format="mp4", url=video_url, fps=30, duration=10, width=1920, height=1080))
    db.add(Task(id=1, name=name, date=datetime(2026, 1, 1), created_at=datetime(2026, 1, 1, 12), video_id=1, locality_id=1))
    if with_history:
        db.add(TaskStatusHistory(id=1, from_date=datetime(2026, 1, 1, 12), task_id=1, status_id="VIDEO_UPLOADED"))
    if processed_url:
        db.add(
            Inference(
                id=1,
                task_id=1,
                transition_counts={},
                transition_undetermined={},
                transition_determined={},
                url_data_obj_history="task/1/history.json",
                url_video_processed=processed_url,
                inferred_at=datetime(2026, 1, 2),
            )
        )
    db.commit()
    return db.get(Task, 1)
