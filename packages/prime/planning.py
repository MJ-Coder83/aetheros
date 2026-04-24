"""Prime Autonomous Planning -- Multi-step plan execution for the Prime meta-agent.

This module enables Prime to decompose high-level goals into structured,
executable plans with dependency tracking, progress monitoring, and adaptive
failure handling.

Design principles:
- Every plan action is logged to the Tape (recursive self-awareness)
- Plans follow a lifecycle: DRAFT -> ACTIVE -> COMPLETED (or FAILED/ABORTED)
- Steps have dependencies -- no step starts until all its deps are done
- Failed steps can be retried or skipped (configurable per plan)
- Humans can approve/abort plans via the Proposal workflow for high-risk goals
- Plans integrate with PrimeIntrospector for goal-aware system understanding

Usage::

    from packages.prime.planning import PlanningEngine

    engine = PlanningEngine(tape_service=tape_svc)
    plan = await engine.create_plan(
        goal="Reduce system error rate below 5%",
        steps=[
            PlanStep(step_id="s1", name="Analyse errors", action="analyse_errors"),
            PlanStep(step_id="s2", name="Fix top errors", action="fix_errors",
                     dependencies=["s1"]),
            PlanStep(step_id="s3", name="Verify fix", action="verify_fix",
                     dependencies=["s2"]),
        ],
    )
    result = await engine.execute_plan(plan.id)
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PlanStatus(StrEnum):
    """Lifecycle states for a plan."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class StepStatus(StrEnum):
    """Lifecycle states for a plan step."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class FailurePolicy(StrEnum):
    """What to do when a step fails."""

    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"
    PAUSE = "pause"


class StepAction(StrEnum):
    """Predefined step actions that Prime can execute.

    These map to real system operations. Custom actions can be registered
    via the PlanningEngine action registry.
    """

    ANALYSE_ERRORS = "analyse_errors"
    FIX_ERRORS = "fix_errors"
    VERIFY_FIX = "verify_fix"
    INTROSPECT_SYSTEM = "introspect_system"
    GENERATE_PROPOSAL = "generate_proposal"
    APPROVE_PROPOSAL = "approve_proposal"
    IMPLEMENT_PROPOSAL = "implement_proposal"
    RUN_SIMULATION = "run_simulation"
    EVOLVE_SKILL = "evolve_skill"
    CREATE_DOMAIN = "create_domain"
    REGISTER_AGENTS = "register_agents"
    DEPLOY_CHANGE = "deploy_change"
    MONITOR_METRICS = "monitor_metrics"
    NOTIFY_STAKEHOLDERS = "notify_stakeholders"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class PlanStep(BaseModel):
    """A single step within a plan.

    Steps can have dependencies on other steps (by step_id). A step
    becomes READY when all its dependencies are COMPLETED (or SKIPPED).
    """

    step_id: str
    name: str
    action: str
    description: str = ""
    dependencies: list[str] = []
    parameters: dict[str, object] = Field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    max_retries: int = 2
    retry_count: int = 0
    result: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class Plan(BaseModel):
    """A multi-step plan for achieving a goal.

    Plans are created in DRAFT status and transition to ACTIVE when
    execution begins. Steps are executed in dependency order.
    """

    id: UUID = Field(default_factory=uuid4)
    goal: str
    description: str = ""
    steps: list[PlanStep] = []
    status: PlanStatus = PlanStatus.DRAFT
    failure_policy: FailurePolicy = FailurePolicy.ABORT
    priority: str = "normal"  # low, normal, high, critical
    requires_approval: bool = False
    proposal_id: UUID | None = None
    created_by: str = "prime"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress_pct: float = 0.0
    metadata: dict[str, object] = Field(default_factory=dict)


class PlanResult(BaseModel):
    """Outcome of a plan execution."""

    plan_id: UUID
    status: PlanStatus
    steps_completed: int
    steps_failed: int
    steps_skipped: int
    total_steps: int
    progress_pct: float
    duration_seconds: float
    error_summary: str | None = None


class StepResult(BaseModel):
    """Outcome of a single step execution."""

    step_id: str
    status: StepStatus
    result: str | None = None
    error_message: str | None = None
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class PlanningError(Exception):
    """Base exception for planning operations."""


class PlanNotFoundError(PlanningError):
    """Raised when a requested plan does not exist."""


class StepNotFoundError(PlanningError):
    """Raised when a requested step does not exist."""


class PlanTransitionError(PlanningError):
    """Raised when an invalid state transition is attempted."""


class CyclicDependencyError(PlanningError):
    """Raised when step dependencies form a cycle."""


class PlanNotActiveError(PlanningError):
    """Raised when trying to execute a step on a non-active plan."""


class StepActionError(PlanningError):
    """Raised when a step action fails during execution."""


# ---------------------------------------------------------------------------
# Plan store (in-memory; will be backed by Postgres later)
# ---------------------------------------------------------------------------


class PlanStore:
    """In-memory store for plans and their steps."""

    def __init__(self) -> None:
        self._plans: dict[UUID, Plan] = {}

    def add(self, plan: Plan) -> None:
        self._plans[plan.id] = plan

    def get(self, plan_id: UUID) -> Plan | None:
        return self._plans.get(plan_id)

    def list_all(self) -> list[Plan]:
        return list(self._plans.values())

    def list_by_status(self, status: PlanStatus) -> list[Plan]:
        return [p for p in self._plans.values() if p.status == status]

    def update(self, plan: Plan) -> None:
        if plan.id not in self._plans:
            raise PlanNotFoundError(f"Plan {plan.id} not found")
        self._plans[plan.id] = plan

    def remove(self, plan_id: UUID) -> None:
        self._plans.pop(plan_id, None)


# ---------------------------------------------------------------------------
# Dependency resolver
# ---------------------------------------------------------------------------


def _validate_no_cycles(steps: list[PlanStep]) -> None:
    """Validate that the step dependency graph has no cycles.

    Uses Kahn's algorithm (topological sort) to detect cycles.
    Raises CyclicDependencyError if a cycle is found.
    """
    step_ids = {s.step_id for s in steps}
    # Build adjacency list: step_id -> list of dependents
    dependents: dict[str, list[str]] = {s.step_id: [] for s in steps}
    in_degree: dict[str, int] = {s.step_id: 0 for s in steps}

    for step in steps:
        for dep in step.dependencies:
            if dep not in step_ids:
                raise StepNotFoundError(
                    f"Step '{step.step_id}' depends on unknown step '{dep}'"
                )
            dependents[dep].append(step.step_id)
            in_degree[step.step_id] = in_degree.get(step.step_id, 0) + 1

    # Kahn's algorithm
    queue: list[str] = [sid for sid, deg in in_degree.items() if deg == 0]
    visited = 0

    while queue:
        node = queue.pop(0)
        visited += 1
        for dependent in dependents.get(node, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if visited != len(steps):
        raise CyclicDependencyError(
            "Step dependencies contain a cycle -- plan cannot be executed"
        )


def _get_ready_steps(steps: list[PlanStep]) -> list[PlanStep]:
    """Return steps that are ready to execute (PENDING with deps met, or READY)."""
    done_ids = {
        s.step_id
        for s in steps
        if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
    }
    ready: list[PlanStep] = []
    for step in steps:
        if step.status not in (StepStatus.PENDING, StepStatus.READY):
            continue
        if step.status == StepStatus.READY or all(dep in done_ids for dep in step.dependencies):
            ready.append(step)
    return ready


def _compute_progress(steps: list[PlanStep]) -> float:
    """Compute plan progress as a percentage [0.0, 100.0]."""
    if not steps:
        return 0.0
    done = sum(
        1 for s in steps if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
    )
    return round(done / len(steps) * 100, 1)


# ---------------------------------------------------------------------------
# Allowed state transitions
# ---------------------------------------------------------------------------

_VALID_PLAN_TRANSITIONS: dict[PlanStatus, set[PlanStatus]] = {
    PlanStatus.DRAFT: {PlanStatus.ACTIVE, PlanStatus.ABORTED},
    PlanStatus.ACTIVE: {PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.ABORTED},
    PlanStatus.COMPLETED: set(),
    PlanStatus.FAILED: {PlanStatus.DRAFT, PlanStatus.ABORTED},  # can retry
    PlanStatus.ABORTED: set(),
}

_VALID_STEP_TRANSITIONS: dict[StepStatus, set[StepStatus]] = {
    StepStatus.PENDING: {StepStatus.READY, StepStatus.SKIPPED},
    StepStatus.READY: {StepStatus.RUNNING, StepStatus.SKIPPED},
    StepStatus.RUNNING: {StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.RETRYING, StepStatus.SKIPPED},
    StepStatus.FAILED: {StepStatus.RETRYING, StepStatus.SKIPPED},
    StepStatus.RETRYING: {StepStatus.RUNNING, StepStatus.FAILED, StepStatus.SKIPPED},
    StepStatus.COMPLETED: set(),
    StepStatus.SKIPPED: set(),
}


def _validate_plan_transition(current: PlanStatus, target: PlanStatus) -> None:
    allowed = _VALID_PLAN_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise PlanTransitionError(
            f"Cannot transition plan from {current.value} to {target.value}"
        )


def _validate_step_transition(current: StepStatus, target: StepStatus) -> None:
    allowed = _VALID_STEP_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise PlanTransitionError(
            f"Cannot transition step from {current.value} to {target.value}"
        )


# ---------------------------------------------------------------------------
# Step action executor
# ---------------------------------------------------------------------------

# Type for step action handlers
class StepActionRegistry:
    """Registry of named step action handlers.

    Action handlers are async callables that take (step, context) and
    return a StepResult. Register custom actions to extend Prime's
    planning capabilities.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Coroutine[None, None, StepResult]]] = {}

    def register(
        self,
        action: str,
        handler: Callable[..., Coroutine[None, None, StepResult]],
    ) -> None:
        self._handlers[action] = handler

    def get(
        self, action: str,
    ) -> Callable[..., Coroutine[None, None, StepResult]] | None:
        return self._handlers.get(action)

    def list_actions(self) -> list[str]:
        return sorted(self._handlers.keys())


