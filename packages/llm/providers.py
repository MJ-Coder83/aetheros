"""LLM provider implementations for the Provider & Model Selector."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from packages.llm import LLMProvider


class OpenAIProvider:
    """OpenAI API provider (gpt-4o, gpt-4o-mini, etc.)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise RuntimeError(
                    "openai package not installed. Run: pip install openai"
                ) from None
        return self._client

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""


class AnthropicProvider:
    """Anthropic API provider (Claude models)."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        base_url: str = "https://api.anthropic.com/v1",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. Run: pip install anthropic"
                ) from None
        return self._client

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        # Anthropic returns content blocks
        text_blocks = [block.text for block in response.content if block.type == "text"]
        return "".join(text_blocks)


class OpenRouterProvider:
    """OpenRouter API provider (aggregates multiple model providers)."""

    def __init__(
        self,
        api_key: str,
        model: str = "openai/gpt-4o",
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI

                # OpenRouter is OpenAI-compatible
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    default_headers={
                        "HTTP-Referer": "https://inkos.ai",
                        "X-Title": "InkosAI",
                    },
                )
            except ImportError:
                raise RuntimeError(
                    "openai package not installed. Run: pip install openai"
                ) from None
        return self._client

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""


class NVIDIAProvider:
    """NVIDIA API provider (NIM endpoints)."""

    def __init__(
        self,
        api_key: str,
        model: str = "nvidia/llama-3.1-nemotron-70b-instruct",
        base_url: str = "https://integrate.api.nvidia.com/v1",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI

                # NVIDIA NIM is OpenAI-compatible
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise RuntimeError(
                    "openai package not installed. Run: pip install openai"
                ) from None
        return self._client

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""


class GrokProvider:
    """Grok (xAI) API provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "grok-2",
        base_url: str = "https://api.x.ai/v1",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import OpenAI

                # xAI is OpenAI-compatible
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except ImportError:
                raise RuntimeError(
                    "openai package not installed. Run: pip install openai"
                ) from None
        return self._client

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        return content if content is not None else ""


_PROVIDER_CLASSES: dict[str, type] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "openrouter": OpenRouterProvider,
    "nvidia": NVIDIAProvider,
    "grok": GrokProvider,
}


def create_provider(
    provider_id: str,
    api_key: str,
    model: str,
    base_url: str | None = None,
) -> LLMProvider:
    """Factory: create an LLM provider instance by provider_id.

    Args:
        provider_id: One of 'openai', 'anthropic', 'openrouter', 'nvidia', 'grok'.
        api_key: The API key for the provider.
        model: The model identifier to use.
        base_url: Optional override for the provider's base URL.

    Returns:
        An instance satisfying the LLMProvider Protocol.

    Raises:
        ValueError: If provider_id is not recognized.
    """
    cls = _PROVIDER_CLASSES.get(provider_id)
    if cls is None:
        raise ValueError(
            f"Unknown provider: {provider_id}. Available: {list(_PROVIDER_CLASSES)}"
        )

    kwargs: dict[str, str] = {"api_key": api_key, "model": model}
    if base_url is not None:
        kwargs["base_url"] = base_url

    instance = cls(**kwargs)
    return instance  # type: ignore[no-any-return]
