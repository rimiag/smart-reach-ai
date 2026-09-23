"""
User Schemas

Pydantic models for user-related requests and responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# -----------------------------------------------------------------------------
# Base User Schema
# -----------------------------------------------------------------------------
class UserBase(BaseModel):
    """Base user fields."""

    email: EmailStr
    name: Optional[str] = None


# -----------------------------------------------------------------------------
# Request Schemas
# -----------------------------------------------------------------------------
class UserCreate(UserBase):
    """Schema for user registration."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="User password (max 72 characters for bcrypt compatibility)",
    )


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str = Field(..., description="User password")


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserUpdatePassword(BaseModel):
    """Schema for password change."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")


# -----------------------------------------------------------------------------
# Response Schemas
# -----------------------------------------------------------------------------
class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    role: str
    is_active: bool
    # Default True keeps auth flows working against a users table that has not
    # received the verification columns yet (same pattern as the billing cols).
    is_verified: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None
    # Defaults keep token/auth flows working against a users table that has
    # not received the 006 billing columns yet.
    plan: str = "free"
    billing_status: str = "active"

    model_config = {"from_attributes": True}


class UserWithTokenResponse(UserResponse):
    """Schema for login response with tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str = Field(..., description="Refresh token")


class VerifyEmailRequest(BaseModel):
    """Schema for confirming an account from the email link."""

    token: str = Field(..., description="Token from the verification email link")


class ResendVerificationRequest(BaseModel):
    """Schema for re-sending the verification email."""

    email: EmailStr


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
