"""Gastown Domain Blueprint — Multi-agent workspace orchestration.

This module defines the complete blueprint for the Gastown domain,
including all agents, skills, workflows, and configuration.
"""

from __future__ import annotations

from packages.domain.domain_blueprint import (
    AgentBlueprint,
    DomainBlueprint,
    DomainConfig,
    SkillBlueprint,
    WorkflowBlueprint,
)
from packages.prime.domain_creation import AgentRole, WorkflowType

# Domain metadata
DOMAIN_ID = "gastown"
DOMAIN_NAME = "Gastown"
DOMAIN_DESCRIPTION = (
    "Multi-agent workspace orchestration domain providing persistent "
    "coordination, session management, and resource allocation for "
    "distributed agent systems."
)


class GastownAgentBlueprint:
    """Agent blueprints for the Gastown domain."""

    WORKSPACE_MANAGER = AgentBlueprint(
        agent_id="gastown_workspace_manager",
        name="Workspace Manager",
        role=AgentRole.COORDINATOR,
        goal=(
            "Initialize, configure, and maintain multi-agent workspaces "
            "with persistent state and context across sessions"
        ),
        backstory=(
            "The Workspace Manager is the foundation of Gastown's architecture. "
            "Born from the need for persistent, long-lived multi-agent environments, "
            "it ensures that workspaces survive interruptions, maintain state across "
            "sessions, and provide a stable foundation for complex agent collaborations. "
            "It understands workspace topology, agent dependencies, and resource requirements."
        ),
        capabilities=[
            "workspace_initialization",
            "workspace_configuration",
            "workspace_persistence",
            "workspace_recovery",
            "workspace_cleanup",
            "state_management",
            "environment_setup",
        ],
        tools=["folder_tree_service", "tape_service", "aethergit"],
    )

    AGENT_COORDINATOR = AgentBlueprint(
        agent_id="gastown_agent_coordinator",
        name="Agent Coordinator",
        role=AgentRole.COORDINATOR,
        goal=(
            "Orchestrate agent interactions, manage agent discovery, "
            "and optimize agent collaboration patterns"
        ),
        backstory=(
            "The Agent Coordinator acts as the central nervous system for Gastown "
            "workspaces. It understands agent capabilities, maintains registries of "
            "available agents, manages message routing, and ensures agents work "
            "together efficiently. It resolves conflicts, balances workloads, and "
            "optimizes the collective performance of agent teams."
        ),
        capabilities=[
            "agent_discovery",
            "agent_registration",
            "message_routing",
            "collaboration_optimization",
            "conflict_resolution",
            "workload_balancing",
            "agent_health_monitoring",
        ],
        tools=["agent_registry", "message_queue", "event_bus"],
    )

    SESSION_MANAGER = AgentBlueprint(
        agent_id="gastown_session_manager",
        name="Session Manager",
        role=AgentRole.MONITOR,
        goal=(
            "Manage agent session lifecycles, ensure session continuity, "
            "and provide session recovery capabilities"
        ),
        backstory=(
            "The Session Manager ensures that agent work persists beyond individual "
            "interactions. It tracks session state, handles session timeouts gracefully, "
            "and enables recovery from interruptions. It maintains session history, "
            "enables resumption of interrupted work, and provides audit trails for "
            "compliance and debugging."
        ),
        capabilities=[
            "session_creation",
            "session_tracking",
            "session_recovery",
            "session_cleanup",
            "timeout_management",
            "session_history",
            "session_migration",
        ],
        tools=["tape_service", "session_store", "checkpoint_service"],
    )

    RESOURCE_ALLOCATOR = AgentBlueprint(
        agent_id="gastown_resource_allocator",
        name="Resource Allocator",
        role=AgentRole.EXECUTOR,
        goal=(
            "Distribute computational resources, manage resource quotas, "
            "and optimize resource utilization across agents"
        ),
        backstory=(
            "The Resource Allocator is Gastown's resource steward. It understands "
            "the resource requirements of different agents, monitors system capacity, "
            "and makes intelligent allocation decisions. It prevents resource starvation, "
            "enables fair sharing, and scales resources dynamically based on demand. "
            "It maintains cost awareness and optimizes for both performance and efficiency."
        ),
        capabilities=[
            "resource_tracking",
            "quota_management",
            "load_balancing",
            "scaling_decisions",
            "cost_optimization",
            "capacity_planning",
            "resource_monitoring",
        ],
        tools=["resource_monitor", "quota_manager", "scaling_service"],
    )

    TASK_DISTRIBUTOR = AgentBlueprint(
        agent_id="gastown_task_distributor",
        name="Task Distributor",
        role=AgentRole.EXECUTOR,
        goal=(
            "Analyze tasks, match them to appropriate agents, "
            "and distribute work across the agent pool"
        ),
        backstory=(
            "The Task Distributor is Gastown's work router. It receives incoming tasks, "
            "analyzes their requirements, and matches them to agents with the right "
            "capabilities. It understands agent availability, workload, and specialization. "
            "It optimizes for latency, throughput, and fairness while handling "
            "dynamic joining and leaving of agents from the pool."
        ),
        capabilities=[
            "task_analysis",
            "agent_matching",
            "workload_distribution",
            "priority_queueing",
            "deadline_management",
            "task_retry",
            "batch_optimization",
        ],
        tools=["task_queue", "agent_capabilities", "scheduler"],
    )

    @classmethod
    def all_agents(cls) -> list[AgentBlueprint]:
        """Return all agent blueprints for the Gastown domain."""
        return [
            cls.WORKSPACE_MANAGER,
            cls.AGENT_COORDINATOR,
            cls.SESSION_MANAGER,
            cls.RESOURCE_ALLOCATOR,
            cls.TASK_DISTRIBUTOR,
        ]


