"""Starter Canvas Generation — visual canvas from a DomainBlueprint.

When a domain is created with the "Domain + Starter Canvas" option, this module
produces a ready-to-use visual canvas with connected nodes, sensible auto-layout,
and correct edge topology — no manual arrangement needed.

Layout strategies
-----------------
``LAYERED``
    Columns of nodes arranged left-to-right by role layer:
    Domain → Skills → Agents → Workflows.  Edges flow left-to-right.
    Best for domains with clear separation between skills and agents.

``HUB_AND_SPOKE``
    Domain node at the centre with agents and skills radiating outward in a
    circular arrangement.  Ideal for small domains (≤ 6 agents/skills) where
    the domain node is the focal point.

``CLUSTERED``
    Agents and their associated skills are grouped into visual clusters.
    Workflow nodes are placed below their owning agent cluster.
    Best for larger domains where clear agent→skill ownership matters.

``LINEAR``
    All nodes in a single horizontal row, ordered by type.  Simplest layout
    for quick inspection and very small domains.

Architecture::

    StarterCanvasGenerator
    ├── generate()               — Main entry point: blueprint → StarterCanvas
    ├── _choose_layout()         — Heuristic layout selection based on blueprint size
    ├── _build_nodes()           — Create CanvasNode objects for every blueprint item
    ├── _build_edges()           — Wire up edges between related nodes
    ├── _apply_layered_layout()  — Compute (x, y) positions for LAYERED strategy
    ├── _apply_hub_spoke_layout()— Compute positions for HUB_AND_SPOKE strategy
    ├── _apply_clustered_layout()— Compute positions for CLUSTERED strategy
    └── _apply_linear_layout()   — Compute positions for LINEAR strategy

Usage::

    from packages.domain.starter_canvas import StarterCanvasGenerator, CanvasLayout
    from packages.prime.domain_creation import DomainBlueprint

    blueprint = DomainBlueprint(domain_name="Legal Research", ...)
    generator = StarterCanvasGenerator(tape_service=tape_svc)
    canvas    = await generator.generate(blueprint, layout=CanvasLayout.LAYERED)

    # canvas.nodes  — list[CanvasNode]  (id, type, label, x, y, metadata)
    # canvas.edges  — list[CanvasEdge]  (id, source, target, edge_type)
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.tape.service import TapeService

if TYPE_CHECKING:
    from packages.prime.domain_creation import DomainBlueprint


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CanvasNodeType(StrEnum):
    """Visual node types on the canvas."""

    DOMAIN = "domain"
    AGENT = "agent"
    SKILL = "skill"
    WORKFLOW = "workflow"
    TEMPLATE = "template"
    DATA_SOURCE = "data_source"


class CanvasLayout(StrEnum):
    """Auto-layout strategy for the starter canvas."""

    LAYERED = "layered"
    HUB_AND_SPOKE = "hub_and_spoke"
    CLUSTERED = "clustered"
    LINEAR = "linear"


class CanvasEdgeType(StrEnum):
    """Semantic type of a canvas edge."""

    CONTAINS = "contains"       # domain → agent, domain → skill
    USES = "uses"               # agent → skill
    EXECUTES = "executes"       # workflow → agent
    DEPENDS_ON = "depends_on"   # workflow → skill


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class CanvasNode(BaseModel):
    """A single node on the starter canvas.

    ``x`` and ``y`` are canvas coordinates in pixels (origin top-left).
    ``metadata`` carries display hints (colour, icon, description) that
    the frontend Canvas renderer uses to style the node.
    """

    id: str
    node_type: CanvasNodeType
    label: str
    x: float = 0.0
    y: float = 0.0
    width: float = 180.0
    height: float = 60.0
    metadata: dict[str, object] = Field(default_factory=dict)


class CanvasEdge(BaseModel):
    """A directed edge between two nodes on the canvas."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str          # CanvasNode.id
    target: str          # CanvasNode.id
    edge_type: CanvasEdgeType = CanvasEdgeType.CONTAINS
    label: str = ""
    animated: bool = False


