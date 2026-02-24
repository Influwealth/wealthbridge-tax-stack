from tax_capsule.utils.logger import get_logger
from tax_capsule.utils.schemas import TaxCalculationRequest

logger = get_logger("TaxEngine")

def calculate_tax(data: TaxCalculationRequest):
    taxable_income = max(data.income - data.expenses, 0)
    tax_rate = 0.21
    tax_due = taxable_income * tax_rate
    logger.info(f"Processed calculation: income={data.income}, expenses={data.expenses}, tax_due={tax_due}")
    return {
        "taxable_income": taxable_income,
        "tax_due": round(tax_due, 2),
        "currency": "USD"
    }
