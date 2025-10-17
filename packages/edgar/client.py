"""SEC EDGAR API client with rate limiting and caching."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class EdgarClient:
    """
    Async client for SEC EDGAR API.

    Features:
    - Rate limiting (10 req/sec per SEC guidelines)
    - Proper User-Agent header
    - Retry logic with exponential backoff
    - Response caching
    """

    BASE_URL = "https://data.sec.gov/"
    EDGAR_URL = "https://www.sec.gov/"

    def __init__(
        self,
        contact_email: str,
        user_agent: str = "AIHedgeFund/1.0",
        max_retries: int = 3,
        timeout: int = 30,
        rate_limit: int = 10,
    ):
        """
        Initialize EDGAR client.

        Args:
            contact_email: Contact email (required by SEC)
            user_agent: User agent string
            max_retries: Max retry attempts
            timeout: Request timeout in seconds
            rate_limit: Max requests per second
        """
        self.contact_email = contact_email
        self.user_agent = f"{user_agent} ({contact_email})"
        self.max_retries = max_retries
        self.timeout = ClientTimeout(total=timeout)
        self.rate_limiter = RateLimiter(max_requests=rate_limit, time_window=1.0)
        self._session: Optional[ClientSession] = None
        self._cache: Dict[str, Any] = {}

    async def _get_session(self) -> ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                timeout=self.timeout,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept-Encoding": "gzip, deflate",
                },
            )
        return self._session

    async def close(self) -> None:
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        url: str,
        method: str = "GET",
        use_cache: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with rate limiting and retries.

        Args:
            url: Full URL to request
            method: HTTP method
            use_cache: Whether to use cached response
            **kwargs: Additional arguments for aiohttp

        Returns:
            JSON response as dict
        """
        # Check cache
        cache_key = f"{method}:{url}"
        if use_cache and cache_key in self._cache:
            logger.debug(f"Cache hit for {url}")
            return self._cache[cache_key]

        session = await self._get_session()

        for attempt in range(self.max_retries):
            try:
                # Rate limit
                await self.rate_limiter.acquire()

                logger.debug(f"Request {attempt + 1}/{self.max_retries}: {method} {url}")

                async with session.request(method, url, **kwargs) as response:
                    # Handle rate limiting from server
                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited by server, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue

                    response.raise_for_status()

                    # Parse JSON response
                    data = await response.json()

                    # Cache successful response
                    if use_cache:
                        self._cache[cache_key] = data

                    return data

            except aiohttp.ClientError as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")

                if attempt == self.max_retries - 1:
                    raise

                # Exponential backoff
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        raise Exception(f"Failed to fetch {url} after {self.max_retries} attempts")

    async def get_company_tickers(self) -> List[Dict[str, Any]]:
        """
        Get company ticker list from SEC.

        Returns:
            List of companies with CIK, ticker, name
        """
        url = urljoin(self.BASE_URL, "files/company_tickers.json")
        response = await self._request(url)

        # Response format: {0: {cik_str, ticker, title}, 1: {...}, ...}
        companies = []
        for item in response.values():
            companies.append({
                "cik": str(item["cik_str"]).zfill(10),
                "ticker": item["ticker"],
                "name": item["title"],
            })

        logger.info(f"Fetched {len(companies)} companies")
        return companies

    async def get_company_submissions(self, cik: str) -> Dict[str, Any]:
        """
        Get company submission history.

        Args:
            cik: Company CIK (10 digits, zero-padded)

        Returns:
            Company metadata and recent filings
        """
        cik = cik.zfill(10)
        url = urljoin(self.BASE_URL, f"submissions/CIK{cik}.json")

        data = await self._request(url)
        logger.info(f"Fetched submissions for CIK {cik}: {data.get('name')}")

        return data

    async def get_company_facts(self, cik: str) -> Dict[str, Any]:
        """
        Get company XBRL facts.

        Args:
            cik: Company CIK (10 digits, zero-padded)

        Returns:
            XBRL facts by taxonomy
        """
        cik = cik.zfill(10)
        url = urljoin(self.BASE_URL, f"api/xbrl/companyfacts/CIK{cik}.json")

        data = await self._request(url)
        logger.info(f"Fetched XBRL facts for CIK {cik}")

        return data

    async def get_company_concept(
        self,
        cik: str,
        taxonomy: str,
        tag: str,
    ) -> Dict[str, Any]:
        """
        Get specific XBRL concept for a company.

        Args:
            cik: Company CIK
            taxonomy: XBRL taxonomy (e.g., 'us-gaap')
            tag: XBRL tag (e.g., 'AccountsPayable')

        Returns:
            Concept data with historical values
        """
        cik = cik.zfill(10)
        url = urljoin(
            self.BASE_URL,
            f"api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json"
        )

        data = await self._request(url)
        logger.info(f"Fetched concept {taxonomy}:{tag} for CIK {cik}")

        return data

    async def get_filing_document(
        self,
        accession_number: str,
        cik: str,
    ) -> str:
        """
        Get raw filing document (HTML/XML).

        Args:
            accession_number: Filing accession number
            cik: Company CIK

        Returns:
            Raw document text
        """
        cik = cik.zfill(10)
        # Remove dashes from accession number
        accession = accession_number.replace("-", "")

        url = urljoin(
            self.EDGAR_URL,
            f"Archives/edgar/data/{cik}/{accession}/{accession_number}.txt"
        )

        session = await self._get_session()
        await self.rate_limiter.acquire()

        async with session.get(url) as response:
            response.raise_for_status()
            text = await response.text()

        logger.info(f"Fetched filing document {accession_number}")
        return text

    async def get_submission_files(
        self,
        accession_number: str,
        cik: str,
    ) -> Dict[str, Any]:
        """
        Get list of files in a submission.

        Args:
            accession_number: Filing accession number
            cik: Company CIK

        Returns:
            Submission metadata and file list
        """
        cik = cik.zfill(10)
        accession = accession_number.replace("-", "")

        url = urljoin(
            self.BASE_URL,
            f"submissions/{accession}.json"
        )

        try:
            data = await self._request(url, use_cache=False)
            return data
        except Exception:
            # Fallback: construct from EDGAR structure
            logger.warning(f"Could not fetch submission files, using fallback")
            return {}

    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()
        logger.info("Cache cleared")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
