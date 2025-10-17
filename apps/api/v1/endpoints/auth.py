"""Authentication API endpoints."""

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    generate_api_key,
    get_current_user,
)
from apps.api.core.config import settings
from apps.api.v1.schemas import (
    APIResponse,
    UserCreate,
    UserLogin,
    Token,
    ApiKeyCreate,
    ApiKeyResponse,
)
from packages.db.models import User, ApiKey, Plan
from packages.db.session import get_session

router = APIRouter()


@router.post("/register", response_model=APIResponse)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user."""
    # Check if user exists
    result = await session.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Get free plan
    result = await session.execute(
        select(Plan).where(Plan.name == "free")
    )
    free_plan = result.scalar_one_or_none()

    # Create user
    user = User(
        id=uuid4(),
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        is_verified=False,
        role="user",
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return APIResponse(
        data={
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
            },
            "access_token": access_token,
            "token_type": "bearer",
        }
    )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    """Login and get access token."""
    # Get user
    result = await session.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await session.commit()

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_EXPIRY_HOURS * 3600,
    )


@router.post("/api-keys", response_model=APIResponse)
async def create_api_key(
    key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new API key."""
    # Generate key
    key, key_hash = generate_api_key()

    # Get key prefix for display
    key_prefix = key[:20] + "..."

    # Create API key record
    api_key = ApiKey(
        id=uuid4(),
        user_id=current_user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=key_data.name,
        is_active=True,
    )

    session.add(api_key)
    await session.commit()
    await session.refresh(api_key)

    return APIResponse(
        data=ApiKeyResponse(
            id=api_key.id,
            key=key,  # Only shown once!
            key_prefix=key_prefix,
            name=api_key.name,
            created_at=api_key.created_at,
        )
    )


@router.get("/api-keys", response_model=APIResponse)
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List user's API keys."""
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.user_id == current_user.id,
            ApiKey.is_active == True,
        )
    )
    api_keys = result.scalars().all()

    return APIResponse(
        data=[
            {
                "id": str(key.id),
                "key_prefix": key.key_prefix,
                "name": key.name,
                "created_at": key.created_at,
                "last_used_at": key.last_used_at,
                "usage_count": key.usage_count,
            }
            for key in api_keys
        ]
    )


@router.delete("/api-keys/{key_id}", response_model=APIResponse)
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Revoke an API key."""
    result = await session.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == current_user.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.is_active = False
    await session.commit()

    return APIResponse(data={"success": True})


@router.get("/me", response_model=APIResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user info."""
    return APIResponse(
        data={
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at,
        }
    )
