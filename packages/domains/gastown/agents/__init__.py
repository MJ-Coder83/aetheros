"""Gastown Domain Agents.

This module defines the specialized agents for the Gastown multi-agent
workspace orchestration domain.
"""

from __future__ import annotations

# Agent configurations are defined in the blueprint module
# This package structure allows for future agent implementations

__all__ = [
    "WORKSPACE_MANAGER_CONFIG",
    "AGENT_COORDINATOR_CONFIG",
    "SESSION_MANAGER_CONFIG",
    "RESOURCE_ALLOCATOR_CONFIG",
    "TASK_DISTRIBUTOR_CONFIG",
]

# Agent configuration exports (for IDE/type checking)
WORKSPACE_MANAGER_CONFIG = {
    "agent_id": "gastown_workspace_manager",
    "name": "Workspace Manager",
}

AGENT_COORDINATOR_CONFIG = {
    "agent_id": "gastown_agent_coordinator",
    "name": "Agent Coordinator",
}

SESSION_MANAGER_CONFIG = {
    "agent_id": "gastown_session_manager",
    "name": "Session Manager",
}

RESOURCE_ALLOCATOR_CONFIG = {
    "agent_id": "gastown_resource_allocator",
    "name": "Resource Allocator",
}

TASK_DISTRIBUTOR_CONFIG = {
    "agent_id": "gastown_task_distributor",
    "name": "Task Distributor",
}
