"""
FastAPI Dependencies

Reusable dependency functions for authentication, database sessions, etc.
"""

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.base import get_db
from app.models.user import User
from app.schemas.user import UserResponse

# -----------------------------------------------------------------------------
# Database Session Dependency
# -----------------------------------------------------------------------------
DBSession = Annotated[AsyncSession, Depends(get_db)]

# -----------------------------------------------------------------------------
# Security Dependencies
# -----------------------------------------------------------------------------
security = HTTPBearer()


async def get_current_user(
    db: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> UserResponse:
    """
    Get the current authenticated user from JWT token.

    Args:
        db: Database session
        credentials: HTTP Bearer credentials

    Returns:
        UserResponse: Current user data

    Raises:
        HTTPException: If token is invalid or user not found
    """
    print(f"DEBUG: credentials = {credentials}")
    if credentials is None:
        print("DEBUG: No credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        print(f"DEBUG: Token = {credentials.credentials[:20]}...")
        payload = decode_token(credentials.credentials)
        print(f"DEBUG: Payload = {payload}")
        user_id: int = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

    except JWTError as e:
        print(f"DEBUG: JWT Error = {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

    # Get user from database
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        print(f"DEBUG: User not found with id = {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    print(f"DEBUG: User found = {user.email}, is_active = {user.is_active}")
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return UserResponse.model_validate(user)


async def get_current_admin(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    """
    Get the current authenticated user and verify they are an admin.

    Args:
        current_user: Current authenticated user

    Returns:
        UserResponse: Admin user data

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


# -----------------------------------------------------------------------------
# Account hold (new signups wait for admin approval before consuming resources)
# -----------------------------------------------------------------------------
HOLD_MESSAGE = (
    "Your account is on hold. An administrator must approve your account "
    "before you can do this."
)


def _raise_if_held(user: UserResponse) -> None:
    if getattr(user, "account_status", "active") == "hold":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=HOLD_MESSAGE,
        )


async def require_active_account(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    """
    Block resource-consuming endpoints for held accounts.

    Use directly on endpoints whose HTTP verb alone doesn't reveal cost
    (e.g. GET /replies/check triggers an IMAP poll).
    """
    _raise_if_held(current_user)
    return current_user


async def hold_guard(
    request: Request,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> None:
    """
    Router-level guard: held accounts may GET (read-only browsing) but every
    write method is rejected. Applied via APIRouter(dependencies=...) so all
    endpoints in the router inherit the policy - including ones added later.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    _raise_if_held(current_user)


# -----------------------------------------------------------------------------
# Optional Auth (returns None if no token provided)
# -----------------------------------------------------------------------------
async def get_optional_user(
    db: DBSession,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
) -> Optional[UserResponse]:
    """
    Get current user if authenticated, otherwise return None.

    Useful for endpoints that work for both authenticated and anonymous users.
    """
    if credentials is None:
        return None

    try:
        return await get_current_user(db, credentials)
    except HTTPException:
        return None
