"""Comprehensive tests for InkosAI Planning Domains.

Tests for:
- Gastown Domain (multi-agent workspace orchestration)
- GSD Domain (meta-prompting and phase-based development)
- BMAD Domain (agile AI-driven development)
- Planning Super Domain (unified planning environment)
- PlanningDomainFactory for creation and management
- PlanningDomainRegistry for registration and discovery
"""

from __future__ import annotations

import pytest

from packages.domain.domain_blueprint import (
    AgentBlueprint,
    DomainBlueprint,
    SkillBlueprint,
    WorkflowBlueprint,
)
from packages.domains.bmad.blueprint import (
    BMADAgentBlueprint,
    BMADDomainBlueprint,
    BMADSkillBlueprint,
    BMADWorkflowBlueprint,
)
from packages.domains.constants import (
    CONFLICT_RESOLUTION_STRATEGIES,
    DOMAIN_VISUAL_STYLES,
    HYBRID_PATTERNS,
    PLANNING_DOMAIN_VERSION,
    PlanningDomainType,
)
from packages.domains.factory import PlanningDomainFactory
from packages.domains.gastown.blueprint import (
    GastownAgentBlueprint,
    GastownDomainBlueprint,
    GastownSkillBlueprint,
    GastownWorkflowBlueprint,
)
from packages.domains.gsd.blueprint import (
    GSDAgentBlueprint,
    GSDDomainBlueprint,
    GSDSkillBlueprint,
    GSDWorkflowBlueprint,
)
from packages.domains.super_domain.blueprint import (
    PlanningSuperDomainBlueprint,
    SuperDomainAgentBlueprint,
    SuperDomainSkillBlueprint,
    SuperDomainWorkflowBlueprint,
)
from packages.prime.domain_creation import AgentRole, WorkflowType
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# =============================================================================
# Gastown Domain Tests
# =============================================================================


class TestGastownDomainBlueprint:
    """Tests for Gastown domain blueprint."""

    def test_create_returns_valid_blueprint(self):
        """GastownDomainBlueprint.create() returns a valid DomainBlueprint."""
        blueprint = GastownDomainBlueprint.create()
        assert isinstance(blueprint, DomainBlueprint)
        assert blueprint.domain_id == "gastown"
        assert blueprint.domain_name == "Gastown"

    def test_blueprint_has_correct_domain_id(self):
        """Gastown blueprint has correct domain ID."""
        blueprint = GastownDomainBlueprint.create()
        assert blueprint.domain_id == "gastown"

    def test_blueprint_has_correct_domain_name(self):
        """Gastown blueprint has correct domain name."""
        blueprint = GastownDomainBlueprint.create()
        assert blueprint.domain_name == "Gastown"

    def test_blueprint_has_description(self):
        """Gastown blueprint has a description."""
        blueprint = GastownDomainBlueprint.create()
        assert blueprint.description
        assert "workspace" in blueprint.description.lower()

    def test_blueprint_has_5_agents(self):
        """Gastown blueprint has exactly 5 agents."""
        blueprint = GastownDomainBlueprint.create()
        assert len(blueprint.agents) == 5

    def test_blueprint_has_5_skills(self):
        """Gastown blueprint has exactly 5 skills."""
        blueprint = GastownDomainBlueprint.create()
        assert len(blueprint.skills) == 5

    def test_blueprint_has_3_workflows(self):
        """Gastown blueprint has exactly 3 workflows."""
        blueprint = GastownDomainBlueprint.create()
        assert len(blueprint.workflows) == 3

    def test_workspace_manager_agent_exists(self):
        """Gastown has Workspace Manager agent."""
        blueprint = GastownDomainBlueprint.create()
        agent_ids = [a.agent_id for a in blueprint.agents]
        assert "gastown_workspace_manager" in agent_ids

    def test_agent_coordinator_agent_exists(self):
        """Gastown has Agent Coordinator agent."""
        blueprint = GastownDomainBlueprint.create()
        agent_ids = [a.agent_id for a in blueprint.agents]
        assert "gastown_agent_coordinator" in agent_ids

    def test_config_has_workspace_persistence(self):
        """Gastown config enables workspace persistence."""
        blueprint = GastownDomainBlueprint.create()
        assert blueprint.config.custom_settings.get("workspace_persistence") is True

    def test_config_has_session_recovery(self):
        """Gastown config enables session recovery."""
        blueprint = GastownDomainBlueprint.create()
        assert blueprint.config.custom_settings.get("session_recovery") is True

    def test_agents_have_valid_roles(self):
        """All Gastown agents have valid roles."""
        blueprint = GastownDomainBlueprint.create()
        valid_roles = {r.value for r in AgentRole}
        for agent in blueprint.agents:
            assert agent.role.value in valid_roles

    def test_agents_have_goals(self):
        """All Gastown agents have goals."""
        blueprint = GastownDomainBlueprint.create()
        for agent in blueprint.agents:
            assert agent.goal
            assert len(agent.goal) > 0

    def test_agents_have_backstories(self):
        """All Gastown agents have backstories."""
        blueprint = GastownDomainBlueprint.create()
        for agent in blueprint.agents:
            assert agent.backstory
            assert len(agent.backstory) > 0

    def test_workflows_have_valid_types(self):
        """All Gastown workflows have valid workflow types."""
        blueprint = GastownDomainBlueprint.create()
        valid_types = {t.value for t in WorkflowType}
        for workflow in blueprint.workflows:
            assert workflow.workflow_type.value in valid_types

    def test_skills_have_valid_ids(self):
        """All Gastown skills have gastown-prefixed IDs."""
        blueprint = GastownDomainBlueprint.create()
        for skill in blueprint.skills:
            assert skill.skill_id.startswith("gastown_")

    def test_config_high_priority(self):
        """Gastown domain has high priority level."""
        blueprint = GastownDomainBlueprint.create()
        assert blueprint.config.priority_level == "high"


