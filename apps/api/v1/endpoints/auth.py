"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.v1.schemas import (
    APIResponse,
    UserCreate,
    UserLogin,
    Token,
    ApiKeyCreate,
    ApiKeyResponse,
)
from packages.db.session import get_session

router = APIRouter()


@router.post("/register", response_model=APIResponse)
async def register(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    """Register a new user."""
    # TODO: Implement user registration
    # 1. Hash password
    # 2. Create user in database
    # 3. Send verification email
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Registration not yet implemented",
    )


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    """Login and get access token."""
    # TODO: Implement login
    # 1. Verify credentials
    # 2. Generate JWT
    # 3. Return token
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Login not yet implemented",
    )


@router.post("/api-keys", response_model=APIResponse)
async def create_api_key(
    key_data: ApiKeyCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new API key."""
    # TODO: Implement API key creation
    # 1. Generate key
    # 2. Hash and store
    # 3. Return key (only this once)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="API key creation not yet implemented",
    )


@router.get("/api-keys", response_model=APIResponse)
async def list_api_keys(
    session: AsyncSession = Depends(get_session),
):
    """List user's API keys."""
    # TODO: Implement API key listing
    return APIResponse(data=[])


@router.delete("/api-keys/{key_id}", response_model=APIResponse)
async def revoke_api_key(
    key_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Revoke an API key."""
    # TODO: Implement API key revocation
    return APIResponse(data={"success": True})
