"""InkosAI Domain Canvas — dual-mode visual + folder-tree canvas.

Architecture::

    Canvas              — complete canvas (nodes + edges + metadata)
    CanvasNode          — a single positioned node
    CanvasEdge          — a directed edge between nodes
    CanvasNodeType      — semantic type (domain, agent, skill, workflow, …)
    CanvasEdgeType      — semantic type (contains, uses, executes, …)
    CanvasLayout        — layout strategy (layered, hub-and-spoke, …)
    CanvasViewMode      — visual / folder view toggle
    CanvasOperation     — a single canvas mutation (for audit / undo)
    CanvasDiff          — diff between two canvas snapshots
    LayoutEngine        — stateless layout algorithm dispatcher
    CanvasService       — full lifecycle service with folder-tree sync
    CanvasStore         — in-memory backing store

Exceptions::

    CanvasError, CanvasNotFoundError, NodeNotFoundError,
    EdgeNotFoundError, NodeAlreadyExistsError, InvalidEdgeError
"""

from packages.canvas.core import (
    CanvasService,
    CanvasStore,
    LayoutEngine,
)
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
