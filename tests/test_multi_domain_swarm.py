"""Comprehensive tests for Multi-Domain Swarm features.

Tests cover:
- Data models (ConflictSeverity, ConflictStatus, CrossDomainConflict,
  ConflictResolutionResult, DomainGroup, MultiDomainSwarmConfig,
  MultiDomainSwarmProgress, MultiDomainSwarmResult)
- MultiDomainSwarmEngine._initialize_domain_groups
- MultiDomainSwarmEngine._detect_conflicts
- MultiDomainSwarmEngine._auto_resolve_conflict
- MultiDomainSwarmEngine.run() full pipeline
- SwarmIntegration.run_multi_domain_swarm
- CanvasV5Engine.run_multi_domain_swarm
- Edge cases (single domain, three domains, empty agent_ids, max_conflicts)
"""

from __future__ import annotations

import pytest

from packages.canvas.canvas_v5 import (
    CanvasV5Engine,
    ConflictResolutionResult,
    ConflictSeverity,
    ConflictStatus,
    CrossDomainConflict,
    DomainGroup,
    MultiDomainSwarmConfig,
    MultiDomainSwarmEngine,
    MultiDomainSwarmProgress,
    MultiDomainSwarmResult,
    SwarmIntegration,
)
from packages.canvas.core import CanvasService
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tape_repo() -> InMemoryTapeRepository:
    return InMemoryTapeRepository()


@pytest.fixture()
def tape_service(tape_repo: InMemoryTapeRepository) -> TapeService:
    return TapeService(tape_repo)


@pytest.fixture()
def canvas_service(tape_service: TapeService) -> CanvasService:
    return CanvasService(tape_service)


@pytest.fixture()
def swarm_engine(tape_service: TapeService) -> MultiDomainSwarmEngine:
    return MultiDomainSwarmEngine(tape_service)


@pytest.fixture()
def swarm_integration(tape_service: TapeService) -> SwarmIntegration:
    return SwarmIntegration(tape_service)


@pytest.fixture()
def canvas_v5_engine(
    tape_service: TapeService,
    canvas_service: CanvasService,
) -> CanvasV5Engine:
    return CanvasV5Engine(tape_service, canvas_service)


# ===========================================================================
# Group A: Data Model Tests
# ===========================================================================


class TestConflictSeverity:
    """Tests for ConflictSeverity enum values."""

    def test_low_value(self) -> None:
        assert ConflictSeverity.LOW == "low"

    def test_medium_value(self) -> None:
        assert ConflictSeverity.MEDIUM == "medium"

    def test_high_value(self) -> None:
        assert ConflictSeverity.HIGH == "high"

    def test_critical_value(self) -> None:
        assert ConflictSeverity.CRITICAL == "critical"


class TestConflictStatus:
    """Tests for ConflictStatus enum values."""

    def test_detected_value(self) -> None:
        assert ConflictStatus.DETECTED == "detected"

    def test_in_resolution_value(self) -> None:
        assert ConflictStatus.IN_RESOLUTION == "in_resolution"

    def test_resolved_value(self) -> None:
        assert ConflictStatus.RESOLVED == "resolved"

    def test_escalated_value(self) -> None:
        assert ConflictStatus.ESCALATED == "escalated"


class TestCrossDomainConflict:
    """Tests for CrossDomainConflict model."""

    def test_creation_with_defaults(self) -> None:
        conflict = CrossDomainConflict(
            domain_ids=["domain-a", "domain-b"],
            agent_ids=["agent-1", "agent-2"],
        )
        assert conflict.description == ""
        assert conflict.severity == ConflictSeverity.MEDIUM
        assert conflict.status == ConflictStatus.DETECTED
        assert conflict.resolution == ""
        assert conflict.debate_id is None
        assert conflict.simulation_run_id is None
        assert conflict.id != ""

    def test_creation_with_all_fields(self) -> None:
        conflict = CrossDomainConflict(
            domain_ids=["d1", "d2"],
            agent_ids=["a1", "a2"],
            description="Overlap detected",
            severity=ConflictSeverity.HIGH,
            status=ConflictStatus.ESCALATED,
            resolution="Deferred",
            debate_id="debate-123",
            simulation_run_id="sim-456",
        )
        assert conflict.description == "Overlap detected"
        assert conflict.severity == ConflictSeverity.HIGH
        assert conflict.status == ConflictStatus.ESCALATED
        assert conflict.resolution == "Deferred"
        assert conflict.debate_id == "debate-123"
        assert conflict.simulation_run_id == "sim-456"


