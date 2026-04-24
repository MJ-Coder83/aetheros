"""Tests for Multi-Step Autonomous Planning Engine.

Covers: plan CRUD, lifecycle, execution, dependency resolution,
failure policies, auto-generation, step operations, progress tracking.
"""

import asyncio

import pytest

from packages.prime.planning import (
    CyclicDependencyError,
    FailurePolicy,
    Plan,
    PlanningEngine,
    PlanNotActiveError,
    PlanNotFoundError,
    PlanResult,
    PlanStatus,
    PlanStep,
    PlanStore,
    PlanTransitionError,
    StepAction,
    StepActionError,
    StepActionRegistry,
    StepNotFoundError,
    StepResult,
    StepStatus,
    _compute_progress,
    _get_ready_steps,
    _validate_no_cycles,
)
from packages.tape.repository import InMemoryTapeRepository
from packages.tape.service import TapeService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tape_service() -> TapeService:
    return TapeService(InMemoryTapeRepository())


@pytest.fixture
def engine(tape_service: TapeService) -> PlanningEngine:
    return PlanningEngine(tape_service=tape_service)


@pytest.fixture
def store() -> PlanStore:
    return PlanStore()


# ---------------------------------------------------------------------------
# Sample steps
# ---------------------------------------------------------------------------

def make_linear_steps() -> list[PlanStep]:
    return [
        PlanStep(step_id="s1", name="Step 1", action="analyse_errors"),
        PlanStep(step_id="s2", name="Step 2", action="fix_errors", dependencies=["s1"]),
        PlanStep(step_id="s3", name="Step 3", action="verify_fix", dependencies=["s2"]),
    ]


def make_parallel_steps() -> list[PlanStep]:
    return [
        PlanStep(step_id="s1", name="Parallel A", action="analyse_errors"),
        PlanStep(step_id="s2", name="Parallel B", action="introspect_system"),
        PlanStep(step_id="s3", name="Merge", action="verify_fix", dependencies=["s1", "s2"]),
    ]


def make_diamond_steps() -> list[PlanStep]:
    return [
        PlanStep(step_id="s1", name="Start", action="introspect_system"),
        PlanStep(step_id="s2", name="Branch A", action="analyse_errors", dependencies=["s1"]),
        PlanStep(step_id="s3", name="Branch B", action="monitor_metrics", dependencies=["s1"]),
        PlanStep(step_id="s4", name="Join", action="verify_fix", dependencies=["s2", "s3"]),
    ]


def make_cyclic_steps() -> list[PlanStep]:
    return [
        PlanStep(step_id="s1", name="A", action="custom", dependencies=["s2"]),
        PlanStep(step_id="s2", name="B", action="custom", dependencies=["s1"]),
    ]


# ===========================================================================
# TestPlanStore
# ===========================================================================

class TestPlanStore:
    def test_add_and_get(self, store: PlanStore) -> None:
        plan = Plan(goal="Test", steps=[])
        store.add(plan)
        assert store.get(plan.id) is not None
        assert store.get(plan.id) is plan

    def test_get_not_found(self, store: PlanStore) -> None:
        from uuid import uuid4
        assert store.get(uuid4()) is None

    def test_list_all(self, store: PlanStore) -> None:
        p1 = Plan(goal="A", steps=[])
        p2 = Plan(goal="B", steps=[])
        store.add(p1)
        store.add(p2)
        assert len(store.list_all()) == 2

    def test_list_by_status(self, store: PlanStore) -> None:
        p1 = Plan(goal="A", steps=[], status=PlanStatus.DRAFT)
        p2 = Plan(goal="B", steps=[], status=PlanStatus.ACTIVE)
        store.add(p1)
        store.add(p2)
        assert len(store.list_by_status(PlanStatus.DRAFT)) == 1
        assert len(store.list_by_status(PlanStatus.ACTIVE)) == 1

    def test_update(self, store: PlanStore) -> None:
        plan = Plan(goal="Original", steps=[])
        store.add(plan)
        updated = plan.model_copy(update={"goal": "Updated"})
        store.update(updated)
        assert store.get(plan.id) is not None
        assert store.get(plan.id) is updated

    def test_update_not_found(self, store: PlanStore) -> None:
        plan = Plan(goal="Ghost", steps=[])
        with pytest.raises(PlanNotFoundError):
            store.update(plan)

    def test_remove(self, store: PlanStore) -> None:
        plan = Plan(goal="Remove me", steps=[])
        store.add(plan)
        store.remove(plan.id)
        assert store.get(plan.id) is None


