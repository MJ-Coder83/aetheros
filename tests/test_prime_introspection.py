"""Unit tests for Prime Deep System Introspection.

Run with:  pytest tests/test_prime_introspection.py -v
"""

import pytest

from packages.prime.introspection import (
    AgentDescriptor,
    AgentRegistry,
    DomainDescriptor,
    DomainRegistry,
    PrimeIntrospector,
    SkillDescriptor,
    SkillRegistry,
    SystemSnapshot,
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
def agent_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.register(
        AgentDescriptor(
            agent_id="agent-001",
            name="CoderBot",
            capabilities=["write_code", "review"],
            status="active",
        )
    )
    registry.register(
        AgentDescriptor(
            agent_id="agent-002",
            name="AnalystBot",
            capabilities=["analyze", "summarize"],
            status="idle",
        )
    )
    return registry


@pytest.fixture()
def skill_registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.register(
        SkillDescriptor(
            skill_id="skill-python",
            name="Python Expert",
            version="1.0.0",
            description="Writes and reviews Python code",
        )
    )
    registry.register(
        SkillDescriptor(
            skill_id="skill-search",
            name="Web Search",
            version="0.5.0",
            description="Searches the web for information",
        )
    )
    return registry


@pytest.fixture()
def domain_registry() -> DomainRegistry:
    registry = DomainRegistry()
    registry.register(
        DomainDescriptor(
            domain_id="domain-codegen",
            name="Code Generation",
            description="Automated code generation and review",
            agent_count=2,
        )
    )
    return registry


@pytest.fixture()
def introspector(
    tape_svc: TapeService,
    agent_registry: AgentRegistry,
    skill_registry: SkillRegistry,
    domain_registry: DomainRegistry,
) -> PrimeIntrospector:
    return PrimeIntrospector(
        tape_service=tape_svc,
        agent_registry=agent_registry,
        skill_registry=skill_registry,
        domain_registry=domain_registry,
    )


# ---------------------------------------------------------------------------
# SystemSnapshot model
# ---------------------------------------------------------------------------


class TestSystemSnapshot:
    def test_snapshot_has_timestamp(self) -> None:
        snap = SystemSnapshot()
        assert snap.timestamp is not None

    def test_snapshot_defaults(self) -> None:
        snap = SystemSnapshot()
        assert snap.agents == []
        assert snap.skills == []
        assert snap.domains == []
        assert snap.health_status == "unknown"
        assert snap.tape_stats == {}


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    def test_register_and_list(self) -> None:
        reg = AgentRegistry()
        reg.register(AgentDescriptor(agent_id="a1", name="Agent One"))
        agents = reg.list_agents()
        assert len(agents) == 1
        assert agents[0].agent_id == "a1"

    def test_unregister(self) -> None:
        reg = AgentRegistry()
        reg.register(AgentDescriptor(agent_id="a1", name="Agent One"))
        reg.unregister("a1")
        assert reg.list_agents() == []

    def test_get_agent_found(self) -> None:
        reg = AgentRegistry()
        reg.register(AgentDescriptor(agent_id="a1", name="Agent One"))
        agent = reg.get_agent("a1")
        assert agent is not None
        assert agent.name == "Agent One"

    def test_get_agent_not_found(self) -> None:
        reg = AgentRegistry()
        assert reg.get_agent("nonexistent") is None

    def test_unregister_nonexistent_is_safe(self) -> None:
        reg = AgentRegistry()
        reg.unregister("does-not-exist")  # should not raise


class TestSkillRegistry:
    def test_register_and_list(self) -> None:
        reg = SkillRegistry()
        reg.register(SkillDescriptor(skill_id="s1", name="Skill One"))
        skills = reg.list_skills()
        assert len(skills) == 1
        assert skills[0].skill_id == "s1"

    def test_unregister(self) -> None:
        reg = SkillRegistry()
        reg.register(SkillDescriptor(skill_id="s1", name="Skill One"))
        reg.unregister("s1")
        assert reg.list_skills() == []


class TestDomainRegistry:
    def test_register_and_list(self) -> None:
        reg = DomainRegistry()
        reg.register(DomainDescriptor(domain_id="d1", name="Domain One"))
        domains = reg.list_domains()
        assert len(domains) == 1
        assert domains[0].domain_id == "d1"


# ---------------------------------------------------------------------------
# PrimeIntrospector — snapshot
# ---------------------------------------------------------------------------


class TestPrimeIntrospectorSnapshot:
    @pytest.mark.asyncio
    async def test_snapshot_returns_system_snapshot(self, introspector: PrimeIntrospector) -> None:
        snapshot = await introspector.snapshot()
        assert isinstance(snapshot, SystemSnapshot)

    @pytest.mark.asyncio
    async def test_snapshot_includes_system_info(self, introspector: PrimeIntrospector) -> None:
        snapshot = await introspector.snapshot()
        assert "python_version" in snapshot.system_info
        assert "platform" in snapshot.system_info

    @pytest.mark.asyncio
    async def test_snapshot_includes_agents(self, introspector: PrimeIntrospector) -> None:
        snapshot = await introspector.snapshot()
        assert len(snapshot.agents) == 2
        agent_ids = {a.agent_id for a in snapshot.agents}
        assert "agent-001" in agent_ids
        assert "agent-002" in agent_ids

    @pytest.mark.asyncio
    async def test_snapshot_includes_skills(self, introspector: PrimeIntrospector) -> None:
        snapshot = await introspector.snapshot()
        assert len(snapshot.skills) == 2
        skill_ids = {s.skill_id for s in snapshot.skills}
        assert "skill-python" in skill_ids

    @pytest.mark.asyncio
    async def test_snapshot_includes_domains(self, introspector: PrimeIntrospector) -> None:
        snapshot = await introspector.snapshot()
        assert len(snapshot.domains) == 1
        assert snapshot.domains[0].domain_id == "domain-codegen"

    @pytest.mark.asyncio
    async def test_snapshot_health_status(self, introspector: PrimeIntrospector) -> None:
        snapshot = await introspector.snapshot()
        assert snapshot.health_status == "healthy"

    @pytest.mark.asyncio
    async def test_snapshot_logs_introspection_to_tape(
        self, introspector: PrimeIntrospector, tape_svc: TapeService
    ) -> None:
        await introspector.snapshot()
        # The introspection itself should be logged
        entries = await tape_svc.get_entries(event_type="prime.introspection")
        assert len(entries) >= 1
        assert entries[0].agent_id == "prime"


# ---------------------------------------------------------------------------
# PrimeIntrospector — query_tape
# ---------------------------------------------------------------------------


class TestPrimeIntrospectorQueryTape:
    @pytest.mark.asyncio
    async def test_query_tape_returns_entries(
        self, introspector: PrimeIntrospector, tape_svc: TapeService
    ) -> None:
        # Pre-populate some tape entries
        await tape_svc.log_event(
            event_type="agent.invoke",
            payload={"tool": "search"},
            agent_id="agent-001",
        )
        await tape_svc.log_event(
            event_type="agent.invoke",
            payload={"tool": "code"},
            agent_id="agent-002",
        )
        entries = await introspector.query_tape(event_type="agent.invoke")
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_query_tape_logs_to_tape(
        self, introspector: PrimeIntrospector, tape_svc: TapeService
    ) -> None:
        await introspector.query_tape(event_type="test")
        entries = await tape_svc.get_entries(event_type="prime.tape_query")
        assert len(entries) == 1
        assert entries[0].payload["filters"]["event_type"] == "test"

    @pytest.mark.asyncio
    async def test_query_tape_with_agent_filter(
        self, introspector: PrimeIntrospector, tape_svc: TapeService
    ) -> None:
        await tape_svc.log_event(event_type="task", payload={}, agent_id="agent-001")
        await tape_svc.log_event(event_type="task", payload={}, agent_id="agent-002")
        entries = await introspector.query_tape(agent_id="agent-001")
        assert all(e.agent_id == "agent-001" for e in entries)


# ---------------------------------------------------------------------------
# PrimeIntrospector — agent/skill/domain lookups
# ---------------------------------------------------------------------------


class TestPrimeIntrospectorLookups:
    @pytest.mark.asyncio
    async def test_get_agent_status_found(
        self, introspector: PrimeIntrospector, tape_svc: TapeService
    ) -> None:
        agent = await introspector.get_agent_status("agent-001")
        assert agent is not None
        assert agent.name == "CoderBot"
        # Should log the lookup
        entries = await tape_svc.get_entries(event_type="prime.agent_lookup")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_get_agent_status_not_found(self, introspector: PrimeIntrospector) -> None:
        agent = await introspector.get_agent_status("nonexistent")
        assert agent is None

    @pytest.mark.asyncio
    async def test_list_skills(
        self, introspector: PrimeIntrospector, tape_svc: TapeService
    ) -> None:
        skills = await introspector.list_skills()
        assert len(skills) == 2
        entries = await tape_svc.get_entries(event_type="prime.skill_list")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_list_domains(
        self, introspector: PrimeIntrospector, tape_svc: TapeService
    ) -> None:
        domains = await introspector.list_domains()
        assert len(domains) == 1
        entries = await tape_svc.get_entries(event_type="prime.domain_list")
        assert len(entries) == 1


# ---------------------------------------------------------------------------
# PrimeIntrospector — empty registries
# ---------------------------------------------------------------------------


class TestPrimeIntrospectorEmpty:
    @pytest.mark.asyncio
    async def test_snapshot_with_empty_registries(self, tape_svc: TapeService) -> None:
        introspector = PrimeIntrospector(tape_service=tape_svc)
        snapshot = await introspector.snapshot()
        assert snapshot.agents == []
        assert snapshot.skills == []
        assert snapshot.domains == []
        assert snapshot.tape_stats["total_entries"] >= 0
