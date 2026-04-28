"""Domain Canvas — Core engine.

Provides two primary classes:

``LayoutEngine``
    Stateless engine that computes (x, y) positions for all nodes on a
    ``Canvas`` using one of five strategies:

    - ``LAYERED``      — left-to-right columns ordered by node type
    - ``HUB_AND_SPOKE`` — domain node at centre; others radiate outward
    - ``CLUSTERED``    — agents + their owned skills grouped into clusters
    - ``LINEAR``       — all nodes in a single horizontal row
    - ``SMART``        — heuristic that selects the best of the above

``CanvasService``
    Stateful service that manages the lifecycle of canvases:

    - ``create_canvas()``         — create a new empty canvas
    - ``get_canvas()``            — retrieve a canvas by domain ID
    - ``add_node()``              — add a node (syncs to folder tree)
    - ``remove_node()``           — remove a node and its edges
    - ``move_node()``             — reposition a node
    - ``update_node()``           — update node metadata / label
    - ``add_edge()``              — add a directed edge
    - ``remove_edge()``           — remove an edge
    - ``apply_layout()``          — run a layout algorithm in-place
    - ``set_view_mode()``         — switch between Visual ↔ Folder view
    - ``sync_to_folder_tree()``   — push canvas changes → FolderTree
    - ``sync_from_folder_tree()`` — pull FolderTree changes → canvas
    - ``canvas_from_domain_blueprint()`` — bootstrap a canvas from a blueprint

All mutating operations are logged to the Tape under the ``canvas.*``
event namespace.

Architecture::

    CanvasService
    ├── _store: CanvasStore        (in-memory; Postgres-backed later)
    ├── _tape: TapeService
    ├── _folder_tree: FolderTreeService | None
    └── _layout_engine: LayoutEngine

    LayoutEngine
    ├── layout()                  — dispatch to strategy
    ├── _layered()
    ├── _hub_and_spoke()
    ├── _clustered()
    ├── _linear()
    └── _smart()                  — heuristic selection
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from packages.canvas.models import (
    Canvas,
    CanvasDiff,
    CanvasEdge,
    CanvasEdgeType,
    CanvasError,
    CanvasLayout,
    CanvasNode,
    CanvasNodeType,
    CanvasNotFoundError,
    CanvasOperation,
    CanvasOperationType,
    CanvasViewMode,
    EdgeNotFoundError,
    InvalidEdgeError,
    NodeAlreadyExistsError,
    NodeNotFoundError,
)
from packages.tape.service import TapeService

if TYPE_CHECKING:
    from packages.folder_tree import FolderTree, FolderTreeService
    from packages.prime.domain_creation import DomainBlueprint

__all__ = [
    "Canvas",
    "CanvasDiff",
    "CanvasEdge",
    "CanvasEdgeType",
    "CanvasError",
    "CanvasLayout",
    "CanvasNode",
    "CanvasNodeType",
    "CanvasNotFoundError",
    "CanvasOperation",
    "CanvasOperationType",
    "CanvasService",
    "CanvasStore",
    "CanvasViewMode",
    "EdgeNotFoundError",
    "InvalidEdgeError",
    "LayoutEngine",
    "NodeAlreadyExistsError",
    "NodeNotFoundError",
]


# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------

_H_GAP = 260  # horizontal gap between columns (LAYERED / LINEAR)
_V_GAP = 100  # vertical gap between rows within a column
_CLUSTER_GAP = 320  # horizontal gap between clusters (CLUSTERED)

# Colour palette per node type (CSS hex)
_NODE_COLOURS: dict[CanvasNodeType, str] = {
    CanvasNodeType.DOMAIN: "#6366f1",
    CanvasNodeType.AGENT: "#06b6d4",
    CanvasNodeType.SKILL: "#10b981",
    CanvasNodeType.WORKFLOW: "#f59e0b",
    CanvasNodeType.TEMPLATE: "#8b5cf6",
    CanvasNodeType.DATA_SOURCE: "#64748b",
    CanvasNodeType.BROWSER: "#3b82f6",
    CanvasNodeType.TERMINAL: "#22c55e",
    CanvasNodeType.LIVE_TERMINAL: "#16a34a",  # Darker green
    CanvasNodeType.TUI_DESIGNER: "#84cc16",  # Lime green
    CanvasNodeType.FILE_BROWSER: "#f97316",
    CanvasNodeType.MARKDOWN_VIEWER: "#ec4899",
    CanvasNodeType.CUSTOM: "#94a3b8",
}

_NODE_ICONS: dict[CanvasNodeType, str] = {
    CanvasNodeType.DOMAIN: "globe",
    CanvasNodeType.AGENT: "bot",
    CanvasNodeType.SKILL: "zap",
    CanvasNodeType.WORKFLOW: "git-branch",
    CanvasNodeType.TEMPLATE: "file-text",
    CanvasNodeType.DATA_SOURCE: "database",
    CanvasNodeType.BROWSER: "monitor",
    CanvasNodeType.TERMINAL: "terminal",
    CanvasNodeType.LIVE_TERMINAL: "terminal-square",
    CanvasNodeType.TUI_DESIGNER: "layout-grid",
    CanvasNodeType.FILE_BROWSER: "folder",
    CanvasNodeType.MARKDOWN_VIEWER: "file-text",
    CanvasNodeType.CUSTOM: "box",
}

# Column ordering for LAYERED layout
_LAYERED_ORDER: list[CanvasNodeType] = [
    CanvasNodeType.DOMAIN,
    CanvasNodeType.DATA_SOURCE,
    CanvasNodeType.SKILL,
    CanvasNodeType.AGENT,
    CanvasNodeType.WORKFLOW,
    CanvasNodeType.TEMPLATE,
    CanvasNodeType.BROWSER,
    CanvasNodeType.TERMINAL,
    CanvasNodeType.FILE_BROWSER,
    CanvasNodeType.MARKDOWN_VIEWER,
    CanvasNodeType.CUSTOM,
]

# Type ordering for LINEAR layout
_LINEAR_ORDER: dict[CanvasNodeType, int] = {t: i for i, t in enumerate(_LAYERED_ORDER)}


# ---------------------------------------------------------------------------
# LayoutEngine
# ---------------------------------------------------------------------------


class LayoutEngine:
    """Stateless layout engine.  Mutates node (x, y) positions in-place.

    Parameters
    ----------
    None — the engine is fully stateless.

    Usage::

        engine = LayoutEngine()
        engine.layout(canvas)            # uses canvas.layout strategy
        engine.layout(canvas, CanvasLayout.LAYERED)  # explicit strategy
    """

    def layout(
        self,
        canvas: Canvas,
        strategy: CanvasLayout | None = None,
    ) -> None:
        """Apply a layout strategy to the canvas, mutating node positions.

        Parameters
        ----------
        canvas:
            The canvas to lay out.  All nodes are mutated in-place.
        strategy:
            Layout strategy to use.  Falls back to ``canvas.layout`` (and
            resolves ``SMART`` automatically).
        """
        chosen = strategy or canvas.layout
        if chosen == CanvasLayout.SMART:
            chosen = self._choose_smart(canvas.nodes)

        if chosen == CanvasLayout.LAYERED:
            self._layered(canvas.nodes)
        elif chosen == CanvasLayout.HUB_AND_SPOKE:
            self._hub_and_spoke(canvas.nodes)
        elif chosen == CanvasLayout.CLUSTERED:
            self._clustered(canvas.nodes, canvas.edges)
        else:  # LINEAR (and fallback)
            self._linear(canvas.nodes)

    # ------------------------------------------------------------------
    # Smart heuristic
    # ------------------------------------------------------------------

    def _choose_smart(self, nodes: list[CanvasNode]) -> CanvasLayout:
        """Heuristically pick the best layout strategy.

        Rules (in priority order):
        1. Total non-domain nodes <= 3  → LINEAR
        2. Total non-domain nodes <= 6  → HUB_AND_SPOKE
        3. >= 3 agents each with >= 2 connected skills  → CLUSTERED
        4. Default  → LAYERED
        """
        non_domain = [n for n in nodes if n.node_type != CanvasNodeType.DOMAIN]
        total = len(non_domain)

        if total <= 3:
            return CanvasLayout.LINEAR
        if total <= 6:
            return CanvasLayout.HUB_AND_SPOKE

        agents = [n for n in nodes if n.node_type == CanvasNodeType.AGENT]
        if len(agents) >= 3:
            return CanvasLayout.CLUSTERED

        return CanvasLayout.LAYERED

    # ------------------------------------------------------------------
    # LAYERED
    # ------------------------------------------------------------------

    def _layered(self, nodes: list[CanvasNode]) -> None:
        """Left-to-right columns, one column per node type."""
        columns: dict[CanvasNodeType, list[CanvasNode]] = {t: [] for t in _LAYERED_ORDER}
        for node in nodes:
            bucket = columns.get(node.node_type)
            if bucket is not None:
                bucket.append(node)
            else:
                columns.setdefault(CanvasNodeType.CUSTOM, []).append(node)

        x = 60.0
        for col_type in _LAYERED_ORDER:
            col_nodes = columns.get(col_type, [])
            if not col_nodes:
                continue
            for i, node in enumerate(col_nodes):
                node.x = x
                node.y = 60.0 + i * (node.height + _V_GAP)
            x += _H_GAP

    # ------------------------------------------------------------------
    # HUB_AND_SPOKE
    # ------------------------------------------------------------------

    def _hub_and_spoke(self, nodes: list[CanvasNode]) -> None:
        """Domain node at centre; all others radiate outward in a circle."""
        spoke_nodes = [n for n in nodes if n.node_type != CanvasNodeType.DOMAIN]
        domain_nodes = [n for n in nodes if n.node_type == CanvasNodeType.DOMAIN]

        cx, cy = 500.0, 400.0
        for d in domain_nodes:
            d.x = cx - d.width / 2
            d.y = cy - d.height / 2

        if not spoke_nodes:
            return

        count = len(spoke_nodes)
        radius = max(220.0, count * 50.0)
        angle_step = 2 * math.pi / count
        start_angle = -math.pi / 2  # first node at 12 o'clock

        for i, node in enumerate(spoke_nodes):
            angle = start_angle + i * angle_step
            node.x = cx + radius * math.cos(angle) - node.width / 2
            node.y = cy + radius * math.sin(angle) - node.height / 2

    # ------------------------------------------------------------------
    # CLUSTERED
    # ------------------------------------------------------------------

    def _clustered(
        self,
        nodes: list[CanvasNode],
        edges: list[CanvasEdge],
    ) -> None:
        """Agents + their owned skills in vertical clusters; workflows at bottom."""
        by_id = {n.id: n for n in nodes}

        # Find domain node
        domain_nodes = [n for n in nodes if n.node_type == CanvasNodeType.DOMAIN]
        agents = [n for n in nodes if n.node_type == CanvasNodeType.AGENT]
        num_agents = max(len(agents), 1)
        canvas_width = num_agents * _CLUSTER_GAP

        for d in domain_nodes:
            d.x = canvas_width / 2 - d.width / 2
            d.y = 60.0

        # Build agent → owned skills map via USES edges
        agent_skills: dict[str, list[str]] = {}
        claimed_skills: set[str] = set()
        for edge in edges:
            if edge.edge_type == CanvasEdgeType.USES:
                agent_skills.setdefault(edge.source, []).append(edge.target)
                claimed_skills.add(edge.target)

        agent_y = 220.0
        for col_idx, agent_node in enumerate(agents):
            cluster_x = 60.0 + col_idx * _CLUSTER_GAP
            agent_node.x = cluster_x
            agent_node.y = agent_y

            # Skills below agent
            skill_ids = agent_skills.get(agent_node.id, [])
            for s_idx, skill_id in enumerate(skill_ids):
                skill_node = by_id.get(skill_id)
                if skill_node:
                    skill_node.x = cluster_x - 40 + s_idx * 120
                    skill_node.y = agent_y + 120

        # Unclaimed skills / data sources below domain
        unclaimed = [
            n
            for n in nodes
            if n.node_type in (CanvasNodeType.SKILL, CanvasNodeType.DATA_SOURCE)
            and n.id not in claimed_skills
        ]
        for idx, node in enumerate(unclaimed):
            node.x = 60.0 + idx * (_H_GAP * 0.7)
            node.y = agent_y - 100

        # Workflows at the bottom
        workflows = [n for n in nodes if n.node_type == CanvasNodeType.WORKFLOW]
        wf_y = agent_y + 260
        for wf_idx, wf_node in enumerate(workflows):
            wf_node.x = 60.0 + wf_idx * _H_GAP
            wf_node.y = wf_y

        # Browser / terminal nodes in their own row
        special = [
            n
            for n in nodes
            if n.node_type
            in (CanvasNodeType.BROWSER, CanvasNodeType.TERMINAL, CanvasNodeType.CUSTOM)
        ]
        sp_y = wf_y + 180
        for sp_idx, sp_node in enumerate(special):
            sp_node.x = 60.0 + sp_idx * _H_GAP
            sp_node.y = sp_y

    # ------------------------------------------------------------------
    # LINEAR
    # ------------------------------------------------------------------

    def _linear(self, nodes: list[CanvasNode]) -> None:
        """All nodes in a single horizontal row, ordered by type."""
        sorted_nodes = sorted(
            nodes,
            key=lambda n: _LINEAR_ORDER.get(n.node_type, 99),
        )
        y = 300.0
        for i, node in enumerate(sorted_nodes):
            node.x = 60.0 + i * _H_GAP
            node.y = y


# ---------------------------------------------------------------------------
# CanvasStore — PostgreSQL-backed store
# ---------------------------------------------------------------------------


class CanvasStore:
    """PostgreSQL-backed store for Canvas objects.

    Keyed by domain_id (one canvas per domain).
    """

    def __init__(self) -> None:
        self._cache: dict[str, Canvas] = {}  # Runtime cache

    async def add(self, canvas: Canvas) -> None:
        """Persist a new canvas to the database."""
        from sqlalchemy import select

        from services.api.database import CanvasEdgeORM, CanvasNodeORM, CanvasORM, async_session

        async with async_session() as session, session.begin():
            # Check if canvas already exists
            result = await session.execute(
                select(CanvasORM).where(CanvasORM.domain_id == canvas.domain_id)
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing canvas
                existing.domain_name = canvas.domain_name
                existing.layout = canvas.layout.value
                existing.view_mode = canvas.view_mode.value
                existing.viewport_x = canvas.viewport_x
                existing.viewport_y = canvas.viewport_y
                existing.viewport_zoom = canvas.viewport_zoom
                existing.updated_at = datetime.now(UTC)

                # Delete existing nodes and edges
                await session.execute(
                    select(CanvasNodeORM).where(CanvasNodeORM.canvas_id == str(canvas.id))
                )
                await session.execute(
                    select(CanvasEdgeORM).where(CanvasEdgeORM.canvas_id == str(canvas.id))
                )

            # Create new canvas or use existing
            if not existing:
                canvas_orm = CanvasORM(
                    id=str(canvas.id),
                    domain_id=canvas.domain_id,
                    domain_name=canvas.domain_name,
                    layout=canvas.layout.value,
                    view_mode=canvas.view_mode.value,
                    viewport_x=canvas.viewport_x,
                    viewport_y=canvas.viewport_y,
                    viewport_zoom=canvas.viewport_zoom,
                    created_at=canvas.created_at,
                    updated_at=canvas.updated_at,
                )
                session.add(canvas_orm)
            else:
                canvas_orm = existing

            # Add nodes
            for node in canvas.nodes:
                node_orm = CanvasNodeORM(
                    id=node.id,
                    canvas_id=str(canvas.id),
                    node_type=node.node_type.value,
                    label=node.label,
                    x=node.x,
                    y=node.y,
                    width=node.width,
                    height=node.height,
                    folder_path=node.folder_path,
                    selected=node.selected,
                    locked=node.locked,
                    meta_data=node.metadata,
                )
                session.add(node_orm)

            # Add edges
            for edge in canvas.edges:
                edge_orm = CanvasEdgeORM(
                    id=edge.id if edge.id else str(uuid4()),
                    canvas_id=str(canvas.id),
                    source=edge.source,
                    target=edge.target,
                    edge_type=edge.edge_type.value,
                    label=edge.label,
                    animated=edge.animated,
                    waypoints=edge.waypoints,
                    meta_data=edge.metadata,
                )
                session.add(edge_orm)

        # Update cache
        self._cache[canvas.domain_id] = canvas

    async def get(self, domain_id: str) -> Canvas | None:
        """Retrieve a canvas by domain ID from the database."""
        # Check cache first
        if domain_id in self._cache:
            return self._cache[domain_id]

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from services.api.database import CanvasORM, async_session

        async with async_session() as session:
            result = await session.execute(
                select(CanvasORM)
                .where(CanvasORM.domain_id == domain_id)
                .options(selectinload(CanvasORM.nodes))
                .options(selectinload(CanvasORM.edges))
            )
            orm = result.scalar_one_or_none()

            if orm is None:
                return None

            # Convert ORM to Pydantic model
            canvas = Canvas(
                id=UUID(orm.id),
                domain_id=orm.domain_id,
                domain_name=orm.domain_name,
                layout=CanvasLayout(orm.layout),
                view_mode=CanvasViewMode(orm.view_mode),
                viewport_x=orm.viewport_x,
                viewport_y=orm.viewport_y,
                viewport_zoom=orm.viewport_zoom,
                created_at=orm.created_at,
                updated_at=orm.updated_at,
            )

            # Convert nodes
            for node_orm in orm.nodes:
                node = CanvasNode(
                    id=node_orm.id,
                    node_type=CanvasNodeType(node_orm.node_type),
                    label=node_orm.label,
                    x=node_orm.x,
                    y=node_orm.y,
                    width=node_orm.width,
                    height=node_orm.height,
                    folder_path=node_orm.folder_path,
                    selected=node_orm.selected,
                    locked=node_orm.locked,
                    metadata=node_orm.meta_data or {},
                )
                canvas.nodes.append(node)

            # Convert edges
            for edge_orm in orm.edges:
                edge = CanvasEdge(
                    id=edge_orm.id,
                    source=edge_orm.source,
                    target=edge_orm.target,
                    edge_type=CanvasEdgeType(edge_orm.edge_type),
                    label=edge_orm.label,
                    animated=edge_orm.animated,
                    waypoints=edge_orm.waypoints or [],
                    metadata=edge_orm.meta_data or {},
                )
                canvas.edges.append(edge)

            self._cache[domain_id] = canvas
            return canvas

    async def update(self, canvas: Canvas) -> None:
        """Update an existing canvas in the database."""
        await self.add(canvas)  # add handles upsert

    async def remove(self, domain_id: str) -> Canvas | None:
        """Remove a canvas from the database."""
        from sqlalchemy import select

        from services.api.database import CanvasORM, async_session

        canvas = await self.get(domain_id)
        if canvas is None:
            return None

        async with async_session() as session, session.begin():
            result = await session.execute(
                select(CanvasORM).where(CanvasORM.domain_id == domain_id)
            )
            orm = result.scalar_one_or_none()
            if orm:
                await session.delete(orm)

        self._cache.pop(domain_id, None)
        return canvas

    async def list_domain_ids(self) -> list[str]:
        """List all domain IDs with canvases."""
        from sqlalchemy import select

        from services.api.database import CanvasORM, async_session

        async with async_session() as session:
            result = await session.execute(select(CanvasORM.domain_id))
            return [row[0] for row in result.all()]

    async def version(self, domain_id: str) -> int:
        """Get the version number for a canvas."""
        canvas = await self.get(domain_id)
        if canvas is None:
            return 0
        return int(canvas.updated_at.timestamp())


# ---------------------------------------------------------------------------
# CanvasService
# ---------------------------------------------------------------------------


class CanvasService:
    """Full lifecycle management for Domain Canvases.

    All mutating operations log to the Tape under ``canvas.*`` events and
    optionally synchronise changes to/from the ``FolderTreeService``.

    Parameters
    ----------
    tape_service:
        Shared Tape service for audit logging.
    folder_tree_service:
        Optional FolderTreeService for two-way sync.  When ``None``,
        sync operations are skipped gracefully.
    store:
        Backing store.  Defaults to a fresh ``CanvasStore``.
    layout_engine:
        Layout engine.  Defaults to a fresh ``LayoutEngine``.

    Usage::

        svc = CanvasService(tape_service=tape_svc)

        canvas = await svc.create_canvas("legal-research", "Legal Research")
        node   = await svc.add_node(canvas.domain_id, CanvasNode(...))
        await svc.apply_layout(canvas.domain_id)
    """

    def __init__(
        self,
        tape_service: TapeService,
        folder_tree_service: FolderTreeService | None = None,
        store: CanvasStore | None = None,
        layout_engine: LayoutEngine | None = None,
    ) -> None:
        self._tape = tape_service
        self._folder_tree = folder_tree_service
        self._store = store or CanvasStore()
        self._layout_engine = layout_engine or LayoutEngine()

    # ------------------------------------------------------------------
    # create_canvas
    # ------------------------------------------------------------------

    async def create_canvas(
        self,
        domain_id: str,
        domain_name: str,
        layout: CanvasLayout = CanvasLayout.SMART,
    ) -> Canvas:
        """Create a new empty canvas for a domain.

        Parameters
        ----------
        domain_id:
            Slug-style domain identifier.
        domain_name:
            Human-readable domain name.
        layout:
            Default auto-layout strategy.

        Returns
        -------
        Canvas
            The newly created canvas.
        """
        canvas = Canvas(
            domain_id=domain_id,
            domain_name=domain_name,
            layout=layout,
        )
        await self._store.add(canvas)

        await self._tape.log_event(
            event_type="canvas.created",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": domain_id,
                "domain_name": domain_name,
                "layout": layout,
            },
            agent_id="canvas-service",
        )

        return canvas

    # ------------------------------------------------------------------
    # get_canvas
    # ------------------------------------------------------------------

    async def get_canvas(self, domain_id: str) -> Canvas:
        """Retrieve a canvas by domain ID.

        Raises
        ------
        CanvasNotFoundError
            If no canvas exists for the given domain ID.
        """
        canvas = await self._store.get(domain_id)
        if canvas is None:
            raise CanvasNotFoundError(f"No canvas found for domain '{domain_id}'")
        return canvas

    # ------------------------------------------------------------------
    # add_node
    # ------------------------------------------------------------------

    async def add_node(
        self,
        domain_id: str,
        node: CanvasNode,
        sync_to_tree: bool = True,
    ) -> CanvasNode:
        """Add a node to the canvas.

        Parameters
        ----------
        domain_id:
            Domain to add the node to.
        node:
            The node to add.
        sync_to_tree:
            If ``True`` (default) and a ``FolderTreeService`` is configured,
            creates a corresponding directory in the folder tree.

        Raises
        ------
        CanvasNotFoundError
            If no canvas exists for the domain.
        NodeAlreadyExistsError
            If a node with the same ID already exists.
        """
        canvas = await self._get_canvas(domain_id)
        if canvas.get_node(node.id) is not None:
            raise NodeAlreadyExistsError(f"Node '{node.id}' already exists on canvas '{domain_id}'")

        # Inject default display metadata if absent
        if "colour" not in node.metadata:
            node.metadata["colour"] = _NODE_COLOURS.get(node.node_type, "#94a3b8")
        if "icon" not in node.metadata:
            node.metadata["icon"] = _NODE_ICONS.get(node.node_type, "box")

        canvas.nodes.append(node)
        canvas.updated_at = datetime.now(UTC)
        await self._store.update(canvas)

        # Sync to folder tree
        if sync_to_tree and self._folder_tree is not None and node.folder_path:
            import contextlib

            with contextlib.suppress(Exception):
                await self._folder_tree.create_directory(domain_id, node.folder_path)

        await self._tape.log_event(
            event_type="canvas.node_added",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": domain_id,
                "node_id": node.id,
                "node_type": node.node_type,
                "label": node.label,
            },
            agent_id="canvas-service",
        )

        return node

    # ------------------------------------------------------------------
    # remove_node
    # ------------------------------------------------------------------

    async def remove_node(
        self,
        domain_id: str,
        node_id: str,
        sync_to_tree: bool = True,
    ) -> None:
        """Remove a node and all its connected edges from the canvas.

        Raises
        ------
        CanvasNotFoundError / NodeNotFoundError
        """
        canvas = await self._get_canvas(domain_id)
        node = canvas.get_node(node_id)
        if node is None:
            raise NodeNotFoundError(f"Node '{node_id}' not found on canvas '{domain_id}'")

        if node.locked:
            raise CanvasError(f"Node '{node_id}' is locked and cannot be removed")

        # Remove connected edges
        canvas.edges = [e for e in canvas.edges if e.source != node_id and e.target != node_id]
        canvas.nodes = [n for n in canvas.nodes if n.id != node_id]
        canvas.updated_at = datetime.now(UTC)
        await self._store.update(canvas)

        # Sync to folder tree
        if sync_to_tree and self._folder_tree is not None and node.folder_path:
            import contextlib

            with contextlib.suppress(Exception):
                await self._folder_tree.delete_path(domain_id, node.folder_path)

        await self._tape.log_event(
            event_type="canvas.node_removed",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": domain_id,
                "node_id": node_id,
            },
            agent_id="canvas-service",
        )

    # ------------------------------------------------------------------
    # move_node
    # ------------------------------------------------------------------

    async def move_node(
        self,
        domain_id: str,
        node_id: str,
        x: float,
        y: float,
    ) -> CanvasNode:
        """Move a node to new (x, y) coordinates.

        Raises
        ------
        CanvasNotFoundError / NodeNotFoundError
        """
        canvas = await self._get_canvas(domain_id)
        node = canvas.get_node(node_id)
        if node is None:
            raise NodeNotFoundError(f"Node '{node_id}' not found on canvas '{domain_id}'")

        old_x, old_y = node.x, node.y
        node.x = x
        node.y = y
        canvas.updated_at = datetime.now(UTC)
        await self._store.update(canvas)

        await self._tape.log_event(
            event_type="canvas.node_moved",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": domain_id,
                "node_id": node_id,
                "from": {"x": old_x, "y": old_y},
                "to": {"x": x, "y": y},
            },
            agent_id="canvas-service",
        )

        return node

    # ------------------------------------------------------------------
    # update_node
    # ------------------------------------------------------------------

    async def update_node(
        self,
        domain_id: str,
        node_id: str,
        label: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> CanvasNode:
        """Update a node's label and/or metadata.

        Raises
        ------
        CanvasNotFoundError / NodeNotFoundError
        """
        canvas = await self._get_canvas(domain_id)
        node = canvas.get_node(node_id)
        if node is None:
            raise NodeNotFoundError(f"Node '{node_id}' not found on canvas '{domain_id}'")

        if label is not None:
            node.label = label
        if metadata is not None:
            node.metadata.update(metadata)

        canvas.updated_at = datetime.now(UTC)
        await self._store.update(canvas)

        await self._tape.log_event(
            event_type="canvas.node_updated",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": domain_id,
                "node_id": node_id,
                "label": node.label,
            },
            agent_id="canvas-service",
        )

        return node

    # ------------------------------------------------------------------
    # add_edge
    # ------------------------------------------------------------------

    async def add_edge(
        self,
        domain_id: str,
        edge: CanvasEdge,
    ) -> CanvasEdge:
        """Add a directed edge to the canvas.

        Raises
        ------
        CanvasNotFoundError / InvalidEdgeError
            If source or target nodes don't exist.
        """
        canvas = await self._get_canvas(domain_id)

        # Validate source and target
        if canvas.get_node(edge.source) is None:
            raise InvalidEdgeError(
                f"Source node '{edge.source}' does not exist on canvas '{domain_id}'"
            )
        if canvas.get_node(edge.target) is None:
            raise InvalidEdgeError(
                f"Target node '{edge.target}' does not exist on canvas '{domain_id}'"
            )

        canvas.edges.append(edge)
        canvas.updated_at = datetime.now(UTC)
        await self._store.update(canvas)

        await self._tape.log_event(
            event_type="canvas.edge_added",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": domain_id,
                "edge_id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "edge_type": edge.edge_type,
            },
            agent_id="canvas-service",
        )

        return edge

    # ------------------------------------------------------------------
    # remove_edge
    # ------------------------------------------------------------------

    async def remove_edge(self, domain_id: str, edge_id: str) -> None:
        """Remove an edge from the canvas.

        Raises
        ------
        CanvasNotFoundError / EdgeNotFoundError
        """
        canvas = await self._get_canvas(domain_id)
        edge = canvas.get_edge(edge_id)
        if edge is None:
            raise EdgeNotFoundError(f"Edge '{edge_id}' not found on canvas '{domain_id}'")

        canvas.edges = [e for e in canvas.edges if e.id != edge_id]
        canvas.updated_at = datetime.now(UTC)
        await self._store.update(canvas)

        await self._tape.log_event(
            event_type="canvas.edge_removed",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": domain_id,
                "edge_id": edge_id,
            },
            agent_id="canvas-service",
        )

    # ------------------------------------------------------------------
    # apply_layout
    # ------------------------------------------------------------------

    async def apply_layout(
        self,
        domain_id: str,
        strategy: CanvasLayout | None = None,
    ) -> Canvas:
        """Run a layout algorithm on the canvas, updating all node positions.

        Parameters
        ----------
        domain_id:
            Domain whose canvas to lay out.
        strategy:
            Layout strategy override.  Falls back to ``canvas.layout``.

        Returns
        -------
        Canvas
            The updated canvas with new node positions.
        """
        canvas = await self._get_canvas(domain_id)
        chosen = strategy or canvas.layout
        self._layout_engine.layout(canvas, chosen)

        if strategy is not None:
            canvas.layout = strategy
        canvas.updated_at = datetime.now(UTC)
        await self._store.update(canvas)

        await self._tape.log_event(
            event_type="canvas.layout_applied",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": domain_id,
                "strategy": str(chosen),
                "node_count": canvas.node_count,
            },
            agent_id="canvas-service",
        )

        return canvas

    # ------------------------------------------------------------------
    # set_view_mode
    # ------------------------------------------------------------------

    async def set_view_mode(
        self,
        domain_id: str,
        mode: CanvasViewMode,
    ) -> Canvas:
        """Toggle between Visual and Folder view mode.

        When switching to FOLDER mode this service triggers a
        ``sync_from_folder_tree()`` to ensure the folder-tree view is fresh.

        Returns
        -------
        Canvas
            The updated canvas.
        """
        canvas = await self._get_canvas(domain_id)
        old_mode = canvas.view_mode
        canvas.view_mode = mode
        canvas.updated_at = datetime.now(UTC)
        await self._store.update(canvas)

        # Pull latest folder-tree state when entering FOLDER mode
        if mode == CanvasViewMode.FOLDER and self._folder_tree is not None:
            import contextlib

            with contextlib.suppress(Exception):
                await self.sync_from_folder_tree(domain_id)

        await self._tape.log_event(
            event_type="canvas.view_mode_changed",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": domain_id,
                "from": old_mode,
                "to": mode,
            },
            agent_id="canvas-service",
        )

        return canvas

    # ------------------------------------------------------------------
    # sync_to_folder_tree
    # ------------------------------------------------------------------

    async def sync_to_folder_tree(self, domain_id: str) -> None:
        """Push canvas node changes to the FolderTreeService.

        Deep sync: for every node with a ``folder_path``, creates the
        directory AND writes content files that represent the node:

        - Agent nodes -> ``agents/<slug>/role.md``, ``agents/<slug>/goals.md``
        - Skill nodes -> ``skills/<slug>.py``
        - Workflow nodes -> ``workflows/<slug>/workflow.json``
        - Domain nodes -> ``README.md`` update
        - Other nodes -> ``<path>/node.json``

        Always logs to the Tape, even when no FolderTreeService is configured.
        """
        canvas = await self._get_canvas(domain_id)
        synced: list[str] = []
        files_written: list[str] = []

        if self._folder_tree is not None:
            import contextlib
            import json

            for node in canvas.nodes:
                if not node.folder_path:
                    continue
                # Ensure the directory exists
                with contextlib.suppress(Exception):
                    await self._folder_tree.create_directory(domain_id, node.folder_path)
                    synced.append(node.folder_path)

                # Write node-specific content files
                with contextlib.suppress(Exception):
                    if node.node_type == CanvasNodeType.AGENT:
                        role_path = f"{node.folder_path}/role.md"
                        role_content = (
                            f"# {node.label}\n\n"
                            f"**Role**: {node.metadata.get('role', 'specialist')}\n\n"
                            f"**Goal**: {node.metadata.get('description', 'No goal defined')}\n"
                        )
                        await self._folder_tree.write_file(
                            domain_id, role_path, role_content,
                        )
                        files_written.append(role_path)

                        goals_path = f"{node.folder_path}/goals.md"
                        goals_content = (
                            f"# Goals\n\n- "
                            f"{node.metadata.get('description', 'No goals defined')}\n"
                        )
                        await self._folder_tree.write_file(
                            domain_id, goals_path, goals_content,
                        )
                        files_written.append(goals_path)

                    elif node.node_type == CanvasNodeType.SKILL:
                        skill_file = (
                            f"{node.folder_path}.py"
                            if not node.folder_path.endswith(".py")
                            else node.folder_path
                        )
                        skill_content = (
                            f'"""{node.label} -- '
                            f'{node.metadata.get("description", "")}"""\n\n'
                            f"def execute(*args, **kwargs):\n"
                            f'    """Execute the {node.label} skill."""\n'
                            f"    pass\n"
                        )
                        await self._folder_tree.write_file(
                            domain_id, skill_file, skill_content,
                        )
                        files_written.append(skill_file)

                    elif node.node_type == CanvasNodeType.WORKFLOW:
                        wf_json_path = f"{node.folder_path}/workflow.json"
                        wf_data = {
                            "name": node.label,
                            "type": str(node.metadata.get("workflow_type", "sequential")),
                            "description": node.metadata.get("description", ""),
                        }
                        await self._folder_tree.write_file(
                            domain_id, wf_json_path, json.dumps(wf_data, indent=2),
                        )
                        files_written.append(wf_json_path)

                    elif node.node_type == CanvasNodeType.DOMAIN:
                        readme_path = f"{node.folder_path}/README.md"
                        readme_content = (
                            f"# {node.label}\n\n"
                            f"{node.metadata.get('description', '')}\n\n"
                            f"Generated by InkosAI Canvas sync.\n"
                        )
                        await self._folder_tree.write_file(
                            domain_id, readme_path, readme_content,
                        )
                        files_written.append(readme_path)

                    else:
                        node_json_path = f"{node.folder_path}/node.json"
                        meta_dict = {k: str(v) for k, v in node.metadata.items()}
                        await self._folder_tree.write_file(
                            domain_id, node_json_path,
                            json.dumps(
                                {"label": node.label, "type": node.node_type.value, "metadata": meta_dict},
                                indent=2,
                            ),
                        )
                        files_written.append(node_json_path)

        await self._tape.log_event(
            event_type="canvas.synced_to_tree",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": domain_id,
                "synced_paths": synced,
                "files_written": files_written,
                "synced_count": len(synced),
                "files_count": len(files_written),
            },
            agent_id="canvas-service",
        )

    # ------------------------------------------------------------------
    # sync_from_folder_tree
    # ------------------------------------------------------------------

    async def sync_from_folder_tree(self, domain_id: str) -> Canvas:
        """Pull FolderTree changes into the canvas.

        Recursively reads the folder tree and creates/updates canvas nodes
        to match. Deep sync maps path structure to node types:

        - ``agents/`` subdirectories -> AGENT nodes (label from role.md)
        - ``skills/`` .py files -> SKILL nodes
        - ``workflows/`` subdirectories -> WORKFLOW nodes (label from workflow.json)
        - ``templates/``, ``data_sources/``, ``config/`` -> matching node types
        - Other directories -> CUSTOM nodes

        Existing nodes with matching ``folder_path`` are updated (not duplicated).
        No-op if no ``FolderTreeService`` is configured or the domain has no tree.

        Returns
        -------
        Canvas
            The (possibly updated) canvas.
        """
        canvas = await self._get_canvas(domain_id)
        added = 0
        updated = 0

        if self._folder_tree is not None:
            import contextlib

            tree = None
            with contextlib.suppress(Exception):
                tree = await self._folder_tree.get_tree(domain_id)

            if tree is not None:
                existing_paths = {n.folder_path for n in canvas.nodes if n.folder_path}
                added, updated = await self._sync_tree_recursive(
                    domain_id, tree, tree.root_path, canvas, existing_paths, depth=0,
                )

                if added or updated:
                    canvas.updated_at = datetime.now(UTC)
                    await self._store.update(canvas)

            await self._tape.log_event(
                event_type="canvas.synced_from_tree",
                payload={
                    "canvas_id": str(canvas.id),
                    "domain_id": domain_id,
                    "nodes_added": added,
                    "nodes_updated": updated,
                },
                agent_id="canvas-service",
            )

        return canvas

    async def _sync_tree_recursive(
        self,
        domain_id: str,
        tree: FolderTree,
        current_path: str,
        canvas: Canvas,
        existing_paths: set[str],
        depth: int,
    ) -> tuple[int, int]:
        """Recursively walk the folder tree and sync nodes."""
        added = 0
        updated = 0
        current_node = tree.nodes.get(current_path)
        if current_node is None:
            return added, updated

        from packages.folder_tree import NodeType

        # Skip files -- only directories map to canvas nodes
        if current_node.node_type == NodeType.FILE:
            return added, updated

        # Skip the root itself (depth 0) -- it maps to the domain node
        if depth > 0:
            root_path = tree.root_path
            rel_path = current_path
            if current_path.startswith(root_path + "/"):
                rel_path = current_path[len(root_path) + 1 :]
            elif current_path == root_path:
                rel_path = ""

            if rel_path and rel_path not in existing_paths:
                node_type = self._infer_node_type_from_path(rel_path)
                label = current_node.name

                # Try to get a better label from content files
                label = await self._read_node_label_from_tree(
                    domain_id, rel_path, node_type, label,
                )

                new_node = CanvasNode(
                    id=f"tree-{current_path.replace('/', '-')}",
                    node_type=node_type,
                    label=label,
                    folder_path=rel_path,
                    metadata={
                        "colour": _NODE_COLOURS.get(node_type, "#94a3b8"),
                        "icon": _NODE_ICONS.get(node_type, "box"),
                        "source": "folder_tree",
                    },
                )
                canvas.nodes.append(new_node)
                existing_paths.add(rel_path)
                added += 1
            elif rel_path in existing_paths:
                for existing in canvas.nodes:
                    if existing.folder_path == rel_path:
                        new_label = await self._read_node_label_from_tree(
                            domain_id, rel_path,
                            self._infer_node_type_from_path(rel_path),
                            existing.label,
                        )
                        if new_label != existing.label:
                            existing.label = new_label
                            updated += 1
                        break

        # Recurse into children
        for child_path in current_node.children:
            child_added, child_updated = await self._sync_tree_recursive(
                domain_id, tree, child_path, canvas, existing_paths, depth + 1,
            )
            added += child_added
            updated += child_updated

        return added, updated

    async def _read_node_label_from_tree(
        self,
        domain_id: str,
        rel_path: str,
        node_type: CanvasNodeType,
        fallback_label: str,
    ) -> str:
        """Try to read a better label from the folder tree content."""
        if self._folder_tree is None:
            return fallback_label
        import contextlib
        import json

        if node_type == CanvasNodeType.AGENT:
            with contextlib.suppress(Exception):
                node = await self._folder_tree.read_file(
                    domain_id, f"{rel_path}/role.md",
                )
                file_content = getattr(node, "content", "")
                first_line = file_content.split("\n")[0].strip()
                if first_line.startswith("# "):
                    return first_line[2:].strip()

        if node_type == CanvasNodeType.WORKFLOW:
            with contextlib.suppress(Exception):
                node = await self._folder_tree.read_file(
                    domain_id, f"{rel_path}/workflow.json",
                )
                file_content = getattr(node, "content", "")
                data = json.loads(file_content)
                if isinstance(data, dict) and "name" in data:
                    return str(data["name"])

        return fallback_label

    @staticmethod
    def _infer_node_type_from_path(rel_path: str) -> CanvasNodeType:
        """Infer a canvas node type from a relative folder path.

        More accurate than name-based inference because it uses
        the full path context (e.g. ``agents/analyst`` -> AGENT).
        """
        parts = rel_path.lower().split("/")
        if len(parts) >= 2:
            parent = parts[0]
            if parent in ("agents", "agent"):
                return CanvasNodeType.AGENT
            if parent in ("skills", "skill"):
                return CanvasNodeType.SKILL
            if parent in ("workflows", "workflow"):
                return CanvasNodeType.WORKFLOW
            if parent in ("templates", "template"):
                return CanvasNodeType.TEMPLATE
            if parent in ("data_sources", "data_source"):
                return CanvasNodeType.DATA_SOURCE
            if parent in ("config", "configuration"):
                return CanvasNodeType.CUSTOM
            if parent in ("canvas",):
                return CanvasNodeType.DOMAIN
        name = parts[-1] if parts else ""
        return CanvasService._infer_node_type(name)

    # ------------------------------------------------------------------
    # canvas_from_domain_blueprint
    # ------------------------------------------------------------------

    async def canvas_from_domain_blueprint(
        self,
        blueprint: DomainBlueprint,
        layout: CanvasLayout = CanvasLayout.SMART,
        sync_to_tree: bool = False,
    ) -> Canvas:
        """Bootstrap a fully-populated canvas from a ``DomainBlueprint``.

        Creates a canvas with one node per agent, skill, workflow, plus a
        domain node, and wires up the standard edge topology.  Applies the
        requested layout.

        Parameters
        ----------
        blueprint:
            The domain blueprint to visualise.
        layout:
            Layout strategy to apply.
        sync_to_tree:
            If ``True`` and a ``FolderTreeService`` is configured, syncs
            canvas nodes to the folder tree after creation.

        Returns
        -------
        Canvas
            The newly created and laid-out canvas.
        """
        canvas = await self.create_canvas(
            domain_id=blueprint.domain_id,
            domain_name=blueprint.domain_name,
            layout=layout,
        )

        # --- Domain node ---
        domain_node = CanvasNode(
            id=f"domain-{blueprint.domain_id}",
            node_type=CanvasNodeType.DOMAIN,
            label=blueprint.domain_name,
            folder_path=blueprint.domain_name.replace(" ", "_"),
            metadata={
                "colour": _NODE_COLOURS[CanvasNodeType.DOMAIN],
                "icon": _NODE_ICONS[CanvasNodeType.DOMAIN],
                "description": blueprint.description,
            },
        )
        canvas.nodes.append(domain_node)

        # --- Agent nodes ---
        for agent in blueprint.agents:
            agent_node = CanvasNode(
                id=f"agent-{agent.agent_id}",
                node_type=CanvasNodeType.AGENT,
                label=agent.name,
                folder_path=f"{blueprint.domain_name.replace(' ', '_')}/agents/{agent.name.lower().replace(' ', '_')}",
                metadata={
                    "colour": _NODE_COLOURS[CanvasNodeType.AGENT],
                    "icon": _NODE_ICONS[CanvasNodeType.AGENT],
                    "description": agent.goal,
                    "role": agent.role,
                },
            )
            canvas.nodes.append(agent_node)

        # --- Skill nodes ---
        for skill in blueprint.skills:
            skill_node = CanvasNode(
                id=f"skill-{skill.skill_id}",
                node_type=CanvasNodeType.SKILL,
                label=skill.name,
                folder_path=f"{blueprint.domain_name.replace(' ', '_')}/skills/{skill.name.lower().replace(' ', '_')}",
                metadata={
                    "colour": _NODE_COLOURS[CanvasNodeType.SKILL],
                    "icon": _NODE_ICONS[CanvasNodeType.SKILL],
                    "description": skill.description,
                    "is_reused": skill.is_reused,
                },
            )
            canvas.nodes.append(skill_node)

        # --- Workflow nodes ---
        for workflow in blueprint.workflows:
            wf_node = CanvasNode(
                id=f"workflow-{workflow.workflow_id}",
                node_type=CanvasNodeType.WORKFLOW,
                label=workflow.name,
                folder_path=f"{blueprint.domain_name.replace(' ', '_')}/workflows/{workflow.name.lower().replace(' ', '_')}",
                metadata={
                    "colour": _NODE_COLOURS[CanvasNodeType.WORKFLOW],
                    "icon": _NODE_ICONS[CanvasNodeType.WORKFLOW],
                    "description": workflow.description,
                    "workflow_type": workflow.workflow_type,
                },
            )
            canvas.nodes.append(wf_node)

        # --- Edges ---
        node_ids = {n.id for n in canvas.nodes}
        domain_node_id = f"domain-{blueprint.domain_id}"

        # domain -> agents
        for agent in blueprint.agents:
            agent_node_id = f"agent-{agent.agent_id}"
            if agent_node_id in node_ids:
                canvas.edges.append(
                    CanvasEdge(
                        source=domain_node_id,
                        target=agent_node_id,
                        edge_type=CanvasEdgeType.CONTAINS,
                    )
                )

        # agent -> skills (via tools matching)
        agent_claimed_skills: set[str] = set()
        for agent in blueprint.agents:
            agent_node_id = f"agent-{agent.agent_id}"
            for tool in agent.tools:
                for skill in blueprint.skills:
                    skill_node_id = f"skill-{skill.skill_id}"
                    if (
                        tool.lower() in skill.name.lower() or skill.skill_id.lower() in tool.lower()
                    ) and skill_node_id in node_ids:
                        canvas.edges.append(
                            CanvasEdge(
                                source=agent_node_id,
                                target=skill_node_id,
                                edge_type=CanvasEdgeType.USES,
                                animated=True,
                            )
                        )
                        agent_claimed_skills.add(skill_node_id)

        # domain -> unclaimed skills
        for skill in blueprint.skills:
            skill_node_id = f"skill-{skill.skill_id}"
            if skill_node_id not in agent_claimed_skills and skill_node_id in node_ids:
                canvas.edges.append(
                    CanvasEdge(
                        source=domain_node_id,
                        target=skill_node_id,
                        edge_type=CanvasEdgeType.CONTAINS,
                    )
                )

        # workflow -> agents
        for workflow in blueprint.workflows:
            wf_node_id = f"workflow-{workflow.workflow_id}"
            if wf_node_id not in node_ids:
                continue
            for agent_id_ref in workflow.agent_ids:
                agent_node_id = f"agent-{agent_id_ref}"
                if agent_node_id in node_ids:
                    canvas.edges.append(
                        CanvasEdge(
                            source=wf_node_id,
                            target=agent_node_id,
                            edge_type=CanvasEdgeType.EXECUTES,
                        )
                    )

        # Apply layout
        self._layout_engine.layout(canvas, layout)
        canvas.updated_at = datetime.now(UTC)
        await self._store.update(canvas)

        # Sync to folder tree if requested
        if sync_to_tree and self._folder_tree is not None:
            import contextlib

            with contextlib.suppress(Exception):
                await self.sync_to_folder_tree(canvas.domain_id)

        await self._tape.log_event(
            event_type="canvas.created_from_blueprint",
            payload={
                "canvas_id": str(canvas.id),
                "domain_id": canvas.domain_id,
                "domain_name": canvas.domain_name,
                "layout": str(layout),
                "node_count": canvas.node_count,
                "edge_count": canvas.edge_count,
                "blueprint_id": str(blueprint.id),
                "synced_to_tree": sync_to_tree and self._folder_tree is not None,
            },
            agent_id="canvas-service",
        )

        return canvas

    # ------------------------------------------------------------------
    # create_canvas_from_domain (alias with sync by default)
    # ------------------------------------------------------------------

    async def create_canvas_from_domain(
        self,
        blueprint: DomainBlueprint,
        layout: CanvasLayout = CanvasLayout.SMART,
    ) -> Canvas:
        """Create a canvas from a domain blueprint with folder-tree sync.

        This is a convenience wrapper around ``canvas_from_domain_blueprint``
        that enables folder-tree synchronization by default.

        Parameters
        ----------
        blueprint:
            The domain blueprint to visualise.
        layout:
            Layout strategy to apply.

        Returns
        -------
        Canvas
            The newly created canvas with nodes, edges, and folder-tree sync.
        """
        return await self.canvas_from_domain_blueprint(blueprint, layout=layout, sync_to_tree=True)

    # ------------------------------------------------------------------
    # diff
    # ------------------------------------------------------------------

    async def diff(
        self,
        domain_id: str,
        old_canvas: Canvas,
        new_canvas: Canvas,
    ) -> CanvasDiff:
        """Compute a structural diff between two canvas snapshots.

        Parameters
        ----------
        domain_id:
            Domain these canvases belong to.
        old_canvas:
            The baseline canvas snapshot.
        new_canvas:
            The updated canvas snapshot.

        Returns
        -------
        CanvasDiff
        """
        old_node_ids = {n.id for n in old_canvas.nodes}
        new_node_ids = {n.id for n in new_canvas.nodes}

        added_nodes = [n for n in new_canvas.nodes if n.id not in old_node_ids]
        removed_ids = [nid for nid in old_node_ids if nid not in new_node_ids]

        # Moved nodes: same ID but different position
        moved_nodes: list[CanvasNode] = []
        old_by_id = {n.id: n for n in old_canvas.nodes}
        for node in new_canvas.nodes:
            old = old_by_id.get(node.id)
            if old and (old.x != node.x or old.y != node.y):
                moved_nodes.append(node)

        old_edge_ids = {e.id for e in old_canvas.edges}
        new_edge_ids = {e.id for e in new_canvas.edges}

        added_edges = [e for e in new_canvas.edges if e.id not in old_edge_ids]
        removed_edge_ids = [eid for eid in old_edge_ids if eid not in new_edge_ids]

        summary_parts = []
        if added_nodes:
            summary_parts.append(f"+{len(added_nodes)} node(s)")
        if removed_ids:
            summary_parts.append(f"-{len(removed_ids)} node(s)")
        if moved_nodes:
            summary_parts.append(f"~{len(moved_nodes)} moved")
        if added_edges:
            summary_parts.append(f"+{len(added_edges)} edge(s)")
        if removed_edge_ids:
            summary_parts.append(f"-{len(removed_edge_ids)} edge(s)")

        return CanvasDiff(
            canvas_id=old_canvas.id,
            from_version=await self._store.version(domain_id) - 1,
            to_version=await self._store.version(domain_id),
            added_nodes=added_nodes,
            removed_node_ids=removed_ids,
            moved_nodes=moved_nodes,
            added_edges=added_edges,
            removed_edge_ids=removed_edge_ids,
            summary=", ".join(summary_parts) or "no changes",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_canvas(self, domain_id: str) -> Canvas:
        """Retrieve canvas or raise CanvasNotFoundError."""
        canvas = await self._store.get(domain_id)
        if canvas is None:
            raise CanvasNotFoundError(f"No canvas found for domain '{domain_id}'")
        return canvas

    @staticmethod
    def _infer_node_type(name: str) -> CanvasNodeType:
        """Infer a canvas node type from a folder/file name."""
        name_lower = name.lower()
        if name_lower in ("agents", "agent"):
            return CanvasNodeType.AGENT
        if name_lower in ("skills", "skill"):
            return CanvasNodeType.SKILL
        if name_lower in ("workflows", "workflow"):
            return CanvasNodeType.WORKFLOW
        if name_lower in ("templates", "template"):
            return CanvasNodeType.TEMPLATE
        if name_lower in ("data_sources", "data_source"):
            return CanvasNodeType.DATA_SOURCE
        return CanvasNodeType.CUSTOM

    # ------------------------------------------------------------------
    # Store accessor (for testing)
    # ------------------------------------------------------------------

    @property
    def store(self) -> CanvasStore:
        """Access the underlying store (for testing)."""
        return self._store
