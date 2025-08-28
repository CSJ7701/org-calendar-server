from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .db import Base

class Placeholder(Base):
    __tablename__ = "placeholders"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

class Snapshot(Base):
    __tablename__ = "snapshots"
    id = Column(Integer, primary_key=True, index=True)
    commit_hash = Column(String, nullable=True)
    status = Column(String, default="pending")
    log = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
