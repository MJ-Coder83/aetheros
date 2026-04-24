"""AetherOS API — FastAPI application with Tape and AetherGit endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from packages.aethergit.advanced import (
    AdvancedAetherGit,
    BranchNotFoundError,
    CommitNotFoundError,
    WorktreeNotFoundError,
)
from packages.core.models import AetherCommit
from packages.prime.debate import (
    DebateAlreadyConcludedError,
    DebateArena,
    DebateFormat,
    DebateNotFoundError,
    DebateParticipant,
    DebateRoundLimitError,
    DebateStatus,
    NoParticipantsError,
)
from packages.prime.domain_creation import (
    BlueprintNotFoundError,
    BlueprintValidationError,
    CreationMode,
    DomainCreationEngine,
    DomainNotApprovedError,
    DuplicateDomainError,
)
from packages.prime.explainability import (
    ActionType,
    ExplainabilityEngine,
    ExplanationNotFoundError,
)
from packages.prime.introspection import PrimeIntrospector
from packages.prime.knowledge_transfer import (
    KnowledgeTransferEngine,
    KnowledgeTransferError,
    KnowledgeType,
    TransferStatus,
)
from packages.prime.knowledge_transfer import (
    TransferNotFoundError as KTTransferNotFoundError,
)
from packages.prime.planning import (
    CyclicDependencyError,
    FailurePolicy,
    PlanningEngine,
    PlanNotActiveError,
    PlanNotFoundError,
    PlanStatus,
    PlanStep,
    StepNotFoundError,
)
from packages.prime.proposals import ProposalEngine
from packages.tape.models import TapeEntry
from packages.tape.repository import InMemoryTapeRepository, TapeRepository
from packages.tape.schemas import TapeEntryCreate, TapeEntryRead
from packages.tape.service import TapeEntryNotFoundError, TapeService
from services.api.database import get_db

app = FastAPI(title="AetherOS API", version="0.1.0")


# ---------------------------------------------------------------------------
# Service instantiation
# For now we use the in-memory repository so the API works without Postgres.
# Swap to TapeRepository(session) when the database is available.
# ---------------------------------------------------------------------------

_tape_service = TapeService(InMemoryTapeRepository())


def _get_tape_service() -> TapeService:
    """Return the singleton TapeService instance."""
    return _tape_service


def _get_db_tape_service(db: AsyncSession = Depends(get_db)) -> TapeService:  # noqa: B008
    """Return a TapeService backed by PostgreSQL (used when DB is connected)."""
    repo = TapeRepository(db)
    return TapeService(repo)


# Type alias for injecting the in-memory TapeService via FastAPI Depends.
TapeServiceDep = Annotated[TapeService, Depends(_get_tape_service)]

# AetherGit service singleton
_aethergit_service = AdvancedAetherGit(tape_service=_tape_service)


def _get_aethergit_service() -> AdvancedAetherGit:
    """Return the singleton AdvancedAetherGit instance."""
    return _aethergit_service


AetherGitServiceDep = Annotated[AdvancedAetherGit, Depends(_get_aethergit_service)]

# Debate Arena service singleton
_debate_service = DebateArena(tape_service=_tape_service)


def _get_debate_service() -> DebateArena:
    """Return the singleton DebateArena instance."""
    return _debate_service


DebateServiceDep = Annotated[DebateArena, Depends(_get_debate_service)]

# Explainability Engine service singleton
_explainability_service = ExplainabilityEngine(tape_service=_tape_service)


def _get_explainability_service() -> ExplainabilityEngine:
    """Return the singleton ExplainabilityEngine instance."""
    return _explainability_service


ExplainabilityServiceDep = Annotated[
    ExplainabilityEngine, Depends(_get_explainability_service)
]

# Domain Creation Engine service singleton
_introspector_singleton = PrimeIntrospector(tape_service=_tape_service)
_proposal_engine_singleton = ProposalEngine(
    tape_service=_tape_service, introspector=_introspector_singleton,
)
_domain_creation_service = DomainCreationEngine(
    tape_service=_tape_service,
    introspector=_introspector_singleton,
    proposal_engine=_proposal_engine_singleton,
)


def _get_domain_creation_service() -> DomainCreationEngine:
    """Return the singleton DomainCreationEngine instance."""
    return _domain_creation_service


DomainCreationServiceDep = Annotated[
    DomainCreationEngine, Depends(_get_domain_creation_service)
]


# ---------------------------------------------------------------------------
# AetherGit request schemas
# ---------------------------------------------------------------------------


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


class StartDebateRequest(BaseModel):
    """Schema for starting a new debate."""

    topic: str
    format: DebateFormat = DebateFormat.STANDARD
    participants: list[DebateParticipant] = []
    max_rounds: int = Field(default=3, ge=1, le=20)
    description: str = ""
    initiator: str = "prime"


class RunDebateRoundRequest(BaseModel):
    """Schema for running a debate round with optional arguments."""

    # In production, arguments would come from real agents
    pass


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Tape endpoints
# ---------------------------------------------------------------------------


@app.post("/tape/log", response_model=TapeEntryRead, status_code=201)
async def log_event(
    body: TapeEntryCreate,
    svc: TapeServiceDep,
) -> TapeEntry:
    """Append a new immutable entry to the Tape."""
    entry = await svc.log_event(
        event_type=body.event_type,
        payload=body.payload,
        agent_id=body.agent_id,
        metadata=body.metadata,
        commit_id=body.commit_id,
    )
    return entry


@app.get("/tape/entries", response_model=list[TapeEntryRead])
async def get_entries(
    svc: TapeServiceDep,
    event_type: str | None = Query(None, description="Filter by event type"),
    agent_id: str | None = Query(None, description="Filter by agent ID"),
    commit_id: UUID | None = Query(None, description="Filter by AetherGit commit ID"),  # noqa: B008
    from_time: str | None = Query(None, description="ISO-8601 start timestamp"),
    to_time: str | None = Query(None, description="ISO-8601 end timestamp"),
    limit: int = Query(50, ge=1, le=1000, description="Max entries to return"),
) -> list[TapeEntry]:
    """Query Tape entries with optional filters."""
    return await svc.get_entries(
        event_type=event_type,
        agent_id=agent_id,
        commit_id=commit_id,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
    )


@app.get("/tape/entries/{entry_id}", response_model=TapeEntryRead)
async def get_entry_by_id(
    entry_id: UUID,
    svc: TapeServiceDep,
) -> TapeEntry:
    """Retrieve a single Tape entry by its ID."""
    try:
        return await svc.get_entry_by_id(entry_id)
    except TapeEntryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/tape/recent", response_model=list[TapeEntryRead])
async def get_recent_entries(
    svc: TapeServiceDep,
    limit: int = Query(50, ge=1, le=1000, description="Max entries to return"),
) -> list[TapeEntry]:
    """Return the most recent Tape entries, newest first."""
    return await svc.get_recent_entries(limit)


# ---------------------------------------------------------------------------
# AetherGit — Commit management
# ---------------------------------------------------------------------------


@app.post("/aethergit/commits", status_code=201)
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


@app.get("/aethergit/commits/{commit_id}")
async def get_commit(
    commit_id: UUID,
    svc: AetherGitServiceDep,
) -> AetherCommit:
    """Retrieve a commit by ID."""
    try:
        return svc.get_commit(commit_id)
    except CommitNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/aethergit/commits")
async def list_commits(
    svc: AetherGitServiceDep,
    branch: str | None = Query(None, description="Filter by branch name"),
    limit: int = Query(50, ge=1, le=500, description="Max commits to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[AetherCommit]:
    """List commits with optional branch filter and pagination."""
    return await svc.get_commit_history(branch=branch, limit=limit, offset=offset)


@app.get("/aethergit/branches")
async def list_branches(
    svc: AetherGitServiceDep,
) -> list[str]:
    """List all branch names."""
    return svc.store.get_branch_names()


# ---------------------------------------------------------------------------
# AetherGit — Semantic search
# ---------------------------------------------------------------------------


@app.post("/aethergit/search")
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


# ---------------------------------------------------------------------------
# AetherGit — Merge analysis
# ---------------------------------------------------------------------------


@app.post("/aethergit/merge/analyze")
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


@app.post("/aethergit/merge/resolve")
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


# ---------------------------------------------------------------------------
# AetherGit — Branch explorer
# ---------------------------------------------------------------------------


@app.get("/aethergit/branch-explorer")
async def get_branch_explorer(
    svc: AetherGitServiceDep,
) -> dict[str, object]:
    """Get the branch DAG for visual exploration."""
    dag = await svc.get_branch_explorer()
    return dag.model_dump()


# ---------------------------------------------------------------------------
# AetherGit — Worktree management
# ---------------------------------------------------------------------------


@app.post("/aethergit/worktrees", status_code=201)
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


@app.get("/aethergit/worktrees")
async def list_worktrees(
    svc: AetherGitServiceDep,
) -> list[dict[str, object]]:
    """List all managed worktrees."""
    worktrees = await svc.list_worktrees()
    return [wt.model_dump() for wt in worktrees]


@app.delete("/aethergit/worktrees/{worktree_id}")
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


# ---------------------------------------------------------------------------
# AetherGit — Commit comparison
# ---------------------------------------------------------------------------


@app.get("/aethergit/compare/{source_id}/{target_id}")
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


# ---------------------------------------------------------------------------
# Debate Arena endpoints
# ---------------------------------------------------------------------------


@app.post("/debates", status_code=201)
async def start_debate(
    body: StartDebateRequest,
    svc: DebateServiceDep,
) -> dict[str, object]:
    """Start a new structured debate."""
    try:
        debate = await svc.start_debate(
            topic=body.topic,
            format=body.format,
            participants=body.participants,
            max_rounds=body.max_rounds,
            description=body.description,
            initiator=body.initiator,
        )
        return debate.model_dump()
    except NoParticipantsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/debates/{debate_id}/round")
async def run_debate_round(
    debate_id: UUID,
    svc: DebateServiceDep,
) -> dict[str, object]:
    """Execute one round of a debate."""
    try:
        result = await svc.run_debate_round(debate_id)
        return result.model_dump()
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (DebateAlreadyConcludedError, DebateRoundLimitError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/debates/{debate_id}/conclude")
async def conclude_debate(
    debate_id: UUID,
    svc: DebateServiceDep,
) -> dict[str, object]:
    """Conclude a debate and produce a final result."""
    try:
        result = await svc.conclude_debate(debate_id)
        return result.model_dump()
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DebateAlreadyConcludedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/debates/{debate_id}/transcript")
async def get_debate_transcript(
    debate_id: UUID,
    svc: DebateServiceDep,
) -> dict[str, object]:
    """Retrieve the full debate transcript."""
    try:
        debate = await svc.get_debate_transcript(debate_id)
        return debate.model_dump()
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/debates")
async def list_debates(
    svc: DebateServiceDep,
    status: DebateStatus | None = Query(None, description="Filter by status"),  # noqa: B008
) -> list[dict[str, object]]:
    """List all debates, optionally filtered by status."""
    debates = await svc.list_debates(status=status)
    return [d.model_dump() for d in debates]


@app.post("/debates/{debate_id}/abort")
async def abort_debate(
    debate_id: UUID,
    svc: DebateServiceDep,
) -> dict[str, object]:
    """Abort a debate before its natural conclusion."""
    try:
        debate = await svc.abort_debate(debate_id)
        return debate.model_dump()
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DebateAlreadyConcludedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Explainability Dashboard request schemas
# ---------------------------------------------------------------------------


class GenerateExplanationRequest(BaseModel):
    """Schema for generating an explanation."""
    action_id: str
    action_type: ActionType
    context: dict[str, object] = Field(default_factory=dict)


class DecisionTraceRequest(BaseModel):
    """Schema for requesting a decision trace."""
    action_id: str
    action_type: ActionType | None = None
    context: dict[str, object] = Field(default_factory=dict)


class HighlightFactorsRequest(BaseModel):
    """Schema for highlighting key factors."""
    action_id: str
    action_type: ActionType | None = None
    context: dict[str, object] = Field(default_factory=dict)
    top_n: int = Field(default=5, ge=1, le=20)


class CompareAlternativesRequest(BaseModel):
    """Schema for comparing alternatives."""
    action_id: str
    alternatives: list[dict[str, object]] = []
    action_type: ActionType | None = None
    context: dict[str, object] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Explainability Dashboard endpoints
# ---------------------------------------------------------------------------


@app.post("/explain/generate", status_code=201)
async def generate_explanation(
    body: GenerateExplanationRequest,
    svc: ExplainabilityServiceDep,
) -> dict[str, object]:
    """Generate a full explanation for a system action."""
    explanation = await svc.generate_explanation(
        action_id=body.action_id,
        action_type=body.action_type,
        context=body.context,
    )
    return explanation.model_dump()


@app.post("/explain/trace")
async def get_decision_trace(
    body: DecisionTraceRequest,
    svc: ExplainabilityServiceDep,
) -> dict[str, object]:
    """Get the full decision trace for an action."""
    trace = await svc.get_decision_trace(
        action_id=body.action_id,
        action_type=body.action_type,
        context=body.context,
    )
    return trace.model_dump()


@app.post("/explain/factors")
async def highlight_key_factors(
    body: HighlightFactorsRequest,
    svc: ExplainabilityServiceDep,
) -> list[dict[str, object]]:
    """Highlight the top factors that influenced a decision."""
    factors = await svc.highlight_key_factors(
        action_id=body.action_id,
        action_type=body.action_type,
        context=body.context,
        top_n=body.top_n,
    )
    return [f.model_dump() for f in factors]


@app.post("/explain/compare")
async def compare_alternatives(
    body: CompareAlternativesRequest,
    svc: ExplainabilityServiceDep,
) -> dict[str, object]:
    """Compare alternatives and explain why the chosen option was selected."""
    comparison = await svc.compare_alternatives(
        action_id=body.action_id,
        alternatives=body.alternatives,
        action_type=body.action_type,
        context=body.context,
    )
    return comparison.model_dump()


@app.get("/explain/{explanation_id}")
async def get_explanation(
    explanation_id: UUID,
    svc: ExplainabilityServiceDep,
) -> dict[str, object]:
    """Retrieve a stored explanation by ID."""
    try:
        explanation = await svc.get_explanation(explanation_id)
        return explanation.model_dump()
    except ExplanationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/explain")
async def list_explanations(
    svc: ExplainabilityServiceDep,
    action_type: ActionType | None = Query(None, description="Filter by action type"),  # noqa: B008
) -> list[dict[str, object]]:
    """List all stored explanations, optionally filtered by action type."""
    explanations = await svc.list_explanations(action_type=action_type)
    return [e.model_dump() for e in explanations]


# Planning Engine service singleton
_planning_service = PlanningEngine(tape_service=_tape_service)

def _get_planning_service() -> PlanningEngine:
    """Return the singleton PlanningEngine instance."""
    return _planning_service


PlanningServiceDep = Annotated[PlanningEngine, Depends(_get_planning_service)]


# ---------------------------------------------------------------------------
# Planning request schemas
# ---------------------------------------------------------------------------


class CreatePlanRequest(BaseModel):
    """Schema for creating a plan."""
    goal: str
    steps: list[dict[str, object]] = []
    description: str = ""
    failure_policy: FailurePolicy = FailurePolicy.ABORT
    priority: str = "normal"
    requires_approval: bool = False
    created_by: str = "prime"


class ExecutePlanRequest(BaseModel):
    """Schema for executing a plan."""
    step_timeout: float = Field(default=30.0, ge=1.0, le=300.0)


class GeneratePlanRequest(BaseModel):
    """Schema for auto-generating a plan from a goal."""
    goal: str
    priority: str = "normal"


class ExecuteStepRequest(BaseModel):
    """Schema for executing a single plan step."""
    step_id: str
    timeout: float = Field(default=30.0, ge=1.0, le=300.0)


# ---------------------------------------------------------------------------
# Planning endpoints
# ---------------------------------------------------------------------------


@app.post("/plans", status_code=201)
async def create_plan(
    body: CreatePlanRequest,
    svc: PlanningServiceDep,
) -> dict[str, object]:
    """Create a new multi-step plan."""

    steps = [PlanStep(**s) for s in body.steps]  # type: ignore[arg-type]
    try:
        plan = await svc.create_plan(
            goal=body.goal,
            steps=steps,
            description=body.description,
            failure_policy=body.failure_policy,
            priority=body.priority,
            requires_approval=body.requires_approval,
            created_by=body.created_by,
        )
        return plan.model_dump()
    except (CyclicDependencyError, StepNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/plans/generate", status_code=201)
async def generate_plan(
    body: GeneratePlanRequest,
    svc: PlanningServiceDep,
) -> dict[str, object]:
    """Auto-generate a plan from a high-level goal."""
    try:
        plan = await svc.generate_plan_from_goal(
            goal=body.goal,
            priority=body.priority,
        )
        return plan.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/plans/{plan_id}/activate")
async def activate_plan(
    plan_id: UUID,
    svc: PlanningServiceDep,
) -> dict[str, object]:
    """Activate a draft plan."""
    try:
        plan = await svc.activate_plan(plan_id)
        return plan.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PlanNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/plans/{plan_id}/execute")
async def execute_plan(
    plan_id: UUID,
    svc: PlanningServiceDep,
    body: ExecutePlanRequest | None = None,
) -> dict[str, object]:
    """Execute all steps in a plan."""
    timeout = body.step_timeout if body else 30.0
    try:
        result = await svc.execute_plan(plan_id, step_timeout=timeout)
        return result.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PlanNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/plans/{plan_id}/abort")
async def abort_plan(
    svc: PlanningServiceDep,
    plan_id: UUID,
    reason: str | None = None,
) -> dict[str, object]:
    """Abort an active plan."""
    try:
        plan = await svc.abort_plan(plan_id, reason=reason)
        return plan.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/plans")
async def list_plans(
    svc: PlanningServiceDep,
    status: PlanStatus | None = Query(None, description="Filter by status"),  # noqa: B008
) -> list[dict[str, object]]:
    """List all plans, optionally filtered by status."""
    plans = await svc.list_plans(status=status)
    return [p.model_dump() for p in plans]


@app.get("/plans/{plan_id}")
async def get_plan(
    plan_id: UUID,
    svc: PlanningServiceDep,
) -> dict[str, object]:
    """Get a plan by ID."""
    try:
        plan = await svc.get_plan(plan_id)
        return plan.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/plans/{plan_id}/progress")
async def get_plan_progress(
    plan_id: UUID,
    svc: PlanningServiceDep,
) -> dict[str, object]:
    """Get detailed progress for a plan."""
    try:
        return await svc.get_progress(plan_id)
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/plans/{plan_id}/steps/{step_id}/skip")
async def skip_plan_step(
    svc: PlanningServiceDep,
    plan_id: UUID,
    step_id: str,
) -> dict[str, object]:
    """Skip a step in a plan."""
    try:
        step = await svc.skip_step(plan_id, step_id)
        return step.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StepNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/plans/{plan_id}/steps/{step_id}/retry")
async def retry_plan_step(
    svc: PlanningServiceDep,
    plan_id: UUID,
    step_id: str,
) -> dict[str, object]:
    """Retry a failed step."""
    try:
        result = await svc.retry_step(plan_id, step_id)
        return result.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StepNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: UUID,
    svc: PlanningServiceDep,
) -> dict[str, str]:
    """Delete a draft or aborted plan."""
    try:
        await svc.delete_plan(plan_id)
        return {"status": "deleted"}
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Domain Creation request schemas
# ---------------------------------------------------------------------------


class CreateDomainRequest(BaseModel):
    """Schema for creating a domain from a description."""
    description: str
    domain_name: str | None = None
    creation_mode: CreationMode = CreationMode.HUMAN_GUIDED
    created_by: str = "prime"


class GenerateBlueprintRequest(BaseModel):
    """Schema for generating a domain blueprint."""
    description: str
    domain_name: str | None = None
    creation_mode: CreationMode = CreationMode.HUMAN_GUIDED
    created_by: str = "prime"


class RegisterDomainRequest(BaseModel):
    """Schema for registering a domain from an approved blueprint."""
    blueprint_id: UUID
    reviewer: str | None = None


# ---------------------------------------------------------------------------
# Domain Creation endpoints
# ---------------------------------------------------------------------------


@app.post("/domains/create", status_code=201)
async def create_domain(
    body: CreateDomainRequest,
    svc: DomainCreationServiceDep,
) -> dict[str, object]:
    """Create a domain from a natural language description."""
    try:
        result = await svc.create_domain_from_description(
            description=body.description,
            domain_name=body.domain_name,
            creation_mode=body.creation_mode,
            created_by=body.created_by,
        )
        return result.model_dump()
    except BlueprintValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/domains/blueprint", status_code=201)
async def generate_blueprint(
    body: GenerateBlueprintRequest,
    svc: DomainCreationServiceDep,
) -> dict[str, object]:
    """Generate a domain blueprint without submitting a proposal."""
    try:
        blueprint = await svc.generate_domain_blueprint(
            description=body.description,
            domain_name=body.domain_name,
            creation_mode=body.creation_mode,
            created_by=body.created_by,
        )
        return blueprint.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/domains/register")
async def register_domain(
    body: RegisterDomainRequest,
    svc: DomainCreationServiceDep,
) -> dict[str, object]:
    """Register a domain after its proposal has been approved."""
    try:
        domain = await svc.register_domain(
            blueprint_id=body.blueprint_id,
            reviewer=body.reviewer,
        )
        return domain.model_dump()
    except BlueprintNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (DomainNotApprovedError, DuplicateDomainError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/domains")
async def list_domains(
    svc: DomainCreationServiceDep,
) -> list[dict[str, object]]:
    """List all registered domains."""
    domains = await svc.list_domains()
    return [d.model_dump() for d in domains]


@app.get("/domains/{domain_id}")
async def get_domain(
    domain_id: str,
    svc: DomainCreationServiceDep,
) -> dict[str, object]:
    """Retrieve a single domain by ID."""
    domain = await svc.get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' not found")
    return domain.model_dump()


@app.get("/domains/blueprints")
async def list_blueprints(
    svc: DomainCreationServiceDep,
) -> list[dict[str, object]]:
    """List all stored domain blueprints."""
    blueprints = await svc.list_blueprints()
    return [bp.model_dump() for bp in blueprints]


@app.get("/domains/blueprints/{blueprint_id}")
async def get_blueprint(
    blueprint_id: UUID,
    svc: DomainCreationServiceDep,
) -> dict[str, object]:
    """Retrieve a specific blueprint by ID."""
    try:
        blueprint = await svc.get_blueprint(blueprint_id)
        return blueprint.model_dump()
    except BlueprintNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Knowledge Transfer endpoints
# ---------------------------------------------------------------------------


def _get_knowledge_transfer_service() -> KnowledgeTransferEngine:
    return KnowledgeTransferEngine(tape_service=_get_tape_service())


KnowledgeTransferServiceDep = Annotated[
    KnowledgeTransferEngine, Depends(_get_knowledge_transfer_service)
]


class TransferKnowledgeRequest(BaseModel):
    """Request body for initiating a knowledge transfer."""

    source_domain_id: str
    target_domain_id: str
    source_metadata: dict[str, object] = Field(default_factory=dict)
    target_metadata: dict[str, object] = Field(default_factory=dict)
    knowledge_types: list[str] | None = None
    created_by: str = "prime"


class ExtractKnowledgeRequest(BaseModel):
    """Request body for extracting knowledge from a domain."""

    domain_id: str
    domain_metadata: dict[str, object] = Field(default_factory=dict)
    knowledge_types: list[str] | None = None


class AssessCompatibilityRequest(BaseModel):
    """Request body for assessing knowledge compatibility."""

    source_domain_id: str
    target_metadata: dict[str, object] = Field(default_factory=dict)
    source_metadata: dict[str, object] = Field(default_factory=dict)
    knowledge_types: list[str] | None = None


class RecommendTransfersRequest(BaseModel):
    """Request body for recommending knowledge transfers."""

    domain_id: str
    all_domain_metadata: dict[str, dict[str, object]] = Field(default_factory=dict)


@app.post("/knowledge-transfer/transfer")
async def execute_knowledge_transfer(
    body: TransferKnowledgeRequest,
    svc: KnowledgeTransferServiceDep,
) -> dict[str, object]:
    """Execute a cross-domain knowledge transfer."""
    ktypes = None
    if body.knowledge_types is not None:
        ktypes = [KnowledgeType(t) for t in body.knowledge_types]

    record = await svc.transfer_knowledge(
        source_domain_id=body.source_domain_id,
        target_domain_id=body.target_domain_id,
        source_metadata=body.source_metadata,
        target_metadata=body.target_metadata,
        knowledge_types=ktypes,
        created_by=body.created_by,
    )
    return record.model_dump()


@app.post("/knowledge-transfer/extract")
async def extract_knowledge(
    body: ExtractKnowledgeRequest,
    svc: KnowledgeTransferServiceDep,
) -> list[dict[str, object]]:
    """Extract transferable knowledge from a domain."""
    ktypes = None
    if body.knowledge_types is not None:
        ktypes = [KnowledgeType(t) for t in body.knowledge_types]

    items = await svc.extract_knowledge(
        domain_id=body.domain_id,
        domain_metadata=body.domain_metadata,
        knowledge_types=ktypes,
    )
    return [i.model_dump() for i in items]


@app.post("/knowledge-transfer/assess")
async def assess_compatibility(
    body: AssessCompatibilityRequest,
    svc: KnowledgeTransferServiceDep,
) -> list[dict[str, object]]:
    """Assess compatibility of knowledge items with a target domain."""
    ktypes = None
    if body.knowledge_types is not None:
        ktypes = [KnowledgeType(t) for t in body.knowledge_types]

    items = await svc.extract_knowledge(
        domain_id=body.source_domain_id,
        domain_metadata=body.source_metadata,
        knowledge_types=ktypes,
    )
    assessed = await svc.assess_compatibility(items, body.target_metadata)
    return [i.model_dump() for i in assessed]


@app.post("/knowledge-transfer/package")
async def create_knowledge_package(
    body: TransferKnowledgeRequest,
    svc: KnowledgeTransferServiceDep,
) -> dict[str, object]:
    """Create a knowledge package for transfer between domains."""
    ktypes = None
    if body.knowledge_types is not None:
        ktypes = [KnowledgeType(t) for t in body.knowledge_types]

    package = await svc.create_package(
        name=f"Transfer: {body.source_domain_id} -> {body.target_domain_id}",
        source_domain_id=body.source_domain_id,
        target_domain_id=body.target_domain_id,
        source_metadata=body.source_metadata,
        target_metadata=body.target_metadata,
        knowledge_types=ktypes,
    )
    return package.model_dump()


@app.get("/knowledge-transfer/transfers")
async def list_transfers(
    svc: KnowledgeTransferServiceDep,
    status: str | None = None,
) -> list[dict[str, object]]:
    """List all knowledge transfers, optionally filtered by status."""
    ts = TransferStatus(status) if status is not None else None
    records = await svc.list_transfers(status=ts)
    return [r.model_dump() for r in records]


@app.get("/knowledge-transfer/transfers/{transfer_id}")
async def get_transfer(
    transfer_id: UUID,
    svc: KnowledgeTransferServiceDep,
) -> dict[str, object]:
    """Retrieve a specific knowledge transfer by ID."""
    try:
        record = await svc.get_transfer(transfer_id)
        return record.model_dump()
    except KTTransferNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/knowledge-transfer/transfers/{transfer_id}/rollback")
async def rollback_transfer(
    transfer_id: UUID,
    svc: KnowledgeTransferServiceDep,
) -> dict[str, object]:
    """Rollback a completed or failed knowledge transfer."""
    try:
        record = await svc.rollback_transfer(transfer_id)
        return record.model_dump()
    except KTTransferNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/knowledge-transfer/recommendations")
async def recommend_transfers(
    body: RecommendTransfersRequest,
    svc: KnowledgeTransferServiceDep,
) -> list[dict[str, object]]:
    """Recommend knowledge transfers for a domain."""
    recommendations = await svc.recommend_transfers(
        domain_id=body.domain_id,
        all_domain_metadata=body.all_domain_metadata,
    )
    return recommendations


@app.get("/knowledge-transfer/packages")
async def list_packages(
    svc: KnowledgeTransferServiceDep,
) -> list[dict[str, object]]:
    """List all knowledge packages."""
    packages = await svc.list_packages()
    return [p.model_dump() for p in packages]


@app.get("/knowledge-transfer/packages/{package_id}")
async def get_package(
    package_id: UUID,
    svc: KnowledgeTransferServiceDep,
) -> dict[str, object]:
    """Retrieve a specific knowledge package by ID."""
    try:
        package = await svc.get_package(package_id)
        return package.model_dump()
    except KnowledgeTransferError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/knowledge-transfer/items")
async def list_knowledge_items(
    svc: KnowledgeTransferServiceDep,
    source_domain_id: str | None = None,
    knowledge_type: str | None = None,
) -> list[dict[str, object]]:
    """List knowledge items, optionally filtered by source domain or type."""
    kt = KnowledgeType(knowledge_type) if knowledge_type is not None else None
    items = await svc.list_knowledge_items(
        source_domain_id=source_domain_id,
        knowledge_type=kt,
    )
    return [i.model_dump() for i in items]
