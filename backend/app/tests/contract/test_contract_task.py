import pytest

from app.tests.contract.support import bearer, create_user, seed_task

TASK_NOT_FOUND = {"detail": "La tarea no existe"}
MISSING_ID = 999

ROAD = {"name": "Ruta", "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]]}
CONFIG_BODY = {"roads_in": [ROAD], "roads_out": [ROAD]}
UPDATE_BODY = {"rutas": {}, "indeterminados": {}}


@pytest.fixture
def admin(client, db_session):
    create_user(db_session, "admin", "ROLE_ADMIN")
    return bearer(client, "admin")


@pytest.fixture
def operator(client, db_session):
    create_user(db_session, "operator", "ROLE_OPERADOR")
    return bearer(client, "operator")


@pytest.fixture
def viewer(client, db_session):
    create_user(db_session, "viewer", "ROLE_VIEWER")
    return bearer(client, "viewer")


# --- autenticación y roles -------------------------------------------------

@pytest.mark.parametrize("method, url", [
    ("get", "/task"),
    ("get", "/task/archived"),
    ("get", "/task/1"),
    ("post", "/task"),
    ("post", "/task/1/archive"),
    ("delete", "/task/1"),
    ("get", "/task/1/download"),
    ("get", "/task/1/get-first-frame-info"),
    ("post", "/task/upload/presigned-url"),
])
def test_task_endpoints_require_authentication(client, method, url):
    response = getattr(client, method)(url)

    assert response.status_code == 401
    assert response.json() == {"detail": "No autenticado"}


@pytest.mark.parametrize("method, url", [
    ("post", "/task/1/archive"),
    ("post", "/task/1/unarchive"),
    ("post", "/task"),
    ("post", "/task/1/config"),
    ("post", "/task/1/update-data"),
    ("delete", "/task/1"),
    ("get", "/task/1/download"),
])
def test_write_endpoints_reject_roles_outside_admin_and_operator(client, viewer, method, url):
    response = getattr(client, method)(url, headers=viewer)

    assert response.status_code == 403
    assert response.json() == {"detail": "Acceso denegado"}


def test_read_endpoints_are_open_to_any_authenticated_role(client, viewer):
    assert client.get("/task", headers=viewer).status_code == 200
    assert client.get("/task/archived", headers=viewer).status_code == 200


# --- listados y detalle ----------------------------------------------------

def test_list_returns_active_tasks_with_expected_shape(client, db_session, admin):
    seed_task(db_session)

    response = client.get("/task", headers=admin)

    assert response.status_code == 200
    [task] = response.json()
    assert set(task) == {"id", "name", "locality", "name_video", "duration", "status", "date", "created_at", "progress"}
    assert task["name"] == "Tarea 1"
    assert task["status"]["id"] == "VIDEO_UPLOADED"
    assert task["progress"] == 0


def test_archived_list_is_empty_until_a_task_is_archived(client, db_session, admin):
    seed_task(db_session)

    assert client.get("/task/archived", headers=admin).json() == []


def test_get_task_not_found_is_404(client, admin):
    response = client.get(f"/task/{MISSING_ID}", headers=admin)

    assert response.status_code == 404
    assert response.json() == TASK_NOT_FOUND


def test_get_task_returns_details(client, db_session, admin):
    seed_task(db_session)

    response = client.get("/task/1", headers=admin)

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Tarea 1",
        "videoPath": "/bucket/siat-bucket/task/1/clip.mp4",
        "videoWidth": 1920,
        "videoHeight": 1080,
        "videoFps": 30,
        "roadsIn": [],
        "roadsOut": [],
    }


def test_task_id_must_be_an_integer(client, admin):
    assert client.get("/task/abc", headers=admin).status_code == 422


# --- archivar, desarchivar, borrar -----------------------------------------

