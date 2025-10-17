"""Job to ingest company master list from SEC."""

import asyncio
import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from apps.workers.config import settings
from packages.db.models import Company
from packages.edgar import EdgarClient

logger = logging.getLogger(__name__)


async def ingest_companies():
    """
    Ingest all companies from SEC company tickers file.

    This job:
    1. Fetches company_tickers.json from SEC
    2. Upserts companies to database
    3. Returns count of companies processed
    """
    logger.info("Starting company ingestion")

    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create EDGAR client
    async with EdgarClient(
        contact_email=settings.SEC_CONTACT_EMAIL,
        user_agent=settings.SEC_USER_AGENT,
    ) as edgar:
        # Fetch companies
        companies_data = await edgar.get_company_tickers()

        logger.info(f"Fetched {len(companies_data)} companies from SEC")

        # Upsert to database
        async with AsyncSessionLocal() as session:
            created = 0
            updated = 0

            for company_data in companies_data:
                cik = company_data["cik"]

                # Check if exists
                result = await session.execute(
                    select(Company).where(Company.cik == cik)
                )
                company = result.scalar_one_or_none()

                if company:
                    # Update existing
                    company.name = company_data["name"]
                    if company_data["ticker"] not in (company.tickers or []):
                        company.tickers = (company.tickers or []) + [company_data["ticker"]]
                    updated += 1
                else:
                    # Create new
                    company = Company(
                        id=uuid4(),
                        cik=cik,
                        name=company_data["name"],
                        tickers=[company_data["ticker"]],
                    )
                    session.add(company)
                    created += 1

                # Commit in batches
                if (created + updated) % settings.INGESTION_BATCH_SIZE == 0:
                    await session.commit()
                    logger.info(f"Processed {created + updated} companies")

            # Final commit
            await session.commit()

            logger.info(
                f"Company ingestion complete: {created} created, {updated} updated"
            )

    await engine.dispose()

    return {"created": created, "updated": updated, "total": len(companies_data)}


# Sync wrapper for RQ
def ingest_companies_sync():
    """Sync wrapper for RQ worker."""
    return asyncio.run(ingest_companies())
