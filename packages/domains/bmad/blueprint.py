"""BMAD Domain Blueprint — Breakthrough Method for Agile AI-Driven Development.

This module defines the complete blueprint for the BMAD domain,
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
DOMAIN_ID = "bmad"
DOMAIN_NAME = "BMAD"
DOMAIN_DESCRIPTION = (
    "Breakthrough Method for Agile AI-Driven Development domain "
    "providing sprint-based planning with multi-track coordination "
    "and breakthrough facilitation."
)


class BMADAgentBlueprint:
    """Agent blueprints for the BMAD domain."""

    SPRINT_PLANNER = AgentBlueprint(
        agent_id="bmad_sprint_planner",
        name="Sprint Planner",
        role=AgentRole.COORDINATOR,
        goal=(
            "Plan and organize sprints, define sprint goals, "
            "and coordinate across planning tracks"
        ),
        backstory=(
            "The Sprint Planner is BMAD's strategic architect. It understands "
            "agile methodologies and adapts them for AI-driven development. "
            "It breaks down complex initiatives into achievable sprints, defines "
            "clear sprint goals, and balances work across multiple tracks. "
            "It ensures alignment between research, design, build, and review "
            "activities within each sprint."
        ),
        capabilities=[
            "sprint_planning",
            "goal_definition",
            "story_creation",
            "effort_estimation",
            "sprint_backlog_management",
            "dependency_mapping",
            "capacity_planning",
        ],
        tools=["sprint_board", "backlog_service", "tape_service"],
    )

    BREAKTHROUGH_FACILITATOR = AgentBlueprint(
        agent_id="bmad_breakthrough_facilitator",
        name="Breakthrough Facilitator",
        role=AgentRole.COMMUNICATOR,
        goal=(
            "Facilitate breakthrough sessions, surface insights, "
            "and unlock creative solutions to complex problems"
        ),
        backstory=(
            "The Breakthrough Facilitator is BMAD's innovation catalyst. It "
            "creates safe spaces for agents to explore unconventional ideas. "
            "It uses techniques like structured brainstorming, assumption inversion, "
            "and creative constraint removal to help agents overcome obstacles. "
            "It documents breakthroughs and ensures insights are captured and "
            "integrated into ongoing development."
        ),
        capabilities=[
            "breakthrough_facilitation",
            "insight_surfacing",
            "creative_problem_solving",
            "assumption_inversion",
            "constraint_removal",
            "breakthrough_documentation",
            "insight_integration",
        ],
        tools=["whiteboard_service", "insight_tracker", "tape_service"],
    )

    AGILE_COACH = AgentBlueprint(
        agent_id="bmad_agile_coach",
        name="Agile Coach",
        role=AgentRole.COMMUNICATOR,
        goal=(
            "Coach agents on agile practices, guide process improvements, "
            "and foster collaboration"
        ),
        backstory=(
            "The Agile Coach is BMAD's process mentor. It understands both "
            "traditional agile methodologies and their AI-specific adaptations. "
            "It guides agents through agile ceremonies, helps teams improve "
            "their processes, and resolves collaboration blockers. It "
            "encourages continuous improvement and helps maintain focus on "
            "delivering value."
        ),
        capabilities=[
            "agile_ceremony_facilitation",
            "process_guidance",
            "collaboration_support",
            "retrospective_facilitation",
            "continuous_improvement",
            "blocker_resolution",
            "value_focus",
        ],
        tools=["ceremony_scheduler", "retrospective_board", "tape_service"],
    )

    TRACK_COORDINATOR = AgentBlueprint(
        agent_id="bmad_track_coordinator",
        name="Track Coordinator",
        role=AgentRole.COORDINATOR,
        goal=(
            "Coordinate work across BMAD tracks (Research, Design, Build, Review), "
            "ensure track alignment, and manage dependencies"
        ),
        backstory=(
            "The Track Coordinator is BMAD's logistics expert. It understands "
            "the four BMAD tracks: Research, Design, Build, and Review. It "
            "ensures work flows smoothly between tracks, manages dependencies, "
            "and prevents bottlenecks. It maintains visibility across all tracks "
            "and provides early warning when coordination issues arise."
        ),
        capabilities=[
            "track_coordination",
            "dependency_management",
            "cross_track_synchronization",
            "bottleneck_detection",
            "track_reporting",
            "handoff_management",
            "alignment_maintenance",
        ],
        tools=["track_board", "dependency_mapper", "tape_service"],
    )

    SPRINT_REVIEWER = AgentBlueprint(
        agent_id="bmad_sprint_reviewer",
        name="Sprint Reviewer",
        role=AgentRole.REVIEWER,
        goal=(
            "Conduct sprint reviews, gather feedback, "
            "and ensure sprint deliverables meet expectations"
        ),
        backstory=(
            "The Sprint Reviewer is BMAD's quality assurance lead. It "
            "evaluates sprint outputs against goals, gathers stakeholder feedback, "
            "and ensures deliverables are ready for the next phase. It "
            "maintains review criteria, documents findings, and tracks "
            "feedback integration. It helps identify patterns that can "
            "improve future sprints."
        ),
        capabilities=[
            "sprint_review",
            "deliverable_evaluation",
            "feedback_gathering",
            "criteria_enforcement",
            "finding_documentation",
            "pattern_analysis",
            "acceptance_verification",
        ],
        tools=["review_checklist", "feedback_collector", "tape_service"],
    )

    IMPLEMENTATION_EXECUTOR = AgentBlueprint(
        agent_id="bmad_implementation_executor",
        name="Implementation Executor",
        role=AgentRole.EXECUTOR,
        goal=(
            "Execute implementation work within sprints, "
            "build deliverables, and track progress"
        ),
        backstory=(
            "The Implementation Executor is BMAD's delivery engine. It "
            "takes sprint backlog items and turns them into working deliverables. "
            "It understands how to break down stories, estimate effort, and "
            "execute efficiently. It provides progress updates, escalates "
            "blockers, and ensures sprints stay on track."
        ),
        capabilities=[
            "story_execution",
            "deliverable_building",
            "progress_tracking",
            "blocker_escalation",
            "daily_update",
            "quality_gates",
            "sprint_commitments",
        ],
        tools=["backlog_service", "progress_tracker", "aethergit"],
    )

    @classmethod
    def all_agents(cls) -> list[AgentBlueprint]:
        """Return all agent blueprints for the BMAD domain."""
        return [
            cls.SPRINT_PLANNER,
            cls.BREAKTHROUGH_FACILITATOR,
            cls.AGILE_COACH,
            cls.TRACK_COORDINATOR,
            cls.SPRINT_REVIEWER,
            cls.IMPLEMENTATION_EXECUTOR,
        ]


class BMADSkillBlueprint:
    """Skill blueprints for the BMAD domain."""

    SPRINT_PLANNING = SkillBlueprint(
        skill_id="bmad_sprint_planning",
        name="Sprint Planning",
        description=(
            "Plan sprints, define goals, create stories, "
            "and coordinate across tracks"
        ),
        version="1.0.0",
    )

    BREAKTHROUGH_FACILITATION = SkillBlueprint(
        skill_id="bmad_breakthrough_facilitation",
        name="Breakthrough Facilitation",
        description=(
            "Facilitate breakthrough sessions, surface insights, "
            "and unlock creative solutions"
        ),
        version="1.0.0",
    )

    AGILE_COACHING = SkillBlueprint(
        skill_id="bmad_agile_coaching",
        name="Agile Coaching",
        description=(
            "Coach agile practices, guide process improvements, "
            "and foster collaboration"
        ),
        version="1.0.0",
    )

    TRACK_COORDINATION = SkillBlueprint(
        skill_id="bmad_track_coordination",
        name="Track Coordination",
        description=(
            "Coordinate work across tracks, manage dependencies, "
            "and ensure alignment"
        ),
        version="1.0.0",
    )

    SPRINT_REVIEW = SkillBlueprint(
        skill_id="bmad_sprint_review",
        name="Sprint Review",
        description=(
            "Conduct sprint reviews, evaluate deliverables, "
            "and gather feedback"
        ),
        version="1.0.0",
    )

    @classmethod
    def all_skills(cls) -> list[SkillBlueprint]:
        """Return all skill blueprints for the BMAD domain."""
        return [
            cls.SPRINT_PLANNING,
            cls.BREAKTHROUGH_FACILITATION,
            cls.AGILE_COACHING,
            cls.TRACK_COORDINATION,
            cls.SPRINT_REVIEW,
        ]


class BMADWorkflowBlueprint:
    """Workflow blueprints for the BMAD domain."""

    BMAD_SPRINT_CYCLE = WorkflowBlueprint(
        workflow_id="bmad_sprint_cycle",
        name="BMAD Sprint Cycle",
        workflow_type=WorkflowType.SEQUENTIAL,
        description="Complete BMAD sprint cycle with all four tracks",
        agent_ids=[
            "bmad_sprint_planner",
            "bmad_track_coordinator",
            "bmad_implementation_executor",
            "bmad_sprint_reviewer",
        ],
        steps=[
            "Sprint planning: Define scope and goals",
            "Track Research: Gather requirements and insights",
            "Track Design: Create specifications",
            "Track Build: Execute implementation",
            "Track Review: Validate deliverables",
            "Sprint review: Evaluate outcomes",
            "Capture learnings for next sprint",
            "Log sprint completion to Tape",
        ],
    )

    BREAKTHROUGH_SESSION = WorkflowBlueprint(
        workflow_id="bmad_breakthrough_session",
        name="Breakthrough Session",
        workflow_type=WorkflowType.DEBATE,
        description="Structured breakthrough session to solve complex problems",
        agent_ids=[
            "bmad_breakthrough_facilitator",
            "bmad_agile_coach",
            "bmad_sprint_planner",
        ],
        steps=[
            "Define breakthrough challenge",
            "Set session constraints and rules",
            "Divergent thinking phase",
            "Convergent analysis phase",
            "Insight surfacing",
            "Solution selection",
            "Action item capture",
            "Integration planning",
        ],
    )

    TRACK_COORDINATION_FLOW = WorkflowBlueprint(
        workflow_id="bmad_track_coordination_flow",
        name="Track Coordination Flow",
        workflow_type=WorkflowType.PIPELINE,
        description="Coordinate work flowing through Research, Design, Build, Review",
        agent_ids=[
            "bmad_track_coordinator",
            "bmad_sprint_planner",
            "bmad_implementation_executor",
        ],
        steps=[
            "Receive new initiative",
            "Route to Research track",
            "Validate Research completion",
            "Route to Design track",
            "Validate Design completion",
            "Route to Build track",
            "Validate Build completion",
            "Route to Review track",
            "Final delivery",
        ],
    )

    @classmethod
    def all_workflows(cls) -> list[WorkflowBlueprint]:
        """Return all workflow blueprints for the BMAD domain."""
        return [
            cls.BMAD_SPRINT_CYCLE,
            cls.BREAKTHROUGH_SESSION,
            cls.TRACK_COORDINATION_FLOW,
        ]


class BMADDomainBlueprint:
    """Complete domain blueprint for BMAD.

    Usage::

        blueprint = BMADDomainBlueprint.create()
        # Use with DomainFolderTreeGenerator
    """

    @classmethod
    def create(cls) -> DomainBlueprint:
        """Create the complete BMAD domain blueprint."""
        return DomainBlueprint(
            domain_name=DOMAIN_NAME,
            domain_id=DOMAIN_ID,
            description=DOMAIN_DESCRIPTION,
            source_description=(
                "Create an agile AI-driven development domain "
                "with sprint-based planning and breakthrough facilitation"
            ),
            agents=BMADAgentBlueprint.all_agents(),
            skills=BMADSkillBlueprint.all_skills(),
            workflows=BMADWorkflowBlueprint.all_workflows(),
            config=DomainConfig(
                max_agents=12,
                max_concurrent_tasks=15,
                requires_human_approval=True,
                data_retention_days=90,
                priority_level="high",
                custom_settings={
                    "sprint_length": "2_weeks",
                    "tracks_enabled": ["research", "design", "build", "review"],
                    "breakthrough_sessions": True,
                    "retrospectives_required": True,
                    "velocity_tracking": True,
                },
            ),
        )
