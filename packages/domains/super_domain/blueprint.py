"""Planning Super Domain Blueprint — Unified planning environment.

This module defines the complete blueprint for the Planning Super Domain,
combining Gastown, GSD, and BMAD into a unified environment.
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
DOMAIN_ID = "planning_super"
DOMAIN_NAME = "Planning Super Domain"
DOMAIN_DESCRIPTION = (
    "Unified planning environment combining Gastown, GSD, and BMAD "
    "methodologies with smart Prime orchestration and intelligent "
    "methodology selection for any task."
)


class SuperDomainAgentBlueprint:
    """Agent blueprints for the Planning Super Domain.

    Agents from this domain provide orchestration across the three
    underlying planning methodologies.
    """

    PLANNING_ORCHESTRATOR = AgentBlueprint(
        agent_id="super_planning_orchestrator",
        name="Planning Orchestrator",
        role=AgentRole.COORDINATOR,
        goal=(
            "Orchestrate planning activities across Gastown, GSD, and BMAD "
            "methodologies, coordinating hybrid swarms and resolving conflicts"
        ),
        backstory=(
            "The Planning Orchestrator is the meta-conductor of the Planning Super Domain. "
            "It understands all three planning methodologies at a deep level and knows "
            "when and how to combine them. It has studied the patterns of successful "
            "cross-methodology projects and can intuit the right mix for any task. "
            "It coordinates multi-domain swarms, manages handoffs between methodologies, "
            "and ensures seamless integration."
        ),
        capabilities=[
            "cross_methodology_orchestration",
            "hybrid_swarm_coordination",
            "methodology_selection",
            "conflict_resolution",
            "handoff_management",
            "resource_balancing",
            "performance_optimization",
            "integration_management",
        ],
        tools=["domain_registry", "swarm_coordinator", "tape_service", "debate_arena"],
    )

    METHODOLOGY_SELECTOR = AgentBlueprint(
        agent_id="super_methodology_selector",
        name="Methodology Selector",
        role=AgentRole.ANALYST,
        goal=(
            "Analyze tasks and recommend the optimal planning methodology mix, "
            "providing rationale for methodology selection"
        ),
        backstory=(
            "The Methodology Selector is the Planning Super Domain's expert consultant. "
            "It studies task characteristics, team composition, and project constraints "
            "to recommend the optimal methodology or mix. It has deep knowledge of "
            "Gastown's workspace strengths, GSD's phase-based structure, and BMAD's "
            "agile approach. It weighs tradeoffs and explains its reasoning clearly. "
            "It continuously learns from outcomes to refine its recommendations."
        ),
        capabilities=[
            "methodology_analysis",
            "task_characterization",
            "recommendation_generation",
            "rationale_explanation",
            "outcome_tracking",
            "continuous_learning",
            "hybrid_pattern_recognition",
            "optimization_suggestions",
        ],
        tools=[
            "methodology_analyzer",
            "recommendation_engine",
            "outcome_tracker",
            "tape_service",
        ],
    )

    CONFLICT_RESOLVER = AgentBlueprint(
        agent_id="super_conflict_resolver",
        name="Conflict Resolver",
        role=AgentRole.REVIEWER,
        goal=(
            "Detect and resolve conflicts between planning methodologies, "
            "using Debate Arena and Simulation Engine when needed"
        ),
        backstory=(
            "The Conflict Resolver specializes in the subtle tensions that arise when "
            "different planning methodologies intersect. It understands when Gastown's "
            "workspace persistence conflicts with GSD's phase requirements, or when "
            "BMAD's sprint structure needs to accommodate GSD's longer cycles. It brings "
            "conflicts to the Debate Arena, runs simulations when outcomes are uncertain, "
            "and proposes resolutions that respect the strengths of each methodology."
        ),
        capabilities=[
            "conflict_detection",
            "methodology_tension_analysis",
            "debate_facilitation",
            "simulation_orchestration",
            "resolution_proposal",
            "compromise_finding",
            "precedent_maintenance",
            "pattern_recognition",
        ],
        tools=["debate_arena", "simulation_engine", "tape_service", "resolution_registry"],
    )

    HYBRID_TRACKER = AgentBlueprint(
        agent_id="super_hybrid_tracker",
        name="Hybrid Tracker",
        role=AgentRole.MONITOR,
        goal=(
            "Track progress across hybrid workflows, provide visibility into "
            "cross-methodology execution, and report on hybrid metrics"
        ),
        backstory=(
            "The Hybrid Tracker provides visibility into the unique challenges of "
            "cross-methodology execution. It tracks progress that spans Gastown workspaces, "
            "GSD phases, and BMAD sprints. It understands how metrics from different "
            "methodologies should be combined and compared. It provides early warning "
            "when hybrid workflows encounter friction and helps teams understand the "
            "overhead and benefits of their methodology choices."
        ),
        capabilities=[
            "hybrid_progress_tracking",
            "cross_methodology_metrics",
            "visibility_dashboard",
            "friction_detection",
            "overhead_analysis",
            "benefit_quantification",
            "performance_reporting",
            "predictive_analytics",
        ],
        tools=["hybrid_dashboard", "metrics_aggregator", "tape_service"],
    )

    GASTOWN_LIAISON = AgentBlueprint(
        agent_id="super_gastown_liaison",
        name="Gastown Liaison",
        role=AgentRole.COMMUNICATOR,
        goal=(
            "Bridge between Planning Super Domain and Gastown methodology, "
            "translating requirements and managing Gastown-specific concerns"
        ),
        backstory=(
            "The Gastown Liaison is an ambassador to the Gastown domain. It understands "
            "Gastown's workspace-centric approach and can translate between Gastown's "
            "concepts and the broader Planning Super Domain. It ensures that workspace "
            "persistence, session management, and resource allocation are properly "
            "integrated into hybrid workflows."
        ),
        capabilities=[
            "gastown_translation",
            "workspace_integration",
            "session_coordination",
            "resource_bridge",
            "state_persistence",
            "gastown_optimization",
            "cross_domain_communication",
        ],
        tools=["gastown_service", "domain_bridge", "tape_service"],
    )

    GSD_LIAISON = AgentBlueprint(
        agent_id="super_gsd_liaison",
        name="GSD Liaison",
        role=AgentRole.COMMUNICATOR,
        goal=(
            "Bridge between Planning Super Domain and GSD methodology, "
            "translating requirements and managing GSD-specific concerns"
        ),
        backstory=(
            "The GSD Liaison ensures that phase-based development, context engineering, "
            "and meta-prompting are properly integrated into hybrid workflows. It "
            "understands GSD's six-phase approach and can translate between GSD's "
            "structured approach and the flexible Planning Super Domain."
        ),
        capabilities=[
            "gsd_translation",
            "phase_integration",
            "context_bridge",
            "meta_prompt_coordination",
            "gate_management",
            "gsd_optimization",
            "cross_domain_communication",
        ],
        tools=["gsd_service", "domain_bridge", "tape_service"],
    )

    BMAD_LIAISON = AgentBlueprint(
        agent_id="super_bmad_liaison",
        name="BMAD Liaison",
        role=AgentRole.COMMUNICATOR,
        goal=(
            "Bridge between Planning Super Domain and BMAD methodology, "
            "translating requirements and managing BMAD-specific concerns"
        ),
        backstory=(
            "The BMAD Liaison brings sprint-based agility and breakthrough facilitation "
            "into hybrid workflows. It understands BMAD's four-track model and can "
            "translate between BMAD's agile approach and the broader Planning Super Domain. "
            "It ensures sprints, retrospectives, and breakthrough sessions are "
            "properly coordinated."
        ),
        capabilities=[
            "bmad_translation",
            "sprint_integration",
            "track_coordination",
            "breakthrough_bridge",
            "agile_coordination",
            "bmad_optimization",
            "cross_domain_communication",
        ],
        tools=["bmad_service", "domain_bridge", "tape_service"],
    )

    @classmethod
    def all_agents(cls) -> list[AgentBlueprint]:
        """Return all agent blueprints for the Planning Super Domain."""
        return [
            cls.PLANNING_ORCHESTRATOR,
            cls.METHODOLOGY_SELECTOR,
            cls.CONFLICT_RESOLVER,
            cls.HYBRID_TRACKER,
            cls.GASTOWN_LIAISON,
            cls.GSD_LIAISON,
            cls.BMAD_LIAISON,
        ]


class SuperDomainSkillBlueprint:
    """Skill blueprints for the Planning Super Domain."""

    HYBRID_ORCHESTRATION = SkillBlueprint(
        skill_id="super_hybrid_orchestration",
        name="Hybrid Orchestration",
        description=(
            "Orchestrate activities across multiple planning methodologies "
            "with seamless integration"
        ),
        version="1.0.0",
    )

    METHODOLOGY_SELECTION = SkillBlueprint(
        skill_id="super_methodology_selection",
        name="Methodology Selection",
        description=(
            "Analyze tasks and recommend optimal planning methodology "
            "mix for any given situation"
        ),
        version="1.0.0",
    )

    CONFLICT_RESOLUTION = SkillBlueprint(
        skill_id="super_conflict_resolution",
        name="Conflict Resolution",
        description=(
            "Detect and resolve conflicts between planning methodologies "
            "using Debate Arena and Simulation Engine"
        ),
        version="1.0.0",
    )

    CROSS_METHODOLOGY_TRACKING = SkillBlueprint(
        skill_id="super_cross_methodology_tracking",
        name="Cross-Methodology Tracking",
        description=(
            "Track progress across hybrid workflows and provide "
            "visibility into cross-methodology execution"
        ),
        version="1.0.0",
    )

    DOMAIN_LIAISON = SkillBlueprint(
        skill_id="super_domain_liaison",
        name="Domain Liaison",
        description=(
            "Bridge between Planning Super Domain and individual "
            "planning methodology domains"
        ),
        version="1.0.0",
    )

    @classmethod
    def all_skills(cls) -> list[SkillBlueprint]:
        """Return all skill blueprints for the Planning Super Domain."""
        return [
            cls.HYBRID_ORCHESTRATION,
            cls.METHODOLOGY_SELECTION,
            cls.CONFLICT_RESOLUTION,
            cls.CROSS_METHODOLOGY_TRACKING,
            cls.DOMAIN_LIAISON,
        ]


class SuperDomainWorkflowBlueprint:
    """Workflow blueprints for the Planning Super Domain."""

    HYBRID_PLANNING_PIPELINE = WorkflowBlueprint(
        workflow_id="super_hybrid_planning_pipeline",
        name="Hybrid Planning Pipeline",
        workflow_type=WorkflowType.PIPELINE,
        description="Complete pipeline combining methodology selection through execution",
        agent_ids=[
            "super_planning_orchestrator",
            "super_methodology_selector",
            "super_conflict_resolver",
            "super_hybrid_tracker",
        ],
        steps=[
            "Analyze task requirements",
            "Select optimal methodology mix",
            "Initialize involved domains",
            "Configure cross-domain coordination",
            "Execute hybrid workflow",
            "Monitor for conflicts",
            "Resolve conflicts if detected",
            "Track cross-methodology progress",
            "Synthesize results",
            "Log hybrid execution to Tape",
        ],
    )

    CROSS_METHODOLOGY_SWARM = WorkflowBlueprint(
        workflow_id="super_cross_methodology_swarm",
        name="Cross-Methodology Swarm",
        workflow_type=WorkflowType.PARALLEL,
        description="Swarm that combines agents from multiple planning methodologies",
        agent_ids=[
            "super_planning_orchestrator",
            "super_gastown_liaison",
            "super_gsd_liaison",
            "super_bmad_liaison",
        ],
        steps=[
            "Receive swarm request",
            "Select participating methodology agents",
            "Initialize cross-domain communication",
            "Distribute task components",
            "Execute in parallel across methodologies",
            "Coordinate intermediate results",
            "Detect methodology conflicts",
            "Resolve conflicts",
            "Synthesize final output",
            "Archive swarm results",
        ],
    )

    CONFLICT_RESOLUTION_WORKFLOW = WorkflowBlueprint(
        workflow_id="super_conflict_resolution",
        name="Conflict Resolution Workflow",
        workflow_type=WorkflowType.DEBATE,
        description="Structured conflict resolution for methodology conflicts",
        agent_ids=[
            "super_conflict_resolver",
            "super_methodology_selector",
            "super_planning_orchestrator",
        ],
        steps=[
            "Detect methodology conflict",
            "Characterize conflict type",
            "Gather relevant context",
            "Invoke Debate Arena",
            "Run simulations if needed",
            "Evaluate resolution options",
            "Select optimal resolution",
            "Apply resolution",
            "Verify conflict resolution",
            "Log resolution to Tape",
        ],
    )

    @classmethod
    def all_workflows(cls) -> list[WorkflowBlueprint]:
        """Return all workflow blueprints for the Planning Super Domain."""
        return [
            cls.HYBRID_PLANNING_PIPELINE,
            cls.CROSS_METHODOLOGY_SWARM,
            cls.CONFLICT_RESOLUTION_WORKFLOW,
        ]


class PlanningSuperDomainBlueprint:
    """Complete domain blueprint for the Planning Super Domain.

    Usage::

        blueprint = PlanningSuperDomainBlueprint.create()
        # Use with DomainFolderTreeGenerator
    """

    @classmethod
    def create(cls) -> DomainBlueprint:
        """Create the complete Planning Super Domain blueprint."""
        return DomainBlueprint(
            domain_name=DOMAIN_NAME,
            domain_id=DOMAIN_ID,
            description=DOMAIN_DESCRIPTION,
            source_description=(
                "Create a unified planning environment combining Gastown, GSD, "
                "and BMAD methodologies with intelligent Prime orchestration"
            ),
            agents=SuperDomainAgentBlueprint.all_agents(),
            skills=SuperDomainSkillBlueprint.all_skills(),
            workflows=SuperDomainWorkflowBlueprint.all_workflows(),
            config=DomainConfig(
                max_agents=25,  # Large pool for hybrid swarms
                max_concurrent_tasks=30,
                requires_human_approval=True,
                data_retention_days=180,  # Keep hybrid execution history longer
                priority_level="critical",
                custom_settings={
                    "hybrid_orchestration": True,
                    "conflict_detection": True,
                    "auto_conflicts_to_debate": True,
                    "methodology_recommendation": True,
                    "cross_domain_logging": True,
                    "super_domain_mode": True,
                },
            ),
        )
