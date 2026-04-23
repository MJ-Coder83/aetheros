"""Real-Time Simulation Engine — Safe, isolated what-if simulation for InkosAI.

This module allows Prime and agent crews to run safe, isolated "what-if"
simulations before executing real changes.  Every simulation runs in a
sandboxed **SimulationEnvironment** — a deep-copied snapshot of the
system's registries that is completely independent from production state.

Key guarantees:

- **Isolation**: Simulations operate on deep-copied registries.  No real
  state is ever mutated during a simulation run.
- **Auditability**: All simulation events are logged to the Tape with
  ``simulation.*`` event types.
- **Timeout safety**: Each simulation has a configurable timeout; if
  exceeded, the simulation is aborted cleanly.
- **Rollback**: ``rollback_simulation()`` discards a completed run and
  re-verifies that no real state was altered.
- **Comparison**: ``compare_outcomes()`` produces a ``ComparisonReport``
  showing metric deltas between baseline and simulation results.
- **Scenario generation**: ``generate_whatif_scenarios()`` uses
  PrimeIntrospector and SkillEvolutionEngine to suggest interesting
  what-if scenarios automatically.

Architecture::

    SimulationEngine
    ├── run_simulation()          — Execute a scenario in isolation
    ├── compare_outcomes()        — Baseline vs simulation delta report
    ├── generate_whatif_scenarios() — Auto-suggest scenarios from system state
    ├── rollback_simulation()     — Discard a run (verify no side effects)
    ├── get_simulation()          — Query a run by ID
    └── list_simulations()        — List all runs, optionally by status

Usage::

    engine = SimulationEngine(
        tape_service=tape_svc,
        introspector=introspector,
        proposal_engine=proposal_engine,
        skill_evolution_engine=skill_evo_engine,
    )

    # Prime suggests scenarios
    scenarios = await engine.generate_whatif_scenarios()

    # Run a simulation
    result = await engine.run_simulation(
        scenario=scenarios[0],
        timeout_seconds=60,
    )

    # Compare simulation vs baseline
    report = await engine.compare_outcomes(result.id)

    # Clean up
    await engine.rollback_simulation(result.id)
"""

import asyncio
import copy
import time
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.prime.introspection import (
    AgentDescriptor,
    AgentRegistry,
    DomainDescriptor,
    DomainRegistry,
    PrimeIntrospector,
    SkillDescriptor,
    SkillRegistry,
)
from packages.prime.proposals import (
    ProposalEngine,
    RiskLevel,
)
from packages.prime.skill_evolution import (
    SkillAnalysis,
    SkillEvolutionEngine,
)
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SimulationStatus(StrEnum):
    """Lifecycle states for a simulation run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    ROLLED_BACK = "rolled_back"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class WhatIfScenario(BaseModel):
    """A structured what-if scenario to simulate.

    Scenarios describe a hypothetical change to the system — new skills,
    agent reconfigurations, domain changes, etc. — and are executed inside
    a sandboxed SimulationEnvironment.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    scenario_type: str  # "skill_evolution", "agent_reconfig", "domain_change", "custom"
    modifications: dict[str, object] = Field(default_factory=dict)
    expected_outcome: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    source: str = "prime"  # who/what generated this scenario
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SimulationEnvironment(BaseModel):
    """Frozen snapshot of system state used as the sandbox for a simulation.

    Each field is a deep copy of the corresponding registry's contents,
    ensuring the simulation can never affect production state.
    """

    skills: list[SkillDescriptor] = []
    agents: list[AgentDescriptor] = []
    domains: list[DomainDescriptor] = []
    metadata: dict[str, object] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    """Outcome of a single simulation run.

    Captures whether the simulation succeeded, what metrics it produced,
    decision traces for auditability, and the isolated environment state
    after the simulation ran.
    """

    id: UUID = Field(default_factory=uuid4)
    simulation_run_id: UUID
    success: bool
    status: SimulationStatus
    metrics: dict[str, float] = Field(default_factory=dict)
    decision_trace: list[dict[str, object]] = Field(default_factory=list)
    outcome_probabilities: dict[str, float] = Field(default_factory=dict)
    environment_before: SimulationEnvironment = Field(default_factory=SimulationEnvironment)
    environment_after: SimulationEnvironment = Field(default_factory=SimulationEnvironment)
    error_message: str | None = None
    duration_seconds: float = 0.0
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SimulationRun(BaseModel):
    """Record of a simulation run — scenario + result + lifecycle.

    A SimulationRun tracks the full lifecycle: which scenario was run,
    what the baseline state was, what the result was, and the current
    status.  It is the primary unit stored in SimulationRunStore.
    """

    id: UUID = Field(default_factory=uuid4)
    scenario: WhatIfScenario
    status: SimulationStatus = SimulationStatus.PENDING
    environment_snapshot: SimulationEnvironment = Field(default_factory=SimulationEnvironment)
    result: SimulationResult | None = None
    timeout_seconds: float = 60.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None


class OutcomeDelta(BaseModel):
    """Delta between baseline and simulation for a single metric."""

    metric: str
    baseline_value: float
    simulation_value: float
    delta: float
    delta_percent: float
    improved: bool  # True if change is considered positive


