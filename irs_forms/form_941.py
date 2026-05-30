from decimal import Decimal
from irs_forms.base import validate_record, to_dec
from tax_capsule.utils.logger import get_logger

logger = get_logger("Form941")

# 2024 FICA rates
EMPLOYEE_SS_RATE = Decimal("0.062")
EMPLOYEE_MEDICARE_RATE = Decimal("0.0145")
EMPLOYER_SS_RATE = Decimal("0.062")
EMPLOYER_MEDICARE_RATE = Decimal("0.0145")
# Proxy withholding rate (22% bracket); real implementations need per-employee W-4 data
FEDERAL_WITHHOLDING_PROXY = Decimal("0.22")


def generate_941(record, quarter: int = 1) -> dict:
    """
    Generate IRS Form 941 (Employer's Quarterly Federal Tax Return).
    record.income is treated as total quarterly wages paid.
    Note: federal income tax withholding uses a 22% proxy — production use
    requires per-employee W-4 withholding data.
    """
    validate_record(record, expected_entity_type="employer")
    wages = to_dec(record.income)
    quarter = max(1, min(4, int(quarter)))

    employee_ss = (wages * EMPLOYEE_SS_RATE).quantize(Decimal("0.01"))
    employee_medicare = (wages * EMPLOYEE_MEDICARE_RATE).quantize(Decimal("0.01"))
    employer_ss = (wages * EMPLOYER_SS_RATE).quantize(Decimal("0.01"))
    employer_medicare = (wages * EMPLOYER_MEDICARE_RATE).quantize(Decimal("0.01"))
    federal_withheld = (wages * FEDERAL_WITHHOLDING_PROXY).quantize(Decimal("0.01"))
    total_taxes = (
        federal_withheld + employee_ss + employee_medicare + employer_ss + employer_medicare
    ).quantize(Decimal("0.01"))

    logger.info(f"Generating 941 Q{quarter} for {record.entity_name} tax_year={record.tax_year}")

    return {
        "form": "941",
        "revision_year": "2024",
        "employer_name": record.entity_name,
        "tax_year": record.tax_year,
        "quarter": quarter,
        # Part 1 — Tell us about your return
        "line_1_employee_count": 1,  # placeholder — real impl needs payroll headcount
        "line_2_wages_tips": str(wages),
        "line_3_federal_income_tax_withheld": str(federal_withheld),
        # Line 5 — Social Security and Medicare taxes
        "line_5a_ss_wages": str(wages),
        "line_5a_employee_ss_tax": str(employee_ss),
        "line_5a_employer_ss_tax": str(employer_ss),
        "line_5c_medicare_wages": str(wages),
        "line_5c_employee_medicare_tax": str(employee_medicare),
        "line_5c_employer_medicare_tax": str(employer_medicare),
        "line_6_total_taxes": str(total_taxes),
        "generated_by": "WealthBridge Tax Stack v3",
    }
