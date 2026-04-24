"""InkosAI Domain package — One-Click Domain Creation system.

Provides:
- DomainBlueprint + supporting blueprint models (re-exported from prime.domain_creation)
- StarterCanvasGenerator — visual canvas generation from a DomainBlueprint
- CanvasLayout strategies: Layered, Hub-and-Spoke, Clustered, Linear
"""

from packages.domain.starter_canvas import (
    CanvasEdge,
    CanvasLayout,
    CanvasNode,
    CanvasNodeType,
    StarterCanvas,
    StarterCanvasGenerator,
)

__all__ = [
    "CanvasEdge",
    "CanvasLayout",
    "CanvasNode",
    "CanvasNodeType",
    "StarterCanvas",
    "StarterCanvasGenerator",
]
