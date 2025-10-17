"""Authentication utilities."""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.config import settings
from packages.db.models import User, ApiKey
from packages.db.session import get_session

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Data to encode in token
        expires_delta: Token expiration delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode JWT access token.

    Args:
        token: JWT token

    Returns:
        Decoded token data or None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str]:
    """
    Generate API key.

    Returns:
        Tuple of (key, key_hash)
    """
    # Generate random key
    key = f"{settings.API_KEY_PREFIX}{secrets.token_urlsafe(32)}"

    # Hash key for storage
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    return key, key_hash


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Get current user from JWT token.

    Args:
        credentials: HTTP authorization credentials
        session: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_user_from_api_key(
    api_key: str,
    session: AsyncSession,
) -> Optional[User]:
    """
    Get user from API key.

    Args:
        api_key: API key string
        session: Database session

    Returns:
        User object or None
    """
    # Hash the provided key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Find API key
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == True,
        )
    )
    api_key_obj = result.scalar_one_or_none()

    if api_key_obj is None:
        return None

    # Check expiration
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
        return None

    # Update last used
    api_key_obj.last_used_at = datetime.utcnow()
    api_key_obj.usage_count += 1

    # Get user
    result = await session.execute(
        select(User).where(User.id == api_key_obj.user_id)
    )
    user = result.scalar_one_or_none()

    return user if user and user.is_active else None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = None,  # From header
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Get current user from JWT or API key.

    Args:
        credentials: JWT credentials (optional)
        x_api_key: API key from header (optional)
        session: Database session

    Returns:
        User object

    Raises:
        HTTPException: If authentication fails
    """
    # Try API key first
    if x_api_key:
        user = await get_current_user_from_api_key(x_api_key, session)
        if user:
            return user

    # Try JWT token
    if credentials:
        return await get_current_user_from_token(credentials, session)

    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Require admin role.

    Args:
        current_user: Current authenticated user

    Returns:
        User object

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user
