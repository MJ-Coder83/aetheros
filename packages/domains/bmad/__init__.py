"""BMAD Domain — Breakthrough Method for Agile AI-Driven Development.

BMAD provides an agile, sprint-based approach to AI development with
planning tracks, breakthrough facilitation, and collaborative workflows.

Key Features:
- Sprint planning and execution
- Breakthrough facilitation sessions
- Multi-track coordination
- Sprint reviews and retrospectives
- Agile coaching and guidance

Example::

    from packages.domains.bmad import BMADDomainBlueprint
    from packages.domain.domain_blueprint import DomainFolderTreeGenerator

    blueprint = BMADDomainBlueprint.create()
    generator = DomainFolderTreeGenerator(tape_service=tape_svc)
    folder_tree = await generator.generate(blueprint)
"""

from __future__ import annotations

from packages.domains.bmad.blueprint import (
    BMADAgentBlueprint,
    BMADDomainBlueprint,
    BMADSkillBlueprint,
    BMADWorkflowBlueprint,
)

__all__ = [
    # Main blueprint
    "BMADDomainBlueprint",
    "BMADAgentBlueprint",
    "BMADSkillBlueprint",
    "BMADWorkflowBlueprint",
    # Planning tracks
    "BMAD_TRACKS",
    # Constants
    "DOMAIN_ID",
    "DOMAIN_NAME",
    "DOMAIN_DESCRIPTION",
]

# Planning tracks
BMAD_TRACKS = [
    "research",
    "design",
    "build",
    "review",
]

# Domain metadata
DOMAIN_ID = "bmad"
DOMAIN_NAME = "BMAD"
DOMAIN_DESCRIPTION = (
    "Breakthrough Method for Agile AI-Driven Development domain "
    "providing sprint-based planning with multi-track coordination "
    "and breakthrough facilitation."
)
