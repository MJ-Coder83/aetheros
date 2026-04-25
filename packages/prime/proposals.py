"""Prime Proposals — Self-Modification Proposals for the Prime meta-agent.

This module enables Prime to intelligently propose changes to the system based
on introspection data, Tape history, performance metrics, and user goals.

Governance model:
- Every proposal is immutable once created ( Tape-logged )
- Proposals start in ``pending_approval`` status
- A human (or authorised agent) must explicitly approve or reject
- Approved proposals can be implemented; rejected ones are archived
- All state transitions are logged to the Tape for full auditability

Usage::

    from packages.prime.proposals import ProposalEngine

    engine = ProposalEngine(tape_service=tape_svc, introspector=introspector)
    proposal = await engine.propose(
        title="Add retry logic to TapeService",
        modification_type=ModificationType.BEHAVIOR_CHANGE,
        description="Wrap Tape writes in exponential backoff retry",
        reasoning="Tape entries are being lost during transient DB failures",
        expected_impact="Higher write reliability at the cost of latency spikes",
        risk_level=RiskLevel.LOW,
        implementation_steps=["Add tenacity dependency", "Wrap log_event"],
    )
    # proposal.status == ProposalStatus.PENDING_APPROVAL
    approved = await engine.approve(proposal.id, reviewer="human-001")
"""

import contextlib
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.prime.intelligence_profile import IntelligenceProfileEngine, InteractionType
from packages.prime.introspection import PrimeIntrospector
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ModificationType(StrEnum):
    """What kind of system change the proposal targets."""

    SKILL_ADDITION = "skill_addition"
    SKILL_MODIFICATION = "skill_modification"
    AGENT_RECONFIGURATION = "agent_reconfiguration"
    BEHAVIOR_CHANGE = "behavior_change"
    CONFIGURATION_UPDATE = "configuration_update"
    ARCHITECTURE_CHANGE = "architecture_change"
    SELF_MODIFICATION = "self_modification"
    DOMAIN_CREATION = "domain_creation"


