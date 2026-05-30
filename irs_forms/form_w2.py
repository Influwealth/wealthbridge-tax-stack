"""IRS Form W-2 — Wage and Tax Statement."""
from decimal import Decimal
from irs_forms.base import validate_record, to_dec
from tax_capsule.utils.logger import get_logger

logger = get_logger("FormW2")

EMPLOYEE_SS_RATE = Decimal("0.062")
EMPLOYEE_MEDICARE_RATE = Decimal("0.0145")
FEDERAL_WITHHOLDING_PROXY = Decimal("0.22")

# Additional Medicare tax (0.9%) applies above $200k for single filers
ADDITIONAL_MEDICARE_THRESHOLD = Decimal("200000")
ADDITIONAL_MEDICARE_RATE = Decimal("0.009")


def generate_w2(record) -> dict:
    """
    Generate W-2 data for an employee.
    record.income is treated as annual wages.
    Note: actual withholding requires per-employee W-4 data.
    """
    validate_record(record, expected_entity_type="employee")

    wages = to_dec(record.income)
    federal_withheld = (wages * FEDERAL_WITHHOLDING_PROXY).quantize(Decimal("0.01"))
    ss_wages = min(wages, Decimal("168600"))  # 2024 SS wage base
    ss_withheld = (ss_wages * EMPLOYEE_SS_RATE).quantize(Decimal("0.01"))
    medicare_withheld = (wages * EMPLOYEE_MEDICARE_RATE).quantize(Decimal("0.01"))

    additional_medicare = Decimal("0.00")
    if wages > ADDITIONAL_MEDICARE_THRESHOLD:
        additional_medicare = (
            (wages - ADDITIONAL_MEDICARE_THRESHOLD) * ADDITIONAL_MEDICARE_RATE
        ).quantize(Decimal("0.01"))

    logger.info(f"Generating W-2 for {record.entity_name} tax_year={record.tax_year}")

    return {
        "form": "W-2",
        "revision_year": "2024",
        "employer_name": record.entity_name,
        "tax_year": record.tax_year,
        # Box 1 — Wages
        "box_1_wages_tips": str(wages),
        # Box 2 — Federal income tax withheld
        "box_2_federal_withheld": str(federal_withheld),
        # Box 3-4 — Social Security
        "box_3_ss_wages": str(ss_wages),
        "box_4_ss_withheld": str(ss_withheld),
        # Box 5-6 — Medicare
        "box_5_medicare_wages": str(wages),
        "box_6_medicare_withheld": str(medicare_withheld),
        # Additional Medicare Tax
        "additional_medicare_tax": str(additional_medicare),
        "generated_by": "WealthBridge Tax Stack v3",
    }
