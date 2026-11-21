"""
Pruebas de la cola de inferencia (siatlib.service): modelo de trabajos, transiciones
de estado, persistencia en SQLite y worker. Usa un analizador falso, así que no
necesita YOLO, GPU ni videos reales.
"""

import json
import time
from pathlib import Path

import pytest

from siatlib.service import (
    InvalidJobRequest,
    InvalidTransition,
    JobNotFound,
    JobRequest,
    JobStatus,
    JobStore,
    ServiceSettings,
    Worker,
)
from siatlib.service.jobs import can_transition


def make_request(video="video.mp4", **overrides):
    data = {
        "video": video,
        "zones": [
            {"name": "Entrada Sur", "type": "entry", "polygon": [[0, 0], [10, 0], [10, 10]]},
            {"name": "Salida Este", "type": "exit", "polygon": [[50, 50], [60, 50], [60, 60]]},
        ],
        "metadata": {"task_id": 7},
    }
    data.update(overrides)
    return JobRequest.from_dict(data)


class FakeResult:
    def __init__(self, frames=10):
        self.total_frames_processed = frames

    def to_dict(self):
        return {
            "transition_counts": {"Entrada Sur": {"Salida Este": {"Transporte mediano": 1}}},
            "transition_determined_object": {},
            "transition_undetermined_object": {},
            "trajectories": {},
            "total_frames_processed": self.total_frames_processed,
            "output_video_path": "/ruta/interna.mp4",
        }


class FakeAnalyzer:
    """Imita TrafficAnalyzer.process_video: reporta progreso y devuelve un resultado."""

    def __init__(self, fail_on=None, frames=10):
        self.calls = []
        self.fail_on = fail_on
        self.frames = frames

    def process_video(self, video_path, zones, output_video_path=None, max_frames=None,
                      progress_callback=None, imgsz=None, **kwargs):
        self.calls.append({"video_path": video_path, "zones": zones, "output_video_path": output_video_path})
        if self.fail_on and video_path.endswith(self.fail_on):
            raise RuntimeError("explotó la inferencia")
        for f in range(1, self.frames + 1):
            if progress_callback:
                progress_callback(f, self.frames, 30.0)
        if output_video_path:
            Path(output_video_path).write_bytes(b"fake-mp4")
        return FakeResult(self.frames)


@pytest.fixture
def env(tmp_path):
    settings = ServiceSettings(data_dir=tmp_path / "data", models_dir=tmp_path / "models", poll_interval=0.01)
    settings.ensure_dirs()
    settings.models_dir.mkdir()
    (settings.models_dir / settings.default_model).write_bytes(b"pesos")
    for name in ("a.mp4", "b.mp4", "c.mp4", "video.mp4"):
        (settings.input_dir / name).write_bytes(b"video")
    store = JobStore(settings.db_path)
    analyzer = FakeAnalyzer()
    worker = Worker(store, settings, analyzer_factory=lambda model_path: analyzer)
    yield settings, store, worker, analyzer
    worker.stop(timeout=2)
    store.close()


# --------------------------------------------------------------------------- #
# JobRequest: validación del contrato                                          #
# --------------------------------------------------------------------------- #


def test_request_valid_and_zone_conversion():
    req = make_request()
    zones = req.zone_definitions()
    assert [z.name for z in zones] == ["Entrada Sur", "Salida Este"]
    assert zones[0].polygon == [(0, 0), (10, 0), (10, 10)]
    assert req.options.render_video is True
    assert req.metadata == {"task_id": 7}


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"video": ""}, "Falta 'video'"),
        ({"video": "/etc/passwd"}, "ruta relativa"),
        ({"video": "../fuera.mp4"}, "ruta relativa"),
        ({"model": "../../modelo.pt"}, "ruta relativa"),
        ({"zones": [{"name": "E", "type": "entry", "polygon": [[0, 0], [1, 1], [2, 2]]}]}, "'exit'"),
        ({"zones": [{"name": "E", "type": "puerta", "polygon": [[0, 0], [1, 1], [2, 2]]}]}, "tipo 'puerta'"),
        ({"zones": [{"name": "E", "type": "entry", "polygon": [[0, 0], [1, 1]]},
                    {"name": "S", "type": "exit", "polygon": [[0, 0], [1, 1], [2, 2]]}]}, "3 vértices"),
        ({"zones": [{"name": "E", "type": "entry"}]}, "Formato inválido"),
        ({"options": {"max_frames": 0}}, "max_frames"),
        ({"options": {"desconocida": 1}}, "Formato inválido"),
    ],
)
def test_request_rejects_invalid(overrides, message):
    with pytest.raises(InvalidJobRequest, match=message):
        make_request(**overrides)


def test_allowed_transitions():
    assert can_transition(JobStatus.PENDING, JobStatus.PROCESSING)
    assert can_transition(JobStatus.PENDING, JobStatus.CANCELLED)
    assert can_transition(JobStatus.PROCESSING, JobStatus.DONE)
    assert can_transition(JobStatus.PROCESSING, JobStatus.FAILED)
    assert not can_transition(JobStatus.PROCESSING, JobStatus.CANCELLED)
    assert not can_transition(JobStatus.DONE, JobStatus.PENDING)
    assert all(s.is_final for s in (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED))


# --------------------------------------------------------------------------- #
# JobStore                                                                     #
# --------------------------------------------------------------------------- #