class RiskLevel(StrEnum):
    """Risk assessment for a proposal."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProposalStatus(StrEnum):
    """Lifecycle states for a modification proposal.

    State machine::

        PENDING_APPROVAL ──► APPROVED ──► IMPLEMENTED
              │
              └────────────► REJECTED
    """

    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class Proposal(BaseModel):
    """A single self-modification proposal created by Prime.

    Proposals are immutable records — once created, their core fields cannot
    change. Only the ``status`` field transitions through the lifecycle.
    """

    id: UUID = Field(default_factory=uuid4)
    title: str
    modification_type: ModificationType
    description: str
    reasoning: str
    expected_impact: str
    risk_level: RiskLevel
    implementation_steps: list[str]
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    status: ProposalStatus = ProposalStatus.PENDING_APPROVAL
    proposed_by: str = "prime"
    reviewer: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviewed_at: datetime | None = None
    introspection_snapshot_id: str | None = None
    parent_proposal_id: UUID | None = None
    folder_operations: list[dict[str, object]] = []  # Folder tree ops for this proposal


class ProposalSummary(BaseModel):
    """Lightweight summary of a proposal for list views and API responses."""

    id: UUID
    title: str
    modification_type: ModificationType
    risk_level: RiskLevel
    confidence_score: float
    status: ProposalStatus
    proposed_by: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ProposalError(Exception):
    """Base exception for proposal operations."""


class ProposalNotFoundError(ProposalError):
    """Raised when a requested proposal does not exist."""


class ProposalTransitionError(ProposalError):
    """Raised when an invalid state transition is attempted."""


# ---------------------------------------------------------------------------
# In-memory proposal store (will be backed by Postgres later)
# ---------------------------------------------------------------------------


class ProposalStore:
    """In-memory store for modification proposals.

    Provides lookup by ID and filtering by status. Will be replaced by a
    PostgreSQL-backed repository once the ORM layer is in place.
    """

    def __init__(self) -> None:
        self._proposals: dict[UUID, Proposal] = {}

    def add(self, proposal: Proposal) -> None:
        self._proposals[proposal.id] = proposal

    def get(self, proposal_id: UUID) -> Proposal | None:
        return self._proposals.get(proposal_id)

    def list_all(self) -> list[Proposal]:
        return list(self._proposals.values())

    def list_by_status(self, status: ProposalStatus) -> list[Proposal]:
        return [p for p in self._proposals.values() if p.status == status]

    def update(self, proposal: Proposal) -> None:
        """Replace the stored proposal with the updated version."""
        if proposal.id not in self._proposals:
            raise ProposalNotFoundError(f"Proposal {proposal.id} not found")
        self._proposals[proposal.id] = proposal


# ---------------------------------------------------------------------------
# Allowed state transitions
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: dict[ProposalStatus, set[ProposalStatus]] = {
    ProposalStatus.PENDING_APPROVAL: {ProposalStatus.APPROVED, ProposalStatus.REJECTED},
    ProposalStatus.APPROVED: {ProposalStatus.IMPLEMENTED},
    ProposalStatus.REJECTED: set(),
    ProposalStatus.IMPLEMENTED: set(),
}


def _validate_transition(current: ProposalStatus, target: ProposalStatus) -> None:
    """Raise ProposalTransitionError if the transition is not allowed."""
    allowed = _VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ProposalTransitionError(
            f"Cannot transition proposal from {current.value} to {target.value}"
        )


# ---------------------------------------------------------------------------
# ProposalEngine — the main public API
# ---------------------------------------------------------------------------


class ProposalEngine:
    """Engine for creating, reviewing, and managing self-modification proposals.

    ProposalEngine is the single entry point for the Prime Console (and future
    API endpoints) to interact with the proposal system. It ensures:

    - Every proposal is logged to the Tape
    - State transitions follow the governance model
    - Introspection data is captured at proposal-creation time

    Usage::

        engine = ProposalEngine(tape_service=svc, introspector=introspector)

        # Prime creates a proposal
        proposal = await engine.propose(...)

        # Human reviews and approves
        approved = await engine.approve(proposal.id, reviewer="alice")

        # Mark as implemented once the change is deployed
        done = await engine.mark_implemented(proposal.id)
    """

    def __init__(
        self,
        tape_service: TapeService,
        introspector: PrimeIntrospector | None = None,
        store: ProposalStore | None = None,
        profile_engine: IntelligenceProfileEngine | None = None,
    ) -> None:
        self._tape = tape_service
        self._introspector = introspector
        self._store = store or ProposalStore()
        self._profile_engine = profile_engine

    # ------------------------------------------------------------------
    # Create proposals
    # ------------------------------------------------------------------

    async def propose(
        self,
        title: str,
        modification_type: ModificationType,
        description: str,
        reasoning: str,
        expected_impact: str,
        risk_level: RiskLevel,
        implementation_steps: list[str],
        confidence_score: float = 0.0,
        proposed_by: str = "prime",
        parent_proposal_id: UUID | None = None,
        folder_operations: list[dict[str, object]] | None = None,
    ) -> Proposal:
        """Create a new self-modification proposal.

        The proposal starts in ``PENDING_APPROVAL`` status. All core fields
        are captured immutably. The creation event is logged to the Tape.

        If an introspector is available, a system snapshot is taken at
        proposal-creation time and its timestamp is recorded so that the
        decision context can be reconstructed later.
        """
        snapshot_id: str | None = None
        if self._introspector is not None:
            snapshot = await self._introspector.snapshot()
            snapshot_id = snapshot.timestamp.isoformat()

        # Compute confidence score if not explicitly provided
        computed_confidence = confidence_score
        if computed_confidence == 0.0 and self._introspector is not None:
            computed_confidence = await self._estimate_confidence(
                risk_level=risk_level,
                modification_type=modification_type,
            )

        proposal = Proposal(
            title=title,
            modification_type=modification_type,
            description=description,
            reasoning=reasoning,
            expected_impact=expected_impact,
            risk_level=risk_level,
            implementation_steps=implementation_steps,
            confidence_score=computed_confidence,
            proposed_by=proposed_by,
            introspection_snapshot_id=snapshot_id,
            parent_proposal_id=parent_proposal_id,
            folder_operations=folder_operations or [],
        )

        self._store.add(proposal)

        await self._tape.log_event(
            event_type="prime.proposal_created",
            payload={
                "proposal_id": str(proposal.id),
                "title": title,
                "modification_type": modification_type.value,
                "risk_level": risk_level.value,
                "confidence_score": computed_confidence,
            },
            agent_id="prime",
            metadata={"status": ProposalStatus.PENDING_APPROVAL.value},
        )

        # Record proposal creation in user profile
        if self._profile_engine and proposed_by:
            with contextlib.suppress(Exception):
                await self._profile_engine.record_interaction(
                    user_id=proposed_by,
                    interaction_type=InteractionType.PROPOSAL,
                    domain=None,
                    depth=0.5,
                    approved=None,
                )

        return proposal

    # ------------------------------------------------------------------
    # Review proposals (human-in-the-loop governance)
    # ------------------------------------------------------------------

    async def approve(self, proposal_id: UUID, reviewer: str) -> Proposal:
        """Approve a pending proposal.

        Only proposals in ``PENDING_APPROVAL`` can be approved.
        The approval event is logged to the Tape with the reviewer's identity.
        """
        proposal = self._get_or_raise(proposal_id)
        _validate_transition(proposal.status, ProposalStatus.APPROVED)

        updated = proposal.model_copy(
            update={
                "status": ProposalStatus.APPROVED,
                "reviewer": reviewer,
                "reviewed_at": datetime.now(UTC),
            }
        )
        self._store.update(updated)

        await self._tape.log_event(
            event_type="prime.proposal_approved",
            payload={
                "proposal_id": str(proposal_id),
                "reviewer": reviewer,
            },
            agent_id="prime",
            metadata={"risk_level": proposal.risk_level.value},
        )

        return updated

    async def reject(self, proposal_id: UUID, reviewer: str, reason: str | None = None) -> Proposal:
        """Reject a pending proposal.

        Only proposals in ``PENDING_APPROVAL`` can be rejected.
        An optional rejection reason can be provided for the audit trail.
        """
        proposal = self._get_or_raise(proposal_id)
        _validate_transition(proposal.status, ProposalStatus.REJECTED)

        updated = proposal.model_copy(
            update={
                "status": ProposalStatus.REJECTED,
                "reviewer": reviewer,
                "reviewed_at": datetime.now(UTC),
            }
        )
        self._store.update(updated)

        await self._tape.log_event(
            event_type="prime.proposal_rejected",
            payload={
                "proposal_id": str(proposal_id),
                "reviewer": reviewer,
                "reason": reason or "",
            },
            agent_id="prime",
        )

        return updated

    # ------------------------------------------------------------------
    # Implement proposals
    # ------------------------------------------------------------------

    async def mark_implemented(self, proposal_id: UUID) -> Proposal:
        """Mark an approved proposal as implemented.

        Only proposals in ``APPROVED`` status can be marked as implemented.
        This should be called after the actual code/config change has been
        deployed.
        """
        proposal = self._get_or_raise(proposal_id)
        _validate_transition(proposal.status, ProposalStatus.IMPLEMENTED)

        updated = proposal.model_copy(update={"status": ProposalStatus.IMPLEMENTED})
        self._store.update(updated)

        await self._tape.log_event(
            event_type="prime.proposal_implemented",
            payload={
                "proposal_id": str(proposal_id),
                "modification_type": proposal.modification_type.value,
            },
            agent_id="prime",
        )

        return updated

    # ------------------------------------------------------------------
    # Query proposals
    # ------------------------------------------------------------------

    async def get_proposal(self, proposal_id: UUID) -> Proposal:
        """Retrieve a single proposal by ID.

        Raises:
            ProposalNotFoundError: if no proposal with the given ID exists.
        """
        return self._get_or_raise(proposal_id)

    async def list_proposals(
        self,
        status: ProposalStatus | None = None,
        user_id: str | None = None,
    ) -> list[Proposal]:
        """List proposals, optionally filtered by status and personalized for a user."""
        if status is not None:
            proposals = self._store.list_by_status(status)
        else:
            proposals = self._store.list_all()

        if user_id and self._profile_engine:
            try:
                context = await self._profile_engine.get_recommendation_context(user_id)
                proposals = self._reorder_proposals_by_relevance(proposals, context)
            except Exception:
                # Fallback to default order if personalization fails
                pass

        return proposals

    def _reorder_proposals_by_relevance(
        self,
        proposals: list[Proposal],
        context: dict[str, object],
    ) -> list[Proposal]:
        """Re-order proposals by user profile relevance.

        Uses the recommendation context from IntelligenceProfileEngine
        to sort proposals so the most relevant ones appear first.
        """
        # Simple relevance scoring: prefer proposals in domains the user
        # has high expertise in
        user_domains = context.get("top_domains", [])
        if not isinstance(user_domains, list) or not user_domains:
            return proposals

        def _score(proposal: Proposal) -> int:
            """Higher score = more relevant."""
            # Proposals targeting user's top domains rank higher
            scope = getattr(proposal, "scope", "") or ""
            for domain_obj in user_domains:
                domain_id = ""
                if isinstance(domain_obj, dict):
                    domain_id = str(domain_obj.get("domain_id", ""))
                elif isinstance(domain_obj, str):
                    domain_id = domain_obj
                if domain_id and domain_id in str(scope):
                    return 1
            return 0

        return sorted(proposals, key=_score, reverse=True)

    async def list_pending(self) -> list[Proposal]:
        """Convenience: list all proposals awaiting human review."""
        return self._store.list_by_status(ProposalStatus.PENDING_APPROVAL)

    async def summarize(self) -> list[ProposalSummary]:
        """Return lightweight summaries of all proposals."""
        return [
            ProposalSummary(
                id=p.id,
                title=p.title,
                modification_type=p.modification_type,
                risk_level=p.risk_level,
                confidence_score=p.confidence_score,
                status=p.status,
                proposed_by=p.proposed_by,
                created_at=p.created_at,
            )
            for p in self._store.list_all()
        ]

    # ------------------------------------------------------------------
    # Introspection-driven proposal generation
    # ------------------------------------------------------------------

    async def generate_proposals_from_introspection(self) -> list[Proposal]:
        """Analyse the current system state and generate proposals automatically.

        This is Prime's autonomous improvement loop. It inspects the system
        snapshot, identifies potential improvements, and creates structured
        proposals with reasoning and risk assessment.

        Current heuristics (will be replaced by LLM-driven analysis):
        - Idle agents → suggest reassignment or decommission
        - Empty domains → suggest agent assignment
        - High error rates in Tape → suggest reliability improvements
        - No skills registered → suggest skill onboarding
        """
        if self._introspector is None:
            return []

        snapshot = await self._introspector.snapshot()
        proposals: list[Proposal] = []

        # Heuristic 1: idle agents
        idle_agents = [a for a in snapshot.agents if a.status == "idle"]
        if idle_agents:
            agent_names = ", ".join(a.name for a in idle_agents)
            proposal = await self.propose(
                title="Reassign or decommission idle agents",
                modification_type=ModificationType.AGENT_RECONFIGURATION,
                description=(
                    f"The following agents are currently idle: {agent_names}. "
                    "Consider reassigning them to active domains or decommissioning "
                    "to free resources."
                ),
                reasoning=(
                    "Idle agents consume resources without contributing. "
                    "Reassignment can improve overall system throughput."
                ),
                expected_impact="Better resource utilisation and cost efficiency",
                risk_level=RiskLevel.LOW,
                implementation_steps=[
                    "Review each idle agent's capabilities",
                    "Match capabilities to active domain needs",
                    "Reassign agents or schedule decommission",
                ],
                confidence_score=0.85,
            )
            proposals.append(proposal)

        # Heuristic 2: empty domains (agents = 0)
        empty_domains = [d for d in snapshot.domains if d.agent_count == 0]
        if empty_domains:
            domain_names = ", ".join(d.name for d in empty_domains)
            proposal = await self.propose(
                title=f"Assign agents to empty domain(s): {domain_names}",
                modification_type=ModificationType.DOMAIN_CREATION,
                description=(
                    f"Domain(s) {domain_names} have no assigned agents. "
                    "They need agents to become productive."
                ),
                reasoning="Domains without agents cannot perform any useful work.",
                expected_impact="Domains become operational; increased system coverage",
                risk_level=RiskLevel.LOW,
                implementation_steps=[
                    "Identify available agents (idle or shared)",
                    "Match agent capabilities to domain requirements",
                    "Assign agents and verify domain health",
                ],
                confidence_score=0.80,
            )
            proposals.append(proposal)

        # Heuristic 3: no skills registered
        if len(snapshot.skills) == 0:
            proposal = await self.propose(
                title="Onboard foundational skills",
                modification_type=ModificationType.SKILL_ADDITION,
                description=(
                    "No skills are currently registered in the system. "
                    "Foundational skills (e.g. code generation, search, analysis) "
                    "should be onboarded to enable agent capabilities."
                ),
                reasoning="Agents require skills to perform meaningful tasks.",
                expected_impact="Agents gain capabilities; system becomes productive",
                risk_level=RiskLevel.LOW,
                implementation_steps=[
                    "Identify core skills needed for current domains",
                    "Register skill definitions in the SkillRegistry",
                    "Verify skill availability to agents",
                ],
                confidence_score=0.90,
            )
            proposals.append(proposal)

        # Heuristic 4: high error rate in Tape (check recent entries)
        recent = snapshot.recent_tape_entries[:50]
        error_count = sum(1 for e in recent if "error" in e.event_type.lower())
        if recent and error_count / len(recent) > 0.2:
            proposal = await self.propose(
                title="Investigate and reduce error rate",
                modification_type=ModificationType.BEHAVIOR_CHANGE,
                description=(
                    f"{error_count} out of {len(recent)} recent Tape entries "
                    "are error events (>20%). This indicates systemic reliability "
                    "issues that should be investigated."
                ),
                reasoning="High error rates degrade system trust and output quality.",
                expected_impact="Improved reliability and user confidence",
                risk_level=RiskLevel.MEDIUM,
                implementation_steps=[
                    "Analyse error event types and frequencies",
                    "Identify root causes for top error categories",
                    "Implement targeted fixes or retries",
                    "Monitor error rate in subsequent snapshots",
                ],
                confidence_score=0.70,
            )
            proposals.append(proposal)

        return proposals

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_raise(self, proposal_id: UUID) -> Proposal:
        """Look up a proposal or raise ProposalNotFoundError."""
        proposal = self._store.get(proposal_id)
        if proposal is None:
            raise ProposalNotFoundError(f"Proposal {proposal_id} not found")
        return proposal

    async def _estimate_confidence(
        self,
        risk_level: RiskLevel,
        modification_type: ModificationType,
    ) -> float:
        """Heuristic confidence estimator based on risk and modification type.

        This will be replaced by an LLM-driven confidence model in a future
        phase. For now, we use a simple scoring table.
        """
        risk_score = {RiskLevel.LOW: 0.85, RiskLevel.MEDIUM: 0.65, RiskLevel.HIGH: 0.40}
        type_score = {
            ModificationType.CONFIGURATION_UPDATE: 0.90,
            ModificationType.SKILL_ADDITION: 0.85,
            ModificationType.DOMAIN_CREATION: 0.80,
            ModificationType.AGENT_RECONFIGURATION: 0.75,
            ModificationType.SKILL_MODIFICATION: 0.70,
            ModificationType.BEHAVIOR_CHANGE: 0.65,
            ModificationType.ARCHITECTURE_CHANGE: 0.50,
            ModificationType.SELF_MODIFICATION: 0.40,
        }
        r = risk_score.get(risk_level, 0.5)
        t = type_score.get(modification_type, 0.5)
        return round((r + t) / 2, 2)
