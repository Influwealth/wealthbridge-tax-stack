from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.rbac import require_permission
from tax_capsule.utils.schemas import TaxRecordCreate, TaxRecordUpdate, TaxRecordResponse, TaxCalculationRequest
from tax_capsule.tax_engine import calculate_tax

router = APIRouter(prefix="/tax/records", tags=["tax-records"])


@router.post("/", response_model=TaxRecordResponse, status_code=201)
def create_record(
    payload: TaxRecordCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("records:write")),
):
    calc = calculate_tax(
        TaxCalculationRequest(
            income=payload.income,
            expenses=payload.expenses,
            entity_type=payload.entity_type,
        )
    )
    record = models.TaxRecord(
        entity_name=payload.entity_name,
        tax_year=payload.tax_year,
        income=payload.income,
        expenses=payload.expenses,
        tax_due=calc["tax_due"],
        entity_type=payload.entity_type,
        created_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[TaxRecordResponse])
def list_records(
    skip: int = 0,
    limit: int = 50,
    tax_year: Optional[int] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("records:read")),
):
    q = db.query(models.TaxRecord)
    if tax_year:
        q = q.filter(models.TaxRecord.tax_year == tax_year)
    return q.offset(skip).limit(limit).all()


@router.get("/{record_id}", response_model=TaxRecordResponse)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("records:read")),
):
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")
    return record


@router.patch("/{record_id}", response_model=TaxRecordResponse)
def update_record(
    record_id: int,
    payload: TaxRecordUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("records:write")),
):
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    if "income" in update_data or "expenses" in update_data:
        calc = calculate_tax(
            TaxCalculationRequest(income=record.income, expenses=record.expenses)
        )
        record.tax_due = calc["tax_due"]

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=204)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("records:write")),
):
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")
    db.delete(record)
    db.commit()
