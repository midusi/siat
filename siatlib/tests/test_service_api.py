"""
Pruebas de la API HTTP del servicio (siatlib.service.api) contra el contrato de
docs/SIATLIB_SERVICE_API.md. El worker se ejecuta a mano (run_once) para que los
tests sean deterministas.
"""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from siatlib.service import JobStore, ServiceSettings, Worker  # noqa: E402
from siatlib.service.api import create_app  # noqa: E402

from test_service_queue import FakeAnalyzer  # noqa: E402

BODY = {
    "video": "video.mp4",
    "zones": [
        {"name": "Entrada Sur", "type": "entry", "polygon": [[0, 0], [10, 0], [10, 10]]},
        {"name": "Salida Este", "type": "exit", "polygon": [[50, 50], [60, 50], [60, 60]]},
        {"name": "Cartel", "type": "excluded", "polygon": [[1, 1], [2, 1], [2, 2]]},
    ],
    "metadata": {"task_id": 123},
}


@pytest.fixture
def ctx(tmp_path):
    settings = ServiceSettings(data_dir=tmp_path / "data", models_dir=tmp_path / "models")
    settings.ensure_dirs()
    settings.models_dir.mkdir()
    (settings.models_dir / settings.default_model).write_bytes(b"pesos")
    (settings.input_dir / "video.mp4").write_bytes(b"video")
    store = JobStore(settings.db_path)
    analyzer = FakeAnalyzer()
    worker = Worker(store, settings, analyzer_factory=lambda p: analyzer)
    app = create_app(settings, store=store, worker=worker, start_worker=False)
    with TestClient(app) as client:
        yield client, worker, analyzer
    store.close()


def test_full_flow(ctx):
    client, worker, analyzer = ctx

    r = client.post("/jobs", json=BODY)
    assert r.status_code == 202
    job = r.json()
    assert job["status"] == "PENDING" and job["progress"] == 0
    assert job["metadata"] == {"task_id": 123}

    # Antes de procesarse no hay resultados
    assert client.get(f"/jobs/{job['id']}/result").status_code == 409

    worker.run_once()

    r = client.get(f"/jobs/{job['id']}")
    assert r.json()["status"] == "DONE" and r.json()["progress"] == 100

    result = client.get(f"/jobs/{job['id']}/result").json()
    assert result["job_id"] == job["id"]
    assert result["metadata"] == {"task_id": 123}
    assert result["transition_counts"]["Entrada Sur"]["Salida Este"]["Transporte mediano"] == 1

    video = client.get(f"/jobs/{job['id']}/video")
    assert video.status_code == 200
    assert video.headers["content-type"] == "video/mp4"
    assert video.content == b"fake-mp4"

    # Las zonas excluidas llegan al analizador
    names = [z.name for z in analyzer.calls[0]["zones"]]
    assert names == ["Entrada Sur", "Salida Este", "Cartel"]


def test_list_and_filter(ctx):
    client, worker, _ = ctx
    a = client.post("/jobs", json=BODY).json()
    b = client.post("/jobs", json=BODY).json()
    client.delete(f"/jobs/{a['id']}")

    assert [j["id"] for j in client.get("/jobs").json()] == [b["id"], a["id"]]
    assert [j["id"] for j in client.get("/jobs?status=CANCELLED").json()] == [a["id"]]
    assert client.get("/jobs?status=INVENTADO").status_code == 422


def test_cancel_rules(ctx):
    client, worker, _ = ctx
    job = client.post("/jobs", json=BODY).json()
    r = client.delete(f"/jobs/{job['id']}")
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    # Ya cancelado (estado final): no se puede volver a cancelar
    assert client.delete(f"/jobs/{job['id']}").status_code == 409

    done = client.post("/jobs", json=BODY).json()
    worker.run_once()
    assert client.delete(f"/jobs/{done['id']}").status_code == 409


def test_not_found(ctx):
    client, _, _ = ctx
    for path in ("/jobs/nope", "/jobs/nope/result", "/jobs/nope/video"):
        assert client.get(path).status_code == 404
    assert client.delete("/jobs/nope").status_code == 404


@pytest.mark.parametrize(
    "change, fragment",
    [
        ({"video": "no-existe.mp4"}, "No existe el video"),
        ({"video": "../secreto.mp4"}, "ruta relativa"),
        ({"model": "otro.pt"}, "No existe el modelo"),
        ({"zones": BODY["zones"][:1]}, "'exit'"),
    ],
)
def test_validation_errors(ctx, change, fragment):
    client, _, _ = ctx
    r = client.post("/jobs", json={**BODY, **change})
    assert r.status_code == 422
    assert fragment in r.json()["detail"]


def test_schema_errors_from_pydantic(ctx):
    client, _, _ = ctx
    bad = {**BODY, "zones": [{"name": "X", "type": "puerta", "polygon": [[0, 0]]}]}
    assert client.post("/jobs", json=bad).status_code == 422


def test_video_not_rendered(ctx):
    client, worker, _ = ctx
    job = client.post("/jobs", json={**BODY, "options": {"render_video": False}}).json()
    worker.run_once()
    assert client.get(f"/jobs/{job['id']}/video").status_code == 404
    assert client.get(f"/jobs/{job['id']}/result").json()["video"] is None


def test_failed_job_exposes_error(ctx):
    client, worker, analyzer = ctx
    analyzer.fail_on = "video.mp4"
    job = client.post("/jobs", json=BODY).json()
    worker.run_once()
    data = client.get(f"/jobs/{job['id']}").json()
    assert data["status"] == "FAILED"
    assert "explotó la inferencia" in data["error"]
    assert client.get(f"/jobs/{job['id']}/result").status_code == 409


def test_health(ctx):
    client, _, _ = ctx
    client.post("/jobs", json=BODY)
    h = client.get("/health").json()
    assert h["status"] == "ok"
    assert h["default_model_found"] is True
    assert h["queue"]["PENDING"] == 1
    assert "cuda_available" in h["device"]


def test_openapi_docs_available(ctx):
    client, _, _ = ctx
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/jobs", "/jobs/{job_id}", "/jobs/{job_id}/result", "/jobs/{job_id}/video", "/health"} <= set(paths)