def test_store_fifo_claim_and_states():
    store = JobStore()
    a, b = store.create(make_request("a.mp4")), store.create(make_request("b.mp4"))

    first = store.claim_next()
    assert first.id == a.id and first.status == JobStatus.PROCESSING and first.started_at
    assert store.claim_next().id == b.id
    assert store.claim_next() is None

    store.update_progress(a.id, 150)  # se acota a 100
    assert store.get(a.id).progress == 100.0
    done = store.mark_done(a.id)
    assert done.status == JobStatus.DONE and done.finished_at
    failed = store.mark_failed(b.id, "error X")
    assert failed.status == JobStatus.FAILED and failed.error == "error X"


def test_store_cancel_only_pending():
    store = JobStore()
    job = store.create(make_request())
    assert store.cancel(job.id).status == JobStatus.CANCELLED
    assert store.claim_next() is None  # cancelado no se procesa

    other = store.create(make_request())
    store.claim_next()
    with pytest.raises(InvalidTransition):
        store.cancel(other.id)


def test_store_not_found():
    with pytest.raises(JobNotFound):
        JobStore().get("no-existe")


def test_store_persists_and_requeues_interrupted(tmp_path):
    db = tmp_path / "jobs.db"
    store = JobStore(db)
    pending = store.create(make_request("a.mp4"))
    running = store.create(make_request("b.mp4"))
    store.claim_next()  # a -> PROCESSING
    store.close()

    # "Reinicio del contenedor"
    store = JobStore(db)
    assert store.get(pending.id).status == JobStatus.PROCESSING
    assert store.requeue_interrupted() == 1
    assert store.get(pending.id).status == JobStatus.PENDING
    assert store.get(running.id).status == JobStatus.PENDING
    assert store.claim_next().id == pending.id  # conserva el orden original
    assert store.counts()["PROCESSING"] == 1
    store.close()


def test_store_list_filters():
    store = JobStore()
    a = store.create(make_request())
    b = store.create(make_request())
    store.cancel(a.id)
    assert [j.id for j in store.list()] == [b.id, a.id]  # más recientes primero
    assert [j.id for j in store.list(status=JobStatus.CANCELLED)] == [a.id]


# --------------------------------------------------------------------------- #
# Worker                                                                       #
# --------------------------------------------------------------------------- #


def test_worker_processes_three_jobs_in_order(env):
    settings, store, worker, analyzer = env
    jobs = [store.create(make_request(v)) for v in ("a.mp4", "b.mp4", "c.mp4")]

    assert worker.run_once() and worker.run_once() and worker.run_once()
    assert worker.run_once() is False  # cola vacía

    assert [Path(c["video_path"]).name for c in analyzer.calls] == ["a.mp4", "b.mp4", "c.mp4"]
    for job in jobs:
        stored = store.get(job.id)
        assert stored.status == JobStatus.DONE
        assert stored.progress == 100.0
        assert stored.started_at <= stored.finished_at


def test_worker_writes_result_and_video(env):
    settings, store, worker, analyzer = env
    job = store.create(make_request())
    worker.run_once()

    out = settings.output_dir / job.id
    result = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert result["job_id"] == job.id
    assert result["metadata"] == {"task_id": 7}
    assert result["video"] == f"{job.id}/video.mp4"
    assert result["transition_counts"]["Entrada Sur"]["Salida Este"]["Transporte mediano"] == 1
    assert "output_video_path" not in result
    assert (out / "video.mp4").read_bytes() == b"fake-mp4"


def test_worker_without_render_video(env):
    settings, store, worker, analyzer = env
    job = store.create(make_request(options={"render_video": False}))
    worker.run_once()
    result = json.loads((settings.output_dir / job.id / "result.json").read_text())
    assert result["video"] is None
    assert analyzer.calls[0]["output_video_path"] is None


def test_worker_marks_failed_and_continues(env):
    settings, store, worker, analyzer = env
    analyzer.fail_on = "a.mp4"
    bad = store.create(make_request("a.mp4"))
    good = store.create(make_request("b.mp4"))
    worker.run_once()
    worker.run_once()

    failed = store.get(bad.id)
    assert failed.status == JobStatus.FAILED
    assert "explotó la inferencia" in failed.error
    assert store.get(good.id).status == JobStatus.DONE


def test_worker_fails_on_missing_video_or_model(env):
    settings, store, worker, analyzer = env
    no_video = store.create(make_request("no-existe.mp4"))
    no_model = store.create(make_request(model="otro.pt"))
    worker.run_once()
    worker.run_once()
    assert "No existe el video" in store.get(no_video.id).error
    assert "No existe el modelo" in store.get(no_model.id).error
    assert analyzer.calls == []


def test_worker_reuses_analyzer_per_model(env):
    settings, store, worker, analyzer = env
    created = []
    worker._factory = lambda model_path: created.append(model_path) or analyzer
    store.create(make_request("a.mp4"))
    store.create(make_request("b.mp4"))
    worker.run_once()
    worker.run_once()
    assert len(created) == 1


def test_worker_thread_drains_queue(env):
    settings, store, worker, analyzer = env
    jobs = [store.create(make_request(v)) for v in ("a.mp4", "b.mp4", "c.mp4")]
    worker.start()
    deadline = time.time() + 5
    while time.time() < deadline and store.counts()["DONE"] < 3:
        time.sleep(0.02)
    worker.stop(timeout=2)
    assert all(store.get(j.id).status == JobStatus.DONE for j in jobs)
    assert not worker.is_alive
