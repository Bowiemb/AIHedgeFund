"""Filings API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.v1.schemas import APIResponse, Filing, FilingDetail, PaginationMeta
from packages.db.models import Filing as FilingModel
from packages.db.session import get_session

router = APIRouter()


@router.get("", response_model=APIResponse)
async def list_filings(
    cik: Optional[str] = Query(None, description="Filter by CIK"),
    form: Optional[str] = Query(None, description="Filter by form type (10-K, 10-Q, etc.)"),
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="To date (YYYY-MM-DD)"),
    limit: int = Query(100, le=1000),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    session: AsyncSession = Depends(get_session),
):
    """List filings with filters."""
    query = select(FilingModel)

    # Apply filters
    if cik:
        query = query.where(FilingModel.cik == cik.zfill(10))
    if form:
        query = query.where(FilingModel.form_type == form)
    if from_date:
        query = query.where(FilingModel.filing_date >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.where(FilingModel.filing_date <= datetime.fromisoformat(to_date))

    # TODO: Implement cursor-based pagination
    query = query.order_by(FilingModel.filing_date.desc()).limit(limit)

    result = await session.execute(query)
    filings = result.scalars().all()

    return APIResponse(
        data=[Filing.from_orm(f) for f in filings],
        meta=PaginationMeta(
            count=len(filings),
            has_more=len(filings) == limit,
            next_cursor=None,  # TODO: Generate cursor
        ),
    )


@router.get("/{accession_number}", response_model=APIResponse)
async def get_filing(
    accession_number: str,
    session: AsyncSession = Depends(get_session),
):
    """Get filing details by accession number."""
    query = select(FilingModel).where(
        FilingModel.accession_number == accession_number
    )
    result = await session.execute(query)
    filing = result.scalar_one_or_none()

    if not filing:
        return APIResponse(
            data=None,
            meta={"error": "Filing not found"},
        )

    return APIResponse(data=Filing.from_orm(filing))
