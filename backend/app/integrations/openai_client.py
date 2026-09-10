"""
OpenAI AI Client

Wraps the OpenAI chat completions API behind the LLMClient interface.

GeminiClient subclasses this to reuse the same surface against Google's
OpenAI-compatible endpoint.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.integrations.ai_base import AIProviderError, LLMClient, LLMResponse

logger = logging.getLogger(__name__)

# OpenAI models per task type (configurable via settings overrides).
QUALIFICATION_MODEL = "gpt-4o-mini"
EMAIL_MODEL = "gpt-4o"


class OpenAIClient(LLMClient):
    """LLMClient implementation backed by OpenAI chat completions."""

    name = "openai"
    default_model = QUALIFICATION_MODEL
    default_email_model = EMAIL_MODEL

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        # Overridable so GeminiClient can reuse this implementation against
        # Google's OpenAI-compatible endpoint.
        self._api_key = api_key if api_key is not None else settings.openai_api_key
        self._base_url = base_url
        self._client: Optional[object] = None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _sdk_client(self):
        """Lazily create the async SDK client."""
        if self._client is None:
            try:
                import openai

                kwargs = {"api_key": self._api_key, "timeout": settings.ai_qualification_timeout}
                if self._base_url:
                    kwargs["base_url"] = self._base_url
                self._client = openai.AsyncOpenAI(**kwargs)
            except Exception as exc:  # pragma: no cover - SDK import failure
                raise AIProviderError(f"openai SDK unavailable: {exc}") from exc
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
        """
        Return one chat completion.

        Uses ``max_tokens`` (supported by gpt-4o class models and by Gemini's
        OpenAI-compatible endpoint). If you switch the default models to an
        OpenAI reasoning model, switch this to ``max_completion_tokens``.
        """
        client = self._sdk_client()
        model_id = model or self.default_model

        try:
            response = await client.chat.completions.create(
                model=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as exc:
            logger.warning("OpenAI request failed (%s): %s", model_id, exc)
            raise AIProviderError(f"openai: {exc}") from exc

        choice = response.choices[0] if response.choices else None
        text = choice.message.content or "" if choice else ""
        usage = getattr(response, "usage", None)

        return LLMResponse(
            text=text,
            model=getattr(response, "model", model_id),
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )
