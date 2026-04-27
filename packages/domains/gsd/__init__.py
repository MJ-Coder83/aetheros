"""GSD Domain (Get Shit Done) — Meta-prompting and phase-based development.

GSD provides a structured approach to autonomous development through
meta-prompting, context engineering, and phase-based execution.

Key Features:
- Structured phase-based development cycles
- Meta-prompt design and optimization
- Context engineering and management
- Execution tracking and validation
- Quality gates at each phase

Example::

    from packages.domains.gsd import GSDDomainBlueprint
    from packages.domain.domain_blueprint import DomainFolderTreeGenerator

    blueprint = GSDDomainBlueprint.create()
    generator = DomainFolderTreeGenerator(tape_service=tape_svc)
    folder_tree = await generator.generate(blueprint)
"""

from __future__ import annotations

from packages.domains.gsd.blueprint import (
    GSDDomainBlueprint,
    GSDAgentBlueprint,
    GSDSkillBlueprint,
    GSDWorkflowBlueprint,
)

__all__ = [
    # Main blueprint
    "GSDDomainBlueprint",
    "GSDAgentBlueprint",
    "GSDSkillBlueprint",
    "GSDWorkflowBlueprint",
    # Domain phases
    "GSD_PHASES",
    # Constants
    "DOMAIN_ID",
    "DOMAIN_NAME",
    "DOMAIN_DESCRIPTION",
]

# Domain phases
GSD_PHASES = [
    "research",
    "design",
    "implement",
    "test",
    "deploy",
    "validate",
]

# Domain metadata
DOMAIN_ID = "gsd"
DOMAIN_NAME = "GSD (Get Shit Done)"
DOMAIN_DESCRIPTION = (
    "Meta-prompting and phase-based autonomous development domain "
    "providing structured development cycles with context engineering "
    "and quality validation at each phase."
)
