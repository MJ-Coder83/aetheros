# Provider and Model Selector — Design Spec

**Date**: 2026-04-26
**Status**: Approved
**Approach**: Database-backed settings with singleton service, env-var fallback

---

## 1. Overview

Implement a comprehensive Provider and Model Selector in InkosAI Settings, allowing users to configure multiple LLM providers (OpenAI, OpenRouter, NVIDIA, Anthropic, Grok), set API keys, select models, and have all agents respect the chosen provider+model. The system persists settings to PostgreSQL, falls back to `.env` keys, and exposes a clean Settings page in the frontend.

---

## 2. Backend — Data Models

### 2.1 Pydantic Models (`packages/settings/models.py`)

```python
class ProviderConfig(BaseModel):
    """Static definition of an LLM provider."""
    provider_id: str          # e.g. "openai", "anthropic"
    display_name: str         # e.g. "OpenAI", "Anthropic"
    base_url: str             # API base URL
    api_key_env_var: str      # env var to check for API key
    models: list[str]         # available model IDs
    icon: str | None          # lucide icon name for frontend

class SaveSettingsRequest(BaseModel):
    """Request body for POST /settings."""
    provider_keys: dict[str, str]    # provider_id → API key
    default_models: dict[str, str]   # provider_id → preferred model ID
    active_provider_id: str          # currently active provider
    active_model_id: str             # currently active model

class SettingsResponse(BaseModel):
    """Response body for GET /settings."""
    active_provider_id: str
    active_model_id: str
    provider_keys: dict[str, str]    # provider_id → masked key (last 4 chars)
    default_models: dict[str, str]   # provider_id → model ID

class ProviderListResponse(BaseModel):
    """Response body for GET /settings/providers."""
    providers: list[ProviderInfo]

class ProviderInfo(BaseModel):
    """A provider with its configuration status."""
    provider_id: str
    display_name: str
    base_url: str
    icon: str | None
    models: list[str]
    has_key_configured: bool         # True if key exists in DB or env
    selected_model: str | None       # user's chosen model for this provider

class ConnectionTestResult(BaseModel):
    """Result of testing a provider API key."""
    provider_id: str
    success: bool
    message: str
    model_count: int | None          # number of models returned (if applicable)
```

### 2.2 Provider Registry (`packages/settings/registry.py`)

Static list of `ProviderConfig` objects for the 5 native providers:

| provider_id | display_name | base_url | api_key_env_var | models |
|---|---|---|---|---|
| `openai` | OpenAI | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`, `o1`, `o1-mini`, `o3-mini` |
| `anthropic` | Anthropic | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514`, `claude-3-5-haiku-20241022`, `claude-opus-4-20250514` |
| `openrouter` | OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `openai/gpt-4o`, `anthropic/claude-sonnet-4`, `google/gemini-2.0-flash`, `meta-llama/llama-3.1-70b` |
| `nvidia` | NVIDIA | `https://integrate.api.nvidia.com/v1` | `NVIDIA_API_KEY` | `nvidia/llama-3.1-nemotron-70b`, `nvidia/mistral-large`, `nvidia/deepseek-r1` |
| `grok` | Grok (xAI) | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-3`, `grok-3-mini`, `grok-2` |

Adding a new provider requires only adding one `ProviderConfig` entry to this registry.

### 2.3 ORM Model (`services/api/database.py`)

```python
class ProviderSettingsORM(Base):
    """SQLAlchemy ORM mapping for the provider_settings table."""
    __tablename__ = "provider_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider_id: Mapped[str] = mapped_column(String(255), index=True)
    encrypted_api_key: Mapped[str] = mapped_column(Text)  # stored as-provided; encryption TBD
    selected_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

Key resolution order:
1. Database (if `ProviderSettingsORM` has a key for this provider)
2. Environment variable (from `ProviderConfig.api_key_env_var`)
3. `None` (not configured)

---

## 3. Backend — Service Layer

### 3.1 SettingsService (`packages/settings/service.py`)

```python
class SettingsService:
    def __init__(self, db: AsyncSession, registry: ProviderRegistry):
        self.db = db
        self.registry = registry

    async def get_providers(self) -> ProviderListResponse:
        """Return all providers with their configuration status."""

    async def get_settings(self) -> SettingsResponse:
        """Return current active provider/model + saved keys/models."""

    async def save_settings(self, payload: SaveSettingsRequest) -> SettingsResponse:
        """Persist provider keys + model selections + active provider to DB."""

    async def test_connection(self, provider_id: str, api_key: str) -> ConnectionTestResult:
        """Validate an API key by making a minimal API call to the provider."""

    def resolve_api_key(self, provider_id: str) -> str | None:
        """Resolve API key: DB → env var → None."""

    def get_active_provider(self) -> LLMProvider | None:
        """Factory method: return the LLMProvider instance for the active provider/model."""
```

