"""Persistent commit store backed by PostgreSQL.

Replaces the in-memory CommitStore with a SQLAlchemy-backed implementation
so that AetherGit data survives server restarts.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.models import AetherCommit
from services.api.database import AetherCommitORM


class PersistentCommitStore:
    """PostgreSQL-backed store for AetherCommit objects and branch mappings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_commit(self, commit: AetherCommit, branch: str = "main") -> None:
        row: AetherCommitORM = AetherCommitORM(
            id=str(commit.id),
            parent_ids=[str(p) for p in commit.parent_ids],
            author=commit.author,
            timestamp=commit.timestamp,
            message=commit.message,
            commit_type=commit.commit_type,
            scope=commit.scope,
            performance_metrics={k: float(v) for k, v in commit.performance_metrics.items()},
            confidence_score=commit.confidence_score,
            tape_references=[str(t) for t in commit.tape_references],
            tree_id=str(commit.tree_id) if commit.tree_id is not None else None,
            proposed_by=commit.proposed_by,
            evolution_approved=commit.evolution_approved,
            branch=branch,
        )
        self._session.add(row)
        await self._session.flush()

    async def get_commit(self, commit_id: UUID) -> AetherCommit | None:
        result = await self._session.execute(
            select(AetherCommitORM).where(AetherCommitORM.id == str(commit_id))
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._row_to_commit(row)

    async def list_commits(
        self, branch: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[AetherCommit]:
        if branch is not None:
            stmt = (
                select(AetherCommitORM)
                .where(AetherCommitORM.branch == branch)
                .order_by(AetherCommitORM.timestamp.desc())
                .limit(limit)
                .offset(offset)
            )
        else:
            stmt = (
                select(AetherCommitORM)
                .order_by(AetherCommitORM.timestamp.desc())
                .limit(limit)
                .offset(offset)
            )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        return [self._row_to_commit(row) for row in rows]

    async def get_branch_names(self) -> list[str]:
        result = await self._session.execute(
            select(AetherCommitORM.branch).distinct()
        )
        return [str(r) for r in result.scalars().all()]

    async def get_branch_commits(self, branch: str) -> list[AetherCommit]:
        stmt = (
            select(AetherCommitORM)
            .where(AetherCommitORM.branch == branch)
            .order_by(AetherCommitORM.timestamp.asc())
        )
        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        return [self._row_to_commit(row) for row in rows]

    async def get_head(self, branch: str = "main") -> AetherCommit | None:
        stmt = (
            select(AetherCommitORM)
            .where(AetherCommitORM.branch == branch)
            .order_by(AetherCommitORM.timestamp.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return self._row_to_commit(row)

    @staticmethod
    def _row_to_commit(row: AetherCommitORM) -> AetherCommit:
        return AetherCommit(
            id=UUID(row.id),
            parent_ids=[UUID(p) for p in row.parent_ids],
            author=row.author,
            timestamp=row.timestamp,
            message=row.message,
            commit_type=row.commit_type,
            scope=row.scope,
            performance_metrics={k: float(v) for k, v in row.performance_metrics.items()}, # type: ignore
            confidence_score=row.confidence_score,
            tape_references=[UUID(t) for t in row.tape_references],
            tree_id=UUID(row.tree_id) if row.tree_id is not None else None,
            proposed_by=row.proposed_by,
            evolution_approved=row.evolution_approved,
        )
