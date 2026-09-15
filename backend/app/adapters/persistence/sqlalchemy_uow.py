from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app import models as m
from app.adapters.persistence.identity import IdentityMap
from app.adapters.persistence import mappers as map_
from app.crud import user as user_crud
from app.crud import province as province_crud
from app.crud import district as district_crud
from app.crud import locality as locality_crud
from app.crud import task as task_crud
from app.crud import task_status as task_status_crud
from app.crud import task_status_history as history_crud
from app.crud import road as road_crud
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


class _Repo:
    def __init__(self, session: Session, identity: IdentityMap):
        self.session = session
        self.identity = identity

    def _track(self, domain, orm):
        self.identity.remember(domain, orm)
        return domain


class SqlUserRepository(_Repo):
    def get(self, user_id: int) -> User | None:
        orm = user_crud.find_one_by_fields(self.session, id=user_id)
        return self._track(map_.user_to_domain(orm), orm) if orm else None

    def get_by_username(self, username: str) -> User | None:
        orm = user_crud.find_one_by_fields(self.session, username=username)
        return self._track(map_.user_to_domain(orm), orm) if orm else None

    def get_by_username_or_email(self, username: str, email: str) -> User | None:
        orm = user_crud.get_by_username_email(self.session, username, email)
        return self._track(map_.user_to_domain(orm), orm) if orm else None

    def find_by_identifier(self, identifier: str) -> User | None:
        orm = user_crud.find_one_by_fields(self.session, username=identifier) or user_crud.find_one_by_fields(
            self.session, email=identifier
        )
        return self._track(map_.user_to_domain(orm), orm) if orm else None

    def list_all(self, **filters) -> list[User]:
        orms = user_crud.find_by_fields(self.session, **filters)
        return [self._track(map_.user_to_domain(o), o) for o in orms]

    def add(self, user: User) -> User:
        orm = m.User(
            username=user.username,
            password=user.password,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            active=user.active,
            refresh_token_version=user.refresh_token_version,
        )
        self.session.add(orm)
        return self._track(user, orm)

    def delete(self, user: User) -> None:
        orm = self.identity.orm_for(user)
        if orm is not None:
            self.session.delete(orm)
            self.identity.drop(user)


class SqlProvinceRepository(_Repo):
    def list_all(self, **filters) -> list[Province]:
        orms = province_crud.find_by_fields(self.session, **filters) or []
        return [map_.province_to_domain(o) for o in orms]


class SqlDistrictRepository(_Repo):
    def list_all(self, **filters) -> list[District]:
        orms = district_crud.find_by_fields(self.session, **filters) or []
        return [map_.district_to_domain(o) for o in orms]


class SqlLocalityRepository(_Repo):
    def get(self, locality_id: int) -> Locality | None:
        orm = locality_crud.find_one_by_fields(self.session, id=locality_id)
        return map_.locality_to_domain(orm) if orm else None

    def list_all(self) -> list[Locality]:
        return [map_.locality_to_domain(o) for o in locality_crud.find_all(self.session)]

    def list_by_district(self, district_id: int) -> list[Locality]:
        return [
            map_.locality_to_domain(o)
            for o in locality_crud.get_localities_by_district(self.session, district_id)
        ]


class SqlVideoRepository(_Repo):
    def add(self, video: Video) -> Video:
        orm = m.Video(
            name=video.name,
            format=video.format,
            url=video.url,
            fps=video.fps,
            duration=video.duration,
            width=video.width,
            height=video.height,
        )
        self.session.add(orm)
        return self._track(video, orm)

    def delete(self, video: Video) -> None:
        orm = self.identity.orm_for(video)
        if orm is None and video.id is not None:
            orm = self.session.query(m.Video).filter_by(id=video.id).first()
        if orm is not None:
            self.session.delete(orm)
            self.identity.drop(video)


class SqlTaskRepository(_Repo):
    def _load(self, orm: m.Task | None) -> Task | None:
        if orm is None:
            return None
        domain = map_.task_to_domain(orm)
        self._track(domain, orm)
        if orm.video is not None and domain.video is not None:
            self.identity.remember(domain.video, orm.video)
        if orm.inference is not None and domain.inference is not None:
            self.identity.remember(domain.inference, orm.inference)
        for hist_d, hist_o in zip(domain.status_history, orm.status_history or []):
            self.identity.remember(hist_d, hist_o)
        return domain

    def get(self, task_id: int) -> Task | None:
        orm = (
            self.session.query(m.Task)
            .options(
                joinedload(m.Task.video),
                joinedload(m.Task.locality).joinedload(m.Locality.district),
                joinedload(m.Task.status_history).joinedload(m.TaskStatusHistory.task_status),
                joinedload(m.Task.inference),
            )
            .filter_by(id=task_id)
            .first()
        )
        return self._load(orm)

    def list_active(self) -> list[Task]:
        return [self._load(o) for o in task_crud.find_all_active(self.session)]

    def list_archived(self) -> list[Task]:
        return [self._load(o) for o in task_crud.find_all_archived(self.session)]

    def list_by_status(self, status_id: str) -> list[Task]:
        return [self._load(o) for o in (task_crud.find_by_fields(self.session, status_id=status_id) or [])]

    def add(self, task: Task) -> Task:
        orm = m.Task(
            name=task.name,
            date=task.date,
            created_at=task.created_at,
            video_id=task.video_id,
            locality_id=task.locality_id,
        )
        self.session.add(orm)
        return self._track(task, orm)

    def delete_cascade(self, task: Task) -> None:
        orm = self.identity.orm_for(task) or self.session.query(m.Task).filter_by(id=task.id).first()
        if orm is None:
            return
        self.session.query(m.TaskStatusHistory).filter(m.TaskStatusHistory.task_id == orm.id).delete(
            synchronize_session=False
        )
        if orm.inference:
            self.session.delete(orm.inference)
        self.session.query(m.Road).filter(m.Road.video_id == orm.video_id).delete(synchronize_session=False)
        video = orm.video
        self.session.delete(orm)
        if video is not None:
            self.session.delete(video)
        self.identity.drop(task)


