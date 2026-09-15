from __future__ import annotations

from app.domain.entities import (
    District,
    Inference,
    Locality,
    Province,
    Road,
    Task,
    TaskStatus,
    TaskStatusHistory,
    User,
    Video,
)


class _Store:
    def __init__(self):
        self.users: dict[int, User] = {}
        self.provinces: dict[int, Province] = {}
        self.districts: dict[int, District] = {}
        self.localities: dict[int, Locality] = {}
        self.videos: dict[int, Video] = {}
        self.tasks: dict[int, Task] = {}
        self.statuses: dict[str, TaskStatus] = {}
        self.histories: dict[int, TaskStatusHistory] = {}
        self.roads: dict[int, Road] = {}
        self.inferences: dict[int, Inference] = {}
        self.counters = {
            "user": 1,
            "video": 1,
            "task": 1,
            "history": 1,
            "road": 1,
            "inference": 1,
        }

    def next_id(self, key: str) -> int:
        value = self.counters[key]
        self.counters[key] += 1
        return value


class InMemoryUnitOfWork:
    def __init__(self):
        self._store = _Store()
        self._pending: list[object] = []
        self.users = _Users(self)
        self.provinces = _Provinces(self)
        self.districts = _Districts(self)
        self.localities = _Localities(self)
        self.videos = _Videos(self)
        self.tasks = _Tasks(self)
        self.task_statuses = _Statuses(self)
        self.status_histories = _Histories(self)
        self.roads = _Roads(self)
        self.inferences = _Inferences(self)

    def _stage(self, entity):
        self._pending.append(entity)
        return entity

    def flush(self) -> None:
        for entity in self._pending:
            if isinstance(entity, User) and entity.id is None:
                entity.id = self._store.next_id("user")
                self._store.users[entity.id] = entity
            elif isinstance(entity, Video) and entity.id is None:
                entity.id = self._store.next_id("video")
                self._store.videos[entity.id] = entity
            elif isinstance(entity, Task) and entity.id is None:
                entity.id = self._store.next_id("task")
                self._store.tasks[entity.id] = entity
            elif isinstance(entity, TaskStatusHistory) and entity.id is None:
                entity.id = self._store.next_id("history")
                self._store.histories[entity.id] = entity
            elif isinstance(entity, Road) and entity.id is None:
                entity.id = self._store.next_id("road")
                self._store.roads[entity.id] = entity
            elif isinstance(entity, Inference) and entity.id is None:
                entity.id = self._store.next_id("inference")
                self._store.inferences[entity.id] = entity
        self._pending.clear()

    def commit(self) -> None:
        self.flush()

    def rollback(self) -> None:
        self._pending.clear()

    def refresh(self, entity) -> None:
        return None

    def expire_all(self) -> None:
        return None


class _Users:
    def __init__(self, uow: InMemoryUnitOfWork):
        self.uow = uow
        self.store = uow._store

    def get(self, user_id: int) -> User | None:
        return self.store.users.get(user_id)

    def get_by_username(self, username: str) -> User | None:
        return next((u for u in self.store.users.values() if u.username == username), None)

    def get_by_username_or_email(self, username: str, email: str) -> User | None:
        return next((u for u in self.store.users.values() if u.username == username or u.email == email), None)

    def find_by_identifier(self, identifier: str) -> User | None:
        return next(
            (u for u in self.store.users.values() if u.username == identifier or u.email == identifier),
            None,
        )

    def list_all(self, **filters) -> list[User]:
        users = list(self.store.users.values())
        for key, value in filters.items():
            users = [u for u in users if getattr(u, key) == value]
        return users

    def add(self, user: User) -> User:
        return self.uow._stage(user)

    def delete(self, user: User) -> None:
        if user.id is not None:
            self.store.users.pop(user.id, None)


class _Provinces:
    def __init__(self, uow: InMemoryUnitOfWork):
        self.store = uow._store

    def list_all(self, **filters) -> list[Province]:
        items = list(self.store.provinces.values())
        for key, value in filters.items():
            items = [i for i in items if getattr(i, key) == value]
        return items


class _Districts:
    def __init__(self, uow: InMemoryUnitOfWork):
        self.store = uow._store

    def list_all(self, **filters) -> list[District]:
        items = list(self.store.districts.values())
        for key, value in filters.items():
            items = [i for i in items if getattr(i, key) == value]
        return items


class _Localities:
    def __init__(self, uow: InMemoryUnitOfWork):
        self.store = uow._store

    def get(self, locality_id: int) -> Locality | None:
        return self.store.localities.get(locality_id)

    def list_all(self) -> list[Locality]:
        return list(self.store.localities.values())

    def list_by_district(self, district_id: int) -> list[Locality]:
        return [item for item in self.store.localities.values() if item.district_id == district_id]