class TestGastownAgentBlueprint:
    """Tests for Gastown agent blueprints."""

    def test_all_agents_returns_list(self):
        """all_agents() returns a list of AgentBlueprint objects."""
        agents = GastownAgentBlueprint.all_agents()
        assert isinstance(agents, list)
        assert all(isinstance(a, AgentBlueprint) for a in agents)

    def test_workspace_manager_has_coordinator_role(self):
        """Workspace Manager has coordinator role."""
        assert GastownAgentBlueprint.WORKSPACE_MANAGER.role == AgentRole.COORDINATOR

    def test_task_distributor_has_executor_role(self):
        """Task Distributor has executor role."""
        assert GastownAgentBlueprint.TASK_DISTRIBUTOR.role == AgentRole.EXECUTOR

    def test_resource_allocator_has_capabilities(self):
        """Resource Allocator has resource-related capabilities."""
        agent = GastownAgentBlueprint.RESOURCE_ALLOCATOR
        assert "resource_tracking" in agent.capabilities
        assert "quota_management" in agent.capabilities

    def test_session_manager_has_monitor_role(self):
        """Session Manager has monitor role."""
        assert GastownAgentBlueprint.SESSION_MANAGER.role == AgentRole.MONITOR


class TestGastownSkillBlueprint:
    """Tests for Gastown skill blueprints."""

    def test_all_skills_returns_list(self):
        """all_skills() returns a list of SkillBlueprint objects."""
        skills = GastownSkillBlueprint.all_skills()
        assert isinstance(skills, list)
        assert all(isinstance(s, SkillBlueprint) for s in skills)

    def test_workspace_orchestration_skill_exists(self):
        """Workspace Orchestration skill exists."""
        skill_ids = [s.skill_id for s in GastownSkillBlueprint.all_skills()]
        assert "gastown_workspace_orchestration" in skill_ids

    def test_all_skills_have_descriptions(self):
        """All Gastown skills have descriptions."""
        skills = GastownSkillBlueprint.all_skills()
        for skill in skills:
            assert skill.description
            assert len(skill.description) > 0


class TestGastownWorkflowBlueprint:
    """Tests for Gastown workflow blueprints."""

    def test_all_workflows_returns_list(self):
        """all_workflows() returns a list of WorkflowBlueprint objects."""
        workflows = GastownWorkflowBlueprint.all_workflows()
        assert isinstance(workflows, list)
        assert all(isinstance(w, WorkflowBlueprint) for w in workflows)

    def test_workspace_initialization_is_sequential(self):
        """Workspace Initialization workflow is sequential."""
        wf = GastownWorkflowBlueprint.WORKSPACE_INITIALIZATION
        assert wf.workflow_type == WorkflowType.SEQUENTIAL

    def test_multi_agent_coordination_is_parallel(self):
        """Multi-Agent Coordination workflow is parallel."""
        wf = GastownWorkflowBlueprint.MULTI_AGENT_COORDINATION
        assert wf.workflow_type == WorkflowType.PARALLEL

    def test_session_lifecycle_is_iterative(self):
        """Session Lifecycle workflow is iterative."""
        wf = GastownWorkflowBlueprint.SESSION_LIFECYCLE
        assert wf.workflow_type == WorkflowType.ITERATIVE