def test_archive_and_unarchive_round_trip(client, db_session, admin):
    seed_task(db_session)

    archived = client.post("/task/1/archive", headers=admin)
    assert archived.status_code == 200
    assert archived.json()["status"]["id"] == "ARCHIVED"
    assert client.get("/task", headers=admin).json() == []
    assert len(client.get("/task/archived", headers=admin).json()) == 1

    restored = client.post("/task/1/unarchive", headers=admin)
    assert restored.status_code == 200
    assert restored.json()["status"]["id"] == "VIDEO_UPLOADED"


@pytest.mark.parametrize("url", ["/task/{id}/archive", "/task/{id}/unarchive"])
def test_archive_endpoints_return_404_for_missing_task(client, admin, url):
    response = client.post(url.format(id=MISSING_ID), headers=admin)

    assert response.status_code == 404
    assert response.json() == TASK_NOT_FOUND


def test_delete_returns_204_with_empty_body_and_removes_the_task(client, db_session, admin):
    # Sin historial: con filas en task_status_history, delete_cascade falla bajo SQLite
    # (StaleDataError). No se asume que ocurra igual en Postgres, por eso no se fija acá.
    seed_task(db_session, with_history=False)

    response = client.delete("/task/1", headers=admin)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/task/1", headers=admin).status_code == 404


def test_delete_missing_task_is_404(client, operator):
    response = client.delete(f"/task/{MISSING_ID}", headers=operator)

    assert response.status_code == 404
    assert response.json() == TASK_NOT_FOUND


# --- config y update-data --------------------------------------------------

def test_config_missing_task_is_404(client, admin):
    response = client.post(f"/task/{MISSING_ID}/config", json=CONFIG_BODY, headers=admin)

    assert response.status_code == 404
    assert response.json() == TASK_NOT_FOUND


def test_config_with_invalid_body_is_422(client, db_session, admin):
    seed_task(db_session)

    assert client.post("/task/1/config", json={"roads_in": []}, headers=admin).status_code == 422


def test_update_data_missing_task_is_404(client, admin):
    response = client.post(f"/task/{MISSING_ID}/update-data", json=UPDATE_BODY, headers=admin)

    assert response.status_code == 404
    assert response.json() == TASK_NOT_FOUND


def test_update_data_with_invalid_body_is_422(client, db_session, admin):
    seed_task(db_session)

    assert client.post("/task/1/update-data", json={"rutas": {}}, headers=admin).status_code == 422


# --- creación --------------------------------------------------------------

CREATE_FORM = {"name": "Nueva", "locality_id": "1", "date": "2026-01-01T00:00:00"}


def test_create_without_file_or_object_key_is_400(client, admin):
    response = client.post("/task", data=CREATE_FORM, headers=admin)

    assert response.status_code == 400
    assert response.json() == {"detail": "Debe proporcionar 'file' o 'object_key'"}


def test_create_with_empty_object_key_is_400(client, admin):
    response = client.post("/task", data={**CREATE_FORM, "object_key": ""}, headers=admin)

    assert response.status_code == 400
    assert response.json() == {"detail": "Debe proporcionar 'file' o 'object_key'"}


@pytest.mark.parametrize("missing", ["name", "locality_id", "date"])
def test_create_requires_form_fields(client, admin, missing):
    form = {k: v for k, v in CREATE_FORM.items() if k != missing}

    response = client.post("/task", data=form, headers=admin)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", missing]


def test_create_validates_form_fields_before_checking_file_or_object_key(client, admin):
    response = client.post("/task", data={**CREATE_FORM, "locality_id": "abc"}, headers=admin)

    assert response.status_code == 422


# --- uploads directos ------------------------------------------------------

def test_presigned_upload_url_shape(client, admin):
    response = client.post(
        "/task/upload/presigned-url",
        json={"filename": "clip.mp4", "content_type": "video/mp4"},
        headers=admin,
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"upload_url", "object_key", "expires_in"}
    assert body["object_key"].startswith("uploads/") and body["object_key"].endswith(".mp4")
    assert body["expires_in"] == 3600
    assert "siat-bucket" in body["upload_url"]


def test_presigned_upload_url_requires_filename_and_content_type(client, admin):
    response = client.post("/task/upload/presigned-url", json={"filename": "clip.mp4"}, headers=admin)

    assert response.status_code == 422


