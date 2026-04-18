"""SQLAlchemy ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from src.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("Resume", back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    filename = Column(String, nullable=True)
    raw_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")
    optimization_runs = relationship("OptimizationRun", back_populates="resume")


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=True)
    job_description = Column(Text, nullable=False)
    status = Column(String, default="queued")  # queued | running | completed | failed
    celery_job_id = Column(String, nullable=True, index=True)
    result_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    resume = relationship("Resume", back_populates="optimization_runs")


class ProfileSyncState(Base):
    """Tracks OAuth connection state and last-sync cursor per user per platform."""

    __tablename__ = "profile_sync_state"

    id             = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id        = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    platform       = Column(String(20), nullable=False)          # 'github' | 'linkedin'
    last_sync_at   = Column(DateTime, nullable=True)
    access_token   = Column(Text, nullable=True)                  # stored encrypted
    sync_cursor    = Column(String, nullable=True)
    staleness_score = Column(Float, default=1.0)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SyncDelta(Base):
    """A single detected profile update awaiting review/application."""

    __tablename__ = "sync_deltas"

    id               = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id          = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    platform         = Column(String(20), nullable=False)
    item_type        = Column(String(30), nullable=False)        # 'repository' | 'role' | 'skill' | 'certification'
    title            = Column(Text, nullable=False)
    description      = Column(Text, nullable=True)
    relevance_score  = Column(Float, nullable=True)
    suggested_section = Column(String(50), nullable=True)        # 'Experience' | 'Projects' | 'Skills'
    raw_data         = Column(JSON, nullable=True)
    applied          = Column(Boolean, default=False)
    detected_at      = Column(DateTime, default=datetime.utcnow)
    applied_at       = Column(DateTime, nullable=True)


class CollabSession(Base):
    """Collaborative review session — links a job_id to a shared review token."""

    __tablename__ = "collab_sessions"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id       = Column(String, nullable=False, index=True)
    owner_id     = Column(String, nullable=False)
    shared_token = Column(String, unique=True, nullable=False, index=True)
    created_at   = Column(DateTime, default=datetime.utcnow)


class MentorAnnotation(Base):
    """A comment/annotation left by a mentor on a specific bullet."""

    __tablename__ = "mentor_annotations"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("collab_sessions.id"), nullable=False, index=True)
    bullet_id  = Column(String, nullable=False)
    author_id  = Column(String, nullable=False)
    role       = Column(String(20), default="commenter")         # 'viewer' | 'commenter' | 'editor'
    source     = Column(String(10), default="mentor")            # 'mentor' | 'ai'
    text       = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
