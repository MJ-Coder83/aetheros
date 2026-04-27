"""Gastown Domain Skills.

This module defines the specialized skills for the Gastown multi-agent
workspace orchestration domain.
"""

from __future__ import annotations

__all__ = [
    "AGENT_COORDINATION_SKILL",
    "RESOURCE_ALLOCATION_SKILL",
    "SESSION_MANAGEMENT_SKILL",
    "TASK_DISTRIBUTION_SKILL",
    "WORKSPACE_ORCHESTRATION_SKILL",
]

# Skill configuration exports
WORKSPACE_ORCHESTRATION_SKILL = {
    "skill_id": "gastown_workspace_orchestration",
    "name": "Workspace Orchestration",
}

AGENT_COORDINATION_SKILL = {
    "skill_id": "gastown_agent_coordination",
    "name": "Agent Coordination",
}

SESSION_MANAGEMENT_SKILL = {
    "skill_id": "gastown_session_management",
    "name": "Session Management",
}

RESOURCE_ALLOCATION_SKILL = {
    "skill_id": "gastown_resource_allocation",
    "name": "Resource Allocation",
}

TASK_DISTRIBUTION_SKILL = {
    "skill_id": "gastown_task_distribution",
    "name": "Task Distribution",
}
