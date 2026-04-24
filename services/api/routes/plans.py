"""Planning Engine router."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.prime.planning import (
    CyclicDependencyError,
    FailurePolicy,
    PlanNotActiveError,
    PlanNotFoundError,
    PlanStatus,
    PlanStep,
    StepNotFoundError,
)
from services.api.dependencies import PlanningServiceDep

router = APIRouter(prefix="/plans", tags=["plans"])


class CreatePlanRequest(BaseModel):
    """Schema for creating a plan."""

    goal: str
    steps: list[dict[str, object]] = []
    description: str = ""
    failure_policy: FailurePolicy = FailurePolicy.ABORT
    priority: str = "normal"
    requires_approval: bool = False
    created_by: str = "prime"


class ExecutePlanRequest(BaseModel):
    """Schema for executing a plan."""

    step_timeout: float = Field(default=30.0, ge=1.0, le=300.0)


class GeneratePlanRequest(BaseModel):
    """Schema for auto-generating a plan from a goal."""

    goal: str
    priority: str = "normal"


@router.post("", status_code=201)
async def create_plan(
    body: CreatePlanRequest,
    svc: PlanningServiceDep,
) -> dict[str, object]:
    """Create a new multi-step plan."""
    steps = [PlanStep(**s) for s in body.steps]  # type: ignore[arg-type]
    try:
        plan = await svc.create_plan(
            goal=body.goal,
            steps=steps,
            description=body.description,
            failure_policy=body.failure_policy,
            priority=body.priority,
            requires_approval=body.requires_approval,
            created_by=body.created_by,
        )
        return plan.model_dump()
    except (CyclicDependencyError, StepNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate", status_code=201)
async def generate_plan(
    body: GeneratePlanRequest,
    svc: PlanningServiceDep,
) -> dict[str, object]:
    """Auto-generate a plan from a high-level goal."""
    try:
        plan = await svc.generate_plan_from_goal(
            goal=body.goal,
            priority=body.priority,
        )
        return plan.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{plan_id}/activate")
async def activate_plan(
    plan_id: UUID,
    svc: PlanningServiceDep,
) -> dict[str, object]:
    """Activate a draft plan."""
    try:
        plan = await svc.activate_plan(plan_id)
        return plan.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PlanNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{plan_id}/execute")
async def execute_plan(
    plan_id: UUID,
    svc: PlanningServiceDep,
    body: ExecutePlanRequest | None = None,
) -> dict[str, object]:
    """Execute all steps in a plan."""
    timeout = body.step_timeout if body else 30.0
    try:
        result = await svc.execute_plan(plan_id, step_timeout=timeout)
        return result.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PlanNotActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{plan_id}/abort")
async def abort_plan(
    svc: PlanningServiceDep,
    plan_id: UUID,
    reason: str | None = None,
) -> dict[str, object]:
    """Abort an active plan."""
    try:
        plan = await svc.abort_plan(plan_id, reason=reason)
        return plan.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("")
async def list_plans(
    svc: PlanningServiceDep,
    status: PlanStatus | None = None,
) -> list[dict[str, object]]:
    """List all plans, optionally filtered by status."""
    plans = await svc.list_plans(status=status)
    return [p.model_dump() for p in plans]


@router.get("/{plan_id}")
async def get_plan(
    plan_id: UUID,
    svc: PlanningServiceDep,
) -> dict[str, object]:
    """Get a plan by ID."""
    try:
        plan = await svc.get_plan(plan_id)
        return plan.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{plan_id}/progress")
async def get_plan_progress(
    plan_id: UUID,
    svc: PlanningServiceDep,
) -> dict[str, object]:
    """Get detailed progress for a plan."""
    try:
        return await svc.get_progress(plan_id)
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{plan_id}/steps/{step_id}/skip")
async def skip_plan_step(
    svc: PlanningServiceDep,
    plan_id: UUID,
    step_id: str,
) -> dict[str, object]:
    """Skip a step in a plan."""
    try:
        step = await svc.skip_step(plan_id, step_id)
        return step.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StepNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{plan_id}/steps/{step_id}/retry")
async def retry_plan_step(
    svc: PlanningServiceDep,
    plan_id: UUID,
    step_id: str,
) -> dict[str, object]:
    """Retry a failed step."""
    try:
        result = await svc.retry_step(plan_id, step_id)
        return result.model_dump()
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StepNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{plan_id}")
async def delete_plan(
    plan_id: UUID,
    svc: PlanningServiceDep,
) -> dict[str, str]:
    """Delete a draft or aborted plan."""
    try:
        await svc.delete_plan(plan_id)
        return {"status": "deleted"}
    except PlanNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
