"""
Immutable audit log writer.

Every write to an audit log entry is append-only; records are never updated
or deleted (enforced at the application layer — no UPDATE/DELETE methods here).

Usage:
    from audit.logger import log_action

    log_action(
        db=db,
        user_id=current_user.id,
        action="create",
        resource_type="tax_record",
        resource_id=record.id,
        tenant_id=request.state.tenant_id,
        ip_address=request.client.host if request.client else None,
        details={"entity_name": record.entity_name},
    )
"""
import json
from typing import Optional
from sqlalchemy.orm import Session
from app import models
from tax_capsule.utils.logger import get_logger

logger = get_logger("AuditLog")


def log_action(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: Optional[int] = None,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict] = None,
) -> models.AuditLog:
    """
    Append an immutable audit log entry.
    Returns the created AuditLog record.
    """
    entry = models.AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=tenant_id,
        ip_address=ip_address,
        details=json.dumps(details, default=str) if details else None,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info(
        f"AUDIT: action={action} resource={resource_type}:{resource_id} "
        f"user={user_id} tenant={tenant_id}"
    )
    return entry


def get_audit_trail(
    db: Session,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    limit: int = 100,
) -> list[models.AuditLog]:
    """Query audit log with optional filters."""
    q = db.query(models.AuditLog).order_by(models.AuditLog.created_at.desc())
    if resource_type:
        q = q.filter(models.AuditLog.resource_type == resource_type)
    if resource_id is not None:
        q = q.filter(models.AuditLog.resource_id == resource_id)
    if user_id is not None:
        q = q.filter(models.AuditLog.user_id == user_id)
    if tenant_id is not None:
        q = q.filter(models.AuditLog.tenant_id == tenant_id)
    return q.limit(limit).all()