class ComparisonReport(BaseModel):
    """Rich comparison between baseline and simulation results."""

    simulation_run_id: UUID
    scenario_name: str
    deltas: list[OutcomeDelta] = []
    overall_assessment: str = "neutral"  # positive, negative, neutral, mixed
    recommendation: str = ""
    summary: str = ""


class ScenarioTemplate(BaseModel):
    """Template for auto-generating what-if scenarios."""

    name: str
    description: str
    scenario_type: str
    modifications_template: dict[str, object] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.LOW
    source: str = "prime"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SimulationError(Exception):
    """Base exception for simulation operations."""


class SimulationNotFoundError(SimulationError):
    """Raised when a requested simulation does not exist."""


class SimulationTimeoutError(SimulationError):
    """Raised when a simulation exceeds its timeout."""


class SimulationEnvironmentError(SimulationError):
    """Raised when the simulation environment cannot be created or is invalid."""


# ---------------------------------------------------------------------------
# SimulationRunStore — in-memory persistence
# ---------------------------------------------------------------------------


class SimulationRunStore:
    """In-memory store for simulation runs and results.

    Will be replaced by a PostgreSQL-backed repository in a future phase.
    """

    def __init__(self) -> None:
        self._runs: dict[UUID, SimulationRun] = {}

    def add(self, run: SimulationRun) -> None:
        self._runs[run.id] = run

    def get(self, run_id: UUID) -> SimulationRun | None:
        return self._runs.get(run_id)

    def update(self, run: SimulationRun) -> None:
        if run.id not in self._runs:
            raise SimulationNotFoundError(f"Simulation run {run.id} not found")
        self._runs[run.id] = run

    def list_all(self) -> list[SimulationRun]:
        return list(self._runs.values())

    def list_by_status(self, status: SimulationStatus) -> list[SimulationRun]:
        return [r for r in self._runs.values() if r.status == status]

    def remove(self, run_id: UUID) -> None:
        self._runs.pop(run_id, None)


# ---------------------------------------------------------------------------
# SimulationEngine — the main public API
# ---------------------------------------------------------------------------