# =============================================================================
# GSD Domain Tests
# =============================================================================


class TestGSDDomainBlueprint:
    """Tests for GSD domain blueprint."""

    def test_create_returns_valid_blueprint(self):
        """GSDDomainBlueprint.create() returns a valid DomainBlueprint."""
        blueprint = GSDDomainBlueprint.create()
        assert isinstance(blueprint, DomainBlueprint)
        assert blueprint.domain_id == "gsd"

    def test_blueprint_has_correct_domain_id(self):
        """GSD blueprint has correct domain ID."""
        blueprint = GSDDomainBlueprint.create()
        assert blueprint.domain_id == "gsd"

    def test_blueprint_has_correct_domain_name(self):
        """GSD blueprint has correct domain name."""
        blueprint = GSDDomainBlueprint.create()
        assert "GSD" in blueprint.domain_name

    def test_blueprint_has_description(self):
        """GSD blueprint has a description."""
        blueprint = GSDDomainBlueprint.create()
        assert blueprint.description
        assert "meta" in blueprint.description.lower() or "phase" in blueprint.description.lower()

    def test_blueprint_has_6_agents(self):
        """GSD blueprint has exactly 6 agents."""
        blueprint = GSDDomainBlueprint.create()
        assert len(blueprint.agents) == 6

    def test_blueprint_has_5_skills(self):
        """GSD blueprint has exactly 5 skills."""
        blueprint = GSDDomainBlueprint.create()
        assert len(blueprint.skills) == 5

    def test_blueprint_has_3_workflows(self):
        """GSD blueprint has exactly 3 workflows."""
        blueprint = GSDDomainBlueprint.create()
        assert len(blueprint.workflows) == 3

    def test_phase_manager_agent_exists(self):
        """GSD has Phase Manager agent."""
        blueprint = GSDDomainBlueprint.create()
        agent_ids = [a.agent_id for a in blueprint.agents]
        assert "gsd_phase_manager" in agent_ids

    def test_meta_prompt_designer_agent_exists(self):
        """GSD has Meta-Prompt Designer agent."""
        blueprint = GSDDomainBlueprint.create()
        agent_ids = [a.agent_id for a in blueprint.agents]
        assert "gsd_meta_prompt_designer" in agent_ids

    def test_config_has_phase_gates(self):
        """GSD config enables phase gates."""
        blueprint = GSDDomainBlueprint.create()
        assert blueprint.config.custom_settings.get("phase_gates_required") is True

    def test_config_has_context_optimization(self):
        """GSD config enables context optimization."""
        blueprint = GSDDomainBlueprint.create()
        assert blueprint.config.custom_settings.get("context_optimization") is True

    def test_config_has_quality_threshold(self):
        """GSD config has quality threshold set."""
        blueprint = GSDDomainBlueprint.create()
        threshold = blueprint.config.custom_settings.get("quality_threshold")
        assert threshold is not None
        assert 0 <= threshold <= 1


class TestGSDAgentBlueprint:
    """Tests for GSD agent blueprints."""

    def test_all_agents_returns_list(self):
        """all_agents() returns a list of AgentBlueprint objects."""
        agents = GSDAgentBlueprint.all_agents()
        assert isinstance(agents, list)
        assert len(agents) == 6

    def test_phase_manager_has_coordinator_role(self):
        """Phase Manager has coordinator role."""
        assert GSDAgentBlueprint.PHASE_MANAGER.role == AgentRole.COORDINATOR

    def test_context_engineer_has_analyst_role(self):
        """Context Engineer has analyst role."""
        assert GSDAgentBlueprint.CONTEXT_ENGINEER.role == AgentRole.ANALYST

    def test_quality_validator_has_reviewer_role(self):
        """Quality Validator has reviewer role."""
        assert GSDAgentBlueprint.QUALITY_VALIDATOR.role == AgentRole.REVIEWER


