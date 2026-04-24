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
