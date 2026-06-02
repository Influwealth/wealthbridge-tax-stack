"""TX Franchise Tax (Texas Margin Tax) stub — no personal income tax in Texas."""
from decimal import Decimal
from irs_forms.base import to_dec
from tax_capsule.utils.logger import get_logger

logger = get_logger("TX_Franchise")

# 2024 TX franchise tax rates
TX_RATE_GENERAL = Decimal("0.0075")   # 0.75% for most businesses
TX_RATE_RETAIL = Decimal("0.00375")   # 0.375% for retail/wholesale
TX_EZ_THRESHOLD = Decimal("20000000") # EZ computation threshold
TX_NO_TAX_THRESHOLD = Decimal("2470000")  # No-tax-due threshold (2024)


def generate_tx_franchise(record, is_retail: bool = False) -> dict:
    revenue = to_dec(record.income)
    expenses = to_dec(record.expenses)
    taxable_margin = max(revenue - expenses, Decimal("0"))
    rate = TX_RATE_RETAIL if is_retail else TX_RATE_GENERAL
    tax_due = (taxable_margin * rate).quantize(Decimal("0.01"))
    no_tax_due = revenue <= TX_NO_TAX_THRESHOLD

    logger.info(f"Generating TX Franchise Tax stub for {record.entity_name}")

    return {
        "form": "TX Franchise Tax",
        "state": "TX",
        "status": "STUB",
        "tax_year": record.tax_year,
        "entity_name": record.entity_name,
        "total_revenue": str(revenue),
        "taxable_margin": str(taxable_margin),
        "rate_applied": str(rate),
        "estimated_tax_due": str(tax_due),
        "no_tax_due_applies": no_tax_due,
        "no_tax_threshold": str(TX_NO_TAX_THRESHOLD),
        "note": "TX has no personal income tax. Stub — full franchise return requires COGS/compensation deduction election.",
        "generated_by": "WealthBridge Tax Stack v3",
    }