class TestGSDWorkflowBlueprint:
    """Tests for GSD workflow blueprints."""

    def test_gsd_development_cycle_has_all_6_phases(self):
        """GSD Development Cycle includes all 6 phases."""
        wf = GSDWorkflowBlueprint.GSD_DEVELOPMENT_CYCLE
        phase_steps = [s for s in wf.steps if "PHASE" in s]
        assert len(phase_steps) == 6

    def test_phase_execution_pipeline_is_pipeline_type(self):
        """Phase Execution Pipeline is pipeline workflow type."""
        wf = GSDWorkflowBlueprint.PHASE_EXECUTION_PIPELINE
        assert wf.workflow_type == WorkflowType.PIPELINE

    def test_context_optimization_is_iterative(self):
        """Context Optimization workflow is iterative."""
        wf = GSDWorkflowBlueprint.CONTEXT_OPTIMIZATION
        assert wf.workflow_type == WorkflowType.ITERATIVE


# =============================================================================
# BMAD Domain Tests
# =============================================================================


class TestBMADDomainBlueprint:
    """Tests for BMAD domain blueprint."""

    def test_create_returns_valid_blueprint(self):
        """BMADDomainBlueprint.create() returns a valid DomainBlueprint."""
        blueprint = BMADDomainBlueprint.create()
        assert isinstance(blueprint, DomainBlueprint)
        assert blueprint.domain_id == "bmad"

    def test_blueprint_has_correct_domain_id(self):
        """BMAD blueprint has correct domain ID."""
        blueprint = BMADDomainBlueprint.create()
        assert blueprint.domain_id == "bmad"

    def test_blueprint_has_correct_domain_name(self):
        """BMAD blueprint has correct domain name."""
        blueprint = BMADDomainBlueprint.create()
        assert blueprint.domain_name == "BMAD"

    def test_blueprint_has_description(self):
        """BMAD blueprint has a description."""
        blueprint = BMADDomainBlueprint.create()
        assert blueprint.description

    def test_blueprint_has_6_agents(self):
        """BMAD blueprint has exactly 6 agents."""
        blueprint = BMADDomainBlueprint.create()
        assert len(blueprint.agents) == 6

    def test_blueprint_has_5_skills(self):
        """BMAD blueprint has exactly 5 skills."""
        blueprint = BMADDomainBlueprint.create()
        assert len(blueprint.skills) == 5

    def test_blueprint_has_3_workflows(self):
        """BMAD blueprint has exactly 3 workflows."""
        blueprint = BMADDomainBlueprint.create()
        assert len(blueprint.workflows) == 3

    def test_sprint_planner_agent_exists(self):
        """BMAD has Sprint Planner agent."""
        blueprint = BMADDomainBlueprint.create()
        agent_ids = [a.agent_id for a in blueprint.agents]
        assert "bmad_sprint_planner" in agent_ids

    def test_breakthrough_facilitator_agent_exists(self):
        """BMAD has Breakthrough Facilitator agent."""
        blueprint = BMADDomainBlueprint.create()
        agent_ids = [a.agent_id for a in blueprint.agents]
        assert "bmad_breakthrough_facilitator" in agent_ids

    def test_agile_coach_agent_exists(self):
        """BMAD has Agile Coach agent."""
        blueprint = BMADDomainBlueprint.create()
        agent_ids = [a.agent_id for a in blueprint.agents]
        assert "bmad_agile_coach" in agent_ids

    def test_config_has_sprint_length(self):
        """BMAD config has sprint length setting."""
        blueprint = BMADDomainBlueprint.create()
        assert "2_weeks" in blueprint.config.custom_settings.get("sprint_length", "")

    def test_config_has_tracks_enabled(self):
        """BMAD config enables all 4 tracks."""
        blueprint = BMADDomainBlueprint.create()
        tracks = blueprint.config.custom_settings.get("tracks_enabled", [])
        assert len(tracks) == 4

    def test_config_has_breakthrough_sessions(self):
        """BMAD config enables breakthrough sessions."""
        blueprint = BMADDomainBlueprint.create()
        assert blueprint.config.custom_settings.get("breakthrough_sessions") is True


