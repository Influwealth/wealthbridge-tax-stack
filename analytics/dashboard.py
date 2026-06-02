"""
Dashboard analytics — aggregate tax metrics per entity, year, and type.

All queries are read-only and run against the existing tax_records + rd_projects tables.
No new tables required; results are computed on-the-fly (with cache layer support).
"""
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models


def get_tax_summary(db: Session, tax_year: Optional[int] = None) -> dict:
    """
    Aggregate tax metrics across all records (optionally for a specific year).
    Returns totals and per-entity-type breakdown.
    """
    q = db.query(models.TaxRecord)
    if tax_year:
        q = q.filter(models.TaxRecord.tax_year == tax_year)
    records = q.all()

    if not records:
        return {
            "tax_year": tax_year,
            "record_count": 0,
            "total_income": "0.00",
            "total_expenses": "0.00",
            "total_tax_due": "0.00",
            "effective_rate": "0.00",
            "by_entity_type": {},
        }

    total_income = sum(Decimal(str(r.income)) for r in records)
    total_expenses = sum(Decimal(str(r.expenses)) for r in records)
    total_tax = sum(Decimal(str(r.tax_due or 0)) for r in records)
    taxable = max(total_income - total_expenses, Decimal("0"))
    effective_rate = (total_tax / taxable).quantize(Decimal("0.0001")) if taxable else Decimal("0")

    # Group by entity type
    by_type: dict[str, dict] = {}
    for r in records:
        etype = r.entity_type or "unclassified"
        if etype not in by_type:
            by_type[etype] = {
                "count": 0,
                "income": Decimal("0"),
                "expenses": Decimal("0"),
                "tax_due": Decimal("0"),
            }
        by_type[etype]["count"] += 1
        by_type[etype]["income"] += Decimal(str(r.income))
        by_type[etype]["expenses"] += Decimal(str(r.expenses))
        by_type[etype]["tax_due"] += Decimal(str(r.tax_due or 0))

    return {
        "tax_year": tax_year,
        "record_count": len(records),
        "total_income": str(total_income.quantize(Decimal("0.01"))),
        "total_expenses": str(total_expenses.quantize(Decimal("0.01"))),
        "total_tax_due": str(total_tax.quantize(Decimal("0.01"))),
        "effective_rate": str(effective_rate),
        "by_entity_type": {
            k: {
                "count": v["count"],
                "income": str(v["income"].quantize(Decimal("0.01"))),
                "expenses": str(v["expenses"].quantize(Decimal("0.01"))),
                "tax_due": str(v["tax_due"].quantize(Decimal("0.01"))),
            }
            for k, v in by_type.items()
        },
    }


def get_entity_dashboard(db: Session, entity_name: str) -> dict:
    """
    Per-entity tax history dashboard: all years for a given entity name.
    """
    records = (
        db.query(models.TaxRecord)
        .filter(models.TaxRecord.entity_name == entity_name)
        .order_by(models.TaxRecord.tax_year.asc())
        .all()
    )

    if not records:
        return {"entity_name": entity_name, "years": [], "total_tax_paid": "0.00", "year_count": 0}

    years = []
    total_tax = Decimal("0")
    for r in records:
        income = Decimal(str(r.income))
        expenses = Decimal(str(r.expenses))
        tax = Decimal(str(r.tax_due or 0))
        total_tax += tax
        years.append({
            "tax_year": r.tax_year,
            "income": str(income.quantize(Decimal("0.01"))),
            "expenses": str(expenses.quantize(Decimal("0.01"))),
            "taxable_income": str(max(income - expenses, Decimal("0")).quantize(Decimal("0.01"))),
            "tax_due": str(tax.quantize(Decimal("0.01"))),
            "entity_type": r.entity_type,
        })

    return {
        "entity_name": entity_name,
        "years": years,
        "total_tax_paid": str(total_tax.quantize(Decimal("0.01"))),
        "year_count": len(years),
    }


def get_rd_credit_dashboard(db: Session, tax_year: Optional[int] = None) -> dict:
    """Aggregate R&D credit metrics across all projects."""
    q = db.query(models.RDProject)
    if tax_year:
        q = q.join(models.TaxRecord).filter(models.TaxRecord.tax_year == tax_year)
    projects = q.all()

    if not projects:
        return {
            "tax_year": tax_year,
            "project_count": 0,
            "qualified_projects": 0,
            "total_qre": "0.00",
            "total_estimated_credit": "0.00",
        }

    qualified = [p for p in projects if p.is_qualified]
    total_qre = sum(Decimal(str(p.total_qre)) for p in projects)
    total_credit = sum(Decimal(str(p.estimated_credit)) for p in projects)

    return {
        "tax_year": tax_year,
        "project_count": len(projects),
        "qualified_projects": len(qualified),
        "total_qre": str(total_qre.quantize(Decimal("0.01"))),
        "total_estimated_credit": str(total_credit.quantize(Decimal("0.01"))),
    }
