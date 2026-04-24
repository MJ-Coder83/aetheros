"""Semantic Tape Querying (NLQ) API routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.api.dependencies import NLQServiceDep

router = APIRouter(prefix="/tape", tags=["tape"])


class NLQueryRequest(BaseModel):
    """Request body for natural language Tape queries."""

    query: str
    max_results: int = 50


@router.post("/query")
async def nl_query(
    body: NLQueryRequest,
    svc: NLQServiceDep,
) -> dict[str, object]:
    """Ask a natural language question about the Tape."""
    result = await svc.ask(query=body.query, max_results=body.max_results)
    return result.model_dump()


@router.get("/queries")
async def list_nl_queries(
    svc: NLQServiceDep,
) -> list[dict[str, object]]:
    """List all stored natural language query results."""
    results = await svc.list_query_results()
    return [r.model_dump() for r in results]


@router.get("/queries/{query_id}")
async def get_nl_query(
    query_id: UUID,
    svc: NLQServiceDep,
) -> dict[str, object]:
    """Retrieve a specific natural language query result."""
    try:
        result = await svc.get_query_result(query_id)
        return result.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
