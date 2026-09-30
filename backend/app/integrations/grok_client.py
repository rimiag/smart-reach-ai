"""
xAI Grok AI Client

Fallback provider that reuses the OpenAI SDK against xAI's OpenAI-compatible
endpoint (https://api.x.ai/v1).

Get an API key at https://console.x.ai (prepaid credits; xAI has no free
tier). Used automatically when the primary provider (e.g. Gemini) hits its
rate limit - see FailoverLLMClient in ai_base.py.
"""

import logging

from app.core.config import settings
from app.integrations.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

XAI_COMPAT_ENDPOINT = "https://api.x.ai/v1"

# Cheap/fast tier that suits qualification + email generation. Current model
# IDs: https://docs.x.ai/developers/models
QUALIFICATION_MODEL = "grok-4.3"
EMAIL_MODEL = "grok-4.3"


class GrokClient(OpenAIClient):
    """
    LLMClient implementation backed by xAI Grok via its OpenAI-compatible
    chat completions endpoint.
    """

    name = "grok"
    default_model = settings.grok_model or QUALIFICATION_MODEL
    default_email_model = settings.grok_model or EMAIL_MODEL

    def __init__(self) -> None:
        super().__init__(api_key=settings.grok_api_key, base_url=XAI_COMPAT_ENDPOINT)