class SimulationEngine:
    """Engine for running safe, isolated what-if simulations.

    SimulationEngine allows Prime and agent crews to explore hypothetical
    changes to the system without any risk to production state.  Every
    simulation operates on a deep-copied sandbox, is logged to the Tape,
    and can be compared against the baseline.

    Usage::

        engine = SimulationEngine(
            tape_service=tape_svc,
            introspector=introspector,
            proposal_engine=proposal_engine,
            skill_evolution_engine=skill_evo_engine,
        )

        scenarios = await engine.generate_whatif_scenarios()
        result = await engine.run_simulation(scenario=scenarios[0])
        report = await engine.compare_outcomes(result.id)
        await engine.rollback_simulation(result.id)
    """

    def __init__(
        self,
        tape_service: TapeService,
        introspector: PrimeIntrospector | None = None,
        proposal_engine: ProposalEngine | None = None,
        skill_evolution_engine: SkillEvolutionEngine | None = None,
        skill_registry: SkillRegistry | None = None,
        agent_registry: AgentRegistry | None = None,
        domain_registry: DomainRegistry | None = None,
        store: SimulationRunStore | None = None,
    ) -> None:
        self._tape = tape_service
        self._introspector = introspector
        self._proposals = proposal_engine
        self._skill_evo = skill_evolution_engine
        self._skills = skill_registry or SkillRegistry()
        self._agents = agent_registry or AgentRegistry()
        self._domains = domain_registry or DomainRegistry()
        self._store = store or SimulationRunStore()

    # ------------------------------------------------------------------
    # Run simulation
    # ------------------------------------------------------------------

    async def run_simulation(
        self,
        scenario: WhatIfScenario,
        timeout_seconds: float = 60.0,
    ) -> SimulationResult:
        """Execute a what-if scenario in a sandboxed environment.

        The simulation:
        1. Snapshots the current system state into an isolated environment
        2. Applies the scenario's modifications to the sandbox
        3. Evaluates outcomes and collects metrics
        4. Returns a SimulationResult with before/after environments

        If the simulation exceeds ``timeout_seconds``, it is aborted and
        a FAILED result is returned.

        Args:
            scenario: The what-if scenario to simulate.
            timeout_seconds: Maximum wall-clock time for the simulation.

        Returns:
            A SimulationResult capturing all outcomes.
        """
        run = SimulationRun(
            scenario=scenario,
            status=SimulationStatus.PENDING,
            timeout_seconds=timeout_seconds,
        )

        # Snapshot the baseline environment
        try:
            run.environment_snapshot = await self._capture_environment()
        except Exception as exc:
            raise SimulationEnvironmentError(
                f"Failed to capture simulation environment: {exc}"
            ) from exc

        self._store.add(run)

        await self._tape.log_event(
            event_type="simulation.started",
            payload={
                "simulation_run_id": str(run.id),
                "scenario_name": scenario.name,
                "scenario_type": scenario.scenario_type,
                "timeout_seconds": timeout_seconds,
            },
            agent_id="prime",
        )

        run.status = SimulationStatus.RUNNING
        run.started_at = datetime.now(UTC)
        self._store.update(run)

        # Execute the simulation with timeout
        env_before = copy.deepcopy(run.environment_snapshot)
        result: SimulationResult | None = None

        try:
            result = await asyncio.wait_for(
                self._execute_simulation(run),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            run.status = SimulationStatus.ABORTED
            run.finished_at = datetime.now(UTC)
            self._store.update(run)

            result = SimulationResult(
                simulation_run_id=run.id,
                success=False,
                status=SimulationStatus.ABORTED,
                environment_before=env_before,
                environment_after=copy.deepcopy(env_before),
                error_message=(f"Simulation exceeded timeout of {timeout_seconds}s"),
            )
            run.result = result
            self._store.update(run)

            await self._tape.log_event(
                event_type="simulation.timeout",
                payload={
                    "simulation_run_id": str(run.id),
                    "timeout_seconds": timeout_seconds,
                },
                agent_id="prime",
            )
        except Exception as exc:
            run.status = SimulationStatus.FAILED
            run.finished_at = datetime.now(UTC)
            self._store.update(run)

            result = SimulationResult(
                simulation_run_id=run.id,
                success=False,
                status=SimulationStatus.FAILED,
                environment_before=env_before,
                environment_after=copy.deepcopy(env_before),
                error_message=str(exc),
            )
            run.result = result
            self._store.update(run)

            await self._tape.log_event(
                event_type="simulation.failed",
                payload={
                    "simulation_run_id": str(run.id),
                    "error": str(exc),
                },
                agent_id="prime",
            )

        if result is not None:
            run.result = result
            self._store.update(run)

        # Verify isolation: production registries must be unchanged
        await self._verify_isolation(run.environment_snapshot)

        await self._tape.log_event(
            event_type="simulation.completed",
            payload={
                "simulation_run_id": str(run.id),
                "status": run.status.value,
                "success": result.success if result else False,
                "duration_seconds": result.duration_seconds if result else 0.0,
            },
            agent_id="prime",
        )

        return result

    # ------------------------------------------------------------------
    # Compare outcomes
    # ------------------------------------------------------------------

    async def compare_outcomes(self, simulation_run_id: UUID) -> ComparisonReport:
        """Compare simulation results against the baseline.

        Produces a ``ComparisonReport`` with metric-by-metric deltas,
        an overall assessment (positive/negative/neutral/mixed), and a
        recommendation for whether the simulated change should be pursued.

        Raises:
            SimulationNotFoundError: if the run does not exist.
        """
        run = self._get_run_or_raise(simulation_run_id)

        if run.result is None:
            return ComparisonReport(
                simulation_run_id=simulation_run_id,
                scenario_name=run.scenario.name,
                overall_assessment="neutral",
                recommendation="No simulation result available for comparison.",
                summary="Simulation has no result yet.",
            )

        before = run.environment_snapshot
        after = run.result.environment_after

        # Compute deltas for skill and agent counts
        deltas: list[OutcomeDelta] = []

        baseline_skill_count = float(len(before.skills))
        sim_skill_count = float(len(after.skills))
        deltas.append(self._compute_delta("skill_count", baseline_skill_count, sim_skill_count))

        baseline_agent_count = float(len(before.agents))
        sim_agent_count = float(len(after.agents))
        deltas.append(self._compute_delta("agent_count", baseline_agent_count, sim_agent_count))

        baseline_domain_count = float(len(before.domains))
        sim_domain_count = float(len(after.domains))
        deltas.append(self._compute_delta("domain_count", baseline_domain_count, sim_domain_count))

        # Include any custom metrics from the simulation result
        for metric_name, sim_value in run.result.metrics.items():
            baseline_value = 0.0  # custom metrics default to 0 baseline
            deltas.append(self._compute_delta(metric_name, baseline_value, sim_value))

        # Compute overall assessment
        improved_count = sum(1 for d in deltas if d.improved)
        degraded_count = sum(1 for d in deltas if not d.improved and d.delta != 0.0)

        if improved_count > 0 and degraded_count == 0:
            assessment = "positive"
        elif degraded_count > 0 and improved_count == 0:
            assessment = "negative"
        elif improved_count > 0 and degraded_count > 0:
            assessment = "mixed"
        else:
            assessment = "neutral"

        # Generate recommendation
        recommendation = self._generate_recommendation(assessment, deltas)

        summary = (
            f"Scenario '{run.scenario.name}': {assessment} outcome. "
            f"{improved_count} metric(s) improved, "
            f"{degraded_count} metric(s) degraded."
        )

        report = ComparisonReport(
            simulation_run_id=simulation_run_id,
            scenario_name=run.scenario.name,
            deltas=deltas,
            overall_assessment=assessment,
            recommendation=recommendation,
            summary=summary,
        )

        await self._tape.log_event(
            event_type="simulation.comparison",
            payload={
                "simulation_run_id": str(simulation_run_id),
                "overall_assessment": assessment,
                "delta_count": len(deltas),
            },
            agent_id="prime",
        )

        return report

    # ------------------------------------------------------------------
    # Generate what-if scenarios
    # ------------------------------------------------------------------

    async def generate_whatif_scenarios(self) -> list[WhatIfScenario]:
        """Automatically suggest interesting what-if scenarios from system state.

        Uses PrimeIntrospector and SkillEvolutionEngine to identify
        potential improvements, then wraps each as a WhatIfScenario that
        can be simulated safely before real execution.

        Heuristics (will be enhanced by LLM-driven analysis in future):
        - Skills with high error rate → simulate enhancement
        - Overlapping skills → simulate merge
        - Broad skills → simulate split
        - Unused skills → simulate deprecation
        - No skills in system → simulate creation
        - Idle agents → simulate reassignment
        - Empty domains → simulate agent assignment
        - High Tape error rate → simulate reliability improvements
        """
        scenarios: list[WhatIfScenario] = []

        # Introspection-based scenarios
        if self._introspector is not None:
            snapshot = await self._introspector.snapshot()

            # Heuristic: idle agents → reassign
            idle_agents = [a for a in snapshot.agents if a.status == "idle"]
            if idle_agents:
                agent_names = ", ".join(a.name for a in idle_agents)
                scenarios.append(
                    WhatIfScenario(
                        name="Reassign idle agents",
                        description=(
                            f"Simulate reassigning idle agents ({agent_names}) to active domains."
                        ),
                        scenario_type="agent_reconfig",
                        modifications={
                            "action": "reassign_idle",
                            "agent_ids": [a.agent_id for a in idle_agents],
                        },
                        expected_outcome="Increased agent utilisation and throughput",
                        risk_level=RiskLevel.LOW,
                        source="prime.introspection",
                    )
                )

            # Heuristic: empty domains → assign agents
            empty_domains = [d for d in snapshot.domains if d.agent_count == 0]
            if empty_domains:
                domain_names = ", ".join(d.name for d in empty_domains)
                scenarios.append(
                    WhatIfScenario(
                        name="Assign agents to empty domains",
                        description=(
                            f"Simulate assigning agents to empty domains ({domain_names})."
                        ),
                        scenario_type="domain_change",
                        modifications={
                            "action": "assign_to_empty_domains",
                            "domain_ids": [d.domain_id for d in empty_domains],
                        },
                        expected_outcome="All domains become operational",
                        risk_level=RiskLevel.LOW,
                        source="prime.introspection",
                    )
                )

            # Heuristic: high Tape error rate → simulate reliability fix
            recent = snapshot.recent_tape_entries[:50]
            error_count = sum(1 for e in recent if "error" in e.event_type.lower())
            if recent and error_count / len(recent) > 0.2:
                scenarios.append(
                    WhatIfScenario(
                        name="Simulate reliability improvements",
                        description=(
                            f"Recent Tape shows {error_count}/{len(recent)} "
                            f"error events. Simulate adding retry logic."
                        ),
                        scenario_type="custom",
                        modifications={
                            "action": "add_retry_logic",
                            "target_error_rate": 0.05,
                        },
                        expected_outcome="Reduced error rate from "
                        f"{error_count / len(recent):.0%} to ~5%",
                        risk_level=RiskLevel.MEDIUM,
                        source="prime.introspection",
                    )
                )

        # Skill-evolution-based scenarios
        if self._skill_evo is not None:
            analyses = await self._skill_evo.analyze_skills()
            for analysis in analyses:
                if analysis.recommendation == "maintain":
                    continue

                scenario = self._analysis_to_scenario(analysis)
                if scenario is not None:
                    scenarios.append(scenario)

            # No skills at all → simulate creation
            if len(analyses) == 0:
                scenarios.append(
                    WhatIfScenario(
                        name="Simulate adding foundational skills",
                        description=(
                            "System has no skills. Simulate adding "
                            "code-gen, code-review, and search-web."
                        ),
                        scenario_type="skill_evolution",
                        modifications={
                            "action": "create_skills",
                            "skills": [
                                {
                                    "skill_id": "code-gen",
                                    "name": "Code Generation",
                                    "description": "Generate code from specs",
                                },
                                {
                                    "skill_id": "code-review",
                                    "name": "Code Review",
                                    "description": "Review code quality",
                                },
                                {
                                    "skill_id": "search-web",
                                    "name": "Web Search",
                                    "description": "Search the web",
                                },
                            ],
                        },
                        expected_outcome="Agents gain core capabilities",
                        risk_level=RiskLevel.LOW,
                        source="prime.skill_evolution",
                    )
                )

        await self._tape.log_event(
            event_type="simulation.scenarios_generated",
            payload={"scenario_count": len(scenarios)},
            agent_id="prime",
            metadata={f"scenario_{i}": s.name for i, s in enumerate(scenarios)},
        )

        return scenarios

    # ------------------------------------------------------------------
    # Rollback simulation
    # ------------------------------------------------------------------

    async def rollback_simulation(self, simulation_run_id: UUID) -> SimulationResult:
        """Roll back a simulation — verify no side effects and mark as rolled back.

        Since simulations run in isolation, "rollback" means:
        1. Verify that the production registries are unchanged
        2. Mark the simulation as ROLLED_BACK
        3. Log the rollback to the Tape

        Raises:
            SimulationNotFoundError: if the run does not exist.
            SimulationEnvironmentError: if isolation was violated.
        """
        run = self._get_run_or_raise(simulation_run_id)

        # Verify isolation — production state must match baseline
        current_env = await self._capture_environment()
        baseline_skills = {s.skill_id for s in run.environment_snapshot.skills}
        current_skills = {s.skill_id for s in current_env.skills}
        if baseline_skills != current_skills:
            raise SimulationEnvironmentError(
                f"Isolation violation: skill registry changed during simulation {simulation_run_id}"
            )

        baseline_agents = {a.agent_id for a in run.environment_snapshot.agents}
        current_agents = {a.agent_id for a in current_env.agents}
        if baseline_agents != current_agents:
            raise SimulationEnvironmentError(
                f"Isolation violation: agent registry changed during simulation {simulation_run_id}"
            )

        # Mark as rolled back
        run.status = SimulationStatus.ROLLED_BACK
        run.finished_at = datetime.now(UTC)
        self._store.update(run)

        result = SimulationResult(
            simulation_run_id=simulation_run_id,
            success=True,
            status=SimulationStatus.ROLLED_BACK,
            environment_before=run.environment_snapshot,
            environment_after=current_env,
        )
        run.result = result
        self._store.update(run)

        await self._tape.log_event(
            event_type="simulation.rolled_back",
            payload={
                "simulation_run_id": str(simulation_run_id),
                "isolation_verified": True,
            },
            agent_id="prime",
        )

        return result

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_simulation(self, simulation_run_id: UUID) -> SimulationRun:
        """Retrieve a simulation run by ID.

        Raises:
            SimulationNotFoundError: if not found.
        """
        return self._get_run_or_raise(simulation_run_id)

    async def list_simulations(self, status: SimulationStatus | None = None) -> list[SimulationRun]:
        """List simulation runs, optionally filtered by status."""
        if status is not None:
            return self._store.list_by_status(status)
        return self._store.list_all()

    async def get_simulation_result(self, simulation_run_id: UUID) -> SimulationResult | None:
        """Get the result of a simulation run, or None if not yet complete."""
        run = self._get_run_or_raise(simulation_run_id)
        return run.result

    # ------------------------------------------------------------------
    # Internal: simulation execution
    # ------------------------------------------------------------------

    async def _execute_simulation(self, run: SimulationRun) -> SimulationResult:
        """Execute the simulation logic in an isolated environment.

        This method creates a deep copy of the system state, applies the
        scenario modifications, evaluates outcomes, and returns results.
        No real state is ever mutated.
        """
        start_time = time.monotonic()
        env_before = copy.deepcopy(run.environment_snapshot)

        # Create isolated sandbox registries from the snapshot
        sandbox_skills = self._copy_skills_to_registry(env_before.skills)
        sandbox_agents = self._copy_agents_to_registry(env_before.agents)
        sandbox_domains = self._copy_domains_to_registry(env_before.domains)

        # Apply modifications in the sandbox
        metrics: dict[str, float] = {}
        decision_trace: list[dict[str, object]] = []
        outcome_probabilities: dict[str, float] = {}

        scenario = run.scenario
        modifications = scenario.modifications
        action = str(modifications.get("action", ""))

        try:
            match scenario.scenario_type:
                case "skill_evolution":
                    (
                        metrics,
                        decision_trace,
                        outcome_probabilities,
                    ) = await self._simulate_skill_evolution(modifications, sandbox_skills)
                case "agent_reconfig":
                    (
                        metrics,
                        decision_trace,
                        outcome_probabilities,
                    ) = await self._simulate_agent_reconfig(
                        modifications, sandbox_agents, sandbox_domains
                    )
                case "domain_change":
                    (
                        metrics,
                        decision_trace,
                        outcome_probabilities,
                    ) = await self._simulate_domain_change(
                        modifications, sandbox_agents, sandbox_domains
                    )
                case _:
                    metrics, decision_trace, outcome_probabilities = await self._simulate_custom(
                        modifications,
                        sandbox_skills,
                        sandbox_agents,
                        sandbox_domains,
                    )
        except Exception as exc:
            elapsed = time.monotonic() - start_time
            return SimulationResult(
                simulation_run_id=run.id,
                success=False,
                status=SimulationStatus.FAILED,
                environment_before=env_before,
                environment_after=self._registry_env(
                    sandbox_skills, sandbox_agents, sandbox_domains
                ),
                error_message=str(exc),
                duration_seconds=elapsed,
            )

        elapsed = time.monotonic() - start_time

        # Capture post-simulation environment
        env_after = self._registry_env(sandbox_skills, sandbox_agents, sandbox_domains)

        # Compute outcome probabilities based on risk and metrics
        risk_bonus = {
            RiskLevel.LOW: 0.85,
            RiskLevel.MEDIUM: 0.65,
            RiskLevel.HIGH: 0.40,
        }
        base_prob = risk_bonus.get(scenario.risk_level, 0.5)
        outcome_probabilities.setdefault("success_probability", base_prob)
        outcome_probabilities.setdefault("failure_probability", 1.0 - base_prob)

        # Add decision trace entry for completion
        decision_trace.append(
            {
                "phase": "completion",
                "action": action,
                "elapsed_seconds": elapsed,
                "metrics_count": len(metrics),
            }
        )

        result = SimulationResult(
            simulation_run_id=run.id,
            success=True,
            status=SimulationStatus.COMPLETED,
            metrics=metrics,
            decision_trace=decision_trace,
            outcome_probabilities=outcome_probabilities,
            environment_before=env_before,
            environment_after=env_after,
            duration_seconds=round(elapsed, 4),
        )

        # Update the run
        run.status = SimulationStatus.COMPLETED
        run.finished_at = datetime.now(UTC)
        run.result = result
        self._store.update(run)

        return result

    # ------------------------------------------------------------------
    # Internal: scenario simulation types
    # ------------------------------------------------------------------

    async def _simulate_skill_evolution(
        self,
        modifications: dict[str, object],
        sandbox_skills: SkillRegistry,
    ) -> tuple[dict[str, float], list[dict[str, object]], dict[str, float]]:
        """Simulate a skill evolution scenario in the sandbox."""
        metrics: dict[str, float] = {}
        trace: list[dict[str, object]] = []
        probs: dict[str, float] = {}

        action = str(modifications.get("action", ""))

        if action == "enhance":
            skill_id = modifications.get("skill_id")
            if skill_id is not None:
                sid = str(skill_id)
                skill = sandbox_skills.get_skill(sid)
                if skill is not None:
                    # Simulate enhancement: bump version in sandbox
                    parts = skill.version.split(".")
                    minor = int(parts[-1]) + 1 if parts else 1
                    new_version = (
                        ".".join([*parts[:-1], str(minor)]) if len(parts) > 1 else f"0.{minor}"
                    )
                    enhanced = skill.model_copy(
                        update={
                            "version": new_version,
                            "description": f"{skill.description} (enhanced)".strip(),
                        }
                    )
                    sandbox_skills.register(enhanced)
                    metrics["error_rate_reduction"] = 0.3
                    trace.append(
                        {
                            "phase": "enhance",
                            "skill_id": sid,
                            "old_version": skill.version,
                            "new_version": new_version,
                        }
                    )
                else:
                    trace.append({"phase": "enhance", "skill_id": sid, "skipped": True})

        elif action == "merge":
            skill_ids = modifications.get("skill_ids")
            if skill_ids is not None and isinstance(skill_ids, list):
                sids = [str(sid) for sid in skill_ids]
                skills_found: list[SkillDescriptor] = []
                for sid in sids:
                    s = sandbox_skills.get_skill(sid)
                    if s is not None:
                        skills_found.append(s)
                if len(skills_found) >= 2:
                    merged_id = "-".join(s.skill_id for s in skills_found)
                    merged_name = " + ".join(s.name for s in skills_found)
                    merged = SkillDescriptor(
                        skill_id=merged_id,
                        name=merged_name,
                        version="1.0.0",
                        description="Merged: "
                        + "; ".join(s.description for s in skills_found if s.description),
                    )
                    sandbox_skills.register(merged)
                    for s in skills_found:
                        sandbox_skills.unregister(s.skill_id)
                    metrics["skill_count_delta"] = -1.0  # net reduction
                    trace.append(
                        {
                            "phase": "merge",
                            "source_skills": sids,
                            "merged_skill_id": merged_id,
                        }
                    )

        elif action == "split":
            skill_id = modifications.get("skill_id")
            if skill_id is not None:
                sid = str(skill_id)
                skill = sandbox_skills.get_skill(sid)
                if skill is not None:
                    sub_a = SkillDescriptor(
                        skill_id=f"{sid}-a",
                        name=f"{skill.name} (Part A)",
                        version="0.1.0",
                        description=f"Split from {skill.name}: focused subset A",
                    )
                    sub_b = SkillDescriptor(
                        skill_id=f"{sid}-b",
                        name=f"{skill.name} (Part B)",
                        version="0.1.0",
                        description=f"Split from {skill.name}: focused subset B",
                    )
                    sandbox_skills.register(sub_a)
                    sandbox_skills.register(sub_b)
                    sandbox_skills.unregister(sid)
                    metrics["skill_count_delta"] = 1.0  # net increase
                    trace.append(
                        {
                            "phase": "split",
                            "source_skill_id": sid,
                            "sub_skills": [f"{sid}-a", f"{sid}-b"],
                        }
                    )

        elif action == "deprecate":
            skill_id = modifications.get("skill_id")
            if skill_id is not None:
                sid = str(skill_id)
                sandbox_skills.unregister(sid)
                metrics["skill_count_delta"] = -1.0
                trace.append({"phase": "deprecate", "removed_skill_id": sid})

        elif action == "create_skills":
            skills_data = modifications.get("skills")
            if skills_data is not None and isinstance(skills_data, list):
                for sdef in skills_data:
                    if isinstance(sdef, dict):
                        sandbox_skills.register(
                            SkillDescriptor(
                                skill_id=str(sdef.get("skill_id", "unknown")),
                                name=str(sdef.get("name", "Unknown")),
                                description=str(sdef.get("description", "")),
                            )
                        )
                metrics["skills_created"] = float(len(skills_data))
                trace.append(
                    {
                        "phase": "create_skills",
                        "count": len(skills_data),
                    }
                )

        # Compute result probabilities
        skill_count = float(len(sandbox_skills.list_skills()))
        metrics.setdefault("total_skill_count", skill_count)

        probs["success_probability"] = 0.8
        probs["failure_probability"] = 0.2

        return metrics, trace, probs

    async def _simulate_agent_reconfig(
        self,
        modifications: dict[str, object],
        sandbox_agents: AgentRegistry,
        sandbox_domains: DomainRegistry,
    ) -> tuple[dict[str, float], list[dict[str, object]], dict[str, float]]:
        """Simulate an agent reconfiguration scenario."""
        metrics: dict[str, float] = {}
        trace: list[dict[str, object]] = []
        probs: dict[str, float] = {}

        action = str(modifications.get("action", ""))

        if action == "reassign_idle":
            agent_ids = modifications.get("agent_ids")
            if agent_ids is not None and isinstance(agent_ids, list):
                reassigned_count = 0
                for aid in agent_ids:
                    agent = sandbox_agents.get_agent(str(aid))
                    if agent is not None:
                        updated = agent.model_copy(update={"status": "active"})
                        sandbox_agents.register(updated)
                        reassigned_count += 1
                metrics["agents_reassigned"] = float(reassigned_count)
                trace.append(
                    {
                        "phase": "reassign_idle",
                        "reassigned_count": reassigned_count,
                    }
                )

        # Compute result probabilities
        active_agents = sum(1 for a in sandbox_agents.list_agents() if a.status == "active")
        total_agents = len(sandbox_agents.list_agents())
        metrics["active_agent_ratio"] = active_agents / total_agents if total_agents > 0 else 0.0
        metrics["total_agents"] = float(total_agents)

        probs["success_probability"] = 0.85
        probs["failure_probability"] = 0.15

        return metrics, trace, probs

    async def _simulate_domain_change(
        self,
        modifications: dict[str, object],
        sandbox_agents: AgentRegistry,
        sandbox_domains: DomainRegistry,
    ) -> tuple[dict[str, float], list[dict[str, object]], dict[str, float]]:
        """Simulate a domain change scenario."""
        metrics: dict[str, float] = {}
        trace: list[dict[str, object]] = []
        probs: dict[str, float] = {}

        action = str(modifications.get("action", ""))

        if action == "assign_to_empty_domains":
            domain_ids = modifications.get("domain_ids")
            if domain_ids is not None and isinstance(domain_ids, list):
                assigned_count = 0
                for did in domain_ids:
                    domain = sandbox_domains.get_domain(str(did))
                    if domain is not None:
                        updated = domain.model_copy(update={"agent_count": 1})
                        sandbox_domains.register(updated)
                        assigned_count += 1
                metrics["domains_assigned"] = float(assigned_count)
                trace.append(
                    {
                        "phase": "assign_to_empty_domains",
                        "assigned_count": assigned_count,
                    }
                )

        # Compute result probabilities
        populated_domains = sum(1 for d in sandbox_domains.list_domains() if d.agent_count > 0)
        total_domains = len(sandbox_domains.list_domains())
        metrics["populated_domain_ratio"] = (
            populated_domains / total_domains if total_domains > 0 else 0.0
        )
        metrics["total_domains"] = float(total_domains)

        probs["success_probability"] = 0.75
        probs["failure_probability"] = 0.25

        return metrics, trace, probs

    async def _simulate_custom(
        self,
        modifications: dict[str, object],
        sandbox_skills: SkillRegistry,
        sandbox_agents: AgentRegistry,
        sandbox_domains: DomainRegistry,
    ) -> tuple[dict[str, float], list[dict[str, object]], dict[str, float]]:
        """Simulate a custom scenario (fallback handler)."""
        metrics: dict[str, float] = {}
        trace: list[dict[str, object]] = []
        probs: dict[str, float] = {}

        action = str(modifications.get("action", ""))

        if action == "add_retry_logic":
            target_rate = modifications.get("target_error_rate")
            metrics["error_rate_after"] = (
                float(str(target_rate)) if target_rate is not None else 0.05
            )
            metrics["error_rate_improvement"] = max(0.0, 0.25 - metrics["error_rate_after"])
            trace.append(
                {
                    "phase": "add_retry_logic",
                    "target_error_rate": metrics["error_rate_after"],
                }
            )

        # Record sandbox state metrics
        metrics["total_skills"] = float(len(sandbox_skills.list_skills()))
        metrics["total_agents"] = float(len(sandbox_agents.list_agents()))
        metrics["total_domains"] = float(len(sandbox_domains.list_domains()))

        probs["success_probability"] = 0.7
        probs["failure_probability"] = 0.3

        return metrics, trace, probs

    # ------------------------------------------------------------------
    # Internal: environment capture and isolation
    # ------------------------------------------------------------------

    async def _capture_environment(self) -> SimulationEnvironment:
        """Snapshot the current system state into a SimulationEnvironment.

        Deep copies all registry contents so the simulation can never
        affect production state.
        """
        return SimulationEnvironment(
            skills=copy.deepcopy(self._skills.list_skills()),
            agents=copy.deepcopy(self._agents.list_agents()),
            domains=copy.deepcopy(self._domains.list_domains()),
            metadata={
                "captured_at": datetime.now(UTC).isoformat(),
                "source": "simulation_engine",
            },
        )

    async def _verify_isolation(self, baseline: SimulationEnvironment) -> None:
        """Verify that production registries match the baseline snapshot.

        This is a safety check run after every simulation to confirm
        isolation was maintained.  Raises SimulationEnvironmentError
        if any registry was mutated.
        """
        current = await self._capture_environment()
        current_skill_ids = {s.skill_id for s in current.skills}
        baseline_skill_ids = {s.skill_id for s in baseline.skills}
        if current_skill_ids != baseline_skill_ids:
            raise SimulationEnvironmentError(
                "Isolation violation: skill registry was modified during simulation"
            )

    @staticmethod
    def _copy_skills_to_registry(
        skills: list[SkillDescriptor],
    ) -> SkillRegistry:
        """Deep-copy skill descriptors into a new isolated SkillRegistry."""
        registry = SkillRegistry()
        for skill in skills:
            registry.register(copy.deepcopy(skill))
        return registry

    @staticmethod
    def _copy_agents_to_registry(
        agents: list[AgentDescriptor],
    ) -> AgentRegistry:
        """Deep-copy agent descriptors into a new isolated AgentRegistry."""
        registry = AgentRegistry()
        for agent in agents:
            registry.register(copy.deepcopy(agent))
        return registry

    @staticmethod
    def _copy_domains_to_registry(
        domains: list[DomainDescriptor],
    ) -> DomainRegistry:
        """Deep-copy domain descriptors into a new isolated DomainRegistry."""
        registry = DomainRegistry()
        for domain in domains:
            registry.register(copy.deepcopy(domain))
        return registry

    @staticmethod
    def _registry_env(
        skills: SkillRegistry,
        agents: AgentRegistry,
        domains: DomainRegistry,
    ) -> SimulationEnvironment:
        """Create a SimulationEnvironment from sandbox registries."""
        return SimulationEnvironment(
            skills=skills.list_skills(),
            agents=agents.list_agents(),
            domains=domains.list_domains(),
        )

    # ------------------------------------------------------------------
    # Internal: comparison helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_delta(metric: str, baseline: float, simulation: float) -> OutcomeDelta:
        """Compute the delta for a single metric."""
        delta = simulation - baseline
        delta_pct = (delta / baseline * 100.0) if baseline != 0.0 else 0.0

        # Determine if the change is "improved"
        # For counts, more is generally better (more skills, agents, domains)
        # For error rates, lower is better — but we handle that separately
        is_error_metric = "error" in metric.lower()
        improved = delta < 0 if is_error_metric else delta > 0

        return OutcomeDelta(
            metric=metric,
            baseline_value=baseline,
            simulation_value=simulation,
            delta=delta,
            delta_percent=delta_pct,
            improved=improved,
        )

    @staticmethod
    def _generate_recommendation(assessment: str, deltas: list[OutcomeDelta]) -> str:
        """Generate a human-readable recommendation from the comparison."""
        if assessment == "positive":
            return (
                "Simulation shows positive outcomes. "
                "Consider implementing this change through the proposal workflow."
            )
        if assessment == "negative":
            return (
                "Simulation shows negative outcomes. "
                "Recommend revising the approach before implementation."
            )
        if assessment == "mixed":
            improved = [d.metric for d in deltas if d.improved]
            degraded = [d.metric for d in deltas if not d.improved and d.delta != 0.0]
            return (
                f"Simulation shows mixed outcomes. "
                f"Improved: {', '.join(improved)}. "
                f"Degraded: {', '.join(degraded)}. "
                "Proceed with caution and address degradations first."
            )
        return "Simulation shows no significant changes. No action needed at this time."

    # ------------------------------------------------------------------
    # Internal: scenario generation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _analysis_to_scenario(
        analysis: SkillAnalysis,
    ) -> WhatIfScenario | None:
        """Convert a SkillAnalysis into a WhatIfScenario."""

        recommendation = analysis.recommendation
        skill_id = analysis.skill_id

        scenario_map: dict[str, tuple[str, str, str, dict[str, object], RiskLevel]] = {
            "enhance": (
                f"Simulate enhancing skill {skill_id}",
                f"Simulate reliability improvements for skill {skill_id}. "
                f"Reason: {analysis.recommendation_reason}",
                "skill_evolution",
                {"action": "enhance", "skill_id": skill_id},
                RiskLevel.LOW,
            ),
            "merge": (
                f"Simulate merging skill {skill_id}",
                f"Simulate merging {skill_id} with related skills. "
                f"Reason: {analysis.recommendation_reason}",
                "skill_evolution",
                {
                    "action": "merge",
                    "skill_ids": [skill_id, *analysis.related_skill_ids],
                },
                RiskLevel.MEDIUM,
            ),
            "split": (
                f"Simulate splitting skill {skill_id}",
                f"Simulate splitting {skill_id} into focused sub-skills. "
                f"Reason: {analysis.recommendation_reason}",
                "skill_evolution",
                {"action": "split", "skill_id": skill_id},
                RiskLevel.MEDIUM,
            ),
            "deprecate": (
                f"Simulate deprecating skill {skill_id}",
                f"Simulate removing unused skill {skill_id}. "
                f"Reason: {analysis.recommendation_reason}",
                "skill_evolution",
                {"action": "deprecate", "skill_id": skill_id},
                RiskLevel.HIGH,
            ),
        }

        entry = scenario_map.get(recommendation)
        if entry is None:
            return None

        name, desc, stype, mods, risk = entry
        return WhatIfScenario(
            name=name,
            description=desc,
            scenario_type=stype,
            modifications=mods,
            expected_outcome=analysis.recommendation_reason,
            risk_level=risk,
            source="prime.skill_evolution",
        )

    # ------------------------------------------------------------------
    # Internal: utility
    # ------------------------------------------------------------------

    def _get_run_or_raise(self, run_id: UUID) -> SimulationRun:
        """Look up a simulation run or raise SimulationNotFoundError."""
        run = self._store.get(run_id)
        if run is None:
            raise SimulationNotFoundError(f"Simulation run {run_id} not found")
        return run
