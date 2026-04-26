"""Tests for the Settings API routes — provider configuration and model selection.

Covers:
- GET  /settings/providers   — list all providers with status
- GET  /settings             — fetch current settings
- POST /settings             — save settings (provider, model, keys)
- POST /settings             — switch active provider
- POST /settings             — partial update (only model)
- POST /settings/test-connection — connectivity check (fake key)
- POST /settings/test-connection — invalid provider_id

Run with: pytest tests/test_settings_routes.py -v
"""

import pytest
from httpx import ASGITransport, AsyncClient

from services.api.main import app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def client() -> AsyncClient:
    """Create an async test client backed by the FastAPI ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_list_providers(client: AsyncClient) -> None:
    """GET /settings/providers returns list of providers."""
    response = await client.get("/settings/providers")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert len(data["providers"]) >= 5  # openai, anthropic, openrouter, nvidia, grok

    # Check first provider has required fields
    provider = data["providers"][0]
    assert "provider_id" in provider
    assert "display_name" in provider
    assert "base_url" in provider
    assert "models" in provider
    assert "has_key_configured" in provider


async def test_get_settings(client: AsyncClient) -> None:
    """GET /settings returns current settings."""
    response = await client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert "active_provider_id" in data
    assert "active_model_id" in data
    assert "provider_keys" in data
    assert "default_models" in data


async def test_save_settings(client: AsyncClient) -> None:
    """POST /settings saves settings and returns updated settings."""
    response = await client.post(
        "/settings",
        json={
            "active_provider_id": "openai",
            "active_model_id": "gpt-4o",
            "provider_keys": {"openai": "sk-test-key-12345"},
            "default_models": {"openai": "gpt-4o"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active_provider_id"] == "openai"
    assert data["active_model_id"] == "gpt-4o"


async def test_save_settings_switch_provider(client: AsyncClient) -> None:
    """POST /settings switches active provider."""
    # First set to openai
    await client.post(
        "/settings",
        json={
            "active_provider_id": "openai",
            "active_model_id": "gpt-4o",
        },
    )

    # Then switch to anthropic
    response = await client.post(
        "/settings",
        json={
            "active_provider_id": "anthropic",
            "active_model_id": "claude-sonnet-4-20250514",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active_provider_id"] == "anthropic"


async def test_save_settings_partial(client: AsyncClient) -> None:
    """POST /settings with partial data only updates provided fields."""
    # First set full settings
    await client.post(
        "/settings",
        json={
            "active_provider_id": "openai",
            "active_model_id": "gpt-4o",
        },
    )

    # Then update only the model
    response = await client.post(
        "/settings",
        json={
            "active_model_id": "gpt-4o-mini",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active_model_id"] == "gpt-4o-mini"


async def test_test_connection_success(client: AsyncClient) -> None:
    """POST /settings/test-connection tests provider connectivity.

    With a fake key the actual HTTP call will fail, so we just verify
    the endpoint returns the expected response shape.
    """
    response = await client.post(
        "/settings/test-connection",
        params={"provider_id": "openai", "api_key": "sk-fake-key-for-test"},
    )
    # Accept 200 regardless of success/failure — the endpoint always returns 200
    assert response.status_code == 200
    data = response.json()
    assert "provider_id" in data
    assert "success" in data
    assert "message" in data


async def test_test_connection_invalid_provider(client: AsyncClient) -> None:
    """POST /settings/test-connection with invalid provider_id returns error."""
    response = await client.post(
        "/settings/test-connection",
        params={"provider_id": "nonexistent_provider", "api_key": "fake-key"},
    )
    # The service returns 200 with success=False for unknown providers
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
