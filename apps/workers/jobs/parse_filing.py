"""Job to parse a filing and extract data."""

import asyncio
import logging
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from apps.workers.config import settings
from packages.db.models import Filing, Statement, Holding13F
from packages.edgar import EdgarClient
from packages.parsers import XBRLParser, Holdings13FParser
from packages.shared import S3Client

logger = logging.getLogger(__name__)


async def parse_filing(filing_id: str):
    """
    Parse a filing and extract structured data.

    Args:
        filing_id: Filing UUID

    Returns:
        Dict with parse results
    """
    logger.info(f"Starting parse for filing {filing_id}")

    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create clients
    s3 = S3Client(
        endpoint_url=settings.S3_ENDPOINT,
        access_key=settings.S3_ACCESS_KEY,
        secret_key=settings.S3_SECRET_KEY,
        bucket=settings.S3_BUCKET,
        region=settings.S3_REGION,
    )

    async with AsyncSessionLocal() as session:
        # Get filing
        result = await session.execute(
            select(Filing).where(Filing.id == filing_id)
        )
        filing = result.scalar_one_or_none()

        if not filing:
            logger.error(f"Filing not found: {filing_id}")
            return {"error": "Filing not found"}

        # Update status
        filing.processing_status = "processing"
        await session.commit()

        try:
            # Download raw filing if not already cached
            s3_key = f"filings/{filing.cik}/{filing.accession_number}.txt"

            raw_data = await s3.download_file(s3_key)

            if not raw_data:
                # Fetch from SEC
                async with EdgarClient(
                    contact_email=settings.SEC_CONTACT_EMAIL,
                    user_agent=settings.SEC_USER_AGENT,
                ) as edgar:
                    raw_text = await edgar.get_filing_document(
                        filing.accession_number,
                        filing.cik,
                    )
                    raw_data = raw_text.encode("utf-8")

                    # Upload to S3
                    await s3.upload_file(s3_key, raw_data, "text/plain")

                filing.s3_path = s3_key

            # Parse based on form type
            if filing.form_type in ["10-K", "10-Q"]:
                # Parse XBRL financials
                result = await parse_10k_10q(filing, session)

            elif filing.form_type in ["13F-HR"]:
                # Parse 13F holdings
                result = await parse_13f(filing, raw_data.decode("utf-8"), session)

            else:
                logger.info(f"No parser for form type {filing.form_type}")
                result = {"skipped": True}

            # Mark as completed
            filing.processing_status = "completed"
            filing.processed_at = datetime.utcnow()
            await session.commit()

            logger.info(f"Parse complete for filing {filing_id}")
            return result

        except Exception as e:
            logger.error(f"Parse failed for filing {filing_id}: {e}")
            filing.processing_status = "failed"
            filing.error_message = str(e)
            await session.commit()
            return {"error": str(e)}

    await engine.dispose()


async def parse_10k_10q(filing: Filing, session: AsyncSession):
    """Parse 10-K/10-Q using XBRL facts."""
    # Fetch company facts from SEC
    async with EdgarClient(
        contact_email=settings.SEC_CONTACT_EMAIL,
        user_agent=settings.SEC_USER_AGENT,
    ) as edgar:
        facts = await edgar.get_company_facts(filing.cik)

    # Parse XBRL
    parser = XBRLParser()
    statements_data = parser.parse_company_facts(facts)

    filing.has_xbrl = True

    # Insert statements
    total_inserted = 0

    for stmt_type, items in statements_data.items():
        for item in items:
            # Only insert if matches this filing
            if item.get("accession") == filing.accession_number:
                statement = Statement(
                    id=uuid4(),
                    company_id=filing.company_id,
                    filing_id=filing.id,
                    statement_type=stmt_type,
                    line_item=item["line_item"],
                    line_item_std=item.get("line_item_std"),
                    value=item["value"],
                    unit=item.get("unit", "USD"),
                    fiscal_year=item.get("fiscal_year"),
                    fiscal_quarter=item.get("fiscal_quarter"),
                    period_end=item.get("period_end"),
                    is_instant=item.get("is_instant", False),
                    source_path=item.get("line_item_std"),
                )
                session.add(statement)
                total_inserted += 1

    await session.commit()

    logger.info(f"Inserted {total_inserted} statement line items")

    return {"statements": total_inserted}


async def parse_13f(filing: Filing, raw_text: str, session: AsyncSession):
    """Parse 13F holdings from filing text."""
    parser = Holdings13FParser()
    holdings_data = parser.parse_13f_filing(raw_text)

    # Get report date from filing
    report_date = filing.period_end_date or filing.filing_date

    # Insert holdings
    for holding_data in holdings_data:
        holding = Holding13F(
            id=uuid4(),
            filing_id=filing.id,
            company_id=filing.company_id,
            cusip=holding_data.get("cusip"),
            issuer_name=holding_data.get("issuer_name"),
            ticker=holding_data.get("ticker"),
            shares=holding_data.get("shares", 0),
            market_value=holding_data.get("market_value", 0),
            put_call=holding_data.get("put_call", "none"),
            sole=holding_data.get("sole", 0),
            shared=holding_data.get("shared", 0),
            none_discretion=holding_data.get("none_discretion", 0),
            report_date=report_date,
        )
        session.add(holding)

    await session.commit()

    logger.info(f"Inserted {len(holdings_data)} holdings")

    return {"holdings": len(holdings_data)}


def parse_filing_sync(filing_id: str):
    """Sync wrapper for RQ worker."""
    return asyncio.run(parse_filing(filing_id))
