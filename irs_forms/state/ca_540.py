"""CA Form 540 — California Resident Income Tax Return stub."""
from decimal import Decimal
from irs_forms.base import to_dec
from tax_capsule.utils.logger import get_logger

logger = get_logger("CA_540")

# 2024 CA top marginal rate 13.3%; proxy 9.3% (mid-bracket)
CA_TAX_RATE_PROXY = Decimal("0.093")
CA_SDI_RATE = Decimal("0.009")   # State Disability Insurance


def generate_ca_540(record) -> dict:
    income = to_dec(record.income)
    expenses = to_dec(record.expenses)
    ca_agi = max(income - expenses, Decimal("0"))
    ca_tax = (ca_agi * CA_TAX_RATE_PROXY).quantize(Decimal("0.01"))
    sdi = (income * CA_SDI_RATE).quantize(Decimal("0.01"))

    logger.info(f"Generating CA 540 stub for {record.entity_name}")

    return {
        "form": "CA 540",
        "state": "CA",
        "status": "STUB",
        "tax_year": record.tax_year,
        "filer_name": record.entity_name,
        "ca_agi": str(ca_agi),
        "estimated_ca_tax": str(ca_tax),
        "estimated_sdi": str(sdi),
        "rate_used": str(CA_TAX_RATE_PROXY),
        "note": "Stub — full CA 540 requires itemized deductions, credits, AMT, SDI details",
        "generated_by": "WealthBridge Tax Stack v3",
    }
