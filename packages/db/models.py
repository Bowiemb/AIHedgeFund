"""Database models for AIHedgeFund."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


# ============================================================================
# Companies & Filings
# ============================================================================


class Company(Base):
    """SEC registered company."""

    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    cik = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    tickers = Column(ARRAY(String), default=list)
    exchanges = Column(ARRAY(String), default=list)
    sic = Column(String(4), nullable=True)
    sic_description = Column(String(200), nullable=True)
    entity_type = Column(String(50), nullable=True)

    # Metadata
    fiscal_year_end = Column(String(4), nullable=True)
    state_of_incorporation = Column(String(2), nullable=True)
    phone = Column(String(20), nullable=True)

    # Stats
    filing_count = Column(Integer, default=0)
    last_filing_date = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    filings = relationship("Filing", back_populates="company", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_companies_cik", "cik"),)


class Filing(Base):
    """SEC filing."""

    __tablename__ = "filings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    # SEC identifiers
    accession_number = Column(String(20), unique=True, nullable=False, index=True)
    cik = Column(String(10), nullable=False, index=True)

    # Filing details
    form_type = Column(String(10), nullable=False, index=True)
    filing_date = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end_date = Column(DateTime(timezone=True), nullable=True, index=True)
    accepted_date = Column(DateTime(timezone=True), nullable=True)

    # Fiscal period
    fiscal_year = Column(Integer, nullable=True, index=True)
    fiscal_quarter = Column(String(2), nullable=True)

    # URLs
    url_html = Column(String(500), nullable=True)
    url_xbrl = Column(String(500), nullable=True)
    url_raw = Column(String(500), nullable=True)

    # Processing
    has_xbrl = Column(Boolean, default=False)
    s3_path = Column(String(500), nullable=True)
    processing_status = Column(
        Enum("pending", "processing", "completed", "failed", name="processing_status_enum"),
        default="pending",
        nullable=False,
    )
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    company = relationship("Company", back_populates="filings")
    statements = relationship("Statement", back_populates="filing", cascade="all, delete-orphan")
    holdings_13f = relationship("Holding13F", back_populates="filing", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="filing", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_filings_company_date", "company_id", "filing_date"),
        Index("idx_filings_form_date", "form_type", "filing_date"),
        Index("idx_filings_cik_form", "cik", "form_type"),
    )


# ============================================================================
# Financial Statements
# ============================================================================


class Statement(Base):
    """Normalized financial statement line item."""

    __tablename__ = "statements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    filing_id = Column(UUID(as_uuid=True), ForeignKey("filings.id"), nullable=False)

    # Statement details
    statement_type = Column(
        Enum("income", "balance", "cashflow", "equity", name="statement_type_enum"),
        nullable=False,
        index=True,
    )
    line_item = Column(String(500), nullable=False)
    line_item_std = Column(String(200), nullable=True, index=True)  # Standardized name

    # Value
    value = Column(Numeric(20, 2), nullable=False)
    unit = Column(String(20), default="USD")
    currency = Column(String(3), default="USD")

    # Period
    fiscal_year = Column(Integer, nullable=False, index=True)
    fiscal_quarter = Column(String(2), nullable=True)
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    is_instant = Column(Boolean, default=False)  # True for balance sheet, False for flows

    # Source
    source_path = Column(String(500), nullable=True)  # XBRL path or section reference

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    company = relationship("Company")
    filing = relationship("Filing", back_populates="statements")

    __table_args__ = (
        Index("idx_statements_company_period", "company_id", "period_end"),
        Index("idx_statements_filing_type", "filing_id", "statement_type"),
        UniqueConstraint(
            "filing_id", "statement_type", "line_item", "period_end",
            name="uq_statement_filing_item_period"
        ),
    )


# ============================================================================
# 13F Holdings
# ============================================================================


class Holding13F(Base):
    """13F institutional holdings."""

    __tablename__ = "holdings_13f"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    filing_id = Column(UUID(as_uuid=True), ForeignKey("filings.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    # Security details
    cusip = Column(String(9), nullable=False, index=True)
    issuer_name = Column(String(500), nullable=False)
    ticker = Column(String(10), nullable=True, index=True)

    # Position
    shares = Column(Numeric(20, 2), nullable=False)
    market_value = Column(Numeric(20, 2), nullable=False)  # USD thousands
    put_call = Column(Enum("put", "call", "both", "none", name="put_call_enum"), default="none")

    # Investment discretion
    sole = Column(Numeric(20, 2), default=0)
    shared = Column(Numeric(20, 2), default=0)
    none_discretion = Column(Numeric(20, 2), default=0)

    # Period
    report_date = Column(DateTime(timezone=True), nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    filing = relationship("Filing", back_populates="holdings_13f")
    company = relationship("Company")

    __table_args__ = (
        Index("idx_holdings_company_date", "company_id", "report_date"),
        Index("idx_holdings_cusip_date", "cusip", "report_date"),
        Index("idx_holdings_ticker_date", "ticker", "report_date"),
    )


# ============================================================================
# Signals
# ============================================================================


class Signal(Base):
    """Derived signals and insights."""

    __tablename__ = "signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    filing_id = Column(UUID(as_uuid=True), ForeignKey("filings.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    # Signal details
    signal_type = Column(String(50), nullable=False, index=True)
    signal_name = Column(String(200), nullable=False)
    score = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    filing = relationship("Filing", back_populates="signals")
    company = relationship("Company")

    __table_args__ = (
        Index("idx_signals_company_type", "company_id", "signal_type"),
        Index("idx_signals_type_score", "signal_type", "score"),
    )


# ============================================================================
# Users & Auth
# ============================================================================


class User(Base):
    """Platform user."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)

    # Profile
    full_name = Column(String(255), nullable=True)
    company_name = Column(String(255), nullable=True)

    # OAuth
    google_id = Column(String(255), nullable=True, unique=True)
    github_id = Column(String(255), nullable=True, unique=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(Enum("user", "admin", "internal", name="user_role_enum"), default="user")

    # Stripe
    stripe_customer_id = Column(String(255), nullable=True, unique=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")


class ApiKey(Base):
    """User API keys."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Key details
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)
    name = Column(String(100), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Usage
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")


# ============================================================================
# Billing
# ============================================================================


class Plan(Base):
    """Subscription plans."""

    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Plan details
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Pricing
    price_monthly = Column(Numeric(10, 2), nullable=False)
    stripe_price_id = Column(String(255), nullable=True)

    # Limits
    requests_per_day = Column(Integer, nullable=False)
    rows_per_response = Column(Integer, nullable=False)

    # Features
    features = Column(JSON, default=dict)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Subscription(Base):
    """User subscriptions."""

    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)

    # Stripe
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)

    # Status
    status = Column(
        Enum("active", "canceled", "past_due", "paused", name="subscription_status_enum"),
        default="active",
        nullable=False,
    )

    # Dates
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan")


class UsageEvent(Base):
    """API usage tracking."""

    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=True)

    # Request details
    endpoint = Column(String(200), nullable=False)
    method = Column(String(10), nullable=False)
    rows_returned = Column(Integer, default=0)

    # Response
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("idx_usage_user_date", "user_id", "created_at"),
        Index("idx_usage_key_date", "api_key_id", "created_at"),
    )


# ============================================================================
# Trading (OMS)
# ============================================================================


class TradingAccount(Base):
    """Trading account (IBKR)."""

    __tablename__ = "trading_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Account details
    broker = Column(String(50), default="ibkr")
    account_number = Column(String(50), nullable=False)
    account_type = Column(Enum("paper", "live", name="account_type_enum"), default="paper")

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)


class Position(Base):
    """Current positions."""

    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("trading_accounts.id"), nullable=False)

    # Security
    symbol = Column(String(20), nullable=False, index=True)
    quantity = Column(Numeric(20, 4), nullable=False)

    # Prices
    avg_cost = Column(Numeric(20, 4), nullable=False)
    market_price = Column(Numeric(20, 4), nullable=True)
    market_value = Column(Numeric(20, 2), nullable=True)
    unrealized_pnl = Column(Numeric(20, 2), nullable=True)

    # Timestamps
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint("account_id", "symbol", name="uq_position_account_symbol"),
    )


class Order(Base):
    """Trade orders."""

    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("trading_accounts.id"), nullable=False)

    # Order details
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum("buy", "sell", name="order_side_enum"), nullable=False)
    order_type = Column(
        Enum("market", "limit", "stop", "stop_limit", name="order_type_enum"),
        default="market"
    )
    quantity = Column(Numeric(20, 4), nullable=False)
    limit_price = Column(Numeric(20, 4), nullable=True)
    stop_price = Column(Numeric(20, 4), nullable=True)

    # Status
    status = Column(
        Enum("pending", "submitted", "filled", "partially_filled", "canceled", "rejected", name="order_status_enum"),
        default="pending",
        nullable=False,
    )
    filled_quantity = Column(Numeric(20, 4), default=0)
    avg_fill_price = Column(Numeric(20, 4), nullable=True)

    # Broker
    broker_order_id = Column(String(100), nullable=True, unique=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_orders_account_status", "account_id", "status"),
        Index("idx_orders_symbol_created", "symbol", "created_at"),
    )
