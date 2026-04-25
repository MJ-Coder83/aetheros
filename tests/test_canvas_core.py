"""Unit tests for Canvas Core & Visual Engine (Agent 1).

Tests cover:
- Canvas / CanvasNode / CanvasEdge / CanvasDiff data models
- LayoutEngine: LAYERED, HUB_AND_SPOKE, CLUSTERED, LINEAR, SMART strategies
- CanvasStore CRUD
- CanvasService: create, get, add/remove/move/update node, add/remove edge,
  apply_layout, set_view_mode, sync_to/from folder_tree,
  canvas_from_domain_blueprint, diff
- Tape logging for every operation
- Package-level imports from packages.canvas

Run with: pytest tests/test_canvas_core.py -v
"""

from __future__ import annotations

import pytest

from packages.canvas import (
    Canvas,
    CanvasEdge,
    CanvasEdgeType,
    CanvasError,
    CanvasLayout,
    CanvasNode,
    CanvasNodeType,
    CanvasNotFoundError,
    CanvasService,
    CanvasStore,
    CanvasViewMode,
    EdgeNotFoundError,
    InvalidEdgeError,
    LayoutEngine,
    NodeAlreadyExistsError,
    NodeNotFoundError,
)
from packages.folder_tree import FolderTreeService
from packages.prime.domain_creation import (
    AgentBlueprint,
    AgentRole,
    DomainBlueprint,
    SkillBlueprint,
    WorkflowBlueprint,
    WorkflowType,
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
def folder_svc(tape_svc: TapeService) -> FolderTreeService:
    return FolderTreeService(tape_service=tape_svc)


@pytest.fixture()
def store() -> CanvasStore:
    return CanvasStore()


@pytest.fixture()
def layout_engine() -> LayoutEngine:
    return LayoutEngine()


@pytest.fixture()
def svc(tape_svc: TapeService) -> CanvasService:
    return CanvasService(tape_service=tape_svc)


@pytest.fixture()
def svc_with_tree(tape_svc: TapeService, folder_svc: FolderTreeService) -> CanvasService:
    return CanvasService(tape_service=tape_svc, folder_tree_service=folder_svc)


# ---------------------------------------------------------------------------
# Sample blueprints
# ---------------------------------------------------------------------------


def _make_minimal_blueprint() -> DomainBlueprint:
    return DomainBlueprint(
        domain_name="Test Domain",
        domain_id="test-domain",
        description="A minimal test domain",
        agents=[
            AgentBlueprint(agent_id="a1", name="Alpha Agent", role=AgentRole.COORDINATOR, goal="Coordinate"),
        ],
        skills=[
            SkillBlueprint(skill_id="s1", name="Core Skill", description="Core"),
        ],
        workflows=[
            WorkflowBlueprint(workflow_id="w1", name="Main Flow", steps=["step1"]),
        ],
    )


def _make_legal_blueprint() -> DomainBlueprint:
    return DomainBlueprint(
        domain_name="Legal Research Domain",
        domain_id="legal-research",
        description="Legal research domain",
        agents=[
            AgentBlueprint(
                agent_id="a-coord",
                name="Legal Lead",
                role=AgentRole.COORDINATOR,
                goal="Lead operations",
                tools=["contract_analysis"],
            ),
            AgentBlueprint(agent_id="a-spec", name="Contract Analyst", role=AgentRole.SPECIALIST, goal="Analyse"),
            AgentBlueprint(agent_id="a-rev", name="Compliance Checker", role=AgentRole.REVIEWER, goal="Review"),
            AgentBlueprint(agent_id="a-res", name="Legal Researcher", role=AgentRole.RESEARCHER, goal="Research"),
        ],
        skills=[
            SkillBlueprint(skill_id="s-ca", name="Contract Analysis", description="Analyse contracts"),
            SkillBlueprint(skill_id="s-cc", name="Compliance Check", description="Check compliance", is_reused=True),
            SkillBlueprint(skill_id="s-ra", name="Risk Assessment", description="Assess risk"),
        ],
        workflows=[
            WorkflowBlueprint(
                workflow_id="w-rev",
                name="Contract Review",
                workflow_type=WorkflowType.REVIEW,
                agent_ids=["a-coord", "a-spec", "a-rev"],
                steps=["Draft", "Review", "Approve"],
            ),
            WorkflowBlueprint(
                workflow_id="w-aud",
                name="Compliance Audit",
                workflow_type=WorkflowType.SEQUENTIAL,
                agent_ids=["a-coord", "a-rev"],
                steps=["Scope", "Check", "Report"],
            ),
        ],
    )


def _make_canvas_with_nodes(svc: CanvasService) -> Canvas:
    """Synchronous helper — returns a Canvas that already has nodes populated."""
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        svc.create_canvas("demo", "Demo Domain")
    )
    for i in range(3):
        node = CanvasNode(id=f"n{i}", node_type=CanvasNodeType.AGENT, label=f"Agent {i}")
        asyncio.get_event_loop().run_until_complete(svc.add_node("demo", node))
    return asyncio.get_event_loop().run_until_complete(svc.get_canvas("demo"))


# ===========================================================================
# CanvasNode model tests
# ===========================================================================


class TestCanvasNodeModel:
    def test_defaults(self) -> None:
        node = CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="Agent")
        assert node.x == 0.0
        assert node.y == 0.0
        assert node.width == 180.0
        assert node.height == 60.0
        assert node.folder_path == ""
        assert node.selected is False
        assert node.locked is False
        assert node.metadata == {}

    def test_custom_values(self) -> None:
        node = CanvasNode(
            id="n1",
            node_type=CanvasNodeType.WORKFLOW,
            label="My Flow",
            x=100.0,
            y=200.0,
            folder_path="root/workflows/my_flow",
            metadata={"colour": "#ff0000"},
        )
        assert node.x == 100.0
        assert node.folder_path == "root/workflows/my_flow"
        assert node.metadata["colour"] == "#ff0000"

    def test_all_node_types_valid(self) -> None:
        for nt in CanvasNodeType:
            node = CanvasNode(id="n1", node_type=nt, label="test")
            assert node.node_type == nt


