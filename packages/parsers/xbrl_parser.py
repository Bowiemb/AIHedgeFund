"""XBRL parser for extracting financial statements."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class XBRLParser:
    """
    Parser for XBRL financial data from SEC company facts API.

    Extracts:
    - Income statement line items
    - Balance sheet line items
    - Cash flow statement line items
    """

    # Common GAAP tags mapping
    INCOME_STATEMENT_TAGS = {
        "Revenues": "us-gaap:Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "CostOfRevenue": "us-gaap:CostOfRevenue",
        "GrossProfit": "us-gaap:GrossProfit",
        "OperatingExpenses": "us-gaap:OperatingExpenses",
        "OperatingIncomeLoss": "us-gaap:OperatingIncomeLoss",
        "NetIncomeLoss": "us-gaap:NetIncomeLoss",
        "EarningsPerShareBasic": "us-gaap:EarningsPerShareBasic",
        "EarningsPerShareDiluted": "us-gaap:EarningsPerShareDiluted",
    }

    BALANCE_SHEET_TAGS = {
        "Assets": "us-gaap:Assets",
        "AssetsCurrent": "us-gaap:AssetsCurrent",
        "CashAndCashEquivalentsAtCarryingValue": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "AccountsReceivableNetCurrent": "us-gaap:AccountsReceivableNetCurrent",
        "InventoryNet": "us-gaap:InventoryNet",
        "PropertyPlantAndEquipmentNet": "us-gaap:PropertyPlantAndEquipmentNet",
        "Liabilities": "us-gaap:Liabilities",
        "LiabilitiesCurrent": "us-gaap:LiabilitiesCurrent",
        "AccountsPayableCurrent": "us-gaap:AccountsPayableCurrent",
        "LongTermDebt": "us-gaap:LongTermDebt",
        "StockholdersEquity": "us-gaap:StockholdersEquity",
    }

    CASHFLOW_TAGS = {
        "NetCashProvidedByUsedInOperatingActivities": "us-gaap:NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInInvestingActivities": "us-gaap:NetCashProvidedByUsedInInvestingActivities",
        "NetCashProvidedByUsedInFinancingActivities": "us-gaap:NetCashProvidedByUsedInFinancingActivities",
        "PaymentsToAcquirePropertyPlantAndEquipment": "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment",
        "Depreciation": "us-gaap:Depreciation",
    }

    def __init__(self):
        """Initialize XBRL parser."""
        pass

    def parse_company_facts(self, facts_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse company facts from SEC API.

        Args:
            facts_data: Company facts JSON from SEC

        Returns:
            Dict with income, balance, cashflow statements
        """
        result = {
            "income": [],
            "balance": [],
            "cashflow": [],
        }

        if "facts" not in facts_data:
            logger.warning("No facts found in data")
            return result

        # Extract US-GAAP facts
        us_gaap = facts_data["facts"].get("us-gaap", {})

        # Parse income statement
        result["income"] = self._parse_statement_type(
            us_gaap,
            self.INCOME_STATEMENT_TAGS,
            "income",
        )

        # Parse balance sheet
        result["balance"] = self._parse_statement_type(
            us_gaap,
            self.BALANCE_SHEET_TAGS,
            "balance",
        )

        # Parse cash flow
        result["cashflow"] = self._parse_statement_type(
            us_gaap,
            self.CASHFLOW_TAGS,
            "cashflow",
        )

        logger.info(
            f"Parsed {len(result['income'])} income, "
            f"{len(result['balance'])} balance, "
            f"{len(result['cashflow'])} cashflow items"
        )

        return result

    def _parse_statement_type(
        self,
        us_gaap: Dict[str, Any],
        tag_mapping: Dict[str, str],
        statement_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Parse specific statement type from XBRL data.

        Args:
            us_gaap: US-GAAP facts
            tag_mapping: Mapping of friendly names to XBRL tags
            statement_type: Statement type (income, balance, cashflow)

        Returns:
            List of parsed line items
        """
        items = []

        for friendly_name, xbrl_tag in tag_mapping.items():
            # Extract tag name from namespace
            tag_name = xbrl_tag.split(":")[-1]

            if tag_name not in us_gaap:
                continue

            concept = us_gaap[tag_name]

            # Get units (usually USD)
            for unit_type, unit_data in concept.get("units", {}).items():
                for entry in unit_data:
                    # Extract relevant fields
                    item = {
                        "statement_type": statement_type,
                        "line_item": friendly_name,
                        "line_item_std": tag_name,
                        "value": Decimal(str(entry.get("val", 0))),
                        "unit": unit_type,
                        "fiscal_year": entry.get("fy"),
                        "fiscal_quarter": entry.get("fp"),
                        "filed": entry.get("filed"),
                        "form": entry.get("form"),
                        "accession": entry.get("accn"),
                    }

                    # Parse dates
                    if "start" in entry:
                        item["period_start"] = self._parse_date(entry["start"])
                    if "end" in entry:
                        item["period_end"] = self._parse_date(entry["end"])

                    # Instant vs duration
                    item["is_instant"] = "start" not in entry

                    items.append(item)

        return items

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime.

        Args:
            date_str: Date string (YYYY-MM-DD)

        Returns:
            Datetime object or None
        """
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def normalize_line_item(self, line_item: str) -> str:
        """
        Normalize line item name to standard format.

        Args:
            line_item: Original line item name

        Returns:
            Normalized name
        """
        # Remove common suffixes/prefixes
        normalized = line_item
        normalized = normalized.replace("Abstract", "")
        normalized = normalized.replace("TextBlock", "")

        # Convert camelCase to Title Case
        import re
        normalized = re.sub(r"([A-Z])", r" \1", normalized).strip()

        return normalized