class StarterCanvas(BaseModel):
    """Complete starter canvas for a domain.

    Produced by ``StarterCanvasGenerator.generate()``.  The canvas is
    immediately renderable by the InkosAI frontend — all nodes have valid
    positions and all edges reference existing node IDs.
    """

    id: UUID = Field(default_factory=uuid4)
    domain_id: str
    domain_name: str
    layout: CanvasLayout
    nodes: list[CanvasNode] = Field(default_factory=list)
    edges: list[CanvasEdge] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def get_node(self, node_id: str) -> CanvasNode | None:
        """Return the node with the given ID, or None."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_nodes_by_type(self, node_type: CanvasNodeType) -> list[CanvasNode]:
        """Return all nodes of a given type."""
        return [n for n in self.nodes if n.node_type == node_type]


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

# Horizontal and vertical spacing between nodes (pixels)
_H_GAP = 260   # gap between columns in LAYERED / between items in LINEAR
_V_GAP = 100   # gap between rows within a column
_CLUSTER_GAP = 320  # horizontal gap between clusters in CLUSTERED

# Colour palette per node type (CSS hex strings, passed as metadata hints)
_NODE_COLOURS: dict[CanvasNodeType, str] = {
    CanvasNodeType.DOMAIN: "#6366f1",       # indigo
    CanvasNodeType.AGENT: "#06b6d4",        # cyan
    CanvasNodeType.SKILL: "#10b981",        # emerald
    CanvasNodeType.WORKFLOW: "#f59e0b",     # amber
    CanvasNodeType.TEMPLATE: "#8b5cf6",     # violet
    CanvasNodeType.DATA_SOURCE: "#64748b",  # slate
}

_NODE_ICONS: dict[CanvasNodeType, str] = {
    CanvasNodeType.DOMAIN: "globe",
    CanvasNodeType.AGENT: "bot",
    CanvasNodeType.SKILL: "zap",
    CanvasNodeType.WORKFLOW: "git-branch",
    CanvasNodeType.TEMPLATE: "file-text",
    CanvasNodeType.DATA_SOURCE: "database",
}


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class StarterCanvasGenerator:
    """Generate a visual starter canvas from a DomainBlueprint.

    The generator is stateless with respect to canvases — each call to
    ``generate()`` produces a fresh ``StarterCanvas``.  All canvas creation
    events are logged to the Tape under the ``canvas.*`` namespace.

    Parameters
    ----------
    tape_service:
        The shared Tape service used for audit logging.
    default_layout:
        Override the heuristic layout selection.  When ``None`` (default)
        the generator picks the best layout automatically.
    """

    def __init__(
        self,
        tape_service: TapeService,
        default_layout: CanvasLayout | None = None,
    ) -> None:
        self._tape = tape_service
        self._default_layout = default_layout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        blueprint: DomainBlueprint,
        layout: CanvasLayout | None = None,
    ) -> StarterCanvas:
        """Generate a ``StarterCanvas`` from a ``DomainBlueprint``.

        Parameters
        ----------
        blueprint:
            The domain blueprint to visualise.
        layout:
            Layout strategy override.  Falls back to ``self._default_layout``
            and then to heuristic selection based on blueprint size.

        Returns
        -------
        StarterCanvas
            Fully positioned canvas with nodes and edges.
        """
        chosen_layout = layout or self._default_layout or self._choose_layout(blueprint)

        nodes = self._build_nodes(blueprint)
        edges = self._build_edges(blueprint, nodes)

        # Apply layout — assigns (x, y) to every node in-place
        self._apply_layout(chosen_layout, nodes, blueprint)

        canvas = StarterCanvas(
            domain_id=blueprint.domain_id,
            domain_name=blueprint.domain_name,
            layout=chosen_layout,
            nodes=nodes,
            edges=edges,
        )

        await self._log_canvas_created(canvas, blueprint)
        return canvas

    # ------------------------------------------------------------------
    # Layout selection
    # ------------------------------------------------------------------

    def _choose_layout(self, blueprint: DomainBlueprint) -> CanvasLayout:
        """Heuristically select the best layout for the given blueprint.

        Rules (in priority order):
        1. Very small domain (≤ 3 agents + skills total) → LINEAR
        2. Small domain (≤ 6 total, 1 clear hub agent) → HUB_AND_SPOKE
        3. ≥ 3 agents each with ≥ 2 dedicated skills → CLUSTERED
        4. Default → LAYERED
        """
        total = len(blueprint.agents) + len(blueprint.skills)
        if total <= 3:
            return CanvasLayout.LINEAR
        if total <= 6:
            return CanvasLayout.HUB_AND_SPOKE
        # Check for clustered suitability: agents each owning skills
        agents_with_tools = sum(
            1 for a in blueprint.agents if len(a.tools) >= 2 or len(a.capabilities) >= 2
        )
        if agents_with_tools >= 3:
            return CanvasLayout.CLUSTERED
        return CanvasLayout.LAYERED

    # ------------------------------------------------------------------
    # Node and edge construction
    # ------------------------------------------------------------------

    def _build_nodes(self, blueprint: DomainBlueprint) -> list[CanvasNode]:
        """Create all canvas nodes from the blueprint."""
        nodes: list[CanvasNode] = []

        # Domain node (always present, always first)
        nodes.append(self._make_node(
            node_id=f"domain-{blueprint.domain_id}",
            node_type=CanvasNodeType.DOMAIN,
            label=blueprint.domain_name,
            description=blueprint.description,
        ))

        # Agent nodes
        for agent in blueprint.agents:
            nodes.append(self._make_node(
                node_id=f"agent-{agent.agent_id}",
                node_type=CanvasNodeType.AGENT,
                label=agent.name,
                description=agent.goal,
                extra={"role": agent.role, "capabilities": agent.capabilities},
            ))

        # Skill nodes
        for skill in blueprint.skills:
            nodes.append(self._make_node(
                node_id=f"skill-{skill.skill_id}",
                node_type=CanvasNodeType.SKILL,
                label=skill.name,
                description=skill.description,
                extra={"version": skill.version, "is_reused": skill.is_reused},
            ))

        # Workflow nodes
        for wf in blueprint.workflows:
            nodes.append(self._make_node(
                node_id=f"workflow-{wf.workflow_id}",
                node_type=CanvasNodeType.WORKFLOW,
                label=wf.name,
                description=wf.description,
                extra={"workflow_type": wf.workflow_type, "steps": wf.steps},
            ))

        return nodes

    def _make_node(
        self,
        node_id: str,
        node_type: CanvasNodeType,
        label: str,
        description: str = "",
        extra: dict[str, object] | None = None,
    ) -> CanvasNode:
        """Construct a single CanvasNode with display metadata."""
        metadata: dict[str, object] = {
            "colour": _NODE_COLOURS[node_type],
            "icon": _NODE_ICONS[node_type],
            "description": description,
        }
        if extra:
            metadata.update(extra)
        return CanvasNode(
            id=node_id,
            node_type=node_type,
            label=label,
            metadata=metadata,
        )

    def _build_edges(
        self,
        blueprint: DomainBlueprint,
        nodes: list[CanvasNode],
    ) -> list[CanvasEdge]:
        """Wire up edges between related nodes.

        Edge topology:
        - domain → every agent (CONTAINS)
        - domain → every skill not exclusively owned by an agent (CONTAINS)
        - workflow → each of its agents (EXECUTES)
        - workflow → skills named in its steps that match a skill node (DEPENDS_ON)
        - agent → skills that appear in agent.tools and exist as nodes (USES)
        """
        edges: list[CanvasEdge] = []
        node_ids = {n.id for n in nodes}
        domain_id = f"domain-{blueprint.domain_id}"

        # Build a set of skill IDs exclusively claimed by agents via tools
        agent_claimed_skills: set[str] = set()
        for agent in blueprint.agents:
            for tool in agent.tools:
                # Match tool name to skill by substring
                for skill in blueprint.skills:
                    if tool.lower() in skill.name.lower() or skill.skill_id.lower() in tool.lower():
                        agent_claimed_skills.add(f"skill-{skill.skill_id}")

        # domain → agents
        for agent in blueprint.agents:
            agent_node_id = f"agent-{agent.agent_id}"
            if agent_node_id in node_ids:
                edges.append(CanvasEdge(
                    source=domain_id,
                    target=agent_node_id,
                    edge_type=CanvasEdgeType.CONTAINS,
                ))

        # domain → unclaimed skills
        for skill in blueprint.skills:
            skill_node_id = f"skill-{skill.skill_id}"
            if skill_node_id not in agent_claimed_skills and skill_node_id in node_ids:
                edges.append(CanvasEdge(
                    source=domain_id,
                    target=skill_node_id,
                    edge_type=CanvasEdgeType.CONTAINS,
                ))

        # agent → claimed skills
        for agent in blueprint.agents:
            agent_node_id = f"agent-{agent.agent_id}"
            for tool in agent.tools:
                for skill in blueprint.skills:
                    skill_node_id = f"skill-{skill.skill_id}"
                    if (
                        tool.lower() in skill.name.lower()
                        or skill.skill_id.lower() in tool.lower()
                    ) and skill_node_id in node_ids:
                        edges.append(CanvasEdge(
                            source=agent_node_id,
                            target=skill_node_id,
                            edge_type=CanvasEdgeType.USES,
                            animated=True,
                        ))

        # workflow → agents
        for wf in blueprint.workflows:
            wf_node_id = f"workflow-{wf.workflow_id}"
            if wf_node_id not in node_ids:
                continue
            for agent_id_ref in wf.agent_ids:
                agent_node_id = f"agent-{agent_id_ref}"
                if agent_node_id in node_ids:
                    edges.append(CanvasEdge(
                        source=wf_node_id,
                        target=agent_node_id,
                        edge_type=CanvasEdgeType.EXECUTES,
                    ))

        return edges

    # ------------------------------------------------------------------
    # Layout application
    # ------------------------------------------------------------------

    def _apply_layout(
        self,
        layout: CanvasLayout,
        nodes: list[CanvasNode],
        blueprint: DomainBlueprint,
    ) -> None:
        """Dispatch to the correct layout algorithm (mutates nodes in-place)."""
        if layout == CanvasLayout.LAYERED:
            self._apply_layered_layout(nodes)
        elif layout == CanvasLayout.HUB_AND_SPOKE:
            self._apply_hub_spoke_layout(nodes)
        elif layout == CanvasLayout.CLUSTERED:
            self._apply_clustered_layout(nodes, blueprint)
        else:  # LINEAR
            self._apply_linear_layout(nodes)

    def _apply_layered_layout(self, nodes: list[CanvasNode]) -> None:
        """Left-to-right column layout: Domain | Skills | Agents | Workflows.

        Each column is vertically centred. Nodes within a column are evenly
        spaced with ``_V_GAP`` between them.
        """
        # Group by type in column order
        column_order: list[CanvasNodeType] = [
            CanvasNodeType.DOMAIN,
            CanvasNodeType.SKILL,
            CanvasNodeType.AGENT,
            CanvasNodeType.WORKFLOW,
            CanvasNodeType.TEMPLATE,
            CanvasNodeType.DATA_SOURCE,
        ]
        columns: dict[CanvasNodeType, list[CanvasNode]] = {t: [] for t in column_order}
        for node in nodes:
            if node.node_type in columns:
                columns[node.node_type].append(node)

        x = 60.0
        for col_type in column_order:
            col_nodes = columns[col_type]
            if not col_nodes:
                continue
            y_start = 60.0
            # nodes are evenly spaced within each column
            for i, node in enumerate(col_nodes):
                node.x = x
                node.y = y_start + i * (node.height + _V_GAP)
            x += _H_GAP

    def _apply_hub_spoke_layout(self, nodes: list[CanvasNode]) -> None:
        """Domain at centre; all other nodes radiate outward in a circle.

        The radius scales with the number of non-domain nodes.
        """
        spoke_nodes = [n for n in nodes if n.node_type != CanvasNodeType.DOMAIN]
        domain_nodes = [n for n in nodes if n.node_type == CanvasNodeType.DOMAIN]

        # Place domain node at centre
        cx, cy = 500.0, 400.0
        for d in domain_nodes:
            d.x = cx
            d.y = cy

        if not spoke_nodes:
            return

        count = len(spoke_nodes)
        radius = max(220.0, count * 50.0)
        angle_step = 2 * math.pi / count
        # Start from top (-pi/2) so the first node is at 12 o'clock
        start_angle = -math.pi / 2

        for i, node in enumerate(spoke_nodes):
            angle = start_angle + i * angle_step
            node.x = cx + radius * math.cos(angle) - node.width / 2
            node.y = cy + radius * math.sin(angle) - node.height / 2

    def _apply_clustered_layout(
        self, nodes: list[CanvasNode], blueprint: DomainBlueprint
    ) -> None:
        """Group agents and their skills into visual clusters.

        Layout:
        - Domain node centred at the top
        - Each agent forms a cluster below with its skills fanned out
        - Workflows appear in a row at the bottom
        """
        by_id = {n.id: n for n in nodes}

        # Place domain node at top-centre
        domain_node_id = f"domain-{blueprint.domain_id}"
        num_agents = max(len(blueprint.agents), 1)
        canvas_width = num_agents * _CLUSTER_GAP
        if domain_node_id in by_id:
            by_id[domain_node_id].x = canvas_width / 2
            by_id[domain_node_id].y = 60.0

        # Build agent→skill mapping
        agent_skills: dict[str, list[str]] = {}
        claimed_skills: set[str] = set()
        for agent in blueprint.agents:
            skill_ids: list[str] = []
            for tool in agent.tools:
                for skill in blueprint.skills:
                    skill_node_id = f"skill-{skill.skill_id}"
                    if (
                        tool.lower() in skill.name.lower()
                        or skill.skill_id.lower() in tool.lower()
                    ):
                        skill_ids.append(skill_node_id)
                        claimed_skills.add(skill_node_id)
            agent_skills[f"agent-{agent.agent_id}"] = skill_ids

        # Place agent clusters
        agent_y = 220.0
        for col_idx, agent in enumerate(blueprint.agents):
            cluster_x = 60.0 + col_idx * _CLUSTER_GAP
            agent_node_id = f"agent-{agent.agent_id}"
            if agent_node_id in by_id:
                by_id[agent_node_id].x = cluster_x
                by_id[agent_node_id].y = agent_y

            # Place skills below their agent
            skill_ids = agent_skills.get(agent_node_id, [])
            for s_idx, skill_id in enumerate(skill_ids):
                if skill_id in by_id:
                    by_id[skill_id].x = cluster_x - 40 + s_idx * 120
                    by_id[skill_id].y = agent_y + 120

        # Place unclaimed skills in a row below domain
        unclaimed = [
            n for n in nodes
            if n.node_type == CanvasNodeType.SKILL and n.id not in claimed_skills
        ]
        for idx, skill_node in enumerate(unclaimed):
            skill_node.x = 60.0 + idx * (_H_GAP * 0.7)
            skill_node.y = agent_y - 100

        # Workflows at the bottom
        wf_y = agent_y + 260
        for wf_idx, wf in enumerate(blueprint.workflows):
            wf_node_id = f"workflow-{wf.workflow_id}"
            if wf_node_id in by_id:
                by_id[wf_node_id].x = 60.0 + wf_idx * _H_GAP
                by_id[wf_node_id].y = wf_y

    def _apply_linear_layout(self, nodes: list[CanvasNode]) -> None:
        """All nodes in a single horizontal row, ordered by type."""
        type_order: dict[CanvasNodeType, int] = {
            CanvasNodeType.DOMAIN: 0,
            CanvasNodeType.AGENT: 1,
            CanvasNodeType.SKILL: 2,
            CanvasNodeType.WORKFLOW: 3,
            CanvasNodeType.TEMPLATE: 4,
            CanvasNodeType.DATA_SOURCE: 5,
        }
        sorted_nodes = sorted(nodes, key=lambda n: type_order.get(n.node_type, 99))
        y = 300.0
        for i, node in enumerate(sorted_nodes):
            node.x = 60.0 + i * _H_GAP
            node.y = y

    # ------------------------------------------------------------------
    # Tape logging
    # ------------------------------------------------------------------

    async def _log_canvas_created(
        self,
        canvas: StarterCanvas,
        blueprint: DomainBlueprint,
    ) -> None:
        """Log a canvas.created event to the Tape."""
        await self._tape.log_event(
            event_type="canvas.created",
            agent_id="prime",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": canvas.domain_id,
                "domain_name": canvas.domain_name,
                "layout": canvas.layout,
                "node_count": canvas.node_count,
                "edge_count": canvas.edge_count,
                "blueprint_id": str(blueprint.id),
            },
        )
