"""
Expense scorer for IRC §41 QRE determination.

Qualification rates per IRC §41(b):
  - Wages (in-house): 100%
  - Supplies (non-depreciable): 100%
  - Contract research: 65%  (IRC §41(b)(3))
  - Other qualified: 100%
  - Non-qualified: 0%
"""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class ExpenseCategory(str, Enum):
    wages = "wages"
    supplies = "supplies"
    contract_research = "contract_research"
    other_qualified = "other_qualified"
    non_qualified = "non_qualified"


QUALIFICATION_RATES: dict[ExpenseCategory, Decimal] = {
    ExpenseCategory.wages: Decimal("1.00"),
    ExpenseCategory.supplies: Decimal("1.00"),
    ExpenseCategory.contract_research: Decimal("0.65"),
    ExpenseCategory.other_qualified: Decimal("1.00"),
    ExpenseCategory.non_qualified: Decimal("0.00"),
}


@dataclass
class ExpenseRecord:
    category: ExpenseCategory
    amount: Decimal
    description: str = ""


@dataclass
class ScoredExpense:
    category: ExpenseCategory
    amount: Decimal
    qualification_rate: Decimal
    qualified_amount: Decimal
    description: str = ""


def score_expense(category: ExpenseCategory, amount: Decimal) -> ScoredExpense:
    rate = QUALIFICATION_RATES[category]
    qualified = (amount * rate).quantize(Decimal("0.01"))
    return ScoredExpense(
        category=category,
        amount=amount,
        qualification_rate=rate,
        qualified_amount=qualified,
    )


def score_all_expenses(expenses: list[ExpenseRecord]) -> dict:
    """Score a list of expenses and return aggregate QRE totals."""
    scored = [score_expense(e.category, e.amount) for e in expenses]

    total_amount = sum(e.amount for e in scored).quantize(Decimal("0.01"))
    total_qre = sum(e.qualified_amount for e in scored).quantize(Decimal("0.01"))

    by_category: dict[str, dict] = {}
    for s in scored:
        key = s.category.value
        if key not in by_category:
            by_category[key] = {"amount": Decimal("0"), "qualified_amount": Decimal("0")}
        by_category[key]["amount"] += s.amount
        by_category[key]["qualified_amount"] += s.qualified_amount

    return {
        "total_amount": str(total_amount),
        "total_qre": str(total_qre),
        "by_category": {
            k: {
                "amount": str(v["amount"].quantize(Decimal("0.01"))),
                "qualified_amount": str(v["qualified_amount"].quantize(Decimal("0.01"))),
                "qualification_rate": str(QUALIFICATION_RATES[ExpenseCategory(k)]),
            }
            for k, v in by_category.items()
        },
        "line_items": [
            {
                "category": s.category.value,
                "amount": str(s.amount),
                "qualification_rate": str(s.qualification_rate),
                "qualified_amount": str(s.qualified_amount),
                "description": s.description,
            }
            for s in scored
        ],
    }
