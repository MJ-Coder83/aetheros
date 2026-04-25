"""InkosAI Canvas — Visual graph representation with dual-mode support.

The Canvas provides a visual interface for domains alongside the canonical
folder-tree representation. It supports:

- Visual graph layout (Layered, Hub-and-Spoke, Clustered, Linear, Smart Auto)
- Folder tree view (canonical source of truth)
- Real-time synchronization between visual and folder representations
- Browser nodes with live embedding for web frameworks
- Terminal nodes with TUI layout editing
- Tape logging for all canvas operations
"""

from packages.canvas.core import (
    Canvas,
    CanvasDiff,
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
from packages.canvas.nodes import (
    BrowserNode,
    BrowserNodeConfig,
    BrowserNodeType,
    DetectedElement,
    ElementTag,
    FrameworkType,
    LivePreviewState,
    NaturalLanguageEdit,
    PreviewMode,
)
from packages.canvas.service import CanvasDomainService

__all__ = [
    "BrowserNode",
    "BrowserNodeConfig",
    "BrowserNodeType",
    "Canvas",
    "CanvasDiff",
    "CanvasDomainService",
    "CanvasEdge",
    "CanvasEdgeType",
    "CanvasError",
    "CanvasLayout",
    "CanvasNode",
    "CanvasNodeType",
    "CanvasNotFoundError",
    "CanvasService",
    "CanvasStore",
    "CanvasViewMode",
    "DetectedElement",
    "EdgeNotFoundError",
    "ElementTag",
    "FrameworkType",
    "InvalidEdgeError",
    "LayoutEngine",
    "LivePreviewState",
    "NaturalLanguageEdit",
    "NodeAlreadyExistsError",
    "NodeNotFoundError",
    "PreviewMode",
]
