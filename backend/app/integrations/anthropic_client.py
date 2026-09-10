"""
Anthropic AI Client

Wraps the Anthropic SDK (messages API) behind the LLMClient interface.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.integrations.ai_base import AIProviderError, LLMClient, LLMResponse

logger = logging.getLogger(__name__)

# Which Anthropic model to use per task type (configurable via settings
# overrides: ai_qualification_model / anthropic_email_model).
QUALIFICATION_MODEL = "claude-haiku-4-5"  # bulk classification: fast + cheap
EMAIL_MODEL = "claude-sonnet-5"  # higher-quality writing at volume


class AnthropicClient(LLMClient):
    """LLMClient implementation backed by the Anthropic messages API."""

    name = "anthropic"
    default_model = settings.anthropic_model or QUALIFICATION_MODEL
    default_email_model = settings.anthropic_email_model or EMAIL_MODEL

    def __init__(self) -> None:
        self._client: Optional[object] = None

    @property
    def is_configured(self) -> bool:
        return bool(settings.anthropic_api_key)

    def _sdk_client(self):
        """Lazily create the async SDK client."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(
                    api_key=settings.anthropic_api_key,
                    timeout=settings.ai_qualification_timeout,
                )
            except Exception as exc:  # pragma: no cover - SDK import failure
                raise AIProviderError(f"anthropic SDK unavailable: {exc}") from exc
        return self._client

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        model: str = "",
        temperature: float = 0.7,
    ) -> LLMResponse:
        client = self._sdk_client()
        model_id = model or self.default_model

        try:
            response = await client.messages.create(
                model=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:
            # SDK typed exceptions (RateLimitError, APIStatusError, ...) are
            # normalized into AIProviderError for the agents.
            logger.warning("Anthropic request failed: %s", exc)
            raise AIProviderError(f"anthropic: {exc}") from exc

        text = "".join(block.text for block in response.content if block.type == "text")
        usage = getattr(response, "usage", None)

        return LLMResponse(
            text=text,
            model=getattr(response, "model", model_id),
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )
