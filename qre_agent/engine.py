"""
QRE Engine — IRC §41 Alternative Simplified Credit (ASC) calculator.

ASC formula (simplified, no prior-year history required):
  Credit = 14% × total_QRE

When prior 3-year QRE average is available:
  Credit = 14% × (current_QRE − 50% × avg_prior_QRE)
  (This implementation accepts optional prior_qre_avg parameter.)
"""
from decimal import Decimal

from qre_agent.classifier import classify_activity, is_qualified_activity
from qre_agent.scorer import score_all_expenses, ExpenseRecord, ExpenseCategory
from qre_agent.validator import validate_project_documentation

ASC_RATE = Decimal("0.14")
ASC_RATE_STARTUP = Decimal("0.06")  # startup rate (first 3 years with no prior history)
BASE_PERCENTAGE = Decimal("0.50")


def calculate_credit(
    expenses: list[dict],
    prior_qre_avg: Decimal | None = None,
    is_startup: bool = False,
) -> dict:
    """
    Calculate IRC §41 ASC credit from a list of expense dicts.

    Each expense dict: {category: str, amount: str|Decimal, description: str}
    Returns: {total_qre, credit_rate, estimated_credit, method, base_amount, components}
    """
    expense_records = [
        ExpenseRecord(
            category=ExpenseCategory(e["category"]),
            amount=Decimal(str(e["amount"])),
            description=e.get("description", ""),
        )
        for e in expenses
    ]

    scored = score_all_expenses(expense_records)
    total_qre = Decimal(scored["total_qre"])

    if prior_qre_avg is not None and prior_qre_avg > 0:
        base_amount = (prior_qre_avg * BASE_PERCENTAGE).quantize(Decimal("0.01"))
        incremental_qre = max(total_qre - base_amount, Decimal("0"))
        rate = ASC_RATE_STARTUP if is_startup else ASC_RATE
        estimated_credit = (incremental_qre * rate).quantize(Decimal("0.01"))
        method = "ASC with prior-year base (IRC §41(c)(5))"
    else:
        rate = ASC_RATE_STARTUP if is_startup else ASC_RATE
        estimated_credit = (total_qre * rate).quantize(Decimal("0.01"))
        base_amount = Decimal("0")
        method = "ASC simplified (no prior-year QRE)"

    return {
        "total_qre": str(total_qre),
        "base_amount": str(base_amount),
        "credit_rate": str(rate),
        "estimated_credit": str(estimated_credit),
        "method": method,
        "components": scored["by_category"],
        "status": "CALCULATED",
    }


def analyze_project(project_data: dict, expenses: list[dict]) -> dict:
    """
    Full project analysis: classify + validate + score + calculate credit.
    Returns a comprehensive analysis dict suitable for the API response.
    """
    description = project_data.get("description", "")
    activity_type = classify_activity(description)
    qualified = is_qualified_activity(activity_type)

    validation = validate_project_documentation({
        **project_data,
        "activity_type": activity_type.value,
        "has_expenses": len(expenses) > 0,
        "expense_count": len(expenses),
    })

    if qualified and expenses:
        credit_result = calculate_credit(expenses)
    else:
        credit_result = {
            "total_qre": "0.00",
            "base_amount": "0.00",
            "credit_rate": "0.00",
            "estimated_credit": "0.00",
            "method": "N/A — activity not qualified or no expenses",
            "components": {},
            "status": "NOT_QUALIFIED" if not qualified else "NO_EXPENSES",
        }

    return {
        "project_name": project_data.get("project_name", ""),
        "activity_type": activity_type.value,
        "is_qualified": qualified,
        "validation": {
            "is_valid": validation.is_valid,
            "score": validation.score,
            "issues": validation.issues,
            "recommendations": validation.recommendations,
        },
        "credit_calculation": credit_result,
    }
