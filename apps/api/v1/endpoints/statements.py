"""Statements API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.v1.schemas import APIResponse, Statement, PaginationMeta
from packages.db.models import Statement as StatementModel, Company
from packages.db.session import get_session

router = APIRouter()


@router.get("", response_model=APIResponse)
async def list_statements(
    cik: Optional[str] = Query(None, description="Filter by CIK"),
    stmt: Optional[str] = Query(
        None, description="Statement type (income, balance, cashflow)"
    ),
    fy: Optional[int] = Query(None, description="Fiscal year"),
    fq: Optional[str] = Query(None, description="Fiscal quarter (Q1, Q2, Q3, Q4)"),
    limit: int = Query(100, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """List financial statements with filters."""
    query = select(StatementModel)

    # Apply filters
    if cik:
        # Join with company to filter by CIK
        query = query.join(Company).where(Company.cik == cik.zfill(10))
    if stmt:
        query = query.where(StatementModel.statement_type == stmt)
    if fy:
        query = query.where(StatementModel.fiscal_year == fy)
    if fq:
        query = query.where(StatementModel.fiscal_quarter == fq)

    query = query.order_by(StatementModel.period_end.desc()).limit(limit)

    result = await session.execute(query)
    statements = result.scalars().all()

    return APIResponse(
        data=[Statement.from_orm(s) for s in statements],
        meta=PaginationMeta(
            count=len(statements),
            has_more=len(statements) == limit,
        ),
    )


@router.get("/{filing_id}", response_model=APIResponse)
async def get_filing_statements(
    filing_id: str,
    stmt: Optional[str] = Query(None, description="Filter by statement type"),
    session: AsyncSession = Depends(get_session),
):
    """Get all statements for a specific filing."""
    query = select(StatementModel).where(StatementModel.filing_id == filing_id)

    if stmt:
        query = query.where(StatementModel.statement_type == stmt)

    result = await session.execute(query)
    statements = result.scalars().all()

    return APIResponse(
        data=[Statement.from_orm(s) for s in statements],
        meta={"count": len(statements)},
    )
