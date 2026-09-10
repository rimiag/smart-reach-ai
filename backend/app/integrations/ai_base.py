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


def get_ai_client(preferred: Optional[str] = None) -> LLMClient:
    """
    Return a configured AI client.

    Args:
        preferred: ``anthropic``, ``openai``, ``gemini``, or None/``auto`` to
            pick the first configured provider (anthropic → openai → gemini).

    Raises:
        AIProviderError: If no provider is configured.
    """
    from app.core.config import settings
    from app.integrations.anthropic_client import AnthropicClient
    from app.integrations.gemini_client import GeminiClient
    from app.integrations.openai_client import OpenAIClient

    clients = {
        "anthropic": AnthropicClient,
        "openai": OpenAIClient,
        "gemini": GeminiClient,
    }

    choice = (preferred or settings.ai_provider or "auto").lower()

    if choice != "auto":
        client_cls = clients.get(choice)
        if client_cls is None:
            raise AIProviderError(f"Unknown AI provider: {choice}")
        client = client_cls()
        if not client.is_configured:
            raise AIProviderError(
                f"AI provider '{choice}' is selected but not configured (missing API key)"
            )
        return client

    for name in ("anthropic", "openai", "gemini"):
        client = clients[name]()
        if client.is_configured:
            logger.info("Using AI provider: %s", name)
            return client

    raise AIProviderError(
        "No AI provider configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, "
        "or GEMINI_API_KEY (free: aistudio.google.com/apikey)."
    )
