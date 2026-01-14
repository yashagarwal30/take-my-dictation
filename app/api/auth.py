"""
Authentication API endpoints for user registration and login.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import re
from app.db.database import get_db
from app.models.user import User
from app.models.email_verification import EmailVerification
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, Token,
    SendVerificationCode, VerifyEmailCode, VerificationResponse
)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    validate_password_strength
)
from app.core.dependencies import get_current_user
from app.services.email_service import email_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Simple in-memory rate limiting (production should use Redis)
_rate_limit_storage = {}


def check_rate_limit(identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
    """
    Simple rate limiting check.
    In production, use Redis or a proper rate limiting solution.
    """
    now = datetime.utcnow()
    if identifier not in _rate_limit_storage:
        _rate_limit_storage[identifier] = []

    # Clean old attempts
    _rate_limit_storage[identifier] = [
        attempt for attempt in _rate_limit_storage[identifier]
        if (now - attempt).total_seconds() < window_minutes * 60
    ]

    # Check if exceeded
    if len(_rate_limit_storage[identifier]) >= max_attempts:
        return False

    # Add new attempt
    _rate_limit_storage[identifier].append(now)
    return True


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_input(text: str, max_length: int = 255) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not text:
        return ""
    # Remove any null bytes
    text = text.replace('\x00', '')
    # Limit length
    return text[:max_length].strip()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account with enhanced security."""
    # Rate limiting by IP
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"register:{client_ip}", max_attempts=3, window_minutes=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later."
        )

    # Validate email format
    if not validate_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    # Sanitize inputs
    email = sanitize_input(user_data.email.lower(), 255)
    full_name = sanitize_input(user_data.full_name, 255) if user_data.full_name else None

    # Validate password strength
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Check if user already exists
    result = await db.execute(select(User).filter(User.email == email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Use same response time as successful registration to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    try:
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name,
            last_login_at=datetime.utcnow()
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        # Create access token
        access_token = create_access_token(
            data={"user_id": new_user.id, "email": new_user.email}
        )

        return Token(
            access_token=access_token,
            user=UserResponse.model_validate(new_user)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account. Please try again."
        )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password. Protected against brute force attacks."""
    # Rate limiting by IP and email
    client_ip = request.client.host if request.client else "unknown"
    email_lower = credentials.email.lower()

    # Check rate limit by IP
    if not check_rate_limit(f"login:ip:{client_ip}", max_attempts=10, window_minutes=15):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again in 15 minutes."
        )

    # Check rate limit by email
    if not check_rate_limit(f"login:email:{email_lower}", max_attempts=5, window_minutes=15):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts for this account. Please try again in 15 minutes."
        )

    # Validate email format
    if not validate_email(credentials.email):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Find user by email
    result = await db.execute(select(User).filter(User.email == email_lower))
    user = result.scalar_one_or_none()

    # Use constant-time comparison to prevent timing attacks
    if not user or not verify_password(credentials.password, user.hashed_password):
        # Same generic error message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )

    try:
        # Update last login
        user.last_login_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)

        # Create access token
        access_token = create_access_token(
            data={"user_id": user.id, "email": user.email}
        )

        return Token(
            access_token=access_token,
            user=UserResponse.model_validate(user)
        )
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again."
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return UserResponse.model_validate(current_user)


@router.post("/send-verification", response_model=VerificationResponse)
async def send_verification_code(
    data: SendVerificationCode,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Send a 6-digit verification code to the provided email.
    Rate limited to prevent spam.
    """
    # Rate limiting by IP
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"verify:ip:{client_ip}", max_attempts=5, window_minutes=15):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please try again later."
        )

    # Rate limiting by email
    email_lower = data.email.lower()
    if not check_rate_limit(f"verify:email:{email_lower}", max_attempts=3, window_minutes=15):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification codes sent to this email. Please try again later."
        )

    try:
        # Check if user already exists
        result = await db.execute(select(User).filter(User.email == email_lower))
        existing_user = result.scalar_one_or_none()

        if existing_user and existing_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already verified"
            )

        # Invalidate any existing verification codes for this email
        result = await db.execute(
            select(EmailVerification)
            .filter(EmailVerification.email == email_lower)
            .filter(EmailVerification.is_used == False)
        )
        existing_verifications = result.scalars().all()
        for verification in existing_verifications:
            verification.is_used = True

        # Create new verification code
        verification = EmailVerification.create_verification(email_lower)
        db.add(verification)
        await db.commit()
        await db.refresh(verification)

        # Send email
        email_sent = await email_service.send_verification_code(email_lower, verification.code)

        if not email_sent:
            # In development mode without SendGrid, still return success
            if email_service.is_configured():
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to send verification email. Please try again."
                )

        # Calculate expiration time
        expires_in = int((verification.expires_at - datetime.utcnow()).total_seconds())

        return VerificationResponse(
            success=True,
            message="Verification code sent successfully. Please check your email.",
            expires_in_seconds=max(0, expires_in)
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification code. Please try again."
        )


