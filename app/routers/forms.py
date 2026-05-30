from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.auth import get_current_user
from irs_forms.form_1065 import generate_1065
from irs_forms.form_1120 import generate_1120
from irs_forms.form_941 import generate_941

router = APIRouter(prefix="/forms", tags=["irs-forms"])


def _get_record_or_404(record_id: int, db: Session) -> models.TaxRecord:
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")
    return record


@router.post("/1065/{record_id}")
def generate_form_1065(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    record = _get_record_or_404(record_id, db)
    if record.entity_type != "partnership":
        raise HTTPException(
            status_code=422, detail="Form 1065 requires entity_type='partnership'"
        )
    return generate_1065(record)


@router.post("/1120/{record_id}")
def generate_form_1120(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    record = _get_record_or_404(record_id, db)
    if record.entity_type != "corporation":
        raise HTTPException(
            status_code=422, detail="Form 1120 requires entity_type='corporation'"
        )
    return generate_1120(record)


@router.post("/941/{record_id}")
def generate_form_941(
    record_id: int,
    quarter: int = 1,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    record = _get_record_or_404(record_id, db)
    if record.entity_type != "employer":
        raise HTTPException(
            status_code=422, detail="Form 941 requires entity_type='employer'"
        )
    if quarter not in (1, 2, 3, 4):
        raise HTTPException(status_code=422, detail="Quarter must be 1-4")
    return generate_941(record, quarter=quarter)
