"""
Assistant API Endpoints

Phase 5: natural-language questions about the user's own campaigns, leads
and replies - answered from their database content via the AI provider.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.dependencies import get_current_user
from app.integrations.ai_base import AIProviderError
from app.schemas.user import UserResponse
from app.services.assistant_service import assistant_service

router = APIRouter()


class AskRequest(BaseModel):
    """A natural-language question about the user's data."""

    question: str = Field(..., min_length=3, max_length=500)


class AskResponse(BaseModel):
    """Assistant answer."""

    answer: str
    model: str


@router.post("/ask", response_model=AskResponse)
async def ask_assistant(
    payload: AskRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    """Answer a question grounded in the user's own campaign data."""
    try:
        result = await assistant_service.answer(db, current_user.id, payload.question.strip())
    except AIProviderError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return AskResponse(answer=result["answer"], model=result["model"])
