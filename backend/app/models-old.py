from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel
from app.schemas.user import Role

class User(SQLModel, table=True):
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password: str
    email: str
    active: bool = Field(default=True)
    first_name: str
    last_name: str
    role: Role

class Province(SQLModel, table=True):
    __tablename__ = "province"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class District(SQLModel, table=True):
    __tablename__ = "district"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    province_id: int = Field(foreign_key="province.id")


class Locality(SQLModel, table=True):
    __tablename__ = "locality"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    district_id: int = Field(foreign_key="district.id")

class TaskStatus(SQLModel, table=True):
    __tablename__ = "task_status"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class TaskStatusHistory(SQLModel, table=True):
    __tablename__ = "task_status_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    status_id: int = Field(foreign_key="task_status.id")
    from_date: datetime
    to_date: Optional[datetime]


class Task(SQLModel, table=True):
    __tablename__ = "task"

    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="video.id")
    name: str
    uploaded_at: datetime
    locality_id: int = Field(foreign_key="locality.id")


class Video(SQLModel, table=True):
    __tablename__ = "video"

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    fps: int
    duration: float
    format: str
    name: str
    width: int
    height: int


class InferenceStatus(SQLModel, table=True):
    __tablename__ = "inference_status"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class InferenceStatusHistory(SQLModel, table=True):
    __tablename__ = "inference_status_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    inference_id: int = Field(foreign_key="inference.id")
    status_id: int = Field(foreign_key="inference_status.id")
    from_date: datetime
    to_date: Optional[datetime]


class Inference(SQLModel, table=True):
    __tablename__ = "inference"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(foreign_key="task.id")
    url_transition_counts: str
    url_transition_undetermined: str
    url_video_processed: str
    inferred_at: datetime


class VehicleType(SQLModel, table=True):
    __tablename__ = "vehicle_type"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str


class Route(SQLModel, table=True):
    __tablename__ = "route"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: str  # 'national' or 'provincial'


class Road(SQLModel, table=True):
    __tablename__ = "road"

    id: Optional[int] = Field(default=None, primary_key=True)
    route_id: int = Field(foreign_key="route.id")
    direction: str
    polygon: str
    number: int
    video_id: int = Field(foreign_key="video.id")


class Vehicle(SQLModel, table=True):
    __tablename__ = "vehicle"

    id: Optional[int] = Field(default=None, primary_key=True)
    inference_id: int = Field(foreign_key="inference.id")
    vehicle_type_id: int = Field(foreign_key="vehicle_type.id")
    entry_road_id: int = Field(foreign_key="road.id")
    exit_road_id: int = Field(foreign_key="road.id")


class VehicleDetail(SQLModel, table=True):
    __tablename__ = "vehicle_detail"

    id: Optional[int] = Field(default=None, primary_key=True)
    vehicle_id: int = Field(foreign_key="vehicle.id")
    frame_number: int
    track_id: int
    x1: float
    y1: float
    x2: float
    y2: float
