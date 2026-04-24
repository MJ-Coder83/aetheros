"""AetherGit version control router."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from packages.aethergit.advanced import (
    BranchNotFoundError,
    CommitNotFoundError,
    WorktreeNotFoundError,
)
from packages.core.models import AetherCommit
from services.api.dependencies import AetherGitServiceDep

router = APIRouter(prefix="/aethergit", tags=["aethergit"])


class AddCommitRequest(BaseModel):
    """Schema for adding a commit to AetherGit."""

    author: str
    message: str
    commit_type: str
    scope: str
    branch: str = "main"
    parent_ids: list[UUID] = []
    performance_metrics: dict[str, float] = Field(default_factory=dict)
    confidence_score: float = 0.0
    tape_references: list[UUID] = []
    tree_id: UUID | None = None
    proposed_by: str | None = None
    evolution_approved: bool = False


class SemanticSearchRequest(BaseModel):
    """Schema for semantic search queries."""

    query: str
    max_results: int = Field(default=10, ge=1, le=100)
    min_score: float = Field(default=0.1, ge=0.0, le=1.0)
    search_commits: bool = True
    search_branches: bool = True


class CreateWorktreeRequest(BaseModel):
    """Schema for creating a new worktree."""

    branch: str
    path: str
    commit_id: UUID | None = None


@router.post("/commits", status_code=201)
async def add_commit(
    body: AddCommitRequest,
    svc: AetherGitServiceDep,
) -> dict[str, str]:
    """Add a new commit to AetherGit."""
    commit = AetherCommit(
        author=body.author,
        message=body.message,
        commit_type=body.commit_type,
        scope=body.scope,
        parent_ids=body.parent_ids,
        performance_metrics=body.performance_metrics,
        confidence_score=body.confidence_score,
        tape_references=body.tape_references,
        tree_id=body.tree_id,
        proposed_by=body.proposed_by,
        evolution_approved=body.evolution_approved,
    )
    svc.add_commit(commit, branch=body.branch)
    return {"id": str(commit.id), "branch": body.branch}


@router.get("/commits/{commit_id}")
async def get_commit(
    commit_id: UUID,
    svc: AetherGitServiceDep,
) -> AetherCommit:
    """Retrieve a commit by ID."""
    try:
        return svc.get_commit(commit_id)
    except CommitNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/commits")
async def list_commits(
    svc: AetherGitServiceDep,
    branch: str | None = Query(None, description="Filter by branch name"),
    limit: int = Query(50, ge=1, le=500, description="Max commits to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[AetherCommit]:
    """List commits with optional branch filter and pagination."""
    return await svc.get_commit_history(branch=branch, limit=limit, offset=offset)


@router.get("/branches")
async def list_branches(
    svc: AetherGitServiceDep,
) -> list[str]:
    """List all branch names."""
    return svc.store.get_branch_names()


@router.post("/search")
async def semantic_search(
    body: SemanticSearchRequest,
    svc: AetherGitServiceDep,
) -> dict[str, object]:
    """Search commits and branches by semantic similarity."""
    results = await svc.semantic_search(
        query=body.query,
        max_results=body.max_results,
        min_score=body.min_score,
        search_commits=body.search_commits,
        search_branches=body.search_branches,
    )
    return results.model_dump()


@router.post("/merge/analyze")
async def analyze_merge(
    source_branch: str = Query(..., description="Source branch to merge from"),
    target_branch: str = Query(..., description="Target branch to merge into"),
    svc: AetherGitServiceDep = ...,  # type: ignore[assignment]
) -> dict[str, object]:
    """Detect merge conflicts between two branches."""
    try:
        analysis = await svc.detect_merge_conflicts(source_branch, target_branch)
        return analysis.model_dump()
    except BranchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/merge/resolve")
async def resolve_merge(
    source_branch: str = Query(..., description="Source branch"),
    target_branch: str = Query(..., description="Target branch"),
    svc: AetherGitServiceDep = ...,  # type: ignore[assignment]
) -> dict[str, object]:
    """Suggest resolutions for merge conflicts between two branches."""
    try:
        analysis = await svc.detect_merge_conflicts(source_branch, target_branch)
        report = await svc.suggest_merge_resolution(analysis)
        return report.model_dump()
    except BranchNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/branch-explorer")
async def get_branch_explorer(
    svc: AetherGitServiceDep,
) -> dict[str, object]:
    """Get the branch DAG for visual exploration."""
    dag = await svc.get_branch_explorer()
    return dag.model_dump()


@router.post("/worktrees", status_code=201)
async def create_worktree(
    body: CreateWorktreeRequest,
    svc: AetherGitServiceDep,
) -> dict[str, object]:
    """Create a new git worktree."""
    worktree = await svc.create_worktree(
        branch=body.branch,
        path=body.path,
        commit_id=body.commit_id,
    )
    return worktree.model_dump()


@router.get("/worktrees")
async def list_worktrees(
    svc: AetherGitServiceDep,
) -> list[dict[str, object]]:
    """List all managed worktrees."""
    worktrees = await svc.list_worktrees()
    return [wt.model_dump() for wt in worktrees]


@router.delete("/worktrees/{worktree_id}")
async def remove_worktree(
    worktree_id: UUID,
    svc: AetherGitServiceDep,
) -> dict[str, object]:
    """Remove a git worktree."""
    try:
        worktree = await svc.remove_worktree(worktree_id)
        return worktree.model_dump()
    except WorktreeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/compare/{source_id}/{target_id}")
async def compare_commits(
    source_id: UUID,
    target_id: UUID,
    svc: AetherGitServiceDep,
) -> dict[str, object]:
    """Compare two commits and generate a rich diff."""
    try:
        diff = await svc.compare_commits(source_id, target_id)
        return diff.model_dump()
    except CommitNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
