"""Job to ingest filings for a company."""

import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from apps.workers.config import settings
from packages.db.models import Company, Filing
from packages.edgar import EdgarClient

logger = logging.getLogger(__name__)


async def ingest_company_filings(cik: str, forms: list[str] = None):
    """
    Ingest filings for a specific company.

    Args:
        cik: Company CIK
        forms: List of form types to fetch (default: all)

    Returns:
        Dict with counts
    """
    if forms is None:
        forms = ["10-K", "10-Q", "8-K", "13F-HR"]

    logger.info(f"Starting filing ingestion for CIK {cik}")

    cik = cik.zfill(10)

    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with EdgarClient(
        contact_email=settings.SEC_CONTACT_EMAIL,
        user_agent=settings.SEC_USER_AGENT,
    ) as edgar:
        # Get company submissions
        submissions = await edgar.get_company_submissions(cik)

        # Get company from DB
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Company).where(Company.cik == cik)
            )
            company = result.scalar_one_or_none()

            if not company:
                logger.error(f"Company not found: {cik}")
                return {"error": "Company not found"}

            # Extract filings
            recent_filings = submissions.get("filings", {}).get("recent", {})

            if not recent_filings:
                logger.warning(f"No filings found for {cik}")
                return {"created": 0, "updated": 0}

            created = 0
            updated = 0

            # Process each filing
            accession_numbers = recent_filings.get("accessionNumber", [])
            filing_dates = recent_filings.get("filingDate", [])
            form_types = recent_filings.get("form", [])
            primary_docs = recent_filings.get("primaryDocument", [])

            for i in range(len(accession_numbers)):
                accession = accession_numbers[i]
                form_type = form_types[i]

                # Filter by form type
                if forms and form_type not in forms:
                    continue

                # Check if exists
                result = await session.execute(
                    select(Filing).where(Filing.accession_number == accession)
                )
                filing = result.scalar_one_or_none()

                filing_date = datetime.strptime(filing_dates[i], "%Y-%m-%d")

                if filing:
                    # Update existing
                    filing.form_type = form_type
                    filing.filing_date = filing_date
                    updated += 1
                else:
                    # Create new
                    primary_doc = primary_docs[i] if i < len(primary_docs) else ""

                    # Construct URLs
                    accession_no_dash = accession.replace("-", "")
                    url_base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dash}"

                    filing = Filing(
                        id=uuid4(),
                        company_id=company.id,
                        cik=cik,
                        accession_number=accession,
                        form_type=form_type,
                        filing_date=filing_date,
                        url_html=f"{url_base}/{primary_doc}" if primary_doc else None,
                        url_raw=f"{url_base}/{accession}.txt",
                        processing_status="pending",
                    )
                    session.add(filing)
                    created += 1

                # Commit in batches
                if (created + updated) % settings.INGESTION_BATCH_SIZE == 0:
                    await session.commit()
                    logger.info(f"Processed {created + updated} filings")

            # Final commit
            await session.commit()

            # Update company filing count
            company.filing_count = created + updated
            company.last_filing_date = filing_date
            await session.commit()

            logger.info(
                f"Filing ingestion complete for {cik}: "
                f"{created} created, {updated} updated"
            )

    await engine.dispose()

    return {"created": created, "updated": updated, "cik": cik}


def ingest_company_filings_sync(cik: str, forms: list[str] = None):
    """Sync wrapper for RQ worker."""
    return asyncio.run(ingest_company_filings(cik, forms))
