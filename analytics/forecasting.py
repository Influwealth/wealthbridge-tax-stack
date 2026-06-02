"""
Tax forecasting — cashflow and tax liability projections.

Uses linear trend extrapolation from historical tax records.
Suitable for 1-3 year outlooks; not a substitute for professional tax planning.

Referenced IRC: §461 (all-events test), §451 (accrual basis income timing).
"""
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app import models


def _linear_trend(values: list[Decimal]) -> Decimal:
    """Simple linear trend: return the average year-over-year change."""
    if len(values) < 2:
        return Decimal("0")
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    return sum(deltas) / len(deltas)


def forecast_tax_liability(
    db: Session,
    entity_name: str,
    forecast_years: int = 3,
    growth_rate_override: Optional[Decimal] = None,
) -> dict:
    """
    Project future tax liability for a specific entity based on historical records.

    Parameters:
        entity_name: Entity to forecast
        forecast_years: Number of years to project (1-5)
        growth_rate_override: Optional manual income growth rate (e.g. Decimal("0.05") for 5%)
    """
    forecast_years = max(1, min(forecast_years, 5))

    records = (
        db.query(models.TaxRecord)
        .filter(models.TaxRecord.entity_name == entity_name)
        .order_by(models.TaxRecord.tax_year.asc())
        .all()
    )

    if not records:
        return {
            "entity_name": entity_name,
            "historical_years": 0,
            "projections": [],
            "method": "insufficient_data",
            "warning": "No historical records found for this entity.",
        }

    incomes = [Decimal(str(r.income)) for r in records]
    expenses = [Decimal(str(r.expenses)) for r in records]
    taxes = [Decimal(str(r.tax_due or 0)) for r in records]
    entity_type = records[-1].entity_type

    last_year = records[-1].tax_year
    last_income = incomes[-1]
    last_expense = expenses[-1]
    last_tax = taxes[-1]

    if growth_rate_override is not None:
        income_growth = last_income * growth_rate_override
        expense_growth = last_expense * growth_rate_override
    else:
        income_growth = _linear_trend(incomes)
        expense_growth = _linear_trend(expenses)

    # Determine effective tax rate from last year
    last_taxable = max(last_income - last_expense, Decimal("0"))
    eff_rate = (last_tax / last_taxable).quantize(Decimal("0.0001")) if last_taxable else Decimal("0.21")

    projections = []
    proj_income = last_income
    proj_expense = last_expense

    for i in range(1, forecast_years + 1):
        proj_income = (proj_income + income_growth).quantize(Decimal("0.01"))
        proj_expense = (proj_expense + expense_growth).quantize(Decimal("0.01"))
        proj_taxable = max(proj_income - proj_expense, Decimal("0"))
        proj_tax = (proj_taxable * eff_rate).quantize(Decimal("0.01"))

        projections.append({
            "year": last_year + i,
            "projected_income": str(proj_income),
            "projected_expenses": str(proj_expense),
            "projected_taxable_income": str(proj_taxable),
            "projected_tax_due": str(proj_tax),
            "effective_rate": str(eff_rate),
        })

    return {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "historical_years": len(records),
        "base_year": last_year,
        "projections": projections,
        "method": "linear_trend" if growth_rate_override is None else "manual_growth_rate",
        "assumptions": {
            "income_annual_growth": str(income_growth.quantize(Decimal("0.01"))),
            "expense_annual_growth": str(expense_growth.quantize(Decimal("0.01"))),
            "effective_rate": str(eff_rate),
        },
    }


def forecast_cashflow(
    db: Session,
    entity_name: str,
    tax_year: int,
    quarterly: bool = True,
) -> dict:
    """
    Estimate quarterly estimated tax payments (IRC §6654) for a given year.

    Assumes even income distribution across quarters.
    Safe harbor: pay 100% of prior year tax in equal quarterly installments.
    """
    # Get prior year record for safe harbor
    prior_year_records = (
        db.query(models.TaxRecord)
        .filter(
            models.TaxRecord.entity_name == entity_name,
            models.TaxRecord.tax_year == tax_year - 1,
        )
        .all()
    )

    # Get current year record if available
    current_records = (
        db.query(models.TaxRecord)
        .filter(
            models.TaxRecord.entity_name == entity_name,
            models.TaxRecord.tax_year == tax_year,
        )
        .all()
    )

    prior_tax = sum((Decimal(str(r.tax_due or 0)) for r in prior_year_records), Decimal("0"))
    current_tax = sum((Decimal(str(r.tax_due or 0)) for r in current_records), Decimal("0")) if current_records else None

    safe_harbor_quarterly = (prior_tax / Decimal("4")).quantize(Decimal("0.01"))

    quarters = []
    if quarterly:
        # Standard estimated payment due dates (IRC §6654)
        due_dates = [
            f"{tax_year}-04-15",  # Q1
            f"{tax_year}-06-15",  # Q2
            f"{tax_year}-09-15",  # Q3
            f"{tax_year + 1}-01-15",  # Q4
        ]
        for i, due in enumerate(due_dates, 1):
            quarters.append({
                "quarter": i,
                "due_date": due,
                "safe_harbor_payment": str(safe_harbor_quarterly),
            })

    return {
        "entity_name": entity_name,
        "tax_year": tax_year,
        "prior_year_tax": str(prior_tax.quantize(Decimal("0.01"))),
        "current_year_tax_estimate": str(current_tax.quantize(Decimal("0.01"))) if current_tax else None,
        "safe_harbor_annual": str(prior_tax.quantize(Decimal("0.01"))),
        "safe_harbor_quarterly": str(safe_harbor_quarterly),
        "quarterly_schedule": quarters,
        "method": "safe_harbor_100pct_prior_year",
        "authority": "IRC §6654",
    }
