"""InkosAI database setup — async SQLAlchemy with PostgreSQL."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

DATABASE_URL = "postgresql+asyncpg://inkosai:inkosai@localhost:5432/inkosai"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=20, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


# ---------------------------------------------------------------------------
# Tape ORM model (defined here to avoid circular imports with packages.tape)
# ---------------------------------------------------------------------------


class TapeEntryORM(Base):
    """SQLAlchemy ORM mapping for the ``tape_entries`` table."""

    __tablename__ = "tape_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(UTC), index=True)
    event_type: Mapped[str] = mapped_column(String(255), index=True)
    agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSON, default=dict)
    commit_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


# ---------------------------------------------------------------------------
# AetherCommit ORM model
# ---------------------------------------------------------------------------


class AetherCommitORM(Base):
    """SQLAlchemy ORM mapping for the ``aether_commits`` table."""

    __tablename__ = "aether_commits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parent_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    author: Mapped[str] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(UTC), index=True)
    message: Mapped[str] = mapped_column(Text)
    commit_type: Mapped[str] = mapped_column(String(100))
    scope: Mapped[str] = mapped_column(String(255))
    performance_metrics: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    tape_references: Mapped[list[str]] = mapped_column(JSON, default=list)
    tree_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    proposed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evolution_approved: Mapped[bool] = mapped_column(default=False)
    branch: Mapped[str] = mapped_column(String(255), default="main", index=True)


# ---------------------------------------------------------------------------
# Branch mapping ORM model
# ---------------------------------------------------------------------------


class BranchMappingORM(Base):
    """SQLAlchemy ORM mapping for branch → commit relationships."""

    __tablename__ = "branch_mappings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    branch: Mapped[str] = mapped_column(String(255), index=True)
    commit_id: Mapped[str] = mapped_column(String(36), index=True)
    position: Mapped[int] = mapped_column(default=0)


# ---------------------------------------------------------------------------
# Provider settings ORM model
# ---------------------------------------------------------------------------


class ProviderSettingsORM(Base):
    """SQLAlchemy ORM mapping for provider settings."""

    __tablename__ = "provider_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider_id: Mapped[str] = mapped_column(String(255), index=True)
    encrypted_api_key: Mapped[str] = mapped_column(Text)
    selected_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# User ORM model for Authentication
# ---------------------------------------------------------------------------


class UserORM(Base):
    """SQLAlchemy ORM mapping for users table."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False, default="")
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(UTC))
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Refresh Token ORM model
# ---------------------------------------------------------------------------


class RefreshTokenORM(Base):
    """SQLAlchemy ORM mapping for refresh tokens (allows revocation)."""

    __tablename__ = "refresh_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(UTC))


async def get_db() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency that yields an async database session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables defined on the Base metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
