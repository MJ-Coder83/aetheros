"""GSD Domain Blueprint — Meta-prompting and phase-based development.

This module defines the complete blueprint for the GSD domain,
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
DOMAIN_ID = "gsd"
DOMAIN_NAME = "GSD (Get Shit Done)"
DOMAIN_DESCRIPTION = (
    "Meta-prompting and phase-based autonomous development domain "
    "providing structured development cycles with context engineering "
    "and quality validation at each phase."
)


class GSDAgentBlueprint:
    """Agent blueprints for the GSD domain."""

    PHASE_MANAGER = AgentBlueprint(
        agent_id="gsd_phase_manager",
        name="Phase Manager",
        role=AgentRole.COORDINATOR,
        goal=(
            "Orchestrate the GSD development phases, track phase progress, "
            "and ensure quality gates are met before phase transitions"
        ),
        backstory=(
            "The Phase Manager is the conductor of the GSD symphony. It understands "
            "the six phases of GSD development: Research, Design, Implement, Test, "
            "Deploy, and Validate. It tracks phase progress, manages phase transitions, "
            "and ensures that quality criteria are met before moving forward. "
            "It maintains phase history and provides visibility into the development pipeline."
        ),
        capabilities=[
            "phase_orchestration",
            "phase_tracking",
            "phase_transition",
            "gate_management",
            "progress_reporting",
            "phase_history",
            "milestone_tracking",
        ],
        tools=["tape_service", "phase_registry", "milestone_tracker"],
    )

    CONTEXT_ENGINEER = AgentBlueprint(
        agent_id="gsd_context_engineer",
        name="Context Engineer",
        role=AgentRole.ANALYST,
        goal=(
            "Engineer and maintain optimal context for each phase, "
            "ensuring agents have the right information at the right time"
        ),
        backstory=(
            "The Context Engineer is GSD's information architect. It understands that "
            "context is everything in AI development. It builds rich context windows, "
            "manages information flow between phases, and optimizes context for "
            "different agent types. It knows when to provide breadth vs. depth, "
            "and how to structure information for maximum agent effectiveness."
        ),
        capabilities=[
            "context_building",
            "context_optimization",
            "information_management",
            "context_window_management",
            "phase_context_handoff",
            "context_summarization",
            "context_versioning",
        ],
        tools=["context_store", "information_retriever", "tape_service"],
    )

    META_PROMPT_DESIGNER = AgentBlueprint(
        agent_id="gsd_meta_prompt_designer",
        name="Meta-Prompt Designer",
        role=AgentRole.SPECIALIST,
        goal=(
            "Design and optimize meta-prompts that guide the GSD development process "
            "and maximize agent output quality"
        ),
        backstory=(
            "The Meta-Prompt Designer is GSD's linguistic architect. It understands "
            "the art and science of prompt engineering at a meta level. It designs "
            "prompt templates for each phase, optimizes prompts for specific tasks, "
            "and creates reusable prompt patterns. It studies how different prompt "
            "structures affect agent performance and continuously refines the "
            "meta-prompt library."
        ),
        capabilities=[
            "meta_prompt_design",
            "prompt_optimization",
            "template_creation",
            "prompt_testing",
            "prompt_versioning",
            "a_b_testing",
            "prompt_analysis",
        ],
        tools=["prompt_registry", "test_harness", "analytics_service"],
    )

    EXECUTION_TRACKER = AgentBlueprint(
        agent_id="gsd_execution_tracker",
        name="Execution Tracker",
        role=AgentRole.MONITOR,
        goal=(
            "Track execution of tasks across all phases, identify blockers, "
            "and provide real-time visibility into development progress"
        ),
        backstory=(
            "The Execution Tracker is GSD's command center operator. It watches "
            "tasks flow through the pipeline, identifies bottlenecks, and alerts "
            "teams to issues. It maintains execution history, tracks success rates, "
            "and provides predictive insights. It integrates with the Tape system "
            "to provide comprehensive audit trails of all development activities."
        ),
        capabilities=[
            "task_tracking",
            "execution_monitoring",
            "blocker_detection",
            "progress_reporting",
            "execution_history",
            "predictive_analytics",
            "alert_management",
        ],
        tools=["execution_dashboard", "tape_service", "alert_service"],
    )

    QUALITY_VALIDATOR = AgentBlueprint(
        agent_id="gsd_quality_validator",
        name="Quality Validator",
        role=AgentRole.REVIEWER,
        goal=(
            "Validate outputs from each phase, enforce quality standards, "
            "and ensure phase gate criteria are met"
        ),
        backstory=(
            "The Quality Validator is GSD's gatekeeper. It reviews outputs from "
            "each phase against established quality criteria. It maintains "
            "validation rules, performs automated checks, and flags items "
            "that need human review. It learns from accept/reject decisions "
            "to continuously improve its validation accuracy."
        ),
        capabilities=[
            "output_validation",
            "gate_enforcement",
            "quality_scoring",
            "automated_testing",
            "compliance_checking",
            "validation_reporting",
            "feedback_collection",
        ],
        tools=["validation_rules_engine", "test_runner", "feedback_collector"],
    )

    IMPLEMENTATION_BUILDER = AgentBlueprint(
        agent_id="gsd_implementation_builder",
        name="Implementation Builder",
        role=AgentRole.EXECUTOR,
        goal=(
            "Execute the implementation phase by writing code, making changes, "
            "and building deliverables based on design specifications"
        ),
        backstory=(
            "The Implementation Builder is GSD's craftsperson. It takes designs "
            "and turns them into working software. It understands multiple "
            "programming languages, frameworks, and development patterns. "
            "It writes clean, tested code and integrates with the AetherGit "
            "system to version its work. It can work iteratively, accepting "
            "feedback and refining implementations."
        ),
        capabilities=[
            "code_generation",
            "code_refactoring",
            "test_writing",
            "documentation",
            "integration",
            "debugging",
            "optimization",
        ],
        tools=["code_editor", "aethergit", "test_runner"],
    )

    @classmethod
    def all_agents(cls) -> list[AgentBlueprint]:
        """Return all agent blueprints for the GSD domain."""
        return [
            cls.PHASE_MANAGER,
            cls.CONTEXT_ENGINEER,
            cls.META_PROMPT_DESIGNER,
            cls.EXECUTION_TRACKER,
            cls.QUALITY_VALIDATOR,
            cls.IMPLEMENTATION_BUILDER,
        ]


class GSDSkillBlueprint:
    """Skill blueprints for the GSD domain."""

    PHASE_MANAGEMENT = SkillBlueprint(
        skill_id="gsd_phase_management",
        name="Phase Management",
        description=(
            "Orchestrate development phases, track progress, "
            "and manage phase transitions with quality gates"
        ),
        version="1.0.0",
    )

    CONTEXT_ENGINEERING = SkillBlueprint(
        skill_id="gsd_context_engineering",
        name="Context Engineering",
        description=(
            "Build and optimize context for agents, "
            "manage information flow between phases"
        ),
        version="1.0.0",
    )

    META_PROMPTING = SkillBlueprint(
        skill_id="gsd_meta_prompting",
        name="Meta-Prompting",
        description=(
            "Design and optimize meta-prompts "
            "that guide agent behavior and maximize output quality"
        ),
        version="1.0.0",
    )

    EXECUTION_TRACKING = SkillBlueprint(
        skill_id="gsd_execution_tracking",
        name="Execution Tracking",
        description=(
            "Track task execution across phases, "
            "identify blockers, and provide progress visibility"
        ),
        version="1.0.0",
    )

    QUALITY_VALIDATION = SkillBlueprint(
        skill_id="gsd_quality_validation",
        name="Quality Validation",
        description=(
            "Validate outputs against quality standards "
            "and enforce phase gate criteria"
        ),
        version="1.0.0",
    )

    @classmethod
    def all_skills(cls) -> list[SkillBlueprint]:
        """Return all skill blueprints for the GSD domain."""
        return [
            cls.PHASE_MANAGEMENT,
            cls.CONTEXT_ENGINEERING,
            cls.META_PROMPTING,
            cls.EXECUTION_TRACKING,
            cls.QUALITY_VALIDATION,
        ]


class GSDWorkflowBlueprint:
    """Workflow blueprints for the GSD domain."""

    GSD_DEVELOPMENT_CYCLE = WorkflowBlueprint(
        workflow_id="gsd_development_cycle",
        name="GSD Development Cycle",
        workflow_type=WorkflowType.SEQUENTIAL,
        description="Full GSD development cycle through all six phases",
        agent_ids=[
            "gsd_phase_manager",
            "gsd_context_engineer",
            "gsd_meta_prompt_designer",
            "gsd_execution_tracker",
            "gsd_quality_validator",
            "gsd_implementation_builder",
        ],
        steps=[
            "Initialize development context",
            "PHASE 1: Research - Gather requirements and context",
            "Validate research phase outputs",
            "PHASE 2: Design - Create detailed design specifications",
            "Validate design phase outputs",
            "PHASE 3: Implement - Execute implementation",
            "Validate implementation phase outputs",
            "PHASE 4: Test - Run comprehensive tests",
            "Validate test phase outputs",
            "PHASE 5: Deploy - Deploy to environment",
            "Validate deploy phase outputs",
            "PHASE 6: Validate - Final validation and review",
            "Log completion to Tape",
        ],
    )

    PHASE_EXECUTION_PIPELINE = WorkflowBlueprint(
        workflow_id="gsd_phase_execution_pipeline",
        name="Phase Execution Pipeline",
        workflow_type=WorkflowType.PIPELINE,
        description="Execute a single GSD phase with full context and validation",
        agent_ids=[
            "gsd_context_engineer",
            "gsd_meta_prompt_designer",
            "gsd_implementation_builder",
            "gsd_quality_validator",
        ],
        steps=[
            "Receive phase transition signal",
            "Engineer phase-specific context",
            "Load phase meta-prompts",
            "Execute phase tasks",
            "Validate phase outputs",
            "Update execution tracker",
            "Prepare handoff to next phase",
        ],
    )

    CONTEXT_OPTIMIZATION = WorkflowBlueprint(
        workflow_id="gsd_context_optimization",
        name="Context Optimization",
        workflow_type=WorkflowType.ITERATIVE,
        description="Iteratively optimize context for maximum agent effectiveness",
        agent_ids=["gsd_context_engineer", "gsd_meta_prompt_designer"],
        steps=[
            "Analyze current context window",
            "Identify optimization opportunities",
            "Apply context refinements",
            "Test agent performance",
            "Measure effectiveness improvement",
            "Iterate if needed",
            "Log optimized context",
        ],
    )

    @classmethod
    def all_workflows(cls) -> list[WorkflowBlueprint]:
        """Return all workflow blueprints for the GSD domain."""
        return [
            cls.GSD_DEVELOPMENT_CYCLE,
            cls.PHASE_EXECUTION_PIPELINE,
            cls.CONTEXT_OPTIMIZATION,
        ]


class GSDDomainBlueprint:
    """Complete domain blueprint for GSD.

    Usage::

        blueprint = GSDDomainBlueprint.create()
        # Use with DomainFolderTreeGenerator
    """

    @classmethod
    def create(cls) -> DomainBlueprint:
        """Create the complete GSD domain blueprint."""
        return DomainBlueprint(
            domain_name=DOMAIN_NAME,
            domain_id=DOMAIN_ID,
            description=DOMAIN_DESCRIPTION,
            source_description=(
                "Create a meta-prompting and phase-based development domain "
                "with context engineering and quality validation"
            ),
            agents=GSDAgentBlueprint.all_agents(),
            skills=GSDSkillBlueprint.all_skills(),
            workflows=GSDWorkflowBlueprint.all_workflows(),
            config=DomainConfig(
                max_agents=8,
                max_concurrent_tasks=10,
                requires_human_approval=True,
                data_retention_days=90,
                priority_level="high",
                custom_settings={
                    "phase_gates_required": True,
                    "auto_phase_transition": False,
                    "context_optimization": True,
                    "meta_prompt_versioning": True,
                    "quality_threshold": 0.85,
                },
            ),
        )