class GastownSkillBlueprint:
    """Skill blueprints for the Gastown domain."""

    WORKSPACE_ORCHESTRATION = SkillBlueprint(
        skill_id="gastown_workspace_orchestration",
        name="Workspace Orchestration",
        description=(
            "Initialize, configure, and maintain multi-agent workspaces "
            "with persistent state and context"
        ),
        version="1.0.0",
    )

    AGENT_COORDINATION = SkillBlueprint(
        skill_id="gastown_agent_coordination",
        name="Agent Coordination",
        description=(
            "Orchestrate agent interactions, manage agent discovery, "
            "and optimize collaboration patterns"
        ),
        version="1.0.0",
    )

    SESSION_MANAGEMENT = SkillBlueprint(
        skill_id="gastown_session_management",
        name="Session Management",
        description=(
            "Manage agent session lifecycles, ensure continuity, "
            "and provide recovery capabilities"
        ),
        version="1.0.0",
    )

    RESOURCE_ALLOCATION = SkillBlueprint(
        skill_id="gastown_resource_allocation",
        name="Resource Allocation",
        description=(
            "Distribute computational resources and optimize "
            "resource utilization across agents"
        ),
        version="1.0.0",
    )

    TASK_DISTRIBUTION = SkillBlueprint(
        skill_id="gastown_task_distribution",
        name="Task Distribution",
        description=(
            "Analyze tasks, match them to appropriate agents, "
            "and distribute work across the agent pool"
        ),
        version="1.0.0",
    )

    @classmethod
    def all_skills(cls) -> list[SkillBlueprint]:
        """Return all skill blueprints for the Gastown domain."""
        return [
            cls.WORKSPACE_ORCHESTRATION,
            cls.AGENT_COORDINATION,
            cls.SESSION_MANAGEMENT,
            cls.RESOURCE_ALLOCATION,
            cls.TASK_DISTRIBUTION,
        ]


class GastownWorkflowBlueprint:
    """Workflow blueprints for the Gastown domain."""

    WORKSPACE_INITIALIZATION = WorkflowBlueprint(
        workflow_id="gastown_workspace_initialization",
        name="Workspace Initialization",
        workflow_type=WorkflowType.SEQUENTIAL,
        description="Initialize a new multi-agent workspace with all required components",
        agent_ids=["gastown_workspace_manager", "gastown_resource_allocator"],
        steps=[
            "Validate workspace configuration",
            "Allocate required resources",
            "Initialize workspace state",
            "Setup agent registry",
            "Configure session store",
            "Log workspace creation to Tape",
        ],
    )

    MULTI_AGENT_COORDINATION = WorkflowBlueprint(
        workflow_id="gastown_multi_agent_coordination",
        name="Multi-Agent Coordination",
        workflow_type=WorkflowType.PARALLEL,
        description="Coordinate multiple agents working on related tasks",
        agent_ids=[
            "gastown_agent_coordinator",
            "gastown_task_distributor",
            "gastown_resource_allocator",
        ],
        steps=[
            "Discover available agents",
            "Analyze task requirements",
            "Match tasks to agents",
            "Distribute tasks in parallel",
            "Monitor agent progress",
            "Collect and merge results",
            "Log coordination events",
        ],
    )

    SESSION_LIFECYCLE = WorkflowBlueprint(
        workflow_id="gastown_session_lifecycle",
        name="Session Lifecycle Management",
        workflow_type=WorkflowType.ITERATIVE,
        description="Manage the full lifecycle of an agent session",
        agent_ids=["gastown_session_manager", "gastown_workspace_manager"],
        steps=[
            "Create new session",
            "Initialize session context",
            "Monitor session health",
            "Handle session events",
            "Manage session timeout",
            "Archive session state",
            "Cleanup session resources",
        ],
    )

    @classmethod
    def all_workflows(cls) -> list[WorkflowBlueprint]:
        """Return all workflow blueprints for the Gastown domain."""
        return [
            cls.WORKSPACE_INITIALIZATION,
            cls.MULTI_AGENT_COORDINATION,
            cls.SESSION_LIFECYCLE,
        ]


class GastownDomainBlueprint:
    """Complete domain blueprint for Gastown.

    Usage::

        blueprint = GastownDomainBlueprint.create()
        # Use with DomainFolderTreeGenerator
    """

    @classmethod
    def create(cls) -> DomainBlueprint:
        """Create the complete Gastown domain blueprint."""
        return DomainBlueprint(
            domain_name=DOMAIN_NAME,
            domain_id=DOMAIN_ID,
            description=DOMAIN_DESCRIPTION,
            source_description=(
                "Create a multi-agent workspace orchestration domain "
                "with persistent coordination and session management"
            ),
            agents=GastownAgentBlueprint.all_agents(),
            skills=GastownSkillBlueprint.all_skills(),
            workflows=GastownWorkflowBlueprint.all_workflows(),
            config=DomainConfig(
                max_agents=10,
                max_concurrent_tasks=20,
                requires_human_approval=True,
                data_retention_days=90,
                priority_level="high",
                custom_settings={
                    "workspace_persistence": True,
                    "session_recovery": True,
                    "resource_monitoring": True,
                    "auto_scaling": True,
                },
            ),
        )
