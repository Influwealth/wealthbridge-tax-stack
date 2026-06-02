"""IRS Schedule C — Profit or Loss From Business (Sole Proprietorship)."""
from decimal import Decimal
from irs_forms.base import validate_record, to_dec
from tax_capsule.utils.logger import get_logger

logger = get_logger("FormScheduleC")

# SE tax rate = 15.3% on net earnings (12.4% SS + 2.9% Medicare)
# Deductible half of SE tax = 50% of total SE tax
SE_TAX_RATE = Decimal("0.153")
SE_DEDUCTIBLE_RATE = Decimal("0.5")


def generate_schedule_c(record) -> dict:
    """Generate Schedule C data for a sole proprietor."""
    validate_record(record, expected_entity_type="sole_proprietor")

    gross_income = to_dec(record.income)
    total_expenses = to_dec(record.expenses)
    net_profit = max(gross_income - total_expenses, Decimal("0"))
    net_loss = max(total_expenses - gross_income, Decimal("0"))

    # Self-employment tax calculation (Schedule SE)
    se_earnings = net_profit * Decimal("0.9235")  # 92.35% of net profit
    se_tax = (se_earnings * SE_TAX_RATE).quantize(Decimal("0.01"))
    se_deduction = (se_tax * SE_DEDUCTIBLE_RATE).quantize(Decimal("0.01"))

    logger.info(
        f"Generating Schedule C for {record.entity_name} tax_year={record.tax_year}, "
        f"net_profit={net_profit}"
    )

    return {
        "form": "Schedule C",
        "revision_year": "2023",
        "proprietor_name": record.entity_name,
        "tax_year": record.tax_year,
        # Part I — Income
        "line_1_gross_receipts": str(gross_income),
        "line_7_gross_income": str(gross_income),
        # Part II — Expenses
        "line_28_total_expenses": str(total_expenses),
        # Net Profit/Loss
        "line_31_net_profit": str(net_profit),
        "line_31_net_loss": str(net_loss),
        # Schedule SE summary
        "se_earnings_subject_to_tax": str(se_earnings.quantize(Decimal("0.01"))),
        "estimated_se_tax": str(se_tax),
        "deductible_se_tax": str(se_deduction),
        "generated_by": "WealthBridge Tax Stack v3",
    }
