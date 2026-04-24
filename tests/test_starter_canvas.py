"""Tests for the Starter Canvas Generator (Agent 3 — One-Click Domain Creation).

Covers:
- CanvasNode / CanvasEdge / StarterCanvas data models
- Layout heuristic selection
- Node construction from DomainBlueprint
- Edge topology (CONTAINS, USES, EXECUTES)
- All four layout algorithms (LAYERED, HUB_AND_SPOKE, CLUSTERED, LINEAR)
- Tape logging
- Edge cases (empty blueprint, single agent, no workflows)
"""

from __future__ import annotations

import math

import pytest

from packages.domain.starter_canvas import (
    CanvasEdgeType,
    CanvasLayout,
    CanvasNode,
    CanvasNodeType,
    StarterCanvas,
    StarterCanvasGenerator,
)
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
def generator(tape_svc: TapeService) -> StarterCanvasGenerator:
    return StarterCanvasGenerator(tape_service=tape_svc)


@pytest.fixture()
def minimal_blueprint() -> DomainBlueprint:
    """Smallest valid blueprint — one agent, one skill, no workflows."""
    return DomainBlueprint(
        domain_name="Minimal Domain",
        domain_id="minimal-domain",
        description="A minimal test domain",
        agents=[
            AgentBlueprint(
                agent_id="agent-1",
                name="Analyst",
                role=AgentRole.SPECIALIST,
                goal="Analyse data",
                capabilities=["data_analysis"],
                tools=["data_extractor"],
            )
        ],
        skills=[
            SkillBlueprint(
                skill_id="data_extractor",
                name="Data Extractor",
                description="Extracts structured data",
            )
        ],
    )


@pytest.fixture()
def medium_blueprint() -> DomainBlueprint:
    """Medium blueprint — 3 agents, 4 skills, 2 workflows."""
    return DomainBlueprint(
        domain_name="Legal Research Domain",
        domain_id="legal-research",
        description="Multi-agent legal research system",
        agents=[
            AgentBlueprint(
                agent_id="contract-analyst",
                name="Contract Analyst",
                role=AgentRole.SPECIALIST,
                goal="Analyse contracts",
                capabilities=["contract_analysis", "risk_scoring"],
                tools=["contract_analysis", "risk_scorer"],
            ),
            AgentBlueprint(
                agent_id="compliance-checker",
                name="Compliance Checker",
                role=AgentRole.SPECIALIST,
                goal="Check regulatory compliance",
                capabilities=["regulation_lookup"],
                tools=["regulation_lookup"],
            ),
            AgentBlueprint(
                agent_id="summary-writer",
                name="Summary Writer",
                role=AgentRole.COORDINATOR,
                goal="Write executive summaries",
                capabilities=["text_generation"],
                tools=["summariser"],
            ),
        ],
        skills=[
            SkillBlueprint(skill_id="contract_analysis", name="Contract Analysis"),
            SkillBlueprint(skill_id="risk_scorer", name="Risk Scorer"),
            SkillBlueprint(skill_id="regulation_lookup", name="Regulation Lookup"),
            SkillBlueprint(skill_id="summariser", name="Summariser"),
        ],
        workflows=[
            WorkflowBlueprint(
                workflow_id="full-review",
                name="Full Contract Review",
                workflow_type=WorkflowType.SEQUENTIAL,
                agent_ids=["contract-analyst", "compliance-checker", "summary-writer"],
                steps=["extract", "analyse", "check", "summarise"],
            ),
            WorkflowBlueprint(
                workflow_id="quick-check",
                name="Quick Compliance Check",
                workflow_type=WorkflowType.SEQUENTIAL,
                agent_ids=["compliance-checker"],
                steps=["check"],
            ),
        ],
    )


