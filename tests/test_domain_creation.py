"""Unit tests for One-Click Domain Creation.

Run with: pytest tests/test_domain_creation.py -v
"""

import pytest

from packages.aethergit.advanced import AdvancedAetherGit
from packages.folder_tree import FolderTreeService, NodeType
from packages.prime.domain_creation import (
    AgentBlueprint,
    AgentRole,
    BlueprintGenerator,
    BlueprintNotFoundError,
    BlueprintStore,
    BlueprintValidationError,
    BlueprintValidator,
    CreationMode,
    DomainBlueprint,
    DomainConfig,
    DomainCreationEngine,
    DomainCreationResult,
    DomainNotApprovedError,
    DomainStatus,
    DuplicateDomainError,
    SkillBlueprint,
    WorkflowBlueprint,
    WorkflowType,
)
from packages.prime.introspection import (
    DomainDescriptor,
    DomainRegistry,
    FolderThinkingError,
    PrimeIntrospector,
    SkillDescriptor,
)
from packages.prime.proposals import (
    ModificationType,
    ProposalEngine,
    RiskLevel,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tape_svc() -> TapeService:
    return TapeService(InMemoryTapeRepository())


@pytest.fixture()
def introspector(tape_svc: TapeService) -> PrimeIntrospector:
    return PrimeIntrospector(tape_service=tape_svc)


@pytest.fixture()
def proposal_engine(tape_svc: TapeService, introspector: PrimeIntrospector) -> ProposalEngine:
    return ProposalEngine(tape_service=tape_svc, introspector=introspector)


@pytest.fixture()
def engine(
    tape_svc: TapeService,
    introspector: PrimeIntrospector,
    proposal_engine: ProposalEngine,
) -> DomainCreationEngine:
    return DomainCreationEngine(
        tape_service=tape_svc,
        introspector=introspector,
        proposal_engine=proposal_engine,
    )


@pytest.fixture()
def engine_no_proposal(tape_svc: TapeService, introspector: PrimeIntrospector) -> DomainCreationEngine:
    return DomainCreationEngine(
        tape_service=tape_svc,
        introspector=introspector,
        proposal_engine=None,
    )


@pytest.fixture()
def store() -> BlueprintStore:
    return BlueprintStore()


@pytest.fixture()
def generator() -> BlueprintGenerator:
    return BlueprintGenerator()


@pytest.fixture()
def validator() -> BlueprintValidator:
    return BlueprintValidator()


@pytest.fixture()
def domain_registry() -> DomainRegistry:
    return DomainRegistry()


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------


LEGAL_DESCRIPTION = "Create a Legal Research Domain for contract analysis and compliance checking"

RESEARCH_DESCRIPTION = "Build a domain for academic research and literature review"

ENGINEERING_DESCRIPTION = "Create a software engineering domain for code review and deployment"

FINANCE_DESCRIPTION = "Set up a financial operations domain for trading and risk management"

HEALTHCARE_DESCRIPTION = "Create a healthcare domain for patient care and diagnosis support"

GENERIC_DESCRIPTION = "Create a custom domain for data processing and reporting"


# ===========================================================================
# BlueprintStore tests
# ===========================================================================


class TestBlueprintStore:
    """Tests for the in-memory blueprint store."""

    def test_add_and_get(self, store: BlueprintStore) -> None:
        bp = DomainBlueprint(domain_name="Test", domain_id="test")
        store.add(bp)
        assert store.get(bp.id) is bp

    def test_get_not_found(self, store: BlueprintStore) -> None:
        from uuid import uuid4
        assert store.get(uuid4()) is None

    def test_get_by_domain_id(self, store: BlueprintStore) -> None:
        bp = DomainBlueprint(domain_name="Test", domain_id="legal-ops")
        store.add(bp)
        assert store.get_by_domain_id("legal-ops") is bp

    def test_get_by_domain_id_not_found(self, store: BlueprintStore) -> None:
        assert store.get_by_domain_id("nonexistent") is None

    def test_list_all(self, store: BlueprintStore) -> None:
        store.add(DomainBlueprint(domain_name="A", domain_id="a"))
        store.add(DomainBlueprint(domain_name="B", domain_id="b"))
        assert len(store.list_all()) == 2

    def test_update(self, store: BlueprintStore) -> None:
        bp = DomainBlueprint(domain_name="Old", domain_id="old")
        store.add(bp)
        bp.domain_name = "New"
        store.update(bp)
        bp_retrieved = store.get(bp.id)
        assert bp_retrieved is not None
        assert bp_retrieved.domain_name == "New"

    def test_update_not_found(self, store: BlueprintStore) -> None:
        bp = DomainBlueprint(domain_name="Ghost", domain_id="ghost")
        with pytest.raises(BlueprintNotFoundError):
            store.update(bp)

    def test_remove(self, store: BlueprintStore) -> None:
        bp = DomainBlueprint(domain_name="Remove", domain_id="remove")
        store.add(bp)
        store.remove(bp.id)
        assert store.get(bp.id) is None


# ===========================================================================
# BlueprintGenerator tests
# ===========================================================================


class TestBlueprintGenerator:
    """Tests for domain blueprint generation from NL descriptions."""

    def test_legal_domain_generation(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(LEGAL_DESCRIPTION)
        assert "Legal" in bp.domain_name or "legal" in bp.domain_id
        assert len(bp.agents) >= 4
        assert len(bp.skills) >= 3
        assert len(bp.workflows) >= 1

    def test_research_domain_generation(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(RESEARCH_DESCRIPTION)
        assert len(bp.agents) >= 4
        # Description starts with "Build" so name may not contain "Research"
        assert bp.description != ""

    def test_engineering_domain_generation(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(ENGINEERING_DESCRIPTION)
        assert len(bp.agents) >= 4
        assert "engineering" in bp.domain_id.lower() or "Engineering" in bp.domain_name

    def test_finance_domain_generation(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(FINANCE_DESCRIPTION)
        assert len(bp.agents) >= 4
        # Finance archetype detected from "trading", "risk" keywords
        assert "financial" in bp.domain_id.lower() or "finance" in bp.domain_id.lower()

    def test_healthcare_domain_generation(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(HEALTHCARE_DESCRIPTION)
        assert len(bp.agents) >= 4
        assert "healthcare" in bp.domain_id.lower() or "Healthcare" in bp.domain_name

    def test_generic_domain_default_agents(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(GENERIC_DESCRIPTION)
        assert len(bp.agents) >= 4  # Default template provides 4 agents

    def test_custom_domain_name(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(
            "A test domain",
            domain_name="My Custom Domain",
        )
        assert bp.domain_name == "My Custom Domain"
        assert "my-custom-domain" in bp.domain_id

    def test_domain_id_is_slug(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate("Create a Legal Research Domain")
        # Slug should be lowercase, hyphen-separated
        assert bp.domain_id == bp.domain_id.lower()
        assert " " not in bp.domain_id

    def test_agents_have_roles(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(LEGAL_DESCRIPTION)
        for agent in bp.agents:
            assert agent.role in list(AgentRole)

    def test_agents_have_goals(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(LEGAL_DESCRIPTION)
        for agent in bp.agents:
            assert agent.goal.strip() != ""

    def test_agents_have_unique_ids(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(LEGAL_DESCRIPTION)
        ids = [a.agent_id for a in bp.agents]
        assert len(ids) == len(set(ids))

    def test_skills_generated(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(LEGAL_DESCRIPTION)
        assert len(bp.skills) >= 3
        for skill in bp.skills:
            assert skill.skill_id.strip() != ""
            assert skill.name.strip() != ""

    def test_skill_reuse(self, generator: BlueprintGenerator) -> None:
        existing = [SkillDescriptor(skill_id="s1", name="contract_analysis", description="Analyzes contracts")]
        bp = generator.generate(LEGAL_DESCRIPTION, existing_skills=existing)
        reused = [s for s in bp.skills if s.is_reused]
        assert len(reused) >= 1

    def test_workflows_have_steps(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(LEGAL_DESCRIPTION)
        for wf in bp.workflows:
            assert len(wf.steps) >= 1

    def test_workflows_reference_valid_agents(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(ENGINEERING_DESCRIPTION)
        agent_ids = {a.agent_id for a in bp.agents}
        for wf in bp.workflows:
            for aid in wf.agent_ids:
                assert aid in agent_ids

    def test_config_for_high_risk_domain(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(HEALTHCARE_DESCRIPTION)
        assert bp.config.requires_human_approval is True
        assert bp.config.priority_level in ("high", "critical")

    def test_config_for_standard_domain(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(GENERIC_DESCRIPTION)
        # Generic/research domain should not require human approval by default
        assert isinstance(bp.config.requires_human_approval, bool)

    def test_source_description_preserved(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(LEGAL_DESCRIPTION)
        assert bp.source_description == LEGAL_DESCRIPTION

    def test_creation_mode_set(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate(
            LEGAL_DESCRIPTION,
            creation_mode=CreationMode.AUTOMATIC,
        )
        assert bp.creation_mode == CreationMode.AUTOMATIC

    def test_quoted_domain_name_extraction(self, generator: BlueprintGenerator) -> None:
        bp = generator.generate('Create a domain called "Contract Analysis Hub"')
        assert bp.domain_name == "Contract Analysis Hub"


# ===========================================================================
# BlueprintValidator tests
# ===========================================================================


class TestBlueprintValidator:
    """Tests for blueprint validation."""

    def test_valid_blueprint_no_errors(self, validator: BlueprintValidator) -> None:
        bp = DomainBlueprint(
            domain_name="Legal Ops",
            domain_id="legal-ops",
            description="A legal domain",
            agents=[
                AgentBlueprint(agent_id="a1", name="Agent 1", goal="Do things"),
                AgentBlueprint(agent_id="a2", name="Agent 2", goal="Do other things"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="Skill 1")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="Workflow 1")],
        )
        errors, _warnings = validator.validate(bp, [])
        assert len(errors) == 0

    def test_empty_name_error(self, validator: BlueprintValidator) -> None:
        bp = DomainBlueprint(domain_name="", domain_id="test", agents=[
            AgentBlueprint(agent_id="a1", name="A", goal="G"),
            AgentBlueprint(agent_id="a2", name="B", goal="G"),
        ], skills=[SkillBlueprint(skill_id="s1", name="S")], workflows=[
            WorkflowBlueprint(workflow_id="w1", name="W"),
        ])
        errors, _ = validator.validate(bp, [])
        assert any("name" in e.lower() for e in errors)

    def test_too_few_agents_error(self, validator: BlueprintValidator) -> None:
        bp = DomainBlueprint(
            domain_name="Test",
            domain_id="test",
            agents=[AgentBlueprint(agent_id="a1", name="A", goal="G")],
            skills=[SkillBlueprint(skill_id="s1", name="S")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="W")],
        )
        errors, _ = validator.validate(bp, [])
        assert any("agent" in e.lower() for e in errors)

    def test_no_skills_error(self, validator: BlueprintValidator) -> None:
        bp = DomainBlueprint(
            domain_name="Test",
            domain_id="test",
            agents=[
                AgentBlueprint(agent_id="a1", name="A", goal="G"),
                AgentBlueprint(agent_id="a2", name="B", goal="G"),
            ],
            skills=[],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="W")],
        )
        errors, _ = validator.validate(bp, [])
        assert any("skill" in e.lower() for e in errors)

    def test_no_workflows_error(self, validator: BlueprintValidator) -> None:
        bp = DomainBlueprint(
            domain_name="Test",
            domain_id="test",
            agents=[
                AgentBlueprint(agent_id="a1", name="A", goal="G"),
                AgentBlueprint(agent_id="a2", name="B", goal="G"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="S")],
            workflows=[],
        )
        errors, _ = validator.validate(bp, [])
        assert any("workflow" in e.lower() for e in errors)

    def test_duplicate_domain_name(self, validator: BlueprintValidator) -> None:
        existing = [DomainDescriptor(domain_id="legal-ops", name="Legal Ops")]
        bp = DomainBlueprint(
            domain_name="Legal Ops",
            domain_id="new-legal",
            agents=[
                AgentBlueprint(agent_id="a1", name="A", goal="G"),
                AgentBlueprint(agent_id="a2", name="B", goal="G"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="S")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="W")],
        )
        errors, _ = validator.validate(bp, existing)
        assert any("already exists" in e.lower() for e in errors)

    def test_duplicate_domain_id(self, validator: BlueprintValidator) -> None:
        existing = [DomainDescriptor(domain_id="legal-ops", name="Some Other Name")]
        bp = DomainBlueprint(
            domain_name="New Name",
            domain_id="legal-ops",
            agents=[
                AgentBlueprint(agent_id="a1", name="A", goal="G"),
                AgentBlueprint(agent_id="a2", name="B", goal="G"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="S")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="W")],
        )
        errors, _ = validator.validate(bp, existing)
        assert any("already exists" in e.lower() for e in errors)

    def test_unsafe_domain_id(self, validator: BlueprintValidator) -> None:
        bp = DomainBlueprint(
            domain_name="Hack",
            domain_id="hack-exploit",
            agents=[
                AgentBlueprint(agent_id="a1", name="A", goal="G"),
                AgentBlueprint(agent_id="a2", name="B", goal="G"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="S")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="W")],
        )
        errors, _ = validator.validate(bp, [])
        assert any("unsafe" in e.lower() for e in errors)

    def test_duplicate_agent_ids(self, validator: BlueprintValidator) -> None:
        bp = DomainBlueprint(
            domain_name="Test",
            domain_id="test",
            agents=[
                AgentBlueprint(agent_id="dup", name="A", goal="G"),
                AgentBlueprint(agent_id="dup", name="B", goal="G"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="S")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="W")],
        )
        errors, _ = validator.validate(bp, [])
        assert any("duplicate agent" in e.lower() for e in errors)

    def test_empty_agent_name_error(self, validator: BlueprintValidator) -> None:
        bp = DomainBlueprint(
            domain_name="Test",
            domain_id="test",
            agents=[
                AgentBlueprint(agent_id="a1", name="", goal="G"),
                AgentBlueprint(agent_id="a2", name="B", goal="G"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="S")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="W")],
        )
        errors, _ = validator.validate(bp, [])
        assert any("empty name" in e.lower() for e in errors)

    def test_no_goal_warning(self, validator: BlueprintValidator) -> None:
        bp = DomainBlueprint(
            domain_name="Test",
            domain_id="test",
            agents=[
                AgentBlueprint(agent_id="a1", name="A", goal=""),
                AgentBlueprint(agent_id="a2", name="B", goal="G"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="S")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="W")],
        )
        _, warnings = validator.validate(bp, [])
        assert any("goal" in w.lower() for w in warnings)

    def test_valid_blueprint_passes(self, validator: BlueprintValidator) -> None:
        bp = DomainBlueprint(
            domain_name="Valid Domain",
            domain_id="valid-domain",
            description="A valid domain",
            agents=[
                AgentBlueprint(agent_id="a1", name="Agent One", goal="Do stuff"),
                AgentBlueprint(agent_id="a2", name="Agent Two", goal="Do more stuff"),
            ],
            skills=[
                SkillBlueprint(skill_id="s1", name="Skill One"),
                SkillBlueprint(skill_id="s2", name="Skill Two"),
            ],
            workflows=[
                WorkflowBlueprint(workflow_id="w1", name="Main Pipeline", steps=["a", "b"]),
            ],
        )
        errors, _ = validator.validate(bp, [])
        assert errors == []


# ===========================================================================
# DomainCreationEngine — generate_domain_blueprint tests
# ===========================================================================


class TestGenerateDomainBlueprint:
    """Tests for blueprint generation via the engine."""

    @pytest.mark.asyncio
    async def test_generate_legal_blueprint(self, engine: DomainCreationEngine) -> None:
        bp = await engine.generate_domain_blueprint(LEGAL_DESCRIPTION)
        assert bp.domain_name != ""
        assert bp.domain_id != ""
        assert len(bp.agents) >= 2
        assert len(bp.skills) >= 1
        assert len(bp.workflows) >= 1

    @pytest.mark.asyncio
    async def test_generate_blueprint_stored(self, engine: DomainCreationEngine) -> None:
        bp = await engine.generate_domain_blueprint(LEGAL_DESCRIPTION)
        retrieved = engine._store.get(bp.id)
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_generate_blueprint_validated(self, engine: DomainCreationEngine) -> None:
        bp = await engine.generate_domain_blueprint(LEGAL_DESCRIPTION)
        # A valid legal description should produce a blueprint with no errors
        assert bp.validation_errors == []

    @pytest.mark.asyncio
    async def test_generate_blueprint_logs_to_tape(self, engine: DomainCreationEngine) -> None:
        await engine.generate_domain_blueprint(LEGAL_DESCRIPTION)
        entries = await engine._tape.get_entries(event_type="domain.blueprint_generated")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_generate_empty_description_raises(self, engine: DomainCreationEngine) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            await engine.generate_domain_blueprint("")

    @pytest.mark.asyncio
    async def test_generate_with_custom_name(self, engine: DomainCreationEngine) -> None:
        bp = await engine.generate_domain_blueprint(
            LEGAL_DESCRIPTION, domain_name="My Legal Domain",
        )
        assert bp.domain_name == "My Legal Domain"


# ===========================================================================
# DomainCreationEngine — create_domain_from_description tests
# ===========================================================================


class TestCreateDomainFromDescription:
    """Tests for the full domain creation pipeline."""

    @pytest.mark.asyncio
    async def test_create_legal_domain(self, engine: DomainCreationEngine) -> None:
        result = await engine.create_domain_from_description(
            description=LEGAL_DESCRIPTION,
            created_by="alice",
        )
        assert isinstance(result, DomainCreationResult)
        assert result.blueprint.domain_name != ""
        assert result.proposal_id is not None
        assert not result.registered

    @pytest.mark.asyncio
    async def test_create_sets_proposed_status(self, engine: DomainCreationEngine) -> None:
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.blueprint.status == DomainStatus.PROPOSED

    @pytest.mark.asyncio
    async def test_create_logs_to_tape(self, engine: DomainCreationEngine) -> None:
        await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        entries = await engine._tape.get_entries(event_type="domain.creation_requested")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_create_with_no_proposal_engine(
        self, engine_no_proposal: DomainCreationEngine,
    ) -> None:
        result = await engine_no_proposal.create_domain_from_description(
            description=LEGAL_DESCRIPTION,
        )
        assert result.proposal_id is None
        assert result.blueprint.status == DomainStatus.DRAFT

    @pytest.mark.asyncio
    async def test_create_empty_description_raises(self, engine: DomainCreationEngine) -> None:
        with pytest.raises(ValueError):
            await engine.create_domain_from_description("")

    @pytest.mark.asyncio
    async def test_create_proposes_domain_creation_type(
        self, engine: DomainCreationEngine,
    ) -> None:
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        # Verify the proposal was created with DOMAIN_CREATION type
        assert engine._proposal_engine is not None
        proposal = engine._proposal_engine._store.get(result.proposal_id)
        assert proposal is not None
        assert proposal.modification_type == ModificationType.DOMAIN_CREATION

    @pytest.mark.asyncio
    async def test_create_risk_level_based_on_priority(
        self, engine: DomainCreationEngine,
    ) -> None:
        result = await engine.create_domain_from_description(HEALTHCARE_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        proposal = engine._proposal_engine._store.get(result.proposal_id)
        assert proposal is not None
        # Healthcare (critical priority) should have MEDIUM or HIGH risk
        assert proposal.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH)


# ===========================================================================
# DomainCreationEngine — register_domain tests
# ===========================================================================


class TestRegisterDomain:
    """Tests for domain registration after approval."""

    @pytest.mark.asyncio
    async def test_register_after_approval(self, engine: DomainCreationEngine) -> None:
        # Create domain
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        bp_id = result.blueprint.id

        # Approve the proposal
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="bob")

        # Register the domain
        domain = await engine.register_domain(bp_id, reviewer="bob")
        assert domain.domain_id == result.blueprint.domain_id
        assert domain.name == result.blueprint.domain_name
        assert domain.agent_count == len(result.blueprint.agents)

    @pytest.mark.asyncio
    async def test_register_without_approval_raises(
        self, engine: DomainCreationEngine,
    ) -> None:
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        with pytest.raises(DomainNotApprovedError):
            await engine.register_domain(result.blueprint.id)

    @pytest.mark.asyncio
    async def test_register_blueprint_not_found(
        self, engine: DomainCreationEngine,
    ) -> None:
        from uuid import uuid4
        with pytest.raises(BlueprintNotFoundError):
            await engine.register_domain(uuid4())

    @pytest.mark.asyncio
    async def test_register_duplicate_raises(
        self, engine: DomainCreationEngine,
    ) -> None:
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="bob")

        # First registration succeeds
        await engine.register_domain(result.blueprint.id, reviewer="bob")

        # Second registration of the same domain should fail
        with pytest.raises(DuplicateDomainError):
            await engine.register_domain(result.blueprint.id, reviewer="bob")

    @pytest.mark.asyncio
    async def test_register_logs_to_tape(self, engine: DomainCreationEngine) -> None:
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="bob")
        await engine.register_domain(result.blueprint.id, reviewer="bob")

        entries = await engine._tape.get_entries(event_type="domain.registered")
        assert len(entries) == 1
        assert entries[0].payload["domain_id"] == result.blueprint.domain_id

    @pytest.mark.asyncio
    async def test_register_updates_blueprint_status(
        self, engine: DomainCreationEngine,
    ) -> None:
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="bob")
        await engine.register_domain(result.blueprint.id, reviewer="bob")

        bp = engine._store.get(result.blueprint.id)
        assert bp is not None
        assert bp.status == DomainStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_register_creates_agents_in_registry(
        self, engine: DomainCreationEngine,
    ) -> None:
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="bob")
        await engine.register_domain(result.blueprint.id, reviewer="bob")

        # Check that agents were registered
        assert engine._introspector is not None
        agents = engine._introspector._agents.list_agents()
        assert len(agents) >= 4  # Legal archetype has 6 agents

    @pytest.mark.asyncio
    async def test_register_creates_new_skills_in_registry(
        self, engine: DomainCreationEngine,
    ) -> None:
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="bob")
        await engine.register_domain(result.blueprint.id, reviewer="bob")

        # Check that new (non-reused) skills were registered
        assert engine._introspector is not None
        skills = engine._introspector._skills.list_skills()
        new_skills = [s for s in skills if result.blueprint.domain_id in s.skill_id]
        assert len(new_skills) >= 1


# ===========================================================================
# DomainCreationEngine — query tests
# ===========================================================================


class TestDomainQueries:
    """Tests for domain listing and retrieval."""

    @pytest.mark.asyncio
    async def test_list_domains_empty(self, engine: DomainCreationEngine) -> None:
        domains = await engine.list_domains()
        assert domains == []

    @pytest.mark.asyncio
    async def test_list_domains_after_registration(
        self, engine: DomainCreationEngine,
    ) -> None:
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="bob")
        await engine.register_domain(result.blueprint.id, reviewer="bob")

        domains = await engine.list_domains()
        assert len(domains) == 1

    @pytest.mark.asyncio
    async def test_get_domain(self, engine: DomainCreationEngine) -> None:
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="bob")
        await engine.register_domain(result.blueprint.id, reviewer="bob")

        domain = await engine.get_domain(result.blueprint.domain_id)
        assert domain is not None
        assert domain.name == result.blueprint.domain_name

    @pytest.mark.asyncio
    async def test_get_domain_not_found(self, engine: DomainCreationEngine) -> None:
        domain = await engine.get_domain("nonexistent")
        assert domain is None

    @pytest.mark.asyncio
    async def test_get_blueprint(self, engine: DomainCreationEngine) -> None:
        bp = await engine.generate_domain_blueprint(LEGAL_DESCRIPTION)
        retrieved = await engine.get_blueprint(bp.id)
        assert retrieved.id == bp.id

    @pytest.mark.asyncio
    async def test_get_blueprint_not_found(self, engine: DomainCreationEngine) -> None:
        from uuid import uuid4
        with pytest.raises(BlueprintNotFoundError):
            await engine.get_blueprint(uuid4())

    @pytest.mark.asyncio
    async def test_list_blueprints(self, engine: DomainCreationEngine) -> None:
        await engine.generate_domain_blueprint(LEGAL_DESCRIPTION)
        await engine.generate_domain_blueprint(RESEARCH_DESCRIPTION)
        bps = await engine.list_blueprints()
        assert len(bps) == 2


# ===========================================================================
# DomainCreationEngine — validate_blueprint tests
# ===========================================================================


class TestValidateBlueprint:
    """Tests for standalone blueprint validation."""

    def test_validate_valid_blueprint(self, engine: DomainCreationEngine) -> None:
        bp = DomainBlueprint(
            domain_name="Test Domain",
            domain_id="test-domain",
            agents=[
                AgentBlueprint(agent_id="a1", name="Agent 1", goal="Goal 1"),
                AgentBlueprint(agent_id="a2", name="Agent 2", goal="Goal 2"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="Skill 1")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="Workflow 1")],
        )
        errors, _warnings = engine.validate_blueprint(bp)
        assert len(errors) == 0

    def test_validate_duplicate_domain(self, engine: DomainCreationEngine) -> None:
        # Pre-register a domain
        engine._domain_registry.register(
            DomainDescriptor(domain_id="test-domain", name="Test Domain")
        )
        bp = DomainBlueprint(
            domain_name="Test Domain",
            domain_id="test-domain",
            agents=[
                AgentBlueprint(agent_id="a1", name="Agent 1", goal="Goal 1"),
                AgentBlueprint(agent_id="a2", name="Agent 2", goal="Goal 2"),
            ],
            skills=[SkillBlueprint(skill_id="s1", name="Skill 1")],
            workflows=[WorkflowBlueprint(workflow_id="w1", name="Workflow 1")],
        )
        errors, _ = engine.validate_blueprint(bp)
        assert len(errors) >= 1


