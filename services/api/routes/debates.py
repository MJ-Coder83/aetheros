"""Debate Arena router."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.prime.debate import (
    DebateAlreadyConcludedError,
    DebateFormat,
    DebateNotFoundError,
    DebateParticipant,
    DebateRoundLimitError,
    DebateStatus,
    NoParticipantsError,
)
from services.api.dependencies import DebateServiceDep

router = APIRouter(prefix="/debates", tags=["debates"])


class StartDebateRequest(BaseModel):
    """Schema for starting a new debate."""

    topic: str
    format: DebateFormat = DebateFormat.STANDARD
    participants: list[DebateParticipant] = []
    max_rounds: int = Field(default=3, ge=1, le=20)
    description: str = ""
    initiator: str = "prime"


@router.post("", status_code=201)
async def start_debate(
    body: StartDebateRequest,
    svc: DebateServiceDep,
) -> dict[str, object]:
    """Start a new structured debate."""
    try:
        debate = await svc.start_debate(
            topic=body.topic,
            format=body.format,
            participants=body.participants,
            max_rounds=body.max_rounds,
            description=body.description,
            initiator=body.initiator,
        )
        return debate.model_dump()
    except NoParticipantsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{debate_id}/round")
async def run_debate_round(
    debate_id: UUID,
    svc: DebateServiceDep,
) -> dict[str, object]:
    """Execute one round of a debate."""
    try:
        result = await svc.run_debate_round(debate_id)
        return result.model_dump()
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (DebateAlreadyConcludedError, DebateRoundLimitError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{debate_id}/conclude")
async def conclude_debate(
    debate_id: UUID,
    svc: DebateServiceDep,
) -> dict[str, object]:
    """Conclude a debate and produce a final result."""
    try:
        result = await svc.conclude_debate(debate_id)
        return result.model_dump()
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DebateAlreadyConcludedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{debate_id}/transcript")
async def get_debate_transcript(
    debate_id: UUID,
    svc: DebateServiceDep,
) -> dict[str, object]:
    """Retrieve the full debate transcript."""
    try:
        debate = await svc.get_debate_transcript(debate_id)
        return debate.model_dump()
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("")
async def list_debates(
    svc: DebateServiceDep,
    status: DebateStatus | None = None,
) -> list[dict[str, object]]:
    """List all debates, optionally filtered by status."""
    # To maintain the description in OpenAPI, we can use Query in the function body
    # but for simplicity and to satisfy B008, we use the type hint and
    # let FastAPI handle the default None.
    # If description is absolutely required, we can use Annotated.
    debates = await svc.list_debates(status=status)
    return [d.model_dump() for d in debates]



@router.post("/{debate_id}/abort")
async def abort_debate(
    debate_id: UUID,
    svc: DebateServiceDep,
) -> dict[str, object]:
    """Abort a debate before its natural conclusion."""
    try:
        debate = await svc.abort_debate(debate_id)
        return debate.model_dump()
    except DebateNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DebateAlreadyConcludedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
