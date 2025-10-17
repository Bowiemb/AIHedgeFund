"""Usage API endpoints."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.v1.schemas import APIResponse, UsageStats
from packages.db.models import UsageEvent, User
from packages.db.session import get_session

router = APIRouter()


@router.get("", response_model=APIResponse)
async def get_usage_stats(
    # TODO: Get user from auth token
    session: AsyncSession = Depends(get_session),
):
    """Get current user's usage statistics."""
    # TODO: Extract user from JWT/API key
    # For now, return mock data
    now = datetime.utcnow()
    period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = period_start + timedelta(days=1)

    # Mock stats
    stats = UsageStats(
        user_id="00000000-0000-0000-0000-000000000000",
        period_start=period_start,
        period_end=period_end,
        total_requests=45,
        total_rows=1250,
        plan_limit=100,
        remaining_requests=55,
    )

    return APIResponse(data=stats)