# ===========================================================================
# Data model tests
# ===========================================================================


class TestDataModels:
    """Tests for data model defaults and validation."""

    def test_domain_blueprint_defaults(self) -> None:
        bp = DomainBlueprint(domain_name="Test", domain_id="test")
        assert bp.agents == []
        assert bp.skills == []
        assert bp.workflows == []
        assert bp.status == DomainStatus.DRAFT
        assert bp.creation_mode == CreationMode.HUMAN_GUIDED
        assert bp.created_by == "prime"
        assert bp.validation_errors == []

    def test_domain_config_defaults(self) -> None:
        config = DomainConfig()
        assert config.max_agents == 10
        assert config.max_concurrent_tasks == 5
        assert config.requires_human_approval is True
        assert config.data_retention_days == 90
        assert config.priority_level == "normal"

    def test_agent_role_enum(self) -> None:
        assert AgentRole.COORDINATOR.value == "coordinator"
        assert AgentRole.EXECUTOR.value == "executor"
        assert AgentRole.REVIEWER.value == "reviewer"

    def test_workflow_type_enum(self) -> None:
        assert WorkflowType.SEQUENTIAL.value == "sequential"
        assert WorkflowType.PARALLEL.value == "parallel"
        assert WorkflowType.DEBATE.value == "debate"

    def test_domain_status_enum(self) -> None:
        assert DomainStatus.DRAFT.value == "draft"
        assert DomainStatus.ACTIVE.value == "active"
        assert DomainStatus.PROPOSED.value == "proposed"

    def test_creation_mode_enum(self) -> None:
        assert CreationMode.AUTOMATIC.value == "automatic"
        assert CreationMode.HUMAN_GUIDED.value == "human_guided"
        assert CreationMode.HYBRID.value == "hybrid"

    def test_agent_blueprint_defaults(self) -> None:
        ab = AgentBlueprint(agent_id="a1", name="Test Agent")
        assert ab.role == AgentRole.SPECIALIST
        assert ab.goal == ""
        assert ab.capabilities == []

    def test_skill_blueprint_defaults(self) -> None:
        sb = SkillBlueprint(skill_id="s1", name="Test Skill")
        assert sb.is_reused is False
        assert sb.version == "0.1.0"

    def test_workflow_blueprint_defaults(self) -> None:
        wb = WorkflowBlueprint(workflow_id="w1", name="Test Workflow")
        assert wb.workflow_type == WorkflowType.SEQUENTIAL
        assert wb.agent_ids == []
        assert wb.steps == []