# ---------------------------------------------------------------------------
# Planning Engine -- the main public API
# ---------------------------------------------------------------------------


class PlanningEngine:
    """Multi-step autonomous planning engine for the Prime meta-agent.

    PlanningEngine allows Prime to:
    - Decompose goals into structured, dependency-ordered plans
    - Execute plans with automatic dependency resolution
    - Handle failures with configurable policies (retry, skip, abort, pause)
    - Track progress and log every action to the Tape
    - Generate plans automatically from introspection data

    Usage::

        engine = PlanningEngine(tape_service=tape_svc)
        plan = await engine.create_plan(
            goal="Improve system reliability",
            steps=[...],
        )
        result = await engine.execute_plan(plan.id)
    """

    def __init__(
        self,
        tape_service: TapeService,
        store: PlanStore | None = None,
        action_registry: StepActionRegistry | None = None,
        introspector: object | None = None,
        proposal_engine: object | None = None,
    ) -> None:
        self._tape = tape_service
        self._store = store or PlanStore()
        self._actions = action_registry or StepActionRegistry()
        self._introspector = introspector
        self._proposal_engine = proposal_engine
        self._register_default_actions()

    # ------------------------------------------------------------------
    # Plan CRUD
    # ------------------------------------------------------------------

    async def create_plan(
        self,
        goal: str,
        steps: list[PlanStep],
        description: str = "",
        failure_policy: FailurePolicy = FailurePolicy.ABORT,
        priority: str = "normal",
        requires_approval: bool = False,
        created_by: str = "prime",
        metadata: dict[str, object] | None = None,
    ) -> Plan:
        """Create a new multi-step plan.

        Validates that:
        - The goal is non-empty
        - Step IDs are unique within the plan
        - Dependencies reference existing step IDs
        - No cyclic dependencies exist

        The plan starts in DRAFT status. Call ``activate_plan()`` to
        begin execution, or ``execute_plan()`` to activate and execute
        in one call.
        """
        if not goal.strip():
            raise ValueError("Plan goal must not be empty")

        step_ids = [s.step_id for s in steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Step IDs must be unique within a plan")

        _validate_no_cycles(steps)

        # Mark initial ready steps
        updated_steps = list(steps)
        for i, step in enumerate(updated_steps):
            if not step.dependencies:
                updated_steps[i] = step.model_copy(
                    update={"status": StepStatus.READY}
                )

        plan = Plan(
            goal=goal,
            description=description,
            steps=updated_steps,
            failure_policy=failure_policy,
            priority=priority,
            requires_approval=requires_approval,
            created_by=created_by,
            metadata=metadata or {},
            progress_pct=_compute_progress(updated_steps),
        )

        self._store.add(plan)

        await self._tape.log_event(
            event_type="plan.created",
            payload={
                "plan_id": str(plan.id),
                "goal": goal,
                "step_count": len(steps),
                "failure_policy": failure_policy.value,
                "priority": priority,
            },
            agent_id="planning-engine",
            metadata={"status": PlanStatus.DRAFT.value},
        )

        return plan

    async def get_plan(self, plan_id: UUID) -> Plan:
        """Retrieve a plan by ID.

        Raises:
            PlanNotFoundError: if the plan does not exist.
        """
        plan = self._store.get(plan_id)
        if plan is None:
            raise PlanNotFoundError(f"Plan {plan_id} not found")
        return plan

    async def list_plans(self, status: PlanStatus | None = None) -> list[Plan]:
        """List all plans, optionally filtered by status."""
        if status is not None:
            return self._store.list_by_status(status)
        return self._store.list_all()

    async def delete_plan(self, plan_id: UUID) -> None:
        """Delete a plan. Only DRAFT or ABORTED plans can be deleted."""
        plan = await self.get_plan(plan_id)
        if plan.status not in (PlanStatus.DRAFT, PlanStatus.ABORTED):
            raise PlanTransitionError(
                f"Cannot delete plan in {plan.status.value} status"
            )
        self._store.remove(plan_id)

        await self._tape.log_event(
            event_type="plan.deleted",
            payload={"plan_id": str(plan_id)},
            agent_id="planning-engine",
        )

    # ------------------------------------------------------------------
    # Plan lifecycle
    # ------------------------------------------------------------------

    async def activate_plan(self, plan_id: UUID) -> Plan:
        """Transition a DRAFT plan to ACTIVE, making it ready for execution."""
        plan = await self.get_plan(plan_id)
        _validate_plan_transition(plan.status, PlanStatus.ACTIVE)

        updated = plan.model_copy(
            update={
                "status": PlanStatus.ACTIVE,
                "started_at": datetime.now(UTC),
            }
        )
        self._store.update(updated)

        await self._tape.log_event(
            event_type="plan.activated",
            payload={"plan_id": str(plan_id), "goal": plan.goal},
            agent_id="planning-engine",
        )

        return updated

    async def abort_plan(self, plan_id: UUID, reason: str | None = None) -> Plan:
        """Abort an active plan. All running steps are left in their current state."""
        plan = await self.get_plan(plan_id)
        _validate_plan_transition(plan.status, PlanStatus.ABORTED)

        updated = plan.model_copy(
            update={
                "status": PlanStatus.ABORTED,
                "completed_at": datetime.now(UTC),
            }
        )
        self._store.update(updated)

        await self._tape.log_event(
            event_type="plan.aborted",
            payload={"plan_id": str(plan_id), "reason": reason or ""},
            agent_id="planning-engine",
        )

        return updated

    # ------------------------------------------------------------------
    # Plan execution
    # ------------------------------------------------------------------

    async def execute_plan(
        self,
        plan_id: UUID,
        step_timeout: float = 30.0,
    ) -> PlanResult:
        """Activate (if needed) and execute all steps in dependency order.

        Steps are executed sequentially in topological order. When a step
        has no registered action handler, a simulated execution is performed
        (step is marked COMPLETED with a placeholder result).

        Args:
            plan_id: The plan to execute.
            step_timeout: Maximum seconds per step before timeout.

        Returns:
            A PlanResult summarising the execution outcome.
        """
        plan = await self.get_plan(plan_id)

        # Activate if still in DRAFT
        if plan.status == PlanStatus.DRAFT:
            plan = await self.activate_plan(plan_id)

        if plan.status != PlanStatus.ACTIVE:
            raise PlanNotActiveError(
                f"Plan {plan_id} is in {plan.status.value} status, not active"
            )

        start_time = datetime.now(UTC)

        while True:
            ready = _get_ready_steps(plan.steps)
            if not ready:
                break

            # Execute the first ready step (sequential execution)
            step = ready[0]
            await self._execute_step(plan, step, timeout=step_timeout)

            # Refresh plan from store after step execution
            plan = await self.get_plan(plan_id)

        # Determine final plan status
        all_done = all(
            s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
            for s in plan.steps
        )
        any_failed = any(s.status == StepStatus.FAILED for s in plan.steps)

        if all_done:
            final_status = PlanStatus.COMPLETED
        elif any_failed and plan.failure_policy != FailurePolicy.PAUSE:
            final_status = PlanStatus.FAILED
        elif any_failed and plan.failure_policy == FailurePolicy.PAUSE:
            final_status = PlanStatus.ACTIVE  # paused, waiting for manual intervention
        else:
            final_status = plan.status  # still active (paused)

        if final_status != plan.status:
            _validate_plan_transition(plan.status, final_status)
            plan = plan.model_copy(
                update={
                    "status": final_status,
                    "completed_at": datetime.now(UTC),
                    "progress_pct": _compute_progress(plan.steps),
                }
            )
            self._store.update(plan)
        else:
            # Update progress even if status unchanged
            plan = plan.model_copy(
                update={"progress_pct": _compute_progress(plan.steps)}
            )
            self._store.update(plan)

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        completed_count = sum(
            1 for s in plan.steps if s.status == StepStatus.COMPLETED
        )
        failed_count = sum(1 for s in plan.steps if s.status == StepStatus.FAILED)
        skipped_count = sum(1 for s in plan.steps if s.status == StepStatus.SKIPPED)

        error_summary: str | None = None
        if failed_count > 0:
            failed_steps = [s for s in plan.steps if s.status == StepStatus.FAILED]
            error_summary = "; ".join(
                f"{s.name}: {s.error_message or 'unknown error'}"
                for s in failed_steps
            )

        result = PlanResult(
            plan_id=plan.id,
            status=final_status,
            steps_completed=completed_count,
            steps_failed=failed_count,
            steps_skipped=skipped_count,
            total_steps=len(plan.steps),
            progress_pct=plan.progress_pct,
            duration_seconds=round(duration, 2),
            error_summary=error_summary,
        )

        await self._tape.log_event(
            event_type="plan.completed" if final_status == PlanStatus.COMPLETED else "plan.execution_ended",
            payload=result.model_dump(),
            agent_id="planning-engine",
        )

        return result

    async def _execute_step(
        self,
        plan: Plan,
        step: PlanStep,
        timeout: float = 30.0,
    ) -> StepResult:
        """Execute a single step, handling failures per the plan's policy."""
        # If step is PENDING, transition to READY first
        if step.status == StepStatus.PENDING:
            _validate_step_transition(StepStatus.PENDING, StepStatus.READY)
            step = step.model_copy(update={"status": StepStatus.READY})
            step_idx = next(
                i for i, s in enumerate(plan.steps) if s.step_id == step.step_id
            )
            plan.steps[step_idx] = step
            self._store.update(plan)

        if step.status != StepStatus.RUNNING:
            _validate_step_transition(step.status, StepStatus.RUNNING)

        # Update step to RUNNING (if not already)
        step_idx = next(
            i for i, s in enumerate(plan.steps) if s.step_id == step.step_id
        )
        now = datetime.now(UTC)
        if step.status != StepStatus.RUNNING:
            updated_step = step.model_copy(
                update={
                    "status": StepStatus.RUNNING,
                    "started_at": now,
                }
            )
            plan.steps[step_idx] = updated_step
            self._store.update(plan)
        else:
            updated_step = step

        await self._tape.log_event(
            event_type="plan.step_started",
            payload={
                "plan_id": str(plan.id),
                "step_id": step.step_id,
                "step_name": step.name,
                "action": step.action,
            },
            agent_id="planning-engine",
        )

        step_start = datetime.now(UTC)

        # Execute the action
        try:
            handler = self._actions.get(step.action)
            if handler is not None:
                result = await asyncio.wait_for(
                    handler(step, plan),
                    timeout=timeout,
                )
            else:
                # No handler registered -- simulated execution
                result = StepResult(
                    step_id=step.step_id,
                    status=StepStatus.COMPLETED,
                    result=f"Simulated execution of '{step.action}'",
                )
        except TimeoutError:
            result = StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error_message=f"Step timed out after {timeout}s",
            )
        except StepActionError as exc:
            result = StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error_message=str(exc),
            )
        except Exception as exc:
            result = StepResult(
                step_id=step.step_id,
                status=StepStatus.FAILED,
                error_message=f"Unexpected error: {exc}",
            )

        step_end = datetime.now(UTC)
        duration = (step_end - step_start).total_seconds()
        result.duration_seconds = round(duration, 2)

        # Handle the result based on failure policy
        if result.status == StepStatus.FAILED:
            return await self._handle_step_failure(plan, step_idx, result, timeout)

        # Step succeeded
        _validate_step_transition(updated_step.status, result.status)
        final_step = updated_step.model_copy(
            update={
                "status": result.status,
                "result": result.result,
                "completed_at": datetime.now(UTC),
            }
        )
        plan.steps[step_idx] = final_step
        plan = plan.model_copy(
            update={"progress_pct": _compute_progress(plan.steps)}
        )
        self._store.update(plan)

        # Mark newly-ready steps
        await self._mark_ready_steps(plan)

        await self._tape.log_event(
            event_type="plan.step_completed",
            payload={
                "plan_id": str(plan.id),
                "step_id": step.step_id,
                "step_name": step.name,
                "status": result.status.value,
                "duration_seconds": result.duration_seconds,
            },
            agent_id="planning-engine",
        )

        return result

    async def _handle_step_failure(
        self,
        plan: Plan,
        step_idx: int,
        result: StepResult,
        timeout: float,
    ) -> StepResult:
        """Handle a failed step according to the plan's failure policy."""
        step = plan.steps[step_idx]

        # Refresh plan from store
        plan = await self.get_plan(plan.id)
        step = plan.steps[step_idx]

        if plan.failure_policy == FailurePolicy.RETRY and step.retry_count < step.max_retries:
            # Retry the step
            new_retry_count = step.retry_count + 1
            _validate_step_transition(step.status, StepStatus.RETRYING)
            retrying_step = step.model_copy(
                update={
                    "status": StepStatus.RETRYING,
                    "retry_count": new_retry_count,
                }
            )
            plan.steps[step_idx] = retrying_step
            self._store.update(plan)

            await self._tape.log_event(
                event_type="plan.step_retrying",
                payload={
                    "plan_id": str(plan.id),
                    "step_id": step.step_id,
                    "retry_count": new_retry_count,
                    "max_retries": step.max_retries,
                },
                agent_id="planning-engine",
            )

            # Transition to RUNNING for the retry
            _validate_step_transition(StepStatus.RETRYING, StepStatus.RUNNING)
            running_step = retrying_step.model_copy(
                update={"status": StepStatus.RUNNING}
            )
            plan.steps[step_idx] = running_step
            self._store.update(plan)

            # Re-execute the step
            return await self._execute_step(plan, running_step, timeout=timeout)

        if plan.failure_policy == FailurePolicy.SKIP:
            # Skip the failed step and continue
            _validate_step_transition(step.status, StepStatus.SKIPPED)
            skipped_step = step.model_copy(
                update={
                    "status": StepStatus.SKIPPED,
                    "error_message": result.error_message,
                    "completed_at": datetime.now(UTC),
                }
            )
            plan.steps[step_idx] = skipped_step
            plan = plan.model_copy(
                update={"progress_pct": _compute_progress(plan.steps)}
            )
            self._store.update(plan)

            await self._mark_ready_steps(plan)

            await self._tape.log_event(
                event_type="plan.step_skipped",
                payload={
                    "plan_id": str(plan.id),
                    "step_id": step.step_id,
                    "error_message": result.error_message or "",
                },
                agent_id="planning-engine",
            )

            return StepResult(
                step_id=step.step_id,
                status=StepStatus.SKIPPED,
                error_message=result.error_message,
                duration_seconds=result.duration_seconds,
            )

        if plan.failure_policy == FailurePolicy.PAUSE:
            # Leave the step as FAILED but keep the plan ACTIVE (paused)
            _validate_step_transition(step.status, StepStatus.FAILED)
            failed_step = step.model_copy(
                update={
                    "status": StepStatus.FAILED,
                    "error_message": result.error_message,
                    "completed_at": datetime.now(UTC),
                }
            )
            plan.steps[step_idx] = failed_step
            self._store.update(plan)

            await self._tape.log_event(
                event_type="plan.step_failed",
                payload={
                    "plan_id": str(plan.id),
                    "step_id": step.step_id,
                    "error_message": result.error_message or "",
                    "policy": "pause",
                },
                agent_id="planning-engine",
            )

            return result

        # Default: ABORT -- fail the step and the plan
        _validate_step_transition(step.status, StepStatus.FAILED)
        failed_step = step.model_copy(
            update={
                "status": StepStatus.FAILED,
                "error_message": result.error_message,
                "completed_at": datetime.now(UTC),
            }
        )
        plan.steps[step_idx] = failed_step
        self._store.update(plan)

        await self._tape.log_event(
            event_type="plan.step_failed",
            payload={
                "plan_id": str(plan.id),
                "step_id": step.step_id,
                "error_message": result.error_message or "",
                "policy": "abort",
            },
            agent_id="planning-engine",
        )

        return result

    async def _mark_ready_steps(self, plan: Plan) -> None:
        """Mark steps whose dependencies are now satisfied as READY."""
        changed = False
        for i, step in enumerate(plan.steps):
            if step.status == StepStatus.PENDING:
                done_ids = {
                    s.step_id
                    for s in plan.steps
                    if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
                }
                if all(dep in done_ids for dep in step.dependencies):
                    plan.steps[i] = step.model_copy(
                        update={"status": StepStatus.READY}
                    )
                    changed = True

        if changed:
            self._store.update(plan)

    # ------------------------------------------------------------------
    # Step-level operations
    # ------------------------------------------------------------------

    async def execute_step(
        self,
        plan_id: UUID,
        step_id: str,
        timeout: float = 30.0,
    ) -> StepResult:
        """Execute a single step of an active plan.

        Useful for manual step-by-step execution or resuming after a pause.
        """
        plan = await self.get_plan(plan_id)
        if plan.status != PlanStatus.ACTIVE:
            raise PlanNotActiveError(
                f"Plan {plan_id} is not active (status: {plan.status.value})"
            )

        step = next((s for s in plan.steps if s.step_id == step_id), None)
        if step is None:
            raise StepNotFoundError(
                f"Step '{step_id}' not found in plan {plan_id}"
            )

        if step.status not in (StepStatus.READY, StepStatus.PENDING):
            raise PlanTransitionError(
                f"Step '{step_id}' is in {step.status.value} status and "
                f"cannot be executed"
            )

        return await self._execute_step(plan, step, timeout=timeout)

    async def skip_step(self, plan_id: UUID, step_id: str) -> PlanStep:
        """Skip a pending or ready step."""
        plan = await self.get_plan(plan_id)
        step_idx = next(
            (i for i, s in enumerate(plan.steps) if s.step_id == step_id),
            None,
        )
        if step_idx is None:
            raise StepNotFoundError(f"Step '{step_id}' not found in plan {plan_id}")

        step = plan.steps[step_idx]
        if step.status not in (StepStatus.PENDING, StepStatus.READY, StepStatus.FAILED):
            raise PlanTransitionError(
                f"Cannot skip step in {step.status.value} status"
            )

        _validate_step_transition(step.status, StepStatus.SKIPPED)
        updated_step = step.model_copy(
            update={
                "status": StepStatus.SKIPPED,
                "completed_at": datetime.now(UTC),
            }
        )
        plan.steps[step_idx] = updated_step
        plan = plan.model_copy(
            update={"progress_pct": _compute_progress(plan.steps)}
        )
        self._store.update(plan)

        await self._mark_ready_steps(plan)

        await self._tape.log_event(
            event_type="plan.step_skipped",
            payload={
                "plan_id": str(plan_id),
                "step_id": step_id,
            },
            agent_id="planning-engine",
        )

        return updated_step

    async def retry_step(
        self,
        plan_id: UUID,
        step_id: str,
        timeout: float = 30.0,
    ) -> StepResult:
        """Retry a failed step."""
        plan = await self.get_plan(plan_id)
        step_idx = next(
            (i for i, s in enumerate(plan.steps) if s.step_id == step_id),
            None,
        )
        if step_idx is None:
            raise StepNotFoundError(f"Step '{step_id}' not found in plan {plan_id}")

        step = plan.steps[step_idx]
        if step.status != StepStatus.FAILED:
            raise PlanTransitionError(
                f"Can only retry FAILED steps, got {step.status.value}"
            )

        # Reset step for retry
        _validate_step_transition(step.status, StepStatus.RETRYING)
        retrying_step = step.model_copy(
            update={
                "status": StepStatus.RETRYING,
                "retry_count": step.retry_count + 1,
                "error_message": None,
            }
        )
        plan.steps[step_idx] = retrying_step
        self._store.update(plan)

        _validate_step_transition(StepStatus.RETRYING, StepStatus.RUNNING)
        running_step = retrying_step.model_copy(
            update={"status": StepStatus.RUNNING}
        )
        plan.steps[step_idx] = running_step
        self._store.update(plan)

        return await self._execute_step(plan, running_step, timeout=timeout)

    # ------------------------------------------------------------------
    # Auto-plan generation from introspection
    # ------------------------------------------------------------------

    async def generate_plan_from_goal(
        self,
        goal: str,
        priority: str = "normal",
    ) -> Plan:
        """Generate a plan automatically from a high-level goal.

        Uses keyword-based heuristics to decompose the goal into steps.
        In production, this would use an LLM for intelligent decomposition.

        Recognised goal patterns:
        - "reduce error rate" -> analyse + fix + verify
        - "improve reliability" -> introspect + propose + implement + monitor
        - "add skill" -> generate proposal + approve + implement
        - "create domain" -> create domain + register agents + verify
        - "evolve skill" -> analyse + propose + approve + evolve
        - Generic fallback -> introspect + propose + implement + verify
        """
        goal_lower = goal.lower()
        steps: list[PlanStep] = []

        if "error" in goal_lower or "reliability" in goal_lower:
            if "reduce" in goal_lower or "improve" in goal_lower:
                steps = [
                    PlanStep(
                        step_id="s1",
                        name="Analyse errors",
                        action=StepAction.ANALYSE_ERRORS,
                        description="Identify and categorise system errors",
                    ),
                    PlanStep(
                        step_id="s2",
                        name="Fix top errors",
                        action=StepAction.FIX_ERRORS,
                        description="Implement fixes for highest-impact errors",
                        dependencies=["s1"],
                    ),
                    PlanStep(
                        step_id="s3",
                        name="Verify fix",
                        action=StepAction.VERIFY_FIX,
                        description="Verify that the error rate has decreased",
                        dependencies=["s2"],
                    ),
                    PlanStep(
                        step_id="s4",
                        name="Monitor metrics",
                        action=StepAction.MONITOR_METRICS,
                        description="Monitor system metrics for regression",
                        dependencies=["s3"],
                    ),
                ]
            else:
                steps = [
                    PlanStep(
                        step_id="s1",
                        name="Introspect system",
                        action=StepAction.INTROSPECT_SYSTEM,
                        description="Capture current system state",
                    ),
                    PlanStep(
                        step_id="s2",
                        name="Generate proposal",
                        action=StepAction.GENERATE_PROPOSAL,
                        description="Create improvement proposal",
                        dependencies=["s1"],
                    ),
                    PlanStep(
                        step_id="s3",
                        name="Approve proposal",
                        action=StepAction.APPROVE_PROPOSAL,
                        description="Get human approval for changes",
                        dependencies=["s2"],
                    ),
                    PlanStep(
                        step_id="s4",
                        name="Implement proposal",
                        action=StepAction.IMPLEMENT_PROPOSAL,
                        description="Deploy the approved changes",
                        dependencies=["s3"],
                    ),
                ]
        elif "add skill" in goal_lower or "new skill" in goal_lower:
            steps = [
                PlanStep(
                    step_id="s1",
                    name="Generate proposal",
                    action=StepAction.GENERATE_PROPOSAL,
                    description="Create skill addition proposal",
                ),
                PlanStep(
                    step_id="s2",
                    name="Approve proposal",
                    action=StepAction.APPROVE_PROPOSAL,
                    description="Get human approval",
                    dependencies=["s1"],
                ),
                PlanStep(
                    step_id="s3",
                    name="Implement skill",
                    action=StepAction.IMPLEMENT_PROPOSAL,
                    description="Register the new skill",
                    dependencies=["s2"],
                ),
            ]
        elif "create domain" in goal_lower or "new domain" in goal_lower:
            steps = [
                PlanStep(
                    step_id="s1",
                    name="Create domain",
                    action=StepAction.CREATE_DOMAIN,
                    description="Generate domain blueprint from description",
                ),
                PlanStep(
                    step_id="s2",
                    name="Register agents",
                    action=StepAction.REGISTER_AGENTS,
                    description="Register domain agents in the system",
                    dependencies=["s1"],
                ),
            ]
        elif "evolve skill" in goal_lower or "improve skill" in goal_lower:
            steps = [
                PlanStep(
                    step_id="s1",
                    name="Introspect system",
                    action=StepAction.INTROSPECT_SYSTEM,
                    description="Analyse current skill landscape",
                ),
                PlanStep(
                    step_id="s2",
                    name="Generate proposal",
                    action=StepAction.GENERATE_PROPOSAL,
                    description="Create skill evolution proposal",
                    dependencies=["s1"],
                ),
                PlanStep(
                    step_id="s3",
                    name="Approve proposal",
                    action=StepAction.APPROVE_PROPOSAL,
                    description="Get human approval for evolution",
                    dependencies=["s2"],
                ),
                PlanStep(
                    step_id="s4",
                    name="Evolve skill",
                    action=StepAction.EVOLVE_SKILL,
                    description="Apply the skill evolution",
                    dependencies=["s3"],
                ),
            ]
        else:
            # Generic fallback
            steps = [
                PlanStep(
                    step_id="s1",
                    name="Introspect system",
                    action=StepAction.INTROSPECT_SYSTEM,
                    description="Capture current system state",
                ),
                PlanStep(
                    step_id="s2",
                    name="Generate proposal",
                    action=StepAction.GENERATE_PROPOSAL,
                    description="Create improvement proposal based on introspection",
                    dependencies=["s1"],
                ),
                PlanStep(
                    step_id="s3",
                    name="Implement changes",
                    action=StepAction.IMPLEMENT_PROPOSAL,
                    description="Deploy the approved changes",
                    dependencies=["s2"],
                ),
                PlanStep(
                    step_id="s4",
                    name="Verify results",
                    action=StepAction.VERIFY_FIX,
                    description="Verify that the goal has been achieved",
                    dependencies=["s3"],
                ),
            ]

        # Determine failure policy and approval requirement based on priority
        failure_policy = FailurePolicy.ABORT
        requires_approval = False
        if priority == "critical":
            failure_policy = FailurePolicy.PAUSE
            requires_approval = True
        elif priority == "high":
            failure_policy = FailurePolicy.RETRY
            requires_approval = True

        plan = await self.create_plan(
            goal=goal,
            steps=steps,
            description=f"Auto-generated plan for: {goal}",
            failure_policy=failure_policy,
            priority=priority,
            requires_approval=requires_approval,
        )

        await self._tape.log_event(
            event_type="plan.auto_generated",
            payload={
                "plan_id": str(plan.id),
                "goal": goal,
                "step_count": len(steps),
                "priority": priority,
            },
            agent_id="planning-engine",
        )

        return plan

    # ------------------------------------------------------------------
    # Progress and status queries
    # ------------------------------------------------------------------

    async def get_progress(self, plan_id: UUID) -> dict[str, object]:
        """Get detailed progress information for a plan."""
        plan = await self.get_plan(plan_id)

        step_statuses: dict[str, str] = {}
        for step in plan.steps:
            step_statuses[step.step_id] = step.status.value

        return {
            "plan_id": str(plan.id),
            "goal": plan.goal,
            "status": plan.status.value,
            "progress_pct": plan.progress_pct,
            "steps": step_statuses,
            "started_at": plan.started_at.isoformat() if plan.started_at else None,
            "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
        }

    async def get_step(self, plan_id: UUID, step_id: str) -> PlanStep:
        """Get a specific step from a plan."""
        plan = await self.get_plan(plan_id)
        step = next((s for s in plan.steps if s.step_id == step_id), None)
        if step is None:
            raise StepNotFoundError(
                f"Step '{step_id}' not found in plan {plan_id}"
            )
        return step

    # ------------------------------------------------------------------
    # Default action handlers
    # ------------------------------------------------------------------

    def _register_default_actions(self) -> None:
        """Register built-in action handlers for simulated execution.

        In production, these would be replaced with real system operations.
        The simulated handlers mark steps as COMPLETED with placeholder results.
        """

        async def _simulated_handler(step: PlanStep, plan: Plan) -> StepResult:
            """Default handler: simulate execution and succeed."""
            await self._tape.log_event(
                event_type="plan.step_simulated",
                payload={
                    "plan_id": str(plan.id),
                    "step_id": step.step_id,
                    "action": step.action,
                },
                agent_id="planning-engine",
            )
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                result=f"Simulated: {step.action}",
            )

        # Register handlers for all known step actions
        for action in StepAction:
            self._actions.register(action.value, _simulated_handler)

    # ------------------------------------------------------------------
    # Action registry management
    # ------------------------------------------------------------------

    def register_action(
        self,
        action: str,
        handler: Callable[..., Coroutine[None, None, StepResult]],
    ) -> None:
        """Register a custom action handler."""
        self._actions.register(action, handler)

    def list_actions(self) -> list[str]:
        """List all registered action names."""
        return self._actions.list_actions()
