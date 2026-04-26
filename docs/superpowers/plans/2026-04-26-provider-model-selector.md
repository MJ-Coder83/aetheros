# Provider and Model Selector — Implementation Plan

**Date**: 2026-04-26
**Spec**: `docs/superpowers/specs/2026-04-26-provider-model-selector-design.md`
**Commit message**: `feat: implement comprehensive Provider and Model Selector in Settings`

---

## Execution Strategy

The work is decomposed into **5 independent parallel tracks** that can be delegated simultaneously, followed by a verification track. Each track has zero dependencies on other tracks during implementation.

---

## Track 1: Backend — Settings Package + ORM + Service + Routes

### Files to CREATE:
1. `packages/settings/__init__.py` — re-exports
2. `packages/settings/models.py` — Pydantic models (ProviderConfig, SaveSettingsRequest, SettingsResponse, ProviderListResponse, ProviderInfo, ConnectionTestResult)
3. `packages/settings/registry.py` — ProviderRegistry with 5 native providers (openai, anthropic, openrouter, nvidia, grok)
4. `packages/settings/service.py` — SettingsService (get_providers, get_settings, save_settings, test_connection, resolve_api_key, get_active_provider)

### Files to MODIFY:
5. `services/api/database.py` — add ProviderSettingsORM class
6. `services/api/dependencies.py` — add _settings_service_singleton, get_settings_service(), SettingsServiceDep
7. `services/api/main.py` — import settings route, add app.include_router(settings.router)
8. `services/api/routes/settings.py` (NEW) — 4 endpoints: GET /settings/providers, GET /settings, POST /settings, POST /settings/test-connection

### Exact Code Patterns:

**ProviderSettingsORM** (add after BranchMappingORM in database.py):
```python
class ProviderSettingsORM(Base):
    __tablename__ = "provider_settings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    provider_id: Mapped[str] = mapped_column(String(255), index=True)
    encrypted_api_key: Mapped[str] = mapped_column(Text)
    selected_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Dependency** (add after DbSessionDep in dependencies.py):
```python
_settings_service_singleton: SettingsService | None = None

def get_settings_service() -> SettingsService:
    global _settings_service_singleton
    if _settings_service_singleton is None:
        from packages.settings.registry import ProviderRegistry
        from packages.settings.service import SettingsService
        _settings_service_singleton = SettingsService(db=None, registry=ProviderRegistry())
    return _settings_service_singleton

SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
```

**Settings Router** pattern follows `health.py`:
```python
router = APIRouter(prefix="/settings", tags=["settings"])
```

**main.py** registration: add `from services.api.routes import settings` to the import block, add `app.include_router(settings.router)` after marketplace.

---

## Track 2: LLM Integration — Provider Factory + Unify Duplicate Protocol

### Files to CREATE:
1. `packages/llm/providers.py` — Concrete OpenAI-compatible provider classes: OpenAIProvider, AnthropicProvider, OpenRouterProvider, NVIDIAProvider, GrokProvider + `create_provider()` factory function

### Files to MODIFY:
2. `packages/llm/__init__.py` — add `from packages.llm.providers import create_provider` to exports, keep DSPyLLMProvider and HeuristicLLMProvider intact (backward compat)
3. `packages/prime/llm_planning.py` — replace duplicate `LLMProvider` Protocol import with `from packages.llm import LLMProvider`, update DSPyProvider to optionally accept SettingsService for key resolution

### Key Rules:
- Do NOT remove DSPyLLMProvider or HeuristicLLMProvider (backward compat)
- The `LLMProvider` Protocol in `packages/llm/__init__.py` has `async def generate(prompt: str, max_tokens: int) -> str` — keep this
- The `LLMProvider` Protocol in `packages/prime/llm_planning.py` has different methods (`provider_type`, `decompose`) — this is a SEPARATE protocol for planning. DO NOT merge these. They serve different purposes. The `llm_planning.py` LLMProvider is about goal decomposition, not text generation.
- `create_provider()` in `providers.py` should accept `(provider_id, api_key, model, base_url)` and return an instance that satisfies the `packages.llm.LLMProvider` protocol

---

## Track 3: Frontend — Types + API Client + React Query Hooks

### Files to MODIFY:
1. `apps/web/src/types/index.ts` — add ProviderInfo, Settings, ConnectionTestResult interfaces at the bottom
2. `apps/web/src/lib/api.ts` — add `settingsApi` namespace (getProviders, getSettings, saveSettings, testConnection)
3. `apps/web/src/hooks/use-api.ts` — add useSettings, useProviders, useSaveSettings, useTestConnection hooks

### Exact Types (add to end of types/index.ts):
```typescript
/* ── Provider & Settings ─────────────────────────────────────── */

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