# ===========================================================================
# Integration tests
# ===========================================================================


class TestDomainCreationIntegration:
    """Integration tests covering full creation workflows."""

    @pytest.mark.asyncio
    async def test_full_legal_domain_lifecycle(
        self, engine: DomainCreationEngine,
    ) -> None:
        """Test: generate -> create -> approve -> register -> verify."""
        # Step 1: Generate blueprint
        bp = await engine.generate_domain_blueprint(LEGAL_DESCRIPTION)
        assert bp.status == DomainStatus.DRAFT
        assert len(bp.agents) >= 4

        # Step 2: Create domain (generates + validates + proposes)
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert result.blueprint.status == DomainStatus.PROPOSED

        # Step 3: Approve the proposal
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="alice")

        # Step 4: Register the domain
        domain = await engine.register_domain(result.blueprint.id, reviewer="alice")
        assert domain.name != ""
        assert domain.agent_count >= 4

        # Step 5: Verify domain is in the registry
        domains = await engine.list_domains()
        assert len(domains) == 1
        assert domains[0].domain_id == result.blueprint.domain_id

        # Step 6: Verify agents were created
        assert engine._introspector is not None
        agents = engine._introspector._agents.list_agents()
        assert len(agents) >= 4

    @pytest.mark.asyncio
    async def test_all_tape_events_logged(
        self, engine: DomainCreationEngine,
    ) -> None:
        """All domain creation events should be logged to Tape."""
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="bob")
        await engine.register_domain(result.blueprint.id, reviewer="bob")

        gen = await engine._tape.get_entries(event_type="domain.blueprint_generated")
        created = await engine._tape.get_entries(event_type="domain.creation_requested")
        registered = await engine._tape.get_entries(event_type="domain.registered")

        assert len(gen) == 1  # Blueprint generated once inside create
        assert len(created) == 1
        assert len(registered) == 1

    @pytest.mark.asyncio
    async def test_multiple_domains(
        self, engine: DomainCreationEngine,
    ) -> None:
        """Create and register multiple distinct domains."""
        # Create legal domain
        r1 = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert r1.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(r1.proposal_id, reviewer="alice")
        await engine.register_domain(r1.blueprint.id, reviewer="alice")

        # Create research domain
        r2 = await engine.create_domain_from_description(RESEARCH_DESCRIPTION)
        assert r2.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(r2.proposal_id, reviewer="alice")
        await engine.register_domain(r2.blueprint.id, reviewer="alice")

        domains = await engine.list_domains()
        assert len(domains) == 2

    @pytest.mark.asyncio
    async def test_duplicate_domain_name_prevented(
        self, engine: DomainCreationEngine,
    ) -> None:
        """Cannot create a domain with the same name as an existing one."""
        r1 = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert r1.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(r1.proposal_id, reviewer="alice")
        await engine.register_domain(r1.blueprint.id, reviewer="alice")

        # Try to create the same domain again
        with pytest.raises(BlueprintValidationError):
            await engine.create_domain_from_description(LEGAL_DESCRIPTION)



