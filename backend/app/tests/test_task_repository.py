import datetime

from app.adapters.persistence.memory import InMemoryUnitOfWork
from app.adapters.storage.memory import InMemoryObjectStorage
from app.domain.entities import District, Locality, Task, TaskStatus, TaskStatusHistory, Video
from app.services.task_service import TaskService


def _seed_task(uow: InMemoryUnitOfWork) -> None:
    uow._store.statuses["VIDEO_UPLOADED"] = TaskStatus(id="VIDEO_UPLOADED", name="Video cargado")
    uow._store.statuses["ARCHIVED"] = TaskStatus(id="ARCHIVED", name="Archivada")
    uow._store.statuses["REVIEW"] = TaskStatus(id="REVIEW", name="Revisión")
    district = District(id=1, name="La Plata", province_id=1)
    uow._store.districts[1] = district
    uow._store.localities[1] = Locality(id=1, name="Centro", district_id=1, district=district)
    video = Video(id=1, name="clip", format="mp4", url="task/1/clip.mp4", fps=30, duration=10, width=1920, height=1080)
    uow._store.videos[1] = video
    uow._store.counters["video"] = 2
    task = Task(
        id=1,
        name="Tarea 1",
        date=datetime.datetime(2026, 1, 1),
        created_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        video_id=1,
        locality_id=1,
    )
    uow._store.tasks[1] = task
    uow._store.counters["task"] = 2
    history = TaskStatusHistory(
        id=1,
        from_date=datetime.datetime(2026, 1, 1, 12, 0, 0),
        task_id=1,
        status_id="VIDEO_UPLOADED",
        status_name="Video cargado",
    )
    uow._store.histories[1] = history
    uow._store.counters["history"] = 2


def test_task_archive_and_list_with_memory_uow():
    uow = InMemoryUnitOfWork()
    _seed_task(uow)
    service = TaskService(uow, InMemoryObjectStorage(bucket_name="siat-bucket"))

    active = service.get_list()
    assert len(active) == 1
    assert active[0].name == "Tarea 1"
    assert active[0].status.id == "VIDEO_UPLOADED"

    archived = service.archive(1)
    assert archived.status.id == "ARCHIVED"
    assert service.get_list() == []
    assert len(service.get_archived_list()) == 1

    restored = service.unarchive(1)
    assert restored.status.id == "VIDEO_UPLOADED"
    assert len(service.get_list()) == 1
