"""
rd_plugin.rd_core — thin wrapper around qre_agent.engine.

Keeps the existing run_rd_analysis() API so integrations.py and legacy
callers continue to work without changes.
"""
from decimal import Decimal
from tax_capsule.utils.logger import get_logger
from qre_agent.engine import calculate_credit
from qre_agent.scorer import ExpenseCategory

logger = get_logger("RDPlugin")


def run_rd_analysis(data: dict) -> dict:
    project = data.get("project_name", "Unknown Project")

    try:
        qualified_expenses = Decimal(str(data.get("qualified_expenses", "0")))
        wages = Decimal(str(data.get("total_wages") or "0"))
        supplies = Decimal(str(data.get("supply_costs") or "0"))
        contract_raw = Decimal(str(data.get("contract_research") or "0"))
    except Exception as e:
        logger.error(f"Invalid R&D input data: {e}")
        return {"project": project, "status": "ERROR", "error": str(e)}

    # Build structured expense list for the engine
    expenses = []
    if wages > 0:
        expenses.append({"category": ExpenseCategory.wages.value, "amount": str(wages)})
    if supplies > 0:
        expenses.append({"category": ExpenseCategory.supplies.value, "amount": str(supplies)})
    if contract_raw > 0:
        expenses.append({"category": ExpenseCategory.contract_research.value, "amount": str(contract_raw)})
    if qualified_expenses > 0:
        expenses.append({"category": ExpenseCategory.other_qualified.value, "amount": str(qualified_expenses)})

    if not expenses:
        return {"project": project, "status": "ANALYZED", "total_qre": "0.00", "estimated_credit": "0.00"}

    result = calculate_credit(expenses)

    logger.info(
        f"R&D analysis for '{project}': total_qre={result['total_qre']}, "
        f"credit={result['estimated_credit']}"
    )

    return {
        "project": project,
        "qualified_expenses": str(qualified_expenses),
        "total_wages_included": str(wages),
        "supply_costs_included": str(supplies),
        "contract_research_65pct": str(
            (contract_raw * Decimal("0.65")).quantize(Decimal("0.01"))
        ),
        "total_qre": result["total_qre"],
        "credit_rate": result["credit_rate"],
        "estimated_credit": result["estimated_credit"],
        "method": result["method"],
        "status": "ANALYZED",
    }
