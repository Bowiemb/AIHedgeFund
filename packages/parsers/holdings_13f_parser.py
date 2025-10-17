"""13F holdings parser for institutional positions."""

import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class Holdings13FParser:
    """
    Parser for 13F institutional holdings filings.

    Extracts:
    - CUSIP
    - Issuer name
    - Position size
    - Market value
    - Put/call indicator
    """

    def __init__(self):
        """Initialize 13F parser."""
        pass

    def parse_13f_filing(self, filing_text: str) -> List[Dict[str, Any]]:
        """
        Parse 13F filing text to extract holdings.

        Args:
            filing_text: Raw filing text (HTML/XML)

        Returns:
            List of holdings
        """
        holdings = []

        # Try XML parsing first (newer filings)
        try:
            holdings = self._parse_xml(filing_text)
            if holdings:
                logger.info(f"Parsed {len(holdings)} holdings from XML")
                return holdings
        except Exception as e:
            logger.debug(f"XML parsing failed: {e}")

        # Fallback to HTML/table parsing
        try:
            holdings = self._parse_html_table(filing_text)
            if holdings:
                logger.info(f"Parsed {len(holdings)} holdings from HTML")
                return holdings
        except Exception as e:
            logger.debug(f"HTML parsing failed: {e}")

        logger.warning("Could not parse 13F filing")
        return []

    def _parse_xml(self, filing_text: str) -> List[Dict[str, Any]]:
        """
        Parse 13F XML format.

        Args:
            filing_text: XML text

        Returns:
            List of holdings
        """
        holdings = []

        # Extract XML document
        xml_start = filing_text.find("<?xml")
        if xml_start == -1:
            return []

        xml_text = filing_text[xml_start:]

        # Parse with ElementTree
        root = ET.fromstring(xml_text)

        # Find namespace
        namespace = {"ns": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}

        # Find all infoTable elements
        for info_table in root.findall(".//ns:infoTable", namespace):
            holding = {}

            # Extract fields
            name_elem = info_table.find(".//ns:nameOfIssuer", namespace)
            if name_elem is not None:
                holding["issuer_name"] = name_elem.text

            cusip_elem = info_table.find(".//ns:cusip", namespace)
            if cusip_elem is not None:
                holding["cusip"] = cusip_elem.text

            value_elem = info_table.find(".//ns:value", namespace)
            if value_elem is not None:
                # Value in thousands
                holding["market_value"] = Decimal(value_elem.text)

            shares_elem = info_table.find(".//ns:sshPrnamt", namespace)
            if shares_elem is not None:
                holding["shares"] = Decimal(shares_elem.text)

            putcall_elem = info_table.find(".//ns:putCall", namespace)
            if putcall_elem is not None:
                holding["put_call"] = putcall_elem.text.lower()
            else:
                holding["put_call"] = "none"

            # Investment discretion
            sole_elem = info_table.find(".//ns:Sole", namespace)
            if sole_elem is not None:
                holding["sole"] = Decimal(sole_elem.text)

            shared_elem = info_table.find(".//ns:Shared", namespace)
            if shared_elem is not None:
                holding["shared"] = Decimal(shared_elem.text)

            none_elem = info_table.find(".//ns:None", namespace)
            if none_elem is not None:
                holding["none_discretion"] = Decimal(none_elem.text)

            if holding.get("cusip"):
                holdings.append(holding)

        return holdings

    def _parse_html_table(self, filing_text: str) -> List[Dict[str, Any]]:
        """
        Parse 13F HTML table format (older filings).

        Args:
            filing_text: HTML text

        Returns:
            List of holdings
        """
        holdings = []

        soup = BeautifulSoup(filing_text, "html.parser")

        # Find tables containing holdings
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")

            # Skip header rows
            data_rows = [r for r in rows if len(r.find_all("td")) > 0]

            for row in data_rows:
                cells = row.find_all("td")

                if len(cells) < 4:
                    continue

                # Try to extract CUSIP (9 chars, alphanumeric)
                cusip = None
                issuer_name = None
                shares = None
                value = None

                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)

                    # CUSIP pattern
                    if not cusip and re.match(r"^[A-Z0-9]{9}$", text):
                        cusip = text

                    # Issuer name (usually first non-CUSIP text column)
                    if not issuer_name and len(text) > 10 and not text.isdigit():
                        if cusip or i == 0:
                            issuer_name = text

                    # Shares (large number)
                    shares_match = re.search(r"(\d{1,3}(?:,\d{3})*)", text)
                    if shares_match and not shares:
                        try:
                            shares = Decimal(shares_match.group(1).replace(",", ""))
                        except Exception:
                            pass

                    # Value (in thousands, usually last column)
                    if i == len(cells) - 1:
                        value_match = re.search(r"(\d{1,3}(?:,\d{3})*)", text)
                        if value_match:
                            try:
                                value = Decimal(value_match.group(1).replace(",", ""))
                            except Exception:
                                pass

                # Add if we have minimum required fields
                if cusip and issuer_name:
                    holding = {
                        "cusip": cusip,
                        "issuer_name": issuer_name,
                        "shares": shares or Decimal(0),
                        "market_value": value or Decimal(0),
                        "put_call": "none",
                    }
                    holdings.append(holding)

        return holdings

    def enrich_with_ticker(
        self,
        holdings: List[Dict[str, Any]],
        cusip_to_ticker: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Enrich holdings with ticker symbols.

        Args:
            holdings: List of holdings
            cusip_to_ticker: Mapping of CUSIP to ticker

        Returns:
            Enriched holdings
        """
        for holding in holdings:
            cusip = holding.get("cusip")
            if cusip and cusip in cusip_to_ticker:
                holding["ticker"] = cusip_to_ticker[cusip]

        return holdings