class TestConflictResolutionResult:
    """Tests for ConflictResolutionResult model."""

    def test_defaults_success_true(self) -> None:
        result = ConflictResolutionResult(
            conflict_id="c-1",
            method="auto_resolved",
        )
        assert result.success is True
        assert result.resolution == ""
        assert result.debate_result is None
        assert result.simulation_result is None


class TestDomainGroup:
    """Tests for DomainGroup model."""

    def test_creation_with_defaults(self) -> None:
        group = DomainGroup(domain_id="legal")
        assert group.domain_name == ""
        assert group.color == "#6366f1"
        assert group.agent_ids == []
        assert group.node_ids == []
        assert group.position == {"x": 0.0, "y": 0.0}


class TestMultiDomainSwarmConfig:
    """Tests for MultiDomainSwarmConfig model."""

    def test_defaults(self) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2"],
            task="Test task",
        )
        assert config.governed is False
        assert config.agent_ids is None
        assert config.max_conflicts == 10
        assert config.auto_resolve_conflicts is True
        assert config.simulate_before_execute is True
        assert config.debate_format == "standard"
        assert config.max_debate_rounds == 3
        assert config.impact_analysis_enabled is True
        assert config.folder_path == "/swarms/multi_domain/current_task/"
        assert len(config.color_palette) == 8


class TestMultiDomainSwarmProgress:
    """Tests for MultiDomainSwarmProgress model."""

    def test_defaults(self) -> None:
        progress = MultiDomainSwarmProgress(swarm_id="sw-1")
        assert progress.status == "initializing"
        assert progress.domain_groups == []
        assert progress.conflicts == []
        assert progress.resolved_conflicts == 0
        assert progress.total_conflicts == 0
        assert progress.simulation_completed is False
        assert progress.impact_reports == []
        assert progress.current_phase == "initialization"
        assert progress.progress_percent == 0.0


class TestMultiDomainSwarmResult:
    """Tests for MultiDomainSwarmResult model."""

    def test_defaults(self) -> None:
        result = MultiDomainSwarmResult(
            task="Test",
            domain_ids=["d1"],
        )
        assert result.status == "completed"
        assert result.mode == "quick"
        assert result.domain_groups == []
        assert result.participants == []
        assert result.results == []
        assert result.conflicts == []
        assert result.conflict_resolutions == []
        assert result.simulation_completed is False
        assert result.simulation_passed is True
        assert result.impact_severity == "low"
        assert result.folder_path == ""
        assert result.aethergit_branch == ""
        assert result.explanation_id == ""
        assert result.duration_ms == 0.0
        assert result.swarm_id != ""


# ===========================================================================
# Group B: MultiDomainSwarmEngine._initialize_domain_groups
# ===========================================================================