class TestBMADAgentBlueprint:
    """Tests for BMAD agent blueprints."""

    def test_all_agents_returns_list(self):
        """all_agents() returns a list of AgentBlueprint objects."""
        agents = BMADAgentBlueprint.all_agents()
        assert isinstance(agents, list)
        assert len(agents) == 6

    def test_sprint_planner_has_coordinator_role(self):
        """Sprint Planner has coordinator role."""
        assert BMADAgentBlueprint.SPRINT_PLANNER.role == AgentRole.COORDINATOR

    def test_breakthrough_facilitator_has_communicator_role(self):
        """Breakthrough Facilitator has communicator role."""
        assert BMADAgentBlueprint.BREAKTHROUGH_FACILITATOR.role == AgentRole.COMMUNICATOR

    def test_agile_coach_has_communicator_role(self):
        """Agile Coach has communicator role."""
        assert BMADAgentBlueprint.AGILE_COACH.role == AgentRole.COMMUNICATOR

    def test_track_coordinator_has_coordinator_role(self):
        """Track Coordinator has coordinator role."""
        assert BMADAgentBlueprint.TRACK_COORDINATOR.role == AgentRole.COORDINATOR

    def test_sprint_reviewer_has_reviewer_role(self):
        """Sprint Reviewer has reviewer role."""
        assert BMADAgentBlueprint.SPRINT_REVIEWER.role == AgentRole.REVIEWER


class TestBMADWorkflowBlueprint:
    """Tests for BMAD workflow blueprints."""

    def test_bmad_sprint_cycle_contains_all_4_tracks(self):
        """BMAD Sprint Cycle includes all 4 tracks."""
        wf = BMADWorkflowBlueprint.BMAD_SPRINT_CYCLE
        track_steps = [s for s in wf.steps if "Track" in s]
        assert len(track_steps) == 4

    def test_breakthrough_session_is_debate_type(self):
        """Breakthrough Session workflow is debate type."""
        wf = BMADWorkflowBlueprint.BREAKTHROUGH_SESSION
        assert wf.workflow_type == WorkflowType.DEBATE


# =============================================================================
# Planning Super Domain Tests
# =============================================================================


class TestPlanningSuperDomainBlueprint:
    """Tests for Planning Super Domain blueprint."""

    def test_create_returns_valid_blueprint(self):
        """PlanningSuperDomainBlueprint.create() returns a valid DomainBlueprint."""
        blueprint = PlanningSuperDomainBlueprint.create()
        assert isinstance(blueprint, DomainBlueprint)
        assert blueprint.domain_id == "planning_super"

    def test_blueprint_has_correct_domain_id(self):
        """Super Domain has correct domain ID."""
        blueprint = PlanningSuperDomainBlueprint.create()
        assert blueprint.domain_id == "planning_super"

    def test_blueprint_has_correct_domain_name(self):
        """Super Domain has correct domain name."""
        blueprint = PlanningSuperDomainBlueprint.create()
        assert "Planning Super Domain" in blueprint.domain_name

    def test_blueprint_has_7_agents(self):
        """Super Domain has exactly 7 agents."""
        blueprint = PlanningSuperDomainBlueprint.create()
        assert len(blueprint.agents) == 7

    def test_blueprint_has_5_skills(self):
        """Super Domain has exactly 5 skills."""
        blueprint = PlanningSuperDomainBlueprint.create()
        assert len(blueprint.skills) == 5

    def test_blueprint_has_3_workflows(self):
        """Super Domain has exactly 3 workflows."""
        blueprint = PlanningSuperDomainBlueprint.create()
        assert len(blueprint.workflows) == 3

    def test_planning_orchestrator_agent_exists(self):
        """Super Domain has Planning Orchestrator agent."""
        blueprint = PlanningSuperDomainBlueprint.create()
        agent_ids = [a.agent_id for a in blueprint.agents]
        assert "super_planning_orchestrator" in agent_ids

    def test_methodology_selector_agent_exists(self):
        """Super Domain has Methodology Selector agent."""
        blueprint = PlanningSuperDomainBlueprint.create()
        agent_ids = [a.agent_id for a in blueprint.agents]
        assert "super_methodology_selector" in agent_ids

    def test_conflict_resolver_agent_exists(self):
        """Super Domain has Conflict Resolver agent."""
        blueprint = PlanningSuperDomainBlueprint.create()
        agent_ids = [a.agent_id for a in blueprint.agents]
        assert "super_conflict_resolver" in agent_ids

    def test_has_3_liaison_agents(self):
        """Super Domain has 3 liaison agents (one per methodology)."""
        blueprint = PlanningSuperDomainBlueprint.create()
        liaison_agents = [a for a in blueprint.agents if "liaison" in a.agent_id]
        assert len(liaison_agents) == 3

    def test_config_has_super_domain_mode(self):
        """Super Domain config enables super domain mode."""
        blueprint = PlanningSuperDomainBlueprint.create()
        assert blueprint.config.custom_settings.get("super_domain_mode") is True

    def test_config_has_conflict_detection(self):
        """Super Domain config enables conflict detection."""
        blueprint = PlanningSuperDomainBlueprint.create()
        assert blueprint.config.custom_settings.get("conflict_detection") is True

    def test_config_has_hybrid_orchestration(self):
        """Super Domain config enables hybrid orchestration."""
        blueprint = PlanningSuperDomainBlueprint.create()
        assert blueprint.config.custom_settings.get("hybrid_orchestration") is True

    def test_config_critical_priority(self):
        """Super Domain has critical priority level."""
        blueprint = PlanningSuperDomainBlueprint.create()
        assert blueprint.config.priority_level == "critical"

    def test_has_more_agents_than_base_domains(self):
        """Super Domain has more agents than any base domain individually."""
        super_bp = PlanningSuperDomainBlueprint.create()
        gastown_bp = GastownDomainBlueprint.create()
        gsd_bp = GSDDomainBlueprint.create()
        bmad_bp = BMADDomainBlueprint.create()

        super_count = len(super_bp.agents)
        assert super_count > len(gastown_bp.agents)
        assert super_count > len(gsd_bp.agents)
        assert super_count > len(bmad_bp.agents)