# ===========================================================================
# TestDependencyValidation
# ===========================================================================

class TestDependencyValidation:
    def test_linear_no_cycle(self) -> None:
        _validate_no_cycles(make_linear_steps())  # should not raise

    def test_parallel_no_cycle(self) -> None:
        _validate_no_cycles(make_parallel_steps())

    def test_diamond_no_cycle(self) -> None:
        _validate_no_cycles(make_diamond_steps())

    def test_cyclic_raises(self) -> None:
        with pytest.raises(CyclicDependencyError):
            _validate_no_cycles(make_cyclic_steps())

    def test_unknown_dependency_raises(self) -> None:
        steps = [
            PlanStep(step_id="s1", name="A", action="custom", dependencies=["s99"]),
        ]
        with pytest.raises(StepNotFoundError):
            _validate_no_cycles(steps)

    def test_self_dependency_raises(self) -> None:
        steps = [
            PlanStep(step_id="s1", name="A", action="custom", dependencies=["s1"]),
        ]
        with pytest.raises(CyclicDependencyError):
            _validate_no_cycles(steps)


# ===========================================================================
# TestReadySteps
# ===========================================================================

class TestReadySteps:
    def test_no_deps_are_ready(self) -> None:
        steps = make_linear_steps()
        ready = _get_ready_steps(steps)
        assert len(ready) == 1
        assert ready[0].step_id == "s1"

    def test_parallel_first_steps_ready(self) -> None:
        steps = make_parallel_steps()
        ready = _get_ready_steps(steps)
        assert len(ready) == 2

    def test_completed_unblocks_dependents(self) -> None:
        steps = make_linear_steps()
        steps[0] = steps[0].model_copy(update={"status": StepStatus.COMPLETED})
        ready = _get_ready_steps(steps)
        assert len(ready) == 1
        assert ready[0].step_id == "s2"

    def test_skipped_also_unblocks(self) -> None:
        steps = make_linear_steps()
        steps[0] = steps[0].model_copy(update={"status": StepStatus.SKIPPED})
        ready = _get_ready_steps(steps)
        assert len(ready) == 1
        assert ready[0].step_id == "s2"

    def test_all_done_no_ready(self) -> None:
        steps = make_linear_steps()
        for i in range(len(steps)):
            steps[i] = steps[i].model_copy(update={"status": StepStatus.COMPLETED})
        ready = _get_ready_steps(steps)
        assert len(ready) == 0

    def test_diamond_partial(self) -> None:
        steps = make_diamond_steps()
        steps[0] = steps[0].model_copy(update={"status": StepStatus.COMPLETED})
        ready = _get_ready_steps(steps)
        assert len(ready) == 2  # s2, s3


# ===========================================================================
# TestComputeProgress
# ===========================================================================

class TestComputeProgress:
    def test_empty_steps(self) -> None:
        assert _compute_progress([]) == 0.0

    def test_nothing_done(self) -> None:
        assert _compute_progress(make_linear_steps()) == 0.0

    def test_one_third_done(self) -> None:
        steps = make_linear_steps()
        steps[0] = steps[0].model_copy(update={"status": StepStatus.COMPLETED})
        assert _compute_progress(steps) == pytest.approx(33.3, abs=0.1)

    def test_all_done(self) -> None:
        steps = make_linear_steps()
        for i in range(len(steps)):
            steps[i] = steps[i].model_copy(update={"status": StepStatus.COMPLETED})
        assert _compute_progress(steps) == 100.0


# ===========================================================================
# TestStepActionRegistry
# ===========================================================================