### API Client (add to api.ts):
```typescript
/* ── Settings / Providers ──────────────────────────────────── */
import type { ProviderInfo, Settings, ConnectionTestResult } from "@/types";

export const settingsApi = {
  getProviders(): Promise<ProviderInfo[]> {
    return request("/api/settings/providers");
  },
  getSettings(): Promise<Settings> {
    return request("/api/settings");
  },
  saveSettings(data: Settings): Promise<Settings> {
    return request("/api/settings", { method: "POST", body: JSON.stringify(data) });
  },
  testConnection(providerId: string, apiKey: string): Promise<ConnectionTestResult> {
    return request("/api/settings/test-connection", {
      method: "POST",
      body: JSON.stringify({ provider_id: providerId, api_key: apiKey }),
    });
  },
};
```

### React Query Hooks (add to use-api.ts):
Follow existing patterns exactly: useQuery with queryKey, useMutation with qc.invalidateQueries + toast.success/error.

---

## Track 4: Frontend — Settings Page UI + Navbar Badge

### Files to CREATE:
1. `apps/web/src/app/settings/page.tsx` — Full settings page with provider sidebar + detail panel
2. `apps/web/src/components/provider-card.tsx` — Left sidebar provider card (icon, name, status badge, click to select)
3. `apps/web/src/components/provider-detail.tsx` — Right panel (API key input with mask/toggle, Test Connection button, model dropdown, Set Active button)
4. `apps/web/src/components/settings-footer.tsx` — Bottom bar (active provider/model display + Save button)

### Files to MODIFY:
5. `apps/web/src/components/navbar.tsx` — add provider/model badge pill between search and settings button

### UI Rules:
- Use existing shadcn/ui components: Button, Input, Separator
- Use lucide-react icons consistent with navbar patterns
- Use `cn()` from `@/lib/utils` for conditional classes
- Use framer-motion for animations (already in project)
- Follow the glass-morphism aesthetic: `glass-strong`, `bg-white/[0.02]`, `border-white/[0.06]`, `text-inkos-cyan`
- Add a `/settings` nav item to NAV_ITEMS with Settings icon
- Navbar badge: small pill between search trigger and settings button, reads from useSettings() hook

### Layout Wireframe (from spec):
```
┌─────────────────────────────────────────────────┐
│ Settings > LLM Providers                         │
├──────────────┬──────────────────────────────────┤
│ [OpenAI]     │ OpenAI Configuration              │
│ [Anthropic]  │ ─────────────────────────────     │
│ [OpenRouter] │ API Key: [••••••••sk-1234] 👁     │
│ [NVIDIA]     │ [Test Connection] → ✓ Connected   │
│ [Grok]       │                                   │
│              │ Default Model:                     │
│              │ [gpt-4o ▾]                         │
│              │                                    │
│              │ [Set as Active Provider]           │
├──────────────┴──────────────────────────────────┤
│ Active: GPT-4o (OpenAI)            [Save Settings]│
└─────────────────────────────────────────────────┘
```

---

## Track 5: Backend Tests

### Files to CREATE:
1. `tests/test_settings_routes.py` — 7 test functions per spec section 9

### Test Cases:
- `test_list_providers` — mock SettingsService, returns 5 providers with correct metadata
- `test_get_settings_default` — returns defaults from env when no DB settings
- `test_save_settings` — persists to DB, returns updated settings
- `test_test_connection_success` — mock provider API, returns success
- `test_test_connection_failure` — mock bad key, returns failure with message
- `test_active_provider_factory` — get_active_provider() returns correct instance
- `test_backward_compat_env_vars` — when no DB settings, env vars still work

---

## Track 6: Verification (after all tracks complete)

1. `ruff check` on all new Python files
2. Python typecheck (if configured)
3. `tsc --noEmit` in `apps/web/`
4. `npm run build` in `apps/web/`
5. `pytest tests/test_settings_routes.py` — all pass
6. Final commit: `feat: implement comprehensive Provider and Model Selector in Settings`

---

## Parallel Execution Map

```
Track 1 (Backend)  ─────────────────────┐
Track 2 (LLM)      ─────────────────────┤  → Track 6 (Verify)
Track 3 (Frontend Data) ────────────────┤
Track 4 (Frontend UI) ──────────────────┤
Track 5 (Tests)    ─────────────────────┘
```

All 5 tracks can run simultaneously. Track 6 runs after all complete.
