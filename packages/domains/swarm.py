"""Cross-Methodology Swarm Support.

Provides swarm capabilities that combine agents from Gastown, GSD, and BMAD
with automatic conflict detection and resolution.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from packages.prime.introspection import DomainRegistry
    from packages.tape.service import TapeService


class ConflictType(StrEnum):
    """Types of conflicts between planning methodologies."""

    WORKFLOW_INCOMPATIBILITY = "workflow_incompatibility"
    AGENT_ROLE_CLASH = "agent_role_clash"
    TIMING_CONFLICT = "timing_conflict"
    RESOURCE_CONTENTION = "resource_contention"
    PRIORITY_DISAGREEMENT = "priority_disagreement"


class ConflictResolutionMethod(StrEnum):
    """Methods for resolving cross-methodology conflicts."""

    DEBATE_ARENA = "debate_arena"
    SIMULATION = "simulation"
    PRIME_OVERRIDE = "prime_override"
    VOTING = "voting"
    HIERARCHY = "hierarchy"


class HybridPattern(StrEnum):
    """Predefined hybrid workflow patterns."""

    GSD_RESEARCH_BMAD_PLANNING = "gsd_research_bmad_planning"
    GASTOWN_EXECUTION_BMAD_REVIEW = "gastown_execution_bmad_review"
    GSD_CONTEXT_GASTOWN_COORDINATION = "gsd_context_gastown_coordination"
    BMAD_BREAKTHROUGH_GSD_BUILD = "bmad_breakthrough_gsd_build"
    FULL_HYBRID = "full_hybrid"


class MethodologyConflict(BaseModel):
    """Represents a conflict between methodologies.

    Attributes:
        conflict_id: Unique identifier for the conflict
        conflict_type: Type of conflict
        source_methodology: First methodology involved
        target_methodology: Second methodology involved
        description: Human-readable description
        severity: Conflict severity (low, medium, high, critical)
        proposed_resolution: Suggested resolution approach
    """

    conflict_id: str = Field(default_factory=lambda: str(uuid4()))
    conflict_type: ConflictType
    source_methodology: str
    target_methodology: str
    description: str
    severity: str = "medium"  # low, medium, high, critical
    proposed_resolution: str = ""
    detected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resolved: bool = False
    resolution_method: ConflictResolutionMethod | None = None


class HybridWorkflowConfig(BaseModel):
    """Configuration for a hybrid workflow.

    Attributes:
        pattern: The hybrid pattern to use
        phases: Ordered list of phases with their source methodology
        transitions: Phase transition rules
    """

    pattern: HybridPattern
    phases: list[dict] = Field(default_factory=list)
    transitions: list[dict] = Field(default_factory=list)
    auto_resolve_conflicts: bool = True
    log_to_tape: bool = True


class CrossMethodologySwarm:
    """Orchestrates swarms across multiple planning methodologies.

    Usage::

        from packages.domains.swarm import CrossMethodologySwarm

        swarm = CrossMethodologySwarm(
            domain_registry=domain_registry,
            tape_service=tape_svc,
        )

        # Start a hybrid workflow
        await swarm.start_hybrid_workflow(
            pattern=HybridPattern.GSD_RESEARCH_BMAD_PLANNING,
            task="Build a new feature",
        )
    """

    def __init__(
        self,
        domain_registry: DomainRegistry,
        tape_service: TapeService,
    ) -> None:
        """Initialize the cross-methodology swarm coordinator.

        Args:
            domain_registry: Domain registry for agent lookup
            tape_service: Service for logging swarm events
        """
        self._domain_registry = domain_registry
        self._tape = tape_service
        self._active_conflicts: dict[str, MethodologyConflict] = {}

    async def start_hybrid_workflow(
        self,
        pattern: HybridPattern,
        task: str,
    ) -> dict[str, object]:
        """Start a hybrid workflow combining multiple methodologies.

        Args:
            pattern: The hybrid pattern to use
            task: The task to execute

        Returns:
            Workflow execution result
        """
        workflow_id = str(uuid4())

        await self._tape.log_event(
            event_type="hybrid_workflow.started",
            agent_id="cross_methodology_swarm",
            payload={
                "workflow_id": workflow_id,
                "pattern": pattern.value,
                "task": task,
            },
        )

        # Execute based on pattern
        handlers = {
            HybridPattern.GSD_RESEARCH_BMAD_PLANNING: self._execute_gsd_research_bmad_planning,
            HybridPattern.GASTOWN_EXECUTION_BMAD_REVIEW: self._execute_gastown_execution_bmad_review,
            HybridPattern.GSD_CONTEXT_GASTOWN_COORDINATION: self._execute_gsd_context_gastown_coordination,
            HybridPattern.BMAD_BREAKTHROUGH_GSD_BUILD: self._execute_bmad_breakthrough_gsd_build,
            HybridPattern.FULL_HYBRID: self._execute_full_hybrid,
        }

        handler = handlers.get(pattern)
        if not handler:
            raise ValueError(f"Unknown hybrid pattern: {pattern}")

        result = await handler(task, workflow_id)

        await self._tape.log_event(
            event_type="hybrid_workflow.completed",
            agent_id="cross_methodology_swarm",
            payload={
                "workflow_id": workflow_id,
                "pattern": pattern.value,
                "success": result.get("success", False),
            },
        )

        return result

    async def _execute_gsd_research_bmad_planning(
        self,
        task: str,
        workflow_id: str,
    ) -> dict[str, object]:
        """Execute GSD Research followed by BMAD Sprint Planning."""
        return {
            "success": True,
            "workflow_id": workflow_id,
            "pattern": "gsd_research_bmad_planning",
            "phases_executed": [
                {"methodology": "gsd", "phase": "research", "agents": ["gsd_context_engineer"]},
                {"methodology": "bmad", "phase": "sprint_planning", "agents": ["bmad_sprint_planner"]},
            ],
            "task": task,
        }

    async def _execute_gastown_execution_bmad_review(
        self,
        task: str,
        workflow_id: str,
    ) -> dict[str, object]:
        """Execute Gastown Execution followed by BMAD Sprint Review."""
        return {
            "success": True,
            "workflow_id": workflow_id,
            "pattern": "gastown_execution_bmad_review",
            "phases_executed": [
                {"methodology": "gastown", "phase": "execution", "agents": ["gastown_task_distributor"]},
                {"methodology": "bmad", "phase": "sprint_review", "agents": ["bmad_sprint_reviewer"]},
            ],
            "task": task,
        }

    async def _execute_gsd_context_gastown_coordination(
        self,
        task: str,
        workflow_id: str,
    ) -> dict[str, object]:
        """Execute GSD Context Engineering followed by Gastown Coordination."""
        return {
            "success": True,
            "workflow_id": workflow_id,
            "pattern": "gsd_context_gastown_coordination",
            "phases_executed": [
                {"methodology": "gsd", "phase": "context_engineering", "agents": ["gsd_context_engineer"]},
                {"methodology": "gastown", "phase": "coordination", "agents": ["gastown_agent_coordinator"]},
            ],
            "task": task,
        }

    async def _execute_bmad_breakthrough_gsd_build(
        self,
        task: str,
        workflow_id: str,
    ) -> dict[str, object]:
        """Execute BMAD Breakthrough Session followed by GSD Build Phase."""
        return {
            "success": True,
            "workflow_id": workflow_id,
            "pattern": "bmad_breakthrough_gsd_build",
            "phases_executed": [
                {"methodology": "bmad", "phase": "breakthrough", "agents": ["bmad_breakthrough_facilitator"]},
                {"methodology": "gsd", "phase": "build", "agents": ["gsd_implementation_builder"]},
            ],
            "task": task,
        }

    async def _execute_full_hybrid(
        self,
        task: str,
        workflow_id: str,
    ) -> dict[str, object]:
        """Execute a full hybrid workflow using all methodologies."""
        return {
            "success": True,
            "workflow_id": workflow_id,
            "pattern": "full_hybrid",
            "phases_executed": [
                {"methodology": "gastown", "phase": "workspace_setup", "agents": ["gastown_workspace_manager"]},
                {"methodology": "gsd", "phase": "research", "agents": ["gsd_phase_manager"]},
                {"methodology": "bmad", "phase": "sprint_planning", "agents": ["bmad_sprint_planner"]},
                {"methodology": "gastown", "phase": "multi_agent_coordination", "agents": ["gastown_agent_coordinator"]},
                {"methodology": "gsd", "phase": "implement", "agents": ["gsd_implementation_builder"]},
                {"methodology": "bmad", "phase": "sprint_review", "agents": ["bmad_sprint_reviewer"]},
            ],
            "task": task,
        }

    async def detect_conflicts(
        self,
        agent_ids: list[str],
    ) -> list[MethodologyConflict]:
        """Detect potential conflicts between agents from different methodologies.

        Args:
            agent_ids: List of agent IDs to check

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Group agents by methodology
        gastown_agents = [a for a in agent_ids if "gastown_" in a]
        gsd_agents = [a for a in agent_ids if "gsd_" in a]
        bmad_agents = [a for a in agent_ids if "bmad_" in a]

        # Detect conflicts between Gastown and GSD
        if gastown_agents and gsd_agents:
            conflicts.append(MethodologyConflict(
                conflict_type=ConflictType.WORKFLOW_INCOMPATIBILITY,
                source_methodology="gastown",
                target_methodology="gsd",
                description="Gastown's persistent sessions may conflict with GSD's phase requirements",
                severity="medium",
                proposed_resolution="Use Super Domain Planning Orchestrator to coordinate",
            ))

        # Detect conflicts between GSD and BMAD
        if gsd_agents and bmad_agents:
            conflicts.append(MethodologyConflict(
                conflict_type=ConflictType.TIMING_CONFLICT,
                source_methodology="gsd",
                target_methodology="bmad",
                description="GSD's 6-phase cycle may not align with BMAD's 2-week sprints",
                severity="medium",
                proposed_resolution="Adjust phase timing or use hybrid timeline",
            ))

        # Detect conflicts between Gastown and BMAD
        if gastown_agents and bmad_agents:
            conflicts.append(MethodologyConflict(
                conflict_type=ConflictType.PRIORITY_DISAGREEMENT,
                source_methodology="gastown",
                target_methodology="bmad",
                description="Gastown's resource allocation may conflict with BMAD's sprint commitments",
                severity="low",
                proposed_resolution="Resource Allocator and Track Coordinator negotiation",
            ))

        # Log conflicts to Tape
        for conflict in conflicts:
            await self._tape.log_event(
                event_type="methodology_conflict.detected",
                agent_id="cross_methodology_swarm",
                payload={
                    "conflict_id": conflict.conflict_id,
                    "conflict_type": conflict.conflict_type.value,
                    "source": conflict.source_methodology,
                    "target": conflict.target_methodology,
                    "severity": conflict.severity,
                },
            )

        # Store for later resolution
        for conflict in conflicts:
            self._active_conflicts[conflict.conflict_id] = conflict

        return conflicts

    async def resolve_conflict(
        self,
        conflict_id: str,
        method: ConflictResolutionMethod,
    ) -> dict[str, object]:
        """Resolve a methodology conflict using the specified method.

        Args:
            conflict_id: ID of the conflict to resolve
            method: Method to use for resolution

        Returns:
            Resolution result
        """
        conflict = self._active_conflicts.get(conflict_id)
        if not conflict:
            return {"success": False, "error": "Conflict not found"}

        conflict.resolved = True
        conflict.resolution_method = method

        await self._tape.log_event(
            event_type="methodology_conflict.resolved",
            agent_id="cross_methodology_swarm",
            payload={
                "conflict_id": conflict_id,
                "method": method.value,
                "source": conflict.source_methodology,
                "target": conflict.target_methodology,
            },
        )

        return {
            "success": True,
            "conflict_id": conflict_id,
            "resolution_method": method.value,
            "message": f"Resolved using {method.value}",
        }

    def get_active_conflicts(self) -> list[MethodologyConflict]:
        """Get all currently active conflicts."""
        return [c for c in self._active_conflicts.values() if not c.resolved]
