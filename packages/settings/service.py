"""Settings service — provider configuration, key management, and connection testing."""

import os

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.settings.models import (
    ConnectionTestResult,
    ProviderConfig,
    ProviderInfo,
    SaveSettingsRequest,
    SettingsResponse,
)
from packages.settings.registry import ProviderRegistry
from services.api.database import ProviderSettingsORM


class SettingsService:
    """Manages provider settings, API keys, and active provider selection."""

    def __init__(self, db: AsyncSession | None, registry: ProviderRegistry) -> None:
        self._db = db
        self._registry = registry

    def get_providers(self) -> list[ProviderInfo]:
        """Return all providers with their current key-configured status."""
        result: list[ProviderInfo] = []
        for cfg in self._registry.get_all():
            key = self.resolve_api_key(cfg.provider_id)
            result.append(
                ProviderInfo(
                    provider_id=cfg.provider_id,
                    display_name=cfg.display_name,
                    base_url=cfg.base_url,
                    icon=cfg.icon,
                    models=cfg.models,
                    has_key_configured=key is not None and len(key) > 0,
                    selected_model=None,
                )
            )
        return result

    async def get_settings(self, db: AsyncSession) -> SettingsResponse:
        """Return current settings with masked API keys."""
        active_provider_id = ""
        active_model_id = ""
        provider_keys: dict[str, str] = {}
        default_models: dict[str, str] = {}

        stmt = select(ProviderSettingsORM)
        rows = (await db.execute(stmt)).scalars().all()

        active_row: ProviderSettingsORM | None = None
        for row in rows:
            raw_key = row.encrypted_api_key or ""
            if raw_key:
                provider_keys[row.provider_id] = self._mask_key(raw_key)
            else:
                provider_keys[row.provider_id] = ""

            if row.selected_model:
                default_models[row.provider_id] = row.selected_model

            if row.is_active:
                active_row = row

        if active_row is not None:
            active_provider_id = active_row.provider_id
            active_model_id = active_row.selected_model or ""
        else:
            for cfg in self._registry.get_all():
                env_val = os.environ.get(cfg.env_key, "")
                if env_val:
                    active_provider_id = cfg.provider_id
                    active_model_id = default_models.get(cfg.provider_id, cfg.models[0] if cfg.models else "")
                    break

        return SettingsResponse(
            active_provider_id=active_provider_id,
            active_model_id=active_model_id,
            provider_keys=provider_keys,
            default_models=default_models,
        )

    async def save_settings(self, data: SaveSettingsRequest, db: AsyncSession) -> SettingsResponse:
        """Upsert provider settings rows and return updated settings."""
        if data.active_provider_id is not None:
            stmt = select(ProviderSettingsORM).where(ProviderSettingsORM.is_active.is_(True))
            active_rows = (await db.execute(stmt)).scalars().all()
            for row in active_rows:
                row.is_active = False

        for provider_id, api_key in data.provider_keys.items():
            stmt = select(ProviderSettingsORM).where(ProviderSettingsORM.provider_id == provider_id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                # Store as plain text for now — encryption hook for future
                existing.encrypted_api_key = api_key
            else:
                new_row = ProviderSettingsORM(
                    provider_id=provider_id,
                    encrypted_api_key=api_key,
                    is_active=(provider_id == data.active_provider_id),
                )
                db.add(new_row)

        for provider_id, model_id in data.default_models.items():
            stmt = select(ProviderSettingsORM).where(ProviderSettingsORM.provider_id == provider_id)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                existing.selected_model = model_id
            else:
                new_row = ProviderSettingsORM(
                    provider_id=provider_id,
                    encrypted_api_key="",
                    selected_model=model_id,
                    is_active=(provider_id == data.active_provider_id),
                )
                db.add(new_row)

        if data.active_provider_id is not None:
            stmt = select(ProviderSettingsORM).where(
                ProviderSettingsORM.provider_id == data.active_provider_id
            )
            active_row = (await db.execute(stmt)).scalar_one_or_none()
            if active_row is not None:
                active_row.is_active = True
                if data.active_model_id is not None:
                    active_row.selected_model = data.active_model_id
            else:
                new_row = ProviderSettingsORM(
                    provider_id=data.active_provider_id,
                    encrypted_api_key="",
                    selected_model=data.active_model_id or "",
                    is_active=True,
                )
                db.add(new_row)

        await db.flush()
        return await self.get_settings(db)

    async def test_connection(self, provider_id: str, api_key: str) -> ConnectionTestResult:
        """Test connectivity to a provider by calling its /models endpoint."""
        cfg = self._registry.get(provider_id)
        if cfg is None:
            return ConnectionTestResult(
                provider_id=provider_id,
                success=False,
                message=f"Unknown provider: {provider_id}",
            )

        url = f"{cfg.base_url.rstrip('/')}/models"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
                if resp.status_code == 200:
                    body = resp.json()
                    model_count = len(body.get("data", [])) if isinstance(body, dict) else None
                    return ConnectionTestResult(
                        provider_id=provider_id,
                        success=True,
                        message="Connection successful",
                        model_count=model_count,
                    )
                return ConnectionTestResult(
                    provider_id=provider_id,
                    success=False,
                    message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                )
        except httpx.HTTPError as exc:
            return ConnectionTestResult(
                provider_id=provider_id,
                success=False,
                message=f"Connection error: {exc}",
            )

    def resolve_api_key(self, provider_id: str) -> str | None:
        """Resolve API key for a provider — DB first, then env var fallback."""
        # DB lookup requires async, so for sync usage we only check env vars.
        # Callers with a DB session should query ProviderSettingsORM directly.
        cfg = self._registry.get(provider_id)
        if cfg is None:
            return None
        return os.environ.get(cfg.env_key) or None

    async def resolve_api_key_async(self, provider_id: str, db: AsyncSession) -> str | None:
        """Resolve API key — DB first, then env var fallback (async)."""
        stmt = select(ProviderSettingsORM).where(ProviderSettingsORM.provider_id == provider_id)
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is not None and row.encrypted_api_key:
            return row.encrypted_api_key
        cfg = self._registry.get(provider_id)
        if cfg is None:
            return None
        return os.environ.get(cfg.env_key) or None

    def get_active_provider(self) -> ProviderConfig | None:
        """Return the active provider — DB check requires async, so this uses env fallback."""
        for cfg in self._registry.get_all():
            if os.environ.get(cfg.env_key):
                return cfg
        return None

    @staticmethod
    def _mask_key(key: str) -> str:
        """Mask an API key, showing only the last 4 characters."""
        if len(key) <= 4:
            return "••••"
        return f"••••••{key[-4:]}"
