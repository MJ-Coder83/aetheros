"""Canvas node plugins — specialist node types for the Domain Canvas.

Sub-modules
-----------
browser     — BrowserNode: live web / Electron / Tauri preview (Agent 2)
terminal    — TerminalNode: TUI layout editor (Agent 3)
"""

from packages.canvas.nodes.browser import (
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

__all__ = [
    "BrowserNode",
    "BrowserNodeConfig",
    "BrowserNodeType",
    "DetectedElement",
    "ElementTag",
    "FrameworkType",
    "LivePreviewState",
    "NaturalLanguageEdit",
    "PreviewMode",
]