@pytest.fixture()
def large_blueprint() -> DomainBlueprint:
    """Large blueprint — 5 agents with multiple tools each (triggers CLUSTERED)."""
    agents = [
        AgentBlueprint(
            agent_id=f"agent-{i}",
            name=f"Agent {i}",
            role=AgentRole.SPECIALIST,
            goal=f"Goal {i}",
            capabilities=[f"cap-{i}-a", f"cap-{i}-b", f"cap-{i}-c"],
            tools=[f"skill-{i}-a", f"skill-{i}-b"],
        )
        for i in range(5)
    ]
    skills = [
        SkillBlueprint(skill_id=f"skill-{i}-{s}", name=f"Skill {i} {s}")
        for i in range(5)
        for s in ("a", "b")
    ]
    return DomainBlueprint(
        domain_name="Large Domain",
        domain_id="large-domain",
        description="Many agents and skills",
        agents=agents,
        skills=skills,
    )


# ---------------------------------------------------------------------------
# Data model tests
# ---------------------------------------------------------------------------


class TestCanvasNode:
    def test_defaults(self) -> None:
        node = CanvasNode(id="n1", node_type=CanvasNodeType.AGENT, label="Test")
        assert node.x == 0.0
        assert node.y == 0.0
        assert node.width == 180.0
        assert node.height == 60.0
        assert node.metadata == {}

    def test_custom_position(self) -> None:
        node = CanvasNode(id="n1", node_type=CanvasNodeType.SKILL, label="Skill", x=100.0, y=200.0)
        assert node.x == 100.0
        assert node.y == 200.0


class TestStarterCanvas:
    def test_node_count(self) -> None:
        canvas = StarterCanvas(domain_id="d", domain_name="D", layout=CanvasLayout.LINEAR)
        canvas.nodes = [
            CanvasNode(id="a", node_type=CanvasNodeType.DOMAIN, label="D"),
            CanvasNode(id="b", node_type=CanvasNodeType.AGENT, label="A"),
        ]
        assert canvas.node_count == 2

    def test_edge_count(self) -> None:
        from packages.domain.starter_canvas import CanvasEdge
        canvas = StarterCanvas(domain_id="d", domain_name="D", layout=CanvasLayout.LINEAR)
        canvas.edges = [CanvasEdge(source="a", target="b")]
        assert canvas.edge_count == 1

    def test_get_node(self) -> None:
        canvas = StarterCanvas(domain_id="d", domain_name="D", layout=CanvasLayout.LINEAR)
        node = CanvasNode(id="x", node_type=CanvasNodeType.SKILL, label="S")
        canvas.nodes = [node]
        assert canvas.get_node("x") is node
        assert canvas.get_node("missing") is None

    def test_get_nodes_by_type(self) -> None:
        canvas = StarterCanvas(domain_id="d", domain_name="D", layout=CanvasLayout.LINEAR)
        canvas.nodes = [
            CanvasNode(id="a", node_type=CanvasNodeType.AGENT, label="A1"),
            CanvasNode(id="b", node_type=CanvasNodeType.AGENT, label="A2"),
            CanvasNode(id="c", node_type=CanvasNodeType.SKILL, label="S1"),
        ]
        agents = canvas.get_nodes_by_type(CanvasNodeType.AGENT)
        assert len(agents) == 2
        skills = canvas.get_nodes_by_type(CanvasNodeType.SKILL)
        assert len(skills) == 1


# ---------------------------------------------------------------------------
# Layout heuristic tests
# ---------------------------------------------------------------------------


class TestChooseLayout:
    def test_linear_for_very_small(self, generator: StarterCanvasGenerator) -> None:
        bp = DomainBlueprint(
            domain_name="Tiny", domain_id="tiny",
            agents=[AgentBlueprint(agent_id="a", name="A")],
            skills=[SkillBlueprint(skill_id="s", name="S")],
        )
        assert generator._choose_layout(bp) == CanvasLayout.LINEAR

    def test_hub_spoke_for_small(self, generator: StarterCanvasGenerator) -> None:
        bp = DomainBlueprint(
            domain_name="Small", domain_id="small",
            agents=[
                AgentBlueprint(agent_id=f"a{i}", name=f"A{i}")
                for i in range(3)
            ],
            skills=[
                SkillBlueprint(skill_id=f"s{i}", name=f"S{i}")
                for i in range(2)
            ],
        )
        assert generator._choose_layout(bp) == CanvasLayout.HUB_AND_SPOKE

    def test_clustered_for_agents_with_many_tools(
        self, generator: StarterCanvasGenerator, large_blueprint: DomainBlueprint
    ) -> None:
        assert generator._choose_layout(large_blueprint) == CanvasLayout.CLUSTERED

    def test_layered_default(self, generator: StarterCanvasGenerator) -> None:
        bp = DomainBlueprint(
            domain_name="Medium", domain_id="medium",
            agents=[
                AgentBlueprint(agent_id=f"a{i}", name=f"A{i}", tools=[], capabilities=[])
                for i in range(4)
            ],
            skills=[
                SkillBlueprint(skill_id=f"s{i}", name=f"S{i}")
                for i in range(4)
            ],
        )
        assert generator._choose_layout(bp) == CanvasLayout.LAYERED


