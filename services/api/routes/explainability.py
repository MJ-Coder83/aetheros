"""Explainability Dashboard router."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.prime.explainability import (
    ActionType,
    ExplanationNotFoundError,
)
from services.api.dependencies import ExplainabilityServiceDep

router = APIRouter(prefix="/explain", tags=["explainability"])


class GenerateExplanationRequest(BaseModel):
    """Schema for generating an explanation."""

    action_id: str
    action_type: ActionType
    context: dict[str, object] = Field(default_factory=dict)


class DecisionTraceRequest(BaseModel):
    """Schema for requesting a decision trace."""

    action_id: str
    action_type: ActionType | None = None
    context: dict[str, object] = Field(default_factory=dict)


class HighlightFactorsRequest(BaseModel):
    """Schema for highlighting key factors."""

    action_id: str
    action_type: ActionType | None = None
    context: dict[str, object] = Field(default_factory=dict)
    top_n: int = Field(default=5, ge=1, le=20)


class CompareAlternativesRequest(BaseModel):
    """Schema for comparing alternatives."""

    action_id: str
    alternatives: list[dict[str, object]] = []
    action_type: ActionType | None = None
    context: dict[str, object] = Field(default_factory=dict)


@router.post("/generate", status_code=201)
async def generate_explanation(
    body: GenerateExplanationRequest,
    svc: ExplainabilityServiceDep,
) -> dict[str, object]:
    """Generate a full explanation for a system action."""
    explanation = await svc.generate_explanation(
        action_id=body.action_id,
        action_type=body.action_type,
        context=body.context,
    )
    return explanation.model_dump()


@router.post("/trace")
async def get_decision_trace(
    body: DecisionTraceRequest,
    svc: ExplainabilityServiceDep,
) -> dict[str, object]:
    """Get the full decision trace for an action."""
    trace = await svc.get_decision_trace(
        action_id=body.action_id,
        action_type=body.action_type,
        context=body.context,
    )
    return trace.model_dump()


@router.post("/factors")
async def highlight_key_factors(
    body: HighlightFactorsRequest,
    svc: ExplainabilityServiceDep,
) -> list[dict[str, object]]:
    """Highlight the top factors that influenced a decision."""
    factors = await svc.highlight_key_factors(
        action_id=body.action_id,
        action_type=body.action_type,
        context=body.context,
        top_n=body.top_n,
    )
    return [f.model_dump() for f in factors]


@router.post("/compare")
async def compare_alternatives(
    body: CompareAlternativesRequest,
    svc: ExplainabilityServiceDep,
) -> dict[str, object]:
    """Compare alternatives and explain why the chosen option was selected."""
    comparison = await svc.compare_alternatives(
        action_id=body.action_id,
        alternatives=body.alternatives,
        action_type=body.action_type,
        context=body.context,
    )
    return comparison.model_dump()


@router.get("/{explanation_id}")
async def get_explanation(
    explanation_id: UUID,
    svc: ExplainabilityServiceDep,
) -> dict[str, object]:
    """Retrieve a stored explanation by ID."""
    try:
        explanation = await svc.get_explanation(explanation_id)
        return explanation.model_dump()
    except ExplanationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("")
async def list_explanations(
    svc: ExplainabilityServiceDep,
    action_type: ActionType | None = None,
) -> list[dict[str, object]]:
    """List all stored explanations, optionally filtered by action type."""
    explanations = await svc.list_explanations(action_type=action_type)
    return [e.model_dump() for e in explanations]
