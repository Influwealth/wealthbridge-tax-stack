"""
Credit and deduction optimizer.

Analyzes a tax record's entity type, income, expenses, and R&D projects to
surface the highest-impact tax reduction strategies.

References:
  - IRC §41: Research Credit
  - IRC §179: Immediate expensing of qualified business property
  - IRC §199A: Qualified Business Income (QBI) deduction for pass-throughs
  - IRC §163(j): Business interest expense limitation
  - IRC §174: R&D expenditure amortization (post-TCJA)
"""
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OptimizationOpportunity:
    strategy: str
    authority: str
    estimated_savings: Decimal
    confidence: str  # "high" | "medium" | "low"
    action_items: list[str] = field(default_factory=list)
    notes: str = ""


def optimize_credits(
    income: Decimal,
    expenses: Decimal,
    entity_type: Optional[str],
    total_qre: Decimal = Decimal("0"),
    estimated_rd_credit: Decimal = Decimal("0"),
    asset_purchases: Decimal = Decimal("0"),
    business_interest: Decimal = Decimal("0"),
) -> dict:
    """
    Identify tax optimization opportunities for a given tax profile.

    Returns a ranked list of strategies with estimated savings.
    """
    taxable_income = max(income - expenses, Decimal("0"))
    opportunities: list[OptimizationOpportunity] = []

    # 1. R&D Credit (IRC §41)
    if total_qre > 0 and estimated_rd_credit > 0:
        opportunities.append(OptimizationOpportunity(
            strategy="R&D Tax Credit (IRC §41 ASC)",
            authority="IRC §41",
            estimated_savings=estimated_rd_credit,
            confidence="high",
            action_items=[
                "Ensure all QRE documentation meets 4-part test requirements",
                "File Form 6765 with return",
                "Consider payroll tax offset for startup companies (IRC §41(h))",
            ],
            notes="Credit reduces tax liability dollar-for-dollar.",
        ))

    # 2. Section 179 expensing
    section_179_limit = Decimal("1160000")  # 2023 limit
    if asset_purchases > 0 and entity_type in ("corporation", "sole_proprietor", "employer"):
        deductible = min(asset_purchases, section_179_limit)
        tax_rate = Decimal("0.21") if entity_type == "corporation" else Decimal("0.37")
        savings = (deductible * tax_rate).quantize(Decimal("0.01"))
        opportunities.append(OptimizationOpportunity(
            strategy="Section 179 Immediate Expensing",
            authority="IRC §179",
            estimated_savings=savings,
            confidence="high",
            action_items=[
                f"Elect §179 expensing for up to ${section_179_limit:,.0f} of qualifying property",
                "Attach Form 4562 to return",
            ],
        ))

    # 3. QBI Deduction for pass-throughs (IRC §199A)
    if entity_type in ("partnership", "sole_proprietor") and taxable_income > 0:
        qbi_deduction = (taxable_income * Decimal("0.20")).quantize(Decimal("0.01"))
        # Approximate income tax savings (assuming 37% bracket)
        savings = (qbi_deduction * Decimal("0.37")).quantize(Decimal("0.01"))
        opportunities.append(OptimizationOpportunity(
            strategy="Qualified Business Income (QBI) Deduction",
            authority="IRC §199A",
            estimated_savings=savings,
            confidence="medium",
            action_items=[
                "Verify entity qualifies (not a Specified Service Trade or Business)",
                "W-2 wage / UBIA limitation may apply above income thresholds",
                "Attach Form 8995 or 8995-A to return",
            ],
            notes="Deduction = 20% of QBI, subject to limitations.",
        ))

    # 4. Business interest limitation (IRC §163(j)) — flag if high interest
    interest_limit_rate = Decimal("0.30")
    if business_interest > 0:
        adjusted_taxable = taxable_income  # simplified (pre-EBITDA adjustment)
        limit = (adjusted_taxable * interest_limit_rate).quantize(Decimal("0.01"))
        if business_interest > limit:
            disallowed = business_interest - limit
            # Savings from restructuring to reduce disallowance
            savings = (disallowed * Decimal("0.21")).quantize(Decimal("0.01"))
            opportunities.append(OptimizationOpportunity(
                strategy="Business Interest Expense Restructuring",
                authority="IRC §163(j)",
                estimated_savings=savings,
                confidence="low",
                action_items=[
                    f"${disallowed:,.2f} of interest may be disallowed",
                    "Consider real property or farming trade exemptions",
                    "Carry forward disallowed interest to future years",
                ],
                notes="Limitation = 30% of ATI. Consult §163(j) election options.",
            ))

    # Sort by estimated savings descending
    opportunities.sort(key=lambda o: o.estimated_savings, reverse=True)

    total_potential = sum((o.estimated_savings for o in opportunities), Decimal("0"))

    return {
        "entity_type": entity_type,
        "taxable_income": str(taxable_income.quantize(Decimal("0.01"))),
        "total_potential_savings": str(total_potential.quantize(Decimal("0.01"))),
        "opportunity_count": len(opportunities),
        "opportunities": [
            {
                "strategy": o.strategy,
                "authority": o.authority,
                "estimated_savings": str(o.estimated_savings),
                "confidence": o.confidence,
                "action_items": o.action_items,
                "notes": o.notes,
            }
            for o in opportunities
        ],
        "disclaimer": (
            "Estimates are for planning purposes only. "
            "Consult a licensed tax professional before filing."
        ),
    }
