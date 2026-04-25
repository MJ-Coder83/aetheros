"""InkosAI Domain package — One-Click Domain Creation system.

Provides:
- DomainBlueprint + supporting blueprint models
- EvaluationCriteria — success/quality metrics for a domain
- DomainFolderTreeGenerator — generate a FolderTree from a DomainBlueprint
- StarterCanvasGenerator — visual canvas generation from a DomainBlueprint
- CanvasLayout strategies: Layered, Hub-and-Spoke, Clustered, Linear
- OneClickDomainCreationEngine — orchestrates blueprint + tree + canvas
"""

from packages.domain.creation import (
    DomainCreationOption,
    OneClickDomainCreationEngine,
    OneClickDomainCreationResult,
)
from packages.domain.domain_blueprint import (
    AgentBlueprint,
    AgentRole,
    CreationMode,
    DomainBlueprint,
    DomainConfig,
    DomainCreationError,
    DomainFolderTreeGenerator,
    DomainStatus,
    EvaluationCriteria,
    SkillBlueprint,
    WorkflowBlueprint,
    WorkflowType,
)
from packages.domain.starter_canvas import (
    CanvasEdge,
    CanvasLayout,
    CanvasNode,
    CanvasNodeType,
    StarterCanvas,
    StarterCanvasGenerator,
)

__all__ = [
    "AgentBlueprint",
    "AgentRole",
    "CanvasEdge",
    "CanvasLayout",
    "CanvasNode",
    "CanvasNodeType",
    "CreationMode",
    "DomainBlueprint",
    "DomainConfig",
    "DomainCreationError",
    "DomainCreationOption",
    "DomainFolderTreeGenerator",
    "DomainStatus",
    "EvaluationCriteria",
    "OneClickDomainCreationEngine",
    "OneClickDomainCreationResult",
    "SkillBlueprint",
    "StarterCanvas",
    "StarterCanvasGenerator",
    "WorkflowBlueprint",
    "WorkflowType",
]
