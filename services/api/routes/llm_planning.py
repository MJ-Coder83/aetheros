"""LLM Planning API routes."""


from fastapi import APIRouter
from pydantic import BaseModel, Field

from packages.prime.llm_planning import (
    DecompositionStrategy,
)
from services.api.dependencies import LLMPlannerServiceDep

router = APIRouter(prefix="/planning", tags=["planning"])


class DecomposeGoalRequest(BaseModel):
    """Request body for LLM goal decomposition."""

    goal: str
    context: dict[str, object] = Field(default_factory=dict)
    max_steps: int = 10
    strategy: str = "llm"


@router.post("/decompose")
async def decompose_goal(
    body: DecomposeGoalRequest,
    svc: LLMPlannerServiceDep,
) -> dict[str, object]:
    """Decompose a goal using LLM-powered planning."""
    strategy = DecompositionStrategy(body.strategy)
    result = await svc.decompose_goal(
        goal=body.goal,
        context=body.context,
        max_steps=body.max_steps,
        strategy=strategy,
    )
    return result.model_dump()


@router.get("/decompositions")
async def list_decompositions(
    svc: LLMPlannerServiceDep,
) -> list[dict[str, object]]:
    """List all stored decomposition results."""
    results = await svc.list_decompositions()
    return [r.model_dump() for r in results]


@router.post("/should-use-llm")
async def should_use_llm(
    svc: LLMPlannerServiceDep,
    goal: str = "",
) -> dict[str, object]:
    """Determine whether a goal would benefit from LLM decomposition."""
    use_llm = await svc.should_use_llm(goal)
    return {"goal": goal, "use_llm": use_llm}
