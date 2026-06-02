"""
Documents router — generate, store, retrieve, validate, and delete tax documents.
Supports PDF (pure-Python) and XML (MeF stub) output.
"""
from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.rbac import require_permission
from documents.pdf_filler import fill_form_pdf
from documents.xml_efile import generate_1120_xml, generate_1065_xml
from documents.vault import store_document, retrieve_document, list_documents, delete_document, validate_document

# Import form generators
from irs_forms.form_1065 import generate_1065
from irs_forms.form_1120 import generate_1120
from irs_forms.form_941 import generate_941
from irs_forms.form_schedule_c import generate_schedule_c
from irs_forms.form_w2 import generate_w2
from irs_forms.form_1099_nec import generate_1099_nec
from irs_forms.base import FormValidationError

router = APIRouter(prefix="/documents", tags=["documents"])

FORM_GENERATORS = {
    "1065": generate_1065,
    "1120": generate_1120,
    "941": generate_941,
    "schedule_c": generate_schedule_c,
    "w2": generate_w2,
    "1099_nec": generate_1099_nec,
}

XML_GENERATORS = {
    "1120": generate_1120_xml,
    "1065": generate_1065_xml,
}


class DocumentMeta(BaseModel):
    id: Optional[int] = None
    record_id: int
    doc_type: str
    format: str
    vault_key: str
    size_bytes: Optional[int]
    checksum_sha256: Optional[str]
    stored_at: Optional[str] = None


def _get_record_or_404(record_id: int, db: Session) -> models.TaxRecord:
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")
    return record


@router.post("/{record_id}/generate/{doc_type}")
def generate_document(
    record_id: int,
    doc_type: str,
    fmt: Literal["pdf", "xml", "json"] = "pdf",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("filings:read")),
):
    """
    Generate a document for a tax record and store it in the vault.
    Returns document metadata.
    """
    record = _get_record_or_404(record_id, db)

    if doc_type not in FORM_GENERATORS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown doc_type '{doc_type}'. Available: {list(FORM_GENERATORS)}",
        )

    try:
        form_data = FORM_GENERATORS[doc_type](record)
    except FormValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if fmt == "json":
        import json
        content = json.dumps(form_data, default=str, indent=2).encode()
    elif fmt == "xml":
        if doc_type not in XML_GENERATORS:
            raise HTTPException(
                status_code=422,
                detail=f"XML e-file not available for '{doc_type}'. Supported: {list(XML_GENERATORS)}",
            )
        content = XML_GENERATORS[doc_type](form_data).encode()
    else:  # pdf
        content = fill_form_pdf(form_data)

    meta = store_document(record_id, doc_type, fmt, content)

    # Persist metadata to DB
    doc = models.TaxDocument(
        record_id=record_id,
        doc_type=doc_type,
        format=fmt,
        vault_key=meta["key"],
        size_bytes=meta["size_bytes"],
        checksum_sha256=meta["checksum_sha256"],
        created_by=current_user.id,
    )
    db.add(doc)
    db.commit()

    return meta


@router.get("/{record_id}/list")
def list_record_documents(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    """List all stored documents for a tax record."""
    _get_record_or_404(record_id, db)
    return list_documents(record_id=record_id)


@router.get("/{record_id}/retrieve/{doc_type}")
def retrieve_record_document(
    record_id: int,
    doc_type: str,
    fmt: Literal["pdf", "xml", "json"] = "pdf",
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    """Retrieve a stored document as a binary response."""
    _get_record_or_404(record_id, db)
    content = retrieve_document(record_id, doc_type, fmt)
    if content is None:
        raise HTTPException(status_code=404, detail="Document not found in vault")

    media_types = {"pdf": "application/pdf", "xml": "application/xml", "json": "application/json"}
    return Response(
        content=content,
        media_type=media_types.get(fmt, "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="record_{record_id}_{doc_type}.{fmt}"'},
    )


@router.get("/{record_id}/validate/{doc_type}")
def validate_record_document(
    record_id: int,
    doc_type: str,
    fmt: Literal["pdf", "xml", "json"] = "pdf",
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    """Validate a stored document by checksum."""
    _get_record_or_404(record_id, db)
    return validate_document(record_id, doc_type, fmt)


@router.delete("/{record_id}/delete/{doc_type}", status_code=204)
def delete_record_document(
    record_id: int,
    doc_type: str,
    fmt: Literal["pdf", "xml", "json"] = "pdf",
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("filings:write")),
):
    """Delete a stored document from the vault and DB record."""
    _get_record_or_404(record_id, db)
    deleted = delete_document(record_id, doc_type, fmt)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    # Remove DB record
    db.query(models.TaxDocument).filter(
        models.TaxDocument.record_id == record_id,
        models.TaxDocument.doc_type == doc_type,
        models.TaxDocument.format == fmt,
    ).delete()
    db.commit()
