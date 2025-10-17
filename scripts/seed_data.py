#!/usr/bin/env python3
"""Seed database with sample data."""

import asyncio
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from packages.db.models import Company, Filing, Plan

DATABASE_URL = "postgresql+asyncpg://aihedge:aihedge123@localhost:5432/aihedge"


async def seed():
    """Seed database with sample data."""
    print("Seeding database...")

    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with AsyncSessionLocal() as session:
        # Create plans
        free_plan = Plan(
            id=uuid4(),
            name="free",
            display_name="Free",
            description="Basic access to SEC data API",
            price_monthly=0,
            requests_per_day=100,
            rows_per_response=100,
            is_active=True,
            features={"api_access": True, "support": False},
        )

        pro_plan = Plan(
            id=uuid4(),
            name="pro",
            display_name="Pro",
            description="Full API access with higher limits",
            price_monthly=99,
            requests_per_day=10000,
            rows_per_response=1000,
            is_active=True,
            features={"api_access": True, "support": True, "webhooks": True},
        )

        enterprise_plan = Plan(
            id=uuid4(),
            name="enterprise",
            display_name="Enterprise",
            description="Unlimited access with SLA",
            price_monthly=999,
            requests_per_day=1000000,
            rows_per_response=100000,
            is_active=True,
            features={
                "api_access": True,
                "support": True,
                "webhooks": True,
                "sla": True,
                "custom_data": True,
            },
        )

        session.add_all([free_plan, pro_plan, enterprise_plan])

        # Create sample company
        apple = Company(
            id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            tickers=["AAPL"],
            exchanges=["NASDAQ"],
            sic="3571",
            sic_description="Electronic Computers",
            entity_type="corporation",
            fiscal_year_end="0930",
        )

        session.add(apple)

        # Create sample filing
        filing = Filing(
            id=uuid4(),
            company_id=apple.id,
            cik=apple.cik,
            accession_number="0000320193-23-000077",
            form_type="10-K",
            filing_date=datetime(2023, 11, 3),
            period_end_date=datetime(2023, 9, 30),
            fiscal_year=2023,
            fiscal_quarter="FY",
            processing_status="pending",
        )

        session.add(filing)

        await session.commit()

        print("✓ Created 3 plans")
        print("✓ Created Apple Inc. sample company")
        print("✓ Created sample 10-K filing")
        print("\nSeed complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
