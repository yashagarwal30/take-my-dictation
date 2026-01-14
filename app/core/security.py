"""
Security utilities for authentication and authorization.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
from app.core.config import settings

# Password hashing context with strong cost factor
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Strong cost factor for bcrypt
)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password policy
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets security requirements.

    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"

    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Password must not exceed {MAX_PASSWORD_LENGTH} characters"

    # Check for at least one number
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"

    # Check for at least one letter
    if not any(char.isalpha() for char in password):
        return False, "Password must contain at least one letter"

    return True, ""


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    Uses constant-time comparison to prevent timing attacks.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Prevent information leakage through exceptions
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt with strong cost factor.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with additional security claims.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add security claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # Issued at
        "jti": secrets.token_urlsafe(32),  # JWT ID for token revocation tracking
    })

    # Validate SECRET_KEY strength
    if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters long")

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT access token.
    """
    try:
        # Decode with validation
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={
                "verify_exp": True,  # Verify expiration
                "verify_iat": True,  # Verify issued at
                "verify_signature": True,  # Verify signature
            }
        )

        # Additional validation
        if "user_id" not in payload:
            return None

        return payload
    except JWTError:
        return None
    except Exception:
        # Catch any other exceptions to prevent information leakage
        return None


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    Used for password reset tokens, API keys, etc.
    """
    return secrets.token_urlsafe(length)
