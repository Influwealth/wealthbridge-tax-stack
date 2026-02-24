from .utils.logger import get_logger
from .utils.validators import validate_required_fields

logger = get_logger("TaxEngine")

def calculate_tax(data: dict):
    validate_required_fields(data, ["income"])
    income = data["income"]
    expenses = data.get("expenses", 0)
    taxable_income = max(income - expenses, 0)
    tax_due = taxable_income * 0.21
    logger.info(f"Tax calculated: {tax_due}")
    return {
        "taxable_income": taxable_income,
        "tax_due": tax_due
    }
