"""13F Holdings API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.v1.schemas import APIResponse, Holding13F, PaginationMeta
from packages.db.models import Holding13F as Holding13FModel, Company
from packages.db.session import get_session

router = APIRouter()


@router.get("", response_model=APIResponse)
async def list_13f_holdings(
    cik: Optional[str] = Query(None, description="Institutional investor CIK"),
    cusip: Optional[str] = Query(None, description="Filter by CUSIP"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="To date (YYYY-MM-DD)"),
    limit: int = Query(100, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """List 13F institutional holdings with filters."""
    query = select(Holding13FModel)

    # Apply filters
    if cik:
        query = query.join(Company).where(Company.cik == cik.zfill(10))
    if cusip:
        query = query.where(Holding13FModel.cusip == cusip)
    if ticker:
        query = query.where(Holding13FModel.ticker == ticker.upper())
    if from_date:
        query = query.where(
            Holding13FModel.report_date >= datetime.fromisoformat(from_date)
        )
    if to_date:
        query = query.where(
            Holding13FModel.report_date <= datetime.fromisoformat(to_date)
        )

    query = query.order_by(Holding13FModel.report_date.desc()).limit(limit)

    result = await session.execute(query)
    holdings = result.scalars().all()

    return APIResponse(
        data=[Holding13F.from_orm(h) for h in holdings],
        meta=PaginationMeta(
            count=len(holdings),
            has_more=len(holdings) == limit,
        ),
    )


@router.get("/{filing_id}", response_model=APIResponse)
async def get_filing_13f_holdings(
    filing_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get all 13F holdings for a specific filing."""
    query = select(Holding13FModel).where(Holding13FModel.filing_id == filing_id)
    result = await session.execute(query)
    holdings = result.scalars().all()

    return APIResponse(
        data=[Holding13F.from_orm(h) for h in holdings],
        meta={"count": len(holdings)},
    )
