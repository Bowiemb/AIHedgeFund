"""API v1 schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Common
# ============================================================================


class APIResponse(BaseModel):
    """Standard API response wrapper."""

    data: Any
    meta: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    count: int
    next_cursor: Optional[str] = None
    has_more: bool = False


class ErrorResponse(BaseModel):
    """Error response."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# Companies
# ============================================================================


class CompanyBase(BaseModel):
    """Base company schema."""

    cik: str
    name: str
    tickers: List[str] = []
    exchanges: List[str] = []
    sic: Optional[str] = None
    sic_description: Optional[str] = None
    entity_type: Optional[str] = None


class Company(CompanyBase):
    """Company response schema."""

    id: UUID
    filing_count: int = 0
    last_filing_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CompanySearch(BaseModel):
    """Company search result."""

    cik: str
    name: str
    tickers: List[str]
    filing_count: int


# ============================================================================
# Filings
# ============================================================================


class FilingBase(BaseModel):
    """Base filing schema."""

    accession_number: str
    cik: str
    form_type: str
    filing_date: datetime
    period_end_date: Optional[datetime] = None
    fiscal_year: Optional[int] = None
    fiscal_quarter: Optional[str] = None


class Filing(FilingBase):
    """Filing response schema."""

    id: UUID
    company_id: UUID
    url_html: Optional[str] = None
    url_xbrl: Optional[str] = None
    has_xbrl: bool = False
    processing_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class FilingDetail(Filing):
    """Detailed filing with relationships."""

    company: Optional[Company] = None


class FilingQuery(BaseModel):
    """Filing query parameters."""

    cik: Optional[str] = None
    form: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    limit: int = Field(default=100, le=1000)
    cursor: Optional[str] = None


# ============================================================================
# Statements
# ============================================================================


class StatementBase(BaseModel):
    """Base statement schema."""

    statement_type: str
    line_item: str
    value: Decimal
    unit: str = "USD"
    currency: str = "USD"
    fiscal_year: int
    fiscal_quarter: Optional[str] = None
    period_end: datetime


class Statement(StatementBase):
    """Statement response schema."""

    id: UUID
    company_id: UUID
    filing_id: UUID
    line_item_std: Optional[str] = None

    class Config:
        from_attributes = True


class StatementQuery(BaseModel):
    """Statement query parameters."""

    cik: Optional[str] = None
    stmt: Optional[str] = None  # income, balance, cashflow
    fy: Optional[int] = None
    fq: Optional[str] = None
    asof: Optional[str] = None
    limit: int = Field(default=100, le=1000)


# ============================================================================
# 13F Holdings
# ============================================================================


class Holding13FBase(BaseModel):
    """Base 13F holding schema."""

    cusip: str
    issuer_name: str
    ticker: Optional[str] = None
    shares: Decimal
    market_value: Decimal
    put_call: str = "none"
    report_date: datetime


class Holding13F(Holding13FBase):
    """13F holding response schema."""

    id: UUID
    filing_id: UUID
    company_id: UUID

    class Config:
        from_attributes = True


class Holding13FQuery(BaseModel):
    """13F query parameters."""

    cik: Optional[str] = None
    cusip: Optional[str] = None
    ticker: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    limit: int = Field(default=100, le=1000)


# ============================================================================
# Signals
# ============================================================================


class SignalBase(BaseModel):
    """Base signal schema."""

    signal_type: str
    signal_name: str
    score: Optional[float] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = {}


class Signal(SignalBase):
    """Signal response schema."""

    id: UUID
    filing_id: UUID
    company_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class SignalQuery(BaseModel):
    """Signal query parameters."""

    cik: Optional[str] = None
    kind: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    limit: int = Field(default=100, le=1000)


# ============================================================================
# Usage
# ============================================================================


class UsageStats(BaseModel):
    """Usage statistics."""

    user_id: UUID
    period_start: datetime
    period_end: datetime
    total_requests: int
    total_rows: int
    plan_limit: int
    remaining_requests: int


# ============================================================================
# Auth
# ============================================================================


class UserCreate(BaseModel):
    """User creation schema."""

    email: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login schema."""

    email: str
    password: str


class Token(BaseModel):
    """Token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ApiKeyCreate(BaseModel):
    """API key creation schema."""

    name: Optional[str] = None


class ApiKeyResponse(BaseModel):
    """API key response (includes actual key once)."""

    id: UUID
    key: str  # Only returned on creation
    key_prefix: str
    name: Optional[str] = None
    created_at: datetime
