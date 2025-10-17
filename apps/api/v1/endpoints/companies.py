"""Companies API endpoints."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.v1.schemas import APIResponse, Company, CompanySearch, PaginationMeta
from packages.db.models import Company as CompanyModel
from packages.db.session import get_session

router = APIRouter()


@router.get("/search", response_model=APIResponse)
async def search_companies(
    q: str = Query(..., description="Search query (name, ticker, or CIK)"),
    limit: int = Query(100, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """Search companies by name, ticker, or CIK."""
    # Simple search - can be enhanced with full-text search
    query = select(CompanyModel).where(
        (CompanyModel.name.ilike(f"%{q}%"))
        | (CompanyModel.cik.ilike(f"%{q}%"))
    ).limit(limit)

    result = await session.execute(query)
    companies = result.scalars().all()

    return APIResponse(
        data=[
            CompanySearch(
                cik=c.cik,
                name=c.name,
                tickers=c.tickers or [],
                filing_count=c.filing_count,
            )
            for c in companies
        ],
        meta=PaginationMeta(
            count=len(companies),
            has_more=len(companies) == limit,
        ),
    )


@router.get("/{cik_or_ticker}", response_model=APIResponse)
async def get_company(
    cik_or_ticker: str,
    session: AsyncSession = Depends(get_session),
):
    """Get company details by CIK or ticker."""
    # Try CIK first
    query = select(CompanyModel).where(CompanyModel.cik == cik_or_ticker.zfill(10))
    result = await session.execute(query)
    company = result.scalar_one_or_none()

    # If not found, try ticker
    if not company:
        query = select(CompanyModel).where(
            CompanyModel.tickers.any(cik_or_ticker.upper())
        )
        result = await session.execute(query)
        company = result.scalar_one_or_none()

    if not company:
        return APIResponse(
            data=None,
            meta={"error": "Company not found"},
        )

    return APIResponse(data=Company.from_orm(company))


@router.get("/{cik}/filings", response_model=APIResponse)
async def get_company_filings(
    cik: str,
    form: str = Query(None, description="Filter by form type"),
    limit: int = Query(100, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """Get filings for a specific company."""
    from apps.api.v1.schemas import Filing
    from packages.db.models import Filing as FilingModel

    query = select(FilingModel).where(FilingModel.cik == cik.zfill(10))

    if form:
        query = query.where(FilingModel.form_type == form)

    query = query.order_by(FilingModel.filing_date.desc()).limit(limit)

    result = await session.execute(query)
    filings = result.scalars().all()

    return APIResponse(
        data=[Filing.from_orm(f) for f in filings],
        meta=PaginationMeta(
            count=len(filings),
            has_more=len(filings) == limit,
        ),
    )