@router.post("/verify-email", response_model=VerificationResponse)
async def verify_email_code(
    data: VerifyEmailCode,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify the 6-digit code sent to the email.
    """
    # Rate limiting by IP
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"verify_check:ip:{client_ip}", max_attempts=10, window_minutes=15):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please try again later."
        )

    email_lower = data.email.lower()

    try:
        # Find the most recent verification code for this email
        result = await db.execute(
            select(EmailVerification)
            .filter(EmailVerification.email == email_lower)
            .filter(EmailVerification.code == data.code)
            .filter(EmailVerification.is_used == False)
            .order_by(EmailVerification.created_at.desc())
        )
        verification = result.scalar_one_or_none()

        if not verification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code"
            )

        # Check if code is valid
        if not verification.is_valid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired. Please request a new one."
            )

        # Verify the code
        if not verification.verify():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to verify code. Please try again."
            )

        # Update user if they exist
        result = await db.execute(select(User).filter(User.email == email_lower))
        user = result.scalar_one_or_none()
        if user:
            user.is_verified = True
            user.email_verified_at = datetime.utcnow()

        await db.commit()

        return VerificationResponse(
            success=True,
            message="Email verified successfully!"
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify code. Please try again."
        )


@router.post("/resend-verification", response_model=VerificationResponse)
async def resend_verification_code(
    data: SendVerificationCode,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend verification code to the email.
    Uses the same logic as send-verification but with stricter rate limiting.
    """
    # Rate limiting by IP
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"resend:ip:{client_ip}", max_attempts=3, window_minutes=30):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many resend attempts. Please try again later."
        )

    # Rate limiting by email (stricter than initial send)
    email_lower = data.email.lower()
    if not check_rate_limit(f"resend:email:{email_lower}", max_attempts=2, window_minutes=30):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification codes sent. Please check your spam folder or try again later."
        )

    # Reuse the send verification logic
    return await send_verification_code(data, request, db)


@router.post("/convert-trial", response_model=Token, status_code=status.HTTP_201_CREATED)
async def convert_trial_to_paid(
    user_data: UserCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Convert a trial user to a paid account.

    This endpoint allows trial users to upgrade to a full account by:
    1. Setting a password
    2. Verifying their email
    3. Maintaining their trial usage history

    The trial user's session token must be provided in the Authorization header.
    """
    # Verify this is a trial user
    if not current_user.is_trial_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for converting trial accounts. Use /auth/register for new accounts."
        )

    # Rate limiting by IP
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(f"convert:ip:{client_ip}", max_attempts=3, window_minutes=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many conversion attempts. Please try again later."
        )

    # Validate email format
    if not validate_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )

    # Sanitize inputs
    email = sanitize_input(user_data.email.lower(), 255)
    full_name = sanitize_input(user_data.full_name, 255) if user_data.full_name else None

    # Validate password strength
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Check if email is already registered by another user
    result = await db.execute(select(User).filter(
        User.email == email,
        User.id != current_user.id
    ))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered by another account"
        )

    try:
        # Convert trial user to paid user
        current_user.email = email
        current_user.hashed_password = get_password_hash(user_data.password)
        current_user.full_name = full_name
        current_user.is_trial_user = False
        # Keep trial_email and trial_minutes_used for history
        # User must verify email before full access
        current_user.is_verified = False
        current_user.last_login_at = datetime.utcnow()

        await db.commit()
        await db.refresh(current_user)

        # Create new access token with updated user info
        access_token = create_access_token(
            data={"user_id": current_user.id, "email": current_user.email}
        )

        return Token(
            access_token=access_token,
            user=UserResponse.model_validate(current_user)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to convert trial account. Please try again."
        )
