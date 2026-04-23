"""Unit tests for Prime Self-Modification Proposals.

Run with:  pytest tests/test_prime_proposals.py -v
"""

from uuid import UUID

import pytest

from packages.prime.introspection import (
    AgentDescriptor,
    AgentRegistry,
    DomainDescriptor,
    DomainRegistry,
    PrimeIntrospector,
    SkillRegistry,
)
from packages.prime.proposals import (
    ModificationType,
    Proposal,
    ProposalEngine,
    ProposalNotFoundError,
    ProposalStatus,
    ProposalStore,
    ProposalSummary,
    ProposalTransitionError,
    RiskLevel,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tape_repo() -> InMemoryTapeRepository:
    return InMemoryTapeRepository()


@pytest.fixture()
def tape_svc(tape_repo: InMemoryTapeRepository) -> TapeService:
    return TapeService(tape_repo)


@pytest.fixture()
def engine(tape_svc: TapeService) -> ProposalEngine:
    return ProposalEngine(tape_service=tape_svc)


@pytest.fixture()
def introspector(tape_svc: TapeService) -> PrimeIntrospector:
    return PrimeIntrospector(tape_service=tape_svc)


@pytest.fixture()
def engine_with_introspector(
    tape_svc: TapeService, introspector: PrimeIntrospector
) -> ProposalEngine:
    return ProposalEngine(tape_service=tape_svc, introspector=introspector)


@pytest.fixture()
def populated_introspector(tape_svc: TapeService) -> PrimeIntrospector:
    """Introspector with some idle agents and empty domains for heuristics."""
    agent_reg = AgentRegistry()
    agent_reg.register(AgentDescriptor(agent_id="a1", name="IdleBot", status="idle"))
    agent_reg.register(AgentDescriptor(agent_id="a2", name="ActiveBot", status="active"))
    domain_reg = DomainRegistry()
    domain_reg.register(DomainDescriptor(domain_id="d1", name="Empty Domain", agent_count=0))
    skill_reg = SkillRegistry()
    return PrimeIntrospector(
        tape_service=tape_svc,
        agent_registry=agent_reg,
        skill_registry=skill_reg,
        domain_registry=domain_reg,
    )


@pytest.fixture()
def engine_with_data(
    tape_svc: TapeService, populated_introspector: PrimeIntrospector
) -> ProposalEngine:
    return ProposalEngine(tape_service=tape_svc, introspector=populated_introspector)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class TestProposalModel:
    def test_proposal_defaults(self) -> None:
        p = Proposal(
            title="Test",
            modification_type=ModificationType.BEHAVIOR_CHANGE,
            description="desc",
            reasoning="reason",
            expected_impact="impact",
            risk_level=RiskLevel.LOW,
            implementation_steps=["step 1"],
        )
        assert p.status == ProposalStatus.PENDING_APPROVAL
        assert p.proposed_by == "prime"
        assert p.confidence_score == 0.0
        assert p.reviewer is None
        assert p.reviewed_at is None
        assert isinstance(p.id, UUID)

    def test_proposal_with_confidence(self) -> None:
        p = Proposal(
            title="Test",
            modification_type=ModificationType.SKILL_ADDITION,
            description="desc",
            reasoning="reason",
            expected_impact="impact",
            risk_level=RiskLevel.MEDIUM,
            implementation_steps=[],
            confidence_score=0.75,
        )
        assert p.confidence_score == 0.75

    def test_proposal_summary(self) -> None:
        p = Proposal(
            title="My Proposal",
            modification_type=ModificationType.CONFIGURATION_UPDATE,
            description="desc",
            reasoning="reason",
            expected_impact="impact",
            risk_level=RiskLevel.HIGH,
            implementation_steps=[],
        )
        summary = ProposalSummary(
            id=p.id,
            title=p.title,
            modification_type=p.modification_type,
            risk_level=p.risk_level,
            confidence_score=p.confidence_score,
            status=p.status,
            proposed_by=p.proposed_by,
            created_at=p.created_at,
        )
        assert summary.title == "My Proposal"
        assert summary.risk_level == RiskLevel.HIGH


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_modification_types(self) -> None:
        assert ModificationType.SKILL_ADDITION.value == "skill_addition"
        assert ModificationType.SELF_MODIFICATION.value == "self_modification"
        assert len(ModificationType) == 8

    def test_risk_levels(self) -> None:
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"

    def test_proposal_statuses(self) -> None:
        assert ProposalStatus.PENDING_APPROVAL.value == "pending_approval"
        assert ProposalStatus.APPROVED.value == "approved"
        assert ProposalStatus.REJECTED.value == "rejected"
        assert ProposalStatus.IMPLEMENTED.value == "implemented"


# ---------------------------------------------------------------------------
# ProposalStore
# ---------------------------------------------------------------------------


class TestProposalStore:
    def test_add_and_get(self) -> None:
        store = ProposalStore()
        p = Proposal(
            title="Test",
            modification_type=ModificationType.BEHAVIOR_CHANGE,
            description="desc",
            reasoning="reason",
            expected_impact="impact",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        store.add(p)
        assert store.get(p.id) is p

    def test_get_not_found(self) -> None:
        store = ProposalStore()
        assert store.get(UUID("00000000-0000-0000-0000-000000000000")) is None

    def test_list_all(self) -> None:
        store = ProposalStore()
        p1 = Proposal(
            title="P1",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        p2 = Proposal(
            title="P2",
            modification_type=ModificationType.ARCHITECTURE_CHANGE,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.HIGH,
            implementation_steps=[],
        )
        store.add(p1)
        store.add(p2)
        assert len(store.list_all()) == 2

    def test_list_by_status(self) -> None:
        store = ProposalStore()
        p = Proposal(
            title="Test",
            modification_type=ModificationType.BEHAVIOR_CHANGE,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        store.add(p)
        pending = store.list_by_status(ProposalStatus.PENDING_APPROVAL)
        assert len(pending) == 1
        approved = store.list_by_status(ProposalStatus.APPROVED)
        assert len(approved) == 0

    def test_update_not_found_raises(self) -> None:
        store = ProposalStore()
        p = Proposal(
            title="Ghost",
            modification_type=ModificationType.BEHAVIOR_CHANGE,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        with pytest.raises(ProposalNotFoundError):
            store.update(p)


# ---------------------------------------------------------------------------
# ProposalEngine — propose
# ---------------------------------------------------------------------------


class TestProposalEngineCreate:
    @pytest.mark.asyncio
    async def test_propose_creates_proposal(self, engine: ProposalEngine) -> None:
        proposal = await engine.propose(
            title="Add retry logic",
            modification_type=ModificationType.BEHAVIOR_CHANGE,
            description="Wrap writes in retry",
            reasoning="Transient failures causing data loss",
            expected_impact="Higher reliability",
            risk_level=RiskLevel.LOW,
            implementation_steps=["Add tenacity", "Wrap log_event"],
            confidence_score=0.9,
        )
        assert proposal.title == "Add retry logic"
        assert proposal.status == ProposalStatus.PENDING_APPROVAL
        assert proposal.confidence_score == 0.9

    @pytest.mark.asyncio
    async def test_propose_logs_to_tape(
        self, engine: ProposalEngine, tape_svc: TapeService
    ) -> None:
        await engine.propose(
            title="Test proposal",
            modification_type=ModificationType.CONFIGURATION_UPDATE,
            description="desc",
            reasoning="reason",
            expected_impact="impact",
            risk_level=RiskLevel.MEDIUM,
            implementation_steps=[],
        )
        entries = await tape_svc.get_entries(event_type="prime.proposal_created")
        assert len(entries) == 1
        assert entries[0].agent_id == "prime"
        payload = entries[0].payload
        assert payload["modification_type"] == "configuration_update"

    @pytest.mark.asyncio
    async def test_propose_with_introspection_snapshot(
        self, engine_with_introspector: ProposalEngine
    ) -> None:
        proposal = await engine_with_introspector.propose(
            title="Test",
            modification_type=ModificationType.SKILL_ADDITION,
            description="desc",
            reasoning="reason",
            expected_impact="impact",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        assert proposal.introspection_snapshot_id is not None

    @pytest.mark.asyncio
    async def test_propose_auto_confidence(self, engine_with_introspector: ProposalEngine) -> None:
        """When confidence_score=0.0 and introspector is available,
        the engine should auto-compute a confidence score."""
        proposal = await engine_with_introspector.propose(
            title="Test",
            modification_type=ModificationType.CONFIGURATION_UPDATE,
            description="desc",
            reasoning="reason",
            expected_impact="impact",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
            confidence_score=0.0,  # default — should trigger auto-estimate
        )
        assert proposal.confidence_score > 0.0

    @pytest.mark.asyncio
    async def test_propose_with_parent(self, engine: ProposalEngine) -> None:
        parent = await engine.propose(
            title="Original",
            modification_type=ModificationType.BEHAVIOR_CHANGE,
            description="desc",
            reasoning="reason",
            expected_impact="impact",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        child = await engine.propose(
            title="Revised",
            modification_type=ModificationType.BEHAVIOR_CHANGE,
            description="desc v2",
            reasoning="reason v2",
            expected_impact="impact v2",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
            parent_proposal_id=parent.id,
        )
        assert child.parent_proposal_id == parent.id


# ---------------------------------------------------------------------------
# ProposalEngine — approve / reject
# ---------------------------------------------------------------------------


class TestProposalEngineReview:
    @pytest.mark.asyncio
    async def test_approve_pending(self, engine: ProposalEngine) -> None:
        proposal = await engine.propose(
            title="Good idea",
            modification_type=ModificationType.SKILL_ADDITION,
            description="desc",
            reasoning="reason",
            expected_impact="impact",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        approved = await engine.approve(proposal.id, reviewer="alice")
        assert approved.status == ProposalStatus.APPROVED
        assert approved.reviewer == "alice"
        assert approved.reviewed_at is not None

    @pytest.mark.asyncio
    async def test_approve_logs_to_tape(
        self, engine: ProposalEngine, tape_svc: TapeService
    ) -> None:
        proposal = await engine.propose(
            title="T",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        await engine.approve(proposal.id, reviewer="bob")
        entries = await tape_svc.get_entries(event_type="prime.proposal_approved")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_reject_pending(self, engine: ProposalEngine) -> None:
        proposal = await engine.propose(
            title="Bad idea",
            modification_type=ModificationType.ARCHITECTURE_CHANGE,
            description="desc",
            reasoning="reason",
            expected_impact="impact",
            risk_level=RiskLevel.HIGH,
            implementation_steps=[],
        )
        rejected = await engine.reject(proposal.id, reviewer="carol", reason="Too risky")
        assert rejected.status == ProposalStatus.REJECTED
        assert rejected.reviewer == "carol"

    @pytest.mark.asyncio
    async def test_reject_logs_to_tape(self, engine: ProposalEngine, tape_svc: TapeService) -> None:
        proposal = await engine.propose(
            title="T",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        await engine.reject(proposal.id, reviewer="dave")
        entries = await tape_svc.get_entries(event_type="prime.proposal_rejected")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_cannot_approve_rejected(self, engine: ProposalEngine) -> None:
        proposal = await engine.propose(
            title="T",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        await engine.reject(proposal.id, reviewer="eve")
        with pytest.raises(ProposalTransitionError):
            await engine.approve(proposal.id, reviewer="eve")

    @pytest.mark.asyncio
    async def test_cannot_reject_approved(self, engine: ProposalEngine) -> None:
        proposal = await engine.propose(
            title="T",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        await engine.approve(proposal.id, reviewer="frank")
        with pytest.raises(ProposalTransitionError):
            await engine.reject(proposal.id, reviewer="frank")

    @pytest.mark.asyncio
    async def test_approve_nonexistent_raises(self, engine: ProposalEngine) -> None:
        with pytest.raises(ProposalNotFoundError):
            await engine.approve(UUID("00000000-0000-0000-0000-000000000000"), reviewer="x")


# ---------------------------------------------------------------------------
# ProposalEngine — mark_implemented
# ---------------------------------------------------------------------------


class TestProposalEngineImplement:
    @pytest.mark.asyncio
    async def test_mark_implemented(self, engine: ProposalEngine) -> None:
        proposal = await engine.propose(
            title="T",
            modification_type=ModificationType.CONFIGURATION_UPDATE,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        await engine.approve(proposal.id, reviewer="grace")
        implemented = await engine.mark_implemented(proposal.id)
        assert implemented.status == ProposalStatus.IMPLEMENTED

    @pytest.mark.asyncio
    async def test_implemented_logs_to_tape(
        self, engine: ProposalEngine, tape_svc: TapeService
    ) -> None:
        proposal = await engine.propose(
            title="T",
            modification_type=ModificationType.CONFIGURATION_UPDATE,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        await engine.approve(proposal.id, reviewer="hank")
        await engine.mark_implemented(proposal.id)
        entries = await tape_svc.get_entries(event_type="prime.proposal_implemented")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_cannot_implement_pending(self, engine: ProposalEngine) -> None:
        proposal = await engine.propose(
            title="T",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        with pytest.raises(ProposalTransitionError):
            await engine.mark_implemented(proposal.id)

    @pytest.mark.asyncio
    async def test_cannot_implement_rejected(self, engine: ProposalEngine) -> None:
        proposal = await engine.propose(
            title="T",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        await engine.reject(proposal.id, reviewer="ivy")
        with pytest.raises(ProposalTransitionError):
            await engine.mark_implemented(proposal.id)

    @pytest.mark.asyncio
    async def test_cannot_implement_twice(self, engine: ProposalEngine) -> None:
        proposal = await engine.propose(
            title="T",
            modification_type=ModificationType.CONFIGURATION_UPDATE,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        await engine.approve(proposal.id, reviewer="jack")
        await engine.mark_implemented(proposal.id)
        with pytest.raises(ProposalTransitionError):
            await engine.mark_implemented(proposal.id)


# ---------------------------------------------------------------------------
# ProposalEngine — queries
# ---------------------------------------------------------------------------


class TestProposalEngineQueries:
    @pytest.mark.asyncio
    async def test_get_proposal(self, engine: ProposalEngine) -> None:
        proposal = await engine.propose(
            title="T",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        fetched = await engine.get_proposal(proposal.id)
        assert fetched.id == proposal.id

    @pytest.mark.asyncio
    async def test_get_proposal_not_found(self, engine: ProposalEngine) -> None:
        with pytest.raises(ProposalNotFoundError):
            await engine.get_proposal(UUID("00000000-0000-0000-0000-000000000000"))

    @pytest.mark.asyncio
    async def test_list_proposals_all(self, engine: ProposalEngine) -> None:
        await engine.propose(
            title="P1",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        await engine.propose(
            title="P2",
            modification_type=ModificationType.BEHAVIOR_CHANGE,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.MEDIUM,
            implementation_steps=[],
        )
        all_proposals = await engine.list_proposals()
        assert len(all_proposals) == 2

    @pytest.mark.asyncio
    async def test_list_proposals_by_status(self, engine: ProposalEngine) -> None:
        p1 = await engine.propose(
            title="P1",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        await engine.propose(
            title="P2",
            modification_type=ModificationType.BEHAVIOR_CHANGE,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.MEDIUM,
            implementation_steps=[],
        )
        await engine.approve(p1.id, reviewer="kim")
        approved = await engine.list_proposals(status=ProposalStatus.APPROVED)
        assert len(approved) == 1
        pending = await engine.list_proposals(status=ProposalStatus.PENDING_APPROVAL)
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_list_pending(self, engine: ProposalEngine) -> None:
        await engine.propose(
            title="P1",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
        )
        pending = await engine.list_pending()
        assert len(pending) == 1
        assert pending[0].status == ProposalStatus.PENDING_APPROVAL

    @pytest.mark.asyncio
    async def test_summarize(self, engine: ProposalEngine) -> None:
        await engine.propose(
            title="My Prop",
            modification_type=ModificationType.SKILL_ADDITION,
            description="",
            reasoning="",
            expected_impact="",
            risk_level=RiskLevel.LOW,
            implementation_steps=[],
            confidence_score=0.88,
        )
        summaries = await engine.summarize()
        assert len(summaries) == 1
        assert isinstance(summaries[0], ProposalSummary)
        assert summaries[0].title == "My Prop"
        assert summaries[0].confidence_score == 0.88


# ---------------------------------------------------------------------------
# ProposalEngine — introspection-driven generation
# ---------------------------------------------------------------------------


class TestProposalEngineAutoGenerate:
    @pytest.mark.asyncio
    async def test_no_proposals_without_introspector(self, engine: ProposalEngine) -> None:
        proposals = await engine.generate_proposals_from_introspection()
        assert proposals == []

    @pytest.mark.asyncio
    async def test_generates_idle_agent_proposal(self, engine_with_data: ProposalEngine) -> None:
        proposals = await engine_with_data.generate_proposals_from_introspection()
        titles = [p.title for p in proposals]
        assert any("idle" in t.lower() for t in titles)

    @pytest.mark.asyncio
    async def test_generates_empty_domain_proposal(self, engine_with_data: ProposalEngine) -> None:
        proposals = await engine_with_data.generate_proposals_from_introspection()
        titles = [p.title for p in proposals]
        assert any("empty domain" in t.lower() for t in titles)

    @pytest.mark.asyncio
    async def test_generates_no_skill_proposal(self, tape_svc: TapeService) -> None:
        """No skills registered → should generate a skill onboarding proposal."""
        introspector = PrimeIntrospector(tape_service=tape_svc)
        engine = ProposalEngine(tape_service=tape_svc, introspector=introspector)
        proposals = await engine.generate_proposals_from_introspection()
        titles = [p.title for p in proposals]
        assert any("skill" in t.lower() for t in titles)

    @pytest.mark.asyncio
    async def test_auto_proposals_are_pending(self, engine_with_data: ProposalEngine) -> None:
        proposals = await engine_with_data.generate_proposals_from_introspection()
        for p in proposals:
            assert p.status == ProposalStatus.PENDING_APPROVAL

    @pytest.mark.asyncio
    async def test_auto_proposals_have_positive_confidence(
        self, engine_with_data: ProposalEngine
    ) -> None:
        proposals = await engine_with_data.generate_proposals_from_introspection()
        for p in proposals:
            assert p.confidence_score > 0.0

    @pytest.mark.asyncio
    async def test_auto_proposals_are_logged_to_tape(
        self, engine_with_data: ProposalEngine, tape_svc: TapeService
    ) -> None:
        await engine_with_data.generate_proposals_from_introspection()
        entries = await tape_svc.get_entries(event_type="prime.proposal_created")
        assert len(entries) >= 1


# ---------------------------------------------------------------------------
# State transition validation
# ---------------------------------------------------------------------------


class TestStateTransitions:
    def test_valid_transitions_from_pending(self) -> None:
        from packages.prime.proposals import _validate_transition

        # Should not raise
        _validate_transition(ProposalStatus.PENDING_APPROVAL, ProposalStatus.APPROVED)
        _validate_transition(ProposalStatus.PENDING_APPROVAL, ProposalStatus.REJECTED)

    def test_invalid_transition_raises(self) -> None:
        from packages.prime.proposals import _validate_transition

        with pytest.raises(ProposalTransitionError):
            _validate_transition(ProposalStatus.PENDING_APPROVAL, ProposalStatus.IMPLEMENTED)

    def test_no_transitions_from_terminal_states(self) -> None:
        from packages.prime.proposals import _validate_transition

        with pytest.raises(ProposalTransitionError):
            _validate_transition(ProposalStatus.REJECTED, ProposalStatus.APPROVED)
        with pytest.raises(ProposalTransitionError):
            _validate_transition(ProposalStatus.IMPLEMENTED, ProposalStatus.APPROVED)
