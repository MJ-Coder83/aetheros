"""Unit tests for the Skill Evolution Engine.

Run with:  pytest tests/test_skill_evolution.py -v
"""

from uuid import UUID

import pytest

from packages.prime.introspection import (
    PrimeIntrospector,
    SkillDescriptor,
    SkillRegistry,
)
from packages.prime.proposals import (
    ModificationType,
    ProposalEngine,
    RiskLevel,
)
from packages.prime.skill_evolution import (
    EvolutionNotApprovedError,
    EvolutionProposalNotFoundError,
    EvolutionResult,
    EvolutionType,
    RollbackError,
    SkillAnalysis,
    SkillEvolutionEngine,
    SkillEvolutionProposal,
    SkillEvolutionStore,
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
def skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(
        SkillDescriptor(
            skill_id="code-gen",
            name="Code Generation",
            version="1.0.0",
            description="Generate code from natural language specs",
        )
    )
    registry.register(
        SkillDescriptor(
            skill_id="code-review",
            name="Code Review",
            version="0.5.0",
            description="Review code for quality and bugs",
        )
    )
    registry.register(
        SkillDescriptor(
            skill_id="search-web",
            name="Web Search",
            version="0.3.0",
            description="Search the web for information",
        )
    )
    return registry


@pytest.fixture()
def proposal_engine(tape_svc: TapeService) -> ProposalEngine:
    return ProposalEngine(tape_service=tape_svc)


@pytest.fixture()
def introspector(tape_svc: TapeService, skill_registry: SkillRegistry) -> PrimeIntrospector:
    return PrimeIntrospector(tape_service=tape_svc, skill_registry=skill_registry)


@pytest.fixture()
def engine(
    tape_svc: TapeService,
    introspector: PrimeIntrospector,
    proposal_engine: ProposalEngine,
    skill_registry: SkillRegistry,
) -> SkillEvolutionEngine:
    return SkillEvolutionEngine(
        tape_service=tape_svc,
        introspector=introspector,
        proposal_engine=proposal_engine,
        skill_registry=skill_registry,
    )


@pytest.fixture()
def engine_minimal(tape_svc: TapeService) -> SkillEvolutionEngine:
    """Engine with no introspector or skills — for edge-case testing."""
    return SkillEvolutionEngine(tape_service=tape_svc)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class TestEvolutionType:
    def test_all_types(self) -> None:
        assert EvolutionType.ENHANCE.value == "enhance"
        assert EvolutionType.MERGE.value == "merge"
        assert EvolutionType.SPLIT.value == "split"
        assert EvolutionType.DEPRECATE.value == "deprecate"
        assert EvolutionType.CREATE.value == "create"
        assert len(EvolutionType) == 5


class TestSkillAnalysis:
    def test_defaults(self) -> None:
        a = SkillAnalysis(skill_id="test")
        assert a.invocation_count == 0
        assert a.error_rate == 0.0
        assert a.recommendation == "maintain"

    def test_custom_values(self) -> None:
        a = SkillAnalysis(
            skill_id="test",
            invocation_count=100,
            error_count=5,
            error_rate=0.05,
            recommendation="enhance",
            recommendation_reason="High error rate",
        )
        assert a.invocation_count == 100
        assert a.recommendation == "enhance"


class TestSkillEvolutionProposal:
    def test_defaults(self) -> None:
        p = SkillEvolutionProposal(
            proposal_id=UUID("00000000-0000-0000-0000-000000000001"),
            evolution_type=EvolutionType.ENHANCE,
            target_skill_ids=["s1"],
            reasoning="test",
        )
        assert p.before_snapshot == []
        assert p.new_skill_descriptor is None
        assert isinstance(p.id, UUID)


class TestEvolutionResult:
    def test_success_result(self) -> None:
        r = EvolutionResult(
            evolution_proposal_id=UUID("00000000-0000-0000-0000-000000000001"),
            success=True,
            skills_added=["new-skill"],
            skills_removed=["old-skill"],
        )
        assert r.success is True
        assert r.error_message is None

    def test_failure_result(self) -> None:
        r = EvolutionResult(
            evolution_proposal_id=UUID("00000000-0000-0000-0000-000000000001"),
            success=False,
            error_message="Something went wrong",
        )
        assert r.success is False
        assert r.error_message == "Something went wrong"


# ---------------------------------------------------------------------------
# SkillEvolutionStore
# ---------------------------------------------------------------------------


class TestSkillEvolutionStore:
    def test_add_and_get_proposal(self) -> None:
        store = SkillEvolutionStore()
        p = SkillEvolutionProposal(
            proposal_id=UUID("00000000-0000-0000-0000-000000000001"),
            evolution_type=EvolutionType.ENHANCE,
            target_skill_ids=["s1"],
            reasoning="test",
        )
        store.add_proposal(p)
        assert store.get_proposal(p.id) is p

    def test_get_proposal_not_found(self) -> None:
        store = SkillEvolutionStore()
        assert store.get_proposal(UUID("00000000-0000-0000-0000-000000000000")) is None

    def test_list_proposals(self) -> None:
        store = SkillEvolutionStore()
        p1 = SkillEvolutionProposal(
            proposal_id=UUID("00000000-0000-0000-0000-000000000001"),
            evolution_type=EvolutionType.ENHANCE,
            target_skill_ids=["s1"],
            reasoning="test",
        )
        store.add_proposal(p1)
        assert len(store.list_proposals()) == 1

    def test_add_and_get_result(self) -> None:
        store = SkillEvolutionStore()
        r = EvolutionResult(
            evolution_proposal_id=UUID("00000000-0000-0000-0000-000000000001"),
            success=True,
        )
        store.add_result(r)
        assert store.get_result(r.id) is r

    def test_results_for_proposal(self) -> None:
        store = SkillEvolutionStore()
        ev_id = UUID("00000000-0000-0000-0000-000000000001")
        r1 = EvolutionResult(evolution_proposal_id=ev_id, success=True)
        r2 = EvolutionResult(
            evolution_proposal_id=UUID("00000000-0000-0000-0000-000000000002"),
            success=True,
        )
        store.add_result(r1)
        store.add_result(r2)
        results = store.get_results_for_proposal(ev_id)
        assert len(results) == 1
        assert results[0].evolution_proposal_id == ev_id


# ---------------------------------------------------------------------------
# SkillEvolutionEngine — analyze_skills
# ---------------------------------------------------------------------------


class TestAnalyzeSkills:
    @pytest.mark.asyncio
    async def test_analyze_returns_per_skill(self, engine: SkillEvolutionEngine) -> None:
        analyses = await engine.analyze_skills()
        assert len(analyses) == 3
        skill_ids = {a.skill_id for a in analyses}
        assert "code-gen" in skill_ids
        assert "search-web" in skill_ids

    @pytest.mark.asyncio
    async def test_analyze_logs_to_tape(
        self, engine: SkillEvolutionEngine, tape_svc: TapeService
    ) -> None:
        await engine.analyze_skills()
        entries = await tape_svc.get_entries(event_type="prime.skill_analysis")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_analyze_empty_registry(self, engine_minimal: SkillEvolutionEngine) -> None:
        analyses = await engine_minimal.analyze_skills()
        assert analyses == []


# ---------------------------------------------------------------------------
# SkillEvolutionEngine — generate_evolution_proposals
# ---------------------------------------------------------------------------


class TestGenerateEvolutionProposals:
    @pytest.mark.asyncio
    async def test_generates_proposals(self, engine: SkillEvolutionEngine) -> None:
        proposals = await engine.generate_evolution_proposals()
        assert isinstance(proposals, list)
        for p in proposals:
            assert p.evolution_type in EvolutionType

    @pytest.mark.asyncio
    async def test_generates_create_when_no_skills(
        self, engine_minimal: SkillEvolutionEngine
    ) -> None:
        proposals = await engine_minimal.generate_evolution_proposals()
        assert len(proposals) >= 1
        create_proposals = [p for p in proposals if p.evolution_type == EvolutionType.CREATE]
        assert len(create_proposals) >= 1
        assert create_proposals[0].new_skill_descriptor is not None

    @pytest.mark.asyncio
    async def test_generated_proposals_have_linked_proposal(
        self, engine: SkillEvolutionEngine
    ) -> None:
        proposals = await engine.generate_evolution_proposals()
        for ev in proposals:
            assert ev.proposal_id is not None
            assert isinstance(ev.proposal_id, UUID)

    @pytest.mark.asyncio
    async def test_generated_proposals_stored(self, engine: SkillEvolutionEngine) -> None:
        await engine.generate_evolution_proposals()
        listed = await engine.list_evolution_proposals()
        assert len(listed) >= 1


# ---------------------------------------------------------------------------
# SkillEvolutionEngine — apply_evolution
# ---------------------------------------------------------------------------


class TestApplyEvolution:
    @pytest.mark.asyncio
    async def test_apply_not_found_raises(self, engine: SkillEvolutionEngine) -> None:
        with pytest.raises(EvolutionProposalNotFoundError):
            await engine.apply_evolution(UUID("00000000-0000-0000-0000-000000000099"))

    @pytest.mark.asyncio
    async def test_apply_unapproved_raises(self, engine: SkillEvolutionEngine) -> None:
        proposals = await engine.generate_evolution_proposals()
        if not proposals:
            pytest.skip("No proposals generated")
        # Proposal is still PENDING → should raise
        with pytest.raises(EvolutionNotApprovedError):
            await engine.apply_evolution(proposals[0].id)

    @pytest.mark.asyncio
    async def test_apply_enhance_after_approval(
        self, tape_svc: TapeService, skill_registry: SkillRegistry
    ) -> None:
        """End-to-end: generate → approve → apply for an enhance evolution."""
        proposal_engine = ProposalEngine(tape_service=tape_svc)
        introspector = PrimeIntrospector(tape_service=tape_svc, skill_registry=skill_registry)
        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            introspector=introspector,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )

        # Create an enhance proposal
        proposal = await proposal_engine.propose(
            title="[enhance] Skill code-gen",
            modification_type=ModificationType.SKILL_MODIFICATION,
            description="Enhance code-gen",
            reasoning="High error rate",
            expected_impact="Better reliability",
            risk_level=RiskLevel.LOW,
            implementation_steps=["Bump version"],
        )
        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=EvolutionType.ENHANCE,
            target_skill_ids=["code-gen"],
            before_snapshot=skill_registry.list_skills(),
            reasoning="Enhance test",
        )
        engine._store.add_proposal(ev_proposal)

        # Approve the proposal
        await proposal_engine.approve(proposal.id, reviewer="tester")

        # Apply the evolution
        result = await engine.apply_evolution(ev_proposal.id)
        assert result.success is True
        assert "code-gen" in result.skills_modified

    @pytest.mark.asyncio
    async def test_apply_deprecate_removes_skill(
        self, tape_svc: TapeService, skill_registry: SkillRegistry
    ) -> None:
        proposal_engine = ProposalEngine(tape_service=tape_svc)
        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )

        proposal = await proposal_engine.propose(
            title="[deprecate] Skill search-web",
            modification_type=ModificationType.SKILL_MODIFICATION,
            description="Deprecate search-web",
            reasoning="Unused",
            expected_impact="Reduced complexity",
            risk_level=RiskLevel.HIGH,
            implementation_steps=["Remove skill"],
        )
        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=EvolutionType.DEPRECATE,
            target_skill_ids=["search-web"],
            before_snapshot=skill_registry.list_skills(),
            reasoning="Unused skill",
        )
        engine._store.add_proposal(ev_proposal)

        await proposal_engine.approve(proposal.id, reviewer="tester")
        result = await engine.apply_evolution(ev_proposal.id)
        assert result.success is True
        assert "search-web" in result.skills_removed
        # Skill should no longer be in registry
        remaining_ids = {s.skill_id for s in skill_registry.list_skills()}
        assert "search-web" not in remaining_ids

    @pytest.mark.asyncio
    async def test_apply_create_adds_skill(
        self, tape_svc: TapeService, skill_registry: SkillRegistry
    ) -> None:
        proposal_engine = ProposalEngine(tape_service=tape_svc)
        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )

        new_skill = SkillDescriptor(
            skill_id="translation",
            name="Translation",
            version="0.1.0",
            description="Translate text between languages",
        )
        proposal = await proposal_engine.propose(
            title="[create] New skill: Translation",
            modification_type=ModificationType.SKILL_ADDITION,
            description="Add translation skill",
            reasoning="Agents need multilingual capabilities",
            expected_impact="New capability",
            risk_level=RiskLevel.LOW,
            implementation_steps=["Register skill"],
        )
        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=EvolutionType.CREATE,
            target_skill_ids=[],
            new_skill_descriptor=new_skill,
            before_snapshot=[],
            reasoning="New skill needed",
        )
        engine._store.add_proposal(ev_proposal)

        await proposal_engine.approve(proposal.id, reviewer="tester")
        result = await engine.apply_evolution(ev_proposal.id)
        assert result.success is True
        assert "translation" in result.skills_added
        skill_ids = {s.skill_id for s in skill_registry.list_skills()}
        assert "translation" in skill_ids

    @pytest.mark.asyncio
    async def test_apply_merge_combines_skills(
        self, tape_svc: TapeService, skill_registry: SkillRegistry
    ) -> None:
        proposal_engine = ProposalEngine(tape_service=tape_svc)
        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )

        proposal = await proposal_engine.propose(
            title="[merge] Code Gen + Code Review",
            modification_type=ModificationType.SKILL_MODIFICATION,
            description="Merge related skills",
            reasoning="Overlapping functionality",
            expected_impact="Consolidated skill",
            risk_level=RiskLevel.MEDIUM,
            implementation_steps=["Merge skills"],
        )
        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=EvolutionType.MERGE,
            target_skill_ids=["code-gen", "code-review"],
            before_snapshot=skill_registry.list_skills(),
            reasoning="Overlapping skills",
        )
        engine._store.add_proposal(ev_proposal)

        await proposal_engine.approve(proposal.id, reviewer="tester")
        result = await engine.apply_evolution(ev_proposal.id)
        assert result.success is True
        assert len(result.skills_added) == 1
        assert "code-gen" in result.skills_removed
        assert "code-review" in result.skills_removed

    @pytest.mark.asyncio
    async def test_apply_split_divides_skill(
        self, tape_svc: TapeService, skill_registry: SkillRegistry
    ) -> None:
        proposal_engine = ProposalEngine(tape_service=tape_svc)
        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )

        proposal = await proposal_engine.propose(
            title="[split] Skill code-gen",
            modification_type=ModificationType.SKILL_MODIFICATION,
            description="Split broad skill",
            reasoning="Too broad",
            expected_impact="Focused sub-skills",
            risk_level=RiskLevel.MEDIUM,
            implementation_steps=["Split skill"],
        )
        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=EvolutionType.SPLIT,
            target_skill_ids=["code-gen"],
            before_snapshot=skill_registry.list_skills(),
            reasoning="Skill too broad",
        )
        engine._store.add_proposal(ev_proposal)

        await proposal_engine.approve(proposal.id, reviewer="tester")
        result = await engine.apply_evolution(ev_proposal.id)
        assert result.success is True
        assert "code-gen" in result.skills_removed
        assert len(result.skills_added) == 2

    @pytest.mark.asyncio
    async def test_apply_logs_to_tape(
        self, tape_svc: TapeService, skill_registry: SkillRegistry
    ) -> None:
        proposal_engine = ProposalEngine(tape_service=tape_svc)
        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )

        proposal = await proposal_engine.propose(
            title="[create] New skill",
            modification_type=ModificationType.SKILL_ADDITION,
            description="Add skill",
            reasoning="Needed",
            expected_impact="New cap",
            risk_level=RiskLevel.LOW,
            implementation_steps=["Register"],
        )
        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=EvolutionType.CREATE,
            target_skill_ids=[],
            new_skill_descriptor=SkillDescriptor(
                skill_id="new-one", name="New One", description="A new skill"
            ),
            before_snapshot=[],
            reasoning="test",
        )
        engine._store.add_proposal(ev_proposal)
        await proposal_engine.approve(proposal.id, reviewer="tester")

        await engine.apply_evolution(ev_proposal.id)
        entries = await tape_svc.get_entries(event_type="prime.skill_evolution_applied")
        assert len(entries) == 1