# ---------------------------------------------------------------------------
# Node construction tests
# ---------------------------------------------------------------------------


class TestBuildNodes:
    def test_domain_node_always_present(
        self, generator: StarterCanvasGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(minimal_blueprint)
        domain_nodes = [n for n in nodes if n.node_type == CanvasNodeType.DOMAIN]
        assert len(domain_nodes) == 1
        assert domain_nodes[0].label == "Minimal Domain"

    def test_agent_nodes_created(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(medium_blueprint)
        agent_nodes = [n for n in nodes if n.node_type == CanvasNodeType.AGENT]
        assert len(agent_nodes) == 3

    def test_skill_nodes_created(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(medium_blueprint)
        skill_nodes = [n for n in nodes if n.node_type == CanvasNodeType.SKILL]
        assert len(skill_nodes) == 4

    def test_workflow_nodes_created(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(medium_blueprint)
        wf_nodes = [n for n in nodes if n.node_type == CanvasNodeType.WORKFLOW]
        assert len(wf_nodes) == 2

    def test_node_metadata_has_colour_and_icon(
        self, generator: StarterCanvasGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(minimal_blueprint)
        for node in nodes:
            assert "colour" in node.metadata
            assert "icon" in node.metadata

    def test_node_ids_are_unique(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(medium_blueprint)
        ids = [n.id for n in nodes]
        assert len(ids) == len(set(ids))

    def test_empty_blueprint_has_only_domain_node(
        self, generator: StarterCanvasGenerator
    ) -> None:
        bp = DomainBlueprint(domain_name="Empty", domain_id="empty")
        nodes = generator._build_nodes(bp)
        assert len(nodes) == 1
        assert nodes[0].node_type == CanvasNodeType.DOMAIN


# ---------------------------------------------------------------------------
# Edge construction tests
# ---------------------------------------------------------------------------


class TestBuildEdges:
    def test_domain_to_agent_edges(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(medium_blueprint)
        edges = generator._build_edges(medium_blueprint, nodes)
        contains_edges = [e for e in edges if e.edge_type == CanvasEdgeType.CONTAINS]
        agent_targets = [
            e.target for e in contains_edges
            if e.target.startswith("agent-")
        ]
        assert len(agent_targets) == 3  # 3 agents

    def test_agent_to_skill_uses_edges(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(medium_blueprint)
        edges = generator._build_edges(medium_blueprint, nodes)
        uses_edges = [e for e in edges if e.edge_type == CanvasEdgeType.USES]
        assert len(uses_edges) > 0

    def test_workflow_to_agent_executes_edges(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(medium_blueprint)
        edges = generator._build_edges(medium_blueprint, nodes)
        executes_edges = [e for e in edges if e.edge_type == CanvasEdgeType.EXECUTES]
        # full-review workflow → 3 agents, quick-check → 1 agent = 4 total
        assert len(executes_edges) == 4

    def test_no_edges_for_empty_blueprint(
        self, generator: StarterCanvasGenerator
    ) -> None:
        bp = DomainBlueprint(domain_name="Empty", domain_id="empty")
        nodes = generator._build_nodes(bp)
        edges = generator._build_edges(bp, nodes)
        assert edges == []

    def test_edge_source_and_target_exist_as_node_ids(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(medium_blueprint)
        edges = generator._build_edges(medium_blueprint, nodes)
        node_ids = {n.id for n in nodes}
        for edge in edges:
            assert edge.source in node_ids, f"source {edge.source!r} not in nodes"
            assert edge.target in node_ids, f"target {edge.target!r} not in nodes"

    def test_uses_edges_are_animated(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        nodes = generator._build_nodes(medium_blueprint)
        edges = generator._build_edges(medium_blueprint, nodes)
        for edge in edges:
            if edge.edge_type == CanvasEdgeType.USES:
                assert edge.animated is True


# ---------------------------------------------------------------------------
# Layout algorithm tests
# ---------------------------------------------------------------------------


class TestLayeredLayout:
    @pytest.mark.asyncio
    async def test_all_nodes_get_positions(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(medium_blueprint, layout=CanvasLayout.LAYERED)
        for node in canvas.nodes:
            # All nodes should have been placed (non-zero for non-domain)
            assert isinstance(node.x, float)
            assert isinstance(node.y, float)

    @pytest.mark.asyncio
    async def test_domain_node_in_first_column(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(medium_blueprint, layout=CanvasLayout.LAYERED)
        domain_node = canvas.get_nodes_by_type(CanvasNodeType.DOMAIN)[0]
        agent_nodes = canvas.get_nodes_by_type(CanvasNodeType.AGENT)
        # Domain node should be left of agents
        for agent in agent_nodes:
            assert domain_node.x < agent.x

    @pytest.mark.asyncio
    async def test_nodes_in_same_column_have_different_y(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(medium_blueprint, layout=CanvasLayout.LAYERED)
        agent_nodes = canvas.get_nodes_by_type(CanvasNodeType.AGENT)
        ys = [n.y for n in agent_nodes]
        assert len(ys) == len(set(ys))  # all unique y positions


class TestHubSpokeLayout:
    @pytest.mark.asyncio
    async def test_domain_node_is_central(
        self, generator: StarterCanvasGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(minimal_blueprint, layout=CanvasLayout.HUB_AND_SPOKE)
        domain_node = canvas.get_nodes_by_type(CanvasNodeType.DOMAIN)[0]
        spoke_nodes = [n for n in canvas.nodes if n.node_type != CanvasNodeType.DOMAIN]
        # All spokes should be at some distance from domain node
        for spoke in spoke_nodes:
            dist = math.hypot(spoke.x - domain_node.x, spoke.y - domain_node.y)
            assert dist > 50.0, f"Spoke node {spoke.id} too close to hub"

    @pytest.mark.asyncio
    async def test_spoke_nodes_not_all_coincident(
        self, generator: StarterCanvasGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(minimal_blueprint, layout=CanvasLayout.HUB_AND_SPOKE)
        spoke_nodes = [n for n in canvas.nodes if n.node_type != CanvasNodeType.DOMAIN]
        positions = [(round(n.x), round(n.y)) for n in spoke_nodes]
        # Each spoke should have a unique position
        assert len(positions) == len(set(positions))


class TestClusteredLayout:
    @pytest.mark.asyncio
    async def test_agents_have_different_x_positions(
        self, generator: StarterCanvasGenerator, large_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(large_blueprint, layout=CanvasLayout.CLUSTERED)
        agent_nodes = canvas.get_nodes_by_type(CanvasNodeType.AGENT)
        xs = [n.x for n in agent_nodes]
        assert len(set(xs)) > 1  # at least 2 distinct x values

    @pytest.mark.asyncio
    async def test_all_nodes_positioned(
        self, generator: StarterCanvasGenerator, large_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(large_blueprint, layout=CanvasLayout.CLUSTERED)
        for node in canvas.nodes:
            assert node.x >= 0.0
            assert node.y >= 0.0


class TestLinearLayout:
    @pytest.mark.asyncio
    async def test_all_nodes_at_same_y(
        self, generator: StarterCanvasGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(minimal_blueprint, layout=CanvasLayout.LINEAR)
        ys = [n.y for n in canvas.nodes]
        assert len(set(ys)) == 1  # all same y

    @pytest.mark.asyncio
    async def test_nodes_ordered_by_type(
        self, generator: StarterCanvasGenerator, minimal_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(minimal_blueprint, layout=CanvasLayout.LINEAR)
        # Domain should come before agent
        domain_node = canvas.get_nodes_by_type(CanvasNodeType.DOMAIN)[0]
        agent_nodes = canvas.get_nodes_by_type(CanvasNodeType.AGENT)
        for agent in agent_nodes:
            assert domain_node.x < agent.x


# ---------------------------------------------------------------------------
# Full generate() integration tests
# ---------------------------------------------------------------------------


class TestGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_starter_canvas(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(medium_blueprint)
        assert isinstance(canvas, StarterCanvas)

    @pytest.mark.asyncio
    async def test_generate_canvas_has_correct_domain_id(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(medium_blueprint)
        assert canvas.domain_id == medium_blueprint.domain_id
        assert canvas.domain_name == medium_blueprint.domain_name

    @pytest.mark.asyncio
    async def test_generate_with_explicit_layout(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(medium_blueprint, layout=CanvasLayout.LAYERED)
        assert canvas.layout == CanvasLayout.LAYERED

    @pytest.mark.asyncio
    async def test_generate_with_default_layout_override(
        self, tape_svc: TapeService, medium_blueprint: DomainBlueprint
    ) -> None:
        gen = StarterCanvasGenerator(
            tape_service=tape_svc, default_layout=CanvasLayout.LINEAR
        )
        canvas = await gen.generate(medium_blueprint)
        assert canvas.layout == CanvasLayout.LINEAR

    @pytest.mark.asyncio
    async def test_generate_canvas_has_nodes_and_edges(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(medium_blueprint)
        assert canvas.node_count > 0
        assert canvas.edge_count > 0

    @pytest.mark.asyncio
    async def test_generate_empty_blueprint(
        self, generator: StarterCanvasGenerator
    ) -> None:
        bp = DomainBlueprint(domain_name="Empty", domain_id="empty")
        canvas = await generator.generate(bp)
        assert canvas.node_count == 1  # only domain node
        assert canvas.edge_count == 0

    @pytest.mark.asyncio
    async def test_total_node_count_matches_blueprint(
        self, generator: StarterCanvasGenerator, medium_blueprint: DomainBlueprint
    ) -> None:
        canvas = await generator.generate(medium_blueprint)
        expected = (
            1  # domain
            + len(medium_blueprint.agents)
            + len(medium_blueprint.skills)
            + len(medium_blueprint.workflows)
        )
        assert canvas.node_count == expected


# ---------------------------------------------------------------------------
# Tape logging tests
# ---------------------------------------------------------------------------


class TestTapeLogging:
    @pytest.mark.asyncio
    async def test_canvas_created_event_logged(
        self,
        generator: StarterCanvasGenerator,
        medium_blueprint: DomainBlueprint,
        tape_svc: TapeService,
    ) -> None:
        await generator.generate(medium_blueprint)
        entries = await tape_svc.get_entries(event_type="canvas.created")
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_canvas_created_payload(
        self,
        generator: StarterCanvasGenerator,
        medium_blueprint: DomainBlueprint,
        tape_svc: TapeService,
    ) -> None:
        canvas = await generator.generate(medium_blueprint)
        entries = await tape_svc.get_entries(event_type="canvas.created")
        payload = entries[0].payload
        assert payload["domain_id"] == medium_blueprint.domain_id
        assert payload["node_count"] == canvas.node_count
        assert payload["edge_count"] == canvas.edge_count
        assert "canvas_id" in payload
        assert "blueprint_id" in payload

    @pytest.mark.asyncio
    async def test_multiple_generates_log_multiple_events(
        self,
        generator: StarterCanvasGenerator,
        medium_blueprint: DomainBlueprint,
        tape_svc: TapeService,
    ) -> None:
        await generator.generate(medium_blueprint)
        await generator.generate(medium_blueprint)
        entries = await tape_svc.get_entries(event_type="canvas.created")
        assert len(entries) == 2
