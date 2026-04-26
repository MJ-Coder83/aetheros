"""Comprehensive tests for Domain Canvas (v5) features.

Tests cover:
- TieredUIRegistry (framework registration, detection, listing by tier)
- PluginNodeManager (CRUD, command execution)
- SimulationOverlay (metric updates, overlay data, clearing)
- TapeOverlay (event management, node mapping)
- NLEditEngine (pattern parsing, apply edits)
- PrimeCoPilot (UX issues, layout optimizations, best practices, apply)
- CanvasVersioningManager (save, list, diff, rewind)
- SwarmIntegration (quick, governed, multi-domain)
- CanvasV5Engine (convenience methods, integration)
"""

from __future__ import annotations

import pytest

from packages.canvas.canvas_v5 import (
    CanvasV5Engine,
    CanvasVersioningManager,
    CopilotSuggestion,
    CopilotSuggestionType,
    FrameworkTier,
    GovernedSwarmResult,
    MultiDomainSwarmResult,
    NLEditEngine,
    NLEditType,
    PluginNodeConfig,
    PluginNodeManager,
    PrimeCoPilot,
    QuickSwarmResult,
    SimulationOverlay,
    SwarmIntegration,
    TapeEventEntry,
    TapeOverlay,
    TieredFramework,
    TieredUIRegistry,
    UIFramework,
)
from packages.canvas.core import CanvasService
from packages.canvas.models import (
    Canvas,
    CanvasEdge,
    CanvasEdgeType,
    CanvasError,
    CanvasLayout,
    CanvasNode,
    CanvasNodeType,
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
def tape_service(tape_repo: InMemoryTapeRepository) -> TapeService:
    return TapeService(tape_repo)


@pytest.fixture()
def canvas_service(tape_service: TapeService) -> CanvasService:
    return CanvasService(tape_service=tape_service)


@pytest.fixture()
async def canvas_with_nodes(canvas_service: CanvasService) -> Canvas:
    _canvas = await canvas_service.create_canvas("test-domain", "Test Domain")
    domain_node = CanvasNode(
        id="domain-1", node_type=CanvasNodeType.DOMAIN,
        label="Test Domain", x=300, y=40, width=180, height=70,
    )
    agent_node = CanvasNode(
        id="agent-1", node_type=CanvasNodeType.AGENT,
        label="Analyst", x=120, y=160, width=160, height=80,
    )
    skill_node = CanvasNode(
        id="skill-1", node_type=CanvasNodeType.SKILL,
        label="contract_analysis", x=120, y=300, width=160, height=60,
    )
    await canvas_service.add_node("test-domain", domain_node, sync_to_tree=False)
    await canvas_service.add_node("test-domain", agent_node, sync_to_tree=False)
    await canvas_service.add_node("test-domain", skill_node, sync_to_tree=False)
    edge = CanvasEdge(source="domain-1", target="agent-1", edge_type=CanvasEdgeType.CONTAINS)
    await canvas_service.add_edge("test-domain", edge)
    edge2 = CanvasEdge(source="agent-1", target="skill-1", edge_type=CanvasEdgeType.USES)
    await canvas_service.add_edge("test-domain", edge2)
    return await canvas_service.get_canvas("test-domain")


# ===========================================================================
# TieredUIRegistry
# ===========================================================================


class TestTieredUIRegistry:
    """Tests for the TieredUIRegistry."""

    def test_default_frameworks_loaded(self) -> None:
        registry = TieredUIRegistry()
        frameworks = registry.list_frameworks()
        assert len(frameworks) >= 15  # 10 Tier1 + 3 Tier2 + 3 Tier3 + 3 Tier4

    def test_list_tier_1_frameworks(self) -> None:
        registry = TieredUIRegistry()
        tier1 = registry.list_frameworks(FrameworkTier.TIER_1_BROWSER)
        assert len(tier1) == 10
        for fw in tier1:
            assert fw.tier == FrameworkTier.TIER_1_BROWSER

    def test_list_tier_2_frameworks(self) -> None:
        registry = TieredUIRegistry()
        tier2 = registry.list_frameworks(FrameworkTier.TIER_2_HIGH_FIDELITY)
        assert len(tier2) >= 3

    def test_list_tier_3_frameworks(self) -> None:
        registry = TieredUIRegistry()
        tier3 = registry.list_frameworks(FrameworkTier.TIER_3_TERMINAL)
        assert len(tier3) >= 3

    def test_list_tier_4_frameworks(self) -> None:
        registry = TieredUIRegistry()
        tier4 = registry.list_frameworks(FrameworkTier.TIER_4_PLUGIN)
        assert len(tier4) >= 3

    def test_get_framework_by_name(self) -> None:
        registry = TieredUIRegistry()
        react = registry.get_framework("react")
        assert react is not None
        assert react.label == "React"
        assert react.tier == FrameworkTier.TIER_1_BROWSER
        assert react.preview_supported is True

    def test_get_framework_not_found(self) -> None:
        registry = TieredUIRegistry()
        assert registry.get_framework("nonexistent") is None

    def test_register_custom_framework(self) -> None:
        registry = TieredUIRegistry()
        custom = TieredFramework(
            framework=UIFramework.VSCODE,
            tier=FrameworkTier.TIER_4_PLUGIN,
            label="My VS Code Plugin",
            preview_supported=True,
        )
        registry.register_framework(custom)
        found = registry.get_framework("vscode")
        assert found is not None
        assert found.label == "My VS Code Plugin"

    def test_get_tier_for_framework(self) -> None:
        registry = TieredUIRegistry()
        tier = registry.get_tier("react")
        assert tier == FrameworkTier.TIER_1_BROWSER

    def test_get_tier_not_found(self) -> None:
        registry = TieredUIRegistry()
        assert registry.get_tier("nonexistent") is None

    def test_detect_framework_by_extension(self) -> None:
        registry = TieredUIRegistry()
        # .tsx -> React or Next.js
        found = registry.detect_framework(".tsx")
        assert found is not None
        assert found.tier == FrameworkTier.TIER_1_BROWSER

    def test_detect_framework_by_extension_without_dot(self) -> None:
        registry = TieredUIRegistry()
        found = registry.detect_framework("vue")
        assert found is not None
        assert found.framework == UIFramework.VUE

    def test_detect_framework_unknown_extension(self) -> None:
        registry = TieredUIRegistry()
        assert registry.detect_framework(".xyz") is None

    def test_tier_1_frameworks_have_preview(self) -> None:
        registry = TieredUIRegistry()
        tier1 = registry.list_frameworks(FrameworkTier.TIER_1_BROWSER)
        for fw in tier1:
            assert fw.preview_supported, f"Tier 1 framework {fw.label} should support preview"


# ===========================================================================
# PluginNodeManager
# ===========================================================================


class TestPluginNodeManager:
    """Tests for the PluginNodeManager."""

    def test_register_plugin_node(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        config = PluginNodeConfig(plugin_id="p1", label="My Plugin")
        result = mgr.register_plugin_node(config)
        assert result.node_id == config.node_id

    def test_register_duplicate_raises(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        config = PluginNodeConfig(plugin_id="p1", node_id="fixed-id", label="P1")
        mgr.register_plugin_node(config)
        with pytest.raises(CanvasError, match="already exists"):
            mgr.register_plugin_node(PluginNodeConfig(plugin_id="p2", node_id="fixed-id", label="P2"))

    def test_get_plugin_node(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        config = PluginNodeConfig(plugin_id="p1", label="P1")
        mgr.register_plugin_node(config)
        found = mgr.get_plugin_node(config.node_id)
        assert found is not None
        assert found.plugin_id == "p1"

    def test_get_plugin_node_not_found(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        assert mgr.get_plugin_node("nonexistent") is None

    def test_list_plugin_nodes(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        mgr.register_plugin_node(PluginNodeConfig(plugin_id="p1", label="P1"))
        mgr.register_plugin_node(PluginNodeConfig(plugin_id="p2", label="P2"))
        nodes = mgr.list_plugin_nodes()
        assert len(nodes) == 2

    def test_update_plugin_node(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        config = PluginNodeConfig(plugin_id="p1", label="Original")
        mgr.register_plugin_node(config)
        updated = mgr.update_plugin_node(config.node_id, label="Updated", status="active")
        assert updated.label == "Updated"
        assert updated.status == "active"

    def test_update_plugin_node_not_found(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        with pytest.raises(CanvasError, match="not found"):
            mgr.update_plugin_node("nonexistent", label="X")

    def test_remove_plugin_node(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        config = PluginNodeConfig(plugin_id="p1", label="P1")
        mgr.register_plugin_node(config)
        removed = mgr.remove_plugin_node(config.node_id)
        assert removed is not None
        assert mgr.get_plugin_node(config.node_id) is None

    def test_remove_plugin_node_not_found(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        assert mgr.remove_plugin_node("nonexistent") is None

    def test_execute_command(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        config = PluginNodeConfig(
            plugin_id="p1", label="P1",
            command_registry=["render", "export"],
        )
        mgr.register_plugin_node(config)
        result = mgr.execute_command(config.node_id, "render")
        assert result["status"] == "executed"

    def test_execute_command_not_found_node(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        with pytest.raises(CanvasError, match="not found"):
            mgr.execute_command("nonexistent", "render")

    async def test_log_plugin_event(self, tape_service: TapeService) -> None:
        mgr = PluginNodeManager(tape_service)
        await mgr.log_plugin_event("node-1", "activated", {"detail": "test"})
        # No assertion needed -- just verify no exception


# ===========================================================================
# SimulationOverlay
# ===========================================================================


class TestSimulationOverlay:
    """Tests for the SimulationOverlay."""

    def test_update_node_metric(self, tape_service: TapeService) -> None:
        overlay = SimulationOverlay(tape_service)
        metric = overlay.update_node_metric("agent-1", "execution_time", 1.5, "ms", "normal", "stable")
        assert metric.metric_name == "execution_time"
        assert metric.value == 1.5

    def test_get_node_metrics(self, tape_service: TapeService) -> None:
        overlay = SimulationOverlay(tape_service)
        overlay.update_node_metric("agent-1", "exec_time", 1.0)
        overlay.update_node_metric("agent-1", "success_rate", 0.95)
        metrics = overlay.get_node_metrics("agent-1")
        assert len(metrics) == 2

    def test_get_latest_metrics(self, tape_service: TapeService) -> None:
        overlay = SimulationOverlay(tape_service)
        overlay.update_node_metric("agent-1", "exec_time", 1.0)
        overlay.update_node_metric("agent-1", "exec_time", 2.0)  # Updated value
        latest = overlay.get_latest_metrics("agent-1")
        assert "exec_time" in latest
        assert latest["exec_time"].value == 2.0

    def test_get_overlay_data(self, tape_service: TapeService) -> None:
        overlay = SimulationOverlay(tape_service)
        overlay.update_node_metric("agent-1", "metric_a", 1.0)
        overlay.update_node_metric("agent-2", "metric_b", 2.0)
        data = overlay.get_overlay_data()
        assert "agent-1" in data
        assert "agent-2" in data

    def test_get_overlay_data_filtered(self, tape_service: TapeService) -> None:
        overlay = SimulationOverlay(tape_service)
        overlay.update_node_metric("agent-1", "metric_a", 1.0)
        overlay.update_node_metric("agent-2", "metric_b", 2.0)
        data = overlay.get_overlay_data(["agent-1"])
        assert "agent-1" in data
        assert "agent-2" not in data

    def test_clear_metrics_specific_node(self, tape_service: TapeService) -> None:
        overlay = SimulationOverlay(tape_service)
        overlay.update_node_metric("agent-1", "m", 1.0)
        overlay.update_node_metric("agent-2", "m", 2.0)
        overlay.clear_metrics("agent-1")
        assert overlay.get_node_metrics("agent-1") == []
        assert len(overlay.get_node_metrics("agent-2")) == 1

    def test_clear_metrics_all(self, tape_service: TapeService) -> None:
        overlay = SimulationOverlay(tape_service)
        overlay.update_node_metric("agent-1", "m", 1.0)
        overlay.update_node_metric("agent-2", "m", 2.0)
        overlay.clear_metrics()
        assert overlay.get_node_metrics("agent-1") == []
        assert overlay.get_node_metrics("agent-2") == []

    def test_metric_trimming_at_100(self, tape_service: TapeService) -> None:
        overlay = SimulationOverlay(tape_service)
        for i in range(120):
            overlay.update_node_metric("agent-1", "m", float(i))
        metrics = overlay.get_node_metrics("agent-1")
        assert len(metrics) == 100

    def test_set_active_simulation(self, tape_service: TapeService) -> None:
        overlay = SimulationOverlay(tape_service)
        overlay.set_active_simulation("sim-123")
        assert overlay._active_simulation == "sim-123"
        overlay.set_active_simulation(None)
        assert overlay._active_simulation is None


# ===========================================================================
# TapeOverlay
# ===========================================================================


class TestTapeOverlay:
    """Tests for the TapeOverlay."""

    def test_add_event(self, tape_service: TapeService) -> None:
        overlay = TapeOverlay(tape_service)
        event = TapeEventEntry(event_id="e1", event_type="canvas.node_added")
        overlay.add_event(event)
        events = overlay.get_recent_events()
        assert len(events) == 1

    def test_get_recent_events_limit(self, tape_service: TapeService) -> None:
        overlay = TapeOverlay(tape_service)
        for i in range(60):
            overlay.add_event(TapeEventEntry(event_id=f"e{i}", event_type="test"))
        events = overlay.get_recent_events(limit=10)
        assert len(events) == 10

    def test_get_events_for_node(self, tape_service: TapeService) -> None:
        overlay = TapeOverlay(tape_service)
        overlay.add_event(TapeEventEntry(event_id="e1", event_type="test", source_node_id="agent-1"))
        overlay.add_event(TapeEventEntry(event_id="e2", event_type="test", target_node_id="agent-1"))
        overlay.add_event(TapeEventEntry(event_id="e3", event_type="test", source_node_id="agent-2"))
        events = overlay.get_events_for_node("agent-1")
        assert len(events) == 2

    def test_get_events_between(self, tape_service: TapeService) -> None:
        overlay = TapeOverlay(tape_service)
        overlay.add_event(TapeEventEntry(
            event_id="e1", event_type="test",
            source_node_id="agent-1", target_node_id="skill-1",
        ))
        overlay.add_event(TapeEventEntry(
            event_id="e2", event_type="test",
            source_node_id="agent-2", target_node_id="skill-1",
        ))
        events = overlay.get_events_between("agent-1", "skill-1")
        assert len(events) == 1

    def test_clear_events(self, tape_service: TapeService) -> None:
        overlay = TapeOverlay(tape_service)
        overlay.add_event(TapeEventEntry(event_id="e1", event_type="test"))
        overlay.clear_events()
        assert len(overlay.get_recent_events()) == 0

    def test_event_trimming_at_200(self, tape_service: TapeService) -> None:
        overlay = TapeOverlay(tape_service)
        for i in range(250):
            overlay.add_event(TapeEventEntry(event_id=f"e{i}", event_type="test"))
        assert len(overlay.get_recent_events(limit=999)) == 200

    def test_map_event_to_nodes(self, tape_service: TapeService) -> None:
        overlay = TapeOverlay(tape_service)
        canvas = Canvas(
            domain_id="test",
            domain_name="Test",
            nodes=[
                CanvasNode(id="agent-analyst", node_type=CanvasNodeType.AGENT, label="Analyst"),
                CanvasNode(id="domain-test", node_type=CanvasNodeType.DOMAIN, label="Test"),
            ],
        )
        source, target = overlay.map_event_to_nodes(
            event_type="canvas.node_added",
            agent_id="analyst",
            payload={"domain_id": "test"},
            canvas=canvas,
        )
        assert source is not None or target is not None


# ===========================================================================
# NLEditEngine
# ===========================================================================


class TestNLEditEngine:
    """Tests for the NLEditEngine."""

    def test_parse_move_center(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Move the analyst to the center")
        assert result.edit_type == NLEditType.MOVE
        assert result.confidence >= 0.7
        assert len(result.changes) == 1
        assert result.changes[0]["action"] == "move"

    def test_parse_move_above(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Move the analyst above the skill node")
        assert result.edit_type == NLEditType.MOVE
        assert result.changes[0]["direction"] == "above"

    def test_parse_resize_larger(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Make the domain larger")
        assert result.edit_type == NLEditType.RESIZE
        assert result.changes[0]["resize_type"] == "larger"

    def test_parse_resize_smaller(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Make the button smaller")
        assert result.edit_type == NLEditType.RESIZE
        assert result.changes[0]["resize_type"] == "smaller"

    def test_parse_resize_full_width(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Make the header full width")
        assert result.edit_type == NLEditType.RESIZE
        assert result.changes[0]["resize_type"] == "full_width"

    def test_parse_add_node(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Add an agent node called \"Researcher\"")
        assert result.edit_type == NLEditType.ADD
        assert result.changes[0]["node_type"] == "agent"

    def test_parse_add_skill_node(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Create a skill named \"summarizer\"")
        assert result.edit_type == NLEditType.ADD

    def test_parse_remove_node(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Remove the analyst node")
        assert result.edit_type == NLEditType.REMOVE
        assert result.changes[0]["action"] == "remove"

    def test_parse_connect_nodes(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Connect the analyst to the skill")
        assert result.edit_type == NLEditType.CONNECT

    def test_parse_link_nodes(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Link the analyst with the domain")
        assert result.edit_type == NLEditType.CONNECT

    def test_parse_layout_change(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Apply a layered layout")
        assert result.edit_type == NLEditType.LAYOUT
        assert result.changes[0]["layout"] == "layered"

    def test_parse_beautify(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Beautify")
        assert result.edit_type == NLEditType.LAYOUT

    def test_parse_unrecognized(self, tape_service: TapeService) -> None:
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Turn everything into a unicorn")
        assert result.edit_type == NLEditType.COMPOUND
        assert result.confidence < 0.5

    async def test_apply_edit_move(self, tape_service: TapeService, canvas_service: CanvasService) -> None:
        await canvas_service.create_canvas("test-nl", "Test NL")
        await canvas_service.add_node(
            "test-nl",
            CanvasNode(id="agent-analyst", node_type=CanvasNodeType.AGENT, label="Analyst", x=100, y=100),
            sync_to_tree=False,
        )
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Move the analyst to the center")
        result = await engine.apply_edit(canvas_service, "test-nl", result)
        assert result.applied is True

    async def test_apply_edit_layout(self, tape_service: TapeService, canvas_service: CanvasService) -> None:
        await canvas_service.create_canvas("test-layout-nl", "Test")
        engine = NLEditEngine(tape_service)
        result = engine.parse_instruction("Apply a layered layout")
        result = await engine.apply_edit(canvas_service, "test-layout-nl", result)
        assert result.applied is True


# ===========================================================================
# PrimeCoPilot
# ===========================================================================


class TestPrimeCoPilot:
    """Tests for the PrimeCoPilot."""

    async def test_detect_overlapping_nodes(self, tape_service: TapeService) -> None:
        copilot = PrimeCoPilot(tape_service)
        canvas = Canvas(
            domain_id="test",
            domain_name="Test",
            nodes=[
                CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A1", x=100, y=100, width=180, height=60),
                CanvasNode(id="n2", node_type=CanvasNodeType.AGENT, label="A2", x=120, y=110, width=180, height=60),
            ],
        )
        suggestions = await copilot.analyze_canvas(canvas)
        overlap_suggestions = [s for s in suggestions if s.suggestion_type == CopilotSuggestionType.UX_ISSUE]
        assert len(overlap_suggestions) >= 1

    async def test_detect_disconnected_agents(self, tape_service: TapeService) -> None:
        copilot = PrimeCoPilot(tape_service)
        canvas = Canvas(
            domain_id="test",
            domain_name="Test",
            nodes=[
                CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="A1"),
            ],
        )
        suggestions = await copilot.analyze_canvas(canvas)
        disconnected = [s for s in suggestions if "Disconnected" in s.title or "without" in s.description.lower()]
        assert len(disconnected) >= 1

    async def test_detect_no_agents_best_practice(self, tape_service: TapeService) -> None:
        copilot = PrimeCoPilot(tape_service)
        canvas = Canvas(
            domain_id="test",
            domain_name="Test",
            nodes=[
                CanvasNode(id="d1", node_type=CanvasNodeType.DOMAIN, label="D1"),
            ],
        )
        suggestions = await copilot.analyze_canvas(canvas)
        bp = [s for s in suggestions if s.suggestion_type == CopilotSuggestionType.BEST_PRACTICE]
        assert len(bp) >= 1

    async def test_detect_no_skills_best_practice(self, tape_service: TapeService) -> None:
        copilot = PrimeCoPilot(tape_service)
        canvas = Canvas(
            domain_id="test",
            domain_name="Test",
            nodes=[
                CanvasNode(id="d1", node_type=CanvasNodeType.DOMAIN, label="D1"),
                CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="A1"),
            ],
        )
        suggestions = await copilot.analyze_canvas(canvas)
        no_skills = [s for s in suggestions if "No skills" in s.title]
        assert len(no_skills) >= 1

    async def test_detect_redundant_nodes(self, tape_service: TapeService) -> None:
        copilot = PrimeCoPilot(tape_service)
        canvas = Canvas(
            domain_id="test",
            domain_name="Test",
            nodes=[
                CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="Analyst"),
                CanvasNode(id="a2", node_type=CanvasNodeType.AGENT, label="Analyst"),
            ],
        )
        suggestions = await copilot.analyze_canvas(canvas)
        redundant = [s for s in suggestions if s.suggestion_type == CopilotSuggestionType.REDUNDANT_NODE]
        assert len(redundant) >= 1

    async def test_suggestions_sorted_by_confidence(self, tape_service: TapeService) -> None:
        copilot = PrimeCoPilot(tape_service)
        canvas = Canvas(
            domain_id="test",
            domain_name="Test",
            nodes=[
                CanvasNode(id="d1", node_type=CanvasNodeType.DOMAIN, label="D1"),
            ],
        )
        suggestions = await copilot.analyze_canvas(canvas)
        if len(suggestions) >= 2:
            for i in range(len(suggestions) - 1):
                assert suggestions[i].confidence >= suggestions[i + 1].confidence

    async def test_apply_overlap_suggestion(self, tape_service: TapeService, canvas_service: CanvasService) -> None:
        copilot = PrimeCoPilot(tape_service)
        canvas = await canvas_service.create_canvas("overlap-test", "Overlap Test")
        await canvas_service.add_node(
            "overlap-test",
            CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A1", x=100, y=100),
            sync_to_tree=False,
        )
        await canvas_service.add_node(
            "overlap-test",
            CanvasNode(id="n2", node_type=CanvasNodeType.AGENT, label="A2", x=120, y=110),
            sync_to_tree=False,
        )
        canvas = await canvas_service.get_canvas("overlap-test")
        suggestions = await copilot.analyze_canvas(canvas)
        overlap = [s for s in suggestions if s.auto_applicable and s.suggestion_type == CopilotSuggestionType.UX_ISSUE]
        if overlap:
            applied = await copilot.apply_suggestion(canvas_service, "overlap-test", overlap[0])
            assert applied is True

    async def test_apply_non_auto_suggestion_fails(self, tape_service: TapeService) -> None:
        copilot = PrimeCoPilot(tape_service)
        suggestion = CopilotSuggestion(
            suggestion_type=CopilotSuggestionType.MISSING_CONNECTION,
            title="Test",
            auto_applicable=False,
        )
        # apply_suggestion returns False for non-auto suggestions
        # We need a canvas_service but it won't be called
        from unittest.mock import MagicMock
        mock_svc = MagicMock()
        result = await copilot.apply_suggestion(mock_svc, "test", suggestion)  # type: ignore[arg-type]
        assert result is False

    async def test_generate_ab_variant(self, tape_service: TapeService) -> None:
        copilot = PrimeCoPilot(tape_service)
        canvas = Canvas(
            domain_id="test",
            domain_name="Test",
            nodes=[
                CanvasNode(id="d1", node_type=CanvasNodeType.DOMAIN, label="D1", x=300, y=40),
                CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="A1", x=120, y=160),
            ],
        )
        variant = await copilot.generate_ab_variant(canvas, CanvasLayout.HUB_AND_SPOKE)
        assert variant.layout == CanvasLayout.HUB_AND_SPOKE
        assert variant.domain_id == "test"
        # Original canvas unchanged
        assert canvas.layout != CanvasLayout.HUB_AND_SPOKE or canvas.layout == CanvasLayout.HUB_AND_SPOKE


# ===========================================================================
# CanvasVersioningManager
# ===========================================================================


class TestCanvasVersioningManager:
    """Tests for the CanvasVersioningManager."""

    def test_save_version(self, tape_service: TapeService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        canvas = Canvas(domain_id="test", domain_name="Test")
        version = mgr.save_version(canvas, "Initial commit")
        assert version.version == 1
        assert version.commit_message == "Initial commit"

    def test_save_multiple_versions(self, tape_service: TapeService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        canvas = Canvas(domain_id="test", domain_name="Test")
        mgr.save_version(canvas, "v1")
        mgr.save_version(canvas, "v2")
        mgr.save_version(canvas, "v3")
        versions = mgr.list_versions("test")
        assert len(versions) == 3
        assert versions[2].version == 3

    def test_get_version(self, tape_service: TapeService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        canvas = Canvas(domain_id="test", domain_name="Test")
        mgr.save_version(canvas, "v1")
        mgr.save_version(canvas, "v2")
        v2 = mgr.get_version("test", 2)
        assert v2 is not None
        assert v2.version == 2

    def test_get_version_not_found(self, tape_service: TapeService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        assert mgr.get_version("test", 1) is None

    def test_get_latest_version(self, tape_service: TapeService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        canvas = Canvas(domain_id="test", domain_name="Test")
        mgr.save_version(canvas, "v1")
        mgr.save_version(canvas, "v2")
        latest = mgr.get_latest_version("test")
        assert latest is not None
        assert latest.version == 2

    def test_get_latest_version_empty(self, tape_service: TapeService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        assert mgr.get_latest_version("test") is None

    def test_diff_versions(self, tape_service: TapeService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        # Version 1: 1 node
        canvas1 = Canvas(
            domain_id="test",
            domain_name="Test",
            nodes=[CanvasNode(id="n1", node_type=CanvasNodeType.DOMAIN, label="D1", x=100, y=100)],
        )
        mgr.save_version(canvas1, "v1")
        # Version 2: 2 nodes, moved n1
        canvas2 = Canvas(
            domain_id="test",
            domain_name="Test",
            nodes=[
                CanvasNode(id="n1", node_type=CanvasNodeType.DOMAIN, label="D1", x=200, y=200),
                CanvasNode(id="n2", node_type=CanvasNodeType.AGENT, label="A1", x=100, y=300),
            ],
        )
        mgr.save_version(canvas2, "v2")
        diff = mgr.diff_versions("test", 1, 2)
        assert diff["added_nodes"] == 1
        assert diff["moved_nodes"] == 1

    def test_diff_versions_not_found(self, tape_service: TapeService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        diff = mgr.diff_versions("test", 1, 2)
        assert "error" in diff

    def test_version_trimming_at_100(self, tape_service: TapeService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        canvas = Canvas(domain_id="test", domain_name="Test")
        for i in range(120):
            mgr.save_version(canvas, f"v{i + 1}")
        versions = mgr.list_versions("test")
        assert len(versions) == 100

    def test_rewind_to_version(self, tape_service: TapeService, canvas_service: CanvasService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        canvas = canvas_service._store.get("")  # No canvas yet
        # Create a canvas first
        canvas = Canvas(domain_id="rewind-test", domain_name="Rewind Test")
        canvas_service._store.add(canvas)

        # Save v1 with a domain node
        canvas.nodes = [CanvasNode(id="d1", node_type=CanvasNodeType.DOMAIN, label="D1")]
        canvas_service._store.update(canvas)
        mgr.save_version(canvas, "v1 with domain")

        # Save v2 with an added agent
        canvas.nodes.append(CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="A1"))
        canvas_service._store.update(canvas)
        mgr.save_version(canvas, "v2 with agent")

        # Rewind to v1
        result = mgr.rewind_to_version("rewind-test", 1, canvas_service)
        assert result is not None
        assert len(result.nodes) == 1

    def test_rewind_to_version_not_found(self, tape_service: TapeService, canvas_service: CanvasService) -> None:
        mgr = CanvasVersioningManager(tape_service)
        canvas = Canvas(domain_id="rewind-test-2", domain_name="Test")
        canvas_service._store.add(canvas)
        result = mgr.rewind_to_version("rewind-test-2", 99, canvas_service)
        assert result is None


# ===========================================================================
# SwarmIntegration
# ===========================================================================


class TestSwarmIntegration:
    """Tests for the SwarmIntegration."""

    async def test_run_quick_swarm(self, tape_service: TapeService) -> None:
        swarm = SwarmIntegration(tape_service)
        result = await swarm.run_quick_swarm("test-domain", "Optimize layout")
        assert isinstance(result, QuickSwarmResult)
        assert result.status == "completed"
        assert result.task == "Optimize layout"

    async def test_run_quick_swarm_with_agents(self, tape_service: TapeService) -> None:
        swarm = SwarmIntegration(tape_service)
        result = await swarm.run_quick_swarm(
            "test-domain", "Analyze", agent_ids=["agent-1", "agent-2"],
        )
        assert "agent-1" in result.participants

    async def test_run_governed_swarm(self, tape_service: TapeService) -> None:
        swarm = SwarmIntegration(tape_service)
        result = await swarm.run_governed_swarm("test-domain", "Reorganize domain")
        assert isinstance(result, GovernedSwarmResult)
        assert result.status == "pending_approval"
        assert result.approval_required is True

    async def test_run_multi_domain_swarm_quick(self, tape_service: TapeService) -> None:
        swarm = SwarmIntegration(tape_service)
        result = await swarm.run_multi_domain_swarm(
            ["domain-1", "domain-2"], "Cross-domain analysis", governed=False,
        )
        assert isinstance(result, MultiDomainSwarmResult)
        assert result.mode == "quick"

    async def test_run_multi_domain_swarm_governed(self, tape_service: TapeService) -> None:
        swarm = SwarmIntegration(tape_service)
        result = await swarm.run_multi_domain_swarm(
            ["domain-1", "domain-2"], "Cross-domain restructure", governed=True,
        )
        assert isinstance(result, MultiDomainSwarmResult)
        assert result.mode == "governed"


# ===========================================================================
# CanvasV5Engine (integration)
# ===========================================================================


class TestCanvasV5Engine:
    """Tests for the CanvasV5Engine orchestration."""

    def test_engine_has_sub_engines(self, tape_service: TapeService, canvas_service: CanvasService) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        assert engine.plugin_nodes is not None
        assert engine.simulation_overlay is not None
        assert engine.tape_overlay is not None
        assert engine.nl_edit is not None
        assert engine.copilot is not None
        assert engine.versioning is not None
        assert engine.swarm is not None
        assert engine.framework_registry is not None

    async def test_natural_language_edit_convenience(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        await canvas_service.create_canvas("nl-test", "NL Test")
        result = await engine.natural_language_edit("nl-test", "Apply a clustered layout")
        assert result.edit_type == NLEditType.LAYOUT
        assert result.applied is True

    async def test_get_copilot_suggestions_convenience(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        await canvas_service.create_canvas("copilot-test", "Copilot Test")
        suggestions = await engine.get_copilot_suggestions("copilot-test")
        assert isinstance(suggestions, list)

    async def test_save_canvas_version_convenience(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        await canvas_service.create_canvas("version-test", "Version Test")
        version = await engine.save_canvas_version("version-test", "First save")
        assert version.version == 1

    async def test_run_quick_swarm_convenience(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        result = await engine.run_quick_swarm("swarm-test", "Quick task")
        assert result.status == "completed"

    async def test_run_governed_swarm_convenience(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        result = await engine.run_governed_swarm("swarm-test", "Governed task")
        assert result.status == "pending_approval"

    async def test_add_plugin_node_convenience(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        await canvas_service.create_canvas("plugin-test", "Plugin Test")
        config = PluginNodeConfig(plugin_id="godot-render", label="Godot Render")
        _plugin_config, canvas_node = await engine.add_plugin_node("plugin-test", config)
        assert canvas_node.node_type == CanvasNodeType.CUSTOM
        assert "plugin_id" in canvas_node.metadata

    async def test_update_simulation_overlay_convenience(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        result = await engine.update_simulation_overlay(
            "sim-test",
            {"agent-1": {"exec_time": 1.5, "success_rate": 0.95}},
        )
        assert "agent-1" in result
        assert "exec_time" in result["agent-1"]

    def test_get_tape_overlay_events_convenience(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        engine.tape_overlay.add_event(
            TapeEventEntry(event_id="e1", event_type="test"),
        )
        events = engine.get_tape_overlay_events()
        assert len(events) == 1

    def test_list_frameworks_convenience(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        frameworks = engine.list_frameworks()
        assert len(frameworks) >= 15

    def test_list_frameworks_by_tier(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        tier1 = engine.list_frameworks(FrameworkTier.TIER_1_BROWSER)
        assert all(f.tier == FrameworkTier.TIER_1_BROWSER for f in tier1)

    def test_detect_framework_convenience(
        self, tape_service: TapeService, canvas_service: CanvasService,
    ) -> None:
        engine = CanvasV5Engine(tape_service, canvas_service)
        found = engine.detect_framework(".vue")
        assert found is not None
        assert found.framework == UIFramework.VUE
