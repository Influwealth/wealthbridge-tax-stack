from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.rbac import require_permission, require_any_role
from tax_capsule.utils.schemas import (
    UserWithRolesResponse,
    RoleAssign,
    RoleRevoke,
    UserRoleResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserWithRolesResponse])
def list_users(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("users:manage")),
):
    users = db.query(models.User).all()
    return [
        UserWithRolesResponse(
            id=u.id,
            username=u.username,
            is_active=u.is_active,
            roles=u.roles,
        )
        for u in users
    ]


@router.get("/me", response_model=UserWithRolesResponse)
def get_me(
    current_user: models.User = Depends(require_any_role(
        "admin", "accountant", "business_owner", "agent", "auditor"
    )),
):
    return UserWithRolesResponse(
        id=current_user.id,
        username=current_user.username,
        is_active=current_user.is_active,
        roles=current_user.roles,
    )


@router.post("/roles/assign", response_model=UserRoleResponse, status_code=201)
def assign_role(
    payload: RoleAssign,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_permission("users:manage")),
):
    target = db.query(models.User).filter(models.User.username == payload.username).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = (
        db.query(models.UserRole)
        .filter(
            models.UserRole.user_id == target.id,
            models.UserRole.role == payload.role,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="User already has this role")

    user_role = models.UserRole(
        user_id=target.id,
        role=payload.role,
        granted_by=current_user.id,
    )
    db.add(user_role)
    db.commit()
    db.refresh(user_role)
    return user_role


@router.post("/roles/revoke", status_code=204)
def revoke_role(
    payload: RoleRevoke,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_permission("users:manage")),
):
    target = db.query(models.User).filter(models.User.username == payload.username).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    user_role = (
        db.query(models.UserRole)
        .filter(
            models.UserRole.user_id == target.id,
            models.UserRole.role == payload.role,
        )
        .first()
    )
    if not user_role:
        raise HTTPException(status_code=404, detail="Role not assigned to user")

    db.delete(user_role)
    db.commit()
