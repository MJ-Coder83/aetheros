"""InkosAI LLM integration — pluggable language model provider.

Provides a unified interface for DSPy-based LLM calls across the system.
All LLM usage is gated behind the ``USE_REAL_LLM`` configuration flag.
When disabled, the system falls back to heuristic/rule-based behaviour.
"""

import os
from typing import Protocol

from packages.llm.providers import (
    AnthropicProvider,
    GrokProvider,
    NVIDIAProvider,
    OpenAIProvider,
    OpenRouterProvider,
    create_provider,
)


class LLMProvider(Protocol):
    """Protocol for LLM providers."""

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate text from a prompt."""
        ...


class DSPyLLMProvider:
    """DSPy-based LLM provider using the configured language model."""

    def __init__(self) -> None:
        self._model = os.getenv("DSPY_LM_MODEL", "openai/gpt-4o-mini")
        self._api_key = os.getenv("OPENAI_API_KEY")
        self._initialised = False

    def _init_dspy(self) -> None:
        if self._initialised:
            return
        try:
            import dspy

            if self._api_key:
                lm = dspy.LM(self._model, api_key=self._api_key)
            else:
                lm = dspy.LM(self._model)
            dspy.configure(lm=lm)
            self._initialised = True
        except Exception as exc:
            raise RuntimeError(f"Failed to initialise DSPy: {exc}") from exc

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate text using DSPy."""
        self._init_dspy()
        import dspy

        class GenerateText(dspy.Signature):  # type: ignore
            """Generate text based on a prompt."""

            prompt = dspy.InputField(desc="The input prompt")
            response = dspy.OutputField(desc="The generated response")

        predictor = dspy.Predict(GenerateText)
        result = predictor(prompt=prompt)
        return str(result.response)


class HeuristicLLMProvider:
    """Fallback provider that returns empty strings.

    Used when ``USE_REAL_LLM`` is false. Callers should check
    ``is_llm_enabled()`` and provide heuristic fallbacks.
    """

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        return ""


def is_llm_enabled() -> bool:
    """Check whether real LLM integration is enabled."""
    return os.getenv("USE_REAL_LLM", "false").lower() in ("true", "1", "yes")


def get_llm_provider() -> LLMProvider:
    """Return the active LLM provider based on configuration."""
    if is_llm_enabled():
        return DSPyLLMProvider()
    return HeuristicLLMProvider()