class _Videos:
    def __init__(self, uow: InMemoryUnitOfWork):
        self.uow = uow
        self.store = uow._store

    def add(self, video: Video) -> Video:
        return self.uow._stage(video)

    def delete(self, video: Video) -> None:
        if video.id is not None:
            self.store.videos.pop(video.id, None)


class _Tasks:
    def __init__(self, uow: InMemoryUnitOfWork):
        self.uow = uow
        self.store = uow._store

    def _current_status_id(self, task_id: int) -> str | None:
        open_h = [h for h in self.store.histories.values() if h.task_id == task_id and h.to_date is None]
        if open_h:
            return open_h[-1].status_id
        items = [h for h in self.store.histories.values() if h.task_id == task_id]
        return items[-1].status_id if items else None

    def get(self, task_id: int) -> Task | None:
        task = self.store.tasks.get(task_id)
        if task is None:
            return None
        task.video = self.store.videos.get(task.video_id)
        task.locality = self.store.localities.get(task.locality_id)
        task.inference = next((i for i in self.store.inferences.values() if i.task_id == task.id), None)
        task.status_history = [h for h in self.store.histories.values() if h.task_id == task.id]
        for hist in task.status_history:
            status = self.store.statuses.get(hist.status_id)
            if status is not None:
                hist.status_name = status.name
        current_id = self._current_status_id(task.id)
        current = next((h for h in reversed(task.status_history) if h.status_id == current_id), None)
        task.current_status_id = current_id
        task.current_status_name = current.status_name if current else None
        if current is not None:
            task.status_history = [current] + [h for h in task.status_history if h is not current]
        return task

    def list_active(self) -> list[Task]:
        return [self.get(t.id) for t in self.store.tasks.values() if self._current_status_id(t.id) != "ARCHIVED"]

    def list_archived(self) -> list[Task]:
        return [self.get(t.id) for t in self.store.tasks.values() if self._current_status_id(t.id) == "ARCHIVED"]

    def list_by_status(self, status_id: str) -> list[Task]:
        return [self.get(t.id) for t in self.store.tasks.values() if self._current_status_id(t.id) == status_id]

    def add(self, task: Task) -> Task:
        return self.uow._stage(task)

    def delete_cascade(self, task: Task) -> None:
        if task.id is None:
            return
        self.store.histories = {i: h for i, h in self.store.histories.items() if h.task_id != task.id}
        self.store.inferences = {i: inf for i, inf in self.store.inferences.items() if inf.task_id != task.id}
        self.store.roads = {i: r for i, r in self.store.roads.items() if r.video_id != task.video_id}
        self.store.tasks.pop(task.id, None)
        self.store.videos.pop(task.video_id, None)


class _Statuses:
    def __init__(self, uow: InMemoryUnitOfWork):
        self.store = uow._store

    def get(self, status_id: str) -> TaskStatus | None:
        return self.store.statuses.get(status_id)


class _Histories:
    def __init__(self, uow: InMemoryUnitOfWork):
        self.uow = uow
        self.store = uow._store

    def get_current(self, task_id: int) -> TaskStatusHistory | None:
        open_h = [h for h in self.store.histories.values() if h.task_id == task_id and h.to_date is None]
        return open_h[-1] if open_h else None

    def previous_non_archived(self, task_id: int, archived_id: str) -> TaskStatusHistory | None:
        items = [h for h in self.store.histories.values() if h.task_id == task_id and h.status_id != archived_id]
        return items[-1] if items else None

    def add(self, history: TaskStatusHistory) -> TaskStatusHistory:
        return self.uow._stage(history)

    def delete_for_task(self, task_id: int) -> None:
        self.store.histories = {i: h for i, h in self.store.histories.items() if h.task_id != task_id}


class _Roads:
    def __init__(self, uow: InMemoryUnitOfWork):
        self.uow = uow
        self.store = uow._store

    def list_by_video(self, video_id: int) -> list[Road]:
        return [r for r in self.store.roads.values() if r.video_id == video_id]

    def add(self, road: Road) -> Road:
        return self.uow._stage(road)

    def delete(self, road: Road) -> None:
        if road.id is not None:
            self.store.roads.pop(road.id, None)

    def delete_for_video(self, video_id: int) -> None:
        self.store.roads = {i: r for i, r in self.store.roads.items() if r.video_id != video_id}


class _Inferences:
    def __init__(self, uow: InMemoryUnitOfWork):
        self.uow = uow

    def add(self, inference: Inference) -> Inference:
        return self.uow._stage(inference)

    def delete(self, inference: Inference) -> None:
        if inference.id is not None:
            self.uow._store.inferences.pop(inference.id, None)