class TestInitializeDomainGroups:
    """Tests for MultiDomainSwarmEngine._initialize_domain_groups."""

    async def test_creates_one_group_per_domain(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["legal", "finance", "engineering"],
            task="Test",
        )
        groups = await swarm_engine._initialize_domain_groups(config)
        assert len(groups) == 3
        assert [g.domain_id for g in groups] == ["legal", "finance", "engineering"]

    async def test_assigns_colors_from_palette(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2"],
            task="Test",
        )
        groups = await swarm_engine._initialize_domain_groups(config)
        palette = config.color_palette
        assert groups[0].color == palette[0]
        assert groups[1].color == palette[1]

    async def test_wraps_around_palette(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        # 8 colors in default palette, use 10 domains to test wrap-around
        domain_ids = [f"d{i}" for i in range(10)]
        config = MultiDomainSwarmConfig(domain_ids=domain_ids, task="Test")
        groups = await swarm_engine._initialize_domain_groups(config)
        palette = config.color_palette
        # Index 8 wraps to 0, index 9 wraps to 1
        assert groups[8].color == palette[8 % len(palette)]
        assert groups[9].color == palette[9 % len(palette)]

    async def test_position_x_proportional_to_index(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d0", "d1", "d2"],
            task="Test",
        )
        groups = await swarm_engine._initialize_domain_groups(config)
        assert groups[0].position["x"] == 0.0
        assert groups[1].position["x"] == 200.0
        assert groups[2].position["x"] == 400.0

    async def test_uses_agent_ids_from_config(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2"],
            task="Test",
            agent_ids=["agent-a", "agent-b"],
        )
        groups = await swarm_engine._initialize_domain_groups(config)
        for group in groups:
            assert group.agent_ids == ["agent-a", "agent-b"]

    async def test_empty_agent_ids_when_none(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1"],
            task="Test",
            agent_ids=None,
        )
        groups = await swarm_engine._initialize_domain_groups(config)
        assert groups[0].agent_ids == []

    async def test_logs_domain_groups_initialized_to_tape(
        self, swarm_engine: MultiDomainSwarmEngine, tape_service: TapeService
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2"],
            task="Test",
        )
        await swarm_engine._initialize_domain_groups(config)
        events = await tape_service.get_entries(
            event_type="canvas.multi_domain_swarm.domain_groups_initialized"
        )
        assert len(events) >= 1


# ===========================================================================
# Group C: MultiDomainSwarmEngine._detect_conflicts
# ===========================================================================


class TestDetectConflicts:
    """Tests for MultiDomainSwarmEngine._detect_conflicts."""

    async def test_detects_conflicts_between_domain_pairs(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        groups = [
            DomainGroup(domain_id="d1", agent_ids=["a1"]),
            DomainGroup(domain_id="d2", agent_ids=["a2"]),
        ]
        conflicts = await swarm_engine._detect_conflicts(groups, "Test task")
        assert len(conflicts) == 1
        assert set(conflicts[0].domain_ids) == {"d1", "d2"}

    async def test_returns_empty_when_no_agent_ids(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        groups = [
            DomainGroup(domain_id="d1", agent_ids=[]),
            DomainGroup(domain_id="d2", agent_ids=[]),
        ]
        conflicts = await swarm_engine._detect_conflicts(groups, "Test task")
        assert conflicts == []

    async def test_creates_conflicts_with_medium_severity_and_detected_status(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        groups = [
            DomainGroup(domain_id="d1", agent_ids=["a1"]),
            DomainGroup(domain_id="d2", agent_ids=["a2"]),
        ]
        conflicts = await swarm_engine._detect_conflicts(groups, "Test task")
        assert conflicts[0].severity == ConflictSeverity.MEDIUM
        assert conflicts[0].status == ConflictStatus.DETECTED

    async def test_description_includes_both_domain_ids(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        groups = [
            DomainGroup(domain_id="alpha", agent_ids=["a1"]),
            DomainGroup(domain_id="beta", agent_ids=["b1"]),
        ]
        conflicts = await swarm_engine._detect_conflicts(groups, "Do stuff")
        assert "alpha" in conflicts[0].description
        assert "beta" in conflicts[0].description

    async def test_logs_conflicts_detected_to_tape(
        self, swarm_engine: MultiDomainSwarmEngine, tape_service: TapeService
    ) -> None:
        groups = [
            DomainGroup(domain_id="d1", agent_ids=["a1"]),
            DomainGroup(domain_id="d2", agent_ids=["a2"]),
        ]
        await swarm_engine._detect_conflicts(groups, "Test task")
        events = await tape_service.get_entries(
            event_type="canvas.multi_domain_swarm.conflicts_detected"
        )
        assert len(events) >= 1

    async def test_correct_conflict_count_formula(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        """n*(n-1)/2 conflicts for n groups with agents."""
        groups = [
            DomainGroup(domain_id=f"d{i}", agent_ids=[f"a{i}"])
            for i in range(4)
        ]
        conflicts = await swarm_engine._detect_conflicts(groups, "Test")
        # 4 * 3 / 2 = 6
        assert len(conflicts) == 6


# ===========================================================================
# Group D: MultiDomainSwarmEngine._auto_resolve_conflict
# ===========================================================================


class TestAutoResolveConflict:
    """Tests for MultiDomainSwarmEngine._auto_resolve_conflict."""

    async def test_resolves_with_method_auto_resolved(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        conflict = CrossDomainConflict(
            domain_ids=["d1", "d2"],
            agent_ids=["a1", "a2"],
        )
        config = MultiDomainSwarmConfig(domain_ids=["d1", "d2"], task="Test")
        result = await swarm_engine._auto_resolve_conflict(conflict, config)
        assert result.method == "auto_resolved"

    async def test_gives_priority_to_first_domain_id(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        conflict = CrossDomainConflict(
            domain_ids=["first-domain", "second-domain"],
            agent_ids=["a1", "a2"],
        )
        config = MultiDomainSwarmConfig(
            domain_ids=["first-domain", "second-domain"], task="Test"
        )
        result = await swarm_engine._auto_resolve_conflict(conflict, config)
        assert "first-domain" in result.resolution

    async def test_sets_conflict_status_to_resolved(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        conflict = CrossDomainConflict(
            domain_ids=["d1", "d2"],
            agent_ids=["a1", "a2"],
        )
        config = MultiDomainSwarmConfig(domain_ids=["d1", "d2"], task="Test")
        await swarm_engine._auto_resolve_conflict(conflict, config)
        assert conflict.status == ConflictStatus.RESOLVED

    async def test_logs_auto_resolved_to_tape(
        self, swarm_engine: MultiDomainSwarmEngine, tape_service: TapeService
    ) -> None:
        conflict = CrossDomainConflict(
            domain_ids=["d1", "d2"],
            agent_ids=["a1", "a2"],
        )
        config = MultiDomainSwarmConfig(domain_ids=["d1", "d2"], task="Test")
        await swarm_engine._auto_resolve_conflict(conflict, config)
        events = await tape_service.get_entries(
            event_type="canvas.multi_domain_swarm.conflict_auto_resolved"
        )
        assert len(events) >= 1


# ===========================================================================
# Group E: MultiDomainSwarmEngine.run() full pipeline
# ===========================================================================


class TestMultiDomainSwarmEngineRun:
    """Tests for MultiDomainSwarmEngine.run() full pipeline."""

    async def test_quick_mode_returns_quick_result(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2"],
            task="Quick task",
            governed=False,
            agent_ids=["a1", "a2"],
        )
        result = await swarm_engine.run(config)
        assert isinstance(result, MultiDomainSwarmResult)
        assert result.mode == "quick"

    async def test_governed_mode_returns_governed_result(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2"],
            task="Governed task",
            governed=True,
            agent_ids=["a1", "a2"],
        )
        result = await swarm_engine.run(config)
        assert result.mode == "governed"

    async def test_result_contains_correct_domain_ids(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["legal", "finance"],
            task="Test",
            agent_ids=["a1"],
        )
        result = await swarm_engine.run(config)
        assert result.domain_ids == ["legal", "finance"]

    async def test_result_contains_domain_groups(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2"],
            task="Test",
            agent_ids=["a1"],
        )
        result = await swarm_engine.run(config)
        assert len(result.domain_groups) == 2

    async def test_result_has_folder_path_populated(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1"],
            task="Test",
            agent_ids=["a1"],
        )
        result = await swarm_engine.run(config)
        assert result.folder_path != ""

    async def test_result_has_aethergit_branch(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1"],
            task="Test",
            agent_ids=["a1"],
        )
        result = await swarm_engine.run(config)
        assert result.aethergit_branch.startswith("swarm/")

    async def test_progress_tracking_after_run(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2"],
            task="Test",
            agent_ids=["a1", "a2"],
        )
        result = await swarm_engine.run(config)
        progress = swarm_engine.get_progress(result.swarm_id)
        assert progress is not None
        assert isinstance(progress, MultiDomainSwarmProgress)
        assert progress.status == "completed"

    async def test_progress_none_for_unknown_swarm_id(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        progress = swarm_engine.get_progress("nonexistent-id")
        assert progress is None

    async def test_list_runs_returns_completed_run(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1"],
            task="Test",
            agent_ids=["a1"],
        )
        await swarm_engine.run(config)
        runs = swarm_engine.list_runs()
        assert len(runs) >= 1

    async def test_result_duration_ms_positive(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        config = MultiDomainSwarmConfig(
            domain_ids=["d1"],
            task="Test",
            agent_ids=["a1"],
        )
        result = await swarm_engine.run(config)
        assert result.duration_ms > 0


# ===========================================================================
# Group F: SwarmIntegration.run_multi_domain_swarm
# ===========================================================================


class TestSwarmIntegrationMultiDomain:
    """Tests for SwarmIntegration.run_multi_domain_swarm."""

    async def test_returns_multi_domain_swarm_result(
        self, swarm_integration: SwarmIntegration
    ) -> None:
        result = await swarm_integration.run_multi_domain_swarm(
            domain_ids=["d1", "d2"],
            task="Test task",
            agent_ids=["a1", "a2"],
        )
        assert isinstance(result, MultiDomainSwarmResult)

    async def test_governed_false_returns_quick_mode(
        self, swarm_integration: SwarmIntegration
    ) -> None:
        result = await swarm_integration.run_multi_domain_swarm(
            domain_ids=["d1", "d2"],
            task="Test",
            governed=False,
        )
        assert result.mode == "quick"

    async def test_governed_true_returns_governed_mode(
        self, swarm_integration: SwarmIntegration
    ) -> None:
        result = await swarm_integration.run_multi_domain_swarm(
            domain_ids=["d1", "d2"],
            task="Test",
            governed=True,
        )
        assert result.mode == "governed"

    async def test_passes_domain_ids_and_task_through(
        self, swarm_integration: SwarmIntegration
    ) -> None:
        result = await swarm_integration.run_multi_domain_swarm(
            domain_ids=["legal", "finance", "engineering"],
            task="Cross-domain analysis",
        )
        assert result.domain_ids == ["legal", "finance", "engineering"]
        assert result.task == "Cross-domain analysis"


# ===========================================================================
# Group G: CanvasV5Engine.run_multi_domain_swarm
# ===========================================================================


class TestCanvasV5EngineMultiDomain:
    """Tests for CanvasV5Engine.run_multi_domain_swarm."""

    async def test_returns_multi_domain_swarm_result(
        self, canvas_v5_engine: CanvasV5Engine
    ) -> None:
        result = await canvas_v5_engine.run_multi_domain_swarm(
            domain_ids=["d1", "d2"],
            task="Test",
        )
        assert isinstance(result, MultiDomainSwarmResult)

    async def test_delegates_to_swarm_integration(
        self, canvas_v5_engine: CanvasV5Engine
    ) -> None:
        result = await canvas_v5_engine.run_multi_domain_swarm(
            domain_ids=["d1", "d2"],
            task="Delegation test",
            agent_ids=["a1"],
        )
        # If delegation works, we get a proper result with domain_ids
        assert result.domain_ids == ["d1", "d2"]
        assert result.task == "Delegation test"

    async def test_governed_flag_works(
        self, canvas_v5_engine: CanvasV5Engine
    ) -> None:
        result = await canvas_v5_engine.run_multi_domain_swarm(
            domain_ids=["d1"],
            task="Test governed",
            governed=True,
        )
        assert result.mode == "governed"

    async def test_agent_ids_optional_param_passed_through(
        self, canvas_v5_engine: CanvasV5Engine
    ) -> None:
        result = await canvas_v5_engine.run_multi_domain_swarm(
            domain_ids=["d1", "d2"],
            task="Test with agents",
            agent_ids=["agent-x", "agent-y"],
        )
        # agent_ids are passed through to config, which populates participants
        assert "agent-x" in result.participants or result.participants == ["agent-x", "agent-y"]


# ===========================================================================
# Group H: Edge Cases
# ===========================================================================


class TestEdgeCases:
    """Tests for edge cases in multi-domain swarm."""

    async def test_single_domain_no_conflicts(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        """Single domain: no conflicts detected (only 1 group, no pairs)."""
        config = MultiDomainSwarmConfig(
            domain_ids=["solo"],
            task="Solo task",
            agent_ids=["a1"],
        )
        result = await swarm_engine.run(config)
        assert len(result.conflicts) == 0

    async def test_three_domains_three_conflicts(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        """Three domains: 3 conflicts detected (3 pairs)."""
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2", "d3"],
            task="Three-way task",
            agent_ids=["a1", "a2", "a3"],
        )
        result = await swarm_engine.run(config)
        # 3 * 2 / 2 = 3 conflicts
        assert len(result.conflicts) == 3

    async def test_empty_agent_ids_no_conflicts(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        """Empty agent_ids: no conflicts despite multiple domains."""
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2", "d3"],
            task="No agents task",
            agent_ids=None,
        )
        result = await swarm_engine.run(config)
        # agent_ids=None → groups get [] → no conflicts
        assert len(result.conflicts) == 0

    async def test_max_conflicts_limits_resolutions(
        self, swarm_engine: MultiDomainSwarmEngine
    ) -> None:
        """config.max_conflicts limits number of resolutions."""
        config = MultiDomainSwarmConfig(
            domain_ids=["d1", "d2", "d3", "d4"],
            task="Limited conflicts",
            agent_ids=["a1", "a2", "a3", "a4"],
            max_conflicts=2,
        )
        result = await swarm_engine.run(config)
        # 4 domains → 6 conflicts, but only 2 resolutions due to max_conflicts
        assert len(result.conflicts) == 6
        assert len(result.conflict_resolutions) == 2
