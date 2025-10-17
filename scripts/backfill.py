#!/usr/bin/env python3
"""Backfill historical data from SEC EDGAR."""

import asyncio
import logging
from typing import List, Optional

import typer
from rq import Queue
from redis import Redis

from apps.workers.jobs import (
    ingest_companies_sync,
    ingest_company_filings_sync,
    parse_filing_sync,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer()

# S&P 500 sample CIKs (top 20 for testing)
SP500_SAMPLE_CIKS = [
    "0000320193",  # Apple
    "0001652044",  # Google/Alphabet
    "0001018724",  # Amazon
    "0001045810",  # NVIDIA
    "0000789019",  # Microsoft
    "0001318605",  # Tesla
    "0001067983",  # Berkshire Hathaway
    "0001326801",  # Meta/Facebook
    "0001551152",  # Visa
    "0001800227",  # AMD
    "0000886982",  # Intel
    "0001403161",  # Costco
    "0000789019",  # Netflix
    "0000063908",  # Adobe
    "0001559720",  # Salesforce
    "0001287894",  # Cisco
    "0001047469",  # Qualcomm
    "0000014272",  # Oracle
    "0000315213",  # Pfizer
    "0001551152",  # PayPal
]


@app.command()
def companies():
    """Ingest company master list."""
    logger.info("Starting company backfill")

    redis_conn = Redis(host="localhost", port=6379, db=0)
    queue = Queue(connection=redis_conn)

    # Enqueue job
    job = queue.enqueue(ingest_companies_sync, job_timeout="10m")

    logger.info(f"Job enqueued: {job.id}")
    logger.info("Waiting for completion...")

    # Wait for job
    while not job.is_finished and not job.is_failed:
        asyncio.sleep(1)

    if job.is_failed:
        logger.error(f"Job failed: {job.exc_info}")
    else:
        logger.info(f"Job completed: {job.result}")


@app.command()
def filings(
    ciks: Optional[List[str]] = typer.Option(None, help="CIKs to backfill"),
    sp500: bool = typer.Option(False, help="Backfill S&P 500 sample"),
    forms: Optional[List[str]] = typer.Option(
        ["10-K", "10-Q", "13F-HR"],
        help="Form types to fetch"
    ),
):
    """Backfill filings for companies."""
    if sp500:
        ciks = SP500_SAMPLE_CIKS
    elif not ciks:
        logger.error("Provide --ciks or --sp500")
        return

    logger.info(f"Starting filing backfill for {len(ciks)} companies")

    redis_conn = Redis(host="localhost", port=6379, db=0)
    queue = Queue(connection=redis_conn)

    # Enqueue jobs
    jobs = []
    for cik in ciks:
        job = queue.enqueue(
            ingest_company_filings_sync,
            cik,
            forms,
            job_timeout="30m",
        )
        jobs.append(job)
        logger.info(f"Enqueued filing ingestion for CIK {cik}: {job.id}")

    logger.info(f"Total jobs enqueued: {len(jobs)}")


@app.command()
def full(
    sp500: bool = typer.Option(True, help="Backfill S&P 500 sample"),
):
    """Full backfill: companies + filings."""
    logger.info("Starting full backfill")

    # Step 1: Ingest companies
    logger.info("Step 1: Ingesting companies...")
    companies()

    # Step 2: Ingest filings
    logger.info("Step 2: Ingesting filings...")
    filings(sp500=sp500)

    logger.info("Full backfill initiated. Monitor worker logs for progress.")


if __name__ == "__main__":
    app()