### 3.2 Dependency Injection (`services/api/dependencies.py`)

```python
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]

async def get_settings_service(db: DbDep) -> SettingsService:
    """FastAPI dependency that provides a SettingsService instance."""
    return SettingsService(db=db, registry=ProviderRegistry())
```

---

## 4. Backend — API Endpoints

### 4.1 Routes (`services/api/routes/settings.py`)

```python
router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("/providers")
async def list_providers(svc: SettingsServiceDep) -> ProviderListResponse:
    """Return all providers with available models and configuration status."""

@router.get("")
async def get_settings(svc: SettingsServiceDep) -> SettingsResponse:
    """Return current active provider/model and all saved configurations."""

@router.post("")
async def save_settings(body: SaveSettingsRequest, svc: SettingsServiceDep) -> SettingsResponse:
    """Save provider API keys, model selections, and active provider."""

@router.post("/test-connection")
async def test_connection(body: TestConnectionRequest, svc: SettingsServiceDep) -> ConnectionTestResult:
    """Test an API key by making a real call to the provider."""
```

### 4.2 Registration (`services/api/main.py`)

Add `from services.api.routes import settings` and `app.include_router(settings.router)`.

---

## 5. LLM Integration

### 5.1 Consolidate LLMProvider Protocol

Current state: `LLMProvider` protocol exists in both `packages/llm/__init__.py` and `packages/prime/llm_planning.py`.

Fix:
1. `packages/llm/__init__.py` remains the canonical location for the `LLMProvider` protocol
2. New file `packages/llm/providers.py` contains concrete implementations: `OpenAIProvider`, `AnthropicProvider`, `OpenRouterProvider`, `NVIDIAProvider`, `GrokProvider`
3. Each concrete provider accepts `(api_key: str, model: str, base_url: str)` and implements `async def generate(prompt: str, max_tokens: int) -> str`
4. `packages/prime/llm_planning.py` imports `LLMProvider` from `packages.llm` and removes its duplicate protocol
5. `DSPyProvider` in `llm_planning.py` is kept as a legacy adapter but updated to also use the factory

### 5.2 Provider Factory

```python
# packages/settings/service.py
def get_active_provider(self) -> LLMProvider | None:
    """Return the LLMProvider for the currently active provider+model."""
    settings = self.get_settings_sync()  # cached
    provider_config = self.registry.get(settings.active_provider_id)
    api_key = self.resolve_api_key(settings.active_provider_id)
    if not api_key:
        return None
    return create_provider(
        provider_id=settings.active_provider_id,
        api_key=api_key,
        model=settings.active_model_id,
        base_url=provider_config.base_url,
    )
```

All agents (Prime, swarms, canvas) call `settings_service.get_active_provider()` instead of constructing their own provider.

---

## 6. Frontend — Settings Page

### 6.1 New Route: `/settings`

Full page at `apps/web/src/app/settings/page.tsx`. The existing `settings-dialog.tsx` remains for API URL + refresh interval config (its current role). The new page handles provider configuration.

### 6.2 Layout

```
┌─────────────────────────────────────────────────┐
│  Settings  >  LLM Providers                      │
├──────────────┬──────────────────────────────────┤
│              │                                    │
│  [OpenAI]    │   OpenAI Configuration             │
│  [Anthropic] │   ─────────────────────────────   │
│  [OpenRouter]│   API Key: [••••••••sk-1234] 👁   │
│  [NVIDIA]    │   [Test Connection] → ✓ Connected │
│  [Grok]      │                                    │
│              │   Default Model:                   │
│              │   [gpt-4o              ▾]          │
│              │                                    │
│              │   [Set as Active Provider]         │
│              │                                    │
├──────────────┴──────────────────────────────────┤
│  Active: GPT-4o (OpenAI)    [Save Settings]      │
└─────────────────────────────────────────────────┘
```

### 6.3 Components

- **ProviderCard**: Left sidebar card with icon, name, status badge (configured/unconfigured/active), click to select
- **ProviderDetail**: Right panel with API key input (masked + show/hide toggle), Test Connection button, model dropdown, Set Active toggle
- **SettingsFooter**: Bottom bar showing active provider/model + Save button

### 6.4 TypeScript Types (added to `apps/web/src/types/index.ts`)

```typescript
export interface ProviderInfo {
  provider_id: string;
  display_name: string;
  base_url: string;
  icon: string | null;
  models: string[];
  has_key_configured: boolean;
  selected_model: string | null;
}

export interface Settings {
  active_provider_id: string;
  active_model_id: string;
  provider_keys: Record<string, string>;
  default_models: Record<string, string>;
}

export interface ConnectionTestResult {
  provider_id: string;
  success: boolean;
  message: string;
  model_count: number | null;
}
```

