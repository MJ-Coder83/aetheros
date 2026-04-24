"""Domain Creation router."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from packages.prime.domain_creation import (
    BlueprintNotFoundError,
    BlueprintValidationError,
    CreationMode,
    DomainNotApprovedError,
    DuplicateDomainError,
)
from services.api.dependencies import DomainCreationServiceDep

router = APIRouter(prefix="/domains", tags=["domains"])


class CreateDomainRequest(BaseModel):
    """Schema for creating a domain from a description."""

    description: str
    domain_name: str | None = None
    creation_mode: CreationMode = CreationMode.HUMAN_GUIDED
    created_by: str = "prime"


class GenerateBlueprintRequest(BaseModel):
    """Schema for generating a domain blueprint."""

    description: str
    domain_name: str | None = None
    creation_mode: CreationMode = CreationMode.HUMAN_GUIDED
    created_by: str = "prime"


class RegisterDomainRequest(BaseModel):
    """Schema for registering a domain from an approved blueprint."""

    blueprint_id: UUID
    reviewer: str | None = None


@router.post("/create", status_code=201)
async def create_domain(
    body: CreateDomainRequest,
    svc: DomainCreationServiceDep,
) -> dict[str, object]:
    """Create a domain from a natural language description."""
    try:
        result = await svc.create_domain_from_description(
            description=body.description,
            domain_name=body.domain_name,
            creation_mode=body.creation_mode,
            created_by=body.created_by,
        )
        return result.model_dump()
    except BlueprintValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/blueprint", status_code=201)
async def generate_blueprint(
    body: GenerateBlueprintRequest,
    svc: DomainCreationServiceDep,
) -> dict[str, object]:
    """Generate a domain blueprint without submitting a proposal."""
    try:
        blueprint = await svc.generate_domain_blueprint(
            description=body.description,
            domain_name=body.domain_name,
            creation_mode=body.creation_mode,
            created_by=body.created_by,
        )
        return blueprint.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/register")
async def register_domain(
    body: RegisterDomainRequest,
    svc: DomainCreationServiceDep,
) -> dict[str, object]:
    """Register a domain after its proposal has been approved."""
    try:
        domain = await svc.register_domain(
            blueprint_id=body.blueprint_id,
            reviewer=body.reviewer,
        )
        return domain.model_dump()
    except BlueprintNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (DomainNotApprovedError, DuplicateDomainError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("")
async def list_domains(
    svc: DomainCreationServiceDep,
) -> list[dict[str, object]]:
    """List all registered domains."""
    domains = await svc.list_domains()
    return [d.model_dump() for d in domains]


@router.get("/{domain_id}")
async def get_domain(
    domain_id: str,
    svc: DomainCreationServiceDep,
) -> dict[str, object]:
    """Retrieve a single domain by ID."""
    domain = await svc.get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' not found")
    return domain.model_dump()


@router.get("/blueprints")
async def list_blueprints(
    svc: DomainCreationServiceDep,
) -> list[dict[str, object]]:
    """List all stored domain blueprints."""
    blueprints = await svc.list_blueprints()
    return [bp.model_dump() for bp in blueprints]


@router.get("/blueprints/{blueprint_id}")
async def get_blueprint(
    blueprint_id: UUID,
    svc: DomainCreationServiceDep,
) -> dict[str, object]:
    """Retrieve a specific blueprint by ID."""
    try:
        blueprint = await svc.get_blueprint(blueprint_id)
        return blueprint.model_dump()
    except BlueprintNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
