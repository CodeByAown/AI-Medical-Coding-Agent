from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer,
    String, Text, JSON, ForeignKey, Index,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

from app.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


# ─── Auth / User Tables ───────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="coder")
    full_name = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_user_email", "email"),
        Index("ix_user_role", "role"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # user_id is stored as string to support both DB user IDs and non-DB values
    # (e.g., "anonymous", "dev-user", "api-key-service")
    # No FK constraint — audit log must never fail due to referential integrity issues
    user_id = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_audit_action", "action"),
        Index("ix_audit_created", "created_at"),
        Index("ix_audit_user", "user_id"),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_refresh_token_hash", "token_hash"),
        Index("ix_refresh_user", "user_id"),
    )


# ─── Coding Tables ────────────────────────────────────────────────────────────

class CodingSession(Base):
    __tablename__ = "coding_sessions"

    id = Column(String(36), primary_key=True)
    # User association (nullable for backward compat with pre-auth sessions)
    user_id = Column(String(100), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    document_type = Column(String(50), nullable=False)
    specialty = Column(String(50), nullable=False)
    patient_id = Column(String(100), nullable=True, index=True)
    encounter_id = Column(String(100), nullable=True, index=True)
    clinical_text = Column(Text, nullable=False)
    phi_encrypted = Column(Boolean, default=False, nullable=False)
    soap_json = Column(JSON, nullable=True)
    extracted_entities_json = Column(JSON, nullable=True)
    model_used = Column(String(100), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    summary = Column(Text, nullable=True)
    requires_human_review = Column(Boolean, default=False)
    review_reason = Column(Text, nullable=True)
    reviewer_id = Column(String(100), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    codes = relationship("AssignedCode", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_session_created", "created_at"),
        Index("ix_session_status_created", "status", "created_at"),
        Index("ix_session_user_id", "user_id"),
    )


class AssignedCode(Base):
    __tablename__ = "assigned_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("coding_sessions.id"), nullable=False, index=True)
    code = Column(String(20), nullable=False, index=True)
    code_type = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    is_primary = Column(Boolean, default=False)
    evidence = Column(Text, nullable=True)
    modifiers = Column(JSON, nullable=True)
    status = Column(String(20), default="suggested")
    hierarchy = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("CodingSession", back_populates="codes")

    __table_args__ = (
        Index("ix_code_type", "code_type"),
        Index("ix_assigned_code", "code"),
    )


class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code_type = Column(String(20), nullable=False)
    total_codes = Column(Integer, nullable=False)
    indexed_at = Column(DateTime, default=datetime.utcnow)
    version = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)


# ─── Database Engine & Session Factory ───────────────────────────────────────

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# Keep legacy alias for backward compat
AsyncSessionLocal = async_session_maker


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Context manager variant for use outside route handlers (e.g., lifespan)
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_async_session():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