class TestSuperDomainAgentBlueprint:
    """Tests for Super Domain agent blueprints."""

    def test_all_agents_returns_list(self):
        """all_agents() returns a list of AgentBlueprint objects."""
        agents = SuperDomainAgentBlueprint.all_agents()
        assert isinstance(agents, list)
        assert len(agents) == 7

    def test_planning_orchestrator_has_coordinator_role(self):
        """Planning Orchestrator has coordinator role."""
        assert SuperDomainAgentBlueprint.PLANNING_ORCHESTRATOR.role == AgentRole.COORDINATOR

    def test_methodology_selector_has_analyst_role(self):
        """Methodology Selector has analyst role."""
        assert SuperDomainAgentBlueprint.METHODOLOGY_SELECTOR.role == AgentRole.ANALYST

    def test_conflict_resolver_has_reviewer_role(self):
        """Conflict Resolver has reviewer role."""
        assert SuperDomainAgentBlueprint.CONFLICT_RESOLVER.role == AgentRole.REVIEWER

    def test_hybrid_tracker_has_monitor_role(self):
        """Hybrid Tracker has monitor role."""
        assert SuperDomainAgentBlueprint.HYBRID_TRACKER.role == AgentRole.MONITOR


class TestSuperDomainWorkflowBlueprint:
    """Tests for Super Domain workflow blueprints."""

    def test_cross_methodology_swarm_is_parallel_type(self):
        """Cross-Methodology Swarm workflow is parallel type."""
        wf = SuperDomainWorkflowBlueprint.CROSS_METHODOLOGY_SWARM
        assert wf.workflow_type == WorkflowType.PARALLEL

    def test_conflict_resolution_workflow_is_debate_type(self):
        """Conflict Resolution workflow is debate type."""
        wf = SuperDomainWorkflowBlueprint.CONFLICT_RESOLUTION_WORKFLOW
        assert wf.workflow_type == WorkflowType.DEBATE

    def test_hybrid_planning_pipeline_is_pipeline_type(self):
        """Hybrid Planning Pipeline is pipeline workflow type."""
        wf = SuperDomainWorkflowBlueprint.HYBRID_PLANNING_PIPELINE
        assert wf.workflow_type == WorkflowType.PIPELINE


# =============================================================================
# PlanningDomainFactory Tests
# =============================================================================


