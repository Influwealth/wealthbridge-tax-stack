"""
Analytics router — BI dashboards, forecasting, credit optimization.

All endpoints are read-only and require filings:read permission.
Snapshot creation (saving results) requires filings:write.
"""
import json
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.rbac import require_permission
from analytics.dashboard import get_tax_summary, get_entity_dashboard, get_rd_credit_dashboard
from analytics.forecasting import forecast_tax_liability, forecast_cashflow
from analytics.credit_optimizer import optimize_credits

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ─── Dashboard endpoints ──────────────────────────────────────────────────────

@router.get("/dashboard/summary")
def tax_summary_dashboard(
    tax_year: Optional[int] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    return get_tax_summary(db, tax_year=tax_year)


@router.get("/dashboard/entity/{entity_name}")
def entity_dashboard(
    entity_name: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    result = get_entity_dashboard(db, entity_name)
    if result["year_count"] == 0:
        raise HTTPException(status_code=404, detail=f"No records found for entity '{entity_name}'")
    return result


@router.get("/dashboard/rd")
def rd_credit_dashboard(
    tax_year: Optional[int] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    return get_rd_credit_dashboard(db, tax_year=tax_year)


# ─── Forecast endpoints ───────────────────────────────────────────────────────

class ForecastRequest(BaseModel):
    entity_name: str
    forecast_years: int = Field(default=3, ge=1, le=5)
    growth_rate_override: Optional[Decimal] = Field(None, ge=0, le=1)


@router.post("/forecast/tax-liability")
def forecast_liability(
    payload: ForecastRequest,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    return forecast_tax_liability(
        db,
        entity_name=payload.entity_name,
        forecast_years=payload.forecast_years,
        growth_rate_override=payload.growth_rate_override,
    )


class CashflowRequest(BaseModel):
    entity_name: str
    tax_year: int = Field(..., ge=2000, le=2100)
    quarterly: bool = True


@router.post("/forecast/cashflow")
def forecast_cashflow_endpoint(
    payload: CashflowRequest,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    return forecast_cashflow(
        db,
        entity_name=payload.entity_name,
        tax_year=payload.tax_year,
        quarterly=payload.quarterly,
    )


# ─── Optimizer endpoint ───────────────────────────────────────────────────────

class OptimizerRequest(BaseModel):
    record_id: int
    asset_purchases: Optional[Decimal] = Field(Decimal("0"), ge=0)
    business_interest: Optional[Decimal] = Field(Decimal("0"), ge=0)


@router.post("/optimize/{record_id}")
def optimize_record(
    record_id: int,
    payload: OptimizerRequest,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")

    # Aggregate R&D credit for this record
    rd_projects = db.query(models.RDProject).filter(models.RDProject.record_id == record_id).all()
    total_qre = sum(Decimal(str(p.total_qre)) for p in rd_projects)
    total_rd_credit = sum(Decimal(str(p.estimated_credit)) for p in rd_projects)

    return optimize_credits(
        income=Decimal(str(record.income)),
        expenses=Decimal(str(record.expenses)),
        entity_type=record.entity_type,
        total_qre=total_qre,
        estimated_rd_credit=total_rd_credit,
        asset_purchases=payload.asset_purchases or Decimal("0"),
        business_interest=payload.business_interest or Decimal("0"),
    )


# ─── Snapshot endpoints ───────────────────────────────────────────────────────

@router.post("/snapshots")
def save_snapshot(
    snapshot_type: str,
    entity_name: Optional[str] = None,
    tax_year: Optional[int] = None,
    payload: dict = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("filings:write")),
):
    snap = models.AnalyticsSnapshot(
        snapshot_type=snapshot_type,
        entity_name=entity_name,
        tax_year=tax_year,
        payload=json.dumps(payload or {}, default=str),
        created_by=current_user.id,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)
    return {"id": snap.id, "snapshot_type": snap.snapshot_type, "created_at": str(snap.created_at)}


@router.get("/snapshots")
def list_snapshots(
    snapshot_type: Optional[str] = None,
    entity_name: Optional[str] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    q = db.query(models.AnalyticsSnapshot)
    if snapshot_type:
        q = q.filter(models.AnalyticsSnapshot.snapshot_type == snapshot_type)
    if entity_name:
        q = q.filter(models.AnalyticsSnapshot.entity_name == entity_name)
    snaps = q.order_by(models.AnalyticsSnapshot.created_at.desc()).limit(50).all()
    return [
        {
            "id": s.id,
            "snapshot_type": s.snapshot_type,
            "entity_name": s.entity_name,
            "tax_year": s.tax_year,
            "created_at": str(s.created_at),
        }
        for s in snaps
    ]