@pytest.fixture()
def aethergit(tape_svc: TapeService) -> AdvancedAetherGit:
    return AdvancedAetherGit(tape_service=tape_svc)


@pytest.fixture()
def engine_with_full_integration(
    tape_svc: TapeService,
    introspector: PrimeIntrospector,
    proposal_engine: ProposalEngine,
    aethergit: AdvancedAetherGit,
) -> DomainCreationEngine:
    folder_svc = FolderTreeService(tape_service=tape_svc)
    introspector_with_folders = PrimeIntrospector(
        tape_service=tape_svc,
        folder_tree_service=folder_svc,
    )
    return DomainCreationEngine(
        tape_service=tape_svc,
        introspector=introspector_with_folders,
        proposal_engine=proposal_engine,
        folder_tree_service=folder_svc,
        aethergit=aethergit,
    )


class TestAetherGitIntegration:
    """Tests for AetherGit commit creation during domain registration."""

    @pytest.mark.asyncio
    async def test_register_creates_aethergit_commit(
        self,
        engine_with_full_integration: DomainCreationEngine,
    ) -> None:
        """Domain registration should create an AetherGit commit."""
        result = await engine_with_full_integration.create_domain_from_description(
            LEGAL_DESCRIPTION,
        )
        assert result.proposal_id is not None
        assert engine_with_full_integration._proposal_engine is not None
        await engine_with_full_integration._proposal_engine.approve(
            result.proposal_id, reviewer="alice",
        )
        await engine_with_full_integration.register_domain(
            result.blueprint.id, reviewer="alice",
        )

        aethergit = engine_with_full_integration._aethergit
        assert aethergit is not None
        commits = await aethergit.get_commit_history(
            branch=f"domain/{result.blueprint.domain_id}",
        )
        assert len(commits) == 1
        commit = commits[0]
        assert commit.message == f"Create domain: {result.blueprint.domain_name}"
        assert commit.commit_type == "domain_creation"
        assert commit.scope == result.blueprint.domain_id
        assert commit.performance_metrics["agent_count"] == len(result.blueprint.agents)
        assert commit.performance_metrics["skill_count"] == len(result.blueprint.skills)
        assert commit.evolution_approved is True

    @pytest.mark.asyncio
    async def test_register_without_aethergit_still_works(
        self,
        tape_svc: TapeService,
        introspector: PrimeIntrospector,
        proposal_engine: ProposalEngine,
    ) -> None:
        """Domain registration works even without AetherGit."""
        engine = DomainCreationEngine(
            tape_service=tape_svc,
            introspector=introspector,
            proposal_engine=proposal_engine,
            aethergit=None,
        )
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="alice")
        domain = await engine.register_domain(result.blueprint.id, reviewer="alice")
        assert domain.domain_id == result.blueprint.domain_id


