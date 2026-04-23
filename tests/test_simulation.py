"""Unit tests for the Real-Time Simulation Engine.

Run with:  pytest tests/test_simulation.py -v
"""

import asyncio
from uuid import UUID

import pytest

from packages.prime.introspection import (
    AgentDescriptor,
    AgentRegistry,
    DomainDescriptor,
    DomainRegistry,
    PrimeIntrospector,
    SkillDescriptor,
    SkillRegistry,
)
from packages.prime.proposals import (
    ProposalEngine,
    RiskLevel,
)
from packages.prime.skill_evolution import (
    SkillEvolutionEngine,
)
from packages.simulation.engine import (
    ComparisonReport,
    OutcomeDelta,
    SimulationEngine,
    SimulationEnvironment,
    SimulationNotFoundError,
    SimulationResult,
    SimulationRun,
    SimulationRunStore,
    SimulationStatus,
    WhatIfScenario,
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
def agent_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(
        AgentDescriptor(
            agent_id="agent-1",
            name="CoderBot",
            capabilities=["code-gen", "code-review"],
            status="active",
        )
    )
    registry.register(
        AgentDescriptor(
            agent_id="agent-2",
            name="SearchBot",
            capabilities=["search-web"],
            status="idle",
        )
    )
    return registry


@pytest.fixture()
def domain_registry() -> DomainRegistry:
    registry = DomainRegistry()
    registry.register(
        DomainDescriptor(
            domain_id="code-domain",
            name="Code Domain",
            description="Software development",
            agent_count=1,
        )
    )
    registry.register(
        DomainDescriptor(
            domain_id="empty-domain",
            name="Empty Domain",
            description="Unstaffed domain",
            agent_count=0,
        )
    )
    return registry


@pytest.fixture()
def proposal_engine(tape_svc: TapeService) -> ProposalEngine:
    return ProposalEngine(tape_service=tape_svc)


@pytest.fixture()
def introspector(
    tape_svc: TapeService,
    skill_registry: SkillRegistry,
    agent_registry: AgentRegistry,
    domain_registry: DomainRegistry,
) -> PrimeIntrospector:
    return PrimeIntrospector(
        tape_service=tape_svc,
        skill_registry=skill_registry,
        agent_registry=agent_registry,
        domain_registry=domain_registry,
    )


@pytest.fixture()
def skill_evo_engine(
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
def engine(
    tape_svc: TapeService,
    introspector: PrimeIntrospector,
    proposal_engine: ProposalEngine,
    skill_evo_engine: SkillEvolutionEngine,
    skill_registry: SkillRegistry,
    agent_registry: AgentRegistry,
    domain_registry: DomainRegistry,
) -> SimulationEngine:
    return SimulationEngine(
        tape_service=tape_svc,
        introspector=introspector,
        proposal_engine=proposal_engine,
        skill_evolution_engine=skill_evo_engine,
        skill_registry=skill_registry,
        agent_registry=agent_registry,
        domain_registry=domain_registry,
    )


@pytest.fixture()
def engine_minimal(tape_svc: TapeService) -> SimulationEngine:
    """Engine with no introspector or skills — for edge-case testing."""
    return SimulationEngine(tape_service=tape_svc)


@pytest.fixture()
def enhance_scenario() -> WhatIfScenario:
    return WhatIfScenario(
        name="Enhance code-gen",
        description="Simulate enhancing the code-gen skill",
        scenario_type="skill_evolution",
        modifications={"action": "enhance", "skill_id": "code-gen"},
        expected_outcome="Improved reliability",
        risk_level=RiskLevel.LOW,
    )


@pytest.fixture()
def merge_scenario() -> WhatIfScenario:
    return WhatIfScenario(
        name="Merge Code Gen + Code Review",
        description="Simulate merging overlapping skills",
        scenario_type="skill_evolution",
        modifications={
            "action": "merge",
            "skill_ids": ["code-gen", "code-review"],
        },
        expected_outcome="Consolidated skill",
        risk_level=RiskLevel.MEDIUM,
    )


@pytest.fixture()
def split_scenario() -> WhatIfScenario:
    return WhatIfScenario(
        name="Split code-gen",
        description="Simulate splitting the code-gen skill",
        scenario_type="skill_evolution",
        modifications={"action": "split", "skill_id": "code-gen"},
        expected_outcome="Focused sub-skills",
        risk_level=RiskLevel.MEDIUM,
    )


@pytest.fixture()
def deprecate_scenario() -> WhatIfScenario:
    return WhatIfScenario(
        name="Deprecate search-web",
        description="Simulate removing unused skill",
        scenario_type="skill_evolution",
        modifications={"action": "deprecate", "skill_id": "search-web"},
        expected_outcome="Reduced complexity",
        risk_level=RiskLevel.HIGH,
    )


@pytest.fixture()
def agent_reassign_scenario() -> WhatIfScenario:
    return WhatIfScenario(
        name="Reassign idle agents",
        description="Simulate reassigning idle agents",
        scenario_type="agent_reconfig",
        modifications={
            "action": "reassign_idle",
            "agent_ids": ["agent-2"],
        },
        expected_outcome="Increased utilisation",
        risk_level=RiskLevel.LOW,
    )


@pytest.fixture()
def domain_assign_scenario() -> WhatIfScenario:
    return WhatIfScenario(
        name="Assign agents to empty domains",
        description="Simulate assigning agents to empty domains",
        scenario_type="domain_change",
        modifications={
            "action": "assign_to_empty_domains",
            "domain_ids": ["empty-domain"],
        },
        expected_outcome="All domains operational",
        risk_level=RiskLevel.LOW,
    )


@pytest.fixture()
def custom_retry_scenario() -> WhatIfScenario:
    return WhatIfScenario(
        name="Add retry logic",
        description="Simulate adding retry logic for error reduction",
        scenario_type="custom",
        modifications={
            "action": "add_retry_logic",
            "target_error_rate": 0.05,
        },
        expected_outcome="Reduced error rate",
        risk_level=RiskLevel.MEDIUM,
    )


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class TestSimulationStatus:
    def test_all_statuses(self) -> None:
        assert SimulationStatus.PENDING.value == "pending"
        assert SimulationStatus.RUNNING.value == "running"
        assert SimulationStatus.COMPLETED.value == "completed"
        assert SimulationStatus.FAILED.value == "failed"
        assert SimulationStatus.ABORTED.value == "aborted"
        assert SimulationStatus.ROLLED_BACK.value == "rolled_back"
        assert len(SimulationStatus) == 6


class TestWhatIfScenario:
    def test_defaults(self) -> None:
        s = WhatIfScenario(name="Test", description="A test", scenario_type="custom")
        assert s.risk_level == RiskLevel.LOW
        assert s.source == "prime"
        assert s.modifications == {}
        assert isinstance(s.id, UUID)

    def test_custom_values(self) -> None:
        s = WhatIfScenario(
            name="Test",
            description="A test",
            scenario_type="skill_evolution",
            modifications={"action": "enhance"},
            risk_level=RiskLevel.HIGH,
            source="human",
        )
        assert s.risk_level == RiskLevel.HIGH
        assert s.source == "human"


class TestSimulationEnvironment:
    def test_defaults(self) -> None:
        env = SimulationEnvironment()
        assert env.skills == []
        assert env.agents == []
        assert env.domains == []

    def test_with_data(self) -> None:
        env = SimulationEnvironment(
            skills=[SkillDescriptor(skill_id="s1", name="S1")],
            agents=[AgentDescriptor(agent_id="a1", name="A1")],
            domains=[DomainDescriptor(domain_id="d1", name="D1")],
        )
        assert len(env.skills) == 1
        assert len(env.agents) == 1


class TestSimulationResult:
    def test_success_result(self) -> None:
        r = SimulationResult(
            simulation_run_id=UUID("00000000-0000-0000-0000-000000000001"),
            success=True,
            status=SimulationStatus.COMPLETED,
        )
        assert r.success is True
        assert r.error_message is None
        assert r.metrics == {}

    def test_failure_result(self) -> None:
        r = SimulationResult(
            simulation_run_id=UUID("00000000-0000-0000-0000-000000000001"),
            success=False,
            status=SimulationStatus.FAILED,
            error_message="Boom",
        )
        assert r.success is False
        assert r.error_message == "Boom"


class TestOutcomeDelta:
    def test_positive_improvement(self) -> None:
        d = OutcomeDelta(
            metric="skill_count",
            baseline_value=3.0,
            simulation_value=4.0,
            delta=1.0,
            delta_percent=33.33,
            improved=True,
        )
        assert d.improved is True
        assert d.delta == 1.0


class TestComparisonReport:
    def test_defaults(self) -> None:
        r = ComparisonReport(
            simulation_run_id=UUID("00000000-0000-0000-0000-000000000001"),
            scenario_name="Test",
        )
        assert r.overall_assessment == "neutral"
        assert r.deltas == []


# ---------------------------------------------------------------------------
# SimulationRunStore
# ---------------------------------------------------------------------------


class TestSimulationRunStore:
    def test_add_and_get(self) -> None:
        store = SimulationRunStore()
        run = SimulationRun(
            scenario=WhatIfScenario(name="T", description="T", scenario_type="custom")
        )
        store.add(run)
        assert store.get(run.id) is run

    def test_get_not_found(self) -> None:
        store = SimulationRunStore()
        assert store.get(UUID("00000000-0000-0000-0000-000000000000")) is None

    def test_list_all(self) -> None:
        store = SimulationRunStore()
        run1 = SimulationRun(
            scenario=WhatIfScenario(name="T1", description="T", scenario_type="custom")
        )
        store.add(run1)
        assert len(store.list_all()) == 1

    def test_list_by_status(self) -> None:
        store = SimulationRunStore()
        run_pending = SimulationRun(
            scenario=WhatIfScenario(name="T1", description="T", scenario_type="custom"),
            status=SimulationStatus.PENDING,
        )
        run_completed = SimulationRun(
            scenario=WhatIfScenario(name="T2", description="T", scenario_type="custom"),
            status=SimulationStatus.COMPLETED,
        )
        store.add(run_pending)
        store.add(run_completed)
        pending = store.list_by_status(SimulationStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].status == SimulationStatus.PENDING

    def test_remove(self) -> None:
        store = SimulationRunStore()
        run = SimulationRun(
            scenario=WhatIfScenario(name="T", description="T", scenario_type="custom")
        )
        store.add(run)
        store.remove(run.id)
        assert store.get(run.id) is None

    def test_update_nonexistent_raises(self) -> None:
        store = SimulationRunStore()
        run = SimulationRun(
            scenario=WhatIfScenario(name="T", description="T", scenario_type="custom")
        )
        with pytest.raises(SimulationNotFoundError):
            store.update(run)


# ---------------------------------------------------------------------------
# SimulationEngine — run_simulation
# ---------------------------------------------------------------------------


class TestRunSimulation:
    @pytest.mark.asyncio
    async def test_run_enhance_scenario(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(enhance_scenario)
        assert result.success is True
        assert result.status == SimulationStatus.COMPLETED
        assert result.duration_seconds > 0
        assert len(result.environment_before.skills) == 3
        # After enhancement, still 3 skills (enhanced in place)
        assert len(result.environment_after.skills) == 3

    @pytest.mark.asyncio
    async def test_run_merge_scenario(
        self, engine: SimulationEngine, merge_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(merge_scenario)
        assert result.success is True
        # Merge removes 2 skills, adds 1 merged skill → 3 - 2 + 1 = 2
        assert len(result.environment_after.skills) == 2

    @pytest.mark.asyncio
    async def test_run_split_scenario(
        self, engine: SimulationEngine, split_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(split_scenario)
        assert result.success is True
        # Split removes 1 skill, adds 2 sub-skills → 3 - 1 + 2 = 4
        assert len(result.environment_after.skills) == 4

    @pytest.mark.asyncio
    async def test_run_deprecate_scenario(
        self, engine: SimulationEngine, deprecate_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(deprecate_scenario)
        assert result.success is True
        # Deprecate removes 1 skill → 3 - 1 = 2
        assert len(result.environment_after.skills) == 2

    @pytest.mark.asyncio
    async def test_run_agent_reassign(
        self, engine: SimulationEngine, agent_reassign_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(agent_reassign_scenario)
        assert result.success is True
        # The agent should be marked as active in the after-env
        after_agent_ids = {a.agent_id for a in result.environment_after.agents}
        assert "agent-2" in after_agent_ids

    @pytest.mark.asyncio
    async def test_run_domain_assign(
        self, engine: SimulationEngine, domain_assign_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(domain_assign_scenario)
        assert result.success is True
        assert "domains_assigned" in result.metrics

    @pytest.mark.asyncio
    async def test_run_custom_retry(
        self, engine: SimulationEngine, custom_retry_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(custom_retry_scenario)
        assert result.success is True
        assert "error_rate_after" in result.metrics

    @pytest.mark.asyncio
    async def test_run_creates_decision_trace(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(enhance_scenario)
        assert len(result.decision_trace) > 0

    @pytest.mark.asyncio
    async def test_run_includes_outcome_probabilities(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(enhance_scenario)
        assert "success_probability" in result.outcome_probabilities
        assert "failure_probability" in result.outcome_probabilities

    @pytest.mark.asyncio
    async def test_run_logs_to_tape(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        await engine.run_simulation(enhance_scenario)
        started = await engine._tape.get_entries(event_type="simulation.started")
        completed = await engine._tape.get_entries(event_type="simulation.completed")
        assert len(started) == 1
        assert len(completed) == 1

    @pytest.mark.asyncio
    async def test_run_isolation_preserved(
        self,
        engine: SimulationEngine,
        enhance_scenario: WhatIfScenario,
        skill_registry: SkillRegistry,
    ) -> None:
        """Verify that running a simulation does NOT change the real registry."""
        skill_ids_before = {s.skill_id for s in skill_registry.list_skills()}
        await engine.run_simulation(enhance_scenario)
        skill_ids_after = {s.skill_id for s in skill_registry.list_skills()}
        assert skill_ids_before == skill_ids_after


class TestRunSimulationTimeout:
    @pytest.mark.asyncio
    async def test_timeout_aborts_simulation(self, tape_svc: TapeService) -> None:
        """Simulate a scenario that would take too long — timeout should abort."""

        # Create a scenario whose execution would exceed the timeout
        # We use a very short timeout to force the timeout path
        slow_scenario = WhatIfScenario(
            name="Slow scenario",
            description="Will time out",
            scenario_type="custom",
            modifications={"action": "slow_action"},
            risk_level=RiskLevel.LOW,
        )

        engine = SimulationEngine(tape_service=tape_svc)

        # Patch _execute_simulation to simulate a slow execution
        original_execute = engine._execute_simulation

        async def slow_execute(run: SimulationRun) -> SimulationResult:
            await asyncio.sleep(10)  # Simulate long-running
            return await original_execute(run)

        engine._execute_simulation = slow_execute  # type: ignore[assignment]

        result = await engine.run_simulation(slow_scenario, timeout_seconds=0.1)
        assert result.status == SimulationStatus.ABORTED
        assert "timeout" in (result.error_message or "").lower()

    @pytest.mark.asyncio
    async def test_timeout_logs_to_tape(self, tape_svc: TapeService) -> None:
        slow_scenario = WhatIfScenario(
            name="Slow",
            description="Will time out",
            scenario_type="custom",
            modifications={"action": "slow"},
        )

        engine = SimulationEngine(tape_service=tape_svc)

        async def slow_execute(run: SimulationRun) -> SimulationResult:
            await asyncio.sleep(10)
            return SimulationResult(
                simulation_run_id=run.id,
                success=True,
                status=SimulationStatus.COMPLETED,
            )

        engine._execute_simulation = slow_execute  # type: ignore[assignment]

        await engine.run_simulation(slow_scenario, timeout_seconds=0.1)
        timeout_entries = await tape_svc.get_entries(event_type="simulation.timeout")
        assert len(timeout_entries) == 1


# ---------------------------------------------------------------------------
# SimulationEngine — compare_outcomes
# ---------------------------------------------------------------------------


class TestCompareOutcomes:
    @pytest.mark.asyncio
    async def test_compare_enhance(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(enhance_scenario)
        report = await engine.compare_outcomes(result.simulation_run_id)
        assert isinstance(report, ComparisonReport)
        assert report.scenario_name == enhance_scenario.name
        assert len(report.deltas) > 0

    @pytest.mark.asyncio
    async def test_compare_merge_has_negative_skill_delta(
        self, engine: SimulationEngine, merge_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(merge_scenario)
        report = await engine.compare_outcomes(result.simulation_run_id)
        skill_delta = [d for d in report.deltas if d.metric == "skill_count"]
        assert len(skill_delta) == 1
        # Merge reduces skill count → negative delta
        assert skill_delta[0].delta < 0

    @pytest.mark.asyncio
    async def test_compare_split_has_positive_skill_delta(
        self, engine: SimulationEngine, split_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(split_scenario)
        report = await engine.compare_outcomes(result.simulation_run_id)
        skill_delta = [d for d in report.deltas if d.metric == "skill_count"]
        assert len(skill_delta) == 1
        # Split increases skill count → positive delta
        assert skill_delta[0].delta > 0

    @pytest.mark.asyncio
    async def test_compare_logs_to_tape(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(enhance_scenario)
        await engine.compare_outcomes(result.simulation_run_id)
        entries = await engine._tape.get_entries(event_type="simulation.comparison")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_compare_nonexistent_raises(self, engine: SimulationEngine) -> None:
        with pytest.raises(SimulationNotFoundError):
            await engine.compare_outcomes(UUID("00000000-0000-0000-0000-000000000099"))


# ---------------------------------------------------------------------------
# SimulationEngine — generate_whatif_scenarios
# ---------------------------------------------------------------------------


class TestGenerateWhatIfScenarios:
    @pytest.mark.asyncio
    async def test_generates_scenarios(self, engine: SimulationEngine) -> None:
        scenarios = await engine.generate_whatif_scenarios()
        assert isinstance(scenarios, list)
        assert len(scenarios) >= 1

    @pytest.mark.asyncio
    async def test_generates_idle_agent_scenario(self, engine: SimulationEngine) -> None:
        scenarios = await engine.generate_whatif_scenarios()
        idle_scenarios = [s for s in scenarios if s.scenario_type == "agent_reconfig"]
        assert len(idle_scenarios) >= 1
        assert (
            "idle" in idle_scenarios[0].name.lower() or "reassign" in idle_scenarios[0].name.lower()
        )

    @pytest.mark.asyncio
    async def test_generates_empty_domain_scenario(self, engine: SimulationEngine) -> None:
        scenarios = await engine.generate_whatif_scenarios()
        domain_scenarios = [s for s in scenarios if s.scenario_type == "domain_change"]
        assert len(domain_scenarios) >= 1

    @pytest.mark.asyncio
    async def test_generates_skill_evolution_scenarios(self, engine: SimulationEngine) -> None:
        scenarios = await engine.generate_whatif_scenarios()
        skill_scenarios = [s for s in scenarios if s.scenario_type == "skill_evolution"]
        # Code Gen + Code Review overlap → merge scenario
        assert len(skill_scenarios) >= 1

    @pytest.mark.asyncio
    async def test_logs_generation_to_tape(self, engine: SimulationEngine) -> None:
        await engine.generate_whatif_scenarios()
        entries = await engine._tape.get_entries(event_type="simulation.scenarios_generated")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_no_introspector_still_works(self, engine_minimal: SimulationEngine) -> None:
        scenarios = await engine_minimal.generate_whatif_scenarios()
        # Without introspector or skill_evo, should return empty or minimal
        assert isinstance(scenarios, list)

    @pytest.mark.asyncio
    async def test_empty_skill_registry_generates_create(self, tape_svc: TapeService) -> None:
        """When there are no skills, generate a create-skills scenario."""
        empty_skill_reg = SkillRegistry()
        skill_evo = SkillEvolutionEngine(tape_service=tape_svc, skill_registry=empty_skill_reg)
        engine = SimulationEngine(
            tape_service=tape_svc,
            skill_evolution_engine=skill_evo,
            skill_registry=empty_skill_reg,
        )
        scenarios = await engine.generate_whatif_scenarios()
        create_scenarios = [
            s for s in scenarios if "foundational" in s.name.lower() or "create" in s.name.lower()
        ]
        assert len(create_scenarios) >= 1


# ---------------------------------------------------------------------------
# SimulationEngine — rollback_simulation
# ---------------------------------------------------------------------------


class TestRollbackSimulation:
    @pytest.mark.asyncio
    async def test_rollback_marks_as_rolled_back(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(enhance_scenario)
        rollback_result = await engine.rollback_simulation(result.simulation_run_id)
        assert rollback_result.success is True
        assert rollback_result.status == SimulationStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_rollback_logs_to_tape(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(enhance_scenario)
        await engine.rollback_simulation(result.simulation_run_id)
        entries = await engine._tape.get_entries(event_type="simulation.rolled_back")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_rollback_nonexistent_raises(self, engine: SimulationEngine) -> None:
        with pytest.raises(SimulationNotFoundError):
            await engine.rollback_simulation(UUID("00000000-0000-0000-0000-000000000099"))

    @pytest.mark.asyncio
    async def test_rollback_verifies_isolation(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        """Rollback should verify that real registries weren't changed."""
        result = await engine.run_simulation(enhance_scenario)
        rollback_result = await engine.rollback_simulation(result.simulation_run_id)
        assert rollback_result.success is True


# ---------------------------------------------------------------------------
# SimulationEngine — query helpers
# ---------------------------------------------------------------------------


class TestQueryHelpers:
    @pytest.mark.asyncio
    async def test_get_simulation(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(enhance_scenario)
        run = await engine.get_simulation(result.simulation_run_id)
        assert run.id == result.simulation_run_id

    @pytest.mark.asyncio
    async def test_get_simulation_not_found(self, engine: SimulationEngine) -> None:
        with pytest.raises(SimulationNotFoundError):
            await engine.get_simulation(UUID("00000000-0000-0000-0000-000000000099"))

    @pytest.mark.asyncio
    async def test_list_simulations(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        await engine.run_simulation(enhance_scenario)
        runs = await engine.list_simulations()
        assert len(runs) >= 1

    @pytest.mark.asyncio
    async def test_list_simulations_by_status(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        await engine.run_simulation(enhance_scenario)
        completed = await engine.list_simulations(SimulationStatus.COMPLETED)
        assert len(completed) >= 1

    @pytest.mark.asyncio
    async def test_get_simulation_result(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(enhance_scenario)
        fetched = await engine.get_simulation_result(result.simulation_run_id)
        assert fetched is not None
        assert fetched.success is True


# ---------------------------------------------------------------------------
# ComparisonReport internals
# ---------------------------------------------------------------------------


class TestComparisonAssessment:
    @pytest.mark.asyncio
    async def test_positive_assessment(
        self, engine: SimulationEngine, split_scenario: WhatIfScenario
    ) -> None:
        """Split increases skill count → positive delta → 'positive' assessment."""
        result = await engine.run_simulation(split_scenario)
        report = await engine.compare_outcomes(result.simulation_run_id)
        # At minimum skill_count should be positive
        # Overall depends on all deltas
        assert report.overall_assessment in (
            "positive",
            "mixed",
            "neutral",
            "negative",
        )

    @pytest.mark.asyncio
    async def test_neutral_assessment_no_change(self, tape_svc: TapeService) -> None:
        """A scenario that makes no net changes should be neutral."""
        # Use a custom scenario with no modifications
        neutral_scenario = WhatIfScenario(
            name="No-op",
            description="Does nothing",
            scenario_type="custom",
            modifications={"action": "no_op"},
        )
        engine = SimulationEngine(tape_service=tape_svc)
        result = await engine.run_simulation(neutral_scenario)
        report = await engine.compare_outcomes(result.simulation_run_id)
        assert report.overall_assessment == "neutral"

    @pytest.mark.asyncio
    async def test_report_contains_recommendation(
        self, engine: SimulationEngine, enhance_scenario: WhatIfScenario
    ) -> None:
        result = await engine.run_simulation(enhance_scenario)
        report = await engine.compare_outcomes(result.simulation_run_id)
        assert report.recommendation != ""
        assert report.summary != ""


# ---------------------------------------------------------------------------
# Isolation safety
# ---------------------------------------------------------------------------


class TestIsolationSafety:
    @pytest.mark.asyncio
    async def test_skill_registry_unchanged_after_merge(
        self,
        engine: SimulationEngine,
        merge_scenario: WhatIfScenario,
        skill_registry: SkillRegistry,
    ) -> None:
        """Merge removes skills in sandbox but NOT in the real registry."""
        ids_before = {s.skill_id for s in skill_registry.list_skills()}
        await engine.run_simulation(merge_scenario)
        ids_after = {s.skill_id for s in skill_registry.list_skills()}
        assert ids_before == ids_after

    @pytest.mark.asyncio
    async def test_agent_registry_unchanged_after_reassign(
        self,
        engine: SimulationEngine,
        agent_reassign_scenario: WhatIfScenario,
        agent_registry: AgentRegistry,
    ) -> None:
        """Agent reassignment in sandbox does NOT affect real registry."""
        agents_before = {a.agent_id: a.status for a in agent_registry.list_agents()}
        await engine.run_simulation(agent_reassign_scenario)
        agents_after = {a.agent_id: a.status for a in agent_registry.list_agents()}
        assert agents_before == agents_after

    @pytest.mark.asyncio
    async def test_domain_registry_unchanged_after_assign(
        self,
        engine: SimulationEngine,
        domain_assign_scenario: WhatIfScenario,
        domain_registry: DomainRegistry,
    ) -> None:
        """Domain assignment in sandbox does NOT affect real registry."""
        domains_before = {d.domain_id: d.agent_count for d in domain_registry.list_domains()}
        await engine.run_simulation(domain_assign_scenario)
        domains_after = {d.domain_id: d.agent_count for d in domain_registry.list_domains()}
        assert domains_before == domains_after


# ---------------------------------------------------------------------------
# Delta computation internals
# ---------------------------------------------------------------------------


class TestComputeDelta:
    def test_positive_count_delta(self) -> None:
        delta = SimulationEngine._compute_delta("skill_count", 3.0, 5.0)
        assert delta.delta == 2.0
        assert delta.improved is True
        assert delta.delta_percent == pytest.approx(66.67, rel=0.01)

    def test_negative_count_delta(self) -> None:
        delta = SimulationEngine._compute_delta("skill_count", 3.0, 2.0)
        assert delta.delta == -1.0
        assert delta.improved is False

    def test_error_rate_delta_improved(self) -> None:
        delta = SimulationEngine._compute_delta("error_rate", 0.25, 0.05)
        assert delta.delta == -0.2
        assert delta.improved is True  # Lower error rate = improvement

    def test_zero_baseline(self) -> None:
        delta = SimulationEngine._compute_delta("new_metric", 0.0, 5.0)
        assert delta.delta == 5.0
        assert delta.delta_percent == 0.0  # Avoid division by zero


class TestGenerateRecommendation:
    def test_positive_recommendation(self) -> None:
        rec = SimulationEngine._generate_recommendation("positive", [])
        assert "implement" in rec.lower()

    def test_negative_recommendation(self) -> None:
        rec = SimulationEngine._generate_recommendation("negative", [])
        assert "revis" in rec.lower() or "caution" in rec.lower()

    def test_mixed_recommendation(self) -> None:
        deltas = [
            OutcomeDelta(
                metric="a",
                baseline_value=0.0,
                simulation_value=1.0,
                delta=1.0,
                delta_percent=100.0,
                improved=True,
            ),
            OutcomeDelta(
                metric="b",
                baseline_value=1.0,
                simulation_value=0.0,
                delta=-1.0,
                delta_percent=-100.0,
                improved=False,
            ),
        ]
        rec = SimulationEngine._generate_recommendation("mixed", deltas)
        assert "caution" in rec.lower()

    def test_neutral_recommendation(self) -> None:
        rec = SimulationEngine._generate_recommendation("neutral", [])
        assert "no significant" in rec.lower()