def test_multipart_init_shape(client, admin):
    response = client.post(
        "/task/upload/multipart/init",
        json={"filename": "clip.mp4", "file_size": 11 * 1024 * 1024},
        headers=admin,
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"object_key", "upload_id", "part_size", "part_count", "expires_in"}
    assert body["part_count"] == 3
    assert body["object_key"].startswith("uploads/")


@pytest.mark.parametrize("file_size, detail", [
    (0, "El archivo está vacío"),
    (8 * 1024 * 1024 * 1024 + 1, "El archivo supera el tamaño máximo de 8 GB"),
])
def test_multipart_init_rejects_invalid_sizes(client, admin, file_size, detail):
    response = client.post(
        "/task/upload/multipart/init",
        json={"filename": "clip.mp4", "file_size": file_size},
        headers=admin,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": detail}


def test_multipart_part_url_and_abort(client, admin):
    init = client.post(
        "/task/upload/multipart/init",
        json={"filename": "clip.mp4", "file_size": 1024},
        headers=admin,
    ).json()
    ref = {"object_key": init["object_key"], "upload_id": init["upload_id"]}

    part = client.post("/task/upload/multipart/part-url", json={**ref, "part_number": 1}, headers=admin)
    assert part.status_code == 200
    assert set(part.json()) == {"upload_url", "part_number", "expires_in"}
    assert part.json()["part_number"] == 1

    aborted = client.post("/task/upload/multipart/abort", json=ref, headers=admin)
    assert aborted.status_code == 200
    assert aborted.json() == {"status": "aborted"}


@pytest.mark.parametrize("url, extra", [
    ("/task/upload/multipart/part-url", {"part_number": 1}),
    ("/task/upload/multipart/complete", {"part_count": 1}),
    ("/task/upload/multipart/abort", {}),
])
def test_multipart_endpoints_reject_keys_outside_uploads(client, admin, url, extra):
    response = client.post(
        url,
        json={"object_key": "../secret.mp4", "upload_id": "x", **extra},
        headers=admin,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "object_key inválido"}


# --- primer frame ----------------------------------------------------------

def test_first_frame_info_missing_task_is_404(client, admin):
    response = client.get(f"/task/{MISSING_ID}/get-first-frame-info", headers=admin)

    assert response.status_code == 404
    assert response.json() == TASK_NOT_FOUND


def test_first_frame_info_returns_dimensions_and_frame(client, db_session, admin, video_frame):
    seed_task(db_session)

    response = client.get("/task/1/get-first-frame-info", headers=admin)

    assert response.status_code == 200
    assert response.json() == {
        "width": 1920,
        "height": 1080,
        "image_b64": video_frame,
        "mimetype": "image/jpeg",
    }


# --- descarga --------------------------------------------------------------

def test_download_missing_task_is_404(client, admin):
    response = client.get(f"/task/{MISSING_ID}/download", headers=admin)

    assert response.status_code == 404
    assert response.json() == TASK_NOT_FOUND


def test_download_streams_the_original_video_as_attachment(client, db_session, storage, operator):
    seed_task(db_session)
    storage.upload(b"original-bytes", object_name="task/1/clip.mp4", content_type="video/mp4")

    response = client.get("/task/1/download", headers=operator)

    assert response.status_code == 200
    assert response.content == b"original-bytes"
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["content-disposition"] == 'attachment; filename="clip.mp4"'
    assert response.headers["content-length"] == str(len(b"original-bytes"))


def test_download_prefers_the_processed_video_when_there_is_an_inference(client, db_session, storage, admin):
    seed_task(db_session, processed_url="task/1/processed.mp4")
    storage.upload(b"original-bytes", object_name="task/1/clip.mp4", content_type="video/mp4")
    storage.upload(b"processed-bytes", object_name="task/1/processed.mp4", content_type="video/mp4")

    response = client.get("/task/1/download", headers=admin)

    assert response.status_code == 200
    assert response.content == b"processed-bytes"
    assert response.headers["content-disposition"] == 'attachment; filename="clip_processed.mp4"'
