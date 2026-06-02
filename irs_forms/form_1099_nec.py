"""IRS Form 1099-NEC — Nonemployee Compensation."""
from decimal import Decimal
from irs_forms.base import validate_record, to_dec
from tax_capsule.utils.logger import get_logger

logger = get_logger("Form1099NEC")

# 1099-NEC reporting threshold (2024)
REPORTING_THRESHOLD = Decimal("600.00")
# Backup withholding rate (if TIN not provided)
BACKUP_WITHHOLDING_RATE = Decimal("0.24")


def generate_1099_nec(record, apply_backup_withholding: bool = False) -> dict:
    """
    Generate Form 1099-NEC data for a contractor.
    record.income is treated as nonemployee compensation paid.
    """
    validate_record(record, expected_entity_type="contractor")

    compensation = to_dec(record.income)
    backup_withholding = Decimal("0.00")

    if apply_backup_withholding:
        backup_withholding = (compensation * BACKUP_WITHHOLDING_RATE).quantize(Decimal("0.01"))

    below_threshold = compensation < REPORTING_THRESHOLD

    logger.info(
        f"Generating 1099-NEC for {record.entity_name} tax_year={record.tax_year}, "
        f"compensation={compensation}, below_threshold={below_threshold}"
    )

    return {
        "form": "1099-NEC",
        "revision_year": "2024",
        "payer_name": record.entity_name,
        "tax_year": record.tax_year,
        # Box 1 — Nonemployee compensation
        "box_1_nonemployee_compensation": str(compensation),
        # Box 4 — Federal income tax withheld (backup withholding)
        "box_4_federal_withheld": str(backup_withholding),
        "filing_required": not below_threshold,
        "below_reporting_threshold": below_threshold,
        "reporting_threshold": str(REPORTING_THRESHOLD),
        "generated_by": "WealthBridge Tax Stack v3",
    }
