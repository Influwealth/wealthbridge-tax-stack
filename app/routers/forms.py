from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.rbac import require_permission
from irs_forms.form_1065 import generate_1065
from irs_forms.form_1120 import generate_1120
from irs_forms.form_941 import generate_941
from irs_forms.form_schedule_c import generate_schedule_c
from irs_forms.form_w2 import generate_w2
from irs_forms.form_1099_nec import generate_1099_nec
from irs_forms.state.ny_it201 import generate_ny_it201
from irs_forms.state.ca_540 import generate_ca_540
from irs_forms.state.tx_franchise import generate_tx_franchise
from irs_forms.base import FormValidationError

router = APIRouter(prefix="/forms", tags=["irs-forms"])

STATE_GENERATORS = {
    "ny": {"it201": generate_ny_it201},
    "ca": {"540": generate_ca_540},
    "tx": {"franchise": generate_tx_franchise},
}


def _get_record_or_404(record_id: int, db: Session) -> models.TaxRecord:
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")
    return record


def _handle_form_error(e: FormValidationError):
    raise HTTPException(status_code=422, detail=str(e))


@router.post("/1065/{record_id}")
def generate_form_1065(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    record = _get_record_or_404(record_id, db)
    try:
        return generate_1065(record)
    except FormValidationError as e:
        _handle_form_error(e)


@router.post("/1120/{record_id}")
def generate_form_1120(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    record = _get_record_or_404(record_id, db)
    try:
        return generate_1120(record)
    except FormValidationError as e:
        _handle_form_error(e)


@router.post("/941/{record_id}")
def generate_form_941(
    record_id: int,
    quarter: int = 1,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    record = _get_record_or_404(record_id, db)
    if quarter not in (1, 2, 3, 4):
        raise HTTPException(status_code=422, detail="Quarter must be 1-4")
    try:
        return generate_941(record, quarter=quarter)
    except FormValidationError as e:
        _handle_form_error(e)


@router.post("/schedule-c/{record_id}")
def generate_form_schedule_c(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    record = _get_record_or_404(record_id, db)
    try:
        return generate_schedule_c(record)
    except FormValidationError as e:
        _handle_form_error(e)


@router.post("/w2/{record_id}")
def generate_form_w2(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    record = _get_record_or_404(record_id, db)
    try:
        return generate_w2(record)
    except FormValidationError as e:
        _handle_form_error(e)


@router.post("/1099-nec/{record_id}")
def generate_form_1099_nec(
    record_id: int,
    backup_withholding: bool = False,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    record = _get_record_or_404(record_id, db)
    try:
        return generate_1099_nec(record, apply_backup_withholding=backup_withholding)
    except FormValidationError as e:
        _handle_form_error(e)


@router.post("/state/{state}/{form_name}/{record_id}")
def generate_state_form(
    state: str,
    form_name: str,
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    state = state.lower()
    form_name = form_name.lower()
    if state not in STATE_GENERATORS or form_name not in STATE_GENERATORS[state]:
        raise HTTPException(
            status_code=404,
            detail=f"No state form generator for {state.upper()}/{form_name}. "
                   f"Available: ny/it201, ca/540, tx/franchise",
        )
    record = _get_record_or_404(record_id, db)
    try:
        return STATE_GENERATORS[state][form_name](record)
    except FormValidationError as e:
        _handle_form_error(e)
