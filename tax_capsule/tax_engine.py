from decimal import Decimal
from tax_capsule.utils.logger import get_logger
from tax_capsule.utils.schemas import TaxCalculationRequest

logger = get_logger("TaxEngine")

ENTITY_RATES = {
    "corporation": Decimal("0.21"),
    "partnership": Decimal("0.00"),   # pass-through entity — no entity-level tax
    "employer": Decimal("0.21"),      # proxy; actual liability is FICA on wages
    None: Decimal("0.21"),
}

FORM_MAP = {
    "corporation": "1120",
    "partnership": "1065",
    "employer": "941",
    None: "1120",
}


def calculate_tax(data: TaxCalculationRequest) -> dict:
    income = Decimal(str(data.income))
    expenses = Decimal(str(data.expenses or 0))
    taxable_income = max(income - expenses, Decimal("0"))

    entity_type = getattr(data, "entity_type", None)
    tax_rate = ENTITY_RATES.get(entity_type, Decimal("0.21"))
    tax_due = (taxable_income * tax_rate).quantize(Decimal("0.01"))

    logger.info(
        f"Tax calc: entity_type={entity_type}, income={income}, "
        f"expenses={expenses}, taxable={taxable_income}, rate={tax_rate}, due={tax_due}"
    )

    return {
        "taxable_income": taxable_income,
        "tax_due": tax_due,
        "currency": "USD",
        "form_hint": FORM_MAP.get(entity_type),
    }
