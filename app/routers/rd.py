"""
R&D Credit router — QRE Agent integration.

All write endpoints require filings:write (accountant or admin).
All read endpoints require filings:read.
"""
import json
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.rbac import require_permission
from qre_agent.classifier import classify_activity
from qre_agent.scorer import score_expense, ExpenseCategory
from qre_agent.validator import validate_project_documentation
from qre_agent.engine import calculate_credit, analyze_project
from tax_capsule.utils.schemas import (
    RDProjectCreate, RDProjectUpdate, RDProjectResponse,
    RDExpenseCreate, RDExpenseResponse,
    RDDocumentSubmit, RDDocumentResponse,
    RDCreditSummary,
)

router = APIRouter(prefix="/rd", tags=["rd-credit"])


def _get_project_or_404(project_id: int, db: Session) -> models.RDProject:
    project = db.query(models.RDProject).filter(models.RDProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="R&D project not found")
    return project


# ─── Projects ────────────────────────────────────────────────────────────────

@router.post("/projects", response_model=RDProjectResponse, status_code=201)
def create_project(
    payload: RDProjectCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:write")),
):
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == payload.record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")

    project = models.RDProject(
        record_id=payload.record_id,
        project_name=payload.project_name,
        description=payload.description,
        principal_researcher=payload.principal_researcher,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_ongoing=payload.is_ongoing,
    )

    # Auto-classify if description provided
    if payload.description:
        activity = classify_activity(payload.description)
        from qre_agent.classifier import is_qualified_activity
        project.activity_type = activity.value
        project.is_qualified = is_qualified_activity(activity)

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=List[RDProjectResponse])
def list_projects(
    record_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    q = db.query(models.RDProject)
    if record_id is not None:
        q = q.filter(models.RDProject.record_id == record_id)
    return q.all()


@router.get("/projects/{project_id}", response_model=RDProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    return _get_project_or_404(project_id, db)


@router.patch("/projects/{project_id}", response_model=RDProjectResponse)
def update_project(
    project_id: int,
    payload: RDProjectUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:write")),
):
    project = _get_project_or_404(project_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    # Re-classify if description changed
    if payload.description is not None:
        activity = classify_activity(payload.description)
        from qre_agent.classifier import is_qualified_activity
        project.activity_type = activity.value
        project.is_qualified = is_qualified_activity(activity)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:write")),
):
    project = _get_project_or_404(project_id, db)
    db.delete(project)
    db.commit()


# ─── Expenses ────────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/expenses", response_model=RDExpenseResponse, status_code=201)
def add_expense(
    project_id: int,
    payload: RDExpenseCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:write")),
):
    project = _get_project_or_404(project_id, db)

    scored = score_expense(ExpenseCategory(payload.category), Decimal(str(payload.amount)))

    expense = models.RDExpense(
        project_id=project.id,
        category=payload.category,
        description=payload.description,
        amount=scored.amount,
        qualification_rate=scored.qualification_rate,
        qualified_amount=scored.qualified_amount,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/projects/{project_id}/expenses", response_model=List[RDExpenseResponse])
def list_expenses(
    project_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    _get_project_or_404(project_id, db)
    return db.query(models.RDExpense).filter(models.RDExpense.project_id == project_id).all()


@router.delete("/projects/{project_id}/expenses/{expense_id}", status_code=204)
def delete_expense(
    project_id: int,
    expense_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:write")),
):
    expense = (
        db.query(models.RDExpense)
        .filter(models.RDExpense.id == expense_id, models.RDExpense.project_id == project_id)
        .first()
    )
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(expense)
    db.commit()


# ─── Documents ───────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/documents", response_model=RDDocumentResponse, status_code=201)
def submit_document(
    project_id: int,
    payload: RDDocumentSubmit,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:write")),
):
    project = _get_project_or_404(project_id, db)

    # Validate the document submission
    result = validate_project_documentation({
        "project_name": project.project_name,
        "description": project.description or "",
        "activity_type": project.activity_type or "",
        "start_date": project.start_date,
        "end_date": project.end_date,
        "is_ongoing": project.is_ongoing,
        "principal_researcher": project.principal_researcher,
        "has_expenses": len(project.expenses) > 0,
        "expense_count": len(project.expenses),
    })

    doc = models.RDDocument(
        project_id=project.id,
        doc_name=payload.doc_name,
        doc_type=payload.doc_type,
        is_valid=result.is_valid,
        validation_score=result.score,
        issues=json.dumps(result.issues) if result.issues else None,
    )
    db.add(doc)

    # Update project validation score
    project.validation_score = result.score
    db.commit()
    db.refresh(doc)
    return doc


# ─── Credit Calculation ───────────────────────────────────────────────────────

@router.post("/projects/{project_id}/calculate", response_model=dict)
def calculate_project_credit(
    project_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:write")),
):
    project = _get_project_or_404(project_id, db)

    expenses_data = [
        {
            "category": e.category,
            "amount": str(e.amount),
            "description": e.description or "",
        }
        for e in project.expenses
    ]

    if not project.is_qualified:
        return {
            "project_id": project_id,
            "project_name": project.project_name,
            "status": "NOT_QUALIFIED",
            "total_qre": "0.00",
            "estimated_credit": "0.00",
            "message": "Activity type is not qualified under IRC §41.",
        }

    if not expenses_data:
        return {
            "project_id": project_id,
            "project_name": project.project_name,
            "status": "NO_EXPENSES",
            "total_qre": "0.00",
            "estimated_credit": "0.00",
            "message": "No expenses recorded for this project.",
        }

    result = calculate_credit(expenses_data)

    # Persist updated totals
    project.total_qre = Decimal(result["total_qre"])
    project.estimated_credit = Decimal(result["estimated_credit"])
    db.commit()

    return {
        "project_id": project_id,
        "project_name": project.project_name,
        **result,
    }


# ─── Record-level Summary ─────────────────────────────────────────────────────

@router.get("/summary/{record_id}", response_model=RDCreditSummary)
def get_credit_summary(
    record_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("filings:read")),
):
    record = db.query(models.TaxRecord).filter(models.TaxRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Tax record not found")

    projects = db.query(models.RDProject).filter(models.RDProject.record_id == record_id).all()
    total_qre = sum(Decimal(str(p.total_qre)) for p in projects)
    total_credit = sum(Decimal(str(p.estimated_credit)) for p in projects)

    return RDCreditSummary(
        record_id=record_id,
        project_count=len(projects),
        total_qre=total_qre,
        total_estimated_credit=total_credit,
        projects=[RDProjectResponse.model_validate(p) for p in projects],
    )
