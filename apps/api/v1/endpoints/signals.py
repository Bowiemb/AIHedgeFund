"""Signals API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.v1.schemas import APIResponse, Signal, PaginationMeta
from packages.db.models import Signal as SignalModel, Company
from packages.db.session import get_session

router = APIRouter()


@router.get("", response_model=APIResponse)
async def list_signals(
    cik: Optional[str] = Query(None, description="Filter by CIK"),
    kind: Optional[str] = Query(None, description="Filter by signal type"),
    limit: int = Query(100, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """List derived signals with filters."""
    query = select(SignalModel)

    # Apply filters
    if cik:
        query = query.join(Company).where(Company.cik == cik.zfill(10))
    if kind:
        query = query.where(SignalModel.signal_type == kind)

    query = query.order_by(SignalModel.created_at.desc()).limit(limit)

    result = await session.execute(query)
    signals = result.scalars().all()

    return APIResponse(
        data=[Signal.from_orm(s) for s in signals],
        meta=PaginationMeta(
            count=len(signals),
            has_more=len(signals) == limit,
        ),
    )


@router.get("/{filing_id}", response_model=APIResponse)
async def get_filing_signals(
    filing_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get all signals for a specific filing."""
    query = select(SignalModel).where(SignalModel.filing_id == filing_id)
    result = await session.execute(query)
    signals = result.scalars().all()

    return APIResponse(
        data=[Signal.from_orm(s) for s in signals],
        meta={"count": len(signals)},
    )
