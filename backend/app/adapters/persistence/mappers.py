from __future__ import annotations

from app.domain import entities as d
from app import models as m


def user_to_domain(orm: m.User) -> d.User:
    return d.User(
        id=orm.id,
        username=orm.username,
        password=orm.password,
        email=orm.email,
        first_name=orm.first_name,
        last_name=orm.last_name,
        role=orm.role,
        active=bool(orm.active),
        refresh_token_version=orm.refresh_token_version or 0,
    )


def apply_user(orm: m.User, domain: d.User) -> None:
    orm.username = domain.username
    orm.password = domain.password
    orm.email = domain.email
    orm.first_name = domain.first_name
    orm.last_name = domain.last_name
    orm.role = domain.role
    orm.active = domain.active
    orm.refresh_token_version = domain.refresh_token_version


def province_to_domain(orm: m.Province) -> d.Province:
    return d.Province(id=orm.id, name=orm.name)


def district_to_domain(orm: m.District) -> d.District:
    return d.District(id=orm.id, name=orm.name, province_id=orm.province_id)


def locality_to_domain(orm: m.Locality) -> d.Locality:
    district = district_to_domain(orm.district) if getattr(orm, "district", None) else None
    return d.Locality(
        id=orm.id,
        name=orm.name,
        district_id=orm.district_id,
        district=district,
    )


def video_to_domain(orm: m.Video | None) -> d.Video | None:
    if orm is None:
        return None
    return d.Video(
        id=orm.id,
        name=orm.name,
        format=orm.format,
        url=orm.url,
        fps=orm.fps,
        duration=orm.duration,
        width=orm.width,
        height=orm.height,
    )


def apply_video(orm: m.Video, domain: d.Video) -> None:
    orm.name = domain.name
    orm.format = domain.format
    orm.url = domain.url
    orm.fps = domain.fps
    orm.duration = domain.duration
    orm.width = domain.width
    orm.height = domain.height


def inference_to_domain(orm: m.Inference | None) -> d.Inference | None:
    if orm is None:
        return None
    return d.Inference(
        id=orm.id,
        task_id=orm.task_id,
        transition_counts=orm.transition_counts,
        transition_undetermined=orm.transition_undetermined,
        transition_determined=orm.transition_determined,
        url_data_obj_history=orm.url_data_obj_history,
        url_video_processed=orm.url_video_processed,
        inferred_at=orm.inferred_at,
    )


def apply_inference(orm: m.Inference, domain: d.Inference) -> None:
    orm.task_id = domain.task_id
    orm.transition_counts = domain.transition_counts
    orm.transition_undetermined = domain.transition_undetermined
    orm.transition_determined = domain.transition_determined
    orm.url_data_obj_history = domain.url_data_obj_history
    orm.url_video_processed = domain.url_video_processed
    orm.inferred_at = domain.inferred_at


def history_to_domain(orm: m.TaskStatusHistory) -> d.TaskStatusHistory:
    status_name = orm.task_status.name if getattr(orm, "task_status", None) else None
    return d.TaskStatusHistory(
        id=orm.id,
        from_date=orm.from_date,
        to_date=orm.to_date,
        task_id=orm.task_id,
        status_id=orm.status_id,
        status_name=status_name,
    )


def apply_history(orm: m.TaskStatusHistory, domain: d.TaskStatusHistory) -> None:
    orm.from_date = domain.from_date
    orm.to_date = domain.to_date
    orm.task_id = domain.task_id
    orm.status_id = domain.status_id


def road_to_domain(orm: m.Road) -> d.Road:
    return d.Road(
        id=orm.id,
        name=orm.name,
        polygon=orm.polygon,
        direction=str(orm.direction),
        video_id=orm.video_id,
    )


def apply_road(orm: m.Road, domain: d.Road) -> None:
    orm.name = domain.name
    orm.polygon = domain.polygon
    orm.direction = domain.direction
    orm.video_id = domain.video_id


def task_to_domain(orm: m.Task) -> d.Task:
    history = list(orm.status_history or [])
    current = history[0] if history else None
    return d.Task(
        id=orm.id,
        name=orm.name,
        date=orm.date,
        created_at=orm.created_at,
        video_id=orm.video_id,
        locality_id=orm.locality_id,
        video=video_to_domain(getattr(orm, "video", None)),
        locality=locality_to_domain(orm.locality) if getattr(orm, "locality", None) else None,
        inference=inference_to_domain(getattr(orm, "inference", None)),
        status_history=[history_to_domain(h) for h in history],
        current_status_id=current.status_id if current else None,
        current_status_name=current.task_status.name if current and getattr(current, "task_status", None) else None,
    )


def apply_task(orm: m.Task, domain: d.Task) -> None:
    orm.name = domain.name
    orm.date = domain.date
    orm.created_at = domain.created_at
    orm.video_id = domain.video_id
    orm.locality_id = domain.locality_id
