"""
Admin router — firm and tenant management.

All endpoints require the 'admin' role (users:manage permission).
Provides the hierarchical Firm → Tenant structure for multi-tenant isolation.
"""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.rbac import require_permission
from audit.logger import log_action, get_audit_trail

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class FirmCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9\-]+$")
    plan: str = Field(default="starter", pattern=r"^(starter|pro|enterprise)$")


class FirmResponse(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    plan: str
    tenant_count: int = 0


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    external_id: Optional[str] = None


class TenantResponse(BaseModel):
    id: int
    firm_id: int
    name: str
    external_id: Optional[str]
    is_active: bool


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[int]
    tenant_id: Optional[int]
    ip_address: Optional[str]
    details: Optional[str]
    created_at: str


# ─── Firms ───────────────────────────────────────────────────────────────────

@router.post("/firms", response_model=FirmResponse, status_code=201)
def create_firm(
    payload: FirmCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("users:manage")),
):
    if db.query(models.Firm).filter(models.Firm.slug == payload.slug).first():
        raise HTTPException(status_code=409, detail=f"Firm with slug '{payload.slug}' already exists")

    firm = models.Firm(name=payload.name, slug=payload.slug, plan=payload.plan)
    db.add(firm)
    db.commit()
    db.refresh(firm)

    log_action(
        db=db, action="create", resource_type="firm", resource_id=firm.id,
        user_id=current_user.id, ip_address=request.client.host if request.client else None,
        details={"name": firm.name, "slug": firm.slug},
    )
    return FirmResponse(id=firm.id, name=firm.name, slug=firm.slug,
                        is_active=firm.is_active, plan=firm.plan, tenant_count=0)


@router.get("/firms", response_model=List[FirmResponse])
def list_firms(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("users:manage")),
):
    firms = db.query(models.Firm).filter(models.Firm.is_active == True).all()
    return [
        FirmResponse(
            id=f.id, name=f.name, slug=f.slug, is_active=f.is_active,
            plan=f.plan, tenant_count=len(f.tenants),
        )
        for f in firms
    ]


@router.delete("/firms/{firm_id}", status_code=204)
def deactivate_firm(
    firm_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("users:manage")),
):
    firm = db.query(models.Firm).filter(models.Firm.id == firm_id).first()
    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found")
    firm.is_active = False
    db.commit()
    log_action(
        db=db, action="deactivate", resource_type="firm", resource_id=firm_id,
        user_id=current_user.id, ip_address=request.client.host if request.client else None,
    )


# ─── Tenants ──────────────────────────────────────────────────────────────────

@router.post("/firms/{firm_id}/tenants", response_model=TenantResponse, status_code=201)
def create_tenant(
    firm_id: int,
    payload: TenantCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("users:manage")),
):
    firm = db.query(models.Firm).filter(models.Firm.id == firm_id, models.Firm.is_active == True).first()
    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found or inactive")

    tenant = models.Tenant(firm_id=firm_id, name=payload.name, external_id=payload.external_id)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    log_action(
        db=db, action="create", resource_type="tenant", resource_id=tenant.id,
        user_id=current_user.id, tenant_id=tenant.id,
        ip_address=request.client.host if request.client else None,
        details={"name": tenant.name, "firm_id": firm_id},
    )
    return TenantResponse(id=tenant.id, firm_id=tenant.firm_id, name=tenant.name,
                          external_id=tenant.external_id, is_active=tenant.is_active)


@router.get("/firms/{firm_id}/tenants", response_model=List[TenantResponse])
def list_tenants(
    firm_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("users:manage")),
):
    firm = db.query(models.Firm).filter(models.Firm.id == firm_id).first()
    if not firm:
        raise HTTPException(status_code=404, detail="Firm not found")
    return [
        TenantResponse(id=t.id, firm_id=t.firm_id, name=t.name,
                       external_id=t.external_id, is_active=t.is_active)
        for t in firm.tenants if t.is_active
    ]


@router.delete("/firms/{firm_id}/tenants/{tenant_id}", status_code=204)
def deactivate_tenant(
    firm_id: int,
    tenant_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("users:manage")),
):
    tenant = db.query(models.Tenant).filter(
        models.Tenant.id == tenant_id,
        models.Tenant.firm_id == firm_id,
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    tenant.is_active = False
    db.commit()
    log_action(
        db=db, action="deactivate", resource_type="tenant", resource_id=tenant_id,
        user_id=current_user.id, tenant_id=tenant_id,
        ip_address=request.client.host if request.client else None,
    )


# ─── Audit log ───────────────────────────────────────────────────────────────

@router.get("/audit-log", response_model=List[AuditLogResponse])
def read_audit_log(
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("audit:read")),
):
    logs = get_audit_trail(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        tenant_id=tenant_id,
        limit=min(limit, 500),
    )
    return [
        AuditLogResponse(
            id=lg.id,
            user_id=lg.user_id,
            action=lg.action,
            resource_type=lg.resource_type,
            resource_id=lg.resource_id,
            tenant_id=lg.tenant_id,
            ip_address=lg.ip_address,
            details=lg.details,
            created_at=str(lg.created_at),
        )
        for lg in logs
    ]
