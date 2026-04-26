"""Settings router — provider configuration and model selection."""

from fastapi import APIRouter

from packages.settings.models import (
    ConnectionTestResult,
    ProviderListResponse,
    SaveSettingsRequest,
    SettingsResponse,
)
from services.api.dependencies import DbSessionDep, SettingsServiceDep

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    svc: SettingsServiceDep,
) -> ProviderListResponse:
    """List all available LLM providers with their status."""
    providers = svc.get_providers()
    return ProviderListResponse(providers=providers)


@router.get("", response_model=SettingsResponse)
async def get_settings(
    svc: SettingsServiceDep,
    db: DbSessionDep,
) -> SettingsResponse:
    """Get current settings (active provider, model, masked keys)."""
    return await svc.get_settings(db)


@router.post("", response_model=SettingsResponse)
async def save_settings(
    data: SaveSettingsRequest,
    svc: SettingsServiceDep,
    db: DbSessionDep,
) -> SettingsResponse:
    """Save settings (API keys, active provider, default models)."""
    return await svc.save_settings(data, db)


@router.post("/test-connection", response_model=ConnectionTestResult)
async def test_connection(
    provider_id: str,
    api_key: str,
    svc: SettingsServiceDep,
) -> ConnectionTestResult:
    """Test connectivity to a provider with the given API key."""
    return await svc.test_connection(provider_id, api_key)
