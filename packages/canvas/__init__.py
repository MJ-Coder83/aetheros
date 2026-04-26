"""InkosAI Canvas -- Visual graph representation with dual-mode support.

The Canvas provides a visual interface for domains alongside the canonical
folder-tree representation. It supports:

- Visual graph layout (Layered, Hub-and-Spoke, Clustered, Linear, Smart Auto)
- Folder tree view (canonical source of truth)
- Real-time synchronization between visual and folder representations
- Browser nodes with live embedding for web frameworks
- Terminal nodes with TUI layout editing
- Tape logging for all canvas operations
- Canvas v5: Plugin Nodes, Simulation/Tape Overlays, NL Editing,
  Prime Co-Pilot, AetherGit Versioning, Swarm Integration
"""

from packages.canvas.canvas_v5 import (
    CanvasV5Engine,
    CanvasVersion,
    CanvasVersioningManager,
    CopilotSuggestion,
    CopilotSuggestionType,
    FrameworkTier,
    GovernedSwarmResult,
    NLEditEngine,
    NLEditResult,
    NLEditType,
    PluginNodeConfig,
    PluginNodeManager,
    PrimeCoPilot,
    QuickSwarmResult,
    SimulationMetric,
    SimulationOverlay,
    SwarmIntegration,
    SwarmMode,
    TapeEventEntry,
    TapeOverlay,
    TieredFramework,
    TieredUIRegistry,
    UIFramework,
)
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
    "CanvasV5Engine",
    "CanvasVersion",
    "CanvasVersioningManager",
    "CanvasViewMode",
    "CopilotSuggestion",
    "CopilotSuggestionType",
    "DetectedElement",
    "EdgeNotFoundError",
    "ElementTag",
    "FrameworkTier",
    "FrameworkType",
    "GovernedSwarmResult",
    "InvalidEdgeError",
    "LayoutEngine",
    "LivePreviewState",
    "NLEditEngine",
    "NLEditResult",
    "NLEditType",
    "NaturalLanguageEdit",
    "NodeAlreadyExistsError",
    "NodeNotFoundError",
    "PluginNodeConfig",
    "PluginNodeManager",
    "PreviewMode",
    "PrimeCoPilot",
    "QuickSwarmResult",
    "SimulationMetric",
    "SimulationOverlay",
    "SwarmIntegration",
    "SwarmMode",
    "TapeEventEntry",
    "TapeOverlay",
    "TieredFramework",
    "TieredUIRegistry",
    "UIFramework",
]
