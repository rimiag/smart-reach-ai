"""
AI Provider Base

Common interface for LLM providers (Anthropic, OpenAI) used by the
qualification and email-generation agents. Providers translate a system+user
prompt pair into a single text completion; all prompting and parsing lives in
the agents.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Raised when an AI provider is unavailable, unconfigured or failing."""


class AIRateLimitError(AIProviderError):
    """Raised when a provider rejects a request due to its quota (HTTP 429)."""


@dataclass
class LLMResponse:
    """A single text completion plus usage metadata."""

    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMClient(ABC):
    """
    Abstract async LLM client.

    Concrete providers implement :meth:`complete`; agents only ever see this
    interface, which keeps them provider-agnostic and easy to test.
    """

    name: str = "base"
    # Task-specific model defaults (providers override with current model IDs;
    # settings can override further via ai_qualification_model etc. if added).
    default_model: str = ""  # bulk tasks (qualification)
    default_email_model: str = ""  # higher-quality generation (emails)

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Whether the provider has the credentials it needs."""

    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        model: str = "",
        temperature: float = 0.7,
    ) -> LLMResponse:
        """
        Return a single text completion for the prompt pair.

        Args:
            system: System prompt (task definition, rules, output format).
            user: User prompt (the lead/campaign data to process).
            max_tokens: Output token ceiling.
            model: Model override; empty string selects ``default_model``.
            temperature: Sampling temperature.
        """


class FailoverLLMClient(LLMClient):
    """
    Wraps an ordered chain of providers (primary first) and transparently
    retries a request against the next provider when the current one is rate
    limited (HTTP 429). Other errors are not retried - they fail loudly so
    misconfiguration never silently doubles spend.

    ``name`` reflects the provider that served the most recent request (or the
    primary before the first call), so per-provider usage tracking stays
    accurate.
    """

    def __init__(self, clients: list) -> None:
        if not clients:
            raise ValueError("FailoverLLMClient needs at least one client")
        self._clients = clients
        self._active: LLMClient = clients[0]

    @property
    def name(self) -> str:
        return self._active.name

    @property
    def is_configured(self) -> bool:
        return any(client.is_configured for client in self._clients)

    @property
    def default_model(self) -> str:
        return self._active.default_model

    @property
    def default_email_model(self) -> str:
        return self._active.default_email_model

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        model: str = "",
        temperature: float = 0.7,
    ) -> LLMResponse:
        last_error: Optional[AIRateLimitError] = None
        for client in self._clients:
            try:
                response = await client.complete(
                    system=system,
                    user=user,
                    max_tokens=max_tokens,
                    model=model,
                    temperature=temperature,
                )
                self._active = client
                return response
            except AIRateLimitError as exc:
                logger.warning(
                    "%s rate limited; failing over to next provider", client.name
                )
                last_error = exc
        raise last_error  # type: ignore[misc]


def get_ai_client(preferred: Optional[str] = None) -> LLMClient:
    """
    Return a configured AI client.

    Args:
        preferred: ``anthropic``, ``openai``, ``gemini``, ``grok``, or
            None/``auto``. The preferred provider becomes the head of the
            chain; every other configured provider follows as a rate-limit
            (429) fallback via :class:`FailoverLLMClient`, in priority order
            anthropic → openai → gemini → grok. So ``AI_PROVIDER=gemini`` +
            ``GROK_API_KEY`` yields gemini → grok failover. A single
            configured provider is returned directly.

    Raises:
        AIProviderError: If no provider is configured or the preferred
            provider is unknown/unconfigured.
    """
    from app.core.config import settings
    from app.integrations.anthropic_client import AnthropicClient
    from app.integrations.gemini_client import GeminiClient
    from app.integrations.grok_client import GrokClient
    from app.integrations.openai_client import OpenAIClient

    clients = {
        "anthropic": AnthropicClient,
        "openai": OpenAIClient,
        "gemini": GeminiClient,
        "grok": GrokClient,
    }

    choice = (preferred or settings.ai_provider or "auto").lower()

    auto_order = ("anthropic", "openai", "gemini", "grok")
    configured = [name for name in auto_order if clients[name]().is_configured]
    if not configured:
        raise AIProviderError(
            "No AI provider configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, "
            "GEMINI_API_KEY (free: aistudio.google.com/apikey), or GROK_API_KEY "
            "(paid: console.x.ai)."
        )

    if choice != "auto":
        client_cls = clients.get(choice)
        if client_cls is None:
            raise AIProviderError(f"Unknown AI provider: {choice}")
        if choice not in configured:
            raise AIProviderError(
                f"AI provider '{choice}' is selected but not configured (missing API key)"
            )
        # Preferred provider first, remaining configured ones as 429 fallbacks.
        configured = [choice] + [name for name in configured if name != choice]

    if len(configured) == 1:
        logger.info("Using AI provider: %s", configured[0])
        return clients[configured[0]]()

    logger.info("Using AI provider failover chain: %s", " → ".join(configured))
    return FailoverLLMClient([clients[name]() for name in configured])
