"""NY Form IT-201 — Resident Income Tax Return stub."""
from decimal import Decimal
from irs_forms.base import to_dec
from tax_capsule.utils.logger import get_logger

logger = get_logger("NY_IT201")

# 2024 NY top marginal rate proxy (10.9% above $25M; use 6.85% as mid-bracket proxy)
NY_TAX_RATE_PROXY = Decimal("0.0685")


def generate_ny_it201(record) -> dict:
    income = to_dec(record.income)
    expenses = to_dec(record.expenses)
    ny_agi = max(income - expenses, Decimal("0"))
    ny_tax = (ny_agi * NY_TAX_RATE_PROXY).quantize(Decimal("0.01"))

    logger.info(f"Generating NY IT-201 stub for {record.entity_name}")

    return {
        "form": "NY IT-201",
        "state": "NY",
        "status": "STUB",
        "tax_year": record.tax_year,
        "filer_name": record.entity_name,
        "ny_agi": str(ny_agi),
        "estimated_ny_tax": str(ny_tax),
        "rate_used": str(NY_TAX_RATE_PROXY),
        "note": "Stub — full NY IT-201 requires NYC/Yonkers surcharge, itemized deductions, credits",
        "generated_by": "WealthBridge Tax Stack v3",
    }
