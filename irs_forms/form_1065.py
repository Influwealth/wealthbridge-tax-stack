from decimal import Decimal
from irs_forms.base import validate_record, to_dec
from tax_capsule.utils.logger import get_logger

logger = get_logger("Form1065")


def generate_1065(record) -> dict:
    """
    Generate IRS Form 1065 data for a partnership.
    Partnerships are pass-through entities — no entity-level income tax.
    Income flows to Schedule K and then to partners' K-1s.
    """
    validate_record(record, expected_entity_type="partnership")
    income = to_dec(record.income)
    expenses = to_dec(record.expenses)
    ordinary_income = max(income - expenses, Decimal("0"))

    logger.info(f"Generating 1065 for {record.entity_name} tax_year={record.tax_year}")

    return {
        "form": "1065",
        "revision_year": "2023",
        "partnership_name": record.entity_name,
        "tax_year": record.tax_year,
        # Part I — Income
        "line_1a_gross_receipts": str(income),
        "line_2_cost_of_goods_sold": "0.00",
        "line_3_gross_profit": str(income),
        # Part I — Deductions
        "line_20_other_deductions": str(expenses),
        "line_22_total_deductions": str(expenses),
        # Ordinary Business Income (Loss)
        "line_22_ordinary_business_income": str(ordinary_income),
        # Schedule K — Partners' Distributive Share Items
        "schedule_k_line_1_ordinary_income": str(ordinary_income),
        # Partnerships have no entity-level income tax
        "entity_level_tax": "0.00",
        "generated_by": "WealthBridge Tax Stack v3",
    }
