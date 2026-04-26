"""Pydantic v2 models for provider settings and model selection."""

from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    """Internal provider configuration (not exposed directly to API)."""

    provider_id: str
    display_name: str
    base_url: str
    icon: str | None = None
    models: list[str] = Field(default_factory=list)
    env_key: str = ""


class ProviderInfo(BaseModel):
    """API response model for a single provider's status."""

    provider_id: str
    display_name: str
    base_url: str
    icon: str | None
    models: list[str]
    has_key_configured: bool
    selected_model: str | None = None


class SettingsResponse(BaseModel):
    """Response for GET /settings — current active configuration."""

    active_provider_id: str
    active_model_id: str
    provider_keys: dict[str, str]
    default_models: dict[str, str]


class SaveSettingsRequest(BaseModel):
    """Request body for POST /settings — update provider configuration."""

    active_provider_id: str | None = None
    active_model_id: str | None = None
    provider_keys: dict[str, str] = Field(default_factory=dict)
    default_models: dict[str, str] = Field(default_factory=dict)


class ProviderListResponse(BaseModel):
    """Response for GET /settings/providers — all providers with status."""

    providers: list[ProviderInfo]


class ConnectionTestResult(BaseModel):
    """Response for POST /settings/test-connection — connectivity check."""

    provider_id: str
    success: bool
    message: str
    model_count: int | None = None
