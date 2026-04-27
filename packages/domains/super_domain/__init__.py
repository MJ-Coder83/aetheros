"""Planning Super Domain — Unified planning environment.

The Planning Super Domain combines Gastown, GSD, and BMAD methodologies
into a unified environment with intelligent Prime orchestration.

Key Features:
- Hybrid agent pool from all three methodologies
- Smart Planning Orchestrator (powered by Prime)
- Visual planning board with methodology tags
- Automatic recommendation of best planning mix for tasks
- Cross-methodology conflict resolution

Example::

    from packages.domains.super_domain import PlanningSuperDomainBlueprint
    from packages.domain.domain_blueprint import DomainFolderTreeGenerator

    blueprint = PlanningSuperDomainBlueprint.create()
    generator = DomainFolderTreeGenerator(tape_service=tape_svc)
    folder_tree = await generator.generate(blueprint)
"""

from __future__ import annotations

from packages.domains.super_domain.blueprint import (
    PlanningSuperDomainBlueprint,
    SuperDomainAgentBlueprint,
    SuperDomainSkillBlueprint,
    SuperDomainWorkflowBlueprint,
)

__all__ = [
    # Main blueprint
    "PlanningSuperDomainBlueprint",
    "SuperDomainAgentBlueprint",
    "SuperDomainSkillBlueprint",
    "SuperDomainWorkflowBlueprint",
    # Planning mix types
    "PLANNING_MIX_TYPES",
    # Constants
    "DOMAIN_ID",
    "DOMAIN_NAME",
    "DOMAIN_DESCRIPTION",
]

# Planning mix recommendation types
PLANNING_MIX_TYPES = [
    "pure_gastown",
    "pure_gsd",
    "pure_bmad",
    "gastown_gsd",
    "gastown_bmad",
    "gsd_bmad",
    "full_hybrid",
]

# Domain metadata
DOMAIN_ID = "planning_super"
DOMAIN_NAME = "Planning Super Domain"
DOMAIN_DESCRIPTION = (
    "Unified planning environment combining Gastown, GSD, and BMAD "
    "methodologies with smart Prime orchestration and intelligent "
    "methodology selection for any task."
)