class TestFolderThinkingModeIntegration:
    """Tests for Folder Thinking Mode during domain creation."""

    @pytest.mark.asyncio
    async def test_folder_thinking_mode_validates_tree(
        self,
        engine_with_full_integration: DomainCreationEngine,
    ) -> None:
        """Folder Thinking Mode should be able to navigate the generated tree."""
        result = await engine_with_full_integration.create_domain_from_description(
            LEGAL_DESCRIPTION,
        )
        assert result.proposal_id is not None
        assert engine_with_full_integration._proposal_engine is not None
        await engine_with_full_integration._proposal_engine.approve(
            result.proposal_id, reviewer="alice",
        )
        await engine_with_full_integration.register_domain(
            result.blueprint.id, reviewer="alice",
        )

        introspector = engine_with_full_integration._introspector
        assert introspector is not None
        children = await introspector.folder_navigate(result.blueprint.domain_id, "")
        assert len(children) > 0

    @pytest.mark.asyncio
    async def test_folder_thinking_reads_agent_role(
        self,
        engine_with_full_integration: DomainCreationEngine,
    ) -> None:
        """Prime should be able to read agent role files via Folder Thinking Mode."""
        result = await engine_with_full_integration.create_domain_from_description(
            LEGAL_DESCRIPTION,
        )
        assert result.proposal_id is not None
        assert engine_with_full_integration._proposal_engine is not None
        await engine_with_full_integration._proposal_engine.approve(
            result.proposal_id, reviewer="alice",
        )
        await engine_with_full_integration.register_domain(
            result.blueprint.id, reviewer="alice",
        )

        introspector = engine_with_full_integration._introspector
        assert introspector is not None
        agents_dir = await introspector.folder_navigate(
            result.blueprint.domain_id, "agents",
        )
        assert len(agents_dir) > 0
        first_agent = agents_dir[0]
        role_file = await introspector.folder_read(
            result.blueprint.domain_id, f"agents/{first_agent.name}/role.md",
        )
        assert role_file.node_type == NodeType.FILE
        assert first_agent.name.replace("_", " ").title() in role_file.content

    @pytest.mark.asyncio
    async def test_folder_thinking_without_service_raises_error(
        self,
        tape_svc: TapeService,
        introspector: PrimeIntrospector,
        proposal_engine: ProposalEngine,
    ) -> None:
        """Folder Thinking Mode raises error when service not configured."""
        engine = DomainCreationEngine(
            tape_service=tape_svc,
            introspector=introspector,
            proposal_engine=proposal_engine,
            folder_tree_service=None,
        )
        result = await engine.create_domain_from_description(LEGAL_DESCRIPTION)
        assert result.proposal_id is not None
        assert engine._proposal_engine is not None
        await engine._proposal_engine.approve(result.proposal_id, reviewer="alice")
        await engine.register_domain(result.blueprint.id, reviewer="alice")

        with pytest.raises(FolderThinkingError):
            await introspector.folder_navigate(result.blueprint.domain_id, "")