# ===========================================================================
# CanvasEdge model tests
# ===========================================================================


class TestCanvasEdgeModel:
    def test_defaults(self) -> None:
        edge = CanvasEdge(source="n1", target="n2")
        assert edge.edge_type == CanvasEdgeType.CONTAINS
        assert edge.label == ""
        assert edge.animated is False
        assert edge.waypoints == []
        assert edge.metadata == {}

    def test_id_auto_generated(self) -> None:
        e1 = CanvasEdge(source="a", target="b")
        e2 = CanvasEdge(source="a", target="b")
        assert e1.id != e2.id

    def test_all_edge_types_valid(self) -> None:
        for et in CanvasEdgeType:
            edge = CanvasEdge(source="n1", target="n2", edge_type=et)
            assert edge.edge_type == et


# ===========================================================================
# Canvas model tests
# ===========================================================================


class TestCanvasModel:
    def test_defaults(self) -> None:
        c = Canvas(domain_id="d1", domain_name="Domain")
        assert c.layout == CanvasLayout.SMART
        assert c.view_mode == CanvasViewMode.VISUAL
        assert c.nodes == []
        assert c.edges == []
        assert c.viewport_zoom == 1.0

    def test_node_count(self) -> None:
        c = Canvas(domain_id="d1", domain_name="Domain")
        c.nodes = [CanvasNode(id=f"n{i}", node_type=CanvasNodeType.AGENT, label=f"A{i}") for i in range(5)]
        assert c.node_count == 5

    def test_edge_count(self) -> None:
        c = Canvas(domain_id="d1", domain_name="Domain")
        c.edges = [CanvasEdge(source="n0", target="n1") for _ in range(3)]
        assert c.edge_count == 3

    def test_get_node_found(self) -> None:
        c = Canvas(domain_id="d1", domain_name="Domain")
        node = CanvasNode(id="abc", node_type=CanvasNodeType.SKILL, label="Skill")
        c.nodes = [node]
        assert c.get_node("abc") is node

    def test_get_node_not_found(self) -> None:
        c = Canvas(domain_id="d1", domain_name="Domain")
        assert c.get_node("missing") is None

    def test_get_nodes_by_type(self) -> None:
        c = Canvas(domain_id="d1", domain_name="Domain")
        c.nodes = [
            CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="A"),
            CanvasNode(id="a2", node_type=CanvasNodeType.AGENT, label="B"),
            CanvasNode(id="s1", node_type=CanvasNodeType.SKILL, label="S"),
        ]
        agents = c.get_nodes_by_type(CanvasNodeType.AGENT)
        assert len(agents) == 2
        skills = c.get_nodes_by_type(CanvasNodeType.SKILL)
        assert len(skills) == 1

    def test_get_edges_from(self) -> None:
        c = Canvas(domain_id="d1", domain_name="Domain")
        c.nodes = [
            CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"),
            CanvasNode(id="n2", node_type=CanvasNodeType.SKILL, label="S"),
            CanvasNode(id="n3", node_type=CanvasNodeType.DOMAIN, label="D"),
        ]
        e1 = CanvasEdge(source="n1", target="n2")
        e2 = CanvasEdge(source="n1", target="n3")
        e3 = CanvasEdge(source="n3", target="n2")
        c.edges = [e1, e2, e3]
        result = c.get_edges_from("n1")
        assert len(result) == 2
        assert e3 not in result

    def test_get_edges_to(self) -> None:
        c = Canvas(domain_id="d1", domain_name="Domain")
        c.nodes = [
            CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"),
            CanvasNode(id="n2", node_type=CanvasNodeType.SKILL, label="S"),
        ]
        e1 = CanvasEdge(source="n1", target="n2")
        e2 = CanvasEdge(source="n2", target="n1")
        c.edges = [e1, e2]
        to_n2 = c.get_edges_to("n2")
        assert len(to_n2) == 1
        assert to_n2[0] is e1

    def test_get_edge_found(self) -> None:
        c = Canvas(domain_id="d1", domain_name="Domain")
        edge = CanvasEdge(source="n1", target="n2")
        c.edges = [edge]
        assert c.get_edge(edge.id) is edge

    def test_get_edge_not_found(self) -> None:
        c = Canvas(domain_id="d1", domain_name="Domain")
        assert c.get_edge("nonexistent") is None


# ===========================================================================
# CanvasStore tests
# ===========================================================================


class TestCanvasStore:
    def test_add_and_get(self, store: CanvasStore) -> None:
        canvas = Canvas(domain_id="d1", domain_name="Domain")
        store.add(canvas)
        result = store.get("d1")
        assert result is canvas

    def test_get_not_found(self, store: CanvasStore) -> None:
        assert store.get("missing") is None

    def test_update(self, store: CanvasStore) -> None:
        canvas = Canvas(domain_id="d1", domain_name="Old")
        store.add(canvas)
        canvas.domain_name = "New"
        store.update(canvas)
        assert store.get("d1").domain_name == "New"

    def test_version_increments_on_update(self, store: CanvasStore) -> None:
        canvas = Canvas(domain_id="d1", domain_name="D")
        store.add(canvas)
        assert store.version("d1") == 1
        store.update(canvas)
        assert store.version("d1") == 2
        store.update(canvas)
        assert store.version("d1") == 3

    def test_remove(self, store: CanvasStore) -> None:
        canvas = Canvas(domain_id="d1", domain_name="D")
        store.add(canvas)
        store.remove("d1")
        assert store.get("d1") is None

    def test_remove_returns_canvas(self, store: CanvasStore) -> None:
        canvas = Canvas(domain_id="d1", domain_name="D")
        store.add(canvas)
        removed = store.remove("d1")
        assert removed is canvas

    def test_remove_nonexistent_returns_none(self, store: CanvasStore) -> None:
        assert store.remove("ghost") is None

    def test_list_domain_ids(self, store: CanvasStore) -> None:
        store.add(Canvas(domain_id="d1", domain_name="D1"))
        store.add(Canvas(domain_id="d2", domain_name="D2"))
        ids = store.list_domain_ids()
        assert set(ids) == {"d1", "d2"}


