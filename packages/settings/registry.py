"""Provider registry — static catalogue of supported LLM providers."""

from packages.settings.models import ProviderConfig


class ProviderRegistry:
    """Registry of native LLM providers supported by InkosAI."""

    def __init__(self) -> None:
        self._providers: list[ProviderConfig] = [
            ProviderConfig(
                provider_id="openai",
                display_name="OpenAI",
                base_url="https://api.openai.com/v1",
                models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
                env_key="OPENAI_API_KEY",
                icon="openai",
            ),
            ProviderConfig(
                provider_id="anthropic",
                display_name="Anthropic",
                base_url="https://api.anthropic.com/v1",
                models=[
                    "claude-sonnet-4-20250514",
                    "claude-3-5-haiku-20241022",
                    "claude-3-opus-20240229",
                ],
                env_key="ANTHROPIC_API_KEY",
                icon="anthropic",
            ),
            ProviderConfig(
                provider_id="openrouter",
                display_name="OpenRouter",
                base_url="https://openrouter.ai/api/v1",
                models=[
                    "openai/gpt-4o",
                    "anthropic/claude-sonnet-4-20250514",
                    "google/gemini-pro",
                    "meta-llama/llama-3-70b-instruct",
                ],
                env_key="OPENROUTER_API_KEY",
                icon="openrouter",
            ),
            ProviderConfig(
                provider_id="nvidia",
                display_name="NVIDIA",
                base_url="https://integrate.api.nvidia.com/v1",
                models=[
                    "nvidia/llama-3.1-nemotron-70b-instruct",
                    "nvidia/mistral-large",
                    "nvidia/gemma-2-9b-it",
                ],
                env_key="NVIDIA_API_KEY",
                icon="nvidia",
            ),
            ProviderConfig(
                provider_id="grok",
                display_name="Grok",
                base_url="https://api.x.ai/v1",
                models=["grok-2", "grok-2-mini"],
                env_key="GROK_API_KEY",
                icon="grok",
            ),
        ]

    def get_all(self) -> list[ProviderConfig]:
        """Return all registered providers."""
        return list(self._providers)

    def get(self, provider_id: str) -> ProviderConfig | None:
        """Find a provider by its identifier."""
        for p in self._providers:
            if p.provider_id == provider_id:
                return p
        return None

    def get_model_list(self, provider_id: str) -> list[str]:
        """Return the model list for a given provider."""
        provider = self.get(provider_id)
        return provider.models if provider is not None else []
