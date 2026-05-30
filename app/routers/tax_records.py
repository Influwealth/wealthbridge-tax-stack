from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.rbac import require_permission
from app.cache import cache_get, cache_set, cache_delete
from app.tasks import invalidate_record_cache
from tax_capsule.utils.schemas import TaxRecordCreate, TaxRecordUpdate, TaxRecordResponse, TaxCalculationRequest
from tax_capsule.tax_engine import calculate_tax

router = APIRouter(prefix="/tax/records", tags=["tax-records"])

_RECORD_TTL = 120   # 2 min cache for individual records


def _record_key(record_id: int) -> str:
    return f"record:{record_id}:detail"


@router.post("/", response_model=TaxRecordResponse, status_code=201)
def create_record(
    payload: TaxRecordCreate,
    background_tasks: BackgroundTasks,
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
    # Evict list caches after write
    background_tasks.add_task(cache_delete, "records:list")
    return record


@router.get("/", response_model=List[TaxRecordResponse])
def list_records(
    skip: int = 0,
    limit: int = 50,
    tax_year: Optional[int] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("records:read")),
):
    # Cache only the first page with no filters
    cache_key = f"records:list:{tax_year}:{skip}:{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    q = db.query(models.TaxRecord)
    if tax_year:
        q = q.filter(models.TaxRecord.tax_year == tax_year)
    results = q.offset(skip).limit(limit).all()

    # Serialize via Pydantic then cache
    serialized = [TaxRecordResponse.model_validate(r).model_dump(mode="json") for r in results]
    cache_set(cache_key, serialized, ttl=60)
    return results


@router.get("/{record_id}", response_model=TaxRecordResponse)
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("records:read")),
):
    cached = cache_get(_record_key(record_id))
    if cached is not None:
        return cached

    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")

    serialized = TaxRecordResponse.model_validate(record).model_dump(mode="json")
    cache_set(_record_key(record_id), serialized, ttl=_RECORD_TTL)
    return record


@router.patch("/{record_id}", response_model=TaxRecordResponse)
def update_record(
    record_id: int,
    payload: TaxRecordUpdate,
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(invalidate_record_cache, record_id)
    return record


@router.delete("/{record_id}", status_code=204)
def delete_record(
    record_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("records:write")),
):
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")
    db.delete(record)
    db.commit()
    background_tasks.add_task(invalidate_record_cache, record_id)
