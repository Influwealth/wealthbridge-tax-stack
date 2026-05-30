from decimal import Decimal
from irs_forms.base import validate_record, to_dec
from tax_capsule.utils.logger import get_logger

logger = get_logger("Form1120")

# Post-TCJA flat corporate tax rate (IRC §11)
CORPORATE_TAX_RATE = Decimal("0.21")


def generate_1120(record) -> dict:
    """Generate IRS Form 1120 data for a C-corporation."""
    validate_record(record, expected_entity_type="corporation")
    income = to_dec(record.income)
    expenses = to_dec(record.expenses)
    taxable_income = max(income - expenses, Decimal("0"))
    total_tax = (taxable_income * CORPORATE_TAX_RATE).quantize(Decimal("0.01"))

    logger.info(f"Generating 1120 for {record.entity_name} tax_year={record.tax_year}")

    return {
        "form": "1120",
        "revision_year": "2023",
        "corporation_name": record.entity_name,
        "tax_year": record.tax_year,
        # Part I — Income
        "line_1a_gross_receipts": str(income),
        "line_3_gross_profit": str(income),
        "line_11_total_income": str(income),
        # Part II — Deductions
        "line_26_total_deductions": str(expenses),
        # Part III — Tax Computation
        "line_28_taxable_income": str(taxable_income),
        "line_29_tax_rate": str(CORPORATE_TAX_RATE),
        "line_31_total_tax": str(total_tax),
        # Schedule J — Tax Computation and Payment
        "schedule_j_line_1_tax": str(total_tax),
        "generated_by": "WealthBridge Tax Stack v3",
    }