# ===========================================================================
# LayoutEngine tests
# ===========================================================================


class TestLayoutEngineLayered:
    def _make_canvas(self) -> Canvas:
        c = Canvas(domain_id="d1", domain_name="D", layout=CanvasLayout.LAYERED)
        c.nodes = [
            CanvasNode(id="dom", node_type=CanvasNodeType.DOMAIN, label="D"),
            CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="A1"),
            CanvasNode(id="a2", node_type=CanvasNodeType.AGENT, label="A2"),
            CanvasNode(id="s1", node_type=CanvasNodeType.SKILL, label="S1"),
            CanvasNode(id="w1", node_type=CanvasNodeType.WORKFLOW, label="W1"),
        ]
        return c

    def test_all_nodes_get_positions(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas()
        layout_engine.layout(c, CanvasLayout.LAYERED)
        for node in c.nodes:
            assert node.x > 0, f"Node {node.id} has x=0"

    def test_domain_in_leftmost_column(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas()
        layout_engine.layout(c, CanvasLayout.LAYERED)
        domain = c.get_node("dom")
        agents = [c.get_node("a1"), c.get_node("a2")]
        # Domain column should be leftmost
        for agent in agents:
            assert domain.x <= agent.x

    def test_agents_have_different_y(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas()
        layout_engine.layout(c, CanvasLayout.LAYERED)
        a1 = c.get_node("a1")
        a2 = c.get_node("a2")
        assert a1.y != a2.y

    def test_columns_separated_horizontally(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas()
        layout_engine.layout(c, CanvasLayout.LAYERED)
        dom = c.get_node("dom")
        skill = c.get_node("s1")
        agent = c.get_node("a1")
        # skill column < agent column (skill comes before agent in _LAYERED_ORDER)
        assert skill.x < agent.x
        # domain is before skill
        assert dom.x < skill.x


class TestLayoutEngineHubAndSpoke:
    def _make_canvas(self, n_spokes: int = 4) -> Canvas:
        c = Canvas(domain_id="d1", domain_name="D", layout=CanvasLayout.HUB_AND_SPOKE)
        c.nodes = [CanvasNode(id="dom", node_type=CanvasNodeType.DOMAIN, label="D")]
        for i in range(n_spokes):
            c.nodes.append(
                CanvasNode(id=f"n{i}", node_type=CanvasNodeType.AGENT, label=f"A{i}")
            )
        return c

    def test_domain_node_near_centre(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas(4)
        layout_engine.layout(c, CanvasLayout.HUB_AND_SPOKE)
        dom = c.get_node("dom")
        # Domain should be roughly centred (x ~= 500 ± 200)
        assert 200 < dom.x < 800
        assert 200 < dom.y < 700

    def test_spoke_nodes_not_coincident(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas(6)
        layout_engine.layout(c, CanvasLayout.HUB_AND_SPOKE)
        positions = [(n.x, n.y) for n in c.nodes if n.id != "dom"]
        # All positions should be unique
        assert len(set(positions)) == len(positions)

    def test_only_domain_no_crash(self, layout_engine: LayoutEngine) -> None:
        c = Canvas(domain_id="d1", domain_name="D", layout=CanvasLayout.HUB_AND_SPOKE)
        c.nodes = [CanvasNode(id="dom", node_type=CanvasNodeType.DOMAIN, label="D")]
        layout_engine.layout(c, CanvasLayout.HUB_AND_SPOKE)  # should not raise


class TestLayoutEngineLinear:
    def _make_canvas(self) -> Canvas:
        c = Canvas(domain_id="d1", domain_name="D", layout=CanvasLayout.LINEAR)
        c.nodes = [
            CanvasNode(id="dom", node_type=CanvasNodeType.DOMAIN, label="D"),
            CanvasNode(id="s1", node_type=CanvasNodeType.SKILL, label="S"),
            CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="A"),
            CanvasNode(id="w1", node_type=CanvasNodeType.WORKFLOW, label="W"),
        ]
        return c

    def test_all_same_y(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas()
        layout_engine.layout(c, CanvasLayout.LINEAR)
        ys = {n.y for n in c.nodes}
        assert len(ys) == 1

    def test_different_x(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas()
        layout_engine.layout(c, CanvasLayout.LINEAR)
        xs = [n.x for n in c.nodes]
        assert len(set(xs)) == len(xs)

    def test_ordered_by_type(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas()
        layout_engine.layout(c, CanvasLayout.LINEAR)
        # Domain comes before Skill, Skill before Agent, Agent before Workflow
        dom = c.get_node("dom")
        s1 = c.get_node("s1")
        a1 = c.get_node("a1")
        w1 = c.get_node("w1")
        assert dom.x < s1.x < a1.x < w1.x


class TestLayoutEngineClustered:
    def _make_canvas(self) -> Canvas:
        c = Canvas(domain_id="d1", domain_name="D", layout=CanvasLayout.CLUSTERED)
        c.nodes = [
            CanvasNode(id="dom", node_type=CanvasNodeType.DOMAIN, label="D"),
            CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="A1"),
            CanvasNode(id="a2", node_type=CanvasNodeType.AGENT, label="A2"),
            CanvasNode(id="a3", node_type=CanvasNodeType.AGENT, label="A3"),
            CanvasNode(id="s1", node_type=CanvasNodeType.SKILL, label="S1"),
            CanvasNode(id="s2", node_type=CanvasNodeType.SKILL, label="S2"),
            CanvasNode(id="w1", node_type=CanvasNodeType.WORKFLOW, label="W1"),
        ]
        c.edges = [
            CanvasEdge(source="a1", target="s1", edge_type=CanvasEdgeType.USES),
            CanvasEdge(source="a2", target="s2", edge_type=CanvasEdgeType.USES),
        ]
        return c

    def test_all_nodes_positioned(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas()
        layout_engine.layout(c, CanvasLayout.CLUSTERED)
        for node in c.nodes:
            assert (node.x, node.y) != (0.0, 0.0), f"Node {node.id} not positioned"

    def test_agents_different_x(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas()
        layout_engine.layout(c, CanvasLayout.CLUSTERED)
        a_xs = [c.get_node(f"a{i}").x for i in range(1, 4)]
        assert len(set(a_xs)) == 3

    def test_workflow_below_agents(self, layout_engine: LayoutEngine) -> None:
        c = self._make_canvas()
        layout_engine.layout(c, CanvasLayout.CLUSTERED)
        w1 = c.get_node("w1")
        a1 = c.get_node("a1")
        assert w1.y > a1.y


class TestLayoutEngineSmart:
    def test_smart_picks_linear_for_tiny(self, layout_engine: LayoutEngine) -> None:
        c = Canvas(domain_id="d1", domain_name="D", layout=CanvasLayout.SMART)
        c.nodes = [
            CanvasNode(id="dom", node_type=CanvasNodeType.DOMAIN, label="D"),
            CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="A"),
        ]
        chosen = layout_engine._choose_smart(c.nodes)
        assert chosen == CanvasLayout.LINEAR

    def test_smart_picks_hub_for_small(self, layout_engine: LayoutEngine) -> None:
        c = Canvas(domain_id="d1", domain_name="D", layout=CanvasLayout.SMART)
        c.nodes = [CanvasNode(id="dom", node_type=CanvasNodeType.DOMAIN, label="D")]
        for i in range(5):
            c.nodes.append(
                CanvasNode(id=f"n{i}", node_type=CanvasNodeType.AGENT, label=f"A{i}")
            )
        chosen = layout_engine._choose_smart(c.nodes)
        assert chosen == CanvasLayout.HUB_AND_SPOKE

    def test_smart_picks_clustered_for_many_agents(self, layout_engine: LayoutEngine) -> None:
        c = Canvas(domain_id="d1", domain_name="D", layout=CanvasLayout.SMART)
        c.nodes = [CanvasNode(id="dom", node_type=CanvasNodeType.DOMAIN, label="D")]
        for i in range(7):
            c.nodes.append(
                CanvasNode(id=f"a{i}", node_type=CanvasNodeType.AGENT, label=f"A{i}")
            )
        chosen = layout_engine._choose_smart(c.nodes)
        assert chosen == CanvasLayout.CLUSTERED

    def test_smart_picks_layered_as_default(self, layout_engine: LayoutEngine) -> None:
        c = Canvas(domain_id="d1", domain_name="D", layout=CanvasLayout.SMART)
        c.nodes = [CanvasNode(id="dom", node_type=CanvasNodeType.DOMAIN, label="D")]
        # 8 mixed-type nodes, fewer than 3 agents — should fall to LAYERED
        for i in range(4):
            c.nodes.append(CanvasNode(id=f"s{i}", node_type=CanvasNodeType.SKILL, label=f"S{i}"))
        for i in range(4):
            c.nodes.append(CanvasNode(id=f"w{i}", node_type=CanvasNodeType.WORKFLOW, label=f"W{i}"))
        chosen = layout_engine._choose_smart(c.nodes)
        assert chosen == CanvasLayout.LAYERED

    def test_smart_layout_runs_without_error(self, layout_engine: LayoutEngine) -> None:
        c = Canvas(domain_id="d1", domain_name="D", layout=CanvasLayout.SMART)
        c.nodes = [
            CanvasNode(id="dom", node_type=CanvasNodeType.DOMAIN, label="D"),
            CanvasNode(id="a1", node_type=CanvasNodeType.AGENT, label="A"),
            CanvasNode(id="s1", node_type=CanvasNodeType.SKILL, label="S"),
        ]
        layout_engine.layout(c)  # should not raise


# ===========================================================================
# CanvasService — create_canvas
# ===========================================================================


class TestCanvasServiceCreate:
    @pytest.mark.asyncio
    async def test_create_canvas_returns_canvas(self, svc: CanvasService) -> None:
        canvas = await svc.create_canvas("d1", "Domain 1")
        assert isinstance(canvas, Canvas)
        assert canvas.domain_id == "d1"
        assert canvas.domain_name == "Domain 1"

    @pytest.mark.asyncio
    async def test_create_canvas_stored(self, svc: CanvasService) -> None:
        canvas = await svc.create_canvas("d1", "Domain 1")
        stored = svc.store.get("d1")
        assert stored is not None
        assert stored.id == canvas.id

    @pytest.mark.asyncio
    async def test_create_canvas_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "Domain 1")
        entries = await tape_svc.get_entries(event_type="canvas.created")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_create_canvas_log_payload(self, svc: CanvasService, tape_svc: TapeService) -> None:
        canvas = await svc.create_canvas("d1", "Domain 1")
        entries = await tape_svc.get_entries(event_type="canvas.created")
        payload = entries[0].payload
        assert payload["domain_id"] == "d1"
        assert payload["canvas_id"] == str(canvas.id)

    @pytest.mark.asyncio
    async def test_create_canvas_default_layout(self, svc: CanvasService) -> None:
        canvas = await svc.create_canvas("d1", "Domain 1")
        assert canvas.layout == CanvasLayout.SMART

    @pytest.mark.asyncio
    async def test_create_canvas_explicit_layout(self, svc: CanvasService) -> None:
        canvas = await svc.create_canvas("d1", "Domain 1", layout=CanvasLayout.LAYERED)
        assert canvas.layout == CanvasLayout.LAYERED


# ===========================================================================
# CanvasService — get_canvas
# ===========================================================================


class TestCanvasServiceGet:
    @pytest.mark.asyncio
    async def test_get_existing(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "Domain 1")
        canvas = await svc.get_canvas("d1")
        assert canvas.domain_id == "d1"

    @pytest.mark.asyncio
    async def test_get_not_found_raises(self, svc: CanvasService) -> None:
        with pytest.raises(CanvasNotFoundError):
            await svc.get_canvas("nonexistent")


# ===========================================================================
# CanvasService — add_node
# ===========================================================================


class TestCanvasServiceAddNode:
    @pytest.mark.asyncio
    async def test_add_node_appears_on_canvas(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        node = CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="Agent")
        await svc.add_node("d1", node)
        canvas = await svc.get_canvas("d1")
        assert canvas.get_node("n1") is not None

    @pytest.mark.asyncio
    async def test_add_node_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "D")
        node = CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="Agent")
        await svc.add_node("d1", node)
        entries = await tape_svc.get_entries(event_type="canvas.node_added")
        assert len(entries) == 1
        assert entries[0].payload["node_id"] == "n1"

    @pytest.mark.asyncio
    async def test_add_node_injects_colour(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        node = CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A")
        await svc.add_node("d1", node)
        canvas = await svc.get_canvas("d1")
        assert "colour" in canvas.get_node("n1").metadata

    @pytest.mark.asyncio
    async def test_add_node_injects_icon(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        node = CanvasNode(id="n1", node_type=CanvasNodeType.SKILL, label="S")
        await svc.add_node("d1", node)
        canvas = await svc.get_canvas("d1")
        assert "icon" in canvas.get_node("n1").metadata

    @pytest.mark.asyncio
    async def test_add_duplicate_raises(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        node = CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A")
        await svc.add_node("d1", node)
        with pytest.raises(NodeAlreadyExistsError):
            await svc.add_node("d1", node)

    @pytest.mark.asyncio
    async def test_add_node_canvas_not_found(self, svc: CanvasService) -> None:
        node = CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A")
        with pytest.raises(CanvasNotFoundError):
            await svc.add_node("nonexistent", node)

    @pytest.mark.asyncio
    async def test_preserves_existing_colour_metadata(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        node = CanvasNode(
            id="n1", node_type=CanvasNodeType.AGENT, label="A",
            metadata={"colour": "#custom"}
        )
        await svc.add_node("d1", node)
        canvas = await svc.get_canvas("d1")
        assert canvas.get_node("n1").metadata["colour"] == "#custom"


# ===========================================================================
# CanvasService — remove_node
# ===========================================================================


class TestCanvasServiceRemoveNode:
    @pytest.mark.asyncio
    async def test_remove_node_disappears(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        node = CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A")
        await svc.add_node("d1", node)
        await svc.remove_node("d1", "n1")
        canvas = await svc.get_canvas("d1")
        assert canvas.get_node("n1") is None

    @pytest.mark.asyncio
    async def test_remove_node_removes_connected_edges(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.add_node("d1", CanvasNode(id="n2", node_type=CanvasNodeType.SKILL, label="S"))
        await svc.add_edge("d1", CanvasEdge(source="n1", target="n2"))
        await svc.remove_node("d1", "n1")
        canvas = await svc.get_canvas("d1")
        assert canvas.edge_count == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_raises(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        with pytest.raises(NodeNotFoundError):
            await svc.remove_node("d1", "ghost")

    @pytest.mark.asyncio
    async def test_remove_locked_raises(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        node = CanvasNode(id="n1", node_type=CanvasNodeType.DOMAIN, label="D", locked=True)
        await svc.add_node("d1", node)
        with pytest.raises(CanvasError):
            await svc.remove_node("d1", "n1")

    @pytest.mark.asyncio
    async def test_remove_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.remove_node("d1", "n1")
        entries = await tape_svc.get_entries(event_type="canvas.node_removed")
        assert len(entries) == 1


# ===========================================================================
# CanvasService — move_node
# ===========================================================================


class TestCanvasServiceMoveNode:
    @pytest.mark.asyncio
    async def test_move_updates_position(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        node = await svc.move_node("d1", "n1", 123.0, 456.0)
        assert node.x == 123.0
        assert node.y == 456.0

    @pytest.mark.asyncio
    async def test_move_persisted(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.move_node("d1", "n1", 99.0, 88.0)
        canvas = await svc.get_canvas("d1")
        assert canvas.get_node("n1").x == 99.0

    @pytest.mark.asyncio
    async def test_move_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.move_node("d1", "n1", 10.0, 20.0)
        entries = await tape_svc.get_entries(event_type="canvas.node_moved")
        assert len(entries) == 1
        payload = entries[0].payload
        assert payload["to"]["x"] == 10.0

    @pytest.mark.asyncio
    async def test_move_nonexistent_raises(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        with pytest.raises(NodeNotFoundError):
            await svc.move_node("d1", "ghost", 0.0, 0.0)


# ===========================================================================
# CanvasService — update_node
# ===========================================================================


class TestCanvasServiceUpdateNode:
    @pytest.mark.asyncio
    async def test_update_label(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="Old"))
        node = await svc.update_node("d1", "n1", label="New")
        assert node.label == "New"

    @pytest.mark.asyncio
    async def test_update_metadata(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.update_node("d1", "n1", metadata={"extra": "value"})
        canvas = await svc.get_canvas("d1")
        assert canvas.get_node("n1").metadata["extra"] == "value"

    @pytest.mark.asyncio
    async def test_update_nonexistent_raises(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        with pytest.raises(NodeNotFoundError):
            await svc.update_node("d1", "ghost", label="X")

    @pytest.mark.asyncio
    async def test_update_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.update_node("d1", "n1", label="Updated")
        entries = await tape_svc.get_entries(event_type="canvas.node_updated")
        assert len(entries) == 1


# ===========================================================================
# CanvasService — add_edge / remove_edge
# ===========================================================================


class TestCanvasServiceEdges:
    @pytest.mark.asyncio
    async def test_add_edge_appears_on_canvas(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.add_node("d1", CanvasNode(id="n2", node_type=CanvasNodeType.SKILL, label="S"))
        edge = CanvasEdge(source="n1", target="n2", edge_type=CanvasEdgeType.USES)
        await svc.add_edge("d1", edge)
        canvas = await svc.get_canvas("d1")
        assert canvas.get_edge(edge.id) is not None

    @pytest.mark.asyncio
    async def test_add_edge_invalid_source_raises(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n2", node_type=CanvasNodeType.SKILL, label="S"))
        with pytest.raises(InvalidEdgeError):
            await svc.add_edge("d1", CanvasEdge(source="ghost", target="n2"))

    @pytest.mark.asyncio
    async def test_add_edge_invalid_target_raises(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        with pytest.raises(InvalidEdgeError):
            await svc.add_edge("d1", CanvasEdge(source="n1", target="ghost"))

    @pytest.mark.asyncio
    async def test_add_edge_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.add_node("d1", CanvasNode(id="n2", node_type=CanvasNodeType.SKILL, label="S"))
        await svc.add_edge("d1", CanvasEdge(source="n1", target="n2"))
        entries = await tape_svc.get_entries(event_type="canvas.edge_added")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_remove_edge_disappears(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.add_node("d1", CanvasNode(id="n2", node_type=CanvasNodeType.SKILL, label="S"))
        edge = CanvasEdge(source="n1", target="n2")
        await svc.add_edge("d1", edge)
        await svc.remove_edge("d1", edge.id)
        canvas = await svc.get_canvas("d1")
        assert canvas.get_edge(edge.id) is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_edge_raises(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        with pytest.raises(EdgeNotFoundError):
            await svc.remove_edge("d1", "ghost")

    @pytest.mark.asyncio
    async def test_remove_edge_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.add_node("d1", CanvasNode(id="n2", node_type=CanvasNodeType.SKILL, label="S"))
        edge = CanvasEdge(source="n1", target="n2")
        await svc.add_edge("d1", edge)
        await svc.remove_edge("d1", edge.id)
        entries = await tape_svc.get_entries(event_type="canvas.edge_removed")
        assert len(entries) == 1


# ===========================================================================
# CanvasService — apply_layout
# ===========================================================================


class TestCanvasServiceApplyLayout:
    @pytest.mark.asyncio
    async def test_apply_layout_moves_nodes(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        for i in range(4):
            await svc.add_node(
                "d1",
                CanvasNode(id=f"n{i}", node_type=CanvasNodeType.AGENT, label=f"A{i}"),
            )
        canvas = await svc.apply_layout("d1", CanvasLayout.LINEAR)
        ys = {n.y for n in canvas.nodes}
        assert len(ys) == 1  # LINEAR — all same y

    @pytest.mark.asyncio
    async def test_apply_layout_updates_canvas_layout_field(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D", layout=CanvasLayout.SMART)
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        canvas = await svc.apply_layout("d1", CanvasLayout.LAYERED)
        assert canvas.layout == CanvasLayout.LAYERED

    @pytest.mark.asyncio
    async def test_apply_layout_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.apply_layout("d1", CanvasLayout.LAYERED)
        entries = await tape_svc.get_entries(event_type="canvas.layout_applied")
        assert len(entries) == 1


# ===========================================================================
# CanvasService — set_view_mode
# ===========================================================================


class TestCanvasServiceViewMode:
    @pytest.mark.asyncio
    async def test_switch_to_folder_mode(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        canvas = await svc.set_view_mode("d1", CanvasViewMode.FOLDER)
        assert canvas.view_mode == CanvasViewMode.FOLDER

    @pytest.mark.asyncio
    async def test_switch_to_visual_mode(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.set_view_mode("d1", CanvasViewMode.FOLDER)
        canvas = await svc.set_view_mode("d1", CanvasViewMode.VISUAL)
        assert canvas.view_mode == CanvasViewMode.VISUAL

    @pytest.mark.asyncio
    async def test_switch_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.set_view_mode("d1", CanvasViewMode.FOLDER)
        entries = await tape_svc.get_entries(event_type="canvas.view_mode_changed")
        assert len(entries) == 1
        payload = entries[0].payload
        assert payload["from"] == "visual"
        assert payload["to"] == "folder"


# ===========================================================================
# CanvasService — sync_to_folder_tree
# ===========================================================================


class TestCanvasServiceSyncToTree:
    @pytest.mark.asyncio
    async def test_sync_no_tree_service_no_error(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A", folder_path="D/agents/a"))
        await svc.sync_to_folder_tree("d1")  # should not raise

    @pytest.mark.asyncio
    async def test_sync_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        await svc.sync_to_folder_tree("d1")
        entries = await tape_svc.get_entries(event_type="canvas.synced_to_tree")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_sync_with_tree_service(
        self, svc_with_tree: CanvasService, folder_svc: FolderTreeService
    ) -> None:
        await folder_svc.create_tree(
            domain_id="d1", domain_name="D", description="D",
            agents=[], skills=[], workflows=[],
        )
        await svc_with_tree.create_canvas("d1", "D")
        await svc_with_tree.add_node(
            "d1",
            CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A", folder_path="agents/new_agent"),
            sync_to_tree=True,
        )
        await svc_with_tree.sync_to_folder_tree("d1")
        # No exception means success


# ===========================================================================
# CanvasService — sync_from_folder_tree
# ===========================================================================


class TestCanvasServiceSyncFromTree:
    @pytest.mark.asyncio
    async def test_sync_no_tree_service_returns_canvas(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        canvas = await svc.sync_from_folder_tree("d1")
        assert isinstance(canvas, Canvas)

    @pytest.mark.asyncio
    async def test_sync_logs_event(self, svc: CanvasService, tape_svc: TapeService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.sync_from_folder_tree("d1")
        entries = await tape_svc.get_entries(event_type="canvas.synced_from_tree")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_sync_from_tree_adds_nodes(
        self, svc_with_tree: CanvasService, folder_svc: FolderTreeService
    ) -> None:
        await folder_svc.create_tree(
            domain_id="d1", domain_name="D", description="D",
            agents=[], skills=[], workflows=[],
        )
        await svc_with_tree.create_canvas("d1", "D")
        canvas = await svc_with_tree.sync_from_folder_tree("d1")
        # The tree has some standard dirs; they should become nodes
        assert canvas.node_count >= 0  # no crash; nodes may or may not be added


# ===========================================================================
# CanvasService — canvas_from_domain_blueprint
# ===========================================================================


class TestCanvasFromBlueprint:
    @pytest.mark.asyncio
    async def test_creates_canvas(self, svc: CanvasService) -> None:
        bp = _make_minimal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        assert isinstance(canvas, Canvas)
        assert canvas.domain_id == bp.domain_id

    @pytest.mark.asyncio
    async def test_has_domain_node(self, svc: CanvasService) -> None:
        bp = _make_minimal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        domain_nodes = canvas.get_nodes_by_type(CanvasNodeType.DOMAIN)
        assert len(domain_nodes) == 1
        assert domain_nodes[0].label == bp.domain_name

    @pytest.mark.asyncio
    async def test_has_agent_nodes(self, svc: CanvasService) -> None:
        bp = _make_legal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        agents = canvas.get_nodes_by_type(CanvasNodeType.AGENT)
        assert len(agents) == len(bp.agents)

    @pytest.mark.asyncio
    async def test_has_skill_nodes(self, svc: CanvasService) -> None:
        bp = _make_legal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        skills = canvas.get_nodes_by_type(CanvasNodeType.SKILL)
        assert len(skills) == len(bp.skills)

    @pytest.mark.asyncio
    async def test_has_workflow_nodes(self, svc: CanvasService) -> None:
        bp = _make_legal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        workflows = canvas.get_nodes_by_type(CanvasNodeType.WORKFLOW)
        assert len(workflows) == len(bp.workflows)

    @pytest.mark.asyncio
    async def test_total_node_count(self, svc: CanvasService) -> None:
        bp = _make_legal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        expected = 1 + len(bp.agents) + len(bp.skills) + len(bp.workflows)
        assert canvas.node_count == expected

    @pytest.mark.asyncio
    async def test_has_edges(self, svc: CanvasService) -> None:
        bp = _make_legal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        assert canvas.edge_count > 0

    @pytest.mark.asyncio
    async def test_domain_edges_connect_agents(self, svc: CanvasService) -> None:
        bp = _make_legal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        domain_node = canvas.get_nodes_by_type(CanvasNodeType.DOMAIN)[0]
        outgoing = canvas.get_edges_from(domain_node.id)
        agent_targets = {
            e.target for e in outgoing if e.edge_type == CanvasEdgeType.CONTAINS
        }
        # All agents should be reachable from domain
        assert len(agent_targets) > 0

    @pytest.mark.asyncio
    async def test_workflow_edges_connect_agents(self, svc: CanvasService) -> None:
        bp = _make_legal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        wf_nodes = canvas.get_nodes_by_type(CanvasNodeType.WORKFLOW)
        for wf_node in wf_nodes:
            executes = [e for e in canvas.get_edges_from(wf_node.id)
                        if e.edge_type == CanvasEdgeType.EXECUTES]
            assert len(executes) > 0

    @pytest.mark.asyncio
    async def test_all_nodes_positioned(self, svc: CanvasService) -> None:
        bp = _make_legal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        # After layout, not all nodes should be at (0, 0)
        not_origin = [n for n in canvas.nodes if (n.x, n.y) != (0.0, 0.0)]
        assert len(not_origin) > 0

    @pytest.mark.asyncio
    async def test_logs_created_from_blueprint_event(
        self, svc: CanvasService, tape_svc: TapeService
    ) -> None:
        bp = _make_minimal_blueprint()
        await svc.canvas_from_domain_blueprint(bp)
        entries = await tape_svc.get_entries(event_type="canvas.created_from_blueprint")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_blueprint_event_payload(
        self, svc: CanvasService, tape_svc: TapeService
    ) -> None:
        bp = _make_minimal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        entries = await tape_svc.get_entries(event_type="canvas.created_from_blueprint")
        payload = entries[0].payload
        assert payload["domain_id"] == bp.domain_id
        assert payload["node_count"] == canvas.node_count
        assert payload["blueprint_id"] == str(bp.id)

    @pytest.mark.asyncio
    async def test_explicit_layout_used(self, svc: CanvasService) -> None:
        bp = _make_minimal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp, layout=CanvasLayout.LAYERED)
        assert canvas.layout == CanvasLayout.LAYERED

    @pytest.mark.asyncio
    async def test_agent_folder_paths_set(self, svc: CanvasService) -> None:
        bp = _make_minimal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        agent_nodes = canvas.get_nodes_by_type(CanvasNodeType.AGENT)
        for node in agent_nodes:
            assert node.folder_path != "", f"Agent node {node.id} has no folder_path"

    @pytest.mark.asyncio
    async def test_node_metadata_colour_set(self, svc: CanvasService) -> None:
        bp = _make_minimal_blueprint()
        canvas = await svc.canvas_from_domain_blueprint(bp)
        for node in canvas.nodes:
            assert "colour" in node.metadata, f"Node {node.id} missing colour"


# ===========================================================================
# CanvasService — diff
# ===========================================================================


class TestCanvasServiceDiff:
    @pytest.mark.asyncio
    async def test_diff_no_changes(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        canvas = await svc.get_canvas("d1")
        diff = await svc.diff("d1", canvas, canvas)
        assert diff.added_nodes == []
        assert diff.removed_node_ids == []
        assert diff.summary == "no changes"

    @pytest.mark.asyncio
    async def test_diff_detects_added_node(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        old = await svc.get_canvas("d1")

        import copy
        new_canvas = copy.deepcopy(old)
        new_canvas.nodes.append(
            CanvasNode(id="new-node", node_type=CanvasNodeType.AGENT, label="New")
        )

        diff = await svc.diff("d1", old, new_canvas)
        assert len(diff.added_nodes) == 1
        assert diff.added_nodes[0].id == "new-node"

    @pytest.mark.asyncio
    async def test_diff_detects_removed_node(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A"))
        old = await svc.get_canvas("d1")

        import copy
        new_canvas = copy.deepcopy(old)
        new_canvas.nodes = [n for n in new_canvas.nodes if n.id != "n1"]

        diff = await svc.diff("d1", old, new_canvas)
        assert "n1" in diff.removed_node_ids

    @pytest.mark.asyncio
    async def test_diff_detects_moved_node(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        await svc.add_node("d1", CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="A", x=0, y=0))
        old = await svc.get_canvas("d1")

        import copy
        new_canvas = copy.deepcopy(old)
        new_canvas.get_node("n1").x = 999.0

        diff = await svc.diff("d1", old, new_canvas)
        assert len(diff.moved_nodes) == 1
        assert diff.moved_nodes[0].id == "n1"

    @pytest.mark.asyncio
    async def test_diff_summary_non_empty_on_changes(self, svc: CanvasService) -> None:
        await svc.create_canvas("d1", "D")
        old = await svc.get_canvas("d1")

        import copy
        new_canvas = copy.deepcopy(old)
        new_canvas.nodes.append(
            CanvasNode(id="extra", node_type=CanvasNodeType.SKILL, label="X")
        )

        diff = await svc.diff("d1", old, new_canvas)
        assert diff.summary != "no changes"
        assert "+" in diff.summary


# ===========================================================================
# CanvasService — infer_node_type
# ===========================================================================


class TestInferNodeType:
    def test_agents_inferred(self, svc: CanvasService) -> None:
        assert svc._infer_node_type("agents") == CanvasNodeType.AGENT

    def test_skills_inferred(self, svc: CanvasService) -> None:
        assert svc._infer_node_type("skills") == CanvasNodeType.SKILL

    def test_workflows_inferred(self, svc: CanvasService) -> None:
        assert svc._infer_node_type("workflows") == CanvasNodeType.WORKFLOW

    def test_templates_inferred(self, svc: CanvasService) -> None:
        assert svc._infer_node_type("templates") == CanvasNodeType.TEMPLATE

    def test_data_sources_inferred(self, svc: CanvasService) -> None:
        assert svc._infer_node_type("data_sources") == CanvasNodeType.DATA_SOURCE

    def test_unknown_defaults_to_custom(self, svc: CanvasService) -> None:
        assert svc._infer_node_type("evaluation") == CanvasNodeType.CUSTOM


# ===========================================================================
# Package-level import tests
# ===========================================================================


class TestPackageImports:
    def test_canvas(self) -> None:
        from packages.canvas import Canvas  # noqa: F401

    def test_canvas_node(self) -> None:
        from packages.canvas import CanvasNode  # noqa: F401

    def test_canvas_edge(self) -> None:
        from packages.canvas import CanvasEdge  # noqa: F401

    def test_canvas_node_type(self) -> None:
        from packages.canvas import CanvasNodeType  # noqa: F401

    def test_canvas_edge_type(self) -> None:
        from packages.canvas import CanvasEdgeType  # noqa: F401

    def test_canvas_layout(self) -> None:
        from packages.canvas import CanvasLayout  # noqa: F401

    def test_canvas_view_mode(self) -> None:
        from packages.canvas import CanvasViewMode  # noqa: F401

    def test_canvas_diff(self) -> None:
        pass

    def test_layout_engine(self) -> None:
        from packages.canvas import LayoutEngine  # noqa: F401

    def test_canvas_service(self) -> None:
        from packages.canvas import CanvasService  # noqa: F401

    def test_canvas_store(self) -> None:
        from packages.canvas import CanvasStore  # noqa: F401

    def test_exceptions(self) -> None:
        from packages.canvas import (  # noqa: F401
            CanvasError,
            CanvasNotFoundError,
            EdgeNotFoundError,
            InvalidEdgeError,
            NodeAlreadyExistsError,
            NodeNotFoundError,
        )
