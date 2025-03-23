from datetime import datetime, timedelta
from sqlalchemy import Column, String, TIMESTAMP, Boolean, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Link(Base):
    __tablename__ = "links"

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False)
    short = Column(String, nullable=False)  
    created_at = Column(TIMESTAMP, default=lambda: datetime.utcnow() + timedelta(hours=3))
    last_usage = Column(TIMESTAMP, nullable=True)
    cnt_usage = Column(Integer, default=0)
    expires_at = Column(TIMESTAMP, nullable=True)
    project_id = Column(Integer, ForeignKey('projects.id'))
    deleted = Column(Boolean, default=False)

    project = relationship("Project", back_populates="project_links")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    descr = Column(String, nullable=True)
    started_at = Column(TIMESTAMP, default=lambda: datetime.utcnow() + timedelta(hours=3), nullable=False)
    finished_at = Column(TIMESTAMP, nullable=True)

    project_links = relationship("Link", back_populates="project", cascade="all, delete-orphan")
