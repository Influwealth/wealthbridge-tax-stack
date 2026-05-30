from decimal import Decimal
from tax_capsule.utils.logger import get_logger

logger = get_logger("RDPlugin")

# IRC §41 — Research Credit, Alternative Simplified Credit (ASC)
# ASC rate: 14% of QREs exceeding 50% of avg prior 3yr QREs.
# Simplified here (no historical QRE data): 14% of total current-year QREs.
ASC_RATE = Decimal("0.14")
# Contract research: only 65% qualifies under IRC §41(b)(3)
CONTRACT_RESEARCH_FACTOR = Decimal("0.65")


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

    contract_qualified = (contract_raw * CONTRACT_RESEARCH_FACTOR).quantize(Decimal("0.01"))
    total_qre = qualified_expenses + wages + supplies + contract_qualified
    estimated_credit = (total_qre * ASC_RATE).quantize(Decimal("0.01"))

    logger.info(
        f"R&D analysis for '{project}': total_qre={total_qre}, credit={estimated_credit}"
    )

    return {
        "project": project,
        "qualified_expenses": str(qualified_expenses),
        "total_wages_included": str(wages),
        "supply_costs_included": str(supplies),
        "contract_research_65pct": str(contract_qualified),
        "total_qre": str(total_qre),
        "credit_rate": str(ASC_RATE),
        "estimated_credit": str(estimated_credit),
        "method": "Alternative Simplified Credit (IRC §41)",
        "status": "ANALYZED",
    }