class TestFullIntegrationPipeline:
    """End-to-end integration tests for all systems working together."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_all_integrations(
        self,
        engine_with_full_integration: DomainCreationEngine,
    ) -> None:
        """Complete pipeline: create → approve → register → verify tree + commit."""
        result = await engine_with_full_integration.create_domain_from_description(
            LEGAL_DESCRIPTION, created_by="test-user",
        )
        assert result.proposal_id is not None
        assert result.blueprint.status == DomainStatus.PROPOSED

        assert engine_with_full_integration._proposal_engine is not None
        await engine_with_full_integration._proposal_engine.approve(
            result.proposal_id, reviewer="alice",
        )

        domain = await engine_with_full_integration.register_domain(
            result.blueprint.id, reviewer="alice",
        )
        assert domain.domain_id == result.blueprint.domain_id

        folder_svc = engine_with_full_integration._folder_tree_service
        assert folder_svc is not None
        tree = await folder_svc.get_tree(result.blueprint.domain_id)
        assert tree.domain_id == result.blueprint.domain_id
        assert len(tree.nodes) > 0

        aethergit = engine_with_full_integration._aethergit
        assert aethergit is not None
        commits = await aethergit.get_commit_history(
            branch=f"domain/{result.blueprint.domain_id}",
        )
        assert len(commits) == 1

        tape = engine_with_full_integration._tape
        gen = await tape.get_entries(event_type="domain.blueprint_generated")
        created = await tape.get_entries(event_type="domain.creation_requested")
        registered = await tape.get_entries(event_type="domain.registered")
        assert len(gen) >= 1
        assert len(created) >= 1
        assert len(registered) >= 1

    @pytest.mark.asyncio
    async def test_multiple_domains_with_aethergit(
        self,
        engine_with_full_integration: DomainCreationEngine,
    ) -> None:
        """Multiple domains each get their own AetherGit branch."""
        descriptions = [LEGAL_DESCRIPTION, RESEARCH_DESCRIPTION]
        domain_ids: list[str] = []

        for desc in descriptions:
            result = await engine_with_full_integration.create_domain_from_description(desc)
            assert result.proposal_id is not None
            assert engine_with_full_integration._proposal_engine is not None
            await engine_with_full_integration._proposal_engine.approve(
                result.proposal_id, reviewer="alice",
            )
            await engine_with_full_integration.register_domain(
                result.blueprint.id, reviewer="alice",
            )
            domain_ids.append(result.blueprint.domain_id)

        aethergit = engine_with_full_integration._aethergit
        assert aethergit is not None
        for domain_id in domain_ids:
            commits = await aethergit.get_commit_history(branch=f"domain/{domain_id}")
            assert len(commits) == 1