### 6.5 API Client (added to `apps/web/src/lib/api.ts`)

```typescript
export const settingsApi = {
  getProviders: () => request<ProviderInfo[]>("/settings/providers"),
  getSettings: () => request<Settings>("/settings"),
  saveSettings: (data: Settings) => request<Settings>("/settings", { method: "POST", body: JSON.stringify(data) }),
  testConnection: (providerId: string, apiKey: string) =>
    request<ConnectionTestResult>("/settings/test-connection", { method: "POST", body: JSON.stringify({ provider_id: providerId, api_key: apiKey }) }),
};
```

### 6.6 React Query Hooks (added to `apps/web/src/hooks/use-api.ts`)

```typescript
export function useSettings() { /* useQuery wrapping settingsApi.getSettings */ }
export function useProviders() { /* useQuery wrapping settingsApi.getProviders */ }
export function useSaveSettings() { /* useMutation wrapping settingsApi.saveSettings */ }
export function useTestConnection() { /* useMutation wrapping settingsApi.testConnection */ }
```

---

## 7. Navbar Status Indicator

Extend `apps/web/src/components/navbar.tsx` to show a provider/model badge next to the existing health status indicator:

- Reads from `useSettings()` hook
- Displays: `🟢 GPT-4o (OpenAI)` when configured, `⚫ No provider` when not
- Updates reactively when settings change
- Style: small pill badge with provider icon + model name

---

## 8. Test Connection Implementation

Each provider's test connection makes a lightweight API call:

| Provider | Test Call |
|---|---|
| OpenAI | `GET /models` with API key |
| Anthropic | `POST /messages` with minimal prompt (1 token) |
| OpenRouter | `GET /models` with API key |
| NVIDIA | `GET /models` with API key |
| Grok | `GET /models` with API key |

Returns `ConnectionTestResult` with success/failure + message.

---

## 9. Testing

### 9.1 Backend Tests (`tests/test_settings_routes.py`)

- `test_list_providers` — returns 5 providers with correct metadata
- `test_get_settings_default` — returns defaults from env when no DB settings
- `test_save_settings` — persists to DB, returns updated settings
- `test_test_connection_success` — mock provider API, returns success
- `test_test_connection_failure` — mock bad key, returns failure with message
- `test_active_provider_factory` — `get_active_provider()` returns correct instance
- `test_backward_compat_env_vars` — when no DB settings, env vars still work

### 9.2 Frontend Verification

- TypeScript compilation: `tsc --noEmit` passes
- Build: `npm run build` succeeds
- New types match API responses

### 9.3 Lint

- Python: `ruff check` on all new files
- TypeScript: `eslint` on all new files

---

## 10. Backward Compatibility

- Existing env vars (`OPENAI_API_KEY`, `DSPY_LM_MODEL`, `USE_REAL_LLM`) continue to work as defaults
- `DSPyLLMProvider` in `packages/llm/__init__.py` continues to function unchanged
- When no DB settings exist, the system reads from env vars (no behavior change)
- When DB settings exist, they take precedence over env vars
- The `settings-dialog.tsx` (API URL + refresh intervals) is untouched

---

## 11. Future Extensibility

Adding a new provider requires:
1. Add a `ProviderConfig` entry to `packages/settings/registry.py`
2. Add a concrete `LLMProvider` subclass to `packages/llm/providers.py` (if the API differs from OpenAI-compatible format)
3. No database migration needed (the `provider_settings` table is provider-agnostic)
4. No frontend changes needed (the provider list is driven by the API response)

---

## 12. Files Changed

### New Files
- `packages/settings/__init__.py`
- `packages/settings/models.py`
- `packages/settings/registry.py`
- `packages/settings/service.py`
- `packages/llm/providers.py`
- `services/api/routes/settings.py`
- `apps/web/src/app/settings/page.tsx`
- `apps/web/src/components/provider-card.tsx`
- `apps/web/src/components/provider-detail.tsx`
- `apps/web/src/components/settings-footer.tsx`
- `apps/web/src/components/provider-status-badge.tsx`
- `tests/test_settings_routes.py`

### Modified Files
- `services/api/database.py` — add `ProviderSettingsORM`
- `services/api/dependencies.py` — add `SettingsServiceDep`
- `services/api/main.py` — register settings router
- `services/api/routes/__init__.py` — export settings router
- `packages/llm/__init__.py` — export concrete providers
- `packages/prime/llm_planning.py` — import `LLMProvider` from `packages.llm`
- `apps/web/src/types/index.ts` — add `ProviderInfo`, `Settings`, `ConnectionTestResult`
- `apps/web/src/lib/api.ts` — add `settingsApi`
- `apps/web/src/hooks/use-api.ts` — add settings hooks
- `apps/web/src/components/navbar.tsx` — add provider/model badge
