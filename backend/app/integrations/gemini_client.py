"""
Google Gemini AI Client

Free-tier-friendly provider that reuses the OpenAI SDK against Gemini's
OpenAI-compatible endpoint (https://generativelanguage.googleapis.com/v1beta/openai/).

Get a free API key at https://aistudio.google.com/apikey (no credit card
required; free tier allows ~1,500 requests/day on Flash models).
"""

import logging
from typing import Optional

from app.core.config import settings
from app.integrations.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

OPENAI_COMPAT_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai"

QUALIFICATION_MODEL = "gemini-3.6-flash"
EMAIL_MODEL = "gemini-3.6-flash"


class GeminiClient(OpenAIClient):
    """
    LLMClient implementation backed by Google Gemini via its OpenAI-compatible
    chat completions endpoint.
    """

    name = "gemini"
    default_model = settings.gemini_model or QUALIFICATION_MODEL
    default_email_model = settings.gemini_model or EMAIL_MODEL

    def __init__(self) -> None:
        super().__init__(api_key=settings.gemini_api_key, base_url=OPENAI_COMPAT_ENDPOINT)