class SqlTaskStatusRepository(_Repo):
    def get(self, status_id: str) -> TaskStatus | None:
        orm = task_status_crud.find_one_by_fields(self.session, id=status_id)
        if not orm:
            return None
        return TaskStatus(id=orm.id, name=orm.name)


class SqlStatusHistoryRepository(_Repo):
    def get_current(self, task_id: int) -> TaskStatusHistory | None:
        orm = history_crud.get_current_by_task(self.session, task_id)
        return self._track(map_.history_to_domain(orm), orm) if orm else None

    def previous_non_archived(self, task_id: int, archived_id: str) -> TaskStatusHistory | None:
        orm = (
            self.session.query(m.TaskStatusHistory)
            .filter(m.TaskStatusHistory.task_id == task_id, m.TaskStatusHistory.status_id != archived_id)
            .order_by(m.TaskStatusHistory.id.desc())
            .first()
        )
        return self._track(map_.history_to_domain(orm), orm) if orm else None

    def add(self, history: TaskStatusHistory) -> TaskStatusHistory:
        orm = m.TaskStatusHistory(
            from_date=history.from_date,
            to_date=history.to_date,
            task_id=history.task_id,
            status_id=history.status_id,
        )
        self.session.add(orm)
        return self._track(history, orm)

    def delete_for_task(self, task_id: int) -> None:
        self.session.query(m.TaskStatusHistory).filter(m.TaskStatusHistory.task_id == task_id).delete(
            synchronize_session=False
        )


class SqlRoadRepository(_Repo):
    def list_by_video(self, video_id: int) -> list[Road]:
        orms = road_crud.find_by_fields(self.session, video_id=video_id) or []
        return [self._track(map_.road_to_domain(o), o) for o in orms]

    def add(self, road: Road) -> Road:
        orm = m.Road(
            name=road.name,
            polygon=road.polygon,
            direction=road.direction,
            video_id=road.video_id,
        )
        self.session.add(orm)
        return self._track(road, orm)

    def delete(self, road: Road) -> None:
        orm = self.identity.orm_for(road)
        if orm is not None:
            self.session.delete(orm)
            self.identity.drop(road)

    def delete_for_video(self, video_id: int) -> None:
        self.session.query(m.Road).filter(m.Road.video_id == video_id).delete(synchronize_session=False)


class SqlInferenceRepository(_Repo):
    def add(self, inference: Inference) -> Inference:
        orm = m.Inference(
            task_id=inference.task_id,
            transition_counts=inference.transition_counts,
            transition_undetermined=inference.transition_undetermined,
            transition_determined=inference.transition_determined,
            url_data_obj_history=inference.url_data_obj_history,
            url_video_processed=inference.url_video_processed,
            inferred_at=inference.inferred_at,
        )
        self.session.add(orm)
        return self._track(inference, orm)

    def delete(self, inference: Inference) -> None:
        orm = self.identity.orm_for(inference)
        if orm is not None:
            self.session.delete(orm)
            self.identity.drop(inference)


_WRITE_BACK = {
    User: map_.apply_user,
    Video: map_.apply_video,
    Task: map_.apply_task,
    TaskStatusHistory: map_.apply_history,
    Road: map_.apply_road,
    Inference: map_.apply_inference,
}


class SqlAlchemyUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.identity = IdentityMap()
        self.users = SqlUserRepository(session, self.identity)
        self.provinces = SqlProvinceRepository(session, self.identity)
        self.districts = SqlDistrictRepository(session, self.identity)
        self.localities = SqlLocalityRepository(session, self.identity)
        self.videos = SqlVideoRepository(session, self.identity)
        self.tasks = SqlTaskRepository(session, self.identity)
        self.task_statuses = SqlTaskStatusRepository(session, self.identity)
        self.status_histories = SqlStatusHistoryRepository(session, self.identity)
        self.roads = SqlRoadRepository(session, self.identity)
        self.inferences = SqlInferenceRepository(session, self.identity)

    def _write_back(self) -> None:
        for domain, orm in self.identity.pairs():
            apply = _WRITE_BACK.get(type(domain))
            if apply:
                apply(orm, domain)

    def flush(self) -> None:
        self._write_back()
        self.session.flush()
        self.identity.sync_pks()

    def commit(self) -> None:
        self._write_back()
        self.session.commit()
        self.identity.sync_pks()

    def rollback(self) -> None:
        self.session.rollback()

    def refresh(self, entity) -> None:
        orm = self.identity.orm_for(entity)
        if orm is not None:
            self.session.refresh(orm)
            self.identity.sync_pks()

    def expire_all(self) -> None:
        self.session.expire_all()
