"""
Authentication API Endpoints

Handles user registration, login, token refresh, and user profile.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.db.base import get_db
from app.models.user import User
from app.schemas.user import (
    ResendVerificationRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    UserUpdatePassword,
    VerifyEmailRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

VERIFICATION_TOKEN_TTL_HOURS = 24
VERIFICATION_RESEND_COOLDOWN_SECONDS = 60


def _verification_email_body(user: User, token: str) -> str:
    """Plain-text welcome / email-confirmation message."""
    link = f"{settings.frontend_url}/verify?token={token}"
    name = user.name or user.email.split("@")[0]
    return (
        f"Hi {name},\n\n"
        "Welcome to ReachPulse by Smart Reach AI!\n\n"
        "Please confirm your email address to activate your account:\n\n"
        f"{link}\n\n"
        "This link expires in 24 hours. If you didn't create an account, "
        "you can safely ignore this email.\n\n"
        "- The ReachPulse Team"
    )


async def _send_verification_email(user: User, token: str) -> bool:
    """
    Send the verification email. Returns True when sent.

    Fail-open policy: when SMTP is not configured (laptop dev) or the send
    fails, the caller auto-verifies the user so signup never dead-ends.
    """
    from app.integrations.smtp_client import SMTPSendError, smtp_client

    if not smtp_client.is_configured:
        logger.warning(
            "SMTP not configured - auto-verifying %s without sending email", user.email
        )
        return False

    try:
        await smtp_client.send(
            from_addr=settings.smtp_from_email or settings.smtp_user,
            from_name="ReachPulse",
            to_addr=user.email,
            subject="Confirm your email - ReachPulse",
            body=_verification_email_body(user, token),
        )
        return True
    except SMTPSendError as exc:
        logger.error("Verification email to %s failed: %s", user.email, exc)
        return False


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.

    Creates a new user with email and password. Returns the user data.
    """
    try:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create new user - unverified until the email link is clicked, and on
        # hold until an admin releases them (read-only until then)
        token = secrets.token_urlsafe(32)
        new_user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            name=user_data.name,
            is_verified=False,
            account_status="hold",
            verification_token=token,
            verification_token_expires=datetime.now(timezone.utc)
            + timedelta(hours=VERIFICATION_TOKEN_TTL_HOURS),
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Send the confirmation email. If it cannot be delivered (SMTP not
        # configured, or the send failed), auto-verify so the account is
        # never unreachable - the user must be able to sign in.
        if not await _send_verification_email(new_user, token):
            new_user.is_verified = True
            new_user.verification_token = None
            new_user.verification_token_expires = None
            await db.commit()

        return UserResponse.model_validate(new_user)

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        print(f"Registration error: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}",
        )


@router.post("/login")
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return user data with tokens.

    Validates credentials and returns user profile with access and refresh tokens.
    """
    try:
        # Find user by email
        result = await db.execute(select(User).where(User.email == credentials.email))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        # Block unverified accounts until they confirm their email
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please check your inbox for the confirmation link.",
            )

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await db.commit()

        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # Build response with all fields
        user_data = UserResponse.model_validate(user).model_dump()
        user_data["access_token"] = access_token
        user_data["refresh_token"] = refresh_token
        user_data["token_type"] = "bearer"

        return user_data

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        print(f"Login error: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}",
        )


@router.post("/logout")
async def logout():
    """
    Logout user (invalidate token).

    In a stateless JWT setup, logout is handled client-side by removing the token.
    For true server-side logout, you would implement a token blacklist in Redis.
    """
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token_data: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token using refresh token.

    Validates the refresh token and issues a new access token.
    """
    from app.core.security import decode_token

    try:
        payload = decode_token(token_data.refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        )

    # Verify user exists and is active
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox for the confirmation link.",
        )

    # Create new tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Get current user profile.

    Returns the authenticated user's profile information.
    """
    from app.dependencies import get_current_user

    return await get_current_user(db, credentials)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db),
    credentials=Depends(security),
):
    """
    Update current user profile.

    Allows updating name and email. Email must be unique.
    """
    from app.dependencies import get_current_user

    # Get full user model
    user_response = await get_current_user(db, credentials)
    result = await db.execute(select(User).where(User.id == user_response.id))
    user = result.scalar_one_or_none()

    # Update name if provided
    if user_update.name is not None:
        user.name = user_update.name

    # Update email if provided and different
    if user_update.email and user_update.email != user.email:
        # Check if email is already taken
        result = await db.execute(select(User).where(User.email == user_update.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user.email = user_update.email

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.post("/verify")
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """
    Confirm an account via the token from the verification email.

    Marks the account verified and clears the token. Invalid or expired
    tokens return 400 with a user-friendly message.
    """
    result = await db.execute(select(User).where(User.verification_token == payload.token))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification link.",
        )

    expires = user.verification_token_expires
    expired = expires is None or expires.replace(tzinfo=timezone.utc) < datetime.now(
        timezone.utc
    )
    if expired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification link has expired. Request a new email from the sign-in page.",
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    await db.commit()

    logger.info("Email verified for user %d", user.id)
    return {"message": "Email verified. You can now sign in."}


@router.post("/resend-verification")
async def resend_verification(
    payload: ResendVerificationRequest, db: AsyncSession = Depends(get_db)
):
    """
    Re-send the verification email.

    Always returns 200 - the response never reveals whether the address has
    an account. Throttled to one email per minute per address (a still-fresh
    token is reused as-is and no new email goes out inside the cooldown).
    """
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user and not user.is_verified:
        now = datetime.now(timezone.utc)
        expires = user.verification_token_expires
        minted_at = (
            expires.replace(tzinfo=timezone.utc) - timedelta(hours=VERIFICATION_TOKEN_TTL_HOURS)
            if expires is not None
            else None
        )

        if (
            not user.verification_token
            or minted_at is None
            or now - minted_at >= timedelta(seconds=VERIFICATION_RESEND_COOLDOWN_SECONDS)
        ):
            token = secrets.token_urlsafe(32)
            user.verification_token = token
            user.verification_token_expires = now + timedelta(
                hours=VERIFICATION_TOKEN_TTL_HOURS
            )
            await db.commit()
            await _send_verification_email(user, token)

    return {
        "message": "If that address needs verification, a new email has been sent."
    }
