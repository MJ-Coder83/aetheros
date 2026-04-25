"""Domain Canvas — Data models.

Defines the core data models for the Domain Canvas system:

- ``CanvasNodeType``   — semantic type of a visual node
- ``CanvasEdgeType``   — semantic type of a directed edge
- ``CanvasViewMode``   — Visual vs. Folder view toggle
- ``CanvasLayout``     — auto-layout strategy enum
- ``CanvasNode``       — a single positioned node on the canvas
- ``CanvasEdge``       — a directed edge between two nodes
- ``Canvas``           — the complete canvas (nodes + edges + metadata)
- ``CanvasOperation``  — a single mutation applied to the canvas
- ``CanvasDiff``       — diff between two canvas states

These models are intentionally decoupled from ``packages.domain.starter_canvas``
(which remains for backward compatibility) and provide the richer model needed
by the full Domain Canvas system.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CanvasNodeType(StrEnum):
    """Semantic type of a canvas node."""

    # Domain-level
    DOMAIN = "domain"
    # Agents
    AGENT = "agent"
    # Skills / capabilities
    SKILL = "skill"
    # Workflows / pipelines
    WORKFLOW = "workflow"
    # Template documents
    TEMPLATE = "template"
    # External data sources
    DATA_SOURCE = "data_source"
    # Browser / web preview node (Agent 2)
    BROWSER = "browser"
    # Terminal / TUI node (Agent 3)
    TERMINAL = "terminal"
    # Generic / custom node
    CUSTOM = "custom"


class CanvasEdgeType(StrEnum):
    """Semantic type of a directed canvas edge."""

    CONTAINS = "contains"  # domain -> agent / skill
    USES = "uses"  # agent -> skill
    EXECUTES = "executes"  # workflow -> agent
    DEPENDS_ON = "depends_on"  # workflow -> skill / data source
    TRIGGERS = "triggers"  # event-driven connection
    DATA_FLOW = "data_flow"  # data-passing connection
    CUSTOM = "custom"


class CanvasViewMode(StrEnum):
    """Current view mode of the canvas — visual graph or folder tree."""

    VISUAL = "visual"
    FOLDER = "folder"


class CanvasLayout(StrEnum):
    """Auto-layout strategy for the canvas."""

    LAYERED = "layered"  # Left-to-right columns by node type
    HUB_AND_SPOKE = "hub_and_spoke"  # Domain at centre, others radiate
    CLUSTERED = "clustered"  # Agents + owned skills in clusters
    LINEAR = "linear"  # All nodes in a single row
    SMART = "smart"  # Heuristic — picks the best of the above


class CanvasOperationType(StrEnum):
    """Type of a single canvas mutation."""

    ADD_NODE = "add_node"
    REMOVE_NODE = "remove_node"
    MOVE_NODE = "move_node"
    UPDATE_NODE = "update_node"
    ADD_EDGE = "add_edge"
    REMOVE_EDGE = "remove_edge"
    UPDATE_EDGE = "update_edge"
    CHANGE_LAYOUT = "change_layout"
    CHANGE_VIEW_MODE = "change_view_mode"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class CanvasNode(BaseModel):
    """A single positioned node on the canvas.

    ``x`` and ``y`` are canvas coordinates in pixels (origin top-left).
    ``metadata`` carries display hints that the frontend renderer uses
    to style the node (colour, icon, description, etc.).
    """

    id: str
    node_type: CanvasNodeType
    label: str
    x: float = 0.0
    y: float = 0.0
    width: float = 180.0
    height: float = 60.0
    # Folder-tree path this node corresponds to (e.g. "Legal_Research/agents/analyst")
    folder_path: str = ""
    # Whether this node is currently selected in the UI
    selected: bool = False
    # Whether this node is locked (cannot be moved/deleted)
    locked: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class CanvasEdge(BaseModel):
    """A directed edge between two canvas nodes."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    source: str  # CanvasNode.id
    target: str  # CanvasNode.id
    edge_type: CanvasEdgeType = CanvasEdgeType.CONTAINS
    label: str = ""
    animated: bool = False
    # Routing waypoints [[x1,y1], [x2,y2], ...] — empty = straight line
    waypoints: list[list[float]] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class Canvas(BaseModel):
    """The complete Domain Canvas — nodes, edges, metadata, and view state.

    The canvas holds the visual representation of a domain.  It is always
    kept in sync with the canonical ``FolderTree`` stored by the
    ``FolderTreeService``.
    """

    id: UUID = Field(default_factory=uuid4)
    domain_id: str
    domain_name: str
    layout: CanvasLayout = CanvasLayout.SMART
    view_mode: CanvasViewMode = CanvasViewMode.VISUAL
    nodes: list[CanvasNode] = Field(default_factory=list)
    edges: list[CanvasEdge] = Field(default_factory=list)
    # Canvas viewport state
    viewport_x: float = 0.0
    viewport_y: float = 0.0
    viewport_zoom: float = 1.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

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
        """Return all nodes of the given type."""
        return [n for n in self.nodes if n.node_type == node_type]

    def get_edges_from(self, node_id: str) -> list[CanvasEdge]:
        """Return all edges originating from the given node."""
        return [e for e in self.edges if e.source == node_id]

    def get_edges_to(self, node_id: str) -> list[CanvasEdge]:
        """Return all edges pointing to the given node."""
        return [e for e in self.edges if e.target == node_id]

    def get_edge(self, edge_id: str) -> CanvasEdge | None:
        """Return the edge with the given ID, or None."""
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None


class CanvasOperation(BaseModel):
    """A single mutation applied to a canvas — used for audit logging and undo/redo."""

    id: UUID = Field(default_factory=uuid4)
    canvas_id: UUID
    op_type: CanvasOperationType
    # Serialised before/after state for undo/redo (node or edge dict, or layout str)
    before: dict[str, object] = Field(default_factory=dict)
    after: dict[str, object] = Field(default_factory=dict)
    description: str = ""
    applied_by: str = "system"
    applied_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CanvasDiff(BaseModel):
    """Diff between two canvas states — used for sync and conflict resolution."""

    canvas_id: UUID
    from_version: int
    to_version: int
    added_nodes: list[CanvasNode] = Field(default_factory=list)
    removed_node_ids: list[str] = Field(default_factory=list)
    moved_nodes: list[CanvasNode] = Field(default_factory=list)
    added_edges: list[CanvasEdge] = Field(default_factory=list)
    removed_edge_ids: list[str] = Field(default_factory=list)
    summary: str = ""


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CanvasError(Exception):
    """Base exception for canvas operations."""


class CanvasNotFoundError(CanvasError):
    """Raised when a requested canvas does not exist."""


class NodeNotFoundError(CanvasError):
    """Raised when a requested node does not exist on the canvas."""


class EdgeNotFoundError(CanvasError):
    """Raised when a requested edge does not exist on the canvas."""


class NodeAlreadyExistsError(CanvasError):
    """Raised when trying to add a node that already exists."""


class InvalidEdgeError(CanvasError):
    """Raised when an edge references non-existent nodes."""
