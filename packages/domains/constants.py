"""Constants for InkosAI Planning Domains.

Shared enums, types, and configuration values used across Gastown, GSD,
BMAD, and the Planning Super Domain.
"""

from __future__ import annotations

from enum import StrEnum

# Domain version for tracking changes
PLANNING_DOMAIN_VERSION = "1.0.0"


class PlanningDomainType(StrEnum):
    """The three official planning domains plus the super domain."""

    GASTOWN = "gastown"
    GSD = "gsd"
    BMAD = "bmad"
    SUPER = "planning_super"


class PlanningAgentRole(StrEnum):
    """Extended agent roles specific to planning methodologies."""

    # Gastown roles
    WORKSPACE_MANAGER = "workspace_manager"
    AGENT_COORDINATOR = "agent_coordinator"
    SESSION_MANAGER = "session_manager"
    RESOURCE_ALLOCATOR = "resource_allocator"
    TASK_DISTRIBUTOR = "task_distributor"

    # GSD roles
    PHASE_MANAGER = "phase_manager"
    CONTEXT_ENGINEER = "context_engineer"
    META_PROMPT_DESIGNER = "meta_prompt_designer"
    EXECUTION_TRACKER = "execution_tracker"
    QUALITY_VALIDATOR = "quality_validator"

    # BMAD roles
    SPRINT_PLANNER = "sprint_planner"
    BREAKTHROUGH_FACILITATOR = "breakthrough_facilitator"
    AGILE_COACH = "agile_coach"
    TRACK_COORDINATOR = "track_coordinator"
    SPRINT_REVIEWER = "sprint_reviewer"

    # Super domain roles
    PLANNING_ORCHESTRATOR = "planning_orchestrator"
    METHODOLOGY_SELECTOR = "methodology_selector"


class PlanningSkillType(StrEnum):
    """Skill types used across planning domains."""

    # Gastown skills
    WORKSPACE_ORCHESTRATION = "workspace_orchestration"
    AGENT_COORDINATION = "agent_coordination"
    SESSION_MANAGEMENT = "session_management"
    RESOURCE_ALLOCATION = "resource_allocation"
    TASK_DISTRIBUTION = "task_distribution"

    # GSD skills
    META_PROMPTING = "meta_prompting"
    CONTEXT_ENGINEERING = "context_engineering"
    PHASE_MANAGEMENT = "phase_management"
    EXECUTION_TRACKING = "execution_tracking"
    QUALITY_VALIDATION = "quality_validation"

    # BMAD skills
    SPRINT_PLANNING = "sprint_planning"
    BREAKTHROUGH_FACILITATION = "breakthrough_facilitation"
    AGILE_COACHING = "agile_coaching"
    TRACK_COORDINATION = "track_coordination"
    SPRINT_REVIEW = "sprint_review"

    # Cross-methodology skills
    CONFLICT_RESOLUTION = "conflict_resolution"
    HYBRID_ORCHESTRATION = "hybrid_orchestration"


class PlanningWorkflowType(StrEnum):
    """Workflow types for planning domains."""

    # Gastown workflows
    WORKSPACE_INITIALIZATION = "workspace_initialization"
    MULTI_AGENT_COORDINATION = "multi_agent_coordination"
    SESSION_LIFECYCLE = "session_lifecycle"

    # GSD workflows
    GSD_DEVELOPMENT_CYCLE = "gsd_development_cycle"
    PHASE_EXECUTION_PIPELINE = "phase_execution_pipeline"
    CONTEXT_OPTIMIZATION = "context_optimization"

    # BMAD workflows
    BMAD_SPRINT_CYCLE = "bmad_sprint_cycle"
    BREAKTHROUGH_SESSION = "breakthrough_session"
    TRACK_COORDINATION_FLOW = "track_coordination_flow"

    # Hybrid workflows
    HYBRID_PLANNING_PIPELINE = "hybrid_planning_pipeline"
    CROSS_METHODOLOGY_SWARM = "cross_methodology_swarm"


# Domain-specific colors and icons for visual canvas
DOMAIN_VISUAL_STYLES = {
    PlanningDomainType.GASTOWN: {
        "primary_color": "#6366f1",  # Indigo
        "secondary_color": "#818cf8",
        "icon": "LayoutGrid",
        "accent_color": "#4f46e5",
    },
    PlanningDomainType.GSD: {
        "primary_color": "#10b981",  # Emerald
        "secondary_color": "#34d399",
        "icon": "Zap",
        "accent_color": "#059669",
    },
    PlanningDomainType.BMAD: {
        "primary_color": "#f59e0b",  # Amber
        "secondary_color": "#fbbf24",
        "icon": "Rocket",
        "accent_color": "#d97706",
    },
    PlanningDomainType.SUPER: {
        "primary_color": "#8b5cf6",  # Violet
        "secondary_color": "#a78bfa",
        "icon": "Layers",
        "accent_color": "#7c3aed",
    },
}


# Cross-methodology conflict resolution strategies
CONFLICT_RESOLUTION_STRATEGIES = {
    "debate": "Use Debate Arena for agent discussion",
    "simulation": "Run Simulation Engine for outcome prediction",
    "prime_override": "Prime makes final decision based on context",
    "voting": "Democratic voting across participating agents",
    "hierarchy": "Follow methodology hierarchy (GSD > BMAD > Gastown)",
}


# Hybrid workflow patterns
HYBRID_PATTERNS = {
    "gsd_research_bmad_planning": "GSD Research -> BMAD Sprint Planning",
    "gastown_execution_bmad_review": "Gastown Execution -> BMAD Sprint Review",
    "gsd_context_gastown_coordination": "GSD Context Engineering -> Gastown Coordination",
    "bmad_breakthrough_gsd_build": "BMAD Breakthrough -> GSD Build Phase",
    "full_hybrid": "All three methodologies integrated",
}
