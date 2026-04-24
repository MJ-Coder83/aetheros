"""Knowledge Transfer router."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from packages.prime.knowledge_transfer import (
    KnowledgeTransferError,
    KnowledgeType,
    TransferNotFoundError,
    TransferStatus,
)
from services.api.dependencies import KnowledgeTransferServiceDep

router = APIRouter(prefix="/knowledge-transfer", tags=["knowledge-transfer"])


class TransferKnowledgeRequest(BaseModel):
    """Request body for initiating a knowledge transfer."""

    source_domain_id: str
    target_domain_id: str
    source_metadata: dict[str, object] = Field(default_factory=dict)
    target_metadata: dict[str, object] = Field(default_factory=dict)
    knowledge_types: list[str] | None = None
    created_by: str = "prime"


class ExtractKnowledgeRequest(BaseModel):
    """Request body for extracting knowledge from a domain."""

    domain_id: str
    domain_metadata: dict[str, object] = Field(default_factory=dict)
    knowledge_types: list[str] | None = None


class AssessCompatibilityRequest(BaseModel):
    """Request body for assessing knowledge compatibility."""

    source_domain_id: str
    target_metadata: dict[str, object] = Field(default_factory=dict)
    source_metadata: dict[str, object] = Field(default_factory=dict)
    knowledge_types: list[str] | None = None


class RecommendTransfersRequest(BaseModel):
    """Request body for recommending knowledge transfers."""

    domain_id: str
    all_domain_metadata: dict[str, dict[str, object]] = Field(default_factory=dict)


@router.post("/transfer")
async def execute_knowledge_transfer(
    body: TransferKnowledgeRequest,
    svc: KnowledgeTransferServiceDep,
) -> dict[str, object]:
    """Execute a cross-domain knowledge transfer."""
    ktypes = None
    if body.knowledge_types is not None:
        ktypes = [KnowledgeType(t) for t in body.knowledge_types]

    record = await svc.transfer_knowledge(
        source_domain_id=body.source_domain_id,
        target_domain_id=body.target_domain_id,
        source_metadata=body.source_metadata,
        target_metadata=body.target_metadata,
        knowledge_types=ktypes,
        created_by=body.created_by,
    )
    return record.model_dump()


@router.post("/extract")
async def extract_knowledge(
    body: ExtractKnowledgeRequest,
    svc: KnowledgeTransferServiceDep,
) -> list[dict[str, object]]:
    """Extract transferable knowledge from a domain."""
    ktypes = None
    if body.knowledge_types is not None:
        ktypes = [KnowledgeType(t) for t in body.knowledge_types]

    items = await svc.extract_knowledge(
        domain_id=body.domain_id,
        domain_metadata=body.domain_metadata,
        knowledge_types=ktypes,
    )
    return [i.model_dump() for i in items]


@router.post("/assess")
async def assess_compatibility(
    body: AssessCompatibilityRequest,
    svc: KnowledgeTransferServiceDep,
) -> list[dict[str, object]]:
    """Assess compatibility of knowledge items with a target domain."""
    ktypes = None
    if body.knowledge_types is not None:
        ktypes = [KnowledgeType(t) for t in body.knowledge_types]

    items = await svc.extract_knowledge(
        domain_id=body.source_domain_id,
        domain_metadata=body.source_metadata,
        knowledge_types=ktypes,
    )
    assessed = await svc.assess_compatibility(items, body.target_metadata)
    return [i.model_dump() for i in assessed]


@router.post("/package")
async def create_knowledge_package(
    body: TransferKnowledgeRequest,
    svc: KnowledgeTransferServiceDep,
) -> dict[str, object]:
    """Create a knowledge package for transfer between domains."""
    ktypes = None
    if body.knowledge_types is not None:
        ktypes = [KnowledgeType(t) for t in body.knowledge_types]

    package = await svc.create_package(
        name=f"Transfer: {body.source_domain_id} -> {body.target_domain_id}",
        source_domain_id=body.source_domain_id,
        target_domain_id=body.target_domain_id,
        source_metadata=body.source_metadata,
        target_metadata=body.target_metadata,
        knowledge_types=ktypes,
    )
    return package.model_dump()


@router.get("/transfers")
async def list_transfers(
    svc: KnowledgeTransferServiceDep,
    status: str | None = None,
) -> list[dict[str, object]]:
    """List all knowledge transfers, optionally filtered by status."""
    ts = TransferStatus(status) if status is not None else None
    records = await svc.list_transfers(status=ts)
    return [r.model_dump() for r in records]


@router.get("/transfers/{transfer_id}")
async def get_transfer(
    transfer_id: UUID,
    svc: KnowledgeTransferServiceDep,
) -> dict[str, object]:
    """Retrieve a specific knowledge transfer by ID."""
    try:
        record = await svc.get_transfer(transfer_id)
        return record.model_dump()
    except TransferNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/transfers/{transfer_id}/rollback")
async def rollback_transfer(
    transfer_id: UUID,
    svc: KnowledgeTransferServiceDep,
) -> dict[str, object]:
    """Rollback a completed or failed knowledge transfer."""
    try:
        record = await svc.rollback_transfer(transfer_id)
        return record.model_dump()
    except TransferNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/recommendations")
async def recommend_transfers(
    body: RecommendTransfersRequest,
    svc: KnowledgeTransferServiceDep,
) -> list[dict[str, object]]:
    """Recommend knowledge transfers for a domain."""
    recommendations = await svc.recommend_transfers(
        domain_id=body.domain_id,
        all_domain_metadata=body.all_domain_metadata,
    )
    return recommendations


@router.get("/packages")
async def list_packages(
    svc: KnowledgeTransferServiceDep,
) -> list[dict[str, object]]:
    """List all knowledge packages."""
    packages = await svc.list_packages()
    return [p.model_dump() for p in packages]


@router.get("/packages/{package_id}")
async def get_package(
    package_id: UUID,
    svc: KnowledgeTransferServiceDep,
) -> dict[str, object]:
    """Retrieve a specific knowledge package by ID."""
    try:
        package = await svc.get_package(package_id)
        return package.model_dump()
    except KnowledgeTransferError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/items")
async def list_knowledge_items(
    svc: KnowledgeTransferServiceDep,
    source_domain_id: str | None = None,
    knowledge_type: str | None = None,
) -> list[dict[str, object]]:
    """List knowledge items, optionally filtered by source domain or type."""
    kt = KnowledgeType(knowledge_type) if knowledge_type is not None else None
    items = await svc.list_knowledge_items(
        source_domain_id=source_domain_id,
        knowledge_type=kt,
    )
    return [i.model_dump() for i in items]
