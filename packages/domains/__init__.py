"""InkosAI Official Planning Domains — Gastown, GSD, and BMAD.

This package provides three leading AI planning methodologies as first-class
InkosAI domains:

- **Gastown Domain** — Multi-agent workspace orchestration and persistent coordination
- **GSD Domain (Get Shit Done)** — Meta-prompting and structured phase-based autonomous development
- **BMAD Domain** — Agile AI-driven development with planning tracks and collaborative workflows

**Planning Super Domain**
A unified domain that allows mixing and matching planning styles from all three
methodologies on the same canvas.

Example::

    from packages.domains import PlanningDomainFactory, PlanningDomainType

    # Create individual domains
    gastown = await PlanningDomainFactory.create_domain(
        PlanningDomainType.GASTOWN,
        tape_service=tape_svc
    )

    # Create the Planning Super Domain
    super_domain = await PlanningDomainFactory.create_planning_super_domain(
        tape_service=tape_svc
    )

    # Register all planning domains
    registry = PlanningDomainRegistry(tape_svc)
    await registry.register_all(domain_registry)
"""

from __future__ import annotations

from packages.domains.constants import (
    PlanningDomainType,
    PlanningAgentRole,
    PlanningSkillType,
    PlanningWorkflowType,
    PLANNING_DOMAIN_VERSION,
)

__all__ = [
    # Domain types
    "PlanningDomainType",
    "PlanningAgentRole",
    "PlanningSkillType",
    "PlanningWorkflowType",
    # Version
    "PLANNING_DOMAIN_VERSION",
]
