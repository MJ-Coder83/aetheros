"""Gastown Domain Workflows.

This module defines the specialized workflows for the Gastown multi-agent
workspace orchestration domain.
"""

from __future__ import annotations

__all__ = [
    "MULTI_AGENT_COORDINATION_WORKFLOW",
    "SESSION_LIFECYCLE_WORKFLOW",
    "WORKSPACE_INITIALIZATION_WORKFLOW",
]

# Workflow configuration exports
WORKSPACE_INITIALIZATION_WORKFLOW = {
    "workflow_id": "gastown_workspace_initialization",
    "name": "Workspace Initialization",
}

MULTI_AGENT_COORDINATION_WORKFLOW = {
    "workflow_id": "gastown_multi_agent_coordination",
    "name": "Multi-Agent Coordination",
}

SESSION_LIFECYCLE_WORKFLOW = {
    "workflow_id": "gastown_session_lifecycle",
    "name": "Session Lifecycle Management",
}