# ---------------------------------------------------------------------------
# SkillEvolutionEngine — rollback
# ---------------------------------------------------------------------------


class TestRollback:
    @pytest.mark.asyncio
    async def test_rollback_deprecate(
        self, tape_svc: TapeService, skill_registry: SkillRegistry
    ) -> None:
        """Deprecate a skill, then rollback — skill should reappear."""
        proposal_engine = ProposalEngine(tape_service=tape_svc)
        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )

        proposal = await proposal_engine.propose(
            title="[deprecate] Skill search-web",
            modification_type=ModificationType.SKILL_MODIFICATION,
            description="Deprecate",
            reasoning="Unused",
            expected_impact="Simpler",
            risk_level=RiskLevel.HIGH,
            implementation_steps=["Remove"],
        )
        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=EvolutionType.DEPRECATE,
            target_skill_ids=["search-web"],
            before_snapshot=skill_registry.list_skills(),
            reasoning="Unused",
        )
        engine._store.add_proposal(ev_proposal)
        await proposal_engine.approve(proposal.id, reviewer="tester")

        # Apply deprecation
        result = await engine.apply_evolution(ev_proposal.id)
        assert result.success is True
        assert "search-web" in result.skills_removed

        # Rollback
        rollback_result = await engine.rollback(ev_proposal.id)
        assert rollback_result.success is True
        assert "search-web" in rollback_result.skills_added
        # Skill should be back
        skill_ids = {s.skill_id for s in skill_registry.list_skills()}
        assert "search-web" in skill_ids

    @pytest.mark.asyncio
    async def test_rollback_logs_to_tape(
        self, tape_svc: TapeService, skill_registry: SkillRegistry
    ) -> None:
        proposal_engine = ProposalEngine(tape_service=tape_svc)
        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )

        proposal = await proposal_engine.propose(
            title="[deprecate] Skill search-web",
            modification_type=ModificationType.SKILL_MODIFICATION,
            description="Deprecate",
            reasoning="Unused",
            expected_impact="Simpler",
            risk_level=RiskLevel.HIGH,
            implementation_steps=["Remove"],
        )
        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=EvolutionType.DEPRECATE,
            target_skill_ids=["search-web"],
            before_snapshot=skill_registry.list_skills(),
            reasoning="Unused",
        )
        engine._store.add_proposal(ev_proposal)
        await proposal_engine.approve(proposal.id, reviewer="tester")
        await engine.apply_evolution(ev_proposal.id)

        await engine.rollback(ev_proposal.id)
        entries = await tape_svc.get_entries(event_type="prime.skill_evolution_rollback")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_rollback_no_snapshot_raises(self, engine: SkillEvolutionEngine) -> None:
        with pytest.raises(RollbackError):
            await engine.rollback(UUID("00000000-0000-0000-0000-000000000099"))

    @pytest.mark.asyncio
    async def test_rollback_create_removes_added_skill(
        self, tape_svc: TapeService, skill_registry: SkillRegistry
    ) -> None:
        """Create a new skill, then rollback — it should be removed."""
        proposal_engine = ProposalEngine(tape_service=tape_svc)
        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )

        new_skill = SkillDescriptor(skill_id="temp-skill", name="Temp", description="Temporary")
        proposal = await proposal_engine.propose(
            title="[create] Temp skill",
            modification_type=ModificationType.SKILL_ADDITION,
            description="Add temp skill",
            reasoning="Test",
            expected_impact="Test",
            risk_level=RiskLevel.LOW,
            implementation_steps=["Add"],
        )
        ev_proposal = SkillEvolutionProposal(
            proposal_id=proposal.id,
            evolution_type=EvolutionType.CREATE,
            target_skill_ids=[],
            new_skill_descriptor=new_skill,
            before_snapshot=skill_registry.list_skills(),
            reasoning="test",
        )
        engine._store.add_proposal(ev_proposal)
        await proposal_engine.approve(proposal.id, reviewer="tester")

        # Apply — adds "temp-skill"
        await engine.apply_evolution(ev_proposal.id)
        assert "temp-skill" in {s.skill_id for s in skill_registry.list_skills()}

        # Rollback — "temp-skill" should be removed
        result = await engine.rollback(ev_proposal.id)
        assert result.success is True
        assert "temp-skill" in result.skills_removed
        assert "temp-skill" not in {s.skill_id for s in skill_registry.list_skills()}


