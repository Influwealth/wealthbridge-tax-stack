"""
RBAC permission engine.

Permission matrix — which roles hold which scopes:
  admin          : all scopes
  accountant     : filings:read/write/submit, expenses:read/approve, records:read/write, audit:read
  business_owner : filings:read/submit, expenses:read, records:read/write
  agent          : filings:read, records:read, expenses:read
  auditor        : filings:read, audit:read, records:read, expenses:read
"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app import models

# All available permission scopes
SCOPES = {
    "filings:read",
    "filings:write",
    "filings:submit",
    "filings:approve",
    "expenses:read",
    "expenses:approve",
    "records:read",
    "records:write",
    "users:manage",
    "audit:read",
}

# Role → set of allowed scopes
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": set(SCOPES),  # admin holds every scope
    "accountant": {
        "filings:read", "filings:write", "filings:submit",
        "expenses:read", "expenses:approve",
        "records:read", "records:write",
        "audit:read",
    },
    "business_owner": {
        "filings:read", "filings:submit",
        "expenses:read",
        "records:read", "records:write",
    },
    "agent": {
        "filings:read",
        "records:read",
        "expenses:read",
    },
    "auditor": {
        "filings:read",
        "audit:read",
        "records:read",
        "expenses:read",
    },
}


def user_has_permission(user: models.User, scope: str) -> bool:
    """Return True if any of the user's roles grants the given scope."""
    for role in user.roles:
        if scope in ROLE_PERMISSIONS.get(role, set()):
            return True
    return False


def require_permission(scope: str):
    """
    FastAPI dependency factory.
    Usage: Depends(require_permission("filings:submit"))
    """
    def _check(
        current_user: models.User = Depends(get_current_user),
    ) -> models.User:
        if not user_has_permission(current_user, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{scope}' required",
            )
        return current_user

    return _check


def require_any_role(*roles: str):
    """Dependency that passes if the user holds at least one of the given roles."""
    def _check(
        current_user: models.User = Depends(get_current_user),
    ) -> models.User:
        for role in roles:
            if current_user.has_role(role):
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role required: one of {list(roles)}",
        )

    return _check
