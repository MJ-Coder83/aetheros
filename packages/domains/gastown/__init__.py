"""Gastown Domain — Multi-agent workspace orchestration and coordination.

Gastown provides persistent workspace management for multi-agent systems,
with specialized agents for workspace lifecycle, agent coordination,
session management, and resource allocation.

Key Features:
- Workspace initialization and teardown
- Multi-agent session coordination
- Resource allocation and monitoring
- Task distribution across agent pools
- Persistent agent state and context

Example::

    from packages.domains.gastown import GastownDomainBlueprint
    from packages.domain.domain_blueprint import DomainFolderTreeGenerator

    blueprint = GastownDomainBlueprint.create()
    generator = DomainFolderTreeGenerator(tape_service=tape_svc)
    folder_tree = await generator.generate(blueprint)
"""

from __future__ import annotations

from packages.domains.gastown.agents import (
    AGENT_COORDINATOR_CONFIG,
    RESOURCE_ALLOCATOR_CONFIG,
    SESSION_MANAGER_CONFIG,
    TASK_DISTRIBUTOR_CONFIG,
    WORKSPACE_MANAGER_CONFIG,
)
from packages.domains.gastown.blueprint import (
    GastownAgentBlueprint,
    GastownDomainBlueprint,
    GastownSkillBlueprint,
    GastownWorkflowBlueprint,
)
from packages.domains.gastown.skills import (
    AGENT_COORDINATION_SKILL,
    RESOURCE_ALLOCATION_SKILL,
    SESSION_MANAGEMENT_SKILL,
    TASK_DISTRIBUTION_SKILL,
    WORKSPACE_ORCHESTRATION_SKILL,
)
from packages.domains.gastown.workflows import (
    MULTI_AGENT_COORDINATION_WORKFLOW,
    SESSION_LIFECYCLE_WORKFLOW,
    WORKSPACE_INITIALIZATION_WORKFLOW,
)

__all__ = [
    # Main blueprint
    "GastownDomainBlueprint",
    "GastownAgentBlueprint",
    "GastownSkillBlueprint",
    "GastownWorkflowBlueprint",
    # Agent configs
    "WORKSPACE_MANAGER_CONFIG",
    "AGENT_COORDINATOR_CONFIG",
    "SESSION_MANAGER_CONFIG",
    "RESOURCE_ALLOCATOR_CONFIG",
    "TASK_DISTRIBUTOR_CONFIG",
    # Skill configs
    "WORKSPACE_ORCHESTRATION_SKILL",
    "AGENT_COORDINATION_SKILL",
    "SESSION_MANAGEMENT_SKILL",
    "RESOURCE_ALLOCATION_SKILL",
    "TASK_DISTRIBUTION_SKILL",
    # Workflow configs
    "WORKSPACE_INITIALIZATION_WORKFLOW",
    "MULTI_AGENT_COORDINATION_WORKFLOW",
    "SESSION_LIFECYCLE_WORKFLOW",
    # Constants
    "DOMAIN_ID",
    "DOMAIN_NAME",
    "DOMAIN_DESCRIPTION",
]

# Domain metadata
DOMAIN_ID = "gastown"
DOMAIN_NAME = "Gastown"
DOMAIN_DESCRIPTION = (
    "Multi-agent workspace orchestration domain providing persistent "
    "coordination, session management, and resource allocation for "
    "distributed agent systems."
)
