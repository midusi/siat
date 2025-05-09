from __future__ import annotations
from sqlalchemy import Column, Integer, ForeignKey, String, Float, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "user"

    id= Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, nullable=False)

class Province(Base):
    __tablename__ = "province"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class District(Base):
    __tablename__ = "district"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    province_id = Column(Integer, ForeignKey("province.id"), nullable=False)

    province = relationship("Province")

class Locality(Base):
    __tablename__ = "locality"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    district_id = Column(Integer, ForeignKey("district.id"), nullable=False)

    district = relationship("District")

class Video(Base):
    __tablename__ = "video"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    format = Column(String, nullable=False)
    url = Column(String, nullable=False)
    fps = Column(Integer, nullable=False)
    duration = Column(Float, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

class Task(Base):
    __tablename__ = "task"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    uploaded_at = Column(DateTime, nullable=False)
    video_id = Column(Integer, ForeignKey("video.id"), nullable=False)
    locality_id = Column(Integer, ForeignKey("locality.id"), nullable=False)
    
    video = relationship("Video")
    locality = relationship("Locality")

class TaskStatus(Base):
    __tablename__ = "task_status"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)

class TaskStatusHistory(Base):
    __tablename__ = "task_status_history"

    id = Column(Integer, primary_key=True)
    from_date = Column(DateTime, nullable=False)
    to_date = Column(DateTime)
    task_id = Column(Integer, ForeignKey("task.id"), nullable=False)
    status_id = Column(String, ForeignKey("task_status.id"), nullable=False)
    
    task = relationship("Task")
    task_status = relationship("TaskStatus")