class TestStepActionRegistry:
    def test_register_and_get(self) -> None:
        registry = StepActionRegistry()

        async def handler(step: PlanStep, plan: Plan) -> StepResult:
            return StepResult(step_id=step.step_id, status=StepStatus.COMPLETED)

        registry.register("custom_action", handler)
        assert registry.get("custom_action") is handler

    def test_get_not_found(self) -> None:
        registry = StepActionRegistry()
        assert registry.get("nonexistent") is None

    def test_list_actions(self) -> None:
        registry = StepActionRegistry()

        async def h1(step: PlanStep, plan: Plan) -> StepResult:
            return StepResult(step_id=step.step_id, status=StepStatus.COMPLETED)

        async def h2(step: PlanStep, plan: Plan) -> StepResult:
            return StepResult(step_id=step.step_id, status=StepStatus.COMPLETED)

        registry.register("beta", h1)
        registry.register("alpha", h2)
        assert registry.list_actions() == ["alpha", "beta"]


# ===========================================================================
# TestCreatePlan
# ===========================================================================

class TestCreatePlan:
    @pytest.mark.asyncio
    async def test_create_basic_plan(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(
            goal="Reduce errors",
            steps=make_linear_steps(),
        )
        assert plan.goal == "Reduce errors"
        assert plan.status == PlanStatus.DRAFT
        assert len(plan.steps) == 3
        assert plan.progress_pct == 0.0

    @pytest.mark.asyncio
    async def test_first_steps_marked_ready(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(
            goal="Test",
            steps=make_linear_steps(),
        )
        assert plan.steps[0].status == StepStatus.READY
        assert plan.steps[1].status == StepStatus.PENDING

    @pytest.mark.asyncio
    async def test_parallel_first_steps_ready(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(
            goal="Test",
            steps=make_parallel_steps(),
        )
        assert plan.steps[0].status == StepStatus.READY
        assert plan.steps[1].status == StepStatus.READY
        assert plan.steps[2].status == StepStatus.PENDING

    @pytest.mark.asyncio
    async def test_empty_goal_raises(self, engine: PlanningEngine) -> None:
        with pytest.raises(ValueError, match="goal"):
            await engine.create_plan(goal="", steps=[])

    @pytest.mark.asyncio
    async def test_duplicate_step_ids_raises(self, engine: PlanningEngine) -> None:
        steps = [
            PlanStep(step_id="s1", name="A", action="custom"),
            PlanStep(step_id="s1", name="B", action="custom"),
        ]
        with pytest.raises(ValueError, match="unique"):
            await engine.create_plan(goal="Test", steps=steps)

    @pytest.mark.asyncio
    async def test_cyclic_deps_raises(self, engine: PlanningEngine) -> None:
        with pytest.raises(CyclicDependencyError):
            await engine.create_plan(goal="Test", steps=make_cyclic_steps())

    @pytest.mark.asyncio
    async def test_stored_in_store(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(
            goal="Stored?",
            steps=make_linear_steps(),
        )
        retrieved = await engine.get_plan(plan.id)
        assert retrieved.id == plan.id

    @pytest.mark.asyncio
    async def test_logs_to_tape(self, engine: PlanningEngine) -> None:
        await engine.create_plan(goal="Tape test", steps=make_linear_steps())
        entries = await engine._tape.get_entries(event_type="plan.created")
        assert len(entries) == 1


# ===========================================================================
# TestPlanLifecycle
# ===========================================================================

class TestPlanLifecycle:
    @pytest.mark.asyncio
    async def test_activate_draft(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        activated = await engine.activate_plan(plan.id)
        assert activated.status == PlanStatus.ACTIVE
        assert activated.started_at is not None

    @pytest.mark.asyncio
    async def test_cannot_activate_active(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.activate_plan(plan.id)
        with pytest.raises(PlanTransitionError):
            await engine.activate_plan(plan.id)

    @pytest.mark.asyncio
    async def test_abort_active(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.activate_plan(plan.id)
        aborted = await engine.abort_plan(plan.id, reason="Changed mind")
        assert aborted.status == PlanStatus.ABORTED
        assert aborted.completed_at is not None

    @pytest.mark.asyncio
    async def test_cannot_abort_completed(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.activate_plan(plan.id)
        # Execute to completion
        await engine.execute_plan(plan.id)
        with pytest.raises(PlanTransitionError):
            await engine.abort_plan(plan.id)

    @pytest.mark.asyncio
    async def test_delete_draft(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.delete_plan(plan.id)
        with pytest.raises(PlanNotFoundError):
            await engine.get_plan(plan.id)

    @pytest.mark.asyncio
    async def test_cannot_delete_active(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.activate_plan(plan.id)
        with pytest.raises(PlanTransitionError):
            await engine.delete_plan(plan.id)


# ===========================================================================
# TestPlanExecution
# ===========================================================================

class TestPlanExecution:
    @pytest.mark.asyncio
    async def test_execute_linear_plan(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED
        assert result.steps_completed == 3
        assert result.steps_failed == 0
        assert result.progress_pct == 100.0

    @pytest.mark.asyncio
    async def test_execute_auto_activates(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        assert plan.status == PlanStatus.DRAFT
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_parallel_plan(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_parallel_steps())
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED
        assert result.steps_completed == 3

    @pytest.mark.asyncio
    async def test_execute_diamond_plan(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_diamond_steps())
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED
        assert result.steps_completed == 4

    @pytest.mark.asyncio
    async def test_execute_empty_steps_plan(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Empty", steps=[])
        await engine.activate_plan(plan.id)
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED
        assert result.steps_completed == 0

    @pytest.mark.asyncio
    async def test_execute_logs_tape_events(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.execute_plan(plan.id)
        events = await engine._tape.get_entries(event_type="plan.step_completed")
        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_execute_updates_progress(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        result = await engine.execute_plan(plan.id)
        assert result.progress_pct == 100.0

    @pytest.mark.asyncio
    async def test_result_duration_positive(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        result = await engine.execute_plan(plan.id)
        assert result.duration_seconds >= 0


# ===========================================================================
# TestFailurePolicyAbort
# ===========================================================================

class TestFailurePolicyAbort:
    @pytest.mark.asyncio
    async def test_abort_on_step_failure(self, engine: PlanningEngine) -> None:
        # Register a handler that always fails
        async def failing_handler(step: PlanStep, plan: Plan) -> StepResult:
            raise StepActionError("Deliberate failure")

        engine.register_action("fail_action", failing_handler)

        steps = [
            PlanStep(step_id="s1", name="Fail", action="fail_action"),
            PlanStep(step_id="s2", name="After", action="verify_fix", dependencies=["s1"]),
        ]
        plan = await engine.create_plan(
            goal="Test abort",
            steps=steps,
            failure_policy=FailurePolicy.ABORT,
        )
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.FAILED
        assert result.steps_failed >= 1
        assert result.error_summary is not None


# ===========================================================================
# TestFailurePolicySkip
# ===========================================================================

class TestFailurePolicySkip:
    @pytest.mark.asyncio
    async def test_skip_failed_step(self, engine: PlanningEngine) -> None:
        async def failing_handler(step: PlanStep, plan: Plan) -> StepResult:
            raise StepActionError("Skip me")

        engine.register_action("skip_action", failing_handler)

        steps = [
            PlanStep(step_id="s1", name="Skip", action="skip_action"),
            PlanStep(step_id="s2", name="After", action="verify_fix", dependencies=["s1"]),
        ]
        plan = await engine.create_plan(
            goal="Test skip",
            steps=steps,
            failure_policy=FailurePolicy.SKIP,
        )
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED
        assert result.steps_skipped >= 1

    @pytest.mark.asyncio
    async def test_skipped_step_unblocks_deps(self, engine: PlanningEngine) -> None:
        async def failing_handler(step: PlanStep, plan: Plan) -> StepResult:
            raise StepActionError("Skip me")

        engine.register_action("skip_dep_action", failing_handler)

        steps = [
            PlanStep(step_id="s1", name="Skip", action="skip_dep_action"),
            PlanStep(step_id="s2", name="After", action="verify_fix", dependencies=["s1"]),
        ]
        plan = await engine.create_plan(
            goal="Skip chain",
            steps=steps,
            failure_policy=FailurePolicy.SKIP,
        )
        result = await engine.execute_plan(plan.id)
        # s1 skipped, s2 should still run and complete
        assert result.steps_completed >= 1


# ===========================================================================
# TestFailurePolicyRetry
# ===========================================================================

class TestFailurePolicyRetry:
    @pytest.mark.asyncio
    async def test_retry_then_succeed(self, engine: PlanningEngine) -> None:
        call_count = 0

        async def flaky_handler(step: PlanStep, plan: Plan) -> StepResult:
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise StepActionError("Transient error")
            return StepResult(step_id=step.step_id, status=StepStatus.COMPLETED)

        engine.register_action("flaky_action", flaky_handler)

        steps = [
            PlanStep(
                step_id="s1", name="Flaky", action="flaky_action",
                max_retries=2,
            ),
        ]
        plan = await engine.create_plan(
            goal="Test retry",
            steps=steps,
            failure_policy=FailurePolicy.RETRY,
        )
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED
        assert call_count >= 2  # initial fail + retry

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, engine: PlanningEngine) -> None:
        async def always_fail(step: PlanStep, plan: Plan) -> StepResult:
            raise StepActionError("Always fails")

        engine.register_action("always_fail", always_fail)

        steps = [
            PlanStep(
                step_id="s1", name="Fail", action="always_fail",
                max_retries=1,
            ),
        ]
        plan = await engine.create_plan(
            goal="Exhausted",
            steps=steps,
            failure_policy=FailurePolicy.RETRY,
        )
        result = await engine.execute_plan(plan.id)
        # After retries exhausted with RETRY policy and no more retries,
        # the step stays FAILED and plan is FAILED
        assert result.steps_failed >= 1


# ===========================================================================
# TestFailurePolicyPause
# ===========================================================================

class TestFailurePolicyPause:
    @pytest.mark.asyncio
    async def test_pause_on_failure(self, engine: PlanningEngine) -> None:
        async def failing_handler(step: PlanStep, plan: Plan) -> StepResult:
            raise StepActionError("Pause me")

        engine.register_action("pause_action", failing_handler)

        steps = [
            PlanStep(step_id="s1", name="Pause", action="pause_action"),
            PlanStep(step_id="s2", name="After", action="verify_fix", dependencies=["s1"]),
        ]
        plan = await engine.create_plan(
            goal="Test pause",
            steps=steps,
            failure_policy=FailurePolicy.PAUSE,
        )
        result = await engine.execute_plan(plan.id)
        # Plan stays ACTIVE (paused), step is FAILED
        assert result.status == PlanStatus.ACTIVE
        updated_plan = await engine.get_plan(plan.id)
        assert any(s.status == StepStatus.FAILED for s in updated_plan.steps)


# ===========================================================================
# TestStepTimeout
# ===========================================================================

class TestStepTimeout:
    @pytest.mark.asyncio
    async def test_timeout_marks_step_failed(self, engine: PlanningEngine) -> None:
        async def slow_handler(step: PlanStep, plan: Plan) -> StepResult:
            await asyncio.sleep(10)
            return StepResult(step_id=step.step_id, status=StepStatus.COMPLETED)

        engine.register_action("slow_action", slow_handler)

        steps = [PlanStep(step_id="s1", name="Slow", action="slow_action")]
        plan = await engine.create_plan(
            goal="Timeout test",
            steps=steps,
            failure_policy=FailurePolicy.ABORT,
        )
        result = await engine.execute_plan(plan.id, step_timeout=0.1)
        assert result.status == PlanStatus.FAILED


# ===========================================================================
# TestStepOperations
# ===========================================================================

class TestStepOperations:
    @pytest.mark.asyncio
    async def test_skip_step(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.activate_plan(plan.id)
        skipped = await engine.skip_step(plan.id, "s1")
        assert skipped.status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_skip_unblocks_deps(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.activate_plan(plan.id)
        await engine.skip_step(plan.id, "s1")
        updated = await engine.get_plan(plan.id)
        assert updated.steps[1].status == StepStatus.READY

    @pytest.mark.asyncio
    async def test_skip_not_found_step(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.activate_plan(plan.id)
        with pytest.raises(StepNotFoundError):
            await engine.skip_step(plan.id, "nonexistent")

    @pytest.mark.asyncio
    async def test_skip_wrong_status(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.activate_plan(plan.id)
        # Execute step 1 first
        await engine.execute_step(plan.id, "s1")
        # Can't skip a completed step
        with pytest.raises(PlanTransitionError):
            await engine.skip_step(plan.id, "s1")

    @pytest.mark.asyncio
    async def test_execute_single_step(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        await engine.activate_plan(plan.id)
        result = await engine.execute_step(plan.id, "s1")
        assert result.status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_step_not_active(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        with pytest.raises(PlanNotActiveError):
            await engine.execute_step(plan.id, "s1")

    @pytest.mark.asyncio
    async def test_retry_failed_step(self, engine: PlanningEngine) -> None:
        call_count = 0

        async def flaky(step: PlanStep, plan: Plan) -> StepResult:
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise StepActionError("First fail")
            return StepResult(step_id=step.step_id, status=StepStatus.COMPLETED)

        engine.register_action("flaky_retry", flaky)

        steps = [PlanStep(step_id="s1", name="Flaky", action="flaky_retry")]
        plan = await engine.create_plan(
            goal="Test", steps=steps, failure_policy=FailurePolicy.PAUSE,
        )
        await engine.execute_plan(plan.id)
        # Step failed, plan paused
        result = await engine.retry_step(plan.id, "s1")
        assert result.status == StepStatus.COMPLETED


# ===========================================================================
# TestPlanQueries
# ===========================================================================

class TestPlanQueries:
    @pytest.mark.asyncio
    async def test_list_plans(self, engine: PlanningEngine) -> None:
        await engine.create_plan(goal="A", steps=make_linear_steps())
        await engine.create_plan(goal="B", steps=make_linear_steps())
        plans = await engine.list_plans()
        assert len(plans) == 2

    @pytest.mark.asyncio
    async def test_list_by_status(self, engine: PlanningEngine) -> None:
        await engine.create_plan(goal="Draft", steps=make_linear_steps())
        p2 = await engine.create_plan(goal="Active", steps=make_linear_steps())
        await engine.activate_plan(p2.id)
        drafts = await engine.list_plans(status=PlanStatus.DRAFT)
        actives = await engine.list_plans(status=PlanStatus.ACTIVE)
        assert len(drafts) == 1
        assert len(actives) == 1

    @pytest.mark.asyncio
    async def test_get_progress(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        progress = await engine.get_progress(plan.id)
        assert progress["status"] == PlanStatus.DRAFT.value
        assert progress["progress_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_get_step(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        step = await engine.get_step(plan.id, "s1")
        assert step.name == "Step 1"

    @pytest.mark.asyncio
    async def test_get_step_not_found(self, engine: PlanningEngine) -> None:
        plan = await engine.create_plan(goal="Test", steps=make_linear_steps())
        with pytest.raises(StepNotFoundError):
            await engine.get_step(plan.id, "nonexistent")


# ===========================================================================
# TestAutoPlanGeneration
# ===========================================================================

class TestAutoPlanGeneration:
    @pytest.mark.asyncio
    async def test_reduce_error_rate_goal(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("Reduce system error rate below 5%")
        assert "error" in plan.goal.lower() or "error" in plan.description.lower()
        assert len(plan.steps) >= 3
        # First step should have no deps
        assert plan.steps[0].dependencies == []

    @pytest.mark.asyncio
    async def test_improve_reliability_goal(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("Improve system reliability")
        assert len(plan.steps) >= 3

    @pytest.mark.asyncio
    async def test_add_skill_goal(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("Add new skill for data analysis")
        assert len(plan.steps) >= 2

    @pytest.mark.asyncio
    async def test_create_domain_goal(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("Create domain for legal research")
        assert len(plan.steps) >= 2

    @pytest.mark.asyncio
    async def test_evolve_skill_goal(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("Evolve skill for better performance")
        assert len(plan.steps) >= 3

    @pytest.mark.asyncio
    async def test_generic_goal(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("Make the system better overall")
        assert len(plan.steps) >= 3

    @pytest.mark.asyncio
    async def test_critical_priority_requires_approval(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("Fix critical bug", priority="critical")
        assert plan.requires_approval is True
        assert plan.failure_policy == FailurePolicy.PAUSE

    @pytest.mark.asyncio
    async def test_high_priority_requires_approval(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("Improve performance", priority="high")
        assert plan.requires_approval is True
        assert plan.failure_policy == FailurePolicy.RETRY

    @pytest.mark.asyncio
    async def test_normal_priority_no_approval(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("General improvement")
        assert plan.requires_approval is False

    @pytest.mark.asyncio
    async def test_empty_goal_raises(self, engine: PlanningEngine) -> None:
        with pytest.raises(ValueError):
            await engine.generate_plan_from_goal("")

    @pytest.mark.asyncio
    async def test_logs_auto_generation_to_tape(self, engine: PlanningEngine) -> None:
        await engine.generate_plan_from_goal("Reduce error rate")
        entries = await engine._tape.get_entries(event_type="plan.auto_generated")
        assert len(entries) == 1


# ===========================================================================
# TestGeneratedPlanExecution
# ===========================================================================

class TestGeneratedPlanExecution:
    @pytest.mark.asyncio
    async def test_execute_generated_error_plan(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("Reduce system error rate below 5%")
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED
        assert result.progress_pct == 100.0

    @pytest.mark.asyncio
    async def test_execute_generated_domain_plan(self, engine: PlanningEngine) -> None:
        plan = await engine.generate_plan_from_goal("Create domain for trading")
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED


# ===========================================================================
# TestDataModels
# ===========================================================================

class TestDataModels:
    def test_plan_status_enum(self) -> None:
        assert PlanStatus.DRAFT.value == "draft"
        assert PlanStatus.ACTIVE.value == "active"
        assert PlanStatus.COMPLETED.value == "completed"
        assert PlanStatus.FAILED.value == "failed"
        assert PlanStatus.ABORTED.value == "aborted"

    def test_step_status_enum(self) -> None:
        assert StepStatus.PENDING.value == "pending"
        assert StepStatus.READY.value == "ready"
        assert StepStatus.RUNNING.value == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.FAILED.value == "failed"
        assert StepStatus.SKIPPED.value == "skipped"
        assert StepStatus.RETRYING.value == "retrying"

    def test_failure_policy_enum(self) -> None:
        assert FailurePolicy.RETRY.value == "retry"
        assert FailurePolicy.SKIP.value == "skip"
        assert FailurePolicy.ABORT.value == "abort"
        assert FailurePolicy.PAUSE.value == "pause"

    def test_step_action_enum(self) -> None:
        assert len(StepAction) >= 10

    def test_plan_defaults(self) -> None:
        plan = Plan(goal="Test")
        assert plan.status == PlanStatus.DRAFT
        assert plan.created_by == "prime"
        assert plan.priority == "normal"
        assert plan.progress_pct == 0.0

    def test_step_defaults(self) -> None:
        step = PlanStep(step_id="s1", name="Test", action="custom")
        assert step.status == StepStatus.PENDING
        assert step.dependencies == []
        assert step.max_retries == 2
        assert step.retry_count == 0

    def test_plan_result_model(self) -> None:
        result = PlanResult(
            plan_id=Plan(goal="T").id,
            status=PlanStatus.COMPLETED,
            steps_completed=3,
            steps_failed=0,
            steps_skipped=0,
            total_steps=3,
            progress_pct=100.0,
            duration_seconds=1.5,
        )
        assert result.steps_completed == 3

    def test_step_result_model(self) -> None:
        result = StepResult(
            step_id="s1",
            status=StepStatus.COMPLETED,
            result="Done",
        )
        assert result.result == "Done"


# ===========================================================================
# TestCustomActionHandlers
# ===========================================================================

class TestCustomActionHandlers:
    @pytest.mark.asyncio
    async def test_custom_handler_executes(self, engine: PlanningEngine) -> None:
        async def custom(step: PlanStep, plan: Plan) -> StepResult:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                result=f"Custom result for {step.name}",
            )

        engine.register_action("my_custom", custom)
        steps = [PlanStep(step_id="s1", name="Custom", action="my_custom")]
        plan = await engine.create_plan(goal="Custom", steps=steps)
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_list_registered_actions(self, engine: PlanningEngine) -> None:
        # Default actions should be registered
        actions = engine.list_actions()
        assert len(actions) >= len(StepAction)

    @pytest.mark.asyncio
    async def test_override_default_action(self, engine: PlanningEngine) -> None:
        async def override(step: PlanStep, plan: Plan) -> StepResult:
            return StepResult(
                step_id=step.step_id,
                status=StepStatus.COMPLETED,
                result="Overridden",
            )

        engine.register_action(StepAction.ANALYSE_ERRORS.value, override)
        steps = [PlanStep(step_id="s1", name="Test", action=StepAction.ANALYSE_ERRORS)]
        plan = await engine.create_plan(goal="Override", steps=steps)
        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED


# ===========================================================================
# TestPlanningIntegration
# ===========================================================================

class TestPlanningIntegration:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, engine: PlanningEngine) -> None:
        """Create -> Activate -> Execute -> Complete."""
        plan = await engine.create_plan(
            goal="Full lifecycle test",
            steps=make_linear_steps(),
        )
        assert plan.status == PlanStatus.DRAFT

        await engine.activate_plan(plan.id)
        plan = await engine.get_plan(plan.id)
        assert plan.status == PlanStatus.ACTIVE

        result = await engine.execute_plan(plan.id)
        assert result.status == PlanStatus.COMPLETED
        assert result.progress_pct == 100.0

    @pytest.mark.asyncio
    async def test_all_tape_events_logged(self, engine: PlanningEngine) -> None:
        """Verify Tape events are logged for the full lifecycle."""
        plan = await engine.create_plan(goal="Tape test", steps=make_linear_steps())
        await engine.execute_plan(plan.id)

        created = await engine._tape.get_entries(event_type="plan.created")
        activated = await engine._tape.get_entries(event_type="plan.activated")
        step_completed = await engine._tape.get_entries(event_type="plan.step_completed")
        plan_completed = await engine._tape.get_entries(event_type="plan.completed")

        assert len(created) == 1
        assert len(activated) == 1
        assert len(step_completed) == 3
        assert len(plan_completed) == 1

    @pytest.mark.asyncio
    async def test_abort_and_delete(self, engine: PlanningEngine) -> None:
        """Create -> Activate -> Abort -> Delete."""
        plan = await engine.create_plan(goal="Abort test", steps=make_linear_steps())
        await engine.activate_plan(plan.id)
        await engine.abort_plan(plan.id, reason="Not needed")

        plan = await engine.get_plan(plan.id)
        assert plan.status == PlanStatus.ABORTED

        await engine.delete_plan(plan.id)
        with pytest.raises(PlanNotFoundError):
            await engine.get_plan(plan.id)

    @pytest.mark.asyncio
    async def test_multiple_plans(self, engine: PlanningEngine) -> None:
        """Create multiple plans and manage them independently."""
        p1 = await engine.create_plan(goal="Plan A", steps=make_linear_steps())
        p2 = await engine.create_plan(goal="Plan B", steps=make_parallel_steps())

        r1 = await engine.execute_plan(p1.id)
        r2 = await engine.execute_plan(p2.id)

        assert r1.status == PlanStatus.COMPLETED
        assert r2.status == PlanStatus.COMPLETED