# ---------------------------------------------------------------------------
# SkillEvolutionEngine — query helpers
# ---------------------------------------------------------------------------


class TestQueryHelpers:
    @pytest.mark.asyncio
    async def test_get_evolution_proposal(self, engine: SkillEvolutionEngine) -> None:
        proposals = await engine.generate_evolution_proposals()
        if not proposals:
            pytest.skip("No proposals generated")
        fetched = await engine.get_evolution_proposal(proposals[0].id)
        assert fetched.id == proposals[0].id

    @pytest.mark.asyncio
    async def test_get_evolution_proposal_not_found(self, engine: SkillEvolutionEngine) -> None:
        with pytest.raises(EvolutionProposalNotFoundError):
            await engine.get_evolution_proposal(UUID("00000000-0000-0000-0000-000000000099"))

    @pytest.mark.asyncio
    async def test_list_evolution_proposals(self, engine: SkillEvolutionEngine) -> None:
        await engine.generate_evolution_proposals()
        proposals = await engine.list_evolution_proposals()
        assert isinstance(proposals, list)
        assert len(proposals) >= 1

    @pytest.mark.asyncio
    async def test_list_results_empty(
        self, tape_svc: TapeService, skill_registry: SkillRegistry
    ) -> None:
        proposal_engine = ProposalEngine(tape_service=tape_svc)
        engine = SkillEvolutionEngine(
            tape_service=tape_svc,
            proposal_engine=proposal_engine,
            skill_registry=skill_registry,
        )
        # No results yet
        results = await engine.list_results()
        assert results == []


