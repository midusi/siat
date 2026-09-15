from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class User:
    username: str
    password: str
    email: str
    first_name: str
    last_name: str
    role: str
    active: bool = True
    refresh_token_version: int = 0
    id: int | None = None


@dataclass
class Province:
    name: str
    id: int | None = None


@dataclass
class District:
    name: str
    province_id: int
    id: int | None = None


@dataclass
class Locality:
    name: str
    district_id: int
    id: int | None = None
    district: District | None = None


@dataclass
class Video:
    name: str
    format: str
    url: str
    fps: int
    duration: float
    width: int
    height: int
    id: int | None = None


@dataclass
class TaskStatus:
    id: str
    name: str


@dataclass
class TaskStatusHistory:
    from_date: datetime
    task_id: int
    status_id: str
    to_date: datetime | None = None
    id: int | None = None
    status_name: str | None = None


@dataclass
class Road:
    name: str
    polygon: Any
    direction: str
    video_id: int
    id: int | None = None


@dataclass
class Inference:
    task_id: int
    transition_counts: Any
    transition_undetermined: Any
    transition_determined: Any
    url_data_obj_history: str
    url_video_processed: str
    inferred_at: datetime
    id: int | None = None


@dataclass
class Task:
    name: str
    date: datetime
    created_at: datetime
    video_id: int
    locality_id: int
    id: int | None = None
    video: Video | None = None
    locality: Locality | None = None
    inference: Inference | None = None
    status_history: list[TaskStatusHistory] = field(default_factory=list)
    current_status_id: str | None = None
    current_status_name: str | None = None