class TestPlanningDomainFactory:
    """Tests for PlanningDomainFactory."""

    def test_create_blueprint_gastown(self):
        """Factory can create Gastown blueprint."""
        blueprint = PlanningDomainFactory.create_blueprint(PlanningDomainType.GASTOWN)
        assert blueprint.domain_id == "gastown"

    def test_create_blueprint_gsd(self):
        """Factory can create GSD blueprint."""
        blueprint = PlanningDomainFactory.create_blueprint(PlanningDomainType.GSD)
        assert blueprint.domain_id == "gsd"

    def test_create_blueprint_bmad(self):
        """Factory can create BMAD blueprint."""
        blueprint = PlanningDomainFactory.create_blueprint(PlanningDomainType.BMAD)
        assert blueprint.domain_id == "bmad"

    def test_create_blueprint_super(self):
        """Factory can create Super Domain blueprint."""
        blueprint = PlanningDomainFactory.create_blueprint(PlanningDomainType.SUPER)
        assert blueprint.domain_id == "planning_super"

    def test_create_blueprint_invalid_raises_error(self):
        """Factory raises ValueError for invalid domain type."""
        with pytest.raises(ValueError):
            PlanningDomainFactory.create_blueprint("invalid_type")  # type: ignore

    def test_list_all_domain_info_returns_all_domains(self):
        """list_all_domain_info returns info for all 4 domain types."""
        info = PlanningDomainFactory.list_all_domain_info()
        assert len(info) == 4
        assert PlanningDomainType.GASTOWN in info
        assert PlanningDomainType.GSD in info
        assert PlanningDomainType.BMAD in info
        assert PlanningDomainType.SUPER in info

    def test_get_domain_info_returns_correct_structure(self):
        """get_domain_info returns dictionary with expected structure."""
        info = PlanningDomainFactory.get_domain_info(PlanningDomainType.GASTOWN)
        assert "id" in info
        assert "name" in info
        assert "agent_count" in info
        assert "skill_count" in info
        assert "workflow_count" in info

    def test_domain_info_has_counts(self):
        """Domain info includes agent/skill/workflow counts."""
        info = PlanningDomainFactory.get_domain_info(PlanningDomainType.GASTOWN)
        assert info["agent_count"] == 5
        assert info["skill_count"] == 5
        assert info["workflow_count"] == 3


# =============================================================================
# Constants Tests
# =============================================================================


class TestPlanningConstants:
    """Tests for planning domain constants."""

    def test_planning_domain_type_enum_has_all_values(self):
        """PlanningDomainType enum has all 4 values."""
        values = [t.value for t in PlanningDomainType]
        assert "gastown" in values
        assert "gsd" in values
        assert "bmad" in values
        assert "planning_super" in values

    def test_domain_visual_styles_has_all_domains(self):
        """DOMAIN_VISUAL_STYLES has entries for all domains."""
        for domain_type in PlanningDomainType:
            assert domain_type in DOMAIN_VISUAL_STYLES

    def test_visual_styles_have_colors(self):
        """Each domain has primary and secondary colors defined."""
        for domain_type in PlanningDomainType:
            style = DOMAIN_VISUAL_STYLES[domain_type]
            assert "primary_color" in style
            assert "secondary_color" in style
            assert style["primary_color"].startswith("#")

    def test_conflict_resolution_strategies_defined(self):
        """CONFLICT_RESOLUTION_STRATEGIES has strategies."""
        assert "debate" in CONFLICT_RESOLUTION_STRATEGIES
        assert "simulation" in CONFLICT_RESOLUTION_STRATEGIES
        assert "prime_override" in CONFLICT_RESOLUTION_STRATEGIES

    def test_hybrid_patterns_defined(self):
        """HYBRID_PATTERNS has hybrid workflow patterns."""
        assert "gsd_research_bmad_planning" in HYBRID_PATTERNS
        assert "full_hybrid" in HYBRID_PATTERNS

    def test_version_is_semver(self):
        """PLANNING_DOMAIN_VERSION follows semver format."""
        parts = PLANNING_DOMAIN_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


# =============================================================================
# Integration Tests
# =============================================================================