# ---------------------------------------------------------------------------
# Recommendation heuristics
# ---------------------------------------------------------------------------


class TestRecommendationHeuristics:
    def test_high_error_rate_recommends_enhance(self) -> None:
        skill = SkillDescriptor(skill_id="buggy", name="Buggy Skill", description="Has issues")
        rec, reason = SkillEvolutionEngine._compute_recommendation(
            skill=skill,
            invocation_count=100,
            error_rate=0.5,
            all_skills=[skill],
        )
        assert rec == "enhance"
        assert "error rate" in reason.lower()

    def test_zero_invocations_recommends_deprecate(self) -> None:
        skill = SkillDescriptor(
            skill_id="unused",
            name="Unused Skill",
            description="Nobody uses this",
        )
        rec, reason = SkillEvolutionEngine._compute_recommendation(
            skill=skill,
            invocation_count=0,
            error_rate=0.0,
            all_skills=[skill],
        )
        assert rec == "deprecate"
        assert "zero" in reason.lower()

    def test_overlapping_names_recommends_merge(self) -> None:
        skill_a = SkillDescriptor(
            skill_id="code-gen",
            name="Code Generation",
            description="gen code",
        )
        skill_b = SkillDescriptor(
            skill_id="code-review",
            name="Code Review",
            description="review code",
        )
        rec, _ = SkillEvolutionEngine._compute_recommendation(
            skill=skill_a,
            invocation_count=50,
            error_rate=0.0,
            all_skills=[skill_a, skill_b],
        )
        assert rec == "merge"

    def test_broad_description_recommends_split(self) -> None:
        skill = SkillDescriptor(
            skill_id="mega",
            name="Mega Skill",
            description=(
                "This skill does code generation AND code review AND "
                "testing AND deployment AND monitoring AND documentation"
            ),
        )
        rec, _ = SkillEvolutionEngine._compute_recommendation(
            skill=skill,
            invocation_count=50,
            error_rate=0.0,
            all_skills=[skill],
        )
        assert rec == "split"

    def test_healthy_skill_recommends_maintain(self) -> None:
        skill = SkillDescriptor(skill_id="good", name="Good Skill", description="Works well")
        rec, _ = SkillEvolutionEngine._compute_recommendation(
            skill=skill,
            invocation_count=50,
            error_rate=0.0,
            all_skills=[skill],
        )
        assert rec == "maintain"

    def test_find_related_skills(self) -> None:
        skill_a = SkillDescriptor(skill_id="code-gen", name="Code Generation", description="")
        skill_b = SkillDescriptor(skill_id="code-review", name="Code Review", description="")
        skill_c = SkillDescriptor(skill_id="search-web", name="Web Search", description="")
        related = SkillEvolutionEngine._find_related_skills(skill_a, [skill_a, skill_b, skill_c])
        assert "code-review" in related
        assert "search-web" not in related