class TestPlanningDomainIntegration:
    """Integration tests for planning domains."""

    def test_all_domains_have_unique_ids(self):
        """All 4 domains have unique domain IDs."""
        blueprints = [
            GastownDomainBlueprint.create(),
            GSDDomainBlueprint.create(),
            BMADDomainBlueprint.create(),
            PlanningSuperDomainBlueprint.create(),
        ]
        domain_ids = [bp.domain_id for bp in blueprints]
        assert len(domain_ids) == len(set(domain_ids))

    def test_all_agents_across_domains_have_unique_ids(self):
        """All agents across all domains have unique IDs."""
        all_agents = []
        all_agents.extend(GastownAgentBlueprint.all_agents())
        all_agents.extend(GSDAgentBlueprint.all_agents())
        all_agents.extend(BMADAgentBlueprint.all_agents())
        all_agents.extend(SuperDomainAgentBlueprint.all_agents())

        agent_ids = [a.agent_id for a in all_agents]
        assert len(agent_ids) == len(set(agent_ids))

    def test_all_skills_across_domains_have_unique_ids(self):
        """All skills across all domains have unique IDs."""
        all_skills = []
        all_skills.extend(GastownSkillBlueprint.all_skills())
        all_skills.extend(GSDSkillBlueprint.all_skills())
        all_skills.extend(BMADSkillBlueprint.all_skills())
        all_skills.extend(SuperDomainSkillBlueprint.all_skills())

        skill_ids = [s.skill_id for s in all_skills]
        assert len(skill_ids) == len(set(skill_ids))

    def test_role_distribution_across_domains(self):
        """All agent roles are used across domains."""
        all_agents = []
        all_agents.extend(GastownAgentBlueprint.all_agents())
        all_agents.extend(GSDAgentBlueprint.all_agents())
        all_agents.extend(BMADAgentBlueprint.all_agents())
        all_agents.extend(SuperDomainAgentBlueprint.all_agents())

        roles_used = {a.role for a in all_agents}
        assert AgentRole.COORDINATOR in roles_used
        assert AgentRole.EXECUTOR in roles_used
        assert AgentRole.REVIEWER in roles_used

    def test_workflow_types_distribution_across_domains(self):
        """Multiple workflow types used across domains."""
        all_workflows = []
        all_workflows.extend(GastownWorkflowBlueprint.all_workflows())
        all_workflows.extend(GSDWorkflowBlueprint.all_workflows())
        all_workflows.extend(BMADWorkflowBlueprint.all_workflows())
        all_workflows.extend(SuperDomainWorkflowBlueprint.all_workflows())

        types_used = {w.workflow_type for w in all_workflows}
        assert len(types_used) >= 5  # At least 5 different workflow types

    def test_total_agent_count(self):
        """Total of 24 agents across all 4 domains."""
        total = (
            len(GastownAgentBlueprint.all_agents()) +
            len(GSDAgentBlueprint.all_agents()) +
            len(BMADAgentBlueprint.all_agents()) +
            len(SuperDomainAgentBlueprint.all_agents())
        )
        assert total == 24

    def test_total_skill_count(self):
        """Total of 20 skills across all 4 domains."""
        total = (
            len(GastownSkillBlueprint.all_skills()) +
            len(GSDSkillBlueprint.all_skills()) +
            len(BMADSkillBlueprint.all_skills()) +
            len(SuperDomainSkillBlueprint.all_skills())
        )
        assert total == 20


# =============================================================================
# Async Tests (for Factory methods requiring TapeService)
# =============================================================================


@pytest.mark.asyncio
class TestPlanningDomainFactoryAsync:
    """Async tests for PlanningDomainFactory."""

    async def test_create_domain_gastown(self):
        """Factory can create Gastown domain with folder tree."""
        tape_repo = InMemoryTapeRepository()
        tape_svc = TapeService(tape_repo)

        folder_tree = await PlanningDomainFactory.create_domain(
            PlanningDomainType.GASTOWN, tape_svc
        )
        assert folder_tree is not None
        assert len(folder_tree.nodes) > 0

    async def test_create_all_domains(self):
        """Factory can create all 3 base domains."""
        tape_repo = InMemoryTapeRepository()
        tape_svc = TapeService(tape_repo)

        results = await PlanningDomainFactory.create_all_domains(tape_svc)
        assert len(results) == 3
        assert PlanningDomainType.GASTOWN in results
        assert PlanningDomainType.GSD in results
        assert PlanningDomainType.BMAD in results

    async def test_create_planning_super_domain(self):
        """Factory can create Super Domain (includes base domains)."""
        tape_repo = InMemoryTapeRepository()
        tape_svc = TapeService(tape_repo)

        folder_tree = await PlanningDomainFactory.create_planning_super_domain(tape_svc)
        assert folder_tree is not None
        # Super domain has more agents so more nodes
        assert len(folder_tree.nodes) > 10
